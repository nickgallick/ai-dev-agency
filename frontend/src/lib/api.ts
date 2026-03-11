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

export interface AutonomyTier {
  id: string
  label: string
  description: string
  checkpoint_agents: string[]
  auto_continue_timeout: number
  allow_output_editing: boolean
}

// Pipeline Plan types (#13)
export interface PlanAgent {
  agent_id: string
  description: string
  dependencies: string[]
  parallel_group: string | null
  skipped: boolean
  required: boolean
  is_checkpoint: boolean
  model: string
  estimated_cost: number
  estimated_time_seconds: number
  estimated_input_tokens: number
  estimated_output_tokens: number
}

export interface PlanSummary {
  total_agents: number
  active_agents: number
  skipped_agents: number
  checkpoint_count: number
  total_cost: number
  active_cost: number
  min_cost: number
  max_cost: number
  total_time_display: string
  total_time_seconds: number
  total_tokens: number
  confidence: number
}

export interface PipelinePlan {
  project_type: string
  cost_profile: string
  autonomy_tier: string
  agents: PlanAgent[]
  summary: PlanSummary
}

export const api = {
  // Autonomy tiers (#26)
  getAutonomyTiers: async (): Promise<AutonomyTier[]> => {
    const response = await apiClient.get('/health/autonomy-tiers')
    return response.data.tiers
  },

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
    pipeline_plan?: { skipped_agents: string[] }
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

  // Pipeline plan generation (#13)
  generatePlan: async (data: {
    brief: string
    project_type: string
    cost_profile: string
    num_features?: number
    num_pages?: number
    build_mode?: string
  }): Promise<PipelinePlan> => {
    const response = await apiClient.post('/projects/generate-plan', data)
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

  // ── Conversational Clarification System ─────────────────────────────

  sendChatMessage: async (message: string, conversationId?: string): Promise<ChatMessageResponse> => {
    const response = await apiClient.post('/chat/', { message, conversation_id: conversationId })
    return response.data
  },

  getChatHistory: async (conversationId: string): Promise<ChatMessage[]> => {
    const response = await apiClient.get(`/chat/${conversationId}`)
    return response.data
  },

  startBuildFromChat: async (params: { conversation_id: string; project_type?: string; cost_profile?: string; name?: string }): Promise<StartBuildResponse> => {
    const response = await apiClient.post('/chat/start-build', params)
    return response.data
  },

  answerInterrupt: async (projectId: string, answer: string): Promise<{ status: string }> => {
    const response = await apiClient.post(`/chat/interrupt/${projectId}/answer`, { answer })
    return response.data
  },

  getInterruptStatus: async (projectId: string): Promise<InterruptStatus> => {
    const response = await apiClient.get(`/chat/interrupt/${projectId}/status`)
    return response.data
  },

  // ── Project History Timeline (#6) ─────────────────────────────────

  getProjectCheckpoints: async (projectId: string): Promise<{ project_id: string; checkpoints: CheckpointEntry[] }> => {
    const response = await apiClient.get(`/projects/${projectId}/checkpoints`)
    return response.data
  },

  getProjectAuditLog: async (projectId: string, eventType?: string, limit: number = 200): Promise<{ project_id: string; entries: AuditLogEntry[] }> => {
    const response = await apiClient.get(`/projects/${projectId}/audit-log`, {
      params: { event_type: eventType, limit },
    })
    return response.data
  },

  // ── Persistent Project Memory (#12) ────────────────────────────────

  getProjectMemory: async (projectId: string, category?: string): Promise<MemoryEntry[]> => {
    const response = await apiClient.get(`/projects/${projectId}/memory`, {
      params: { category },
    })
    return response.data
  },

  createMemoryEntry: async (projectId: string, data: MemoryEntryCreate): Promise<MemoryEntry> => {
    const response = await apiClient.post(`/projects/${projectId}/memory`, data)
    return response.data
  },

  updateMemoryEntry: async (projectId: string, entryId: string, data: Partial<MemoryEntryCreate>): Promise<MemoryEntry> => {
    const response = await apiClient.put(`/projects/${projectId}/memory/${entryId}`, data)
    return response.data
  },

  deleteMemoryEntry: async (projectId: string, entryId: string): Promise<void> => {
    await apiClient.delete(`/projects/${projectId}/memory/${entryId}`)
  },

  getMemoryCategories: async (): Promise<{ categories: MemoryCategory[] }> => {
    const response = await apiClient.get('/projects/_/memory/categories')
    return response.data
  },

  getMemorySummary: async (projectId: string): Promise<MemorySummary> => {
    const response = await apiClient.get(`/projects/${projectId}/memory/summary`)
    return response.data
  },

  // ── Automated Browser Testing (#11) ─────────────────────────────

  runBrowserTest: async (projectId: string, options?: {
    url?: string
    viewport?: string
    record_video?: boolean
    take_screenshots?: boolean
    test_interactions?: boolean
    test_themes?: boolean
    max_duration_seconds?: number
  }): Promise<BrowserTestResult> => {
    const response = await apiClient.post(`/projects/${projectId}/browser-tests`, options || {})
    return response.data
  },

  getBrowserTestHistory: async (projectId: string, limit: number = 10): Promise<BrowserTestHistory> => {
    const response = await apiClient.get(`/projects/${projectId}/browser-tests`, { params: { limit } })
    return response.data
  },

  // ── Shareable Preview Links (#22) ───────────────────────────────

  createShareLink: async (projectId: string, options?: {
    expires_in_days?: number
    include_outputs?: boolean
    include_code?: boolean
    include_qa?: boolean
    label?: string
  }): Promise<ShareLinkData> => {
    const response = await apiClient.post(`/projects/${projectId}/share`, options || {})
    return response.data
  },

  getShareLinks: async (projectId: string): Promise<{ project_id: string; links: ShareLinkData[] }> => {
    const response = await apiClient.get(`/projects/${projectId}/share`)
    return response.data
  },

  revokeShareLink: async (projectId: string, shareId: string): Promise<void> => {
    await apiClient.delete(`/projects/${projectId}/share/${shareId}`)
  },

  // ── Figma & Screenshot Import (#23) ─────────────────────────────

  importFromFigma: async (projectId: string, data: {
    figma_url: string
    extract_colors?: boolean
    extract_typography?: boolean
    extract_spacing?: boolean
    extract_components?: boolean
  }): Promise<FigmaImportResult> => {
    const response = await apiClient.post(`/projects/${projectId}/design-import/figma`, data)
    return response.data
  },

  uploadDesignScreenshot: async (projectId: string, file: File): Promise<ScreenshotAnalysisResult> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiClient.post(`/projects/${projectId}/design-import/screenshot`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  getDesignTokens: async (projectId: string): Promise<DesignTokensData> => {
    const response = await apiClient.get(`/projects/${projectId}/design-import/tokens`)
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

// Conversational Clarification System Types
export interface ChatMessage {
  role: 'user' | 'assistant'
  message: string
  timestamp?: string
  ready_to_build?: boolean
}

export interface ChatMessageResponse {
  conversation_id: string
  role: string
  message: string
  ready_to_build: boolean
  suggestions: string[]
}

export interface StartBuildResponse {
  project_id: string
  brief: string
  name?: string
}

export interface InterruptStatus {
  has_question: boolean
  question?: string
  context?: string
  agent_name?: string
  asked_at?: string
}

// Project History Timeline (#6)
export interface CheckpointEntry {
  id: string
  project_id: string
  agent_name: string
  agent_status: string
  node_states: Record<string, any>
  pipeline_context?: Record<string, any>
  pipeline_config?: Record<string, any>
  total_cost: number
  cost_breakdown?: Record<string, number>
  step_number: number
  created_at: string
}

export interface AuditLogEntry {
  id: string
  event_type: string
  agent_name: string | null
  message: string
  details: Record<string, any> | null
  timestamp: string | null
  duration_ms: string | null
}

// Persistent Project Memory (#12)
export interface MemoryEntry {
  id: string
  category: string
  title: string
  content: string
  agent_name: string | null
  quality_score: number | null
  usage_count: number
  tags: string[] | null
  created_at: string | null
  updated_at: string | null
}

export interface MemoryEntryCreate {
  category: string
  title: string
  content: string
  tags?: string[]
}

export interface MemoryCategory {
  value: string
  label: string
  description: string
}

export interface MemorySummary {
  project_id: string
  total_entries: number
  by_category: Record<string, { title: string; content: string }[]>
}

// Automated Browser Testing (#11)
export interface BrowserTestStep {
  step: number
  action: string
  selector?: string
  description: string
  status: string
  screenshot_path?: string
  error?: string
  duration_ms: number
}

export interface BrowserTestResult {
  id: string
  project_id: string
  url: string
  viewport: string
  status: string
  started_at: string
  completed_at: string
  duration_ms: number
  steps: BrowserTestStep[]
  video_path?: string
  screenshots: string[]
  console_errors: string[]
  network_errors: string[]
  accessibility_issues: Record<string, any>[]
  performance_metrics: Record<string, any>
  summary: Record<string, any>
}

export interface BrowserTestHistory {
  project_id: string
  tests: Record<string, any>[]
  total: number
}

// Shareable Preview Links (#22)
export interface ShareLinkData {
  id: string
  project_id: string
  share_url: string
  token: string
  label?: string
  created_at: string
  expires_at: string
  include_outputs: boolean
  include_code: boolean
  include_qa: boolean
  is_active: boolean
  view_count: number
}

// Figma & Screenshot Import (#23)
export interface FigmaImportResult {
  status: string
  figma_file_key?: string
  figma_file_name?: string
  tokens: DesignTokensData
  pages_found: number
  components_found: number
  styles_found: number
}

export interface ScreenshotAnalysisResult {
  status: string
  filename: string
  tokens: DesignTokensData
  screenshot_path: string
}

export interface DesignTokensData {
  source: string
  colors: Record<string, any>
  typography: Record<string, any>
  spacing: Record<string, any>
  components: Record<string, any>[]
  layout_description: string
  style_analysis: string
}
