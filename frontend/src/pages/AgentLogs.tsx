import { useQuery } from '@tanstack/react-query'
import { Card } from '@/components/Card'
import { Badge } from '@/components/Badge'
import { api } from '@/lib/api'
import { format } from 'date-fns'

export default function AgentLogs() {
  const { data: logs, isLoading } = useQuery({
    queryKey: ['agentLogs'],
    queryFn: () => api.getAgentLogs({ limit: 100 }),
  })

  return (
    <div className="space-y-6 pb-20 lg:pb-0">
      <div>
        <h2 className="text-2xl font-semibold text-text-primary">Agent Logs</h2>
        <p className="text-text-secondary mt-1">View all LLM calls and agent executions</p>
      </div>

      {/* Logs Table */}
      <Card padding="none">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-background-tertiary">
              <tr>
                <th className="px-4 py-3 text-left text-text-secondary font-medium">Agent</th>
                <th className="px-4 py-3 text-left text-text-secondary font-medium">Model</th>
                <th className="px-4 py-3 text-right text-text-secondary font-medium">Tokens</th>
                <th className="px-4 py-3 text-right text-text-secondary font-medium">Cost</th>
                <th className="px-4 py-3 text-right text-text-secondary font-medium">Duration</th>
                <th className="px-4 py-3 text-left text-text-secondary font-medium">Status</th>
                <th className="px-4 py-3 text-left text-text-secondary font-medium">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle">
              {isLoading && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-text-secondary">
                    Loading...
                  </td>
                </tr>
              )}
              {logs?.length === 0 && !isLoading && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-text-secondary">
                    No logs yet
                  </td>
                </tr>
              )}
              {logs?.map((log) => (
                <tr key={log.id} className="hover:bg-background-tertiary/50">
                  <td className="px-4 py-3 text-text-primary">
                    {log.agent_name}
                  </td>
                  <td className="px-4 py-3">
                    <code className="text-xs text-text-secondary bg-background-tertiary px-1.5 py-0.5 rounded">
                      {log.model_used.split('/').pop()}
                    </code>
                  </td>
                  <td className="px-4 py-3 text-right text-text-secondary font-mono">
                    {log.total_tokens.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right text-text-secondary font-mono">
                    ${log.cost.toFixed(4)}
                  </td>
                  <td className="px-4 py-3 text-right text-text-secondary font-mono">
                    {log.duration_ms}ms
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={log.status === 'completed' ? 'success' : 'error'}>
                      {log.status}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-text-tertiary text-xs">
                    {format(new Date(log.timestamp), 'MMM d, HH:mm')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
