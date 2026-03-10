import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Search, ExternalLink, Github, FolderOpen, CheckCircle, Play, AlertCircle, Clock } from 'lucide-react'
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
    <div className="space-y-6">
      {/* Header */}
      <div className="mb-2">
        <h1 className="text-2xl lg:text-3xl font-bold flex items-center gap-3" style={{ color: 'var(--text-primary)' }}>
          <FolderOpen className="w-7 h-7" style={{ color: 'var(--accent-primary)' }} />
          Project History
        </h1>
        <p className="mt-1" style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-base)' }}>
          All your past projects
        </p>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: 'var(--text-tertiary)' }} />
        <input
          type="text"
          placeholder="Search projects..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="glass-input w-full"
          style={{ paddingLeft: 'var(--space-10)' }}
        />
      </div>

      {/* Project List */}
      <div className="space-y-3">
        {isLoading && (
          <>
            {[1, 2, 3].map((i) => (
              <div key={i} className="skeleton h-24 w-full" />
            ))}
          </>
        )}

        {filteredProjects?.length === 0 && !isLoading && (
          <div className="glass-card text-center py-12">
            <FolderOpen className="w-12 h-12 mx-auto mb-3" style={{ color: 'var(--text-tertiary)' }} />
            <p style={{ color: 'var(--text-secondary)' }}>
              No projects found
            </p>
          </div>
        )}

        {filteredProjects?.map((project, index) => (
          <div 
            key={project.id} 
            className="glass-card animate-enter" 
            style={{ animationDelay: `${index * 50}ms` }}
          >
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
              <Link to={`/project/${project.id}`} className="flex-1">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-medium" style={{ color: 'var(--text-primary)' }}>
                      {project.name || 'Untitled Project'}
                    </h3>
                    <p className="text-sm mt-1 line-clamp-2" style={{ color: 'var(--text-secondary)' }}>
                      {project.brief}
                    </p>
                    <div className="flex items-center gap-3 mt-2" style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-xs)' }}>
                      <span className="badge badge-default">{project.project_type?.replace('_', ' ')}</span>
                      <span>{format(new Date(project.created_at), 'MMM d, yyyy')}</span>
                      {project.cost_estimate && (
                        <span style={{ color: 'var(--accent-warning)' }}>${project.cost_estimate.toFixed(2)}</span>
                      )}
                    </div>
                  </div>
                  <StatusBadge status={project.status} />
                </div>
              </Link>
              
              <div className="flex items-center gap-2 pt-3 lg:pt-0" style={{ borderTop: '1px solid var(--glass-border)' }}>
                {project.github_repo && (
                  <a
                    href={project.github_repo}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-ghost"
                    style={{ padding: 'var(--space-2)' }}
                  >
                    <Github className="w-5 h-5" />
                  </a>
                )}
                {project.live_url && (
                  <a
                    href={project.live_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-ghost"
                    style={{ padding: 'var(--space-2)', color: 'var(--accent-primary)' }}
                  >
                    <ExternalLink className="w-5 h-5" />
                  </a>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { class: string; icon: React.ReactNode }> = {
    completed: { class: 'badge-success', icon: <CheckCircle className="w-3 h-3" /> },
    running: { class: 'badge-running', icon: <Play className="w-3 h-3" /> },
    failed: { class: 'badge-error', icon: <AlertCircle className="w-3 h-3" /> },
    pending: { class: 'badge-default', icon: <Clock className="w-3 h-3" /> },
  }
  const { class: badgeClass, icon } = config[status] || config.pending
  return <span className={`badge ${badgeClass}`}>{icon}{status}</span>
}
