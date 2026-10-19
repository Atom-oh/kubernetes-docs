# Istioメトリクスを使ったKEDAベースのオートスケーリング

> **検証基準**: KEDA/chart 2.20.2、Istio 1.31.0、Kubernetes 1.32–1.37
> **最終確認**: 2026年10月16日

このガイドでは、スケーリングに使うシグナルとその限界を説明します。既存のワークロード、検証済みメトリクス、十分なクラスター容量があることを前提とします。同じDeploymentを対象とする例は**いずれかを選ぶ選択肢**です。このページのオブジェクトをすべて適用するのではなく、対象ごとにScaledObject/HPAの所有者を1つ選んでください。

## 目次

1. [概要](#overview)
2. [アーキテクチャ](#architecture)
3. [Prometheusメトリクスに基づくスケーリング](#prometheus-metrics-based-scaling)
4. [CloudWatchメトリクスに基づくスケーリング](#cloudwatch-metrics-based-scaling)
5. [実践的なスケーリング戦略](#practical-scaling-strategies)
6. [ベストプラクティス](#best-practices)
7. [トラブルシューティング](#troubleshooting)
8. [参考: KEDAのインストール](#reference-keda-installation)

## 概要 {#overview}

Kubernetes HPAは、対応するAPIを通じてリソースメトリクス、カスタムメトリクス、外部メトリクスをサポートし、複数のメトリクスも扱えます。アダプターを使えばCloudWatchも統合できます。HPAでCloudWatchを利用できないわけではありません。KEDAはスケーラー、外部メトリクスAPI、アクティベーション管理を提供し、通常のレプリカ数のスケーリングには引き続きHPAを使います。

| シグナル | 意味 | 用途と制限 |
|---|---|---|
| `istio_requests_total` | HTTP/gRPCリクエストのカウンター | レートで受け入れた負荷を測定できます。reporterを1つにし、実際にスケールするワークロードを指定します |
| `istio_request_duration_milliseconds_bucket` | 従来型レイテンシーヒストグラムのバケット | 分位点は品質を示す観測値であり、容量を逆算できる保証付きシグナルではありません |
| `istio_tcp_connections_opened_total` | 累積接続開始数 | そのレートは接続作成率であり、現在アクティブな接続数ではありません |
| `istio_request_bytes_sum` | 観測されたHTTPリクエストバイト数の累積値 | レートでスループットを測れます。reporterとワークロードの範囲を指定します |
| `envoy_cluster_upstream_rq_pending_overflow` | クライアント側クラスタのオーバーフローカウンター | どのワークロードをスケールするか決める前に、接続プールの上限や依存先を調べます |

校正済みの需要/バックログメトリクスは出発点になります。レイテンシー、エラー、サーキットブレーカーイベントは、レプリカを増やしても解決しない下流障害が原因の場合があります。ステートフルなメンバーシップ、ストレージ、アプリケーションの意味上の制約もスケーリングに影響します。「ステートフル」または「レイテンシー重視」というだけでは、安全なオートスケーリング方針は決まりません。

## アーキテクチャ {#architecture}

KEDAはスケール対象のHPAを作成/設定し、外部メトリクスを公開します。HPAコントローラーはそのAPIからメトリクスを取得し、対象の`/scale`サブリソースを更新します。その後、対象のコントローラーとスケジューラーがPodを作成し、配置します。

| 設定またはコンポーネント | 役割 |
|---|---|
| KEDA `pollingInterval` | トリガーのポーリングとアクティベーションを行う。0→1も含む |
| HPAコントローラーの同期 | 追加のメトリクス要求と1→Nの判断を行う。既定の同期間隔は15秒で、クラスター設定により変更可能 |
| `useCachedMetrics` | ポーリング間のKEDAメトリクスキャッシュを任意で有効にする。この例では無効 |
| `activationThreshold` | 0↔1のアクティベーションしきい値であり、HPAの別のスケールダウンしきい値ではない |
| `cooldownPeriod` | 非アクティブ状態の後にKEDAが0へスケールするまで待つ時間で、各スケールダウン後の一時停止ではない |
| HPA `behavior` | 1→Nの安定化と変化率の上限を設定する |

`minReplicaCount`を0より大きくする場合、アクティベーションやクールダウンを通常のレプリカ数のヒステリシス制御には使わないでください。収集→スクレイプ→クエリ→HPA→Pod起動/Readyまでのすべてが遅延に加わります。15秒ポーリングでも、安定化時間0でも、容量が直ちにReadyになるとは限りません。

### メトリクスの種類と理想的な計算

HPAの許容誤差、欠落/未ReadyのPod、上限、behaviorポリシーを無視すると、次のようになります。

- **AverageValue + 需要の合計値**: 希望レプリカ数 ≈ `ceil(メトリクス合計 / Podあたりの目標値)`。
- **Value + ワークロード全体の値**: 希望レプリカ数 ≈ `ceil(現在のレプリカ数 × 観測値 / 目標値)`。

600 RPSをPodあたり100 RPSとする場合、AverageValueは6レプリカを要求します。クエリを先に3 Podで割ると200が入力され、誤って2レプリカを要求します。`count(up)`はスクレイプ対象数を数えるため、安全なレプリカ数の除数でもありません。

4レプリカで全体レイテンシーが300ms、Value目標が200msなら、6レプリカが示唆されます。レプリカを増やしてもレイテンシーが下がらなければ、判断が繰り返されてワークロードが上限まで達する可能性があります。レイテンシー/エラー率ベースの制御は、本番環境の既定値ではなく、負のフィードバックが働く証拠を必要とする実験として扱ってください。

## Prometheusメトリクスに基づくスケーリング {#prometheus-metrics-based-scaling}

以下の例では、`default`名前空間に実際のDeployment `reviews`があることを前提とします。Service名はスケール対象ではありません。リリースされたBookinfoでは通常`reviews-v1`などのDeployment名が使われます。Service名がDeployment名と一致すると仮定せず、実際のワークロードに合わせて`scaleTargetRef`とメトリクスセレクターを両方調整してください。

各対象プロキシから少なくとも1回スクレイプし、実際のラベルを確認してください。主な例では両方のリクエスト報告を重複計上しないよう`reporter="destination"`を使います。これは対象で受け付けたリクエストを測ります。エッジでの拒否/キューを含めるには、独立して計測した需要シグナルが必要な場合があります。

### 1. RPSに基づくスケーリング

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-rps-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

クエリは失敗リクエストも負荷として含み、RPS合計を返します。`threshold: "100"`はAverageValueのレプリカあたりの目標値であり、「全体が100を超えたらPodを1つ追加する」というスイッチではありません。さらにPod数で割らないでください。

KEDA 2.20.2では、`ignoreNullValues: "false"`により、Prometheusの値がない場合、NaNまたは無限大の場合はエラーになります。実際にレートが0のカウンターは引き続き0です。データソース障害時のfallbackを設定してテストし、任意の欠損メトリクスを黙って0に変換しないでください。スケーラーを有効化する前に、スクレイプとメトリクスのデータ契約を整えてください。

ここでのfallbackは、設定したエラーしきい値に達すると、設定済みのフロアと現在のレプリカ数のうち大きい方を使います。それでもHPAの上限とbehaviorの対象です。停止したKEDAメトリクスAPIやノード容量不足を防ぐものではありません。

### 2. レイテンシーに基づく制御: 条件付き実験

この選択肢では、ワークロード全体のp95に対してValueを明示的に使います。

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-latency-experiment
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: p95
    metricType: Value
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: |-
        (histogram_quantile(0.95, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])))
          and on() (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
        or on() (0 * (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
      threshold: '200'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

クエリは実際のヒストグラム件数のレートが0の場合に限って0を返します。テレメトリがない場合は欠損のままです。無効な分位点は正常な0ではなく、引き続きエラーになります。アイドル時間帯のp95=0は意図した制御値であり、リクエスト時間が0だったという観測ではありません。

複数の分位点もValueメトリクスです。

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-quantile-experiment
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: p50
    metricType: Value
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: |-
        (histogram_quantile(0.5, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])))
          and on() (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
        or on() (0 * (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
      threshold: '50'
      ignoreNullValues: 'false'
  - type: prometheus
    name: p95
    metricType: Value
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: |-
        (histogram_quantile(0.95, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])))
          and on() (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
        or on() (0 * (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
      threshold: '200'
      ignoreNullValues: 'false'
  - type: prometheus
    name: p99
    metricType: Value
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: |-
        (histogram_quantile(0.99, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])))
          and on() (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
        or on() (0 * (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
      threshold: '500'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

HPAは平均や重み付き合計ではなく、最も大きな希望レプリカ数を選びます。分位点同士は相関しています。トリガーを増やしても、それ自体で安定性が向上したりレイテンシーが保証されたりはしません。

### 3. エラー率に基づく制御: 条件付き実験

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-error-experiment
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: error-percent
    metricType: Value
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: |-
        (100 * (sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default",response_code=~"5..|0"}[2m])) or vector(0)) / sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))
          and on() (sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
        or on() (0 * (sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
      threshold: '5'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

これはワークロード全体の5xx/ゼロステータス割合をValue目標で扱います。既知のアイドル状態なら0を返しますが、テレメトリがない場合に0を捏造しません。レプリカ不足がエラーの原因だと確認してから、エラーベースの制御を使ってください。依存先の停止、認可失敗、クライアント側の接続プール上限が原因なら、スケーリングは効果がないか、かえって有害な場合があります。

### 4. 複合メトリクス

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-composite-experiment
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  - type: prometheus
    name: p95
    metricType: Value
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: |-
        (histogram_quantile(0.95, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])))
          and on() (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
        or on() (0 * (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
      threshold: '200'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

RPS入力はAverageValueを使った需要の合計、レイテンシー入力はValueです。HPAは最大の推奨レプリカ数を選びます。スケールアップの`selectPolicy: Max`は許可された変更のうち大きい方を選びます。5 Podのポリシーは、パーセント指定ポリシーがそれ以上を許可する場合には絶対上限になりません。これらの選択肢も容量とワークロードのテストが必要です。

## CloudWatchメトリクスに基づくスケーリング {#cloudwatch-metrics-based-scaling}

CloudWatchの情報鮮度は、ソースの送信間隔、公開遅延、集計期間、参照期間、オフセットで決まります。高解像度のカスタムメトリクスも利用できます。「CloudWatchは常に1〜3分遅れる」という固定的な説明は正確ではありません。Prometheusにも収集と制御ループの遅延があります。

### IDと公開メトリクスの契約

以下ではIRSA経由で設定したKEDA Operatorロールと、ワークロード名前空間にあるこのTriggerAuthenticationを使います。

```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: keda-aws
  namespace: default
spec:
  podIdentity:
    provider: aws
    identityOwner: keda
```

`podIdentity.provider: aws`は現在のIRSAプロバイダーです。その`identityOwner: keda`は、非推奨のスケーラーメタデータ`identityOwner: operator/pod`とは異なります。後者は2.20でも引き続きサポートされますが、3で削除予定です。旧`aws-eks`プロバイダー名を新しいEKS Pod Identityの関連付けと混同しないでください。選択したID方式に対応する文書化済みのプロバイダー/SDK認証情報設定を使ってください。

このガイド後半の公開例では、次を出力します。

| メトリクス | 名前空間と正確なディメンション | 解釈 |
|---|---|---|
| `IstioRequestsPerSecond` | `IstioScaling`; ClusterName=`eks-demo`、destination_workload=`reviews`、destination_workload_namespace=`default` | あらかじめ計算されたRPSゲージ |
| `IstioP95LatencyMilliseconds` | 同じディメンション一式 | 集計期間ごとに計算したp95ゲージ (ミリ秒) |

すべてのディメンションを一致させる必要があります。destination_workloadだけを含むクエリでは、同じカスタムメトリクスを特定できません。

### RPSゲージ

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-cloudwatch-rps
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 60
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: aws-cloudwatch
    name: cw-rps
    metricType: AverageValue
    authenticationRef:
      name: keda-aws
    metadata:
      namespace: IstioScaling
      metricName: IstioRequestsPerSecond
      dimensionName: ClusterName;destination_workload;destination_workload_namespace
      dimensionValue: eks-demo;reviews;default
      targetMetricValue: '100'
      minMetricValue: '0'
      ignoreNullValues: 'false'
      metricStatPeriod: '60'
      metricStat: Average
      metricCollectionTime: '300'
      metricEndTimeOffset: '60'
      awsRegion: us-west-2
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

ゲージの60秒期間で平均してもRPS単位は維持されます。累積値の`istio_requests_total`サンプルを合計しても、1分あたりのリクエスト数にはなりません。実際に公開された差分カウントメトリクスを使う場合は、期間ごとの目標値を別途校正してください。

リリース済みスケーラーパーサーでは`minMetricValue`が明示的に存在しますが、結果が空の場合は`ignoreNullValues: "false"`が優先されます。`metricEndTimeOffset`は未完了の可能性がある直近のデータ点を飛ばします。遅延を加える設定であり、データの鮮度を証明するものではありません。値が空でないまま古くなる場合も含め、タイムスタンプと公開元の健全性を監視してください。

### 事前計算したレイテンシーゲージ

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-cloudwatch-p95-experiment
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 60
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: aws-cloudwatch
    name: cw-p95
    metricType: Value
    authenticationRef:
      name: keda-aws
    metadata:
      namespace: IstioScaling
      metricName: IstioP95LatencyMilliseconds
      dimensionName: ClusterName;destination_workload;destination_workload_namespace
      dimensionValue: eks-demo;reviews;default
      targetMetricValue: '200'
      minMetricValue: '0'
      ignoreNullValues: 'false'
      metricStatPeriod: '60'
      metricStat: Maximum
      metricCollectionTime: '300'
      metricEndTimeOffset: '60'
      awsRegion: us-west-2
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

この設定は期間中に公開されたp95ゲージの最大値を要求します。**CloudWatchの期間全体に含まれる全リクエストのp95ではありません**。Prometheusヒストグラムからの変換やp95ゲージに対して`metricStat: p95`を要求し、元の分布が保たれると説明しないでください。CloudWatch本来のパーセンタイルを使うには、適切に公開されたサンプル/統計値が必要です。

### 複数のソースは優先順位付きフェイルオーバーではない

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-dual-source-example
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: prom-rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  - type: aws-cloudwatch
    name: cw-rps
    metricType: AverageValue
    authenticationRef:
      name: keda-aws
    metadata:
      namespace: IstioScaling
      metricName: IstioRequestsPerSecond
      dimensionName: ClusterName;destination_workload;destination_workload_namespace
      dimensionValue: eks-demo;reviews;default
      targetMetricValue: '100'
      minMetricValue: '0'
      ignoreNullValues: 'false'
      metricStatPeriod: '60'
      metricStat: Average
      metricCollectionTime: '300'
      metricEndTimeOffset: '60'
      awsRegion: us-west-2
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

両方のメトリクスがHPAの最大推奨値に参加します。「Prometheusがプライマリ、CloudWatchがセカンダリ」という設定は、優先順位/フェイルオーバーポリシーではありません。古い値が高いレプリカ数を維持する場合もあります。単一ソースを意図的に選ぶか、複数ソース/fallbackをテストした設計にしてください。

## 実践的なスケーリング戦略 {#practical-scaling-strategies}

### 1. スケジュールによるレプリカ数の下限

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: frontend-scheduled-floor
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 50
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="frontend",destination_workload_namespace="default"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: 0 9 * * 1-5
      end: 0 18 * * 1-5
      desiredReplicas: '20'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

平日のAsia/Seoul時間帯にはCronトリガーが20レプリカを下限として提供し、需要に応じて設定済み上限まで増やせます。これはスケジュールによるスケーリングであり、トラフィック予測モデルではありません。起動/Readyに時間がかかる場合は、需要発生より前にスケジュールしてください。

### 2. 営業時間外に明示的に0へスケール

営業時間外に利用できなくてもよいワークロードでは、時間内に正の希望数を設定し、`minReplicaCount: 0`を使います。

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: analytics-office-hours
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: analytics-service
  pollingInterval: 30
  cooldownPeriod: 600
  minReplicaCount: 0
  maxReplicaCount: 30
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: 0 9 * * 1-5
      end: 0 18 * * 1-5
      desiredReplicas: '20'
```

Cronの`desiredReplicas: "0"`は無効です。アクティブ時間帯の外では、KEDAは非アクティブ/クールダウン規則に基づき0へ戻せます。クライアントのリクエストでCron専用ワークロードが起動することはありません。アプリケーションがない状態では宛先側Istioメトリクスが消えるため、それだけで信頼できる0→1需要シグナルを提供できません。独立して観測できるキュー/インターセプターを使うか、要求時の可用性が必要なら正の最小数を維持してください。

PromQLの`hour()`はUTCを使います。CronスケーラーのAsia/Seoulタイムゾーンを引き継ぎません。業務時間帯が同じだと仮定して混用しないでください。

### 3. サーキットブレーカーのシグナルはまず診断に使う

クライアント側オーバーフローと現在の接続数は個別に調べられます。

```promql
sum(increase(envoy_cluster_upstream_rq_pending_overflow{
  cluster_name=~"outbound[|]9080[|][^|]*[|]backend[.]default[.]svc[.]cluster[.]local"
}[1m]))

sum(envoy_cluster_upstream_cx_active{
  cluster_name=~"outbound[|]9080[|][^|]*[|]backend[.]default[.]svc[.]cluster[.]local"
})

max(envoy_cluster_circuit_breakers_default_cx_open{
  cluster_name=~"outbound[|]9080[|][^|]*[|]backend[.]default[.]svc[.]cluster[.]local"
})
```

実際のクラスター名/ポート、エクスポートされた統計、ソーススクレイプ範囲を確認してください。`cx_open`は0/1のサーキットブレーカーフラグで、接続容量ではありません。アクティブ接続数をこれで割っても飽和率にはなりません。バックエンドのレプリカを増やしても、クライアントの固定接続プール上限は増えません。スケーリング対象を決める前に、制限/依存先を診断してください。

### 4. スケーリングポリシーは負荷階層ではない

Percent/Podsと`selectPolicy: Max`または`Min`を含むHPAポリシー一覧は、ローリング期間中に許可する変更を制限します。コメントにある「低」「中」「高」の負荷階層を自動選択する機能ではありません。主なbehavior例を使って変更幅を制限し、測定したワークロードの応答で検証してください。

### 5. Gatewayが観測するバックエンド需要

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: backend-gateway-rps
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: gateway-backend-rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="source",source_workload="istio-ingressgateway",source_workload_namespace="istio-system",destination_service_name="backend",destination_service_namespace="default"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

実際のGatewayワークロード名と宛先Serviceのラベルを確認してください。これは、そのGatewayから特定のバックエンドへ向かったトラフィックを測ります。`envoy_http_downstream_rq_active`はアクティブなHTTPリクエスト数であり、保留中の接続数ではありません。また、Gateway全体の集計には関係のないServiceも含まれます。その集計を任意のバックエンドのスケーリングに使わないでください。

この例は正の最小数を維持します。0レプリカを検討する場合は、バックエンドエンドポイントがない状態でも独立したGateway/インターセプターが必要なメトリクスを出し、望ましいリクエストバッファリング/エラー処理を提供できることを先に確認してください。

## ベストプラクティス {#best-practices}

### 1. 対象ごとにオートスケーラーの所有者を1つにする

同じ対象に複数のScaledObject例や追加の「バックアップHPA」をインストールしないでください。変更前に、既存HPAの所有権とGitOpsのreplicasフィールドを調整します。1つのScaledObjectで複数メトリクスを扱えます。メトリクスエラー時、ネイティブHPAは有効なスケールアップ推奨を許しながらスケールダウンを見送る場合があります。

KEDA 2.20のfallbackはCPU/メモリを除き、AverageValueとValueのトリガーをサポートします。対象はScaledObjectでありScaledJobではありません。CPU/メモリのトリガーにはmetrics-serverとリソースrequestの前提条件が別途必要で、独立したフェイルオーバーコントローラーではありません。

### 2. ベンチマークではなく容量計画の例

次の数値は**仮定した入力値**としてそのまま示します。

| 仮定/計算 | 結果 |
|---|---|
| Podあたりの実測容量を200 RPSと仮定し、選択した使用率係数70%を乗算 | Podあたり目標140 RPS |
| 通常負荷500 / 140を切り上げ | 4レプリカ |
| ピーク負荷2000 / 140を切り上げ | 15レプリカ |
| 余裕を加えて選んだ最大数 | 20。ただし実際にスケジュール可能な容量が上限 |

これらは今回の監査で測定した値ではありません。対象のレプリカ数/目標を固定した承認済み負荷試験を実施し、レイテンシー、エラー、リソース、Ready状態を記録してください。複数レプリカに負荷分散するServiceでは、1 Podの容量を直接測れません。

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-capacity-example
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 4
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))
      threshold: '140'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 4
    behavior: currentReplicasIfHigher
```

「`maxReplicaCount`をクラスター容量の70%以下にする」という普遍的なルールはありません。Pod数はCPU/メモリ/IP/クォータの割合ではありません。HPA/KEDAはワークロードをスケールし、ノード容量は別のプロビジョニング/オートスケーラー設定で確保します。

### 3. リソースと健全性

実際のコンテナ名と健全性エンドポイントを確認したうえで、この断片を**既存の**Deployment/コンテナにマージしてください。実際のイメージ、セレクター、ラベルは維持します。

```yaml
spec:
  template:
    spec:
      containers:
      - name: reviews
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
        readinessProbe:
          httpGet:
            path: /health
            port: 9080
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
```

requests/limitsとプローブは調整用の入力であり、スループットを保証する測定値ではありません。Readinessと起動/終了処理は、容量を利用できるようになる時点に影響します。下流依存先が使えないだけで、健全なプロセスをlivenessで再起動しないでください。

### 4. 複数クラスターとリージョン

各対象クラスターに、検証済みのクラスター内データソースを使うスケーラーを配置するか、フェデレーションストアに実在する明示的なクラスターラベルを指定します。クラスター内の宛先reporterデータを使うと、この例ではローカルのバックエンド需要全体を数えます。

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: frontend-local-demand
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 3
  maxReplicaCount: 30
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: local-rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="frontend",destination_workload_namespace="default"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

各設定を意図したクラスターコンテキストで適用してください。`region`などのメタデータラベルを付けても、ScaledObjectがリモートクラスターを制御するわけではありません。`source_cluster`は送信元を示すもので、スケールすべき宛先容量ではありません。すでに絞り込んだトラフィックに0.6/0.4を掛けても、グローバルなトラフィック分割にはなりません。

`*-us-*`などのService命名パターンからクライアントの地理的位置は分かりません。また、`destination_region`がIstioの既定ラベルである保証もありません。リージョン別SLOには、サービス名に国名があるという思い込みではなく、検証済みテレメトリとワークロード容量が必要です。

### 5. 決済とキューワークロード

決済ワークロードでは、レイテンシー/エラーを品質指標として扱いながら、校正済み需要と保守的な上限から始められます。

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: payment-capacity-example
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: payment-service
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 5
  maxReplicaCount: 50
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 600
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="payment-service",destination_workload_namespace="production"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 5
    behavior: currentReplicasIfHigher
```

100 RPSの目標と上限は説明用です。比率ベースのトリガーを追加する前に、ボトルネックの因果関係、冪等性、下流の上限、代表的な障害時の動作を確認してください。

キューワーカーでは、ワーカーのレプリカ数が0でもキューは観測可能なままです。

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: data-processor-queue
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: data-processor
  pollingInterval: 30
  cooldownPeriod: 600
  minReplicaCount: 0
  maxReplicaCount: 30
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: aws-sqs-queue
    name: backlog
    metricType: AverageValue
    authenticationRef:
      name: keda-aws
    metadata:
      queueURL: https://sqs.us-west-2.amazonaws.com/123456789012/data-processing-queue
      queueLength: '10'
      activationQueueLength: '0'
      scaleOnInFlight: 'true'
      scaleOnDelayed: 'false'
      awsRegion: us-west-2
```

例のアカウント/キューURLを置き換え、参照されるIDを設定してください。`queueLength: "10"`はレプリカあたりの目標バックログであり、10件でアクティベーションするしきい値ではありません。アクティベーションは、明示的なアクティベーションしきい値0に対する正のバックログを既定で使います。この例は可視メッセージと処理中メッセージを数え、遅延メッセージを除外します。処理並列度、可視性タイムアウト、シャットダウン動作に合わせてください。

Istio HTTPレイテンシーは、SQSジョブ処理時間と自動的に一致するものではありません。0レプリカのワーカーに取得できないPodレイテンシートリガーを追加するのではなく、業務処理を別途計測してください。

### 6. 監視

スケーラーの健全性を監視するには**Operator**メトリクスを公開してスクレイプしてください。メトリクスアダプターだけでは、Operatorのすべてのカウンターを取得できません。KEDAの`namespace`メトリクスラベルはスケール対象リソースの名前空間を示します。これをExporter Podの名前空間で上書きしないでください。

これは、EndpointSlice、Service、Podの名前空間スコープのdiscovery RBACとともに、既存Prometheus設定へマージするスクレイプ設定断片です。

```yaml
scrape_configs:
- job_name: keda-components
  kubernetes_sd_configs:
  - role: endpointslice
    namespaces:
      names:
      - keda
  relabel_configs:
  - source_labels:
    - __meta_kubernetes_service_name
    regex: keda-operator|keda-operator-metrics-apiserver
    action: keep
  - source_labels:
    - __meta_kubernetes_endpointslice_port_name
    regex: metrics
    action: keep
  - source_labels:
    - __meta_kubernetes_namespace
    target_label: exporter_namespace
  - source_labels:
    - __meta_kubernetes_pod_name
    target_label: exporter_pod
```

負荷分散Serviceを通じてHA Operator Podを交互に参照するのではなく、各エンドポイントを検出します。実際のService/ポート名、ターゲットラベル、TLS/メッシュアクセス、スクレイプ結果を確認してください。Prometheus Operatorを使う場合は、生成済みConfigMapを上書きせず、適切に選択したServiceMonitorを使います。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: keda-scaling-alerts
  namespace: keda
spec:
  groups:
  - name: keda-scaling
    rules:
    - alert: KEDAMaxReplicasReached
      expr: |-
        max by (namespace, horizontalpodautoscaler) (
         kube_horizontalpodautoscaler_status_current_replicas{horizontalpodautoscaler=~"keda-hpa-.*"}
        ) >= on(namespace, horizontalpodautoscaler)
        max by (namespace, horizontalpodautoscaler) (
         kube_horizontalpodautoscaler_spec_max_replicas{horizontalpodautoscaler=~"keda-hpa-.*"}
        )
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: KEDA-managed HPA is at its configured maximum
    - alert: KEDAScalerErrors
      expr: sum by (namespace, scaledObject) (increase(keda_scaler_detail_errors_total[5m])) > 0
      for: 2m
      labels:
        severity: warning
      annotations:
        summary: Scaler retrieval errors observed; inspect source/identity and fallback
    - alert: KEDAReplicaCountChurn
      expr: |-
        max by (namespace, horizontalpodautoscaler) (
         changes(kube_horizontalpodautoscaler_status_current_replicas{horizontalpodautoscaler=~"keda-hpa-.*"}[10m])
        ) > 6
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Frequent observed replica-count changes; inspect demand, rollout and stabilization
```

PrometheusRuleには一致するOperatorのルールセレクター/名前空間が必要です。HPAフィルターはKEDAの既定の名前プレフィックスを使います。カスタムHPA名に合わせてください。`keda_scaler_detail_errors_total`はリリース版のエラーカウンターです。`keda_scaler_active`はゲージなので、レプリカ変動の指標として`rate()`に渡してはいけません。

レプリカ数の変化は需要やロールアウトを反映する場合があり、必ずしも有害な振動とは限りません。これらのアラートは調査の手掛かりであり、スケーリング失敗やReady容量の十分さを証明するものではありません。

## トラブルシューティング {#troubleshooting}

```bash
kubectl get scaledobject reviews-rps-scaler -n default -o yaml
kubectl describe hpa keda-hpa-reviews-rps-scaler -n default
kubectl logs -n keda deployment/keda-operator
kubectl get apiservice v1beta1.external.metrics.k8s.io
kubectl get pods -n default -o wide

# Local query inspection; use a second terminal while port-forward is active.
kubectl port-forward -n istio-system svc/prometheus 9090:9090
```

```bash
promtool query instant http://127.0.0.1:9090 'sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))'
```

ローカルのポートフォワードだけでは、KEDA Podの接続性や認証情報は証明できません。実際のコンポーネント経路から、プロバイダーエラー、DNS、TLS/メッシュポリシー、メトリクスの存在/ラベル、集約APIの可用性を確認してください。

スケーリングが遅い場合、`pollingInterval`を短縮する前に、ソースデータの古さ、参照期間、HPA同期/behavior、スケジューリング、イメージ取得、Readinessを確認してください。正の最小数を使う場合、アクティベーションしきい値は通常の1→Nスケーリングを速めません。レプリカ数が不安定なら、測定した容量応答とHPAの安定化/変化率上限を調べてください。`cooldownPeriod`は一般的なスケールダウン制御ではありません。

CloudWatchでは、返されたタイムスタンプ、すべてのディメンション、統計値/単位、収集期間、オフセット、IAMを確認してください。2つ目のメトリクスのしきい値を高くしても、受動的なバックアップにはなりません。

## 参考: KEDAのインストール {#reference-keda-installation}

### 固定するChartと実際の互換性

公開されているKEDA 2.20のデプロイ要件はKubernetes 1.30+ですが、Chartメタデータの下限はより古い1.23です。Helmがあるバージョンを受け入れても、実行時サポートの証明にはなりません。Istio 1.31のサポート範囲1.32–1.37とマネージドプラットフォームのサポートバージョンとの共通範囲を使ってください。

新規インストール、または既存値を維持するレビュー済みアップグレードには次のvaluesを使います。アップグレード前に、リリース変更とCRDの所有権/移行手順も確認してください。

```yaml
operator:
  replicaCount: 2
prometheus:
  operator:
    enabled: true
  metricServer:
    enabled: true
    port: 9022
```

```bash
helm repo add kedacore https://kedacore.github.io/charts
helm repo update kedacore
helm upgrade --install keda kedacore/keda --version 2.20.2   --namespace keda --create-namespace --values keda-values.yaml
kubectl get deployments,services,pods -n keda
```

`operator.replicaCount: 2`とmetrics-adapterポート9022の上書きは有効なChart値です。9022はChart既定の8080を明示的に変更します。これによりOperatorメトリクスも8080で有効になります。Operatorレプリカが2つだけでは、metrics adapter/Webhookやスケーリング経路全体の高可用性は保証されません。

Istioがコンポーネントへサイドカーを注入する場合、KEDAは自らのTLS保護された内部プロトコル用に、次の任意のポート除外回避策を文書化しています。

```yaml
podAnnotations:
  keda:
    traffic.sidecar.istio.io/excludeInboundPorts: '9666'
    traffic.sidecar.istio.io/excludeOutboundPorts: 9443,6443
  metricsAdapter:
    traffic.sidecar.istio.io/excludeInboundPorts: '6443'
    traffic.sidecar.istio.io/excludeOutboundPorts: 9666,9443
  webhooks:
    traffic.sidecar.istio.io/excludeInboundPorts: '9443'
    traffic.sidecar.istio.io/excludeOutboundPorts: 9666,6443
```

適用前に実際のポートとサイドカー注入設定を確認してください。KEDAはネイティブTLSを維持します。Istioの認可は除外したトラフィックを対象としません。これはトランスポートセキュリティ全体を無効化する許可ではありません。APIサーバー集約、アドミッション、Operator↔adapter、Prometheus接続をテストしてください。

### AWS読み取り用ID

IAMロールとEKS OIDC信頼をこの例の外で作成/レビューし、実際のOperator ServiceAccountに範囲を限定してください。既存のServiceAccountを盲目的に上書きせず、対応するHelm valuesを適用します。

```yaml
podIdentity:
  aws:
    irsa:
      enabled: true
      roleArn: arn:aws:iam::123456789012:role/KedaMetricsReader
```

示したCloudWatchスケーラーのリリース実装はGetMetricDataを呼び出します。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:GetMetricData"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "us-west-2"
        }
      }
    }
  ]
}
```

これはリージョン内のメトリクス読み取り権限であり、メトリクス名前空間単位の境界ではありません。AWS例のポリシーにある`cloudwatch:namespace`は、GetMetricDataの照会ではなく**PutMetricDataによる公開**を制限します。CloudWatch PromQL APIには別のIAM要件があります。このスケーラーの設定から推測しないでください。

SQS例を使う場合、Operatorにはさらに対象キューの属性読み取り権限が必要です。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sqs:GetQueueAttributes"
      ],
      "Resource": "arn:aws:sqs:us-west-2:123456789012:data-processing-queue"
    }
  ]
}
```

キューワーカーには、用途に応じて独自の受信/削除/可視性権限が必要です。スケーラーの読み取りロールはそれらを付与しません。Operator IDを使って、ScaledObjectやTriggerAuthenticationを作成/変更できる主体を制限してください。

### CloudWatch EMFの任意公開

この例では**Operator 0.158.0と組み合わせた上流Collector Contrib 0.158.0**を使います。これはOperatorのマイナーバージョン推奨に一致します。Operator 0.158はKubernetes 1.25–1.36をサポートします。Operatorはカスタムイメージを自動的に更新しません。ADOTディストリビューションも選択肢ですが、そのコンポーネント/設定を確認してから使ってください。以下のコマンドは、仕様が不明なADOTイメージでテスト済みとは主張していません。

まず、このrecording-ruleファイルを既存Prometheus (または適切な選択ラベルを持つ同等のPrometheusRule) に読み込みます。

```yaml
groups:
- name: istio-scaling-export
  interval: 30s
  rules:
  - record: istio_scaling_requests_per_second
    expr: sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))
    labels:
      destination_workload: reviews
      destination_workload_namespace: default
  - record: istio_scaling_p95_milliseconds
    expr: |-
      (histogram_quantile(0.95, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])))
        and on() (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
      or on() (0 * (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
    labels:
      destination_workload: reviews
      destination_workload_namespace: default
```

示したワークロードだけをエクスポートします。これらはすでに計算済みのRPSとローリング期間p95のゲージであり、生の累積リクエストカウンターでも、再構成可能なリクエストレイテンシー分布でもありません。

次に、互換性のあるOperator/CRDと、既存のレビュー済み公開ロール/ロググループを使います。

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: istio-metrics-publisher
  namespace: istio-system
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/IstioMetricsPublisher
---
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: istio-scaling
  namespace: istio-system
spec:
  mode: deployment
  replicas: 1
  serviceAccount: istio-metrics-publisher
  image: otel/opentelemetry-collector-contrib:0.158.0
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      memory: 512Mi
  config:
    extensions:
      health_check:
        endpoint: 0.0.0.0:13133
    receivers:
      prometheus:
        config:
          scrape_configs:
          - job_name: istio-scaling-federate
            scrape_interval: 60s
            honor_labels: true
            metrics_path: /federate
            params:
              match[]:
              - '{__name__=~"istio_scaling_requests_per_second|istio_scaling_p95_milliseconds"}'
            static_configs:
            - targets:
              - prometheus.istio-system.svc.cluster.local:9090
    processors:
      memory_limiter:
        check_interval: 1s
        limit_mib: 256
        spike_limit_mib: 64
      metricstransform:
        transforms:
        - include: istio_scaling_requests_per_second
          action: update
          new_name: IstioRequestsPerSecond
          operations:
          - action: add_label
            new_label: ClusterName
            new_value: eks-demo
        - include: istio_scaling_p95_milliseconds
          action: update
          new_name: IstioP95LatencyMilliseconds
          operations:
          - action: add_label
            new_label: ClusterName
            new_value: eks-demo
      batch:
        timeout: 60s
        send_batch_size: 256
    exporters:
      awsemf:
        namespace: IstioScaling
        region: us-west-2
        log_group_name: /aws/otel/istio-scaling
        log_stream_name: eks-demo
        dimension_rollup_option: NoDimensionRollup
        metric_declarations:
        - dimensions:
          - - ClusterName
            - destination_workload
            - destination_workload_namespace
          metric_name_selectors:
          - ^IstioRequestsPerSecond$
          - ^IstioP95LatencyMilliseconds$
        metric_descriptors:
        - metric_name: IstioRequestsPerSecond
          unit: Count/Second
          overwrite: true
        - metric_name: IstioP95LatencyMilliseconds
          unit: Milliseconds
          overwrite: true
    service:
      extensions:
      - health_check
      pipelines:
        metrics:
          receivers:
          - prometheus
          processors:
          - memory_limiter
          - metricstransform
          - batch
          exporters:
          - awsemf
```

`v1beta1`の設定はオブジェクトです。このOperatorリリースでは旧`v1alpha1` APIも引き続き提供されており、削除済みと説明してはいけません。この例では現在の形式と、必要なコンポーネントを含む明示的なContribイメージを使います。

Collectorは名前を指定した2つのrecordingメトリクスだけをフェデレーションし、ワークロードのディメンションを維持して、設定済みClusterNameを追加し、EMFを固定ログストリームへ書き込みます。名前空間、メトリクス名、単位、3つすべてのディメンションをCloudWatchスケーラーと一致させてください。EMF exporterはNaN/Infを破棄します。recording式は、既知のアイドル状態0とテレメトリ欠損を区別します。

この例ではポーリングの重複を避けるため公開元レプリカを1つにしています。これはHA設計ではありません。実際のPrometheus認証/メッシュアクセス、公開元ID、ログ保持期間、リソース上限を設定してください。今回の監査では、Operator/コントローラーもEMF配信もAWSへデプロイ/テストしていません。

公開元のロググループは、プラットフォーム管理の保持設定で事前に作成してください。例のロールには、そのグループ内でストリーム作成/書き込みの権限が必要です。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/otel/istio-scaling:log-stream:eks-demo"
    }
  ]
}
```

EMFはCloudWatch Logs経由で送信されます。`cloudwatch:PutMetricData`だけでは、このExporterは認可されません。設定したメトリクス名前空間は、これらのLogs API呼び出しに対するPutMetricData名前空間条件では強制されません。ログ取り込み/保存と生成されるカスタムメトリクスでは費用が別です。レプリカ削減がそのまま請求額削減になると仮定せず、カーディナリティと保持期間を制御してください。

## 参考資料

- [KEDA ScaledObject仕様](https://keda.sh/docs/2.20/reference/scaledobject-spec/)
- [アクティベーションとスケーリング](https://keda.sh/docs/2.20/concepts/scaling-deployments/)
- [Prometheusスケーラー](https://keda.sh/docs/2.20/scalers/prometheus/)
- [CloudWatchスケーラー](https://keda.sh/docs/2.20/scalers/aws-cloudwatch/)
- [SQSスケーラー](https://keda.sh/docs/2.20/scalers/aws-sqs/)
- [Cronスケーラー](https://keda.sh/docs/2.20/scalers/cron/)
- [AWS IRSAプロバイダー](https://keda.sh/docs/2.20/authentication-providers/aws/)
- [KEDAメトリクス](https://keda.sh/docs/2.20/integrations/prometheus/)
- [KEDAとIstio](https://keda.sh/docs/2.20/integrations/istio-integration/)
- [KEDAデプロイ要件](https://keda.sh/docs/2.20/deploy/)
- [Kubernetes HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Istio標準メトリクス](https://istio.io/latest/docs/reference/config/metrics/)
- [Operator 0.158の互換性](https://raw.githubusercontent.com/open-telemetry/opentelemetry-operator/v0.158.0/docs/getting-started/compatibility.md)
- [Collector 0.158 EMF exporter](https://raw.githubusercontent.com/open-telemetry/opentelemetry-collector-contrib/v0.158.0/exporter/awsemfexporter/README.md)
- [CloudWatch EMF](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format.html)
- [CloudWatch名前空間の条件](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/iam-cw-condition-keys-namespace.html)
- [可観測性](../observability/README.md)
- [レジリエンス](../resilience/README.md)
- [トラフィック管理](../traffic-management/README.md)

本番利用前に、シグナルの意味、実際のメトリクスラベル/鮮度、アイドル/欠損データの動作、スケーリングの単一所有者、容量、代表的な障害時の応答と復旧を検証してください。例のしきい値、レプリカ数の下限、時間値は、それらのテストを始めるための入力です。
