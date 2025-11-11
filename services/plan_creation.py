from __future__ import annotations

from typing import Dict, List, Optional

from repositories.models import WorkoutEntry, WorkoutPlan
from repositories.storage import StorageRepository


class PlanCreationService:
    """Сервис для создания планов из тренировок."""

    def __init__(self, storage: StorageRepository):
        self._storage = storage

    def create_plan_from_workouts(
        self,
        user_id: str,
        workouts_by_day: Dict[str, str],  # day -> entry_id
        plan_name: Optional[str] = None,
    ) -> WorkoutPlan:
        """Создать план из существующих тренировок."""
        from datetime import date
        
        entries = []
        for day, entry_id in workouts_by_day.items():
            if entry_id:  # Если выбрана тренировка (не отдых)
                workout = self._storage.get_workout_entry(user_id, entry_id)
                if workout:
                    entries.append(workout)
        
        if not entries:
            raise ValueError("План должен содержать хотя бы одну тренировку")
        
        plan = WorkoutPlan(
            user_id=user_id,
            name=plan_name,
            start_date=date.today(),
            entries=entries,
            is_active=True,
        )
        
        self._storage.save_workout_plan(plan)
        return plan

    def get_available_workouts_for_day(self, user_id: str, day: str) -> List[WorkoutEntry]:
        """Получить доступные тренировки для дня."""
        return self._storage.get_workout_entries_by_day(user_id, day)

