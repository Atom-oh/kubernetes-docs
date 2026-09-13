# Linkerd可観測性

> **最終更新**: September 11, 2026 · Linkerd edge-26.9.1 / charts 2026.9.1 · Prometheus Operator例は0.93.1で確認

Linkerdはproxy/protocolメトリクスを公開し、VizがPrometheus、metrics-api、tap、tap-injector、web dashboardを追加します。現VizチャートはGrafanaを導入**しません**。分散トレースには設定collector/backend、コンテキスト、サンプリングも必要で、metrics dashboard導入だけでは有効になりません。

[導入ガイド](01-installation.md)と`my-app`内の既存メッシュ`web`/`api`および実通信を前提とします。実名前空間、workload/Service名、port、IDを設定します。opaque TCP DBはHTTP成功/遅延を自動生成しません。

## メトリクスの意味

| メトリクス | 意味 |
|---|---|
| response_total | error/stream終了処理を含む最終応答分類 |
| request_total | 観測要求。業務成功数ではない |
| response_latency_ms_bucket | 最初のバイトまでの時間、ミリ秒ヒストグラム |
| tcp_open_connections | 現在開いている転送接続 |
| tcp_open_total | 累積開始接続で、現在active数ではない |

代表的serviceメトリクスは成功率、要求レート、遅延です。必要なら容量/飽和、アプリ、Kubernetesを追加します。HTTP既定分類はserver errorを失敗とし、400は成功に数えられ得ます。gRPC statusと応答policyで分類は変わり、自動的な業務成功SLIではありません。

遅延は応答stream全体ではありません。リリースproxyは最初の利用可能body frameで、body破棄時はfallbackで、最終分類と独立して記録します。ヒストグラムと応答counterは別時刻に利用可能となり得ます。success/failureラベルを公開しないヒストグラムに適用しないでください。

### CLI統計とライブ確認

```bash
linkerd viz stat deploy -n my-app
linkerd viz stat deploy/web -n my-app --to deploy/api
linkerd viz stat deploy/api -n my-app --from deploy/web
linkerd viz stat pods -n my-app
linkerd viz stat namespaces
linkerd viz stat deploy -n my-app --time-window 10m -o wide
linkerd viz stat deploy -n my-app -o json
```

表はMESHED、SUCCESS、RPS、遅延分位数、TCP_CONNを含みます。wideは転送byte rateを加え、proxy版一覧ではありません。Pod/DeploymentとServiceは観測点が異なり、Service統計は送信client metricsで未参加callerを省きます。合計比較時に区別します。

```bash
linkerd viz top deploy/web -n my-app --hide-sources=false
linkerd viz tap deploy/web -n my-app --method GET --path /api
linkerd viz tap deploy/web -n my-app --to deploy/api --max-rps 20
linkerd viz tap deploy/web -n my-app -o json
linkerd viz edges deploy -n my-app
linkerd viz edges pods -n my-app
```

`top`はtapしたライブ通信の要約です。`--hide-sources=false`はsource列でHTTPヘッダーではありません。`tap --path`はpath前方一致、`--max-rps`はtap要求レート上限でアプリ総要求数ではありません。現tapに`--from`と`--show-headers`はありません。source workloadに`--to`を使うか対応stat filterを使います。

Tapはサンプル/制限付き観測で、packet captureや完全監査ではありません。path/metadataが機密になり得るためAPIアクセスを制限します。edgeは観測接続で、空表示は無通信や普遍的暗号化の証明ではありません。

## Vizダッシュボードとストレージ

```bash
linkerd viz dashboard --address 127.0.0.1 --port 8084 --show url
```

表示されたlocal URLを開きます。loopbackにbindし、外部公開は独自認証/アクセス設計が必要です。bind addressやHost確認はユーザー認証ではありません。

![namespace/workload表示からPod、route metrics、topology、Tapへの論理移動。データは実通信/設定policyに依存し、現全メニューの画像ではない。](../../.gitbook/assets/en-service-mesh-linkerd-05-observability-1.png)

[インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-linkerd-05-observability-1.html)

既定同梱Prometheusは6時間保持と一時保存です。チャートは独自imageを固定するため、黙って新メジャーへ置換しません。永続化は導入ガイドで設定でき、長期/HAは別設計です。

```bash
kubectl -n linkerd-viz port-forward --address 127.0.0.1 svc/prometheus 9090:9090
# In another terminal:
curl --fail --get --data-urlencode 'query=up{job="linkerd-proxy"}' \
  http://127.0.0.1:9090/api/v1/query
```

## 外部Prometheus

直接scrape、federation、適切なremote-writeを意図的に選びます。重複排除なしで同系列を複数経路収集すると二重計上になります。

### 直接スクレイプ設定

既存Prometheusへマージします。選択Vizのjob/label対応に従い、controller targetにnamespace/Podを明示追加します。

```yaml
scrape_configs:
- job_name: linkerd-controller
  kubernetes_sd_configs:
  - role: pod
    namespaces:
      names:
      - linkerd
      - linkerd-viz
  relabel_configs:
  - source_labels:
    - __meta_kubernetes_pod_container_port_name
    action: keep
    regex: .*admin$
  - source_labels:
    - __meta_kubernetes_pod_container_port_name
    action: drop
    regex: linkerd-admin
  - source_labels:
    - __meta_kubernetes_pod_container_name
    action: replace
    target_label: component
  - source_labels:
    - __meta_kubernetes_namespace
    target_label: namespace
  - source_labels:
    - __meta_kubernetes_pod_name
    target_label: pod
- job_name: linkerd-proxy
  kubernetes_sd_configs:
  - role: pod
  relabel_configs:
  - source_labels:
    - __meta_kubernetes_pod_phase
    regex: (Pending|Running)
    action: keep
  - source_labels:
    - __meta_kubernetes_pod_container_name
    - __meta_kubernetes_pod_container_port_name
    - __meta_kubernetes_pod_label_linkerd_io_control_plane_ns
    action: keep
    regex: ^linkerd-proxy;linkerd-admin;linkerd$
  - source_labels:
    - __meta_kubernetes_namespace
    action: replace
    target_label: namespace
  - source_labels:
    - __meta_kubernetes_pod_name
    action: replace
    target_label: pod
  - source_labels:
    - __meta_kubernetes_pod_label_linkerd_io_proxy_job
    action: replace
    target_label: k8s_job
  - action: labeldrop
    regex: __meta_kubernetes_pod_label_linkerd_io_proxy_job
  - action: labelmap
    regex: __meta_kubernetes_pod_label_linkerd_io_proxy_(.+)
  - action: labeldrop
    regex: __meta_kubernetes_pod_label_linkerd_io_proxy_(.+)
  - action: labelmap
    regex: __meta_kubernetes_pod_label_linkerd_io_(.+)
  - action: labelmap
    regex: __meta_kubernetes_pod_label_(.+)
    replacement: __tmp_pod_label_$1
  - action: labelmap
    regex: __tmp_pod_label_linkerd_io_(.+)
    replacement: __tmp_pod_label_$1
  - action: labeldrop
    regex: __tmp_pod_label_linkerd_io_(.+)
  - action: labelmap
    regex: __tmp_pod_label_(.+)
```

旧`admin-http`フィルターは`dest-admin`/`ident-admin`など現portを見逃しました。proxy filterは対象制御の`linkerd-proxy`/`linkerd-admin`を保持します。Pod検出はinitも含むため、`__meta_kubernetes_pod_container_init`がtrueだけで捨てないでください。既定native sidecarはそこにあります。

ラベルは示すworkload queryを支えます。追加Viz/dashboardが必要とするラベルを保持し、mappedアプリラベルのcardinality/機密性を確認します。検出RBAC、API、metrics port到達性を設定します。有効YAMLは検出/収集成功の証明ではありません。

### Prometheus Operatorによる代替

Prometheusは両monitorと名前空間を選ぶ必要があります。例は`release: monitoring`を受け入れるselector前提で、実導入に合わせます。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: linkerd-proxies
  namespace: monitoring
  labels:
    release: monitoring
spec:
  namespaceSelector:
    any: true
  selector:
    matchLabels:
      linkerd.io/control-plane-ns: linkerd
  podMetricsEndpoints:
  - port: linkerd-admin
    path: /metrics
    interval: 10s
    relabelings:
    - sourceLabels:
      - __meta_kubernetes_pod_phase
      regex: (Pending|Running)
      action: keep
    - sourceLabels:
      - __meta_kubernetes_pod_container_name
      - __meta_kubernetes_pod_container_port_name
      - __meta_kubernetes_pod_label_linkerd_io_control_plane_ns
      action: keep
      regex: ^linkerd-proxy;linkerd-admin;linkerd$
    - sourceLabels:
      - __meta_kubernetes_namespace
      action: replace
      targetLabel: namespace
    - sourceLabels:
      - __meta_kubernetes_pod_name
      action: replace
      targetLabel: pod
    - sourceLabels:
      - __meta_kubernetes_pod_label_linkerd_io_proxy_job
      action: replace
      targetLabel: k8s_job
    - action: labeldrop
      regex: __meta_kubernetes_pod_label_linkerd_io_proxy_job
    - action: labelmap
      regex: __meta_kubernetes_pod_label_linkerd_io_proxy_(.+)
    - action: labeldrop
      regex: __meta_kubernetes_pod_label_linkerd_io_proxy_(.+)
    - action: labelmap
      regex: __meta_kubernetes_pod_label_linkerd_io_(.+)
    - action: labelmap
      regex: __meta_kubernetes_pod_label_(.+)
      replacement: __tmp_pod_label_$1
    - action: labelmap
      regex: __tmp_pod_label_linkerd_io_(.+)
      replacement: __tmp_pod_label_$1
    - action: labeldrop
      regex: __tmp_pod_label_linkerd_io_(.+)
    - action: labelmap
      regex: __tmp_pod_label_(.+)
    - targetLabel: job
      replacement: linkerd-proxy
---
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: linkerd-destination
  namespace: monitoring
  labels:
    release: monitoring
spec:
  namespaceSelector:
    matchNames:
    - linkerd
  selector:
    matchLabels:
      linkerd.io/control-plane-component: destination
  podMetricsEndpoints:
  - port: dest-admin
    path: /metrics
    interval: 10s
    relabelings:
    - sourceLabels:
      - __meta_kubernetes_pod_container_name
      targetLabel: component
    - targetLabel: job
      replacement: linkerd-controller
  - port: spval-admin
    path: /metrics
    interval: 10s
    relabelings:
    - sourceLabels:
      - __meta_kubernetes_pod_container_name
      targetLabel: component
    - targetLabel: job
      replacement: linkerd-controller
  - port: policy-admin
    path: /metrics
    interval: 10s
    relabelings:
    - sourceLabels:
      - __meta_kubernetes_pod_container_name
      targetLabel: component
    - targetLabel: job
      replacement: linkerd-controller
```

2つ目のPodMonitorは**destination Deployment**の3メトリクスendpointで、全controllerではありません。他componentは実宣言portを使います。

| コンポーネント | メトリクスポート名 |
|---|---|
| Identity | ident-admin |
| Proxy injector | injector-admin |
| Vizコンポーネント | admin |

destination Serviceに`admin-http`はなく、選択ServiceMonitorは検出できません。宣言container port用PodMonitorか適切なServiceを意図的に作ります。同targetへraw scrapeとPodMonitorを重複設定しないでください。

Federationも選択肢です。Viz PrometheusのService port名は**admin**、endpointは`/federate`です。exported labelを保持し意図jobを選び、callerメッシュServiceAccountをVizの`prometheus-admin` Serverで認可します。汎用`admin-http`例はこのチャートと不一致です。

### Vizから既存Prometheusを照会

必要Linkerdデータを保持し設定済みで到達可能なPrometheus向けです。

```yaml
prometheus:
  enabled: false
prometheusUrl: http://prometheus.monitoring.svc.cluster.local:9090
```

選択Vizの完全設定へvaluesをマージします。local Prometheus無効化前にquery API、scrape label、保持、認証/認可を検証します。URLはPrometheus導入やアクセス付与をしません。

## 範囲を明示したクエリ

受信API観測を1度選びます。namespace/deploymentを合わせ、共有backendはclusterを追加します。

成功率:

```promql
((sum(rate(response_total{namespace="my-app",deployment="api",direction="inbound",classification="success"}[5m])) or vector(0)) / sum(rate(response_total{namespace="my-app",deployment="api",direction="inbound"}[5m])))
and on() (sum(rate(response_total{namespace="my-app",deployment="api",direction="inbound"}[5m])) > 0)
```

全観測応答が失敗しsuccess系列がない場合は分子を0へfallbackします。正の合計条件により欠損/idleは成功結果なしとなり、欠損を100%と表示しません。

要求レート:

```promql
sum(rate(request_total{namespace="my-app",deployment="api",direction="inbound"}[5m]))
```

最初のバイトまでの分位数（ミリ秒）:

```promql
histogram_quantile(0.5, sum by (le) (rate(response_latency_ms_bucket{namespace="my-app",deployment="api",direction="inbound"}[5m])))

histogram_quantile(0.95, sum by (le) (rate(response_latency_ms_bucket{namespace="my-app",deployment="api",direction="inbound"}[5m])))

histogram_quantile(0.99, sum by (le) (rate(response_latency_ms_bucket{namespace="my-app",deployment="api",direction="inbound"}[5m])))
```

受信の送信元側active TCP接続:

```promql
sum(tcp_open_connections{namespace="my-app",deployment="api",direction="inbound",peer="src"})
```

`peer="src"`でproxyの別ローカルアプリ接続を含めるのを避けます。毎秒開始接続には同じ範囲の`tcp_open_total`へrateを適用します。

request_totalに汎用`retry="true"`はありません。ServiceProfileはroute_actual_request_total、route_request_total、route_retryable_totalを同範囲/窓で調べます。retryable応答と実送信再試行は別で、no-budget系列は部分集合です。現policyメトリクスとアプリ試行の証拠は独自解釈が必要です。[トラフィック管理](03-traffic-management.md)を参照します。


## Grafana

GrafanaはLinkerd 2.12から別導入です。現デフォルトVizにport-forwardする`svc/grafana`はなく、`grafana.enabled:false`では対応統合は設定されません。

必要metricsのPrometheusデータソースを持つ既存Grafanaを使います。`monitoring`のServiceAccount `grafana`で動くメッシュGrafanaには既存Viz Prometheusへの次の許可を使います。

```yaml
apiVersion: policy.linkerd.io/v1alpha1
kind: AuthorizationPolicy
metadata:
  name: prometheus-admin-grafana
  namespace: linkerd-viz
spec:
  targetRef:
    group: policy.linkerd.io
    kind: Server
    name: prometheus-admin
  requiredAuthenticationRefs:
  - kind: ServiceAccount
    name: grafana
    namespace: monitoring
```

IDや外部Prometheusが異なればそのアクセスを設定します。ServiceAccount許可はcallerが実際にそのメッシュIDを提示する必要があります。

外部到達可能GrafanaへVizをリンクするには:

```yaml
grafana:
  externalUrl: https://grafana.example.com/
```

対応選択肢はbrowser向け完全URLの`grafana.externalUrl`とcluster内reverse proxyの`grafana.url`です。後者はGrafana root/subpathも必要です。`grafana.uidPrefix`はimportしたdashboard UIDを区別し、tenant認可ではありません。

リリース群にはhealth、top-line、namespace/workload、Service、route、authority、multicluster表示があります。**AuthorityはHTTP host/:authorityであり認可権限ではありません。** レビュー済みreleaseからimportしdatasource、label、unit、UID linkを確認します。

### 小さなダッシュボード例

classic JSONはdatasource import入力、固定namespace/deployment変数、パネル単位を含みます。import時に選択/調整します。query/JSONは確認済みですがGrafana-server importはしていません。

```json
{
  "__inputs": [
    {
      "name": "DS_PROMETHEUS",
      "label": "Prometheus",
      "type": "datasource",
      "pluginId": "prometheus",
      "pluginName": "Prometheus"
    }
  ],
  "id": null,
  "uid": "linkerd-api-overview",
  "title": "Linkerd API Overview",
  "schemaVersion": 39,
  "version": 1,
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "templating": {
    "list": [
      {
        "name": "namespace",
        "type": "constant",
        "query": "my-app",
        "current": {
          "text": "my-app",
          "value": "my-app"
        }
      },
      {
        "name": "deployment",
        "type": "constant",
        "query": "api",
        "current": {
          "text": "api",
          "value": "api"
        }
      }
    ]
  },
  "panels": [
    {
      "id": 1,
      "title": "Proxy-classified Success Rate",
      "type": "gauge",
      "datasource": {
        "type": "prometheus",
        "uid": "${DS_PROMETHEUS}"
      },
      "gridPos": {
        "x": 0,
        "y": 0,
        "w": 8,
        "h": 8
      },
      "fieldConfig": {
        "defaults": {
          "unit": "percent"
        },
        "overrides": []
      },
      "targets": [
        {
          "refId": "A",
          "datasource": {
            "type": "prometheus",
            "uid": "${DS_PROMETHEUS}"
          },
          "expr": "100 * (((sum(rate(response_total{namespace=\"$namespace\",deployment=\"$deployment\",direction=\"inbound\",classification=\"success\"}[5m])) or vector(0)) / sum(rate(response_total{namespace=\"$namespace\",deployment=\"$deployment\",direction=\"inbound\"}[5m])))\nand on() (sum(rate(response_total{namespace=\"$namespace\",deployment=\"$deployment\",direction=\"inbound\"}[5m])) > 0))",
          "legendFormat": "success"
        }
      ]
    },
    {
      "id": 2,
      "title": "Request Rate",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "${DS_PROMETHEUS}"
      },
      "gridPos": {
        "x": 8,
        "y": 0,
        "w": 8,
        "h": 8
      },
      "fieldConfig": {
        "defaults": {
          "unit": "reqps"
        },
        "overrides": []
      },
      "targets": [
        {
          "refId": "A",
          "datasource": {
            "type": "prometheus",
            "uid": "${DS_PROMETHEUS}"
          },
          "expr": "sum(rate(request_total{namespace=\"$namespace\",deployment=\"$deployment\",direction=\"inbound\"}[5m]))",
          "legendFormat": "requests/s"
        }
      ]
    },
    {
      "id": 3,
      "title": "Time to First Byte",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "${DS_PROMETHEUS}"
      },
      "gridPos": {
        "x": 16,
        "y": 0,
        "w": 8,
        "h": 8
      },
      "fieldConfig": {
        "defaults": {
          "unit": "ms"
        },
        "overrides": []
      },
      "targets": [
        {
          "refId": "A",
          "datasource": {
            "type": "prometheus",
            "uid": "${DS_PROMETHEUS}"
          },
          "expr": "histogram_quantile(0.5, sum by (le) (rate(response_latency_ms_bucket{namespace=\"$namespace\",deployment=\"$deployment\",direction=\"inbound\"}[5m])))",
          "legendFormat": "p50"
        },
        {
          "refId": "B",
          "datasource": {
            "type": "prometheus",
            "uid": "${DS_PROMETHEUS}"
          },
          "expr": "histogram_quantile(0.95, sum by (le) (rate(response_latency_ms_bucket{namespace=\"$namespace\",deployment=\"$deployment\",direction=\"inbound\"}[5m])))",
          "legendFormat": "p95"
        },
        {
          "refId": "C",
          "datasource": {
            "type": "prometheus",
            "uid": "${DS_PROMETHEUS}"
          },
          "expr": "histogram_quantile(0.99, sum by (le) (rate(response_latency_ms_bucket{namespace=\"$namespace\",deployment=\"$deployment\",direction=\"inbound\"}[5m])))",
          "legendFormat": "p99"
        }
      ]
    }
  ]
}
```

## 分散トレーシング

Linkerd-Jaeger拡張は2.19で削除されました。現在は別管理のOpenTelemetry互換collector/backendを使います。旧`linkerd jaeger`、拡張Webhook address、任意`linkerd-jaeger-config` ConfigMapでは設定されません。

`tracing`のServiceAccount `collector`で動く4317の既存**メッシュ参加**OTLP/gRPC collectorには、完全Linkerd設定へ次をマージします。

```yaml
proxy:
  tracing:
    enabled: true
    collector:
      endpoint: collector.tracing.svc.cluster.local:4317
      meshIdentity:
        serviceAccountName: collector
        namespace: tracing
```

チャートはcollector endpointと両meshIdentityフィールドが必要で、それらから期待DNS IDを導出します。メッシュ外でOTLP receiverを動かすだけでは満たしません。Service port、受信pipeline、network/認可、保存、sampled spanを確認します。所有者経由でworkloadを更新しproxyにtrace設定を渡します。

LinkerdはW3CとB3に参加し、両方ならW3Cが優先です。`x-request-id`は相関IDで必須trace形式ではありません。Ingress/アプリ/テスト生成器がcontextとsamplingを確立し、アプリは自身の呼び出し間で伝播します。

### アプリの伝播例

検証された抽出、子span作成、sampling、exportには適切なOpenTelemetryライブラリを優先します。小さな**GETアダプターはW3Cコンテキストを渡すだけ**です。アプリspan作成、ユーザー認証、汎用reverse proxyは提供しません。backend URLは信頼するデプロイ設定から与えます。

Python（ローカル確認はFlask 3.1.3 / Requests 2.32.5）:

```python
from flask import Flask, Response, request
import requests

app = Flask(__name__)
BACKEND_URL = "http://backend-service/api/backend"  # Trusted configuration.
MAX_RESPONSE_BYTES = 1024 * 1024
app.config["DOWNSTREAM_TIMEOUT"] = (2, 5)  # Connect/read inactivity, not total time.


@app.get("/api/data")
def get_data():
    headers = {}
    if request.headers.get("traceparent"):
        for name in ("traceparent", "tracestate"):
            if request.headers.get(name):
                headers[name] = request.headers[name]
    try:
        with requests.get(
            BACKEND_URL,
            headers=headers,
            timeout=app.config["DOWNSTREAM_TIMEOUT"],
            allow_redirects=False,
            stream=True,
        ) as upstream:
            # This small API adapter does not follow or relay redirects.
            if 300 <= upstream.status_code < 400:
                return Response("Unexpected upstream redirect\n", status=502)
            body = bytearray()
            for chunk in upstream.iter_content(chunk_size=16384):
                body.extend(chunk)
                if len(body) > MAX_RESPONSE_BYTES:
                    return Response("Upstream response too large\n", status=502)
            return Response(
                bytes(body),
                status=upstream.status_code,
                content_type=upstream.headers.get(
                    "Content-Type", "application/octet-stream"
                ),
            )
    except requests.Timeout:
        return Response("Upstream timeout\n", status=504)
    except requests.RequestException:
        return Response("Upstream request failed\n", status=502)
```

connect/read timeoutは接続待ちと読み取り非活動時間で、end-to-end総時間ではありません。継続的に少量ずつ届く応答やcaller取消には、この同期例を超えるアプリ/server期限設計が必要です。応答bufferは上限があり、redirectは明示拒否します。

既存HTTP server向けGo handler:

```go
package main

import (
	"errors"
	"io"
	"net"
	"net/http"
	"time"
)

var backendURL = "http://backend-service/api/backend" // Trusted configuration.
var downstreamClient = &http.Client{
	Timeout: 5 * time.Second,
	CheckRedirect: func(req *http.Request, via []*http.Request) error {
		return http.ErrUseLastResponse
	},
}

const maxResponseBytes = 1024 * 1024

func handler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.Header().Set("Allow", http.MethodGet)
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	req, err := http.NewRequestWithContext(r.Context(), http.MethodGet, backendURL, nil)
	if err != nil {
		http.Error(w, "Invalid backend configuration", http.StatusInternalServerError)
		return
	}
	if r.Header.Get("traceparent") != "" {
		for _, name := range []string{"traceparent", "tracestate"} {
			if value := r.Header.Get(name); value != "" {
				req.Header.Set(name, value)
			}
		}
	}
	resp, err := downstreamClient.Do(req)
	if err != nil {
		status := http.StatusBadGateway
		var networkError net.Error
		if errors.As(err, &networkError) && networkError.Timeout() {
			status = http.StatusGatewayTimeout
		}
		http.Error(w, "Upstream request failed", status)
		return
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 && resp.StatusCode < 400 {
		http.Error(w, "Unexpected upstream redirect", http.StatusBadGateway)
		return
	}
	body, err := io.ReadAll(io.LimitReader(resp.Body, maxResponseBytes+1))
	if err != nil || len(body) > maxResponseBytes {
		http.Error(w, "Invalid or oversized upstream response", http.StatusBadGateway)
		return
	}
	contentType := resp.Header.Get("Content-Type")
	if contentType == "" {
		contentType = "application/octet-stream"
	}
	w.Header().Set("Content-Type", contentType)
	w.WriteHeader(resp.StatusCode)
	_, _ = w.Write(body)
}
```

要求取消を伝播し、client呼出を制限し、応答使用前にエラーを確認してbackend status/bodyを転送します。両例はredirectと過大応答を意図的に拒否します。ローカルテストで経路を確認し、本番trace、取り込み、sampling、負荷動作の証明ではありません。

既知sampled traceが期待proxy/アプリspanとともにbackendへ届くか確認します。trace dashboardが開くことは伝播、正しいsampling、完全traceの証明ではありません。

## 診断ログとアクセスログ

proxy診断level/formatとHTTPアクセスログは別設定です。既存メッシュDeploymentへの**マージパッチ**を`proxy-logging-patch.yaml`に保存します。単独Deploymentではありません。

```yaml
spec:
  template:
    metadata:
      labels:
        mesh-required: 'true'
      annotations:
        config.linkerd.io/access-log: json
        config.linkerd.io/proxy-log-format: json
        config.linkerd.io/proxy-log-level: warn,linkerd=info
```

```bash
# This changes the existing workload's Pod template and triggers its rollout.
kubectl -n my-app patch deployment/api --type merge --patch-file proxy-logging-patch.yaml
kubectl -n my-app rollout status deployment/api --timeout=5m
kubectl -n my-app logs deployment/api -c linkerd-proxy --tail=100
```

`config.linkerd.io/access-log:json`はHTTPアクセス記録、`proxy-log-format:json`は診断形式だけを変更します。無差別debug/traceやheader記録を避け、調査に範囲を限定します。opaque TCPをHTTP要求ログにはしません。

`mesh-required:true` Podラベルは下のalert用に健全proxyを意図的に要求する印で、注入はしません。参加は導入/namespace方針に従います。

## ServiceProfileとPolicy Routeメトリクス

ServiceProfileは互換目的で対応を継続します。追加で同Serviceの現HTTPRoute信頼性設定より優先し得るため、dashboardを埋めるだけのために競合profileを追加しないでください。

既存api-serviceに対する別の旧metrics演習では、再試行なしでroute名を加えます。

```yaml
apiVersion: linkerd.io/v1alpha2
kind: ServiceProfile
metadata:
  name: api-service.my-app.svc.cluster.local
  namespace: my-app
spec:
  routes:
  - name: GET /api/users
    condition:
      all:
      - method: GET
      - pathRegex: ^/api/users$
    isRetryable: false
  - name: POST /api/orders
    condition:
      all:
      - method: POST
      - pathRegex: ^/api/orders$
    isRetryable: false
  - name: GET /health
    condition:
      all:
      - method: GET
      - pathRegex: ^/health$
    isRetryable: false
```

明示all条件でmethod/path一致を明確にします。profile route、HTTPRoute policy metrics、任意アプリpathは別表示です。

```bash
linkerd viz routes service/api-service -n my-app
linkerd viz routes deploy/web -n my-app --to svc/api-service --time-window 10m
linkerd viz stat httproute/api-inbound -n my-app
linkerd viz authz deploy/api -n my-app
```

HTTPRoute例は既存Server接続の受信routeが前提です。`viz routes`はServiceProfile表示で、全Gateway API routeの汎用一覧ではありません。

`web`からの送信では集約にdestinationとroute両ラベルを保持します。

```promql
(sum by (dst, rt_route) (rate(route_response_total{namespace="my-app",deployment="web",direction="outbound",classification="success"}[5m]))
 or on(dst, rt_route) (0 * sum by (dst, rt_route) (rate(route_response_total{namespace="my-app",deployment="web",direction="outbound"}[5m])))) / sum by (dst, rt_route) (rate(route_response_total{namespace="my-app",deployment="web",direction="outbound"}[5m]))
and on(dst, rt_route) (sum by (dst, rt_route) (rate(route_response_total{namespace="my-app",deployment="web",direction="outbound"}[5m])) > 0)
```

```promql
histogram_quantile(0.99, sum by (le, dst, rt_route) (rate(route_response_latency_ms_bucket{namespace="my-app",deployment="web",direction="outbound"}[5m])))
```

```promql
sum by (dst, rt_route) (rate(route_request_total{namespace="my-app",deployment="web",direction="outbound"}[5m]))
```

対応したゼロ分子により全失敗routeを欠落させず残します。route名だけの集約は同ラベルの無関係Serviceを混ぜ得ます。

## アラートと調査

PrometheusRuleはselectorラベルが受理され、示すLinkerd jobを収集し、kube-state-metricsがPodラベルと通常/init両runningメトリクスを公開する前提です。metric-labels許可リストで`mesh-required`を有効にします。なければ対象Pod selectorにデータがありません。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: linkerd-alerts
  namespace: monitoring
  labels:
    release: monitoring
spec:
  groups:
  - name: linkerd
    rules:
    - alert: LinkerdAPIHighErrorRate
      expr: |-
        (((sum(rate(response_total{namespace="my-app",deployment="api",direction="inbound",classification="failure"}[5m])) or vector(0)) / sum(rate(response_total{namespace="my-app",deployment="api",direction="inbound"}[5m])))
        and on() (sum(rate(response_total{namespace="my-app",deployment="api",direction="inbound"}[5m])) > 0)) > 0.05
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: API proxy-classified response error ratio exceeds 5%
    - alert: LinkerdAPIHighTTFB
      expr: histogram_quantile(0.99, sum by (le) (rate(response_latency_ms_bucket{namespace="my-app",deployment="api",direction="inbound"}[5m])))
        > 1000
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: API p99 time-to-first-byte exceeds 1000ms
    - alert: LinkerdExpectedProxyNotRunning
      expr: |-
        max by (namespace, pod) (
          (kube_pod_status_phase{namespace="my-app",phase="Running"} == 1)
          and on(namespace, pod) kube_pod_labels{namespace="my-app",label_mesh_required="true"}
        )
        unless on(namespace, pod) max by (namespace, pod) (
          (kube_pod_container_status_running{namespace="my-app",container="linkerd-proxy"} == 1)
          or (kube_pod_init_container_status_running{namespace="my-app",container="linkerd-proxy"} == 1)
        )
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Expected proxy is not running for {{ $labels.namespace }}/{{ $labels.pod }}
    - alert: LinkerdScrapeTargetDown
      expr: up{job=~"linkerd-proxy|linkerd-controller"} == 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: A discovered Linkerd metrics target cannot be scraped
```

proxy alertは注入有無だけでなく**実行すべきRunning Podに稼働proxyがない状態**を確認します。通常/native init両方を扱い、mesh必須印のないPodは無視します。kube-state-metrics収集欠損で期待一覧も消えるため、収集healthは別監視です。

遅延しきい値1000msはTTFBで、要求全体時間ではありません。分類エラーしきい値をSLIへ合わせます。`up == 0`は検出済みtarget失敗で、未検出全targetではありません。

調査はscrape healthと通信範囲の検証から始めます。その後workload/Service統計、関連route、制限付きTap/log、必要時identity/policyを確認します。原因を診断・修正して要求を再現し復旧確認します。診断コマンド列だけでは障害は解決しません。

## 参考資料と次のステップ

- [マルチクラスター](06-multi-cluster.md)、[ベストプラクティス](07-best-practices.md)、[可観測性クイズ](../../quizzes/service-mesh/linkerd/observability.md)
- [ダッシュボード](https://linkerd.io/docs/features/dashboard/)、[メトリクス出力](https://linkerd.io/docs/tasks/exporting-metrics/)、[Grafana](https://linkerd.io/docs/tasks/grafana/)
- [Proxyメトリクス](https://linkerd.io/docs/reference/proxy-metrics/)と[proxy設定](https://linkerd.io/docs/reference/proxy-configuration/)
- [トレーシング](https://linkerd.io/docs/tasks/distributed-tracing/)
- [リリースのメトリクス時刻実装](https://github.com/linkerd/linkerd2-proxy/blob/a66af8117769df060adda6233302a2d1c4142229/linkerd/http/metrics/src/requests/service.rs)
- [リリースViz scrape設定](https://github.com/linkerd/linkerd2/blob/edge-26.9.1/viz/charts/linkerd-viz/templates/prometheus.yaml)
- [リリースGrafana dashboard群](https://github.com/linkerd/linkerd2/tree/edge-26.9.1/grafana/dashboards)
- [kube-state-metrics Podメトリクス](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/workload/pod-metrics.md)
- [W3C trace context](https://www.w3.org/TR/trace-context/)
