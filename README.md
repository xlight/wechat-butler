# WeChat Butler v0.1.0

AI Service Layer for the WeChat ecosystem. Connects to chatshell-api via MCP for data queries, provides LLM-powered AI chat with tool_call loop, and streams results to chatlog-session via SSE.

## Quick Start

```bash
# Create conda environment
conda env create -f environment.yml

# Activate
conda activate wechat-butler

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run
python -m wechat_butler
```

## Configuration

See `config.yaml` for all options. API keys are set via environment variables in `.env`.

## API

- `POST /api/v1/ai/chat` - AI chat (SSE streaming)
- `GET /api/v1/ai/models` - List models
- `GET /api/v1/ai/status` - Service status
- `GET /api/v1/ai/config` - Get config (masked keys)
- `POST /api/v1/ai/config` - Update config
- `CRUD /api/v1/ai/prompts` - Prompt management
- `GET /health` - Health check (no auth)

All endpoints except `/health` require `X-Butler-API-Key` header.
