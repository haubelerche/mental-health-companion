import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from app.services.db.session import get_session_factory
from app.services.letter_ai_worker import run_ai_reply_worker
from app.services.youtube_agent import run_youtube_crawl_agent, CATEGORIES
from app.services.utils import get_now
from sqlalchemy import select, insert
import random
import uuid
from app.services.db.models import User, SyncOutbox, AutomationLog

logger = logging.getLogger(__name__)

class AdminWorker:
    def __init__(self, name: str, interval_min: Optional[int], task_func, daily_time: Optional[str] = None, trigger_id: str = None, config: dict = None, last_run: Optional[datetime] = None):
        self.name = name
        self.interval_min = interval_min
        self.daily_time = daily_time 
        self.task_func = task_func
        self.trigger_id = trigger_id # DB Reference
        self.config = config or {}
        self.active = False
        self.running = False
        self.last_run = last_run
        self.next_run: Optional[datetime] = None
        self._task: Optional[asyncio.Task] = None

    def _calculate_next_run(self):
        now = get_now().replace(tzinfo=None)
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
            now = get_now().replace(tzinfo=None)
            if self.next_run and now >= self.next_run:
                self.running = True
                try:
                    logger.info(f"Worker {self.name} executing task...")
                    if self.config:
                        await self.task_func(config=self.config, trigger_id=self.trigger_id)
                    else:
                        await self.task_func()
                    self.last_run = now
                    # Update last_run_at in DB
                    if self.trigger_id:
                        db = get_session_factory()()
                        try:
                            from app.services.db.models import AutomationTrigger
                            db.query(AutomationTrigger).filter(AutomationTrigger.trigger_id == self.trigger_id).update({"last_run_at": now})
                            db.commit()
                        finally:
                            db.close()
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
            "seconds_until_next": int((self.next_run - get_now().replace(tzinfo=None)).total_seconds()) if self.next_run else None
        }

# --- Task Functions ---

async def notification_morning_task(config=None, trigger_id=None):
    idx = config.get("template_index", 0) if config else 0
    await _send_templated_notification(NOTIFICATION_TEMPLATES[idx], trigger_id=trigger_id, config=config)

async def notification_reminder_task(config=None, trigger_id=None):
    idx = config.get("template_index", 1) if config else 1
    await _send_templated_notification(NOTIFICATION_TEMPLATES[idx], trigger_id=trigger_id, config=config)

async def notification_letters_task(config=None, trigger_id=None):
    idx = config.get("template_index", 2) if config else 2
    await _send_templated_notification(NOTIFICATION_TEMPLATES[idx], trigger_id=trigger_id, config=config)

async def letter_task(config=None, trigger_id=None):
    db = get_session_factory()()
    try:
        # We might want to update run_ai_reply_worker to return list of IDs/content
        # For now, let's just enhance the log here if possible or just log the count with context
        count = await run_ai_reply_worker(db, hours_threshold=0)
        
        msg = f"Đã hoàn thành trả lời tự động {count} lá thư." if count > 0 else "Không có thư mới cần phản hồi."
        worker_manager.add_log(
            trigger_id or "letter", 
            msg, 
            details={
                "count": count,
                "timestamp": get_now().replace(tzinfo=None).isoformat(),
                "action": "ai_reply_letters"
            }
        )
    except Exception as e:
        worker_manager.add_log(trigger_id or "letter", f"Lỗi: {str(e)}", status="failure")
    finally:
        db.close()

async def resource_task(config=None, trigger_id=None):
    db = get_session_factory()()
    try:
        category = random.choice(CATEGORIES)
        titles = []
        async for res_line in run_youtube_crawl_agent(category, limit=3, db=db):
            # run_youtube_crawl_agent yields SSE strings like "data: {...}\n\n"
            if "event\": \"done\"" in res_line:
                try:
                    json_str = res_line.strip()
                    if json_str.startswith("data: "):
                        json_str = json_str[6:]
                    data = json.loads(json_str)
                    results = data.get("data", {}).get("results", [])
                    # Lấy title của các tài nguyên mới được insert
                    titles = [r["title"] for r in results if r.get("status") == "inserted"]
                except Exception as e:
                    logger.error(f"Error parsing resource_task results: {e}")
            
        count = len(titles)
        msg = f"Đã cập nhật {count} tài nguyên mục {category}." if count > 0 else f"Không tìm thấy tài nguyên mới cho mục {category}."
        worker_manager.add_log(
            trigger_id or "resource", 
            msg, 
            details={
                "category": category, 
                "count": count,
                "titles": titles,
                "action": "crawl_resources"
            }
        )
    except Exception as e:
        worker_manager.add_log(trigger_id or "resource", f"Lỗi: {str(e)}", status="failure")
    finally:
        db.close()

async def _send_templated_notification(tpl, trigger_id=None, config=None):
    from app.services.db.session import get_session_factory
    from app.services.db.models import User, NotificationOutbox
    from sqlalchemy import select
    
    # Priority: Config > Template
    title = (config or {}).get("title") or tpl["title"]
    body = (config or {}).get("body") or tpl["body"]
    category = (config or {}).get("category") or tpl["category"]

    db = get_session_factory()()
    try:
        users = db.scalars(select(User).filter(User.is_active == True)).all()
        outbox_entries = [
            NotificationOutbox(
                user_id=u.user_id,
                title=title,
                body=body,
                category=category,
                metadata_json={"trigger_id": trigger_id}
            )
            for u in users
        ]
        db.add_all(outbox_entries)
        db.commit()
        
        worker_manager.add_log(
            trigger_id or f"notif_{category}", 
            f"Chiến dịch thông báo: '{title}'", 
            details={
                "title": title,
                "body": body,
                "user_count": len(outbox_entries),
                "category": category,
                "action": "push_notifications"
            }
        )
    except Exception as e:
        worker_manager.add_log(trigger_id or f"notif_{tpl['category']}", f"Lỗi: {str(e)}", status="failure")
    finally:
        db.close()

ACTION_MAPPING = {
    "ai_moderation": letter_task,
    "resource_crawler": resource_task,
    "batch_notification": notification_morning_task,
    "daily_reminder": notification_reminder_task,
}

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
        self.workers: Dict[str, AdminWorker] = {}
        self.logs = []
        asyncio.create_task(self.initialize())

    async def initialize(self):
        await asyncio.sleep(2)
        logger.info("Initializing WorkerManager from Database...")
        db = get_session_factory()()
        try:
            from app.services.db.models import AutomationTrigger
            triggers = db.scalars(select(AutomationTrigger)).all()
            for t in triggers:
                task_func = ACTION_MAPPING.get(t.action_key)
                if not task_func: continue
                from app.services.utils import VN_TZ
                last_run = t.last_run_at
                if last_run and last_run.tzinfo is None:
                    last_run = last_run.replace(tzinfo=VN_TZ)

                worker = AdminWorker(
                    name=t.name,
                    interval_min=int(t.schedule_value) if t.schedule_type == 'interval' else None,
                    daily_time=t.schedule_value if t.schedule_type == 'daily' else None,
                    task_func=task_func,
                    trigger_id=t.trigger_id,
                    config=t.config,
                    last_run=last_run
                )
                self.workers[t.trigger_id] = worker
                if t.is_active:
                    worker.start()
        except Exception as e:
            logger.error(f"WorkerManager initialization failed: {e}")
        finally:
            db.close()

    def add_log(self, target_id: str, message: str, status: str = "success", details: dict = None):
        log_entry = {
            "timestamp": get_now().replace(tzinfo=None).isoformat(),
            "worker": target_id,
            "message": message,
            "status": status,
            "details": details or {}
        }
        self.logs.append(log_entry)
        
        db = get_session_factory()()
        try:
            db.execute(insert(AutomationLog).values(
                log_id=str(uuid.uuid4()),
                target_id=target_id,
                action_key="automation_event",
                status=status,
                message=message,
                details=details or {},
                created_at=get_now().replace(tzinfo=None)
            ))
            db.commit()
        except Exception as e:
            logger.error(f"Failed to persist automation log: {e}")
        finally:
            db.close()

        if len(self.logs) > 50:
            self.logs = self.logs[-50:]

    def get_status(self):
        return {
            "workers": {k: w.to_dict() for k, w in self.workers.items()},
            "logs": self.logs[::-1]
        }

    def toggle(self, target_id: str, active: bool):
        if target_id in self.workers:
            worker = self.workers[target_id]
            if active:
                worker.start()
            else:
                worker.stop()
            
            db = get_session_factory()()
            try:
                from app.services.db.models import AutomationTrigger
                db.query(AutomationTrigger).filter(AutomationTrigger.trigger_id == target_id).update({"is_active": active})
                db.commit()
            finally:
                db.close()
                
            self.add_log(target_id, f"Tác vụ {'bắt đầu' if active else 'dừng'}")
            return True
        return False

    def update_config(self, target_id: str, interval_min: Optional[int] = None, daily_time: Optional[str] = None):
        if target_id in self.workers:
            worker = self.workers[target_id]
            
            # Reset values to ensure only one mode is active
            if interval_min is not None:
                worker.interval_min = interval_min
                worker.daily_time = None
            elif daily_time is not None:
                worker.daily_time = daily_time
                worker.interval_min = None
            
            db = get_session_factory()()
            try:
                from app.services.db.models import AutomationTrigger
                val = str(interval_min) if interval_min is not None else daily_time
                dtype = 'interval' if interval_min is not None else 'daily'
                db.query(AutomationTrigger).filter(AutomationTrigger.trigger_id == target_id).update({
                    "schedule_type": dtype,
                    "schedule_value": val
                })
                db.commit()
            finally:
                db.close()

            if worker.active:
                worker.stop()
                worker.start()
            return True
        return False

worker_manager = WorkerManager()
