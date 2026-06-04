import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from wechat_butler import __version__
from wechat_butler.ai.chat import OpenAIChatService
from wechat_butler.api.ai_routes import router as ai_router
from wechat_butler.api.middleware import APIKeyMiddleware
from wechat_butler.api.openai_routes import router as openai_router
from wechat_butler.api.rate_limiter import RateLimiter
from wechat_butler.config import ConfigManager
from wechat_butler.llm.router import LLMRouter
from wechat_butler.mcp_client.client import MCPClient

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config: ConfigManager = app.state.config
    mcp: MCPClient = app.state.mcp_client

    logger.info(f"WeChat Butler v{__version__} starting...")
    logger.info(f"Config loaded from {config._path}")

    await mcp.connect()
    if mcp.is_connected:
        logger.info(f"MCP connected ({len(mcp.tools)} tools)")
    else:
        logger.warning("MCP connection failed, AI Chat will run in no-tool mode")

    yield

    logger.info("Shutting down...")
    await mcp.disconnect()
    logger.info("MCP client disconnected")


def create_app(config: ConfigManager) -> FastAPI:
    app = FastAPI(title="WeChat Butler", version=__version__, lifespan=lifespan)

    mcp_client = MCPClient(
        url=config.config.mcp.chatshell_api_url,
        idle_timeout=config.config.mcp.idle_timeout,
        connect_timeout=config.config.mcp.connect_timeout,
    )
    llm_router = LLMRouter(config.config.llm)
    chat_service = OpenAIChatService(
        llm_config=config.config.llm,
        router=llm_router,
        mcp=mcp_client,
        safety=config.config.safety,
        agent_modes=config.config.agent_modes,
    )
    rate_limiter = RateLimiter(config.config.rate_limiting)

    app.state.config = config
    app.state.mcp_client = mcp_client
    app.state.llm_router = llm_router
    app.state.chat_service = chat_service
    app.state.rate_limiter = rate_limiter

    app.include_router(openai_router)
    app.include_router(ai_router)

    app.add_middleware(APIKeyMiddleware, expected_key=config.config.auth.api_key)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "healthy", "version": __version__}

    return app
