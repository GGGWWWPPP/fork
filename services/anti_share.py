import os
import time
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Config
MARZBAN_DB_URL = os.getenv("MARZBAN_DB_URL", "mysql+pymysql://marzban:marzban_password@127.0.0.1:3306/marzban")
CHECK_INTERVAL = 60 * 5  # 5 minutes
MAX_IPS_PER_USER = 3

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
engine = create_engine(MARZBAN_DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_and_freeze():
    try:
        with SessionLocal() as session:
            # В Marzban логи IP-адресов обычно лежат в логах ядра или таблице node_usages
            # Упрощенная логика: блокируем юзеров, если их трафик подозрительно велик за короткое время
            # Для реального трекинга IP нужен парсинг access.log от Xray.
            logging.info("Running Anti-Share Check (Placeholder logic for IP counting)...")
            
            # Запрос для получения активных пользователей
            result = session.execute(text("SELECT id, username, status FROM users WHERE status='active'"))
            users = result.fetchall()
            
            for user in users:
                # ЗДЕСЬ ДОЛЖНА БЫТЬ ЛОГИКА ПРОВЕРКИ IP (например через Redis или логи Xray)
                # Представим, что мы нашли > 3 IP для user.username
                active_ips_count = 1 # Заглушка
                
                if active_ips_count > MAX_IPS_PER_USER:
                    logging.warning(f"User {user.username} has {active_ips_count} active IPs. Freezing!")
                    session.execute(
                        text("UPDATE users SET status='disabled', note='Frozen by Anti-Share' WHERE id=:uid"),
                        {"uid": user.id}
                    )
                    session.commit()
    except Exception as e:
        logging.error(f"Error in Anti-Share Watchdog: {e}")

if __name__ == "__main__":
    logging.info("Starting Anti-Share Watchdog...")
    while True:
        check_and_freeze()
        time.sleep(CHECK_INTERVAL)
