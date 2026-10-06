import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { ResponderDashboard } from './pages/ResponderDashboard'
import { CitizenMode } from './pages/CitizenMode'

export function App() {
  return (
    <Router>
      <Routes>
        {/* Responder Dashboard (Desktop) */}
        <Route path="/" element={<ResponderDashboard />} />

        {/* Citizen Mode (Mobile-First) */}
        <Route path="/citizen" element={<CitizenMode />} />

        {/* Catch all redirect to Responder Dashboard */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  )
}

export default App
