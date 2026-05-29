import aiohttp
from config import config
from datetime import datetime, timezone, timedelta

class MarzbanAPI:
    def __init__(self):
        self.base_url = config.MARZBAN_URL
        self.username = config.MARZBAN_USERNAME
        self.password = config.MARZBAN_PASSWORD
        self.token = None

    async def _get_token(self):
        async with aiohttp.ClientSession() as session:
            data = {"username": self.username, "password": self.password}
            async with session.post(f"{self.base_url}/api/admin/token", data=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    self.token = result['access_token']
                else:
                    raise Exception(f"Failed to get Marzban Token: {resp.status}")

    async def _request(self, method, endpoint, **kwargs):
        if not self.token:
            await self._get_token()
        
        headers = {"Authorization": f"Bearer {self.token}"}
        if 'headers' in kwargs:
            kwargs['headers'].update(headers)
        else:
            kwargs['headers'] = headers
            
        async with aiohttp.ClientSession() as session:
            async with session.request(method, f"{self.base_url}{endpoint}", **kwargs) as resp:
                if resp.status == 401:
                    await self._get_token()
                    kwargs['headers']["Authorization"] = f"Bearer {self.token}"
                    async with session.request(method, f"{self.base_url}{endpoint}", **kwargs) as retry_resp:
                        if retry_resp.status not in (200, 204):
                            raise Exception(f"Marzban API error {retry_resp.status}")
                        if retry_resp.status == 204 or retry_resp.content_length == 0:
                            return {}
                        return await retry_resp.json()
                if resp.status == 204 or resp.content_length == 0:
                    return {}
                if resp.status != 200:
                    raise Exception(f"Marzban API error {resp.status}")
                return await resp.json()

    async def create_user(self, username: str, expire_days: int):
        now = datetime.now(timezone.utc)
        expire_timestamp = int((now + timedelta(days=expire_days)).timestamp())
        
        # Для современных версий Marzban достаточно передать пустые словари
        # для inbounds и proxies, либо вообще не передавать их, и панель 
        # сама сгенерирует UUID и распределит по протоколами по умолчанию.
        data = {
            "username": username,
            "expire": expire_timestamp,
            "proxies": {},
            "inbounds": {},
            "data_limit": 200 * 1024 * 1024 * 1024,
            "data_limit_reset_strategy": "no_reset"
        }
        
        # Если API выдаст ошибку, попробуем запросить дефолтные inbounds
        try:
            return await self._request("POST", "/api/user", json=data)
        except Exception as e:
            # Fallback: get inbounds and construct full payload
            inbounds_res = await self._request("GET", "/api/inbounds")
            inbounds_dict = {}
            proxies_dict = {}
            if inbounds_res and isinstance(inbounds_res, dict):
                for protocol, items in inbounds_res.items():
                    if items:
                        inbounds_dict[protocol] = [i['tag'] for i in items]
                        proxies_dict[protocol] = {}
            data["inbounds"] = inbounds_dict
            data["proxies"] = proxies_dict
            return await self._request("POST", "/api/user", json=data)

    async def get_user(self, username: str):
        return await self._request("GET", f"/api/user/{username}")

    async def modify_user(self, username: str, expire_timestamp: int):
        data = {
            "expire": expire_timestamp
        }
        return await self._request("PUT", f"/api/user/{username}", json=data)

    async def add_days(self, username: str, days: int):
        user = await self.get_user(username)
        if not user or 'expire' not in user:
            return None
        current_expire = user['expire']
        now = int(datetime.now(timezone.utc).timestamp())
        if not current_expire or current_expire < now:
            new_expire = now + (days * 86400)
        else:
            new_expire = current_expire + (days * 86400)
        
        return await self.modify_user(username, new_expire)

    async def remove_user(self, username: str):
        return await self._request("DELETE", f"/api/user/{username}")
