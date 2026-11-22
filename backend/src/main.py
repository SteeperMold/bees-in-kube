from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.router import api_router
from clients.rancher import RancherClient
from core.settings import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.rancher_client = RancherClient(
        base_url=settings.RANCHER_BASE_URL,
        api_token=settings.RANCHER_API_TOKEN,
        timeout=settings.RANCHER_TIMEOUT,
        verify_ssl=settings.RANCHER_VERIFY_SSL,
    )

    yield

    await app.state.rancher_client.close()


app = FastAPI(title=settings.APP_TITLE, lifespan=lifespan)

app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
