import logging
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from wechat_butler.config import (
    AppConfig,
    ConfigManager,
)
from wechat_butler.mcp_client.client import MCPClient
from wechat_butler.openai_compat.errors import (
    ErrorCode,
    ErrorType,
    error_response,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai", tags=["ai-aux"])


class ModePatchRequest(BaseModel):
    enabled: bool | None = None
    model: str | None = None
    max_tokens: int | None = None
    system_prompt: str | None = None


@router.get("/status")
async def status(req: Request):
    config: AppConfig = req.app.state.config.config
    mcp: MCPClient = req.app.state.mcp_client
    return {
        "butler": {"version": "0.2.0", "status": "ok"},
        "llm": {
            "status": "configured" if config.llm.api_key else "not_configured",
            "provider": config.llm.provider,
            "default_model": config.llm.default_model,
        },
        "mcp": {
            "status": "connected" if mcp.is_connected else "disconnected",
            "url": config.mcp.chatshell_api_url,
            "tools": len(mcp.tools),
            "tool_names": mcp.tool_names,
        },
    }


@router.get("/modes")
async def list_modes(req: Request):
    config: AppConfig = req.app.state.config.config
    return {
        "observer": config.agent_modes.observer.model_dump(),
        "mention": config.agent_modes.mention.model_dump(),
        "user_actions": config.agent_modes.user_actions.model_dump(),
    }


@router.patch("/modes/{mode}")
async def patch_mode(mode: str, patch: ModePatchRequest, req: Request):
    config_manager: ConfigManager = req.app.state.config
    config = config_manager.config

    target = _resolve_mode(config, mode)
    if target is None:
        return error_response(
            status_code=404,
            message=f"Mode '{mode}' not found",
            error_type=ErrorType.INVALID_REQUEST,
            code=ErrorCode.MODE_NOT_FOUND,
        )

    updates: dict[str, Any] = {k: v for k, v in patch.model_dump().items() if v is not None}
    for key, value in updates.items():
        setattr(target, key, value)

    return target.model_dump()


def _resolve_mode(config: AppConfig, mode: str):
    if mode == "observer":
        return config.agent_modes.observer
    if mode == "mention":
        return config.agent_modes.mention
    if mode == "user_actions":
        return config.agent_modes.user_actions
    return None
