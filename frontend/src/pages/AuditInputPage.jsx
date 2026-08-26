import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createAudit, uploadBulkCSV } from '../services/api.js'
import './AuditInputPage.css'

const INITIAL_FORM = {
  businessName: '',
  websiteUrl: '',
  city: '',
  state: '',
  category: '',
}

function validateForm(form) {
  const errors = {}

  if (!form.businessName.trim()) {
    errors.businessName = 'Business name is required.'
  }

  if (!form.websiteUrl.trim()) {
    errors.websiteUrl = 'Website URL is required.'
  } else {
    try {
      const raw = form.websiteUrl.trim()
      const normalized = raw.startsWith('http') ? raw : `https://${raw}`
      const url = new URL(normalized)
      if (!['http:', 'https:'].includes(url.protocol)) {
        errors.websiteUrl = 'Please enter a valid website URL (must be http or https).'
      } else if (!url.hostname.includes('.')) {
        errors.websiteUrl = 'Please enter a valid website URL.'
      }
    } catch {
      errors.websiteUrl = 'Please enter a valid website URL.'
    }
  }

  if (!form.city.trim()) {
    errors.city = 'City is required.'
  }

  if (!form.state.trim()) {
    errors.state = 'State is required.'
  }

  if (!form.category.trim()) {
    errors.category = 'Business category is required.'
  }

  return errors
}

export default function AuditInputPage() {
  const navigate = useNavigate()
  const [mode, setMode] = useState('single') // 'single' or 'bulk'
  const [form, setForm] = useState(INITIAL_FORM)
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')

  // Bulk upload state
  const [csvFile, setCsvFile] = useState(null)
  const [dragOver, setDragOver] = useState(false)

  function handleChange(e) {
    const { name, value } = e.target
    setForm(prev => ({ ...prev, [name]: value }))
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }))
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSubmitError('')

    const validationErrors = validateForm(form)
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors)
      return
    }

    setSubmitting(true)

    try {
      const normalizedUrl = form.websiteUrl.startsWith('http')
        ? form.websiteUrl
        : `https://${form.websiteUrl}`

      const audit = await createAudit({
        business_name: form.businessName.trim(),
        website_url: normalizedUrl.trim(),
        city: form.city.trim(),
        state: form.state.trim(),
        category: form.category.trim(),
      })

      navigate(`/audit/${audit.id}/processing`)
    } catch (err) {
      setSubmitError(err.message || 'Failed to start audit. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleBulkUpload(e) {
    e.preventDefault()
    setSubmitError('')

    if (!csvFile) {
      setSubmitError('Please select a CSV file.')
      return
    }

    setSubmitting(true)

    try {
      const result = await uploadBulkCSV(csvFile)
      navigate(`/bulk/${result.batch_id}`)
    } catch (err) {
      setSubmitError(err.message || 'Failed to upload CSV. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  function handleFileChange(e) {
    const file = e.target.files[0]
    if (file) {
      setCsvFile(file)
      setSubmitError('')
    }
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file && file.name.endsWith('.csv')) {
      setCsvFile(file)
      setSubmitError('')
    } else {
      setSubmitError('Please drop a .csv file.')
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

  return (
    <main className="audit-input">
      <div className="container">
        <header className="audit-input__header">
          <a href="/" className="audit-input__logo">
            Zero to <span>GEO</span>
          </a>
        </header>

        <div className="audit-input__card">
          <h1 className="audit-input__title">Start Your GEO Audit</h1>
          <p className="audit-input__subtitle">
            Audit a single site or upload a CSV to audit multiple sites at once.
          </p>

          {/* Mode Toggle */}
          <div className="audit-input__toggle">
            <button
              type="button"
              className={`toggle-btn${mode === 'single' ? ' toggle-btn--active' : ''}`}
              onClick={() => { setMode('single'); setSubmitError('') }}
            >
              Single Site
            </button>
            <button
              type="button"
              className={`toggle-btn${mode === 'bulk' ? ' toggle-btn--active' : ''}`}
              onClick={() => { setMode('bulk'); setSubmitError('') }}
            >
              Bulk CSV Upload
            </button>
          </div>

          {mode === 'single' ? (
            <form onSubmit={handleSubmit} noValidate className="audit-input__form">
              <div className="form-field">
                <label className="form-field__label" htmlFor="businessName">
                  Business Name <span aria-hidden="true">*</span>
                </label>
                <input
                  id="businessName"
                  name="businessName"
                  type="text"
                  className={`form-field__input${errors.businessName ? ' form-field__input--error' : ''}`}
                  placeholder="e.g. Branson Roofing Co."
                  value={form.businessName}
                  onChange={handleChange}
                  autoComplete="organization"
                  aria-required="true"
                  aria-describedby={errors.businessName ? 'businessName-error' : undefined}
                />
                {errors.businessName && (
                  <span id="businessName-error" className="form-field__error" role="alert">
                    {errors.businessName}
                  </span>
                )}
              </div>

              <div className="form-field">
                <label className="form-field__label" htmlFor="websiteUrl">
                  Website URL <span aria-hidden="true">*</span>
                </label>
                <input
                  id="websiteUrl"
                  name="websiteUrl"
                  type="url"
                  className={`form-field__input${errors.websiteUrl ? ' form-field__input--error' : ''}`}
                  placeholder="e.g. https://bransonroofing.com"
                  value={form.websiteUrl}
                  onChange={handleChange}
                  autoComplete="url"
                  aria-required="true"
                  aria-describedby={errors.websiteUrl ? 'websiteUrl-error' : undefined}
                />
                {errors.websiteUrl && (
                  <span id="websiteUrl-error" className="form-field__error" role="alert">
                    {errors.websiteUrl}
                  </span>
                )}
              </div>

              <div className="form-field-row">
                <div className="form-field">
                  <label className="form-field__label" htmlFor="city">
                    City <span aria-hidden="true">*</span>
                  </label>
                  <input
                    id="city"
                    name="city"
                    type="text"
                    className={`form-field__input${errors.city ? ' form-field__input--error' : ''}`}
                    placeholder="e.g. Branson"
                    value={form.city}
                    onChange={handleChange}
                    autoComplete="address-level2"
                    aria-required="true"
                    aria-describedby={errors.city ? 'city-error' : undefined}
                  />
                  {errors.city && (
                    <span id="city-error" className="form-field__error" role="alert">
                      {errors.city}
                    </span>
                  )}
                </div>

                <div className="form-field">
                  <label className="form-field__label" htmlFor="state">
                    State <span aria-hidden="true">*</span>
                  </label>
                  <input
                    id="state"
                    name="state"
                    type="text"
                    className={`form-field__input${errors.state ? ' form-field__input--error' : ''}`}
                    placeholder="e.g. MO"
                    value={form.state}
                    onChange={handleChange}
                    autoComplete="address-level1"
                    aria-required="true"
                    aria-describedby={errors.state ? 'state-error' : undefined}
                  />
                  {errors.state && (
                    <span id="state-error" className="form-field__error" role="alert">
                      {errors.state}
                    </span>
                  )}
                </div>
              </div>

              <div className="form-field">
                <label className="form-field__label" htmlFor="category">
                  Primary Business Category <span aria-hidden="true">*</span>
                </label>
                <input
                  id="category"
                  name="category"
                  type="text"
                  className={`form-field__input${errors.category ? ' form-field__input--error' : ''}`}
                  placeholder="e.g. Residential Roofing"
                  value={form.category}
                  onChange={handleChange}
                  aria-required="true"
                  aria-describedby={errors.category ? 'category-error' : undefined}
                />
                {errors.category && (
                  <span id="category-error" className="form-field__error" role="alert">
                    {errors.category}
                  </span>
                )}
              </div>

              {submitError && (
                <div className="audit-input__submit-error" role="alert">
                  {submitError}
                </div>
              )}

              <button
                type="submit"
                className="btn btn--primary btn--large audit-input__submit"
                disabled={submitting}
              >
                {submitting ? 'Starting Audit…' : 'Start GEO Audit'}
              </button>
            </form>
          ) : (
            <form onSubmit={handleBulkUpload} className="audit-input__form">
              <div className="bulk-upload__info">
                <h3>CSV Format</h3>
                <p>Your CSV needs these columns (header row required):</p>
                <code className="bulk-upload__columns">
                  business_name, industry, website, address, phone, email, website_host
                </code>
                <a
                  href="/template.csv"
                  download="zerotogeo_template.csv"
                  className="btn btn--secondary bulk-upload__download-template"
                  onClick={(e) => {
                    e.preventDefault()
                    const csvContent = 'business_name,industry,website,address,phone,email,website_host\n'
                    const blob = new Blob([csvContent], { type: 'text/csv' })
                    const url = URL.createObjectURL(blob)
                    const a = document.createElement('a')
                    a.href = url
                    a.download = 'zerotogeo_template.csv'
                    a.click()
                    URL.revokeObjectURL(url)
                  }}
                >
                  ⬇ Download CSV Template
                </a>
                <p className="bulk-upload__copy-label">Or copy this and give it to your AI:</p>
                <pre className="bulk-upload__example">
{`business_name,industry,website,address,phone,email,website_host
Branson Roofing Co,Residential Roofing,bransonroofing.com,"123 Main St, Branson MO 65616",417-555-1234,info@bransonroofing.com,GoDaddy
Smith Plumbing,Plumbing,smithplumbing.com,"456 Oak Ave, Springfield MO 65801",417-555-5678,contact@smithplumbing.com,Wix`}
                </pre>
              </div>

              <div
                className={`bulk-upload__dropzone${dragOver ? ' bulk-upload__dropzone--active' : ''}${csvFile ? ' bulk-upload__dropzone--has-file' : ''}`}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
              >
                {csvFile ? (
                  <div className="bulk-upload__file-info">
                    <span className="bulk-upload__file-icon">📄</span>
                    <span className="bulk-upload__file-name">{csvFile.name}</span>
                    <button
                      type="button"
                      className="bulk-upload__remove-file"
                      onClick={() => setCsvFile(null)}
                      aria-label="Remove file"
                    >
                      ✕
                    </button>
                  </div>
                ) : (
                  <>
                    <span className="bulk-upload__drop-icon">📁</span>
                    <p>Drag & drop your CSV here</p>
                    <p className="bulk-upload__or">or</p>
                    <label className="btn btn--secondary bulk-upload__browse-btn">
                      Browse Files
                      <input
                        type="file"
                        accept=".csv"
                        onChange={handleFileChange}
                        className="sr-only"
                      />
                    </label>
                  </>
                )}
              </div>

              {submitError && (
                <div className="audit-input__submit-error" role="alert">
                  {submitError}
                </div>
              )}

              <button
                type="submit"
                className="btn btn--primary btn--large audit-input__submit"
                disabled={submitting || !csvFile}
              >
                {submitting ? 'Uploading & Starting Audits…' : 'Upload & Start All Audits'}
              </button>
            </form>
          )}
        </div>
      </div>
    </main>
  )
}
