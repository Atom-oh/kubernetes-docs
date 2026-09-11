# KEDA Quiz

> **Last Updated**: September 11, 2026

This quiz tests your understanding of KEDA (Kubernetes Event-driven Autoscaling).

## Question 1: KEDA Basic Concepts

<details>
<summary>What is KEDA and what are its main benefits?</summary>

**Answer:**
KEDA (Kubernetes Event-driven Autoscaling) is an open source project that enables Kubernetes applications to scale automatically based on events.

**Main Benefits:**
1. **Event-driven Scaling**: Scaling based on various event sources (message queues, databases, streams, etc.)
2. **Scale to Zero**: Supported triggers activate/deactivate workloads according to minimum replicas, activation thresholds and cooldown.
3. **Diverse Scaler Support**: 50+ built-in scalers and custom scaler support
4. **Kubernetes Native**: Integrates with existing Kubernetes HPA
5. **Cloud Agnostic**: Runs in compatible Kubernetes environments with required APIs, identity and connectivity.
6. **Deployment Model**: Standard installation includes an operator, metrics API server and admission webhooks.

KEDA2.20 examples use its published Kubernetes1.33–1.35 tested window. Kubernetes1.37 HPA also supports beta scale-to-zero for object/external metrics; zero is not uniquely possible with KEDA.
</details>

## Question 2: KEDA Architecture

<details>
<summary>What are the main components of KEDA?</summary>

**Answer:**
- **KEDA Operator**: Manages ScaledObject and ScaledJob resources
- **Metrics Adapter**: Exposes external metrics to HPA via Kubernetes API aggregation and the operator metrics service.
- **Admission Webhooks**: Validate supported KEDA resource configurations.
- **ScaledObject**: Defines scaling targets and triggers
- **ScaledJob**: Operator-created Jobs; these are not scaled by an HPA.
- **TriggerAuthentication**: External system authentication information
- **ClusterTriggerAuthentication**: Cluster-level authentication

ScaledObject scaling uses KEDA for activation/zero and HPA for nonzero replicas. Polling, HPA sync and metric caching differ. Use one scaling owner per workload.
</details>

## Question 3: Scaler Types

<details>
<summary>What are the main scalers supported by KEDA?</summary>

**Answer:**
**Message Queue Scalers:**
- Apache Kafka, RabbitMQ, Azure Service Bus, AWS SQS
- Redis Lists/Streams, Google Pub/Sub

**Database Scalers:**
- MySQL, PostgreSQL, MongoDB

**Cloud Service Scalers:**
- AWS CloudWatch, Azure Monitor, GCP Pub/Sub
- Prometheus, InfluxDB

**Other Scalers:**
- Cron (time-based), metrics-api (numeric HTTP endpoint); request interception/buffering belongs to the separate HTTP add-on
- CPU/Memory, External Push

**Custom Scalers:**
- User-defined metrics via External Scaler
</details>

## Question 4: ScaledObject Configuration

<details>
<summary>What is an example Kafka-based ScaledObject configuration?</summary>

**Answer:**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: kafka-scaledobject
  namespace: default
spec:
  scaleTargetRef:
    name: kafka-consumer
  minReplicaCount: 0
  maxReplicaCount: 30
  pollingInterval: 30
  cooldownPeriod: 300
  triggers:
  - type: kafka
    metadata:
      bootstrapServers: kafka.default.svc.cluster.local:9093
      consumerGroup: my-group
      topic: my-topic
      lagThreshold: '5'
      offsetResetPolicy: latest
      tls: enable
    authenticationRef:
      name: kafka-auth
---
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: kafka-auth
  namespace: default
spec:
  secretTargetRef:
  - parameter: sasl
    name: kafka-secrets
    key: sasl
  - parameter: username
    name: kafka-secrets
    key: username
  - parameter: password
    name: kafka-secrets
    key: password
```

Assume an existing TLS Kafka listener, trusted CA and kafka-secrets containing valid SASL settings/credentials. Add a CA reference when the broker uses a private CA. The consumer application must use compatible auth and offset behavior too. With the default allowIdleConsumers=false, replicas are limited by partition count; a new group with latest/invalid offsets has activation caveats.
</details>

## Question 5: Custom Metrics Scaling

<details>
<summary>How do you configure custom scaling using Prometheus metrics?</summary>

**Answer:**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: prometheus-scaledobject
  namespace: default
spec:
  scaleTargetRef:
    name: my-app
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      threshold: '100'
      query: sum(rate(http_requests_total{job="my-app"}[1m]))
      ignoreNullValues: 'false'
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: twitter-scaledobject
  namespace: default
spec:
  scaleTargetRef:
    name: twitter-processor
  triggers:
  - type: metrics-api
    metadata:
      url: http://twitter-metrics-collector.default.svc.cluster.local/metrics
      targetValue: '10'
      valueLocation: tweet_count
  minReplicaCount: 1
  maxReplicaCount: 20
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: calendar-scaledobject
  namespace: default
spec:
  scaleTargetRef:
    name: calendar-processor
  triggers:
  - type: metrics-api
    metadata:
      url: http://calendar-metrics-collector.default.svc.cluster.local/metrics
      targetValue: '1'
      valueLocation: upcoming_events
  minReplicaCount: 1
  maxReplicaCount: 10
```

These are separate alternatives using the source chapter’s HTTP collectors. A fixed Cron schedule does not read Google Calendar, and external-push requires a real KEDA gRPC service. Keep collectors available independently; absent or stale metrics are errors, not zero.
</details>

## Question 6: Cron-based Scaling

<details>
<summary>How do you implement time-based scaling?</summary>

**Answer:**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: cron-scaledobject
  namespace: default
spec:
  scaleTargetRef:
    name: batch-processor
  minReplicaCount: 0
  maxReplicaCount: 20
  triggers:
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: 0 9 * * 1-5
      end: 0 18 * * 1-5
      desiredReplicas: '10'
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: 0 0 * * *
      end: 0 6 * * *
      desiredReplicas: '5'
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: 0 10 * * 0,6
      end: 0 16 * * 0,6
      desiredReplicas: '2'
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: event-scaledobject
  namespace: default
spec:
  scaleTargetRef:
    name: event-handler
  triggers:
  - type: cron
    metadata:
      timezone: America/New_York
      start: 0 0 24 11 *
      end: 59 23 24 11 *
      desiredReplicas: '50'
```

Cron windows supply a replica floor; the HPA chooses the largest recommendation rather than adding them. Scale-to-zero waits for cooldown/controller timing. The second example is an annual November24 schedule, not an automatic Black Friday calculation; Cron has no year field. Review or remove one-off schedules after use.
</details>

## Question 7: ScaledJob Configuration

<details>
<summary>How do you configure Job-based workload scaling?</summary>

**Answer:**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledJob
metadata:
  name: batch-job-scaler
  namespace: default
spec:
  jobTargetRef:
    backoffLimit: 4
    template:
      spec:
        containers:
        - name: batch-processor
          image: my-batch-app:latest
          command:
          - ./process-batch
        restartPolicy: Never
  pollingInterval: 30
  maxReplicaCount: 10
  successfulJobsHistoryLimit: 5
  failedJobsHistoryLimit: 5
  triggers:
  - type: rabbitmq
    metadata:
      protocol: amqp
      queueName: batch-queue
      mode: QueueLength
      value: '5'
    authenticationRef:
      name: rabbitmq-auth
---
apiVersion: keda.sh/v1alpha1
kind: ScaledJob
metadata:
  name: sqs-job-scaler
  namespace: default
spec:
  jobTargetRef:
    backoffLimit: 4
    template:
      spec:
        containers:
        - name: sqs-processor
          image: sqs-worker:latest
        restartPolicy: Never
  triggers:
  - type: aws-sqs-queue
    metadata:
      queueURL: https://sqs.us-east-1.amazonaws.com/123456789012/my-queue
      queueLength: '10'
      awsRegion: us-east-1
    authenticationRef:
      name: aws-credentials
  maxReplicaCount: 10
```

Use the source chapter’s rabbitmq-auth/credentials and aws-credentials (provider: aws, identityOwner: keda), adjusted for these queues. Supply real worker images, consumer identity, acknowledgements, visibility timeouts and idempotency. jobTargetRef is a JobSpec with one template; ScaledJob does not use HPA.
</details>

## Question 8: Istio Metrics Scaling

<details>
<summary>How do you configure scaling using Istio service mesh metrics?</summary>

**Answer:**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: istio-scaledobject
  namespace: default
spec:
  scaleTargetRef:
    name: productpage
  minReplicaCount: 1
  maxReplicaCount: 20
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      threshold: '50'
      query: "sum(rate(istio_requests_total{\n  reporter=\"destination\",\n      \
        \    destination_service_namespace=\"default\",\n          destination_service_name=\"\
        productpage\",\n  response_code!~\"5.*\"\n}[1m]))\n"
      ignoreNullValues: 'false'
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      threshold: '0.5'
      query: "histogram_quantile(0.95,\n  sum(rate(istio_request_duration_milliseconds_bucket{\n\
        \    reporter=\"destination\",\n          destination_service_namespace=\"\
        default\",\n          destination_service_name=\"productpage\"\n  }[1m]))\
        \ by (le)\n) / 1000\n"
      ignoreNullValues: 'false'
    metricType: Value
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: error-rate-scaler
  namespace: default
spec:
  scaleTargetRef:
    name: backend-service
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      threshold: '0.05'
      query: (sum(rate(istio_requests_total{reporter="destination",destination_service_namespace="default",destination_service_name="backend-service",response_code=~"5.*"}[2m]))
        or vector(0)) / clamp_min(sum(rate(istio_requests_total{reporter="destination",destination_service_namespace="default",destination_service_name="backend-service"}[2m])),
        0.001)
      ignoreNullValues: 'false'
    metricType: Value
  minReplicaCount: 1
  maxReplicaCount: 10
```

RPS totals use AverageValue (total/target). Service-wide p95 latency and error ratio use Value (current replicas × metric/target), which is a different feedback loop. These examples assume destination-side metrics for the named namespace and representative nonempty samples. Guard missing/NaN series, bound scaling and test whether added replicas actually help; latency/errors can originate downstream and are often safer alert signals. No production scaling result has been measured.
</details>

## Question 9: Monitoring and Troubleshooting

<details>
<summary>How do you monitor KEDA's scaling activities?</summary>

**Answer:**
1. **Check KEDA Metrics**:
   ```bash
   kubectl get scaledobject
   kubectl describe scaledobject <name>
   kubectl get hpa
   ```

2. **Check KEDA Logs**:
   ```bash
   kubectl logs -n keda -l app=keda-operator
   kubectl logs -n keda -l app=keda-operator-metrics-apiserver
   ```

3. **Event Monitoring**:
   ```bash
   kubectl get events --field-selector involvedObject.name=<scaledobject-name>
   ```

4. **Prometheus Metrics**:
   ```promql
   # KEDA scaler metrics
   keda_scaler_metrics_value
   keda_scaled_object_paused
   keda_scaled_object_errors_total

   # HPA metrics
   kube_horizontalpodautoscaler_status_current_replicas
   kube_horizontalpodautoscaler_status_desired_replicas
   ```

5. **Common Troubleshooting**:
   ```bash
   # Inspect existing operator diagnostics
   kubectl logs -n keda deployment/keda-operator --since=10m

   # Check metrics adapter status
   kubectl get apiservice v1beta1.external.metrics.k8s.io

   # Check authentication information
   kubectl get triggerauthentication
   kubectl get secret <auth-secret> -o json | jq '{name: .metadata.name, type: .type, keys: ((.data // {}) | keys)}'
   ```

The second manager process has been removed: starting another /manager inside an operator Pod is not a connectivity test. Use existing logs, resource conditions and APIService status. The listed KEDA metrics are verified for2.20; HPA replica metrics require kube-state-metrics and a configured scraper.
</details>

## Question 10: Amazon EKS Integration

<details>
<summary>What are the considerations when integrating KEDA with Amazon EKS?</summary>

**Answer:**
1. **IAM Permission Setup**:
   ```yaml
   serviceAccount:
     operator:
       create: true
       name: keda-operator
       annotations:
         eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/keda-role
         eks.amazonaws.com/sts-regional-endpoints: 'true'
   ```

2. **AWS Service Integration**:
   ```yaml
   - type: aws-sqs-queue
     metadata:
       queueURL: https://sqs.us-west-2.amazonaws.com/123456789012/my-queue
       awsRegion: us-west-2
       queueLength: '5'
     authenticationRef:
       name: aws-credentials
   - type: aws-cloudwatch
     metadata:
       namespace: AWS/ApplicationELB
       metricName: RequestCount
       dimensionName: LoadBalancer
       dimensionValue: app/my-alb/1234567890
       awsRegion: us-west-2
       targetMetricValue: '100'
       minMetricValue: '0'
       metricStat: Sum
       metricStatPeriod: '60'
       metricCollectionTime: '300'
     authenticationRef:
       name: aws-credentials
   ```

3. **Network Considerations**:
   - Evaluate matching VPC endpoints, DNS/routes/policies and total NAT/endpoint/AZ cost; savings are workload-dependent.
   - Security group configuration
   - Subnet routing setup

4. **Monitoring Integration**:
   ```yaml
   annotations:
     prometheus.io/scrape: 'true'
     prometheus.io/port: '8080'
     prometheus.io/path: /metrics
   ```

5. **Fargate Considerations**:
   - EC2 is a common placement for KEDA components; this is not a universal protocol requirement. Validate compute placement, API aggregation reachability and webhooks.
   - Eligible targets can use Fargate with matching profiles and capacity. EKS Pod Identity does not support Fargate; use an applicable identity mechanism such as IRSA.
   - Adjust resource limits and scaling policies

6. **Cost Optimization**:
   - Use with Spot instances
   - Save costs with scale to zero
   - Set appropriate scaling thresholds

The YAML trigger list is a fragment for separate ScaledObjects and assumes the source chapter’s aws-credentials authentication. CloudWatch RequestCount with Sum/60seconds is a count per period, not RPS. IRSA requires an existing correctly scoped OIDC trust and read permissions; consumer permissions are separate. Scrape annotations alone do not install or configure CloudWatch Container Insights: configure the collector/IAM/export destination. Workload scale-to-zero does not automatically remove nodes or all cost.
</details>

---

**Scoring:**
- 8-10 correct: Excellent (KEDA expert level)
- 6-7 correct: Good (additional learning recommended)
- 4-5 correct: Average (basic concepts review needed)
- 0-3 correct: Insufficient (full content re-study needed)
