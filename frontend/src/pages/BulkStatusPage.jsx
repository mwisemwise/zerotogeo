import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getBatchStatus } from '../services/api.js'
import './BulkStatusPage.css'

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

export default function BulkStatusPage() {
  const { batchId } = useParams()
  const navigate = useNavigate()
  const [batch, setBatch] = useState(null)
  const [error, setError] = useState('')
  const [polling, setPolling] = useState(true)

  useEffect(() => {
    let interval = null

    async function fetchStatus() {
      try {
        const data = await getBatchStatus(batchId)
        setBatch(data)
        // Stop polling when all audits are done
        if (data.in_progress === 0) {
          setPolling(false)
        }
      } catch (err) {
        setError(err.message || 'Failed to load batch status.')
        setPolling(false)
      }
    }

    fetchStatus()

    if (polling) {
      interval = setInterval(fetchStatus, 3000)
    }

    return () => {
      if (interval) clearInterval(interval)
    }
  }, [batchId, polling])

  if (error) {
    return (
      <main className="bulk-status">
        <div className="container">
          <div className="bulk-status__error">{error}</div>
        </div>
      </main>
    )
  }

  if (!batch) {
    return (
      <main className="bulk-status">
        <div className="container">
          <div className="bulk-status__loading">Loading batch status…</div>
        </div>
      </main>
    )
  }

  const progressPercent = batch.total > 0
    ? Math.round(((batch.completed + batch.failed) / batch.total) * 100)
    : 0

  return (
    <main className="bulk-status">
      <div className="container">
        <header className="bulk-status__header">
          <a href="/" className="bulk-status__logo">
            Zero to <span>GEO</span>
          </a>
        </header>

        <div className="bulk-status__card">
          <h1 className="bulk-status__title">Bulk Audit Progress</h1>

          {/* Progress summary */}
          <div className="bulk-status__summary">
            <div className="bulk-status__progress-bar">
              <div
                className="bulk-status__progress-fill"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <div className="bulk-status__stats">
              <span className="stat stat--total">{batch.total} total</span>
              <span className="stat stat--complete">{batch.completed} complete</span>
              {batch.failed > 0 && (
                <span className="stat stat--failed">{batch.failed} failed</span>
              )}
              {batch.in_progress > 0 && (
                <span className="stat stat--active">{batch.in_progress} in progress</span>
              )}
            </div>
          </div>

          {/* Audit table */}
          <div className="bulk-status__table-wrapper">
            <table className="bulk-status__table">
              <thead>
                <tr>
                  <th>Business</th>
                  <th>Website</th>
                  <th>Location</th>
                  <th>Category</th>
                  <th>Status</th>
                  <th>Score</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {batch.audits.map((audit) => (
                  <tr key={audit.audit_id} className={`audit-row ${STATUS_COLORS[audit.status] || ''}`}>
                    <td className="audit-row__name">{audit.business_name}</td>
                    <td className="audit-row__url">
                      <a href={audit.website_url} target="_blank" rel="noopener noreferrer">
                        {audit.website_url.replace(/^https?:\/\//, '')}
                      </a>
                    </td>
                    <td>{audit.city}, {audit.state}</td>
                    <td>{audit.category}</td>
                    <td>
                      <span className={`status-badge ${STATUS_COLORS[audit.status] || ''}`}>
                        {STATUS_LABELS[audit.status] || audit.status}
                      </span>
                    </td>
                    <td className="audit-row__score">
                      {audit.overall_score !== null ? Math.round(audit.overall_score) : '—'}
                    </td>
                    <td>
                      {audit.status === 'complete' && (
                        <button
                          className="btn btn--small"
                          onClick={() => navigate(`/audit/${audit.audit_id}/report`)}
                        >
                          View Report
                        </button>
                      )}
                      {audit.status === 'failed' && (
                        <span className="audit-row__error-hint" title={audit.error_message}>
                          ⚠️
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {batch.status === 'complete' && (
            <div className="bulk-status__done">
              ✅ All audits complete!
            </div>
          )}

          <div className="bulk-status__actions">
            <button
              className="btn btn--primary"
              onClick={() => navigate('/audit/new')}
            >
              Start New Audit
            </button>
          </div>
        </div>
      </div>
    </main>
  )
}
