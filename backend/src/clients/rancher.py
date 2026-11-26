from typing import Any

import httpx

from clients.models.namespace import Namespace, NamespaceCreate
from clients.models.project import RancherProject, RancherProjectCreate

from clients.exceptions import RancherError

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
        labels: dict[str, Any] | None = None
    ) -> RancherProject:
        payload: RancherProjectCreate = {
            "clusterId": cluster_id,
            "name": name,
        }

        if description:
            payload["description"] = description

        if labels:
            payload["labels"] = labels

        request = self._client.build_request("POST", "v3/projects", json=payload)
        response = await self.__exec_request(request)

        return response.json()

    async def delete_project(self, project_id: str) -> RancherProject:
        request = self._client.build_request("DELETE", f"v3/projects/{project_id}")
        response = await self.__exec_request(request)
        return response.json()

    async def create_namespace(
        self,
        cluster_id: str,
        name: str,
        project_id: str,
        labels: dict[str, Any] | None = None
    ) -> Namespace:
        payload: NamespaceCreate = {
            "projectId": project_id,
            "name": name
        }

        if labels:
            payload["labels"] = labels

        request = self._client.build_request("POST", f"v3/clusters/{cluster_id}/namespaces", json=payload)
        response = await self.__exec_request(request)

        return response.json()

    async def delete_namespace(self, cluster_id: str, namespace_id: str) -> Namespace:
        request = self._client.build_request("DELETE", f"v3/clusters/{cluster_id}/namespaces/{namespace_id}")
        response = await self.__exec_request(request)
        return response.json()

    @staticmethod
    def _extract_error(response: httpx.Response) -> str:
        try:
            message = response.json().get("message")
        except ValueError:
            message = None

        return f"Rancher API Error: {message or response.text}"

    async def __exec_request(self, request: httpx.Request) -> httpx.Response:
        try:
            response = await self._client.send(request)
        except httpx.HTTPError as e:
            raise RancherError(f"Не удалось выполнить запрос к Rancher API: {e}")

        if not response.is_success:
            raise RancherError(self._extract_error(response), response.status_code)

        return response
