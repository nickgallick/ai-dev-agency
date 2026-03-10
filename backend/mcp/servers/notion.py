"""Notion MCP Server wrapper.

Provides Notion API integration for documentation management.
"""

import logging
from typing import Any, Dict, List, Optional
import httpx

from mcp.manager import MCPServerBase, ServerStatus
from mcp.credential_resolver import get_credential
from config.settings import get_settings

logger = logging.getLogger(__name__)

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


class NotionMCPServer(MCPServerBase):
    """MCP server for Notion API operations.
    
    Used by: Delivery, Coding Standards agents.
    """
    
    name = "notion"
    
    def __init__(self):
        super().__init__()
        self._client: Optional[httpx.AsyncClient] = None
        self._token: Optional[str] = None
    
    async def _get_token(self) -> Optional[str]:
        """Get Notion token from UI credentials or environment."""
        # Try UI credentials first
        token = await get_credential("notion", "token")
        if token:
            return token
        
        # Fall back to environment
        settings = get_settings()
        return settings.notion_token
    
    async def connect(self) -> bool:
        """Initialize Notion API client."""
        try:
            self._token = await self._get_token()
            
            if not self._token:
                self.error_message = "Notion token not configured"
                logger.warning(self.error_message)
                self.status = ServerStatus.DEGRADED
                return True  # Server available but not configured
            
            self._client = httpx.AsyncClient(
                base_url=NOTION_API_BASE,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Notion-Version": NOTION_VERSION,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
            
            # Test connection
            response = await self._client.get("/users/me")
            if response.status_code == 200:
                self.status = ServerStatus.CONNECTED
                logger.info("Notion MCP connected")
                return True
            
            self.error_message = "Notion authentication failed"
            self.status = ServerStatus.DEGRADED
            return True
            
        except Exception as e:
            self.error_message = str(e)
            logger.error(f"Notion MCP connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Close Notion API client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self.status = ServerStatus.DISCONNECTED
    
    async def health_check(self) -> ServerStatus:
        """Check Notion API availability."""
        if not self._token:
            return ServerStatus.DEGRADED
        
        if not self._client:
            return ServerStatus.DISCONNECTED
        
        try:
            response = await self._client.get("/users/me")
            if response.status_code == 200:
                return ServerStatus.CONNECTED
            return ServerStatus.DEGRADED
        except Exception:
            return ServerStatus.DISCONNECTED
    
    async def discover_tools(self) -> List[str]:
        """Return available Notion tools."""
        self.discovered_tools = [
            "search",
            "get_page",
            "create_page",
            "update_page",
            "get_database",
            "query_database",
            "get_block_children",
            "append_block_children",
        ]
        return self.discovered_tools
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a Notion tool."""
        self._update_last_used()
        
        if not self._client:
            raise RuntimeError("Notion client not connected")
        
        if not self._token:
            return {"success": False, "error": "Notion token not configured"}
        
        tool_map = {
            "search": self.search,
            "get_page": self.get_page,
            "create_page": self.create_page,
            "update_page": self.update_page,
            "get_database": self.get_database,
            "query_database": self.query_database,
            "get_block_children": self.get_block_children,
            "append_block_children": self.append_block_children,
        }
        
        handler = tool_map.get(tool_name)
        if not handler:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        return await handler(**arguments)
    
    async def search(
        self,
        query: str,
        filter_type: Optional[str] = None,  # page, database
        sort_direction: str = "descending",
        page_size: int = 10,
    ) -> Dict[str, Any]:
        """Search Notion workspace."""
        payload = {
            "query": query,
            "page_size": page_size,
            "sort": {
                "direction": sort_direction,
                "timestamp": "last_edited_time",
            },
        }
        
        if filter_type:
            payload["filter"] = {"property": "object", "value": filter_type}
        
        try:
            response = await self._client.post("/search", json=payload)
            return {
                "success": response.status_code == 200,
                "data": response.json(),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_page(self, page_id: str) -> Dict[str, Any]:
        """Get a page by ID."""
        try:
            response = await self._client.get(f"/pages/{page_id}")
            return {
                "success": response.status_code == 200,
                "data": response.json(),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def create_page(
        self,
        parent_id: str,
        parent_type: str = "page_id",  # page_id or database_id
        title: str = "",
        properties: Optional[Dict[str, Any]] = None,
        children: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Create a new page."""
        parent = {parent_type: parent_id}
        
        # Default properties with title
        if not properties:
            properties = {
                "title": {
                    "title": [{"text": {"content": title}}]
                }
            }
        
        payload = {
            "parent": parent,
            "properties": properties,
        }
        
        if children:
            payload["children"] = children
        
        try:
            response = await self._client.post("/pages", json=payload)
            return {
                "success": response.status_code == 200,
                "data": response.json(),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def update_page(
        self,
        page_id: str,
        properties: Dict[str, Any],
        archived: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update page properties."""
        payload = {"properties": properties}
        
        if archived is not None:
            payload["archived"] = archived
        
        try:
            response = await self._client.patch(f"/pages/{page_id}", json=payload)
            return {
                "success": response.status_code == 200,
                "data": response.json(),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_database(self, database_id: str) -> Dict[str, Any]:
        """Get a database by ID."""
        try:
            response = await self._client.get(f"/databases/{database_id}")
            return {
                "success": response.status_code == 200,
                "data": response.json(),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def query_database(
        self,
        database_id: str,
        filter: Optional[Dict[str, Any]] = None,
        sorts: Optional[List[Dict[str, Any]]] = None,
        page_size: int = 100,
    ) -> Dict[str, Any]:
        """Query a database."""
        payload = {"page_size": page_size}
        
        if filter:
            payload["filter"] = filter
        if sorts:
            payload["sorts"] = sorts
        
        try:
            response = await self._client.post(
                f"/databases/{database_id}/query", json=payload
            )
            return {
                "success": response.status_code == 200,
                "data": response.json(),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_block_children(
        self, block_id: str, page_size: int = 100
    ) -> Dict[str, Any]:
        """Get child blocks of a block/page."""
        try:
            response = await self._client.get(
                f"/blocks/{block_id}/children",
                params={"page_size": page_size},
            )
            return {
                "success": response.status_code == 200,
                "data": response.json(),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def append_block_children(
        self, block_id: str, children: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Append children blocks to a block/page."""
        try:
            response = await self._client.patch(
                f"/blocks/{block_id}/children",
                json={"children": children},
            )
            return {
                "success": response.status_code == 200,
                "data": response.json(),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
