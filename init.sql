-- NodeConnect DB Schema
-- ==========================================
-- Этот файл создаёт все необходимые таблицы.
-- Данные пользователей не включены — они создаются через бота/сайт.
-- ==========================================

-- 1. BOT TABLES
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR,
    email VARCHAR,
    referrer_id BIGINT,
    marzban_username VARCHAR,
    is_trial_used BOOLEAN DEFAULT FALSE,
    is_banned BOOLEAN DEFAULT FALSE,
    accepted_tos BOOLEAN DEFAULT FALSE,
    subscription_end TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    marzban_username VARCHAR UNIQUE,
    name VARCHAR DEFAULT 'Подписка'
);

CREATE TABLE IF NOT EXISTS promo_codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR UNIQUE NOT NULL,
    days INTEGER NOT NULL,
    max_uses INTEGER DEFAULT 1,
    current_uses INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_by BIGINT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS promo_code_usages (
    id SERIAL PRIMARY KEY,
    promo_id INTEGER REFERENCES promo_codes(id),
    user_id BIGINT REFERENCES users(user_id),
    used_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fortune_spins (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    milestone INTEGER NOT NULL,
    prize_days INTEGER NOT NULL,
    spun_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gift_certificates (
    id SERIAL PRIMARY KEY,
    code VARCHAR UNIQUE NOT NULL,
    days INTEGER NOT NULL,
    created_by BIGINT REFERENCES users(user_id),
    redeemed_by BIGINT,
    is_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    redeemed_at TIMESTAMP
);

-- 2. WEBSITE TABLES
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
);

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
);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_web_users_email ON web_users(email);
CREATE INDEX IF NOT EXISTS idx_web_payments_order ON web_payments(order_id);
