import { useNavigate } from 'react-router-dom'
import './LandingPage.css'

export default function LandingPage() {
  const navigate = useNavigate()

  return (
    <main className="landing">
      <div className="container">
        <header className="landing__header">
          <div className="landing__logo">
            <span className="landing__logo-zero">Zero</span>
            <span className="landing__logo-sep"> to </span>
            <span className="landing__logo-geo">GEO</span>
          </div>
        </header>

        <section className="landing__hero">
          <h1 className="landing__headline" style={{ textAlign: 'center' }}>
            Is your company set up to be recommended and cited by AI?
          </h1>

          <p className="landing__subhead" style={{ textAlign: 'center', color: 'blue' }}>
            AI citations are quickly becoming the preferred way to find services — replacing traditional search engines.
          </p>

          <ul className="landing__facts">
            <li>Nearly 40% of Gen Z now uses AI tools like ChatGPT instead of Google to search for local services and recommendations.</li>
            <li>AI answers pull from a small set of cited sources — if your business isn't structured to be one of them, you're invisible in the new search landscape.</li>
            <li>Unlike traditional SEO where you compete for 10 blue links, AI citations typically recommend only 1–3 businesses per query — making visibility far more winner-take-all.</li>
            <li>Businesses that AI systems can clearly identify, understand, and verify are cited up to 6x more often than those with unstructured or vague web presence.</li>
          </ul>

          <p className="landing__description">
            Zero to GEO analyzes your business website and produces a structured GEO audit —
            showing exactly how prepared you are to be discovered, understood, and cited
            by AI-powered search systems.
          </p>

          <button
            className="btn btn--primary btn--large"
            onClick={() => navigate('/audit/new')}
          >
            Run Your Free GEO Audit
          </button>

          <p className="landing__cta-sub">
            See how prepared your business is to be discovered, understood,
            recommended and cited by AI.
          </p>
        </section>

        <section className="landing__pillars" aria-label="What we analyze">
          <h2 className="landing__section-title">What Zero to GEO analyzes</h2>
          <div className="landing__pillar-grid">
            {PILLARS.map(({ icon, title, description }) => (
              <div key={title} className="landing__pillar-card">
                <span className="landing__pillar-icon" aria-hidden="true">{icon}</span>
                <h3 className="landing__pillar-title">{title}</h3>
                <p className="landing__pillar-desc">{description}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="landing__evidence" aria-label="Our approach">
          <h2 className="landing__section-title">Evidence-based. Not guesswork.</h2>
          <p className="landing__evidence-text">
            Every finding in a Zero to GEO audit is backed by something we actually observed on your website.
            We never claim a business is cited by AI — we tell you what signals make citation more or less likely.
          </p>
        </section>

        <footer className="landing__footer">
          <p>Zero to GEO — AI Visibility &amp; Citation Audit Platform</p>
        </footer>
      </div>
    </main>
  )
}

const PILLARS = [
  {
    icon: '🏢',
    title: 'Business Entity Clarity',
    description: 'Does your website clearly communicate who you are, what you do, where you operate, and who you serve?',
  },
  {
    icon: '📍',
    title: 'Local & NAP Signals',
    description: 'Is your business name, address, phone, and service area clear and consistent?',
  },
  {
    icon: '🔖',
    title: 'Structured Data',
    description: 'Does your site use Schema.org markup to help AI systems identify and classify your business?',
  },
  {
    icon: '💬',
    title: 'Content Answerability',
    description: 'Can AI extract specific, useful facts about your services, prices, process, and qualifications?',
  },
  {
    icon: '⭐',
    title: 'Authority & Trust',
    description: 'Does your site show detectable trust signals — reviews, credentials, years in business, case studies?',
  },
  {
    icon: '🤖',
    title: 'AI Citation Readiness',
    description: 'Is your content specific, factual, extractable, and organized around real customer questions?',
  },
]
