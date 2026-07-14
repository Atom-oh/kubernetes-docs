# リソース最適化: Requests/Limits、JVM チューニング、フレームワーク別ガイド

> **サポート対象バージョン**: Kubernetes 1.28+, Java 17+, Python 3.11+, Node.js 20+, Go 1.21+
> **最終更新**: February 21, 2026

< [前へ: Observability Stack Operations](./09-observability-stack.md) | [目次](./README.md) | [次へ: EKS Upgrades](./11-upgrade-operations.md) >

---

## 目次

- [リソース設定の基礎](#resource-configuration-fundamentals)
- [最適なリソース計算](#optimal-resource-calculation)
- [JVM ワークロード最適化](#jvm-workload-optimization)
- [Python/Node.js ワークロード](#pythonnodejs-workloads)
- [Go/Rust ワークロード](#gorust-workloads)
- [リソース監視ダッシュボード](#resource-monitoring-dashboards)
- [Auto Mode におけるリソース最適化](#resource-optimization-in-auto-mode)

---

## リソース設定の基礎

### Requests と Limits

requests と limits の違いを理解することは、Kubernetes で適切なリソース管理を行ううえで重要です。

| 観点 | Requests | Limits |
|--------|----------|--------|
| **目的** | スケジューリングの保証 | 許可される最大値 |
| **Scheduler** | node 配置に使用 | 使用されない |
| **適用** | ソフト (予約) | ハード (cgroups によって強制) |
| **オーバーコミット** | request を超過可能 | limit は超過不可 |
| **OOM Kill** | トリガーされない | 超過時に OOM をトリガー |
| **Throttling** | 適用されない | limit で CPU が throttling される |

```yaml
# Resource configuration example
apiVersion: v1
kind: Pod
metadata:
  name: resource-demo
spec:
  containers:
    - name: app
      image: myapp:latest
      resources:
        requests:
          cpu: "500m"      # 0.5 CPU cores guaranteed
          memory: "512Mi"  # 512 MiB guaranteed
        limits:
          cpu: "1000m"     # Max 1 CPU core
          memory: "1Gi"    # Max 1 GiB, OOM killed if exceeded
```

### Quality of Service (QoS) クラス

Kubernetes はリソース設定に基づいて QoS クラスを割り当てます。

| QoS クラス | 基準 | OOM 優先度 | ユースケース |
|-----------|----------|--------------|----------|
| **Guaranteed** | すべての container で requests = limits | 最低 (最後に kill される) | 重要な workload |
| **Burstable** | requests < limits、または一部のみ設定 | 中 | ほとんどのアプリケーション |
| **BestEffort** | requests も limits もなし | 最高 (最初に kill される) | Batch job、開発用 Pod |

```yaml
# Guaranteed QoS - requests equal limits
apiVersion: v1
kind: Pod
metadata:
  name: guaranteed-pod
spec:
  containers:
    - name: critical-app
      resources:
        requests:
          cpu: "1"
          memory: "1Gi"
        limits:
          cpu: "1"
          memory: "1Gi"
---
# Burstable QoS - requests less than limits
apiVersion: v1
kind: Pod
metadata:
  name: burstable-pod
spec:
  containers:
    - name: normal-app
      resources:
        requests:
          cpu: "500m"
          memory: "512Mi"
        limits:
          cpu: "2"
          memory: "2Gi"
---
# BestEffort QoS - no resource specifications
apiVersion: v1
kind: Pod
metadata:
  name: besteffort-pod
spec:
  containers:
    - name: batch-job
      image: batch:latest
      # No resources specified
```

### CPU Throttling と CFS Bandwidth

Linux は CPU 管理に Completely Fair Scheduler (CFS) を使用します。

```
┌─────────────────────────────────────────────────────────────────┐
│                    CFS Bandwidth Control                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  CPU Limit = 1000m (1 core)                                     │
│                                                                  │
│  CFS Period: 100ms (default)                                    │
│  CFS Quota:  100ms (limit * period)                             │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 100ms period                                              │   │
│  │ ┌─────────────┐                                          │   │
│  │ │   100ms     │ quota exhausted → THROTTLED              │   │
│  │ │   running   │                                          │   │
│  │ └─────────────┘────────────────────────────────────────  │   │
│  │ 0            100ms                              200ms     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  With 500m limit:                                               │
│  CFS Quota: 50ms → Can only use 50ms per 100ms period          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Throttling の影響**:

- CPU throttling はスループット低下ではなく、**レイテンシの急増**を引き起こします
- 平均 CPU が低くても、アプリケーションが遅く見えることがあります
- GC 集約型アプリケーションは特に影響を受けます
- throttling を避けるため、limit は観測された peak より 20-50% 高く設定します

**Throttling の検出**:

```promql
# Throttled seconds per second (should be 0)
rate(container_cpu_cfs_throttled_seconds_total[5m])

# Throttle percentage
rate(container_cpu_cfs_throttled_periods_total[5m])
/ rate(container_cpu_cfs_periods_total[5m]) * 100
```

### メモリ OOMKill の挙動

container がメモリ limit を超過すると、次のようになります。

1. Kernel が SIGKILL を送信します (捕捉できません)
2. Container は即座に終了します
3. Pod status に `OOMKilled` と表示されます
4. Kubernetes は `restartPolicy` に基づいて container を再起動します

```yaml
# OOMKill-resistant configuration
apiVersion: v1
kind: Pod
metadata:
  name: memory-safe
spec:
  containers:
    - name: app
      resources:
        requests:
          memory: "1Gi"   # Scheduling amount
        limits:
          memory: "1.5Gi" # 50% headroom for spikes
      # Use memory-based liveness probe
      livenessProbe:
        exec:
          command:
            - /bin/sh
            - -c
            - "[ $(cat /sys/fs/cgroup/memory/memory.usage_in_bytes) -lt 1400000000 ]"
        periodSeconds: 10
```

### よくあるアンチパターン

| アンチパターン | 問題 | 解決策 |
|--------------|---------|----------|
| **limits なし** | Noisy neighbor、node の不安定化 | 常に memory limits を設定する |
| **Limits = requests = 観測最大値** | 過剰プロビジョニング、リソースの無駄 | requests は p70、limits は p99 に設定する |
| **レイテンシに敏感な app で CPU limits** | Throttling がレイテンシ急増を引き起こす | CPU limits の削除を検討する |
| **Memory limit = JVM heap** | non-heap による OOMKill | Limit = heap + 25% overhead |
| **すべての workload に同じ設定** | リソースの不一致 | workload type ごとに profile する |
| **requests >> 実使用量** | スケジューリング失敗、無駄 | VPA recommendations を使用する |

**正しいリソースサイジング**:

```yaml
# Anti-pattern: Oversized resources
resources:
  requests:
    cpu: "4"
    memory: "8Gi"
  limits:
    cpu: "4"
    memory: "8Gi"
# Actual usage: 500m CPU, 1Gi memory → 87% waste

# Better: Right-sized based on profiling
resources:
  requests:
    cpu: "500m"      # p70 usage
    memory: "1Gi"    # p70 usage
  limits:
    cpu: "1500m"     # p99 usage + headroom
    memory: "1.5Gi"  # p99 usage + 25% headroom
```

---

## 最適なリソース計算

### Vertical Pod Autoscaler (VPA)

VPA は過去のリソース使用量を分析し、recommendation を提供します。

```yaml
# vpa-recommender.yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: api-server-vpa
  namespace: production
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-server
  updatePolicy:
    updateMode: "Off"  # Recommendation only, no auto-updates
  resourcePolicy:
    containerPolicies:
      - containerName: api-server
        minAllowed:
          cpu: 100m
          memory: 128Mi
        maxAllowed:
          cpu: 4
          memory: 8Gi
        controlledResources: ["cpu", "memory"]
        controlledValues: RequestsAndLimits
```

**VPA Update Modes**:

| Mode | 動作 | ユースケース |
|------|----------|----------|
| `Off` | Recommendations のみ | 本番分析 |
| `Initial` | Pod 作成時のみ設定 | Stateful workload |
| `Recreate` | Pod を evict して再作成 | Stateless、再起動に耐えられる場合 |
| `Auto` | 将来の in-place support を伴う再作成 | 将来対応 |

**VPA Recommendations の確認**:

```bash
# Get VPA recommendations
kubectl describe vpa api-server-vpa

# Output example:
# Recommendation:
#   Container Recommendations:
#     Container Name: api-server
#     Lower Bound:
#       Cpu:     250m
#       Memory:  512Mi
#     Target:            # Use this for requests
#       Cpu:     500m
#       Memory:  1Gi
#     Uncapped Target:   # Without min/max constraints
#       Cpu:     500m
#       Memory:  1Gi
#     Upper Bound:       # Use this for limits
#       Cpu:     2
#       Memory:  2Gi
```

### Goldilocks Dashboard

Goldilocks はすべての deployment に対して VPA を作成し、dashboard を提供します。

```bash
# Install Goldilocks
helm repo add fairwinds-stable https://charts.fairwinds.com/stable
helm install goldilocks fairwinds-stable/goldilocks \
  --namespace goldilocks \
  --create-namespace

# Enable for a namespace
kubectl label namespace production goldilocks.fairwinds.com/enabled=true

# Access dashboard
kubectl port-forward -n goldilocks svc/goldilocks-dashboard 8080:80
```

### PromQL リソース分析

**CPU 分析 (目標 70-80% utilization)**:

```promql
# Current CPU utilization percentage
sum(rate(container_cpu_usage_seconds_total{namespace="production", container!=""}[5m]))
by (pod, container)
/
sum(kube_pod_container_resource_requests{namespace="production", resource="cpu"})
by (pod, container)
* 100

# P95 CPU usage over 7 days
quantile_over_time(0.95,
  sum(rate(container_cpu_usage_seconds_total{namespace="production", container!=""}[5m]))
  by (pod, container)[7d:1h]
)

# Recommended CPU request (P70)
quantile_over_time(0.70,
  sum(rate(container_cpu_usage_seconds_total{namespace="production", container!=""}[5m]))
  by (pod, container)[7d:1h]
)

# Recommended CPU limit (P99 + 20%)
quantile_over_time(0.99,
  sum(rate(container_cpu_usage_seconds_total{namespace="production", container!=""}[5m]))
  by (pod, container)[7d:1h]
) * 1.2
```

**メモリ分析 (目標は最大 utilization 80%)**:

```promql
# Current memory utilization
sum(container_memory_working_set_bytes{namespace="production", container!=""})
by (pod, container)
/
sum(kube_pod_container_resource_requests{namespace="production", resource="memory"})
by (pod, container)
* 100

# P95 memory usage over 7 days
quantile_over_time(0.95,
  sum(container_memory_working_set_bytes{namespace="production", container!=""})
  by (pod, container)[7d:1h]
)

# Recommended memory request (P80)
quantile_over_time(0.80,
  sum(container_memory_working_set_bytes{namespace="production", container!=""})
  by (pod, container)[7d:1h]
)

# Recommended memory limit (P99 + 25%)
quantile_over_time(0.99,
  sum(container_memory_working_set_bytes{namespace="production", container!=""})
  by (pod, container)[7d:1h]
) * 1.25
```

### Minimum Replicas の計算

```promql
# Required replicas for target CPU utilization (70%)
ceil(
  sum(rate(container_cpu_usage_seconds_total{namespace="production", container="api-server"}[5m]))
  /
  (0.70 * avg(kube_pod_container_resource_requests{namespace="production", container="api-server", resource="cpu"}))
)

# Required replicas based on request rate (100 req/s per pod target)
ceil(
  sum(rate(http_requests_total{namespace="production", service="api-server"}[5m]))
  / 100
)
```

### リソースサイジングチェックリスト

| Workload Type | CPU Request | CPU Limit | Memory Request | Memory Limit |
|---------------|-------------|-----------|----------------|--------------|
| **API Service** | P70 usage | P99 + 50% またはなし | P80 usage | P99 + 25% |
| **Worker/Consumer** | P70 usage | P99 + 20% | P80 usage | P99 + 25% |
| **JVM Application** | P70 usage | P99 + 50% | Heap + 40% | Heap + 50% |
| **ML Inference** | P70 usage | P99 + 100% | Model size + 50% | Model size + 100% |
| **Batch Job** | Average usage | 2x average | Peak usage | Peak + 20% |
| **Sidecar (envoy)** | 100m | 500m | 128Mi | 256Mi |

---

## JVM ワークロード最適化

### Container 内の JVM メモリモデル

JVM メモリを理解することは、適切な container sizing に不可欠です。

```
┌─────────────────────────────────────────────────────────────────┐
│                    Container Memory Limit                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    JVM Process Memory                      │  │
│  │                                                            │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │              Heap Memory (MaxRAMPercentage)          │  │  │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌────────────┐   │  │  │
│  │  │  │    Eden     │  │  Survivor   │  │   Old Gen  │   │  │  │
│  │  │  │   Space     │  │   Spaces    │  │            │   │  │  │
│  │  │  └─────────────┘  └─────────────┘  └────────────┘   │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │                                                            │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │           Non-Heap Memory (~25% overhead)            │  │  │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │  │  │
│  │  │  │ Metaspace│ │  Code    │ │  Thread  │ │ Native │  │  │  │
│  │  │  │          │ │  Cache   │ │  Stacks  │ │ Memory │  │  │  │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └────────┘  │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │                                                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Remaining: Kernel buffers, page cache                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

Memory Limit = Heap (MaxRAMPercentage) + Non-Heap Overhead (~25%)
             = Heap * 1.25 to Heap * 1.40
```

### MaxRAMPercentage 設定

**75% が最適な理由**:

| Percentage | Heap Size (1Gi container) | Non-Heap Available | Risk |
|------------|---------------------------|-------------------|------|
| 50% | 512Mi | 512Mi | Heap の利用不足 |
| 75% | 768Mi | 256Mi | 最適なバランス |
| 80% | 819Mi | 205Mi | わずかな OOM リスク |
| 90% | 921Mi | 102Mi | 高い OOM リスク |

```bash
# JVM arguments for containers
JAVA_OPTS="-XX:+UseContainerSupport \
           -XX:MaxRAMPercentage=75.0 \
           -XX:InitialRAMPercentage=50.0 \
           -XX:MinRAMPercentage=50.0"
```

### UseContainerSupport

Java 11+ は `-XX:+UseContainerSupport` (デフォルトで有効) により container limits を自動検出します。

```bash
# Verify container detection
java -XX:+PrintFlagsFinal -version | grep -i container
# Output: bool UseContainerSupport = true

# Check detected memory
java -XshowSettings:system -version 2>&1 | grep -A5 "Operating System"
```

### GC アルゴリズムの選択

| Algorithm | 最適な用途 | Heap Size | Pause Target | CPU Overhead |
|-----------|----------|-----------|--------------|--------------|
| **G1GC** | 汎用 | 4-64GB | 200ms | 中 |
| **ZGC** | 低レイテンシ | 8GB-16TB | <10ms | 高め |
| **Shenandoah** | 低レイテンシ | 任意 | <10ms | 高め |
| **ParallelGC** | スループット | Small-Medium | 保証なし | 低め |
| **SerialGC** | 小さい heap | <100MB | 該当なし | 最低 |

**G1GC 設定** (推奨デフォルト):

```bash
JAVA_OPTS="-XX:+UseG1GC \
           -XX:MaxGCPauseMillis=200 \
           -XX:G1HeapRegionSize=16m \
           -XX:G1ReservePercent=10 \
           -XX:ParallelGCThreads=4 \
           -XX:ConcGCThreads=2"
```

**ZGC 設定** (低レイテンシ):

```bash
JAVA_OPTS="-XX:+UseZGC \
           -XX:+ZGenerational \
           -XX:SoftMaxHeapSize=6g \
           -XX:ZCollectionInterval=0"
```

**Shenandoah 設定**:

```bash
JAVA_OPTS="-XX:+UseShenandoahGC \
           -XX:ShenandoahGCHeuristics=adaptive \
           -XX:ShenandoahGuaranteedGCInterval=30000"
```

### CPU Shares と CFS Quota

JVM GC threads は CPU 制約の影響を受けます。

```
┌─────────────────────────────────────────────────────────────────┐
│                   CPU Limit Impact on GC                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  CPU Limit: 2 cores                                             │
│  Default GC Threads: min(cores, 8) = 2                          │
│                                                                  │
│  Problem: GC threads compete with application threads           │
│                                                                  │
│  Timeline during GC:                                            │
│  ├────────────────────────────────────────────────────────────┤ │
│  │ App │ GC │ App │ GC │ App │ GC │ App │ Throttled │ App │   │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │                  CFS Period (100ms)                        │ │
│                                                                  │
│  Solution: Higher CPU limit or explicit GC thread control       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**明示的な GC Thread 設定**:

```bash
# For CPU limit of 2 cores
JAVA_OPTS="-XX:ParallelGCThreads=2 \
           -XX:ConcGCThreads=1 \
           -XX:+UseContainerSupport"

# For CPU limit of 4 cores
JAVA_OPTS="-XX:ParallelGCThreads=4 \
           -XX:ConcGCThreads=2 \
           -XX:+UseContainerSupport"
```

### JMX Exporter セットアップ

```yaml
# jmx-exporter-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: jmx-exporter-config
data:
  jmx-config.yaml: |
    startDelaySeconds: 0
    ssl: false
    lowercaseOutputName: true
    lowercaseOutputLabelNames: true
    rules:
      # JVM memory
      - pattern: 'java.lang<type=Memory><HeapMemoryUsage>(\w+)'
        name: jvm_memory_heap_$1_bytes
        type: GAUGE

      - pattern: 'java.lang<type=Memory><NonHeapMemoryUsage>(\w+)'
        name: jvm_memory_nonheap_$1_bytes
        type: GAUGE

      # Memory pools
      - pattern: 'java.lang<type=MemoryPool, name=(.+)><Usage>(\w+)'
        name: jvm_memory_pool_$2_bytes
        labels:
          pool: $1
        type: GAUGE

      # GC metrics
      - pattern: 'java.lang<type=GarbageCollector, name=(.+)><CollectionCount>'
        name: jvm_gc_collection_count
        labels:
          gc: $1
        type: COUNTER

      - pattern: 'java.lang<type=GarbageCollector, name=(.+)><CollectionTime>'
        name: jvm_gc_collection_time_ms
        labels:
          gc: $1
        type: COUNTER

      # Threading
      - pattern: 'java.lang<type=Threading><ThreadCount>'
        name: jvm_threads_current
        type: GAUGE

      - pattern: 'java.lang<type=Threading><DaemonThreadCount>'
        name: jvm_threads_daemon
        type: GAUGE

      - pattern: 'java.lang<type=Threading><PeakThreadCount>'
        name: jvm_threads_peak
        type: GAUGE

      # Class loading
      - pattern: 'java.lang<type=ClassLoading><LoadedClassCount>'
        name: jvm_classes_loaded
        type: GAUGE

      # CPU
      - pattern: 'java.lang<type=OperatingSystem><ProcessCpuLoad>'
        name: jvm_process_cpu_load
        type: GAUGE

      - pattern: 'java.lang<type=OperatingSystem><SystemCpuLoad>'
        name: jvm_system_cpu_load
        type: GAUGE

      # Buffer pools
      - pattern: 'java.nio<type=BufferPool, name=(.+)><(\w+)>'
        name: jvm_buffer_pool_$2
        labels:
          pool: $1
        type: GAUGE
```

### Kubernetes での JFR Profiling

```yaml
# Enable JFR in deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: java-app
spec:
  template:
    spec:
      containers:
        - name: app
          env:
            - name: JAVA_OPTS
              value: >-
                -XX:StartFlightRecording=name=continuous,settings=default,maxsize=100m,maxage=1h,dumponexit=true,filename=/tmp/jfr/recording.jfr
                -XX:FlightRecorderOptions=stackdepth=256
          volumeMounts:
            - name: jfr-data
              mountPath: /tmp/jfr
      volumes:
        - name: jfr-data
          emptyDir:
            sizeLimit: 200Mi
```

**JFR dump のトリガー**:

```bash
# Connect to container and dump JFR
kubectl exec -it java-app-xxx -- jcmd 1 JFR.dump name=continuous filename=/tmp/jfr/dump.jfr

# Copy JFR file locally
kubectl cp java-app-xxx:/tmp/jfr/dump.jfr ./dump.jfr
```

### Spring Boot Actuator + Micrometer

```yaml
# application.yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,prometheus,metrics
  endpoint:
    health:
      show-details: always
      probes:
        enabled: true
  metrics:
    tags:
      application: ${spring.application.name}
      environment: ${ENVIRONMENT:development}
    export:
      prometheus:
        enabled: true
        step: 30s
    distribution:
      percentiles-histogram:
        http.server.requests: true
      percentiles:
        http.server.requests: 0.5, 0.75, 0.95, 0.99
      slo:
        http.server.requests: 100ms, 500ms, 1000ms, 2000ms
```

**pom.xml dependencies**:

```xml
<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-actuator</artifactId>
    </dependency>
    <dependency>
        <groupId>io.micrometer</groupId>
        <artifactId>micrometer-registry-prometheus</artifactId>
    </dependency>
</dependencies>
```

### 完全な JVM Deployment YAML

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: java-api-service
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: java-api-service
  template:
    metadata:
      labels:
        app: java-api-service
        version: v1
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/actuator/prometheus"
    spec:
      serviceAccountName: java-api-service
      containers:
        - name: api-service
          image: myregistry/java-api-service:v1.0.0
          ports:
            - name: http
              containerPort: 8080
            - name: jmx
              containerPort: 9090
          env:
            - name: JAVA_OPTS
              value: >-
                -XX:+UseContainerSupport
                -XX:MaxRAMPercentage=75.0
                -XX:InitialRAMPercentage=50.0
                -XX:+UseG1GC
                -XX:MaxGCPauseMillis=200
                -XX:ParallelGCThreads=2
                -XX:ConcGCThreads=1
                -XX:+HeapDumpOnOutOfMemoryError
                -XX:HeapDumpPath=/tmp/heapdump
                -Djava.security.egd=file:/dev/./urandom
            - name: SPRING_PROFILES_ACTIVE
              value: "kubernetes"
            - name: ENVIRONMENT
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace
          resources:
            requests:
              cpu: "500m"
              memory: "1Gi"
            limits:
              cpu: "2"          # Higher for GC headroom
              memory: "1536Mi"  # Heap (75% of 1Gi) + 50% overhead
          livenessProbe:
            httpGet:
              path: /actuator/health/liveness
              port: 8080
            initialDelaySeconds: 60
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /actuator/health/readiness
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3
          startupProbe:
            httpGet:
              path: /actuator/health/liveness
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 30  # 150 seconds max startup
          volumeMounts:
            - name: tmp
              mountPath: /tmp
            - name: heap-dumps
              mountPath: /tmp/heapdump
      volumes:
        - name: tmp
          emptyDir: {}
        - name: heap-dumps
          emptyDir:
            sizeLimit: 2Gi
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: java-api-service
```

### Grafana JVM Dashboard Panels

```json
{
  "title": "JVM Memory",
  "type": "timeseries",
  "targets": [
    {
      "expr": "jvm_memory_used_bytes{application=\"$application\", area=\"heap\"}",
      "legendFormat": "Heap Used"
    },
    {
      "expr": "jvm_memory_max_bytes{application=\"$application\", area=\"heap\"}",
      "legendFormat": "Heap Max"
    },
    {
      "expr": "jvm_memory_committed_bytes{application=\"$application\", area=\"heap\"}",
      "legendFormat": "Heap Committed"
    }
  ]
}
```

**監視すべき主要 JVM Metrics**:

```promql
# Heap utilization
jvm_memory_used_bytes{area="heap"} / jvm_memory_max_bytes{area="heap"} * 100

# GC pause time (p99)
histogram_quantile(0.99, sum(rate(jvm_gc_pause_seconds_bucket[5m])) by (le, gc, cause))

# GC frequency
sum(rate(jvm_gc_pause_seconds_count[5m])) by (gc, cause)

# GC overhead (time spent in GC)
sum(rate(jvm_gc_pause_seconds_sum[5m])) / sum(rate(process_cpu_seconds_total[5m])) * 100

# Thread count
jvm_threads_live_threads

# Class loading
rate(jvm_classes_loaded_classes_total[5m])
```

---

## Python/Node.js ワークロード

### Python (Gunicorn) 最適化

**Worker 計算**:

```python
# workers = (2 * CPU) + 1
# For CPU-bound: workers = CPU cores
# For I/O-bound: workers = (2 * CPU) + 1

# For 500m CPU request (0.5 cores):
# workers = (2 * 0.5) + 1 = 2 workers

# For 2 CPU request:
# workers = (2 * 2) + 1 = 5 workers
```

**Gunicorn 設定**:

```python
# gunicorn.conf.py
import multiprocessing
import os

# Get CPU limit from cgroup
def get_cpu_limit():
    try:
        with open('/sys/fs/cgroup/cpu/cpu.cfs_quota_us') as f:
            quota = int(f.read())
        with open('/sys/fs/cgroup/cpu/cpu.cfs_period_us') as f:
            period = int(f.read())
        if quota > 0:
            return quota / period
    except:
        pass
    return multiprocessing.cpu_count()

cpu_limit = get_cpu_limit()
workers = int((2 * cpu_limit) + 1)
threads = 2  # Per worker
worker_class = 'gthread'
worker_connections = 1000

# Timeouts
timeout = 30
graceful_timeout = 30
keepalive = 2

# Server socket
bind = '0.0.0.0:8000'
backlog = 2048

# Process naming
proc_name = 'gunicorn-app'

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Memory management
max_requests = 1000
max_requests_jitter = 50
```

**tracemalloc による Memory Profiling**:

```python
# memory_profiler.py
import tracemalloc
import linecache
import os

def display_top(snapshot, key_type='lineno', limit=10):
    """Display top memory-consuming lines."""
    snapshot = snapshot.filter_traces((
        tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
        tracemalloc.Filter(False, "<unknown>"),
    ))
    top_stats = snapshot.statistics(key_type)

    print(f"Top {limit} memory consumers:")
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        print(f"#{index}: {frame.filename}:{frame.lineno}: {stat.size / 1024:.1f} KiB")
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            print(f"    {line}")

# Enable in Flask app
from flask import Flask
app = Flask(__name__)

@app.before_first_request
def start_tracing():
    if os.environ.get('ENABLE_MEMORY_PROFILING'):
        tracemalloc.start()

@app.route('/debug/memory')
def memory_snapshot():
    if tracemalloc.is_tracing():
        snapshot = tracemalloc.take_snapshot()
        display_top(snapshot)
        return "Memory snapshot logged"
    return "Memory profiling not enabled"
```

**Python Kubernetes Deployment**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: python-api-service
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: python-api-service
  template:
    metadata:
      labels:
        app: python-api-service
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      containers:
        - name: api-service
          image: myregistry/python-api:v1.0.0
          command: ["gunicorn"]
          args:
            - "--config"
            - "gunicorn.conf.py"
            - "app:create_app()"
          ports:
            - name: http
              containerPort: 8000
          env:
            - name: PYTHONUNBUFFERED
              value: "1"
            - name: PYTHONDONTWRITEBYTECODE
              value: "1"
            - name: WEB_CONCURRENCY
              value: "3"  # Override calculated workers if needed
          resources:
            requests:
              cpu: "500m"
              memory: "512Mi"
            limits:
              cpu: "1500m"
              memory: "768Mi"
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 5
```

### Node.js 最適化

**V8 メモリ設定**:

```bash
# --max-old-space-size in MB
# Rule: 75% of container memory limit
# For 1Gi limit: 768MB (1024 * 0.75)
NODE_OPTIONS="--max-old-space-size=768"
```

**UV_THREADPOOL_SIZE**:

```bash
# Default: 4 threads
# For I/O-heavy apps: CPU cores * 2
# Max: 1024
UV_THREADPOOL_SIZE=8
```

**マルチコア向け Cluster Mode**:

```javascript
// cluster.js
const cluster = require('cluster');
const os = require('os');
const fs = require('fs');

// Get CPU limit from cgroup
function getCpuLimit() {
  try {
    const quota = parseInt(fs.readFileSync('/sys/fs/cgroup/cpu/cpu.cfs_quota_us', 'utf8'));
    const period = parseInt(fs.readFileSync('/sys/fs/cgroup/cpu/cpu.cfs_period_us', 'utf8'));
    if (quota > 0) {
      return Math.ceil(quota / period);
    }
  } catch (e) {
    // Fallback to OS CPU count
  }
  return os.cpus().length;
}

const numCPUs = getCpuLimit();

if (cluster.isMaster) {
  console.log(`Master ${process.pid} starting ${numCPUs} workers`);

  for (let i = 0; i < numCPUs; i++) {
    cluster.fork();
  }

  cluster.on('exit', (worker, code, signal) => {
    console.log(`Worker ${worker.process.pid} died. Restarting...`);
    cluster.fork();
  });
} else {
  require('./app');
}
```

**Memory Leak Detection**:

```javascript
// memory-monitor.js
const v8 = require('v8');

class MemoryMonitor {
  constructor(options = {}) {
    this.threshold = options.threshold || 0.85; // 85% of limit
    this.interval = options.interval || 30000;  // 30 seconds
    this.maxHeap = this.getMaxHeap();
  }

  getMaxHeap() {
    const heapStats = v8.getHeapStatistics();
    return heapStats.heap_size_limit;
  }

  checkMemory() {
    const heapStats = v8.getHeapStatistics();
    const used = heapStats.used_heap_size;
    const total = heapStats.total_heap_size;
    const limit = heapStats.heap_size_limit;
    const utilization = used / limit;

    console.log(JSON.stringify({
      level: utilization > this.threshold ? 'warn' : 'info',
      message: 'memory_stats',
      heap_used_mb: Math.round(used / 1024 / 1024),
      heap_total_mb: Math.round(total / 1024 / 1024),
      heap_limit_mb: Math.round(limit / 1024 / 1024),
      utilization_percent: Math.round(utilization * 100),
    }));

    if (utilization > this.threshold) {
      console.warn(`High memory utilization: ${Math.round(utilization * 100)}%`);
      // Optionally trigger GC if exposed
      if (global.gc) {
        console.log('Triggering garbage collection');
        global.gc();
      }
    }

    return { used, total, limit, utilization };
  }

  start() {
    this.timer = setInterval(() => this.checkMemory(), this.interval);
    return this;
  }

  stop() {
    if (this.timer) {
      clearInterval(this.timer);
    }
  }
}

module.exports = MemoryMonitor;
```

**Node.js Kubernetes Deployment**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nodejs-api-service
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nodejs-api-service
  template:
    metadata:
      labels:
        app: nodejs-api-service
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "3000"
        prometheus.io/path: "/metrics"
    spec:
      containers:
        - name: api-service
          image: myregistry/nodejs-api:v1.0.0
          ports:
            - name: http
              containerPort: 3000
          env:
            - name: NODE_ENV
              value: "production"
            - name: NODE_OPTIONS
              value: "--max-old-space-size=768 --expose-gc"
            - name: UV_THREADPOOL_SIZE
              value: "8"
          resources:
            requests:
              cpu: "500m"
              memory: "512Mi"
            limits:
              cpu: "1500m"
              memory: "1Gi"
          livenessProbe:
            httpGet:
              path: /health/live
              port: 3000
            initialDelaySeconds: 10
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 3000
            initialDelaySeconds: 5
            periodSeconds: 5
          lifecycle:
            preStop:
              exec:
                command: ["/bin/sh", "-c", "sleep 5"]
```

---

## Go/Rust ワークロード

### Go 最適化

**Container-Aware CPU のための automaxprocs**:

```go
// main.go
package main

import (
    "log"
    _ "go.uber.org/automaxprocs" // Automatically sets GOMAXPROCS
)

func main() {
    // GOMAXPROCS is automatically set based on container CPU limit
    log.Println("Starting application...")
}
```

**GOMEMLIMIT 設定** (Go 1.19+):

```bash
# Set soft memory limit
# Recommendation: 90% of container memory limit
# For 1Gi limit: GOMEMLIMIT=900MiB
GOMEMLIMIT=900MiB
GOGC=100  # Default garbage collection target percentage
```

**Go Application Best Practices**:

```go
// config.go
package main

import (
    "os"
    "runtime"
    "runtime/debug"
)

func configureRuntime() {
    // Set GOMAXPROCS from environment or use automaxprocs
    if maxprocs := os.Getenv("GOMAXPROCS"); maxprocs == "" {
        // Let automaxprocs handle it
    }

    // Configure memory limit
    if memlimit := os.Getenv("GOMEMLIMIT"); memlimit != "" {
        // Already set via environment
    } else {
        // Set programmatically (90% of cgroup limit)
        limit := getMemoryLimit()
        if limit > 0 {
            debug.SetMemoryLimit(int64(float64(limit) * 0.9))
        }
    }

    // Configure GC
    debug.SetGCPercent(100) // Default, can tune based on workload
}

func getMemoryLimit() uint64 {
    // Read from cgroup v2
    data, err := os.ReadFile("/sys/fs/cgroup/memory.max")
    if err != nil {
        return 0
    }
    // Parse and return
    var limit uint64
    fmt.Sscanf(string(data), "%d", &limit)
    return limit
}

// Expose runtime metrics
func getRuntimeMetrics() map[string]interface{} {
    var m runtime.MemStats
    runtime.ReadMemStats(&m)

    return map[string]interface{}{
        "goroutines":     runtime.NumGoroutine(),
        "heap_alloc":     m.HeapAlloc,
        "heap_sys":       m.HeapSys,
        "heap_idle":      m.HeapIdle,
        "heap_inuse":     m.HeapInuse,
        "stack_inuse":    m.StackInuse,
        "gc_pause_ns":    m.PauseNs[(m.NumGC+255)%256],
        "gc_num":         m.NumGC,
        "gomaxprocs":     runtime.GOMAXPROCS(0),
    }
}
```

**Go Resource Efficiency**:

| Metric | Go | Java | Python | Node.js |
|--------|-----|------|--------|---------|
| Memory footprint | ~10-50MB | ~200-500MB | ~50-150MB | ~50-150MB |
| Startup time | ~50ms | ~2-10s | ~500ms | ~200ms |
| Container overhead | 最小 | 25-40% | 10-20% | 10-20% |
| Recommended memory | Actual + 20% | Heap + 40% | Actual + 30% | Heap + 30% |

**Go Kubernetes Deployment**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: go-api-service
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: go-api-service
  template:
    metadata:
      labels:
        app: go-api-service
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
    spec:
      containers:
        - name: api-service
          image: myregistry/go-api:v1.0.0
          ports:
            - name: http
              containerPort: 8080
          env:
            - name: GOMEMLIMIT
              value: "450MiB"  # 90% of 512Mi limit
            - name: GOGC
              value: "100"
          resources:
            requests:
              cpu: "100m"     # Go is efficient
              memory: "128Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8080
            initialDelaySeconds: 3
            periodSeconds: 5
```

### Rust 最適化

**GC がない利点**:

Rust には garbage collector がなく、次を実現します。
- 決定的なメモリ使用量
- GC pause なし
- 一貫したレイテンシ
- 低いメモリ overhead

**jemalloc 設定**:

```rust
// Cargo.toml
[dependencies]
tikv-jemallocator = "0.5"

// main.rs
#[global_allocator]
static GLOBAL: tikv_jemallocator::Jemalloc = tikv_jemallocator::Jemalloc;
```

**Tokio Runtime 設定**:

```rust
// main.rs
use tokio::runtime::Builder;

fn main() {
    // Configure based on container CPU limit
    let cpu_limit = get_cpu_limit();

    let runtime = Builder::new_multi_thread()
        .worker_threads(cpu_limit)
        .thread_stack_size(2 * 1024 * 1024) // 2MB stack per thread
        .enable_all()
        .build()
        .unwrap();

    runtime.block_on(async {
        // Application code
    });
}

fn get_cpu_limit() -> usize {
    // Read from cgroup
    std::fs::read_to_string("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
        .ok()
        .and_then(|quota| quota.trim().parse::<i64>().ok())
        .filter(|&q| q > 0)
        .zip(
            std::fs::read_to_string("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
                .ok()
                .and_then(|period| period.trim().parse::<i64>().ok())
        )
        .map(|(quota, period)| (quota / period) as usize)
        .unwrap_or_else(num_cpus::get)
        .max(1)
}
```

**Rust Kubernetes Deployment**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rust-api-service
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rust-api-service
  template:
    metadata:
      labels:
        app: rust-api-service
    spec:
      containers:
        - name: api-service
          image: myregistry/rust-api:v1.0.0
          ports:
            - name: http
              containerPort: 8080
          env:
            - name: RUST_LOG
              value: "info"
            - name: TOKIO_WORKER_THREADS
              value: "2"
          resources:
            requests:
              cpu: "50m"      # Rust is very efficient
              memory: "64Mi"
            limits:
              cpu: "500m"
              memory: "256Mi"
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 3
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: 8080
            initialDelaySeconds: 2
            periodSeconds: 5
```

### コンパイル言語のリソース比較

| 観点 | Go | Rust | C++ |
|--------|-----|------|-----|
| **Memory model** | GC (concurrent) | Ownership (no GC) | Manual |
| **Startup time** | ~50ms | ~10ms | ~10ms |
| **Memory overhead** | 低い | 最小 | 最小 |
| **CPU efficiency** | 非常に高い | 最高 | 最高 |
| **Request sizing** | Actual * 1.2 | Actual * 1.1 | Actual * 1.1 |
| **Container fit** | 非常に優秀 | 最良 | 良好 |

---

## リソース監視ダッシュボード

### CPU Throttling 検出

```promql
# Throttled time per second (should be near 0)
sum(rate(container_cpu_cfs_throttled_seconds_total{namespace="production"}[5m]))
by (pod, container)

# Throttle percentage (target: < 5%)
sum(rate(container_cpu_cfs_throttled_periods_total{namespace="production"}[5m]))
by (pod, container)
/
sum(rate(container_cpu_cfs_periods_total{namespace="production"}[5m]))
by (pod, container)
* 100

# Pods with high throttling
topk(10,
  sum(rate(container_cpu_cfs_throttled_seconds_total{namespace="production"}[5m]))
  by (pod, container)
)
```

### Memory Pressure 監視

```promql
# Memory utilization percentage
sum(container_memory_working_set_bytes{namespace="production", container!=""})
by (pod, container)
/
sum(kube_pod_container_resource_limits{namespace="production", resource="memory"})
by (pod, container)
* 100

# Near OOM pods (> 90% of limit)
(
  sum(container_memory_working_set_bytes{namespace="production"}) by (pod, container)
  /
  sum(kube_pod_container_resource_limits{namespace="production", resource="memory"}) by (pod, container)
) > 0.9

# OOMKill events
increase(kube_pod_container_status_restarts_total{namespace="production"}[1h])
* on (pod, container) group_left()
kube_pod_container_status_last_terminated_reason{reason="OOMKilled"} > 0
```

### Request と実使用量の比較

```promql
# CPU over-provisioning ratio (target: < 2x)
sum(kube_pod_container_resource_requests{namespace="production", resource="cpu"})
by (pod, container)
/
sum(rate(container_cpu_usage_seconds_total{namespace="production", container!=""}[5m]))
by (pod, container)

# Memory over-provisioning ratio (target: < 1.5x)
sum(kube_pod_container_resource_requests{namespace="production", resource="memory"})
by (pod, container)
/
sum(container_memory_working_set_bytes{namespace="production", container!=""})
by (pod, container)

# Namespace-level waste
sum(kube_pod_container_resource_requests{namespace="production", resource="cpu"})
-
sum(rate(container_cpu_usage_seconds_total{namespace="production", container!=""}[5m]))
```

### 過剰プロビジョニング検出

```promql
# Top over-provisioned deployments by CPU
topk(10,
  sum by (deployment) (
    label_replace(
      kube_pod_container_resource_requests{namespace="production", resource="cpu"},
      "deployment", "$1", "pod", "(.+)-[a-f0-9]+-[a-z0-9]+"
    )
  )
  /
  sum by (deployment) (
    label_replace(
      rate(container_cpu_usage_seconds_total{namespace="production", container!=""}[5m]),
      "deployment", "$1", "pod", "(.+)-[a-f0-9]+-[a-z0-9]+"
    )
  )
)

# Top over-provisioned deployments by memory
topk(10,
  sum by (deployment) (
    label_replace(
      kube_pod_container_resource_requests{namespace="production", resource="memory"},
      "deployment", "$1", "pod", "(.+)-[a-f0-9]+-[a-z0-9]+"
    )
  )
  /
  sum by (deployment) (
    label_replace(
      container_memory_working_set_bytes{namespace="production", container!=""},
      "deployment", "$1", "pod", "(.+)-[a-f0-9]+-[a-z0-9]+"
    )
  )
)
```

### Grafana Panel の例

**CPU Efficiency Panel**:

```json
{
  "title": "CPU Efficiency by Deployment",
  "type": "bargauge",
  "targets": [
    {
      "expr": "sum by (deployment) (rate(container_cpu_usage_seconds_total{namespace=\"production\"}[5m])) / sum by (deployment) (kube_pod_container_resource_requests{namespace=\"production\", resource=\"cpu\"}) * 100",
      "legendFormat": "{{deployment}}"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "thresholds": {
        "steps": [
          { "color": "red", "value": 0 },
          { "color": "yellow", "value": 50 },
          { "color": "green", "value": 70 },
          { "color": "red", "value": 100 }
        ]
      },
      "unit": "percent",
      "max": 150
    }
  }
}
```

**Memory Utilization Heatmap**:

```json
{
  "title": "Memory Utilization Heatmap",
  "type": "heatmap",
  "targets": [
    {
      "expr": "sum by (pod) (container_memory_working_set_bytes{namespace=\"production\"}) / sum by (pod) (kube_pod_container_resource_limits{namespace=\"production\", resource=\"memory\"}) * 100",
      "legendFormat": "{{pod}}"
    }
  ],
  "options": {
    "calculate": false,
    "cellGap": 1,
    "color": {
      "scheme": "RdYlGn",
      "reverse": true
    }
  }
}
```

### Alert Rules

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: resource-alerts
  namespace: monitoring
spec:
  groups:
    - name: resource.rules
      rules:
        - alert: HighCPUThrottling
          expr: |
            sum(rate(container_cpu_cfs_throttled_periods_total{namespace="production"}[5m]))
            by (pod, container)
            /
            sum(rate(container_cpu_cfs_periods_total{namespace="production"}[5m]))
            by (pod, container)
            > 0.25
          for: 15m
          labels:
            severity: warning
          annotations:
            summary: "High CPU throttling for {{ $labels.pod }}/{{ $labels.container }}"
            description: "CPU throttling is {{ $value | humanizePercentage }} for the past 15 minutes. Consider increasing CPU limits."

        - alert: HighMemoryUtilization
          expr: |
            sum(container_memory_working_set_bytes{namespace="production", container!=""})
            by (pod, container)
            /
            sum(kube_pod_container_resource_limits{namespace="production", resource="memory"})
            by (pod, container)
            > 0.9
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "High memory utilization for {{ $labels.pod }}/{{ $labels.container }}"
            description: "Memory utilization is {{ $value | humanizePercentage }}. Risk of OOMKill."

        - alert: PodOOMKilled
          expr: |
            increase(kube_pod_container_status_restarts_total{namespace="production"}[1h]) > 0
            and on (pod, container)
            kube_pod_container_status_last_terminated_reason{reason="OOMKilled"} == 1
          labels:
            severity: critical
          annotations:
            summary: "Pod {{ $labels.pod }} was OOMKilled"
            description: "Container {{ $labels.container }} in pod {{ $labels.pod }} was terminated due to OOM. Increase memory limits."

        - alert: ResourceOverProvisioning
          expr: |
            sum(kube_pod_container_resource_requests{namespace="production", resource="cpu"})
            by (namespace)
            /
            sum(rate(container_cpu_usage_seconds_total{namespace="production", container!=""}[1h]))
            by (namespace)
            > 3
          for: 24h
          labels:
            severity: info
          annotations:
            summary: "Resources over-provisioned in {{ $labels.namespace }}"
            description: "CPU requests are {{ $value }}x actual usage. Consider right-sizing."

        - alert: ResourceUnderProvisioning
          expr: |
            sum(rate(container_cpu_usage_seconds_total{namespace="production", container!=""}[5m]))
            by (pod, container)
            >
            sum(kube_pod_container_resource_requests{namespace="production", resource="cpu"})
            by (pod, container)
            * 0.9
          for: 30m
          labels:
            severity: warning
          annotations:
            summary: "CPU under-provisioned for {{ $labels.pod }}"
            description: "CPU usage is consistently above 90% of request. Consider increasing requests."
```

---

## Auto Mode におけるリソース最適化

### Instance Type Bin-Packing

EKS Auto Mode は pending pod の要件に基づいて instance type を自動選択します。

```
┌─────────────────────────────────────────────────────────────────┐
│                  Auto Mode Bin-Packing                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Pending Pods:                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ 500m CPU │ │ 1 CPU    │ │ 2 CPU    │ │ 500m CPU │           │
│  │ 512Mi    │ │ 2Gi      │ │ 4Gi      │ │ 1Gi      │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│                                                                  │
│  Total: 4 CPU, 7.5Gi Memory                                     │
│                                                                  │
│  Auto Mode Selection:                                           │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  m6i.xlarge (4 vCPU, 16 GiB)                               │ │
│  │  ┌────┐ ┌────┐ ┌────────┐ ┌────┐ ┌─────────────────────┐  │ │
│  │  │Pod1│ │Pod2│ │  Pod3  │ │Pod4│ │    Headroom         │  │ │
│  │  └────┘ └────┘ └────────┘ └────┘ └─────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 高速スケーリングのための Over-Provisioning

より高速な pod scheduling のために over-provisioning を設定します。

```yaml
# Pause pods for capacity reservation
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: overprovisioning
value: -1  # Lowest priority, evicted first
preemptionPolicy: Never
globalDefault: false
description: "Reserved capacity for quick scaling"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: overprovisioning
  namespace: kube-system
spec:
  replicas: 2
  selector:
    matchLabels:
      app: overprovisioning
  template:
    metadata:
      labels:
        app: overprovisioning
    spec:
      priorityClassName: overprovisioning
      containers:
        - name: pause
          image: registry.k8s.io/pause:3.9
          resources:
            requests:
              cpu: "2"
              memory: "4Gi"
```

### Node Consolidation

node utilization を監視し、最適化します。

```promql
# Node CPU utilization
sum(rate(container_cpu_usage_seconds_total{container!=""}[5m]))
by (node)
/
sum(kube_node_status_allocatable{resource="cpu"})
by (node)
* 100

# Node memory utilization
sum(container_memory_working_set_bytes{container!=""})
by (node)
/
sum(kube_node_status_allocatable{resource="memory"})
by (node)
* 100

# Under-utilized nodes (candidates for consolidation)
(
  sum(rate(container_cpu_usage_seconds_total{container!=""}[5m])) by (node)
  /
  sum(kube_node_status_allocatable{resource="cpu"}) by (node)
) < 0.3
and
(
  sum(container_memory_working_set_bytes{container!=""}) by (node)
  /
  sum(kube_node_status_allocatable{resource="memory"}) by (node)
) < 0.3
```

### Cluster-Level Efficiency Metrics

```promql
# Overall cluster CPU efficiency
sum(rate(container_cpu_usage_seconds_total{container!=""}[5m]))
/
sum(kube_node_status_allocatable{resource="cpu"})
* 100

# Overall cluster memory efficiency
sum(container_memory_working_set_bytes{container!=""})
/
sum(kube_node_status_allocatable{resource="memory"})
* 100

# Request vs capacity efficiency
sum(kube_pod_container_resource_requests{resource="cpu"})
/
sum(kube_node_status_allocatable{resource="cpu"})
* 100

# Waste: allocated but unused
(
  sum(kube_pod_container_resource_requests{resource="cpu"})
  -
  sum(rate(container_cpu_usage_seconds_total{container!=""}[5m]))
)
/
sum(kube_node_status_allocatable{resource="cpu"})
* 100
```

### Auto Mode 最適化の推奨事項

| シナリオ | 推奨事項 | Auto Mode の動作 |
|----------|----------------|-------------------|
| 小さな pod が多い | より小さな instance type を使用 | 適切な mix を自動選択 |
| 少数の大きな pod | より大きな instance を許可 | 大きな instance を provision |
| 変動する workload | over-provisioning を有効化 | buffer capacity を維持 |
| コスト最適化 | Spot instances | pool 間で分散 |
| レイテンシに敏感 | Same-AZ placement | topology constraints を尊重 |

**Auto Mode のベストプラクティス**:

1. **正確な resource requests を設定する**: Auto Mode は scheduling decisions に requests を使用します
2. **過剰な limits を避ける**: 高い limits は node を断片化する可能性があります
3. **topology spread を使用する**: pod を zone 間に分散します
4. **PodDisruptionBudgets を設定する**: 安全な consolidation を有効にします
5. **bin-packing efficiency を監視する**: node utilization を追跡します

---

## 関連ドキュメント

- [Observability Stack Operations](./09-observability-stack.md) - 監視と alerting 設定
- [EKS Upgrades](./11-upgrade-operations.md) - Cluster upgrade 手順

---

< [前へ: Observability Stack Operations](./09-observability-stack.md) | [目次](./README.md) | [次へ: EKS Upgrades](./11-upgrade-operations.md) >
