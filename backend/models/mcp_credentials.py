"""Database models for encrypted MCP credentials."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class MCPCredential(Base):
    """Encrypted storage for MCP server credentials.
    
    Credentials stored here take priority over environment variables.
    Values are encrypted with AES-256 before storage.
    """
    
    __tablename__ = "mcp_credentials"
    
    id = Column(String(64), primary_key=True)  # SHA-256 hash of server:key
    server_name = Column(String(100), nullable=False, index=True)
    credential_key = Column(String(100), nullable=False)
    encrypted_value = Column(Text, nullable=False)  # AES-256 encrypted
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<MCPCredential server={self.server_name} key={self.credential_key}>"


class MCPServerStatus(Base):
    """Track MCP server connection status and metadata."""
    
    __tablename__ = "mcp_server_status"
    
    server_name = Column(String(100), primary_key=True)
    status = Column(String(20), default="disconnected")  # connected, degraded, disconnected, disabled
    last_health_check = Column(DateTime, nullable=True)
    last_used = Column(DateTime, nullable=True)
    discovered_tools = Column(Text, nullable=True)  # JSON array of tool names
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<MCPServerStatus server={self.server_name} status={self.status}>"


class CustomMCPServer(Base):
    """User-defined custom MCP servers."""
    
    __tablename__ = "custom_mcp_servers"
    
    id = Column(String(64), primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    url = Column(String(500), nullable=False)
    auth_method = Column(String(50), default="none")  # none, api_key, bearer
    enabled = Column(String(5), default="true")  # Use string to avoid SQLAlchemy Boolean issues
    agent_assignments = Column(Text, nullable=True)  # JSON array of agent names
    discovered_tools = Column(Text, nullable=True)  # JSON array of tool names
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<CustomMCPServer name={self.name}>"
