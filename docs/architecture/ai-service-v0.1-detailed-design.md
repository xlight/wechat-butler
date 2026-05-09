# WeChat Butler v0.1.0 详细方案设计

## 文档信息

- **版本**: v0.1.0
- **创建日期**: 2026-05-09
- **状态**: 设计中
- **前置文档**: [架构设计](ai-service-v0.1.md)、[技术选型](../features/ai-service-tech-decisions.md)

---

## 1. 配置系统详细设计

### 1.1 config.yaml 完整结构

```yaml
server:
  host: "0.0.0.0"
  port: 8837
  log_level: "info"           # debug | info | warning | error

llm:
  provider: "openai"          # 默认 provider（用于无显式 provider 的 model）
  api_key: "${OPENAI_API_KEY}"
  base_url: "https://api.openai.com/v1"
  default_model: "gpt-4o"
  max_tokens: 4096            # 单次响应最大 token 数
  temperature: 0.7            # 默认温度
  models:
    - id: "gpt-4o"
      name: "GPT-4o"
      provider: "openai"      # 可省略，使用默认 provider
      # api_key: ...          # 可省略，使用默认 api_key
      # base_url: ...         # 可省略，使用默认 base_url
    - id: "deepseek-chat"
      name: "DeepSeek Chat"
      provider: "deepseek"
      api_key: "${DEEPSEEK_API_KEY}"
      base_url: "https://api.deepseek.com/v1"
    - id: "qwen-plus"
      name: "通义千问 Plus"
      provider: "openai"      # 兼容 OpenAI 格式
      api_key: "${DASHSCOPE_API_KEY}"
      base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"

mcp:
  chatshell_api_url: "http://127.0.0.1:5030/mcp"
  idle_timeout: 300           # 空闲超时秒数，0 表示不断开
  connect_timeout: 10         # 连接超时秒数

auth:
  api_key: "${BUTLER_API_KEY}"

prompts:
  directory: "prompts"        # 自定义 prompt 文件目录
```

### 1.2 Pydantic 配置模型

```python
# config.py

class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8837
    log_level: str = "info"

class ModelConfig(BaseModel):
    id: str                          # 模型 ID（如 "gpt-4o"）
    name: str                        # 显示名称
    provider: str | None = None      # provider，None 则用默认
    api_key: str | None = None       # API Key，None 则用默认
    base_url: str | None = None      # Base URL，None 则用默认

class LLMConfig(BaseModel):
    provider: str = "openai"
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    default_model: str = "gpt-4o"
    max_tokens: int = 4096
    temperature: float = 0.7
    models: list[ModelConfig] = []

class MCPConfig(BaseModel):
    chatshell_api_url: str = "http://127.0.0.1:5030/mcp"
    idle_timeout: int = 300
    connect_timeout: int = 10

class AuthConfig(BaseModel):
    api_key: str = ""

class PromptsConfig(BaseModel):
    directory: str = "prompts"

class AppConfig(BaseModel):
    server: ServerConfig = ServerConfig()
    llm: LLMConfig = LLMConfig()
    mcp: MCPConfig = MCPConfig()
    auth: AuthConfig = AuthConfig()
    prompts: PromptsConfig = PromptsConfig()
```

### 1.3 环境变量插值

```python
import re
import os

_ENV_PATTERN = re.compile(r"\$\{(\w+)\}")

def interpolate_env(value: str) -> str:
    """将 ${ENV_VAR} 替换为环境变量值，未设置则保留原样"""
    def _replace(match):
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))
    return _ENV_PATTERN.sub(_replace, value)
```

递归遍历 YAML dict，对所有字符串值调用 `interpolate_env()`。

### 1.4 配置重载

不做文件 watch。通过 `POST /api/v1/ai/config` 触发：

```python
class ConfigManager:
    def __init__(self, config_path: str):
        self._path = config_path
        self.config: AppConfig = self._load()

    def _load(self) -> AppConfig:
        raw = yaml.safe_load(Path(self._path).read_text())
        raw = self._interpolate(raw)
        return AppConfig(**raw)

    def reload(self) -> AppConfig:
        """重新从文件加载配置"""
        self.config = self._load()
        return self.config

    def update_llm(self, updates: dict) -> AppConfig:
        """运行时更新 LLM 配置（不写文件）"""
        # 合并 updates 到 self.config.llm
        ...
        return self.config
```

---

## 2. LLM 代理层详细设计

### 2.1 litellm model prefix 路由

litellm 使用 `provider/model` 格式路由请求。butler 配置中的 model id 需要转换为 litellm 格式：

```
配置 model id    →  litellm model     →  实际请求
─────────────────────────────────────────────────
gpt-4o           →  openai/gpt-4o     →  OpenAI API
deepseek-chat    →  deepseek/deepseek-chat →  DeepSeek API
qwen-plus        →  openai/qwen-plus  →  DashScope API (OpenAI 兼容)
```

### 2.2 router.py 设计

```python
# llm/router.py

import litellm

class LLMRouter:
    def __init__(self, config: LLMConfig):
        self._config = config
        self._model_map: dict[str, ModelConfig] = {}
        for m in config.models:
            self._model_map[m.id] = m

    def resolve_model(self, model_id: str | None) -> tuple[str, str, str | None, str | None]:
        """解析 model id → (litellm_model, provider, api_key, base_url)"""
        model_id = model_id or self._config.default_model
        model_cfg = self._model_map.get(model_id)

        if model_cfg:
            provider = model_cfg.provider or self._config.provider
            api_key = model_cfg.api_key or self._config.api_key
            base_url = model_cfg.base_url or self._config.base_url
        else:
            provider = self._config.provider
            api_key = self._config.api_key
            base_url = self._config.base_url

        # litellm model prefix
        litellm_model = f"{provider}/{model_id}"
        return litellm_model, provider, api_key, base_url

    def get_tools_schema(self, mcp_tools: list) -> list[dict]:
        """将 MCP Tool 对象转换为 OpenAI function calling 格式"""
        tools = []
        for tool in mcp_tools:
            tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema or {"type": "object", "properties": {}},
                }
            })
        return tools
```

### 2.3 MCP Tool → OpenAI Tool 转换

MCP SDK 的 `Tool` 对象有 `name`、`description`、`inputSchema`（JSON Schema）。直接映射到 OpenAI function calling 格式：

```
MCP Tool                          OpenAI Tool
─────────────────────────────────────────────────
name: "query_chat_log"     →     function.name: "query_chat_log"
description: "检索历史..."  →     function.description: "检索历史..."
inputSchema: {              →     function.parameters: {
  "type": "object",                "type": "object",
  "properties": {                  "properties": {
    "time": {...},                   "time": {...},
    "talker": {...},                 "talker": {...},
    ...                              ...
  },                               },
  "required": ["time","talker"]     "required": ["time","talker"]
}                                }
```

chatshell-api 的 6 个工具的完整 schema：

| 工具 | 必填参数 | 可选参数 | 说明 |
|------|----------|----------|------|
| `query_contact` | — | keyword | 查询联系人 |
| `query_chat_room` | — | keyword | 查询群聊 |
| `query_recent_chat` | — | — | 最近会话列表 |
| `query_chat_log` | time, talker | sender, keyword | 聊天记录（含多步查询指引） |
| `current_time` | — | — | 当前时间 |
| `query_diary` | — | hours, talker | 最近 N 小时我参与的会话 |

**注意**：`query_chat_log` 的 description 非常长（含多步查询流程指引），这是有意为之 — 引导 LLM 按正确流程使用工具。

---

## 3. MCP 客户端详细设计

### 3.1 生命周期状态机

```
                    ┌──────────┐
                    │ DISCONN- │
          startup   │ ECTED    │
          fail ───▶ │          │
                    └────┬─────┘
                         │ connect()
                         ▼
                    ┌──────────┐
                    │ CONNECT- │
          connect   │ ING      │
          start ───▶│          │
                    └────┬─────┘
                         │ initialize() + list_tools()
                         ▼
                    ┌──────────┐  idle timeout
                    │ CONNECT- │ ──────────────▶ DISCONNECTED
                    │ ED       │
                    │          │ ◀──────────────
                    └──────────┘   call_tool() triggers
                                   auto-reconnect
```

### 3.2 MCPClient 类设计

```python
# mcp/client.py

from contextlib import AsyncExitStack
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import Tool

class MCPClient:
    def __init__(self, url: str, idle_timeout: int = 300, connect_timeout: int = 10):
        self._url = url
        self._idle_timeout = idle_timeout
        self._connect_timeout = connect_timeout

        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._tools: list[Tool] = []
        self._last_used: float = 0
        self._connected: bool = False
        self._watcher_task: asyncio.Task | None = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def tools(self) -> list[Tool]:
        return self._tools

    async def connect(self) -> None:
        """建立 MCP 连接，初始化会话，发现工具"""
        try:
            self._stack = AsyncExitStack()
            transport = await asyncio.wait_for(
                self._stack.enter_async_context(
                    streamablehttp_client(self._url)
                ),
                timeout=self._connect_timeout,
            )
            read_stream, write_stream, _ = transport
            self._session = await self._stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await self._session.initialize()

            # 发现工具
            result = await self._session.list_tools()
            self._tools = result.tools
            self._connected = True
            self._last_used = time.monotonic()

            # 启动空闲监控
            if self._idle_timeout > 0:
                self._watcher_task = asyncio.create_task(self._idle_watcher())

        except Exception as e:
            await self._cleanup()
            logger.warning(f"MCP connection failed: {e}")

    async def disconnect(self) -> None:
        """断开 MCP 连接"""
        await self._cleanup()

    async def call_tool(self, name: str, arguments: dict) -> str:
        """调用 MCP 工具（按需重连）"""
        if not self._connected:
            await self.connect()
            if not self._connected:
                raise MCPDisconnectedError("MCP server unavailable")

        self._last_used = time.monotonic()
        result = await self._session.call_tool(name, arguments)

        # 提取文本结果
        if result.content:
            texts = [c.text for c in result.content if hasattr(c, "text")]
            return "\n".join(texts)
        return ""

    async def _idle_watcher(self) -> None:
        """空闲超时自动断开"""
        try:
            while self._connected:
                await asyncio.sleep(30)  # 每 30 秒检查一次
                if self._connected and \
                   time.monotonic() - self._last_used > self._idle_timeout:
                    logger.info("MCP idle timeout, disconnecting")
                    await self.disconnect()
                    break
        except asyncio.CancelledError:
            pass

    async def _cleanup(self) -> None:
        """清理连接资源"""
        if self._watcher_task:
            self._watcher_task.cancel()
            self._watcher_task = None
        if self._stack:
            await self._stack.aclose()
            self._stack = None
        self._session = None
        self._tools = []
        self._connected = False
```

---

## 4. AI Chat 服务详细设计

### 4.1 tool_call 循环核心算法

这是整个系统最复杂的部分。关键挑战：**streaming 模式下 tool_call 的 chunks 需要累积拼接**。

```
LLM streaming response 中的 tool_call chunks:

chunk 1: delta.tool_calls[0] = {index:0, id:"call_abc", function:{name:"query_chat_log", arguments:""}}
chunk 2: delta.tool_calls[0] = {index:0, id:null,     function:{name:null,             arguments:'{"tim'}}
chunk 3: delta.tool_calls[0] = {index:0, id:null,     function:{name:null,             arguments:'e":"20'}}
chunk 4: delta.tool_calls[0] = {index:0, id:null,     function:{name:null,             arguments:'23-04-0'}}
chunk 5: delta.tool_calls[0] = {index:0, id:null,     function:{name:null,             arguments:'1~2023'}}
chunk 6: delta.tool_calls[0] = {index:0, id:null,     function:{name:null,             arguments:'-04-30"}'}}
chunk 7: finish_reason = "tool_calls"

累积结果:
tool_calls_acc[0] = {
    "id": "call_abc",
    "name": "query_chat_log",
    "arguments": '{"time":"2023-04-01~2023-04-30"}'
}
```

### 4.2 chat.py 设计

```python
# ai/chat.py

import json
import litellm
from sse_starlette import EventSourceResponse

MAX_TOOL_ROUNDS = 10

class ChatService:
    def __init__(self, config: LLMConfig, router: LLMRouter, mcp: MCPClient, prompts: PromptService):
        self._config = config
        self._router = router
        self._mcp = mcp
        self._prompts = prompts

    async def chat(self, request: ChatRequest) -> EventSourceResponse:
        """处理 AI 对话请求，返回 SSE 流"""
        async def event_stream():
            async for event in self._run_chat(request):
                yield event
        return EventSourceResponse(event_stream())

    async def _run_chat(self, request: ChatRequest) -> AsyncIterator[dict]:
        """核心 chat 逻辑，yield SSE 事件 dict"""
        # 1. 构造 messages
        messages = await self._build_messages(request)

        # 2. 获取 tools（MCP 已连接时）
        tools = None
        if self._mcp.is_connected and self._mcp.tools:
            tools = self._router.get_tools_schema(self._mcp.tools)

        # 3. 解析 model
        model_id = request.model or self._config.default_model
        litellm_model, _, api_key, base_url = self._router.resolve_model(model_id)

        # 4. tool_call 循环
        for round_num in range(MAX_TOOL_ROUNDS):
            # 调用 LLM
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

            # 处理 streaming response
            content_parts = []
            tool_calls_acc: dict[int, dict] = {}
            finish_reason = None
            usage = None

            async for chunk in response:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta

                # 文本内容
                if delta.content:
                    content_parts.append(delta.content)
                    yield {"event": "content", "data": json.dumps({"content": delta.content})}

                # tool_call chunks 累积
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

                # finish_reason 和 usage
                if chunk.choices[0].finish_reason:
                    finish_reason = chunk.choices[0].finish_reason
                if hasattr(chunk, "usage") and chunk.usage:
                    usage = chunk.usage

            # 无 tool_calls → 最终响应
            if not tool_calls_acc:
                yield {"event": "done", "data": json.dumps({
                    "usage": {"prompt_tokens": usage.prompt_tokens, "completion_tokens": usage.completion_tokens} if usage else {}
                })}
                return

            # 有 tool_calls → 执行工具
            # 追加 assistant message（含 tool_calls）到 messages
            assistant_msg = {
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

            # 逐个执行 tool_call
            for acc in tool_calls_acc.values():
                tool_name = acc["name"]
                try:
                    tool_args = json.loads(acc["arguments"])
                except json.JSONDecodeError:
                    tool_args = {}

                # yield tool_call 事件
                yield {"event": "tool_call", "data": json.dumps({
                    "tool": tool_name, "args": tool_args
                })}

                # 调用 MCP 工具
                try:
                    result = await self._mcp.call_tool(tool_name, tool_args)
                except Exception as e:
                    result = f"Error: {str(e)}"

                # yield tool_result 事件
                yield {"event": "tool_result", "data": json.dumps({
                    "tool": tool_name, "result": result
                })}

                # 追加 tool result message
                messages.append({
                    "role": "tool",
                    "tool_call_id": acc["id"],
                    "content": result,
                })

        # 达到最大轮次
        yield {"event": "error", "data": json.dumps({
            "type": "max_iterations", "message": f"Reached max tool call rounds ({MAX_TOOL_ROUNDS})"
        })}
        yield {"event": "done", "data": json.dumps({"usage": {}})}

    async def _build_messages(self, request: ChatRequest) -> list[dict]:
        """构造 LLM messages 数组"""
        messages = list(request.messages)  # 前端传的完整历史

        # context 注入
        if request.context:
            ctx_msg = self._format_context(request.context)
            messages.insert(0, {"role": "system", "content": ctx_msg})

        # prompt 模板注入
        if request.prompt_id:
            prompt = await self._prompts.get(request.prompt_id)
            if prompt:
                content = self._prompts.substitute(prompt.content, request.variables or {})
                messages.insert(0, {"role": "system", "content": content})

        return messages

    def _format_context(self, ctx: Context) -> str:
        """将 context 对象格式化为 system message"""
        parts = ["以下是当前对话的上下文信息："]
        if ctx.session_name:
            parts.append(f"- 会话：{ctx.session_name}")
        if ctx.message_count:
            parts.append(f"- 消息数量：{ctx.message_count}")
        if ctx.time_range:
            parts.append(f"- 时间范围：{ctx.time_range}")
        if ctx.content:
            parts.append(f"- 内容摘要：\n{ctx.content}")
        return "\n".join(parts)
```

### 4.3 SSE 事件格式

`sse-starlette` 的 `EventSourceResponse` 接受 async generator，每个 yield 是一个 dict：

```python
# 标准用法
yield {"event": "content", "data": '{"content": "chunk text"}'}
# 等效于 SSE 输出：
# event: content
# data: {"content": "chunk text"}
```

### 4.4 请求/响应模型

```python
# api/ai_routes.py 中的 Pydantic 模型

class Context(BaseModel):
    session_name: str | None = None
    message_count: int | None = None
    time_range: str | None = None
    content: str | None = None

class ChatRequest(BaseModel):
    messages: list[dict]          # OpenAI 格式消息列表
    model: str | None = None      # 模型 ID
    context: Context | None = None
    prompt_id: str | None = None
    variables: dict[str, str] | None = None
```

---

## 5. Prompt 管理详细设计

### 5.1 内置模板

```python
# ai/prompts.py

BUILTIN_PROMPTS = [
    Prompt(
        id="builtin-group-summary",
        name="群聊总结",
        description="总结群聊讨论的要点和关键信息",
        content="请总结以下群聊讨论的要点，包括：\n1. 主要话题\n2. 关键决策\n3. 待办事项\n\n群聊内容：\n{content}",
        variables=["content"],
        builtin=True,
    ),
    Prompt(
        id="builtin-todo-extract",
        name="待办提取",
        description="从聊天记录中提取待办事项",
        content="从以下聊天记录中提取所有待办事项，标注负责人和截止时间（如有）：\n\n{content}",
        variables=["content"],
        builtin=True,
    ),
    Prompt(
        id="builtin-topic-analysis",
        name="话题分析",
        description="分析聊天中的主要话题和讨论趋势",
        content="分析以下聊天记录中的主要话题，统计每个话题的讨论频率和参与人：\n\n{content}",
        variables=["content"],
        builtin=True,
    ),
    Prompt(
        id="builtin-sentiment-analysis",
        name="情绪分析",
        description="分析聊天中的情绪倾向",
        content="分析以下聊天记录中各参与者的情绪倾向（积极/消极/中性），标注情绪变化的关键节点：\n\n{content}",
        variables=["content"],
        builtin=True,
    ),
    Prompt(
        id="builtin-person-profile",
        name="人物画像",
        description="根据聊天记录生成人物画像",
        content="根据以下聊天记录，为 {sessionName} 生成人物画像，包括：\n1. 沟通风格\n2. 关注领域\n3. 活跃时间\n4. 关系网络\n\n聊天记录：\n{content}",
        variables=["sessionName", "content"],
        builtin=True,
    ),
]
```

### 5.2 自定义 Prompt 存储

YAML 文件格式（`prompts/` 目录下）：

```yaml
# prompts/my-template.yaml
id: "custom-weekly-report"
name: "周报生成"
description: "根据群聊内容生成周报"
content: |
  根据 {sessionName} 本周的讨论，生成周报：
  1. 本周完成事项
  2. 进行中的工作
  3. 下周计划

  讨论内容：
  {content}
```

### 5.3 变量替换

```python
import re

_VAR_PATTERN = re.compile(r"\{(\w+)\}")

def substitute(template: str, variables: dict[str, str]) -> str:
    """替换 {var} 占位符，缺失变量保留原样"""
    def _replace(match):
        var_name = match.group(1)
        return variables.get(var_name, match.group(0))
    return _VAR_PATTERN.sub(_replace, template)
```

---

## 6. API 端点详细设计

### 6.1 路由注册

```python
# api/ai_routes.py

from fastapi import APIRouter, Depends, Request
from sse_starlette import EventSourceResponse

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

@router.post("/chat")
async def chat(request: ChatRequest, chat_service: ChatService = Depends(get_chat_service)):
    return await chat_service.chat(request)

@router.get("/models")
async def list_models(router: LLMRouter = Depends(get_llm_router)):
    return {"models": [...], "default_model": ...}

@router.get("/status")
async def status(mcp: MCPClient = Depends(get_mcp_client)):
    return {...}

@router.get("/config")
async def get_config(config: ConfigManager = Depends(get_config)):
    return config.get_masked()

@router.post("/config")
async def update_config(updates: ConfigUpdateRequest, config: ConfigManager = Depends(get_config)):
    return config.update_llm(updates)

@router.get("/prompts")
async def list_prompts(prompts: PromptService = Depends(get_prompt_service)):
    return {"prompts": prompts.list_all()}

@router.post("/prompts")
async def create_prompt(prompt: PromptCreateRequest, prompts: PromptService = Depends(...)):
    return prompts.create(prompt)

@router.put("/prompts/{prompt_id}")
async def update_prompt(prompt_id: str, prompt: PromptUpdateRequest, ...):
    return prompts.update(prompt_id, prompt)

@router.delete("/prompts/{prompt_id}")
async def delete_prompt(prompt_id: str, ...):
    return prompts.delete(prompt_id)
```

### 6.2 认证中间件

```python
# api/middleware.py

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class APIKeyMiddleware(BaseHTTPMiddleware):
    # 不需要认证的路径
    PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request, call_next):
        # 公开路径放行
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)

        # 检查 API Key
        api_key = request.headers.get("X-Butler-API-Key")
        if not api_key or api_key != self._expected_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"},
            )

        return await call_next(request)
```

### 6.3 依赖注入

使用 FastAPI 的 `Depends` + `app.state` 模式：

```python
# server.py

from fastapi import FastAPI, Request

def create_app(config: ConfigManager) -> FastAPI:
    app = FastAPI(title="WeChat Butler", version="0.1.0", lifespan=lifespan)

    # 将服务实例挂到 app.state
    app.state.config = config
    app.state.mcp_client = MCPClient(...)
    app.state.llm_router = LLMRouter(config.config.llm)
    app.state.chat_service = ChatService(...)
    app.state.prompt_service = PromptService(...)

    # 依赖注入函数
    def get_config(request: Request) -> ConfigManager:
        return request.app.state.config

    # ... 其他 getter

    # 注册路由和中间件
    app.include_router(ai_routes.router)
    app.add_middleware(APIKeyMiddleware, expected_key=config.config.auth.api_key)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)

    return app
```

---

## 7. Server 和入口点详细设计

### 7.1 lifespan 事件

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: startup 和 shutdown"""
    config = app.state.config
    mcp = app.state.mcp_client

    # Startup
    logger.info(f"WeChat Butler v0.1.0 starting...")
    logger.info(f"Config loaded from {config._path}")

    # 尝试连接 MCP（失败不阻塞启动）
    await mcp.connect()
    if mcp.is_connected:
        logger.info(f"MCP connected to {config.config.mcp.chatshell_api_url} ({len(mcp.tools)} tools)")
    else:
        logger.warning(f"MCP connection failed, AI Chat will run in no-tool mode")

    yield  # 应用运行中

    # Shutdown
    logger.info("Shutting down...")
    await mcp.disconnect()
    logger.info("MCP client disconnected")
```

### 7.2 main.py CLI 入口

```python
# main.py

import argparse
import uvicorn

def main():
    parser = argparse.ArgumentParser(description="WeChat Butler AI Service")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument("--port", type=int, default=None, help="Override server port")
    parser.add_argument("--host", default=None, help="Override server host")
    args = parser.parse_args()

    # 加载配置
    config = ConfigManager(args.config)

    # 命令行参数覆盖
    host = args.host or config.config.server.host
    port = args.port or config.config.server.port

    # 创建 app
    app = create_app(config)

    # 启动
    uvicorn.run(app, host=host, port=port, log_level=config.config.server.log_level)

if __name__ == "__main__":
    main()
```

### 7.3 /health 端点

```python
@router.get("/health")
async def health():
    return {"status": "healthy", "version": "0.1.0"}
```

---

## 8. 完整请求流程示例

### 示例：用户问"总结今天工作群的讨论"

```
1. 前端发送:
   POST /api/v1/ai/chat
   X-Butler-API-Key: xxx
   {
     "messages": [{"role": "user", "content": "总结今天工作群的讨论"}],
     "model": "deepseek-chat"
   }

2. butler 处理:
   ├── 解析 model: deepseek-chat → litellm model: deepseek/deepseek-chat
   ├── 获取 MCP tools: 6 个工具
   ├── Round 1: litellm.acompletion(messages, tools, stream=True)
   │
   │  LLM streaming response:
   │  → delta.content: "让我"        → SSE: event:content data:{"content":"让我"}
   │  → delta.content: "查询一下"    → SSE: event:content data:{"content":"查询一下"}
   │  → delta.tool_calls[0]: {id:"call_1", name:"current_time", args:""}
   │  → delta.tool_calls[0]: {args:"{}"}
   │  → finish_reason: "tool_calls"
   │
   ├── 累积 tool_calls: [{id:"call_1", name:"current_time", arguments:"{}"}]
   ├── SSE: event:tool_call data:{"tool":"current_time","args":{}}
   ├── MCP call_tool("current_time", {}) → "2026-05-09T15:30:00+08:00"
   ├── SSE: event:tool_result data:{"tool":"current_time","result":"2026-05-09T15:30:00+08:00"}
   ├── 追加 assistant msg + tool result msg 到 messages
   │
   ├── Round 2: litellm.acompletion(messages, tools, stream=True)
   │
   │  LLM streaming response:
   │  → delta.tool_calls[0]: {id:"call_2", name:"query_chat_log", args:""}
   │  → delta.tool_calls[0]: {args:'{"tim'}
   │  → delta.tool_calls[0]: {args:'e":"2026'}
   │  → ... (arguments chunks)
   │  → finish_reason: "tool_calls"
   │
   ├── 累积 tool_calls: [{id:"call_2", name:"query_chat_log", arguments:'{"time":"2026-05-09","talker":"工作群"}'}]
   ├── SSE: event:tool_call data:{"tool":"query_chat_log","args":{"time":"2026-05-09","talker":"工作群"}}
   ├── MCP call_tool("query_chat_log", {...}) → "张三 09:15\n早上好\n李四 09:20\n收到..."
   ├── SSE: event:tool_result data:{"tool":"query_chat_log","result":"张三 09:15\n早上好\n..."}
   ├── 追加 messages
   │
   ├── Round 3: litellm.acompletion(messages, tools, stream=True)
   │
   │  LLM streaming response (最终文本):
   │  → delta.content: "今天工作群的讨论总结：\n1. 早上张三发了问候"
   │  → delta.content: "\n2. 李四确认收到"
   │  → delta.content: "\n3. ..."
   │  → finish_reason: "stop"
   │
   └── SSE: event:done data:{"usage":{"prompt_tokens":500,"completion_tokens":150}}

3. 前端收到完整 SSE 流:
   event: content     → {"content": "让我"}
   event: content     → {"content": "查询一下"}
   event: tool_call   → {"tool": "current_time", "args": {}}
   event: tool_result → {"tool": "current_time", "result": "2026-05-09T15:30:00+08:00"}
   event: tool_call   → {"tool": "query_chat_log", "args": {"time":"2026-05-09","talker":"工作群"}}
   event: tool_result → {"tool": "query_chat_log", "result": "张三 09:15\n早上好\n..."}
   event: content     → {"content": "今天工作群的讨论总结：\n1. 早上张三发了问候"}
   event: content     → {"content": "\n2. 李四确认收到"}
   event: content     → {"content": "\n3. ..."}
   event: done        → {"usage": {"prompt_tokens": 500, "completion_tokens": 150}}
```

---

## 9. 错误处理详细设计

### 9.1 错误类型

```python
class ButlerError(Exception):
    """Base error"""

class MCPDisconnectedError(ButlerError):
    """MCP server 不可用"""

class LLMError(ButlerError):
    """LLM 调用失败"""

class ConfigError(ButlerError):
    """配置错误"""
```

### 9.2 各场景处理

| 场景 | 触发点 | 处理 | SSE 事件 |
|------|--------|------|----------|
| MCP 启动时不可用 | `lifespan startup` | 标记 disconnected，正常启动 | — |
| MCP 调用时不可用 | `call_tool()` | 自动重连，重连失败则抛异常 | `error: {"type": "mcp_error", "message": "..."}` |
| MCP 工具调用失败 | `call_tool()` | 返回错误文本给 LLM | `tool_result: {"tool": "name", "result": "Error: ..."}` |
| LLM API Key 无效 | `acompletion()` | litellm 抛 AuthenticationError | `error: {"type": "auth_error", "message": "..."}` + `done` |
| LLM 限流 | `acompletion()` | litellm 抛 RateLimitError | `error: {"type": "rate_limit", "message": "..."}` + `done` |
| LLM 超时 | `acompletion()` | litellm 抛 Timeout | `error: {"type": "timeout", "message": "..."}` + `done` |
| tool_call 循环达上限 | `_run_chat()` | 返回已有内容 | `error: {"type": "max_iterations", "message": "..."}` + `done` |
| 配置文件格式错误 | `ConfigManager._load()` | 启动失败，打印错误 | — |

### 9.3 chat.py 中的错误捕获

```python
async def _run_chat(self, request):
    try:
        # ... tool_call loop
    except litellm.AuthenticationError as e:
        yield {"event": "error", "data": json.dumps({"type": "auth_error", "message": str(e)})}
        yield {"event": "done", "data": json.dumps({"usage": {}})}
    except litellm.RateLimitError as e:
        yield {"event": "error", "data": json.dumps({"type": "rate_limit", "message": str(e)})}
        yield {"event": "done", "data": json.dumps({"usage": {}})}
    except litellm.Timeout as e:
        yield {"event": "error", "data": json.dumps({"type": "timeout", "message": str(e)})}
        yield {"event": "done", "data": json.dumps({"usage": {}})}
    except Exception as e:
        logger.exception("Unexpected error in chat")
        yield {"event": "error", "data": json.dumps({"type": "internal_error", "message": str(e)})}
        yield {"event": "done", "data": json.dumps({"usage": {}})}
```

---

## 10. API Key 脱敏

```python
def mask_api_key(key: str) -> str:
    """脱敏 API Key: sk-abc123xyz → sk-abc...xyz"""
    if not key or len(key) < 8:
        return "***"
    return f"{key[:5]}...{key[-3:]}"
```

- 日志中所有 API Key 输出使用 `mask_api_key()`
- `GET /api/v1/ai/config` 响应中 API Key 使用 `mask_api_key()`
- litellm 自带 API Key 脱敏日志功能（`litellm.log_level = "INFO"`）

---

## 11. 修订后的任务清单

基于 litellm 决策，原 tasks.md 需要修订：

### 原任务 → 修订

| 原任务 | 修订 |
|--------|------|
| 1.2 pyproject.toml 依赖含 httpx | 改为含 litellm（httpx 由 litellm 间接引入） |
| 3.1 llm/provider.py abstract base | **删除** — litellm 统一处理 |
| 3.2 llm/openai.py | **删除** — litellm 统一处理 |
| 3.3 llm/anthropic.py | **删除** — v0.1.0 不支持 |
| 3.4 llm/router.py model-to-provider | **简化** — 只做 litellm model prefix 路由 |
| 3.5 streaming response forwarding | **简化** — litellm 已处理 SSE 解析，只需 async for chunk |
| 3.6 API key masking | 保留，但 litellm 自带部分脱敏 |
| 4.2 connect on startup | 修订为：尝试连接，失败不阻塞启动 |
| 4.2 auto-reconnect | 修订为：空闲断开 + 按需重连 |
| 2.5 config hot-reload watch | **删除** — 改为 API 触发重载 |

### 简化后的任务清单

```
1. Project Setup (6 tasks — 不变)
2. Configuration System (4 tasks — 删除 2.5 hot-reload watch)
3. LLM Proxy Layer (2 tasks — 只需 router.py + API key masking)
4. MCP Client (5 tasks — 修订 4.2 生命周期)
5. AI Chat Service (6 tasks — 不变)
6. Prompt Management (4 tasks — 不变)
7. API Endpoints (8 tasks — 不变)
8. Server and Entry Point (5 tasks — 不变)

总计: 40 tasks (原 45，减少 5 个)
```
