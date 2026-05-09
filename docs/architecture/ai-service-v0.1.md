# WeChat Butler v0.1.0 AI Service 架构设计

## 文档信息

- **版本**: v0.1.0
- **创建日期**: 2026-05-09
- **适用范围**: AI Service Layer（首个可用版本）
- **前置依赖**: chatshell-api MCP Server（端口 5030）

---

## 定位

v0.1.0 是 wechat-butler 的首个可用版本，**聚焦 AI Service Layer**，为 chatlog-session v0.28.0 的 AI 面板提供后端支持。

核心职责：管理 LLM 连接、通过 MCP 获取 chatlog 数据、处理 tool_call 循环、以 SSE 流式推送结果给前端。

**不包含**：Webhook 接收、规则引擎、定时任务、消息发送（v0.2.0 范围）。

---

## 整体架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                     wechat-butler v0.1.0                             │
│                                                                      │
│  main.py ──▶ server.py (FastAPI app factory)                        │
│                  │                                                   │
│                  ├── lifespan                                        │
│                  │   ├── startup: load config, connect MCP           │
│                  │   └── shutdown: disconnect MCP, cleanup           │
│                  │                                                   │
│                  ├── middleware                                      │
│                  │   ├── API Key auth (X-Butler-API-Key)            │
│                  │   └── CORS (allow all)                           │
│                  │                                                   │
│                  └── routes                                          │
│                      ├── POST /api/v1/ai/chat     → SSE stream      │
│                      ├── GET  /api/v1/ai/models                      │
│                      ├── GET  /api/v1/ai/status                      │
│                      ├── GET  /api/v1/ai/config                      │
│                      ├── POST /api/v1/ai/config                      │
│                      ├── CRUD  /api/v1/ai/prompts                    │
│                      └── GET  /health               (no auth)       │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Core Services                              │   │
│  │                                                              │   │
│  │  config.py ──▶ YAML + ${ENV} + Pydantic validation          │   │
│  │                                                              │   │
│  │  llm/                                                         │   │
│  │  └── router.py ──▶ model → litellm model prefix 路由        │   │
│  │                   (litellm 统一处理 provider 差异)            │   │
│  │                                                              │   │
│  │  mcp/                                                         │   │
│  │  └── client.py ──▶ streamablehttp_client 生命周期管理        │   │
│  │                    长连接 + 空闲超时断开 + 按需重连            │   │
│  │                                                              │   │
│  │  ai/                                                          │   │
│  │  ├── chat.py ────▶ tool_call loop + SSE event streaming     │   │
│  │  └── prompts.py ─▶ 内置模板 + CRUD + 变量替换               │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

### 系统集成视图

```
┌──────────────┐     HTTP/SSE     ┌──────────────────┐
│ chatlog-     │ ◀────────────── │ wechat-butler     │
│ session      │   (AI 面板)     │ (AI Service Layer)│
│ (前端)       │                 │  端口: 8837       │
└──────────────┘                 └────────┬─────────┘
                                           │
                           ┌───────────────┼────────────┐
                           │               │            │
                           ▼               ▼            ▼
                  ┌────────────┐  ┌────────────┐  ┌────────┐
                  │ litellm    │  │ MCP Client │  │ Prompt │
                  │ (多provider│  │ (连接       │  │ 库     │
                  │  统一接口) │  │  chatshell) │  │ 管理   │
                  └─────┬──────┘  └─────┬──────┘  └────────┘
                        │               │
                        ▼               ▼
               ┌──────────────┐  ┌──────────────────┐
               │ OpenAI /     │  │ chatshell-api    │
               │ DeepSeek /   │  │ MCP Server       │
               │ 自定义       │  │ 端口: 5030       │
               └──────────────┘  └──────────────────┘
```

---

## 核心数据流：AI Chat with tool_call loop

```
前端 (chatlog-session)
  │
  │ POST /api/v1/ai/chat  (messages, model, context, prompt_id)
  ▼
butler AI Chat Service
  │
  │ 1. 如果有 prompt_id → 加载 prompt 模板 + 变量替换
  │ 2. 如果有 context → 构造 system message 前缀
  │ 3. 获取 MCP tools 列表（如果 MCP 已连接）
  │
  └── 4. 进入 tool_call loop (max 10 rounds):
       │
       │  iteration = 0
       │  while iteration < 10:
       │    │
       │    ├── litellm.acompletion(messages, tools, stream=True)
       │    │
       │    ├── async for chunk in response:
       │    │   ├── delta.content → yield SSE "content" event
       │    │   └── delta.tool_calls → 累积 tool_call chunks
       │    │
       │    ├── if 无 tool_calls:
       │    │   └── yield SSE "done" event → 结束
       │    │
       │    ├── for each tool_call:
       │    │   ├── yield SSE "tool_call" event
       │    │   ├── 调用 MCP client.call_tool()
       │    │   ├── yield SSE "tool_result" event
       │    │   └── 追加 tool_call + tool_result 到 messages
       │    │
       │    └── iteration += 1, 继续循环
       │
       └── if 达到 10 次限制:
           └── yield SSE "error" event (max iterations) + "done"
```

---

## SSE 事件流格式

自定义事件类型（非纯 OpenAI 格式），前端按 event type 分别渲染：

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

event: error
data: {"type": "rate_limit", "message": "..."}
```

---

## 模块详细设计

### 1. 配置系统 (config.py)

- YAML 主配置文件 + `${ENV_VAR}` 环境变量引用
- Pydantic 模型验证
- API Key 通过环境变量注入，不硬编码在配置文件中
- 支持通过 API 触发配置重载（POST /api/v1/ai/config），不做文件 watch

**配置结构**：

```yaml
server:
  host: "0.0.0.0"
  port: 8837

llm:
  provider: "openai"           # 默认 provider
  api_key: "${OPENAI_API_KEY}" # 环境变量引用
  base_url: "https://api.openai.com/v1"
  default_model: "gpt-4o"
  models:
    - id: "gpt-4o"
      name: "GPT-4o"
      provider: "openai"
    - id: "deepseek-chat"
      name: "DeepSeek Chat"
      provider: "deepseek"
      api_key: "${DEEPSEEK_API_KEY}"
      base_url: "https://api.deepseek.com/v1"

mcp:
  chatshell_api_url: "http://127.0.0.1:5030/mcp"
  idle_timeout: 300            # 空闲 5 分钟后断开

auth:
  api_key: "${BUTLER_API_KEY}"
```

### 2. LLM 代理层 (llm/router.py)

使用 **litellm** 作为统一 LLM 接口：

- `litellm.acompletion()` 统一处理 OpenAI / DeepSeek / 自定义 OpenAI-compatible provider
- model prefix 路由：`deepseek-chat` → `deepseek/deepseek-chat`（litellm 约定）
- streaming + tool_calls 开箱即用，不需要自己解析 SSE chunk 或拼接 tool_call delta
- API Key 通过 litellm 的 `api_key` 参数传入，不在日志中暴露

**v0.1.0 只支持 OpenAI-compatible provider**（OpenAI、DeepSeek、国产模型）。Anthropic 留到后续版本，届时只需改 model 前缀为 `anthropic/claude-xxx`。

### 3. MCP 客户端 (mcp/client.py)

使用官方 **mcp Python SDK** 的 `streamablehttp_client`：

- 连接 chatshell-api 的 `/mcp` 端点（StreamableHTTP 传输）
- **长连接 + 空闲超时断开 + 按需重连**：
  - 启动时尝试连接，chatshell-api 不可用则标记 disconnected
  - 连接后启动空闲监控协程，超时自动断开
  - 下次 `call_tool()` 或 `list_tools()` 时自动重连
- 工具发现：连接后调用 `session.list_tools()`，缓存结果
- 工具调用：`session.call_tool(name, arguments)`

**chatshell-api 注册的 6 个工具**：
- `query_contact` — 查询联系人
- `query_chat_room` — 查询群聊
- `query_recent_chat` — 查询最近聊天
- `query_chat_log` — 查询聊天记录
- `current_time` — 获取当前时间
- `query_diary` — 查询日记

### 4. AI Chat 服务 (ai/chat.py)

核心 tool_call 循环实现：

- 前端传完整对话历史（butler 无状态，不维护会话）
- context 注入：将 context 对象构造为 system message 前缀
- prompt 模板：通过 prompt_id 加载模板 + 变量替换
- MCP 断连时降级为无工具模式（不传 tools 参数）
- tool_call 循环上限 10 轮，防止无限循环
- SSE 事件流通过 `sse-starlette` 的 `EventSourceResponse` 返回

### 5. Prompt 管理 (ai/prompts.py)

- **内置模板**（只读）：群聊总结、待办提取、话题分析、情绪分析、人物画像
- **自定义模板**：YAML 文件存储在 `prompts/` 目录，支持 CRUD
- **变量替换**：`{variableName}` 语法，缺失变量保留原样不报错

---

## 项目目录结构

```
wechat-butler/
├── wechat_butler/               # Python 包
│   ├── __init__.py
│   ├── main.py                  # CLI 入口 (uvicorn)
│   ├── server.py                # FastAPI app factory + lifespan
│   ├── config.py                # YAML + ${ENV} + Pydantic
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   └── router.py            # model → litellm prefix 路由
│   │
│   ├── mcp/
│   │   ├── __init__.py
│   │   └── client.py            # MCP 客户端生命周期管理
│   │
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── chat.py              # tool_call loop + SSE streaming
│   │   └── prompts.py           # 内置模板 + CRUD + 变量替换
│   │
│   └── api/
│       ├── __init__.py
│       ├── ai_routes.py         # AI 相关端点
│       └── middleware.py        # API Key auth + CORS
│
├── prompts/                     # 自定义 prompt YAML 文件
├── config.yaml                  # 默认配置
├── .env.example                 # 环境变量模板
├── pyproject.toml               # 项目元数据 + 依赖
├── requirements.txt             # 固定运行时依赖
└── README.md                    # 安装、配置、使用说明
```

---

## 依赖清单

### 核心依赖

| 包 | 用途 | 说明 |
|----|------|------|
| fastapi | Web 框架 | 异步、自动 OpenAPI 文档 |
| uvicorn | ASGI server | 生产级 server |
| litellm | LLM 统一接口 | streaming + tool_calls 开箱即用，覆盖 100+ provider |
| mcp | MCP 客户端 SDK | 官方 Python SDK，StreamableHTTP 传输 |
| pyyaml | YAML 配置解析 | config.yaml 读取 |
| pydantic | 数据验证 | 配置模型、请求/响应模型 |
| sse-starlette | SSE 流式响应 | FastAPI 的 SSE 支持 |

### litellm 间接引入

| 包 | 说明 |
|----|------|
| openai | OpenAI SDK（litellm 内部使用） |
| httpx | HTTP 客户端（litellm/openai 内部使用） |

---

## 错误处理策略

分层降级，优先级从高到低：

| 优先级 | 场景 | 处理方式 |
|--------|------|----------|
| P0 | LLM API Key 无效/缺失 | 启动时检查，返回明确错误，服务不可用 |
| P1 | LLM 限流/超时 | SSE error event + 重试提示，前端友好展示 |
| P1 | MCP 断连 | 降级为无工具模式，AI Chat 仍可工作 |
| P2 | MCP 工具调用失败 | tool_result 返回错误给 LLM，LLM 自行决定下一步 |
| P2 | tool_call 循环达上限 | 返回已有内容 + warning event |
| P3 | 配置文件格式错误 | 启动失败 + 明确报错 |

---

## 与 v0.2.0 的关系

v0.1.0 是 v0.2.0 的子集。v0.1.0 实现的模块为 v0.2.0 预留扩展点：

| v0.1.0 模块 | v0.2.0 扩展 |
|-------------|-------------|
| config.py | 新增 webhook/rules 配置段 |
| server.py | 新增 webhook 接收路由、规则引擎路由 |
| mcp/client.py | 支持连接多个 MCP server |
| ai/chat.py | 集成规则引擎决策结果 |
