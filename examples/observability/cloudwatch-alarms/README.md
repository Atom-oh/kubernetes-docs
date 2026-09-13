# CloudWatch alarm examples

Reviewed on 2026-09-13. These examples support the Korean and English CloudWatch
Alarms chapters.

`event_normalizer.py` handles **EventBridge CloudWatch Alarm State Change** events.
Its input has `detail.configuration.metrics[*].metricStat.metric.dimensions` as
an object. SNS alarm messages use a different envelope and dimension format.
Direct CloudWatch-to-Lambda actions also have their own envelope.

The normalizer returns inspection data only. It does not reboot instances,
restart workloads, send notifications, or verify the sender's identity.
An actual Lambda target needs a resource policy scoped to the EventBridge rule,
and any remediation needs its own authorization, current-state check, target
allowlist, idempotency, and recovery procedure.

Run the local tests without AWS credentials:

```bash
python3 -m unittest discover -s examples/observability/cloudwatch-alarms/tests -v
```

The tests cover real EventBridge dimension shape, expression queries, composite
alarms, recovery events, mismatched identity fields, malformed data, and input
immutability. They do not execute an AWS alarm evaluator or a Lambda invocation.

Primary reference:
[CloudWatch alarm events in EventBridge](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch-and-eventbridge.html).
