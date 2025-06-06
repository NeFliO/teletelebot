import json
import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import CommandStart
from aiogram import Router

# === Load environment variables ===
TOKEN = os.getenv("TOKEN")
CHANNEL_VIP_MAIN = os.getenv("CHANNEL_VIP_MAIN")
CHANNEL_VIP_LITE = os.getenv("CHANNEL_VIP_LITE")

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
router = Router()

# === Load tariffs ===
try:
    with open("tariffs.json", "r", encoding="utf-8") as f:
        TARIFFS = json.load(f)
except FileNotFoundError:
    print("[ERROR] tariffs.json not found!")
    TARIFFS = []

# === Reply keyboard ===
reply_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="💳 Тарифы"), KeyboardButton(text="⏳ Моя подписка")],
], resize_keyboard=True)

# === Command handlers ===
@router.message(CommandStart())
async def start(message: types.Message):
    await message.answer("Привет! Выберите действие ниже:", reply_markup=reply_kb)

    promo_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Активировать промокод", callback_data="activate_promo")]
    ])
    await message.answer("🎁 <b>ПРОМОКОД НА 20% СКИДКУ НА ВСЕ ТАРИФЫ</b>", reply_markup=promo_kb)

@router.callback_query(F.data == "activate_promo")
async def handle_activate_promo(call: types.CallbackQuery):
    await call.message.edit_text("✅ Промокод был успешно активирован (фиктивно).")

@router.message(F.text == "💳 Тарифы")
async def tariffs_menu(message: types.Message):
    builder = InlineKeyboardBuilder()
    for t in TARIFFS:
        builder.button(text=t["name"], callback_data=f"tariff_{t['id']}")
    await message.answer("Выберите тариф:", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("tariff_"))
async def show_tariff(call: types.CallbackQuery):
    tariff_id = call.data.split("_")[1]
    tariff = next((t for t in TARIFFS if t["id"] == tariff_id), None)
    if not tariff:
        return

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Оплата", callback_data=f"pay_{tariff_id}")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_tariffs")]
    ])
    await call.message.edit_text(tariff["description"], reply_markup=markup)

@router.callback_query(F.data == "back_to_tariffs")
async def back_to_tariffs(call: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    for t in TARIFFS:
        builder.button(text=t["name"], callback_data=f"tariff_{t['id']}")
    await call.message.edit_text("Выберите тариф:", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("pay_"))
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

@router.callback_query(F.data.startswith("sber_"))
async def pay_sber(call: types.CallbackQuery):
    tariff_id = call.data.split("_")[1]
    tariff = next((t for t in TARIFFS if t["id"] == tariff_id), None)
    if not tariff:
        return

    price = tariff["price"]
    text = (
        f"<b>Способ оплаты: Сбербанк</b>\n"
        f"К оплате: {price:.2f} 🇷🇺RUB\n\n"
        f"<b>Реквизиты для оплаты:</b>\n\n"
        f"Отправьте точную сумму в соответствии с тарифом, далее отправьте скриншот оплаты с чеком администрации канала.\n\n"
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

@router.callback_query(F.data.startswith("sbp_"))
async def pay_sbp(call: types.CallbackQuery):
    tariff_id = call.data.split("_")[1]
    tariff = next((t for t in TARIFFS if t["id"] == tariff_id), None)
    if not tariff:
        return

    price = tariff["price"]
    text = (
        f"<b>Способ оплаты: СБП (Сбербанк)</b>\n"
        f"К оплате: {price:.2f} 🇷🇺RUB\n\n"
        f"<b>Реквизиты для оплаты:</b>\n\n"
        f"Отправьте точную сумму в соответствии с тарифом, далее отправьте скриншот оплаты с чеком администрации канала.\n\n"
        f"<b>СПБ по номеру:</b>\n"
        f"<code>+79610605986</code> (Андрей С.)\n"
        f"__________________________\n"
        f"Вы платите физическому лицу.\n"
        f"Деньги поступят на счёт получателя."
    )

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data=f"pay_{tariff_id}")]
    ])
    await call.message.edit_text(text, reply_markup=markup)

@router.message(F.text == "⏳ Моя подписка")
async def my_subscription(message: types.Message):
    await message.answer("Подписки временно отключены (база данных убрана).", reply_markup=reply_kb)

# === Main runner ===
async def main():
    print("[BOOT] Starting bot...")
    dp.include_router(router)
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"[FATAL] Polling failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
