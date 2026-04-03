"""
Prompt templates with versioning for ticket classification.

Prompts are code-reviewed artifacts. Changing a prompt should be a deliberate
commit with version bump so audits can trace decisions back to prompt versions.
"""

# Standard library
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    """A versioned prompt template."""

    name: str
    version: str
    system: str
    user_template: str


CLASSIFICATION_V1 = PromptTemplate(
    name="classification_v1",
    version="1.0",
    system=("You are a support ticket classifier. Return ONLY valid JSON. Do not include commentary."),
    user_template=(
        "Classify this support ticket.\n\n"
        "Return JSON with keys: category, priority.\n"
        "category must be one of: billing|technical|general.\n"
        "priority must be one of: p0|p1|p2|p3.\n\n"
        "Subject:\n{subject}\n\n"
        "Body:\n{body}\n"
    ),
)


CLASSIFICATION_V2 = PromptTemplate(
    name="classification_v2",
    version="2.0",
    system=(
        "You are a support ticket classifier. "
        "Return ONLY valid JSON. Do not include commentary. "
        "Never invent facts not present in the ticket text."
    ),
    user_template=(
        "Classify this support ticket.\n\n"
        "Return JSON with keys: category, priority, sentiment, language, confidence.\n"
        "category: billing|technical|general\n"
        "priority: p0|p1|p2|p3\n"
        "sentiment: negative|neutral|positive\n"
        "language: ISO-like short code (en, es, fr, de, pt, it, nl, ...), or unknown\n"
        "confidence: float from 0.0 to 1.0\n\n"
        "Subject:\n{subject}\n\n"
        "Body:\n{body}\n"
    ),
)


PROMPTS: dict[str, PromptTemplate] = {
    CLASSIFICATION_V1.name: CLASSIFICATION_V1,
    CLASSIFICATION_V2.name: CLASSIFICATION_V2,
}


def get_prompt(name: str, *, subject: str, body: str) -> tuple[str, str, str]:
    """
    Resolve and format a prompt by name.

    Args:
        name: Prompt name (e.g., classification_v2).
        subject: Ticket subject.
        body: Ticket body.

    Returns:
        Tuple of (system_prompt, user_prompt, prompt_version).
    """
    template = PROMPTS[name]
    return (template.system, template.user_template.format(subject=subject, body=body), template.version)
