import asyncio
import logging
import time
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import Tool

logger = logging.getLogger(__name__)


class MCPDisconnectedError(Exception):
    pass


class MCPClient:
    def __init__(self, url: str, idle_timeout: int = 300, connect_timeout: int = 10):
        self._url = url
        self._idle_timeout = idle_timeout
        self._connect_timeout = connect_timeout

        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._tools: list[Tool] = []
        self._last_used: float = 0
        self._connected: bool = False
        self._watcher_task: asyncio.Task | None = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def tools(self) -> list[Tool]:
        return self._tools

    @property
    def tool_names(self) -> list[str]:
        return [t.name for t in self._tools]

    async def connect(self) -> None:
        try:
            self._stack = AsyncExitStack()
            transport = await asyncio.wait_for(
                self._stack.enter_async_context(streamablehttp_client(self._url)),
                timeout=self._connect_timeout,
            )
            read_stream, write_stream, _ = transport
            self._session = await self._stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await self._session.initialize()

            result = await self._session.list_tools()
            self._tools = result.tools
            self._connected = True
            self._last_used = time.monotonic()

            if self._idle_timeout > 0:
                self._watcher_task = asyncio.create_task(self._idle_watcher())

            logger.info(f"MCP connected to {self._url} ({len(self._tools)} tools discovered)")

        except Exception as e:
            await self._cleanup()
            logger.warning(f"MCP connection failed: {e}")

    async def disconnect(self) -> None:
        if self._connected:
            logger.info("MCP disconnecting")
        await self._cleanup()

    async def call_tool(self, name: str, arguments: dict) -> str:
        if not self._connected:
            await self.connect()
            if not self._connected:
                raise MCPDisconnectedError("MCP server unavailable")

        self._last_used = time.monotonic()
        result = await self._session.call_tool(name, arguments)

        if result.content:
            texts = [c.text for c in result.content if hasattr(c, "text")]
            return "\n".join(texts)
        return ""

    async def _idle_watcher(self) -> None:
        try:
            while self._connected:
                await asyncio.sleep(30)
                if self._connected and time.monotonic() - self._last_used > self._idle_timeout:
                    logger.info("MCP idle timeout, disconnecting")
                    await self.disconnect()
                    break
        except asyncio.CancelledError:
            pass

    async def _cleanup(self) -> None:
        if self._watcher_task:
            self._watcher_task.cancel()
            try:
                await self._watcher_task
            except asyncio.CancelledError:
                pass
            self._watcher_task = None
        if self._stack:
            try:
                await self._stack.aclose()
            except Exception:
                pass
            self._stack = None
        self._session = None
        self._tools = []
        self._connected = False
