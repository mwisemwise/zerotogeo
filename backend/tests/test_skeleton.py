"""
Phase 1 skeleton tests.

Verifies:
- App creates successfully
- Health endpoint returns 200 with expected fields
- Scoring weights are valid (sum to 1.0)
- Audit endpoints behave correctly for unknown IDs

DB setup is handled by conftest.py.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import ScoringWeights, GeoScoreClassification, settings


client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self):
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_response_structure(self):
        response = client.get("/api/health")
        data = response.json()
        assert data["status"] == "ok"
        assert "app" in data
        assert "version" in data
        assert "timestamp" in data

    def test_health_app_name(self):
        response = client.get("/api/health")
        data = response.json()
        assert data["app"] == "Zero to GEO"


class TestRootEndpoint:
    def test_root_returns_200(self):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_response_structure(self):
        response = client.get("/")
        data = response.json()
        assert "app" in data
        assert "docs" in data


class TestAuditEndpoints:
    def test_create_audit_validates_input(self):
        # Empty body returns 422 (validation error)
        response = client.post("/api/audits", json={})
        assert response.status_code == 422

    def test_get_audit_unknown_id_returns_404(self):
        response = client.get("/api/audits/nonexistent-id")
        assert response.status_code == 404

    def test_get_audit_report_unknown_id_returns_404(self):
        response = client.get("/api/audits/nonexistent-id/report")
        assert response.status_code == 404


class TestScoringWeights:
    def test_weights_sum_to_one(self):
        weights = ScoringWeights.as_dict()
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, expected 1.0"

    def test_all_six_pillars_present(self):
        weights = ScoringWeights.as_dict()
        expected = {
            "entity_clarity",
            "local_signals",
            "structured_data",
            "content",
            "authority",
            "citation_readiness",
        }
        assert set(weights.keys()) == expected

    def test_all_weights_positive(self):
        for pillar, weight in ScoringWeights.as_dict().items():
            assert weight > 0, f"Weight for {pillar} is not positive: {weight}"


class TestGeoScoreClassification:
    def test_excellent_threshold(self):
        assert GeoScoreClassification.classify(95) == "Excellent"
        assert GeoScoreClassification.classify(90) == "Excellent"

    def test_strong_threshold(self):
        assert GeoScoreClassification.classify(85) == "Strong"
        assert GeoScoreClassification.classify(75) == "Strong"

    def test_good_foundation_threshold(self):
        assert GeoScoreClassification.classify(70) == "Good Foundation"
        assert GeoScoreClassification.classify(60) == "Good Foundation"

    def test_needs_work_threshold(self):
        assert GeoScoreClassification.classify(55) == "Needs Work"
        assert GeoScoreClassification.classify(40) == "Needs Work"

    def test_poor_threshold(self):
        assert GeoScoreClassification.classify(25) == "Poor"
        assert GeoScoreClassification.classify(0) == "Poor"


class TestSettings:
    def test_settings_loads(self):
        assert settings.app_name == "Zero to GEO"
        assert settings.app_version == "0.1.0"
        assert settings.crawl_timeout_seconds > 0
        assert settings.crawl_max_pages > 0
