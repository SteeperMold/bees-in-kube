"""Слой бизнес-логики

Здесь размещайте переиспользуемую логику, не зависящую от фреймворка:
доменные модели, вычисления, оркестрацию внешних API/базы данных и т. п.

Рекомендации:
- Не импортируйте FastAPI (``Request``, ``HTTPException``, роутеры, ...).
  За HTTP-детали отвечает слой API.
- Делайте функции/классы легко тестируемыми без запущенного сервера.
- Модули из ``api/`` вызывают сервисы; сервисы никогда не вызывают хендлеры.

.. note::
   Важно! Это лишь пример. Удалите этот файл при первом коммите в backend.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TestMessage:
    """Результат, который возвращает :class:`TestService`."""

    message: str
    environment: str


class TestService:
    """Пример сервиса, показывающий, как хендлеры должны делегировать работу."""

    def __init__(self, environment: str = "development") -> None:
        self._environment = environment

    def build_message(self, name: str | None = None) -> TestMessage:
        """Собрать приветствие, персональное, если передан ``name``."""
        message = f"Hello, {name}!" if name else "hello world"
        return TestMessage(message=message, environment=self._environment)
