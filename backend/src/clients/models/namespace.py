from clients.models.general import ResourceBase, ResourceStates


class NamespaceBase(ResourceBase):
    projectId: str


class NamespaceCreate(NamespaceBase):
    pass


class Namespace(NamespaceBase, ResourceStates):
    id: str
