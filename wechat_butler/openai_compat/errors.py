from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel


class OpenAIError(BaseModel):
    message: str
    type: str
    code: str
    param: str | None = None


class OpenAIErrorResponse(BaseModel):
    error: OpenAIError


class ErrorType:
    INVALID_REQUEST = "invalid_request_error"
    AUTHENTICATION = "authentication_error"
    RATE_LIMIT = "rate_limit_error"
    SERVER = "server_error"
    PERMISSION = "permission_error"


class ErrorCode:
    STREAM_REQUIRED = "stream_required"
    MISSING_MESSAGES = "missing_messages"
    EMPTY_MESSAGES = "empty_messages"
    MODEL_NOT_FOUND = "model_not_found"
    MODE_NOT_FOUND = "mode_not_found"
    INVALID_API_KEY = "invalid_api_key"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    QUEUE_TIMEOUT = "queue_timeout"
    SESSION_RATE_LIMIT = "session_rate_limit_exceeded"
    LLM_ERROR = "llm_error"
    LLM_TIMEOUT = "llm_timeout"
    FORBIDDEN_SESSION = "forbidden_session"
    INTERNAL = "internal_error"


def error_response(
    *,
    status_code: int,
    message: str,
    error_type: str,
    code: str,
    param: str | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"message": message, "type": error_type, "code": code, "param": param}},
    )


def error_sse_event(*, message: str, error_type: str, code: str) -> str:
    import json

    payload: dict[str, Any] = {
        "error": {"message": message, "type": error_type, "code": code},
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def llm_error_to_http_response(exc: Exception) -> JSONResponse:
    import litellm

    if isinstance(exc, litellm.AuthenticationError):
        return error_response(
            status_code=401,
            message=str(exc),
            error_type=ErrorType.AUTHENTICATION,
            code=ErrorCode.INVALID_API_KEY,
        )
    if isinstance(exc, litellm.RateLimitError):
        return error_response(
            status_code=429,
            message=str(exc),
            error_type=ErrorType.RATE_LIMIT,
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
        )
    if isinstance(exc, litellm.Timeout):
        return error_response(
            status_code=504,
            message=str(exc),
            error_type=ErrorType.SERVER,
            code=ErrorCode.LLM_TIMEOUT,
        )
    if isinstance(exc, litellm.NotFoundError):
        return error_response(
            status_code=404,
            message=str(exc),
            error_type=ErrorType.INVALID_REQUEST,
            code=ErrorCode.MODEL_NOT_FOUND,
        )
    return error_response(
        status_code=500,
        message=str(exc),
        error_type=ErrorType.SERVER,
        code=ErrorCode.LLM_ERROR,
    )
