"""Tests for GitHub MCP Server."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.mcp.servers.github_mcp import GitHubMCPServer
from backend.mcp.manager import ServerStatus


class TestGitHubMCPServer:
    """Tests for GitHub MCP Server."""
    
    @pytest.fixture
    def server(self, mock_settings):
        """Create GitHub server."""
        return GitHubMCPServer()
    
    @pytest.fixture
    def connected_server(self, server, mock_httpx_client):
        """Create connected GitHub server."""
        server._client = mock_httpx_client
        server._token = "test_token"
        server.status = ServerStatus.CONNECTED
        return server
    
    @pytest.mark.asyncio
    async def test_discover_tools(self, server):
        """Test discovering available tools."""
        tools = await server.discover_tools()
        
        assert "get_repo" in tools
        assert "list_repos" in tools
        assert "get_file_contents" in tools
        assert "create_or_update_file" in tools
        assert "create_branch" in tools
        assert "create_pull_request" in tools
    
    @pytest.mark.asyncio
    async def test_get_repo(self, connected_server, mock_httpx_client):
        """Test getting repository info."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 12345,
            "name": "test-repo",
            "full_name": "owner/test-repo",
            "default_branch": "main",
        }
        mock_httpx_client.get = AsyncMock(return_value=mock_response)
        
        result = await connected_server.get_repo(owner="owner", repo="test-repo")
        
        assert result["success"] is True
        assert result["data"]["name"] == "test-repo"
    
    @pytest.mark.asyncio
    async def test_list_repos(self, connected_server, mock_httpx_client):
        """Test listing repositories."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": 1, "name": "repo1"},
            {"id": 2, "name": "repo2"},
        ]
        mock_httpx_client.get = AsyncMock(return_value=mock_response)
        
        result = await connected_server.list_repos(username="testuser")
        
        assert result["success"] is True
        assert len(result["data"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_file_contents(self, connected_server, mock_httpx_client):
        """Test getting file contents."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "README.md",
            "path": "README.md",
            "content": "SGVsbG8gV29ybGQ=",  # base64 of "Hello World"
            "encoding": "base64",
        }
        mock_httpx_client.get = AsyncMock(return_value=mock_response)
        
        result = await connected_server.get_file_contents(
            owner="owner",
            repo="test-repo",
            path="README.md"
        )
        
        assert result["success"] is True
        assert result["data"]["name"] == "README.md"
    
    @pytest.mark.asyncio
    async def test_create_or_update_file(self, connected_server, mock_httpx_client):
        """Test creating/updating a file."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "content": {"name": "new-file.txt"},
            "commit": {"sha": "abc123"},
        }
        mock_httpx_client.put = AsyncMock(return_value=mock_response)
        
        result = await connected_server.create_or_update_file(
            owner="owner",
            repo="test-repo",
            path="new-file.txt",
            content="Hello World",
            message="Add new file",
            branch="main"
        )
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_list_branches(self, connected_server, mock_httpx_client):
        """Test listing branches."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"name": "main", "protected": True},
            {"name": "develop", "protected": False},
        ]
        mock_httpx_client.get = AsyncMock(return_value=mock_response)
        
        result = await connected_server.list_branches(
            owner="owner",
            repo="test-repo"
        )
        
        assert result["success"] is True
        assert len(result["data"]) == 2
    
    @pytest.mark.asyncio
    async def test_create_branch(self, connected_server, mock_httpx_client):
        """Test creating a branch."""
        # Mock getting ref SHA
        ref_response = MagicMock()
        ref_response.status_code = 200
        ref_response.json.return_value = {"object": {"sha": "abc123"}}
        
        # Mock creating branch
        create_response = MagicMock()
        create_response.status_code = 201
        create_response.json.return_value = {"ref": "refs/heads/feature-branch"}
        
        mock_httpx_client.get = AsyncMock(return_value=ref_response)
        mock_httpx_client.post = AsyncMock(return_value=create_response)
        
        result = await connected_server.create_branch(
            owner="owner",
            repo="test-repo",
            branch="feature-branch",
            from_branch="main"
        )
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_create_pull_request(self, connected_server, mock_httpx_client):
        """Test creating a pull request."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "number": 42,
            "title": "Test PR",
            "state": "open",
            "html_url": "https://github.com/owner/repo/pull/42",
        }
        mock_httpx_client.post = AsyncMock(return_value=mock_response)
        
        result = await connected_server.create_pull_request(
            owner="owner",
            repo="test-repo",
            title="Test PR",
            head="feature-branch",
            base="main",
            body="This is a test PR"
        )
        
        assert result["success"] is True
        assert result["data"]["number"] == 42
    
    @pytest.mark.asyncio
    async def test_list_pull_requests(self, connected_server, mock_httpx_client):
        """Test listing pull requests."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"number": 1, "title": "PR 1", "state": "open"},
            {"number": 2, "title": "PR 2", "state": "open"},
        ]
        mock_httpx_client.get = AsyncMock(return_value=mock_response)
        
        result = await connected_server.list_pull_requests(
            owner="owner",
            repo="test-repo",
            state="open"
        )
        
        assert result["success"] is True
        assert len(result["data"]) == 2
    
    @pytest.mark.asyncio
    async def test_call_tool(self, connected_server, mock_httpx_client):
        """Test calling tools via call_tool method."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "test-repo"}
        mock_httpx_client.get = AsyncMock(return_value=mock_response)
        
        result = await connected_server.call_tool(
            "get_repo",
            {"owner": "owner", "repo": "test-repo"}
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
            await server.call_tool("get_repo", {"owner": "o", "repo": "r"})
