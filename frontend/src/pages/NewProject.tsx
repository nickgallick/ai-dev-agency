/**
 * Phase 11A: Smart Adaptive Intake System
 * Phase 11B: Template Browser Integration
 * Complete rewrite of NewProject page with multi-step glassmorphic form
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api, BriefAnalysis, Preset, ProjectTemplate } from '@/lib/api'
import VoiceInput from '@/components/VoiceInput'
import TemplateBrowser from '@/components/TemplateBrowser'
import { 
  Globe, Smartphone, Monitor, Chrome, Terminal, Server, Sparkles, 
  ArrowRight, Zap, Shield, Crown, ChevronDown, ChevronUp, Save,
  Figma, Info, AlertCircle, Check, Plus, X, Palette, Settings2,
  Rocket, FileCode, Layers, Database, Mail, CreditCard, Users,
  Bell, Search, Upload, MessageSquare, Moon, Sun, LayoutTemplate
} from 'lucide-react'
import { clsx } from 'clsx'

// ============ Constants ============

const PROJECT_TYPES = [
  { id: 'web_simple', label: 'Simple Website', icon: Globe, description: 'Landing pages, portfolios, blogs' },
  { id: 'web_complex', label: 'Web Application', icon: Globe, description: 'Dashboards, e-commerce, multi-page apps' },
  { id: 'mobile_native_ios', label: 'iOS Native', icon: Smartphone, description: 'Swift/SwiftUI apps' },
  { id: 'mobile_cross_platform', label: 'Cross-Platform Mobile', icon: Smartphone, description: 'React Native or Flutter' },
  { id: 'mobile_pwa', label: 'PWA', icon: Smartphone, description: 'Progressive Web App' },
  { id: 'desktop_app', label: 'Desktop App', icon: Monitor, description: 'Electron, Tauri, PyQt' },
  { id: 'chrome_extension', label: 'Chrome Extension', icon: Chrome, description: 'Manifest v3' },
  { id: 'cli_tool', label: 'CLI Tool', icon: Terminal, description: 'Python/Node CLI' },
  { id: 'python_api', label: 'REST API', icon: Server, description: 'FastAPI or Flask' },
  { id: 'python_saas', label: 'Full-Stack SaaS', icon: Sparkles, description: 'Complete SaaS solution' },
]

const COST_PROFILES = [
  { id: 'budget', label: 'Budget', icon: Zap, desc: 'Minimize cost', color: '#34D399' },
  { id: 'balanced', label: 'Balanced', icon: Shield, desc: 'Quality & cost', color: '#20B8CD' },
  { id: 'premium', label: 'Premium', icon: Crown, desc: 'Maximum quality', color: '#FBBF24' },
]

const INDUSTRIES = [
  'Healthcare', 'Fintech', 'E-commerce', 'Education', 'Real Estate',
  'Food & Delivery', 'Travel', 'Fitness', 'Social', 'Productivity', 'Other'
]

const DESIGN_STYLES = [
  { id: 'minimal', label: 'Minimal', desc: 'Clean and simple' },
  { id: 'playful', label: 'Playful', desc: 'Fun and colorful' },
  { id: 'corporate', label: 'Corporate', desc: 'Professional and serious' },
  { id: 'bold', label: 'Bold', desc: 'Strong and impactful' },
  { id: 'elegant', label: 'Elegant', desc: 'Sophisticated and refined' },
]

const COMMON_FEATURES = [
  { id: 'authentication', label: 'Authentication', icon: Users },
  { id: 'dashboard', label: 'Dashboard', icon: Layers },
  { id: 'payments', label: 'Payments', icon: CreditCard },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'search', label: 'Search', icon: Search },
  { id: 'file_upload', label: 'File Upload', icon: Upload },
  { id: 'chat', label: 'Chat/Messaging', icon: MessageSquare },
  { id: 'email', label: 'Email', icon: Mail },
  { id: 'database', label: 'Database', icon: Database },
  { id: 'api', label: 'API Integration', icon: FileCode },
]

const STORAGE_KEY = 'ai-dev-agency-new-project-draft'

// ============ Form State Interface ============

interface FormState {
  // Step 1: Basics
  brief: string
  projectType: string | null
  costProfile: string
  
  // Step 2: Conditional
  industry: string
  targetAudience: string
  referenceUrls: string[]
  selectedFeatures: string[]
  pages: string[]
  
  // Mobile options
  mobilePlatforms: string[]
  mobileFramework: string
  submitToStores: boolean
  
  // Web simple options
  numPages: number
  sections: string[]
  includeContactForm: boolean
  includeBlog: boolean
  
  // CLI options
  cliLanguage: string
  publishToRegistry: boolean
  
  // Desktop options
  desktopPlatforms: string[]
  desktopFramework: string
  
  // Step 3: Advanced
  name: string
  figmaUrl: string
  colorScheme: 'light' | 'dark' | 'system'
  primaryColor: string
  designStyle: string
  enableAnimations: boolean
  glassmorphism: boolean
  frontendFramework: string
  cssFramework: string
  backendFramework: string
  database: string
  authProvider: string
  deploymentPlatform: string
  autoDeploy: boolean
  customInstructions: string
  buildMode: 'full_auto' | 'step_approval' | 'preview_only'
}

const defaultFormState: FormState = {
  brief: '',
  projectType: null,
  costProfile: 'balanced',
  industry: '',
  targetAudience: '',
  referenceUrls: [],
  selectedFeatures: [],
  pages: [],
  mobilePlatforms: ['ios', 'android'],
  mobileFramework: 'expo',
  submitToStores: false,
  numPages: 1,
  sections: ['hero', 'features', 'cta'],
  includeContactForm: true,
  includeBlog: false,
  cliLanguage: 'python',
  publishToRegistry: false,
  desktopPlatforms: ['mac', 'windows'],
  desktopFramework: 'electron',
  name: '',
  figmaUrl: '',
  colorScheme: 'system',
  primaryColor: '#20B8CD',
  designStyle: 'minimal',
  enableAnimations: true,
  glassmorphism: true,
  frontendFramework: '',
  cssFramework: 'tailwind',
  backendFramework: '',
  database: '',
  authProvider: '',
  deploymentPlatform: '',
  autoDeploy: true,
  customInstructions: '',
  buildMode: 'full_auto',
}

// ============ Main Component ============

export default function NewProject() {
  const navigate = useNavigate()
  const [form, setForm] = useState<FormState>(defaultFormState)
  const [analysis, setAnalysis] = useState<BriefAnalysis | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [showSummary, setShowSummary] = useState(false)
  const [newPageInput, setNewPageInput] = useState('')
  const [newUrlInput, setNewUrlInput] = useState('')
  const [selectedPresetId, setSelectedPresetId] = useState<string | null>(null)
  const [showSavePreset, setShowSavePreset] = useState(false)
  const [presetName, setPresetName] = useState('')
  const analyzeTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  
  // Phase 11B: Template Browser
  const [showTemplateBrowser, setShowTemplateBrowser] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState<ProjectTemplate | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)

  // Load presets
  const { data: presets = [] } = useQuery({
    queryKey: ['presets'],
    queryFn: () => api.getPresets(true),
  })

  // Load draft from localStorage
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        setForm(prev => ({ ...prev, ...parsed }))
      } catch (e) {
        console.warn('Failed to load draft:', e)
      }
    }
  }, [])

  // Save draft to localStorage
  useEffect(() => {
    if (form.brief || form.projectType) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(form))
    }
  }, [form])

  // Debounced brief analysis
  const analyzeBrief = useCallback(async (brief: string) => {
    if (brief.length < 10) {
      setAnalysis(null)
      return
    }
    
    setIsAnalyzing(true)
    try {
      const result = await api.analyzeBrief(brief)
      setAnalysis(result)
      
      // Auto-select detected type if user hasn't manually selected
      if (result.detected_project_type && !form.projectType) {
        setForm(prev => ({ ...prev, projectType: result.detected_project_type }))
      }
    } catch (e) {
      console.error('Brief analysis failed:', e)
    } finally {
      setIsAnalyzing(false)
    }
  }, [form.projectType])

  // Trigger analysis on brief change (debounced 1s)
  useEffect(() => {
    if (analyzeTimeoutRef.current) {
      clearTimeout(analyzeTimeoutRef.current)
    }
    
    analyzeTimeoutRef.current = setTimeout(() => {
      analyzeBrief(form.brief)
    }, 1000)
    
    return () => {
      if (analyzeTimeoutRef.current) {
        clearTimeout(analyzeTimeoutRef.current)
      }
    }
  }, [form.brief, analyzeBrief])

  // Create project mutation
  const createProject = useMutation({
    mutationFn: api.createProject,
    onSuccess: (data) => {
      setSubmitError(null)
      localStorage.removeItem(STORAGE_KEY)
      navigate(`/project/${data.id}`)
    },
    onError: (err: any) => {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to create project. Is the backend running?'
      setSubmitError(msg)
    },
  })

  // Create preset mutation
  const createPreset = useMutation({
    mutationFn: api.createPreset,
    onSuccess: () => {
      setShowSavePreset(false)
      setPresetName('')
    },
  })

  // Handle preset selection
  const handleSelectPreset = (preset: Preset) => {
    setSelectedPresetId(preset.id)
    const config = preset.config
    
    setForm(prev => ({
      ...prev,
      projectType: config.project_type || prev.projectType,
      costProfile: config.cost_profile || prev.costProfile,
      industry: config.industry || prev.industry,
      colorScheme: config.design_preferences?.color_scheme || prev.colorScheme,
      primaryColor: config.design_preferences?.primary_color || prev.primaryColor,
      designStyle: config.design_preferences?.design_style || prev.designStyle,
      enableAnimations: config.design_preferences?.enable_animations ?? prev.enableAnimations,
      glassmorphism: config.design_preferences?.glassmorphism ?? prev.glassmorphism,
      frontendFramework: config.tech_stack?.frontend_framework || prev.frontendFramework,
      database: config.tech_stack?.database || prev.database,
      mobileFramework: config.mobile_options?.framework || prev.mobileFramework,
      desktopFramework: config.desktop_options?.framework || prev.desktopFramework,
      selectedFeatures: config.web_complex_options?.key_features || prev.selectedFeatures,
      buildMode: config.build_mode || prev.buildMode,
    }))
    
    // Mark preset as used
    api.usePreset(preset.id).catch(() => {})
  }

  // Phase 11B: Handle template selection
  const handleSelectTemplate = async (template: ProjectTemplate) => {
    setSelectedTemplate(template)
    setShowTemplateBrowser(false)
    
    // Apply template data to form
    setForm(prev => ({
      ...prev,
      projectType: template.project_type || prev.projectType,
      brief: template.brief_template || prev.brief,
      industry: template.industry || prev.industry,
      selectedFeatures: template.features || prev.selectedFeatures,
      // Apply design tokens if available
      ...(template.design_tokens ? {
        primaryColor: template.design_tokens.primary_color || prev.primaryColor,
        designStyle: template.design_tokens.design_style || prev.designStyle,
      } : {}),
      // Apply tech stack if available
      ...(template.tech_stack ? {
        frontendFramework: template.tech_stack[0] || prev.frontendFramework,
      } : {}),
    }))
  }

  // Handle voice transcript
  const handleVoiceTranscript = (text: string) => {
    setForm(prev => ({
      ...prev,
      brief: prev.brief + (prev.brief ? ' ' : '') + text
    }))
  }

  // Handle form submit
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.brief.trim() || !form.projectType) return

    const requirements = {
      brief: form.brief,
      project_type: form.projectType,
      name: form.name || undefined,
      cost_profile: form.costProfile,
      industry: form.industry || undefined,
      target_audience: form.targetAudience || undefined,
      reference_urls: form.referenceUrls.length > 0 ? form.referenceUrls : undefined,
      design_preferences: {
        color_scheme: form.colorScheme,
        primary_color: form.primaryColor,
        design_style: form.designStyle,
        enable_animations: form.enableAnimations,
        glassmorphism: form.glassmorphism,
      },
      figma_url: form.figmaUrl || undefined,
      tech_stack: {
        frontend_framework: form.frontendFramework || undefined,
        css_framework: form.cssFramework || undefined,
        backend_framework: form.backendFramework || undefined,
        database: form.database || undefined,
        auth_provider: form.authProvider || undefined,
      },
      deployment: {
        platform: form.deploymentPlatform || undefined,
        auto_deploy: form.autoDeploy,
      },
      custom_instructions: form.customInstructions || undefined,
      build_mode: form.buildMode,
    }

    // Add type-specific options
    if (['web_complex', 'python_saas'].includes(form.projectType)) {
      Object.assign(requirements, {
        web_complex_options: {
          key_features: form.selectedFeatures,
          pages: form.pages,
          include_auth: form.selectedFeatures.includes('authentication'),
          include_dashboard: form.selectedFeatures.includes('dashboard'),
          include_billing: form.selectedFeatures.includes('payments'),
          include_email: form.selectedFeatures.includes('email'),
        }
      })
    } else if (form.projectType === 'web_simple') {
      Object.assign(requirements, {
        web_simple_options: {
          num_pages: form.numPages,
          sections: form.sections,
          include_contact_form: form.includeContactForm,
          include_blog: form.includeBlog,
        }
      })
    } else if (['mobile_native_ios', 'mobile_cross_platform', 'mobile_pwa'].includes(form.projectType)) {
      Object.assign(requirements, {
        mobile_options: {
          platforms: form.mobilePlatforms,
          framework: form.mobileFramework,
          submit_to_stores: form.submitToStores,
        }
      })
    } else if (form.projectType === 'cli_tool') {
      Object.assign(requirements, {
        cli_options: {
          language: form.cliLanguage,
          publish_to_registry: form.publishToRegistry,
        }
      })
    } else if (form.projectType === 'desktop_app') {
      Object.assign(requirements, {
        desktop_options: {
          target_platforms: form.desktopPlatforms,
          framework: form.desktopFramework,
        }
      })
    }

    createProject.mutate({
      brief: form.brief,
      name: form.name || undefined,
      cost_profile: form.costProfile,
      project_type: form.projectType,
      figma_url: form.figmaUrl || undefined,
      requirements,
    })
  }

  // Save as preset
  const handleSavePreset = () => {
    if (!presetName.trim()) return
    
    createPreset.mutate({
      name: presetName,
      description: `Custom preset for ${PROJECT_TYPES.find(t => t.id === form.projectType)?.label || 'projects'}`,
      icon: PROJECT_TYPES.find(t => t.id === form.projectType)?.icon.name || 'Settings',
      config: {
        project_type: form.projectType,
        cost_profile: form.costProfile,
        industry: form.industry,
        design_preferences: {
          color_scheme: form.colorScheme,
          primary_color: form.primaryColor,
          design_style: form.designStyle,
          enable_animations: form.enableAnimations,
          glassmorphism: form.glassmorphism,
        },
        tech_stack: {
          frontend_framework: form.frontendFramework,
          css_framework: form.cssFramework,
          backend_framework: form.backendFramework,
          database: form.database,
        },
        web_complex_options: {
          key_features: form.selectedFeatures,
        },
        build_mode: form.buildMode,
      }
    })
  }

  // Get current project type info
  const currentType = PROJECT_TYPES.find(t => t.id === form.projectType)
  const costEstimate = analysis?.cost_estimate || {}

  // Render icon component
  const renderIcon = (iconName: string | null) => {
    const icons: Record<string, typeof Globe> = {
      Globe, Smartphone, Monitor, Chrome, Terminal, Server, Sparkles,
      Settings2, Rocket, FileCode, Layers
    }
    const IconComponent = iconName ? icons[iconName] : Settings2
    return IconComponent ? <IconComponent className="w-5 h-5" /> : <Settings2 className="w-5 h-5" />
  }

  return (
    <div className="space-y-6 pb-8 lg:pb-32">
      {/* Header */}
      <div className="mb-2">
        <h1 className="text-2xl lg:text-3xl font-bold" style={{ color: 'var(--text-primary)' }}>
          New Project
        </h1>
        <p className="mt-1" style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-base)' }}>
          Tell us what you want to build
        </p>
      </div>

      {/* Phase 11B: Template Browser Section */}
      <div className="glass-card" style={{ padding: 'var(--space-4)' }}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-medium" style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
            Start from Template
          </h3>
          <button
            type="button"
            onClick={() => setShowTemplateBrowser(true)}
            className="btn-secondary flex items-center gap-2"
            style={{ padding: '8px 16px', fontSize: 'var(--text-sm)' }}
          >
            <LayoutTemplate className="w-4 h-4" />
            Browse All
          </button>
        </div>
        {selectedTemplate ? (
          <div className="glass-card-iridescent flex items-center justify-between p-4">
            <div>
              <div className="font-medium" style={{ color: 'var(--text-primary)' }}>
                {selectedTemplate.name}
              </div>
              <div className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
                {selectedTemplate.project_type} • {selectedTemplate.industry || 'General'}
              </div>
            </div>
            <button
              type="button"
              onClick={() => setSelectedTemplate(null)}
              className="btn-ghost"
              style={{ padding: '4px' }}
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <p style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-sm)' }}>
            Use a pre-built template to jump-start your project
          </p>
        )}
      </div>

      {/* Presets Row */}
      {presets.length > 0 && (
        <div className="glass-card" style={{ padding: 'var(--space-4)' }}>
          <h3 className="font-medium mb-3" style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
            Quick Start Presets
          </h3>
          <div className="flex gap-3 overflow-x-auto pb-2" style={{ scrollbarWidth: 'thin' }}>
            {presets.map((preset) => (
              <button
                key={preset.id}
                type="button"
                onClick={() => handleSelectPreset(preset)}
                className={clsx(
                  'glass-card flex-shrink-0 flex items-center gap-3 px-4 py-3 transition-all',
                  selectedPresetId === preset.id && 'glass-card-iridescent'
                )}
                style={{
                  minWidth: '180px',
                  borderColor: selectedPresetId === preset.id ? 'var(--accent-primary)' : undefined,
                }}
              >
                <div style={{ 
                  color: selectedPresetId === preset.id ? 'var(--accent-primary)' : 'var(--text-tertiary)' 
                }}>
                  {renderIcon(preset.icon)}
                </div>
                <div className="text-left">
                  <div className="font-medium text-sm" style={{ color: 'var(--text-primary)' }}>
                    {preset.name}
                  </div>
                  {preset.description && (
                    <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                      {preset.description}
                    </div>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* ============ STEP 1: BASICS ============ */}
        <div className="glass-card-elevated" style={{ padding: 0 }}>
          <div className="bloom-content">
            <div className="flex items-center gap-3 p-4" style={{ borderBottom: '1px solid var(--glass-border)' }}>
              <span className="flex items-center justify-center w-7 h-7 rounded-full text-sm font-bold"
                    style={{ background: 'var(--gradient-accent)', color: 'white' }}>1</span>
              <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>What do you want to build?</span>
            </div>
            
            <div className="relative">
              <textarea
                value={form.brief}
                onChange={(e) => setForm(prev => ({ ...prev, brief: e.target.value }))}
                placeholder="Describe your project in detail... (e.g., 'A fitness tracking mobile app with workout logging, progress charts, and social features')"
                className="glass-textarea w-full border-0 bg-transparent"
                style={{ 
                  minHeight: '140px',
                  padding: 'var(--space-5)',
                  fontSize: 'var(--text-lg)',
                  resize: 'none'
                }}
                autoFocus
              />
            </div>
            
            <div className="flex items-center justify-between p-4" 
                 style={{ borderTop: '1px solid var(--glass-border)' }}>
              <div className="flex items-center gap-3">
                <VoiceInput 
                  onTranscript={handleVoiceTranscript}
                  className="btn-ghost"
                />
                {isAnalyzing && (
                  <span className="flex items-center gap-2 text-xs" style={{ color: 'var(--text-tertiary)' }}>
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Analyzing...
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3">
                {analysis?.detected_project_type && (
                  <span className="badge badge-info flex items-center gap-1">
                    <Check className="w-3 h-3" />
                    Detected: {PROJECT_TYPES.find(t => t.id === analysis.detected_project_type)?.label}
                  </span>
                )}
                <span style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-xs)' }}>
                  {form.brief.length} chars
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Analysis Warnings */}
        {analysis?.warnings && analysis.warnings.length > 0 && (
          <div className="glass-card bg-accent-warning/10 border-accent-warning/30">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 flex-shrink-0 text-accent-warning" />
              <div className="space-y-1">
                {analysis.warnings.map((warning, i) => (
                  <p key={i} className="text-sm" style={{ color: 'var(--text-secondary)' }}>{warning}</p>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Project Type Selection */}
        <div className="glass-card">
          <h3 className="font-medium mb-4" style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
            Project Type
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            {PROJECT_TYPES.map((type) => {
              const Icon = type.icon
              const isSelected = form.projectType === type.id
              const isDetected = analysis?.detected_project_type === type.id
              return (
                <button
                  key={type.id}
                  type="button"
                  onClick={() => setForm(prev => ({ ...prev, projectType: type.id }))}
                  className={clsx(
                    'glass-card flex flex-col items-center gap-2 p-4 text-center transition-all relative',
                    isSelected && 'glass-card-iridescent'
                  )}
                  style={{
                    borderColor: isSelected ? 'var(--accent-primary)' : isDetected ? 'var(--accent-primary-muted, rgba(32,184,205,0.3))' : undefined,
                    background: isSelected ? 'var(--accent-primary-subtle, rgba(32,184,205,0.08))' : undefined
                  }}
                >
                  {isDetected && !isSelected && (
                    <span className="absolute -top-1 -right-1 w-3 h-3 rounded-full" 
                          style={{ background: 'var(--accent-primary)' }} />
                  )}
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

        {/* Cost Profile */}
        <div className="glass-card">
          <h3 className="font-medium mb-4" style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
            Cost Profile
          </h3>
          <div className="grid grid-cols-3 gap-3">
            {COST_PROFILES.map((profile) => {
              const Icon = profile.icon
              const isSelected = form.costProfile === profile.id
              return (
                <button
                  key={profile.id}
                  type="button"
                  onClick={() => setForm(prev => ({ ...prev, costProfile: profile.id }))}
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
                  {costEstimate[profile.id] && (
                    <span className="block mt-2 text-sm font-semibold" style={{ color: profile.color }}>
                      {costEstimate[profile.id]}
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        </div>

        {/* ============ STEP 2: CONDITIONAL FIELDS ============ */}
        {form.projectType && (
          <div className="glass-card">
            <div className="flex items-center gap-3 mb-4">
              <span className="flex items-center justify-center w-7 h-7 rounded-full text-sm font-bold"
                    style={{ background: 'var(--gradient-accent)', color: 'white' }}>2</span>
              <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>Project Details</span>
            </div>

            <div className="space-y-5">
              {/* Common fields */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block mb-2 text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                    Industry
                  </label>
                  <select
                    value={form.industry}
                    onChange={(e) => setForm(prev => ({ ...prev, industry: e.target.value }))}
                    className="glass-input w-full"
                  >
                    <option value="">Select industry...</option>
                    {INDUSTRIES.map(ind => (
                      <option key={ind} value={ind.toLowerCase()}>{ind}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block mb-2 text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                    Target Audience
                  </label>
                  <input
                    type="text"
                    value={form.targetAudience}
                    onChange={(e) => setForm(prev => ({ ...prev, targetAudience: e.target.value }))}
                    placeholder="e.g., Small business owners"
                    className="glass-input w-full"
                  />
                </div>
              </div>

              {/* Reference URLs */}
              <div>
                <label className="block mb-2 text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                  Reference/Inspiration URLs
                </label>
                <div className="flex gap-2 mb-2">
                  <input
                    type="url"
                    value={newUrlInput}
                    onChange={(e) => setNewUrlInput(e.target.value)}
                    placeholder="https://example.com"
                    className="glass-input flex-1"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        if (newUrlInput.trim()) {
                          setForm(prev => ({ ...prev, referenceUrls: [...prev.referenceUrls, newUrlInput.trim()] }))
                          setNewUrlInput('')
                        }
                      }
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => {
                      if (newUrlInput.trim()) {
                        setForm(prev => ({ ...prev, referenceUrls: [...prev.referenceUrls, newUrlInput.trim()] }))
                        setNewUrlInput('')
                      }
                    }}
                    className="btn-secondary px-4"
                  >
                    <Plus className="w-4 h-4" />
                  </button>
                </div>
                {form.referenceUrls.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {form.referenceUrls.map((url, i) => (
                      <span key={i} className="badge flex items-center gap-1">
                        {url.replace(/^https?:\/\//, '').substring(0, 30)}...
                        <button type="button" onClick={() => {
                          setForm(prev => ({ ...prev, referenceUrls: prev.referenceUrls.filter((_, idx) => idx !== i) }))
                        }}>
                          <X className="w-3 h-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Web Complex / SaaS: Features & Pages */}
              {['web_complex', 'python_saas'].includes(form.projectType) && (
                <>
                  <div>
                    <label className="block mb-2 text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                      Key Features
                    </label>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                      {COMMON_FEATURES.map((feature) => {
                        const Icon = feature.icon
                        const isSelected = form.selectedFeatures.includes(feature.id)
                        const isSuggested = analysis?.suggested_features?.includes(feature.id)
                        return (
                          <button
                            key={feature.id}
                            type="button"
                            onClick={() => {
                              setForm(prev => ({
                                ...prev,
                                selectedFeatures: isSelected
                                  ? prev.selectedFeatures.filter(f => f !== feature.id)
                                  : [...prev.selectedFeatures, feature.id]
                              }))
                            }}
                            className={clsx(
                              'glass-card flex items-center gap-2 p-3 text-left transition-all relative',
                              isSelected && 'glass-card-iridescent'
                            )}
                            style={{
                              borderColor: isSelected ? 'var(--accent-primary)' : isSuggested ? 'var(--accent-primary-muted, rgba(32,184,205,0.3))' : undefined,
                            }}
                          >
                            {isSuggested && !isSelected && (
                              <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full" 
                                    style={{ background: 'var(--accent-primary)' }} />
                            )}
                            <Icon className="w-4 h-4" style={{ 
                              color: isSelected ? 'var(--accent-primary)' : 'var(--text-tertiary)' 
                            }} />
                            <span className="text-xs" style={{ 
                              color: isSelected ? 'var(--accent-primary)' : 'var(--text-secondary)' 
                            }}>
                              {feature.label}
                            </span>
                          </button>
                        )
                      })}
                    </div>
                  </div>

                  <div>
                    <label className="block mb-2 text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                      Pages/Routes
                    </label>
                    <div className="flex gap-2 mb-2">
                      <input
                        type="text"
                        value={newPageInput}
                        onChange={(e) => setNewPageInput(e.target.value)}
                        placeholder="Add a page (e.g., Dashboard)"
                        className="glass-input flex-1"
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault()
                            if (newPageInput.trim()) {
                              setForm(prev => ({ ...prev, pages: [...prev.pages, newPageInput.trim()] }))
                              setNewPageInput('')
                            }
                          }
                        }}
                      />
                      <button
                        type="button"
                        onClick={() => {
                          if (newPageInput.trim()) {
                            setForm(prev => ({ ...prev, pages: [...prev.pages, newPageInput.trim()] }))
                            setNewPageInput('')
                          }
                        }}
                        className="btn-secondary px-4"
                      >
                        <Plus className="w-4 h-4" />
                      </button>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {/* Suggested pages from analysis */}
                      {analysis?.suggested_pages?.filter(p => !form.pages.includes(p)).map((page, i) => (
                        <button
                          key={`suggested-${i}`}
                          type="button"
                          onClick={() => setForm(prev => ({ ...prev, pages: [...prev.pages, page] }))}
                          className="badge badge-outline flex items-center gap-1"
                          style={{ borderStyle: 'dashed' }}
                        >
                          <Plus className="w-3 h-3" />
                          {page}
                        </button>
                      ))}
                      {form.pages.map((page, i) => (
                        <span key={i} className="badge badge-info flex items-center gap-1">
                          {page}
                          <button type="button" onClick={() => {
                            setForm(prev => ({ ...prev, pages: prev.pages.filter((_, idx) => idx !== i) }))
                          }}>
                            <X className="w-3 h-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {/* Web Simple: Sections */}
              {form.projectType === 'web_simple' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block mb-2 text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                      Number of Pages
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={20}
                      value={form.numPages}
                      onChange={(e) => setForm(prev => ({ ...prev, numPages: parseInt(e.target.value) || 1 }))}
                      className="glass-input w-full"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={form.includeContactForm}
                        onChange={(e) => setForm(prev => ({ ...prev, includeContactForm: e.target.checked }))}
                        className="rounded"
                      />
                      <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>Include contact form</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={form.includeBlog}
                        onChange={(e) => setForm(prev => ({ ...prev, includeBlog: e.target.checked }))}
                        className="rounded"
                      />
                      <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>Include blog section</span>
                    </label>
                  </div>
                </div>
              )}

              {/* Mobile: Platforms & Framework */}
              {['mobile_native_ios', 'mobile_cross_platform', 'mobile_pwa'].includes(form.projectType) && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {form.projectType === 'mobile_cross_platform' && (
                    <>
                      <div>
                        <label className="block mb-2 text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                          Platforms
                        </label>
                        <div className="flex gap-2">
                          {['ios', 'android'].map(platform => (
                            <button
                              key={platform}
                              type="button"
                              onClick={() => {
                                setForm(prev => ({
                                  ...prev,
                                  mobilePlatforms: prev.mobilePlatforms.includes(platform)
                                    ? prev.mobilePlatforms.filter(p => p !== platform)
                                    : [...prev.mobilePlatforms, platform]
                                }))
                              }}
                              className={clsx(
                                'glass-card px-4 py-2 capitalize transition-all',
                                form.mobilePlatforms.includes(platform) && 'glass-card-iridescent'
                              )}
                            >
                              {platform}
                            </button>
                          ))}
                        </div>
                      </div>
                      <div>
                        <label className="block mb-2 text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                          Framework
                        </label>
                        <select
                          value={form.mobileFramework}
                          onChange={(e) => setForm(prev => ({ ...prev, mobileFramework: e.target.value }))}
                          className="glass-input w-full"
                        >
                          <option value="expo">Expo (React Native)</option>
                          <option value="react_native">React Native</option>
                          <option value="flutter">Flutter</option>
                        </select>
                      </div>
                    </>
                  )}
                  <div className="md:col-span-2">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={form.submitToStores}
                        onChange={(e) => setForm(prev => ({ ...prev, submitToStores: e.target.checked }))}
                        className="rounded"
                      />
                      <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                        Submit to app stores (requires credentials in Settings)
                      </span>
                    </label>
                  </div>
                </div>
              )}

              {/* CLI: Language */}
              {form.projectType === 'cli_tool' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block mb-2 text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                      Language
                    </label>
                    <select
                      value={form.cliLanguage}
                      onChange={(e) => setForm(prev => ({ ...prev, cliLanguage: e.target.value }))}
                      className="glass-input w-full"
                    >
                      <option value="python">Python (Click/Typer)</option>
                      <option value="node">Node.js (Commander)</option>
                    </select>
                  </div>
                  <div className="flex items-end">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={form.publishToRegistry}
                        onChange={(e) => setForm(prev => ({ ...prev, publishToRegistry: e.target.checked }))}
                        className="rounded"
                      />
                      <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                        Publish to {form.cliLanguage === 'python' ? 'PyPI' : 'npm'}
                      </span>
                    </label>
                  </div>
                </div>
              )}

              {/* Desktop: Platforms & Framework */}
              {form.projectType === 'desktop_app' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block mb-2 text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                      Target Platforms
                    </label>
                    <div className="flex gap-2">
                      {['mac', 'windows', 'linux'].map(platform => (
                        <button
                          key={platform}
                          type="button"
                          onClick={() => {
                            setForm(prev => ({
                              ...prev,
                              desktopPlatforms: prev.desktopPlatforms.includes(platform)
                                ? prev.desktopPlatforms.filter(p => p !== platform)
                                : [...prev.desktopPlatforms, platform]
                            }))
                          }}
                          className={clsx(
                            'glass-card px-4 py-2 capitalize transition-all',
                            form.desktopPlatforms.includes(platform) && 'glass-card-iridescent'
                          )}
                        >
                          {platform}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="block mb-2 text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                      Framework
                    </label>
                    <select
                      value={form.desktopFramework}
                      onChange={(e) => setForm(prev => ({ ...prev, desktopFramework: e.target.value }))}
                      className="glass-input w-full"
                    >
                      <option value="electron">Electron</option>
                      <option value="tauri">Tauri</option>
                      <option value="pyqt">PyQt</option>
                    </select>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ============ STEP 3: ADVANCED OPTIONS ============ */}
        <div className="glass-card" style={{ padding: 0 }}>
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="w-full flex items-center justify-between p-4 text-left"
          >
            <div className="flex items-center gap-3">
              <span className="flex items-center justify-center w-7 h-7 rounded-full text-sm font-bold"
                    style={{ background: 'var(--background-tertiary)', color: 'var(--text-secondary)' }}>3</span>
              <span className="font-medium" style={{ color: 'var(--text-secondary)' }}>
                Advanced Options
              </span>
            </div>
            {showAdvanced ? (
              <ChevronUp className="w-5 h-5" style={{ color: 'var(--text-tertiary)' }} />
            ) : (
              <ChevronDown className="w-5 h-5" style={{ color: 'var(--text-tertiary)' }} />
            )}
          </button>
          
          {showAdvanced && (
            <div className="p-4 pt-0 space-y-6" style={{ borderTop: '1px solid var(--glass-border)' }}>
              {/* Project Name & Figma */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block mb-2 text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                    Project Name (optional)
                  </label>
                  <input
                    type="text"
                    value={form.name}
                    onChange={(e) => setForm(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="My Awesome Project"
                    className="glass-input w-full"
                  />
                </div>
                <div>
                  <label className="flex items-center gap-2 mb-2 text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                    <Figma className="w-4 h-4" style={{ color: 'var(--accent-primary)' }} />
                    Figma Design URL
                    <div className="relative group">
                      <Info className="w-4 h-4 cursor-help" style={{ color: 'var(--text-tertiary)' }} />
                      <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block z-50">
                        <div className="glass-card p-3 text-xs" style={{ width: '250px' }}>
                          <p style={{ color: 'var(--text-secondary)' }}>
                            Paste a Figma file URL to extract design tokens and layout structure.
                          </p>
                        </div>
                      </div>
                    </div>
                  </label>
                  <input
                    type="url"
                    value={form.figmaUrl}
                    onChange={(e) => setForm(prev => ({ ...prev, figmaUrl: e.target.value }))}
                    placeholder="https://www.figma.com/file/..."
                    className="glass-input w-full"
                  />
                </div>
              </div>

              {/* Design Preferences */}
              <div>
                <h4 className="flex items-center gap-2 mb-3 font-medium" style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
                  <Palette className="w-4 h-4" />
                  Design Preferences
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block mb-2 text-sm" style={{ color: 'var(--text-tertiary)' }}>
                      Color Scheme
                    </label>
                    <div className="flex gap-2">
                      {[
                        { id: 'light', icon: Sun },
                        { id: 'dark', icon: Moon },
                        { id: 'system', icon: Settings2 },
                      ].map(({ id, icon: Icon }) => (
                        <button
                          key={id}
                          type="button"
                          onClick={() => setForm(prev => ({ ...prev, colorScheme: id as any }))}
                          className={clsx(
                            'glass-card px-3 py-2 flex items-center gap-2 capitalize transition-all',
                            form.colorScheme === id && 'glass-card-iridescent'
                          )}
                        >
                          <Icon className="w-4 h-4" />
                          {id}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="block mb-2 text-sm" style={{ color: 'var(--text-tertiary)' }}>
                      Primary Color
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="color"
                        value={form.primaryColor}
                        onChange={(e) => setForm(prev => ({ ...prev, primaryColor: e.target.value }))}
                        className="w-10 h-10 rounded cursor-pointer"
                      />
                      <input
                        type="text"
                        value={form.primaryColor}
                        onChange={(e) => setForm(prev => ({ ...prev, primaryColor: e.target.value }))}
                        className="glass-input flex-1"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block mb-2 text-sm" style={{ color: 'var(--text-tertiary)' }}>
                      Design Style
                    </label>
                    <select
                      value={form.designStyle}
                      onChange={(e) => setForm(prev => ({ ...prev, designStyle: e.target.value }))}
                      className="glass-input w-full"
                    >
                      {DESIGN_STYLES.map(style => (
                        <option key={style.id} value={style.id}>{style.label}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="flex gap-4 mt-3">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={form.enableAnimations}
                      onChange={(e) => setForm(prev => ({ ...prev, enableAnimations: e.target.checked }))}
                      className="rounded"
                    />
                    <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>Enable animations</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={form.glassmorphism}
                      onChange={(e) => setForm(prev => ({ ...prev, glassmorphism: e.target.checked }))}
                      className="rounded"
                    />
                    <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>Glassmorphic design</span>
                  </label>
                </div>
              </div>

              {/* Tech Stack */}
              <div>
                <h4 className="flex items-center gap-2 mb-3 font-medium" style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
                  <FileCode className="w-4 h-4" />
                  Tech Stack Preferences
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block mb-2 text-sm" style={{ color: 'var(--text-tertiary)' }}>
                      Frontend Framework
                    </label>
                    <select
                      value={form.frontendFramework}
                      onChange={(e) => setForm(prev => ({ ...prev, frontendFramework: e.target.value }))}
                      className="glass-input w-full"
                    >
                      <option value="">Auto (recommended)</option>
                      <option value="nextjs">Next.js</option>
                      <option value="react">React</option>
                      <option value="vue">Vue</option>
                      <option value="svelte">Svelte</option>
                    </select>
                  </div>
                  <div>
                    <label className="block mb-2 text-sm" style={{ color: 'var(--text-tertiary)' }}>
                      CSS Framework
                    </label>
                    <select
                      value={form.cssFramework}
                      onChange={(e) => setForm(prev => ({ ...prev, cssFramework: e.target.value }))}
                      className="glass-input w-full"
                    >
                      <option value="tailwind">Tailwind CSS</option>
                      <option value="css-modules">CSS Modules</option>
                      <option value="styled-components">Styled Components</option>
                    </select>
                  </div>
                  <div>
                    <label className="block mb-2 text-sm" style={{ color: 'var(--text-tertiary)' }}>
                      Database
                    </label>
                    <select
                      value={form.database}
                      onChange={(e) => setForm(prev => ({ ...prev, database: e.target.value }))}
                      className="glass-input w-full"
                    >
                      <option value="">Auto (if needed)</option>
                      <option value="supabase">Supabase</option>
                      <option value="postgresql">PostgreSQL</option>
                      <option value="mongodb">MongoDB</option>
                      <option value="sqlite">SQLite</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Build Mode */}
              <div>
                <h4 className="flex items-center gap-2 mb-3 font-medium" style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
                  <Rocket className="w-4 h-4" />
                  Build Mode
                </h4>
                <div className="flex gap-3">
                  {[
                    { id: 'full_auto', label: 'Full Auto', desc: 'Run entire pipeline automatically' },
                    { id: 'step_approval', label: 'Step Approval', desc: 'Pause after each step for review' },
                    { id: 'preview_only', label: 'Preview Only', desc: 'Generate plan without execution' },
                  ].map(mode => (
                    <button
                      key={mode.id}
                      type="button"
                      onClick={() => setForm(prev => ({ ...prev, buildMode: mode.id as any }))}
                      className={clsx(
                        'glass-card flex-1 p-3 text-left transition-all',
                        form.buildMode === mode.id && 'glass-card-iridescent'
                      )}
                    >
                      <span className="block font-medium text-sm" style={{ 
                        color: form.buildMode === mode.id ? 'var(--accent-primary)' : 'var(--text-primary)' 
                      }}>
                        {mode.label}
                      </span>
                      <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{mode.desc}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Custom Instructions */}
              <div>
                <label className="block mb-2 text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                  Custom Instructions
                </label>
                <textarea
                  value={form.customInstructions}
                  onChange={(e) => setForm(prev => ({ ...prev, customInstructions: e.target.value }))}
                  placeholder="Any special requirements or instructions for the build..."
                  className="glass-textarea w-full"
                  style={{ minHeight: '80px' }}
                />
              </div>

              {/* Save as Preset */}
              <div className="flex justify-end">
                {showSavePreset ? (
                  <div className="flex gap-2 items-center">
                    <input
                      type="text"
                      value={presetName}
                      onChange={(e) => setPresetName(e.target.value)}
                      placeholder="Preset name..."
                      className="glass-input"
                      autoFocus
                    />
                    <button
                      type="button"
                      onClick={handleSavePreset}
                      disabled={!presetName.trim() || createPreset.isPending}
                      className="btn-secondary"
                    >
                      {createPreset.isPending ? 'Saving...' : 'Save'}
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowSavePreset(false)}
                      className="btn-ghost"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => setShowSavePreset(true)}
                    className="btn-ghost flex items-center gap-2"
                  >
                    <Save className="w-4 h-4" />
                    Save as Preset
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* ============ STEP 4: BUILD SUMMARY (Mobile inline) ============ */}
        <div className="lg:hidden glass-card p-4 space-y-3">
          <div className="flex items-center gap-3 mb-1">
            <span className="flex items-center justify-center w-7 h-7 rounded-full text-sm font-bold"
                  style={{ background: form.brief && form.projectType ? 'var(--gradient-accent)' : 'var(--background-tertiary)', color: 'white' }}>4</span>
            <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>Build Summary</span>
            {costEstimate[form.costProfile] && (
              <span className="ml-auto text-lg font-bold" style={{ color: 'var(--accent-primary)' }}>
                Est: {costEstimate[form.costProfile]}
              </span>
            )}
          </div>
          {(!form.brief.trim() || !form.projectType) && (
            <p className="text-sm text-center" style={{ color: 'var(--text-tertiary)' }}>
              {!form.brief.trim()
                ? 'Enter a project description to continue'
                : 'Select a project type above to continue'}
            </p>
          )}
          {submitError && (
            <div className="flex items-start gap-2 rounded-lg p-3 bg-accent-error/10 border border-accent-error/30">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0 text-accent-error" />
              <p className="text-sm text-accent-error">{submitError}</p>
            </div>
          )}
          <button
            type="submit"
            className="btn-iridescent w-full"
            disabled={!form.brief.trim() || !form.projectType || createProject.isPending}
          >
            {createProject.isPending ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Starting Build...
              </span>
            ) : (
              <span className="flex items-center justify-center gap-2">
                <Rocket className="w-5 h-5" />
                Start Building
                <ArrowRight className="w-5 h-5" />
              </span>
            )}
          </button>
        </div>

        {/* ============ STEP 4: BUILD SUMMARY (Desktop sticky footer) ============ */}
        <div
          className="hidden lg:block fixed bottom-0 left-0 right-0 z-[110] lg:left-64"
          style={{ 
            background: 'var(--background-primary)',
            borderTop: '1px solid var(--glass-border)',
          }}
        >
          <div className="max-w-4xl mx-auto px-4 py-4">
            {/* Expandable Summary */}
            <button
              type="button"
              onClick={() => setShowSummary(!showSummary)}
              className="w-full flex items-center justify-between mb-3"
            >
              <div className="flex items-center gap-3">
                <span className="flex items-center justify-center w-7 h-7 rounded-full text-sm font-bold"
                      style={{ background: form.brief && form.projectType ? 'var(--gradient-accent)' : 'var(--background-tertiary)', color: 'white' }}>4</span>
                <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                  Build Summary
                </span>
              </div>
              <div className="flex items-center gap-3">
                {costEstimate[form.costProfile] && (
                  <span className="text-lg font-bold" style={{ color: 'var(--accent-primary)' }}>
                    Est: {costEstimate[form.costProfile]}
                  </span>
                )}
                {showSummary ? (
                  <ChevronDown className="w-5 h-5" style={{ color: 'var(--text-tertiary)' }} />
                ) : (
                  <ChevronUp className="w-5 h-5" style={{ color: 'var(--text-tertiary)' }} />
                )}
              </div>
            </button>

            {showSummary && (
              <div className="glass-card p-4 mb-3 max-h-48 overflow-y-auto">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="block" style={{ color: 'var(--text-tertiary)' }}>Type</span>
                    <span style={{ color: 'var(--text-primary)' }}>{currentType?.label || 'Not selected'}</span>
                  </div>
                  <div>
                    <span className="block" style={{ color: 'var(--text-tertiary)' }}>Profile</span>
                    <span style={{ color: 'var(--text-primary)' }} className="capitalize">{form.costProfile}</span>
                  </div>
                  <div>
                    <span className="block" style={{ color: 'var(--text-tertiary)' }}>Features</span>
                    <span style={{ color: 'var(--text-primary)' }}>{form.selectedFeatures.length || 0}</span>
                  </div>
                  <div>
                    <span className="block" style={{ color: 'var(--text-tertiary)' }}>Complexity</span>
                    <span style={{ color: 'var(--text-primary)' }} className="capitalize">
                      {analysis?.complexity_estimate || 'Unknown'}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Validation hint */}
            {(!form.brief.trim() || !form.projectType) && (
              <p className="text-sm text-center" style={{ color: 'var(--text-tertiary)' }}>
                {!form.brief.trim()
                  ? 'Enter a project description to continue'
                  : 'Select a project type above to continue'}
              </p>
            )}

            {/* Error message */}
            {submitError && (
              <div className="flex items-start gap-2 rounded-lg p-3 bg-accent-error/10 border border-accent-error/30">
                <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0 text-accent-error" />
                <p className="text-sm text-accent-error">{submitError}</p>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              className="btn-iridescent w-full"
              disabled={!form.brief.trim() || !form.projectType || createProject.isPending}
            >
              {createProject.isPending ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Starting Build...
                </span>
              ) : (
                <span className="flex items-center justify-center gap-2">
                  <Rocket className="w-5 h-5" />
                  Start Building
                  <ArrowRight className="w-5 h-5" />
                </span>
              )}
            </button>
          </div>
        </div>
      </form>

      {/* Phase 11B: Template Browser Modal */}
      <TemplateBrowser
        isOpen={showTemplateBrowser}
        onClose={() => setShowTemplateBrowser(false)}
        onSelectTemplate={handleSelectTemplate}
      />
    </div>
  )
}
