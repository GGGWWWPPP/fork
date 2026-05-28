import requests
import urllib.parse
import logging

from config import settings

logger = logging.getLogger(__name__)


def get_marzban_token():
    """Получить токен авторизации Marzban API."""
    url = f"{settings.marzban_url}/api/admin/token"
    data = {
        "username": settings.marzban_username,
        "password": settings.marzban_password,
        "grant_type": "password",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        response = requests.post(
            url, data=urllib.parse.urlencode(data), headers=headers, timeout=10
        )
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception as e:
        logger.error(f"[MARZBAN ERROR]: Ошибка авторизации: {e}")
        return None


def create_or_update_vpn_user(
    username: str, expire_timestamp: int, device_limit: int = 0
) -> dict:
    """Создать или обновить VPN пользователя в Marzban."""
    token = get_marzban_token()
    if not token:
        raise Exception("Внутренняя ошибка. Невозможно подключиться к сервису VPN.")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # Сначала пытаемся получить пользователя
    get_url = f"{settings.marzban_url}/api/user/{username}"
    res = requests.get(get_url, headers=headers, timeout=10)

    payload = {
        "proxies": {"vless": {}},
        "inbounds": {},
        "expire": expire_timestamp,
        "data_limit": 0,  # Безлимит
        "data_limit_reset_strategy": "no_reset",
    }

    if res.status_code == 200:
        # Обновляем пользователя
        update_url = f"{settings.marzban_url}/api/user/{username}"
        response = requests.put(update_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        user_data = response.json()
    else:
        # Создаем нового
        create_url = f"{settings.marzban_url}/api/user"
        payload["username"] = username
        response = requests.post(create_url, json=payload, headers=headers, timeout=10)
        if response.status_code == 409:
            raise Exception("Конфликт: Пользователь уже существует в панели.")
        response.raise_for_status()
        user_data = response.json()

    subscription_url = user_data.get("subscription_url", "")
    links = user_data.get("links", [])
    key_link = links[0] if links else subscription_url

    return {
        "subscription_url": subscription_url,
        "key": key_link,
        "marzban_username": username,
    }


def create_platega_payment(amount: int, order_id: str, email: str) -> str:
    """Создать платёж в Platega и вернуть ссылку на оплату."""
    headers = {
        "X-MerchantId": settings.platega_shop_id,
        "X-Secret": settings.platega_api_key,
        "Content-Type": "application/json",
    }

    data = {
        "paymentMethod": 2,
        "paymentDetails": {"amount": amount, "currency": "RUB"},
        "description": f"Подписка Node Connect VPN",
        "return": "https://nodeconnect.tech",
        "payload": order_id,
    }

    try:
        response = requests.post(
            "https://app.platega.io/transaction/process",
            headers=headers,
            json=data,
            timeout=15,
        )
        if response.status_code in [200, 201]:
            result = response.json()
            redirect_url = result.get("redirect") or result.get("url")
            if redirect_url:
                return redirect_url
            raise Exception(f"Platega не вернул ссылку: {result}")
        else:
            raise Exception(
                f"Ошибка Platega API ({response.status_code}): {response.text}"
            )
    except requests.RequestException as e:
        logger.error(f"Platega payment error: {e}")
        raise Exception(f"Ошибка при создании платежа: {e}")
