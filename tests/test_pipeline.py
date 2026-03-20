"""
Pipeline unit tests.

Tests each stage of the pipeline in isolation so failures can be
pinpointed without running the full HTTP stack. Also covers the
mock AI client injection pattern.
"""

import pytest

from app.ai.client import AIClient, RuleBasedClassifier
from app.schemas.ticket import ClassificationResult
from app.services import auto_resolve, classification, confidence, routing
from app.services.routing import CONFIDENCE_MANUAL_REVIEW_THRESHOLD
from app.services.auto_resolve import CONFIDENCE_AUTO_RESOLVE_THRESHOLD


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


class TestClassification:
    def test_billing_keywords_detected(self) -> None:
        result = classification.classify("billing question", "I need help with my invoice.")
        assert result.category == "billing"

    def test_technical_keywords_detected(self) -> None:
        result = classification.classify("bug report", "The app crashes with an error on login.")
        assert result.category == "technical"

    def test_general_is_fallback(self) -> None:
        result = classification.classify("hello", "I was just wondering about your service.")
        assert result.category == "general"

    def test_high_urgency_detected(self) -> None:
        result = classification.classify("urgent", "This is critical — fix it asap.")
        assert result.urgency == "high"

    def test_low_urgency_detected(self) -> None:
        result = classification.classify("question", "I am wondering about pricing.")
        assert result.urgency == "low"

    def test_medium_urgency_is_default(self) -> None:
        result = classification.classify("help needed", "Can you please help me with this issue?")
        assert result.urgency == "medium"

    def test_confidence_within_valid_range(self) -> None:
        result = classification.classify("subject", "body")
        assert 0.0 <= result.confidence <= 1.0

    def test_returns_classification_result_type(self) -> None:
        result = classification.classify("subject", "body")
        assert isinstance(result, ClassificationResult)

    def test_custom_ai_client_is_used_when_provided(self) -> None:
        """Injected AI client overrides the default rule-based classifier."""

        class FixedClassifier:
            def classify(self, subject: str, body: str) -> ClassificationResult:
                return ClassificationResult(
                    category="billing", urgency="low", confidence=0.99
                )

        result = classification.classify("anything", "anything", ai_client=FixedClassifier())
        assert result.category == "billing"
        assert result.confidence == 0.99

    def test_custom_ai_client_satisfies_protocol(self) -> None:
        """A conforming custom client is recognised as an AIClient."""

        class MyClassifier:
            def classify(self, subject: str, body: str) -> ClassificationResult:
                return ClassificationResult(
                    category="general", urgency="medium", confidence=0.75
                )

        assert isinstance(MyClassifier(), AIClient)

    def test_multiple_billing_keywords_raise_confidence(self) -> None:
        """More keyword matches → higher base confidence from rule-based classifier."""
        single_match = classification.classify("invoice", "I have a billing question.")
        multi_match = classification.classify(
            "invoice payment", "My payment was charged twice and I need a refund."
        )
        assert multi_match.confidence >= single_match.confidence


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------


class TestConfidenceScoring:
    def test_short_body_lowers_confidence(self) -> None:
        base = 0.80
        short_body = "help"  # well under threshold
        result = confidence.score("subject", short_body, base)
        assert result < base

    def test_signal_keywords_boost_confidence(self) -> None:
        base = 0.70
        result = confidence.score(
            "urgent payment issue",
            "Our payment gateway is down and returning an error on every charge.",
            base,
        )
        assert result > base

    def test_score_clamped_to_maximum_of_1(self) -> None:
        result = confidence.score("crash error payment urgent", "crash error down urgent asap critical outage payment invoice broken", 0.99)
        assert result <= 1.0

    def test_score_clamped_to_minimum_of_0(self) -> None:
        # Very short body with a very low base should not go below 0.
        result = confidence.score("s", "s", 0.05)
        assert result >= 0.0

    def test_neutral_ticket_unchanged(self) -> None:
        """A ticket with no penalty/boost factors stays close to base."""
        base = 0.75
        result = confidence.score(
            "General question",
            "I have a moderate length question about your service offering and would like more details please.",
            base,
        )
        # No short-body penalty, no signal keywords — result should equal base.
        assert result == base


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


class TestRouting:
    def _clf(
        self,
        category: str = "general",
        urgency: str = "medium",
        confidence_val: float = 0.75,
    ) -> ClassificationResult:
        return ClassificationResult(
            category=category,  # type: ignore[arg-type]
            urgency=urgency,    # type: ignore[arg-type]
            confidence=confidence_val,
        )

    def test_low_confidence_routes_to_manual_review(self) -> None:
        clf = self._clf(confidence_val=CONFIDENCE_MANUAL_REVIEW_THRESHOLD - 0.01)
        decision = routing.route(clf)
        assert decision.queue == "manual_review"

    def test_exactly_at_threshold_does_not_route_to_manual_review(self) -> None:
        clf = self._clf(confidence_val=CONFIDENCE_MANUAL_REVIEW_THRESHOLD)
        decision = routing.route(clf)
        assert decision.queue != "manual_review"

    def test_high_urgency_routes_to_escalation(self) -> None:
        clf = self._clf(urgency="high", confidence_val=0.80)
        decision = routing.route(clf)
        assert decision.queue == "escalation"

    def test_high_urgency_overrides_category(self) -> None:
        """Billing + high urgency should still escalate, not go to finance."""
        clf = self._clf(category="billing", urgency="high", confidence_val=0.85)
        decision = routing.route(clf)
        assert decision.queue == "escalation"

    def test_billing_routes_to_finance(self) -> None:
        clf = self._clf(category="billing", urgency="medium", confidence_val=0.80)
        decision = routing.route(clf)
        assert decision.queue == "finance"

    def test_technical_routes_to_support(self) -> None:
        clf = self._clf(category="technical", urgency="medium", confidence_val=0.80)
        decision = routing.route(clf)
        assert decision.queue == "support"

    def test_general_routes_to_general_queue(self) -> None:
        clf = self._clf(category="general", urgency="medium", confidence_val=0.80)
        decision = routing.route(clf)
        assert decision.queue == "general"

    def test_routing_decision_has_reason(self) -> None:
        clf = self._clf()
        decision = routing.route(clf)
        assert decision.reason
        assert len(decision.reason) > 0


# ---------------------------------------------------------------------------
# Auto-resolution
# ---------------------------------------------------------------------------


class TestAutoResolve:
    def _clf(
        self,
        category: str = "general",
        confidence_val: float = 0.90,
    ) -> ClassificationResult:
        return ClassificationResult(
            category=category,  # type: ignore[arg-type]
            urgency="low",
            confidence=confidence_val,
        )

    def test_password_reset_resolves(self) -> None:
        clf = self._clf(confidence_val=0.90)
        result = auto_resolve.automate(clf, "account issue", "I need a password reset please.")
        assert result.resolved is True

    def test_how_to_query_resolves(self) -> None:
        clf = self._clf(confidence_val=0.90)
        result = auto_resolve.automate(clf, "help", "How to export my data from the dashboard?")
        assert result.resolved is True

    def test_getting_started_resolves(self) -> None:
        clf = self._clf(confidence_val=0.90)
        result = auto_resolve.automate(clf, "new user", "I need help getting started with the product.")
        assert result.resolved is True

    def test_low_confidence_not_resolved(self) -> None:
        clf = self._clf(confidence_val=CONFIDENCE_AUTO_RESOLVE_THRESHOLD - 0.01)
        result = auto_resolve.automate(clf, "help", "How do I reset my password?")
        assert result.resolved is False
        assert "threshold" in result.reason.lower()

    def test_billing_category_not_resolved(self) -> None:
        clf = self._clf(category="billing", confidence_val=0.95)
        result = auto_resolve.automate(clf, "refund", "How to get a refund for my invoice?")
        assert result.resolved is False
        assert "billing" in result.reason

    def test_technical_category_not_resolved(self) -> None:
        clf = self._clf(category="technical", confidence_val=0.95)
        result = auto_resolve.automate(clf, "bug", "How do I fix this connection error?")
        assert result.resolved is False
        assert "technical" in result.reason

    def test_no_pattern_match_not_resolved(self) -> None:
        clf = self._clf(confidence_val=0.95)
        result = auto_resolve.automate(
            clf, "general", "I have some feedback about the onboarding experience."
        )
        assert result.resolved is False
        assert "pattern" in result.reason.lower()

    def test_automation_result_has_reason(self) -> None:
        clf = self._clf()
        result = auto_resolve.automate(clf, "subject", "body")
        assert result.reason
        assert len(result.reason) > 0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_very_short_ticket_gets_penalised_confidence(self) -> None:
        """One-word body → short-body penalty applies."""
        clf = classification.classify("x", "x")
        scored = confidence.score("x", "x", clf.confidence)
        assert scored < clf.confidence

    def test_ambiguous_ticket_routed_correctly(self) -> None:
        """Ticket with no clear keywords gets general + potentially manual_review."""
        clf = classification.classify("subject", "Please help me.")
        scored = confidence.score("subject", "Please help me.", clf.confidence)
        adjusted = clf.model_copy(update={"confidence": scored})
        decision = routing.route(adjusted)
        # Low-confidence ambiguous tickets go to manual review
        assert decision.queue in {"manual_review", "general"}

    def test_whitespace_only_body_after_strip_triggers_penalty(self) -> None:
        """Whitespace-padded body that strips to short still triggers penalty."""
        base = 0.80
        result = confidence.score("subject", "   hi   ", base)
        assert result < base

    def test_mixed_signals_billing_high_urgency_escalates(self) -> None:
        """Billing ticket with high urgency goes to escalation, not finance."""
        clf = ClassificationResult(category="billing", urgency="high", confidence=0.85)
        decision = routing.route(clf)
        assert decision.queue == "escalation"

    def test_rulebasedclassifier_is_deterministic(self) -> None:
        """Same input always produces the same output."""
        classifier = RuleBasedClassifier()
        r1 = classifier.classify("payment error", "My invoice payment failed with an error.")
        r2 = classifier.classify("payment error", "My invoice payment failed with an error.")
        assert r1 == r2
