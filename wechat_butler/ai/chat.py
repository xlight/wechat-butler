import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import litellm

from wechat_butler.config import (
    AgentModesConfig,
    LLMConfig,
    SafetyConfig,
)
from wechat_butler.llm.router import LLMRouter, ModelNotFoundError
from wechat_butler.mcp_client.client import MCPClient, MCPDisconnectedError
from wechat_butler.openai_compat.errors import (
    ErrorCode,
    ErrorType,
    error_sse_event,
)
from wechat_butler.openai_compat.schemas import (
    ChatCompletionChunk,
    ChatCompletionRequest,
    Choice,
    Delta,
    Usage,
    generate_chunk_id,
    now_ts,
)

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 10

_SEND_TOOL_HINTS = ("send_message", "sendmsg", "send")


class OpenAIChatService:
    def __init__(
        self,
        llm_config: LLMConfig,
        router: LLMRouter,
        mcp: MCPClient,
        safety: SafetyConfig,
        agent_modes: AgentModesConfig,
    ):
        self._llm_config = llm_config
        self._router = router
        self._mcp = mcp
        self._safety = safety
        self._agent_modes = agent_modes

    async def stream(
        self,
        request: ChatCompletionRequest,
        *,
        x_mode: str | None = None,
    ) -> AsyncIterator[str]:
        chunk_id = generate_chunk_id()
        created = now_ts()
        include_tool_results = bool(
            request.stream_options and request.stream_options.x_include_tool_results
        )
        include_usage = bool(
            request.stream_options and request.stream_options.include_usage
        )

        mode_obj = self._resolve_mode(x_mode)
        model_override = None
        max_tokens_override = None
        if mode_obj is not None and getattr(mode_obj, "enabled", True):
            if mode_obj.model:
                model_override = mode_obj.model
            if getattr(mode_obj, "max_tokens", None):
                max_tokens_override = mode_obj.max_tokens

        effective_model = request.model or model_override

        try:
            litellm_model, api_key, base_url, provider_model_id = self._router.resolve_model(
                effective_model
            )
        except ModelNotFoundError as e:
            yield error_sse_event(
                message=str(e),
                error_type=ErrorType.INVALID_REQUEST,
                code=ErrorCode.MODEL_NOT_FOUND,
            )
            yield "data: [DONE]\n\n"
            return

        messages = self._build_messages(request, x_mode, provider_model_id)
        tools = self._build_tools_schema()
        usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        async for sse_line in self._run_loop(
            chunk_id=chunk_id,
            created=created,
            model=provider_model_id,
            messages=messages,
            tools=tools,
            litellm_model=litellm_model,
            api_key=api_key,
            api_base=base_url,
            request=request,
            include_tool_results=include_tool_results,
            include_usage=include_usage,
            usage_total=usage_total,
            max_tokens_override=max_tokens_override,
        ):
            yield sse_line

        if include_usage and (usage_total["prompt_tokens"] or usage_total["completion_tokens"]):
            usage_chunk = ChatCompletionChunk(
                id=chunk_id,
                created=created,
                model=provider_model_id,
                choices=[],
                usage=Usage(**usage_total),
            )
            yield f"data: {usage_chunk.model_dump_json(exclude_none=True)}\n\n"

        yield "data: [DONE]\n\n"

    def _build_messages(
        self,
        request: ChatCompletionRequest,
        x_mode: str | None,
        fallback_model: str,
    ) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [m.model_dump(exclude_none=True) for m in request.messages]
        mode_obj = self._resolve_mode(x_mode)
        system_prompt_override: str | None = None
        if mode_obj is not None and getattr(mode_obj, "enabled", True):
            if mode_obj.system_prompt:
                system_prompt_override = mode_obj.system_prompt

        if system_prompt_override:
            if messages and messages[0].get("role") == "system":
                existing = messages[0].get("content") or ""
                messages[0]["content"] = f"{system_prompt_override}\n\n{existing}"
            else:
                messages.insert(0, {"role": "system", "content": system_prompt_override})

        return messages

    def _resolve_mode(self, x_mode: str | None):
        if not x_mode:
            return None
        return {
            "observer": self._agent_modes.observer,
            "mention": self._agent_modes.mention,
            "user_actions": self._agent_modes.user_actions,
        }.get(x_mode)

    def _build_tools_schema(self) -> list[dict[str, Any]] | None:
        if not self._mcp.is_connected or not self._mcp.tools:
            return None
        return self._router.get_tools_schema(self._mcp.tools)

    async def _run_loop(
        self,
        *,
        chunk_id: str,
        created: int,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        litellm_model: str,
        api_key: str | None,
        api_base: str | None,
        request: ChatCompletionRequest,
        include_tool_results: bool,
        include_usage: bool,
        usage_total: dict[str, int],
        max_tokens_override: int | None = None,
    ) -> AsyncIterator[str]:
        last_finish_reason: str | None = None
        last_round_had_tool_calls = False
        max_iter_seen = False

        effective_max_tokens = (
            request.max_tokens or max_tokens_override or self._llm_config.max_tokens
        )

        for round_index in range(MAX_TOOL_ROUNDS):
            try:
                response = await litellm.acompletion(
                    model=litellm_model,
                    messages=messages,
                    tools=tools or None,
                    stream=True,
                    api_key=api_key,
                    api_base=api_base,
                    max_tokens=effective_max_tokens,
                    temperature=(
                        request.temperature
                        if request.temperature is not None
                        else self._llm_config.temperature
                    ),
                    top_p=request.top_p,
                    frequency_penalty=request.frequency_penalty,
                    presence_penalty=request.presence_penalty,
                    stop=request.stop,
                    stream_options={"include_usage": include_usage} if include_usage else None,
                )
            except litellm.AuthenticationError as e:
                yield error_sse_event(
                    message=str(e),
                    error_type=ErrorType.AUTHENTICATION,
                    code=ErrorCode.INVALID_API_KEY,
                )
                return
            except litellm.RateLimitError as e:
                yield error_sse_event(
                    message=str(e),
                    error_type=ErrorType.RATE_LIMIT,
                    code=ErrorCode.RATE_LIMIT_EXCEEDED,
                )
                return
            except litellm.Timeout as e:
                yield error_sse_event(
                    message=str(e),
                    error_type=ErrorType.SERVER,
                    code=ErrorCode.LLM_TIMEOUT,
                )
                return
            except Exception as e:
                logger.exception("LLM call failed in tool-call loop")
                yield error_sse_event(
                    message=str(e),
                    error_type=ErrorType.SERVER,
                    code=ErrorCode.LLM_ERROR,
                )
                return

            tool_calls_acc: dict[int, dict[str, Any]] = {}
            finish_reason: str | None = None
            round_emitted_role = round_index == 0

            async for litellm_chunk in response:
                if litellm_chunk.usage:
                    usage_total["prompt_tokens"] += getattr(litellm_chunk.usage, "prompt_tokens", 0) or 0
                    usage_total["completion_tokens"] += getattr(
                        litellm_chunk.usage, "completion_tokens", 0
                    ) or 0
                    usage_total["total_tokens"] += getattr(litellm_chunk.usage, "total_tokens", 0) or 0

                if not litellm_chunk.choices:
                    continue
                choice = litellm_chunk.choices[0]
                delta = choice.delta

                if include_tool_results:
                    payload = litellm_chunk.model_dump(exclude_none=True)
                    payload["id"] = chunk_id
                    payload["created"] = created
                    payload["model"] = model
                    payload["object"] = "chat.completion.chunk"
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                else:
                    if round_emitted_role and delta.role:
                        yield self._sse_chunk(
                            chunk_id, created, model, Choice(delta=Delta(role="assistant"))
                        )
                        round_emitted_role = False
                    if delta.content is not None:
                        yield self._sse_chunk(
                            chunk_id, created, model, Choice(delta=Delta(content=delta.content))
                        )

                if delta.tool_calls:
                    for tc_chunk in delta.tool_calls:
                        idx = tc_chunk.index
                        if idx not in tool_calls_acc:
                            tool_calls_acc[idx] = {
                                "id": "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            }
                        acc = tool_calls_acc[idx]
                        if tc_chunk.id:
                            acc["id"] = tc_chunk.id
                        if tc_chunk.function:
                            if tc_chunk.function.name:
                                acc["function"]["name"] = tc_chunk.function.name
                            if tc_chunk.function.arguments:
                                acc["function"]["arguments"] += tc_chunk.function.arguments

                if choice.finish_reason:
                    finish_reason = choice.finish_reason
                    last_finish_reason = finish_reason

            if not tool_calls_acc:
                yield self._sse_chunk(
                    chunk_id,
                    created,
                    model,
                    Choice(delta=Delta(), finish_reason=last_finish_reason or "stop"),
                )
                return

            last_round_had_tool_calls = True

            for acc in tool_calls_acc.values():
                tool_name = acc["function"]["name"] or ""
                raw_args = acc["function"]["arguments"] or "{}"
                try:
                    tool_args = json.loads(raw_args)
                except json.JSONDecodeError:
                    tool_args = {}

                result_text = await self._execute_tool(tool_name, tool_args)

                if include_tool_results:
                    yield (
                        f'data: {json.dumps({"x-tool-result": {"tool": tool_name, "result": result_text}}, ensure_ascii=False)}\n\n'
                    )

                tool_msg: dict[str, Any] = {
                    "role": "tool",
                    "tool_call_id": acc["id"],
                    "content": result_text,
                }
                messages.append(tool_msg)

            if round_index == MAX_TOOL_ROUNDS - 1:
                max_iter_seen = True
                break

        if max_iter_seen and last_round_had_tool_calls:
            notice = "\n\n[Reached max tool call rounds. Final answer may be incomplete.]"
            yield self._sse_chunk(
                chunk_id,
                created,
                model,
                Choice(delta=Delta(content=notice), finish_reason="stop"),
            )
        else:
            yield self._sse_chunk(
                chunk_id,
                created,
                model,
                Choice(delta=Delta(), finish_reason=last_finish_reason or "stop"),
            )

    async def _execute_tool(self, tool_name: str, tool_args: dict[str, Any]) -> str:
        if self._is_forbidden_send(tool_name, tool_args):
            return "Error: this session is in safety.forbidden_send_sessions and cannot receive messages"

        try:
            if not self._mcp.is_connected:
                await self._mcp.connect()
            if not self._mcp.is_connected:
                return "Error: MCP server unavailable"
            return await self._mcp.call_tool(tool_name, tool_args)
        except MCPDisconnectedError as e:
            return f"Error: MCP disconnected ({e})"
        except Exception as e:
            logger.exception("MCP tool call failed")
            return f"Error: {e}"

    def _is_forbidden_send(self, tool_name: str, tool_args: dict[str, Any]) -> bool:
        if not any(hint in tool_name.lower() for hint in _SEND_TOOL_HINTS):
            return False
        forbidden = set(self._safety.forbidden_send_sessions or [])
        if not forbidden:
            return False
        for key in ("session_id", "to_session", "sessionId", "session", "to"):
            if key in tool_args and str(tool_args[key]) in forbidden:
                return True
        return False

    @staticmethod
    def _sse_chunk(chunk_id: str, created: int, model: str, choice: Choice) -> str:
        chunk = ChatCompletionChunk(
            id=chunk_id, created=created, model=model, choices=[choice]
        )
        return f"data: {chunk.model_dump_json(exclude_none=True)}\n\n"
