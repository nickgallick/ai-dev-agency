/**
 * ProjectTimeline — Interactive checkpoint history timeline with branching (#6)
 *
 * Shows the full pipeline run history as a visual timeline, allows forking
 * from any checkpoint, and comparing outputs across different runs/checkpoints.
 */
import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, CheckpointEntry, AuditLogEntry } from '@/lib/api'
import {
  GitBranch,
  GitCommit,
  Clock,
  DollarSign,
  ChevronDown,
  ChevronRight,
  RotateCcw,
  ArrowLeftRight,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Pause,
  Play,
  Zap,
  Filter,
  X,
} from 'lucide-react'

interface ProjectTimelineProps {
  projectId: string
  projectStatus: string
}

// Format duration from ms
function formatDuration(ms: string | number | null): string {
  if (!ms) return ''
  const num = typeof ms === 'string' ? parseInt(ms, 10) : ms
  if (isNaN(num)) return ''
  if (num < 1000) return `${num}ms`
  if (num < 60000) return `${(num / 1000).toFixed(1)}s`
  return `${(num / 60000).toFixed(1)}m`
}

// Format timestamp
function formatTime(ts: string | null): string {
  if (!ts) return ''
  try {
    const d = new Date(ts)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return ''
  }
}

function formatDate(ts: string | null): string {
  if (!ts) return ''
  try {
    const d = new Date(ts)
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' ' + formatTime(ts)
  } catch {
    return ''
  }
}

// Event type icon and color
function eventStyle(eventType: string): { icon: typeof GitCommit; color: string; bg: string } {
  switch (eventType) {
    case 'pipeline_start':
      return { icon: Play, color: '#4ade80', bg: 'rgba(74,222,128,0.15)' }
    case 'pipeline_complete':
      return { icon: CheckCircle, color: '#4ade80', bg: 'rgba(74,222,128,0.15)' }
    case 'pipeline_failed':
      return { icon: XCircle, color: '#f87171', bg: 'rgba(248,113,113,0.15)' }
    case 'agent_start':
      return { icon: Zap, color: '#60a5fa', bg: 'rgba(96,165,250,0.15)' }
    case 'agent_complete':
      return { icon: CheckCircle, color: '#4ade80', bg: 'rgba(74,222,128,0.15)' }
    case 'agent_failed':
      return { icon: XCircle, color: '#f87171', bg: 'rgba(248,113,113,0.15)' }
    case 'checkpoint_save':
      return { icon: GitCommit, color: '#a78bfa', bg: 'rgba(167,139,250,0.15)' }
    case 'checkpoint_pause':
      return { icon: Pause, color: '#fbbf24', bg: 'rgba(251,191,36,0.15)' }
    case 'checkpoint_resume':
      return { icon: Play, color: '#4ade80', bg: 'rgba(74,222,128,0.15)' }
    case 'agent_retry':
      return { icon: RotateCcw, color: '#fbbf24', bg: 'rgba(251,191,36,0.15)' }
    case 'cost_alert':
      return { icon: AlertTriangle, color: '#fbbf24', bg: 'rgba(251,191,36,0.15)' }
    default:
      return { icon: GitCommit, color: 'var(--text-tertiary)', bg: 'var(--background-tertiary)' }
  }
}

// Agent display names
const AGENT_LABELS: Record<string, string> = {
  intake: 'Intake & Classification',
  research: 'Research',
  architect: 'Architect',
  design_system: 'Design System',
  asset_generation: 'Asset Generation',
  content_generation: 'Content Generation',
  pm_checkpoint_1: 'PM Checkpoint 1',
  code_generation: 'Code Generation',
  integration_wiring: 'Integration Wiring',
  pm_checkpoint_2: 'PM Checkpoint 2',
  code_review: 'Code Review',
  security: 'Security Scanning',
  seo: 'SEO & Performance',
  accessibility: 'Accessibility',
  qa: 'QA & Testing',
  deployment: 'Deployment',
  post_deploy_verification: 'Post-Deploy Verification',
  analytics_monitoring: 'Analytics & Monitoring',
  coding_standards: 'Coding Standards',
  delivery: 'Delivery',
}

type ViewMode = 'checkpoints' | 'audit' | 'combined'
type CompareState = { a: CheckpointEntry | null; b: CheckpointEntry | null }

export function ProjectTimeline({ projectId, projectStatus }: ProjectTimelineProps) {
  const queryClient = useQueryClient()
  const [viewMode, setViewMode] = useState<ViewMode>('combined')
  const [expandedCheckpoints, setExpandedCheckpoints] = useState<Record<string, boolean>>({})
  const [compare, setCompare] = useState<CompareState>({ a: null, b: null })
  const [showCompare, setShowCompare] = useState(false)
  const [auditFilter, setAuditFilter] = useState<string | null>(null)

  const { data: checkpointData } = useQuery({
    queryKey: ['projectCheckpoints', projectId],
    queryFn: () => api.getProjectCheckpoints(projectId),
    refetchInterval: projectStatus !== 'completed' && projectStatus !== 'failed' ? 5000 : false,
  })

  const { data: auditData } = useQuery({
    queryKey: ['projectAuditLog', projectId, auditFilter],
    queryFn: () => api.getProjectAuditLog(projectId, auditFilter || undefined),
    refetchInterval: projectStatus !== 'completed' && projectStatus !== 'failed' ? 5000 : false,
  })

  const restartMutation = useMutation({
    mutationFn: (agentName: string) => api.restartFromAgent(projectId, agentName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projectCheckpoints', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
    },
  })

  const checkpoints = checkpointData?.checkpoints || []
  const auditEntries = auditData?.entries || []

  // Build combined timeline
  const combinedTimeline = useMemo(() => {
    if (viewMode === 'checkpoints') {
      return checkpoints.map((cp) => ({
        type: 'checkpoint' as const,
        timestamp: cp.created_at,
        data: cp,
      }))
    }
    if (viewMode === 'audit') {
      return auditEntries.map((e) => ({
        type: 'audit' as const,
        timestamp: e.timestamp || '',
        data: e,
      }))
    }

    // Combined: merge both lists by timestamp
    const items: Array<
      | { type: 'checkpoint'; timestamp: string; data: CheckpointEntry }
      | { type: 'audit'; timestamp: string; data: AuditLogEntry }
    > = []

    for (const cp of checkpoints) {
      items.push({ type: 'checkpoint', timestamp: cp.created_at, data: cp })
    }
    for (const e of auditEntries) {
      // Skip checkpoint_save events in combined view since we show checkpoints directly
      if (e.event_type === 'checkpoint_save') continue
      items.push({ type: 'audit', timestamp: e.timestamp || '', data: e })
    }

    items.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
    return items
  }, [checkpoints, auditEntries, viewMode])

  const toggleCheckpoint = (id: string) => {
    setExpandedCheckpoints((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  const handleCompareSelect = (cp: CheckpointEntry) => {
    if (!compare.a) {
      setCompare({ a: cp, b: null })
    } else if (!compare.b && compare.a.id !== cp.id) {
      setCompare({ a: compare.a, b: cp })
      setShowCompare(true)
    } else {
      setCompare({ a: cp, b: null })
      setShowCompare(false)
    }
  }

  const clearCompare = () => {
    setCompare({ a: null, b: null })
    setShowCompare(false)
  }

  // Unique event types for filter
  const eventTypes = useMemo(
    () => [...new Set(auditEntries.map((e) => e.event_type))].sort(),
    [auditEntries],
  )

  if (checkpoints.length === 0 && auditEntries.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <GitBranch className="w-8 h-8 mb-3" style={{ color: 'var(--text-tertiary)' }} />
        <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
          No pipeline history yet
        </p>
        <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
          History will appear here once the pipeline starts running
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Header controls */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-1">
          {(['combined', 'checkpoints', 'audit'] as ViewMode[]).map((mode) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className="px-2.5 py-1 rounded text-xs font-medium transition-colors"
              style={{
                background: viewMode === mode ? 'var(--accent-primary-bg, rgba(59,130,246,0.15))' : 'transparent',
                color: viewMode === mode ? 'var(--accent-primary)' : 'var(--text-tertiary)',
              }}
            >
              {mode === 'combined' ? 'All Events' : mode === 'checkpoints' ? 'Checkpoints' : 'Audit Log'}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          {/* Event type filter (audit view) */}
          {(viewMode === 'audit' || viewMode === 'combined') && (
            <div className="relative">
              <select
                value={auditFilter || ''}
                onChange={(e) => setAuditFilter(e.target.value || null)}
                className="text-xs rounded px-2 py-1 pr-6 appearance-none"
                style={{
                  background: 'var(--background-tertiary)',
                  color: 'var(--text-secondary)',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <option value="">All events</option>
                {eventTypes.map((t) => (
                  <option key={t} value={t}>
                    {t.replace(/_/g, ' ')}
                  </option>
                ))}
              </select>
              <Filter className="absolute right-1.5 top-1/2 -translate-y-1/2 w-3 h-3 pointer-events-none" style={{ color: 'var(--text-tertiary)' }} />
            </div>
          )}

          {/* Compare mode indicator */}
          {(compare.a || compare.b) && (
            <div className="flex items-center gap-1 px-2 py-1 rounded text-xs" style={{ background: 'rgba(167,139,250,0.15)', color: '#a78bfa' }}>
              <ArrowLeftRight className="w-3 h-3" />
              <span>
                {compare.a && !compare.b
                  ? 'Select 2nd checkpoint'
                  : 'Comparing'}
              </span>
              <button onClick={clearCompare} className="ml-1 hover:opacity-70">
                <X className="w-3 h-3" />
              </button>
            </div>
          )}

          <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
            {checkpoints.length} checkpoints · {auditEntries.length} events
          </span>
        </div>
      </div>

      {/* Compare panel */}
      {showCompare && compare.a && compare.b && (
        <ComparePanel a={compare.a} b={compare.b} onClose={clearCompare} />
      )}

      {/* Timeline */}
      <div className="relative pl-6">
        {/* Vertical line */}
        <div
          className="absolute left-[11px] top-0 bottom-0 w-px"
          style={{ background: 'var(--border-subtle)' }}
        />

        {combinedTimeline.map((item, idx) => {
          if (item.type === 'checkpoint') {
            const cp = item.data as CheckpointEntry
            const isExpanded = expandedCheckpoints[cp.id]
            const isCompareSelected = compare.a?.id === cp.id || compare.b?.id === cp.id
            return (
              <CheckpointNode
                key={`cp-${cp.id}`}
                checkpoint={cp}
                isExpanded={isExpanded}
                isCompareSelected={isCompareSelected}
                onToggle={() => toggleCheckpoint(cp.id)}
                onFork={(agentName) => restartMutation.mutate(agentName)}
                onCompare={() => handleCompareSelect(cp)}
                isForking={restartMutation.isPending}
              />
            )
          } else {
            const entry = item.data as AuditLogEntry
            return <AuditNode key={`audit-${entry.id}`} entry={entry} />
          }
        })}
      </div>
    </div>
  )
}

// ── Checkpoint node ───────────────────────────────────────────────

interface CheckpointNodeProps {
  checkpoint: CheckpointEntry
  isExpanded: boolean
  isCompareSelected: boolean
  onToggle: () => void
  onFork: (agentName: string) => void
  onCompare: () => void
  isForking: boolean
}

function CheckpointNode({
  checkpoint: cp,
  isExpanded,
  isCompareSelected,
  onToggle,
  onFork,
  onCompare,
  isForking,
}: CheckpointNodeProps) {
  const agentLabel = AGENT_LABELS[cp.agent_name] || cp.agent_name.replace(/_/g, ' ')
  const statusColor = cp.agent_status === 'completed' ? '#4ade80' : cp.agent_status === 'failed' ? '#f87171' : '#fbbf24'

  return (
    <div className="relative mb-3">
      {/* Node dot */}
      <div
        className="absolute -left-[13px] top-2 w-5 h-5 rounded-full flex items-center justify-center z-10"
        style={{
          background: isCompareSelected ? 'rgba(167,139,250,0.3)' : 'rgba(167,139,250,0.15)',
          border: isCompareSelected ? '2px solid #a78bfa' : '2px solid rgba(167,139,250,0.4)',
        }}
      >
        <GitCommit className="w-3 h-3" style={{ color: '#a78bfa' }} />
      </div>

      {/* Card */}
      <div
        className="ml-4 rounded-lg border transition-colors"
        style={{
          background: 'var(--background-secondary)',
          borderColor: isCompareSelected ? '#a78bfa' : 'var(--border-subtle)',
        }}
      >
        {/* Header */}
        <button
          onClick={onToggle}
          className="w-full flex items-center justify-between px-3 py-2 text-left"
        >
          <div className="flex items-center gap-2 min-w-0">
            {isExpanded ? (
              <ChevronDown className="w-3.5 h-3.5 flex-shrink-0" style={{ color: 'var(--text-tertiary)' }} />
            ) : (
              <ChevronRight className="w-3.5 h-3.5 flex-shrink-0" style={{ color: 'var(--text-tertiary)' }} />
            )}
            <span className="text-xs font-medium truncate" style={{ color: 'var(--text-primary)' }}>
              Step {cp.step_number}: {agentLabel}
            </span>
            <span
              className="text-[10px] px-1.5 py-0.5 rounded font-medium flex-shrink-0"
              style={{ background: `${statusColor}20`, color: statusColor }}
            >
              {cp.agent_status}
            </span>
          </div>
          <div className="flex items-center gap-3 flex-shrink-0 ml-2">
            <span className="text-[10px] flex items-center gap-1" style={{ color: 'var(--text-tertiary)' }}>
              <DollarSign className="w-3 h-3" />
              ${cp.total_cost?.toFixed(4) || '0'}
            </span>
            <span className="text-[10px] flex items-center gap-1" style={{ color: 'var(--text-tertiary)' }}>
              <Clock className="w-3 h-3" />
              {formatTime(cp.created_at)}
            </span>
          </div>
        </button>

        {/* Expanded content */}
        {isExpanded && (
          <div className="px-3 pb-3 border-t" style={{ borderColor: 'var(--border-subtle)' }}>
            <div className="pt-2 space-y-2">
              {/* Node states */}
              {cp.node_states && (
                <div>
                  <p className="text-[10px] font-medium mb-1" style={{ color: 'var(--text-tertiary)' }}>
                    Pipeline State at This Checkpoint
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(cp.node_states).map(([nodeId, state]) => {
                      const s = (state as any)?.status || 'pending'
                      const col =
                        s === 'completed' ? '#4ade80' :
                        s === 'failed' ? '#f87171' :
                        s === 'running' ? '#60a5fa' :
                        s === 'skipped' ? '#6b7280' :
                        'var(--text-tertiary)'
                      return (
                        <span
                          key={nodeId}
                          className="text-[10px] px-1.5 py-0.5 rounded"
                          style={{ background: `${col}15`, color: col }}
                          title={`${nodeId}: ${s}`}
                        >
                          {(AGENT_LABELS[nodeId] || nodeId).slice(0, 12)}
                        </span>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* Cost breakdown */}
              {cp.cost_breakdown && Object.keys(cp.cost_breakdown).length > 0 && (
                <div>
                  <p className="text-[10px] font-medium mb-1" style={{ color: 'var(--text-tertiary)' }}>
                    Cost Breakdown
                  </p>
                  <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
                    {Object.entries(cp.cost_breakdown).map(([agent, cost]) => (
                      <div key={agent} className="flex justify-between text-[10px]">
                        <span style={{ color: 'var(--text-secondary)' }}>{AGENT_LABELS[agent] || agent}</span>
                        <span style={{ color: 'var(--text-tertiary)' }}>${(cost as number).toFixed(4)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center gap-2 pt-1">
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onFork(cp.agent_name)
                  }}
                  disabled={isForking}
                  className="flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium transition-colors hover:opacity-80 disabled:opacity-50"
                  style={{ background: 'rgba(74,222,128,0.15)', color: '#4ade80' }}
                  title="Fork from this checkpoint — restart the pipeline from this agent"
                >
                  <GitBranch className="w-3 h-3" />
                  Fork from here
                </button>

                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onCompare()
                  }}
                  className="flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium transition-colors hover:opacity-80"
                  style={{ background: 'rgba(167,139,250,0.15)', color: '#a78bfa' }}
                  title="Select this checkpoint for comparison"
                >
                  <ArrowLeftRight className="w-3 h-3" />
                  Compare
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Audit log node ────────────────────────────────────────────────

function AuditNode({ entry }: { entry: AuditLogEntry }) {
  const [expanded, setExpanded] = useState(false)
  const style = eventStyle(entry.event_type)
  const Icon = style.icon

  return (
    <div className="relative mb-2">
      {/* Node dot */}
      <div
        className="absolute -left-[11px] top-1.5 w-4 h-4 rounded-full flex items-center justify-center z-10"
        style={{ background: style.bg, border: `1.5px solid ${style.color}40` }}
      >
        <Icon className="w-2.5 h-2.5" style={{ color: style.color }} />
      </div>

      {/* Content */}
      <div className="ml-4 py-1">
        <button
          onClick={() => entry.details && setExpanded(!expanded)}
          className="flex items-center gap-2 w-full text-left"
        >
          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded" style={{ background: style.bg, color: style.color }}>
            {entry.event_type.replace(/_/g, ' ')}
          </span>
          <span className="text-xs truncate" style={{ color: 'var(--text-secondary)' }}>
            {entry.message}
          </span>
          {entry.agent_name && (
            <span className="text-[10px] flex-shrink-0" style={{ color: 'var(--text-tertiary)' }}>
              {AGENT_LABELS[entry.agent_name] || entry.agent_name}
            </span>
          )}
          <span className="text-[10px] ml-auto flex-shrink-0" style={{ color: 'var(--text-tertiary)' }}>
            {formatTime(entry.timestamp)}
            {entry.duration_ms ? ` (${formatDuration(entry.duration_ms)})` : ''}
          </span>
        </button>

        {expanded && entry.details && (
          <div
            className="mt-1 ml-0.5 p-2 rounded text-[10px] font-mono overflow-auto max-h-32"
            style={{ background: 'var(--background-tertiary)', color: 'var(--text-tertiary)' }}
          >
            <pre className="whitespace-pre-wrap">{JSON.stringify(entry.details, null, 2)}</pre>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Compare panel ─────────────────────────────────────────────────

function ComparePanel({
  a,
  b,
  onClose,
}: {
  a: CheckpointEntry
  b: CheckpointEntry
  onClose: () => void
}) {
  const labelA = `Step ${a.step_number}: ${AGENT_LABELS[a.agent_name] || a.agent_name}`
  const labelB = `Step ${b.step_number}: ${AGENT_LABELS[b.agent_name] || b.agent_name}`

  // Compare node states
  const allNodes = useMemo(() => {
    const keys = new Set([
      ...Object.keys(a.node_states || {}),
      ...Object.keys(b.node_states || {}),
    ])
    return [...keys].sort()
  }, [a, b])

  return (
    <div
      className="rounded-lg border p-4"
      style={{ background: 'var(--background-secondary)', borderColor: '#a78bfa40' }}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <ArrowLeftRight className="w-4 h-4" style={{ color: '#a78bfa' }} />
          <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
            Checkpoint Comparison
          </span>
        </div>
        <button onClick={onClose} className="p-1 rounded hover:opacity-70" style={{ color: 'var(--text-tertiary)' }}>
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Summary row */}
      <div className="grid grid-cols-2 gap-4 mb-3">
        <div className="rounded p-2" style={{ background: 'rgba(96,165,250,0.1)', border: '1px solid rgba(96,165,250,0.2)' }}>
          <p className="text-xs font-medium" style={{ color: '#60a5fa' }}>{labelA}</p>
          <p className="text-[10px] mt-0.5" style={{ color: 'var(--text-tertiary)' }}>
            {formatDate(a.created_at)} · Cost: ${a.total_cost?.toFixed(4)}
          </p>
        </div>
        <div className="rounded p-2" style={{ background: 'rgba(167,139,250,0.1)', border: '1px solid rgba(167,139,250,0.2)' }}>
          <p className="text-xs font-medium" style={{ color: '#a78bfa' }}>{labelB}</p>
          <p className="text-[10px] mt-0.5" style={{ color: 'var(--text-tertiary)' }}>
            {formatDate(b.created_at)} · Cost: ${b.total_cost?.toFixed(4)}
          </p>
        </div>
      </div>

      {/* State diff table */}
      <div className="overflow-auto max-h-64">
        <table className="w-full text-[10px]">
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <th className="text-left py-1 pr-2 font-medium" style={{ color: 'var(--text-tertiary)' }}>Agent</th>
              <th className="text-center py-1 px-2 font-medium" style={{ color: '#60a5fa' }}>A</th>
              <th className="text-center py-1 px-2 font-medium" style={{ color: '#a78bfa' }}>B</th>
              <th className="text-center py-1 pl-2 font-medium" style={{ color: 'var(--text-tertiary)' }}>Diff</th>
            </tr>
          </thead>
          <tbody>
            {allNodes.map((nodeId) => {
              const stateA = (a.node_states?.[nodeId] as any)?.status || 'n/a'
              const stateB = (b.node_states?.[nodeId] as any)?.status || 'n/a'
              const changed = stateA !== stateB
              return (
                <tr key={nodeId} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <td className="py-1 pr-2" style={{ color: 'var(--text-secondary)' }}>
                    {(AGENT_LABELS[nodeId] || nodeId).slice(0, 20)}
                  </td>
                  <td className="text-center py-1 px-2">
                    <StatusBadge status={stateA} />
                  </td>
                  <td className="text-center py-1 px-2">
                    <StatusBadge status={stateB} />
                  </td>
                  <td className="text-center py-1 pl-2">
                    {changed && (
                      <span style={{ color: '#fbbf24' }}>changed</span>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Cost comparison */}
      <div className="mt-3 pt-2 flex gap-6" style={{ borderTop: '1px solid var(--border-subtle)' }}>
        <div>
          <span className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>Cost diff: </span>
          <span className="text-xs font-medium" style={{ color: (b.total_cost - a.total_cost) > 0 ? '#f87171' : '#4ade80' }}>
            {(b.total_cost - a.total_cost) > 0 ? '+' : ''}${(b.total_cost - a.total_cost).toFixed(4)}
          </span>
        </div>
        <div>
          <span className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>Steps diff: </span>
          <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
            {b.step_number - a.step_number} steps
          </span>
        </div>
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const color =
    status === 'completed' ? '#4ade80' :
    status === 'failed' ? '#f87171' :
    status === 'running' ? '#60a5fa' :
    status === 'skipped' ? '#6b7280' :
    'var(--text-tertiary)'

  return (
    <span className="text-[10px] px-1 py-0.5 rounded" style={{ background: `${color}15`, color }}>
      {status}
    </span>
  )
}
