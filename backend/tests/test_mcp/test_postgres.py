"""Tests for PostgreSQL MCP Server."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.mcp.servers.postgres_mcp import PostgresMCPServer
from backend.mcp.manager import ServerStatus


class TestPostgresMCPServer:
    """Tests for PostgreSQL MCP Server."""
    
    @pytest.fixture
    def server(self, mock_settings):
        """Create postgres server."""
        return PostgresMCPServer()
    
    @pytest.fixture
    def connected_server(self, server, mock_asyncpg_pool):
        """Create connected postgres server."""
        pool, conn = mock_asyncpg_pool
        server._pool = pool
        server.status = ServerStatus.CONNECTED
        return server, conn
    
    @pytest.mark.asyncio
    async def test_discover_tools(self, server):
        """Test discovering available tools."""
        tools = await server.discover_tools()
        
        assert "query" in tools
        assert "list_tables" in tools
        assert "describe_table" in tools
        assert "get_table_schema" in tools
    
    @pytest.mark.asyncio
    async def test_read_only_enforcement_select(self, connected_server):
        """Test that SELECT queries are allowed."""
        server, conn = connected_server
        conn.fetch.return_value = [{"id": 1, "name": "test"}]
        
        result = await server.query(sql="SELECT * FROM users")
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_read_only_enforcement_insert(self, connected_server):
        """Test that INSERT queries are rejected."""
        server, conn = connected_server
        
        result = await server.query(sql="INSERT INTO users VALUES (1, 'test')")
        
        assert result["success"] is False
        assert "read-only" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_read_only_enforcement_update(self, connected_server):
        """Test that UPDATE queries are rejected."""
        server, conn = connected_server
        
        result = await server.query(sql="UPDATE users SET name = 'new'")
        
        assert result["success"] is False
        assert "read-only" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_read_only_enforcement_delete(self, connected_server):
        """Test that DELETE queries are rejected."""
        server, conn = connected_server
        
        result = await server.query(sql="DELETE FROM users")
        
        assert result["success"] is False
        assert "read-only" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_read_only_enforcement_drop(self, connected_server):
        """Test that DROP queries are rejected."""
        server, conn = connected_server
        
        result = await server.query(sql="DROP TABLE users")
        
        assert result["success"] is False
        assert "read-only" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_query_with_limit(self, connected_server):
        """Test that LIMIT is added to queries."""
        server, conn = connected_server
        conn.fetch.return_value = []
        
        await server.query(sql="SELECT * FROM users")
        
        # Check that LIMIT was added
        call_args = conn.fetch.call_args
        sql = call_args[0][0]
        assert "LIMIT" in sql.upper()
    
    @pytest.mark.asyncio
    async def test_list_tables(self, connected_server):
        """Test listing tables."""
        server, conn = connected_server
        conn.fetch.return_value = [
            {"table_name": "users", "table_type": "BASE TABLE"},
            {"table_name": "projects", "table_type": "BASE TABLE"},
        ]
        
        result = await server.list_tables(schema="public")
        
        assert result["success"] is True
        assert len(result["tables"]) == 2
    
    @pytest.mark.asyncio
    async def test_describe_table(self, connected_server):
        """Test describing a table."""
        server, conn = connected_server
        conn.fetch.return_value = [
            {
                "column_name": "id",
                "data_type": "integer",
                "is_nullable": "NO",
                "column_default": None,
                "character_maximum_length": None,
            },
            {
                "column_name": "name",
                "data_type": "varchar",
                "is_nullable": "YES",
                "column_default": None,
                "character_maximum_length": 255,
            },
        ]
        
        result = await server.describe_table(
            table_name="users",
            schema="public"
        )
        
        assert result["success"] is True
        assert result["table"] == "users"
        assert len(result["columns"]) == 2
    
    @pytest.mark.asyncio
    async def test_health_check(self, connected_server):
        """Test health check."""
        server, conn = connected_server
        
        status = await server.health_check()
        
        assert status == ServerStatus.CONNECTED
    
    @pytest.mark.asyncio
    async def test_call_tool(self, connected_server):
        """Test calling tools via call_tool method."""
        server, conn = connected_server
        conn.fetch.return_value = []
        
        result = await server.call_tool(
            "query",
            {"sql": "SELECT 1"}
        )
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_call_unknown_tool(self, connected_server):
        """Test calling unknown tool raises error."""
        server, conn = connected_server
        
        with pytest.raises(ValueError, match="Unknown tool"):
            await server.call_tool("unknown_tool", {})
    
    @pytest.mark.asyncio
    async def test_call_tool_not_connected(self, server):
        """Test calling tool when not connected raises error."""
        with pytest.raises(RuntimeError, match="not connected"):
            await server.call_tool("query", {"sql": "SELECT 1"})
