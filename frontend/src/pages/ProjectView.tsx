import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Card } from '@/components/Card'
import { Badge } from '@/components/Badge'
import { PipelineVisualization } from '@/components/PipelineVisualization'
import { api } from '@/lib/api'
import { ExternalLink, Github, RefreshCw } from 'lucide-react'
import { Button } from '@/components/Button'

export default function ProjectView() {
  const { id } = useParams<{ id: string }>()

  const { data: project, isLoading, refetch } = useQuery({
    queryKey: ['project', id],
    queryFn: () => api.getProject(id!),
    refetchInterval: (data) => 
      data?.status === 'completed' || data?.status === 'failed' ? false : 3000,
  })

  const { data: outputs } = useQuery({
    queryKey: ['projectOutputs', id],
    queryFn: () => api.getProjectOutputs(id!),
    enabled: !!project,
  })

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 bg-background-tertiary rounded animate-pulse" />
        <div className="h-32 bg-background-tertiary rounded-lg animate-pulse" />
      </div>
    )
  }

  if (!project) {
    return <div className="text-text-secondary">Project not found</div>
  }

  const agents = [
    { name: 'Intake', status: getAgentStatus(project.status, 'intake') },
    { name: 'Research', status: getAgentStatus(project.status, 'research') },
    { name: 'Architect', status: getAgentStatus(project.status, 'architect') },
    { name: 'Design', status: getAgentStatus(project.status, 'design') },
    { name: 'Code Gen', status: getAgentStatus(project.status, 'code_generation') },
    { name: 'Delivery', status: getAgentStatus(project.status, 'deployment') },
  ]

  return (
    <div className="space-y-6 pb-20 lg:pb-0">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-text-primary">
            {project.name || 'Untitled Project'}
          </h2>
          <p className="text-text-secondary mt-1">
            {project.project_type?.replace('_', ' ')}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={project.status} />
          <Button variant="ghost" size="sm" onClick={() => refetch()}>
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Pipeline Visualization */}
      <Card>
        <h3 className="font-medium text-text-primary mb-4">Pipeline Progress</h3>
        <PipelineVisualization agents={agents} />
      </Card>

      {/* Links */}
      {(project.github_repo || project.live_url) && (
        <div className="flex flex-wrap gap-3">
          {project.github_repo && (
            <a
              href={project.github_repo}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 bg-background-tertiary rounded-lg text-text-primary hover:bg-border-subtle transition-colors"
            >
              <Github className="w-4 h-4" />
              View on GitHub
            </a>
          )}
          {project.live_url && (
            <a
              href={project.live_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 bg-accent-primary/20 rounded-lg text-accent-primary hover:bg-accent-primary/30 transition-colors"
            >
              <ExternalLink className="w-4 h-4" />
              View Live Site
            </a>
          )}
        </div>
      )}

      {/* Brief */}
      <Card>
        <h3 className="font-medium text-text-primary mb-2">Project Brief</h3>
        <p className="text-text-secondary text-sm whitespace-pre-wrap">
          {project.brief}
        </p>
      </Card>

      {/* Agent Outputs */}
      {outputs?.agent_outputs && Object.keys(outputs.agent_outputs).length > 0 && (
        <Card>
          <h3 className="font-medium text-text-primary mb-4">Agent Outputs</h3>
          <div className="space-y-4">
            {Object.entries(outputs.agent_outputs).map(([agent, output]) => (
              <details key={agent} className="group">
                <summary className="cursor-pointer text-sm font-medium text-text-secondary hover:text-text-primary">
                  {agent.charAt(0).toUpperCase() + agent.slice(1).replace('_', ' ')}
                </summary>
                <pre className="mt-2 p-3 bg-background-tertiary rounded-lg text-xs text-text-secondary overflow-x-auto">
                  {JSON.stringify(output, null, 2)}
                </pre>
              </details>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}

function getAgentStatus(projectStatus: string, agent: string): 'queued' | 'active' | 'completed' | 'failed' {
  const order = ['pending', 'intake', 'research', 'architect', 'design', 'code_generation', 'deployment', 'completed']
  const currentIndex = order.indexOf(projectStatus)
  const agentIndex = order.indexOf(agent)

  if (projectStatus === 'failed') return 'failed'
  if (projectStatus === 'completed') return 'completed'
  if (agentIndex < currentIndex) return 'completed'
  if (agentIndex === currentIndex) return 'active'
  return 'queued'
}

function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, 'success' | 'warning' | 'error' | 'info' | 'default'> = {
    completed: 'success',
    intake: 'info',
    research: 'info',
    architect: 'info',
    design: 'info',
    code_generation: 'info',
    deployment: 'info',
    failed: 'error',
    pending: 'default',
  }
  return (
    <Badge variant={variants[status] || 'default'} pulse={variants[status] === 'info'}>
      {status.replace('_', ' ')}
    </Badge>
  )
}
