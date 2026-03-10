import React, { useState, useEffect } from 'react';
import { MCPServerCard } from '../components/MCPServerCard';
import { CredentialModal } from '../components/CredentialModal';
import { AddCustomServerModal } from '../components/AddCustomServerModal';

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
    // Refresh every 30 seconds
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

  // Add custom server (placeholder - would need backend implementation)
  const addCustomServer = async (server: {
    name: string;
    url: string;
    authMethod: string;
    credentialValue?: string;
    agentAssignments: string[];
  }) => {
    // This would call a backend endpoint to add custom servers
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
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Settings
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Manage MCP server connections and credentials
          </p>
        </div>

        {/* MCP Servers Section */}
        <section className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                MCP Servers
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Model Context Protocol servers powering agent capabilities
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={triggerHealthCheck}
                disabled={loading}
                className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 text-sm rounded hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
              >
                Refresh Status
              </button>
              <button
                onClick={() => setAddServerModal(true)}
                className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
              >
                + Add Custom Server
              </button>
            </div>
          </div>

          {/* Status Summary */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
              <div className="text-2xl font-bold text-gray-900 dark:text-white">{stats.total}</div>
              <div className="text-sm text-gray-500">Total Servers</div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-green-200 dark:border-green-800">
              <div className="text-2xl font-bold text-green-600">{stats.connected}</div>
              <div className="text-sm text-gray-500">Connected</div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-yellow-200 dark:border-yellow-800">
              <div className="text-2xl font-bold text-yellow-600">{stats.degraded}</div>
              <div className="text-sm text-gray-500">Degraded</div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-red-200 dark:border-red-800">
              <div className="text-2xl font-bold text-red-600">{stats.disconnected}</div>
              <div className="text-sm text-gray-500">Disconnected</div>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg">
              {error}
            </div>
          )}

          {/* Loading State */}
          {loading && Object.keys(servers).length === 0 ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-2 text-gray-500">Loading servers...</p>
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
        <section className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
          <h3 className="font-medium text-blue-900 dark:text-blue-100 mb-1">
            Need help?
          </h3>
          <p className="text-sm text-blue-700 dark:text-blue-300">
            MCP servers extend agent capabilities with external tools. Configure credentials via
            environment variables (.env) or through this UI. UI credentials take priority.
          </p>
        </section>
      </div>

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
