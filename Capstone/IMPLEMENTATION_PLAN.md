# Capstone RCA Agent Foundation and Simulation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a simple local demo with one dummy login account, a PostgreSQL-backed Day 2 slow-login simulator, a log viewer, an RCA approval queue, and human-approved simulated remediation.

**Architecture:** Use one FastAPI application for the backend and server-rendered HTML/JavaScript for the frontend. Use one dummy credential from environment variables for local login; do not build a user-management system. PostgreSQL runs in Docker and stores simulated logs, RCA findings, approval requests, and audit events. After login, the user starts the Day 2 scenario: login P95 increases from `0.12s` to `1.35s` because the database connection pool is full.

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, Jinja2, vanilla JavaScript, SQLAlchemy 2, psycopg, PostgreSQL 16 in Docker, Alembic, pytest, `uv`.

**Spec:** User-provided Capstone requirements plus `Day-02/Task-1/AIOps_Training-Day2-Task.docx`.

## Global Constraints

- PostgreSQL must run from Docker; the application must read its connection string from `DATABASE_URL`.
- The demo must use exactly one local dummy credential from `DEMO_USERNAME` and `DEMO_PASSWORD`; it must never connect to a real production database.
- The simulated Day 2 incident must preserve these values: baseline P95 `0.12s`, incident P95 `1.35s`, pool maximum `20`, active connections `20`, waiting requests `18`.
- The UI must show application logs and RCA approval requests in the same authenticated session.
- Only a user with a valid local demo session may view logs or approve/reject actions.
- Remediation must be simulated and must require explicit human approval.
- Every simulation, RCA result, approval decision, and remediation result must be traceable through database audit records.
- The later Capstone components—RAG, dynamic thresholds, anomaly detection, alerting, and governance—must consume the same persisted telemetry and audit interfaces rather than bypassing them.

## Review Focus

- Unauthenticated access: login, logs, approvals, and remediation endpoints must reject requests without a valid session.
- Duplicate approval: approving or rejecting the same request twice must not apply remediation twice.
- Simulation repeatability: starting a run must create a new run and not overwrite earlier logs or decisions.
- Database outage: the UI must show a useful error and must not claim that a simulation or remediation succeeded.
- Approval safety: rejection, expired requests, and unexpected approval values must leave simulated system state unchanged.

---

## Phase 1 — Login, PostgreSQL, Simulation, Logs, and Approvals

### Task 1: Scaffold the Capstone application and PostgreSQL

**Files:**
- Create: `Capstone/docker-compose.yml`
- Create: `Capstone/pyproject.toml`
- Create: `Capstone/requirements.txt`
- Create: `Capstone/.env.example`
- Create: `Capstone/app/__init__.py`
- Create: `Capstone/app/config.py`
- Create: `Capstone/app/main.py`
- Create: `Capstone/tests/test_health.py`

**Interfaces:**
- `GET /health -> {"status": "ok"}`
- `Settings.database_url: str`
- `Settings.demo_username: str`
- `Settings.demo_password: str`

- [ ] **Step 1: Write the failing health and configuration tests**

  Verify that the application exposes `/health` and that the database URL is read from `DATABASE_URL` rather than hard-coded.

- [ ] **Step 2: Run the focused tests and verify they fail**

  ```bash
  cd Capstone
  uv run pytest tests/test_health.py -v
  ```

  Expected: failure because the application scaffold does not exist.

- [ ] **Step 3: Add the FastAPI scaffold and Docker PostgreSQL service**

  Configure PostgreSQL 16 with a named volume, healthcheck, database `aiops`, user `aiops`, and password supplied through environment variables. Put `DEMO_USERNAME=admin` and `DEMO_PASSWORD=admin` in `.env.example` for the local training demo. Do not commit a real `.env` file.

- [ ] **Step 4: Run PostgreSQL and verify health**

  ```bash
  docker compose up -d db
  uv run pytest tests/test_health.py -v
  ```

  Expected: PostgreSQL is healthy and the health test passes.

### Task 2: Design the PostgreSQL schema and audit storage

**Files:**
- Create: `Capstone/app/db.py`
- Create: `Capstone/app/models.py`
- Create: `Capstone/app/migrations/`
- Create: `Capstone/tests/test_database.py`

**Interfaces:**
- `get_session() -> Iterator[Session]`
- `create_audit_event(session, event_type: str, actor: str, details: dict) -> AuditEvent`

**Tables:**

- `simulation_runs`: run ID, scenario name, status, start/end timestamps.
- `telemetry_events`: run ID, metric name, value, unit, timestamp.
- `application_logs`: run ID, level, message, endpoint, status, duration, timestamp.
- `rca_findings`: run ID, root cause, evidence, recommendation, confidence, model name.
- `approval_requests`: finding ID, status, requested action, decided by, decided timestamp.
- `audit_events`: actor, event type, correlation ID, JSON details, timestamp.

- [ ] **Step 1: Write failing schema tests**

  Test that a simulation run can own logs and metrics, and audit events preserve a correlation ID.

- [ ] **Step 2: Run the focused tests and verify they fail**

  ```bash
  uv run pytest tests/test_database.py -v
  ```

- [ ] **Step 3: Implement SQLAlchemy models and migrations**

  Do not create a users table. Authentication is handled by the single environment-configured demo credential in the application settings.

- [ ] **Step 4: Run the tests against the Docker PostgreSQL database**

  Expected: schema creation, inserts, relationships, and audit writes pass.

### Task 3: Build the Day 2 login-incident simulator

**Files:**
- Create: `Capstone/app/simulation.py`
- Create: `Capstone/app/routes/simulation.py`
- Create: `Capstone/tests/test_simulation.py`

**Interfaces:**
- `start_login_scenario(session: Session, actor: str) -> SimulationRun`
- `generate_day2_events(session: Session, run_id: UUID) -> SimulationRun`
- `GET /api/simulations/{run_id}`
- `POST /api/simulations/day2/start`

- [ ] **Step 1: Write failing simulator tests**

  Assert that a Day 2 run creates:

  - Normal P95 `0.12s` events.
  - Incident P95 `1.35s` events.
  - Pool maximum `20` and active connections `20`.
  - `18` waiting requests.
  - Successful HTTP 200 login logs with high latency.
  - A unique run ID and correlation ID.

- [ ] **Step 2: Run the focused tests and verify they fail**

  ```bash
  uv run pytest tests/test_simulation.py -v
  ```

- [ ] **Step 3: Implement repeatable simulation generation**

  The simulation must append records for each run and must not delete previous runs. It should return a summary containing the run ID, current P95, pool saturation, waiting requests, and log count. The login page remains simple and responsive; the slow-login behavior is represented in the simulated telemetry and logs after the user clicks `Simulate slow login`.

- [ ] **Step 4: Run the focused tests and verify they pass**

  Expected: a new simulation produces the exact Day 2 evidence and remains queryable from PostgreSQL.

### Task 4: Build RCA findings and the human approval workflow

**Files:**
- Create: `Capstone/app/rca_agent.py`
- Create: `Capstone/app/routes/approvals.py`
- Create: `Capstone/tests/test_approvals.py`

**Interfaces:**
- `create_rca_finding(session, run_id: UUID, actor: str) -> RcaFinding`
- `create_approval_request(session, finding_id: UUID, actor: str) -> ApprovalRequest`
- `POST /api/approvals/{approval_id}/approve`
- `POST /api/approvals/{approval_id}/reject`
- `GET /api/approvals?status=pending`

- [ ] **Step 1: Write failing approval tests**

  Test that the RCA finding contains the database-pool diagnosis and evidence, approval changes `pending` to `approved`, rejection changes it to `rejected`, and a second decision is refused.

- [ ] **Step 2: Run the focused tests and verify they fail**

  ```bash
  uv run pytest tests/test_approvals.py -v
  ```

- [ ] **Step 3: Implement the RCA and approval transaction**

  Use the existing Day 2 diagnosis logic as the first RCA adapter. Persist the model name, prompt/context hash, evidence, recommendation, and confidence. Approval must be transactional and must create an audit event.

- [ ] **Step 4: Run the focused tests and verify they pass**

  Expected: only one approval decision can succeed for a request, and every decision is auditable.

### Task 5: Build the login page and operations dashboard

**Files:**
- Create: `Capstone/app/auth.py`
- Create: `Capstone/app/routes/auth.py`
- Create: `Capstone/app/routes/ui.py`
- Create: `Capstone/app/templates/login.html`
- Create: `Capstone/app/templates/dashboard.html`
- Create: `Capstone/app/static/app.js`
- Create: `Capstone/app/static/styles.css`
- Create: `Capstone/tests/test_ui_flow.py`

**Interfaces:**
- `GET /login`
- `POST /login`
- `POST /logout`
- `GET /dashboard`
- `GET /api/logs?run_id=<id>`
- `GET /api/metrics?run_id=<id>`

- [ ] **Step 1: Write failing UI-flow tests**

  Test that anonymous users are redirected to login, valid demo credentials reach the dashboard, logs are visible after a simulation, and pending approvals show an Approve and Reject control.

- [ ] **Step 2: Run the focused tests and verify they fail**

  ```bash
  uv run pytest tests/test_ui_flow.py -v
  ```

- [ ] **Step 3: Implement the single-credential login and authenticated UI**

  Compare the submitted username and password with `DEMO_USERNAME` and
  `DEMO_PASSWORD` from settings. On success, issue a signed local session
  cookie containing the demo username. On failure, show a simple login error.
  This is a training-only credential gate, not a production identity system.

  The dashboard should contain:

  - One `Run RCA simulation` button that starts the complete guided workflow.
  - A sequential presentation: traces/log rows first, then metrics, then RCA evidence, then the approval request, then audit history.
  - Current P95 and baseline P95, pool capacity, active connections, and waiting requests revealed at the metrics step.
  - Searchable/filterable log table with trace rows displayed one by one.
  - RCA finding and evidence panel revealed after telemetry is displayed.
  - Pending approval card revealed only after the RCA is ready.
  - Recent audit events revealed after the approval decision.

- [ ] **Step 4: Run the UI-flow tests and verify they pass**

  Expected: the complete local flow works through the browser: login, start simulation, inspect logs, view RCA, approve/reject, and see the audit result.

### Task 6: Add the first end-to-end demo and documentation

**Files:**
- Modify: `Capstone/docker-compose.yml`
- Create: `Capstone/README.md`
- Create: `Capstone/tests/test_end_to_end.py`
- Create: `Capstone/.gitignore`

- [ ] **Step 1: Write the end-to-end test**

  Test the full sequence: login, start simulation, fetch logs, fetch pending approval, reject once, start a fresh simulation, approve once, and verify the audit history.

- [ ] **Step 2: Add app and database Docker services**

  The README must document:

  ```bash
  docker compose up --build
  ```

  and the demo login credentials, local-only warning, and browser URL.

- [ ] **Step 3: Run all tests and the browser demonstration**

  ```bash
  uv run pytest -q
  docker compose up --build
  ```

  Capture screenshots showing the login page, logs, RCA finding, approval controls, and audit trail.

---

## Later Capstone Phases

After Phase 1 is working, extend the same database and API contracts:

1. **RAG completed:** local runbooks, deterministic retrieval, persisted retrieved context, protected search endpoint, and dashboard source display.
2. **Dynamic thresholding completed:** baseline-derived threshold evaluation, persisted threshold history, violation status, API fields, and dashboard display.
3. **Anomaly detection completed:** z-score detector, persisted anomaly scores, model version, API fields, and dashboard display.
4. **Alerting completed:** Teams webhook delivery, local simulation mode, failure tracking, alert API, and dashboard status.
5. **Governance completed:** model/version, prompt/retrieval hashes, threshold status, approval policy, actor, and correlation traceability.
6. Add MLflow tracking as an optional enhancement.

These phases must reuse the Phase 1 telemetry, RCA, approval, and audit records so the final screen recording demonstrates one continuous workflow.
