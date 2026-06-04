import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from wechat_butler.ai.chat import OpenAIChatService
from wechat_butler.api.rate_limiter import RateLimiter, rate_limit_error_response
from wechat_butler.config import AppConfig
from wechat_butler.openai_compat.errors import (
    ErrorCode,
    ErrorType,
    error_response,
    error_sse_event,
)
from wechat_butler.openai_compat.schemas import (
    ChatCompletionRequest,
    ModelCapabilities,
    ModelInfo,
    ModelsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["openai"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@router.post("/chat/completions")
async def chat_completions(request: Request):
    rate_limiter: RateLimiter = request.app.state.rate_limiter
    chat_service: OpenAIChatService = request.app.state.chat_service

    try:
        body_bytes = await request.body()
        payload = await _parse_request_body(body_bytes)
    except _BadRequest as e:
        return error_response(
            status_code=400,
            message=str(e),
            error_type=ErrorType.INVALID_REQUEST,
            code=ErrorCode.MISSING_MESSAGES,
        )

    stream_required = payload.get("stream")
    if stream_required is not True:
        return error_response(
            status_code=400,
            message="Only streaming is supported (stream must be true)",
            error_type=ErrorType.INVALID_REQUEST,
            code=ErrorCode.STREAM_REQUIRED,
        )

    messages = payload.get("messages")
    if messages is None:
        return error_response(
            status_code=400,
            message="messages is required",
            error_type=ErrorType.INVALID_REQUEST,
            code=ErrorCode.MISSING_MESSAGES,
        )
    if not isinstance(messages, list) or len(messages) == 0:
        return error_response(
            status_code=400,
            message="messages must not be empty",
            error_type=ErrorType.INVALID_REQUEST,
            code=ErrorCode.EMPTY_MESSAGES,
        )

    try:
        chat_request = ChatCompletionRequest.model_validate(payload)
    except Exception as e:
        return error_response(
            status_code=400,
            message=f"Invalid request body: {e}",
            error_type=ErrorType.INVALID_REQUEST,
            code=ErrorCode.MISSING_MESSAGES,
        )

    x_mode = request.headers.get("x-mode")
    x_session_id = request.headers.get("x-session-id")

    rate_ctx = rate_limiter.acquire(x_mode=x_mode, x_session_id=x_session_id)
    try:
        await rate_ctx.__aenter__()
    except Exception as e:
        return rate_limit_error_response(e)

    async def event_stream() -> AsyncIterator[str]:
        try:
            try:
                async for sse_line in chat_service.stream(chat_request, x_mode=x_mode):
                    yield sse_line
            finally:
                await rate_ctx.__aexit__(None, None, None)
        except Exception as e:
            logger.exception("Streaming error")
            yield error_sse_event(
                message=str(e),
                error_type=ErrorType.SERVER,
                code=ErrorCode.INTERNAL,
            )
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream; charset=utf-8",
        headers=SSE_HEADERS,
    )


@router.get("/models")
async def list_models(request: Request):
    config: AppConfig = request.app.state.config.config
    mcp: MCPClient = request.app.state.mcp_client

    tool_names = list(mcp.tool_names) if mcp.is_connected else []
    capabilities = ModelCapabilities(tools=bool(tool_names), tool_names=tool_names)

    models: list[ModelInfo] = []
    seen: set[str] = set()
    for m in config.llm.models:
        if m.id in seen:
            continue
        seen.add(m.id)
        models.append(
            ModelInfo(
                id=m.id,
                owned_by=m.provider or config.llm.provider,
                x_capabilities=capabilities,
            )
        )
    if config.llm.default_model and config.llm.default_model not in seen:
        models.append(
            ModelInfo(
                id=config.llm.default_model,
                owned_by=config.llm.provider,
                x_capabilities=capabilities,
            )
        )

    return ModelsResponse(data=models)


class _BadRequest(Exception):
    pass


async def _parse_request_body(body_bytes: bytes) -> dict:
    import json

    if not body_bytes:
        raise _BadRequest("Empty request body")
    try:
        return json.loads(body_bytes)
    except json.JSONDecodeError as e:
        raise _BadRequest(f"Invalid JSON: {e}") from e
