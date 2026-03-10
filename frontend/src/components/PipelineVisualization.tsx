import { clsx } from 'clsx'
import { Check, Loader2, AlertCircle, Clock } from 'lucide-react'

type AgentStatus = 'queued' | 'active' | 'completed' | 'failed'

interface Agent {
  name: string
  status: AgentStatus
  duration?: number
  cost?: number
}

interface PipelineVisualizationProps {
  agents: Agent[]
  className?: string
}

export function PipelineVisualization({ agents, className }: PipelineVisualizationProps) {
  return (
    <div className={clsx('w-full', className)}>
      {/* Mobile: Vertical Timeline */}
      <div className="lg:hidden space-y-4">
        {agents.map((agent, index) => (
          <div key={agent.name} className="flex items-start gap-4">
            <div className="flex flex-col items-center">
              <AgentNode status={agent.status} />
              {index < agents.length - 1 && (
                <div className="w-0.5 h-8 bg-border-subtle mt-2" />
              )}
            </div>
            <div className="flex-1 pt-1">
              <p className="font-medium text-text-primary">{agent.name}</p>
              <div className="flex gap-4 mt-1 text-xs text-text-secondary">
                {agent.duration && <span>{agent.duration}ms</span>}
                {agent.cost && <span>${agent.cost.toFixed(4)}</span>}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Desktop: Horizontal Flow */}
      <div className="hidden lg:flex items-center justify-between">
        {agents.map((agent, index) => (
          <div key={agent.name} className="flex items-center flex-1">
            <div className="flex flex-col items-center">
              <AgentNode status={agent.status} />
              <p className="mt-2 text-sm font-medium text-text-primary">{agent.name}</p>
              <div className="flex gap-2 mt-1 text-xs text-text-secondary">
                {agent.duration && <span>{agent.duration}ms</span>}
                {agent.cost && <span>${agent.cost.toFixed(4)}</span>}
              </div>
            </div>
            {index < agents.length - 1 && (
              <div className="flex-1 h-0.5 bg-border-subtle mx-4" />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function AgentNode({ status }: { status: AgentStatus }) {
  return (
    <div
      className={clsx(
        'w-10 h-10 rounded-full flex items-center justify-center',
        status === 'queued' && 'bg-background-tertiary text-text-tertiary',
        status === 'active' && 'bg-accent-primary/20 text-accent-primary ring-2 ring-accent-primary animate-pulse',
        status === 'completed' && 'bg-accent-success/20 text-accent-success',
        status === 'failed' && 'bg-accent-error/20 text-accent-error'
      )}
    >
      {status === 'queued' && <Clock className="w-5 h-5" />}
      {status === 'active' && <Loader2 className="w-5 h-5 animate-spin" />}
      {status === 'completed' && <Check className="w-5 h-5" />}
      {status === 'failed' && <AlertCircle className="w-5 h-5" />}
    </div>
  )
}
