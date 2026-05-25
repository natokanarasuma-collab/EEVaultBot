import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import aiosqlite
import os
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

BOT_TOKEN = "8861332264:AAEaMLb_qcG0ouecTd9s2tXc3oegN6gvxtc"
GROUP_CHAT_ID = -10039546161335   # твой ID (поменяй если нужно)
ADMIN_ID = 6101234604

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = dp

DB_NAME = "bot.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                expiry_date TEXT
            )
        """)
        await db.commit()

async def is_subscribed(user_id: int) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT expiry_date FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row: return False
            return datetime.fromisoformat(row[0]) > datetime.now()

# Главное меню
def main_menu():
    kb = [
        [InlineKeyboardButton(text="🗡️ Оружие и билды", callback_data="cat_weapons")],
        [InlineKeyboardButton(text="🗺 Карты и локации", callback_data="cat_maps")],
        [InlineKeyboardButton(text="📖 Общие гайды", callback_data="cat_general")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.message(Command("start"))
async def start(message: types.Message):
    if not await is_subscribed(message.from_user.id):
        await message.answer("❌ Подписка истекла или не активирована.\nНапиши админу для продления.")
        return
    await message.answer("👋 Добро пожаловать в **EE Vault**!\nВыбирай раздел:", reply_markup=main_menu())

@router.message(Command("addsub"))
async def add_sub(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        _, username, days = message.text.split()
        days = int(days)
        user = await bot.get_chat(username.replace("@", ""))
        expiry = datetime.now() + timedelta(days=days)
        
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)",
                           (user.id, user.username, expiry.isoformat()))
            await db.commit()
        await message.answer(f"✅ Подписка на {days} дней активирована для {username}")
    except:
        await message.answer("Формат: /addsub @username 30")@router.message(Command("addme"))
async def add_me(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    days = 30
    expiry = datetime.now() + timedelta(days=days)
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)",
                       (message.from_user.id, message.from_user.username, expiry.isoformat()))
        await db.commit()
    await message.answer(f"✅ Подписка на {days} дней активирована для тебя")

# Авто-кик каждые 30 минут
async def check_expired():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            for (uid,) in await cursor.fetchall():
                if not await is_subscribed(uid):
                    try:
                        await bot.ban_chat_member(GROUP_CHAT_ID, uid)
                        await bot.unban_chat_member(GROUP_CHAT_ID, uid)
                    except:
                        pass

async def main():
    await init_db()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_expired, "interval", minutes=30)
    scheduler.start()
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
