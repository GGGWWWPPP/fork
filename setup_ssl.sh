#!/bin/bash
# ==================================================
# Скрипт автоматической установки SSL (Let's Encrypt)
# ==================================================
set -e

DOMAIN="nodeconnect.tech"
EXTRA_DOMAIN="paysell.nodeconnect-sub.tech"

echo "🔐 Начинаем установку SSL сертификатов для $DOMAIN..."

# 1. Установка certbot если его нет
if ! command -v certbot &> /dev/null; then
    echo "📦 Установка certbot..."
    apt update && apt install -y certbot
fi

# 2. Остановка Nginx для освобождения порта 80
echo "Stop Docker services to free port 80..."
docker-compose down || true

# 3. Запрос сертификата
echo "📡 Запрос сертификата у Let's Encrypt..."
certbot certonly --standalone --non-interactive --agree-tos --email sergejvoronin555@gmail.com -d $DOMAIN -d $EXTRA_DOMAIN

# 4. Копирование в папку проекта
echo "📂 Копирование сертификатов в nginx/ssl..."
mkdir -p nginx/ssl
cp -L /etc/letsencrypt/live/$DOMAIN/fullchain.pem nginx/ssl/
cp -L /etc/letsencrypt/live/$DOMAIN/privkey.pem nginx/ssl/

echo "✅ Сертификаты скопированы."

# 5. Перезапуск проекта
echo "🚀 Запуск проекта..."
./install.sh

echo ""
echo "=================================================="
echo "🎉 SSL сертификаты успешно установлены!"
echo "Теперь сайт должен открываться по https://$DOMAIN"
echo "=================================================="
