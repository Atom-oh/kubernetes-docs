# Observability optimization examples

These files accompany the Korean/English optimization guide. They are bounded
configuration examples, not a complete Kubernetes deployment.

- `prometheus.yaml` scrapes a synthetic application at loopback port8080 and
  selectively drops buckets of `lab_http_request_duration_seconds`; edit the
  target for your environment. It retains non-histogram metrics, `+Inf`, `_sum`,
  `_count` and the 500ms SLO bucket. Enable exemplar storage with the supported
  Prometheus command-line feature switch when using the exemplar settings.
- `slo-rules.yaml` uses the lab application's `lab_http_*` metrics and a
  request-based 99.9% objective. It distinguishes short-window burn from a
  30-day request-weighted budget. Check collection completeness and retention;
  zero/missing traffic is not perfect availability. Queries group one cluster
  by service; add consistent cluster dimensions for centralized data.
- `alertmanager.yaml` parses routing, guarded inhibition and Asia/Seoul schedules.
  Its receiver has no integrations and sends nothing. Configure approved
  contacts and routing before operational use.
- `collector-tail-local.yaml` listens only on loopback14318. Set `OTLP_TEST_SINK`
  to a local OTLP HTTP receiver for a synthetic experiment. Its small buffer and
  two-second wait are test settings, not production capacity guidance. It removes
  only one named attribute and does not promise complete sensitive-data removal.
- `opencost-values.yaml` is for chart2.5.31/app1.121.2 and an existing Prometheus.
  Replace the endpoint and provide required metrics/authentication. Cloud Cost
  is disabled; allocation is not reconciliation with an AWS invoice.

With Prometheus3.14.0, Alertmanager0.34.0 and Collector Contrib0.160.0:

```bash
promtool check config prometheus.yaml
promtool check rules slo-rules.yaml
amtool check-config alertmanager.yaml
OTLP_TEST_SINK=http://127.0.0.1:14319 \
  otelcol-contrib validate --config collector-tail-local.yaml
```

Native audit tests used loopback servers and synthetic data. They did not install
Kubernetes/eBPF agents, generate a cloud bill or send external notifications.
