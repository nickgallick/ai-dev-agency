import React, { useState, useEffect, useRef } from 'react';
import { MCPServerCard } from '../components/MCPServerCard';
import { CredentialModal } from '../components/CredentialModal';
import { AddCustomServerModal } from '../components/AddCustomServerModal';
import { useTheme, ThemeMode } from '../contexts/ThemeContext';
import { 
  RefreshCw, Plus, Server, CheckCircle, AlertTriangle, XCircle, HelpCircle,
  Figma, Globe, Mail, HardDrive, Zap, Settings2, ExternalLink,
  Monitor, Sun, Moon, Palette
} from 'lucide-react';

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

// Phase 10: Integration configuration
interface IntegrationStatus {
  name: string;
  configured: boolean;
  description: string;
  category: string;
  required_vars: string[];
}

interface IntegrationsResponse {
  integrations: Record<string, IntegrationStatus>;
  agency_system_count: number;
  generated_project_count: number;
  total_configured: number;
}

// Integration card metadata
const INTEGRATION_META: Record<string, { icon: any; docsUrl: string; color: string }> = {
  figma: { 
    icon: Figma, 
    docsUrl: 'https://www.figma.com/developers/api',
    color: 'var(--accent-primary)'
  },
  browserstack: { 
    icon: Globe, 
    docsUrl: 'https://www.browserstack.com/docs/automate/api-reference/selenium/introduction',
    color: 'var(--accent-secondary)'
  },
  resend: { 
    icon: Mail, 
    docsUrl: 'https://resend.com/docs',
    color: '#00D4AA'
  },
  r2: { 
    icon: HardDrive, 
    docsUrl: 'https://developers.cloudflare.com/r2/',
    color: '#F6821F'
  },
  inngest: { 
    icon: Zap, 
    docsUrl: 'https://www.inngest.com/docs',
    color: '#6366F1'
  },
};

// Theme toggle component with sliding pill animation
function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const containerRef = useRef<HTMLDivElement>(null);
  const [pillStyle, setPillStyle] = useState({ left: 0, width: 0 });

  const options: { value: ThemeMode; label: string; icon: typeof Monitor }[] = [
    { value: 'system', label: 'System', icon: Monitor },
    { value: 'light', label: 'Light', icon: Sun },
    { value: 'dark', label: 'Dark', icon: Moon },
  ];

  // Update pill position when theme changes
  useEffect(() => {
    if (!containerRef.current) return;
    const activeIndex = options.findIndex(opt => opt.value === theme);
    const buttons = containerRef.current.querySelectorAll('.theme-toggle-option');
    const activeButton = buttons[activeIndex] as HTMLElement;
    
    if (activeButton) {
      setPillStyle({
        left: activeButton.offsetLeft,
        width: activeButton.offsetWidth,
      });
    }
  }, [theme]);

  return (
    <div 
      ref={containerRef}
      className="theme-toggle"
      style={{ position: 'relative' }}
    >
      {/* Sliding pill */}
      <div
        className="theme-toggle-pill"
        style={{
          left: pillStyle.left,
          width: pillStyle.width,
        }}
      />
      
      {/* Options */}
      {options.map(({ value, label, icon: Icon }) => (
        <button
          key={value}
          onClick={() => setTheme(value)}
          className={`theme-toggle-option ${theme === value ? 'active' : ''}`}
        >
          <Icon className="w-4 h-4" />
          <span>{label}</span>
        </button>
      ))}
    </div>
  );
}

export function Settings() {
  const { theme, resolvedTheme } = useTheme();
  const [servers, setServers] = useState<Record<string, MCPServerStatus>>({});
  const [stats, setStats] = useState({ total: 0, connected: 0, degraded: 0, disconnected: 0, disabled: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Phase 10: Integration state
  const [integrations, setIntegrations] = useState<Record<string, IntegrationStatus>>({});
  const [integrationsLoading, setIntegrationsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'appearance' | 'mcp' | 'integrations'>('appearance');
  
  // Modal states
  const [credentialModal, setCredentialModal] = useState<{
    isOpen: boolean;
    serverName: string;
    credentialKey: string;
  }>({ isOpen: false, serverName: '', credentialKey: '' });
  const [addServerModal, setAddServerModal] = useState(false);

  const API_BASE = '/api/mcp';
  const INTEGRATIONS_API = '/api/integrations';

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

  // Fetch integrations status
  const fetchIntegrations = async () => {
    try {
      const response = await fetch(`${INTEGRATIONS_API}/status`);
      if (!response.ok) throw new Error('Failed to fetch integrations');
      const data: IntegrationsResponse = await response.json();
      setIntegrations(data.integrations);
    } catch (err: any) {
      console.error('Failed to fetch integrations:', err);
    } finally {
      setIntegrationsLoading(false);
    }
  };

  useEffect(() => {
    fetchServers();
    fetchIntegrations();
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

  // Render integration card
  const renderIntegrationCard = (key: string, integration: IntegrationStatus) => {
    const meta = INTEGRATION_META[key] || { icon: Settings2, docsUrl: '#', color: 'var(--text-secondary)' };
    const Icon = meta.icon;
    
    return (
      <div 
        key={key}
        className="glass-card"
        style={{
          borderColor: integration.configured ? `${meta.color}40` : undefined,
          background: integration.configured ? `${meta.color}08` : undefined,
        }}
      >
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div 
              className="p-2 rounded-lg"
              style={{ background: `${meta.color}15` }}
            >
              <Icon className="w-5 h-5" style={{ color: meta.color }} />
            </div>
            <div>
              <h4 className="font-medium" style={{ color: 'var(--text-primary)' }}>
                {integration.name}
              </h4>
              <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                {integration.category === 'agency_system' ? 'Agency System' : 'Generated Project'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {integration.configured ? (
              <span className="badge badge-success">Configured</span>
            ) : (
              <span className="badge badge-neutral">Not Configured</span>
            )}
          </div>
        </div>
        
        <p className="text-sm mb-3" style={{ color: 'var(--text-secondary)' }}>
          {integration.description}
        </p>
        
        <div className="flex items-center justify-between">
          <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
            Required: {integration.required_vars.join(', ')}
          </div>
          <a 
            href={meta.docsUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs"
            style={{ color: meta.color }}
          >
            Docs <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="mb-2">
        <h1 className="text-2xl lg:text-3xl font-bold" style={{ color: 'var(--text-primary)' }}>
          Settings
        </h1>
        <p className="mt-1" style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-base)' }}>
          Manage integrations and MCP server connections
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-2 mb-6 flex-wrap">
        <button
          onClick={() => setActiveTab('appearance')}
          className={`px-4 py-2 rounded-lg font-medium text-sm transition-all ${
            activeTab === 'appearance' 
              ? 'bg-gradient-to-r from-[var(--accent-primary)] to-[var(--accent-secondary)] text-white'
              : 'glass-card'
          }`}
          style={activeTab !== 'appearance' ? { color: 'var(--text-secondary)' } : {}}
        >
          <Palette className="w-4 h-4 inline-block mr-2" />
          Appearance
        </button>
        <button
          onClick={() => setActiveTab('integrations')}
          className={`px-4 py-2 rounded-lg font-medium text-sm transition-all ${
            activeTab === 'integrations' 
              ? 'bg-gradient-to-r from-[var(--accent-primary)] to-[var(--accent-secondary)] text-white'
              : 'glass-card'
          }`}
          style={activeTab !== 'integrations' ? { color: 'var(--text-secondary)' } : {}}
        >
          <Settings2 className="w-4 h-4 inline-block mr-2" />
          Integrations
        </button>
        <button
          onClick={() => setActiveTab('mcp')}
          className={`px-4 py-2 rounded-lg font-medium text-sm transition-all ${
            activeTab === 'mcp' 
              ? 'bg-gradient-to-r from-[var(--accent-primary)] to-[var(--accent-secondary)] text-white'
              : 'glass-card'
          }`}
          style={activeTab !== 'mcp' ? { color: 'var(--text-secondary)' } : {}}
        >
          <Server className="w-4 h-4 inline-block mr-2" />
          MCP Servers
        </button>
      </div>

      {/* Appearance Tab */}
      {activeTab === 'appearance' && (
        <div className="space-y-6">
          {/* Theme Section */}
          <section className="glass-card">
            <div className="mb-4">
              <h2 className="text-lg font-semibold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                <Palette className="w-5 h-5" style={{ color: 'var(--accent-primary)' }} />
                Theme
              </h2>
              <p style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-sm)' }}>
                Choose how AI Dev Agency looks to you
              </p>
            </div>
            
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
                  {theme === 'system' 
                    ? `System preference (currently ${resolvedTheme})`
                    : theme === 'light'
                    ? 'Light mode - frosted daylight glass'
                    : 'Dark mode - deep space glass'
                  }
                </p>
              </div>
              <ThemeToggle />
            </div>
          </section>

          {/* Theme Preview */}
          <section>
            <h3 className="text-base font-medium mb-3" style={{ color: 'var(--text-primary)' }}>
              Preview
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* Sample Glass Card */}
              <div className="glass-card">
                <div className="flex items-center gap-3 mb-3">
                  <div 
                    className="w-10 h-10 rounded-lg flex items-center justify-center"
                    style={{ background: 'var(--glass-bg-elevated)' }}
                  >
                    <Sun className="w-5 h-5" style={{ color: 'var(--accent-primary)' }} />
                  </div>
                  <div>
                    <p className="font-medium" style={{ color: 'var(--text-primary)' }}>Glass Card</p>
                    <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Translucent surface</p>
                  </div>
                </div>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                  Frosted glass with subtle bloom effects
                </p>
              </div>

              {/* Sample Stat Card */}
              <div className="stat-card">
                <div className="stat-card-icon">
                  <Zap className="w-5 h-5" />
                </div>
                <div className="stat-card-value">42</div>
                <div className="stat-card-label">Sample Metric</div>
                <div className="stat-card-change positive">+12.5%</div>
              </div>

              {/* Sample Badges */}
              <div className="glass-card">
                <p className="font-medium mb-3" style={{ color: 'var(--text-primary)' }}>Status Badges</p>
                <div className="flex flex-wrap gap-2">
                  <span className="badge badge-success">Success</span>
                  <span className="badge badge-running">Running</span>
                  <span className="badge badge-warning">Warning</span>
                  <span className="badge badge-error">Error</span>
                  <span className="badge badge-default">Default</span>
                </div>
              </div>
            </div>
          </section>

          {/* Design Philosophy */}
          <section className="glass-card" style={{ 
            background: `var(--gradient-cool)`,
            borderColor: 'rgba(91, 158, 244, 0.2)'
          }}>
            <div className="flex items-start gap-3">
              <Moon className="w-5 h-5 mt-0.5" style={{ color: 'var(--accent-secondary)' }} />
              <div>
                <h3 className="font-medium mb-1" style={{ color: 'var(--text-primary)' }}>
                  Glassmorphic Design
                </h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
                  {resolvedTheme === 'dark' 
                    ? 'Dark mode features deep space backgrounds with luminous glass panels catching ethereal light blooms. Inspired by premium dashboard interfaces.'
                    : 'Light mode feels like a clean modern office with floor-to-ceiling windows - bright, airy, with glass panels catching daylight. Same premium quality, inverted for daylight use.'
                  }
                </p>
              </div>
            </div>
          </section>
        </div>
      )}

      {/* Integrations Tab */}
      {activeTab === 'integrations' && (
        <div className="space-y-6">
          {/* Agency System Integrations */}
          <section>
            <div className="mb-4">
              <h2 className="text-lg font-semibold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                <Zap className="w-5 h-5" style={{ color: 'var(--accent-primary)' }} />
                Agency System Integrations
              </h2>
              <p style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-sm)' }}>
                Used by agents during project generation
              </p>
            </div>
            
            {integrationsLoading ? (
              <div className="glass-card text-center py-8">
                <div className="animate-spin rounded-full h-6 w-6 mx-auto mb-2" 
                     style={{ border: '2px solid var(--glass-border)', borderTopColor: 'var(--accent-primary)' }} />
                <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>Loading...</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(integrations)
                  .filter(([_, i]) => i.category === 'agency_system')
                  .map(([key, integration]) => renderIntegrationCard(key, integration))}
              </div>
            )}
          </section>

          {/* Generated Project Defaults */}
          <section>
            <div className="mb-4">
              <h2 className="text-lg font-semibold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                <HardDrive className="w-5 h-5" style={{ color: 'var(--accent-secondary)' }} />
                Generated Project Defaults
              </h2>
              <p style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-sm)' }}>
                Auto-injected into generated SaaS projects when applicable
              </p>
            </div>
            
            {integrationsLoading ? (
              <div className="glass-card text-center py-8">
                <div className="animate-spin rounded-full h-6 w-6 mx-auto mb-2" 
                     style={{ border: '2px solid var(--glass-border)', borderTopColor: 'var(--accent-primary)' }} />
                <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>Loading...</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(integrations)
                  .filter(([_, i]) => i.category === 'generated_project')
                  .map(([key, integration]) => renderIntegrationCard(key, integration))}
              </div>
            )}
          </section>

          {/* Configuration Instructions */}
          <section className="glass-card" style={{ 
            background: 'rgba(91, 158, 244, 0.08)',
            borderColor: 'rgba(91, 158, 244, 0.2)'
          }}>
            <div className="flex items-start gap-3">
              <HelpCircle className="w-5 h-5 mt-0.5" style={{ color: 'var(--accent-secondary)' }} />
              <div>
                <h3 className="font-medium mb-1" style={{ color: 'var(--accent-secondary)' }}>
                  Configuration
                </h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
                  Configure integrations via environment variables in your <code>.env</code> file. 
                  Agency System integrations enhance the build process, while Generated Project Defaults 
                  are automatically added to applicable projects (e.g., Resend for auth, R2 for uploads).
                </p>
              </div>
            </div>
          </section>
        </div>
      )}

      {/* MCP Servers Tab */}
      {activeTab === 'mcp' && (
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
      </section>
      )}

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
