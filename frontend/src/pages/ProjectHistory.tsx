import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Card } from '@/components/Card'
import { Badge } from '@/components/Badge'
import { Input } from '@/components/Input'
import { api } from '@/lib/api'
import { Search, ExternalLink, Github } from 'lucide-react'
import { useState } from 'react'
import { format } from 'date-fns'

export default function ProjectHistory() {
  const [search, setSearch] = useState('')

  const { data: projects, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.getProjects({ limit: 50 }),
  })

  const filteredProjects = projects?.filter(
    (p) =>
      p.name?.toLowerCase().includes(search.toLowerCase()) ||
      p.brief.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-6 pb-20 lg:pb-0">
      <div>
        <h2 className="text-2xl font-semibold text-text-primary">Project History</h2>
        <p className="text-text-secondary mt-1">All your past projects</p>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-tertiary" />
        <input
          type="text"
          placeholder="Search projects..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2.5 bg-background-input border border-border-subtle rounded-[10px] text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-border-focus"
        />
      </div>

      {/* Project List */}
      <div className="space-y-3">
        {isLoading && (
          <>
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-24 bg-background-tertiary rounded-lg animate-pulse" />
            ))}
          </>
        )}

        {filteredProjects?.length === 0 && !isLoading && (
          <Card>
            <p className="text-center text-text-secondary py-8">
              No projects found
            </p>
          </Card>
        )}

        {filteredProjects?.map((project) => (
          <Card key={project.id} className="hover:border-border-focus/50 transition-colors">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
              <Link to={`/project/${project.id}`} className="flex-1">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-medium text-text-primary">
                      {project.name || 'Untitled Project'}
                    </h3>
                    <p className="text-sm text-text-secondary mt-1 line-clamp-2">
                      {project.brief}
                    </p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-text-tertiary">
                      <span>{project.project_type?.replace('_', ' ')}</span>
                      <span>•</span>
                      <span>{format(new Date(project.created_at), 'MMM d, yyyy')}</span>
                      {project.cost_estimate && (
                        <>
                          <span>•</span>
                          <span>${project.cost_estimate.toFixed(2)}</span>
                        </>
                      )}
                    </div>
                  </div>
                  <StatusBadge status={project.status} />
                </div>
              </Link>
              
              <div className="flex items-center gap-2 pt-2 lg:pt-0 border-t lg:border-t-0 border-border-subtle">
                {project.github_repo && (
                  <a
                    href={project.github_repo}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2 rounded-lg hover:bg-background-tertiary text-text-secondary"
                  >
                    <Github className="w-5 h-5" />
                  </a>
                )}
                {project.live_url && (
                  <a
                    href={project.live_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2 rounded-lg hover:bg-background-tertiary text-accent-primary"
                  >
                    <ExternalLink className="w-5 h-5" />
                  </a>
                )}
              </div>
            </div>
          </Card>
        ))}
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
