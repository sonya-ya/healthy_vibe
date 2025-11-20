from __future__ import annotations

import json
import logging
import re
from datetime import date
from typing import List, Optional

from repositories.models import Exercise, UserProfile, WorkoutEntry, WorkoutPlan
from repositories.storage import StorageRepository
from services.openai_service import OpenAIService
from utils.constants import DAY_NAMES

logger = logging.getLogger(__name__)

# Дни недели в правильном порядке
WEEK_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def create_workout_plan_with_llm(
    user_id: str,
    profile: UserProfile,
    storage: StorageRepository,
    openai_service: OpenAIService,
) -> Optional[WorkoutPlan]:
    """Создать план тренировок через LLM на основе профиля пользователя."""
    logger.info("Creating workout plan via LLM: user_id=%s", user_id)
    
    if not openai_service.is_available():
        logger.error("OpenAI service unavailable")
        raise ValueError("Сервис ИИ временно недоступен. Попробуйте позже.")
    
    # Формируем промпт для LLM
    profile_info = f"""
Профиль пользователя:
- Возраст: {profile.age} лет
- Пол: {profile.gender}
- Вес: {profile.weight} кг
- Цель: {profile.goal}
- Опыт: {profile.experience}
- Место тренировок: {profile.preferred_location}
- Время тренировок: {profile.workout_time}
"""
    
    prompt = f"""Ты профессиональный тренер. Создай персональный план тренировок на неделю (7 дней) для следующего пользователя:

{profile_info}

Требования:
1. Создай план на 7 дней недели (понедельник - воскресенье)
2. Каждый день должен содержать тренировку с 3-5 упражнениями
3. Учитывай цель пользователя ({profile.goal}), опыт ({profile.experience}) и место тренировок ({profile.preferred_location})
4. Для кардио дней можно использовать меньше упражнений
5. Включи дни отдыха (1-2 дня в неделю)

Верни ответ ТОЛЬКО в формате JSON без дополнительного текста:
{{
  "plan_name": "Название плана",
  "workouts": [
    {{
      "day": "mon",
      "workout_name": "Название тренировки",
      "exercises": [
        {{
          "name": "Название упражнения",
          "sets": 3,
          "reps": 12,
          "weight": 10
        }}
      ]
    }}
  ]
}}

Дни недели: mon (понедельник), tue (вторник), wed (среда), thu (четверг), fri (пятница), sat (суббота), sun (воскресенье).
Для дней отдыха верни пустой массив exercises или пропусти день.

Важно: верни ТОЛЬКО валидный JSON, без markdown форматирования, без дополнительных комментариев."""

    try:
        logger.debug("Sending plan creation request to LLM")
        response = openai_service.generate_answer(prompt, None)
        logger.debug("LLM response received: length=%d", len(response))
        
        # Извлекаем JSON из ответа (может быть обернут в markdown или текст)
        json_text = _extract_json_from_response(response)
        
        # Парсим JSON
        plan_data = json.loads(json_text)
        logger.debug("Plan data parsed: plan_name=%s, workouts_count=%d", 
                    plan_data.get("plan_name"), len(plan_data.get("workouts", [])))
        
        # Создаем WorkoutEntry объекты
        entries = []
        for workout_data in plan_data.get("workouts", []):
            day = workout_data.get("day")
            if not day or day not in WEEK_DAYS:
                logger.warning("Invalid day in workout data: %s", day)
                continue
            
            exercises = []
            for ex_data in workout_data.get("exercises", []):
                exercises.append(
                    Exercise(
                        name=ex_data.get("name", "Упражнение"),
                        sets=ex_data.get("sets", 3),
                        reps=ex_data.get("reps", 12),
                        weight=ex_data.get("weight"),
                        rest_seconds=60,
                    )
                )
            
            # Пропускаем дни отдыха (без упражнений)
            if not exercises:
                logger.debug("Skipping rest day: %s", day)
                continue
            
            workout_entry = WorkoutEntry(
                day_of_week=day,
                exercises=exercises,
                workout_name=workout_data.get("workout_name"),
            )
            entries.append(workout_entry)
        
        if not entries:
            raise ValueError("LLM не создал ни одной тренировки в плане")
        
        # Создаем план
        plan = WorkoutPlan(
            user_id=user_id,
            name=plan_data.get("plan_name"),
            start_date=date.today(),
            entries=entries,
            is_active=True,
        )
        
        # Сохраняем план
        storage.save_workout_plan(plan)
        logger.info("Plan created and saved: user_id=%s, plan_id=%s, entries_count=%d",
                   user_id, plan.plan_id, len(entries))
        
        return plan
        
    except json.JSONDecodeError as e:
        logger.exception("Failed to parse JSON from LLM response: %s", e)
        logger.error("LLM response was: %s", response[:500])
        raise ValueError("Не удалось обработать ответ ИИ. Попробуйте еще раз.")
    except Exception as e:
        logger.exception("Error creating plan via LLM: %s", e)
        raise


def _extract_json_from_response(response: str) -> str:
    """Извлечь JSON из ответа LLM (может быть обернут в markdown или текст)."""
    # Убираем markdown форматирование
    response = response.strip()
    
    # Пытаемся найти JSON блок
    # Вариант 1: JSON обернут в ```json ... ```
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
    if json_match:
        return json_match.group(1)
    
    # Вариант 2: JSON обернут в ``` ... ```
    json_match = re.search(r'```\s*(\{.*?\})\s*```', response, re.DOTALL)
    if json_match:
        return json_match.group(1)
    
    # Вариант 3: Ищем первый { и последний }
    start_idx = response.find('{')
    end_idx = response.rfind('}')
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        return response[start_idx:end_idx + 1]
    
    # Вариант 4: Возвращаем весь ответ (надеемся что это JSON)
    return response

