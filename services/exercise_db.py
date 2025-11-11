from __future__ import annotations

from typing import Dict, List

# База данных упражнений по категориям
EXERCISES_BY_CATEGORY: Dict[str, List[str]] = {
    "legs": [
        "Приседания",
        "Выпады",
        "Жим ногами",
        "Разгибание ног",
        "Сгибание ног",
        "Подъём на носки",
        "Болгарские выпады",
        "Пистолет",
        "Подъём таза",
        "Приседания с прыжком",
    ],
    "back": [
        "Тяга верхнего блока",
        "Тяга нижнего блока",
        "Становая тяга",
        "Тяга гантели",
        "Гиперэкстензия",
        "Подтягивания",
        "Тяга штанги",
        "Супермен",
        "Обратные отжимания",
    ],
    "chest": [
        "Жим лёжа",
        "Отжимания",
        "Жим гантелей",
        "Разводка гантелей",
        "Отжимания на брусьях",
        "Пуловер",
        "Кроссоверы",
        "Отжимания с наклоном",
    ],
    "arms": [
        "Подъём на бицепс",
        "Французский жим",
        "Отжимания узким хватом",
        "Молотки",
        "Концентрированные сгибания",
        "Разгибание на трицепс",
        "Подтягивания обратным хватом",
    ],
    "shoulders": [
        "Жим над головой",
        "Махи гантелями",
        "Тяга к подбородку",
        "Разводка в стороны",
        "Армейский жим",
        "Боковые подъёмы",
        "Подъёмы вперед",
    ],
    "cardio": [
        "Бег",
        "Бёрпи",
        "Скакалка",
        "Велотренажер",
        "Эллипс",
        "Бег на месте",
        "Прыжки",
        "Гребля",
        "Планка",
    ],
}

# Названия категорий для отображения
CATEGORY_NAMES: Dict[str, str] = {
    "legs": "Ноги",
    "back": "Спина",
    "chest": "Грудь",
    "arms": "Руки",
    "shoulders": "Плечи",
    "cardio": "Кардио",
}

# Обратный словарь для получения категории по названию упражнения
EXERCISE_TO_CATEGORY: Dict[str, str] = {}
for category, exercises in EXERCISES_BY_CATEGORY.items():
    for exercise in exercises:
        EXERCISE_TO_CATEGORY[exercise] = category


def get_exercises_by_category(category: str) -> List[str]:
    """Получить список упражнений по категории."""
    return EXERCISES_BY_CATEGORY.get(category, [])


def get_all_categories() -> List[str]:
    """Получить список всех категорий."""
    return list(EXERCISES_BY_CATEGORY.keys())


def get_category_name(category: str) -> str:
    """Получить название категории для отображения."""
    return CATEGORY_NAMES.get(category, category)


def get_exercise_category(exercise_name: str) -> str | None:
    """Получить категорию упражнения."""
    return EXERCISE_TO_CATEGORY.get(exercise_name)


def search_exercises(query: str) -> List[str]:
    """Поиск упражнений по запросу."""
    query_lower = query.lower()
    results = []
    for exercise in EXERCISE_TO_CATEGORY.keys():
        if query_lower in exercise.lower():
            results.append(exercise)
    return results

