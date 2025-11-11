from __future__ import annotations

from typing import Dict, Tuple

from pydantic import ValidationError as PydanticValidationError

from repositories.models import UserProfile
from utils.exceptions import ValidationError


def validate_profile_data(raw_data: Dict[str, str]) -> Tuple[UserProfile, str]:
    """Construct UserProfile from raw string data, raising ValidationError if invalid."""
    try:
        profile = UserProfile(**raw_data)
    except PydanticValidationError as exc:  # pragma: no cover - simple passthrough
        raise ValidationError(str(exc)) from exc
    return profile, "Профиль обновлён"


def validate_age(age_str: str) -> Tuple[bool, int | None, str]:
    """Валидация возраста."""
    try:
        age = int(age_str.strip())
        if age < 10:
            return False, None, "Возраст должен быть не менее 10 лет"
        if age > 100:
            return False, None, "Возраст должен быть не более 100 лет"
        return True, age, ""
    except ValueError:
        return False, None, "Пожалуйста, введите число"


def validate_weight(weight_str: str) -> Tuple[bool, float | None, str]:
    """Валидация веса."""
    try:
        weight = float(weight_str.strip().replace(",", "."))
        if weight < 20:
            return False, None, "Вес должен быть не менее 20 кг"
        if weight > 300:
            return False, None, "Вес должен быть не более 300 кг"
        return True, weight, ""
    except ValueError:
        return False, None, "Пожалуйста, введите число (можно с десятичной точкой)"


def validate_reps(reps_str: str) -> Tuple[bool, int | None, str]:
    """Валидация количества повторений."""
    try:
        reps = int(reps_str.strip())
        if reps < 1:
            return False, None, "Количество повторений должно быть не менее 1"
        if reps > 100:
            return False, None, "Количество повторений должно быть не более 100"
        return True, reps, ""
    except ValueError:
        return False, None, "Пожалуйста, введите число"


def validate_sets(sets_str: str) -> Tuple[bool, int | None, str]:
    """Валидация количества подходов."""
    try:
        sets = int(sets_str.strip())
        if sets < 1:
            return False, None, "Количество подходов должно быть не менее 1"
        if sets > 10:
            return False, None, "Количество подходов должно быть не более 10"
        return True, sets, ""
    except ValueError:
        return False, None, "Пожалуйста, введите число"


def validate_exercise_weight(weight_str: str) -> Tuple[bool, float | None, str]:
    """Валидация веса для упражнения."""
    try:
        weight = float(weight_str.strip().replace(",", "."))
        if weight < 0:
            return False, None, "Вес не может быть отрицательным"
        if weight > 500:
            return False, None, "Вес должен быть не более 500 кг"
        return True, weight, ""
    except ValueError:
        return False, None, "Пожалуйста, введите число (можно с десятичной точкой) или 0"
