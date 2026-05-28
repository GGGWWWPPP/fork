import aiohttp
from config import config

class PlategaAPI:
    def __init__(self):
        self.api_key = config.PLATEGA_API_KEY
        self.shop_id = config.PLATEGA_SHOP_ID
        self.base_url = "https://api.platega.io/v1"

    async def create_invoice(self, amount: int, order_id: str):
        headers = {
            "X-MerchantId": self.shop_id,
            "X-Secret": self.api_key,
            "Content-Type": "application/json"
        }
        
        data = {
            "paymentMethod": 2,
            "paymentDetails": {
                "amount": amount,
                "currency": "RUB"
            },
            "description": "Оплата подписки",
            "return": "https://t.me",
            "payload": order_id
        }
        
        # Новый правильный URL по документации
        async with aiohttp.ClientSession() as session:
            async with session.post("https://app.platega.io/transaction/process", headers=headers, json=data) as resp:
                if resp.status in [200, 201]:
                    result = await resp.json()
                    # Ссылка для оплаты возвращается в поле "redirect"
                    return result.get("redirect") or result.get("url", "Ссылка не найдена")
                else:
                    text = await resp.text()
                    raise Exception(f"Ошибка Platega API ({resp.status}): {text}")
