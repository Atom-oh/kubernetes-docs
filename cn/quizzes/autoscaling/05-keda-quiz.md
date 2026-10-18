# KEDA 测验

> **最后更新**：October 16, 2026

本测验用于检验你对 KEDA（Kubernetes 事件驱动自动伸缩）的理解。

## 问题 1：KEDA 基本概念

<details>
<summary>KEDA 是什么？它有哪些主要优势？</summary>

**答案：**
KEDA（Kubernetes 事件驱动自动伸缩）是一个开源项目，可根据事件自动扩缩 Kubernetes 应用程序。

**主要优势：**
1. **事件驱动伸缩**：根据各种事件源（消息队列、数据库、流等）进行伸缩
2. **缩容至零**：支持的触发器会根据最小副本数、激活阈值和冷却时间激活或停用工作负载。
3. **支持多种 Scaler**：提供 50 多种内置 Scaler，并支持自定义 Scaler
4. **Kubernetes 原生**：可与现有的 Kubernetes HPA 集成
5. **云平台无关**：可在兼容的 Kubernetes 环境中运行，但需要相应的 API、身份凭证和网络连接。
6. **部署模型**：标准安装包括 operator、指标 API 服务器和准入 Webhook。

KEDA2.21 示例使用其公布的 Kubernetes1.34–1.36 测试范围。Kubernetes1.37 HPA 也支持对对象/外部指标进行 beta 版缩容至零；缩容至零并非 KEDA 独有的能力。
</details>

## 问题 2：KEDA 架构

<details>
<summary>KEDA 的主要组件有哪些？</summary>

**答案：**
- **KEDA Operator**：管理 ScaledObject 和 ScaledJob 资源
- **指标适配器**：通过 Kubernetes API 聚合和 operator 指标服务向 HPA 提供外部指标。
- **准入 Webhook**：验证受支持的 KEDA 资源配置。
- **ScaledObject**：定义伸缩目标和触发器
- **ScaledJob**：由 operator 创建的 Job；它们不会由 HPA 伸缩。
- **TriggerAuthentication**：外部系统的身份验证信息
- **ClusterTriggerAuthentication**：集群级身份验证

ScaledObject 伸缩时，KEDA 负责激活和缩容至零，HPA 负责非零副本数的伸缩。轮询、HPA 同步和指标缓存的行为各不相同。每个工作负载只应由一个伸缩控制器负责。
</details>

## 问题 3：Scaler 类型

<details>
<summary>KEDA 支持哪些主要的 Scaler？</summary>

**答案：**
**消息队列 Scaler：**
- Apache Kafka、RabbitMQ、Azure Service Bus、AWS SQS
- Redis Lists/Streams、Google Pub/Sub

**数据库 Scaler：**
- MySQL、PostgreSQL、MongoDB

**云服务 Scaler：**
- AWS CloudWatch、Azure Monitor、GCP Pub/Sub
- Prometheus、InfluxDB

**其他 Scaler：**
- Cron（基于时间）、metrics-api（数值型 HTTP 端点）；请求拦截/缓冲功能属于独立的 HTTP add-on
- CPU/Memory、External Push

**自定义 Scaler：**
- 通过 External Scaler 提供用户定义的指标
</details>

## 问题 4：ScaledObject 配置

<details>
<summary>如何配置一个基于 Kafka 的 ScaledObject？</summary>

**答案：**
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

假设已有一个启用了 TLS 的 Kafka listener、受信任的 CA，以及包含有效 SASL 设置/凭证的 kafka-secrets。如果 broker 使用私有 CA，请添加 CA 引用。消费者应用也必须使用兼容的身份验证和 offset 行为。默认情况下，allowIdleConsumers=false，因此副本数受分区数限制；使用 latest/无效 offset 的新 consumer group 在激活方面存在注意事项。
</details>

## 问题 5：自定义指标伸缩

<details>
<summary>如何使用 Prometheus 指标配置自定义伸缩？</summary>

**答案：**
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

这些是使用源章节中 HTTP 收集器的不同替代方案。固定的 Cron 计划不会读取 Google Calendar，而 external-push 需要一个实际的 KEDA gRPC 服务。请确保收集器能够独立运行；指标缺失或过期属于错误，不应视为零。
</details>

## 问题 6：基于 Cron 的伸缩

<details>
<summary>如何实现基于时间的伸缩？</summary>

**答案：**
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

Cron 时间窗口会设定副本数下限；HPA 会选择建议值中的最大值，而不是将它们相加。缩容至零需要等待冷却时间和控制器完成处理。第二个示例表示每年 11 月 24 日的计划，并非自动计算的黑色星期五计划；Cron 没有年份字段。使用后请检查或移除一次性计划。
</details>

## 问题 7：ScaledJob 配置

<details>
<summary>如何配置基于 Job 的工作负载伸缩？</summary>

**答案：**
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

使用源章节中的 rabbitmq-auth/credentials 和 aws-credentials（provider: aws, identityOwner: keda），并根据这些队列进行调整。请提供真实的 worker 镜像、消费者身份、确认机制、可见性超时和幂等性保障。jobTargetRef 是一个包含单个模板的 JobSpec；ScaledJob 不使用 HPA。
</details>

## 问题 8：Istio 指标伸缩

<details>
<summary>如何使用 Istio 服务网格指标配置伸缩？</summary>

**答案：**
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

RPS 总量使用 AverageValue（总量/目标值）。服务级 p95 延迟和错误率使用 Value（当前副本数 × 指标值/目标值），这采用了不同的反馈机制。这些示例假定针对指定命名空间采集了 destination 端指标，且有具有代表性的非空样本。请处理缺失/NaN 序列，为伸缩设置上限，并测试增加副本是否确实有帮助；延迟/错误可能源自下游服务，通常更适合作为告警信号。尚未测量任何生产环境的伸缩结果。
</details>

## 问题 9：监控与故障排查

<details>
<summary>如何监控 KEDA 的伸缩活动？</summary>

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
   kubectl logs -n keda -l app=keda-operator-metrics-apiserver
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
   # Inspect existing operator diagnostics
   kubectl logs -n keda deployment/keda-operator --since=10m

   # Check metrics adapter status
   kubectl get apiservice v1beta1.external.metrics.k8s.io

   # Check authentication information
   kubectl get triggerauthentication
   kubectl get secret <auth-secret> -o json | jq '{name: .metadata.name, type: .type, keys: ((.data // {}) | keys)}'
   ```

已移除第二个管理进程：在 operator Pod 中再启动一个 /manager 并不能用于测试连通性。请使用现有日志、资源状态条件和 APIService 状态。所列 KEDA 指标已在2.20版本中验证；HPA 副本指标需要 kube-state-metrics 和已配置的 scraper。
</details>

## 问题 10：Amazon EKS 集成

<details>
<summary>将 KEDA 与 Amazon EKS 集成时需要考虑什么？</summary>

**答案：**
1. **IAM 权限设置**：
   ```yaml
   serviceAccount:
     operator:
       create: true
       name: keda-operator
       annotations:
         eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/keda-role
         eks.amazonaws.com/sts-regional-endpoints: 'true'
   ```

2. **AWS 服务集成**：
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

3. **网络注意事项**：
   - 评估匹配的 VPC endpoint、DNS/路由/策略，以及 NAT/endpoint/AZ 的总成本；节省的费用取决于工作负载。
   - 安全组配置
   - 子网路由设置

4. **监控集成**：
   ```yaml
   annotations:
     prometheus.io/scrape: 'true'
     prometheus.io/port: '8080'
     prometheus.io/path: /metrics
   ```

5. **Fargate 注意事项**：
   - KEDA 组件通常部署在 EC2 上；这不是普遍适用的协议要求。请验证计算资源放置、API 聚合的可达性以及 Webhook。
   - 符合条件的目标可以使用 Fargate，但需配置匹配的 profile 和容量。EKS Pod Identity 不支持 Fargate；请使用适用的身份机制，例如 IRSA。
   - 调整资源限制和伸缩策略

6. **成本优化**：
   - 配合 Spot 实例使用
   - 利用缩容至零节省成本
   - 设置合适的伸缩阈值

YAML 中的触发器列表是用于不同 ScaledObject 的片段，并假设使用源章节中的 aws-credentials 身份验证。CloudWatch RequestCount 配合 Sum/60seconds 表示每个周期内的计数，而不是 RPS。IRSA 需要已存在且作用域配置正确的 OIDC 信任关系和读取权限；消费者权限需单独配置。仅添加 scrape 注解并不会安装或配置 CloudWatch Container Insights：还需配置 collector/IAM/导出目标。工作负载缩容至零不会自动移除节点或消除所有成本。
</details>

---

**评分：**
- 答对 8-10 题：优秀（KEDA 专家水平）
- 答对 6-7 题：良好（建议进一步学习）
- 答对 4-5 题：一般（需要复习基本概念）
- 答对 0-3 题：不足（需要重新学习全部内容）
