import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createAudit } from '../services/api.js'
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
        // Require at least one dot in the hostname (e.g. example.com)
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
  const [form, setForm] = useState(INITIAL_FORM)
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')

  function handleChange(e) {
    const { name, value } = e.target
    setForm(prev => ({ ...prev, [name]: value }))
    // Clear field error on change
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
            Enter your business details below. We'll analyze your website and tell you
            exactly how prepared you are to be discovered by AI systems.
          </p>

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
        </div>
      </div>
    </main>
  )
}
