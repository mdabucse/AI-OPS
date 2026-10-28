# Day 2 Login Slow AI Helper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python AIOps helper that detects slow login performance, identifies database connection-pool exhaustion from supplied telemetry and logs, recommends a safe fix, and applies the fix only after explicit human approval.

**Architecture:** Use a deterministic local scenario fixture as the source of telemetry, a small Python evidence layer to calculate the latency change and pool saturation, an Ollama adapter to explain the evidence, and a command-line approval gate before simulated remediation. The model recommends actions; Python owns validation, approval, remediation, and audit logging.

**Tech Stack:** Python 3.11+, `uv`, Ollama HTTP API, `qwen3:8b` by default with `OLLAMA_MODEL` override, JSON fixtures, `pytest`.

**Spec:** `Day-02/Task-1/AIOps_Training-Day2-Task.docx`

## Global Constraints

- The helper must identify the known scenario: login P95 increases from approximately `0.12` seconds to `1.35` seconds.
- The diagnosis must use the evidence that the database pool is full and login requests are waiting in a queue.
- The default local model is `qwen3:8b`; support an override through `OLLAMA_MODEL`.
- The model must return structured diagnosis data; invalid or unparseable model output must not trigger remediation.
- The helper must ask for explicit human approval before applying any fix.
- A `no`/`n` response must make no state change.
- Remediation is simulated by updating the local scenario/configuration data; do not modify a real database or production service.
- Every run must record the diagnosis, recommendation, approval, and action taken in an audit JSON file.
- Tests must run without an Ollama server by using a fake model client.

## Review Focus

- Missing or malformed telemetry: the CLI should report a useful validation error and exit without calling the model.
- Zero or missing database-pool capacity: the helper should not divide by zero or claim pool saturation without valid capacity data.
- Ollama unavailable or timed out: the helper should explain the failure and never offer an executable remediation based on incomplete evidence.
- Invalid model JSON or confidence outside `0.0..1.0`: the diagnosis should be rejected and no fix should be applied.
- Human rejection or unexpected approval text: the helper should treat it as rejection and leave the scenario unchanged.

---

### Task 1: Create the scenario fixture and evidence model

**Files:**
- Create: `Day-02/Task-1/scenario.json`
- Create: `Day-02/Task-1/day2_models.py`
- Create: `Day-02/Task-1/tests/test_day2_models.py`
- Create or modify: `Day-02/Task-1/pyproject.toml`

**Interfaces:**
- `Telemetry.from_dict(data: dict) -> Telemetry`
- `Telemetry.validate() -> None`
- `Evidence.from_telemetry(telemetry: Telemetry) -> Evidence`
- `Evidence.latency_multiplier() -> float`
- `Evidence.pool_saturation() -> float`

- [x] **Step 1: Write failing model-validation tests**

  Add tests for:

  - The supplied scenario loads with `baseline_p95_latency_seconds == 0.12` and `current_p95_latency_seconds == 1.35`.
  - Pool saturation is `1.0` when `db_pool_in_use == db_pool_max`.
  - Latency multiplier is `11.25` for `1.35 / 0.12`.
  - Missing `current` data raises `ValueError`.
  - A zero or negative pool maximum raises `ValueError`.

- [x] **Step 2: Run the focused tests and verify they fail**

  Run:

  ```bash
  cd Day-02/Task-1
  uv run pytest tests/test_day2_models.py -v
  ```

  Expected: failure because the models and fixture loader do not exist yet.

- [x] **Step 3: Implement `Telemetry`, `Evidence`, and the fixture**

  Use dataclasses and explicit validation. Store logs as `list[str]`. Preserve the exact task values: normal P95 `0.12`, current P95 `1.35`, pool maximum `20`, pool in use `20`, and waiting requests `18`.

- [x] **Step 4: Run the focused tests and verify they pass**

  Run the same `pytest` command. Expected: all model tests pass.

### Task 2: Add the Ollama diagnosis adapter

**Files:**
- Create: `Day-02/Task-1/diagnosis.py`
- Create: `Day-02/Task-1/tests/test_diagnosis.py`
- Create or modify: `Day-02/Task-1/requirements.txt`

**Interfaces:**
- `Diagnosis.from_dict(data: dict) -> Diagnosis`
- `build_prompt(evidence: Evidence) -> str`
- `OllamaClient.diagnose(evidence: Evidence) -> Diagnosis`
- `FakeModelClient.diagnose(evidence: Evidence) -> Diagnosis`

- [x] **Step 1: Write failing diagnosis tests**

  Test that:

  - The prompt contains the latency baseline, current latency, pool capacity, active connections, waiting requests, and logs.
  - A valid model response becomes a `Diagnosis` object.
  - Missing required fields raise `ValueError`.
  - Confidence values below `0.0` or above `1.0` raise `ValueError`.
  - The fake client returns the expected database-pool diagnosis without requiring Ollama.

- [x] **Step 2: Run the focused tests and verify they fail**

  Run:

  ```bash
  uv run pytest tests/test_diagnosis.py -v
  ```

  Expected: failure because the diagnosis interfaces do not exist yet.

- [x] **Step 3: Implement structured diagnosis**

  Define these fields exactly:

  ```text
  user_impact: str
  root_cause: str
  evidence: list[str]
  recommended_fix: str
  risk: str
  confidence: float
  ```

  Use the Ollama `/api/chat` endpoint with the configured model and request JSON-only output. Parse and validate the response before returning it. Default to `qwen3:8b`; read `OLLAMA_MODEL` and `OLLAMA_URL` from the environment.

- [x] **Step 4: Run the focused tests and verify they pass**

  Run the same `pytest` command. Expected: all diagnosis tests pass without a live Ollama server.

### Task 3: Implement approval and simulated remediation

**Files:**
- Create: `Day-02/Task-1/remediation.py`
- Create: `Day-02/Task-1/tests/test_remediation.py`

**Interfaces:**
- `FixPlan.from_diagnosis(diagnosis: Diagnosis) -> FixPlan`
- `request_approval(input_fn: Callable[[str], str]) -> bool`
- `apply_fix(telemetry: Telemetry, fix: FixPlan) -> RemediationResult`
- `write_audit_record(path: Path, record: AuditRecord) -> None`

- [x] **Step 1: Write failing approval tests**

  Test that:

  - `yes` and `y` return approval.
  - `no`, `n`, blank input, and unexpected input return rejection.
  - Rejection leaves `db_pool_max` unchanged.
  - Approval changes the simulated pool size from `20` to `30`.
  - The audit record includes diagnosis, recommendation, human approval, and action taken.

- [x] **Step 2: Run the focused tests and verify they fail**

  Run:

  ```bash
  uv run pytest tests/test_remediation.py -v
  ```

  Expected: failure because the approval and remediation interfaces do not exist yet.

- [x] **Step 3: Implement the approval gate**

  Display the diagnosis, evidence, recommendation, and risk before asking:

  ```text
  Apply this fix? [yes/no]:
  ```

  Treat every answer other than `yes` or `y` as rejection. Apply only the fixed, simulated change to the local scenario state. Never execute arbitrary model-generated shell commands.

- [x] **Step 4: Run the focused tests and verify they pass**

  Run the same `pytest` command. Expected: all approval and remediation tests pass.

### Task 4: Wire the command-line helper together

**Files:**
- Create: `Day-02/Task-1/day2_helper.py`
- Create: `Day-02/Task-1/tests/test_cli.py`

**Interfaces:**
- `run(input_path: Path, audit_path: Path, model_client: ModelClient) -> int`
- CLI command: `uv run python day2_helper.py --scenario scenario.json --audit decision_log.json`

- [x] **Step 1: Write failing orchestration tests**

  Test that a run:

  - Loads and validates the scenario.
  - Reports abnormal latency.
  - Sends evidence to the model client.
  - Prints the diagnosis and recommendation.
  - Rejects a fix without changing the scenario when approval is `no`.
  - Applies the simulated fix and writes an audit record when approval is `yes`.
  - Returns a non-zero exit code for invalid input or invalid model output.

- [x] **Step 2: Run the focused tests and verify they fail**

  Run:

  ```bash
  uv run pytest tests/test_cli.py -v
  ```

  Expected: failure because the CLI entry point does not exist yet.

- [x] **Step 3: Implement the orchestration flow**

  Keep the order explicit: load data, validate data, calculate evidence, diagnose, display recommendation, request approval, optionally apply fix, write audit record. Inject the model client so tests never depend on a running Ollama server.

- [x] **Step 4: Run the focused tests and verify they pass**

  Run:

  ```bash
  uv run pytest tests/test_cli.py -v
  ```

  Expected: all CLI tests pass.

### Task 5: Add documentation and end-to-end verification

**Files:**
- Create or modify: `Day-02/Task-1/README.md`
- Create or modify: `Day-02/Task-1/requirements.txt`
- Create: `Day-02/Task-1/tests/test_end_to_end.py`

- [x] **Step 1: Write the end-to-end verification test**

  Run the helper with the fake model client twice:

  - Approval `no`: verify no remediation occurs and the audit record says `rejected`.
  - Approval `yes`: verify the pool size changes from `20` to `30` and the audit record says `applied`.

- [x] **Step 2: Implement dependency and run instructions**

  Document:

  ```bash
  uv sync
  ollama serve
  ollama pull qwen3:8b
  uv run python day2_helper.py --scenario scenario.json --audit decision_log.json
  ```

  Explain that the remediation is simulated and that the helper must not be pointed at a real production database.

- [x] **Step 3: Run all tests**

  Run:

  ```bash
  uv run pytest -q
  ```

  Expected: all tests pass without Ollama.

- [ ] **Step 4: Run the live Ollama demonstration**

  Start Ollama, pull the configured model, and run the CLI. Capture one rejected-fix run and one approved-fix run for the submission.

- [x] **Step 5: Review the submission artifacts**

  Confirm that the folder contains:

  - Working Python helper
  - Scenario fixture
  - Tests
  - README with setup and usage instructions
  - At least one audit JSON output
  - Evidence that `no` does not change state and `yes` applies only the simulated fix

