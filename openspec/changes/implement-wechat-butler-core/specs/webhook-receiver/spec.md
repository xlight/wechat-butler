## ADDED Requirements

### Requirement: Webhook endpoint accepts POST requests
The webhook receiver SHALL expose an HTTP endpoint at `/webhook/message` that accepts POST requests with JSON payloads.

#### Scenario: Valid webhook request
- **WHEN** a POST request is made to `/webhook/message` with a valid JSON payload containing message data
- **THEN** the system SHALL accept the request and return HTTP 200 status

#### Scenario: Invalid HTTP method
- **WHEN** a GET/PUT/DELETE request is made to `/webhook/message`
- **THEN** the system SHALL return HTTP 405 Method Not Allowed

### Requirement: Webhook payload validation
The webhook receiver SHALL validate incoming payloads contain required fields: `talker`, `sender`, `content`, `type`, and `timestamp`.

#### Scenario: Valid payload with all required fields
- **WHEN** a webhook payload contains all required fields with valid types
- **THEN** the system SHALL process the message and return HTTP 200

#### Scenario: Missing required field
- **WHEN** a webhook payload is missing the `content` field
- **THEN** the system SHALL return HTTP 400 Bad Request with error details indicating which field is missing

#### Scenario: Invalid field type
- **WHEN** a webhook payload has `type` field as string instead of integer
- **THEN** the system SHALL return HTTP 400 Bad Request indicating type validation error

### Requirement: Webhook authentication via HMAC signature
The webhook receiver SHALL verify HMAC-SHA256 signatures when `webhook.secret` is configured in config.yaml.

#### Scenario: Valid signature
- **WHEN** a request includes correct `X-Signature` header matching HMAC-SHA256 of payload body using configured secret
- **THEN** the system SHALL process the message and return HTTP 200

#### Scenario: Invalid signature
- **WHEN** a request includes `X-Signature` that does not match calculated HMAC
- **THEN** the system SHALL return HTTP 401 Unauthorized

#### Scenario: Missing signature when secret configured
- **WHEN** webhook secret is configured but request lacks `X-Signature` header
- **THEN** the system SHALL return HTTP 401 Unauthorized

#### Scenario: No authentication when secret not configured
- **WHEN** webhook secret is not configured in config.yaml
- **THEN** the system SHALL accept requests without signature verification and return HTTP 200 for valid payloads

### Requirement: Message standardization
The webhook receiver SHALL convert incoming payload to a standardized internal message format.

#### Scenario: Standardize valid message
- **WHEN** a valid webhook payload is received from chatshell-api
- **THEN** the system SHALL convert it to standardized format with fields: `id`, `timestamp`, `talker`, `sender`, `content`, `type`, and preserve original payload in `raw` field

### Requirement: Rate limiting
The webhook receiver SHALL enforce rate limiting to prevent abuse.

#### Scenario: Within rate limit
- **WHEN** webhook requests arrive at a rate below configured limit (default 100 requests/minute)
- **THEN** the system SHALL process all requests normally

#### Scenario: Exceeding rate limit
- **WHEN** webhook requests exceed the configured rate limit
- **THEN** the system SHALL return HTTP 429 Too Many Requests and drop excess requests

### Requirement: Error logging
The webhook receiver SHALL log all errors with sufficient detail for debugging.

#### Scenario: Validation error logging
- **WHEN** a webhook request fails validation
- **THEN** the system SHALL log the error with timestamp, client IP, error type, and request payload (sanitized)

#### Scenario: Authentication failure logging
- **WHEN** signature verification fails
- **THEN** the system SHALL log the attempt with timestamp, client IP, and failure reason
