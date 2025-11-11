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
    "📊 Прогресс",
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
    "⚡ Быстрая тренировка",
    "📈 Общая статистика",
    "💪 По тренировкам",
    "🏋️ По упражнениям",
    "📉 Графики",
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
        prompt = message.text.strip()
        if not prompt:
            return
        
        # Быстрая проверка на ключевые слова перед вызовом OpenAI
        keywords = [
            "трениров", "упражн", "спорт", "фитнес", "workout", "exercise",
            "мышц", "вес", "повтор", "кардио", "растяж",
        ]
        prompt_lower = prompt.lower()
        has_keywords = any(word in prompt_lower for word in keywords)
        
        if not has_keywords:
            # Если нет ключевых слов, проверяем через OpenAI (но это медленно)
            # Для ускорения - просто говорим, что это не про тренировки
            bot.send_message(message.chat.id, "Пожалуйста, задавайте вопросы по теме тренировок и фитнеса.")
            return
        
        # Быстрая проверка релевантности без вызова API
        if not openai_service.is_query_relevant(prompt):
            bot.send_message(message.chat.id, "Пожалуйста, задавайте вопросы по теме тренировок.")
            return
        
        profile = storage.get_profile(str(message.from_user.id))
        profile_context = None
        if profile:
            profile_context = (
                "Профиль пользователя: цель {goal}, опыт {experience}, вес {weight}"
            ).format(**profile.dict())
        
        answer = openai_service.generate_answer(prompt, profile_context)
        if MEDICAL_DISCLAIMER not in answer:
            answer = f"{answer}\n\n{MEDICAL_DISCLAIMER}"
        bot.send_message(message.chat.id, answer)
        logger.info("LLM response sent to user %s", message.from_user.id)
