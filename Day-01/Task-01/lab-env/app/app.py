"""Sample service for the AIOps labs.

Exposes Prometheus metrics, writes JSON logs, and has switchable failure modes
(latency, errors, cpu) so we can generate realistic incidents on demand.
"""
import json
import logging
import math
import os
import random
import threading
import time

from flask import Flask, Response, g, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

LOG_PATH = os.environ.get("LOG_PATH", "/var/log/app/app.log")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        payload.update(getattr(record, "fields", {}))
        return json.dumps(payload)


logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
for handler in (logging.FileHandler(LOG_PATH), logging.StreamHandler()):
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)

# Control-plane events go to a file Promtail does NOT ship, so learners must
# diagnose from symptoms and cannot just read "chaos toggled" in Loki.
CONTROL_LOG_PATH = os.environ.get("CONTROL_LOG_PATH", "/var/log/chaos-control.log")
control_logger = logging.getLogger("control")
control_logger.setLevel(logging.INFO)
control_logger.addHandler(logging.FileHandler(CONTROL_LOG_PATH))

REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "endpoint", "status"])
LATENCY = Histogram(
    "request_latency_seconds",
    "Request latency",
    ["endpoint"],
    buckets=(0.025, 0.05, 0.1, 0.25, 0.5, 0.75, 1, 1.5, 2.5, 5),
)

# Failure modes that can be toggled at runtime.
state = {"latency": False, "errors": False, "cpu": False}
# A full reset simulates a service restart: the app answers 503 for this many seconds.
RESTART_SECONDS = 20
restart_until = 0.0
app = Flask(__name__)


def burn_cpu():
    while state["cpu"]:
        for i in range(200000):
            math.sqrt(i)
        time.sleep(0.001)


@app.before_request
def start_timer():
    g.start = time.time()


@app.after_request
def record(response):
    if request.path == "/metrics" or request.path.startswith(("/chaos/", "/debug/")):
        return response  # keep control-plane calls out of metrics and logs
    endpoint = request.url_rule.rule if request.url_rule else "unmatched"
    duration = time.time() - g.start
    REQUESTS.labels(request.method, endpoint, str(response.status_code)).inc()
    LATENCY.labels(endpoint).observe(duration)
    level = logging.ERROR if response.status_code >= 500 else logging.INFO
    logger.log(
        level,
        "request",
        extra={"fields": {
            "endpoint": endpoint,
            "status": response.status_code,
            "duration_ms": round(duration * 1000, 1),
        }},
    )
    return response


@app.get("/")
def index():
    return jsonify(service="sample-app", status="ok")


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.get("/work")
def work():
    if time.time() < restart_until:
        return jsonify(error="service restarting"), 503
    if state["latency"]:
        time.sleep(random.uniform(0.8, 1.5))
    else:
        time.sleep(random.uniform(0.02, 0.08))
    if state["errors"] and random.random() < 0.5:
        logger.error("database connection timeout", extra={"fields": {"component": "db"}})
        return jsonify(error="upstream failure"), 500
    return jsonify(result="done")


@app.post("/chaos/reset")
def chaos_reset():
    global restart_until
    for key in state:
        state[key] = False
    restart_until = time.time() + RESTART_SECONDS  # blast radius of the broadest fix
    control_logger.info("chaos reset")
    return jsonify(ok=True)


@app.post("/chaos/<mode>/<action>")
def chaos(mode, action):
    if mode not in state or action not in ("on", "off"):
        return jsonify(error="unknown mode or action"), 400
    was_on = state[mode]
    state[mode] = action == "on"
    if mode == "cpu" and state[mode] and not was_on:
        threading.Thread(target=burn_cpu, daemon=True).start()
    control_logger.info("chaos %s %s", mode, action)
    return jsonify(ok=True)


@app.post("/debug/log")
def debug_log():
    """Lab only: write an arbitrary line into the app log (used to test prompt injection via logs)."""
    message = (request.get_json(silent=True) or {}).get("msg", "")[:500]
    logger.warning(message, extra={"fields": {"component": "app"}})
    return jsonify(ok=True)


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
