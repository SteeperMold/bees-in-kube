from typing import Annotated

from fastapi import Depends, Request

from clients.rancher import RancherClient


def get_rancher_client(request: Request) -> RancherClient:
    return request.app.state.rancher_client


RancherClientDep = Annotated[RancherClient, Depends(get_rancher_client)]
