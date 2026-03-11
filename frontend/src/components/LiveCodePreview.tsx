/**
 * LiveCodePreview — Renders generated code as a working app in the browser
 * using CodeSandbox's Sandpack. Supports editing and live-reloading.
 *
 * Feature #3: Live Code Preview with Sandpack
 *
 * Code-split via React.lazy() so Sandpack only loads when the user
 * opens the Live Preview tab.
 */
import { useMemo, useState } from 'react'
import {
  SandpackProvider,
  SandpackLayout,
  SandpackCodeEditor,
  SandpackPreview,
  SandpackFileExplorer,
} from '@codesandbox/sandpack-react'
import { AlertTriangle, Maximize2, Minimize2, Monitor, Smartphone, Tablet } from 'lucide-react'

interface CodeFile {
  path: string
  content?: string
  code?: string
  source?: string
  name?: string
  file?: string
}

interface LiveCodePreviewProps {
  files: CodeFile[]
  projectType?: string
  fileContents?: Record<string, string>
}

// Map file extensions to Sandpack-compatible templates
function detectTemplate(files: CodeFile[], projectType?: string): string {
  const paths = files.map(f => f.path || f.name || f.file || '').join(' ')

  if (paths.includes('next.config') || paths.includes('app/page.tsx') || paths.includes('app/layout.tsx')) {
    return 'nextjs'
  }
  if (paths.includes('vite.config') || paths.includes('index.html')) {
    return 'vite-react-ts'
  }
  if (paths.includes('.vue') || paths.includes('vue.config')) {
    return 'vue'
  }
  if (paths.includes('angular.json')) {
    return 'angular'
  }

  // Default based on project type
  if (projectType?.includes('web') || projectType?.includes('pwa') || projectType?.includes('saas')) {
    return 'vite-react-ts'
  }
  return 'static'
}

// Normalize file path for Sandpack (must start with /)
function normalizePath(path: string): string {
  let p = path.trim()
  if (!p.startsWith('/')) p = '/' + p
  return p
}

// Get file content from various possible structures
function getContent(file: CodeFile): string {
  return file.content || file.code || file.source || ''
}

// Build Sandpack files from code generation output
function buildSandpackFiles(
  files: CodeFile[],
  fileContents?: Record<string, string>
): Record<string, string> {
  const result: Record<string, string> = {}

  for (const file of files) {
    const path = file.path || file.name || file.file || ''
    if (!path) continue

    const normalPath = normalizePath(path)
    let content = getContent(file)

    // Try fileContents map as fallback
    if (!content && fileContents) {
      content = fileContents[path] || fileContents[normalPath] || ''
    }

    if (content) {
      result[normalPath] = content
    }
  }

  return result
}

// Determine which file should be the entry/active file
function findEntryFile(files: Record<string, string>): string {
  const priorities = [
    '/app/page.tsx',
    '/app/page.jsx',
    '/src/App.tsx',
    '/src/App.jsx',
    '/src/app.tsx',
    '/src/app.jsx',
    '/App.tsx',
    '/App.jsx',
    '/src/main.tsx',
    '/src/main.jsx',
    '/src/index.tsx',
    '/src/index.jsx',
    '/index.tsx',
    '/index.jsx',
    '/index.html',
    '/pages/index.tsx',
    '/pages/index.jsx',
  ]

  for (const p of priorities) {
    if (files[p]) return p
  }

  // Just pick the first .tsx/.jsx/.html file
  const keys = Object.keys(files)
  return keys.find(k => k.endsWith('.tsx') || k.endsWith('.jsx')) ||
    keys.find(k => k.endsWith('.html')) ||
    keys[0] || '/index.tsx'
}

// Check if the project type is previewable
function isPreviewable(projectType?: string): boolean {
  if (!projectType) return true
  const nonPreviewable = ['cli_tool', 'python_api', 'desktop_app', 'mobile_native_ios']
  return !nonPreviewable.includes(projectType)
}

type ViewportSize = 'desktop' | 'tablet' | 'mobile'

export default function LiveCodePreview({ files, projectType, fileContents }: LiveCodePreviewProps) {
  const [viewport, setViewport] = useState<ViewportSize>('desktop')
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [showEditor, setShowEditor] = useState(true)

  const sandpackFiles = useMemo(() => buildSandpackFiles(files, fileContents), [files, fileContents])
  const template = useMemo(() => detectTemplate(files, projectType), [files, projectType])
  const entryFile = useMemo(() => findEntryFile(sandpackFiles), [sandpackFiles])
  const fileCount = Object.keys(sandpackFiles).length

  // Not previewable for non-web project types
  if (!isPreviewable(projectType)) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <AlertTriangle className="w-8 h-8 mb-3" style={{ color: 'var(--text-tertiary)' }} />
        <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
          Live preview not available for {projectType?.replace(/_/g, ' ')} projects
        </p>
        <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
          Download the project to run it locally
        </p>
      </div>
    )
  }

  // No files to preview
  if (fileCount === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <AlertTriangle className="w-8 h-8 mb-3" style={{ color: 'var(--text-tertiary)' }} />
        <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
          No code files available for preview
        </p>
        <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
          The code generation agent hasn't produced output yet
        </p>
      </div>
    )
  }

  const viewportWidths: Record<ViewportSize, string> = {
    desktop: '100%',
    tablet: '768px',
    mobile: '375px',
  }

  const containerClass = isFullscreen
    ? 'fixed inset-0 z-[250] flex flex-col'
    : 'flex flex-col rounded-lg overflow-hidden border'

  return (
    <div
      className={containerClass}
      style={{
        background: 'var(--background-primary)',
        borderColor: isFullscreen ? undefined : 'var(--border-subtle)',
        height: isFullscreen ? '100vh' : '600px',
      }}
    >
      {/* Toolbar */}
      <div
        className="flex items-center justify-between px-3 py-2 border-b"
        style={{ borderColor: 'var(--border-subtle)', background: 'var(--background-secondary)' }}
      >
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
            Live Preview
          </span>
          <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: 'var(--background-tertiary)', color: 'var(--text-tertiary)' }}>
            {fileCount} files
          </span>
          <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: 'rgba(74,222,128,0.15)', color: '#4ade80' }}>
            {template}
          </span>
        </div>

        <div className="flex items-center gap-1">
          {/* Viewport switcher */}
          <button
            onClick={() => setViewport('desktop')}
            className={`p-1.5 rounded transition-colors ${viewport === 'desktop' ? 'bg-accent-primary/20 text-accent-primary' : 'text-text-tertiary hover:text-text-secondary'}`}
            title="Desktop view"
          >
            <Monitor className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setViewport('tablet')}
            className={`p-1.5 rounded transition-colors ${viewport === 'tablet' ? 'bg-accent-primary/20 text-accent-primary' : 'text-text-tertiary hover:text-text-secondary'}`}
            title="Tablet view"
          >
            <Tablet className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setViewport('mobile')}
            className={`p-1.5 rounded transition-colors ${viewport === 'mobile' ? 'bg-accent-primary/20 text-accent-primary' : 'text-text-tertiary hover:text-text-secondary'}`}
            title="Mobile view"
          >
            <Smartphone className="w-3.5 h-3.5" />
          </button>

          <div className="w-px h-4 mx-1" style={{ background: 'var(--border-subtle)' }} />

          {/* Toggle editor */}
          <button
            onClick={() => setShowEditor(!showEditor)}
            className="px-2 py-1 rounded text-xs transition-colors"
            style={{
              background: showEditor ? 'var(--accent-primary-bg, rgba(59,130,246,0.15))' : 'transparent',
              color: showEditor ? 'var(--accent-primary)' : 'var(--text-tertiary)',
            }}
          >
            Editor
          </button>

          {/* Fullscreen */}
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1.5 rounded text-text-tertiary hover:text-text-secondary transition-colors"
            title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Sandpack */}
      <div className="flex-1 overflow-hidden">
        <SandpackProvider
          template={template as any}
          files={sandpackFiles}
          theme="dark"
          options={{
            activeFile: entryFile,
            visibleFiles: Object.keys(sandpackFiles).slice(0, 20),
            recompileMode: 'delayed',
            recompileDelay: 500,
          }}
        >
          <SandpackLayout style={{ height: '100%', border: 'none', borderRadius: 0 }}>
            {showEditor && (
              <>
                <SandpackFileExplorer style={{ minWidth: 160, maxWidth: 200 }} />
                <SandpackCodeEditor
                  showTabs
                  showLineNumbers
                  showInlineErrors
                  wrapContent
                  style={{ flex: 1 }}
                />
              </>
            )}
            <SandpackPreview
              showOpenInCodeSandbox={false}
              showRefreshButton
              style={{
                flex: showEditor ? 1 : 2,
                maxWidth: viewport === 'desktop' ? '100%' : viewportWidths[viewport],
                margin: viewport !== 'desktop' ? '0 auto' : undefined,
              }}
            />
          </SandpackLayout>
        </SandpackProvider>
      </div>
    </div>
  )
}
