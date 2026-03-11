/**
 * DesignImportPanel — Figma & Screenshot import for design context (#23)
 *
 * Accept Figma URLs or screenshot uploads to extract design tokens and
 * inject them as context for the Design System agent.
 */
import { useState, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, DesignTokensData } from '@/lib/api'
import {
  Upload,
  Image,
  Palette,
  Check,
  AlertTriangle,
  Loader2,
  ChevronDown,
  ChevronRight,
  X,
} from 'lucide-react'

// Figma icon inline since lucide doesn't have it
function FigmaIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 5.5A3.5 3.5 0 0 1 8.5 2H12v7H8.5A3.5 3.5 0 0 1 5 5.5z" />
      <path d="M12 2h3.5a3.5 3.5 0 1 1 0 7H12V2z" />
      <path d="M12 12.5a3.5 3.5 0 1 1 7 0 3.5 3.5 0 1 1-7 0z" />
      <path d="M5 19.5A3.5 3.5 0 0 1 8.5 16H12v3.5a3.5 3.5 0 1 1-7 0z" />
      <path d="M5 12.5A3.5 3.5 0 0 1 8.5 9H12v7H8.5A3.5 3.5 0 0 1 5 12.5z" />
    </svg>
  )
}

interface DesignImportPanelProps {
  projectId: string
}

export function DesignImportPanel({ projectId }: DesignImportPanelProps) {
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [figmaUrl, setFigmaUrl] = useState('')
  const [showTokens, setShowTokens] = useState(false)

  const { data: tokens } = useQuery({
    queryKey: ['designTokens', projectId],
    queryFn: () => api.getDesignTokens(projectId),
  })

  const figmaMutation = useMutation({
    mutationFn: () => api.importFromFigma(projectId, { figma_url: figmaUrl }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['designTokens', projectId] })
      setFigmaUrl('')
    },
  })

  const screenshotMutation = useMutation({
    mutationFn: (file: File) => api.uploadDesignScreenshot(projectId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['designTokens', projectId] })
    },
  })

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      screenshotMutation.mutate(file)
    }
    // Reset input so same file can be re-uploaded
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const hasTokens = tokens && tokens.source !== 'none'
  const colorCount = Object.keys(tokens?.colors || {}).length
  const typoCount = Object.keys(tokens?.typography || {}).length
  const compCount = (tokens?.components || []).length

  return (
    <div className="flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Palette className="w-4 h-4" style={{ color: 'var(--accent-primary)' }} />
        <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
          Design Import
        </span>
        {hasTokens && (
          <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: 'rgba(74,222,128,0.15)', color: '#4ade80' }}>
            {colorCount} colors · {typoCount} fonts · {compCount} components
          </span>
        )}
      </div>

      {/* Import methods */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {/* Figma import */}
        <div
          className="rounded-lg border p-3 space-y-2"
          style={{ background: 'var(--background-secondary)', borderColor: 'var(--border-subtle)' }}
        >
          <div className="flex items-center gap-2">
            <FigmaIcon className="w-4 h-4" />
            <span className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>
              Import from Figma
            </span>
          </div>
          <div className="flex gap-2">
            <input
              value={figmaUrl}
              onChange={(e) => setFigmaUrl(e.target.value)}
              placeholder="https://www.figma.com/file/..."
              className="flex-1 text-xs rounded px-2 py-1.5"
              style={{
                background: 'var(--background-tertiary)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-subtle)',
              }}
            />
            <button
              onClick={() => figmaMutation.mutate()}
              disabled={!figmaUrl || figmaMutation.isPending}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded text-xs font-medium disabled:opacity-50"
              style={{ background: 'rgba(59,130,246,0.15)', color: 'var(--accent-primary)' }}
            >
              {figmaMutation.isPending ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <FigmaIcon className="w-3 h-3" />
              )}
              Import
            </button>
          </div>
          {figmaMutation.isSuccess && (
            <div className="flex items-center gap-1 text-[10px]" style={{ color: '#4ade80' }}>
              <Check className="w-3 h-3" />
              Imported {figmaMutation.data?.components_found || 0} components, {figmaMutation.data?.styles_found || 0} styles
            </div>
          )}
          {figmaMutation.isError && (
            <div className="flex items-center gap-1 text-[10px]" style={{ color: '#f87171' }}>
              <AlertTriangle className="w-3 h-3" />
              {(figmaMutation.error as any)?.response?.data?.detail || 'Import failed'}
            </div>
          )}
        </div>

        {/* Screenshot upload */}
        <div
          className="rounded-lg border p-3 space-y-2"
          style={{ background: 'var(--background-secondary)', borderColor: 'var(--border-subtle)' }}
        >
          <div className="flex items-center gap-2">
            <Image className="w-4 h-4" style={{ color: '#a78bfa' }} />
            <span className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>
              Upload Design Screenshot
            </span>
          </div>
          <p className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>
            Upload a PNG, JPG, or WebP screenshot. AI will extract colors, typography, and layout patterns.
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={handleFileSelect}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={screenshotMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium w-full justify-center disabled:opacity-50 transition-colors"
            style={{ background: 'rgba(167,139,250,0.15)', color: '#a78bfa' }}
          >
            {screenshotMutation.isPending ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <Upload className="w-3 h-3" />
            )}
            {screenshotMutation.isPending ? 'Analyzing...' : 'Upload Screenshot'}
          </button>
          {screenshotMutation.isSuccess && (
            <div className="flex items-center gap-1 text-[10px]" style={{ color: '#4ade80' }}>
              <Check className="w-3 h-3" />
              {screenshotMutation.data?.tokens?.style_analysis?.slice(0, 80) || 'Analyzed successfully'}
            </div>
          )}
          {screenshotMutation.isError && (
            <div className="flex items-center gap-1 text-[10px]" style={{ color: '#f87171' }}>
              <AlertTriangle className="w-3 h-3" />
              {(screenshotMutation.error as any)?.response?.data?.detail || 'Upload failed'}
            </div>
          )}
        </div>
      </div>

      {/* Extracted tokens preview */}
      {hasTokens && (
        <div>
          <button
            onClick={() => setShowTokens(!showTokens)}
            className="flex items-center gap-1.5 text-xs font-medium"
            style={{ color: 'var(--text-secondary)' }}
          >
            {showTokens ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            Extracted Design Tokens
          </button>

          {showTokens && tokens && (
            <div
              className="mt-2 rounded-lg border p-3 space-y-3"
              style={{ background: 'var(--background-secondary)', borderColor: 'var(--border-subtle)' }}
            >
              {/* Source */}
              <p className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>
                Source: {tokens.source}
              </p>

              {/* Colors */}
              {colorCount > 0 && (
                <div>
                  <p className="text-[10px] font-medium mb-1" style={{ color: 'var(--text-tertiary)' }}>
                    Colors ({colorCount})
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(tokens.colors).slice(0, 20).map(([name, value]) => (
                      <div key={name} className="flex items-center gap-1.5">
                        <div
                          className="w-4 h-4 rounded border"
                          style={{ backgroundColor: String(value), borderColor: 'var(--border-subtle)' }}
                        />
                        <span className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>
                          {name}
                        </span>
                        <span className="text-[10px] font-mono" style={{ color: 'var(--text-tertiary)' }}>
                          {String(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Typography */}
              {typoCount > 0 && (
                <div>
                  <p className="text-[10px] font-medium mb-1" style={{ color: 'var(--text-tertiary)' }}>
                    Typography ({typoCount})
                  </p>
                  <div className="space-y-0.5">
                    {Object.entries(tokens.typography).slice(0, 10).map(([name, value]) => (
                      <div key={name} className="flex items-center gap-2 text-[10px]">
                        <span style={{ color: 'var(--text-secondary)' }}>{name}</span>
                        <span className="font-mono" style={{ color: 'var(--text-tertiary)' }}>
                          {typeof value === 'object' ? (value as any).fontFamily || JSON.stringify(value) : String(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Components */}
              {compCount > 0 && (
                <div>
                  <p className="text-[10px] font-medium mb-1" style={{ color: 'var(--text-tertiary)' }}>
                    Components ({compCount})
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {tokens.components.slice(0, 15).map((comp: any, i: number) => (
                      <span
                        key={i}
                        className="text-[10px] px-1.5 py-0.5 rounded"
                        style={{ background: 'var(--background-tertiary)', color: 'var(--text-secondary)' }}
                      >
                        {comp.name || `Component ${i + 1}`}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Style analysis */}
              {tokens.style_analysis && (
                <div>
                  <p className="text-[10px] font-medium mb-1" style={{ color: 'var(--text-tertiary)' }}>Analysis</p>
                  <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{tokens.style_analysis}</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
