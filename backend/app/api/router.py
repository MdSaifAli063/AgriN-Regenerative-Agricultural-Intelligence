from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.farms import router as farms_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(farms_router)
