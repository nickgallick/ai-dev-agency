"""Memory MCP Server wrapper.

Provides Redis-backed persistent memory storage for cross-session
and cross-agent knowledge sharing.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import redis.asyncio as redis

from backend.mcp.manager import MCPServerBase, ServerStatus
from backend.config.settings import get_settings

logger = logging.getLogger(__name__)

# Key prefixes for organization
PREFIX_MEMORY = "mcp:memory:"
PREFIX_INDEX = "mcp:index:"
PREFIX_AGENT = "mcp:agent:"


class MemoryMCPServer(MCPServerBase):
    """MCP server for Redis-backed memory storage.
    
    Used by: Research, Architect, Design System, QA agents.
    Provides persistent memory across sessions and agents.
    """
    
    name = "memory"
    
    def __init__(self):
        super().__init__()
        self._redis: Optional[redis.Redis] = None
    
    async def connect(self) -> bool:
        """Initialize Redis connection."""
        try:
            settings = get_settings()
            
            self._redis = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            
            # Test connection
            await self._redis.ping()
            
            self.status = ServerStatus.CONNECTED
            logger.info("Memory MCP connected to Redis")
            return True
            
        except Exception as e:
            self.error_message = str(e)
            logger.error(f"Memory MCP connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
        self.status = ServerStatus.DISCONNECTED
    
    async def health_check(self) -> ServerStatus:
        """Check Redis connectivity."""
        if not self._redis:
            return ServerStatus.DISCONNECTED
        
        try:
            await self._redis.ping()
            return ServerStatus.CONNECTED
        except Exception:
            return ServerStatus.DISCONNECTED
    
    async def discover_tools(self) -> List[str]:
        """Return available memory tools."""
        self.discovered_tools = [
            "store",
            "retrieve",
            "search",
            "delete",
            "list_keys",
            "store_agent_context",
            "get_agent_context",
            "get_project_memory",
            "set_project_memory",
        ]
        return self.discovered_tools
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a memory tool."""
        self._update_last_used()
        
        if not self._redis:
            raise RuntimeError("Redis not connected")
        
        tool_map = {
            "store": self.store,
            "retrieve": self.retrieve,
            "search": self.search,
            "delete": self.delete,
            "list_keys": self.list_keys,
            "store_agent_context": self.store_agent_context,
            "get_agent_context": self.get_agent_context,
            "get_project_memory": self.get_project_memory,
            "set_project_memory": self.set_project_memory,
        }
        
        handler = tool_map.get(tool_name)
        if not handler:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        return await handler(**arguments)
    
    async def store(
        self,
        key: str,
        value: Any,
        namespace: str = "default",
        ttl_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Store a value with optional metadata."""
        full_key = f"{PREFIX_MEMORY}{namespace}:{key}"
        
        data = {
            "value": value,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
            "namespace": namespace,
        }
        
        try:
            serialized = json.dumps(data)
            if ttl_seconds:
                await self._redis.setex(full_key, ttl_seconds, serialized)
            else:
                await self._redis.set(full_key, serialized)
            
            # Update index
            await self._redis.sadd(f"{PREFIX_INDEX}{namespace}", key)
            
            return {"success": True, "key": key, "namespace": namespace}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def retrieve(
        self, key: str, namespace: str = "default"
    ) -> Dict[str, Any]:
        """Retrieve a value by key."""
        full_key = f"{PREFIX_MEMORY}{namespace}:{key}"
        
        try:
            data = await self._redis.get(full_key)
            if data:
                parsed = json.loads(data)
                return {
                    "success": True,
                    "found": True,
                    "value": parsed.get("value"),
                    "metadata": parsed.get("metadata", {}),
                    "created_at": parsed.get("created_at"),
                }
            return {"success": True, "found": False, "value": None}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def search(
        self, pattern: str, namespace: str = "default", limit: int = 100
    ) -> Dict[str, Any]:
        """Search for keys matching a pattern."""
        full_pattern = f"{PREFIX_MEMORY}{namespace}:{pattern}"
        
        try:
            keys = []
            async for key in self._redis.scan_iter(match=full_pattern, count=limit):
                # Remove prefix from key
                short_key = key.replace(f"{PREFIX_MEMORY}{namespace}:", "")
                keys.append(short_key)
                if len(keys) >= limit:
                    break
            
            return {"success": True, "keys": keys, "count": len(keys)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def delete(self, key: str, namespace: str = "default") -> Dict[str, Any]:
        """Delete a key."""
        full_key = f"{PREFIX_MEMORY}{namespace}:{key}"
        
        try:
            deleted = await self._redis.delete(full_key)
            await self._redis.srem(f"{PREFIX_INDEX}{namespace}", key)
            return {"success": True, "deleted": deleted > 0}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def list_keys(
        self, namespace: str = "default", pattern: str = "*"
    ) -> Dict[str, Any]:
        """List all keys in a namespace."""
        try:
            # Use index set for efficiency
            keys = await self._redis.smembers(f"{PREFIX_INDEX}{namespace}")
            
            # Filter by pattern if not wildcard
            if pattern != "*":
                import fnmatch
                keys = [k for k in keys if fnmatch.fnmatch(k, pattern)]
            
            return {"success": True, "keys": list(keys), "count": len(keys)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def store_agent_context(
        self,
        agent_name: str,
        project_id: str,
        context: Dict[str, Any],
        ttl_seconds: int = 86400,  # 24 hours default
    ) -> Dict[str, Any]:
        """Store agent-specific context for a project."""
        key = f"{PREFIX_AGENT}{agent_name}:{project_id}"
        
        data = {
            "context": context,
            "agent": agent_name,
            "project_id": project_id,
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        try:
            await self._redis.setex(key, ttl_seconds, json.dumps(data))
            return {"success": True, "agent": agent_name, "project_id": project_id}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_agent_context(
        self, agent_name: str, project_id: str
    ) -> Dict[str, Any]:
        """Retrieve agent-specific context for a project."""
        key = f"{PREFIX_AGENT}{agent_name}:{project_id}"
        
        try:
            data = await self._redis.get(key)
            if data:
                parsed = json.loads(data)
                return {
                    "success": True,
                    "found": True,
                    "context": parsed.get("context", {}),
                    "updated_at": parsed.get("updated_at"),
                }
            return {"success": True, "found": False, "context": {}}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_project_memory(
        self, project_id: str, keys: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get all memory entries for a project."""
        namespace = f"project:{project_id}"
        
        try:
            if keys:
                results = {}
                for key in keys:
                    result = await self.retrieve(key, namespace=namespace)
                    if result.get("found"):
                        results[key] = result.get("value")
                return {"success": True, "data": results}
            else:
                # Get all keys in project namespace
                all_keys = await self.list_keys(namespace=namespace)
                results = {}
                for key in all_keys.get("keys", []):
                    result = await self.retrieve(key, namespace=namespace)
                    if result.get("found"):
                        results[key] = result.get("value")
                return {"success": True, "data": results}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def set_project_memory(
        self,
        project_id: str,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Set a memory entry for a project."""
        namespace = f"project:{project_id}"
        return await self.store(
            key=key,
            value=value,
            namespace=namespace,
            ttl_seconds=ttl_seconds,
            metadata={"project_id": project_id},
        )
