import http

import httpx

from clients.exceptions import RancherError
from clients.models.kubeconfig import Kubeconfig
from clients.models.namespace import Namespace, NamespaceCreate
from clients.models.project import RancherProject, RancherProjectCreate
from clients.models.user import User, UserCreate


class RancherClient:
    def __init__(
        self,
        base_url: str,
        api_token: str,
        timeout: float = 10.0,
        verify_ssl: bool = True
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Accept": "application/json", "Authorization": f"Bearer {api_token}"},
            timeout=timeout,
            verify=verify_ssl,
        )

    async def check_connection(self) -> bool:
        try:
            response = await self._client.get("/v3")
        except httpx.HTTPError:
            return False

        return response.is_success

    async def close(self) -> None:
        await self._client.aclose()

    async def create_project(
        self,
        cluster_id: str,
        name: str,
        description: str | None = None,
        labels: dict[str, str] | None = None
    ) -> RancherProject:
        payload = RancherProjectCreate(
            cluster_id=cluster_id,
            name=name,
            description=description,
            labels=labels or {}
        )

        request = self._client.build_request(
            method=http.HTTPMethod.POST,
            url="v3/projects",
            json=payload.model_dump(by_alias=True)
        )

        response = await self._exec_request(request)

        return RancherProject.model_validate_json(response.content)

    async def delete_project(self, project_id: str) -> RancherProject:
        request = self._client.build_request(
            method=http.HTTPMethod.DELETE,
            url=f"v3/projects/{project_id}"
        )

        response = await self._exec_request(request)

        return RancherProject.model_validate_json(response.content)

    async def get_namespace(self, cluster_id: str, namespace_id: str) -> Namespace:
        request = self._client.build_request(
            method="GET",
            url=f"v3/clusters/{cluster_id}/namespaces/{namespace_id}"
        )

        response = await self._exec_request(request)

        return Namespace.model_validate_json(response.content)

    async def create_namespace(
        self,
        cluster_id: str,
        name: str,
        project_id: str,
        labels: dict[str, str] | None = None
    ) -> Namespace:
        payload = NamespaceCreate(
            project_id=project_id,
            name=name,
            labels=labels or {}
        )

        request = self._client.build_request(
            method=http.HTTPMethod.POST,
            url=f"v3/clusters/{cluster_id}/namespaces",
            json=payload.model_dump(by_alias=True)
        )

        response = await self._exec_request(request)

        return Namespace.model_validate_json(response.content)

    async def delete_namespace(self, cluster_id: str, namespace_id: str) -> Namespace:
        request = self._client.build_request(
            method=http.HTTPMethod.DELETE,
            url=f"v3/clusters/{cluster_id}/namespaces/{namespace_id}"
        )

        response = await self._exec_request(request)

        return Namespace.model_validate_json(response.content)

    async def create_user(
        self,
        username: str,
        password: str,
        must_change_password: bool,
        enabled: bool
    ) -> User:
        payload = UserCreate(
            name=username,
            username=username,
            password=password,
            must_change_password=must_change_password,
            enabled=enabled
        )

        request = self._client.build_request(
            method=http.HTTPMethod.POST,
            url="/v3/users",
            json=payload.model_dump(by_alias=True)
        )

        response = await self._exec_request(request)

        return User.model_validate_json(response.content)

    async def generate_kubeconfig(self, cluster_id: str, user_token: str) -> Kubeconfig:
        request = self._client.build_request(
            method=http.HTTPMethod.POST,
            url=f"/v3/clusters/{cluster_id}",
            headers={"Accept": "application/json", "Authorization": f"Bearer {user_token}"},
            params={"action": "generateKubeconfig"}
        )

        response = await self._exec_request(request)

        return Kubeconfig.model_validate_json(response.content)

    @staticmethod
    def _extract_error(response: httpx.Response) -> str:
        try:
            message = response.json().get("message")
        except ValueError:
            message = None

        return f"Rancher API Error: {message or response.text}"

    async def _exec_request(self, request: httpx.Request) -> httpx.Response:
        try:
            response = await self._client.send(request)
        except httpx.HTTPError as e:
            raise RancherError(f"Не удалось выполнить запрос к Rancher API: {e}") from e

        if not response.is_success:
            raise RancherError(self._extract_error(response), response.status_code) from None

        return response
