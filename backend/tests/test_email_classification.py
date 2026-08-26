"""
Tests for business-email vs free-email classification.

Verifies:
- Business-domain emails are classified correctly
- Free-provider emails are classified correctly
- Mixed emails correctly set has_business_email
- No emails found leaves classification empty
- Email extraction continues working as before
"""

import pytest

from app.services.extractor import (
    classify_email,
    ClassifiedEmail,
    FREE_EMAIL_PROVIDERS,
    ExtractedData,
    extract_content,
)


class TestClassifyEmail:
    """Unit tests for the classify_email function."""

    def test_business_domain_email(self):
        result = classify_email("business@example.com")
        assert result.address == "business@example.com"
        assert result.domain == "example.com"
        assert result.classification == "business_domain"

    def test_gmail_is_free_provider(self):
        result = classify_email("business@gmail.com")
        assert result.address == "business@gmail.com"
        assert result.domain == "gmail.com"
        assert result.classification == "free_provider"

    def test_yahoo_is_free_provider(self):
        result = classify_email("contact@yahoo.com")
        assert result.domain == "yahoo.com"
        assert result.classification == "free_provider"

    def test_hotmail_is_free_provider(self):
        result = classify_email("info@hotmail.com")
        assert result.domain == "hotmail.com"
        assert result.classification == "free_provider"

    def test_outlook_is_free_provider(self):
        result = classify_email("owner@outlook.com")
        assert result.domain == "outlook.com"
        assert result.classification == "free_provider"

    def test_aol_is_free_provider(self):
        result = classify_email("sales@aol.com")
        assert result.domain == "aol.com"
        assert result.classification == "free_provider"

    def test_case_insensitive_domain(self):
        result = classify_email("Business@Gmail.COM")
        assert result.domain == "gmail.com"
        assert result.classification == "free_provider"

    def test_custom_domain_is_business(self):
        result = classify_email("info@bransonroofing.com")
        assert result.domain == "bransonroofing.com"
        assert result.classification == "business_domain"


class TestFreeEmailProvidersList:
    """Verify the provider list contains the required entries."""

    def test_required_providers_present(self):
        required = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com"}
        assert required.issubset(FREE_EMAIL_PROVIDERS)

    def test_list_is_frozenset(self):
        assert isinstance(FREE_EMAIL_PROVIDERS, frozenset)


class TestExtractedDataEmailClassification:
    """Integration tests using extract_content on HTML with emails."""

    def _html_with_emails(self, *emails):
        """Build minimal HTML containing the given email addresses."""
        email_text = " ".join(emails)
        return f"""
        <html>
        <head><title>Test Business</title></head>
        <body>
            <h1>Test Business</h1>
            <p>Contact us at {email_text}</p>
            <p>We are located at 123 Main St, Branson MO 65616</p>
        </body>
        </html>
        """

    def test_business_domain_email_sets_has_business_email(self):
        html = self._html_with_emails("info@mybusiness.com")
        data = extract_content(html, "https://mybusiness.com")
        assert data.has_email is True
        assert data.has_business_email is True
        assert len(data.classified_emails) == 1
        assert data.classified_emails[0].classification == "business_domain"

    def test_free_email_only_sets_has_business_email_false(self):
        html = self._html_with_emails("owner@gmail.com")
        data = extract_content(html, "https://mybusiness.com")
        assert data.has_email is True
        assert data.has_business_email is False
        assert len(data.classified_emails) == 1
        assert data.classified_emails[0].classification == "free_provider"

    def test_mixed_emails_has_business_email_true(self):
        html = self._html_with_emails("owner@gmail.com", "info@mybusiness.com")
        data = extract_content(html, "https://mybusiness.com")
        assert data.has_email is True
        assert data.has_business_email is True
        classifications = {ce.classification for ce in data.classified_emails}
        assert "business_domain" in classifications
        assert "free_provider" in classifications

    def test_no_email_found_leaves_classification_empty(self):
        html = """
        <html>
        <head><title>Test</title></head>
        <body><h1>No contact info here</h1><p>Just some text.</p></body>
        </html>
        """
        data = extract_content(html, "https://mybusiness.com")
        assert data.has_email is False
        assert data.has_business_email is False
        assert data.classified_emails == []

    def test_email_extraction_still_populates_email_addresses(self):
        """Verify email extraction continues working exactly as before."""
        html = self._html_with_emails("info@mybusiness.com", "backup@yahoo.com")
        data = extract_content(html, "https://mybusiness.com")
        assert data.has_email is True
        assert len(data.email_addresses) == 2
        assert "info@mybusiness.com" in data.email_addresses
        assert "backup@yahoo.com" in data.email_addresses


class TestFreeEmailFinding:
    """Test that the recommendation engine fires the correct finding."""

    def test_free_email_only_generates_finding(self):
        from app.services.recommendations import generate_findings

        # Build extracted data with only a free email
        extracted = ExtractedData(url="https://test.com")
        extracted.has_email = True
        extracted.has_business_email = False
        extracted.classified_emails = [
            ClassifiedEmail(address="owner@gmail.com", domain="gmail.com", classification="free_provider")
        ]
        # Set minimal fields to avoid unrelated findings from crashing
        extracted.body_text = "We serve Branson and surrounding areas."
        extracted.has_phone = True
        extracted.phone_numbers = ["417-555-1234"]
        extracted.has_address = True
        extracted.addresses = ["123 Main St"]
        extracted.has_location_content = True

        class FakeBusiness:
            name = "Test Business"
            city = "Branson"
            state = "MO"
            category = "Roofing"

        pillar_scores = {
            "entity_clarity": {"score": 50},
            "local_signals": {"score": 50},
            "structured_data": {"score": 50},
            "content": {"score": 50},
            "authority": {"score": 50},
            "citation_readiness": {"score": 50},
        }

        findings = generate_findings(pillar_scores, extracted, FakeBusiness())

        free_email_findings = [f for f in findings if "Free email" in f["title"] or "free email" in f["title"].lower()]
        assert len(free_email_findings) == 1
        finding = free_email_findings[0]
        assert finding["severity"] == "medium"
        assert finding["priority"] == "P2"
        assert finding["pillar"] == "local_signals"
        assert "gmail.com" in finding["evidence"]
        # Must NOT claim SEO penalty or ranking damage
        assert "penalty" not in finding["finding"].lower()
        assert "ranking" not in finding["finding"].lower()
        assert "hurts" not in finding["finding"].lower()

    def test_business_email_present_no_finding(self):
        from app.services.recommendations import generate_findings

        extracted = ExtractedData(url="https://test.com")
        extracted.has_email = True
        extracted.has_business_email = True
        extracted.classified_emails = [
            ClassifiedEmail(address="info@mybusiness.com", domain="mybusiness.com", classification="business_domain")
        ]
        extracted.body_text = "We serve Branson and surrounding areas."
        extracted.has_phone = True
        extracted.phone_numbers = ["417-555-1234"]
        extracted.has_address = True
        extracted.addresses = ["123 Main St"]
        extracted.has_location_content = True

        class FakeBusiness:
            name = "Test Business"
            city = "Branson"
            state = "MO"
            category = "Roofing"

        pillar_scores = {
            "entity_clarity": {"score": 50},
            "local_signals": {"score": 50},
            "structured_data": {"score": 50},
            "content": {"score": 50},
            "authority": {"score": 50},
            "citation_readiness": {"score": 50},
        }

        findings = generate_findings(pillar_scores, extracted, FakeBusiness())

        free_email_findings = [f for f in findings if "free email" in f["title"].lower()]
        assert len(free_email_findings) == 0

    def test_no_email_no_finding(self):
        from app.services.recommendations import generate_findings

        extracted = ExtractedData(url="https://test.com")
        extracted.has_email = False
        extracted.has_business_email = False
        extracted.classified_emails = []
        extracted.body_text = "We serve Branson and surrounding areas."
        extracted.has_phone = True
        extracted.phone_numbers = ["417-555-1234"]
        extracted.has_address = True
        extracted.addresses = ["123 Main St"]
        extracted.has_location_content = True

        class FakeBusiness:
            name = "Test Business"
            city = "Branson"
            state = "MO"
            category = "Roofing"

        pillar_scores = {
            "entity_clarity": {"score": 50},
            "local_signals": {"score": 50},
            "structured_data": {"score": 50},
            "content": {"score": 50},
            "authority": {"score": 50},
            "citation_readiness": {"score": 50},
        }

        findings = generate_findings(pillar_scores, extracted, FakeBusiness())

        free_email_findings = [f for f in findings if "free email" in f["title"].lower()]
        assert len(free_email_findings) == 0
