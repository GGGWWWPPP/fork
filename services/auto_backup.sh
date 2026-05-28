#!/bin/bash
# ===============================================
# Auto-Backup Database to Telegram
# ===============================================

BOT_TOKEN="${1:-YOUR_BOT_TOKEN}"
ADMIN_ID="${2:-YOUR_ADMIN_ID}"

DATE=$(date +"%Y-%m-%d_%H-%M")
BACKUP_DIR="/tmp/nodeconnect_backups"
ARCHIVE_NAME="backup_nodeconnect_${DATE}.tar.gz"
MARZBAN_DB="marzban_dump_${DATE}.sql"
POSTGRES_DB="postgres_dump_${DATE}.sql"

mkdir -p $BACKUP_DIR
cd $BACKUP_DIR

echo "📦 Создание дампа MariaDB (Marzban)..."
docker exec nodeconnect-mariadb-1 /usr/bin/mysqldump -u marzban -pmarzban_password marzban > $MARZBAN_DB

echo "📦 Создание дампа PostgreSQL (Bot)..."
docker exec nodeconnect-postgres-1 pg_dump -U nodeconnect nodeconnect > $POSTGRES_DB

echo "🗜 Архивация дампов..."
tar -czf $ARCHIVE_NAME $MARZBAN_DB $POSTGRES_DB
rm $MARZBAN_DB $POSTGRES_DB

echo "🚀 Отправка в Telegram..."
curl -F document=@"$ARCHIVE_NAME" "https://api.telegram.org/bot${BOT_TOKEN}/sendDocument?chat_id=${ADMIN_ID}&caption=📦 Автоматический бэкап баз данных NodeConnect от ${DATE}"

echo "🧹 Очистка временных файлов..."
rm $ARCHIVE_NAME

echo "✅ Бэкап успешно отправлен!"
