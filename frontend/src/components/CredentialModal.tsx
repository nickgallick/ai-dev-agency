import React, { useState } from 'react';

interface CredentialModalProps {
  isOpen: boolean;
  onClose: () => void;
  serverName: string;
  credentialKey: string;
  onSave: (value: string) => Promise<void>;
  onDelete: () => Promise<void>;
}

export function CredentialModal({
  isOpen,
  onClose,
  serverName,
  credentialKey,
  onSave,
  onDelete,
}: CredentialModalProps) {
  const [value, setValue] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSave = async () => {
    if (!value.trim()) {
      setError('Please enter a value');
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      await onSave(value);
      setValue('');
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to save credential');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    setIsSaving(true);
    try {
      await onDelete();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to delete credential');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md shadow-xl">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Configure {serverName} Credential
        </h2>

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {credentialKey}
          </label>
          <input
            type="password"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Enter credential value"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            This value will be encrypted before storage.
          </p>
        </div>

        {error && (
          <div className="mb-4 p-2 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 text-sm rounded">
            {error}
          </div>
        )}

        <div className="flex justify-between">
          <button
            onClick={handleDelete}
            disabled={isSaving}
            className="px-3 py-2 text-red-600 hover:text-red-700 text-sm disabled:opacity-50"
          >
            Remove Stored Credential
          </button>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {isSaving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CredentialModal;
