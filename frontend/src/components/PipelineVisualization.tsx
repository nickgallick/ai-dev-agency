import { clsx } from 'clsx'
import { Check, Loader2, AlertCircle, Clock, ChevronRight } from 'lucide-react'
import { useState, useEffect, useRef } from 'react'

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

/** Names that indicate parallel batches */
const PARALLEL_BATCHES: string[][] = [
  ['Asset', 'Content'],
  ['Security', 'SEO', 'Access'],
  ['Monitor', 'Standard'],
]

interface PipelineStep {
  type: 'single' | 'parallel'
  agents: Agent[]
}

function groupIntoPipelineSteps(agents: Agent[]): PipelineStep[] {
  const steps: PipelineStep[] = []
  const consumed = new Set<number>()

  for (let i = 0; i < agents.length; i++) {
    if (consumed.has(i)) continue

    // Check if this agent starts a parallel batch
    const batch = PARALLEL_BATCHES.find((keywords) =>
      keywords.some((kw) => agents[i].name.toLowerCase().includes(kw.toLowerCase()))
    )

    if (batch) {
      // Collect all agents in this batch that are adjacent (or nearby)
      const parallelAgents: Agent[] = []
      const batchIndices: number[] = []
      for (let j = i; j < agents.length; j++) {
        if (
          batch.some((kw) =>
            agents[j].name.toLowerCase().includes(kw.toLowerCase())
          )
        ) {
          parallelAgents.push(agents[j])
          batchIndices.push(j)
        }
      }
      if (parallelAgents.length > 1) {
        batchIndices.forEach((idx) => consumed.add(idx))
        steps.push({ type: 'parallel', agents: parallelAgents })
        continue
      }
    }

    // Sequential agent
    consumed.add(i)
    steps.push({ type: 'single', agents: [agents[i]] })
  }

  return steps
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  const seconds = ms / 1000
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = Math.round(seconds % 60)
  return `${minutes}m ${remainingSeconds}s`
}

function StatusIcon({ status }: { status: AgentStatus }) {
  switch (status) {
    case 'queued':
      return <Clock className="w-4 h-4" />
    case 'active':
      return <Loader2 className="w-4 h-4 animate-spin" />
    case 'completed':
      return <Check className="w-4 h-4" />
    case 'failed':
      return <AlertCircle className="w-4 h-4" />
  }
}

function AgentCard({
  agent,
  innerRef,
}: {
  agent: Agent
  innerRef?: React.Ref<HTMLDivElement>
}) {
  return (
    <div
      ref={innerRef}
      className={clsx(
        'rounded-lg border p-3 transition-all duration-500 ease-in-out min-w-0',
        // Queued
        agent.status === 'queued' &&
          'bg-background-tertiary border-border-subtle opacity-60',
        // Active — pulsing border
        agent.status === 'active' &&
          'bg-accent-primary/10 border-accent-primary ring-2 ring-accent-primary/50 animate-pulse shadow-md',
        // Completed
        agent.status === 'completed' &&
          'bg-accent-success/10 border-accent-success/40',
        // Failed
        agent.status === 'failed' &&
          'bg-accent-error/10 border-accent-error/40'
      )}
    >
      {/* Header row: icon + name */}
      <div className="flex items-center gap-2">
        <span
          className={clsx(
            'flex-shrink-0 flex items-center justify-center w-6 h-6 rounded-full',
            agent.status === 'queued' && 'text-text-tertiary',
            agent.status === 'active' && 'text-accent-primary',
            agent.status === 'completed' && 'text-accent-success',
            agent.status === 'failed' && 'text-accent-error'
          )}
        >
          <StatusIcon status={agent.status} />
        </span>
        <span className="font-medium text-sm text-text-primary truncate">
          {agent.name}
        </span>
      </div>

      {/* Meta row */}
      {(agent.duration != null || agent.cost != null) && (
        <div className="mt-1.5 ml-8 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-text-secondary">
          {agent.duration != null && <span>{formatDuration(agent.duration)}</span>}
          {agent.cost != null && <span>${agent.cost.toFixed(4)}</span>}
        </div>
      )}

      {/* Summary */}
      {agent.summary && (
        <p className="mt-1.5 ml-8 text-xs text-text-secondary line-clamp-2">
          {agent.summary}
        </p>
      )}
    </div>
  )
}

function ProgressBar({ agents }: { agents: Agent[] }) {
  const completed = agents.filter((a) => a.status === 'completed').length
  const failed = agents.filter((a) => a.status === 'failed').length
  const total = agents.length
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0

  return (
    <div className="mb-5">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-sm font-medium text-text-primary">
          Pipeline Progress
        </span>
        <span className="text-sm text-text-secondary">
          {completed}/{total} agents complete
          {failed > 0 && (
            <span className="text-accent-error ml-1">({failed} failed)</span>
          )}
          {' — '}
          {pct}%
        </span>
      </div>
      <div className="w-full h-2 rounded-full bg-background-tertiary overflow-hidden">
        <div
          className={clsx(
            'h-full rounded-full transition-all duration-700 ease-out',
            failed > 0 ? 'bg-accent-error' : 'bg-accent-primary'
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

export function PipelineVisualization({
  agents,
  className,
}: PipelineVisualizationProps) {
  const steps = groupIntoPipelineSteps(agents)
  const activeRef = useRef<HTMLDivElement | null>(null)
  const scrollContainerRef = useRef<HTMLDivElement | null>(null)

  // Auto-scroll active agent into view
  useEffect(() => {
    if (activeRef.current) {
      activeRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
        inline: 'nearest',
      })
    }
  }, [agents])

  // Find the first active agent name to assign the ref
  const activeAgentName = agents.find((a) => a.status === 'active')?.name

  return (
    <div className={clsx('w-full', className)}>
      {/* Overall progress bar */}
      <ProgressBar agents={agents} />

      {/* Mobile: vertical card list */}
      <div className="lg:hidden space-y-2" ref={scrollContainerRef}>
        {steps.map((step, stepIdx) => (
          <div key={stepIdx}>
            {step.type === 'parallel' ? (
              <div className="flex gap-2">
                {step.agents.map((agent) => (
                  <div key={agent.name} className="flex-1 min-w-0">
                    <AgentCard
                      agent={agent}
                      innerRef={
                        agent.name === activeAgentName ? activeRef : undefined
                      }
                    />
                  </div>
                ))}
              </div>
            ) : (
              <AgentCard
                agent={step.agents[0]}
                innerRef={
                  step.agents[0].name === activeAgentName
                    ? activeRef
                    : undefined
                }
              />
            )}

            {/* Connector */}
            {stepIdx < steps.length - 1 && (
              <div className="flex justify-center py-1">
                <ChevronRight className="w-4 h-4 text-border-subtle rotate-90" />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Desktop: grid layout with connectors */}
      <div
        className="hidden lg:flex flex-wrap items-center gap-y-3"
        ref={scrollContainerRef}
      >
        {steps.map((step, stepIdx) => (
          <div key={stepIdx} className="flex items-center">
            {step.type === 'parallel' ? (
              <div className="flex flex-col gap-2">
                {step.agents.map((agent) => (
                  <div key={agent.name} className="w-48">
                    <AgentCard
                      agent={agent}
                      innerRef={
                        agent.name === activeAgentName ? activeRef : undefined
                      }
                    />
                  </div>
                ))}
              </div>
            ) : (
              <div className="w-48">
                <AgentCard
                  agent={step.agents[0]}
                  innerRef={
                    step.agents[0].name === activeAgentName
                      ? activeRef
                      : undefined
                  }
                />
              </div>
            )}

            {/* Connector arrow between steps */}
            {stepIdx < steps.length - 1 && (
              <div className="flex items-center px-1.5 text-border-subtle">
                <div className="w-4 h-px bg-border-subtle" />
                <ChevronRight className="w-4 h-4 -ml-1" />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
