import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_IDS: list[int]
    REQUIRED_CHANNEL_ID: int = 0
    CHANNEL_URL: str = ""
    
    # Marzban API
    MARZBAN_URL: str = "https://your-marzban-domain.com:8000"
    MARZBAN_USERNAME: str = "admin"
    MARZBAN_PASSWORD: str = "admin_password"
    
    # DB
    DB_URL: str = "postgresql+asyncpg://nodeconnect:password@postgres:5432/nodeconnect"
    
    # Payments
    PLATEGA_API_KEY: str = "your_platega_api_key"
    PLATEGA_SHOP_ID: str = "your_shop_id"
    STARS_PROVIDER_TOKEN: str = "" # Leave empty for Telegram Stars
    CRYPTO_BOT_TOKEN: str = "your_cryptobot_token"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

config = Settings()
