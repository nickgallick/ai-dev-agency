/**
 * ProjectMemory — Persistent project memory viewer/editor (#12)
 *
 * Displays and manages project-level decisions, preferences, context,
 * lessons, and constraints that persist across pipeline runs.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, MemoryEntry, MemoryEntryCreate } from '@/lib/api'
import {
  Brain,
  Plus,
  Trash2,
  Edit3,
  Save,
  X,
  BookOpen,
  Lightbulb,
  Settings2,
  AlertTriangle,
  FileText,
  ChevronDown,
  ChevronRight,
} from 'lucide-react'

interface ProjectMemoryProps {
  projectId: string
}

const CATEGORY_CONFIG: Record<string, { icon: typeof Brain; color: string; label: string }> = {
  decision: { icon: Lightbulb, color: '#fbbf24', label: 'Decisions' },
  preference: { icon: Settings2, color: '#60a5fa', label: 'Preferences' },
  context: { icon: FileText, color: '#4ade80', label: 'Context' },
  lesson: { icon: BookOpen, color: '#a78bfa', label: 'Lessons' },
  constraint: { icon: AlertTriangle, color: '#f87171', label: 'Constraints' },
}

export function ProjectMemory({ projectId }: ProjectMemoryProps) {
  const queryClient = useQueryClient()
  const [filterCategory, setFilterCategory] = useState<string | null>(null)
  const [showAddForm, setShowAddForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({
    decision: true,
    preference: true,
    context: true,
    lesson: true,
    constraint: true,
  })

  // Form state
  const [formCategory, setFormCategory] = useState('decision')
  const [formTitle, setFormTitle] = useState('')
  const [formContent, setFormContent] = useState('')
  const [editTitle, setEditTitle] = useState('')
  const [editContent, setEditContent] = useState('')

  const { data: entries = [], isLoading } = useQuery({
    queryKey: ['projectMemory', projectId, filterCategory],
    queryFn: () => api.getProjectMemory(projectId, filterCategory || undefined),
  })

  const createMutation = useMutation({
    mutationFn: (data: MemoryEntryCreate) => api.createMemoryEntry(projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projectMemory', projectId] })
      setShowAddForm(false)
      setFormTitle('')
      setFormContent('')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ entryId, data }: { entryId: string; data: Partial<MemoryEntryCreate> }) =>
      api.updateMemoryEntry(projectId, entryId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projectMemory', projectId] })
      setEditingId(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (entryId: string) => api.deleteMemoryEntry(projectId, entryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projectMemory', projectId] })
    },
  })

  const handleCreate = () => {
    if (!formTitle.trim() || !formContent.trim()) return
    createMutation.mutate({
      category: formCategory,
      title: formTitle.trim(),
      content: formContent.trim(),
    })
  }

  const handleUpdate = (entryId: string) => {
    if (!editTitle.trim() || !editContent.trim()) return
    updateMutation.mutate({
      entryId,
      data: { title: editTitle.trim(), content: editContent.trim() },
    })
  }

  const startEdit = (entry: MemoryEntry) => {
    setEditingId(entry.id)
    setEditTitle(entry.title)
    setEditContent(entry.content)
  }

  // Group entries by category
  const grouped: Record<string, MemoryEntry[]> = {}
  for (const entry of entries) {
    const cat = entry.category || 'context'
    if (!grouped[cat]) grouped[cat] = []
    grouped[cat].push(entry)
  }

  const toggleGroup = (cat: string) => {
    setExpandedGroups((prev) => ({ ...prev, [cat]: !prev[cat] }))
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4" style={{ color: 'var(--accent-primary)' }} />
          <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
            Project Memory
          </span>
          <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: 'var(--background-tertiary)', color: 'var(--text-tertiary)' }}>
            {entries.length} entries
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Category filter */}
          <div className="flex items-center gap-1">
            <button
              onClick={() => setFilterCategory(null)}
              className="px-2 py-1 rounded text-[10px] font-medium transition-colors"
              style={{
                background: !filterCategory ? 'var(--accent-primary-bg, rgba(59,130,246,0.15))' : 'transparent',
                color: !filterCategory ? 'var(--accent-primary)' : 'var(--text-tertiary)',
              }}
            >
              All
            </button>
            {Object.entries(CATEGORY_CONFIG).map(([key, cfg]) => (
              <button
                key={key}
                onClick={() => setFilterCategory(filterCategory === key ? null : key)}
                className="px-2 py-1 rounded text-[10px] font-medium transition-colors"
                style={{
                  background: filterCategory === key ? `${cfg.color}20` : 'transparent',
                  color: filterCategory === key ? cfg.color : 'var(--text-tertiary)',
                }}
              >
                {cfg.label}
              </button>
            ))}
          </div>

          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition-colors"
            style={{
              background: showAddForm ? 'rgba(74,222,128,0.15)' : 'var(--background-tertiary)',
              color: showAddForm ? '#4ade80' : 'var(--text-secondary)',
            }}
          >
            {showAddForm ? <X className="w-3 h-3" /> : <Plus className="w-3 h-3" />}
            {showAddForm ? 'Cancel' : 'Add'}
          </button>
        </div>
      </div>

      {/* Add form */}
      {showAddForm && (
        <div
          className="rounded-lg border p-3 space-y-2"
          style={{ background: 'var(--background-secondary)', borderColor: 'var(--border-subtle)' }}
        >
          <div className="flex items-center gap-2">
            <select
              value={formCategory}
              onChange={(e) => setFormCategory(e.target.value)}
              className="text-xs rounded px-2 py-1.5"
              style={{
                background: 'var(--background-tertiary)',
                color: 'var(--text-secondary)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              {Object.entries(CATEGORY_CONFIG).map(([key, cfg]) => (
                <option key={key} value={key}>
                  {cfg.label}
                </option>
              ))}
            </select>
            <input
              value={formTitle}
              onChange={(e) => setFormTitle(e.target.value)}
              placeholder="Title"
              className="flex-1 text-xs rounded px-2 py-1.5"
              style={{
                background: 'var(--background-tertiary)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-subtle)',
              }}
            />
          </div>
          <textarea
            value={formContent}
            onChange={(e) => setFormContent(e.target.value)}
            placeholder="Content — describe the decision, preference, context, or constraint..."
            rows={3}
            className="w-full text-xs rounded px-2 py-1.5 resize-y"
            style={{
              background: 'var(--background-tertiary)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-subtle)',
            }}
          />
          <div className="flex justify-end">
            <button
              onClick={handleCreate}
              disabled={!formTitle.trim() || !formContent.trim() || createMutation.isPending}
              className="flex items-center gap-1 px-3 py-1.5 rounded text-xs font-medium transition-colors disabled:opacity-50"
              style={{ background: 'rgba(74,222,128,0.15)', color: '#4ade80' }}
            >
              <Save className="w-3 h-3" />
              {createMutation.isPending ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      )}

      {/* Empty state */}
      {entries.length === 0 && !isLoading && (
        <div className="flex flex-col items-center justify-center py-10 text-center">
          <Brain className="w-8 h-8 mb-3" style={{ color: 'var(--text-tertiary)' }} />
          <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
            No project memory yet
          </p>
          <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
            Add decisions, preferences, and context that persist across pipeline runs
          </p>
        </div>
      )}

      {/* Grouped entries */}
      {filterCategory ? (
        // Flat list when filtering
        <div className="space-y-2">
          {entries.map((entry) => (
            <MemoryCard
              key={entry.id}
              entry={entry}
              isEditing={editingId === entry.id}
              editTitle={editTitle}
              editContent={editContent}
              onEditTitle={setEditTitle}
              onEditContent={setEditContent}
              onStartEdit={() => startEdit(entry)}
              onCancelEdit={() => setEditingId(null)}
              onSaveEdit={() => handleUpdate(entry.id)}
              onDelete={() => deleteMutation.mutate(entry.id)}
              isSaving={updateMutation.isPending}
              isDeleting={deleteMutation.isPending}
            />
          ))}
        </div>
      ) : (
        // Grouped view
        Object.entries(CATEGORY_CONFIG).map(([cat, cfg]) => {
          const catEntries = grouped[cat]
          if (!catEntries || catEntries.length === 0) return null
          const Icon = cfg.icon
          const isOpen = expandedGroups[cat]

          return (
            <div key={cat}>
              <button
                onClick={() => toggleGroup(cat)}
                className="flex items-center gap-2 mb-2 w-full text-left"
              >
                {isOpen ? (
                  <ChevronDown className="w-3.5 h-3.5" style={{ color: 'var(--text-tertiary)' }} />
                ) : (
                  <ChevronRight className="w-3.5 h-3.5" style={{ color: 'var(--text-tertiary)' }} />
                )}
                <Icon className="w-3.5 h-3.5" style={{ color: cfg.color }} />
                <span className="text-xs font-medium" style={{ color: cfg.color }}>
                  {cfg.label}
                </span>
                <span className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>
                  ({catEntries.length})
                </span>
              </button>
              {isOpen && (
                <div className="space-y-2 ml-5">
                  {catEntries.map((entry) => (
                    <MemoryCard
                      key={entry.id}
                      entry={entry}
                      isEditing={editingId === entry.id}
                      editTitle={editTitle}
                      editContent={editContent}
                      onEditTitle={setEditTitle}
                      onEditContent={setEditContent}
                      onStartEdit={() => startEdit(entry)}
                      onCancelEdit={() => setEditingId(null)}
                      onSaveEdit={() => handleUpdate(entry.id)}
                      onDelete={() => deleteMutation.mutate(entry.id)}
                      isSaving={updateMutation.isPending}
                      isDeleting={deleteMutation.isPending}
                    />
                  ))}
                </div>
              )}
            </div>
          )
        })
      )}
    </div>
  )
}

// ── Memory card ───────────────────────────────────────────────────

interface MemoryCardProps {
  entry: MemoryEntry
  isEditing: boolean
  editTitle: string
  editContent: string
  onEditTitle: (v: string) => void
  onEditContent: (v: string) => void
  onStartEdit: () => void
  onCancelEdit: () => void
  onSaveEdit: () => void
  onDelete: () => void
  isSaving: boolean
  isDeleting: boolean
}

function MemoryCard({
  entry,
  isEditing,
  editTitle,
  editContent,
  onEditTitle,
  onEditContent,
  onStartEdit,
  onCancelEdit,
  onSaveEdit,
  onDelete,
  isSaving,
  isDeleting,
}: MemoryCardProps) {
  const cfg = CATEGORY_CONFIG[entry.category] || CATEGORY_CONFIG.context
  const Icon = cfg.icon

  if (isEditing) {
    return (
      <div
        className="rounded-lg border p-3 space-y-2"
        style={{ background: 'var(--background-secondary)', borderColor: cfg.color + '40' }}
      >
        <input
          value={editTitle}
          onChange={(e) => onEditTitle(e.target.value)}
          className="w-full text-xs rounded px-2 py-1.5 font-medium"
          style={{
            background: 'var(--background-tertiary)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-subtle)',
          }}
        />
        <textarea
          value={editContent}
          onChange={(e) => onEditContent(e.target.value)}
          rows={3}
          className="w-full text-xs rounded px-2 py-1.5 resize-y"
          style={{
            background: 'var(--background-tertiary)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-subtle)',
          }}
        />
        <div className="flex justify-end gap-2">
          <button
            onClick={onCancelEdit}
            className="px-2 py-1 rounded text-[10px] font-medium"
            style={{ color: 'var(--text-tertiary)' }}
          >
            Cancel
          </button>
          <button
            onClick={onSaveEdit}
            disabled={isSaving}
            className="flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium disabled:opacity-50"
            style={{ background: 'rgba(74,222,128,0.15)', color: '#4ade80' }}
          >
            <Save className="w-3 h-3" />
            Save
          </button>
        </div>
      </div>
    )
  }

  return (
    <div
      className="rounded-lg border p-3 group"
      style={{ background: 'var(--background-secondary)', borderColor: 'var(--border-subtle)' }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2 min-w-0">
          <Icon className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" style={{ color: cfg.color }} />
          <div className="min-w-0">
            <p className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>
              {entry.title}
            </p>
            <p className="text-xs mt-1 whitespace-pre-wrap" style={{ color: 'var(--text-secondary)' }}>
              {entry.content}
            </p>
            <div className="flex items-center gap-3 mt-1.5">
              {entry.agent_name && (
                <span className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>
                  by {entry.agent_name}
                </span>
              )}
              {entry.usage_count > 0 && (
                <span className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>
                  used {entry.usage_count}x
                </span>
              )}
              {entry.created_at && (
                <span className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>
                  {new Date(entry.created_at).toLocaleDateString()}
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
          <button
            onClick={onStartEdit}
            className="p-1 rounded hover:opacity-70"
            style={{ color: 'var(--text-tertiary)' }}
            title="Edit"
          >
            <Edit3 className="w-3 h-3" />
          </button>
          <button
            onClick={onDelete}
            disabled={isDeleting}
            className="p-1 rounded hover:opacity-70 disabled:opacity-50"
            style={{ color: '#f87171' }}
            title="Delete"
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      </div>
    </div>
  )
}
