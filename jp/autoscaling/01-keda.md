# KEDA（Kubernetes イベント駆動オートスケーリング）

> **例のバージョン**: KEDA / Helm chart 2.21.0。テスト済みの Kubernetes バージョンは下記を参照してください。
> **最終更新日**: 2026年10月16日

## 目次
- [はじめに](#introduction)
- [アーキテクチャ](#architecture)
- [インストールと設定](#installation-and-configuration)
- [Scaler](#scalers)
- [カスタムメトリクスによるスケーリング](#custom-metric-scaling)
- [Twitter メトリクスによるスケーリング](#twitter-metric-scaling)
- [Google Calendar によるスケーリング](#google-calendar-scaling)
- [Istio メトリクスによるスケーリング](#istio-metric-scaling)
- [Cron によるスケーリング](#cron-based-scaling)
- [Amazon EKS との統合](#integration-with-amazon-eks)
- [ベストプラクティス](#best-practices)
- [トラブルシューティング](#troubleshooting)
- [まとめ](#conclusion)

## はじめに {#introduction}

KEDA（Kubernetes Event-driven Autoscaling）は、Kubernetes アプリケーションのイベント駆動型オートスケーリングを可能にするオープンソースプロジェクトです。KEDA は Kubernetes 標準の Horizontal Pod Autoscaler（HPA）を拡張し、CPU やメモリの使用量に限らず、さまざまなイベントソースやメトリクスに基づいてワークロードをスケーリングできるようにします。

### KEDA の主な利点

1. **イベント駆動型スケーリング**: メッセージキュー、データベース、ストリームなど、さまざまなイベントソースに基づいてスケーリングできます。
2. **ゼロまでのスケーリング**: 対応するイベントトリガーで停止中のワークロードを起動できます。ワークロードごとに最小数、アクティベーションしきい値、クールダウンを設定してください。
3. **幅広い Scaler**: 50種類を超える組み込み Scaler とカスタム Scaler を利用できます。
4. **Kubernetes との親和性**: 既存の Kubernetes HPA と統合します。
5. **クラウドに依存しない設計**: 必要な API、ネットワークアクセス、ID 設定を備えた互換性のある Kubernetes 環境で動作します。
6. **標準的なデプロイモデル**: 標準インストールには operator、メトリクス API server、admission webhook が含まれます。

### 既存のスケーリング方式との比較

| 機能 | KEDA | Kubernetes HPA | クラウドプロバイダーの Autoscaler |
|---------|------|----------------|---------------------------|
| メトリクスソース | 組み込みイベント Scaler と外部 Scaler | 適切な adapter を介したリソース、カスタム、外部メトリクス | 製品による |
| ゼロまでのスケーリング | 対応するトリガーと設定で可能 | バージョン / 機能に依存。Kubernetes 1.37 beta では object / external metric によるゼロスケールに対応 | 製品による |
| イベント駆動 | イベントソース統合とアクティベーションに対応 | custom / external metric adapter で実現可能 | 製品による |
| クラウドに依存しない | ✅ | ✅ | ❌ |
| デプロイの複雑さ | operator、metrics server、webhook、認証情報が必要 | 組み込み controller。adapter が必要な場合あり | 製品による |
| カスタムメトリクス | Scaler 統合または HTTP/gRPC producer | 適切な metrics adapter が必要 | 製品による |

## アーキテクチャ {#architecture}

KEDA は Kubernetes operator パターンに基づいています。外部メトリクスソースを監視し、Kubernetes HPA を管理します。

![KEDA operator は ScaledObject のアクティベーションと HPA のライフサイクルを管理し、Scaler の結果を metrics API server に渡し、ScaledJob に対しては Job を直接作成します。HPA は ScaledObject のゼロ以外の replica 数を管理し、admission webhook はリソースを検証します。](../.gitbook/assets/en-autoscaling-01-keda-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-01-keda-0.html)

### 主なコンポーネント

1. **KEDA Operator**: ScaledObject と関連する HPA を調整し、ゼロからのアクティベーション / 停止を処理し、ScaledJob 用の Job を作成します。
2. **KEDA Metrics Server**: 集約 Kubernetes API を通じて外部メトリクスを提供し、operator の metrics service から Scaler の結果を取得します。
3. **ScaledObject**: Deployment、StatefulSet などのスケーリング設定を定義します。
4. **ScaledJob**: Kubernetes Job のスケーリング設定を定義します。
5. **Trigger / Scaler**: イベントソースのメトリクスを取得してアクティベーションを判定します。admission webhook は対応するリソース設定を検証します。

### 動作の仕組み

1. ScaledObject は、同じ namespace にある互換性のあるスケール対象を参照します。KEDA は対象ごとに HPA を1つ管理するため、スケーリングの所有者は1つにしてください。
2. ワークロードがゼロの間も、operator は `pollingInterval` に従ってアクティベーション用のトリガーをポーリングします。
3. replica 数がゼロ以外の場合、HPA は metrics API server と operator を介して外部メトリクスを要求します。HPA の同期設定とメトリクスの cache 設定は、クエリ頻度に影響します。
4. HPA がゼロ以外の replica 数を調整し、KEDA はアクティベーションと設定済みのゼロスケール用クールダウンを処理します。`cooldownPeriod` は、N replica から1 replicaへの HPA scale-down stabilization の代わりにはなりません。
5. ScaledJob は別経路で動きます。KEDA はイベントとスケーリング戦略に基づいて batch Job を作成します。これらの Job に対する HPA は作成しません。

## インストールと設定 {#installation-and-configuration}

以下の例は、それぞれ独立して使う選択肢であり、ひとまとめの manifest ではありません。参照するワークロード、Service、Secret、image を準備し、account、queue、URL、image の placeholder を置き換えてください。同じ対象に複数の ScaledObject / HPA を割り当てないでください。オートスケーリングが replica 数を管理する場合、GitOps と `spec.replicas` の適用所有権を調整します。ここに示す手順は本番環境にデプロイも測定もしていません。

Kubernetes 1.37 では object / external metric を使った HPA のゼロスケールが beta として導入され、`HPAScaleToZero` によってデフォルトで有効になります。CPU / memory のみのメトリクスからゼロ状態を起動することはできません。この変更によって KEDA 2.21 の operator / HPA の役割分担は変わらず、Kubernetes 1.37 との互換性が保証されるわけでもありません。

### 前提条件

- プロバイダーと利用する KEDA release がサポートする Kubernetes version を選んでください。KEDA 2.21 のデプロイ文書にある**テスト済みマトリクスは1.34～1.36**です。このマトリクスは1.37との互換性を示すものではありません。組み合わせを別途検証してください。
- KEDA 2.20 からアップグレードする場合は、先に[2.21 移行ガイド](https://keda.sh/docs/2.21/migration/#upgrading-from-keda-220-to-221)を確認してください。CVE-2026-77524 の修正として、2.21 では Vault Kubernetes 認証と `boundServiceAccountToken` に対する service account token audience 検証がデフォルトで強制されます（`operator.serviceAccountTokens.mode: enforce-audience`）。また、Temporal Scaler の非推奨設定が削除され、Azure Pipelines の `scaleOnInFlight` のデフォルトが変更されました。この章の例では、これらの認証方式や Scaler は使いません。
- kubectl を設定しておきます。
- Helm（任意）

### インストール方法

#### 1. Helm を使ったインストール

```bash
helm repo add kedacore https://kedacore.github.io/charts
helm repo update
helm install keda kedacore/keda --version 2.21.0 --namespace keda --create-namespace
```

#### 2. YAML manifest を使ったインストール

```bash
kubectl apply --server-side -f https://github.com/kedacore/keda/releases/download/v2.21.0/keda-2.21.0.yaml
```

#### 3. インストールの確認

```bash
kubectl get deployments,pods -n keda
kubectl wait --for=condition=Available deployment --all -n keda --timeout=180s
kubectl get apiservice v1beta1.external.metrics.k8s.io
```

以下は参考出力です（名前や件数は chart の設定により異なり、実行結果を記録したものではありません）。
```
NAME                                      READY   STATUS    RESTARTS   AGE
keda-operator-<hash>-<id>                  1/1     Running   0          1m
keda-operator-metrics-apiserver-<hash>-<id> 1/1     Running   0          1m
keda-admission-webhooks-<hash>-<id>        1/1     Running   0          1m
```

### 基本設定

後述する IRSA の値は、固定した Helm values に統合してから同じ chart の upgrade に適用してください。ServiceAccount annotation の反映を確認し、ID を変更したときは通常の rollout 手順で operator Pod を再起動します。

以下の値は Helm chart 2.21.0 に対応します。operator を2 replicaにしても leader-election の待機系が増えるだけで、reconcile を同時に行う active replica が2つになるわけではありません。metrics-server の冗長性も API aggregation routing に左右され、end-to-end の完全な高可用性を意味しません。resource 値は出発点であり、測定によって決めた sizing ではありません。

#### Helm values ファイルによるカスタム設定

```yaml
operator:
  replicaCount: 2
metricsServer:
  replicaCount: 1
resources:
  operator:
    limits:
      cpu: '1'
      memory: 1000Mi
    requests:
      cpu: 100m
      memory: 100Mi
  metricServer:
    limits:
      cpu: '1'
      memory: 1000Mi
    requests:
      cpu: 100m
      memory: 100Mi
  webhooks:
    limits:
      cpu: '1'
      memory: 1000Mi
    requests:
      cpu: 100m
      memory: 100Mi
logging:
  operator:
    level: info
  metricServer:
    level: 0
```

```bash
helm upgrade --install keda kedacore/keda --version 2.21.0 --namespace keda --create-namespace -f values.yaml
```

## Scaler {#scalers}

KEDA はさまざまなイベントソース向けの Scaler を提供します。各 Scaler は特定のイベントソースからメトリクスを取得し、それに基づいてワークロードをスケーリングします。

### 主な Scaler

KEDA は50種類以上の Scaler に対応しています。主なものを以下に示します。

1. **メッセージキュー**:
   - Apache Kafka
   - RabbitMQ
   - AWS SQS
   - Azure Service Bus
   - Google Cloud Pub/Sub

2. **データベース**:
   - MySQL
   - PostgreSQL
   - MongoDB
   - Redis

3. **ストリーミングプラットフォーム**:
   - Apache Kafka
   - AWS Kinesis
   - Azure Event Hubs

4. **クラウドサービス**:
   - AWS CloudWatch
   - Azure Monitor
   - Google Cloud Monitoring

5. **その他**:
   - Prometheus
   - InfluxDB
   - Cron
   - CPU / Memory

### ScaledObject の基本例

対象 namespace に `rabbitmq-credentials` Secret を作成し、`host` key に認証済みの完全な AMQP / AMQPS 接続 URI を設定してください。参照先の `rabbitmq-consumer` Deployment は、すでにその queue を消費するよう構成しておく必要があります。隔離されていないネットワークでは、信頼性を検証した TLS を推奨します。この例は broker をデプロイせず、認証情報も生成しません。

```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: rabbitmq-auth
  namespace: default
spec:
  secretTargetRef:
  - parameter: host
    name: rabbitmq-credentials
    key: host
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: rabbitmq-scaledobject
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: rabbitmq-consumer
  pollingInterval: 15
  cooldownPeriod: 30
  minReplicaCount: 0
  maxReplicaCount: 30
  triggers:
  - type: rabbitmq
    metadata:
      protocol: amqp
      queueName: hello
      mode: QueueLength
      value: '5'
    authenticationRef:
      name: rabbitmq-auth
```

### ScaledJob の基本例

上記の `rabbitmq-auth` と `rabbitmq-credentials` を再利用します。worker image には、制限された単位の処理を受け取り、acknowledge して終了する process を用意してください。そうしなければ Job は完了しません。retry によって処理が繰り返される可能性があるため、アプリケーション側の冪等性と適切な acknowledgment / visibility timeout を設定します。`jobTargetRef` は JobSpec であり、Job や PodTemplate をさらに入れ子にする場所ではありません。

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledJob
metadata:
  name: rabbitmq-scaledjob
  namespace: default
spec:
  jobTargetRef:
    template:
      spec:
        containers:
        - name: rabbitmq-worker
          image: rabbitmq-worker:latest
          imagePullPolicy: Always
          env:
          - name: RABBITMQ_HOST
            valueFrom:
              secretKeyRef:
                name: rabbitmq-credentials
                key: host
        restartPolicy: Never
    backoffLimit: 4
  pollingInterval: 15
  maxReplicaCount: 30
  successfulJobsHistoryLimit: 5
  failedJobsHistoryLimit: 5
  triggers:
  - type: rabbitmq
    metadata:
      protocol: amqp
      queueName: hello
      mode: QueueLength
      value: '5'
    authenticationRef:
      name: rabbitmq-auth
```
## カスタムメトリクスによるスケーリング {#custom-metric-scaling}

KEDA では、組み込み Scaler に加えてカスタムメトリクスにも柔軟に対応できます。ビジネス要件に合わせた独自のスケーリングロジックを実装できます。

### External Metrics API の利用

counter の例では `rate(...[2m])` を使うため、目標値は累積件数ではなく replica あたりの events/second です。Prometheus query は数値を1つだけ返す必要があります。`ignoreNullValues: false` にすると series の欠落が error として表面化します。空の結果をゼロとみなすのか、telemetry の停止とみなすのかを意図的に選択してください。

Prometheus などの外部メトリクスソースを使って、カスタムメトリクスに基づくスケーリングを実装できます。

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: custom-metrics-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus-server.monitoring.svc.cluster.local
      threshold: '100'
      query: sum(rate(custom_metric_total{namespace="default",pod=~"my-app-.*"}[2m]))
      ignoreNullValues: 'false'
```

### HTTP Scaler の利用

これは数値を返す endpoint 向けの `metrics-api` Scaler です。request を横取りして buffer し、アクティベーションする別製品の KEDA HTTP add-on ではありません。特に対象ワークロードがゼロのときも、この endpoint は独立して利用可能でなければなりません。

HTTP endpoint からメトリクスを取得してスケーリングできます。

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: http-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
  - type: metrics-api
    metadata:
      targetValue: '100'
      url: https://metrics.example.com/metrics
      valueLocation: value
```

### カスタム Scaler の開発

以下の Go の例は、組み込み `metrics-api` Scaler 向けの **HTTP JSON メトリクス producer** です。Kubernetes の external.metrics.k8s.io API や KEDA の external-scaler protocol を実装する例ではありません。KEDA の `external` / `external-push` service では、文書化された gRPC method の `IsActive`、`GetMetricSpec`、`GetMetrics` と、push activation 用の `StreamIsActive` を実装します。

1. Metrics Server の実装:

完全な Go server は、数値の `value` と RFC3339 形式の `observed_at` を含み、原子的に置換される JSON snapshot の `METRICS_FILE` を読み込みます。別の business-metric producer がこのファイルを書き込む必要があります。ファイルがない、形式が不正、値が負、またはデータが2分より古い場合、HTTP 503 を返します。次の ScaledObject を使う前に、この server を build / deploy し、対応する Service を作成してください。これは Kubernetes の集約 API server ではありません。

```go
package main

import (
    "encoding/json"
    "errors"
    "io"
    "log"
    "net/http"
    "os"
    "time"
)

type snapshot struct {
    Value *float64 `json:"value"`
    ObservedAt time.Time `json:"observed_at"`
}

func metricsHandler(path string) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        if r.Method != http.MethodGet {
            w.Header().Set("Allow", "GET")
            http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
            return
        }
        f, err := os.Open(path)
        if err != nil {
            http.Error(w, "metric unavailable", http.StatusServiceUnavailable)
            return
        }
        defer f.Close()
        var v snapshot
        decoder := json.NewDecoder(io.LimitReader(f, 1<<20))
        if err = decoder.Decode(&v); err == nil {
            var extra any
            if err = decoder.Decode(&extra); !errors.Is(err, io.EOF) {
                http.Error(w, "invalid snapshot", http.StatusServiceUnavailable)
                return
            }
        } else {
            http.Error(w, "invalid snapshot", http.StatusServiceUnavailable)
            return
        }
        age := time.Since(v.ObservedAt)
        if v.Value == nil || *v.Value < 0 || v.ObservedAt.IsZero() || age < -5*time.Second || age > 2*time.Minute {
            http.Error(w, "stale or invalid metric", http.StatusServiceUnavailable)
            return
        }
        w.Header().Set("Content-Type", "application/json")
        w.Header().Set("Cache-Control", "no-store")
        _ = json.NewEncoder(w).Encode(v)
    }
}

func main() {
    path := os.Getenv("METRICS_FILE")
    if path == "" { log.Fatal("METRICS_FILE is required") }
    mux := http.NewServeMux()
    mux.HandleFunc("/metrics", metricsHandler(path))
    server := &http.Server{
        Addr: ":8080", Handler: mux,
        ReadHeaderTimeout: 5 * time.Second,
        WriteTimeout: 10 * time.Second,
        IdleTimeout: 60 * time.Second,
    }
    log.Fatal(server.ListenAndServe())
}
```

2. KEDA との統合:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: custom-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
  - type: metrics-api
    metadata:
      targetValue: '100'
      url: http://custom-metrics-server:8080/metrics
      valueLocation: value
```

## Twitter メトリクスによるスケーリング {#twitter-metric-scaling}

この例は X API（旧 Twitter）の v2 recent-counts endpoint を使います。収集の30秒前に終了する5分間の window 内の一致件数を数えるため、累積件数でも瞬時の投稿 rate でもありません。利用予定の account access、query の意味、料金、rate limit を確認してください。

### 前提条件

- recent Post count にアクセスできる X developer application と app bearer token。例を使っても API access や課金条件が付与されるわけではありません。
- メトリクスを収集して公開する service

### 実装手順

1. Twitter Metrics Collector Service を実装します。

以下の単独例を、Flask、requests、Gunicorn を含む collector image の `app.py` として保存します。deployment は Gunicorn worker を1つ使い、WSGI 起動時に background collector が動くよう `app:create_app()` を指定します。worker / replica を複数にすると API polling の回数が増えます。件数の一部しか取得できない場合や rate limit / 認証 error が発生した場合、この code は失敗として HTTP 503 を返し、切り詰められた検索ページの数を rate として黙って扱うことはありません。利用権限に合わせて polling を調整してください。

```python
import datetime as dt
import os
import threading
import time

import requests
from flask import Flask, jsonify

TOKEN = os.environ["X_BEARER_TOKEN"]
QUERY = os.environ.get("X_QUERY", "#kubernetes")
POLL_SECONDS = 60
MAX_AGE_SECONDS = 120
METRIC_NAME = "tweet_count"


def fetch_value():
    # Five-minute window ending 30 seconds ago; not a lifetime count or live rate.
    end = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=30)
    start = end - dt.timedelta(minutes=5)
    response = requests.get(
        "https://api.x.com/2/tweets/counts/recent",
        headers={"Authorization": f"Bearer {TOKEN}"},
        params={"query": QUERY, "granularity": "minute",
                "start_time": start.isoformat(), "end_time": end.isoformat()},
        timeout=(3, 10),
    )
    response.raise_for_status()
    body = response.json()
    meta = body["meta"]
    # Never silently scale from a partial result or an API error payload.
    if body.get("errors") or meta.get("next_token"):
        raise ValueError("incomplete counts response")
    value = meta["total_tweet_count"]
    if type(value) is not int or value < 0:
        raise ValueError("invalid count")
    return value


def create_app():
    app = Flask(__name__)
    lock = threading.Lock()
    state = {"value": None, "updated": 0.0, "healthy": False}

    def collect():
        while True:
            try:
                value = fetch_value()
                if type(value) is not int or value < 0:
                    raise ValueError("invalid metric")
                with lock:
                    state.update(value=value, updated=time.monotonic(), healthy=True)
            except Exception as exc:
                with lock:
                    state["healthy"] = False
                app.logger.warning("Metric refresh failed: %s", type(exc).__name__)
            time.sleep(POLL_SECONDS)

    @app.get("/metrics")
    def get_metrics():
        with lock:
            current = state.copy()
        if not current["healthy"] or time.monotonic() - current["updated"] > MAX_AGE_SECONDS:
            return jsonify(error="metric unavailable or stale"), 503
        response = jsonify({METRIC_NAME: current["value"]})
        response.headers["Cache-Control"] = "no-store"
        return response

    threading.Thread(target=collect, daemon=True).start()
    return app


if __name__ == "__main__":
    # Local development only; use a WSGI server for the deployment example.
    create_app().run(host="127.0.0.1", port=8080)
```

2. Metrics Collector Service をデプロイします。

デプロイ前に collector image を build して固定します。既存の token file を Secret input として渡し、shell argument に token の値を含めないでください。

```bash
kubectl create secret generic twitter-api-secrets --namespace default --from-file=bearer-token=./x-bearer-token
```

この command を実行すると Kubernetes Secret が作成されます。この監査では実行していません。source file は version control に追加しないでください。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: twitter-metrics-collector
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: twitter-metrics-collector
  template:
    metadata:
      labels:
        app: twitter-metrics-collector
    spec:
      containers:
      - name: collector
        image: twitter-metrics-collector:latest
        ports:
        - containerPort: 8080
        env:
        - name: X_BEARER_TOKEN
          valueFrom:
            secretKeyRef:
              name: twitter-api-secrets
              key: bearer-token
        command:
        - gunicorn
        args:
        - --bind
        - 0.0.0.0:8080
        - --workers
        - '1'
        - --threads
        - '4'
        - app:create_app()
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            memory: 256Mi
        readinessProbe:
          httpGet:
            path: /metrics
            port: 8080
          periodSeconds: 10
          failureThreshold: 3
      automountServiceAccountToken: false
---
apiVersion: v1
kind: Service
metadata:
  name: twitter-metrics-collector
  namespace: default
spec:
  selector:
    app: twitter-metrics-collector
  ports:
  - port: 80
    targetPort: 8080
```

3. KEDA ScaledObject を設定します。

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: twitter-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: twitter-processor
  minReplicaCount: 1
  maxReplicaCount: 20
  pollingInterval: 15
  cooldownPeriod: 30
  triggers:
  - type: metrics-api
    metadata:
      targetValue: "10"
      url: "http://twitter-metrics-collector/metrics"
      valueLocation: "tweet_count"
```

デフォルトの AverageValue では、count / target の比率から設定済みの範囲内で replica 数が提案されます。処理 throughput を直接モデル化するものではありません。collector は独立して1 replicaで稼働し、利用できないときは503を返します。upstream 停止だけを理由に再起動させる liveness probe はありません。本番利用には、テスト済みの認証情報、制限、ライフサイクル管理、observability も必要です。

## Google Calendar によるスケーリング {#google-calendar-scaling}

この例は、これから1時間の間に**一部でも重なる** Google Calendar event instance を数えます。進行中の event も含みます。`timeMin` は終了時刻、`timeMax` は開始時刻で event を絞り込みます。すべてのページを数え、取得が一部のみ、失敗、または古い場合は、誤ったゼロではなくメトリクス利用不可として扱います。

### 前提条件

- Calendar API を有効にし、特定の共有 calendar を読み取れる service account を使います。実際の calendar ID を指定してください。service account と共有されていないユーザー calendar では `primary` を代わりに使えません。
- メトリクスを収集して公開する service

### 実装手順

1. Google Calendar Metrics Collector Service を実装します。

Flask、requests、google-auth、Gunicorn を含む専用 image に、別の例として `app.py` を保存してください。単一 collector thread が全ページをたどり、token の反復や page safety limit 超過を failure として報告します。数えるのは重なる event instance であり、参加者数や必要 replica 数ではありません。service account には calendar access を許可する必要があります。OAuth scope を設定するだけではアクセス権は付与されません。

```python
import datetime as dt
import os
import threading
import time
from urllib.parse import quote

from flask import Flask, jsonify
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

CALENDAR_ID = os.environ["CALENDAR_ID"]
SERVICE_ACCOUNT_FILE = "/etc/secrets/service-account.json"
POLL_SECONDS = 300
MAX_AGE_SECONDS = 360
METRIC_NAME = "upcoming_events"


def fetch_value():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/calendar.readonly"],
    )
    now = dt.datetime.now(dt.timezone.utc)
    params = {"timeMin": now.isoformat(),
              "timeMax": (now + dt.timedelta(hours=1)).isoformat(),
              "singleEvents": "true", "showDeleted": "false",
              "orderBy": "startTime", "maxResults": 2500}
    url = f"https://www.googleapis.com/calendar/v3/calendars/{quote(CALENDAR_ID, safe='')}/events"
    total = 0
    seen_tokens = set()
    with AuthorizedSession(credentials) as session:
        for _ in range(100):
            response = session.get(url, params=params, timeout=(3, 10))
            response.raise_for_status()
            body = response.json()
            if body.get("error") or body.get("kind") != "calendar#events" or not isinstance(body.get("items", []), list):
                raise ValueError("invalid events response")
            total += len(body.get("items", []))
            token = body.get("nextPageToken")
            if not token:
                return total
            if token in seen_tokens:
                raise ValueError("repeated page token")
            seen_tokens.add(token)
            params["pageToken"] = token
    raise ValueError("pagination limit exceeded; result is incomplete")


def create_app():
    app = Flask(__name__)
    lock = threading.Lock()
    state = {"value": None, "updated": 0.0, "healthy": False}

    def collect():
        while True:
            try:
                value = fetch_value()
                if type(value) is not int or value < 0:
                    raise ValueError("invalid metric")
                with lock:
                    state.update(value=value, updated=time.monotonic(), healthy=True)
            except Exception as exc:
                with lock:
                    state["healthy"] = False
                app.logger.warning("Metric refresh failed: %s", type(exc).__name__)
            time.sleep(POLL_SECONDS)

    @app.get("/metrics")
    def get_metrics():
        with lock:
            current = state.copy()
        if not current["healthy"] or time.monotonic() - current["updated"] > MAX_AGE_SECONDS:
            return jsonify(error="metric unavailable or stale"), 503
        response = jsonify({METRIC_NAME: current["value"]})
        response.headers["Cache-Control"] = "no-store"
        return response

    threading.Thread(target=collect, daemon=True).start()
    return app


if __name__ == "__main__":
    # Local development only; use a WSGI server for the deployment example.
    create_app().run(host="127.0.0.1", port=8080)
```

2. Metrics Collector Service をデプロイします。

実際に共有された calendar ID と、既存の service-account JSON file を使ってください。以下を実行すると Secret が作成されますが、レビュー時には実行していません。

```bash
kubectl create secret generic google-calendar-secrets --namespace default --from-file=service-account.json=./service-account.json
```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: calendar-metrics-collector
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: calendar-metrics-collector
  template:
    metadata:
      labels:
        app: calendar-metrics-collector
    spec:
      containers:
      - name: collector
        image: calendar-metrics-collector:latest
        ports:
        - containerPort: 8080
        env:
        - name: CALENDAR_ID
          value: REPLACE_WITH_SHARED_CALENDAR_ID
        volumeMounts:
        - name: google-calendar-credentials
          mountPath: /etc/secrets
          readOnly: true
        command:
        - gunicorn
        args:
        - --bind
        - 0.0.0.0:8080
        - --workers
        - '1'
        - --threads
        - '4'
        - app:create_app()
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            memory: 256Mi
        readinessProbe:
          httpGet:
            path: /metrics
            port: 8080
          periodSeconds: 10
          failureThreshold: 3
      volumes:
      - name: google-calendar-credentials
        secret:
          secretName: google-calendar-secrets
      automountServiceAccountToken: false
---
apiVersion: v1
kind: Service
metadata:
  name: calendar-metrics-collector
  namespace: default
spec:
  selector:
    app: calendar-metrics-collector
  ports:
  - port: 80
    targetPort: 8080
```

3. KEDA ScaledObject を設定します。

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: calendar-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: calendar-processor
  minReplicaCount: 1
  maxReplicaCount: 10
  pollingInterval: 15
  cooldownPeriod: 30
  triggers:
  - type: metrics-api
    metadata:
      targetValue: "1"
      url: "http://calendar-metrics-collector/metrics"
      valueLocation: "upcoming_events"
```

デフォルトの AverageValue では、count / target の比率から設定済みの範囲内で replica 数が提案されます。処理 throughput を直接モデル化するものではありません。collector は独立して1 replicaで稼働し、利用できないときは503を返します。upstream 停止だけを理由に再起動させる liveness probe はありません。本番利用には、テスト済みの認証情報、制限、ライフサイクル管理、observability も必要です。

## Istio メトリクスによるスケーリング {#istio-metric-scaling}

この例は Istio service mesh から収集したメトリクスに基づいてアプリケーションをスケーリングします。ここでは1秒あたりの request 数（RPS）を使います。

### 前提条件

- Istio service mesh がインストール済みであること
- Prometheus がインストールされ、Istio と連携していること

### 実装手順

1. 既存の Istio sidecar インストールと injection policy を確認します。この例は mesh 内の routing を使い、存在しない ingress Gateway resource を前提にしません。

```bash
istioctl proxy-status
kubectl get namespace default --show-labels
kubectl get pods -n default
```

2. サンプルアプリケーションをデプロイします。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sample-app
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: sample-app
  template:
    metadata:
      labels:
        app: sample-app
    spec:
      containers:
      - name: sample-app
        image: nginx:1.30.6
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: sample-app
  namespace: default
spec:
  selector:
    app: sample-app
  ports:
  - port: 80
    targetPort: 80
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: sample-app
  namespace: default
spec:
  hosts:
  - sample-app.default.svc.cluster.local
  gateways:
  - mesh
  http:
  - route:
    - destination:
        host: sample-app
        port:
          number: 80
```

3. KEDA ScaledObject を設定します。

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: istio-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sample-app
  minReplicaCount: 1
  maxReplicaCount: 10
  pollingInterval: 15
  cooldownPeriod: 30
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus.istio-system:9090
      threshold: '10'
      query: sum(rate(istio_requests_total{reporter="destination",destination_service="sample-app.default.svc.cluster.local"}[2m]))
      ignoreNullValues: 'false'
```

デフォルトの `AverageValue` metric type では、合計100 request / second、replica あたりの target を10 request / second とすると、HPA の tolerance、stabilization、上限 / 下限を考慮する前の目安は約10 replicaです。query は destination report を選ぶことで source / destination の両方から同じ request を二重計上しないようにしています。Prometheus が対象 traffic を実際に scrape している必要があります。

### 高度な設定

次の例は **利用者が定義した `request_path` telemetry label** を必要とします。この label は Istio metric にデフォルトで存在する dimension ではありません。任意 URL による cardinality の増加を避けながら、先に label を設定して動作確認するか、直前の query を使ってください。同じ対象向けに追加で導入するものではなく、別の ScaledObject の例です。

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: istio-path-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sample-app
  minReplicaCount: 1
  maxReplicaCount: 10
  pollingInterval: 15
  cooldownPeriod: 30
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus.istio-system:9090
      threshold: '5'
      query: sum(rate(istio_requests_total{reporter="destination",destination_service="sample-app.default.svc.cluster.local",request_path="/api/v1/products"}[2m]))
      ignoreNullValues: 'false'
```

error ratio や latency は、スケーリング入力より alerting signal に適することがよくあります。次の任意例は service 全体の ratio に `metricType: Value` を使い、分母がゼロの場合を処理して scale-up の速度を制限します。replica を増やせば診断済みの過負荷が実際に軽減することを前提にしています。下流 error や少量 sample の揺らぎがあると有害なスケーリングを起こす可能性があります。本番での効果は測定していません。

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: istio-error-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sample-app
  minReplicaCount: 1
  maxReplicaCount: 10
  pollingInterval: 15
  cooldownPeriod: 30
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus.istio-system:9090
      threshold: '0.05'
      query: (sum(rate(istio_requests_total{reporter="destination",destination_service="sample-app.default.svc.cluster.local",response_code=~"5.*"}[2m]))
        or vector(0)) / clamp_min(sum(rate(istio_requests_total{reporter="destination",destination_service="sample-app.default.svc.cluster.local"}[2m])),
        0.001)
      ignoreNullValues: 'false'
    metricType: Value
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleUp:
          policies:
          - type: Pods
            value: 1
            periodSeconds: 60
        scaleDown:
          stabilizationWindowSeconds: 300
```

## Cron によるスケーリング {#cron-based-scaling}

KEDA は Cron expression を使った時間ベースのスケーリングに対応します。予測可能な traffic pattern や予定に合わせて、事前にアプリケーションの規模を調整できます。

### Cron Scaler の基本例

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: cron-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sample-app
  minReplicaCount: 0
  maxReplicaCount: 10
  pollingInterval: 15
  cooldownPeriod: 30
  triggers:
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: 30 * * * *
      end: 45 * * * *
      desiredReplicas: "5"
```

毎時30～45分の間、Cron trigger は replica 数を最低5に保つよう要求します。その時間帯以外は trigger が inactive になります。ゼロまで下がる場合は polling と設定済み cooldown（この例では30秒）、および controller の処理時間を待ちます。45分ちょうどに遷移する保証はありません。

### 営業時間と時間外のスケーリング

時間外の最小数を `minReplicaCount: 2` にし、平日の営業時間帯に replica 数を5にする Cron window を1つだけ設定します。夜間と週末の window を重ねずに済みます。HPA stabilization によって営業時間後の縮小が遅れる場合があります。

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: multi-cron-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sample-app
  minReplicaCount: 2
  maxReplicaCount: 10
  pollingInterval: 15
  cooldownPeriod: 30
  triggers:
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: 0 9 * * 1-5
      end: 0 18 * * 1-5
      desiredReplicas: '5'
```

### Cron と他の Scaler の併用

Cron Scaler を他の Scaler と組み合わせると、基本となる規模を時間で設定し、実際の負荷に応じた追加スケーリングも行えます。

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: combined-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sample-app
  minReplicaCount: 1
  maxReplicaCount: 20
  pollingInterval: 15
  cooldownPeriod: 30
  triggers:
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: 0 9 * * 1-5
      end: 0 18 * * 1-5
      desiredReplicas: '5'
  - type: prometheus
    metadata:
      serverAddress: http://prometheus.monitoring.svc.cluster.local:9090
      threshold: '10'
      query: sum(rate(http_requests_total{app="sample-app"}[1m]))
      ignoreNullValues: 'false'
```

## Amazon EKS との統合 {#integration-with-amazon-eks}

Kubernetes の互換性、operator の ID、権限、接続性を適切に設定すれば、KEDA は AWS のメトリクスを使って EKS workload をスケーリングできます。KEDA 自体が計算資源を増やすわけではありません。workload のスケーリングと適切な node / Fargate 容量の設計を組み合わせてください。

### EKS への KEDA インストール

```bash
helm status keda -n keda
kubectl get deployment -n keda
```

### AWS service に基づくスケーリング

#### SQS queue に基づくスケーリング

```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: aws-credentials
  namespace: default
spec:
  podIdentity:
    provider: aws
    identityOwner: keda
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: aws-sqs-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sqs-consumer
  minReplicaCount: 0
  maxReplicaCount: 10
  pollingInterval: 15
  cooldownPeriod: 30
  triggers:
  - type: aws-sqs-queue
    metadata:
      queueURL: https://sqs.us-west-2.amazonaws.com/123456789012/my-queue
      queueLength: '5'
      awsRegion: us-west-2
    authenticationRef:
      name: aws-credentials
```

#### CloudWatch metric に基づくスケーリング

```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: aws-credentials
  namespace: default
spec:
  podIdentity:
    provider: aws
    identityOwner: keda
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: aws-cloudwatch-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cloudwatch-app
  minReplicaCount: 1
  maxReplicaCount: 10
  pollingInterval: 15
  cooldownPeriod: 30
  triggers:
  - type: aws-cloudwatch
    metadata:
      namespace: AWS/SQS
      dimensionName: QueueName
      dimensionValue: my-queue
      metricName: ApproximateNumberOfMessagesVisible
      targetMetricValue: '5'
      minMetricValue: '0'
      awsRegion: us-west-2
      metricStat: Average
      metricStatPeriod: '60'
      metricCollectionTime: '300'
    authenticationRef:
      name: aws-credentials
```

### IRSA（Service Account 向け IAM Role）との統合

この例は `system:serviceaccount:keda:keda-operator` に対する**既存の** IRSA role があり、この cluster の OIDC provider に紐付けられ、`aud: sts.amazonaws.com` が設定済みであることを前提にします。対象 queue に対する `sqs:GetQueueAttributes` と、必要な CloudWatch metric 読み取り action（例: `cloudwatch:GetMetricData`）を許可してください。resource レベルの指定をサポートしない CloudWatch action は resource に wildcard が必要ですが、要求する Region で制限できます。consumer 自身の権限は別に設定します。以下の command は既存設定を調査するもので、role の作成はレビュー済みの infrastructure 設定で行ってください。

```bash
: "${KEDA_IAM_ROLE_NAME:?Set the existing IRSA role name}"
aws iam get-role --role-name "$KEDA_IAM_ROLE_NAME" --query Role.AssumeRolePolicyDocument
kubectl get serviceaccount keda-operator -n keda -o yaml
```

```yaml
serviceAccount:
  operator:
    create: true
    name: keda-operator
    annotations:
      eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/keda-operator-role
      eks.amazonaws.com/sts-regional-endpoints: 'true'
```

## ベストプラクティス {#best-practices}

### パフォーマンスの最適化

1. **適切な polling 間隔を設定する**: workload の特性に合わせて間隔を調整します。
2. **Cooldown と HPA の動作を別々に設定する**: cooldown はゼロスケールを制御し、HPA の stabilization / policy はゼロ以外の replica 数の変更を制御します。
3. **Resource Request と Limit を設定する**: KEDA component に適切な resource を割り当てます。
4. **効率的な query を書く**: metric query を最適化します。

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: optimized-scaler
  namespace: default
spec:
  pollingInterval: 30
  cooldownPeriod: 300
  scaleTargetRef:
    name: my-app
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus.monitoring.svc.cluster.local:9090
      threshold: '100'
      query: sum(rate(http_requests_total{namespace="default",app="my-app"}[2m]))
      ignoreNullValues: 'false'
```

### 信頼性の向上

1. **複数 trigger の動作を理解する**: HPA は通常、最大の replica 推奨数を採用します。trigger の値を足し合わせて容量を決めるわけではなく、error によって scale-down が抑止される場合があります。
2. **最小 / 最大 replica 数を適切に設定する**: workload の要件に合う範囲を設定します。
3. **障害時の動作を決める**: KEDA 2.21 の fallback は CPU / memory 以外の Value / AverageValue trigger に対応し、ScaledObject に適用されます。ScaledJob には適用されません。停止時の挙動と認証 failure をテストしてください。
4. **監視と alert を設定する**: KEDA の運用状態を監視します。

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reliable-scaler
  namespace: default
spec:
  minReplicaCount: 2
  maxReplicaCount: 20
  fallback:
    failureThreshold: 3
    replicas: 5
  scaleTargetRef:
    name: my-app
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus.monitoring.svc.cluster.local:9090
      threshold: '100'
      query: sum(rate(http_requests_total{namespace="default",app="my-app"}[2m]))
      ignoreNullValues: 'false'
```

### セキュリティの強化

以下の NetworkPolicy は Twitter collector への ingress を TCP 8080 の KEDA operator に制限する例です。KEDA control plane 全体を保護する policy ではありません。適用には NetworkPolicy 対応が必要です。KEDA 自体への通信を制限する前に、metrics API / admission webhook への API server access、operator と metrics-server の通信、DNS、Kubernetes API、各 Scaler endpoint を考慮してください。EKS control plane は単純に `kube-system` 内の Pod として扱えるものではありません。

1. **最小権限の原則を適用する**: 必要な権限だけを付与します。
2. **Secret を管理する**: 機密情報を安全に管理します。
3. **NetworkPolicy を適用する**: KEDA component への access を制限します。
4. **RBAC を設定する**: 適切な role-based access control を構成します。

```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: secure-auth
  namespace: default
spec:
  secretTargetRef:
  - parameter: host
    name: rabbitmq-credentials
    key: host
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: twitter-metrics-from-keda
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: twitter-metrics-collector
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: keda
      podSelector:
        matchLabels:
          app: keda-operator
    ports:
    - protocol: TCP
      port: 8080
```

## トラブルシューティング {#troubleshooting}

### よくある問題

#### 1. スケーリングされない

**症状**: metric がしきい値を超えても Pod 数が変わらない

**対処**:
- KEDA log を確認します。
- metric source への接続を確認します。
- 認証設定を確認します。

```bash
# Check KEDA operator logs
kubectl logs -n keda -l app=keda-operator

# Check KEDA metrics server logs
kubectl logs -n keda -l app=keda-operator-metrics-apiserver

# Check ScaledObject status
kubectl get scaledobject -n <namespace> <name> -o yaml
```

#### 2. ゼロスケールの問題

**症状**: 活動がないのに replica 数が0まで下がらない

**対処**:
- minReplicaCount の設定を確認します。
- metric value を確認します。
- HPA の状態を確認します。

```bash
# Check HPA status
kubectl get hpa -n <namespace>

# Check metric values directly
kubectl get --raw "/apis/external.metrics.k8s.io/v1beta1/namespaces/<namespace>/<metric-name>?labelSelector=scaledobject.keda.sh%2Fname%3D<scaledobject-name>" | jq
```

#### 3. 認証の問題

**症状**: metric source に接続できない

**対処**:
- TriggerAuthentication の設定を確認します。
- Secret または環境変数を確認します。
- 権限を確認します。

```bash
# Check TriggerAuthentication
kubectl get triggerauthentication -n <namespace> <name> -o yaml

# Check secrets
kubectl get secret -n <namespace> <name> -o json | jq '{name: .metadata.name, type: .type, keys: ((.data // {}) | keys)}'
```

### デバッグ用ツール

```bash
# Check KEDA version
kubectl get deployment -n keda keda-operator -o jsonpath="{.spec.template.spec.containers[0].image}"

# Check ScaledObject status
kubectl describe scaledobject -n <namespace> <name>

# Check HPA status
kubectl describe hpa -n <namespace> <name>

# Check metric values
kubectl get --raw "/apis/external.metrics.k8s.io/v1beta1/namespaces/<namespace>/<metric-name>?labelSelector=scaledobject.keda.sh%2Fname%3D<scaledobject-name>"

# Check KEDA logs
kubectl logs -n keda -l app=keda-operator --tail=100
```

## まとめ {#conclusion}

KEDA（Kubernetes Event-driven Autoscaling）は、Kubernetes 環境でイベント駆動型のオートスケーリングを実現するツールです。Kubernetes HPA を拡張し、さまざまなイベントソースとメトリクスに基づいて workload をスケーリングします。

この章では、KEDA の基本概念とインストール方法、各種 Scaler の使い方、カスタムメトリクスによるスケーリング、Twitter や Google Calendar などの外部 service との統合、Istio メトリクスと Cron によるスケーリング、Amazon EKS との統合、ベストプラクティス、トラブルシューティングを説明しました。

KEDA を使うと、アプリケーションを効率的にスケーリングし、resource 使用量を最適化してコストを抑えられます。イベント駆動型アーキテクチャや serverless pattern の実装に特に役立ちます。

### 次のステップ

- KEDA で serverless architecture を実装する
- さまざまなイベントソースとの統合を調べる
- カスタム Scaler を開発する
- マルチクラスター環境で KEDA を活用する
- 他の cloud-native tool と KEDA を連携する

## 参考資料

- [KEDA 公式ドキュメント](https://keda.sh/docs/)
- [KEDA GitHub repository](https://github.com/kedacore/keda)
- [KEDA Scaler 一覧](https://keda.sh/docs/latest/scalers/)
- [KEDA Operator Hub](https://operatorhub.io/operator/keda)
- [AWS IRSA 設定](https://docs.aws.amazon.com/eks/latest/userguide/associate-service-account-role.html)

## クイズ

この章の内容を確認するには、[トピック別クイズ](../quizzes/autoscaling/05-keda-quiz.md)に挑戦してください。

この改訂で確認した資料: [KEDA 互換性](https://keda.sh/docs/2.21/operate/cluster/)、[ScaledObject](https://keda.sh/docs/2.21/reference/scaledobject-spec/)、[ScaledJob](https://keda.sh/docs/2.21/reference/scaledjob-spec/)、[AWS 認証](https://keda.sh/docs/2.21/authentication-providers/aws/)、[External scaler gRPC](https://keda.sh/docs/2.21/concepts/external-scalers/)、[X の count API](https://docs.x.com/x-api/posts/counts/quickstart)、[Calendar event API](https://developers.google.com/workspace/calendar/api/v3/reference/events/list)、[HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)。
