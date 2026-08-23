import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <main style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: '2rem' }}>
      <div>
        <h1 style={{ fontSize: '4rem', fontWeight: 800, color: 'var(--color-accent)', marginBottom: '0.5rem' }}>404</h1>
        <p style={{ color: 'var(--color-text-muted)', marginBottom: '2rem' }}>Page not found.</p>
        <Link to="/" className="btn btn--primary">Go Home</Link>
      </div>
    </main>
  )
}
