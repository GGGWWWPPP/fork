-- NodeConnect DB Migration Dump


-- ==========================================
-- NodeConnect Database Schema (PostgreSQL)
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


-- Data for table users
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (6473026404, 'hagaromoj', NULL, 'user_6473026404', TRUE, FALSE, TRUE, '2026-04-16 08:57:21.211905') ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (8340496714, 'NodeConnect_Suport', NULL, 'user_8340496714', TRUE, FALSE, TRUE, '2026-04-16 04:45:15.640634') ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (1081151348, 'hqdeshka', NULL, 'user_1081151348', TRUE, FALSE, TRUE, '2026-04-18 08:57:16.522665') ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (1427841891, 'parastenzia', NULL, 'user_1427841891', TRUE, FALSE, TRUE, '2026-04-16 08:13:48.193057') ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (887184064, NULL, NULL, 'user_887184064', TRUE, FALSE, TRUE, '2026-04-16 08:23:25.681626') ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (944838048, 'Msss22123', NULL, 'user_944838048', TRUE, FALSE, TRUE, '2026-04-16 08:26:38.923897') ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (7548459412, 'MaseratiMansory', 1081151348, 'user_7548459412', TRUE, FALSE, TRUE, '2026-04-16 09:04:12.729259') ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (1186179998, 'TOXA4560', 1081151348, NULL, FALSE, FALSE, FALSE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (1917141009, 'Rodia65', NULL, 'user_1917141009', TRUE, FALSE, TRUE, '2026-04-16 10:23:59.210476') ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (6080554630, 'Nobroes', NULL, 'user_6080554630', TRUE, FALSE, TRUE, '2026-04-16 10:37:13.499570') ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (5848828200, 'yrodebaniy', 1081151348, NULL, FALSE, FALSE, TRUE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (1170734324, NULL, NULL, NULL, FALSE, FALSE, TRUE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (2114998080, 'C4REFREE', NULL, 'user_2114998080', TRUE, FALSE, TRUE, '2026-04-16 19:36:07.998121') ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (2062027933, NULL, NULL, NULL, TRUE, FALSE, TRUE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (1911255806, 'evgen_kobi', NULL, 'user_1911255806', TRUE, FALSE, TRUE, '2026-04-16 21:29:45.939235') ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (996106352, 'SquBnonono', NULL, 'user_996106352', TRUE, FALSE, TRUE, '2026-04-17 05:41:56.221376') ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (8280589305, 'merjiu', NULL, NULL, FALSE, FALSE, FALSE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (1161294101, NULL, NULL, 'user_1161294101', TRUE, FALSE, TRUE, '2026-04-17 07:39:25.999967') ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (5180480029, 'OgnaliadeArgon', NULL, NULL, FALSE, FALSE, FALSE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (1596364103, 'Sisyoonok', NULL, NULL, TRUE, FALSE, TRUE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (7120858829, 'Gerzel_Mantaew', NULL, 'user_7120858829', TRUE, FALSE, TRUE, '2026-04-17 15:25:25.413230') ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (1394034854, 'plategabottest', NULL, NULL, FALSE, FALSE, TRUE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (7578496986, 'arinix2280', NULL, 'user_7578496986', TRUE, FALSE, TRUE, '2026-04-17 17:15:48.661669') ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (5103566821, 'nad_yuusha', NULL, NULL, TRUE, FALSE, TRUE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (6684484315, 'MyCode_23512', 1081151348, 'user_6684484315', TRUE, FALSE, TRUE, '2026-04-18 01:43:12.679863') ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (8372114720, 'kxkhcd', NULL, NULL, FALSE, FALSE, TRUE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (5702587446, 'misispeni', NULL, NULL, FALSE, FALSE, TRUE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (8645867804, 'Gereneda', NULL, 'user_8645867804', TRUE, FALSE, TRUE, '2026-04-18 11:27:01.896638') ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (2028642590, 'O_pupup', NULL, NULL, TRUE, FALSE, FALSE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (8618921278, 'ComplSus', NULL, NULL, FALSE, FALSE, FALSE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (6471839117, 'neywhs1', NULL, NULL, TRUE, FALSE, FALSE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (7087692625, 'Rojy01', NULL, NULL, TRUE, FALSE, FALSE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (7899921736, NULL, NULL, NULL, FALSE, FALSE, FALSE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (6877046799, NULL, NULL, NULL, TRUE, FALSE, FALSE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (7517637813, 'Samiiikaaa', NULL, NULL, TRUE, FALSE, FALSE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (7686339084, 'nellwwex', NULL, NULL, TRUE, FALSE, FALSE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (6862651882, 'ammmmiir', NULL, NULL, FALSE, FALSE, FALSE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (8218794162, 'Dan_27rus', NULL, NULL, TRUE, FALSE, FALSE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (6716043213, 'naturalAiMLord', NULL, NULL, FALSE, FALSE, FALSE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (599606550, 'Aleks1701', NULL, NULL, FALSE, FALSE, FALSE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (7378100732, 'Clonazepam_C15H10ClN3O3', NULL, NULL, FALSE, FALSE, FALSE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (1071456478, 'HeTvoy', NULL, NULL, TRUE, FALSE, FALSE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (8653553965, NULL, NULL, NULL, TRUE, FALSE, FALSE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (396396419, 'kizzn', NULL, NULL, FALSE, FALSE, FALSE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (6014176847, 'KsuGoHard_00', NULL, NULL, TRUE, FALSE, FALSE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (7011461526, NULL, NULL, NULL, TRUE, FALSE, FALSE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (5486248600, 'danchantix', NULL, NULL, TRUE, FALSE, FALSE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (5950538389, 'ERROR899', NULL, NULL, FALSE, FALSE, FALSE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (6694647819, 'qpwirtyx_05', NULL, NULL, TRUE, FALSE, FALSE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (2011938742, 'nastychka52', NULL, NULL, FALSE, FALSE, FALSE, NULL) ON CONFLICT (user_id) DO NOTHING;
INSERT INTO users (user_id, username, referrer_id, marzban_username, is_trial_used, is_banned, accepted_tos, subscription_end) VALUES (6696195572, 'bse_valit32', NULL, NULL, TRUE, FALSE, FALSE, NULL) ON CONFLICT (user_id) DO NOTHING;

-- Data for table subscriptions
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (1, 6473026404, 'user_6473026404', 'Подписка №1') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (2, 8340496714, 'user_8340496714', 'Подписка №1') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (3, 1081151348, 'user_1081151348', 'Подписка №1') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (4, 1427841891, 'user_1427841891', 'Подписка №1') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (5, 887184064, 'user_887184064', 'Подписка №1') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (6, 944838048, 'user_944838048', 'Подписка №1') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (7, 7548459412, 'user_7548459412', 'Подписка №1') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (8, 1917141009, 'user_1917141009', 'Подписка №1') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (9, 6080554630, 'user_6080554630', 'Подписка №1') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (10, 2114998080, 'user_2114998080', 'Подписка №1') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (11, 1911255806, 'user_1911255806', 'Подписка №1') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (12, 996106352, 'user_996106352', 'Подписка №1') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (13, 1161294101, 'user_1161294101', 'Подписка №1') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (14, 7120858829, 'user_7120858829', 'Подписка №1') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (15, 7578496986, 'user_7578496986', 'Подписка №1') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (16, 6684484315, 'user_6684484315', 'Подписка №1') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (17, 8645867804, 'user_8645867804', 'Подписка №1') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (18, 2028642590, 'user_2028642590_trial', 'Trial (3 Дня)') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (19, 5103566821, 'user_5103566821_trial', 'Trial (3 Дня)') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (20, 6471839117, 'user_6471839117_trial', 'Trial (3 Дня)') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (21, 6473026404, 'user_6473026404_2_1776395330', 'Подписка №2') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (22, 6473026404, 'user_6473026404_3_1776401125', 'Подписка №3') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (23, 6473026404, 'user_6473026404_4_1776401237', 'Подписка №4') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (24, 6473026404, 'user_6473026404_5_1776401369', 'Подписка №5') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (25, 6473026404, 'user_6473026404_6_1776401522', 'Подписка №6') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (26, 7087692625, 'user_7087692625_trial', 'Trial (3 Дня)') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (27, 1596364103, 'user_1596364103_trial', 'Trial (3 Дня)') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (28, 6877046799, 'user_6877046799_trial', 'Trial (3 Дня)') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (29, 7517637813, 'user_7517637813_trial', 'Trial (3 Дня)') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (30, 7686339084, 'user_7686339084_trial', 'Trial (3 Дня)') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (31, 8218794162, 'user_8218794162_trial', 'Trial (3 Дня)') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (32, 1071456478, 'user_1071456478_trial', 'Trial (3 Дня)') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (33, 8653553965, 'user_8653553965_trial', 'Trial (3 Дня)') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (34, 6014176847, 'user_6014176847_trial', 'Trial (3 Дня)') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (35, 7011461526, 'user_7011461526_trial', 'Trial (3 Дня)') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (36, 2062027933, 'user_2062027933_trial', 'Trial (3 Дня)') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (37, 5486248600, 'user_5486248600_trial', 'Trial (3 Дня)') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (38, 2062027933, 'user_2062027933_2_1777704295', 'Подписка №2') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (39, 6694647819, 'user_6694647819_trial', 'Trial (3 Дня)') ON CONFLICT (marzban_username) DO NOTHING;
INSERT INTO subscriptions (id, user_id, marzban_username, name) VALUES (40, 6696195572, 'user_6696195572_trial', 'Trial (3 Дня)') ON CONFLICT (marzban_username) DO NOTHING;

-- Update sequences
SELECT setval('subscriptions_id_seq', (SELECT MAX(id) FROM subscriptions)) WHERE EXISTS (SELECT 1 FROM subscriptions);
