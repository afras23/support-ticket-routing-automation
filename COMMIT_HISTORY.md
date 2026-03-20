# Commit History

Ordered from oldest to newest. Each commit represents one logical change.
Messages follow `type: description` convention.

---

```
chore: initialise project structure with fastapi and sqlalchemy dependencies

feat: add FastAPI application entry point with single placeholder route

feat: add TicketRequest schema with subject, body, and customer_email fields

feat: add rule-based classifier for billing, technical, and general categories

test: add unit tests for billing and technical keyword detection

feat: add urgency detection — high/medium/low based on keyword signals

test: add unit tests for urgency detection including low urgency signals

feat: add base confidence scoring from keyword match count in classifier

chore: extract RuleBasedClassifier into app/ai/client.py with AIClient protocol

test: add test verifying custom AIClient is used when injected into classify()

feat: add confidence adjustment service with short-body penalty and keyword boost

test: add tests for confidence scoring — penalty, boost, clamping to [0.0, 1.0]

feat: add routing service — assigns queue based on confidence, urgency, category

feat: add manual_review routing for tickets below confidence threshold (0.60)

feat: add escalation routing for high-urgency tickets above confidence threshold

test: add routing unit tests covering all queue assignments and threshold boundary

feat: add auto-resolve service with three-gate evaluation logic

feat: add pattern matching for password reset and FAQ-type auto-resolvable queries

test: add auto-resolve tests for each gate — confidence, category, pattern match

feat: add pipeline orchestrator in automation.py wiring all five stages

test: add integration test for full pipeline via POST /support-ticket/

feat: add TicketLog ORM model with columns for input, classification, routing, automation

feat: add audit service with engine setup, get_db(), and log_ticket()

feat: connect audit logging in orchestrator — every ticket produces an audit row

feat: add health, readiness, and metrics endpoints

feat: add structured logging formatter with pipe-separated key=value output

chore: add Dockerfile with multi-stage build and non-root user

chore: add docker-compose.yml with volume mount for SQLite persistence

chore: add .env.example with descriptions for all configurable values

test: add edge case tests — ambiguous input, short body, mixed urgency and category signals

docs: add README covering architecture, decision logic, failure modes, and setup
```

---

## Notes on the history

**Tests run alongside features, not after.** Classification tests appear immediately after the classifier is built (commits 5, 7). Routing tests follow routing (commit 16). This is the pattern throughout.

**Infrastructure comes after core logic.** Docker and CI are added once the application is working, not upfront. This avoids configuring infrastructure around code that hasn't stabilised.

**Each commit is one thing.** The `manual_review` routing rule and `escalation` routing rule are separate commits (14 and 15) because they are independent conditions. This keeps diffs reviewable and makes `git bisect` useful if a specific routing behaviour regresses.

**The orchestrator is committed after all stages are individually tested.** The `process_ticket` function in `automation.py` is built after classification, confidence, routing, and auto-resolve each have tests. Wiring untested components together is how integration tests hide unit-level bugs.

**Documentation is last.** The README is written against the finished system, not the intended system. Writing documentation before the code is done means it describes what was planned, not what was built.
