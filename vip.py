import json
import asyncio
import os
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
TOKEN = os.getenv("7668643270:AAEjxp0JKx_4A7KwqegRrzXWvFh1kty5Bkk")
CHANNEL_VIP_MAIN = int(os.getenv("CHANNEL_VIP_MAIN"))
CHANNEL_VIP_LITE = int(os.getenv("CHANNEL_VIP_LITE"))

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

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
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="back_to_tariffs")]
    ])
    await call.message.edit_text(tariff["description"], reply_markup=markup)

@dp.callback_query(F.data == "back_to_tariffs")
async def back_to_tariffs(call: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    for t in TARIFFS:
        builder.button(text=t["name"], callback_data=f"tariff_{t['id']}")
    await call.message.edit_text("Выберите тариф:", reply_markup=builder.as_markup())

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

async def main():
    asyncio.create_task(auto_kick())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
