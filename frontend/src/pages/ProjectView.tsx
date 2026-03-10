import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card } from '@/components/Card'
import { Badge } from '@/components/Badge'
import { PipelineVisualization } from '@/components/PipelineVisualization'
import { ScoreGauge } from '@/components/ScoreGauge'
import { ActivityFeed } from '@/components/ActivityFeed'
import { api } from '@/lib/api'
import { ExternalLink, Github, RefreshCw, CheckCircle, XCircle, AlertTriangle, Rocket, TestTube, Activity, FileText, BarChart3, Shield, Gauge, ClipboardCheck, Code2, Globe, Pause, Play, RotateCcw, Settings2 } from 'lucide-react'
import { Button } from '@/components/Button'
import { useState } from 'react'

export default function ProjectView() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const [showCheckpointModal, setShowCheckpointModal] = useState(false)

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

  // Phase 11C: Checkpoint status
  const { data: checkpointStatus } = useQuery({
    queryKey: ['checkpointStatus', id],
    queryFn: () => api.getCheckpointStatus(id!),
    enabled: !!project && project.status !== 'completed' && project.status !== 'failed',
    refetchInterval: 5000,
  })

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

  // Extract QA and deployment data from outputs
  const qaReport = outputs?.agent_outputs?.qa?.report
  const deploymentReport = outputs?.agent_outputs?.deployment?.report
  
  // Extract Phase 6 data from outputs
  const monitoringReport = outputs?.agent_outputs?.analytics_monitoring?.report
  const codingStandardsReport = outputs?.agent_outputs?.coding_standards?.report
  
  // Extract Phase 8 data - New agents
  const pmCheckpoint1 = outputs?.agent_outputs?.pm_checkpoint_1
  const pmCheckpoint2 = outputs?.agent_outputs?.pm_checkpoint_2
  const codeReviewReport = outputs?.agent_outputs?.code_review?.report
  const deployVerificationReport = outputs?.agent_outputs?.post_deploy_verification?.report

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

      {/* Real-time Activity Feed */}
      {project.status !== 'completed' && project.status !== 'failed' && (
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
      )}

      {/* Phase 11C: Checkpoint Controls */}
      {project.status !== 'completed' && project.status !== 'failed' && (
        <Card>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Settings2 className="w-5 h-5 text-accent-primary" />
              <h3 className="font-medium text-text-primary">Build Controls</h3>
            </div>
            {checkpointStatus && (
              <Badge variant={checkpointStatus.state === 'paused' ? 'warning' : 'info'}>
                {checkpointStatus.state}
              </Badge>
            )}
          </div>

          <div className="flex flex-wrap gap-3 mb-4">
            {/* Pause/Resume Button */}
            {project.status === 'paused' || checkpointStatus?.state === 'paused' ? (
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
            )}

            {/* Mode Selector */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-text-secondary">Mode:</span>
              <select
                value={checkpointStatus?.mode || 'auto'}
                onChange={(e) => setModeMutation.mutate(e.target.value)}
                className="bg-background-tertiary border border-border-subtle rounded px-2 py-1 text-sm text-text-primary"
              >
                <option value="auto">Auto (no checkpoints)</option>
                <option value="supervised">Supervised (pause at key points)</option>
                <option value="manual">Manual (custom checkpoints)</option>
              </select>
            </div>
          </div>

          {/* Current Checkpoint Info */}
          {checkpointStatus?.current_checkpoint && (
            <div className="p-3 bg-yellow-500/10 rounded-lg border border-yellow-500/20">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-4 h-4 text-yellow-400" />
                <span className="text-sm font-medium text-yellow-400">Paused at Checkpoint</span>
              </div>
              <p className="text-sm text-text-primary">
                Agent: <strong>{checkpointStatus.paused_at_agent}</strong>
              </p>
              <p className="text-xs text-text-secondary mt-1">
                Paused at: {checkpointStatus.paused_at ? new Date(checkpointStatus.paused_at).toLocaleString() : 'N/A'}
              </p>
              <p className="text-xs text-text-tertiary mt-2">
                Will auto-continue in 5 minutes if not resumed
              </p>
            </div>
          )}

          {/* Available Checkpoints Info */}
          {checkpointStatus?.mode === 'supervised' && (
            <div className="mt-3 text-xs text-text-secondary">
              <span className="font-medium">Default checkpoints:</span> {checkpointStatus.available_checkpoints?.join(', ')}
            </div>
          )}
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

      {/* PM Checkpoint 1 - Build Manifest */}
      {pmCheckpoint1 && pmCheckpoint1.build_manifest && (
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <ClipboardCheck className="w-5 h-5 text-accent-primary" />
            <h3 className="font-medium text-text-primary">PM Checkpoint 1: Coherence</h3>
            <Badge variant={pmCheckpoint1.coherent ? 'success' : 'error'}>
              {pmCheckpoint1.coherent ? 'Passed' : 'Issues Found'}
            </Badge>
          </div>
          
          {pmCheckpoint1.issues?.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-medium text-text-secondary mb-2">Validation Issues</h4>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {pmCheckpoint1.issues.slice(0, 10).map((issue: any, idx: number) => (
                  <div key={idx} className={`p-2 rounded border-l-2 ${
                    issue.severity === 'critical' ? 'border-red-400 bg-red-500/10' :
                    issue.severity === 'warning' ? 'border-yellow-400 bg-yellow-500/10' :
                    'border-blue-400 bg-blue-500/10'
                  }`}>
                    <div className="flex items-center gap-2">
                      <Badge variant={issue.severity === 'critical' ? 'error' : issue.severity === 'warning' ? 'warning' : 'info'}>
                        {issue.severity}
                      </Badge>
                      <span className="text-sm text-text-primary">{issue.category}</span>
                    </div>
                    <p className="text-xs text-text-secondary mt-1">{issue.message}</p>
                    <p className="text-xs text-text-tertiary mt-1">💡 {issue.suggestion}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          <details className="group">
            <summary className="cursor-pointer text-sm font-medium text-text-secondary hover:text-text-primary">
              View Build Manifest
            </summary>
            <div className="mt-3 p-3 bg-background-tertiary rounded-lg">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                <div>
                  <span className="text-text-tertiary">Pages:</span>
                  <span className="ml-2 text-text-primary">{pmCheckpoint1.build_manifest.pages?.length || 0}</span>
                </div>
                <div>
                  <span className="text-text-tertiary">Components:</span>
                  <span className="ml-2 text-text-primary">{pmCheckpoint1.build_manifest.components?.length || 0}</span>
                </div>
                <div>
                  <span className="text-text-tertiary">API Endpoints:</span>
                  <span className="ml-2 text-text-primary">{pmCheckpoint1.build_manifest.api_endpoints?.length || 0}</span>
                </div>
                <div>
                  <span className="text-text-tertiary">Warnings:</span>
                  <span className="ml-2 text-text-primary">{pmCheckpoint1.build_manifest.warnings?.length || 0}</span>
                </div>
              </div>
            </div>
          </details>
        </Card>
      )}

      {/* Code Review Report */}
      {codeReviewReport && (
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <Code2 className="w-5 h-5 text-accent-primary" />
            <h3 className="font-medium text-text-primary">Code Review</h3>
            <Badge variant={codeReviewReport.pass_threshold ? 'success' : 'error'}>
              {codeReviewReport.pass_threshold ? 'Passed' : 'Needs Attention'}
            </Badge>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
            <div className="bg-background-tertiary rounded-lg p-3 text-center">
              <div className="text-xl font-bold text-text-primary">{codeReviewReport.total_files_scanned || 0}</div>
              <div className="text-xs text-text-secondary">Files Scanned</div>
            </div>
            <div className="bg-background-tertiary rounded-lg p-3 text-center">
              <div className="text-xl font-bold text-text-primary">{codeReviewReport.total_issues || 0}</div>
              <div className="text-xs text-text-secondary">Total Issues</div>
            </div>
            <div className="bg-red-500/10 rounded-lg p-3 text-center">
              <div className="text-xl font-bold text-red-400">{codeReviewReport.issues_by_severity?.critical || 0}</div>
              <div className="text-xs text-text-secondary">Critical</div>
            </div>
            <div className="bg-yellow-500/10 rounded-lg p-3 text-center">
              <div className="text-xl font-bold text-yellow-400">{codeReviewReport.issues_by_severity?.high || 0}</div>
              <div className="text-xs text-text-secondary">High</div>
            </div>
            <div className="bg-green-500/10 rounded-lg p-3 text-center">
              <div className="text-xl font-bold text-green-400">{codeReviewReport.auto_fixes_applied?.length || 0}</div>
              <div className="text-xs text-text-secondary">Auto-Fixed</div>
            </div>
          </div>

          {codeReviewReport.issues?.length > 0 && (
            <details className="group">
              <summary className="cursor-pointer text-sm font-medium text-text-secondary hover:text-text-primary">
                View Issues by Category
              </summary>
              <div className="mt-3 space-y-2 max-h-64 overflow-y-auto">
                {codeReviewReport.issues.slice(0, 15).map((issue: any, idx: number) => (
                  <div key={idx} className={`p-2 rounded border-l-2 ${
                    issue.severity === 'critical' ? 'border-red-400 bg-red-500/10' :
                    issue.severity === 'high' ? 'border-orange-400 bg-orange-500/10' :
                    issue.severity === 'medium' ? 'border-yellow-400 bg-yellow-500/10' :
                    'border-blue-400 bg-blue-500/10'
                  }`}>
                    <div className="flex items-center gap-2">
                      <Badge variant={issue.severity === 'critical' || issue.severity === 'high' ? 'error' : 'warning'} className="text-xs">
                        {issue.category}
                      </Badge>
                      <span className="text-sm text-text-primary">{issue.rule}</span>
                      {issue.auto_fixable && <span className="text-xs text-green-400">🔧 Auto-fixable</span>}
                    </div>
                    <p className="text-xs text-text-secondary mt-1">{issue.message}</p>
                    <p className="text-xs text-text-tertiary">{issue.file}:{issue.line}</p>
                  </div>
                ))}
              </div>
            </details>
          )}

          <div className="mt-4 p-3 bg-background-tertiary rounded-lg">
            <p className="text-sm text-text-secondary">{codeReviewReport.summary}</p>
          </div>
        </Card>
      )}

      {/* QA Test Results */}
      {qaReport && (
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <TestTube className="w-5 h-5 text-accent-primary" />
            <h3 className="font-medium text-text-primary">QA Test Results</h3>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
            <div className="text-center">
              <ScoreGauge 
                score={qaReport.quality_score || 0} 
                label="Quality Score" 
                size="md"
              />
            </div>
            <div className="bg-background-tertiary rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-text-primary">{qaReport.total_tests || 0}</div>
              <div className="text-sm text-text-secondary">Total Tests</div>
            </div>
            <div className="bg-green-500/10 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-green-400">{qaReport.passed || 0}</div>
              <div className="text-sm text-text-secondary">Passed</div>
            </div>
            <div className="bg-red-500/10 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-red-400">{qaReport.failed || 0}</div>
              <div className="text-sm text-text-secondary">Failed</div>
            </div>
            <div className="bg-yellow-500/10 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-yellow-400">{qaReport.skipped || 0}</div>
              <div className="text-sm text-text-secondary">Skipped</div>
            </div>
          </div>

          {/* Test Results List */}
          {qaReport.test_results?.length > 0 && (
            <details className="group">
              <summary className="cursor-pointer text-sm font-medium text-text-secondary hover:text-text-primary flex items-center gap-2">
                <span>View Test Details ({qaReport.test_results.length} tests)</span>
              </summary>
              <div className="mt-3 space-y-2 max-h-64 overflow-y-auto">
                {qaReport.test_results.slice(0, 20).map((test: any, idx: number) => (
                  <div key={idx} className="flex items-center gap-3 p-2 bg-background-tertiary rounded">
                    {test.status === 'passed' ? (
                      <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
                    ) : test.status === 'failed' ? (
                      <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-yellow-400 flex-shrink-0" />
                    )}
                    <span className="text-sm text-text-primary truncate">{test.name}</span>
                    {test.duration > 0 && (
                      <span className="text-xs text-text-tertiary ml-auto">{test.duration.toFixed(2)}s</span>
                    )}
                  </div>
                ))}
                {qaReport.test_results.length > 20 && (
                  <p className="text-sm text-text-tertiary text-center py-2">
                    ...and {qaReport.test_results.length - 20} more tests
                  </p>
                )}
              </div>
            </details>
          )}

          {/* Code Quality Issues */}
          {qaReport.quality_issues?.length > 0 && (
            <details className="group mt-4">
              <summary className="cursor-pointer text-sm font-medium text-text-secondary hover:text-text-primary flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-yellow-400" />
                <span>Code Quality Issues ({qaReport.quality_issues.length})</span>
              </summary>
              <div className="mt-3 space-y-2 max-h-48 overflow-y-auto">
                {qaReport.quality_issues.slice(0, 10).map((issue: any, idx: number) => (
                  <div key={idx} className="p-2 bg-background-tertiary rounded border-l-2 border-yellow-400">
                    <div className="flex items-center gap-2">
                      <Badge variant={issue.severity === 'error' ? 'error' : 'warning'} className="text-xs">
                        {issue.tool}
                      </Badge>
                      <span className="text-sm text-text-primary">{issue.rule}</span>
                    </div>
                    <p className="text-xs text-text-secondary mt-1">{issue.message}</p>
                    <p className="text-xs text-text-tertiary">{issue.file_path}:{issue.line}</p>
                  </div>
                ))}
              </div>
            </details>
          )}

          {/* Fix Attempts */}
          {qaReport.fix_iterations > 0 && (
            <div className="mt-4 p-3 bg-background-tertiary rounded-lg">
              <p className="text-sm text-text-secondary">
                Fix Iterations: <span className="text-text-primary font-medium">{qaReport.fix_iterations} / 3</span>
                {qaReport.all_tests_passing && (
                  <span className="ml-2 text-green-400">✓ All tests passing</span>
                )}
              </p>
            </div>
          )}
        </Card>
      )}

      {/* Deployment Status */}
      {deploymentReport && (
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <Rocket className="w-5 h-5 text-accent-primary" />
            <h3 className="font-medium text-text-primary">Deployment Status</h3>
          </div>

          <div className="space-y-4">
            {deploymentReport.deployments?.map((deployment: any, idx: number) => (
              <div key={idx} className="p-4 bg-background-tertiary rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-text-primary capitalize">{deployment.platform}</span>
                    <DeploymentStatusBadge status={deployment.status} />
                  </div>
                  {deployment.url && (
                    <a
                      href={deployment.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-accent-primary hover:underline flex items-center gap-1"
                    >
                      <ExternalLink className="w-3 h-3" />
                      {deployment.url}
                    </a>
                  )}
                </div>
                {deployment.error_message && (
                  <p className="text-sm text-red-400 mt-2">{deployment.error_message}</p>
                )}
                {deployment.logs?.length > 0 && (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-xs text-text-tertiary hover:text-text-secondary">
                      View logs ({deployment.logs.length} entries)
                    </summary>
                    <pre className="mt-2 p-2 bg-background-secondary rounded text-xs text-text-tertiary overflow-x-auto max-h-32">
                      {deployment.logs.join('\n')}
                    </pre>
                  </details>
                )}
              </div>
            ))}
          </div>

          {/* GitHub Actions */}
          {deploymentReport.github_actions_generated && (
            <div className="mt-4 p-3 bg-green-500/10 rounded-lg">
              <p className="text-sm text-green-400 flex items-center gap-2">
                <CheckCircle className="w-4 h-4" />
                GitHub Actions workflows generated
              </p>
              {deploymentReport.github_actions_files?.length > 0 && (
                <ul className="mt-2 text-xs text-text-secondary">
                  {deploymentReport.github_actions_files.map((file: string, idx: number) => (
                    <li key={idx}>• {file.split('/').slice(-2).join('/')}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* Manual Instructions */}
          {deploymentReport.manual_instructions?.length > 0 && (
            <details className="mt-4">
              <summary className="cursor-pointer text-sm font-medium text-text-secondary hover:text-text-primary">
                Manual Setup Instructions
              </summary>
              <div className="mt-3 p-3 bg-background-tertiary rounded-lg prose prose-sm prose-invert max-w-none">
                <pre className="text-xs whitespace-pre-wrap text-text-secondary">
                  {deploymentReport.manual_instructions.join('\n')}
                </pre>
              </div>
            </details>
          )}
        </Card>
      )}

      {/* Post-Deploy Verification */}
      {deployVerificationReport && (
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <Globe className="w-5 h-5 text-accent-primary" />
            <h3 className="font-medium text-text-primary">Post-Deploy Verification</h3>
            <Badge variant={deployVerificationReport.overall_status === 'passed' ? 'success' : 
                           deployVerificationReport.overall_status === 'partial' ? 'warning' : 'error'}>
              {deployVerificationReport.overall_status}
            </Badge>
          </div>
          
          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="bg-green-500/10 rounded-lg p-3 text-center">
              <div className="text-xl font-bold text-green-400">{deployVerificationReport.checks_passed || 0}</div>
              <div className="text-xs text-text-secondary">Checks Passed</div>
            </div>
            <div className="bg-red-500/10 rounded-lg p-3 text-center">
              <div className="text-xl font-bold text-red-400">{deployVerificationReport.checks_failed || 0}</div>
              <div className="text-xs text-text-secondary">Checks Failed</div>
            </div>
            <div className={`rounded-lg p-3 text-center ${deployVerificationReport.ssl_valid ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
              <div className="text-xl font-bold text-text-primary">{deployVerificationReport.ssl_valid ? '🔒' : '🔓'}</div>
              <div className="text-xs text-text-secondary">SSL {deployVerificationReport.ssl_valid ? 'Valid' : 'Invalid'}</div>
            </div>
            {deployVerificationReport.visual_diff_score !== null && (
              <div className="bg-background-tertiary rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-text-primary">{Math.round((deployVerificationReport.visual_diff_score || 0) * 100)}%</div>
                <div className="text-xs text-text-secondary">Visual Match</div>
              </div>
            )}
          </div>

          {/* Endpoint Checks */}
          {deployVerificationReport.endpoint_checks?.length > 0 && (
            <details className="group mb-4">
              <summary className="cursor-pointer text-sm font-medium text-text-secondary hover:text-text-primary">
                Endpoint Health Checks ({deployVerificationReport.endpoint_checks.length})
              </summary>
              <div className="mt-3 space-y-2 max-h-48 overflow-y-auto">
                {deployVerificationReport.endpoint_checks.map((check: any, idx: number) => (
                  <div key={idx} className={`p-2 rounded flex items-center justify-between ${
                    check.passed ? 'bg-green-500/10' : 'bg-red-500/10'
                  }`}>
                    <div className="flex items-center gap-2">
                      {check.passed ? (
                        <CheckCircle className="w-4 h-4 text-green-400" />
                      ) : (
                        <XCircle className="w-4 h-4 text-red-400" />
                      )}
                      <span className="text-sm text-text-primary truncate max-w-[200px]">{check.url}</span>
                    </div>
                    <div className="flex items-center gap-3 text-xs">
                      <span className={check.passed ? 'text-green-400' : 'text-red-400'}>{check.status_code}</span>
                      <span className="text-text-tertiary">{check.response_time_ms}ms</span>
                    </div>
                  </div>
                ))}
              </div>
            </details>
          )}

          {/* Verification Results */}
          {deployVerificationReport.verification_results?.length > 0 && (
            <details className="group">
              <summary className="cursor-pointer text-sm font-medium text-text-secondary hover:text-text-primary">
                Verification Details
              </summary>
              <div className="mt-3 space-y-2">
                {deployVerificationReport.verification_results.map((result: any, idx: number) => (
                  <div key={idx} className={`p-2 rounded flex items-center gap-2 ${
                    result.passed ? 'bg-green-500/10' : result.severity === 'critical' ? 'bg-red-500/10' : 'bg-yellow-500/10'
                  }`}>
                    {result.passed ? (
                      <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
                    ) : (
                      <XCircle className={`w-4 h-4 flex-shrink-0 ${result.severity === 'critical' ? 'text-red-400' : 'text-yellow-400'}`} />
                    )}
                    <div>
                      <span className="text-sm text-text-primary">{result.check}</span>
                      <p className="text-xs text-text-secondary">{result.message}</p>
                    </div>
                  </div>
                ))}
              </div>
            </details>
          )}

          {/* Deployment URL */}
          {deployVerificationReport.deployment_url && (
            <div className="mt-4 p-3 bg-background-tertiary rounded-lg">
              <a
                href={deployVerificationReport.deployment_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-accent-primary hover:underline flex items-center gap-2"
              >
                <ExternalLink className="w-4 h-4" />
                {deployVerificationReport.deployment_url}
              </a>
            </div>
          )}
        </Card>
      )}

      {/* Monitoring Status - Phase 6 */}
      {monitoringReport && (
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-5 h-5 text-accent-primary" />
            <h3 className="font-medium text-text-primary">Monitoring & Analytics</h3>
          </div>

          {/* Services Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            {monitoringReport.services?.map((service: any, idx: number) => (
              <div 
                key={idx} 
                className={`p-3 rounded-lg ${service.configured ? 'bg-green-500/10' : 'bg-background-tertiary'}`}
              >
                <div className="flex items-center gap-2 mb-1">
                  {service.configured ? (
                    <CheckCircle className="w-4 h-4 text-green-400" />
                  ) : (
                    <XCircle className="w-4 h-4 text-text-tertiary" />
                  )}
                  <span className="text-sm font-medium text-text-primary">{service.name}</span>
                </div>
                {service.configured && service.dashboard_url && (
                  <a
                    href={service.dashboard_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-accent-primary hover:underline flex items-center gap-1"
                  >
                    <ExternalLink className="w-3 h-3" />
                    Dashboard
                  </a>
                )}
                {!service.configured && service.error_message && (
                  <p className="text-xs text-text-tertiary">{service.error_message}</p>
                )}
              </div>
            ))}
          </div>

          {/* Lighthouse CI Status */}
          {monitoringReport.lighthouse_ci_configured && (
            <div className="p-3 bg-blue-500/10 rounded-lg mb-4">
              <div className="flex items-center gap-2">
                <Gauge className="w-4 h-4 text-blue-400" />
                <span className="text-sm font-medium text-blue-400">Lighthouse CI Configured</span>
              </div>
              <p className="text-xs text-text-secondary mt-1">
                Performance monitoring runs on every push to main branch
              </p>
            </div>
          )}

          {/* Dashboard Links */}
          <div className="flex flex-wrap gap-2">
            {monitoringReport.services?.filter((s: any) => s.configured && s.dashboard_url).map((service: any, idx: number) => (
              <a
                key={idx}
                href={service.dashboard_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 px-3 py-1.5 bg-background-tertiary rounded text-xs text-text-secondary hover:text-text-primary transition-colors"
              >
                <BarChart3 className="w-3 h-3" />
                {service.name}
              </a>
            ))}
          </div>

          {/* Summary */}
          <div className="mt-4 p-3 bg-background-tertiary rounded-lg">
            <p className="text-sm text-text-secondary">
              Configured: <span className="text-text-primary font-medium">{monitoringReport.total_configured || 0}</span> / {monitoringReport.total_available || 0} services
            </p>
          </div>
        </Card>
      )}

      {/* Documentation Status - Phase 6 */}
      {codingStandardsReport && (
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <FileText className="w-5 h-5 text-accent-primary" />
            <h3 className="font-medium text-text-primary">Documentation & Standards</h3>
          </div>

          {/* Generated Documents */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            {codingStandardsReport.documents?.filter((d: any) => d.generated).map((doc: any, idx: number) => (
              <div key={idx} className="p-3 bg-green-500/10 rounded-lg">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-green-400" />
                  <span className="text-sm text-text-primary">{doc.name}</span>
                </div>
                <span className="text-xs text-text-tertiary capitalize">{doc.type.replace('_', ' ')}</span>
              </div>
            ))}
          </div>

          {/* Style Configs */}
          {codingStandardsReport.style_configs?.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-medium text-text-secondary mb-2">Code Style Configurations</h4>
              <div className="flex flex-wrap gap-2">
                {codingStandardsReport.style_configs.map((config: string, idx: number) => (
                  <span key={idx} className="px-2 py-1 bg-background-tertiary rounded text-xs text-text-secondary">
                    {config}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* ADRs */}
          {codingStandardsReport.adrs_generated > 0 && (
            <div className="p-3 bg-purple-500/10 rounded-lg mb-4">
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-purple-400" />
                <span className="text-sm text-purple-400">
                  {codingStandardsReport.adrs_generated} Architecture Decision Records Generated
                </span>
              </div>
            </div>
          )}

          {/* Summary */}
          <div className="p-3 bg-background-tertiary rounded-lg">
            <p className="text-sm text-text-secondary">
              Total Documents: <span className="text-text-primary font-medium">{codingStandardsReport.total_generated || 0}</span> files generated
            </p>
          </div>
        </Card>
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
            {Object.entries(outputs.agent_outputs)
              .filter(([agent]) => !['qa', 'deployment', 'analytics_monitoring', 'coding_standards'].includes(agent))
              .map(([agent, output]) => (
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
