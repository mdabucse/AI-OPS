# Capstone RAG Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local retrieval-augmented RCA context so the Day 2 RCA uses relevant runbooks and records the retrieved sources.

**Architecture:** Store a small JSON knowledge base inside the Capstone application. Use deterministic keyword retrieval so the demo works offline and remains explainable. The RCA adapter will persist retrieved documents and expose them through the simulation API and a protected search endpoint.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL, JSON knowledge documents, pytest.

**Spec:** `Capstone/IMPLEMENTATION_PLAN.md` RAG phase.

## Global Constraints

- RAG must work without an external API or internet connection.
- Retrieved sources must be visible and traceable in the RCA result.
- Existing Phase 1 login, simulation, approval, and remediation behavior must remain unchanged.
- Unauthenticated users must not access the RAG search endpoint.

## Review Focus

- Empty or unrelated queries return an empty result rather than inventing evidence.
- Pool-saturation queries retrieve the database-pool runbook.
- RCA findings persist retrieved context and expose it to the UI/API.
- Existing approval decisions still change simulated metrics only after approval.

### Task 1: Add the local knowledge base and retrieval service

**Files:**
- Create: `Capstone/app/knowledge/runbooks.json`
- Create: `Capstone/app/rag.py`
- Create: `Capstone/tests/test_rag.py`

**Interfaces:**
- `retrieve_context(query: str, top_k: int = 3) -> list[dict]`

- [x] Write failing retrieval tests for pool saturation, top-k, and unrelated queries.
- [x] Run `uv run pytest tests/test_rag.py -v` and verify failure.
- [x] Implement deterministic token-overlap retrieval over the JSON runbooks.
- [x] Run the focused tests and verify they pass.

### Task 2: Persist RAG context in RCA findings

**Files:**
- Modify: `Capstone/app/models.py`
- Modify: `Capstone/app/db.py`
- Modify: `Capstone/app/rca_agent.py`
- Modify: `Capstone/app/routes/simulation.py`
- Modify: `Capstone/tests/test_approvals.py`

**Interfaces:**
- `RcaFinding.retrieved_context: list[dict]`

- [x] Add a failing assertion that RCA findings contain the database-pool runbook source.
- [x] Add the database migration-safe column and include retrieved context in the context hash.
- [x] Use retrieved context in the RCA evidence and API payload.
- [x] Run focused and full tests.

### Task 3: Add the protected retrieval endpoint and dashboard references

**Files:**
- Create: `Capstone/app/routes/rag.py`
- Modify: `Capstone/app/main.py`
- Modify: `Capstone/app/templates/dashboard.html`
- Modify: `Capstone/app/static/app.js`
- Modify: `Capstone/tests/test_rag.py`

**Interfaces:**
- `GET /api/rag/search?q=<query>&top_k=<n>`

- [x] Verify unauthenticated search is rejected and authenticated search returns source titles/content.
- [x] Add a protected endpoint and show retrieved references under the RCA panel.
- [x] Run all tests and rebuild the Docker app.
