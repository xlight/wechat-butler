## ADDED Requirements

### Requirement: Health check endpoint returns service status
The health endpoint SHALL expose a public endpoint at `/health` that returns the service health status.

#### Scenario: Service is healthy
- **GIVEN** all components are functioning normally
- **WHEN** a GET request is made to `/health`
- **THEN** the system SHALL return HTTP 200 with status "healthy"

#### Scenario: Service is starting up
- **GIVEN** service is initializing but not fully ready
- **WHEN** a request is made to `/health`
- **THEN** the system SHALL return HTTP 503 with status "starting"

#### Scenario: Service has degraded functionality
- **GIVEN** one component (e.g., LLM client) is unavailable but core functions work
- **WHEN** a request is made to `/health`
- **THEN** the system SHALL return HTTP 200 with status "degraded" and details about failing component

### Requirement: Health check returns detailed metrics
The health endpoint SHALL include detailed system information in the response.

#### Scenario: Return full health information
- **WHEN** requesting `/health` while service is healthy
- **THEN** the response SHALL include:
  - `status`: "healthy" | "degraded" | "unhealthy"
  - `version`: application version
  - `uptime`: seconds since start
  - `timestamp`: current ISO timestamp
  - `components`: status of each component (webhook, llm, wechat-sender)

#### Scenario: Component health details
- **GIVEN** service is running
- **WHEN** requesting health status
- **THEN** the response SHALL include component status for:
  - `webhook_receiver`: "ok" or error details
  - `llm_client`: "ok" or error details
  - `wechat_sender`: "ok" or error details

### Requirement: Health check no authentication required
The health endpoint SHALL be accessible without authentication.

#### Scenario: Public access to health endpoint
- **GIVEN** API authentication is enabled
- **WHEN** making request to `/health` without API key
- **THEN** the system SHALL return health status without requiring authentication

#### Scenario: Load balancer health check
- **GIVEN** load balancer polls `/health` periodically
- **WHEN** making health check requests
- **THEN** the system SHALL respond without auth requirements

### Requirement: Liveness and readiness probes
The health endpoint SHALL support Kubernetes-style liveness and readiness probes.

#### Scenario: Liveness probe
- **WHEN** requesting `/health/live`
- **THEN** the system SHALL return HTTP 200 if process is running, regardless of component health

#### Scenario: Readiness probe
- **GIVEN** all components are initialized and ready
- **WHEN** requesting `/health/ready`
- **THEN** the system SHALL return HTTP 200 indicating ready to accept traffic

#### Scenario: Not ready
- **GIVEN** required components are not initialized
- **WHEN** requesting `/health/ready`
- **THEN** the system SHALL return HTTP 503 with details about uninitialized components

### Requirement: Health check performance
The health endpoint SHALL respond quickly to avoid timeouts.

#### Scenario: Fast health response
- **WHEN** making request to `/health`
- **THEN** the system SHALL respond within 100ms

#### Scenario: Background health checks
- **GIVEN** component health is checked periodically in background
- **WHEN** requesting `/health`
- **THEN** the system SHALL return cached health status rather than performing synchronous checks

### Requirement: Memory usage reporting
The health endpoint SHALL report current memory usage.

#### Scenario: Include memory metrics
- **WHEN** requesting `/health` with full details
- **THEN** the response SHALL include:
  - `memory.usage`: current memory usage in bytes
  - `memory.percent`: memory usage percentage
  - `memory.limit`: configured memory limit (if any)

### Requirement: Message processing metrics
The health endpoint SHALL include message processing statistics.

#### Scenario: Include processing stats
- **GIVEN** service has processed messages
- **WHEN** requesting `/health`
- **THEN** the response SHALL include:
  - `messages.total`: total messages received
  - `messages.processed`: successfully processed messages
  - `messages.failed`: failed message processing count
  - `messages.avg_processing_time_ms`: average processing time

### Requirement: Dependency health checks
The health endpoint SHALL check health of external dependencies.

#### Scenario: Check wechat-sendmsg connectivity
- **GIVEN** wechat-sendmsg is configured
- **WHEN** performing health check
- **THEN** the system SHALL verify connectivity to wechat-sendmsg and report status

#### Scenario: Check LLM API connectivity
- **GIVEN** LLM is enabled in config
- **WHEN** performing health check
- **THEN** the system SHALL verify LLM API accessibility (optional lightweight check)

#### Scenario: Skip optional dependency checks
- **GIVEN** LLM is disabled in config
- **WHEN** performing health check
- **THEN** the system SHALL NOT check LLM connectivity and report it as "disabled"
