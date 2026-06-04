from wechat_butler.config import LLMConfig


class ModelNotFoundError(Exception):
    pass


class LLMRouter:
    def __init__(self, config: LLMConfig):
        self._config = config
        self._model_map: dict[str, object] = {m.id: m for m in config.models}

    def resolve_model(self, model_id: str | None) -> tuple[str, str | None, str | None, str]:
        effective_id = model_id or self._config.default_model
        if effective_id not in self._model_map and effective_id != self._config.default_model:
            raise ModelNotFoundError(
                f"Model '{effective_id}' is not configured. "
                f"Available: {sorted(self._model_map.keys())} or default '{self._config.default_model}'"
            )

        model_cfg = self._model_map.get(effective_id)
        if model_cfg:
            provider = getattr(model_cfg, "provider", None) or self._config.provider
            api_key = getattr(model_cfg, "api_key", None) or self._config.api_key
            base_url = getattr(model_cfg, "base_url", None) or self._config.base_url
        else:
            provider = self._config.provider
            api_key = self._config.api_key
            base_url = self._config.base_url

        litellm_model = f"{provider}/{effective_id}"
        return litellm_model, api_key, base_url, effective_id

    def get_tools_schema(self, mcp_tools: list) -> list[dict]:
        tools = []
        for tool in mcp_tools:
            tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema or {"type": "object", "properties": {}},
                },
            })
        return tools

    def list_models(self) -> list[dict]:
        result = []
        for m in self._config.models:
            result.append({
                "id": m.id,
                "name": m.name,
                "provider": m.provider or self._config.provider,
            })
        return result
