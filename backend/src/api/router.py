from fastapi import APIRouter

from api import test_handler

api_router = APIRouter()

api_router.include_router(test_handler.router)
