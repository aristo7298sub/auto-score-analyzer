from fastapi import APIRouter
from app.api.endpoints import router as endpoints_router

router = APIRouter()
router.include_router(endpoints_router) 