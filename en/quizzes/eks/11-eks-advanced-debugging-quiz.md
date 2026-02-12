# Amazon EKS Advanced Debugging Quiz

This quiz tests your understanding of advanced debugging techniques in Amazon EKS, including incident response, control plane debugging, node troubleshooting, kubectl debug, PromQL queries, and observability.

## Quiz Overview
- Incident Response Process
- EKS Control Plane Debugging
- Node and kubelet Troubleshooting
- kubectl debug Command Usage
- PromQL Queries and Metric Analysis
- Distributed Tracing and Log Analysis

## Multiple Choice Questions

### 1. Where should you check EKS API server audit logs?

A. /var/log/kubernetes/ directory
B. Amazon CloudWatch Logs
C. etcd database
D. kubectl logs command

<details>
<summary>View Answer</summary>

**Answer: B. Amazon CloudWatch Logs**

**Explanation:**
EKS control plane logs are managed by AWS and sent to CloudWatch Logs. Audit logs can be found in the `/aws/eks/<cluster-name>/cluster` log group.

**Log Types:**
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

### 2. What flag is used to add a debugging container to a running Pod with kubectl debug?

A. --attach
B. --copy-to
C. --ephemeral
D. --sidecar

<details>
<summary>View Answer</summary>

**Answer: B. --copy-to**

**Explanation:**
The `--copy-to` flag creates a copy of an existing Pod and allows you to add debugging containers or modified settings. Using it with `--share-processes` enables process namespace sharing.

```bash
# Add debug container to Pod copy
kubectl debug myapp-pod --copy-to=myapp-debug --container=debugger --image=busybox -- sh

# Share process namespace
kubectl debug myapp-pod --copy-to=myapp-debug --share-processes --container=debugger --image=busybox

# Direct debugging with Ephemeral container (no Pod copy)
kubectl debug -it myapp-pod --image=busybox --target=myapp-container
```

**Key Options:**
- `--copy-to`: Create Pod copy
- `--share-processes`: Share process namespace
- `--target`: Specify target container (for ephemeral containers)

</details>

### 3. What should you check first when a node is in NotReady state?

A. Pod logs
B. kubelet status and logs
C. etcd status
D. CoreDNS logs

<details>
<summary>View Answer</summary>

**Answer: B. kubelet status and logs**

**Explanation:**
The most common cause of a node becoming NotReady is kubelet issues. When kubelet cannot communicate with the API server, the node status changes to NotReady.

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

**NotReady Checklist:**
1. kubelet process status
2. Network connectivity (API server access)
3. Disk space
4. Memory (OOM)
5. Container runtime status

</details>

### 4. What PromQL query finds Pods with CPU utilization above 80% over the last 5 minutes?

A. `cpu_usage > 80`
B. `rate(container_cpu_usage_seconds_total[5m]) > 0.8`
C. `sum(rate(container_cpu_usage_seconds_total[5m])) by (pod) / sum(kube_pod_container_resource_limits{resource="cpu"}) by (pod) > 0.8`
D. `container_cpu_percent > 80`

<details>
<summary>View Answer</summary>

**Answer: C. `sum(rate(container_cpu_usage_seconds_total[5m])) by (pod) / sum(kube_pod_container_resource_limits{resource="cpu"}) by (pod) > 0.8`**

**Explanation:**
CPU utilization is the ratio of actual usage to the limit. The `rate()` function calculates CPU usage per second, which is then divided by the limit to get the percentage.

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

### 5. Which tool is NOT suitable for debugging network issues between nodes in EKS?

A. tcpdump
B. wireshark
C. ping/curl tests via kubectl exec
D. etcdctl

<details>
<summary>View Answer</summary>

**Answer: D. etcdctl**

**Explanation:**
etcdctl is a tool for managing the etcd database and is unrelated to network debugging. In EKS, etcd is managed by AWS so you cannot access it directly anyway.

**Network Debugging Tools:**
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

### 6. What is the most effective way to reduce MTTD (Mean Time To Detect) in incident response?

A. Enhanced manual monitoring
B. Set alert thresholds very low
C. Build appropriate alerting rules and automated monitoring systems
D. Extend log retention period

<details>
<summary>View Answer</summary>

**Answer: C. Build appropriate alerting rules and automated monitoring systems**

**Explanation:**
To reduce MTTD, you need appropriate alert thresholds and automated monitoring. Overly sensitive alerts cause alert fatigue.

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

**MTTD Optimization Strategies:**
- SLO-based alerting
- Multi-window burn rate alerts
- Alert priority classification
- On-call rotation and escalation

</details>

### 7. What is the command to create a debugging Pod directly on a node with kubectl debug?

A. `kubectl debug node/<node-name> -it --image=busybox`
B. `kubectl exec node/<node-name> -- sh`
C. `kubectl attach node/<node-name>`
D. `kubectl run debug --node=<node-name>`

<details>
<summary>View Answer</summary>

**Answer: A. `kubectl debug node/<node-name> -it --image=busybox`**

**Explanation:**
In Kubernetes 1.20+, the `kubectl debug node/` command creates a privileged Pod on the node with access to the host filesystem and network.

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

**Important Notes:**
- Node debugging Pods run in privileged mode
- Have access to host namespaces
- Restrict access with RBAC in production environments

</details>

### 8. What does "Span" mean in distributed tracing?

A. Total processing time of a request
B. Time measurement of a single unit of work
C. Network latency between services
D. Timestamp of log messages

<details>
<summary>View Answer</summary>

**Answer: B. Time measurement of a single unit of work**

**Explanation:**
A Span represents a single unit of work in a distributed system, including start time, end time, and metadata. Multiple Spans together form a Trace.

**Distributed Tracing Concepts:**
- **Trace**: Collection of Spans representing the entire request flow
- **Span**: Single unit of work (e.g., HTTP request, DB query)
- **Parent-Child relationship**: Call relationships between Spans
- **Baggage**: Context information propagated between Spans

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

### 9. What is the most useful command for debugging CoreDNS issues in EKS?

A. `kubectl logs -n kube-system -l k8s-app=kube-dns`
B. `kubectl describe service kubernetes`
C. `aws eks describe-cluster`
D. `kubectl get endpoints`

<details>
<summary>View Answer</summary>

**Answer: A. `kubectl logs -n kube-system -l k8s-app=kube-dns`**

**Explanation:**
Checking CoreDNS Pod logs reveals DNS query processing status, errors, and timeouts.

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

**Common CoreDNS Issues:**
- Pod resource constraints (CPU/Memory)
- ConfigMap configuration errors
- Upstream DNS connection issues
- Cluster IP service connectivity problems

</details>

### 10. What kubectl command shows real-time Pod resource usage?

A. `kubectl describe pod`
B. `kubectl top pods`
C. `kubectl get pods -o wide`
D. `kubectl logs`

<details>
<summary>View Answer</summary>

**Answer: B. `kubectl top pods`**

**Explanation:**
The `kubectl top` command displays resource usage data collected by Metrics Server. You can check CPU and memory usage in real-time.

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

**Prerequisites:**
- Metrics Server must be installed
- `kubectl top` only provides real-time snapshots (no history)
- Use Prometheus + Grafana for long-term monitoring

</details>

## Short Answer Questions

### 1. What is the log group name pattern for viewing EKS control plane logs in CloudWatch Logs?

<details>
<summary>View Answer</summary>

**Answer:** `/aws/eks/<cluster-name>/cluster`

**Explanation:**
EKS control plane logs are automatically sent to this log group.

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

### 2. What feature gate name is needed to enable Ephemeral Containers in Kubernetes?

<details>
<summary>View Answer</summary>

**Answer:** `EphemeralContainers` (enabled by default in Kubernetes 1.25+)

**Explanation:**
This feature became beta in Kubernetes 1.23 and GA (Generally Available) in 1.25, enabled by default. No additional configuration needed in EKS 1.25+.

```bash
# Add Ephemeral Container
kubectl debug -it <pod-name> --image=busybox --target=<container-name>

# Check Ephemeral Containers
kubectl get pod <pod-name> -o jsonpath='{.spec.ephemeralContainers}'

# List Ephemeral Containers added to Pod
kubectl describe pod <pod-name> | grep -A 10 "Ephemeral Containers"
```

</details>

### 3. What is the difference between rate() and irate() functions in PromQL?

<details>
<summary>View Answer</summary>

**Answer:**
- `rate()`: Calculates average rate of change over the entire specified time range (smooth)
- `irate()`: Calculates instant rate of change using only the last two data points (volatile)

**Usage Examples:**
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

**Selection Guide:**
- Alert rules: Use `rate()` (reduces noise)
- Debugging/sudden change detection: Use `irate()`
- Long-term trend analysis: Use `rate()`

</details>

### 4. What path is the host filesystem mounted to when connecting to a node with kubectl debug?

<details>
<summary>View Answer</summary>

**Answer:** `/host`

**Explanation:**
When a Pod is created with `kubectl debug node/`, the host's root filesystem is mounted at `/host`.

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

### 5. What are the two main components of MTTR (Mean Time To Resolve) in incident response?

<details>
<summary>View Answer</summary>

**Answer:**
1. **MTTD (Mean Time To Detect)**: Time from issue occurrence to detection
2. **MTTI (Mean Time To Investigate/Identify)**: Time from detection to root cause identification and resolution

Or:
- MTTD + MTTI + MTTFix (actual fix time)

**MTTR Improvement Strategies:**
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

## Hands-on Exercises

### 1. Write a PromQL query that meets the following requirements:
- Find containers that have restarted in the production namespace over the last 5 minutes
- Filter for restart count of 2 or more

<details>
<summary>View Answer</summary>

```promql
# Containers with restart count >= 2 over last 5 minutes
increase(kube_pod_container_status_restarts_total{namespace="production"}[5m]) >= 2
```

**Variant Queries:**
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

**For Grafana Dashboard:**
```promql
# Time series graph
rate(kube_pod_container_status_restarts_total{namespace="production"}[5m])

# Table (current status)
kube_pod_container_status_restarts_total{namespace="production"}
```

</details>

### 2. Write step-by-step commands for debugging a Pod in CrashLoopBackOff state.

<details>
<summary>View Answer</summary>

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

**Common CrashLoopBackOff Causes:**
- Invalid configuration files
- Missing environment variables or secrets
- Resource constraints (OOM Kill)
- Health check failures
- Dependency service connection failures

</details>

### 3. Write a CloudWatch Logs Insights query to search for permission denied (403) events in EKS audit logs over the last hour.

<details>
<summary>View Answer</summary>

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

**Execute via AWS CLI:**
```bash
aws logs start-query \
  --log-group-name "/aws/eks/my-cluster/cluster" \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter @logStream like /kube-apiserver-audit/ | filter @message like /"code":403/ | sort @timestamp desc | limit 50'
```

</details>

## Advanced Questions

### 1. In a microservices architecture, a specific API is experiencing intermittent slow response times. Develop a comprehensive debugging strategy using distributed tracing, metrics, and logs.

<details>
<summary>View Answer</summary>

**Comprehensive Debugging Strategy: Intermittent Latency Analysis**

**Step 1: Define Problem Scope (Metrics)**

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

**Step 2: Identify Bottlenecks with Distributed Tracing**

```yaml
# Jaeger Query Strategy
# 1. Search slow traces (>2s)
service=api-gateway minDuration=2s

# 2. Traces with errors
service=api-gateway tags={"error":"true"}

# 3. Traces for specific endpoint
service=api-gateway operation="GET /api/products"
```

**Step 3: Log Correlation Analysis**

```bash
# Search related logs by Trace ID
kubectl logs -l app=api-gateway | grep "trace_id=abc123"

# CloudWatch Logs Insights
fields @timestamp, @message
| filter @message like /trace_id=abc123/
| sort @timestamp asc
```

**Step 4: Infrastructure Level Analysis**

```promql
# Check Pod CPU Throttling
rate(container_cpu_cfs_throttled_seconds_total[5m])

# Network latency
rate(container_network_receive_bytes_total[5m])

# GC impact analysis (Java)
rate(jvm_gc_pause_seconds_sum[5m])
```

**Step 5: Integrated Dashboard**

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

**Step 6: Automated Anomaly Detection**

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

**Analysis Checklist:**
- [ ] Is it occurring only on specific endpoints?
- [ ] Is it concentrated at specific times?
- [ ] Is a specific downstream service the cause?
- [ ] Is resource limitation (CPU throttling) affecting it?
- [ ] Is it a GC or JVM related issue?
- [ ] Is it a network level issue?

</details>

### 2. Nodes in an EKS cluster are intermittently becoming NotReady. Establish a systematic Root Cause Analysis (RCA) process and preventive measures.

<details>
<summary>View Answer</summary>

**Root Cause Analysis (RCA) Process**

**Phase 1: Data Collection**

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

**Phase 2: System Log Analysis**

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

**Phase 3: Network Analysis**

```bash
# Check API server connectivity
curl -k https://kubernetes.default.svc.cluster.local/healthz

# Check VPC CNI status
kubectl logs -n kube-system -l k8s-app=aws-node --tail=100

# Check ENI and IP allocation status
aws ec2 describe-network-interfaces \
  --filters Name=attachment.instance-id,Values=<instance-id>
```

**Phase 4: Resource Pressure Analysis**

```promql
# Node memory pressure
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 90

# Node disk pressure
(1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) * 100 > 85

# Node PID pressure
node_processes_threads / node_processes_max_threads * 100 > 80
```

**Phase 5: Root Cause Classification**

| Category | Possible Cause | Verification Method |
|---------|------------|----------|
| Resource | OOM Kill | `dmesg \| grep -i oom` |
| Resource | Disk full | `df -h` |
| Network | CNI issue | aws-node logs |
| Network | API server connection | curl healthz |
| System | kubelet crash | `journalctl -u kubelet` |
| Infrastructure | EC2 instance issue | CloudWatch metrics |

**Phase 6: Preventive Measures**

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
