import React, { useState, useEffect } from 'react';
import { MCPServerCard } from '../components/MCPServerCard';
import { CredentialModal } from '../components/CredentialModal';
import { AddCustomServerModal } from '../components/AddCustomServerModal';
import { RefreshCw, Plus, Server, CheckCircle, AlertTriangle, XCircle, HelpCircle } from 'lucide-react';

interface MCPServerStatus {
  status: 'connected' | 'degraded' | 'disconnected' | 'disabled';
  enabled: boolean;
  agent_wired: boolean;
  used_by: string[];
  source: string;
  description: string;
  discovered_tools: string[];
  last_used: string | null;
  last_health_check: string | null;
  error_message: string | null;
}

interface AllServersResponse {
  servers: Record<string, MCPServerStatus>;
  total: number;
  connected: number;
  degraded: number;
  disconnected: number;
  disabled: number;
}

// Servers that require authentication credentials
const SERVERS_REQUIRING_AUTH: Record<string, string> = {
  slack: 'webhook_url',
  notion: 'token',
  github: 'token',
};

const AVAILABLE_AGENTS = [
  'research',
  'architect',
  'delivery',
  'v0_codegen',
  'security',
  'qa',
  'deploy',
];

export function Settings() {
  const [servers, setServers] = useState<Record<string, MCPServerStatus>>({});
  const [stats, setStats] = useState({ total: 0, connected: 0, degraded: 0, disconnected: 0, disabled: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Modal states
  const [credentialModal, setCredentialModal] = useState<{
    isOpen: boolean;
    serverName: string;
    credentialKey: string;
  }>({ isOpen: false, serverName: '', credentialKey: '' });
  const [addServerModal, setAddServerModal] = useState(false);

  const API_BASE = '/api/mcp';

  // Fetch server statuses
  const fetchServers = async () => {
    try {
      const response = await fetch(`${API_BASE}/servers`);
      if (!response.ok) throw new Error('Failed to fetch servers');
      const data: AllServersResponse = await response.json();
      setServers(data.servers);
      setStats({
        total: data.total,
        connected: data.connected,
        degraded: data.degraded,
        disconnected: data.disconnected,
        disabled: data.disabled,
      });
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchServers();
    const interval = setInterval(fetchServers, 30000);
    return () => clearInterval(interval);
  }, []);

  // Test connection
  const testConnection = async (serverName: string) => {
    const response = await fetch(`${API_BASE}/servers/${serverName}/test`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error('Test failed');
    await fetchServers();
  };

  // Toggle server enabled/disabled
  const toggleServer = async (serverName: string, enabled: boolean) => {
    const endpoint = enabled ? 'enable' : 'disable';
    const response = await fetch(`${API_BASE}/servers/${serverName}/${endpoint}`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error(`Failed to ${endpoint} server`);
    await fetchServers();
  };

  // Save credential
  const saveCredential = async (serverName: string, credentialKey: string, value: string) => {
    const response = await fetch(`${API_BASE}/credentials`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        server_name: serverName,
        credential_key: credentialKey,
        value,
      }),
    });
    if (!response.ok) throw new Error('Failed to save credential');
    await fetchServers();
  };

  // Delete credential
  const deleteCredential = async (serverName: string, credentialKey: string) => {
    const response = await fetch(`${API_BASE}/credentials`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        server_name: serverName,
        credential_key: credentialKey,
      }),
    });
    if (!response.ok) throw new Error('Failed to delete credential');
    await fetchServers();
  };

  // Add custom server (placeholder)
  const addCustomServer = async (server: {
    name: string;
    url: string;
    authMethod: string;
    credentialValue?: string;
    agentAssignments: string[];
  }) => {
    console.log('Adding custom server:', server);
    throw new Error('Custom server support coming in future update');
  };

  // Trigger health check
  const triggerHealthCheck = async () => {
    setLoading(true);
    try {
      await fetch(`${API_BASE}/health-check`, { method: 'POST' });
      await fetchServers();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="mb-2">
        <h1 className="text-2xl lg:text-3xl font-bold" style={{ color: 'var(--text-primary)' }}>
          Settings
        </h1>
        <p className="mt-1" style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-base)' }}>
          Manage MCP server connections and credentials
        </p>
      </div>

      {/* MCP Servers Section */}
      <section>
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
          <div>
            <h2 className="text-lg font-semibold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
              <Server className="w-5 h-5" style={{ color: 'var(--accent-primary)' }} />
              MCP Servers
            </h2>
            <p style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-sm)' }}>
              Model Context Protocol servers powering agent capabilities
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={triggerHealthCheck}
              disabled={loading}
              className="btn-secondary flex items-center gap-2"
              style={{ padding: 'var(--space-2) var(--space-4)' }}
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button
              onClick={() => setAddServerModal(true)}
              className="btn-primary flex items-center gap-2"
              style={{ padding: 'var(--space-2) var(--space-4)' }}
            >
              <Plus className="w-4 h-4" />
              Add Server
            </button>
          </div>
        </div>

        {/* Status Summary - Bento Grid */}
        <div className="bento-grid mb-6">
          <div className="stat-card">
            <div className="stat-card-icon">
              <Server className="w-5 h-5" />
            </div>
            <div className="stat-card-value">{stats.total}</div>
            <div className="stat-card-label">Total Servers</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-icon" style={{ background: 'rgba(52, 211, 153, 0.15)' }}>
              <CheckCircle className="w-5 h-5" style={{ color: 'var(--accent-success)' }} />
            </div>
            <div className="stat-card-value" style={{ color: 'var(--accent-success)' }}>{stats.connected}</div>
            <div className="stat-card-label">Connected</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-icon" style={{ background: 'rgba(251, 191, 36, 0.15)' }}>
              <AlertTriangle className="w-5 h-5" style={{ color: 'var(--accent-warning)' }} />
            </div>
            <div className="stat-card-value" style={{ color: 'var(--accent-warning)' }}>{stats.degraded}</div>
            <div className="stat-card-label">Degraded</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-icon" style={{ background: 'rgba(248, 113, 113, 0.15)' }}>
              <XCircle className="w-5 h-5" style={{ color: 'var(--accent-error)' }} />
            </div>
            <div className="stat-card-value" style={{ color: 'var(--accent-error)' }}>{stats.disconnected}</div>
            <div className="stat-card-label">Disconnected</div>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="glass-card mb-4" style={{ 
            background: 'rgba(248, 113, 113, 0.1)', 
            borderColor: 'rgba(248, 113, 113, 0.3)' 
          }}>
            <p style={{ color: 'var(--accent-error)' }}>{error}</p>
          </div>
        )}

        {/* Loading State */}
        {loading && Object.keys(servers).length === 0 ? (
          <div className="glass-card text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 mx-auto mb-3" 
                 style={{ border: '2px solid var(--glass-border)', borderTopColor: 'var(--accent-primary)' }} />
            <p style={{ color: 'var(--text-secondary)' }}>Loading servers...</p>
          </div>
        ) : (
          /* Server Grid */
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(servers).map(([name, server]) => (
              <MCPServerCard
                key={name}
                name={name}
                status={server.status}
                enabled={server.enabled}
                agentWired={server.agent_wired}
                usedBy={server.used_by}
                source={server.source}
                description={server.description}
                discoveredTools={server.discovered_tools}
                lastUsed={server.last_used}
                lastHealthCheck={server.last_health_check}
                errorMessage={server.error_message}
                onTest={() => testConnection(name)}
                onToggle={(enabled) => toggleServer(name, enabled)}
                requiresAuth={name in SERVERS_REQUIRING_AUTH}
                onConfigureCredentials={
                  name in SERVERS_REQUIRING_AUTH
                    ? () =>
                        setCredentialModal({
                          isOpen: true,
                          serverName: name,
                          credentialKey: SERVERS_REQUIRING_AUTH[name],
                        })
                    : undefined
                }
              />
            ))}
          </div>
        )}
      </section>

      {/* Documentation Link */}
      <section className="glass-card" style={{ 
        background: 'rgba(91, 158, 244, 0.08)',
        borderColor: 'rgba(91, 158, 244, 0.2)'
      }}>
        <div className="flex items-start gap-3">
          <HelpCircle className="w-5 h-5 mt-0.5" style={{ color: 'var(--accent-secondary)' }} />
          <div>
            <h3 className="font-medium mb-1" style={{ color: 'var(--accent-secondary)' }}>
              Need help?
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
              MCP servers extend agent capabilities with external tools. Configure credentials via
              environment variables (.env) or through this UI. UI credentials take priority.
            </p>
          </div>
        </div>
      </section>

      {/* Modals */}
      <CredentialModal
        isOpen={credentialModal.isOpen}
        onClose={() => setCredentialModal({ isOpen: false, serverName: '', credentialKey: '' })}
        serverName={credentialModal.serverName}
        credentialKey={credentialModal.credentialKey}
        onSave={(value) =>
          saveCredential(credentialModal.serverName, credentialModal.credentialKey, value)
        }
        onDelete={() =>
          deleteCredential(credentialModal.serverName, credentialModal.credentialKey)
        }
      />

      <AddCustomServerModal
        isOpen={addServerModal}
        onClose={() => setAddServerModal(false)}
        onAdd={addCustomServer}
        availableAgents={AVAILABLE_AGENTS}
      />
    </div>
  );
}

export default Settings;
