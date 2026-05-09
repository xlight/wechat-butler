## 1. Project Setup and Infrastructure

- [ ] 1.1 Create project directory structure (`src/wechat_butler/`, `tests/`, `config/`, `rules/`)
- [ ] 1.2 Create `pyproject.toml` with project metadata and dependencies
- [ ] 1.3 Create `requirements.txt` with runtime dependencies (fastapi, uvicorn, pyyaml, httpx, pydantic)
- [ ] 1.4 Create `requirements-dev.txt` with development dependencies (pytest, black, isort, mypy)
- [ ] 1.5 Set up `.gitignore` for Python project
- [ ] 1.6 Create basic `README.md` with installation and usage instructions

## 2. Configuration System

- [ ] 2.1 Define Pydantic models for configuration schema (ServerConfig, WebhookConfig, LLMConfig, etc.)
- [ ] 2.2 Implement YAML configuration loader with environment variable interpolation
- [ ] 2.3 Add configuration validation with meaningful error messages
- [ ] 2.4 Implement default values for optional configuration fields
- [ ] 2.5 Create `config.yaml` example file with all options documented
- [ ] 2.6 Add secret masking for API keys in logs
- [ ] 2.7 Write unit tests for configuration loading and validation

## 3. Core Utilities and Base Classes

- [ ] 3.1 Set up structured logging with JSON formatter
- [ ] 3.2 Create custom exception classes (WeChatButlerError, ConfigurationError, ValidationError)
- [ ] 3.3 Implement base classes for conditions and actions
- [ ] 3.4 Create utility functions for common operations (sanitization, validation)
- [ ] 3.5 Set up async HTTP client with connection pooling

## 4. Webhook Receiver

- [ ] 4.1 Create FastAPI endpoint `/webhook/message` accepting POST requests
- [ ] 4.2 Implement HMAC-SHA256 signature verification middleware
- [ ] 4.3 Add payload validation for required fields (talker, sender, content, type, timestamp)
- [ ] 4.4 Implement message standardization to internal format
- [ ] 4.5 Add rate limiting (default 100 req/min per IP)
- [ ] 4.6 Implement error logging with sanitized payloads
- [ ] 4.7 Write unit tests for webhook handler
- [ ] 4.8 Write integration tests for full webhook flow

## 5. Mention Detector

- [ ] 5.1 Implement @mention pattern detection with configurable bot name
- [ ] 5.2 Add support for WeChat's Unicode separator in mentions
- [ ] 5.3 Implement query extraction after mention
- [ ] 5.4 Handle edge cases (empty query, multiple mentions, @all vs @bot)
- [ ] 5.5 Add case-insensitive matching for bot name
- [ ] 5.6 Write unit tests for mention detection scenarios

## 6. LLM Client

- [ ] 6.1 Create abstract `LLMProvider` base class
- [ ] 6.2 Implement `OpenAIProvider` with GPT-3.5/GPT-4 support
- [ ] 6.3 Implement `ClaudeProvider` with Claude API support
- [ ] 6.4 Add async API calls with timeout handling (default 30s)
- [ ] 6.5 Implement retry logic with exponential backoff
- [ ] 6.6 Add cost tracking and token usage logging
- [ ] 6.7 Support configurable model, temperature, and max_tokens
- [ ] 6.8 Create unified response format across providers
- [ ] 6.9 Write unit tests with mocked API responses

## 7. WeChat Sender

- [ ] 7.1 Implement HTTP client for wechat-sendmsg API
- [ ] 7.2 Add message sending function with retry logic (default 3 attempts)
- [ ] 7.3 Implement error handling for various failure modes (unavailable, invalid contact, window not ready)
- [ ] 7.4 Add async message sending support
- [ ] 7.5 Implement send status tracking and result objects
- [ ] 7.6 Add configuration for endpoint URL, timeout, and retry settings
- [ ] 7.7 Write unit tests with mocked wechat-sendmsg responses

## 8. Health Endpoint

- [ ] 8.1 Create `/health` endpoint returning service status
- [ ] 8.2 Implement component health checks (webhook, LLM, wechat-sender)
- [ ] 8.3 Add `/health/live` liveness probe endpoint
- [ ] 8.4 Add `/health/ready` readiness probe endpoint
- [ ] 8.5 Include memory usage metrics in health response
- [ ] 8.6 Add message processing statistics (total, processed, failed, avg time)
- [ ] 8.7 Implement dependency connectivity checks
- [ ] 8.8 Write unit tests for health endpoint

## 9. Main Application Integration

- [ ] 9.1 Create main FastAPI application setup
- [ ] 9.2 Wire up all components (config, webhook, mention detector, LLM, sender)
- [ ] 9.3 Implement main message processing flow
- [ ] 9.4 Add startup and shutdown event handlers
- [ ] 9.5 Implement graceful error handling at application level
- [ ] 9.6 Create `main.py` entry point script
- [ ] 9.7 Add command-line argument parsing (--config, --port, etc.)

## 10. Testing

- [ ] 10.1 Set up pytest configuration and fixtures
- [ ] 10.2 Write unit tests for configuration system (>80% coverage)
- [ ] 10.3 Write unit tests for webhook receiver (>80% coverage)
- [ ] 10.4 Write unit tests for mention detector (>80% coverage)
- [ ] 10.5 Write unit tests for LLM client (>70% coverage)
- [ ] 10.6 Write unit tests for wechat sender (>70% coverage)
- [ ] 10.7 Write integration tests for full message flow
- [ ] 10.8 Write end-to-end test simulating @mention → joke scenario
- [ ] 10.9 Set up test coverage reporting

## 11. Documentation

- [ ] 11.1 Document API endpoints with OpenAPI/Swagger annotations
- [ ] 11.2 Create configuration reference documentation
- [ ] 11.3 Write deployment guide (systemd, Docker)
- [ ] 11.4 Create troubleshooting guide
- [ ] 11.5 Document environment variables and secrets management

## 12. Deployment and DevOps

- [ ] 12.1 Create systemd service file
- [ ] 12.2 Create Dockerfile for containerized deployment
- [ ] 12.3 Create docker-compose.yml with dependent services
- [ ] 12.4 Set up GitHub Actions CI/CD pipeline
- [ ] 12.5 Add linting and formatting checks to CI
- [ ] 12.6 Add test execution to CI pipeline
- [ ] 12.7 Create release script with versioning
