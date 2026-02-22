from fastapi import APIRouter
from .health import router as health_router
from .analyze import router as analyze_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(analyze_router)
# later: include report, sources, etc.
