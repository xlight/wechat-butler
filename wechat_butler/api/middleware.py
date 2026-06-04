import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from wechat_butler.openai_compat.errors import ErrorCode, ErrorType, error_response

logger = logging.getLogger(__name__)

PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class APIKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, expected_key: str):
        super().__init__(app)
        self._expected_key = expected_key

    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        if not self._expected_key:
            return await call_next(request)

        provided_key = self._extract_key(request)
        if not provided_key or provided_key != self._expected_key:
            return error_response(
                status_code=401,
                message="Invalid or missing API key",
                error_type=ErrorType.AUTHENTICATION,
                code=ErrorCode.INVALID_API_KEY,
            )

        return await call_next(request)

    def _extract_key(self, request: Request) -> str | None:
        auth_header = request.headers.get("Authorization")
        if auth_header:
            parts = auth_header.split(None, 1)
            if len(parts) == 2 and parts[0].lower() == "bearer":
                return parts[1].strip()

        legacy = request.headers.get("X-Butler-API-Key") or request.headers.get("x-butler-api-key")
        if legacy:
            return legacy

        return None
