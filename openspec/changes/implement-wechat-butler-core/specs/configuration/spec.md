## ADDED Requirements

### Requirement: Load configuration from YAML file
The configuration system SHALL load settings from a YAML configuration file.

#### Scenario: Load existing config file
- **GIVEN** a config.yaml file exists with valid settings
- **WHEN** the system starts
- **THEN** the system SHALL load and parse the configuration successfully

#### Scenario: Missing config file
- **GIVEN** config.yaml does not exist
- **WHEN** the system starts
- **THEN** the system SHALL raise ConfigurationError with clear message indicating file is missing

#### Scenario: Invalid YAML syntax
- **GIVEN** config.yaml contains invalid YAML syntax
- **WHEN** the system attempts to load configuration
- **THEN** the system SHALL raise ConfigurationError with parse error details

### Requirement: Validate configuration structure
The configuration system SHALL validate that required fields are present and have correct types.

#### Scenario: Valid complete configuration
- **GIVEN** config.yaml contains all required fields with valid types
- **WHEN** loading configuration
- **THEN** the system SHALL accept the configuration and start normally

#### Scenario: Missing required field
- **GIVEN** config.yaml is missing required field `wechat.sendmsg_url`
- **WHEN** loading configuration
- **THEN** the system SHALL raise ConfigurationError indicating missing required field

#### Scenario: Invalid field type
- **GIVEN** config.yaml has `server.port: "8080"` (string instead of integer)
- **WHEN** loading configuration
- **THEN** the system SHALL raise ValidationError with type mismatch details

#### Scenario: Invalid enum value
- **GIVEN** config.yaml has `llm.provider: "invalid_provider"`
- **WHEN** loading configuration
- **THEN** the system SHALL raise ValidationError indicating invalid provider choice

### Requirement: Support environment variable interpolation
The configuration system SHALL support reading values from environment variables.

#### Scenario: Environment variable substitution
- **GIVEN** config.yaml contains `api_key: "${OPENAI_API_KEY}"`
- **AND** environment variable OPENAI_API_KEY is set to "sk-abc123"
- **WHEN** loading configuration
- **THEN** the system SHALL resolve the value to "sk-abc123"

#### Scenario: Missing environment variable
- **GIVEN** config references `${MISSING_VAR}`
- **AND** the environment variable is not set
- **WHEN** loading configuration
- **THEN** the system SHALL raise ConfigurationError indicating missing environment variable

#### Scenario: Default value for env var
- **GIVEN** config contains `port: "${PORT:-8080}"`
- **AND** PORT environment variable is not set
- **WHEN** loading configuration
- **THEN** the system SHALL use default value 8080

### Requirement: Provide default values
The configuration system SHALL provide sensible defaults for optional fields.

#### Scenario: Use default port
- **GIVEN** config.yaml does not specify `server.port`
- **WHEN** loading configuration
- **THEN** the system SHALL use default value 8080

#### Scenario: Use default log level
- **GIVEN** config.yaml does not specify `logging.level`
- **WHEN** loading configuration
- **THEN** the system SHALL use default value "INFO"

#### Scenario: Override default with explicit value
- **GIVEN** config.yaml sets `server.port: 3000`
- **WHEN** loading configuration
- **THEN** the system SHALL use value 3000 instead of default 8080

### Requirement: Hot-reload configuration
The configuration system SHALL support hot-reloading of configuration without restart.

#### Scenario: Reload on file change
- **GIVEN** configuration hot-reload is enabled
- **WHEN** config.yaml is modified
- **THEN** the system SHALL detect the change and reload configuration within 5 seconds

#### Scenario: Validation on reload
- **GIVEN** hot-reload is enabled
- **WHEN** config.yaml is modified with invalid values
- **THEN** the system SHALL log error and keep previous valid configuration

#### Scenario: Disable hot-reload
- **GIVEN** hot-reload is disabled in config
- **WHEN** config.yaml is modified
- **THEN** the system SHALL NOT reload and continue using original configuration

### Requirement: Access configuration values
The configuration system SHALL provide easy access to configuration values throughout the application.

#### Scenario: Access nested config
- **GIVEN** configuration is loaded
- **WHEN** code accesses `config.wechat.sendmsg_url`
- **THEN** the system SHALL return the configured URL value

#### Scenario: Type-safe access
- **GIVEN** configuration defines `server.port` as integer
- **WHEN** accessing the value
- **THEN** the system SHALL return an integer type (not string)

### Requirement: Configuration structure
The configuration system SHALL support the following configuration sections:

#### Scenario: Server configuration
- **GIVEN** config contains `server` section with host, port, debug settings
- **WHEN** loading configuration
- **THEN** the system SHALL validate and load server settings

#### Scenario: Webhook configuration
- **GIVEN** config contains `webhook` section with secret and path
- **WHEN** loading configuration
- **THEN** the system SHALL validate and load webhook settings

#### Scenario: LLM configuration
- **GIVEN** config contains `llm` section with provider, api_key, model, temperature
- **WHEN** loading configuration
- **THEN** the system SHALL validate and load LLM settings

#### Scenario: WeChat configuration
- **GIVEN** config contains `wechat` section with sendmsg_url, timeout, retry settings
- **WHEN** loading configuration
- **THEN** the system SHALL validate and load WeChat settings

#### Scenario: Logging configuration
- **GIVEN** config contains `logging` section with level, file, rotation settings
- **WHEN** loading configuration
- **THEN** the system SHALL validate and load logging settings

### Requirement: Secret masking in logs
The configuration system SHALL mask sensitive values when logging configuration.

#### Scenario: Mask API keys in logs
- **GIVEN** configuration contains `api_key: "sk-secret123"`
- **WHEN** the system logs the configuration
- **THEN** API keys SHALL be displayed as "***" or truncated (e.g., "sk...123")

#### Scenario: Mask webhook secrets
- **GIVEN** configuration contains `webhook.secret`
- **WHEN** logging or displaying config
- **THEN** the secret SHALL be masked
