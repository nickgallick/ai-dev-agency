import { useState, lazy, Suspense } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, ProjectArtifacts } from '@/lib/api'
import { Card } from '@/components/Card'
import { Badge } from '@/components/Badge'
import { ScoreGauge } from '@/components/ScoreGauge'
import {
  ExternalLink,
  Github,
  Download,
  FileText,
  Folder,
  Globe,
  Smartphone,
  Terminal,
  Chrome,
  Monitor,
  Package,
  Eye,
  EyeOff,
  Code2,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Rocket,
  TestTube,
  Shield,
  Search,
  Accessibility,
  BarChart3,
  DollarSign,
  Layers,
  Palette,
  LayoutDashboard,
  Minus,
  Check,
  Play,
} from 'lucide-react'
import { Button } from '@/components/Button'

// Code-split: Sandpack only loads when user opens the Live Preview tab
const LiveCodePreview = lazy(() => import('@/components/LiveCodePreview'))

interface ArtifactViewerProps {
  projectId: string
  projectType?: string | null
  liveUrl?: string | null
  githubRepo?: string | null
  outputs?: Record<string, any>
}

const PROJECT_TYPE_CONFIG: Record<string, {
  icon: React.ReactNode
  label: string
  showPreview: boolean
  artifactLabel: string
  instructions: string
}> = {
  web_simple: {
    icon: <Globe className="w-5 h-5" />,
    label: 'Web App',
    showPreview: true,
    artifactLabel: 'Live Preview',
    instructions: 'Your web app is ready. Open it in a browser or view the live preview below.',
  },
  web_complex: {
    icon: <Globe className="w-5 h-5" />,
    label: 'Full-Stack Web App',
    showPreview: true,
    artifactLabel: 'Live Preview',
    instructions: 'Your full-stack web app is deployed. Click "View Live" to open it.',
  },
  mobile_pwa: {
    icon: <Smartphone className="w-5 h-5" />,
    label: 'Progressive Web App',
    showPreview: true,
    artifactLabel: 'PWA Preview',
    instructions: 'Your PWA is deployed. Open the live URL on mobile to install it.',
  },
  mobile_native_ios: {
    icon: <Smartphone className="w-5 h-5" />,
    label: 'iOS App',
    showPreview: false,
    artifactLabel: 'iOS Project',
    instructions: 'Download the project and open it in Xcode to build and run on a simulator or device.',
  },
  mobile_cross_platform: {
    icon: <Smartphone className="w-5 h-5" />,
    label: 'Cross-Platform Mobile App',
    showPreview: false,
    artifactLabel: 'Mobile Project',
    instructions: 'Download the project. Run `npx expo start` (Expo) or `flutter run` (Flutter) to launch.',
  },
  desktop_app: {
    icon: <Monitor className="w-5 h-5" />,
    label: 'Desktop App',
    showPreview: false,
    artifactLabel: 'Desktop App',
    instructions: 'Download the project and run `npm install && npm start` to launch the desktop app.',
  },
  chrome_extension: {
    icon: <Chrome className="w-5 h-5" />,
    label: 'Chrome Extension',
    showPreview: false,
    artifactLabel: 'Extension Package',
    instructions: 'Download the extension. In Chrome, go to chrome://extensions, enable Developer Mode, then click "Load unpacked" and select the downloaded folder.',
  },
  cli_tool: {
    icon: <Terminal className="w-5 h-5" />,
    label: 'CLI Tool',
    showPreview: false,
    artifactLabel: 'CLI Package',
    instructions: 'Download the project and run `pip install -e .` or `npm install -g .` to install the CLI tool.',
  },
  python_api: {
    icon: <Package className="w-5 h-5" />,
    label: 'Python API',
    showPreview: false,
    artifactLabel: 'API Project',
    instructions: 'Download the project. Run `pip install -r requirements.txt && uvicorn main:app` to start the API server.',
  },
  python_saas: {
    icon: <Package className="w-5 h-5" />,
    label: 'Python SaaS',
    showPreview: true,
    artifactLabel: 'SaaS App',
    instructions: 'Your SaaS app is deployed. Click "View Live" to open the application.',
  },
}

function MarkdownRenderer({ content }: { content: string }) {
  const lines = content.split('\n')
  return (
    <div className="space-y-1 text-sm text-text-secondary font-mono whitespace-pre-wrap overflow-x-auto max-h-96 overflow-y-auto">
      {lines.map((line, idx) => {
        if (line.startsWith('# ')) {
          return <p key={idx} className="text-lg font-bold text-text-primary mt-4">{line.slice(2)}</p>
        }
        if (line.startsWith('## ')) {
          return <p key={idx} className="text-base font-semibold text-text-primary mt-3">{line.slice(3)}</p>
        }
        if (line.startsWith('### ')) {
          return <p key={idx} className="text-sm font-semibold text-text-primary mt-2">{line.slice(4)}</p>
        }
        if (line.startsWith('```')) {
          return <p key={idx} className="text-accent-primary text-xs">{line}</p>
        }
        if (line.startsWith('- ') || line.startsWith('* ')) {
          return <p key={idx} className="pl-4">{'\u2022'} {line.slice(2)}</p>
        }
        return <p key={idx}>{line}</p>
      })}
    </div>
  )
}

function ScoreBadge({ score }: { score: number | null | undefined }) {
  if (score == null) return null
  const variant = score > 80 ? 'success' : score > 60 ? 'warning' : 'error'
  return <Badge variant={variant}>{score}/100</Badge>
}

function NoData({ label }: { label?: string }) {
  return (
    <div className="p-8 text-center">
      <p className="text-sm text-text-tertiary">{label || 'No data available for this section.'}</p>
    </div>
  )
}

const TAB_DEFINITIONS = [
  { key: 'overview', label: 'Overview', icon: <LayoutDashboard className="w-4 h-4" /> },
  { key: 'architecture', label: 'Architecture', icon: <Layers className="w-4 h-4" /> },
  { key: 'design', label: 'Design System', icon: <Palette className="w-4 h-4" /> },
  { key: 'code', label: 'Generated Code', icon: <Code2 className="w-4 h-4" /> },
  { key: 'preview', label: 'Live Preview', icon: <Play className="w-4 h-4" /> },
  { key: 'qa', label: 'QA Report', icon: <TestTube className="w-4 h-4" /> },
  { key: 'security', label: 'Security Report', icon: <Shield className="w-4 h-4" /> },
  { key: 'seo', label: 'SEO Report', icon: <Search className="w-4 h-4" /> },
  { key: 'accessibility', label: 'Accessibility Report', icon: <Accessibility className="w-4 h-4" /> },
  { key: 'deployment', label: 'Deployment Info', icon: <Rocket className="w-4 h-4" /> },
  { key: 'cost', label: 'Cost Breakdown', icon: <DollarSign className="w-4 h-4" /> },
] as const

type TabKey = typeof TAB_DEFINITIONS[number]['key']

export function ArtifactViewer({ projectId, projectType, liveUrl, githubRepo, outputs }: ArtifactViewerProps) {
  const [activeTab, setActiveTab] = useState<TabKey>('overview')
  const [showPreview, setShowPreview] = useState(false)
  const [previewError, setPreviewError] = useState(false)

  const { data: artifacts, isLoading } = useQuery({
    queryKey: ['artifacts', projectId],
    queryFn: () => api.getProjectArtifacts(projectId),
    enabled: !!projectId,
  })

  const { data: agentLogs } = useQuery({
    queryKey: ['agentLogs', projectId],
    queryFn: () => api.getAgentLogs({ project_id: projectId }),
    enabled: !!projectId,
  })

  const typeConfig = PROJECT_TYPE_CONFIG[projectType || ''] || {
    icon: <Globe className="w-5 h-5" />,
    label: 'Project',
    showPreview: true,
    artifactLabel: 'Preview',
    instructions: 'Your project is ready.',
  }

  const effectiveLiveUrl = artifacts?.live_url || liveUrl
  const effectiveGithubRepo = artifacts?.github_repo || githubRepo
  const canPreview = typeConfig.showPreview && !!effectiveLiveUrl

  const handleDownload = async () => {
    try {
      const blob = await api.exportProject(projectId)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${artifacts?.project_name || 'project'}-${projectId.slice(0, 8)}.zip`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error('Download failed:', e)
    }
  }

  // Determine which tabs have data
  function hasTabData(tab: TabKey): boolean | null {
    switch (tab) {
      case 'overview': return true
      case 'architecture': return !!outputs?.architect
      case 'design': return !!outputs?.design_system
      case 'code': return !!(artifacts?.file_structure && artifacts.file_structure.length > 0) || !!outputs?.code_generation
      case 'preview': {
        const cg = outputs?.code_generation
        const codeFiles = cg?.files || cg?.generated_files || []
        return codeFiles.length > 0
      }
      case 'qa': return !!outputs?.qa?.report
      case 'security': return !!outputs?.security
      case 'seo': return !!outputs?.seo
      case 'accessibility': return !!outputs?.accessibility
      case 'deployment': return !!outputs?.deployment?.report
      case 'cost': return !!(agentLogs && agentLogs.length > 0)
      default: return false
    }
  }

  if (isLoading) {
    return (
      <Card>
        <div className="h-32 bg-background-tertiary rounded animate-pulse" />
      </Card>
    )
  }

  return (
    <Card>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-accent-primary">{typeConfig.icon}</span>
          <h3 className="font-medium text-text-primary">Project Artifacts</h3>
          <span className="text-xs text-text-tertiary px-2 py-0.5 bg-background-tertiary rounded-full">
            {typeConfig.label}
          </span>
        </div>
        <Button variant="ghost" size="sm" onClick={handleDownload}>
          <Download className="w-4 h-4 mr-2" />
          Download ZIP
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-1 mb-6 border-b border-border-subtle pb-0">
        {TAB_DEFINITIONS.map((tab) => {
          const has = hasTabData(tab.key)
          const isActive = activeTab === tab.key
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
                isActive
                  ? 'border-accent-primary text-accent-primary'
                  : 'border-transparent text-text-tertiary hover:text-text-secondary hover:border-border-subtle'
              }`}
            >
              {tab.icon}
              <span className="hidden md:inline">{tab.label}</span>
              {has === true && (
                <Check className="w-3 h-3 text-green-400" />
              )}
              {has === false && (
                <Minus className="w-3 h-3 text-text-tertiary" />
              )}
            </button>
          )
        })}
      </div>

      {/* Tab Content */}
      <div className="min-h-[200px]">
        {activeTab === 'overview' && (
          <OverviewTab
            typeConfig={typeConfig}
            effectiveLiveUrl={effectiveLiveUrl}
            effectiveGithubRepo={effectiveGithubRepo}
            canPreview={canPreview}
            showPreview={showPreview}
            setShowPreview={setShowPreview}
            previewError={previewError}
            setPreviewError={setPreviewError}
            artifacts={artifacts}
            outputs={outputs}
          />
        )}
        {activeTab === 'architecture' && <ArchitectureTab outputs={outputs} />}
        {activeTab === 'design' && <DesignSystemTab outputs={outputs} />}
        {activeTab === 'code' && <GeneratedCodeTab artifacts={artifacts} outputs={outputs} />}
        {activeTab === 'preview' && (
          <LivePreviewTab outputs={outputs} projectType={projectType} />
        )}
        {activeTab === 'qa' && <QAReportTab outputs={outputs} />}
        {activeTab === 'security' && <SecurityReportTab outputs={outputs} />}
        {activeTab === 'seo' && <SEOReportTab outputs={outputs} />}
        {activeTab === 'accessibility' && <AccessibilityReportTab outputs={outputs} />}
        {activeTab === 'deployment' && <DeploymentInfoTab outputs={outputs} />}
        {activeTab === 'cost' && <CostBreakdownTab agentLogs={agentLogs} />}
      </div>
    </Card>
  )
}

// ─── Overview Tab ──────────────────────────────────────────────────────────────

function OverviewTab({
  typeConfig,
  effectiveLiveUrl,
  effectiveGithubRepo,
  canPreview,
  showPreview,
  setShowPreview,
  previewError,
  setPreviewError,
  artifacts,
  outputs,
}: {
  typeConfig: { instructions: string; showPreview: boolean }
  effectiveLiveUrl?: string | null
  effectiveGithubRepo?: string | null
  canPreview: boolean
  showPreview: boolean
  setShowPreview: (v: boolean) => void
  previewError: boolean
  setPreviewError: (v: boolean) => void
  artifacts?: ProjectArtifacts
  outputs?: Record<string, any>
}) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-text-secondary">{typeConfig.instructions}</p>

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-3">
        {effectiveLiveUrl && (
          <a
            href={effectiveLiveUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 bg-accent-primary/20 rounded-lg text-accent-primary hover:bg-accent-primary/30 transition-colors text-sm font-medium"
          >
            <ExternalLink className="w-4 h-4" />
            View Live
          </a>
        )}

        {canPreview && (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setShowPreview(!showPreview)}
          >
            {showPreview ? <EyeOff className="w-4 h-4 mr-2" /> : <Eye className="w-4 h-4 mr-2" />}
            {showPreview ? 'Hide Preview' : 'Preview in App'}
          </Button>
        )}

        {effectiveGithubRepo && (
          <a
            href={effectiveGithubRepo}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 bg-background-tertiary rounded-lg text-text-primary hover:bg-border-subtle transition-colors text-sm"
          >
            <Github className="w-4 h-4" />
            View Source
          </a>
        )}
      </div>

      {/* Deployment URLs */}
      {artifacts?.deployment_urls && artifacts.deployment_urls.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {artifacts.deployment_urls.map((dep, idx) => (
            <a
              key={idx}
              href={dep.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-3 py-1.5 bg-green-500/10 rounded-lg text-green-400 hover:bg-green-500/20 transition-colors text-xs"
            >
              <ExternalLink className="w-3 h-3" />
              {dep.platform}
            </a>
          ))}
        </div>
      )}

      {/* Live Preview iframe */}
      {showPreview && effectiveLiveUrl && !previewError && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-text-tertiary">Live Preview - {effectiveLiveUrl}</span>
            <a
              href={effectiveLiveUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-accent-primary hover:underline flex items-center gap-1"
            >
              <ExternalLink className="w-3 h-3" />
              Open Full Screen
            </a>
          </div>
          <div className="relative w-full rounded-lg overflow-hidden border border-border-subtle bg-white"
            style={{ height: '500px' }}>
            <iframe
              src={effectiveLiveUrl}
              className="w-full h-full"
              title="Project Preview"
              sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
              onError={() => setPreviewError(true)}
            />
          </div>
        </div>
      )}

      {showPreview && previewError && (
        <div className="p-4 bg-yellow-500/10 rounded-lg border border-yellow-500/20">
          <p className="text-sm text-yellow-400">
            Preview blocked by the site's security policy.{' '}
            <a href={effectiveLiveUrl!} target="_blank" rel="noopener noreferrer"
              className="underline hover:no-underline">
              Open in a new tab instead
            </a>
          </p>
        </div>
      )}

      {/* File Structure */}
      {artifacts?.file_structure && artifacts.file_structure.length > 0 && (
        <details className="group">
          <summary className="cursor-pointer text-sm font-medium text-text-secondary hover:text-text-primary flex items-center gap-2">
            <Folder className="w-4 h-4" />
            File Structure ({artifacts.file_structure.length} files shown)
          </summary>
          <div className="mt-3 p-3 bg-background-tertiary rounded-lg">
            <div className="space-y-1 max-h-48 overflow-y-auto">
              {artifacts.file_structure.map((file, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <Code2 className="w-3 h-3 text-text-tertiary flex-shrink-0" />
                  <span className="text-xs text-text-secondary font-mono">{file}</span>
                </div>
              ))}
            </div>
          </div>
        </details>
      )}

      {/* README */}
      {artifacts?.readme_content && (
        <details className="group">
          <summary className="cursor-pointer text-sm font-medium text-text-secondary hover:text-text-primary flex items-center gap-2">
            <FileText className="w-4 h-4" />
            README
          </summary>
          <div className="mt-3 p-3 bg-background-tertiary rounded-lg">
            <MarkdownRenderer content={artifacts.readme_content} />
          </div>
        </details>
      )}

      {/* No artifacts available */}
      {!effectiveLiveUrl && !effectiveGithubRepo && !artifacts?.has_local_files && (
        <NoData label="No artifacts available yet. The project may still be building or deployment may have failed." />
      )}
    </div>
  )
}

// ─── Architecture Tab ──────────────────────────────────────────────────────────

function ArchitectureTab({ outputs }: { outputs?: Record<string, any> }) {
  const arch = outputs?.architect
  if (!arch) return <NoData />

  const techStack = arch.tech_stack || arch.technology_stack
  const components = arch.components || arch.component_structure
  const endpoints = arch.api_endpoints || arch.endpoints
  const dbSchema = arch.database_schema || arch.db_schema

  return (
    <div className="space-y-6">
      {/* Tech Stack */}
      {techStack && (
        <div>
          <h4 className="text-sm font-medium text-text-primary mb-3">Tech Stack</h4>
          {typeof techStack === 'object' && !Array.isArray(techStack) ? (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {Object.entries(techStack).map(([category, value]) => (
                <div key={category} className="p-3 bg-background-tertiary rounded-lg">
                  <span className="text-xs text-text-tertiary capitalize">{category.replace(/_/g, ' ')}</span>
                  <p className="text-sm text-text-primary font-medium mt-1">
                    {Array.isArray(value) ? (value as string[]).join(', ') : String(value)}
                  </p>
                </div>
              ))}
            </div>
          ) : Array.isArray(techStack) ? (
            <div className="flex flex-wrap gap-2">
              {techStack.map((tech: string, idx: number) => (
                <span key={idx} className="px-3 py-1 bg-accent-primary/10 text-accent-primary rounded-full text-sm">
                  {tech}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-sm text-text-secondary">{String(techStack)}</p>
          )}
        </div>
      )}

      {/* Component Structure */}
      {components && (
        <div>
          <h4 className="text-sm font-medium text-text-primary mb-3">Component Structure</h4>
          {Array.isArray(components) ? (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {components.map((comp: any, idx: number) => (
                <div key={idx} className="p-3 bg-background-tertiary rounded-lg">
                  <span className="text-sm font-medium text-text-primary">
                    {typeof comp === 'string' ? comp : comp.name || comp.component || JSON.stringify(comp)}
                  </span>
                  {comp.description && (
                    <p className="text-xs text-text-secondary mt-1">{comp.description}</p>
                  )}
                  {comp.type && (
                    <Badge variant="info" className="mt-1">{comp.type}</Badge>
                  )}
                </div>
              ))}
            </div>
          ) : typeof components === 'object' ? (
            <pre className="p-3 bg-background-tertiary rounded-lg text-xs text-text-secondary font-mono overflow-x-auto max-h-64 overflow-y-auto">
              {JSON.stringify(components, null, 2)}
            </pre>
          ) : (
            <p className="text-sm text-text-secondary">{String(components)}</p>
          )}
        </div>
      )}

      {/* API Endpoints */}
      {endpoints && (
        <div>
          <h4 className="text-sm font-medium text-text-primary mb-3">API Endpoints</h4>
          {Array.isArray(endpoints) ? (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {endpoints.map((ep: any, idx: number) => (
                <div key={idx} className="flex items-center gap-3 p-2 bg-background-tertiary rounded">
                  {ep.method && (
                    <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                      ep.method === 'GET' ? 'bg-green-500/20 text-green-400' :
                      ep.method === 'POST' ? 'bg-blue-500/20 text-blue-400' :
                      ep.method === 'PUT' ? 'bg-yellow-500/20 text-yellow-400' :
                      ep.method === 'DELETE' ? 'bg-red-500/20 text-red-400' :
                      'bg-background-tertiary text-text-secondary'
                    }`}>
                      {ep.method}
                    </span>
                  )}
                  <span className="text-sm text-text-primary font-mono">
                    {typeof ep === 'string' ? ep : ep.path || ep.endpoint || ep.url || JSON.stringify(ep)}
                  </span>
                  {ep.description && (
                    <span className="text-xs text-text-tertiary ml-auto hidden md:inline">{ep.description}</span>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <pre className="p-3 bg-background-tertiary rounded-lg text-xs text-text-secondary font-mono overflow-x-auto max-h-64 overflow-y-auto">
              {typeof endpoints === 'object' ? JSON.stringify(endpoints, null, 2) : String(endpoints)}
            </pre>
          )}
        </div>
      )}

      {/* Database Schema */}
      {dbSchema && (
        <div>
          <h4 className="text-sm font-medium text-text-primary mb-3">Database Schema</h4>
          {Array.isArray(dbSchema) ? (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {dbSchema.map((table: any, idx: number) => (
                <div key={idx} className="p-3 bg-background-tertiary rounded-lg">
                  <span className="text-sm font-medium text-text-primary font-mono">
                    {typeof table === 'string' ? table : table.name || table.table || JSON.stringify(table)}
                  </span>
                  {table.columns && Array.isArray(table.columns) && (
                    <div className="mt-2 space-y-1">
                      {table.columns.map((col: any, cidx: number) => (
                        <div key={cidx} className="flex items-center gap-2 text-xs text-text-secondary pl-3">
                          <span className="font-mono">{typeof col === 'string' ? col : col.name}</span>
                          {col.type && <span className="text-text-tertiary">{col.type}</span>}
                          {col.primary_key && <Badge variant="info">PK</Badge>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <pre className="p-3 bg-background-tertiary rounded-lg text-xs text-text-secondary font-mono overflow-x-auto max-h-64 overflow-y-auto">
              {typeof dbSchema === 'object' ? JSON.stringify(dbSchema, null, 2) : String(dbSchema)}
            </pre>
          )}
        </div>
      )}

      {/* Fallback: show raw data if none of the known keys matched */}
      {!techStack && !components && !endpoints && !dbSchema && (
        <pre className="p-3 bg-background-tertiary rounded-lg text-xs text-text-secondary font-mono overflow-x-auto max-h-96 overflow-y-auto">
          {JSON.stringify(arch, null, 2)}
        </pre>
      )}
    </div>
  )
}

// ─── Design System Tab ─────────────────────────────────────────────────────────

function DesignSystemTab({ outputs }: { outputs?: Record<string, any> }) {
  const ds = outputs?.design_system
  if (!ds) return <NoData />

  const colorPalette = ds.color_palette || ds.colors
  const typography = ds.typography || ds.fonts
  const componentLibrary = ds.component_library || ds.components || ds.ui_library

  return (
    <div className="space-y-6">
      {/* Color Palette */}
      {colorPalette && (
        <div>
          <h4 className="text-sm font-medium text-text-primary mb-3">Color Palette</h4>
          {typeof colorPalette === 'object' && !Array.isArray(colorPalette) ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {Object.entries(colorPalette).map(([name, value]) => (
                <div key={name} className="flex items-center gap-3 p-3 bg-background-tertiary rounded-lg">
                  <div
                    className="w-8 h-8 rounded-md border border-border-subtle flex-shrink-0"
                    style={{ backgroundColor: String(value) }}
                  />
                  <div>
                    <span className="text-xs text-text-tertiary capitalize">{name.replace(/_/g, ' ')}</span>
                    <p className="text-sm text-text-primary font-mono">{String(value)}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : Array.isArray(colorPalette) ? (
            <div className="flex flex-wrap gap-3">
              {colorPalette.map((color: any, idx: number) => {
                const colorValue = typeof color === 'string' ? color : color.value || color.hex || color.color
                const colorName = typeof color === 'string' ? color : color.name || color.label || `Color ${idx + 1}`
                return (
                  <div key={idx} className="flex items-center gap-2 p-2 bg-background-tertiary rounded-lg">
                    <div
                      className="w-6 h-6 rounded border border-border-subtle"
                      style={{ backgroundColor: colorValue }}
                    />
                    <span className="text-sm text-text-secondary">{colorName}</span>
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="text-sm text-text-secondary">{String(colorPalette)}</p>
          )}
        </div>
      )}

      {/* Typography */}
      {typography && (
        <div>
          <h4 className="text-sm font-medium text-text-primary mb-3">Typography</h4>
          {typeof typography === 'object' && !Array.isArray(typography) ? (
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(typography).map(([key, value]) => (
                <div key={key} className="p-3 bg-background-tertiary rounded-lg">
                  <span className="text-xs text-text-tertiary capitalize">{key.replace(/_/g, ' ')}</span>
                  <p className="text-sm text-text-primary mt-1">
                    {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-text-secondary">{String(typography)}</p>
          )}
        </div>
      )}

      {/* Component Library */}
      {componentLibrary && (
        <div>
          <h4 className="text-sm font-medium text-text-primary mb-3">Component Library</h4>
          {typeof componentLibrary === 'string' ? (
            <p className="text-sm text-text-secondary">{componentLibrary}</p>
          ) : Array.isArray(componentLibrary) ? (
            <div className="flex flex-wrap gap-2">
              {componentLibrary.map((lib: any, idx: number) => (
                <span key={idx} className="px-3 py-1 bg-accent-primary/10 text-accent-primary rounded-full text-sm">
                  {typeof lib === 'string' ? lib : lib.name || JSON.stringify(lib)}
                </span>
              ))}
            </div>
          ) : (
            <pre className="p-3 bg-background-tertiary rounded-lg text-xs text-text-secondary font-mono overflow-x-auto max-h-64 overflow-y-auto">
              {JSON.stringify(componentLibrary, null, 2)}
            </pre>
          )}
        </div>
      )}

      {/* Fallback raw data */}
      {!colorPalette && !typography && !componentLibrary && (
        <pre className="p-3 bg-background-tertiary rounded-lg text-xs text-text-secondary font-mono overflow-x-auto max-h-96 overflow-y-auto">
          {JSON.stringify(ds, null, 2)}
        </pre>
      )}
    </div>
  )
}

// ─── Generated Code Tab ────────────────────────────────────────────────────────

// ─── Live Preview Tab (#3) ──────────────────────────────────────────────────

function LivePreviewTab({ outputs, projectType }: { outputs?: Record<string, any>; projectType?: string | null }) {
  const codeGen = outputs?.code_generation
  const codeFiles = codeGen?.files || codeGen?.generated_files || []
  const fileContents = codeGen?.file_contents || codeGen?.code || codeGen?.source_files

  if (!codeFiles.length) {
    return (
      <div className="p-8 text-center">
        <p className="text-sm text-text-tertiary">No code files available for live preview.</p>
      </div>
    )
  }

  return (
    <Suspense fallback={
      <div className="flex items-center justify-center py-16">
        <div className="text-center">
          <div className="animate-spin h-8 w-8 border-2 border-accent-primary border-t-transparent rounded-full mx-auto mb-3" />
          <p className="text-sm text-text-tertiary">Loading live preview...</p>
        </div>
      </div>
    }>
      <LiveCodePreview
        files={codeFiles}
        projectType={projectType || undefined}
        fileContents={typeof fileContents === 'object' ? fileContents : undefined}
      />
    </Suspense>
  )
}

// ─── Generated Code Tab ─────────────────────────────────────────────────────

function GeneratedCodeTab({ artifacts, outputs }: { artifacts?: ProjectArtifacts; outputs?: Record<string, any> }) {
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const codeGen = outputs?.code_generation
  const files = artifacts?.file_structure || []
  const codeFiles = codeGen?.generated_files || codeGen?.files || []

  if (files.length === 0 && codeFiles.length === 0 && !codeGen) {
    return <NoData />
  }

  // Attempt to find file content from code generation output
  const getFileContent = (path: string): string | null => {
    if (!codeGen) return null
    // Check different structures for file content
    const fileMap = codeGen.file_contents || codeGen.code || codeGen.source_files
    if (fileMap && typeof fileMap === 'object') {
      return fileMap[path] || null
    }
    // Check generated_files array
    if (Array.isArray(codeFiles)) {
      const found = codeFiles.find((f: any) => f.path === path || f.name === path || f.file === path)
      if (found) return found.content || found.code || found.source || null
    }
    return null
  }

  const displayFiles = files.length > 0 ? files : codeFiles.map((f: any) => typeof f === 'string' ? f : f.path || f.name || f.file || '')

  return (
    <div className="space-y-4">
      {/* File Tree */}
      <div>
        <h4 className="text-sm font-medium text-text-primary mb-3 flex items-center gap-2">
          <Folder className="w-4 h-4" />
          File Tree ({displayFiles.length} files)
        </h4>
        <div className="p-3 bg-background-tertiary rounded-lg max-h-64 overflow-y-auto">
          <div className="space-y-1">
            {displayFiles.map((file: string, idx: number) => (
              <button
                key={idx}
                onClick={() => setSelectedFile(file === selectedFile ? null : file)}
                className={`flex items-center gap-2 w-full text-left px-2 py-1 rounded text-xs font-mono transition-colors ${
                  selectedFile === file
                    ? 'bg-accent-primary/20 text-accent-primary'
                    : 'text-text-secondary hover:bg-background-tertiary hover:text-text-primary'
                }`}
              >
                <Code2 className="w-3 h-3 flex-shrink-0" />
                {file}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Code Preview */}
      {selectedFile && (
        <div>
          <h4 className="text-sm font-medium text-text-primary mb-2 flex items-center gap-2">
            <FileText className="w-4 h-4" />
            {selectedFile}
          </h4>
          <div className="bg-background-tertiary rounded-lg overflow-hidden">
            {getFileContent(selectedFile) ? (
              <pre className="p-4 text-xs font-mono text-text-secondary overflow-x-auto max-h-96 overflow-y-auto">
                <code>{getFileContent(selectedFile)}</code>
              </pre>
            ) : (
              <div className="p-4 text-sm text-text-tertiary text-center">
                Source code not available for preview. Download the ZIP to view all files.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Code Gen Summary */}
      {codeGen && (codeGen.summary || codeGen.platform || codeGen.framework) && (
        <div className="p-3 bg-background-tertiary rounded-lg">
          {codeGen.platform && (
            <p className="text-sm text-text-secondary">
              Platform: <span className="text-text-primary font-medium">{codeGen.platform}</span>
            </p>
          )}
          {codeGen.framework && (
            <p className="text-sm text-text-secondary">
              Framework: <span className="text-text-primary font-medium">{codeGen.framework}</span>
            </p>
          )}
          {codeGen.summary && (
            <p className="text-sm text-text-secondary mt-2">{codeGen.summary}</p>
          )}
        </div>
      )}
    </div>
  )
}

// ─── QA Report Tab ─────────────────────────────────────────────────────────────

function QAReportTab({ outputs }: { outputs?: Record<string, any> }) {
  const qaReport = outputs?.qa?.report
  if (!qaReport) return <NoData />

  return (
    <div className="space-y-6">
      {/* Score and Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
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

      {/* Test Results */}
      {qaReport.test_results?.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-text-secondary mb-3">Test Details ({qaReport.test_results.length} tests)</h4>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {qaReport.test_results.slice(0, 30).map((test: any, idx: number) => (
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
            {qaReport.test_results.length > 30 && (
              <p className="text-sm text-text-tertiary text-center py-2">
                ...and {qaReport.test_results.length - 30} more tests
              </p>
            )}
          </div>
        </div>
      )}

      {/* Code Quality Issues */}
      {qaReport.quality_issues?.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-text-secondary mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-yellow-400" />
            Code Quality Issues ({qaReport.quality_issues.length})
          </h4>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {qaReport.quality_issues.slice(0, 15).map((issue: any, idx: number) => (
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
        </div>
      )}

      {/* Fix Iterations */}
      {qaReport.fix_iterations > 0 && (
        <div className="p-3 bg-background-tertiary rounded-lg">
          <p className="text-sm text-text-secondary">
            Fix Iterations: <span className="text-text-primary font-medium">{qaReport.fix_iterations} / 3</span>
            {qaReport.all_tests_passing && (
              <span className="ml-2 text-green-400">All tests passing</span>
            )}
          </p>
        </div>
      )}
    </div>
  )
}

// ─── Security Report Tab ───────────────────────────────────────────────────────

function SecurityReportTab({ outputs }: { outputs?: Record<string, any> }) {
  const security = outputs?.security
  if (!security) return <NoData />

  const report = security.report || security
  const score = report.security_score ?? report.score ?? security.security_score
  const vulnerabilities = report.vulnerabilities || report.findings || report.issues || []

  return (
    <div className="space-y-6">
      {/* Score */}
      {score != null && (
        <div className="flex items-center gap-6">
          <ScoreGauge score={score} label="Security Score" size="md" />
          <div>
            <ScoreBadge score={score} />
            {report.summary && (
              <p className="text-sm text-text-secondary mt-2">{report.summary}</p>
            )}
          </div>
        </div>
      )}

      {/* Vulnerability Scan Results */}
      {Array.isArray(vulnerabilities) && vulnerabilities.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-text-primary mb-3">Vulnerabilities Found ({vulnerabilities.length})</h4>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {vulnerabilities.map((vuln: any, idx: number) => {
              const severity = vuln.severity || vuln.level || 'info'
              return (
                <div key={idx} className={`p-3 rounded border-l-2 ${
                  severity === 'critical' || severity === 'high' ? 'border-red-400 bg-red-500/10' :
                  severity === 'medium' || severity === 'warning' ? 'border-yellow-400 bg-yellow-500/10' :
                  'border-blue-400 bg-blue-500/10'
                }`}>
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant={severity === 'critical' || severity === 'high' ? 'error' : severity === 'medium' ? 'warning' : 'info'}>
                      {severity}
                    </Badge>
                    <span className="text-sm font-medium text-text-primary">
                      {vuln.title || vuln.name || vuln.rule || vuln.type || 'Issue'}
                    </span>
                  </div>
                  {(vuln.description || vuln.message) && (
                    <p className="text-xs text-text-secondary">{vuln.description || vuln.message}</p>
                  )}
                  {vuln.file && (
                    <p className="text-xs text-text-tertiary mt-1 font-mono">{vuln.file}{vuln.line ? `:${vuln.line}` : ''}</p>
                  )}
                  {vuln.recommendation && (
                    <p className="text-xs text-accent-primary mt-1">Fix: {vuln.recommendation}</p>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {Array.isArray(vulnerabilities) && vulnerabilities.length === 0 && score != null && (
        <div className="p-4 bg-green-500/10 rounded-lg flex items-center gap-2">
          <CheckCircle className="w-5 h-5 text-green-400" />
          <p className="text-sm text-green-400">No vulnerabilities detected.</p>
        </div>
      )}

      {/* Fallback raw data */}
      {score == null && vulnerabilities.length === 0 && (
        <pre className="p-3 bg-background-tertiary rounded-lg text-xs text-text-secondary font-mono overflow-x-auto max-h-96 overflow-y-auto">
          {JSON.stringify(security, null, 2)}
        </pre>
      )}
    </div>
  )
}

// ─── SEO Report Tab ────────────────────────────────────────────────────────────

function SEOReportTab({ outputs }: { outputs?: Record<string, any> }) {
  const seo = outputs?.seo
  if (!seo) return <NoData />

  const report = seo.report || seo
  const score = report.seo_score ?? report.score ?? seo.seo_score
  const recommendations = report.recommendations || report.suggestions || report.issues || []

  return (
    <div className="space-y-6">
      {/* Score */}
      {score != null && (
        <div className="flex items-center gap-6">
          <ScoreGauge score={score} label="SEO Score" size="md" />
          <div>
            <ScoreBadge score={score} />
            {report.summary && (
              <p className="text-sm text-text-secondary mt-2">{report.summary}</p>
            )}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {Array.isArray(recommendations) && recommendations.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-text-primary mb-3">Recommendations ({recommendations.length})</h4>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {recommendations.map((rec: any, idx: number) => {
              const priority = rec.priority || rec.severity || rec.level || 'info'
              return (
                <div key={idx} className={`p-3 rounded border-l-2 ${
                  priority === 'critical' || priority === 'high' ? 'border-red-400 bg-red-500/10' :
                  priority === 'medium' || priority === 'warning' ? 'border-yellow-400 bg-yellow-500/10' :
                  'border-blue-400 bg-blue-500/10'
                }`}>
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant={priority === 'critical' || priority === 'high' ? 'error' : priority === 'medium' ? 'warning' : 'info'}>
                      {priority}
                    </Badge>
                    <span className="text-sm font-medium text-text-primary">
                      {typeof rec === 'string' ? rec : rec.title || rec.name || rec.category || 'Recommendation'}
                    </span>
                  </div>
                  {typeof rec === 'object' && (rec.description || rec.message || rec.detail) && (
                    <p className="text-xs text-text-secondary">{rec.description || rec.message || rec.detail}</p>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Metrics */}
      {report.metrics && typeof report.metrics === 'object' && (
        <div>
          <h4 className="text-sm font-medium text-text-primary mb-3">SEO Metrics</h4>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {Object.entries(report.metrics).map(([key, value]) => (
              <div key={key} className="p-3 bg-background-tertiary rounded-lg">
                <span className="text-xs text-text-tertiary capitalize">{key.replace(/_/g, ' ')}</span>
                <p className="text-sm text-text-primary font-medium mt-1">{String(value)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Fallback */}
      {score == null && recommendations.length === 0 && !report.metrics && (
        <pre className="p-3 bg-background-tertiary rounded-lg text-xs text-text-secondary font-mono overflow-x-auto max-h-96 overflow-y-auto">
          {JSON.stringify(seo, null, 2)}
        </pre>
      )}
    </div>
  )
}

// ─── Accessibility Report Tab ──────────────────────────────────────────────────

function AccessibilityReportTab({ outputs }: { outputs?: Record<string, any> }) {
  const a11y = outputs?.accessibility
  if (!a11y) return <NoData />

  const report = a11y.report || a11y
  const score = report.accessibility_score ?? report.a11y_score ?? report.score ?? a11y.accessibility_score
  const issues = report.issues || report.violations || report.findings || []
  const wcag = report.wcag_compliance || report.wcag || report.compliance

  return (
    <div className="space-y-6">
      {/* Score */}
      {score != null && (
        <div className="flex items-center gap-6">
          <ScoreGauge score={score} label="A11y Score" size="md" />
          <div>
            <ScoreBadge score={score} />
            {report.summary && (
              <p className="text-sm text-text-secondary mt-2">{report.summary}</p>
            )}
          </div>
        </div>
      )}

      {/* WCAG Compliance */}
      {wcag && (
        <div>
          <h4 className="text-sm font-medium text-text-primary mb-3">WCAG Compliance</h4>
          {typeof wcag === 'object' && !Array.isArray(wcag) ? (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {Object.entries(wcag).map(([level, status]) => (
                <div key={level} className={`p-3 rounded-lg flex items-center gap-2 ${
                  status === true || status === 'pass' || status === 'passed' ? 'bg-green-500/10' : 'bg-red-500/10'
                }`}>
                  {status === true || status === 'pass' || status === 'passed' ? (
                    <CheckCircle className="w-4 h-4 text-green-400" />
                  ) : (
                    <XCircle className="w-4 h-4 text-red-400" />
                  )}
                  <span className="text-sm text-text-primary font-medium">{level}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-text-secondary">{String(wcag)}</p>
          )}
        </div>
      )}

      {/* Issues */}
      {Array.isArray(issues) && issues.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-text-primary mb-3">Accessibility Issues ({issues.length})</h4>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {issues.map((issue: any, idx: number) => {
              const impact = issue.impact || issue.severity || issue.level || 'info'
              return (
                <div key={idx} className={`p-3 rounded border-l-2 ${
                  impact === 'critical' || impact === 'serious' ? 'border-red-400 bg-red-500/10' :
                  impact === 'moderate' || impact === 'warning' ? 'border-yellow-400 bg-yellow-500/10' :
                  'border-blue-400 bg-blue-500/10'
                }`}>
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant={impact === 'critical' || impact === 'serious' ? 'error' : impact === 'moderate' ? 'warning' : 'info'}>
                      {impact}
                    </Badge>
                    <span className="text-sm font-medium text-text-primary">
                      {typeof issue === 'string' ? issue : issue.title || issue.description || issue.id || 'Issue'}
                    </span>
                  </div>
                  {typeof issue === 'object' && issue.help && (
                    <p className="text-xs text-text-secondary">{issue.help}</p>
                  )}
                  {typeof issue === 'object' && issue.wcag_criteria && (
                    <span className="text-xs text-accent-primary">{issue.wcag_criteria}</span>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {Array.isArray(issues) && issues.length === 0 && score != null && (
        <div className="p-4 bg-green-500/10 rounded-lg flex items-center gap-2">
          <CheckCircle className="w-5 h-5 text-green-400" />
          <p className="text-sm text-green-400">No accessibility issues detected.</p>
        </div>
      )}

      {/* Fallback */}
      {score == null && issues.length === 0 && !wcag && (
        <pre className="p-3 bg-background-tertiary rounded-lg text-xs text-text-secondary font-mono overflow-x-auto max-h-96 overflow-y-auto">
          {JSON.stringify(a11y, null, 2)}
        </pre>
      )}
    </div>
  )
}

// ─── Deployment Info Tab ───────────────────────────────────────────────────────

function DeploymentInfoTab({ outputs }: { outputs?: Record<string, any> }) {
  const deploymentReport = outputs?.deployment?.report
  const verificationReport = outputs?.post_deploy_verification?.report
  const monitoringReport = outputs?.analytics_monitoring?.report
  const codingStandardsReport = outputs?.coding_standards?.report

  if (!deploymentReport && !verificationReport && !monitoringReport && !codingStandardsReport) {
    return <NoData />
  }

  return (
    <div className="space-y-6">
      {/* Deployment Status */}
      {deploymentReport && (
        <div>
          <h4 className="text-sm font-medium text-text-primary mb-3 flex items-center gap-2">
            <Rocket className="w-4 h-4 text-accent-primary" />
            Deployment Status
          </h4>
          <div className="space-y-3">
            {deploymentReport.deployments?.map((deployment: any, idx: number) => (
              <div key={idx} className="p-4 bg-background-tertiary rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-text-primary capitalize">{deployment.platform}</span>
                    <Badge variant={
                      deployment.status === 'deployed' ? 'success' :
                      deployment.status === 'failed' ? 'error' :
                      deployment.status === 'deploying' || deployment.status === 'building' ? 'info' : 'default'
                    }>
                      {deployment.status}
                    </Badge>
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
            <div className="mt-3 p-3 bg-green-500/10 rounded-lg">
              <p className="text-sm text-green-400 flex items-center gap-2">
                <CheckCircle className="w-4 h-4" />
                GitHub Actions workflows generated
              </p>
              {deploymentReport.github_actions_files?.length > 0 && (
                <ul className="mt-2 text-xs text-text-secondary">
                  {deploymentReport.github_actions_files.map((file: string, idx: number) => (
                    <li key={idx}>{'\u2022'} {file.split('/').slice(-2).join('/')}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* Manual Instructions */}
          {deploymentReport.manual_instructions?.length > 0 && (
            <details className="mt-3">
              <summary className="cursor-pointer text-sm font-medium text-text-secondary hover:text-text-primary">
                Manual Setup Instructions
              </summary>
              <pre className="mt-3 p-3 bg-background-tertiary rounded-lg text-xs whitespace-pre-wrap text-text-secondary">
                {deploymentReport.manual_instructions.join('\n')}
              </pre>
            </details>
          )}
        </div>
      )}

      {/* Post-Deploy Verification */}
      {verificationReport && (
        <div>
          <h4 className="text-sm font-medium text-text-primary mb-3 flex items-center gap-2">
            <Globe className="w-4 h-4 text-accent-primary" />
            Post-Deploy Verification
            <Badge variant={verificationReport.overall_status === 'passed' ? 'success' :
                           verificationReport.overall_status === 'partial' ? 'warning' : 'error'}>
              {verificationReport.overall_status}
            </Badge>
          </h4>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <div className="bg-green-500/10 rounded-lg p-3 text-center">
              <div className="text-xl font-bold text-green-400">{verificationReport.checks_passed || 0}</div>
              <div className="text-xs text-text-secondary">Checks Passed</div>
            </div>
            <div className="bg-red-500/10 rounded-lg p-3 text-center">
              <div className="text-xl font-bold text-red-400">{verificationReport.checks_failed || 0}</div>
              <div className="text-xs text-text-secondary">Checks Failed</div>
            </div>
            <div className={`rounded-lg p-3 text-center ${verificationReport.ssl_valid ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
              <div className="text-xl font-bold text-text-primary">{verificationReport.ssl_valid ? 'Valid' : 'Invalid'}</div>
              <div className="text-xs text-text-secondary">SSL Status</div>
            </div>
            {verificationReport.visual_diff_score != null && (
              <div className="bg-background-tertiary rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-text-primary">{Math.round((verificationReport.visual_diff_score || 0) * 100)}%</div>
                <div className="text-xs text-text-secondary">Visual Match</div>
              </div>
            )}
          </div>

          {/* Endpoint Checks */}
          {verificationReport.endpoint_checks?.length > 0 && (
            <details className="group mb-3">
              <summary className="cursor-pointer text-sm font-medium text-text-secondary hover:text-text-primary">
                Endpoint Health Checks ({verificationReport.endpoint_checks.length})
              </summary>
              <div className="mt-3 space-y-2 max-h-48 overflow-y-auto">
                {verificationReport.endpoint_checks.map((check: any, idx: number) => (
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
          {verificationReport.verification_results?.length > 0 && (
            <details className="group">
              <summary className="cursor-pointer text-sm font-medium text-text-secondary hover:text-text-primary">
                Verification Details
              </summary>
              <div className="mt-3 space-y-2">
                {verificationReport.verification_results.map((result: any, idx: number) => (
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

          {verificationReport.deployment_url && (
            <div className="mt-3 p-3 bg-background-tertiary rounded-lg">
              <a
                href={verificationReport.deployment_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-accent-primary hover:underline flex items-center gap-2"
              >
                <ExternalLink className="w-4 h-4" />
                {verificationReport.deployment_url}
              </a>
            </div>
          )}
        </div>
      )}

      {/* Monitoring */}
      {monitoringReport && (
        <div>
          <h4 className="text-sm font-medium text-text-primary mb-3 flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-accent-primary" />
            Monitoring & Analytics
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
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
          <div className="p-3 bg-background-tertiary rounded-lg">
            <p className="text-sm text-text-secondary">
              Configured: <span className="text-text-primary font-medium">{monitoringReport.total_configured || 0}</span> / {monitoringReport.total_available || 0} services
            </p>
          </div>
        </div>
      )}

      {/* Coding Standards */}
      {codingStandardsReport && (
        <div>
          <h4 className="text-sm font-medium text-text-primary mb-3 flex items-center gap-2">
            <FileText className="w-4 h-4 text-accent-primary" />
            Documentation & Standards
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
            {codingStandardsReport.documents?.filter((d: any) => d.generated).map((doc: any, idx: number) => (
              <div key={idx} className="p-3 bg-green-500/10 rounded-lg">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-green-400" />
                  <span className="text-sm text-text-primary">{doc.name}</span>
                </div>
                <span className="text-xs text-text-tertiary capitalize">{doc.type?.replace('_', ' ')}</span>
              </div>
            ))}
          </div>
          {codingStandardsReport.style_configs?.length > 0 && (
            <div className="mb-3">
              <span className="text-xs text-text-tertiary">Style Configs: </span>
              <span className="text-xs text-text-secondary">{codingStandardsReport.style_configs.join(', ')}</span>
            </div>
          )}
          <div className="p-3 bg-background-tertiary rounded-lg">
            <p className="text-sm text-text-secondary">
              Total Documents: <span className="text-text-primary font-medium">{codingStandardsReport.total_generated || 0}</span> files generated
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Cost Breakdown Tab ────────────────────────────────────────────────────────

function CostBreakdownTab({ agentLogs }: { agentLogs?: any[] }) {
  if (!agentLogs || agentLogs.length === 0) return <NoData label="No cost data available for this project." />

  // Aggregate costs by agent
  const costByAgent: Record<string, { cost: number; tokens: number; calls: number; duration: number }> = {}
  let totalCost = 0
  let totalTokens = 0

  for (const log of agentLogs) {
    const name = log.agent_name || 'unknown'
    if (!costByAgent[name]) {
      costByAgent[name] = { cost: 0, tokens: 0, calls: 0, duration: 0 }
    }
    costByAgent[name].cost += log.cost || 0
    costByAgent[name].tokens += log.total_tokens || 0
    costByAgent[name].calls += 1
    costByAgent[name].duration += log.duration_ms || 0
    totalCost += log.cost || 0
    totalTokens += log.total_tokens || 0
  }

  const sortedAgents = Object.entries(costByAgent).sort((a, b) => b[1].cost - a[1].cost)

  return (
    <div className="space-y-6">
      {/* Totals */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-background-tertiary rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-text-primary">${totalCost.toFixed(4)}</div>
          <div className="text-sm text-text-secondary">Total Cost</div>
        </div>
        <div className="bg-background-tertiary rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-text-primary">{totalTokens.toLocaleString()}</div>
          <div className="text-sm text-text-secondary">Total Tokens</div>
        </div>
        <div className="bg-background-tertiary rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-text-primary">{agentLogs.length}</div>
          <div className="text-sm text-text-secondary">API Calls</div>
        </div>
      </div>

      {/* Cost by Agent Table */}
      <div>
        <h4 className="text-sm font-medium text-text-primary mb-3">Cost per Agent</h4>
        <div className="bg-background-tertiary rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-subtle">
                <th className="text-left p-3 text-text-tertiary font-medium">Agent</th>
                <th className="text-right p-3 text-text-tertiary font-medium">Cost</th>
                <th className="text-right p-3 text-text-tertiary font-medium hidden md:table-cell">Tokens</th>
                <th className="text-right p-3 text-text-tertiary font-medium hidden md:table-cell">Calls</th>
                <th className="text-right p-3 text-text-tertiary font-medium hidden lg:table-cell">Duration</th>
              </tr>
            </thead>
            <tbody>
              {sortedAgents.map(([name, data]) => (
                <tr key={name} className="border-b border-border-subtle/50">
                  <td className="p-3 text-text-primary capitalize">{name.replace(/_/g, ' ')}</td>
                  <td className="p-3 text-text-primary text-right font-mono">${data.cost.toFixed(4)}</td>
                  <td className="p-3 text-text-secondary text-right font-mono hidden md:table-cell">{data.tokens.toLocaleString()}</td>
                  <td className="p-3 text-text-secondary text-right hidden md:table-cell">{data.calls}</td>
                  <td className="p-3 text-text-secondary text-right font-mono hidden lg:table-cell">{(data.duration / 1000).toFixed(1)}s</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Token Usage Details */}
      <details className="group">
        <summary className="cursor-pointer text-sm font-medium text-text-secondary hover:text-text-primary">
          Detailed API Call Log ({agentLogs.length} calls)
        </summary>
        <div className="mt-3 space-y-2 max-h-64 overflow-y-auto">
          {agentLogs.map((log, idx) => (
            <div key={idx} className="flex items-center justify-between p-2 bg-background-tertiary rounded text-xs">
              <div className="flex items-center gap-2">
                <Badge variant={log.status === 'completed' ? 'success' : log.status === 'failed' ? 'error' : 'default'} className="text-xs">
                  {log.agent_name?.replace(/_/g, ' ')}
                </Badge>
                <span className="text-text-tertiary hidden md:inline">{log.model_used}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-text-secondary font-mono">{(log.total_tokens || 0).toLocaleString()} tok</span>
                <span className="text-text-primary font-mono">${(log.cost || 0).toFixed(4)}</span>
              </div>
            </div>
          ))}
        </div>
      </details>
    </div>
  )
}
