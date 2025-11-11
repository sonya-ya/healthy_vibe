from __future__ import annotations

from statistics import mean
from typing import Dict, Iterable, List, Optional

from repositories.models import ProgressEntry
from repositories.storage import StorageRepository


class ProgressService:
    """Handles user progress persistence and analytics."""

    def __init__(self, storage: StorageRepository) -> None:
        self._storage = storage

    def add_entry(self, entry: ProgressEntry) -> None:
        self._storage.add_progress_entry(entry)

    def fetch_entries(self, user_id: str) -> List[ProgressEntry]:
        return list(self._storage.list_progress(user_id))

    def summarize(self, user_id: str) -> Dict[str, Optional[float]]:
        entries = self.fetch_entries(user_id)
        if not entries:
            # Проверяем, есть ли выполнения тренировок
            try:
                executions = self._storage.get_workout_executions(user_id)
                sessions = len(executions)
            except AttributeError:
                # Если метод не доступен (старая версия хранилища)
                sessions = 0
            return {"average_weight": None, "sessions": sessions}
        
        weights = [e.weight for e in entries if e.weight]
        avg_weight = mean(weights) if weights else None
        
        # Подсчитываем количество выполненных тренировок из WorkoutExecution
        try:
            executions = self._storage.get_workout_executions(user_id)
            sessions = len(executions)
        except AttributeError:
            # Если метод не доступен (старая версия хранилища)
            sessions = 0
        
        return {
            "average_weight": avg_weight,
            "sessions": sessions,
        }

    def last_workouts(self, user_id: str, limit: int = 5) -> List[ProgressEntry]:
        entries = self.fetch_entries(user_id)
        return sorted(entries, key=lambda e: e.date, reverse=True)[:limit]


class EnhancedProgressService(ProgressService):
    """Расширенный сервис для отслеживания прогресса с поддержкой WorkoutExecution."""
    
    def get_workout_progress(self, user_id: str, workout_entry_id: str) -> List:
        """Получить прогресс по тренировке."""
        from repositories.models import WorkoutExecution
        return self._storage.get_workout_executions(user_id, workout_entry_id)
    
    def get_exercise_progress(self, user_id: str, exercise_name: str) -> List:
        """Получить прогресс по упражнению."""
        return self._storage.get_exercise_progress_history(user_id, exercise_name)
    
    def get_exercise_statistics(self, user_id: str, exercise_name: str) -> Dict:
        """Получить статистику по упражнению."""
        progress_history = self.get_exercise_progress(user_id, exercise_name)
        if not progress_history:
            return {
                "current_weight": None,
                "current_reps": None,
                "progress": "Нет данных",
            }
        
        # Получаем последние данные
        latest = progress_history[-1]
        weights = [p.actual_weight for p in progress_history if p.actual_weight]
        
        return {
            "current_weight": latest.actual_weight,
            "current_reps": latest.actual_reps[-1] if latest.actual_reps else None,
            "progress": f"+{weights[-1] - weights[0]:.1f} кг" if len(weights) > 1 and weights[0] else "Нет данных",
        }
