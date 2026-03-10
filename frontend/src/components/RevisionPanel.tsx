import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Card } from '@/components/Card'
import { Button } from '@/components/Button'
import { Badge } from '@/components/Badge'
import { api } from '@/lib/api'
import { Revision, RevisionScope } from '@/types'
import { MessageSquarePlus, GitBranch, Clock, ChevronDown, ChevronUp, RotateCcw, AlertCircle } from 'lucide-react'
import { clsx } from 'clsx'

interface RevisionPanelProps {
  projectId: string
  revisions: Revision[]
  onRevisionCreated?: () => void
}

const SCOPE_INFO: Record<RevisionScope, { label: string; color: string; description: string }> = {
  small_tweak: { 
    label: 'Small Tweak', 
    color: 'bg-green-500/10 text-green-400',
    description: 'Minor changes like text updates, colors, bug fixes'
  },
  medium_feature: { 
    label: 'Medium Feature', 
    color: 'bg-yellow-500/10 text-yellow-400',
    description: 'New pages, components, or features'
  },
  major_addition: { 
    label: 'Major Addition', 
    color: 'bg-red-500/10 text-red-400',
    description: 'Significant new capabilities'
  },
}

export function RevisionPanel({ projectId, revisions, onRevisionCreated }: RevisionPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [showRequestForm, setShowRequestForm] = useState(false)
  const [revisionBrief, setRevisionBrief] = useState('')
  const queryClient = useQueryClient()

  const createRevision = useMutation({
    mutationFn: async (brief: string) => {
      const response = await fetch(`/api/projects/${projectId}/revisions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ revision_brief: brief }),
      })
      if (!response.ok) throw new Error('Failed to create revision')
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      setRevisionBrief('')
      setShowRequestForm(false)
      onRevisionCreated?.()
    },
  })

  const rollbackRevision = useMutation({
    mutationFn: async (revisionId: string) => {
      const response = await fetch(`/api/projects/${projectId}/revisions/${revisionId}/rollback`, {
        method: 'POST',
      })
      if (!response.ok) throw new Error('Failed to rollback')
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (revisionBrief.trim()) {
      createRevision.mutate(revisionBrief)
    }
  }

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <GitBranch className="w-5 h-5 text-accent-primary" />
          <h3 className="text-lg font-semibold text-text-primary">Revisions</h3>
          {revisions.length > 0 && (
            <span className="px-2 py-0.5 text-xs rounded-full bg-background-tertiary text-text-secondary">
              {revisions.length}
            </span>
          )}
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => setShowRequestForm(!showRequestForm)}
        >
          <MessageSquarePlus className="w-4 h-4 mr-1" />
          Request Changes
        </Button>
      </div>

      {/* Request Revision Form */}
      {showRequestForm && (
        <form onSubmit={handleSubmit} className="mb-4 p-4 bg-background-tertiary rounded-lg">
          <textarea
            value={revisionBrief}
            onChange={(e) => setRevisionBrief(e.target.value)}
            placeholder="Describe the changes you want to make..."
            className="w-full min-h-[100px] p-3 bg-background-input border border-border-subtle rounded-lg text-text-primary placeholder:text-text-tertiary resize-none focus:outline-none focus:ring-2 focus:ring-border-focus"
            autoFocus
          />
          <div className="flex justify-end gap-2 mt-3">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setShowRequestForm(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              isLoading={createRevision.isPending}
              disabled={!revisionBrief.trim()}
            >
              Submit Revision
            </Button>
          </div>
        </form>
      )}

      {/* Revision History */}
      {revisions.length > 0 ? (
        <div className="space-y-2">
          {/* Show first 3 or all if expanded */}
          {(isExpanded ? revisions : revisions.slice(0, 3)).map((revision) => (
            <div
              key={revision.id}
              className="p-3 bg-background-tertiary rounded-lg"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-text-primary truncate">
                    {revision.brief}
                  </p>
                  <div className="flex items-center gap-2 mt-1 flex-wrap">
                    <span className={clsx(
                      'px-2 py-0.5 text-xs rounded-full',
                      SCOPE_INFO[revision.scope_type]?.color || 'bg-gray-500/10 text-gray-400'
                    )}>
                      {SCOPE_INFO[revision.scope_type]?.label || revision.scope_type}
                    </span>
                    <span className={clsx(
                      'px-2 py-0.5 text-xs rounded-full',
                      revision.status === 'completed' ? 'bg-green-500/10 text-green-400' :
                      revision.status === 'in_progress' ? 'bg-blue-500/10 text-blue-400' :
                      revision.status === 'failed' ? 'bg-red-500/10 text-red-400' :
                      'bg-gray-500/10 text-gray-400'
                    )}>
                      {revision.status}
                    </span>
                    {revision.cost && (
                      <span className="text-xs text-text-tertiary">
                        ${revision.cost.toFixed(2)}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-text-tertiary flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {new Date(revision.created_at).toLocaleDateString()}
                  </span>
                  {revision.git_commit_sha && (
                    <button
                      onClick={() => rollbackRevision.mutate(revision.id)}
                      className="p-1 rounded hover:bg-background-secondary text-text-tertiary hover:text-text-primary"
                      title="Rollback to this version"
                    >
                      <RotateCcw className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
              
              {revision.git_commit_sha && (
                <p className="mt-1 text-xs text-text-tertiary font-mono">
                  {revision.git_commit_sha.substring(0, 7)}
                </p>
              )}
              
              {revision.errors && revision.errors.length > 0 && (
                <div className="mt-2 p-2 bg-red-500/10 rounded text-xs text-red-400 flex items-start gap-1">
                  <AlertCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                  {revision.errors[0]}
                </div>
              )}
            </div>
          ))}

          {revisions.length > 3 && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="w-full flex items-center justify-center gap-1 py-2 text-sm text-text-secondary hover:text-text-primary"
            >
              {isExpanded ? (
                <>
                  <ChevronUp className="w-4 h-4" />
                  Show Less
                </>
              ) : (
                <>
                  <ChevronDown className="w-4 h-4" />
                  Show {revisions.length - 3} More
                </>
              )}
            </button>
          )}
        </div>
      ) : (
        <p className="text-sm text-text-tertiary text-center py-4">
          No revisions yet. Request changes to modify your project.
        </p>
      )}
    </Card>
  )
}
