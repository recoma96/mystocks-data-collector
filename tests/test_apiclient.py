import json
from typing import Callable

import httpx
import pytest

from mystocks_data_collector.modules.client import APIClient
from mystocks_data_collector.modules.exc import APIRequestError, APIResponseError


class _DummyAPIClient(APIClient):
    pass


def _build_client(handler: Callable[[httpx.Request], httpx.Response]) -> _DummyAPIClient:
    client = _DummyAPIClient(base_url="http://testserver")
    client._client = httpx.AsyncClient(
        base_url="http://testserver",
        transport=httpx.MockTransport(handler), # HTTP 로 통신하는 실제 로직을 Mock으로 커스텀
        headers=client._client.headers,
    )
    return client


async def test_get_with_param_send_as_param():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/v1/stocks"
        assert request.url.params["symbol"] == "005930"
        return httpx.Response(200, json={"price": 71000})

    client = _build_client(handler)

    await client.get("/v1/stocks", params={"symbol": "005930"})


async def test_post_with_json_body_sends_as_json():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.headers["content-type"] == "application/json"
        assert json.loads(request.content) == {"symbol": "005930", "qty": 10}
        return httpx.Response(200, json={"order_id": "abc123"})

    client = _build_client(handler)

    await client.post("/v1/orders", json={"symbol": "005930", "qty": 10})


async def test_post_with_form_data_sends_as_urlencoded_body():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.headers["content-type"] == "application/x-www-form-urlencoded"
        assert request.content == b"grant_type=client_credentials&client_id=abc"
        return httpx.Response(200, json={"access_token": "token123"})

    client = _build_client(handler)

    await client.post(
        "/oauth2/token",
        data={"grant_type": "client_credentials", "client_id": "abc"},
    )


async def test_update_headers_and_set_header_are_sent_with_request():
    captured: dict[str, httpx.Headers] = {} # HTTP 호출 과정에서 header를 스캔하기 위한 변수

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = request.headers
        return httpx.Response(200, json={})

    client = _build_client(handler)
    client.update_headers({"client-id": "id-1", "client-secret": "secret-1"})
    client.set_header("Authorization", "Bearer token")

    await client.get("/ping")

    headers = captured["headers"]
    assert headers["client-id"] == "id-1"
    assert headers["client-secret"] == "secret-1"
    assert headers["authorization"] == "Bearer token"


async def test_4xx_response_raises_api_response_error_with_details():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid_request"})

    client = _build_client(handler)

    with pytest.raises(APIResponseError) as exc_info:
        await client.get("/v1/stocks")

    assert exc_info.value.status_code == 400
    assert "invalid_request" in exc_info.value.response_body


async def test_5xx_response_raises_api_response_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal error")

    client = _build_client(handler)

    with pytest.raises(APIResponseError) as exc_info:
        await client.get("/v1/stocks")

    assert exc_info.value.status_code == 500


async def test_invalid_json_body_raises_api_response_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not-json")

    client = _build_client(handler)

    with pytest.raises(APIResponseError) as exc_info:
        await client.get("/v1/stocks")

    assert exc_info.value.status_code == 200
    assert exc_info.value.response_body == "not-json"


async def test_network_error_raises_api_request_error_with_cause():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    client = _build_client(handler)

    with pytest.raises(APIRequestError) as exc_info:
        await client.get("/v1/stocks")

    assert isinstance(exc_info.value.cause, httpx.ConnectError)


async def test_timeout_raises_api_request_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out")

    client = _build_client(handler)

    with pytest.raises(APIRequestError) as exc_info:
        await client.get("/v1/stocks")

    assert isinstance(exc_info.value.cause, httpx.TimeoutException)


async def test_close_closes_underlying_client():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    client = _build_client(handler)

    await client.close()

    assert client._client.is_closed


async def test_context_manager_closes_client_even_on_exception():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    client = _build_client(handler)

    with pytest.raises(ValueError):
        async with client as ctx_client:
            assert ctx_client is client
            raise ValueError("boom")

    assert client._client.is_closed
