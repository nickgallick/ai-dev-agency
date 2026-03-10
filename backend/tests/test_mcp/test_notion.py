"""Tests for Notion MCP Server."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.mcp.servers.notion import NotionMCPServer
from backend.mcp.manager import ServerStatus


class TestNotionMCPServer:
    """Tests for Notion MCP Server."""
    
    @pytest.fixture
    def server(self, mock_settings):
        """Create notion server."""
        return NotionMCPServer()
    
    @pytest.fixture
    def connected_server(self, server, mock_httpx_client):
        """Create connected notion server."""
        server._client = mock_httpx_client
        server._token = "test_token"
        server.status = ServerStatus.CONNECTED
        return server
    
    @pytest.mark.asyncio
    async def test_discover_tools(self, server):
        """Test discovering available tools."""
        tools = await server.discover_tools()
        
        assert "search" in tools
        assert "get_page" in tools
        assert "create_page" in tools
        assert "update_page" in tools
        assert "get_database" in tools
        assert "query_database" in tools
    
    @pytest.mark.asyncio
    async def test_search(self, connected_server, mock_httpx_client):
        """Test searching Notion workspace."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"id": "page-1", "object": "page"},
                {"id": "page-2", "object": "page"},
            ],
            "has_more": False,
        }
        mock_httpx_client.post = AsyncMock(return_value=mock_response)
        
        result = await connected_server.search(query="test")
        
        assert result["success"] is True
        assert len(result["data"]["results"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_page(self, connected_server, mock_httpx_client):
        """Test getting a page."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "page-123",
            "object": "page",
            "properties": {"title": {"title": [{"text": {"content": "Test Page"}}]}},
        }
        mock_httpx_client.get = AsyncMock(return_value=mock_response)
        
        result = await connected_server.get_page(page_id="page-123")
        
        assert result["success"] is True
        assert result["data"]["id"] == "page-123"
    
    @pytest.mark.asyncio
    async def test_create_page(self, connected_server, mock_httpx_client):
        """Test creating a page."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "new-page-123",
            "object": "page",
        }
        mock_httpx_client.post = AsyncMock(return_value=mock_response)
        
        result = await connected_server.create_page(
            parent_id="parent-123",
            parent_type="page_id",
            title="New Page"
        )
        
        assert result["success"] is True
        assert result["data"]["id"] == "new-page-123"
    
    @pytest.mark.asyncio
    async def test_update_page(self, connected_server, mock_httpx_client):
        """Test updating a page."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "page-123",
            "object": "page",
        }
        mock_httpx_client.patch = AsyncMock(return_value=mock_response)
        
        result = await connected_server.update_page(
            page_id="page-123",
            properties={"Status": {"select": {"name": "Done"}}}
        )
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_get_database(self, connected_server, mock_httpx_client):
        """Test getting a database."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "db-123",
            "object": "database",
            "title": [{"text": {"content": "Tasks"}}],
        }
        mock_httpx_client.get = AsyncMock(return_value=mock_response)
        
        result = await connected_server.get_database(database_id="db-123")
        
        assert result["success"] is True
        assert result["data"]["id"] == "db-123"
    
    @pytest.mark.asyncio
    async def test_query_database(self, connected_server, mock_httpx_client):
        """Test querying a database."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"id": "row-1", "object": "page"},
                {"id": "row-2", "object": "page"},
            ],
            "has_more": False,
        }
        mock_httpx_client.post = AsyncMock(return_value=mock_response)
        
        result = await connected_server.query_database(
            database_id="db-123",
            filter={"property": "Status", "select": {"equals": "Done"}}
        )
        
        assert result["success"] is True
        assert len(result["data"]["results"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_block_children(self, connected_server, mock_httpx_client):
        """Test getting block children."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"id": "block-1", "type": "paragraph"},
                {"id": "block-2", "type": "heading_1"},
            ],
            "has_more": False,
        }
        mock_httpx_client.get = AsyncMock(return_value=mock_response)
        
        result = await connected_server.get_block_children(block_id="page-123")
        
        assert result["success"] is True
        assert len(result["data"]["results"]) == 2
    
    @pytest.mark.asyncio
    async def test_append_block_children(self, connected_server, mock_httpx_client):
        """Test appending block children."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{"id": "new-block-1", "type": "paragraph"}],
        }
        mock_httpx_client.patch = AsyncMock(return_value=mock_response)
        
        children = [
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"text": {"content": "New paragraph"}}]
                }
            }
        ]
        
        result = await connected_server.append_block_children(
            block_id="page-123",
            children=children
        )
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_no_token(self, server):
        """Test operations without token configured."""
        server._client = MagicMock()
        server._token = None
        server.status = ServerStatus.DEGRADED
        
        result = await server.call_tool("search", {"query": "test"})
        
        assert result["success"] is False
        assert "not configured" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_call_tool(self, connected_server, mock_httpx_client):
        """Test calling tools via call_tool method."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "page-123"}
        mock_httpx_client.get = AsyncMock(return_value=mock_response)
        
        result = await connected_server.call_tool(
            "get_page",
            {"page_id": "page-123"}
        )
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_call_unknown_tool(self, connected_server):
        """Test calling unknown tool raises error."""
        with pytest.raises(ValueError, match="Unknown tool"):
            await connected_server.call_tool("unknown_tool", {})
