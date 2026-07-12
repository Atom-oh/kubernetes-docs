# KEDA 测验

本测验用于测试你对 KEDA (Kubernetes Event-driven Autoscaling) 的理解。

## 问题 1：KEDA 基本概念

<details>
<summary>KEDA 是什么，它的主要优势是什么？</summary>

**答案：**
KEDA (Kubernetes Event-driven Autoscaling) 是一个开源项目，使 Kubernetes 应用能够基于事件自动扩缩。

**主要优势：**
1. **事件驱动扩缩**：基于各种事件源（消息队列、数据库、流等）进行扩缩
2. **缩至零**：在没有活动时缩减到 0 个副本以节省成本
3. **多样的 Scaler 支持**：内置 50+ 个 Scaler，并支持自定义 Scaler
4. **Kubernetes 原生**：与现有 Kubernetes HPA 集成
5. **云无关**：可在任何 Kubernetes 环境中运行
6. **简单的部署模型**：通过单个 Operator 即可轻松部署
</details>

## 问题 2：KEDA 架构

<details>
<summary>KEDA 的主要组件有哪些？</summary>

**答案：**
- **KEDA Operator**：管理 ScaledObject 和 ScaledJob 资源
- **Metrics Adapter**：向 HPA 提供自定义指标
- **Admission Webhooks**：资源验证和变更
- **ScaledObject**：定义扩缩目标和触发器
- **ScaledJob**：基于 Job 的工作负载扩缩
- **TriggerAuthentication**：外部系统认证信息
- **ClusterTriggerAuthentication**：集群级认证
</details>

## 问题 3：Scaler 类型

<details>
<summary>KEDA 支持的主要 Scaler 有哪些？</summary>

**答案：**
**消息队列 Scaler：**
- Apache Kafka, RabbitMQ, Azure Service Bus, AWS SQS
- Redis Lists/Streams, Google Pub/Sub

**数据库 Scaler：**
- MySQL, PostgreSQL, MongoDB, Cassandra

**云服务 Scaler：**
- AWS CloudWatch, Azure Monitor, GCP Pub/Sub
- Prometheus, InfluxDB

**其他 Scaler：**
- Cron（基于时间）, HTTP（基于请求）
- CPU/Memory, External Push

**自定义 Scaler：**
- 通过 External Scaler 使用用户定义指标
</details>

## 问题 4：ScaledObject 配置

<details>
<summary>基于 Kafka 的 ScaledObject 配置示例是什么？</summary>

**答案：**
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

## 问题 5：自定义指标扩缩

<details>
<summary>如何使用 Prometheus 指标配置自定义扩缩？</summary>

**答案：**
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

## 问题 6：基于 Cron 的扩缩

<details>
<summary>如何实现基于时间的扩缩？</summary>

**答案：**
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

## 问题 7：ScaledJob 配置

<details>
<summary>如何配置基于 Job 的工作负载扩缩？</summary>

**答案：**
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

## 问题 8：Istio 指标扩缩

<details>
<summary>如何使用 Istio service mesh 指标配置扩缩？</summary>

**答案：**
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

## 问题 9：监控与故障排查

<details>
<summary>如何监控 KEDA 的扩缩活动？</summary>

**答案：**
1. **检查 KEDA 指标**：
   ```bash
   kubectl get scaledobject
   kubectl describe scaledobject <name>
   kubectl get hpa
   ```

2. **检查 KEDA 日志**：
   ```bash
   kubectl logs -n keda -l app=keda-operator
   kubectl logs -n keda -l app=keda-metrics-apiserver
   ```

3. **事件监控**：
   ```bash
   kubectl get events --field-selector involvedObject.name=<scaledobject-name>
   ```

4. **Prometheus 指标**：
   ```promql
   # KEDA scaler metrics
   keda_scaler_metrics_value
   keda_scaled_object_paused
   keda_scaled_object_errors_total

   # HPA metrics
   kube_horizontalpodautoscaler_status_current_replicas
   kube_horizontalpodautoscaler_status_desired_replicas
   ```

5. **常见故障排查**：
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

## 问题 10：Amazon EKS 集成

<details>
<summary>将 KEDA 与 Amazon EKS 集成时有哪些注意事项？</summary>

**答案：**
1. **IAM 权限设置**：
   ```yaml
   # IRSA (IAM Roles for Service Accounts) configuration
   serviceAccount:
     annotations:
       eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT:role/keda-role
   ```

2. **AWS 服务集成**：
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

3. **网络注意事项**：
   - 使用 VPC endpoints（节省成本）
   - Security group 配置
   - Subnet 路由设置

4. **监控集成**：
   ```yaml
   # CloudWatch Container Insights
   annotations:
     prometheus.io/scrape: "true"
     prometheus.io/port: "8080"
     prometheus.io/path: "/metrics"
   ```

5. **Fargate 注意事项**：
   - KEDA Operator 在 EC2 nodes 上运行
   - 扩缩后的工作负载可以使用 Fargate
   - 调整资源限制和扩缩策略

6. **成本优化**：
   - 与 Spot instances 搭配使用
   - 通过缩至零节省成本
   - 设置适当的扩缩阈值
</details>

---

**评分：**
- 8-10 题正确：优秀（KEDA 专家级）
- 6-7 题正确：良好（建议继续学习）
- 4-5 题正确：一般（需要复习基本概念）
- 0-3 题正确：不足（需要重新学习全部内容）
