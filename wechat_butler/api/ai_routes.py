import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sse_starlette import EventSourceResponse

from wechat_butler.ai.chat import ChatRequest, ChatService
from wechat_butler.ai.prompts import PromptService
from wechat_butler.config import ConfigManager, mask_api_key
from wechat_butler.llm.router import LLMRouter
from wechat_butler.mcp.client import MCPClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


class ConfigUpdateRequest(BaseModel):
    provider: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    default_model: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None


class PromptCreateRequest(BaseModel):
    name: str
    description: str
    content: str


class PromptUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    content: str | None = None


@router.post("/chat")
async def chat(request: ChatRequest, req: Request):
    chat_service: ChatService = req.app.state.chat_service
    prompts: PromptService = req.app.state.prompt_service
    chat_service._prompts = prompts

    async def event_stream():
        async for event in chat_service.run_chat(request):
            yield event

    return EventSourceResponse(event_stream())


@router.get("/models")
async def list_models(req: Request):
    llm_router: LLMRouter = req.app.state.llm_router
    config = req.app.state.config.config
    return {"models": llm_router.list_models(), "default_model": config.llm.default_model}


@router.get("/status")
async def status(req: Request):
    config = req.app.state.config.config
    mcp: MCPClient = req.app.state.mcp_client
    return {
        "butler": {"version": "0.1.0", "status": "ok"},
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


@router.get("/config")
async def get_config(req: Request):
    config: ConfigManager = req.app.state.config
    return config.get_masked()["llm"]


@router.post("/config")
async def update_config(updates: ConfigUpdateRequest, req: Request):
    config: ConfigManager = req.app.state.config
    update_dict = {k: v for k, v in updates.model_dump().items() if v is not None}
    config.update_llm(update_dict)
    return config.get_masked()["llm"]


@router.get("/prompts")
async def list_prompts(req: Request):
    prompts: PromptService = req.app.state.prompt_service
    return {"prompts": [p.model_dump() for p in prompts.list_all()]}


@router.post("/prompts")
async def create_prompt(prompt: PromptCreateRequest, req: Request):
    prompts: PromptService = req.app.state.prompt_service
    result = prompts.create(prompt.name, prompt.description, prompt.content)
    return result.model_dump()


@router.put("/prompts/{prompt_id}")
async def update_prompt(prompt_id: str, prompt: PromptUpdateRequest, req: Request):
    prompts: PromptService = req.app.state.prompt_service
    for p in prompts.list_all():
        if p.id == prompt_id and p.builtin:
            raise HTTPException(status_code=403, detail="Built-in prompts cannot be modified")
    result = prompts.update(prompt_id, prompt.name, prompt.description, prompt.content)
    if not result:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return result.model_dump()


@router.delete("/prompts/{prompt_id}")
async def delete_prompt(prompt_id: str, req: Request):
    prompts: PromptService = req.app.state.prompt_service
    for p in prompts.list_all():
        if p.id == prompt_id and p.builtin:
            raise HTTPException(status_code=403, detail="Built-in prompts cannot be deleted")
    if not prompts.delete(prompt_id):
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {"deleted": True}
