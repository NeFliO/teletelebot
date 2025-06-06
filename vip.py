import json
import asyncio
import os
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramAPIError
from aiogram.filters import CommandStart

# === Load environment variables ===
TOKEN = os.getenv("TOKEN")
CHANNEL_VIP_MAIN = os.getenv("CHANNEL_VIP_MAIN")
CHANNEL_VIP_LITE = os.getenv("CHANNEL_VIP_LITE")
ADMIN_ID = 1106693795

# === Validate environment variables ===
if not TOKEN:
    raise ValueError("TOKEN environment variable is missing!")
if not CHANNEL_VIP_MAIN or not CHANNEL_VIP_LITE:
    raise ValueError("CHANNEL_VIP_MAIN or CHANNEL_VIP_LITE environment variables are missing!")

CHANNEL_VIP_MAIN = int(CHANNEL_VIP_MAIN)
CHANNEL_VIP_LITE = int(CHANNEL_VIP_LITE)

# === Setup bot and dispatcher ===
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# === Connect to SQLite database ===
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    registered_at TEXT,
    promo_active INTEGER DEFAULT 0
)
""")
conn.commit()

# === Load tariffs ===
try:
    with open("tariffs.json", "r", encoding="utf-8") as f:
        TARIFFS = json.load(f)
except FileNotFoundError:
    print("[ERROR] tariffs.json not found!")
    TARIFFS = []

# === Load/Save subs ===
def load_subs():
    try:
        with open("subs.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_subs(subs):
    with open("subs.json", "w", encoding="utf-8") as f:
        json.dump(subs, f, ensure_ascii=False, indent=2)

# === User operations ===
def save_user(user: types.User):
    cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, registered_at, promo_active)
        VALUES (?, ?, ?, ?, ?, 0)
    """, (
        user.id,
        user.username,
        user.first_name,
        user.last_name,
        datetime.now().isoformat()
    ))
    conn.commit()

def is_promo_active(user_id):
    cursor.execute("SELECT promo_active FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row and row[0] == 1

def activate_promo(user_id):
    cursor.execute("UPDATE users SET promo_active = 1 WHERE user_id = ?", (user_id,))
    conn.commit()

# === Subscription management ===
def get_user_subs(user_id):
    subs = load_subs()
    for user in subs:
        if user["user_id"] == user_id:
            return user
    return None

def add_subscription(user_id, tariff_id):
    subs = load_subs()
    tariff = next((t for t in TARIFFS if t["id"] == tariff_id), None)
    if not tariff:
        return

    expires_at = (datetime.now() + timedelta(days=tariff["duration_days"])).isoformat()
    found = False

    for user in subs:
        if user["user_id"] == user_id:
            for t in user["tariffs"]:
                if t["id"] == tariff_id:
                    t["expires_at"] = expires_at
                    found = True
                    break
            if not found:
                user["tariffs"].append({"id": tariff_id, "expires_at": expires_at})
            break
    else:
        subs.append({"user_id": user_id, "tariffs": [{"id": tariff_id, "expires_at": expires_at}]})

    save_subs(subs)

def is_subscription_active(user_id, tariff_id):
    user = get_user_subs(user_id)
    if not user:
        return False
    now = datetime.now()
    for t in user["tariffs"]:
        if t["id"] == tariff_id and datetime.fromisoformat(t["expires_at"]) > now:
            return True
    return False

# === Auto kick expired users ===
async def auto_kick():
    while True:
        try:
            now = datetime.now()
            subs = load_subs()

            for user in subs:
                active_tariffs = []

                for t in user["tariffs"]:
                    exp_date = datetime.fromisoformat(t["expires_at"])
                    if exp_date > now:
                        active_tariffs.append(t)
                    else:
                        tariff = next((tar for tar in TARIFFS if tar["id"] == t["id"]), None)
                        if tariff:
                            try:
                                await bot.ban_chat_member(tariff["channel_id"], user["user_id"])
                                await bot.unban_chat_member(tariff["channel_id"], user["user_id"])
                                print(f"[KICK] User {user['user_id']} kicked from {tariff['channel_id']}")
                            except TelegramBadRequest as e:
                                print(f"[KICK ERROR] {e}")

                user["tariffs"] = active_tariffs

            save_subs(subs)
            await asyncio.sleep(3600)
        except Exception as e:
            print(f"[AUTO_KICK ERROR] {e}")

# === Reply keyboard ===
reply_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="💳 Тарифы"), KeyboardButton(text="⏳ Моя подписка")],
], resize_keyboard=True)

# === Command handlers ===
@dp.message(CommandStart())
async def start(message: types.Message):
    print(f"[START] from {message.from_user.id}")
    save_user(message.from_user)
    try:
        await message.answer("Привет! Выберите действие ниже:", reply_markup=reply_kb)

        promo_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Активировать промокод", callback_data="activate_promo")]
        ])
        await message.answer("🎁 <b>ПРОМОКОД НА 20% СКИДКУ НА ВСЕ ТАРИФЫ</b>", reply_markup=promo_kb)

    except Exception as e:
        print(f"[ERROR] start(): {e}")

# === Main runner ===
async def main():
    print("[BOOT] Starting bot...")
    print(f"[ENV] TOKEN: {'set' if TOKEN else 'missing'}")
    print(f"[ENV] CHANNEL_VIP_MAIN: {CHANNEL_VIP_MAIN}, CHANNEL_VIP_LITE: {CHANNEL_VIP_LITE}")

    asyncio.create_task(auto_kick())

    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"[FATAL] Polling failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
