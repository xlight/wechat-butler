## ADDED Requirements

### Requirement: Built-in prompt templates
The system SHALL provide built-in prompt templates: 群聊总结, 待办提取, 话题分析, 情绪分析, 人物画像. Each template SHALL have a name, description, content, and optional variables.

#### Scenario: List built-in prompts
- **WHEN** GET /api/v1/ai/prompts is called
- **THEN** response includes all built-in prompts with name, description, and content

### Requirement: Custom prompt CRUD
The system SHALL support creating, reading, updating, and deleting custom prompts. Custom prompts SHALL be stored in a prompts/ directory as YAML files.

#### Scenario: Create custom prompt
- **WHEN** POST /api/v1/ai/prompts with name, description, content
- **THEN** prompt is saved and returned with an assigned ID

#### Scenario: Update custom prompt
- **WHEN** PUT /api/v1/ai/prompts/:id with updated content
- **THEN** prompt is updated and saved

#### Scenario: Delete custom prompt
- **WHEN** DELETE /api/v1/ai/prompts/:id
- **THEN** prompt is removed; built-in prompts cannot be deleted

### Requirement: Prompt variable substitution
The system SHALL support variable placeholders in prompt content using {variableName} syntax. Variables SHALL be substituted with provided values before sending to LLM.

#### Scenario: Variable substitution
- **WHEN** prompt content contains "{sessionName}" and variables {"sessionName": "工作群"} are provided
- **THEN** "{sessionName}" is replaced with "工作群" in the final content

#### Scenario: Missing variable
- **WHEN** a required variable is not provided
- **THEN** the placeholder is left as-is (not removed, not errored)
