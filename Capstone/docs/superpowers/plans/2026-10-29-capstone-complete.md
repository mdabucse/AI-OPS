# Capstone Mandatory Components Completion Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the Capstone RCA Agent with anomaly detection, alerting, and governance while preserving the working RAG, dynamic threshold, approval, and remediation workflow.

**Architecture:** Anomaly detection, alerting, and governance are separate services that consume the existing simulation and RCA records. Each service persists its result in PostgreSQL, emits an audit event, and exposes its state through the API and sequential dashboard workflow. External notifications use Microsoft Teams webhook configuration when available and a clearly labelled local simulation mode otherwise.

**Tech Stack:** FastAPI, SQLAlchemy 2, PostgreSQL, Python standard library, pytest, vanilla JavaScript.

**Spec:** `Capstone/IMPLEMENTATION_PLAN.md` and the Capstone requirements supplied by the user.

## Global Constraints

- The application must demonstrate the complete flow from metric monitoring to anomaly detection, alert generation, RCA, approval, and simulated remediation.
- Existing Phase 1, RAG, and dynamic-threshold behavior must remain working.
- Anomaly detection must use a documented ML-style statistical method and persist its score and status.
- Alerts must support Microsoft Teams webhook delivery and local simulation mode for offline training.
- Governance must preserve model, threshold, retrieval, approval, actor, and correlation traceability.
- Rejection or duplicate approval must not apply remediation.

## Review Focus

- A normal baseline is not marked anomalous.
- The Day 2 incident produces an anomaly score and `anomalous` status.
- Notification failure is recorded and never reported as successful delivery.
- A rejected or duplicate approval leaves metrics unchanged.
- Governance records retain the model/version, RAG context hash, threshold evaluation, actor, and correlation ID.

### Task 1: Add anomaly detection

**Files:**
- Create: `Capstone/app/anomaly.py`
- Create: `Capstone/tests/test_anomaly.py`
- Modify: `Capstone/app/models.py`
- Modify: `Capstone/app/db.py`
- Modify: `Capstone/app/simulation.py`
- Modify: `Capstone/app/routes/ui.py`

**Interfaces:**
- `calculate_z_score(observed: float, baseline: float, deviation: float) -> float`
- `detect_run_anomaly(session: Session, run_id: str) -> AnomalyResult`

- [x] Write failing tests for the z-score and persisted Day 2 anomaly result.
- [x] Implement the statistical detector using baseline `0.12s`, incident `1.35s`, and a documented deviation floor.
- [x] Persist model name, version, score, status, baseline, and observed value.
- [x] Add anomaly fields to the metrics API and dashboard.
- [x] Run focused anomaly tests.

### Task 2: Add alerting

**Files:**
- Create: `Capstone/app/alerting.py`
- Create: `Capstone/app/routes/alerts.py`
- Create: `Capstone/tests/test_alerting.py`
- Modify: `Capstone/app/models.py`
- Modify: `Capstone/app/db.py`
- Modify: `Capstone/app/simulation.py`
- Modify: `Capstone/app/main.py`

**Interfaces:**
- `send_alert(session: Session, run_id: str, channel: str = "teams") -> AlertEvent`
- `POST /api/alerts/{run_id}/send`
- `GET /api/alerts?run_id=<id>`

- [x] Write tests for local simulation delivery, Teams payload construction, and failed delivery status.
- [x] Persist alert channel, payload, status, delivery time, and error.
- [x] Automatically create a Teams alert in local simulation mode when the threshold or anomaly is violated.
- [x] Use `TEAMS_WEBHOOK_URL` when configured; never claim delivery success when the webhook fails.
- [x] Add alert status to the dashboard and audit history.

### Task 3: Add governance and traceability

**Files:**
- Create: `Capstone/app/governance.py`
- Create: `Capstone/app/routes/governance.py`
- Create: `Capstone/tests/test_governance.py`
- Modify: `Capstone/app/models.py`
- Modify: `Capstone/app/db.py`
- Modify: `Capstone/app/rca_agent.py`
- Modify: `Capstone/app/rca_agent.py`
- Modify: `Capstone/app/routes/approvals.py`
- Modify: `Capstone/app/main.py`

**Interfaces:**
- `record_governance_event(session, run_id: str, event_type: str, actor: str, details: dict) -> GovernanceRecord`
- `GET /api/governance?run_id=<id>`

- [x] Write tests that governance records include model version, context hash, threshold status, actor, and correlation ID.
- [x] Persist governance records for RCA creation, alert creation, approval decisions, and remediation.
- [x] Add a protected governance endpoint and dashboard section.
- [x] Ensure duplicate approvals create no second remediation event.

### Task 4: Integrate and verify the complete workflow

**Files:**
- Modify: `Capstone/app/routes/simulation.py`
- Modify: `Capstone/app/static/app.js`
- Modify: `Capstone/app/templates/dashboard.html`
- Modify: `Capstone/README.md`
- Modify: `Capstone/IMPLEMENTATION_PLAN.md`
- Create: `Capstone/tests/test_complete_workflow.py`

- [x] Write an end-to-end test covering simulation, threshold violation, anomaly, alert, RAG RCA, governance, approval, and remediation.
- [x] Present the workflow sequentially in the UI: traces, metrics, threshold/anomaly, alert, RAG/RCA, approval, remediation, governance.
- [x] Document Teams webhook configuration and local simulation mode.
- [x] Run `uv run pytest -q`, build Docker, start the stack, and verify `/health`.

MLflow remains optional and will not block completion of the five mandatory requirements.
