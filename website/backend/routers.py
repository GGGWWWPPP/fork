from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel
import time
import uuid
import re
import random
import logging
import bcrypt

from models import AuthRequest, PaymentCreateRequest, ReferralApplyRequest
from database import (
    get_user_by_email,
    get_user_by_token,
    create_user,
    update_user_token,
    update_user_subscription,
    create_payment,
    complete_payment,
    get_user_by_id,
    get_bot_user_by_email,
    get_referral_count,
    get_claimed_milestones,
    record_fortune_spin,
    is_admin_user,
    admin_get_stats,
    admin_get_bot_users,
    admin_toggle_ban,
    admin_get_web_payments,
    admin_get_promos,
    admin_create_promo,
    admin_delete_promo,
    admin_get_fortune_history,
    apply_referral_code,
    admin_get_web_users,
)
from services import create_or_update_vpn_user, create_platega_payment
from database import get_db
from psycopg2.extras import RealDictCursor
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()
# pwd_context removed as we use bcrypt directly

# Pricing table matching frontend
PRICING = {
    "standard": {
        30: {1: 149, 3: 219, 5: 279, 10: 399, 9999: 799},
        60: {1: 249, 3: 319, 5: 399, 10: 599, 9999: 999},
        90: {1: 349, 3: 419, 5: 579, 10: 799, 9999: 1599},
    },
    "white": {30: 399, 60: 699, 90: 849},
}


def verify_password(plain_password, hashed_password):
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def validate_password_strength(password: str):
    if len(password) < 8:
        raise HTTPException(
            status_code=400, detail="Пароль должен быть не менее 8 символов"
        )
    if password.isdigit() or len(set(password)) < 3:
        raise HTTPException(
            status_code=400,
            detail="Пароль слишком простой. Добавьте буквы или спецсимволы.",
        )
    if password.lower() in ["12345678", "password", "qwertyuiop", "123123123"]:
        raise HTTPException(
            status_code=400,
            detail="Данный пароль слишком распространен, выберите другой",
        )
    if not re.search(r"[a-zA-Zа-яА-Я]", password):
        raise HTTPException(
            status_code=400, detail="Пароль должен содержать хотя бы одну букву"
        )


def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.split(" ")[1]
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


# ==================== AUTH ====================


@router.post("/auth/register")
async def register_user(request: AuthRequest):
    email = request.email.lower()

    user = get_user_by_email(email)
    if user:
        raise HTTPException(
            status_code=400, detail="Пользователь с таким Email уже существует"
        )

    validate_password_strength(request.password)
    hashed_pwd = get_password_hash(request.password)

    create_user(email, hashed_pwd)

    token = str(uuid.uuid4())
    update_user_token(email, token)

    return {"status": "success", "access_token": token, "token_type": "bearer"}


@router.post("/auth/login")
async def login_user(request: AuthRequest):
    email = request.email.lower()

    user = get_user_by_email(email)
    if not user or not user["password_hash"]:
        raise HTTPException(status_code=400, detail="Неверный Email или пароль")

    if not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Неверный Email или пароль")

    token = str(uuid.uuid4())
    update_user_token(email, token)

    return {"status": "success", "access_token": token, "token_type": "bearer"}


# ==================== USER DATA ====================


@router.get("/users/me")
async def get_me(user: dict = Depends(get_current_user)):
    current_time = int(time.time())
    has_active = user["subscription_end"] > current_time

    return {
        "email": user["email"],
        "has_active_subscription": has_active,
        "subscription_end": user["subscription_end"],
        "device_limit": user["device_limit"],
        "sub_url": user["sub_url"] if has_active else None,
        "referral_code": user.get("referral_code"),
        "is_referred": bool(user.get("referred_by_id")),
    }


@router.get("/users/me/traffic")
async def get_my_traffic(user: dict = Depends(get_current_user)):
    """Получить статистику трафика пользователя из Marzban."""
    marzban_username = user.get("marzban_username")
    if not marzban_username:
        return {"download": 0, "upload": 0, "online_at": None}

    try:
        from services import get_marzban_token
        from config import settings
        import requests as req

        token = get_marzban_token()
        if not token:
            return {"download": 0, "upload": 0, "online_at": None}

        headers = {"Authorization": f"Bearer {token}"}
        res = req.get(
            f"{settings.marzban_url}/api/user/{marzban_username}",
            headers=headers, timeout=10
        )
        if res.status_code == 200:
            data = res.json()
            return {
                "download": data.get("used_traffic", 0),
                "upload": data.get("used_traffic_up", 0) if "used_traffic_up" in data else 0,
                "online_at": data.get("online_at"),
            }
    except Exception as e:
        logger.warning(f"Traffic fetch error: {e}")

    return {"download": 0, "upload": 0, "online_at": None}


# ==================== REFERRALS ====================


@router.post("/referral/apply")
async def apply_ref_code(
    request: ReferralApplyRequest, user: dict = Depends(get_current_user)
):
    success, message = apply_referral_code(user["id"], request.code)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"status": "success", "message": message}


# ==================== PAYMENTS ====================


@router.post("/payments/create")
async def create_new_payment(
    request: PaymentCreateRequest, user: dict = Depends(get_current_user)
):
    dur = request.duration_days
    dev = request.devices_count
    plan_type = request.plan_type

    if plan_type not in PRICING:
        raise HTTPException(status_code=400, detail="Неверный тип подписки")

    if plan_type == "white":
        if dur not in PRICING["white"]:
            raise HTTPException(
                status_code=400,
                detail="Неверные параметры длительности для белого интернета",
            )
        amount = PRICING["white"][dur]
    else:
        if dur not in PRICING["standard"] or dev not in PRICING["standard"][dur]:
            raise HTTPException(status_code=400, detail="Неверные параметры тарифа")
        amount = PRICING["standard"][dur][dev]

    # Apply referral discount (10%)
    if user.get("referred_by_id"):
        amount = int(amount * 0.9)

    order_id = str(uuid.uuid4())


    create_payment(user["id"], amount, order_id, dur, dev, plan_type)
    payment_url = create_platega_payment(amount, order_id, user["email"])

    return {"payment_url": payment_url, "order_id": order_id}


# ==================== PLATEGA WEBHOOK ====================


@router.post("/webhook/platega")
async def platega_webhook(request: Request):
    """Обработка webhook от Platega после успешной оплаты."""
    try:
        data = await request.json()
        logger.info(f"[WEB] PLATEGA WEBHOOK: {data}")

        status = data.get("status")
        order_id = (
            data.get("payload") or data.get("orderId") or data.get("custom") or ""
        )

        if status not in ["CONFIRMED", "success", "PAID", "paid", "SUCCESS"]:
            logger.info(f"[WEB] Non-success status: {status}")
            return {"status": "ok"}

        # Найти платёж
        payment = complete_payment(order_id)
        if not payment:
            logger.warning(f"[WEB] Payment not found or already completed: {order_id}")
            return {"status": "ok"}

        # Получить пользователя
        user = get_user_by_id(payment["user_id"])
        if not user:
            logger.error(f"[WEB] User not found for payment: {order_id}")
            return {"status": "ok"}

        # Создать или продлить VPN подписку через Marzban
        duration_days = payment["duration_days"]
        devices_count = payment["devices_count"]
        plan_type = payment.get("plan_type", "standard")

        # Генерация username для marzban
        if user.get("marzban_username"):
            marzban_username = user["marzban_username"]
        else:
            marzban_username = f"web_{user['id']}_{int(time.time())}"

        # Вычислить expire
        current_time = int(time.time())
        current_sub_end = user.get("subscription_end", 0)
        if current_sub_end > current_time:
            # Продление: добавить дни к текущей подписке
            new_expire = current_sub_end + (duration_days * 86400)
        else:
            # Новая подписка
            new_expire = current_time + (duration_days * 86400)

        vpn_result = create_or_update_vpn_user(
            marzban_username, new_expire, devices_count
        )

        sub_url = vpn_result.get("key") or vpn_result.get("subscription_url", "")

        update_user_subscription(
            user["id"],
            marzban_username,
            new_expire,
            devices_count,
            sub_url,
            plan_type,
        )

        logger.info(
            f"[WEB] Payment processed: user={user['email']}, days={duration_days}, expires={new_expire}"
        )
        return {"status": "ok"}

    except Exception as e:
        logger.error(f"[WEB] Webhook error: {e}", exc_info=True)
        return {"status": "ok"}


# ==================== FORTUNE WHEEL ====================

MILESTONES = [3, 5, 10, 15, 20, 25, 30]

# Призы и шансы (чем меньше дней — тем выше шанс)
FORTUNE_PRIZES = [
    {"days": 1,  "weight": 35, "label": "1 день"},
    {"days": 3,  "weight": 25, "label": "3 дня"},
    {"days": 5,  "weight": 18, "label": "5 дней"},
    {"days": 8,  "weight": 12, "label": "8 дней"},
    {"days": 15, "weight": 7,  "label": "15 дней"},
    {"days": 30, "weight": 3,  "label": "30 дней"},
]


def spin_wheel() -> dict:
    """Выбрать приз с учётом весов."""
    weights = [p["weight"] for p in FORTUNE_PRIZES]
    return random.choices(FORTUNE_PRIZES, weights=weights, k=1)[0]


@router.get("/fortune/status")
async def fortune_status(user: dict = Depends(get_current_user)):
    """Получить статус колеса фортуны: кол-во рефералов и доступные прокрутки."""
    bot_user = get_bot_user_by_email(user["email"])
    if not bot_user:
        return {
            "referral_count": 0,
            "milestones": MILESTONES,
            "available_spins": [],
            "claimed": [],
            "linked": False
        }
    
    ref_count = get_referral_count(bot_user["user_id"])
    claimed = get_claimed_milestones(bot_user["user_id"])
    
    available = [m for m in MILESTONES if m <= ref_count and m not in claimed]
    
    return {
        "referral_count": ref_count,
        "milestones": MILESTONES,
        "available_spins": available,
        "claimed": claimed,
        "linked": True,
        "prizes": [{"days": p["days"], "label": p["label"]} for p in FORTUNE_PRIZES]
    }


@router.post("/fortune/spin")
async def fortune_spin(request: Request, user: dict = Depends(get_current_user)):
    """Прокрутить колесо фортуны для достигнутого майлстоуна."""
    data = await request.json()
    milestone = data.get("milestone")
    
    if milestone not in MILESTONES:
        raise HTTPException(status_code=400, detail="Неверный майлстоун")
    
    bot_user = get_bot_user_by_email(user["email"])
    if not bot_user:
        raise HTTPException(status_code=400, detail="Аккаунт не привязан к боту")
    
    ref_count = get_referral_count(bot_user["user_id"])
    if ref_count < milestone:
        raise HTTPException(status_code=400, detail="Недостаточно рефералов")
    
    claimed = get_claimed_milestones(bot_user["user_id"])
    if milestone in claimed:
        raise HTTPException(status_code=400, detail="Этот майлстоун уже использован")
    
    # Крутим!
    prize = spin_wheel()
    
    # Добавляем дни через Marzban (если есть подписка на сайте)
    if user.get("marzban_username") and user.get("subscription_end", 0) > int(time.time()):
        try:
            current_time = int(time.time())
            new_expire = user["subscription_end"] + (prize["days"] * 86400)
            create_or_update_vpn_user(user["marzban_username"], new_expire, user.get("device_limit", 1))
            update_user_subscription(
                user["id"], user["marzban_username"], new_expire,
                user.get("device_limit", 1), user.get("sub_url", ""),
                user.get("plan_type", "standard")
            )
        except Exception as e:
            logger.error(f"Fortune wheel Marzban error: {e}")
    
    # Записываем прокрутку
    record_fortune_spin(bot_user["user_id"], milestone, prize["days"])
    
    return {
        "prize_days": prize["days"],
        "prize_label": prize["label"],
        "milestone": milestone
    }


# ==================== ADMIN PANEL API ====================

def require_admin(user: dict):
    """Check if current user is admin."""
    if not is_admin_user(user.get("email", "")):
        raise HTTPException(status_code=403, detail="Доступ запрещён")


@router.get("/admin/check")
async def admin_check(user: dict = Depends(get_current_user)):
    return {"is_admin": is_admin_user(user.get("email", ""))}


@router.get("/admin/stats")
async def admin_stats_endpoint(user: dict = Depends(get_current_user)):
    require_admin(user)
    return admin_get_stats()


@router.get("/admin/users")
async def admin_users_endpoint(search: str = "", limit: int = 50, offset: int = 0, user: dict = Depends(get_current_user)):
    require_admin(user)
    try:
        return admin_get_bot_users(search, limit, offset)
    except Exception as e:
        logger.warning(f"Bot users table may not exist: {e}")
        return {"users": [], "total": 0}


@router.get("/admin/web-users")
async def admin_web_users_endpoint(search: str = "", limit: int = 50, offset: int = 0, user: dict = Depends(get_current_user)):
    require_admin(user)
    return admin_get_web_users(search, limit, offset)



@router.post("/admin/users/{user_id}/ban")
async def admin_ban_endpoint(user_id: int, user: dict = Depends(get_current_user)):
    require_admin(user)
    result = admin_toggle_ban(user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return {"is_banned": result}


@router.get("/admin/payments")
async def admin_payments_endpoint(limit: int = 50, offset: int = 0, status: str = "", user: dict = Depends(get_current_user)):
    require_admin(user)
    return admin_get_web_payments(limit, offset, status)


@router.get("/admin/promos")
async def admin_promos_endpoint(user: dict = Depends(get_current_user)):
    require_admin(user)
    return admin_get_promos()


@router.post("/admin/promos")
async def admin_create_promo_endpoint(request: Request, user: dict = Depends(get_current_user)):
    require_admin(user)
    data = await request.json()
    code = data.get("code", "").strip()
    days = data.get("days", 0)
    max_uses = data.get("max_uses", 1)
    if not code or days < 1:
        raise HTTPException(status_code=400, detail="Неверные данные")
    promo = admin_create_promo(code, days, max_uses)
    if not promo:
        raise HTTPException(status_code=400, detail="Ошибка создания")
    return promo


@router.delete("/admin/promos/{promo_id}")
async def admin_delete_promo_endpoint(promo_id: int, user: dict = Depends(get_current_user)):
    require_admin(user)
    admin_delete_promo(promo_id)
    return {"status": "ok"}


@router.get("/admin/fortune-history")
async def admin_fortune_history_endpoint(user: dict = Depends(get_current_user)):
    require_admin(user)
    return admin_get_fortune_history()


# ==================== GIFT CERTIFICATES ====================


class GiftCreateRequest(BaseModel):
    days: int


class GiftRedeemRequest(BaseModel):
    code: str


@router.post("/gifts/create")
async def create_gift(request: GiftCreateRequest, user: dict = Depends(get_current_user)):
    if request.days < 1 or request.days > 90:
        raise HTTPException(status_code=400, detail="Дни должны быть от 1 до 90")

    if not user.get("subscription_end") or user["subscription_end"] < int(time.time()):
        raise HTTPException(status_code=400, detail="Нужна активная подписка для создания подарка")

    import string
    import random
    code = 'GIFT-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    conn = get_db()
    try:
        with conn.cursor() as cur:
            # created_by = None, т.к. web_users.id не является FK для users(user_id)
            cur.execute(
                "INSERT INTO gift_certificates (code, days, created_by, created_at) VALUES (%s, %s, %s, NOW()) RETURNING id, code, days",
                (code, request.days, None)
            )
            result = cur.fetchone()
            conn.commit()
            return {"code": result[1], "days": result[2]}
    except Exception as e:
        conn.rollback()
        logger.error(f"Gift create error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка создания подарка")
    finally:
        conn.close()


@router.post("/gifts/redeem")
async def redeem_gift(request: GiftRedeemRequest, user: dict = Depends(get_current_user)):
    code = request.code.strip().upper()

    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM gift_certificates WHERE code = %s AND is_used = FALSE", (code,))
            gift = cur.fetchone()

            if not gift:
                raise HTTPException(status_code=404, detail="Подарочный код не найден или уже использован")

            marzban_username = user.get("marzban_username")
            if not marzban_username:
                raise HTTPException(status_code=400, detail="Нет активной подписки")

            # Add days via Marzban
            from services import get_marzban_token
            marzban_token = get_marzban_token()
            if marzban_token:
                import requests as req
                headers = {"Authorization": f"Bearer {marzban_token}"}

                # Get current user expire
                res = req.get(f"{settings.marzban_url}/api/user/{marzban_username}", headers=headers, timeout=10)
                if res.status_code == 200:
                    mdata = res.json()
                    current_expire = mdata.get("expire", 0) or 0
                    now = int(time.time())
                    if current_expire < now:
                        new_expire = now + (gift["days"] * 86400)
                    else:
                        new_expire = current_expire + (gift["days"] * 86400)

                    req.put(
                        f"{settings.marzban_url}/api/user/{marzban_username}",
                        headers=headers, json={"expire": new_expire}, timeout=10
                    )

                    # Update subscription_end in web_users
                    cur.execute("UPDATE web_users SET subscription_end = %s WHERE id = %s", (new_expire, user["id"]))

            # Mark gift as used
            cur.execute(
                "UPDATE gift_certificates SET is_used = TRUE, redeemed_by = %s, redeemed_at = NOW() WHERE id = %s",
                (user["id"], gift["id"])
            )
            conn.commit()
            return {"days": gift["days"], "message": f"+{gift['days']} дней добавлено!"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Gift redeem error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка активации подарка")
    finally:
        conn.close()
