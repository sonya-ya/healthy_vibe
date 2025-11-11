from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import settings


def configure_logging() -> None:
    """Configure root logger for the application."""
    log_dir: Path = settings.logs_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    log_path = log_dir / "bot.log"
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(log_path, maxBytes=2 * 1024 * 1024, backupCount=3)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])
