## 1. Project Setup

- [x] 1.1 Create project directory structure: wechat_butler/, main.py, config.py, server.py
- [x] 1.2 Create pyproject.toml with project metadata and dependencies (fastapi, uvicorn, litellm, mcp, pyyaml, pydantic, sse-starlette)
- [x] 1.3 Create requirements.txt with pinned runtime dependencies
- [x] 1.4 Create config.yaml with default configuration (server, llm, mcp, auth sections)
- [x] 1.5 Create .env.example with all required environment variables documented
- [x] 1.6 Create basic README.md with installation, configuration, and usage instructions

## 2. Configuration System

- [x] 2.1 Implement config.py: YAML loader with ${ENV_VAR} interpolation, Pydantic validation, default values
- [x] 2.2 Implement LLM config model: provider, api_key, base_url, default_model, max_tokens, temperature, models list
- [x] 2.3 Implement MCP config model: chatshell_api_url, idle_timeout, connect_timeout
- [x] 2.4 Implement auth config model: api_key

## 3. LLM Proxy Layer

- [x] 3.1 Create llm/router.py: litellm model prefix routing (model id → provider/model format), resolve model config (api_key, base_url)
- [x] 3.2 Implement MCP Tool → OpenAI function calling schema conversion in router.py
- [x] 3.3 Implement API key masking utility: mask_api_key() for logs and API responses

## 4. MCP Client

- [x] 4.1 Create mcp/client.py: MCP client using official mcp SDK streamablehttp_client with AsyncExitStack lifecycle
- [x] 4.2 Implement connection lifecycle: try connect on startup (non-blocking), idle timeout auto-disconnect, auto-reconnect on next use
- [x] 4.3 Implement tool discovery: call tools/list on connect, cache results
- [x] 4.4 Implement tool execution: call tools/call with arguments, return text result
- [x] 4.5 Implement connection status tracking: connected/disconnected state, available tool count and names

## 5. AI Chat Service

- [x] 5.1 Create ai/chat.py: main chat handler accepting messages, model, context, prompt_id
- [x] 5.2 Implement tool_call loop: send messages to LLM with tools via litellm.acompletion, handle tool_calls response, call MCP tools, return results to LLM, repeat until final response
- [x] 5.3 Implement streaming tool_call chunks accumulation: accumulate delta.tool_calls by index (id, name, arguments), assemble complete tool_calls on finish_reason
- [x] 5.4 Implement tool_call iteration limit (max 10 rounds)
- [x] 5.5 Implement context injection: prepend system message with context data (session name, message count, time range, content)
- [x] 5.6 Implement SSE event streaming: yield content, tool_call, tool_result, error, done events via sse-starlette EventSourceResponse
- [x] 5.7 Implement no-tool fallback: when MCP is disconnected, send chat without tools parameter
- [x] 5.8 Implement error handling: catch litellm AuthenticationError, RateLimitError, Timeout, yield SSE error events

## 6. Prompt Management

- [x] 6.1 Create ai/prompts.py: built-in prompt templates (群聊总结, 待办提取, 话题分析, 情绪分析, 人物画像)
- [x] 6.2 Implement custom prompt storage: YAML files in prompts/ directory
- [x] 6.3 Implement prompt CRUD: list, create, update, delete (built-in prompts are read-only)
- [x] 6.4 Implement variable substitution: replace {variableName} with provided values

## 7. API Endpoints

- [x] 7.1 Create api/ai_routes.py: POST /api/v1/ai/chat (SSE streaming response)
- [x] 7.2 Add GET /api/v1/ai/models endpoint (return configured model list)
- [x] 7.3 Add GET /api/v1/ai/status endpoint (butler version, LLM status, MCP status, tool count)
- [x] 7.4 Add GET /api/v1/ai/config endpoint (return config with masked API keys)
- [x] 7.5 Add POST /api/v1/ai/config endpoint (update LLM config at runtime, trigger reload)
- [x] 7.6 Add prompt CRUD endpoints: GET/POST/PUT/DELETE /api/v1/ai/prompts
- [x] 7.7 Create api/middleware.py: API key authentication (X-Butler-API-Key header)
- [x] 7.8 Add CORS middleware (allow all origins for local browser access)

## 8. Server and Entry Point

- [x] 8.1 Create server.py: FastAPI app factory, include routes, add middleware, lifespan events
- [x] 8.2 Create main.py: CLI entry point with uvicorn, --config flag, --port flag
- [x] 8.3 Implement startup event: load config, try connect MCP client (non-blocking), log status
- [x] 8.4 Implement shutdown event: disconnect MCP client, cleanup resources
- [x] 8.5 Add /health endpoint for basic health check (no auth required)
