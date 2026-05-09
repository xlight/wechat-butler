import litellm

from wechat_butler.config import LLMConfig, mask_api_key


class LLMRouter:
    def __init__(self, config: LLMConfig):
        self._config = config
        self._model_map: dict[str, LLMConfig.models.__class__] = {}
        for m in config.models:
            self._model_map[m.id] = m

    def resolve_model(self, model_id: str | None) -> tuple[str, str | None, str | None]:
        model_id = model_id or self._config.default_model
        model_cfg = self._model_map.get(model_id)

        if model_cfg:
            provider = model_cfg.provider or self._config.provider
            api_key = model_cfg.api_key or self._config.api_key
            base_url = model_cfg.base_url or self._config.base_url
        else:
            provider = self._config.provider
            api_key = self._config.api_key
            base_url = self._config.base_url

        litellm_model = f"{provider}/{model_id}"
        return litellm_model, api_key, base_url

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
