from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.agents import router as agents_router
from app.api.memory_write import router as write_router
from app.api.memory_read import router as read_router
from app.api.admin import router as admin_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(agents_router, tags=["agents"])
api_router.include_router(write_router, tags=["memory"])
api_router.include_router(read_router, tags=["memory"])
api_router.include_router(admin_router)
