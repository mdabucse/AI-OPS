# Golden dataset

Real output of one full `chaos/run_chaos.py` run (defaults: 6 cycles, 120 s normal, 90 s incident) exported with `tools/export_dataset.py` (5 s step).

- 265 rows: 157 normal, 36 each of latency / errors / cpu
- Columns: `ts, req_rate, err_rate, p95_latency, cpu, incident_type, is_incident, transition`
- Regenerate and replace this file if you change the app, the chaos script, or the export queries.

## The `transition` column

Metrics use `rate(...[1m])`, but labels switch exactly when an incident starts and ends. So the first ~30 s of an incident still look normal, and the ~60 s after it ends still look abnormal. Those 108 rows have an unreliable label and are flagged `transition = True`. Training excludes them by default.

## What to expect on this file (Day 3)

| Setting | Isolation Forest | Logistic regression | Random forest |
|---|---|---|---|
| Default (transitions excluded) | F1 about 0.5-0.6 | about 0.96 | about 1.0 |
| `KEEP_TRANSITIONS=1` | F1 about 0.5-0.6 | about 0.69 | about 0.60 |

The test half (last 50% by time) contains every incident type. The easy default numbers are optimistic: they hide exactly the moments (an incident's first 30 s) where detection delay matters. Use that as a discussion point.
