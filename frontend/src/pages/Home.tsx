import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Card } from '@/components/Card'
import { Button } from '@/components/Button'
import { Badge } from '@/components/Badge'
import { PlusCircle, Zap, DollarSign, CheckCircle } from 'lucide-react'
import { api } from '@/lib/api'

export default function Home() {
  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.getProjects({ limit: 5 }),
  })

  const { data: costSummary } = useQuery({
    queryKey: ['costSummary'],
    queryFn: api.getCostSummary,
  })

  return (
    <div className="space-y-6 pb-20 lg:pb-0">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-semibold text-text-primary">Welcome back</h2>
        <p className="text-text-secondary mt-1">Build software with AI agents</p>
      </div>

      {/* Quick Actions */}
      <Link to="/new">
        <Card className="hover:border-accent-primary/50 transition-colors cursor-pointer">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-accent-primary to-accent-secondary flex items-center justify-center">
              <PlusCircle className="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-text-primary">Start New Project</h3>
              <p className="text-sm text-text-secondary">Describe what you want to build</p>
            </div>
          </div>
        </Card>
      </Link>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <Card padding="sm">
          <div className="flex items-center gap-3">
            <Zap className="w-5 h-5 text-accent-primary" />
            <div>
              <p className="text-2xl font-semibold text-text-primary">
                {projects?.length || 0}
              </p>
              <p className="text-xs text-text-secondary">Total Projects</p>
            </div>
          </div>
        </Card>
        <Card padding="sm">
          <div className="flex items-center gap-3">
            <CheckCircle className="w-5 h-5 text-accent-success" />
            <div>
              <p className="text-2xl font-semibold text-text-primary">
                {projects?.filter(p => p.status === 'completed').length || 0}
              </p>
              <p className="text-xs text-text-secondary">Deployed</p>
            </div>
          </div>
        </Card>
        <Card padding="sm" className="col-span-2 lg:col-span-1">
          <div className="flex items-center gap-3">
            <DollarSign className="w-5 h-5 text-accent-warning" />
            <div>
              <p className="text-2xl font-semibold text-text-primary">
                ${costSummary?.total_cost?.toFixed(2) || '0.00'}
              </p>
              <p className="text-xs text-text-secondary">Total Spent</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Recent Projects */}
      <div>
        <h3 className="text-lg font-semibold text-text-primary mb-3">Recent Projects</h3>
        <div className="space-y-3">
          {projects?.length === 0 && (
            <Card>
              <p className="text-center text-text-secondary py-8">
                No projects yet. Start your first one!
              </p>
            </Card>
          )}
          {projects?.map((project) => (
            <Link key={project.id} to={`/project/${project.id}`}>
              <Card className="hover:border-border-focus/50 transition-colors cursor-pointer">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium text-text-primary">
                      {project.name || 'Untitled Project'}
                    </h4>
                    <p className="text-sm text-text-secondary truncate max-w-xs">
                      {project.brief.slice(0, 80)}...
                    </p>
                  </div>
                  <StatusBadge status={project.status} />
                </div>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, 'success' | 'warning' | 'error' | 'info' | 'default'> = {
    completed: 'success',
    running: 'info',
    failed: 'error',
    pending: 'default',
  }
  return <Badge variant={variants[status] || 'default'}>{status}</Badge>
}
