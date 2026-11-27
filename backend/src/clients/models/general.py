from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ResourceBase(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str
    description: str | None = Field(default=None)
    labels: dict[str, str] = Field(default_factory=dict)


class ResourceStates(BaseModel):
    state: Literal["active", "provisioning", "updating", "removing"]
    transitioning: Literal["yes", "no", "error"]
