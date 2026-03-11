import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card } from '@/components/Card'
import { api, type Project, type AgentLog } from '@/lib/api'
import {
  DollarSign, TrendingUp, Zap, Clock, Trophy, BarChart3,
  AlertTriangle, Target, CheckCircle2, XCircle, Timer, Flame, FolderOpen
} from 'lucide-react'

type TabType = 'overview' | 'per-project' | 'agents' | 'models' | 'build-time' | 'issues' | 'accuracy'

const DATE_RANGE_OPTIONS = [
  { label: 'Today', days: 1 },
  { label: '7 Days', days: 7 },
  { label: '30 Days', days: 30 },
  { label: '90 Days', days: 90 },
] as const

export default function CostDashboard() {
  const [activeTab, setActiveTab] = useState<TabType>('overview')
  const [days, setDays] = useState<number>(30)
  const [customFrom, setCustomFrom] = useState('')
  const [customTo, setCustomTo] = useState('')
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null)

  // Existing cost queries
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
    queryKey: ['costTrends', days],
    queryFn: () => api.getCostTrends(days),
  })

  // Phase 9A: New analytics queries — all keyed on `days`
  const { data: analyticsSummary } = useQuery({
    queryKey: ['analyticsSummary', days],
    queryFn: () => api.getAnalyticsSummary(days),
  })

  const { data: successRates } = useQuery({
    queryKey: ['agentSuccessRates', days],
    queryFn: () => api.getAgentSuccessRates(days, 20),
  })

  const { data: modelComparison } = useQuery({
    queryKey: ['modelComparison', days],
    queryFn: () => api.getModelComparison(undefined, days),
  })

  const { data: buildTimeWaterfall } = useQuery({
    queryKey: ['buildTimeWaterfall', days],
    queryFn: () => api.getBuildTimeWaterfall(undefined, days),
  })

  const { data: failurePatterns } = useQuery({
    queryKey: ['qaFailurePatterns'],
    queryFn: () => api.getQAFailurePatterns(10, false),
  })

  const { data: costAccuracy } = useQuery({
    queryKey: ['costAccuracy', days],
    queryFn: () => api.getCostAccuracyStats(undefined, undefined, days),
  })

  // Per-project queries
  const { data: projects } = useQuery({
    queryKey: ['projects-cost-dashboard'],
    queryFn: () => api.getProjects({ limit: 50 }),
    enabled: activeTab === 'per-project',
  })

  const { data: projectAgentLogs } = useQuery({
    queryKey: ['agentLogs', selectedProjectId],
    queryFn: () => api.getAgentLogs({ project_id: selectedProjectId! }),
    enabled: !!selectedProjectId,
  })

  // Compute total cost for flame icon thresholds
  const totalAgentCost = useMemo(() => {
    if (!byAgent || byAgent.length === 0) return 0
    return byAgent.reduce((sum, a) => sum + a.total_cost, 0)
  }, [byAgent])

  const totalModelCost = useMemo(() => {
    if (!byModel || byModel.length === 0) return 0
    return byModel.reduce((sum, m) => sum + m.total_cost, 0)
  }, [byModel])

  // Per-project cost breakdown from agent logs
  const projectCostBreakdown = useMemo(() => {
    if (!projectAgentLogs || projectAgentLogs.length === 0) return []
    const map: Record<string, { agent_name: string; total_cost: number; call_count: number }> = {}
    for (const log of projectAgentLogs) {
      if (!map[log.agent_name]) {
        map[log.agent_name] = { agent_name: log.agent_name, total_cost: 0, call_count: 0 }
      }
      map[log.agent_name].total_cost += log.cost
      map[log.agent_name].call_count += 1
    }
    return Object.values(map).sort((a, b) => b.total_cost - a.total_cost)
  }, [projectAgentLogs])

  const selectedProject = useMemo(() => {
    if (!selectedProjectId || !projects) return null
    return projects.find(p => p.id === selectedProjectId) || null
  }, [selectedProjectId, projects])

  const handleApplyCustomRange = () => {
    if (customFrom && customTo) {
      const from = new Date(customFrom)
      const to = new Date(customTo)
      const diffMs = to.getTime() - from.getTime()
      const diffDays = Math.max(1, Math.ceil(diffMs / (1000 * 60 * 60 * 24)))
      setDays(diffDays)
    }
  }

  const tabs = [
    { id: 'overview', label: 'Overview', icon: BarChart3 },
    { id: 'per-project', label: 'Per Project', icon: FolderOpen },
    { id: 'agents', label: 'Agent Performance', icon: Trophy },
    { id: 'models', label: 'Model Comparison', icon: Zap },
    { id: 'build-time', label: 'Build Time', icon: Timer },
    { id: 'issues', label: 'Common Issues', icon: AlertTriangle },
    { id: 'accuracy', label: 'Cost Accuracy', icon: Target },
  ] as const

  return (
    <div className="space-y-6 pb-20 lg:pb-0">
      <div>
        <h2 className="text-2xl font-semibold text-text-primary">Cost & Analytics Dashboard</h2>
        <p className="text-text-secondary mt-1">Track spending and agent performance</p>
      </div>

      {/* Date Range Filter */}
      <div className="flex flex-wrap items-center gap-2">
        {DATE_RANGE_OPTIONS.map((opt) => (
          <button
            key={opt.days}
            onClick={() => setDays(opt.days)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              days === opt.days
                ? 'bg-accent-primary text-white'
                : 'bg-background-secondary text-text-secondary hover:bg-background-tertiary'
            }`}
          >
            {opt.label}
          </button>
        ))}
        <div className="flex items-center gap-1 ml-2">
          <input
            type="date"
            value={customFrom}
            onChange={(e) => setCustomFrom(e.target.value)}
            className="px-2 py-1.5 rounded-lg text-sm bg-background-secondary text-text-primary border border-border-subtle"
          />
          <span className="text-text-tertiary text-sm">to</span>
          <input
            type="date"
            value={customTo}
            onChange={(e) => setCustomTo(e.target.value)}
            className="px-2 py-1.5 rounded-lg text-sm bg-background-secondary text-text-primary border border-border-subtle"
          />
          <button
            onClick={handleApplyCustomRange}
            disabled={!customFrom || !customTo}
            className="px-3 py-1.5 rounded-lg text-sm font-medium bg-background-secondary text-text-secondary hover:bg-background-tertiary disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Apply
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex flex-wrap gap-2 border-b border-border-subtle pb-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? 'bg-accent-primary text-white'
                : 'text-text-secondary hover:bg-background-secondary'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <>
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
                  <CheckCircle2 className="w-5 h-5 text-accent-success" />
                </div>
                <div>
                  <p className="text-xl font-semibold text-text-primary">
                    {analyticsSummary?.overall_success_rate?.toFixed(1) || '0'}%
                  </p>
                  <p className="text-xs text-text-secondary">Success Rate</p>
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
                    {analyticsSummary?.total_agent_executions || 0}
                  </p>
                  <p className="text-xs text-text-secondary">Agent Executions</p>
                </div>
              </div>
            </Card>
            <Card padding="sm">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-accent-warning/20 flex items-center justify-center">
                  <Target className="w-5 h-5 text-accent-warning" />
                </div>
                <div>
                  <p className="text-xl font-semibold text-text-primary">
                    {costAccuracy?.avg_accuracy?.toFixed(0) || '--'}%
                  </p>
                  <p className="text-xs text-text-secondary">Cost Accuracy</p>
                </div>
              </div>
            </Card>
          </div>

          {/* Cost by Agent */}
          <Card>
            <h3 className="font-medium text-text-primary mb-4">Cost by Agent</h3>
            <div className="space-y-3">
              {byAgent?.map((agent) => {
                const isExpensive = totalAgentCost > 0 && agent.total_cost > totalAgentCost * 0.5
                return (
                  <div key={agent.agent_name} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-2 h-2 rounded-full bg-accent-primary" />
                      <span className="text-sm text-text-primary capitalize">
                        {agent.agent_name.replace('_', ' ')}
                      </span>
                      {isExpensive && (
                        <span title="Over 50% of total cost"><Flame className="w-4 h-4 text-orange-500" /></span>
                      )}
                    </div>
                    <div className="flex items-center gap-4 text-sm">
                      <span className="text-text-tertiary">{agent.call_count} calls</span>
                      <span className="text-text-primary font-mono">
                        ${agent.total_cost.toFixed(4)}
                      </span>
                    </div>
                  </div>
                )
              })}
              {(!byAgent || byAgent.length === 0) && (
                <p className="text-sm text-text-secondary text-center py-4">No data yet</p>
              )}
            </div>
          </Card>

          {/* Cost by Model */}
          <Card>
            <h3 className="font-medium text-text-primary mb-4">Cost by Model</h3>
            <div className="space-y-3">
              {byModel?.map((model) => {
                const isExpensive = totalModelCost > 0 && model.total_cost > totalModelCost * 0.5
                return (
                  <div key={model.model} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-2 h-2 rounded-full bg-accent-secondary" />
                      <code className="text-sm text-text-primary">
                        {model.model.split('/').pop()}
                      </code>
                      {isExpensive && (
                        <span title="Over 50% of total cost"><Flame className="w-4 h-4 text-orange-500" /></span>
                      )}
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
                )
              })}
              {(!byModel || byModel.length === 0) && (
                <p className="text-sm text-text-secondary text-center py-4">No data yet</p>
              )}
            </div>
          </Card>
        </>
      )}

      {/* Per Project Tab */}
      {activeTab === 'per-project' && (
        <>
          <Card>
            <h3 className="font-medium text-text-primary mb-4 flex items-center gap-2">
              <FolderOpen className="w-5 h-5 text-accent-primary" />
              Per-Project Cost Breakdown
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-text-secondary border-b border-border-subtle">
                    <th className="pb-3 font-medium">Project Name</th>
                    <th className="pb-3 font-medium">Type</th>
                    <th className="pb-3 font-medium">Status</th>
                    <th className="pb-3 font-medium">Total Cost</th>
                    <th className="pb-3 font-medium">Created At</th>
                  </tr>
                </thead>
                <tbody>
                  {projects?.map((project) => (
                    <tr
                      key={project.id}
                      onClick={() => setSelectedProjectId(
                        selectedProjectId === project.id ? null : project.id
                      )}
                      className={`border-b border-border-subtle/50 cursor-pointer transition-colors ${
                        selectedProjectId === project.id
                          ? 'bg-accent-primary/10'
                          : 'hover:bg-background-secondary'
                      }`}
                    >
                      <td className="py-3 text-text-primary font-medium">
                        {project.name || project.brief?.slice(0, 40) || project.id.slice(0, 8)}
                      </td>
                      <td className="py-3 text-text-secondary capitalize">
                        {project.project_type?.replace(/_/g, ' ') || '--'}
                      </td>
                      <td className="py-3">
                        <span className={`px-2 py-0.5 text-xs rounded font-medium ${
                          project.status === 'completed' ? 'bg-accent-success/20 text-accent-success' :
                          project.status === 'running' || project.status === 'in_progress' ? 'bg-accent-primary/20 text-accent-primary' :
                          project.status === 'failed' ? 'bg-accent-error/20 text-accent-error' :
                          'bg-background-secondary text-text-tertiary'
                        }`}>
                          {project.status}
                        </span>
                      </td>
                      <td className="py-3 font-mono text-text-primary">
                        ${project.cost_estimate?.toFixed(4) || '0.0000'}
                      </td>
                      <td className="py-3 text-text-secondary">
                        {new Date(project.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {(!projects || projects.length === 0) && (
                <p className="text-sm text-text-secondary text-center py-8">
                  No projects found.
                </p>
              )}
            </div>
          </Card>

          {/* Selected project detail */}
          {selectedProject && (
            <Card>
              <h3 className="font-medium text-text-primary mb-4">
                Agent Cost Breakdown: {selectedProject.name || selectedProject.id.slice(0, 8)}
              </h3>
              {projectCostBreakdown.length > 0 ? (
                <div className="space-y-3">
                  {projectCostBreakdown.map((item) => (
                    <div key={item.agent_name} className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-2 h-2 rounded-full bg-accent-primary" />
                        <span className="text-sm text-text-primary capitalize">
                          {item.agent_name.replace(/_/g, ' ')}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-sm">
                        <span className="text-text-tertiary">{item.call_count} calls</span>
                        <span className="text-text-primary font-mono">
                          ${item.total_cost.toFixed(4)}
                        </span>
                      </div>
                    </div>
                  ))}
                  <div className="pt-3 border-t border-border-subtle flex justify-between text-sm">
                    <span className="text-text-secondary font-medium">Total</span>
                    <span className="text-text-primary font-mono font-semibold">
                      ${projectCostBreakdown.reduce((s, i) => s + i.total_cost, 0).toFixed(4)}
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-text-secondary text-center py-4">
                  No agent logs found for this project.
                </p>
              )}

              {/* Agent log details */}
              {projectAgentLogs && projectAgentLogs.length > 0 && (
                <div className="mt-6">
                  <h4 className="text-sm font-medium text-text-secondary mb-3">Agent Log Details</h4>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-text-secondary border-b border-border-subtle">
                          <th className="pb-2 font-medium">Agent</th>
                          <th className="pb-2 font-medium">Model</th>
                          <th className="pb-2 font-medium">Status</th>
                          <th className="pb-2 font-medium">Tokens</th>
                          <th className="pb-2 font-medium">Cost</th>
                          <th className="pb-2 font-medium">Duration</th>
                        </tr>
                      </thead>
                      <tbody>
                        {projectAgentLogs.map((log) => (
                          <tr key={log.id} className="border-b border-border-subtle/50">
                            <td className="py-2 capitalize text-text-primary">
                              {log.agent_name.replace(/_/g, ' ')}
                            </td>
                            <td className="py-2">
                              <code className="text-xs bg-background-secondary px-1.5 py-0.5 rounded text-text-secondary">
                                {log.model_used.split('/').pop()}
                              </code>
                            </td>
                            <td className="py-2">
                              <span className={`text-xs ${
                                log.status === 'success' ? 'text-accent-success' :
                                log.status === 'failed' ? 'text-accent-error' :
                                'text-text-tertiary'
                              }`}>
                                {log.status}
                              </span>
                            </td>
                            <td className="py-2 text-text-secondary">
                              {log.total_tokens.toLocaleString()}
                            </td>
                            <td className="py-2 font-mono text-text-primary">
                              ${log.cost.toFixed(4)}
                            </td>
                            <td className="py-2 text-text-secondary">
                              {(log.duration_ms / 1000).toFixed(1)}s
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </Card>
          )}
        </>
      )}

      {/* Agent Performance Tab */}
      {activeTab === 'agents' && (
        <Card>
          <h3 className="font-medium text-text-primary mb-4 flex items-center gap-2">
            <Trophy className="w-5 h-5 text-accent-warning" />
            Agent Success Rate Leaderboard
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-text-secondary border-b border-border-subtle">
                  <th className="pb-3 font-medium">Rank</th>
                  <th className="pb-3 font-medium">Agent</th>
                  <th className="pb-3 font-medium">Success Rate</th>
                  <th className="pb-3 font-medium">Executions</th>
                  <th className="pb-3 font-medium">Avg Time</th>
                  <th className="pb-3 font-medium">Avg Revisions</th>
                  <th className="pb-3 font-medium">Quality Score</th>
                  <th className="pb-3 font-medium">Total Cost</th>
                </tr>
              </thead>
              <tbody>
                {successRates?.map((agent, index) => (
                  <tr key={agent.agent_name} className="border-b border-border-subtle/50">
                    <td className="py-3">
                      <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${
                        index === 0 ? 'bg-yellow-500/20 text-yellow-500' :
                        index === 1 ? 'bg-gray-400/20 text-gray-400' :
                        index === 2 ? 'bg-amber-600/20 text-amber-600' :
                        'bg-background-secondary text-text-tertiary'
                      }`}>
                        {index + 1}
                      </span>
                    </td>
                    <td className="py-3 capitalize text-text-primary">
                      {agent.agent_name.replace(/_/g, ' ')}
                    </td>
                    <td className="py-3">
                      <span className={`font-mono ${
                        agent.success_rate >= 90 ? 'text-accent-success' :
                        agent.success_rate >= 70 ? 'text-accent-warning' :
                        'text-accent-error'
                      }`}>
                        {agent.success_rate.toFixed(1)}%
                      </span>
                    </td>
                    <td className="py-3 text-text-secondary">{agent.total_executions}</td>
                    <td className="py-3 text-text-secondary">
                      {(agent.avg_execution_time_ms / 1000).toFixed(1)}s
                    </td>
                    <td className="py-3 text-text-secondary">
                      {agent.avg_revision_count.toFixed(1)}
                    </td>
                    <td className="py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-2 bg-background-secondary rounded-full overflow-hidden">
                          <div
                            className="h-full bg-accent-primary rounded-full"
                            style={{ width: `${agent.avg_quality_score * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-text-tertiary">
                          {(agent.avg_quality_score * 100).toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td className="py-3 font-mono text-text-primary">
                      ${agent.total_cost.toFixed(4)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {(!successRates || successRates.length === 0) && (
              <p className="text-sm text-text-secondary text-center py-8">
                No agent performance data yet. Data will appear after agents execute.
              </p>
            )}
          </div>
        </Card>
      )}

      {/* Model Comparison Tab */}
      {activeTab === 'models' && (
        <Card>
          <h3 className="font-medium text-text-primary mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-accent-secondary" />
            Model Performance Comparison
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-text-secondary border-b border-border-subtle">
                  <th className="pb-3 font-medium">Agent</th>
                  <th className="pb-3 font-medium">Model</th>
                  <th className="pb-3 font-medium">Success Rate</th>
                  <th className="pb-3 font-medium">Executions</th>
                  <th className="pb-3 font-medium">Avg Revisions</th>
                  <th className="pb-3 font-medium">Avg Cost</th>
                </tr>
              </thead>
              <tbody>
                {modelComparison?.map((item, index) => (
                  <tr key={`${item.agent_name}-${item.model_used}-${index}`} className="border-b border-border-subtle/50">
                    <td className="py-3 capitalize text-text-primary">
                      {item.agent_name.replace(/_/g, ' ')}
                    </td>
                    <td className="py-3">
                      <code className="text-xs bg-background-secondary px-2 py-1 rounded">
                        {item.model_used.split('/').pop()}
                      </code>
                    </td>
                    <td className="py-3">
                      <span className={`font-mono ${
                        item.success_rate >= 90 ? 'text-accent-success' :
                        item.success_rate >= 70 ? 'text-accent-warning' :
                        'text-accent-error'
                      }`}>
                        {item.success_rate.toFixed(1)}%
                      </span>
                    </td>
                    <td className="py-3 text-text-secondary">{item.execution_count}</td>
                    <td className="py-3 text-text-secondary">{item.avg_revision_count.toFixed(1)}</td>
                    <td className="py-3 font-mono text-text-primary">${item.avg_cost.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {(!modelComparison || modelComparison.length === 0) && (
              <p className="text-sm text-text-secondary text-center py-8">
                No model comparison data yet.
              </p>
            )}
          </div>
        </Card>
      )}

      {/* Build Time Tab */}
      {activeTab === 'build-time' && (
        <Card>
          <h3 className="font-medium text-text-primary mb-4 flex items-center gap-2">
            <Timer className="w-5 h-5 text-accent-primary" />
            Build Time Analysis (Waterfall)
          </h3>
          <div className="space-y-3">
            {buildTimeWaterfall?.map((item) => (
              <div key={item.agent_name} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="capitalize text-text-primary">
                    {item.agent_name.replace(/_/g, ' ')}
                  </span>
                  <div className="flex items-center gap-4">
                    <span className="text-text-tertiary">
                      {(item.avg_time_ms / 1000).toFixed(1)}s avg
                    </span>
                    <span className="text-text-secondary font-mono">
                      {item.percentage_of_total.toFixed(1)}%
                    </span>
                  </div>
                </div>
                <div className="w-full h-4 bg-background-secondary rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-accent-primary to-accent-secondary rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(100, item.percentage_of_total)}%` }}
                  />
                </div>
              </div>
            ))}
            {(!buildTimeWaterfall || buildTimeWaterfall.length === 0) && (
              <p className="text-sm text-text-secondary text-center py-8">
                No build time data yet.
              </p>
            )}
          </div>

          {buildTimeWaterfall && buildTimeWaterfall.length > 0 && (
            <div className="mt-6 pt-4 border-t border-border-subtle">
              <div className="flex justify-between text-sm">
                <span className="text-text-secondary">Total Average Build Time:</span>
                <span className="font-semibold text-text-primary">
                  {(buildTimeWaterfall.reduce((sum, item) => sum + item.avg_time_ms, 0) / 1000).toFixed(1)}s
                </span>
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Common Issues Tab */}
      {activeTab === 'issues' && (
        <Card>
          <h3 className="font-medium text-text-primary mb-4 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-accent-error" />
            Top 10 Recurring QA Issues
          </h3>
          <div className="space-y-4">
            {failurePatterns?.map((pattern, index) => (
              <div
                key={pattern.id}
                className="p-4 bg-background-secondary rounded-lg border border-border-subtle"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`px-2 py-0.5 text-xs rounded font-medium ${
                        pattern.pattern_type === 'security' ? 'bg-red-500/20 text-red-400' :
                        pattern.pattern_type === 'accessibility' ? 'bg-purple-500/20 text-purple-400' :
                        pattern.pattern_type === 'seo' ? 'bg-blue-500/20 text-blue-400' :
                        'bg-gray-500/20 text-gray-400'
                      }`}>
                        {pattern.pattern_type}
                      </span>
                      {pattern.causing_agent && (
                        <span className="text-xs text-text-tertiary">
                          from {pattern.causing_agent.replace(/_/g, ' ')}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-text-primary mb-2">{pattern.description}</p>
                    {pattern.sample_error && (
                      <code className="text-xs text-text-tertiary bg-bg-primary px-2 py-1 rounded block overflow-x-auto">
                        {pattern.sample_error.slice(0, 100)}...
                      </code>
                    )}
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-accent-error">
                      {pattern.occurrence_count}
                    </div>
                    <div className="text-xs text-text-tertiary">occurrences</div>
                  </div>
                </div>
              </div>
            ))}
            {(!failurePatterns || failurePatterns.length === 0) && (
              <div className="text-center py-8">
                <CheckCircle2 className="w-12 h-12 text-accent-success mx-auto mb-3" />
                <p className="text-text-secondary">No recurring QA issues found!</p>
                <p className="text-sm text-text-tertiary">Issues will appear here as they occur.</p>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Cost Accuracy Tab */}
      {activeTab === 'accuracy' && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <Card padding="sm">
              <div className="text-center">
                <p className="text-3xl font-bold text-accent-primary">
                  {costAccuracy?.avg_accuracy?.toFixed(1) || '--'}%
                </p>
                <p className="text-xs text-text-secondary">Average Accuracy</p>
              </div>
            </Card>
            <Card padding="sm">
              <div className="text-center">
                <p className="text-3xl font-bold text-text-primary">
                  {costAccuracy?.total_projects || 0}
                </p>
                <p className="text-xs text-text-secondary">Projects Tracked</p>
              </div>
            </Card>
            <Card padding="sm">
              <div className="text-center">
                <p className="text-3xl font-bold text-accent-warning">
                  {costAccuracy?.underestimates || 0}
                </p>
                <p className="text-xs text-text-secondary">Underestimates</p>
              </div>
            </Card>
            <Card padding="sm">
              <div className="text-center">
                <p className="text-3xl font-bold text-accent-success">
                  {costAccuracy?.overestimates || 0}
                </p>
                <p className="text-xs text-text-secondary">Overestimates</p>
              </div>
            </Card>
          </div>

          <Card>
            <h3 className="font-medium text-text-primary mb-4">Accuracy by Project Type</h3>
            <div className="space-y-3">
              {costAccuracy?.by_project_type && Object.entries(costAccuracy.by_project_type).map(([type, accuracy]) => (
                <div key={type} className="flex items-center justify-between">
                  <span className="text-sm text-text-primary capitalize">
                    {type.replace(/_/g, ' ')}
                  </span>
                  <div className="flex items-center gap-3">
                    <div className="w-32 h-2 bg-background-secondary rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          accuracy >= 80 ? 'bg-accent-success' :
                          accuracy >= 60 ? 'bg-accent-warning' :
                          'bg-accent-error'
                        }`}
                        style={{ width: `${Math.min(100, accuracy)}%` }}
                      />
                    </div>
                    <span className="text-sm font-mono text-text-secondary w-16 text-right">
                      {accuracy.toFixed(1)}%
                    </span>
                  </div>
                </div>
              ))}
              {(!costAccuracy?.by_project_type || Object.keys(costAccuracy.by_project_type).length === 0) && (
                <p className="text-sm text-text-secondary text-center py-4">
                  No accuracy data by project type yet.
                </p>
              )}
            </div>
          </Card>

          <Card>
            <h3 className="font-medium text-text-primary mb-4">Accuracy by Cost Profile</h3>
            <div className="space-y-3">
              {costAccuracy?.by_cost_profile && Object.entries(costAccuracy.by_cost_profile).map(([profile, accuracy]) => (
                <div key={profile} className="flex items-center justify-between">
                  <span className="text-sm text-text-primary capitalize">{profile}</span>
                  <div className="flex items-center gap-3">
                    <div className="w-32 h-2 bg-background-secondary rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          accuracy >= 80 ? 'bg-accent-success' :
                          accuracy >= 60 ? 'bg-accent-warning' :
                          'bg-accent-error'
                        }`}
                        style={{ width: `${Math.min(100, accuracy)}%` }}
                      />
                    </div>
                    <span className="text-sm font-mono text-text-secondary w-16 text-right">
                      {accuracy.toFixed(1)}%
                    </span>
                  </div>
                </div>
              ))}
              {(!costAccuracy?.by_cost_profile || Object.keys(costAccuracy.by_cost_profile).length === 0) && (
                <p className="text-sm text-text-secondary text-center py-4">
                  No accuracy data by cost profile yet.
                </p>
              )}
            </div>
          </Card>
        </>
      )}
    </div>
  )
}
