## 1. Docker Build Infrastructure

- [x] 1.1 Create `.dockerignore` to exclude `.git`, `__pycache__`, `.env`, `*.pyc`, `.venv`, `openspec`, `docs`, `.sisyphus` from build context
- [x] 1.2 Create `Dockerfile` with multi-stage build (builder + runtime) based on `python:3.11-slim`
- [x] 1.3 Add non-root `butler` user (UID 1000) and set file ownership in Dockerfile
- [x] 1.4 Add `HEALTHCHECK` directive probing `/health` endpoint in Dockerfile

## 2. Configuration Template & Entrypoint

- [x] 2.1 Create `config.yaml.template` with all fields using `${ENV_VAR}` syntax
- [x] 2.2 Create `entrypoint.sh` with config.yaml fallback logic and `exec butler --config /app/config.yaml`
- [x] 2.3 Add `ENV` defaults in Dockerfile for `SERVER_PORT`, `MCP_CHATSELL_API_URL`, `SERVER_LOG_LEVEL`, and other sensible defaults

## 3. Docker Compose

- [x] 3.1 Create `docker-compose.yml` with `butler-net` bridge network
- [x] 3.2 Define `wechat-butler` service with port exposure, env file, and volume mounts
- [x] 3.3 Define `chatshell` service on `butler-net` (no host port exposure)
- [x] 3.4 Add volume mount points for `config.yaml` and `prompts` directory
