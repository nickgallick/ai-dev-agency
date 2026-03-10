"""Tests for Memory MCP Server."""

import json
import pytest
from unittest.mock import AsyncMock, patch

from mcp.servers.memory import MemoryMCPServer
from mcp.manager import ServerStatus


class TestMemoryMCPServer:
    """Tests for Memory MCP Server."""
    
    @pytest.fixture
    def server(self, mock_redis):
        """Create memory server with mocked Redis."""
        server = MemoryMCPServer()
        server._redis = mock_redis
        server.status = ServerStatus.CONNECTED
        return server
    
    @pytest.mark.asyncio
    async def test_connect(self, mock_redis, mock_settings):
        """Test connecting to memory server."""
        server = MemoryMCPServer()
        result = await server.connect()
        
        assert result is True
        assert server.status == ServerStatus.CONNECTED
    
    @pytest.mark.asyncio
    async def test_disconnect(self, server):
        """Test disconnecting from memory server."""
        await server.disconnect()
        
        assert server.status == ServerStatus.DISCONNECTED
        assert server._redis is None
    
    @pytest.mark.asyncio
    async def test_health_check(self, server, mock_redis):
        """Test health check."""
        status = await server.health_check()
        assert status == ServerStatus.CONNECTED
        mock_redis.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_discover_tools(self, server):
        """Test discovering available tools."""
        tools = await server.discover_tools()
        
        assert "store" in tools
        assert "retrieve" in tools
        assert "search" in tools
        assert "delete" in tools
        assert "store_agent_context" in tools
        assert "get_agent_context" in tools
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, server, mock_redis):
        """Test storing and retrieving a value."""
        # Setup mock to return stored data
        stored_data = {
            "value": "test_value",
            "metadata": {},
            "namespace": "default",
        }
        mock_redis.get.return_value = json.dumps(stored_data)
        
        # Store
        store_result = await server.store(
            key="test_key",
            value="test_value",
            namespace="default"
        )
        assert store_result["success"] is True
        
        # Retrieve
        retrieve_result = await server.retrieve(
            key="test_key",
            namespace="default"
        )
        assert retrieve_result["success"] is True
        assert retrieve_result["found"] is True
        assert retrieve_result["value"] == "test_value"
    
    @pytest.mark.asyncio
    async def test_retrieve_not_found(self, server, mock_redis):
        """Test retrieving non-existent key."""
        mock_redis.get.return_value = None
        
        result = await server.retrieve(
            key="nonexistent",
            namespace="default"
        )
        
        assert result["success"] is True
        assert result["found"] is False
        assert result["value"] is None
    
    @pytest.mark.asyncio
    async def test_store_with_ttl(self, server, mock_redis):
        """Test storing value with TTL."""
        result = await server.store(
            key="temp_key",
            value="temp_value",
            ttl_seconds=3600
        )
        
        assert result["success"] is True
        mock_redis.setex.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete(self, server, mock_redis):
        """Test deleting a key."""
        result = await server.delete(
            key="test_key",
            namespace="default"
        )
        
        assert result["success"] is True
        assert result["deleted"] is True
    
    @pytest.mark.asyncio
    async def test_list_keys(self, server, mock_redis):
        """Test listing keys in namespace."""
        mock_redis.smembers.return_value = {"key1", "key2", "key3"}
        
        result = await server.list_keys(namespace="default")
        
        assert result["success"] is True
        assert len(result["keys"]) == 3
    
    @pytest.mark.asyncio
    async def test_store_agent_context(self, server, mock_redis):
        """Test storing agent context."""
        result = await server.store_agent_context(
            agent_name="research",
            project_id="proj-123",
            context={"findings": ["competitor A", "competitor B"]}
        )
        
        assert result["success"] is True
        assert result["agent"] == "research"
        assert result["project_id"] == "proj-123"
    
    @pytest.mark.asyncio
    async def test_get_agent_context(self, server, mock_redis):
        """Test retrieving agent context."""
        stored_context = {
            "context": {"findings": ["competitor A"]},
            "agent": "research",
            "project_id": "proj-123",
            "updated_at": "2024-01-01T00:00:00",
        }
        mock_redis.get.return_value = json.dumps(stored_context)
        
        result = await server.get_agent_context(
            agent_name="research",
            project_id="proj-123"
        )
        
        assert result["success"] is True
        assert result["found"] is True
        assert "findings" in result["context"]
    
    @pytest.mark.asyncio
    async def test_get_agent_context_not_found(self, server, mock_redis):
        """Test retrieving non-existent agent context."""
        mock_redis.get.return_value = None
        
        result = await server.get_agent_context(
            agent_name="unknown",
            project_id="unknown"
        )
        
        assert result["success"] is True
        assert result["found"] is False
        assert result["context"] == {}
    
    @pytest.mark.asyncio
    async def test_call_tool(self, server, mock_redis):
        """Test calling tools via call_tool method."""
        stored_data = {"value": "test", "metadata": {}}
        mock_redis.get.return_value = json.dumps(stored_data)
        
        result = await server.call_tool(
            "retrieve",
            {"key": "test", "namespace": "default"}
        )
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_call_unknown_tool(self, server):
        """Test calling unknown tool raises error."""
        with pytest.raises(ValueError, match="Unknown tool"):
            await server.call_tool("unknown_tool", {})
