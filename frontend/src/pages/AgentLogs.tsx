import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useState } from 'react'
import { format } from 'date-fns'
import { Activity, Filter, Clock, DollarSign, Cpu, ChevronDown, ChevronUp, Search } from 'lucide-react'

export default function AgentLogs() {
  const [expandedLog, setExpandedLog] = useState<string | null>(null)
  const [filterAgent, setFilterAgent] = useState<string>('all')

  const { data: logs, isLoading } = useQuery({
    queryKey: ['agentLogs'],
    queryFn: () => api.getAgentLogs({ limit: 100 }),
  })

  const agents = Array.from(new Set(logs?.map(l => l.agent_name) || []))
  const filteredLogs = filterAgent === 'all' 
    ? logs 
    : logs?.filter(l => l.agent_name === filterAgent)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="mb-2">
        <h1 className="text-2xl lg:text-3xl font-bold flex items-center gap-3" style={{ color: 'var(--text-primary)' }}>
          <Activity className="w-7 h-7" style={{ color: 'var(--accent-primary)' }} />
          Agent Logs
        </h1>
        <p className="mt-1" style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-base)' }}>
          Debugging view for all LLM calls
        </p>
      </div>

      {/* Filter */}
      <div className="glass-card flex flex-wrap items-center gap-4" style={{ padding: 'var(--space-4)' }}>
        <Filter className="w-5 h-5" style={{ color: 'var(--text-tertiary)' }} />
        <select
          value={filterAgent}
          onChange={(e) => setFilterAgent(e.target.value)}
          className="glass-input"
          style={{ width: 'auto', padding: 'var(--space-2) var(--space-4)' }}
        >
          <option value="all">All Agents</option>
          {agents.map(agent => (
            <option key={agent} value={agent}>{agent}</option>
          ))}
        </select>
        <span style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-sm)' }}>
          {filteredLogs?.length || 0} logs
        </span>
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

        {filteredLogs?.length === 0 && !isLoading && (
          <div className="glass-card text-center py-12">
            <Activity className="w-12 h-12 mx-auto mb-3" style={{ color: 'var(--text-tertiary)' }} />
            <p style={{ color: 'var(--text-secondary)' }}>
              No logs found
            </p>
          </div>
        )}

        {filteredLogs?.map((log, index) => (
          <div 
            key={log.id} 
            className="glass-card animate-enter cursor-pointer"
            style={{ animationDelay: `${index * 30}ms` }}
            onClick={() => setExpandedLog(expandedLog === log.id ? null : log.id)}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center"
                     style={{ background: 'var(--glass-bg-elevated)' }}>
                  <Cpu className="w-5 h-5" style={{ color: 'var(--accent-primary)' }} />
                </div>
                <div>
                  <h3 className="font-medium" style={{ color: 'var(--text-primary)' }}>
                    {log.agent_name}
                  </h3>
                  <div className="flex items-center gap-3" style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-xs)' }}>
                    <span className="badge badge-info">{log.model_used}</span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {format(new Date(log.timestamp), 'HH:mm:ss')}
                    </span>
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <p className="font-medium" style={{ color: 'var(--text-primary)' }}>
                    {log.token_usage?.toLocaleString() || 0} tokens
                  </p>
                  <p className="flex items-center gap-1" style={{ color: 'var(--accent-warning)', fontSize: 'var(--text-xs)' }}>
                    <DollarSign className="w-3 h-3" />
                    {log.cost?.toFixed(4) || '0.0000'}
                  </p>
                </div>
                {expandedLog === log.id ? (
                  <ChevronUp className="w-5 h-5" style={{ color: 'var(--text-tertiary)' }} />
                ) : (
                  <ChevronDown className="w-5 h-5" style={{ color: 'var(--text-tertiary)' }} />
                )}
              </div>
            </div>
            
            {expandedLog === log.id && (
              <div className="mt-4 pt-4" style={{ borderTop: '1px solid var(--glass-border)' }}>
                <div className="space-y-4">
                  <div>
                    <h4 className="text-sm font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>Input</h4>
                    <pre className="glass-card font-mono text-xs overflow-x-auto" 
                         style={{ background: 'var(--bg-primary)', padding: 'var(--space-3)', maxHeight: '200px' }}>
                      {JSON.stringify(log.input_data, null, 2)}
                    </pre>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>Output</h4>
                    <pre className="glass-card font-mono text-xs overflow-x-auto" 
                         style={{ background: 'var(--bg-primary)', padding: 'var(--space-3)', maxHeight: '200px' }}>
                      {JSON.stringify(log.output_data, null, 2)}
                    </pre>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
