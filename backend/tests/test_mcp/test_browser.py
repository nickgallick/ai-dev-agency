"""Tests for Browser MCP Server."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from backend.mcp.servers.browser import BrowserMCPServer
from backend.mcp.manager import ServerStatus


class TestBrowserMCPServer:
    """Tests for Browser MCP Server."""
    
    @pytest.fixture
    def server(self, mock_settings):
        """Create browser server."""
        return BrowserMCPServer()
    
    @pytest.fixture
    def connected_server(self, server, mock_httpx_client):
        """Create connected browser server."""
        server._client = mock_httpx_client
        server._server_url = "http://localhost:3000"
        server.status = ServerStatus.CONNECTED
        return server
    
    @pytest.mark.asyncio
    async def test_discover_tools(self, server):
        """Test discovering available tools."""
        tools = await server.discover_tools()
        
        assert "navigate" in tools
        assert "screenshot" in tools
        assert "get_content" in tools
        assert "click" in tools
        assert "type_text" in tools
        assert "get_links" in tools
        assert "extract_text" in tools
    
    @pytest.mark.asyncio
    async def test_navigate(self, connected_server, mock_httpx_client):
        """Test navigating to a URL."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_httpx_client.post = AsyncMock(return_value=mock_response)
        
        result = await connected_server.navigate(
            url="https://example.com"
        )
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_get_content(self, connected_server, mock_httpx_client):
        """Test getting page content."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": "<html><body>Hello</body></html>"
        }
        mock_httpx_client.post = AsyncMock(return_value=mock_response)
        
        result = await connected_server.get_content()
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_click(self, connected_server, mock_httpx_client):
        """Test clicking an element."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"clicked": True}
        mock_httpx_client.post = AsyncMock(return_value=mock_response)
        
        result = await connected_server.click(selector="button.submit")
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_type_text(self, connected_server, mock_httpx_client):
        """Test typing text into an input."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"typed": True}
        mock_httpx_client.post = AsyncMock(return_value=mock_response)
        
        result = await connected_server.type_text(
            selector="input#email",
            text="test@example.com"
        )
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_get_links(self, connected_server, mock_httpx_client):
        """Test extracting links from page."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"href": "https://example.com/page1", "text": "Page 1"},
            {"href": "https://example.com/page2", "text": "Page 2"},
        ]
        mock_httpx_client.post = AsyncMock(return_value=mock_response)
        
        result = await connected_server.get_links()
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_extract_text(self, connected_server, mock_httpx_client):
        """Test extracting text from element."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = "Hello World"
        mock_httpx_client.post = AsyncMock(return_value=mock_response)
        
        result = await connected_server.extract_text(selector="h1")
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_screenshot(self, connected_server, mock_httpx_client):
        """Test taking a screenshot."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"image": "base64data..."}
        mock_httpx_client.post = AsyncMock(return_value=mock_response)
        
        result = await connected_server.screenshot(full_page=True)
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_evaluate_script(self, connected_server, mock_httpx_client):
        """Test evaluating JavaScript."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = "result"
        mock_httpx_client.post = AsyncMock(return_value=mock_response)
        
        result = await connected_server.evaluate(
            script="document.title"
        )
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_connection_error(self, server, mock_httpx_client):
        """Test handling connection error."""
        mock_httpx_client.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await server.connect()
        
        assert result is False
        assert server.error_message is not None
    
    @pytest.mark.asyncio
    async def test_call_tool(self, connected_server, mock_httpx_client):
        """Test calling tools via call_tool method."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_httpx_client.post = AsyncMock(return_value=mock_response)
        
        result = await connected_server.call_tool(
            "navigate",
            {"url": "https://example.com"}
        )
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_call_unknown_tool(self, connected_server):
        """Test calling unknown tool raises error."""
        with pytest.raises(ValueError, match="Unknown tool"):
            await connected_server.call_tool("unknown_tool", {})
    
    @pytest.mark.asyncio
    async def test_call_tool_not_connected(self, server):
        """Test calling tool when not connected raises error."""
        with pytest.raises(RuntimeError, match="not connected"):
            await server.call_tool("navigate", {"url": "https://example.com"})
