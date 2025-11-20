from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, List, Optional

import matplotlib.pyplot as plt
from datetime import datetime

from config import settings
from repositories.models import ProgressEntry, WorkoutExecution
from utils.constants import MEDICAL_DISCLAIMER

logger = logging.getLogger(__name__)


def generate_progress_chart(user_id: str, entries: Iterable[ProgressEntry]) -> Path:
    """Генерировать график динамики веса тела."""
    entries = list(entries)
    if not entries:
        raise ValueError("No progress entries to build a chart")

    dates = [entry.date for entry in entries if entry.weight is not None]
    weights = [entry.weight for entry in entries if entry.weight is not None]

    if not dates or not weights:
        raise ValueError("Недостаточно данных о весе для построения графика")

    output_dir = settings.data_dir / "charts"
    output_dir.mkdir(parents=True, exist_ok=True)
    chart_path = output_dir / f"progress_{user_id}.png"

    plt.figure(figsize=(10, 6))
    plt.plot(dates, weights, marker="o", linestyle="-", linewidth=2, markersize=6)
    plt.title("Динамика веса тела", fontsize=14, fontweight="bold")
    plt.xlabel("Дата", fontsize=12)
    plt.ylabel("Вес (кг)", fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.figtext(0.5, 0.01, MEDICAL_DISCLAIMER, wrap=True, ha="center", fontsize=8)

    try:
        plt.tight_layout()
        plt.savefig(chart_path, dpi=150, bbox_inches="tight")
        logger.info("Progress chart saved to %s", chart_path)
    finally:
        plt.close()
    return chart_path


def generate_workout_executions_chart(user_id: str, executions: List[WorkoutExecution]) -> Path:
    """Генерировать график выполненных тренировок по датам."""
    if not executions:
        raise ValueError("Нет данных о выполненных тренировках")

    # Группируем по датам
    from collections import defaultdict
    dates_count = defaultdict(int)
    for execution in executions:
        date_key = execution.execution_date.date()
        dates_count[date_key] += 1

    dates = sorted(dates_count.keys())
    counts = [dates_count[d] for d in dates]

    output_dir = settings.data_dir / "charts"
    output_dir.mkdir(parents=True, exist_ok=True)
    chart_path = output_dir / f"workouts_{user_id}.png"

    plt.figure(figsize=(10, 6))
    plt.bar(dates, counts, color='#4CAF50', alpha=0.7, edgecolor='black', linewidth=1)
    plt.title("Количество выполненных тренировок", fontsize=14, fontweight="bold")
    plt.xlabel("Дата", fontsize=12)
    plt.ylabel("Количество тренировок", fontsize=12)
    plt.grid(True, alpha=0.3, axis='y')
    plt.xticks(rotation=45)
    plt.figtext(0.5, 0.01, MEDICAL_DISCLAIMER, wrap=True, ha="center", fontsize=8)

    try:
        plt.tight_layout()
        plt.savefig(chart_path, dpi=150, bbox_inches="tight")
        logger.info("Workout executions chart saved to %s", chart_path)
    finally:
        plt.close()
    return chart_path


def generate_exercise_progress_chart(user_id: str, exercise_name: str, executions: List[WorkoutExecution]) -> Path:
    """Генерировать график прогресса по конкретному упражнению."""
    # Собираем данные по упражнению
    exercise_data = []
    for execution in executions:
        for ex_progress in execution.exercises_progress:
            if ex_progress.exercise_name.lower() == exercise_name.lower():
                if ex_progress.actual_weight:
                    exercise_data.append({
                        'date': execution.execution_date,
                        'weight': ex_progress.actual_weight,
                        'reps': ex_progress.actual_reps[-1] if ex_progress.actual_reps else None,
                    })

    if not exercise_data:
        raise ValueError(f"Нет данных о прогрессе по упражнению '{exercise_name}'")

    exercise_data.sort(key=lambda x: x['date'])
    dates = [d['date'] for d in exercise_data]
    weights = [d['weight'] for d in exercise_data if d['weight']]

    if not weights:
        raise ValueError(f"Нет данных о весе для упражнения '{exercise_name}'")

    output_dir = settings.data_dir / "charts"
    output_dir.mkdir(parents=True, exist_ok=True)
    chart_path = output_dir / f"exercise_{user_id}_{exercise_name.replace(' ', '_')}.png"

    plt.figure(figsize=(10, 6))
    plt.plot(dates, weights, marker="o", linestyle="-", linewidth=2, markersize=8, color='#2196F3')
    plt.title(f"Прогресс по упражнению: {exercise_name}", fontsize=14, fontweight="bold")
    plt.xlabel("Дата", fontsize=12)
    plt.ylabel("Вес (кг)", fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.figtext(0.5, 0.01, MEDICAL_DISCLAIMER, wrap=True, ha="center", fontsize=8)

    try:
        plt.tight_layout()
        plt.savefig(chart_path, dpi=150, bbox_inches="tight")
        logger.info("Exercise progress chart saved to %s", chart_path)
    finally:
        plt.close()
    return chart_path
