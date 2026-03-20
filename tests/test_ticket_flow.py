"""
Tests for the ticket processing pipeline.

Covers the API endpoint, classification service, and routing service in
isolation so failures can be pinpointed quickly.
"""

import pytest
from fastapi.testclient import TestClient

from app.services import classification, routing


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestTicketEndpoint:
    def test_bug_ticket_routes_to_bugs_channel(self, client: TestClient) -> None:
        response = client.post(
            "/support-ticket/",
            json={
                "subject": "App crashes on login",
                "body": "I get an error every time I try to log in. The app crashes immediately.",
                "customer_email": "user@example.com",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["routed_to"] == "#support-bugs"
        assert data["classification"]["category"] == "bug"

    def test_billing_ticket_routes_to_billing_channel(self, client: TestClient) -> None:
        response = client.post(
            "/support-ticket/",
            json={
                "subject": "Invoice question",
                "body": "I have a question about my latest invoice and billing cycle.",
                "customer_email": "user@example.com",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["routed_to"] == "#support-billing"
        assert data["classification"]["category"] == "billing"

    def test_feature_request_routes_to_features_channel(self, client: TestClient) -> None:
        response = client.post(
            "/support-ticket/",
            json={
                "subject": "Feature request: dark mode",
                "body": "I would like to request a dark mode feature for the app.",
                "customer_email": "user@example.com",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["routed_to"] == "#support-features"
        assert data["classification"]["category"] == "feature_request"

    def test_general_question_routes_to_tech_channel(self, client: TestClient) -> None:
        response = client.post(
            "/support-ticket/",
            json={
                "subject": "How do I configure SSO?",
                "body": "I need help setting up single sign-on for my organisation.",
                "customer_email": "user@example.com",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["classification"]["category"] == "technical_question"
        assert data["routed_to"] == "#support-tech"

    def test_urgent_ticket_has_high_urgency(self, client: TestClient) -> None:
        response = client.post(
            "/support-ticket/",
            json={
                "subject": "URGENT: payment not working",
                "body": "This is urgent — our payment integration is broken and orders are failing.",
                "customer_email": "user@example.com",
            },
        )
        assert response.status_code == 200
        assert response.json()["classification"]["urgency"] == "high"

    def test_negative_sentiment_detected(self, client: TestClient) -> None:
        response = client.post(
            "/support-ticket/",
            json={
                "subject": "Very frustrated with the service",
                "body": "I am angry and frustrated. This is terrible and unacceptable.",
                "customer_email": "user@example.com",
            },
        )
        assert response.status_code == 200
        assert response.json()["classification"]["sentiment"] == "negative"

    def test_response_includes_classification_fields(self, client: TestClient) -> None:
        response = client.post(
            "/support-ticket/",
            json={
                "subject": "Test ticket",
                "body": "This is a test ticket body.",
                "customer_email": "test@example.com",
            },
        )
        assert response.status_code == 200
        classification_data = response.json()["classification"]
        assert "category" in classification_data
        assert "urgency" in classification_data
        assert "sentiment" in classification_data
        assert "confidence" in classification_data
        assert "summary" in classification_data

    def test_missing_customer_email_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/support-ticket/",
            json={"subject": "Test", "body": "Test body"},
        )
        assert response.status_code == 422

    def test_empty_subject_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/support-ticket/",
            json={"subject": "", "body": "Test body", "customer_email": "user@example.com"},
        )
        assert response.status_code == 422

    def test_empty_body_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/support-ticket/",
            json={"subject": "Test subject", "body": "", "customer_email": "user@example.com"},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Classification service unit tests
# ---------------------------------------------------------------------------


class TestClassificationService:
    def test_bug_keywords_detected(self) -> None:
        result = classification.classify("app crash", "The system has an error and crashed.")
        assert result.category == "bug"

    def test_billing_keywords_detected(self) -> None:
        result = classification.classify("billing issue", "My invoice shows the wrong amount.")
        assert result.category == "billing"

    def test_feature_request_keywords_detected(self) -> None:
        result = classification.classify("feature request", "Please add dark mode to the app.")
        assert result.category == "feature_request"

    def test_fallback_to_technical_question(self) -> None:
        result = classification.classify("general", "How does the system work?")
        assert result.category == "technical_question"

    def test_urgency_high_on_urgent_keyword(self) -> None:
        result = classification.classify("urgent issue", "This is critical — fix it asap.")
        assert result.urgency == "high"

    def test_urgency_medium_by_default(self) -> None:
        result = classification.classify("question", "I have a question about the product.")
        assert result.urgency == "medium"

    def test_negative_sentiment_detected(self) -> None:
        result = classification.classify("problem", "I am frustrated and angry about this.")
        assert result.sentiment == "negative"

    def test_positive_sentiment_detected(self) -> None:
        result = classification.classify("feedback", "Great product, I love it, thanks!")
        assert result.sentiment == "positive"

    def test_neutral_sentiment_by_default(self) -> None:
        result = classification.classify("question", "How do I reset my password?")
        assert result.sentiment == "neutral"

    def test_long_body_summary_truncated(self) -> None:
        long_body = "word " * 60  # well over 180 chars
        result = classification.classify("subject", long_body)
        assert result.summary.endswith("...")
        assert len(result.summary) <= 183  # 180 chars + "..."

    def test_short_body_summary_not_truncated(self) -> None:
        short_body = "Short body."
        result = classification.classify("subject", short_body)
        assert result.summary == short_body
        assert not result.summary.endswith("...")

    def test_confidence_within_valid_range(self) -> None:
        result = classification.classify("subject", "body text")
        assert 0.0 <= result.confidence <= 1.0


# ---------------------------------------------------------------------------
# Routing service unit tests
# ---------------------------------------------------------------------------


class TestRoutingService:
    def test_bug_routes_to_bugs(self) -> None:
        assert routing.route("bug") == "#support-bugs"

    def test_billing_routes_to_billing(self) -> None:
        assert routing.route("billing") == "#support-billing"

    def test_feature_request_routes_to_features(self) -> None:
        assert routing.route("feature_request") == "#support-features"

    def test_technical_question_routes_to_tech(self) -> None:
        assert routing.route("technical_question") == "#support-tech"

    def test_unknown_category_routes_to_default(self) -> None:
        channel = routing.route("unknown_category")
        assert channel == "#support-general"
