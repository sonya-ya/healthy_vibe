from __future__ import annotations

import logging

from telebot import TeleBot
from telebot.types import Message

from repositories.storage import StorageRepository
from services.openai_service import OpenAIService
from utils.constants import MEDICAL_DISCLAIMER

logger = logging.getLogger(__name__)

# Список известных текстов кнопок меню - их не нужно обрабатывать через OpenAI
MENU_BUTTONS = {
    "📋 Мои тренировки",
    "➕ Создать",
    "⚙️ Настройки",
    "📅 План",
    "🔔 Напоминания",
    "💪 Тренировка",
    "❓ Помощь",
    "🏠 Главное меню",
    "👤 Создать профиль",
    "📅 Все тренировки",
    "📆 По дням недели",
    "📊 Активные планы",
    "📈 Статистика",
    "💪 Создать тренировку",
    "📋 Создать план из тренировок",
    "➕ Создать план",
    "⚡ Быстрая тренировка",
    "👤 Мой профиль",
    "🔕 Уведомления",
    "ℹ️ О боте",
    "📜 История планов",
    "📋 Шаблоны планов",
    "💪 Тренировка на сегодня",
    "📋 Выбрать тренировку",
    "✅ Выполнить тренировку",
    "📋 Мои напоминания",
    "➕ Добавить напоминание",
    "🗑️ Удалить напоминание",
}


def register_text_handler(bot: TeleBot, storage: StorageRepository, openai_service: OpenAIService) -> None:
    """Регистрирует текстовый обработчик, который НЕ обрабатывает кнопки меню."""
    
    @bot.message_handler(content_types=["text"], func=lambda m: m.text and m.text not in MENU_BUTTONS and not m.text.startswith("/"))
    def text_handler(message: Message) -> None:
        """Обрабатывает только текстовые сообщения, которые не являются командами или кнопками меню."""
        user_id = str(message.from_user.id)
        chat_id = message.chat.id
        prompt = message.text.strip()
        
        logger.debug("Text handler called: user_id=%s, chat_id=%d, prompt_length=%d", 
                     user_id, chat_id, len(prompt))
        
        if not prompt:
            logger.debug("Empty prompt, ignoring")
            return
        
        # Проверяем доступность OpenAI
        if not openai_service.is_available():
            logger.warning("OpenAI service unavailable for user %s", user_id)
            bot.send_message(chat_id, "Сейчас я не могу обратиться к интеллектуальному помощнику. Попробуйте позже.")
            return
        
        logger.info("Processing LLM request: user_id=%s, prompt_preview=%.50s...", user_id, prompt)
        
        # Отправляем сообщение о том, что обрабатываем запрос
        bot.send_chat_action(chat_id, "typing")
        
        try:
            profile = storage.get_profile(user_id)
            profile_context = None
            if profile:
                profile_context = (
                    "Профиль пользователя: цель {goal}, опыт {experience}, вес {weight}"
                ).format(**profile.dict())
                logger.debug("Profile context loaded for user %s: goal=%s, experience=%s, weight=%s",
                           user_id, profile.goal, profile.experience, profile.weight)
            else:
                logger.debug("No profile found for user %s", user_id)
            
            logger.debug("Calling OpenAI API: prompt_length=%d, has_profile_context=%s",
                       len(prompt), profile_context is not None)
            answer = openai_service.generate_answer(prompt, profile_context)
            logger.debug("OpenAI response received: answer_length=%d", len(answer))
            
            bot.send_message(chat_id, answer)
            logger.info("LLM response sent successfully: user_id=%s, answer_length=%d", user_id, len(answer))
        except Exception as e:
            logger.exception("Error generating LLM response: user_id=%s, error=%s", user_id, str(e))
            bot.send_message(chat_id, "Произошла ошибка при обработке запроса. Попробуйте позже.")
