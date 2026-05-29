#!/bin/bash
# ==================================================
# NodeConnect — Замена SSL на Let's Encrypt
# Используйте ПОСЛЕ установки для замены self-signed
# ==================================================
set -e

R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'; C='\033[0;36m'; N='\033[0m'

cd /opt/NodeConnect || { echo -e "${R}Проект не найден в /opt/NodeConnect${N}"; exit 1; }

# Читаем домены из .env
if [ -f .env ]; then
    source .env
fi

DOMAIN="${SITE_DOMAIN}"
PANEL="${PANEL_DOMAIN}"

if [ -z "$DOMAIN" ]; then
    read -rp "$(echo -e "${C}Введите основной домен${N}: ")" DOMAIN </dev/tty
fi

if [ -z "$PANEL" ]; then
    read -rp "$(echo -e "${C}Введите домен панели${N}: ")" PANEL </dev/tty
fi

EMAIL="${ADMIN_EMAIL}"
if [ -z "$EMAIL" ]; then
    read -rp "$(echo -e "${C}Введите email для Let's Encrypt${N}: ")" EMAIL </dev/tty
fi

echo "🔐 Получение SSL сертификатов для: $DOMAIN, $PANEL"

# Устанавливаем certbot
apt install -y certbot 2>/dev/null || true

# Останавливаем nginx для освобождения 80 порта
echo "⏹ Останавливаем Nginx..."
docker compose stop nginx 2>/dev/null || docker-compose stop nginx 2>/dev/null || true
systemctl stop nginx 2>/dev/null || true

# Запрашиваем сертификат
echo "📡 Запрос сертификата у Let's Encrypt..."
certbot certonly --standalone --non-interactive --agree-tos \
    --email "$EMAIL" -d "$DOMAIN" -d "$PANEL"

# Копируем
echo "📂 Копируем сертификаты..."
mkdir -p nginx/ssl
cp -L "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" nginx/ssl/
cp -L "/etc/letsencrypt/live/$DOMAIN/privkey.pem" nginx/ssl/

# Авто-обновление
(crontab -l 2>/dev/null | grep -v "certbot renew"; echo "0 3 * * * certbot renew --quiet && cp -L /etc/letsencrypt/live/${DOMAIN}/fullchain.pem /opt/NodeConnect/nginx/ssl/ && cp -L /etc/letsencrypt/live/${DOMAIN}/privkey.pem /opt/NodeConnect/nginx/ssl/ && cd /opt/NodeConnect && docker compose restart nginx 2>/dev/null") | crontab -

# Перезапуск
echo "🚀 Перезапуск Nginx..."
docker compose start nginx 2>/dev/null || docker-compose start nginx 2>/dev/null || true

echo ""
echo -e "${G}══════════════════════════════════════════${N}"
echo -e "${G}🎉 SSL сертификаты успешно установлены!${N}"
echo -e "${G}══════════════════════════════════════════${N}"
echo -e "Сайт:   ${C}https://$DOMAIN${N}"
echo -e "Панель: ${C}https://$PANEL${N}"
echo -e "Авто-обновление: каждый день в 3:00"
