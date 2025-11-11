from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt

from config import settings
from repositories.models import ProgressEntry
from utils.constants import MEDICAL_DISCLAIMER

logger = logging.getLogger(__name__)


def generate_progress_chart(user_id: str, entries: Iterable[ProgressEntry]) -> Path:
    entries = list(entries)
    if not entries:
        raise ValueError("No progress entries to build a chart")

    dates = [entry.date for entry in entries if entry.weight is not None]
    weights = [entry.weight for entry in entries if entry.weight is not None]

    output_dir = settings.data_dir / "charts"
    output_dir.mkdir(parents=True, exist_ok=True)
    chart_path = output_dir / f"progress_{user_id}.png"

    plt.figure(figsize=(8, 4))
    plt.plot(dates, weights, marker="o", linestyle="-")
    plt.title("Динамика веса")
    plt.xlabel("Дата")
    plt.ylabel("Вес (кг)")
    plt.grid(True)
    plt.figtext(0.5, 0.01, MEDICAL_DISCLAIMER, wrap=True, ha="center", fontsize=8)

    try:
        plt.tight_layout()
        plt.savefig(chart_path)
        logger.info("Progress chart saved to %s", chart_path)
    finally:
        plt.close()
    return chart_path
