import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { LandingPage } from './pages/LandingPage'
import { ResponderDashboard } from './pages/ResponderDashboard'
import { CitizenMode } from './pages/CitizenMode'

export function App() {
  return (
    <Router>
      <Routes>
        {/* Landing Page (Overview & Portals) */}
        <Route path="/" element={<LandingPage />} />

        {/* Responder Dashboard (Desktop Tactical GIS Console) */}
        <Route path="/dashboard" element={<ResponderDashboard />} />
        <Route path="/responder" element={<ResponderDashboard />} />

        {/* Citizen Mode (Mobile-First Offline Survival & Triage) */}
        <Route path="/citizen" element={<CitizenMode />} />

        {/* Fallback to Landing Page */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  )
}

export default App
