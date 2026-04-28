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
    onboarding,
    policies,
    reflect,
    resources,
    safety,
    screening,
)

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
api_router.include_router(home.router)
api_router.include_router(reflect.router)
api_router.include_router(resources.router)
api_router.include_router(connect.router)
api_router.include_router(admin.router)
