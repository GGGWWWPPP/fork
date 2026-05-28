#!/bin/bash
set -e

# ===============================================
# NodeConnect — установка бота + сайта на дедике
# ===============================================

echo "=== 🚀 Начало установки NodeConnect ==="

# 1. Обновление системы
echo "📦 Обновляем пакеты системы..."
apt update && apt upgrade -y

# 2. Установка Docker
echo "🐳 Устанавливаем Docker..."
apt install -y curl
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
fi

if ! command -v docker-compose &> /dev/null; then
    apt install -y docker-compose-plugin docker-compose
fi

# 3. Создаём SSL сертификаты (self-signed для начала)
echo "🔐 Настраиваем SSL сертификаты..."
mkdir -p nginx/ssl
if [ ! -f nginx/ssl/fullchain.pem ]; then
    echo "Генерируем self-signed сертификат (замени на Let's Encrypt позже)..."
    openssl req -x509 -newkey rsa:2048 \
        -keyout nginx/ssl/privkey.pem \
        -out nginx/ssl/fullchain.pem \
        -days 365 -nodes \
        -subj "/CN=nodeconnect.tech"
# 4. Обработка аргументов или интерактивный ввод
BOT_TOKEN=""
ADMIN_ID=""
DOMAIN_NAME=""

while getopts t:a:d: flag
do
    case "${flag}" in
        t) BOT_TOKEN=${OPTARG};;
        a) ADMIN_ID=${OPTARG};;
        d) DOMAIN_NAME=${OPTARG};;
    esac
done

if [ ! -f .env ]; then
    echo "⚙️  Настройка конфигурации (.env)..."
    
    if [ -z "$BOT_TOKEN" ]; then
        read -p "🔹 Введите токен Telegram-бота: " BOT_TOKEN
    fi
    if [ -z "$ADMIN_ID" ]; then
        read -p "🔹 Введите ваш Telegram ID: " ADMIN_ID
    fi
    if [ -z "$DOMAIN_NAME" ]; then
        read -p "🔹 Введите домен (например, vpn.com): " DOMAIN_NAME
    fi

    echo "🔐 Генерация безопасных паролей..."
    DB_PASS=$(openssl rand -hex 16)
    MARZBAN_DB_PASS=$(openssl rand -hex 16)

    cat <<EOF > .env
# ==========================================
# NodeConnect — Автосгенерированная конфигурация
# ==========================================

# Telegram бот
BOT_TOKEN="${BOT_TOKEN}"
ADMIN_IDS=[${ADMIN_ID}]

# Marzban
MARZBAN_URL="https://admin.${DOMAIN_NAME}"
MARZBAN_USERNAME="admin"
MARZBAN_PASSWORD="${MARZBAN_DB_PASS}"
MARZBAN_DB_URL="mysql+aiomysql://marzban:${MARZBAN_DB_PASS}@mariadb:3306/marzban"

# PostgreSQL (Бот/Сайт)
DB_URL="postgresql+asyncpg://nodeconnect:${DB_PASS}@postgres:5432/nodeconnect"
POSTGRES_DB=nodeconnect
POSTGRES_USER=nodeconnect
POSTGRES_PASSWORD=${DB_PASS}
DB_HOST=postgres
DB_PORT=5432
DB_NAME=nodeconnect
DB_USER=nodeconnect
DB_PASSWORD=${DB_PASS}
EOF
    echo "✅ Файл .env успешно создан!"
fi

# 5. Запуск всех сервисов (PostgreSQL поднимется и автоматически загрузит init.sql)
echo ""
echo "🔧 Останавливаем старые контейнеры (если есть)..."
docker-compose down 2>/dev/null || true

echo "🔧 Запускаем новые сервисы..."
docker-compose up -d --build

echo ""
echo "=== ✅ Установка завершена! ==="
echo ""
echo "📌 Сервисы:"
echo "   🌐 Сайт:     http://YOUR_IP (или https://nodeconnect.tech после SSL)"
echo "   🤖 Бот:      Запущен (Telegram polling)"
echo "   🗄  БД:       PostgreSQL на порту 5432 (только localhost)"
echo ""
echo "📋 Полезные команды:"
echo "   docker-compose logs -f          — все логи"
echo "   docker-compose logs -f bot      — логи бота"
echo "   docker-compose logs -f website  — логи сайта"
echo "   docker-compose restart bot      — перезапуск бота"
echo "   docker-compose restart website  — перезапуск сайта"
echo ""
echo "🔒 Для Let's Encrypt SSL:"
echo "   apt install certbot"
echo "   certbot certonly --standalone -d nodeconnect.tech"
echo "   cp /etc/letsencrypt/live/nodeconnect.tech/fullchain.pem nginx/ssl/"
echo "   cp /etc/letsencrypt/live/nodeconnect.tech/privkey.pem nginx/ssl/"
echo "   docker-compose restart nginx"
