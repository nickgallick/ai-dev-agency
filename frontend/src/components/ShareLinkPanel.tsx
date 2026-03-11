/**
 * ShareLinkPanel — Shareable preview links for stakeholder review (#22)
 *
 * Create, manage, and share read-only signed URLs for project output.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, ShareLinkData } from '@/lib/api'
import {
  Share2,
  Link,
  Copy,
  Check,
  Trash2,
  Eye,
  Clock,
  Plus,
  X,
  ExternalLink,
  Shield,
} from 'lucide-react'

interface ShareLinkPanelProps {
  projectId: string
}

export function ShareLinkPanel({ projectId }: ShareLinkPanelProps) {
  const queryClient = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [label, setLabel] = useState('')
  const [expiryDays, setExpiryDays] = useState(7)
  const [includeOutputs, setIncludeOutputs] = useState(true)
  const [includeCode, setIncludeCode] = useState(true)
  const [includeQa, setIncludeQa] = useState(true)

  const { data } = useQuery({
    queryKey: ['shareLinks', projectId],
    queryFn: () => api.getShareLinks(projectId),
  })

  const createMutation = useMutation({
    mutationFn: () => api.createShareLink(projectId, {
      expires_in_days: expiryDays,
      include_outputs: includeOutputs,
      include_code: includeCode,
      include_qa: includeQa,
      label: label || undefined,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shareLinks', projectId] })
      setShowCreate(false)
      setLabel('')
    },
  })

  const revokeMutation = useMutation({
    mutationFn: (shareId: string) => api.revokeShareLink(projectId, shareId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shareLinks', projectId] })
    },
  })

  const links = (data?.links || []).filter((l: ShareLinkData) => l.is_active)
  const revokedLinks = (data?.links || []).filter((l: ShareLinkData) => !l.is_active)

  const copyToClipboard = (url: string, id: string) => {
    navigator.clipboard.writeText(url)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const isExpired = (expiresAt: string) => new Date(expiresAt) < new Date()

  return (
    <div className="flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Share2 className="w-4 h-4" style={{ color: 'var(--accent-primary)' }} />
          <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
            Share Links
          </span>
          <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: 'var(--background-tertiary)', color: 'var(--text-tertiary)' }}>
            {links.length} active
          </span>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-1 px-2 py-1 rounded text-xs font-medium"
          style={{
            background: showCreate ? 'rgba(74,222,128,0.15)' : 'var(--background-tertiary)',
            color: showCreate ? '#4ade80' : 'var(--text-secondary)',
          }}
        >
          {showCreate ? <X className="w-3 h-3" /> : <Plus className="w-3 h-3" />}
          {showCreate ? 'Cancel' : 'New Link'}
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div
          className="rounded-lg border p-3 space-y-2"
          style={{ background: 'var(--background-secondary)', borderColor: 'var(--border-subtle)' }}
        >
          <input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="Label (e.g., 'For client review')"
            className="w-full text-xs rounded px-2 py-1.5"
            style={{
              background: 'var(--background-tertiary)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-subtle)',
            }}
          />
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-1.5">
              <span className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>Expires in</span>
              <select
                value={expiryDays}
                onChange={(e) => setExpiryDays(Number(e.target.value))}
                className="text-xs rounded px-1.5 py-1"
                style={{
                  background: 'var(--background-tertiary)',
                  color: 'var(--text-secondary)',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <option value={1}>1 day</option>
                <option value={7}>7 days</option>
                <option value={30}>30 days</option>
                <option value={90}>90 days</option>
              </select>
            </div>
            <label className="flex items-center gap-1 text-[10px] cursor-pointer" style={{ color: 'var(--text-tertiary)' }}>
              <input type="checkbox" checked={includeOutputs} onChange={(e) => setIncludeOutputs(e.target.checked)} className="rounded" />
              Outputs
            </label>
            <label className="flex items-center gap-1 text-[10px] cursor-pointer" style={{ color: 'var(--text-tertiary)' }}>
              <input type="checkbox" checked={includeCode} onChange={(e) => setIncludeCode(e.target.checked)} className="rounded" />
              Code
            </label>
            <label className="flex items-center gap-1 text-[10px] cursor-pointer" style={{ color: 'var(--text-tertiary)' }}>
              <input type="checkbox" checked={includeQa} onChange={(e) => setIncludeQa(e.target.checked)} className="rounded" />
              QA Report
            </label>
          </div>
          <div className="flex justify-end">
            <button
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending}
              className="flex items-center gap-1 px-3 py-1.5 rounded text-xs font-medium disabled:opacity-50"
              style={{ background: 'rgba(59,130,246,0.15)', color: 'var(--accent-primary)' }}
            >
              <Link className="w-3 h-3" />
              {createMutation.isPending ? 'Creating...' : 'Create Link'}
            </button>
          </div>
        </div>
      )}

      {/* Active links */}
      {links.length > 0 && (
        <div className="space-y-2">
          {links.map((link: ShareLinkData) => {
            const expired = isExpired(link.expires_at)
            return (
              <div
                key={link.id}
                className="rounded-lg border p-3 group"
                style={{
                  background: 'var(--background-secondary)',
                  borderColor: expired ? 'rgba(251,191,36,0.3)' : 'var(--border-subtle)',
                  opacity: expired ? 0.7 : 1,
                }}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <Shield className="w-3.5 h-3.5 flex-shrink-0" style={{ color: expired ? '#fbbf24' : '#4ade80' }} />
                    <span className="text-xs font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                      {link.label || `Share link ${link.id.slice(0, 6)}`}
                    </span>
                    {expired && (
                      <span className="text-[10px] px-1 py-0.5 rounded flex-shrink-0" style={{ background: 'rgba(251,191,36,0.15)', color: '#fbbf24' }}>
                        expired
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {link.share_url && (
                      <>
                        <button
                          onClick={() => copyToClipboard(link.share_url, link.id)}
                          className="p-1 rounded hover:opacity-70"
                          style={{ color: 'var(--text-tertiary)' }}
                          title="Copy link"
                        >
                          {copiedId === link.id ? <Check className="w-3 h-3" style={{ color: '#4ade80' }} /> : <Copy className="w-3 h-3" />}
                        </button>
                        <a
                          href={link.share_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-1 rounded hover:opacity-70"
                          style={{ color: 'var(--text-tertiary)' }}
                          title="Open link"
                        >
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      </>
                    )}
                    <button
                      onClick={() => revokeMutation.mutate(link.id)}
                      disabled={revokeMutation.isPending}
                      className="p-1 rounded hover:opacity-70 disabled:opacity-50"
                      style={{ color: '#f87171' }}
                      title="Revoke"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>
                <div className="flex items-center gap-3 mt-1.5 text-[10px]" style={{ color: 'var(--text-tertiary)' }}>
                  <span className="flex items-center gap-1">
                    <Eye className="w-3 h-3" />
                    {link.view_count} views
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    Expires {new Date(link.expires_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Empty state */}
      {links.length === 0 && !showCreate && (
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <Share2 className="w-6 h-6 mb-2" style={{ color: 'var(--text-tertiary)' }} />
          <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
            Create signed links to share project output with stakeholders
          </p>
        </div>
      )}
    </div>
  )
}
