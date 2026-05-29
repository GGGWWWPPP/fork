#!/bin/bash
set -e

# ══════════════════════════════════════════════════════════════
# NodeConnect — Полная установка в одну команду
# Всё, что нужно — ответить на вопросы мастера.
# Поддержка: Ubuntu 20.04+ / Debian 11+
# ══════════════════════════════════════════════════════════════

R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'; C='\033[0;36m'; B='\033[1;37m'; N='\033[0m'
ok()   { echo -e "${G}[✓]${N} $1"; }
warn() { echo -e "${Y}[!]${N} $1"; }
err()  { echo -e "${R}[✗]${N} $1"; }

# Проверка root
if [ "$EUID" -ne 0 ]; then
    err "Запустите скрипт от root: sudo bash install.sh"
    exit 1
fi

banner() {
  echo ""
  echo -e "${C}╔══════════════════════════════════════════════════╗${N}"
  echo -e "${C}║${B}        🚀 NodeConnect — Мастер Установки         ${C}║${N}"
  echo -e "${C}║${N}     Панель + Бот + Сайт + SSL — всё сразу       ${C}║${N}"
  echo -e "${C}╚══════════════════════════════════════════════════╝${N}"
  echo ""
}

# ─────────────────────────────────────────────
# Функция: обязательный ввод
# ─────────────────────────────────────────────
ask_required() {
    local prompt="$1"
    local var=""
    while [ -z "$var" ]; do
        read -rp "$(echo -e "${C}${prompt}${N}: ")" var </dev/tty
        [ -z "$var" ] && warn "Это поле обязательно. Попробуйте ещё раз."
    done
    echo "$var"
}

# ─────────────────────────────────────────────
# Функция: опциональный ввод с default
# ─────────────────────────────────────────────
ask_optional() {
    local prompt="$1"
    local default="$2"
    local var=""
    read -rp "$(echo -e "${C}${prompt}${N} [${default}]: ")" var </dev/tty
    echo "${var:-$default}"
}

# ─────────────────────────────────────────────
# Функция: секретный ввод (звёздочки)
# ─────────────────────────────────────────────
ask_secret() {
    local prompt="$1"
    local var=""
    while [ -z "$var" ]; do
        read -rsp "$(echo -e "${C}${prompt}${N}: ")" var </dev/tty
        echo ""
        [ -z "$var" ] && warn "Это поле обязательно."
    done
    echo "$var"
}

banner

# ═══════════════════════════════════════════════
# ЭТАП 1: СИСТЕМНЫЕ ЗАВИСИМОСТИ
# ═══════════════════════════════════════════════
echo -e "${B}═══ Этап 1/6: Установка системных зависимостей ═══${N}"

echo "📦 Обновляем пакеты..."
apt update && apt upgrade -y

echo "🐳 Устанавливаем Docker..."
apt install -y curl git openssl
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    ok "Docker установлен"
else
    ok "Docker уже установлен"
fi

if ! docker compose version &> /dev/null; then
    apt install -y docker-compose-plugin 2>/dev/null || apt install -y docker-compose 2>/dev/null || true
fi
ok "Docker Compose готов"

# ═══════════════════════════════════════════════
# ЭТАП 2: КЛОНИРОВАНИЕ ПРОЕКТА
# ═══════════════════════════════════════════════
echo ""
echo -e "${B}═══ Этап 2/6: Загрузка проекта ═══${N}"

if [ -d "/opt/NodeConnect" ]; then
    warn "Папка /opt/NodeConnect уже существует. Обновляем..."
    cd /opt/NodeConnect
    git fetch --all 2>/dev/null || true
    git reset --hard origin/main 2>/dev/null || true
else
    git clone https://github.com/GGGWWWPPP/fork.git /opt/NodeConnect
    cd /opt/NodeConnect
fi
ok "Проект загружен в /opt/NodeConnect"

# ═══════════════════════════════════════════════
# ЭТАП 3: ИНТЕРАКТИВНЫЙ МАСТЕР НАСТРОЙКИ
# ═══════════════════════════════════════════════
echo ""
echo -e "${B}═══ Этап 3/6: Настройка — ответьте на вопросы ═══${N}"
echo ""
echo -e "${Y}📌 Подсказка: все данные можно изменить позже в файлах .env${N}"
echo ""

# ── Блок 1: Домены ──
echo -e "${B}─── 🌐 Домены ───${N}"
SITE_DOMAIN=$(ask_required "Домен для сайта продаж (например: vpn.com)")
PANEL_DOMAIN=$(ask_optional "Домен для админ-панели" "panel.${SITE_DOMAIN}")
PAY_DOMAIN=$(ask_optional "Домен для webhook'ов оплаты" "pay.${SITE_DOMAIN}")
ADMIN_EMAIL=$(ask_required "Email администратора (для SSL и панели)")
echo ""

# ── Блок 2: Telegram ──
echo -e "${B}─── 🤖 Telegram Bot ───${N}"
echo -e "${N}Создайте бота через @BotFather и вставьте токен${N}"
BOT_TOKEN=$(ask_required "Токен Telegram-бота")
ADMIN_ID=$(ask_required "Ваш Telegram ID (для прав администратора)")
echo ""
echo -e "${N}Если у вас есть канал, на который юзеры должны быть подписаны:${N}"
CHANNEL_ID=$(ask_optional "ID канала для обязательной подписки (0 = выкл)" "0")
CHANNEL_URL=$(ask_optional "Ссылка на канал" "https://t.me/your_channel")
echo ""

# ── Блок 3: Платежи ──
echo -e "${B}─── 💳 Платежные системы ───${N}"
echo -e "${N}Оставьте пустым если не используете (нажмите Enter)${N}"
echo ""

read -rp "$(echo -e "${C}API ключ Platega (или Enter — пропустить)${N}: ")" PLATEGA_API_KEY </dev/tty
PLATEGA_API_KEY="${PLATEGA_API_KEY:-}"

PLATEGA_SHOP_ID=""
if [ -n "$PLATEGA_API_KEY" ]; then
    PLATEGA_SHOP_ID=$(ask_required "Shop ID Platega")
fi

read -rp "$(echo -e "${C}Токен CryptoBot (или Enter — пропустить)${N}: ")" CRYPTO_BOT_TOKEN </dev/tty
CRYPTO_BOT_TOKEN="${CRYPTO_BOT_TOKEN:-}"

USDT_RATE=$(ask_optional "Курс RUB/USDT" "90.0")
echo ""

# ── Блок 4: SSL ──
echo -e "${B}─── 🔐 SSL Сертификаты ───${N}"
echo -e "  1) ${G}Let's Encrypt${N} — бесплатный, автоматический (домены должны быть направлены на сервер)"
echo -e "  2) ${Y}Self-signed${N} — для тестирования (браузер покажет предупреждение)"
echo ""
read -rp "$(echo -e "${C}Выберите [1/2]${N}: ")" SSL_CHOICE </dev/tty
SSL_CHOICE="${SSL_CHOICE:-2}"

# ═══════════════════════════════════════════════
# ЭТАП 4: ГЕНЕРАЦИЯ КОНФИГУРАЦИИ
# ═══════════════════════════════════════════════
echo ""
echo -e "${B}═══ Этап 4/6: Генерация конфигурации ═══${N}"

echo "🔐 Генерация безопасных паролей..."
DB_PASS=$(openssl rand -hex 16)
MARIADB_PASS=$(openssl rand -hex 16)
MARZBAN_ADMIN_PASS=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 20)

# ── Главный .env ──
cat <<EOF > .env
# ==========================================
# NodeConnect — Автосгенерированная конфигурация
# Дата: $(date +"%Y-%m-%d %H:%M")
# ==========================================

# ─── Telegram Bot ───
BOT_TOKEN="${BOT_TOKEN}"
ADMIN_IDS=[${ADMIN_ID}]
REQUIRED_CHANNEL_ID=${CHANNEL_ID}
CHANNEL_URL="${CHANNEL_URL}"

# ─── Домены ───
SITE_DOMAIN="${SITE_DOMAIN}"
PANEL_DOMAIN="${PANEL_DOMAIN}"
SITE_URL="https://${SITE_DOMAIN}"
ADMIN_EMAIL="${ADMIN_EMAIL}"

# ─── NodeConnect Core API ───
MARZBAN_URL="https://${PANEL_DOMAIN}"
MARZBAN_USERNAME="admin"
MARZBAN_PASSWORD="${MARZBAN_ADMIN_PASS}"
MARIADB_PASSWORD="${MARIADB_PASS}"
MARZBAN_DB_URL="mysql+pymysql://marzban:${MARIADB_PASS}@mariadb:3306/marzban"

# ─── PostgreSQL (Bot + Website) ───
DB_URL="postgresql+asyncpg://nodeconnect:${DB_PASS}@postgres:5432/nodeconnect"
POSTGRES_DB=nodeconnect
POSTGRES_USER=nodeconnect
POSTGRES_PASSWORD=${DB_PASS}
DB_HOST=postgres
DB_PORT=5432
DB_NAME=nodeconnect
DB_USER=nodeconnect
DB_PASSWORD=${DB_PASS}

# ─── Платежные системы ───
PLATEGA_API_KEY="${PLATEGA_API_KEY}"
PLATEGA_SHOP_ID="${PLATEGA_SHOP_ID}"
CRYPTO_BOT_TOKEN="${CRYPTO_BOT_TOKEN}"
USDT_RATE=${USDT_RATE}
EOF
ok "Создан .env"

# ── Core .env ──
cat <<EOF > nodeconnect-core/.env
# ==========================================
# NodeConnect Core — Автосгенерированная конфигурация
# ==========================================
UVICORN_HOST = "0.0.0.0"
UVICORN_PORT = 8000

SUDO_USERNAME = "admin"
SUDO_PASSWORD = "${MARZBAN_ADMIN_PASS}"

SQLALCHEMY_DATABASE_URL = "mysql+pymysql://marzban:${MARIADB_PASS}@127.0.0.1:3306/marzban"

XRAY_SUBSCRIPTION_URL_PREFIX = "https://${PANEL_DOMAIN}"

TELEGRAM_API_TOKEN = "${BOT_TOKEN}"
TELEGRAM_ADMIN_ID = ${ADMIN_ID}

CUSTOM_TEMPLATES_DIRECTORY = "/var/lib/nodeconnect/templates/"

SUB_PROFILE_TITLE = "NodeConnect"
SUB_SUPPORT_URL = "https://t.me/your_support"

NOTIFY_STATUS_CHANGE = True
NOTIFY_USER_CREATED = True
NOTIFY_USER_UPDATED = True
NOTIFY_USER_DELETED = True
NOTIFY_IF_DATA_USAGE_PERCENT_REACHED = True
NOTIFY_IF_DAYS_LEFT_REACHED = True
NOTIFY_LOGIN = True
NOTIFY_DAYS_LEFT = 3,7
NOTIFY_REACHED_USAGE_PERCENT = 80,90

USERS_AUTODELETE_DAYS = -1
INACTIVE_USER_DELETE_DAYS = 30

DOCS = True
EOF
ok "Создан nodeconnect-core/.env"

# ═══════════════════════════════════════════════
# ЭТАП 5: SSL + NGINX
# ═══════════════════════════════════════════════
echo ""
echo -e "${B}═══ Этап 5/6: SSL сертификаты и Nginx ═══${N}"

mkdir -p nginx/ssl

if [ "$SSL_CHOICE" = "1" ]; then
    echo "📡 Получение Let's Encrypt сертификатов..."
    
    # Устанавливаем certbot
    apt install -y certbot 2>/dev/null || true
    
    # Останавливаем всё что на 80/443
    docker compose down 2>/dev/null || docker-compose down 2>/dev/null || true
    systemctl stop nginx 2>/dev/null || true
    
    # Получаем сертификат
    if certbot certonly --standalone --non-interactive --agree-tos \
        --email "${ADMIN_EMAIL}" \
        -d "${SITE_DOMAIN}" \
        -d "${PANEL_DOMAIN}" \
        -d "${PAY_DOMAIN}" 2>/dev/null; then
        
        cp -L "/etc/letsencrypt/live/${SITE_DOMAIN}/fullchain.pem" nginx/ssl/
        cp -L "/etc/letsencrypt/live/${SITE_DOMAIN}/privkey.pem" nginx/ssl/
        ok "Let's Encrypt сертификаты установлены"
        
        # Авто-обновление сертификатов
        (crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet && cp -L /etc/letsencrypt/live/${SITE_DOMAIN}/fullchain.pem /opt/NodeConnect/nginx/ssl/ && cp -L /etc/letsencrypt/live/${SITE_DOMAIN}/privkey.pem /opt/NodeConnect/nginx/ssl/ && cd /opt/NodeConnect && docker compose restart nginx 2>/dev/null || docker-compose restart nginx 2>/dev/null") | crontab -
        ok "Авто-обновление SSL настроено (каждый день в 3:00)"
    else
        warn "Не удалось получить Let's Encrypt. Генерируем self-signed..."
        SSL_CHOICE="2"
    fi
fi

if [ "$SSL_CHOICE" = "2" ]; then
    echo "🔐 Генерируем self-signed сертификат..."
    openssl req -x509 -newkey rsa:2048 \
        -keyout nginx/ssl/privkey.pem \
        -out nginx/ssl/fullchain.pem \
        -days 365 -nodes -subj "/CN=${SITE_DOMAIN}"
    ok "Self-signed сертификат создан (замените на Let's Encrypt позже)"
fi

# Настраиваем Nginx
echo "⚙️ Настраиваем Nginx..."
cp nginx/nginx.conf nginx/nginx.conf.backup 2>/dev/null || true
sed -i "s/yourdomain.com/${SITE_DOMAIN}/g" nginx/nginx.conf
sed -i "s/panel\.${SITE_DOMAIN}/${PANEL_DOMAIN}/g" nginx/nginx.conf
sed -i "s/pay\.${SITE_DOMAIN}/${PAY_DOMAIN}/g" nginx/nginx.conf
ok "Nginx настроен для ${SITE_DOMAIN}"

# ═══════════════════════════════════════════════
# ЭТАП 6: ЗАПУСК
# ═══════════════════════════════════════════════
echo ""
echo -e "${B}═══ Этап 6/6: Запуск всех сервисов ═══${N}"

echo "🔧 Останавливаем старые контейнеры..."
docker compose down 2>/dev/null || docker-compose down 2>/dev/null || true

echo "🚀 Собираем и запускаем..."
docker compose up -d --build 2>/dev/null || docker-compose up -d --build

# Ждём пока контейнеры запустятся
echo "⏳ Ожидаем запуск сервисов (30 сек)..."
sleep 30

# Проверяем статус
echo ""
echo "📊 Статус контейнеров:"
docker compose ps 2>/dev/null || docker-compose ps 2>/dev/null || true

# ═══════════════════════════════════════════════
# ФИНАЛЬНЫЙ БАННЕР
# ═══════════════════════════════════════════════
echo ""
echo -e "${G}╔══════════════════════════════════════════════════════╗${N}"
echo -e "${G}║${B}     🎉 NodeConnect установлен и запущен!             ${G}║${N}"
echo -e "${G}╚══════════════════════════════════════════════════════╝${N}"
echo ""
echo -e "  ${B}📌 Ваши сервисы:${N}"
echo -e "     🌐 Сайт:           ${C}https://${SITE_DOMAIN}${N}"
echo -e "     🔧 Админ-панель:   ${C}https://${PANEL_DOMAIN}/dashboard/${N}"
echo -e "     🤖 Telegram-бот:   Запущен"
echo -e "     💳 Webhook:        ${C}https://${PAY_DOMAIN}${N}"
echo ""
echo -e "  ${B}🔐 Учётные данные панели:${N}"
echo -e "     Логин:   ${C}admin${N}"
echo -e "     Пароль:  ${C}${MARZBAN_ADMIN_PASS}${N}"
echo -e "     ${R}⚠️ ЗАПИШИТЕ ПАРОЛЬ — он больше не покажется!${N}"
echo ""
echo -e "  ${B}📋 Полезные команды:${N}"
echo -e "     docker compose logs -f              — все логи"
echo -e "     docker compose logs -f bot          — логи бота"
echo -e "     docker compose logs -f nodeconnect  — логи панели"
echo -e "     docker compose logs -f website      — логи сайта"
echo -e "     docker compose restart bot          — перезапуск бота"
echo -e "     docker compose restart nodeconnect  — перезапуск панели"
echo ""
if [ -z "$PLATEGA_API_KEY" ] && [ -z "$CRYPTO_BOT_TOKEN" ]; then
    echo -e "  ${Y}⚠️ Платежные системы не настроены!${N}"
    echo -e "     Для приёма платежей добавьте ключи в ${C}/opt/NodeConnect/.env${N}"
    echo -e "     и перезапустите: ${C}docker compose restart bot website${N}"
    echo ""
fi
echo -e "  ${B}📂 Конфигурация:${N}"
echo -e "     Основной:  ${C}/opt/NodeConnect/.env${N}"
echo -e "     Панель:    ${C}/opt/NodeConnect/nodeconnect-core/.env${N}"
echo -e "     Nginx:     ${C}/opt/NodeConnect/nginx/nginx.conf${N}"
echo ""
