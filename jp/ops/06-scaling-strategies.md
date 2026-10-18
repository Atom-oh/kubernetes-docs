# スケーリング戦略

> **本番環境での検証**: Spot を採用する前に、[EKS Spot 本番実験と結果の評価](./17-spot-production-experiments.md)を使い、中断、フォールバック、正確性、コストを検証してください。設定例や予測削減額は実測値ではありません。

> **レビュー時の基準**: Prometheus Adapter 0.12.0／chart 5.3.0、KEDA 2.21.0、VPA 1.8.0／公式 chart 0.14.0、Goldilocks 4.16.2／chart 11.2.0  \
> **最終レビュー日**: 2026年10月16日。バージョンを固定した chart、CRD、Kubernetes OpenAPI、ローカルレンダリングを確認しました。実環境へのインストール、負荷テスト、SQS／データベースへのアクセス、Pod のリサイズは実施していません。

< [前へ: GitOps Automation](05-gitops-automation.md) | [目次](README.md) | [次へ: 運用アラート](07-observability-alerts.md) >

カスタムメトリクス HPA、KEDA、VPA、Spot 配置は、それぞれ分けて扱います。**ワークロードのレプリカ数を管理するオートスケーラーは1つだけにしてください。** `podinfo` を対象とする HPA、RPS ScaledObject、Cron ScaledObject は相互に代替となる構成であり、同時に適用してはいけません。

KEDA 2.21 の公式デプロイメント文書では、検証済みの Kubernetes バージョン範囲は 1.34～1.36 とされています。この範囲を確認し、それより新しいディストリビューションは別途検証してください。このガイドのネイティブオブジェクト検査には Kubernetes 1.36.2 の OpenAPI を使用しました。実環境での互換性テストではありません。

## 1. HPA とカスタムメトリクス

![収集されたメトリクス値、Adapter へのクエリ応答、API 集約、および HPA Controller による Deployment の scale 更新。](../.gitbook/assets/en-ops-06-scaling-strategies-0.png)

[インタラクティブ図](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-06-scaling-strategies-0.html)

| API | この例の Provider | 役割 |
|---|---|---|
| `metrics.k8s.io` | metrics-server | CPU とメモリのリソースメトリクス |
| `custom.metrics.k8s.io` | Prometheus Adapter | Pod などの Kubernetes オブジェクトに関連付けられたメトリクス |
| `external.metrics.k8s.io` | KEDA を選んだ場合の KEDA metrics API server | 外部イベントのメトリクス |

Prometheus Adapter は resource／external API も提供できますが、この例で有効にするのは custom metrics だけです。同じ APIService を複数の Provider に所有させないでください。CloudWatch Exporter をインストールしただけでは、Kubernetes の external metrics API は作成されません。

### 前提条件とデモアプリケーション

metrics-server、Prometheus Operator／Prometheus、cert-manager を準備します。values 内の Prometheus Service アドレスを実際のエンドポイントに置き換えてください。Prometheus の `serviceMonitorSelector` と `serviceMonitorNamespaceSelector` が `scaling-demo` の ServiceMonitor を選択する必要があります。収集された時系列に、想定される `namespace`、`pod`、`service` のターゲットラベルが付いていることを確認してください。

以下の公開 Podinfo 6.15.0 マルチプラットフォームイメージの digest は確認済みです。この例を応用するときは、実際のメトリクス、probe、シャットダウンの要件を満たす承認済みアプリケーションに置き換えてください。

```yaml
# fixtures/application.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: scaling-demo
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: podinfo
  namespace: scaling-demo
spec:
  replicas: 3
  selector:
    matchLabels:
      app: podinfo
  template:
    metadata:
      labels:
        app: podinfo
    spec:
      automountServiceAccountToken: false
      terminationGracePeriodSeconds: 45
      containers:
        - name: podinfo
          image: ghcr.io/stefanprodan/podinfo@sha256:ec73780a8425f59ea49f5bc8cdff0d598805a224fbaa1f86c67a244f250fa9da
          ports:
            - name: http
              containerPort: 9898
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: "1"
              memory: 512Mi
          readinessProbe:
            httpGet:
              path: /readyz
              port: http
          livenessProbe:
            httpGet:
              path: /healthz
              port: http
---
apiVersion: v1
kind: Service
metadata:
  name: podinfo
  namespace: scaling-demo
  labels:
    app: podinfo
spec:
  selector:
    app: podinfo
  ports:
    - name: http
      port: 80
      targetPort: http
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: podinfo
  namespace: scaling-demo
spec:
  selector:
    matchLabels:
      app: podinfo
  namespaceSelector:
    matchNames: [scaling-demo]
  endpoints:
    - port: http
      path: /metrics
      interval: 15s
```

Podinfo の `http_requests_total` は HTTP リクエストのカウンターです。ヘルスチェックなどの運用リクエストも加算されることがあるため、本番業務のトラフィックだけを測るとは限りません。同じターゲットを重複収集する annotation ベースの scrape 経路を追加しないでください。

### Adapter の設定

```yaml
# fixtures/adapter-values.yaml
replicas: 2
prometheus:
  url: http://prometheus.monitoring.svc
  port: 9090
certManager:
  enabled: true
podDisruptionBudget:
  enabled: true
  minAvailable: 1
  maxUnavailable: null
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi
rules:
  default: false
  external: []
  custom:
    - seriesQuery: 'http_requests_total{namespace="scaling-demo",pod!=""}'
      resources:
        overrides:
          namespace:
            resource: namespace
          pod:
            resource: pod
      name:
        matches: "^http_requests_total$"
        as: http_requests_per_second
      metricsQuery: 'sum(rate(http_requests_total{<<.LabelMatchers>>}[2m])) by (<<.GroupBy>>)'
```

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm upgrade --install prometheus-adapter prometheus-community/prometheus-adapter \
  --version 5.3.0 --namespace monitoring --create-namespace \
  --kube-context "$TARGET_CONTEXT" --values adapter-values.yaml

kubectl --context "$TARGET_CONTEXT" get --raw \
  /apis/custom.metrics.k8s.io/v1beta1
```

証明書と APIService への CA 注入は cert-manager が管理します。`tls.enable=false` のような Helm オプション名だけを見て通信が暗号化されるか判断せず、レンダリングされた APIService、証明書、検証設定を確認してください。ここでは external rule がないため、Adapter が external API を所有する想定はありません。

Helm の `rules.custom` と Adapter server の生設定は構造が異なります。任意の ConfigMap を作成しても、既存の chart がそれを読み込むようにはなりません。設定の所有者を1つにしてください。

### Pod ごとの RPS と CPU を使う HPA

```yaml
# fixtures/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: podinfo
  namespace: scaling-demo
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: podinfo
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "100"
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15
        - type: Pods
          value: 4
          periodSeconds: 15
      selectPolicy: Max
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
        - type: Pods
          value: 2
          periodSeconds: 60
      selectPolicy: Min
```

複数メトリクスは優先順位リストでも、単純な「CPU へのフォールバック」でもありません。HPA は各メトリクスから推奨値を計算し、**最も大きいレプリカ数**を選びます。メトリクスが取得できないとスケールダウンが止まることがあります。一方、有効なメトリクスがスケールアップを要求すれば、増加できる場合があります。

対象の Pod とメトリクスがすべて Ready であると仮定した基本比率は、`ceil(currentReplicas × currentMetric / targetMetric)` です。平均 250 RPS の Pod が4つあり、目標が100なら、計算上の目標は10レプリカです。min／max、未 Ready の Pod、欠落メトリクス、許容誤差、behavior 設定によって実際の判断は変わります。

| 設定 | 意味 |
|---|---|
| スケールアップの安定化 | 最近の低い推奨値も考慮し、急激な増加を抑える |
| スケールダウンの安定化 | 最近の高い推奨値も考慮し、急激な減少を抑える |
| `periodSeconds` | 許可される変更量を計算する対象期間 |
| `selectPolicy: Max` | より大きな変更を許可する Policy |
| スケールダウンの `Min` | 削除数をより少なくする Policy |

安定化期間は、各観測のたびに固定時間の待機が新しく始まるわけではありません。`periodSeconds` は1～1,800秒、安定化期間は0～3,600秒を指定できるため、300秒の Policy は有効です。500% の増加 Policy は、現在数に**さらに500%を加えた**最大6倍まで増やせます。

現在20レプリカの場合、この例のスケールダウン Policy は、Percent 10% と Pods 2 のどちらも1回あたり最大2 Pod の削除を許可します。履歴、推奨値、その他の制限も適用されるため、特定の時点に18 Pod が Ready であることを保証するものではありません。

一般に HPA の `minReplicas: 0` を使えるかは、Kubernetes のバージョン、`HPAScaleToZero`、メトリクスの前提条件によります。この例では3を使用します。外部キューを使ってゼロまでスケールする方法は、別途 KEDA で扱います。メトリクス API が正常に応答しても、イメージ取得、ノード容量、アプリケーション起動にかかる時間は解消されません。

### External metrics と確認方法

キュー深度はゲージです。累積カウンターの名前を `*_total` から変更しても、現在のバックログを表す値にはなりません。全体キューを Pod ごとの処理目標と比較するには、通常 `AverageValue` が適切です。`Value` でも同じ計算になるとは限りません。

CloudWatch と連携するには、KEDA の直接 scaler を使うか、Exporter → Prometheus → Adapter の external rule まで一式を構成する必要があります。実際の Exporter の名前とラベルを HPA に合わせ、APIService の所有者が競合しないようにします。`AWS/ApplicationELB RequestCount` に任意の TargetGroup dimension を追加しないでください。[レビュー済み KEDA ガイド](../autoscaling/01-keda.md)の CloudWatch 例を参照してください。

```bash
kubectl --context "$TARGET_CONTEXT" get --raw \
  '/apis/custom.metrics.k8s.io/v1beta1/namespaces/scaling-demo/pods/*/http_requests_per_second'
kubectl --context "$TARGET_CONTEXT" describe hpa podinfo -n scaling-demo
kubectl --context "$TARGET_CONTEXT" get deployment,pods -n scaling-demo
```

無制限ループを実行する古い BusyBox イメージを使わず、分離されたテスト環境で上限のある負荷テストを実施してください。Deployment の `replicas` を GitOps とオートスケーラーのどちらが所有するかも一致させてください。

## 2. KEDA によるイベント駆動スケーリング

KEDA operator は ScaledObject／HPA と、有効化／ゼロへの遷移を管理します。ゼロより大きいレプリカ数での水平スケーリングには HPA が関与します。ScaledJob は別に Job を作成し、HPA は Job のレプリカフィールドを変更しません。

### インストールと AWS の認証情報

全般的なインストール、互換性、ネットワーキングについては[KEDA ガイド](../autoscaling/01-keda.md)に従ってください。AWS の例では、**KEDA operator に IRSA を明示的に使用します**。事前にクラスターの OIDC provider、正確な namespace／ServiceAccount に対する信頼設定、キュー読み取り用 IAM role を準備してください。

```yaml
# fixtures/keda-values.yaml
# This example explicitly uses IRSA on the KEDA operator.
# Prepare the cluster OIDC provider, scoped trust and queue-read role first.
podIdentity:
  aws:
    irsa:
      enabled: true
      roleArn: arn:aws:iam::123456789012:role/KedaQueueReadRole
```

```bash
helm repo add kedacore https://kedacore.github.io/charts
helm repo update
helm upgrade --install keda kedacore/keda \
  --version 2.21.0 --namespace keda --create-namespace \
  --kube-context "$TARGET_CONTEXT" --values keda-values.yaml
```

role ARN を承認済みの値に置き換えてください。古い `provider: aws-eks` オプションは EKS Pod Identity を意味しません。IRSA と Pod Identity は別の構成です。別の方式を選ぶ場合は、operator の SDK credential chain、association、trust をその方式に合わせて設定する必要があります。

### RPS ScaledObject

競合する HPA の所有権を解消するか、サポート対象の移行手順に従ったうえで、この**代替構成**を選択します。

```yaml
# fixtures/keda-rps.yaml
# Alternative to hpa.yaml. Do not let both own podinfo's replica count.
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: podinfo
  namespace: scaling-demo
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: podinfo
  minReplicaCount: 3
  maxReplicaCount: 20
  pollingInterval: 15
  cooldownPeriod: 300
  fallback:
    failureThreshold: 3
    replicas: 5
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
  triggers:
    - type: prometheus
      name: requests
      metricType: AverageValue
      metadata:
        serverAddress: http://prometheus.monitoring.svc:9090
        query: sum(rate(http_requests_total{namespace="scaling-demo",service="podinfo"}[2m]))
        threshold: "100"
        activationThreshold: "0"
        ignoreNullValues: "false"
    - type: cpu
      metricType: Utilization
      metadata:
        value: "70"
```

`AverageValue` のしきい値100は、**Pod ごとに100 RPS を目標とする値**であり、総トラフィックに対する無条件のスケールアップしきい値ではありません。たとえば合計1,000 RPS なら、他の制限を適用する前の計算では10レプリカになります。activation のしきい値は有効化の制御に使うもので、HPA の目標値とは異なります。

`ignoreNullValues=false` にすると、クエリ結果の欠落を正常なゼロ負荷として黙って扱うことを防げます。集約した数値を1つ返し、エラー、NaN、トラフィックがない場合を意図的に処理してください。fallback は対応するメトリクスで失敗が繰り返された場合に使うもので、あらゆるメトリクス Provider、HPA、ノード障害から復旧するものではありません。

HTTP の例では3 Pod を維持します。唯一の稼働シグナルをその Pod 自身から取得している状態で Pod をすべて削除すると、新しい HTTP トラフィックを観測して再有効化する経路がなくなることがあります。ゼロまでスケールするには、外部キューまたは別の activation 機構が必要です。

### SQS キュー

実際の `sqs-worker` Deployment と、そのキューコンシューマー専用の権限を準備してください。KEDA がキュー属性を読み取る権限と、worker がメッセージを受信、削除、visibility を変更する権限は異なります。

```yaml
# fixtures/keda-sqs.yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: keda-aws
  namespace: scaling-demo
spec:
  podIdentity:
    provider: aws
    identityOwner: keda
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: sqs-worker
  namespace: scaling-demo
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sqs-worker
  minReplicaCount: 0
  maxReplicaCount: 50
  pollingInterval: 15
  cooldownPeriod: 60
  triggers:
    - type: aws-sqs-queue
      authenticationRef:
        name: keda-aws
      metadata:
        queueURL: https://sqs.ap-northeast-2.amazonaws.com/REPLACE_ACCOUNT/my-queue
        queueLength: "10"
        activationQueueLength: "0"
        scaleOnInFlight: "true"
        scaleOnDelayed: "false"
        awsRegion: ap-northeast-2
```

`activationQueueLength: "0"` は0を超えると有効化します。値を `"1"` にすると、1件以上ではなく**1件を超えた場合**に有効になります。処理中／遅延中のメッセージや visibility timeout も確認してください。DLQ のバックログが自動的に含まれるわけではありません。

polling は KEDA の確認頻度を指し、HPA の同期周期や Pod の起動時間ではありません。1から複数へのスケールと、ゼロからの有効化は異なります。`cooldownPeriod` はどのような場合にも適用されるスケールダウン待機時間ではありません。処理に時間がかかる場合は、終了、再試行、重複排除、visibility の扱いを設計してください。

### PostgreSQL の作業キュー

データベース接続数の増加を根拠にアプリケーションをスケールすると、接続の逼迫が悪化することがあります。この例では worker が実際に処理する未完了作業を使います。

```yaml
# fixtures/keda-postgresql.yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: queue-database
  namespace: scaling-demo
spec:
  secretTargetRef:
    - parameter: connection
      name: queue-database
      key: connection
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: database-worker
  namespace: scaling-demo
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: database-worker
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
    - type: postgresql
      authenticationRef:
        name: queue-database
      metricType: AverageValue
      metadata:
        query: SELECT count(*) FROM public.job_queue WHERE status = 'pending'
        targetQueryValue: "50"
        activationTargetQueryValue: "0"
```

`queue-database` Secret の `connection` key には有効な DSN が必要です。KEDA operator の環境変数に `sslmode=verify-full` と必要な CA path を設定し、ホスト名と CA を検証してください。認証情報を Git に保存しないでください。worker の書き込み権限とは別に、KEDA にはキューテーブルの読み取り権限を付与します。

数値を1つ返してください。1時間より古い未処理 job をすべて除外すると、バックログを隠す可能性があります。worker 側でも、原子的な claim、重複排除、完了状態の管理が必要です。

### Cron と複数メトリクス

```yaml
# fixtures/keda-cron.yaml
# Alternative to the preceding podinfo HPA/ScaledObject.
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: podinfo
  namespace: scaling-demo
spec:
  scaleTargetRef:
    name: podinfo
  minReplicaCount: 3
  maxReplicaCount: 50
  triggers:
    - type: cron
      metadata:
        timezone: Asia/Seoul
        start: "0 9 * * 1-5"
        end: "0 18 * * 1-5"
        desiredReplicas: "20"
    - type: cron
      metadata:
        timezone: Asia/Seoul
        start: "30 11 * * 1-5"
        end: "30 13 * * 1-5"
        desiredReplicas: "40"
    - type: prometheus
      metricType: AverageValue
      metadata:
        serverAddress: http://prometheus.monitoring.svc:9090
        query: sum(rate(http_requests_total{namespace="scaling-demo",service="podinfo"}[2m]))
        threshold: "100"
        ignoreNullValues: "false"
```

営業時間中の20レプリカと昼食時間帯の40レプリカを、メトリクスに基づく需要と比較します。最も大きい有効な要求が採用され、Cron と Prometheus に任意の優先順位があるわけではありません。これらの時間帯以外の最小数は3です。夜間や週末のスケジュールを加えるときは、設定したタイムゾーンで境界と重なりをテストしてください。

現行の KEDA は `advanced.scalingModifiers` をサポートしています。式が将来の機能だと説明したり、OR 動作だけがあると主張したりするのは誤りです。この例では、1つの worker が処理する**同じ単位のキューゲージ**を2つ組み合わせます。

```yaml
# fixtures/keda-composite.yaml
# Requires a worker that consumes both queues and the two named gauge series.
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: shared-queue-worker
  namespace: scaling-demo
spec:
  scaleTargetRef:
    name: shared-queue-worker
  minReplicaCount: 1
  maxReplicaCount: 30
  advanced:
    scalingModifiers:
      formula: queue_a + queue_b
      target: "50"
      activationTarget: "0"
      metricType: AverageValue
  triggers:
    - type: prometheus
      name: queue_a
      metadata:
        serverAddress: http://prometheus.monitoring.svc:9090
        query: sum(queue_messages_pending{queue="a"})
        threshold: "50"
        ignoreNullValues: "false"
    - type: prometheus
      name: queue_b
      metadata:
        serverAddress: http://prometheus.monitoring.svc:9090
        query: sum(queue_messages_pending{queue="b"})
        threshold: "50"
        ignoreNullValues: "false"
```

trigger 名は式から参照できる形式にし、式は数値メトリクスを返す必要があります。resource trigger や単位の異なる値を安易に組み合わせないでください。AND に近い動作が必要な場合は、条件に基づいて数値を返す式を設計し、処理の滞留、activation、障害時の動作をテストしてください。

### ScaledJob

これは実際の worker image と `batch-worker` ServiceAccount を指定して使うテンプレートです。

```yaml
# fixtures/keda-job.yaml
# Supply an actual bounded, idempotent SQS consumer image and worker identity.
apiVersion: keda.sh/v1alpha1
kind: ScaledJob
metadata:
  name: batch-processor
  namespace: scaling-demo
spec:
  pollingInterval: 30
  minReplicaCount: 0
  maxReplicaCount: 20
  successfulJobsHistoryLimit: 5
  failedJobsHistoryLimit: 5
  scalingStrategy:
    strategy: default
  jobTargetRef:
    parallelism: 1
    completions: 1
    activeDeadlineSeconds: 600
    backoffLimit: 2
    template:
      spec:
        serviceAccountName: batch-worker
        restartPolicy: Never
        containers:
          - name: processor
            image: REPLACE_WITH_APPROVED_WORKER_IMAGE
            env:
              - name: SQS_QUEUE_URL
                value: https://sqs.ap-northeast-2.amazonaws.com/REPLACE_ACCOUNT/batch-queue
            resources:
              requests:
                cpu: 250m
                memory: 256Mi
  triggers:
    - type: aws-sqs-queue
      authenticationRef:
        name: keda-aws
      metadata:
        queueURL: https://sqs.ap-northeast-2.amazonaws.com/REPLACE_ACCOUNT/batch-queue
        queueLength: "1"
        awsRegion: ap-northeast-2
```

履歴上限の単位は**件数**であり、秒数ではありません。`queueLength: "1"` を指定しても、特定のメッセージが厳密に一度だけ Job に割り当てられるわけではありません。worker はメッセージを受信、処理、削除し、再試行にも対応する必要があります。既定、accurate、custom、eager の各 strategy では、キューと実行中／保留中の Job が作成数に与える影響が異なります。

ScaledJob の Cron trigger は、対象時間帯に Job を繰り返し作成することがあります。「1日1回」を実現する場合は、意図した schedule／timeZone、concurrency、再試行 Policy を設定した Kubernetes CronJob を使ってください。チューニング用の例で `autoscaling.keda.sh/paused-replicas` を誤って有効なままにしないでください。

## 3. VPA と In-Place Resize

VPA が主に推奨するのは**リソース request**です。limit の扱いは `controlledValues` と既存の比率に依存し、常に独立した最適値を計算するわけではありません。

### 公式 chart と推奨モード

公式 VPA chart 0.14.0 と VPA 1.8.0 を使用します。すでに VPA がインストールされている場合は重ねてインストールせず、CRD、RBAC、設定の移行を先に確認してください。次の例では cert-manager／cainjector で webhook 証明書を管理します。

```yaml
# fixtures/vpa-values.yaml
admissionController:
  replicas: 2
  certGen:
    enabled: false
  certManager:
    enabled: true
    createSelfSignedIssuer:
      enabled: true
recommender:
  replicas: 2
updater:
  replicas: 2
  extraArgs:
    - --in-place-skip-disruption-budget=false
```

```bash
helm upgrade --install vpa \
  https://github.com/kubernetes/autoscaler/releases/download/vertical-pod-autoscaler-chart-0.14.0/vertical-pod-autoscaler-0.14.0.tgz \
  --namespace vpa --create-namespace --kube-context "$TARGET_CONTEXT" \
  --values vpa-values.yaml
```

この chart では `replicas` を使います。他の chart の `replicaCount` や `extraArgs` の構造を混在させないでください。複数の recommender／updater replica 向けに leader election を有効にします。ここでは disruption budget を無視する設定を明示的に無効にしています。文書化されていない Prometheus history オプションを追加しても、history pipeline が動作するとは限りません。

```yaml
# fixtures/vpa.yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: podinfo
  namespace: scaling-demo
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: podinfo
  updatePolicy:
    updateMode: "Off"
  resourcePolicy:
    containerPolicies:
      - containerName: podinfo
        controlledResources: [cpu, memory]
        controlledValues: RequestsOnly
        minAllowed:
          cpu: 100m
          memory: 128Mi
        maxAllowed:
          cpu: "1"
          memory: 512Mi
```

`Off` は Pod に適用せず、推奨値を生成するだけです。推奨値を適用する前に request／limit、quota、ノード容量を確認してください。同じ Deployment に複数の代替 VPA をインストールしないでください。

| モード | VPA 1.8.0 での動作 |
|---|---|
| `Off` | 推奨値だけを生成 |
| `Initial` | Pod 作成時に適用 |
| `Recreate` | 必要に応じて eviction／再作成を通じて適用 |
| `InPlaceOrRecreate` | in-place update を試み、失敗時は再作成 |
| `InPlace` | eviction への fallback なしで in-place を再試行。別途 feature gate が必要 |
| `Auto` | 非推奨で、現在は `Recreate` と同等。明示的なモードを選択 |

VPA 1.8.0 の in-place mode では、Kubernetes 1.33 以降を含む前提条件を確認してください。旧 `InPlaceOrRecreate` VPA gate は1.7で削除されましたが、`InPlace` には `--feature-gates=InPlace=true` が必要です。`minReplicas` は updater の対象選択条件であり、その数の Pod が利用可能であることを保証しません。

### Kubernetes の resize

Pod の in-place resize は1.27で alpha、1.33で beta となり、1.35で stable になりました。1.27以降のクラスターなら、既定で中断のない更新が使えるという意味ではありません。対応ノード／runtime、QoS、resize policy を確認してください。

```yaml
# Container fragment; select the restart behavior required by the application.
resizePolicy:
  - resourceName: cpu
    restartPolicy: NotRequired
  - resourceName: memory
    restartPolicy: RestartContainer
```

この patch はデモ Pod の CPU request を変更します。resize subresource を使う前に、実際の Pod 名を確認してください。

```json
{
  "spec": {
    "containers": [
      {
        "name": "podinfo",
        "resources": {
          "requests": {"cpu": "200m"},
          "limits": {"cpu": "1"}
        }
      }
    ]
  }
}
```

```bash
kubectl --context "$TARGET_CONTEXT" patch pod "$POD_NAME" -n scaling-demo \
  --subresource=resize --type=strategic --patch-file=resize-patch.json
kubectl --context "$TARGET_CONTEXT" get pod "$POD_NAME" -n scaling-demo -o json |
  jq '.status.conditions[]? | select(.type | startswith("PodResize"))'
```

`PodResizePending` の Deferred／Infeasible reason と `PodResizeInProgress` を確認してください。廃止された `.status.resize` field だけに頼らないでください。`RestartContainer` policy でコンテナが再起動される間も、Pod 自体は残ることがあります。QoS の変更、未対応の init／ephemeral container、ノード Policy、OS による制約もあります。

Pod を直接 resize しても Deployment template は永続的には更新されません。置換後の Pod にも設定を引き継ぐには、VPA または Git を通じて意図した設定を保存してください。

### Goldilocks と HPA の併用

```yaml
# fixtures/goldilocks-values.yaml
vpa:
  enabled: false
controller:
  enabled: true
dashboard:
  enabled: true
  service:
    type: ClusterIP
```

```bash
helm repo add fairwinds-stable https://charts.fairwinds.com/stable
helm repo update
helm upgrade --install goldilocks fairwinds-stable/goldilocks \
  --version 11.2.0 --namespace goldilocks --create-namespace \
  --kube-context "$TARGET_CONTEXT" --values goldilocks-values.yaml
```

既存の VPA インストールを再利用し、dashboard は ClusterIP のままにしてください。確認時は認証付きの内部経路または localhost への port-forward を使います。namespace で Goldilocks を有効にすると VPA が作成されることがあるため、手動管理している VPA target と所有権が競合しないようにしてください。

CPU 使用率を使う HPA と VPA の CPU request 変更は、使用率の分母を通じて相互作用します。`Initial` も新しい Pod の request を変更します。まずは推奨値を確認するか、HPA には RPS／backlog などのワークロードメトリクスを使い、VPA でサイズを調整して組み合わせた動作を検証してください。CPU HPA とメモリのみの VPA の併用でも、再起動やスケジューリングへの影響があります。

## 4. Pod Deletion Cost

この annotation は、ReplicaSet のスケールダウン時に使う**ベストエフォートの優先設定**です。ノード中断、eviction、Job、StatefulSet、異なる Deployment 間のレプリカ比率に適用されるグローバルな優先度ではありません。

```yaml
metadata:
  annotations:
    controller.kubernetes.io/pod-deletion-cost: "100"
```

現行 ReplicaSet の順序付けでは、まず割り当て状態、Pod phase、Ready 状態を比較し、その後に deletion cost を比較します。さらにノードあたりの replica 密度、Ready になってからの時間、再起動回数、作成時刻が考慮されます。cost を低くすれば常にほかのすべての候補より先に削除される、というわけではありません。

値は符号付き32ビットの範囲で、既定値は0です。優先度を変更する前に、**同じ ReplicaSet** に属する Pod の所有者と現在の状態を確認してください。

```bash
kubectl --context "$TARGET_CONTEXT" get pod "$POD_A" "$POD_B" \
  -n scaling-demo -o json |
  jq '.items[] | {name:.metadata.name,node:.spec.nodeName,
    owners:.metadata.ownerReferences,phase:.status.phase}'

kubectl --context "$TARGET_CONTEXT" annotate pod "$POD_A" -n scaling-demo \
  controller.kubernetes.io/pod-deletion-cost=-100 --overwrite
kubectl --context "$TARGET_CONTEXT" annotate pod "$POD_B" -n scaling-demo \
  controller.kubernetes.io/pod-deletion-cost=100 --overwrite
```

すべての Pod template に同じ cost を設定しても Pod 間の優先度は変わりません。CREATE admission webhook では、通常、将来割り当てられるノードを特定できません。また `preStop` は削除対象が選ばれた後に実行されるため、その選択には間に合いません。

動的に制御する実際の controller には、binding 後の処理、controller の所有者／UID の厳密な確認、対象を限定した patch 権限、annotation が nil の場合の処理、watch 再接続、API error の処理が必要です。Pod が Ready でも作業完了とは限りません。Job の進捗を annotation に記録しても、Job の終了が ReplicaSet の deletion cost ルールに従うことにはなりません。

## 5. Spot の配置と終了処理

以下は、既存の `default` NodeClass があるデモ用 Auto Mode クラスターを前提とします。どちらの pool も同じ workload label を提供するため、いずれの capacity type も配置対象になります。

```yaml
# fixtures/nodepools.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: web-spot
spec:
  weight: 100
  template:
    metadata:
      labels:
        workload-type: web
    spec:
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: [spot]
        - key: kubernetes.io/arch
          operator: In
          values: [amd64, arm64]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: [m7i.large, m7i.xlarge, m7g.large, m7g.xlarge, c7i.large, c7g.large]
  limits:
    cpu: "100"
    memory: 200Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 5m
    budgets:
      - nodes: "10%"
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: web-ondemand
spec:
  weight: 10
  template:
    metadata:
      labels:
        workload-type: web
    spec:
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: [on-demand]
        - key: kubernetes.io/arch
          operator: In
          values: [amd64, arm64]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: [m7i.large, m7i.xlarge, m7g.large, m7g.xlarge, c7i.large, c7g.large]
  limits:
    cpu: "50"
    memory: 100Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 10m
    budgets:
      - nodes: "10%"
```

weight が高いほど、provisioning 時に優先されます。ただし、Spot 容量をすべて使い切るまで On-Demand が選ばれないこと、固定の Spot 比率、または予約済みの fallback 容量を保証するものではありません。既存ノード、スケジューリング条件、AZ／instance type の可用性、quota、capacity が結果に影響します。

Auto Mode／Karpenter は `spot`／`on-demand` の値を持つ `karpenter.sh/capacity-type` を使います。Managed node group の `eks.amazonaws.com/capacityType` や独自 taint と混同しないでください。この例では `kubernetes.io/capacity-type` は使用しません。

### 配置 patch と PDB

```yaml
# fixtures/placement-patch.yaml
# Kustomize strategic-merge patch for application.yaml; not standalone.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: podinfo
  namespace: scaling-demo
spec:
  template:
    spec:
      nodeSelector:
        workload-type: web
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 80
              preference:
                matchExpressions:
                  - key: karpenter.sh/capacity-type
                    operator: In
                    values: [spot]
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: podinfo
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: podinfo
```

```yaml
# fixtures/pdb.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: podinfo
  namespace: scaling-demo
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: podinfo
```

```yaml
# fixtures/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - application.yaml
  - hpa.yaml
  - nodepools.yaml
  - pdb.yaml
patches:
  - path: placement-patch.yaml
```

ファイルを同じディレクトリに置き、`kustomize build .` で確認してください。この patch は単独で適用できる Deployment ではありません。`ScheduleAnyway` は soft な条件であり、`DoNotSchedule` の動作も対象となる topology domain の有無に依存します。topology spread constraint は任意の80／20比率や予備ノードを作成するものではありません。

PDB が制約するのは、対応する自発的な eviction です。HPA／ReplicaSet によるレプリカ数の削減や、実際の Spot ノード喪失は防止しません。`minAvailable: 2` は、常に2 Pod が稼働する保証ではありません。

### 中断と graceful shutdown

Auto Mode が管理する中断処理に、別の drain controller を重ねて追加しないでください。自己管理の Karpenter では、中断キュー／EventBridge の設定と権限が必要です。Node Termination Handler を使う場合は、対象ノードの管理方式と必要な前提条件を明確にしてください。

Spot の通知を受け取っても、アプリケーションに120秒残されている保証にはなりません。休止状態に関する例外、検知／drain／終了の遅延、実際の期限を考慮してください。

`terminationGracePeriodSeconds` は**Pod spec**に設定し、preStop hook の実行もその時間枠に含めます。実際の SIGTERM／drain 処理を実装し、readiness を解除した後の接続、メッセージ、再試行を検証してください。`/tmp/unhealthy` に触れても HTTP probe が自動的に失敗するわけではありません。また、「接続を閉じる」と出力してもデータベースの connection pool は閉じません。

外部通知や Pushgateway への呼び出しが終了処理を無期限に妨げないようにしてください。PriorityClass と deletion cost は Spot による reclaim を防ぎません。

### コストと容量

CPU request の gauge に対する `increase()` は node-hour ではありません。実際の稼働時間と、それに対応する時刻、AZ、platform、購入タイプのコストデータを使用してください。価格データがない部分を無料として扱ってはいけません。

同等の使用量を前提にした On-Demand baseline を明確に定義し、実際の支出と比較してください。Savings Plans／RI、EKS／Auto Mode、ストレージ、ネットワーク、再試行、アイドル容量をどこまで含めたか明記します。「70%割引」や「80／20の構成で少なくとも50%削減」といった固定値は保証されません。

対象を指定した Capacity Reservation を作っても、NodePool が自動的にそれを使うようにはなりません。対応する NodeClass selector、AZ／instance type の一致、料金、未使用容量を確認してください。可用性要件に合った負荷・障害テストで fallback 設計を検証します。

## 参考資料

- [HPA の動作](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [KEDA 2.21 ScaledObject](https://keda.sh/docs/2.21/reference/scaledobject-spec/)
- [KEDA 2.21 ScaledJob](https://keda.sh/docs/2.21/reference/scaledjob-spec/)
- [VPA 1.8.0 の機能](https://github.com/kubernetes/autoscaler/blob/vertical-pod-autoscaler-1.8.0/vertical-pod-autoscaler/docs/features.md)
- [Pod resize](https://kubernetes.io/docs/tasks/configure-pod-container/resize-container-resources/)
- [ReplicaSet の deletion cost](https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/#pod-deletion-cost)
- [章のクイズ](../quizzes/ops/06-scaling-strategies-quiz.md)

< [前へ: GitOps Automation](05-gitops-automation.md) | [目次](README.md) | [次へ: 運用アラート](07-observability-alerts.md) >
