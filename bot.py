import os
import asyncio
import random
import re
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Update
from aiohttp import web

TOKEN = "8558117158:AAG9MRnBKXqnTlWdPd_SxSM9JOfWyFAEwzw"
WEBHOOK_PATH = f"/webhook/{TOKEN}"  # Путь для вебхука
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL", "") + WEBHOOK_PATH  # Render сам подставит URL

# Коренные муринские слова
MURIN_CORE = {"ч", "т", "е", "м", "в", "друн", "подруня", "фог", "гм", "паг", "дм", "ква", "члик", "манстр"}

# Словарь замен
WORD_TO_MURIN = {
    "друг": "друн", "друга": "друна", "другу": "друну", "другом": "друном", "друге": "друне",
    "подруга": "подруня", "подруги": "подруни", "подруге": "подруне", "подругу": "подруню", "подругой": "подруней",
    "туман": "фог", "тумана": "фога", "туману": "фогу", "туманом": "фогом", "тумане": "фоге",
    "город": "гм", "города": "гма", "городу": "гму", "городом": "гмом", "городе": "гме",
    "парк": "паг", "парка": "пага", "парку": "пагу", "парком": "пагом", "парке": "паге",
    "дом": "дм", "дома": "дма", "дому": "дму", "домом": "дмом", "доме": "дме",
    "квартира": "ква", "квартиры": "квы", "квартире": "кве", "квартиру": "кву", "квартирой": "квой",
    "человек": "члик", "человека": "члика", "человеку": "члику", "человеком": "чликом", "человеке": "члике",
    "монстр": "манстр", "монстра": "манстра", "монстру": "манстру", "монстром": "манстром", "монстре": "манстре",
}

PRONOUNS = {"я": "ч", "ты": "т", "он": "е", "она": "е", "мы": "м", "вы": "в", "они": "е"}

def add_ost(word):
    if word.lower() in MURIN_CORE or word.lower() in WORD_TO_MURIN or word.lower() in PRONOUNS:
        return word
    return word + "ость"

def translate(text):
    words = text.split()
    result = []
    replace_count = min(random.randint(2, 3), len(words))
    replace_indices = random.sample(range(len(words)), replace_count)
    
    for i, word in enumerate(words):
        match = re.match(r"^(\W*)(\w+)(\W*)$", word)
        if match:
            prefix, clean, suffix = match.groups()
        else:
            prefix, clean, suffix = "", word, ""
        
        clean_lower = clean.lower()
        
        if clean_lower in PRONOUNS:
            new = PRONOUNS[clean_lower]
        elif clean_lower in WORD_TO_MURIN:
            new = WORD_TO_MURIN[clean_lower]
        elif i in replace_indices:
            new = add_ost(clean)
        else:
            new = clean
        
        if clean and clean[0].isupper() and new:
            new = new[0].upper() + new[1:]
        
        result.append(prefix + new + suffix)
    
    return ' '.join(result)

# Инициализация бота
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("mell"))
async def cmd_mell(message: types.Message):
    text = message.text[5:].strip()
    if not text:
        await message.reply("напиши текст")
        return
    await message.reply(translate(text))

# Обработчик вебхуков
async def handle_webhook(request: web.Request) -> web.Response:
    """Принимаем обновления от Telegram"""
    update = await request.json()
    await dp.feed_update(bot, Update(**update))
    return web.Response(text="OK", status=200)

# Проверка здоровья (Render требует endpoint)
async def health_check(request: web.Request) -> web.Response:
    return web.Response(text="OK", status=200)

async def main():
    # Устанавливаем вебхук
    await bot.set_webhook(WEBHOOK_URL)
    print(f"Webhook установлен на {WEBHOOK_URL}")
    
    # Создаем aiohttp приложение
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle_webhook)
    app.router.add_get("/health", health_check)
    
    # Запускаем сервер
    port = int(os.environ.get("PORT", 8000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Сервер запущен на порту {port}")
    
    # Держим сервер запущенным
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())