## Context

WeChat Butler is the missing automation layer in the WeChat ecosystem. Currently, chatshell-api can read messages and wechat-sendmsg can send messages, but there's no intelligent processor connecting them. This project creates a production-ready rule engine that enables automated message processing workflows.

**Current Ecosystem**:
```
chatshell-api ──► [GAP] ──► wechat-sendmsg
     │                            ▲
     │                            │
     └──── chatlog-session ───────┘
           (viewing only)
```

**Target Architecture**:
```
chatshell-api ──► WeChat Butler ──► wechat-sendmsg
     │                 │                  ▲
     │                 │                  │
     └──── chatlog-session ───────────────┘
           (control + viewing)
```

WeChat Butler serves as the intelligent hub that transforms passive message monitoring into active automation through a declarative rule engine.

**Design Philosophy**:
- **Single Process**: Avoid microservice complexity
- **Minimal Dependencies**: Only essential libraries
- **Fast Startup**: < 2 seconds cold start
- **Low Resource**: < 50MB RAM footprint
- **Configurable**: YAML-based rules, hot-reload support
- **Extensible**: Plugin architecture for future growth

## Goals / Non-Goals

**Goals:**
1. Receive authenticated webhook messages from chatshell-api
2. Parse and standardize message format across different sources
3. Evaluate declarative rules with multiple condition types (keyword, regex, sender, talker, time)
4. Execute actions: reply, forward, command execution, HTTP calls, notifications
5. Optional LLM integration for intelligent responses
6. Configuration hot-reload without restart
7. Comprehensive RESTful API for management
8. Real-time event streaming (SSE) for monitoring
9. Health checks and metrics
10. Secure authentication (API keys, webhook signatures)

**Non-Goals:**
- Multi-instance clustering or high availability
- Built-in database (optional SQLite for state only)
- Complex workflow engine (v0.2.0)
- Web-based management UI (v0.3.0)
- Plugin marketplace (v0.3.0)
- Support for WeChat Work/Enterprise
- Multi-tenant architecture

## Decisions

### 1. Architecture: Modular Monolith

**Decision**: Single process with clear module separation

**Structure**:
```
wechat_butler/
├── main.py                 # Entry point
├── config.py              # Configuration management
├── server.py              # FastAPI application
├── webhook/               # Webhook handling
│   ├── receiver.py        # HTTP endpoint
│   ├── validator.py       # Signature validation
│   └── parser.py          # Message normalization
├── rule_engine/           # Rule processing
│   ├── engine.py          # Core engine
│   ├── compiler.py        # Rule compilation & caching
│   ├── conditions.py      # Condition evaluators
│   └── actions.py         # Action generators
├── executors/             # Action execution
│   ├── wechat.py          # Send messages
│   ├── command.py         # Shell commands
│   ├── http.py            # HTTP calls
│   └── llm.py             # LLM integration
├── api/                   # REST API
│   ├── routes/            # API endpoints
│   └── middleware.py      # Auth, logging
└── utils/                 # Utilities
    ├── logging.py         # Structured logging
    └── validation.py      # Data validation
```

**Rationale**:
- Clear separation of concerns
- Testable modules
- Easy to extend with new conditions/actions
- Still deployable as single unit

### 2. Message Processing Pipeline

**Decision**: Async pipeline with standardized message format

**Flow**:
```
Webhook Receiver ──► Validator ──► Parser ──► Rule Engine ──► Scheduler ──► Executors
```

**Standardized Message Format**:
```python
{
    "id": "msg_123456",
    "timestamp": 1732252800,
    "talker": "filehelper",      # Chat/group name
    "sender": "user123",          # Actual sender
    "content": "Hello World",
    "type": 1,                    # 1=text, 3=image, etc.
    "raw": {...}                  # Original payload
}
```

**Rationale**:
- Consistent format throughout pipeline
- Easy to add new input sources later
- Clear transformation at each stage

### 3. Rule Engine Design

**Decision**: Compiled rule engine with priority-based evaluation

**Rule Structure**:
```yaml
rules:
  - name: "自动问候"
    priority: 100                    # Higher = evaluated first
    enabled: true
    conditions:                      # All must match (AND logic)
      - type: "keyword"
        field: "content"
        value: ["你好", "hello"]
        case_sensitive: false
    actions:                         # Executed in order
      - type: "reply"
        content: "你好！"
```

**Compilation Strategy**:
- Parse YAML rules at startup
- Compile conditions into evaluator functions
- Cache compiled rules in memory
- Build indexes for fast lookup (by talker, sender, keywords)

**Evaluation Order**:
1. Sort rules by priority (descending)
2. For each rule, evaluate all conditions
3. Short-circuit on first false condition
4. Generate actions for matching rules
5. Execute all actions

**Rationale**:
- Compiled rules faster than interpreted
- Priority allows rule precedence
- Indexing enables O(1) lookups for common filters

### 4. Condition Types

**Decision**: Support 6 condition types in v0.1.0

1. **keyword**: Substring matching in content
2. **regex**: Regular expression matching
3. **sender**: Match message sender
4. **talker**: Match chat/group name
5. **type**: Match message type (text, image, etc.)
6. **time**: Match time ranges and weekdays

**Condition Interface**:
```python
class Condition(ABC):
    @abstractmethod
    def evaluate(self, message: dict) -> bool: ...
    
    @property
    def cost(self) -> int: ...  # For optimization
```

**Optimization**: Evaluate low-cost conditions first (sender/talker) before expensive ones (regex/time).

### 5. Action System

**Decision**: Async action execution with retry and timeout

**Action Types**:
1. **reply**: Send text reply
2. **forward**: Forward message to another chat
3. **command**: Execute shell command
4. **http**: Call external HTTP API
5. **notification**: Send system notification
6. **llm**: Generate AI response

**Execution Model**:
```python
async def execute_action(action: dict, context: dict) -> dict:
    executor = get_executor(action['type'])
    try:
        result = await asyncio.wait_for(
            executor.execute(action, context),
            timeout=action.get('timeout', 30)
        )
        return {'success': True, 'result': result}
    except Exception as e:
        if action.get('retry', 0) > 0:
            return await retry_execute(action, context)
        return {'success': False, 'error': str(e)}
```

**Rationale**:
- Async prevents blocking on slow actions
- Timeout prevents runaway commands
- Retry handles transient failures
- Context provides message data for templating

### 6. Configuration Management

**Decision**: YAML with Pydantic validation and hot-reload

**Config Structure**:
```yaml
server:
  host: "0.0.0.0"
  port: 8080

webhook:
  secret: "${WEBHOOK_SECRET}"
  path: "/webhook/message"

wechat:
  sendmsg_url: "http://localhost:8000"

llm:
  enabled: true
  provider: "openai"
  api_key: "${OPENAI_API_KEY}"
  model: "gpt-3.5-turbo"

rules:
  directory: "./rules"
  auto_reload: true

logging:
  level: "INFO"
  file: "./logs/butler.log"
```

**Hot-Reload**:
- Watch config.yaml and rules/*.yaml for changes
- Validate before applying
- Rollback on validation failure
- Preserve existing connections

**Rationale**:
- YAML is human-readable
- Pydantic provides validation and defaults
- Hot-reload enables quick iteration
- Environment variable support for secrets

### 7. API Design

**Decision**: RESTful API with FastAPI, authentication required

**Endpoints**:
```
# Public
GET  /health                    # Health check
POST /webhook/message          # Webhook receiver (sig auth)

# Authenticated (API Key)
GET  /api/v1/rules             # List rules
POST /api/v1/rules             # Create rule
GET  /api/v1/rules/{id}        # Get rule
PUT  /api/v1/rules/{id}        # Update rule
DELETE /api/v1/rules/{id}      # Delete rule
POST /api/v1/rules/{id}/test   # Test rule

POST /api/v1/commands/execute  # Execute command
GET  /api/v1/commands          # Command history

GET  /api/v1/metrics           # System metrics
GET  /api/v1/config            # Get config
PUT  /api/v1/config            # Update config
POST /api/v1/reload            # Reload config

GET  /api/v1/events            # SSE stream
```

**Authentication**:
- Webhook: HMAC-SHA256 signature verification
- API: API key in `X-API-Key` header

**Rationale**:
- REST is familiar and well-documented
- FastAPI auto-generates OpenAPI spec
- Separate auth for webhooks (signature) vs API (key)

### 8. Error Handling Strategy

**Decision**: Structured error handling with graceful degradation

**Principles**:
1. Don't crash on bad input - log and continue
2. Return meaningful HTTP status codes
3. Structured error responses with error codes
4. Separate user-facing vs developer-facing errors

**Error Response Format**:
```json
{
  "error": {
    "code": "RULE_VALIDATION_FAILED",
    "message": "Rule contains invalid condition",
    "details": {
      "rule": "rule_001",
      "field": "conditions[0].type",
      "reason": "Unknown condition type 'invalid'"
    }
  }
}
```

**Rationale**:
- Helps API consumers handle errors
- Enables better debugging
- Structured logging for observability

### 9. Testing Strategy

**Decision**: Three-tier testing approach

1. **Unit Tests**: Individual modules (pytest)
2. **Integration Tests**: API endpoints (TestClient)
3. **E2E Tests**: Full message flow (simulated webhooks)

**Coverage Targets**:
- Core logic: > 80%
- API endpoints: > 70%
- Error paths: > 60%

**Rationale**:
- Prevents regressions
- Documents expected behavior
- Enables confident refactoring

### 10. Deployment Strategy

**Decision**: Multiple deployment options

1. **Direct**: `python main.py`
2. **Systemd**: Service with auto-restart
3. **Docker**: Containerized deployment
4. **Docker Compose**: With chatshell-api, wechat-sendmsg

**Rationale**:
- Flexibility for different user needs
- Simple for personal use
- Containerized for advanced users
- Fits Raspberry Pi deployment

## Risks / Trade-offs

### Risk: Performance with Many Rules

**Issue**: 1000+ rules may cause slow evaluation

**Mitigation**:
- Rule indexing by talker/sender
- Compiled condition evaluators
- Async processing pipeline
- Benchmark at 100, 500, 1000 rules

### Risk: Memory Leaks

**Issue**: Long-running process may accumulate memory

**Mitigation**:
- No global state accumulation
- Use context managers
- Regular memory profiling
- Health check monitors memory

### Risk: Security Vulnerabilities

**Issue**: Webhook/API endpoints could be exploited

**Mitigation**:
- Input validation on all endpoints
- HMAC signature verification
- API key authentication
- Rate limiting (configurable)
- No execution of arbitrary code

### Trade-off: Complexity vs Features

**Choice**: Build full rule engine in v0.1.0, not just @mention bot

**Benefit**: More useful, validates architecture

**Cost**: Longer development time

**Acceptance**: 4-6 week timeline acceptable for complete v0.1.0

### Risk: LLM Integration Complexity

**Issue**: Multiple LLM providers, different APIs, costs

**Mitigation**:
- Abstract LLM interface
- Start with OpenAI (most popular)
- Make LLM optional feature
- Document costs clearly

## Migration Plan

**Not applicable** - new project

**Deployment Checklist**:
1. Install Python 3.11+
2. Install dependencies
3. Create config.yaml
4. Create rules directory with sample rules
5. Start service
6. Configure chatshell-api webhook
7. Test with sample messages
8. Monitor logs for errors

## Open Questions

1. **Rule Conflicts**: How to handle multiple rules matching same message? Current design: execute all actions. Alternative: stop after first match.

2. **Async Action Failure**: If one action fails, continue with others or stop? Current: continue, log error.

3. **Message Ordering**: Ensure actions executed in order? Current: yes, sequential.

4. **State Persistence**: Need to persist state across restarts? Current: no state in v0.1.0.

5. **Rate Limiting**: Implement per-action or global? Current: global webhook rate limit.

6. **LLM Context**: Pass conversation history to LLM? Current: no, single message only.

7. **Action Templating**: Template syntax (Jinja2 vs simple {{var}})? Current: simple variable substitution.
