import aiohttp
from config import config

class CryptoBotAPI:
    def __init__(self):
        self.token = config.CRYPTO_BOT_TOKEN
        self.base_url = "https://pay.crypt.bot/api"

    async def create_invoice(self, amount: float, order_id: str):
        headers = {"Crypto-Pay-API-Token": self.token}
        data = {
            "asset": "USDT",
            "amount": str(amount),
            "payload": order_id,
            "allow_anonymous": False
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/createInvoice", headers=headers, json=data) as resp:
                result = await resp.json()
                if resp.status == 200 and result.get("ok"):
                    return result["result"]["pay_url"]
                else:
                    raise Exception(f"CryptoBot error: {result}")
