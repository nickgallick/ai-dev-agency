"""Browser MCP Server wrapper.

Connects to the Puppeteer MCP server running in a separate Docker container
for browser automation and web scraping.
"""

import logging
from typing import Any, Dict, List, Optional
import httpx

from mcp.manager import MCPServerBase, ServerStatus
from mcp.config import MCP_SERVERS
from config.settings import get_settings

logger = logging.getLogger(__name__)


class BrowserMCPServer(MCPServerBase):
    """MCP server for browser automation via Puppeteer.
    
    Used by: Research, QA agents.
    Connects to external Puppeteer container.
    """
    
    name = "browser"
    
    def __init__(self):
        super().__init__()
        self._client: Optional[httpx.AsyncClient] = None
        self._server_url: str = ""
    
    async def connect(self) -> bool:
        """Initialize connection to Puppeteer server."""
        try:
            settings = get_settings()
            config = MCP_SERVERS.get("browser", {})
            
            self._server_url = config.get("config", {}).get(
                "server_url", settings.mcp_browser_url
            )
            
            self._client = httpx.AsyncClient(
                base_url=self._server_url,
                timeout=60.0,  # Browser operations can be slow
            )
            
            # Test connection with health check endpoint
            response = await self._client.get("/health")
            if response.status_code == 200:
                self.status = ServerStatus.CONNECTED
                logger.info(f"Browser MCP connected to {self._server_url}")
                return True
            
            self.status = ServerStatus.DEGRADED
            return True
            
        except httpx.ConnectError:
            self.error_message = f"Cannot connect to browser server at {self._server_url}"
            logger.warning(self.error_message)
            return False
        except Exception as e:
            self.error_message = str(e)
            logger.error(f"Browser MCP connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Close browser server connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self.status = ServerStatus.DISCONNECTED
    
    async def health_check(self) -> ServerStatus:
        """Check Puppeteer server availability."""
        if not self._client:
            return ServerStatus.DISCONNECTED
        
        try:
            response = await self._client.get("/health")
            if response.status_code == 200:
                return ServerStatus.CONNECTED
            return ServerStatus.DEGRADED
        except Exception:
            return ServerStatus.DISCONNECTED
    
    async def discover_tools(self) -> List[str]:
        """Return available browser tools."""
        self.discovered_tools = [
            "navigate",
            "screenshot",
            "get_content",
            "click",
            "type_text",
            "wait_for_selector",
            "evaluate",
            "get_links",
            "extract_text",
        ]
        return self.discovered_tools
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a browser tool."""
        self._update_last_used()
        
        if not self._client:
            raise RuntimeError("Browser server not connected")
        
        tool_map = {
            "navigate": self.navigate,
            "screenshot": self.screenshot,
            "get_content": self.get_content,
            "click": self.click,
            "type_text": self.type_text,
            "wait_for_selector": self.wait_for_selector,
            "evaluate": self.evaluate,
            "get_links": self.get_links,
            "extract_text": self.extract_text,
        }
        
        handler = tool_map.get(tool_name)
        if not handler:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        return await handler(**arguments)
    
    async def _call_puppeteer(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to the Puppeteer server."""
        try:
            response = await self._client.post(
                "/execute",
                json={"action": action, "params": params},
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {
                    "success": False,
                    "error": response.text,
                    "status_code": response.status_code,
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def navigate(self, url: str, wait_until: str = "networkidle0") -> Dict[str, Any]:
        """Navigate to a URL."""
        return await self._call_puppeteer("navigate", {
            "url": url,
            "waitUntil": wait_until,
        })
    
    async def screenshot(
        self,
        path: Optional[str] = None,
        full_page: bool = False,
        selector: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Take a screenshot."""
        params = {"fullPage": full_page}
        if path:
            params["path"] = path
        if selector:
            params["selector"] = selector
        
        return await self._call_puppeteer("screenshot", params)
    
    async def get_content(self) -> Dict[str, Any]:
        """Get page HTML content."""
        return await self._call_puppeteer("getContent", {})
    
    async def click(self, selector: str) -> Dict[str, Any]:
        """Click an element."""
        return await self._call_puppeteer("click", {"selector": selector})
    
    async def type_text(self, selector: str, text: str, delay: int = 0) -> Dict[str, Any]:
        """Type text into an input."""
        return await self._call_puppeteer("type", {
            "selector": selector,
            "text": text,
            "delay": delay,
        })
    
    async def wait_for_selector(
        self, selector: str, timeout: int = 30000
    ) -> Dict[str, Any]:
        """Wait for an element to appear."""
        return await self._call_puppeteer("waitForSelector", {
            "selector": selector,
            "timeout": timeout,
        })
    
    async def evaluate(self, script: str) -> Dict[str, Any]:
        """Execute JavaScript in the page context."""
        return await self._call_puppeteer("evaluate", {"script": script})
    
    async def get_links(self) -> Dict[str, Any]:
        """Extract all links from the page."""
        script = """
            Array.from(document.querySelectorAll('a[href]'))
                .map(a => ({href: a.href, text: a.textContent.trim()}))
        """
        return await self._call_puppeteer("evaluate", {"script": script})
    
    async def extract_text(self, selector: str = "body") -> Dict[str, Any]:
        """Extract text content from an element."""
        script = f"""
            document.querySelector('{selector}')?.textContent || ''
        """
        return await self._call_puppeteer("evaluate", {"script": script})
