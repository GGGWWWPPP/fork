from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, PreCheckoutQuery, Message, LabeledPrice
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards.inline import periods_keyboard, users_keyboard, payment_methods_keyboard, main_menu, help_os_keyboard
from database.db import AsyncSessionLocal
from database.models import User, Subscription
from sqlalchemy import select
from services.marzban import MarzbanAPI
from services.platega import PlategaAPI
from services.cryptobot import CryptoBotAPI
from contextlib import suppress
from aiogram.exceptions import TelegramBadRequest
import time
import re
import logging

logger = logging.getLogger(__name__)

router = Router()
marzban = MarzbanAPI()
platega = PlategaAPI()
cryptobot = CryptoBotAPI()


class PaymentStates(StatesGroup):
    waiting_for_email = State()


# ==================== Выбор тарифа ====================

@router.callback_query(F.data == "buy_sub")
async def buy_sub(callback: CallbackQuery):
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            "💎 <b>Купить подписку</b>\n\n"
            "Выберите срок действия защиты:",
            reply_markup=periods_keyboard(action="buy", sub_id=0),
            parse_mode="HTML"
        )
    await callback.answer()

@router.callback_query(F.data.startswith("extend_"))
async def extend_sub(callback: CallbackQuery):
    sub_id = int(callback.data.split("_")[1])
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            "💎 <b>Продлить подписку</b>\n\n"
            "Выберите срок действия защиты:",
            reply_markup=periods_keyboard(action="extend", sub_id=sub_id),
            parse_mode="HTML"
        )
    await callback.answer()

@router.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    with suppress(TelegramBadRequest):
        await callback.message.edit_text("🛡 <b>Главное меню</b>", reply_markup=main_menu(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("period_"))
async def choose_users(callback: CallbackQuery):
    parts = callback.data.split("_")
    action = parts[1]
    sub_id = int(parts[2])
    days = int(parts[3])
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            f"⏳ <b>Защита на {days} Дней</b>\n\n"
            "Выберите ограничение по количеству устройств:",
            reply_markup=users_keyboard(action, sub_id, days),
            parse_mode="HTML"
        )
    await callback.answer()

@router.callback_query(F.data.startswith("tariff_"))
async def choose_payment(callback: CallbackQuery):
    parts = callback.data.split("_")
    action = parts[1]
    sub_id = int(parts[2])
    days = int(parts[3])
    users = int(parts[4])
    price = int(parts[5])
    
    if users == 1:
        user_text = "1 устройство"
    elif users in [2, 3, 4]:
        user_text = f"{users} устройства"
    elif users == 999:
        user_text = "Безлимит устройств"
    else:
        user_text = f"{users} устройств"
    
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            f"💳 <b>Оплата</b>\n\n"
            f"Тариф: {days} Дней, {user_text}\n"
            f"Сумма: {price} ₽\n\n"
            "Выберите удобный способ оплаты:",
            reply_markup=payment_methods_keyboard(action, sub_id, days, users, price),
            parse_mode="HTML"
        )
    await callback.answer()


# ==================== Email проверка ====================

def validate_email(email: str) -> bool:
    """Простая валидация email."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))


async def get_user_email(user_id: int) -> str | None:
    """Получить email пользователя из БД."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        return user.email if user else None


async def save_user_email(user_id: int, email: str):
    """Сохранить email пользователя в БД."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.email = email.strip().lower()
            await session.commit()


# ==================== Обработка оплаты (с проверкой email) ====================

@router.callback_query(F.data.startswith("pay_platega_"))
async def pay_platega_handler(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    action = parts[2]
    sub_id = int(parts[3])
    days = int(parts[4])
    users = int(parts[5])
    price = int(parts[6])
    
    email = await get_user_email(callback.from_user.id)
    
    if email:
        # Email уже есть — сразу создаём платёж
        await _create_platega_payment(callback, action, sub_id, days, users, price, email)
    else:
        # Email нет — спрашиваем
        await state.update_data(
            pay_method="platega", action=action, sub_id=sub_id,
            days=days, users=users, price=price
        )
        await state.set_state(PaymentStates.waiting_for_email)
        await callback.message.answer(
            "📧 <b>Введите ваш Email</b>\n\n"
            "Он нужен для привязки к аккаунту и получения чека об оплате.\n"
            "Email вводится <b>один раз</b> — при следующих покупках спрашивать не будем.",
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data.startswith("pay_cryptobot_"))
async def pay_cryptobot_handler(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    action = parts[2]
    sub_id = int(parts[3])
    days = int(parts[4])
    users = int(parts[5])
    price = int(parts[6])
    
    email = await get_user_email(callback.from_user.id)
    
    if email:
        await _create_cryptobot_payment(callback, action, sub_id, days, users, price)
    else:
        await state.update_data(
            pay_method="cryptobot", action=action, sub_id=sub_id,
            days=days, users=users, price=price
        )
        await state.set_state(PaymentStates.waiting_for_email)
        await callback.message.answer(
            "📧 <b>Введите ваш Email</b>\n\n"
            "Он нужен для привязки к аккаунту и получения чека об оплате.\n"
            "Email вводится <b>один раз</b> — при следующих покупках спрашивать не будем.",
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data.startswith("pay_stars_"))
async def pay_stars(callback: CallbackQuery, bot: Bot, state: FSMContext):
    parts = callback.data.split("_")
    action = parts[2]
    sub_id = int(parts[3])
    days = int(parts[4])
    users = int(parts[5])
    price = int(parts[6])
    
    email = await get_user_email(callback.from_user.id)
    
    if email:
        await _create_stars_payment(callback, bot, action, sub_id, days, users, price)
    else:
        await state.update_data(
            pay_method="stars", action=action, sub_id=sub_id,
            days=days, users=users, price=price
        )
        await state.set_state(PaymentStates.waiting_for_email)
        await callback.message.answer(
            "📧 <b>Введите ваш Email</b>\n\n"
            "Он нужен для привязки к аккаунту и получения чека об оплате.\n"
            "Email вводится <b>один раз</b> — при следующих покупках спрашивать не будем.",
            parse_mode="HTML"
        )
    await callback.answer()


# ==================== FSM: Ввод email ====================

@router.message(PaymentStates.waiting_for_email)
async def process_email_input(message: Message, state: FSMContext, bot: Bot):
    email = message.text.strip()
    
    if not validate_email(email):
        await message.answer(
            "❌ <b>Некорректный email.</b>\n\n"
            "Пожалуйста, введите правильный адрес электронной почты (например: user@gmail.com):",
            parse_mode="HTML"
        )
        return
    
    # Сохраняем email
    await save_user_email(message.from_user.id, email)
    
    await message.answer(
        f"✅ Email <b>{email.lower()}</b> сохранён!\n\n"
        "⏳ Создаём платёж...",
        parse_mode="HTML"
    )
    
    # Достаём данные из FSM
    data = await state.get_data()
    await state.clear()
    
    pay_method = data.get("pay_method")
    action = data.get("action")
    sub_id = data.get("sub_id")
    days = data.get("days")
    users = data.get("users")
    price = data.get("price")
    
    if pay_method == "platega":
        await _create_platega_payment_msg(message, action, sub_id, days, users, price, email.lower())
    elif pay_method == "cryptobot":
        await _create_cryptobot_payment_msg(message, action, sub_id, days, users, price)
    elif pay_method == "stars":
        await _create_stars_payment_msg(message, bot, action, sub_id, days, users, price)


# ==================== Создание платежей ====================

async def _create_platega_payment(callback: CallbackQuery, action, sub_id, days, users, price, email):
    """Создать Platega платёж (из callback)."""
    order_id = f"order_{callback.from_user.id}_{action}_{sub_id}_{days}_{users}_{price}"
    try:
        pay_url = await platega.create_invoice(price, order_id)
        await callback.message.answer(
            f"💳 Оплата через <b>Platega (СБП)</b>\n\n"
            f"📧 Чек на: {email}\n"
            f"💰 Сумма: {price} ₽\n\n"
            f"👉 <a href='{pay_url}'>Перейти к оплате</a>\n\n"
            "Ваша подписка будет автоматически обновлена после успешной оплаты.",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Platega error: {e}")
        await callback.message.answer(f"❌ Ошибка создания платежа: {e}")


async def _create_platega_payment_msg(message: Message, action, sub_id, days, users, price, email):
    """Создать Platega платёж (из message после ввода email)."""
    order_id = f"order_{message.from_user.id}_{action}_{sub_id}_{days}_{users}_{price}"
    try:
        pay_url = await platega.create_invoice(price, order_id)
        await message.answer(
            f"💳 Оплата через <b>Platega (СБП)</b>\n\n"
            f"📧 Чек на: {email}\n"
            f"💰 Сумма: {price} ₽\n\n"
            f"👉 <a href='{pay_url}'>Перейти к оплате</a>\n\n"
            "Ваша подписка будет автоматически обновлена после успешной оплаты.",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Platega error: {e}")
        await message.answer(f"❌ Ошибка создания платежа: {e}")


async def _create_cryptobot_payment(callback: CallbackQuery, action, sub_id, days, users, price):
    """Создать CryptoBot платёж (из callback)."""
    amount_usdt = round(price / 90, 2)
    order_id = f"order_{callback.from_user.id}_{action}_{sub_id}_{days}_{users}_{price}"
    try:
        pay_url = await cryptobot.create_invoice(amount_usdt, order_id)
        await callback.message.answer(
            f"💎 Оплата через <b>Crypto Bot (USDT)</b>\n\n"
            f"💰 Сумма: {amount_usdt} USDT (~{price} ₽)\n\n"
            f"👉 <a href='{pay_url}'>Перейти к оплате</a>\n\n"
            "Ваша подписка будет автоматически обновлена после успешной оплаты.",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"CryptoBot error: {e}")
        await callback.message.answer(f"❌ Ошибка создания платежа: {e}")


async def _create_cryptobot_payment_msg(message: Message, action, sub_id, days, users, price):
    """Создать CryptoBot платёж (из message после ввода email)."""
    amount_usdt = round(price / 90, 2)
    order_id = f"order_{message.from_user.id}_{action}_{sub_id}_{days}_{users}_{price}"
    try:
        pay_url = await cryptobot.create_invoice(amount_usdt, order_id)
        await message.answer(
            f"💎 Оплата через <b>Crypto Bot (USDT)</b>\n\n"
            f"💰 Сумма: {amount_usdt} USDT (~{price} ₽)\n\n"
            f"👉 <a href='{pay_url}'>Перейти к оплате</a>\n\n"
            "Ваша подписка будет автоматически обновлена после успешной оплаты.",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"CryptoBot error: {e}")
        await message.answer(f"❌ Ошибка создания платежа: {e}")


async def _create_stars_payment(callback: CallbackQuery, bot: Bot, action, sub_id, days, users, price):
    """Создать Stars платёж (из callback)."""
    prices = [LabeledPrice(label=f"Защита подключения - {days} Дней", amount=price)]
    payload = f"order_{action}_{sub_id}_{days}_{users}_{price}"
    try:
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title="Защита подключения",
            description=f"Безопасный доступ на {days} дней",
            payload=payload,
            provider_token="", 
            currency="XTR",
            prices=prices
        )
    except Exception as e:
        logger.error(f"Stars error: {e}")
        await callback.message.answer(f"❌ Ошибка создания платежа: {e}")


async def _create_stars_payment_msg(message: Message, bot: Bot, action, sub_id, days, users, price):
    """Создать Stars платёж (из message после ввода email)."""
    prices = [LabeledPrice(label=f"Защита подключения - {days} Дней", amount=price)]
    payload = f"order_{action}_{sub_id}_{days}_{users}_{price}"
    try:
        await bot.send_invoice(
            chat_id=message.from_user.id,
            title="Защита подключения",
            description=f"Безопасный доступ на {days} дней",
            payload=payload,
            provider_token="", 
            currency="XTR",
            prices=prices
        )
    except Exception as e:
        logger.error(f"Stars error: {e}")
        await message.answer(f"❌ Ошибка создания платежа: {e}")


# ==================== Stars Pre-checkout & Success ====================

@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@router.message(F.successful_payment)
async def successful_payment_handler(message: Message, bot: Bot):
    payload = message.successful_payment.invoice_payload
    if payload.startswith("order_"):
        parts = payload.split("_")
        action = parts[1]
        sub_id = int(parts[2])
        days = int(parts[3])
        users = int(parts[4])
        
        async with AsyncSessionLocal() as session:
            text = "Ошибка обработки платежа."
            if action == "buy":
                result = await session.execute(select(Subscription).where(Subscription.user_id == message.from_user.id))
                subs = result.scalars().all()
                count = len(subs) + 1
                
                marzban_username = f"user_{message.from_user.id}_{count}_{int(time.time())}"
                
                try:
                    await marzban.create_user(marzban_username, days)
                    new_sub = Subscription(user_id=message.from_user.id, marzban_username=marzban_username, name=f"Подписка №{count}")
                    session.add(new_sub)
                    await session.commit()
                    text = (
                        f"✅ <b>Покупка успешно завершена!</b> Добавлено {days} дней к вашему новому подключению.\n\n"
                        f"👉 Перейдите в раздел <b>🔑 Мои активные ключи</b>, чтобы скопировать ваш ключ доступа.\n"
                        f"👉 Чтобы настроить устройство прямо сейчас, выберите вашу операционную систему ниже:"
                    )
                except Exception as e:
                    text = f"Оплата прошла, но возникла ошибка создания ключа: {e}"

            elif action == "extend":
                result = await session.execute(select(Subscription).where(Subscription.id == sub_id, Subscription.user_id == message.from_user.id))
                sub = result.scalar_one_or_none()
                if sub:
                    try:
                        await marzban.add_days(sub.marzban_username, days)
                        text = (
                            f"✅ <b>Продление успешно завершено!</b> Добавлено {days} дней к вашей подписке.\n\n"
                            f"👉 Перейдите в раздел <b>🔑 Мои активные ключи</b>, чтобы скопировать ваш ключ доступа."
                        )
                    except Exception as e:
                        text = f"Оплата прошла, но возникла ошибка продления: {e}"
                else:
                    text = "Оплата прошла, но подписка не найдена для продления."
            
            keyboard = help_os_keyboard() if action == "buy" and "успешно" in text else main_menu()
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
