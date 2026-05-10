import asyncio
from uuid import uuid4
from fastapi import Depends, Request, Body, Path
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from app.api.deps import enforce_admin_ip, get_admin_claims, get_db
from app.core.responses import ok
from app.services.worker_manager import worker_manager
from app.services.db.models import AutomationTrigger
from .shared import router

@router.get("/automation/status")
async def get_automation_status(
    request: Request,
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    return ok(worker_manager.get_status())

@router.post("/automation/toggle")
async def toggle_worker(
    request: Request,
    worker_name: str = Body(..., embed=True),
    active: bool = Body(..., embed=True),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    success = worker_manager.toggle(worker_name, active)
    return ok({"success": success, "status": worker_manager.get_status()})

@router.get("/automation/triggers")
async def list_triggers(
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    triggers = db.scalars(select(AutomationTrigger).order_by(AutomationTrigger.created_at.desc())).all()
    return ok({"triggers": triggers})

@router.post("/automation/triggers")
async def create_trigger(
    request: Request,
    name: str = Body(...),
    action_key: str = Body(...),
    schedule_type: str = Body("daily"),
    schedule_value: str = Body(...),
    config: dict = Body({}),
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    trigger = AutomationTrigger(
        trigger_id=str(uuid4()),
        name=name,
        trigger_type="custom",
        action_key=action_key,
        schedule_type=schedule_type,
        schedule_value=schedule_value,
        config=config,
        is_active=True
    )
    db.add(trigger)
    db.commit()
    db.refresh(trigger)
    return ok({"trigger": trigger})

@router.patch("/automation/triggers/{trigger_id}")
async def update_trigger(
    request: Request,
    trigger_id: str = Path(...),
    name: str | None = Body(None),
    schedule_type: str | None = Body(None),
    schedule_value: str | None = Body(None),
    config: dict | None = Body(None),
    is_active: bool | None = Body(None),
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    trigger = db.get(AutomationTrigger, trigger_id)
    if not trigger:
        return ok({"success": False, "message": "Trigger không tồn tại"}, status_code=404)
    
    if name is not None: trigger.name = name
    if schedule_type is not None: trigger.schedule_type = schedule_type
    if schedule_value is not None: trigger.schedule_value = schedule_value
    if config is not None: trigger.config = config
    if is_active is not None: trigger.is_active = is_active
    
    db.commit()
    db.refresh(trigger)
    return ok({"trigger": trigger})

@router.delete("/automation/triggers/{trigger_id}")
async def delete_trigger(
    request: Request,
    trigger_id: str = Path(...),
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    trigger = db.get(AutomationTrigger, trigger_id)
    if not trigger:
        return ok({"success": False, "message": "Trigger không tồn tại"}, status_code=404)
    
    if trigger.trigger_type == "fixed":
        return ok({"success": False, "message": "Không thể xóa trigger cố định của hệ thống"}, status_code=400)
        
    db.delete(trigger)
    db.commit()
    return ok({"success": True})

@router.post("/automation/run-now")
async def run_worker_now(
    request: Request,
    worker_name: str = Body(..., embed=True),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    if worker_name in worker_manager.workers:
        worker = worker_manager.workers[worker_name]
        if worker.running:
            return ok({"success": False, "message": "Worker đang chạy rồi"})
        asyncio.create_task(worker.task_func())
        return ok({"success": True, "message": f"Đã kích hoạt {worker_name} chạy ngay lập tức"})
    return ok({"success": False, "message": "Worker không tồn tại"})

