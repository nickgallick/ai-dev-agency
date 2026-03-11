/**
 * BrowserTestPanel — Automated browser testing with video evidence (#11)
 *
 * Run Playwright-based browser tests against the generated app, view step-by-step
 * results, screenshots, and video recordings as proof the app works.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, BrowserTestResult } from '@/lib/api'
import {
  Play,
  Monitor,
  Tablet,
  Smartphone,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  Video,
  Camera,
  Loader2,
  ChevronDown,
  ChevronRight,
  Globe,
  Moon,
} from 'lucide-react'

interface BrowserTestPanelProps {
  projectId: string
  liveUrl?: string | null
}

const VIEWPORT_OPTIONS = [
  { id: 'desktop', label: 'Desktop', icon: Monitor, size: '1280x720' },
  { id: 'tablet', label: 'Tablet', icon: Tablet, size: '768x1024' },
  { id: 'mobile', label: 'Mobile', icon: Smartphone, size: '375x812' },
]

function statusIcon(status: string) {
  if (status === 'passed') return <CheckCircle className="w-3.5 h-3.5" style={{ color: '#4ade80' }} />
  if (status === 'failed') return <XCircle className="w-3.5 h-3.5" style={{ color: '#f87171' }} />
  if (status === 'skipped') return <AlertTriangle className="w-3.5 h-3.5" style={{ color: '#fbbf24' }} />
  return <AlertTriangle className="w-3.5 h-3.5" style={{ color: 'var(--text-tertiary)' }} />
}

function statusColor(status: string): string {
  if (status === 'passed') return '#4ade80'
  if (status === 'failed') return '#f87171'
  if (status === 'error') return '#f87171'
  return '#fbbf24'
}

export function BrowserTestPanel({ projectId, liveUrl }: BrowserTestPanelProps) {
  const queryClient = useQueryClient()
  const [viewport, setViewport] = useState('desktop')
  const [testThemes, setTestThemes] = useState(false)
  const [customUrl, setCustomUrl] = useState('')
  const [expandedTest, setExpandedTest] = useState<string | null>(null)

  const { data: history } = useQuery({
    queryKey: ['browserTests', projectId],
    queryFn: () => api.getBrowserTestHistory(projectId),
  })

  const runMutation = useMutation({
    mutationFn: () => api.runBrowserTest(projectId, {
      url: customUrl || undefined,
      viewport,
      record_video: true,
      take_screenshots: true,
      test_interactions: true,
      test_themes: testThemes,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['browserTests', projectId] })
    },
  })

  const latestResult = runMutation.data
  const tests = history?.tests || []

  return (
    <div className="flex flex-col gap-4">
      {/* Controls */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <Globe className="w-4 h-4" style={{ color: 'var(--accent-primary)' }} />
            <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
              Browser Testing
            </span>
            {liveUrl && (
              <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: 'rgba(74,222,128,0.15)', color: '#4ade80' }}>
                URL available
              </span>
            )}
          </div>

          <button
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending || (!liveUrl && !customUrl)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors disabled:opacity-50"
            style={{ background: 'rgba(59,130,246,0.15)', color: 'var(--accent-primary)' }}
          >
            {runMutation.isPending ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Play className="w-3.5 h-3.5" />
            )}
            {runMutation.isPending ? 'Testing...' : 'Run Tests'}
          </button>
        </div>

        {/* Options row */}
        <div className="flex items-center gap-3 flex-wrap">
          {/* Viewport selector */}
          <div className="flex items-center gap-1">
            {VIEWPORT_OPTIONS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setViewport(id)}
                className="flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium transition-colors"
                style={{
                  background: viewport === id ? 'var(--accent-primary-bg, rgba(59,130,246,0.15))' : 'transparent',
                  color: viewport === id ? 'var(--accent-primary)' : 'var(--text-tertiary)',
                }}
              >
                <Icon className="w-3 h-3" />
                {label}
              </button>
            ))}
          </div>

          {/* Theme toggle */}
          <button
            onClick={() => setTestThemes(!testThemes)}
            className="flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium transition-colors"
            style={{
              background: testThemes ? 'rgba(167,139,250,0.15)' : 'transparent',
              color: testThemes ? '#a78bfa' : 'var(--text-tertiary)',
            }}
          >
            <Moon className="w-3 h-3" />
            Test themes
          </button>

          {/* Custom URL */}
          {!liveUrl && (
            <input
              value={customUrl}
              onChange={(e) => setCustomUrl(e.target.value)}
              placeholder="https://your-app.vercel.app"
              className="text-xs rounded px-2 py-1 flex-1 min-w-[200px]"
              style={{
                background: 'var(--background-tertiary)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-subtle)',
              }}
            />
          )}
        </div>
      </div>

      {/* Latest result */}
      {latestResult && (
        <TestResultCard result={latestResult} isLatest />
      )}

      {/* History */}
      {tests.length > 0 && (
        <div>
          <p className="text-xs font-medium mb-2" style={{ color: 'var(--text-tertiary)' }}>
            Test History ({tests.length})
          </p>
          <div className="space-y-2">
            {tests.map((test: any, i: number) => (
              <div key={test.id || i}>
                <button
                  onClick={() => setExpandedTest(expandedTest === (test.id || String(i)) ? null : (test.id || String(i)))}
                  className="w-full flex items-center justify-between px-3 py-2 rounded-lg border transition-colors text-left"
                  style={{ background: 'var(--background-secondary)', borderColor: 'var(--border-subtle)' }}
                >
                  <div className="flex items-center gap-2">
                    {statusIcon(test.status)}
                    <span className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>
                      {test.viewport || 'desktop'} — {test.url?.slice(0, 40)}
                    </span>
                    <span
                      className="text-[10px] px-1.5 py-0.5 rounded font-medium"
                      style={{ background: `${statusColor(test.status)}20`, color: statusColor(test.status) }}
                    >
                      {test.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {test.summary?.has_video && <Video className="w-3 h-3" style={{ color: '#a78bfa' }} />}
                    <span className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>
                      {test.summary?.passed || 0}/{test.summary?.total_steps || 0} passed
                    </span>
                    <span className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>
                      {test.duration_ms ? `${(test.duration_ms / 1000).toFixed(1)}s` : ''}
                    </span>
                    {expandedTest === (test.id || String(i)) ? (
                      <ChevronDown className="w-3 h-3" style={{ color: 'var(--text-tertiary)' }} />
                    ) : (
                      <ChevronRight className="w-3 h-3" style={{ color: 'var(--text-tertiary)' }} />
                    )}
                  </div>
                </button>
                {expandedTest === (test.id || String(i)) && test.steps && (
                  <div className="ml-4 mt-1 space-y-1">
                    {test.steps.map((step: any, j: number) => (
                      <div key={j} className="flex items-center gap-2 py-1 text-[10px]">
                        {statusIcon(step.status)}
                        <span style={{ color: 'var(--text-secondary)' }}>{step.description}</span>
                        {step.duration_ms > 0 && (
                          <span style={{ color: 'var(--text-tertiary)' }}>({step.duration_ms}ms)</span>
                        )}
                        {step.error && (
                          <span className="text-[10px] truncate max-w-[200px]" style={{ color: '#f87171' }}>
                            {step.error}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!latestResult && tests.length === 0 && (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <Monitor className="w-8 h-8 mb-3" style={{ color: 'var(--text-tertiary)' }} />
          <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
            No browser tests yet
          </p>
          <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
            {liveUrl
              ? 'Click "Run Tests" to test the live app with video evidence'
              : 'Deploy the project first, then run browser tests'}
          </p>
        </div>
      )}
    </div>
  )
}

function TestResultCard({ result, isLatest }: { result: BrowserTestResult; isLatest?: boolean }) {
  const summary = result.summary || {}
  const overallColor = statusColor(result.status)

  return (
    <div
      className="rounded-lg border p-3 space-y-3"
      style={{ background: 'var(--background-secondary)', borderColor: `${overallColor}30` }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {statusIcon(result.status)}
          <span className="text-xs font-medium" style={{ color: overallColor }}>
            {result.status === 'passed' ? 'All checks passed' : result.status === 'failed' ? 'Issues found' : 'Test error'}
          </span>
          {isLatest && (
            <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: 'rgba(59,130,246,0.15)', color: 'var(--accent-primary)' }}>
              Latest
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 text-[10px]" style={{ color: 'var(--text-tertiary)' }}>
          {result.video_path && (
            <span className="flex items-center gap-1">
              <Video className="w-3 h-3" style={{ color: '#a78bfa' }} />
              Video recorded
            </span>
          )}
          <span className="flex items-center gap-1">
            <Camera className="w-3 h-3" />
            {result.screenshots.length} screenshots
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {(result.duration_ms / 1000).toFixed(1)}s
          </span>
        </div>
      </div>

      {/* Stats */}
      <div className="flex gap-4">
        <div className="text-center">
          <div className="text-lg font-bold" style={{ color: '#4ade80' }}>{summary.passed || 0}</div>
          <div className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>Passed</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold" style={{ color: '#f87171' }}>{summary.failed || 0}</div>
          <div className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>Failed</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold" style={{ color: '#fbbf24' }}>{summary.skipped || 0}</div>
          <div className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>Skipped</div>
        </div>
        {(result.console_errors?.length || 0) > 0 && (
          <div className="text-center">
            <div className="text-lg font-bold" style={{ color: '#f87171' }}>{result.console_errors.length}</div>
            <div className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>Console Errors</div>
          </div>
        )}
      </div>

      {/* Steps */}
      <div className="space-y-1">
        {result.steps.map((step) => (
          <div key={step.step} className="flex items-center gap-2 py-0.5">
            {statusIcon(step.status)}
            <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
              {step.description}
            </span>
            {step.error && (
              <span className="text-[10px] truncate max-w-[250px]" style={{ color: '#f87171' }}>
                {step.error}
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Performance */}
      {result.performance_metrics && Object.keys(result.performance_metrics).length > 0 && (
        <div className="pt-2" style={{ borderTop: '1px solid var(--border-subtle)' }}>
          <p className="text-[10px] font-medium mb-1" style={{ color: 'var(--text-tertiary)' }}>Performance</p>
          <div className="flex gap-4 text-[10px]">
            {result.performance_metrics.dom_content_loaded != null && (
              <span style={{ color: 'var(--text-secondary)' }}>
                DOMContentLoaded: {result.performance_metrics.dom_content_loaded}ms
              </span>
            )}
            {result.performance_metrics.load_event != null && (
              <span style={{ color: 'var(--text-secondary)' }}>
                Load: {result.performance_metrics.load_event}ms
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
