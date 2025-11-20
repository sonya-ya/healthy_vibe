from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from config import settings
from utils.exceptions import StorageError

from .models import (
    ExerciseProgress,
    ProgressEntry,
    ReminderConfig,
    UserProfile,
    WorkoutEntry,
    WorkoutExecution,
    WorkoutPlan,
)
from .storage import StorageRepository

logger = logging.getLogger(__name__)


class FileStorageRepository(StorageRepository):
    """File-based storage using JSON persistent files."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._base_dir = (base_dir or settings.data_dir).resolve()
        self._profiles_path = self._base_dir / "users.json"
        self._progress_dir = self._base_dir / "progress"
        self._reminders_path = self._base_dir / "reminders.json"
        self._workouts_dir = self._base_dir / "workouts"
        self._lock = threading.Lock()

        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._workouts_dir.mkdir(parents=True, exist_ok=True)
        self._progress_dir.mkdir(parents=True, exist_ok=True)

        if not self._profiles_path.exists():
            self._profiles_path.write_text("{}", encoding="utf-8")
            logger.debug("Created profiles file: %s", self._profiles_path)
        if not self._reminders_path.exists():
            self._reminders_path.write_text("{}", encoding="utf-8")
            logger.debug("Created reminders file: %s", self._reminders_path)
        
        logger.info("FileStorageRepository initialized: base_dir=%s", self._base_dir)

    # Utilities -----------------------------------------------------------------
    def _read_json(self, path: Path) -> Dict[str, object]:
        logger.debug("Reading JSON file: %s", path)
        try:
            if not path.exists():
                logger.debug("File does not exist, returning empty dict: %s", path)
                return {}
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
                logger.debug("JSON file read successfully: path=%s, keys_count=%d", path, len(data) if isinstance(data, dict) else 0)
                return data
        except json.JSONDecodeError as exc:
            logger.error("Failed to decode JSON from %s: %s", path, exc)
            raise StorageError(f"Cannot decode JSON from {path}") from exc

    def _write_json(self, path: Path, payload: Dict[str, object]) -> None:
        logger.debug("Writing JSON file: %s, keys_count=%d", path, len(payload))
        temp_path = path.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2, default=str)
        temp_path.replace(path)
        logger.debug("JSON file written successfully: %s", path)

    # Profiles -------------------------------------------------------------------
    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        logger.debug("Getting profile: user_id=%s", user_id)
        data = self._read_json(self._profiles_path)
        raw = data.get(user_id)
        if raw:
            profile = UserProfile.parse_obj(raw)
            logger.debug("Profile found: user_id=%s, goal=%s, experience=%s", 
                        user_id, profile.goal, profile.experience)
            return profile
        else:
            logger.debug("Profile not found: user_id=%s", user_id)
            return None

    def save_profile(self, profile: UserProfile) -> None:
        logger.info("Saving profile: user_id=%s, goal=%s, experience=%s", 
                   profile.user_id, profile.goal, profile.experience)
        with self._lock:
            data = self._read_json(self._profiles_path)
            data[profile.user_id] = profile.dict()
            self._write_json(self._profiles_path, data)
        logger.info("Profile saved successfully: user_id=%s", profile.user_id)

    # Workouts -------------------------------------------------------------------
    def _workout_path(self, user_id: str) -> Path:
        return self._workouts_dir / f"{user_id}.json"

    def _load_workout_data(self, user_id: str) -> Dict:
        """Загрузить данные тренировок пользователя."""
        path = self._workout_path(user_id)
        if not path.exists():
            return {"plans": [], "standalone_workouts": []}
        
        with path.open("r", encoding="utf-8") as file:
            raw = json.load(file)
        
        # Поддержка старого формата (массив планов)
        if isinstance(raw, list):
            return {"plans": raw, "standalone_workouts": []}
        
        # Новый формат
        return {
            "plans": raw.get("plans", []),
            "standalone_workouts": raw.get("standalone_workouts", []),
        }

    def _save_workout_data(self, user_id: str, data: Dict) -> None:
        """Сохранить данные тренировок пользователя."""
        path = self._workout_path(user_id)
        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2, default=str)

    def save_workout_plan(self, plan: WorkoutPlan) -> None:
        with self._lock:
            data = self._load_workout_data(plan.user_id)
            plans = [WorkoutPlan.parse_obj(item) for item in data["plans"]]
            
            # Проверяем, не существует ли уже план с таким ID
            existing_index = None
            for i, p in enumerate(plans):
                if p.plan_id == plan.plan_id:
                    existing_index = i
                    break
            
            if existing_index is not None:
                plans[existing_index] = plan
            else:
                plans.append(plan)
            
            data["plans"] = [p.dict() for p in plans]
            self._save_workout_data(plan.user_id, data)

    def _load_plans(self, user_id: str) -> List[WorkoutPlan]:
        data = self._load_workout_data(user_id)
        return [WorkoutPlan.parse_obj(item) for item in data["plans"]]

    def get_workout_plans(self, user_id: str) -> Iterable[WorkoutPlan]:
        return self._load_plans(user_id)

    def get_workout_entry(self, user_id: str, entry_id: str) -> Optional[WorkoutEntry]:
        """Получить конкретную тренировку по ID."""
        # Ищем в планах
        for plan in self._load_plans(user_id):
            for entry in plan.entries:
                if entry.entry_id == entry_id:
                    return entry
        
        # Ищем в standalone тренировках
        data = self._load_workout_data(user_id)
        for workout_dict in data["standalone_workouts"]:
            workout = WorkoutEntry.parse_obj(workout_dict)
            if workout.entry_id == entry_id:
                return workout
        
        return None

    def get_workout_entries_by_day(self, user_id: str, day: str) -> List[WorkoutEntry]:
        """Получить все тренировки пользователя для конкретного дня."""
        result = []
        
        # Из планов
        for plan in self._load_plans(user_id):
            for entry in plan.entries:
                if entry.day_of_week == day:
                    result.append(entry)
        
        # Из standalone тренировок
        data = self._load_workout_data(user_id)
        for workout_dict in data["standalone_workouts"]:
            workout = WorkoutEntry.parse_obj(workout_dict)
            if workout.day_of_week == day:
                result.append(workout)
        
        return result

    def get_all_workout_entries(self, user_id: str) -> List[WorkoutEntry]:
        """Получить все тренировки пользователя из всех планов."""
        result = []
        
        # Из планов
        for plan in self._load_plans(user_id):
            result.extend(plan.entries)
        
        # Из standalone тренировок
        data = self._load_workout_data(user_id)
        for workout_dict in data["standalone_workouts"]:
            result.append(WorkoutEntry.parse_obj(workout_dict))
        
        return result

    def update_workout_entry(self, user_id: str, entry_id: str, entry: WorkoutEntry) -> None:
        """Обновить тренировку."""
        with self._lock:
            data = self._load_workout_data(user_id)
            
            # Обновляем в планах
            plans = [WorkoutPlan.parse_obj(item) for item in data["plans"]]
            for plan in plans:
                for i, e in enumerate(plan.entries):
                    if e.entry_id == entry_id:
                        plan.entries[i] = entry
                        data["plans"] = [p.dict() for p in plans]
                        self._save_workout_data(user_id, data)
                        return
            
            # Обновляем в standalone тренировках
            workouts = [WorkoutEntry.parse_obj(item) for item in data["standalone_workouts"]]
            for i, w in enumerate(workouts):
                if w.entry_id == entry_id:
                    workouts[i] = entry
                    data["standalone_workouts"] = [w.dict() for w in workouts]
                    self._save_workout_data(user_id, data)
                    return
            
            raise StorageError(f"Workout entry {entry_id} not found")

    def delete_workout_entry(self, user_id: str, entry_id: str) -> None:
        """Удалить тренировку."""
        with self._lock:
            data = self._load_workout_data(user_id)
            
            # Удаляем из планов
            plans = [WorkoutPlan.parse_obj(item) for item in data["plans"]]
            for plan in plans:
                plan.entries = [e for e in plan.entries if e.entry_id != entry_id]
            data["plans"] = [p.dict() for p in plans]
            
            # Удаляем из standalone тренировок
            workouts = [WorkoutEntry.parse_obj(item) for item in data["standalone_workouts"]]
            workouts = [w for w in workouts if w.entry_id != entry_id]
            data["standalone_workouts"] = [w.dict() for w in workouts]
            
            self._save_workout_data(user_id, data)

    def get_active_plans(self, user_id: str) -> List[WorkoutPlan]:
        """Получить все активные планы пользователя."""
        plans = self._load_plans(user_id)
        return [p for p in plans if p.is_active]

    def deactivate_plan(self, user_id: str, plan_id: str) -> None:
        """Деактивировать план."""
        with self._lock:
            data = self._load_workout_data(user_id)
            plans = [WorkoutPlan.parse_obj(item) for item in data["plans"]]
            
            for plan in plans:
                if plan.plan_id == plan_id:
                    plan.is_active = False
                    break
            
            data["plans"] = [p.dict() for p in plans]
            self._save_workout_data(user_id, data)

    def save_standalone_workout(self, user_id: str, workout: WorkoutEntry) -> None:
        """Сохранить отдельную тренировку (не в плане)."""
        with self._lock:
            data = self._load_workout_data(user_id)
            workouts = [WorkoutEntry.parse_obj(item) for item in data["standalone_workouts"]]
            
            # Проверяем, не существует ли уже тренировка с таким ID
            existing_index = None
            for i, w in enumerate(workouts):
                if w.entry_id == workout.entry_id:
                    existing_index = i
                    break
            
            if existing_index is not None:
                workouts[existing_index] = workout
            else:
                workouts.append(workout)
            
            data["standalone_workouts"] = [w.dict() for w in workouts]
            self._save_workout_data(user_id, data)

    # Progress -------------------------------------------------------------------
    def _progress_path(self, user_id: str) -> Path:
        return self._progress_dir / f"{user_id}.json"

    def _load_progress_data(self, user_id: str) -> Dict:
        """Загрузить данные прогресса пользователя."""
        path = self._progress_path(user_id)
        if not path.exists():
            return {"body_progress": [], "workout_executions": []}
        
        with path.open("r", encoding="utf-8") as file:
            raw = json.load(file)
        
        # Поддержка старого формата (массив ProgressEntry)
        if isinstance(raw, list):
            return {"body_progress": raw, "workout_executions": []}
        
        # Новый формат
        return {
            "body_progress": raw.get("body_progress", []),
            "workout_executions": raw.get("workout_executions", []),
        }

    def _save_progress_data(self, user_id: str, data: Dict) -> None:
        """Сохранить данные прогресса пользователя."""
        path = self._progress_path(user_id)
        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2, default=str)

    def add_progress_entry(self, entry: ProgressEntry) -> None:
        with self._lock:
            data = self._load_progress_data(entry.user_id)
            body_progress = [ProgressEntry.parse_obj(item) for item in data["body_progress"]]
            body_progress.append(entry)
            data["body_progress"] = [e.dict() for e in body_progress]
            self._save_progress_data(entry.user_id, data)

    def list_progress(self, user_id: str) -> Iterable[ProgressEntry]:
        data = self._load_progress_data(user_id)
        return [ProgressEntry.parse_obj(item) for item in data["body_progress"]]

    def save_workout_execution(self, execution: WorkoutExecution) -> None:
        """Сохранить выполнение тренировки."""
        with self._lock:
            data = self._load_progress_data(execution.user_id)
            executions = [WorkoutExecution.parse_obj(item) for item in data["workout_executions"]]
            executions.append(execution)
            data["workout_executions"] = [e.dict() for e in executions]
            self._save_progress_data(execution.user_id, data)
            
            # Обновляем статистику тренировки
            workout = self.get_workout_entry(execution.user_id, execution.workout_entry_id)
            if workout:
                workout.completion_count += 1
                workout.last_completed = execution.execution_date
                self.update_workout_entry(execution.user_id, execution.workout_entry_id, workout)

    def get_workout_executions(self, user_id: str, workout_entry_id: Optional[str] = None) -> List[WorkoutExecution]:
        """Получить все выполнения тренировок."""
        data = self._load_progress_data(user_id)
        executions = [WorkoutExecution.parse_obj(item) for item in data["workout_executions"]]
        
        if workout_entry_id:
            return [e for e in executions if e.workout_entry_id == workout_entry_id]
        
        return executions

    def get_exercise_progress_history(self, user_id: str, exercise_name: str) -> List[ExerciseProgress]:
        """Получить историю прогресса по упражнению."""
        data = self._load_progress_data(user_id)
        executions = [WorkoutExecution.parse_obj(item) for item in data["workout_executions"]]
        
        result = []
        for execution in executions:
            for exercise_progress in execution.exercises_progress:
                if exercise_progress.exercise_name.lower() == exercise_name.lower():
                    result.append(exercise_progress)
        
        return result

    # Reminders ------------------------------------------------------------------
    def save_reminder(self, reminder: ReminderConfig) -> None:
        with self._lock:
            data = self._read_json(self._reminders_path)
            user_reminders: Dict[str, Dict[str, object]] = data.get(reminder.user_id, {})
            user_reminders[reminder.reminder_id] = reminder.dict()
            data[reminder.user_id] = user_reminders
            self._write_json(self._reminders_path, data)

    def list_reminders(self, user_id: str) -> Iterable[ReminderConfig]:
        data = self._read_json(self._reminders_path)
        user_reminders = data.get(user_id, {})
        return [ReminderConfig.parse_obj(item) for item in user_reminders.values()]

    def delete_reminder(self, user_id: str, reminder_id: str) -> None:
        with self._lock:
            data = self._read_json(self._reminders_path)
            user_reminders = data.get(user_id, {})
            if reminder_id in user_reminders:
                user_reminders.pop(reminder_id)
                data[user_id] = user_reminders
                self._write_json(self._reminders_path, data)
