import os
import asyncio
import random
import re
import tempfile
import yt_dlp
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ChatPermissions, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from aiohttp import web

TOKEN = "8558117158:AAG9MRnBKXqnTlWdPd_SxSM9JOfWyFAEwzw"

# ================ БАЗА ДАННЫХ ================
conn = sqlite3.connect('bot_database.db')
cursor = conn.cursor()
# Таблица для статистики видео
cursor.execute('''
    CREATE TABLE IF NOT EXISTS video_stats (
        video_url TEXT PRIMARY KEY,
        video_name TEXT,
        download_count INTEGER DEFAULT 0
    )
''')
# Таблица для антиспама
cursor.execute('''
    CREATE TABLE IF NOT EXISTS spam_warnings (
        user_id INTEGER,
        chat_id INTEGER,
        warning_count INTEGER DEFAULT 0,
        last_message_time TIMESTAMP,
        last_message_text TEXT,
        PRIMARY KEY (user_id, chat_id)
    )
''')
conn.commit()

def update_video_stat(video_url, video_name):
    cursor.execute('''
        INSERT INTO video_stats (video_url, video_name, download_count)
        VALUES (?, ?, 1)
        ON CONFLICT(video_url) DO UPDATE SET
            download_count = download_count + 1,
            video_name = excluded.video_name
    ''', (video_url, video_name))
    conn.commit()

def get_top_videos(limit=5):
    cursor.execute('''
        SELECT video_name, download_count FROM video_stats
        ORDER BY download_count DESC LIMIT ?
    ''', (limit,))
    return cursor.fetchall()

# ================ АНТИСПАМ ================
BAD_WORDS = ['хуй', 'пизда', 'блядь', 'сука', 'ебать', 'нахер', 'далбаеб']
user_spam_data = defaultdict(list)  # {user_id: [list_of_message_times]}

async def check_spam(message: types.Message) -> bool:
    user_id = message.from_user.id
    chat_id = message.chat.id
    now = datetime.now()
    text = message.text or message.caption or ""

    # Проверка на плохие слова
    if any(bad_word in text.lower() for bad_word in BAD_WORDS):
        await message.reply("⚠️ Не выражайся!")

    # Проверка на частые сообщения
    user_spam_data[user_id].append(now)
    # Оставляем только сообщения за последние 30 секунд
    user_spam_data[user_id] = [t for t in user_spam_data[user_id] if (now - t).seconds < 30]

    if len(user_spam_data[user_id]) > 5:
        # Достаём из базы или создаём запись о предупреждениях
        cursor.execute('SELECT warning_count FROM spam_warnings WHERE user_id=? AND chat_id=?', (user_id, chat_id))
        result = cursor.fetchone()
        warning_count = result[0] if result else 0

        if warning_count >= 2:
            # Мутим на 10 минут
            mute_time = timedelta(minutes=10)
            until_date = datetime.now() + mute_time
            try:
                await message.bot.restrict_chat_member(
                    chat_id, user_id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=until_date
                )
                await message.reply("🚫 Автоматический мут на 10 минут за спам.")
                # Сбрасываем счётчик
                cursor.execute('DELETE FROM spam_warnings WHERE user_id=? AND chat_id=?', (user_id, chat_id))
                conn.commit()
            except:
                pass
        else:
            # Увеличиваем счётчик предупреждений
            cursor.execute('''
                INSERT INTO spam_warnings (user_id, chat_id, warning_count, last_message_time, last_message_text)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, chat_id) DO UPDATE SET
                    warning_count = warning_count + 1,
                    last_message_time = excluded.last_message_time,
                    last_message_text = excluded.last_message_text
            ''', (user_id, chat_id, 1, now, text[:100]))
            conn.commit()
            await message.reply("⚠️ Предупреждение: не спамь! Ещё пару раз и получишь мут.")
        return True
    return False

# ================ БИБЛИОТЕКА ВИДЕО ================
VIDEO_LIBRARY = [
    {"name": "што ты маленький привет", "url": "https://www.tiktok.com/@mels_tro/video/7356116038204902677"},
    {"name": "стоп стоп бля я далбаеб", "url": "https://www.tiktok.com/@mels_tro/video/7345126018006420738"},
    {"name": "поступление денег", "url": "https://www.tiktok.com/@mels_tro/video/7332865419998465298"},
    {"name": "мелл одинок", "url": "https://www.tiktok.com/@futazh1488/video/7600761564991327495"},
