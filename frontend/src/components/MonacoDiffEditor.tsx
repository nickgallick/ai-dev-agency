/**
 * MonacoDiffEditor — Code-split Monaco diff editor for comparing agent outputs.
 *
 * Lazy-loaded so the ~2MB Monaco bundle doesn't bloat the main chunk.
 * Usage: compare any two agent outputs (before/after, or two different agents).
 */
import { lazy, Suspense, useState, useMemo } from 'react'
import { Loader2, X, ArrowLeftRight, Copy, Check } from 'lucide-react'

// Lazy-load Monaco to avoid bundle bloat
const DiffEditor = lazy(() =>
  import('@monaco-editor/react').then((mod) => ({ default: mod.DiffEditor }))
)

interface MonacoDiffEditorProps {
  /** Left-side content label */
  originalLabel?: string
  /** Right-side content label */
  modifiedLabel?: string
  /** Left-side content (JSON or text) */
  original: string
  /** Right-side content (JSON or text) */
  modified: string
  /** Language for syntax highlighting */
  language?: string
  /** Height of the editor */
  height?: string | number
  /** Called when the modal/panel should close */
  onClose?: () => void
}

function formatForDiff(value: any): string {
  if (typeof value === 'string') return value
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

export function MonacoDiffEditor({
  originalLabel = 'Before',
  modifiedLabel = 'After',
  original,
  modified,
  language = 'json',
  height = '500px',
  onClose,
}: MonacoDiffEditorProps) {
  const [copied, setCopied] = useState<'original' | 'modified' | null>(null)

  const handleCopy = async (side: 'original' | 'modified') => {
    const text = side === 'original' ? original : modified
    await navigator.clipboard.writeText(text)
    setCopied(side)
    setTimeout(() => setCopied(null), 2000)
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-background-secondary border-b border-white/5">
        <div className="flex items-center gap-3">
          <ArrowLeftRight className="w-4 h-4 text-accent-primary" />
          <div className="flex items-center gap-2 text-sm">
            <span className="font-medium text-red-400">{originalLabel}</span>
            <span className="text-text-tertiary">vs</span>
            <span className="font-medium text-green-400">{modifiedLabel}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleCopy('original')}
            className="flex items-center gap-1 px-2 py-1 text-xs text-text-secondary hover:text-text-primary rounded bg-background-tertiary hover:bg-white/10 transition-colors"
            title={`Copy ${originalLabel}`}
          >
            {copied === 'original' ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />}
            {originalLabel}
          </button>
          <button
            onClick={() => handleCopy('modified')}
            className="flex items-center gap-1 px-2 py-1 text-xs text-text-secondary hover:text-text-primary rounded bg-background-tertiary hover:bg-white/10 transition-colors"
            title={`Copy ${modifiedLabel}`}
          >
            {copied === 'modified' ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />}
            {modifiedLabel}
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="p-1 text-text-tertiary hover:text-text-primary rounded hover:bg-white/10 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Editor */}
      <div className="flex-1 min-h-0">
        <Suspense
          fallback={
            <div className="flex items-center justify-center h-full bg-background-primary">
              <Loader2 className="w-6 h-6 animate-spin text-accent-primary" />
              <span className="ml-2 text-sm text-text-secondary">Loading diff editor...</span>
            </div>
          }
        >
          <DiffEditor
            height={height}
            language={language}
            original={original}
            modified={modified}
            theme="vs-dark"
            options={{
              readOnly: true,
              renderSideBySide: true,
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              fontSize: 12,
              wordWrap: 'on',
              lineNumbers: 'on',
              folding: true,
              renderWhitespace: 'none',
              contextmenu: false,
              automaticLayout: true,
            }}
          />
        </Suspense>
      </div>
    </div>
  )
}

/**
 * AgentOutputDiffModal — Modal wrapper for comparing two agent outputs.
 *
 * Pass two agent IDs and their output data; the modal renders a
 * side-by-side diff using Monaco.
 */
interface AgentOutputDiffModalProps {
  agentOutputs: Record<string, any>
  agents: Array<{ id: string; label: string }>
  onClose: () => void
}

export function AgentOutputDiffModal({
  agentOutputs,
  agents,
  onClose,
}: AgentOutputDiffModalProps) {
  const completedAgents = useMemo(
    () => agents.filter((a) => agentOutputs[a.id]),
    [agents, agentOutputs]
  )

  const [leftAgent, setLeftAgent] = useState(completedAgents[0]?.id || '')
  const [rightAgent, setRightAgent] = useState(completedAgents[1]?.id || completedAgents[0]?.id || '')

  const leftData = useMemo(() => {
    const raw = agentOutputs[leftAgent]
    if (!raw) return ''
    const { _reasoning, ...rest } = typeof raw === 'object' ? raw : { value: raw }
    return formatForDiff(rest)
  }, [agentOutputs, leftAgent])

  const rightData = useMemo(() => {
    const raw = agentOutputs[rightAgent]
    if (!raw) return ''
    const { _reasoning, ...rest } = typeof raw === 'object' ? raw : { value: raw }
    return formatForDiff(rest)
  }, [agentOutputs, rightAgent])

  const leftLabel = completedAgents.find((a) => a.id === leftAgent)?.label || leftAgent
  const rightLabel = completedAgents.find((a) => a.id === rightAgent)?.label || rightAgent

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-[90vw] max-w-[1400px] h-[80vh] bg-background-primary rounded-xl border border-white/10 shadow-2xl overflow-hidden flex flex-col">
        {/* Agent selectors */}
        <div className="flex items-center gap-4 px-4 py-3 bg-background-secondary border-b border-white/5">
          <select
            value={leftAgent}
            onChange={(e) => setLeftAgent(e.target.value)}
            className="px-3 py-1.5 text-sm bg-background-tertiary text-text-primary border border-white/10 rounded-md focus:outline-none focus:border-accent-primary"
          >
            {completedAgents.map((a) => (
              <option key={a.id} value={a.id}>{a.label}</option>
            ))}
          </select>
          <ArrowLeftRight className="w-4 h-4 text-text-tertiary flex-shrink-0" />
          <select
            value={rightAgent}
            onChange={(e) => setRightAgent(e.target.value)}
            className="px-3 py-1.5 text-sm bg-background-tertiary text-text-primary border border-white/10 rounded-md focus:outline-none focus:border-accent-primary"
          >
            {completedAgents.map((a) => (
              <option key={a.id} value={a.id}>{a.label}</option>
            ))}
          </select>
          <div className="flex-1" />
          <button
            onClick={onClose}
            className="p-1.5 text-text-tertiary hover:text-text-primary rounded-md hover:bg-white/10 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Diff editor */}
        <div className="flex-1 min-h-0">
          <MonacoDiffEditor
            originalLabel={leftLabel}
            modifiedLabel={rightLabel}
            original={leftData}
            modified={rightData}
            height="100%"
          />
        </div>
      </div>
    </div>
  )
}

export default MonacoDiffEditor
