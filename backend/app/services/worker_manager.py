import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from app.services.db.session import get_session_factory
from app.services.letter_ai_worker import run_ai_reply_worker
from app.services.youtube_agent import run_youtube_crawl_agent, CATEGORIES
from app.services.db.models import User, SyncOutbox
from app.services.utils import get_now
from sqlalchemy import select
import random

logger = logging.getLogger(__name__)

class AdminWorker:
    def __init__(self, name: str, interval_min: Optional[int], task_func, daily_time: Optional[str] = None):
        self.name = name
        self.interval_min = interval_min
        self.daily_time = daily_time # e.g. "08:00"
        self.task_func = task_func
        self.active = False
        self.running = False
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self._task: Optional[asyncio.Task] = None

    def _calculate_next_run(self):
        now = get_now()
        if self.daily_time:
            try:
                hour, minute = map(int, self.daily_time.split(':'))
                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
                return next_run
            except:
                return now + timedelta(hours=24) # Fallback
        elif self.interval_min:
            return now + timedelta(minutes=self.interval_min)
        return None

    def start(self):
        if self.active:
            return
        self.active = True
        self.next_run = self._calculate_next_run()
        self._task = asyncio.create_task(self._loop())
        logger.info(f"Worker {self.name} started (Daily: {self.daily_time}, Interval: {self.interval_min}m)")

    def stop(self):
        self.active = False
        if self._task:
            self._task.cancel()
        self.next_run = None
        logger.info(f"Worker {self.name} stopped")

    async def _loop(self):
        while self.active:
            now = get_now()
            if self.next_run and now >= self.next_run:
                self.running = True
                try:
                    logger.info(f"Worker {self.name} executing task...")
                    await self.task_func()
                    self.last_run = now
                except Exception as e:
                    logger.error(f"Worker {self.name} error: {e}")
                finally:
                    self.running = False
                    self.next_run = self._calculate_next_run()
            
            await asyncio.sleep(10) # Check every 10 seconds

    def to_dict(self):
        return {
            "name": self.name,
            "active": self.active,
            "running": self.running,
            "interval_min": self.interval_min,
            "daily_time": self.daily_time,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "seconds_until_next": int((self.next_run - get_now()).total_seconds()) if self.next_run else None
        }

# --- Task Functions ---

async def letter_task():
    db = get_session_factory()()
    try:
        # Change threshold to 0 for immediate testing
        count = await run_ai_reply_worker(db, hours_threshold=0)
        worker_manager.add_log("letter", f"Hoàn thành: Đã trả lời {count} lá thư.")
    except Exception as e:
        worker_manager.add_log("letter", f"Lỗi: {str(e)}")
    finally:
        db.close()

async def resource_task():
    db = get_session_factory()()
    try:
        category = random.choice(CATEGORIES)
        async for _ in run_youtube_crawl_agent(category, limit=3, db=db):
            pass
        worker_manager.add_log("resource", f"Hoàn thành: Đã cập nhật tài nguyên mục {category}.")
    except Exception as e:
        worker_manager.add_log("resource", f"Lỗi: {str(e)}")
    finally:
        db.close()

async def notification_morning_task():
    await _send_templated_notification(NOTIFICATION_TEMPLATES[0])

async def notification_reminder_task():
    await _send_templated_notification(NOTIFICATION_TEMPLATES[1])

async def notification_letters_task():
    await _send_templated_notification(NOTIFICATION_TEMPLATES[2])

async def _send_templated_notification(tpl: dict):
    db = get_session_factory()()
    try:
        users = db.scalars(select(User).where(User.is_active == True)).all()
        outbox_entries = []
        for user in users:
            outbox_entries.append(
                SyncOutbox(
                    user_id=user.user_id,
                    event_type="admin.broadcast",
                    payload={
                        "title": tpl["title"],
                        "message": tpl["body"],
                        "category": tpl["category"]
                    },
                    status="pending"
                )
            )
        db.add_all(outbox_entries)
        db.commit()
        worker_manager.add_log(f"notif_{tpl['category']}", f"Hoàn thành: Đã gửi thông báo '{tpl['title']}' đến {len(outbox_entries)} người.")
    except Exception as e:
        worker_manager.add_log(f"notif_{tpl['category']}", f"Lỗi: {str(e)}")
    finally:
        db.close()

# --- Templates ---

NOTIFICATION_TEMPLATES = [
    {
        "title": "Chào buổi sáng",
        "body": "Chào buổi sáng bạn nhé! Đừng quên dành 5 phút check-in tâm trạng hôm nay cùng Serene nhé. 🌿",
        "category": "morning"
    },
    {
        "title": "Nhắc nhở tự chăm sóc",
        "body": "Bạn ơi, hôm nay bạn đã dành thời gian cho bản thân chưa? Một chút nhạc thư giãn có thể giúp bạn cảm thấy tốt hơn đấy. ❤️",
        "category": "reminder"
    },
    {
        "title": "Gửi trao tâm tình",
        "body": "Hôm nay có rất nhiều lá thư ẩn danh đang đợi được hồi đáp. Hãy ghé qua hòm thư để chia sẻ sự thấu cảm cùng mọi người nhé! 💌",
        "category": "letters"
    }
]

# --- Manager ---

class WorkerManager:
    def __init__(self):
        self.workers: Dict[str, AdminWorker] = {
            "letter": AdminWorker("Letter Responder", 20, letter_task),
            "resource": AdminWorker("Resource Crawler", 60, resource_task),
            "notif_morning": AdminWorker("Chào buổi sáng", None, notification_morning_task, daily_time="07:00"),
            "notif_reminder": AdminWorker("Nhắc nhở tự chăm sóc", None, notification_reminder_task, daily_time="14:00"),
            "notif_letters": AdminWorker("Gửi trao tâm tình", None, notification_letters_task, daily_time="20:00")
        }
        self.logs = []

    def add_log(self, worker_name: str, message: str):
        self.logs.append({
            "timestamp": get_now().isoformat(),
            "worker": worker_name,
            "message": message
        })
        # Keep only last 50 logs
        if len(self.logs) > 50:
            self.logs = self.logs[-50:]

    def get_status(self):
        return {
            "workers": {k: w.to_dict() for k, w in self.workers.items()},
            "logs": self.logs[::-1] # Newest first
        }

    def toggle(self, name: str, active: bool):
        if name in self.workers:
            if active:
                self.workers[name].start()
            else:
                self.workers[name].stop()
            self.add_log(name, f"Worker {'bắt đầu' if active else 'dừng'}")
            return True
        return False

    def update_config(self, name: str, interval_min: Optional[int] = None, daily_time: Optional[str] = None):
        if name in self.workers:
            old_interval = self.workers[name].interval_min
            old_time = self.workers[name].daily_time
            
            if interval_min is not None:
                self.workers[name].interval_min = interval_min
            if daily_time is not None:
                self.workers[name].daily_time = daily_time
                
            # If running, restart to apply new config
            if self.workers[name].active:
                self.workers[name].stop()
                self.workers[name].start()
                
            msg = f"Cập nhật config: "
            if interval_min: msg += f"Interval {old_interval}m -> {interval_min}m. "
            if daily_time: msg += f"Time {old_time} -> {daily_time}. "
            self.add_log(name, msg)
            return True
        return False

worker_manager = WorkerManager()
