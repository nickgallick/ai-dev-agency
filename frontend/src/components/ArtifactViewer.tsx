import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, ProjectArtifacts } from '@/lib/api'
import { Card } from '@/components/Card'
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
} from 'lucide-react'
import { Button } from '@/components/Button'

interface ArtifactViewerProps {
  projectId: string
  projectType?: string | null
  liveUrl?: string | null
  githubRepo?: string | null
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
  // Simple markdown renderer for README display
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
          return <p key={idx} className="pl-4">• {line.slice(2)}</p>
        }
        return <p key={idx}>{line}</p>
      })}
    </div>
  )
}

export function ArtifactViewer({ projectId, projectType, liveUrl, githubRepo }: ArtifactViewerProps) {
  const [showPreview, setShowPreview] = useState(false)
  const [previewError, setPreviewError] = useState(false)

  const { data: artifacts, isLoading } = useQuery({
    queryKey: ['artifacts', projectId],
    queryFn: () => api.getProjectArtifacts(projectId),
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

  if (isLoading) {
    return (
      <Card>
        <div className="h-32 bg-background-tertiary rounded animate-pulse" />
      </Card>
    )
  }

  return (
    <Card>
      <div className="flex items-center gap-2 mb-4">
        <span className="text-accent-primary">{typeConfig.icon}</span>
        <h3 className="font-medium text-text-primary">Project Artifacts</h3>
        <span className="text-xs text-text-tertiary px-2 py-0.5 bg-background-tertiary rounded-full">
          {typeConfig.label}
        </span>
      </div>

      {/* Instructions */}
      <p className="text-sm text-text-secondary mb-4">{typeConfig.instructions}</p>

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-3 mb-6">
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

        <Button variant="ghost" size="sm" onClick={handleDownload}>
          <Download className="w-4 h-4 mr-2" />
          Download ZIP
        </Button>
      </div>

      {/* Additional Deployment URLs */}
      {artifacts?.deployment_urls && artifacts.deployment_urls.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
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
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-text-tertiary">Live Preview — {effectiveLiveUrl}</span>
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
        <div className="mb-6 p-4 bg-yellow-500/10 rounded-lg border border-yellow-500/20">
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
        <details className="group mb-4">
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
        <div className="p-4 bg-background-tertiary rounded-lg text-center">
          <p className="text-sm text-text-tertiary">
            No artifacts available yet. The project may still be building or deployment may have failed.
          </p>
        </div>
      )}
    </Card>
  )
}
