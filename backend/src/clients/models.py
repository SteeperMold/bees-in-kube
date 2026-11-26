from typing import Any, Literal, NotRequired, TypedDict


class RancherProjectBase(TypedDict):
    clusterId: str
    name: str
    description: NotRequired[str]
    labels: NotRequired[dict[str, Any]]


class RancherProjectCreate(RancherProjectBase):
    pass


class RancherProject(RancherProjectBase):
    id: str
    state: Literal["active", "provisioning", "updating", "removing"]
    transitioning: Literal["yes", "no", "error"]
