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

export const api = {
  // Projects
  createProject: async (data: {
    brief: string
    name?: string
    cost_profile?: string
    reference_urls?: string[]
  }): Promise<Project> => {
    const response = await apiClient.post('/projects/', data)
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
}
