import { BrowserRouter, Routes, Route } from 'react-router-dom'
import LandingPage from './pages/LandingPage.jsx'
import AuditInputPage from './pages/AuditInputPage.jsx'
import AuditProcessingPage from './pages/AuditProcessingPage.jsx'
import AuditReportPage from './pages/AuditReportPage.jsx'
import CustomerReportPage from './pages/CustomerReportPage.jsx'
import BulkStatusPage from './pages/BulkStatusPage.jsx'
import BusinessesPage from './pages/BusinessesPage.jsx'
import BusinessDetailPage from './pages/BusinessDetailPage.jsx'
import NotFoundPage from './pages/NotFoundPage.jsx'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/audit/new" element={<AuditInputPage />} />
        <Route path="/audit/:auditId/processing" element={<AuditProcessingPage />} />
        <Route path="/audit/:auditId/report" element={<CustomerReportPage />} />
        <Route path="/audit/:auditId/summary" element={<AuditReportPage />} />
        <Route path="/bulk/:batchId" element={<BulkStatusPage />} />
        <Route path="/businesses" element={<BusinessesPage />} />
        <Route path="/businesses/:businessId" element={<BusinessDetailPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  )
}
