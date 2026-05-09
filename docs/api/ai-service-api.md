# WeChat Butler v0.1.0 AI Service API 参考

## 文档信息

- **版本**: v0.1.0
- **创建日期**: 2026-05-09
- **API 版本**: v1
- **基础路径**: `/api/v1`
- **默认端口**: 8837

---

## 概述

v0.1.0 提供 AI 对话、模型管理、配置管理、Prompt 管理和健康检查等 API。所有端点（除 `/health` 外）需要 API Key 认证。

### 基础信息

- **基础 URL**: `http://localhost:8837`
- **API 版本**: `v1`
- **内容类型**: `application/json`（SSE 端点除外）
- **认证方式**: `X-Butler-API-Key` 请求头

---

## 认证

### API Key 认证

所有 API 端点（除 `/health`）要求 `X-Butler-API-Key` 请求头：

```http
GET /api/v1/ai/models
X-Butler-API-Key: your-butler-api-key
```

**认证失败**：返回 `401 Unauthorized`

```json
{
  "detail": "Invalid or missing API key"
}
```

---

## API 端点

### 健康检查

#### GET /health

基础健康检查，**无需认证**。

**响应**:

```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

---

### AI 对话

#### POST /api/v1/ai/chat

AI 对话接口，返回 SSE 流式响应。

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `messages` | array | 是 | 对话消息列表（OpenAI 格式） |
| `model` | string | 否 | 模型 ID，默认使用配置中的 default_model |
| `context` | object | 否 | 上下文信息，注入为 system message |
| `prompt_id` | string | 否 | Prompt 模板 ID，加载模板作为 system prompt |
| `variables` | object | 否 | Prompt 变量键值对，用于模板变量替换 |

**context 对象**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `session_name` | string | 会话名称（如"工作群"） |
| `message_count` | integer | 消息数量 |
| `time_range` | string | 时间范围（如"today"） |
| `content` | string | 上下文内容摘要 |

**请求示例**:

```json
{
  "messages": [
    {"role": "user", "content": "总结今天工作群的讨论"}
  ],
  "model": "deepseek-chat",
  "context": {
    "session_name": "工作群",
    "message_count": 50,
    "time_range": "today"
  }
}
```

**响应**: SSE 流（`Content-Type: text/event-stream`）

**SSE 事件类型**:

| event | data 格式 | 说明 |
|-------|-----------|------|
| `content` | `{"content": "..."}` | LLM 生成的文本片段 |
| `tool_call` | `{"tool": "name", "args": {...}}` | LLM 请求调用工具 |
| `tool_result` | `{"tool": "name", "result": "..."}` | 工具调用结果 |
| `error` | `{"type": "...", "message": "..."}` | 错误事件 |
| `done` | `{"usage": {"prompt_tokens": N, "completion_tokens": M}}` | 完成事件 |

**SSE 流示例**:

```
event: content
data: {"content": "让我查询一下"}

event: tool_call
data: {"tool": "query_chat_log", "args": {"talker": "工作群", "time": "today"}}

event: tool_result
data: {"tool": "query_chat_log", "result": "[张三: 早上好...][李四: 收到...]"}

event: content
data: {"content": "今天工作群的讨论总结如下：\n1. 早上张三发了问候"}

event: content
data: {"content": "\n2. 李四确认收到"}

event: done
data: {"usage": {"prompt_tokens": 150, "completion_tokens": 80}}
```

**前端调用示例**:

```javascript
const eventSource = new EventSource('/api/v1/ai/chat', {
  headers: { 'X-Butler-API-Key': 'your-key' }
});

// 注意：POST 请求需要用 fetch + ReadableStream
const response = await fetch('/api/v1/ai/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-Butler-API-Key': 'your-key'
  },
  body: JSON.stringify({ messages, model })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();
// 解析 SSE 事件...
```

---

### 模型管理

#### GET /api/v1/ai/models

获取已配置的模型列表。

**响应**:

```json
{
  "models": [
    {
      "id": "gpt-4o",
      "name": "GPT-4o",
      "provider": "openai"
    },
    {
      "id": "deepseek-chat",
      "name": "DeepSeek Chat",
      "provider": "deepseek"
    }
  ],
  "default_model": "gpt-4o"
}
```

---

### 状态检查

#### GET /api/v1/ai/status

获取 butler 及各子系统状态。

**响应**:

```json
{
  "butler": {
    "version": "0.1.0",
    "status": "ok"
  },
  "llm": {
    "status": "configured",
    "provider": "openai",
    "default_model": "gpt-4o"
  },
  "mcp": {
    "status": "connected",
    "url": "http://127.0.0.1:5030/mcp",
    "tools": 6,
    "tool_names": [
      "query_contact", "query_chat_room", "query_recent_chat",
      "query_chat_log", "current_time", "query_diary"
    ]
  }
}
```

**MCP 断连时**:

```json
{
  "butler": {"version": "0.1.0", "status": "ok"},
  "llm": {"status": "configured", "provider": "openai", "default_model": "gpt-4o"},
  "mcp": {"status": "disconnected", "url": "http://127.0.0.1:5030/mcp", "tools": 0, "tool_names": []}
}
```

---

### 配置管理

#### GET /api/v1/ai/config

获取当前 LLM 配置（API Key 已脱敏）。

**响应**:

```json
{
  "provider": "openai",
  "api_key": "sk-***...abc",
  "base_url": "https://api.openai.com/v1",
  "default_model": "gpt-4o",
  "models": [
    {"id": "gpt-4o", "name": "GPT-4o", "provider": "openai"},
    {"id": "deepseek-chat", "name": "DeepSeek Chat", "provider": "deepseek"}
  ]
}
```

#### POST /api/v1/ai/config

运行时更新 LLM 配置（无需重启）。

**请求体**:

```json
{
  "provider": "deepseek",
  "api_key": "sk-new-key",
  "default_model": "deepseek-chat"
}
```

**响应**: 更新后的配置（API Key 已脱敏）

---

### Prompt 管理

#### GET /api/v1/ai/prompts

获取所有 Prompt 模板（内置 + 自定义）。

**响应**:

```json
{
  "prompts": [
    {
      "id": "builtin-group-summary",
      "name": "群聊总结",
      "description": "总结群聊讨论内容",
      "content": "请总结以下群聊讨论的要点：\n{content}",
      "variables": ["content"],
      "builtin": true
    },
    {
      "id": "custom-001",
      "name": "我的模板",
      "description": "自定义模板",
      "content": "分析 {sessionName} 的消息",
      "variables": ["sessionName"],
      "builtin": false
    }
  ]
}
```

#### POST /api/v1/ai/prompts

创建自定义 Prompt 模板。

**请求体**:

```json
{
  "name": "周报生成",
  "description": "根据群聊内容生成周报",
  "content": "根据 {sessionName} 本周的讨论，生成周报：\n{content}"
}
```

#### PUT /api/v1/ai/prompts/:id

更新自定义 Prompt 模板（内置模板不可修改）。

#### DELETE /api/v1/ai/prompts/:id

删除自定义 Prompt 模板（内置模板不可删除）。

**删除内置模板时返回**: `403 Forbidden`

```json
{
  "detail": "Built-in prompts cannot be deleted"
}
```

---

## 错误响应格式

所有错误使用统一格式：

```json
{
  "detail": "错误描述"
}
```

### 常见错误码

| 状态码 | 场景 |
|--------|------|
| 401 | 缺少或无效的 API Key |
| 403 | 尝试修改/删除内置 Prompt |
| 404 | Prompt 或模型不存在 |
| 422 | 请求体验证失败 |
| 500 | 内部错误 |
