import { BrowserRouter, Routes, Route } from 'react-router-dom'
import LandingPage from './pages/LandingPage.jsx'
import AuditInputPage from './pages/AuditInputPage.jsx'
import AuditProcessingPage from './pages/AuditProcessingPage.jsx'
import AuditReportPage from './pages/AuditReportPage.jsx'
import NotFoundPage from './pages/NotFoundPage.jsx'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/audit/new" element={<AuditInputPage />} />
        <Route path="/audit/:auditId/processing" element={<AuditProcessingPage />} />
        <Route path="/audit/:auditId/report" element={<AuditReportPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  )
}
