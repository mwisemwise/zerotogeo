import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { getBusinesses, importBusinesses, launchAudits } from '../services/api.js'
import './BusinessesPage.css'

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

function parseCSV(text) {
  const lines = text.trim().split('\n')
  if (lines.length < 2) return []

  const headers = lines[0].split(',').map(h => h.trim().toLowerCase())
  const rows = []

  for (let i = 1; i < lines.length; i++) {
    const values = []
    let current = ''
    let inQuotes = false

    for (const char of lines[i]) {
      if (char === '"') {
        inQuotes = !inQuotes
      } else if (char === ',' && !inQuotes) {
        values.push(current.trim())
        current = ''
      } else {
        current += char
      }
    }
    values.push(current.trim())

    if (values.length >= headers.length) {
      const row = {}
      headers.forEach((h, idx) => { row[h] = values[idx] || '' })
      rows.push(row)
    }
  }

  return rows
}

function csvToBusinesses(rows) {
  return rows
    .filter(row => row.business_name && row.website)
    .map(row => ({
      name: row.business_name,
      website: row.website.startsWith('http') ? row.website : `https://${row.website}`,
      city: (row.address || '').split(',').slice(-2, -1)[0]?.trim() || '',
      state: (row.address || '').match(/([A-Z]{2})\s*\d{5}/)?.[1] || '',
      category: row.industry || '',
    }))
}

export default function BusinessesPage() {
  const navigate = useNavigate()
  const [businesses, setBusinesses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState(new Set())
  const [launching, setLaunching] = useState(false)
  const [importError, setImportError] = useState('')
  const [importSuccess, setImportSuccess] = useState('')
  const [csvFile, setCsvFile] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [importing, setImporting] = useState(false)
  const searchTimeout = useRef(null)
  const fileInputRef = useRef(null)

  const fetchBusinesses = useCallback(async (searchTerm) => {
    try {
      setError('')
      const data = await getBusinesses(searchTerm || '')
      setBusinesses(data)
    } catch (err) {
      setError(err.message || 'Failed to load businesses.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchBusinesses('')
  }, [fetchBusinesses])

  function handleSearchChange(e) {
    const value = e.target.value
    setSearch(value)

    if (searchTimeout.current) clearTimeout(searchTimeout.current)
    searchTimeout.current = setTimeout(() => {
      fetchBusinesses(value)
    }, 300)
  }

  function handleSelectAll(e) {
    if (e.target.checked) {
      setSelected(new Set(businesses.map(b => b.id)))
    } else {
      setSelected(new Set())
    }
  }

  function handleSelectOne(id) {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  async function handleLaunchAudits() {
    if (selected.size === 0) return
    setLaunching(true)
    setError('')

    try {
      const result = await launchAudits(Array.from(selected))
      navigate(`/bulk/${result.batch_id}`)
    } catch (err) {
      setError(err.message || 'Failed to launch audits.')
      setLaunching(false)
    }
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file && file.name.endsWith('.csv')) {
      setCsvFile(file)
      setImportError('')
    } else {
      setImportError('Please drop a .csv file.')
    }
  }

  function handleDragOver(e) {
    e.preventDefault()
    setDragOver(true)
  }

  function handleDragLeave(e) {
    e.preventDefault()
    setDragOver(false)
  }

  function handleFileChange(e) {
    const file = e.target.files[0]
    if (file) {
      setCsvFile(file)
      setImportError('')
    }
  }

  async function handleImport() {
    if (!csvFile) return
    setImporting(true)
    setImportError('')
    setImportSuccess('')

    try {
      const text = await csvFile.text()
      const rows = parseCSV(text)
      if (rows.length === 0) {
        setImportError('No valid rows found in CSV.')
        setImporting(false)
        return
      }

      const businessPayload = csvToBusinesses(rows)
      if (businessPayload.length === 0) {
        setImportError('No rows with required fields (business_name, website) found.')
        setImporting(false)
        return
      }

      const result = await importBusinesses(businessPayload)
      setImportSuccess(`Imported ${result.imported} business${result.imported !== 1 ? 'es' : ''}${result.duplicates > 0 ? ` (${result.duplicates} duplicate${result.duplicates !== 1 ? 's' : ''} skipped)` : ''}.`)
      setCsvFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      // Refresh the list
      fetchBusinesses(search)
    } catch (err) {
      setImportError(err.message || 'Failed to import businesses.')
    } finally {
      setImporting(false)
    }
  }

  const allSelected = businesses.length > 0 && selected.size === businesses.length
  const someSelected = selected.size > 0 && selected.size < businesses.length

  return (
    <main className="businesses-page">
      <div className="container">
        <header className="businesses-page__header">
          <a href="/" className="businesses-page__logo">
            Zero to <span>GEO</span>
          </a>
          <nav className="businesses-page__nav" aria-label="Main navigation">
            <Link to="/audit/new" className="btn btn--secondary btn--small">New Audit</Link>
          </nav>
        </header>

        <div className="businesses-page__card">
          <div className="businesses-page__title-row">
            <h1 className="businesses-page__title">Businesses &amp; Prospects</h1>
            <button
              className="btn btn--primary btn--large businesses-page__launch-btn"
              disabled={selected.size === 0 || launching}
              onClick={handleLaunchAudits}
              aria-label={`Launch audit for ${selected.size} selected businesses`}
            >
              {launching
                ? 'Launching…'
                : `Launch Audit${selected.size > 0 ? ` (${selected.size} selected)` : ''}`}
            </button>
          </div>

          {/* Search and Import */}
          <div className="businesses-page__toolbar">
            <div className="businesses-page__search">
              <label htmlFor="business-search" className="sr-only">Search businesses</label>
              <input
                id="business-search"
                type="search"
                className="form-field__input businesses-page__search-input"
                placeholder="Search by name, city, state, or category…"
                value={search}
                onChange={handleSearchChange}
                aria-label="Search businesses"
              />
            </div>
          </div>

          {/* CSV Import Section */}
          <details className="businesses-page__import-section">
            <summary className="businesses-page__import-toggle">
              📁 Import Prospects from CSV
            </summary>
            <div className="businesses-page__import-content">
              <div className="bulk-upload__info">
                <p>Import businesses as prospects without running audits. CSV format:</p>
                <code className="bulk-upload__columns">
                  business_name, industry, website, address, phone, email, website_host
                </code>
              </div>

              <div
                className={`bulk-upload__dropzone${dragOver ? ' bulk-upload__dropzone--active' : ''}${csvFile ? ' bulk-upload__dropzone--has-file' : ''}`}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                role="button"
                tabIndex={0}
                aria-label="Drop CSV file here or click to browse"
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click() }}
              >
                {csvFile ? (
                  <div className="bulk-upload__file-info">
                    <span className="bulk-upload__file-icon">📄</span>
                    <span className="bulk-upload__file-name">{csvFile.name}</span>
                    <button
                      type="button"
                      className="bulk-upload__remove-file"
                      onClick={() => { setCsvFile(null); if (fileInputRef.current) fileInputRef.current.value = '' }}
                      aria-label="Remove file"
                    >
                      ✕
                    </button>
                  </div>
                ) : (
                  <>
                    <span className="bulk-upload__drop-icon">📁</span>
                    <p>Drag &amp; drop your CSV here</p>
                    <p className="bulk-upload__or">or</p>
                    <label className="btn btn--secondary bulk-upload__browse-btn">
                      Browse Files
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept=".csv"
                        onChange={handleFileChange}
                        className="sr-only"
                      />
                    </label>
                  </>
                )}
              </div>

              {importError && (
                <div className="businesses-page__import-error" role="alert">{importError}</div>
              )}
              {importSuccess && (
                <div className="businesses-page__import-success" role="status">{importSuccess}</div>
              )}

              <button
                type="button"
                className="btn btn--primary businesses-page__import-btn"
                disabled={!csvFile || importing}
                onClick={handleImport}
              >
                {importing ? 'Importing…' : 'Import as Prospects'}
              </button>
            </div>
          </details>

          {/* Error/Loading states */}
          {error && (
            <div className="businesses-page__error" role="alert">{error}</div>
          )}

          {loading ? (
            <div className="businesses-page__loading">Loading businesses…</div>
          ) : businesses.length === 0 ? (
            <div className="businesses-page__empty">
              <p>No businesses found.{search ? ' Try a different search.' : ' Import some prospects to get started.'}</p>
            </div>
          ) : (
            <div className="businesses-page__table-wrapper">
              <table className="businesses-page__table" aria-label="Businesses table">
                <thead>
                  <tr>
                    <th className="businesses-page__th-check">
                      <input
                        type="checkbox"
                        checked={allSelected}
                        ref={(el) => { if (el) el.indeterminate = someSelected }}
                        onChange={handleSelectAll}
                        aria-label="Select all businesses"
                      />
                    </th>
                    <th>Business Name</th>
                    <th>Website</th>
                    <th>City/State</th>
                    <th>Category</th>
                    <th>Latest Score</th>
                    <th>Latest Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {businesses.map(business => (
                    <tr key={business.id} className={selected.has(business.id) ? 'businesses-page__row--selected' : ''}>
                      <td>
                        <input
                          type="checkbox"
                          checked={selected.has(business.id)}
                          onChange={() => handleSelectOne(business.id)}
                          aria-label={`Select ${business.name}`}
                        />
                      </td>
                      <td className="businesses-page__name-cell">
                        <Link to={`/businesses/${business.id}`} className="businesses-page__name-link">
                          {business.name}
                        </Link>
                      </td>
                      <td className="businesses-page__url-cell">
                        <a href={business.website} target="_blank" rel="noopener noreferrer">
                          {(business.website || '').replace(/^https?:\/\//, '')}
                        </a>
                      </td>
                      <td>{[business.city, business.state].filter(Boolean).join(', ') || '—'}</td>
                      <td>{business.category || '—'}</td>
                      <td className="businesses-page__score-cell">
                        {business.latest_audit?.overall_score != null ? Math.round(business.latest_audit.overall_score) : '—'}
                      </td>
                      <td>
                        {business.latest_audit?.status ? (
                          <span className={`status-badge ${STATUS_COLORS[business.latest_audit.status] || ''}`}>
                            {STATUS_LABELS[business.latest_audit.status] || business.latest_audit.status}
                          </span>
                        ) : (
                          <span className="status-badge status--pending">No Audit</span>
                        )}
                      </td>
                      <td>
                        <Link
                          to={`/businesses/${business.id}`}
                          className="btn btn--small"
                        >
                          View
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </main>
  )
}
