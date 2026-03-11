import React, { useState } from 'react';
import { AlertCircle } from 'lucide-react';

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
    <div
      className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50"
      onClick={onClose}
      onKeyDown={(e) => e.key === 'Escape' && onClose()}
      tabIndex={-1}
    >
      <div
        className="glass-card-elevated w-full max-w-md mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold text-text-primary mb-4">
          Configure {serverName} Credential
        </h2>

        <div className="mb-4">
          <label className="block text-sm font-medium text-text-primary mb-1">
            {credentialKey}
          </label>
          <input
            type="password"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Enter credential value"
            className="glass-input w-full"
          />
          <p className="mt-1 text-xs text-text-tertiary">
            This value will be encrypted before storage.
          </p>
        </div>

        {error && (
          <div className="mb-4 flex items-start gap-2 p-3 bg-accent-error/10 border border-accent-error/30 rounded-lg">
            <AlertCircle className="w-4 h-4 text-accent-error flex-shrink-0 mt-0.5" />
            <span className="text-sm text-accent-error">{error}</span>
          </div>
        )}

        <div className="flex justify-between items-center">
          <button
            onClick={handleDelete}
            disabled={isSaving}
            className="px-3 py-2 text-accent-error hover:opacity-80 text-sm disabled:opacity-50 transition-opacity"
          >
            Remove Stored Credential
          </button>
          <div className="flex gap-2">
            <button onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button onClick={handleSave} disabled={isSaving} className="btn-primary disabled:opacity-50">
              {isSaving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CredentialModal;
