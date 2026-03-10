import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { Home, PlusCircle, FolderOpen, Settings, Activity, DollarSign, Menu, X, LogOut, User } from 'lucide-react'
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
  { path: '/costs', icon: DollarSign, label: 'Costs' },
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
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex lg:flex-col lg:w-60 bg-background-primary border-r border-border-subtle">
        <div className="p-4 border-b border-border-subtle">
          <h1 className="text-xl font-semibold bg-gradient-to-r from-accent-primary to-accent-secondary bg-clip-text text-transparent">
            AI Dev Agency
          </h1>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-background-tertiary text-text-primary'
                    : 'text-text-secondary hover:bg-background-tertiary hover:text-text-primary'
                )
              }
            >
              <item.icon className="w-5 h-5" />
              {item.label}
            </NavLink>
          ))}
          
          <div className="pt-4 mt-4 border-t border-border-subtle">
            {secondaryNav.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-background-tertiary text-text-primary'
                      : 'text-text-secondary hover:bg-background-tertiary hover:text-text-primary'
                  )
                }
              >
                <item.icon className="w-5 h-5" />
                {item.label}
              </NavLink>
            ))}
          </div>
        </nav>
        
        {/* User Info & Logout */}
        <div className="p-3 border-t border-border-subtle">
          <div className="flex items-center gap-3 px-3 py-2">
            <div className="w-8 h-8 rounded-full bg-accent-primary/20 flex items-center justify-center">
              <User className="w-4 h-4 text-accent-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-text-primary truncate">
                {user?.name || 'Admin'}
              </p>
              <p className="text-xs text-text-tertiary truncate">
                {user?.email}
              </p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2.5 mt-1 rounded-lg text-sm font-medium text-text-secondary hover:bg-background-tertiary hover:text-accent-error transition-colors"
          >
            <LogOut className="w-5 h-5" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Mobile Header */}
      <header className="lg:hidden flex items-center justify-between p-4 bg-background-primary border-b border-border-subtle">
        <h1 className="text-lg font-semibold bg-gradient-to-r from-accent-primary to-accent-secondary bg-clip-text text-transparent">
          AI Dev Agency
        </h1>
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-2 rounded-lg hover:bg-background-tertiary"
        >
          {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </header>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="lg:hidden absolute inset-x-0 top-16 bg-background-secondary border-b border-border-subtle z-50">
          <nav className="p-3 space-y-1">
            {[...navItems, ...secondaryNav].map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={() => setMobileMenuOpen(false)}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center gap-3 px-3 py-3 rounded-lg text-base font-medium',
                    isActive
                      ? 'bg-background-tertiary text-text-primary'
                      : 'text-text-secondary'
                  )
                }
              >
                <item.icon className="w-5 h-5" />
                {item.label}
              </NavLink>
            ))}
            
            {/* Mobile User Info & Logout */}
            <div className="pt-3 mt-3 border-t border-border-subtle">
              <div className="flex items-center gap-3 px-3 py-2">
                <div className="w-8 h-8 rounded-full bg-accent-primary/20 flex items-center justify-center">
                  <User className="w-4 h-4 text-accent-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-text-primary truncate">
                    {user?.name || 'Admin'}
                  </p>
                  <p className="text-xs text-text-tertiary truncate">
                    {user?.email}
                  </p>
                </div>
              </div>
              <button
                onClick={() => { handleLogout(); setMobileMenuOpen(false); }}
                className="w-full flex items-center gap-3 px-3 py-3 rounded-lg text-base font-medium text-text-secondary hover:text-accent-error"
              >
                <LogOut className="w-5 h-5" />
                Sign Out
              </button>
            </div>
          </nav>
        </div>
      )}

      {/* Main Content */}
      <main className="flex-1 bg-background-secondary overflow-auto">
        <div className="p-4 lg:p-8 max-w-6xl mx-auto">
          <Outlet />
        </div>
      </main>

      {/* Mobile Bottom Tab Bar */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 bg-background-primary border-t border-border-subtle">
        <div className="flex justify-around py-2">
          {navItems.slice(0, 4).map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                clsx(
                  'flex flex-col items-center gap-1 px-4 py-2 text-xs',
                  isActive ? 'text-accent-primary' : 'text-text-secondary'
                )
              }
            >
              <item.icon className="w-5 h-5" />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  )
}
