## Why

chatlog-session v0.28.0 需要集成 AI 能力（右侧面板对话、上下文投喂、工具调用展示），但前端不应直接管理 LLM API Key 或实现 MCP tool_call 循环。wechat-butler 作为微信生态的智能中枢，应承担 AI Service Layer 的角色：管理 LLM 连接、通过 MCP 获取 chatlog 数据、处理 tool_call 循环、以 SSE 流式推送结果给前端。这是 butler 的第一个可用版本（v0.1.0），聚焦 AI 服务能力。

## What Changes

- 新增 FastAPI 项目骨架和配置系统（YAML + 环境变量）
- 新增 LLM 代理层：支持 OpenAI / Anthropic / DeepSeek / 自定义 provider，API Key 通过配置文件/环境变量管理
- 新增 MCP 客户端：通过 Streamable HTTP 连接 chatshell-api /mcp，获取 6 个数据查询工具
- 新增 tool_call 循环：LLM 返回 tool_call 时自动调 MCP 工具，结果回传 LLM 继续生成
- 新增 AI Chat API：POST /api/v1/ai/chat（SSE 流式响应，OpenAI 兼容格式）
- 新增 Prompt 库 API：CRUD + 内置模板
- 新增模型管理 API：GET /api/v1/ai/models
- 新增 LLM 配置 API：GET/POST /api/v1/ai/config（前端可修改 LLM 配置）
- 新增健康检查 API：GET /api/v1/ai/status
- 新增 API Key 认证中间件

## Capabilities

### New Capabilities
- `llm-proxy`: LLM 代理服务（多 provider 路由、API Key 管理、流式转发）
- `mcp-client`: MCP 客户端（连接 chatshell-api、工具发现、工具调用）
- `ai-chat-service`: AI 对话服务（tool_call 循环、上下文注入、SSE 流式响应）
- `prompt-management`: Prompt 库管理（内置模板、CRUD、变量替换）
- `butler-api`: Butler HTTP API（认证、配置、状态、模型管理）

### Modified Capabilities

（无，这是全新项目）

## Impact

- **新增项目**: wechat-butler Python FastAPI 项目（~2000 行 Python 代码）
- **新增依赖**: fastapi, uvicorn, httpx, mcp, pyyaml, pydantic, sse-starlette
- **前置依赖**: chatshell-api 需运行（MCP Server 端口 5030）
- **端口**: 默认 8837
- **配置**: config.yaml + 环境变量（LLM_API_KEY, BUTLER_API_KEY 等）
