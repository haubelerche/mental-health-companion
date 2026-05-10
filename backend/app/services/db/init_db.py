from app.services.db import models
from app.services.db.session import Base, get_engine, get_session_factory
from sqlalchemy import select
from uuid import uuid4

FIXED_TRIGGERS = [
    {
        "trigger_id": "fixed_notif_morning",
        "name": "Chào buổi sáng",
        "trigger_type": "fixed",
        "action_key": "batch_notification",
        "schedule_type": "daily",
        "schedule_value": "07:00",
        "config": {"template_index": 0}
    },
    {
        "trigger_id": "fixed_notif_reminder",
        "name": "Nhắc nhở tự chăm sóc",
        "trigger_type": "fixed",
        "action_key": "daily_reminder",
        "schedule_type": "daily",
        "schedule_value": "14:00",
        "config": {"template_index": 1}
    },
    {
        "trigger_id": "fixed_notif_letters",
        "name": "Nhắc nhở hòm thư",
        "trigger_type": "fixed",
        "action_key": "batch_notification",
        "schedule_type": "daily",
        "schedule_value": "20:00",
        "config": {"template_index": 2}
    },
    {
        "trigger_id": "fixed_letter_responder",
        "name": "AI Letter Responder",
        "trigger_type": "fixed",
        "action_key": "ai_moderation",
        "schedule_type": "interval",
        "schedule_value": "20",
        "config": {}
    },
    {
        "trigger_id": "fixed_resource_crawler",
        "name": "AI Resource Crawler",
        "trigger_type": "fixed",
        "action_key": "resource_crawler",
        "schedule_type": "interval",
        "schedule_value": "60",
        "config": {}
    }
]

def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    
    # Fix constraint if needed
    from sqlalchemy import text
    db = get_session_factory()()
    try:
        # PostgreSQL specific fix for action_key constraint
        db.execute(text("ALTER TABLE app.automation_triggers DROP CONSTRAINT IF EXISTS ck_automation_action_key"))
        db.execute(text("ALTER TABLE app.automation_triggers ADD CONSTRAINT ck_automation_action_key CHECK (action_key IN ('batch_notification','ai_moderation','resource_crawler','custom_webhook','daily_reminder'))"))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Constraint update skipped or failed (might not be Postgres): {e}")

    # Seed fixed triggers
    try:
        from app.services.db.models import AutomationTrigger
        for ft in FIXED_TRIGGERS:
            existing = db.get(AutomationTrigger, ft["trigger_id"])
            if not existing:
                trigger = AutomationTrigger(**ft)
                db.add(trigger)
        db.commit()
    except Exception as e:
        print(f"Failed to seed automation triggers: {e}")
    finally:
        db.close()