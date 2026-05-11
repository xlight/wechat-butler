## Why

项目目前没有任何容器化支持，无法方便地部署和运行。需要 Dockerfile 和 docker-compose 配置，使 WeChat Butler 可以一键容器化部署，同时通过环境变量全面覆盖所有配置项，避免硬编码敏感信息。

## What Changes

- 新增多阶段构建 Dockerfile（builder + runtime），基于 python:3.11-slim
- 新增 entrypoint.sh 脚本，支持 config.yaml 模板生成与 volume mount 覆盖
- 新增 config.yaml.template，所有字段均支持 `${ENV_VAR}` 环境变量插值
- 新增 docker-compose.yml，编排 wechat-butler 与 chatshell MCP 服务的网络
- 所有 config.yaml 中的配置项均可通过环境变量覆盖（server、llm、mcp、auth、prompts）
- prompts 目录支持 volume 挂载
- 容器以非 root 用户运行，内置健康检查

## Capabilities

### New Capabilities
- `docker-build`: 多阶段 Dockerfile 构建，生成最小化生产镜像
- `docker-config`: 环境变量全面覆盖配置，config.yaml 模板 + entrypoint 脚本
- `docker-compose`: docker-compose 编排，网络配置，volume 挂载

### Modified Capabilities

## Impact

- 新增文件：Dockerfile、entrypoint.sh、config.yaml.template、docker-compose.yml、.dockerignore
- 不修改现有源码，完全向后兼容
- 部署方式从"本地 Python 环境"扩展为"容器化部署"
- MCP 服务地址默认从 `127.0.0.1:5030` 变为 `chatshell:5030`（Docker 网络内）
