import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { getBusiness, launchAudits } from '../services/api.js'
import './BusinessDetailPage.css'

const STATUS_LABELS = {
  pending: 'Pending',
  crawling: 'Crawling',
  extracting: 'Extracting',
  analyzing: 'Analyzing',
  scoring: 'Scoring',
  complete: 'Complete',
  failed: 'Failed',
}

const STATUS_COLORS = {
  pending: 'status--pending',
  crawling: 'status--active',
  extracting: 'status--active',
  analyzing: 'status--active',
  scoring: 'status--active',
  complete: 'status--complete',
  failed: 'status--failed',
}

export default function BusinessDetailPage() {
  const { businessId } = useParams()
  const navigate = useNavigate()
  const [business, setBusiness] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [launching, setLaunching] = useState(false)

  useEffect(() => {
    async function fetchBusiness() {
      try {
        const data = await getBusiness(businessId)
        setBusiness(data)
      } catch (err) {
        setError(err.message || 'Failed to load business.')
      } finally {
        setLoading(false)
      }
    }
    fetchBusiness()
  }, [businessId])

  async function handleRunAudit() {
    setLaunching(true)
    setError('')

    try {
      const result = await launchAudits([businessId])
      navigate(`/bulk/${result.batch_id}`)
    } catch (err) {
      setError(err.message || 'Failed to launch audit.')
      setLaunching(false)
    }
  }

  if (loading) {
    return (
      <main className="business-detail">
        <div className="container">
          <div className="business-detail__loading">Loading business…</div>
        </div>
      </main>
    )
  }

  if (error && !business) {
    return (
      <main className="business-detail">
        <div className="container">
          <header className="business-detail__header">
            <a href="/" className="business-detail__logo">
              Zero to <span>GEO</span>
            </a>
          </header>
          <div className="business-detail__error" role="alert">{error}</div>
        </div>
      </main>
    )
  }

  const latestAudit = business.audits && business.audits.length > 0 ? business.audits[0] : null

  return (
    <main className="business-detail">
      <div className="container">
        <header className="business-detail__header">
          <a href="/" className="business-detail__logo">
            Zero to <span>GEO</span>
          </a>
          <nav className="business-detail__nav" aria-label="Breadcrumb navigation">
            <Link to="/businesses" className="business-detail__back">← All Businesses</Link>
          </nav>
        </header>

        <div className="business-detail__card">
          {/* Business Info */}
          <div className="business-detail__info-row">
            <div className="business-detail__info">
              <h1 className="business-detail__name">{business.name}</h1>
              <div className="business-detail__meta">
                <a
                  href={business.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="business-detail__website"
                >
                  {(business.website || '').replace(/^https?:\/\//, '')}
                </a>
                {(business.city || business.state) && (
                  <span className="business-detail__location">
                    📍 {[business.city, business.state].filter(Boolean).join(', ')}
                  </span>
                )}
                {business.category && (
                  <span className="business-detail__category">
                    🏷️ {business.category}
                  </span>
                )}
              </div>
            </div>
            <button
              className="btn btn--primary btn--large"
              onClick={handleRunAudit}
              disabled={launching}
              aria-label="Run a new audit for this business"
            >
              {launching ? 'Launching…' : 'Run New Audit'}
            </button>
          </div>

          {error && (
            <div className="business-detail__error" role="alert">{error}</div>
          )}

          {/* Latest Audit Summary */}
          {latestAudit && (
            <div className="business-detail__latest">
              <h2 className="business-detail__section-title">Latest Audit</h2>
              <div className="business-detail__latest-card">
                <div className="business-detail__latest-score">
                  {latestAudit.overall_score != null ? (
                    <span className="business-detail__score-value">{Math.round(latestAudit.overall_score)}</span>
                  ) : (
                    <span className="business-detail__score-value business-detail__score-value--na">—</span>
                  )}
                  <span className="business-detail__score-label">Score</span>
                </div>
                <div className="business-detail__latest-info">
                  <span className={`status-badge ${STATUS_COLORS[latestAudit.status] || ''}`}>
                    {STATUS_LABELS[latestAudit.status] || latestAudit.status}
                  </span>
                  {latestAudit.completed_at && (
                    <span className="business-detail__latest-date">
                      {new Date(latestAudit.completed_at).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                      })}
                    </span>
                  )}
                </div>
                {latestAudit.status === 'complete' && (
                  <Link
                    to={`/audit/${latestAudit.id}/report`}
                    className="btn btn--primary btn--small"
                  >
                    View Report
                  </Link>
                )}
              </div>
            </div>
          )}

          {/* Audit History */}
          <div className="business-detail__history">
            <h2 className="business-detail__section-title">Audit History</h2>
            {(!business.audits || business.audits.length === 0) ? (
              <p className="business-detail__no-audits">
                No audits yet. Click "Run New Audit" to get started.
              </p>
            ) : (
              <div className="business-detail__history-list">
                {business.audits.map(audit => (
                  <div key={audit.id} className="business-detail__history-item">
                    <span className="business-detail__history-date">
                      {audit.completed_at
                        ? new Date(audit.completed_at).toLocaleDateString('en-US', {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })
                        : audit.created_at
                          ? new Date(audit.created_at).toLocaleDateString('en-US', {
                              year: 'numeric',
                              month: 'short',
                              day: 'numeric',
                            })
                          : '—'}
                    </span>
                    <span className="business-detail__history-score">
                      Score: {audit.overall_score != null ? Math.round(audit.overall_score) : '—'}
                    </span>
                    <span className={`status-badge ${STATUS_COLORS[audit.status] || ''}`}>
                      {STATUS_LABELS[audit.status] || audit.status}
                    </span>
                    {audit.status === 'complete' && (
                      <Link
                        to={`/audit/${audit.id}/report`}
                        className="btn btn--small"
                      >
                        View Report
                      </Link>
                    )}
                    {audit.status === 'failed' && audit.error_message && (
                      <span className="business-detail__history-error" title={audit.error_message}>
                        ⚠️ {audit.error_message.slice(0, 50)}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  )
}
