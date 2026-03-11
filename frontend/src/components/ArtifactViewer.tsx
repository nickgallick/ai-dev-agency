import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card } from '@/components/Card'
import {
  ExternalLink, Github, Download, FileText, Folder, Globe,
  Code2, Shield, Eye, Rocket, DollarSign, Check,
  Copy, ChevronRight, ChevronDown, AlertTriangle, CheckCircle2,
  XCircle, Cpu, Lock, Search, Smartphone, Monitor,
  Terminal, Chrome, Package, FileCode2,
} from 'lucide-react'
import { Button } from '@/components/Button'

// ─── Types ─────────────────────────────────────────────────────────────────

type TabId = 'overview' | 'architecture' | 'design' | 'code' | 'qa' | 'security' | 'seo' | 'accessibility' | 'deployment' | 'costs'

interface ArtifactViewerProps {
  projectId: string
  projectType?: string | null
  liveUrl?: string | null
  githubRepo?: string | null
  agentOutputs?: Record<string, any>
}

// ─── Helpers ────────────────────────────────────────────────────────────────

function ScoreCircle({ score, label, color }: { score: number; label: string; color: string }) {
  const pct = Math.round(score)
  const radius = 28
  const circ = 2 * Math.PI * radius
  const strokeDash = (pct / 100) * circ
  return (
    <div className="flex flex-col items-center gap-1">
      <svg width="72" height="72" viewBox="0 0 72 72">
        <circle cx="36" cy="36" r={radius} fill="none" stroke="var(--bg-secondary)" strokeWidth="6" />
        <circle
          cx="36" cy="36" r={radius}
          fill="none" stroke={color} strokeWidth="6"
          strokeDasharray={`${strokeDash} ${circ}`}
          strokeLinecap="round"
          transform="rotate(-90 36 36)"
          style={{ transition: 'stroke-dasharray 0.6s ease' }}
        />
        <text x="36" y="40" textAnchor="middle" fontSize="14" fontWeight="bold" fill="var(--text-primary)">{pct}</text>
      </svg>
      <span className="text-xs text-text-secondary">{label}</span>
    </div>
  )
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }
  return (
    <button
      onClick={copy}
      className="flex items-center gap-1 px-2 py-1 rounded text-xs bg-bg-secondary hover:bg-border-subtle text-text-secondary hover:text-text-primary transition-colors"
    >
      {copied ? <Check className="w-3 h-3 text-accent-success" /> : <Copy className="w-3 h-3" />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

function CodeBlock({ content, language = 'text' }: { content: string; language?: string }) {
  return (
    <div className="relative group rounded-lg overflow-hidden border border-border-subtle">
      <div className="flex items-center justify-between px-3 py-2 bg-bg-secondary border-b border-border-subtle">
        <span className="text-xs text-text-tertiary font-mono">{language}</span>
        <CopyButton text={content} />
      </div>
      <pre className="overflow-x-auto p-4 text-xs font-mono text-text-primary bg-bg-primary leading-relaxed max-h-96 overflow-y-auto">
        <code>{content}</code>
      </pre>
    </div>
  )
}

function FileTree({
  files,
  selectedFile,
  onSelect,
}: {
  files: string[]
  selectedFile: string | null
  onSelect: (f: string) => void
}) {
  // Group files by top-level directory for a simple grouped view
  const groups: Record<string, string[]> = {}
  const rootFiles: string[] = []
  files.forEach((path) => {
    const parts = path.split('/')
    if (parts.length === 1) {
      rootFiles.push(path)
    } else {
      const dir = parts[0]
      groups[dir] = groups[dir] || []
      groups[dir].push(path)
    }
  })

  return (
    <div className="space-y-0.5">
      {rootFiles.map((file) => (
        <button
          key={file}
          onClick={() => onSelect(file)}
          className={`w-full text-left flex items-center gap-1.5 px-2 py-1 rounded text-xs font-mono transition-colors ${
            selectedFile === file
              ? 'bg-accent-primary/20 text-accent-primary'
              : 'text-text-secondary hover:bg-bg-secondary hover:text-text-primary'
          }`}
        >
          <FileCode2 className="w-3 h-3 flex-shrink-0" />
          {file}
        </button>
      ))}
      {Object.entries(groups).map(([dir, dirFiles]) => (
        <DirGroup key={dir} dir={dir} files={dirFiles} selectedFile={selectedFile} onSelect={onSelect} />
      ))}
    </div>
  )
}

function DirGroup({ dir, files, selectedFile, onSelect }: {
  dir: string; files: string[]; selectedFile: string | null; onSelect: (f: string) => void
}) {
  const [open, setOpen] = useState(true)
  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="w-full text-left flex items-center gap-1.5 px-2 py-1 rounded text-xs font-mono text-text-tertiary hover:text-text-secondary hover:bg-bg-secondary/50 transition-colors"
      >
        {open ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        <Folder className="w-3 h-3 text-accent-warning" />
        {dir}
      </button>
      {open && (
        <div className="pl-3">
          {files.map((file) => (
            <button
              key={file}
              onClick={() => onSelect(file)}
              className={`w-full text-left flex items-center gap-1.5 px-2 py-1 rounded text-xs font-mono transition-colors ${
                selectedFile === file
                  ? 'bg-accent-primary/20 text-accent-primary'
                  : 'text-text-secondary hover:bg-bg-secondary hover:text-text-primary'
              }`}
            >
              <FileCode2 className="w-3 h-3 flex-shrink-0" />
              {file.split('/').slice(1).join('/')}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 py-2 border-b border-border-subtle/50 last:border-0">
      <span className="text-sm text-text-secondary whitespace-nowrap">{label}</span>
      <span className="text-sm text-text-primary text-right font-medium">{value}</span>
    </div>
  )
}

function SeverityBadge({ level }: { level: string }) {
  const cls = {
    critical: 'bg-accent-error/20 text-accent-error',
    high: 'bg-accent-error/15 text-accent-error',
    medium: 'bg-accent-warning/20 text-accent-warning',
    low: 'bg-accent-secondary/20 text-accent-secondary',
    info: 'bg-bg-secondary text-text-tertiary',
  }[level.toLowerCase()] || 'bg-bg-secondary text-text-tertiary'
  return <span className={`px-2 py-0.5 text-xs rounded font-medium ${cls}`}>{level}</span>
}


const TABS: { id: TabId; label: string; icon: React.ElementType }[] = [
  { id: 'overview', label: 'Overview', icon: Eye },
  { id: 'architecture', label: 'Architecture', icon: Cpu },
  { id: 'design', label: 'Design System', icon: Globe },
  { id: 'code', label: 'Generated Code', icon: Code2 },
  { id: 'qa', label: 'QA Report', icon: CheckCircle2 },
  { id: 'security', label: 'Security', icon: Shield },
  { id: 'seo', label: 'SEO', icon: Search },
  { id: 'accessibility', label: 'Accessibility', icon: Eye },
  { id: 'deployment', label: 'Deployment', icon: Rocket },
  { id: 'costs', label: 'Cost Breakdown', icon: DollarSign },
]

// ─── Main Component ─────────────────────────────────────────────────────────

export function ArtifactViewer({ projectId, projectType, liveUrl, githubRepo, agentOutputs }: ArtifactViewerProps) {
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [selectedFile, setSelectedFile] = useState<string | null>(null)

  const { data: artifacts, isLoading } = useQuery({
    queryKey: ['artifacts', projectId],
    queryFn: () => api.getProjectArtifacts(projectId),
    enabled: !!projectId,
  })

  const { data: projectLogs } = useQuery({
    queryKey: ['projectLogs', projectId],
    queryFn: () => api.getAgentLogs({ project_id: projectId, limit: 500 }),
    enabled: activeTab === 'costs',
  })

  const effectiveLiveUrl = artifacts?.live_url || liveUrl
  const effectiveGithubRepo = artifacts?.github_repo || githubRepo

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

  if (isLoading) {
    return (
      <Card>
        <div className="h-48 bg-background-tertiary rounded animate-pulse" />
      </Card>
    )
  }

  // Agent output shortcuts
  const ao = agentOutputs || {}
  const intake = ao.intake || {}
  const architect = ao.architect || {}
  const design = ao.design_system || {}
  const codeGen = ao.code_generation || {}
  const qa = ao.qa?.report || ao.qa || {}
  const security = ao.security?.report || ao.security || {}
  const seo = ao.seo?.report || ao.seo || {}
  const accessibility = ao.accessibility?.report || ao.accessibility || {}
  const deployment = ao.deployment?.report || ao.deployment || {}
  const postDeploy = ao.post_deploy_verification || {}

  // Quality scores (0-100)
  const qaScore = typeof qa.quality_score === 'number' ? (qa.quality_score > 1 ? qa.quality_score : qa.quality_score * 100) : null
  const secScore = security.score ?? (security.findings?.length === 0 ? 100 : null)
  const seoScore = typeof seo.score === 'number' ? seo.score : null
  const a11yScore = typeof accessibility.score === 'number' ? accessibility.score : null

  // Files from code generation
  const generatedFiles: Record<string, string> = codeGen.files || {}
  const fileList = artifacts?.file_structure || Object.keys(generatedFiles)

  const activeFileContent = selectedFile
    ? generatedFiles[selectedFile] || '# No content available for this file'
    : null

  // Cost aggregation per agent
  const costByAgent: Record<string, { cost: number; tokens: number; calls: number }> = {}
  projectLogs?.forEach((log) => {
    if (!costByAgent[log.agent_name]) costByAgent[log.agent_name] = { cost: 0, tokens: 0, calls: 0 }
    costByAgent[log.agent_name].cost += log.cost || 0
    costByAgent[log.agent_name].tokens += log.total_tokens || 0
    costByAgent[log.agent_name].calls += 1
  })
  const totalProjectCost = Object.values(costByAgent).reduce((s, v) => s + v.cost, 0)

  return (
    <Card padding="none">
      {/* Tab Navigation */}
      <div className="border-b border-border-subtle overflow-x-auto">
        <div className="flex min-w-max">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-accent-primary text-accent-primary'
                  : 'border-transparent text-text-secondary hover:text-text-primary hover:border-border-subtle'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="p-6">
        {/* ── Overview ─────────────────────────────────── */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            <div className="flex flex-wrap gap-3">
              {effectiveLiveUrl && (
                <a href={effectiveLiveUrl} target="_blank" rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-accent-primary/20 rounded-lg text-accent-primary hover:bg-accent-primary/30 transition-colors text-sm font-medium">
                  <ExternalLink className="w-4 h-4" />
                  View Live
                </a>
              )}
              {effectiveGithubRepo && (
                <a href={effectiveGithubRepo} target="_blank" rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-bg-secondary rounded-lg text-text-primary hover:bg-border-subtle transition-colors text-sm">
                  <Github className="w-4 h-4" />
                  View Source
                </a>
              )}
              <Button variant="ghost" size="sm" onClick={handleDownload}>
                <Download className="w-4 h-4 mr-2" />
                Download ZIP
              </Button>
            </div>

            {/* Project info */}
            {intake && Object.keys(intake).length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-text-primary mb-3">Project Details</h4>
                <div className="bg-bg-secondary rounded-lg p-4 space-y-1">
                  {intake.project_type && <InfoRow label="Type" value={intake.project_type.replace(/_/g, ' ')} />}
                  {intake.industry && <InfoRow label="Industry" value={intake.industry} />}
                  {intake.complexity && <InfoRow label="Complexity" value={intake.complexity} />}
                  {intake.features && Array.isArray(intake.features) && (
                    <InfoRow label="Features" value={
                      <div className="flex flex-wrap gap-1 justify-end">
                        {intake.features.slice(0, 6).map((f: string) => (
                          <span key={f} className="px-2 py-0.5 bg-accent-primary/10 text-accent-primary text-xs rounded">{f}</span>
                        ))}
                      </div>
                    } />
                  )}
                </div>
              </div>
            )}

            {/* Quality Scores */}
            {(qaScore !== null || secScore !== null || seoScore !== null || a11yScore !== null) && (
              <div>
                <h4 className="text-sm font-semibold text-text-primary mb-3">Quality Scores</h4>
                <div className="flex flex-wrap gap-6 justify-center p-4 bg-bg-secondary rounded-lg">
                  {qaScore !== null && <ScoreCircle score={qaScore} label="QA" color="var(--accent-success, #22c55e)" />}
                  {secScore !== null && <ScoreCircle score={secScore} label="Security" color="var(--accent-primary, #6366f1)" />}
                  {seoScore !== null && <ScoreCircle score={seoScore} label="SEO" color="var(--accent-secondary)" />}
                  {a11yScore !== null && <ScoreCircle score={a11yScore} label="Accessibility" color="var(--accent-purple)" />}
                </div>
              </div>
            )}

            {/* Deployment URLs */}
            {artifacts?.deployment_urls && artifacts.deployment_urls.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-text-primary mb-3">Deployments</h4>
                <div className="flex flex-wrap gap-2">
                  {artifacts.deployment_urls.map((dep, idx) => (
                    <a key={idx} href={dep.url} target="_blank" rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 px-3 py-1.5 bg-accent-success/10 rounded-lg text-accent-success hover:bg-accent-success/20 transition-colors text-xs">
                      <Rocket className="w-3 h-3" />
                      {dep.platform}
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* README */}
            {artifacts?.readme_content && (
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                    <FileText className="w-4 h-4" />
                    README
                  </h4>
                  <CopyButton text={artifacts.readme_content} />
                </div>
                <CodeBlock content={artifacts.readme_content} language="markdown" />
              </div>
            )}
          </div>
        )}

        {/* ── Architecture ─────────────────────────────── */}
        {activeTab === 'architecture' && (
          <div className="space-y-6">
            <h3 className="text-base font-semibold text-text-primary flex items-center gap-2">
              <Cpu className="w-5 h-5 text-accent-primary" />
              Architecture Plan
            </h3>
            {Object.keys(architect).length === 0 ? (
              <p className="text-sm text-text-secondary">Architecture data not available.</p>
            ) : (
              <>
                {architect.tech_stack && (
                  <div>
                    <h4 className="text-sm font-medium text-text-secondary mb-2">Tech Stack</h4>
                    <div className="bg-bg-secondary rounded-lg p-4 space-y-1">
                      {Object.entries(architect.tech_stack).map(([k, v]) => (
                        <InfoRow key={k} label={k} value={String(v)} />
                      ))}
                    </div>
                  </div>
                )}
                {architect.pages && Array.isArray(architect.pages) && (
                  <div>
                    <h4 className="text-sm font-medium text-text-secondary mb-2">Pages</h4>
                    <div className="grid grid-cols-2 gap-2">
                      {architect.pages.map((page: any, i: number) => (
                        <div key={i} className="p-3 bg-bg-secondary rounded-lg">
                          <p className="text-sm font-medium text-text-primary">{typeof page === 'string' ? page : page.name}</p>
                          {page.description && <p className="text-xs text-text-secondary mt-1">{page.description}</p>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {architect.components && Array.isArray(architect.components) && (
                  <div>
                    <h4 className="text-sm font-medium text-text-secondary mb-2">Components</h4>
                    <div className="flex flex-wrap gap-2">
                      {architect.components.map((c: any, i: number) => (
                        <span key={i} className="px-3 py-1.5 bg-accent-primary/10 text-accent-primary text-sm rounded-lg">
                          {typeof c === 'string' ? c : c.name}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {Object.keys(architect).filter(k => !['tech_stack', 'pages', 'components'].includes(k)).length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-text-secondary mb-2">Additional Details</h4>
                    <CodeBlock content={JSON.stringify(
                      Object.fromEntries(Object.entries(architect).filter(([k]) => !['tech_stack', 'pages', 'components'].includes(k))),
                      null, 2
                    )} language="json" />
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ── Design System ────────────────────────────── */}
        {activeTab === 'design' && (
          <div className="space-y-6">
            <h3 className="text-base font-semibold text-text-primary">Design System</h3>
            {Object.keys(design).length === 0 ? (
              <p className="text-sm text-text-secondary">Design system data not available.</p>
            ) : (
              <>
                {design.colors && (
                  <div>
                    <h4 className="text-sm font-medium text-text-secondary mb-3">Color Palette</h4>
                    <div className="flex flex-wrap gap-3">
                      {Object.entries(design.colors).map(([name, hex]) => (
                        <div key={name} className="flex items-center gap-2">
                          <div
                            className="w-8 h-8 rounded-lg border border-border-subtle shadow"
                            style={{ backgroundColor: String(hex) }}
                          />
                          <div>
                            <p className="text-xs font-medium text-text-primary">{name}</p>
                            <p className="text-xs text-text-tertiary font-mono">{String(hex)}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {design.typography && (
                  <div>
                    <h4 className="text-sm font-medium text-text-secondary mb-2">Typography</h4>
                    <div className="bg-bg-secondary rounded-lg p-4 space-y-1">
                      {Object.entries(design.typography).map(([k, v]) => (
                        <InfoRow key={k} label={k} value={String(v)} />
                      ))}
                    </div>
                  </div>
                )}
                {design.design_tokens && (
                  <div>
                    <h4 className="text-sm font-medium text-text-secondary mb-2">Design Tokens</h4>
                    <CodeBlock content={JSON.stringify(design.design_tokens, null, 2)} language="json" />
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ── Generated Code ───────────────────────────── */}
        {activeTab === 'code' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-semibold text-text-primary flex items-center gap-2">
                <Code2 className="w-5 h-5 text-accent-primary" />
                Generated Code
              </h3>
              {codeGen.lines_of_code && (
                <span className="text-sm text-text-secondary">
                  {codeGen.lines_of_code?.toLocaleString()} lines across {fileList.length} files
                </span>
              )}
            </div>
            {fileList.length === 0 ? (
              <p className="text-sm text-text-secondary">No generated files available.</p>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
                {/* File Tree */}
                <div className="lg:col-span-1 bg-bg-secondary rounded-lg p-3 h-96 overflow-y-auto">
                  <p className="text-xs font-medium text-text-tertiary uppercase tracking-wide mb-2 px-2">Files</p>
                  <FileTree
                    files={fileList}
                    selectedFile={selectedFile}
                    onSelect={setSelectedFile}
                  />
                </div>
                {/* Code Viewer */}
                <div className="lg:col-span-3">
                  {selectedFile ? (
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-mono text-text-secondary">{selectedFile}</span>
                        {activeFileContent && <CopyButton text={activeFileContent} />}
                      </div>
                      {activeFileContent ? (
                        <CodeBlock
                          content={activeFileContent}
                          language={selectedFile.split('.').pop() || 'text'}
                        />
                      ) : (
                        <div className="p-8 bg-bg-secondary rounded-lg text-center text-sm text-text-secondary">
                          File content not available — download the ZIP to view.
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="h-full bg-bg-secondary rounded-lg flex items-center justify-center p-8">
                      <div className="text-center">
                        <FileCode2 className="w-12 h-12 text-text-tertiary mx-auto mb-3" />
                        <p className="text-sm text-text-secondary">Select a file from the tree to view its contents</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── QA Report ────────────────────────────────── */}
        {activeTab === 'qa' && (
          <div className="space-y-6">
            <h3 className="text-base font-semibold text-text-primary flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-accent-success" />
              QA Report
            </h3>
            {Object.keys(qa).length === 0 ? (
              <p className="text-sm text-text-secondary">QA data not available.</p>
            ) : (
              <>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  {qa.total_tests != null && (
                    <div className="p-4 bg-bg-secondary rounded-lg text-center">
                      <p className="text-2xl font-bold text-text-primary">{qa.total_tests}</p>
                      <p className="text-xs text-text-secondary">Total Tests</p>
                    </div>
                  )}
                  {qa.passed != null && (
                    <div className="p-4 bg-accent-success/10 rounded-lg text-center">
                      <p className="text-2xl font-bold text-accent-success">{qa.passed}</p>
                      <p className="text-xs text-text-secondary">Passed</p>
                    </div>
                  )}
                  {qa.failed != null && (
                    <div className="p-4 bg-accent-error/10 rounded-lg text-center">
                      <p className="text-2xl font-bold text-accent-error">{qa.failed}</p>
                      <p className="text-xs text-text-secondary">Failed</p>
                    </div>
                  )}
                  {qaScore !== null && (
                    <div className="p-4 bg-bg-secondary rounded-lg flex items-center justify-center">
                      <ScoreCircle score={qaScore} label="Quality" color="var(--accent-success, #22c55e)" />
                    </div>
                  )}
                </div>
                {qa.summary && (
                  <div className="p-4 bg-bg-secondary rounded-lg">
                    <p className="text-sm text-text-secondary">{qa.summary}</p>
                  </div>
                )}
                {qa.test_results && Array.isArray(qa.test_results) && qa.test_results.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-text-secondary mb-2">Test Results</h4>
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                      {qa.test_results.map((t: any, i: number) => (
                        <div key={i} className="flex items-start gap-3 p-3 bg-bg-secondary rounded-lg">
                          {t.passed ? (
                            <CheckCircle2 className="w-4 h-4 text-accent-success flex-shrink-0 mt-0.5" />
                          ) : (
                            <XCircle className="w-4 h-4 text-accent-error flex-shrink-0 mt-0.5" />
                          )}
                          <div>
                            <p className="text-sm text-text-primary">{t.name || t.test}</p>
                            {t.error && <p className="text-xs text-accent-error mt-1">{t.error}</p>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {qa.quality_issues && Array.isArray(qa.quality_issues) && qa.quality_issues.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-text-secondary mb-2">Quality Issues</h4>
                    <div className="space-y-2">
                      {qa.quality_issues.map((issue: any, i: number) => (
                        <div key={i} className="flex items-start gap-3 p-3 bg-accent-warning/5 border border-accent-warning/20 rounded-lg">
                          <AlertTriangle className="w-4 h-4 text-accent-warning flex-shrink-0 mt-0.5" />
                          <p className="text-sm text-text-secondary">{typeof issue === 'string' ? issue : issue.description || JSON.stringify(issue)}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ── Security ──────────────────────────────────── */}
        {activeTab === 'security' && (
          <div className="space-y-6">
            <h3 className="text-base font-semibold text-text-primary flex items-center gap-2">
              <Shield className="w-5 h-5 text-accent-primary" />
              Security Report
            </h3>
            {Object.keys(security).length === 0 ? (
              <p className="text-sm text-text-secondary">Security data not available.</p>
            ) : (
              <>
                <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                  {security.findings != null && (
                    <div className="p-4 bg-bg-secondary rounded-lg text-center">
                      <p className="text-2xl font-bold text-text-primary">{Array.isArray(security.findings) ? security.findings.length : security.findings}</p>
                      <p className="text-xs text-text-secondary">Total Findings</p>
                    </div>
                  )}
                  {security.auto_fixed != null && (
                    <div className="p-4 bg-accent-success/10 rounded-lg text-center">
                      <p className="text-2xl font-bold text-accent-success">{security.auto_fixed}</p>
                      <p className="text-xs text-text-secondary">Auto-Fixed</p>
                    </div>
                  )}
                  {security.vulnerabilities != null && (
                    <div className="p-4 bg-accent-error/10 rounded-lg text-center">
                      <p className="text-2xl font-bold text-accent-error">
                        {Array.isArray(security.vulnerabilities) ? security.vulnerabilities.length : security.vulnerabilities}
                      </p>
                      <p className="text-xs text-text-secondary">Vulnerabilities</p>
                    </div>
                  )}
                </div>
                {Array.isArray(security.findings) && security.findings.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-text-secondary mb-2">Findings</h4>
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                      {security.findings.map((f: any, i: number) => (
                        <div key={i} className="p-3 bg-bg-secondary rounded-lg flex items-start gap-3">
                          <Lock className="w-4 h-4 text-accent-error flex-shrink-0 mt-0.5" />
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              {f.severity && <SeverityBadge level={f.severity} />}
                              <span className="text-sm text-text-primary">{f.title || f.name || f.description}</span>
                            </div>
                            {f.file && <p className="text-xs text-text-tertiary font-mono">{f.file}{f.line ? `:${f.line}` : ''}</p>}
                            {f.remediation && <p className="text-xs text-text-secondary mt-1">{f.remediation}</p>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {(!Array.isArray(security.findings) || security.findings.length === 0) && (
                  <div className="flex items-center gap-3 p-4 bg-accent-success/10 rounded-lg">
                    <CheckCircle2 className="w-5 h-5 text-accent-success" />
                    <p className="text-sm text-accent-success">No security issues found</p>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ── SEO ─────────────────────────────────────── */}
        {activeTab === 'seo' && (
          <div className="space-y-6">
            <h3 className="text-base font-semibold text-text-primary flex items-center gap-2">
              <Search className="w-5 h-5 text-accent-secondary" />
              SEO Report
            </h3>
            {Object.keys(seo).length === 0 ? (
              <p className="text-sm text-text-secondary">SEO data not available.</p>
            ) : (
              <>
                <div className="flex items-center gap-6">
                  {seoScore !== null && (
                    <ScoreCircle score={seoScore} label="SEO Score" color="var(--accent-secondary)" />
                  )}
                  <div className="flex-1 space-y-1">
                    {seo.meta_tags && <InfoRow label="Meta Tags" value={seo.meta_tags} />}
                    {seo.structured_data != null && (
                      <InfoRow label="Structured Data" value={seo.structured_data ? 'Present' : 'Missing'} />
                    )}
                    {seo.sitemap != null && (
                      <InfoRow label="Sitemap" value={seo.sitemap ? 'Generated' : 'Not generated'} />
                    )}
                  </div>
                </div>
                {Array.isArray(seo.issues) && seo.issues.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-text-secondary mb-2">Issues</h4>
                    <div className="space-y-2">
                      {seo.issues.map((issue: any, i: number) => (
                        <div key={i} className="flex items-start gap-3 p-3 bg-accent-warning/5 border border-accent-warning/20 rounded-lg">
                          <AlertTriangle className="w-4 h-4 text-accent-warning flex-shrink-0 mt-0.5" />
                          <p className="text-sm text-text-secondary">{typeof issue === 'string' ? issue : issue.description || JSON.stringify(issue)}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ── Accessibility ─────────────────────────────── */}
        {activeTab === 'accessibility' && (
          <div className="space-y-6">
            <h3 className="text-base font-semibold text-text-primary flex items-center gap-2">
              <Eye className="w-5 h-5 text-accent-purple" />
              Accessibility Report
            </h3>
            {Object.keys(accessibility).length === 0 ? (
              <p className="text-sm text-text-secondary">Accessibility data not available.</p>
            ) : (
              <>
                <div className="flex items-center gap-6">
                  {a11yScore !== null && (
                    <ScoreCircle score={a11yScore} label="A11y Score" color="var(--accent-purple)" />
                  )}
                  <div className="flex-1 space-y-1">
                    {accessibility.compliance_level && (
                      <InfoRow label="Compliance Level" value={
                        <span className="px-2 py-0.5 bg-accent-purple/20 text-accent-purple text-xs rounded font-medium">
                          {accessibility.compliance_level}
                        </span>
                      } />
                    )}
                    {accessibility.violations != null && (
                      <InfoRow label="Violations" value={Array.isArray(accessibility.violations) ? accessibility.violations.length : accessibility.violations} />
                    )}
                  </div>
                </div>
                {Array.isArray(accessibility.violations) && accessibility.violations.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-text-secondary mb-2">Violations</h4>
                    <div className="space-y-2 max-h-72 overflow-y-auto">
                      {accessibility.violations.map((v: any, i: number) => (
                        <div key={i} className="p-3 bg-bg-secondary rounded-lg">
                          <div className="flex items-center gap-2 mb-1">
                            {v.impact && <SeverityBadge level={v.impact} />}
                            <span className="text-sm text-text-primary">{v.description || v.id || String(v)}</span>
                          </div>
                          {v.helpUrl && (
                            <a href={v.helpUrl} target="_blank" rel="noopener noreferrer" className="text-xs text-accent-primary hover:underline">
                              Learn more
                            </a>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {(!Array.isArray(accessibility.violations) || accessibility.violations.length === 0) && (
                  <div className="flex items-center gap-3 p-4 bg-accent-success/10 rounded-lg">
                    <CheckCircle2 className="w-5 h-5 text-accent-success" />
                    <p className="text-sm text-accent-success">No accessibility violations found</p>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ── Deployment ────────────────────────────────── */}
        {activeTab === 'deployment' && (
          <div className="space-y-6">
            <h3 className="text-base font-semibold text-text-primary flex items-center gap-2">
              <Rocket className="w-5 h-5 text-accent-primary" />
              Deployment Info
            </h3>
            {/* Links */}
            <div className="flex flex-wrap gap-3">
              {effectiveLiveUrl && (
                <a href={effectiveLiveUrl} target="_blank" rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-accent-primary/20 rounded-lg text-accent-primary hover:bg-accent-primary/30 text-sm font-medium">
                  <Globe className="w-4 h-4" />
                  {effectiveLiveUrl}
                </a>
              )}
              {effectiveGithubRepo && (
                <a href={effectiveGithubRepo} target="_blank" rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-bg-secondary rounded-lg text-text-secondary hover:text-text-primary text-sm">
                  <Github className="w-4 h-4" />
                  {effectiveGithubRepo}
                </a>
              )}
            </div>

            {/* Deployment report */}
            {Object.keys(deployment).length > 0 && (
              <>
                {deployment.deployments && Array.isArray(deployment.deployments) && (
                  <div>
                    <h4 className="text-sm font-medium text-text-secondary mb-2">Deployments</h4>
                    <div className="space-y-2">
                      {deployment.deployments.map((d: any, i: number) => (
                        <div key={i} className="p-3 bg-bg-secondary rounded-lg flex items-center gap-3">
                          <Rocket className="w-4 h-4 text-accent-primary" />
                          <div className="flex-1">
                            <p className="text-sm font-medium text-text-primary">{d.platform || d.name}</p>
                            {d.url && (
                              <a href={d.url} target="_blank" rel="noopener noreferrer"
                                className="text-xs text-accent-primary hover:underline">{d.url}</a>
                            )}
                          </div>
                          {d.status && (
                            <span className={`text-xs px-2 py-0.5 rounded ${d.status === 'success' ? 'bg-accent-success/20 text-accent-success' : 'bg-accent-warning/20 text-accent-warning'}`}>
                              {d.status}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {deployment.manual_instructions && (
                  <div>
                    <h4 className="text-sm font-medium text-text-secondary mb-2">Manual Instructions</h4>
                    <CodeBlock content={deployment.manual_instructions} language="bash" />
                  </div>
                )}
              </>
            )}

            {/* Post-deploy verification */}
            {Object.keys(postDeploy).length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-text-secondary mb-3">Verification Results</h4>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
                  {postDeploy.checks_passed != null && (
                    <div className="p-3 bg-accent-success/10 rounded-lg text-center">
                      <p className="text-xl font-bold text-accent-success">{postDeploy.checks_passed}</p>
                      <p className="text-xs text-text-secondary">Checks Passed</p>
                    </div>
                  )}
                  {postDeploy.checks_failed != null && (
                    <div className="p-3 bg-accent-error/10 rounded-lg text-center">
                      <p className="text-xl font-bold text-accent-error">{postDeploy.checks_failed}</p>
                      <p className="text-xs text-text-secondary">Checks Failed</p>
                    </div>
                  )}
                  {postDeploy.ssl_valid != null && (
                    <div className={`p-3 rounded-lg text-center ${postDeploy.ssl_valid ? 'bg-accent-success/10' : 'bg-accent-error/10'}`}>
                      <p className={`text-xl font-bold ${postDeploy.ssl_valid ? 'text-accent-success' : 'text-accent-error'}`}>
                        {postDeploy.ssl_valid ? '✓' : '✗'}
                      </p>
                      <p className="text-xs text-text-secondary">SSL Valid</p>
                    </div>
                  )}
                  {postDeploy.visual_diff_score != null && (
                    <div className="p-3 bg-bg-secondary rounded-lg flex items-center justify-center">
                      <ScoreCircle score={postDeploy.visual_diff_score} label="Visual" color="var(--accent-purple)" />
                    </div>
                  )}
                </div>
                {postDeploy.overall_status && (
                  <div className={`flex items-center gap-2 p-3 rounded-lg ${postDeploy.overall_status === 'passed' ? 'bg-accent-success/10' : 'bg-accent-error/10'}`}>
                    {postDeploy.overall_status === 'passed' ? (
                      <CheckCircle2 className="w-4 h-4 text-accent-success" />
                    ) : (
                      <XCircle className="w-4 h-4 text-accent-error" />
                    )}
                    <span className={`text-sm font-medium ${postDeploy.overall_status === 'passed' ? 'text-accent-success' : 'text-accent-error'}`}>
                      Verification {postDeploy.overall_status}
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── Cost Breakdown ────────────────────────────── */}
        {activeTab === 'costs' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-semibold text-text-primary flex items-center gap-2">
                <DollarSign className="w-5 h-5 text-accent-warning" />
                Cost Breakdown
              </h3>
              {totalProjectCost > 0 && (
                <span className="text-lg font-bold text-text-primary">
                  Total: ${totalProjectCost.toFixed(4)}
                </span>
              )}
            </div>
            {Object.keys(costByAgent).length === 0 ? (
              <p className="text-sm text-text-secondary">No cost data available for this project.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-text-secondary border-b border-border-subtle">
                      <th className="pb-3 font-medium">Agent</th>
                      <th className="pb-3 font-medium text-right">Calls</th>
                      <th className="pb-3 font-medium text-right">Tokens</th>
                      <th className="pb-3 font-medium text-right">Cost</th>
                      <th className="pb-3 font-medium text-right">% of Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(costByAgent)
                      .sort(([, a], [, b]) => b.cost - a.cost)
                      .map(([agent, data]) => (
                        <tr key={agent} className="border-b border-border-subtle/50">
                          <td className="py-3 capitalize text-text-primary">
                            {agent.replace(/_/g, ' ')}
                          </td>
                          <td className="py-3 text-right text-text-secondary">{data.calls}</td>
                          <td className="py-3 text-right text-text-secondary">
                            {data.tokens.toLocaleString()}
                          </td>
                          <td className="py-3 text-right font-mono text-text-primary">
                            ${data.cost.toFixed(4)}
                          </td>
                          <td className="py-3 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <div className="w-16 h-1.5 bg-bg-secondary rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-accent-primary rounded-full"
                                  style={{ width: `${totalProjectCost > 0 ? (data.cost / totalProjectCost) * 100 : 0}%` }}
                                />
                              </div>
                              <span className="text-text-tertiary text-xs w-10 text-right">
                                {totalProjectCost > 0 ? ((data.cost / totalProjectCost) * 100).toFixed(1) : '0'}%
                              </span>
                            </div>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                  <tfoot>
                    <tr>
                      <td colSpan={3} className="pt-3 font-semibold text-text-primary">Total</td>
                      <td className="pt-3 text-right font-mono font-bold text-text-primary">
                        ${totalProjectCost.toFixed(4)}
                      </td>
                      <td />
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  )
}
