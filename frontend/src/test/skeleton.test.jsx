/**
 * Phase 1 frontend skeleton tests.
 *
 * Verifies:
 * - LandingPage renders without crashing
 * - AuditInputPage renders the form
 * - AuditInputPage validates required fields
 * - AuditInputPage validates URL format
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import LandingPage from '../pages/LandingPage.jsx'
import AuditInputPage from '../pages/AuditInputPage.jsx'

function renderWithRouter(component, path = '/') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      {component}
    </MemoryRouter>
  )
}

describe('LandingPage', () => {
  it('renders without crashing', () => {
    renderWithRouter(<LandingPage />)
    expect(document.body).toBeTruthy()
  })

  it('shows the main headline', () => {
    renderWithRouter(<LandingPage />)
    expect(screen.getByRole('heading', { level: 1 })).toBeTruthy()
  })

  it('shows a CTA button to start an audit', () => {
    renderWithRouter(<LandingPage />)
    const cta = screen.getByText(/Run Your Free GEO Audit/i)
    expect(cta).toBeTruthy()
  })

  it('shows the six GEO pillars', () => {
    renderWithRouter(<LandingPage />)
    expect(screen.getByText(/Business Entity Clarity/i)).toBeTruthy()
    expect(screen.getByText(/AI Citation Readiness/i)).toBeTruthy()
  })
})

describe('AuditInputPage', () => {
  it('renders the form', () => {
    renderWithRouter(<AuditInputPage />)
    expect(screen.getByRole('heading', { level: 1 })).toBeTruthy()
  })

  it('shows all required form fields', () => {
    renderWithRouter(<AuditInputPage />)
    expect(screen.getByLabelText(/Business Name/i)).toBeTruthy()
    expect(screen.getByLabelText(/Website URL/i)).toBeTruthy()
    expect(screen.getByLabelText(/City/i)).toBeTruthy()
    expect(screen.getByLabelText(/State/i)).toBeTruthy()
    expect(screen.getByLabelText(/Primary Business Category/i)).toBeTruthy()
  })

  it('shows the submit button', () => {
    renderWithRouter(<AuditInputPage />)
    expect(screen.getByText(/Start GEO Audit/i)).toBeTruthy()
  })

  it('shows validation errors when submitted empty', async () => {
    renderWithRouter(<AuditInputPage />)
    const submitBtn = screen.getByText(/Start GEO Audit/i)
    fireEvent.click(submitBtn)
    expect(screen.getByText(/Business name is required/i)).toBeTruthy()
    expect(screen.getByText(/Website URL is required/i)).toBeTruthy()
    expect(screen.getByText(/City is required/i)).toBeTruthy()
    expect(screen.getByText(/State is required/i)).toBeTruthy()
  })

  it('shows URL validation error for invalid URL', async () => {
    renderWithRouter(<AuditInputPage />)
    const urlInput = screen.getByLabelText(/Website URL/i)
    // A URL without a dot in the hostname is rejected by validation
    fireEvent.change(urlInput, { target: { value: 'https://notavalidhostname' } })
    const submitBtn = screen.getByText(/Start GEO Audit/i)
    fireEvent.click(submitBtn)
    expect(screen.getByText(/valid website URL/i)).toBeTruthy()
  })

  it('accepts valid URL input without URL error', async () => {
    renderWithRouter(<AuditInputPage />)
    const urlInput = screen.getByLabelText(/Website URL/i)
    fireEvent.change(urlInput, { target: { value: 'https://example.com' } })
    const submitBtn = screen.getByText(/Start GEO Audit/i)
    fireEvent.click(submitBtn)
    // URL error should not appear for a valid URL
    expect(screen.queryByText(/valid website URL/i)).toBeNull()
  })
})
