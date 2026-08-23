"""
Zero to GEO — Semantic Service Area Detector.

PURPOSE:
  Determine whether a web page communicates WHERE a business operates,
  regardless of the exact phrasing used.

PHILOSOPHY:
  We're not looking for exact phrases. We're looking for meaning + evidence.

  A page communicates service area when it contains:
    1. Geographic references (city names, state names, regions, zip codes, neighborhoods)
    2. In a context that implies coverage/availability (not just a mailing address)

  Evidence types that indicate service area:
    - Dedicated section (heading) about location/coverage
    - Explicit statements like "throughout Southwest Missouri"
    - Lists of cities or areas served
    - Map embeds or "areas we cover" pages
    - Geographic terms paired with service verbs (serve, cover, provide, operate, work)

APPROACH:
  Layer 1 — Heading signals:    Does any heading semantically mean "where we work"?
  Layer 2 — Statement signals:  Does the body contain geographic + coverage language?
  Layer 3 — List signals:       Is there a list of places (3+ geographic names together)?
  Layer 4 — Schema signals:     Does structured data specify areaServed or serviceArea?

  If ANY layer fires with sufficient confidence, has_location_content = True.
  The detector also extracts the evidence (what it actually found).

NO LLM REQUIRED — this is deterministic semantic analysis using:
  - Pattern families (not single regexes)
  - Contextual co-occurrence (geography near service language)
  - Structural signals (headings, lists, schema)
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class ServiceAreaResult:
    """Result of service area detection."""
    detected: bool = False
    confidence: str = "none"  # none | low | medium | high
    evidence: List[str] = field(default_factory=list)
    detected_locations: List[str] = field(default_factory=list)
    section_heading: Optional[str] = None
    source_layer: Optional[str] = None  # heading | statement | list | schema


# ---------------------------------------------------------------------------
# Pattern families — groups of patterns that share semantic meaning
# ---------------------------------------------------------------------------

# Headings that mean "where we work" regardless of exact words
_HEADING_LOCATION_PATTERNS = [
    # Direct: where/areas/locations
    re.compile(r'\bwhere\s+we\s+(?:work|serve|operate|go|cover|build|service)\b', re.I),
    re.compile(r'\bareas?\s+(?:we|I)\s+(?:serve|service|cover|work)\b', re.I),
    re.compile(r'\b(?:our|the)\s+(?:service|coverage|serving)\s+area', re.I),
    re.compile(r'\bservice\s+(?:area|region|territory|locations?|zone)\b', re.I),
    re.compile(r'\bserving\s+(?:the\s+)?(?:greater|metro|all of)?\s*\w+', re.I),
    re.compile(r'\blocations?\s+(?:we\s+)?serv(?:e|ed|ice)', re.I),
    # City/region name + service word in heading
    re.compile(r'\b(?:serving|coverage|available)\s+(?:in|across|throughout)\b', re.I),
    # Common heading variations
    re.compile(r'\bcommunities?\s+we\s+serve\b', re.I),
    re.compile(r'\b(?:cities|towns|neighborhoods?)\s+we\s+(?:serve|cover)\b', re.I),
    re.compile(r'\bour\s+(?:service|work|coverage)\s+(?:area|territory|region|footprint)\b', re.I),
    # Implicit: "Local [Service]" as a heading
    re.compile(r'\blocal\s+\w+\s+(?:services?|company|contractor|provider)\b', re.I),
]

# Body-level patterns that indicate service coverage statements
_COVERAGE_STATEMENT_PATTERNS = [
    # "[verb] throughout/across/in [geographic area]"
    re.compile(
        r'\b(?:serv(?:e|ing|es|iced)|operat(?:e|ing|es)|provid(?:e|ing|es)|work(?:ing)?|cover(?:ing|s)?|available|build(?:ing)?)\b'
        r'.{0,30}?'
        r'\b(?:throughout|across|in|around|near|within)\b'
        r'.{0,60}?'
        r'\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
        re.MULTILINE,
    ),
    # "throughout [Area]" — can stand alone with a geographic reference
    re.compile(
        r'\b(?:throughout|across)\b'
        r'\s+(?:the\s+)?'
        r'(?:greater\s+)?'
        r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*',
        re.MULTILINE,
    ),
    # "proudly serving [area]"
    re.compile(r'\bproudly\s+serv(?:ing|e)\b.{0,80}', re.I),
    # "serving the [area]" — simpler form
    re.compile(
        r'\bserving\s+(?:the\s+)?(?:greater\s+)?'
        r'(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*|tri[\-\s]?(?:state|county|city)(?:\s+\w+)*)',
        re.MULTILINE | re.IGNORECASE,
    ),
    # "from [place] to [place]"
    re.compile(r'\b[Ff]rom\s+[A-Z][a-z]+.{0,40}?\bto\s+[A-Z][a-z]+'),
    # "[distance] mile radius"
    re.compile(r'\b\d+[\s\-]mile\s+(?:radius|range|area)\b', re.I),
    # "and surrounding areas/communities"
    re.compile(r'\band\s+(?:the\s+)?surrounding\s+(?:areas?|communities|towns?|cities|region)\b', re.I),
    # "including [City], [City], and [City]"
    re.compile(r'\bincluding\s+[A-Z][a-z]+(?:\s*,\s*[A-Z][a-z]+){1,}', re.MULTILINE),
    # "[services] in [City], [State]"
    re.compile(
        r'\b(?:services?|work|construction|roofing|plumbing|repairs?)\b'
        r'\s+in\s+'
        r'[A-Z][a-z]+(?:\s*,\s*[A-Z]{2})?',
        re.MULTILINE,
    ),
    # "the [region] area" with geographic modifier
    re.compile(
        r'\bthe\s+(?:greater|metro|tri[\-\s]?(?:state|county|city))\s+\w+\s*(?:area|region|metro)',
        re.I,
    ),
]

# Geographic entity patterns (evidence of place names)
_GEO_PATTERNS = [
    # US State names (common ones — extend as needed)
    re.compile(
        r'\b(?:Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|'
        r'Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|'
        r'Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|'
        r'New\s+Hampshire|New\s+Jersey|New\s+Mexico|New\s+York|North\s+Carolina|North\s+Dakota|'
        r'Ohio|Oklahoma|Oregon|Pennsylvania|Rhode\s+Island|South\s+Carolina|South\s+Dakota|'
        r'Tennessee|Texas|Utah|Vermont|Virginia|Washington|West\s+Virginia|Wisconsin|Wyoming)\b'
    ),
    # US State abbreviations
    re.compile(r'\b[A-Z]{2}\b(?=\s*\d{5}|\s*,|\s*$)'),
    # ZIP codes
    re.compile(r'\b\d{5}(?:-\d{4})?\b'),
    # County references
    re.compile(r'\b\w+\s+County\b', re.I),
    # Regional descriptors
    re.compile(
        r'\b(?:southwest|southeast|northwest|northeast|central|southern|northern|'
        r'eastern|western|greater|metro|tri-state|tri-county)\s+\w+',
        re.I,
    ),
]

# Schema patterns for areaServed
_SCHEMA_AREA_KEYS = {"areaserved", "servicearea", "geographicarea", "availableatorsendto"}


def detect_service_area(
    headings: List[str],
    body_text: str,
    schema_data: List[dict],
) -> ServiceAreaResult:
    """
    Semantically detect whether a page communicates service area information.

    Args:
        headings: All heading text (h1–h3) from the page.
        body_text: Cleaned body text of the page.
        schema_data: Parsed JSON-LD schema objects.

    Returns:
        ServiceAreaResult with detection status, confidence, and evidence.
    """
    result = ServiceAreaResult()

    # --- Layer 1: Heading signals ---
    heading_hit = _check_headings(headings, result)
    if heading_hit:
        result.confidence = "high"
        result.source_layer = "heading"
        result.detected = True

    # --- Layer 2: Statement signals ---
    statement_hit = _check_statements(body_text, result)
    if statement_hit and not result.detected:
        result.confidence = "high" if len(result.evidence) >= 2 else "medium"
        result.source_layer = "statement"
        result.detected = True

    # --- Layer 3: List signals (multiple geographic names clustered) ---
    list_hit = _check_geo_lists(body_text, result)
    if list_hit and not result.detected:
        result.confidence = "medium"
        result.source_layer = "list"
        result.detected = True

    # --- Layer 4: Schema signals ---
    schema_hit = _check_schema(schema_data, result)
    if schema_hit and not result.detected:
        result.confidence = "high"
        result.source_layer = "schema"
        result.detected = True

    # Upgrade confidence if multiple layers agree
    if result.detected:
        layers_hit = sum([heading_hit, statement_hit, list_hit, schema_hit])
        if layers_hit >= 2:
            result.confidence = "high"

    return result


def _check_headings(headings: List[str], result: ServiceAreaResult) -> bool:
    """Check if any heading semantically means 'where we operate'."""
    for heading in headings:
        for pattern in _HEADING_LOCATION_PATTERNS:
            if pattern.search(heading):
                result.section_heading = heading
                result.evidence.append(f"Section heading: \"{heading}\"")
                return True
    return False


def _check_statements(body_text: str, result: ServiceAreaResult) -> bool:
    """Check for explicit coverage/service-area statements in body text."""
    found = False
    for pattern in _COVERAGE_STATEMENT_PATTERNS:
        match = pattern.search(body_text)
        if match:
            snippet = match.group(0).strip()[:150]
            result.evidence.append(f"Coverage statement: \"{snippet}\"")
            found = True
            # Extract location names from the match
            _extract_locations_from_text(snippet, result)
            if len(result.evidence) >= 3:
                break  # Enough evidence
    return found


def _check_geo_lists(body_text: str, result: ServiceAreaResult) -> bool:
    """
    Detect clusters of geographic names that suggest a service area list.
    Look for 3+ capitalized place names in proximity (within 200 chars).
    """
    # Find sequences of capitalized words that look like place names
    # Pattern: capitalized word, not at sentence start, that could be a city
    place_pattern = re.compile(r'\b([A-Z][a-z]{2,15})\b')
    # Common non-place capitalized words to exclude
    non_places = {
        'The', 'Our', 'We', 'Your', 'This', 'That', 'About', 'Contact',
        'Home', 'Services', 'Service', 'Work', 'Call', 'Get', 'Free',
        'Learn', 'More', 'Read', 'View', 'See', 'All', 'New', 'Best',
        'Top', 'Why', 'How', 'What', 'When', 'Who', 'Mon', 'Tue', 'Wed',
        'Thu', 'Fri', 'Sat', 'Sun', 'Jan', 'Feb', 'Mar', 'Apr', 'May',
        'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Inc', 'LLC',
        'Company', 'Business', 'Professional', 'Quality', 'Licensed',
    }

    # Look for comma-separated or line-separated lists of capitalized names
    list_pattern = re.compile(
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
        r'(?:\s*[,\n•·|]\s*)'
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
        r'(?:\s*[,\n•·|]\s*)'
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
    )

    matches = list_pattern.findall(body_text)
    if matches:
        for match_group in matches[:3]:
            places = [p for p in match_group if p not in non_places]
            if len(places) >= 3:
                result.detected_locations.extend(places)
                result.evidence.append(
                    f"Geographic list detected: {', '.join(places[:5])}"
                )
                return True

    return False


def _check_schema(schema_data: List[dict], result: ServiceAreaResult) -> bool:
    """Check JSON-LD schema for areaServed or serviceArea properties."""
    for schema in schema_data:
        if not isinstance(schema, dict):
            continue
        for key, value in schema.items():
            if key.lower().replace("_", "").replace("-", "") in _SCHEMA_AREA_KEYS:
                if value:
                    area_str = _schema_value_to_string(value)
                    result.evidence.append(f"Schema areaServed: \"{area_str[:100]}\"")
                    result.detected_locations.append(area_str[:100])
                    return True
        # Check nested address for geo info suggesting area
        if "geo" in schema or "areaServed" in schema or "serviceArea" in schema:
            geo_val = schema.get("geo") or schema.get("areaServed") or schema.get("serviceArea")
            if geo_val:
                area_str = _schema_value_to_string(geo_val)
                result.evidence.append(f"Schema geographic data: \"{area_str[:100]}\"")
                return True
    return False


def _extract_locations_from_text(text: str, result: ServiceAreaResult) -> None:
    """Pull geographic names from a matched text snippet."""
    for pattern in _GEO_PATTERNS:
        matches = pattern.findall(text)
        for m in matches[:5]:
            loc = m.strip() if isinstance(m, str) else str(m)
            if loc and len(loc) > 2 and loc not in result.detected_locations:
                result.detected_locations.append(loc)


def _schema_value_to_string(value) -> str:
    """Convert a schema value (string, dict, or list) to a readable string."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        name = value.get("name") or value.get("addressLocality") or value.get("description") or ""
        return str(name) if name else str(value)[:100]
    if isinstance(value, list):
        parts = []
        for item in value[:5]:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(item.get("name", str(item)[:50]))
        return ", ".join(parts)
    return str(value)[:100]
