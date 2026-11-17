"""HTTP-слой.

Здесь размещайте роутеры FastAPI, схемы запросов/ответов (Pydantic-модели)
и функции-эндпоинты, сгруппированные по фичам (удобно начинать с одного
модуля на ресурс).

Рекомендации:
- Хендлеры валидируют вход, вызывают сервис из ``services/`` и формируют
  ответ. Не размещайте здесь бизнес-логику и прямой доступ к БД.
- Регистрируйте ``router`` модуля в ``api/router.py``, чтобы он монтировался
  под ``/api/v1`` в ``main.py``.
- Бросайте ``HTTPException`` здесь, когда нужен HTTP-статус.

.. note::
   Важно! Это лишь пример. Удалите этот файл при первом коммите в backend.
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from infra.settings import Settings
from services.test_service import TestService

router = APIRouter(tags=["test"])


class TestResponse(BaseModel):
    """Схема ответа для примера эндпоинта."""

    message: str = Field(examples=["Hello, Alice!"])
    environment: str = Field(examples=["development"])


@router.get("/test", response_model=TestResponse)
async def get_test_message(
    name: str | None = Query(default=None, min_length=1, max_length=50),
) -> TestResponse:
    """Вернуть приветствие, опционально персональное через ``?name=``."""
    service = TestService(environment=Settings().APP_ENV.value)
    result = service.build_message(name)
    return TestResponse(message=result.message, environment=result.environment)
