import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { ThemeProvider } from './contexts/ThemeContext'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'
import Login from './pages/Login'
import Home from './pages/Home'
import ChatBuilder from './pages/ChatBuilder'
import ProjectView from './pages/ProjectView'
import ProjectHistory from './pages/ProjectHistory'
import Settings from './pages/Settings'
import AgentLogs from './pages/AgentLogs'
import CostDashboard from './pages/CostDashboard'
import KnowledgeBase from './pages/KnowledgeBase'
import Queue from './pages/Queue'
import SystemBackup from './pages/SystemBackup'

function AppRoutes() {
  const { isAuthenticated, setupRequired, isLoading } = useAuth()

  // Show login for unauthenticated users or setup screen
  if (!isLoading && (!isAuthenticated || setupRequired)) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  return (
    <Routes>
      <Route path="/login" element={<Navigate to="/" replace />} />

      {/* Chat builder — full-width, no sidebar wrapper */}
      <Route
        path="/chat"
        element={
          <ProtectedRoute>
            <ChatBuilder />
          </ProtectedRoute>
        }
      />
      <Route
        path="/chat/:projectId"
        element={
          <ProtectedRoute>
            <ChatBuilder />
          </ProtectedRoute>
        }
      />

      {/* Standard layout with sidebar */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Home />} />
        <Route path="new" element={<Navigate to="/chat" replace />} />
        <Route path="project/:id" element={<ProjectView />} />
        <Route path="projects" element={<ProjectHistory />} />
        <Route path="settings" element={<Settings />} />
        <Route path="logs" element={<AgentLogs />} />
        <Route path="costs" element={<CostDashboard />} />
        <Route path="knowledge" element={<KnowledgeBase />} />
        <Route path="queue" element={<Queue />} />
        <Route path="backup" element={<SystemBackup />} />
      </Route>
    </Routes>
  )
}

function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  )
}

export default App
