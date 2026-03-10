import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'

interface User {
  id: string
  email: string
  name: string | null
  last_login: string | null
  created_at: string
}

interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  setupRequired: boolean
  login: (email: string, password: string, rememberMe?: boolean) => Promise<void>
  logout: () => Promise<void>
  setup: (email: string, password: string, name?: string) => Promise<void>
  refreshToken: () => Promise<void>
  checkAuth: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

const API_BASE = '/api/auth'
const IDLE_TIMEOUT_MS = 30 * 60 * 1000 // 30 minutes
const TOKEN_REFRESH_INTERVAL_MS = 13 * 60 * 1000 // 13 minutes (refresh before 15 min expiry)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [setupRequired, setSetupRequired] = useState(false)
  const [lastActivity, setLastActivity] = useState(Date.now())

  // Check auth status on mount
  const checkAuth = useCallback(async () => {
    try {
      // First check if setup is needed
      const statusRes = await fetch(`${API_BASE}/status`, {
        credentials: 'include',
      })
      const status = await statusRes.json()
      
      if (!status.setup_complete) {
        setSetupRequired(true)
        setIsLoading(false)
        return
      }
      
      setSetupRequired(false)
      
      // Try to get current user
      const meRes = await fetch(`${API_BASE}/me`, {
        credentials: 'include',
      })
      
      if (meRes.ok) {
        const userData = await meRes.json()
        setUser(userData)
      } else if (meRes.status === 401) {
        // Try to refresh token
        try {
          await refreshToken()
        } catch {
          setUser(null)
        }
      } else {
        setUser(null)
      }
    } catch (error) {
      console.error('Auth check failed:', error)
      setUser(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  // Token refresh interval
  useEffect(() => {
    if (!user) return
    
    const interval = setInterval(() => {
      refreshToken().catch(console.error)
    }, TOKEN_REFRESH_INTERVAL_MS)
    
    return () => clearInterval(interval)
  }, [user])

  // Idle timeout tracking
  useEffect(() => {
    if (!user) return

    const updateActivity = () => setLastActivity(Date.now())
    
    window.addEventListener('mousemove', updateActivity)
    window.addEventListener('keypress', updateActivity)
    window.addEventListener('click', updateActivity)
    window.addEventListener('scroll', updateActivity)
    
    const idleCheck = setInterval(() => {
      if (Date.now() - lastActivity > IDLE_TIMEOUT_MS) {
        // Session timed out due to inactivity
        logout()
      }
    }, 60000) // Check every minute
    
    return () => {
      window.removeEventListener('mousemove', updateActivity)
      window.removeEventListener('keypress', updateActivity)
      window.removeEventListener('click', updateActivity)
      window.removeEventListener('scroll', updateActivity)
      clearInterval(idleCheck)
    }
  }, [user, lastActivity])

  const login = async (email: string, password: string, rememberMe = false) => {
    const res = await fetch(`${API_BASE}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email, password, remember_me: rememberMe }),
    })
    
    if (!res.ok) {
      const error = await res.json()
      throw new Error(error.detail || 'Login failed')
    }
    
    const data = await res.json()
    setUser(data.user)
    setLastActivity(Date.now())
  }

  const logout = async () => {
    try {
      await fetch(`${API_BASE}/logout`, {
        method: 'POST',
        credentials: 'include',
      })
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      setUser(null)
    }
  }

  const setup = async (email: string, password: string, name?: string) => {
    const res = await fetch(`${API_BASE}/setup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email, password, name }),
    })
    
    if (!res.ok) {
      const error = await res.json()
      throw new Error(error.detail || 'Setup failed')
    }
    
    const data = await res.json()
    setUser(data.user)
    setSetupRequired(false)
    setLastActivity(Date.now())
  }

  const refreshToken = async () => {
    const res = await fetch(`${API_BASE}/refresh`, {
      method: 'POST',
      credentials: 'include',
    })
    
    if (!res.ok) {
      setUser(null)
      throw new Error('Token refresh failed')
    }
    
    const data = await res.json()
    setUser(data.user)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        setupRequired,
        login,
        logout,
        setup,
        refreshToken,
        checkAuth,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
