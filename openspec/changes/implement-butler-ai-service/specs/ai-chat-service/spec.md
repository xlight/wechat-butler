## ADDED Requirements

### Requirement: Process AI chat requests with tool_call loop
The system SHALL accept chat requests, send them to LLM with MCP tools description, and handle the tool_call loop: when LLM returns tool_calls, execute each via MCP client, return results to LLM, and continue until LLM produces a final text response.

#### Scenario: Simple chat without tool call
- **WHEN** user sends "你好" with no context
- **THEN** LLM responds directly without tool calls, response streamed as SSE content events

#### Scenario: Chat with tool call
- **WHEN** user sends "总结今天工作群的讨论" and LLM decides to call query_chat_log
- **THEN** SSE events: tool_call → tool_result → content (final summary)

#### Scenario: Multiple tool calls in sequence
- **WHEN** LLM returns multiple tool_calls in one response
- **THEN** all tools are called, all results returned to LLM, then LLM continues

#### Scenario: Tool call loop with multiple rounds
- **WHEN** LLM calls a tool, gets result, then decides to call another tool
- **THEN** the loop continues until LLM produces a final response without tool_calls

### Requirement: Inject context into LLM request
The system SHALL accept a context object in the chat request and inject it into the LLM messages as a system/assistant message prefix. Context SHALL include session name, message count, time range, and message content.

#### Scenario: Context injected as system message
- **WHEN** chat request includes context with session "工作群" and 50 messages
- **THEN** a system message is prepended to the LLM request describing the context

### Requirement: Stream SSE events to client
The system SHALL stream the following SSE event types to the client: content (text chunk), tool_call (tool invocation), tool_result (tool output), error (failure), done (completion with usage stats).

#### Scenario: Content event
- **WHEN** LLM generates a text chunk
- **THEN** SSE event: event: content, data: {"content": "chunk text"}

#### Scenario: Tool call event
- **WHEN** LLM requests a tool call
- **THEN** SSE event: event: tool_call, data: {"tool": "name", "args": {...}}

#### Scenario: Tool result event
- **WHEN** MCP tool returns a result
- **THEN** SSE event: event: tool_result, data: {"tool": "name", "result": "..."}

#### Scenario: Done event
- **WHEN** LLM completes the response
- **THEN** SSE event: event: done, data: {"usage": {"prompt_tokens": N, "completion_tokens": M}}

### Requirement: Limit tool call iterations
The system SHALL limit the tool_call loop to a maximum of 10 iterations to prevent infinite loops. If the limit is reached, the system SHALL return the last LLM response with a warning.

#### Scenario: Tool call limit reached
- **WHEN** tool_call loop exceeds 10 iterations
- **THEN** response is returned with a warning that tool call limit was reached
