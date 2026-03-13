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
    founding_senate_size: int = 10
    min_citizens_for_election: int = 10

    # Derived from election_cycle_hours
    @property
    def nomination_window_hours(self) -> float:
        return self.election_cycle_hours * (2 / 24)

    @property
    def voting_window_hours(self) -> float:
        return self.election_cycle_hours * (1.5 / 24)

    @property
    def counting_window_hours(self) -> float:
        return self.election_cycle_hours * (0.25 / 24)

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
