/**
 * Phase 11B: Knowledge Base Page
 *
 * Displays knowledge base statistics, recent learnings, and user preferences.
 */
import { useState, useEffect, useRef } from 'react'
import { api, KnowledgeStats, KnowledgeEntry, PreferenceCreate } from '../lib/api'
import '../styles/KnowledgeBase.css'

function KnowledgeBase() {
  const [stats, setStats] = useState<KnowledgeStats | null>(null)
  const [entries, setEntries] = useState<KnowledgeEntry[]>([])
  const [searchResults, setSearchResults] = useState<KnowledgeEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [activeTab, setActiveTab] = useState<'overview' | 'search' | 'preferences' | 'upload'>('overview')
  const [entryTypeFilter, setEntryTypeFilter] = useState('')
  const [agentFilter, setAgentFilter] = useState('')

  // File upload state
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState<{ success: boolean; message: string } | null>(null)
  const [dragOver, setDragOver] = useState(false)

  // Text/manual entry state
  const [manualTitle, setManualTitle] = useState('')
  const [manualContent, setManualContent] = useState('')
  const [manualSaving, setManualSaving] = useState(false)

  // Preference form state
  const [showPreferenceForm, setShowPreferenceForm] = useState(false)
  const [newPreference, setNewPreference] = useState<PreferenceCreate>({
    title: '',
    preference: '',
    category: 'tech_stack',
  })

  useEffect(() => {
    loadData()
  }, [])

  useEffect(() => {
    if (activeTab === 'search' && (entryTypeFilter || agentFilter)) {
      loadEntries()
    }
  }, [entryTypeFilter, agentFilter])

  const loadData = async () => {
    setLoading(true)
    try {
      const [statsData, entriesData] = await Promise.all([
        api.getKnowledgeStats(),
        api.getKnowledgeEntries({ limit: 20 }),
      ])
      setStats(statsData)
      setEntries(entriesData)
    } catch (error) {
      console.error('Failed to load knowledge base data:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadEntries = async () => {
    try {
      const data = await api.getKnowledgeEntries({
        entry_type: entryTypeFilter || undefined,
        agent_name: agentFilter || undefined,
        limit: 50,
      })
      setEntries(data)
    } catch (error) {
      console.error('Failed to load entries:', error)
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    setSearching(true)
    try {
      const results = await api.searchKnowledge({
        query: searchQuery,
        limit: 20,
      })
      setSearchResults(results)
    } catch (error) {
      console.error('Search failed:', error)
    } finally {
      setSearching(false)
    }
  }

  const handleAddPreference = async () => {
    if (!newPreference.title || !newPreference.preference) return
    try {
      await api.storePreference(newPreference)
      setShowPreferenceForm(false)
      setNewPreference({ title: '', preference: '', category: 'tech_stack' })
      loadData() // Refresh
    } catch (error) {
      console.error('Failed to add preference:', error)
    }
  }

  const handleDeleteEntry = async (id: string) => {
    if (!confirm('Delete this knowledge entry?')) return
    try {
      await api.deleteKnowledgeEntry(id)
      setEntries(entries.filter(e => e.id !== id))
      loadData() // Refresh stats
    } catch (error) {
      console.error('Failed to delete entry:', error)
    }
  }

  const handleFileUpload = async (file: File) => {
    if (!file) return
    const ext = file.name.split('.').pop()?.toLowerCase()
    if (!['pdf', 'txt', 'md'].includes(ext || '')) {
      setUploadResult({ success: false, message: 'Only .pdf, .txt, and .md files are supported' })
      return
    }
    setUploading(true)
    setUploadResult(null)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const response = await fetch('/api/knowledge/upload', {
        method: 'POST',
        credentials: 'include',
        body: formData,
      })
      if (!response.ok) {
        const err = await response.json().catch(() => ({}))
        throw new Error(err.detail || 'Upload failed')
      }
      setUploadResult({ success: true, message: `"${file.name}" uploaded successfully` })
      loadData()
    } catch (error: any) {
      setUploadResult({ success: false, message: error.message })
    } finally {
      setUploading(false)
    }
  }

  const handleManualSave = async () => {
    if (!manualTitle.trim() || !manualContent.trim()) return
    setManualSaving(true)
    try {
      await api.storePreference({
        title: manualTitle.trim(),
        preference: manualContent.trim(),
        category: 'other',
      })
      setManualTitle('')
      setManualContent('')
      setUploadResult({ success: true, message: 'Entry saved to knowledge base' })
      loadData()
    } catch (error: any) {
      setUploadResult({ success: false, message: error.message })
    } finally {
      setManualSaving(false)
    }
  }

  const formatEntryType = (type: string) => {
    return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  }

  if (loading) {
    return (
      <div className="knowledge-base-page">
        <div className="loading-container">
          <div className="spinner" />
          <p>Loading knowledge base...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="knowledge-base-page">
      <header className="page-header">
        <h1>Knowledge Base</h1>
        <p className="subtitle">RAG-powered learning from past projects</p>
      </header>

      <div className="tabs">
        <button
          className={`tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button
          className={`tab ${activeTab === 'search' ? 'active' : ''}`}
          onClick={() => setActiveTab('search')}
        >
          Browse & Search
        </button>
        <button
          className={`tab ${activeTab === 'upload' ? 'active' : ''}`}
          onClick={() => setActiveTab('upload')}
        >
          Upload / Add
        </button>
        <button
          className={`tab ${activeTab === 'preferences' ? 'active' : ''}`}
          onClick={() => setActiveTab('preferences')}
        >
          Preferences
        </button>
      </div>

      {activeTab === 'overview' && stats && (
        <div className="overview-tab">
          <div className="stats-grid">
            <div className="stat-card">
              <h3>Total Entries</h3>
              <div className="stat-value">{stats.total_entries}</div>
            </div>
            <div className="stat-card">
              <h3>Avg Quality</h3>
              <div className="stat-value">{(stats.average_quality_score * 100).toFixed(0)}%</div>
            </div>
          </div>

          <div className="breakdown-section">
            <h2>Entries by Type</h2>
            <div className="breakdown-grid">
              {Object.entries(stats.entries_by_type).map(([type, count]) => (
                <div key={type} className="breakdown-item">
                  <span className="breakdown-label">{formatEntryType(type)}</span>
                  <span className="breakdown-value">{count}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="breakdown-section">
            <h2>Entries by Agent</h2>
            <div className="breakdown-grid">
              {Object.entries(stats.entries_by_agent).map(([agent, count]) => (
                <div key={agent} className="breakdown-item">
                  <span className="breakdown-label">{agent}</span>
                  <span className="breakdown-value">{count}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="recent-section">
            <h2>Recent Learnings</h2>
            <div className="entries-list">
              {stats.recent_entries.slice(0, 5).map((entry: any) => (
                <div key={entry.id} className="entry-card compact">
                  <div className="entry-header">
                    <span className="entry-type">{formatEntryType(entry.entry_type)}</span>
                    <span className="entry-date">
                      {new Date(entry.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <h4>{entry.title}</h4>
                  <p className="entry-content">{entry.content.substring(0, 150)}...</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'upload' && (
        <div className="upload-tab" style={{ maxWidth: 640 }}>
          {/* Status feedback */}
          {uploadResult && (
            <div className={`upload-result ${uploadResult.success ? 'success' : 'error'}`}
                 style={{ marginBottom: '1.5rem', padding: '0.75rem 1rem', borderRadius: '0.5rem',
                   background: uploadResult.success ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
                   border: `1px solid ${uploadResult.success ? '#22c55e40' : '#ef444440'}`,
                   color: uploadResult.success ? '#22c55e' : '#ef4444' }}>
              {uploadResult.message}
            </div>
          )}

          {/* File Upload */}
          <section style={{ marginBottom: '2rem' }}>
            <h2 style={{ marginBottom: '0.75rem', fontSize: '1rem', fontWeight: 600 }}>Upload File</h2>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
              Upload a PDF, TXT, or Markdown file. The content will be parsed and saved to the knowledge base.
            </p>
            <div
              className={`drop-zone ${dragOver ? 'drag-over' : ''}`}
              style={{ border: '2px dashed var(--glass-border)', borderRadius: '0.75rem', padding: '2.5rem 1rem',
                textAlign: 'center', cursor: 'pointer', transition: 'border-color 0.15s',
                borderColor: dragOver ? 'var(--accent-primary)' : undefined }}
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer.files[0]; if (f) handleFileUpload(f) }}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.txt,.md"
                style={{ display: 'none' }}
                onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFileUpload(f) }}
              />
              {uploading ? (
                <p style={{ color: 'var(--text-secondary)' }}>Uploading…</p>
              ) : (
                <>
                  <p style={{ fontWeight: 500, marginBottom: '0.25rem' }}>Drop file here or click to browse</p>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)' }}>PDF, TXT, MD — max 10 000 characters extracted</p>
                </>
              )}
            </div>
          </section>

          {/* Manual text entry */}
          <section>
            <h2 style={{ marginBottom: '0.75rem', fontSize: '1rem', fontWeight: 600 }}>Add Text Manually</h2>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
              Type or paste knowledge directly — coding preferences, guidelines, architecture notes, etc.
            </p>
            <input
              type="text"
              placeholder="Title (e.g. 'API Design Guidelines')"
              value={manualTitle}
              onChange={(e) => setManualTitle(e.target.value)}
              style={{ width: '100%', marginBottom: '0.75rem', padding: '0.625rem 0.875rem',
                borderRadius: '0.5rem', border: '1px solid var(--glass-border)',
                background: 'var(--glass-bg)', color: 'var(--text-primary)', fontSize: '0.875rem' }}
            />
            <textarea
              placeholder="Paste your knowledge here…"
              value={manualContent}
              onChange={(e) => setManualContent(e.target.value)}
              rows={8}
              style={{ width: '100%', marginBottom: '0.75rem', padding: '0.625rem 0.875rem',
                borderRadius: '0.5rem', border: '1px solid var(--glass-border)',
                background: 'var(--glass-bg)', color: 'var(--text-primary)', fontSize: '0.875rem',
                resize: 'vertical', fontFamily: 'inherit' }}
            />
            <button
              onClick={handleManualSave}
              disabled={manualSaving || !manualTitle.trim() || !manualContent.trim()}
              style={{ padding: '0.625rem 1.5rem', borderRadius: '0.5rem', fontWeight: 600,
                background: 'var(--accent-primary)', color: 'white', cursor: 'pointer',
                opacity: manualSaving ? 0.6 : 1, border: 'none' }}
            >
              {manualSaving ? 'Saving…' : 'Save to Knowledge Base'}
            </button>
          </section>
        </div>
      )}

      {activeTab === 'search' && (
        <div className="search-tab">
          <div className="search-bar">
            <input
              type="text"
              placeholder="Search knowledge base..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
            />
            <button onClick={handleSearch} disabled={searching}>
              {searching ? 'Searching...' : 'Search'}
            </button>
          </div>

          <div className="filters-row">
            <select
              value={entryTypeFilter}
              onChange={e => setEntryTypeFilter(e.target.value)}
            >
              <option value="">All Types</option>
              <option value="architecture_decision">Architecture Decisions</option>
              <option value="qa_finding">QA Findings</option>
              <option value="prompt_result">Prompt Results</option>
              <option value="code_pattern">Code Patterns</option>
              <option value="user_preference">User Preferences</option>
              <option value="design_token">Design Tokens</option>
              <option value="security_finding">Security Findings</option>
            </select>
            <select
              value={agentFilter}
              onChange={e => setAgentFilter(e.target.value)}
            >
              <option value="">All Agents</option>
              <option value="research">Research</option>
              <option value="architect">Architect</option>
              <option value="design_system">Design System</option>
              <option value="code_generation">Code Generation</option>
              <option value="qa_testing">QA Testing</option>
              <option value="security">Security</option>
              <option value="code_review">Code Review</option>
            </select>
          </div>

          <div className="entries-list">
            {(searchResults.length > 0 ? searchResults : entries).map(entry => (
              <div key={entry.id} className="entry-card">
                <div className="entry-header">
                  <span className="entry-type">{formatEntryType(entry.entry_type)}</span>
                  {entry.agent_name && (
                    <span className="entry-agent">{entry.agent_name}</span>
                  )}
                  {entry.quality_score && (
                    <span className="entry-quality">{(entry.quality_score * 100).toFixed(0)}%</span>
                  )}
                  {entry.similarity_score !== undefined && (
                    <span className="similarity-score">
                      {(entry.similarity_score * 100).toFixed(0)}% match
                    </span>
                  )}
                </div>
                <h4>{entry.title}</h4>
                <p className="entry-content">{entry.content}</p>
                <div className="entry-footer">
                  <div className="entry-meta">
                    {entry.project_type && (
                      <span className="meta-item">{entry.project_type}</span>
                    )}
                    {entry.industry && (
                      <span className="meta-item">{entry.industry}</span>
                    )}
                    <span className="meta-item">{entry.usage_count} uses</span>
                  </div>
                  <button
                    className="delete-btn"
                    onClick={() => handleDeleteEntry(entry.id)}
                    title="Delete entry"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'preferences' && (
        <div className="preferences-tab">
          <div className="preferences-header">
            <h2>User Preferences</h2>
            <button
              className="add-preference-btn"
              onClick={() => setShowPreferenceForm(true)}
            >
              + Add Preference
            </button>
          </div>

          {showPreferenceForm && (
            <div className="preference-form">
              <h3>Add New Preference</h3>
              <input
                type="text"
                placeholder="Title (e.g., 'Preferred CSS Framework')"
                value={newPreference.title}
                onChange={e => setNewPreference({ ...newPreference, title: e.target.value })}
              />
              <textarea
                placeholder="Preference details..."
                value={newPreference.preference}
                onChange={e => setNewPreference({ ...newPreference, preference: e.target.value })}
              />
              <select
                value={newPreference.category}
                onChange={e => setNewPreference({ ...newPreference, category: e.target.value })}
              >
                <option value="tech_stack">Tech Stack</option>
                <option value="design">Design</option>
                <option value="code_style">Code Style</option>
                <option value="deployment">Deployment</option>
                <option value="other">Other</option>
              </select>
              <div className="form-actions">
                <button onClick={() => setShowPreferenceForm(false)}>Cancel</button>
                <button className="primary" onClick={handleAddPreference}>Save</button>
              </div>
            </div>
          )}

          <div className="entries-list">
            {entries
              .filter(e => e.entry_type === 'user_preference')
              .map(entry => (
                <div key={entry.id} className="entry-card preference-card">
                  <div className="entry-header">
                    <span className="entry-type">Preference</span>
                    {entry.tags && entry.tags[0] && (
                      <span className="category-tag">{entry.tags[0]}</span>
                    )}
                  </div>
                  <h4>{entry.title}</h4>
                  <p className="entry-content">{entry.content}</p>
                  <div className="entry-footer">
                    <span className="meta-item">{entry.usage_count} uses</span>
                    <button
                      className="delete-btn"
                      onClick={() => handleDeleteEntry(entry.id)}
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              ))}
            {entries.filter(e => e.entry_type === 'user_preference').length === 0 && (
              <div className="empty-state">
                <p>No preferences saved yet</p>
                <p className="subtext">Add preferences to help agents make better decisions</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default KnowledgeBase
