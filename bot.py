import os
import asyncio
import logging
import re
from datetime import datetime
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import *



logs_dir = os.path.join(bot_dir, "logs")
os.makedirs(logs_dir, exist_ok=True)
log = os.path.join(logs_dir, "bot.log")

logging.basicConfig(
    filename=log,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
bot = Bot(token=token)
dp = Dispatcher()
user_activity = {}

def filter_content(text: str) -> str:
    if not words_filter:
        return text
    for banned, synonym in WORDS.items():
        pattern = re.compile(r'\b' + re.escape(banned) + r'\b', re.IGNORECASE)
        text = pattern.sub(synonym, text)
    return text

def format_reply_text(message: types.Message) -> str:
    if not message.reply_to_message or not message.reply_to_message.text:
        return ""
    
    parent_text = message.reply_to_message.text.strip()
    if parent_text.startswith("В ответ на:"):
        parts = parent_text.split("\n", 1)
        if len(parts) == 2:
            parent_text = parts[1].strip()
        else:
            parent_text = ""
    return f"В ответ на: {parent_text}\n"

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    subscribe_button = InlineKeyboardButton(text="Подписаться", callback_data="subscribe")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[subscribe_button]])
    await message.reply(
        "Привествую падаван!\nпозволь рассказат тебе что это за бот и что ты можешь тут делать)\nэто - свобода, чувствуешь ее?\nв этом чате ты можешь писать что хочешь и оставаться абсолютно анонимным, позволь себе глатнуть свежего воздуха, выскажи другим все, что так долго копил в себе\nНо не забывай!\nпорой люди в интернете могут иметь злые намерение и подписавшись на бота ты всю ответсвенность берешь только на себя\nУ бота есть система антиспама, больше 3 сообщений в секунду и ты в бане\nЧто здесь можно делать?\nздесь ты можешь писать что хочешь, однако некоторые твои маты будут заменяться синонимами\nты можешь отвечать на сообщение\nоднако у нас не работают медия и стикеры((\nЖелаю хорошо провести время и удачи в начинаниях!!",
        reply_markup=keyboard,
    )
    username = message.from_user.username or ""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (telegram_id, username, warnings, banned_until) VALUES (?, ?, 0, NULL)",
            (message.from_user.id, username),
        )
        await db.commit()

@dp.callback_query(lambda callback_query: callback_query.data == "subscribe")
async def process_subscribe(callback_query: types.CallbackQuery):
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE users SET warnings = 0, banned_until = NULL WHERE telegram_id = ?",
            (callback_query.from_user.id,),
        )
        await db.commit()
    await bot.answer_callback_query(callback_query.id, text="Вы подписались!")
    await bot.send_message(callback_query.from_user.id, "Ты успешно зашел в чат, теперь приятного общения тебе))")

@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    current_time = datetime.now().timestamp()
    if user_id not in user_activity:
        user_activity[user_id] = []
    user_activity[user_id] = [t for t in user_activity[user_id] if current_time - t < 1]
    user_activity[user_id].append(current_time)
    if len(user_activity[user_id]) > limit:
        async with aiosqlite.connect(db_path) as db:
            async with db.execute("SELECT warnings FROM users WHERE telegram_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                warnings = row[0] if row else 0
            warnings += 1
            if warnings >= 3:
                banned_until = datetime.now().timestamp() + ban_time
                await db.execute("UPDATE users SET warnings = ?, banned_until = ? WHERE telegram_id = ?", (warnings, banned_until, user_id),)
                await db.commit()
                await message.reply(f"Вы были забанены на {ban_time} секунд за спам.")
                logging.info(f"Пользователь {user_id} забанен за спам.")
                asyncio.create_task(unban_user(user_id))
                return
            else:
                await db.execute(
                    "UPDATE users SET warnings = ? WHERE telegram_id = ?",
                    (warnings, user_id),
                )
                await db.commit()
                await message.reply(f"Предупреждение {warnings}/3: Пожалуйста, не спамьте.")
                logging.info(f"Пользователь {user_id} получил предупреждение {warnings}.")
        return
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT banned_until FROM users WHERE telegram_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0] is not None and float(row[0]) > datetime.now().timestamp():
                await message.reply("Вы временно забанены.")
                return

    reply_prefix = format_reply_text(message)
    original_text = reply_prefix + message.text
    processed_text = filter_content(original_text)

    async with aiosqlite.connect(db_path) as db:
        current_timestamp = datetime.now().timestamp()
        async with db.execute(
            "SELECT telegram_id FROM users WHERE banned_until IS NULL OR banned_until <= ?",
            (current_timestamp,),
        ) as cursor:
            users = await cursor.fetchall()
    for (tg_id,) in users:
        if tg_id != user_id:
            try:
                await bot.send_message(tg_id, processed_text)
            except Exception as e:
                logging.error(f"Ошибка при отправке сообщения пользователю {tg_id}: {e}")

async def unban_user(user_id: int):
    await asyncio.sleep(ban_time)
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE users SET warnings = 0, banned_until = NULL WHERE telegram_id = ?",
            (user_id,),
        )
        await db.commit()
    try:
        await bot.send_message(user_id, "Вы были разбанены. Пожалуйста, соблюдайте правила.")
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения о разбане пользователю {user_id}: {e}")
    logging.info(f"Пользователь {user_id} разбанен.")
async def main():
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
