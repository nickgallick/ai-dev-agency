import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card } from '@/components/Card'
import { Badge } from '@/components/Badge'
import { Button } from '@/components/Button'
import { api, BackupInfo } from '@/lib/api'
import { 
  Download,
  Upload,
  HardDrive,
  Cloud,
  Database,
  RefreshCw,
  Check,
  AlertTriangle,
  Clock,
  FileArchive
} from 'lucide-react'

export default function SystemBackup() {
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [destination, setDestination] = useState<'local' | 's3' | 'r2'>('local')
  const [includeProjects, setIncludeProjects] = useState(false)
  const [backupStatus, setBackupStatus] = useState<'idle' | 'running' | 'success' | 'error'>('idle')
  const [lastBackupResult, setLastBackupResult] = useState<any>(null)
  const [restoreStatus, setRestoreStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [importStatus, setImportStatus] = useState<{ imported: number; skipped: number } | null>(null)
  const [confirmRestore, setConfirmRestore] = useState<string | null>(null)

  const { data: backups, isLoading } = useQuery({
    queryKey: ['backups'],
    queryFn: api.listBackups,
  })

  const backupMutation = useMutation({
    mutationFn: () => api.createBackup(destination, undefined, includeProjects),
    onMutate: () => setBackupStatus('running'),
    onSuccess: (result) => {
      setBackupStatus(result.success ? 'success' : 'error')
      setLastBackupResult(result)
      queryClient.invalidateQueries({ queryKey: ['backups'] })
    },
    onError: () => setBackupStatus('error'),
  })

  const restoreMutation = useMutation({
    mutationFn: (backupPath: string) => api.restoreBackup(backupPath),
    onSuccess: (result) => {
      setConfirmRestore(null)
      setRestoreStatus({
        type: result.success ? 'success' : 'error',
        message: result.success
          ? 'Restore completed successfully!'
          : 'Restore completed with errors. Check logs for details.',
      })
    },
    onError: (error) => {
      setConfirmRestore(null)
      setRestoreStatus({ type: 'error', message: 'Restore failed: ' + (error as Error).message })
    },
  })

  const exportKnowledgeMutation = useMutation({
    mutationFn: () => api.exportKnowledge(false),
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `knowledge_base_${new Date().toISOString().split('T')[0]}.json`
      a.click()
      URL.revokeObjectURL(url)
    },
  })

  const importKnowledgeMutation = useMutation({
    mutationFn: (file: File) => api.importKnowledge(file, true),
    onSuccess: (result) => {
      setImportStatus({ imported: result.imported, skipped: result.skipped })
    },
  })

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const handleKnowledgeImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      importKnowledgeMutation.mutate(file)
    }
  }

  return (
    <div className="space-y-6 pb-20 lg:pb-0">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-semibold text-text-primary">System Backup</h2>
        <p className="text-text-secondary mt-1">Create backups and restore your system</p>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Create Backup Card */}
        <Card className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-lg bg-accent-primary/10">
              <HardDrive className="w-6 h-6 text-accent-primary" />
            </div>
            <div>
              <h3 className="font-medium text-text-primary">Create Backup</h3>
              <p className="text-sm text-text-secondary">Backup database and files</p>
            </div>
          </div>

          <div className="space-y-4">
            {/* Destination Selection */}
            <div>
              <label className="text-sm font-medium text-text-primary mb-2 block">Destination</label>
              <div className="flex gap-2">
                {[
                  { id: 'local', label: 'Local', icon: HardDrive },
                  { id: 's3', label: 'S3', icon: Cloud },
                  { id: 'r2', label: 'R2', icon: Cloud },
                ].map(opt => (
                  <button
                    key={opt.id}
                    onClick={() => setDestination(opt.id as any)}
                    className={`flex-1 p-3 rounded-lg border transition-colors ${
                      destination === opt.id
                        ? 'border-accent-primary bg-accent-primary/10'
                        : 'border-border-subtle hover:border-border-focus'
                    }`}
                  >
                    <opt.icon className={`w-5 h-5 mx-auto mb-1 ${
                      destination === opt.id ? 'text-accent-primary' : 'text-text-secondary'
                    }`} />
                    <p className={`text-xs ${
                      destination === opt.id ? 'text-accent-primary' : 'text-text-secondary'
                    }`}>{opt.label}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Options */}
            <div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeProjects}
                  onChange={(e) => setIncludeProjects(e.target.checked)}
                  className="w-4 h-4 rounded border-border-subtle"
                />
                <span className="text-sm text-text-primary">Include generated project files</span>
              </label>
              <p className="text-xs text-text-tertiary mt-1 ml-6">
                Warning: This can significantly increase backup size
              </p>
            </div>

            {/* Backup Button */}
            <Button
              onClick={() => backupMutation.mutate()}
              disabled={backupStatus === 'running'}
              className="w-full"
            >
              {backupStatus === 'running' ? (
                <><RefreshCw className="w-4 h-4 mr-2 animate-spin" />Creating Backup...</>
              ) : (
                <><Download className="w-4 h-4 mr-2" />Create Backup</>
              )}
            </Button>

            {/* Status */}
            {backupStatus === 'success' && lastBackupResult && (
              <div className="p-3 bg-accent-success/10 rounded-lg border border-accent-success/20">
                <div className="flex items-center gap-2 text-accent-success">
                  <Check className="w-4 h-4" />
                  <span className="text-sm font-medium">Backup Created</span>
                </div>
                <p className="text-xs text-text-secondary mt-1">
                  {lastBackupResult.path || lastBackupResult.key}
                </p>
                <p className="text-xs text-text-tertiary">
                  Size: {formatFileSize(lastBackupResult.size_bytes || 0)}
                </p>
              </div>
            )}

            {backupStatus === 'error' && (
              <div className="p-3 bg-accent-error/10 rounded-lg border border-accent-error/20">
                <div className="flex items-center gap-2 text-accent-error">
                  <AlertTriangle className="w-4 h-4" />
                  <span className="text-sm font-medium">Backup Failed</span>
                </div>
                <p className="text-xs text-text-secondary mt-1">
                  {lastBackupResult?.error || 'Unknown error'}
                </p>
              </div>
            )}
          </div>
        </Card>

        {/* Knowledge Base Card */}
        <Card className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-lg bg-accent-purple/10">
              <Database className="w-6 h-6 text-accent-purple" />
            </div>
            <div>
              <h3 className="font-medium text-text-primary">Knowledge Base</h3>
              <p className="text-sm text-text-secondary">Export or import knowledge</p>
            </div>
          </div>

          <div className="space-y-3">
            <Button
              variant="secondary"
              onClick={() => exportKnowledgeMutation.mutate()}
              disabled={exportKnowledgeMutation.isPending}
              className="w-full"
            >
              <Download className="w-4 h-4 mr-2" />
              Export Knowledge Base
            </Button>

            <input
              type="file"
              ref={fileInputRef}
              accept=".json"
              onChange={handleKnowledgeImport}
              className="hidden"
            />
            <Button
              variant="secondary"
              onClick={() => fileInputRef.current?.click()}
              disabled={importKnowledgeMutation.isPending}
              className="w-full"
            >
              <Upload className="w-4 h-4 mr-2" />
              Import Knowledge Base
            </Button>

            {importStatus && (
              <div className="p-3 bg-accent-success/10 rounded-lg border border-accent-success/20">
                <div className="flex items-center gap-2 text-accent-success">
                  <Check className="w-4 h-4" />
                  <span className="text-sm">
                    Imported {importStatus.imported}, skipped {importStatus.skipped}
                  </span>
                </div>
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Backup History */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-medium text-text-primary">Backup History</h3>
          <Button 
            variant="ghost" 
            size="sm"
            onClick={() => queryClient.invalidateQueries({ queryKey: ['backups'] })}
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>

        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-16 bg-background-tertiary rounded-lg animate-pulse" />
            ))}
          </div>
        ) : !backups?.backups?.length ? (
          <div className="text-center py-8 text-text-secondary">
            <FileArchive className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No backups found</p>
            <p className="text-sm">Create your first backup above</p>
          </div>
        ) : (
          <div className="space-y-3">
            {backups.backups.map((backup: BackupInfo) => (
              <div key={backup.filename} className="p-4 bg-background-tertiary rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <FileArchive className="w-5 h-5 text-text-secondary" />
                    <div>
                      <p className="font-medium text-text-primary">{backup.filename}</p>
                      <div className="flex items-center gap-3 text-xs text-text-secondary">
                        <span className="flex items-center gap-1">
                          <HardDrive className="w-3 h-3" />
                          {formatFileSize(backup.size_bytes)}
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {new Date(backup.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setConfirmRestore(backup.path)}
                      disabled={restoreMutation.isPending}
                    >
                      <Upload className="w-4 h-4 mr-1" />
                      Restore
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Restore status */}
      {restoreStatus && (
        <div className={`p-4 rounded-lg border flex items-start gap-3 ${
          restoreStatus.type === 'success'
            ? 'bg-accent-success/10 border-accent-success/20'
            : 'bg-accent-error/10 border-accent-error/20'
        }`}>
          {restoreStatus.type === 'success'
            ? <Check className="w-5 h-5 text-accent-success mt-0.5" />
            : <AlertTriangle className="w-5 h-5 text-accent-error mt-0.5" />}
          <div className="flex-1">
            <p className={`font-medium ${restoreStatus.type === 'success' ? 'text-accent-success' : 'text-accent-error'}`}>
              {restoreStatus.message}
            </p>
          </div>
          <button
            onClick={() => setRestoreStatus(null)}
            className="text-text-tertiary hover:text-text-primary transition-colors"
            aria-label="Dismiss"
          >
            ✕
          </button>
        </div>
      )}

      {/* Info Card */}
      <Card className="p-4 border-l-4 border-l-accent-primary">
        <h4 className="font-medium text-text-primary mb-2">Backup Information</h4>
        <ul className="space-y-1 text-sm text-text-secondary">
          <li>• <strong>Database tables:</strong> projects, agent_logs, cost_tracking, knowledge_base, templates, presets</li>
          <li>• <strong>Files:</strong> generated assets, templates, configurations</li>
          <li>• <strong>Local backups:</strong> stored in /home/ubuntu/ai-dev-agency/backups/</li>
          <li>• <strong>Cloud backups:</strong> require S3/R2 credentials in Settings</li>
        </ul>
      </Card>

      {/* Restore confirmation dialog */}
      {confirmRestore && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
          onClick={() => setConfirmRestore(null)}
          onKeyDown={(e) => e.key === 'Escape' && setConfirmRestore(null)}
          tabIndex={-1}
        >
          <div
            className="glass-card max-w-md w-full space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-accent-warning/10">
                <AlertTriangle className="w-6 h-6 text-accent-warning" />
              </div>
              <div>
                <h3 className="font-semibold text-text-primary">Confirm Restore</h3>
                <p className="text-sm text-text-secondary">This will overwrite your current database.</p>
              </div>
            </div>
            <p className="text-sm text-text-secondary">
              Are you sure you want to restore from this backup? All data created after this backup will be lost.
            </p>
            <div className="flex gap-3 justify-end">
              <Button variant="ghost" onClick={() => setConfirmRestore(null)}>
                Cancel
              </Button>
              <Button
                onClick={() => restoreMutation.mutate(confirmRestore)}
                disabled={restoreMutation.isPending}
              >
                {restoreMutation.isPending ? (
                  <><RefreshCw className="w-4 h-4 mr-2 animate-spin" />Restoring...</>
                ) : (
                  <><Upload className="w-4 h-4 mr-2" />Yes, Restore</>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
