# Alerting overview validation examples

These files mirror the Korean/English alerting overview. They assume a single
cluster and deduplicated metric series. Replace jobs, labels and thresholds
after inspecting actual exporters. Missing data needs separate monitoring.

`alertmanager.yaml` deliberately has empty receivers: it exercises routing and
inhibition without sending notifications. It is not a production notification
configuration. Configure reviewed integrations and file-mounted credentials
before deploying any receiver.

Validated locally with Prometheus/promtool 3.14.0 and Alertmanager/amtool 0.34.0.
No cluster, AWS resource, real receiver, or incident service was exercised.
