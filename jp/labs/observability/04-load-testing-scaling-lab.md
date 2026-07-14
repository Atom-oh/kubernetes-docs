# パート4: 負荷テストと自動スケーリング

> **難易度**: 中級
> **所要時間**: 45分
> **最終更新**: February 22, 2026

## 学習目標

- k6 と Locust を使用した負荷テストシナリオを設計・実行する
- KEDA による Pod 自動スケーリングをリアルタイムで観察する
- 負荷急増時の Karpenter Node 自動スケーリングを監視する
- スケーリングイベントを可視化する Grafana ダッシュボードを構築する

## 前提条件

- [ ] [パート3: MSA デプロイ](./03-msa-deployment-lab.md)を完了している
- [ ] OTel インストルメンテーションを備えた MSA サービスが稼働している
- [ ] KEDA および Karpenter が設定されている
- [ ] k6 がローカルにインストールされている（`brew install k6` または `apt install k6`）

---

## 負荷テストとスケーリングのタイムライン

```mermaid
sequenceDiagram
    participant k6 as k6 Load Test
    participant API as API Gateway
    participant KEDA as KEDA Controller
    participant Karpenter as Karpenter
    participant Grafana as Grafana

    Note over k6,Grafana: Phase 1: Ramp-up (0-5 min)
    k6->>API: 10 → 100 VUs
    API-->>KEDA: Metrics increase
    KEDA->>KEDA: Scale Pods 2 → 8

    Note over k6,Grafana: Phase 2: Sustained Load (5-15 min)
    k6->>API: 100 VUs sustained
    KEDA->>KEDA: Maintain Pod count
    Grafana->>Grafana: Stable metrics

    Note over k6,Grafana: Phase 3: Spike (15-20 min)
    k6->>API: 100 → 500 VUs
    API-->>KEDA: Metrics spike
    KEDA->>KEDA: Scale Pods 8 → 30
    KEDA-->>Karpenter: Node capacity needed
    Karpenter->>Karpenter: Provision new nodes

    Note over k6,Grafana: Phase 4: Cool-down (20-30 min)
    k6->>API: 500 → 0 VUs
    KEDA->>KEDA: Scale Pods 30 → 2
    Karpenter->>Karpenter: Consolidate/terminate nodes
```

---

## 演習1: k6 負荷テストシナリオ

### 手順

**ステップ1.1: k6 負荷テストスクリプトを作成する**

```bash
cat > ~/obs-lab/k6-load-test.js << 'EOF'
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const orderLatency = new Trend('order_latency', true);

// Test configuration
export const options = {
  stages: [
    // Phase 1: Ramp-up
    { duration: '2m', target: 50 },   // Warm up
    { duration: '3m', target: 100 },  // Ramp to 100 VUs

    // Phase 2: Sustained load
    { duration: '10m', target: 100 }, // Hold at 100 VUs

    // Phase 3: Spike
    { duration: '2m', target: 300 },  // Spike to 300 VUs
    { duration: '3m', target: 500 },  // Peak at 500 VUs
    { duration: '2m', target: 500 },  // Hold peak

    // Phase 4: Cool-down
    { duration: '3m', target: 100 },  // Ramp down
    { duration: '2m', target: 50 },   // Further down
    { duration: '3m', target: 0 },    // Complete cool-down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    errors: ['rate<0.1'],
    order_latency: ['p(95)<800'],
  },
};

const BASE_URL = __ENV.API_URL || 'http://api-gateway.msa.svc.cluster.local:8080';

// Test data
const products = ['PROD-001', 'PROD-002', 'PROD-003', 'PROD-004', 'PROD-005'];
const quantities = [1, 2, 3, 5, 10];

function randomItem(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function generateOrder() {
  return {
    customer_id: `CUST-${Math.floor(Math.random() * 10000)}`,
    product_id: randomItem(products),
    quantity: randomItem(quantities),
    payment_method: Math.random() > 0.5 ? 'credit_card' : 'debit_card',
  };
}

export default function () {
  // Scenario 1: Create Order (60% of traffic)
  if (Math.random() < 0.6) {
    const orderPayload = JSON.stringify(generateOrder());
    const orderStart = Date.now();

    const orderRes = http.post(`${BASE_URL}/api/v1/orders`, orderPayload, {
      headers: {
        'Content-Type': 'application/json',
        'X-Request-ID': `req-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      },
      tags: { name: 'CreateOrder' },
    });

    orderLatency.add(Date.now() - orderStart);

    const orderSuccess = check(orderRes, {
      'order created': (r) => r.status === 201,
      'order has id': (r) => r.json('order_id') !== undefined,
    });
    errorRate.add(!orderSuccess);
  }

  // Scenario 2: Get Order Status (30% of traffic)
  else if (Math.random() < 0.9) {
    const orderId = `ORD-${Math.floor(Math.random() * 100000)}`;
    const statusRes = http.get(`${BASE_URL}/api/v1/orders/${orderId}`, {
      tags: { name: 'GetOrderStatus' },
    });

    const statusSuccess = check(statusRes, {
      'status retrieved': (r) => r.status === 200 || r.status === 404,
    });
    errorRate.add(!statusSuccess);
  }

  // Scenario 3: List Orders (10% of traffic)
  else {
    const listRes = http.get(`${BASE_URL}/api/v1/orders?limit=10`, {
      tags: { name: 'ListOrders' },
    });

    const listSuccess = check(listRes, {
      'list retrieved': (r) => r.status === 200,
    });
    errorRate.add(!listSuccess);
  }

  // Think time
  sleep(Math.random() * 2 + 0.5);
}

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    '/tmp/k6-summary.json': JSON.stringify(data),
  };
}
EOF
```

**ステップ1.2: 負荷テストフェーズの説明**

| フェーズ | 期間 | VUs | 目的 |
|-------|----------|-----|---------|
| ランプアップ | 5分 | 10 → 100 | 段階的なウォームアップ、初期スケーリングをトリガー |
| 継続 | 10分 | 100 | 定常状態、安定したメトリクスを観察 |
| スパイク | 7分 | 100 → 500 | ストレステスト、積極的なスケーリングをトリガー |
| クールダウン | 8分 | 500 → 0 | スケールインの観察、リソースのクリーンアップ |

**ステップ1.3: API Gateway URL を取得する**

```bash
kubectl config use-context $(kubectl config get-contexts -o name | grep obs-service)

API_URL=$(kubectl -n msa get svc api-gateway \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo "API Gateway URL: http://$API_URL:8080"
```

**ステップ1.4: k6 負荷テストを実行する**

```bash
# Run load test
k6 run --env API_URL=http://$API_URL:8080 ~/obs-lab/k6-load-test.js

# Or run with output to Prometheus
k6 run --env API_URL=http://$API_URL:8080 \
  --out experimental-prometheus-rw \
  ~/obs-lab/k6-load-test.js
```

---

## 演習2: Locust の代替手段（Python ベース）

### 手順

**ステップ2.1: Locust Deployment を作成する**

```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: locust-script
  namespace: msa
data:
  locustfile.py: |
    from locust import HttpUser, task, between
    import random
    import json

    class OrderUser(HttpUser):
        wait_time = between(0.5, 2)

        products = ['PROD-001', 'PROD-002', 'PROD-003', 'PROD-004', 'PROD-005']

        @task(6)
        def create_order(self):
            order = {
                'customer_id': f'CUST-{random.randint(1, 10000)}',
                'product_id': random.choice(self.products),
                'quantity': random.choice([1, 2, 3, 5, 10]),
                'payment_method': random.choice(['credit_card', 'debit_card']),
            }
            with self.client.post(
                '/api/v1/orders',
                json=order,
                headers={'Content-Type': 'application/json'},
                catch_response=True
            ) as response:
                if response.status_code == 201:
                    response.success()
                else:
                    response.failure(f'Status: {response.status_code}')

        @task(3)
        def get_order_status(self):
            order_id = f'ORD-{random.randint(1, 100000)}'
            self.client.get(f'/api/v1/orders/{order_id}')

        @task(1)
        def list_orders(self):
            self.client.get('/api/v1/orders?limit=10')
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: locust-master
  namespace: msa
spec:
  replicas: 1
  selector:
    matchLabels:
      app: locust
      role: master
  template:
    metadata:
      labels:
        app: locust
        role: master
    spec:
      containers:
        - name: locust
          image: locustio/locust:2.22.0
          ports:
            - containerPort: 8089
            - containerPort: 5557
          command:
            - locust
            - --master
            - --host=http://api-gateway:8080
          volumeMounts:
            - name: locust-script
              mountPath: /home/locust
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
      volumes:
        - name: locust-script
          configMap:
            name: locust-script
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: locust-worker
  namespace: msa
spec:
  replicas: 4
  selector:
    matchLabels:
      app: locust
      role: worker
  template:
    metadata:
      labels:
        app: locust
        role: worker
    spec:
      containers:
        - name: locust
          image: locustio/locust:2.22.0
          command:
            - locust
            - --worker
            - --master-host=locust-master
          volumeMounts:
            - name: locust-script
              mountPath: /home/locust
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
      volumes:
        - name: locust-script
          configMap:
            name: locust-script
---
apiVersion: v1
kind: Service
metadata:
  name: locust-master
  namespace: msa
spec:
  selector:
    app: locust
    role: master
  ports:
    - name: web
      port: 8089
      targetPort: 8089
    - name: master
      port: 5557
      targetPort: 5557
  type: LoadBalancer
EOF
```

**ステップ2.2: Locust Web UI にアクセスする**

```bash
LOCUST_URL=$(kubectl -n msa get svc locust-master \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo "Locust UI: http://$LOCUST_URL:8089"
```

---

## 演習3: 負荷中の自動スケーリングを観察する

### 手順

**ステップ3.1: 監視用に複数のターミナルウィンドウを開く**

```bash
# Terminal 1: Watch Pod scaling
watch -n 2 'kubectl get pods -n msa -l app=order-service -o wide'

# Terminal 2: Watch HPA status
watch -n 5 'kubectl get hpa -n msa'

# Terminal 3: Watch Node scaling (Karpenter)
watch -n 10 'kubectl get nodes -l workload-type=msa'

# Terminal 4: Watch Karpenter logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -f
```

**ステップ3.2: 負荷テスト中の観察ポイント**

| メトリクス | 観察場所 | 期待される動作 |
|--------|-----------------|-------------------|
| Pod 数 | `kubectl get pods -n msa` | 2 → 8 → 30 → 2 |
| HPA メトリクス | `kubectl get hpa -n msa` | CPU/リクエストレートの増加 |
| Node 数 | `kubectl get nodes` | 新しい Node がプロビジョニングされる |
| SQS キュー深度 | AWS Console / CloudWatch | ピーク時にスパイク |
| Prometheus メトリクス | Grafana Explore | リクエストレート、レイテンシ |
| トレース | Tempo / Grafana | エンドツーエンドのレイテンシ |

**ステップ3.3: KEDA スケーリングイベント**

```bash
# Watch KEDA events
kubectl get events -n msa --field-selector reason=KEDAScaleTargetActivated -w

# Check ScaledObject status
kubectl describe scaledobject -n msa order-service-scaler
```

**ステップ3.4: Karpenter プロビジョニングイベント**

```bash
# Watch node provisioning
kubectl get events -A --field-selector reason=Provisioned -w

# Check NodePool status
kubectl describe nodepool msa-workloads
```

---

## 演習4: クールダウンとスケールインを観察する

### 手順

**ステップ4.1: 負荷テスト完了後のスケールインを監視する**

```bash
# Watch Pod termination
kubectl get pods -n msa -l app=order-service -w

# Watch node consolidation
kubectl get events -A --field-selector reason=Consolidated -w
```

**ステップ4.2: スケールインのタイムライン**

| 負荷後の時間 | Pod 数 | Node 数 | 注記 |
|-----------------|-----------|------------|-------|
| 0分 | 30 | 8+ | ピーク状態 |
| 2分 | 20 | 8+ | HPA のクールダウン開始 |
| 5分 | 10 | 6 | Pod を終了中 |
| 10分 | 4 | 4 | Karpenter が統合中 |
| 15分 | 2 | 3 | ベースライン付近 |
| 20分 | 2 | 2 | ベースラインに復帰 |

**ステップ4.3: コスト最適化を検証する**

```bash
# Check spot instance usage
kubectl get nodes -o custom-columns=NAME:.metadata.name,TYPE:.metadata.labels.karpenter\\.sh/capacity-type,INSTANCE:.metadata.labels.node\\.kubernetes\\.io/instance-type

# Expected: Mix of spot and on-demand instances
```

---

## 演習5: Grafana スケーリングダッシュボード

### 手順

**ステップ5.1: スケーリングダッシュボードのパネルを作成する**

| パネル | メトリクスクエリ | 可視化 |
|-------|-------------|---------------|
| Pod 数 | `sum(kube_deployment_status_replicas{namespace="msa"}) by (deployment)` | 時系列 |
| Node 数 | `count(kube_node_info{node=~".*msa.*"})` | Stat |
| CPU 使用量 | `sum(rate(container_cpu_usage_seconds_total{namespace="msa"}[5m])) by (pod)` | 時系列 |
| メモリ使用量 | `sum(container_memory_working_set_bytes{namespace="msa"}) by (pod)` | 時系列 |
| SQS キュー深度 | `aws_sqs_approximate_number_of_messages_visible_average{queue_name="obs-lab-orders"}` | 時系列 |
| リクエストレート | `sum(rate(http_server_request_count{namespace="msa"}[1m])) by (service)` | 時系列 |
| エラーレート | `sum(rate(http_server_request_count{namespace="msa",http_status_code=~"5.."}[1m])) / sum(rate(http_server_request_count{namespace="msa"}[1m]))` | Gauge |
| P99 レイテンシ | `histogram_quantile(0.99, sum(rate(http_server_request_duration_seconds_bucket{namespace="msa"}[5m])) by (le, service))` | 時系列 |

**ステップ5.2: ダッシュボード JSON をインポートする**

```bash
cat > /tmp/scaling-dashboard.json << 'EOF'
{
  "dashboard": {
    "title": "MSA Scaling Dashboard",
    "tags": ["obs-lab", "scaling", "k6"],
    "timezone": "browser",
    "panels": [
      {
        "title": "Pod Replicas by Deployment",
        "type": "timeseries",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
        "targets": [{
          "expr": "sum(kube_deployment_status_replicas{namespace=\"msa\"}) by (deployment)",
          "legendFormat": "{{deployment}}"
        }]
      },
      {
        "title": "Node Count",
        "type": "stat",
        "gridPos": {"h": 4, "w": 6, "x": 12, "y": 0},
        "targets": [{
          "expr": "count(kube_node_info)"
        }]
      },
      {
        "title": "Request Rate",
        "type": "timeseries",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
        "targets": [{
          "expr": "sum(rate(http_server_request_count{namespace=\"msa\"}[1m])) by (service)",
          "legendFormat": "{{service}}"
        }]
      },
      {
        "title": "P99 Latency (ms)",
        "type": "timeseries",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
        "targets": [{
          "expr": "histogram_quantile(0.99, sum(rate(http_server_request_duration_seconds_bucket{namespace=\"msa\"}[5m])) by (le, service)) * 1000",
          "legendFormat": "{{service}}"
        }]
      }
    ]
  }
}
EOF

# Import via Grafana API
curl -X POST -H "Content-Type: application/json" \
  -u admin:ObsLab2026! \
  -d @/tmp/scaling-dashboard.json \
  "http://$GRAFANA_URL/api/dashboards/db"
```

**ステップ5.3: スケーリングイベントのアノテーションを作成する**

```bash
# Add Prometheus recording rules for scaling events
cat <<'EOF' | kubectl apply -f -
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: scaling-events
  namespace: monitoring
spec:
  groups:
    - name: scaling-events
      rules:
        - record: scaling:pod_scale_up
          expr: |
            changes(kube_deployment_status_replicas{namespace="msa"}[5m]) > 0
            and
            delta(kube_deployment_status_replicas{namespace="msa"}[5m]) > 0

        - record: scaling:pod_scale_down
          expr: |
            changes(kube_deployment_status_replicas{namespace="msa"}[5m]) > 0
            and
            delta(kube_deployment_status_replicas{namespace="msa"}[5m]) < 0

        - record: scaling:node_added
          expr: |
            changes(kube_node_created{node=~".*msa.*"}[10m]) > 0
EOF
```

### 検証

```bash
# Open Grafana dashboard
echo "Grafana URL: http://$GRAFANA_URL"
echo "Dashboard: MSA Scaling Dashboard"

# Verify metrics are populated
curl -s -u admin:ObsLab2026! \
  "http://$GRAFANA_URL/api/datasources/proxy/1/api/v1/query?query=kube_deployment_status_replicas" | jq
```

---

## まとめ

このラボでは、以下を実施しました。

| タスク | ステータス |
|------|--------|
| k6 負荷テストスクリプト | 作成済み |
| Locust Deployment | デプロイ済み |
| Pod 自動スケーリング（KEDA） | 観察済み |
| Node 自動スケーリング（Karpenter） | 観察済み |
| スケールイン動作 | 検証済み |
| スケーリングダッシュボード | 作成済み |

### 主な観察結果

| メトリクス | ベースライン | ピーク | 復旧 |
|--------|----------|------|----------|
| Order Service Pod | 2 | 30 | 2 |
| 合計 Node 数 | 3 | 8+ | 3 |
| リクエストレート | 0 | 500+ RPS | 0 |
| P99 レイテンシ | <100ms | <500ms | <100ms |
| エラーレート | 0% | <1% | 0% |

## クリーンアップ

クリーンアップは[パート6](./06-distributed-tracing-lab.md#cleanup)で実行します。

## トラブルシューティング

<details>
<summary>k6 が API Gateway に到達できない</summary>

- LoadBalancer に外部 IP があることを確認する: `kubectl get svc -n msa api-gateway`
- セキュリティグループがインバウンドトラフィックを許可していることを確認する
- 接続性をテストする: `curl http://$API_URL:8080/health`
</details>

<details>
<summary>Pod がスケーリングしない</summary>

- HPA ステータスを確認する: `kubectl describe hpa -n msa`
- KEDA ScaledObject を確認する: `kubectl describe scaledobject -n msa`
- メトリクスの可用性を確認する: `kubectl top pods -n msa`
</details>

<details>
<summary>Node がプロビジョニングされない</summary>

- Karpenter ログを確認する: `kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter`
- NodePool の制限を確認する: `kubectl describe nodepool msa-workloads`
- AWS アカウントの EC2 インスタンス制限を確認する
</details>

## 次のステップ

アラートと AI を活用したインシデントレスポンスを設定するには、[パート5: Alerting と AIOps](./05-alerting-aiops-lab.md)に進んでください。

## 参考資料

- [k6 ドキュメント](https://k6.io/docs/)
- [Locust ドキュメント](https://docs.locust.io/)
- [KEDA ドキュメント](../../autoscaling/01-keda.md)
- [Karpenter ドキュメント](../../autoscaling/02-karpenter.md)
