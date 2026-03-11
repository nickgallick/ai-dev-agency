import { useState, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { Loader2, Lock, Mail, User, AlertCircle, Sparkles, ArrowRight } from 'lucide-react'

export default function Login() {
  const { login, setup, setupRequired, isLoading: authLoading } = useAuth()
  const navigate = useNavigate()
  
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [name, setName] = useState('')
  const [rememberMe, setRememberMe] = useState(false)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)
    
    try {
      if (setupRequired) {
        if (password !== confirmPassword) {
          setError('Passwords do not match')
          setIsLoading(false)
          return
        }
        if (password.length < 8) {
          setError('Password must be at least 8 characters')
          setIsLoading(false)
          return
        }
        await setup(email, password, name || undefined)
      } else {
        await login(email, password, rememberMe)
      }
      navigate('/')
    } catch (err: any) {
      setError(err.message || 'Authentication failed')
    } finally {
      setIsLoading(false)
    }
  }

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--bg-base)' }}>
        <Loader2 className="w-8 h-8 animate-spin" style={{ color: 'var(--accent-primary)' }} />
      </div>
    )
  }

  return (
    <div 
      className="min-h-screen flex items-center justify-center p-4" 
      style={{ 
        background: 'var(--bg-base)',
        backgroundImage: 'linear-gradient(var(--grid-line, rgba(255,255,255,0.015)) 1px, transparent 1px), linear-gradient(90deg, var(--grid-line, rgba(255,255,255,0.015)) 1px, transparent 1px)',
        backgroundSize: '40px 40px'
      }}
    >
      <div className="w-full max-w-md">
        {/* Logo/Header */}
        <div className="text-center mb-8">
          <div 
            className="inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-4"
            style={{ background: 'var(--gradient-accent)', boxShadow: 'var(--shadow-glow)' }}
          >
            <Sparkles className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
            AI Dev Agency
          </h1>
          <p className="mt-1" style={{ color: 'var(--text-secondary)' }}>
            {setupRequired ? 'Create your admin account' : 'Sign in to continue'}
          </p>
        </div>
        
        {/* Form Card - Glassmorphic */}
        <div className="glass-card-elevated" style={{ padding: 'var(--space-6)' }}>
          <div className="bloom-content">
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Error Message */}
              {error && (
                <div className="glass-card flex items-center gap-2 bg-accent-error/10 border-accent-error/30"
                     style={{ padding: 'var(--space-3)' }}
                >
                  <AlertCircle className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--accent-error)' }} />
                  <span style={{ color: 'var(--accent-error)', fontSize: 'var(--text-sm)' }}>{error}</span>
                </div>
              )}
              
              {/* Name field (setup only) */}
              {setupRequired && (
                <div>
                  <label 
                    htmlFor="name" 
                    className="block mb-2 font-medium"
                    style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}
                  >
                    Name (optional)
                  </label>
                  <div className="relative">
                    <User 
                      className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" 
                      style={{ color: 'var(--text-tertiary)' }}
                    />
                    <input
                      id="name"
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Admin"
                      className="glass-input w-full"
                      style={{ paddingLeft: 'var(--space-10)' }}
                    />
                  </div>
                </div>
              )}
              
              {/* Email */}
              <div>
                <label 
                  htmlFor="email" 
                  className="block mb-2 font-medium"
                  style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}
                >
                  Email
                </label>
                <div className="relative">
                  <Mail 
                    className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" 
                    style={{ color: 'var(--text-tertiary)' }}
                  />
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="admin@example.com"
                    required
                    autoFocus
                    className="glass-input w-full"
                    style={{ paddingLeft: 'var(--space-10)' }}
                  />
                </div>
              </div>
              
              {/* Password */}
              <div>
                <label 
                  htmlFor="password" 
                  className="block mb-2 font-medium"
                  style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}
                >
                  Password
                </label>
                <div className="relative">
                  <Lock 
                    className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" 
                    style={{ color: 'var(--text-tertiary)' }}
                  />
                  <input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    minLength={8}
                    className="glass-input w-full"
                    style={{ paddingLeft: 'var(--space-10)' }}
                  />
                </div>
                {setupRequired && (
                  <p className="mt-1" style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-xs)' }}>
                    Minimum 8 characters
                  </p>
                )}
              </div>
              
              {/* Confirm Password (setup only) */}
              {setupRequired && (
                <div>
                  <label 
                    htmlFor="confirmPassword" 
                    className="block mb-2 font-medium"
                    style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}
                  >
                    Confirm Password
                  </label>
                  <div className="relative">
                    <Lock 
                      className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" 
                      style={{ color: 'var(--text-tertiary)' }}
                    />
                    <input
                      id="confirmPassword"
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="••••••••"
                      required
                      minLength={8}
                      className="glass-input w-full"
                      style={{ paddingLeft: 'var(--space-10)' }}
                    />
                  </div>
                </div>
              )}
              
              {/* Remember Me (login only) */}
              {!setupRequired && (
                <div className="flex items-center">
                  <input
                    id="rememberMe"
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-4 h-4 rounded"
                    style={{ 
                      accentColor: 'var(--accent-primary)',
                      background: 'var(--glass-bg)',
                      borderColor: 'var(--glass-border)'
                    }}
                  />
                  <label 
                    htmlFor="rememberMe" 
                    className="ml-2"
                    style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}
                  >
                    Remember me
                  </label>
                </div>
              )}
              
              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="btn-iridescent w-full flex items-center justify-center gap-2"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    {setupRequired ? 'Creating Account...' : 'Signing in...'}
                  </>
                ) : (
                  <>
                    {setupRequired ? 'Create Admin Account' : 'Sign In'}
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          </div>
        </div>
        
        {/* Footer */}
        <p className="text-center mt-6" style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-xs)' }}>
          {setupRequired 
            ? 'This is a single-user system. Create one admin account.'
            : 'Session expires after 30 minutes of inactivity.'
          }
        </p>
      </div>
    </div>
  )
}
