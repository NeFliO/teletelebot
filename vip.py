import json
import asyncio
import os
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.formatting import Text
from aiogram.utils.markdown import hbold
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram import F

# Load token and channel IDs from environment variables
TOKEN = os.getenv("TOKEN")
CHANNEL_VIP_MAIN = int(os.getenv("CHANNEL_VIP_MAIN"))
CHANNEL_VIP_LITE = int(os.getenv("CHANNEL_VIP_LITE"))
ADMIN_ID = 1106693795

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# === CONNECT TO SQLITE DATABASE ===
import sqlite3

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

# Create users table if it doesn't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)
""")
conn.commit()

# Load tariffs
with open("tariffs.json", "r", encoding="utf-8") as f:
    TARIFFS = json.load(f)

# Load subscriptions
def load_subs():
    try:
        with open("subs.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_subs(subs):
    with open("subs.json", "w", encoding="utf-8") as f:
        json.dump(subs, f, ensure_ascii=False, indent=2)

def save_user(user: types.User):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user.id,))
    conn.commit()

# Find user by ID
def get_user_subs(user_id):
    subs = load_subs()
    for user in subs:
        if user["user_id"] == user_id:
            return user
    return None

# Add or update user's subscription
def add_subscription(user_id, tariff_id):
    subs = load_subs()
    tariff = next((t for t in TARIFFS if t["id"] == tariff_id), None)
    if not tariff:
        return  # Or handle error if tariff is not found

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

# Subscription checker
def is_subscription_active(user_id, tariff_id):
    user = get_user_subs(user_id)
    if not user:
        return False
    now = datetime.now()
    for t in user["tariffs"]:
        if t["id"] == tariff_id and datetime.fromisoformat(t["expires_at"]) > now:
            return True
    return False

# Autokick expired users
async def auto_kick():
    while True:
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
                            print(f"[KICK] User {user['user_id']} was kicked from channel {tariff['channel_id']} due to expired tariff {t['id']}")
                        except TelegramBadRequest as e:
                            print(f"[ERROR] Failed to kick user {user['user_id']}: {e}")

            user["tariffs"] = active_tariffs

        save_subs(subs)
        await asyncio.sleep(3600)

# Persistent reply buttons
reply_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="💳 Тарифы"), KeyboardButton(text="⏳ Моя подписка")],
], resize_keyboard=True)

@dp.message(CommandStart())
async def start(message: types.Message):
    save_user(message.from_user)  # NEW: save user
    await message.answer("Привет! Выберите действие ниже:", reply_markup=reply_kb)

@dp.message(F.text == "💳 Тарифы")
async def tariffs_menu(message: types.Message):
    builder = InlineKeyboardBuilder()
    for t in TARIFFS:
        builder.button(text=t["name"], callback_data=f"tariff_{t['id']}")
    await message.answer("Выберите тариф:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("tariff_"))
async def show_tariff(call: types.CallbackQuery):
    tariff_id = call.data.split("_")[1]
    tariff = next((t for t in TARIFFS if t["id"] == tariff_id), None)
    if not tariff:
        return

    # Кнопка оплаты и назад
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Оплата", callback_data=f"pay_{tariff_id}")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_tariffs")]
    ])
    await call.message.edit_text(tariff["description"], reply_markup=markup)

@dp.callback_query(F.data == "back_to_tariffs")
async def back_to_tariffs(call: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    for t in TARIFFS:
        builder.button(text=t["name"], callback_data=f"tariff_{t['id']}")
    await call.message.edit_text("Выберите тариф:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("pay_"))
async def show_payment_options(call: types.CallbackQuery):
    tariff_id = call.data.split("_")[1]
    tariff = next((t for t in TARIFFS if t["id"] == tariff_id), None)
    if not tariff:
        return

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Сбербанк", callback_data=f"sber_{tariff_id}")],
        [InlineKeyboardButton(text="СБП", callback_data=f"sbp_{tariff_id}")],
        [InlineKeyboardButton(text="Назад", callback_data=f"tariff_{tariff_id}")]
    ])
    await call.message.edit_text(f"Выберите способ оплаты для тарифа {tariff['name']}:", reply_markup=markup)
    
@dp.callback_query(F.data.startswith("sber_"))
async def pay_sber(call: types.CallbackQuery):
    tariff_id = call.data.split("_")[1]
    tariff = next((t for t in TARIFFS if t["id"] == tariff_id), None)
    if not tariff:
        return

    text = (
        f"<b>Способ оплаты: Сбербанк</b>\n"
        f"К оплате: {tariff['price']:.2f} 🇷🇺RUB\n\n"
        f"<b>Реквизиты для оплаты:</b>\n\n"
        f"Отправьте точную сумму в соответствии с тарифом, далее отправьте скриншот оплаты с чеком администрации канала: @bloodtrials или @deathwithoutregret\n\n"
        f"<b>Сбербанк по номеру карты:</b>\n"
        f"Получатель: Андрей С.\n\n"
        f"<code>2202206392411927</code>\n"
        f"__________________________\n"
        f"Вы платите физическому лицу.\n"
        f"Деньги поступят на счёт получателя."
    )

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data=f"pay_{tariff_id}")]
    ])
    await call.message.edit_text(text, reply_markup=markup)
    
@dp.callback_query(F.data.startswith("sbp_"))
async def pay_sbp(call: types.CallbackQuery):
    tariff_id = call.data.split("_")[1]
    tariff = next((t for t in TARIFFS if t["id"] == tariff_id), None)
    if not tariff:
        return

    text = (
        f"<b>Способ оплаты: СБП (Сбербанк)</b>\n"
        f"К оплате: {tariff['price']:.2f} 🇷🇺RUB\n\n"
        f"<b>Реквизиты для оплаты:</b>\n\n"
        f"Отправьте точную сумму в соответствии с тарифом, далее отправьте скриншот оплаты с чеком администрации канала: @bloodtrials или @deathwithoutregret\n\n"
        f"<b>СПБ по номеру (ТОЛЬКО на Сбербанк!):</b>\n"
        f"<code>+79610605986</code> (Андрей С.)\n"
        f"__________________________\n"
        f"Вы платите физическому лицу.\n"
        f"Деньги поступят на счёт получателя."
    )

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data=f"pay_{tariff_id}")]
    ])
    await call.message.edit_text(text, reply_markup=markup)

@dp.message(F.text == "⏳ Моя подписка")
async def my_subscription(message: types.Message):
    user = get_user_subs(message.from_user.id)
    if not user or not user["tariffs"]:
        await message.answer("У вас нет активной подписки.", reply_markup=reply_kb)
        return
    lines = []
    now = datetime.now()
    for t in user["tariffs"]:
        exp = datetime.fromisoformat(t["expires_at"])
        left = exp - now
        lines.append(f"Тариф {t['id']} — до {exp.strftime('%Y-%m-%d %H:%M:%S')} (осталось {left.days} дн.)")
    await message.answer("\n".join(lines), reply_markup=reply_kb)

@dp.message(F.text.startswith("/broadcast"))
async def broadcast_message(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return  # Ignore if not admin

    # Get the message to broadcast (after the command)
    text = message.text[len("/broadcast"):].strip()
    if not text:
        await message.answer("Пожалуйста, добавьте текст после команды /broadcast.")
        return

    # Send message to all users in DB
    cursor.execute("SELECT user_id FROM users")
    user_ids = cursor.fetchall()
    sent = 0
    failed = 0

    for (user_id,) in user_ids:
        try:
            await bot.send_message(user_id, text)
            sent += 1
            await asyncio.sleep(0.05)  # Avoid flooding
        except:
            failed += 1

    await message.answer(f"✅ Рассылка завершена\nОтправлено: {sent}\nНе удалось: {failed}")

async def main():
    asyncio.create_task(auto_kick())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
