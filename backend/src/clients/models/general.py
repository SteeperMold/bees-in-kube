from typing import Any, Literal, NotRequired, TypedDict

LifecycleState = Literal["active", "provisioning", "updating", "removing"]
TransitionState = Literal["yes", "no", "error"]


class ResourceBase(TypedDict):
    name: str
    description: NotRequired[str]
    labels: NotRequired[dict[str, Any]]


class ResourceStates(TypedDict):
    state: LifecycleState
    transitioning: TransitionState
