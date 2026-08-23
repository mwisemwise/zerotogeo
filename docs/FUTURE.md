# Zero to GEO — Future Features

This file captures good ideas that are **out of scope for the MVP**.

When a feature idea is discovered during development that falls outside the approved MVP spec, it is recorded here instead of built. This enforces MVP discipline.

Nothing in this file is approved for development. These are inputs to future planning only.

---

## Format

```
## FUTURE-NNN — Title
Discovered: YYYY-MM-DD
Context: What triggered this idea.
Description: What it would do.
Value: Why it might be worth building.
Dependency: What MVP capabilities it builds on.
```

---

## FUTURE-001 — User Accounts and Audit History

Discovered: 2026-08-11
Context: MVP spec explicitly excludes user accounts.
Description: Allow users to create accounts, save audit history, track score improvements over time, and re-run audits to measure progress.
Value: Enables recurring use, long-term value tracking, and subscription business model.
Dependency: Requires MVP audit pipeline to work reliably first.

---

## FUTURE-002 — LLM-Enhanced Finding Explanations

Discovered: 2026-08-11
Context: MVP uses deterministic scoring only. LLM dependency explicitly excluded.
Description: Use an LLM (OpenAI, Anthropic, or self-hosted) to generate more nuanced, natural-language explanations of findings and recommendations.
Value: Better reading experience, more specific advice, ability to handle edge cases that rule-based analysis misses.
Dependency: Core deterministic scoring engine must be solid first. LLM should enhance, not replace.

---

## FUTURE-003 — Competitor Intelligence

Discovered: 2026-08-11
Context: MVP is single-business audit only.
Description: Crawl and score competitors in the same category/location, show comparative GEO scores, identify gaps and opportunities.
Value: Helps businesses understand where they stand relative to alternatives.
Dependency: Core audit pipeline. Requires careful rate limiting and robots.txt handling at scale.

---

## FUTURE-004 — Scheduled Re-Audits and Progress Tracking

Discovered: 2026-08-11
Context: MVP is a single on-demand audit.
Description: Allow users to schedule periodic re-audits (weekly, monthly) and track GEO score improvement over time with a trend chart.
Value: Transforms one-time tool into ongoing monitoring service.
Dependency: User accounts (FUTURE-001).

---

## FUTURE-005 — White-Label Reports

Discovered: 2026-08-11
Context: MVP spec explicitly excludes white-label.
Description: Allow agencies to brand reports with their logo, company name, and colors. Export to PDF.
Value: Enables B2B reseller channel.
Dependency: PDF export capability, agency account type, report template system.

---

## FUTURE-006 — Agency / Multi-Client Dashboard

Discovered: 2026-08-11
Context: MVP is single-business, no accounts.
Description: Agency accounts can manage multiple client businesses, view all audits in one dashboard, track aggregate performance.
Value: Primary monetization vector for agency market.
Dependency: User accounts, white-label reports.

---

## FUTURE-007 — Playwright / JS-Rendered Page Support

Discovered: 2026-08-11
Context: MVP crawler uses httpx (no JavaScript execution).
Description: Optional browser-based crawl mode using Playwright for websites that render critical content via JavaScript (React SPAs, etc.).
Value: More complete analysis for modern JS-heavy business websites.
Dependency: Core crawler must be stable. Playwright adds significant infrastructure complexity.

---

## FUTURE-008 — AI Citation Testing

Discovered: 2026-08-11
Context: MVP does not test actual AI citations.
Description: Submit test queries to LLM APIs (with consent) to see whether a business is actually mentioned or cited. Record results with timestamp.
Value: Closes the loop between "citation readiness" and actual citation behavior.
Dependency: LLM API integration, user consent flow, significant cost considerations.

---

## FUTURE-009 — Email Report Delivery

Discovered: 2026-08-11
Context: MVP spec explicitly excludes email automation.
Description: After audit completes, offer to email a PDF or link to the report.
Value: Lead capture, report sharing, product stickiness.
Dependency: Email service integration (SendGrid, etc.), user auth or email collection.

---

## FUTURE-010 — Billing and Subscription

Discovered: 2026-08-11
Context: MVP spec explicitly excludes Stripe/billing.
Description: Freemium model: free basic audit, paid tier for full report, recommendations, and scheduled monitoring.
Value: Primary revenue mechanism.
Dependency: User accounts, email, product-market fit validation.

---

## FUTURE-011 — Schema.org Validation API Integration

Discovered: 2026-08-11
Context: MVP checks for schema presence via HTML parsing.
Description: Submit detected schema to Google's Rich Results Test API or Schema.org validator for authoritative validity checking.
Value: More accurate structured data assessment.
Dependency: External API integration, rate limiting.

---

## FUTURE-012 — Mobile App

Discovered: 2026-08-11
Context: MVP spec explicitly excludes mobile app.
Description: React Native or PWA version for on-the-go audit requests.
Value: Convenience, field sales use case (run audit while meeting with prospect).
Dependency: Stable API, user accounts.

---

## FUTURE-013 — Multi-Page Crawling

Discovered: 2026-08-11
Context: MVP does basic single/limited-page crawl.
Description: Full site crawl with configurable depth, robots.txt compliance, sitemap parsing, and per-page analysis.
Value: More complete analysis for larger sites.
Dependency: Robust crawler, rate limiting, crawl budget management.

---

## FUTURE-014 — Question Coverage Analysis

Discovered: 2026-08-11
Context: MVP identifies general content gaps.
Description: Generate the actual questions potential customers would ask an AI, then check whether the business website provides answers to each.
Value: Extremely actionable — shows exactly which customer questions are unanswered.
Dependency: LLM integration for question generation, or curated question bank by category.

---
