# Amazon EKS 高级调试测验

本测验测试你对 Amazon EKS 高级调试技术的理解，包括事件响应、control plane 调试、node 故障排查、kubectl debug、PromQL 查询以及可观测性。

## 测验概览
- 事件响应流程
- EKS Control Plane 调试
- Node 和 kubelet 故障排查
- kubectl debug 命令用法
- PromQL 查询和指标分析
- 分布式追踪和日志分析

## 选择题

### 1. 应该在哪里检查 EKS API server audit logs？

A. /var/log/kubernetes/ 目录
B. Amazon CloudWatch Logs
C. etcd 数据库
D. kubectl logs 命令

<details>
<summary>查看答案</summary>

**答案：B. Amazon CloudWatch Logs**

**解释：**
EKS control plane logs 由 AWS 管理并发送到 CloudWatch Logs。Audit logs 可在 `/aws/eks/<cluster-name>/cluster` log group 中找到。

**日志类型：**
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

### 2. 使用 kubectl debug 向正在运行的 Pod 添加调试 container 时使用哪个 flag？

A. --attach
B. --copy-to
C. --ephemeral
D. --sidecar

<details>
<summary>查看答案</summary>

**答案：B. --copy-to**

**解释：**
`--copy-to` flag 会创建现有 Pod 的副本，并允许你添加调试 container 或修改后的设置。与 `--share-processes` 一起使用可启用 process namespace 共享。

```bash
# Add debug container to Pod copy
kubectl debug myapp-pod --copy-to=myapp-debug --container=debugger --image=busybox -- sh

# Share process namespace
kubectl debug myapp-pod --copy-to=myapp-debug --share-processes --container=debugger --image=busybox

# Direct debugging with Ephemeral container (no Pod copy)
kubectl debug -it myapp-pod --image=busybox --target=myapp-container
```

**关键选项：**
- `--copy-to`: 创建 Pod 副本
- `--share-processes`: 共享 process namespace
- `--target`: 指定目标 container（用于 ephemeral containers）

</details>

### 3. 当 node 处于 NotReady 状态时，应该首先检查什么？

A. Pod logs
B. kubelet 状态和 logs
C. etcd 状态
D. CoreDNS logs

<details>
<summary>查看答案</summary>

**答案：B. kubelet 状态和 logs**

**解释：**
node 变为 NotReady 的最常见原因是 kubelet 问题。当 kubelet 无法与 API server 通信时，node 状态会变为 NotReady。

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

**NotReady 检查清单：**
1. kubelet process 状态
2. 网络连接性（API server 访问）
3. 磁盘空间
4. 内存（OOM）
5. Container runtime 状态

</details>

### 4. 哪个 PromQL 查询可查找过去 5 分钟内 CPU utilization 超过 80% 的 Pods？

A. `cpu_usage > 80`
B. `rate(container_cpu_usage_seconds_total[5m]) > 0.8`
C. `sum(rate(container_cpu_usage_seconds_total[5m])) by (pod) / sum(kube_pod_container_resource_limits{resource="cpu"}) by (pod) > 0.8`
D. `container_cpu_percent > 80`

<details>
<summary>查看答案</summary>

**答案：C. `sum(rate(container_cpu_usage_seconds_total[5m])) by (pod) / sum(kube_pod_container_resource_limits{resource="cpu"}) by (pod) > 0.8`**

**解释：**
CPU utilization 是实际用量与 limit 的比值。`rate()` 函数计算每秒 CPU 用量，然后除以 limit 得到百分比。

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

### 5. 哪个工具不适合用于调试 EKS 中 node 之间的网络问题？

A. tcpdump
B. wireshark
C. 通过 kubectl exec 执行 ping/curl 测试
D. etcdctl

<details>
<summary>查看答案</summary>

**答案：D. etcdctl**

**解释：**
etcdctl 是用于管理 etcd 数据库的工具，与网络调试无关。并且在 EKS 中，etcd 由 AWS 管理，因此你无法直接访问它。

**网络调试工具：**
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

### 6. 在事件响应中，降低 MTTD (Mean Time To Detect) 的最有效方法是什么？

A. 增强手动监控
B. 将 alert thresholds 设置得非常低
C. 构建适当的 alerting rules 和自动化监控系统
D. 延长日志保留期

<details>
<summary>查看答案</summary>

**答案：C. 构建适当的 alerting rules 和自动化监控系统**

**解释：**
要降低 MTTD，需要适当的 alert thresholds 和自动化监控。过于敏感的 alerts 会导致 alert fatigue。

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

**MTTD 优化策略：**
- 基于 SLO 的 alerting
- Multi-window burn rate alerts
- Alert 优先级分类
- On-call rotation 和升级流程

</details>

### 7. 使用 kubectl debug 直接在 node 上创建调试 Pod 的命令是什么？

A. `kubectl debug node/<node-name> -it --image=busybox`
B. `kubectl exec node/<node-name> -- sh`
C. `kubectl attach node/<node-name>`
D. `kubectl run debug --node=<node-name>`

<details>
<summary>查看答案</summary>

**答案：A. `kubectl debug node/<node-name> -it --image=busybox`**

**解释：**
在 Kubernetes 1.20+ 中，`kubectl debug node/` 命令会在 node 上创建一个 privileged Pod，并可访问 host filesystem 和网络。

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

**重要说明：**
- Node 调试 Pods 以 privileged mode 运行
- 可访问 host namespaces
- 在 production environments 中使用 RBAC 限制访问

</details>

### 8. 在 distributed tracing 中，“Span”是什么意思？

A. 请求的总处理时间
B. 单个工作单元的时间测量
C. services 之间的网络延迟
D. log messages 的 timestamp

<details>
<summary>查看答案</summary>

**答案：B. 单个工作单元的时间测量**

**解释：**
Span 表示 distributed system 中的单个工作单元，包括 start time、end time 和 metadata。多个 Span 共同组成一个 Trace。

**Distributed Tracing 概念：**
- **Trace**: 表示整个请求流程的 Span 集合
- **Span**: 单个工作单元（例如 HTTP request、DB query）
- **Parent-Child relationship**: Span 之间的调用关系
- **Baggage**: 在 Span 之间传播的 context information

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

### 9. 用于调试 EKS 中 CoreDNS 问题的最有用命令是什么？

A. `kubectl logs -n kube-system -l k8s-app=kube-dns`
B. `kubectl describe service kubernetes`
C. `aws eks describe-cluster`
D. `kubectl get endpoints`

<details>
<summary>查看答案</summary>

**答案：A. `kubectl logs -n kube-system -l k8s-app=kube-dns`**

**解释：**
检查 CoreDNS Pod logs 可以揭示 DNS query 处理状态、errors 和 timeouts。

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

**常见 CoreDNS 问题：**
- Pod resource constraints（CPU/Memory）
- ConfigMap 配置错误
- Upstream DNS 连接问题
- Cluster IP service 连接性问题

</details>

### 10. 哪个 kubectl 命令显示实时 Pod resource usage？

A. `kubectl describe pod`
B. `kubectl top pods`
C. `kubectl get pods -o wide`
D. `kubectl logs`

<details>
<summary>查看答案</summary>

**答案：B. `kubectl top pods`**

**解释：**
`kubectl top` 命令显示 Metrics Server 收集的 resource usage 数据。你可以实时检查 CPU 和 memory 用量。

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

**先决条件：**
- 必须安装 Metrics Server
- `kubectl top` 只提供实时快照（无历史记录）
- 使用 Prometheus + Grafana 进行长期监控

</details>

## 简答题

### 1. 在 CloudWatch Logs 中查看 EKS control plane logs 的 log group 名称模式是什么？

<details>
<summary>查看答案</summary>

**答案：** `/aws/eks/<cluster-name>/cluster`

**解释：**
EKS control plane logs 会自动发送到此 log group。

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

### 2. 在 Kubernetes 中启用 Ephemeral Containers 需要哪个 feature gate 名称？

<details>
<summary>查看答案</summary>

**答案：** `EphemeralContainers`（在 Kubernetes 1.25+ 中默认启用）

**解释：**
此 feature 在 Kubernetes 1.23 中成为 beta，并在 1.25 中成为 GA (Generally Available)，且默认启用。在 EKS 1.25+ 中无需额外配置。

```bash
# Add Ephemeral Container
kubectl debug -it <pod-name> --image=busybox --target=<container-name>

# Check Ephemeral Containers
kubectl get pod <pod-name> -o jsonpath='{.spec.ephemeralContainers}'

# List Ephemeral Containers added to Pod
kubectl describe pod <pod-name> | grep -A 10 "Ephemeral Containers"
```

</details>

### 3. PromQL 中 rate() 和 irate() 函数有什么区别？

<details>
<summary>查看答案</summary>

**答案：**
- `rate()`: 计算整个指定时间范围内的平均变化率（平滑）
- `irate()`: 仅使用最后两个数据点计算即时变化率（波动较大）

**用法示例：**
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

**选择指南：**
- Alert rules：使用 `rate()`（降低噪声）
- 调试/突然变化检测：使用 `irate()`
- 长期趋势分析：使用 `rate()`

</details>

### 4. 使用 kubectl debug 连接到 node 时，host filesystem 挂载到哪个路径？

<details>
<summary>查看答案</summary>

**答案：** `/host`

**解释：**
当使用 `kubectl debug node/` 创建 Pod 时，host 的 root filesystem 会挂载到 `/host`。

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

### 5. 在事件响应中，MTTR (Mean Time To Resolve) 的两个主要组成部分是什么？

<details>
<summary>查看答案</summary>

**答案：**
1. **MTTD (Mean Time To Detect)**: 从问题发生到被检测到的时间
2. **MTTI (Mean Time To Investigate/Identify)**: 从检测到问题到识别 root cause 并解决的时间

或者：
- MTTD + MTTI + MTTFix（实际修复时间）

**MTTR 改进策略：**
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

## 动手练习

### 1. 编写一个满足以下要求的 PromQL 查询：
- 查找过去 5 分钟内在 production namespace 中已重启的 containers
- 筛选 restart count 为 2 次或更多的项

<details>
<summary>查看答案</summary>

```promql
# Containers with restart count >= 2 over last 5 minutes
increase(kube_pod_container_status_restarts_total{namespace="production"}[5m]) >= 2
```

**变体查询：**
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

**用于 Grafana Dashboard：**
```promql
# Time series graph
rate(kube_pod_container_status_restarts_total{namespace="production"}[5m])

# Table (current status)
kube_pod_container_status_restarts_total{namespace="production"}
```

</details>

### 2. 编写用于调试处于 CrashLoopBackOff 状态的 Pod 的逐步命令。

<details>
<summary>查看答案</summary>

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

**常见 CrashLoopBackOff 原因：**
- 无效的配置文件
- 缺失 environment variables 或 secrets
- Resource constraints（OOM Kill）
- Health check 失败
- 依赖 service 连接失败

</details>

### 3. 编写一个 CloudWatch Logs Insights 查询，用于搜索过去一小时内 EKS audit logs 中的 permission denied (403) 事件。

<details>
<summary>查看答案</summary>

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

**通过 AWS CLI 执行：**
```bash
aws logs start-query \
  --log-group-name "/aws/eks/my-cluster/cluster" \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter @logStream like /kube-apiserver-audit/ | filter @message like /"code":403/ | sort @timestamp desc | limit 50'
```

</details>

## 高级问题

### 1. 在 microservices 架构中，某个特定 API 出现间歇性的响应缓慢。请制定一套使用 distributed tracing、metrics 和 logs 的综合调试策略。

<details>
<summary>查看答案</summary>

**综合调试策略：间歇性延迟分析**

**步骤 1：定义问题范围（Metrics）**

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

**步骤 2：使用 Distributed Tracing 识别瓶颈**

```yaml
# Jaeger Query Strategy
# 1. Search slow traces (>2s)
service=api-gateway minDuration=2s

# 2. Traces with errors
service=api-gateway tags={"error":"true"}

# 3. Traces for specific endpoint
service=api-gateway operation="GET /api/products"
```

**步骤 3：Log 关联分析**

```bash
# Search related logs by Trace ID
kubectl logs -l app=api-gateway | grep "trace_id=abc123"

# CloudWatch Logs Insights
fields @timestamp, @message
| filter @message like /trace_id=abc123/
| sort @timestamp asc
```

**步骤 4：Infrastructure Level 分析**

```promql
# Check Pod CPU Throttling
rate(container_cpu_cfs_throttled_seconds_total[5m])

# Network latency
rate(container_network_receive_bytes_total[5m])

# GC impact analysis (Java)
rate(jvm_gc_pause_seconds_sum[5m])
```

**步骤 5：集成 Dashboard**

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

**步骤 6：自动化 Anomaly Detection**

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

**分析检查清单：**
- [ ] 是否只发生在特定 endpoints？
- [ ] 是否集中在特定时间？
- [ ] 是否由某个特定 downstream service 引起？
- [ ] Resource limitation（CPU throttling）是否造成影响？
- [ ] 是否是 GC 或 JVM 相关问题？
- [ ] 是否是 network level 问题？

</details>

### 2. EKS cluster 中的 nodes 间歇性变为 NotReady。建立一个系统化的 Root Cause Analysis (RCA) 流程和预防措施。

<details>
<summary>查看答案</summary>

**Root Cause Analysis (RCA) 流程**

**阶段 1：数据收集**

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

**阶段 2：System Log 分析**

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

**阶段 3：网络分析**

```bash
# Check API server connectivity
curl -k https://kubernetes.default.svc.cluster.local/healthz

# Check VPC CNI status
kubectl logs -n kube-system -l k8s-app=aws-node --tail=100

# Check ENI and IP allocation status
aws ec2 describe-network-interfaces \
  --filters Name=attachment.instance-id,Values=<instance-id>
```

**阶段 4：Resource Pressure 分析**

```promql
# Node memory pressure
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 90

# Node disk pressure
(1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) * 100 > 85

# Node PID pressure
node_processes_threads / node_processes_max_threads * 100 > 80
```

**阶段 5：Root Cause 分类**

| 类别 | 可能原因 | 验证方法 |
|---------|------------|----------|
| Resource | OOM Kill | `dmesg \| grep -i oom` |
| Resource | Disk full | `df -h` |
| Network | CNI 问题 | aws-node logs |
| Network | API server 连接 | curl healthz |
| System | kubelet crash | `journalctl -u kubelet` |
| Infrastructure | EC2 instance 问题 | CloudWatch metrics |

**阶段 6：预防措施**

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

**RCA Report Template：**
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
