"""
Zero to GEO — Content extractor service (Phase 5).

Parses HTML with BeautifulSoup4 and extracts structured signals for analysis.

Extracted data includes:
- Page title and meta description
- Headings (h1–h3)
- Body text (cleaned)
- NAP signals (name/address/phone)
- Schema.org markup (JSON-LD and microdata)
- Contact information
- Links
- Social proof signals (testimonials, reviews, credentials)
- Service descriptions
- FAQ content
"""

import json
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from bs4 import BeautifulSoup


@dataclass
class ExtractedData:
    """All signals extracted from a web page."""

    url: str = ""
    title: str = ""
    meta_description: str = ""

    # Headings
    h1_tags: List[str] = field(default_factory=list)
    h2_tags: List[str] = field(default_factory=list)
    h3_tags: List[str] = field(default_factory=list)

    # Body text (cleaned, first 5000 chars for analysis)
    body_text: str = ""
    word_count: int = 0

    # NAP signals
    phone_numbers: List[str] = field(default_factory=list)
    addresses: List[str] = field(default_factory=list)
    email_addresses: List[str] = field(default_factory=list)

    # Schema.org
    schema_types: List[str] = field(default_factory=list)        # e.g. ["LocalBusiness", "Organization"]
    schema_data: List[Dict[str, Any]] = field(default_factory=list)  # Raw parsed schema objects
    has_local_business_schema: bool = False
    has_organization_schema: bool = False
    has_service_schema: bool = False
    has_faq_schema: bool = False
    has_website_schema: bool = False
    has_breadcrumb_schema: bool = False

    # Content signals
    has_faq_content: bool = False            # FAQ section detected on page
    has_pricing_content: bool = False        # Pricing/rates mentioned
    has_service_descriptions: bool = False   # Service descriptions found
    has_location_content: bool = False       # Location/service area mentioned
    has_process_content: bool = False        # Process/how-it-works content
    has_credentials: bool = False            # Certifications, licenses

    # Trust/authority signals
    has_testimonials: bool = False
    has_reviews: bool = False
    has_case_studies: bool = False
    has_years_in_business: bool = False
    has_team_info: bool = False
    has_awards: bool = False
    has_associations: bool = False

    # Contact completeness
    has_phone: bool = False
    has_address: bool = False
    has_email: bool = False
    has_contact_page: bool = False

    # Links
    internal_links: List[str] = field(default_factory=list)
    external_links: List[str] = field(default_factory=list)

    # Raw evidence strings (for finding evidence fields)
    evidence: Dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Phone / email / address patterns
# ---------------------------------------------------------------------------

_PHONE_RE = re.compile(
    r'(?:\+1[\s\-.]?)?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}'
)
_EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
_YEARS_RE = re.compile(
    r'\b(?:serving|in business|established|founded|since)\b.{0,40}?\b(19|20)\d{2}\b',
    re.IGNORECASE,
)
_PRICE_RE = re.compile(
    r'\$\s*\d+|\bpric(?:e|ing|es)\b|\brate[s]?\b|\bfee[s]?\b|\bquote\b|\bestimate\b',
    re.IGNORECASE,
)
_FAQ_RE = re.compile(
    r'\bfaq\b|frequently asked|common questions',
    re.IGNORECASE,
)
_PROCESS_RE = re.compile(
    r'\bhow (?:it|we) work[s]?\b|\bour process\b|\bstep[s]?\b|\bwhat to expect\b',
    re.IGNORECASE,
)
_SERVICE_AREA_RE = re.compile(
    r'\bservice area\b|\bserving\b|\bwe serve\b|\blocal(?:ly)?\b|\bnearby\b'
    r'|\bwhere we (?:work|serve|operate)\b|\bareas? we (?:serve|service|cover)\b'
    r'|\bthroughout\b|\bcommunities we serve\b|\bservice (?:region|territory|locations?)\b'
    r'|\bserve (?:the|all|clients? in)\b',
    re.IGNORECASE,
)
_CREDENTIAL_RE = re.compile(
    r'\blicens(?:ed|e)\b|\bcertifi(?:ed|cation)\b|\binsured\b|\bbonded\b|\baccredited\b|\bmember\b',
    re.IGNORECASE,
)
_TESTIMONIAL_RE = re.compile(
    r'\btestimonial[s]?\b|\breview[s]?\b|\bwhat (?:our )? (?:customers?|clients?) say\b|\bfive[\s\-]star\b|\b5[\s\-]star\b',
    re.IGNORECASE,
)
_CASE_STUDY_RE = re.compile(
    r'\bcase stud(?:y|ies)\b|\bproject[s]?\b|\bportfolio\b|\bwork we[\'\s]ve done\b',
    re.IGNORECASE,
)
_TEAM_RE = re.compile(
    r'\bour team\b|\bmeet (?:the|our)\b|\babout us\b|\bour staff\b|\bfounder\b',
    re.IGNORECASE,
)
_AWARD_RE = re.compile(
    r'\baward[s]?\b|\bhonor[s]?\b|\bbest of\b|\brecogniz(?:ed|ition)\b|\btop[\s\-]rated\b',
    re.IGNORECASE,
)
_ASSOCIATION_RE = re.compile(
    r'\bmember(?:ship)?\b|\bassociation\b|\baffiliat(?:ed|ion)\b|\bchamber of commerce\b|\bnational\b',
    re.IGNORECASE,
)


def extract_content(html: str, url: str) -> ExtractedData:
    """
    Parse HTML and extract all GEO-relevant signals.

    Uses lxml parser for main content (speed + malformed-HTML tolerance).
    Uses html.parser for JSON-LD schema extraction (lxml can mangle script content).
    """
    data = ExtractedData(url=url)

    if not html or not html.strip():
        data.evidence["parse_error"] = "Page returned empty content."
        return data

    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception as e:
            data.evidence["parse_error"] = f"Could not parse HTML: {str(e)[:200]}"
            return data

    # Use a separate html.parser soup for JSON-LD to avoid lxml stripping script content
    try:
        soup_for_schema = BeautifulSoup(html, "html.parser")
    except Exception:
        soup_for_schema = soup

    _extract_meta(soup, data)
    _extract_headings(soup, data)
    _extract_body_text(soup, data)
    _extract_schema(soup_for_schema, data)
    _extract_contact_signals(data)
    _extract_content_signals(data)
    _extract_links(soup, url, data)

    return data


def _extract_meta(soup: BeautifulSoup, data: ExtractedData) -> None:
    title_tag = soup.find("title")
    if title_tag:
        data.title = title_tag.get_text(strip=True)[:300]

    meta_desc = soup.find("meta", attrs={"name": re.compile(r"description", re.I)})
    if meta_desc:
        data.meta_description = meta_desc.get("content", "")[:500]

    if data.title:
        data.evidence["title"] = data.title
    if data.meta_description:
        data.evidence["meta_description"] = data.meta_description


def _extract_headings(soup: BeautifulSoup, data: ExtractedData) -> None:
    data.h1_tags = [h.get_text(strip=True) for h in soup.find_all("h1")][:5]
    data.h2_tags = [h.get_text(strip=True) for h in soup.find_all("h2")][:15]
    data.h3_tags = [h.get_text(strip=True) for h in soup.find_all("h3")][:20]

    if data.h1_tags:
        data.evidence["h1"] = data.h1_tags[0]
    if data.h2_tags:
        data.evidence["h2_sample"] = " | ".join(data.h2_tags[:3])


def _extract_body_text(soup: BeautifulSoup, data: ExtractedData) -> None:
    # Remove script, style, nav, footer to get main content text
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    raw_text = soup.get_text(separator=" ", strip=True)
    # Collapse whitespace
    cleaned = re.sub(r'\s+', ' ', raw_text).strip()
    data.body_text = cleaned[:8000]  # Cap for analysis
    data.word_count = len(cleaned.split())


def _extract_schema(soup: BeautifulSoup, data: ExtractedData) -> None:
    """Extract JSON-LD schema.org markup."""
    schema_scripts = soup.find_all("script", attrs={"type": "application/ld+json"})

    for script in schema_scripts:
        try:
            raw = script.string or script.get_text()
            if not raw:
                continue
            parsed = json.loads(raw)

            # Handle @graph arrays
            if isinstance(parsed, dict) and "@graph" in parsed:
                items = parsed["@graph"]
            elif isinstance(parsed, list):
                items = parsed
            else:
                items = [parsed]

            for item in items:
                if not isinstance(item, dict):
                    continue
                schema_type = item.get("@type", "")
                if isinstance(schema_type, list):
                    for t in schema_type:
                        _record_schema_type(t, item, data)
                elif schema_type:
                    _record_schema_type(schema_type, item, data)

        except (json.JSONDecodeError, Exception):
            # Malformed schema — record the presence of the tag but not the content
            data.evidence["schema_parse_error"] = "Schema.org markup found but could not be parsed (malformed JSON-LD)."

    if data.schema_types:
        data.evidence["schema_types_found"] = ", ".join(sorted(set(data.schema_types)))


def _record_schema_type(schema_type: str, item: dict, data: ExtractedData) -> None:
    data.schema_types.append(schema_type)
    data.schema_data.append(item)

    t = schema_type.lower()
    if "localbusiness" in t or "home" in t or "contractor" in t or "service" in t.split()[0] if t.split() else False:
        data.has_local_business_schema = True
    if t == "localbusiness":
        data.has_local_business_schema = True
    if t == "organization":
        data.has_organization_schema = True
    if t in ("service", "product"):
        data.has_service_schema = True
    if t == "faqpage":
        data.has_faq_schema = True
    if t == "website":
        data.has_website_schema = True
    if t == "breadcrumblist":
        data.has_breadcrumb_schema = True

    # Many local business types inherit from LocalBusiness
    local_business_subtypes = {
        "plumber", "plumbingservice", "electrician", "contractor",
        "roofingcontractor", "hvacbusiness", "locksmith", "movers",
        "painter", "dentist", "physician", "lawyer", "accountant",
        "restaurant", "store", "autorepair", "beautysalon", "hotel",
        "realestate", "insurance", "financialservice", "homeandc",
        "generalcontractor", "handyman", "landscaping", "cleaning",
        "pestcontrol", "towing", "veterinar", "optician", "pharmacy",
        "drycleaning", "notary", "tattooparlor", "gym", "fitness",
    }
    if any(sub in t for sub in local_business_subtypes):
        data.has_local_business_schema = True


def _extract_contact_signals(data: ExtractedData) -> None:
    """Extract contact info from body text."""
    text = data.body_text

    phones = _PHONE_RE.findall(text)
    data.phone_numbers = list(set(phones))[:5]
    data.has_phone = bool(data.phone_numbers)
    if data.phone_numbers:
        data.evidence["phone_found"] = data.phone_numbers[0]

    emails = _EMAIL_RE.findall(text)
    # Filter out common non-contact emails
    emails = [e for e in emails if not any(x in e.lower() for x in ("example", "domain", "test"))]
    data.email_addresses = list(set(emails))[:5]
    data.has_email = bool(data.email_addresses)

    # Basic address detection: look for common address patterns
    addr_pattern = re.compile(
        r'\d{1,6}\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:St|Ave|Rd|Blvd|Dr|Ln|Way|Ct|Pl|Hwy)\b.{0,60}',
        re.IGNORECASE,
    )
    addresses = addr_pattern.findall(text)
    data.addresses = [a.strip() for a in addresses[:3]]
    data.has_address = bool(data.addresses)
    if data.addresses:
        data.evidence["address_found"] = data.addresses[0][:200]


def _extract_content_signals(data: ExtractedData) -> None:
    """Scan body text for content quality signals."""
    text = data.body_text + " " + " ".join(data.h1_tags + data.h2_tags + data.h3_tags)

    data.has_faq_content = bool(_FAQ_RE.search(text))
    data.has_pricing_content = bool(_PRICE_RE.search(text))
    data.has_process_content = bool(_PROCESS_RE.search(text))
    data.has_credentials = bool(_CREDENTIAL_RE.search(text))
    data.has_testimonials = bool(_TESTIMONIAL_RE.search(text))
    data.has_case_studies = bool(_CASE_STUDY_RE.search(text))
    data.has_team_info = bool(_TEAM_RE.search(text))
    data.has_awards = bool(_AWARD_RE.search(text))
    data.has_associations = bool(_ASSOCIATION_RE.search(text))
    data.has_years_in_business = bool(_YEARS_RE.search(text))

    # Service area — use semantic detector instead of regex-only check
    from app.services.service_area_detector import detect_service_area
    all_headings = data.h1_tags + data.h2_tags + data.h3_tags
    sa_result = detect_service_area(all_headings, data.body_text, data.schema_data)
    data.has_location_content = sa_result.detected
    if sa_result.detected:
        if sa_result.section_heading:
            data.evidence["service_area_heading"] = sa_result.section_heading
        if sa_result.evidence:
            data.evidence["service_area_evidence"] = " | ".join(sa_result.evidence[:3])
        if sa_result.detected_locations:
            data.evidence["service_area_locations"] = ", ".join(sa_result.detected_locations[:8])

    # Service descriptions: if there are meaningful h2/h3 headings beyond "Home" / "Contact"
    content_headings = [h for h in data.h2_tags + data.h3_tags
                        if len(h) > 5 and h.lower() not in ("home", "contact", "menu", "navigation")]
    data.has_service_descriptions = len(content_headings) >= 2

    # Evidence samples
    if data.has_faq_content:
        data.evidence["faq_signal"] = "FAQ content detected on page."
    if data.has_pricing_content:
        data.evidence["pricing_signal"] = "Pricing or rates content detected."
    if data.has_credentials:
        data.evidence["credentials_signal"] = "License/certification language detected."
    if data.has_testimonials:
        data.evidence["testimonials_signal"] = "Testimonial or review language detected."
    if data.has_years_in_business:
        match = _YEARS_RE.search(text)
        if match:
            data.evidence["years_in_business"] = match.group(0)[:100]


def _extract_links(soup: BeautifulSoup, base_url: str, data: ExtractedData) -> None:
    from urllib.parse import urlparse, urljoin
    base_domain = urlparse(base_url).netloc

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            if href.startswith("tel:"):
                # Extract phone from tel: links
                phone = href.replace("tel:", "").strip()
                if phone:
                    data.phone_numbers.append(phone)
                    data.has_phone = True
                    data.evidence["phone_from_tel_link"] = phone
            continue

        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)

        if parsed.netloc == base_domain or not parsed.netloc:
            data.internal_links.append(full_url)
            # Detect contact page
            if "contact" in href.lower():
                data.has_contact_page = True
        else:
            data.external_links.append(full_url)

    data.internal_links = list(set(data.internal_links))[:30]
    data.external_links = list(set(data.external_links))[:20]
