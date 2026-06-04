from __future__ import annotations

import secrets
import time
from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolCallFunction(BaseModel):
    name: str
    arguments: str


class ToolCall(BaseModel):
    index: int
    id: str | None = None
    type: Literal["function"] = "function"
    function: ToolCallFunction


class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] | None = None


class ChatCompletionStreamOptions(BaseModel):
    include_usage: bool | None = None
    x_include_tool_results: bool | None = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[Message]
    stream: bool | None = None
    stream_options: ChatCompletionStreamOptions | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    stop: str | list[str] | None = None
    user: str | None = None
    n: int | None = None
    tools: list[dict[str, Any]] | None = None
    tool_choice: Any | None = None


class Delta(BaseModel):
    role: Literal["assistant"] | None = None
    content: str | None = None
    tool_calls: list[ToolCall] | None = None


class Choice(BaseModel):
    index: int = 0
    delta: Delta
    finish_reason: str | None = None


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionChunk(BaseModel):
    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int
    model: str
    choices: list[Choice]
    usage: Usage | None = None


class ModelCapabilities(BaseModel):
    tools: bool
    tool_names: list[str]


class ModelInfo(BaseModel):
    id: str
    object: Literal["model"] = "model"
    owned_by: str = "butler"
    x_capabilities: ModelCapabilities | None = Field(default=None, alias="x-capabilities")

    model_config = {"populate_by_name": True}


class ModelsResponse(BaseModel):
    object: Literal["list"] = "list"
    data: list[ModelInfo]


def generate_chunk_id() -> str:
    return f"chatcmpl-{secrets.token_hex(4)}"


def now_ts() -> int:
    return int(time.time())
