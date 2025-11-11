from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from telebot import TeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from analytics.charts import generate_progress_chart
from repositories.models import ProgressEntry, ReminderConfig
from repositories.storage import StorageRepository
from services.progress_service import ProgressService
from services.reminder_service import ReminderService
from services.workout_service import WorkoutService
from utils.constants import HELP_MESSAGE, MEDICAL_DISCLAIMER, WELCOME_MESSAGE

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


def register_command_handlers(
    bot: TeleBot,
    storage: StorageRepository,
    workout_service: WorkoutService,
    progress_service: ProgressService,
    reminder_service: ReminderService,
    menu_handler=None,
) -> None:
    @bot.message_handler(commands=["start"])
    def start_handler(message: Message) -> None:
        user_id = str(message.from_user.id)
        if menu_handler:
            menu_handler.show_main_menu(message.chat.id, f"{WELCOME_MESSAGE}\n\n{HELP_MESSAGE}", user_id)
        else:
            bot.send_message(message.chat.id, f"{WELCOME_MESSAGE}\n\n{HELP_MESSAGE}")

    @bot.message_handler(commands=["help"])
    def help_handler(message: Message) -> None:
        bot.send_message(message.chat.id, HELP_MESSAGE)

    @bot.message_handler(commands=["workout"])
    def workout_handler(message: Message) -> None:
        user_id = str(message.from_user.id)
        profile = storage.get_profile(user_id)
        if not profile:
            bot.send_message(message.chat.id, "Сначала заполните профиль командой /profile")
            return

        focus = "legs"
        if len(message.text.split()) > 1:
            focus = message.text.split()[1]

        templates = workout_service.get_available_templates(profile, focus)
        if templates:
            markup = InlineKeyboardMarkup(row_width=1)
            for template in templates[:10]:  # Limit to 10 templates
                markup.add(
                    InlineKeyboardButton(
                        f"{template.name}",
                        callback_data=f"template_{template.template_id}",
                    )
                )
            markup.add(InlineKeyboardButton("Случайная тренировка", callback_data="template_random"))
            bot.send_message(
                message.chat.id,
                "Выберите темплейт тренировки или случайную:",
                reply_markup=markup,
            )
        else:
            # Fallback to random generation
            workout_entry = workout_service.generate_daily_workout(profile, focus)
            workout_service.save_standalone_workout(user_id, workout_entry)
            _send_workout(bot, message.chat.id, workout_entry)

    @bot.message_handler(commands=["progress"])
    def progress_handler(message: Message) -> None:
        user_id = str(message.from_user.id)
        # Команда /progress теперь показывает меню прогресса через кнопку меню
        # Просто перенаправляем на кнопку меню
        if menu_handler:
            # Создаем временный объект сообщения с текстом кнопки
            from handlers.progress_handler import ProgressHandler
            # Но проще просто показать меню прогресса
            # Для этого нужно получить progress_handler из контекста
            # Пока просто показываем старое поведение, но с меню
            entries = progress_service.fetch_entries(user_id)
            summary = progress_service.summarize(user_id)
            text = (
                f"📊 Прогресс\n\n"
                f"Всего сессий: {summary.get('sessions', 0)}\n"
                f"Средний вес: {summary.get('average_weight') or '—'}\n\n"
                f"Используйте меню '📊 Прогресс' для детальной информации."
            )
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("Анализ прогресса", callback_data="analyse"))
            bot.send_message(message.chat.id, text, reply_markup=markup)
        else:
            entries = progress_service.fetch_entries(user_id)
            if not entries:
                bot.send_message(message.chat.id, "Пока нет записей о прогрессе. Отмечайте тренировки!")
                return
            summary = progress_service.summarize(user_id)
            text = (
                f"Всего сессий: {summary.get('sessions', 0)}\n"
                f"Средний вес: {summary.get('average_weight') or '—'}"
            )
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("Анализ прогресса", callback_data="analyse"))
            bot.send_message(message.chat.id, text, reply_markup=markup)

    @bot.message_handler(commands=["reminders"])
    def reminders_handler(message: Message) -> None:
        user_id = str(message.from_user.id)
        reminders = list(reminder_service.list_reminders(user_id))
        if not reminders:
            bot.send_message(message.chat.id, "Напоминания пока не настроены. Используйте /setreminder командой вида: /setreminder training 09:00 daily")
            return
        lines = ["Ваши напоминания:"]
        for r in reminders:
            lines.append(f"• {r.type} в {r.time.strftime('%H:%M')} ({r.frequency})")
        bot.send_message(message.chat.id, "\n".join(lines))

    @bot.message_handler(commands=["setreminder"])
    def set_reminder_handler(message: Message) -> None:
        parts = message.text.split()
        if len(parts) < 4:
            bot.send_message(message.chat.id, "Используйте формат: /setreminder <type> <HH:MM> <daily|weekly>")
            return
        reminder_type, time_str, frequency = parts[1:4]
        try:
            reminder_time = datetime.strptime(time_str, "%H:%M").time()
        except ValueError:
            bot.send_message(message.chat.id, "Некорректное время. Используйте формат HH:MM")
            return
        reminder = ReminderConfig(
            user_id=str(message.from_user.id),
            reminder_id=f"{reminder_type}_{time_str}",
            type=reminder_type,
            time=reminder_time,
            frequency=frequency,
            message=f"Напоминание: {reminder_type}",
        )
        reminder_service.schedule_reminder(reminder)
        bot.send_message(message.chat.id, "Напоминание сохранено")

    @bot.message_handler(commands=["createplan"])
    def create_plan_handler(message: Message) -> None:
        user_id = str(message.from_user.id)
        profile = storage.get_profile(user_id)
        if not profile:
            bot.send_message(message.chat.id, "Сначала заполните профиль командой /profile")
            return
        focus_order = ["legs", "back", "cardio"]
        entries = []
        for focus in focus_order:
            entries.append(workout_service.generate_daily_workout(profile, focus))
        plan = workout_service.save_plan(user_id, entries)
        bot.send_message(message.chat.id, f"План на {len(plan.entries)} тренировки сохранён")

    @bot.message_handler(commands=["logworkout"])
    def log_workout_handler(message: Message) -> None:
        user_id = str(message.from_user.id)
        # Простое логирование через ProgressEntry (без конкретной тренировки)
        entry = ProgressEntry(
            user_id=user_id,
            weight=None,
            measurements={},
            mood=None,
        )
        progress_service.add_entry(entry)
        reply_text = "Отлично! Тренировка отмечена.\n" + MEDICAL_DISCLAIMER
        if menu_handler:
            menu_handler.show_main_menu(message.chat.id, reply_text, user_id)
        else:
            bot.send_message(message.chat.id, reply_text)
