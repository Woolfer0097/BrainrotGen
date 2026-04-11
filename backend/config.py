from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BrainrotGen API"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    api_base_url: str = "http://127.0.0.1:8000"
    debug: bool = False
    elevenlabs_api_key: str = ""
    voice_id: str = ""
    model_id: str = "eleven_flash_v2_5"
    output_format: str = "mp3_44100_128"

    use_static_example_video: bool = False
    static_example_video_path: str = "assets/example.mp4"

    sqlite_db_path: str = "./app.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.sqlite_db_path}"

    @property
    def static_example_video_file(self) -> Path:
        root = Path(__file__).resolve().parents[1]
        path = Path(self.static_example_video_path)
        return path if path.is_absolute() else root / path


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
