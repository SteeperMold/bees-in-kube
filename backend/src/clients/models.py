from typing import Any, NotRequired, TypedDict


class RancherProjectBase(TypedDict):
    clusterId: str
    name: str
    description: NotRequired[str]
    labels: NotRequired[dict[str, Any]]


class RancherProjectCreate(RancherProjectBase):
    pass


class RancherProject(RancherProjectBase):
    id: str
    state: str
