## Why

WeChat ecosystem currently has separate tools for reading messages (chatshell-api) and sending messages (wechat-sendmsg), but lacks an intelligent automation layer to connect them. This project creates the missing "brain" that transforms passive message monitoring into active automation.

**Success Criteria for this phase**: User can @mention the bot in a WeChat group chat, and the bot responds with a joke/story. This validates the core message processing loop: receive webhook → parse @mention → call LLM → send reply.

## What Changes

Implement WeChat Butler v0.1.0 with a focused MVP scope targeting the @mention → joke scenario:

- **Webhook Receiver**: HTTP endpoint to receive messages from chatshell-api with basic validation
- **@Mention Detection**: Parse message content to detect @mentions directed at the bot
- **LLM Integration**: Basic integration with OpenAI/Claude API to generate jokes/stories when triggered
- **Message Sender**: HTTP client to send replies via wechat-sendmsg
- **Simple Configuration**: YAML config for LLM API keys and bot identity
- **Health Check**: Basic endpoint to verify service is running

**Out of Scope for v0.1.0**: Full rule engine, multiple condition types, hot-reload, comprehensive API, SSE events, plugin system.

## Capabilities

### New Capabilities
- `webhook-receiver`: HTTP endpoint to receive messages from chatshell-api with JSON parsing and validation
- `mention-detector`: Parse message content to detect @mentions targeting the bot, extracting the command/query after the mention
- `llm-client`: Basic LLM API client supporting OpenAI and Claude for generating text responses (jokes/stories)
- `wechat-sender`: HTTP client to send messages via wechat-sendmsg with retry logic
- `configuration`: YAML configuration for LLM API keys, bot nickname, and basic settings
- `health-endpoint`: Simple HTTP endpoint for service health checks

### Modified Capabilities
<!-- No existing capabilities to modify - this is a new project -->

## Impact

**New Code**: Python 3.11+ application (~500-800 lines) using FastAPI for webhook handling and HTTP client for LLM/wechat-sendmsg integration

**External Dependencies**: 
- chatshell-api: Webhook source for incoming messages
- wechat-sendmsg: Target service for sending replies
- OpenAI API or Claude API: For generating jokes/stories

**APIs**: 
- `POST /webhook/message` - Receive messages from chatshell-api
- `GET /health` - Health check endpoint

**Configuration Files**: 
- `config.yaml` - LLM API keys and bot nickname

**User Flow**:
1. User @mentions bot in WeChat group: "@机器人 讲个段子"
2. chatshell-api sends webhook with message
3. Butler detects @mention and extracts "讲个段子"
4. Butler calls LLM API to generate a joke
5. Butler sends reply via wechat-sendmsg
6. User sees the joke in the chat

**System Requirements**: Python 3.11+, local network access to chatshell-api and wechat-sendmsg, internet access for LLM API
