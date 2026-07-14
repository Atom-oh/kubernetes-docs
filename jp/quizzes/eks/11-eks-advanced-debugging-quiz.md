# Amazon EKS 高度なデバッグクイズ

このクイズでは、インシデント対応、コントロールプレーンのデバッグ、Node のトラブルシューティング、kubectl debug、PromQL クエリ、オブザーバビリティなど、Amazon EKS における高度なデバッグ手法の理解を確認します。

## クイズ概要
- インシデント対応プロセス
- EKS コントロールプレーンのデバッグ
- Node と kubelet のトラブルシューティング
- kubectl debug コマンドの使用方法
- PromQL クエリとメトリクス分析
- 分散トレーシングとログ分析

## 選択問題

### 1. EKS API server の audit logs はどこで確認すべきですか？

A. /var/log/kubernetes/ ディレクトリ
B. Amazon CloudWatch Logs
C. etcd database
D. kubectl logs コマンド

<details>
<summary>回答を見る</summary>

**回答: B. Amazon CloudWatch Logs**

**解説:**
EKS control plane logs は AWS によって管理され、CloudWatch Logs に送信されます。Audit logs は `/aws/eks/<cluster-name>/cluster` log group で確認できます。

**ログの種類:**
- `api`: API server logs
- `audit`: Audit logs
- `authenticator`: Authentication logs
- `controllerManager`: Controller manager logs
- `scheduler`: Scheduler logs

```bash
# Enable control plane logging
aws eks update-cluster-config \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# CloudWatch Logs Insights Query
fields @timestamp, @message
| filter @logStream like /kube-apiserver-audit/
| filter @message like "403"
| sort @timestamp desc
| limit 100
```

</details>

### 2. kubectl debug を使用して実行中の Pod にデバッグ用 container を追加するために使う flag はどれですか？

A. --attach
B. --copy-to
C. --ephemeral
D. --sidecar

<details>
<summary>回答を見る</summary>

**回答: B. --copy-to**

**解説:**
`--copy-to` flag は既存の Pod のコピーを作成し、デバッグ用 container や変更した設定を追加できるようにします。`--share-processes` と一緒に使用すると、process namespace の共有が有効になります。

```bash
# Add debug container to Pod copy
kubectl debug myapp-pod --copy-to=myapp-debug --container=debugger --image=busybox -- sh

# Share process namespace
kubectl debug myapp-pod --copy-to=myapp-debug --share-processes --container=debugger --image=busybox

# Direct debugging with Ephemeral container (no Pod copy)
kubectl debug -it myapp-pod --image=busybox --target=myapp-container
```

**主なオプション:**
- `--copy-to`: Pod のコピーを作成
- `--share-processes`: process namespace を共有
- `--target`: 対象 container を指定（ephemeral containers 用）

</details>

### 3. Node が NotReady 状態の場合、最初に何を確認すべきですか？

A. Pod logs
B. kubelet の status と logs
C. etcd status
D. CoreDNS logs

<details>
<summary>回答を見る</summary>

**回答: B. kubelet の status と logs**

**解説:**
Node が NotReady になる最も一般的な原因は kubelet の問題です。kubelet が API server と通信できない場合、Node status は NotReady に変わります。

```bash
# Check node status
kubectl describe node <node-name>

# SSH to node and check kubelet status
systemctl status kubelet

# Check kubelet logs
journalctl -u kubelet -f

# Restart kubelet
sudo systemctl restart kubelet
```

**NotReady チェックリスト:**
1. kubelet process status
2. ネットワーク接続（API server へのアクセス）
3. Disk space
4. Memory (OOM)
5. Container runtime status

</details>

### 4. 過去 5 分間で CPU 使用率が 80% を超える Pods を見つける PromQL クエリはどれですか？

A. `cpu_usage > 80`
B. `rate(container_cpu_usage_seconds_total[5m]) > 0.8`
C. `sum(rate(container_cpu_usage_seconds_total[5m])) by (pod) / sum(kube_pod_container_resource_limits{resource="cpu"}) by (pod) > 0.8`
D. `container_cpu_percent > 80`

<details>
<summary>回答を見る</summary>

**回答: C. `sum(rate(container_cpu_usage_seconds_total[5m])) by (pod) / sum(kube_pod_container_resource_limits{resource="cpu"}) by (pod) > 0.8`**

**解説:**
CPU 使用率は、実際の使用量と limit の比率です。`rate()` 関数は 1 秒あたりの CPU 使用量を計算し、それを limit で割ることでパーセンテージを求めます。

```promql
# CPU utilization (against limit)
sum(rate(container_cpu_usage_seconds_total{container!=""}[5m])) by (pod, namespace)
/
sum(kube_pod_container_resource_limits{resource="cpu"}) by (pod, namespace)
* 100 > 80

# Memory utilization
sum(container_memory_working_set_bytes{container!=""}) by (pod, namespace)
/
sum(kube_pod_container_resource_limits{resource="memory"}) by (pod, namespace)
* 100 > 80

# Top 10 CPU usage in specific namespace
topk(10, sum(rate(container_cpu_usage_seconds_total{namespace="production"}[5m])) by (pod))
```

</details>

### 5. EKS で Node 間のネットワーク問題をデバッグするのに適していない tool はどれですか？

A. tcpdump
B. wireshark
C. kubectl exec 経由の ping/curl tests
D. etcdctl

<details>
<summary>回答を見る</summary>

**回答: D. etcdctl**

**解説:**
etcdctl は etcd database を管理するための tool であり、ネットワークデバッグとは関係ありません。EKS では etcd は AWS によって管理されるため、いずれにしても直接アクセスすることはできません。

**ネットワークデバッグツール:**
```bash
# Capture packets with tcpdump
kubectl debug node/<node-name> -it --image=nicolaka/netshoot -- tcpdump -i eth0

# Test connectivity between nodes
kubectl debug node/<node-name> -it --image=nicolaka/netshoot -- ping <other-node-ip>

# Test network from within Pod
kubectl exec -it <pod-name> -- curl -v http://service-name

# DNS test
kubectl exec -it <pod-name> -- nslookup kubernetes.default.svc.cluster.local
```

</details>

### 6. インシデント対応において MTTD (Mean Time To Detect) を短縮する最も効果的な方法は何ですか？

A. 手動監視の強化
B. alert threshold を非常に低く設定する
C. 適切な alerting rules と自動監視システムを構築する
D. log retention period を延長する

<details>
<summary>回答を見る</summary>

**回答: C. 適切な alerting rules と自動監視システムを構築する**

**解説:**
MTTD を短縮するには、適切な alert thresholds と自動監視が必要です。過度に敏感な alerts は alert fatigue を引き起こします。

```yaml
# Prometheus AlertRule Example
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: eks-alerts
spec:
  groups:
  - name: eks.rules
    rules:
    - alert: HighErrorRate
      expr: |
        sum(rate(http_requests_total{status=~"5.."}[5m]))
        / sum(rate(http_requests_total[5m])) > 0.05
      for: 2m
      labels:
        severity: critical
      annotations:
        summary: "High error rate detected"

    - alert: PodCrashLooping
      expr: |
        rate(kube_pod_container_status_restarts_total[15m]) > 0
      for: 5m
      labels:
        severity: warning
```

**MTTD 最適化戦略:**
- SLO ベースの alerting
- Multi-window burn rate alerts
- Alert priority classification
- On-call rotation and escalation

</details>

### 7. kubectl debug を使用して Node 上に直接デバッグ用 Pod を作成するコマンドはどれですか？

A. `kubectl debug node/<node-name> -it --image=busybox`
B. `kubectl exec node/<node-name> -- sh`
C. `kubectl attach node/<node-name>`
D. `kubectl run debug --node=<node-name>`

<details>
<summary>回答を見る</summary>

**回答: A. `kubectl debug node/<node-name> -it --image=busybox`**

**解説:**
Kubernetes 1.20 以降では、`kubectl debug node/` コマンドにより、host filesystem とネットワークにアクセスできる privileged Pod が Node 上に作成されます。

```bash
# Node debugging
kubectl debug node/ip-10-0-1-100.us-west-2.compute.internal -it --image=busybox

# Access host filesystem (mounted at /host)
# Inside the Pod:
chroot /host

# Use image with more tools
kubectl debug node/<node-name> -it --image=nicolaka/netshoot

# Check node's kubelet logs (inside Pod)
journalctl -u kubelet --no-pager | tail -100
```

**重要な注意事項:**
- Node debugging Pods は privileged mode で実行される
- Host namespaces にアクセスできる
- 本番環境では RBAC でアクセスを制限する

</details>

### 8. 分散トレーシングにおける「Span」とは何を意味しますか？

A. request の総処理時間
B. 単一作業単位の時間計測
C. services 間の network latency
D. log messages の timestamp

<details>
<summary>回答を見る</summary>

**回答: B. 単一作業単位の時間計測**

**解説:**
Span は分散システムにおける単一の作業単位を表し、開始時刻、終了時刻、metadata を含みます。複数の Spans がまとまって Trace を形成します。

**分散トレーシングの概念:**
- **Trace**: request flow 全体を表す Spans の集合
- **Span**: 単一の作業単位（例: HTTP request、DB query）
- **Parent-Child relationship**: Spans 間の呼び出し関係
- **Baggage**: Spans 間で伝播される context information

```yaml
# OpenTelemetry Collector Configuration
apiVersion: opentelemetry.io/v1alpha1
kind: OpenTelemetryCollector
metadata:
  name: otel-collector
spec:
  config: |
    receivers:
      otlp:
        protocols:
          grpc:
          http:
    processors:
      batch:
    exporters:
      jaeger:
        endpoint: jaeger-collector:14250
    service:
      pipelines:
        traces:
          receivers: [otlp]
          processors: [batch]
          exporters: [jaeger]
```

</details>

### 9. EKS で CoreDNS の問題をデバッグするのに最も有用なコマンドはどれですか？

A. `kubectl logs -n kube-system -l k8s-app=kube-dns`
B. `kubectl describe service kubernetes`
C. `aws eks describe-cluster`
D. `kubectl get endpoints`

<details>
<summary>回答を見る</summary>

**回答: A. `kubectl logs -n kube-system -l k8s-app=kube-dns`**

**解説:**
CoreDNS Pod logs を確認すると、DNS query の処理状況、errors、timeouts が分かります。

```bash
# Check CoreDNS logs
kubectl logs -n kube-system -l k8s-app=kube-dns -f

# Check CoreDNS Pod status
kubectl get pods -n kube-system -l k8s-app=kube-dns

# Check CoreDNS ConfigMap
kubectl get configmap coredns -n kube-system -o yaml

# Create DNS test Pod
kubectl run dns-test --image=busybox:1.28 --rm -it --restart=Never -- nslookup kubernetes.default

# Debug DNS queries
kubectl exec -it <pod-name> -- nslookup -debug kubernetes.default.svc.cluster.local
```

**一般的な CoreDNS の問題:**
- Pod resource constraints (CPU/Memory)
- ConfigMap configuration errors
- Upstream DNS connection issues
- Cluster IP service connectivity problems

</details>

### 10. リアルタイムの Pod resource usage を表示する kubectl コマンドはどれですか？

A. `kubectl describe pod`
B. `kubectl top pods`
C. `kubectl get pods -o wide`
D. `kubectl logs`

<details>
<summary>回答を見る</summary>

**回答: B. `kubectl top pods`**

**解説:**
`kubectl top` コマンドは Metrics Server によって収集された resource usage data を表示します。CPU と memory usage をリアルタイムで確認できます。

```bash
# Pod resource usage across all namespaces
kubectl top pods -A

# Pods in specific namespace
kubectl top pods -n production

# Resource usage by container
kubectl top pods --containers

# Node resource usage
kubectl top nodes

# Sort by CPU
kubectl top pods --sort-by=cpu

# Sort by memory
kubectl top pods --sort-by=memory
```

**前提条件:**
- Metrics Server がインストールされている必要がある
- `kubectl top` はリアルタイムの snapshot のみを提供する（履歴なし）
- 長期的な監視には Prometheus + Grafana を使用する

</details>

## 短答問題

### 1. CloudWatch Logs で EKS control plane logs を表示するための log group name pattern は何ですか？

<details>
<summary>回答を見る</summary>

**回答:** `/aws/eks/<cluster-name>/cluster`

**解説:**
EKS control plane logs は自動的にこの log group に送信されます。

```bash
# CloudWatch Logs Insights Query Example
# Log group: /aws/eks/my-cluster/cluster

# Search API server error logs
fields @timestamp, @message
| filter @logStream like /kube-apiserver/
| filter @message like /error|Error|ERROR/
| sort @timestamp desc
| limit 50

# Search specific user activity in audit logs
fields @timestamp, @message
| filter @logStream like /kube-apiserver-audit/
| filter @message like /"user":.*"admin"/
| sort @timestamp desc
```

</details>

### 2. Kubernetes で Ephemeral Containers を有効化するために必要な feature gate name は何ですか？

<details>
<summary>回答を見る</summary>

**回答:** `EphemeralContainers` (Kubernetes 1.25 以降ではデフォルトで有効)

**解説:**
この feature は Kubernetes 1.23 で beta になり、1.25 で GA (Generally Available) となってデフォルトで有効化されました。EKS 1.25 以降では追加設定は不要です。

```bash
# Add Ephemeral Container
kubectl debug -it <pod-name> --image=busybox --target=<container-name>

# Check Ephemeral Containers
kubectl get pod <pod-name> -o jsonpath='{.spec.ephemeralContainers}'

# List Ephemeral Containers added to Pod
kubectl describe pod <pod-name> | grep -A 10 "Ephemeral Containers"
```

</details>

### 3. PromQL における rate() と irate() 関数の違いは何ですか？

<details>
<summary>回答を見る</summary>

**回答:**
- `rate()`: 指定された時間範囲全体での平均変化率を計算する（滑らか）
- `irate()`: 最後の 2 つの data points のみを使用して瞬間変化率を計算する（変動が大きい）

**使用例:**
```promql
# rate() - Average request rate over 5 minutes (good for alerts, dashboards)
rate(http_requests_total[5m])

# irate() - Instant request rate (good for detecting sudden changes)
irate(http_requests_total[5m])

# CPU utilization - rate() recommended
rate(container_cpu_usage_seconds_total[5m])

# Spike detection - irate() recommended
irate(http_requests_total[1m]) > 1000
```

**選択ガイド:**
- Alert rules: `rate()` を使用（noise を減らす）
- デバッグ/急激な変化の検出: `irate()` を使用
- 長期トレンド分析: `rate()` を使用

</details>

### 4. kubectl debug で Node に接続したとき、host filesystem はどの path にマウントされますか？

<details>
<summary>回答を見る</summary>

**回答:** `/host`

**解説:**
`kubectl debug node/` で Pod が作成されると、host の root filesystem は `/host` にマウントされます。

```bash
# Create node debugging Pod
kubectl debug node/<node-name> -it --image=busybox

# Access host filesystem inside Pod
ls /host
cat /host/etc/kubernetes/kubelet/kubelet-config.json

# chroot to host environment
chroot /host

# After chroot, run host commands
systemctl status kubelet
journalctl -u kubelet -n 100
```

</details>

### 5. インシデント対応における MTTR (Mean Time To Resolve) の 2 つの主な構成要素は何ですか？

<details>
<summary>回答を見る</summary>

**回答:**
1. **MTTD (Mean Time To Detect)**: 問題発生から検出までの時間
2. **MTTI (Mean Time To Investigate/Identify)**: 検出から root cause の特定と解決までの時間

または:
- MTTD + MTTI + MTTFix（実際の修正時間）

**MTTR 改善戦略:**
```
MTTR = MTTD + MTTI + MTTFix

MTTD Improvement:
- Effective monitoring and alerting
- SLO-based alerting

MTTI Improvement:
- Create runbooks
- Automated diagnostic tools

MTTFix Improvement:
- Auto-recovery mechanisms
- Rollback automation
- GitOps-based deployment
```

</details>

## ハンズオン演習

### 1. 次の要件を満たす PromQL クエリを書いてください:
- 過去 5 分間に production namespace で再起動した containers を見つける
- restart count が 2 以上のものに絞り込む

<details>
<summary>回答を見る</summary>

```promql
# Containers with restart count >= 2 over last 5 minutes
increase(kube_pod_container_status_restarts_total{namespace="production"}[5m]) >= 2
```

**バリアントクエリ:**
```promql
# Show Pod name with restart count
sum by (pod, container) (
  increase(kube_pod_container_status_restarts_total{namespace="production"}[5m])
) >= 2

# Total restart count (cumulative)
kube_pod_container_status_restarts_total{namespace="production"} > 5

# Top 10 most restarted Pods over last hour
topk(10,
  increase(kube_pod_container_status_restarts_total{namespace="production"}[1h])
)
```

**Grafana Dashboard 用:**
```promql
# Time series graph
rate(kube_pod_container_status_restarts_total{namespace="production"}[5m])

# Table (current status)
kube_pod_container_status_restarts_total{namespace="production"}
```

</details>

### 2. CrashLoopBackOff 状態の Pod をデバッグするための step-by-step commands を書いてください。

<details>
<summary>回答を見る</summary>

```bash
# 1. Check Pod status
kubectl get pods -n <namespace> | grep CrashLoopBackOff

# 2. Check Pod detailed info (including events)
kubectl describe pod <pod-name> -n <namespace>

# 3. Check previous container logs (pre-crash logs)
kubectl logs <pod-name> -n <namespace> --previous

# 4. Check current container logs
kubectl logs <pod-name> -n <namespace>

# 5. Override container start command for debugging
kubectl debug <pod-name> -n <namespace> --copy-to=debug-pod \
  --container=<container-name> -- sleep infinity

# 6. Connect to debug Pod
kubectl exec -it debug-pod -n <namespace> -- sh

# 7. Check environment variables
kubectl exec -it debug-pod -n <namespace> -- env

# 8. Check filesystem and configuration
kubectl exec -it debug-pod -n <namespace> -- ls -la /app
kubectl exec -it debug-pod -n <namespace> -- cat /app/config.yaml

# 9. Cleanup after debugging
kubectl delete pod debug-pod -n <namespace>
```

**一般的な CrashLoopBackOff の原因:**
- 無効な configuration files
- 不足している environment variables または secrets
- Resource constraints (OOM Kill)
- Health check failures
- Dependency service connection failures

</details>

### 3. 過去 1 時間の EKS audit logs で permission denied (403) events を検索する CloudWatch Logs Insights クエリを書いてください。

<details>
<summary>回答を見る</summary>

```sql
# CloudWatch Logs Insights Query
# Log group: /aws/eks/<cluster-name>/cluster

# Basic 403 error search
fields @timestamp, @message
| filter @logStream like /kube-apiserver-audit/
| filter @message like /"responseStatus":\s*\{\s*"code":\s*403/
| sort @timestamp desc
| limit 100

# Parse detailed information
fields @timestamp, @message
| filter @logStream like /kube-apiserver-audit/
| parse @message '"user":{"username":"*"}' as username
| parse @message '"verb":"*"' as verb
| parse @message '"resource":"*"' as resource
| parse @message '"responseStatus":{"code":*}' as statusCode
| filter statusCode = 403
| display @timestamp, username, verb, resource
| sort @timestamp desc
| limit 100

# Aggregate 403 errors by user
fields @timestamp, @message
| filter @logStream like /kube-apiserver-audit/
| parse @message '"user":{"username":"*"}' as username
| parse @message '"responseStatus":{"code":*}' as statusCode
| filter statusCode = 403
| stats count(*) as errorCount by username
| sort errorCount desc
```

**AWS CLI で実行:**
```bash
aws logs start-query \
  --log-group-name "/aws/eks/my-cluster/cluster" \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter @logStream like /kube-apiserver-audit/ | filter @message like /"code":403/ | sort @timestamp desc | limit 50'
```

</details>

## 上級問題

### 1. microservices architecture で、特定の API が断続的に遅い response times を経験しています。Distributed tracing、metrics、logs を使用した包括的なデバッグ戦略を作成してください。

<details>
<summary>回答を見る</summary>

**包括的なデバッグ戦略: 断続的なレイテンシ分析**

**Step 1: 問題範囲の定義（Metrics）**

```promql
# Check P99 response time
histogram_quantile(0.99,
  sum(rate(http_request_duration_seconds_bucket{service="api-gateway"}[5m])) by (le, endpoint)
)

# Check response time distribution (for heatmap)
sum(rate(http_request_duration_seconds_bucket{service="api-gateway"}[1m])) by (le)

# Slow request ratio
sum(rate(http_request_duration_seconds_count{service="api-gateway"}[5m]))
-
sum(rate(http_request_duration_seconds_bucket{service="api-gateway",le="0.5"}[5m]))
```

**Step 2: Distributed Tracing で bottlenecks を特定**

```yaml
# Jaeger Query Strategy
# 1. Search slow traces (>2s)
service=api-gateway minDuration=2s

# 2. Traces with errors
service=api-gateway tags={"error":"true"}

# 3. Traces for specific endpoint
service=api-gateway operation="GET /api/products"
```

**Step 3: Log correlation analysis**

```bash
# Search related logs by Trace ID
kubectl logs -l app=api-gateway | grep "trace_id=abc123"

# CloudWatch Logs Insights
fields @timestamp, @message
| filter @message like /trace_id=abc123/
| sort @timestamp asc
```

**Step 4: Infrastructure level analysis**

```promql
# Check Pod CPU Throttling
rate(container_cpu_cfs_throttled_seconds_total[5m])

# Network latency
rate(container_network_receive_bytes_total[5m])

# GC impact analysis (Java)
rate(jvm_gc_pause_seconds_sum[5m])
```

**Step 5: Integrated dashboard**

```yaml
# Grafana Dashboard Configuration
panels:
  - title: "Request Latency (P50, P95, P99)"
    query: histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))

  - title: "Request Rate by Status"
    query: sum(rate(http_requests_total[5m])) by (status_code)

  - title: "Slow Requests Heatmap"
    query: sum(increase(http_request_duration_seconds_bucket[1m])) by (le)

  - title: "Downstream Service Latency"
    query: histogram_quantile(0.99, sum(rate(downstream_request_duration_seconds_bucket[5m])) by (le, service))

  - title: "Pod Resource Usage"
    queries:
      - container_cpu_usage_seconds_total
      - container_memory_working_set_bytes
```

**Step 6: Automated anomaly detection**

```yaml
# Prometheus AlertRule
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: latency-anomaly-detection
spec:
  groups:
  - name: latency.rules
    rules:
    - alert: LatencyAnomaly
      expr: |
        (
          histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service))
          -
          histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[1h])) by (le, service))
        )
        /
        histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[1h])) by (le, service))
        > 0.5
      for: 5m
      annotations:
        summary: "Latency increased by 50% compared to 1h average"
```

**分析チェックリスト:**
- [ ] 特定の endpoints でのみ発生しているか？
- [ ] 特定の時間帯に集中しているか？
- [ ] 特定の downstream service が原因か？
- [ ] Resource limitation (CPU throttling) が影響しているか？
- [ ] GC または JVM 関連の問題か？
- [ ] network level の問題か？

</details>

### 2. EKS cluster の Nodes が断続的に NotReady になっています。体系的な Root Cause Analysis (RCA) process と予防策を確立してください。

<details>
<summary>回答を見る</summary>

**Root Cause Analysis (RCA) プロセス**

**Phase 1: Data collection**

```bash
# 1. Check node event history
kubectl get events --field-selector involvedObject.kind=Node --sort-by='.lastTimestamp'

# 2. Check detailed node status
kubectl describe node <node-name> | grep -A 20 "Conditions:"

# 3. Check node metrics in CloudWatch
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name StatusCheckFailed \
  --dimensions Name=InstanceId,Value=<instance-id> \
  --start-time $(date -d '24 hours ago' -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Sum
```

**Phase 2: System log analysis**

```bash
# Deploy debugging Pod on node
kubectl debug node/<node-name> -it --image=amazonlinux:2 -- bash

# Access host environment with chroot
chroot /host

# Check system logs
journalctl -u kubelet --since "24 hours ago" | grep -i "error\|fail\|timeout"
dmesg | tail -100

# Check memory/CPU status
free -h
vmstat 1 5
cat /proc/pressure/memory
cat /proc/pressure/cpu
```

**Phase 3: Network analysis**

```bash
# Check API server connectivity
curl -k https://kubernetes.default.svc.cluster.local/healthz

# Check VPC CNI status
kubectl logs -n kube-system -l k8s-app=aws-node --tail=100

# Check ENI and IP allocation status
aws ec2 describe-network-interfaces \
  --filters Name=attachment.instance-id,Values=<instance-id>
```

**Phase 4: Resource pressure analysis**

```promql
# Node memory pressure
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 90

# Node disk pressure
(1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) * 100 > 85

# Node PID pressure
node_processes_threads / node_processes_max_threads * 100 > 80
```

**Phase 5: Root cause classification**

| Category | Possible Cause | Verification Method |
|---------|------------|----------|
| Resource | OOM Kill | `dmesg \| grep -i oom` |
| Resource | Disk full | `df -h` |
| Network | CNI issue | aws-node logs |
| Network | API server connection | curl healthz |
| System | kubelet crash | `journalctl -u kubelet` |
| Infrastructure | EC2 instance issue | CloudWatch metrics |

**Phase 6: Preventive measures**

```yaml
# 1. Deploy Node Problem Detector
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-problem-detector
  namespace: kube-system
spec:
  selector:
    matchLabels:
      app: node-problem-detector
  template:
    spec:
      containers:
      - name: node-problem-detector
        image: registry.k8s.io/node-problem-detector/node-problem-detector:v0.8.13
        securityContext:
          privileged: true
        volumeMounts:
        - name: log
          mountPath: /var/log
          readOnly: true
        - name: kmsg
          mountPath: /dev/kmsg
          readOnly: true
      volumes:
      - name: log
        hostPath:
          path: /var/log/
      - name: kmsg
        hostPath:
          path: /dev/kmsg
```

```yaml
# 2. Resource-based Alerts
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: node-health-rules
spec:
  groups:
  - name: node.health
    rules:
    - alert: NodeMemoryPressure
      expr: |
        (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) > 0.85
      for: 5m
      labels:
        severity: warning

    - alert: NodeDiskPressure
      expr: |
        (1 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes) > 0.85
      for: 5m
      labels:
        severity: warning

    - alert: NodeNotReady
      expr: |
        kube_node_status_condition{condition="Ready",status="true"} == 0
      for: 2m
      labels:
        severity: critical
```

```bash
# 3. Node auto-recovery setup (Karpenter)
# Karpenter automatically replaces NotReady nodes

# 4. kubelet configuration optimization
# /etc/kubernetes/kubelet/kubelet-config.json
{
  "evictionHard": {
    "memory.available": "500Mi",
    "nodefs.available": "10%",
    "imagefs.available": "15%"
  },
  "evictionSoft": {
    "memory.available": "1Gi",
    "nodefs.available": "15%"
  },
  "evictionSoftGracePeriod": {
    "memory.available": "1m",
    "nodefs.available": "1m"
  }
}
```

**RCA Report Template:**
```markdown
## Incident Summary
- Occurrence time: 2024-01-15 14:30 PST
- Impact scope: 3 nodes, 45 Pods affected
- Resolution time: 2024-01-15 15:15 PST (MTTR: 45min)

## Timeline
- 14:30 - Alert triggered: NodeNotReady
- 14:35 - Initial analysis started
- 14:50 - Root cause identified: kubelet OOM due to memory pressure
- 15:00 - Node drain and restart
- 15:15 - Normalization confirmed

## Root Cause
Application with memory leak caused node memory exhaustion

## Preventive Measures
1. [Complete] Set memory limit on problematic application
2. [In Progress] Adjust node memory pressure alert threshold (90% -> 80%)
3. [Planned] Deploy Node Problem Detector
```

</details>
