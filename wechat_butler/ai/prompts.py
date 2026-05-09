import re
from pathlib import Path

import yaml
from pydantic import BaseModel

_VAR_PATTERN = re.compile(r"\{(\w+)\}")


class Prompt(BaseModel):
    id: str
    name: str
    description: str
    content: str
    variables: list[str] = []
    builtin: bool = False


BUILTIN_PROMPTS = [
    Prompt(
        id="builtin-group-summary",
        name="群聊总结",
        description="总结群聊讨论的要点和关键信息",
        content="请总结以下群聊讨论的要点，包括：\n1. 主要话题\n2. 关键决策\n3. 待办事项\n\n群聊内容：\n{content}",
        variables=["content"],
        builtin=True,
    ),
    Prompt(
        id="builtin-todo-extract",
        name="待办提取",
        description="从聊天记录中提取待办事项",
        content="从以下聊天记录中提取所有待办事项，标注负责人和截止时间（如有）：\n\n{content}",
        variables=["content"],
        builtin=True,
    ),
    Prompt(
        id="builtin-topic-analysis",
        name="话题分析",
        description="分析聊天中的主要话题和讨论趋势",
        content="分析以下聊天记录中的主要话题，统计每个话题的讨论频率和参与人：\n\n{content}",
        variables=["content"],
        builtin=True,
    ),
    Prompt(
        id="builtin-sentiment-analysis",
        name="情绪分析",
        description="分析聊天中的情绪倾向",
        content="分析以下聊天记录中各参与者的情绪倾向（积极/消极/中性），标注情绪变化的关键节点：\n\n{content}",
        variables=["content"],
        builtin=True,
    ),
    Prompt(
        id="builtin-person-profile",
        name="人物画像",
        description="根据聊天记录生成人物画像",
        content="根据以下聊天记录，为 {sessionName} 生成人物画像，包括：\n1. 沟通风格\n2. 关注领域\n3. 活跃时间\n4. 关系网络\n\n聊天记录：\n{content}",
        variables=["sessionName", "content"],
        builtin=True,
    ),
]


def substitute(template: str, variables: dict[str, str]) -> str:
    def _replace(match):
        return variables.get(match.group(1), match.group(0))
    return _VAR_PATTERN.sub(_replace, template)


class PromptService:
    def __init__(self, directory: str = "prompts"):
        self._directory = Path(directory)
        self._custom_prompts: dict[str, Prompt] = {}
        self._load_custom()

    def _load_custom(self) -> None:
        self._custom_prompts.clear()
        if not self._directory.exists():
            return
        for f in self._directory.glob("*.yaml"):
            try:
                data = yaml.safe_load(f.read_text(encoding="utf-8"))
                if data and isinstance(data, dict):
                    prompt = Prompt(**data, builtin=False)
                    self._custom_prompts[prompt.id] = prompt
            except Exception:
                pass

    def list_all(self) -> list[Prompt]:
        return list(BUILTIN_PROMPTS) + list(self._custom_prompts.values())

    def get(self, prompt_id: str) -> Prompt | None:
        for p in BUILTIN_PROMPTS:
            if p.id == prompt_id:
                return p
        return self._custom_prompts.get(prompt_id)

    def create(self, name: str, description: str, content: str) -> Prompt:
        self._directory.mkdir(parents=True, exist_ok=True)
        prompt_id = f"custom-{len(self._custom_prompts) + 1:03d}"
        variables = _VAR_PATTERN.findall(content)
        prompt = Prompt(id=prompt_id, name=name, description=description, content=content, variables=variables, builtin=False)
        self._custom_prompts[prompt.id] = prompt
        self._save(prompt)
        return prompt

    def update(self, prompt_id: str, name: str | None = None, description: str | None = None, content: str | None = None) -> Prompt | None:
        prompt = self._custom_prompts.get(prompt_id)
        if not prompt:
            return None
        if name:
            prompt.name = name
        if description:
            prompt.description = description
        if content:
            prompt.content = content
            prompt.variables = _VAR_PATTERN.findall(content)
        self._save(prompt)
        return prompt

    def delete(self, prompt_id: str) -> bool:
        prompt = self._custom_prompts.get(prompt_id)
        if not prompt:
            return False
        f = self._directory / f"{prompt_id}.yaml"
        if f.exists():
            f.unlink()
        del self._custom_prompts[prompt_id]
        return True

    def _save(self, prompt: Prompt) -> None:
        self._directory.mkdir(parents=True, exist_ok=True)
        data = prompt.model_dump(exclude={"builtin"})
        (self._directory / f"{prompt.id}.yaml").write_text(
            yaml.dump(data, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )
