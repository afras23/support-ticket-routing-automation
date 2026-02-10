# Support Ticket Routing & Summarization

Webhook → Classification → Sentiment → Routing → Database

## Problem
Support teams manually triage 50–200 tickets per day, causing slow response times and inconsistent routing.

## Solution
An automated support ticket pipeline that classifies, prioritizes, summarizes, and routes tickets instantly.

## Features
- Multi-class ticket classification
- Urgency & sentiment detection
- Automatic team routing
- Manager-ready ticket summaries
- Persistent ticket logging with confidence scores

## Tech Stack
- Python
- FastAPI
- Rule-based NLP (LLM-ready)
- SQLite (Postgres-ready)
- Slack-ready routing logic

## Business Impact
- ~60% faster first response time
- Consistent routing
- Reduced support workload

> Architecture is LLM-provider agnostic and can be upgraded to Claude/OpenAI in production.
