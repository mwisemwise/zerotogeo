import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getAuditReport } from '../services/api.js'
import './AuditReportPage.css'

// ---------------------------------------------------------------------------
// Category mapping — maps pillars to presentation categories
// ---------------------------------------------------------------------------

const CATEGORY_CONFIG = {
  credibility: {
    key: 'credibility',
    label: 'Credibility',
    description: 'Consumer confidence and trust signals',
    pillars: ['authority'],
  },
  visibility: {
    key: 'visibility',
    label: 'Visibility',
    description: 'Local search and AI visibility signals',
    pillars: ['local_signals'],
  },
  ai_readiness: {
    key: 'ai_readiness',
    label: 'AI / Entity Readiness',
    description: 'How clearly AI systems can identify and cite this business',
    pillars: ['entity_clarity', 'citation_readiness'],
  },
  technical: {
    key: 'technical',
    label: 'Website / Technical',
    description: 'Structured data and technical website signals',
    pillars: ['structured_data'],
  },
  content: {
    key: 'content',
    label: 'Content / Answerability',
    description: 'Whether AI systems can extract useful answers from this site',
    pillars: ['content'],
  },
}

// Reverse map: pillar → category key
const PILLAR_TO_CATEGORY = {}
for (const [catKey, config] of Object.entries(CATEGORY_CONFIG)) {
  for (const pillar of config.pillars) {
    PILLAR_TO_CATEGORY[pillar] = catKey
  }
}

function classificationCssKey(classification) {
  return classification.toLowerCase().replace(/\s+/g, '-')
}

function groupFindingsByCategory(findings, pillarResults) {
  const categories = {}

  // Initialize all categories
  for (const [key, config] of Object.entries(CATEGORY_CONFIG)) {
    categories[key] = {
      ...config,
      problems: [],
      strengths: [],
      score: null,
    }
  }

  // Calculate average score per category from pillar results
  if (pillarResults?.length > 0) {
    for (const [key, config] of Object.entries(CATEGORY_CONFIG)) {
      const relevantPillars = pillarResults.filter(p => config.pillars.includes(p.pillar))
      if (relevantPillars.length > 0) {
        const avg = relevantPillars.reduce((sum, p) => sum + p.score, 0) / relevantPillars.length
        categories[key].score = Math.round(avg)
      }
    }
  }

  // Sort findings into categories
  for (const finding of (findings || [])) {
    const catKey = PILLAR_TO_CATEGORY[finding.pillar] || 'technical'
    if (!categories[catKey]) continue

    if (finding.severity === 'positive') {
      categories[catKey].strengths.push(finding)
    } else {
      categories[catKey].problems.push(finding)
    }
  }

  return categories
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

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
  } = report

  const cssClass = classificationCssKey(classification)
  const categories = groupFindingsByCategory(findings, pillar_results)

  // Collect all positive findings across categories
  const allStrengths = Object.values(categories).flatMap(cat => cat.strengths)

  // Categories with problems (for display)
  const categoriesWithProblems = Object.values(categories).filter(cat => cat.problems.length > 0)

  return (
    <main className="report">
      <div className="container">
        <header className="report__header">
          <Link to="/" className="report__logo">Zero to <span>GEO</span></Link>
          <Link to="/audit/new" className="btn btn--secondary">New Audit</Link>
        </header>

        {/* GEO Percentile */}
        <section className="report__score-section" aria-label="GEO Percentile">
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

        {/* Pillar Percentiles */}
        {pillar_results?.length > 0 && (
          <section className="report__section" aria-label="Pillar Percentiles">
            <h2 className="report__section-title">GEO Pillar Percentiles</h2>
            <div className="report__pillar-grid">
              {pillar_results.map(pillar => (
                <PillarCard key={pillar.pillar} pillar={pillar} />
              ))}
            </div>
          </section>
        )}

        {/* Grouped Findings by Category */}
        {categoriesWithProblems.length > 0 && (
          <section className="report__section" aria-label="Opportunities">
            <h2 className="report__section-title">Opportunities for Improvement</h2>
            <div className="report__categories">
              {categoriesWithProblems.map(cat => (
                <CategoryGroup key={cat.key} category={cat} />
              ))}
            </div>
          </section>
        )}

        {/* What You're Doing Well */}
        {allStrengths.length > 0 && (
          <section className="report__section" aria-label="Strengths">
            <h2 className="report__section-title">What You're Doing Well</h2>
            <div className="report__strengths-grid">
              {allStrengths.map((finding, i) => (
                <StrengthCard key={finding.id || i} finding={finding} />
              ))}
            </div>
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
  const percentile = Math.round(score)
  return (
    <div className={`report__score-circle report__score-circle--${cssClass}`}>
      <span className="report__score-number">{percentile}<sup className="report__score-th">{getOrdinalSuffix(percentile)}</sup></span>
      <span className="report__score-max">percentile</span>
    </div>
  )
}

function getOrdinalSuffix(n) {
  const s = ['th', 'st', 'nd', 'rd']
  const v = n % 100
  return s[(v - 20) % 10] || s[v] || s[0]
}

function PillarCard({ pillar }) {
  const percentile = Math.round(pillar.score)
  const scoreClass =
    pillar.score >= 75 ? 'strong' :
    pillar.score >= 60 ? 'good' :
    pillar.score >= 40 ? 'needs-work' : 'poor'

  return (
    <div className="report__pillar-card">
      <div className="report__pillar-name">{pillar.pillar_display || pillar.pillar}</div>
      <div className={`report__pillar-score report__pillar-score--${scoreClass}`}>
        {percentile}<sup className="report__pillar-th">{getOrdinalSuffix(percentile)}</sup>
        <span className="report__pillar-percentile-label"> percentile</span>
      </div>
      <div className="report__pillar-bar">
        <div
          className={`report__pillar-bar-fill report__pillar-bar-fill--${scoreClass}`}
          style={{ width: `${Math.min(100, pillar.score)}%` }}
          role="progressbar"
          aria-valuenow={percentile}
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

function CategoryGroup({ category }) {
  const [expanded, setExpanded] = useState(false)
  const { label, description, score, problems } = category

  const scoreClass =
    score === null ? '' :
    score >= 75 ? 'strong' :
    score >= 60 ? 'good' :
    score >= 40 ? 'needs-work' : 'poor'

  return (
    <div className="report__category">
      <button
        className="report__category-header"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        aria-controls={`category-${category.key}`}
      >
        <div className="report__category-info">
          <h3 className="report__category-label">{label}</h3>
          <p className="report__category-desc">{description}</p>
        </div>
        <div className="report__category-meta">
          {score !== null && (
            <span className={`report__category-score report__category-score--${scoreClass}`}>
              {score}{getOrdinalSuffix(score)} percentile
            </span>
          )}
          <span className="report__category-count">
            {problems.length} {problems.length === 1 ? 'issue' : 'issues'}
          </span>
          <span className={`report__category-chevron${expanded ? ' report__category-chevron--open' : ''}`} aria-hidden="true">
            ▸
          </span>
        </div>
      </button>

      {expanded && (
        <div className="report__category-findings" id={`category-${category.key}`}>
          {problems.map((finding, i) => (
            <FindingCard key={finding.id || i} finding={finding} />
          ))}
        </div>
      )}
    </div>
  )
}

function FindingCard({ finding }) {
  const [expanded, setExpanded] = useState(false)
  const [showRec, setShowRec] = useState(false)

  return (
    <article className={`report__finding report__finding--${finding.severity}`}>
      <button
        className="report__finding-toggle"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
      >
        <div className="report__finding-header">
          <h4 className="report__finding-title">{finding.title}</h4>
          <span className={`report__finding-severity report__finding-severity--${finding.severity}`}>
            {finding.severity}
          </span>
        </div>
      </button>

      {expanded && (
        <div className="report__finding-body">
          {/* Why this matters */}
          <div className="report__finding-section">
            <strong className="report__finding-label">Why this matters</strong>
            <p className="report__finding-text">{finding.finding}</p>
          </div>

          {/* Evidence — only when present */}
          {finding.evidence && (
            <div className="report__finding-section">
              <strong className="report__finding-label">Evidence</strong>
              <div className="report__finding-evidence">
                {finding.evidence}
              </div>
            </div>
          )}

          {/* Recommendation — collapsed behind a button */}
          {finding.recommendation && (
            <div className="report__finding-section">
              {!showRec ? (
                <button
                  className="report__finding-rec-btn"
                  onClick={() => setShowRec(true)}
                >
                  View Recommended Action
                </button>
              ) : (
                <div className="report__finding-rec">
                  <strong className="report__finding-label">Recommended Action</strong>
                  <p className="report__finding-rec-text">{finding.recommendation}</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </article>
  )
}

function StrengthCard({ finding }) {
  return (
    <article className="report__strength">
      <div className="report__strength-icon" aria-hidden="true">✓</div>
      <div className="report__strength-content">
        <h4 className="report__strength-title">{finding.title}</h4>
        <p className="report__strength-text">{finding.finding}</p>
        {finding.evidence && (
          <div className="report__strength-evidence">{finding.evidence}</div>
        )}
      </div>
    </article>
  )
}
