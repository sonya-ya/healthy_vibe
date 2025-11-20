from __future__ import annotations

import logging
from typing import Optional

from telebot import TeleBot
from telebot.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, Message, ReplyKeyboardMarkup

from repositories.storage import StorageRepository
from services.workout_management import WorkoutManagementService
from utils.constants import DAY_NAMES

logger = logging.getLogger(__name__)


class WorkoutManagementHandler:
    """Обработчик для управления тренировками."""

    def __init__(self, bot: TeleBot, storage: StorageRepository, workout_service, menu_handler):
        self._bot = bot
        self._storage = storage
        self._workout_service = workout_service
        self._management_service = WorkoutManagementService(storage)
        self._menu_handler = menu_handler

    def show_my_workouts_menu(self, message: Message) -> None:
        """Показать меню 'Мои тренировки'."""
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(KeyboardButton("📅 Все тренировки"))
        markup.add(KeyboardButton("📆 По дням недели"))
        markup.add(KeyboardButton("📊 Активные планы"))
        markup.add(KeyboardButton("🏠 Главное меню"))
        self._bot.send_message(message.chat.id, "📋 Мои тренировки\n\nВыберите действие:", reply_markup=markup)

    def register_handlers(self) -> None:
        """Зарегистрировать обработчики для управления тренировками."""
        
        @self._bot.message_handler(func=lambda m: m.text == "📅 Все тренировки")
        def all_workouts_handler(message: Message) -> None:
            self._show_all_workouts(message)

        @self._bot.message_handler(func=lambda m: m.text == "📆 По дням недели")
        def workouts_by_day_handler(message: Message) -> None:
            self._show_workouts_by_day_menu(message)

        @self._bot.message_handler(func=lambda m: m.text == "📊 Активные планы")
        def active_plans_handler(message: Message) -> None:
            self._show_active_plans(message)
        
        # Обработчик для дней недели - проверяем, начинается ли текст с "📅" и является ли это днем недели
        @self._bot.message_handler(func=lambda m: m.text and m.text.startswith("📅 ") and any(m.text == f"📅 {name}" for name in DAY_NAMES.values()))
        def day_handler(message: Message) -> None:
            # Извлекаем день из текста
            text = message.text.replace("📅 ", "")
            day_code = None
            for code, name in DAY_NAMES.items():
                if name == text:
                    day_code = code
                    break
            if day_code:
                self._show_workouts_for_day(message, day_code)

    def _show_all_workouts(self, message: Message) -> None:
        """Показать все тренировки пользователя."""
        user_id = str(message.from_user.id)
        workouts_by_day = self._management_service.get_all_workouts(user_id)
        
        if not workouts_by_day:
            self._bot.send_message(
                message.chat.id,
                "У вас пока нет сохраненных тренировок.\n\nИспользуйте '➕ Создать' для создания тренировки.",
                reply_markup=self._menu_handler.get_menu(user_id)
            )
            return
        
        text_lines = ["📋 Все ваши тренировки:\n"]
        
        for day, workouts in sorted(workouts_by_day.items(), key=lambda x: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"].index(x[0])):
            day_name = DAY_NAMES.get(day, day)
            text_lines.append(f"📅 {day_name}:")
            for workout in workouts:
                name = workout.workout_name or "Тренировка"
                exercise_count = len(workout.exercises)
                completion_count = workout.completion_count
                text_lines.append(f"  💪 {name} ({exercise_count} упражнений, выполнено {completion_count} раз)")
            
            text_lines.append("")
        
        text = "\n".join(text_lines)
        
        # Разбиваем на части, если текст слишком длинный
        if len(text) > 4000:
            parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for part in parts:
                self._bot.send_message(message.chat.id, part)
        else:
            self._bot.send_message(message.chat.id, text, reply_markup=self._menu_handler.get_menu(user_id))

    def _show_workouts_by_day_menu(self, message: Message) -> None:
        """Показать меню выбора дня недели."""
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for day_code, day_name in DAY_NAMES.items():
            markup.add(KeyboardButton(f"📅 {day_name}"))
        markup.add(KeyboardButton("🏠 Главное меню"))
        self._bot.send_message(message.chat.id, "Выберите день недели:", reply_markup=markup)

    def _show_workouts_for_day(self, message: Message, day: str) -> None:
        """Показать тренировки для конкретного дня."""
        user_id = str(message.from_user.id)
        workouts = self._management_service._storage.get_workout_entries_by_day(user_id, day)
        
        day_name = DAY_NAMES.get(day, day)
        
        if not workouts:
            self._bot.send_message(
                message.chat.id,
                f"У вас нет тренировок на {day_name.lower()}.\n\nИспользуйте '➕ Создать' для создания тренировки.",
                reply_markup=self._menu_handler.get_menu(user_id)
            )
            return
        
        text_lines = [f"📅 Тренировки на {day_name}:\n"]
        
        for workout in workouts:
            name = workout.workout_name or "Тренировка"
            exercise_count = len(workout.exercises)
            completion_count = workout.completion_count
            
            text_lines.append(f"💪 {name}")
            text_lines.append(f"   Упражнений: {exercise_count}")
            text_lines.append(f"   Выполнено: {completion_count} раз")
            
            # Показываем первые несколько упражнений
            for ex in workout.exercises[:3]:
                weight_str = f", {ex.weight} кг" if ex.weight else ""
                text_lines.append(f"   • {ex.name}: {ex.sets}×{ex.reps}{weight_str}")
            
            if len(workout.exercises) > 3:
                text_lines.append(f"   ... и еще {len(workout.exercises) - 3} упражнений")
            
            text_lines.append("")
        
        text = "\n".join(text_lines)
        self._bot.send_message(message.chat.id, text, reply_markup=self._menu_handler.get_menu(user_id))

    def _show_active_plans(self, message: Message) -> None:
        """Показать активные планы пользователя."""
        user_id = str(message.from_user.id)
        active_plans = self._storage.get_active_plans(user_id)
        
        if not active_plans:
            self._bot.send_message(
                message.chat.id,
                "У вас нет активных планов тренировок.\n\nИспользуйте '📅 План' → '➕ Создать план' для создания плана.",
                reply_markup=self._menu_handler.get_menu(user_id)
            )
            return
        
        text_lines = ["📊 Активные планы:\n"]
        
        for plan in active_plans:
            plan_name = plan.name or "План тренировок"
            start_date = plan.start_date.strftime("%d.%m.%Y")
            entries_count = len(plan.entries)
            
            text_lines.append(f"📆 {plan_name}")
            text_lines.append(f"   Начат: {start_date}")
            text_lines.append(f"   Тренировок: {entries_count}")
            
            # Показываем дни тренировок
            days = [DAY_NAMES.get(e.day_of_week, e.day_of_week) for e in plan.entries]
            text_lines.append(f"   Дни: {', '.join(days)}")
            text_lines.append("")
        
        text = "\n".join(text_lines)
        self._bot.send_message(message.chat.id, text, reply_markup=self._menu_handler.get_menu(user_id))

