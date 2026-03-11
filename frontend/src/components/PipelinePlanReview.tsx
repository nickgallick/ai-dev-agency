/**
 * PipelinePlanReview — Interactive pipeline execution plan review
 * before the build starts. Users see all agents, estimated costs,
 * which will be skipped, and can toggle optional agents on/off.
 *
 * Feature #13: Granular Pipeline Plan Review Before Execution
 */
import { useState, useMemo } from 'react'
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
  Target, Search, Blocks, Palette, ImagePlus, PenLine,
  ClipboardCheck, Code2, Link2, Eye, Shield, BarChart3,
  TestTube, Rocket, CheckCircle2, Activity, FileText, Package,
  SkipForward, Clock, DollarSign, Zap, Layers, AlertTriangle,
  X, ChevronDown, ChevronUp, Pause,
} from 'lucide-react'
import type { PipelinePlan, PlanAgent } from '@/lib/api'
import './PipelineDAG.css'

// ── Types ──────────────────────────────────────────────────────────────

interface PlanNodeData extends Record<string, unknown> {
  label: string
  agentId: string
  icon: string
  skipped: boolean
  required: boolean
  isCheckpoint: boolean
  cost: number
  timeSeconds: number
  model: string
  description: string
  canToggle: boolean
}

interface PipelinePlanReviewProps {
  plan: PipelinePlan
  onApprove: (skippedAgents: string[]) => void
  onCancel: () => void
  isSubmitting?: boolean
}

// ── Agent metadata ──────────────────────────────────────────────────

const AGENT_META: Record<string, { label: string; icon: string }> = {
  intake:                 { label: 'Intake',          icon: 'target' },
  research:              { label: 'Research',         icon: 'search' },
  architect:             { label: 'Architect',        icon: 'blocks' },
  design_system:         { label: 'Design System',   icon: 'palette' },
  asset_generation:      { label: 'Assets',          icon: 'image' },
  content_generation:    { label: 'Content',         icon: 'pen' },
  pm_checkpoint_1:       { label: 'PM Check 1',      icon: 'clipboard' },
  code_generation:       { label: 'Code Gen',        icon: 'code' },
  integration_wiring:    { label: 'Integrations',    icon: 'link' },
  pm_checkpoint_2:       { label: 'PM Check 2',      icon: 'clipboard' },
  code_review:           { label: 'Code Review',     icon: 'eye' },
  security:              { label: 'Security',        icon: 'shield' },
  seo:                   { label: 'SEO',             icon: 'chart' },
  accessibility:         { label: 'Accessibility',   icon: 'eye' },
  qa:                    { label: 'QA Testing',      icon: 'test' },
  deployment:            { label: 'Deploy',          icon: 'rocket' },
  post_deploy_verification: { label: 'Verify',      icon: 'check' },
  analytics_monitoring:  { label: 'Analytics',       icon: 'activity' },
  coding_standards:      { label: 'Standards',       icon: 'file' },
  delivery:              { label: 'Delivery',        icon: 'package' },
}

// ── DAG layout (mirroring PipelineDAG positions) ────────────────────

const COL = 200
const ROW = 100

const NODE_POSITIONS: Record<string, { x: number; y: number }> = {
  intake:                 { x: 0,       y: 0 },
  research:              { x: COL,     y: 0 },
  architect:             { x: COL*2,   y: 0 },
  design_system:         { x: COL*3,   y: -ROW },
  asset_generation:      { x: COL*3,   y: 0 },
  content_generation:    { x: COL*3,   y: ROW },
  pm_checkpoint_1:       { x: COL*4,   y: 0 },
  code_generation:       { x: COL*5,   y: 0 },
  integration_wiring:    { x: COL*6,   y: 0 },
  pm_checkpoint_2:       { x: COL*7,   y: 0 },
  code_review:           { x: COL*8,   y: 0 },
  security:              { x: COL*9,   y: -ROW },
  seo:                   { x: COL*9,   y: 0 },
  accessibility:         { x: COL*9,   y: ROW },
  qa:                    { x: COL*10,  y: 0 },
  deployment:            { x: COL*11,  y: 0 },
  post_deploy_verification: { x: COL*12, y: 0 },
  analytics_monitoring:  { x: COL*13,  y: -ROW/2 },
  coding_standards:      { x: COL*13,  y: ROW/2 },
  delivery:              { x: COL*14,  y: 0 },
}

// ── Icon resolver ───────────────────────────────────────────────────

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

// ── Plan node component ─────────────────────────────────────────────

function PlanNodeComponent({ data }: NodeProps<Node<PlanNodeData>>) {
  const { label, icon, skipped, required, isCheckpoint, cost, timeSeconds, description, canToggle } = data

  const nodeClass = skipped
    ? 'dag-node dag-node-skipped'
    : isCheckpoint
    ? 'dag-node dag-node-paused'
    : 'dag-node dag-node-pending'

  return (
    <div className={nodeClass} style={{ opacity: skipped ? 0.45 : 1, minWidth: 140 }}>
      <Handle type="target" position={Position.Left} className="dag-handle" />

      <div className="dag-node-header">
        <div className="dag-node-icon">
          {skipped ? (
            <SkipForward className="w-4 h-4" />
          ) : isCheckpoint ? (
            <Pause className="w-4 h-4" />
          ) : (
            <AgentIcon icon={icon} />
          )}
        </div>
        <span className="dag-node-label">{label}</span>
      </div>

      {/* Cost + time */}
      {!skipped && (
        <div className="dag-node-meta">
          <span>${cost.toFixed(3)}</span>
          <span>{timeSeconds < 60 ? `${Math.round(timeSeconds)}s` : `${Math.round(timeSeconds / 60)}m`}</span>
        </div>
      )}

      {/* Badges */}
      <div style={{ display: 'flex', gap: 3, marginTop: 2, flexWrap: 'wrap', justifyContent: 'center' }}>
        {required && !skipped && (
          <span style={{ fontSize: 9, padding: '1px 4px', borderRadius: 4, background: 'rgba(239,68,68,0.2)', color: '#f87171' }}>
            required
          </span>
        )}
        {isCheckpoint && !skipped && (
          <span style={{ fontSize: 9, padding: '1px 4px', borderRadius: 4, background: 'rgba(168,85,247,0.2)', color: '#c084fc' }}>
            checkpoint
          </span>
        )}
        {skipped && (
          <span style={{ fontSize: 9, padding: '1px 4px', borderRadius: 4, background: 'rgba(156,163,175,0.2)', color: '#9ca3af' }}>
            skipped
          </span>
        )}
      </div>

      <Handle type="source" position={Position.Right} className="dag-handle" />
    </div>
  )
}

const nodeTypes = { planNode: PlanNodeComponent }

// ── Main component ──────────────────────────────────────────────────

export default function PipelinePlanReview({
  plan,
  onApprove,
  onCancel,
  isSubmitting = false,
}: PipelinePlanReviewProps) {
  // Track user toggle state for each agent
  const [userSkips, setUserSkips] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {}
    for (const agent of plan.agents) {
      initial[agent.agent_id] = agent.skipped
    }
    return initial
  })

  const [showAgentList, setShowAgentList] = useState(true)

  // Build React Flow nodes
  const initialNodes = useMemo((): Node<PlanNodeData>[] => {
    return plan.agents.map((agent) => {
      const meta = AGENT_META[agent.agent_id] || { label: agent.agent_id, icon: 'target' }
      const pos = NODE_POSITIONS[agent.agent_id] || { x: 0, y: 0 }
      return {
        id: agent.agent_id,
        type: 'planNode',
        position: { x: pos.x + 60, y: pos.y + 200 },
        data: {
          label: meta.label,
          agentId: agent.agent_id,
          icon: meta.icon,
          skipped: userSkips[agent.agent_id] ?? agent.skipped,
          required: agent.required,
          isCheckpoint: agent.is_checkpoint,
          cost: agent.estimated_cost,
          timeSeconds: agent.estimated_time_seconds,
          model: agent.model,
          description: agent.description,
          canToggle: !agent.required,
        },
      }
    })
  }, [plan.agents, userSkips])

  // Build edges
  const initialEdges = useMemo((): Edge[] => {
    const edges: Edge[] = []
    for (const agent of plan.agents) {
      for (const dep of agent.dependencies) {
        const isSkipped = userSkips[agent.agent_id] || userSkips[dep]
        edges.push({
          id: `${dep}->${agent.agent_id}`,
          source: dep,
          target: agent.agent_id,
          type: 'smoothstep',
          animated: false,
          style: {
            stroke: isSkipped ? 'var(--text-tertiary)' : 'var(--border-primary)',
            strokeWidth: 2,
            opacity: isSkipped ? 0.3 : 1,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 16,
            height: 16,
            color: isSkipped ? 'var(--text-tertiary)' : 'var(--border-primary)',
          },
        })
      }
    }
    return edges
  }, [plan.agents, userSkips])

  const [nodes, , onNodesChange] = useNodesState(initialNodes)
  const [edges, , onEdgesChange] = useEdgesState(initialEdges)

  // Toggle skip for an agent
  const toggleAgent = (agentId: string) => {
    const agent = plan.agents.find(a => a.agent_id === agentId)
    if (!agent || agent.required) return
    setUserSkips(prev => ({ ...prev, [agentId]: !prev[agentId] }))
  }

  // Recalculate summary based on user toggles
  const activePlan = useMemo(() => {
    const active = plan.agents.filter(a => !userSkips[a.agent_id])
    const skipped = plan.agents.filter(a => userSkips[a.agent_id])
    const activeCost = active.reduce((sum, a) => sum + a.estimated_cost, 0)
    const activeTime = active.reduce((sum, a) => sum + a.estimated_time_seconds, 0)
    return {
      activeCount: active.length,
      skippedCount: skipped.length,
      activeCost,
      activeTime,
      checkpoints: active.filter(a => a.is_checkpoint).length,
    }
  }, [plan.agents, userSkips])

  const skippedAgentIds = Object.entries(userSkips)
    .filter(([, skipped]) => skipped)
    .map(([id]) => id)

  return (
    <div className="fixed inset-0 z-[200] flex flex-col"
         style={{ background: 'var(--background-primary)' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b"
           style={{ borderColor: 'var(--border-subtle)', background: 'var(--background-secondary)' }}>
        <div>
          <h2 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>
            Pipeline Execution Plan
          </h2>
          <p className="text-sm mt-0.5" style={{ color: 'var(--text-tertiary)' }}>
            Review and customize which agents will run before starting the build
          </p>
        </div>
        <button onClick={onCancel} className="p-2 rounded-lg hover:bg-white/10">
          <X className="w-5 h-5" style={{ color: 'var(--text-tertiary)' }} />
        </button>
      </div>

      {/* Summary bar */}
      <div className="flex items-center gap-6 px-6 py-3 border-b"
           style={{ borderColor: 'var(--border-subtle)', background: 'var(--background-secondary)' }}>
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4" style={{ color: 'var(--accent-primary)' }} />
          <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
            {activePlan.activeCount} agents
          </span>
          {activePlan.skippedCount > 0 && (
            <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
              ({activePlan.skippedCount} skipped)
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <DollarSign className="w-4 h-4" style={{ color: 'var(--accent-success)' }} />
          <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
            ${activePlan.activeCost.toFixed(2)}
          </span>
          <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
            ({Math.round(plan.summary.confidence * 100)}% confidence)
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4" style={{ color: 'var(--text-tertiary)' }} />
          <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
            {plan.summary.total_time_display}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4" style={{ color: 'var(--text-tertiary)' }} />
          <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
            {(plan.summary.total_tokens / 1000).toFixed(0)}K tokens
          </span>
        </div>
        {activePlan.checkpoints > 0 && (
          <div className="flex items-center gap-2">
            <Pause className="w-4 h-4" style={{ color: '#c084fc' }} />
            <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
              {activePlan.checkpoints} checkpoints
            </span>
          </div>
        )}
      </div>

      {/* Main content: DAG + agent list */}
      <div className="flex flex-1 overflow-hidden">
        {/* DAG visualization */}
        <div className="flex-1 relative">
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
            defaultEdgeOptions={{ type: 'smoothstep' }}
          >
            <Background color="var(--border-subtle)" gap={20} size={1} />
            <Controls showInteractive={false} className="dag-controls" />
            <MiniMap
              nodeColor={(n) => {
                const data = n.data as PlanNodeData
                if (data?.skipped) return 'var(--text-tertiary)'
                if (data?.isCheckpoint) return '#c084fc'
                if (data?.required) return 'var(--accent-error)'
                return 'var(--accent-primary)'
              }}
              maskColor="rgba(0,0,0,0.6)"
              className="dag-minimap"
            />
          </ReactFlow>

          {/* Legend */}
          <div className="absolute top-3 left-3 flex gap-3 px-3 py-2 rounded-lg text-xs"
               style={{ background: 'var(--background-secondary)', border: '1px solid var(--border-subtle)' }}>
            <LegendItem color="var(--accent-primary)" label="Active" />
            <LegendItem color="var(--accent-error)" label="Required" />
            <LegendItem color="#c084fc" label="Checkpoint" />
            <LegendItem color="var(--text-tertiary)" label="Skipped" />
          </div>
        </div>

        {/* Agent list sidebar */}
        <div className="w-80 border-l overflow-y-auto"
             style={{ borderColor: 'var(--border-subtle)', background: 'var(--background-secondary)' }}>
          <div className="px-4 py-3 border-b flex items-center justify-between"
               style={{ borderColor: 'var(--border-subtle)' }}>
            <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
              Agent List
            </span>
            <button onClick={() => setShowAgentList(!showAgentList)}
                    className="p-1 rounded hover:bg-white/10">
              {showAgentList ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          </div>

          {showAgentList && (
            <div className="divide-y" style={{ borderColor: 'var(--border-subtle)' }}>
              {plan.agents.map((agent, i) => {
                const meta = AGENT_META[agent.agent_id] || { label: agent.agent_id, icon: 'target' }
                const isSkipped = userSkips[agent.agent_id]

                return (
                  <div key={agent.agent_id}
                       className="px-4 py-3 flex items-start gap-3"
                       style={{ opacity: isSkipped ? 0.5 : 1, borderColor: 'var(--border-subtle)' }}>
                    {/* Toggle */}
                    <div className="pt-0.5">
                      {agent.required ? (
                        <div className="w-5 h-5 rounded flex items-center justify-center"
                             style={{ background: 'rgba(239,68,68,0.2)' }}
                             title="Required — cannot be skipped">
                          <AlertTriangle className="w-3 h-3" style={{ color: '#f87171' }} />
                        </div>
                      ) : (
                        <button
                          onClick={() => toggleAgent(agent.agent_id)}
                          className="w-5 h-5 rounded border flex items-center justify-center transition-colors"
                          style={{
                            borderColor: isSkipped ? 'var(--border-primary)' : 'var(--accent-primary)',
                            background: isSkipped ? 'transparent' : 'var(--accent-primary)',
                          }}
                          title={isSkipped ? 'Click to enable' : 'Click to skip'}
                        >
                          {!isSkipped && <CheckCircle2 className="w-3 h-3 text-white" />}
                        </button>
                      )}
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                          {i + 1}. {meta.label}
                        </span>
                        {agent.is_checkpoint && (
                          <Pause className="w-3 h-3 flex-shrink-0" style={{ color: '#c084fc' }} />
                        )}
                      </div>
                      <p className="text-xs mt-0.5 line-clamp-2" style={{ color: 'var(--text-tertiary)' }}>
                        {agent.description}
                      </p>
                      {!isSkipped && (
                        <div className="flex items-center gap-3 mt-1 text-xs" style={{ color: 'var(--text-tertiary)' }}>
                          <span>${agent.estimated_cost.toFixed(3)}</span>
                          <span>
                            {agent.estimated_time_seconds < 60
                              ? `${Math.round(agent.estimated_time_seconds)}s`
                              : `${Math.round(agent.estimated_time_seconds / 60)}m`}
                          </span>
                          {agent.model && (
                            <span className="truncate max-w-[100px]">
                              {agent.model.split('/').pop()}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* Footer actions */}
      <div className="flex items-center justify-between px-6 py-4 border-t"
           style={{ borderColor: 'var(--border-subtle)', background: 'var(--background-secondary)' }}>
        <div className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
          Toggle agents on/off in the sidebar. Required agents cannot be skipped.
        </div>
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="btn-ghost px-4 py-2"
          >
            Cancel
          </button>
          <button
            onClick={() => onApprove(skippedAgentIds)}
            disabled={isSubmitting}
            className="btn-iridescent flex items-center gap-2 px-6 py-2"
          >
            <Rocket className="w-4 h-4" />
            {isSubmitting ? 'Starting...' : `Approve Plan & Build ($${activePlan.activeCost.toFixed(2)})`}
          </button>
        </div>
      </div>
    </div>
  )
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-2.5 h-2.5 rounded-full" style={{ background: color }} />
      <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
    </div>
  )
}
