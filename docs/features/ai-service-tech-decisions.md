# WeChat Butler v0.1.0 技术选型与设计决策

## 文档信息

- **版本**: v0.1.0
- **创建日期**: 2026-05-09
- **状态**: 已确认

---

## 决策总览

| # | 决策 | 选择 | 核心理由 |
|---|------|------|----------|
| 1 | 技术栈 | Python 3.11+ / FastAPI | LLM/MCP 生态 Python 最成熟 |
| 2 | LLM 调用 | litellm | 社区广泛使用，streaming+tool_calls 开箱即用 |
| 3 | MCP 客户端 | 官方 mcp Python SDK | 协议标准一致，减少实现风险 |
| 4 | SSE 响应格式 | 自定义事件类型 | 前端需区分 content/tool_call/tool_result |
| 5 | 配置管理 | YAML + 环境变量 | 可读性好，API Key 不落盘 |
| 6 | 配置重载 | API 触发，不做文件 watch | POST /api/v1/ai/config 已够，减少复杂度 |
| 7 | 认证 | API Key 头部认证 | 本地运行，简单认证足够 |
| 8 | MCP 连接生命周期 | 长连接 + 空闲断开 + 按需重连 | 健壮且高效 |
| 9 | 对话历史 | 前端传完整历史 | butler 无状态，实现简单 |
| 10 | Provider 范围 | v0.1.0 仅 OpenAI-compatible | 覆盖主流需求，Anthropic 后续加 |

---

## 决策详情

### 1. 技术栈：Python 3.11+ / FastAPI

**选择**：Python FastAPI

**替代方案**：
- Go（与 chatshell-api 一致）：性能更好，但 Python 的 LLM/MCP 生态更成熟
- Node.js：与前端技术栈一致，但 Python 在 AI/ML 领域库更丰富

**理由**：butler 的核心是 LLM 交互和 MCP 协议，Python 生态有最成熟的 SDK 支持。FastAPI 的异步特性和自动 OpenAPI 文档也是加分项。

---

### 2. LLM 调用：litellm

**选择**：使用 `litellm` 的 `acompletion()` 作为统一 LLM 接口

**替代方案**：
- httpx 直接调 API（原 design.md 决策）：最小依赖，但需自己解析 SSE chunk、拼接 tool_call delta，工作量大且容易出 bug
- openai Python SDK：官方 SDK，但只覆盖 OpenAI-compatible，未来加 Anthropic 需要两套适配
- litellm：统一多 provider 接口，streaming + tool_calls 开箱即用

**选择 litellm 的理由**：

1. **社区广泛使用** — GitHub 20k+ stars，ragflow、PraisonAI、Life-Agent 等项目在用
2. **streaming + tool_calls 开箱即用** — 不需要自己解析 SSE chunk、拼接 tool_call delta chunks（这部分是最复杂的）
3. **统一接口** — `litellm.acompletion()` 一个函数覆盖 OpenAI / DeepSeek / Anthropic / 100+ provider
4. **未来扩展零成本** — 加 Anthropic 支持只需改 model 前缀为 `anthropic/claude-xxx`，零代码改动
5. **返回格式统一** — 始终为 OpenAI 兼容格式，tool_call 处理逻辑只需写一套
6. **内置能力** — 重试、fallback、rate limit 处理、API Key 脱敏日志

**用法示例**：

```python
import litellm

# 流式 + tool_calls
response = await litellm.acompletion(
    model="deepseek/deepseek-chat",
    messages=messages,
    tools=tool_schemas,
    stream=True,
    api_key="...",
    api_base="...",
)

async for chunk in response:
    delta = chunk.choices[0].delta
    if delta.content:
        # 文本内容
        yield sse_event("content", {"content": delta.content})
    if delta.tool_calls:
        # tool_call chunks（litellm 已处理好拼接）
        ...
```

**v0.1.0 范围**：仅使用 OpenAI-compatible provider（OpenAI、DeepSeek、国产模型）。Anthropic 留到后续版本。

---

### 3. MCP 客户端：官方 mcp Python SDK

**选择**：使用 `mcp` Python 包的 `streamablehttp_client` 连接 chatshell-api `/mcp` 端点

**替代方案**：
- 手写 MCP 客户端：可控但工作量大，协议细节容易出错
- 使用 SSE 传输（/sse + /message）：旧版协议，官方已标记为 deprecated
- fastmcp：更高层封装，但增加额外依赖，且 client 端用法不如官方 SDK 稳定

**理由**：chatshell-api 同时支持 /mcp（StreamableHTTP）和 /sse（SSE），优先使用新版 StreamableHTTP。官方 SDK 处理协议细节（初始化、会话管理、错误处理），减少实现风险。

**用法模式**：

```python
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async with streamablehttp_client(url) as (read_stream, write_stream, _):
    async with ClientSession(read_stream, write_stream) as session:
        await session.initialize()
        tools = await session.list_tools()
        result = await session.call_tool(name, arguments)
```

---

### 4. SSE 响应格式：自定义事件类型

**选择**：AI Chat API 的 SSE 响应使用自定义事件类型

**格式**：
```
event: content     data: {"content": "..."}
event: tool_call   data: {"tool": "name", "args": {...}}
event: tool_result data: {"tool": "name", "result": "..."}
event: done        data: {"usage": {...}}
event: error       data: {"type": "...", "message": "..."}
```

**替代方案**：
- 纯 OpenAI SSE 格式：只有 delta text，无法表达 tool_call 过程

**理由**：前端需要区分 content、tool_call、tool_result 三种事件来分别渲染。自定义事件类型让前端解析更简单。

**实现**：使用 `sse-starlette` 的 `EventSourceResponse`，通过 `event` 字段指定自定义事件类型。

---

### 5. 配置管理：YAML + 环境变量

**选择**：config.yaml 主配置 + `${ENV_VAR}` 环境变量引用

**理由**：YAML 可读性好，环境变量引用满足 12-Factor App 原则，API Key 不落盘更安全。

---

### 6. 配置重载：API 触发，不做文件 watch

**选择**：通过 POST /api/v1/ai/config 触发配置重载，不使用文件 watch

**替代方案**：
- watchdog 文件监控：自动检测 config.yaml 变化并重载

**理由**：
- POST /api/v1/ai/config 已经支持运行时修改配置
- 文件 watch 增加依赖（watchdog）和复杂度
- 本地开发场景下，API 触发或手动重启足够
- 如果未来需要，可以加一个 CLI 命令 `butler config reload`

---

### 7. 认证：API Key 头部认证

**选择**：`X-Butler-API-Key` 请求头认证

**理由**：butler 运行在本地，简单的 API Key 认证足够。前端在 settings 中配置 butler API Key（类似 wechat-sendmsg 配置模式）。

---

### 8. MCP 连接生命周期：长连接 + 空闲断开 + 按需重连

**选择**：启动时尝试连接，连接后保持长连接，空闲超时自动断开，下次使用时自动重连

**替代方案**：
- 每次调用新建 session（无状态模式）：更简单，但每次有连接开销
- 纯长连接不断开：chatshell-api 重启后无法自动恢复

**理由**：
- 长连接避免每次调用的连接开销
- 空闲断开节省资源（chatshell-api 可能长时间不使用）
- 按需重连保证 chatshell-api 重启后自动恢复
- 使用 `AsyncExitStack` 管理 context manager 生命周期

**实现模式**：

```python
class MCPClient:
    async def connect(self): ...        # 建立连接 + 发现工具
    async def disconnect(self): ...     # 断开连接
    async def call_tool(self, name, args): ...  # 按需连接 + 调用
    async def list_tools(self): ...     # 按需连接 + 返回缓存/重新发现
    async def _idle_watcher(self): ...  # 空闲超时自动断开
```

---

### 9. 对话历史：前端传完整历史

**选择**：前端在每次请求中传完整对话历史，butler 不维护会话状态

**替代方案**：
- butler 维护会话状态（内存中）：减少请求体积，但增加复杂度，重启后丢失
- butler + SQLite 持久化：v0.2.0 考虑

**理由**：
- butler 无状态设计，实现最简单
- 重启后不丢失对话（前端持有历史）
- 对话历史通常不大（几 KB），带宽开销可忽略

---

### 10. Provider 范围：v0.1.0 仅 OpenAI-compatible

**选择**：v0.1.0 仅支持 OpenAI-compatible provider（OpenAI、DeepSeek、国产模型、自定义 endpoint）

**理由**：
- OpenAI-compatible 格式覆盖绝大多数使用场景
- litellm 已统一接口，未来加 Anthropic 只需改 model 前缀
- 减少首期测试和适配工作量

**后续扩展**：加 Anthropic 支持时，只需在 config.yaml 中配置 `anthropic` provider 和 API Key，model 使用 `anthropic/claude-xxx` 前缀即可。

---

## 依赖决策总结

### 直接依赖

| 包 | 版本建议 | 引入理由 |
|----|----------|----------|
| fastapi | >=0.110 | Web 框架 |
| uvicorn | >=0.29 | ASGI server |
| litellm | >=1.40 | LLM 统一接口 |
| mcp | >=1.6 | MCP 客户端 SDK |
| pyyaml | >=6.0 | YAML 解析 |
| pydantic | >=2.0 | 数据验证 |
| sse-starlette | >=2.0 | SSE 流式响应 |

### 间接依赖（litellm 引入）

| 包 | 说明 |
|----|------|
| openai | OpenAI SDK |
| httpx | HTTP 客户端 |

### 不引入的依赖

| 包 | 原因 |
|----|------|
| anthropic | v0.1.0 不支持 Anthropic，litellm 未来按需引入 |
| watchdog | 不做文件 watch |
| sqlalchemy | v0.1.0 无数据库 |
| redis | v0.1.0 无缓存 |
