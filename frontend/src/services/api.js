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
// Bulk CSV Upload
// ---------------------------------------------------------------------------

/**
 * Upload a CSV file for bulk audit creation.
 * Returns { batch_id, total, created_audits, skipped_rows }
 */
export function uploadBulkCSV(file) {
  const formData = new FormData()
  formData.append('file', file)

  return fetch(`${API_BASE}/bulk/upload`, {
    method: 'POST',
    body: formData,
  }).then(async (res) => {
    if (res.ok) return res.json()
    let detail = `Request failed (${res.status})`
    try {
      const body = await res.json()
      detail = body.detail?.message || body.detail || detail
    } catch {}
    throw new ApiError(detail, res.status)
  })
}

/**
 * Get the status of a bulk batch.
 * Returns { batch_id, status, total, completed, failed, in_progress, audits }
 */
export function getBatchStatus(batchId) {
  return request(`/bulk/${batchId}`)
}

// ---------------------------------------------------------------------------
// Businesses / Prospects
// ---------------------------------------------------------------------------

/**
 * Get all businesses with latest audit info.
 * Supports optional search filter across name/city/state/category.
 * Returns array of business objects.
 */
export function getBusinesses(search) {
  const params = search ? `?search=${encodeURIComponent(search)}` : ''
  return request(`/businesses${params}`)
}

/**
 * Get a single business by ID with full audit history.
 * Returns { id, name, website_url, city, state, category, audits: [...] }
 */
export function getBusiness(id) {
  return request(`/businesses/${id}`)
}

/**
 * Import businesses from JSON array (dedup by URL).
 * Returns { imported, duplicates, businesses }
 */
export function importBusinesses(businesses) {
  return request('/businesses/import', {
    method: 'POST',
    body: JSON.stringify({ businesses }),
  })
}

/**
 * Launch audits for selected business IDs.
 * Returns { batch_id, total, audits }
 */
export function launchAudits(businessIds) {
  return request('/businesses/launch-audits', {
    method: 'POST',
    body: JSON.stringify({ business_ids: businessIds }),
  })
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export function getHealth() {
  return request('/health')
}

// ---------------------------------------------------------------------------
// Customer Report (Five C's customer-facing audit)
// ---------------------------------------------------------------------------

/**
 * Get the full customer-facing audit report.
 * Returns position, Five C's findings, competitive comparison, fixes.
 */
export function getCustomerReport(auditId) {
  return request(`/customer-report/${auditId}`)
}

/**
 * Update the validation status of a customer finding.
 * status: 'open' | 'fixed' | 'verified'
 */
export function updateFindingStatus(findingId, status) {
  return request(`/customer-report/findings/${findingId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })
}
