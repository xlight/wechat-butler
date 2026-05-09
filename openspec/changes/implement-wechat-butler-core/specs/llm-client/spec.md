## ADDED Requirements

### Requirement: Support OpenAI API
The LLM client SHALL support OpenAI API for text generation.

#### Scenario: Generate text with OpenAI
- **GIVEN** OpenAI is configured as provider with valid API key
- **WHEN** the system requests text generation with prompt "讲个程序员笑话"
- **THEN** the system SHALL call OpenAI API and return generated text response

#### Scenario: OpenAI API error
- **GIVEN** OpenAI API returns 500 error or times out
- **WHEN** the system attempts to generate text
- **THEN** the system SHALL raise LLMException with error details and NOT crash

#### Scenario: Invalid OpenAI API key
- **GIVEN** configured OpenAI API key is invalid
- **WHEN** the system attempts to generate text
- **THEN** the system SHALL raise LLMException with authentication error

### Requirement: Support Claude API
The LLM client SHALL support Anthropic Claude API as an alternative provider.

#### Scenario: Generate text with Claude
- **GIVEN** Claude is configured as provider with valid API key
- **WHEN** the system requests text generation
- **THEN** the system SHALL call Claude API and return generated text

#### Scenario: Claude-specific error handling
- **GIVEN** Claude API returns an error
- **WHEN** the system attempts to generate text
- **THEN** the system SHALL handle Claude error format and raise appropriate exception

### Requirement: Configurable model selection
The LLM client SHALL allow configuration of which model to use per provider.

#### Scenario: OpenAI model selection
- **GIVEN** config specifies `model: gpt-4` for OpenAI
- **WHEN** generating text
- **THEN** the system SHALL use gpt-4 model instead of default gpt-3.5-turbo

#### Scenario: Claude model selection
- **GIVEN** config specifies `model: claude-3-opus-20240229`
- **WHEN** generating text
- **THEN** the system SHALL use the specified Claude model

### Requirement: Support temperature and max_tokens
The LLM client SHALL support temperature and max_tokens parameters.

#### Scenario: Configure generation parameters
- **GIVEN** config specifies `temperature: 0.7` and `max_tokens: 150`
- **WHEN** generating text with prompt "讲个故事"
- **THEN** the system SHALL pass these parameters to the LLM API

#### Scenario: Response within token limit
- **GIVEN** max_tokens is set to 100
- **WHEN** generating a long response
- **THEN** the system SHALL receive response truncated to approximately 100 tokens

### Requirement: Async API calls
The LLM client SHALL make asynchronous API calls to avoid blocking.

#### Scenario: Non-blocking generation
- **WHEN** multiple LLM requests are made concurrently
- **THEN** the system SHALL process them asynchronously without blocking other operations

#### Scenario: Timeout handling
- **GIVEN** LLM API takes longer than configured timeout (default 30 seconds)
- **WHEN** the system makes a generation request
- **THEN** the system SHALL raise TimeoutException after timeout period

### Requirement: Cost tracking and logging
The LLM client SHALL track and log API usage for cost monitoring.

#### Scenario: Log token usage
- **WHEN** an LLM API call completes successfully
- **THEN** the system SHALL log input tokens, output tokens, and total tokens used

#### Scenario: Request logging
- **WHEN** any LLM request is made
- **THEN** the system SHALL log timestamp, provider, model, and success/failure status

### Requirement: Abstract interface for extensibility
The LLM client SHALL provide an abstract interface allowing easy addition of new providers.

#### Scenario: Implement new provider
- **WHEN** a developer implements the LLMProvider interface for a new service (e.g., DeepSeek)
- **THEN** the system SHALL be able to use it without modifying core code

#### Scenario: Unified response format
- **GIVEN** different providers return different response formats
- **WHEN** any provider generates text
- **THEN** the system SHALL return standardized response with `text`, `tokens_used`, and `model` fields
