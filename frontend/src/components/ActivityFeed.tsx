import { useEffect, useState, useRef } from 'react'
import { Loader2, CheckCircle, AlertCircle, Zap, Bot } from 'lucide-react'
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

  useEffect(() => {
    if (!isActive || !projectId) return

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
    }

    return () => {
      eventSource.close()
      eventSourceRef.current = null
    }
  }, [projectId, isActive])

  // Auto-scroll to bottom
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight
    }
  }, [events])

  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case 'agent_start':
      case 'agent_thinking':
        return <Loader2 className="w-4 h-4 animate-spin text-accent-primary" />
      case 'agent_complete':
        return <CheckCircle className="w-4 h-4 text-accent-success" />
      case 'agent_error':
      case 'pipeline_error':
        return <AlertCircle className="w-4 h-4 text-accent-error" />
      case 'pipeline_start':
        return <Zap className="w-4 h-4 text-accent-primary" />
      case 'pipeline_complete':
        return <CheckCircle className="w-4 h-4 text-accent-success" />
      default:
        return <Bot className="w-4 h-4 text-text-tertiary" />
    }
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
          events.map((event) => (
            <div 
              key={event.id} 
              className={`activity-event ${event.event_type}`}
            >
              <div className="event-icon">
                {getEventIcon(event.event_type)}
              </div>
              <div className="event-content">
                {event.agent_display_name && (
                  <span className="event-agent">{event.agent_display_name}</span>
                )}
                <span className="event-message">{event.message}</span>
              </div>
              <span className="event-time">{formatTime(event.timestamp)}</span>
            </div>
          ))
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
