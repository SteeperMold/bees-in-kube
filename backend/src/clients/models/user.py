from pydantic import Field

from clients.models.general import ResourceBase, ResourceStates


class UserBase(ResourceBase):
    username: str
    enabled: bool
    must_change_password: bool = Field(default=False)


class UserCreate(UserBase):
    password: str = Field(min_length=12)


class User(UserBase):
    pass
