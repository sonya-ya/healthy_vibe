from __future__ import annotations

import logging
import signal
import sys
from typing import Optional

import telebot

from config import settings
from handlers.callbacks import register_callback_handlers
from handlers.commands import register_command_handlers
from handlers.conversation import register_conversation_handlers
from handlers.menu_handler import MenuHandler
from handlers.progress_handler import ProgressHandler
from handlers.text import register_text_handler
from handlers.workout_creation import register_workout_creation_handlers
from handlers.workout_management_handler import WorkoutManagementHandler
from repositories.file_storage import FileStorageRepository
from services.openai_service import openai_service
from services.progress_service import EnhancedProgressService, ProgressService
from services.reminder_service import ReminderService
from services.workout_service import WorkoutService
from utils.logging import configure_logging

logger = logging.getLogger(__name__)


def create_bot() -> telebot.TeleBot:
    configure_logging()
    logger.info("Starting Training Assistant bot in %s mode", settings.environment)

    storage = FileStorageRepository()
    workout_service = WorkoutService(storage)
    progress_service = EnhancedProgressService(storage)

    bot = telebot.TeleBot(settings.bot_token)#, parse_mode="HTML")
    
    reminder_service = ReminderService(storage, notifier=lambda u, m: bot.send_message(int(u), m))

    # Создаем меню-обработчик
    menu_handler = MenuHandler(bot, storage, workout_service, reminder_service)

    # Создаем обработчики для новых функций
    workout_management_handler = WorkoutManagementHandler(bot, storage, workout_service, menu_handler)
    progress_handler = ProgressHandler(bot, storage, progress_service, menu_handler)

    profile_conversation = register_conversation_handlers(bot, storage)
    workout_creation_manager = register_workout_creation_handlers(bot, storage, workout_service)
    
    # Регистрируем обработчики с меню
    register_command_handlers(bot, storage, workout_service, progress_service, reminder_service, menu_handler)
    register_callback_handlers(
        bot, progress_service, workout_service, storage, profile_conversation, workout_creation_manager
    )
    
    # Регистрируем обработчики меню с новыми обработчиками
    menu_handler.register_menu_handlers(
        workout_management_handler=workout_management_handler,
        progress_handler=progress_handler,
        workout_creation_manager=workout_creation_manager,
    )
    
    # Регистрируем обработчики для новых функций
    workout_management_handler.register_handlers()
    progress_handler.register_handlers()
    
    # Текстовый обработчик должен быть последним, чтобы не перехватывать кнопки меню
    register_text_handler(bot, storage, openai_service)

    def shutdown(*_: object) -> None:
        logger.info("Shutting down bot")
        reminder_service.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    return bot


def main() -> None:
    bot = create_bot()
    if settings.webhook_url:
        logger.info("Configuring webhook at %s", settings.webhook_url)
        bot.remove_webhook()
        bot.set_webhook(settings.webhook_url)
    else:
        logger.info("Starting polling with interval %s", settings.polling_interval)
        bot.infinity_polling(interval=settings.polling_interval, skip_pending=True)


if __name__ == "__main__":
    main()
