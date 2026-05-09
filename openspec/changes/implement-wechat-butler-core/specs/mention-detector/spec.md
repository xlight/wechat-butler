## ADDED Requirements

### Requirement: Detect @mention patterns in messages
The mention detector SHALL identify when a message contains an @mention directed at the bot.

#### Scenario: Simple @mention at start
- **WHEN** message content is "@机器人 讲个段子"
- **THEN** the system SHALL detect the bot is mentioned and extract "讲个段子" as the query

#### Scenario: @mention in middle of message
- **WHEN** message content is "大家好，@机器人 请讲个笑话"
- **THEN** the system SHALL detect the mention and extract "请讲个笑话" as the query

#### Scenario: Multiple @mentions
- **WHEN** message content is "@张三 @机器人 你好"
- **THEN** the system SHALL detect the bot mention specifically and extract "你好"

#### Scenario: No @mention of bot
- **WHEN** message content is "大家好" or "@张三 你好"
- **THEN** the system SHALL return None indicating bot is not mentioned

### Requirement: Configurable bot nickname
The mention detector SHALL use the bot nickname configured in config.yaml to match @mentions.

#### Scenario: Custom bot name
- **GIVEN** bot name is configured as "小助手" in config.yaml
- **WHEN** message contains "@小助手 帮助"
- **THEN** the system SHALL detect the mention using the configured name

#### Scenario: Case insensitive matching
- **GIVEN** bot name is configured as "Bot"
- **WHEN** message contains "@bot 你好" or "@BOT 你好"
- **THEN** the system SHALL detect the mention regardless of case

### Requirement: Extract query after mention
The mention detector SHALL extract the text following the @mention as the user query.

#### Scenario: Extract simple query
- **WHEN** message is "@机器人 讲个程序员笑话"
- **THEN** the system SHALL return extracted query "讲个程序员笑话" with mention position info

#### Scenario: Handle extra whitespace
- **WHEN** message is "@机器人    多个空格"
- **THEN** the system SHALL trim whitespace and return "多个空格"

#### Scenario: Empty query after mention
- **WHEN** message is "@机器人" with no text following
- **THEN** the system SHALL return empty string as query

### Requirement: Support WeChat mention format
The mention detector SHALL handle WeChat's specific @mention formatting.

#### Scenario: WeChat @nickname format
- **WHEN** WeChat sends @mention in format "@机器人 消息内容" (with special Unicode separator)
- **THEN** the system SHALL correctly parse and extract "消息内容"

#### Scenario: Group chat @all vs @bot
- **WHEN** message contains "@所有人 @机器人 测试"
- **THEN** the system SHALL distinguish @所有人 from @机器人 and extract "测试"

### Requirement: Return structured mention data
The mention detector SHALL return structured data when mention is detected.

#### Scenario: Return mention info object
- **WHEN** bot is mentioned in a message
- **THEN** the system SHALL return an object containing:
  - `mentioned`: true
  - `bot_name`: the matched bot name
  - `query`: extracted text after mention
  - `position`: start/end indices of mention in original content

#### Scenario: Return negative result
- **WHEN** bot is not mentioned
- **THEN** the system SHALL return an object with `mentioned`: false and `query`: null
