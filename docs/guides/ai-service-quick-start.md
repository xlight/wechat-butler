# WeChat Butler v0.1.0 快速开始

## 前置条件

- Python 3.11+
- chatshell-api 已运行（MCP Server 端口 5030，可选）
- 至少一个 LLM API Key（OpenAI / DeepSeek 等）

---

## 安装

### 1. 克隆项目

```bash
git clone https://github.com/your-org/wechat-butler.git
cd wechat-butler
```

### 2. 安装依赖

使用 pip：

```bash
pip install -e .
```

或使用 uv（更快）：

```bash
uv pip install -e .
```

### 3. 配置环境变量

复制环境变量模板：

```bash
cp .env.example .env
```

编辑 `.env`，填入你的 API Key：

```bash
# LLM API Key（至少填一个）
OPENAI_API_KEY=sk-your-openai-key
DEEPSEEK_API_KEY=sk-your-deepseek-key

# Butler API Key（前端连接 butler 时使用）
BUTLER_API_KEY=your-butler-api-key
```

### 4. 自定义配置（可选）

编辑 `config.yaml` 修改默认配置：

```yaml
server:
  host: "0.0.0.0"
  port: 8837

llm:
  provider: "openai"
  default_model: "gpt-4o"

mcp:
  chatshell_api_url: "http://127.0.0.1:5030/mcp"
  idle_timeout: 300

auth:
  api_key: "${BUTLER_API_KEY}"
```

---

## 启动

```bash
# 使用默认配置
python -m wechat_butler

# 指定配置文件
python -m wechat_butler --config /path/to/config.yaml

# 指定端口
python -m wechat_butler --port 9000
```

启动成功后输出：

```
INFO:     WeChat Butler v0.1.0 starting...
INFO:     Config loaded from config.yaml
INFO:     MCP client connected to http://127.0.0.1:5030/mcp (6 tools discovered)
INFO:     Uvicorn running on http://0.0.0.0:8837
```

---

## 验证

### 健康检查

```bash
curl http://localhost:8837/health
```

```json
{"status": "healthy", "version": "0.1.0"}
```

### 查看状态

```bash
curl -H "X-Butler-API-Key: your-butler-api-key" \
  http://localhost:8837/api/v1/ai/status
```

### 查看可用模型

```bash
curl -H "X-Butler-API-Key: your-butler-api-key" \
  http://localhost:8837/api/v1/ai/models
```

### AI 对话测试

```bash
curl -N -H "X-Butler-API-Key: your-butler-api-key" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"你好"}]}' \
  http://localhost:8837/api/v1/ai/chat
```

---

## 前端集成（chatlog-session）

在 chatlog-session 的设置中配置：

- **Butler URL**: `http://localhost:8837`
- **Butler API Key**: 你在 `.env` 中设置的 `BUTLER_API_KEY`

前端通过以下方式与 butler 交互：

1. **AI 对话**：POST `/api/v1/ai/chat`（SSE 流式响应）
2. **模型选择**：GET `/api/v1/ai/models`
3. **状态检查**：GET `/api/v1/ai/status`
4. **配置修改**：GET/POST `/api/v1/ai/config`
5. **Prompt 管理**：CRUD `/api/v1/ai/prompts`

---

## 常见问题

### Q: 启动时 MCP 连接失败？

如果 chatshell-api 未运行，butler 会输出警告但正常启动。AI Chat 将以无工具模式运行（LLM 无法查询聊天数据）。

启动 chatshell-api 后，butler 会在下次 AI Chat 请求时自动重连 MCP。

### Q: 如何切换 LLM provider？

通过 API：

```bash
curl -X POST -H "X-Butler-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"provider":"deepseek","default_model":"deepseek-chat"}' \
  http://localhost:8837/api/v1/ai/config
```

或修改 `config.yaml` 后重启 butler。

### Q: 如何添加自定义 Prompt？

通过 API：

```bash
curl -X POST -H "X-Butler-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"name":"周报生成","description":"根据群聊生成周报","content":"根据 {sessionName} 本周的讨论，生成周报"}' \
  http://localhost:8837/api/v1/ai/prompts
```

或在 `prompts/` 目录下创建 YAML 文件。
