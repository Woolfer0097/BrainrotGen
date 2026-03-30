from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BrainrotGen API"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    debug: bool = False
    elevenlabs_api_key: str = ""
    voice_id: str = "eleven_flash_v2_5"
    output_format: str = "mp3_44100_128"

    sqlite_db_path: str = "./app.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.sqlite_db_path}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
