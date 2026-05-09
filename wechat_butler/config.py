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


class PromptsConfig(BaseModel):
    directory: str = "prompts"


class AppConfig(BaseModel):
    server: ServerConfig = ServerConfig()
    llm: LLMConfig = LLMConfig()
    mcp: MCPConfig = MCPConfig()
    auth: AuthConfig = AuthConfig()
    prompts: PromptsConfig = PromptsConfig()


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
            result[k] = [_interpolate_dict(i) if isinstance(i, dict) else _interpolate_env(i) if isinstance(i, str) else i for i in v]
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

    def update_llm(self, updates: dict) -> AppConfig:
        llm = self.config.llm
        if "provider" in updates:
            llm.provider = updates["provider"]
        if "api_key" in updates:
            llm.api_key = updates["api_key"]
        if "base_url" in updates:
            llm.base_url = updates["base_url"]
        if "default_model" in updates:
            llm.default_model = updates["default_model"]
        if "max_tokens" in updates:
            llm.max_tokens = updates["max_tokens"]
        if "temperature" in updates:
            llm.temperature = updates["temperature"]
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
