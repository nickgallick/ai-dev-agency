import React, { useState } from 'react';

interface AddCustomServerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (server: {
    name: string;
    url: string;
    authMethod: string;
    credentialValue?: string;
    agentAssignments: string[];
  }) => Promise<void>;
  availableAgents: string[];
}

export function AddCustomServerModal({
  isOpen,
  onClose,
  onAdd,
  availableAgents,
}: AddCustomServerModalProps) {
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [authMethod, setAuthMethod] = useState('none');
  const [credentialValue, setCredentialValue] = useState('');
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async () => {
    if (!name.trim() || !url.trim()) {
      setError('Name and URL are required');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await onAdd({
        name,
        url,
        authMethod,
        credentialValue: authMethod !== 'none' ? credentialValue : undefined,
        agentAssignments: selectedAgents,
      });
      // Reset form
      setName('');
      setUrl('');
      setAuthMethod('none');
      setCredentialValue('');
      setSelectedAgents([]);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to add server');
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleAgent = (agent: string) => {
    setSelectedAgents((prev) =>
      prev.includes(agent)
        ? prev.filter((a) => a !== agent)
        : [...prev, agent]
    );
  };

  return (
    <div
      className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50"
      onClick={onClose}
      onKeyDown={(e) => e.key === 'Escape' && onClose()}
      tabIndex={-1}
    >
      <div
        className="glass-card-elevated w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold text-text-primary mb-4">
          Add Custom MCP Server
        </h2>

        <div className="space-y-4">
          {/* Server Name */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-1">
              Server Name *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="my-custom-server"
              className="glass-input w-full"
            />
          </div>

          {/* Server URL */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-1">
              Server URL *
            </label>
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="http://localhost:3001 or stdio://command"
              className="glass-input w-full"
            />
          </div>

          {/* Auth Method */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-1">
              Authentication Method
            </label>
            <select
              value={authMethod}
              onChange={(e) => setAuthMethod(e.target.value)}
              className="glass-input select w-full"
            >
              <option value="none">None</option>
              <option value="api_key">API Key</option>
              <option value="bearer">Bearer Token</option>
            </select>
          </div>

          {/* Credential Value */}
          {authMethod !== 'none' && (
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">
                {authMethod === 'api_key' ? 'API Key' : 'Bearer Token'}
              </label>
              <input
                type="password"
                value={credentialValue}
                onChange={(e) => setCredentialValue(e.target.value)}
                placeholder="Enter credential"
                className="glass-input w-full"
              />
            </div>
          )}

          {/* Agent Assignment */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              Assign to Agents
            </label>
            <div className="flex flex-wrap gap-2">
              {availableAgents.map((agent) => (
                <label
                  key={agent}
                  className={`px-3 py-1.5 rounded-full text-sm cursor-pointer transition-colors ${
                    selectedAgents.includes(agent)
                      ? 'bg-accent-primary text-white'
                      : 'bg-bg-secondary text-text-secondary hover:bg-bg-tertiary'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedAgents.includes(agent)}
                    onChange={() => toggleAgent(agent)}
                    className="sr-only"
                  />
                  {agent}
                </label>
              ))}
            </div>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-accent-error/10 border border-accent-error/30 text-accent-error text-sm rounded-lg">
            {error}
          </div>
        )}

        <div className="flex justify-end gap-2 mt-6">
          <button onClick={onClose} className="btn-secondary">
            Cancel
          </button>
          <button onClick={handleSubmit} disabled={isSubmitting} className="btn-primary disabled:opacity-50">
            {isSubmitting ? 'Adding...' : 'Add Server'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default AddCustomServerModal;
