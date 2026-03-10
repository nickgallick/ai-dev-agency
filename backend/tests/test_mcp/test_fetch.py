"""Tests for Fetch MCP Server."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from backend.mcp.servers.fetch import FetchMCPServer
from backend.mcp.manager import ServerStatus


class TestFetchMCPServer:
    """Tests for Fetch MCP Server."""
    
    @pytest.fixture
    def server(self):
        """Create fetch server."""
        return FetchMCPServer()
    
    @pytest.mark.asyncio
    async def test_connect(self, server):
        """Test connecting to fetch server."""
        result = await server.connect()
        assert result is True
        assert server.status == ServerStatus.CONNECTED
        assert server._client is not None
        await server.disconnect()
    
    @pytest.mark.asyncio
    async def test_disconnect(self, server):
        """Test disconnecting from fetch server."""
        await server.connect()
        await server.disconnect()
        assert server.status == ServerStatus.DISCONNECTED
        assert server._client is None
    
    @pytest.mark.asyncio
    async def test_discover_tools(self, server):
        """Test discovering available tools."""
        tools = await server.discover_tools()
        assert "get" in tools
        assert "post" in tools
        assert "fetch_json" in tools
        assert "fetch_text" in tools
        assert "download_file" in tools
    
    @pytest.mark.asyncio
    async def test_get_request(self, server, mock_httpx_client):
        """Test making GET request."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"key": "value"}
        mock_response.text = '{"key": "value"}'
        mock_response.url = "https://api.example.com/test"
        
        mock_httpx_client.request = AsyncMock(return_value=mock_response)
        
        server._client = mock_httpx_client
        server.status = ServerStatus.CONNECTED
        
        result = await server.get(url="https://api.example.com/test")
        
        assert result["success"] is True
        assert result["status_code"] == 200
    
    @pytest.mark.asyncio
    async def test_post_request(self, server, mock_httpx_client):
        """Test making POST request."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"id": 1}
        mock_response.text = '{"id": 1}'
        mock_response.url = "https://api.example.com/create"
        
        mock_httpx_client.request = AsyncMock(return_value=mock_response)
        
        server._client = mock_httpx_client
        server.status = ServerStatus.CONNECTED
        
        result = await server.post(
            url="https://api.example.com/create",
            json_data={"name": "test"}
        )
        
        assert result["success"] is True
        assert result["status_code"] == 201
    
    @pytest.mark.asyncio
    async def test_fetch_json(self, server, mock_httpx_client):
        """Test fetching JSON data."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"data": [1, 2, 3]}
        mock_response.text = '{"data": [1, 2, 3]}'
        mock_response.url = "https://api.example.com/data"
        
        mock_httpx_client.request = AsyncMock(return_value=mock_response)
        
        server._client = mock_httpx_client
        server.status = ServerStatus.CONNECTED
        
        result = await server.fetch_json(url="https://api.example.com/data")
        
        assert result["success"] is True
        assert result["data"] == {"data": [1, 2, 3]}
    
    @pytest.mark.asyncio
    async def test_fetch_text(self, server, mock_httpx_client):
        """Test fetching text content."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.json.side_effect = Exception("Not JSON")
        mock_response.text = "Hello, World!"
        mock_response.url = "https://example.com/text"
        
        mock_httpx_client.request = AsyncMock(return_value=mock_response)
        
        server._client = mock_httpx_client
        server.status = ServerStatus.CONNECTED
        
        result = await server.fetch_text(url="https://example.com/text")
        
        assert result["success"] is True
        assert result["text"] == "Hello, World!"
    
    @pytest.mark.asyncio
    async def test_head_request(self, server, mock_httpx_client):
        """Test making HEAD request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            "content-length": "12345",
            "content-type": "text/html"
        }
        
        mock_httpx_client.head = AsyncMock(return_value=mock_response)
        
        server._client = mock_httpx_client
        server.status = ServerStatus.CONNECTED
        
        result = await server.head(url="https://example.com")
        
        assert result["success"] is True
        assert result["status_code"] == 200
        assert "content-length" in result["headers"]
    
    @pytest.mark.asyncio
    async def test_request_timeout(self, server, mock_httpx_client):
        """Test handling request timeout."""
        mock_httpx_client.request = AsyncMock(
            side_effect=httpx.TimeoutException("Timeout")
        )
        
        server._client = mock_httpx_client
        server.status = ServerStatus.CONNECTED
        
        result = await server.get(url="https://slow.example.com")
        
        assert result["success"] is False
        assert "timeout" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_call_tool(self, server, mock_httpx_client):
        """Test calling tools via call_tool method."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = {}
        mock_response.text = "{}"
        mock_response.url = "https://example.com"
        
        mock_httpx_client.request = AsyncMock(return_value=mock_response)
        
        server._client = mock_httpx_client
        server.status = ServerStatus.CONNECTED
        
        result = await server.call_tool("get", {"url": "https://example.com"})
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_call_unknown_tool(self, server):
        """Test calling unknown tool raises error."""
        await server.connect()
        
        with pytest.raises(ValueError, match="Unknown tool"):
            await server.call_tool("unknown_tool", {})
        
        await server.disconnect()
