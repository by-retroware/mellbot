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

# ================ ТВОЙ ID (ТОЛЬКО ТЫ СМОЖЕШЬ МУТИТЬ/БАНИТЬ) ================
OWNER_ID = 5695593671

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
    {"name": "оборачивается и смеется", "url": "https://www.tiktok.com/@mels_tro/video/7347727557187439874"},
    {"name": "сьебал в пиджаке", "url": "https://www.tiktok.com/@mels_tro/video/7367471179491282197"},
    {"name": "орущий мелл(жирный)", "url": "https://www.tiktok.com/@alena_lifonova/video/7593733962476932382"},
    {"name": "блять давай", "url": "https://www.tiktok.com/@glavaborovnarezki/video/7333572410811092267"},
    {"name": "мелл кликает", "url": "https://www.tiktok.com/@mellstroyzelyoniyfon/video/7344311380704791854"},
    {"name": "подозрительный мелл", "url": "https://www.tiktok.com/@mels_tro/video/7347087044960701717"},
    {"name": "ААААА", "url": "https://www.tiktok.com/@mels_tro/video/7347220322459880725"},
    {"name": "Бляя", "url": "https://vt.tiktok.com/ZSmqukRfC/"},
    {"name": "я помылся", "url": "https://vt.tiktok.com/ZSmquBcQf/"},
    {"name": "мелл звонит", "url": "https://vt.tiktok.com/ZSmqugFTA/"},
    {"name": "скажи это сон?", "url": "https://vt.tiktok.com/ZSmqu4Vrg/"},
    {"name": "блять давай (2)", "url": "https://vt.tiktok.com/ZSmquPuQV/"},
    {"name": "ахаха нихуя(возмущается)", "url": "https://vt.tiktok.com/ZSmquDAJa/"},
    {"name": "плачущий мелл", "url": "https://vt.tiktok.com/ZSmquHqTy/"},
    {"name": "динахуй от сюда", "url": "https://vt.tiktok.com/ZSmquHgnJ/"},
    {"name": "орущий мелл(громко)", "url": "https://vt.tiktok.com/ZSmquq3BR/"},
    {"name": "еще посидим", "url": "https://vt.tiktok.com/ZSmqu41dC/"},
    {"name": "бурмалдалец", "url": "https://vt.tiktok.com/ZSmquaY1K/"},
    {"name": "танцуем все", "url": "https://vt.tiktok.com/ZSmquBdtT/"},
    {"name": "омайгад нихуя", "url": "https://vt.tiktok.com/ZSmquUGBW/"},
    {"name": "мамино золотце", "url": "https://vt.tiktok.com/ZSmquHoSy/"},
    {"name": "маленький фкусный малэшульчек", "url": "https://vimeo.com/1169158351?fl=tl&fe=ec"},
    {"name": "терет руки", "url": "https://vimeo.com/1169158371?fl=tl&fe=ec"},
    {"name": "да убери нахуй это", "url": "https://vimeo.com/1169158396?fl=tl&fe=ec"},
    {"name": "ой баляя", "url": "https://vimeo.com/1169158407?fl=tl&fe=ec"},
    {"name": "они даже пахнут девственостью", "url": "https://vimeo.com/1169158415?fl=tl&fe=ec"},
    {"name": "щяс сделать или потом?", "url": "https://vimeo.com/1169158423?fl=tl&fe=ec"},
    {"name": "думала думала думала", "url": "https://vimeo.com/1169158454?fl=tl&fe=ec"},
    {"name": "быстрее! быстрее!", "url": "https://vimeo.com/1169158603?fl=tl&fe=ec"},
    {"name": "меед потек мед", "url": "https://vimeo.com/1169158638?fl=tl&fe=ec"},
    {"name": "апладисменты мелла", "url": "https://vimeo.com/1169158674?fl=tl&fe=ec"},
    {"name": "пополните баланс", "url": "https://vimeo.com/1169158695?fl=tl&fe=ec"},
    {"name": "иди нахуй далбаеб", "url": "https://vimeo.com/1169158719?fl=tl&fe=ec"},
    {"name": "злится", "url": "https://vimeo.com/1169158739?fl=tl&fe=ec"},
    {"name": "иди нахуй", "url": "https://vimeo.com/1169158779?fl=tl&fe=ec"},
    {"name": "стоп стоп стоп блять я далбаеб", "url": "https://vimeo.com/1169158803?fl=tl&fe=ec"},
    {"name": "сколько нахуй", "url": "https://vimeo.com/1169158822?fl=tl&fe=ec"},
    {"name": "хоть бы сука повезло бляяять", "url": "https://vimeo.com/1169158838?fl=tl&fe=ec"},
    {"name": "будет свет да света будет(новая версия)", "url": "https://vimeo.com/1169158852?fl=tl&fe=ec"},
    {"name": "калдует", "url": "https://vimeo.com/1169158873?fl=tl&fe=ec"},
    {"name": "уронил сумку(приахуел)", "url": "https://vimeo.com/1169158902?fl=tl&fe=ec"},
    {"name": "да дура ебаная говори чмо", "url": "https://vimeo.com/1169158921?fl=tl&fe=ec"},
    {"name": "это кто нахуй", "url": "https://vimeo.com/1169158936?fl=tl&fe=ec"},
    {"name": "ни сиси ни жопы", "url": "https://vimeo.com/1169158954?fl=tl&fe=ec"},
    {"name": "сними спасательный круг", "url": "https://vimeo.com/1169158972?fl=tl&fe=ec"},
    {"name": "ты чот сука борщищь", "url": "https://vimeo.com/1169158989?fl=tl&fe=ec"},
    {"name": "а де калбаска", "url": "https://vimeo.com/1169159010?fl=tl&fe=ec"},
    {"name": "заработал нарулил", "url": "https://vimeo.com/1169159027?fl=tl&fe=ec"},
    {"name": "еще посидим еще посидим", "url": "https://vimeo.com/1169159049?fl=tl&fe=ec"},
    {"name": "есть бля бля есть ", "url": "https://vimeo.com/1169159071?fl=tl&fe=ec"},
    {"name": "я уже красный", "url": "https://vimeo.com/1169159086?fl=tl&fe=ec"},
    {"name": "да пошло оно все нахуй тогда", "url": "https://vimeo.com/1169159108?fl=tl&fe=ec"},
    {"name": "ахахахах это пиздец", "url": "https://vimeo.com/1169159124?fl=tl&fe=ec"},
    {"name": "бляяяять(громко)", "url": "https://vimeo.com/1169159143?fl=tl&fe=ec"},
    {"name": "ты блять далбаеб?", "url": "https://vimeo.com/1169159157?fl=tl&fe=ec"},
    {"name": "я заперт на этом острове изза интерпола", "url": "https://vimeo.com/1169159174?fl=tl&fe=ec"},
    {"name": "ди сюда", "url": "https://vimeo.com/1169159189?fl=tl&fe=ec"},
    {"name": "подозревает что то", "url": "https://vimeo.com/1169159207?fl=tl&fe=ec"},
    {"name": "танцуем все", "url": "https://vimeo.com/1169159220?fl=tl&fe=ec"},
    {"name": "ой ой ой ойойойойой", "url": "https://vimeo.com/1169159242?fl=tl&fe=ec"},
    {"name": "эта пизда или нармалды", "url": "https://vimeo.com/1169159261?fl=tl&fe=ec"},
    {"name": "вот с такенной елдой", "url": "https://vimeo.com/1169159275?fl=tl&fe=ec"},
    {"name": "нет.", "url": "https://vimeo.com/1169159290?fl=tl&fe=ec"},
    {"name": "обидно сука", "url": "https://vimeo.com/1169159299?fl=tl&fe=ec"},
    {"name": "орет(на кресле)", "url": "https://vimeo.com/1169159313?fl=tl&fe=ec"},
    {"name": "а еще я пдф", "url": "https://vimeo.com/1169159325?fl=tl&fe=ec"},
    {"name": "медленно смотрит направо", "url": "https://vimeo.com/1169159339?fl=tl&fe=ec"},
    {"name": "это не сфоткать грех", "url": "https://vimeo.com/1169159372?fl=tl&fe=ec"},
    {"name": "парни прикиньте для него это деньги", "url": "https://vimeo.com/1169159407?fl=tl&fe=ec"},
    {"name": "дай руку", "url": "https://vimeo.com/1169159432?fl=tl&fe=ec"},
    {"name": "даже за лям баксов, нет.", "url": "https://vimeo.com/1169159452?fl=tl&fe=ec"},
    {"name": "ода детка ты такая сладкая конфетка", "url": "https://vimeo.com/1169159465?fl=tl&fe=ec"},
    {"name": "вроде да вроде нет", "url": "https://vimeo.com/1169159496?fl=tl&fe=ec"},
    {"name": "фу блять нахуй я на это посмотрел", "url": "https://vimeo.com/1169159537?fl=tl&fe=ec"},
]

# ================ ФУНКЦИЯ СКАЧИВАНИЯ ВИДЕО ================
async def download_video(url):
    try:
        temp_dir = tempfile.mkdtemp()
        ydl_opts = {
            'format': 'mp4',
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }
        loop = asyncio.get_event_loop()
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                if not os.path.exists(filename):
                    for f in os.listdir(temp_dir):
                        if f.endswith('.mp4'):
                            return os.path.join(temp_dir, f)
                return filename if os.path.exists(filename) else None
        file_path = await loop.run_in_executor(None, download)
        return file_path if file_path else None
    except Exception as e:
        print(f"Ошибка скачивания: {e}")
        return None

# ================ ИНИЦИАЛИЗАЦИЯ ================
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ================ ФУНКЦИЯ ПРОВЕРКИ ВЛАДЕЛЬЦА ================
def is_owner(user_id):
    return user_id == OWNER_ID

# ================ ПРИВЕТСТВИЕ НОВИЧКОВ ================
@dp.chat_member()
async def greet_new_member(event: types.ChatMemberUpdated):
    if event.old_chat_member.status in ("left", "kicked") and event.new_chat_member.status == "member":
        user = event.new_chat_member.user
        await event.answer(
            f"🥳 Привет, {user.full_name}! Добро пожаловать в чат! Пропиши /help чтобы узнать все команды"
        )

# ================ КОМАНДА /help ================
@dp.message(Command("help", "start"))
async def cmd_help(message: types.Message):
    help_text = """
🤖 **Видео-бот — команды**

**Видео:**
/videos — список видео с кнопками
/video [номер] — видео по номеру
/randomvideo — случайное видео
/searchvideo [слово] — поиск видео по названию
/topvideo — топ-5 популярных видео

**Модерация (только для создателя бота):**
/mute [время] [причина] — замутить пользователя
/unmute — снять мут
/ban [причина] — забанить пользователя
/unban — разбанить
/mute_list — список замученных

**Другое:**
/myid — узнать свой ID
    """
    await message.reply(help_text)

# ================ ВИДЕО КОМАНДЫ ================

# Храним текущую страницу для каждого чата
user_pages = {}

@dp.message(Command("videos"))
async def cmd_videos(message: types.Message):
    """Обработчик команды /videos"""
    if not VIDEO_LIBRARY:
        await message.reply("📭 Видео пока нет")
        return
    
    # Показываем первую страницу
    await show_video_page(message.chat.id, None, 0)

async def show_video_page(chat_id, message_id, page):
    """Показывает страницу с видео и кнопками навигации"""
    videos_per_page = 10
    total_videos = len(VIDEO_LIBRARY)
    total_pages = (total_videos + videos_per_page - 1) // videos_per_page
    
    start = page * videos_per_page
    end = min(start + videos_per_page, total_videos)
    
    # Формируем текст
    response = f"🎬 **Видео ({start+1}-{end} из {total_videos})**\n\n"
    for i in range(start, end):
        response += f"{i+1}. {VIDEO_LIBRARY[i]['name']}\n"
    response += f"\nСтраница {page+1} из {total_pages}\n"
    response += "👇 Выбери видео по номеру или листай страницы"
    
    # Создаём кнопки с номерами
    buttons = []
    row = []
    for i in range(start + 1, end + 1):
        # Используем короткие callback_data чтобы избежать ошибок
        row.append(InlineKeyboardButton(text=str(i), callback_data=f"vid_{i}"))
        if len(row) == 5:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    # Кнопки навигации
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"prev_{page-1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"next_{page+1}"))
    if nav_row:
        buttons.append(nav_row)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    try:
        if message_id:
            # Редактируем существующее сообщение
            await bot.edit_message_text(
                response,
                chat_id=chat_id,
                message_id=message_id,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        else:
            # Отправляем новое сообщение
            await bot.send_message(
                chat_id,
                response,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
    except Exception as e:
        print(f"Ошибка: {e}")

@dp.callback_query(lambda c: c.data.startswith('prev_'))
async def process_prev_page(callback_query: types.CallbackQuery):
    """Обработчик кнопки Назад"""
    page = int(callback_query.data.split('_')[1])
    await show_video_page(
        callback_query.message.chat.id,
        callback_query.message.message_id,
        page
    )
    await callback_query.answer()

@dp.callback_query(lambda c: c.data.startswith('next_'))
async def process_next_page(callback_query: types.CallbackQuery):
    """Обработчик кнопки Вперёд"""
    page = int(callback_query.data.split('_')[1])
    await show_video_page(
        callback_query.message.chat.id,
        callback_query.message.message_id,
        page
    )
    await callback_query.answer()

@dp.callback_query(lambda c: c.data.startswith('vid_'))
async def process_video_callback(callback_query: types.CallbackQuery):
    """Обработчик выбора видео"""
    try:
        num = int(callback_query.data.split('_')[1]) - 1
        if num < 0 or num >= len(VIDEO_LIBRARY):
            await callback_query.answer("❌ Неверный номер")
            return

        video = VIDEO_LIBRARY[num]
        await callback_query.message.answer(f"⏬ Скачиваю: {video['name']}...")

        file_path = await download_video(video['url'])
        if file_path and os.path.exists(file_path):
            update_video_stat(video['url'], video['name'])
            await callback_query.message.reply_video(
                video=FSInputFile(file_path),
                caption=f"🎥 {video['name']}"
            )
            os.unlink(file_path)
            os.rmdir(os.path.dirname(file_path))
        else:
            await callback_query.message.answer(f"❌ Не удалось скачать видео: {video['name']}")

        await callback_query.answer()
    except Exception as e:
        print(f"Ошибка в video_callback: {e}")
        await callback_query.answer("❌ Произошла ошибка")

@dp.message(Command("searchvideo"))
async def cmd_search_video(message: types.Message):
    query = message.text[12:].strip().lower()
    if not query:
        await message.reply("🔍 Укажи слово для поиска.\nПример: /searchvideo калбаска")
        return

    found = []
    for i, video in enumerate(VIDEO_LIBRARY, 1):
        if query in video['name'].lower():
            found.append(f"{i}. {video['name']}")

    if found:
        response = "🔍 **Найденные видео:**\n\n" + "\n".join(found[:20])
        response += "\n\nИспользуй `/video [номер]` чтобы получить видео."
        await message.reply(response, parse_mode="Markdown")
    else:
        await message.reply("❌ Ничего не найдено.")

@dp.message(Command("topvideo"))
async def cmd_top_video(message: types.Message):
    top_videos = get_top_videos(5)
    if not top_videos:
        await message.reply("📊 Статистика пока пуста. Скачивай видео!")
        return

    response = "🏆 **Топ-5 популярных видео:**\n\n"
    for i, (name, count) in enumerate(top_videos, 1):
        response += f"{i}. {name} — {count} скачиваний\n"
    await message.reply(response, parse_mode="Markdown")

@dp.message(Command("video"))
async def cmd_video(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❌ Укажи номер видео\nПример: /video 5")
        return
    try:
        num = int(args[1]) - 1
        if num < 0 or num >= len(VIDEO_LIBRARY):
            await message.reply(f"❌ Номер должен быть от 1 до {len(VIDEO_LIBRARY)}")
            return
        video = VIDEO_LIBRARY[num]
        status_msg = await message.reply(f"⏬ Скачиваю: {video['name']}...")
        file_path = await download_video(video['url'])
        if file_path and os.path.exists(file_path):
            update_video_stat(video['url'], video['name'])
            await message.reply_video(
                video=FSInputFile(file_path),
                caption=f"🎥 {video['name']}",
                has_spoiler=True
            )
            os.unlink(file_path)
            os.rmdir(os.path.dirname(file_path))
            await status_msg.delete()
        else:
            await status_msg.edit_text(f"❌ Не удалось скачать видео: {video['name']}")
    except ValueError:
        await message.reply("❌ Номер должен быть числом")

@dp.message(Command("randomvideo"))
async def cmd_randomvideo(message: types.Message):
    if not VIDEO_LIBRARY:
        await message.reply("📭 Видео пока нет")
        return
    video = random.choice(VIDEO_LIBRARY)
    status_msg = await message.reply(f"🎲 Случайное видео: {video['name']}\n⏬ Скачиваю...")
    file_path = await download_video(video['url'])
    if file_path and os.path.exists(file_path):
        update_video_stat(video['url'], video['name'])
        await message.reply_video(
            video=FSInputFile(file_path),
            caption=f"🎲 {video['name']}",
            has_spoiler=True
        )
        os.unlink(file_path)
        os.rmdir(os.path.dirname(file_path))
        await status_msg.delete()
    else:
        await status_msg.edit_text(f"❌ Не удалось скачать видео: {video['name']}")

# ================ АНТИСПАМ ================
@dp.message()
async def anti_spam_handler(message: types.Message):
    # Пропускаем команды
    if message.text and message.text.startswith('/'):
        return
    # Пропускаем владельца (тебя)
    if is_owner(message.from_user.id):
        return
    await check_spam(message)

# ================ КОМАНДЫ МОДЕРАЦИИ (ТОЛЬКО ДЛЯ ТЕБЯ) ================
@dp.message(Command("myid"))
async def cmd_myid(message: types.Message):
    await message.reply(f"🆔 Твой ID: `{message.from_user.id}`", parse_mode="Markdown")

@dp.message(Command("mute"))
async def cmd_mute(message: types.Message):
    # Проверяем, что это владелец (ты)
    if not is_owner(message.from_user.id):
        await message.reply("❌ Только создатель бота может использовать эту команду")
        return

    if not message.reply_to_message:
        await message.reply("❌ Ответь на сообщение пользователя")
        return

    user_to_mute = message.reply_to_message.from_user
    chat_id = message.chat.id

    # Нельзя мутить себя
    if is_owner(user_to_mute.id):
        await message.reply("❌ Нельзя замутить создателя бота")
        return

    args = message.text.split(maxsplit=2)
    mute_time = timedelta(minutes=30)
    reason = "Без причины"

    if len(args) >= 2:
        parsed = parse_time(args[1])
        if parsed:
            mute_time = parsed
            if len(args) >= 3:
                reason = args[2]
        else:
            reason = args[1] if len(args) >= 2 else "Без причины"

    until_date = datetime.now() + mute_time

    try:
        permissions = ChatPermissions(
            can_send_messages=False,
            can_send_media_messages=False,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False
        )

        await bot.restrict_chat_member(chat_id, user_to_mute.id, permissions=permissions, until_date=until_date)

        total_seconds = int(mute_time.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60

        duration_parts = []
        if days > 0:
            duration_parts.append(f"{days} дн.")
        if hours > 0:
            duration_parts.append(f"{hours} ч.")
        if minutes > 0:
            duration_parts.append(f"{minutes} мин.")

        duration_str = " ".join(duration_parts) if duration_parts else "навсегда"

        response = (
            f"🔇 **Пользователь замучен**\n"
            f"👤 {user_to_mute.full_name}\n"
            f"⏰ Срок: {duration_str}\n"
            f"📝 Причина: {reason}"
        )
        await message.reply(response)

    except TelegramBadRequest as e:
        await message.reply(f"❌ Ошибка: {e}")

@dp.message(Command("unmute"))
async def cmd_unmute(message: types.Message):
    if not is_owner(message.from_user.id):
        await message.reply("❌ Только создатель бота может использовать эту команду")
        return

    if not message.reply_to_message:
        await message.reply("❌ Ответь на сообщение пользователя")
        return

    user_to_unmute = message.reply_to_message.from_user
    chat_id = message.chat.id

    try:
        permissions = ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False
        )

        await bot.restrict_chat_member(chat_id, user_to_unmute.id, permissions=permissions)
        await message.reply(f"🔊 {user_to_unmute.full_name} размучен")

    except TelegramBadRequest as e:
        await message.reply(f"❌ Ошибка: {e}")

@dp.message(Command("ban"))
async def cmd_ban(message: types.Message):
    if not is_owner(message.from_user.id):
        await message.reply("❌ Только создатель бота может использовать эту команду")
        return

    if not message.reply_to_message:
        await message.reply("❌ Ответь на сообщение пользователя")
        return

    user_to_ban = message.reply_to_message.from_user
    chat_id = message.chat.id

    if is_owner(user_to_ban.id):
        await message.reply("❌ Нельзя забанить создателя бота")
        return

    reason = "Без причины"
    args = message.text.split(maxsplit=1)
    if len(args) >= 2:
        reason = args[1]

    try:
        await bot.ban_chat_member(chat_id, user_to_ban.id)

        response = (
            f"🔨 **Пользователь забанен**\n"
            f"👤 {user_to_ban.full_name}\n"
            f"📝 Причина: {reason}"
        )
        await message.reply(response)

    except TelegramBadRequest as e:
        await message.reply(f"❌ Ошибка: {e}")

@dp.message(Command("unban"))
async def cmd_unban(message: types.Message):
    if not is_owner(message.from_user.id):
        await message.reply("❌ Только создатель бота может использовать эту команду")
        return

    if not message.reply_to_message:
        await message.reply("❌ Ответь на сообщение пользователя")
        return

    user_to_unban = message.reply_to_message.from_user
    chat_id = message.chat.id

    try:
        await bot.unban_chat_member(chat_id, user_to_unban.id)
        await message.reply(f"✅ {user_to_unban.full_name} разбанен")

    except TelegramBadRequest as e:
        await message.reply(f"❌ Ошибка: {e}")

@dp.message(Command("mute_list"))
async def cmd_mute_list(message: types.Message):
    if not is_owner(message.from_user.id):
        await message.reply("❌ Только создатель бота может использовать эту команду")
        return
    await message.reply("📋 Список замученных пока не реализован в этой версии.")

# ================ ПАРСЕР ВРЕМЕНИ ================
def parse_time(time_str):
    time_str = time_str.lower().strip()
    time_str = re.sub(r'(\d+)\s+([чмд])', r'\1\2', time_str)
    numbers = re.findall(r'\d+', time_str)
    if not numbers:
        return None
    num = int(numbers[0])
    if 'д' in time_str or 'дн' in time_str:
        return timedelta(days=num)
    elif 'ч' in time_str or 'час' in time_str:
        return timedelta(hours=num)
    elif 'м' in time_str or 'мин' in time_str:
        return timedelta(minutes=num)
    else:
        return timedelta(minutes=num)

# ================ WEBHOOK НАСТРОЙКИ ================
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL", "") + WEBHOOK_PATH

async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook установлен на {WEBHOOK_URL}")

async def on_shutdown():
    await bot.delete_webhook()
    conn.close()
    print("❌ Webhook удален, БД закрыта")

async def handle_webhook(request):
    update = await request.json()
    await dp.feed_update(bot, types.Update(**update))
    return web.Response(text="OK")

async def health_check(request):
    return web.Response(text="OK")

async def main():
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle_webhook)
    app.router.add_get("/health", health_check)
    app.router.add_get("/", lambda r: web.Response(text="Bot is running!"))

    app.on_startup.append(lambda _: asyncio.create_task(on_startup()))
    app.on_shutdown.append(lambda _: asyncio.create_task(on_shutdown()))

    port = int(os.environ.get("PORT", 8000))
    # ... остальной код
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🚀 Сервер запущен на порту {port}")

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())



