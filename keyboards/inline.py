from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Мои активные ключи", callback_data="my_keys")],
        [InlineKeyboardButton(text="💎 Купить подписку", callback_data="buy_sub")],
        [InlineKeyboardButton(text="🎁 Бесплатный период (3 Дня)", callback_data="get_trial")],
        [InlineKeyboardButton(text="🎟 Активировать промокод", callback_data="enter_promo")],
        [
            InlineKeyboardButton(text="🎁 Подарить VPN", callback_data="gift_create"),
            InlineKeyboardButton(text="🎀 Активировать подарок", callback_data="gift_redeem")
        ],
        [
            InlineKeyboardButton(text="👥 Партнерская", callback_data="referral"),
            InlineKeyboardButton(text="ℹ️ О проекте", callback_data="about_project")
        ],
        [InlineKeyboardButton(text="⚙️ Помощь/Инструкции", callback_data="help")],
        [InlineKeyboardButton(text="❓ FAQ", callback_data="faq")]
    ])


def faq_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_main")]
    ])

def sub_channel_keyboard(channel_url: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url=channel_url)],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")]
    ])

def user_keys_keyboard(subs):
    kb = []
    for sub in subs:
        kb.append([InlineKeyboardButton(text=f"🔑 {sub.name}", callback_data=f"key_{sub.id}")])
    kb.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def key_info_keyboard(sub_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Продлить", callback_data=f"extend_{sub_id}")],
        [InlineKeyboardButton(text="🔙 К списку ключей", callback_data="my_keys")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_main")]
    ])

def periods_keyboard(action="buy", sub_id=0):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 30 Дней", callback_data=f"period_{action}_{sub_id}_30")],
        [InlineKeyboardButton(text="📅 60 Дней", callback_data=f"period_{action}_{sub_id}_60")],
        [InlineKeyboardButton(text="📅 90 Дней", callback_data=f"period_{action}_{sub_id}_90")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"key_{sub_id}" if action == "extend" else "back_main")]
    ])

def users_keyboard(action: str, sub_id: int, days: int):
    PRICES = {
        30: {1: 149, 3: 219, 5: 279, 10: 399, 999: 799},
        60: {1: 249, 3: 319, 5: 399, 10: 599, 999: 999},
        90: {1: 349, 3: 419, 5: 579, 10: 799, 999: 1599}
    }
    kb = []
    prices_for_day = PRICES.get(days, {})
    for users, price in prices_for_day.items():
        user_text = f"👤 {users} устройств{'а' if users in [2,3,4] else ''}" if users != 999 else "♾ Безлимит устройств"
        if users > 4 and users != 999:
            user_text = f"👤 {users} устройств"
        if users == 1:
            user_text = f"👤 1 устройство"
            
        kb.append([InlineKeyboardButton(text=f"{user_text} - {price} ₽", callback_data=f"tariff_{action}_{sub_id}_{days}_{users}_{price}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"extend_{sub_id}" if action == "extend" else "buy_sub")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def payment_methods_keyboard(action: str, sub_id: int, days: int, users: int, price: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💳 СБП / Platega ({price} ₽)", callback_data=f"pay_platega_{action}_{sub_id}_{days}_{users}_{price}")],
        [InlineKeyboardButton(text=f"💎 Crypto Bot (USDT)", callback_data=f"pay_cryptobot_{action}_{sub_id}_{days}_{users}_{price}")],
        [InlineKeyboardButton(text=f"⭐️ Звезды ({price} ⭐️)", callback_data=f"pay_stars_{action}_{sub_id}_{days}_{users}_{price}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"period_{action}_{sub_id}_{days}")]
    ])

def admin_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Найти пользователя", callback_data="admin_find_user")],
        [InlineKeyboardButton(text="🏆 Топ рефералов", callback_data="admin_top_refs")],
        [InlineKeyboardButton(text="🎟 Промокоды", callback_data="admin_promos")],
        [InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin_create_promo")]
    ])

def admin_user_card_keyboard(user_id: int, is_banned: bool):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить дни", callback_data=f"adm_add_{user_id}")],
        [InlineKeyboardButton(text="🔄 Сбросить триал", callback_data=f"adm_rtrial_{user_id}")],
        [InlineKeyboardButton(text="🗑 Удалить подписку", callback_data=f"adm_rm_{user_id}")],
        [InlineKeyboardButton(text="🔓 Разбанить" if is_banned else "🔨 Забанить", callback_data=f"adm_ban_{user_id}")],
        [InlineKeyboardButton(text="🔙 В админ-панель", callback_data="admin_home")]
    ])

def help_os_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Android", callback_data="help_android")],
        [InlineKeyboardButton(text="🍏 iOS", callback_data="help_ios")],
        [InlineKeyboardButton(text="💻 Windows", callback_data="help_windows")],
        [InlineKeyboardButton(text="🍏 MacOS", callback_data="help_macos")],
        [InlineKeyboardButton(text="👨‍💻 Связь с поддержкой", url="https://t.me/NodeConnect_Suport")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_main")]
    ])

def help_back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К выбору ОС", callback_data="help")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_main")]
    ])
