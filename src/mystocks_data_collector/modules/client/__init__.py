from abc import ABCMeta
from typing import Any, Dict

import httpx

from mystocks_data_collector.modules.exc import APIRequestError, APIResponseError


class APIClient(metaclass=ABCMeta):
    _client: httpx.AsyncClient

    def __init__(self, base_url: str, timeout: float = 10.0):
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            headers={},
        )

    def update_headers(self, headers: Dict[str, str]) -> None:
        self._client.headers.update(headers)

    def set_header(self, key: str, value: str) -> None:
        self._client.headers[key] = value

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Dict[str, Any] | None = None,
        data: Dict[str, Any] | None = None,
        json: Dict[str, Any] | None = None,
        headers: Dict[str, str] | None = None,
    ) -> Dict[str, Any]:
        try:
            response = await self._client.request(
                method, path, params=params, data=data, json=json, headers=headers
            )
        except httpx.TimeoutException as e:
            raise APIRequestError(f"요청 시간 초과: {method} {path}", cause=e) from e
        except httpx.RequestError as e:
            raise APIRequestError(f"요청 실패: {method} {path}", cause=e) from e

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise APIResponseError(
                f"API 오류 응답: {response.status_code} {method} {path}",
                status_code=response.status_code,
                response_body=response.text,
            ) from e

        try:
            return response.json()
        except ValueError as e:
            raise APIResponseError(
                f"JSON 파싱 실패: {method} {path}",
                status_code=response.status_code,
                response_body=response.text,
            ) from e

    async def get(self, path: str, *, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return await self._request("GET", path, params=params)

    async def post(
        self,
        path: str,
        *,
        data: Dict[str, Any] | None = None,
        json: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        return await self._request("POST", path, data=data, json=json)

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "APIClient":
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.close()
