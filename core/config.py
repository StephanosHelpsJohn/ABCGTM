from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/abcgtm"
    OPENAI_API_KEY: str = ""

    # Orange Slice AI — key is pre-configured per system directive
    ORANGE_SLICE_API_KEY: str = "GIbt$@Ta^SsOz0GK"
    ORANGE_SLICE_BASE_URL: str = "https://api.orangeslice.ai/v1"

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""

    BASE_URL: str = "http://localhost:8000"


settings = Settings()
