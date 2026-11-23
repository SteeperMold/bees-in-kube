from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.router import api_router
from infra.settings import Settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application starting...")

    yield

    print("Application shutting down...")


def create_app() -> FastAPI:
    settings = Settings()

    app = FastAPI(
        title=settings.APP_TITLE,
        lifespan=lifespan,
    )

    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
