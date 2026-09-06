from fastapi import APIRouter

from app.api.v1 import coordinator, health, models, projects

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(projects.router)
api_router.include_router(models.router)
api_router.include_router(coordinator.router)
