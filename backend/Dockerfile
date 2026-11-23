FROM ghcr.io/astral-sh/uv:bookworm-slim
# образ линукса который скачивает с python опираясь на uv

ENV PYTHONUNBUFFERED=1

ENV UV_LINK_MODE=copy

ENV UV_COMPILE_BYTECODE=1

WORKDIR /app


COPY .python-version pyproject.toml uv.lock ./
# .python-version т.к использовали ghcr.io

RUN uv sync --frozen --no-dev --no-install-project

COPY . .

RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

CMD ["uvicorn", "main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
