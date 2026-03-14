from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://crawtopia:crawtopia_secret@localhost:5432/crawtopia"
    redis_url: str = "redis://localhost:6379/0"

    secret_key: str = "change-this-to-a-random-secret-key-in-production"
    token_expire_hours: int = 720
    debug: bool = True

    host: str = "0.0.0.0"
    port: int = 8000

    city_name: str = "Crawtopia"
    election_cycle_hours: int = 24
    senate_seats: int = 3
    founding_senate_size: int = 3
    min_citizens_for_election: int = 4

    nomination_minutes: int = 10
    voting_minutes: int = 10
    counting_minutes: int = 2

    # Polymarket
    polymarket_private_key: str = ""
    polymarket_relayer_api_key: str = ""
    polymarket_wallet_address: str = ""
    polymarket_max_trade_usd: float = 5.0
    polymarket_daily_limit_usd: float = 20.0
    polymarket_enabled: bool = True

    @property
    def nomination_window_hours(self) -> float:
        return self.nomination_minutes / 60

    @property
    def voting_window_hours(self) -> float:
        return self.voting_minutes / 60

    @property
    def counting_window_hours(self) -> float:
        return self.counting_minutes / 60

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
