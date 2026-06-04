import os
import re
from pathlib import Path

import yaml
from pydantic import BaseModel

_ENV_PATTERN = re.compile(r"\$\{(\w+)\}")


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8837
    log_level: str = "info"


class ModelConfig(BaseModel):
    id: str
    name: str
    provider: str | None = None
    api_key: str | None = None
    base_url: str | None = None


class LLMConfig(BaseModel):
    provider: str = "openai"
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    default_model: str = "gpt-4o"
    max_tokens: int = 4096
    temperature: float = 0.7
    models: list[ModelConfig] = []


class MCPConfig(BaseModel):
    chatshell_api_url: str = "http://127.0.0.1:5030/mcp"
    idle_timeout: int = 300
    connect_timeout: int = 10


class AuthConfig(BaseModel):
    api_key: str = ""


class BaseModeConfig(BaseModel):
    enabled: bool = True
    model: str | None = None
    max_tokens: int | None = None
    system_prompt: str | None = None


class ObserverModeConfig(BaseModeConfig):
    pass


class MentionModeConfig(BaseModeConfig):
    pass


class UserActionSubConfig(BaseModel):
    model: str | None = None
    max_tokens: int | None = None
    system_prompt: str | None = None


class UserActionsModeConfig(BaseModel):
    enabled: bool = True
    model: str | None = None
    max_tokens: int | None = None
    system_prompt: str | None = None
    analyze: UserActionSubConfig = UserActionSubConfig()
    draft_reply: UserActionSubConfig = UserActionSubConfig()
    free_chat: UserActionSubConfig = UserActionSubConfig()


class AgentModesConfig(BaseModel):
    observer: ObserverModeConfig = ObserverModeConfig()
    mention: MentionModeConfig = MentionModeConfig()
    user_actions: UserActionsModeConfig = UserActionsModeConfig()


class SafetyConfig(BaseModel):
    forbidden_send_sessions: list[str] = []


class RateLimitingTierConfig(BaseModel):
    max_concurrent: int


class RateLimitingConfig(BaseModel):
    max_concurrent: int = 5
    max_requests_per_minute: int = 10
    queue_timeout_seconds: int = 30
    per_session_max_per_minute: int = 5
    mention: RateLimitingTierConfig = RateLimitingTierConfig(max_concurrent=2)
    user_actions: RateLimitingTierConfig = RateLimitingTierConfig(max_concurrent=2)
    observer: RateLimitingTierConfig = RateLimitingTierConfig(max_concurrent=1)


class AppConfig(BaseModel):
    server: ServerConfig = ServerConfig()
    llm: LLMConfig = LLMConfig()
    mcp: MCPConfig = MCPConfig()
    auth: AuthConfig = AuthConfig()
    agent_modes: AgentModesConfig = AgentModesConfig()
    safety: SafetyConfig = SafetyConfig()
    rate_limiting: RateLimitingConfig = RateLimitingConfig()


def _interpolate_env(value: str) -> str:
    def _replace(match):
        return os.environ.get(match.group(1), match.group(0))
    return _ENV_PATTERN.sub(_replace, value)


def _interpolate_dict(d: dict) -> dict:
    result = {}
    for k, v in d.items():
        if isinstance(v, str):
            result[k] = _interpolate_env(v)
        elif isinstance(v, dict):
            result[k] = _interpolate_dict(v)
        elif isinstance(v, list):
            result[k] = [
                _interpolate_dict(i) if isinstance(i, dict) else _interpolate_env(i) if isinstance(i, str) else i
                for i in v
            ]
        else:
            result[k] = v
    return result


class ConfigManager:
    def __init__(self, config_path: str):
        self._path = config_path
        self.config: AppConfig = self._load()

    def _load(self) -> AppConfig:
        raw = yaml.safe_load(Path(self._path).read_text(encoding="utf-8"))
        if raw is None:
            raw = {}
        raw = _interpolate_dict(raw)
        return AppConfig(**raw)

    def reload(self) -> AppConfig:
        self.config = self._load()
        return self.config

    def get_masked(self) -> dict:
        data = self.config.model_dump()
        data["llm"]["api_key"] = mask_api_key(self.config.llm.api_key)
        for m in data["llm"]["models"]:
            if m.get("api_key"):
                m["api_key"] = mask_api_key(m["api_key"])
        return data


def mask_api_key(key: str) -> str:
    if not key or len(key) < 8:
        return "***"
    return f"{key[:5]}...{key[-3:]}"
