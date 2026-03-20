# Support Ticket Routing System

Internal backend service for automated support ticket triage and routing.

Receives inbound tickets via HTTP, classifies them by category and urgency, scores classification confidence, routes to the appropriate support queue, and attempts auto-resolution for simple cases. All decisions are persisted to an audit log.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Problem Context](#2-problem-context)
3. [Architecture](#3-architecture)
4. [Ticket Processing Flow](#4-ticket-processing-flow)
5. [Decision Logic](#5-decision-logic)
6. [Reliability and Safeguards](#6-reliability-and-safeguards)
7. [Failure Modes](#7-failure-modes)
8. [Running the System](#8-running-the-system)
9. [Project Structure](#9-project-structure)

---

## 1. System Overview

This service sits between the customer-facing ticket intake (web form, email parser, or webhook) and the internal support queues. It processes each inbound ticket through a fixed five-stage pipeline and returns a structured decision object that downstream systems can act on.

It does not replace the support team. It handles the mechanical work — reading tickets, deciding where they go, and resolving the ones that don't need a human — so that support agents spend their time on cases that actually require judgement.

**What it owns:**
- Ticket classification (category + urgency)
- Confidence scoring on that classification
- Queue assignment (escalation, manual review, finance, support, general)
- Auto-resolution for simple, high-confidence cases
- Full audit trail of every decision

**What it does not own:**
- Ticket intake (handled upstream)
- Sending messages to customers (handled downstream)
- Managing the queues themselves (handled by your support tooling)

---

## 2. Problem Context

### Manual triage at volume does not scale

A support team processing 50–200 tickets per day manually reads each one, decides the category, assesses urgency, and routes it to the right person or channel. At low volume this works. As volume grows, the process breaks:

- Response time increases because tickets queue behind the triage step.
- Routing becomes inconsistent depending on who does the triage and when.
- Urgent tickets are not reliably separated from low-priority ones.
- There is no record of routing decisions, so misroutes are invisible until a customer escalates.

### Misrouting has a compounding cost

A ticket sent to the wrong queue has to be re-read, re-categorised, and re-routed. Every handoff adds latency and creates an opportunity for context loss. Billing questions that land with technical support, and technical outages that land with billing, are both common and costly.

### Automation needs a fallback

Fully automated triage only works when the system is confident in its decisions. A system that auto-routes without surfacing uncertainty will silently misroute ambiguous tickets. This system makes the confidence of every decision explicit and routes low-confidence tickets to manual review rather than forcing a potentially incorrect assignment.

---

## 3. Architecture

```
Inbound ticket (HTTP POST)
        │
        ▼
┌─────────────────┐
│   Ingestion     │  Normalise input (strip whitespace, validate fields)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Classification  │  Determine category + urgency + base confidence
│  (ai_client)   │  Default: rule-based keyword matching
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Confidence      │  Adjust base confidence using rule signals:
│  Scoring        │  short body penalty, known keyword boost
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Routing       │  Assign to queue based on confidence → urgency → category
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Auto-resolve    │  Attempt resolution if conditions permit
│                 │  (high confidence + general category + known pattern)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Audit logging   │  Persist full pipeline result to database
└────────┬────────┘
         │
         ▼
    PipelineResult
    (returned to caller)
```

### Stage responsibilities

**Ingestion** (`app/services/ingestion.py`)

Strips whitespace and validates that the ticket has a non-empty subject and body. No logic beyond normalisation.

**Classification** (`app/services/classification.py`, `app/ai/client.py`)

Calls an `AIClient` to produce a `ClassificationResult`: category, urgency, and a base confidence score. The default implementation (`RuleBasedClassifier`) uses keyword matching with confidence derived from match count. Any classifier that satisfies the `AIClient` protocol can be substituted — the rest of the pipeline does not change.

Categories: `billing`, `technical`, `general`
Urgency levels: `low`, `medium`, `high`

**Confidence scoring** (`app/services/confidence.py`)

Applies deterministic adjustments to the base confidence:
- Short body penalty (`−0.15` when body is under 50 characters)
- Signal keyword boost (`+0.08` per match, capped at `+0.20`)

Result is clamped to `[0.0, 1.0]`.

**Routing** (`app/services/routing.py`)

Assigns the ticket to a queue. Decision evaluated in strict priority order — see [Decision Logic](#5-decision-logic).

Queues: `manual_review`, `escalation`, `finance`, `support`, `general`

**Auto-resolve** (`app/services/auto_resolve.py`)

Attempts to resolve the ticket without human involvement. All three conditions must be met:
1. Confidence ≥ 0.85
2. Category is `general`
3. Subject/body matches a known pattern (password reset, FAQ-type queries)

If any condition fails, the ticket is not auto-resolved and continues to the assigned queue.

**Audit logging** (`app/services/audit.py`)

Writes a single row to the `tickets` table for every processed ticket. Stores the original input, classification result, routing decision, and automation outcome. This is the authoritative record of what the system decided and why.

---

## 4. Ticket Processing Flow

### Input

```json
{
  "subject": "Cannot log in to account",
  "body": "Getting a 401 error when trying to log in. Started this morning after we updated our SSO config.",
  "customer_email": "eng@example.com"
}
```

### Classification

The classifier receives the subject and body, detects `technical` category based on keywords (`error`, `login`, `sso`, `configure`), and assigns `medium` urgency (no urgency keywords present). With three matching keywords, base confidence is `0.90`.

### Confidence scoring

Body is 88 characters — above the short-body threshold, no penalty. The words `error` and `login` match signal keywords: `+0.08 + 0.08 = +0.16` boost, capped at `+0.20`. Final confidence: `min(0.90 + 0.16, 1.0) = 1.0`.

### Routing decision

Confidence is `1.0` — above manual review threshold (`0.60`). Urgency is `medium` — no escalation. Category is `technical` → queue: `support`.

```json
{
  "queue": "support",
  "reason": "Technical support request"
}
```

### Automation outcome

Confidence is `1.0` — above auto-resolve threshold (`0.85`). Category is `technical`, not `general`. Gate 2 fails.

```json
{
  "resolved": false,
  "reason": "Category 'technical' requires human review"
}
```

### Full response

```json
{
  "ticket_id": 42,
  "classification": {
    "category": "technical",
    "urgency": "medium",
    "confidence": 1.0
  },
  "routing": {
    "queue": "support",
    "reason": "Technical support request"
  },
  "automation": {
    "resolved": false,
    "reason": "Category 'technical' requires human review"
  }
}
```

---

## 5. Decision Logic

### Routing priority

Routing is evaluated as a strict cascade — the first condition that matches determines the queue. Later conditions are not evaluated.

```
1. confidence < 0.60  →  manual_review
   "Confidence too low for auto-routing (0.52)"

2. urgency == high    →  escalation
   "High urgency — requires immediate attention"

3. category == billing   →  finance
   "Billing or payment inquiry"

4. category == technical →  support
   "Technical support request"

5. (default)             →  general
   "General inquiry"
```

The confidence check takes priority over urgency because a low-confidence classification cannot reliably determine whether the ticket is actually urgent. If we are not sure what the ticket is about, a human needs to look at it regardless of urgency signals.

### Confidence thresholds

| Threshold | Value | Effect |
|-----------|-------|--------|
| Manual review | 0.60 | Below this: routed to `manual_review` regardless of category or urgency |
| Auto-resolve | 0.85 | Below this: auto-resolution is skipped |

### Auto-resolution conditions

All three conditions must be true. A failure at any gate stops resolution.

| Gate | Condition | Failure result |
|------|-----------|----------------|
| 1 | confidence ≥ 0.85 | `resolved: false`, reason includes threshold |
| 2 | category == `general` | `resolved: false`, reason includes category |
| 3 | text matches a known pattern | `resolved: false`, "No auto-resolve pattern matched" |

Auto-resolvable patterns currently include: `password reset`, `forgot password`, `how to`, `how do i`, `what is`, `where can i`, `when does`, `getting started`.

### Base confidence from rule-based classifier

The `RuleBasedClassifier` assigns base confidence based on how many category keywords match:

| Keyword matches | Base confidence |
|----------------|-----------------|
| 3 or more | 0.90 |
| 2 | 0.80 |
| 1 | 0.72 |
| 0 (general fallback) | 0.60 |

The confidence scorer then adjusts this value up or down based on body length and signal keywords.

---

## 6. Reliability and Safeguards

### Low confidence routes to manual review, not to a guess

When the classifier is uncertain (confidence < 0.60), the ticket goes to `manual_review`. The system does not attempt to force a category assignment and route it — it surfaces the uncertainty explicitly. This means ambiguous or malformed tickets are reviewed by a human rather than silently misrouted.

### Auto-resolution has three independent gates

Auto-resolution only fires when all three conditions are met. The category gate (`general` only) prevents billing or technical issues from being resolved without human involvement. The pattern gate ensures there is a concrete textual reason to resolve — it is not inferred from confidence alone.

### The classifier is replaceable without touching the pipeline

The `AIClient` protocol defines a single method: `classify(subject, body) -> ClassificationResult`. Any implementation that satisfies this interface can be dropped in without changes to routing, confidence scoring, auto-resolve, or audit. Switching from rule-based to an LLM-backed classifier is a one-line change at the call site.

### All decisions are logged

Every ticket produces a row in the `tickets` table containing the original input, every stage output, and all reasoning strings. There are no silent decisions. If a ticket is misrouted, the audit log shows exactly what confidence score it received, what queue it was assigned to, and why.

### Health and readiness endpoints

The service exposes three operational endpoints:

- `GET /health` — liveness: is the process running?
- `GET /health/ready` — readiness: can it serve traffic? (checks database connection, returns 503 if not)
- `GET /metrics` — in-process counters for request count, category distribution, queue distribution

---

## 7. Failure Modes

### Short or vague ticket body

**Symptom:** Ticket arrives with a subject like "help" and a one-line body with no domain keywords.

**Handling:** Short body penalty reduces confidence. With no keyword matches, base confidence is 0.60 (general fallback). After penalty, confidence may fall below 0.60, routing to `manual_review`. The ticket is not lost — it goes to a human who can read it.

### Ticket matches keywords from multiple categories

**Symptom:** A billing ticket that also mentions an error ("payment returned an error code").

**Handling:** Category detection iterates in order: `billing` → `technical` → `general`. The first match wins. In this case, billing keywords appear first in the table and the ticket is classified as `billing`. The iteration order is documented in `app/ai/client.py` and can be adjusted if category priority needs to change.

### Misclassification by rule-based classifier

**Symptom:** A ticket is classified into the wrong category.

**Handling:** The routing logic routes to `manual_review` when confidence is below 0.60. A misclassification that produces high confidence (because matching keywords are present but misleading) will not be caught by the confidence gate. This is a known limitation of keyword matching. Switching to an LLM-backed classifier reduces this failure mode; the `AIClient` abstraction is the mechanism for doing so.

### Missing or malformed input

**Symptom:** Ticket arrives with missing `customer_email`, empty `subject`, or empty `body`.

**Handling:** Pydantic validation on `TicketRequest` rejects the request before it reaches any pipeline stage. The API returns `422 Unprocessable Entity` with field-level error details. No partial processing occurs.

### Database unavailable

**Symptom:** The database file is missing, corrupted, or locked.

**Handling:** The audit write at the end of the pipeline will fail with an SQLAlchemy exception. The request returns a `500` error. The `/health/ready` endpoint will also return `503` in this state, which allows load balancers or monitoring to detect the problem independently.

---

## 8. Running the System

### Local setup (without Docker)

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate

# Install runtime dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env

# Start the server
uvicorn app.main:app --reload --port 8000
```

The database file (`tickets.db`) is created automatically on first startup.

### Local setup (Docker)

```bash
docker-compose up --build
```

The SQLite database is mounted to `./data/tickets.db` via the volume in `docker-compose.yml`.

### Sending a ticket

```bash
curl -s -X POST http://localhost:8000/support-ticket/ \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Password reset not working",
    "body": "I requested a password reset but never received the email. How do I reset my password?",
    "customer_email": "user@example.com"
  }' | python -m json.tool
```

Expected response:

```json
{
  "ticket_id": 1,
  "classification": {
    "category": "general",
    "urgency": "low",
    "confidence": 0.75
  },
  "routing": {
    "queue": "general",
    "reason": "General inquiry"
  },
  "automation": {
    "resolved": true,
    "reason": "Matched auto-resolve pattern: 'password reset'"
  }
}
```

### Observing system state

```bash
# Liveness
curl http://localhost:8000/health

# Readiness (checks DB connection)
curl http://localhost:8000/health/ready

# In-process metrics
curl http://localhost:8000/metrics
```

Metrics response:

```json
{
  "request_count": 14,
  "classification_distribution": {
    "billing": 4,
    "technical": 7,
    "general": 3
  },
  "routing_distribution": {
    "support": 6,
    "escalation": 2,
    "finance": 3,
    "manual_review": 1,
    "general": 2
  }
}
```

### Running tests

```bash
pip install -r requirements-dev.txt
DATABASE_URL="sqlite:///:memory:" pytest tests/ -v
```

---

## 9. Project Structure

```
app/
├── main.py                 FastAPI application. Registers routers and
│                           runs setup_logging() on startup. No logic.
│
├── config.py               Pydantic Settings. All environment variables
│                           are declared and validated here. Nothing else
│                           reads from os.environ directly.
│
├── ai/
│   └── client.py           AIClient protocol (the interface any classifier
│                           must satisfy) and RuleBasedClassifier (the default
│                           deterministic implementation). Swap here to use an LLM.
│
├── core/
│   ├── logging.py          Structured log formatter. Produces pipe-separated
│   │                       key=value lines. Call setup_logging() once at startup.
│   └── metrics.py          In-process AppMetrics singleton. Counts requests,
│                           category distribution, and queue distribution.
│                           Not durable — resets on restart.
│
├── models/
│   └── ticket.py           SQLAlchemy ORM model for the tickets table.
│                           Defines schema only. All DB access goes through
│                           services/audit.py.
│
├── schemas/
│   └── ticket.py           Pydantic types used across service boundaries:
│                           TicketRequest, ClassificationResult, RoutingDecision,
│                           AutomationResult, PipelineResult.
│
├── services/
│   ├── ingestion.py        Normalises raw input (strip, validate). Returns
│   │                       (subject, body) tuple ready for classification.
│   │
│   ├── classification.py   Calls ai_client.classify(). Thin wrapper —
│   │                       all classification logic lives in app/ai/client.py.
│   │
│   ├── confidence.py       Applies rule-based adjustments to base confidence.
│   │                       Short body penalty and signal keyword boost.
│   │
│   ├── routing.py          Maps ClassificationResult to a RoutingDecision.
│   │                       Priority: confidence → urgency → category.
│   │
│   ├── auto_resolve.py     Evaluates three gates for auto-resolution.
│   │                       Returns AutomationResult with resolved flag and reason.
│   │
│   ├── automation.py       Pipeline orchestrator. Calls each service in order
│   │                       and assembles the PipelineResult. The only file that
│   │                       coordinates across all stages.
│   │
│   └── audit.py            Owns the SQLAlchemy engine and session factory.
│                           Provides get_db() for dependency injection and
│                           log_ticket() for writing audit rows.
│
└── routes/
    ├── health.py           GET /health, GET /health/ready, GET /metrics
    └── tickets.py          POST /support-ticket/ — delegates to process_ticket()

tests/
├── conftest.py             Sets DATABASE_URL to in-memory SQLite before import.
│                           Provides shared TestClient fixture.
├── test_health.py          Health and metrics endpoint tests.
├── test_ticket_flow.py     API endpoint tests covering each routing outcome
│                           and input validation rejection cases.
└── test_pipeline.py        Unit tests for each service stage in isolation:
                            classification, confidence scoring, routing,
                            auto-resolve, and edge cases.
```

### Configuration reference

All values can be overridden via environment variable or `.env` file.

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Environment name, included in logs |
| `DATABASE_URL` | `sqlite:///./tickets.db` | SQLAlchemy connection string |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `CONFIDENCE_DEFAULT` | `0.82` | Fallback base confidence (unused when classifier computes its own) |
| `CONFIDENCE_THRESHOLD_AUTO_ROUTE` | `0.70` | Reserved for future use |
| `DEFAULT_CHANNEL` | `#support-general` | Fallback routing destination |

### Extending the classifier

To replace the rule-based classifier with an LLM:

```python
# 1. Implement the AIClient protocol
class ClaudeClassifier:
    def classify(self, subject: str, body: str) -> ClassificationResult:
        # Call your LLM API here
        ...

# 2. Pass it to the classification service at the call site in automation.py
raw = classification.classify(subject, body, ai_client=ClaudeClassifier())
```

No other file needs to change.

---

## Dependencies

**Runtime** (`requirements.txt`)
- `fastapi` — HTTP framework and request routing
- `uvicorn` — ASGI server
- `pydantic` + `pydantic-settings` — schema validation and environment config
- `sqlalchemy` — ORM and database access

**Development** (`requirements-dev.txt`)
- `pytest` — test runner
- `httpx` — async HTTP client used by TestClient
- `pytest-cov` — coverage reporting
