import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { 
  Mic, ChevronDown, ChevronUp, Globe, Smartphone, Monitor, 
  Chrome, Terminal, Server, Sparkles, ArrowRight, Zap, Shield, Crown,
  Figma, Info
} from 'lucide-react'
import { clsx } from 'clsx'

// All 10 supported project types
const PROJECT_TYPES = [
  { 
    id: 'web_simple', 
    label: 'Simple Website', 
    icon: Globe, 
    description: 'Landing pages, portfolios, blogs',
    costRange: { budget: '$1-3', balanced: '$5-10', premium: '$15-30' }
  },
  { 
    id: 'web_complex', 
    label: 'Web Application', 
    icon: Globe, 
    description: 'Dashboards, e-commerce, multi-page apps',
    costRange: { budget: '$3-8', balanced: '$10-20', premium: '$30-60' }
  },
  { 
    id: 'mobile_native_ios', 
    label: 'iOS Native App', 
    icon: Smartphone, 
    description: 'Swift/SwiftUI apps for iPhone/iPad',
    costRange: { budget: '$4-10', balanced: '$12-25', premium: '$40-80' }
  },
  { 
    id: 'mobile_cross_platform', 
    label: 'Cross-Platform Mobile', 
    icon: Smartphone, 
    description: 'React Native (Expo) or Flutter apps',
    costRange: { budget: '$3-8', balanced: '$10-20', premium: '$35-70' }
  },
  { 
    id: 'mobile_pwa', 
    label: 'Progressive Web App', 
    icon: Smartphone, 
    description: 'Installable web apps with offline support',
    costRange: { budget: '$2-5', balanced: '$6-12', premium: '$20-40' }
  },
  { 
    id: 'desktop_app', 
    label: 'Desktop Application', 
    icon: Monitor, 
    description: 'Electron, Tauri, or PyQt apps',
    costRange: { budget: '$3-8', balanced: '$8-18', premium: '$30-60' }
  },
  { 
    id: 'chrome_extension', 
    label: 'Chrome Extension', 
    icon: Chrome, 
    description: 'Browser extensions with manifest v3',
    costRange: { budget: '$1-3', balanced: '$4-8', premium: '$12-25' }
  },
  { 
    id: 'cli_tool', 
    label: 'CLI Tool', 
    icon: Terminal, 
    description: 'Command-line tools (Python/Node)',
    costRange: { budget: '$0.5-2', balanced: '$2-5', premium: '$8-15' }
  },
  { 
    id: 'python_api', 
    label: 'REST API', 
    icon: Server, 
    description: 'FastAPI or Flask REST APIs',
    costRange: { budget: '$1-4', balanced: '$5-12', premium: '$15-35' }
  },
  { 
    id: 'python_saas', 
    label: 'Full-Stack SaaS', 
    icon: Sparkles, 
    description: 'Complete Python SaaS with auth & billing',
    costRange: { budget: '$4-12', balanced: '$15-30', premium: '$50-100' }
  },
]

// Cost profile configurations
const COST_PROFILES = [
  { id: 'budget', label: 'Budget', icon: Zap, desc: 'Minimize cost', color: 'var(--accent-success)' },
  { id: 'balanced', label: 'Balanced', icon: Shield, desc: 'Quality & cost', color: 'var(--accent-primary)' },
  { id: 'premium', label: 'Premium', icon: Crown, desc: 'Maximum quality', color: 'var(--accent-warning)' },
]

// Keywords to detect project type from brief
const TYPE_KEYWORDS: Record<string, string[]> = {
  mobile_native_ios: ['ios', 'iphone', 'ipad', 'swift', 'swiftui', 'app store', 'native ios'],
  mobile_cross_platform: ['react native', 'flutter', 'expo', 'cross-platform', 'android and ios'],
  mobile_pwa: ['pwa', 'progressive web app', 'offline-first', 'installable'],
  desktop_app: ['desktop app', 'electron', 'tauri', 'windows app', 'mac app'],
  chrome_extension: ['chrome extension', 'browser extension', 'plugin'],
  cli_tool: ['cli', 'command line', 'terminal tool', 'command-line'],
  python_api: ['api', 'rest api', 'fastapi', 'flask api', 'backend api'],
  python_saas: ['saas', 'subscription', 'multi-tenant', 'billing'],
  web_complex: ['dashboard', 'admin', 'e-commerce', 'authentication', 'web app'],
  web_simple: ['landing page', 'portfolio', 'blog', 'simple website'],
}

export default function NewProject() {
  const navigate = useNavigate()
  const [brief, setBrief] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [name, setName] = useState('')
  const [costProfile, setCostProfile] = useState('balanced')
  const [referenceUrls, setReferenceUrls] = useState('')
  const [selectedType, setSelectedType] = useState<string | null>(null)
  const [detectedType, setDetectedType] = useState<string | null>(null)
  // Phase 10: Figma integration
  const [figmaUrl, setFigmaUrl] = useState('')

  // Detect project type from brief
  useEffect(() => {
    const briefLower = brief.toLowerCase()
    let detected: string | null = null
    
    for (const [type, keywords] of Object.entries(TYPE_KEYWORDS)) {
      if (keywords.some(keyword => briefLower.includes(keyword))) {
        detected = type
        break
      }
    }
    
    setDetectedType(detected)
    if (detected && !selectedType) {
      setSelectedType(detected)
    }
  }, [brief])

  const createProject = useMutation({
    mutationFn: api.createProject,
    onSuccess: (data) => {
      navigate(`/project/${data.id}`)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!brief.trim()) return

    createProject.mutate({
      brief,
      name: name || undefined,
      cost_profile: costProfile,
      project_type: selectedType || detectedType || 'web_simple',
      reference_urls: referenceUrls ? referenceUrls.split('\n').filter(Boolean) : undefined,
      // Phase 10: Figma integration
      figma_url: figmaUrl || undefined,
    })
  }

  const currentType = PROJECT_TYPES.find(t => t.id === (selectedType || detectedType))
  const costEstimate = currentType?.costRange[costProfile as keyof typeof currentType.costRange] || ''

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="mb-2">
        <h1 className="text-2xl lg:text-3xl font-bold" style={{ color: 'var(--text-primary)' }}>
          New Project
        </h1>
        <p className="mt-1" style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-base)' }}>
          Describe what you want to build
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        
        {/* Hero Input Card */}
        <div className="glass-card-elevated" style={{ padding: 0 }}>
          <div className="bloom-content">
            <textarea
              value={brief}
              onChange={(e) => setBrief(e.target.value)}
              placeholder="What do you want built? Describe your project in detail..."
              className="glass-textarea w-full border-0 bg-transparent"
              style={{ 
                minHeight: '160px',
                padding: 'var(--space-5)',
                fontSize: 'var(--text-lg)',
                resize: 'none'
              }}
              autoFocus
            />
            <div className="flex items-center justify-between p-4" 
                 style={{ borderTop: '1px solid var(--glass-border)' }}>
              <button
                type="button"
                className="btn-ghost"
                style={{ padding: 'var(--space-2)' }}
                title="Voice input"
              >
                <Mic className="w-5 h-5" style={{ color: 'var(--text-tertiary)' }} />
              </button>
              <div className="flex items-center gap-3">
                {detectedType && (
                  <span className="badge badge-info">
                    Detected: {PROJECT_TYPES.find(t => t.id === detectedType)?.label}
                  </span>
                )}
                <span style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-xs)' }}>
                  {brief.length} characters
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Project Type Selector */}
        <div className="glass-card">
          <h3 className="font-medium mb-4" style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
            Project Type
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            {PROJECT_TYPES.map((type) => {
              const Icon = type.icon
              const isSelected = selectedType === type.id || (!selectedType && detectedType === type.id)
              return (
                <button
                  key={type.id}
                  type="button"
                  onClick={() => setSelectedType(type.id)}
                  className={clsx(
                    'glass-card flex flex-col items-center gap-2 p-4 text-center transition-all',
                    isSelected && 'glass-card-iridescent'
                  )}
                  style={{
                    borderColor: isSelected ? 'var(--accent-primary)' : undefined,
                    background: isSelected ? 'rgba(32, 184, 205, 0.08)' : undefined
                  }}
                >
                  <Icon className="w-6 h-6" style={{ 
                    color: isSelected ? 'var(--accent-primary)' : 'var(--text-tertiary)' 
                  }} />
                  <span className="text-xs font-medium" style={{ 
                    color: isSelected ? 'var(--accent-primary)' : 'var(--text-secondary)' 
                  }}>
                    {type.label}
                  </span>
                </button>
              )
            })}
          </div>
          {currentType && (
            <p className="mt-4" style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-sm)' }}>
              {currentType.description}
            </p>
          )}
        </div>

        {/* Cost Profile Selector */}
        <div className="glass-card">
          <h3 className="font-medium mb-4" style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
            Cost Profile
          </h3>
          <div className="grid grid-cols-3 gap-3">
            {COST_PROFILES.map((profile) => {
              const Icon = profile.icon
              const isSelected = costProfile === profile.id
              return (
                <button
                  key={profile.id}
                  type="button"
                  onClick={() => setCostProfile(profile.id)}
                  className="glass-card text-center p-4 transition-all"
                  style={{
                    borderColor: isSelected ? profile.color : undefined,
                    background: isSelected ? `${profile.color}10` : undefined
                  }}
                >
                  <Icon className="w-5 h-5 mx-auto mb-2" style={{ 
                    color: isSelected ? profile.color : 'var(--text-tertiary)' 
                  }} />
                  <span className="block font-medium text-sm" style={{ 
                    color: isSelected ? profile.color : 'var(--text-primary)' 
                  }}>
                    {profile.label}
                  </span>
                  <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                    {profile.desc}
                  </span>
                </button>
              )
            })}
          </div>
          
          {/* Cost Estimate */}
          {costEstimate && (
            <div className="glass-card mt-4" style={{ 
              padding: 'var(--space-4)',
              background: 'var(--glass-bg-elevated)' 
            }}>
              <div className="flex justify-between items-center">
                <span style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
                  Estimated Cost
                </span>
                <span className="text-xl font-bold" style={{ color: 'var(--accent-primary)' }}>
                  {costEstimate}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Advanced Options Accordion */}
        <div className="glass-card" style={{ padding: 0 }}>
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="w-full flex items-center justify-between p-4 text-left"
          >
            <span className="font-medium" style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
              Advanced Options
            </span>
            {showAdvanced ? (
              <ChevronUp className="w-5 h-5" style={{ color: 'var(--text-tertiary)' }} />
            ) : (
              <ChevronDown className="w-5 h-5" style={{ color: 'var(--text-tertiary)' }} />
            )}
          </button>
          
          {showAdvanced && (
            <div className="p-4 pt-0 space-y-4" style={{ borderTop: '1px solid var(--glass-border)' }}>
              <div>
                <label className="block mb-2 font-medium" 
                       style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
                  Project Name (optional)
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="My Awesome Project"
                  className="glass-input"
                />
              </div>
              
              {/* Phase 10: Figma URL Input */}
              <div>
                <label className="flex items-center gap-2 mb-2 font-medium" 
                       style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
                  <Figma className="w-4 h-4" style={{ color: 'var(--accent-primary)' }} />
                  Figma Design URL (optional)
                  <div className="relative group">
                    <Info className="w-4 h-4 cursor-help" style={{ color: 'var(--text-tertiary)' }} />
                    <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block z-50">
                      <div className="glass-card p-3 text-xs" style={{ 
                        width: '250px', 
                        background: 'var(--background-tertiary)',
                        borderColor: 'var(--accent-primary)'
                      }}>
                        <p style={{ color: 'var(--text-primary)', marginBottom: '8px' }}>
                          <strong>Figma Integration</strong>
                        </p>
                        <p style={{ color: 'var(--text-secondary)' }}>
                          Paste a Figma file URL to extract design tokens, layout structure, and component definitions. 
                          Helps create more accurate code that matches your design.
                        </p>
                      </div>
                    </div>
                  </div>
                </label>
                <input
                  type="url"
                  value={figmaUrl}
                  onChange={(e) => setFigmaUrl(e.target.value)}
                  placeholder="https://www.figma.com/file/abc123/..."
                  className="glass-input"
                />
                {figmaUrl && (
                  <p className="mt-1 text-xs" style={{ color: 'var(--accent-success)' }}>
                    ✓ Figma design will be analyzed for colors, typography, and layout
                  </p>
                )}
              </div>
              
              <div>
                <label className="block mb-2 font-medium" 
                       style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
                  Reference URLs (one per line)
                </label>
                <textarea
                  value={referenceUrls}
                  onChange={(e) => setReferenceUrls(e.target.value)}
                  placeholder="https://example.com&#10;https://inspiration-site.com"
                  className="glass-textarea"
                  style={{ minHeight: '100px' }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Submit Button - Fixed on mobile */}
        <div className="fixed bottom-20 left-4 right-4 lg:static lg:bottom-auto z-40">
          <button
            type="submit"
            className="btn-iridescent w-full"
            disabled={!brief.trim() || createProject.isPending}
          >
            {createProject.isPending ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Starting...
              </span>
            ) : (
              <span className="flex items-center justify-center gap-2">
                Start Building
                <ArrowRight className="w-5 h-5" />
              </span>
            )}
          </button>
        </div>
      </form>
    </div>
  )
}
