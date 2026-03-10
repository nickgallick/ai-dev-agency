"""GitHub MCP Server wrapper.

Provides GitHub repository operations including file management,
branch operations, and repository queries.
"""

import logging
from typing import Any, Dict, List, Optional
import httpx

from mcp.manager import MCPServerBase, ServerStatus
from mcp.credential_resolver import get_credential
from config.settings import get_settings

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


class GitHubMCPServer(MCPServerBase):
    """MCP server for GitHub operations.
    
    Used by: V0 Codegen, Deploy, Delivery agents.
    """
    
    name = "github"
    
    def __init__(self):
        super().__init__()
        self._client: Optional[httpx.AsyncClient] = None
        self._token: Optional[str] = None
    
    async def _get_token(self) -> Optional[str]:
        """Get GitHub token from UI credentials or environment."""
        # Try UI credentials first
        token = await get_credential("github", "token")
        if token:
            return token
        
        # Fall back to environment
        settings = get_settings()
        return settings.github_token
    
    async def connect(self) -> bool:
        """Initialize GitHub API client."""
        try:
            self._token = await self._get_token()
            
            headers = {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"
            
            self._client = httpx.AsyncClient(
                base_url=GITHUB_API_BASE,
                headers=headers,
                timeout=30.0,
            )
            
            # Test connection
            if self._token:
                response = await self._client.get("/user")
                if response.status_code == 200:
                    self.status = ServerStatus.CONNECTED
                    logger.info("GitHub MCP connected with authenticated user")
                    return True
            
            # Unauthenticated connection (limited API)
            self.status = ServerStatus.DEGRADED
            logger.warning("GitHub MCP connected without authentication (limited API)")
            return True
            
        except Exception as e:
            self.error_message = str(e)
            logger.error(f"GitHub MCP connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Close GitHub API client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self.status = ServerStatus.DISCONNECTED
    
    async def health_check(self) -> ServerStatus:
        """Check GitHub API availability."""
        if not self._client:
            return ServerStatus.DISCONNECTED
        
        try:
            response = await self._client.get("/rate_limit")
            if response.status_code == 200:
                data = response.json()
                remaining = data.get("resources", {}).get("core", {}).get("remaining", 0)
                if remaining < 10:
                    return ServerStatus.DEGRADED
                return ServerStatus.CONNECTED
            return ServerStatus.DEGRADED
        except Exception:
            return ServerStatus.DISCONNECTED
    
    async def discover_tools(self) -> List[str]:
        """Return available GitHub tools."""
        self.discovered_tools = [
            "get_repo",
            "list_repos",
            "get_file_contents",
            "create_or_update_file",
            "delete_file",
            "list_branches",
            "create_branch",
            "create_pull_request",
            "list_pull_requests",
            "get_commit",
            "list_commits",
        ]
        return self.discovered_tools
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a GitHub tool."""
        self._update_last_used()
        
        if not self._client:
            raise RuntimeError("GitHub client not connected")
        
        tool_map = {
            "get_repo": self.get_repo,
            "list_repos": self.list_repos,
            "get_file_contents": self.get_file_contents,
            "create_or_update_file": self.create_or_update_file,
            "delete_file": self.delete_file,
            "list_branches": self.list_branches,
            "create_branch": self.create_branch,
            "create_pull_request": self.create_pull_request,
            "list_pull_requests": self.list_pull_requests,
            "get_commit": self.get_commit,
            "list_commits": self.list_commits,
        }
        
        handler = tool_map.get(tool_name)
        if not handler:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        return await handler(**arguments)
    
    async def get_repo(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository information."""
        response = await self._client.get(f"/repos/{owner}/{repo}")
        return {"success": response.status_code == 200, "data": response.json()}
    
    async def list_repos(
        self, username: Optional[str] = None, org: Optional[str] = None, per_page: int = 30
    ) -> Dict[str, Any]:
        """List repositories."""
        if org:
            endpoint = f"/orgs/{org}/repos"
        elif username:
            endpoint = f"/users/{username}/repos"
        else:
            endpoint = "/user/repos"
        
        response = await self._client.get(endpoint, params={"per_page": per_page})
        return {"success": response.status_code == 200, "data": response.json()}
    
    async def get_file_contents(
        self, owner: str, repo: str, path: str, ref: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get file contents from repository."""
        params = {"ref": ref} if ref else {}
        response = await self._client.get(
            f"/repos/{owner}/{repo}/contents/{path}", params=params
        )
        return {"success": response.status_code == 200, "data": response.json()}
    
    async def create_or_update_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str = "main",
        sha: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create or update a file in repository."""
        import base64
        
        data = {
            "message": message,
            "content": base64.b64encode(content.encode()).decode(),
            "branch": branch,
        }
        if sha:
            data["sha"] = sha
        
        response = await self._client.put(
            f"/repos/{owner}/{repo}/contents/{path}", json=data
        )
        return {"success": response.status_code in [200, 201], "data": response.json()}
    
    async def delete_file(
        self, owner: str, repo: str, path: str, message: str, sha: str, branch: str = "main"
    ) -> Dict[str, Any]:
        """Delete a file from repository."""
        data = {"message": message, "sha": sha, "branch": branch}
        response = await self._client.delete(
            f"/repos/{owner}/{repo}/contents/{path}", json=data
        )
        return {"success": response.status_code == 200, "data": response.json()}
    
    async def list_branches(
        self, owner: str, repo: str, per_page: int = 30
    ) -> Dict[str, Any]:
        """List repository branches."""
        response = await self._client.get(
            f"/repos/{owner}/{repo}/branches", params={"per_page": per_page}
        )
        return {"success": response.status_code == 200, "data": response.json()}
    
    async def create_branch(
        self, owner: str, repo: str, branch: str, from_branch: str = "main"
    ) -> Dict[str, Any]:
        """Create a new branch."""
        # Get SHA of source branch
        ref_response = await self._client.get(
            f"/repos/{owner}/{repo}/git/refs/heads/{from_branch}"
        )
        if ref_response.status_code != 200:
            return {"success": False, "error": "Source branch not found"}
        
        sha = ref_response.json()["object"]["sha"]
        
        # Create new branch
        response = await self._client.post(
            f"/repos/{owner}/{repo}/git/refs",
            json={"ref": f"refs/heads/{branch}", "sha": sha},
        )
        return {"success": response.status_code == 201, "data": response.json()}
    
    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str = "main",
        body: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a pull request."""
        data = {"title": title, "head": head, "base": base}
        if body:
            data["body"] = body
        
        response = await self._client.post(
            f"/repos/{owner}/{repo}/pulls", json=data
        )
        return {"success": response.status_code == 201, "data": response.json()}
    
    async def list_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        per_page: int = 30,
    ) -> Dict[str, Any]:
        """List pull requests."""
        response = await self._client.get(
            f"/repos/{owner}/{repo}/pulls",
            params={"state": state, "per_page": per_page},
        )
        return {"success": response.status_code == 200, "data": response.json()}
    
    async def get_commit(self, owner: str, repo: str, ref: str) -> Dict[str, Any]:
        """Get a specific commit."""
        response = await self._client.get(f"/repos/{owner}/{repo}/commits/{ref}")
        return {"success": response.status_code == 200, "data": response.json()}
    
    async def list_commits(
        self,
        owner: str,
        repo: str,
        sha: Optional[str] = None,
        per_page: int = 30,
    ) -> Dict[str, Any]:
        """List repository commits."""
        params = {"per_page": per_page}
        if sha:
            params["sha"] = sha
        
        response = await self._client.get(
            f"/repos/{owner}/{repo}/commits", params=params
        )
        return {"success": response.status_code == 200, "data": response.json()}
