## Context

WeChat Butler 是一个基于 FastAPI + Uvicorn 的 AI 服务层，当前仅支持本地 Python 环境运行。配置通过 `config.yaml` 加载，已内置 `${ENV_VAR}` 环境变量插值机制（`ConfigManager._interpolate_env`）。项目无任何容器化支持。

关键约束：
- Python >= 3.11，依赖 fastapi/uvicorn/litellm/mcp/pyyaml/pydantic/sse-starlette
- 入口点：`butler` CLI（`pyproject.toml` 中定义的 `wechat_butler.main:main`）
- MCP 客户端通过 streamable HTTP 连接外部 ChatShell 服务
- `config.yaml` 在 `.gitignore` 中（含敏感信息），需模板化处理
- `prompts/*.yaml` 也在 `.gitignore` 中，需支持 volume 挂载

## Goals / Non-Goals

**Goals:**
- 生成最小化生产 Docker 镜像（多阶段构建）
- 所有 config.yaml 字段均可通过环境变量覆盖
- 支持 volume mount 覆盖 config.yaml 和 prompts 目录
- docker-compose 编排 butler + chatshell 网络
- 非 root 用户运行，内置健康检查
- 完全向后兼容，不修改现有源码

**Non-Goals:**
- 不修改 `config.py` 或其他 Python 源码
- 不实现 Kubernetes 部署配置
- 不实现 CI/CD pipeline 集成
- 不实现多架构构建（arm64/amd64）

## Decisions

### D1: 基础镜像选择 — python:3.11-slim

**选择**: `python:3.11-slim`  
**替代方案**:
- `python:3.11-alpine`: 更小（~50MB vs ~150MB），但 musl libc 与 litellm/mcp 的 C 扩展可能有兼容问题
- `python:3.11`: 完整版（~1GB），体积过大

**理由**: slim 基于 Debian + glibc，兼容性最好，体积适中。litellm 依赖的 numpy 等库在 musl 下可能需要从源码编译。

### D2: 环境变量覆盖策略 — 复用 Python `${VAR}` 插值

**选择**: config.yaml.template 中所有字段使用 `${ENV_VAR}` 语法，由 Python 的 `ConfigManager._interpolate_env()` 解析，entrypoint.sh 不做环境变量替换  
**替代方案**:
- entrypoint.sh 中用 `envsubst` 预替换：与 Python `${VAR}` 语法冲突，需双重转义
- entrypoint.sh 中用 `yq` 逐字段替换：需额外安装 yq，逻辑复杂

**理由**: 项目已有成熟的 `${VAR}` 插值机制，完全复用最简洁。entrypoint 只负责"如果用户没挂载 config.yaml，就从模板复制"。

### D3: Entrypoint 职责 — 最小化

**选择**: entrypoint.sh 仅做两件事：
1. 检测 `/app/config.yaml` 是否存在（volume mount），不存在则从模板复制
2. `exec butler --config /app/config.yaml`

**理由**: 保持 entrypoint 极简，所有配置逻辑由 Python 层处理。避免 shell 脚本中的复杂替换逻辑。

### D4: 多阶段构建 — builder + runtime

**选择**: 两阶段构建
- Stage 1 (builder): 安装构建依赖，`pip install` 项目
- Stage 2 (runtime): 仅复制安装好的 site-packages + 源码

**理由**: 避免构建工具（setuptools、wheel 等）留在生产镜像中，减小攻击面和体积。

### D5: docker-compose 网络配置

**选择**: 自定义 bridge 网络 `butler-net`，butler 和 chatshell 在同一网络中。MCP 默认地址改为 `http://chatshell:5030/mcp`（Docker 网络内 DNS 解析）。  
**替代方案**:
- host 网络模式：失去网络隔离，不推荐
- 外部 MCP 地址：通过环境变量覆盖即可

**理由**: bridge 网络提供隔离 + DNS 解析，是 Docker Compose 的标准模式。

### D6: 非 root 用户

**选择**: 创建 `butler` 用户 (UID 1000)，所有文件属主设为该用户，容器以 `USER butler` 运行。  
**理由**: 安全最佳实践，避免容器内进程拥有 root 权限。

## Risks / Trade-offs

- **[musl 兼容性]** → 已通过选择 slim 而非 alpine 规避
- **[config.yaml 模板与用户挂载冲突]** → entrypoint 检测逻辑：挂载优先，模板仅作 fallback
- **[MCP 服务不可用]** → 已有 graceful degradation（server.py 中 MCP 连接失败时降级为 no-tool-mode）
- **[环境变量未设置时 `${VAR}` 原样保留]** → 这是 Python `_interpolate_env` 的现有行为，未设置的变量保留为 `${VAR_NAME}` 字符串，可能导致配置错误 → 在 entrypoint.sh 中对关键变量（API Key）做检查并 warn
- **[镜像体积]** → slim + 多阶段构建预计 ~200-250MB，可接受
