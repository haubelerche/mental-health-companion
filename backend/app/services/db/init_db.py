from app.services.db import models
from app.services.db.session import Base, get_engine, get_session_factory
from sqlalchemy import select

def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())
    
    # Seed fixed triggers
    factory = get_session_factory()
    db = factory()
    try:
        from app.services.db.models import AutomationTrigger
        fixed_triggers = [
            {
                "trigger_id": "fixed_batch_notification",
                "name": "Gửi thông báo hàng loạt",
                "trigger_type": "fixed",
                "action_key": "batch_notification",
                "schedule_interval": "0 9 * * *", # 9 AM daily
                "config": {"template_id": "daily_greeting"}
            },
            {
                "trigger_id": "fixed_ai_moderation",
                "name": "Kiểm duyệt thư với AI",
                "trigger_type": "fixed",
                "action_key": "ai_moderation",
                "schedule_interval": "*/30 * * * *", # Every 30 mins
                "config": {"threshold": 0.8}
            },
            {
                "trigger_id": "fixed_resource_crawler",
                "name": "Crawler tài nguyên resource",
                "trigger_type": "fixed",
                "action_key": "resource_crawler",
                "schedule_interval": "0 0 * * 0", # Every Sunday midnight
                "config": {"sources": ["meditation_hub"]}
            }
        ]
        
        for ft in fixed_triggers:
            exists = db.scalar(select(AutomationTrigger).where(AutomationTrigger.trigger_id == ft["trigger_id"]))
            if not exists:
                db.add(AutomationTrigger(**ft))
        db.commit()
    except Exception as e:
        print(f"Failed to seed automation triggers: {e}")
        db.rollback()
    finally:
        db.close()

