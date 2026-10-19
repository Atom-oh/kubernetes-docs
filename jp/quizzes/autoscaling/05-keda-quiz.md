# KEDA クイズ

> **最終更新**: 2026年10月16日

このクイズでは、KEDA（Kubernetes Event-driven Autoscaling）への理解を確認します。

## 質問1: KEDAの基本概念

<details>
<summary>KEDAとは何ですか。また、主な利点は何ですか？</summary>

**回答:**
KEDA（Kubernetes Event-driven Autoscaling）は、イベントに基づいてKubernetesアプリケーションを自動的にスケーリングできるオープンソースプロジェクトです。

**主な利点:**
1. **イベント駆動型スケーリング**: メッセージキュー、データベース、ストリームなど、さまざまなイベントソースに基づいてスケーリングできます。
2. **ゼロへのスケール**: 対応するトリガーは、最小レプリカ数、アクティベーションしきい値、クールダウンに応じてワークロードを起動・停止します。
3. **幅広いスケーラー**: 50種類以上の組み込みスケーラーに加え、カスタムスケーラーも利用できます。
4. **Kubernetesとのネイティブな統合**: 既存のHPAと連携します。
5. **クラウドに依存しない設計**: 必要なAPI、ID、接続性を備えた互換性のあるKubernetes環境で動作します。
6. **デプロイモデル**: 標準インストールには、オペレーター、Metrics API Server、Admission Webhookが含まれます。

KEDA 2.21の例は、公開されているKubernetes 1.34～1.36のテスト済み対応範囲を使用します。Kubernetes 1.37のHPAも、オブジェクト/外部メトリクスを対象としたベータ版のゼロへのスケールをサポートします。ゼロへのスケールはKEDAだけが実現できる機能ではありません。
</details>

## 質問2: KEDAのアーキテクチャ

<details>
<summary>KEDAの主なコンポーネントは何ですか？</summary>

**回答:**
- **KEDA Operator**: ScaledObjectおよびScaledJobリソースを管理します。
- **Metrics Adapter**: Kubernetes API AggregationとオペレーターのMetrics Serviceを介して、HPAに外部メトリクスを公開します。
- **Admission Webhook**: 対応するKEDAリソース設定を検証します。
- **ScaledObject**: スケーリング対象とトリガーを定義します。
- **ScaledJob**: オペレーターがJobを作成します。HPAによるスケーリングは行いません。
- **TriggerAuthentication**: 外部システムの認証情報を指定します。
- **ClusterTriggerAuthentication**: クラスター全体で使用する認証情報を指定します。

ScaledObjectでは、アクティベーションとレプリカ数ゼロへのスケールをKEDAが担い、ゼロ以外のレプリカ数へのスケーリングをHPAが担います。ポーリング、HPAの同期、メトリクスキャッシュのタイミングはそれぞれ異なります。ワークロードごとにスケーリングの管理者を1つにしてください。
</details>

## 質問3: スケーラーの種類

<details>
<summary>KEDAがサポートする主なスケーラーは何ですか？</summary>

**回答:**
**メッセージキューのスケーラー:**
- Apache Kafka、RabbitMQ、Azure Service Bus、AWS SQS
- Redis Lists/Streams、Google Pub/Sub

**データベースのスケーラー:**
- MySQL、PostgreSQL、MongoDB

**クラウドサービスのスケーラー:**
- AWS CloudWatch、Azure Monitor、GCP Pub/Sub
- Prometheus、InfluxDB

**その他のスケーラー:**
- Cron（時間ベース）、metrics-api（数値を返すHTTPエンドポイント）。リクエストのインターセプト/バッファリングには別のHTTPアドオンを使用します。
- CPU/Memory、External Push

**カスタムスケーラー:**
- External Scalerを介してユーザー定義メトリクスを使用します。
</details>

## 質問4: ScaledObjectの設定

<details>
<summary>Kafkaを使ったScaledObjectの設定例を示してください。</summary>

**回答:**

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


既存のTLS対応Kafkaリスナー、信頼済みCA、および有効なSASL設定/認証情報を含む`kafka-secrets`があることを前提とします。ブローカーがプライベートCAを使用する場合は、CA参照を追加してください。コンシューマーアプリケーション側も、互換性のある認証とオフセット動作を使用する必要があります。デフォルトの`allowIdleConsumers=false`では、レプリカ数はパーティション数によって制限されます。オフセットが`latest`または無効な状態で新しいグループを使う場合、アクティベーションに関する注意点があります。
</details>

## 質問5: カスタムメトリクスによるスケーリング

<details>
<summary>Prometheusメトリクスを使ってカスタムスケーリングを設定するには、どうすればよいですか？</summary>

**回答:**

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


これらは、参照先の章にあるHTTPコレクターを使う個別の代替例です。固定のCronスケジュールではGoogle Calendarの予定を読み取りません。また、External Pushには実際に動作するKEDA gRPCサービスが必要です。コレクターは独立して稼働させてください。メトリクスが存在しない場合や古い場合は、ゼロとして扱うのではなくエラーとして扱います。
</details>

## 質問6: Cronによるスケーリング

<details>
<summary>時間ベースのスケーリングを実装するには、どうすればよいですか？</summary>

**回答:**

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


Cronの各時間帯はレプリカ数の下限を指定します。HPAは各推奨値を合算するのではなく、最大の推奨値を選択します。ゼロへのスケールには、クールダウンとコントローラーの処理時間が必要です。2つ目の例は毎年11月24日に実行されるスケジュールであり、ブラックフライデーを自動計算するものではありません。Cronには年を指定するフィールドがありません。一度限りのスケジュールは、用途が終わったら確認または削除してください。
</details>

## 質問7: ScaledJobの設定

<details>
<summary>Jobベースのワークロードをスケーリングするには、どう設定しますか？</summary>

**回答:**

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


参照先の章で定義されている`rabbitmq-auth`/認証情報と、`provider: aws`および`identityOwner: keda`を指定した`aws-credentials`を、ここで使うキューに合わせて使用します。実際のワーカーイメージ、コンシューマーID、メッセージの確認応答、可視性タイムアウト、冪等性を適切に設定してください。`jobTargetRef`はテンプレートを1つ持つJobSpecです。ScaledJobはHPAを使用しません。
</details>

## 質問8: Istioメトリクスによるスケーリング

<details>
<summary>Istioサービスメッシュのメトリクスを使ってスケーリングするには、どう設定しますか？</summary>

**回答:**

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


RPSの合計には`AverageValue`（合計値/目標値）を使用します。サービス全体のp95レイテンシーとエラー率には`Value`（現在のレプリカ数×メトリクス値/目標値）を使用します。これは異なるフィードバックループです。これらの例は、指定した名前空間の送信先側メトリクスと、適切な量のサンプルが存在することを前提とします。メトリクス系列の欠落やNaNに備え、スケーリング上限を設定してください。また、レプリカを増やすことで実際に改善するか検証します。レイテンシーやエラーの原因が下流にある場合もあり、スケーリングよりアラートが適切なことがあります。本番環境でのスケーリング結果は測定されていません。
</details>

## 質問9: 監視とトラブルシューティング

<details>
<summary>KEDAのスケーリング動作をどのように監視しますか？</summary>

**回答:**
1. **KEDAのメトリクスを確認する:**

   ```bash
   kubectl get scaledobject
   kubectl describe scaledobject <name>
   kubectl get hpa
   ```


2. **KEDAのログを確認する:**

   ```bash
   kubectl logs -n keda -l app=keda-operator
   kubectl logs -n keda -l app=keda-operator-metrics-apiserver
   ```


3. **イベントを監視する:**

   ```bash
   kubectl get events --field-selector involvedObject.name=<scaledobject-name>
   ```


4. **Prometheusメトリクスを確認する:**

   ```promql
   # KEDA scaler metrics
   keda_scaler_metrics_value
   keda_scaled_object_paused
   keda_scaled_object_errors_total

   # HPA metrics
   kube_horizontalpodautoscaler_status_current_replicas
   kube_horizontalpodautoscaler_status_desired_replicas
   ```


5. **よくあるトラブルを調査する:**

   ```bash
   # Inspect existing operator diagnostics
   kubectl logs -n keda deployment/keda-operator --since=10m

   # Check metrics adapter status
   kubectl get apiservice v1beta1.external.metrics.k8s.io

   # Check authentication information
   kubectl get triggerauthentication
   kubectl get secret <auth-secret> -o json | jq '{name: .metadata.name, type: .type, keys: ((.data // {}) | keys)}'
   ```


2つ目のManagerプロセスは削除済みです。オペレーターPod内で`/manager`をもう一度起動しても、接続テストにはなりません。既存のログ、リソースの状態、およびAPIServiceの状態を確認してください。ここに示したKEDAメトリクスは2.20で検証済みです。HPAレプリカ数のメトリクスには、kube-state-metricsと設定済みのスクレーパーが必要です。
</details>

## 質問10: Amazon EKSとの統合

<details>
<summary>KEDAをAmazon EKSと統合する際に考慮すべきことは何ですか？</summary>

**回答:**
1. **IAM権限の設定:**

   ```yaml
   serviceAccount:
     operator:
       create: true
       name: keda-operator
       annotations:
         eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/keda-role
         eks.amazonaws.com/sts-regional-endpoints: 'true'
   ```


2. **AWSサービスとの統合:**

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


3. **ネットワークに関する考慮事項:**
   - 対応するVPCエンドポイント、DNS/ルート/ポリシー、およびNAT/エンドポイント/AZの総コストを評価してください。削減効果はワークロードによって異なります。
   - セキュリティグループを設定します。
   - サブネットのルーティングを設定します。

4. **監視との統合:**

   ```yaml
   annotations:
     prometheus.io/scrape: 'true'
     prometheus.io/port: '8080'
     prometheus.io/path: /metrics
   ```


5. **Fargateに関する考慮事項:**
   - KEDAコンポーネントはEC2に配置するのが一般的ですが、これはプロトコル上の必須条件ではありません。コンピュートの配置、API Aggregationへの到達性、Webhookを検証してください。
   - 条件を満たすターゲットワークロードは、対応するプロファイルとキャパシティがあればFargateを使用できます。EKS Pod IdentityはFargateをサポートしないため、IRSAなど適用可能なIDの仕組みを使用してください。
   - リソース上限とスケーリングポリシーを調整します。

6. **コストの最適化:**
   - Spotインスタンスと併用します。
   - ゼロへのスケールでコストを削減します。
   - 適切なスケーリングしきい値を設定します。

YAMLのトリガー一覧は個別のScaledObjectに含める断片であり、参照先の章にある`aws-credentials`認証を前提とします。CloudWatchの`RequestCount`に対する`Sum`/60秒は期間内の件数であり、RPSではありません。IRSAには、正しくスコープされた既存のOIDC信頼関係と読み取り権限が必要です。コンシューマー側の権限は別途必要です。スクレイプ用アノテーションだけではCloudWatch Container Insightsはインストールも設定もされません。コレクター、IAM、エクスポート先を構成してください。ワークロードをゼロにスケールしても、ノードやすべてのコストが自動的に削減されるわけではありません。
</details>

---

**採点:**
- 8～10問正解: 優秀（KEDAのエキスパートレベル）
- 6～7問正解: 良好（追加学習を推奨）
- 4～5問正解: 平均（基本的な内容を復習してください）
- 0～3問正解: 不十分（全コンテンツを再学習してください）
