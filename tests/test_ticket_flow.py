"""
API endpoint smoke tests.

Covers the happy path for each routing outcome and validates that
the response structure matches the PipelineResult schema. Input
validation error cases are also covered here.
"""

from fastapi.testclient import TestClient


class TestTicketEndpoint:
    def test_billing_ticket_routes_to_finance(self, client: TestClient) -> None:
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
        assert data["classification"]["category"] == "billing"
        assert data["routing"]["queue"] == "finance"

    def test_technical_ticket_routes_to_support(self, client: TestClient) -> None:
        response = client.post(
            "/support-ticket/",
            json={
                "subject": "Cannot connect to API",
                "body": "The API integration keeps failing with a connection error.",
                "customer_email": "user@example.com",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["classification"]["category"] == "technical"
        assert data["routing"]["queue"] == "support"

    def test_high_urgency_routes_to_escalation(self, client: TestClient) -> None:
        response = client.post(
            "/support-ticket/",
            json={
                "subject": "URGENT: payment system down",
                "body": "Our payment system is down and we are losing revenue. This is critical.",
                "customer_email": "user@example.com",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["classification"]["urgency"] == "high"
        assert data["routing"]["queue"] == "escalation"

    def test_general_ticket_routes_to_general_queue(self, client: TestClient) -> None:
        response = client.post(
            "/support-ticket/",
            json={
                "subject": "General inquiry",
                "body": "I am wondering about your pricing plans and what features are included.",
                "customer_email": "user@example.com",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["classification"]["category"] == "general"
        # Should not be escalated unless urgency is high
        assert data["routing"]["queue"] in {"general", "manual_review"}

    def test_response_has_complete_pipeline_shape(self, client: TestClient) -> None:
        response = client.post(
            "/support-ticket/",
            json={
                "subject": "Test",
                "body": "This is a test ticket body with enough content.",
                "customer_email": "test@example.com",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "ticket_id" in data
        assert "classification" in data
        assert "routing" in data
        assert "automation" in data

        clf = data["classification"]
        assert "category" in clf
        assert "urgency" in clf
        assert "confidence" in clf

        rte = data["routing"]
        assert "queue" in rte
        assert "reason" in rte

        aut = data["automation"]
        assert "resolved" in aut
        assert "reason" in aut

    def test_ticket_id_is_integer(self, client: TestClient) -> None:
        response = client.post(
            "/support-ticket/",
            json={
                "subject": "Test",
                "body": "A simple test ticket.",
                "customer_email": "test@example.com",
            },
        )
        assert response.status_code == 200
        assert isinstance(response.json()["ticket_id"], int)

    def test_missing_customer_email_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/support-ticket/",
            json={"subject": "Test", "body": "Test body"},
        )
        assert response.status_code == 422

    def test_empty_subject_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/support-ticket/",
            json={
                "subject": "",
                "body": "Test body",
                "customer_email": "user@example.com",
            },
        )
        assert response.status_code == 422

    def test_empty_body_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/support-ticket/",
            json={
                "subject": "Test subject",
                "body": "",
                "customer_email": "user@example.com",
            },
        )
        assert response.status_code == 422
