-- MCP Credentials Migration
-- Creates tables for encrypted credential storage and MCP server management

-- Table for storing encrypted MCP server credentials
CREATE TABLE IF NOT EXISTS mcp_credentials (
    id VARCHAR(64) PRIMARY KEY,  -- SHA-256 hash of server:key
    server_name VARCHAR(100) NOT NULL,
    credential_key VARCHAR(100) NOT NULL,
    encrypted_value TEXT NOT NULL,  -- AES-256 encrypted value
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Index for faster lookups by server name
CREATE INDEX IF NOT EXISTS idx_mcp_credentials_server ON mcp_credentials(server_name);

-- Table for tracking MCP server status
CREATE TABLE IF NOT EXISTS mcp_server_status (
    server_name VARCHAR(100) PRIMARY KEY,
    status VARCHAR(20) DEFAULT 'disconnected',  -- connected, degraded, disconnected, disabled
    last_health_check TIMESTAMP,
    last_used TIMESTAMP,
    discovered_tools TEXT,  -- JSON array of tool names
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Table for custom MCP servers added via UI
CREATE TABLE IF NOT EXISTS custom_mcp_servers (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    url VARCHAR(500) NOT NULL,
    auth_method VARCHAR(50) DEFAULT 'none',  -- none, api_key, bearer
    enabled VARCHAR(5) DEFAULT 'true',
    agent_assignments TEXT,  -- JSON array of agent names
    discovered_tools TEXT,  -- JSON array of tool names
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for auto-updating timestamps
DROP TRIGGER IF EXISTS update_mcp_credentials_updated_at ON mcp_credentials;
CREATE TRIGGER update_mcp_credentials_updated_at
    BEFORE UPDATE ON mcp_credentials
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_mcp_server_status_updated_at ON mcp_server_status;
CREATE TRIGGER update_mcp_server_status_updated_at
    BEFORE UPDATE ON mcp_server_status
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_custom_mcp_servers_updated_at ON custom_mcp_servers;
CREATE TRIGGER update_custom_mcp_servers_updated_at
    BEFORE UPDATE ON custom_mcp_servers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
