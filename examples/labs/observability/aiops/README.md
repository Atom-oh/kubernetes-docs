# Observability lab diagnostic reporter

This SNS-triggered Lambda produces a hypothesis for human review. It has no
resource-changing tools, automatic remediation, public webhook or AgentCore
runtime. It accepts native CloudWatch alarm messages and Alertmanager JSON.

The SAM template creates separate encrypted input/output SNS topics, a reporter,
an idempotency table, a failure queue and one SQS backlog alarm. It also creates
an unattached publishing policy for your existing Alertmanager workload role.
The application queue and structured log group must already exist.

The reporter validates alert/service allowlists, reads at most 15 minutes of
configured CloudWatch metrics and aggregated log counts, and sends only those
observations to an explicitly configured Converse model or inference profile.
No raw log messages, arbitrary alert annotations or model-generated queries are
used. Missing sources remain missing; insufficient evidence skips the model.

The log source must contain structured `service` and `level` fields. A successful
query with no matching data does not prove that the application's logging path
is healthy. The sample metrics cover SQS; the collector function also supports
an explicitly configured RDS **instance** identifier. It does not invent AMP
values or X-Ray traces that the lab never collected.

Run the portable tests without AWS credentials or network calls:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
```

To package and deploy in your own approved lab account:

```bash
sam build --template-file template.yaml
sam deploy --guided --capabilities CAPABILITY_IAM
```

Review the change set before executing it. Supply the existing queue/log group,
service name, currently available model/profile ID and its exact required IAM
resource ARNs. Cross-region inference profiles may require both profile and
destination foundation-model ARNs. Managed prompt ARNs are not supported by
this sample's explicit system/inference settings. No secret is a template
parameter, and the reserved `AWS_REGION` variable is not overwritten.

The template deliberately creates no email/SMS subscription. Connect the
**output** topic to the notification system you choose. The function can publish
only to that output topic, and its Lambda subscription belongs only to the
input topic. Do not subscribe the reporter to its own result topic.

For Alertmanager **0.34.0**, merge the following receiver into the configuration
actually loaded by your installed Prometheus/Alertmanager release:

```yaml
receivers:
- name: lab-diagnostics
  sns_configs:
  - topic_arn: REPLACE_WITH_INPUT_TOPIC_ARN
    sigv4:
      region: REPLACE_WITH_REGION
    message: '{{ . | toJson }}'
    send_resolved: true
```

Attach the template's `AlertmanagerPublishPolicyArn` only to the configured
Alertmanager workload role. Ensure that the role can actually be assumed from
the Alertmanager Pod and that the receiver is selected by a route. Configure
the alert's `service` label to match the catalog. `toJson` serializes the
capitalized template fields; the parser also accepts the lowercase webhook
shape. The default human-readable SNS template is not this JSON contract.

Operational boundaries:

- Powertools 3.34.0 deduplicates a successful SNS message ID for 24 hours using
  DynamoDB. Changed payloads under the same ID are rejected. A different SNS
  message ID is a different operation.
- SNS delivery is at least once. Publishing a result and committing idempotency
  state are not an atomic transaction; a crash in that window can duplicate a
  notification. Do not claim exactly-once delivery.
- Lambda concurrency is two, asynchronous retries are two, and event age is
  limited to one hour after Lambda accepts the event. SNS delivery retries are
  a separate mechanism. Inspect both subscription delivery failures and Lambda
  failures in the failure queue.
- Logs Insights polling has a time budget and cancels unfinished queries.
  SDK timeouts, retries and remaining Lambda time further bound work. A timeout
  is a failed/missing observation, never a zero-error measurement.
- Converse uses `maxTokens: 1024`; truncated, blocked or empty output does not
  count as a completed diagnosis. Reports remain hypotheses for human review.
- Current source reads are not a reconstruction of the exact original alarm
  period. The report states the actual observation window.

CloudWatch Investigations is a separate managed workflow. Configure an
investigation group and add its ARN as an alarm action using the official
procedure; this stack does not claim to create investigations:

- [Configure an alarm to create investigations](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Investigations-configure-alarm-procedures.html)
- [Powertools idempotency](https://docs.powertools.aws.dev/lambda/python/latest/utilities/idempotency/)
- [Converse API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html)

Validation so far: Python tests, actual Powertools with an in-memory test store,
botocore Stubber contracts for telemetry/Converse/DynamoDB, and `cfn-lint`.
No AWS deployment, model invocation, real DynamoDB operation, notification
delivery or CloudWatch query execution was performed during the audit.
