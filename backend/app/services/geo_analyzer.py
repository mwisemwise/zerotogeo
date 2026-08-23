"""
Zero to GEO — Six-pillar GEO analyzer (Phase 6).

Each pillar is scored 0–100 using deterministic rules applied to ExtractedData.
Every score is derived from something the system actually observed.

Pillars:
  1. entity_clarity       — Business Entity Clarity
  2. local_signals        — Local / NAP Signals
  3. structured_data      — Structured Data
  4. content              — Content / Answerability
  5. authority            — Authority / Trust
  6. citation_readiness   — AI Citation Readiness

Returns a dict of pillar_key → {"score": float, "summary": str}
"""

from app.services.extractor import ExtractedData


def analyze(extracted: ExtractedData, business) -> dict:
    """
    Run all six pillars and return scores + summaries.
    business is the SQLAlchemy Business ORM object.
    """
    return {
        "entity_clarity": _pillar_entity_clarity(extracted, business),
        "local_signals": _pillar_local_signals(extracted, business),
        "structured_data": _pillar_structured_data(extracted),
        "content": _pillar_content(extracted, business),
        "authority": _pillar_authority(extracted),
        "citation_readiness": _pillar_citation_readiness(extracted, business),
    }


# ---------------------------------------------------------------------------
# PILLAR 1 — Business Entity Clarity
# ---------------------------------------------------------------------------

def _pillar_entity_clarity(extracted: ExtractedData, business) -> dict:
    """
    Does the website clearly communicate who the business is,
    what it does, where it operates, and who it serves?
    """
    score = 0
    signals = []

    # Page title present and meaningful
    if extracted.title and len(extracted.title) > 10:
        score += 15
        signals.append(f"Page title present: '{extracted.title[:80]}'")
    else:
        signals.append("Page title is missing or very short.")

    # Business name appears in title or H1
    name_lower = business.name.lower()
    title_lower = extracted.title.lower()
    h1_text = " ".join(extracted.h1_tags).lower()
    if name_lower in title_lower or name_lower in h1_text:
        score += 15
        signals.append("Business name appears in title or H1.")
    else:
        # Check for partial name match
        name_words = [w for w in name_lower.split() if len(w) > 3]
        if any(w in title_lower or w in h1_text for w in name_words):
            score += 8
            signals.append("Business name partially matches title or H1.")
        else:
            signals.append("Business name not clearly identified in title or H1.")

    # H1 tag present and descriptive
    if extracted.h1_tags and len(extracted.h1_tags[0]) > 10:
        score += 15
        signals.append(f"H1 present: '{extracted.h1_tags[0][:80]}'")
    else:
        signals.append("No descriptive H1 tag found.")

    # Meta description present
    if extracted.meta_description and len(extracted.meta_description) > 20:
        score += 15
        signals.append("Meta description present.")
    else:
        signals.append("Meta description missing or too short.")

    # Service/category mentioned in visible headings
    category_lower = business.category.lower()
    all_headings_lower = " ".join(extracted.h1_tags + extracted.h2_tags + extracted.h3_tags).lower()
    category_words = [w for w in category_lower.split() if len(w) > 3]
    if any(w in all_headings_lower for w in category_words):
        score += 20
        signals.append(f"Business category '{business.category}' referenced in headings.")
    else:
        signals.append(f"Business category '{business.category}' not clearly found in headings.")

    # Word count — thin pages score lower
    if extracted.word_count >= 300:
        score += 10
        signals.append(f"Page has substantial content ({extracted.word_count} words).")
    elif extracted.word_count >= 100:
        score += 5
        signals.append(f"Page has some content ({extracted.word_count} words).")
    else:
        signals.append(f"Page has very little content ({extracted.word_count} words).")

    # Contact information present
    if extracted.has_phone or extracted.has_email:
        score += 10
        signals.append("Contact information (phone or email) present on page.")
    else:
        signals.append("No contact information (phone or email) detected.")

    score = min(100, score)
    summary = f"Entity Clarity score: {score}/100. " + " ".join(signals[:4])
    return {"score": score, "summary": summary}


# ---------------------------------------------------------------------------
# PILLAR 2 — Local / NAP Signals
# ---------------------------------------------------------------------------

def _pillar_local_signals(extracted: ExtractedData, business) -> dict:
    """
    Is the business name, address, phone, location, and service area clear?
    """
    score = 0
    signals = []

    city_lower = business.city.lower()
    state_lower = business.state.lower()
    body_lower = extracted.body_text.lower()
    heading_text = " ".join(extracted.h1_tags + extracted.h2_tags + extracted.h3_tags).lower()
    all_text = body_lower + " " + heading_text

    # Phone present
    if extracted.has_phone:
        score += 25
        signals.append(f"Phone number found: {extracted.phone_numbers[0] if extracted.phone_numbers else 'detected'}.")
    else:
        signals.append("No phone number detected on the page.")

    # Physical address detected
    if extracted.has_address:
        score += 20
        signals.append(f"Street address detected: '{extracted.addresses[0][:100]}'.")
    else:
        signals.append("No street address detected on page.")

    # City name in content
    if city_lower in all_text:
        score += 20
        signals.append(f"City name '{business.city}' found in page content.")
    else:
        signals.append(f"City name '{business.city}' not found in page content.")

    # State in content
    if state_lower in all_text or business.state.upper() in extracted.body_text:
        score += 10
        signals.append(f"State '{business.state}' referenced on page.")
    else:
        signals.append(f"State '{business.state}' not found on page.")

    # Service area language
    if extracted.has_location_content:
        score += 15
        signals.append("Service area or location language detected.")
    else:
        signals.append("No service area or local coverage language found.")

    # LocalBusiness schema includes address
    if extracted.has_local_business_schema:
        for schema in extracted.schema_data:
            if schema.get("address"):
                score += 10
                signals.append("Address present in LocalBusiness schema.")
                break
            elif schema.get("areaServed") or schema.get("serviceArea"):
                score += 8
                signals.append("areaServed present in schema.")
                break
        else:
            score += 5
            signals.append("LocalBusiness schema present but address not found in schema.")

    score = min(100, score)
    summary = f"Local/NAP score: {score}/100. " + " ".join(signals[:4])
    return {"score": score, "summary": summary}


# ---------------------------------------------------------------------------
# PILLAR 3 — Structured Data
# ---------------------------------------------------------------------------

def _pillar_structured_data(extracted: ExtractedData) -> dict:
    """
    Does the site use Schema.org markup correctly?
    """
    score = 0
    signals = []

    if not extracted.schema_types:
        signals.append("No Schema.org markup (JSON-LD) detected on this page.")
        return {
            "score": 0,
            "summary": f"Structured Data score: 0/100. {signals[0]}"
        }

    unique_types = sorted(set(extracted.schema_types))
    signals.append(f"Schema types found: {', '.join(unique_types)}.")

    # LocalBusiness schema
    if extracted.has_local_business_schema:
        score += 30
        signals.append("LocalBusiness (or subtype) schema present.")

        # Check completeness of LocalBusiness schema
        # Find the schema object — could be "LocalBusiness", "Plumber", "RoofingContractor", etc.
        lb_schema = None
        for s in extracted.schema_data:
            if not isinstance(s, dict):
                continue
            s_type = s.get("@type", "")
            if isinstance(s_type, str):
                t_lower = s_type.lower()
                # Match any known local business type
                if ("business" in t_lower or "plumb" in t_lower or
                    "contractor" in t_lower or "electrician" in t_lower or
                    "service" in t_lower or "restaurant" in t_lower or
                    "store" in t_lower or "repair" in t_lower or
                    "salon" in t_lower or "dentist" in t_lower or
                    "physician" in t_lower or "lawyer" in t_lower or
                    "hotel" in t_lower or t_lower == "localbusiness"):
                    lb_schema = s
                    break

        if lb_schema:
            completeness_points = 0
            completeness_total = 5
            if lb_schema.get("name"):
                completeness_points += 1
                score += 3
            if lb_schema.get("address"):
                completeness_points += 1
                score += 3
            if lb_schema.get("telephone"):
                completeness_points += 1
                score += 3
            if lb_schema.get("url"):
                completeness_points += 1
                score += 3
            if lb_schema.get("areaServed") or lb_schema.get("serviceArea"):
                completeness_points += 1
                score += 8
                signals.append("areaServed defined in schema (strong local signal).")
            signals.append(f"LocalBusiness schema completeness: {completeness_points}/{completeness_total} key fields present.")
    else:
        signals.append("LocalBusiness schema not found (important for local AI visibility).")

    # Organization schema
    if extracted.has_organization_schema:
        score += 10
        signals.append("Organization schema present.")

    # Service schema
    if extracted.has_service_schema:
        score += 10
        signals.append("Service schema present.")

    # FAQ schema
    if extracted.has_faq_schema:
        score += 15
        signals.append("FAQPage schema present.")

    # Website schema
    if extracted.has_website_schema:
        score += 10
        signals.append("WebSite schema present.")

    # Breadcrumb schema
    if extracted.has_breadcrumb_schema:
        score += 5
        signals.append("BreadcrumbList schema present.")

    score = min(100, score)
    summary = f"Structured Data score: {score}/100. " + " ".join(signals[:4])
    return {"score": score, "summary": summary}


# ---------------------------------------------------------------------------
# PILLAR 4 — Content / Answerability
# ---------------------------------------------------------------------------

def _pillar_content(extracted: ExtractedData, business) -> dict:
    """
    Can AI systems extract specific, useful facts from this site?
    """
    score = 0
    signals = []

    # Service descriptions
    if extracted.has_service_descriptions:
        score += 20
        signals.append("Service descriptions found in page headings.")
    else:
        signals.append("No clear service descriptions found in headings.")

    # Location/service area content
    if extracted.has_location_content:
        score += 15
        signals.append("Location/service area information present.")
    else:
        signals.append("No service area information found.")

    # FAQ content
    if extracted.has_faq_content or extracted.has_faq_schema:
        score += 15
        signals.append("FAQ content detected (improves answerability for AI queries).")
    else:
        signals.append("No FAQ content found.")

    # Pricing/rates information
    if extracted.has_pricing_content:
        score += 10
        signals.append("Pricing or rate information found.")
    else:
        signals.append("No pricing or rate information detected.")

    # Process / how-it-works content
    if extracted.has_process_content:
        score += 10
        signals.append("Process or 'how it works' content found.")
    else:
        signals.append("No process description found.")

    # Credentials
    if extracted.has_credentials:
        score += 10
        signals.append("License/certification/credentials mentioned.")
    else:
        signals.append("No credential or licensing information found.")

    # Word count
    if extracted.word_count >= 600:
        score += 10
        signals.append(f"Substantial page content ({extracted.word_count} words).")
    elif extracted.word_count >= 300:
        score += 5
        signals.append(f"Moderate page content ({extracted.word_count} words).")
    else:
        signals.append(f"Thin page content ({extracted.word_count} words).")

    # Business category appears in content
    category_lower = business.category.lower()
    category_words = [w for w in category_lower.split() if len(w) > 3]
    if any(w in extracted.body_text.lower() for w in category_words):
        score += 10
        signals.append(f"Service category '{business.category}' referenced in page content.")
    else:
        signals.append(f"Service category '{business.category}' not clearly referenced in content.")

    score = min(100, score)
    summary = f"Content/Answerability score: {score}/100. " + " ".join(signals[:4])
    return {"score": score, "summary": summary}


# ---------------------------------------------------------------------------
# PILLAR 5 — Authority / Trust
# ---------------------------------------------------------------------------

def _pillar_authority(extracted: ExtractedData) -> dict:
    """
    Does the site show detectable trust and authority signals?
    Only awards points for signals actually detected.
    """
    score = 0
    signals = []

    if extracted.has_testimonials:
        score += 20
        signals.append("Testimonials or review language detected.")
    else:
        signals.append("No testimonials or review language found.")

    if extracted.has_credentials:
        score += 20
        signals.append("License, certification, or credential information found.")
    else:
        signals.append("No credential or licensing information detected.")

    if extracted.has_years_in_business:
        score += 15
        evidence = extracted.evidence.get("years_in_business", "Years in business reference found.")
        signals.append(f"Years in business: '{evidence[:80]}'.")
    else:
        signals.append("Years in business or founding date not detected.")

    if extracted.has_case_studies:
        score += 15
        signals.append("Case studies or portfolio content detected.")
    else:
        signals.append("No case studies or portfolio found.")

    if extracted.has_team_info:
        score += 10
        signals.append("Team or 'about us' information found.")
    else:
        signals.append("No team or 'about us' information found.")

    if extracted.has_awards:
        score += 10
        signals.append("Awards or recognition language detected.")

    if extracted.has_associations:
        score += 10
        signals.append("Association or membership language detected.")

    score = min(100, score)
    summary = f"Authority/Trust score: {score}/100. " + " ".join(signals[:4])
    return {"score": score, "summary": summary}


# ---------------------------------------------------------------------------
# PILLAR 6 — AI Citation Readiness
# ---------------------------------------------------------------------------

def _pillar_citation_readiness(extracted: ExtractedData, business) -> dict:
    """
    Is the site's information specific, factual, extractable, and
    organized around real customer questions?
    """
    score = 0
    signals = []

    # Specific factual information present
    has_specifics = (
        extracted.has_phone or
        extracted.has_address or
        extracted.has_pricing_content or
        extracted.has_credentials
    )
    if has_specifics:
        score += 20
        signals.append("Specific factual information (contact, pricing, or credentials) present.")
    else:
        signals.append("Little specific factual information detected.")

    # Internal consistency: business name in multiple places
    name_lower = business.name.lower()
    title_has_name = name_lower in extracted.title.lower()
    content_has_name = name_lower in extracted.body_text.lower()
    if title_has_name and content_has_name:
        score += 15
        signals.append("Business name appears consistently in title and content.")
    elif title_has_name or content_has_name:
        score += 8
        signals.append("Business name appears in some locations.")
    else:
        signals.append("Business name not clearly found in title or content.")

    # Content organized for customer questions (FAQ, process, service descriptions)
    question_signals = sum([
        extracted.has_faq_content,
        extracted.has_faq_schema,
        extracted.has_process_content,
        extracted.has_service_descriptions,
    ])
    if question_signals >= 3:
        score += 25
        signals.append("Content well-organized around customer questions (FAQ, process, services).")
    elif question_signals >= 2:
        score += 15
        signals.append("Some content organized around customer questions.")
    elif question_signals == 1:
        score += 8
        signals.append("Limited content organized around customer questions.")
    else:
        signals.append("Content not organized around customer questions.")

    # Locally relevant content
    city_in_content = business.city.lower() in extracted.body_text.lower()
    state_in_content = (
        business.state.lower() in extracted.body_text.lower() or
        business.state.upper() in extracted.body_text
    )
    if city_in_content and state_in_content:
        score += 15
        signals.append(f"Location ({business.city}, {business.state}) referenced in content.")
    elif city_in_content or state_in_content:
        score += 8
        signals.append("Partial location information in content.")
    else:
        signals.append("Location information not found in page content.")

    # Structured data makes content attributable
    if extracted.has_local_business_schema or extracted.has_organization_schema:
        score += 15
        signals.append("Structured schema helps AI systems attribute content to this business.")
    else:
        signals.append("No structured schema to help AI systems attribute content.")

    # Easy to attribute: business name in schema
    for schema in extracted.schema_data:
        if schema.get("name") and schema.get("@type"):
            score += 10
            signals.append(f"Business name present in schema ({schema.get('@type')}).")
            break

    score = min(100, score)
    summary = f"AI Citation Readiness score: {score}/100. " + " ".join(signals[:4])
    return {"score": score, "summary": summary}
