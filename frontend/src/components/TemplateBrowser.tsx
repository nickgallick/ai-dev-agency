/**
 * Phase 11B: Template Browser Component
 * 
 * Displays project templates in a grid with filtering and search.
 */
import { useState, useEffect } from 'react'
import { api, ProjectTemplate } from '../lib/api'
import './TemplateBrowser.css'

interface TemplateBrowserProps {
  isOpen: boolean
  onClose: () => void
  onSelectTemplate: (template: ProjectTemplate) => void
}

export function TemplateBrowser({ isOpen, onClose, onSelectTemplate }: TemplateBrowserProps) {
  const [templates, setTemplates] = useState<ProjectTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [projectTypeFilter, setProjectTypeFilter] = useState<string>('')
  const [industryFilter, setIndustryFilter] = useState<string>('')

  const projectTypes = [
    { value: '', label: 'All Types' },
    { value: 'web_simple', label: 'Simple Website' },
    { value: 'web_complex', label: 'Complex Web App' },
    { value: 'mobile_native_ios', label: 'iOS App' },
    { value: 'mobile_native_android', label: 'Android App' },
    { value: 'mobile_cross_platform', label: 'Cross-Platform Mobile' },
    { value: 'saas', label: 'SaaS' },
    { value: 'dashboard', label: 'Dashboard' },
    { value: 'cli', label: 'CLI Tool' },
    { value: 'desktop', label: 'Desktop App' },
    { value: 'api_backend', label: 'API/Backend' },
  ]

  useEffect(() => {
    if (isOpen) {
      loadTemplates()
    }
  }, [isOpen, projectTypeFilter, industryFilter, search])

  const loadTemplates = async () => {
    setLoading(true)
    try {
      const data = await api.getTemplates({
        project_type: projectTypeFilter || undefined,
        industry: industryFilter || undefined,
        search: search || undefined,
        limit: 50,
      })
      setTemplates(data)
    } catch (error) {
      console.error('Failed to load templates:', error)
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="template-browser-overlay" onClick={onClose}>
      <div className="template-browser-modal" onClick={e => e.stopPropagation()}>
        <div className="template-browser-header">
          <h2>Start from Template</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="template-browser-filters">
          <input
            type="text"
            placeholder="Search templates..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="search-input"
          />
          <select
            value={projectTypeFilter}
            onChange={e => setProjectTypeFilter(e.target.value)}
            className="filter-select"
          >
            {projectTypes.map(type => (
              <option key={type.value} value={type.value}>{type.label}</option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Industry..."
            value={industryFilter}
            onChange={e => setIndustryFilter(e.target.value)}
            className="filter-input"
          />
        </div>

        <div className="template-browser-content">
          {loading ? (
            <div className="loading-state">
              <div className="spinner" />
              <p>Loading templates...</p>
            </div>
          ) : templates.length === 0 ? (
            <div className="empty-state">
              <p>No templates found</p>
              <p className="subtext">Try adjusting your filters or create a new project from scratch</p>
            </div>
          ) : (
            <div className="template-grid">
              {templates.map(template => (
                <div
                  key={template.id}
                  className="template-card"
                  onClick={() => onSelectTemplate(template)}
                >
                  <div className="template-thumbnail">
                    {template.thumbnail_url ? (
                      <img src={template.thumbnail_url} alt={template.name} />
                    ) : (
                      <div className="placeholder-thumbnail">
                        <span className="icon">📄</span>
                      </div>
                    )}
                    {template.is_auto_generated && (
                      <span className="auto-badge">Auto</span>
                    )}
                  </div>
                  <div className="template-info">
                    <h3>{template.name}</h3>
                    <p className="template-description">
                      {template.description || 'No description'}
                    </p>
                    <div className="template-meta">
                      <span className="project-type-badge">{template.project_type}</span>
                      {template.industry && (
                        <span className="industry-badge">{template.industry}</span>
                      )}
                    </div>
                    <div className="template-stats">
                      {template.qa_score !== null && (
                        <span className="stat">
                          <span className="stat-icon">⭐</span>
                          {(template.qa_score * 100).toFixed(0)}%
                        </span>
                      )}
                      <span className="stat">
                        <span className="stat-icon">📊</span>
                        {template.total_usage_count} uses
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default TemplateBrowser
