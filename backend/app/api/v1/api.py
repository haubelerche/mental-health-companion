from fastapi import APIRouter

from app.api.v1.routers import (
    admin,
    auth,
    chat,
    checkin,
    connect,
    dashboard,
    guest,
    home,
    intake,
    nutrition,
    onboarding,
    policies,
    reflect,
    resources,
    rewards,
    safety,
    screening,
    ws,
    letter,
    notifications,
)
from app.knowledge.routes import router as knowledge_router
from app.memory.routes import router as memory_router

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(guest.router)
api_router.include_router(policies.router)
api_router.include_router(onboarding.router)
api_router.include_router(intake.router)
api_router.include_router(checkin.router)
api_router.include_router(screening.router)
api_router.include_router(safety.router)
api_router.include_router(dashboard.router)
api_router.include_router(chat.router)
api_router.include_router(memory_router)
api_router.include_router(home.router)
api_router.include_router(reflect.router)
api_router.include_router(resources.router)
api_router.include_router(connect.router)
api_router.include_router(admin.router)
api_router.include_router(nutrition.router)
api_router.include_router(rewards.router)
api_router.include_router(knowledge_router)
api_router.include_router(ws.router)
api_router.include_router(letter.router)
api_router.include_router(notifications.router)
