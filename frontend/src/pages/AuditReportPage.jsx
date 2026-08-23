import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getAuditReport } from '../services/api.js'
import './AuditReportPage.css'

function classificationCssKey(classification) {
  return classification.toLowerCase().replace(/\s+/g, '-')
}

export default function AuditReportPage() {
  const { auditId } = useParams()
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function loadReport() {
      try {
        const data = await getAuditReport(auditId)
        setReport(data)
      } catch (err) {
        setError(err.message || 'Failed to load report.')
      } finally {
        setLoading(false)
      }
    }
    loadReport()
  }, [auditId])

  if (loading) {
    return (
      <main className="report">
        <div className="container">
          <div className="report__loading" aria-live="polite">
            Loading your GEO report…
          </div>
        </div>
      </main>
    )
  }

  if (error) {
    return (
      <main className="report">
        <div className="container">
          <div className="report__error" role="alert">
            <p>{error}</p>
            <Link to="/audit/new" className="btn btn--secondary">Run a New Audit</Link>
          </div>
        </div>
      </main>
    )
  }

  const {
    business,
    overall_score,
    classification,
    summary,
    pillar_results,
    findings,
    action_plan,
  } = report

  const cssClass = classificationCssKey(classification)

  // Separate strengths from problems
  const problems = (findings || []).filter(f => f.severity !== 'positive')
  const strengths = (findings || []).filter(f => f.severity === 'positive')

  return (
    <main className="report">
      <div className="container">
        <header className="report__header">
          <Link to="/" className="report__logo">Zero to <span>GEO</span></Link>
          <Link to="/audit/new" className="btn btn--secondary">New Audit</Link>
        </header>

        {/* GEO Score */}
        <section className="report__score-section" aria-label="GEO Score">
          <ScoreCircle score={overall_score} cssClass={cssClass} />
          <h1 className="report__score-classification">{classification}</h1>
          <p className="report__score-business">
            {business?.name}
            {business?.city && business?.state && ` · ${business.city}, ${business.state}`}
          </p>
        </section>

        {/* Executive Summary */}
        {summary && (
          <section className="report__section" aria-label="Executive Summary">
            <h2 className="report__section-title">Executive Summary</h2>
            <p className="report__summary-text">{summary}</p>
          </section>
        )}

        {/* Pillar Scores */}
        {pillar_results?.length > 0 && (
          <section className="report__section" aria-label="Pillar Scores">
            <h2 className="report__section-title">GEO Pillar Scores</h2>
            <div className="report__pillar-grid">
              {pillar_results.map(pillar => (
                <PillarCard key={pillar.pillar} pillar={pillar} />
              ))}
            </div>
          </section>
        )}

        {/* Top Problems */}
        {problems.length > 0 && (
          <section className="report__section" aria-label="Top Problems">
            <h2 className="report__section-title">Top Problems</h2>
            {problems.slice(0, 10).map((finding, i) => (
              <FindingCard key={finding.id || i} finding={finding} />
            ))}
          </section>
        )}

        {/* Strengths */}
        {strengths.length > 0 && (
          <section className="report__section" aria-label="Top Strengths">
            <h2 className="report__section-title">Top Strengths</h2>
            {strengths.map((finding, i) => (
              <FindingCard key={finding.id || i} finding={finding} />
            ))}
          </section>
        )}

        {/* Action Plan */}
        {action_plan?.length > 0 && (
          <section className="report__section" aria-label="Action Plan">
            <h2 className="report__section-title">Action Plan</h2>
            <ActionPlanList items={action_plan} />
          </section>
        )}

        {/* Footer CTA */}
        <div className="report__footer-cta">
          <Link to="/audit/new" className="btn btn--primary">Run Another Audit</Link>
        </div>
      </div>
    </main>
  )
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ScoreCircle({ score, cssClass }) {
  return (
    <div className={`report__score-circle report__score-circle--${cssClass}`}>
      <span className="report__score-number">{Math.round(score)}</span>
      <span className="report__score-max">/100</span>
    </div>
  )
}

function PillarCard({ pillar }) {
  const scoreClass =
    pillar.score >= 75 ? 'strong' :
    pillar.score >= 60 ? 'good' :
    pillar.score >= 40 ? 'needs-work' : 'poor'

  return (
    <div className="report__pillar-card">
      <div className="report__pillar-name">{pillar.pillar_display || pillar.pillar}</div>
      <div className={`report__pillar-score report__pillar-score--${scoreClass}`}>
        {Math.round(pillar.score)}
      </div>
      <div className="report__pillar-bar">
        <div
          className={`report__pillar-bar-fill report__pillar-bar-fill--${scoreClass}`}
          style={{ width: `${Math.min(100, pillar.score)}%` }}
          role="progressbar"
          aria-valuenow={Math.round(pillar.score)}
          aria-valuemin="0"
          aria-valuemax="100"
        />
      </div>
      {pillar.summary && (
        <p className="report__pillar-summary">{pillar.summary}</p>
      )}
    </div>
  )
}

function FindingCard({ finding }) {
  return (
    <article className={`report__finding report__finding--${finding.severity}`}>
      <div className="report__finding-header">
        <h3 className="report__finding-title">{finding.title}</h3>
        <span className={`report__finding-severity report__finding-severity--${finding.severity}`}>
          {finding.severity}
        </span>
      </div>
      <p className="report__finding-text">{finding.finding}</p>
      {finding.evidence && (
        <div className="report__finding-evidence">
          <strong>Evidence:</strong> {finding.evidence}
        </div>
      )}
      {finding.recommendation && (
        <p className="report__finding-recommendation">
          <strong>↗ Recommendation:</strong> {finding.recommendation}
        </p>
      )}
    </article>
  )
}

function ActionPlanList({ items }) {
  return (
    <ol className="report__action-list">
      {items.map((action, i) => (
        <li key={i} className="report__action-item">
          <span className={`report__action-priority report__action-priority--${action.priority.toLowerCase()}`}>
            {action.priority}
          </span>
          <div className="report__action-content">
            <span className="report__action-text">{action.description}</span>
            <span className="report__action-pillar">{action.pillar_display}</span>
          </div>
        </li>
      ))}
    </ol>
  )
}
