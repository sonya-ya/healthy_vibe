from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from repositories.models import WorkoutEntry
from repositories.storage import StorageRepository


class WorkoutManagementService:
    """Сервис для управления тренировками."""

    def __init__(self, storage: StorageRepository):
        self._storage = storage

    def get_all_workouts(self, user_id: str) -> Dict[str, List[WorkoutEntry]]:
        """Получить все тренировки, сгруппированные по дням недели."""
        workouts = self._storage.get_all_workout_entries(user_id)
        grouped = defaultdict(list)
        for workout in workouts:
            grouped[workout.day_of_week].append(workout)
        return dict(grouped)

    def get_workout_by_id(self, user_id: str, entry_id: str) -> Optional[WorkoutEntry]:
        """Получить тренировку по ID."""
        return self._storage.get_workout_entry(user_id, entry_id)

    def delete_workout(self, user_id: str, entry_id: str) -> None:
        """Удалить тренировку."""
        self._storage.delete_workout_entry(user_id, entry_id)

    def update_workout(self, user_id: str, entry_id: str, entry: WorkoutEntry) -> None:
        """Обновить тренировку."""
        self._storage.update_workout_entry(user_id, entry_id, entry)

    def get_workout_statistics(self, user_id: str, entry_id: str) -> Dict:
        """Получить статистику по тренировке."""
        workout = self.get_workout_by_id(user_id, entry_id)
        if not workout:
            return {}
        
        executions = self._storage.get_workout_executions(user_id, entry_id)
        
        return {
            "workout_name": workout.workout_name or "Без названия",
            "completion_count": workout.completion_count,
            "last_completed": workout.last_completed,
            "total_executions": len(executions),
            "exercises_count": len(workout.exercises),
        }

