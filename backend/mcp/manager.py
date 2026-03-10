"""MCP (Model Context Protocol) Manager.

Handles connection pooling, health checks, routing, and error handling
for all MCP servers.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Type
from enum import Enum

from mcp.config import MCP_SERVERS, get_enabled_servers
from config.settings import get_settings

logger = logging.getLogger(__name__)


class ServerStatus(Enum):
    """MCP Server connection status."""
    CONNECTED = "connected"
    DEGRADED = "degraded"
    DISCONNECTED = "disconnected"
    DISABLED = "disabled"


class MCPServerBase:
    """Base class for MCP server wrappers."""
    
    name: str = ""
    
    def __init__(self):
        self.status = ServerStatus.DISCONNECTED
        self.last_used: Optional[datetime] = None
        self.last_health_check: Optional[datetime] = None
        self.discovered_tools: List[str] = []
        self.error_message: Optional[str] = None
    
    async def connect(self) -> bool:
        """Initialize connection to the MCP server."""
        raise NotImplementedError
    
    async def disconnect(self) -> None:
        """Close connection to the MCP server."""
        raise NotImplementedError
    
    async def health_check(self) -> ServerStatus:
        """Check server health and update status."""
        raise NotImplementedError
    
    async def discover_tools(self) -> List[str]:
        """Discover available tools from the server."""
        raise NotImplementedError
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the MCP server."""
        raise NotImplementedError
    
    def _update_last_used(self) -> None:
        """Update the last used timestamp."""
        self.last_used = datetime.utcnow()


class MCPManager:
    """Central manager for all MCP server connections.
    
    Provides connection pooling, health monitoring, request routing,
    and graceful error handling for MCP servers.
    """
    
    _instance: Optional['MCPManager'] = None
    
    def __new__(cls) -> 'MCPManager':
        """Singleton pattern for MCP Manager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._servers: Dict[str, MCPServerBase] = {}
        self._health_check_interval = 60  # seconds
        self._health_check_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._initialized = True
        
        logger.info("MCP Manager initialized")
    
    async def initialize(self) -> None:
        """Initialize all enabled MCP servers."""
        from mcp.servers import (
            FilesystemMCPServer,
            GitHubMCPServer,
            PostgresMCPServer,
            BrowserMCPServer,
            SlackMCPServer,
            NotionMCPServer,
            MemoryMCPServer,
            FetchMCPServer,
        )
        
        server_classes: Dict[str, Type[MCPServerBase]] = {
            "filesystem": FilesystemMCPServer,
            "github": GitHubMCPServer,
            "postgres": PostgresMCPServer,
            "browser": BrowserMCPServer,
            "slack": SlackMCPServer,
            "notion": NotionMCPServer,
            "memory": MemoryMCPServer,
            "fetch": FetchMCPServer,
        }
        
        enabled_servers = get_enabled_servers()
        logger.info(f"Initializing {len(enabled_servers)} MCP servers")
        
        for server_name in enabled_servers:
            server_class = server_classes.get(server_name)
            if server_class:
                try:
                    server = server_class()
                    success = await server.connect()
                    if success:
                        server.status = ServerStatus.CONNECTED
                        server.discovered_tools = await server.discover_tools()
                        logger.info(f"MCP server '{server_name}' connected with {len(server.discovered_tools)} tools")
                    else:
                        server.status = ServerStatus.DISCONNECTED
                        logger.warning(f"MCP server '{server_name}' failed to connect")
                    self._servers[server_name] = server
                except Exception as e:
                    logger.error(f"Failed to initialize MCP server '{server_name}': {e}")
                    # Create a placeholder server with error status
                    server = server_class()
                    server.status = ServerStatus.DISCONNECTED
                    server.error_message = str(e)
                    self._servers[server_name] = server
        
        # Start background health checks
        self._health_check_task = asyncio.create_task(self._run_health_checks())
    
    async def shutdown(self) -> None:
        """Shutdown all MCP servers and cleanup."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        for server_name, server in self._servers.items():
            try:
                await server.disconnect()
                logger.info(f"MCP server '{server_name}' disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting MCP server '{server_name}': {e}")
        
        self._servers.clear()
        logger.info("MCP Manager shutdown complete")
    
    async def _run_health_checks(self) -> None:
        """Background task for periodic health checks."""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                await self.check_all_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
    
    async def check_all_health(self) -> Dict[str, ServerStatus]:
        """Check health of all servers."""
        results = {}
        for server_name, server in self._servers.items():
            try:
                status = await server.health_check()
                server.status = status
                server.last_health_check = datetime.utcnow()
                server.error_message = None
                results[server_name] = status
            except Exception as e:
                server.status = ServerStatus.DISCONNECTED
                server.error_message = str(e)
                results[server_name] = ServerStatus.DISCONNECTED
        return results
    
    def get_server(self, server_name: str) -> Optional[MCPServerBase]:
        """Get a specific MCP server instance."""
        return self._servers.get(server_name)
    
    def get_server_status(self, server_name: str) -> Optional[ServerStatus]:
        """Get the status of a specific server."""
        server = self._servers.get(server_name)
        return server.status if server else None
    
    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get status information for all servers."""
        statuses = {}
        for server_name, server in self._servers.items():
            config = MCP_SERVERS.get(server_name, {})
            statuses[server_name] = {
                "status": server.status.value,
                "last_used": server.last_used.isoformat() if server.last_used else None,
                "last_health_check": server.last_health_check.isoformat() if server.last_health_check else None,
                "discovered_tools": server.discovered_tools,
                "error_message": server.error_message,
                "enabled": config.get("enabled", False),
                "agent_wired": config.get("agent_wired", False),
                "used_by": config.get("used_by", []),
                "source": config.get("source", ""),
                "description": config.get("description", ""),
            }
        return statuses
    
    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
        fallback_server: Optional[str] = None
    ) -> Any:
        """Route a tool call to the appropriate MCP server.
        
        Args:
            server_name: Target MCP server name.
            tool_name: Name of the tool to call.
            arguments: Arguments to pass to the tool.
            fallback_server: Optional fallback server if primary fails.
            
        Returns:
            Tool execution result.
            
        Raises:
            ValueError: If server not found or tool not available.
            RuntimeError: If server is disconnected with no fallback.
        """
        async with self._lock:
            server = self._servers.get(server_name)
            
            if not server:
                raise ValueError(f"MCP server '{server_name}' not found")
            
            if server.status == ServerStatus.DISABLED:
                raise RuntimeError(f"MCP server '{server_name}' is disabled")
            
            if server.status == ServerStatus.DISCONNECTED:
                # Try to reconnect
                try:
                    success = await server.connect()
                    if success:
                        server.status = ServerStatus.CONNECTED
                    else:
                        if fallback_server:
                            return await self.call_tool(fallback_server, tool_name, arguments)
                        raise RuntimeError(f"MCP server '{server_name}' is disconnected")
                except Exception as e:
                    if fallback_server:
                        logger.warning(f"Primary server '{server_name}' failed, using fallback")
                        return await self.call_tool(fallback_server, tool_name, arguments)
                    raise
            
            try:
                result = await server.call_tool(tool_name, arguments)
                server._update_last_used()
                return result
            except Exception as e:
                logger.error(f"Tool call failed on '{server_name}': {e}")
                server.status = ServerStatus.DEGRADED
                server.error_message = str(e)
                
                if fallback_server:
                    logger.warning(f"Falling back to '{fallback_server}'")
                    return await self.call_tool(fallback_server, tool_name, arguments)
                raise
    
    async def enable_server(self, server_name: str) -> bool:
        """Enable a disabled server."""
        server = self._servers.get(server_name)
        if not server:
            return False
        
        if server.status == ServerStatus.DISABLED:
            try:
                success = await server.connect()
                if success:
                    server.status = ServerStatus.CONNECTED
                    server.discovered_tools = await server.discover_tools()
                    return True
            except Exception as e:
                server.error_message = str(e)
        return False
    
    async def disable_server(self, server_name: str) -> bool:
        """Disable a server."""
        server = self._servers.get(server_name)
        if not server:
            return False
        
        try:
            await server.disconnect()
            server.status = ServerStatus.DISABLED
            return True
        except Exception as e:
            logger.error(f"Error disabling server '{server_name}': {e}")
            return False
    
    async def test_connection(self, server_name: str) -> Dict[str, Any]:
        """Test connection to a specific server."""
        server = self._servers.get(server_name)
        if not server:
            return {"success": False, "error": "Server not found"}
        
        start_time = datetime.utcnow()
        try:
            status = await server.health_check()
            latency = (datetime.utcnow() - start_time).total_seconds() * 1000
            return {
                "success": status in [ServerStatus.CONNECTED, ServerStatus.DEGRADED],
                "status": status.value,
                "latency_ms": round(latency, 2),
                "tools": server.discovered_tools,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# Global manager instance
_manager: Optional[MCPManager] = None


async def get_mcp_manager() -> MCPManager:
    """Get or create the global MCP Manager instance."""
    global _manager
    if _manager is None:
        _manager = MCPManager()
        await _manager.initialize()
    return _manager
