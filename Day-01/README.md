# AIOps — Day 1

## What I learned

Day 1 introduced the basics of monitoring an application using metrics and
logs, then using those signals to investigate an incident.

### Lab architecture

The lab runs five Docker services:

- **Application** — generates traffic, metrics, and JSON logs.
- **Prometheus** — collects and stores numerical metrics.
- **Loki** — stores and searches application logs.
- **Promtail** — reads application log files and sends them to Loki.
- **Grafana** — displays Prometheus metrics and Loki logs in dashboards.

The application and Promtail share the `applogs` Docker volume. The
application writes logs to the volume, and Promtail reads them.

### Metrics and logs

- **Metrics** are numerical measurements, such as request rate, latency,
  CPU usage, and error rate.
- **Logs** are detailed records of individual events, such as an endpoint,
  HTTP status, and request duration.
- Metrics help identify trends and abnormal behavior.
- Logs help explain what happened for individual requests.

### Prometheus queries

I learned how to use PromQL to investigate application health:

- Request rate using `rate()` and `sum()`.
- P95 latency using `histogram_quantile()`.
- CPU usage using `process_cpu_seconds_total`.
- Error ratio by dividing 5xx request rate by total request rate.

### Loki queries

I learned how to use LogQL to search logs:

```logql
{job="app"}
```

This selects application logs. JSON logs can be parsed and filtered, for
example to find requests slower than 100 milliseconds:

```logql
{job="app"} | json | duration_ms > 100
```

### Grafana dashboard

I created a dashboard with four time-series panels:

1. Request rate
2. P95 latency
3. Process CPU usage
4. Error ratio

The dashboard was configured for the last 15 minutes and refreshed every
5 seconds.

### Mystery challenge result

The challenge injected a CPU fault into the application. The evidence was:

- CPU usage increased to approximately 0.75 CPU cores.
- Requests continued returning HTTP `200`.
- The error ratio remained at `0%`.
- P95 latency remained approximately `95 ms`.

The diagnosis was excessive CPU consumption. The availability/error budget
was not burned because there were no failed requests. A latency budget would
only be affected if the SLO latency limit were below approximately 95 ms.

## Key lessons

- Always compare current values with a known normal baseline.
- Do not diagnose an incident from one metric alone.
- Use metrics to identify the abnormal signal.
- Use logs to confirm what happened at request level.
- Support every diagnosis with a number or an actual log entry.
- A resource problem does not always immediately cause user-visible errors.
- SLO and error-budget impact depends on the SLO definition.
