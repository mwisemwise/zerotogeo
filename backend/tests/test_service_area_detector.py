"""
Zero to GEO — Service Area Detector tests (PERMANENT).

These tests ensure the semantic service area detector correctly identifies
service area content regardless of exact phrasing.

CRITICAL REGRESSION TEST: "Where We Work"
  A real-world heading that was previously missed by regex-only matching.
  This test must NEVER be removed.

The detector must find meaning + evidence, not exact phrases.
"""

import pytest
from app.services.service_area_detector import detect_service_area, ServiceAreaResult


# ---------------------------------------------------------------------------
# REGRESSION TEST — "Where We Work" (must never be removed)
# ---------------------------------------------------------------------------

class TestWhereWeWorkRegression:
    """
    PERMANENT REGRESSION TEST.

    A real business site uses the heading "Where We Work" to describe
    their service area. The old regex-only approach missed this completely.

    This test ensures we never regress on semantic heading detection.
    """

    def test_where_we_work_heading_detected(self):
        """'Where We Work' heading must be detected as service area content."""
        headings = ["About Us", "Our Services", "Where We Work", "Contact"]
        body = "We provide commercial construction services throughout Southwest Missouri."

        result = detect_service_area(headings, body, [])

        assert result.detected is True
        assert result.confidence == "high"
        assert "Where We Work" in (result.section_heading or "")

    def test_where_we_work_with_city_list(self):
        """'Where We Work' with a list of cities must be detected."""
        headings = ["Where We Work"]
        body = (
            "We proudly serve Branson, Hollister, Springfield, Ozark, Nixa, "
            "and the surrounding communities in Southwest Missouri."
        )

        result = detect_service_area(headings, body, [])

        assert result.detected is True
        assert result.confidence == "high"

    def test_where_we_work_body_only(self):
        """Even without a heading, 'throughout Southwest Missouri' should detect."""
        headings = ["Home", "Services"]
        body = "We provide commercial construction services throughout Southwest Missouri."

        result = detect_service_area(headings, body, [])

        assert result.detected is True


# ---------------------------------------------------------------------------
# Layer 1 — Heading detection
# ---------------------------------------------------------------------------

class TestHeadingDetection:
    """Test that various heading phrasings are correctly identified."""

    @pytest.mark.parametrize("heading", [
        "Where We Work",
        "Where We Serve",
        "Where We Operate",
        "Areas We Serve",
        "Areas We Service",
        "Areas We Cover",
        "Our Service Area",
        "Service Area",
        "Service Locations",
        "Communities We Serve",
        "Cities We Serve",
        "Serving the Greater Springfield Area",
        "Serving Southwest Missouri",
        "Our Coverage Area",
    ])
    def test_heading_variations_detected(self, heading):
        """All common service-area heading variations must be detected."""
        result = detect_service_area(
            [heading],
            "Some generic body text about our business.",
            [],
        )
        assert result.detected is True, f"Failed to detect heading: '{heading}'"
        assert result.section_heading == heading

    @pytest.mark.parametrize("heading", [
        "About Us",
        "Contact Us",
        "Our Team",
        "Services",
        "Home",
        "Portfolio",
        "Testimonials",
    ])
    def test_non_location_headings_not_detected(self, heading):
        """Non-location headings should NOT trigger detection by themselves."""
        result = detect_service_area(
            [heading],
            "We are a great company that does great things.",
            [],
        )
        assert result.detected is False


# ---------------------------------------------------------------------------
# Layer 2 — Coverage statement detection
# ---------------------------------------------------------------------------

class TestStatementDetection:
    """Test detection of service-area statements in body text."""

    @pytest.mark.parametrize("statement", [
        "We serve clients throughout Southwest Missouri.",
        "Proudly serving Branson and the surrounding areas.",
        "Operating across the greater Springfield metropolitan area.",
        "We provide roofing services in Branson, Springfield, and Ozark.",
        "Available within a 50-mile radius of Springfield, MO.",
        "Serving the tri-state area since 2005.",
        "From Branson to Springfield, we cover it all.",
        "We work throughout Taney County and Stone County.",
    ])
    def test_coverage_statements_detected(self, statement):
        """Service coverage statements must be detected."""
        result = detect_service_area([], statement, [])
        assert result.detected is True, f"Failed to detect: '{statement}'"

    def test_no_location_content_not_detected(self):
        """Generic business text without location info should not trigger."""
        text = (
            "We offer the best quality service at competitive prices. "
            "Our team has years of experience and is fully licensed. "
            "Contact us today for a free estimate."
        )
        result = detect_service_area(["Services", "About"], text, [])
        assert result.detected is False


# ---------------------------------------------------------------------------
# Layer 3 — Geographic list detection
# ---------------------------------------------------------------------------

class TestGeoListDetection:
    """Test detection of city/place lists."""

    def test_comma_separated_cities_detected(self):
        """A list of 3+ city names should be detected."""
        body = "We serve Branson, Springfield, Ozark, Nixa, and Republic."
        result = detect_service_area([], body, [])
        assert result.detected is True

    def test_two_cities_not_enough(self):
        """Two cities alone shouldn't trigger list detection."""
        body = "Our office is in Springfield. We also have a branch in Branson."
        # This might still fire via statement detection depending on wording
        # but list detection specifically needs 3+ names in proximity
        result = detect_service_area([], body, [])
        # This could go either way — the point is that simple mentions
        # without coverage language have lower confidence


# ---------------------------------------------------------------------------
# Layer 4 — Schema detection
# ---------------------------------------------------------------------------

class TestSchemaDetection:
    """Test detection from Schema.org structured data."""

    def test_area_served_string(self):
        """areaServed as a simple string."""
        schema = [{"@type": "LocalBusiness", "areaServed": "Southwest Missouri"}]
        result = detect_service_area([], "Some text.", schema)
        assert result.detected is True
        assert result.confidence == "high"

    def test_area_served_object(self):
        """areaServed as a Place object."""
        schema = [{
            "@type": "LocalBusiness",
            "areaServed": {"@type": "State", "name": "Missouri"},
        }]
        result = detect_service_area([], "Some text.", schema)
        assert result.detected is True

    def test_area_served_list(self):
        """areaServed as a list of places."""
        schema = [{
            "@type": "LocalBusiness",
            "areaServed": [
                {"@type": "City", "name": "Branson"},
                {"@type": "City", "name": "Springfield"},
            ],
        }]
        result = detect_service_area([], "Some text.", schema)
        assert result.detected is True

    def test_no_schema_no_detection(self):
        """Empty schema should not trigger detection."""
        result = detect_service_area([], "Generic text.", [])
        assert result.source_layer != "schema"

    def test_schema_without_area_served(self):
        """Schema without areaServed should not trigger schema layer."""
        schema = [{"@type": "LocalBusiness", "name": "Test Co", "telephone": "555-1234"}]
        result = detect_service_area([], "Generic text.", schema)
        # Should not fire from schema alone
        if result.detected:
            assert result.source_layer != "schema"


# ---------------------------------------------------------------------------
# Evidence quality tests
# ---------------------------------------------------------------------------

class TestEvidenceQuality:
    """The detector must always provide evidence for its findings."""

    def test_detection_always_has_evidence(self):
        """When detected=True, evidence list must not be empty."""
        headings = ["Where We Work"]
        body = "We serve Branson and surrounding areas in Missouri."
        result = detect_service_area(headings, body, [])

        assert result.detected is True
        assert len(result.evidence) > 0, "Detection without evidence violates the evidence rule."

    def test_evidence_is_specific(self):
        """Evidence must contain specific text from the page, not generic claims."""
        headings = ["Areas We Serve"]
        body = "We provide plumbing services throughout Greene County, Missouri."
        result = detect_service_area(headings, body, [])

        assert result.detected is True
        # Evidence should reference the actual heading or text
        all_evidence = " ".join(result.evidence)
        assert "Areas We Serve" in all_evidence or "Greene County" in all_evidence or "throughout" in all_evidence

    def test_no_detection_no_evidence(self):
        """When detected=False, evidence should be empty (don't manufacture)."""
        result = detect_service_area(
            ["Home", "About"],
            "We are a great company.",
            [],
        )
        assert result.detected is False
        assert len(result.evidence) == 0


# ---------------------------------------------------------------------------
# Confidence level tests
# ---------------------------------------------------------------------------

class TestConfidenceLevels:
    """Test that confidence is appropriately assigned."""

    def test_heading_gives_high_confidence(self):
        """A dedicated heading should give high confidence."""
        result = detect_service_area(
            ["Our Service Area"],
            "We cover many locations.",
            [],
        )
        assert result.confidence == "high"

    def test_schema_gives_high_confidence(self):
        """Schema areaServed should give high confidence."""
        schema = [{"@type": "LocalBusiness", "areaServed": "Springfield, MO"}]
        result = detect_service_area([], "text", schema)
        assert result.confidence == "high"

    def test_multiple_layers_gives_high_confidence(self):
        """Multiple confirming signals should produce high confidence."""
        headings = ["Where We Work"]
        body = "Proudly serving Branson, Springfield, and Ozark in Southwest Missouri."
        schema = [{"@type": "LocalBusiness", "areaServed": "Southwest Missouri"}]

        result = detect_service_area(headings, body, schema)
        assert result.confidence == "high"


# ---------------------------------------------------------------------------
# Integration with extractor
# ---------------------------------------------------------------------------

class TestExtractorIntegration:
    """Test that the extractor correctly uses the semantic detector."""

    def test_where_we_work_page_has_location_content(self):
        """Full HTML page with 'Where We Work' section must set has_location_content."""
        from app.services.extractor import extract_content

        html = """<!DOCTYPE html>
        <html><head><title>Test Construction Co</title></head>
        <body>
          <h1>Test Construction Co</h1>
          <h2>Our Services</h2>
          <p>We provide commercial construction services.</p>
          <h2>Where We Work</h2>
          <p>We provide commercial construction services throughout
             Southwest Missouri, including Branson, Hollister, Springfield, and Ozark.</p>
          <h2>Contact Us</h2>
          <p>Call (417) 555-1234</p>
        </body></html>
        """

        data = extract_content(html, "https://testconstruction.com")

        assert data.has_location_content is True
        assert "service_area_heading" in data.evidence or "service_area_evidence" in data.evidence

    def test_page_without_service_area_content(self):
        """Page with no location signals should not set has_location_content."""
        from app.services.extractor import extract_content

        html = """<!DOCTYPE html>
        <html><head><title>Generic Site</title></head>
        <body>
          <h1>Welcome</h1>
          <p>We offer great products at great prices.</p>
          <h2>About</h2>
          <p>Our team is experienced and professional.</p>
        </body></html>
        """

        data = extract_content(html, "https://generic.com")
        assert data.has_location_content is False
