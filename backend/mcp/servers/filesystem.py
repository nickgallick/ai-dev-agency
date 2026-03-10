"""Filesystem MCP Server wrapper.

Provides file system operations for reading, writing, and listing
project files within allowed paths.
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.mcp.manager import MCPServerBase, ServerStatus
from backend.mcp.config import MCP_SERVERS

logger = logging.getLogger(__name__)


class FilesystemMCPServer(MCPServerBase):
    """MCP server for filesystem operations.
    
    Used by: Architect, V0 Codegen, Security agents.
    """
    
    name = "filesystem"
    
    def __init__(self):
        super().__init__()
        config = MCP_SERVERS.get("filesystem", {})
        self.allowed_paths = config.get("config", {}).get(
            "allowed_paths", ["/tmp/projects", "/app/projects"]
        )
        self._ensure_paths_exist()
    
    def _ensure_paths_exist(self) -> None:
        """Ensure allowed paths exist."""
        for path in self.allowed_paths:
            Path(path).mkdir(parents=True, exist_ok=True)
    
    def _validate_path(self, path: str) -> bool:
        """Validate that path is within allowed directories."""
        abs_path = os.path.abspath(path)
        return any(
            abs_path.startswith(os.path.abspath(allowed))
            for allowed in self.allowed_paths
        )
    
    async def connect(self) -> bool:
        """Initialize filesystem server."""
        try:
            self._ensure_paths_exist()
            self.status = ServerStatus.CONNECTED
            logger.info(f"Filesystem MCP connected with paths: {self.allowed_paths}")
            return True
        except Exception as e:
            self.error_message = str(e)
            logger.error(f"Filesystem MCP connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Cleanup filesystem server."""
        self.status = ServerStatus.DISCONNECTED
    
    async def health_check(self) -> ServerStatus:
        """Check filesystem accessibility."""
        try:
            for path in self.allowed_paths:
                if not os.path.isdir(path):
                    return ServerStatus.DEGRADED
            return ServerStatus.CONNECTED
        except Exception:
            return ServerStatus.DISCONNECTED
    
    async def discover_tools(self) -> List[str]:
        """Return available filesystem tools."""
        self.discovered_tools = [
            "read_file",
            "write_file",
            "list_directory",
            "create_directory",
            "delete_file",
            "file_exists",
            "get_file_info",
        ]
        return self.discovered_tools
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a filesystem tool."""
        self._update_last_used()
        
        if tool_name == "read_file":
            return await self.read_file(**arguments)
        elif tool_name == "write_file":
            return await self.write_file(**arguments)
        elif tool_name == "list_directory":
            return await self.list_directory(**arguments)
        elif tool_name == "create_directory":
            return await self.create_directory(**arguments)
        elif tool_name == "delete_file":
            return await self.delete_file(**arguments)
        elif tool_name == "file_exists":
            return await self.file_exists(**arguments)
        elif tool_name == "get_file_info":
            return await self.get_file_info(**arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    async def read_file(self, path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """Read file contents."""
        if not self._validate_path(path):
            raise PermissionError(f"Path not allowed: {path}")
        
        try:
            with open(path, "r", encoding=encoding) as f:
                content = f.read()
            return {"success": True, "content": content, "path": path}
        except FileNotFoundError:
            return {"success": False, "error": "File not found", "path": path}
        except Exception as e:
            return {"success": False, "error": str(e), "path": path}
    
    async def write_file(
        self, path: str, content: str, encoding: str = "utf-8", create_dirs: bool = True
    ) -> Dict[str, Any]:
        """Write content to file."""
        if not self._validate_path(path):
            raise PermissionError(f"Path not allowed: {path}")
        
        try:
            if create_dirs:
                Path(path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, "w", encoding=encoding) as f:
                f.write(content)
            
            return {"success": True, "path": path, "bytes_written": len(content.encode(encoding))}
        except Exception as e:
            return {"success": False, "error": str(e), "path": path}
    
    async def list_directory(
        self, path: str, recursive: bool = False, pattern: str = "*"
    ) -> Dict[str, Any]:
        """List directory contents."""
        if not self._validate_path(path):
            raise PermissionError(f"Path not allowed: {path}")
        
        try:
            p = Path(path)
            if not p.is_dir():
                return {"success": False, "error": "Not a directory", "path": path}
            
            if recursive:
                items = list(p.rglob(pattern))
            else:
                items = list(p.glob(pattern))
            
            entries = []
            for item in items:
                entries.append({
                    "name": item.name,
                    "path": str(item),
                    "is_file": item.is_file(),
                    "is_dir": item.is_dir(),
                })
            
            return {"success": True, "path": path, "entries": entries}
        except Exception as e:
            return {"success": False, "error": str(e), "path": path}
    
    async def create_directory(self, path: str) -> Dict[str, Any]:
        """Create a directory."""
        if not self._validate_path(path):
            raise PermissionError(f"Path not allowed: {path}")
        
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return {"success": True, "path": path}
        except Exception as e:
            return {"success": False, "error": str(e), "path": path}
    
    async def delete_file(self, path: str) -> Dict[str, Any]:
        """Delete a file."""
        if not self._validate_path(path):
            raise PermissionError(f"Path not allowed: {path}")
        
        try:
            Path(path).unlink()
            return {"success": True, "path": path}
        except FileNotFoundError:
            return {"success": False, "error": "File not found", "path": path}
        except Exception as e:
            return {"success": False, "error": str(e), "path": path}
    
    async def file_exists(self, path: str) -> Dict[str, Any]:
        """Check if file exists."""
        if not self._validate_path(path):
            raise PermissionError(f"Path not allowed: {path}")
        
        return {"exists": Path(path).exists(), "path": path}
    
    async def get_file_info(self, path: str) -> Dict[str, Any]:
        """Get file metadata."""
        if not self._validate_path(path):
            raise PermissionError(f"Path not allowed: {path}")
        
        try:
            p = Path(path)
            if not p.exists():
                return {"success": False, "error": "File not found", "path": path}
            
            stat = p.stat()
            return {
                "success": True,
                "path": path,
                "name": p.name,
                "is_file": p.is_file(),
                "is_dir": p.is_dir(),
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "created": stat.st_ctime,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "path": path}
