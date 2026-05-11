## Purpose

Docker container configuration via environment variables, config template, and entrypoint script.

## Requirements

### Requirement: Config template with full environment variable coverage
The system SHALL provide a `config.yaml.template` where every configuration field uses `${ENV_VAR}` syntax, enabling complete configuration via environment variables.

#### Scenario: All server config fields covered by env vars
- **WHEN** environment variables `SERVER_HOST`, `SERVER_PORT`, `SERVER_LOG_LEVEL` are set
- **THEN** the corresponding `server.host`, `server.port`, `server.log_level` fields in config SHALL use those values

#### Scenario: All LLM config fields covered by env vars
- **WHEN** environment variables `LLM_PROVIDER`, `OPENAI_API_KEY`, `LLM_BASE_URL`, `LLM_DEFAULT_MODEL`, `LLM_MAX_TOKENS`, `LLM_TEMPERATURE` are set
- **THEN** the corresponding `llm.*` fields in config SHALL use those values

#### Scenario: All MCP config fields covered by env vars
- **WHEN** environment variables `MCP_CHATSELL_API_URL`, `MCP_IDLE_TIMEOUT`, `MCP_CONNECT_TIMEOUT` are set
- **THEN** the corresponding `mcp.*` fields in config SHALL use those values

#### Scenario: Auth config covered by env var
- **WHEN** environment variable `BUTLER_API_KEY` is set
- **THEN** the `auth.api_key` field in config SHALL use that value

#### Scenario: Prompts directory covered by env var
- **WHEN** environment variable `PROMPTS_DIRECTORY` is set
- **THEN** the `prompts.directory` field in config SHALL use that value

### Requirement: Entrypoint script with config fallback
The system SHALL provide an `entrypoint.sh` that checks for a user-mounted `config.yaml` and falls back to the template if not present.

#### Scenario: User mounts custom config.yaml
- **WHEN** a `config.yaml` is volume-mounted at `/app/config.yaml`
- **THEN** the entrypoint SHALL use the mounted file and NOT overwrite it with the template

#### Scenario: No config.yaml mounted
- **WHEN** no `config.yaml` exists at `/app/config.yaml`
- **THEN** the entrypoint SHALL copy `config.yaml.template` to `config.yaml` and proceed

#### Scenario: Entrypoint launches application
- **WHEN** the entrypoint script runs
- **THEN** it SHALL execute `butler --config /app/config.yaml` as the final command

### Requirement: Environment variable defaults in Dockerfile
The system SHALL set sensible default values for environment variables via `ENV` directives in the Dockerfile.

#### Scenario: Default server port
- **WHEN** `SERVER_PORT` is not explicitly set at runtime
- **THEN** the default value SHALL be `8837`

#### Scenario: Default MCP URL for Docker network
- **WHEN** `MCP_CHATSELL_API_URL` is not explicitly set at runtime
- **THEN** the default value SHALL be `http://chatshell:5030/mcp` (Docker network DNS)

#### Scenario: Default log level
- **WHEN** `SERVER_LOG_LEVEL` is not explicitly set at runtime
- **THEN** the default value SHALL be `info`

### Requirement: Prompts directory volume mount support
The system SHALL support volume mounting of the prompts directory for custom prompt YAML files.

#### Scenario: Custom prompts via volume mount
- **WHEN** a volume is mounted at `/app/prompts`
- **THEN** the application SHALL load prompt YAML files from the mounted directory

#### Scenario: Default prompts included in image
- **WHEN** no volume is mounted for prompts
- **THEN** the application SHALL use the default prompts directory included in the image
