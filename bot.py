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
from handlers.text import register_text_handler
from handlers.workout_creation import register_workout_creation_handlers
from handlers.workout_management_handler import WorkoutManagementHandler
from repositories.file_storage import FileStorageRepository
from services.openai_service import openai_service
from services.reminder_service import ReminderService
from services.workout_service import WorkoutService
from utils.logging import configure_logging

logger = logging.getLogger(__name__)


def create_bot() -> telebot.TeleBot:
    configure_logging()
    logger.info("=" * 60)
    logger.info("Starting Training Assistant bot")
    logger.info("Environment: %s", settings.environment)
    logger.info("Data directory: %s", settings.data_dir)
    logger.info("Logs directory: %s", settings.logs_dir)
    logger.info("=" * 60)

    logger.debug("Initializing storage repository")
    storage = FileStorageRepository()
    logger.debug("Storage repository initialized")
    
    logger.debug("Initializing workout service")
    workout_service = WorkoutService(storage)
    logger.debug("Workout service initialized")

    logger.debug("Creating TeleBot instance")
    bot = telebot.TeleBot(settings.bot_token)#, parse_mode="HTML")
    logger.info("TeleBot instance created")
    
    logger.debug("Initializing reminder service")
    reminder_service = ReminderService(storage, notifier=lambda u, m: bot.send_message(int(u), m))
    logger.debug("Reminder service initialized")

    # Создаем меню-обработчик
    logger.debug("Initializing menu handler")
    menu_handler = MenuHandler(bot, storage, workout_service, reminder_service)
    logger.debug("Menu handler initialized")

    # Создаем обработчики для новых функций
    logger.debug("Initializing workout management handler")
    workout_management_handler = WorkoutManagementHandler(bot, storage, workout_service, menu_handler)
    logger.debug("Workout management handler initialized")

    logger.debug("Registering conversation handlers")
    profile_conversation = register_conversation_handlers(bot, storage)
    logger.debug("Conversation handlers registered")
    
    logger.debug("Registering workout creation handlers")
    workout_creation_manager = register_workout_creation_handlers(bot, storage, workout_service)
    logger.debug("Workout creation handlers registered")
    
    # Регистрируем обработчики с меню
    logger.debug("Registering command handlers")
    register_command_handlers(bot, storage, workout_service, None, reminder_service, menu_handler)
    logger.debug("Command handlers registered")
    
    logger.debug("Registering callback handlers")
    register_callback_handlers(
        bot, workout_service, storage, profile_conversation, workout_creation_manager
    )
    logger.debug("Callback handlers registered")
    
    # Регистрируем обработчики меню с новыми обработчиками
    logger.debug("Registering menu handlers")
    menu_handler.register_menu_handlers(
        workout_management_handler=workout_management_handler,
        workout_creation_manager=workout_creation_manager,
    )
    logger.debug("Menu handlers registered")
    
    # Регистрируем обработчики для новых функций
    logger.debug("Registering workout management handlers")
    workout_management_handler.register_handlers()
    logger.debug("Workout management handlers registered")
    
    # Текстовый обработчик должен быть последним, чтобы не перехватывать кнопки меню
    logger.debug("Registering text handler")
    register_text_handler(bot, storage, openai_service)
    logger.debug("Text handler registered")
    
    logger.info("All handlers registered successfully. Bot is ready to start.")

    def shutdown(*_: object) -> None:
        logger.info("Shutting down bot")
        reminder_service.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    return bot


def main() -> None:
    try:
        bot = create_bot()
        if settings.webhook_url:
            logger.info("Configuring webhook: url=%s", settings.webhook_url)
            bot.remove_webhook()
            bot.set_webhook(settings.webhook_url)
            logger.info("Webhook configured successfully")
        else:
            logger.info("Starting polling: interval=%.1fs, skip_pending=%s", 
                       settings.polling_interval, True)
            bot.infinity_polling(interval=settings.polling_interval, skip_pending=True)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (KeyboardInterrupt)")
    except Exception as e:
        logger.exception("Fatal error in main: %s", str(e))
        raise


if __name__ == "__main__":
    main()
