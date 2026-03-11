import { useEffect, useRef } from 'react'
import { clsx } from 'clsx'
import { Check, Loader2, AlertCircle, Clock } from 'lucide-react'

type AgentStatus = 'queued' | 'active' | 'completed' | 'failed'

interface Agent {
  name: string
  status: AgentStatus
  duration?: number
  cost?: number
  summary?: string
}

interface PipelineVisualizationProps {
  agents: Agent[]
  className?: string
}

// Names of agents that should render in parallel (side-by-side)
const PARALLEL_GROUPS: string[][] = [
  ['Monitoring', 'Standards'],
]

function getParallelGroup(name: string): string[] | null {
  return PARALLEL_GROUPS.find((g) => g.includes(name)) || null
}

function isGroupLeader(name: string): boolean {
  return PARALLEL_GROUPS.some((g) => g[0] === name)
}

function AgentCard({ agent, compact = false }: { agent: Agent; compact?: boolean }) {
  const isActive = agent.status === 'active'
  const isCompleted = agent.status === 'completed'
  const isFailed = agent.status === 'failed'

  return (
    <div
      className={clsx(
        'relative rounded-xl border transition-all duration-300',
        compact ? 'p-3' : 'p-4',
        isActive && 'border-accent-primary bg-accent-primary/5 shadow-lg shadow-accent-primary/10',
        isCompleted && 'border-accent-success/30 bg-accent-success/5',
        isFailed && 'border-accent-error/30 bg-accent-error/5',
        !isActive && !isCompleted && !isFailed && 'border-border-subtle bg-bg-secondary',
      )}
    >
      {/* Active animated ring */}
      {isActive && (
        <div className="absolute inset-0 rounded-xl border-2 border-accent-primary animate-pulse pointer-events-none" />
      )}

      <div className="flex items-center gap-3">
        {/* Status icon */}
        <div
          className={clsx(
            'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
            isActive && 'bg-accent-primary/20 text-accent-primary',
            isCompleted && 'bg-accent-success/20 text-accent-success',
            isFailed && 'bg-accent-error/20 text-accent-error',
            !isActive && !isCompleted && !isFailed && 'bg-bg-primary text-text-tertiary',
          )}
        >
          {agent.status === 'queued' && <Clock className="w-4 h-4" />}
          {agent.status === 'active' && <Loader2 className="w-4 h-4 animate-spin" />}
          {agent.status === 'completed' && <Check className="w-4 h-4" />}
          {agent.status === 'failed' && <AlertCircle className="w-4 h-4" />}
        </div>

        {/* Name + meta */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span
              className={clsx(
                'text-sm font-medium truncate',
                isActive && 'text-accent-primary',
                isCompleted && 'text-text-primary',
                isFailed && 'text-accent-error',
                !isActive && !isCompleted && !isFailed && 'text-text-tertiary',
              )}
            >
              {agent.name}
            </span>
            <StatusPill status={agent.status} />
          </div>
          {/* Duration / cost */}
          {(agent.duration || agent.cost) && (
            <div className="flex gap-3 mt-0.5 text-xs text-text-tertiary">
              {agent.duration && <span>{(agent.duration / 1000).toFixed(1)}s</span>}
              {agent.cost && <span>${agent.cost.toFixed(4)}</span>}
            </div>
          )}
          {/* Summary */}
          {agent.summary && (
            <p className="text-xs text-text-secondary mt-1 truncate">{agent.summary}</p>
          )}
        </div>
      </div>
    </div>
  )
}

function StatusPill({ status }: { status: AgentStatus }) {
  if (status === 'queued') return null
  return (
    <span
      className={clsx(
        'text-xs px-1.5 py-0.5 rounded font-medium flex-shrink-0',
        status === 'active' && 'bg-accent-primary/20 text-accent-primary',
        status === 'completed' && 'bg-accent-success/20 text-accent-success',
        status === 'failed' && 'bg-accent-error/20 text-accent-error',
      )}
    >
      {status}
    </span>
  )
}

function Connector({ completed }: { completed: boolean }) {
  return (
    <div className="flex justify-center my-1">
      <div
        className={clsx(
          'w-0.5 h-4 rounded-full transition-colors duration-300',
          completed ? 'bg-accent-success/50' : 'bg-border-subtle',
        )}
      />
    </div>
  )
}

export function PipelineVisualization({ agents, className }: PipelineVisualizationProps) {
  const activeRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to active agent
  useEffect(() => {
    if (activeRef.current) {
      activeRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [agents])

  const completedCount = agents.filter((a) => a.status === 'completed').length
  const totalCount = agents.length
  const progressPct = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0
  const activeAgent = agents.find((a) => a.status === 'active')
  const failedAgents = agents.filter((a) => a.status === 'failed')

  // Build rendered rows (group parallel agents)
  type Row = { parallel: boolean; items: Agent[] }
  const rows: Row[] = []
  const seen = new Set<string>()

  for (const agent of agents) {
    if (seen.has(agent.name)) continue
    const group = getParallelGroup(agent.name)
    if (group && isGroupLeader(agent.name)) {
      // Collect all agents in this parallel group
      const groupAgents = group
        .map((name) => agents.find((a) => a.name === name))
        .filter(Boolean) as Agent[]
      rows.push({ parallel: true, items: groupAgents })
      group.forEach((n) => seen.add(n))
    } else if (!group) {
      rows.push({ parallel: false, items: [agent] })
      seen.add(agent.name)
    } else {
      // Part of a group but not the leader — already added
      seen.add(agent.name)
    }
  }

  return (
    <div className={clsx('space-y-2', className)}>
      {/* Progress bar */}
      <div className="flex items-center gap-3 mb-4">
        <div className="flex-1 h-2 bg-bg-secondary rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-accent-primary to-accent-success rounded-full transition-all duration-700 ease-out"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <span className="text-sm font-medium text-text-secondary whitespace-nowrap">
          {completedCount}/{totalCount}
          <span className="text-text-tertiary ml-1">({progressPct}%)</span>
        </span>
      </div>

      {/* Status summary */}
      {activeAgent && (
        <div className="flex items-center gap-2 px-3 py-2 bg-accent-primary/10 rounded-lg border border-accent-primary/20 mb-3">
          <Loader2 className="w-4 h-4 text-accent-primary animate-spin" />
          <span className="text-sm text-accent-primary font-medium">
            Running: {activeAgent.name}
          </span>
        </div>
      )}
      {failedAgents.length > 0 && (
        <div className="flex items-center gap-2 px-3 py-2 bg-accent-error/10 rounded-lg border border-accent-error/20 mb-3">
          <AlertCircle className="w-4 h-4 text-accent-error" />
          <span className="text-sm text-accent-error font-medium">
            Failed: {failedAgents.map((a) => a.name).join(', ')}
          </span>
        </div>
      )}

      {/* Rows */}
      {rows.map((row, rowIdx) => {
        const rowIsActive = row.items.some((a) => a.status === 'active')
        const prevRowCompleted =
          rowIdx === 0
            ? true
            : rows[rowIdx - 1].items.every((a) => a.status === 'completed')

        return (
          <div key={rowIdx}>
            {rowIdx > 0 && <Connector completed={prevRowCompleted} />}

            {row.parallel ? (
              /* Parallel group — side by side */
              <div
                ref={rowIsActive ? activeRef : undefined}
                className="grid gap-2"
                style={{ gridTemplateColumns: `repeat(${row.items.length}, 1fr)` }}
              >
                {row.items.map((agent) => (
                  <AgentCard key={agent.name} agent={agent} compact />
                ))}
              </div>
            ) : (
              /* Sequential */
              <div ref={rowIsActive ? activeRef : undefined}>
                <AgentCard agent={row.items[0]} />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
