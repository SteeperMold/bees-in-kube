from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from api.deps import RancherClientDep, get_rancher_client

router = APIRouter(prefix="/rancher", tags=["Rancher"], dependencies=[Depends(get_rancher_client)])


@router.get("/health")
async def rancher_health(client: RancherClientDep) -> JSONResponse:
    if await client.check_connection():
        return JSONResponse(
            status_code=200, content={"status": "connected", "rancher": "available"}
        )

    return JSONResponse(
        status_code=503, content={"status": "disconnected", "rancher": "unavailable"}
    )
