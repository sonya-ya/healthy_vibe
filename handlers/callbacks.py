from __future__ import annotations

import logging
from datetime import datetime

from telebot import TeleBot
from telebot.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from analytics.charts import generate_progress_chart
from repositories.models import ProgressEntry
from repositories.storage import StorageRepository
from services.progress_service import ProgressService
from services.workout_service import WorkoutService
from utils.constants import DAY_NAMES, MEDICAL_DISCLAIMER

logger = logging.getLogger(__name__)


def _send_workout(bot: TeleBot, chat_id: int, workout_entry) -> None:
    text_lines = ["Тренировка на сегодня:"]
    for ex in workout_entry.exercises:
        weight = f", вес {ex.weight} кг" if ex.weight else ""
        text_lines.append(
            f"• {ex.name}: {ex.sets}х{ex.reps}{weight}"
        )
    text_lines.append("\nНе забудьте отметить выполнение!")

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Выполнено", callback_data="progress_done"))

    bot.send_message(chat_id, "\n".join(text_lines), reply_markup=markup)


def register_callback_handlers(
    bot: TeleBot,
    progress_service: ProgressService,
    workout_service: WorkoutService,
    storage: StorageRepository,
    profile_conversation=None,
    workout_creation_manager=None,
) -> None:
    @bot.callback_query_handler(func=lambda call: call.data == "progress_done")
    def progress_done_callback(query: CallbackQuery) -> None:
        user_id = str(query.from_user.id)
        # Простое логирование через ProgressEntry (без конкретной тренировки)
        # В будущем это можно заменить на WorkoutExecution с детальным прогрессом
        entry = ProgressEntry(
            user_id=user_id,
            date=datetime.utcnow(),
        )
        progress_service.add_entry(entry)
        bot.answer_callback_query(query.id, "Отлично, тренировка отмечена!")
        bot.send_message(query.message.chat.id, f"Продолжайте в том же духе!\n\n{MEDICAL_DISCLAIMER}")
        logger.info("Workout logged via callback for user %s", user_id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("template_"))
    def template_callback(query: CallbackQuery) -> None:
        user_id = str(query.from_user.id)
        profile = storage.get_profile(user_id)
        if not profile:
            bot.answer_callback_query(query.id, "Сначала заполните профиль!")
            return

        template_id = query.data.replace("template_", "")
        if template_id == "random":
            focus = "legs"
            workout_entry = workout_service.generate_daily_workout(profile, focus)
        else:
            workout_entry = workout_service.generate_daily_workout(profile, "legs", template_id=template_id)

        # Сохраняем как standalone тренировку, а не как план
        workout_service.save_standalone_workout(user_id, workout_entry)
        bot.answer_callback_query(query.id, "Тренировка создана!")
        _send_workout(bot, query.message.chat.id, workout_entry)
        logger.info("Template workout created for user %s: %s", user_id, template_id)

    @bot.callback_query_handler(func=lambda call: call.data == "analyse")
    def analyse_callback(query: CallbackQuery) -> None:
        user_id = str(query.from_user.id)
        entries = progress_service.fetch_entries(user_id)
        if not entries:
            bot.answer_callback_query(query.id, "Нет данных для анализа")
            bot.send_message(query.message.chat.id, "Пока нет записей о прогрессе. Отмечайте тренировки!")
            return

        summary = progress_service.summarize(user_id)
        text = (
            f"📊 Анализ прогресса:\n\n"
            f"Всего сессий: {summary['sessions']}\n"
            f"Средний вес: {summary['average_weight'] or '—'} кг\n\n"
            f"Продолжайте в том же духе! 💪"
        )
        bot.answer_callback_query(query.id, "Анализ готов!")
        bot.send_message(query.message.chat.id, text)
        try:
            chart_path = generate_progress_chart(user_id, entries)
            with chart_path.open("rb") as chart_file:
                bot.send_photo(query.message.chat.id, chart_file)
        except ValueError as e:
            bot.send_message(query.message.chat.id, f"Недостаточно данных для графика: {e}")
        except Exception as e:
            logger.exception("Failed to generate chart: %s", e)
            bot.send_message(query.message.chat.id, "Ошибка при генерации графика.")
        logger.info("Progress analysis requested for user %s", user_id)

    # Profile callbacks
    @bot.callback_query_handler(func=lambda call: call.data.startswith("profile_field_"))
    def profile_field_callback(query: CallbackQuery) -> None:
        if not profile_conversation:
            bot.answer_callback_query(query.id, "Ошибка обработки")
            return

        user_id = str(query.from_user.id)
        data = query.data.replace("profile_field_", "")
        
        # Маппинг полей: короткие имена в callback_data -> полные имена полей
        # Важно: проверяем длинные имена первыми (preferred_location перед location)
        field_mapping = [
            ("preferred_location", "preferred_location"),
            ("workout_time", "workout_time"),
            ("gender", "gender"),
            ("goal", "goal"),
            ("experience", "experience"),
            ("location", "preferred_location"),  # Обратная совместимость
            ("time", "workout_time"),  # Обратная совместимость
        ]
        
        # Попробуем найти поле и значение
        # Формат: profile_field_{field}_{value}
        # Поля могут содержать подчеркивания (preferred_location, workout_time)
        field = None
        value = None
        
        # Проверяем известные поля (сначала длинные имена)
        for key, mapped_field in field_mapping:
            if data.startswith(f"{key}_"):
                field = mapped_field
                value = data[len(key) + 1:]  # +1 для подчеркивания
                break
        
        if not field or not value:
            bot.answer_callback_query(query.id, "Ошибка: неверный формат")
            logger.error("Invalid profile field callback data: %s", query.data)
            return

        bot.answer_callback_query(query.id, "Выбрано")
        profile_conversation.handle_button_selection(field, value, user_id, query.message.chat.id)

    @bot.callback_query_handler(func=lambda call: call.data == "profile_save")
    def profile_save_callback(query: CallbackQuery) -> None:
        if not profile_conversation:
            bot.answer_callback_query(query.id, "Ошибка обработки")
            return

        user_id = str(query.from_user.id)
        bot.answer_callback_query(query.id, "Сохранение...")
        profile_conversation.save_profile(user_id, query.message.chat.id)

    @bot.callback_query_handler(func=lambda call: call.data == "profile_cancel")
    def profile_cancel_callback(query: CallbackQuery) -> None:
        if not profile_conversation:
            bot.answer_callback_query(query.id, "Ошибка обработки")
            return

        user_id = str(query.from_user.id)
        bot.answer_callback_query(query.id, "Отменено")
        profile_conversation.cancel_profile_creation(user_id, query.message.chat.id)

    @bot.callback_query_handler(func=lambda call: call.data == "profile_edit")
    def profile_edit_callback(query: CallbackQuery) -> None:
        if not profile_conversation:
            bot.answer_callback_query(query.id, "Ошибка обработки")
            return

        user_id = str(query.from_user.id)
        # Начать редактирование - очистить состояние и начать заново
        from utils.state_manager import state_manager

        state_manager.clear_state(user_id, "profile_creation")
        state_manager.set_state(
            user_id,
            "profile_creation",
            {
                "user_id": user_id,
                "collected_data": {},
                "current_field_index": 0,
            },
        )

        bot.answer_callback_query(query.id, "Редактирование")
        profile_conversation._ask_next_field_by_chat_id(user_id, query.message.chat.id)

    @bot.callback_query_handler(func=lambda call: call.data == "profile_edit_summary")
    def profile_edit_summary_callback(query: CallbackQuery) -> None:
        # Вернуться к первому полю для редактирования
        if not profile_conversation:
            bot.answer_callback_query(query.id, "Ошибка обработки")
            return

        user_id = str(query.from_user.id)
        from utils.state_manager import state_manager

        state = state_manager.get_state(user_id, "profile_creation")
        if state:
            state["current_field_index"] = 0
            state_manager.update_state(user_id, "profile_creation", state)
            bot.answer_callback_query(query.id, "Редактирование")
            profile_conversation._ask_next_field_by_chat_id(user_id, query.message.chat.id)

    # Workout creation callbacks
    @bot.callback_query_handler(func=lambda call: call.data.startswith("workout_day_"))
    def workout_day_callback(query: CallbackQuery) -> None:
        if not workout_creation_manager:
            bot.answer_callback_query(query.id, "Ошибка обработки")
            return
        user_id = str(query.from_user.id)
        day = query.data.replace("workout_day_", "")
        bot.answer_callback_query(query.id, f"Выбран {DAY_NAMES.get(day, day)}")
        workout_creation_manager.handle_day_selection(day, user_id, query.message.chat.id)

    @bot.callback_query_handler(func=lambda call: call.data == "workout_exercise_list")
    def workout_exercise_list_callback(query: CallbackQuery) -> None:
        if not workout_creation_manager:
            bot.answer_callback_query(query.id, "Ошибка обработки")
            return
        user_id = str(query.from_user.id)
        bot.answer_callback_query(query.id, "Выбор категории")
        workout_creation_manager.show_exercise_categories(user_id, query.message.chat.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("workout_category_"))
    def workout_category_callback(query: CallbackQuery) -> None:
        if not workout_creation_manager:
            bot.answer_callback_query(query.id, "Ошибка обработки")
            return
        user_id = str(query.from_user.id)
        category = query.data.replace("workout_category_", "")
        bot.answer_callback_query(query.id, "Выбор упражнения")
        workout_creation_manager.show_exercises_by_category(category, user_id, query.message.chat.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("workout_idx_"))
    def workout_idx_callback(query: CallbackQuery) -> None:
        """Обработчик выбора упражнения по индексу (новый формат с коротким callback_data)."""
        if not workout_creation_manager:
            bot.answer_callback_query(query.id, "Ошибка обработки")
            return
        user_id = str(query.from_user.id)
        from utils.state_manager import state_manager
        
        # Получаем индекс из callback_data: "workout_idx_{idx}"
        data = query.data.replace("workout_idx_", "")
        
        # Получаем состояние пользователя
        state = state_manager.get_state(user_id, "workout_creation")
        if not state:
            bot.answer_callback_query(query.id, "Сессия истекла")
            return
        
        # Получаем список упражнений из состояния
        exercises = state.get("current_category_exercises", [])
        
        if not exercises:
            bot.answer_callback_query(query.id, "Ошибка: список упражнений не найден")
            return
        
        # Получаем упражнение по индексу
        try:
            idx = int(data)
            if 0 <= idx < len(exercises):
                exercise_name = exercises[idx]
            else:
                bot.answer_callback_query(query.id, "Ошибка: неверный индекс")
                logger.error("Invalid index %d for exercises list of length %d", idx, len(exercises))
                return
        except ValueError:
            bot.answer_callback_query(query.id, "Ошибка: неверный формат")
            logger.error("Invalid callback_data format: %s", query.data)
            return
        
        bot.answer_callback_query(query.id, "Упражнение выбрано")
        workout_creation_manager.handle_exercise_selection(exercise_name, user_id, query.message.chat.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("workout_exercise_"))
    def workout_exercise_callback(query: CallbackQuery) -> None:
        """Обработчик для специальных команд workout_exercise_* (list, manual, back)."""
        if not workout_creation_manager:
            bot.answer_callback_query(query.id, "Ошибка обработки")
            return
        user_id = str(query.from_user.id)
        data = query.data.replace("workout_exercise_", "")
        if data == "list":
            bot.answer_callback_query(query.id, "Выбор категории")
            workout_creation_manager.show_exercise_categories(user_id, query.message.chat.id)
        elif data == "manual":
            bot.answer_callback_query(query.id, "Введите название")
            msg = bot.send_message(query.message.chat.id, "Введите название упражнения:")
            bot.register_next_step_handler(msg, workout_creation_manager.handle_exercise_manual_input)
        elif data == "back":
            bot.answer_callback_query(query.id)
            workout_creation_manager._ask_exercise_choice(user_id, query.message.chat.id)
        else:
            # Старый формат с полным названием (для обратной совместимости)
            # Но если название длинное, это может не сработать из-за лимита 64 байта
            bot.answer_callback_query(query.id, "Упражнение выбрано")
            workout_creation_manager.handle_exercise_selection(data, user_id, query.message.chat.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("sel_wk_"))
    def select_workout_callback(query: CallbackQuery) -> None:
        """Обработчик выбора тренировки для выполнения (новый формат с индексом)."""
        user_id = str(query.from_user.id)
        from utils.state_manager import state_manager
        
        # Получаем индекс из callback_data: "sel_wk_{idx}"
        try:
            idx = int(query.data.replace("sel_wk_", ""))
        except ValueError:
            bot.answer_callback_query(query.id, "Ошибка: неверный формат")
            logger.error("Invalid workout selection callback_data: %s", query.data)
            return
        
        # Получаем список тренировок из состояния
        selection_state = state_manager.get_state(user_id, "workout_selection")
        if not selection_state:
            bot.answer_callback_query(query.id, "Сессия истекла. Выберите тренировку заново")
            return
        
        workout_entry_ids = selection_state.get("workouts", [])
        if idx < 0 or idx >= len(workout_entry_ids):
            bot.answer_callback_query(query.id, "Ошибка: неверный индекс")
            logger.error("Invalid workout index: %d, total workouts: %d", idx, len(workout_entry_ids))
            return
        
        # Получаем тренировку по entry_id
        entry_id = workout_entry_ids[idx]
        workout = storage.get_workout_entry(user_id, entry_id)
        
        if not workout:
            bot.answer_callback_query(query.id, "Тренировка не найдена")
            logger.error("Workout not found: entry_id=%s, user_id=%s", entry_id, user_id)
            return
        
        bot.answer_callback_query(query.id, "Тренировка выбрана")
        
        # Показываем детали тренировки
        from utils.constants import DAY_NAMES
        day_name = DAY_NAMES.get(workout.day_of_week, workout.day_of_week)
        name = workout.workout_name or "Тренировка"
        
        text_lines = [f"💪 {name} ({day_name})\n\nУпражнения:"]
        for ex in workout.exercises:
            weight_str = f", {ex.weight} кг" if ex.weight else ""
            text_lines.append(f"• {ex.name}: {ex.sets}×{ex.reps}{weight_str}")
        
        text_lines.append("\nНажмите '✅ Выполнить' чтобы начать тренировку")
        
        # Используем индекс и в callback_data для выполнения
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ Выполнить тренировку", callback_data=f"exec_wk_{idx}"))
        markup.add(InlineKeyboardButton("❌ Отменить", callback_data="workout_select_cancel"))
        
        bot.send_message(query.message.chat.id, "\n".join(text_lines), reply_markup=markup)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("select_workout_"))
    def select_workout_old_callback(query: CallbackQuery) -> None:
        """Обработчик выбора тренировки (старый формат с полным UUID)."""
        user_id = str(query.from_user.id)
        entry_id = query.data.replace("select_workout_", "")
        
        # Получаем тренировку по ID
        workout = storage.get_workout_entry(user_id, entry_id)
        if not workout:
            bot.answer_callback_query(query.id, "Тренировка не найдена")
            return
        
        bot.answer_callback_query(query.id, "Тренировка выбрана")
        
        # Показываем детали тренировки
        from utils.constants import DAY_NAMES
        day_name = DAY_NAMES.get(workout.day_of_week, workout.day_of_week)
        name = workout.workout_name or "Тренировка"
        
        text_lines = [f"💪 {name} ({day_name})\n\nУпражнения:"]
        for ex in workout.exercises:
            weight_str = f", {ex.weight} кг" if ex.weight else ""
            text_lines.append(f"• {ex.name}: {ex.sets}×{ex.reps}{weight_str}")
        
        text_lines.append("\nНажмите '✅ Выполнить' чтобы начать тренировку")
        
        markup = InlineKeyboardMarkup()
        # Используем короткий ID для callback_data
        short_id = entry_id[:8] if len(entry_id) > 8 else entry_id
        markup.add(InlineKeyboardButton("✅ Выполнить тренировку", callback_data=f"exec_wk_{short_id}"))
        markup.add(InlineKeyboardButton("❌ Отменить", callback_data="workout_select_cancel"))
        
        bot.send_message(query.message.chat.id, "\n".join(text_lines), reply_markup=markup)
    
    @bot.callback_query_handler(func=lambda call: call.data == "workout_select_cancel")
    def workout_select_cancel_callback(query: CallbackQuery) -> None:
        """Отменить выбор тренировки."""
        bot.answer_callback_query(query.id, "Отменено")
        bot.send_message(query.message.chat.id, "Выбор тренировки отменен.")
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("exec_wk_"))
    def execute_workout_callback(query: CallbackQuery) -> None:
        """Начать выполнение выбранной тренировки (новый формат с индексом)."""
        user_id = str(query.from_user.id)
        from utils.state_manager import state_manager
        
        # Получаем индекс из callback_data: "exec_wk_{idx}"
        try:
            idx = int(query.data.replace("exec_wk_", ""))
        except ValueError:
            bot.answer_callback_query(query.id, "Ошибка: неверный формат")
            logger.error("Invalid workout execution callback_data: %s", query.data)
            return
        
        # Получаем список тренировок из состояния
        selection_state = state_manager.get_state(user_id, "workout_selection")
        if not selection_state:
            bot.answer_callback_query(query.id, "Сессия истекла. Выберите тренировку заново")
            return
        
        workout_entry_ids = selection_state.get("workouts", [])
        if idx < 0 or idx >= len(workout_entry_ids):
            bot.answer_callback_query(query.id, "Ошибка: неверный индекс")
            logger.error("Invalid workout index for execution: %d, total workouts: %d", idx, len(workout_entry_ids))
            return
        
        # Получаем тренировку по entry_id
        entry_id = workout_entry_ids[idx]
        workout = storage.get_workout_entry(user_id, entry_id)
        
        if not workout:
            bot.answer_callback_query(query.id, "Тренировка не найдена")
            logger.error("Workout not found for execution: entry_id=%s, user_id=%s", entry_id, user_id)
            return
        
        bot.answer_callback_query(query.id, "Тренировка начата!")
        
        # Показываем тренировку с кнопкой "Выполнено"
        from handlers.commands import _send_workout
        _send_workout(bot, query.message.chat.id, workout)
        
        # Очищаем состояние выбора тренировки
        state_manager.clear_state(user_id, "workout_selection")
        
    @bot.callback_query_handler(func=lambda call: call.data.startswith("execute_workout_"))
    def execute_workout_old_callback(query: CallbackQuery) -> None:
        """Начать выполнение выбранной тренировки (старый формат с полным UUID)."""
        user_id = str(query.from_user.id)
        entry_id = query.data.replace("execute_workout_", "")
        
        # Получаем тренировку
        workout = storage.get_workout_entry(user_id, entry_id)
        if not workout:
            bot.answer_callback_query(query.id, "Тренировка не найдена")
            return
        
        bot.answer_callback_query(query.id, "Тренировка начата!")
        
        # Показываем тренировку с кнопкой "Выполнено"
        from handlers.commands import _send_workout
        _send_workout(bot, query.message.chat.id, workout)
        
    @bot.callback_query_handler(func=lambda call: call.data.startswith("workout_sets_"))
    def workout_sets_callback(query: CallbackQuery) -> None:
        if not workout_creation_manager:
            bot.answer_callback_query(query.id, "Ошибка обработки")
            return
        user_id = str(query.from_user.id)
        data = query.data.replace("workout_sets_", "")
        if data == "manual":
            bot.answer_callback_query(query.id, "Введите количество")
            workout_creation_manager._ask_sets_manual(user_id, query.message.chat.id)
        else:
            try:
                sets = int(data)
                bot.answer_callback_query(query.id, f"Выбрано {sets} подходов")
                workout_creation_manager.handle_sets_selection(sets, user_id, query.message.chat.id)
            except ValueError:
                bot.answer_callback_query(query.id, "Ошибка")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("workout_weight_"))
    def workout_weight_callback(query: CallbackQuery) -> None:
        if not workout_creation_manager:
            bot.answer_callback_query(query.id, "Ошибка обработки")
            return
        user_id = str(query.from_user.id)
        data = query.data.replace("workout_weight_", "")
        if data == "skip":
            bot.answer_callback_query(query.id, "Без веса")
            workout_creation_manager.handle_weight_skip(user_id, query.message.chat.id)
        elif data == "manual":
            bot.answer_callback_query(query.id, "Введите вес")
            workout_creation_manager._ask_weight_manual(user_id, query.message.chat.id)

    @bot.callback_query_handler(func=lambda call: call.data == "workout_add_exercise")
    def workout_add_exercise_callback(query: CallbackQuery) -> None:
        if not workout_creation_manager:
            bot.answer_callback_query(query.id, "Ошибка обработки")
            return
        user_id = str(query.from_user.id)
        bot.answer_callback_query(query.id)
        workout_creation_manager._ask_exercise_choice(user_id, query.message.chat.id)

    @bot.callback_query_handler(func=lambda call: call.data == "workout_save")
    def workout_save_callback(query: CallbackQuery) -> None:
        if not workout_creation_manager:
            bot.answer_callback_query(query.id, "Ошибка обработки")
            return
        user_id = str(query.from_user.id)
        bot.answer_callback_query(query.id, "Сохранение...")
        workout_creation_manager.save_workout(user_id, query.message.chat.id)

    @bot.callback_query_handler(func=lambda call: call.data == "workout_cancel")
    def workout_cancel_callback(query: CallbackQuery) -> None:
        if not workout_creation_manager:
            bot.answer_callback_query(query.id, "Ошибка обработки")
            return
        user_id = str(query.from_user.id)
        bot.answer_callback_query(query.id, "Отменено")
        workout_creation_manager.cancel_workout_creation(user_id, query.message.chat.id)
