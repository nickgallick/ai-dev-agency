"""Fetch MCP Server wrapper.

Provides generic HTTP client for making API calls and fetching data.
"""

import logging
from typing import Any, Dict, List, Optional, Union
import httpx

from backend.mcp.manager import MCPServerBase, ServerStatus

logger = logging.getLogger(__name__)

# Default timeout in seconds
DEFAULT_TIMEOUT = 30


class FetchMCPServer(MCPServerBase):
    """MCP server for generic HTTP operations.
    
    Used by: Research, Deploy, Analytics, QA agents.
    """
    
    name = "fetch"
    
    def __init__(self):
        super().__init__()
        self._client: Optional[httpx.AsyncClient] = None
    
    async def connect(self) -> bool:
        """Initialize HTTP client."""
        try:
            self._client = httpx.AsyncClient(
                timeout=DEFAULT_TIMEOUT,
                follow_redirects=True,
                headers={
                    "User-Agent": "AI-Dev-Agency-Fetch/1.0",
                },
            )
            
            self.status = ServerStatus.CONNECTED
            logger.info("Fetch MCP connected")
            return True
            
        except Exception as e:
            self.error_message = str(e)
            logger.error(f"Fetch MCP connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self.status = ServerStatus.DISCONNECTED
    
    async def health_check(self) -> ServerStatus:
        """Check HTTP client health."""
        if not self._client:
            return ServerStatus.DISCONNECTED
        
        try:
            # Test with a simple HEAD request
            response = await self._client.head("https://httpbin.org/status/200")
            if response.status_code == 200:
                return ServerStatus.CONNECTED
            return ServerStatus.DEGRADED
        except Exception:
            # Might just be network issues, still functional
            return ServerStatus.CONNECTED
    
    async def discover_tools(self) -> List[str]:
        """Return available HTTP tools."""
        self.discovered_tools = [
            "get",
            "post",
            "put",
            "patch",
            "delete",
            "head",
            "fetch_json",
            "fetch_text",
            "download_file",
        ]
        return self.discovered_tools
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute an HTTP tool."""
        self._update_last_used()
        
        if not self._client:
            raise RuntimeError("HTTP client not connected")
        
        tool_map = {
            "get": self.get,
            "post": self.post,
            "put": self.put,
            "patch": self.patch,
            "delete": self.delete,
            "head": self.head,
            "fetch_json": self.fetch_json,
            "fetch_text": self.fetch_text,
            "download_file": self.download_file,
        }
        
        handler = tool_map.get(tool_name)
        if not handler:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        return await handler(**arguments)
    
    async def _make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request and return response details."""
        try:
            response = await self._client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                content=data,
                timeout=timeout or DEFAULT_TIMEOUT,
            )
            
            # Try to get response body
            try:
                response_json = response.json()
                content_type = "json"
                body = response_json
            except Exception:
                body = response.text
                content_type = "text"
            
            return {
                "success": True,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content_type": content_type,
                "body": body,
                "url": str(response.url),
            }
        except httpx.TimeoutException:
            return {"success": False, "error": "Request timed out"}
        except httpx.RequestError as e:
            return {"success": False, "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Make a GET request."""
        return await self._make_request(
            "GET", url, headers=headers, params=params, timeout=timeout
        )
    
    async def post(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Make a POST request."""
        return await self._make_request(
            "POST", url, headers=headers, params=params,
            json_data=json_data, data=data, timeout=timeout
        )
    
    async def put(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Make a PUT request."""
        return await self._make_request(
            "PUT", url, headers=headers, params=params,
            json_data=json_data, data=data, timeout=timeout
        )
    
    async def patch(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Make a PATCH request."""
        return await self._make_request(
            "PATCH", url, headers=headers, params=params,
            json_data=json_data, data=data, timeout=timeout
        )
    
    async def delete(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Make a DELETE request."""
        return await self._make_request(
            "DELETE", url, headers=headers, params=params, timeout=timeout
        )
    
    async def head(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Make a HEAD request."""
        try:
            response = await self._client.head(
                url, headers=headers, timeout=timeout or DEFAULT_TIMEOUT
            )
            return {
                "success": True,
                "status_code": response.status_code,
                "headers": dict(response.headers),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def fetch_json(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Fetch JSON data from a URL."""
        result = await self.get(url, headers=headers, params=params)
        
        if not result.get("success"):
            return result
        
        if result.get("content_type") == "json":
            return {"success": True, "data": result.get("body")}
        
        # Try to parse text as JSON
        try:
            import json
            data = json.loads(result.get("body", ""))
            return {"success": True, "data": data}
        except Exception:
            return {"success": False, "error": "Response is not valid JSON"}
    
    async def fetch_text(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Fetch text content from a URL."""
        result = await self.get(url, headers=headers, params=params)
        
        if not result.get("success"):
            return result
        
        body = result.get("body")
        if isinstance(body, dict):
            import json
            body = json.dumps(body)
        
        return {"success": True, "text": body}
    
    async def download_file(
        self,
        url: str,
        output_path: str,
        headers: Optional[Dict[str, str]] = None,
        chunk_size: int = 8192,
    ) -> Dict[str, Any]:
        """Download a file to disk."""
        try:
            async with self._client.stream("GET", url, headers=headers) as response:
                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                    }
                
                total_size = 0
                with open(output_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=chunk_size):
                        f.write(chunk)
                        total_size += len(chunk)
                
                return {
                    "success": True,
                    "path": output_path,
                    "size_bytes": total_size,
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
