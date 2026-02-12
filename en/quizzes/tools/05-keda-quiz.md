# KEDA Quiz

This quiz tests your understanding of KEDA (Kubernetes Event-driven Autoscaling).

## Question 1: KEDA Basic Concepts

<details>
<summary>What is KEDA and what are its main benefits?</summary>

**Answer:**
KEDA (Kubernetes Event-driven Autoscaling) is an open source project that enables Kubernetes applications to scale automatically based on events.

**Main Benefits:**
1. **Event-driven Scaling**: Scaling based on various event sources (message queues, databases, streams, etc.)
2. **Scale to Zero**: Scale down to 0 replicas when there's no activity to save costs
3. **Diverse Scaler Support**: 50+ built-in scalers and custom scaler support
4. **Kubernetes Native**: Integrates with existing Kubernetes HPA
5. **Cloud Agnostic**: Works in any Kubernetes environment
6. **Simple Deployment Model**: Easy deployment with a single operator
</details>

## Question 2: KEDA Architecture

<details>
<summary>What are the main components of KEDA?</summary>

**Answer:**
- **KEDA Operator**: Manages ScaledObject and ScaledJob resources
- **Metrics Adapter**: Provides custom metrics to HPA
- **Admission Webhooks**: Resource validation and mutation
- **ScaledObject**: Defines scaling targets and triggers
- **ScaledJob**: Job-based workload scaling
- **TriggerAuthentication**: External system authentication information
- **ClusterTriggerAuthentication**: Cluster-level authentication
</details>

## Question 3: Scaler Types

<details>
<summary>What are the main scalers supported by KEDA?</summary>

**Answer:**
**Message Queue Scalers:**
- Apache Kafka, RabbitMQ, Azure Service Bus, AWS SQS
- Redis Lists/Streams, Google Pub/Sub

**Database Scalers:**
- MySQL, PostgreSQL, MongoDB, Cassandra

**Cloud Service Scalers:**
- AWS CloudWatch, Azure Monitor, GCP Pub/Sub
- Prometheus, InfluxDB

**Other Scalers:**
- Cron (time-based), HTTP (request-based)
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
      bootstrapServers: kafka:9092
      consumerGroup: my-group
      topic: my-topic
      lagThreshold: '5'
      offsetResetPolicy: latest
    authenticationRef:
      name: kafka-auth

---
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: kafka-auth
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
spec:
  scaleTargetRef:
    name: my-app
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      metricName: http_requests_per_second
      threshold: '100'
      query: sum(rate(http_requests_total{job="my-app"}[1m]))

---
# Twitter metrics-based scaling
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: twitter-scaledobject
spec:
  scaleTargetRef:
    name: twitter-processor
  triggers:
  - type: external-push
    metadata:
      scalerAddress: twitter-scaler:8080
      metricName: twitter_mentions
      threshold: '10'

---
# Google Calendar-based scaling
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: calendar-scaledobject
spec:
  scaleTargetRef:
    name: meeting-processor
  triggers:
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: "0 9 * * 1-5"  # Weekday 9 AM
      end: "0 18 * * 1-5"   # Weekday 6 PM
      desiredReplicas: "5"
```
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
spec:
  scaleTargetRef:
    name: batch-processor
  minReplicaCount: 0
  maxReplicaCount: 20
  triggers:
  # Business hours scaling (weekdays 9-18)
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: "0 9 * * 1-5"
      end: "0 18 * * 1-5"
      desiredReplicas: "10"

  # Nightly batch processing (daily midnight)
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: "0 0 * * *"
      end: "0 6 * * *"
      desiredReplicas: "5"

  # Weekend minimal operation
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: "0 10 * * 0,6"
      end: "0 16 * * 0,6"
      desiredReplicas: "2"

---
# Special event response scaling
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: event-scaledobject
spec:
  scaleTargetRef:
    name: event-handler
  triggers:
  # Black Friday preparation
  - type: cron
    metadata:
      timezone: America/New_York
      start: "0 0 24 11 *"  # November 24th midnight
      end: "59 23 24 11 *"  # November 24th 23:59
      desiredReplicas: "50"
```
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
spec:
  jobTargetRef:
    template:
      spec:
        template:
          spec:
            containers:
            - name: batch-processor
              image: my-batch-app:latest
              command: ["./process-batch"]
            restartPolicy: Never
        backoffLimit: 4
  pollingInterval: 30
  maxReplicaCount: 10
  successfulJobsHistoryLimit: 5
  failedJobsHistoryLimit: 5
  triggers:
  - type: rabbitmq
    metadata:
      queueName: batch-queue
      host: amqp://rabbitmq:5672
      queueLength: '5'
    authenticationRef:
      name: rabbitmq-auth

---
# AWS SQS-based Job scaling
apiVersion: keda.sh/v1alpha1
kind: ScaledJob
metadata:
  name: sqs-job-scaler
spec:
  jobTargetRef:
    template:
      spec:
        template:
          spec:
            containers:
            - name: sqs-processor
              image: sqs-worker:latest
            restartPolicy: Never
  triggers:
  - type: aws-sqs-queue
    metadata:
      queueURL: https://sqs.us-east-1.amazonaws.com/123456789/my-queue
      queueLength: '10'
      awsRegion: us-east-1
    authenticationRef:
      name: aws-credentials
```
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
spec:
  scaleTargetRef:
    name: productpage
  minReplicaCount: 1
  maxReplicaCount: 20
  triggers:
  # Request rate-based scaling
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      metricName: istio_request_rate
      threshold: '50'
      query: |
        sum(rate(istio_requests_total{
          destination_service_name="productpage",
          response_code!~"5.*"
        }[1m]))

  # Response time-based scaling
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      metricName: istio_response_time
      threshold: '0.5'
      query: |
        histogram_quantile(0.95,
          sum(rate(istio_request_duration_milliseconds_bucket{
            destination_service_name="productpage"
          }[1m])) by (le)
        ) / 1000

---
# Service mesh error rate-based scaling
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: error-rate-scaler
spec:
  scaleTargetRef:
    name: backend-service
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      metricName: error_rate
      threshold: '0.05'  # 5% error rate
      query: |
        sum(rate(istio_requests_total{
          destination_service_name="backend-service",
          response_code=~"5.*"
        }[1m])) /
        sum(rate(istio_requests_total{
          destination_service_name="backend-service"
        }[1m]))
```
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
   kubectl logs -n keda -l app=keda-metrics-apiserver
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
   # Scaler connection test
   kubectl exec -n keda deployment/keda-operator -- /manager --zap-log-level=debug

   # Check metrics adapter status
   kubectl get apiservice v1beta1.external.metrics.k8s.io

   # Check authentication information
   kubectl get triggerauthentication
   kubectl describe secret <auth-secret>
   ```
</details>

## Question 10: Amazon EKS Integration

<details>
<summary>What are the considerations when integrating KEDA with Amazon EKS?</summary>

**Answer:**
1. **IAM Permission Setup**:
   ```yaml
   # IRSA (IAM Roles for Service Accounts) configuration
   serviceAccount:
     annotations:
       eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT:role/keda-role
   ```

2. **AWS Service Integration**:
   ```yaml
   # SQS Scaler
   - type: aws-sqs-queue
     metadata:
       queueURL: https://sqs.region.amazonaws.com/account/queue-name
       awsRegion: us-west-2

   # CloudWatch Scaler
   - type: aws-cloudwatch
     metadata:
       namespace: AWS/ApplicationELB
       metricName: RequestCount
       dimensionName: LoadBalancer
       dimensionValue: app/my-alb/1234567890
   ```

3. **Network Considerations**:
   - Use VPC endpoints (cost savings)
   - Security group configuration
   - Subnet routing setup

4. **Monitoring Integration**:
   ```yaml
   # CloudWatch Container Insights
   annotations:
     prometheus.io/scrape: "true"
     prometheus.io/port: "8080"
     prometheus.io/path: "/metrics"
   ```

5. **Fargate Considerations**:
   - KEDA Operator runs on EC2 nodes
   - Scaled workloads can use Fargate
   - Adjust resource limits and scaling policies

6. **Cost Optimization**:
   - Use with Spot instances
   - Save costs with scale to zero
   - Set appropriate scaling thresholds
</details>

---

**Scoring:**
- 8-10 correct: Excellent (KEDA expert level)
- 6-7 correct: Good (additional learning recommended)
- 4-5 correct: Average (basic concepts review needed)
- 0-3 correct: Insufficient (full content re-study needed)
