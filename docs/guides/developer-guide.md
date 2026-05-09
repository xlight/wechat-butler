# WeChat Butler 开发者指南

## 文档信息

- **版本**: v1.0.0
- **创建日期**: 2025-11-22
- **最后更新**: 2025-11-22
- **适用对象**: 项目开发者和贡献者

---

## 📋 目录

- [开发环境搭建](#开发环境搭建)
- [项目结构说明](#项目结构说明)
- [代码规范](#代码规范)
- [开发流程](#开发流程)
- [测试指南](#测试指南)
- [调试技巧](#调试技巧)
- [发布流程](#发布流程)
- [贡献指南](#贡献指南)

---

## 开发环境搭建

### 环境要求

#### 1. 基础环境
- **Python**: 3.11 或更高版本
- **pip**: 最新版本
- **Git**: 版本控制
- **IDE**: VS Code、PyCharm 或任意文本编辑器

#### 2. 操作系统
- **推荐**: Ubuntu 22.04+ / macOS 12+
- **支持**: Windows 10/11 (WSL2 推荐)

### 安装步骤

#### 1. 克隆代码库
```bash
git clone https://github.com/your-username/wechat-butler.git
cd wechat-butler
```

#### 2. 创建虚拟环境
```bash
# 使用 venv
python -m venv venv

# 激活虚拟环境
# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

#### 3. 安装依赖
```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 或安装生产依赖
pip install -r requirements.txt
```

#### 4. 安装预提交钩子
```bash
pre-commit install
```

### 开发工具配置

#### VS Code 配置
```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

#### PyCharm 配置
1. 设置 Python 解释器为虚拟环境
2. 启用代码格式化（Black）
3. 配置测试运行器为 pytest
4. 启用类型检查

### 环境验证

运行验证脚本检查环境：
```bash
python scripts/check_environment.py
```

预期输出：
```
✅ Python 版本: 3.11.0
✅ 虚拟环境: 已激活
✅ 依赖包: 全部安装
✅ 开发工具: 已配置
```

---

## 项目结构说明

### 目录结构

```
wechat-butler/
├── src/                          # 源代码目录
│   ├── wechat_butler/           # 主包
│   │   ├── __init__.py
│   │   ├── main.py              # 程序入口
│   │   ├── config.py            # 配置管理
│   │   ├── server.py            # HTTP 服务器
│   │   ├── webhook.py           # Webhook 处理器
│   │   ├── rule_engine/         # 规则引擎
│   │   │   ├── __init__.py
│   │   │   ├── engine.py        # 规则引擎核心
│   │   │   ├── conditions.py    # 条件系统
│   │   │   ├── actions.py       # 动作系统
│   │   │   └── compiler.py      # 规则编译器
│   │   ├── executors/           # 执行器
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # 执行器基类
│   │   │   ├── wechat.py        # 微信消息执行器
│   │   │   ├── command.py       # 命令执行器
│   │   │   └── http.py          # HTTP 执行器
│   │   └── utils/               # 工具函数
│   │       ├── __init__.py
│   │       ├── logging.py       # 日志工具
│   │       └── validation.py    # 数据验证
├── tests/                       # 测试目录
│   ├── unit/                   # 单元测试
│   ├── integration/            # 集成测试
│   └── fixtures/               # 测试数据
├── config/                     # 配置文件
│   ├── config.yaml            # 主配置文件
│   └── config.example.yaml    # 配置示例
├── rules/                      # 规则文件
│   ├── basic.yaml             # 基础规则
│   └── advanced.yaml          # 高级规则
├── scripts/                    # 脚本目录
│   ├── check_environment.py   # 环境检查
│   ├── generate_docs.py       # 文档生成
│   └── release.py             # 发布脚本
├── docs/                       # 文档目录
├── .github/                    # GitHub 配置
│   └── workflows/             # CI/CD 工作流
├── requirements.txt           # 生产依赖
├── requirements-dev.txt       # 开发依赖
├── pyproject.toml            # 项目配置
├── README.md                  # 项目说明
└── .pre-commit-config.yaml   # 预提交配置
```

### 核心模块说明

#### 1. 配置管理 (config.py)
- 加载和验证 YAML 配置文件
- 环境变量支持
- 配置热重载
- 默认值管理

#### 2. 规则引擎 (rule_engine/)
- 规则加载和解析
- 条件评估系统
- 动作生成和执行
- 性能优化和缓存

#### 3. 执行器 (executors/)
- 微信消息发送
- 系统命令执行
- HTTP API 调用
- 插件系统支持

#### 4. HTTP 服务器 (server.py)
- FastAPI Web 服务器
- API 路由和中间件
- 认证和授权
- 错误处理和日志

---

## 代码规范

### Python 代码规范

#### 1. 遵循 PEP 8
- 使用 4 个空格缩进
- 行长度不超过 88 个字符（Black 默认）
- 导入分组和排序
- 命名规范：
  - 类名：`CamelCase`
  - 函数/变量：`snake_case`
  - 常量：`UPPER_CASE`

#### 2. 类型注解
```python
from typing import Dict, List, Optional, Any

def process_message(
    message: Dict[str, Any],
    rules: List[Rule],
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """处理消息并返回结果"""
    pass
```

#### 3. 文档字符串
```python
def calculate_score(content: str, keywords: List[str]) -> float:
    """
    计算消息内容与关键词的匹配分数。
    
    Args:
        content: 消息内容字符串
        keywords: 关键词列表
        
    Returns:
        匹配分数，范围 0.0-1.0
        
    Raises:
        ValueError: 如果内容为空
        
    Examples:
        >>> calculate_score("hello world", ["hello"])
        0.5
    """
    if not content:
        raise ValueError("内容不能为空")
    
    # 实现逻辑
    return 0.5
```

### 项目特定规范

#### 1. 错误处理
```python
class WeChatButlerError(Exception):
    """基础错误类"""
    pass

class RuleValidationError(WeChatButlerError):
    """规则验证错误"""
    def __init__(self, rule_name: str, message: str):
        super().__init__(f"规则 '{rule_name}' 验证失败: {message}")
        self.rule_name = rule_name
```

#### 2. 日志记录
```python
import logging

logger = logging.getLogger(__name__)

def process_webhook(payload: dict):
    logger.info("开始处理 Webhook 请求", extra={"payload_size": len(payload)})
    
    try:
        # 处理逻辑
        logger.debug("详细处理信息", extra={"step": "parsing"})
    except Exception as e:
        logger.error("处理失败", exc_info=True, extra={"error": str(e)})
        raise
```

#### 3. 配置管理
```python
from pydantic import BaseModel, Field

class ServerConfig(BaseModel):
    """服务器配置"""
    host: str = Field(default="0.0.0.0", description="监听地址")
    port: int = Field(default=8080, ge=1, le=65535, description="监听端口")
    debug: bool = Field(default=False, description="调试模式")
```

### 工具配置

#### 1. Black 代码格式化
```toml
# pyproject.toml
[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'
exclude = '''
/(
    \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | _build
  | buck-out
  | build
  | dist
)/
'''
```

#### 2. isort 导入排序
```toml
[tool.isort]
profile = "black"
line_length = 88
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true
```

#### 3. mypy 类型检查
```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
```

#### 4. 预提交钩子
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
  
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
  
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
  
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
```

---

## 开发流程

### 1. 获取最新代码
```bash
git pull origin main
git checkout -b feature/your-feature-name
```

### 2. 编写代码
```bash
# 激活虚拟环境
source venv/bin/activate

# 启动开发服务器（热重载）
python -m src.wechat_butler.main --reload

# 或使用脚本
./scripts/dev.sh
```

### 3. 运行测试
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/unit/test_rule_engine.py -v

# 运行测试并生成覆盖率报告
pytest --cov=src.wechat_butler --cov-report=html
```

### 4. 代码检查
```bash
# 运行预提交检查
pre-commit run --all-files

# 手动检查
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
```

### 5. 提交代码
```bash
# 添加更改
git add .

# 提交（预提交钩子会自动运行）
git commit -m "feat: 添加新功能描述"

# 推送到远程
git push origin feature/your-feature-name
```

### 6. 创建 Pull Request
1. 在 GitHub 创建 Pull Request
2. 填写 PR 描述，关联 Issue
3. 等待 CI 检查通过
4. 请求代码审查
5. 根据反馈修改代码
6. 合并到主分支

---

## 测试指南

### 测试结构

```
tests/
├── unit/                    # 单元测试
│   ├── test_config.py      # 配置测试
│   ├── test_rule_engine.py # 规则引擎测试
│   └── test_utils.py       # 工具函数测试
├── integration/            # 集成测试
│   ├── test_webhook.py     # Webhook 集成测试
│   └── test_api.py         # API 集成测试
├── fixtures/               # 测试数据
│   ├── messages/          # 消息数据
│   └── rules/             # 规则数据
└── conftest.py            # 测试配置
```

### 单元测试示例

```python
# tests/unit/test_rule_engine.py
import pytest
from src.wechat_butler.rule_engine import RuleEngine
from src.wechat_butler.rule_engine.conditions import KeywordCondition

class TestRuleEngine:
    @pytest.fixture
    def rule_engine(self):
        """规则引擎测试夹具"""
        return RuleEngine(rules_dir="tests/fixtures/rules")
    
    def test_keyword_condition_match(self):
        """测试关键词条件匹配"""
        condition = KeywordCondition({
            "type": "keyword",
            "field": "content",
            "value": ["你好", "hello"],
            "case_sensitive": False
        })
        
        message = {"content": "你好，世界"}
        assert condition.evaluate(message) is True
    
    def test_keyword_condition_no_match(self):
        """测试关键词条件不匹配"""
        condition = KeywordCondition({
            "type": "keyword",
            "field": "content",
            "value": ["你好"],
            "case_sensitive": True
        })
        
        message = {"content": "Hello"}  # 大小写不匹配
        assert condition.evaluate(message) is False
    
    @pytest.mark.asyncio
    async def test_process_message(self, rule_engine):
        """测试消息处理"""
        message = {
            "talker": "filehelper",
            "sender": "user123",
            "content": "帮助",
            "type": 1
        }
        
        result = await rule_engine.process(message)
        assert result["processed"] is True
        assert len(result["actions"]) > 0
```

### 集成测试示例

```python
# tests/integration/test_webhook.py
import pytest
from fastapi.testclient import TestClient
from src.wechat_butler.main import app

class TestWebhookIntegration:
    @pytest.fixture
    def client(self):
        """测试客户端夹具"""
        return TestClient(app)
    
    def test_webhook_signature_validation(self, client):
        """测试 Webhook 签名验证"""
        payload = {"event": "message.new", "data": {}}
        signature = calculate_signature(payload, "test-secret")
        
        response = client.post(
            "/webhook/message",
            json=payload,
            headers={"X-Signature": signature}
        )
        
        assert response.status_code == 200
    
    def test_webhook_invalid_signature(self, client):
        """测试无效签名"""
        payload = {"event": "message.new", "data": {}}
        
        response = client.post(
            "/webhook/message",
            json=payload,
            headers={"X-Signature": "invalid-signature"}
        )
        
        assert response.status_code == 401
```

### 测试配置

```python
# tests/conftest.py
import pytest
import asyncio
from typing import Generator
from src.wechat_butler.config import load_config

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """创建事件循环夹具"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def test_config():
    """测试配置夹具"""
    return load_config("tests/fixtures/config/test.yaml")

@pytest.fixture
async def rule_engine_with_rules(test_config):
    """带规则的规则引擎夹具"""
    from src.wechat_butler.rule_engine import RuleEngine
    engine = RuleEngine(test_config)
    await engine.load_rules()
    return engine
```

### 测试命令

```bash
# 运行所有测试
pytest

# 运行测试并显示详细输出
pytest -v

# 运行特定标记的测试
pytest -m "integration"

# 运行测试并生成覆盖率报告
pytest --cov=src.wechat_butler --cov-report=term-missing

# 运行测试并生成 HTML 覆盖率报告
pytest --cov=src.wechat_butler --cov-report=html

# 监视文件变化自动运行测试
ptw -- --tb=short
```

---

## 调试技巧

### 1. 日志调试

配置详细日志：
```yaml
# config.yaml
logging:
  level: "DEBUG"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "./logs/debug.log"
```

在代码中添加调试日志：
```python
import logging

logger = logging.getLogger(__name__)

def complex_function(data):
    logger.debug("开始处理数据", extra={"data_size": len(data)})
    
    # 处理步骤
    step1_result = step1(data)
    logger.debug("步骤1完成", extra={"result": step1_result})
    
    step2_result = step2(step1_result)
    logger.debug("步骤2完成",