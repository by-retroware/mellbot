import os
import asyncio
import random
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ChatPermissions
from aiogram.exceptions import TelegramBadRequest
from aiohttp import web

TOKEN = "8558117158:AAG9MRnBKXqnTlWdPd_SxSM9JOfWyFAEwzw"

# ================ ТВОЙ ID ================
OWNER_ID = 5695593671  # твой ID

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
]

# ================ СЛОВАРИ ДЛЯ ПЕРЕВОДА ================
MURIN_CORE = {
    "ч", "т", "е", "м", "в",
    "друн", "друна", "друну", "друном", "друне", "друны", "друнов",
    "подруня", "подруни", "подруне", "подруню", "подруней", "подруням", "подрунями", "подрунях",
    "фог", "фога", "фогу", "фогом", "фоге",
    "гм", "гма", "гму", "гмом", "гме",
    "паг", "пага", "пагу", "пагом", "паге",
    "дм", "дма", "дму", "дмом", "дме",
    "ква", "квы", "кве", "кву", "квой",
    "члик", "члика", "члику", "чликом", "члике",
    "манстр", "манстра", "манстру", "манстром", "манстре",
}

WORD_TO_MURIN = {
    "друг": "друн", "друга": "друна", "другу": "друну", "другом": "друном", "друге": "друне",
    "друзья": "друны", "друзей": "друнов",
    "подруга": "подруня", "подруги": "подруни", "подруге": "подруне", "подругу": "подруню", "подругой": "подруней",
    "туман": "фог", "тумана": "фога", "туману": "фогу", "туманом": "фогом", "тумане": "фоге",
    "город": "гм", "города": "гма", "городу": "гму", "городом": "гмом", "городе": "гме",
    "парк": "паг", "парка": "пага", "парку": "пагу", "парком": "пагом", "парке": "паге",
    "дом": "дм", "дома": "дма", "дому": "дму", "домом": "дмом", "доме": "дме",
    "квартира": "ква", "квартиры": "квы", "квартире": "кве", "квартиру": "кву", "квартирой": "квой",
    "человек": "члик", "человека": "члика", "человеку": "члику", "человеком": "чликом", "человеке": "члике",
    "монстр": "манстр", "монстра": "манстру", "монстром": "манстром", "монстре": "манстре",
}

PRONOUNS = {
    "я": "ч", "меня": "меня", "мне": "мне", "мой": "мой", "моя": "моя", "моё": "моё", "мои": "мои",
    "ты": "т", "тебя": "тебя", "тебе": "тебе", "твой": "твой", "твоя": "твоя", "твоё": "твоё", "твои": "твои",
    "он": "е", "его": "его", "ему": "ему",
    "она": "е", "её": "её", "ей": "ей",
    "мы": "м", "нас": "нас", "нам": "нам",
    "вы": "в", "вас": "вас", "вам": "вам",
    "они": "е", "их": "их", "им": "им",
}

SKIP_WORDS = {
    "и", "в", "на", "с", "со", "у", "о", "об", "от", "до", "по", "под", "над",
    "для", "без", "через", "около", "возле", "мимо",
    "это", "этот", "эта", "это", "эти", "тот", "та", "то", "те",
    "который", "которая", "которое", "которые",
    "что", "чтобы", "как", "так", "такой", "такая", "такое", "такие",
    "когда", "где", "тут", "там", "сюда", "туда", "отсюда", "оттуда",
    "очень", "слишком", "совсем", "абсолютно", "просто",
    "бы", "ли", "же", "ведь", "даже", "уже", "ещё",
    "не", "ни", "нет", "да",
    "привет", "пока", "здравствуй", "здрасте", "спасибо", "пожалуйста",
    "хорошо", "плохо", "нормально", "круто", "классно", "супер",
    "сегодня", "завтра", "вчера", "сейчас", "потом", "позже", "раньше",
}

# ================ ФУНКЦИИ ПЕРЕВОДА ================
def add_ost(word):
    if word.lower() in SKIP_WORDS:
        return word
    if word.lower() in MURIN_CORE:
        return word
    if word.lower() in WORD_TO_MURIN:
        return WORD_TO_MURIN[word.lower()]
    if word.lower() in PRONOUNS:
        return PRONOUNS[word.lower()]
    if word and word[0].isupper() and word.lower() not in SKIP_WORDS:
        clean = word.strip(".,!?;:()\"'")
        if clean and clean[0].isupper():
            return word + "ость"
    noun_endings = ('а', 'я', 'о', 'е', 'и', 'ы', 'ь', 'й')
    if any(word.lower().endswith(ending) for ending in noun_endings):
        if len(word) > 3:
            return word + "ость"
    return word

def translate(text):
    words = text.split()
    result = []
    replace_count = min(random.randint(2, 3), len(words))
    replace_indices = random.sample(range(len(words)), replace_count) if words else []
    
    for i, word in enumerate(words):
        match = re.match(r"^(\W*)(\w+)(\W*)$", word)
        if match:
            prefix, clean, suffix = match.groups()
        else:
            prefix, clean, suffix = "", word, ""
        
        if i in replace_indices:
            new_word = add_ost(clean)
        else:
            new_word = clean
        
        if clean and clean[0].isupper() and new_word and new_word != clean:
            new_word = new_word[0].upper() + new_word[1:]
        
        result.append(prefix + new_word + suffix)
    
    return ' '.join(result)

# ================ СИСТЕМА МОДЕРАЦИИ ================
muted_users = {}
banned_users = {}

def is_admin(member):
    return member.status in ['creator', 'administrator']

def is_owner(user_id):
    return user_id == OWNER_ID

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

# ================ ИНИЦИАЛИЗАЦИЯ ================
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ================ КОМАНДА ДЛЯ УЗНАТЬ СВОЙ ID ================
@dp.message(Command("myid"))
async def cmd_myid(message: types.Message):
    await message.reply(f"🆔 Твой ID: `{message.from_user.id}`", parse_mode="Markdown")

# ================ КОМАНДА /HELP ================
@dp.message(Command("help", "start"))
async def cmd_help(message: types.Message):
    help_text = """
🤖 **Муринский бот — команды**

**Перевод:**
/mell [текст] — переводит на муринский язык

**Видео:**
/videos — список всех видео
/video [номер] — отправить видео по номеру
/randomvideo — случайное видео

**Модерация (только для владельца):**
/mute [время] [причина] — мут пользователя
/unmute — снять мут
/ban [причина] — бан пользователя
/unban — разбан
/mute_list — список замученных

**Другое:**
/myid — узнать свой Telegram ID
    """
    await message.reply(help_text, parse_mode="Markdown")

# ================ ВИДЕО КОМАНДЫ ================
@dp.message(Command("videos"))
async def cmd_videos(message: types.Message):
    if not VIDEO_LIBRARY:
        await message.reply("📭 Видео пока нет")
        return
    response = "🎬 **Список видео:**\n\n"
    for i, video in enumerate(VIDEO_LIBRARY, 1):
        response += f"{i}. {video['name']}\n"
    response += "\nОтправь `/video [номер]` чтобы получить видео"
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
        await message.reply(
            f"🎥 **{video['name']}**\n\n{video['url']}",
            disable_web_page_preview=False
        )
    except ValueError:
        await message.reply("❌ Номер должен быть числом")

@dp.message(Command("randomvideo"))
async def cmd_randomvideo(message: types.Message):
    if not VIDEO_LIBRARY:
        await message.reply("📭 Видео пока нет")
        return
    video = random.choice(VIDEO_LIBRARY)
    await message.reply(
        f"🎲 **Случайное видео:**\n🎥 **{video['name']}**\n\n{video['url']}",
        disable_web_page_preview=False
    )

# ================ КОМАНДЫ МУТА ================
@dp.message(Command("mute"))
async def cmd_mute(message: types.Message):
    if not is_owner(message.from_user.id):
        await message.reply("❌ Только создатель бота может использовать эту команду")
        return
    if not message.reply_to_message:
        await message.reply("❌ Ответь на сообщение пользователя")
        return
    user_to_mute = message.reply_to_message.from_user
    chat_id = message.chat.id
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
        if chat_id not in muted_users:
            muted_users[chat_id] = {}
        muted_users[chat_id][user_to_mute.id] = until_date.timestamp()
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
        if chat_id in muted_users and user_to_unmute.id in muted_users[chat_id]:
            del muted_users[chat_id][user_to_unmute.id]
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
        if chat_id not in banned_users:
            banned_users[chat_id] = {}
        banned_users[chat_id][user_to_ban.id] = True
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
        if chat_id in banned_users and user_to_unban.id in banned_users[chat_id]:
            del banned_users[chat_id][user_to_unban.id]
        await message.reply(f"✅ {user_to_unban.full_name} разбанен")
    except TelegramBadRequest as e:
        await message.reply(f"❌ Ошибка: {e}")

@dp.message(Command("mute_list"))
async def cmd_mute_list(message: types.Message):
    if not is_owner(message.from_user.id):
        await message.reply("❌ Только создатель бота может использовать эту команду")
        return
    chat_id = message.chat.id
    if chat_id not in muted_users or not muted_users[chat_id]:
        await message.reply("📋 Нет замученных пользователей")
        return
    response = "📋 **Замученные пользователи:**\n\n"
    now = datetime.now().timestamp()
    for user_id, until in list(muted_users[chat_id].items()):
        try:
            user = await bot.get_chat_member(chat_id, user_id)
            remaining = until - now
            if remaining > 0:
                hours = int(remaining // 3600)
                minutes = int((remaining % 3600) // 60)
                time_left = f"{hours}ч {minutes}м" if hours > 0 else f"{minutes}м"
                response += f"• {user.user.full_name}: осталось {time_left}\n"
            else:
                del muted_users[chat_id][user_id]
        except:
            response += f"• ID {user_id}: данные недоступны\n"
    await message.reply(response, parse_mode="Markdown")

# ================ КОМАНДА ПЕРЕВОДА ================
@dp.message(Command("mell"))
async def cmd_mell(message: types.Message):
    text = message.text[5:].strip()
    if not text:
        await message.reply("напиши текст после /mell")
        return
    translated = translate(text)
    await message.reply(translated)

# ================ WEBHOOK НАСТРОЙКИ ================
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL", "") + WEBHOOK_PATH

async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook установлен на {WEBHOOK_URL}")

async def on_shutdown():
    await bot.delete_webhook()
    print("❌ Webhook удален")

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
    
    app.on_startup.append(lambda _: asyncio.create_task(on_startup()))
    app.on_shutdown.append(lambda _: asyncio.create_task(on_shutdown()))
    
    port = int(os.environ.get("PORT", 8000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🚀 Сервер запущен на порту {port}")
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
