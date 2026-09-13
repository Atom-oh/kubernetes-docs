# 可観測性クイズ

> **最終更新**: September 11, 2026 · Istio 1.31 · Kubernetes 1.32–1.36。EKSとKialiの互換性制限はインストールとダッシュボードの章を参照してください。

このクイズは設定済みのサイドカー/waypointテレメトリーを扱います。各解答例は独立し、明記したバックエンド、名前空間、権限、通信が存在する前提です。YAML/API/クエリ確認は本番や実クラスターのテストではありません。ztunnel L4、ネイティブサイドカー、HAデプロイにはそれぞれ固有の収集設定が必要です。

## 選択問題（1-5）

### 問1: Prometheusメトリクス

**Istio標準サービスメトリクスの名前/ファミリーではない**ものはどれですか？

A. istio\_requests\_total（総リクエスト数）\
B. istio\_request\_duration\_milliseconds（リクエストレイテンシー）\
C. istio\_request\_bytes（リクエストサイズ）\
D. istio\_pod\_cpu\_usage（Pod CPU使用量）

<details>

<summary>解答を表示</summary>

**正解: D**

Istio標準サービスメトリクスは通信を記述し、Envoyは内部プロキシ統計も公開します。Prometheusはkubelet/cAdvisor（またはランタイムリソースのパイプライン）からコンテナCPU使用量を取得します。Metrics Serverは自動スケーリングと`kubectl top`用のリソースメトリクス、kube-state-metricsはオブジェクト状態と設定requests/limitsを公開し、実測CPU消費は公開しません。

**解説:**

**Istioが収集するメトリクス:**

1. **istio\_requests\_total（A - O）**

```promql
# Request rate by service (per second)
sum(rate(istio_requests_total{reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
```

2. **istio\_request\_duration\_milliseconds（B - O）**

```promql
# P95 latency
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket{reporter="destination"}[5m])) by (le)
)
```

3. **istio\_request\_bytes（C - O）**

```promql
# Request body byte rate (bytes/second), not mean request size
sum(rate(istio_request_bytes_sum{reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
```

4. **istio\_pod\_cpu\_usage（D - X）**

* Istioのメトリクスではない
* Kubernetesメトリクス: `container_cpu_usage_seconds_total`
* kubelet/cAdvisorをスクレイプする。設定limitsと使用量の比較にはkube-state-metricsが有用

**Istioメトリクスのカテゴリ:**

| カテゴリ | メトリクス例 | 説明 |
| ------------ | --------------------------------------------- | ----------------------------- |
| **リクエスト** | istio\_requests\_total | リクエスト数、応答コード |
| **所要時間** | istio\_request\_duration\_milliseconds | レイテンシー分布 |
| **サイズ** | istio\_request\_bytes, istio\_response\_bytes | 通信サイズ |
| **TCP** | istio\_tcp\_connections\_opened\_total | TCP接続 |

**ゴールデンシグナルの例:**

```promql
# 1. Latency
histogram_quantile(0.95,
  sum(rate(
    istio_request_duration_milliseconds_bucket{reporter="destination",
      destination_service_name="reviews", destination_service_namespace="default"
    }[5m]
  )) by (le)
)

# 2. Traffic
sum(rate(
  istio_requests_total{reporter="destination",
    destination_service_name="reviews", destination_service_namespace="default"
  }[5m]
))

# 3. Errors (error rate)
sum(rate(
  istio_requests_total{reporter="destination",
    destination_service_name="reviews", destination_service_namespace="default",
    response_code=~"5.."
  }[5m]
))
/
sum(rate(
  istio_requests_total{reporter="destination",
    destination_service_name="reviews", destination_service_namespace="default"
  }[5m]
))

# 4. Saturation - Uses Kubernetes metrics
sum(rate(
  container_cpu_usage_seconds_total{
    namespace="default", container="istio-proxy", pod=~"reviews-.*"
  }[5m]
))
```

**メトリクスの確認:**

```bash
# Check metrics via Envoy Admin API
istioctl x envoy-stats <pod-name>.default --output prom

# Check in Prometheus
kubectl port-forward -n istio-system svc/prometheus 9090:9090
# Query at http://localhost:9090
```

**参考資料:**

* [メトリクス](../../../service-mesh/istio/observability/01-metrics.md)

</details>

***

### 問2: 分散トレーシング

動作するトレースprovider/バックエンドがある場合、サービス呼び出し間でプロキシスパンをつなぐために必要なアプリケーションの責任は何ですか？

A. アプリケーションがトレースIDを生成する必要がある\
B. アプリケーションがHTTPヘッダーを伝播する必要がある\
C. 全サービスにJaegerクライアントをインストールする必要がある\
D. Envoyが自動ですべてを処理する

<details>

<summary>解答を表示</summary>

**正解: B**

設定済みプロキシはスパンとトレースIDを生成できますが、アプリは送信呼び出しへトレースコンテキストを伝播する必要があります。SDKはアクティブコンテキストを注入すべきなので、トレースIDを維持しつつ子スパンIDは変わり得ます。独自スパンを持たない透過的アプリは、選択された伝播ヘッダーを転送できます。

**解説:**

**分散トレーシングの動作:**

![Ingress Gatewayが受信要求にトレースヘッダーを生成し、下流サービスA、B、Cが次ホップへコンテキストを伝播し、各ホップもJaegerへスパンを送る図。](../../../.gitbook/assets/en-quizzes-service-mesh-istio-observability-0.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-quizzes-service-mesh-istio-observability-0.html)

図は設定済みJaegerへのB3伝播を示します。W3C伝播や中間OpenTelemetry Collectorもサポートされます。計装済みアプリは全ヘッダーをそのままコピーせず、アクティブスパンのコンテキストを注入します。

**伝播するHTTPヘッダー:**

```text
W3C: traceparent, tracestate
B3 (if configured): b3 OR x-b3-traceid, x-b3-spanid, x-b3-parentspanid, x-b3-sampled
Istio correlation: x-request-id
B3 debug flag: x-b3-flags (do not force debug sampling on ordinary traffic)
```

**アプリケーションコード例:**

```python
# Python Flask example
from flask import Flask, request
import requests

app = Flask(__name__)

@app.route('/api/users')
def get_users():
    # 1. Extract received headers
    headers = {}
    for header in ['x-request-id', 'traceparent', 'tracestate', 'b3', 'x-b3-traceid', 'x-b3-spanid',
                   'x-b3-parentspanid', 'x-b3-sampled', 'x-b3-flags']:
        if header in request.headers:
            headers[header] = request.headers[header]

    # 2. Propagate headers when calling next service
    response = requests.get(
        'http://user-service/users',
        headers=headers, timeout=3  # Selected propagation format
    )

    response.raise_for_status()
    return response.json()
```

```javascript
// Node.js Express example
const express = require('express');
const axios = require('axios');
const app = express();

app.get('/api/users', async (req, res) => {
  // 1. Extract received headers
  const tracingHeaders = {};
  ['x-request-id', 'traceparent', 'tracestate', 'b3', 'x-b3-traceid', 'x-b3-spanid',
   'x-b3-parentspanid', 'x-b3-sampled', 'x-b3-flags'].forEach(header => {
    if (req.headers[header]) {
      tracingHeaders[header] = req.headers[header];
    }
  });

  // 2. Propagate headers when calling next service
  try {
    const response = await axios.get('http://user-service/users', {
      headers: tracingHeaders, timeout: 3000
    });
    res.json(response.data);
  } catch (error) {
    res.status(502).json({error: 'Downstream request failed'});
  }
});
```

**各選択肢の分析:**

* **A（X）**: EnvoyがトレースIDを自動生成
* **B（O）**: アプリケーションがHTTPヘッダーを伝播する必要がある（必須）
* **C（X）**: Jaegerクライアントは不要。Envoyがスパンを送信
* **D（X）**: Envoyはスパンを作成/送信するが、ヘッダー伝播はアプリの責任

**サンプリング設定:**

トレース章の`otel-tracing` providerを前提とします。`1.0`は100%でなく1%です。provider/エクスポーター設定とコンテキスト伝播は別の要件です。

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: tracing-sample
  namespace: default
spec:
  tracing:
  - providers:
    - name: otel-tracing
    randomSamplingPercentage: 1.0
```

**Jaegerへのアクセス:**

```bash
kubectl port-forward -n observability svc/jaeger-query 16686:16686
```

**参考資料:**

* [分散トレーシング](../../../service-mesh/istio/observability/02-tracing.md)

</details>

***

### 問3: Kialiの可視化

Kialiが**提供しない**機能はどれですか？

A. サービストポロジー可視化\
B. トラフィックフロー分析\
C. カナリアデプロイの自動実行\
D. Istio設定検証

<details>

<summary>解答を表示</summary>

**正解: C**

Kialiは**観測と分析のツール**で、デプロイ実行は**Argo Rollouts**などが担当します。

**解説:**

**Kialiの主な機能:**

**1. サービストポロジー可視化（A - O）**

```bash
# Open Kiali dashboard
istioctl dashboard kiali

# Features:
# - Real-time service connection display
# - Traffic flow direction display
# - Service status (healthy/error)
# - Response time display
```

**グラフ表示例:**

```
Frontend → Backend → Database
   ↓
External API

Color codes:
- Green: Normal
- Red: Error
- Gray: No traffic
```

**2. トラフィックフロー分析（B - O）**

Kialiは次を表示します。

* リクエスト数（RPS）
* エラー率（%）
* P50/P95/P99レイテンシー
* TCP接続数

**3. カナリアデプロイの自動実行（C - X）**

* Kialiは通信を表示し、権限があればIstio設定の編集/トラフィックウィザードの使用が可能
* 自動の段階的デリバリーコントローラーを代替しない
* デプロイ実行: Argo Rollouts、Flagger

**4. Istio設定検証（D - O）**

[Kiali検証カタログ](https://kiali.io/docs/features/validations/)の例:

- VirtualService: 未定義subset（`KIA1107`）。
- DestinationRule: 重複するhost/subset定義（`KIA0201`）。
- AuthorizationPolicy: 参照名前空間がない（`KIA0101`）、またはprincipalが検出済みワークロードServiceAccountと関連付かない（`KIA0106`）。

確認内容はKiali版、検出範囲、アクセスに依存します。実コード/メッセージと実効プロキシポリシーを確認してください。Kialiは任意ポリシーの競合や、全証明書/実行時経路の動作を証明しません。

**Kialiのインストール:**

固定Operator、認証、現互換性制限は[ダッシュボードの章](../../../service-mesh/istio/observability/04-dashboards.md)に従います。Kialiは別途インストールします。サンプルアドオンはデモであり、バックエンド/RBAC設定なしのHelmインストールは本番設定ではありません。

**Kialiの主なメニュー:**

```
1. Overview: Service summary by Namespace
2. Graph: Service topology
3. Applications: Application list
4. Workloads: Deployment, StatefulSet, etc.
5. Services: Kubernetes Service
6. Istio Config: VirtualService, DestinationRule, etc.
```

**Kialiと他ツールの比較:**

| ツール | 役割 | 自動の段階的デリバリー |
| ----------------- | ----------------------------------- | -------------------- |
| **Kiali** | 可視化、分析、検証 | なし |
| **Argo Rollouts** | 段階的デリバリー | あり |
| **Flagger** | カナリアデプロイ自動化 | あり |
| **Grafana** | メトリクスダッシュボード | なし |
| **Jaeger** | 分散トレーシング | なし |

**実用例:**

```bash
# 1. Check service topology in Kiali
istioctl dashboard kiali

# 2. Detect anomalies in Graph view
#    - reviews service error rate 5%
#    - productpage → reviews latency increase

# 3. Check details in Workload view
#    - Check reviews-v2 Pod logs
#    - Check Envoy metrics

# 4. Validate configuration in Istio Config view
#    - Found typo in VirtualService
#    - Fix and redeploy
```

**参考資料:**

* [可視化](../../../service-mesh/istio/observability/04-dashboards.md)
* [Kiali公式ドキュメント](https://kiali.io/docs/)

</details>

***

### 問4: アクセスログ設定

Istioでアクセスログを**JSON形式**で出力するにはどう設定しますか？

A. IstioOperatorのmeshConfig.accessLogEncodingをJSONにする\
B. Envoy ConfigMapを直接変更する\
C. 各Podにアノテーションを追加する\
D. PrometheusクエリでJSONに変換する

<details>

<summary>解答を表示</summary>

**正解: A**

Aは有効なMeshConfig方式です。ログを有効にした`istioctl install -f`入力で`accessLogEncoding: JSON`を使います。クラスター内Operatorリソースではありません。ログ章のカスタム`envoyFileAccessLog.logFormat.labels` providerも対応する別方式です。

**解説:**

**JSON形式アクセスログ設定:**

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    # Enable Access Log
    accessLogFile: /dev/stdout

    # Output in JSON format
    accessLogEncoding: JSON

    # Define custom JSON format
    accessLogFormat: |
      {
        "log_type": "access",
        "start_time": "%START_TIME%",
        "method": "%REQ(:METHOD)%",
        "path": "%REQ_WITHOUT_QUERY(X-ENVOY-ORIGINAL-PATH?:PATH)%",
        "protocol": "%PROTOCOL%",
        "response_code": "%RESPONSE_CODE%",
        "response_flags": "%RESPONSE_FLAGS%",
        "bytes_received": "%BYTES_RECEIVED%",
        "bytes_sent": "%BYTES_SENT%",
        "duration": "%DURATION%",
        "upstream_service_time": "%RESP(X-ENVOY-UPSTREAM-SERVICE-TIME)%",
        "x_forwarded_for": "%REQ(X-FORWARDED-FOR)%",
        "user_agent": "%REQ(USER-AGENT)%",
        "request_id": "%REQ(X-REQUEST-ID)%",
        "authority": "%REQ(:AUTHORITY)%",
        "upstream_host": "%UPSTREAM_HOST%",
        "upstream_cluster": "%UPSTREAM_CLUSTER%",
        "upstream_local_address": "%UPSTREAM_LOCAL_ADDRESS%",
        "downstream_local_address": "%DOWNSTREAM_LOCAL_ADDRESS%",
        "downstream_remote_address": "%DOWNSTREAM_REMOTE_ADDRESS%",
        "requested_server_name": "%REQUESTED_SERVER_NAME%",
        "route_name": "%ROUTE_NAME%"
      }
```

**出力例:**

```json
{
  "log_type": "access",
  "start_time": "2025-01-20T10:30:00.123Z",
  "method": "GET",
  "path": "/api/users",
  "protocol": "HTTP/1.1",
  "response_code": 200,
  "response_flags": "-",
  "bytes_received": 0,
  "bytes_sent": 1234,
  "duration": 42,
  "upstream_service_time": "40",
  "x_forwarded_for": "192.168.1.100",
  "user_agent": "Mozilla/5.0",
  "request_id": "abc-123-def",
  "authority": "example.com",
  "upstream_host": "10.0.1.20:8080",
  "upstream_cluster": "outbound|8080||backend.default.svc.cluster.local",
  "upstream_local_address": "10.0.1.10:54321",
  "downstream_local_address": "10.0.1.10:8080",
  "downstream_remote_address": "10.0.1.5:12345",
  "requested_server_name": "-",
  "route_name": "default"
}
```

**名前空間ごとの設定:**

この代替方法では先にログ章のように`mesh-json`を定義します。Telemetryはprovider/範囲を選び、それ自体がprovider形式を変えるわけではありません。

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: access-logging
  namespace: production
spec:
  accessLogging:
  - providers:
    - name: mesh-json
    # Select the already-defined JSON provider
```

**Envoyの形式変数:**

```text
# Key variables:
%START_TIME%: Request start time
%REQ(HEADER)%: Request header
%RESP(HEADER)%: Response header
%RESPONSE_CODE%: HTTP response code
%DURATION%: Total duration (ms)
%BYTES_RECEIVED%: Bytes received
%BYTES_SENT%: Bytes sent
%UPSTREAM_HOST%: Upstream server address
%DOWNSTREAM_REMOTE_ADDRESS%: Client address
```

**CloudWatch Logs統合:**

これは一致する入力タグ、CRI/JSON解析、IAM認証情報、ログマウントを持つデプロイ済みFluent Bitエージェントの出力断片だけです。ConfigMap単体ではログは収集されません。EKS Fargateには対応ログルーター設定が必要です。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: istio-system
data:
  output.conf: |
    [OUTPUT]
        Name cloudwatch_logs
        Match *
        region us-east-1
        log_group_name /aws/eks/istio/access-logs
        log_stream_prefix istio-
        auto_create_group true
```

**ログの確認:**

```bash
# Check Pod's Access Log
kubectl logs <pod-name> -c istio-proxy

# Real-time monitoring
kubectl logs -f <pod-name> -c istio-proxy | jq -R 'fromjson?'

# Filter specific response codes
kubectl logs <pod-name> -c istio-proxy | \
  jq -R 'fromjson? | select((.response_code | tonumber?) == 500)'
```

**TEXT形式とJSON形式の比較:**

| 項目 | TEXT | JSON |
| --------------- | ------------ | --------------- |
| **読みやすさ** | 高い（人間） | 低い（人間） |
| **解析** | 難しい | 容易（機械） |
| **サイズ** | 小さい | 大きい |
| **構造** | 非構造化 | 構造化 |
| **クエリ** | 難しい | 容易（jqなど） |

**TEXT形式の例:**

```
[2025-01-20T10:30:00.123Z] "GET /api/users HTTP/1.1" 200 - "-" "-" 0 1234 42 40 "192.168.1.100" "Mozilla/5.0" "abc-123-def" "example.com" "10.0.1.20:8080" outbound|8080||backend.default.svc.cluster.local 10.0.1.10:54321 10.0.1.10:8080 10.0.1.5:12345 - default
```

**参考資料:**

* [ログ記録](../../../service-mesh/istio/observability/03-logging.md)
* [Envoyアクセスログ形式](https://www.envoyproxy.io/docs/envoy/latest/configuration/observability/access_log/usage)

</details>

***

### 問5: Grafanaダッシュボード

Istioが公開するGrafanaダッシュボード群に**含まれない**ものはどれですか？

A. Istio Service Dashboard\
B. Istio Workload Dashboard\
C. Istio Performance Dashboard\
D. Istio Cost Dashboard

<details>

<summary>解答を表示</summary>

**正解: D**

D。Istioは通信/コントロールプレーンのダッシュボードを公開しますが、Grafana自体は別アドオンです。Istioインストールで自動導入されません。

**解説:**

1.31カタログにはService7636、Workload7630、Mesh7639、Performance11829、Control Plane7645、Wasm13277、Ztunnel21306があります。Performanceはリソース/データ使用に重点を置き、xDS/Webhookパネルは主にControl Planeです。Meshには全体通信とコンポーネント版がありますが、以前ここに列挙した全レイテンシーパネルはありません。インストールしたIstioリリースに合うリビジョンを選びます。

`istio_requests_total`にGB転送料を掛けても費用は計算できません。リクエストはバイトではなく、`source_cluster`/`destination_cluster`はAZでなくクラスターを識別します。プロキシメモリは使用量で、請求ではありません。ネットワーク費用には課金対象バイト測定と実送信元/宛先位置・サービス規則、リソース配賦にはノード価格、時間、明示配賦モデルが必要です。固定式を断言せず、AWS請求/CURデータと該当料金で見積もりを照合します。

検証済みカタログリビジョンと完全なカスタムJSON/プロビジョニング例は[ダッシュボードの章](../../../service-mesh/istio/observability/04-dashboards.md)を使います。ConfigMapとラベルだけではローダーはインストールされず、データソース入力も解決しません。

</details>

***

## 短答問題（6-10）

### 問6: ゴールデンシグナル監視

IstioとPrometheusでGoogle SREの**ゴールデンシグナル**（レイテンシー、トラフィック、エラー、飽和）を監視する方法を説明してください。各シグナルの**Prometheusクエリ**と**アラートルール**を含めてください。

<details>

<summary>解答を表示</summary>

サービスホップ計算ごとにreporterを1つ使い、サービス名前空間（必要ならクラスターも）を保持します。destinationメトリクスはサービスが受信した要求を測り、届かなかった上流失敗にはsourceメトリクスが必要です。HTTP5xxはエラー定義の1つにすぎません。gRPC失敗には`grpc_response_status`とアプリ固有SLIルールが必要です。以下のレイテンシーはミリ秒、rateは毎秒です。

```promql
histogram_quantile(0.95, sum by (destination_service_name, destination_service_namespace, le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination"}[5m])))

histogram_quantile(0.99, sum by (destination_service_name, destination_service_namespace, le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination"}[5m])))

sum by (destination_service_name, destination_service_namespace) (rate(istio_requests_total{reporter="destination"}[5m]))

sum by (destination_service_name, destination_service_namespace) (rate(istio_requests_total{reporter="destination",response_code=~"5.."}[5m])) / sum by (destination_service_name, destination_service_namespace) (rate(istio_requests_total{reporter="destination"}[5m]))
```

単一クラスターの従来サイドカーデプロイでは、使用量/limit比率にkubelet/cAdvisorとkube-state-metricsが必要です。欠損/ゼロlimitを除外します。ネイティブサイドカーは宣言limitをinitコンテナリソース系列に報告する場合があるため、式を使う前に実メトリクスファミリーを確認してください。

```promql
sum by (namespace, pod, container) (rate(container_cpu_usage_seconds_total{container="istio-proxy"}[5m])) / on (namespace, pod, container) (max by (namespace, pod, container) (kube_pod_container_resource_limits{container="istio-proxy",resource="cpu",unit="core"}) > 0)

max by (namespace, pod, container) (container_memory_working_set_bytes{container="istio-proxy"}) / on (namespace, pod, container) (max by (namespace, pod, container) (kube_pod_container_resource_limits{container="istio-proxy",resource="memory",unit="byte"}) > 0)

envoy_cluster_upstream_cx_active
envoy_cluster_upstream_rq_pending_active
envoy_cluster_circuit_breakers_default_cx_open
```

`_cx_open`は0/1状態ゲージで、アクティブ接続を割っても使用率にはなりません。容量比率が必要なら設定済みサーキットブレーカーしきい値を確認します。割る前のCPU rateはコア、メモリワーキングセットはバイトです。メソッド別内訳には、値を制限した`request_method` Telemetryラベルを先に追加します。

以下のPrometheusRuleはインストール済みPrometheus Operatorが選択する必要があります。しきい値と比較期間は例示です。通信の季節性、no-data、スクレイプ失敗、最小量条件には環境固有対応が必要です。直前1時間の窓は学習された正常基準ではありません。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: istio-golden-signals
  namespace: monitoring
spec:
  groups:
  - name: golden-signals
    rules:
    - alert: HighLatency
      expr: histogram_quantile(0.95, sum by (destination_service_name, destination_service_namespace,
        le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination"}[5m]))) > 500
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: P95 request duration exceeds500ms
    - alert: TrafficSpike
      expr: sum by (destination_service_name, destination_service_namespace) (rate(istio_requests_total{reporter="destination"}[5m]))
        > 2 * sum by (destination_service_name, destination_service_namespace) (rate(istio_requests_total{reporter="destination"}[1h]
        offset 1h))
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Traffic exceeds the previous comparison window
    - alert: HighErrorRate
      expr: sum by (destination_service_name, destination_service_namespace) (rate(istio_requests_total{reporter="destination",response_code=~"5.."}[5m]))
        / sum by (destination_service_name, destination_service_namespace) (rate(istio_requests_total{reporter="destination"}[5m]))
        > 0.01
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: HTTP5xx fraction exceeds1%
    - alert: HighEnvoyCPU
      expr: sum by (namespace, pod, container) (rate(container_cpu_usage_seconds_total{container="istio-proxy"}[5m]))
        / on (namespace, pod, container) (max by (namespace, pod, container) (kube_pod_container_resource_limits{container="istio-proxy",resource="cpu",unit="core"})
        > 0) > 0.8
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Proxy CPU consumption exceeds80% of its configured limit
    - alert: HighEnvoyMemory
      expr: max by (namespace, pod, container) (container_memory_working_set_bytes{container="istio-proxy"})
        / on (namespace, pod, container) (max by (namespace, pod, container) (kube_pod_container_resource_limits{container="istio-proxy",resource="memory",unit="byte"})
        > 0) > 0.8
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Proxy working set exceeds80% of its configured limit
    - alert: ConnectionBreakerAtCapacity
      expr: envoy_cluster_circuit_breakers_default_cx_open == 1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Connection breaker at capacity
```

[確認済みダッシュボードテンプレート](../../../service-mesh/istio/observability/04-dashboards.md)で、リクエストレート、エラー割合、レイテンシー、リソース単位ごとに別パネルを作成します。CPUコアとメモリバイトを単位表示のない同じ尺度に置かないでください。

</details>

***

### 問7: Jaegerによる性能ボトルネックの発見

分散トレースツールJaegerでマイクロサービス構成の**性能ボトルネック**を見つける方法を説明してください。**トレース分析手法**と**実践的なデバッグシナリオ**を含めてください。

<details>

<summary>解答を表示</summary>

[Jaeger2/OTLPトレース設定](../../../service-mesh/istio/observability/02-tracing.md)、設定済みTelemetry provider、アプリのコンテキスト伝播から始めます。旧Jaegerアドオン/Zipkinポートやサンプリング値だけでトレースが導入されると想定しないでください。アプリ/DBスパンにはSDKかエージェント計装が必要です。プロキシスパンからDBクエリ内部は分かりません。

1. 名前空間に限定したPrometheusレイテンシークエリで対象サービス/時間帯を特定し、Jaegerで代表的な遅い/通常トレースを探します。Prometheusヒストグラムクエリは集計統計を返し、トレースIDは返しません。
2. クリティカルパスを追い、親の所要時間と自身だけの時間を区別します。長い親には子が含まれ、自動的に原因とはなりません。
3. エラー、再試行、接続待ち、クエリ実行、並列性を比較します。トレース時刻、サンプリング、欠損スパンが結論を制限します。

```promql
histogram_quantile(0.99, sum by (destination_service_name, destination_service_namespace, le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination"}[5m]))) > 2000
```

```bash
kubectl port-forward -n observability svc/jaeger-query 16686:16686
```

以下は仮定のデバッグシナリオで、ベンチマーク結果や実際のJaeger API応答ではありません。

| 観測 | 確認事項 | 適切な対応 |
|---|---|---|
|2.1sリクエスト内に1.8sの計装DB操作|プール待ち、クエリ時間、ロック、ネットワーク遅延を分け、DB実行計画を確認|実測原因を修正。`redis.conf`というConfigMapではアプリキャッシュは追加されない|
|接続プールタイムアウトを伴う約10sリクエスト|アプリDBクライアントプール、同時実行数、DB容量を確認|アプリ/DBプールを調整してリークを修正。Envoy DestinationRuleはアプリプールを設定せず、HTTPプール設定はPostgreSQLを調整しない|
|独立した2s+2s+1s呼び出しを順次実行|依存関係、負荷上限、トレースコンテキストを確認|実asyncクライアントか上限付きスレッドで独立I/Oだけを並列化。所要時間は最長呼び出し＋オーバーヘッドに近づき得るが2s保証ではない|

既存同期I/Oコールバック向けのPython3.9+断片は、戻り値の順序を保持してワーカースレッドを使います。アプリはコールバックを提供し、独自タイムアウトを適用する必要があります。待機タスクのキャンセルはすでに実行中のスレッドを止めません。

```python
import asyncio

async def get_user_data(user_id):
    # Application-owned synchronous I/O functions; each must enforce its timeout.
    profile, orders, recommendations = await asyncio.gather(
        asyncio.to_thread(call_backend_a, user_id),
        asyncio.to_thread(call_backend_b, user_id),
        asyncio.to_thread(call_backend_c, user_id),
    )
    return merge(profile, orders, recommendations)
```

タイムアウトは待ち時間を制限し、遅いDBを直しません。再試行は負荷を増幅し得ます。VirtualServiceタイムアウト例には実ルート宛先を含め、冪等性/負荷を考慮した場合だけ再試行を使います。永続的なJaeger依存マップには追加集約が必要な場合があります。単一トレースのウォーターフォールと全体依存マップは別の表示です。見栄えの良い1トレースだけでなく、反復通信とメトリクス/トレースで修正仮説を検証します。

</details>

***

### 問8: Kialiによるサービスメッシュのトラブルシューティング

KialiでIstioサービスメッシュの**よくある問題**（設定エラー、通信異常、セキュリティポリシー競合）を診断・解決する方法を説明してください。

<details>

<summary>解答を表示</summary>

Kialiの設定チェック、観測通信、Podログ、トレースを証拠に使い、実効プロキシ設定を検証します。ダッシュボード章に版/認証の前提条件があります。グラフの形から架空のKiali警告を作ったり、緑アイコンを実行時保証として扱ったりしないでください。

| 症状 | 正しい解釈と確認 |
|---|---|
|サービス/subsetがない|`default`内では`reviews`と`reviews.default.svc.cluster.local`は同じホストに解決。名前短縮で存在しないServiceは作られない。KIA1107は未定義subsetを示す。Service/EndpointSlice、DestinationRule、実Podラベルを確認|
|subsetラベル不一致|ラベル値`1.0`自体が誤りではない。意図するDeploymentラベルとsubsetを合わせる。完全DestinationRuleを書く際はメタデータ、host、文書区切りを含める|
|設定50/50に対し観測90/10|実効重み、一致ルール、接続アフィニティ、再試行、エンドポイント/除外状態、時間帯を確認。Readyレプリカが少ないだけでVirtualServiceのsubset重みは再定義されず、後の50/50分配も保証されない|
|A↔Bの循環|双方向グラフは再帰呼び出し、デッドロック、自動Kialiアラートの証明ではない。アプリ再設計前にトレースで実際の意図しない循環を特定|
|HTTP403|適用プロキシのポリシー、ID、応答詳細を調査。specが空のAuthorizationPolicyは一致ルールのないALLOWで、別ALLOWが例外を提供可能。優先するDENYではない|
|mTLS失敗|PeerAuthenticationは受信側を記述。特定方向の送信TLS設定、受信ポリシー、参加、証明書/信頼、ポートプロトコルを確認。受信モードの違いは自動的な競合ではない。一律STRICTは移行判断で、汎用修正ではない|

mTLSが指定フロントエンドprincipalを提供し、先行CUSTOM/DENYが拒否しない前提なら、範囲限定のデフォルト拒否とフロントエンド例外は有効です。

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-default-deny
  namespace: default
spec:
  selector:
    matchLabels:
      app: backend
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-allow-frontend
  namespace: default
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/default/sa/frontend
```

```bash
kubectl get service reviews -n default
kubectl get endpointslice -n default -l kubernetes.io/service-name=reviews
kubectl get pods -n default -l app=reviews --show-labels
istioctl analyze -n default
istioctl proxy-config clusters <source-pod> -n default --fqdn reviews.default.svc.cluster.local -o json
istioctl x authz check <backend-pod>.default
```

通信アニメーションは選択時間帯を要約し、バイト単位で正確なパケット検査ではありません。仮説が外れたら無条件でワークロードを再起動せず、診断/設定/テストを繰り返します。

![KialiでGraph表示を開き、症状を無通信、エラー、遅い応答、セキュリティ拒否に分類し、Istio設定、ログ、トレース、セキュリティポリシーを確認して設定を修正・テストし、未解決なら再診断するループ。](../../../.gitbook/assets/en-quizzes-service-mesh-istio-observability-1.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-quizzes-service-mesh-istio-observability-1.html)

</details>

***

### 問9: 本番可観測性スタックの設定

本番KubernetesクラスターでIstio可観測性スタック（Prometheus、Grafana、Jaeger、Kiali）を **高可用性（HA）** 構成でデプロイする方法を説明してください。**永続ストレージ**、**スケーリング**、**バックアップ**戦略を含めてください。

<details>

<summary>解答を表示</summary>

本番HAスタックは環境固有の設計・検証作業です。以下は主な要件で、本番テスト済みデプロイ一式ではありません。互換Kubernetes/Istio/Operator/チャート/バックエンド版を固定し、実際のチャートvaluesを確認し、ロールアウト前に障害/復元動作を検証します。[ダッシュボードの章](../../../service-mesh/istio/observability/04-dashboards.md)に現在のKiali互換性の不足を記録しています。最新リリースだから互換と推測しないでください。

| コンポーネント | 状態とHA要件 |
|---|---|
|Prometheus|独立レプリカを各PVCで動かし、同一クラスターのレプリカ間でclusterラベルを共有し、replicaラベルを分ける（重複排除には他ラベルの一致が必要）。障害ドメインを分散し、実取り込み量に合わせて保持を設定。ロードバランサーは履歴を統合しない|
|Thanos|サイドカーがStoreAPIを公開し、任意でブロックをアップロード。Queryは実StoreAPIエンドポイントを検出し設定replicaラベルで重複排除。Store Gatewayはオブジェクトストレージを読み、Compactorは適切な単一書き込み/シャード所有権でブロック圧縮・保持を処理|
|Grafana|2レプリカには共有HA PostgreSQL/MySQL、整合したプロビジョニング/プラグイン/シークレット設定、ロードバランサーが必要。SQLite共有や、ノードをまたいで1つのEBS ReadWriteOnceを共有する2レプリカはGrafana HAではない|
|Alertmanager|ピア/通知重複排除設定、永続状態、保護したreceiver認証情報が必要。チャートvaluesにSlack webhookを置くだけでは完全なシークレット/通知設計ではない|
|Jaeger2/collector|対応永続バックエンドとそのHA/TLS/認証情報を使い、ステートレスquery/collectorレプリカを配置。テールサンプラーにはトレースIDアフィニティが必要。ランダムService背後の複数レプリカには完全トレースが届かない|
|Kiali|互換Operator/サーバー、共有設定/セッションシークレット動作、適切なPod配置を使用。バックエンドAPIとユーザー名前空間権限を保護。token方式は単一クラスター用で、必要なら文書化されたマルチクラスター認証を選ぶ|

**ストレージとオブジェクトストアの接続**:

- オブジェクトストレージがあってもローカルPrometheus永続化を維持します。最近のhead/WALデータは未アップロードかもしれません。サイドカーアップロードでは使用Thanos版のローカルコンパクション/ブロック期間要件に従います。
- S3バケット、リージョンエンドポイント、暗号化、保持、IAM権限が存在する必要があります。実際にsidecar/Store/Compactorを動かすPodに認証情報を持つServiceAccountを結び付けます。「IRSA」と書いたYAMLコメントは認証情報を作りません。現Thanos S3設定は、対応AWS SDK認証情報チェーンで`aws_sdk_auth: true`を使えます。
- 現kube-prometheus-stackでは、既存オブジェクトストアSecretを`prometheus.prometheusSpec.thanos.objectStorageConfig.existingSecret`で実名/キー指定します。キー`thanos.yaml`をマウントしても`objstore.yaml`というファイルは作られません。ファイルパス、名前付きgRPC Serviceポート、DNS-SRV対象を確認します。
- 現Thanos Queryはエンドポイント/重複排除設定に`--endpoint`と`--query.replica-label`を使います。選択リリースを確認せず旧`--store`例を引き継がないでください。Prometheus互換バックエンドを照会するKialiには文書化された`thanos_proxy`設定も必要な場合があります。
- 各Deployment/StatefulSetには一致セレクター/PodラベルとServiceが必要です。元の不完全リソースでは動作するStoreAPI構成になりませんでした。EKSのEBS状態には対応EC2配置/CSI設定が必要で、FargateはEBSマウントも任意DaemonSet実行もしません。

**設定、バックアップ、証明**:

1. 実monitor/ruleセレクターとスクレイプ対象を設定します。kube-prometheus-stackで`alertmanager.config`は`alertmanager.alertmanagerSpec`と同階層です。固定チャートのスキーマを確認します。パスワード/webhookは対応Secret参照に保持します。
2. GrafanaのDB/設定/プロビジョニング済みダッシュボード/プラグイン、必要なPrometheus状態、Jaegerストレージをアプリ整合性のある手順でバックアップします。オブジェクトストア保持だけでは全コンポーネントの復元戦略ではありません。
3. Velero PVC/PVマニフェストだけではボリュームデータ取得は証明されません。対応CSIスナップショット/データムーバーかファイルシステムバックアップ経路、snapshot class/プラグイン、認証情報、復元に必要なリソースを設定します。状態を確認し、隔離復元を実施します。
4. バックアップJobには必要ツールを含むテスト済みイメージ、正しいソースURL、範囲限定ID、送信先バケット、失敗処理が必要です。旧AWS CLIイメージ/想定curl+jq/S3 CronJobは検証済みバックアップ解決策ではありませんでした。
5. receiver/exporter失敗、キュー待ち、スクレイプ健全性、実PVC容量メトリクスを監視します。`prometheus_tsdb_storage_blocks_bytes_total`は有効な容量分母ではありません。スタックは自身の全停止を確実には報告できません。独立したハートビート/観測者を使い、欠損系列/no-dataを`up == 0`と分けて扱います。
6. レプリカ/ノード/ゾーン喪失、ストレージ中断、バックエンド/認証失敗、ロールアウト、復元をテストします。PDBは計画中断を助けますが、DBやゾーンレベルHAを作りません。レプリカ数から断言せず、RPO/RTOと観測容量を記録します。

[Grafana HA](https://grafana.com/docs/grafana/latest/setup-grafana/set-up-for-high-availability/)、[Thanos Sidecar](https://thanos.io/tip/components/sidecar.md/)、[Thanos Query](https://thanos.io/tip/components/query.md/)、[Thanosストレージ](https://thanos.io/tip/thanos/storage.md/)、[Velero CSIバックアップ](https://velero.io/docs/main/csi/)を参照してください。

</details>

***

### 問10: カスタムメトリクスとダッシュボードの作成

Istio Envoyのデフォルトメトリクスに加え、**業務メトリクス**（注文数、決済成功率など）を収集し、Grafanaカスタムダッシュボードを作成する方法を説明してください。

<details>

<summary>解答を表示</summary>

メトリクス選択前に業務イベントと計数境界を定義します。Envoyが把握するのはリクエストで、注文の永続作成や決済確定ではありません。以下の**統合断片は完了した処理試行を数え**、一意注文数や会計売上は数えません。アプリは処理関数/エラー契約、冪等性、検証を提供する必要があります。真の決済成功メトリクスには決済境界で結果を計装し、結果カウンターから比率を導出します。更新されないGaugeは成功率ではありません。

値が限定されたカテゴリ/状態ラベル、試行のCounter、非負金額/所要時間のHistogramを使います。失敗も含めるため`finally`で所要時間を観測します。注文ID、ユーザーID、生URLをラベルにしないでください。例は単一プロセスで、複数ワーカー集約にはクライアントライブラリがサポートする設定が必要です。

**Python/Flask**（アプリが`process_order`と`PaymentException`を提供）:

```python
from flask import Flask, request, jsonify, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time

# Integration fragment: your application supplies process_order and PaymentException.
# process_order returns a validated nonnegative USD amount and category after processing.
app = Flask(__name__)
CATEGORIES = {"books", "electronics", "other"}
STATUSES = ("success", "payment_failed", "error")
orders_total = Counter("orders_total", "Completed order-processing attempts", ["status", "product_category"])
order_amount = Histogram("order_amount_dollars", "Observed amounts of successful attempts in USD",
                         buckets=[10, 50, 100, 500, 1000, 5000])
order_duration = Histogram("order_processing_duration_seconds", "Order attempt duration, including failures",
                           buckets=[0.1, 0.5, 1.0, 2.0, 5.0])
for status in STATUSES:
    for category in CATEGORIES:
        orders_total.labels(status=status, product_category=category).inc(0)

@app.post("/api/orders")
def create_order():
    payload = request.get_json()
    started = time.perf_counter()
    try:
        order = process_order(payload)
        category = order["category"] if order["category"] in CATEGORIES else "other"
        orders_total.labels(status="success", product_category=category).inc()
        order_amount.observe(order["amount"])
        return jsonify(order), 201
    except PaymentException:
        orders_total.labels(status="payment_failed", product_category="other").inc()
        return jsonify({"error": "Payment failed"}), 400
    except Exception:
        orders_total.labels(status="error", product_category="other").inc()
        return jsonify({"error": "Order processing failed"}), 500
    finally:
        order_duration.observe(time.perf_counter() - started)

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), content_type=CONTENT_TYPE_LATEST)

# Use the application's server lifecycle. Do not treat a Flask development server
# or process-local counters as a production accounting system.
```

**Node.js/Express**: 保守中パッケージは`@prometheus-io/client`です（例のAPIはNode 22で0.16.1を確認）。`prom-client`はこれに代わって非推奨となっており、既存プロジェクトは移行変更履歴を確認します。JSONミドルウェアを設定し、`register.metrics()`をawaitします。

```javascript
const express = require('express');
const client = require('@prometheus-io/client'); // Example verified with 0.16.1, Node 22
const app = express();
app.use(express.json());
const register = new client.Registry();
const categories = new Set(['books', 'electronics', 'other']);
const ordersTotal = new client.Counter({
  name: 'orders_total', help: 'Completed order-processing attempts',
  labelNames: ['status', 'product_category'], registers: [register]
});
const orderAmount = new client.Histogram({
  name: 'order_amount_dollars', help: 'Observed successful attempt amounts in USD',
  buckets: [10, 50, 100, 500, 1000, 5000], registers: [register]
});
const orderDuration = new client.Histogram({
  name: 'order_processing_duration_seconds', help: 'Order attempt duration, including failures',
  buckets: [0.1, 0.5, 1, 2, 5], registers: [register]
});
for (const status of ['success', 'payment_failed', 'error']) {
  for (const product_category of categories) ordersTotal.inc({status, product_category}, 0);
}
// The application supplies async processOrder with validated amount/category output.
app.post('/api/orders', async (req, res) => {
  const end = orderDuration.startTimer();
  try {
    const order = await processOrder(req.body);
    const product_category = categories.has(order.category) ? order.category : 'other';
    ordersTotal.inc({status: 'success', product_category});
    orderAmount.observe(order.amount);
    res.status(201).json(order);
  } catch (error) {
    const status = error.code === 'PAYMENT_FAILED' ? 'payment_failed' : 'error';
    ordersTotal.inc({status, product_category: 'other'});
    res.status(status === 'payment_failed' ? 400 : 500).json({error: 'Order processing failed'});
  } finally {
    end();
  }
});
app.get('/metrics', async (req, res) => {
  try {
    res.set('Content-Type', register.contentType);
    res.end(await register.metrics());
  } catch (error) {
    res.status(500).end();
  }
});
// Integrate app.listen/shutdown with the application's server lifecycle.
```

**Kubernetesでの収集**: このサイドカー演習はIstioの統合エンドポイントを使い、平文アプリスクレイプがSTRICT mTLSを通ると想定しません。`default`の実`order-service` Deploymentへラベル/アノテーションをマージします。イメージにアプリを含め、8080で`/metrics`を公開する必要があります。メッシュでPrometheus統合を有効にします。エージェントエンドポイント15020は平文なのでアクセスを制限します。既存スクレイパーがこの業務メトリクスを集める場合、重複monitorを追加しないでください。

```yaml
spec:
  template:
    metadata:
      labels:
        app: order-service
      annotations:
        prometheus.io/scrape: 'true'
        prometheus.io/path: /metrics
        prometheus.io/port: '8080'
        prometheus.istio.io/merge-metrics: 'true'
```

```yaml
apiVersion: v1
kind: Service
metadata:
  name: order-service
  namespace: default
  labels:
    app: order-service
spec:
  selector:
    app: order-service
  ports:
  - name: http
    port: 8080
    targetPort: 8080
  - name: merged-metrics
    port: 15020
    targetPort: 15020
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: order-service-metrics
  namespace: istio-system
spec:
  namespaceSelector:
    matchNames:
    - default
  selector:
    matchLabels:
      app: order-service
  targetLabels:
  - app
  endpoints:
  - port: merged-metrics
    path: /stats/prometheus
    interval: 30s
    metricRelabelings:
    - sourceLabels:
      - __name__
      regex: orders_total|order_amount_dollars_(bucket|sum|count)|order_processing_duration_seconds_(bucket|sum|count)
      action: keep
```

Prometheusリソースは`istio-system`のServiceMonitorを選ぶ必要があり、それが`default`のServiceを検出します。業務メトリクスファミリーだけを保持することで、他で収集済みのプロキシメトリクス重複を避けます。`targetLabels`はServiceの`app`ラベルを明示追加します。サイドカー例であり、ambient/直接TLSスクレイプには別の対応設計が必要です。

**クエリ**（順に、期間試行数、毎秒試行数、成功割合、観測金額P95、所要時間P99、カテゴリ別レート、注文試行中の決済失敗割合）:

```promql
sum(increase(orders_total{namespace="default",app="order-service"}[5m]))

sum(rate(orders_total{namespace="default",app="order-service"}[5m]))

sum(rate(orders_total{namespace="default",app="order-service",status="success"}[5m])) / sum(rate(orders_total{namespace="default",app="order-service"}[5m]))

histogram_quantile(0.95, sum by (le) (rate(order_amount_dollars_bucket{namespace="default",app="order-service"}[5m])))

histogram_quantile(0.99, sum by (le) (rate(order_processing_duration_seconds_bucket{namespace="default",app="order-service"}[5m])))

sum by (product_category) (rate(orders_total{namespace="default",app="order-service"}[5m]))

sum(rate(orders_total{namespace="default",app="order-service",status="payment_failed"}[5m])) / sum(rate(orders_total{namespace="default",app="order-service"}[5m]))
```

`increase`は期間合計を推定し、`rate`は毎秒です。プロセス再起動、再試行、スクレイプ欠損があるため、運用カウンター/金額合計は会計台帳ではありません。一意のコミット済み注文や売上にはテレメトリーをexactly-onceと想定せず、永続業務システムと照合します。

**Grafana**: この完全ダッシュボードオブジェクトはデータソースUID `prometheus`と上のmonitorのラベルを期待します。APIラッパーなしで保存し、[文書化されたダッシュボードファイルのプロビジョニング](../../../service-mesh/istio/observability/04-dashboards.md)を使います。ConfigMapラベルだけではproviderは設定されません。

```json
{
  "uid": "order-business-metrics",
  "title": "Order Processing Operational Metrics",
  "timezone": "browser",
  "panels": [
    {
      "id": 1,
      "title": "Completed Attempts per Minute",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "sum(rate(orders_total{namespace=\"default\",app=\"order-service\"}[5m])) * 60",
          "refId": "A"
        }
      ],
      "gridPos": {
        "x": 0,
        "y": 0,
        "w": 12,
        "h": 8
      }
    },
    {
      "id": 2,
      "title": "Attempt Success Fraction",
      "type": "gauge",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "sum(rate(orders_total{namespace=\"default\",app=\"order-service\",status=\"success\"}[5m])) / sum(rate(orders_total{namespace=\"default\",app=\"order-service\"}[5m]))",
          "refId": "A"
        }
      ],
      "gridPos": {
        "x": 12,
        "y": 0,
        "w": 12,
        "h": 8
      },
      "fieldConfig": {
        "defaults": {
          "unit": "percentunit"
        }
      }
    },
    {
      "id": 3,
      "title": "Processing P95",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "histogram_quantile(0.95, sum by (le) (rate(order_processing_duration_seconds_bucket{namespace=\"default\",app=\"order-service\"}[5m])))",
          "refId": "A"
        }
      ],
      "gridPos": {
        "x": 0,
        "y": 8,
        "w": 12,
        "h": 8
      },
      "fieldConfig": {
        "defaults": {
          "unit": "s"
        }
      }
    },
    {
      "id": 4,
      "title": "Observed Successful Attempt Amount (Last Hour)",
      "type": "stat",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "sum(increase(order_amount_dollars_sum{namespace=\"default\",app=\"order-service\"}[1h]))",
          "refId": "A"
        }
      ],
      "gridPos": {
        "x": 12,
        "y": 8,
        "w": 12,
        "h": 8
      },
      "fieldConfig": {
        "defaults": {
          "unit": "currencyUSD"
        }
      }
    }
  ],
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "refresh": "30s"
}
```

**アラート**: インストール済みPrometheus Operatorでこのルールを選びます。最小通信しきい値は無通信時の比率アラートを避けますが、欠損/スクレイプ失敗は別シグナルが必要です。しきい値は例で、業務SLO保証ではありません。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: business-metrics-alerts
  namespace: istio-system
spec:
  groups:
  - name: business-metrics
    rules:
    - alert: LowOrderAttemptSuccessFraction
      expr: (sum(rate(orders_total{namespace="default",app="order-service",status="success"}[5m])) / sum(rate(orders_total{namespace="default",app="order-service"}[5m]))
        < 0.95) and (sum(rate(orders_total{namespace="default",app="order-service"}[5m])) > 0.1)
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Order-processing attempt success fraction below95%
    - alert: SlowOrderProcessing
      expr: histogram_quantile(0.95, sum by (le) (rate(order_processing_duration_seconds_bucket{namespace="default",app="order-service"}[5m])))
        > 2
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: P95 processing attempt duration exceeds2s
```

メトリクスタイプ、公開、プロセスモデルは[Pythonクライアント](https://prometheus.github.io/client_python/)と[JavaScriptクライアント](https://github.com/prometheus/client_js)の文書を参照してください。

</details>

***

## 得点計算

* 選択問題1-5: 各10点（計50点）
* 短答問題6-10: 各10点（計50点）
* **合計: 100点**

**評価基準:**

* 90-100点: これらのトピックを非常によく理解
* 80-89点: よく理解。デプロイ検証は別途必要
* 70-79点: 平均的（追加学習を推奨）
* 60-69点: 平均未満（基本概念の復習が必要）
* 0-59点: 再学習が必要

## 学習資料

* [メトリクス](../../../service-mesh/istio/observability/01-metrics.md)
* [分散トレーシング](../../../service-mesh/istio/observability/02-tracing.md)
* [ログ記録](../../../service-mesh/istio/observability/03-logging.md)
* [可視化](../../../service-mesh/istio/observability/04-dashboards.md)
