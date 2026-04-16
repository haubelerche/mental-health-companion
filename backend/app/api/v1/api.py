from fastapi import APIRouter

from app.api.v1.routers import admin, auth, chat, connect, home, reflect, resources

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(home.router)
api_router.include_router(reflect.router)
api_router.include_router(resources.router)
api_router.include_router(connect.router)
api_router.include_router(admin.router)
