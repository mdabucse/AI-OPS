# AIOps Capstone RCA Agent

This local training application demonstrates an end-to-end AIOps workflow:

```text
login → traces/logs → dynamic threshold → anomaly detection → alert → RAG RCA → approval → remediation → governance
```

It uses FastAPI, PostgreSQL, SQLAlchemy, a browser dashboard, local runbooks, and a deterministic statistical anomaly detector.

## Run with Docker

```bash
docker compose up --build
```

Open <http://localhost:8000/login>.

Training-only credentials:

- Username: `admin`
- Password: `admin`

Click **Run RCA simulation**. The dashboard reveals the evidence step by step. Approving the recommendation changes the simulated metrics from P95 `1.35s` and `18` waiting requests to P95 `0.12s` and `0` waiting requests.

## Alerting

Without configuration, alerts use local Teams simulation mode and are stored in PostgreSQL with status `simulated`.

To send a real Microsoft Teams webhook notification, create a local `.env` file from `.env.example` and set:

```bash
TEAMS_WEBHOOK_URL=https://your-teams-webhook-url
ALERT_CHANNEL=teams
```

Failed webhook delivery is stored as `failed`; the application never reports a failed notification as sent.

## Run tests locally

```bash
docker compose up -d db
uv sync
uv run pytest -q
```

The local test configuration uses `localhost:5433`; the app container uses `db:5432`.

## API highlights

- `GET /health`
- `POST /api/simulations/day2/start`
- `GET /api/metrics?run_id=<id>`
- `GET /api/rag/search?q=database+pool`
- `GET /api/alerts?run_id=<id>`
- `GET /api/governance?run_id=<id>`
- `POST /api/approvals/<approval_id>/approve`
- `POST /api/approvals/<approval_id>/reject`

MLflow is optional and is not required for the mandatory workflow.
