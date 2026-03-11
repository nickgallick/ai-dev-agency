/**
 * PipelineDAG — Real-time directed-acyclic-graph visualization of the
 * 20-agent pipeline, powered by React Flow and SSE.
 *
 * Each agent is a node. Edges show dependency flow. Node colors, icons,
 * and animations update live as SSE events stream in.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Position,
  Handle,
  type Node,
  type Edge,
  type NodeProps,
  MarkerType,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import {
  Check,
  Loader2,
  AlertCircle,
  Clock,
  SkipForward,
  Target,
  Search,
  Blocks,
  Palette,
  ImagePlus,
  PenLine,
  ClipboardCheck,
  Code2,
  Link2,
  Shield,
  BarChart3,
  Eye,
  TestTube,
  Rocket,
  CheckCircle2,
  Activity,
  FileText,
  Package,
} from 'lucide-react'
import './PipelineDAG.css'

// ── Types ──────────────────────────────────────────────────────────────

export type AgentNodeStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'skipped'

export interface AgentNodeData extends Record<string, unknown> {
  label: string
  agentId: string
  status: AgentNodeStatus
  icon: string
  duration?: number
  cost?: number
  message?: string
  parallelGroup?: string
}

interface PipelineDAGProps {
  projectId: string
  projectStatus: string
  /** Pass existing SSE events from ActivityFeed if shared */
  sseEvents?: SSEEvent[]
  className?: string
}

interface SSEEvent {
  id: string
  event_type: string
  agent_name?: string
  message?: string
  progress?: number
  details?: Record<string, any>
}

// ── Agent metadata ─────────────────────────────────────────────────────

const AGENT_META: Record<string, { label: string; icon: string }> = {
  intake:                 { label: 'Intake',            icon: 'target' },
  research:              { label: 'Research',           icon: 'search' },
  architect:             { label: 'Architect',          icon: 'blocks' },
  design_system:         { label: 'Design System',     icon: 'palette' },
  asset_generation:      { label: 'Assets',            icon: 'image' },
  content_generation:    { label: 'Content',           icon: 'pen' },
  pm_checkpoint_1:       { label: 'PM Check 1',        icon: 'clipboard' },
  code_generation:       { label: 'Code Gen',          icon: 'code' },
  integration_wiring:    { label: 'Integrations',      icon: 'link' },
  pm_checkpoint_2:       { label: 'PM Check 2',        icon: 'clipboard' },
  code_review:           { label: 'Code Review',       icon: 'eye' },
  security:              { label: 'Security',          icon: 'shield' },
  seo:                   { label: 'SEO',               icon: 'chart' },
  accessibility:         { label: 'Accessibility',     icon: 'eye' },
  qa:                    { label: 'QA Testing',        icon: 'test' },
  deployment:            { label: 'Deploy',            icon: 'rocket' },
  post_deploy_verification: { label: 'Verify',        icon: 'check' },
  analytics_monitoring:  { label: 'Analytics',         icon: 'activity' },
  coding_standards:      { label: 'Standards',         icon: 'file' },
  delivery:              { label: 'Delivery',          icon: 'package' },
}

// ── Pipeline DAG definition (node positions + edges) ───────────────────

// Column-based layout: X = column (step), Y = row within parallel groups
const COL = 200 // horizontal spacing
const ROW = 100 // vertical spacing

interface NodeDef {
  id: string
  x: number
  y: number
  deps: string[]
}

const PIPELINE_NODES: NodeDef[] = [
  // Phase 1: Sequential intake → research → architect
  { id: 'intake',              x: 0,       y: 0,        deps: [] },
  { id: 'research',            x: COL,     y: 0,        deps: ['intake'] },
  { id: 'architect',           x: COL*2,   y: 0,        deps: ['research'] },

  // Phase 2: Design + parallel asset/content
  { id: 'design_system',       x: COL*3,   y: -ROW,     deps: ['architect'] },
  { id: 'asset_generation',    x: COL*3,   y: 0,        deps: ['architect'] },
  { id: 'content_generation',  x: COL*3,   y: ROW,      deps: ['architect'] },

  // Phase 3: PM checkpoint → code gen → integrations
  { id: 'pm_checkpoint_1',     x: COL*4,   y: 0,        deps: ['design_system', 'asset_generation', 'content_generation'] },
  { id: 'code_generation',     x: COL*5,   y: 0,        deps: ['pm_checkpoint_1'] },
  { id: 'integration_wiring',  x: COL*6,   y: 0,        deps: ['code_generation'] },

  // Phase 4: PM2 → code review
  { id: 'pm_checkpoint_2',     x: COL*7,   y: 0,        deps: ['integration_wiring'] },
  { id: 'code_review',         x: COL*8,   y: 0,        deps: ['pm_checkpoint_2'] },

  // Phase 5: Parallel quality gates
  { id: 'security',            x: COL*9,   y: -ROW,     deps: ['code_review'] },
  { id: 'seo',                 x: COL*9,   y: 0,        deps: ['code_review'] },
  { id: 'accessibility',       x: COL*9,   y: ROW,      deps: ['code_review'] },

  // Phase 6: QA → Deploy → Verify
  { id: 'qa',                  x: COL*10,  y: 0,        deps: ['security', 'seo', 'accessibility'] },
  { id: 'deployment',          x: COL*11,  y: 0,        deps: ['qa'] },
  { id: 'post_deploy_verification', x: COL*12, y: 0,   deps: ['deployment'] },

  // Phase 7: Parallel analytics/standards → delivery
  { id: 'analytics_monitoring', x: COL*13, y: -ROW/2,   deps: ['post_deploy_verification'] },
  { id: 'coding_standards',    x: COL*13,  y: ROW/2,    deps: ['post_deploy_verification'] },
  { id: 'delivery',            x: COL*14,  y: 0,        deps: ['analytics_monitoring', 'coding_standards'] },
]

// ── Build React Flow nodes and edges ──────────────────────────────────

function buildInitialNodes(): Node<AgentNodeData>[] {
  return PIPELINE_NODES.map((def) => {
    const meta = AGENT_META[def.id] || { label: def.id, icon: 'target' }
    return {
      id: def.id,
      type: 'agentNode',
      position: { x: def.x + 60, y: def.y + 200 },
      data: {
        label: meta.label,
        agentId: def.id,
        status: 'pending' as AgentNodeStatus,
        icon: meta.icon,
      },
    }
  })
}

function buildEdges(): Edge[] {
  const edges: Edge[] = []
  for (const def of PIPELINE_NODES) {
    for (const dep of def.deps) {
      edges.push({
        id: `${dep}->${def.id}`,
        source: dep,
        target: def.id,
        type: 'smoothstep',
        animated: false,
        style: { stroke: 'var(--border-primary)', strokeWidth: 2 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 16,
          height: 16,
          color: 'var(--border-primary)',
        },
      })
    }
  }
  return edges
}

// ── Icon resolver ──────────────────────────────────────────────────────

function AgentIcon({ icon, className }: { icon: string; className?: string }) {
  const cls = className || 'w-4 h-4'
  switch (icon) {
    case 'target':    return <Target className={cls} />
    case 'search':    return <Search className={cls} />
    case 'blocks':    return <Blocks className={cls} />
    case 'palette':   return <Palette className={cls} />
    case 'image':     return <ImagePlus className={cls} />
    case 'pen':       return <PenLine className={cls} />
    case 'clipboard': return <ClipboardCheck className={cls} />
    case 'code':      return <Code2 className={cls} />
    case 'link':      return <Link2 className={cls} />
    case 'eye':       return <Eye className={cls} />
    case 'shield':    return <Shield className={cls} />
    case 'chart':     return <BarChart3 className={cls} />
    case 'test':      return <TestTube className={cls} />
    case 'rocket':    return <Rocket className={cls} />
    case 'check':     return <CheckCircle2 className={cls} />
    case 'activity':  return <Activity className={cls} />
    case 'file':      return <FileText className={cls} />
    case 'package':   return <Package className={cls} />
    default:          return <Target className={cls} />
  }
}

// ── Custom node component ──────────────────────────────────────────────

function AgentNodeComponent({ data }: NodeProps<Node<AgentNodeData>>) {
  const { label, status, icon, duration, cost, message } = data

  const statusClass = `dag-node-${status}`
  const isRunning = status === 'running'

  return (
    <div className={`dag-node ${statusClass}`}>
      <Handle type="target" position={Position.Left} className="dag-handle" />

      <div className="dag-node-header">
        <div className="dag-node-icon">
          {status === 'running' ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : status === 'completed' ? (
            <Check className="w-4 h-4" />
          ) : status === 'failed' ? (
            <AlertCircle className="w-4 h-4" />
          ) : status === 'skipped' ? (
            <SkipForward className="w-4 h-4" />
          ) : (
            <AgentIcon icon={icon} />
          )}
        </div>
        <span className="dag-node-label">{label}</span>
      </div>

      {/* Status indicator dot */}
      <div className={`dag-node-status-dot ${statusClass}`} />

      {/* Running message */}
      {isRunning && message && (
        <div className="dag-node-message">{message}</div>
      )}

      {/* Completed meta */}
      {status === 'completed' && (duration != null || cost != null) && (
        <div className="dag-node-meta">
          {duration != null && (
            <span>{duration < 1000 ? `${duration}ms` : `${(duration/1000).toFixed(1)}s`}</span>
          )}
          {cost != null && cost > 0 && <span>${cost.toFixed(4)}</span>}
        </div>
      )}

      <Handle type="source" position={Position.Right} className="dag-handle" />
    </div>
  )
}

const nodeTypes = { agentNode: AgentNodeComponent }

// ── Main component ────────────────────────────────────────────────────

export function PipelineDAG({
  projectId,
  projectStatus,
  sseEvents: externalEvents,
  className,
}: PipelineDAGProps) {
  const initialNodes = useMemo(() => buildInitialNodes(), [])
  const initialEdges = useMemo(() => buildEdges(), [])

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const [progress, setProgress] = useState(0)
  const [connected, setConnected] = useState(false)

  const eventSourceRef = useRef<EventSource | null>(null)
  const nodeStatusRef = useRef<Record<string, AgentNodeStatus>>({})

  // ── SSE connection ───────────────────────────────────────────────

  useEffect(() => {
    const isActive = !['completed', 'failed', 'pending'].includes(projectStatus)
    if (!isActive || !projectId) return

    const apiUrl = import.meta.env.VITE_API_URL || ''
    const es = new EventSource(`${apiUrl}/api/activity/${projectId}/stream`)
    eventSourceRef.current = es

    es.onopen = () => setConnected(true)

    es.onmessage = (event) => {
      try {
        const data: SSEEvent = JSON.parse(event.data)
        handleSSEEvent(data)
      } catch (e) {
        console.error('DAG SSE parse error:', e)
      }
    }

    es.onerror = () => {
      setConnected(false)
      es.close()
      eventSourceRef.current = null
      // Reconnect after 3s
      const timer = setTimeout(() => {
        if (isActive && projectId) {
          const retry = new EventSource(`${apiUrl}/api/activity/${projectId}/stream`)
          eventSourceRef.current = retry
          retry.onopen = () => setConnected(true)
          retry.onmessage = es.onmessage
          retry.onerror = es.onerror
        }
      }, 3000)
      return () => clearTimeout(timer)
    }

    return () => {
      es.close()
      eventSourceRef.current = null
    }
  }, [projectId, projectStatus])

  // If external events are passed (e.g., shared with ActivityFeed), apply them
  useEffect(() => {
    if (!externalEvents) return
    for (const ev of externalEvents) {
      handleSSEEvent(ev)
    }
  }, [externalEvents])

  // Mark all nodes completed when project is completed
  useEffect(() => {
    if (projectStatus === 'completed') {
      setNodes((nds) =>
        nds.map((n) => ({
          ...n,
          data: { ...n.data, status: 'completed' as AgentNodeStatus },
        }))
      )
      setEdges((eds) =>
        eds.map((e) => ({
          ...e,
          animated: false,
          style: { ...e.style, stroke: 'var(--accent-success)' },
          markerEnd: { ...e.markerEnd as any, color: 'var(--accent-success)' },
        }))
      )
      setProgress(100)
    }
  }, [projectStatus])

  // ── Handle SSE events → update node status ─────────────────────

  const handleSSEEvent = useCallback((ev: SSEEvent) => {
    const agentName = ev.agent_name
    if (ev.progress != null) setProgress(ev.progress)

    if (!agentName) return

    let newStatus: AgentNodeStatus | null = null
    let message: string | undefined

    switch (ev.event_type) {
      case 'agent_start':
      case 'agent_thinking':
        newStatus = 'running'
        message = ev.message
        break
      case 'agent_complete':
        newStatus = 'completed'
        break
      case 'agent_error':
      case 'agent_failed':
        newStatus = 'failed'
        break
      case 'agent_skip':
        newStatus = 'skipped'
        break
    }

    if (!newStatus) return

    // Track status in ref (for edge updates)
    nodeStatusRef.current[agentName] = newStatus

    // Update the specific node
    setNodes((nds) =>
      nds.map((n) => {
        if (n.id !== agentName) return n
        return {
          ...n,
          data: {
            ...n.data,
            status: newStatus!,
            message: message,
            duration: ev.details?.duration_ms,
            cost: ev.details?.cost,
          },
        }
      })
    )

    // Update edge colors based on node status
    setEdges((eds) =>
      eds.map((e) => {
        const sourceStatus = nodeStatusRef.current[e.source]
        const targetStatus = nodeStatusRef.current[e.target]

        // Animate edges leading to running nodes
        const animated = targetStatus === 'running'

        // Color completed edges green
        let stroke = 'var(--border-primary)'
        let markerColor = 'var(--border-primary)'
        if (sourceStatus === 'completed' && targetStatus === 'completed') {
          stroke = 'var(--accent-success)'
          markerColor = 'var(--accent-success)'
        } else if (targetStatus === 'running') {
          stroke = 'var(--accent-primary)'
          markerColor = 'var(--accent-primary)'
        } else if (sourceStatus === 'failed' || targetStatus === 'failed') {
          stroke = 'var(--accent-error)'
          markerColor = 'var(--accent-error)'
        }

        return {
          ...e,
          animated,
          style: { ...e.style, stroke, strokeWidth: 2 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 16,
            height: 16,
            color: markerColor,
          },
        }
      })
    )
  }, [setNodes, setEdges])

  // ── Legend ───────────────────────────────────────────────────────

  const completedCount = nodes.filter((n) => (n.data as AgentNodeData).status === 'completed').length
  const totalCount = nodes.length

  return (
    <div className={`dag-container ${className || ''}`}>
      {/* Header bar */}
      <div className="dag-header">
        <div className="dag-header-left">
          <span className="dag-header-title">Pipeline DAG</span>
          <span className={`dag-connection-dot ${connected ? 'live' : ''}`} />
          <span className="dag-connection-text">
            {connected ? 'Live' : projectStatus === 'completed' ? 'Done' : 'Offline'}
          </span>
        </div>
        <div className="dag-header-right">
          <span className="dag-progress-text">
            {completedCount}/{totalCount} agents
          </span>
          <div className="dag-progress-bar">
            <div
              className="dag-progress-fill"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="dag-progress-pct">{Math.round(progress)}%</span>
        </div>
      </div>

      {/* Legend */}
      <div className="dag-legend">
        <LegendItem status="pending" label="Pending" />
        <LegendItem status="running" label="Running" />
        <LegendItem status="completed" label="Done" />
        <LegendItem status="failed" label="Failed" />
        <LegendItem status="skipped" label="Skipped" />
      </div>

      {/* React Flow canvas */}
      <div className="dag-canvas">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2, maxZoom: 1.2 }}
          minZoom={0.3}
          maxZoom={2}
          nodesDraggable={false}
          nodesConnectable={false}
          proOptions={{ hideAttribution: true }}
          defaultEdgeOptions={{
            type: 'smoothstep',
          }}
        >
          <Background color="var(--border-subtle)" gap={20} size={1} />
          <Controls
            showInteractive={false}
            className="dag-controls"
          />
          <MiniMap
            nodeColor={(n) => {
              const status = (n.data as AgentNodeData)?.status
              switch (status) {
                case 'completed': return 'var(--accent-success)'
                case 'running':   return 'var(--accent-primary)'
                case 'failed':    return 'var(--accent-error)'
                case 'skipped':   return 'var(--text-tertiary)'
                default:          return 'var(--border-primary)'
              }
            }}
            maskColor="rgba(0,0,0,0.6)"
            className="dag-minimap"
          />
        </ReactFlow>
      </div>
    </div>
  )
}

function LegendItem({ status, label }: { status: string; label: string }) {
  return (
    <div className="dag-legend-item">
      <div className={`dag-legend-dot dag-legend-${status}`} />
      <span>{label}</span>
    </div>
  )
}
