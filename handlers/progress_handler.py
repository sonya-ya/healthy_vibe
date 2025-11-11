from __future__ import annotations

import logging
from typing import Optional

from telebot import TeleBot
from telebot.types import KeyboardButton, Message, ReplyKeyboardMarkup

from repositories.storage import StorageRepository
from services.progress_service import EnhancedProgressService
from utils.constants import DAY_NAMES

logger = logging.getLogger(__name__)


class ProgressHandler:
    """Обработчик для отображения прогресса."""

    def __init__(self, bot: TeleBot, storage: StorageRepository, progress_service: EnhancedProgressService, menu_handler):
        self._bot = bot
        self._storage = storage
        self._progress_service = progress_service
        self._menu_handler = menu_handler

    def show_progress_menu(self, message: Message) -> None:
        """Показать меню 'Прогресс'."""
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(KeyboardButton("📈 Общая статистика"))
        markup.add(KeyboardButton("💪 По тренировкам"))
        markup.add(KeyboardButton("🏋️ По упражнениям"))
        markup.add(KeyboardButton("📉 Графики"))
        markup.add(KeyboardButton("🏠 Главное меню"))
        self._bot.send_message(message.chat.id, "📊 Мой прогресс\n\nВыберите что показать:", reply_markup=markup)

    def register_handlers(self) -> None:
        """Зарегистрировать обработчики для прогресса."""
        
        @self._bot.message_handler(func=lambda m: m.text == "📈 Общая статистика")
        def general_stats_handler(message: Message) -> None:
            self._show_general_stats(message)

        @self._bot.message_handler(func=lambda m: m.text == "💪 По тренировкам")
        def workouts_progress_handler(message: Message) -> None:
            self._show_workouts_progress(message)

        @self._bot.message_handler(func=lambda m: m.text == "🏋️ По упражнениям")
        def exercises_progress_handler(message: Message) -> None:
            self._show_exercises_progress(message)

        @self._bot.message_handler(func=lambda m: m.text == "📉 Графики")
        def charts_handler(message: Message) -> None:
            self._show_charts_menu(message)

    def _show_general_stats(self, message: Message) -> None:
        """Показать общую статистику."""
        user_id = str(message.from_user.id)
        summary = self._progress_service.summarize(user_id)
        
        # Получаем дополнительные данные
        try:
            executions = self._storage.get_workout_executions(user_id)
            total_executions = len(executions)
        except Exception:
            total_executions = summary.get('sessions', 0)
        
        # Последняя тренировка
        last_execution = None
        try:
            executions = self._storage.get_workout_executions(user_id)
            if executions:
                last_execution = max(executions, key=lambda e: e.execution_date)
        except Exception:
            pass
        
        text_lines = ["📈 Общая статистика:\n"]
        text_lines.append(f"✅ Всего тренировок выполнено: {summary.get('sessions', total_executions) or 0}")
        
        if summary.get('average_weight'):
            text_lines.append(f"⚖️ Средний вес тела: {summary['average_weight']:.1f} кг")
        else:
            text_lines.append("⚖️ Вес тела: не указан")
        
        if last_execution:
            last_date = last_execution.execution_date.strftime("%d.%m.%Y %H:%M")
            text_lines.append(f"📅 Последняя тренировка: {last_date}")
        
        # Активные планы
        try:
            active_plans = self._storage.get_active_plans(user_id)
            text_lines.append(f"📆 Активных планов: {len(active_plans)}")
        except Exception:
            pass
        
        text = "\n".join(text_lines)
        self._bot.send_message(message.chat.id, text, reply_markup=self._menu_handler.get_menu(user_id))

    def _show_workouts_progress(self, message: Message) -> None:
        """Показать прогресс по тренировкам."""
        user_id = str(message.from_user.id)
        try:
            workouts = self._storage.get_all_workout_entries(user_id)
        except Exception as e:
            logger.error("Error getting workouts: %s", e)
            workouts = []
        
        if not workouts:
            self._bot.send_message(
                message.chat.id,
                "У вас пока нет тренировок для отслеживания прогресса.\n\nИспользуйте '➕ Создать' для создания тренировки.",
                reply_markup=self._menu_handler.get_menu(user_id)
            )
            return
        
        text_lines = ["💪 Прогресс по тренировкам:\n"]
        
        for workout in workouts[:10]:  # Показываем первые 10
            name = workout.workout_name or "Тренировка"
            try:
                executions = self._storage.get_workout_executions(user_id, workout.entry_id)
                execution_count = len(executions)
            except Exception:
                execution_count = workout.completion_count or 0
            
            text_lines.append(f"💪 {name}")
            text_lines.append(f"   Выполнено: {execution_count} раз")
            
            if workout.last_completed:
                last_date = workout.last_completed.strftime("%d.%m.%Y")
                text_lines.append(f"   Последний раз: {last_date}")
            
            text_lines.append("")
        
        if len(workouts) > 10:
            text_lines.append(f"... и еще {len(workouts) - 10} тренировок")
        
        text = "\n".join(text_lines)
        self._bot.send_message(message.chat.id, text, reply_markup=self._menu_handler.get_menu(user_id))

    def _show_exercises_progress(self, message: Message) -> None:
        """Показать прогресс по упражнениям."""
        user_id = str(message.from_user.id)
        try:
            executions = self._storage.get_workout_executions(user_id)
        except Exception as e:
            logger.error("Error getting executions: %s", e)
            executions = []
        
        if not executions:
            self._bot.send_message(
                message.chat.id,
                "У вас пока нет данных о выполнении упражнений.\n\nВыполните тренировку и отметьте прогресс!",
                reply_markup=self._menu_handler.get_menu(user_id)
            )
            return
        
        # Собираем все уникальные упражнения
        exercises_dict = {}
        for execution in executions:
            for ex_progress in execution.exercises_progress:
                ex_name = ex_progress.exercise_name
                if ex_name not in exercises_dict:
                    exercises_dict[ex_name] = []
                exercises_dict[ex_name].append(ex_progress)
        
        if not exercises_dict:
            self._bot.send_message(
                message.chat.id,
                "Нет данных о прогрессе по упражнениям.\n\nВыполните тренировку и введите данные о прогрессе по каждому упражнению.",
                reply_markup=self._menu_handler.get_menu(user_id)
            )
            return
        
        text_lines = ["🏋️ Прогресс по упражнениям:\n"]
        
        for ex_name, progress_list in list(exercises_dict.items())[:10]:
            latest = progress_list[-1]
            first = progress_list[0]
            
            text_lines.append(f"🏋️ {ex_name}")
            
            if latest.actual_weight:
                text_lines.append(f"   Текущий вес: {latest.actual_weight} кг")
                if first.actual_weight and first.actual_weight != latest.actual_weight:
                    diff = latest.actual_weight - first.actual_weight
                    text_lines.append(f"   Изменение: {diff:+.1f} кг")
            else:
                text_lines.append("   Вес: не указан")
            
            if latest.actual_reps:
                text_lines.append(f"   Последние повторения: {', '.join(map(str, latest.actual_reps))}")
            
            text_lines.append(f"   Выполнено раз: {len(progress_list)}")
            text_lines.append("")
        
        if len(exercises_dict) > 10:
            text_lines.append(f"... и еще {len(exercises_dict) - 10} упражнений")
        
        text = "\n".join(text_lines)
        self._bot.send_message(message.chat.id, text, reply_markup=self._menu_handler.get_menu(user_id))

    def _show_charts_menu(self, message: Message) -> None:
        """Показать меню графиков."""
        user_id = str(message.from_user.id)
        self._bot.send_message(
            message.chat.id,
            "📉 Графики прогресса\n\nФункция графиков будет доступна в ближайшее время.",
            reply_markup=self._menu_handler.get_menu(user_id)
        )

