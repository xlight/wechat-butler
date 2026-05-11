# WeChat Butler v0.1.0 使用指南

## 文档信息

- **版本**: v0.1.0
- **创建日期**: 2026-05-09
- **适用范围**: AI Service Layer

---

## 概述

WeChat Butler 是微信生态的 AI 智能中枢。它连接 chatshell-api 获取聊天数据，通过 LLM 进行智能分析，以 SSE 流式响应将结果推送给前端（chatlog-session）。

典型使用场景：

- 在 chatlog-session 的 AI 面板中与 AI 对话，AI 自动调用工具查询聊天数据
- 使用内置 Prompt 模板快速完成群聊总结、待办提取等任务
- 运行时切换 LLM provider 和模型，无需重启
- 管理自定义 Prompt 模板

---

## 前置条件

| 依赖 | 要求 | 说明 |
|------|------|------|
| Python | 3.11+ | 推荐 3.11 或 3.12 |
| chatshell-api | 运行中（可选） | MCP Server 端口 5030，提供 6 个数据查询工具 |
| LLM API Key | 至少一个 | OpenAI / DeepSeek / 其他 OpenAI-compatible provider |

> chatshell-api 未运行时，butler 仍可正常启动，AI Chat 以无工具模式运行（LLM 无法查询聊天数据）。

---

## 安装

### 方式一：pip 安装

```bash
git clone https://github.com/your-org/wechat-butler.git
cd wechat-butler
pip install -e .
```

### 方式二：uv 安装（更快）

```bash
git clone https://github.com/your-org/wechat-butler.git
cd wechat-butler
uv pip install -e .
```

### 方式三：Conda 环境

```bash
git clone https://github.com/your-org/wechat-butler.git
cd wechat-butler
conda env create -f environment.yml
conda activate wechat-butler
```

---

## 配置

### 1. 设置环境变量

复制模板并填入 API Key：

```bash
cp .env.example .env
```

编辑 `.env`：

```bash
# LLM API Key（至少填一个）
OPENAI_API_KEY=sk-your-openai-key
DEEPSEEK_API_KEY=sk-your-deepseek-key

# Butler API Key（前端连接 butler 时使用）
BUTLER_API_KEY=your-butler-api-key
```

### 2. 自定义配置（可选）

编辑 `config.yaml`：

```yaml
server:
  host: "0.0.0.0"
  port: 8837
  log_level: "info"

llm:
  provider: "openai"
  api_key: "${OPENAI_API_KEY}"
  base_url: "https://api.openai.com/v1"
  default_model: "gpt-4o"
  max_tokens: 4096
  temperature: 0.7
  models:
    - id: "gpt-4o"
      name: "GPT-4o"
    - id: "deepseek-chat"
      name: "DeepSeek Chat"
      provider: "deepseek"
      api_key: "${DEEPSEEK_API_KEY}"
      base_url: "https://api.deepseek.com/v1"

mcp:
  chatshell_api_url: "http://127.0.0.1:5030/mcp"
  idle_timeout: 300
  connect_timeout: 10

auth:
  api_key: "${BUTLER_API_KEY}"

prompts:
  directory: "prompts"
```

**配置要点**：

- `${ENV_VAR}` 语法引用环境变量，API Key 不硬编码在配置文件中
- `models` 列表定义前端可选的模型，每个模型可覆盖全局 provider/api_key/base_url
- `mcp.idle_timeout` 控制 MCP 空闲自动断开时间（秒），默认 300
- `auth.api_key` 为空时跳过认证（仅限本地开发）

### 3. 添加自定义 Prompt（可选）

在 `prompts/` 目录下创建 YAML 文件：

```yaml
id: "custom-weekly-report"
name: "周报生成"
description: "根据群聊内容生成周报"
content: "根据 {sessionName} 本周的讨论，生成周报：\n{content}"
variables:
  - "sessionName"
  - "content"
```

也可通过 API 创建（见下文）。

---

## 启动

```bash
# 默认配置启动
python -m wechat_butler

# 指定配置文件
python -m wechat_butler --config /path/to/config.yaml

# 覆盖端口
python -m wechat_butler --port 9000

# 覆盖主机和端口
python -m wechat_butler --host 127.0.0.1 --port 9000
```

启动成功日志：

```
INFO:     WeChat Butler v0.1.0 starting...
INFO:     Config loaded from config.yaml
INFO:     MCP connected to http://127.0.0.1:5030/mcp (6 tools discovered)
INFO:     Uvicorn running on http://0.0.0.0:8837
```

MCP 连接失败时（chatshell-api 未运行）：

```
INFO:     WeChat Butler v0.1.0 starting...
INFO:     Config loaded from config.yaml
WARNING:  MCP connection failed, AI Chat will run in no-tool mode
INFO:     Uvicorn running on http://0.0.0.0:8837
```

> butler 正常启动，AI Chat 可用但无法调用 MCP 工具。chatshell-api 启动后，下次 AI Chat 请求会自动重连。

---

## API 使用

所有 API 端点（除 `/health`）需要 `X-Butler-API-Key` 请求头认证。

### 健康检查

无需认证：

```bash
curl http://localhost:8837/health
```

```json
{"status": "healthy", "version": "0.1.0"}
```

### 查看服务状态

```bash
curl -H "X-Butler-API-Key: your-butler-api-key" \
  http://localhost:8837/api/v1/ai/status
```

```json
{
  "butler": {"version": "0.1.0", "status": "ok"},
  "llm": {"status": "configured", "provider": "openai", "default_model": "gpt-4o"},
  "mcp": {
    "status": "connected",
    "url": "http://127.0.0.1:5030/mcp",
    "tools": 6,
    "tool_names": ["query_contact", "query_chat_room", "query_recent_chat", "query_chat_log", "current_time", "query_diary"]
  }
}
```

### 查看可用模型

```bash
curl -H "X-Butler-API-Key: your-butler-api-key" \
  http://localhost:8837/api/v1/ai/models
```

```json
{
  "models": [
    {"id": "gpt-4o", "name": "GPT-4o", "provider": "openai"},
    {"id": "deepseek-chat", "name": "DeepSeek Chat", "provider": "deepseek"}
  ],
  "default_model": "gpt-4o"
}
```

### AI 对话

AI 对话是核心功能，返回 SSE 流式响应。

#### 简单对话

```bash
curl -N -H "X-Butler-API-Key: your-butler-api-key" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"你好"}]}' \
  http://localhost:8837/api/v1/ai/chat
```

SSE 响应：

```
event: content
data: {"content": "你好！"}

event: done
data: {"usage": {"prompt_tokens": 10, "completion_tokens": 5}}
```

#### 带工具调用的对话

当 MCP 已连接时，LLM 可自动调用工具查询数据：

```bash
curl -N -H "X-Butler-API-Key: your-butler-api-key" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"总结今天工作群的讨论"}]}' \
  http://localhost:8837/api/v1/ai/chat
```

SSE 响应（含工具调用）：

```
event: content
data: {"content": "让我查询一下今天的聊天记录"}

event: tool_call
data: {"tool": "query_chat_log", "args": {"talker": "工作群", "time": "today"}}

event: tool_result
data: {"tool": "query_chat_log", "result": "[张三: 早上好...][李四: 收到...]"}

event: content
data: {"content": "今天工作群的讨论总结如下：\n1. 早上张三发了问候\n2. 李四确认收到"}

event: done
data: {"usage": {"prompt_tokens": 150, "completion_tokens": 80}}
```

#### 带上下文的对话

注入会话上下文信息，帮助 LLM 理解对话背景：

```bash
curl -N -H "X-Butler-API-Key: your-butler-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "帮我总结一下"}],
    "context": {
      "session_name": "工作群",
      "message_count": 50,
      "time_range": "today",
      "content": "张三: 早上好\n李四: 收到\n王五: 今天开会"
    }
  }' \
  http://localhost:8837/api/v1/ai/chat
```

#### 使用 Prompt 模板

通过 `prompt_id` 指定 Prompt 模板，`variables` 传入变量值：

```bash
curl -N -H "X-Butler-API-Key: your-butler-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "请分析"}],
    "prompt_id": "builtin-group-summary",
    "variables": {"content": "张三: 早上好\n李四: 收到"}
  }' \
  http://localhost:8837/api/v1/ai/chat
```

#### 指定模型

```bash
curl -N -H "X-Butler-API-Key: your-butler-api-key" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"你好"}], "model": "deepseek-chat"}' \
  http://localhost:8837/api/v1/ai/chat
```

#### SSE 事件类型汇总

| event | data 格式 | 说明 |
|-------|-----------|------|
| `content` | `{"content": "..."}` | LLM 生成的文本片段 |
| `tool_call` | `{"tool": "name", "args": {...}}` | LLM 请求调用 MCP 工具 |
| `tool_result` | `{"tool": "name", "result": "..."}` | 工具调用结果 |
| `error` | `{"type": "...", "message": "..."}` | 错误事件 |
| `done` | `{"usage": {"prompt_tokens": N, "completion_tokens": M}}` | 完成事件 |

**error 事件类型**：

| type | 说明 |
|------|------|
| `auth_error` | LLM API Key 无效 |
| `rate_limit` | LLM API 限流 |
| `timeout` | LLM API 超时 |
| `mcp_error` | MCP 工具调用失败 |
| `max_iterations` | tool_call 循环超过 10 轮限制 |
| `internal_error` | 其他内部错误 |

### 配置管理

#### 查看当前配置

API Key 已脱敏：

```bash
curl -H "X-Butler-API-Key: your-butler-api-key" \
  http://localhost:8837/api/v1/ai/config
```

```json
{
  "provider": "openai",
  "api_key": "sk-***...abc",
  "base_url": "https://api.openai.com/v1",
  "default_model": "gpt-4o",
  "max_tokens": 4096,
  "temperature": 0.7
}
```

#### 运行时修改配置

无需重启，立即生效：

```bash
curl -X POST -H "X-Butler-API-Key: your-butler-api-key" \
  -H "Content-Type: application/json" \
  -d '{"provider":"deepseek","default_model":"deepseek-chat"}' \
  http://localhost:8837/api/v1/ai/config
```

可修改的字段：`provider`、`api_key`、`base_url`、`default_model`、`max_tokens`、`temperature`。

### Prompt 管理

#### 列出所有 Prompt

```bash
curl -H "X-Butler-API-Key: your-butler-api-key" \
  http://localhost:8837/api/v1/ai/prompts
```

内置模板列表：

| ID | 名称 | 说明 |
|----|------|------|
| `builtin-group-summary` | 群聊总结 | 总结群聊讨论的要点和关键信息 |
| `builtin-todo-extract` | 待办提取 | 从聊天记录中提取待办事项 |
| `builtin-topic-analysis` | 话题分析 | 分析聊天中的主要话题和讨论趋势 |
| `builtin-sentiment-analysis` | 情绪分析 | 分析聊天中的情绪倾向 |
| `builtin-person-profile` | 人物画像 | 根据聊天记录生成人物画像 |

#### 创建自定义 Prompt

```bash
curl -X POST -H "X-Butler-API-Key: your-butler-api-key" \
  -H "Content-Type: application/json" \
  -d '{"name":"周报生成","description":"根据群聊内容生成周报","content":"根据 {sessionName} 本周的讨论，生成周报：\n{content}"}' \
  http://localhost:8837/api/v1/ai/prompts
```

`{variableName}` 语法定义模板变量，调用时通过 `variables` 参数传入值。未提供的变量保留原样。

#### 更新自定义 Prompt

```bash
curl -X PUT -H "X-Butler-API-Key: your-butler-api-key" \
  -H "Content-Type: application/json" \
  -d '{"content":"更新后的模板内容 {content}"}' \
  http://localhost:8837/api/v1/ai/prompts/custom-001
```

> 内置模板不可修改，返回 `403 Forbidden`。

#### 删除自定义 Prompt

```bash
curl -X DELETE -H "X-Butler-API-Key: your-butler-api-key" \
  http://localhost:8837/api/v1/ai/prompts/custom-001
```

> 内置模板不可删除，返回 `403 Forbidden`。

---

## 前端集成

在 chatlog-session 的设置中配置：

- **Butler URL**: `http://localhost:8837`
- **Butler API Key**: `.env` 中设置的 `BUTLER_API_KEY`

前端通过以下方式与 butler 交互：

1. **AI 对话**：`POST /api/v1/ai/chat`（SSE 流式响应）
2. **模型选择**：`GET /api/v1/ai/models`
3. **状态检查**：`GET /api/v1/ai/status`
4. **配置修改**：`GET/POST /api/v1/ai/config`
5. **Prompt 管理**：`CRUD /api/v1/ai/prompts`

### 前端 SSE 解析示例

```javascript
const response = await fetch('http://localhost:8837/api/v1/ai/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-Butler-API-Key': 'your-butler-api-key'
  },
  body: JSON.stringify({
    messages: [{ role: 'user', content: '总结今天工作群的讨论' }],
    model: 'gpt-4o'
  })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const text = decoder.decode(value);
  // 解析 SSE 事件：event: xxx\ndata: {...}\n\n
  const lines = text.split('\n');
  for (const line of lines) {
    if (line.startsWith('event: ')) {
      const eventType = line.slice(7);
      // 处理事件类型
    } else if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      // 处理事件数据
    }
  }
}
```

---

## MCP 工具说明

当 chatshell-api 运行时，butler 通过 MCP 协议连接，获取以下 6 个数据查询工具：

| 工具 | 说明 |
|------|------|
| `query_contact` | 查询联系人信息 |
| `query_chat_room` | 查询群聊信息 |
| `query_recent_chat` | 查询最近聊天 |
| `query_chat_log` | 查询聊天记录 |
| `current_time` | 获取当前时间 |
| `query_diary` | 查询日记 |

LLM 在对话中会根据用户意图自动选择调用这些工具。前端通过 SSE 的 `tool_call` 和 `tool_result` 事件可展示工具调用过程。

### MCP 连接生命周期

```
启动 → 尝试连接 chatshell-api
  ├─ 连接成功 → 保持长连接，发现工具
  └─ 连接失败 → 正常启动，无工具模式

运行中 → 空闲超时（默认 300s）→ 自动断开
       → 下次 AI Chat 请求 → 自动重连

关闭 → 断开 MCP 连接，清理资源
```

---

## 常见问题

### Q: 启动时 MCP 连接失败？

chatshell-api 未运行时，butler 输出警告但正常启动。AI Chat 以无工具模式运行。启动 chatshell-api 后，下次 AI Chat 请求会自动重连。

### Q: 如何切换 LLM provider？

通过 API 运行时切换（无需重启）：

```bash
curl -X POST -H "X-Butler-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"provider":"deepseek","default_model":"deepseek-chat"}' \
  http://localhost:8837/api/v1/ai/config
```

或修改 `config.yaml` 后重启 butler。

### Q: 如何使用国产模型？

在 `config.yaml` 的 `models` 列表中添加配置，provider 设为 `openai`（因为国产模型大多兼容 OpenAI API），`base_url` 指向国产模型的 API 地址：

```yaml
models:
  - id: "qwen-plus"
    name: "通义千问 Plus"
    provider: "openai"
    api_key: "${QWEN_API_KEY}"
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
```

### Q: AI Chat 返回 error 事件？

常见原因：

| error type | 原因 | 解决 |
|------------|------|------|
| `auth_error` | LLM API Key 无效 | 检查 `.env` 中的 API Key |
| `rate_limit` | LLM API 限流 | 等待后重试，或切换 provider |
| `timeout` | LLM API 超时 | 检查网络，或增大 `max_tokens` |
| `mcp_error` | MCP 工具调用失败 | 检查 chatshell-api 是否运行 |
| `max_iterations` | tool_call 超过 10 轮 | 简化问题，或分步提问 |

### Q: 如何添加自定义 Prompt？

通过 API：

```bash
curl -X POST -H "X-Butler-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"name":"周报生成","description":"根据群聊生成周报","content":"根据 {sessionName} 本周的讨论，生成周报"}' \
  http://localhost:8837/api/v1/ai/prompts
```

或在 `prompts/` 目录下创建 YAML 文件。

### Q: 如何跳过认证？

将 `config.yaml` 中 `auth.api_key` 设为空字符串，或 `.env` 中不设置 `BUTLER_API_KEY`。此时所有端点无需认证。**仅限本地开发使用**。

### Q: tool_call 循环最多执行几轮？

默认最多 10 轮。超过后返回 `max_iterations` 错误事件和当前已生成的内容。这是为了防止 LLM 陷入无限工具调用循环。

---

## 相关文档

- [快速开始](ai-service-quick-start.md) - 安装和启动的精简版
- [API 参考](../api/ai-service-api.md) - 完整的 API 端点文档
- [架构设计](../architecture/ai-service-v0.1.md) - 系统架构和数据流
- [技术选型](../features/ai-service-tech-decisions.md) - 技术决策和理由
