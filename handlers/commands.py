from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from telebot import TeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from repositories.models import ReminderConfig
from repositories.storage import StorageRepository
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
    bot.send_message(chat_id, "\n".join(text_lines))


def register_command_handlers(
    bot: TeleBot,
    storage: StorageRepository,
    workout_service: WorkoutService,
    progress_service,
    reminder_service: ReminderService,
    menu_handler=None,
) -> None:
    @bot.message_handler(commands=["start"])
    def start_handler(message: Message) -> None:
        user_id = str(message.from_user.id)
        username = message.from_user.username or "unknown"
        logger.info("Command /start: user_id=%s, username=%s, chat_id=%d", 
                   user_id, username, message.chat.id)
        if menu_handler:
            menu_handler.show_main_menu(message.chat.id, f"{WELCOME_MESSAGE}\n\n{HELP_MESSAGE}", user_id)
        else:
            bot.send_message(message.chat.id, f"{WELCOME_MESSAGE}\n\n{HELP_MESSAGE}")
        logger.debug("Start command completed: user_id=%s", user_id)

    @bot.message_handler(commands=["help"])
    def help_handler(message: Message) -> None:
        user_id = str(message.from_user.id)
        logger.info("Command /help: user_id=%s", user_id)
        bot.send_message(message.chat.id, HELP_MESSAGE)
        logger.debug("Help command completed: user_id=%s", user_id)

    @bot.message_handler(commands=["workout"])
    def workout_handler(message: Message) -> None:
        user_id = str(message.from_user.id)
        logger.info("Command /workout: user_id=%s", user_id)
        
        profile = storage.get_profile(user_id)
        if not profile:
            logger.warning("Profile not found for workout command: user_id=%s", user_id)
            bot.send_message(message.chat.id, "Сначала заполните профиль командой /profile")
            return

        focus = "legs"
        if len(message.text.split()) > 1:
            focus = message.text.split()[1]
            logger.debug("Workout focus specified: user_id=%s, focus=%s", user_id, focus)

        try:
            templates = workout_service.get_available_templates(profile, focus)
            logger.debug("Available templates: user_id=%s, templates_count=%d", user_id, len(templates))
            
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
                logger.info("Templates menu sent: user_id=%s, templates_count=%d", user_id, len(templates))
            else:
                # Fallback to random generation
                logger.debug("No templates available, generating random workout: user_id=%s, focus=%s", user_id, focus)
                workout_entry = workout_service.generate_daily_workout(profile, focus)
                workout_service.save_standalone_workout(user_id, workout_entry)
                _send_workout(bot, message.chat.id, workout_entry)
                logger.info("Random workout generated and sent: user_id=%s, exercises_count=%d",
                           user_id, len(workout_entry.exercises))
        except Exception as e:
            logger.exception("Error in workout handler: user_id=%s, error=%s", user_id, str(e))
            bot.send_message(message.chat.id, "Произошла ошибка при создании тренировки. Попробуйте позже.")


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


