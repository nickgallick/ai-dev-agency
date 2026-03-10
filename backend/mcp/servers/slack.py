"""Slack MCP Server wrapper.

Provides Slack webhook integration for notifications.
"""

import logging
from typing import Any, Dict, List, Optional
import httpx

from backend.mcp.manager import MCPServerBase, ServerStatus
from backend.mcp.credential_resolver import get_credential
from backend.config.settings import get_settings

logger = logging.getLogger(__name__)


class SlackMCPServer(MCPServerBase):
    """MCP server for Slack notifications via webhook.
    
    Used by: Delivery, Deploy agents.
    """
    
    name = "slack"
    
    def __init__(self):
        super().__init__()
        self._webhook_url: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_webhook_url(self) -> Optional[str]:
        """Get Slack webhook URL from UI credentials or environment."""
        # Try UI credentials first
        url = await get_credential("slack", "webhook_url")
        if url:
            return url
        
        # Fall back to environment
        settings = get_settings()
        return settings.slack_webhook_url
    
    async def connect(self) -> bool:
        """Initialize Slack webhook connection."""
        try:
            self._webhook_url = await self._get_webhook_url()
            
            if not self._webhook_url:
                self.error_message = "Slack webhook URL not configured"
                logger.warning(self.error_message)
                self.status = ServerStatus.DEGRADED
                return True  # Server available but not fully configured
            
            self._client = httpx.AsyncClient(timeout=30.0)
            self.status = ServerStatus.CONNECTED
            logger.info("Slack MCP connected")
            return True
            
        except Exception as e:
            self.error_message = str(e)
            logger.error(f"Slack MCP connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Close Slack client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self.status = ServerStatus.DISCONNECTED
    
    async def health_check(self) -> ServerStatus:
        """Check Slack configuration."""
        if not self._webhook_url:
            return ServerStatus.DEGRADED
        
        # We can't truly test the webhook without sending a message
        # Just verify the URL format
        if self._webhook_url.startswith("https://hooks.slack.com/"):
            return ServerStatus.CONNECTED
        
        return ServerStatus.DEGRADED
    
    async def discover_tools(self) -> List[str]:
        """Return available Slack tools."""
        self.discovered_tools = [
            "send_message",
            "send_blocks",
            "send_notification",
        ]
        return self.discovered_tools
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a Slack tool."""
        self._update_last_used()
        
        tool_map = {
            "send_message": self.send_message,
            "send_blocks": self.send_blocks,
            "send_notification": self.send_notification,
        }
        
        handler = tool_map.get(tool_name)
        if not handler:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        return await handler(**arguments)
    
    async def send_message(
        self,
        text: str,
        channel: Optional[str] = None,
        username: Optional[str] = None,
        icon_emoji: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a simple text message."""
        if not self._webhook_url:
            return {"success": False, "error": "Webhook URL not configured"}
        
        payload = {"text": text}
        
        if channel:
            payload["channel"] = channel
        if username:
            payload["username"] = username
        if icon_emoji:
            payload["icon_emoji"] = icon_emoji
        
        try:
            response = await self._client.post(self._webhook_url, json=payload)
            success = response.status_code == 200
            return {
                "success": success,
                "status_code": response.status_code,
                "response": response.text if not success else "ok",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def send_blocks(
        self,
        blocks: List[Dict[str, Any]],
        text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a message with Slack Block Kit blocks."""
        if not self._webhook_url:
            return {"success": False, "error": "Webhook URL not configured"}
        
        payload = {"blocks": blocks}
        if text:
            payload["text"] = text  # Fallback text
        
        try:
            response = await self._client.post(self._webhook_url, json=payload)
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def send_notification(
        self,
        title: str,
        message: str,
        status: str = "info",  # info, success, warning, error
        fields: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Send a formatted notification message."""
        # Color mapping
        color_map = {
            "info": "#3498db",
            "success": "#2ecc71",
            "warning": "#f39c12",
            "error": "#e74c3c",
        }
        color = color_map.get(status, color_map["info"])
        
        # Emoji mapping
        emoji_map = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
        }
        emoji = emoji_map.get(status, emoji_map["info"])
        
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{emoji} {title}"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": message},
            },
        ]
        
        if fields:
            field_blocks = [
                {"type": "mrkdwn", "text": f"*{k}:*\n{v}"}
                for k, v in fields.items()
            ]
            blocks.append({"type": "section", "fields": field_blocks})
        
        return await self.send_blocks(blocks, text=f"{title}: {message}")
