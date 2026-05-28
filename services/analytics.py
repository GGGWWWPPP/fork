import os
import matplotlib.pyplot as plt
import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Config
MARZBAN_DB_URL = os.getenv("MARZBAN_DB_URL", "mysql+pymysql://marzban:marzban_password@127.0.0.1:3306/marzban")
engine = create_engine(MARZBAN_DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def generate_mrr_chart():
    try:
        with SessionLocal() as session:
            # We fetch user counts and estimate MRR
            result = session.execute(text("SELECT status, count(*) FROM users GROUP BY status"))
            data = result.fetchall()
            
            stats = {row[0]: row[1] for row in data}
            active = stats.get('active', 0)
            disabled = stats.get('disabled', 0)
            expired = stats.get('expired', 0)
            
            # Estimate MRR (assuming $5 per active user)
            ARPU = 5.0
            MRR = active * ARPU
            
            # Generate Chart
            labels = ['Active', 'Disabled/Frozen', 'Expired (Churn)']
            sizes = [active, disabled, expired]
            colors = ['#2ecc71', '#f1c40f', '#e74c3c']
            
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')  
            
            plt.title(f"NodeConnect Financial Dashboard\nEstimated MRR: ${MRR:.2f} | ARPU: ${ARPU:.2f}")
            
            os.makedirs("/tmp/analytics", exist_ok=True)
            chart_path = "/tmp/analytics/mrr_chart.png"
            plt.savefig(chart_path)
            plt.close()
            print(f"Chart generated at {chart_path}")
            return chart_path
            
    except Exception as e:
        print(f"Analytics Error: {e}")
        return None

if __name__ == "__main__":
    generate_mrr_chart()
