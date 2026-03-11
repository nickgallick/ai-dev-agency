import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card } from '@/components/Card'
import { Badge } from '@/components/Badge'
import { PipelineVisualization } from '@/components/PipelineVisualization'
import { PipelineDAG } from '@/components/PipelineDAG'
import { ScoreGauge } from '@/components/ScoreGauge'
import { ActivityFeed } from '@/components/ActivityFeed'
import { api } from '@/lib/api'
import { ExternalLink, Github, RefreshCw, CheckCircle, XCircle, AlertTriangle, Rocket, TestTube, Activity, FileText, BarChart3, Shield, Gauge, ClipboardCheck, Code2, Globe, Pause, Play, RotateCcw, Settings2, DollarSign, Zap, Clock, ArrowLeftRight, MessageCircle, Send, HelpCircle, GitBranch, Brain, Monitor, Share2 } from 'lucide-react'
import { Button } from '@/components/Button'
import { ArtifactViewer } from '@/components/ArtifactViewer'
import { AgentOutputTimeline } from '@/components/AgentOutputTimeline'
import { ProjectTimeline } from '@/components/ProjectTimeline'
import { ProjectMemory } from '@/components/ProjectMemory'
import { BrowserTestPanel } from '@/components/BrowserTestPanel'
import { ShareLinkPanel } from '@/components/ShareLinkPanel'
import { DesignImportPanel } from '@/components/DesignImportPanel'
import { lazy, Suspense, useState, useCallback } from 'react'

// Code-split Monaco diff editor — only loaded when user clicks "Compare Outputs"
const AgentOutputDiffModal = lazy(() =>
  import('@/components/MonacoDiffEditor').then((m) => ({ default: m.AgentOutputDiffModal }))
)

export default function ProjectView() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const [showCheckpointModal, setShowCheckpointModal] = useState(false)
  const [editingOutput, setEditingOutput] = useState<string | null>(null)
  const [showDiffModal, setShowDiffModal] = useState(false)
  const [clarificationAnswer, setClarificationAnswer] = useState('')
  const [answeringClarification, setAnsweringClarification] = useState(false)
  const [editedOutputText, setEditedOutputText] = useState('')

  const { data: project, isLoading, refetch } = useQuery({
    queryKey: ['project', id],
    queryFn: () => api.getProject(id!),
    refetchInterval: (query) => 
      query.state.data?.status === 'completed' || query.state.data?.status === 'failed' ? false : 3000,
  })

  const { data: outputs } = useQuery({
    queryKey: ['projectOutputs', id],
    queryFn: () => api.getProjectOutputs(id!),
    enabled: !!project,
    refetchInterval: (query) => {
      const status = query.state.data
      // Poll every 4s while building so agent output cards fill in live
      if (project?.status === 'completed' || project?.status === 'failed') return false
      return 4000
    },
  })

  // Per-agent cost & token tracking
  const { data: agentLogs } = useQuery({
    queryKey: ['agentLogs', id],
    queryFn: () => api.getAgentLogs({ project_id: id! }),
    enabled: !!project,
    refetchInterval: (query) => {
      if (project?.status === 'completed' || project?.status === 'failed') return false
      return 5000
    },
  })

  // Phase 11C: Checkpoint status
  const { data: checkpointStatus } = useQuery({
    queryKey: ['checkpointStatus', id],
    queryFn: () => api.getCheckpointStatus(id!),
    enabled: !!project && project.status !== 'completed' && project.status !== 'failed',
    refetchInterval: 5000,
  })

  // Mid-pipeline clarification interrupt status
  const { data: interruptStatus } = useQuery({
    queryKey: ['interruptStatus', id],
    queryFn: () => api.getInterruptStatus(id!),
    enabled: !!project && project.status !== 'completed' && project.status !== 'failed',
    refetchInterval: 3000,
  })

  const handleAnswerClarification = async () => {
    if (!clarificationAnswer.trim() || !id) return
    setAnsweringClarification(true)
    try {
      await api.answerInterrupt(id, clarificationAnswer)
      setClarificationAnswer('')
      queryClient.invalidateQueries({ queryKey: ['interruptStatus', id] })
      refetch()
    } catch (e) {
      console.error('Failed to answer clarification:', e)
    } finally {
      setAnsweringClarification(false)
    }
  }

  // Checkpoint mutations
  const pauseMutation = useMutation({
    mutationFn: () => api.pauseProject(id!),
    onSuccess: () => {
      refetch()
      queryClient.invalidateQueries({ queryKey: ['checkpointStatus', id] })
    },
  })

  const resumeMutation = useMutation({
    mutationFn: () => api.resumeProject(id!),
    onSuccess: () => {
      refetch()
      queryClient.invalidateQueries({ queryKey: ['checkpointStatus', id] })
    },
  })

  const setModeMutation = useMutation({
    mutationFn: (mode: string) => api.setCheckpointMode(id!, mode),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['checkpointStatus', id] })
    },
  })

  const resumeWithEditMutation = useMutation({
    mutationFn: (editedOutput: Record<string, any>) => api.resumeProject(id!, editedOutput),
    onSuccess: () => {
      setEditingOutput(null)
      setEditedOutputText('')
      refetch()
      queryClient.invalidateQueries({ queryKey: ['checkpointStatus', id] })
    },
  })

  const restartFromMutation = useMutation({
    mutationFn: (agentName: string) => api.restartFromAgent(id!, agentName),
    onSuccess: () => {
      refetch()
      queryClient.invalidateQueries({ queryKey: ['checkpointStatus', id] })
    },
  })

  const handleApproveCheckpoint = useCallback(() => {
    resumeMutation.mutate()
  }, [resumeMutation])

  const handleApproveWithEdits = useCallback(() => {
    try {
      const parsed = JSON.parse(editedOutputText)
      resumeWithEditMutation.mutate(parsed)
    } catch {
      // If not valid JSON, wrap as a simple edit
      resumeWithEditMutation.mutate({ edited_content: editedOutputText })
    }
  }, [editedOutputText, resumeWithEditMutation])

  const handleRejectCheckpoint = useCallback(() => {
    const pausedAgent = checkpointStatus?.paused_at_agent
    if (pausedAgent) {
      restartFromMutation.mutate(pausedAgent)
    }
  }, [checkpointStatus, restartFromMutation])

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
    { name: 'PM Check 1', status: getAgentStatus(project.status, 'pm_checkpoint_1') },  // ★ New
    { name: 'Code Gen', status: getAgentStatus(project.status, 'code_generation') },
    { name: 'PM Check 2', status: getAgentStatus(project.status, 'pm_checkpoint_2') },  // ★ New
    { name: 'Code Review', status: getAgentStatus(project.status, 'code_review') },    // ★ New
    { name: 'Security', status: getAgentStatus(project.status, 'security') },
    { name: 'QA Test', status: getAgentStatus(project.status, 'qa') },
    { name: 'Deploy', status: getAgentStatus(project.status, 'deployment') },
    { name: 'Verify', status: getAgentStatus(project.status, 'post_deploy_verification') },  // ★ New
    { name: 'Monitoring', status: getAgentStatus(project.status, 'analytics_monitoring') },
    { name: 'Standards', status: getAgentStatus(project.status, 'coding_standards') },
  ]

  // Extract deployment data for links section
  const deploymentReport = outputs?.agent_outputs?.deployment?.report

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

      {/* Real-Time Pipeline DAG */}
      <Card className="!p-0 overflow-hidden">
        <PipelineDAG
          projectId={id!}
          projectStatus={project.status}
        />
      </Card>

      {/* Fallback compact view (mobile / accessibility) */}
      <details className="group">
        <summary className="cursor-pointer text-sm font-medium text-text-secondary hover:text-text-primary px-1 py-2">
          Show compact pipeline list
        </summary>
        <Card>
          <PipelineVisualization agents={agents} />
        </Card>
      </details>

      {/* Real-time Activity Feed + Live Agent Outputs (side by side on desktop during builds) */}
      {project.status !== 'completed' && project.status !== 'failed' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Activity Feed - left column */}
          <Card>
            <h3 className="font-medium text-text-primary mb-4 flex items-center gap-2">
              <Activity className="w-5 h-5 text-accent-primary" />
              Live Activity
            </h3>
            <ActivityFeed
              projectId={id!}
              isActive={project.status !== 'completed' && project.status !== 'failed'}
            />
          </Card>

          {/* Live Agent Outputs - right column */}
          <Card>
            <h3 className="font-medium text-text-primary mb-4 flex items-center gap-2">
              <Code2 className="w-5 h-5 text-accent-primary" />
              Agent Outputs (Live)
            </h3>
            <div className="max-h-[500px] overflow-y-auto">
              <AgentOutputTimeline
                projectStatus={project.status}
                agentOutputs={outputs?.agent_outputs || {}}
              />
            </div>
          </Card>
        </div>
      )}

      {/* Phase 11C: Build Controls & HITL Approval Gates */}
      {project.status !== 'completed' && project.status !== 'failed' && (
        <Card>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Settings2 className="w-5 h-5 text-accent-primary" />
              <h3 className="font-medium text-text-primary">Build Controls</h3>
            </div>
            {checkpointStatus && (
              <Badge variant={checkpointStatus.state === 'paused' ? 'warning' : checkpointStatus.state === 'running' ? 'info' : 'default'}>
                {checkpointStatus.state}
              </Badge>
            )}
          </div>

          <div className="flex flex-wrap gap-3 mb-4">
            {/* Pause/Resume Button — only show when NOT at a HITL checkpoint */}
            {!(checkpointStatus?.state === 'paused' && checkpointStatus?.current_checkpoint) && (
              project.status === 'paused' ? (
                <Button
                  onClick={() => resumeMutation.mutate()}
                  disabled={resumeMutation.isPending}
                  variant="primary"
                  size="sm"
                >
                  <Play className="w-4 h-4 mr-2" />
                  Resume Build
                </Button>
              ) : (
                <Button
                  onClick={() => pauseMutation.mutate()}
                  disabled={pauseMutation.isPending}
                  variant="secondary"
                  size="sm"
                >
                  <Pause className="w-4 h-4 mr-2" />
                  Pause Build
                </Button>
              )
            )}

            {/* Autonomy Tier Selector (#26) */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-text-secondary">Autonomy:</span>
              <select
                value={
                  (checkpointStatus as any)?.custom_checkpoints?.length > 5
                    ? 'supervised-tier'
                    : (checkpointStatus as any)?.custom_checkpoints?.length > 0
                    ? 'guided-tier'
                    : checkpointStatus?.mode || 'auto'
                }
                onChange={(e) => {
                  const val = e.target.value
                  if (val === 'supervised-tier') {
                    setModeMutation.mutate('manual')
                  } else if (val === 'guided-tier') {
                    setModeMutation.mutate('manual')
                  } else {
                    setModeMutation.mutate(val)
                  }
                }}
                className="bg-background-tertiary border border-border-subtle rounded px-2 py-1 text-sm text-text-primary"
              >
                <option value="auto">Autonomous (no checkpoints)</option>
                <option value="guided-tier">Guided (5 critical checkpoints)</option>
                <option value="supervised-tier">Supervised (every agent)</option>
                <option value="manual">Manual (custom checkpoints)</option>
              </select>
            </div>
          </div>

          {/* ── Mid-Pipeline Clarification Interrupt ───────────────── */}
          {interruptStatus?.has_question && (
            <div className="p-4 bg-purple-500/10 rounded-lg border border-purple-500/30">
              <div className="flex items-center gap-2 mb-3">
                <HelpCircle className="w-5 h-5 text-purple-400" />
                <span className="font-semibold text-purple-400">
                  Clarification Needed — {interruptStatus.agent_name?.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())}
                </span>
              </div>

              <p className="text-sm text-text-primary mb-2 font-medium">
                {interruptStatus.question}
              </p>

              {interruptStatus.context && (
                <p className="text-xs text-text-tertiary mb-3 italic">
                  Context: {interruptStatus.context}
                </p>
              )}

              <div className="flex gap-2">
                <input
                  type="text"
                  value={clarificationAnswer}
                  onChange={(e) => setClarificationAnswer(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') handleAnswerClarification() }}
                  placeholder="Type your answer..."
                  className="flex-1 px-3 py-2 bg-background-secondary border border-border-subtle rounded-lg text-sm text-text-primary"
                />
                <Button
                  onClick={handleAnswerClarification}
                  disabled={!clarificationAnswer.trim() || answeringClarification}
                  variant="primary"
                  size="sm"
                >
                  <Send className="w-4 h-4 mr-1" />
                  Answer
                </Button>
              </div>
            </div>
          )}

          {/* ── HITL Approval Gate ────────────────────────────────── */}
          {checkpointStatus?.state === 'paused' && checkpointStatus?.current_checkpoint && (
            <div className="p-4 bg-yellow-500/10 rounded-lg border border-yellow-500/30">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="w-5 h-5 text-yellow-400" />
                <span className="font-semibold text-yellow-400">
                  Approval Required — {checkpointStatus.paused_at_agent?.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())}
                </span>
              </div>

              <p className="text-sm text-text-secondary mb-3">
                The pipeline has paused after <strong className="text-text-primary">{checkpointStatus.paused_at_agent}</strong>.
                Review the output below and choose to approve, edit, or reject.
              </p>

              <p className="text-xs text-text-tertiary mb-4">
                Paused at: {checkpointStatus.paused_at ? new Date(checkpointStatus.paused_at).toLocaleString() : 'N/A'}
                {' — '}Auto-continues in 5 minutes if not acted upon.
              </p>

              {/* Agent Output Preview */}
              {checkpointStatus.current_checkpoint?.output_data && (
                <details className="group mb-4" open>
                  <summary className="cursor-pointer text-sm font-medium text-text-secondary hover:text-text-primary mb-2">
                    Agent Output
                  </summary>
                  <pre className="p-3 bg-background-secondary rounded-lg text-xs text-text-secondary overflow-x-auto max-h-64 overflow-y-auto whitespace-pre-wrap border border-border-subtle">
                    {JSON.stringify(checkpointStatus.current_checkpoint.output_data, null, 2)}
                  </pre>
                </details>
              )}

              {/* Edit Mode */}
              {editingOutput === checkpointStatus.paused_at_agent && (
                <div className="mb-4">
                  <label className="block text-sm font-medium text-text-secondary mb-1">
                    Edit Output (JSON)
                  </label>
                  <textarea
                    value={editedOutputText}
                    onChange={(e) => setEditedOutputText(e.target.value)}
                    className="w-full h-40 p-3 bg-background-secondary border border-border-subtle rounded-lg text-xs text-text-primary font-mono resize-y"
                    placeholder="Edit the agent output JSON..."
                  />
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex flex-wrap gap-2">
                <Button
                  onClick={handleApproveCheckpoint}
                  disabled={resumeMutation.isPending}
                  variant="primary"
                  size="sm"
                >
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Approve & Continue
                </Button>

                {editingOutput === checkpointStatus.paused_at_agent ? (
                  <>
                    <Button
                      onClick={handleApproveWithEdits}
                      disabled={resumeWithEditMutation.isPending}
                      variant="primary"
                      size="sm"
                    >
                      <Play className="w-4 h-4 mr-2" />
                      Apply Edits & Continue
                    </Button>
                    <Button
                      onClick={() => { setEditingOutput(null); setEditedOutputText('') }}
                      variant="ghost"
                      size="sm"
                    >
                      Cancel Edit
                    </Button>
                  </>
                ) : (
                  <Button
                    onClick={() => {
                      setEditingOutput(checkpointStatus.paused_at_agent || null)
                      setEditedOutputText(
                        JSON.stringify(checkpointStatus.current_checkpoint?.output_data || {}, null, 2)
                      )
                    }}
                    variant="secondary"
                    size="sm"
                  >
                    <Code2 className="w-4 h-4 mr-2" />
                    Edit Output
                  </Button>
                )}

                <Button
                  onClick={handleRejectCheckpoint}
                  disabled={restartFromMutation.isPending}
                  variant="ghost"
                  size="sm"
                  className="text-red-400 hover:text-red-300"
                >
                  <RotateCcw className="w-4 h-4 mr-2" />
                  Reject & Re-run
                </Button>
              </div>
            </div>
          )}

          {/* Available Checkpoints Info */}
          {checkpointStatus?.mode !== 'auto' && checkpointStatus?.state !== 'paused' && (
            <div className="mt-3 text-xs text-text-secondary">
              <span className="font-medium">Checkpoint agents:</span>{' '}
              {(checkpointStatus?.custom_checkpoints?.length
                ? checkpointStatus.custom_checkpoints
                : checkpointStatus?.available_checkpoints
              )?.join(', ')}
            </div>
          )}
        </Card>
      )}

      {/* Per-Agent Cost & Token Tracking */}
      {agentLogs && agentLogs.length > 0 && (
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <DollarSign className="w-5 h-5 text-accent-primary" />
            <h3 className="font-medium text-text-primary">Cost & Token Tracking</h3>
          </div>

          {/* Summary Stats */}
          {(() => {
            const totalCost = agentLogs.reduce((sum: number, l: any) => sum + (l.cost || 0), 0)
            const totalTokens = agentLogs.reduce((sum: number, l: any) => sum + (l.total_tokens || 0), 0)
            const totalPrompt = agentLogs.reduce((sum: number, l: any) => sum + (l.prompt_tokens || 0), 0)
            const totalCompletion = agentLogs.reduce((sum: number, l: any) => sum + (l.completion_tokens || 0), 0)
            const totalDuration = agentLogs.reduce((sum: number, l: any) => sum + (l.duration_ms || 0), 0)

            return (
              <>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
                  <div className="bg-accent-primary/10 rounded-lg p-3 text-center">
                    <div className="text-xl font-bold text-accent-primary">${totalCost.toFixed(4)}</div>
                    <div className="text-xs text-text-secondary">Total Cost</div>
                  </div>
                  <div className="bg-background-tertiary rounded-lg p-3 text-center">
                    <div className="text-xl font-bold text-text-primary">{totalTokens.toLocaleString()}</div>
                    <div className="text-xs text-text-secondary">Total Tokens</div>
                  </div>
                  <div className="bg-background-tertiary rounded-lg p-3 text-center">
                    <div className="text-lg font-bold text-text-primary">
                      {totalPrompt.toLocaleString()} / {totalCompletion.toLocaleString()}
                    </div>
                    <div className="text-xs text-text-secondary">Prompt / Completion</div>
                  </div>
                  <div className="bg-background-tertiary rounded-lg p-3 text-center">
                    <div className="text-xl font-bold text-text-primary">
                      {totalDuration < 60000
                        ? `${(totalDuration / 1000).toFixed(1)}s`
                        : `${Math.floor(totalDuration / 60000)}m ${Math.round((totalDuration % 60000) / 1000)}s`
                      }
                    </div>
                    <div className="text-xs text-text-secondary">Total Duration</div>
                  </div>
                </div>

                {/* Per-Agent Breakdown */}
                <div className="space-y-2">
                  <h4 className="text-sm font-medium text-text-secondary mb-2">Per-Agent Breakdown</h4>
                  {(() => {
                    const agentMap: Record<string, { cost: number; tokens: number; prompt: number; completion: number; duration: number; model: string; status: string }> = {}
                    for (const log of agentLogs) {
                      if (!agentMap[log.agent_name]) {
                        agentMap[log.agent_name] = { cost: 0, tokens: 0, prompt: 0, completion: 0, duration: 0, model: log.model_used || 'unknown', status: log.status || 'completed' }
                      }
                      agentMap[log.agent_name].cost += log.cost || 0
                      agentMap[log.agent_name].tokens += log.total_tokens || 0
                      agentMap[log.agent_name].prompt += log.prompt_tokens || 0
                      agentMap[log.agent_name].completion += log.completion_tokens || 0
                      agentMap[log.agent_name].duration += log.duration_ms || 0
                      if (log.model_used) agentMap[log.agent_name].model = log.model_used
                      if (log.status) agentMap[log.agent_name].status = log.status
                    }
                    const sorted = Object.entries(agentMap).sort((a, b) => b[1].cost - a[1].cost)
                    const maxCost = sorted.length > 0 ? sorted[0][1].cost : 1

                    return sorted.map(([name, data]) => (
                      <div key={name} className="flex items-center gap-3 p-2 bg-background-tertiary rounded-lg">
                        <div className="w-24 flex-shrink-0">
                          <span className="text-sm font-medium text-text-primary truncate block">
                            {name.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())}
                          </span>
                        </div>
                        {/* Cost bar */}
                        <div className="flex-1 min-w-0">
                          <div className="h-2 rounded-full bg-background-secondary overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all duration-500 ${
                                data.status === 'failed' ? 'bg-accent-error' : 'bg-accent-primary'
                              }`}
                              style={{ width: `${maxCost > 0 ? Math.max(2, (data.cost / maxCost) * 100) : 0}%` }}
                            />
                          </div>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-text-secondary flex-shrink-0">
                          <span className="font-mono">${data.cost.toFixed(4)}</span>
                          <span>{data.tokens.toLocaleString()} tok</span>
                          <span className="text-text-tertiary hidden md:inline">{data.model.split('/').pop()}</span>
                          <span className="text-text-tertiary">
                            {data.duration < 1000 ? `${data.duration}ms` : `${(data.duration / 1000).toFixed(1)}s`}
                          </span>
                        </div>
                      </div>
                    ))
                  })()}
                </div>
              </>
            )
          })()}
        </Card>
      )}

      {/* Links */}
      {(project.github_repo || project.live_url || deploymentReport?.deployments?.some((d: any) => d.url)) && (
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
          {deploymentReport?.deployments?.map((d: any) => d.url && (
            <a
              key={d.platform}
              href={d.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 bg-green-500/20 rounded-lg text-green-400 hover:bg-green-500/30 transition-colors"
            >
              <Rocket className="w-4 h-4" />
              {d.platform} Deployment
            </a>
          ))}
        </div>
      )}

      {/* Artifact Viewer — always visible, shows live preview + code + all report tabs */}
      <ArtifactViewer
        projectId={id!}
        projectType={project.project_type}
        liveUrl={project.live_url}
        githubRepo={project.github_repo}
        outputs={outputs?.agent_outputs}
      />

      {/* Agent Output Timeline — shows each agent's output as it completes */}
      <Card>
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-medium text-text-primary flex items-center gap-2">
            <FileText className="w-5 h-5 text-accent-primary" />
            Agent Outputs
          </h3>
          {Object.keys(outputs?.agent_outputs || {}).length >= 2 && (
            <button
              onClick={() => setShowDiffModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-text-secondary hover:text-text-primary bg-background-tertiary hover:bg-white/10 rounded-md transition-colors"
            >
              <ArrowLeftRight className="w-3.5 h-3.5" />
              Compare Outputs
            </button>
          )}
        </div>
        <AgentOutputTimeline
          projectStatus={project.status}
          agentOutputs={outputs?.agent_outputs || {}}
        />
      </Card>

      {/* Brief */}
      <details className="group">
        <summary className="cursor-pointer text-sm font-medium text-text-secondary hover:text-text-primary px-1 py-2">
          Show Project Brief
        </summary>
        <Card>
          <p className="text-text-secondary text-sm whitespace-pre-wrap">
            {project.brief}
          </p>
        </Card>
      </details>

      {/* Advanced Tools — collapsed by default */}
      <details className="group">
        <summary className="cursor-pointer text-sm font-medium text-text-secondary hover:text-text-primary px-1 py-2">
          Advanced Tools (History, Memory, Testing, Sharing, Design Import)
        </summary>
        <div className="space-y-6 mt-2">
          <Card>
            <div className="flex items-center gap-2 mb-3">
              <GitBranch className="w-4 h-4" style={{ color: 'var(--accent-primary)' }} />
              <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                Pipeline History & Branching
              </h3>
            </div>
            <ProjectTimeline projectId={id!} projectStatus={project.status} />
          </Card>
          <Card><ProjectMemory projectId={id!} /></Card>
          <Card><BrowserTestPanel projectId={id!} liveUrl={project.live_url} /></Card>
          <Card><ShareLinkPanel projectId={id!} /></Card>
          <Card><DesignImportPanel projectId={id!} /></Card>
        </div>
      </details>

      {/* Monaco Diff Editor Modal — code-split, only loaded on demand */}
      {showDiffModal && (
        <Suspense fallback={null}>
          <AgentOutputDiffModal
            agentOutputs={outputs?.agent_outputs || {}}
            agents={[
              { id: 'intake', label: 'Intake' },
              { id: 'research', label: 'Research' },
              { id: 'architect', label: 'Architect' },
              { id: 'design_system', label: 'Design System' },
              { id: 'asset_generation', label: 'Assets' },
              { id: 'content_generation', label: 'Content' },
              { id: 'pm_checkpoint_1', label: 'PM Check 1' },
              { id: 'code_generation', label: 'Code Gen' },
              { id: 'pm_checkpoint_2', label: 'PM Check 2' },
              { id: 'code_review', label: 'Code Review' },
              { id: 'security', label: 'Security' },
              { id: 'seo', label: 'SEO' },
              { id: 'accessibility', label: 'Accessibility' },
              { id: 'qa', label: 'QA Testing' },
              { id: 'deployment', label: 'Deploy' },
              { id: 'post_deploy_verification', label: 'Verify' },
              { id: 'analytics_monitoring', label: 'Analytics' },
              { id: 'coding_standards', label: 'Standards' },
              { id: 'delivery', label: 'Delivery' },
            ]}
            onClose={() => setShowDiffModal(false)}
          />
        </Suspense>
      )}
    </div>
  )
}

function DeploymentStatusBadge({ status }: { status: string }) {
  const variants: Record<string, 'success' | 'warning' | 'error' | 'info' | 'default'> = {
    deployed: 'success',
    deploying: 'info',
    building: 'info',
    pending: 'default',
    failed: 'error',
  }
  return (
    <Badge variant={variants[status] || 'default'} pulse={status === 'building' || status === 'deploying'}>
      {status}
    </Badge>
  )
}

function getAgentStatus(projectStatus: string, agent: string): 'queued' | 'active' | 'completed' | 'failed' {
  // Updated order with new agents: PM checkpoints, code review, post-deploy verification
  const order = [
    'pending', 
    'intake', 
    'research', 
    'architect', 
    'design', 
    'pm_checkpoint_1',      // ★ New
    'code_generation', 
    'pm_checkpoint_2',      // ★ New
    'code_review',          // ★ New
    'security',
    'qa', 
    'deployment', 
    'post_deploy_verification',  // ★ New
    'analytics_monitoring', 
    'coding_standards', 
    'completed'
  ]
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
    pm_checkpoint_1: 'info',     // ★ New
    pm_checkpoint_2: 'info',     // ★ New
    code_generation: 'info',
    code_review: 'info',         // ★ New
    security: 'info',
    qa: 'info',
    deployment: 'info',
    post_deploy_verification: 'info',  // ★ New
    analytics_monitoring: 'info',
    coding_standards: 'info',
    failed: 'error',
    pending: 'default',
  }
  return (
    <Badge variant={variants[status] || 'default'} pulse={variants[status] === 'info'}>
      {status.replace('_', ' ')}
    </Badge>
  )
}
