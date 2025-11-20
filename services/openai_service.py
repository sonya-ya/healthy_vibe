from __future__ import annotations

import logging
from typing import Optional

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency for dev environments
    OpenAI = None  # type: ignore

from config import settings
from utils.constants import MEDICAL_DISCLAIMER
from utils.exceptions import OpenAIError

logger = logging.getLogger(__name__)


class OpenAIService:
    """Wrapper around OpenAI chat models with domain-specific helpers."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key or settings.openai_api_key
        if self._api_key and OpenAI:
            self._client = OpenAI(api_key=self._api_key, base_url="https://api.proxyapi.ru/openai/v1")
            logger.info("OpenAI service initialized: base_url=%s, has_api_key=%s", 
                       "https://api.proxyapi.ru/openai/v1", bool(self._api_key))
        else:
            self._client = None
            logger.warning("OpenAI service not initialized: OpenAI module=%s, has_api_key=%s",
                          OpenAI is not None, bool(self._api_key))

    def is_available(self) -> bool:
        available = self._client is not None
        logger.debug("OpenAI service availability check: %s", available)
        return available

    def is_query_relevant(self, prompt: str) -> bool:
        """Быстрая проверка релевантности БЕЗ вызова API - только по ключевым словам."""
        keywords = [
            "трениров", "упражн", "спорт", "фитнес", "workout", "exercise",
            "мышц", "вес", "повтор", "кардио", "растяж", "программа",
            "план", "режим", "диета", "питание", "белок", "жир", "углевод",
            "выносливость", "сила", "масса", "похудение", "набор", "как",
            "что", "почему", "когда", "сколько", "лучш", "рекоменд",
        ]
        prompt_lower = prompt.lower()
        # Только проверка по ключевым словам - НЕ вызываем API для классификации
        return any(word in prompt_lower for word in keywords)

    def generate_answer(self, prompt: str, profile_context: Optional[str] = None) -> str:
        logger.debug("generate_answer called: prompt_length=%d, has_profile_context=%s",
                    len(prompt), profile_context is not None)
        
        if not self._client:
            logger.warning("OpenAI client unavailable, returning fallback response")
            return (
                "Сейчас я не могу обратиться к интеллектуальному помощнику."
                " Попробуйте позже."  # noqa: E501
            )

        system_prompt = (
            "Ты — виртуальный тренер. Отвечай кратко и по сути, придерживайся"
            " спортивной тематики. В конце каждого ответа добавляй дисклеймер"
            " о необходимости консультации с врачом при серьёзных симптомах."
        )

        messages = [
            {"role": "system", "content": system_prompt},
        ]
        if profile_context:
            messages.append({"role": "user", "content": profile_context})
            logger.debug("Added profile context to messages")
        messages.append({"role": "user", "content": prompt})
        
        logger.info("Sending request to OpenAI API: model=gpt-5-nano, messages_count=%d, prompt_preview=%.50s...",
                   len(messages), prompt)

        try:
            import time
            start_time = time.time()
            response = self._client.chat.completions.create(
                model="gpt-5-nano",
                messages=messages
            )
            elapsed_time = time.time() - start_time
            answer = response.choices[0].message.content.strip()
            logger.info("OpenAI API response received: elapsed_time=%.2fs, answer_length=%d, tokens_used=%s",
                       elapsed_time, len(answer), 
                       getattr(response.usage, 'total_tokens', 'unknown') if hasattr(response, 'usage') else 'unknown')
        except Exception as exc:  # pragma: no cover - network failure
            logger.exception("OpenAI generate_answer failed: error=%s, error_type=%s", str(exc), type(exc).__name__)
            raise OpenAIError("Failed to generate response from OpenAI") from exc

        if MEDICAL_DISCLAIMER not in answer:
            answer = f"{answer}\n\n{MEDICAL_DISCLAIMER}"
            logger.debug("Added medical disclaimer to answer")
        
        logger.debug("generate_answer completed: final_answer_length=%d", len(answer))
        return answer


openai_service = OpenAIService()
