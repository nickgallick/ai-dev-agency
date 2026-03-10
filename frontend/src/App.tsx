import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import NewProject from './pages/NewProject'
import ProjectView from './pages/ProjectView'
import ProjectHistory from './pages/ProjectHistory'
import Settings from './pages/Settings'
import AgentLogs from './pages/AgentLogs'
import CostDashboard from './pages/CostDashboard'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="new" element={<NewProject />} />
          <Route path="project/:id" element={<ProjectView />} />
          <Route path="projects" element={<ProjectHistory />} />
          <Route path="settings" element={<Settings />} />
          <Route path="logs" element={<AgentLogs />} />
          <Route path="costs" element={<CostDashboard />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
