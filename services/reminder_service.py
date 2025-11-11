from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from typing import Callable, Dict, Iterable, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config import settings
from repositories.models import ReminderConfig
from repositories.storage import StorageRepository

logger = logging.getLogger(__name__)


class ReminderService:
    """Schedules and manages reminders for users."""

    def __init__(
        self,
        storage: StorageRepository,
        notifier: Callable[[str, str], None],
    ) -> None:
        self._storage = storage
        self._notifier = notifier
        self._scheduler = BackgroundScheduler(timezone=settings.timezone)
        self._scheduler.start()
        self._jobs: Dict[str, str] = {}

    def shutdown(self) -> None:
        self._scheduler.shutdown(wait=False)

    def _job_id(self, reminder: ReminderConfig) -> str:
        return f"{reminder.user_id}:{reminder.reminder_id}"

    def schedule_reminder(self, reminder: ReminderConfig) -> None:
        job_id = self._job_id(reminder)
        self._storage.save_reminder(reminder)
        self._remove_job(job_id)
        trigger = self._build_trigger(reminder)
        self._scheduler.add_job(
            func=self._notifier,
            trigger=trigger,
            args=(reminder.user_id, reminder.message),
            id=job_id,
            replace_existing=True,
        )
        self._jobs[job_id] = reminder.message
        logger.info("Reminder scheduled: %s", job_id)

    def cancel_reminder(self, user_id: str, reminder_id: str) -> None:
        job_id = f"{user_id}:{reminder_id}"
        self._remove_job(job_id)
        self._storage.delete_reminder(user_id, reminder_id)

    def list_reminders(self, user_id: str) -> Iterable[ReminderConfig]:
        return self._storage.list_reminders(user_id)

    def _build_trigger(self, reminder: ReminderConfig) -> CronTrigger:
        reminder_time: time = reminder.time
        if reminder.frequency == "daily":
            return CronTrigger(hour=reminder_time.hour, minute=reminder_time.minute)
        if reminder.frequency == "weekly":
            return CronTrigger(
                day_of_week="mon",
                hour=reminder_time.hour,
                minute=reminder_time.minute,
            )
        raise ValueError(f"Unsupported frequency: {reminder.frequency}")

    def _remove_job(self, job_id: str) -> None:
        job = self._scheduler.get_job(job_id)
        if job:
            job.remove()
            self._jobs.pop(job_id, None)

    def schedule_one_off(self, user_id: str, message: str, delay_minutes: int = 5) -> None:
        run_time = datetime.now().astimezone() + timedelta(minutes=delay_minutes)
        self._scheduler.add_job(
            func=self._notifier,
            trigger="date",
            run_date=run_time,
            args=(user_id, message),
        )
