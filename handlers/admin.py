from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func, desc
from config import config
from database.db import AsyncSessionLocal
from database.models import User, PromoCode
from keyboards.inline import admin_main_keyboard, admin_user_card_keyboard
from services.marzban import MarzbanAPI
from contextlib import suppress
from aiogram.exceptions import TelegramBadRequest

router = Router()
marzban = MarzbanAPI()

class AdminStates(StatesGroup):
    waiting_for_user_query = State()
    waiting_for_days = State()
    waiting_promo_code = State()
    waiting_promo_days = State()
    waiting_promo_max_uses = State()

def is_admin(user_id):
    return user_id in config.ADMIN_IDS

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id): return
    await message.answer("🛡 <b>Админ-панель</b>", reply_markup=admin_main_keyboard(), parse_mode="HTML")

@router.callback_query(F.data == "admin_home")
async def adm_home(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    with suppress(TelegramBadRequest):
         await callback.message.edit_text("🛡 <b>Админ-панель</b>", reply_markup=admin_main_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin_top_refs")
async def admin_top_refs(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    async with AsyncSessionLocal() as session:
        stmt = (
            select(User.referrer_id, func.count(User.user_id).label('ref_count'))
            .where(User.referrer_id.isnot(None))
            .group_by(User.referrer_id)
            .order_by(desc('ref_count'))
            .limit(10)
        )
        result = await session.execute(stmt)
        top_refs = result.all()
        
        if not top_refs:
            with suppress(TelegramBadRequest):
                await callback.message.edit_text("🤷‍♂️ Пока нет ни одного реферала.", reply_markup=admin_main_keyboard(), parse_mode="HTML")
            await callback.answer()
            return
            
        text = "🏆 <b>Топ рефералов:</b>\n\n"
        kb = []
        for rank, (ref_id, count) in enumerate(top_refs, 1):
            u_stmt = select(User).where(User.user_id == ref_id)
            u_res = await session.execute(u_stmt)
            user_obj = u_res.scalar_one_or_none()
            username = f"@{user_obj.username}" if user_obj and user_obj.username else f"ID: {ref_id}"
            
            text += f"{rank}. {username} — {count} приглашенных\n"
            kb.append([InlineKeyboardButton(text=f"Управление {username}", callback_data=f"adm_user_{ref_id}")])
            
        kb.append([InlineKeyboardButton(text="🔙 В админ-панель", callback_data="admin_home")])
        
        with suppress(TelegramBadRequest):
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin_find_user")
async def admin_find_user(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.set_state(AdminStates.waiting_for_user_query)
    with suppress(TelegramBadRequest):
        await callback.message.edit_text("🔍 Отправьте User ID или Username:")
    await callback.answer()

@router.message(AdminStates.waiting_for_user_query)
async def process_find_user(message: Message, state: FSMContext):
    query = message.text.strip()
    async with AsyncSessionLocal() as session:
        if query.isdigit():
            result = await session.execute(select(User).where(User.user_id == int(query)))
        else:
            username = query.lstrip('@')
            result = await session.execute(select(User).where(User.username == username))
            
        user = result.scalar_one_or_none()
        if user:
            ref_stmt = select(func.count(User.user_id)).where(User.referrer_id == user.user_id)
            ref_count = await session.scalar(ref_stmt)
            status_text = (
                f"👤 <b>Информация об управлении:</b>\n"
                f"ID: <code>{user.user_id}</code>\n"
                f"Username: @{user.username}\n"
                f"Marzban: {user.marzban_username}\n"
                f"Заблокирован: {'Да' if user.is_banned else 'Нет'}\n"
                f"Пригласил: {ref_count} чел.\n"
            )
            await message.answer(status_text, reply_markup=admin_user_card_keyboard(user.user_id, user.is_banned), parse_mode="HTML")
        else:
            await message.answer("❌ Пользователь не найден в БД.", reply_markup=admin_main_keyboard())
    await state.clear()

@router.callback_query(F.data.startswith("adm_user_"))
async def adm_user_info(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    user_id = int(callback.data.split("_")[2])
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        
        if user:
            ref_stmt = select(func.count(User.user_id)).where(User.referrer_id == user.user_id)
            ref_count = await session.scalar(ref_stmt)
            
            status_text = (
                f"👤 <b>Информация об управлении:</b>\n"
                f"ID: <code>{user.user_id}</code>\n"
                f"Username: @{user.username}\n"
                f"Email: {user.email or '—'}\n"
                f"Marzban: {user.marzban_username}\n"
                f"Заблокирован: {'Да' if user.is_banned else 'Нет'}\n"
                f"Пригласил: {ref_count} чел.\n"
            )
            with suppress(TelegramBadRequest):
                await callback.message.edit_text(status_text, reply_markup=admin_user_card_keyboard(user.user_id, user.is_banned), parse_mode="HTML")
            await callback.answer()
        else:
            await callback.answer("Пользователь не найден.", show_alert=True)

@router.callback_query(F.data.startswith("adm_add_"))
async def adm_add_days_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    user_id = int(callback.data.split("_")[2])
    await state.update_data(target_user_id=user_id)
    await state.set_state(AdminStates.waiting_for_days)
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(f"➕ Сколько дней добавить пользователю {user_id}?\n\n(Введите число в чат)")
    await callback.answer()

@router.message(AdminStates.waiting_for_days)
async def process_add_days(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("target_user_id")
    if not user_id or not message.text.isdigit():
        await message.answer("Ошибка формата. Пожалуйста, введите корректное число.")
        return
        
    days = int(message.text)
    async with AsyncSessionLocal() as session:
         result = await session.execute(select(User).where(User.user_id == user_id))
         user = result.scalar_one_or_none()
         if user and user.marzban_username:
             try:
                 await marzban.add_days(user.marzban_username, days)
                 await message.answer(f"✅ Успешно добавлено {days} дней пользователю {user_id}.")
             except Exception as e:
                 await message.answer(f"Ошибка API Marzban: {e}")
         else:
             await message.answer("❌ Узел Marzban для данного пользователя не найден (скорее всего подписка не была создана).")
    
    await state.clear()
    await message.answer("Вы вернулись в меню администратора.", reply_markup=admin_main_keyboard())

@router.callback_query(F.data.startswith("adm_rm_"))
async def adm_remove_sub(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    user_id = int(callback.data.split("_")[2])
    async with AsyncSessionLocal() as session:
         result = await session.execute(select(User).where(User.user_id == user_id))
         user = result.scalar_one_or_none()
         if user and user.marzban_username:
             try:
                 await marzban.remove_user(user.marzban_username)
                 user.marzban_username = None
                 await session.commit()
                 with suppress(TelegramBadRequest):
                     await callback.message.edit_text(f"✅ Подписка пользователя {user_id} удалена.", reply_markup=admin_main_keyboard())
             except Exception as e:
                 await callback.message.answer(f"Ошибка API. {e}")
         else:
             await callback.answer("Запись не найдена, либо подписка уже удалена.", show_alert=True)

@router.callback_query(F.data.startswith("adm_rtrial_"))
async def adm_reset_trial(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    user_id = int(callback.data.split("_")[2])
    async with AsyncSessionLocal() as session:
         result = await session.execute(select(User).where(User.user_id == user_id))
         user = result.scalar_one_or_none()
         if user:
             user.is_trial_used = False
             await session.commit()
             await callback.answer("✅ Бесплатный период (триал) успешно сброшен!", show_alert=True)
         else:
             await callback.answer("Запись не найдена.", show_alert=True)

@router.callback_query(F.data.startswith("adm_ban_"))
async def adm_ban_user(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    user_id = int(callback.data.split("_")[2])
    async with AsyncSessionLocal() as session:
         result = await session.execute(select(User).where(User.user_id == user_id))
         user = result.scalar_one_or_none()
         if user:
             user.is_banned = not user.is_banned
             await session.commit()
             status = 'Да' if user.is_banned else 'Нет'
             with suppress(TelegramBadRequest):
                 await callback.message.edit_reply_markup(reply_markup=admin_user_card_keyboard(user_id, user.is_banned))
             await callback.answer(f"Статус блокировки изменен! Заблокирован: {status}", show_alert=True)
         else:
             await callback.answer("Не найдено.", show_alert=True)


# ==================== ПРОМОКОДЫ ====================

@router.callback_query(F.data == "admin_promos")
async def admin_promos_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(PromoCode).where(PromoCode.is_active == True).order_by(PromoCode.id.desc())
        )
        promos = result.scalars().all()
        
        if not promos:
            with suppress(TelegramBadRequest):
                await callback.message.edit_text(
                    "🎟 <b>Промокоды</b>\n\n"
                    "Нет активных промокодов.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin_create_promo")],
                        [InlineKeyboardButton(text="🔙 В админ-панель", callback_data="admin_home")]
                    ]),
                    parse_mode="HTML"
                )
            await callback.answer()
            return
        
        text = "🎟 <b>Активные промокоды:</b>\n\n"
        kb = []
        for p in promos:
            uses_text = f"{p.current_uses}/{p.max_uses}" if p.max_uses > 0 else f"{p.current_uses}/∞"
            text += f"• <code>{p.code}</code> — +{p.days} дн. | Исп.: {uses_text}\n"
            kb.append([InlineKeyboardButton(text=f"❌ Удалить {p.code}", callback_data=f"adm_delpromo_{p.id}")])
        
        kb.append([InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin_create_promo")])
        kb.append([InlineKeyboardButton(text="🔙 В админ-панель", callback_data="admin_home")])
        
        with suppress(TelegramBadRequest):
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_create_promo")
async def admin_create_promo_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.set_state(AdminStates.waiting_promo_code)
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            "➕ <b>Создание промокода</b>\n\n"
            "Шаг 1/3: Введите код промокода (например: SPRING2026):",
            parse_mode="HTML"
        )
    await callback.answer()


@router.message(AdminStates.waiting_promo_code)
async def process_promo_code(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    if len(code) < 3 or len(code) > 30 or ' ' in code:
        await message.answer("❌ Код должен быть от 3 до 30 символов без пробелов. Попробуйте ещё:")
        return
    
    # Проверка уникальности
    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(PromoCode).where(PromoCode.code == code))
        if existing.scalar_one_or_none():
            await message.answer(f"❌ Промокод <code>{code}</code> уже существует! Введите другой:", parse_mode="HTML")
            return
    
    await state.update_data(promo_code=code)
    await state.set_state(AdminStates.waiting_promo_days)
    await message.answer(
        f"✅ Код: <code>{code}</code>\n\n"
        "Шаг 2/3: Сколько дней добавляет этот промокод?",
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_promo_days)
async def process_promo_days(message: Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) < 1 or int(message.text) > 365:
        await message.answer("❌ Введите число от 1 до 365:")
        return
    
    await state.update_data(promo_days=int(message.text))
    await state.set_state(AdminStates.waiting_promo_max_uses)
    await message.answer(
        f"✅ Дней: {message.text}\n\n"
        "Шаг 3/3: Максимальное кол-во активаций (0 = безлимит):"
    )


@router.message(AdminStates.waiting_promo_max_uses)
async def process_promo_max_uses(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Введите число (например: 100 или 0 для безлимита):")
        return
    
    data = await state.get_data()
    await state.clear()
    
    from datetime import datetime, timezone
    code = data["promo_code"]
    days = data["promo_days"]
    max_uses = int(message.text)
    
    async with AsyncSessionLocal() as session:
        new_promo = PromoCode(
            code=code,
            days=days,
            max_uses=max_uses,
            current_uses=0,
            is_active=True,
            created_by=message.from_user.id,
            created_at=datetime.now(timezone.utc)
        )
        session.add(new_promo)
        await session.commit()
    
    uses_text = f"{max_uses} активаций" if max_uses > 0 else "Безлимит активаций"
    await message.answer(
        f"✅ <b>Промокод создан!</b>\n\n"
        f"🎟 Код: <code>{code}</code>\n"
        f"📅 Дней: +{days}\n"
        f"👥 Лимит: {uses_text}\n",
        reply_markup=admin_main_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("adm_delpromo_"))
async def admin_delete_promo(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    promo_id = int(callback.data.split("_")[2])
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(PromoCode).where(PromoCode.id == promo_id))
        promo = result.scalar_one_or_none()
        if promo:
            promo.is_active = False
            await session.commit()
            await callback.answer(f"✅ Промокод {promo.code} деактивирован!", show_alert=True)
            # Обновим список
            await admin_promos_list(callback)
        else:
            await callback.answer("Промокод не найден.", show_alert=True)
