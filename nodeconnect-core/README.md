# NodeConnect Panel

**VPN Management Panel** — форк [Marzban](https://github.com/Gozargah/Marzban) от Gozargah, работающий на Xray.

## Возможности

- 🌐 **Web-панель** — полноценный Dashboard для управления пользователями
- 📊 **Мониторинг** — трафик, статусы, истечение подписок в реальном времени
- 🔔 **Telegram-уведомления** — создание/удаление юзеров, лимиты трафика, истечение подписки, логины
- 🗑️ **Авто-удаление** — неактивных и просроченных пользователей
- 📱 **Кастомная страница подписки** — HTML-шаблон для клиентов
- 🔌 **Multi-protocol** — VLESS, VMess, Trojan, Shadowsocks через Xray
- 🌍 **Multi-node** — поддержка нескольких серверов
- 📡 **REST API** — полный API для интеграции с ботами и сайтами
- 🛡️ **CLI** — управление из командной строки (`nodeconnect-cli`)
- 🔗 **Webhook** — интеграция с внешними сервисами
- 📈 **Учёт трафика** — по пользователям и нодам

## Быстрая установка

```bash
sudo bash install.sh
```

Скрипт автоматически:
1. Установит Docker и зависимости
2. Настроит SSL сертификаты
3. Сконфигурирует Nginx reverse-proxy
4. Запустит панель
5. Создаст администратора

## Ручная установка (Docker)

```bash
git clone https://github.com/YOUR_USERNAME/NodeConnect.git
cd NodeConnect/nodeconnect-core
cp .env.example .env
# Отредактируйте .env
docker compose up -d
```

## Конфигурация

Все настройки через `.env` файл. Ключевые параметры:

| Параметр | Описание | Default |
|----------|----------|---------|
| `UVICORN_PORT` | Порт панели | `8000` |
| `SQLALCHEMY_DATABASE_URL` | Строка подключения к БД | `sqlite:///db.sqlite3` |
| `TELEGRAM_API_TOKEN` | Токен Telegram-бота для уведомлений | — |
| `TELEGRAM_ADMIN_ID` | Telegram ID администраторов | — |
| `XRAY_SUBSCRIPTION_URL_PREFIX` | URL для подписок | — |
| `USERS_AUTODELETE_DAYS` | Авто-удаление просроченных (дни, -1 = выкл) | `-1` |
| `INACTIVE_USER_DELETE_DAYS` | Удаление неактивных (дни) | `30` |
| `NOTIFY_DAYS_LEFT` | Уведомить за N дней до истечения | `3` |
| `NOTIFY_REACHED_USAGE_PERCENT` | Уведомить при % трафика | `80` |

Полный список — см. `.env.example`.

## CLI

```bash
# Внутри Docker-контейнера:
nodeconnect-cli admin create --sudo    # Создать админа
nodeconnect-cli user list              # Список пользователей
nodeconnect-cli --help                 # Все команды
```

## Лицензия

Этот проект распространяется под лицензией **GNU AGPL-3.0**.

Основан на [Marzban](https://github.com/Gozargah/Marzban) © 2023 Gozargah organization.

Модификации © 2024-2026 NodeConnect.
