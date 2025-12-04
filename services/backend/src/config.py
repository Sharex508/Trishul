from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "crypto"
    POSTGRES_USER: str = "crypto"
    POSTGRES_PASSWORD: str = "crypto"
    TIMEZONE: str = "UTC"
    PRICE_SYMBOLS: str = "BTCUSDT,ETHUSDT"

    # Admin and secrets management
    SECRET_ENC_KEY: str = "change-me-please-32-bytes-min"
    ADMIN_API_TOKEN: str = "set-admin-token"

    # Monitor/Gainers-Losers cache settings (Binance 24h)
    TOP24H_REFRESH_SEC: int = 20
    USDT_UNIVERSE_REFRESH_SEC: int = 1800
    TOP24H_TOPN: int = 200
    TOP24H_PRICE_FLOOR: float = 0.0001

    # Session-based trending (Coin Monitor style)
    TRENDING_REFRESH_SEC: int = 10
    MONITOR_LOSS_THRESHOLD_PCT: float = 2.0
    MONITOR_RECOVERY_PCT: float = 0.5

    @property
    def PRICE_SYMBOLS_LIST(self):
        return [s.strip().upper() for s in self.PRICE_SYMBOLS.split(",") if s.strip()]


@lru_cache()
def get_settings() -> "Settings":
    return Settings()  # type: ignore


settings = get_settings()
