## ADDED Requirements

### Requirement: API Key authentication
All API endpoints SHALL require an X-Butler-API-Key header matching the configured auth.api_key. Requests without valid authentication SHALL receive 401 Unauthorized.

#### Scenario: Valid API key
- **WHEN** request includes X-Butler-API-Key matching config
- **THEN** request is processed normally

#### Scenario: Missing API key
- **WHEN** request does not include X-Butler-API-Key header
- **THEN** response is 401 Unauthorized

#### Scenario: Invalid API key
- **WHEN** request includes wrong X-Butler-API-Key
- **THEN** response is 401 Unauthorized

### Requirement: Health check and status API
The system SHALL provide GET /api/v1/ai/status returning: butler version, LLM provider status (configured/not configured), MCP connection status, available tool count and names.

#### Scenario: All services healthy
- **WHEN** butler is running with LLM configured and MCP connected
- **THEN** status returns {"butler": {"version": "0.1.0", "status": "ok"}, "llm": {"status": "configured", ...}, "mcp": {"status": "connected", "tools": 6, "tool_names": [...]}}

#### Scenario: MCP disconnected
- **WHEN** chatshell-api is not running
- **THEN** status returns {"mcp": {"status": "disconnected", "tools": 0, "tool_names": []}}

### Requirement: Model list API
The system SHALL provide GET /api/v1/ai/models returning the list of configured models with id, name, and provider.

#### Scenario: List models
- **WHEN** GET /api/v1/ai/models is called
- **THEN** response includes all configured models from config.yaml

### Requirement: LLM configuration API
The system SHALL provide GET /api/v1/ai/config to read current LLM config (with api_key masked) and POST /api/v1/ai/config to update LLM config at runtime (without restart). Configuration reload is triggered via API only, not file watch.

#### Scenario: Get config with masked key
- **WHEN** GET /api/v1/ai/config is called
- **THEN** api_key is returned as "sk-***...abc" (masked)

#### Scenario: Update config at runtime
- **WHEN** POST /api/v1/ai/config with new provider and model
- **THEN** config is updated immediately without restart, subsequent requests use new config

### Requirement: CORS support
The system SHALL include CORS middleware allowing requests from any origin (since butler runs locally and is accessed by browser-based chatlog-session).

#### Scenario: CORS preflight
- **WHEN** browser sends OPTIONS request
- **THEN** appropriate CORS headers are returned allowing the request
