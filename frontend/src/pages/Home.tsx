import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Sparkles, ArrowRight, CheckCircle, Play, Clock, AlertCircle,
  Key, MessageSquare, FolderOpen
} from 'lucide-react'
import { api } from '@/lib/api'

export default function Home() {
  const navigate = useNavigate()

  const { data: projects, isLoading: loadingProjects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.getProjects({ limit: 10 }),
  })

  const { data: missingKeys } = useQuery({
    queryKey: ['missingRequiredKeys'],
    queryFn: async () => {
      const res = await fetch('/api/api-keys/missing-required', { credentials: 'include' })
      if (!res.ok) return { missing: [], count: 0 }
      return res.json()
    },
    staleTime: 60_000,
  })

  const activeProjects = projects?.filter(p => p.status === 'running' || p.status === 'pending') || []

  return (
    <div className="space-y-6">
      {/* Missing required API keys banner */}
      {missingKeys && missingKeys.count > 0 && (
        <div className="glass-card flex items-start gap-3" style={{
          background: 'rgba(248, 113, 113, 0.1)',
          borderColor: 'rgba(248, 113, 113, 0.3)',
        }}>
          <Key className="w-5 h-5 mt-0.5 flex-shrink-0" style={{ color: 'var(--accent-error)' }} />
          <div className="flex-1">
            <p className="font-medium" style={{ color: 'var(--accent-error)' }}>
              Required API keys missing — pipeline will not run
            </p>
            <p className="text-sm mt-0.5" style={{ color: 'var(--text-secondary)' }}>
              {missingKeys.missing.map((k: any) => k.label).join(', ')} must be configured in{' '}
              <Link to="/settings" className="underline" style={{ color: 'var(--accent-primary)' }}>
                Settings
              </Link>
              .
            </p>
          </div>
        </div>
      )}

      {/* Hero — Start Building CTA */}
      <div
        className="glass-card-elevated cursor-pointer group"
        style={{ minHeight: '200px' }}
        onClick={() => navigate('/chat')}
      >
        <div className="bloom-content flex flex-col items-center justify-center text-center py-8">
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-6"
               style={{ background: 'var(--gradient-accent)', boxShadow: 'var(--shadow-glow)' }}>
            <Sparkles className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl lg:text-3xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>
            What do you want to build?
          </h1>
          <p className="mb-6" style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-base)', maxWidth: '400px' }}>
            Describe your project and 20 AI agents will build it for you.
          </p>
          <div className="btn-primary group-hover:shadow-lg transition-shadow"
               style={{ padding: 'var(--space-3) var(--space-6)' }}>
            <MessageSquare className="w-4 h-4" />
            Start Building
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </div>
        </div>
      </div>

      {/* Active builds */}
      {activeProjects.length > 0 && (
        <div>
          <h2 className="font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>
            Active Builds
          </h2>
          <div className="space-y-2">
            {activeProjects.map((project) => (
              <Link
                key={project.id}
                to={`/chat/${project.id}`}
                className="glass-card block"
                style={{ padding: 'var(--space-3) var(--space-4)' }}
              >
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <h4 className="font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                      {project.name || 'Untitled Project'}
                    </h4>
                    <p className="text-sm truncate" style={{ color: 'var(--text-tertiary)' }}>
                      {project.brief?.slice(0, 80)}
                    </p>
                  </div>
                  <span className="badge badge-running">
                    <Play className="w-3 h-3" />
                    Building
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Recent projects */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold" style={{ color: 'var(--text-primary)' }}>
            Recent Projects
          </h2>
          <Link to="/projects" className="btn-ghost text-sm flex items-center gap-1"
                style={{ color: 'var(--accent-primary)' }}>
            View all <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        {loadingProjects ? (
          <div className="space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="skeleton h-16 w-full" />
            ))}
          </div>
        ) : !projects?.length ? (
          <div className="glass-card text-center py-12">
            <FolderOpen className="w-10 h-10 mx-auto mb-3" style={{ color: 'var(--text-tertiary)' }} />
            <p style={{ color: 'var(--text-secondary)' }}>
              No projects yet. Start your first build!
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {projects.slice(0, 6).map((project, index) => (
              <Link
                key={project.id}
                to={`/project/${project.id}`}
                className="glass-card block animate-enter"
                style={{
                  padding: 'var(--space-3) var(--space-4)',
                  animationDelay: `${index * 50}ms`
                }}
              >
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <h4 className="font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                      {project.name || 'Untitled Project'}
                    </h4>
                    <p className="text-sm truncate" style={{ color: 'var(--text-tertiary)' }}>
                      {project.brief?.slice(0, 80)}
                    </p>
                  </div>
                  <StatusBadge status={project.status} />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { class: string; icon: React.ReactNode }> = {
    completed: {
      class: 'badge-success',
      icon: <CheckCircle className="w-3 h-3" />
    },
    running: {
      class: 'badge-running',
      icon: <Play className="w-3 h-3" />
    },
    failed: {
      class: 'badge-error',
      icon: <AlertCircle className="w-3 h-3" />
    },
    pending: {
      class: 'badge-default',
      icon: <Clock className="w-3 h-3" />
    },
  }

  const { class: badgeClass, icon } = config[status] || config.pending

  return (
    <span className={`badge ${badgeClass}`}>
      {icon}
      {status}
    </span>
  )
}
