/**
 * Zero to GEO — API service client.
 *
 * Single place for all backend communication.
 * Vite dev proxy forwards /api/* to http://localhost:8000 (see vite.config.js).
 *
 * All functions throw an ApiError on non-2xx responses so callers
 * can catch and display the message directly.
 */

const API_BASE = '/api'

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })

  if (res.ok) {
    return res.json()
  }

  // Try to extract a meaningful error message from the response body
  let detail = `Request failed (${res.status})`
  try {
    const body = await res.json()
    detail = body.detail || body.message || detail
  } catch {
    // response wasn't JSON
  }

  throw new ApiError(detail, res.status)
}

// ---------------------------------------------------------------------------
// Audits
// ---------------------------------------------------------------------------

/**
 * Create a new GEO audit.
 * Returns the audit object with id and initial status='pending'.
 */
export function createAudit(payload) {
  return request('/audits', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

/**
 * Get the current status of an audit (for polling).
 * Returns { id, status, overall_score, error_message, business, ... }
 */
export function getAuditStatus(auditId) {
  return request(`/audits/${auditId}`)
}

/**
 * Get the full GEO report for a completed audit.
 * Only call this when status === 'complete'.
 */
export function getAuditReport(auditId) {
  return request(`/audits/${auditId}/report`)
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export function getHealth() {
  return request('/health')
}
