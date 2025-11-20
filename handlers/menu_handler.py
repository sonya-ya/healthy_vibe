from __future__ import annotations

import logging
from typing import Optional

from telebot import TeleBot
from telebot.types import KeyboardButton, ReplyKeyboardMarkup

from repositories.storage import StorageRepository

logger = logging.getLogger(__name__)


class MenuHandler:
    """Обработчик главного меню и навигации."""

    def __init__(self, bot: TeleBot, storage: StorageRepository, workout_service=None, reminder_service=None):
        self._bot = bot
        self._storage = storage
        self._workout_service = workout_service
        self._reminder_service = reminder_service
        self._main_menu = self._create_main_menu()
        self._menu_for_new_users = self._create_menu_for_new_users()

    def _create_main_menu(self) -> ReplyKeyboardMarkup:
        """Создать главное меню для пользователей с профилем."""
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

        # Первая строка
        markup.add(
            KeyboardButton("📋 Мои тренировки"),
            KeyboardButton("➕ Создать")
        )

        # Вторая строка
        markup.add(
            KeyboardButton("⚙️ Настройки")
        )

        # Третья строка
        markup.add(
            KeyboardButton("📅 План"),
            KeyboardButton("🔔 Напоминания")
        )

        # Четвертая строка
        markup.add(
            KeyboardButton("💪 Тренировка"),
            KeyboardButton("❓ Помощь")
        )

        return markup

    def _create_menu_for_new_users(self) -> ReplyKeyboardMarkup:
        """Создать меню для пользователей без профиля."""
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(KeyboardButton("👤 Создать профиль"))
        markup.add(KeyboardButton("❓ Помощь"))
        return markup

    def get_menu(self, user_id: str) -> ReplyKeyboardMarkup:
        """Получить меню для пользователя (зависит от наличия профиля)."""
        profile = self._storage.get_profile(user_id)
        if profile:
            return self._main_menu
        return self._menu_for_new_users

    def show_main_menu(self, chat_id: int, text: str = "Главное меню:", user_id: Optional[str] = None) -> None:
        """Показать главное меню."""
        if user_id:
            markup = self.get_menu(user_id)
        else:
            markup = self._main_menu
        self._bot.send_message(chat_id, text, reply_markup=markup)

    def create_submenu(self, buttons: list[str]) -> ReplyKeyboardMarkup:
        """Создать подменю с кнопками и кнопкой 'Главное меню'."""
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        for button_text in buttons:
            markup.add(KeyboardButton(button_text))
        markup.add(KeyboardButton("🏠 Главное меню"))
        return markup

    def register_menu_handlers(
        self,
        workout_management_handler=None,
        workout_creation_manager=None,
    ) -> None:
        """Зарегистрировать обработчики кнопок меню."""
        
        @self._bot.message_handler(func=lambda m: m.text == "📋 Мои тренировки")
        def my_workouts_handler(message) -> None:
            user_id = str(message.from_user.id)
            logger.info("Menu button pressed: 'Мои тренировки', user_id=%s", user_id)
            if workout_management_handler:
                workout_management_handler.show_my_workouts_menu(message)
            else:
                logger.warning("WorkoutManagementHandler not available for user %s", user_id)
                self._bot.send_message(
                    message.chat.id,
                    "Функция 'Мои тренировки' пока не реализована",
                    reply_markup=self.get_menu(user_id)
                )

        @self._bot.message_handler(func=lambda m: m.text == "➕ Создать")
        def create_handler(message) -> None:
            user_id = str(message.from_user.id)
            markup = self.create_submenu([
                "💪 Создать тренировку",
                "📋 Создать план из тренировок",
            ])
            self._bot.send_message(message.chat.id, "Что вы хотите создать?", reply_markup=markup)

        @self._bot.message_handler(func=lambda m: m.text == "💪 Создать тренировку")
        def create_workout_handler(message) -> None:
            if workout_creation_manager:
                workout_creation_manager.start_workout_creation(message)
            else:
                user_id = str(message.from_user.id)
                self._bot.send_message(
                    message.chat.id,
                    "Используйте команду /createworkout для создания тренировки",
                    reply_markup=self.get_menu(user_id)
                )

        @self._bot.message_handler(func=lambda m: m.text == "📋 Создать план из тренировок" or m.text == "➕ Создать план")
        def create_plan_handler(message) -> None:
            """Создать план тренировок через LLM."""
            user_id = str(message.from_user.id)
            logger.info("Plan creation requested: user_id=%s", user_id)
            
            # Проверяем наличие профиля
            profile = self._storage.get_profile(user_id)
            if not profile:
                logger.warning("Profile not found for plan creation: user_id=%s", user_id)
                self._bot.send_message(
                    message.chat.id,
                    "Сначала заполните профиль командой /profile",
                    reply_markup=self.get_menu(user_id)
                )
                return
            
            # Отправляем сообщение о том, что создаем план
            self._bot.send_chat_action(message.chat.id, "typing")
            self._bot.send_message(
                message.chat.id,
                "🤖 Создаю персональный план тренировок с помощью ИИ...\n\nЭто может занять несколько секунд."
            )
            
            try:
                from services.openai_service import openai_service
                from services.plan_llm import create_workout_plan_with_llm
                
                # Создаем план через LLM
                plan = create_workout_plan_with_llm(user_id, profile, self._storage, openai_service)
                
                if plan:
                    name_text = f" '{plan.name}'" if plan.name else ""
                    self._bot.send_message(
                        message.chat.id,
                        f"✅ План тренировок{name_text} успешно создан!\n\n"
                        f"План содержит {len(plan.entries)} тренировок на неделю.\n\n"
                        f"План доступен в '📋 Мои тренировки' → '📊 Активные планы'.",
                        reply_markup=self.get_menu(user_id)
                    )
                    logger.info("Plan created successfully via LLM: user_id=%s, plan_id=%s, entries_count=%d",
                               user_id, plan.plan_id, len(plan.entries))
                else:
                    raise ValueError("Не удалось создать план")
                    
            except Exception as e:
                logger.exception("Error creating plan via LLM: user_id=%s, error=%s", user_id, str(e))
                self._bot.send_message(
                    message.chat.id,
                    f"❌ Произошла ошибка при создании плана: {str(e)}\n\nПопробуйте позже.",
                    reply_markup=self.get_menu(user_id)
                )


        @self._bot.message_handler(func=lambda m: m.text == "⚙️ Настройки")
        def settings_handler_menu(message) -> None:
            user_id = str(message.from_user.id)
            markup = self.create_submenu([
                "👤 Мой профиль",
                "🔕 Уведомления",
                "ℹ️ О боте",
            ])
            self._bot.send_message(message.chat.id, "⚙️ Настройки\n\nВыберите действие:", reply_markup=markup)

        @self._bot.message_handler(func=lambda m: m.text == "👤 Мой профиль")
        def my_profile_handler(message) -> None:
            user_id = str(message.from_user.id)
            profile = self._storage.get_profile(user_id)
            if profile:
                from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
                from utils.constants import GENDER_DISPLAY, GOAL_DISPLAY, EXPERIENCE_DISPLAY, LOCATION_DISPLAY, WORKOUT_TIME_DISPLAY
                text_lines = ["👤 Ваш профиль:\n"]
                text_lines.append(f"Возраст: {profile.age} лет")
                text_lines.append(f"Пол: {GENDER_DISPLAY.get(profile.gender, profile.gender)}")
                text_lines.append(f"Вес: {profile.weight} кг")
                text_lines.append(f"Цель: {GOAL_DISPLAY.get(profile.goal, profile.goal)}")
                text_lines.append(f"Опыт: {EXPERIENCE_DISPLAY.get(profile.experience, profile.experience)}")
                text_lines.append(f"Место тренировок: {LOCATION_DISPLAY.get(profile.preferred_location, profile.preferred_location)}")
                text_lines.append(f"Длительность: {WORKOUT_TIME_DISPLAY.get(profile.workout_time, profile.workout_time)}")
                
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("Редактировать", callback_data="profile_edit"))
                self._bot.send_message(message.chat.id, "\n".join(text_lines), reply_markup=markup)
            else:
                self._bot.send_message(
                    message.chat.id,
                    "У вас нет профиля. Используйте команду /profile для создания профиля.",
                    reply_markup=self.get_menu(user_id)
                )

        @self._bot.message_handler(func=lambda m: m.text == "📅 План")
        def plan_handler_menu(message) -> None:
            user_id = str(message.from_user.id)
            markup = self.create_submenu([
                "➕ Создать план",
            ])
            self._bot.send_message(message.chat.id, "📅 План тренировок\n\nВыберите действие:", reply_markup=markup)

        @self._bot.message_handler(func=lambda m: m.text == "🔔 Напоминания")
        def reminders_handler_menu(message) -> None:
            user_id = str(message.from_user.id)
            markup = self.create_submenu([
                "📋 Мои напоминания",
                "➕ Добавить напоминание",
            ])
            self._bot.send_message(message.chat.id, "🔔 Напоминания\n\nВыберите действие:", reply_markup=markup)

        @self._bot.message_handler(func=lambda m: m.text == "📋 Мои напоминания")
        def my_reminders_handler(message) -> None:
            user_id = str(message.from_user.id)
            if self._reminder_service:
                reminders = list(self._reminder_service.list_reminders(user_id))
                if not reminders:
                    self._bot.send_message(
                        message.chat.id,
                        "Напоминания пока не настроены.\n\nИспользуйте '➕ Добавить напоминание' для создания.",
                        reply_markup=self.get_menu(user_id)
                    )
                    return
                lines = ["🔔 Ваши напоминания:\n"]
                for r in reminders:
                    lines.append(f"• {r.type} в {r.time.strftime('%H:%M')} ({r.frequency})")
                self._bot.send_message(message.chat.id, "\n".join(lines), reply_markup=self.get_menu(user_id))
            else:
                self._bot.send_message(message.chat.id, "Используйте команду /reminders для просмотра напоминаний", reply_markup=self.get_menu(user_id))

        @self._bot.message_handler(func=lambda m: m.text == "➕ Добавить напоминание")
        def add_reminder_handler(message) -> None:
            user_id = str(message.from_user.id)
            self._bot.send_message(
                message.chat.id,
                "Используйте команду /setreminder для добавления напоминания.\n\nФормат: /setreminder <type> <HH:MM> <daily|weekly>\nПример: /setreminder training 09:00 daily",
                reply_markup=self.get_menu(user_id)
            )

        @self._bot.message_handler(func=lambda m: m.text == "💪 Тренировка")
        def workout_handler_menu(message) -> None:
            user_id = str(message.from_user.id)
            markup = self.create_submenu([
                "💪 Тренировка на сегодня",
                "📋 Выбрать тренировку",
                "⚡ Быстрая тренировка",
            ])
            self._bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

        @self._bot.message_handler(func=lambda m: m.text == "💪 Тренировка на сегодня")
        def workout_today_handler(message) -> None:
            if self._workout_service:
                user_id = str(message.from_user.id)
                profile = self._storage.get_profile(user_id)
                if not profile:
                    self._bot.send_message(message.chat.id, "Сначала заполните профиль командой /profile", reply_markup=self.get_menu(user_id))
                    return
                
                templates = self._workout_service.get_available_templates(profile, "legs")
                if templates:
                    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
                    markup = InlineKeyboardMarkup(row_width=1)
                    for template in templates[:10]:
                        markup.add(
                            InlineKeyboardButton(
                                f"{template.name}",
                                callback_data=f"template_{template.template_id}",
                            )
                        )
                    markup.add(InlineKeyboardButton("Случайная тренировка", callback_data="template_random"))
                    self._bot.send_message(
                        message.chat.id,
                        "Выберите темплейт тренировки или случайную:",
                        reply_markup=markup,
                    )
                else:
                    from handlers.commands import _send_workout
                    workout_entry = self._workout_service.generate_daily_workout(profile, "legs")
                    self._workout_service.save_standalone_workout(user_id, workout_entry)
                    _send_workout(self._bot, message.chat.id, workout_entry)
            else:
                user_id = str(message.from_user.id)
                self._bot.send_message(message.chat.id, "Используйте команду /workout для тренировки на сегодня", reply_markup=self.get_menu(user_id))

        @self._bot.message_handler(func=lambda m: m.text == "📋 Выбрать тренировку")
        def select_workout_handler(message) -> None:
            """Показать список тренировок для выбора и выполнения."""
            logger.info("Select workout handler called for user %s", message.from_user.id)
            user_id = str(message.from_user.id)
            try:
                from services.workout_management import WorkoutManagementService
                management_service = WorkoutManagementService(self._storage)
                workouts_by_day = management_service.get_all_workouts(user_id)
                logger.info("Found %d workout days for user %s", len(workouts_by_day), user_id)
            except Exception as e:
                logger.error("Error getting workouts: %s", e, exc_info=True)
                self._bot.send_message(
                    message.chat.id,
                    "Ошибка при получении тренировок. Попробуйте позже.",
                    reply_markup=self.get_menu(user_id)
                )
                return
            
            if not workouts_by_day:
                self._bot.send_message(
                    message.chat.id,
                    "У вас пока нет сохраненных тренировок.\n\nИспользуйте '➕ Создать' для создания тренировки.",
                    reply_markup=self.get_menu(user_id)
                )
                return
            
            from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
            from utils.constants import DAY_NAMES
            from utils.state_manager import state_manager
            import time as time_module
            
            all_workouts_flat = []
            for day, workouts in sorted(workouts_by_day.items(), key=lambda x: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"].index(x[0])):
                all_workouts_flat.extend(workouts)
            
            state_manager.set_state(
                user_id,
                "workout_selection",
                {
                    "workouts": [w.entry_id for w in all_workouts_flat],
                    "timestamp": time_module.time(),
                },
            )
            
            text_lines = ["📋 Выберите тренировку для выполнения:\n"]
            markup = InlineKeyboardMarkup(row_width=1)
            
            workout_idx = 0
            for day, workouts in sorted(workouts_by_day.items(), key=lambda x: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"].index(x[0])):
                day_name = DAY_NAMES.get(day, day)
                for workout in workouts:
                    name = workout.workout_name or "Тренировка"
                    exercise_count = len(workout.exercises)
                    callback_data = f"sel_wk_{workout_idx}"
                    
                    button_text = f"💪 {name} ({day_name})"
                    if len(button_text) > 60:
                        button_text = button_text[:57] + "..."
                    
                    markup.add(InlineKeyboardButton(button_text, callback_data=callback_data))
                    text_lines.append(f"📅 {day_name}: {name} ({exercise_count} упражнений)")
                    workout_idx += 1
                    
                    if workout_idx >= 50:
                        break
                
                if workout_idx >= 50:
                    break
            
            text = "\n".join(text_lines[:15])
            if len(text_lines) > 15:
                text += f"\n... и еще {len(text_lines) - 15} тренировок"
            
            markup.add(InlineKeyboardButton("❌ Отменить", callback_data="workout_select_cancel"))
            self._bot.send_message(message.chat.id, text, reply_markup=markup)

        @self._bot.message_handler(func=lambda m: m.text == "⚡ Быстрая тренировка")
        def quick_workout_handler(message) -> None:
            if self._workout_service:
                user_id = str(message.from_user.id)
                profile = self._storage.get_profile(user_id)
                if not profile:
                    self._bot.send_message(message.chat.id, "Сначала заполните профиль командой /profile", reply_markup=self.get_menu(user_id))
                    return
                
                from handlers.commands import _send_workout
                workout_entry = self._workout_service.generate_daily_workout(profile, "legs")
                self._workout_service.save_standalone_workout(user_id, workout_entry)
                _send_workout(self._bot, message.chat.id, workout_entry)
            else:
                user_id = str(message.from_user.id)
                self._bot.send_message(message.chat.id, "Используйте команду /workout для быстрой тренировки", reply_markup=self.get_menu(user_id))

        @self._bot.message_handler(func=lambda m: m.text == "❓ Помощь")
        def help_handler_menu(message) -> None:
            from utils.constants import HELP_MESSAGE
            self._bot.send_message(message.chat.id, HELP_MESSAGE, reply_markup=self.get_menu(str(message.from_user.id)))

        @self._bot.message_handler(func=lambda m: m.text == "🏠 Главное меню")
        def main_menu_handler(message) -> None:
            user_id = str(message.from_user.id)
            self.show_main_menu(message.chat.id, "Главное меню:", user_id)

        @self._bot.message_handler(func=lambda m: m.text == "👤 Создать профиль")
        def create_profile_handler(message) -> None:
            self._bot.send_message(message.chat.id, "Используйте команду /profile для создания профиля.")

