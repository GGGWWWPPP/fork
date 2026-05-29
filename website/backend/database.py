import os
import psycopg2
from psycopg2.extras import RealDictCursor
from config import settings
import logging

logger = logging.getLogger(__name__)


def get_db():
    conn = psycopg2.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
    )
    return conn


def init_db():
    """Создание таблиц для веб-части (users, payments)."""
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS web_users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR UNIQUE NOT NULL,
                    password_hash TEXT,
                    marzban_username TEXT,
                    subscription_end BIGINT DEFAULT 0,
                    device_limit INTEGER DEFAULT 0,
                    sub_url TEXT DEFAULT '',
                    plan_type VARCHAR DEFAULT 'standard',
                    token TEXT,
                    referral_code VARCHAR(20) UNIQUE,
                    referred_by_id INTEGER REFERENCES web_users(id),

                    created_at BIGINT DEFAULT 0
                )
            """)
            
            # Миграция: добавление реферальных колонок и поля для пароля
            cur.execute("""
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='web_users' AND column_name='referral_code') THEN
                        ALTER TABLE web_users ADD COLUMN referral_code VARCHAR(20) UNIQUE;
                        ALTER TABLE web_users ADD COLUMN referred_by_id INTEGER REFERENCES web_users(id);
                    END IF;

                END $$;
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS web_payments (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES web_users(id),
                    amount INTEGER,
                    status TEXT DEFAULT 'pending',
                    order_id TEXT UNIQUE,
                    duration_days INTEGER,
                    devices_count INTEGER,
                    plan_type VARCHAR DEFAULT 'standard',
                    created_at BIGINT DEFAULT 0
                )
            """)
        conn.commit()
        conn.close()
        logger.info("Web DB tables initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to init web DB: {e}")


def get_user_by_email(email: str):
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM web_users WHERE email = %s", (email,))
            user = cur.fetchone()
        return dict(user) if user else None
    finally:
        conn.close()


def get_user_by_token(token: str):
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM web_users WHERE token = %s", (token,))
            user = cur.fetchone()
        return dict(user) if user else None
    finally:
        conn.close()


def create_user(email: str, password_hash: str):
    import random
    import string
    import time
    conn = get_db()
    try:
        ref_code = 'NC-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO web_users (email, password_hash, referral_code, created_at) VALUES (%s, %s, %s, %s) ON CONFLICT (email) DO NOTHING",
                (email, password_hash, ref_code, int(time.time())),
            )
        conn.commit()
    finally:
        conn.close()




def update_user_token(email: str, token: str):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE web_users SET token = %s WHERE email = %s", (token, email))
        conn.commit()
    finally:
        conn.close()


def update_user_subscription(
    user_id: int,
    username: str,
    sub_end: int,
    dev_limit: int,
    sub_url: str,
    plan_type: str = "standard",
):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE web_users 
                SET marzban_username = %s, subscription_end = %s, device_limit = %s, 
                    sub_url = %s, plan_type = %s
                WHERE id = %s
            """,
                (username, sub_end, dev_limit, sub_url, plan_type, user_id),
            )
        conn.commit()
    finally:
        conn.close()


def create_payment(
    user_id: int,
    amount: int,
    order_id: str,
    duration_days: int,
    devices_count: int,
    plan_type: str = "standard",
):
    import time
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO web_payments (user_id, amount, status, order_id, duration_days, devices_count, plan_type, created_at)
                VALUES (%s, %s, 'pending', %s, %s, %s, %s, %s)
            """,
                (user_id, amount, order_id, duration_days, devices_count, plan_type, int(time.time())),
            )
        conn.commit()
    finally:
        conn.close()


def get_payment_by_order_id(order_id: str):
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM web_payments WHERE order_id = %s", (order_id,))
            payment = cur.fetchone()
        return dict(payment) if payment else None
    finally:
        conn.close()


def get_user_by_id(user_id: int):
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM web_users WHERE id = %s", (user_id,))
            user = cur.fetchone()
        return dict(user) if user else None
    finally:
        conn.close()


def complete_payment(order_id: str):
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM web_payments WHERE order_id = %s AND status = 'pending' FOR UPDATE", (order_id,))
            payment = cur.fetchone()
            if payment:
                cur.execute("UPDATE web_payments SET status = 'completed' WHERE order_id = %s", (order_id,))
                conn.commit()
                return dict(payment)
        return None
    finally:
        conn.close()


# ==================== FORTUNE WHEEL ====================

def get_bot_user_by_email(email: str):
    """Найти пользователя бота по email (таблица users бота в той же БД)."""
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (email.lower(),))
            user = cur.fetchone()
        return dict(user) if user else None
    finally:
        conn.close()


def get_referral_count(bot_user_id: int) -> int:
    """Посчитать кол-во рефералов пользователя бота."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users WHERE referrer_id = %s", (bot_user_id,))
            return cur.fetchone()[0]
    finally:
        conn.close()


def get_claimed_milestones(bot_user_id: int) -> list:
    """Получить список уже использованных майлстоунов."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT milestone FROM fortune_spins WHERE user_id = %s", (bot_user_id,))
            return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()


def record_fortune_spin(bot_user_id: int, milestone: int, prize_days: int):
    """Записать прокрутку колеса."""
    import time as _time
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO fortune_spins (user_id, milestone, prize_days, spun_at) VALUES (%s, %s, %s, NOW())",
                (bot_user_id, milestone, prize_days)
            )
        conn.commit()
    finally:
        conn.close()


# ==================== ADMIN PANEL ====================

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com")


def is_admin_user(email: str) -> bool:
    return email.lower() == ADMIN_EMAIL.lower()


def admin_get_stats():
    """Статистика для дашборда."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Bot tables (may not exist if bot hasn't run yet)
            def safe_count(query):
                try:
                    cur.execute(query)
                    return cur.fetchone()[0]
                except Exception:
                    conn.rollback()
                    return 0

            bot_users = safe_count("SELECT COUNT(*) FROM users")

            cur.execute("SELECT COUNT(*) FROM web_users")
            web_users = cur.fetchone()[0]

            active_subs = safe_count("SELECT COUNT(*) FROM subscriptions")

            cur.execute("SELECT COUNT(*) FROM web_payments WHERE status = 'completed'")
            completed_payments = cur.fetchone()[0]

            cur.execute("SELECT COALESCE(SUM(amount), 0) FROM web_payments WHERE status = 'completed'")
            total_revenue = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM web_payments WHERE status = 'pending'")
            pending_payments = cur.fetchone()[0]

            active_promos = safe_count("SELECT COUNT(*) FROM promo_codes WHERE is_active = TRUE")
            total_spins = safe_count("SELECT COUNT(*) FROM fortune_spins")
            banned_users = safe_count("SELECT COUNT(*) FROM users WHERE is_banned = TRUE")

        return {
            "bot_users": bot_users,
            "web_users": web_users,
            "active_subs": active_subs,
            "completed_payments": completed_payments,
            "total_revenue": total_revenue,
            "pending_payments": pending_payments,
            "active_promos": active_promos,
            "total_spins": total_spins,
            "banned_users": banned_users,
        }
    finally:
        conn.close()



def admin_get_bot_users(search: str = "", limit: int = 50, offset: int = 0):
    """Получить пользователей бота с поиском."""
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if search:
                cur.execute("""
                    SELECT u.*, 
                        (SELECT COUNT(*) FROM users r WHERE r.referrer_id = u.user_id) as ref_count,
                        (SELECT COUNT(*) FROM subscriptions s WHERE s.user_id = u.user_id) as sub_count
                    FROM users u
                    WHERE u.username ILIKE %s OR CAST(u.user_id AS TEXT) LIKE %s OR u.email ILIKE %s
                    ORDER BY u.user_id DESC LIMIT %s OFFSET %s
                """, (f"%{search}%", f"%{search}%", f"%{search}%", limit, offset))
            else:
                cur.execute("""
                    SELECT u.*, 
                        (SELECT COUNT(*) FROM users r WHERE r.referrer_id = u.user_id) as ref_count,
                        (SELECT COUNT(*) FROM subscriptions s WHERE s.user_id = u.user_id) as sub_count
                    FROM users u
                    ORDER BY u.user_id DESC LIMIT %s OFFSET %s
                """, (limit, offset))
            users = cur.fetchall()

            cur.execute("SELECT COUNT(*) FROM users")
            total = cur.fetchone()["count"]
        return {"users": [dict(u) for u in users], "total": total}
    finally:
        conn.close()


def admin_toggle_ban(user_id: int):
    """Забанить/разбанить пользователя бота."""
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT is_banned FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            if not row:
                return None
            new_status = not row["is_banned"]
            cur.execute("UPDATE users SET is_banned = %s WHERE user_id = %s", (new_status, user_id))
        conn.commit()
        return new_status
    finally:
        conn.close()


def admin_get_web_users(search: str = "", limit: int = 50, offset: int = 0):
    """Получить пользователей сайта."""
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if search:
                cur.execute("""
                    SELECT * FROM web_users 
                    WHERE email ILIKE %s 
                    ORDER BY id DESC LIMIT %s OFFSET %s
                """, (f"%{search}%", limit, offset))
            else:
                cur.execute("SELECT * FROM web_users ORDER BY id DESC LIMIT %s OFFSET %s", (limit, offset))
            users = cur.fetchall()

            cur.execute("SELECT COUNT(*) FROM web_users")
            total = cur.fetchone()["count"]
        return {"users": [dict(u) for u in users], "total": total}
    finally:
        conn.close()



def admin_get_web_payments(limit: int = 50, offset: int = 0, status_filter: str = ""):
    """Получить платежи сайта."""
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            base = """
                SELECT wp.*, wu.email 
                FROM web_payments wp 
                LEFT JOIN web_users wu ON wp.user_id = wu.id
            """
            if status_filter:
                cur.execute(base + " WHERE wp.status = %s ORDER BY wp.id DESC LIMIT %s OFFSET %s",
                            (status_filter, limit, offset))
            else:
                cur.execute(base + " ORDER BY wp.id DESC LIMIT %s OFFSET %s", (limit, offset))
            payments = cur.fetchall()

            cur.execute("SELECT COUNT(*) FROM web_payments")
            total = cur.fetchone()["count"]
        return {"payments": [dict(p) for p in payments], "total": total}
    finally:
        conn.close()


def admin_get_promos():
    """Получить все промокоды."""
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM promo_codes ORDER BY id DESC")
            promos = cur.fetchall()
        return [dict(p) for p in promos]
    finally:
        conn.close()


def admin_create_promo(code: str, days: int, max_uses: int):
    """Создать промокод."""
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO promo_codes (code, days, max_uses, current_uses, is_active, created_at)
                VALUES (%s, %s, %s, 0, TRUE, NOW())
                RETURNING *
            """, (code.upper(), days, max_uses))
            promo = cur.fetchone()
        conn.commit()
        return dict(promo) if promo else None
    finally:
        conn.close()


def admin_delete_promo(promo_id: int):
    """Деактивировать промокод."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE promo_codes SET is_active = FALSE WHERE id = %s", (promo_id,))
        conn.commit()
        return True
    finally:
        conn.close()


def admin_get_fortune_history(limit: int = 50):
    """Получить историю прокруток колеса."""
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT fs.*, u.username, u.email
                FROM fortune_spins fs
                LEFT JOIN users u ON fs.user_id = u.user_id
                ORDER BY fs.id DESC LIMIT %s
            """, (limit,))
            spins = cur.fetchall()
        return [dict(s) for s in spins]
    finally:
        conn.close()
def apply_referral_code(user_id: int, code: str):
    """Применить реферальный код пригласителя."""
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Найти пригласителя
            cur.execute("SELECT id FROM web_users WHERE referral_code = %s", (code.upper(),))
            referrer = cur.fetchone()
            if not referrer:
                return False, "Код не найден"
            
            if referrer['id'] == user_id:
                return False, "Нельзя использовать свой собственный код"
                
            # 2. Проверить не использовал ли уже
            cur.execute("SELECT referred_by_id FROM web_users WHERE id = %s", (user_id,))
            current = cur.fetchone()
            if current and current['referred_by_id']:
                return False, "Вы уже использовали реферальный код"
            
            # 3. Привязать
            cur.execute("UPDATE web_users SET referred_by_id = %s WHERE id = %s", (referrer['id'], user_id))
            conn.commit()
            return True, "Код успешно применен! Скидка 10% активирована."
    finally:
        conn.close()
