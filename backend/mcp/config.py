"""MCP Server configuration."""

from typing import Dict, List, Any

MCP_SERVERS: Dict[str, Dict[str, Any]] = {
    "filesystem": {
        "enabled": True,
        "source": "@modelcontextprotocol/server-filesystem",
        "config": {"allowed_paths": ["/tmp/projects", "/app/projects"]},
        "used_by": ["architect", "v0_codegen", "security"],
        "agent_wired": True,  # Wired to architect in Phase 3
        "description": "File system operations for project management",
    },
    "browser": {
        "enabled": True,
        "source": "@anthropic/mcp-server-puppeteer",
        "config": {"server_url": "http://mcp-browser:3000"},
        "used_by": ["research", "qa"],
        "agent_wired": True,  # Wired to research in Phase 3
        "description": "Browser automation via Puppeteer for web scraping",
    },
    "github": {
        "enabled": True,
        "source": "@modelcontextprotocol/server-github",
        "config": {},
        "used_by": ["v0_codegen", "deploy", "deliver"],
        "agent_wired": True,  # Wired to delivery in Phase 3
        "description": "GitHub repository operations",
    },
    "fetch": {
        "enabled": True,
        "source": "@modelcontextprotocol/server-fetch",
        "config": {},
        "used_by": ["research", "deploy", "analytics", "qa"],
        "agent_wired": True,  # Wired to research in Phase 3
        "description": "HTTP client for API calls and data fetching",
    },
    "postgres": {
        "enabled": True,
        "source": "@modelcontextprotocol/server-postgres",
        "config": {"access": "read-only"},
        "used_by": ["intake", "deliver"],
        "agent_wired": False,  # Server built, agent wiring in Phase 5/6
        "description": "Read-only PostgreSQL database access",
    },
    "slack": {
        "enabled": True,
        "source": "@modelcontextprotocol/server-slack",
        "config": {},
        "used_by": ["deliver", "deploy"],
        "agent_wired": False,  # Server built, agent wiring in Phase 5
        "description": "Slack notifications via webhook",
    },
    "notion": {
        "enabled": True,
        "source": "notion-mcp-server",
        "config": {},
        "used_by": ["deliver", "coding_standards"],
        "agent_wired": False,  # Server built, agent wiring in Phase 6
        "description": "Notion API for documentation management",
    },
    "memory": {
        "enabled": True,
        "source": "@modelcontextprotocol/server-memory",
        "config": {},
        "used_by": ["research", "architect", "design_system", "qa"],
        "agent_wired": False,  # Server built, agent wiring in Phase 7
        "description": "Redis-backed persistent memory storage",
    },
}


def get_server_config(server_name: str) -> Dict[str, Any]:
    """Get configuration for a specific MCP server."""
    return MCP_SERVERS.get(server_name, {})


def get_enabled_servers() -> List[str]:
    """Get list of enabled MCP servers."""
    return [name for name, config in MCP_SERVERS.items() if config.get("enabled", False)]


def get_wired_servers() -> List[str]:
    """Get list of servers currently wired to agents."""
    return [name for name, config in MCP_SERVERS.items() if config.get("agent_wired", False)]
