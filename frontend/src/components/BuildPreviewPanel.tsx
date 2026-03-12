/**
 * BuildPreviewPanel — Right-side viewer for build output
 * Shows agent progress, generated code, and live preview
 */
import { useState, lazy, Suspense } from 'react'
import { Project } from '@/lib/api'
import {
  Code2, Eye, FileText, CheckCircle, Loader2, XCircle,
  ChevronDown, ChevronRight, ExternalLink, Github, Clock,
  Layers
} from 'lucide-react'

const LiveCodePreview = lazy(() => import('@/components/LiveCodePreview'))

interface Props {
  projectId: string | null
  project: Project | null
  outputs: Record<string, any> | null
  isBuilding: boolean
}

// Agent display names in pipeline order
const AGENT_ORDER = [
  'intake', 'research', 'architect', 'design_system', 'asset_generation',
  'content_generation', 'project_manager', 'code_generation', 'code_generation_openhands',
  'integration_wiring', 'code_review', 'security', 'seo', 'accessibility',
  'qa', 'deploy', 'analytics', 'coding_standards', 'post_deploy_verification', 'delivery'
]

function agentLabel(name: string): string {
  return name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

type Tab = 'progress' | 'code' | 'preview'

export default function BuildPreviewPanel({ projectId, project, outputs, isBuilding }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('progress')
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null)

  const completedAgents = outputs ? Object.keys(outputs).filter(k => !k.startsWith('_')) : []
  const totalAgents = 20
  const progress = Math.round((completedAgents.length / totalAgents) * 100)

  // Extract code files from code_generation output
  const codeFiles = outputs?.code_generation?.files || outputs?.code_generation_openhands?.files || null
  const hasCode = !!codeFiles

  const tabs: { id: Tab; label: string; icon: any; disabled: boolean }[] = [
    { id: 'progress', label: 'Progress', icon: Layers, disabled: false },
    { id: 'code', label: 'Code', icon: Code2, disabled: !hasCode },
    { id: 'preview', label: 'Preview', icon: Eye, disabled: !hasCode },
  ]

  return (
    <div className="build-preview">
      {/* Header */}
      <div className="build-preview-header">
        <div className="build-preview-title">
          <h3>{project?.name || 'Building...'}</h3>
          {project?.status && (
            <span className={`badge badge-${project.status === 'completed' ? 'success' : project.status === 'failed' ? 'error' : 'running'}`}>
              {project.status}
            </span>
          )}
        </div>

        {/* Progress bar */}
        {isBuilding && (
          <div className="build-progress">
            <div className="build-progress-bar">
              <div
                className="build-progress-fill"
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="build-progress-text">
              {completedAgents.length}/{totalAgents} agents
            </span>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="build-preview-tabs">
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`build-preview-tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
            disabled={tab.disabled}
          >
            <tab.icon className="w-3.5 h-3.5" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="build-preview-content">
        {activeTab === 'progress' && (
          <div className="build-agents">
            {AGENT_ORDER.map(agentName => {
              const isCompleted = completedAgents.includes(agentName)
              const output = outputs?.[agentName]
              const isExpanded = expandedAgent === agentName

              return (
                <div
                  key={agentName}
                  className={`build-agent ${isCompleted ? 'completed' : isBuilding ? 'pending' : ''}`}
                >
                  <button
                    className="build-agent-header"
                    onClick={() => isCompleted && setExpandedAgent(isExpanded ? null : agentName)}
                  >
                    <div className="build-agent-status">
                      {isCompleted ? (
                        <CheckCircle className="w-4 h-4" style={{ color: 'var(--accent-success)' }} />
                      ) : isBuilding ? (
                        <div className="build-agent-pending-dot" />
                      ) : (
                        <div className="build-agent-pending-dot dimmed" />
                      )}
                    </div>
                    <span className="build-agent-name">{agentLabel(agentName)}</span>
                    {isCompleted && (
                      isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />
                    )}
                  </button>

                  {isExpanded && output && (
                    <div className="build-agent-output">
                      <pre>{typeof output === 'string' ? output : JSON.stringify(output, null, 2).slice(0, 2000)}</pre>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}

        {activeTab === 'code' && hasCode && (
          <div className="build-code">
            {Array.isArray(codeFiles) ? codeFiles.map((file: any, i: number) => (
              <div key={i} className="build-code-file">
                <div className="build-code-file-header">
                  <FileText className="w-3.5 h-3.5" />
                  <span>{file.path || file.filename || `File ${i + 1}`}</span>
                </div>
                <pre className="build-code-content">
                  <code>{file.content || file.code || file.source || ''}</code>
                </pre>
              </div>
            )) : (
              <pre className="build-code-content">
                <code>{JSON.stringify(codeFiles, null, 2)}</code>
              </pre>
            )}
          </div>
        )}

        {activeTab === 'preview' && hasCode && (
          <div className="build-live-preview">
            <Suspense fallback={
              <div className="build-preview-loading">
                <Loader2 className="w-6 h-6 animate-spin" />
                <p>Loading preview...</p>
              </div>
            }>
              <LiveCodePreview
                files={codeFiles}
                projectType={project?.project_type}
              />
            </Suspense>
          </div>
        )}
      </div>

      {/* Footer links */}
      {project?.status === 'completed' && (
        <div className="build-preview-footer">
          {project.github_repo && (
            <a href={project.github_repo} target="_blank" rel="noopener noreferrer" className="build-footer-link">
              <Github className="w-4 h-4" />
              View on GitHub
            </a>
          )}
          {project.live_url && (
            <a href={project.live_url} target="_blank" rel="noopener noreferrer" className="build-footer-link">
              <ExternalLink className="w-4 h-4" />
              Live Site
            </a>
          )}
        </div>
      )}
    </div>
  )
}
