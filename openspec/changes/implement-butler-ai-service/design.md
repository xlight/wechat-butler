## Context

wechat-butler 是微信生态的智能中枢，连接 chatshell-api（读取消息）和 wechat-sendmsg（发送消息）。本项目是 butler 的第一个可用版本（v0.1.0），聚焦 AI Service Layer，为 chatlog-session v0.28.0 的 AI 面板提供后端支持。

chatshell-api MCP Server 已就绪，注册了 6 个工具（query_contact, query_chat_room, query_recent_chat, query_chat_log, current_time, query_diary），同时支持 /mcp（StreamableHTTP）和 /sse + /message（SSE）两种传输协议。

前端（chatlog-session）通过 butler HTTP API 交互，不直接连接 LLM 或 MCP。butler 负责所有 AI 相关的复杂逻辑。

## Goals / Non-Goals

**Goals:**
1. 提供 LLM 代理服务，支持 OpenAI / DeepSeek / 自定义 OpenAI-compatible provider（v0.1.0 范围）
2. 通过 MCP 客户端连接 chatshell-api，获取数据查询工具
3. 实现 tool_call 循环（LLM ↔ MCP 工具调用），前端无需感知
4. 提供 AI Chat API（SSE 流式响应），供前端实时渲染
5. 提供 Prompt 库管理（内置模板 + CRUD）
6. 提供 LLM 配置 API，前端可修改 provider/model/API Key
7. 提供健康检查和状态 API
8. API Key 认证保护所有端点

**Non-Goals:**
- Anthropic provider 支持（v0.1.0 不含，litellm 后续零成本扩展）
- Webhook 接收和规则引擎（v0.2.0 范围）
- 定时任务和消息发送（v0.2.0 范围）
- Web 管理界面（前端由 chatlog-session 负责）
- 多实例部署或高可用
- 内置数据库（首期无状态，对话历史不持久化）
- 插件系统
- 配置文件 watch 热重载（API 触发重载已够）

## Decisions

### 1. 技术栈：Python 3.11+ / FastAPI

**决策**：使用 Python FastAPI 作为 butler 的技术栈。

**替代方案**：
- Go（与 chatshell-api 一致）：性能更好，但 Python 的 LLM/MCP 生态更成熟
- Node.js：与前端技术栈一致，但 Python 在 AI/ML 领域库更丰富

**理由**：butler 的核心是 LLM 交互和 MCP 协议，Python 生态有最成熟的 SDK 支持。FastAPI 的异步特性和自动 OpenAPI 文档也是加分项。

### 2. LLM 调用：使用 litellm

**决策**：使用 `litellm` 的 `acompletion()` 作为统一 LLM 接口。

**替代方案**：
- httpx 直接调 API：最小依赖，但需自己解析 SSE chunk、拼接 tool_call delta，工作量大且容易出 bug
- openai Python SDK：官方 SDK，但只覆盖 OpenAI-compatible，未来加 Anthropic 需要两套适配

**理由**：
1. 社区广泛使用（GitHub 20k+ stars），ragflow、PraisonAI 等项目在用
2. streaming + tool_calls 开箱即用，不需要自己解析 SSE chunk 或拼接 tool_call delta chunks
3. 统一接口：`litellm.acompletion()` 一个函数覆盖 OpenAI / DeepSeek / Anthropic / 100+ provider
4. 未来加 Anthropic 支持只需改 model 前缀为 `anthropic/claude-xxx`，零代码改动
5. 返回格式统一为 OpenAI 兼容格式，tool_call 处理逻辑只需写一套
6. 内置重试、fallback、rate limit 处理、API Key 脱敏日志

**v0.1.0 范围**：仅使用 OpenAI-compatible provider（OpenAI、DeepSeek、国产模型）。

### 3. MCP 客户端：使用官方 mcp Python SDK

**决策**：使用 `mcp` Python 包的 `streamablehttp_client` 连接 chatshell-api /mcp 端点。

**替代方案**：
- 手写 MCP 客户端：可控但工作量大，协议细节容易出错
- 使用 SSE 传输（/sse + /message）：旧版协议，官方已标记为 deprecated

**理由**：chatshell-api 同时支持 /mcp（StreamableHTTP）和 /sse（SSE），优先使用新版 StreamableHTTP。官方 SDK 处理协议细节（初始化、会话管理、错误处理），减少实现风险。

### 4. MCP 连接生命周期：长连接 + 空闲断开 + 按需重连

**决策**：启动时尝试连接（失败不阻塞），连接后保持长连接，空闲超时自动断开，下次使用时自动重连。

**替代方案**：
- 每次调用新建 session（无状态模式）：更简单，但每次有连接开销
- 纯长连接不断开：chatshell-api 重启后无法自动恢复

**理由**：长连接避免每次调用的连接开销；空闲断开节省资源；按需重连保证 chatshell-api 重启后自动恢复。使用 `AsyncExitStack` 管理 context manager 生命周期。

### 5. SSE 响应格式：自定义事件类型

**决策**：AI Chat API 的 SSE 响应使用自定义事件类型，而非纯 OpenAI 格式。

**格式**：
```
event: content
data: {"content": "根据聊天记录..."}

event: tool_call
data: {"tool": "query_chat_log", "args": {"talker": "工作群", "time": "today"}}

event: tool_result
data: {"tool": "query_chat_log", "result": "..."}

event: content
data: {"content": "总结如下：\n1. ..."}

event: done
data: {"usage": {"prompt_tokens": 100, "completion_tokens": 200}}
```

**理由**：前端需要区分 content、tool_call、tool_result 三种事件来分别渲染。纯 OpenAI 格式只有 delta text，无法表达 tool_call 过程。自定义事件类型让前端解析更简单。

### 6. 配置管理：YAML + 环境变量

**决策**：使用 config.yaml 作为主配置文件，支持 `${ENV_VAR}` 语法引用环境变量。LLM API Key 通过环境变量注入，不硬编码在配置文件中。

**理由**：YAML 可读性好，环境变量引用满足 12-Factor App 原则，API Key 不落盘更安全。

### 7. 配置重载：API 触发，不做文件 watch

**决策**：通过 POST /api/v1/ai/config 触发配置重载，不使用文件 watch。

**理由**：POST /api/v1/ai/config 已支持运行时修改配置；文件 watch 增加依赖和复杂度；本地开发场景下 API 触发或手动重启足够。

### 8. 认证：API Key 头部认证

**决策**：所有 API 端点要求 `X-Butler-API-Key` 请求头，值与配置中的 `auth.api_key` 匹配。

**理由**：butler 运行在本地，简单的 API Key 认证足够。前端在 settings 中配置 butler API Key（类似 sendmsg 配置模式）。

### 9. 对话历史：前端传完整历史

**决策**：前端在每次请求中传完整对话历史，butler 不维护会话状态。

**理由**：butler 无状态设计，实现最简单；重启后不丢失对话（前端持有历史）；对话历史通常不大，带宽开销可忽略。

## Risks / Trade-offs

- [chatshell-api 未运行时 MCP 工具不可用] → AI Chat 仍可工作（无工具模式），但 AI 无法查询聊天数据；status API 反映 MCP 连接状态
- [LLM API 限流或不可用] → 返回 SSE error event，前端展示重试提示；litellm 内置重试和 rate limit 处理
- [SSE 连接中断] → 前端 EventSource 自动重连；butler 无状态设计，重连后可继续对话
- [对话历史不持久化] → 首期可接受，butler 重启后对话清空；v0.2.0 可加 SQLite 持久化
- [Python 依赖管理] → 提供 requirements.txt + pyproject.toml，支持 pip 和 uv
- [MCP SDK 兼容性] → chatshell-api 使用 mark3labs/mcp-go，butler 使用官方 mcp Python SDK，协议标准一致但实现细节可能有差异；需要集成测试验证
- [litellm 依赖] → 引入 litellm 及其间接依赖（openai SDK、httpx），但换来 streaming + tool_calls 开箱即用，比自己实现 SSE 解析更可靠
