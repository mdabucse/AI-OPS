# AIOps Stream — Day 1 Lab Runbook

| | |
|---|---|
| **Audience** | Trainees |
| **Duration** | 105 minutes |
| **Session** | Day 1, S2 — Metrics, Logs and Traces |

---

## How to use this runbook

Follow each step in order, top to bottom. No background knowledge is assumed — every action is written out in full, including exact commands and exact clicks. Concepts are covered separately by your trainer; this document only tells you *what to do*.

If any step produces something other than what's listed under **Expected**, stop and raise your hand. Do not try to self-diagnose during the lab — flag it and move on with support.

There is no spare time built into this schedule. If you fall behind, each step that has a shortcut says so explicitly.

---

## Step 0 — First-time environment setup
**Time: 15-20 minutes — only needed once, skip if already done**

1. Unzip the `lab-env` folder you received anywhere on your laptop (e.g. your Desktop).
2. Install Docker Desktop if you don't already have it: go to docker.com, download it, install it, open it once, and wait until it shows "Docker Desktop is running".
3. Open a terminal (Mac/Linux: Terminal; Windows: PowerShell) and check Python is installed:
   ```
   python3 --version
   ```
   **Expected:** `Python 3.x.x`. If this command isn't recognized, install Python from python.org first, then retry.
4. Move into the folder:
   ```
   cd path/to/lab-env
   ```
   (Replace `path/to/lab-env` with wherever you unzipped it — e.g. `cd ~/Desktop/lab-env`.)
5. Create and activate a virtual environment:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   ```
   On Windows PowerShell, use instead: `.venv\Scripts\Activate.ps1`
   **Expected:** your terminal prompt now shows `(.venv)` at the start of the line.
6. Install the required packages:
   ```
   pip install --upgrade pip
   pip install -r requirements-core.txt
   ```
   This takes a few minutes and prints a lot of scrolling text — that's normal.
7. Start the lab stack:
   ```
   docker compose up -d --build
   ```
   **The first time only**, this downloads several Docker images and can take 5-10 minutes depending on your internet connection. Let it finish completely before moving on.

Once Step 0 is done, continue to Step 1. You won't need to repeat Step 0 again for the rest of this course.

---

## Step 1 — Start and verify the stack
**Time: 10 minutes**

1. Open a terminal and run:
   ```
   cd AIOps-Curriculum/lab-env
   docker compose ps
   ```
   **Expected:** five rows — `app`, `prometheus`, `loki`, `promtail`, `grafana` — each marked `running` / `Up`.

2. Run:
   ```
   curl http://localhost:8000/health
   ```
   **Expected:** `{"status":"ok"}`

3. Run:
   ```
   curl -s http://localhost:8000/metrics | head
   ```
   **Expected:** several lines beginning `# HELP`

4. Run:
   ```
   curl http://localhost:3100/ready
   ```
   **Expected:** `ready`. If not, wait 15 seconds and retry.

5. In a browser, open `http://localhost:9090/targets`.
   **Expected:** a row labeled `app` with a green **UP** badge.

6. In a browser, open `http://localhost:3000` and log in with username `admin`, password `admin`. Click **Connections → Data sources**.
   **Expected:** both **Prometheus** and **Loki** already listed.

> If any check above fails, stop here and get your trainer before continuing.

---

## Step 2 — Start background traffic
**Time: runs for the rest of the lab**

1. Open a **second** terminal (keep the first one open).
2. Run:
   ```
   while true; do curl -s http://localhost:8000/work > /dev/null; sleep 0.2; done
   ```
3. Leave this running, minimized, until Step 8. Every query in this lab depends on recent traffic being present.

---

## Step 3 — Query Prometheus
**Time: 25 minutes**

1. Open `http://localhost:9090/graph`.
2. Enter each query below one at a time, pressing **Enter** after each, and record the value shown.

   | # | Query |
   |---|---|
   | 1 | `sum(rate(http_requests_total{endpoint="/work"}[1m]))` |
   | 2 | `histogram_quantile(0.95, sum(rate(request_latency_seconds_bucket{endpoint="/work"}[1m])) by (le))` |
   | 3 | `rate(process_cpu_seconds_total[1m])` |
   | 4 | `sum(rate(http_requests_total{endpoint="/work",status=~"5.."}[1m])) / sum(rate(http_requests_total{endpoint="/work"}[1m]))` |

3. Keep these four values — your trainer will ask for them.

---

## Step 4 — Query Loki (logs)
**Time: 15 minutes**

1. In Grafana, click **Explore** (compass icon, left-hand menu).
2. Confirm the data-source dropdown at the top reads **Loki**. If it reads "Prometheus", change it.
3. Enter:
   ```
   {job="app"}
   ```
   Press **Shift + Enter**, or click **Run query**.
   **Expected:** a list of JSON-formatted log lines with fields such as `endpoint`, `status`, `duration_ms`.
4. Enter:
   ```
   {job="app"} | json | duration_ms > 100
   ```
   Run it again.
   **Expected right now:** no results. This is correct — record it as a finding, not an error.

---

## Step 5 — Build the Grafana dashboard
**Time: 25 minutes**

1. Click **Dashboards → New → New Dashboard**.
2. Click **Add visualization**, choose **Prometheus** as the data source.
3. Paste this query, then click **Apply**:
   ```
   sum(rate(http_requests_total{endpoint="/work"}[1m]))
   ```
4. Click **Add → Visualization** to create a second panel. Paste, then **Apply**:
   ```
   sum(rate(http_requests_total{endpoint="/work",status=~"5.."}[1m])) / sum(rate(http_requests_total{endpoint="/work"}[1m]))
   ```
5. Add a third panel. Paste, then **Apply**:
   ```
   histogram_quantile(0.95, sum(rate(request_latency_seconds_bucket{endpoint="/work"}[1m])) by (le))
   ```
6. Add a fourth panel. Paste, then **Apply**:
   ```
   rate(process_cpu_seconds_total[1m])
   ```
7. Set the dashboard time range (top right) to **Last 15 minutes**, and the refresh interval to **5s**.
8. Click **Save dashboard**, name it exactly `AIOps Day 1`, and click **Save**.

> **Behind schedule?** Skip to **Dashboards → New → Import** and upload `AIOps-Day1-dashboard.json`, provided by your trainer, instead of building panels manually.

---

## Step 6 — Retrieve your incident dataset
**Time: 10 minutes — mandatory, do not skip**

1. In your first terminal, run:
   ```
   cp data/golden/incident_dataset.csv data/incident_dataset.csv
   ```
2. Run:
   ```
   python -c "import pandas as pd; d=pd.read_csv('data/incident_dataset.csv'); print(d.shape); print(d['incident_type'].value_counts())"
   ```
3. **Expected:** shape near `(265, 8)`; counts near `normal 157`, and `latency`, `errors`, `cpu` each around 36.
4. If the output errors or the numbers are far off, tell your trainer immediately. This file is required for Days 3 and 4.

---

## Step 7 — Mystery challenge
**Time: 15 minutes, if scheduled**

Your trainer will tell you when to begin. This step runs entirely on your own laptop — no coordination or setup with anyone else is needed.

1. Read the problem statement your trainer provides (`Day-1-Problem-Statement.md`).
2. From the `day-1` folder, run:
   ```
   python3 day1_mystery_challenge.py
   ```
   A fault is picked at random, right there, and injected into your own local app.
3. Using your dashboard and any query from Steps 3-4, investigate while the countdown runs. There is no command to reveal the answer — the fault clears itself automatically when time is up.
4. When the script asks, type your diagnosis: which signal(s) changed, what the logs showed (if anything), your diagnosis and the evidence behind it, and whether this burns the SLO/error budget you wrote earlier today.
5. The script saves your answers to a file named `diagnosis_<timestamp>.json`. This file also records the real answer and a verification hash — but only after your diagnosis is already written, so you can't go back and change your answer once you see it. **Submit the file to your trainer exactly as generated.**

> Do not open `day1_mystery_challenge.py` in an editor before completing the exercise. The fault is random each run, so reading the code won't tell you this run's answer — but it defeats the point of the exercise for you.

---

## Step 8 — End-of-day verification
**Time: 10 minutes**

Confirm with your trainer that you have:

- [ ] A saved Grafana dashboard named exactly `AIOps Day 1`, with four live-updating panels
- [ ] `data/incident_dataset.csv` present in your `lab-env` folder, approximately 265 rows
- [ ] Verbally answered your trainer's recap questions

Leave your stack running and your dataset file in place — Day 2 continues from exactly where you stop today.
