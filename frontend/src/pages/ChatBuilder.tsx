/**
 * ChatBuilder — Lovable/Deep Agent style chat-first project builder
 * Split-pane: chat on left, live preview on right
 * Design: Framer Motion animations, glassmorphic glass panels,
 *         warm/cool chat bubbles matching sleek-chat-soul reference
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { api, ChatMessage, Project } from '@/lib/api'
import BuildPreviewPanel from '@/components/BuildPreviewPanel'
import {
  Send, Loader2, Sparkles, Bot, User, ArrowRight,
  PanelRightOpen, PanelRightClose, Zap, Lightbulb,
  FileCode, Smartphone, Globe
} from 'lucide-react'

// Quick-start suggestion prompts with distinct icons
const SUGGESTIONS = [
  { text: 'Build me a SaaS dashboard with auth and billing', icon: Globe },
  { text: 'Create a portfolio website with a blog', icon: FileCode },
  { text: 'Build a REST API for a todo app', icon: Lightbulb },
  { text: 'Make a Chrome extension that summarizes pages', icon: Smartphone },
]

// Agent descriptions for source-citation-style pills
const AGENT_DESCRIPTIONS: Record<string, string> = {
  intake: 'Classified project type & requirements',
  research: 'Analyzed market & technical landscape',
  architect: 'Designed system architecture',
  design_system: 'Created design tokens & component specs',
  asset_generation: 'Generated visual assets',
  content_generation: 'Wrote copy & content',
  project_manager: 'Reviewed checkpoint quality',
  code_generation: 'Generated application code',
  code_generation_openhands: 'Generated application code',
  integration_wiring: 'Connected components & APIs',
  code_review: 'Reviewed code quality',
  security: 'Scanned for vulnerabilities',
  seo: 'Optimized SEO & performance',
  accessibility: 'Checked WCAG compliance',
  qa: 'Ran QA tests & bug fixes',
  deploy: 'Deployed to hosting',
  analytics: 'Set up monitoring',
  coding_standards: 'Enforced coding standards',
  post_deploy_verification: 'Verified live deployment',
  delivery: 'Packaged final deliverables',
}

interface ChatEntry {
  role: 'user' | 'assistant' | 'system'
  message: string
  timestamp: string
  agentName?: string
  agentStatus?: 'running' | 'completed' | 'failed'
  // Agent source citations shown as pills under AI messages
  agentSources?: { name: string; description: string }[]
}

// Animation variants matching sleek-chat-soul's Framer Motion style
const messageVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.06, duration: 0.3, ease: 'easeOut' },
  }),
}

const suggestionVariants = {
  hidden: { opacity: 0, y: 8 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: 0.15 + i * 0.08, duration: 0.3, ease: 'easeOut' },
  }),
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
  // Collect completed agent names for source citations on build-complete message
  const completedAgentsRef = useRef<string[]>([])

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

  // Track agent progress as chat messages with source citations
  useEffect(() => {
    if (!outputs?.agent_outputs || !buildStarted) return

    const agentNames = Object.keys(outputs.agent_outputs).filter(k => !k.startsWith('_'))
    const existingAgentMessages = messages.filter(m => m.role === 'system' && m.agentName)

    for (const agentName of agentNames) {
      const existing = existingAgentMessages.find(m => m.agentName === agentName)
      if (!existing) {
        const label = agentName.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
        completedAgentsRef.current = [...new Set([...completedAgentsRef.current, agentName])]
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

  // Show build complete message with agent source citations
  useEffect(() => {
    if (project?.status === 'completed' && buildStarted) {
      const alreadyHasComplete = messages.some(m => m.message.includes('build is complete'))
      if (!alreadyHasComplete) {
        // Build source citations from completed agents
        const sources = completedAgentsRef.current.map(name => ({
          name: name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
          description: AGENT_DESCRIPTIONS[name] || 'Completed',
        }))
        setMessages(prev => [...prev, {
          role: 'assistant',
          message: 'Your build is complete! Check the preview panel to see the results.',
          timestamp: new Date().toISOString(),
          agentSources: sources,
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
      {/* Background image layer for glassmorphism depth */}
      <div className="chat-bg-image" />

      {/* Chat Panel */}
      <div className="chat-panel">
        {/* Chat Messages */}
        <div className="chat-messages">
          {messages.length === 0 ? (
            <div className="chat-empty">
              <motion.div
                className="chat-empty-icon"
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ duration: 0.4, ease: 'easeOut' }}
              >
                <Sparkles className="w-8 h-8" />
              </motion.div>
              <motion.h2
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1, duration: 0.3 }}
              >
                What do you want to build?
              </motion.h2>
              <motion.p
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2, duration: 0.3 }}
              >
                Describe your project and I'll build it for you with AI agents.
              </motion.p>
              <div className="chat-suggestions">
                {SUGGESTIONS.map((s, i) => (
                  <motion.button
                    key={i}
                    custom={i}
                    variants={suggestionVariants}
                    initial="hidden"
                    animate="visible"
                    className="chat-suggestion"
                    onClick={() => sendMessage(s.text)}
                    whileHover={{ y: -2 }}
                    whileTap={{ scale: 0.97 }}
                  >
                    <div className="chat-suggestion-icon">
                      <s.icon className="w-4 h-4" />
                    </div>
                    <span>{s.text}</span>
                  </motion.button>
                ))}
              </div>
            </div>
          ) : (
            <div className="chat-message-list">
              <AnimatePresence initial={false}>
                {messages.map((msg, i) => (
                  <motion.div
                    key={`${msg.timestamp}-${i}`}
                    custom={i}
                    variants={messageVariants}
                    initial="hidden"
                    animate="visible"
                    className={`chat-message chat-message-${msg.role}`}
                  >
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
                        <div className="chat-message-content-wrapper">
                          <div className="chat-message-content">
                            <p>{msg.message}</p>
                          </div>
                          {/* Agent source citation pills */}
                          {msg.agentSources && msg.agentSources.length > 0 && (
                            <div className="chat-sources">
                              {msg.agentSources.map((source, si) => (
                                <div key={si} className="chat-source-pill">
                                  <span className="chat-source-num">{si + 1}</span>
                                  <span className="chat-source-name">{source.name}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </>
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>

              {sending && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="chat-message chat-message-assistant"
                >
                  <div className="chat-avatar chat-avatar-ai">
                    <Bot className="w-4 h-4" />
                  </div>
                  <div className="chat-typing">
                    <span /><span /><span />
                  </div>
                </motion.div>
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
                <Send className="w-4 h-4" />
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
