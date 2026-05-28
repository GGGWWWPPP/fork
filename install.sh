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

# 2.5 Клонирование репозитория
echo "📥 Скачиваем файлы проекта NodeConnect..."
apt install -y git
if [ -d "/opt/NodeConnect" ]; then
    echo "⚠️ Папка /opt/NodeConnect уже существует. Обновляем..."
    cd /opt/NodeConnect
    git pull
else
    git clone https://github.com/GGGWWWPPP/fork.git /opt/NodeConnect
    cd /opt/NodeConnect
fi

# 3. Создаём SSL сертификаты (self-signed для начала)
echo "🔐 Настраиваем SSL сертификаты..."
mkdir -p nginx/ssl
if [ ! -f nginx/ssl/fullchain.pem ]; then
    echo "Генерируем self-signed сертификат (замени на Let's Encrypt позже)..."
    openssl req -x509 -newkey rsa:2048 \
        -keyout nginx/ssl/privkey.pem \
        -out nginx/ssl/fullchain.pem \
        -days 365 -nodes -subj "/CN=localhost"
fi

# 4. Пошаговый Интерактивный Мастер Установки
echo "==================================================="
echo "⚙️  МАСТЕР НАСТРОЙКИ NODECONNECT"
echo "==================================================="
echo "Пожалуйста, ответьте на несколько вопросов для настройки сервера."
echo ""

read -p "🔹 [1/5] Введите ТОКЕН Telegram-бота: " BOT_TOKEN </dev/tty
while [ -z "$BOT_TOKEN" ]; do
    read -p "Токен не может быть пустым. Введите ТОКЕН Telegram-бота: " BOT_TOKEN </dev/tty
done

read -p "🔹 [2/5] Введите ваш TELEGRAM ID (для прав администратора): " ADMIN_ID </dev/tty
while [ -z "$ADMIN_ID" ]; do
    read -p "ID не может быть пустым. Введите ваш TELEGRAM ID: " ADMIN_ID </dev/tty
done

read -p "🔹 [3/5] Введите домен для АДМИН-ПАНЕЛИ (например, admin.vpn.com): " PANEL_DOMAIN </dev/tty
while [ -z "$PANEL_DOMAIN" ]; do
    read -p "Домен не может быть пустым. Введите домен АДМИН-ПАНЕЛИ: " PANEL_DOMAIN </dev/tty
done

read -p "🔹 [4/5] Введите домен для САЙТА ПРОДАЖ (например, vpn.com): " SITE_DOMAIN </dev/tty
while [ -z "$SITE_DOMAIN" ]; do
    read -p "Домен не может быть пустым. Введите домен САЙТА ПРОДАЖ: " SITE_DOMAIN </dev/tty
done

read -p "🔹 [5/5] Введите SUB-домен для ПОДПИСОК клиентов (например, sub.vpn.com): " SUB_DOMAIN </dev/tty
while [ -z "$SUB_DOMAIN" ]; do
    read -p "Домен не может быть пустым. Введите SUB-домен для ПОДПИСОК: " SUB_DOMAIN </dev/tty
done

echo ""
echo "🔐 Генерация безопасных паролей для баз данных..."
DB_PASS=$(openssl rand -hex 16)
MARZBAN_DB_PASS=$(openssl rand -hex 16)

echo "📝 Создание конфигурационного файла .env..."
cat <<EOF > .env
# ==========================================
# NodeConnect — Автосгенерированная конфигурация
# ==========================================

# Telegram бот
BOT_TOKEN="${BOT_TOKEN}"
ADMIN_IDS=[${ADMIN_ID}]

# Домены
SITE_DOMAIN="${SITE_DOMAIN}"
PANEL_DOMAIN="${PANEL_DOMAIN}"
SUB_DOMAIN="${SUB_DOMAIN}"

# NodeConnect Core (Marzban)
MARZBAN_URL="https://${PANEL_DOMAIN}"
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

echo "✅ Конфигурация успешно сохранена!"

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
