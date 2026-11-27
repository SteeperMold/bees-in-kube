from pydantic import BaseModel


class Kubeconfig(BaseModel):
    config: str
