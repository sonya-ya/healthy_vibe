from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Таймаут для очистки состояния (30 минут)
STATE_TIMEOUT = 30 * 60  # 30 минут в секундах


class UserStateManager:
    """Управление состояниями пользователей в памяти с автоматической очисткой."""

    def __init__(self) -> None:
        self._states: Dict[str, Dict[str, Any]] = {}
        self._state_timestamps: Dict[str, Dict[str, float]] = {}
        self._lock = threading.Lock()

    def get_state(self, user_id: str, state_type: str) -> Optional[Dict[str, Any]]:
        """Получить состояние пользователя."""
        key = f"{user_id}:{state_type}"
        with self._lock:
            # Проверка на истечение времени
            if user_id in self._state_timestamps and state_type in self._state_timestamps[user_id]:
                timestamp = self._state_timestamps[user_id][state_type]
                if time.time() - timestamp > STATE_TIMEOUT:
                    self._clear_state(user_id, state_type)
                    return None
            return self._states.get(key)

    def set_state(self, user_id: str, state_type: str, state: Dict[str, Any]) -> None:
        """Установить состояние пользователя."""
        key = f"{user_id}:{state_type}"
        with self._lock:
            self._states[key] = state
            if user_id not in self._state_timestamps:
                self._state_timestamps[user_id] = {}
            self._state_timestamps[user_id][state_type] = time.time()
            logger.debug("State set for user %s, type %s", user_id, state_type)

    def update_state(self, user_id: str, state_type: str, updates: Dict[str, Any]) -> None:
        """Обновить часть состояния пользователя."""
        current_state = self.get_state(user_id, state_type) or {}
        current_state.update(updates)
        self.set_state(user_id, state_type, current_state)

    def clear_state(self, user_id: str, state_type: str) -> None:
        """Очистить состояние пользователя."""
        self._clear_state(user_id, state_type)

    def _clear_state(self, user_id: str, state_type: str) -> None:
        """Внутренний метод очистки состояния."""
        key = f"{user_id}:{state_type}"
        with self._lock:
            self._states.pop(key, None)
            if user_id in self._state_timestamps:
                self._state_timestamps[user_id].pop(state_type, None)
            logger.debug("State cleared for user %s, type %s", user_id, state_type)

    def has_state(self, user_id: str, state_type: str) -> bool:
        """Проверить наличие состояния."""
        return self.get_state(user_id, state_type) is not None

    def clear_all_states(self, user_id: str) -> None:
        """Очистить все состояния пользователя."""
        with self._lock:
            keys_to_remove = [key for key in self._states.keys() if key.startswith(f"{user_id}:")]
            for key in keys_to_remove:
                self._states.pop(key, None)
            self._state_timestamps.pop(user_id, None)
            logger.debug("All states cleared for user %s", user_id)


# Глобальный экземпляр менеджера состояний
state_manager = UserStateManager()

