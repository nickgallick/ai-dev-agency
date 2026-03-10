"""Tests for MCP Manager."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from backend.mcp.manager import (
    MCPManager,
    MCPServerBase,
    ServerStatus,
    get_mcp_manager,
)


class TestMCPManager:
    """Tests for MCP Manager functionality."""
    
    @pytest.fixture
    def manager(self):
        """Create fresh MCP Manager instance."""
        # Reset singleton
        MCPManager._instance = None
        return MCPManager()
    
    def test_singleton_pattern(self, manager):
        """Test that MCPManager follows singleton pattern."""
        manager2 = MCPManager()
        assert manager is manager2
    
    def test_initial_state(self, manager):
        """Test initial manager state."""
        assert manager._servers == {}
        assert manager._health_check_interval == 60
        assert manager._initialized is True
    
    @pytest.mark.asyncio
    async def test_get_server_not_found(self, manager):
        """Test getting non-existent server."""
        server = manager.get_server("nonexistent")
        assert server is None
    
    @pytest.mark.asyncio
    async def test_get_server_status_not_found(self, manager):
        """Test getting status of non-existent server."""
        status = manager.get_server_status("nonexistent")
        assert status is None
    
    @pytest.mark.asyncio
    async def test_get_all_statuses_empty(self, manager):
        """Test getting all statuses when no servers."""
        statuses = manager.get_all_statuses()
        assert statuses == {}
    
    @pytest.mark.asyncio
    async def test_call_tool_server_not_found(self, manager):
        """Test calling tool on non-existent server."""
        with pytest.raises(ValueError, match="not found"):
            await manager.call_tool("nonexistent", "test_tool", {})


class TestMCPServerBase:
    """Tests for MCPServerBase."""
    
    def test_initial_state(self):
        """Test initial server state."""
        server = MCPServerBase()
        assert server.status == ServerStatus.DISCONNECTED
        assert server.last_used is None
        assert server.last_health_check is None
        assert server.discovered_tools == []
        assert server.error_message is None
    
    def test_update_last_used(self):
        """Test updating last used timestamp."""
        server = MCPServerBase()
        assert server.last_used is None
        server._update_last_used()
        assert server.last_used is not None
        assert isinstance(server.last_used, datetime)
    
    @pytest.mark.asyncio
    async def test_abstract_methods(self):
        """Test that abstract methods raise NotImplementedError."""
        server = MCPServerBase()
        
        with pytest.raises(NotImplementedError):
            await server.connect()
        
        with pytest.raises(NotImplementedError):
            await server.disconnect()
        
        with pytest.raises(NotImplementedError):
            await server.health_check()
        
        with pytest.raises(NotImplementedError):
            await server.discover_tools()
        
        with pytest.raises(NotImplementedError):
            await server.call_tool("test", {})


class TestServerStatus:
    """Tests for ServerStatus enum."""
    
    def test_status_values(self):
        """Test status enum values."""
        assert ServerStatus.CONNECTED.value == "connected"
        assert ServerStatus.DEGRADED.value == "degraded"
        assert ServerStatus.DISCONNECTED.value == "disconnected"
        assert ServerStatus.DISABLED.value == "disabled"
