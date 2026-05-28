#!/bin/bash
set -eo pipefail

# ══════════════════════════════════════════════════════════════
# Marzban 一键部署 / One-Click Install
# 支持: Debian 11+ / Ubuntu 20.04+
# ══════════════════════════════════════════════════════════════

INSTALL_DIR="/opt/marzban"
REPO_URL="https://github.com/Gozargah/Marzban.git"

R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'; C='\033[0;36m'; B='\033[1;37m'; N='\033[0m'
ok()   { echo -e "${G}[✓]${N} $1"; }
warn() { echo -e "${Y}[!]${N} $1"; }
err()  { echo -e "${R}[✗]${N} $1"; exit 1; }
info() { echo -e "${C}[i]${N} $1"; }

on_error() {
  local rc=$?
  local lineno=$1
  echo ""
  echo -e "${R}══════════════════════════════════════════════${N}"
  echo -e "${R}[✗] Установка прервана, код ошибки $rc, строка $lineno${N}"
  echo -e "${R}══════════════════════════════════════════════${N}"
  exit $rc
}
trap 'on_error $LINENO' ERR

banner() {
  echo ""
  echo -e "${C}╔══════════════════════════════════════════════╗${N}"
  echo -e "${C}║${B}            🚀 Marzban Установка              ${C}║${N}"
  echo -e "${C}║${N}       Авто-настройка + SSL + Docker        ${C}║${N}"
  echo -e "${C}╚══════════════════════════════════════════════╝${N}"
  echo ""
}

preflight() {
  [ "$(id -u)" -ne 0 ] && err "Пожалуйста, запустите скрипт от имени root (sudo -i)"
  command -v apt &>/dev/null || err "Скрипт поддерживает только Debian / Ubuntu (apt)"
}

install_deps() {
  ok "Обновление пакетов..."
  apt update -qq

  local pkgs=(curl git socat cron tar nginx certbot python3-certbot-nginx)
  local need=()
  for p in "${pkgs[@]}"; do
    dpkg -s "$p" &>/dev/null || need+=("$p")
  done
  if [ ${#need[@]} -gt 0 ]; then
    ok "Установка: ${need[*]}"
    DEBIAN_FRONTEND=noninteractive apt install -y -qq "${need[@]}"
  else
    ok "Системные зависимости готовы"
  fi
}

install_docker() {
  if command -v docker &>/dev/null; then
    ok "Docker $(docker -v) ✓"
  else
    ok "Установка Docker..."
    curl -fsSL https://get.docker.com | bash -s docker
    ok "Docker установлен"
  fi

  if command -v docker-compose &>/dev/null || docker compose version &>/dev/null; then
    ok "Docker Compose ✓"
  else
    ok "Установка Docker Compose..."
    apt install -y docker-compose-plugin
  fi
}

setup_ssl() {
  echo ""
  echo -e "${C}━━━ Настройка Доменов ━━━${N}"
  echo ""

  while true; do
    read -rp "$(echo -e "${C}Домен для Панели${N} (например, panel.example.com): ")" PANEL_DOMAIN
    [ -n "$PANEL_DOMAIN" ] && break
    warn "Домен не может быть пустым"
  done

  while true; do
    read -rp "$(echo -e "${C}Домен для Подписок (Sub)${N} (например, sub.example.com): ")" SUB_DOMAIN
    [ -n "$SUB_DOMAIN" ] && break
    warn "Домен для подписок не может быть пустым"
  done

  ok "Установка acme.sh для получения SSL сертификатов..."
  if [ ! -f ~/.acme.sh/acme.sh ]; then
    curl -s https://get.acme.sh | sh -s email="admin@${PANEL_DOMAIN}"
  fi
  source ~/.bashrc || true
  ~/.acme.sh/acme.sh --upgrade --auto-upgrade

  mkdir -p /var/lib/marzban/certs
  
  ok "Настройка Nginx-заглушек для проверки доменов..."
  systemctl start nginx 2>/dev/null || true
  
  cat > /etc/nginx/sites-available/marzban-temp << EOF
server { listen 80; server_name ${PANEL_DOMAIN} ${SUB_DOMAIN}; location /.well-known/acme-challenge/ { root /var/www/html; } }
EOF
  ln -sf /etc/nginx/sites-available/marzban-temp /etc/nginx/sites-enabled/
  rm -f /etc/nginx/sites-enabled/default
  nginx -t &>/dev/null && systemctl reload nginx

  ok "Получение сертификата для панели: $PANEL_DOMAIN"
  ~/.acme.sh/acme.sh --issue -d "$PANEL_DOMAIN" -w /var/www/html \
    --key-file /var/lib/marzban/certs/panel.key \
    --fullchain-file /var/lib/marzban/certs/panel.cer

  ok "Получение сертификата для подписок: $SUB_DOMAIN"
  ~/.acme.sh/acme.sh --issue -d "$SUB_DOMAIN" -w /var/www/html \
    --key-file /var/lib/marzban/certs/sub.key \
    --fullchain-file /var/lib/marzban/certs/sub.cer

  ok "Сертификаты успешно получены!"
}

setup_nginx() {
  ok "Настройка Nginx как reverse-proxy для Marzban..."

  cat > /etc/nginx/sites-available/marzban << NGINXEOF
server {
    listen 80;
    server_name ${PANEL_DOMAIN} ${SUB_DOMAIN};
    return 301 https://\$host\$request_uri;
}

# Сервер для панели
server {
    listen 443 ssl http2;
    server_name ${PANEL_DOMAIN};

    ssl_certificate     /var/lib/marzban/certs/panel.cer;
    ssl_certificate_key /var/lib/marzban/certs/panel.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;

    client_max_body_size 50m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

# Сервер для подписок
server {
    listen 443 ssl http2;
    server_name ${SUB_DOMAIN};

    ssl_certificate     /var/lib/marzban/certs/sub.cer;
    ssl_certificate_key /var/lib/marzban/certs/sub.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;

    client_max_body_size 50m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
NGINXEOF

  ln -sf /etc/nginx/sites-available/marzban /etc/nginx/sites-enabled/
  rm -f /etc/nginx/sites-available/marzban-temp
  nginx -t &>/dev/null && systemctl reload nginx
  ok "Nginx настроен"
}

deploy_code() {
  if [ -d "$INSTALL_DIR/.git" ]; then
    ok "Обновление Marzban..."
    cd "$INSTALL_DIR"
    git fetch origin master --quiet && git reset --hard origin/master --quiet
  else
    ok "Клонирование Marzban..."
    git clone --depth 1 "$REPO_URL" "$INSTALL_DIR" --quiet
    cd "$INSTALL_DIR"
  fi
}

configure_env() {
  cd "$INSTALL_DIR"
  if [ ! -f .env ]; then
    cp .env.example .env
  fi

  # Поскольку мы используем Nginx reverse proxy, Marzban (Uvicorn) не должен сам включать SSL,
  # он будет работать по HTTP на порту 8000, а Nginx уже оборачивает всё в HTTPS.
  sed -i 's/# UVICORN_PORT = 8000/UVICORN_PORT = 8000/' .env
  sed -i "s|# UVICORN_HOST = \"0.0.0.0\"|UVICORN_HOST = \"127.0.0.1\"|" .env
  
  # Настройка .env для саб-домена
  sed -i "s|# XRAY_SUBSCRIPTION_URL_PREFIX.*|XRAY_SUBSCRIPTION_URL_PREFIX = \"https://${SUB_DOMAIN}\"|" .env

  ok ".env файл настроен"
}

start_marzban() {
  ok "Запуск Marzban..."
  cd "$INSTALL_DIR"
  docker compose up -d
  sleep 5
  ok "Marzban запущен"
}

create_admin() {
  echo ""
  echo -e "${C}━━━ Создание Админа ━━━${N}"
  read -rp "$(echo -e "${C}Логин администратора${N}: ")" ADMIN_USER
  read -rp "$(echo -e "${C}Пароль администратора${N}: ")" ADMIN_PASS

  if [ -n "$ADMIN_USER" ] && [ -n "$ADMIN_PASS" ]; then
    docker compose exec marzban marzban-cli admin create --sudo -u "$ADMIN_USER" -p "$ADMIN_PASS" || true
    ok "Администратор $ADMIN_USER создан"
  else
    warn "Создание админа пропущено, вы можете сделать это позже: docker compose exec marzban marzban-cli admin create --sudo"
  fi
}

show_result() {
  echo ""
  echo -e "${G}╔══════════════════════════════════════════════╗${N}"
  echo -e "${G}║${B}       🚀 Установка Marzban завершена         ${G}║${N}"
  echo -e "${G}╚══════════════════════════════════════════════╝${N}"
  echo ""
  echo -e "  🌐 Панель:   ${C}https://${PANEL_DOMAIN}${N}"
  echo -e "  📡 Подписки: ${C}https://${SUB_DOMAIN}${N}"
  echo -e "  📁 Каталог:  ${INSTALL_DIR}"
  echo ""
  echo -e "  Логин: ${ADMIN_USER}"
  echo -e "  Пароль: ${ADMIN_PASS}"
  echo ""
  echo -e "  Полезные команды:"
  echo -e "    cd ${INSTALL_DIR} && docker compose logs -f  ${C}# Логи${N}"
  echo -e "    cd ${INSTALL_DIR} && docker compose restart  ${C}# Перезапуск${N}"
  echo ""
}

main() {
  banner
  preflight
  install_deps
  install_docker
  setup_ssl
  setup_nginx
  deploy_code
  configure_env
  start_marzban
  create_admin
  show_result
}

main "$@"
