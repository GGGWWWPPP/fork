import sqlite3
import os

db_path = r"C:\Users\User\Pictures\Новая папка (2)\nodeconnect.db"
output_path = r"C:\Users\User\Documents\NodeConnect\init.sql"

if not os.path.exists(db_path):
    print("DB not found")
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get bot tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row['name'] for row in cur.fetchall()]

schema_sql = """
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

"""

with open(output_path, "w", encoding="utf-8") as f:
    f.write("-- NodeConnect DB Migration Dump\n\n")
    f.write(schema_sql)
    f.write("\n")

    for table in tables:
        if table == "sqlite_sequence":
            continue
            
        cur.execute(f"PRAGMA table_info({table});")
        columns = [col['name'] for col in cur.fetchall()]
        
        cur.execute(f"SELECT * FROM {table};")
        rows = cur.fetchall()
        
        if rows:
            print(f"Dumping {len(rows)} rows from {table}")
            f.write(f"-- Data for table {table}\n")
            for row in rows:
                cols_str = ", ".join(columns)
                vals = []
                for i, val in enumerate(row):
                    col_name = columns[i]
                    if val is None:
                        vals.append("NULL")
                    elif isinstance(val, str):
                        escaped_val = val.replace("'", "''")
                        vals.append(f"'{escaped_val}'")
                    elif col_name in ['is_trial_used', 'is_banned', 'accepted_tos', 'is_active']:
                        vals.append("TRUE" if val else "FALSE")
                    else:
                        vals.append(str(val))
                vals_str = ", ".join(vals)
                
                conflict_clause = ""
                if table == "users":
                    conflict_clause = " ON CONFLICT (user_id) DO NOTHING"
                elif table == "subscriptions":
                    conflict_clause = " ON CONFLICT (marzban_username) DO NOTHING"
                    
                f.write(f"INSERT INTO {table} ({cols_str}) VALUES ({vals_str}){conflict_clause};\n")
            f.write("\n")

    f.write("-- Update sequences\n")
    f.write("SELECT setval('subscriptions_id_seq', (SELECT MAX(id) FROM subscriptions)) WHERE EXISTS (SELECT 1 FROM subscriptions);\n")

print(f"Dump written to {output_path}")
