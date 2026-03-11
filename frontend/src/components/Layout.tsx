import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { Home, PlusCircle, FolderOpen, Settings, Activity, DollarSign, Menu, X, LogOut, User, Sparkles, Brain, Layers, HardDrive } from 'lucide-react'
import { useState } from 'react'
import { clsx } from 'clsx'
import { useAuth } from '@/contexts/AuthContext'

const navItems = [
  { path: '/', icon: Home, label: 'Home' },
  { path: '/new', icon: PlusCircle, label: 'New Project' },
  { path: '/projects', icon: FolderOpen, label: 'Projects' },
  { path: '/settings', icon: Settings, label: 'Settings' },
]

const secondaryNav = [
  { path: '/logs', icon: Activity, label: 'Agent Logs' },
  { path: '/costs', icon: DollarSign, label: 'Cost Dashboard' },
  { path: '/knowledge', icon: Brain, label: 'Knowledge Base' },  // Phase 11B
  { path: '/queue', icon: Layers, label: 'Queue' },  // Phase 11C
  { path: '/backup', icon: HardDrive, label: 'Backup' },  // Phase 11C
]

export default function Layout() {
  const location = useLocation()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const { user, logout } = useAuth()

  const handleLogout = async () => {
    await logout()
  }

  return (
    <div className="min-h-screen flex flex-col lg:flex-row">
      {/* Desktop Sidebar - Glassmorphic */}
      <aside className="glass-sidebar hidden lg:flex">
        {/* Logo */}
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">
            <Sparkles className="w-5 h-5" />
          </div>
          <span className="sidebar-logo-text">AI Dev Agency</span>
        </div>

        {/* Main Navigation */}
        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                clsx('sidebar-nav-item', isActive && 'active')
              }
            >
              <item.icon />
              {item.label}
            </NavLink>
          ))}
          
          {/* Divider */}
          <div className="my-4 border-t border-glass-border" style={{ borderColor: 'var(--glass-border)' }} />
          
          {/* Secondary Navigation */}
          {secondaryNav.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                clsx('sidebar-nav-item', isActive && 'active')
              }
            >
              <item.icon />
              {item.label}
            </NavLink>
          ))}
        </nav>
        
        {/* User Info & Logout */}
        <div className="mt-auto pt-4 border-t" style={{ borderColor: 'var(--glass-border)' }}>
          <div className="glass-card" style={{ padding: 'var(--space-3)' }}>
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full flex items-center justify-center" 
                   style={{ background: 'rgba(32, 184, 205, 0.15)' }}>
                <User className="w-4 h-4" style={{ color: 'var(--accent-primary)' }} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                  {user?.name || 'Admin'}
                </p>
                <p className="text-xs truncate" style={{ color: 'var(--text-tertiary)' }}>
                  {user?.email}
                </p>
              </div>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="sidebar-nav-item w-full mt-2 hover:text-red-400"
            style={{ color: 'var(--text-secondary)' }}
          >
            <LogOut />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Mobile Header */}
      <header className="lg:hidden flex items-center justify-between p-4"
              style={{
                background: 'var(--mobile-header-bg)',
                backdropFilter: 'blur(20px)',
                WebkitBackdropFilter: 'blur(20px)',
                borderBottom: '1px solid var(--glass-border)'
              }}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center"
               style={{ background: 'var(--gradient-accent)' }}>
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <span className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
            AI Dev Agency
          </span>
        </div>
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="btn-ghost"
          style={{ padding: 'var(--space-2)' }}
        >
          {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </header>

      {/* Mobile Dropdown Menu */}
      {mobileMenuOpen && (
        <div className="lg:hidden absolute inset-x-0 top-16 z-50"
             style={{
               background: 'var(--mobile-header-bg)',
               backdropFilter: 'blur(40px)',
               WebkitBackdropFilter: 'blur(40px)',
               borderBottom: '1px solid var(--glass-border)'
             }}>
          <nav style={{ padding: 'var(--space-4)' }}>
            {[...navItems, ...secondaryNav].map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={() => setMobileMenuOpen(false)}
                className={({ isActive }) =>
                  clsx('sidebar-nav-item', isActive && 'active')
                }
                style={{ marginBottom: 'var(--space-1)' }}
              >
                <item.icon />
                {item.label}
              </NavLink>
            ))}
            
            {/* Mobile User Info & Logout */}
            <div className="pt-4 mt-4" style={{ borderTop: '1px solid var(--glass-border)' }}>
              <div className="flex items-center gap-3 p-3">
                <div className="w-9 h-9 rounded-full flex items-center justify-center"
                     style={{ background: 'rgba(32, 184, 205, 0.15)' }}>
                  <User className="w-4 h-4" style={{ color: 'var(--accent-primary)' }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                    {user?.name || 'Admin'}
                  </p>
                  <p className="text-xs truncate" style={{ color: 'var(--text-tertiary)' }}>
                    {user?.email}
                  </p>
                </div>
              </div>
              <button
                onClick={() => { handleLogout(); setMobileMenuOpen(false); }}
                className="sidebar-nav-item w-full hover:text-red-400"
              >
                <LogOut />
                Sign Out
              </button>
            </div>
          </nav>
        </div>
      )}

      {/* Main Content */}
      <main className="flex-1 overflow-auto lg:ml-[260px]" style={{ background: 'var(--bg-base)' }}>
        <div className="p-4 lg:p-8 max-w-6xl mx-auto pb-24 lg:pb-8">
          <Outlet />
        </div>
      </main>

      {/* Mobile Bottom Tab Bar */}
      <nav className="mobile-tab-bar lg:hidden">
        {navItems.slice(0, 4).map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              clsx('mobile-tab-item', isActive && 'active')
            }
          >
            <item.icon />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
