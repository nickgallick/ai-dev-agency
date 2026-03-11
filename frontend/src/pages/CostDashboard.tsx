import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card } from '@/components/Card'
import { api } from '@/lib/api'
import { format } from 'date-fns'
import {
  DollarSign, TrendingUp, Zap, Clock, Trophy, BarChart3,
  AlertTriangle, Target, CheckCircle2, XCircle, Timer, Layers,
  ChevronDown, ChevronUp, Calendar
} from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

type TabType = 'overview' | 'agents' | 'models' | 'build-time' | 'issues' | 'accuracy' | 'projects'

type DateRange = '1' | '7' | '30' | '90' | 'custom'

export default function CostDashboard() {
  const [activeTab, setActiveTab] = useState<TabType>('overview')
  const [dateRange, setDateRange] = useState<DateRange>('30')
  const [customFrom, setCustomFrom] = useState('')
  const [customTo, setCustomTo] = useState('')
  const [expandedProject, setExpandedProject] = useState<string | null>(null)

  const days = dateRange === 'custom' ? 90 : parseInt(dateRange)

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

  // Phase 9A: New analytics queries
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

  // Per-project costs — fetch all projects + their agent logs
  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.getProjects({ limit: 100 }),
    enabled: activeTab === 'projects',
  })

  const { data: allLogs } = useQuery({
    queryKey: ['allAgentLogs'],
    queryFn: () => api.getAgentLogs({ limit: 500 }),
    enabled: activeTab === 'projects',
  })

  // Group logs by project
  const costByProject = useMemo(() => {
    if (!allLogs) return {} as Record<string, { total: number; agents: Record<string, number> }>
    const result: Record<string, { total: number; agents: Record<string, number> }> = {}
    allLogs.forEach((log) => {
      if (!result[log.project_id]) result[log.project_id] = { total: 0, agents: {} }
      result[log.project_id].total += log.cost ?? 0
      result[log.project_id].agents[log.agent_name] =
        (result[log.project_id].agents[log.agent_name] ?? 0) + (log.cost ?? 0)
    })
    return result
  }, [allLogs])

  // Trends chart data — date filtering for custom range
  const chartData = useMemo(() => {
    if (!trends) return []
    if (dateRange !== 'custom' || !customFrom) return trends
    const from = new Date(customFrom)
    const to = customTo ? new Date(customTo + 'T23:59:59') : new Date()
    return trends.filter((t) => {
      const d = new Date(t.date)
      return d >= from && d <= to
    })
  }, [trends, dateRange, customFrom, customTo])

  const tabs = [
    { id: 'overview', label: 'Overview', icon: BarChart3 },
    { id: 'projects', label: 'By Project', icon: Layers },
    { id: 'agents', label: 'Agent Performance', icon: Trophy },
    { id: 'models', label: 'Model Comparison', icon: Zap },
    { id: 'build-time', label: 'Build Time', icon: Timer },
    { id: 'issues', label: 'Common Issues', icon: AlertTriangle },
    { id: 'accuracy', label: 'Cost Accuracy', icon: Target },
  ] as const

  return (
    <div className="space-y-6 pb-20 lg:pb-0">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-2xl font-semibold text-text-primary">Cost & Analytics Dashboard</h2>
          <p className="text-text-secondary mt-1">Track spending and agent performance</p>
        </div>

        {/* Date Range Selector */}
        <div className="flex items-center gap-2 flex-wrap">
          <Calendar className="w-4 h-4 text-text-tertiary" />
          {(['1', '7', '30', '90'] as DateRange[]).map((d) => (
            <button
              key={d}
              onClick={() => setDateRange(d)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                dateRange === d
                  ? 'bg-accent-primary text-white'
                  : 'bg-bg-secondary text-text-secondary hover:bg-border-subtle'
              }`}
            >
              {d === '1' ? 'Today' : `${d}d`}
            </button>
          ))}
          <button
            onClick={() => setDateRange('custom')}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              dateRange === 'custom'
                ? 'bg-accent-primary text-white'
                : 'bg-bg-secondary text-text-secondary hover:bg-border-subtle'
            }`}
          >
            Custom
          </button>
          {dateRange === 'custom' && (
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={customFrom}
                onChange={(e) => setCustomFrom(e.target.value)}
                className="glass-input text-sm px-2 py-1 rounded"
              />
              <span className="text-text-tertiary text-xs">–</span>
              <input
                type="date"
                value={customTo}
                onChange={(e) => setCustomTo(e.target.value)}
                className="glass-input text-sm px-2 py-1 rounded"
              />
            </div>
          )}
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex flex-wrap gap-2 border-b border-border-default pb-2 overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
              activeTab === tab.id
                ? 'bg-accent-primary text-white'
                : 'text-text-secondary hover:bg-bg-secondary'
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

          {/* Spend Trend Chart */}
          {chartData.length > 0 && (
            <Card>
              <h3 className="font-medium text-text-primary mb-4">Daily Spend Trend</h3>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle, #334155)" opacity={0.5} />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: 'var(--text-tertiary)', fontSize: 11 }}
                    tickFormatter={(v) => {
                      try { return format(new Date(v), 'MMM d') } catch { return v }
                    }}
                  />
                  <YAxis tick={{ fill: 'var(--text-tertiary)', fontSize: 11 }} tickFormatter={(v) => `$${v}`} />
                  <Tooltip
                    contentStyle={{
                      background: 'var(--bg-secondary)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '8px',
                      color: 'var(--text-primary)',
                      fontSize: 12,
                    }}
                    formatter={(v: number) => [`$${v.toFixed(4)}`, 'Cost']}
                    labelFormatter={(l) => {
                      try { return format(new Date(l), 'MMM d, yyyy') } catch { return l }
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="daily_cost"
                    stroke="var(--accent-primary)"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          )}

          {/* Cost by Agent — with most expensive highlighted */}
          <Card>
            <h3 className="font-medium text-text-primary mb-4">Cost by Agent</h3>
            <div className="space-y-2">
              {byAgent?.map((agent, idx) => {
                const maxCost = byAgent[0]?.total_cost || 1
                const isTop = idx === 0
                return (
                  <div key={agent.agent_name} className={`flex items-center justify-between p-2 rounded-lg ${isTop ? 'bg-accent-warning/5 border border-accent-warning/20' : ''}`}>
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <div className={`w-2 h-2 rounded-full flex-shrink-0 ${isTop ? 'bg-accent-warning' : 'bg-accent-primary'}`} />
                      <span className="text-sm text-text-primary capitalize truncate">
                        {agent.agent_name.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-sm ml-2">
                      <div className="hidden sm:block w-24 h-1.5 bg-bg-secondary rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${isTop ? 'bg-accent-warning' : 'bg-accent-primary'}`}
                          style={{ width: `${(agent.total_cost / maxCost) * 100}%` }}
                        />
                      </div>
                      <span className="text-text-tertiary">{agent.call_count} calls</span>
                      <span className={`font-mono ${isTop ? 'text-accent-warning font-semibold' : 'text-text-primary'}`}>
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

          {/* Cost by Model — with most expensive highlighted */}
          <Card>
            <h3 className="font-medium text-text-primary mb-4">Cost by Model</h3>
            <div className="space-y-2">
              {byModel?.map((model, idx) => {
                const maxCost = byModel[0]?.total_cost || 1
                const isTop = idx === 0
                return (
                  <div key={model.model} className={`flex items-center justify-between p-2 rounded-lg ${isTop ? 'bg-accent-primary/5 border border-accent-primary/20' : ''}`}>
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <div className={`w-2 h-2 rounded-full flex-shrink-0 ${isTop ? 'bg-accent-primary' : 'bg-accent-secondary'}`} />
                      <code className="text-sm text-text-primary truncate">
                        {model.model.split('/').pop()}
                      </code>
                    </div>
                    <div className="flex items-center gap-4 text-sm ml-2">
                      <div className="hidden sm:block w-24 h-1.5 bg-bg-secondary rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${isTop ? 'bg-accent-primary' : 'bg-accent-secondary'}`}
                          style={{ width: `${(model.total_cost / maxCost) * 100}%` }}
                        />
                      </div>
                      <span className="text-text-tertiary">
                        {(model.prompt_tokens + model.completion_tokens).toLocaleString()} tok
                      </span>
                      <span className={`font-mono ${isTop ? 'text-accent-primary font-semibold' : 'text-text-primary'}`}>
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

      {/* By Project Tab */}
      {activeTab === 'projects' && (
        <Card>
          <h3 className="font-medium text-text-primary mb-4 flex items-center gap-2">
            <Layers className="w-5 h-5 text-accent-primary" />
            Cost by Project
          </h3>
          <div className="space-y-2">
            {projects
              ?.filter((p) => costByProject[p.id])
              .sort((a, b) => (costByProject[b.id]?.total ?? 0) - (costByProject[a.id]?.total ?? 0))
              .map((project) => {
                const projectCost = costByProject[project.id]
                const isExpanded = expandedProject === project.id
                if (!projectCost) return null
                return (
                  <div key={project.id} className="border border-border-subtle rounded-lg overflow-hidden">
                    <button
                      className="w-full flex items-center justify-between p-4 hover:bg-bg-secondary transition-colors text-left"
                      onClick={() => setExpandedProject(isExpanded ? null : project.id)}
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium text-text-primary">
                          {project.name || 'Untitled Project'}
                        </span>
                        <span className="text-xs text-text-tertiary capitalize">
                          {project.project_type?.replace(/_/g, ' ')}
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          project.status === 'completed' ? 'bg-accent-success/20 text-accent-success' :
                          project.status === 'failed' ? 'bg-accent-error/20 text-accent-error' :
                          'bg-accent-primary/20 text-accent-primary'
                        }`}>
                          {project.status}
                        </span>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="font-mono text-sm font-semibold text-text-primary">
                          ${projectCost.total.toFixed(4)}
                        </span>
                        {isExpanded ? <ChevronUp className="w-4 h-4 text-text-tertiary" /> : <ChevronDown className="w-4 h-4 text-text-tertiary" />}
                      </div>
                    </button>
                    {isExpanded && (
                      <div className="border-t border-border-subtle px-4 py-3 bg-bg-secondary">
                        <div className="space-y-1.5">
                          {Object.entries(projectCost.agents)
                            .sort(([, a], [, b]) => b - a)
                            .map(([agent, cost]) => (
                              <div key={agent} className="flex items-center justify-between text-sm">
                                <span className="capitalize text-text-secondary">{agent.replace(/_/g, ' ')}</span>
                                <span className="font-mono text-text-primary">${cost.toFixed(4)}</span>
                              </div>
                            ))}
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            {(!projects || projects.length === 0 || Object.keys(costByProject).length === 0) && (
              <p className="text-sm text-text-secondary text-center py-8">No project cost data yet.</p>
            )}
          </div>
        </Card>
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
                <tr className="text-left text-text-secondary border-b border-border-default">
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
                  <tr key={agent.agent_name} className="border-b border-border-default/50">
                    <td className="py-3">
                      <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${
                        index === 0 ? 'bg-yellow-500/20 text-yellow-500' :
                        index === 1 ? 'bg-gray-400/20 text-gray-400' :
                        index === 2 ? 'bg-amber-600/20 text-amber-600' :
                        'bg-bg-secondary text-text-tertiary'
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
                        <div className="w-16 h-2 bg-bg-secondary rounded-full overflow-hidden">
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
                <tr className="text-left text-text-secondary border-b border-border-default">
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
                  <tr key={`${item.agent_name}-${item.model_used}-${index}`} className="border-b border-border-default/50">
                    <td className="py-3 capitalize text-text-primary">
                      {item.agent_name.replace(/_/g, ' ')}
                    </td>
                    <td className="py-3">
                      <code className="text-xs bg-bg-secondary px-2 py-1 rounded">
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
                <div className="w-full h-4 bg-bg-secondary rounded-full overflow-hidden">
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
            <div className="mt-6 pt-4 border-t border-border-default">
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
                className="p-4 bg-bg-secondary rounded-lg border border-border-default"
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
                    <div className="w-32 h-2 bg-bg-secondary rounded-full overflow-hidden">
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
                    <div className="w-32 h-2 bg-bg-secondary rounded-full overflow-hidden">
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
