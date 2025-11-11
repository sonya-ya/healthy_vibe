from __future__ import annotations

MEDICAL_DISCLAIMER = (
    "Важно: этот бот не является медицинским специалистом. При серьёзных или"
    " тревожных симптомах обязательно обратитесь к врачу."
)

WELCOME_MESSAGE = (
    "Привет! Я помогу составить персональные тренировки, отслеживать прогресс"
    " и напоминать о важных активностях."
)

HELP_MESSAGE = (
    "Доступные команды:\n"
    "/start — узнать, что умеет бот\n"
    "/profile — заполнить или обновить профиль\n"
    "/workout — получить тренировку на сегодня\n"
    "/createworkout — создать тренировку вручную\n"
    "/progress — посмотреть прогресс\n"
    "/reminders — настроить напоминания\n"
    "/createplan — создать план тренировок\n"
    "/help — список команд"
)

# Константы для профиля
GENDER_OPTIONS = {
    "Мужской": "male",
    "Женский": "female",
    "Другое": "other",
}

GOAL_OPTIONS = {
    "Похудение": "lose",
    "Набор массы": "gain",
    "Поддержание": "maintain",
}

EXPERIENCE_OPTIONS = {
    "Начинающий": "beginner",
    "Средний": "intermediate",
    "Продвинутый": "advanced",
}

LOCATION_OPTIONS = {
    "Дома": "home",
    "В зале": "gym",
}

WORKOUT_TIME_OPTIONS = {
    "Короткая (15-20 мин)": "short",
    "Средняя (30-40 мин)": "medium",
    "Длинная (50+ мин)": "long",
}

# Обратные словари для отображения
GENDER_DISPLAY = {v: k for k, v in GENDER_OPTIONS.items()}
GOAL_DISPLAY = {v: k for k, v in GOAL_OPTIONS.items()}
EXPERIENCE_DISPLAY = {v: k for k, v in EXPERIENCE_OPTIONS.items()}
LOCATION_DISPLAY = {v: k for k, v in LOCATION_OPTIONS.items()}
WORKOUT_TIME_DISPLAY = {v: k for k, v in WORKOUT_TIME_OPTIONS.items()}

# Порядок полей профиля
PROFILE_FIELDS_ORDER = [
    "age",
    "gender",
    "weight",
    "goal",
    "experience",
    "preferred_location",
    "workout_time",
]

# Названия дней недели
DAY_NAMES = {
    "mon": "Понедельник",
    "tue": "Вторник",
    "wed": "Среда",
    "thu": "Четверг",
    "fri": "Пятница",
    "sat": "Суббота",
    "sun": "Воскресенье",
}
