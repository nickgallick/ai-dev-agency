import { useEffect, useState, useRef } from 'react'
import { Loader2, CheckCircle, AlertCircle, AlertTriangle, Zap, Bot, RefreshCw, ShieldAlert, KeyRound } from 'lucide-react'
import './ActivityFeed.css'

interface ActivityEvent {
  id: string
  project_id: string
  timestamp: string
  event_type: string
  agent_name?: string
  agent_display_name?: string
  message: string
  details?: Record<string, any>
  progress?: number
}

interface ActivityFeedProps {
  projectId: string
  isActive: boolean
}

export function ActivityFeed({ projectId, isActive }: ActivityFeedProps) {
  const [events, setEvents] = useState<ActivityEvent[]>([])
  const [connected, setConnected] = useState(false)
  const [currentProgress, setCurrentProgress] = useState(0)
  const feedRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  const [reconnectKey, setReconnectKey] = useState(0)

  useEffect(() => {
    if (!isActive || !projectId) return

    let retryTimer: ReturnType<typeof setTimeout> | null = null
    let cancelled = false

    // Connect to SSE endpoint
    const apiUrl = import.meta.env.VITE_API_URL || ''
    const eventSource = new EventSource(`${apiUrl}/api/activity/${projectId}/stream`)
    eventSourceRef.current = eventSource

    eventSource.onopen = () => {
      setConnected(true)
    }

    eventSource.onmessage = (event) => {
      try {
        const data: ActivityEvent = JSON.parse(event.data)
        setEvents(prev => {
          // Avoid duplicates
          if (prev.some(e => e.id === data.id)) return prev
          // Keep last 50 events
          const newEvents = [...prev, data].slice(-50)
          return newEvents
        })

        // Update progress
        if (data.progress !== undefined && data.progress !== null) {
          setCurrentProgress(data.progress)
        }
      } catch (e) {
        console.error('Failed to parse activity event:', e)
      }
    }

    eventSource.onerror = () => {
      setConnected(false)
      eventSource.close()
      eventSourceRef.current = null
      // Schedule reconnect — the effect cleanup will cancel this if component unmounts
      retryTimer = setTimeout(() => {
        if (!cancelled) {
          setReconnectKey(k => k + 1)
        }
      }, 3000)
    }

    return () => {
      cancelled = true
      if (retryTimer) clearTimeout(retryTimer)
      eventSource.close()
      eventSourceRef.current = null
    }
  }, [projectId, isActive, reconnectKey])

  // Auto-scroll to bottom
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight
    }
  }, [events])

  const getErrorIcon = (details?: Record<string, any>) => {
    const category = details?._error_category || details?.error_category
    switch (category) {
      case 'auth':
        return <KeyRound className="w-4 h-4 text-accent-error" />
      case 'rate_limit':
        return <RefreshCw className="w-4 h-4 text-yellow-400" />
      case 'quota':
        return <ShieldAlert className="w-4 h-4 text-accent-error" />
      case 'transient':
      case 'upstream':
        return <AlertTriangle className="w-4 h-4 text-yellow-400" />
      default:
        return <AlertCircle className="w-4 h-4 text-accent-error" />
    }
  }

  const getEventIcon = (event: ActivityEvent) => {
    switch (event.event_type) {
      case 'agent_start':
      case 'agent_thinking':
        return <Loader2 className="w-4 h-4 animate-spin text-accent-primary" />
      case 'agent_complete':
        return <CheckCircle className="w-4 h-4 text-accent-success" />
      case 'agent_error':
      case 'pipeline_error':
        return getErrorIcon(event.details)
      case 'pipeline_start':
        return <Zap className="w-4 h-4 text-accent-primary" />
      case 'pipeline_complete':
        return <CheckCircle className="w-4 h-4 text-accent-success" />
      default:
        return <Bot className="w-4 h-4 text-text-tertiary" />
    }
  }

  const getErrorDetail = (event: ActivityEvent): string | null => {
    const userMsg = event.details?._error_user_message || event.details?.error_user_message
    if (userMsg) return userMsg
    return null
  }

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      second: '2-digit'
    })
  }

  return (
    <div className="activity-feed">
      {/* Progress Bar */}
      <div className="activity-progress">
        <div className="activity-progress-bar">
          <div 
            className="activity-progress-fill"
            style={{ width: `${currentProgress}%` }}
          />
        </div>
        <span className="activity-progress-text">{Math.round(currentProgress)}%</span>
      </div>

      {/* Connection Status */}
      <div className="activity-header">
        <div className="activity-status">
          <span className={`status-dot ${connected ? 'connected' : 'disconnected'}`} />
          <span className="status-text">
            {connected ? 'Live' : 'Connecting...'}
          </span>
        </div>
        <span className="event-count">{events.length} events</span>
      </div>

      {/* Activity Stream */}
      <div className="activity-stream" ref={feedRef}>
        {events.length === 0 ? (
          <div className="activity-empty">
            <Bot className="w-8 h-8 text-text-tertiary" />
            <p>Waiting for activity...</p>
          </div>
        ) : (
          events.map((event) => {
            const errorDetail = getErrorDetail(event)
            return (
              <div
                key={event.id}
                className={`activity-event ${event.event_type}`}
              >
                <div className="event-icon">
                  {getEventIcon(event)}
                </div>
                <div className="event-content">
                  {event.agent_display_name && (
                    <span className="event-agent">{event.agent_display_name}</span>
                  )}
                  <span className="event-message">{event.message}</span>
                  {errorDetail && (
                    <span className="event-error-detail" style={{
                      display: 'block',
                      fontSize: '0.75rem',
                      opacity: 0.7,
                      marginTop: '2px',
                    }}>{errorDetail}</span>
                  )}
                </div>
                <span className="event-time">{formatTime(event.timestamp)}</span>
              </div>
            )
          })
        )}
        
        {/* Current thinking indicator */}
        {events.length > 0 && events[events.length - 1]?.event_type === 'agent_thinking' && (
          <div className="thinking-indicator">
            <div className="thinking-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
