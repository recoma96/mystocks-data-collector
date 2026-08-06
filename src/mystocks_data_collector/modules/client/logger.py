import json
from typing import Any

import httpx


_SENSITIVE_KEYS = {"client_id", "client_secret", "access_token"}
_MAX_LOG_BODY_LENGTH = 2000


def redact(payload: Any) -> Any:
    """민감한 키(client_id, client_secret, access_token 등)를 마스킹"""
    if isinstance(payload, dict):
        return {
            key: "***" if key.lower() in _SENSITIVE_KEYS else redact(value)
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [redact(item) for item in payload]
    return payload


def truncate(text: str) -> str:
    """너무 긴 로그를 일정 크기로 자르기"""
    if len(text) <= _MAX_LOG_BODY_LENGTH:
        return text
    return text[:_MAX_LOG_BODY_LENGTH] + f"... ({len(text) - _MAX_LOG_BODY_LENGTH} more chars)"


def dump_redacted(payload: Any) -> str:
    return truncate(json.dumps(redact(payload), ensure_ascii=False, default=str))


def dump_response_body(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return truncate(response.text)
    return dump_redacted(body)
