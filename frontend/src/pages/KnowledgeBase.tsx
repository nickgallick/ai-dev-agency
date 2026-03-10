/**
 * Phase 11B: Knowledge Base Page
 * 
 * Displays knowledge base statistics, recent learnings, and user preferences.
 */
import { useState, useEffect } from 'react'
import { api, KnowledgeStats, KnowledgeEntry, PreferenceCreate } from '../lib/api'
import '../styles/KnowledgeBase.css'

function KnowledgeBase() {
  const [stats, setStats] = useState<KnowledgeStats | null>(null)
  const [entries, setEntries] = useState<KnowledgeEntry[]>([])
  const [searchResults, setSearchResults] = useState<KnowledgeEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [activeTab, setActiveTab] = useState<'overview' | 'search' | 'preferences'>('overview')
  const [entryTypeFilter, setEntryTypeFilter] = useState('')
  const [agentFilter, setAgentFilter] = useState('')
  
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
