from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

# Load .env file if it exists
load_dotenv()


class Settings(BaseModel):
    """Application configuration loaded from environment or .env files."""

    bot_token: str = Field(default="")
    openai_api_key: Optional[str] = Field(default=None)
    data_dir: Path = Field(default=Path("data"))
    logs_dir: Path = Field(default=Path("logs"))
    timezone: str = Field(default="Europe/Moscow")
    environment: str = Field(default="development")
    webhook_url: Optional[str] = Field(default=None)
    polling_interval: float = Field(default=1.0)

    @field_validator("data_dir", "logs_dir", mode="before")
    @classmethod
    def ensure_path(cls, value: str | Path) -> Path:
        return Path(value)

    @classmethod
    def load_from_env(cls) -> "Settings":
        """Load settings from environment variables."""
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        # Remove quotes if present
        if bot_token.startswith('"') and bot_token.endswith('"'):
            bot_token = bot_token[1:-1]
        if bot_token.startswith("'") and bot_token.endswith("'"):
            bot_token = bot_token[1:-1]

        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        if openai_key.startswith('"') and openai_key.endswith('"'):
            openai_key = openai_key[1:-1]
        if openai_key.startswith("'") and openai_key.endswith("'"):
            openai_key = openai_key[1:-1] if openai_key else None

        return cls(
            bot_token=bot_token,
            openai_api_key=openai_key if openai_key else None,
            data_dir=Path(os.getenv("DATA_DIR", "data")),
            logs_dir=Path(os.getenv("LOGS_DIR", "logs")),
            timezone=os.getenv("TIMEZONE", "Europe/Moscow"),
            environment=os.getenv("ENVIRONMENT", "development"),
            webhook_url=os.getenv("WEBHOOK_URL"),
            polling_interval=float(os.getenv("POLLING_INTERVAL", "1.0")),
        )


settings = Settings.load_from_env()
