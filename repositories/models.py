from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, validator


class Exercise(BaseModel):
    exercise_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    weight: Optional[float] = None
    reps: int
    sets: int = Field(default=1)
    rest_seconds: Optional[int] = None

    @validator("exercise_id", pre=True, always=True)
    def ensure_exercise_id(cls, v):
        """Генерировать ID если отсутствует (для обратной совместимости)."""
        return v if v else str(uuid.uuid4())


class WorkoutEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    day_of_week: Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    exercises: List[Exercise]
    workout_name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completion_count: int = Field(default=0)
    last_completed: Optional[datetime] = None

    @validator("entry_id", pre=True, always=True)
    def ensure_entry_id(cls, v):
        """Генерировать ID если отсутствует (для обратной совместимости)."""
        return v if v else str(uuid.uuid4())


class WorkoutPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: Optional[str] = None
    start_date: date
    entries: List[WorkoutEntry]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)

    @validator("entries")
    def ensure_entries(cls, value: List[WorkoutEntry]) -> List[WorkoutEntry]:
        if not value:
            raise ValueError("Workout plan must contain at least one entry")
        return value

    @validator("plan_id", pre=True, always=True)
    def ensure_plan_id(cls, v):
        """Генерировать ID если отсутствует (для обратной совместимости)."""
        return v if v else str(uuid.uuid4())


class UserProfile(BaseModel):
    user_id: str
    age: int
    gender: Literal["male", "female", "other"]
    weight: float
    goal: Literal["lose", "gain", "maintain"]
    experience: Literal["beginner", "intermediate", "advanced"]
    preferred_location: Literal["home", "gym"]
    workout_time: Literal["short", "medium", "long"]
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @validator("age")
    def validate_age(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Age must be positive")
        return value

    @validator("weight")
    def validate_weight(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Weight must be positive")
        return value


class ProgressEntry(BaseModel):
    user_id: str
    date: datetime = Field(default_factory=datetime.utcnow)
    weight: Optional[float] = None
    measurements: Dict[str, float] = Field(default_factory=dict)
    mood: Optional[Literal["low", "medium", "high"]] = None
    # completed_workouts удалено - используется WorkoutExecution вместо этого


class ExerciseProgress(BaseModel):
    """Прогресс по конкретному упражнению в рамках выполнения тренировки."""
    exercise_id: str
    exercise_name: str
    actual_weight: Optional[float] = None
    actual_reps: List[int] = Field(default_factory=list)
    completed_sets: int
    rating: Optional[Literal["easy", "normal", "hard"]] = None
    notes: Optional[str] = None


class WorkoutExecution(BaseModel):
    """Выполнение тренировки с детальным прогрессом по упражнениям."""
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    workout_entry_id: str
    plan_id: Optional[str] = None
    execution_date: datetime = Field(default_factory=datetime.utcnow)
    exercises_progress: List[ExerciseProgress] = Field(default_factory=list)
    overall_rating: Optional[Literal["easy", "normal", "hard"]] = None
    notes: Optional[str] = None
    body_weight: Optional[float] = None

    @validator("execution_id", pre=True, always=True)
    def ensure_execution_id(cls, v):
        """Генерировать ID если отсутствует."""
        return v if v else str(uuid.uuid4())


class ReminderConfig(BaseModel):
    user_id: str
    reminder_id: str
    type: Literal["training", "water"]
    time: time
    frequency: Literal["daily", "weekly"] = Field(default="daily")
    message: str
    enabled: bool = Field(default=True)
