import asyncio
from fastapi import Depends, Request, Body
from app.api.deps import enforce_admin_ip, get_admin_claims
from app.core.responses import ok
from app.services.worker_manager import worker_manager
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

@router.patch("/automation/config")
async def update_worker_config(
    request: Request,
    worker_name: str = Body(..., embed=True),
    interval_min: int | None = Body(None, embed=True),
    daily_time: str | None = Body(None, embed=True),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    success = worker_manager.update_config(worker_name, interval_min, daily_time)
    return ok({"success": success, "status": worker_manager.get_status()})

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
        # Run task in background to not block the response
        asyncio.create_task(worker.task_func())
        return ok({"success": True, "message": f"Đã kích hoạt {worker_name} chạy ngay lập tức"})
    return ok({"success": False, "message": "Worker không tồn tại"})
