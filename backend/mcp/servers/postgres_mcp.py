"""PostgreSQL MCP Server wrapper.

Provides read-only database access for querying project data.
"""

import logging
from typing import Any, Dict, List, Optional
import asyncpg

from mcp.manager import MCPServerBase, ServerStatus
from config.settings import get_settings

logger = logging.getLogger(__name__)

# Disallowed keywords for read-only enforcement
WRITE_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
    "TRUNCATE", "GRANT", "REVOKE", "VACUUM", "REINDEX",
]


class PostgresMCPServer(MCPServerBase):
    """MCP server for PostgreSQL read-only operations.
    
    Used by: Intake, Delivery agents.
    Enforces read-only access to prevent data modification.
    """
    
    name = "postgres"
    
    def __init__(self):
        super().__init__()
        self._pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> bool:
        """Initialize PostgreSQL connection pool."""
        try:
            settings = get_settings()
            
            self._pool = await asyncpg.create_pool(
                settings.database_url,
                min_size=1,
                max_size=5,
                command_timeout=30,
            )
            
            # Test connection
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            
            self.status = ServerStatus.CONNECTED
            logger.info("PostgreSQL MCP connected (read-only mode)")
            return True
            
        except Exception as e:
            self.error_message = str(e)
            logger.error(f"PostgreSQL MCP connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Close PostgreSQL connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
        self.status = ServerStatus.DISCONNECTED
    
    async def health_check(self) -> ServerStatus:
        """Check database connectivity."""
        if not self._pool:
            return ServerStatus.DISCONNECTED
        
        try:
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return ServerStatus.CONNECTED
        except Exception:
            return ServerStatus.DEGRADED
    
    async def discover_tools(self) -> List[str]:
        """Return available PostgreSQL tools."""
        self.discovered_tools = [
            "query",
            "list_tables",
            "describe_table",
            "get_table_schema",
        ]
        return self.discovered_tools
    
    def _is_read_only(self, sql: str) -> bool:
        """Check if SQL query is read-only."""
        sql_upper = sql.upper().strip()
        
        # Check for write operations
        for keyword in WRITE_KEYWORDS:
            if keyword in sql_upper:
                return False
        
        # Must start with SELECT, WITH, or EXPLAIN
        if not any(sql_upper.startswith(k) for k in ["SELECT", "WITH", "EXPLAIN"]):
            return False
        
        return True
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a PostgreSQL tool."""
        self._update_last_used()
        
        if not self._pool:
            raise RuntimeError("PostgreSQL not connected")
        
        tool_map = {
            "query": self.query,
            "list_tables": self.list_tables,
            "describe_table": self.describe_table,
            "get_table_schema": self.get_table_schema,
        }
        
        handler = tool_map.get(tool_name)
        if not handler:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        return await handler(**arguments)
    
    async def query(
        self, sql: str, params: Optional[List] = None, limit: int = 100
    ) -> Dict[str, Any]:
        """Execute a read-only SQL query."""
        if not self._is_read_only(sql):
            return {
                "success": False,
                "error": "Only read-only queries (SELECT) are allowed",
            }
        
        # Add LIMIT if not present
        sql_upper = sql.upper()
        if "LIMIT" not in sql_upper:
            sql = f"{sql.rstrip(';')} LIMIT {limit}"
        
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(sql, *(params or []))
                return {
                    "success": True,
                    "rows": [dict(row) for row in rows],
                    "count": len(rows),
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def list_tables(self, schema: str = "public") -> Dict[str, Any]:
        """List all tables in a schema."""
        sql = """
            SELECT table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = $1
            ORDER BY table_name
        """
        
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(sql, schema)
                return {
                    "success": True,
                    "tables": [dict(row) for row in rows],
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def describe_table(
        self, table_name: str, schema: str = "public"
    ) -> Dict[str, Any]:
        """Get table column information."""
        sql = """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = $1 AND table_name = $2
            ORDER BY ordinal_position
        """
        
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(sql, schema, table_name)
                return {
                    "success": True,
                    "table": table_name,
                    "columns": [dict(row) for row in rows],
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_table_schema(
        self, table_name: str, schema: str = "public"
    ) -> Dict[str, Any]:
        """Get full table schema including constraints."""
        columns = await self.describe_table(table_name, schema)
        if not columns.get("success"):
            return columns
        
        # Get constraints
        constraint_sql = """
            SELECT
                tc.constraint_name,
                tc.constraint_type,
                kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_schema = $1 AND tc.table_name = $2
        """
        
        try:
            async with self._pool.acquire() as conn:
                constraint_rows = await conn.fetch(constraint_sql, schema, table_name)
                return {
                    "success": True,
                    "table": table_name,
                    "schema": schema,
                    "columns": columns["columns"],
                    "constraints": [dict(row) for row in constraint_rows],
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
