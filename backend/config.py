"""Application configuration settings.

Loads configuration from environment variables and .env file.
Uses pydantic-settings for validation and type coercion.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Configuration is read from .env file and environment variables.
    All ElevenLabs-related settings control the TTS generation.

    Attributes:
        app_name: Application name for FastAPI docs.
        app_version: API version string.
        api_v1_prefix: URL prefix for v1 API routes.
        api_base_url: Base URL for the API server.
        debug: Enable debug mode.
        elevenlabs_api_key: API key for ElevenLabs text-to-speech.
        voice_id: Voice ID for ElevenLabs TTS.
        model_id: ElevenLabs model to use (default: eleven_flash_v2_5).
        output_format: Audio format from ElevenLabs (e.g., mp3_44100_128).
        use_static_example_video: Use static video instead of generating.
        static_example_video_path: Path to static example video file.
        sqlite_db_path: Path to SQLite database file.
    """
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
