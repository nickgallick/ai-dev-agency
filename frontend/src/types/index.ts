// All 10 supported project types
export type ProjectType = 
  | 'web_simple' 
  | 'web_complex'
  | 'mobile_native_ios'
  | 'mobile_cross_platform'
  | 'mobile_pwa'
  | 'desktop_app'
  | 'chrome_extension'
  | 'cli_tool'
  | 'python_api'
  | 'python_saas'

export type ProjectStatus =
  | 'pending'
  | 'intake'
  | 'research'
  | 'architect'
  | 'design'
  | 'code_generation'
  | 'qa'
  | 'deployment'
  | 'completed'
  | 'failed'
  | 'paused'
  | 'cancelled'

export type CostProfile = 'budget' | 'balanced' | 'premium'

export type AgentStatus = 'queued' | 'active' | 'completed' | 'failed'

export type RevisionScope = 'small_tweak' | 'medium_feature' | 'major_addition'

export type RevisionStatus = 'pending' | 'in_progress' | 'completed' | 'failed'

export interface Revision {
  id: string
  brief: string
  scope_type: RevisionScope
  status: RevisionStatus
  created_at: string
  completed_at?: string
  git_commit_sha?: string
  cost?: number
  affected_agents?: string[]
  files_modified?: string[]
  files_created?: string[]
  errors?: string[]
}

export interface Project {
  id: string
  name?: string
  brief: string
  project_type: ProjectType
  status: ProjectStatus
  cost_profile: CostProfile
  cost_estimate?: number
  github_repo?: string
  live_url?: string
  created_at: string
  updated_at: string
  completed_at?: string
  agent_outputs?: Record<string, any>
  revision_history?: Revision[]
  cost_breakdown?: Record<string, number>
}

export interface CostEstimate {
  min_cost: number
  max_cost: number
  expected_cost: number
  breakdown: Record<string, number>
  confidence: number
}

export interface AgentLog {
  id: string
  project_id: string
  agent_name: string
  model_used: string
  timestamp: string
  token_usage: number
  cost: number
  status: 'success' | 'error'
  input_data?: Record<string, any>
  output_data?: Record<string, any>
}

// Project type display info
export const PROJECT_TYPE_INFO: Record<ProjectType, { label: string; description: string }> = {
  web_simple: { label: 'Simple Website', description: 'Landing pages, portfolios, blogs' },
  web_complex: { label: 'Web Application', description: 'Dashboards, e-commerce, multi-page apps' },
  mobile_native_ios: { label: 'iOS Native App', description: 'Swift/SwiftUI apps' },
  mobile_cross_platform: { label: 'Cross-Platform Mobile', description: 'React Native or Flutter' },
  mobile_pwa: { label: 'Progressive Web App', description: 'Installable with offline support' },
  desktop_app: { label: 'Desktop Application', description: 'Electron, Tauri, or PyQt' },
  chrome_extension: { label: 'Chrome Extension', description: 'Browser extensions' },
  cli_tool: { label: 'CLI Tool', description: 'Command-line tools' },
  python_api: { label: 'REST API', description: 'FastAPI or Flask APIs' },
  python_saas: { label: 'Full-Stack SaaS', description: 'Complete Python SaaS' },
}
