import enum
import functools

import pydantic_settings


class AppEnv(enum.Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TEST = "test"


class Settings(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_TITLE: str = "Bees-In-Kube API"
    APP_ENV: AppEnv = AppEnv.DEVELOPMENT

    RANCHER_BASE_URL: str = "https://localhost"
    RANCHER_API_TOKEN: str = "YOUR_API_TOKEN"
    RANCHER_VERIFY_SSL: bool = False
    RANCHER_TIMEOUT: float = 10.0


@functools.lru_cache
def get_settings() -> Settings:
    return Settings()
