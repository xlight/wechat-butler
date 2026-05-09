## ADDED Requirements

### Requirement: Connect to chatshell-api MCP Server
The system SHALL connect to chatshell-api MCP Server via Streamable HTTP transport at the configured URL (default http://127.0.0.1:5030/mcp). The connection SHALL be attempted on startup but failure SHALL NOT block server startup.

#### Scenario: Successful MCP connection on startup
- **WHEN** butler starts and chatshell-api is running
- **THEN** MCP client connects to /mcp endpoint and initializes the session

#### Scenario: chatshell-api not running on startup
- **WHEN** butler starts but chatshell-api is not reachable
- **THEN** MCP client reports disconnected status; butler starts normally; AI chat works in no-tool mode

### Requirement: Long connection with idle timeout and auto-reconnect
The system SHALL maintain a long MCP connection when in use. When idle for longer than the configured idle_timeout (default 300 seconds), the connection SHALL be automatically disconnected. When a tool call is needed and the connection is disconnected, the system SHALL automatically attempt to reconnect.

#### Scenario: Idle timeout disconnect
- **WHEN** no MCP tool calls are made for idle_timeout seconds
- **THEN** MCP client automatically disconnects to save resources

#### Scenario: Auto-reconnect on next use
- **WHEN** chatshell-api becomes available after being unreachable or after idle disconnect
- **THEN** MCP client automatically reconnects when the next tool call is requested

### Requirement: Discover available MCP tools
The system SHALL call tools/list on the MCP server to discover available tools. Discovered tools SHALL be cached and used to populate the tools parameter in LLM requests.

#### Scenario: List tools on connect
- **WHEN** MCP client connects successfully
- **THEN** available tools (query_contact, query_chat_room, query_recent_chat, query_chat_log, current_time, query_diary) are discovered and cached

### Requirement: Call MCP tools
The system SHALL call tools/call on the MCP server when the LLM requests a tool invocation. The tool result SHALL be returned to the LLM for continued generation.

#### Scenario: Call query_chat_log tool
- **WHEN** LLM returns a tool_call for "query_chat_log" with arguments
- **THEN** MCP client calls the tool on chatshell-api and returns the result

#### Scenario: Tool call error
- **WHEN** MCP tool call fails (invalid args, server error)
- **THEN** an error result is returned to the LLM indicating the tool call failed

### Requirement: Connection status tracking
The system SHALL track and report MCP connection status (connected/disconnected), available tool count, and tool names.

#### Scenario: Status when connected
- **WHEN** MCP client is connected
- **THEN** status reports connected, tool count (6), and tool names

#### Scenario: Status when disconnected
- **WHEN** MCP client is disconnected
- **THEN** status reports disconnected, tool count (0), and empty tool names
