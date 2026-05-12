# ---- Builder stage ----
FROM python:3.11-slim AS builder

WORKDIR /build

COPY pyproject.toml requirements.txt ./
COPY wechat_butler/ wechat_butler/

RUN pip install --no-cache-dir --prefix=/install .

# ---- Runtime stage ----
FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 butler && \
    useradd --uid 1000 --gid butler --shell /bin/bash --create-home butler

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY wechat_butler/ wechat_butler/
COPY pyproject.toml ./

# Copy config template and entrypoint
COPY config.yaml.template config.yaml.template
COPY entrypoint.sh entrypoint.sh
RUN chmod +x entrypoint.sh

COPY prompts/ ./prompts/

# Set ownership to butler user
RUN chown -R butler:butler /app

# Environment variable defaults
ENV SERVER_HOST=0.0.0.0 \
    SERVER_PORT=8837 \
    SERVER_LOG_LEVEL=info \
    LLM_PROVIDER=openai \
    LLM_BASE_URL=https://api.openai.com/v1 \
    LLM_DEFAULT_MODEL=gpt-4o \
    LLM_MAX_TOKENS=4096 \
    LLM_TEMPERATURE=0.7 \
    MCP_CHATSELL_API_URL=http://chatshell:5030/mcp \
    MCP_IDLE_TIMEOUT=300 \
    MCP_CONNECT_TIMEOUT=10 \
    PROMPTS_DIRECTORY=prompts

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${SERVER_PORT}/health || exit 1

USER butler

EXPOSE ${SERVER_PORT}

ENTRYPOINT ["./entrypoint.sh"]
