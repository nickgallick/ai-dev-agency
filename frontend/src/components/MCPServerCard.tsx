import React, { useState } from 'react';
import { ChevronRight, CheckCircle, AlertTriangle, XCircle, Power, Zap, Clock, Key } from 'lucide-react';

interface MCPServerCardProps {
  name: string;
  status: 'connected' | 'degraded' | 'disconnected' | 'disabled';
  enabled: boolean;
  agentWired: boolean;
  usedBy: string[];
  source: string;
  description: string;
  discoveredTools: string[];
  lastUsed: string | null;
  lastHealthCheck: string | null;
  errorMessage: string | null;
  onTest: () => Promise<void>;
  onToggle: (enabled: boolean) => Promise<void>;
  onConfigureCredentials?: () => void;
  requiresAuth?: boolean;
}

const statusConfig = {
  connected: {
    icon: CheckCircle,
    color: 'var(--accent-success)',
    bg: 'var(--accent-success-bg, rgba(52,211,153,0.15))',
    label: 'Connected'
  },
  degraded: {
    icon: AlertTriangle,
    color: 'var(--accent-warning)',
    bg: 'var(--accent-warning-bg, rgba(251,191,36,0.15))',
    label: 'Degraded'
  },
  disconnected: {
    icon: XCircle,
    color: 'var(--accent-error)',
    bg: 'var(--accent-error-bg, rgba(248,113,113,0.15))',
    label: 'Disconnected'
  },
  disabled: {
    icon: Power,
    color: 'var(--text-tertiary)',
    bg: 'var(--glass-bg)',
    label: 'Disabled'
  },
};

export function MCPServerCard({
  name,
  status,
  enabled,
  agentWired,
  usedBy,
  source,
  description,
  discoveredTools,
  lastUsed,
  lastHealthCheck,
  errorMessage,
  onTest,
  onToggle,
  onConfigureCredentials,
  requiresAuth = false,
}: MCPServerCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; latency?: number } | null>(null);

  const handleTest = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      await onTest();
      setTestResult({ success: true });
    } catch (error) {
      setTestResult({ success: false });
    } finally {
      setIsTesting(false);
    }
  };

  const formatTimestamp = (ts: string | null) => {
    if (!ts) return 'Never';
    return new Date(ts).toLocaleString();
  };

  const StatusIcon = statusConfig[status].icon;

  return (
    <div className="glass-card" style={{ padding: 'var(--space-4)' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div 
            className="w-10 h-10 rounded-lg flex items-center justify-center"
            style={{ background: statusConfig[status].bg }}
          >
            <StatusIcon className="w-5 h-5" style={{ color: statusConfig[status].color }} />
          </div>
          <div>
            <h3 className="font-semibold capitalize" style={{ color: 'var(--text-primary)' }}>
              {name}
            </h3>
            <p className="font-mono" style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-xs)' }}>
              {source}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {agentWired && (
            <span className="badge badge-success flex items-center gap-1">
              <Zap className="w-3 h-3" />
              Active
            </span>
          )}
          {/* Toggle Switch */}
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => onToggle(e.target.checked)}
              className="sr-only peer"
            />
            <div 
              className="w-10 h-6 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[3px] after:left-[3px] after:rounded-full after:h-[18px] after:w-[18px] after:transition-all"
              style={{
                background: enabled ? 'var(--accent-primary)' : 'var(--bg-tertiary)',
              }}
            >
              <span 
                className="absolute top-[3px] rounded-full w-[18px] h-[18px] transition-all"
                style={{
                  background: 'white',
                  left: enabled ? 'calc(100% - 21px)' : '3px'
                }}
              />
            </div>
          </label>
        </div>
      </div>

      {/* Description */}
      <p className="mb-3" style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
        {description}
      </p>

      {/* Agent Pills */}
      <div className="flex flex-wrap gap-1 mb-3">
        {usedBy.map((agent) => (
          <span key={agent} className="badge badge-info">
            {agent}
          </span>
        ))}
      </div>

      {/* Error Message */}
      {errorMessage && (
        <div 
          className="glass-card mb-3 bg-accent-error/10 border-accent-error/30"
          style={{ padding: 'var(--space-3)' }}
        >
          <p style={{ color: 'var(--accent-error)', fontSize: 'var(--text-sm)' }}>{errorMessage}</p>
        </div>
      )}

      {/* Expandable Tools Section */}
      <div className="pt-3" style={{ borderTop: '1px solid var(--glass-border)' }}>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 w-full text-left"
          style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}
        >
          <ChevronRight 
            className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
          />
          {discoveredTools.length} tools available
        </button>

        {isExpanded && (
          <div className="mt-3 ml-6">
            <div className="flex flex-wrap gap-1">
              {discoveredTools.map((tool) => (
                <code
                  key={tool}
                  className="font-mono"
                  style={{ 
                    padding: 'var(--space-1) var(--space-2)',
                    background: 'var(--glass-bg-elevated)',
                    borderRadius: 'var(--radius-sm)',
                    color: 'var(--text-secondary)',
                    fontSize: 'var(--text-xs)'
                  }}
                >
                  {tool}
                </code>
              ))}
            </div>
            <div className="mt-3 flex items-center gap-4" style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-xs)' }}>
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                Last used: {formatTimestamp(lastUsed)}
              </span>
              <span className="flex items-center gap-1">
                <CheckCircle className="w-3 h-3" />
                Health: {formatTimestamp(lastHealthCheck)}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-2 mt-3 pt-3" style={{ borderTop: '1px solid var(--glass-border)' }}>
        <button
          onClick={handleTest}
          disabled={isTesting}
          className="btn-primary flex items-center gap-2"
          style={{ padding: 'var(--space-2) var(--space-4)', fontSize: 'var(--text-sm)' }}
        >
          {isTesting ? (
            <>
              <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Testing...
            </>
          ) : (
            'Test Connection'
          )}
        </button>
        {requiresAuth && onConfigureCredentials && (
          <button
            onClick={onConfigureCredentials}
            className="btn-secondary flex items-center gap-2"
            style={{ padding: 'var(--space-2) var(--space-4)', fontSize: 'var(--text-sm)' }}
          >
            <Key className="w-4 h-4" />
            Configure Auth
          </button>
        )}
      </div>

      {/* Test Result */}
      {testResult && (
        <div
          className={`glass-card mt-2 px-3 py-2 ${
            testResult.success ? 'bg-accent-success/10 border-accent-success/30' : 'bg-accent-error/10 border-accent-error/30'
          }`}
        >
          <p style={{ 
            color: testResult.success ? 'var(--accent-success)' : 'var(--accent-error)',
            fontSize: 'var(--text-sm)'
          }}>
            {testResult.success ? '✓ Connection successful' : '✗ Connection failed'}
          </p>
        </div>
      )}
    </div>
  );
}

export default MCPServerCard;
