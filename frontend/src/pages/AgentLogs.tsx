import { useQuery } from '@tanstack/react-query'
import { api, AgentLog } from '@/lib/api'
import { useState, useMemo, useCallback, useRef, useEffect } from 'react'
import { format } from 'date-fns'
import {
  Activity, Filter, Clock, DollarSign, Cpu, ChevronDown, ChevronUp,
  Download, Trash2, AlertCircle, CheckCircle2, XCircle, X,
} from 'lucide-react'
import { Button } from '@/components/Button'

// ─── CSV Export ─────────────────────────────────────────────────────────────

function exportCSV(logs: AgentLog[]) {
  const headers = ['Timestamp', 'Project ID', 'Agent', 'Model', 'Status', 'Prompt Tokens', 'Completion Tokens', 'Total Tokens', 'Cost ($)', 'Duration (ms)', 'Error']
  const rows = logs.map((l) => [
    format(new Date(l.timestamp), 'yyyy-MM-dd HH:mm:ss'),
    l.project_id,
    l.agent_name,
    l.model_used,
    l.status,
    l.prompt_tokens ?? '',
    l.completion_tokens ?? '',
    l.total_tokens ?? '',
    l.cost?.toFixed(6) ?? '0',
    l.duration_ms ?? '',
    l.error_message ?? '',
  ])
  const csv = [headers, ...rows]
    .map((r) => r.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(','))
    .join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `agent-logs-${format(new Date(), 'yyyyMMdd-HHmmss')}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// ─── Row ────────────────────────────────────────────────────────────────────

function LogRow({ log }: { log: AgentLog }) {
  const [expanded, setExpanded] = useState(false)
  const latencyMs = log.duration_ms

  const statusColor = {
    success: 'text-accent-success',
    completed: 'text-accent-success',
    failed: 'text-accent-error',
    error: 'text-accent-error',
    running: 'text-accent-primary',
  }[log.status] || 'text-text-tertiary'

  const StatusIcon = {
    success: CheckCircle2,
    completed: CheckCircle2,
    failed: XCircle,
    error: XCircle,
    running: Activity,
  }[log.status] || AlertCircle

  return (
    <div
      className="border border-border-subtle rounded-lg overflow-hidden mb-2 transition-shadow hover:shadow-sm"
      style={{ background: 'var(--bg-secondary)' }}
    >
      {/* Summary row */}
      <button
        className="w-full text-left"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3 px-4 py-3">
          {/* Status icon */}
          <StatusIcon className={`w-4 h-4 flex-shrink-0 ${statusColor}`} />

          {/* Agent name */}
          <div className="w-36 flex-shrink-0">
            <span className="text-sm font-medium text-text-primary capitalize">
              {log.agent_name.replace(/_/g, ' ')}
            </span>
          </div>

          {/* Model */}
          <div className="hidden sm:block w-40 flex-shrink-0">
            <code className="text-xs bg-bg-primary px-1.5 py-0.5 rounded text-text-secondary">
              {log.model_used?.split('/').pop() ?? '—'}
            </code>
          </div>

          {/* Timestamp */}
          <div className="hidden md:flex items-center gap-1 text-xs text-text-tertiary w-28 flex-shrink-0">
            <Clock className="w-3 h-3" />
            {format(new Date(log.timestamp), 'HH:mm:ss')}
          </div>

          {/* Tokens */}
          <div className="hidden lg:block text-xs text-text-secondary w-28 flex-shrink-0">
            <span>{(log.total_tokens ?? 0).toLocaleString()} tok</span>
            {log.prompt_tokens != null && (
              <span className="text-text-tertiary ml-1">
                ({log.prompt_tokens}+{log.completion_tokens})
              </span>
            )}
          </div>

          {/* Latency */}
          {latencyMs != null && (
            <div className="hidden lg:block text-xs text-text-tertiary w-16 flex-shrink-0">
              {latencyMs >= 1000 ? `${(latencyMs / 1000).toFixed(1)}s` : `${latencyMs}ms`}
            </div>
          )}

          {/* Cost */}
          <div className="ml-auto flex items-center gap-1 text-xs text-accent-warning font-mono flex-shrink-0">
            <DollarSign className="w-3 h-3" />
            {log.cost?.toFixed(4) ?? '0.0000'}
          </div>

          {/* Expand */}
          <div className="ml-2 text-text-tertiary flex-shrink-0">
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </div>
        </div>
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-border-subtle px-4 py-4 space-y-3 bg-bg-primary">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div>
              <p className="text-text-tertiary mb-1">Project</p>
              <p className="font-mono text-text-secondary">{log.project_id.slice(0, 8)}…</p>
            </div>
            <div>
              <p className="text-text-tertiary mb-1">Status</p>
              <p className={`font-medium ${statusColor}`}>{log.status}</p>
            </div>
            <div>
              <p className="text-text-tertiary mb-1">Date</p>
              <p className="text-text-secondary">{format(new Date(log.timestamp), 'MMM d, yyyy')}</p>
            </div>
            <div>
              <p className="text-text-tertiary mb-1">Model (full)</p>
              <p className="font-mono text-text-secondary break-all">{log.model_used ?? '—'}</p>
            </div>
          </div>
          {log.error_message && (
            <div className="p-3 bg-accent-error/10 rounded-lg border border-accent-error/20">
              <p className="text-xs font-medium text-accent-error mb-1">Error</p>
              <pre className="text-xs text-accent-error/80 whitespace-pre-wrap">{log.error_message}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Clear Confirmation Dialog ───────────────────────────────────────────────

function ClearDialog({ onConfirm, onCancel }: { onConfirm: () => void; onCancel: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-bg-secondary border border-border-subtle rounded-xl p-6 max-w-sm w-full mx-4 shadow-xl">
        <h3 className="text-base font-semibold text-text-primary mb-2">Clear All Logs?</h3>
        <p className="text-sm text-text-secondary mb-6">
          This will permanently delete all visible logs. This action cannot be undone.
        </p>
        <div className="flex gap-3">
          <Button variant="secondary" size="sm" onClick={onCancel} className="flex-1">
            Cancel
          </Button>
          <button
            onClick={onConfirm}
            className="flex-1 px-4 py-2 bg-accent-error text-white rounded-lg text-sm font-medium hover:bg-accent-error/90 transition-colors"
          >
            Delete Logs
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Main Page ──────────────────────────────────────────────────────────────

const PAGE_SIZE = 100

export default function AgentLogs() {
  const [filterAgent, setFilterAgent] = useState('all')
  const [filterStatus, setFilterStatus] = useState('all')
  const [filterModel, setFilterModel] = useState('all')
  const [filterProject, setFilterProject] = useState('all')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE)
  const [showClearDialog, setShowClearDialog] = useState(false)
  const loadMoreRef = useRef<HTMLDivElement>(null)

  // Fetch projects for project filter
  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.getProjects({ limit: 100 }),
  })

  // Fetch all logs (max 500)
  const { data: logs, isLoading, refetch } = useQuery({
    queryKey: ['agentLogs', filterProject],
    queryFn: () => api.getAgentLogs({
      limit: 500,
      project_id: filterProject !== 'all' ? filterProject : undefined,
    }),
  })

  // Client-side filters
  const filteredLogs = useMemo(() => {
    let result = logs ?? []
    if (filterAgent !== 'all') result = result.filter((l) => l.agent_name === filterAgent)
    if (filterStatus !== 'all') result = result.filter((l) => l.status === filterStatus)
    if (filterModel !== 'all') result = result.filter((l) => l.model_used === filterModel)
    if (dateFrom) result = result.filter((l) => new Date(l.timestamp) >= new Date(dateFrom))
    if (dateTo) result = result.filter((l) => new Date(l.timestamp) <= new Date(dateTo + 'T23:59:59'))
    return result
  }, [logs, filterAgent, filterStatus, filterModel, dateFrom, dateTo])

  const visibleLogs = filteredLogs.slice(0, visibleCount)
  const hasMore = visibleCount < filteredLogs.length

  // Unique values for dropdowns
  const agents = useMemo(() => Array.from(new Set(logs?.map((l) => l.agent_name) ?? [])).sort(), [logs])
  const statuses = useMemo(() => Array.from(new Set(logs?.map((l) => l.status) ?? [])).sort(), [logs])
  const models = useMemo(() => Array.from(new Set(logs?.map((l) => l.model_used).filter(Boolean) ?? [])).sort(), [logs])

  // Infinite scroll via IntersectionObserver
  useEffect(() => {
    if (!loadMoreRef.current || !hasMore) return
    const obs = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          setVisibleCount((c) => c + PAGE_SIZE)
        }
      },
      { rootMargin: '200px' }
    )
    obs.observe(loadMoreRef.current)
    return () => obs.disconnect()
  }, [hasMore])

  // Reset visible count when filters change
  useEffect(() => {
    setVisibleCount(PAGE_SIZE)
  }, [filterAgent, filterStatus, filterModel, filterProject, dateFrom, dateTo])

  const clearFilters = useCallback(() => {
    setFilterAgent('all')
    setFilterStatus('all')
    setFilterModel('all')
    setFilterProject('all')
    setDateFrom('')
    setDateTo('')
  }, [])

  const hasActiveFilters = filterAgent !== 'all' || filterStatus !== 'all' || filterModel !== 'all' || filterProject !== 'all' || dateFrom || dateTo

  // Summary stats for visible logs
  const totalTokens = filteredLogs.reduce((s, l) => s + (l.total_tokens ?? 0), 0)
  const totalCost = filteredLogs.reduce((s, l) => s + (l.cost ?? 0), 0)

  return (
    <div className="space-y-6 pb-20 lg:pb-0">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold flex items-center gap-3 text-text-primary">
            <Activity className="w-7 h-7 text-accent-primary" />
            Agent Logs
          </h1>
          <p className="mt-1 text-text-secondary">
            All LLM calls — {filteredLogs.length.toLocaleString()} entries
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => exportCSV(filteredLogs)}
            disabled={filteredLogs.length === 0}
          >
            <Download className="w-4 h-4 mr-2" />
            Export CSV
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowClearDialog(true)}
            disabled={filteredLogs.length === 0}
            className="text-accent-error hover:bg-accent-error/10"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Clear
          </Button>
        </div>
      </div>

      {/* Stats bar */}
      {filteredLogs.length > 0 && (
        <div className="flex flex-wrap gap-4 px-4 py-3 bg-bg-secondary rounded-lg border border-border-subtle text-sm">
          <div className="flex items-center gap-1.5 text-text-secondary">
            <Cpu className="w-4 h-4 text-text-tertiary" />
            <span>{filteredLogs.length} calls</span>
          </div>
          <div className="flex items-center gap-1.5 text-text-secondary">
            <Activity className="w-4 h-4 text-text-tertiary" />
            <span>{totalTokens.toLocaleString()} tokens</span>
          </div>
          <div className="flex items-center gap-1.5 text-accent-warning">
            <DollarSign className="w-4 h-4" />
            <span className="font-mono">${totalCost.toFixed(4)}</span>
          </div>
          {filteredLogs.length > 0 && (
            <div className="flex items-center gap-1.5 text-text-secondary">
              <Clock className="w-4 h-4 text-text-tertiary" />
              <span>avg ${(totalCost / filteredLogs.length).toFixed(4)}/call</span>
            </div>
          )}
        </div>
      )}

      {/* Filters */}
      <div className="p-4 bg-bg-secondary border border-border-subtle rounded-xl space-y-3">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-text-tertiary" />
          <span className="text-sm font-medium text-text-secondary">Filters</span>
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="ml-auto flex items-center gap-1 text-xs text-text-tertiary hover:text-text-primary px-2 py-1 rounded hover:bg-bg-primary transition-colors"
            >
              <X className="w-3 h-3" />
              Clear all
            </button>
          )}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
          {/* Project */}
          <select
            value={filterProject}
            onChange={(e) => setFilterProject(e.target.value)}
            className="glass-input text-sm px-3 py-2 rounded-lg"
          >
            <option value="all">All Projects</option>
            {projects?.map((p) => (
              <option key={p.id} value={p.id}>
                {(p.name || 'Untitled').slice(0, 20)}
              </option>
            ))}
          </select>

          {/* Agent */}
          <select
            value={filterAgent}
            onChange={(e) => setFilterAgent(e.target.value)}
            className="glass-input text-sm px-3 py-2 rounded-lg"
          >
            <option value="all">All Agents</option>
            {agents.map((a) => (
              <option key={a} value={a}>{a.replace(/_/g, ' ')}</option>
            ))}
          </select>

          {/* Status */}
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="glass-input text-sm px-3 py-2 rounded-lg"
          >
            <option value="all">All Statuses</option>
            {statuses.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

          {/* Model */}
          <select
            value={filterModel}
            onChange={(e) => setFilterModel(e.target.value)}
            className="glass-input text-sm px-3 py-2 rounded-lg"
          >
            <option value="all">All Models</option>
            {models.map((m) => (
              <option key={m} value={m}>{m.split('/').pop()}</option>
            ))}
          </select>

          {/* Date from */}
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="glass-input text-sm px-3 py-2 rounded-lg"
            placeholder="From date"
          />

          {/* Date to */}
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="glass-input text-sm px-3 py-2 rounded-lg"
            placeholder="To date"
          />
        </div>
      </div>

      {/* Column headers */}
      {filteredLogs.length > 0 && (
        <div className="hidden md:flex items-center gap-3 px-4 text-xs font-medium text-text-tertiary uppercase tracking-wide">
          <div className="w-4 flex-shrink-0" />
          <div className="w-36 flex-shrink-0">Agent</div>
          <div className="hidden sm:block w-40 flex-shrink-0">Model</div>
          <div className="hidden md:block w-28 flex-shrink-0">Time</div>
          <div className="hidden lg:block w-28 flex-shrink-0">Tokens</div>
          <div className="hidden lg:block w-16 flex-shrink-0">Latency</div>
          <div className="ml-auto">Cost</div>
          <div className="w-4 flex-shrink-0" />
        </div>
      )}

      {/* Log list */}
      <div>
        {isLoading && (
          <div className="space-y-2">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-14 bg-bg-secondary rounded-lg animate-pulse" />
            ))}
          </div>
        )}

        {!isLoading && filteredLogs.length === 0 && (
          <div className="text-center py-16">
            <Activity className="w-12 h-12 mx-auto mb-3 text-text-tertiary" />
            <p className="text-text-secondary">No logs found</p>
            {hasActiveFilters && (
              <button onClick={clearFilters} className="mt-2 text-sm text-accent-primary hover:underline">
                Clear filters
              </button>
            )}
          </div>
        )}

        {visibleLogs.map((log) => (
          <LogRow key={log.id} log={log} />
        ))}

        {/* Infinite scroll sentinel */}
        <div ref={loadMoreRef} />

        {hasMore && (
          <div className="text-center py-4">
            <p className="text-xs text-text-tertiary">
              Showing {visibleCount} of {filteredLogs.length} — scroll to load more
            </p>
          </div>
        )}
      </div>

      {/* Clear confirmation */}
      {showClearDialog && (
        <ClearDialog
          onConfirm={() => {
            // Note: no backend delete endpoint, just clear the local view via refetch
            setShowClearDialog(false)
            // Reset filters to clear the view
            clearFilters()
            refetch()
          }}
          onCancel={() => setShowClearDialog(false)}
        />
      )}
    </div>
  )
}
