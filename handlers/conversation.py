from __future__ import annotations

import logging
from typing import Dict

from telebot import TeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from repositories.models import UserProfile
from repositories.storage import StorageRepository
from services.validation import validate_age, validate_profile_data, validate_weight
from utils.constants import (
    EXPERIENCE_OPTIONS,
    GENDER_OPTIONS,
    GOAL_OPTIONS,
    LOCATION_OPTIONS,
    PROFILE_FIELDS_ORDER,
    WORKOUT_TIME_OPTIONS,
)
from utils.state_manager import state_manager

logger = logging.getLogger(__name__)


class ProfileConversation:
    """Stateful conversation for collecting user profile data with buttons."""

    def __init__(self, bot: TeleBot, storage: StorageRepository) -> None:
        self._bot = bot
        self._storage = storage

    def start_profile_creation(self, message: Message) -> None:
        """Начать процесс создания профиля."""
        user_id = str(message.from_user.id)
        existing_profile = self._storage.get_profile(user_id)

        if existing_profile:
            # Показать существующий профиль с кнопкой редактирования
            profile_text = self._format_profile_summary(existing_profile)
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("Редактировать", callback_data="profile_edit"))
            markup.add(InlineKeyboardButton("Отменить", callback_data="profile_cancel"))
            self._bot.send_message(
                message.chat.id,
                f"Текущий профиль:\n\n{profile_text}\n\nХотите отредактировать?",
                reply_markup=markup,
            )
            return

        # Начать создание нового профиля
        state_manager.set_state(
            user_id,
            "profile_creation",
            {
                "user_id": user_id,
                "collected_data": {},
                "current_field_index": 0,
            },
        )
        self._ask_next_field(message)

    def _ask_next_field(self, message: Message) -> None:
        """Запросить следующее поле профиля."""
        self._ask_next_field_by_chat_id(str(message.from_user.id), message.chat.id)

    def _ask_next_field_by_chat_id(self, user_id: str, chat_id: int) -> None:
        """Запросить следующее поле профиля по chat_id."""
        state = state_manager.get_state(user_id, "profile_creation")
        if not state:
            self._bot.send_message(chat_id, "Сессия истекла. Начните заново командой /profile")
            return

        field_index = state["current_field_index"]
        if field_index >= len(PROFILE_FIELDS_ORDER):
            self._show_summary_by_chat_id(user_id, chat_id)
            return

        field = PROFILE_FIELDS_ORDER[field_index]
        state["current_field"] = field
        state_manager.update_state(user_id, "profile_creation", state)

        if field == "age":
            msg = self._bot.send_message(
                chat_id,
                f"Шаг {field_index + 1} из {len(PROFILE_FIELDS_ORDER)}\n\n"
                "Укажите ваш возраст (от 10 до 100 лет):",
            )
            self._bot.register_next_step_handler(msg, self._handle_age_input)
        elif field == "weight":
            msg = self._bot.send_message(
                chat_id,
                f"Шаг {field_index + 1} из {len(PROFILE_FIELDS_ORDER)}\n\n"
                "Укажите ваш текущий вес в кг (от 20 до 300):",
            )
            self._bot.register_next_step_handler(msg, self._handle_weight_input)
        elif field == "gender":
            self._ask_gender_by_chat_id(user_id, chat_id, field_index)
        elif field == "goal":
            self._ask_goal_by_chat_id(user_id, chat_id, field_index)
        elif field == "experience":
            self._ask_experience_by_chat_id(user_id, chat_id, field_index)
        elif field == "preferred_location":
            self._ask_location_by_chat_id(user_id, chat_id, field_index)
        elif field == "workout_time":
            self._ask_workout_time_by_chat_id(user_id, chat_id, field_index)

    def _handle_age_input(self, message: Message) -> None:
        """Обработать ввод возраста."""
        user_id = str(message.from_user.id)
        is_valid, age, error_msg = validate_age(message.text)

        if not is_valid:
            error_msg_obj = self._bot.send_message(message.chat.id, f"❌ {error_msg}\n\nПопробуйте ещё раз:")
            self._bot.register_next_step_handler(error_msg_obj, self._handle_age_input)
            return

        state = state_manager.get_state(user_id, "profile_creation")
        if state:
            state["collected_data"]["age"] = age
            state["current_field_index"] += 1
            state_manager.update_state(user_id, "profile_creation", state)
            self._ask_next_field(message)

    def _handle_weight_input(self, message: Message) -> None:
        """Обработать ввод веса."""
        user_id = str(message.from_user.id)
        is_valid, weight, error_msg = validate_weight(message.text)

        if not is_valid:
            error_msg_obj = self._bot.send_message(message.chat.id, f"❌ {error_msg}\n\nПопробуйте ещё раз:")
            self._bot.register_next_step_handler(error_msg_obj, self._handle_weight_input)
            return

        state = state_manager.get_state(user_id, "profile_creation")
        if state:
            state["collected_data"]["weight"] = weight
            state["current_field_index"] += 1
            state_manager.update_state(user_id, "profile_creation", state)
            self._ask_next_field(message)

    def _ask_gender_by_chat_id(self, user_id: str, chat_id: int, field_index: int) -> None:
        """Запросить пол через кнопки."""
        markup = InlineKeyboardMarkup(row_width=1)
        for display_name in GENDER_OPTIONS.keys():
            markup.add(
                InlineKeyboardButton(display_name, callback_data=f"profile_field_gender_{GENDER_OPTIONS[display_name]}")
            )
        markup.add(InlineKeyboardButton("❌ Отменить", callback_data="profile_cancel"))
        self._bot.send_message(
            chat_id,
            f"Шаг {field_index + 1} из {len(PROFILE_FIELDS_ORDER)}\n\nВыберите ваш пол:",
            reply_markup=markup,
        )

    def _ask_goal_by_chat_id(self, user_id: str, chat_id: int, field_index: int) -> None:
        """Запросить цель через кнопки."""
        markup = InlineKeyboardMarkup(row_width=1)
        for display_name in GOAL_OPTIONS.keys():
            markup.add(
                InlineKeyboardButton(display_name, callback_data=f"profile_field_goal_{GOAL_OPTIONS[display_name]}")
            )
        markup.add(InlineKeyboardButton("❌ Отменить", callback_data="profile_cancel"))
        self._bot.send_message(
            chat_id,
            f"Шаг {field_index + 1} из {len(PROFILE_FIELDS_ORDER)}\n\nВыберите вашу цель:",
            reply_markup=markup,
        )

    def _ask_experience_by_chat_id(self, user_id: str, chat_id: int, field_index: int) -> None:
        """Запросить уровень опыта через кнопки."""
        markup = InlineKeyboardMarkup(row_width=1)
        for display_name in EXPERIENCE_OPTIONS.keys():
            markup.add(
                InlineKeyboardButton(
                    display_name, callback_data=f"profile_field_experience_{EXPERIENCE_OPTIONS[display_name]}"
                )
            )
        markup.add(InlineKeyboardButton("❌ Отменить", callback_data="profile_cancel"))
        self._bot.send_message(
            chat_id,
            f"Шаг {field_index + 1} из {len(PROFILE_FIELDS_ORDER)}\n\nВыберите ваш уровень подготовки:",
            reply_markup=markup,
        )

    def _ask_location_by_chat_id(self, user_id: str, chat_id: int, field_index: int) -> None:
        """Запросить предпочитаемое место тренировок через кнопки."""
        markup = InlineKeyboardMarkup(row_width=2)
        for display_name in LOCATION_OPTIONS.keys():
            markup.add(
                InlineKeyboardButton(
                    display_name, callback_data=f"profile_field_preferred_location_{LOCATION_OPTIONS[display_name]}"
                )
            )
        markup.add(InlineKeyboardButton("❌ Отменить", callback_data="profile_cancel"))
        self._bot.send_message(
            chat_id,
            f"Шаг {field_index + 1} из {len(PROFILE_FIELDS_ORDER)}\n\nГде вы предпочитаете тренироваться?",
            reply_markup=markup,
        )

    def _ask_workout_time_by_chat_id(self, user_id: str, chat_id: int, field_index: int) -> None:
        """Запросить длительность тренировки через кнопки."""
        markup = InlineKeyboardMarkup(row_width=1)
        for display_name in WORKOUT_TIME_OPTIONS.keys():
            markup.add(
                InlineKeyboardButton(
                    display_name, callback_data=f"profile_field_workout_time_{WORKOUT_TIME_OPTIONS[display_name]}"
                )
            )
        markup.add(InlineKeyboardButton("❌ Отменить", callback_data="profile_cancel"))
        self._bot.send_message(
            chat_id,
            f"Шаг {field_index + 1} из {len(PROFILE_FIELDS_ORDER)}\n\nВыберите предпочитаемую длительность тренировки:",
            reply_markup=markup,
        )

    def handle_button_selection(self, field: str, value: str, user_id: str, chat_id: int) -> None:
        """Обработать выбор значения через кнопку."""
        state = state_manager.get_state(user_id, "profile_creation")
        if not state:
            self._bot.send_message(chat_id, "Сессия истекла. Начните заново командой /profile")
            return

        # Сохранить выбранное значение
        if field == "gender":
            state["collected_data"]["gender"] = value
        elif field == "goal":
            state["collected_data"]["goal"] = value
        elif field == "experience":
            state["collected_data"]["experience"] = value
        elif field == "preferred_location":
            state["collected_data"]["preferred_location"] = value
        elif field == "workout_time":
            state["collected_data"]["workout_time"] = value
        else:
            logger.warning("Unknown field in handle_button_selection: %s with value %s", field, value)
            self._bot.send_message(chat_id, f"Ошибка: неизвестное поле {field}")
            return

        logger.debug("Profile field saved: %s = %s for user %s", field, value, user_id)
        state["current_field_index"] += 1
        state_manager.update_state(user_id, "profile_creation", state)

        # Перейти к следующему полю
        self._ask_next_field_by_chat_id(user_id, chat_id)

    def _show_summary(self, message: Message) -> None:
        """Показать сводку профиля для подтверждения."""
        self._show_summary_by_chat_id(str(message.from_user.id), message.chat.id)

    def _show_summary_by_chat_id(self, user_id: str, chat_id: int) -> None:
        """Показать сводку профиля для подтверждения по chat_id."""
        state = state_manager.get_state(user_id, "profile_creation")
        if not state:
            return

        collected_data = state["collected_data"].copy()  # Копируем, чтобы не изменять оригинал
        collected_data["user_id"] = user_id

        # Логируем собранные данные для отладки
        logger.debug("Collected profile data for user %s: %s", user_id, collected_data)

        # Проверяем, что все необходимые поля заполнены
        required_fields = ["age", "gender", "weight", "goal", "experience", "preferred_location", "workout_time"]
        missing_fields = [field for field in required_fields if field not in collected_data]
        if missing_fields:
            error_msg = f"Не заполнены поля: {', '.join(missing_fields)}"
            logger.error("Missing fields for user %s: %s", user_id, missing_fields)
            self._bot.send_message(chat_id, f"❌ {error_msg}\n\nПожалуйста, начните заново командой /profile")
            return

        try:
            profile, _ = validate_profile_data(collected_data)
            summary_text = self._format_profile_summary(profile)
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("✅ Сохранить", callback_data="profile_save"))
            markup.add(InlineKeyboardButton("✏️ Редактировать", callback_data="profile_edit_summary"))
            markup.add(InlineKeyboardButton("❌ Отменить", callback_data="profile_cancel"))
            self._bot.send_message(
                chat_id,
                f"Проверьте данные профиля:\n\n{summary_text}\n\nСохранить?",
                reply_markup=markup,
            )
        except Exception as exc:
            logger.error("Error validating profile for user %s: %s. Data: %s", user_id, exc, collected_data)
            self._bot.send_message(chat_id, f"Ошибка при проверке данных: {exc}\n\nПожалуйста, начните заново командой /profile")

    def _format_profile_summary(self, profile: UserProfile) -> str:
        """Форматировать сводку профиля для отображения."""
        from utils.constants import (
            EXPERIENCE_DISPLAY,
            GENDER_DISPLAY,
            GOAL_DISPLAY,
            LOCATION_DISPLAY,
            WORKOUT_TIME_DISPLAY,
        )

        return (
            f"Возраст: {profile.age} лет\n"
            f"Пол: {GENDER_DISPLAY.get(profile.gender, profile.gender)}\n"
            f"Вес: {profile.weight} кг\n"
            f"Цель: {GOAL_DISPLAY.get(profile.goal, profile.goal)}\n"
            f"Уровень: {EXPERIENCE_DISPLAY.get(profile.experience, profile.experience)}\n"
            f"Место: {LOCATION_DISPLAY.get(profile.preferred_location, profile.preferred_location)}\n"
            f"Длительность: {WORKOUT_TIME_DISPLAY.get(profile.workout_time, profile.workout_time)}"
        )

    def save_profile(self, user_id: str, chat_id: int) -> None:
        """Сохранить профиль."""
        state = state_manager.get_state(user_id, "profile_creation")
        if not state:
            self._bot.send_message(chat_id, "Сессия истекла. Начните заново командой /profile")
            return

        collected_data = state["collected_data"]
        collected_data["user_id"] = user_id

        try:
            profile, result_message = validate_profile_data(collected_data)
            self._storage.save_profile(profile)
            state_manager.clear_state(user_id, "profile_creation")
            self._bot.send_message(chat_id, f"✅ {result_message}")
            logger.info("Profile saved for user %s", user_id)
        except Exception as exc:
            logger.error("Error saving profile: %s", exc)
            self._bot.send_message(chat_id, f"❌ Ошибка при сохранении: {exc}")

    def cancel_profile_creation(self, user_id: str, chat_id: int) -> None:
        """Отменить создание профиля."""
        state_manager.clear_state(user_id, "profile_creation")
        self._bot.send_message(chat_id, "❌ Создание профиля отменено.")


def register_conversation_handlers(bot: TeleBot, storage: StorageRepository) -> ProfileConversation:
    """Зарегистрировать обработчики для создания профиля."""
    manager = ProfileConversation(bot, storage)

    @bot.message_handler(commands=["profile"])
    def profile_command(message: Message) -> None:
        manager.start_profile_creation(message)

    return manager
