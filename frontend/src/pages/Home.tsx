import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  PlusCircle,
  Zap,
  DollarSign,
  CheckCircle,
  Rocket,
  TrendingUp,
  Calendar,
  ArrowRight,
  Play,
  Clock,
  AlertCircle,
  Key
} from 'lucide-react'
import { api } from '@/lib/api'

export default function Home() {
  const { data: projects, isLoading: loadingProjects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.getProjects({ limit: 5 }),
  })

  const { data: costSummary, isLoading: loadingCosts } = useQuery({
    queryKey: ['costSummary'],
    queryFn: api.getCostSummary,
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
  const completedProjects = projects?.filter(p => p.status === 'completed') || []
  const currentBuild = activeProjects[0]

  return (
    <div className="space-y-6">
      {/* Missing required API keys banner */}
      {missingKeys && missingKeys.count > 0 && (
        <div className="glass-card flex items-start gap-3 bg-accent-error/10 border-accent-error/30">
          <Key className="w-5 h-5 mt-0.5 flex-shrink-0" style={{ color: 'var(--accent-error)' }} />
          <div className="flex-1">
            <p className="font-medium" style={{ color: 'var(--accent-error)' }}>
              Required API keys missing — pipeline will not run
            </p>
            <p className="text-sm mt-0.5" style={{ color: 'var(--text-secondary)' }}>
              {missingKeys.missing.map((k: any) => k.label).join(', ')} must be configured in{' '}
              <Link to="/settings" className="underline" style={{ color: 'var(--accent-primary)' }}>
                Settings → API Keys
              </Link>
              .
            </p>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl lg:text-3xl font-bold" style={{ color: 'var(--text-primary)' }}>
          Welcome back
        </h1>
        <p className="mt-1" style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-base)' }}>
          Build software with AI agents
        </p>
      </div>

      {/* Bento Grid */}
      <div className="bento-grid">
        
        {/* Hero Input Card - Spans 2 columns */}
        <Link to="/new" className="bento-item span-2">
          <div className="glass-card-elevated h-full cursor-pointer group" style={{ minHeight: '180px' }}>
            <div className="bloom-content flex flex-col h-full">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 rounded-xl flex items-center justify-center"
                     style={{ background: 'var(--gradient-accent)' }}>
                  <PlusCircle className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h2 className="font-semibold text-lg" style={{ color: 'var(--text-primary)' }}>
                    Start New Project
                  </h2>
                  <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
                    Describe what you want built
                  </p>
                </div>
              </div>
              
              <div className="glass-input-hero flex items-center gap-3 mt-auto group-hover:border-accent-primary transition-colors"
                   style={{ cursor: 'pointer' }}>
                <span style={{ color: 'var(--text-tertiary)' }}>What do you want built?</span>
                <ArrowRight className="w-5 h-5 ml-auto opacity-50 group-hover:opacity-100 transition-opacity"
                           style={{ color: 'var(--accent-primary)' }} />
              </div>
            </div>
          </div>
        </Link>

        {/* Active Projects Stat */}
        <div className="bento-item">
          <div className="stat-card h-full">
            <div className="stat-card-icon">
              <Zap className="w-5 h-5" />
            </div>
            <div className="stat-card-value">
              {loadingProjects ? '-' : activeProjects.length}
            </div>
            <div className="stat-card-label">Active Projects</div>
            {activeProjects.length > 0 && (
              <div className="stat-card-change positive">
                <TrendingUp className="w-3 h-3 inline mr-1" />
                In progress
              </div>
            )}
          </div>
        </div>

        {/* Deployed Stat */}
        <div className="bento-item">
          <div className="stat-card h-full">
            <div className="stat-card-icon bg-accent-success/15">
              <Rocket className="w-5 h-5 text-accent-success" />
            </div>
            <div className="stat-card-value">
              {loadingProjects ? '-' : completedProjects.length}
            </div>
            <div className="stat-card-label">Total Deployed</div>
          </div>
        </div>

        {/* Cost Stat */}
        <div className="bento-item">
          <div className="stat-card h-full">
            <div className="stat-card-icon bg-accent-warning/15">
              <DollarSign className="w-5 h-5 text-accent-warning" />
            </div>
            <div className="stat-card-value">
              ${loadingCosts ? '-' : (costSummary?.total_cost?.toFixed(2) || '0.00')}
            </div>
            <div className="stat-card-label">Total Spent</div>
          </div>
        </div>

        {/* This Month */}
        <div className="bento-item">
          <div className="stat-card h-full">
            <div className="stat-card-icon bg-accent-secondary/15">
              <Calendar className="w-5 h-5 text-accent-secondary" />
            </div>
            <div className="stat-card-value">
              {loadingProjects ? '-' : projects?.length || 0}
            </div>
            <div className="stat-card-label">This Month</div>
          </div>
        </div>

        {/* Current Build Card - Spans 2 columns */}
        {currentBuild && (
          <div className="bento-item span-2">
            <div className="glass-card h-full">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                  Current Build
                </h3>
                <span className="badge badge-running">
                  <Play className="w-3 h-3" />
                  Building
                </span>
              </div>
              
              <Link to={`/project/${currentBuild.id}`} className="block">
                <div className="glass-card" style={{ padding: 'var(--space-4)' }}>
                  <h4 className="font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
                    {currentBuild.name || 'Untitled Project'}
                  </h4>
                  <p className="text-sm mb-3" style={{ color: 'var(--text-secondary)' }}>
                    {currentBuild.brief?.slice(0, 100)}...
                  </p>
                  
                  {/* Mini Pipeline */}
                  <div className="flex items-center gap-2">
                    {['Intake', 'Architect', 'Code', 'Deploy'].map((step, i) => (
                      <div key={step} className="flex items-center">
                        <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs
                          ${i === 0 ? 'bg-accent-success/20 text-accent-success' :
                            i === 1 ? 'bg-accent-primary/20 text-accent-primary' :
                            'bg-bg-secondary text-text-tertiary'}`}>
                          {i < 2 ? '✓' : i + 1}
                        </div>
                        {i < 3 && (
                          <div className={`w-8 h-0.5 ${i < 1 ? 'bg-accent-success/50' : 'bg-border-subtle'}`} />
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </Link>
            </div>
          </div>
        )}

        {/* Recent Projects Card - Spans 2 columns */}
        <div className={`bento-item span-2 ${!currentBuild ? 'col-span-4' : ''}`}>
          <div className="glass-card h-full">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                Recent Projects
              </h3>
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
            ) : projects?.length === 0 ? (
              <div className="glass-card text-center py-8" style={{ background: 'var(--glass-bg)' }}>
                <AlertCircle className="w-10 h-10 mx-auto mb-3" style={{ color: 'var(--text-tertiary)' }} />
                <p style={{ color: 'var(--text-secondary)' }}>
                  No projects yet. Start your first one!
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {projects?.slice(0, 4).map((project, index) => (
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
                          {project.brief?.slice(0, 60)}...
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
