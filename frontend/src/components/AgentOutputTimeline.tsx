/**
 * AgentOutputTimeline — Live per-agent artifact display.
 *
 * Shows every pipeline agent in order. As each agent completes its work,
 * its card expands with a rich, formatted view of what it produced — not raw JSON.
 * While a project is still building, agents that haven't run yet are shown as
 * pending and the active agent pulses.
 */
import { useState } from 'react'
import { Badge } from '@/components/Badge'
import {
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Circle,
  Loader2,
  XCircle,
  ClipboardList,
  Search,
  Building2,
  Palette,
  Image,
  FileText,
  Code2,
  ShieldCheck,
  Eye,
  Accessibility,
  TestTube2,
  Rocket,
  BarChart2,
  BookOpen,
  PackageCheck,
  ClipboardCheck,
  Layers,
  Globe,
  Cpu,
  Brain,
} from 'lucide-react'

// ─── Types ────────────────────────────────────────────────────────────────────

interface AgentOutputTimelineProps {
  /** Current pipeline status string (e.g. "intake", "research", "completed") */
  projectStatus: string
  /** Agent outputs keyed by agent id, from /api/projects/:id/outputs */
  agentOutputs: Record<string, any>
}

type AgentStepStatus = 'pending' | 'active' | 'completed' | 'failed'

// ─── Pipeline definition ──────────────────────────────────────────────────────

const PIPELINE_ORDER = [
  'intake',
  'research',
  'architect',
  'design_system',
  'asset_generation',
  'content_generation',
  'pm_checkpoint_1',
  'code_generation',
  'pm_checkpoint_2',
  'code_review',
  'security',
  'seo',
  'accessibility',
  'qa',
  'deployment',
  'post_deploy_verification',
  'analytics_monitoring',
  'coding_standards',
  'delivery',
]

interface StepConfig {
  label: string
  icon: React.ReactNode
  color: string
  description: string
}

const STEP_CONFIG: Record<string, StepConfig> = {
  intake: {
    label: 'Intake',
    icon: <ClipboardList className="w-4 h-4" />,
    color: 'text-violet-400',
    description: 'Parsed project brief and structured requirements',
  },
  research: {
    label: 'Research',
    icon: <Search className="w-4 h-4" />,
    color: 'text-blue-400',
    description: 'Researched competitors, design trends, and best practices',
  },
  architect: {
    label: 'Architect',
    icon: <Building2 className="w-4 h-4" />,
    color: 'text-cyan-400',
    description: 'Designed application structure, pages, and component hierarchy',
  },
  design_system: {
    label: 'Design System',
    icon: <Palette className="w-4 h-4" />,
    color: 'text-pink-400',
    description: 'Created color palette, typography, spacing, and design tokens',
  },
  asset_generation: {
    label: 'Asset Generation',
    icon: <Image className="w-4 h-4" />,
    color: 'text-orange-400',
    description: 'Generated favicons, logos, OG images, and illustrations',
  },
  content_generation: {
    label: 'Content',
    icon: <FileText className="w-4 h-4" />,
    color: 'text-yellow-400',
    description: 'Wrote headlines, CTAs, body copy, and SEO meta content',
  },
  pm_checkpoint_1: {
    label: 'PM Checkpoint 1',
    icon: <ClipboardCheck className="w-4 h-4" />,
    color: 'text-indigo-400',
    description: 'Validated design coherence and build manifest',
  },
  code_generation: {
    label: 'Code Generation',
    icon: <Code2 className="w-4 h-4" />,
    color: 'text-green-400',
    description: 'Generated all application code and components',
  },
  pm_checkpoint_2: {
    label: 'PM Checkpoint 2',
    icon: <Layers className="w-4 h-4" />,
    color: 'text-indigo-400',
    description: 'Verified all features and pages are implemented',
  },
  code_review: {
    label: 'Code Review',
    icon: <Eye className="w-4 h-4" />,
    color: 'text-teal-400',
    description: 'Reviewed code quality, patterns, and best practices',
  },
  security: {
    label: 'Security',
    icon: <ShieldCheck className="w-4 h-4" />,
    color: 'text-red-400',
    description: 'Scanned for vulnerabilities and applied auto-fixes',
  },
  seo: {
    label: 'SEO',
    icon: <Globe className="w-4 h-4" />,
    color: 'text-emerald-400',
    description: 'Optimized meta tags, structured data, and page performance',
  },
  accessibility: {
    label: 'Accessibility',
    icon: <Accessibility className="w-4 h-4" />,
    color: 'text-sky-400',
    description: 'Checked WCAG compliance and applied accessibility fixes',
  },
  qa: {
    label: 'QA Testing',
    icon: <TestTube2 className="w-4 h-4" />,
    color: 'text-amber-400',
    description: 'Ran Playwright E2E tests and code quality checks',
  },
  deployment: {
    label: 'Deployment',
    icon: <Rocket className="w-4 h-4" />,
    color: 'text-rose-400',
    description: 'Deployed to Vercel / Railway and generated CI/CD workflows',
  },
  post_deploy_verification: {
    label: 'Verification',
    icon: <Cpu className="w-4 h-4" />,
    color: 'text-lime-400',
    description: 'Tested live deployment endpoints and SSL certificate',
  },
  analytics_monitoring: {
    label: 'Monitoring',
    icon: <BarChart2 className="w-4 h-4" />,
    color: 'text-purple-400',
    description: 'Configured Plausible, Sentry, and Lighthouse CI',
  },
  coding_standards: {
    label: 'Standards & Docs',
    icon: <BookOpen className="w-4 h-4" />,
    color: 'text-fuchsia-400',
    description: 'Generated README, API docs, ADRs, and style configs',
  },
  delivery: {
    label: 'Delivery',
    icon: <PackageCheck className="w-4 h-4" />,
    color: 'text-green-300',
    description: 'Assembled final delivery package',
  },
}

// ─── Per-agent output renderers ───────────────────────────────────────────────

function Chip({ children, color = 'bg-background-tertiary text-text-secondary' }: { children: React.ReactNode; color?: string }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${color}`}>
      {children}
    </span>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs font-semibold text-text-tertiary uppercase tracking-wider mb-1.5">{title}</p>
      {children}
    </div>
  )
}

function renderIntake(data: any) {
  const req = data?.requirements || data
  const features = req?.features || data?.suggested_features || []
  const pages = req?.pages || data?.suggested_pages || []
  const projectType = req?.project_type || data?.detected_project_type || data?.project_type
  const industry = req?.industry || data?.detected_industry
  const complexity = req?.complexity || data?.complexity_estimate

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {projectType && <Chip color="bg-violet-500/20 text-violet-300">{projectType}</Chip>}
        {industry && <Chip color="bg-blue-500/20 text-blue-300">{industry}</Chip>}
        {complexity && <Chip color="bg-gray-500/20 text-gray-300">{complexity}</Chip>}
      </div>
      {features.length > 0 && (
        <Section title={`Features (${features.length})`}>
          <div className="flex flex-wrap gap-1.5">
            {features.slice(0, 12).map((f: string, i: number) => <Chip key={i}>{f}</Chip>)}
            {features.length > 12 && <Chip>+{features.length - 12} more</Chip>}
          </div>
        </Section>
      )}
      {pages.length > 0 && (
        <Section title={`Pages (${pages.length})`}>
          <div className="flex flex-wrap gap-1.5">
            {pages.slice(0, 8).map((p: string, i: number) => <Chip key={i} color="bg-violet-500/10 text-violet-300">{p}</Chip>)}
          </div>
        </Section>
      )}
    </div>
  )
}

function renderResearch(data: any) {
  const competitors = data?.competitors || data?.competitor_sites || []
  const trends = data?.design_trends || data?.trends || []
  const insights = data?.insights || data?.key_insights || []

  return (
    <div className="space-y-3">
      {competitors.length > 0 && (
        <Section title={`Competitors Analyzed (${competitors.length})`}>
          <div className="space-y-1">
            {competitors.slice(0, 5).map((c: any, i: number) => (
              <div key={i} className="text-xs text-text-secondary">
                {typeof c === 'string' ? (
                  <span className="font-mono">{c}</span>
                ) : (
                  <span>{c.name || c.url || JSON.stringify(c)}</span>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}
      {trends.length > 0 && (
        <Section title="Design Trends Found">
          <div className="flex flex-wrap gap-1.5">
            {trends.slice(0, 6).map((t: string, i: number) => <Chip key={i} color="bg-blue-500/10 text-blue-300">{t}</Chip>)}
          </div>
        </Section>
      )}
      {insights.length > 0 && (
        <Section title="Key Insights">
          <ul className="space-y-1">
            {insights.slice(0, 4).map((ins: string, i: number) => (
              <li key={i} className="text-xs text-text-secondary flex gap-1.5">
                <span className="text-blue-400 flex-shrink-0">•</span>{ins}
              </li>
            ))}
          </ul>
        </Section>
      )}
    </div>
  )
}

function renderArchitect(data: any) {
  const techStack = data?.tech_stack || {}
  const pages = data?.pages || data?.page_structure || []
  const components = data?.components || data?.component_hierarchy || []

  return (
    <div className="space-y-3">
      {Object.keys(techStack).length > 0 && (
        <Section title="Tech Stack">
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(techStack).flatMap(([, v]: [string, any]) =>
              (Array.isArray(v) ? v : [v]).map((item: string, i: number) => (
                <Chip key={`${item}-${i}`} color="bg-cyan-500/10 text-cyan-300">{item}</Chip>
              ))
            ).slice(0, 12)}
          </div>
        </Section>
      )}
      {pages.length > 0 && (
        <Section title={`Pages (${pages.length})`}>
          <div className="flex flex-wrap gap-1.5">
            {pages.slice(0, 8).map((p: any, i: number) => (
              <Chip key={i}>{typeof p === 'string' ? p : (p.name || p.path || JSON.stringify(p))}</Chip>
            ))}
          </div>
        </Section>
      )}
      {components.length > 0 && (
        <Section title={`Components (${components.length})`}>
          <div className="flex flex-wrap gap-1.5">
            {components.slice(0, 10).map((c: any, i: number) => (
              <Chip key={i} color="bg-cyan-500/10 text-cyan-300">
                {typeof c === 'string' ? c : (c.name || JSON.stringify(c))}
              </Chip>
            ))}
            {components.length > 10 && <Chip>+{components.length - 10} more</Chip>}
          </div>
        </Section>
      )}
    </div>
  )
}

function renderDesignSystem(data: any) {
  const colors = data?.colors || data?.color_palette || {}
  const typography = data?.typography || {}
  const tokens = data?.design_tokens || {}

  const colorEntries = Object.entries(colors).slice(0, 8)

  return (
    <div className="space-y-3">
      {colorEntries.length > 0 && (
        <Section title="Color Palette">
          <div className="flex flex-wrap gap-2">
            {colorEntries.map(([name, value]: [string, any]) => {
              const hex = typeof value === 'string' ? value : value?.hex || value?.value || '#888'
              return (
                <div key={name} className="flex items-center gap-1.5">
                  <div
                    className="w-5 h-5 rounded border border-white/10 flex-shrink-0"
                    style={{ backgroundColor: hex }}
                  />
                  <span className="text-xs text-text-secondary">{name}</span>
                </div>
              )
            })}
          </div>
        </Section>
      )}
      {Object.keys(typography).length > 0 && (
        <Section title="Typography">
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(typography).slice(0, 4).map(([k, v]: [string, any]) => (
              <Chip key={k} color="bg-pink-500/10 text-pink-300">{k}: {typeof v === 'string' ? v : JSON.stringify(v)}</Chip>
            ))}
          </div>
        </Section>
      )}
      {Object.keys(tokens).length > 0 && (
        <Section title={`Design Tokens (${Object.keys(tokens).length})`}>
          <div className="flex flex-wrap gap-1.5">
            {Object.keys(tokens).slice(0, 6).map((k) => <Chip key={k}>{k}</Chip>)}
          </div>
        </Section>
      )}
    </div>
  )
}

function renderAssets(data: any) {
  const assets = data?.assets || data?.generated_assets || []
  const favicon = data?.favicon_url || data?.favicon
  const ogImage = data?.og_image_url || data?.og_image

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2 items-center">
        {favicon && (
          <div className="flex items-center gap-1.5 p-2 bg-background-tertiary rounded">
            <img src={favicon} alt="favicon" className="w-6 h-6" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }} />
            <span className="text-xs text-text-secondary">Favicon</span>
          </div>
        )}
        {ogImage && (
          <div className="flex items-center gap-1.5 p-2 bg-background-tertiary rounded">
            <img src={ogImage} alt="og" className="w-16 h-8 object-cover rounded" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }} />
            <span className="text-xs text-text-secondary">OG Image</span>
          </div>
        )}
      </div>
      {assets.length > 0 && (
        <Section title={`Generated Assets (${assets.length})`}>
          <div className="flex flex-wrap gap-1.5">
            {assets.slice(0, 8).map((a: any, i: number) => (
              <Chip key={i} color="bg-orange-500/10 text-orange-300">
                {typeof a === 'string' ? a.split('/').pop() : (a.name || a.type || JSON.stringify(a))}
              </Chip>
            ))}
          </div>
        </Section>
      )}
      {assets.length === 0 && !favicon && !ogImage && (
        <p className="text-xs text-text-tertiary">Assets generated and saved to project directory</p>
      )}
    </div>
  )
}

function renderContent(data: any) {
  const pages = data?.pages || data?.content_by_page || {}
  const headlines = data?.headlines || []
  const ctas = data?.ctas || data?.call_to_actions || []

  return (
    <div className="space-y-3">
      {Object.keys(pages).length > 0 && (
        <Section title={`Pages with Content (${Object.keys(pages).length})`}>
          <div className="space-y-2">
            {Object.entries(pages).slice(0, 4).map(([page, content]: [string, any]) => (
              <div key={page} className="p-2 bg-background-tertiary rounded">
                <p className="text-xs font-medium text-text-primary capitalize">{page}</p>
                {typeof content === 'object' && content?.headline && (
                  <p className="text-xs text-text-secondary mt-0.5 italic">"{content.headline}"</p>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}
      {headlines.length > 0 && (
        <Section title="Headlines">
          {headlines.slice(0, 3).map((h: string, i: number) => (
            <p key={i} className="text-xs text-text-secondary italic">"{h}"</p>
          ))}
        </Section>
      )}
      {ctas.length > 0 && (
        <Section title="CTAs">
          <div className="flex flex-wrap gap-1.5">
            {ctas.slice(0, 5).map((c: string, i: number) => (
              <Chip key={i} color="bg-yellow-500/10 text-yellow-300">{c}</Chip>
            ))}
          </div>
        </Section>
      )}
    </div>
  )
}

function renderCheckpoint(data: any, label: string) {
  const passed = data?.passed ?? data?.coherent ?? data?.complete
  const issues = data?.issues || []
  const manifest = data?.build_manifest || {}
  const score = data?.score ?? data?.quality_score

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        {passed ? (
          <CheckCircle2 className="w-4 h-4 text-green-400" />
        ) : (
          <XCircle className="w-4 h-4 text-red-400" />
        )}
        <span className="text-sm font-medium" style={{ color: passed ? '#4ade80' : '#f87171' }}>
          {passed ? 'Passed' : 'Issues Found'}
        </span>
        {score !== undefined && (
          <Chip color="bg-indigo-500/20 text-indigo-300">Score: {Math.round(score * 100)}%</Chip>
        )}
      </div>
      {Object.keys(manifest).length > 0 && (
        <Section title="Build Manifest">
          <div className="flex flex-wrap gap-2">
            {manifest.pages?.length > 0 && <Chip>{manifest.pages.length} pages</Chip>}
            {manifest.components?.length > 0 && <Chip>{manifest.components.length} components</Chip>}
            {manifest.api_endpoints?.length > 0 && <Chip>{manifest.api_endpoints.length} endpoints</Chip>}
          </div>
        </Section>
      )}
      {issues.length > 0 && (
        <Section title={`Issues (${issues.length})`}>
          <div className="space-y-1">
            {issues.slice(0, 4).map((issue: any, i: number) => (
              <div key={i} className={`flex items-start gap-1.5 text-xs p-1.5 rounded ${
                issue.severity === 'critical' ? 'bg-red-500/10 text-red-300' :
                issue.severity === 'warning' ? 'bg-yellow-500/10 text-yellow-300' :
                'bg-blue-500/10 text-blue-300'
              }`}>
                <span className="flex-shrink-0 font-medium">{issue.severity || 'info'}</span>
                <span>{issue.message || JSON.stringify(issue)}</span>
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  )
}

function renderCodeGen(data: any) {
  const files = data?.files || data?.generated_files || []
  const components = data?.components || []
  const linesOfCode = data?.lines_of_code || data?.total_lines
  const fileCount = data?.file_count ?? (Array.isArray(files) ? files.length : 0)

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {fileCount > 0 && <Chip color="bg-green-500/20 text-green-300">{fileCount} files generated</Chip>}
        {linesOfCode > 0 && <Chip color="bg-green-500/10 text-green-400">{linesOfCode.toLocaleString()} lines</Chip>}
        {components.length > 0 && <Chip>{components.length} components</Chip>}
      </div>
      {files.length > 0 && (
        <Section title="Generated Files">
          <div className="space-y-0.5 max-h-40 overflow-y-auto font-mono">
            {files.slice(0, 20).map((f: any, i: number) => (
              <p key={i} className="text-xs text-text-secondary">
                {typeof f === 'string' ? f : (f.path || f.name || JSON.stringify(f))}
              </p>
            ))}
            {files.length > 20 && <p className="text-xs text-text-tertiary">...and {files.length - 20} more</p>}
          </div>
        </Section>
      )}
    </div>
  )
}

function renderCodeReview(data: any) {
  const report = data?.report || data
  const total = report?.total_issues ?? 0
  const critical = report?.issues_by_severity?.critical ?? 0
  const high = report?.issues_by_severity?.high ?? 0
  const autoFixed = report?.auto_fixes_applied?.length ?? 0
  const passed = report?.pass_threshold ?? (total === 0)

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        <Chip color={passed ? 'bg-green-500/20 text-green-300' : 'bg-red-500/20 text-red-300'}>
          {passed ? 'Passed' : 'Needs Attention'}
        </Chip>
        {total > 0 && <Chip>{total} issues</Chip>}
        {critical > 0 && <Chip color="bg-red-500/20 text-red-300">{critical} critical</Chip>}
        {high > 0 && <Chip color="bg-orange-500/20 text-orange-300">{high} high</Chip>}
        {autoFixed > 0 && <Chip color="bg-green-500/20 text-green-300">{autoFixed} auto-fixed</Chip>}
      </div>
      {report?.summary && (
        <p className="text-xs text-text-secondary">{report.summary}</p>
      )}
    </div>
  )
}

function renderSecurity(data: any) {
  const report = data?.report || data
  const findings = report?.findings || data?.vulnerabilities || []
  const autoFixed = report?.auto_fixed ?? 0
  const critical = findings.filter((f: any) => f.severity?.toLowerCase() === 'critical').length
  const high = findings.filter((f: any) => f.severity?.toLowerCase() === 'high').length

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {findings.length === 0 ? (
          <Chip color="bg-green-500/20 text-green-300">No vulnerabilities found</Chip>
        ) : (
          <>
            <Chip color="bg-red-500/20 text-red-300">{findings.length} findings</Chip>
            {critical > 0 && <Chip color="bg-red-600/20 text-red-200">{critical} critical</Chip>}
            {high > 0 && <Chip color="bg-orange-500/20 text-orange-300">{high} high</Chip>}
            {autoFixed > 0 && <Chip color="bg-green-500/20 text-green-300">{autoFixed} auto-fixed</Chip>}
          </>
        )}
      </div>
      {findings.length > 0 && (
        <Section title="Top Findings">
          <div className="space-y-1">
            {findings.slice(0, 4).map((f: any, i: number) => (
              <div key={i} className="text-xs flex gap-2 p-1.5 bg-background-tertiary rounded">
                <Chip color={f.severity === 'critical' ? 'bg-red-500/30 text-red-300' : 'bg-orange-500/20 text-orange-300'}>
                  {f.severity}
                </Chip>
                <span className="text-text-secondary truncate">{f.message || f.rule_id}</span>
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  )
}

function renderSEO(data: any) {
  const report = data?.report || data
  const score = report?.score ?? report?.seo_score
  const metaTags = report?.meta_tags || report?.generated_meta || {}
  const issues = report?.issues || []

  return (
    <div className="space-y-3">
      {score !== undefined && (
        <div className="flex items-center gap-2">
          <div className={`text-2xl font-bold ${score >= 80 ? 'text-green-400' : score >= 60 ? 'text-yellow-400' : 'text-red-400'}`}>
            {score}
          </div>
          <span className="text-xs text-text-secondary">/ 100 SEO Score</span>
        </div>
      )}
      {Object.keys(metaTags).length > 0 && (
        <Section title="Meta Tags">
          <div className="space-y-1">
            {Object.entries(metaTags).slice(0, 4).map(([k, v]: [string, any]) => (
              <div key={k} className="text-xs flex gap-2">
                <span className="text-text-tertiary w-24 flex-shrink-0">{k}:</span>
                <span className="text-text-secondary truncate">{typeof v === 'string' ? v : JSON.stringify(v)}</span>
              </div>
            ))}
          </div>
        </Section>
      )}
      {issues.length > 0 && (
        <Section title="Issues">
          <div className="flex flex-wrap gap-1.5">
            {issues.slice(0, 4).map((iss: string, i: number) => (
              <Chip key={i} color="bg-yellow-500/10 text-yellow-300">{iss}</Chip>
            ))}
          </div>
        </Section>
      )}
    </div>
  )
}

function renderAccessibility(data: any) {
  const report = data?.report || data
  const score = report?.score ?? report?.compliance_score
  const violations = report?.violations || []
  const passes = report?.passes ?? 0
  const wcagLevel = report?.wcag_level || report?.compliance_level

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2 items-center">
        {score !== undefined && (
          <div className={`text-2xl font-bold ${score >= 80 ? 'text-green-400' : score >= 60 ? 'text-yellow-400' : 'text-red-400'}`}>
            {score}
          </div>
        )}
        {wcagLevel && <Chip color="bg-sky-500/20 text-sky-300">{wcagLevel}</Chip>}
        {passes > 0 && <Chip color="bg-green-500/20 text-green-300">{passes} passed</Chip>}
        {violations.length > 0 && <Chip color="bg-red-500/20 text-red-300">{violations.length} violations</Chip>}
      </div>
      {violations.length > 0 && (
        <Section title="Violations">
          <div className="space-y-1">
            {violations.slice(0, 4).map((v: any, i: number) => (
              <p key={i} className="text-xs text-text-secondary">
                {typeof v === 'string' ? v : (v.description || v.id || JSON.stringify(v))}
              </p>
            ))}
          </div>
        </Section>
      )}
    </div>
  )
}

function renderQA(data: any) {
  const report = data?.report || data
  const total = report?.total_tests ?? 0
  const passed = report?.passed ?? 0
  const failed = report?.failed ?? 0
  const score = report?.quality_score

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-4 gap-2">
        {score !== undefined && (
          <div className="bg-background-tertiary rounded p-2 text-center">
            <div className={`text-lg font-bold ${score >= 80 ? 'text-green-400' : score >= 60 ? 'text-yellow-400' : 'text-red-400'}`}>
              {score}
            </div>
            <div className="text-xs text-text-tertiary">Score</div>
          </div>
        )}
        <div className="bg-background-tertiary rounded p-2 text-center">
          <div className="text-lg font-bold text-text-primary">{total}</div>
          <div className="text-xs text-text-tertiary">Tests</div>
        </div>
        <div className="bg-green-500/10 rounded p-2 text-center">
          <div className="text-lg font-bold text-green-400">{passed}</div>
          <div className="text-xs text-text-tertiary">Passed</div>
        </div>
        <div className={`${failed > 0 ? 'bg-red-500/10' : 'bg-background-tertiary'} rounded p-2 text-center`}>
          <div className={`text-lg font-bold ${failed > 0 ? 'text-red-400' : 'text-text-primary'}`}>{failed}</div>
          <div className="text-xs text-text-tertiary">Failed</div>
        </div>
      </div>
      {report?.test_results?.length > 0 && (
        <Section title="Test Results">
          <div className="space-y-0.5 max-h-32 overflow-y-auto">
            {report.test_results.slice(0, 8).map((t: any, i: number) => (
              <div key={i} className="flex items-center gap-2 text-xs">
                {t.status === 'passed'
                  ? <CheckCircle2 className="w-3 h-3 text-green-400 flex-shrink-0" />
                  : <XCircle className="w-3 h-3 text-red-400 flex-shrink-0" />
                }
                <span className="text-text-secondary truncate">{t.name}</span>
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  )
}

function renderDeployment(data: any) {
  const report = data?.report || data
  const deployments = report?.deployments || (Array.isArray(data?.deployments) ? data.deployments : [])

  return (
    <div className="space-y-2">
      {deployments.length === 0 && (
        <p className="text-xs text-text-tertiary">No deployment data available</p>
      )}
      {deployments.map((dep: any, i: number) => (
        <div key={i} className="flex items-center justify-between p-2 bg-background-tertiary rounded">
          <div className="flex items-center gap-2">
            <Chip color={dep.status === 'deployed' ? 'bg-green-500/20 text-green-300' : 'bg-yellow-500/20 text-yellow-300'}>
              {dep.platform}
            </Chip>
            <span className="text-xs text-text-tertiary">{dep.status}</span>
          </div>
          {dep.url && (
            <a
              href={dep.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-accent-primary hover:underline flex items-center gap-1"
            >
              Open ↗
            </a>
          )}
        </div>
      ))}
    </div>
  )
}

function renderMonitoring(data: any) {
  const report = data?.report || data
  const services = report?.services || data?.services || []
  const configured = services.filter((s: any) => s.configured).length

  return (
    <div className="space-y-3">
      {services.length > 0 && (
        <>
          <div className="flex items-center gap-2">
            <Chip color="bg-purple-500/20 text-purple-300">{configured} / {services.length} configured</Chip>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {services.map((svc: any, i: number) => (
              <div key={i} className={`flex items-center gap-2 p-2 rounded text-xs ${
                svc.configured ? 'bg-green-500/10' : 'bg-background-tertiary'
              }`}>
                {svc.configured
                  ? <CheckCircle2 className="w-3 h-3 text-green-400 flex-shrink-0" />
                  : <Circle className="w-3 h-3 text-text-tertiary flex-shrink-0" />
                }
                <span className="text-text-secondary">{svc.name}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

function renderCodingStandards(data: any) {
  const report = data?.report || data
  const docs = report?.documents || data?.documents || []
  const configs = report?.style_configs || data?.style_configs || []
  const adrs = report?.adrs_generated ?? 0

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {docs.filter((d: any) => d.generated).length > 0 && (
          <Chip color="bg-fuchsia-500/20 text-fuchsia-300">
            {docs.filter((d: any) => d.generated).length} documents
          </Chip>
        )}
        {adrs > 0 && <Chip color="bg-purple-500/20 text-purple-300">{adrs} ADRs</Chip>}
        {configs.length > 0 && <Chip>{configs.length} style configs</Chip>}
      </div>
      {docs.length > 0 && (
        <Section title="Generated Docs">
          <div className="flex flex-wrap gap-1.5">
            {docs.filter((d: any) => d.generated).map((doc: any, i: number) => (
              <Chip key={i} color="bg-fuchsia-500/10 text-fuchsia-300">{doc.name || doc.type}</Chip>
            ))}
          </div>
        </Section>
      )}
    </div>
  )
}

function renderDelivery(data: any) {
  const liveUrl = data?.live_url
  const githubRepo = data?.github_repo
  const files = data?.delivery_files || data?.files || []

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        <Chip color="bg-green-500/20 text-green-300">Build Complete</Chip>
        {files.length > 0 && <Chip>{files.length} deliverables</Chip>}
      </div>
      {(liveUrl || githubRepo) && (
        <div className="flex flex-wrap gap-2">
          {liveUrl && (
            <a href={liveUrl} target="_blank" rel="noopener noreferrer"
              className="text-xs text-accent-primary hover:underline">
              Live Site ↗
            </a>
          )}
          {githubRepo && (
            <a href={githubRepo} target="_blank" rel="noopener noreferrer"
              className="text-xs text-accent-primary hover:underline">
              GitHub ↗
            </a>
          )}
        </div>
      )}
    </div>
  )
}

function renderVerification(data: any) {
  const report = data?.report || data
  const overall = report?.overall_status || (report?.checks_passed > 0 ? 'passed' : 'unknown')
  const passed = report?.checks_passed ?? 0
  const failed = report?.checks_failed ?? 0
  const ssl = report?.ssl_valid

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2 items-center">
        <Chip color={overall === 'passed' ? 'bg-green-500/20 text-green-300' : overall === 'partial' ? 'bg-yellow-500/20 text-yellow-300' : 'bg-red-500/20 text-red-300'}>
          {overall}
        </Chip>
        {passed > 0 && <Chip color="bg-green-500/10 text-green-400">{passed} passed</Chip>}
        {failed > 0 && <Chip color="bg-red-500/10 text-red-400">{failed} failed</Chip>}
        {ssl !== undefined && <Chip color={ssl ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}>{ssl ? '🔒 SSL OK' : '🔓 SSL Issue'}</Chip>}
      </div>
    </div>
  )
}

// ─── Agent Reasoning Section ─────────────────────────────────────────────────

function ReasoningSection({ reasoning }: { reasoning: any }) {
  const [expanded, setExpanded] = useState(false)
  if (!reasoning || (!reasoning.goal && !reasoning.key_decisions?.length)) return null

  return (
    <div className="mt-3 pt-3 border-t border-white/5">
      <button
        className="flex items-center gap-1.5 text-xs text-purple-400 hover:text-purple-300 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <Brain className="w-3.5 h-3.5" />
        <span className="font-medium">Agent Reasoning</span>
        <ChevronDown className={`w-3 h-3 transition-transform ${expanded ? '' : '-rotate-90'}`} />
      </button>
      {expanded && (
        <div className="mt-2 space-y-2 text-xs">
          {reasoning.goal && (
            <div>
              <p className="text-[10px] font-semibold text-text-tertiary uppercase tracking-wider mb-0.5">Goal</p>
              <p className="text-text-secondary">{reasoning.goal}</p>
            </div>
          )}
          {reasoning.approach && (
            <div>
              <p className="text-[10px] font-semibold text-text-tertiary uppercase tracking-wider mb-0.5">Approach</p>
              <p className="text-text-secondary">{reasoning.approach}</p>
            </div>
          )}
          {reasoning.key_decisions?.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold text-text-tertiary uppercase tracking-wider mb-1">Key Decisions</p>
              <div className="space-y-1">
                {reasoning.key_decisions.map((d: any, i: number) => (
                  <div key={i} className="flex gap-1.5 text-xs">
                    <span className="text-purple-400 flex-shrink-0">-</span>
                    <span>
                      <span className="text-text-primary font-medium">{d.decision}</span>
                      {d.reason && <span className="text-text-tertiary"> — {d.reason}</span>}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {reasoning.confidence > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-semibold text-text-tertiary uppercase tracking-wider">Confidence</span>
              <div className="flex-1 h-1.5 rounded-full bg-background-tertiary overflow-hidden max-w-[120px]">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-purple-500 to-indigo-500"
                  style={{ width: `${reasoning.confidence * 100}%` }}
                />
              </div>
              <span className="text-text-tertiary">{Math.round(reasoning.confidence * 100)}%</span>
            </div>
          )}
          {reasoning.constraints?.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold text-text-tertiary uppercase tracking-wider mb-0.5">Constraints</p>
              {reasoning.constraints.map((c: string, i: number) => (
                <p key={i} className="text-text-tertiary pl-2 border-l-2 border-yellow-500/30 text-[11px]">{c}</p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Agent output dispatcher ──────────────────────────────────────────────────

function renderAgentOutput(agentId: string, data: any): React.ReactNode {
  if (!data) return <p className="text-xs text-text-tertiary">No output data available</p>

  switch (agentId) {
    case 'intake': return renderIntake(data)
    case 'research': return renderResearch(data)
    case 'architect': return renderArchitect(data)
    case 'design_system': return renderDesignSystem(data)
    case 'asset_generation': return renderAssets(data)
    case 'content_generation': return renderContent(data)
    case 'pm_checkpoint_1': return renderCheckpoint(data, 'Checkpoint 1')
    case 'pm_checkpoint_2': return renderCheckpoint(data, 'Checkpoint 2')
    case 'code_generation': return renderCodeGen(data)
    case 'code_review': return renderCodeReview(data)
    case 'security': return renderSecurity(data)
    case 'seo': return renderSEO(data)
    case 'accessibility': return renderAccessibility(data)
    case 'qa': return renderQA(data)
    case 'deployment': return renderDeployment(data)
    case 'post_deploy_verification': return renderVerification(data)
    case 'analytics_monitoring': return renderMonitoring(data)
    case 'coding_standards': return renderCodingStandards(data)
    case 'delivery': return renderDelivery(data)
    default:
      // Generic fallback — show top-level keys as chips
      return (
        <div className="flex flex-wrap gap-1.5">
          {Object.keys(data).slice(0, 8).map((k) => (
            <Chip key={k}>{k}</Chip>
          ))}
        </div>
      )
  }
}

// ─── Step status helpers ──────────────────────────────────────────────────────

function getStepStatus(agentId: string, projectStatus: string, agentOutputs: Record<string, any>): AgentStepStatus {
  if (projectStatus === 'failed') {
    // If this agent has output it completed before failure
    return agentOutputs[agentId] ? 'completed' : 'failed'
  }
  if (agentOutputs[agentId]) return 'completed'
  if (projectStatus === 'completed') return 'completed'

  const currentIdx = PIPELINE_ORDER.indexOf(projectStatus)
  const agentIdx = PIPELINE_ORDER.indexOf(agentId)

  if (currentIdx === -1) return 'pending'
  if (agentIdx < currentIdx) return 'completed'
  if (agentIdx === currentIdx) return 'active'
  return 'pending'
}

function StatusIcon({ status }: { status: AgentStepStatus }) {
  switch (status) {
    case 'completed': return <CheckCircle2 className="w-4 h-4 text-green-400 flex-shrink-0" />
    case 'active': return <Loader2 className="w-4 h-4 text-accent-primary flex-shrink-0 animate-spin" />
    case 'failed': return <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
    default: return <Circle className="w-4 h-4 text-text-tertiary flex-shrink-0" />
  }
}

// ─── Main component ───────────────────────────────────────────────────────────

export function AgentOutputTimeline({ projectStatus, agentOutputs }: AgentOutputTimelineProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})

  const toggle = (id: string) => setExpanded(prev => ({ ...prev, [id]: !prev[id] }))

  const completedCount = PIPELINE_ORDER.filter(id => agentOutputs[id]).length

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium text-text-primary">Agent Outputs</h3>
        <span className="text-xs text-text-tertiary">{completedCount} / {PIPELINE_ORDER.length} completed</span>
      </div>

      <div className="space-y-1">
        {PIPELINE_ORDER.map((agentId, index) => {
          const config = STEP_CONFIG[agentId]
          const status = getStepStatus(agentId, projectStatus, agentOutputs)
          const hasOutput = !!agentOutputs[agentId]
          const isExpanded = expanded[agentId]
          const isClickable = hasOutput || status === 'active'

          return (
            <div key={agentId} className="relative">
              {/* Vertical connector line */}
              {index < PIPELINE_ORDER.length - 1 && (
                <div
                  className="absolute left-[11px] top-8 w-0.5 h-full -z-10"
                  style={{
                    background: status === 'completed' ? 'rgba(74,222,128,0.3)' : 'rgba(255,255,255,0.06)'
                  }}
                />
              )}

              {/* Step row */}
              <button
                className={`w-full flex items-start gap-3 p-2.5 rounded-lg text-left transition-colors ${
                  isClickable
                    ? 'hover:bg-white/5 cursor-pointer'
                    : 'cursor-default opacity-50'
                } ${isExpanded ? 'bg-white/5' : ''}`}
                onClick={() => isClickable && toggle(agentId)}
                disabled={!isClickable}
              >
                <div className="mt-0.5">
                  <StatusIcon status={status} />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`${config?.color || 'text-text-secondary'}`}>
                      {config?.icon}
                    </span>
                    <span className={`text-sm font-medium ${
                      status === 'completed' ? 'text-text-primary' :
                      status === 'active' ? 'text-accent-primary' :
                      'text-text-tertiary'
                    }`}>
                      {config?.label || agentId}
                    </span>
                    {status === 'active' && (
                      <Badge variant="running" pulse>Running</Badge>
                    )}
                  </div>
                  {!isExpanded && (
                    <p className="text-xs text-text-tertiary mt-0.5">{config?.description}</p>
                  )}
                </div>

                {isClickable && (
                  <div className="mt-0.5 text-text-tertiary flex-shrink-0">
                    {isExpanded
                      ? <ChevronDown className="w-4 h-4" />
                      : <ChevronRight className="w-4 h-4" />
                    }
                  </div>
                )}
              </button>

              {/* Expanded output */}
              {isExpanded && (
                <div className="ml-10 mb-2 p-3 bg-white/3 rounded-lg border border-white/5">
                  {hasOutput
                    ? (
                      <>
                        {renderAgentOutput(agentId, agentOutputs[agentId])}
                        <ReasoningSection reasoning={agentOutputs[agentId]?._reasoning} />
                      </>
                    )
                    : (
                      <div className="flex items-center gap-2 text-xs text-accent-primary">
                        <Loader2 className="w-3 h-3 animate-spin" />
                        Agent is running...
                      </div>
                    )
                  }
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
