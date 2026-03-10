import { useQuery } from '@tanstack/react-query'
import { Card } from '@/components/Card'
import { api } from '@/lib/api'
import { DollarSign, TrendingUp, Zap, Clock } from 'lucide-react'

export default function CostDashboard() {
  const { data: summary } = useQuery({
    queryKey: ['costSummary'],
    queryFn: api.getCostSummary,
  })

  const { data: byAgent } = useQuery({
    queryKey: ['costsByAgent'],
    queryFn: api.getCostsByAgent,
  })

  const { data: byModel } = useQuery({
    queryKey: ['costsByModel'],
    queryFn: api.getCostsByModel,
  })

  const { data: trends } = useQuery({
    queryKey: ['costTrends'],
    queryFn: () => api.getCostTrends(30),
  })

  return (
    <div className="space-y-6 pb-20 lg:pb-0">
      <div>
        <h2 className="text-2xl font-semibold text-text-primary">Cost Dashboard</h2>
        <p className="text-text-secondary mt-1">Track your AI spending</p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card padding="sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-accent-primary/20 flex items-center justify-center">
              <DollarSign className="w-5 h-5 text-accent-primary" />
            </div>
            <div>
              <p className="text-xl font-semibold text-text-primary">
                ${summary?.total_cost?.toFixed(2) || '0.00'}
              </p>
              <p className="text-xs text-text-secondary">Total Spent</p>
            </div>
          </div>
        </Card>
        <Card padding="sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-accent-success/20 flex items-center justify-center">
              <Zap className="w-5 h-5 text-accent-success" />
            </div>
            <div>
              <p className="text-xl font-semibold text-text-primary">
                {summary?.project_count || 0}
              </p>
              <p className="text-xs text-text-secondary">Projects</p>
            </div>
          </div>
        </Card>
        <Card padding="sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-accent-secondary/20 flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-accent-secondary" />
            </div>
            <div>
              <p className="text-xl font-semibold text-text-primary">
                ${summary?.avg_cost_per_project?.toFixed(2) || '0.00'}
              </p>
              <p className="text-xs text-text-secondary">Avg / Project</p>
            </div>
          </div>
        </Card>
        <Card padding="sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-accent-warning/20 flex items-center justify-center">
              <Clock className="w-5 h-5 text-accent-warning" />
            </div>
            <div>
              <p className="text-xl font-semibold text-text-primary">
                ${(trends?.reduce((a, t) => a + t.daily_cost, 0) || 0).toFixed(2)}
              </p>
              <p className="text-xs text-text-secondary">Last 30 Days</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Cost by Agent */}
      <Card>
        <h3 className="font-medium text-text-primary mb-4">Cost by Agent</h3>
        <div className="space-y-3">
          {byAgent?.map((agent) => (
            <div key={agent.agent_name} className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-accent-primary" />
                <span className="text-sm text-text-primary capitalize">
                  {agent.agent_name.replace('_', ' ')}
                </span>
              </div>
              <div className="flex items-center gap-4 text-sm">
                <span className="text-text-tertiary">{agent.call_count} calls</span>
                <span className="text-text-primary font-mono">
                  ${agent.total_cost.toFixed(4)}
                </span>
              </div>
            </div>
          ))}
          {(!byAgent || byAgent.length === 0) && (
            <p className="text-sm text-text-secondary text-center py-4">No data yet</p>
          )}
        </div>
      </Card>

      {/* Cost by Model */}
      <Card>
        <h3 className="font-medium text-text-primary mb-4">Cost by Model</h3>
        <div className="space-y-3">
          {byModel?.map((model) => (
            <div key={model.model} className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-accent-secondary" />
                <code className="text-sm text-text-primary">
                  {model.model.split('/').pop()}
                </code>
              </div>
              <div className="flex items-center gap-4 text-sm">
                <span className="text-text-tertiary">
                  {(model.prompt_tokens + model.completion_tokens).toLocaleString()} tokens
                </span>
                <span className="text-text-primary font-mono">
                  ${model.total_cost.toFixed(4)}
                </span>
              </div>
            </div>
          ))}
          {(!byModel || byModel.length === 0) && (
            <p className="text-sm text-text-secondary text-center py-4">No data yet</p>
          )}
        </div>
      </Card>
    </div>
  )
}
