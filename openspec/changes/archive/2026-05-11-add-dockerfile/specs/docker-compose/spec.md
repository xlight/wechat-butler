## ADDED Requirements

### Requirement: Docker Compose orchestration
The system SHALL provide a `docker-compose.yml` that orchestrates the WeChat Butler service and the ChatShell MCP service on a shared network.

#### Scenario: Both services start together
- **WHEN** `docker compose up` is executed
- **THEN** both `wechat-butler` and `chatshell` services SHALL start and be reachable on the `butler-net` network

#### Scenario: Butler reaches ChatShell via DNS
- **WHEN** the butler service starts in the compose stack
- **THEN** it SHALL be able to reach the chatshell service at `http://chatshell:5030/mcp` via Docker network DNS

### Requirement: Custom bridge network
The system SHALL define a custom bridge network `butler-net` for service communication.

#### Scenario: Services on same network
- **WHEN** both services are running
- **THEN** they SHALL be attached to the `butler-net` network and can resolve each other by service name

#### Scenario: Network isolation
- **WHEN** an external client attempts to access the chatshell service directly
- **THEN** the chatshell service SHALL NOT be exposed to the host by default (no `ports` mapping for chatshell)

### Requirement: Butler service port exposure
The system SHALL expose the butler service port to the host.

#### Scenario: Butler accessible from host
- **WHEN** the compose stack is running
- **THEN** the butler service SHALL be accessible at `http://localhost:${SERVER_PORT:-8837}` from the host machine

### Requirement: Environment variable configuration in compose
The system SHALL support environment variable configuration via `.env` file and `environment:` directives in docker-compose.yml.

#### Scenario: Env file loaded by compose
- **WHEN** a `.env` file exists in the project root
- **THEN** docker compose SHALL load variables from it and pass them to the butler service

#### Scenario: Required API keys configurable
- **WHEN** `OPENAI_API_KEY` and `BUTLER_API_KEY` are set in the environment
- **THEN** the butler service SHALL receive these values and use them for LLM and auth configuration

### Requirement: Volume mounts for persistent data
The system SHALL define volume mount points for config.yaml and prompts directory.

#### Scenario: Config override via volume
- **WHEN** a custom `config.yaml` is mounted at `./config.yaml:/app/config.yaml`
- **THEN** the butler service SHALL use the mounted configuration

#### Scenario: Prompts override via volume
- **WHEN** a custom prompts directory is mounted at `./prompts:/app/prompts`
- **THEN** the butler service SHALL load prompts from the mounted directory
