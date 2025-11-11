from __future__ import annotations

import random
from datetime import date
from typing import Iterable, List, Optional

from repositories.models import Exercise, UserProfile, WorkoutEntry, WorkoutPlan
from repositories.storage import StorageRepository
from services.workout_templates import WorkoutTemplate, get_template, get_templates_by_filters

FOCUS_EXERCISES = {
    "legs": [
        "Приседания", "Выпады", "Подъём таза", "Пистолет", "Жим ногами",
    ],
    "back": [
        "Тяга верхнего блока", "Становая тяга", "Гиперэкстензия", "Тяга гантели",
    ],
    "cardio": [
        "Бёрпи", "Скакалка", "Бег на месте", "Велотренажер", "Эллипс",
    ],
}

WORKOUT_LENGTH_MAP = {
    "short": 3,
    "medium": 4,
    "long": 5,
}


class WorkoutService:
    """Generates and persists workout recommendations."""

    def __init__(self, storage: StorageRepository) -> None:
        self._storage = storage

    def generate_daily_workout(
        self,
        profile: UserProfile,
        focus: str,
        template_id: Optional[str] = None,
    ) -> WorkoutEntry:
        """Generate workout from template or randomly."""
        if template_id:
            template = get_template(template_id)
            if template:
                # Adjust weights based on profile
                exercises = []
                for ex in template.exercises:
                    adjusted_weight = ex.weight
                    if adjusted_weight and focus != "cardio":
                        adjusted_weight = self._adjust_weight_for_profile(adjusted_weight, profile)
                    exercises.append(
                        Exercise(
                            name=ex.name,
                            weight=adjusted_weight,
                            reps=ex.reps,
                            sets=ex.sets,
                            rest_seconds=ex.rest_seconds or 60,
                        )
                    )
                return WorkoutEntry(
                    day_of_week=date.today().strftime("%a").lower()[:3],
                    exercises=exercises,
                )

        # Fallback to random generation
        focus_key = focus if focus in FOCUS_EXERCISES else "legs"
        exercises = random.sample(
            FOCUS_EXERCISES[focus_key],
            k=min(WORKOUT_LENGTH_MAP[profile.workout_time], len(FOCUS_EXERCISES[focus_key])),
        )
        exercise_objects: List[Exercise] = []
        for name in exercises:
            weight = self._estimate_weight(profile, focus_key)
            exercise_objects.append(
                Exercise(
                    name=name,
                    weight=weight,
                    reps=self._estimate_reps(profile),
                    sets=3,
                    rest_seconds=60,
                )
            )
        return WorkoutEntry(day_of_week=date.today().strftime("%a").lower()[:3], exercises=exercise_objects)

    def _adjust_weight_for_profile(self, base_weight: float, profile: UserProfile) -> float:
        """Adjust template weight based on user profile."""
        modifier = {
            "beginner": 0.7,
            "intermediate": 1.0,
            "advanced": 1.3,
        }[profile.experience]
        return round(base_weight * modifier, 1)

    def _estimate_weight(self, profile: UserProfile, focus: str) -> float:
        base = profile.weight * 0.3 if focus != "cardio" else 0.0
        modifier = {
            "beginner": 0.8,
            "intermediate": 1.0,
            "advanced": 1.2,
        }[profile.experience]
        return round(base * modifier, 1)

    def _estimate_reps(self, profile: UserProfile) -> int:
        return {
            "lose": 15,
            "gain": 8,
            "maintain": 12,
        }[profile.goal]

    def save_plan(self, user_id: str, entries: Iterable[WorkoutEntry]) -> WorkoutPlan:
        plan = WorkoutPlan(
            user_id=user_id,
            start_date=date.today(),
            entries=list(entries),
        )
        self._storage.save_workout_plan(plan)
        return plan
    
    def save_standalone_workout(self, user_id: str, workout: WorkoutEntry) -> None:
        """Сохранить отдельную тренировку (не в плане)."""
        if hasattr(self._storage, 'save_standalone_workout'):
            self._storage.save_standalone_workout(user_id, workout)
        else:
            # Fallback: сохраняем как план с одной тренировкой
            self.save_plan(user_id, [workout])

    def list_plans(self, user_id: str) -> List[WorkoutPlan]:
        return list(self._storage.get_workout_plans(user_id))

    def get_available_templates(
        self,
        profile: Optional[UserProfile] = None,
        focus: Optional[str] = None,
    ) -> List[WorkoutTemplate]:
        """Get available workout templates filtered by profile."""
        location = profile.preferred_location if profile else None
        experience = profile.experience if profile else None
        return get_templates_by_filters(focus=focus, location=location, experience=experience)
