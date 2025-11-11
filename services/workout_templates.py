from __future__ import annotations

from typing import Dict, List

from repositories.models import Exercise


class WorkoutTemplate:
    """Predefined workout template with exercises."""

    def __init__(
        self,
        template_id: str,
        name: str,
        description: str,
        focus: str,
        location: str,
        exercises: List[Exercise],
    ) -> None:
        self.template_id = template_id
        self.name = name
        self.description = description
        self.focus = focus
        self.location = location
        self.exercises = exercises


# Predefined workout templates
WORKOUT_TEMPLATES: Dict[str, WorkoutTemplate] = {}

# Home workouts
WORKOUT_TEMPLATES["home_legs_beginner"] = WorkoutTemplate(
    template_id="home_legs_beginner",
    name="Ноги дома (начальный)",
    description="Базовая тренировка ног без инвентаря",
    focus="legs",
    location="home",
    exercises=[
        Exercise(name="Приседания", weight=None, reps=15, sets=3, rest_seconds=60),
        Exercise(name="Выпады", weight=None, reps=12, sets=3, rest_seconds=60),
        Exercise(name="Подъём таза", weight=None, reps=15, sets=3, rest_seconds=45),
    ],
)

WORKOUT_TEMPLATES["home_back_beginner"] = WorkoutTemplate(
    template_id="home_back_beginner",
    name="Спина дома (начальный)",
    description="Укрепление спины без инвентаря",
    focus="back",
    location="home",
    exercises=[
        Exercise(name="Супермен", weight=None, reps=12, sets=3, rest_seconds=45),
        Exercise(name="Обратные отжимания", weight=None, reps=10, sets=3, rest_seconds=60),
        Exercise(name="Планка", weight=None, reps=1, sets=3, rest_seconds=30),
    ],
)

WORKOUT_TEMPLATES["home_cardio_beginner"] = WorkoutTemplate(
    template_id="home_cardio_beginner",
    name="Кардио дома (начальный)",
    description="Кардио тренировка для начинающих",
    focus="cardio",
    location="home",
    exercises=[
        Exercise(name="Бёрпи", weight=None, reps=10, sets=3, rest_seconds=60),
        Exercise(name="Скакалка", weight=None, reps=50, sets=3, rest_seconds=45),
        Exercise(name="Бег на месте", weight=None, reps=30, sets=3, rest_seconds=30),
    ],
)

WORKOUT_TEMPLATES["home_fullbody_beginner"] = WorkoutTemplate(
    template_id="home_fullbody_beginner",
    name="Всё тело дома (начальный)",
    description="Комплексная тренировка для всего тела",
    focus="fullbody",
    location="home",
    exercises=[
        Exercise(name="Приседания", weight=None, reps=15, sets=3, rest_seconds=60),
        Exercise(name="Отжимания", weight=None, reps=10, sets=3, rest_seconds=60),
        Exercise(name="Планка", weight=None, reps=1, sets=3, rest_seconds=30),
        Exercise(name="Бёрпи", weight=None, reps=8, sets=2, rest_seconds=90),
    ],
)

# Gym workouts
WORKOUT_TEMPLATES["gym_legs_beginner"] = WorkoutTemplate(
    template_id="gym_legs_beginner",
    name="Ноги в зале (начальный)",
    description="Базовая тренировка ног в тренажёрном зале",
    focus="legs",
    location="gym",
    exercises=[
        Exercise(name="Приседания со штангой", weight=20.0, reps=12, sets=3, rest_seconds=90),
        Exercise(name="Жим ногами", weight=30.0, reps=15, sets=3, rest_seconds=60),
        Exercise(name="Выпады с гантелями", weight=5.0, reps=12, sets=3, rest_seconds=60),
    ],
)

WORKOUT_TEMPLATES["gym_back_beginner"] = WorkoutTemplate(
    template_id="gym_back_beginner",
    name="Спина в зале (начальный)",
    description="Тренировка спины в тренажёрном зале",
    focus="back",
    location="gym",
    exercises=[
        Exercise(name="Тяга верхнего блока", weight=15.0, reps=12, sets=3, rest_seconds=90),
        Exercise(name="Тяга гантели одной рукой", weight=8.0, reps=10, sets=3, rest_seconds=60),
        Exercise(name="Гиперэкстензия", weight=None, reps=15, sets=3, rest_seconds=45),
    ],
)

WORKOUT_TEMPLATES["gym_chest_beginner"] = WorkoutTemplate(
    template_id="gym_chest_beginner",
    name="Грудь в зале (начальный)",
    description="Тренировка груди в тренажёрном зале",
    focus="chest",
    location="gym",
    exercises=[
        Exercise(name="Жим лёжа", weight=20.0, reps=10, sets=3, rest_seconds=90),
        Exercise(name="Отжимания на брусьях", weight=None, reps=8, sets=3, rest_seconds=60),
        Exercise(name="Разводка гантелей", weight=5.0, reps=12, sets=3, rest_seconds=60),
    ],
)

WORKOUT_TEMPLATES["gym_cardio_beginner"] = WorkoutTemplate(
    template_id="gym_cardio_beginner",
    name="Кардио в зале (начальный)",
    description="Кардио тренировка в тренажёрном зале",
    focus="cardio",
    location="gym",
    exercises=[
        Exercise(name="Беговая дорожка", weight=None, reps=10, sets=1, rest_seconds=0),
        Exercise(name="Велотренажер", weight=None, reps=10, sets=1, rest_seconds=0),
        Exercise(name="Эллипс", weight=None, reps=10, sets=1, rest_seconds=0),
    ],
)

# Intermediate templates
WORKOUT_TEMPLATES["home_legs_intermediate"] = WorkoutTemplate(
    template_id="home_legs_intermediate",
    name="Ноги дома (средний)",
    description="Продвинутая тренировка ног без инвентаря",
    focus="legs",
    location="home",
    exercises=[
        Exercise(name="Приседания с прыжком", weight=None, reps=15, sets=4, rest_seconds=60),
        Exercise(name="Болгарские выпады", weight=None, reps=12, sets=3, rest_seconds=60),
        Exercise(name="Пистолет", weight=None, reps=8, sets=3, rest_seconds=90),
        Exercise(name="Подъём таза на одной ноге", weight=None, reps=12, sets=3, rest_seconds=45),
    ],
)

WORKOUT_TEMPLATES["gym_legs_intermediate"] = WorkoutTemplate(
    template_id="gym_legs_intermediate",
    name="Ноги в зале (средний)",
    description="Продвинутая тренировка ног в зале",
    focus="legs",
    location="gym",
    exercises=[
        Exercise(name="Приседания со штангой", weight=40.0, reps=10, sets=4, rest_seconds=120),
        Exercise(name="Жим ногами", weight=50.0, reps=12, sets=3, rest_seconds=90),
        Exercise(name="Выпады с гантелями", weight=10.0, reps=12, sets=3, rest_seconds=60),
        Exercise(name="Разгибание ног", weight=20.0, reps=15, sets=3, rest_seconds=60),
    ],
)


def get_templates_by_filters(
    focus: str | None = None,
    location: str | None = None,
    experience: str | None = None,
) -> List[WorkoutTemplate]:
    """Filter templates by focus, location, and experience level."""
    result = list(WORKOUT_TEMPLATES.values())
    if focus:
        result = [t for t in result if t.focus == focus]
    if location:
        result = [t for t in result if location in t.template_id]
    if experience:
        result = [t for t in result if experience in t.template_id]
    return result


def get_template(template_id: str) -> WorkoutTemplate | None:
    """Get template by ID."""
    return WORKOUT_TEMPLATES.get(template_id)

