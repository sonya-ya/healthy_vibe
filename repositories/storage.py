from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, List, Optional

from .models import (
    ExerciseProgress,
    ProgressEntry,
    ReminderConfig,
    UserProfile,
    WorkoutEntry,
    WorkoutExecution,
    WorkoutPlan,
)


class StorageRepository(ABC):
    """Abstract interface for persistent storage of user-related data."""

    # User profiles
    @abstractmethod
    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        raise NotImplementedError

    @abstractmethod
    def save_profile(self, profile: UserProfile) -> None:
        raise NotImplementedError

    # Workout plans
    @abstractmethod
    def save_workout_plan(self, plan: WorkoutPlan) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_workout_plans(self, user_id: str) -> Iterable[WorkoutPlan]:
        raise NotImplementedError

    # Workout entries (новые методы)
    @abstractmethod
    def get_workout_entry(self, user_id: str, entry_id: str) -> Optional[WorkoutEntry]:
        """Получить конкретную тренировку по ID."""
        raise NotImplementedError

    @abstractmethod
    def get_workout_entries_by_day(self, user_id: str, day: str) -> List[WorkoutEntry]:
        """Получить все тренировки пользователя для конкретного дня."""
        raise NotImplementedError

    @abstractmethod
    def get_all_workout_entries(self, user_id: str) -> List[WorkoutEntry]:
        """Получить все тренировки пользователя из всех планов."""
        raise NotImplementedError

    @abstractmethod
    def update_workout_entry(self, user_id: str, entry_id: str, entry: WorkoutEntry) -> None:
        """Обновить тренировку."""
        raise NotImplementedError

    @abstractmethod
    def delete_workout_entry(self, user_id: str, entry_id: str) -> None:
        """Удалить тренировку."""
        raise NotImplementedError

    @abstractmethod
    def get_active_plans(self, user_id: str) -> List[WorkoutPlan]:
        """Получить все активные планы пользователя."""
        raise NotImplementedError

    @abstractmethod
    def deactivate_plan(self, user_id: str, plan_id: str) -> None:
        """Деактивировать план."""
        raise NotImplementedError

    # Workout executions (новые методы)
    @abstractmethod
    def save_workout_execution(self, execution: WorkoutExecution) -> None:
        """Сохранить выполнение тренировки."""
        raise NotImplementedError

    @abstractmethod
    def get_workout_executions(self, user_id: str, workout_entry_id: Optional[str] = None) -> List[WorkoutExecution]:
        """Получить все выполнения тренировок."""
        raise NotImplementedError

    @abstractmethod
    def get_exercise_progress_history(self, user_id: str, exercise_name: str) -> List[ExerciseProgress]:
        """Получить историю прогресса по упражнению."""
        raise NotImplementedError

    # Progress entries
    @abstractmethod
    def add_progress_entry(self, entry: ProgressEntry) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_progress(self, user_id: str) -> Iterable[ProgressEntry]:
        raise NotImplementedError

    # Reminders
    @abstractmethod
    def save_reminder(self, reminder: ReminderConfig) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_reminders(self, user_id: str) -> Iterable[ReminderConfig]:
        raise NotImplementedError

    @abstractmethod
    def delete_reminder(self, user_id: str, reminder_id: str) -> None:
        raise NotImplementedError
