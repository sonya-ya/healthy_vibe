from __future__ import annotations

import logging
from datetime import date
from typing import Dict, List

from telebot import TeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from repositories.models import Exercise, WorkoutEntry
from repositories.storage import StorageRepository
from services.exercise_db import (
    CATEGORY_NAMES,
    get_all_categories,
    get_category_name,
    get_exercises_by_category,
)
from services.validation import validate_exercise_weight, validate_reps, validate_sets
from services.workout_service import WorkoutService
from utils.constants import DAY_NAMES
from utils.state_manager import state_manager

logger = logging.getLogger(__name__)


class WorkoutCreationManager:
    """Менеджер пошагового создания тренировки."""

    def __init__(self, bot: TeleBot, storage: StorageRepository, workout_service: WorkoutService) -> None:
        self._bot = bot
        self._storage = storage
        self._workout_service = workout_service

    def start_workout_creation(self, message: Message) -> None:
        """Начать процесс создания тренировки."""
        user_id = str(message.from_user.id)
        state_manager.set_state(
            user_id,
            "workout_creation",
            {
                "user_id": user_id,
                "day_of_week": None,
                "exercises": [],
                "current_step": "day",
            },
        )
        self._ask_day(message)

    def _ask_day(self, message: Message) -> None:
        """Запросить выбор дня недели."""
        markup = InlineKeyboardMarkup(row_width=2)
        days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        buttons = []
        for day in days:
            buttons.append(InlineKeyboardButton(DAY_NAMES[day], callback_data=f"workout_day_{day}"))
        # Разделить на две строки
        for i in range(0, len(buttons), 2):
            if i + 1 < len(buttons):
                markup.row(buttons[i], buttons[i + 1])
            else:
                markup.add(buttons[i])
        markup.add(InlineKeyboardButton("❌ Отменить", callback_data="workout_cancel"))
        self._bot.send_message(message.chat.id, "Выберите день недели для тренировки:", reply_markup=markup)

    def handle_day_selection(self, day: str, user_id: str, chat_id: int) -> None:
        """Обработать выбор дня недели."""
        state = state_manager.get_state(user_id, "workout_creation")
        if not state:
            self._bot.send_message(chat_id, "Сессия истекла. Начните заново командой /createworkout")
            return

        state["day_of_week"] = day
        state["current_step"] = "exercise_choice"
        state_manager.update_state(user_id, "workout_creation", state)
        self._ask_exercise_choice(user_id, chat_id)

    def _ask_exercise_choice(self, user_id: str, chat_id: int) -> None:
        """Запросить способ выбора упражнения."""
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("📋 Выбрать из списка", callback_data="workout_exercise_list"))
        markup.add(InlineKeyboardButton("✏️ Ввести вручную", callback_data="workout_exercise_manual"))
        markup.add(InlineKeyboardButton("❌ Отменить", callback_data="workout_cancel"))
        self._bot.send_message(chat_id, "Как вы хотите добавить упражнение?", reply_markup=markup)

    def show_exercise_categories(self, user_id: str, chat_id: int) -> None:
        """Показать категории упражнений."""
        categories = get_all_categories()
        markup = InlineKeyboardMarkup(row_width=2)
        buttons = []
        for category in categories:
            buttons.append(
                InlineKeyboardButton(
                    get_category_name(category), callback_data=f"workout_category_{category}"
                )
            )
        # Разделить на две строки
        for i in range(0, len(buttons), 2):
            if i + 1 < len(buttons):
                markup.row(buttons[i], buttons[i + 1])
            else:
                markup.add(buttons[i])
        markup.add(InlineKeyboardButton("◀️ Назад", callback_data="workout_exercise_back"))
        markup.add(InlineKeyboardButton("❌ Отменить", callback_data="workout_cancel"))
        self._bot.send_message(chat_id, "Выберите категорию упражнений:", reply_markup=markup)

    def show_exercises_by_category(self, category: str, user_id: str, chat_id: int) -> None:
        """Показать упражнения выбранной категории."""
        exercises = get_exercises_by_category(category)
        if not exercises:
            self._bot.send_message(chat_id, "В этой категории нет упражнений.")
            return

        # Сохраняем список упражнений в состоянии для доступа по индексу
        # Это позволяет использовать короткие callback_data (индекс вместо полного названия)
        state = state_manager.get_state(user_id, "workout_creation")
        if not state:
            self._bot.send_message(chat_id, "Сессия истекла. Начните заново командой /createworkout")
            return
        
        state["current_category_exercises"] = exercises
        state_manager.update_state(user_id, "workout_creation", state)

        markup = InlineKeyboardMarkup(row_width=1)
        # Используем индекс вместо полного названия для callback_data
        # Формат: "workout_idx_{idx}" - короткий и не конфликтует с "workout_exercise_"
        for idx, exercise in enumerate(exercises):
            # callback_data ограничен 64 байтами в Telegram
            # "workout_idx_" (12) + индекс (до 3 цифр) = максимум 15 байт - безопасно
            callback_data = f"workout_idx_{idx}"
            markup.add(InlineKeyboardButton(exercise, callback_data=callback_data))
        markup.add(InlineKeyboardButton("◀️ Назад к категориям", callback_data="workout_exercise_list"))
        markup.add(InlineKeyboardButton("❌ Отменить", callback_data="workout_cancel"))

        category_name = get_category_name(category)
        self._bot.send_message(
            chat_id, f"Выберите упражнение из категории '{category_name}':", reply_markup=markup
        )

    def handle_exercise_selection(self, exercise_name: str, user_id: str, chat_id: int) -> None:
        """Обработать выбор упражнения."""
        state = state_manager.get_state(user_id, "workout_creation")
        if not state:
            self._bot.send_message(chat_id, "Сессия истекла. Начните заново командой /createworkout")
            return

        state["current_exercise"] = {"name": exercise_name, "reps": None, "sets": None, "weight": None}
        state["current_step"] = "reps"
        state_manager.update_state(user_id, "workout_creation", state)
        self._ask_reps(user_id, chat_id)

    def handle_exercise_manual_input(self, message: Message) -> None:
        """Обработать ручной ввод названия упражнения."""
        user_id = str(message.from_user.id)
        exercise_name = message.text.strip()
        if not exercise_name:
            error_msg = self._bot.send_message(message.chat.id, "Название упражнения не может быть пустым. Введите название:")
            self._bot.register_next_step_handler(error_msg, self.handle_exercise_manual_input)
            return

        state = state_manager.get_state(user_id, "workout_creation")
        if not state:
            self._bot.send_message(message.chat.id, "Сессия истекла. Начните заново командой /createworkout")
            return

        state["current_exercise"] = {"name": exercise_name, "reps": None, "sets": None, "weight": None}
        state["current_step"] = "reps"
        state_manager.update_state(user_id, "workout_creation", state)
        self._ask_reps(user_id, message.chat.id)

    def _ask_reps(self, user_id: str, chat_id: int) -> None:
        """Запросить количество повторений."""
        state = state_manager.get_state(user_id, "workout_creation")
        exercise_name = state.get("current_exercise", {}).get("name", "упражнение")
        msg = self._bot.send_message(
            chat_id, f"Упражнение: {exercise_name}\n\nВведите количество повторений (от 1 до 100):"
        )
        self._bot.register_next_step_handler(msg, self._handle_reps_input)

    def _handle_reps_input(self, message: Message) -> None:
        """Обработать ввод количества повторений."""
        user_id = str(message.from_user.id)
        is_valid, reps, error_msg = validate_reps(message.text)

        if not is_valid:
            error_msg_obj = self._bot.send_message(message.chat.id, f"❌ {error_msg}\n\nПопробуйте ещё раз:")
            self._bot.register_next_step_handler(error_msg_obj, self._handle_reps_input)
            return

        state = state_manager.get_state(user_id, "workout_creation")
        if state and "current_exercise" in state:
            state["current_exercise"]["reps"] = reps
            state["current_step"] = "sets"
            state_manager.update_state(user_id, "workout_creation", state)
            self._ask_sets(user_id, message.chat.id)

    def _ask_sets(self, user_id: str, chat_id: int) -> None:
        """Запросить количество подходов."""
        markup = InlineKeyboardMarkup(row_width=5)
        for i in range(1, 6):
            markup.add(InlineKeyboardButton(str(i), callback_data=f"workout_sets_{i}"))
        markup.add(InlineKeyboardButton("Другое", callback_data="workout_sets_manual"))
        markup.add(InlineKeyboardButton("❌ Отменить", callback_data="workout_cancel"))

        state = state_manager.get_state(user_id, "workout_creation")
        exercise_name = state.get("current_exercise", {}).get("name", "упражнение")
        reps = state.get("current_exercise", {}).get("reps", "?")
        self._bot.send_message(
            chat_id,
            f"Упражнение: {exercise_name}\nПовторений: {reps}\n\nВыберите количество подходов:",
            reply_markup=markup,
        )

    def handle_sets_selection(self, sets: int, user_id: str, chat_id: int) -> None:
        """Обработать выбор количества подходов."""
        state = state_manager.get_state(user_id, "workout_creation")
        if not state:
            self._bot.send_message(chat_id, "Сессия истекла. Начните заново командой /createworkout")
            return

        if "current_exercise" in state:
            state["current_exercise"]["sets"] = sets
            state["current_step"] = "weight"
            state_manager.update_state(user_id, "workout_creation", state)
            self._ask_weight(user_id, chat_id)

    def _ask_sets_manual(self, user_id: str, chat_id: int) -> None:
        """Запросить количество подходов вручную."""
        msg = self._bot.send_message(chat_id, "Введите количество подходов (от 1 до 10):")
        self._bot.register_next_step_handler(msg, self._handle_sets_input)

    def _handle_sets_input(self, message: Message) -> None:
        """Обработать ввод количества подходов."""
        user_id = str(message.from_user.id)
        is_valid, sets, error_msg = validate_sets(message.text)

        if not is_valid:
            error_msg_obj = self._bot.send_message(message.chat.id, f"❌ {error_msg}\n\nПопробуйте ещё раз:")
            self._bot.register_next_step_handler(error_msg_obj, self._handle_sets_input)
            return

        state = state_manager.get_state(user_id, "workout_creation")
        if state and "current_exercise" in state:
            state["current_exercise"]["sets"] = sets
            state["current_step"] = "weight"
            state_manager.update_state(user_id, "workout_creation", state)
            self._ask_weight(user_id, message.chat.id)

    def _ask_weight(self, user_id: str, chat_id: int) -> None:
        """Запросить вес."""
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("Пропустить (без веса)", callback_data="workout_weight_skip"))
        markup.add(InlineKeyboardButton("Ввести вес", callback_data="workout_weight_manual"))
        markup.add(InlineKeyboardButton("❌ Отменить", callback_data="workout_cancel"))

        state = state_manager.get_state(user_id, "workout_creation")
        exercise_name = state.get("current_exercise", {}).get("name", "упражнение")
        reps = state.get("current_exercise", {}).get("reps", "?")
        sets = state.get("current_exercise", {}).get("sets", "?")
        self._bot.send_message(
            chat_id,
            f"Упражнение: {exercise_name}\nПовторений: {reps}\nПодходов: {sets}\n\nВес (в кг, или пропустить):",
            reply_markup=markup,
        )

    def handle_weight_skip(self, user_id: str, chat_id: int) -> None:
        """Обработать пропуск веса."""
        state = state_manager.get_state(user_id, "workout_creation")
        if not state:
            self._bot.send_message(chat_id, "Сессия истекла. Начните заново командой /createworkout")
            return

        if "current_exercise" in state:
            state["current_exercise"]["weight"] = 0.0
            self._add_exercise_to_list(user_id, chat_id)

    def _ask_weight_manual(self, user_id: str, chat_id: int) -> None:
        """Запросить вес вручную."""
        msg = self._bot.send_message(chat_id, "Введите вес в кг (от 0 до 500, или 0 если без веса):")
        self._bot.register_next_step_handler(msg, self._handle_weight_input)

    def _handle_weight_input(self, message: Message) -> None:
        """Обработать ввод веса."""
        user_id = str(message.from_user.id)
        is_valid, weight, error_msg = validate_exercise_weight(message.text)

        if not is_valid:
            error_msg_obj = self._bot.send_message(message.chat.id, f"❌ {error_msg}\n\nПопробуйте ещё раз:")
            self._bot.register_next_step_handler(error_msg_obj, self._handle_weight_input)
            return

        state = state_manager.get_state(user_id, "workout_creation")
        if state and "current_exercise" in state:
            state["current_exercise"]["weight"] = weight if weight > 0 else None
            self._add_exercise_to_list(user_id, message.chat.id)

    def _add_exercise_to_list(self, user_id: str, chat_id: int) -> None:
        """Добавить упражнение в список и показать меню."""
        state = state_manager.get_state(user_id, "workout_creation")
        if not state or "current_exercise" not in state:
            return

        exercise_data = state["current_exercise"]
        state["exercises"].append(exercise_data.copy())
        state["current_exercise"] = None
        state["current_step"] = "exercise_choice"
        state_manager.update_state(user_id, "workout_creation", state)

        # Показать список упражнений и предложить добавить еще или сохранить
        self._show_exercises_list(user_id, chat_id)

    def _show_exercises_list(self, user_id: str, chat_id: int) -> None:
        """Показать список добавленных упражнений."""
        state = state_manager.get_state(user_id, "workout_creation")
        if not state:
            return

        exercises = state.get("exercises", [])
        if not exercises:
            return

        text_lines = ["Добавленные упражнения:\n"]
        for i, ex in enumerate(exercises, 1):
            weight_text = f", {ex['weight']} кг" if ex.get("weight") else ""
            text_lines.append(f"{i}. {ex['name']}: {ex['sets']}x{ex['reps']}{weight_text}")

        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("➕ Добавить упражнение", callback_data="workout_add_exercise"))
        markup.add(InlineKeyboardButton("✅ Сохранить тренировку", callback_data="workout_save"))
        markup.add(InlineKeyboardButton("❌ Отменить", callback_data="workout_cancel"))

        self._bot.send_message(chat_id, "\n".join(text_lines) + "\n\nЧто дальше?", reply_markup=markup)

    def save_workout(self, user_id: str, chat_id: int) -> None:
        """Сохранить тренировку."""
        state = state_manager.get_state(user_id, "workout_creation")
        if not state:
            self._bot.send_message(chat_id, "Сессия истекла. Начните заново командой /createworkout")
            return

        day_of_week = state.get("day_of_week")
        exercises_data = state.get("exercises", [])

        if not day_of_week:
            self._bot.send_message(chat_id, "Ошибка: день недели не выбран")
            return

        if not exercises_data:
            self._bot.send_message(chat_id, "Ошибка: не добавлено ни одного упражнения")
            return

        # Создать объекты Exercise
        exercises = []
        for ex_data in exercises_data:
            exercises.append(
                Exercise(
                    name=ex_data["name"],
                    reps=ex_data["reps"],
                    sets=ex_data["sets"],
                    weight=ex_data.get("weight"),
                    rest_seconds=60,
                )
            )

        # Создать WorkoutEntry
        workout_entry = WorkoutEntry(day_of_week=day_of_week, exercises=exercises)

        # Сохранить как standalone тренировку, а не как план
        self._workout_service.save_standalone_workout(user_id, workout_entry)

        # Очистить состояние
        state_manager.clear_state(user_id, "workout_creation")

        # Показать результат
        day_name = DAY_NAMES.get(day_of_week, day_of_week)
        text_lines = [f"✅ Тренировка на {day_name} сохранена!\n\nУпражнения:"]
        for ex in exercises:
            weight_text = f", {ex.weight} кг" if ex.weight else ""
            text_lines.append(f"• {ex.name}: {ex.sets}x{ex.reps}{weight_text}")
        text_lines.append("\nТренировка доступна в '📋 Мои тренировки'")

        self._bot.send_message(chat_id, "\n".join(text_lines))
        logger.info("Workout created for user %s, day %s", user_id, day_of_week)

    def cancel_workout_creation(self, user_id: str, chat_id: int) -> None:
        """Отменить создание тренировки."""
        state_manager.clear_state(user_id, "workout_creation")
        self._bot.send_message(chat_id, "❌ Создание тренировки отменено.")


def register_workout_creation_handlers(
    bot: TeleBot, storage: StorageRepository, workout_service: WorkoutService
) -> WorkoutCreationManager:
    """Зарегистрировать обработчики для создания тренировок."""
    manager = WorkoutCreationManager(bot, storage, workout_service)

    @bot.message_handler(commands=["createworkout"])
    def createworkout_command(message: Message) -> None:
        manager.start_workout_creation(message)

    return manager

