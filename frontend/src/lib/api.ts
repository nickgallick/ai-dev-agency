import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface Project {
  id: string
  brief: string
  name?: string
  project_type?: string
  status: string
  cost_profile: string
  cost_estimate?: number
  github_repo?: string
  live_url?: string
  created_at: string
  updated_at?: string
  completed_at?: string
}

export interface AgentLog {
  id: string
  project_id: string
  agent_name: string
  agent_step?: number
  model_used: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  cost: number
  duration_ms: number
  timestamp: string
  status: string
  error_message?: string
}

export interface CostSummary {
  total_cost: number
  project_count: number
  avg_cost_per_project: number
}

export interface CostByAgent {
  agent_name: string
  total_cost: number
  call_count: number
}

export interface CostByModel {
  model: string
  total_cost: number
  prompt_tokens: number
  completion_tokens: number
  call_count: number
}

export interface CostTrend {
  date: string
  daily_cost: number
  call_count: number
}

// Phase 9A: Agent Performance Analytics Types
export interface AgentSuccessRate {
  agent_name: string
  total_executions: number
  successful_executions: number
  success_rate: number
  avg_execution_time_ms: number
  avg_revision_count: number
  avg_quality_score: number
  total_cost: number
}

export interface ModelComparison {
  agent_name: string
  model_used: string
  execution_count: number
  success_rate: number
  avg_execution_time_ms: number
  avg_revision_count: number
  avg_quality_score: number
  avg_cost: number
}

export interface BuildTimeWaterfall {
  agent_name: string
  total_time_ms: number
  avg_time_ms: number
  percentage_of_total: number
  execution_count: number
}

export interface QAFailurePattern {
  id: string
  pattern_hash: string
  pattern_type: string
  description: string
  sample_error: string | null
  causing_agent: string | null
  occurrence_count: number
  last_occurred: string
  first_occurred: string
  affected_projects: string[]
  is_resolved: boolean
  resolution_notes: string | null
}

export interface CostAccuracyStats {
  total_projects: number
  avg_accuracy: number | null
  avg_estimation_error: number | null
  underestimates: number
  overestimates: number
  by_project_type: Record<string, number>
  by_cost_profile: Record<string, number>
}

export interface CostAccuracyRecord {
  id: string
  project_id: string
  project_type: string
  cost_profile: string
  complexity_score: number
  estimated_cost: number
  actual_cost: number | null
  accuracy_percentage: number | null
  estimation_error: number | null
  estimated_at: string
  completed_at: string | null
}

export interface AnalyticsSummary {
  total_agent_executions: number
  overall_success_rate: number
  total_build_time_ms: number
  avg_build_time_ms: number
  top_performing_agent: string | null
  top_failure_pattern: string | null
  cost_accuracy_avg: number | null
  projects_tracked: number
}

// Phase 11A: Smart Intake Types
export interface BriefAnalysis {
  detected_project_type: string | null
  confidence: number
  suggested_features: string[]
  suggested_pages: string[]
  detected_industry: string | null
  complexity_estimate: string
  cost_estimate: Record<string, string>
  warnings: string[]
}

export interface Preset {
  id: string
  name: string
  description: string | null
  icon: string | null
  config: Record<string, any>
  use_count: number
  created_at: string
  updated_at: string
}

export interface PresetCreate {
  name: string
  description?: string
  icon?: string
  config: Record<string, any>
}

export interface ProjectRequirements {
  brief: string
  project_type: string
  name?: string
  cost_profile?: string
  industry?: string
  target_audience?: string
  reference_urls?: string[]
  design_preferences?: {
    color_scheme?: string
    primary_color?: string
    secondary_color?: string
    design_style?: string
    font_preference?: string
    enable_animations?: boolean
    glassmorphism?: boolean
  }
  figma_url?: string
  tech_stack?: {
    frontend_framework?: string
    css_framework?: string
    backend_framework?: string
    database?: string
    mobile_framework?: string
    desktop_framework?: string
    auth_provider?: string
    file_storage?: string
  }
  deployment?: {
    platform?: string
    auto_deploy?: boolean
    domain?: string
    submit_to_app_store?: boolean
    submit_to_play_store?: boolean
    build_for_mac?: boolean
    build_for_windows?: boolean
    build_for_linux?: boolean
    publish_to_npm?: boolean
    publish_to_pypi?: boolean
  }
  web_complex_options?: {
    key_features?: string[]
    pages?: string[]
    include_auth?: boolean
    include_dashboard?: boolean
    include_billing?: boolean
    include_email?: boolean
  }
  web_simple_options?: {
    num_pages?: number
    sections?: string[]
    include_contact_form?: boolean
    include_blog?: boolean
  }
  mobile_options?: {
    platforms?: string[]
    framework?: string
    submit_to_stores?: boolean
    include_push_notifications?: boolean
    include_offline_support?: boolean
  }
  cli_options?: {
    language?: string
    package_name?: string
    publish_to_registry?: boolean
  }
  desktop_options?: {
    target_platforms?: string[]
    framework?: string
    include_auto_update?: boolean
  }
  custom_instructions?: string
  template_id?: string
  build_mode?: string
  integration_config?: Record<string, any>
}

// Phase 11B: Template Types
export interface ProjectTemplate {
  id: string
  name: string
  description: string | null
  project_type: string
  industry: string | null
  thumbnail_url: string | null
  brief_template: string | null
  requirements: Record<string, any> | null
  design_tokens: Record<string, any> | null
  tech_stack: string[] | null
  features: string[] | null
  source_project_id: string | null
  is_auto_generated: boolean
  is_public: boolean
  qa_score: number | null
  build_success_count: number
  total_usage_count: number
  created_at: string | null
  is_active: boolean
  tags: string[] | null
}

export interface TemplateCreate {
  name: string
  description?: string
  project_type: string
  industry?: string
  brief_template?: string
  requirements?: Record<string, any>
  design_tokens?: Record<string, any>
  tech_stack?: string[]
  features?: string[]
  tags?: string[]
}

export interface UseTemplateRequest {
  name: string
  description?: string
  customizations?: Record<string, any>
}

// Phase 11B: Knowledge Base Types
export interface KnowledgeEntry {
  id: string
  entry_type: string
  title: string
  content: string
  project_id: string | null
  project_type: string | null
  industry: string | null
  tech_stack: string[] | null
  agent_name: string | null
  quality_score: number | null
  usage_count: number
  last_used_at: string | null
  created_at: string | null
  tags: string[] | null
  similarity_score?: number
}

export interface KnowledgeStats {
  total_entries: number
  entries_by_type: Record<string, number>
  entries_by_agent: Record<string, number>
  entries_by_project_type: Record<string, number>
  average_quality_score: number
  most_used_entries: Record<string, any>[]
  recent_entries: Record<string, any>[]
}

export interface PreferenceCreate {
  title: string
  preference: string
  category: string
  tags?: string[]
}

export interface SearchQuery {
  query: string
  entry_types?: string[]
  project_type?: string
  industry?: string
  agent_name?: string
  tech_stack?: string[]
  min_quality_score?: number
  limit?: number
}

// Brief wizard types
export interface BriefScoreResult {
  overall: number
  dimensions: Record<string, number>
  missing: string[]
  suggestions: string[]
  word_count: number
  quality_label: string
}

export interface EnhancedBriefResult {
  original: string
  enhanced: string
  additions: string[]
  score_before: number
  score_after: number
}

// Pre-execution estimation types
export interface AgentEstimate {
  agent_id: string
  model: string
  input_tokens: number
  output_tokens: number
  cost: number
  time_seconds: number
}

export interface PipelineEstimate {
  total_cost: number
  min_cost: number
  max_cost: number
  total_time_seconds: number
  total_time_display: string
  total_input_tokens: number
  total_output_tokens: number
  total_tokens: number
  confidence: number
  cost_profile: string
  project_type: string
  brief_tokens: number
  agents: AgentEstimate[]
}

export const api = {
  // Projects
  createProject: async (data: {
    brief: string
    name?: string
    cost_profile?: string
    project_type?: string
    reference_urls?: string[]
    figma_url?: string
    integration_config?: Record<string, any>
    requirements?: Partial<ProjectRequirements>
  }): Promise<Project> => {
    const response = await apiClient.post('/projects/', data)
    return response.data
  },

  // Brief wizard: scoring & enhancement
  scoreBrief: async (brief: string, projectType: string): Promise<BriefScoreResult> => {
    const response = await apiClient.post('/projects/score-brief', { brief, project_type: projectType })
    return response.data
  },

  enhanceBrief: async (data: {
    brief: string
    project_type: string
    detected_features?: string[]
    detected_pages?: string[]
  }): Promise<EnhancedBriefResult> => {
    const response = await apiClient.post('/projects/enhance-brief', data)
    return response.data
  },

  // Phase 11A: Brief Analysis
  analyzeBrief: async (brief: string): Promise<BriefAnalysis> => {
    const response = await apiClient.post('/projects/analyze-brief', { brief })
    return response.data
  },

  // Pre-execution cost & time estimation
  estimateProject: async (data: {
    brief: string
    project_type: string
    cost_profile: string
    num_features?: number
    num_pages?: number
  }): Promise<PipelineEstimate> => {
    const response = await apiClient.post('/projects/estimate', data)
    return response.data
  },

  getProjects: async (params?: { limit?: number; status?: string }): Promise<Project[]> => {
    const response = await apiClient.get('/projects/', { params })
    return response.data
  },

  getProject: async (id: string): Promise<Project> => {
    const response = await apiClient.get(`/projects/${id}`)
    return response.data
  },

  getProjectOutputs: async (id: string): Promise<{ project_id: string; agent_outputs: Record<string, any> }> => {
    const response = await apiClient.get(`/projects/${id}/outputs`)
    return response.data
  },

  // Phase 11A: Presets
  getPresets: async (includeDefaults: boolean = true): Promise<Preset[]> => {
    const response = await apiClient.get('/presets/', { params: { include_defaults: includeDefaults } })
    return response.data
  },

  getPreset: async (id: string): Promise<Preset> => {
    const response = await apiClient.get(`/presets/${id}`)
    return response.data
  },

  createPreset: async (data: PresetCreate): Promise<Preset> => {
    const response = await apiClient.post('/presets/', data)
    return response.data
  },

  updatePreset: async (id: string, data: Partial<PresetCreate>): Promise<Preset> => {
    const response = await apiClient.put(`/presets/${id}`, data)
    return response.data
  },

  deletePreset: async (id: string): Promise<void> => {
    await apiClient.delete(`/presets/${id}`)
  },

  usePreset: async (id: string): Promise<Preset> => {
    const response = await apiClient.post(`/presets/${id}/use`)
    return response.data
  },

  // Agent Logs
  getAgentLogs: async (params?: {
    project_id?: string
    agent_name?: string
    limit?: number
  }): Promise<AgentLog[]> => {
    const response = await apiClient.get('/agents/logs', { params })
    return response.data
  },

  // Costs
  getCostSummary: async (): Promise<CostSummary> => {
    const response = await apiClient.get('/costs/summary')
    return response.data
  },

  getCostsByAgent: async (): Promise<CostByAgent[]> => {
    const response = await apiClient.get('/costs/by-agent')
    return response.data
  },

  getCostsByModel: async (): Promise<CostByModel[]> => {
    const response = await apiClient.get('/costs/by-model')
    return response.data
  },

  getCostTrends: async (days: number = 30): Promise<CostTrend[]> => {
    const response = await apiClient.get('/costs/trends', { params: { days } })
    return response.data
  },

  // Phase 9A: Agent Performance Analytics
  getAgentSuccessRates: async (days: number = 30, limit: number = 20): Promise<AgentSuccessRate[]> => {
    const response = await apiClient.get('/analytics/agent-success-rates', { params: { days, limit } })
    return response.data
  },

  getModelComparison: async (agentName?: string, days: number = 30): Promise<ModelComparison[]> => {
    const response = await apiClient.get('/analytics/model-comparison', { 
      params: { agent_name: agentName, days } 
    })
    return response.data
  },

  getBuildTimeWaterfall: async (projectId?: string, days: number = 30): Promise<BuildTimeWaterfall[]> => {
    if (projectId) {
      const response = await apiClient.get(`/analytics/build-time-waterfall/${projectId}`)
      return response.data
    }
    const response = await apiClient.get('/analytics/build-time-waterfall', { params: { days } })
    return response.data
  },

  getQAFailurePatterns: async (limit: number = 10, includeResolved: boolean = false): Promise<QAFailurePattern[]> => {
    const response = await apiClient.get('/analytics/qa-failure-patterns', { 
      params: { limit, include_resolved: includeResolved } 
    })
    return response.data
  },

  resolveQAPattern: async (patternId: string, resolutionNotes?: string): Promise<void> => {
    await apiClient.patch(`/analytics/qa-failure-patterns/${patternId}/resolve`, null, {
      params: { resolution_notes: resolutionNotes }
    })
  },

  getCostAccuracyStats: async (
    projectType?: string, 
    costProfile?: string, 
    days: number = 90
  ): Promise<CostAccuracyStats> => {
    const response = await apiClient.get('/analytics/cost-accuracy', { 
      params: { project_type: projectType, cost_profile: costProfile, days } 
    })
    return response.data
  },

  getCostAccuracyData: async (limit: number = 50): Promise<CostAccuracyRecord[]> => {
    const response = await apiClient.get('/analytics/cost-accuracy/data', { params: { limit } })
    return response.data
  },

  getAnalyticsSummary: async (days: number = 30): Promise<AnalyticsSummary> => {
    const response = await apiClient.get('/analytics/summary', { params: { days } })
    return response.data
  },

  // Phase 11B: Templates
  getTemplates: async (params?: {
    project_type?: string
    industry?: string
    is_public?: boolean
    search?: string
    limit?: number
    offset?: number
  }): Promise<ProjectTemplate[]> => {
    const response = await apiClient.get('/templates', { params })
    return response.data
  },

  getTemplate: async (id: string): Promise<ProjectTemplate> => {
    const response = await apiClient.get(`/templates/${id}`)
    return response.data
  },

  createTemplate: async (data: TemplateCreate): Promise<ProjectTemplate> => {
    const response = await apiClient.post('/templates', data)
    return response.data
  },

  createTemplateFromProject: async (projectId: string, name?: string): Promise<ProjectTemplate> => {
    const response = await apiClient.post(`/templates/from-project/${projectId}`, null, {
      params: { name }
    })
    return response.data
  },

  updateTemplate: async (id: string, data: Partial<TemplateCreate>): Promise<ProjectTemplate> => {
    const response = await apiClient.put(`/templates/${id}`, data)
    return response.data
  },

  deleteTemplate: async (id: string): Promise<void> => {
    await apiClient.delete(`/templates/${id}`)
  },

  useTemplate: async (templateId: string, data: UseTemplateRequest): Promise<{ 
    status: string
    template_id: string
    project_data: Record<string, any>
  }> => {
    const response = await apiClient.post(`/templates/${templateId}/use`, data)
    return response.data
  },

  // Phase 11B: Knowledge Base
  getKnowledgeStats: async (): Promise<KnowledgeStats> => {
    const response = await apiClient.get('/knowledge/stats')
    return response.data
  },

  searchKnowledge: async (query: SearchQuery): Promise<KnowledgeEntry[]> => {
    const response = await apiClient.post('/knowledge/search', query)
    return response.data
  },

  storePreference: async (data: PreferenceCreate): Promise<KnowledgeEntry> => {
    const response = await apiClient.post('/knowledge/preference', data)
    return response.data
  },

  getKnowledgeEntries: async (params?: {
    entry_type?: string
    agent_name?: string
    project_type?: string
    limit?: number
    offset?: number
  }): Promise<KnowledgeEntry[]> => {
    const response = await apiClient.get('/knowledge/entries', { params })
    return response.data
  },

  getKnowledgeEntry: async (id: string): Promise<KnowledgeEntry> => {
    const response = await apiClient.get(`/knowledge/entry/${id}`)
    return response.data
  },

  updateKnowledgeQuality: async (id: string, qualityScore: number): Promise<void> => {
    await apiClient.put(`/knowledge/entry/${id}/quality`, null, {
      params: { quality_score: qualityScore }
    })
  },

  deleteKnowledgeEntry: async (id: string): Promise<void> => {
    await apiClient.delete(`/knowledge/entry/${id}`)
  },

  getKnowledgeEntryTypes: async (): Promise<{ types: { value: string; name: string }[] }> => {
    const response = await apiClient.get('/knowledge/types')
    return response.data
  },

  // ==================== Phase 11C: Advanced Features ====================

  // Checkpoint APIs
  getCheckpointStatus: async (projectId: string): Promise<CheckpointStatus> => {
    const response = await apiClient.get(`/checkpoints/${projectId}/status`)
    return response.data
  },

  setCheckpointMode: async (projectId: string, mode: string, customCheckpoints?: string[]): Promise<void> => {
    await apiClient.post(`/checkpoints/${projectId}/mode`, {
      mode,
      custom_checkpoints: customCheckpoints
    })
  },

  pauseProject: async (projectId: string): Promise<void> => {
    await apiClient.post(`/checkpoints/${projectId}/pause`)
  },

  resumeProject: async (projectId: string, editedOutput?: Record<string, any>): Promise<void> => {
    await apiClient.post(`/checkpoints/${projectId}/resume`, {
      edited_output: editedOutput
    })
  },

  editAndReplay: async (projectId: string, editedOutput: Record<string, any>, replayFromAgent?: string): Promise<void> => {
    await apiClient.post(`/checkpoints/${projectId}/edit-and-replay`, {
      edited_output: editedOutput,
      replay_from_agent: replayFromAgent
    })
  },

  restartFromAgent: async (projectId: string, agentName: string): Promise<void> => {
    await apiClient.post(`/checkpoints/${projectId}/restart-from/${agentName}`)
  },

  clearCheckpoints: async (projectId: string): Promise<void> => {
    await apiClient.delete(`/checkpoints/${projectId}/checkpoints`)
  },

  // Queue APIs
  getQueueStatus: async (): Promise<QueueStatus> => {
    const response = await apiClient.get('/queue/status')
    return response.data
  },

  getProjectQueueStatus: async (projectId: string): Promise<ProjectQueueStatus> => {
    const response = await apiClient.get(`/queue/${projectId}/status`)
    return response.data
  },

  enqueueProject: async (projectId: string, priority: string = 'normal'): Promise<EnqueueResult> => {
    const response = await apiClient.post('/queue/enqueue', {
      project_id: projectId,
      priority
    })
    return response.data
  },

  removeFromQueue: async (projectId: string): Promise<void> => {
    await apiClient.delete(`/queue/${projectId}`)
  },

  reprioritizeProject: async (projectId: string, priority: string): Promise<void> => {
    await apiClient.post(`/queue/${projectId}/reprioritize`, { priority })
  },

  moveProjectInQueue: async (projectId: string, direction: 'up' | 'down'): Promise<void> => {
    await apiClient.post(`/queue/${projectId}/move`, { direction })
  },

  getQueueStats: async (): Promise<QueueStats> => {
    const response = await apiClient.get('/queue/stats')
    return response.data
  },

  // Export APIs
  getProjectArtifacts: async (projectId: string): Promise<ProjectArtifacts> => {
    const response = await apiClient.get(`/export/projects/${projectId}/artifacts`)
    return response.data
  },

  getExportableFiles: async (projectId: string): Promise<ExportableFiles> => {
    const response = await apiClient.get(`/export/projects/${projectId}/files`)
    return response.data
  },

  exportProject: async (projectId: string): Promise<Blob> => {
    const response = await apiClient.get(`/export/projects/${projectId}`, {
      responseType: 'blob'
    })
    return response.data
  },

  importProject: async (file: File): Promise<ImportResult> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiClient.post('/export/projects/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  },

  // System Backup APIs
  createBackup: async (destination: string = 'local', bucketName?: string, includeProjects: boolean = false): Promise<BackupResult> => {
    const response = await apiClient.post('/export/system/backup', {
      destination,
      bucket_name: bucketName,
      include_projects: includeProjects
    })
    return response.data
  },

  listBackups: async (): Promise<{ backups: BackupInfo[] }> => {
    const response = await apiClient.get('/export/system/backups')
    return response.data
  },

  restoreBackup: async (backupPath: string, restoreDatabase: boolean = true, restoreFiles: boolean = true): Promise<RestoreResult> => {
    const response = await apiClient.post('/export/system/restore', {
      backup_path: backupPath,
      restore_database: restoreDatabase,
      restore_files: restoreFiles
    })
    return response.data
  },

  exportKnowledge: async (includeEmbeddings: boolean = false): Promise<Blob> => {
    const response = await apiClient.get('/export/knowledge', {
      params: { include_embeddings: includeEmbeddings },
      responseType: 'blob'
    })
    return response.data
  },

  importKnowledge: async (file: File, merge: boolean = true): Promise<KnowledgeImportResult> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiClient.post('/export/knowledge/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      params: { merge }
    })
    return response.data
  },
}

// Phase 11C Types
export interface CheckpointStatus {
  project_id: string
  mode: string
  state: string
  paused_at?: string
  paused_at_agent?: string
  current_checkpoint?: Record<string, any>
  checkpoint_history: Record<string, any>[]
  custom_checkpoints: string[]
  available_checkpoints: string[]
}

export interface QueueStatus {
  queue_length: number
  active_count: number
  max_concurrent: number
  has_capacity: boolean
  queue_items: QueueItem[]
  active_projects: Record<string, any>[]
}

export interface QueueItem {
  project_id: string
  priority: string
  queued_at: string
  position: number
  estimated_wait_seconds: number
}

export interface ProjectQueueStatus {
  project_id: string
  in_queue: boolean
  position?: number
  priority?: string
  estimated_wait_seconds?: number
}

export interface EnqueueResult {
  success: boolean
  project_id: string
  position: number
  priority: string
  estimated_wait_seconds: number
}

export interface QueueStats {
  queue_length: number
  active_count: number
  max_concurrent: number
  capacity_available: boolean
  by_priority: {
    urgent: number
    normal: number
    background: number
  }
  average_wait_seconds: number
}

export interface ProjectArtifacts {
  project_id: string
  project_type: string | null
  project_name: string | null
  status: string | null
  live_url: string | null
  github_repo: string | null
  deployment_urls: { platform: string; url: string; status: string }[]
  readme_content: string | null
  file_structure: string[]
  has_local_files: boolean
}

export interface ExportableFiles {
  project_id: string
  files: { path: string; size: number; type: string }[]
  total_size_bytes: number
  file_count: number
}

export interface ImportResult {
  success: boolean
  project_id: string
  message: string
}

export interface BackupResult {
  success: boolean
  destination: string
  path?: string
  bucket?: string
  key?: string
  size_bytes?: number
  created_at?: string
  error?: string
}

export interface BackupInfo {
  filename: string
  path: string
  size_bytes: number
  created_at: string
}

export interface RestoreResult {
  success: boolean
  backup_version?: string
  backup_created_at?: string
  restored: {
    tables: string[]
    directories: string[]
    errors: string[]
  }
}

export interface KnowledgeImportResult {
  success: boolean
  imported: number
  skipped: number
  errors: string[]
}
