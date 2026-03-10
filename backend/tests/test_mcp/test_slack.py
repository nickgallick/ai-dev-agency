"""Tests for Slack MCP Server."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.mcp.servers.slack import SlackMCPServer
from backend.mcp.manager import ServerStatus


class TestSlackMCPServer:
    """Tests for Slack MCP Server."""
    
    @pytest.fixture
    def server(self, mock_settings):
        """Create slack server."""
        return SlackMCPServer()
    
    @pytest.fixture
    def connected_server(self, server, mock_httpx_client):
        """Create connected slack server."""
        server._client = mock_httpx_client
        server._webhook_url = "https://hooks.slack.com/services/xxx"
        server.status = ServerStatus.CONNECTED
        return server
    
    @pytest.mark.asyncio
    async def test_discover_tools(self, server):
        """Test discovering available tools."""
        tools = await server.discover_tools()
        
        assert "send_message" in tools
        assert "send_blocks" in tools
        assert "send_notification" in tools
    
    @pytest.mark.asyncio
    async def test_send_message(self, connected_server, mock_httpx_client):
        """Test sending a simple message."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_httpx_client.post = AsyncMock(return_value=mock_response)
        
        result = await connected_server.send_message(
            text="Hello from test!"
        )
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_send_message_with_options(self, connected_server, mock_httpx_client):
        """Test sending message with channel and username."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_httpx_client.post = AsyncMock(return_value=mock_response)
        
        result = await connected_server.send_message(
            text="Test message",
            channel="#general",
            username="TestBot",
            icon_emoji=":robot_face:"
        )
        
        assert result["success"] is True
        
        # Verify payload
        call_args = mock_httpx_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["text"] == "Test message"
        assert payload["channel"] == "#general"
    
    @pytest.mark.asyncio
    async def test_send_blocks(self, connected_server, mock_httpx_client):
        """Test sending Block Kit blocks."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_httpx_client.post = AsyncMock(return_value=mock_response)
        
        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "Hello *World*"}
            }
        ]
        
        result = await connected_server.send_blocks(
            blocks=blocks,
            text="Fallback text"
        )
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_send_notification(self, connected_server, mock_httpx_client):
        """Test sending a formatted notification."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_httpx_client.post = AsyncMock(return_value=mock_response)
        
        result = await connected_server.send_notification(
            title="Deployment Complete",
            message="Successfully deployed to production",
            status="success",
            fields={"Version": "1.0.0", "Environment": "prod"}
        )
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_send_message_no_webhook(self, server):
        """Test sending message without webhook configured."""
        server._client = MagicMock()
        server._webhook_url = None
        
        result = await server.send_message(text="Test")
        
        assert result["success"] is False
        assert "not configured" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_send_message_error(self, connected_server, mock_httpx_client):
        """Test handling send error."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "invalid_payload"
        mock_httpx_client.post = AsyncMock(return_value=mock_response)
        
        result = await connected_server.send_message(text="Test")
        
        assert result["success"] is False
    
    @pytest.mark.asyncio
    async def test_health_check_with_valid_url(self, connected_server):
        """Test health check with valid webhook URL."""
        status = await connected_server.health_check()
        assert status == ServerStatus.CONNECTED
    
    @pytest.mark.asyncio
    async def test_health_check_no_url(self, server):
        """Test health check without webhook URL."""
        server._webhook_url = None
        status = await server.health_check()
        assert status == ServerStatus.DEGRADED
    
    @pytest.mark.asyncio
    async def test_call_tool(self, connected_server, mock_httpx_client):
        """Test calling tools via call_tool method."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_httpx_client.post = AsyncMock(return_value=mock_response)
        
        result = await connected_server.call_tool(
            "send_message",
            {"text": "Test via call_tool"}
        )
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_call_unknown_tool(self, connected_server):
        """Test calling unknown tool raises error."""
        with pytest.raises(ValueError, match="Unknown tool"):
            await connected_server.call_tool("unknown_tool", {})
