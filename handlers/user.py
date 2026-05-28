from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import AsyncSessionLocal
from database.models import User, Subscription, PromoCode, PromoCodeUsage, GiftCertificate
from keyboards.inline import main_menu, faq_keyboard, sub_channel_keyboard, help_os_keyboard, help_back_keyboard, user_keys_keyboard, key_info_keyboard
from sqlalchemy import select
from config import config
from services.marzban import MarzbanAPI
from datetime import datetime, timezone, timedelta
from contextlib import suppress
from aiogram.exceptions import TelegramBadRequest

router = Router()
marzban = MarzbanAPI()


class UserStates(StatesGroup):
    waiting_for_promo = State()
    waiting_gift_days = State()
    waiting_gift_code = State()

async def get_db_user(session, user_id):
    result = await session.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()

@router.message(CommandStart())
async def cmd_start(message: Message):
    args = message.text.split(' ')
    referrer_id = None
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        
    async with AsyncSessionLocal() as session:
        user = await get_db_user(session, message.from_user.id)
        if not user:
            user = User(
                user_id=message.from_user.id,
                username=message.from_user.username,
                referrer_id=referrer_id
            )
            session.add(user)
            await session.commit()
            
        if user.is_banned:
            return await message.answer("Доступ к сервису запрещен.")
            
        await message.answer("🛡 Добро пожаловать в NodeConnect. Ваше подключение в безопасности!", reply_markup=main_menu())

@router.callback_query(F.data == "faq")
async def faq_cmd(callback: CallbackQuery):
    text = (
        "❓ <b>FAQ и Документация</b>\n\n"
        "Здесь вы можете ознакомиться с нашими правилами и политикой:\n"
        "• <a href='https://telegra.ph/Polzovatelskoe-soglashenie-04-01-19'>Пользовательское соглашение</a>\n"
        "• <a href='https://telegra.ph/Politika-konfidencialnosti-04-01-26'>Политика конфиденциальности</a>"
    )
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(text, reply_markup=faq_keyboard(), parse_mode="HTML", disable_web_page_preview=True)
    await callback.answer()

@router.callback_query(F.data == "get_trial")
async def get_trial_cmd(callback: CallbackQuery):
    async with AsyncSessionLocal() as session:
        user = await get_db_user(session, callback.from_user.id)
        if user.is_trial_used:
            await callback.answer("❌ Вы уже использовали бесплатный период.", show_alert=True)
            return
            
        with suppress(TelegramBadRequest):
            await callback.message.edit_text(
                "🎁 <b>Бесплатный период на 3 дня</b>\n\n"
                "Чтобы получить доступ, подпишитесь на наш канал и нажмите кнопку проверки ниже.",
                reply_markup=sub_channel_keyboard(config.CHANNEL_URL),
                parse_mode="HTML"
            )
    await callback.answer()

@router.callback_query(F.data == "check_sub")
async def check_subscription(callback: CallbackQuery, bot: Bot):
    with suppress(TelegramBadRequest):
        await callback.answer("⏳ Момент, проверяем подписку...", show_alert=False)
        
    member = await bot.get_chat_member(config.REQUIRED_CHANNEL_ID, callback.from_user.id)
    if member.status in ['member', 'administrator', 'creator']:
        async with AsyncSessionLocal() as session:
            user = await get_db_user(session, callback.from_user.id)
            if not user.is_trial_used:
                user.is_trial_used = True
                
                marzban_username = f"user_{user.user_id}_trial"
                try:
                    await marzban.create_user(marzban_username, 3)
                    new_sub = Subscription(user_id=user.user_id, marzban_username=marzban_username, name="Trial (3 Дня)")
                    session.add(new_sub)
                    
                    if user.referrer_id and user.referrer_id != user.user_id:
                        referrer = await get_db_user(session, user.referrer_id)
                        if referrer:
                            ref_result = await session.execute(select(Subscription).where(Subscription.user_id == referrer.user_id))
                            ref_subs = ref_result.scalars().all()
                            if ref_subs:
                                await marzban.add_days(ref_subs[0].marzban_username, 1)
                                with suppress(Exception):
                                    await bot.send_message(user.referrer_id, "🎉 Ваш реферал активировал пробный период! Начислен +1 день защиты.")
                except Exception as e:
                    import traceback
                    tb = traceback.format_exc()
                    print(f"Sub error: {tb}")
                    await callback.message.answer(f"❌ Ошибка создания узла. Обратитесь в поддержку.\n\nКод: {str(e)}")
                    return
                
                await session.commit()
                with suppress(TelegramBadRequest):
                    await callback.message.edit_text(
                        "✅ <b>Бесплатный период активирован!</b>\n\n"
                        "👉 Для подключения скопируйте ключ из раздела <b>🔑 Мои активные ключи</b> (оно уже добавлено в список).\n"
                        "👉 Чтобы настроить устройство прямо сейчас, выберите вашу операционную систему ниже:",
                        reply_markup=help_os_keyboard(),
                        parse_mode="HTML"
                    )
            else:
                with suppress(TelegramBadRequest):
                    await callback.message.edit_text("❌ Вы уже использовали бесплатный период.", reply_markup=main_menu())
    else:
        await callback.message.answer("❌ Вы не подписаны на канал!")

@router.callback_query(F.data == "my_keys")
async def my_keys_handler(callback: CallbackQuery):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Subscription).where(Subscription.user_id == callback.from_user.id))
        subs = result.scalars().all()
        
        if not subs:
            with suppress(TelegramBadRequest):
                await callback.message.edit_text("У вас нет активных ключей. Перейдите в Продлить/Купить.", reply_markup=main_menu())
            return
            
        with suppress(TelegramBadRequest):
            await callback.message.edit_text("🔑 <b>Ваши активные ключи:</b>\nВыберите ключ для управления:", reply_markup=user_keys_keyboard(subs), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("key_"))
async def key_info(callback: CallbackQuery):
    sub_id = int(callback.data.split("_")[1])
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Subscription).where(Subscription.id == sub_id, Subscription.user_id == callback.from_user.id))
        sub = result.scalar_one_or_none()
        
        if not sub:
            await callback.answer("Ключ не найден", show_alert=True)
            return

        try:
            node_info = await marzban.get_user(sub.marzban_username)
            expire_timestamp = node_info.get('expire')
            used_traffic = node_info.get('used_traffic', 0)
            status = node_info.get('status', 'Unknown')
            subscription_url = node_info.get('subscription_url', '')
            links = node_info.get('links', [])
            
            if subscription_url:
                if subscription_url.startswith('/'):
                    sub_link = f"{config.MARZBAN_URL.rstrip('/')}{subscription_url}"
                else:
                    sub_link = subscription_url
            elif links:
                sub_link = "\n".join(links[:2]) # Ограничим до 2 ссылок, чтобы не было слишком длинно
            else:
                sub_link = "Ссылка не найдена"
            
            if status == "on_hold":
                days_left = "⏳ Начнется при первом подключении"
            elif expire_timestamp:
                dt = datetime.fromtimestamp(expire_timestamp, timezone.utc)
                days_left = (dt - datetime.now(timezone.utc)).days
            else:
                days_left = "Безлимит"
                
            text = (
                f"🛡 <b>{sub.name}</b>\n\n"
                f"Статус: {status}\n"
                f"Осталось дней: {days_left}\n"
                f"Трафик: {used_traffic / (1024**3):.2f} ГБ\n\n"
                f"🔗 <b>Ссылка для подключения:</b>\n<code>{sub_link}</code>"
            )
            with suppress(TelegramBadRequest):
                await callback.message.edit_text(text, reply_markup=key_info_keyboard(sub.id), parse_mode="HTML")
            
        except Exception as e:
            await callback.message.answer(f"❌ Ошибка API. Попробуйте позже.")
    await callback.answer()

@router.callback_query(F.data == "referral")
async def referral_program(callback: CallbackQuery, bot: Bot):
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={callback.from_user.id}"
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            f"👥 <b>Партнерская программа</b>\n\n"
            f"Приглашайте друзей и получайте +1 день защиты за каждого!\n"
            f"Ваша ссылка:\n<code>{ref_link}</code>",
            reply_markup=main_menu(),
            parse_mode="HTML"
        )
    await callback.answer()

@router.callback_query(F.data == "help")
async def help_cmd(callback: CallbackQuery):
    name = callback.from_user.first_name or "Пользователь"
    text = f"{name}, выбери свое устройство ниже 👇 для того, чтобы я показал тебе простую инструкцию подключения 🔌"
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(text, reply_markup=help_os_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("help_"))
async def help_os_cmd(callback: CallbackQuery):
    os_name = callback.data.split("_")[1]
    
    if os_name == "android":
        text = (
            "📱 <b>Инструкция для Android</b>\n\n"
            "1️⃣ Скопируйте ваш ключ доступа (из раздела \"🔑 Мои активные ключи\")\n"
            "2️⃣ Установите приложение:\n"
            "  • v2RayTun (Google Play) <a href='https://play.google.com/store/apps/details?id=com.v2raytun.android'>🌐Скачать</a>\n"
            "  • v2RayTun (из GitHub) <a href='https://github.com/DigneZzZ/v2raytun/releases/download/5.19.64/v2RayTun_universal.apk'>🌐Скачать</a>\n"
            "3️⃣ Запустите программу и нажмите ➕ в правом верхнем углу\n"
            "4️⃣ Выберите «Импорт из буфера обмена»\n"
            "5️⃣ Нажмите на круглую кнопку включения и наслаждайтесь высокой скоростью и стабильностью 😉\n\n"
            "‼️ <i>Что делать, если ничего не грузит после подключения?</i>\n"
            "1. Зайдите в главное меню бота и смените локацию (если доступно, либо просто переполучите ключ).\n"
            "2. Бот выдаст новый ключ, его вставьте в приложение (старый удалите).\n\n"
            "⚠️ <b>Важно:</b> один ключ — два устройства."
        )
    elif os_name == "ios":
        text = (
            "🍏 <b>Инструкция для iOS</b>\n\n"
            "1️⃣ Скопируйте ваш ключ доступа (из раздела \"🔑 Мои активные ключи\")\n"
            "2️⃣ Установите приложение: Happ <a href='https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973'>🌐Скачать</a>\n"
            "3️⃣ Запустите приложение Happ и в правом верхнем углу нажмите на ➕\n"
            "4️⃣ Затем выберите «вставить из буфера обмена» и готово!"
        )
    elif os_name == "windows":
        text = (
            "💻 <b>Инструкция для Windows</b>\n\n"
            "1️⃣ Скопируйте ваш ключ доступа (из раздела \"🔑 Мои активные ключи\")\n"
            "2️⃣ Скачайте и установите приложение v2RayTun <a href='https://cloud.mail.ru/public/taFv/FxEarQUBM'>🌐Скачать</a>\n"
            "3️⃣ Запустите приложение, в правом верхнем углу нажмите ➕\n"
            "4️⃣ Затем «Импорт из буфера обмена», далее поставьте режим туннель."
        )
    elif os_name == "macos":
        text = (
            "🍏 <b>Инструкция для MacOS</b>\n\n"
            "1️⃣ Скопируйте ваш ключ доступа (из раздела \"🔑 Мои активные ключи\")\n"
            "2️⃣ Установите одно из приложений:\n"
            "  • V2Box <a href='https://apps.apple.com/ru/app/v2box-v2ray-client/id6446814690'>🌐Скачать</a>\n"
            "  • Hiddify (Рекомендуем) <a href='https://github.com/hiddify/hiddify-next/releases/download/v2.0.5/Hiddify-MacOS.dmg'>🌐Скачать</a>\n"
            "3️⃣ Запустите программу V2Box\\Hiddify и перейдите на вкладку «Configs» (снизу)\n"
            "4️⃣ Далее нажмите ➕ в правом верхнем углу и выберите «Import v2ray uri from clipboard» (первый пункт в списке)\n"
            "5️⃣ После перейдите на вкладку «Home» (снизу), нажмите большую кнопку «Tap to Connect» и всё готово!"
        )
    else:
        text = "Инструкция в разработке."
        
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(text, reply_markup=help_back_keyboard(), parse_mode="HTML", disable_web_page_preview=True)
    await callback.answer()

@router.callback_query(F.data == "about_project")
async def about_project_cmd(callback: CallbackQuery):
    text = (
        "🛡 <b>NodeConnect — Инструмент корпоративного уровня для защиты трафика</b>\n"
        "NodeConnect — высокотехнологичное решение для создания персональных защищенных узлов связи. Мы обеспечиваем стабильное и зашифрованное соединение для безопасной работы в цифровой среде.\n\n"
        "✨ <b>Технологические преимущества:</b>\n"
        "🔐 <b>Профессиональное шифрование:</b> Использование современных протоколов гарантирует, что ваши данные защищены от перехвата в любых сетях, включая открытые Wi-Fi точки.\n\n"
        "🚀 <b>Оптимизация маршрутов:</b> Наши алгоритмы интеллектуального распределения трафика выбирают наиболее стабильные узлы, что значительно снижает задержки и повышает скорость.\n\n"
        "💎 <b>Приватный доступ:</b> NodeConnect скрывает ваш реальный сетевой идентификатор, предотвращая сбор цифрового профиля рекламными сетями и трекерами.\n\n"
        "💻 <b>Кроссплатформенная интеграция:</b> Используйте один аккаунт для защиты всей вашей инфраструктуры — от мобильных устройств до компьютеров.\n\n"
        "📉 <b>Экономия ресурсов:</b> Оптимизированные приложения не нагружают процессор и минимально влияют на автономность вашего устройства.\n\n"
        "🚫 <b>Отсутствие логов:</b> Мы работаем по принципу отсутствия сбора данных. Мы не храним и не анализируем ваш трафик.\n\n"
        "🛠 <b>Как использовать NodeConnect?</b>\n"
        "1. Перейдите в раздел «💎 Купить подписку» или активируйте бесплатный период.\n"
        "2. Затем в разделе «🔑 Мои активные ключи» скопируйте ваш уникальный ключ доступа.\n"
        "3. Перейдите в раздел «⚙️ Помощь/Инструкции», выберите вашу систему и скачайте рекомендуемое приложение.\n"
        "4. Вставьте ключ в приложение и нажмите кнопку подключения. Готово!\n\n"
        "📋 <i>NodeConnect является инструментом для защиты информации и предназначен для легального использования.</i>"
    )
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(text, reply_markup=main_menu(), parse_mode="HTML")
    await callback.answer()


# ==================== ПРОМОКОДЫ ====================

@router.callback_query(F.data == "enter_promo")
async def enter_promo_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.waiting_for_promo)
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            "🎟 <b>Активация промокода</b>\n\n"
            "Введите ваш промокод:",
            parse_mode="HTML"
        )
    await callback.answer()


@router.message(UserStates.waiting_for_promo)
async def process_promo_activation(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    await state.clear()
    
    async with AsyncSessionLocal() as session:
        # Найти промокод
        result = await session.execute(
            select(PromoCode).where(PromoCode.code == code, PromoCode.is_active == True)
        )
        promo = result.scalar_one_or_none()
        
        if not promo:
            await message.answer(
                "❌ Промокод не найден или деактивирован.",
                reply_markup=main_menu()
            )
            return
        
        # Проверить лимит использований
        if promo.max_uses > 0 and promo.current_uses >= promo.max_uses:
            await message.answer(
                "❌ Этот промокод уже исчерпал лимит использований.",
                reply_markup=main_menu()
            )
            return
        
        # Проверить, не использовал ли уже этот юзер
        usage_check = await session.execute(
            select(PromoCodeUsage).where(
                PromoCodeUsage.promo_id == promo.id,
                PromoCodeUsage.user_id == message.from_user.id
            )
        )
        if usage_check.scalar_one_or_none():
            await message.answer(
                "❌ Вы уже использовали этот промокод.",
                reply_markup=main_menu()
            )
            return
        
        # Проверить наличие активной подписки
        user = await get_db_user(session, message.from_user.id)
        if not user or not user.subscriptions:
            await message.answer(
                "❌ У вас нет активной подписки.\n"
                "Сначала купите подписку, а потом активируйте промокод.",
                reply_markup=main_menu()
            )
            return
        
        # Добавить дни к первой (основной) подписке через Marzban
        sub = user.subscriptions[0]
        try:
            await marzban.add_days(sub.marzban_username, promo.days)
        except Exception as e:
            await message.answer(
                f"❌ Ошибка при добавлении дней: {e}",
                reply_markup=main_menu()
            )
            return
        
        # Записать использование
        usage = PromoCodeUsage(
            promo_id=promo.id,
            user_id=message.from_user.id,
            used_at=datetime.now(timezone.utc)
        )
        session.add(usage)
        promo.current_uses += 1
        await session.commit()
        
        await message.answer(
            f"✅ <b>Промокод активирован!</b>\n\n"
            f"🎟 Код: <code>{code}</code>\n"
            f"📅 Добавлено: +{promo.days} дней к подписке <b>{sub.name}</b>",
            reply_markup=main_menu(),
            parse_mode="HTML"
        )


# ==================== ПОДАРОЧНЫЕ СЕРТИФИКАТЫ ====================

@router.callback_query(F.data == "gift_create")
async def gift_create_start(callback: CallbackQuery, state: FSMContext):
    async with AsyncSessionLocal() as session:
        user = await get_db_user(session, callback.from_user.id)
        if not user or not user.subscriptions:
            await callback.answer("❗ Сначала купите подписку, чтобы дарить VPN.", show_alert=True)
            return
    
    await state.set_state(UserStates.waiting_gift_days)
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            "🎁 <b>Подарочный сертификат</b>\n\n"
            "Сколько дней VPN вы хотите подарить?\n"
            "Введите число от 1 до 90:",
            parse_mode="HTML"
        )
    await callback.answer()


@router.message(UserStates.waiting_gift_days)
async def process_gift_days(message: Message, state: FSMContext):
    try:
        days = int(message.text.strip())
        if days < 1 or days > 90:
            await message.answer("❗ Введите число от 1 до 90.")
            return
    except ValueError:
        await message.answer("❗ Введите число.")
        return
    
    await state.clear()
    
    import string
    import random
    code = 'GIFT-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    async with AsyncSessionLocal() as session:
        gift = GiftCertificate(
            code=code,
            days=days,
            created_by=message.from_user.id,
            created_at=datetime.now(timezone.utc)
        )
        session.add(gift)
        await session.commit()
    
    await message.answer(
        f"✅ <b>Подарочный сертификат создан!</b>\n\n"
        f"🎁 Код: <code>{code}</code>\n"
        f"📅 Дней VPN: <b>{days}</b>\n\n"
        f"Отправьте этот код другу. Он сможет активировать его в меню «🎀 Активировать подарок».",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "gift_redeem")
async def gift_redeem_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.waiting_gift_code)
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            "🎀 <b>Активация подарка</b>\n\n"
            "Введите код подарочного сертификата:",
            parse_mode="HTML"
        )
    await callback.answer()


@router.message(UserStates.waiting_gift_code)
async def process_gift_redeem(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    await state.clear()
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(GiftCertificate).where(
                GiftCertificate.code == code,
                GiftCertificate.is_used == False
            )
        )
        gift = result.scalar_one_or_none()
        
        if not gift:
            await message.answer(
                "❌ Подарочный код не найден или уже использован.",
                reply_markup=main_menu()
            )
            return
        
        user = await get_db_user(session, message.from_user.id)
        if not user or not user.subscriptions:
            await message.answer(
                "❌ Сначала купите подписку или активируйте бесплатный период.",
                reply_markup=main_menu()
            )
            return
        
        sub = user.subscriptions[0]
        try:
            await marzban.add_days(sub.marzban_username, gift.days)
        except Exception as e:
            await message.answer(f"❌ Ошибка: {e}", reply_markup=main_menu())
            return
        
        gift.is_used = True
        gift.redeemed_by = message.from_user.id
        gift.redeemed_at = datetime.now(timezone.utc)
        await session.commit()
        
        await message.answer(
            f"✅ <b>Подарок активирован!</b>\n\n"
            f"🎁 Код: <code>{code}</code>\n"
            f"📅 Добавлено: +{gift.days} дней к подписке <b>{sub.name}</b>",
            reply_markup=main_menu(),
            parse_mode="HTML"
        )
