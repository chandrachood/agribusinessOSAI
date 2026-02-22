try:
    # Pydantic v2 preferred path
    from pydantic_settings import BaseSettings, SettingsConfigDict
    HAS_PYDANTIC_SETTINGS = True
except ImportError:
    # Compatibility fallback when pydantic-settings is not installed
    try:
        from pydantic.v1 import BaseSettings
    except ImportError:
        from pydantic import BaseSettings
    HAS_PYDANTIC_SETTINGS = False


class Settings(BaseSettings):
    app_name: str = "Banking Product Analyzer"
    environment: str = "dev"
    gemini_api_key: str | None = None
    gemini_model_id: str = "gemini-flash-lite-latest"

    if HAS_PYDANTIC_SETTINGS:
        model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    else:
        class Config:
            env_file = ".env"
            extra = "ignore"


settings = Settings()
