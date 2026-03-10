import React, { useState } from 'react';
import { Badge } from './Badge';
import { StatusDot } from './StatusDot';

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

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <StatusDot status={status} size="md" />
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white capitalize">
              {name}
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 font-mono">
              {source}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {agentWired ? (
            <Badge variant="success">Active</Badge>
          ) : (
            <Badge variant="outline">Standby</Badge>
          )}
          {/* Toggle Switch */}
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => onToggle(e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-600 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
          </label>
        </div>
      </div>

      {/* Description */}
      <p className="text-sm text-gray-600 dark:text-gray-300 mb-3">
        {description}
      </p>

      {/* Agent Pills */}
      <div className="flex flex-wrap gap-1 mb-3">
        {usedBy.map((agent) => (
          <Badge key={agent} variant="info" size="sm">
            {agent}
          </Badge>
        ))}
      </div>

      {/* Error Message */}
      {errorMessage && (
        <div className="bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 text-sm rounded p-2 mb-3">
          {errorMessage}
        </div>
      )}

      {/* Expandable Tools Section */}
      <div className="border-t border-gray-100 dark:border-gray-700 pt-3">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
        >
          <svg
            className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          {discoveredTools.length} tools available
        </button>

        {isExpanded && (
          <div className="mt-2 pl-6">
            <div className="flex flex-wrap gap-1">
              {discoveredTools.map((tool) => (
                <code
                  key={tool}
                  className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-xs rounded"
                >
                  {tool}
                </code>
              ))}
            </div>
            <div className="mt-2 text-xs text-gray-500">
              <p>Last used: {formatTimestamp(lastUsed)}</p>
              <p>Last health check: {formatTimestamp(lastHealthCheck)}</p>
            </div>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-2 mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
        <button
          onClick={handleTest}
          disabled={isTesting}
          className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
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
            className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 text-sm rounded hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            Configure Auth
          </button>
        )}
      </div>

      {/* Test Result */}
      {testResult && (
        <div
          className={`mt-2 text-sm p-2 rounded ${
            testResult.success
              ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300'
              : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300'
          }`}
        >
          {testResult.success ? '✓ Connection successful' : '✗ Connection failed'}
        </div>
      )}
    </div>
  );
}

export default MCPServerCard;
