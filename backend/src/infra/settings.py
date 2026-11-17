import enum

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

    APP_TITLE: str = "Bees-In-Kube API"  # # отображается в автосгенерированных доках /docs

    APP_ENV: AppEnv = AppEnv.DEVELOPMENT
