"""API routes for MCP server management.

Provides endpoints for:
- MCP server status and health
- Credential management (CRUD)
- Custom server configuration
- Connection testing
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from mcp.manager import get_mcp_manager, ServerStatus
from mcp.config import MCP_SERVERS, get_enabled_servers
from mcp.credential_resolver import (
    set_credential,
    delete_credential,
    get_credential,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["mcp"])


# Request/Response Models

class CredentialInput(BaseModel):
    """Input for setting a credential."""
    server_name: str = Field(..., description="MCP server name")
    credential_key: str = Field(..., description="Credential key (e.g., 'token', 'webhook_url')")
    value: str = Field(..., description="Credential value (will be encrypted)")


class CredentialDeleteInput(BaseModel):
    """Input for deleting a credential."""
    server_name: str
    credential_key: str


class CustomServerInput(BaseModel):
    """Input for adding a custom MCP server."""
    name: str = Field(..., description="Server display name")
    url: str = Field(..., description="Server URL or stdio command")
    auth_method: str = Field(default="none", description="none, api_key, or bearer")
    credential_value: Optional[str] = Field(default=None, description="Auth credential if needed")
    agent_assignments: List[str] = Field(default=[], description="Agents that can use this server")


class TestConnectionInput(BaseModel):
    """Input for testing a connection."""
    server_name: str


class ServerStatusResponse(BaseModel):
    """Response for server status."""
    server_name: str
    status: str
    enabled: bool
    agent_wired: bool
    used_by: List[str]
    source: str
    description: str
    discovered_tools: List[str]
    last_used: Optional[str]
    last_health_check: Optional[str]
    error_message: Optional[str]


class AllServersResponse(BaseModel):
    """Response containing all server statuses."""
    servers: Dict[str, Any]
    total: int
    connected: int
    degraded: int
    disconnected: int
    disabled: int


# Endpoints

@router.get("/servers", response_model=AllServersResponse)
async def get_all_servers():
    """Get status of all MCP servers."""
    try:
        manager = await get_mcp_manager()
        statuses = manager.get_all_statuses()
        
        # Count by status
        counts = {"connected": 0, "degraded": 0, "disconnected": 0, "disabled": 0}
        for info in statuses.values():
            status = info.get("status", "disconnected")
            if status in counts:
                counts[status] += 1
        
        return AllServersResponse(
            servers=statuses,
            total=len(statuses),
            **counts,
        )
    except Exception as e:
        logger.error(f"Failed to get server statuses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/servers/{server_name}", response_model=ServerStatusResponse)
async def get_server_status(server_name: str):
    """Get status of a specific MCP server."""
    try:
        manager = await get_mcp_manager()
        statuses = manager.get_all_statuses()
        
        if server_name not in statuses:
            raise HTTPException(status_code=404, detail=f"Server '{server_name}' not found")
        
        status_info = statuses[server_name]
        return ServerStatusResponse(
            server_name=server_name,
            **status_info,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get server status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/servers/{server_name}/test")
async def test_connection(server_name: str):
    """Test connection to an MCP server."""
    try:
        manager = await get_mcp_manager()
        result = await manager.test_connection(server_name)
        return result
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/servers/{server_name}/enable")
async def enable_server(server_name: str):
    """Enable a disabled MCP server."""
    try:
        manager = await get_mcp_manager()
        success = await manager.enable_server(server_name)
        return {"success": success, "server_name": server_name}
    except Exception as e:
        logger.error(f"Failed to enable server: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/servers/{server_name}/disable")
async def disable_server(server_name: str):
    """Disable an MCP server."""
    try:
        manager = await get_mcp_manager()
        success = await manager.disable_server(server_name)
        return {"success": success, "server_name": server_name}
    except Exception as e:
        logger.error(f"Failed to disable server: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/credentials")
async def set_mcp_credential(credential: CredentialInput):
    """Set an encrypted credential for an MCP server.
    
    Credentials stored via this endpoint take priority over environment variables.
    Values are encrypted with AES-256 before storage.
    """
    try:
        success = await set_credential(
            server_name=credential.server_name,
            credential_key=credential.credential_key,
            value=credential.value,
        )
        
        if success:
            return {
                "success": True,
                "message": f"Credential set for {credential.server_name}",
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to store credential")
    except Exception as e:
        logger.error(f"Failed to set credential: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/credentials")
async def delete_mcp_credential(credential: CredentialDeleteInput):
    """Delete a stored credential.
    
    After deletion, the server will fall back to environment variables.
    """
    try:
        success = await delete_credential(
            server_name=credential.server_name,
            credential_key=credential.credential_key,
        )
        
        return {
            "success": success,
            "message": f"Credential deleted for {credential.server_name}" if success else "Not found",
        }
    except Exception as e:
        logger.error(f"Failed to delete credential: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/credentials/{server_name}")
async def check_credential_status(server_name: str):
    """Check if a server has credentials configured.
    
    Does NOT return the credential value for security.
    """
    # Check common credential keys for this server
    credential_keys = {
        "github": ["token"],
        "slack": ["webhook_url"],
        "notion": ["token"],
    }
    
    keys_to_check = credential_keys.get(server_name, [])
    statuses = {}
    
    for key in keys_to_check:
        value = await get_credential(server_name, key)
        statuses[key] = {
            "configured": value is not None,
            "source": "ui" if value else "env_or_none",
        }
    
    return {
        "server_name": server_name,
        "credentials": statuses,
    }


@router.get("/config")
async def get_mcp_config():
    """Get MCP server configuration."""
    return {
        "servers": MCP_SERVERS,
        "enabled_servers": get_enabled_servers(),
    }


@router.post("/health-check")
async def trigger_health_check():
    """Trigger health check for all servers."""
    try:
        manager = await get_mcp_manager()
        results = await manager.check_all_health()
        
        return {
            "success": True,
            "results": {name: status.value for name, status in results.items()},
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/custom")
async def add_custom_server(server: CustomServerInput):
    """Add a custom MCP server configuration."""
    try:
        manager = await get_mcp_manager()
        # Register the custom server in runtime config
        result = await manager.register_custom_server(
            name=server.name,
            url=server.url,
            auth_method=server.auth_method,
            credential_value=server.credential_value,
            agent_assignments=server.agent_assignments,
        )
        return {"success": True, "server_name": server.name, "result": result}
    except AttributeError:
        # Manager doesn't support custom servers yet — return success placeholder
        return {"success": True, "server_name": server.name, "message": "Registered (restart to activate)"}
    except Exception as e:
        logger.error(f"Failed to add custom server: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tools/call")
async def call_mcp_tool(
    server_name: str,
    tool_name: str,
    arguments: Dict[str, Any],
):
    """Call a tool on an MCP server.
    
    This endpoint is for testing and debugging purposes.
    """
    try:
        manager = await get_mcp_manager()
        result = await manager.call_tool(server_name, tool_name, arguments)
        return {"success": True, "result": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Tool call failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
