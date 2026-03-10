export type ProjectType = 'web_simple' | 'web_complex'

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
