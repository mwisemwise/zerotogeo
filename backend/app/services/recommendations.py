"""
Zero to GEO — Findings and recommendation engine (Phase 8).

Converts pillar analysis results into structured, actionable findings.

EVIDENCE RULE: Every negative finding must have evidence from what
the system actually observed. We never manufacture findings.

Priority levels:
  P0 = Fix immediately (critical missing signals)
  P1 = High-value improvement
  P2 = Useful improvement
  P3 = Nice to have
"""

from app.services.extractor import ExtractedData


def generate_findings(pillar_scores: dict, extracted: ExtractedData, business) -> list[dict]:
    """
    Generate structured findings from pillar analysis results.
    Returns a list of finding dicts ready to be persisted.
    """
    findings = []

    findings.extend(_findings_entity_clarity(pillar_scores.get("entity_clarity", {}), extracted, business))
    findings.extend(_findings_local_signals(pillar_scores.get("local_signals", {}), extracted, business))
    findings.extend(_findings_structured_data(pillar_scores.get("structured_data", {}), extracted))
    findings.extend(_findings_content(pillar_scores.get("content", {}), extracted, business))
    findings.extend(_findings_authority(pillar_scores.get("authority", {}), extracted))
    findings.extend(_findings_citation_readiness(pillar_scores.get("citation_readiness", {}), extracted, business))

    return findings


# ---------------------------------------------------------------------------
# Helper: build a finding dict
# ---------------------------------------------------------------------------
# Helper: build dynamic FAQ recommendation based on what's missing
# ---------------------------------------------------------------------------

def _build_faq_recommendation(extracted, business):
    """Only suggest FAQ topics the site doesn't already cover."""
    missing_topics = []
    if not extracted.has_pricing_content:
        missing_topics.append("pricing")
    if not extracted.has_process_content:
        missing_topics.append("your process")
    if not extracted.has_credentials:
        missing_topics.append("qualifications")
    if not extracted.has_location_content:
        missing_topics.append("service area")
    if not missing_topics:
        missing_topics.append("common customer questions")

    topics = ", ".join(missing_topics)
    return (
        f"Add a FAQ section addressing questions customers ask about {business.category} "
        f"in {business.city}: {topics}."
    )


# ---------------------------------------------------------------------------
# Helper: build a finding dict
# ---------------------------------------------------------------------------

def _finding(pillar, severity, title, finding_text, evidence, recommendation, priority):
    return {
        "pillar": pillar,
        "severity": severity,
        "title": title,
        "finding": finding_text,
        "evidence": evidence or "Not verified",
        "recommendation": recommendation,
        "priority": priority,
    }


# ---------------------------------------------------------------------------
# PILLAR 1 — Entity Clarity findings
# ---------------------------------------------------------------------------

def _findings_entity_clarity(pillar_data, extracted, business):
    findings = []
    score = pillar_data.get("score", 0)

    # Missing H1
    if not extracted.h1_tags or len(extracted.h1_tags[0]) < 10:
        findings.append(_finding(
            pillar="entity_clarity",
            severity="high",
            title="Missing or weak H1 heading",
            finding_text=(
                "The page does not have a clear H1 heading that describes the business. "
                "AI systems use headings to identify what a page is about."
            ),
            evidence=f"H1 tags found: {extracted.h1_tags or 'None'}",
            recommendation=(
                f"Add an H1 tag that includes your business name and primary service, such as: "
                f"'{business.name} — {business.category} in {business.city}, {business.state}'"
            ),
            priority="P0",
        ))

    # Missing meta description
    if not extracted.meta_description or len(extracted.meta_description) < 20:
        findings.append(_finding(
            pillar="entity_clarity",
            severity="medium",
            title="Missing meta description",
            finding_text=(
                "No meta description was found. Meta descriptions help AI and search systems "
                "understand the purpose of a page."
            ),
            evidence=f"Meta description: '{extracted.meta_description or 'Not found'}'",
            recommendation=(
                f"Add a meta description between 120–160 characters that describes your business: "
                f"'{business.name} provides {business.category} services in {business.city}, {business.state}. [Add key differentiators here]'"
            ),
            priority="P1",
        ))

    # Missing page title
    if not extracted.title or len(extracted.title) < 10:
        findings.append(_finding(
            pillar="entity_clarity",
            severity="high",
            title="Missing or inadequate page title",
            finding_text="The page title is missing or too short to clearly identify the business.",
            evidence=f"Page title: '{extracted.title or 'Not found'}'",
            recommendation=f"Set the page title to something like '{business.name} | {business.category} | {business.city}, {business.state}'",
            priority="P0",
        ))

    # Thin content
    if extracted.word_count < 200:
        findings.append(_finding(
            pillar="entity_clarity",
            severity="high",
            title="Very thin page content",
            finding_text=(
                f"The page contains only {extracted.word_count} words. AI systems need sufficient "
                "content to understand and accurately represent a business."
            ),
            evidence=f"Word count: {extracted.word_count}",
            recommendation=(
                "Expand the page content to at least 400–600 words covering: what you do, "
                "who you serve, your service area, and what makes you different."
            ),
            priority="P0",
        ))

    # Positive: good title
    if extracted.title and len(extracted.title) > 20 and score >= 70:
        findings.append(_finding(
            pillar="entity_clarity",
            severity="positive",
            title="Clear page title and identity",
            finding_text="The page has a clear title that helps AI systems identify the business.",
            evidence=f"Page title: '{extracted.title[:100]}'",
            recommendation=None,
            priority=None,
        ))

    return findings


# ---------------------------------------------------------------------------
# PILLAR 2 — Local/NAP findings
# ---------------------------------------------------------------------------

def _findings_local_signals(pillar_data, extracted, business):
    findings = []

    if not extracted.has_phone:
        findings.append(_finding(
            pillar="local_signals",
            severity="critical",
            title="Phone number not detected",
            finding_text=(
                "No phone number was found on the page. This is a critical gap for local AI visibility — "
                "AI systems use NAP (Name, Address, Phone) signals to identify and verify local businesses."
            ),
            evidence="No phone number detected in page text or tel: links.",
            recommendation=(
                "Add your phone number in a prominent location on every page (header or footer). "
                "Use a tel: link for mobile users: <a href='tel:+1XXXXXXXXXX'>Phone</a>"
            ),
            priority="P0",
        ))
    else:
        findings.append(_finding(
            pillar="local_signals",
            severity="positive",
            title="Phone number present",
            finding_text="A phone number was detected on the page.",
            evidence=f"Phone found: {extracted.phone_numbers[0] if extracted.phone_numbers else 'detected'}",
            recommendation=None,
            priority=None,
        ))

    if not extracted.has_address:
        findings.append(_finding(
            pillar="local_signals",
            severity="high",
            title="Street address not detected",
            finding_text=(
                "No street address was found on the page. A physical address is a key local entity signal "
                "that helps AI systems verify and cite a business with confidence."
            ),
            evidence="No street address pattern found in page content.",
            recommendation=(
                "Add your full business address to the page footer (or contact section) and include it "
                "in your LocalBusiness schema."
            ),
            priority="P0",
        ))

    city_in_content = business.city.lower() in extracted.body_text.lower()
    if not city_in_content:
        findings.append(_finding(
            pillar="local_signals",
            severity="high",
            title=f"City name '{business.city}' missing from page content",
            finding_text=(
                f"The business city '{business.city}' was not found in the page content. "
                "AI systems use geographic references to connect businesses to local queries."
            ),
            evidence=f"City '{business.city}' not found in page body text.",
            recommendation=(
                f"Mention '{business.city}, {business.state}' explicitly in your page content, "
                f"ideally in an H1 or H2 heading and in your service area description."
            ),
            priority="P0",
        ))
    else:
        findings.append(_finding(
            pillar="local_signals",
            severity="positive",
            title=f"City name '{business.city}' present in content",
            finding_text=f"The city name '{business.city}' was found in the page content.",
            evidence=f"City '{business.city}' found in body text.",
            recommendation=None,
            priority=None,
        ))

    if not extracted.has_location_content:
        findings.append(_finding(
            pillar="local_signals",
            severity="medium",
            title="Service area not described",
            finding_text=(
                "No service area language was detected. AI systems and customers need to know "
                "the geographic area you serve."
            ),
            evidence="No service area or coverage language found in page content.",
            recommendation=(
                f"Add a section explaining your service area: "
                f"'We serve {business.city} and surrounding areas in {business.state}.' "
                "List specific cities or zip codes if applicable."
            ),
            priority="P1",
        ))

    return findings


# ---------------------------------------------------------------------------
# PILLAR 3 — Structured Data findings
# ---------------------------------------------------------------------------

def _findings_structured_data(pillar_data, extracted):
    findings = []

    if not extracted.schema_types:
        findings.append(_finding(
            pillar="structured_data",
            severity="critical",
            title="No Schema.org markup found",
            finding_text=(
                "No Schema.org structured data (JSON-LD) was detected on this page. "
                "Structured data is one of the most direct signals that helps AI systems "
                "identify, classify, and cite a business accurately."
            ),
            evidence="No <script type='application/ld+json'> tags found on page.",
            recommendation=(
                "Add a LocalBusiness JSON-LD schema to every page. At minimum include: "
                "@type, name, address, telephone, url, and geo. "
                "See schema.org/LocalBusiness for the full specification."
            ),
            priority="P0",
        ))
        return findings

    # Schema present but no LocalBusiness
    if not extracted.has_local_business_schema:
        findings.append(_finding(
            pillar="structured_data",
            severity="high",
            title="LocalBusiness schema missing",
            finding_text=(
                f"Schema types found ({', '.join(set(extracted.schema_types))}) but no LocalBusiness "
                "schema was detected. LocalBusiness (or a subtype) is the most important schema type "
                "for local AI visibility."
            ),
            evidence=f"Schema types found: {', '.join(set(extracted.schema_types))}. LocalBusiness not among them.",
            recommendation=(
                "Add a LocalBusiness (or specific subtype like RoofingContractor, Plumber, etc.) "
                "JSON-LD schema with complete name, address, telephone, url, and areaServed fields."
            ),
            priority="P0",
        ))
    else:
        findings.append(_finding(
            pillar="structured_data",
            severity="positive",
            title="LocalBusiness schema present",
            finding_text="LocalBusiness Schema.org markup was found on this page.",
            evidence=f"Schema types: {', '.join(set(extracted.schema_types))}",
            recommendation=None,
            priority=None,
        ))

    if not extracted.has_faq_schema and not extracted.has_faq_content:
        findings.append(_finding(
            pillar="structured_data",
            severity="low",
            title="FAQPage schema not present",
            finding_text=(
                "No FAQPage schema was detected. FAQ schema directly improves the ability "
                "of AI systems to extract question-and-answer pairs from your site."
            ),
            evidence="No FAQPage JSON-LD found. No FAQ content section detected.",
            recommendation=(
                "Add a FAQ section with 5–10 common customer questions and answers, "
                "then mark it up with FAQPage schema."
            ),
            priority="P2",
        ))

    return findings


# ---------------------------------------------------------------------------
# PILLAR 4 — Content findings
# ---------------------------------------------------------------------------

def _findings_content(pillar_data, extracted, business):
    findings = []

    if not extracted.has_faq_content and not extracted.has_faq_schema:
        findings.append(_finding(
            pillar="content",
            severity="high",
            title="No FAQ content found",
            finding_text=(
                "No FAQ section or FAQ schema was detected. FAQs directly improve AI answerability — "
                "AI systems often pull answers to customer questions from FAQ sections."
            ),
            evidence="No FAQ content or FAQPage schema found on page.",
            recommendation=_build_faq_recommendation(extracted, business),
            priority="P1",
        ))

    if not extracted.has_service_descriptions:
        findings.append(_finding(
            pillar="content",
            severity="high",
            title="Service descriptions not found",
            finding_text=(
                "No clear service descriptions were detected in the page headings. "
                "Without specific service descriptions, AI systems cannot accurately represent "
                "what this business offers."
            ),
            evidence=f"H2/H3 headings found: {extracted.h2_tags[:3] or 'None'}",
            recommendation=(
                f"Create dedicated sections for each service you offer, using descriptive H2 headings. "
                f"For example: 'Residential {business.category} in {business.city}' with a paragraph "
                "explaining what the service includes."
            ),
            priority="P0",
        ))

    if not extracted.has_pricing_content:
        findings.append(_finding(
            pillar="content",
            severity="medium",
            title="No pricing information found",
            finding_text=(
                "No pricing, rate, or fee information was detected. Specific pricing information "
                "helps AI systems answer cost-related customer queries."
            ),
            evidence="No pricing-related language found in page content.",
            recommendation=(
                "Add pricing information, even if ranges: starting rates, typical project costs, "
                "or factors that affect pricing. This directly answers a top customer question."
            ),
            priority="P2",
        ))

    if not extracted.has_location_content:
        findings.append(_finding(
            pillar="content",
            severity="high",
            title=f"No service area information for {business.city}",
            finding_text=(
                "The page lacks specific service area content. AI systems use geographic content "
                "to match businesses to local queries."
            ),
            evidence="No service area language detected in page content.",
            recommendation=(
                f"Add a dedicated section: '{business.category} in {business.city}, {business.state}' "
                f"describing the areas you serve, response times, and local expertise."
            ),
            priority="P1",
        ))

    # Positive: FAQ present
    if extracted.has_faq_content or extracted.has_faq_schema:
        findings.append(_finding(
            pillar="content",
            severity="positive",
            title="FAQ content detected",
            finding_text="FAQ content was found, which improves AI answerability.",
            evidence="FAQ section or FAQPage schema detected on page.",
            recommendation=None,
            priority=None,
        ))

    return findings


# ---------------------------------------------------------------------------
# PILLAR 5 — Authority findings
# ---------------------------------------------------------------------------

def _findings_authority(pillar_data, extracted):
    findings = []
    score = pillar_data.get("score", 0)

    if not extracted.has_testimonials:
        findings.append(_finding(
            pillar="authority",
            severity="high",
            title="No testimonials or reviews found",
            finding_text=(
                "No testimonial or review content was detected. Social proof is a key trust signal "
                "that AI systems can detect and report as evidence of authority."
            ),
            evidence="No testimonial or review language found on page.",
            recommendation=(
                "Add a testimonials section with real customer reviews. "
                "Consider embedding Google reviews or adding a Review schema markup."
            ),
            priority="P1",
        ))
    else:
        findings.append(_finding(
            pillar="authority",
            severity="positive",
            title="Testimonials or reviews present",
            finding_text="Review or testimonial content was detected on the page.",
            evidence="Testimonial/review language found in page content.",
            recommendation=None,
            priority=None,
        ))

    if not extracted.has_credentials:
        findings.append(_finding(
            pillar="authority",
            severity="medium",
            title="No credentials or licensing information",
            finding_text=(
                "No license, certification, or credential information was detected. "
                "Credentials are a strong trust signal for AI systems when recommending service providers."
            ),
            evidence="No credential or licensing language found on page.",
            recommendation=(
                "Add your license number(s), certifications, insurance status, and any relevant "
                "professional memberships. Place these in a visible location, not just the footer."
            ),
            priority="P1",
        ))

    if not extracted.has_years_in_business:
        findings.append(_finding(
            pillar="authority",
            severity="low",
            title="Years in business not mentioned",
            finding_text="No 'years in business' or founding year information was detected.",
            evidence="No years-in-business language found in page content.",
            recommendation=(
                "Mention how long you have been in business: "
                "'Serving [city] since [year]' or '[X] years of experience.'"
            ),
            priority="P2",
        ))

    return findings


# ---------------------------------------------------------------------------
# PILLAR 6 — Citation Readiness findings
# ---------------------------------------------------------------------------

def _findings_citation_readiness(pillar_data, extracted, business):
    findings = []

    # Low specificity
    specific_signals = sum([
        extracted.has_phone,
        extracted.has_address,
        extracted.has_pricing_content,
        extracted.has_credentials,
        extracted.has_faq_content,
    ])

    if specific_signals < 2:
        findings.append(_finding(
            pillar="citation_readiness",
            severity="high",
            title="Insufficient specific, extractable information",
            finding_text=(
                "The site has very few specific facts an AI system could confidently extract and cite. "
                "Citation readiness requires specific, verifiable information."
            ),
            evidence=f"Specific signals detected: {specific_signals}/5 (phone, address, pricing, credentials, FAQ).",
            recommendation=(
                "Add more specific factual information: phone, address, pricing ranges, "
                "credentials, and answers to common customer questions."
            ),
            priority="P0",
        ))

    # No local schema for attribution
    if not extracted.has_local_business_schema and not extracted.has_organization_schema:
        findings.append(_finding(
            pillar="citation_readiness",
            severity="high",
            title="No schema for AI attribution",
            finding_text=(
                "Without structured schema, AI systems cannot reliably attribute the content on this site "
                "to a specific, named business entity."
            ),
            evidence="No LocalBusiness or Organization schema found.",
            recommendation=(
                "Add a LocalBusiness schema with a defined name, url, and address. "
                "This makes the content on your site attributable to your business by AI systems."
            ),
            priority="P0",
        ))

    # Content not organized around customer questions
    question_signals = sum([
        extracted.has_faq_content,
        extracted.has_faq_schema,
        extracted.has_process_content,
        extracted.has_service_descriptions,
    ])
    if question_signals < 2:
        # Build recommendation based on what's actually missing
        missing_questions = []
        if not extracted.has_pricing_content:
            missing_questions.append(f"What does {business.category} cost in {business.city}?")
        if not extracted.has_process_content:
            missing_questions.append("How does your process work?")
        if not extracted.has_location_content:
            missing_questions.append("What areas do you serve?")
        if not extracted.has_credentials:
            missing_questions.append("What are your qualifications?")
        if not extracted.has_faq_content:
            missing_questions.append("Common customer FAQs")

        rec_text = "Create pages or sections that directly answer customer questions"
        if missing_questions:
            rec_text += ": " + " ".join(missing_questions)

        findings.append(_finding(
            pillar="citation_readiness",
            severity="high",
            title="Content not organized around customer questions",
            finding_text=(
                "AI systems are most likely to cite content that directly answers specific customer questions. "
                "This site lacks content organized around common questions."
            ),
            evidence=f"Question-oriented content signals: {question_signals}/4 (FAQ, process, service descriptions).",
            recommendation=rec_text,
            priority="P1",
        ))

    # Positive: good citation readiness
    if pillar_data.get("score", 0) >= 65:
        findings.append(_finding(
            pillar="citation_readiness",
            severity="positive",
            title="Strong citation readiness signals",
            finding_text=(
                "The site shows good citation readiness — specific information, consistent entity signals, "
                "and content organized around customer questions."
            ),
            evidence="Multiple citation-readiness signals detected.",
            recommendation=None,
            priority=None,
        ))

    return findings
