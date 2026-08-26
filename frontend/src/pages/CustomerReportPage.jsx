import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getCustomerReport, getAuditReport, updateFindingStatus } from '../services/api.js'
import './CustomerReportPage.css'

// ---------------------------------------------------------------------------
// Pillar → Five C's mapping (translates technical audit to customer framework)
// ---------------------------------------------------------------------------

const PILLAR_TO_CATEGORY = {
  structured_data: 'crawlability',
  entity_clarity: 'clarity',
  local_signals: 'clarity',
  content: 'content',
  authority: 'credibility',
  citation_readiness: 'crawlability',
}

const CATEGORY_EXPLANATIONS = {
  crawlability: 'Your site needs to be easily accessible to Google and AI systems so they can find and process the information about your business.',
  clarity: 'Your website needs to make it easy for Google, AI, and customers to understand who you are, what you do, where you work, and what each page is about.',
  content: 'Your website needs to provide the useful, specific information customers, Google, and AI need to understand your services and answer questions about your business.',
  credibility: 'Your website needs to provide clear, consistent evidence that your business is legitimate, qualified, experienced, and trustworthy.',
  confidence: 'Your Google and AI confidence is the result of how well your website can be accessed, understood, supported by useful content, and backed by credible evidence.',
}

/**
 * Translate existing audit findings into the Five C's framework.
 * This bridges the old technical audit data into the new customer-facing structure.
 */
function translateAuditToCustomerReport(auditReport) {
  const { business, findings, pillar_results } = auditReport

  // Build categories from existing findings
  const categoryMap = {
    crawlability: [],
    clarity: [],
    content: [],
    credibility: [],
  }

  for (const finding of (findings || [])) {
    if (finding.severity === 'positive') continue
    const category = PILLAR_TO_CATEGORY[finding.pillar] || 'content'
    categoryMap[category].push({
      id: finding.id,
      business_id: business?.id || '',
      audit_id: finding.audit_id,
      category,
      customer_finding: finding.finding || finding.title,
      evidence: finding.evidence || 'Identified during automated site analysis.',
      source_url: null,
      affected_page: null,
      severity: finding.severity,
      recommended_fix: finding.recommendation || null,
      status: 'open',
      verified: false,
      created_at: auditReport.created_at,
      updated_at: auditReport.created_at,
    })
  }

  const categories = Object.entries(categoryMap).map(([cat, catFindings]) => ({
    category: cat,
    display_name: cat.toUpperCase(),
    explanation: CATEGORY_EXPLANATIONS[cat],
    issue_count: catFindings.length,
    findings: catFindings,
  }))

  // Build confidence summary
  const allIssueCategories = categories.filter(c => c.issue_count > 0).map(c => c.display_name.toLowerCase())
  let confidenceSummary = 'No significant issues were identified affecting your position.'
  if (allIssueCategories.length > 0) {
    const issueStr = allIssueCategories.length > 1
      ? allIssueCategories.slice(0, -1).join(', ') + ', and ' + allIssueCategories[allIssueCategories.length - 1]
      : allIssueCategories[0]
    confidenceSummary = `Your current position is being affected by problems with ${issueStr}.`
  }

  const contributingIssues = (findings || [])
    .filter(f => f.severity !== 'positive')
    .slice(0, 5)
    .map(f => f.finding || f.title)

  // Build fixes
  const fixes = categories
    .filter(cat => cat.findings.some(f => f.recommended_fix))
    .map(cat => ({
      category: cat.category,
      display_name: cat.display_name,
      fixes: [...new Set(cat.findings.filter(f => f.recommended_fix).map(f => f.recommended_fix))],
    }))

  return {
    business_id: business?.id || '',
    business_name: business?.name || '',
    business_city: business?.city || '',
    business_state: business?.state || '',
    business_category: business?.category || '',
    audit_id: auditReport.id,
    audit_created_at: auditReport.created_at,
    position: null,
    total_competitors: null,
    rankings: [],
    categories,
    confidence: {
      explanation: CATEGORY_EXPLANATIONS.confidence,
      summary: confidenceSummary,
      contributing_issues: contributingIssues,
    },
    competitor_evidence: [],
    fixes,
  }
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function CustomerReportPage() {
  const { auditId } = useParams()
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function loadReport() {
      try {
        // Try the new customer report endpoint first
        const data = await getCustomerReport(auditId)
        // If it has findings data, use it directly
        if (data.categories && data.categories.some(c => c.issue_count > 0)) {
          setReport(data)
        } else {
          // Fall back: translate the existing technical audit into Five C's format
          const auditData = await getAuditReport(auditId)
          setReport(translateAuditToCustomerReport(auditData))
        }
      } catch (err) {
        // If customer report fails (404, 409), try the existing audit report
        try {
          const auditData = await getAuditReport(auditId)
          setReport(translateAuditToCustomerReport(auditData))
        } catch (fallbackErr) {
          setError(fallbackErr.message || 'Failed to load report.')
        }
      } finally {
        setLoading(false)
      }
    }
    loadReport()
  }, [auditId])

  if (loading) {
    return (
      <main className="customer-report">
        <div className="container">
          <div className="customer-report__loading" aria-live="polite">
            Loading your audit report…
          </div>
        </div>
      </main>
    )
  }

  if (error) {
    return (
      <main className="customer-report">
        <div className="container">
          <div className="customer-report__error" role="alert">
            <p>{error}</p>
            <Link to="/businesses" className="btn btn--secondary">Back to Businesses</Link>
          </div>
        </div>
      </main>
    )
  }

  return (
    <main className="customer-report">
      <div className="container">
        <header className="customer-report__header">
          <Link to="/" className="customer-report__logo">Zero to <span>GEO</span></Link>
          <Link to="/businesses" className="btn btn--secondary">All Businesses</Link>
        </header>

        {/* PAGE 1: YOUR CURRENT POSITION */}
        <PositionSection report={report} />

        {/* PAGE 2: WHY YOU ARE WHERE YOU ARE */}
        <FiveCsSection report={report} />

        {/* COMPETITIVE COMPARISON */}
        {report.competitor_evidence?.length > 0 && (
          <CompetitiveSection report={report} />
        )}

        {/* WHAT WE CAN FIX */}
        {report.fixes?.length > 0 && (
          <FixesSection report={report} />
        )}

        {/* Footer */}
        <div className="customer-report__footer">
          <Link to={`/audit/${auditId}/summary`} className="btn btn--secondary">
            View the Summary
          </Link>
        </div>
      </div>
    </main>
  )
}


// ---------------------------------------------------------------------------
// PAGE 1: YOUR CURRENT POSITION
// ---------------------------------------------------------------------------

function PositionSection({ report }) {
  const { position, total_competitors, rankings, business_name } = report

  // Separate by ranking type
  const googleRankings = rankings.filter(r => r.ranking_type === 'google')
  const aiRankings = rankings.filter(r => r.ranking_type === 'ai')

  // Use google rankings as primary, fall back to all
  const primaryRankings = googleRankings.length > 0 ? googleRankings : rankings

  return (
    <section className="customer-report__section customer-report__position" aria-label="Your Current Position">
      <h1 className="customer-report__page-title">YOUR CURRENT POSITION</h1>

      {position && total_competitors ? (
        <div className="position__rank">
          <span className="position__rank-number">#{position}</span>
          <span className="position__rank-of"> of {total_competitors}</span>
          <span className="position__rank-suffix"> — for now</span>
        </div>
      ) : (
        <div className="position__rank">
          <span className="position__rank-pending">Position data pending</span>
        </div>
      )}

      {position && total_competitors && (
        <p className="position__explanation">
          You are currently #{position} of {total_competitors} businesses competing
          for this service in this market.
        </p>
      )}

      {/* Primary ranking list */}
      {primaryRankings.length > 0 && (
        <div className="position__list">
          {position && (
            <h3 className="position__list-heading">
              {primaryRankings.filter(r => r.position < position).length > 0
                ? 'Businesses currently ahead:'
                : 'Current standings:'}
            </h3>
          )}
          <ol className="position__competitors">
            {primaryRankings
              .sort((a, b) => a.position - b.position)
              .map((r) => (
                <li
                  key={r.id}
                  className={`position__competitor${r.is_subject ? ' position__competitor--you' : ''}`}
                >
                  <span className="position__competitor-rank">#{r.position}</span>
                  <span className="position__competitor-name">
                    {r.is_subject ? 'YOU' : r.competitor_name}
                  </span>
                  {r.is_subject && (
                    <span className="position__competitor-badge">Your Business</span>
                  )}
                </li>
              ))}
          </ol>
        </div>
      )}

      {/* AI rankings shown separately if different from Google */}
      {aiRankings.length > 0 && googleRankings.length > 0 && (
        <div className="position__list position__list--ai">
          <h3 className="position__list-heading">AI Results (separate measurement)</h3>
          <ol className="position__competitors">
            {aiRankings
              .sort((a, b) => a.position - b.position)
              .map((r) => (
                <li
                  key={r.id}
                  className={`position__competitor${r.is_subject ? ' position__competitor--you' : ''}`}
                >
                  <span className="position__competitor-rank">#{r.position}</span>
                  <span className="position__competitor-name">
                    {r.is_subject ? 'YOU' : r.competitor_name}
                  </span>
                </li>
              ))}
          </ol>
        </div>
      )}
    </section>
  )
}


// ---------------------------------------------------------------------------
// PAGE 2: WHY YOU ARE WHERE YOU ARE (Five C's)
// ---------------------------------------------------------------------------

function FiveCsSection({ report }) {
  const { categories, confidence } = report

  return (
    <section className="customer-report__section" aria-label="Why You Are Where You Are">
      <h2 className="customer-report__page-title">WHY YOU ARE WHERE YOU ARE</h2>

      {/* Four C categories — expandable */}
      <div className="fivecs__categories">
        {categories.map(cat => (
          <CategoryExpandable key={cat.category} category={cat} />
        ))}

        {/* Confidence — the fifth C (summary, not a category) */}
        {confidence && (
          <ConfidenceExpandable confidence={confidence} />
        )}
      </div>
    </section>
  )
}

function CategoryExpandable({ category }) {
  const [expanded, setExpanded] = useState(false)
  const { display_name, explanation, issue_count, findings } = category

  // Short definitions for each category (shown in header)
  const SHORT_DEFS = {
    crawlability: 'Can search & AI crawl and index',
    clarity: 'Can search & AI understand who, what, where',
    content: 'Does the site answer real questions',
    credibility: 'Can trust & authority be verified',
  }

  const shortDef = SHORT_DEFS[category.category] || explanation

  // Group findings by their core problem (customer_finding is the problem statement)
  // Multiple technical findings that point to the same problem get grouped as evidence
  const groupedProblems = groupFindingsIntoProblems(findings)

  return (
    <div className="fivecs__category">
      <button
        className="fivecs__category-header"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        aria-controls={`category-${category.category}`}
      >
        <div className="fivecs__category-info">
          <h3 className="fivecs__category-name">{display_name}</h3>
          <span className="fivecs__category-def">{shortDef}</span>
        </div>
        <span className="fivecs__category-count">
          {groupedProblems.length} {groupedProblems.length === 1 ? 'problem' : 'problems'}
        </span>
        <span className={`fivecs__chevron${expanded ? ' fivecs__chevron--open' : ''}`} aria-hidden="true">
          ▸
        </span>
      </button>

      {expanded && (
        <div className="fivecs__category-body" id={`category-${category.category}`}>
          {groupedProblems.length === 0 ? (
            <p className="fivecs__no-issues">No problems identified in this area.</p>
          ) : (
            <div className="fivecs__findings">
              {groupedProblems.map((problem, index) => (
                <ProblemExpandable key={problem.id} problem={problem} index={index + 1} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/**
 * Group multiple findings into single problems with evidence.
 * If findings share a similar root cause, they become evidence under one problem.
 * Otherwise each finding is its own problem with its evidence field as evidence items.
 */
function groupFindingsIntoProblems(findings) {
  // For now, each finding becomes a problem, and its evidence field
  // contains the supporting proof. The evidence string gets split into
  // individual evidence items if it contains multiple sentences/lines.
  return findings.map(f => ({
    id: f.id,
    problem: f.customer_finding,
    severity: f.severity,
    evidence: splitEvidence(f.evidence),
    recommended_fix: f.recommended_fix,
  }))
}

/**
 * Split evidence text into individual evidence items.
 * Splits on newlines, semicolons, or numbered patterns.
 */
function splitEvidence(evidenceText) {
  if (!evidenceText) return []
  // Split on newlines or semicolons
  const items = evidenceText
    .split(/[;\n]/)
    .map(s => s.trim())
    .filter(s => s.length > 0)
  return items
}

function ProblemExpandable({ problem, index }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <article className={`finding finding--${problem.severity}`}>
      <button
        className="finding__toggle"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
      >
        <span className="finding__title">{index}. {problem.problem}</span>
        <span className={`finding__severity finding__severity--${problem.severity}`}>
          {problem.severity}
        </span>
      </button>

      {expanded && (
        <div className="finding__body">
          {/* EVIDENCE — proof from credible sources */}
          {problem.evidence.length > 0 && (
            <div className="finding__section">
              <strong className="finding__label">EVIDENCE</strong>
              <ol className="finding__evidence-list">
                {problem.evidence.map((item, i) => (
                  <li key={i} className="finding__evidence-item">{item}</li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}
    </article>
  )
}

function ConfidenceExpandable({ confidence }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="fivecs__category fivecs__category--confidence">
      <button
        className="fivecs__category-header"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        aria-controls="category-confidence"
      >
        <div className="fivecs__category-info">
          <h3 className="fivecs__category-name">CONFIDENCE</h3>
          <span className="fivecs__category-def">The result of all four categories combined</span>
        </div>
        <span className={`fivecs__chevron${expanded ? ' fivecs__chevron--open' : ''}`} aria-hidden="true">
          ▸
        </span>
      </button>

      {expanded && (
        <div className="fivecs__category-body" id="category-confidence">
          <div className="confidence__summary">
            <h4 className="confidence__heading">WHAT IS HURTING YOUR CONFIDENCE?</h4>
            <p className="confidence__text">{confidence.summary}</p>

            {confidence.contributing_issues?.length > 0 && (
              <ul className="confidence__issues">
                {confidence.contributing_issues.map((issue, i) => (
                  <li key={i} className="confidence__issue">{issue}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  )
}


// ---------------------------------------------------------------------------
// Individual Finding (Expandable)
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// COMPETITIVE COMPARISON
// ---------------------------------------------------------------------------

function CompetitiveSection({ report }) {
  const { competitor_evidence, rankings } = report

  // Group evidence by competitor
  const byCompetitor = {}
  for (const ev of competitor_evidence) {
    if (!byCompetitor[ev.competitor_name]) {
      byCompetitor[ev.competitor_name] = []
    }
    byCompetitor[ev.competitor_name].push(ev)
  }

  // Get the subject's ranking position
  const subjectRanking = rankings.find(r => r.is_subject)
  const aheadCompetitors = rankings
    .filter(r => !r.is_subject && subjectRanking && r.position < subjectRanking.position)
    .sort((a, b) => a.position - b.position)

  return (
    <section className="customer-report__section" aria-label="Competitive Comparison">
      <h2 className="customer-report__section-title">COMPETITIVE COMPARISON</h2>

      {aheadCompetitors.length > 0 && (
        <p className="competitive__intro">
          These are the businesses currently ahead of you.
        </p>
      )}

      <div className="competitive__grid">
        {Object.entries(byCompetitor).map(([name, evidenceList]) => (
          <CompetitorCard key={name} name={name} evidence={evidenceList} />
        ))}
      </div>
    </section>
  )
}

function CompetitorCard({ name, evidence }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="competitive__card">
      <button
        className="competitive__card-header"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
      >
        <h3 className="competitive__name">{name}</h3>
        <span className={`fivecs__chevron${expanded ? ' fivecs__chevron--open' : ''}`} aria-hidden="true">
          ▸
        </span>
      </button>

      {expanded && (
        <div className="competitive__card-body">
          <ul className="competitive__evidence-list">
            {evidence.map(ev => (
              <li key={ev.id} className="competitive__evidence-item">
                {ev.evidence_summary}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}


// ---------------------------------------------------------------------------
// WHAT WE CAN FIX
// ---------------------------------------------------------------------------

function FixesSection({ report }) {
  return (
    <section className="customer-report__section" aria-label="What We Can Fix">
      <h2 className="customer-report__page-title">WHAT WE CAN FIX</h2>

      <div className="fixes__categories">
        {report.fixes.map(fixCat => (
          <div key={fixCat.category} className="fixes__category">
            <h3 className="fixes__category-name">{fixCat.display_name}</h3>
            <ul className="fixes__list">
              {fixCat.fixes.map((fix, i) => (
                <li key={i} className="fixes__item">{fix}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  )
}
