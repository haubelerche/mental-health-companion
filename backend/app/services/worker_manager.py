import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from app.services.db.session import get_session_factory
from app.services.letter_ai_worker import run_ai_reply_worker
from app.services.youtube_agent import run_youtube_crawl_agent, CATEGORIES
import random

logger = logging.getLogger(__name__)

class AdminWorker:
    def __init__(self, name: str, interval_min: int, task_func):
        self.name = name
        self.interval_min = interval_min
        self.task_func = task_func
        self.active = False
        self.running = False
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self._task: Optional[asyncio.Task] = None

    def start(self):
        if self.active:
            return
        self.active = True
        self.next_run = datetime.now(timezone.utc)
        self._task = asyncio.create_task(self._loop())
        logger.info(f"Worker {self.name} started with interval {self.interval_min}min")

    def stop(self):
        self.active = False
        if self._task:
            self._task.cancel()
        self.next_run = None
        logger.info(f"Worker {self.name} stopped")

    async def _loop(self):
        while self.active:
            now = datetime.now(timezone.utc)
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
                    self.next_run = datetime.now(timezone.utc) + timedelta(minutes=self.interval_min)
            
            await asyncio.sleep(10) # Check every 10 seconds

    def to_dict(self):
        return {
            "name": self.name,
            "active": self.active,
            "running": self.running,
            "interval_min": self.interval_min,
            "last_run": self.last_run.strftime('%Y-%m-%dT%H:%M:%SZ') if self.last_run else None,
            "next_run": self.next_run.strftime('%Y-%m-%dT%H:%M:%SZ') if self.next_run else None,
            "seconds_until_next": int((self.next_run - datetime.now(timezone.utc)).total_seconds()) if self.next_run else None
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

# --- Manager ---

class WorkerManager:
    def __init__(self):
        self.workers: Dict[str, AdminWorker] = {
            "letter": AdminWorker("Letter Responder", 20, letter_task),
            "resource": AdminWorker("Resource Crawler", 60, resource_task)
        }
        self.logs = []

    def add_log(self, worker_name: str, message: str):
        self.logs.append({
            "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
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

    def update_config(self, name: str, interval_min: int):
        if name in self.workers:
            old_interval = self.workers[name].interval_min
            self.workers[name].interval_min = interval_min
            # If running, restart to apply new interval correctly
            if self.workers[name].active:
                self.workers[name].stop()
                self.workers[name].start()
            self.add_log(name, f"Thay đổi tần suất: {old_interval}m -> {interval_min}m")
            return True
        return False

worker_manager = WorkerManager()
