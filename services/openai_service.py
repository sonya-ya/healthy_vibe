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
        else:
            self._client = None

    def is_available(self) -> bool:
        return self._client is not None

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
        if not self._client:
            logger.info("OpenAI client unavailable, returning fallback response")
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
        messages.append({"role": "user", "content": prompt})

        try:
            response = self._client.chat.completions.create(
                model="gpt-5-nano",
                messages=messages
            )
            answer = response.choices[0].message.content.strip()
        except Exception as exc:  # pragma: no cover - network failure
            logger.exception("OpenAI generate_answer failed: %s", exc)
            raise OpenAIError("Failed to generate response from OpenAI") from exc

        if MEDICAL_DISCLAIMER not in answer:
            answer = f"{answer}\n\n{MEDICAL_DISCLAIMER}"
        return answer


openai_service = OpenAIService()
