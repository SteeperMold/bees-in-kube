from clients.models.general import ResourceBase, ResourceStates


class NamespaceBase(ResourceBase):
    project_id: str


class NamespaceCreate(NamespaceBase):
    pass


class Namespace(NamespaceBase, ResourceStates):
    id: str
