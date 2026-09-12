# Amazon EKS Monitoring and Logging Quiz

> **Last Updated**: September 12, 2026

This quiz tests your understanding of Amazon EKS monitoring and logging features, tools, and best practices.

## Quiz Overview
- EKS Cluster Monitoring
- Container and Application Logging
- Performance Metrics Collection and Analysis
- Alerting and Anomaly Detection
- Monitoring and Logging Architecture
- Best Practices and Tools

## Multiple Choice Questions

### 1. Which principle correctly guides the design of an EKS monitoring solution?

- A. CloudWatch cannot collect application traces.
- B. Installing Grafana alone automatically collects all Pod metrics.
- C. Select required signals, configure owned collectors and data sources, and verify delivery and coverage.
- D. Installing CloudWatch, Prometheus, Grafana and X-Ray always guarantees complete visibility.

<details>
<summary>Show Answer</summary>

**Answer: C. Select and verify the signal/collector/backend design.**

**Explanation:**

A combination of tools can be useful, but the required signals and operational constraints determine the design. CloudWatch supports more than basic infrastructure metrics, including Application Signals tracing/APM on supported workloads. Grafana can query AWS and tracing data sources, but the UI does not collect every signal by itself. Collectors, instrumentation, identities, reachable endpoints and compatible configuration must be connected explicitly; no product list guarantees complete coverage.

**Preserve the Useful Layers:**

| Layer | Example signals | Important dependency |
| --- | --- | --- |
| Infrastructure | Node CPU/memory, disk, network | Supported node collector and correct metric dimensions |
| Kubernetes | Object state, readiness, API activity | Exporter/API/audit permissions and actual targets |
| Application | Request latency, errors, business metrics | Application instrumentation and a bounded metric schema |
| Distributed requests | Trace spans and service relationships | Context propagation, sampling and successful export |

**Implementation Sequence:**

1. Follow the [source chapter](../../eks/06-eks-monitoring-logging.md) for the owned CloudWatch add-on catalog/schema/identity checks. Version5+ Auto Monitor and restart settings must be reviewed; do not layer another agent onto already instrumented workloads without checking conflicts.
2. If Prometheus collection/queries are required, use the source’s KPS90.1.1 values and prepared storage, Grafana Secret and kubelet serving-CA prerequisites. The Operator supplies ServiceMonitor/PrometheusRule handling; a standalone Prometheus installation is not equivalent. Verify actual targets after installation.
3. For the explicit ADOT path, use the source’s Operator0.158/Collector0.50 v1beta1 example with object-valued config, TLS and its prepared ServiceAccount. The Collector release does not contain the Operator installation manifest. This traces-only path sends spans to X-Ray; applications still need instrumentation and propagation.
4. For AMP, configure the real workspace remote-write endpoint and writer identity. Configure Grafana/AMG data-source/query identity separately; AMG12+ uses the AMP plugin. An awsemf exporter publishes through CloudWatch, not automatically to AMP.

**Example Data Paths:**

```text
EKS control-plane logs -------------------------------> CloudWatch Logs
Container stdout/stderr -> chosen log collector ------> configured log store
Application spans ------> ADOT OTLP receiver ----------> X-Ray
Metric targets ----------> Prometheus -----------------> local TSDB
                              |-- SigV4 remote_write -> AMP
Grafana/AMG -- configured queries --> Prometheus / AMP / CloudWatch / X-Ray
```

These are selectable paths, not a statement that every collector exports to every backend. Verify permissions, TLS, discovery/selectors, dropped data and representative queries before relying on dashboards. Define alert priorities/escalation and control cardinality, sampling and retention; test any automated response independently.

**Terraform Planning Example:**

The following resource example uses AWS provider6.64.0. It assumes the selected account/Region, an existing reviewed Grafana workspace role, supported AMG version and an eligible IAM Identity Center setup. Existing resources need their owner’s import/change procedure. The application log-group name matches the source collector path; do not create a second owner for a group already managed by an add-on or another stack.

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.64.0"
    }
  }
}

variable "region" {
  type = string
}

variable "account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "Use the approved 12-digit AWS account ID."
  }
}

variable "cluster_name" {
  type = string
}

variable "grafana_workspace_role_arn" {
  type = string
}

variable "grafana_version" {
  type        = string
  description = "A reviewed AMG version supported in the selected Region."
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

resource "aws_prometheus_workspace" "eks_monitoring" {
  alias = "${var.cluster_name}-monitoring"
}

resource "aws_grafana_workspace" "eks_monitoring" {
  name                     = "${var.cluster_name}-monitoring"
  account_access_type      = "CURRENT_ACCOUNT"
  authentication_providers = ["AWS_SSO"]
  permission_type          = "CUSTOMER_MANAGED"
  role_arn                 = var.grafana_workspace_role_arn
  grafana_version          = var.grafana_version
}

resource "aws_cloudwatch_log_group" "application" {
  name              = "/aws/containerinsights/${var.cluster_name}/application"
  log_group_class   = "STANDARD"
  retention_in_days = 30
}

output "amp_workspace_id" {
  value = aws_prometheus_workspace.eks_monitoring.id
}

output "amp_prometheus_endpoint" {
  value = aws_prometheus_workspace.eks_monitoring.prometheus_endpoint
}

output "grafana_workspace_id" {
  value = aws_grafana_workspace.eks_monitoring.id
}
```

This defines resources, not a working collection or login path. Configure the role’s query permissions for the actual workspace ARN, assign users/groups, add data sources and connect collectors using the returned IDs/endpoints. CUSTOMER_MANAGED explicitly leaves IAM management with the owner; the old SERVICE_MANAGED/data_sources fragment was not proof that an API-created workspace had those roles and connections. Review encryption, retention, access and cost requirements separately. No Terraform plan/apply, login or live telemetry query was executed in this audit.

**Why the Other Choices Are Incorrect:** A understates current CloudWatch capabilities; B confuses visualization with collection; D treats installation as a guarantee of coverage. Custom scripts can still be useful for bounded automation and checks when their ownership, errors and scope are explicit.

</details>

### 2. Which approach connects container logs to centralized retention and analysis correctly?

- A. Treat periodic manual node-file copies as a complete durable log pipeline.
- B. Assume files inside a container always survive container and node replacement.
- C. Use an owned collector with the correct runtime parser, permissions, storage and configured backend.
- D. Install two collectors for the same files and assume this guarantees lossless delivery.

<details>
<summary>Show Answer</summary>

**Answer: C. Configure and verify an owned collection path.**

**Explanation:**

Applications should normally write appropriate structured records to stdout/stderr, while the platform supplies collection and retention. stdout is a good interface, but it is not itself a durable centralized store. A collector can add parsing, filtering, buffering and routing; rotation, finite buffers, node loss and retries still affect coverage and duplicates. Control access, sensitive fields and retention rather than claiming that a collector guarantees integrity or lossless delivery.

**A Wired Fluent Bit Baseline:**

Use the [source chapter](../../eks/06-eks-monitoring-logging.md) rather than applying unrelated raw master-branch manifests. Its standalone example uses AWS chart0.2.0/image3.4.14, native cloudWatchLogs settings, CRI parsing, read-only node logs, separate state/buffers and a reviewed RBAC post-renderer. Prepare the actual log group and IAM identity. If the CloudWatch add-on already owns Fluent Bit, use that owner’s configuration instead of creating a second reader accidentally.

For OpenSearch fan-out, combine this source overlay with its complete base values and post-renderer in the owner’s install/upgrade procedure:

```yaml
opensearch:
  enabled: true
  host: vpc-eks-logs-EXAMPLE.us-west-2.es.amazonaws.com
  port: '443'
  tls: 'On'
  awsAuth: 'On'
  awsRegion: us-west-2
  index: eks-logs
  generateId: 'On'
  suppressTypeName: 'On'
  extraOutputs: 'tls.verify On

    storage.total_limit_size 512M

    '
```

Replace the endpoint/Region with the inspected domain values. SigV4 permissions, domain policy, FGAC role mapping and TLS verification are separate requirements. Do not combine basic-auth credentials with SigV4 on one request. Each output has independent success/retry behavior; success in CloudWatch does not prove OpenSearch delivery. Use supported record-accessor templates and a fallback stream name; log_stream_prefix is not arbitrary shell-style expansion of Kubernetes record fields.

**Fluentd Alternative: Explicit Plugin and Input Contracts:**

Fluentd remains an option when the owned image includes the required parser, Kubernetes metadata and OpenSearch plugins. A containerd/CRI-O envelope must be decoded before treating the application body as JSON. Configure the tail input, metadata permissions, per-collector position/buffer storage and mounted configuration; the following is only an OpenSearch output fragment, not a complete ConfigMap/DaemonSet installation:

```text
<match kubernetes.**>
  @type opensearch
  ssl_verify true
  logstash_format false
  include_timestamp true
  index_name eks-logs
  suppress_type_name true
  <endpoint>
    url "#{ENV.fetch('OPENSEARCH_URL')}"
    region "#{ENV.fetch('AWS_REGION')}"
    assume_role_arn "#{ENV.fetch('AWS_ROLE_ARN')}"
    assume_role_web_identity_token_file "#{ENV.fetch('AWS_WEB_IDENTITY_TOKEN_FILE')}"
  </endpoint>
  <buffer>
    @type file
    path /var/lib/fluentd/opensearch
    total_limit_size 256m
    chunk_limit_size 2m
    retry_timeout 1h
    overflow_action block
  </buffer>
</match>
```

This uses the official fluent-plugin-opensearch IRSA endpoint fields and a fixed index. Prepare OPENSEARCH_URL and the IRSA-injected role/token-file environment. logstash_format=true would ignore index_name; arbitrary per-Pod index expressions are not a substitute for a verified routing/retention design. Choose bounded indices/aliases and review rollover policies. File buffers need an appropriate writable, isolated storage path, and blocking/retry can still lose unread logs after rotation or node loss. The plugin/input composition was not executed in this audit.

**ADOT Log Collection Is Supported by the Selected Components:**

ADOT0.50.0 includes filelog, file_storage and awscloudwatchlogs. The matching upstream0.158 CloudWatch Logs exporter is marked alpha; this is a version-specific example with explicit runtime prerequisites, not a production-readiness claim. Use it as an alternative collector for the selected dataset, not an accidental duplicate of Fluent Bit.

Prepare Operator0.158, logging namespace and ServiceAccount adot-logs with its reviewed IRSA role and AWS log-write permissions. Scope trust to this cluster OIDC provider, sub=system:serviceaccount:logging:adot-logs and aud=sts.amazonaws.com; provide the required STS/Logs network path. The example is for standard Linux EC2 nodes and requires admission permission for a root node agent with read-only /var/log/pods and a dedicated writable state directory. The default-namespace include filter limits exported data; it does not turn the node-wide host mount into a filesystem security boundary. Review node placement/taints, file ownership and namespace policy. Set the actual Region/log-group values before deployment:

```yaml
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: adot-logs
  namespace: logging
spec:
  mode: daemonset
  image: public.ecr.aws/aws-observability/aws-otel-collector:v0.50.0
  serviceAccount: adot-logs
  nodeSelector:
    kubernetes.io/os: linux
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: eks.amazonaws.com/compute-type
            operator: NotIn
            values: [fargate, auto, hybrid]
  env:
  - name: AWS_REGION
    value: us-west-2
  - name: AWS_EC2_METADATA_DISABLED
    value: "true"
  - name: K8S_NODE_NAME
    valueFrom:
      fieldRef:
        fieldPath: spec.nodeName
  - name: LOG_GROUP_NAME
    value: /aws/containerinsights/my-owned-cluster/application
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: "1"
      memory: 512Mi
  podSecurityContext:
    runAsUser: 0
    runAsGroup: 0
    runAsNonRoot: false
    seccompProfile:
      type: RuntimeDefault
  securityContext:
    allowPrivilegeEscalation: false
    readOnlyRootFilesystem: true
    capabilities:
      drop: [ALL]
  volumes:
  - name: pod-logs
    hostPath:
      path: /var/log/pods
      type: Directory
  - name: collector-state
    hostPath:
      path: /var/lib/adot-logs
      type: DirectoryOrCreate
  volumeMounts:
  - name: pod-logs
    mountPath: /var/log/pods
    readOnly: true
  - name: collector-state
    mountPath: /var/lib/adot-logs
  config:
    extensions:
      file_storage:
        directory: /var/lib/adot-logs/checkpoints
        create_directory: true
      health_check:
        endpoint: 0.0.0.0:13133
    receivers:
      filelog:
        include: [/var/log/pods/default_*/*/*.log]
        include_file_path: true
        start_at: end
        storage: file_storage
        retry_on_failure:
          enabled: true
          max_elapsed_time: 5m
        operators:
        - type: container
          add_metadata_from_filepath: true
          max_log_size: 1MiB
    processors:
      memory_limiter:
        check_interval: 1s
        limit_mib: 384
        spike_limit_mib: 64
      batch: {}
    exporters:
      awscloudwatchlogs:
        region: us-west-2
        log_group_name: ${env:LOG_GROUP_NAME}
        log_stream_name: ${env:K8S_NODE_NAME}
        log_retention: 30
        raw_log: false
        sending_queue:
          num_consumers: 2
          queue_size: 100
    service:
      extensions: [file_storage, health_check]
      pipelines:
        logs:
          receivers: [filelog]
          processors: [memory_limiter, batch]
          exporters: [awscloudwatchlogs]
```

The container operator handles CRI envelopes/partial records and derives Pod metadata from log.file.path. A generic JSON parser over raw CRI lines is incorrect. The stream name comes from the Downward API node name through Collector environment substitution, rather than unsupported {pod_name}.{container_name} placeholders.

The exporter can create groups/streams and log_retention applies to newly created groups; configure existing retention through the log-group owner. Its documented EMF handling can override configured group/stream names, so restrict the IAM destination scope and inspect the actual data format. A config string alone is not an authorization boundary.

file_storage preserves receiver offsets, not every unexported batch. The example uses an in-memory sending queue and finite retries; checkpoint state, batches and hostPath data have different failure/lifecycle behavior. start_at=end skips existing content on an initial read without saved offsets. Monitor retries, queue/drop/storage errors and node rotation. No Collector process, mount, AWS credential flow or ingestion was tested.

**Analysis and Infrastructure Checks:**

For the source Fluent Bit schema, inspect structured errors with the actual namespace/container fields. The ADOT wrapper or another collector can produce a different stored schema:

```
fields @timestamp, @log, kubernetes.pod_name, data.level, data.message
| filter kubernetes.namespace_name = "default"
| filter toupper(data.level) = "ERROR"
| sort @timestamp desc
| limit 100
```

An independent Terraform inspection example reads an existing approved OpenSearch domain:

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.64.0"
    }
  }
}

variable "aws_region" {
  type    = string
  default = "us-west-2"
}

variable "opensearch_domain_name" {
  type        = string
  description = "Existing domain approved for this workload's logs"
}

provider "aws" {
  region = var.aws_region
}

data "aws_opensearch_domain" "eks_logs" {
  domain_name = var.opensearch_domain_name
}

output "opensearch_endpoint" {
  value = coalesce(
    data.aws_opensearch_domain.eks_logs.endpoint_v2,
    data.aws_opensearch_domain.eks_logs.endpoint
  )
}

output "opensearch_domain_arn" {
  value = data.aws_opensearch_domain.eks_logs.arn
}
```

The data source does not configure networking, IAM/domain policy, FGAC or delivery. Keep administration separate from ingestion, avoid master passwords in code/state and review any resource/address migration. Queries and access tests require the real environment; Terraform validation does not perform those checks.

**Why the Other Choices Are Incorrect:** Manual file inspection is useful for diagnosis but is not a complete centralized pipeline. Container/node lifetimes and volume types determine what files survive. Duplicate readers can duplicate data/cost and still fail; buffering and retries need measured capacity and failure tests.

References: [ADOT components](https://github.com/aws-observability/aws-otel-collector/tree/v0.50.0), [container parser](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.158.0/pkg/stanza/docs/operators/container.md), [CloudWatch Logs exporter](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.158.0/exporter/awscloudwatchlogsexporter), [Fluentd OpenSearch plugin](https://github.com/fluent/fluent-plugin-opensearch).

</details>

### 3. Which approach creates an effective, verifiable alerting path for EKS?

- A. Assume manual log review guarantees immediate detection.
- B. Create one CloudWatch alarm and assume every Kubernetes/application failure is covered.
- C. Create an arbitrary alertmanager-config ConfigMap and assume the Operator consumes it.
- D. Select the required signals, wire metric/event rules to authorized receivers and test each delivery path.

<details>
<summary>Show Answer</summary>

**Answer: D. Wire and verify the required alert paths.**

**Explanation:**

CloudWatch alarms, Prometheus/Alertmanager and EventBridge cover different signal/routing needs and can be combined deliberately. CloudWatch also supports application/custom metrics, while Prometheus can consume appropriate AWS exporters; neither should be dismissed by a generic “infrastructure only” claim. Installation alone does not establish metric coverage, correct thresholds, publisher permissions or successful delivery.

**Metric Rules Must Match Real Series and Units:**

The following PrometheusRule uses the source chapter’s KPS selectors and real node-exporter/kube-state-metrics series. CPU and available-memory calculations explicitly produce percentages, so an80 threshold is meaningful. CrashLoopBackOff uses the waiting reason rather than any restart; Ready=false on a Running Pod is included, while terminal Pods are excluded. Add stable cluster identity when combining clusters, and check for equivalent bundled rules before deploying duplicates:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: eks-observability-alerts
  namespace: monitoring
  labels:
    release: monitoring
spec:
  groups:
  - name: eks-observability-example
    rules:
    - alert: NodeHighCPU
      expr: (100 * (1 - avg by (cluster, instance) (max by (cluster, instance, cpu) (rate(node_cpu_seconds_total{job="node-exporter",mode="idle"}[5m]))))) > 80
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: High non-idle CPU on {{ $labels.instance }}
        description: The node-exporter percentage has exceeded the example threshold; inspect workload and metric health.
    - alert: NodeMemoryFilling
      expr: (100 * (1 - max by (cluster, instance) (node_memory_MemAvailable_bytes{job="node-exporter"}) / max by (cluster, instance) (node_memory_MemTotal_bytes{job="node-exporter"}))) > 80 and on (cluster, instance) (max by (cluster, instance) (node_memory_MemTotal_bytes{job="node-exporter"}) > 0)
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Low available memory on {{ $labels.instance }}
        description: This is a MemAvailable-based estimate, not a MemoryPressure condition or Pod request utilization.
    - alert: KubernetesPodCrashLooping
      expr: max by (cluster, namespace, pod, uid, container) (max_over_time(kube_pod_container_status_waiting_reason{job="kube-state-metrics",reason="CrashLoopBackOff"}[5m])) >= 1
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: CrashLoopBackOff observed for {{ $labels.namespace }}/{{ $labels.pod }}
        description: Inspect container {{ $labels.container }} logs and events; the rule tracks recent waiting reasons, not a restart-count guarantee.
    - alert: PodNotReady
      expr: (max by (cluster, namespace, pod, uid) (kube_pod_status_ready{job="kube-state-metrics",condition="true"}) == 0) and on (cluster, namespace, pod, uid) (max by (cluster, namespace, pod, uid) (kube_pod_status_phase{job="kube-state-metrics",phase=~"Pending|Running|Unknown"}) == 1)
      for: 15m
      labels:
        severity: warning
      annotations:
        summary: Active Pod {{ $labels.namespace }}/{{ $labels.pod }} is not ready
        description: Inspect Ready conditions and probes; terminal Succeeded/Failed Pods are excluded from this example.
```

These are illustrative thresholds and hold times. MemAvailable estimates reclaimable memory availability; it is not the kubelet MemoryPressure condition or a percentage of Pod requests. Missing or stale series do not mean healthy/zero usage. Monitor scrape failures and rule evaluation separately.

**Connect the Actual Alertmanager Configuration:**

Use the source’s alertmanager-routing Secret with key alertmanager.yaml, its alertmanager-values.yaml and notification-credentials mount. Prepare the real Slack webhook and PagerDuty Events API v2 routing key in that Secret. For native SNS, prepare the actual Alertmanager ServiceAccount’s AWS identity with topic-scoped publish and applicable KMS permissions; another component’s IRSA role is not automatically shared.

Replace the example SNS account/Region/topic before use. This complete routing example sends critical alerts to PagerDuty, warnings to Slack and unmatched alerts to SNS; the example Watchdog route is discarded pending a separately configured heartbeat monitor:

```yaml
global:
  resolve_timeout: 5m
route:
  group_by:
  - cluster
  - namespace
  - alertname
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: sns-notifications
  routes:
  - matchers:
    - alertname="Watchdog"
    receiver: discard
  - matchers:
    - severity="critical"
    receiver: pagerduty-notifications
  - matchers:
    - severity="warning"
    receiver: slack-notifications
receivers:
- name: discard
- name: slack-notifications
  slack_configs:
  - api_url_file: /etc/alertmanager/secrets/notification-credentials/slack-url
    channel: '#eks-alerts'
    send_resolved: true
    title: '[{{ .Status | toUpper }}] {{ .CommonLabels.alertname }}'
    text: "{{ range .Alerts }}{{ .Annotations.summary }} \u2014 {{ .Annotations.description }}{{ \"\\n\" }}{{ end }}"
- name: sns-notifications
  sns_configs:
  - sigv4:
      region: us-west-2
    topic_arn: arn:aws:sns:us-west-2:123456789012:eks-alerts
    send_resolved: true
    subject: EKS {{ .CommonLabels.alertname }}
- name: pagerduty-notifications
  pagerduty_configs:
  - routing_key_file: /etc/alertmanager/secrets/notification-credentials/pagerduty-routing-key
    send_resolved: true
    severity: '{{ if eq .CommonLabels.severity "critical" }}critical{{ else }}warning{{ end }}'
    description: '{{ .CommonLabels.alertname }}'
```

The default receiver is a fallback, not automatic fan-out when a child route matches. Configure continue/explicit sibling routes only when intentional fan-out is required. Validate the complete file with the matching amtool and test route labels. No undefined sns-forwarder service or credential-bearing ConfigMap is needed.

**CloudWatch and EventBridge Publisher Permissions:**

- For Container Insights alarms, use the actual metric and dimensions from the source chapter. A managed node-group name is not necessarily an EC2 Auto Scaling group name; do not invent an AWS/EC2 dimension value.
- A CloudWatch alarm publisher needs the appropriate SNS topic policy. If the topic is encrypted, AWS documents that alias/aws/sns is insufficient for CloudWatch alarms; use a customer-managed KMS key whose policy permits the required publisher operations with appropriate restrictions.
- EventBridge uses published EKS add-on health events or supported CloudTrail API events. EKS Cluster Control Plane Health is not in the EKS direct-event catalog. An API attempt is not proof of update completion.
- For an SNS target, prepare the EventBridge execution role or the documented resource-policy alternative. Check PutTargets failures and delivery metrics. Topic existence or a successful rule API response is not delivery proof.

**Terraform Planning Example:**

This independent example references an existing owned standard SNS topic and prepared target role. The topic/key policies, subscriptions and actual ContainerInsights data are prerequisites. The node CPU alarm uses Maximum across the selected ClusterName series, while the add-on event rule is account/Region-wide. Actions and the rule start disabled for review:

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.64.0"
    }
  }
}

variable "region" {
  type = string
}

variable "account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "Use the approved 12-digit AWS account ID."
  }
}

variable "cluster_name" {
  type = string
}

variable "sns_topic_arn" {
  type        = string
  description = "Prepared standard SNS topic with reviewed publisher/subscription/key permissions."
}

variable "eventbridge_role_arn" {
  type        = string
  description = "Prepared target execution role allowed to publish to the selected topic."
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

resource "aws_cloudwatch_metric_alarm" "node_cpu" {
  alarm_name          = "${var.cluster_name}-node-cpu-warning"
  alarm_description   = "Example node CPU Maximum threshold; confirm actual ContainerInsights data."
  namespace           = "ContainerInsights"
  metric_name         = "node_cpu_utilization"
  dimensions          = { ClusterName = var.cluster_name }
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = 80
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "missing"
  actions_enabled     = false
  alarm_actions       = [var.sns_topic_arn]
}

resource "aws_cloudwatch_event_rule" "addon_health" {
  name_prefix = "eks-addon-health-"
  description = "Account/Region add-on health events; not filtered to a single cluster."
  state       = "DISABLED"
  event_pattern = jsonencode({
    source      = ["aws.eks"]
    account     = [var.account_id]
    region      = [var.region]
    detail-type = ["EKS Addon Health Degraded", "EKS Addon Health Restored"]
  })
}

resource "aws_cloudwatch_event_target" "sns" {
  rule      = aws_cloudwatch_event_rule.addon_health.name
  target_id = "ops-sns"
  arn       = var.sns_topic_arn
  role_arn  = var.eventbridge_role_arn
}
```

The CPU example requires two breaching five-minute maxima, not continuous80% usage for ten minutes. Missing data is not treated as automatically healthy. Review resource ownership, publisher access, metric data and expected notifications before enabling through the owner’s controlled change. This excerpt does not create/replace the topic policy or configure subscriptions, and was not planned/applied against AWS.

**SNS Subscriptions and Optional Lambda Processing:**

Email subscriptions require confirmation. Lambda subscriptions require permission on the function for the intended SNS topic; a subscription alone does not grant invocation access. SNS invokes Lambda asynchronously for standard topics, and duplicate processing can occur. A custom adapter needs actual delivery code, packaged dependencies, protected credentials, input validation, idempotency, failure/retry handling and observable outcomes.

Do not deploy the old placeholder handler whose send functions only contain pass and then return “processed successfully.” An HTTP-looking statusCode return is not a notification acknowledgement for an asynchronous SNS invocation. Surface delivery failures correctly, inspect the documented SNS record shape and do not infer severity from arbitrary AlarmName substrings. Configure subscription-delivery failures and Lambda execution failures separately. SQS buffering is another optional design requiring an actual queue/event-source mapping and its own failure controls; none is implied by an architecture sketch.

**Correctly Separated Paths:**

```text
CloudWatch alarm -----------------------------> SNS -> confirmed subscribers
EventBridge rule -- authorized target role ---> SNS -> confirmed subscribers
Prometheus -> Alertmanager -- default --------> SNS
                         |-- warning --------> Slack
                         |-- critical -------> PagerDuty
Optional SNS subscriber -> implemented Lambda adapter -> chosen external channel
```

Group related alerts, bound repeats, define explicit severity/response windows, include evidence and impact, and test representative firing/resolution and failure paths in an approved test destination. Neither complete coverage nor successful delivery follows from installing a set of tools. No topic, subscription, alarm, Lambda invocation or notification was created/executed during this audit.

References: [source chapter](../../eks/06-eks-monitoring-logging.md), [Alertmanager receivers](https://prometheus.io/docs/alerting/latest/configuration/), [EKS events](https://docs.aws.amazon.com/eventbridge/latest/ref/events-ref-eks.html), [SNS/Lambda](https://docs.aws.amazon.com/lambda/latest/dg/with-sns.html), [encrypted SNS for CloudWatch alarms](https://repost.aws/knowledge-center/cloudwatch-configure-alarm-sns).

</details>

### 4. Which application-observability design preserves useful evidence?

- A. Treat node CPU alone as proof of every application latency cause.
- B. Overwrite all incoming service.name attributes with one shared collector name.
- C. Correlate selected metrics, logs and traces while preserving service identity and verifying their actual paths.
- D. Assume a10% head sampler always retains every error and slow request.

<details>
<summary>Show Answer</summary>

**Answer: C. Correlate verified signal paths without collapsing identity.**

**Explanation:**

Metrics describe rates/distributions/resource state, logs add event detail, and traces connect instrumented operations. They support investigation but do not guarantee complete visibility or a proven root cause. Profiling can add CPU/allocation/heap evidence when explicitly enabled and reviewed; it is not automatically provided by every trace collector.

**Use the Correct Collector and Signal Routes:**

Use the source chapter’s owned Operator0.158/ADOT0.50 TLS traces-only configuration and Q2’s separately scoped logging alternative. The Operator manifest comes from its own release, not a Collector release asset. Keep service.name at the application boundary; a shared resource processor must not upsert one global value over order-service, payment-service and other callers.

For Prometheus metrics, use the source’s wired ServiceMonitor/Service path or a separately verified Prometheus receiver. Annotation discovery alone does not configure the correct port/path, RBAC or replica target distribution. awsemf exports to CloudWatch, while AMP requires a real remote-write endpoint and SigV4 identity. Do not draw an AMP path when the configuration only has awsemf.

**Java Instrumentation Example:**

One alternative to a Spring Boot starter is the upstream OpenTelemetry Java agent. The inspected release is2.31.1; prepare its reviewed JAR and a compatible application/JVM through the application build process. This avoids mixing Gradle declarations and application.properties inside a Java source block or copying an unaligned1.18-alpha starter. Do not add another agent to a process already instrumented by CloudWatch Auto Monitor or another owner.

This is application runtime configuration, not an audit test command. It selects OTLP/HTTP traces for the source’s TLS receiver and leaves SDK metric/log exporting off for these separate paths. Mount the trusted CA and preserve any other required JVM startup options:

```bash
set -euo pipefail
: "${OTEL_JAVA_AGENT_JAR:?Set the reviewed OpenTelemetry Java agent 2.31.1 JAR path}"
: "${APP_JAR:?Set the application JAR path}"
test -r "$OTEL_JAVA_AGENT_JAR"
test -r "$APP_JAR"
export OTEL_SERVICE_NAME=order-service
export OTEL_RESOURCE_ATTRIBUTES=k8s.cluster.name=my-owned-cluster
export OTEL_TRACES_EXPORTER=otlp
export OTEL_METRICS_EXPORTER=none
export OTEL_LOGS_EXPORTER=none
export OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://adot-traces-collector.tracing-demo.svc:4318/v1/traces
export OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE=/etc/otel/ca.crt
export OTEL_PROPAGATORS=tracecontext,baggage
export OTEL_TRACES_SAMPLER=parentbased_traceidratio
export OTEL_TRACES_SAMPLER_ARG=0.1
java "-javaagent:$OTEL_JAVA_AGENT_JAR" -jar "$APP_JAR"
```

Java agent2.x defaults to http/protobuf; the example makes that choice explicit. A signal-specific HTTP endpoint includes /v1/traces. The4317 gRPC endpoint uses a different protocol and cannot be substituted by changing only the port. Release/configuration metadata was verified; no Java agent, JDK or application was executed here.

**Python Instrumentation Example:**

Use the source’s RequestTracing adapter with Python3.10+ and aligned SDK/HTTP exporter1.44.0. Set these values in the payment application’s environment, replacing the example cluster name and mounting the trusted CA:

```bash
export OTEL_SERVICE_NAME=payment-service
export CLUSTER_NAME=my-owned-cluster
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://adot-traces-collector.tracing-demo.svc:4318/v1/traces
export OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE=/etc/otel/ca.crt
```

The adapter is reproduced below so the lifecycle and request boundary are explicit:

```python
import os
from urllib.parse import urlsplit

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.trace import SpanKind
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


class RequestTracing:
    def __init__(self):
        endpoint = os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"]
        parsed = urlsplit(endpoint)
        if parsed.scheme != "https" or parsed.path != "/v1/traces":
            raise ValueError("Set the HTTPS OTLP/HTTP traces endpoint including /v1/traces")
        self.provider = TracerProvider(
            resource=Resource.create({
                "service.name": os.environ["OTEL_SERVICE_NAME"],
                "k8s.cluster.name": os.environ["CLUSTER_NAME"],
            }),
            sampler=ParentBased(TraceIdRatioBased(0.1)),
        )
        exporter = OTLPSpanExporter(
            endpoint=endpoint,
            certificate_file=os.environ["OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE"],
            timeout=10,
        )
        self.provider.add_span_processor(BatchSpanProcessor(exporter))
        self.tracer = self.provider.get_tracer("example.request-handler")
        self.propagator = TraceContextTextMapPropagator()

    def handle_request(self, incoming_headers, operation):
        parent = self.propagator.extract(incoming_headers)
        with self.tracer.start_as_current_span("request", context=parent, kind=SpanKind.SERVER):
            outgoing_headers = {}
            self.propagator.inject(outgoing_headers)
            return operation(outgoing_headers)

    def close(self):
        self.provider.shutdown()
```

Create one instance during app startup, call handle_request from the real framework handler with normalized incoming header names and the actual business operation, and call close on graceful shutdown. This is not a Flask server or a payment implementation; app/request/jsonify/process_transaction are not silently assumed to exist. Propagate the supplied context into real outbound calls and asynchronous work using the framework’s supported mechanism.

The audit exercised this adapter with SDK exporting disabled, including business-result/error preservation and pure propagation/sampling checks. That is not evidence of live span export or a deployed Collector.

**Match IRSA Trust, Permissions and the ServiceAccount:**

The following independent Terraform example matches the source collector’s tracing-demo/adot-traces identity. It uses declared inputs and an already existing IAM OIDC provider for the actual cluster issuer. The trust conditions include both sub and aud. X-Ray PutTraceSegments has no resource-level ARN scope, so the policy uses the required wildcard resource with a restricted action/Region and the scoped trust. This does not grant unrelated CloudWatch or AMP permissions:

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.64.0"
    }
  }
}

variable "region" {
  type = string
}

variable "account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "Use the approved 12-digit AWS account ID."
  }
}

variable "cluster_oidc_issuer_url" {
  type        = string
  description = "The actual EKS cluster OIDC issuer URL; its IAM OIDC provider must already exist."
  validation {
    condition     = startswith(var.cluster_oidc_issuer_url, "https://")
    error_message = "Use the HTTPS issuer returned by the owned cluster."
  }
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

data "aws_partition" "current" {}

locals {
  oidc_hostpath     = trimsuffix(trimprefix(var.cluster_oidc_issuer_url, "https://"), "/")
  oidc_provider_arn = "arn:${data.aws_partition.current.partition}:iam::${var.account_id}:oidc-provider/${local.oidc_hostpath}"
}

resource "aws_iam_role" "adot_traces" {
  name = "adot-traces-example"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = local.oidc_provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${local.oidc_hostpath}:aud" = "sts.amazonaws.com"
          "${local.oidc_hostpath}:sub" = "system:serviceaccount:tracing-demo:adot-traces"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "xray_write" {
  name = "xray-trace-write"
  role = aws_iam_role.adot_traces.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["xray:PutTraceSegments"]
      Resource = "*"
      Condition = {
        StringEquals = { "aws:RequestedRegion" = var.region }
      }
    }]
  })
}

resource "aws_xray_group" "applications" {
  group_name        = "EKS-Applications"
  filter_expression = "service(\"order-service\") OR service(\"payment-service\")"
}

output "adot_traces_role_arn" {
  value = aws_iam_role.adot_traces.arn
}
```

Before creating the Collector, a new owned ServiceAccount can be created atomically with its role annotation in the already prepared namespace. Existing ServiceAccounts/roles require their owner’s update/import procedure; do not overwrite another identity or combine an unrelated Pod Identity association:

```bash
set -euo pipefail
: "${ADOT_ROLE_ARN:?Set the reviewed role ARN from the owned Terraform stack}"
python3 - "$ADOT_ROLE_ARN" <<'PY' | kubectl create -f -
import json
import sys
print(json.dumps({
    "apiVersion": "v1",
    "kind": "ServiceAccount",
    "metadata": {
        "name": "adot-traces",
        "namespace": "tracing-demo",
        "annotations": {"eks.amazonaws.com/role-arn": sys.argv[1]},
    },
}))
PY
```

An annotation change does not retroactively inject credentials into running Pods; review any necessary rollout. Verify the actual issuer/provider, token audience, assumed role and network path. The X-Ray group filters matching traces; it does not instrument applications or grant the collector permission. Use Q1’s workspace/data-source setup rather than duplicating an incomplete AMG create command. No IAM role/group/ServiceAccount was created in this audit.

**Browser RUM Is a Distinct Path:**

The CloudWatch RUM web client sends PutRumEvents data to CloudWatch RUM, not automatically to an ADOT OTLP receiver. When X-Ray tracing is enabled, it can add X-Amzn-Trace-Id to allowed HTTP requests. Client/server traces are not connected by default: review supported server propagation/bridging and CORS allowed headers. The W3C-only examples above do not automatically consume an X-Ray header. A generic OpenTelemetry browser client would need its own supported OTLP endpoint/auth/CORS design.

```text
Browser CloudWatch RUM client -----> CloudWatch RUM
                 | optional X-Ray header/segment integration
Java order-service <--- propagated requests ---> Python payment-service
       | OTLP/HTTP TLS                              | OTLP/HTTP TLS
       +--------------> ADOT traces collector <-----+
                              |
                              v
                            X-Ray
Application metrics -> configured Prometheus -> optional SigV4 remote_write -> AMP
Application stdout  -> chosen log collector -> configured log store
Grafana/AMG         -> queries the configured data sources
```

**Coverage, Sampling and Privacy:**

- Measure latency distributions, throughput, error rates and saturation with a defined population/window. A sampled trace set is not automatically an unbiased metric distribution.
- Use bounded service names, normalized routes, version/environment and cluster/namespace identity. Customer/tenant IDs and raw request URLs can create cardinality and privacy problems; they are not default metric labels.
- Head sampling decides before a request’s final outcome. It cannot guarantee all errors/slow requests, and tail sampling cannot recover spans already dropped upstream. Tail sampling needs trace-affine routing and adequate buffers/time windows.
- RUM session/user data, logs, spans and profiles need appropriate access, consent/collection policy and retention. Correlation IDs are metadata, not authentication.
- Performance tests and profiling complement runtime signals. No new benchmark or production performance result is claimed by these examples.

References: [Java agent configuration](https://opentelemetry.io/docs/zero-code/java/agent/configuration/), [Java SDK configuration](https://opentelemetry.io/docs/languages/java/configuration/), [CloudWatch RUM/X-Ray](https://docs.aws.amazon.com/xray/latest/devguide/xray-services-RUM.html), [source chapter](../../eks/06-eks-monitoring-logging.md).

</details>

### 5. How should you monitor the AWS-managed EKS control plane logs?

- A. SSH directly into the AWS-managed control-plane nodes.
- B. Configure the required EKS log types, verify delivery to CloudWatch Logs and apply appropriate queries/access controls.
- C. Assume a worker-node DaemonSet can read the managed control-plane filesystem.
- D. Create a log dashboard and assume it automatically publishes an ErrorCount metric.

<details>
<summary>Show Answer</summary>

**Answer: B. Configure and verify the managed logging path.**

**Explanation:**

EKS sends selected control-plane log types directly to CloudWatch Logs in the account. A worker collector is not the source of these managed logs. This provides diagnostic/audit evidence without control-plane SSH, but it does not guarantee a record of every API call or prove compliance. Audit policy, stages, enablement time, ingestion and retention determine what is available.

**Log Types and Their Scope:**

| Type | Use |
| --- | --- |
| api | API-server diagnostics and errors; not a complete request/response archive |
| audit | Recorded Kubernetes API audit events and identity/resource/status fields |
| authenticator | IAM authentication/mapping diagnostics; distinguish authentication from RBAC authorization |
| controllerManager | Controller reconciliation diagnostics |
| scheduler | Scheduling decisions/failures and related diagnostics |

Inspect the existing cluster configuration first. For an approved all-five-types change, the source chapter’s update captures an update ID and checks status; continue checking until success and then verify actual log delivery:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{ARN:arn,Status:status,Logging:logging}'
```



```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the reviewed cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
UPDATE_ID=$(aws eks update-cluster-config \
  --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query 'update.id' --output text)
if [[ -z "$UPDATE_ID" || "$UPDATE_ID" == None ]]; then
  printf '%s\n' 'No update ID returned; inspect the request result.' >&2
  exit 1
fi
aws eks describe-update --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --update-id "$UPDATE_ID" \
  --query 'update.{ID:id,Status:status,Errors:errors}'
```

The final DescribeUpdate call is a status check, not a waiter or ingestion test. When selecting only some types, preserve all existing required types; do not copy a block that explicitly disables authenticator/controllerManager/scheduler merely to turn on api/audit. For a new cluster, include logging in its reviewed creation/IaC configuration. Do not create another incomplete cluster just to configure monitoring. EKS Capabilities controller logs use their separate delivery path described in the source.

**Query Actual JSON Fields:**

Select the owned /aws/eks/CLUSTER/cluster group and a bounded time range. Example recorded 5xx responses:

```
fields @timestamp, auditID, user.username, verb, objectRef.resource, responseStatus.code
| filter apiVersion = "audit.k8s.io/v1" and stage = "ResponseComplete"
| filter responseStatus.code >= 500
| sort @timestamp desc
| limit 100
```

For a known audit username, use the nested JSON field rather than parsing a literal user.username string. Replace the example username with the actual identity observed in your records:

```
fields @timestamp, auditID, user.username, verb, objectRef.resource, responseStatus.code
| filter apiVersion = "audit.k8s.io/v1"
| filter user.username = "example-user"
| sort @timestamp desc
| limit 100
```

Inspect authenticator records before defining format-specific failure filters. A failed/denied substring can miss real cases or match unrelated text, and an IAM authentication message alone does not describe every Kubernetes authorization outcome.

**A Dashboard Does Not Publish a Metric:**

A Logs Insights widget runs a query. An alarm on a custom metric needs a real publisher, such as a metric filter. The independent Terraform example below connects a STANDARD log group, a filter, its metric, an alarm and dashboard. Manage/import the existing log group through its actual owner before using this configuration; the KMS key and SNS topic/publisher permissions must already be prepared. It does not create a new EKS cluster or KMS key.

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.64.0"
    }
  }
}

variable "region" {
  type = string
}

variable "account_id" {
  type = string
}

variable "cluster_name" {
  type = string
}

variable "logs_kms_key_arn" {
  type        = string
  description = "Prepared symmetric key in the log-group Region with reviewed Logs/caller permissions."
}

variable "sns_topic_arn" {
  type        = string
  description = "Prepared standard SNS topic with confirmed subscriptions and publisher/key permissions."
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

locals {
  metric_namespace = "EKS/ControlPlane"
  metric_name      = "${var.cluster_name}-AuditResponse5xxCount"
  filter_pattern   = "{ ($.apiVersion = \"audit.k8s.io/v1\") && ($.stage = \"ResponseComplete\") && ($.responseStatus.code >= 500) }"
}

resource "aws_cloudwatch_log_group" "control_plane" {
  name              = "/aws/eks/${var.cluster_name}/cluster"
  log_group_class   = "STANDARD"
  retention_in_days = 90
  kms_key_id        = var.logs_kms_key_arn
}

resource "aws_cloudwatch_log_metric_filter" "audit_5xx" {
  name           = "${var.cluster_name}-audit-response-5xx"
  log_group_name = aws_cloudwatch_log_group.control_plane.name
  pattern        = local.filter_pattern

  metric_transformation {
    namespace     = local.metric_namespace
    name          = local.metric_name
    value         = "1"
    default_value = 0
    unit          = "Count"
  }
}

resource "aws_cloudwatch_metric_alarm" "audit_5xx" {
  alarm_name          = "${var.cluster_name}-audit-response-5xx"
  alarm_description   = "Example threshold for ingested audit ResponseComplete records with code>=500."
  namespace           = local.metric_namespace
  metric_name         = local.metric_name
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  threshold           = 10
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "missing"
  actions_enabled     = false
  alarm_actions       = [var.sns_topic_arn]
}

resource "aws_cloudwatch_dashboard" "control_plane" {
  dashboard_name = "${var.cluster_name}-control-plane"
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "log"
        x      = 0
        y      = 0
        width  = 24
        height = 6
        properties = {
          region = var.region
          title  = "Recorded audit 5xx responses per five minutes"
          view   = "timeSeries"
          query  = "SOURCE '${aws_cloudwatch_log_group.control_plane.name}' | fields @timestamp\n| filter apiVersion = \"audit.k8s.io/v1\" and stage = \"ResponseComplete\" and responseStatus.code >= 500\n| stats count(*) as recordedResponses by bin(5m)"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 24
        height = 6
        properties = {
          region  = var.region
          title   = "Metric filter: new ingested audit 5xx records"
          view    = "timeSeries"
          metrics = [[local.metric_namespace, local.metric_name]]
          period  = 300
          stat    = "Sum"
        }
      }
    ]
  })
}
```

The filter counts newly ingested audit ResponseComplete records with responseStatus.code>=500. The cluster-prefixed metric name distinguishes the cluster without inventing a ClusterName dimension absent from audit JSON. Filter, alarm and metric widget use exactly the same namespace/name and no dimensions. The dashboard query may cover older records, but the metric filter does not backfill history. These are recorded-event counts, not an API error rate or a deduplicated request total; duplicate deliveries can occur.

A default_value of0 is emitted when logs arrive but none match; no incoming logs can still produce missing data. Metric filters cannot combine a default value with dimensions. The alarm intentionally starts with actions disabled, treats missing data explicitly and uses an illustrative threshold. Verify new metric datapoints, permissions, subscriptions and a controlled delivery test before enabling.

jsonencode avoids the broken shell quoting in the old dashboard command. If using the CLI instead, pass a valid JSON file with --dashboard-body file://dashboard.json and inspect DashboardValidationMessages. PutDashboard replaces an existing body; preserve its owner’s widgets and configuration. Local HCL/JSON validation is not execution of the AWS filter/query engine.

**KMS and Retention:**

CloudWatch Logs encrypts log data by default. Associating a customer-managed symmetric KMS key changes encryption for newly ingested data; it is not the first encryption layer and does not re-encrypt old records. Use a key in the log group’s Region, retain old keys/permissions while old data is needed, and distinguish association permissions from reading permissions. Disassociation returns new data to default encryption; disabling/deleting an old key can make its retained data unreadable.

The regional Logs service requires key-use permission. The following is only a statement fragment for the key owner to merge into an existing policy while retaining administrator/delegation statements. Replace every example identifier consistently; do not use it as a complete replacement key policy:

```json
{
  "Sid": "AllowLogsServiceForOneGroup",
  "Effect": "Allow",
  "Principal": {
    "Service": "logs.us-west-2.amazonaws.com"
  },
  "Action": [
    "kms:Encrypt",
    "kms:Decrypt",
    "kms:ReEncrypt*",
    "kms:GenerateDataKey*",
    "kms:DescribeKey"
  ],
  "Resource": "*",
  "Condition": {
    "ArnEquals": {
      "kms:EncryptionContext:aws:logs:arn": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/eks/my-cluster/cluster"
    }
  }
}
```

The encryption-context log-group ARN has no trailing :*. The operator associating the key needs the documented Logs permissions and kms:DescribeKey. Read/write callers need the KMS permissions appropriate to their operations, via the regional Logs service. Key rotation or a short deletion waiting period does not remove the requirement to retain decrypt access for historical data. Retention90 is an example, not a compliance or immutability guarantee.

**Scope Read Access Correctly:**

This illustrative identity policy permits the selected group and its streams, plus decrypt on one key through Logs. The key policy must also allow the intended principal. It grants no log-management or key-administration actions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadAndQueryThisLogGroup",
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogStreams",
        "logs:FilterLogEvents",
        "logs:StartQuery",
        "logs:GetQueryResults"
      ],
      "Resource": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/eks/my-cluster/cluster:*"
    },
    {
      "Sid": "ReadThisGroupStreams",
      "Effect": "Allow",
      "Action": "logs:GetLogEvents",
      "Resource": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/eks/my-cluster/cluster:log-stream:*"
    },
    {
      "Sid": "DecryptThisGroupsDataViaLogs",
      "Effect": "Allow",
      "Action": "kms:Decrypt",
      "Resource": "arn:aws:kms:us-west-2:123456789012:key/11111111-2222-3333-4444-555555555555",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "logs.us-west-2.amazonaws.com"
        },
        "ArnEquals": {
          "kms:EncryptionContext:aws:logs:arn": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/eks/my-cluster/cluster"
        }
      }
    }
  ]
}
```

Current AWS authorization documentation supports log-group scoping for StartQuery and GetQueryResults; do not broaden them to Resource:* based on old assumptions. DescribeLogStreams and FilterLogEvents are group actions, while GetLogEvents is a stream action. AWS’s LogGroup arn form includes :* for most IAM actions; logGroupArn and encryption-context/tagging uses omit it. Console/discovery workflows may require additional read actions; DescribeLogGroups is a separately scoped permission with no resource-level ARN support, not implicitly granted by the policy above.

No cluster logging, log retention, key policy, metric filter, dashboard, alarm or cloud query was changed/executed during this audit. References: [CloudWatch metric filters](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/MonitoringLogData.html), [LogGroup ARN forms](https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_LogGroup.html), [Logs IAM actions](https://docs.aws.amazon.com/service-authorization/latest/reference/list_logs.html), [KMS log encryption](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/encrypt-log-data-kms.html).

</details>

### 6. Which monitoring strategy best supports cost optimization in Amazon EKS?

- A. Collect every available metric regardless of its use
- B. Combine resource usage, billing allocation, and owner-reviewed waste candidates
- C. Monitor performance without examining spending
- D. Review only the final monthly bill

<details>
<summary>Show Answer</summary>

**Answer: B. Combine resource usage, billing allocation, and owner-reviewed waste candidates**

**Explanation:** Compare CPU, memory, storage, requests, limits, and workload trends with allocated costs. Investigate anomalies and budget deviations with the resource owner. These signals identify opportunities; they do not guarantee savings or establish that a resource can be deleted.

**Resource efficiency and cost allocation**

Reuse the source guide's kube-prometheus-stack installation, kube-state-metrics, and kubelet ServiceMonitor with verified serving certificates. cAdvisor uses `/metrics/cadvisor` on the kubelet HTTPS metrics port; it is not a separate Service port named `cadvisor`. Do not add a duplicate monitor or disable TLS verification to make scraping work.

The following CPU and memory expressions return **usage/request ratios per container**, not node capacity utilization or monetary cost. A ratio can exceed 1. Zero/missing requests produce no ratio, not zero usage. `max` removes duplicate scrape copies with the listed identity; confirm that copies actually represent the same workload. This example targets one cluster's local Prometheus. For a shared backend, both metric families must carry a consistent cluster label. Pod-name reuse and container restarts also require care when interpreting a time range. These container metrics do not describe the complete scheduler reservation for Pod-level resources, init containers, or Pod overhead.

```promql
max by (cluster, namespace, pod, container) (
  rate(container_cpu_usage_seconds_total{job="kubelet",metrics_path="/metrics/cadvisor",namespace!="",container!="",container!="POD"}[5m])
)
/ on (cluster, namespace, pod, container)
(
  max by (cluster, namespace, pod, container) (
    kube_pod_container_resource_requests{job="kube-state-metrics",resource="cpu",unit="core",container!=""}
  ) > 0
)
```

```promql
max by (cluster, namespace, pod, container) (
  container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",namespace!="",container!="",container!="POD"}
)
/ on (cluster, namespace, pod, container)
(
  max by (cluster, namespace, pod, container) (
    kube_pod_container_resource_requests{job="kube-state-metrics",resource="memory",unit="byte",container!=""}
  ) > 0
)
```

Create two panels in Grafana using the existing Prometheus data source and these queries; name the dashboard **Resource usage versus requests**, use a ratio/percentage unit, and retain cluster, namespace, Pod, and container identity. A ConfigMap containing an unspecified `cost-dashboard.json` does not create a usable dashboard. With the source guide's Grafana sidecar, provisioning a reviewed JSON dashboard additionally requires its configured `grafana_dashboard: "1"` label.

**OpenCost or Kubecost**

For a new OpenCost evaluation against the source guide's existing Prometheus, save this as `opencost-values.yaml`. The checked chart is **2.5.31**, application **1.121.2**. Set the actual cluster ID and Prometheus URL. Its ServiceMonitor label must match the Prometheus selector; allow the `opencost` namespace in namespace selection. This does not install another Prometheus/node exporter.

```yaml
service:
  type: ClusterIP
opencost:
  exporter:
    defaultClusterId: my-cluster
  prometheus:
    internal:
      enabled: false
    external:
      enabled: true
      url: http://monitoring-kube-prometheus-prometheus.monitoring.svc:9090
  metrics:
    serviceMonitor:
      enabled: true
      additionalLabels:
        release: monitoring
  cloudCost:
    enabled: false
  mcp:
    enabled: false
  ui:
    enabled: true
    ingress:
      enabled: false
```

```bash
helm repo add opencost https://opencost.github.io/opencost-helm-chart
helm repo update opencost
helm template opencost opencost/opencost --version 2.5.31 \
  --namespace opencost -f opencost-values.yaml > opencost-rendered.yaml
# After reviewing RBAC, images, resources, selectors, and network access:
helm install opencost opencost/opencost --version 2.5.31 \
  --namespace opencost --create-namespace -f opencost-values.yaml
kubectl -n opencost port-forward --address 127.0.0.1 svc/opencost 9090:9090
```

Open `http://localhost:9090` while the port-forward is running. This baseline uses an ephemeral exporter cache, disables Cloud Cost ingestion and MCP, and exposes only a ClusterIP Service. Review persistence, sizing, authentication/network access, RBAC, and scrape health before shared use; ClusterIP is not a tenant authorization boundary. On-demand price estimates need reconciliation with actual billing, discounts, Spot prices, credits, shared costs, storage, and network charges. AWS billing integration is a separate configuration; supported AWS service-account/default-SDK authentication does not require embedding long-lived access keys.

Kubecost is a separate option. Its checked **3.2.4** chart is `kubecost/kubecost` from `https://kubecost.github.io/kubecost/`. The old `cost-analyzer` repository and 2.x Prometheus values are not a 3.x install recipe: 3.x uses ClickHouse and direct finops-agent collection. Review its license, storage, Kubernetes compatibility, and documented 2.x migration before installation or upgrade. See the paired [FinOps platform guide](../../ops/13-finops-cost-platform.md) and [Kubecost chart documentation](https://github.com/kubecost/cost-analyzer-helm-chart).

**Labels, billing tags, and categories**

Namespace labels help Kubernetes-side grouping:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
  labels:
    team: team-a
    cost-center: cc-123
    environment: production
```

They do not automatically tag EC2/EBS resources or activate AWS billing tags. The billing owner must apply actual AWS resource tags, then activate eligible cost-allocation keys. Allow for billing processing delays and verify their appearance in Cost Explorer/CUR. AWS split cost allocation is a separate opt-in path that creates EKS Pod-level records and AWS-generated attributes such as `aws:eks:namespace`; it does not make every namespace label an EC2 tag. Review its data-source prerequisites and increased report volume.

Cost allocation tag backfill can cover up to 12 months **when those resources were tagged historically**; it cannot invent missing historical tags. A Cost Category classifies billing records using reviewed rules—it is not a dashboard. Its CLI creation operation is `aws ce create-cost-category-definition`, not `create-cost-category`. Use keys and values that actually appear in the billing dataset, and separately configure saved Cost Explorer reports or dashboards.

**Read-only inventory of unattached volumes**

Run the following only with the intended account/Region and an existing ownership tag. It leaves AWS CLI pagination enabled and prints a JSON candidate list. The limited tag syntax is intentional; adapt JSON filters if your real tag contains other characters.

```bash
set -euo pipefail
: "${AWS_REGION:?Set the reviewed Region}"
: "${EXPECTED_ACCOUNT_ID:?Set the reviewed 12-digit account ID}"
: "${OWNER_TAG_KEY:?Set an existing ownership tag key}"
: "${OWNER_TAG_VALUE:?Set its exact value}"
[[ "$EXPECTED_ACCOUNT_ID" =~ ^[0-9]{12}$ ]]
# This example accepts a restricted literal subset, excluding wildcards/shorthand separators.
[[ "$OWNER_TAG_KEY" =~ ^[a-zA-Z0-9_./:@+-]+$ ]]
[[ "$OWNER_TAG_VALUE" =~ ^[a-zA-Z0-9_./:@+-]+$ ]]
actual_account=$(aws sts get-caller-identity --region "$AWS_REGION" \
  --query Account --output text --no-cli-pager)
[[ "$actual_account" == "$EXPECTED_ACCOUNT_ID" ]] || {
  echo "Account mismatch" >&2
  exit 1
}
aws ec2 describe-volumes --region "$AWS_REGION" --page-size 100 \
  --filters Name=status,Values=available \
    "Name=tag:$OWNER_TAG_KEY,Values=$OWNER_TAG_VALUE" \
  --query 'Volumes[].{id:VolumeId,zone:AvailabilityZone,sizeGiB:Size,created:CreateTime,state:State}' \
  --output json --no-cli-pager
```

`available` means unattached now, not unused or safe to delete. The creation time is not a last-used timestamp. Check PV/PVC ownership, reclaim policy, pending workloads, backups, snapshots, and disaster-recovery requirements with the owner. Similarly, low CPU/memory (including an arbitrary 5% cutoff) does not prove a Pod or load balancer is unnecessary. Use representative history and application/SLO signals; do not replace missing metrics with an empty “idle Pods” result.

**Budget example**

This standalone Terraform example uses a real, activated billing tag and an approved recipient. The **1,000 USD monthly limit and 80% alert** are illustrative settings, not observed costs. Import/reconcile an existing budget instead of creating a conflicting owner. Validate the chosen cost basis and tag coverage; a tag filter can omit untagged/shared charges. Applying this example creates a real notification configuration.

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.64.0"
    }
  }
}

variable "account_id" {
  type = string
}

variable "region" {
  type = string
}

variable "budget_name" {
  type = string
}

variable "activated_tag_key" {
  type = string
}

variable "tag_value" {
  type = string
}

variable "notification_email" {
  type        = string
  description = "Approved budget owner; applying this example configures real email notifications."
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

resource "aws_budgets_budget" "eks_monthly" {
  account_id   = var.account_id
  name         = var.budget_name
  budget_type  = "COST"
  limit_amount = "1000"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filter {
    name   = "TagKeyValue"
    values = [join("$", [var.activated_tag_key, var.tag_value])]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.notification_email]
  }
}
```

Budgets use processed billing data and do not impose a hard spending cap. Budget Actions can apply IAM/SCP controls or target supported EC2/RDS instances, but require separate permissions and operational review. The resource-efficiency dashboard above is not a billing dashboard.

Review requests with VPA recommendations and peak/SLO history, and coordinate HPA with node scaling. Karpenter/Cluster Autoscaler and Spot may reduce costs only when workload, interruption, capacity, and disruption constraints permit. Smaller requests alone do not reduce the bill unless provisioned capacity or pricing changes. Track agreed actions and measured outcomes in regular owner reviews.

Other options miss this feedback loop: collecting everything adds telemetry cost/noise; performance alone does not show spending; a final monthly bill arrives too late for timely investigation.

**Primary references:** [OpenCost installation](https://opencost.io/docs/installation/helm), [AWS tag activation](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/activating-tags.html), [tag backfill](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/cost-allocation-backfill.html), [split cost allocation](https://docs.aws.amazon.com/cur/latest/userguide/split-cost-allocation-data.html), [Budget Actions](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-controls.html).

</details>
