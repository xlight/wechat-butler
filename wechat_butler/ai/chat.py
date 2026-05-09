import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import litellm
from pydantic import BaseModel

from wechat_butler.config import LLMConfig
from wechat_butler.llm.router import LLMRouter
from wechat_butler.mcp.client import MCPClient, MCPDisconnectedError

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 10


class Context(BaseModel):
    session_name: str | None = None
    message_count: int | None = None
    time_range: str | None = None
    content: str | None = None


class ChatRequest(BaseModel):
    messages: list[dict]
    model: str | None = None
    context: Context | None = None
    prompt_id: str | None = None
    variables: dict[str, str] | None = None


class ChatService:
    def __init__(self, config: LLMConfig, router: LLMRouter, mcp: MCPClient, prompts: Any):
        self._config = config
        self._router = router
        self._mcp = mcp
        self._prompts = prompts

    async def run_chat(self, request: ChatRequest) -> AsyncIterator[dict]:
        try:
            async for event in self._execute(request):
                yield event
        except litellm.AuthenticationError as e:
            yield _sse_event("error", {"type": "auth_error", "message": str(e)})
            yield _sse_event("done", {"usage": {}})
        except litellm.RateLimitError as e:
            yield _sse_event("error", {"type": "rate_limit", "message": str(e)})
            yield _sse_event("done", {"usage": {}})
        except litellm.Timeout as e:
            yield _sse_event("error", {"type": "timeout", "message": str(e)})
            yield _sse_event("done", {"usage": {}})
        except MCPDisconnectedError as e:
            yield _sse_event("error", {"type": "mcp_error", "message": str(e)})
            yield _sse_event("done", {"usage": {}})
        except Exception as e:
            logger.exception("Unexpected error in chat")
            yield _sse_event("error", {"type": "internal_error", "message": str(e)})
            yield _sse_event("done", {"usage": {}})

    async def _execute(self, request: ChatRequest) -> AsyncIterator[dict]:
        messages = await self._build_messages(request)

        tools = None
        if self._mcp.is_connected and self._mcp.tools:
            tools = self._router.get_tools_schema(self._mcp.tools)

        model_id = request.model or self._config.default_model
        litellm_model, api_key, base_url = self._router.resolve_model(model_id)

        for _ in range(MAX_TOOL_ROUNDS):
            response = await litellm.acompletion(
                model=litellm_model,
                messages=messages,
                tools=tools or None,
                stream=True,
                api_key=api_key,
                api_base=base_url,
                max_tokens=self._config.max_tokens,
                temperature=self._config.temperature,
            )

            content_parts: list[str] = []
            tool_calls_acc: dict[int, dict[str, str]] = {}
            finish_reason = None
            usage = None

            async for chunk in response:
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                delta = choice.delta

                if delta.content:
                    content_parts.append(delta.content)
                    yield _sse_event("content", {"content": delta.content})

                if delta.tool_calls:
                    for tc_chunk in delta.tool_calls:
                        idx = tc_chunk.index
                        if idx not in tool_calls_acc:
                            tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}
                        acc = tool_calls_acc[idx]
                        if tc_chunk.id:
                            acc["id"] = tc_chunk.id
                        if tc_chunk.function:
                            if tc_chunk.function.name:
                                acc["name"] = tc_chunk.function.name
                            if tc_chunk.function.arguments:
                                acc["arguments"] += tc_chunk.function.arguments

                if choice.finish_reason:
                    finish_reason = choice.finish_reason
                if hasattr(chunk, "usage") and chunk.usage:
                    usage = chunk.usage

            if not tool_calls_acc:
                usage_data = {}
                if usage:
                    usage_data = {
                        "prompt_tokens": getattr(usage, "prompt_tokens", 0),
                        "completion_tokens": getattr(usage, "completion_tokens", 0),
                    }
                yield _sse_event("done", {"usage": usage_data})
                return

            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": "".join(content_parts) or None,
                "tool_calls": [
                    {
                        "id": acc["id"],
                        "type": "function",
                        "function": {"name": acc["name"], "arguments": acc["arguments"]},
                    }
                    for acc in tool_calls_acc.values()
                ],
            }
            messages.append(assistant_msg)

            for acc in tool_calls_acc.values():
                tool_name = acc["name"]
                try:
                    tool_args = json.loads(acc["arguments"])
                except json.JSONDecodeError:
                    tool_args = {}

                yield _sse_event("tool_call", {"tool": tool_name, "args": tool_args})

                try:
                    result = await self._mcp.call_tool(tool_name, tool_args)
                except Exception as e:
                    result = f"Error: {e}"

                yield _sse_event("tool_result", {"tool": tool_name, "result": result})

                messages.append({
                    "role": "tool",
                    "tool_call_id": acc["id"],
                    "content": result,
                })

        yield _sse_event("error", {
            "type": "max_iterations",
            "message": f"Reached max tool call rounds ({MAX_TOOL_ROUNDS})",
        })
        yield _sse_event("done", {"usage": {}})

    async def _build_messages(self, request: ChatRequest) -> list[dict]:
        messages = list(request.messages)

        if request.context:
            ctx_msg = self._format_context(request.context)
            messages.insert(0, {"role": "system", "content": ctx_msg})

        if request.prompt_id and self._prompts:
            prompt = self._prompts.get(request.prompt_id)
            if prompt:
                content = self._prompts.substitute(prompt.content, request.variables or {})
                messages.insert(0, {"role": "system", "content": content})

        return messages

    def _format_context(self, ctx: Context) -> str:
        parts = ["Current conversation context:"]
        if ctx.session_name:
            parts.append(f"- Session: {ctx.session_name}")
        if ctx.message_count:
            parts.append(f"- Message count: {ctx.message_count}")
        if ctx.time_range:
            parts.append(f"- Time range: {ctx.time_range}")
        if ctx.content:
            parts.append(f"- Content:\n{ctx.content}")
        return "\n".join(parts)


def _sse_event(event: str, data: dict) -> dict:
    return {"event": event, "data": json.dumps(data, ensure_ascii=False)}
