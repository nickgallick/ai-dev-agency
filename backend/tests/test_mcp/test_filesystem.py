"""Tests for Filesystem MCP Server."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

from mcp.servers.filesystem import FilesystemMCPServer
from mcp.manager import ServerStatus


class TestFilesystemMCPServer:
    """Tests for Filesystem MCP Server."""
    
    @pytest.fixture
    def server(self, temp_project_dir):
        """Create filesystem server with temp directory."""
        with patch("backend.mcp.servers.filesystem.MCP_SERVERS", {
            "filesystem": {
                "config": {"allowed_paths": [temp_project_dir]}
            }
        }):
            server = FilesystemMCPServer()
            server.allowed_paths = [temp_project_dir]
            return server
    
    @pytest.mark.asyncio
    async def test_connect(self, server):
        """Test connecting to filesystem server."""
        result = await server.connect()
        assert result is True
        assert server.status == ServerStatus.CONNECTED
    
    @pytest.mark.asyncio
    async def test_disconnect(self, server):
        """Test disconnecting from filesystem server."""
        await server.connect()
        await server.disconnect()
        assert server.status == ServerStatus.DISCONNECTED
    
    @pytest.mark.asyncio
    async def test_health_check(self, server):
        """Test health check."""
        await server.connect()
        status = await server.health_check()
        assert status == ServerStatus.CONNECTED
    
    @pytest.mark.asyncio
    async def test_discover_tools(self, server):
        """Test discovering available tools."""
        tools = await server.discover_tools()
        assert "read_file" in tools
        assert "write_file" in tools
        assert "list_directory" in tools
    
    @pytest.mark.asyncio
    async def test_write_and_read_file(self, server, temp_project_dir):
        """Test writing and reading a file."""
        await server.connect()
        
        test_path = os.path.join(temp_project_dir, "test.txt")
        content = "Hello, World!"
        
        # Write file
        write_result = await server.write_file(path=test_path, content=content)
        assert write_result["success"] is True
        
        # Read file
        read_result = await server.read_file(path=test_path)
        assert read_result["success"] is True
        assert read_result["content"] == content
    
    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, server, temp_project_dir):
        """Test reading non-existent file."""
        await server.connect()
        
        result = await server.read_file(
            path=os.path.join(temp_project_dir, "nonexistent.txt")
        )
        assert result["success"] is False
        assert "not found" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_list_directory(self, server, temp_project_dir):
        """Test listing directory contents."""
        await server.connect()
        
        # Create some files
        for name in ["file1.txt", "file2.txt"]:
            path = os.path.join(temp_project_dir, name)
            await server.write_file(path=path, content="test")
        
        # List directory
        result = await server.list_directory(path=temp_project_dir)
        assert result["success"] is True
        assert len(result["entries"]) >= 2
    
    @pytest.mark.asyncio
    async def test_create_directory(self, server, temp_project_dir):
        """Test creating a directory."""
        await server.connect()
        
        new_dir = os.path.join(temp_project_dir, "subdir")
        result = await server.create_directory(path=new_dir)
        assert result["success"] is True
        assert Path(new_dir).is_dir()
    
    @pytest.mark.asyncio
    async def test_delete_file(self, server, temp_project_dir):
        """Test deleting a file."""
        await server.connect()
        
        test_path = os.path.join(temp_project_dir, "to_delete.txt")
        await server.write_file(path=test_path, content="delete me")
        
        result = await server.delete_file(path=test_path)
        assert result["success"] is True
        assert not Path(test_path).exists()
    
    @pytest.mark.asyncio
    async def test_file_exists(self, server, temp_project_dir):
        """Test checking file existence."""
        await server.connect()
        
        test_path = os.path.join(temp_project_dir, "exists.txt")
        
        # File doesn't exist
        result = await server.file_exists(path=test_path)
        assert result["exists"] is False
        
        # Create file
        await server.write_file(path=test_path, content="test")
        
        # File exists
        result = await server.file_exists(path=test_path)
        assert result["exists"] is True
    
    @pytest.mark.asyncio
    async def test_path_validation(self, server):
        """Test path validation restricts to allowed paths."""
        await server.connect()
        
        # Try to access outside allowed paths
        with pytest.raises(PermissionError):
            await server.read_file(path="/etc/passwd")
    
    @pytest.mark.asyncio
    async def test_call_tool(self, server, temp_project_dir):
        """Test calling tools via call_tool method."""
        await server.connect()
        
        test_path = os.path.join(temp_project_dir, "via_call.txt")
        
        # Call write_file via call_tool
        result = await server.call_tool(
            "write_file",
            {"path": test_path, "content": "via call_tool"}
        )
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_call_unknown_tool(self, server):
        """Test calling unknown tool raises error."""
        await server.connect()
        
        with pytest.raises(ValueError, match="Unknown tool"):
            await server.call_tool("unknown_tool", {})
