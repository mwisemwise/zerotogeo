"""
Zero to GEO — Phase 2 backend tests.

Tests:
  - Database models (CRUD, relationships, cascade deletes)
  - Pydantic schemas (validation, URL normalization, error cases)
  - API endpoints (health, create audit, get audit, get report)
  - Scoring engine (weighted calculation)
  - Extractor service (HTML parsing)
  - GEO analyzer (pillar scoring)
  - Error states (invalid URL, 404 audit, report before complete)

DB setup is handled by conftest.py (shared test SQLite database).
"""

import pytest
from fastapi.testclient import TestClient

from app.models.models import Base, Business, Audit, PillarResult, Finding
from app.main import app
from app.schemas.schemas import AuditCreate, PILLAR_DISPLAY_NAMES
from app.config import ScoringWeights, GeoScoreClassification
from app.services.scoring import calculate_overall_score
from app.services.extractor import extract_content


client = TestClient(app)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestBusinessModel:
    def test_create_business(self, db):
        b = Business(
            name="Branson Roofing Co.",
            website="https://bransonroofing.com",
            city="Branson",
            state="MO",
            category="Residential Roofing",
        )
        db.add(b)
        db.commit()
        db.refresh(b)

        assert b.id is not None
        assert len(b.id) == 36  # UUID format
        assert b.name == "Branson Roofing Co."
        assert b.created_at is not None

    def test_business_audit_relationship(self, db):
        b = Business(
            name="Test Co",
            website="https://test.com",
            city="Springfield",
            state="MO",
            category="HVAC",
        )
        db.add(b)
        db.commit()

        a = Audit(business_id=b.id)
        db.add(a)
        db.commit()

        db.refresh(b)
        assert len(b.audits) == 1
        assert b.audits[0].id == a.id

    def test_business_cascade_delete(self, db):
        b = Business(
            name="Test Co",
            website="https://test.com",
            city="Springfield",
            state="MO",
            category="HVAC",
        )
        db.add(b)
        db.commit()

        a = Audit(business_id=b.id)
        db.add(a)
        db.commit()
        audit_id = a.id

        db.delete(b)
        db.commit()

        # Audit should be cascade deleted
        assert db.get(Audit, audit_id) is None


class TestAuditModel:
    def _make_business(self, db):
        b = Business(
            name="Test Business",
            website="https://test.com",
            city="KC",
            state="MO",
            category="Plumbing",
        )
        db.add(b)
        db.commit()
        return b

    def test_audit_default_status_pending(self, db):
        b = self._make_business(db)
        a = Audit(business_id=b.id)
        db.add(a)
        db.commit()
        db.refresh(a)
        assert a.status == "pending"

    def test_audit_mark_complete(self, db):
        b = self._make_business(db)
        a = Audit(business_id=b.id)
        db.add(a)
        db.commit()

        a.mark_complete(72.5)
        db.commit()
        db.refresh(a)

        assert a.status == "complete"
        assert a.overall_score == 72.5
        assert a.completed_at is not None

    def test_audit_mark_failed(self, db):
        b = self._make_business(db)
        a = Audit(business_id=b.id)
        db.add(a)
        db.commit()

        a.mark_failed("Website unreachable.")
        db.commit()
        db.refresh(a)

        assert a.status == "failed"
        assert a.error_message == "Website unreachable."
        assert a.completed_at is not None


class TestPillarResultModel:
    def test_create_pillar_result(self, db):
        b = Business(
            name="Test",
            website="https://test.com",
            city="STL",
            state="MO",
            category="Lawn Care",
        )
        db.add(b)
        db.commit()

        a = Audit(business_id=b.id)
        db.add(a)
        db.commit()

        pr = PillarResult(
            audit_id=a.id,
            pillar="entity_clarity",
            score=78.0,
            summary="Good entity clarity.",
        )
        db.add(pr)
        db.commit()
        db.refresh(pr)

        assert pr.id is not None
        assert pr.score == 78.0
        assert pr.pillar == "entity_clarity"


class TestFindingModel:
    def test_create_finding(self, db):
        b = Business(
            name="Test",
            website="https://test.com",
            city="STL",
            state="MO",
            category="Landscaping",
        )
        db.add(b)
        db.commit()

        a = Audit(business_id=b.id)
        db.add(a)
        db.commit()

        f = Finding(
            audit_id=a.id,
            pillar="structured_data",
            severity="critical",
            title="No schema found",
            finding="No Schema.org markup detected.",
            evidence="No JSON-LD script tags found.",
            recommendation="Add LocalBusiness schema.",
            priority="P0",
        )
        db.add(f)
        db.commit()
        db.refresh(f)

        assert f.id is not None
        assert f.severity == "critical"
        assert f.priority == "P0"


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------

class TestAuditCreateSchema:
    def test_valid_input(self):
        data = AuditCreate(
            business_name="Test Roofing",
            website_url="https://testroofing.com",
            city="Branson",
            state="MO",
            category="Roofing",
        )
        assert data.business_name == "Test Roofing"
        assert data.website_url == "https://testroofing.com"

    def test_url_auto_prepends_https(self):
        data = AuditCreate(
            business_name="Test",
            website_url="testroofing.com",
            city="Branson",
            state="MO",
            category="Roofing",
        )
        assert data.website_url.startswith("https://")

    def test_url_validation_rejects_no_dot(self):
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            AuditCreate(
                business_name="Test",
                website_url="https://notavalidhostname",
                city="Branson",
                state="MO",
                category="Roofing",
            )

    def test_empty_business_name_rejected(self):
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            AuditCreate(
                business_name="   ",
                website_url="https://test.com",
                city="Branson",
                state="MO",
                category="Roofing",
            )

    def test_whitespace_stripped_from_fields(self):
        data = AuditCreate(
            business_name="  Test Co  ",
            website_url="  https://test.com  ",
            city="  Branson  ",
            state="  MO  ",
            category="  Roofing  ",
        )
        assert data.business_name == "Test Co"
        assert data.city == "Branson"
        assert data.state == "MO"


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_health_returns_200(self):
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_response_shape(self):
        data = client.get("/api/health").json()
        assert data["status"] == "ok"
        assert data["app"] == "Zero to GEO"
        assert "timestamp" in data


class TestCreateAuditEndpoint:
    VALID_PAYLOAD = {
        "business_name": "Test Roofing Co",
        "website_url": "https://example.com",
        "city": "Branson",
        "state": "MO",
        "category": "Residential Roofing",
    }

    def test_create_audit_returns_202(self):
        response = client.post("/api/audits", json=self.VALID_PAYLOAD)
        assert response.status_code == 202

    def test_create_audit_response_shape(self):
        data = client.post("/api/audits", json=self.VALID_PAYLOAD).json()
        assert "id" in data
        assert data["status"] == "pending"
        assert "business" in data
        assert data["business"]["name"] == "Test Roofing Co"

    def test_create_audit_missing_fields_returns_422(self):
        response = client.post("/api/audits", json={"business_name": "Test"})
        assert response.status_code == 422

    def test_create_audit_invalid_url_returns_422(self):
        bad_payload = {**self.VALID_PAYLOAD, "website_url": "not-a-url"}
        response = client.post("/api/audits", json=bad_payload)
        assert response.status_code == 422

    def test_create_audit_empty_name_returns_422(self):
        bad_payload = {**self.VALID_PAYLOAD, "business_name": ""}
        response = client.post("/api/audits", json=bad_payload)
        assert response.status_code == 422


class TestGetAuditEndpoint:
    VALID_PAYLOAD = {
        "business_name": "Test Roofing Co",
        "website_url": "https://example.com",
        "city": "Branson",
        "state": "MO",
        "category": "Residential Roofing",
    }

    def test_get_audit_returns_status(self):
        create_resp = client.post("/api/audits", json=self.VALID_PAYLOAD)
        audit_id = create_resp.json()["id"]

        get_resp = client.get(f"/api/audits/{audit_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["id"] == audit_id
        assert data["status"] in ("pending", "crawling", "extracting", "analyzing", "scoring", "complete", "failed")

    def test_get_nonexistent_audit_returns_404(self):
        response = client.get("/api/audits/nonexistent-id-xyz")
        assert response.status_code == 404

    def test_get_audit_includes_business(self):
        create_resp = client.post("/api/audits", json=self.VALID_PAYLOAD)
        audit_id = create_resp.json()["id"]

        get_resp = client.get(f"/api/audits/{audit_id}")
        data = get_resp.json()
        assert data["business"]["name"] == "Test Roofing Co"
        assert data["business"]["city"] == "Branson"


class TestGetAuditReportEndpoint:
    def test_report_returns_409_when_not_complete(self, db):
        """Report endpoint returns 409 when audit is still processing."""
        # Create a business and pending audit directly in DB
        b = Business(
            name="Test",
            website="https://test.com",
            city="KC",
            state="MO",
            category="Roofing",
        )
        db.add(b)
        db.commit()

        a = Audit(business_id=b.id, status="crawling")
        db.add(a)
        db.commit()

        response = client.get(f"/api/audits/{a.id}/report")
        assert response.status_code == 409

    def test_report_returns_422_when_failed(self, db):
        b = Business(
            name="Test",
            website="https://test.com",
            city="KC",
            state="MO",
            category="Roofing",
        )
        db.add(b)
        db.commit()

        a = Audit(business_id=b.id)
        a.mark_failed("Could not connect.")
        db.add(a)
        db.commit()

        response = client.get(f"/api/audits/{a.id}/report")
        assert response.status_code == 422

    def test_report_returns_200_when_complete(self, db):
        b = Business(
            name="Test Co",
            website="https://test.com",
            city="Springfield",
            state="MO",
            category="Plumbing",
        )
        db.add(b)
        db.commit()

        a = Audit(business_id=b.id)
        db.add(a)
        db.commit()

        # Add pillar results
        for pillar in ("entity_clarity", "local_signals", "structured_data",
                       "content", "authority", "citation_readiness"):
            db.add(PillarResult(audit_id=a.id, pillar=pillar, score=60.0, summary="Test."))

        # Add a finding
        db.add(Finding(
            audit_id=a.id,
            pillar="structured_data",
            severity="high",
            title="Test finding",
            finding="Something is missing.",
            evidence="No schema found.",
            recommendation="Add schema.",
            priority="P0",
        ))

        a.mark_complete(65.0)
        db.commit()

        response = client.get(f"/api/audits/{a.id}/report")
        assert response.status_code == 200
        data = response.json()
        assert data["overall_score"] == 65.0
        assert data["classification"] == "Good Foundation"
        assert len(data["pillar_results"]) == 6
        assert len(data["findings"]) >= 1
        assert "summary" in data
        assert "action_plan" in data

    def test_report_404_for_unknown_id(self):
        response = client.get("/api/audits/totally-unknown-id/report")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Scoring engine tests
# ---------------------------------------------------------------------------

class TestScoringEngine:
    def test_all_pillars_100_gives_100(self):
        pillar_scores = {
            "entity_clarity": {"score": 100},
            "local_signals": {"score": 100},
            "structured_data": {"score": 100},
            "content": {"score": 100},
            "authority": {"score": 100},
            "citation_readiness": {"score": 100},
        }
        assert calculate_overall_score(pillar_scores) == 100.0

    def test_all_pillars_zero_gives_zero(self):
        pillar_scores = {
            "entity_clarity": {"score": 0},
            "local_signals": {"score": 0},
            "structured_data": {"score": 0},
            "content": {"score": 0},
            "authority": {"score": 0},
            "citation_readiness": {"score": 0},
        }
        assert calculate_overall_score(pillar_scores) == 0.0

    def test_weighted_calculation(self):
        # Content (20%) and citation_readiness (20%) at 100, rest at 0
        # Expected: 0.20 * 100 + 0.20 * 100 = 40
        pillar_scores = {
            "entity_clarity": {"score": 0},
            "local_signals": {"score": 0},
            "structured_data": {"score": 0},
            "content": {"score": 100},
            "authority": {"score": 0},
            "citation_readiness": {"score": 100},
        }
        result = calculate_overall_score(pillar_scores)
        assert abs(result - 40.0) < 0.1

    def test_score_capped_at_100(self):
        pillar_scores = {k: {"score": 150} for k in
                        ("entity_clarity", "local_signals", "structured_data",
                         "content", "authority", "citation_readiness")}
        assert calculate_overall_score(pillar_scores) == 100.0


# ---------------------------------------------------------------------------
# Extractor tests
# ---------------------------------------------------------------------------

class TestExtractor:
    SAMPLE_HTML = """<!DOCTYPE html>
    <html>
    <head>
      <title>Branson Roofing Co | Residential Roofing | Branson, MO</title>
      <meta name="description" content="Branson's top roofing contractor. Serving Branson, MO since 2005.">
    </head>
    <body>
      <h1>Branson Roofing Co — Residential Roofing in Branson, MO</h1>
      <h2>Our Roofing Services</h2>
      <h2>Why Choose Us</h2>
      <p>We are licensed and insured. Call us at (417) 555-1234.</p>
      <p>Serving Branson, Springfield, and surrounding areas in Missouri.</p>
      <p>In business since 2005.</p>
      <script type="application/ld+json">{"@type":"LocalBusiness","name":"Branson Roofing Co","telephone":"(417) 555-1234","address":{"streetAddress":"123 Main St","addressLocality":"Branson"}}</script>
    </body>
    </html>
    """

    def test_extracts_title(self):
        data = extract_content(self.SAMPLE_HTML, "https://bransonroofing.com")
        assert "Branson Roofing" in data.title

    def test_extracts_meta_description(self):
        data = extract_content(self.SAMPLE_HTML, "https://bransonroofing.com")
        assert len(data.meta_description) > 10

    def test_extracts_h1(self):
        data = extract_content(self.SAMPLE_HTML, "https://bransonroofing.com")
        assert len(data.h1_tags) == 1
        assert "Branson" in data.h1_tags[0]

    def test_extracts_phone(self):
        data = extract_content(self.SAMPLE_HTML, "https://bransonroofing.com")
        assert data.has_phone
        assert len(data.phone_numbers) >= 1

    def test_detects_schema_type(self):
        data = extract_content(self.SAMPLE_HTML, "https://bransonroofing.com")
        assert data.has_local_business_schema
        assert "LocalBusiness" in data.schema_types

    def test_detects_credentials(self):
        data = extract_content(self.SAMPLE_HTML, "https://bransonroofing.com")
        assert data.has_credentials

    def test_detects_years_in_business(self):
        data = extract_content(self.SAMPLE_HTML, "https://bransonroofing.com")
        assert data.has_years_in_business

    def test_detects_location_content(self):
        data = extract_content(self.SAMPLE_HTML, "https://bransonroofing.com")
        assert data.has_location_content

    def test_empty_html_returns_gracefully(self):
        data = extract_content("", "https://example.com")
        assert data.title == ""
        assert data.body_text == ""

    def test_malformed_html_handled(self):
        bad_html = "<html><head><title>Test</title><body><p>Unclosed tag"
        data = extract_content(bad_html, "https://example.com")
        assert data.title == "Test"

    def test_word_count_calculated(self):
        data = extract_content(self.SAMPLE_HTML, "https://bransonroofing.com")
        assert data.word_count > 0


# ---------------------------------------------------------------------------
# GEO Analyzer tests
# ---------------------------------------------------------------------------

class TestGeoAnalyzer:
    def _make_business(self):
        """Create a mock business object."""
        class MockBusiness:
            name = "Branson Roofing Co"
            website = "https://bransonroofing.com"
            city = "Branson"
            state = "MO"
            category = "Residential Roofing"
        return MockBusiness()

    def test_all_six_pillars_returned(self):
        from app.services.geo_analyzer import analyze
        from app.services.extractor import ExtractedData
        data = ExtractedData(url="https://example.com")
        result = analyze(data, self._make_business())
        assert set(result.keys()) == {
            "entity_clarity", "local_signals", "structured_data",
            "content", "authority", "citation_readiness"
        }

    def test_scores_are_0_to_100(self):
        from app.services.geo_analyzer import analyze
        from app.services.extractor import ExtractedData
        data = ExtractedData(url="https://example.com")
        result = analyze(data, self._make_business())
        for pillar, pillar_data in result.items():
            assert 0 <= pillar_data["score"] <= 100, f"{pillar} score out of range"

    def test_rich_html_scores_higher_than_empty(self):
        from app.services.geo_analyzer import analyze
        from app.services.extractor import extract_content

        rich_html = """
        <html><head>
          <title>Branson Roofing Co | Roofing in Branson, MO</title>
          <meta name="description" content="Top roofing in Branson, MO.">
        </head><body>
          <h1>Branson Roofing Co</h1>
          <h2>Residential Roofing Services in Branson</h2>
          <p>Call (417) 555-1234. Licensed and insured. Serving Branson, MO since 2005.</p>
          <p>We serve Branson, Springfield, and all of southwest Missouri.</p>
          <script type="application/ld+json">{"@type":"LocalBusiness","name":"Branson Roofing Co","telephone":"(417) 555-1234"}</script>
        </body></html>
        """
        empty_html = "<html><body><p>Hi</p></body></html>"

        business = self._make_business()
        rich_data = extract_content(rich_html, "https://bransonroofing.com")
        empty_data = extract_content(empty_html, "https://example.com")

        rich_scores = analyze(rich_data, business)
        empty_scores = analyze(empty_data, business)

        rich_total = sum(v["score"] for v in rich_scores.values())
        empty_total = sum(v["score"] for v in empty_scores.values())
        assert rich_total > empty_total


# ---------------------------------------------------------------------------
# Pillar display names
# ---------------------------------------------------------------------------

class TestPillarDisplayNames:
    def test_all_six_pillars_have_display_names(self):
        expected = {"entity_clarity", "local_signals", "structured_data",
                    "content", "authority", "citation_readiness"}
        assert set(PILLAR_DISPLAY_NAMES.keys()) == expected

    def test_display_names_not_empty(self):
        for key, name in PILLAR_DISPLAY_NAMES.items():
            assert name, f"Display name for {key} is empty"
