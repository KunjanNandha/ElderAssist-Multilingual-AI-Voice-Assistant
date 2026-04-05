"""
reminder_scheduler.py
Medicine reminder system that stores reminders and checks them at runtime.
Uses APScheduler for background scheduling.

Usage:
    from models.reminder_scheduler import ReminderScheduler
    scheduler = ReminderScheduler(tts_engine)
    scheduler.add_reminder("Metformin", "08:00", frequency=2, language="hi")
    scheduler.start()
"""

import json
import os
import uuid
import logging
from datetime import datetime, time as dtime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Try APScheduler
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
    logger.warning("APScheduler not installed. Run: pip install apscheduler")


# Reminder messages in all supported languages
REMINDER_MESSAGES = {
    "en": "Medicine reminder! Time to take your {medicine}. Please do not skip your medication.",
    "hi": "दवाई लेने का समय हो गया है! कृपया अभी {medicine} लें। दवाई न भूलें।",
    "mr": "औषध घेण्याची वेळ झाली! कृपया आत्ता {medicine} घ्या. औषध विसरू नका.",
    "gu": "દવા લેવાનો સમય થઈ ગયો છે! કૃપા કરીને હવે {medicine} લો. દવા ન ભૂલો.",
    "ta": "மருந்து உட்கொள்ளும் நேரம்! இப்போது {medicine} எடுத்துக்கொள்ளுங்கள். மருந்தை மறவாதீர்கள்.",
    "te": "మందు తీసుకునే సమయం! ఇప్పుడు {medicine} తీసుకోండి. మందు మర్చిపోవద్దు.",
    "bn": "ওষুধ খাওয়ার সময় হয়েছে! এখন {medicine} খান। ওষুধ ভুলবেন না।",
}


class Reminder:
    """A single medicine reminder."""

    def __init__(
        self,
        medicine_name: str,
        times: List[str],          # ["08:00", "14:00", "20:00"]
        language: str = "en",
        notes: str = "",
        active: bool = True
    ):
        self.id            = str(uuid.uuid4())[:8]
        self.medicine_name = medicine_name
        self.times         = times
        self.language      = language
        self.notes         = notes
        self.active        = active
        self.created_at    = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "id":            self.id,
            "medicine_name": self.medicine_name,
            "times":         self.times,
            "language":      self.language,
            "notes":         self.notes,
            "active":        self.active,
            "created_at":    self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Reminder":
        r = cls(
            medicine_name=d["medicine_name"],
            times=d["times"],
            language=d.get("language", "en"),
            notes=d.get("notes", ""),
            active=d.get("active", True),
        )
        r.id         = d.get("id", r.id)
        r.created_at = d.get("created_at", r.created_at)
        return r

    def get_message(self) -> str:
        template = REMINDER_MESSAGES.get(
            self.language,
            REMINDER_MESSAGES["en"]
        )
        msg = template.format(medicine=self.medicine_name)
        if self.notes:
            msg += f" ({self.notes})"
        return msg


class ReminderScheduler:
    """
    Background scheduler for medicine reminders.
    Stores reminders to JSON and fires TTS alerts at scheduled times.
    """

    def __init__(self, tts_engine=None, storage_path: str = "data/reminders.json"):
        self.tts_engine   = tts_engine
        self.storage_path = storage_path
        self.reminders: Dict[str, Reminder] = {}
        self._scheduler   = None
        self._load()

        if SCHEDULER_AVAILABLE:
            self._scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

    # ── CRUD ────────────────────────────────────────────────

    def add_reminder(
        self,
        medicine_name: str,
        times: List[str],
        language: str = "en",
        notes: str = "",
        frequency: int = None
    ) -> Reminder:
        """
        Add a new medicine reminder.

        Args:
            medicine_name: Name of the medicine (e.g., "Metformin 500mg")
            times:         List of times in "HH:MM" format (e.g., ["08:00", "20:00"])
            language:      Response language code
            notes:         Optional notes (e.g., "Take with food")
            frequency:     Shortcut — if given, creates equally spaced times per day
                           e.g., frequency=3 → ["08:00", "14:00", "20:00"]

        Returns:
            The created Reminder object
        """
        if frequency and not times:
            times = self._generate_times(frequency)

        reminder = Reminder(
            medicine_name=medicine_name,
            times=times,
            language=language,
            notes=notes
        )
        self.reminders[reminder.id] = reminder
        self._save()

        # Schedule in APScheduler
        if self._scheduler and self._scheduler.running:
            self._schedule_reminder(reminder)

        logger.info(f"Reminder added: {medicine_name} at {times}")
        return reminder

    def remove_reminder(self, reminder_id: str) -> bool:
        """Remove a reminder by ID."""
        if reminder_id not in self.reminders:
            return False

        # Remove from scheduler
        if self._scheduler:
            for t in self.reminders[reminder_id].times:
                job_id = f"{reminder_id}_{t}"
                try:
                    self._scheduler.remove_job(job_id)
                except Exception:
                    pass

        del self.reminders[reminder_id]
        self._save()
        return True

    def toggle_reminder(self, reminder_id: str) -> Optional[bool]:
        """Toggle a reminder on/off. Returns new active state."""
        if reminder_id not in self.reminders:
            return None
        r = self.reminders[reminder_id]
        r.active = not r.active
        self._save()
        return r.active

    def get_all(self) -> List[dict]:
        """Return all reminders as list of dicts."""
        return [r.to_dict() for r in self.reminders.values()]

    def get_active(self) -> List[Reminder]:
        """Return only active reminders."""
        return [r for r in self.reminders.values() if r.active]

    # ── SCHEDULER ──────────────────────────────────────────

    def start(self):
        """Start the background scheduler."""
        if not SCHEDULER_AVAILABLE or not self._scheduler:
            logger.warning("APScheduler not available; reminders won't fire automatically")
            return

        if not self._scheduler.running:
            self._scheduler.start()
            # Schedule all existing active reminders
            for reminder in self.get_active():
                self._schedule_reminder(reminder)
            logger.info("Reminder scheduler started")

    def stop(self):
        """Stop the background scheduler."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown()
            logger.info("Reminder scheduler stopped")

    def _schedule_reminder(self, reminder: Reminder):
        """Add APScheduler jobs for a reminder."""
        if not self._scheduler:
            return

        for time_str in reminder.times:
            try:
                h, m = map(int, time_str.split(":"))
                job_id = f"{reminder.id}_{time_str}"

                self._scheduler.add_job(
                    func=self._fire_reminder,
                    trigger=CronTrigger(hour=h, minute=m),
                    id=job_id,
                    args=[reminder.id],
                    replace_existing=True
                )
            except Exception as e:
                logger.error(f"Failed to schedule {reminder.medicine_name} at {time_str}: {e}")

    def _fire_reminder(self, reminder_id: str):
        """Called by APScheduler at the scheduled time."""
        if reminder_id not in self.reminders:
            return

        reminder = self.reminders[reminder_id]
        if not reminder.active:
            return

        message = reminder.get_message()
        logger.info(f"REMINDER FIRED: {message}")

        # Play TTS if engine available
        if self.tts_engine:
            try:
                audio_path = self.tts_engine.synthesize(
                    message, reminder.language, slow=True
                )
                if audio_path:
                    # In production, push this to frontend via SSE/WebSocket
                    logger.info(f"TTS audio generated: {audio_path}")
            except Exception as e:
                logger.error(f"TTS error for reminder: {e}")

    # ── STORAGE ─────────────────────────────────────────────

    def _save(self):
        """Persist reminders to JSON file."""
        try:
            os.makedirs(os.path.dirname(self.storage_path) or ".", exist_ok=True)
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(
                    [r.to_dict() for r in self.reminders.values()],
                    f, ensure_ascii=False, indent=2
                )
        except Exception as e:
            logger.error(f"Failed to save reminders: {e}")

    def _load(self):
        """Load reminders from JSON file."""
        if not os.path.exists(self.storage_path):
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                r = Reminder.from_dict(item)
                self.reminders[r.id] = r
            logger.info(f"Loaded {len(self.reminders)} reminders from storage")
        except Exception as e:
            logger.error(f"Failed to load reminders: {e}")

    # ── HELPERS ─────────────────────────────────────────────

    @staticmethod
    def _generate_times(frequency: int) -> List[str]:
        """
        Generate equally spaced times across the day for a given frequency.
        frequency=1 → ["09:00"]
        frequency=2 → ["08:00", "20:00"]
        frequency=3 → ["08:00", "14:00", "20:00"]
        frequency=4 → ["08:00", "12:00", "16:00", "20:00"]
        """
        start_hour = 8
        end_hour   = 20
        if frequency == 1:
            return ["09:00"]
        span = end_hour - start_hour
        step = span / (frequency - 1) if frequency > 1 else span
        return [
            f"{int(start_hour + i * step):02d}:00"
            for i in range(frequency)
        ]

    def check_due_now(self) -> List[str]:
        """
        Manually check which reminders are due right now (within ±1 minute).
        Useful when APScheduler is not available.
        """
        now = datetime.now()
        current = f"{now.hour:02d}:{now.minute:02d}"
        due = []
        for reminder in self.get_active():
            for t in reminder.times:
                if t == current:
                    due.append(reminder.get_message())
        return due
