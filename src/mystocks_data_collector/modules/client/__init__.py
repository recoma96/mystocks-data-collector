import logging
import time
from abc import ABCMeta
from typing import Any, Dict

import httpx

from mystocks_data_collector.config import Config
from mystocks_data_collector.modules.client.logger import dump_redacted, dump_response_body
from mystocks_data_collector.modules.exc import APIRequestError, APIResponseError


logger = logging.getLogger(__name__)
logging.getLogger().setLevel(Config.LOGGING_LEVEL)


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
        started_at = time.monotonic()

        try:
            response = await self._client.request(
                method, path, params=params, data=data, json=json, headers=headers
            )
        except httpx.TimeoutException as e:
            raise APIRequestError(f"요청 시간 초과: {method} {path}", cause=e) from e
        except httpx.RequestError as e:
            raise APIRequestError(f"요청 실패: {method} {path}", cause=e) from e

        elapsed_ms = (time.monotonic() - started_at) * 1000
        url = response.url.copy_with(query=None)

        logger.info("API %s %s -> %s (%.1fms)", method, url, response.status_code, elapsed_ms)
        logger.debug(
            "API %s %s request=%s response=%s",
            method,
            url,
            dump_redacted({"params": params, "data": data, "json": json}),
            dump_response_body(response),
        )

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
