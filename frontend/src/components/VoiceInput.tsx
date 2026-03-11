/**
 * Phase 11A: Voice Input Component
 * Uses Web Speech API (SpeechRecognition) for voice-to-text input
 */
import { useState, useEffect, useCallback } from 'react'
import { Mic, MicOff } from 'lucide-react'
import { clsx } from 'clsx'

interface VoiceInputProps {
  onTranscript: (text: string) => void
  onListeningChange?: (isListening: boolean) => void
  className?: string
  disabled?: boolean
}

// Type declarations for Web Speech API
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList
  resultIndex: number
}

interface SpeechRecognitionResultList {
  length: number
  item(index: number): SpeechRecognitionResult
  [index: number]: SpeechRecognitionResult
}

interface SpeechRecognitionResult {
  isFinal: boolean
  length: number
  item(index: number): SpeechRecognitionAlternative
  [index: number]: SpeechRecognitionAlternative
}

interface SpeechRecognitionAlternative {
  transcript: string
  confidence: number
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean
  interimResults: boolean
  lang: string
  start(): void
  stop(): void
  abort(): void
  onresult: ((event: SpeechRecognitionEvent) => void) | null
  onerror: ((event: Event) => void) | null
  onend: (() => void) | null
  onstart: (() => void) | null
}

declare global {
  interface Window {
    SpeechRecognition: new () => SpeechRecognition
    webkitSpeechRecognition: new () => SpeechRecognition
  }
}

export default function VoiceInput({ 
  onTranscript, 
  onListeningChange,
  className,
  disabled = false 
}: VoiceInputProps) {
  const [isListening, setIsListening] = useState(false)
  const [isSupported, setIsSupported] = useState(false)
  const [recognition, setRecognition] = useState<SpeechRecognition | null>(null)

  // Check for browser support
  useEffect(() => {
    const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition
    if (SpeechRecognitionAPI) {
      setIsSupported(true)
      const recognitionInstance = new SpeechRecognitionAPI()
      recognitionInstance.continuous = true
      recognitionInstance.interimResults = true
      recognitionInstance.lang = 'en-US'
      setRecognition(recognitionInstance)
    }
  }, [])

  // Set up recognition event handlers
  useEffect(() => {
    if (!recognition) return

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let finalTranscript = ''
      
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        if (result.isFinal) {
          finalTranscript += result[0].transcript
        }
      }

      if (finalTranscript) {
        onTranscript(finalTranscript)
      }
    }

    recognition.onerror = (event: Event) => {
      console.error('Speech recognition error:', event)
      setIsListening(false)
      onListeningChange?.(false)
    }

    recognition.onend = () => {
      setIsListening(false)
      onListeningChange?.(false)
    }

    recognition.onstart = () => {
      setIsListening(true)
      onListeningChange?.(true)
    }

    return () => {
      recognition.onresult = null
      recognition.onerror = null
      recognition.onend = null
      recognition.onstart = null
    }
  }, [recognition, onTranscript, onListeningChange])

  const toggleListening = useCallback(() => {
    if (!recognition || disabled) return

    if (isListening) {
      recognition.stop()
    } else {
      try {
        recognition.start()
      } catch (error) {
        // Recognition may already be running
        console.warn('Speech recognition start error:', error)
      }
    }
  }, [recognition, isListening, disabled])

  // Don't render if not supported
  if (!isSupported) {
    return null
  }

  return (
    <button
      type="button"
      onClick={toggleListening}
      disabled={disabled}
      className={clsx(
        'relative transition-all duration-200',
        isListening && 'voice-input-active',
        className
      )}
      style={{
        padding: 'var(--space-2)',
        borderRadius: '50%',
        background: isListening ? 'var(--accent-error-bg, rgba(239,68,68,0.1))' : 'transparent',
        border: isListening ? '2px solid var(--accent-error-border, rgba(239,68,68,0.5))' : '2px solid transparent',
      }}
      title={isListening ? 'Stop listening' : 'Start voice input'}
      aria-label={isListening ? 'Stop voice input' : 'Start voice input'}
    >
      {/* Pulsing ring animation when listening */}
      {isListening && (
        <>
          <span
            className="absolute inset-0 rounded-full animate-ping"
            style={{
              background: 'var(--accent-error-bg, rgba(239,68,68,0.3))',
              animationDuration: '1.5s',
            }}
          />
          <span
            className="absolute inset-0 rounded-full animate-pulse"
            style={{
              background: 'var(--accent-error-bg, rgba(239,68,68,0.2))',
            }}
          />
        </>
      )}
      
      {isListening ? (
        <MicOff 
          className="w-5 h-5 relative z-10" 
          style={{ color: 'var(--accent-error)' }}
        />
      ) : (
        <Mic 
          className="w-5 h-5" 
          style={{ color: disabled ? 'var(--text-tertiary)' : 'var(--text-secondary)' }} 
        />
      )}
    </button>
  )
}
