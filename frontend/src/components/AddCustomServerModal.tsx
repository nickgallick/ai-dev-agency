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
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-lg shadow-xl max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Add Custom MCP Server
        </h2>

        <div className="space-y-4">
          {/* Server Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Server Name *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="my-custom-server"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Server URL */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Server URL *
            </label>
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="http://localhost:3001 or stdio://command"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Auth Method */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Authentication Method
            </label>
            <select
              value={authMethod}
              onChange={(e) => setAuthMethod(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            >
              <option value="none">None</option>
              <option value="api_key">API Key</option>
              <option value="bearer">Bearer Token</option>
            </select>
          </div>

          {/* Credential Value */}
          {authMethod !== 'none' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {authMethod === 'api_key' ? 'API Key' : 'Bearer Token'}
              </label>
              <input
                type="password"
                value={credentialValue}
                onChange={(e) => setCredentialValue(e.target.value)}
                placeholder="Enter credential"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
          )}

          {/* Agent Assignment */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Assign to Agents
            </label>
            <div className="flex flex-wrap gap-2">
              {availableAgents.map((agent) => (
                <label
                  key={agent}
                  className={`px-3 py-1.5 rounded-full text-sm cursor-pointer transition-colors ${
                    selectedAgents.includes(agent)
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
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
          <div className="mt-4 p-2 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 text-sm rounded">
            {error}
          </div>
        )}

        <div className="flex justify-end gap-2 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {isSubmitting ? 'Adding...' : 'Add Server'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default AddCustomServerModal;
