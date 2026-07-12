# KEDA クイズ

このクイズでは、KEDA (Kubernetes Event-driven Autoscaling) に関する理解を確認します。

## 質問 1: KEDA の基本概念

<details>
<summary>KEDA とは何で、その主な利点は何ですか?</summary>

**回答:**
KEDA (Kubernetes Event-driven Autoscaling) は、Kubernetes アプリケーションをイベントに基づいて自動的にスケーリングできるようにするオープンソースプロジェクトです。

**主な利点:**
1. **Event-driven Scaling**: さまざまなイベントソース (メッセージキュー、データベース、ストリームなど) に基づくスケーリング
2. **Scale to Zero**: アクティビティがないときにレプリカを 0 までスケールダウンしてコストを削減
3. **Diverse Scaler Support**: 50 以上の組み込み scaler とカスタム scaler のサポート
4. **Kubernetes Native**: 既存の Kubernetes HPA と統合
5. **Cloud Agnostic**: 任意の Kubernetes 環境で動作
6. **Simple Deployment Model**: 単一の operator による簡単なデプロイ
</details>

## 質問 2: KEDA Architecture

<details>
<summary>KEDA の主なコンポーネントは何ですか?</summary>

**回答:**
- **KEDA Operator**: ScaledObject および ScaledJob リソースを管理
- **Metrics Adapter**: HPA にカスタムメトリクスを提供
- **Admission Webhooks**: リソースの検証と変更
- **ScaledObject**: スケーリング対象とトリガーを定義
- **ScaledJob**: Job ベースのワークロードスケーリング
- **TriggerAuthentication**: 外部システムの認証情報
- **ClusterTriggerAuthentication**: クラスター レベルの認証
</details>

## 質問 3: Scaler Types

<details>
<summary>KEDA がサポートする主な scaler は何ですか?</summary>

**回答:**
**Message Queue Scalers:**
- Apache Kafka, RabbitMQ, Azure Service Bus, AWS SQS
- Redis Lists/Streams, Google Pub/Sub

**Database Scalers:**
- MySQL, PostgreSQL, MongoDB, Cassandra

**Cloud Service Scalers:**
- AWS CloudWatch, Azure Monitor, GCP Pub/Sub
- Prometheus, InfluxDB

**Other Scalers:**
- Cron (時間ベース), HTTP (リクエストベース)
- CPU/Memory, External Push

**Custom Scalers:**
- External Scaler 経由のユーザー定義メトリクス
</details>

## 質問 4: ScaledObject Configuration

<details>
<summary>Kafka ベースの ScaledObject 設定例は何ですか?</summary>

**回答:**
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

## 質問 5: Custom Metrics Scaling

<details>
<summary>Prometheus メトリクスを使用してカスタムスケーリングを設定するにはどうしますか?</summary>

**回答:**
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

## 質問 6: Cron-based Scaling

<details>
<summary>時間ベースのスケーリングを実装するにはどうしますか?</summary>

**回答:**
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

## 質問 7: ScaledJob Configuration

<details>
<summary>Job ベースのワークロードスケーリングを設定するにはどうしますか?</summary>

**回答:**
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

## 質問 8: Istio Metrics Scaling

<details>
<summary>Istio service mesh メトリクスを使用してスケーリングを設定するにはどうしますか?</summary>

**回答:**
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

## 質問 9: Monitoring and Troubleshooting

<details>
<summary>KEDA のスケーリング活動を監視するにはどうしますか?</summary>

**回答:**
1. **KEDA Metrics の確認**:
   ```bash
   kubectl get scaledobject
   kubectl describe scaledobject <name>
   kubectl get hpa
   ```

2. **KEDA Logs の確認**:
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

5. **一般的なトラブルシューティング**:
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

## 質問 10: Amazon EKS Integration

<details>
<summary>KEDA を Amazon EKS と統合する際の考慮事項は何ですか?</summary>

**回答:**
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
   - VPC endpoints を使用 (コスト削減)
   - セキュリティグループ設定
   - サブネットルーティング設定

4. **Monitoring Integration**:
   ```yaml
   # CloudWatch Container Insights
   annotations:
     prometheus.io/scrape: "true"
     prometheus.io/port: "8080"
     prometheus.io/path: "/metrics"
   ```

5. **Fargate Considerations**:
   - KEDA Operator は EC2 nodes で実行
   - スケーリング対象のワークロードは Fargate を使用可能
   - リソース制限とスケーリングポリシーを調整

6. **Cost Optimization**:
   - Spot instances と併用
   - scale to zero によりコストを削減
   - 適切なスケーリングしきい値を設定
</details>

---

**スコア:**
- 8-10 正解: 優秀 (KEDA エキスパートレベル)
- 6-7 正解: 良好 (追加学習を推奨)
- 4-5 正解: 平均 (基本概念の復習が必要)
- 0-3 正解: 不十分 (全コンテンツの再学習が必要)
