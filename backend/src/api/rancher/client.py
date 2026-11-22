import httpx

from fastapi import APIRouter

router = APIRouter()

class RancherClient:
    def __init__(
        self,
        base_url: str,
        api_token: str,
        timeout: float = 10.0,
        verify_ssl: bool = True
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {api_token}"
            },
            timeout=timeout,
            verify=verify_ssl
        )

    async def check_connection(self) -> bool:
        try:
            response = await self._client.get("/v3")
        except httpx.HTTPError:
            return False

        return response.is_success

    async def close(self) -> None:
        await self._client.aclose()
