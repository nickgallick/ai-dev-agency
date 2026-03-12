/**
 * ChatBuilder — Lovable/Deep Agent style chat-first project builder
 * Split-pane: chat on left, live preview on right
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, ChatMessage, Project } from '@/lib/api'
import BuildPreviewPanel from '@/components/BuildPreviewPanel'
import {
  Send, Loader2, Sparkles, Bot, User, ArrowRight,
  PanelRightOpen, PanelRightClose, Zap
} from 'lucide-react'

// Quick-start suggestion prompts
const SUGGESTIONS = [
  'Build me a SaaS dashboard with auth and billing',
  'Create a portfolio website with a blog',
  'Build a REST API for a todo app',
  'Make a Chrome extension that summarizes pages',
]

interface ChatEntry {
  role: 'user' | 'assistant' | 'system'
  message: string
  timestamp: string
  agentName?: string
  agentStatus?: 'running' | 'completed' | 'failed'
}

export default function ChatBuilder() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { projectId: urlProjectId } = useParams<{ projectId?: string }>()

  // Chat state
  const [messages, setMessages] = useState<ChatEntry[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [readyToBuild, setReadyToBuild] = useState(false)
  const [suggestions, setSuggestions] = useState<string[]>([])

  // Build state
  const [projectId, setProjectId] = useState<string | null>(urlProjectId || null)
  const [buildStarted, setBuildStarted] = useState(false)
  const [showPreview, setShowPreview] = useState(true)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // If we have a projectId from URL, we're viewing an existing build
  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => api.getProject(projectId!),
    enabled: !!projectId,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status === 'completed' || status === 'failed') return false
      return 3000
    },
  })

  const { data: outputs } = useQuery({
    queryKey: ['projectOutputs', projectId],
    queryFn: () => api.getProjectOutputs(projectId!),
    enabled: !!projectId && buildStarted,
    refetchInterval: (query) => {
      if (project?.status === 'completed' || project?.status === 'failed') return false
      return 4000
    },
  })

  // Mid-pipeline clarification
  const { data: interruptStatus } = useQuery({
    queryKey: ['interruptStatus', projectId],
    queryFn: () => api.getInterruptStatus(projectId!),
    enabled: !!projectId && buildStarted && project?.status !== 'completed' && project?.status !== 'failed',
    refetchInterval: 3000,
  })

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Track agent progress as chat messages
  useEffect(() => {
    if (!outputs?.agent_outputs || !buildStarted) return

    const agentNames = Object.keys(outputs.agent_outputs)
    const existingAgentMessages = messages.filter(m => m.role === 'system' && m.agentName)

    for (const agentName of agentNames) {
      const output = outputs.agent_outputs[agentName]
      const existing = existingAgentMessages.find(m => m.agentName === agentName)

      if (!existing) {
        const label = agentName.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
        setMessages(prev => [...prev, {
          role: 'system',
          message: `${label} completed`,
          timestamp: new Date().toISOString(),
          agentName,
          agentStatus: 'completed',
        }])
      }
    }
  }, [outputs?.agent_outputs, buildStarted])

  // Show build complete message
  useEffect(() => {
    if (project?.status === 'completed' && buildStarted) {
      const alreadyHasComplete = messages.some(m => m.message.includes('build is complete'))
      if (!alreadyHasComplete) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          message: 'Your build is complete! Check the preview panel to see the results. You can view the full project details or start a new build.',
          timestamp: new Date().toISOString(),
        }])
      }
    }
    if (project?.status === 'failed' && buildStarted) {
      const alreadyHasFailed = messages.some(m => m.message.includes('encountered an issue'))
      if (!alreadyHasFailed) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          message: 'The build encountered an issue. You can check the preview panel for details, or try describing what you want differently.',
          timestamp: new Date().toISOString(),
        }])
      }
    }
  }, [project?.status, buildStarted])

  // Handle mid-pipeline clarification
  useEffect(() => {
    if (interruptStatus?.has_question && interruptStatus.question) {
      const alreadyAsked = messages.some(m => m.message === interruptStatus.question)
      if (!alreadyAsked) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          message: interruptStatus.question!,
          timestamp: new Date().toISOString(),
          agentName: interruptStatus.agent_name,
        }])
      }
    }
  }, [interruptStatus])

  const sendMessage = useCallback(async (text?: string) => {
    const msg = text || input.trim()
    if (!msg || sending) return

    // If there's a pending clarification, answer it
    if (interruptStatus?.has_question && projectId) {
      setMessages(prev => [...prev, {
        role: 'user',
        message: msg,
        timestamp: new Date().toISOString(),
      }])
      setInput('')
      setSending(true)
      try {
        await api.answerInterrupt(projectId, msg)
        queryClient.invalidateQueries({ queryKey: ['interruptStatus', projectId] })
      } catch (e) {
        console.error('Failed to answer clarification:', e)
      } finally {
        setSending(false)
      }
      return
    }

    // Add user message
    setMessages(prev => [...prev, {
      role: 'user',
      message: msg,
      timestamp: new Date().toISOString(),
    }])
    setInput('')
    setSending(true)

    try {
      const response = await api.sendChatMessage(msg, conversationId || undefined)
      setConversationId(response.conversation_id)
      setReadyToBuild(response.ready_to_build)
      if (response.suggestions?.length) {
        setSuggestions(response.suggestions)
      }

      setMessages(prev => [...prev, {
        role: 'assistant',
        message: response.message,
        timestamp: new Date().toISOString(),
      }])

      // Auto-start build when AI says we're ready
      if (response.ready_to_build) {
        startBuild(response.conversation_id)
      }
    } catch (e: any) {
      // If chat endpoint fails, create project directly from the message
      setMessages(prev => [...prev, {
        role: 'assistant',
        message: "Got it! I'll start building that for you now.",
        timestamp: new Date().toISOString(),
      }])
      await createDirectProject(msg)
    } finally {
      setSending(false)
    }
  }, [input, sending, conversationId, interruptStatus, projectId])

  const startBuild = async (convId: string) => {
    try {
      setMessages(prev => [...prev, {
        role: 'system',
        message: 'Starting your build...',
        timestamp: new Date().toISOString(),
        agentStatus: 'running',
      }])

      const result = await api.startBuildFromChat({
        conversation_id: convId,
        cost_profile: 'balanced',
      })

      setProjectId(result.project_id)
      setBuildStarted(true)
      setShowPreview(true)

      setMessages(prev => [...prev, {
        role: 'assistant',
        message: `Building "${result.name || 'your project'}" — I'll show progress as each agent completes.`,
        timestamp: new Date().toISOString(),
      }])
    } catch (e) {
      console.error('Failed to start build:', e)
      setMessages(prev => [...prev, {
        role: 'assistant',
        message: 'Had trouble starting the build. Let me try a different approach...',
        timestamp: new Date().toISOString(),
      }])
    }
  }

  const createDirectProject = async (brief: string) => {
    try {
      const project = await api.createProject({
        brief,
        cost_profile: 'balanced',
      })
      setProjectId(project.id)
      setBuildStarted(true)
      setShowPreview(true)

      setMessages(prev => [...prev, {
        role: 'system',
        message: 'Build started',
        timestamp: new Date().toISOString(),
        agentStatus: 'running',
      }])
    } catch (e) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        message: 'Something went wrong starting the build. Please check your API keys in Settings and try again.',
        timestamp: new Date().toISOString(),
      }])
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const isBuilding = buildStarted && project?.status !== 'completed' && project?.status !== 'failed'

  return (
    <div className="chat-builder">
      {/* Chat Panel */}
      <div className="chat-panel">
        {/* Chat Messages */}
        <div className="chat-messages">
          {messages.length === 0 ? (
            <div className="chat-empty">
              <div className="chat-empty-icon">
                <Sparkles className="w-8 h-8" />
              </div>
              <h2>What do you want to build?</h2>
              <p>Describe your project and I'll build it for you with AI agents.</p>
              <div className="chat-suggestions">
                {SUGGESTIONS.map((s, i) => (
                  <button
                    key={i}
                    className="chat-suggestion"
                    onClick={() => sendMessage(s)}
                  >
                    <Zap className="w-3.5 h-3.5" />
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="chat-message-list">
              {messages.map((msg, i) => (
                <div key={i} className={`chat-message chat-message-${msg.role}`}>
                  {msg.role === 'user' ? (
                    <>
                      <div className="chat-message-content">
                        <p>{msg.message}</p>
                      </div>
                      <div className="chat-avatar chat-avatar-user">
                        <User className="w-4 h-4" />
                      </div>
                    </>
                  ) : msg.role === 'system' ? (
                    <div className="chat-system-message">
                      {msg.agentStatus === 'running' && (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      )}
                      {msg.agentStatus === 'completed' && (
                        <div className="chat-agent-dot completed" />
                      )}
                      {msg.agentStatus === 'failed' && (
                        <div className="chat-agent-dot failed" />
                      )}
                      <span>{msg.message}</span>
                    </div>
                  ) : (
                    <>
                      <div className="chat-avatar chat-avatar-ai">
                        <Bot className="w-4 h-4" />
                      </div>
                      <div className="chat-message-content">
                        <p>{msg.message}</p>
                      </div>
                    </>
                  )}
                </div>
              ))}

              {sending && (
                <div className="chat-message chat-message-assistant">
                  <div className="chat-avatar chat-avatar-ai">
                    <Bot className="w-4 h-4" />
                  </div>
                  <div className="chat-typing">
                    <span /><span /><span />
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="chat-input-area">
          {suggestions.length > 0 && !buildStarted && (
            <div className="chat-input-suggestions">
              {suggestions.map((s, i) => (
                <button key={i} className="chat-suggestion-pill" onClick={() => sendMessage(s)}>
                  {s}
                </button>
              ))}
            </div>
          )}
          <div className="chat-input-wrapper">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                interruptStatus?.has_question
                  ? 'Answer the question above...'
                  : buildStarted
                    ? 'Ask a question about your build...'
                    : 'Describe what you want to build...'
              }
              rows={1}
              className="chat-input"
              disabled={sending}
            />
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || sending}
              className="chat-send-btn"
            >
              {sending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <ArrowRight className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Preview Panel */}
      {showPreview && (projectId || buildStarted) && (
        <div className="preview-panel">
          <BuildPreviewPanel
            projectId={projectId}
            project={project || null}
            outputs={outputs?.agent_outputs || null}
            isBuilding={isBuilding}
          />
        </div>
      )}

      {/* Toggle preview panel button */}
      {projectId && (
        <button
          className="preview-toggle-btn"
          onClick={() => setShowPreview(!showPreview)}
          title={showPreview ? 'Hide preview' : 'Show preview'}
        >
          {showPreview ? (
            <PanelRightClose className="w-4 h-4" />
          ) : (
            <PanelRightOpen className="w-4 h-4" />
          )}
        </button>
      )}
    </div>
  )
}
