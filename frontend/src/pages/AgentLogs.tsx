import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, AgentLog } from '@/lib/api'
import { useState, useMemo } from 'react'
import { format } from 'date-fns'
import {
  Activity,
  Filter,
  Clock,
  DollarSign,
  Cpu,
  ChevronDown,
  ChevronUp,
  Download,
  Trash2,
  Search,
} from 'lucide-react'

const LOGS_PER_PAGE = 50

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`
  const mins = Math.floor(ms / 60_000)
  const secs = ((ms % 60_000) / 1000).toFixed(0)
  return `${mins}m ${secs}s`
}

function statusColor(status: string): string {
  switch (status.toLowerCase()) {
    case 'success':
    case 'completed':
      return 'var(--accent-success, #22c55e)'
    case 'error':
    case 'failed':
      return 'var(--accent-error, #ef4444)'
    case 'running':
    case 'in_progress':
      return 'var(--accent-warning, #f59e0b)'
    default:
      return 'var(--text-tertiary)'
  }
}

export default function AgentLogs() {
  const queryClient = useQueryClient()
  const [expandedLog, setExpandedLog] = useState<string | null>(null)
  const [filterProject, setFilterProject] = useState<string>('all')
  const [filterAgent, setFilterAgent] = useState<string>('all')
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [filterModel, setFilterModel] = useState<string>('all')
  const [dateStart, setDateStart] = useState<string>('')
  const [dateEnd, setDateEnd] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [page, setPage] = useState(0)

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.getProjects({ limit: 200 }),
  })

  const { data: logs, isLoading } = useQuery({
    queryKey: ['agentLogs', filterProject],
    queryFn: () =>
      api.getAgentLogs({
        ...(filterProject !== 'all' ? { project_id: filterProject } : {}),
        limit: 5000,
      }),
  })

  const agents = useMemo(
    () => Array.from(new Set(logs?.map((l) => l.agent_name) || [])).sort(),
    [logs]
  )

  const models = useMemo(
    () => Array.from(new Set(logs?.map((l) => l.model_used).filter(Boolean) || [])).sort(),
    [logs]
  )

  const filteredLogs = useMemo(() => {
    if (!logs) return []
    return logs.filter((log) => {
      if (filterAgent !== 'all' && log.agent_name !== filterAgent) return false
      if (filterStatus !== 'all' && log.status?.toLowerCase() !== filterStatus) return false
      if (filterModel !== 'all' && log.model_used !== filterModel) return false
      if (dateStart) {
        const logDate = new Date(log.timestamp)
        const start = new Date(dateStart)
        start.setHours(0, 0, 0, 0)
        if (logDate < start) return false
      }
      if (dateEnd) {
        const logDate = new Date(log.timestamp)
        const end = new Date(dateEnd)
        end.setHours(23, 59, 59, 999)
        if (logDate > end) return false
      }
      if (searchQuery) {
        const q = searchQuery.toLowerCase()
        if (
          !log.agent_name.toLowerCase().includes(q) &&
          !log.model_used?.toLowerCase().includes(q) &&
          !(log.error_message || '').toLowerCase().includes(q)
        )
          return false
      }
      return true
    })
  }, [logs, filterAgent, filterStatus, filterModel, dateStart, dateEnd, searchQuery])

  const totalPages = Math.max(1, Math.ceil(filteredLogs.length / LOGS_PER_PAGE))
  const safePage = Math.min(page, totalPages - 1)
  const paginatedLogs = filteredLogs.slice(
    safePage * LOGS_PER_PAGE,
    (safePage + 1) * LOGS_PER_PAGE
  )

  // Reset to page 0 when filters change
  useMemo(() => {
    setPage(0)
  }, [filterProject, filterAgent, filterStatus, filterModel, dateStart, dateEnd, searchQuery])

  function handleExportCSV() {
    if (!filteredLogs.length) return
    const headers = [
      'timestamp',
      'project_id',
      'agent_name',
      'model_used',
      'prompt_tokens',
      'completion_tokens',
      'total_tokens',
      'cost',
      'duration_ms',
      'status',
      'error_message',
    ]
    const rows = filteredLogs.map((log) =>
      [
        log.timestamp,
        log.project_id,
        log.agent_name,
        log.model_used,
        log.prompt_tokens,
        log.completion_tokens,
        log.total_tokens,
        log.cost,
        log.duration_ms,
        log.status,
        (log.error_message || '').replace(/"/g, '""'),
      ]
        .map((v) => `"${v}"`)
        .join(',')
    )
    const csv = [headers.join(','), ...rows].join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `agent-logs-${format(new Date(), 'yyyy-MM-dd-HHmmss')}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  function handleClearLogs() {
    if (!window.confirm('Are you sure you want to clear all logs? This action cannot be undone.'))
      return
    fetch('/api/agents/logs', { method: 'DELETE' })
      .then(() => {
        queryClient.invalidateQueries({ queryKey: ['agentLogs'] })
      })
      .catch(() => {
        alert('Failed to clear logs. The backend endpoint may not exist yet.')
      })
  }

  function getProjectName(projectId: string): string {
    const project = projects?.find((p) => p.id === projectId)
    return project?.name || project?.brief?.slice(0, 40) || projectId.slice(0, 8)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-2">
        <div>
          <h1
            className="text-2xl lg:text-3xl font-bold flex items-center gap-3"
            style={{ color: 'var(--text-primary)' }}
          >
            <Activity className="w-7 h-7" style={{ color: 'var(--accent-primary)' }} />
            Agent Logs
          </h1>
          <p
            className="mt-1"
            style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-base)' }}
          >
            Debugging view for all LLM calls across the pipeline
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleExportCSV}
            disabled={!filteredLogs.length}
            className="glass-card flex items-center gap-2 text-sm font-medium transition-colors hover:opacity-80 disabled:opacity-40"
            style={{
              padding: 'var(--space-2) var(--space-4)',
              color: 'var(--text-primary)',
              cursor: filteredLogs.length ? 'pointer' : 'not-allowed',
            }}
          >
            <Download className="w-4 h-4" />
            Export CSV
          </button>
          <button
            onClick={handleClearLogs}
            className="glass-card flex items-center gap-2 text-sm font-medium transition-colors hover:opacity-80"
            style={{
              padding: 'var(--space-2) var(--space-4)',
              color: 'var(--accent-error, #ef4444)',
              cursor: 'pointer',
            }}
          >
            <Trash2 className="w-4 h-4" />
            Clear Logs
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="glass-card" style={{ padding: 'var(--space-4)' }}>
        <div className="flex items-center gap-2 mb-3">
          <Filter className="w-5 h-5" style={{ color: 'var(--text-tertiary)' }} />
          <span
            className="text-sm font-medium"
            style={{ color: 'var(--text-secondary)' }}
          >
            Filters
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {/* Search */}
          <div className="relative">
            <Search
              className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2"
              style={{ color: 'var(--text-tertiary)' }}
            />
            <input
              type="text"
              placeholder="Search logs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="glass-input"
              style={{
                width: '200px',
                paddingLeft: 'var(--space-8)',
                padding: 'var(--space-2) var(--space-4) var(--space-2) var(--space-8)',
              }}
            />
          </div>

          {/* Project filter */}
          <select
            value={filterProject}
            onChange={(e) => setFilterProject(e.target.value)}
            className="glass-input"
            style={{ width: 'auto', padding: 'var(--space-2) var(--space-4)' }}
          >
            <option value="all">All Projects</option>
            {projects?.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name || project.brief?.slice(0, 40) || project.id.slice(0, 8)}
              </option>
            ))}
          </select>

          {/* Agent filter */}
          <select
            value={filterAgent}
            onChange={(e) => setFilterAgent(e.target.value)}
            className="glass-input"
            style={{ width: 'auto', padding: 'var(--space-2) var(--space-4)' }}
          >
            <option value="all">All Agents</option>
            {agents.map((agent) => (
              <option key={agent} value={agent}>
                {agent}
              </option>
            ))}
          </select>

          {/* Status filter */}
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="glass-input"
            style={{ width: 'auto', padding: 'var(--space-2) var(--space-4)' }}
          >
            <option value="all">All Statuses</option>
            <option value="success">Success</option>
            <option value="error">Error</option>
            <option value="running">Running</option>
          </select>

          {/* Model filter */}
          <select
            value={filterModel}
            onChange={(e) => setFilterModel(e.target.value)}
            className="glass-input"
            style={{ width: 'auto', padding: 'var(--space-2) var(--space-4)' }}
          >
            <option value="all">All Models</option>
            {models.map((model) => (
              <option key={model} value={model}>
                {model}
              </option>
            ))}
          </select>

          {/* Date range */}
          <input
            type="date"
            value={dateStart}
            onChange={(e) => setDateStart(e.target.value)}
            className="glass-input"
            style={{ width: 'auto', padding: 'var(--space-2) var(--space-4)' }}
            title="Start date"
          />
          <span style={{ color: 'var(--text-tertiary)' }}>to</span>
          <input
            type="date"
            value={dateEnd}
            onChange={(e) => setDateEnd(e.target.value)}
            className="glass-input"
            style={{ width: 'auto', padding: 'var(--space-2) var(--space-4)' }}
            title="End date"
          />
        </div>
      </div>

      {/* Log count + pagination info */}
      <div className="flex items-center justify-between">
        <span style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-sm)' }}>
          Showing {filteredLogs.length === 0 ? 0 : safePage * LOGS_PER_PAGE + 1}
          {' '}-{' '}
          {Math.min((safePage + 1) * LOGS_PER_PAGE, filteredLogs.length)} of{' '}
          {filteredLogs.length} logs
          {logs && filteredLogs.length !== logs.length && (
            <span> (filtered from {logs.length} total)</span>
          )}
        </span>
        {totalPages > 1 && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={safePage === 0}
              className="glass-card text-sm font-medium transition-colors hover:opacity-80 disabled:opacity-40"
              style={{
                padding: 'var(--space-1) var(--space-3)',
                color: 'var(--text-primary)',
                cursor: safePage === 0 ? 'not-allowed' : 'pointer',
              }}
            >
              Prev
            </button>
            <span style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
              Page {safePage + 1} of {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={safePage >= totalPages - 1}
              className="glass-card text-sm font-medium transition-colors hover:opacity-80 disabled:opacity-40"
              style={{
                padding: 'var(--space-1) var(--space-3)',
                color: 'var(--text-primary)',
                cursor: safePage >= totalPages - 1 ? 'not-allowed' : 'pointer',
              }}
            >
              Next
            </button>
          </div>
        )}
      </div>

      {/* Logs List */}
      <div className="space-y-3">
        {isLoading && (
          <>
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="skeleton h-20 w-full" />
            ))}
          </>
        )}

        {filteredLogs.length === 0 && !isLoading && (
          <div className="glass-card text-center py-12">
            <Activity
              className="w-12 h-12 mx-auto mb-3"
              style={{ color: 'var(--text-tertiary)' }}
            />
            <p style={{ color: 'var(--text-secondary)' }}>No logs found</p>
            {(filterAgent !== 'all' ||
              filterStatus !== 'all' ||
              filterModel !== 'all' ||
              dateStart ||
              dateEnd ||
              searchQuery) && (
              <p
                className="mt-1"
                style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-sm)' }}
              >
                Try adjusting your filters
              </p>
            )}
          </div>
        )}

        {paginatedLogs.map((log) => (
          <div
            key={log.id}
            className="glass-card cursor-pointer transition-all"
            onClick={() => setExpandedLog(expandedLog === log.id ? null : log.id)}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3 min-w-0">
                <div
                  className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
                  style={{ background: 'var(--glass-bg-elevated)' }}
                >
                  <Cpu className="w-5 h-5" style={{ color: 'var(--accent-primary)' }} />
                </div>
                <div className="min-w-0">
                  <h3 className="font-medium" style={{ color: 'var(--text-primary)' }}>
                    {log.agent_name}
                    {log.agent_step != null && (
                      <span
                        className="ml-2 text-xs"
                        style={{ color: 'var(--text-tertiary)' }}
                      >
                        Step {log.agent_step}
                      </span>
                    )}
                  </h3>
                  <div
                    className="flex flex-wrap items-center gap-3"
                    style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-xs)' }}
                  >
                    <span className="badge badge-info">{log.model_used}</span>
                    <span
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
                      style={{
                        color: statusColor(log.status),
                        background: `color-mix(in srgb, ${statusColor(log.status)} 15%, transparent)`,
                      }}
                    >
                      {log.status}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(log.timestamp).toLocaleString()}
                    </span>
                    {filterProject === 'all' && (
                      <span
                        className="truncate max-w-[150px]"
                        title={log.project_id}
                      >
                        {getProjectName(log.project_id)}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-4 shrink-0">
                <div className="text-right">
                  <p className="font-medium" style={{ color: 'var(--text-primary)' }}>
                    {(log.total_tokens || 0).toLocaleString()} tokens
                  </p>
                  <p
                    className="flex items-center gap-1 justify-end"
                    style={{
                      color: 'var(--accent-warning)',
                      fontSize: 'var(--text-xs)',
                    }}
                  >
                    <DollarSign className="w-3 h-3" />
                    {(log.cost || 0).toFixed(4)}
                  </p>
                </div>
                {expandedLog === log.id ? (
                  <ChevronUp
                    className="w-5 h-5"
                    style={{ color: 'var(--text-tertiary)' }}
                  />
                ) : (
                  <ChevronDown
                    className="w-5 h-5"
                    style={{ color: 'var(--text-tertiary)' }}
                  />
                )}
              </div>
            </div>

            {expandedLog === log.id && (
              <div
                className="mt-4 pt-4"
                style={{ borderTop: '1px solid var(--glass-border)' }}
              >
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  {/* Status */}
                  <div
                    className="rounded-lg p-3"
                    style={{ background: 'var(--glass-bg-elevated)' }}
                  >
                    <div
                      className="text-xs mb-1"
                      style={{ color: 'var(--text-tertiary)' }}
                    >
                      Status
                    </div>
                    <div
                      className="font-semibold text-sm"
                      style={{ color: statusColor(log.status) }}
                    >
                      {log.status}
                    </div>
                  </div>

                  {/* Duration */}
                  <div
                    className="rounded-lg p-3"
                    style={{ background: 'var(--glass-bg-elevated)' }}
                  >
                    <div
                      className="text-xs mb-1"
                      style={{ color: 'var(--text-tertiary)' }}
                    >
                      Duration
                    </div>
                    <div
                      className="font-semibold text-sm flex items-center gap-1"
                      style={{ color: 'var(--text-primary)' }}
                    >
                      <Clock className="w-3.5 h-3.5" />
                      {formatDuration(log.duration_ms)}
                    </div>
                  </div>

                  {/* Prompt Tokens */}
                  <div
                    className="rounded-lg p-3"
                    style={{ background: 'var(--glass-bg-elevated)' }}
                  >
                    <div
                      className="text-xs mb-1"
                      style={{ color: 'var(--text-tertiary)' }}
                    >
                      Prompt Tokens
                    </div>
                    <div
                      className="font-semibold text-sm"
                      style={{ color: 'var(--text-primary)' }}
                    >
                      {(log.prompt_tokens || 0).toLocaleString()}
                    </div>
                  </div>

                  {/* Completion Tokens */}
                  <div
                    className="rounded-lg p-3"
                    style={{ background: 'var(--glass-bg-elevated)' }}
                  >
                    <div
                      className="text-xs mb-1"
                      style={{ color: 'var(--text-tertiary)' }}
                    >
                      Completion Tokens
                    </div>
                    <div
                      className="font-semibold text-sm"
                      style={{ color: 'var(--text-primary)' }}
                    >
                      {(log.completion_tokens || 0).toLocaleString()}
                    </div>
                  </div>
                </div>

                {/* Additional details row */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-3">
                  {/* Total Tokens */}
                  <div
                    className="rounded-lg p-3"
                    style={{ background: 'var(--glass-bg-elevated)' }}
                  >
                    <div
                      className="text-xs mb-1"
                      style={{ color: 'var(--text-tertiary)' }}
                    >
                      Total Tokens
                    </div>
                    <div
                      className="font-semibold text-sm"
                      style={{ color: 'var(--text-primary)' }}
                    >
                      {(log.total_tokens || 0).toLocaleString()}
                    </div>
                  </div>

                  {/* Cost */}
                  <div
                    className="rounded-lg p-3"
                    style={{ background: 'var(--glass-bg-elevated)' }}
                  >
                    <div
                      className="text-xs mb-1"
                      style={{ color: 'var(--text-tertiary)' }}
                    >
                      Cost
                    </div>
                    <div
                      className="font-semibold text-sm flex items-center gap-1"
                      style={{ color: 'var(--accent-warning)' }}
                    >
                      <DollarSign className="w-3.5 h-3.5" />
                      {(log.cost || 0).toFixed(6)}
                    </div>
                  </div>

                  {/* Model */}
                  <div
                    className="rounded-lg p-3"
                    style={{ background: 'var(--glass-bg-elevated)' }}
                  >
                    <div
                      className="text-xs mb-1"
                      style={{ color: 'var(--text-tertiary)' }}
                    >
                      Model
                    </div>
                    <div
                      className="font-semibold text-sm truncate"
                      style={{ color: 'var(--text-primary)' }}
                      title={log.model_used}
                    >
                      {log.model_used}
                    </div>
                  </div>

                  {/* Project */}
                  <div
                    className="rounded-lg p-3"
                    style={{ background: 'var(--glass-bg-elevated)' }}
                  >
                    <div
                      className="text-xs mb-1"
                      style={{ color: 'var(--text-tertiary)' }}
                    >
                      Project
                    </div>
                    <div
                      className="font-semibold text-sm truncate"
                      style={{ color: 'var(--text-primary)' }}
                      title={log.project_id}
                    >
                      {getProjectName(log.project_id)}
                    </div>
                  </div>
                </div>

                {/* Error message */}
                {log.error_message && (
                  <div
                    className="mt-3 rounded-lg p-3"
                    style={{
                      background: 'color-mix(in srgb, var(--accent-error, #ef4444) 10%, transparent)',
                      border: '1px solid color-mix(in srgb, var(--accent-error, #ef4444) 30%, transparent)',
                    }}
                  >
                    <div
                      className="text-xs font-medium mb-1"
                      style={{ color: 'var(--accent-error, #ef4444)' }}
                    >
                      Error Message
                    </div>
                    <pre
                      className="font-mono text-xs whitespace-pre-wrap break-words"
                      style={{ color: 'var(--text-primary)' }}
                    >
                      {log.error_message}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Bottom pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-2">
          <button
            onClick={() => setPage(0)}
            disabled={safePage === 0}
            className="glass-card text-sm font-medium transition-colors hover:opacity-80 disabled:opacity-40"
            style={{
              padding: 'var(--space-1) var(--space-3)',
              color: 'var(--text-primary)',
              cursor: safePage === 0 ? 'not-allowed' : 'pointer',
            }}
          >
            First
          </button>
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={safePage === 0}
            className="glass-card text-sm font-medium transition-colors hover:opacity-80 disabled:opacity-40"
            style={{
              padding: 'var(--space-1) var(--space-3)',
              color: 'var(--text-primary)',
              cursor: safePage === 0 ? 'not-allowed' : 'pointer',
            }}
          >
            Prev
          </button>
          <span style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
            Page {safePage + 1} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={safePage >= totalPages - 1}
            className="glass-card text-sm font-medium transition-colors hover:opacity-80 disabled:opacity-40"
            style={{
              padding: 'var(--space-1) var(--space-3)',
              color: 'var(--text-primary)',
              cursor: safePage >= totalPages - 1 ? 'not-allowed' : 'pointer',
            }}
          >
            Next
          </button>
          <button
            onClick={() => setPage(totalPages - 1)}
            disabled={safePage >= totalPages - 1}
            className="glass-card text-sm font-medium transition-colors hover:opacity-80 disabled:opacity-40"
            style={{
              padding: 'var(--space-1) var(--space-3)',
              color: 'var(--text-primary)',
              cursor: safePage >= totalPages - 1 ? 'not-allowed' : 'pointer',
            }}
          >
            Last
          </button>
        </div>
      )}
    </div>
  )
}
