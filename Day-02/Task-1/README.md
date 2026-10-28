# Day 2 Task 1 — Login Is Slow

This project is a small AIOps incident helper. It detects a login-latency
problem, asks an AI model to explain the evidence, recommends a fix, and
waits for human approval before applying a simulated remediation.

## Scenario

- Normal login P95 latency: `0.12` seconds
- Current login P95 latency: `1.35` seconds
- Database pool maximum: `20`
- Database connections in use: `20`
- Waiting login requests: `18`

The expected diagnosis is that the database connection pool is exhausted and
login requests are waiting in a queue.

## Setup

From this directory, install the development environment:

```bash
uv sync
```

For the live model demonstration, start Ollama in another terminal and pull
the default model:

```bash
ollama serve
ollama pull qwen3:8b
```

The model can be changed with:

```bash
export OLLAMA_MODEL=qwen3:4b
```

## Run the helper

The helper uses the local Ollama model by default:

```bash
uv run python day2_helper.py \
  --scenario scenario.json \
  --audit decision_log.json
```

The helper prints the evidence, diagnosis, recommendation, and risk, then
asks:

```text
Apply this fix? [yes/no]:
```

Enter `yes` or `y` to apply the simulated pool-size change from `20` to `30`.
Enter anything else to reject the fix. A rejected fix does not change the
scenario.

The decision is saved to `decision_log.json`.

## Run tests without Ollama

The test suite uses a fake model client, so an Ollama server is not required:

```bash
uv run pytest -q
```

## Safety design

- The model only produces a diagnosis and recommendation.
- Python validates the model response before it can be used.
- The model cannot execute shell commands.
- Human approval is required before remediation.
- Remediation changes only the local scenario fixture; it does not connect to
  or modify a real database.
- Audit output records the diagnosis, recommendation, approval, and action.
