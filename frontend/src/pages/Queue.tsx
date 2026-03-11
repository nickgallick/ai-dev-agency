import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card } from '@/components/Card'
import { Badge } from '@/components/Badge'
import { Button } from '@/components/Button'
import { api, QueueItem } from '@/lib/api'
import { 
  Clock, 
  Layers, 
  Zap, 
  Activity, 
  ArrowUp, 
  ArrowDown, 
  Trash2, 
  RefreshCw,
  PlayCircle
} from 'lucide-react'

export default function Queue() {
  const queryClient = useQueryClient()
  const [selectedPriority, setSelectedPriority] = useState<string | null>(null)

  const { data: queueStatus, isLoading } = useQuery({
    queryKey: ['queueStatus'],
    queryFn: api.getQueueStatus,
    refetchInterval: 5000, // Poll every 5 seconds
  })

  const { data: stats } = useQuery({
    queryKey: ['queueStats'],
    queryFn: api.getQueueStats,
    refetchInterval: 5000,
  })

  const reprioritizeMutation = useMutation({
    mutationFn: ({ projectId, priority }: { projectId: string; priority: string }) =>
      api.reprioritizeProject(projectId, priority),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queueStatus'] })
      queryClient.invalidateQueries({ queryKey: ['queueStats'] })
    },
  })

  const moveMutation = useMutation({
    mutationFn: ({ projectId, direction }: { projectId: string; direction: 'up' | 'down' }) =>
      api.moveProjectInQueue(projectId, direction),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queueStatus'] })
      queryClient.invalidateQueries({ queryKey: ['queueStats'] })
    },
  })

  const removeMutation = useMutation({
    mutationFn: (projectId: string) => api.removeFromQueue(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queueStatus'] })
      queryClient.invalidateQueries({ queryKey: ['queueStats'] })
    },
  })

  const formatWaitTime = (seconds: number) => {
    if (seconds < 60) return `${Math.round(seconds)}s`
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`
    return `${Math.round(seconds / 3600)}h`
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'text-red-400 bg-red-500/10'
      case 'normal': return 'text-blue-400 bg-blue-500/10'
      case 'background': return 'text-gray-400 bg-gray-500/10'
      default: return 'text-text-secondary bg-background-tertiary'
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 bg-background-tertiary rounded animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-24 bg-background-tertiary rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 pb-20 lg:pb-0">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-text-primary">Project Queue</h2>
          <p className="text-text-secondary mt-1">Manage project processing order</p>
        </div>
        <Button variant="ghost" size="sm" onClick={() => {
          queryClient.invalidateQueries({ queryKey: ['queueStatus'] })
          queryClient.invalidateQueries({ queryKey: ['queueStats'] })
        }}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-500/10">
              <Layers className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <p className="text-2xl font-semibold text-text-primary">
                {queueStatus?.queue_length || 0}
              </p>
              <p className="text-xs text-text-secondary">In Queue</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-green-500/10">
              <Activity className="w-5 h-5 text-green-400" />
            </div>
            <div>
              <p className="text-2xl font-semibold text-text-primary">
                {queueStatus?.active_count || 0} / {queueStatus?.max_concurrent || 2}
              </p>
              <p className="text-xs text-text-secondary">Active</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-red-500/10">
              <Zap className="w-5 h-5 text-red-400" />
            </div>
            <div>
              <p className="text-2xl font-semibold text-text-primary">
                {stats?.by_priority?.urgent || 0}
              </p>
              <p className="text-xs text-text-secondary">Urgent</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-yellow-500/10">
              <Clock className="w-5 h-5 text-yellow-400" />
            </div>
            <div>
              <p className="text-2xl font-semibold text-text-primary">
                {stats ? formatWaitTime(stats.average_wait_seconds) : '-'}
              </p>
              <p className="text-xs text-text-secondary">Avg Wait</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Capacity Indicator */}
      <Card className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-medium text-text-primary">Processing Capacity</h3>
            <p className="text-sm text-text-secondary">
              {queueStatus?.has_capacity 
                ? 'Ready to accept new projects' 
                : 'At capacity - new projects will be queued'}
            </p>
          </div>
          <Badge variant={queueStatus?.has_capacity ? 'success' : 'warning'}>
            {queueStatus?.has_capacity ? 'Available' : 'Full'}
          </Badge>
        </div>
        <div className="mt-3 h-2 bg-background-tertiary rounded-full overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-green-500 to-blue-500 transition-all duration-300"
            style={{ 
              width: `${((queueStatus?.active_count || 0) / (queueStatus?.max_concurrent || 2)) * 100}%` 
            }}
          />
        </div>
      </Card>

      {/* Active Projects */}
      {queueStatus?.active_projects && queueStatus.active_projects.length > 0 && (
        <Card>
          <h3 className="font-medium text-text-primary mb-4 flex items-center gap-2">
            <PlayCircle className="w-5 h-5 text-green-400" />
            Currently Processing
          </h3>
          <div className="space-y-3">
            {queueStatus.active_projects.map((project: any, idx: number) => (
              <div key={idx} className="p-3 bg-green-500/10 rounded-lg border border-green-500/20">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-text-primary">
                      {project.item?.metadata?.name || project.item?.project_id?.slice(0, 8)}
                    </p>
                    <p className="text-xs text-text-secondary">
                      Started: {project.started_at ? new Date(project.started_at).toLocaleTimeString() : 'N/A'}
                    </p>
                  </div>
                  <Badge variant="success">Processing</Badge>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Queue List */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-medium text-text-primary">Queued Projects</h3>
          <div className="flex gap-2">
            {['all', 'urgent', 'normal', 'background'].map(priority => (
              <button
                key={priority}
                onClick={() => setSelectedPriority(priority === 'all' ? null : priority)}
                className={`px-3 py-1 text-xs rounded-full transition-colors ${
                  (priority === 'all' && !selectedPriority) || selectedPriority === priority
                    ? 'bg-accent-primary text-white'
                    : 'bg-background-tertiary text-text-secondary hover:text-text-primary'
                }`}
              >
                {priority.charAt(0).toUpperCase() + priority.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {!queueStatus?.queue_items?.length ? (
          <div className="text-center py-8 text-text-secondary">
            <Layers className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No projects in queue</p>
            <p className="text-sm">Projects will appear here when created</p>
          </div>
        ) : (
          <div className="space-y-3">
            {queueStatus.queue_items
              .filter((item: QueueItem) => !selectedPriority || item.priority === selectedPriority)
              .map((item: QueueItem, idx: number) => (
                <div key={item.project_id} className="p-4 bg-background-tertiary rounded-lg">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="text-2xl font-bold text-text-tertiary">#{item.position}</div>
                      <div>
                        <p className="font-medium text-text-primary">
                          {item.project_id.slice(0, 8)}...
                        </p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className={`px-2 py-0.5 rounded text-xs ${getPriorityColor(item.priority)}`}>
                            {item.priority}
                          </span>
                          <span className="text-xs text-text-secondary">
                            ~{formatWaitTime(item.estimated_wait_seconds)} wait
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      {/* Position move buttons */}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => moveMutation.mutate({
                          projectId: item.project_id,
                          direction: 'up'
                        })}
                        disabled={item.position <= 1}
                        title="Move Up"
                      >
                        <ArrowUp className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => moveMutation.mutate({
                          projectId: item.project_id,
                          direction: 'down'
                        })}
                        disabled={item.position >= (queueStatus?.queue_length || 0)}
                        title="Move Down"
                      >
                        <ArrowDown className="w-4 h-4" />
                      </Button>
                      {/* Priority shortcuts */}
                      {item.priority !== 'urgent' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => reprioritizeMutation.mutate({
                            projectId: item.project_id,
                            priority: 'urgent'
                          })}
                          title="Set Urgent Priority"
                          className="text-red-400 hover:text-red-300"
                        >
                          <Zap className="w-4 h-4" />
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeMutation.mutate(item.project_id)}
                        className="text-red-400 hover:text-red-300"
                        title="Remove from Queue"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
          </div>
        )}
      </Card>

      {/* Priority Legend */}
      <Card className="p-4">
        <h4 className="text-sm font-medium text-text-primary mb-3">Priority Levels</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div className="flex items-start gap-3">
            <span className="px-2 py-0.5 rounded text-xs text-red-400 bg-red-500/10">urgent</span>
            <p className="text-text-secondary">Processed immediately, jumps queue</p>
          </div>
          <div className="flex items-start gap-3">
            <span className="px-2 py-0.5 rounded text-xs text-blue-400 bg-blue-500/10">normal</span>
            <p className="text-text-secondary">Standard FIFO processing</p>
          </div>
          <div className="flex items-start gap-3">
            <span className="px-2 py-0.5 rounded text-xs text-gray-400 bg-gray-500/10">background</span>
            <p className="text-text-secondary">Yields to higher priorities</p>
          </div>
        </div>
      </Card>
    </div>
  )
}
