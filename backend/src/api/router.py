from fastapi import APIRouter

from api.endpoints import rancher, system

api_router = APIRouter()

api_router.include_router(system.router)
api_router.include_router(rancher.router)
