import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { Card } from '@/components/Card'
import { Button } from '@/components/Button'
import { Input } from '@/components/Input'
import { api } from '@/lib/api'
import { Mic, ChevronDown, ChevronUp, Globe, Smartphone, Monitor, Chrome, Terminal, Server, Sparkles } from 'lucide-react'
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
    // Auto-select if not manually selected
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
    })
  }

  const currentType = PROJECT_TYPES.find(t => t.id === (selectedType || detectedType))
  const costEstimate = currentType?.costRange[costProfile as keyof typeof currentType.costRange] || ''

  return (
    <div className="space-y-6 pb-24 lg:pb-0">
      <div>
        <h2 className="text-2xl font-semibold text-text-primary">New Project</h2>
        <p className="text-text-secondary mt-1">Describe what you want to build</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Main Input - Perplexity-style */}
        <Card padding="none">
          <div className="relative">
            <textarea
              value={brief}
              onChange={(e) => setBrief(e.target.value)}
              placeholder="What do you want built? Describe your project in detail..."
              className="w-full min-h-[150px] p-4 bg-transparent text-text-primary placeholder:text-text-tertiary resize-none focus:outline-none text-base"
              autoFocus
            />
            <div className="flex items-center justify-between p-3 border-t border-border-subtle">
              <button
                type="button"
                className="p-2 rounded-lg hover:bg-background-tertiary text-text-secondary"
                title="Voice input"
              >
                <Mic className="w-5 h-5" />
              </button>
              <div className="flex items-center gap-3">
                {detectedType && (
                  <span className="text-xs px-2 py-1 rounded-full bg-accent-primary/10 text-accent-primary">
                    Detected: {PROJECT_TYPES.find(t => t.id === detectedType)?.label}
                  </span>
                )}
                <span className="text-xs text-text-tertiary">
                  {brief.length} characters
                </span>
              </div>
            </div>
          </div>
        </Card>

        {/* Project Type Selector */}
        <Card>
          <h3 className="text-sm font-medium text-text-secondary mb-3">Project Type</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
            {PROJECT_TYPES.map((type) => {
              const Icon = type.icon
              const isSelected = selectedType === type.id || (!selectedType && detectedType === type.id)
              return (
                <button
                  key={type.id}
                  type="button"
                  onClick={() => setSelectedType(type.id)}
                  className={clsx(
                    'flex flex-col items-center gap-2 p-3 rounded-lg border transition-all text-center',
                    isSelected
                      ? 'border-accent-primary bg-accent-primary/10'
                      : 'border-border-subtle hover:border-border-focus'
                  )}
                >
                  <Icon className={clsx(
                    'w-5 h-5',
                    isSelected ? 'text-accent-primary' : 'text-text-tertiary'
                  )} />
                  <span className={clsx(
                    'text-xs font-medium',
                    isSelected ? 'text-accent-primary' : 'text-text-secondary'
                  )}>
                    {type.label}
                  </span>
                </button>
              )
            })}
          </div>
          {currentType && (
            <p className="mt-3 text-xs text-text-tertiary">
              {currentType.description}
            </p>
          )}
        </Card>

        {/* Cost Profile Selector */}
        <Card>
          <h3 className="text-sm font-medium text-text-secondary mb-3">Cost Profile</h3>
          <div className="grid grid-cols-3 gap-2">
            {[
              { id: 'budget', label: 'Budget', desc: 'Minimize cost' },
              { id: 'balanced', label: 'Balanced', desc: 'Quality & cost' },
              { id: 'premium', label: 'Premium', desc: 'Maximum quality' },
            ].map((profile) => (
              <button
                key={profile.id}
                type="button"
                onClick={() => setCostProfile(profile.id)}
                className={clsx(
                  'px-4 py-3 rounded-lg text-sm border transition-colors text-center',
                  costProfile === profile.id
                    ? 'border-accent-primary bg-accent-primary/10'
                    : 'border-border-subtle hover:border-border-focus'
                )}
              >
                <span className={clsx(
                  'font-medium block',
                  costProfile === profile.id ? 'text-accent-primary' : 'text-text-primary'
                )}>
                  {profile.label}
                </span>
                <span className="text-xs text-text-tertiary">{profile.desc}</span>
              </button>
            ))}
          </div>
          {costEstimate && (
            <div className="mt-3 p-3 bg-background-tertiary rounded-lg">
              <div className="flex justify-between items-center">
                <span className="text-sm text-text-secondary">Estimated Cost</span>
                <span className="text-lg font-semibold text-accent-primary">{costEstimate}</span>
              </div>
            </div>
          )}
        </Card>

        {/* Advanced Options Accordion */}
        <Card padding="none">
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="w-full flex items-center justify-between p-4 text-left"
          >
            <span className="text-sm font-medium text-text-secondary">Advanced Options</span>
            {showAdvanced ? (
              <ChevronUp className="w-5 h-5 text-text-tertiary" />
            ) : (
              <ChevronDown className="w-5 h-5 text-text-tertiary" />
            )}
          </button>
          
          {showAdvanced && (
            <div className="p-4 pt-0 space-y-4 border-t border-border-subtle">
              <Input
                label="Project Name (optional)"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="My Awesome Project"
              />
              
              <div className="space-y-1.5">
                <label className="block text-sm font-medium text-text-secondary">
                  Reference URLs (one per line)
                </label>
                <textarea
                  value={referenceUrls}
                  onChange={(e) => setReferenceUrls(e.target.value)}
                  placeholder="https://example.com\nhttps://inspiration-site.com"
                  className="w-full px-4 py-2.5 bg-background-input border border-border-subtle rounded-[10px] text-text-primary placeholder:text-text-tertiary resize-none focus:outline-none focus:ring-2 focus:ring-border-focus h-24"
                />
              </div>
            </div>
          )}
        </Card>

        {/* Submit Button - Fixed on mobile */}
        <div className="fixed bottom-20 left-4 right-4 lg:static lg:bottom-auto">
          <Button
            type="submit"
            size="lg"
            className="w-full"
            loading={createProject.isPending}
            disabled={!brief.trim()}
          >
            Start Building
          </Button>
        </div>
      </form>
    </div>
  )
}
