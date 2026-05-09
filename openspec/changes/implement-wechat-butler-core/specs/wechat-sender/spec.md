## ADDED Requirements

### Requirement: Send text messages via HTTP API
The wechat sender SHALL send text messages by calling wechat-sendmsg HTTP API.

#### Scenario: Send simple text message
- **GIVEN** wechat-sendmsg is running at configured URL
- **WHEN** the system sends a text message to contact "filehelper" with content "你好"
- **THEN** the system SHALL make HTTP POST request to wechat-sendmsg and return success

#### Scenario: Send to group chat
- **GIVEN** target is a group chat name "工作群"
- **WHEN** the system sends message "开会通知"
- **THEN** the system SHALL deliver message to the group chat

#### Scenario: Send message with @mention
- **WHEN** the system sends message containing "@张三 请查看"
- **THEN** the message SHALL be delivered with proper @mention formatting

### Requirement: Handle wechat-sendmsg errors
The wechat sender SHALL handle errors from wechat-sendmsg gracefully.

#### Scenario: wechat-sendmsg unavailable
- **GIVEN** wechat-sendmsg service is not running
- **WHEN** the system attempts to send a message
- **THEN** the system SHALL raise WeChatSendException after retry attempts

#### Scenario: Invalid contact name
- **GIVEN** contact name "不存在的用户" is not found
- **WHEN** the system attempts to send message
- **THEN** wechat-sendmsg returns error and the system SHALL log the failure

#### Scenario: WeChat window not ready
- **GIVEN** WeChat window is minimized or not responding
- **WHEN** sending message
- **THEN** wechat-sendmsg SHALL handle window management and the system SHALL receive appropriate error

### Requirement: Retry logic for failed sends
The wechat sender SHALL retry failed message sends with exponential backoff.

#### Scenario: Retry on transient failure
- **GIVEN** first attempt fails due to temporary network error
- **WHEN** the system attempts to send with max_retries=3
- **THEN** the system SHALL retry up to 3 times with exponential backoff before failing

#### Scenario: Success on retry
- **GIVEN** first attempt fails, second attempt succeeds
- **WHEN** sending with retry enabled
- **THEN** the system SHALL return success after second attempt

#### Scenario: No retry for permanent errors
- **GIVEN** wechat-sendmsg returns 400 Bad Request (invalid contact)
- **WHEN** the system attempts to send
- **THEN** the system SHALL NOT retry and return error immediately

### Requirement: Support message types
The wechat sender SHALL support different message types beyond text.

#### Scenario: Send text message (type 1)
- **WHEN** the system sends message with type=1
- **THEN** a text message SHALL be delivered

#### Scenario: Send markdown-style formatting
- **WHEN** the system sends message with markdown formatting "**粗体**"
- **THEN** the formatted text SHALL be delivered (if wechat-sendmsg supports it)

### Requirement: Async message sending
The wechat sender SHALL send messages asynchronously.

#### Scenario: Non-blocking send
- **WHEN** sending a message that takes 2 seconds to process
- **THEN** the system SHALL not block other operations during those 2 seconds

#### Scenario: Concurrent sends
- **WHEN** multiple messages are queued to send simultaneously
- **THEN** the system SHALL send them concurrently without blocking each other

### Requirement: Send status tracking
The wechat sender SHALL provide status information about sent messages.

#### Scenario: Return send result
- **WHEN** a message is sent successfully
- **THEN** the system SHALL return result object containing:
  - `success`: true
  - `message_id`: identifier (if available)
  - `sent_at`: timestamp
  - `recipient`: target contact/group

#### Scenario: Return failure details
- **WHEN** message sending fails
- **THEN** the system SHALL return result with:
  - `success`: false
  - `error_code`: error classification
  - `error_message`: human-readable error
  - `retryable`: whether retry might succeed

### Requirement: Configuration
The wechat sender SHALL be configurable via config.yaml.

#### Scenario: Configure endpoint URL
- **GIVEN** config sets `wechat.sendmsg_url: http://192.168.1.100:8000`
- **WHEN** sending messages
- **THEN** the system SHALL use the configured URL

#### Scenario: Configure timeout
- **GIVEN** config sets `wechat.timeout: 60` seconds
- **WHEN** sending a message
- **THEN** the system SHALL wait up to 60 seconds before timing out

#### Scenario: Configure retry
- **GIVEN** config sets `wechat.retry.max_attempts: 5`
- **WHEN** sending fails
- **THEN** the system SHALL retry up to 5 times
