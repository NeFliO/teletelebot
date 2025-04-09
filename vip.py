import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from aiogram.filters import Command

TOKEN = "7668643270:AAEjxp0JKx_4A7KwqegRrzXWvFh1kty5Bkk"  # Replace with your actual token

logging.basicConfig(level=logging.INFO)
from aiogram.client.default import DefaultBotProperties
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# Tariffs
tariffs = {
    "tariff1": ("#1", "250"),
    "tariff2": ("#2", "400"),
    "tariff3": ("#3", "600"),
    "tariff4": ("Лайт", "200")
}

# Start
@dp.message(Command("start"))
async def start_handler(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Тариф #1", callback_data="tariff1")],
        [InlineKeyboardButton(text="Тариф #2", callback_data="tariff2")],
        [InlineKeyboardButton(text="Тариф #3", callback_data="tariff3")],
        [InlineKeyboardButton(text="Тариф Лайт", callback_data="tariff4")]
    ])
    await message.answer(
        "❤️‍🔥Приветсвуем Вас в ВПИСКА! Здесь вы можете приобрести VIP доступ к нашей группе с лучшими сливами шкур со всей территории России.❤️‍🔥\n\nЧтобы выбрать подходящий Вам тариф, нажмите на соответствующую кнопку ниже ↓",
        reply_markup=kb
    )

# Tariff Info Page
@dp.callback_query(F.data.startswith("tariff"))
async def show_tariff(query: CallbackQuery):
    key = query.data
    title, price = tariffs[key]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Оплатить", callback_data=f"pay_{key}")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_main")]
    ])
    text = f"""Тариф: {title}
Стоимость: {price}.00 RUB
Срок действия: 1 месяц

Вы получите доступ к следующим ресурсам:
• Вписка | VIP (канал)

После Оплаты ты Получишь доступ в вписка | VIP в котором:
Ежедневные сливы
Безграничное количество контента (18+)
(Видео и Вложения пополняются)
"""
    await query.message.edit_text(text, reply_markup=kb)

# Payment Methods
@dp.callback_query(F.data.startswith("pay_tariff"))
async def pay_options(query: CallbackQuery):
    key = query.data.replace("pay_", "")
    title, price = tariffs[key]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Сбербанк", callback_data=f"sber_{key}")],
        [InlineKeyboardButton(text="Криптовалюты (USDT TRC 20)", callback_data=f"crypto_{key}")],
        [InlineKeyboardButton(text="СБП", callback_data=f"sbp_{key}")],
        [InlineKeyboardButton(text="Назад", callback_data=key)]
    ])
    text = f"""Тариф: вписка | VIP {title}
Стоимость: {price}.00 RUB
Срок действия: 1 месяц

Выберите способ оплаты:"""
    await query.message.edit_text(text, reply_markup=kb)

# Payment Details
@dp.callback_query(F.data.startswith(("sber_", "crypto_", "sbp_")))
async def payment_details(query: CallbackQuery):
    method, key = query.data.split("_", 1)
    title, price = tariffs[key]

    if method == "sber":
        text = f"""Способ оплаты: Сбербанк
К оплате: {price}.00 RUB

Реквизиты для оплаты:

Отправь точную Сумму в соответствии с тарифом, далее отправь скриншот оплаты нашей администрации - @bloodtrials / @deathwithoutregret
После проверки, вы будете добавлены в вписка | VIP в соответствии с вашим тарифом.
Сбербанк: 732749812399 Эдик

__________________________
Вы платите физическому лицу.
Деньги поступят на счёт получателя."""
    elif method == "crypto":
        text = f"""Способ оплаты: Криптой (USDT TRC 20)
К оплате: {price}.00 RUB

Реквизиты для оплаты:

Отправь точную Сумму в соответствии с тарифом, далее отправь скриншот оплаты нашей администрации - @bloodtrials / @deathwithoutregret
После проверки, вы будете добавлены в вписка | VIP в соответствии с вашим тарифом.

Адрес: THtGWgQCeZFrQLnDnVjb5MeZAzZecVU8BQ

__________________________
Вы платите физическому лицу.
Деньги поступят на счёт получателя."""
    else:
        text = f"""Способ оплаты: СБП (Сбер)
К оплате: {price}.00 RUB

Реквизиты для оплаты:

Отправь точную Сумму в соответствии с тарифом, далее отправь скриншот оплаты нашей администрации - @bloodtrials / @deathwithoutregret
СБП (только сбербанк): +823752398239 Эд

__________________________
Вы платите физическому лицу.
Деньги поступят на счёт получателя."""

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data=f"pay_tariff{key}")]
    ])
    await query.message.edit_text(text, reply_markup=kb)

# Back to Start
@dp.callback_query(F.data == "back_to_main")
async def back_to_main(query: CallbackQuery):
    await start_handler(query.message)

# Run Bot
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
