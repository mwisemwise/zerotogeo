import { useEffect, useState, useRef } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getAuditStatus } from '../services/api.js'
import './AuditProcessingPage.css'

// Processing steps — label matches what the backend actually does.
const STEPS = [
  { key: 'crawl', label: 'Checking website' },
  { key: 'extract', label: 'Reading business information' },
  { key: 'analyze', label: 'Checking GEO signals' },
  { key: 'citation', label: 'Checking citation readiness' },
  { key: 'score', label: 'Calculating GEO score' },
]

// Map backend status → how many steps are complete
const STATUS_TO_STEP_INDEX = {
  pending: -1,
  crawling: 0,
  extracting: 1,
  analyzing: 2,
  scoring: 3,
  complete: 5,
  failed: -2,
}

const POLL_INTERVAL_MS = 1500
const MAX_POLLS = 120  // 3 minutes max

export default function AuditProcessingPage() {
  const { auditId } = useParams()
  const navigate = useNavigate()
  const [status, setStatus] = useState('pending')
  const [error, setError] = useState('')
  const pollCount = useRef(0)

  useEffect(() => {
    let timer
    let cancelled = false

    async function poll() {
      try {
        const data = await getAuditStatus(auditId)
        if (cancelled) return

        setStatus(data.status)

        if (data.status === 'complete') {
          navigate(`/audit/${auditId}/report`, { replace: true })
          return
        }

        if (data.status === 'failed') {
          setError(data.error_message || 'The audit could not be completed.')
          return
        }

        pollCount.current += 1
        if (pollCount.current >= MAX_POLLS) {
          setError('The audit is taking longer than expected. Please try again.')
          return
        }

        timer = setTimeout(poll, POLL_INTERVAL_MS)
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Lost connection to the server.')
        }
      }
    }

    poll()
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [auditId, navigate])

  const completedStepIndex = STATUS_TO_STEP_INDEX[status] ?? -1
  const isFailed = status === 'failed' || !!error

  return (
    <main className="processing">
      <div className="container">
        <header className="processing__header">
          <a href="/" className="processing__logo">
            Zero to <span>GEO</span>
          </a>
        </header>

        <div className="processing__card">
          <h1 className="processing__title">
            {isFailed ? 'Audit could not be completed' : 'Running your GEO audit…'}
          </h1>

          {!isFailed && (
            <p className="processing__subtitle">
              Analyzing your website. This typically takes 15–30 seconds.
            </p>
          )}

          {isFailed && error && (
            <div className="processing__error" role="alert">
              <p>{error}</p>
              <a href="/audit/new" className="btn btn--secondary processing__retry">
                Try Again
              </a>
            </div>
          )}

          {!isFailed && (
            <ul className="processing__steps" aria-live="polite" aria-label="Audit progress">
              {STEPS.map((step, index) => {
                const isDone = completedStepIndex > index
                const isActive = completedStepIndex === index
                return (
                  <li
                    key={step.key}
                    className={`processing__step ${
                      isDone ? 'processing__step--done' : ''
                    } ${isActive ? 'processing__step--active' : ''}`}
                  >
                    <span className="processing__step-indicator" aria-hidden="true">
                      {isDone ? '✓' : isActive ? '⟳' : '·'}
                    </span>
                    <span className="processing__step-label">{step.label}</span>
                    {isDone && (
                      <span className="processing__step-status">Complete</span>
                    )}
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      </div>
    </main>
  )
}
