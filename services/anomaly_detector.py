import os
import time
import logging
import random
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Config
MARZBAN_DB_URL = os.getenv("MARZBAN_DB_URL", "mysql+pymysql://marzban:marzban_password@127.0.0.1:3306/marzban")
CHECK_INTERVAL = 60 * 60  # 1 hour
ANOMALY_THRESHOLD_GB = 50 # If user uses > 50 GB in 1 hour, throttle them

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
engine = create_engine(MARZBAN_DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_for_anomalies():
    try:
        with SessionLocal() as session:
            logging.info("Running AI Anomaly Detector (Torrent/DDoS check)...")
            # In a real AI system, we would query the node_usages table to get hourly deltas
            # For this MVP, we simulate anomaly detection
            
            result = session.execute(text("SELECT id, username, used_traffic, status FROM users WHERE status='active'"))
            users = result.fetchall()
            
            for user in users:
                # Simulating checking previous hour's traffic
                hourly_usage_gb = random.uniform(0, 1) # Placeholder: 0 to 1 GB normally
                
                # Assume we detected an anomaly (e.g. 55 GB in 1 hour)
                # hourly_usage_gb = 55.0
                
                if hourly_usage_gb > ANOMALY_THRESHOLD_GB:
                    logging.warning(f"🚨 Anomaly Detected! User {user.username} downloaded {hourly_usage_gb:.1f} GB in 1 hour. Throttling speed!")
                    # To throttle in Marzban/Xray without banning: 
                    # We can set a daily data limit that resets, or apply a specific limited proxy profile
                    session.execute(
                        text("UPDATE users SET data_limit_reset_strategy='day', note='Throttled by AI Anomaly Detector' WHERE id=:uid"),
                        {"uid": user.id}
                    )
                    session.commit()
    except Exception as e:
        logging.error(f"Error in Anomaly Detector: {e}")

if __name__ == "__main__":
    logging.info("Starting AI Anomaly Detector Daemon...")
    while True:
        check_for_anomalies()
        time.sleep(CHECK_INTERVAL)
