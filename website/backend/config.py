from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Marzban VPN API
    marzban_url: str = "https://admin.nodeconnect.tech"
    marzban_username: str = "NodeConnect"
    marzban_password: str = ""

    # PostgreSQL
    db_host: str = "postgres"
    db_port: int = 5432
    db_name: str = "nodeconnect"
    db_user: str = "nodeconnect"
    db_password: str = ""

    # Platega
    platega_api_key: str = ""
    platega_shop_id: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
