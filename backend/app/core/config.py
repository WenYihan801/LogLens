"""Application configuration loaded from environment variables (NFR-07, FR-34)."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> repo root is three parents above backend/
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_DEFAULT_SAMPLE_DIR = _BACKEND_DIR.parent / "sample_data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    demo_read_only: bool = False

    database_url: str = "postgresql+psycopg://loglens:loglens@localhost:5432/loglens"

    # Comma-separated list, e.g. "http://localhost:5173,http://127.0.0.1:5173"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    max_upload_size_mb: float = 5
    max_log_lines: int = 20_000
    upload_rate_limit_per_minute: int = 10

    # How to interpret timestamps that carry no timezone (classic syslog SSH lines).
    ssh_log_timezone: str = "UTC"
    # Classic syslog lines have no year. 0 = use the current UTC year.
    ssh_log_year: int = 0

    sample_data_dir: Path = Field(default=_DEFAULT_SAMPLE_DIR)

    log_level: str = "INFO"

    @field_validator("sample_data_dir", mode="before")
    @classmethod
    def _expand(cls, v: object) -> object:
        return Path(str(v)).expanduser() if v else _DEFAULT_SAMPLE_DIR

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return int(self.max_upload_size_mb * 1024 * 1024)


@lru_cache
def get_settings() -> Settings:
    return Settings()
