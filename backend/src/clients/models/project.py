from clients.models.general import ResourceBase, ResourceStates


class RancherProjectBase(ResourceBase):
    clusterId: str


class RancherProjectCreate(RancherProjectBase):
    pass


class RancherProject(RancherProjectBase, ResourceStates):
    id: str
