## ADDED Requirements

### Requirement: Support multiple LLM providers via litellm
The system SHALL use litellm as the unified LLM interface, supporting OpenAI, DeepSeek, and custom OpenAI-compatible providers. Each provider SHALL have its own base_url and api_key configuration. Model routing SHALL use litellm's provider/model prefix format (e.g., "deepseek/deepseek-chat").

#### Scenario: Call OpenAI provider
- **WHEN** a chat request is made with model "gpt-4o"
- **THEN** litellm.acompletion is called with model "openai/gpt-4o" and the configured api_key and base_url

#### Scenario: Call DeepSeek provider
- **WHEN** a chat request is made with model "deepseek-chat" configured under deepseek provider
- **THEN** litellm.acompletion is called with model "deepseek/deepseek-chat" and its own api_key and base_url

#### Scenario: Call custom provider
- **WHEN** a model is configured with a custom provider and base_url
- **THEN** litellm.acompletion is called with the custom base_url using OpenAI-compatible format

### Requirement: Stream LLM responses with tool_calls via litellm
The system SHALL use litellm.acompletion with stream=True to get streaming responses. Text content SHALL be yielded as SSE "content" events. Tool call chunks SHALL be accumulated by index and assembled into complete tool_calls when finish_reason is received.

#### Scenario: Stream response with text content
- **WHEN** LLM returns a streaming response with text content
- **THEN** each delta.content is yielded as an SSE "content" event immediately

#### Scenario: Stream response with tool_calls
- **WHEN** LLM returns a streaming response with tool_calls
- **THEN** delta.tool_calls chunks are accumulated by index; complete tool_calls are available after finish_reason="tool_calls"

#### Scenario: LLM returns error
- **WHEN** LLM API returns an error (rate limit, invalid key, etc.)
- **THEN** an SSE "error" event is sent with error type and message

### Requirement: API Key managed via configuration
LLM API keys SHALL be read from config.yaml with environment variable interpolation. API keys SHALL NOT be logged or exposed in API responses.

#### Scenario: API key from environment variable
- **WHEN** config.yaml specifies api_key: ${OPENAI_API_KEY}
- **THEN** the value is read from the OPENAI_API_KEY environment variable

#### Scenario: API key not logged
- **WHEN** a request is made with an API key
- **THEN** the API key is masked in all log output (e.g., "sk-***...abc")

### Requirement: MCP Tool to OpenAI Tool schema conversion
The system SHALL convert MCP Tool objects (with name, description, inputSchema) to OpenAI function calling format for the tools parameter in litellm.acompletion.

#### Scenario: Convert MCP tool to OpenAI format
- **WHEN** MCP tool "query_chat_log" with inputSchema is discovered
- **THEN** it is converted to {"type": "function", "function": {"name": "query_chat_log", "description": "...", "parameters": inputSchema}}
