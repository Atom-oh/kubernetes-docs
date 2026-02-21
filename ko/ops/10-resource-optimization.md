# 리소스 최적화: Requests/Limits, JVM 튜닝, 프레임워크별 가이드

> **지원 버전**: Kubernetes 1.28+, Java 17+, Python 3.11+, Node.js 20+, Go 1.21+
> **마지막 업데이트**: 2025년 6월

< [이전: 관측성 스택 운영](./09-observability-stack.md) | [목차](./README.md) | [다음: EKS 업그레이드](./11-upgrade-operations.md) >

---

## 1. 리소스 설정 기본 원칙

### 1.1 Requests vs Limits

Kubernetes에서 컨테이너 리소스 설정은 두 가지 개념으로 구분됩니다:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Resource Configuration                                │
├─────────────────────────────────────┬───────────────────────────────────────┤
│             Requests                │              Limits                    │
├─────────────────────────────────────┼───────────────────────────────────────┤
│  - 스케줄링에 사용                   │  - 런타임 제한에 사용                  │
│  - "최소 필요 리소스"                │  - "최대 허용 리소스"                  │
│  - 노드 선택 기준                    │  - 초과 시 throttling/OOMKill         │
│  - QoS 클래스 결정                   │  - cgroup 제한 설정                    │
└─────────────────────────────────────┴───────────────────────────────────────┘
```

**동작 방식:**

| 구분 | Requests | Limits |
|-----|----------|--------|
| **CPU** | 스케줄링 보장 | CFS quota로 제한 (throttling) |
| **Memory** | 스케줄링 보장 | cgroup 한계 (OOMKill) |
| **설정 안함** | 제한 없이 스케줄링 | 제한 없음 |

### 1.2 QoS 클래스

```yaml
# Guaranteed: requests == limits (모든 리소스)
apiVersion: v1
kind: Pod
metadata:
  name: guaranteed-pod
spec:
  containers:
    - name: app
      resources:
        requests:
          cpu: "500m"
          memory: "1Gi"
        limits:
          cpu: "500m"      # requests와 동일
          memory: "1Gi"    # requests와 동일
---
# Burstable: requests < limits 또는 일부만 설정
apiVersion: v1
kind: Pod
metadata:
  name: burstable-pod
spec:
  containers:
    - name: app
      resources:
        requests:
          cpu: "250m"
          memory: "512Mi"
        limits:
          cpu: "1"         # requests보다 큼
          memory: "2Gi"    # requests보다 큼
---
# BestEffort: requests/limits 모두 미설정
apiVersion: v1
kind: Pod
metadata:
  name: besteffort-pod
spec:
  containers:
    - name: app
      # resources 섹션 없음
```

**QoS 클래스별 특성:**

| QoS 클래스 | 스케줄링 | OOM 우선순위 | 사용 케이스 |
|-----------|---------|-------------|------------|
| **Guaranteed** | 예측 가능 | 마지막 제거 | 중요 워크로드 |
| **Burstable** | 유연함 | 중간 | 일반 애플리케이션 |
| **BestEffort** | 가장 유연 | 최우선 제거 | 배치 작업, 테스트 |

### 1.3 CPU Throttling 원리

Linux CFS (Completely Fair Scheduler) bandwidth control:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     CFS Bandwidth Control                                    │
│                                                                             │
│   cpu.cfs_period_us = 100000 (100ms)                                       │
│   cpu.cfs_quota_us  = 설정된 CPU limit * cfs_period_us                      │
│                                                                             │
│   예: CPU limit = 500m (0.5 core)                                           │
│       quota = 0.5 * 100000 = 50000us (50ms)                                 │
│                                                                             │
│   ┌──────────────────────────────────────────────────────────────┐         │
│   │  Period (100ms)                                               │         │
│   │  ┌─────────────────────┬────────────────────────────────────┐│         │
│   │  │   Quota (50ms)      │         Throttled                  ││         │
│   │  │   (CPU 사용 가능)    │         (CPU 사용 불가)             ││         │
│   │  └─────────────────────┴────────────────────────────────────┘│         │
│   └──────────────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Throttling 발생 조건:**
- Period(100ms) 내에 Quota를 모두 사용
- 멀티스레드 애플리케이션에서 여러 스레드가 동시에 CPU 사용 시 빠르게 quota 소진

### 1.4 Memory OOMKill

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Memory Limit Enforcement                            │
│                                                                             │
│   Container Memory Limit = cgroup memory.limit_in_bytes                     │
│                                                                             │
│   Memory 사용량이 limit 초과 시:                                              │
│   1. Kernel이 cgroup의 메모리 할당 실패                                       │
│   2. OOM Killer가 해당 cgroup 내 프로세스 종료                                │
│   3. 컨테이너 재시작 (restartPolicy에 따라)                                   │
│                                                                             │
│   oom_score_adj 값:                                                          │
│   - Guaranteed: -997 (낮음 = 보호)                                           │
│   - Burstable:  계산됨 (중간)                                                │
│   - BestEffort: 1000 (높음 = 우선 종료)                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.5 피해야 할 안티패턴

```yaml
# 안티패턴 1: Limits만 설정 (requests 미설정)
# 결과: requests가 limits와 동일하게 설정됨 (과도한 예약)
resources:
  limits:
    cpu: "2"
    memory: "4Gi"
# requests가 자동으로 cpu: "2", memory: "4Gi"로 설정됨

---
# 안티패턴 2: 너무 낮은 CPU limits (심각한 throttling)
resources:
  requests:
    cpu: "100m"
  limits:
    cpu: "100m"   # 스타트업 시 throttling 심함

---
# 안티패턴 3: 메모리 limits < 실제 필요량
resources:
  limits:
    memory: "256Mi"  # 실제 512Mi 필요 -> 반복적 OOMKill

---
# 안티패턴 4: requests와 limits 차이가 너무 큼
resources:
  requests:
    cpu: "100m"
    memory: "128Mi"
  limits:
    cpu: "4"         # 40배 차이
    memory: "8Gi"    # 64배 차이
# 결과: 노드 과밀화, 불안정한 성능
```

---

## 2. 최적 리소스 산정 방법

### 2.1 VPA (Vertical Pod Autoscaler) Recommender

VPA는 히스토리 데이터를 기반으로 최적의 리소스 설정을 추천합니다.

```yaml
# vpa-recommender.yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: api-gateway-vpa
  namespace: production
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: api-gateway
  updatePolicy:
    updateMode: "Off"  # 추천만 (자동 적용 안함)
  resourcePolicy:
    containerPolicies:
      - containerName: "*"
        minAllowed:
          cpu: "100m"
          memory: "128Mi"
        maxAllowed:
          cpu: "4"
          memory: "8Gi"
        controlledResources: ["cpu", "memory"]
        controlledValues: RequestsAndLimits
```

**VPA 추천 유형:**

```bash
# VPA 추천 확인
kubectl describe vpa api-gateway-vpa -n production
```

```yaml
# 출력 예시
status:
  recommendation:
    containerRecommendations:
      - containerName: api-gateway
        lowerBound:           # 최소 권장값
          cpu: "250m"
          memory: "512Mi"
        target:               # 권장값 (이 값 사용 권장)
          cpu: "500m"
          memory: "1Gi"
        upperBound:           # 최대 권장값 (버스트 대비)
          cpu: "1"
          memory: "2Gi"
        uncappedTarget:       # 제한 없는 권장값
          cpu: "750m"
          memory: "1536Mi"
```

### 2.2 Goldilocks 대시보드

Goldilocks는 VPA 추천을 시각화하고 네임스페이스 단위로 분석합니다.

```bash
# Goldilocks 설치
helm repo add fairwinds-stable https://charts.fairwinds.com/stable
helm install goldilocks fairwinds-stable/goldilocks \
  --namespace goldilocks \
  --create-namespace

# 네임스페이스에 VPA 자동 생성 활성화
kubectl label namespace production goldilocks.fairwinds.com/enabled=true
```

대시보드 접근:

```bash
kubectl port-forward -n goldilocks svc/goldilocks-dashboard 8080:80
# http://localhost:8080 접속
```

### 2.3 PromQL 기반 분석

#### CPU 사용률 분석

```promql
# 컨테이너별 CPU 사용량 대비 request 비율 (목표: 70-80%)
avg(
  rate(container_cpu_usage_seconds_total{
    namespace="production",
    container!="",
    container!="POD"
  }[5m])
) by (container, pod)
/
avg(
  kube_pod_container_resource_requests{
    namespace="production",
    resource="cpu"
  }
) by (container, pod)
* 100

# 네임스페이스별 CPU 요청 대비 사용률
sum(rate(container_cpu_usage_seconds_total{namespace="production"}[5m])) by (namespace)
/
sum(kube_pod_container_resource_requests{namespace="production", resource="cpu"}) by (namespace)
* 100

# CPU throttling 비율 (5% 이상이면 limits 증가 필요)
rate(container_cpu_cfs_throttled_periods_total{namespace="production"}[5m])
/
rate(container_cpu_cfs_periods_total{namespace="production"}[5m])
* 100
```

#### 메모리 사용률 분석

```promql
# 컨테이너별 메모리 사용량 대비 limit 비율 (목표: 80% 미만)
max(
  container_memory_working_set_bytes{
    namespace="production",
    container!="",
    container!="POD"
  }
) by (container, pod)
/
max(
  kube_pod_container_resource_limits{
    namespace="production",
    resource="memory"
  }
) by (container, pod)
* 100

# OOM 위험 컨테이너 식별 (90% 이상 사용)
(
  container_memory_working_set_bytes{namespace="production"}
  /
  kube_pod_container_resource_limits{namespace="production", resource="memory"}
) > 0.9
```

### 2.4 최소 레플리카 계산

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Minimum Replicas Calculation                             │
│                                                                             │
│   목표 RPS (Requests Per Second) = 1000 RPS                                 │
│                                                                             │
│   1. 단일 Pod 처리량 벤치마크:                                               │
│      - 부하 테스트로 측정: 단일 Pod = 200 RPS                                │
│                                                                             │
│   2. 최소 레플리카 계산:                                                     │
│      replicas = ceil(target_rps / pod_rps)                                  │
│               = ceil(1000 / 200)                                            │
│               = 5                                                           │
│                                                                             │
│   3. 버퍼 추가 (20% 여유):                                                   │
│      final_replicas = ceil(5 * 1.2) = 6                                     │
│                                                                             │
│   4. 고가용성 고려:                                                          │
│      - 최소 3개 (단일 실패 대응)                                             │
│      - Zone 분산 시 Zone 수 이상                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.5 리소스 최적화 체크리스트

| 항목 | 확인 기준 | 조치 |
|-----|---------|------|
| CPU 사용률 | 70-80% 유지 | 범위 외 시 request 조정 |
| CPU Throttling | 5% 미만 | 초과 시 limits 증가 |
| 메모리 사용률 | 80% 미만 | 초과 시 OOM 위험 |
| 메모리 Working Set | Limit의 70% 미만 | 초과 시 limit 증가 |
| Pod 재시작 | OOMKilled 없음 | 발생 시 메모리 limit 증가 |
| 응답 시간 | SLO 충족 | 미충족 시 CPU/레플리카 증가 |

---

## 3. JVM 워크로드 최적화

### 3.1 JVM Heap vs 컨테이너 메모리

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Container Memory Layout (JVM)                             │
│                                                                             │
│   Container Memory Limit: 2Gi                                               │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                                                                     │   │
│   │   ┌─────────────────────────────────────────────────────────────┐   │   │
│   │   │              JVM Heap (MaxRAMPercentage=75%)                │   │   │
│   │   │                     ~1.5Gi                                  │   │   │
│   │   │  ┌───────────────┐  ┌────────────────────────────────────┐  │   │   │
│   │   │  │  Young Gen    │  │           Old Gen                  │  │   │   │
│   │   │  │   (~375Mi)    │  │          (~1.125Gi)                │  │   │   │
│   │   │  └───────────────┘  └────────────────────────────────────┘  │   │   │
│   │   └─────────────────────────────────────────────────────────────┘   │   │
│   │                                                                     │   │
│   │   ┌─────────────────────────────────────────────────────────────┐   │   │
│   │   │                    Non-Heap Memory                          │   │   │
│   │   │                       ~512Mi                                │   │   │
│   │   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────────┐ │   │   │
│   │   │  │Metaspace │ │ Thread   │ │   NIO    │ │   Native Mem    │ │   │   │
│   │   │  │ ~128Mi   │ │ Stacks   │ │ Buffers  │ │   (JNI, etc)    │ │   │   │
│   │   │  │          │ │ ~100Mi   │ │  ~64Mi   │ │     ~220Mi      │ │   │   │
│   │   │  └──────────┘ └──────────┘ └──────────┘ └─────────────────┘ │   │   │
│   │   └─────────────────────────────────────────────────────────────┘   │   │
│   │                                                                     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 컨테이너 인식 JVM 설정

```yaml
# jvm-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spring-boot-app
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: spring-boot-app
  template:
    metadata:
      labels:
        app: spring-boot-app
    spec:
      containers:
        - name: app
          image: myapp:latest
          resources:
            requests:
              cpu: "500m"
              memory: "1Gi"
            limits:
              cpu: "2"
              memory: "2Gi"
          env:
            - name: JAVA_OPTS
              value: >-
                -XX:+UseContainerSupport
                -XX:MaxRAMPercentage=75.0
                -XX:InitialRAMPercentage=50.0
                -XX:+UseG1GC
                -XX:MaxGCPauseMillis=200
                -XX:+HeapDumpOnOutOfMemoryError
                -XX:HeapDumpPath=/tmp/heapdump.hprof
                -Djava.security.egd=file:/dev/./urandom
          ports:
            - containerPort: 8080
          livenessProbe:
            httpGet:
              path: /actuator/health/liveness
              port: 8080
            initialDelaySeconds: 60
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /actuator/health/readiness
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 5
```

**MaxRAMPercentage 권장값:**

| 컨테이너 메모리 | MaxRAMPercentage | 이유 |
|---------------|------------------|------|
| 512Mi 이하 | 50-60% | 작은 컨테이너는 non-heap 비율 높음 |
| 1-2Gi | 70-75% | 일반적인 권장값 |
| 4Gi 이상 | 75-80% | 대용량은 non-heap 비율 낮음 |

### 3.3 GC 알고리즘 선택

```yaml
# gc-comparison.yaml
# G1GC (기본, Java 9+)
env:
  - name: JAVA_OPTS
    value: >-
      -XX:+UseG1GC
      -XX:MaxGCPauseMillis=200
      -XX:G1HeapRegionSize=16m
      -XX:G1ReservePercent=10

# ZGC (저지연, Java 17+)
env:
  - name: JAVA_OPTS
    value: >-
      -XX:+UseZGC
      -XX:+ZGenerational
      -XX:ZCollectionInterval=0

# Shenandoah (저지연, OpenJDK)
env:
  - name: JAVA_OPTS
    value: >-
      -XX:+UseShenandoahGC
      -XX:ShenandoahGCHeuristics=adaptive
```

**GC 알고리즘 비교:**

| GC | 지연시간 | 처리량 | 메모리 오버헤드 | 사용 케이스 |
|---|--------|-------|---------------|-----------|
| **G1GC** | 중간 (10-200ms) | 높음 | 중간 | 일반 서버 애플리케이션 |
| **ZGC** | 매우 낮음 (<10ms) | 높음 | 높음 (15-20%) | 실시간 시스템, 대용량 힙 |
| **Shenandoah** | 낮음 (<10ms) | 중간 | 중간 | 응답 시간 중요 애플리케이션 |
| **Parallel GC** | 높음 | 매우 높음 | 낮음 | 배치 처리, 처리량 우선 |

### 3.4 CPU Shares와 CFS Quota의 JVM 영향

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CPU Limit Impact on JVM                                   │
│                                                                             │
│   Runtime.getRuntime().availableProcessors()                                │
│                                                                             │
│   - Java 10 이전: 호스트 CPU 수 반환 (컨테이너 무시)                          │
│   - Java 10+: CFS quota 기반 CPU 수 반환 (UseContainerSupport)              │
│                                                                             │
│   예: 8 core 노드, CPU limit = 2                                            │
│       availableProcessors() = 2                                             │
│                                                                             │
│   GC 스레드 수 = availableProcessors()                                       │
│   (ParallelGCThreads, ConcGCThreads)                                        │
│                                                                             │
│   CPU limit가 낮으면:                                                        │
│   - GC 스레드 감소 → GC 시간 증가                                            │
│   - 컴파일러 스레드 감소 → 워밍업 시간 증가                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

**명시적 GC 스레드 설정:**

```yaml
env:
  - name: JAVA_OPTS
    value: >-
      -XX:+UseG1GC
      -XX:ParallelGCThreads=4
      -XX:ConcGCThreads=2
```

### 3.5 JMX 모니터링 설정

```yaml
# jmx-exporter-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: java-app-with-jmx
spec:
  template:
    spec:
      containers:
        - name: app
          image: myapp:latest
          env:
            - name: JAVA_OPTS
              value: >-
                -XX:+UseContainerSupport
                -XX:MaxRAMPercentage=75.0
                -javaagent:/opt/jmx_prometheus_javaagent.jar=9404:/opt/jmx-config.yaml
          ports:
            - containerPort: 8080
              name: http
            - containerPort: 9404
              name: metrics
          volumeMounts:
            - name: jmx-config
              mountPath: /opt/jmx-config.yaml
              subPath: jmx-config.yaml
      volumes:
        - name: jmx-config
          configMap:
            name: jmx-exporter-config
---
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
      # JVM 메모리
      - pattern: 'java.lang<type=Memory><HeapMemoryUsage>(\w+)'
        name: jvm_memory_heap_$1
        type: GAUGE

      # GC 통계
      - pattern: 'java.lang<type=GarbageCollector, name=(.*)><(\w+)>'
        name: jvm_gc_$2
        labels:
          gc: $1
        type: GAUGE

      # 스레드
      - pattern: 'java.lang<type=Threading><(\w+)>'
        name: jvm_threading_$1
        type: GAUGE

      # 클래스 로딩
      - pattern: 'java.lang<type=ClassLoading><(\w+)>'
        name: jvm_classloading_$1
        type: GAUGE
```

### 3.6 JFR (Java Flight Recorder) 설정

```yaml
# jfr-enabled-deployment.yaml
env:
  - name: JAVA_OPTS
    value: >-
      -XX:+FlightRecorder
      -XX:StartFlightRecording=duration=60s,filename=/tmp/recording.jfr,settings=profile
      -XX:FlightRecorderOptions=stackdepth=256
```

JFR 데이터 수집 (운영 중):

```bash
# 실행 중인 JVM에서 JFR 시작
kubectl exec -it pod-name -- jcmd 1 JFR.start duration=60s filename=/tmp/recording.jfr

# JFR 파일 복사
kubectl cp pod-name:/tmp/recording.jfr ./recording.jfr
```

### 3.7 Spring Boot Actuator + Micrometer

```yaml
# application.yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics,prometheus
  endpoint:
    health:
      show-details: always
      probes:
        enabled: true
  metrics:
    export:
      prometheus:
        enabled: true
    distribution:
      percentiles-histogram:
        http.server.requests: true
      slo:
        http.server.requests: 10ms,50ms,100ms,200ms,500ms,1s,5s
    tags:
      application: ${spring.application.name}
```

**커스텀 메트릭 등록:**

```java
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import io.micrometer.core.instrument.Counter;

@Component
public class OrderMetrics {
    private final Timer orderProcessingTimer;
    private final Counter orderCounter;

    public OrderMetrics(MeterRegistry registry) {
        this.orderProcessingTimer = Timer.builder("order.processing.time")
            .description("Time taken to process orders")
            .publishPercentiles(0.5, 0.95, 0.99)
            .register(registry);

        this.orderCounter = Counter.builder("order.total")
            .description("Total number of orders")
            .tag("type", "all")
            .register(registry);
    }

    public void recordOrderProcessing(Runnable task) {
        orderProcessingTimer.record(task);
        orderCounter.increment();
    }
}
```

### 3.8 Grafana JVM 대시보드 패널

```json
{
  "panels": [
    {
      "title": "JVM Heap Usage",
      "targets": [
        {
          "expr": "jvm_memory_used_bytes{area=\"heap\", application=\"$application\"}",
          "legendFormat": "Used"
        },
        {
          "expr": "jvm_memory_committed_bytes{area=\"heap\", application=\"$application\"}",
          "legendFormat": "Committed"
        },
        {
          "expr": "jvm_memory_max_bytes{area=\"heap\", application=\"$application\"}",
          "legendFormat": "Max"
        }
      ]
    },
    {
      "title": "GC Pause Time",
      "targets": [
        {
          "expr": "rate(jvm_gc_pause_seconds_sum{application=\"$application\"}[5m])",
          "legendFormat": "{{gc}} - {{action}}"
        }
      ]
    },
    {
      "title": "Thread Count",
      "targets": [
        {
          "expr": "jvm_threads_live_threads{application=\"$application\"}",
          "legendFormat": "Live Threads"
        },
        {
          "expr": "jvm_threads_daemon_threads{application=\"$application\"}",
          "legendFormat": "Daemon Threads"
        }
      ]
    }
  ]
}
```

---

## 4. Python/Node.js 워크로드

### 4.1 Python (Gunicorn/uWSGI)

#### Worker 수 계산

```
Workers = (2 * CPU cores) + 1

예: CPU limit = 2 cores
    Workers = (2 * 2) + 1 = 5
```

#### Gunicorn 설정

```python
# gunicorn.conf.py
import multiprocessing

# Worker 설정
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"  # async 지원
worker_connections = 1000
max_requests = 10000
max_requests_jitter = 1000

# 타임아웃
timeout = 30
graceful_timeout = 30
keepalive = 5

# 메모리 관리
preload_app = True

# 로깅
accesslog = "-"
errorlog = "-"
loglevel = "info"
```

#### Python Deployment

```yaml
# python-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: python-api
spec:
  replicas: 3
  template:
    spec:
      containers:
        - name: api
          image: python-api:latest
          command: ["gunicorn"]
          args:
            - "--config=/app/gunicorn.conf.py"
            - "main:app"
          resources:
            requests:
              cpu: "500m"
              memory: "512Mi"
            limits:
              cpu: "2"
              memory: "1Gi"
          env:
            - name: PYTHONUNBUFFERED
              value: "1"
            - name: PYTHONDONTWRITEBYTECODE
              value: "1"
            # 메모리 프로파일링 활성화 (디버그용)
            - name: PYTHONTRACEMALLOC
              value: "1"
          ports:
            - containerPort: 8000
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 5
```

#### 메모리 프로파일링

```python
# memory_profiler.py
import tracemalloc
import linecache

def display_top_memory_usage(snapshot, limit=10):
    """메모리 사용량 상위 항목 출력"""
    top_stats = snapshot.statistics('lineno')

    print(f"Top {limit} memory consumers:")
    for stat in top_stats[:limit]:
        print(stat)

# 애플리케이션에서 사용
tracemalloc.start()
# ... 애플리케이션 코드 ...
snapshot = tracemalloc.take_snapshot()
display_top_memory_usage(snapshot)
```

### 4.2 Node.js

#### V8 힙 설정

```yaml
# nodejs-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nodejs-api
spec:
  replicas: 3
  template:
    spec:
      containers:
        - name: api
          image: nodejs-api:latest
          resources:
            requests:
              cpu: "500m"
              memory: "512Mi"
            limits:
              cpu: "2"
              memory: "1Gi"
          env:
            # V8 힙 제한 (컨테이너 메모리의 70-75%)
            - name: NODE_OPTIONS
              value: "--max-old-space-size=768"
            # I/O 집약적 워크로드용 스레드풀 확장
            - name: UV_THREADPOOL_SIZE
              value: "16"
          ports:
            - containerPort: 3000
          livenessProbe:
            httpGet:
              path: /health
              port: 3000
            initialDelaySeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: 3000
            initialDelaySeconds: 5
```

#### Cluster 모드 (멀티코어 활용)

```javascript
// cluster.js
const cluster = require('cluster');
const numCPUs = require('os').cpus().length;

if (cluster.isMaster) {
  console.log(`Master ${process.pid} is running`);

  // CPU 수만큼 워커 생성
  for (let i = 0; i < numCPUs; i++) {
    cluster.fork();
  }

  cluster.on('exit', (worker, code, signal) => {
    console.log(`Worker ${worker.process.pid} died`);
    // 워커 재시작
    cluster.fork();
  });
} else {
  // 워커에서 앱 실행
  require('./app');
  console.log(`Worker ${process.pid} started`);
}
```

**PM2 사용 시:**

```javascript
// ecosystem.config.js
module.exports = {
  apps: [{
    name: 'api',
    script: './app.js',
    instances: 'max',  // CPU 수만큼 인스턴스
    exec_mode: 'cluster',
    max_memory_restart: '750M',
    env: {
      NODE_ENV: 'production'
    }
  }]
};
```

#### 메모리 누수 감지

```javascript
// memory-monitor.js
const v8 = require('v8');

function logMemoryUsage() {
  const heapStats = v8.getHeapStatistics();
  const memoryUsage = process.memoryUsage();

  console.log({
    heapUsed: Math.round(memoryUsage.heapUsed / 1024 / 1024) + 'MB',
    heapTotal: Math.round(memoryUsage.heapTotal / 1024 / 1024) + 'MB',
    external: Math.round(memoryUsage.external / 1024 / 1024) + 'MB',
    rss: Math.round(memoryUsage.rss / 1024 / 1024) + 'MB',
    heapSizeLimit: Math.round(heapStats.heap_size_limit / 1024 / 1024) + 'MB'
  });
}

// 주기적으로 메모리 사용량 로깅
setInterval(logMemoryUsage, 30000);
```

---

## 5. Go/Rust 워크로드

### 5.1 Go

#### GOMAXPROCS 자동 설정

```go
// main.go
package main

import (
    _ "go.uber.org/automaxprocs" // 자동으로 GOMAXPROCS 설정
    "log"
)

func main() {
    // automaxprocs가 컨테이너 CPU limit 감지하여 GOMAXPROCS 설정
    log.Printf("GOMAXPROCS: %d", runtime.GOMAXPROCS(0))
    // ...
}
```

#### GOMEMLIMIT 설정

```yaml
# go-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: go-api
spec:
  template:
    spec:
      containers:
        - name: api
          image: go-api:latest
          resources:
            requests:
              cpu: "250m"
              memory: "256Mi"
            limits:
              cpu: "1"
              memory: "512Mi"
          env:
            # Go 1.19+ GOMEMLIMIT (컨테이너 메모리의 80-90%)
            - name: GOMEMLIMIT
              value: "450MiB"
            # GC 목표 비율 (기본값 100)
            - name: GOGC
              value: "100"
```

**GOMEMLIMIT 권장값:**

```
GOMEMLIMIT = Container Memory Limit * 0.8 ~ 0.9

예: Memory Limit = 512Mi
    GOMEMLIMIT = 450MiB (약 88%)
```

#### Go 리소스 효율성

```yaml
# Go의 리소스 효율적 특성
#
# 1. 빠른 시작 시간 (바이너리 직접 실행)
# 2. 낮은 메모리 오버헤드 (VM 없음)
# 3. 효율적인 GC (Go 1.19+ GOMEMLIMIT)
# 4. 컴파일된 바이너리로 일관된 성능

# 권장 리소스 설정
resources:
  requests:
    cpu: "100m"      # 시작에 많은 CPU 불필요
    memory: "128Mi"  # 기본 메모리 낮음
  limits:
    cpu: "500m"      # 버스트 허용
    memory: "256Mi"  # 실제 필요량 + 여유
```

### 5.2 Rust

#### 메모리 사용 패턴

```yaml
# rust-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rust-api
spec:
  template:
    spec:
      containers:
        - name: api
          image: rust-api:latest
          resources:
            requests:
              cpu: "100m"
              memory: "64Mi"
            limits:
              cpu: "500m"
              memory: "128Mi"
          # Rust는 GC가 없어 결정적 메모리 사용
          # 메모리 limit을 타이트하게 설정 가능
```

#### Tokio 런타임 설정

```rust
// main.rs
use tokio::runtime::Builder;

fn main() {
    // 워커 스레드 수 명시적 설정
    let runtime = Builder::new_multi_thread()
        .worker_threads(4)  // CPU cores에 맞춤
        .enable_all()
        .build()
        .unwrap();

    runtime.block_on(async {
        // 애플리케이션 코드
    });
}
```

환경 변수로 설정:

```yaml
env:
  # Tokio 워커 스레드 수
  - name: TOKIO_WORKER_THREADS
    value: "4"
```

#### jemalloc 사용

```toml
# Cargo.toml
[dependencies]
jemallocator = "0.5"

[profile.release]
lto = true
codegen-units = 1
```

```rust
// main.rs
#[global_allocator]
static GLOBAL: jemallocator::Jemalloc = jemallocator::Jemalloc;
```

### 5.3 컴파일 언어 장점

| 특성 | Go | Rust | JVM (비교) |
|-----|----|----|-----------|
| **시작 시간** | 수십 ms | 수십 ms | 수 초 |
| **메모리 오버헤드** | 낮음 | 매우 낮음 | 높음 |
| **GC** | 있음 (효율적) | 없음 | 있음 |
| **메모리 예측성** | 높음 | 매우 높음 | 중간 |
| **CPU 효율성** | 높음 | 매우 높음 | 높음 |
| **Cold Start** | 빠름 | 빠름 | 느림 |

---

## 6. 리소스 모니터링 대시보드

### 6.1 CPU Throttling 감지

```promql
# Throttling 비율 (5% 이상이면 limits 증가 필요)
sum(
  rate(container_cpu_cfs_throttled_periods_total{
    namespace="production",
    container!=""
  }[5m])
) by (namespace, pod, container)
/
sum(
  rate(container_cpu_cfs_periods_total{
    namespace="production",
    container!=""
  }[5m])
) by (namespace, pod, container)
* 100

# Throttling이 발생한 컨테이너 목록
(
  rate(container_cpu_cfs_throttled_periods_total[5m])
  /
  rate(container_cpu_cfs_periods_total[5m])
) > 0.05
```

### 6.2 메모리 압박 감지

```promql
# 메모리 사용률 (limit 대비)
container_memory_working_set_bytes{namespace="production", container!=""}
/
container_spec_memory_limit_bytes{namespace="production", container!=""}
* 100

# 90% 이상 사용 중인 컨테이너 (OOM 위험)
(
  container_memory_working_set_bytes{namespace="production"}
  /
  container_spec_memory_limit_bytes{namespace="production"}
) > 0.9

# OOM 발생 횟수
increase(kube_pod_container_status_last_terminated_reason{reason="OOMKilled"}[1h])
```

### 6.3 Request vs 실제 사용량

```promql
# CPU: Request 대비 실제 사용 비율 (목표: 70-80%)
sum(
  rate(container_cpu_usage_seconds_total{namespace="production", container!=""}[5m])
) by (namespace)
/
sum(
  kube_pod_container_resource_requests{namespace="production", resource="cpu"}
) by (namespace)
* 100

# Memory: Request 대비 실제 사용 비율
sum(
  container_memory_working_set_bytes{namespace="production", container!=""}
) by (namespace)
/
sum(
  kube_pod_container_resource_requests{namespace="production", resource="memory"}
) by (namespace)
* 100
```

### 6.4 과잉 프로비저닝 감지

```promql
# CPU 과잉 프로비저닝 (사용률 30% 미만)
(
  sum(rate(container_cpu_usage_seconds_total{namespace="production"}[5m])) by (pod, container)
  /
  sum(kube_pod_container_resource_requests{namespace="production", resource="cpu"}) by (pod, container)
) < 0.3

# 메모리 과잉 프로비저닝 (사용률 30% 미만)
(
  sum(container_memory_working_set_bytes{namespace="production"}) by (pod, container)
  /
  sum(kube_pod_container_resource_requests{namespace="production", resource="memory"}) by (pod, container)
) < 0.3
```

### 6.5 Grafana 패널 예시

```json
{
  "panels": [
    {
      "title": "CPU Throttling by Container",
      "type": "timeseries",
      "targets": [
        {
          "expr": "sum(rate(container_cpu_cfs_throttled_periods_total{namespace=\"$namespace\"}[5m])) by (pod, container) / sum(rate(container_cpu_cfs_periods_total{namespace=\"$namespace\"}[5m])) by (pod, container) * 100",
          "legendFormat": "{{pod}}/{{container}}"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "percent",
          "thresholds": {
            "mode": "absolute",
            "steps": [
              { "value": 0, "color": "green" },
              { "value": 5, "color": "yellow" },
              { "value": 15, "color": "red" }
            ]
          }
        }
      }
    },
    {
      "title": "Memory Usage vs Limit",
      "type": "gauge",
      "targets": [
        {
          "expr": "sum(container_memory_working_set_bytes{namespace=\"$namespace\", pod=\"$pod\"}) / sum(container_spec_memory_limit_bytes{namespace=\"$namespace\", pod=\"$pod\"}) * 100"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "percent",
          "max": 100,
          "thresholds": {
            "steps": [
              { "value": 0, "color": "green" },
              { "value": 70, "color": "yellow" },
              { "value": 90, "color": "red" }
            ]
          }
        }
      }
    }
  ]
}
```

### 6.6 알림 규칙

```yaml
# resource-alerts.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: resource-alerts
  namespace: monitoring
spec:
  groups:
    - name: resource-optimization
      rules:
        # CPU Throttling 알림
        - alert: HighCPUThrottling
          expr: |
            (
              sum(rate(container_cpu_cfs_throttled_periods_total[5m])) by (namespace, pod, container)
              /
              sum(rate(container_cpu_cfs_periods_total[5m])) by (namespace, pod, container)
            ) > 0.25
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "High CPU throttling on {{ $labels.pod }}/{{ $labels.container }}"
            description: "Container {{ $labels.container }} in pod {{ $labels.pod }} is being throttled {{ $value | humanizePercentage }}"

        # 메모리 부족 임박 알림
        - alert: MemoryNearLimit
          expr: |
            (
              container_memory_working_set_bytes
              /
              container_spec_memory_limit_bytes
            ) > 0.9
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "Memory usage near limit on {{ $labels.pod }}"
            description: "Container {{ $labels.container }} is using {{ $value | humanizePercentage }} of memory limit"

        # OOM 발생 알림
        - alert: ContainerOOMKilled
          expr: |
            increase(kube_pod_container_status_last_terminated_reason{reason="OOMKilled"}[5m]) > 0
          for: 0m
          labels:
            severity: critical
          annotations:
            summary: "Container OOMKilled in {{ $labels.namespace }}"
            description: "Container {{ $labels.container }} in pod {{ $labels.pod }} was OOMKilled"

        # 과잉 프로비저닝 알림
        - alert: ResourceOverProvisioned
          expr: |
            (
              sum(rate(container_cpu_usage_seconds_total[1h])) by (namespace, pod, container)
              /
              sum(kube_pod_container_resource_requests{resource="cpu"}) by (namespace, pod, container)
            ) < 0.2
          for: 24h
          labels:
            severity: info
          annotations:
            summary: "Resource over-provisioned for {{ $labels.pod }}"
            description: "Container {{ $labels.container }} is using only {{ $value | humanizePercentage }} of requested CPU"
```

---

## 7. Auto Mode에서의 리소스 최적화

### 7.1 NodePool 인스턴스 타입 영향

```yaml
# EKS Auto Mode NodePool 설정
apiVersion: eks.amazonaws.com/v1
kind: NodePool
metadata:
  name: general-purpose
spec:
  template:
    spec:
      requirements:
        - key: "node.kubernetes.io/instance-type"
          operator: In
          values:
            - m7i.large      # 2 vCPU, 8 GiB
            - m7i.xlarge     # 4 vCPU, 16 GiB
            - m7i.2xlarge    # 8 vCPU, 32 GiB
```

**인스턴스 크기와 Bin-packing:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Instance Size Impact on Bin-Packing                       │
│                                                                             │
│   작은 인스턴스 (m7i.large: 2 vCPU, 8 GiB)                                  │
│   ┌─────────────────────┐                                                   │
│   │ Pod A (500m, 1Gi)  │  낮은 활용도, 많은 노드                             │
│   │ Pod B (500m, 1Gi)  │  노드당 오버헤드 높음                              │
│   │ [여유 공간 적음]    │  스케줄링 실패 가능성 높음                         │
│   └─────────────────────┘                                                   │
│                                                                             │
│   큰 인스턴스 (m7i.2xlarge: 8 vCPU, 32 GiB)                                 │
│   ┌─────────────────────────────────────────────────────────────────┐       │
│   │ Pod A │ Pod B │ Pod C │ Pod D │ Pod E │ Pod F │ [여유 공간]    │       │
│   │ (1Gi) │ (1Gi) │ (1Gi) │ (1Gi) │ (1Gi) │ (1Gi) │               │       │
│   └─────────────────────────────────────────────────────────────────┘       │
│   높은 활용도, 적은 노드, 낮은 오버헤드                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Over-provisioning vs Right-sizing

```yaml
# Over-provisioning 전략: 버스트 대응용 여유 노드
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pause-overprovisioner
spec:
  replicas: 2
  template:
    spec:
      priorityClassName: overprovisioner  # 낮은 우선순위
      containers:
        - name: pause
          image: registry.k8s.io/pause:3.9
          resources:
            requests:
              cpu: "2"
              memory: "4Gi"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: overprovisioner
value: -1
globalDefault: false
description: "Priority class for overprovisioner"
```

### 7.3 노드 통합 동작

Auto Mode의 노드 통합 동작:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Node Consolidation in Auto Mode                        │
│                                                                             │
│   Before Consolidation:                                                     │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                     │
│   │   Node A     │  │   Node B     │  │   Node C     │                     │
│   │  [Pod 1]     │  │  [Pod 2]     │  │  [Pod 3]     │                     │
│   │  [25% 활용]  │  │  [30% 활용]  │  │  [20% 활용]  │                     │
│   └──────────────┘  └──────────────┘  └──────────────┘                     │
│                                                                             │
│   After Consolidation:                                                      │
│   ┌──────────────────────────────────┐                                     │
│   │            Node A                │  Node B, C: 종료됨                   │
│   │  [Pod 1] [Pod 2] [Pod 3]        │                                     │
│   │        [75% 활용]                │                                     │
│   └──────────────────────────────────┘                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.4 클러스터 수준 리소스 효율성 메트릭

```promql
# 클러스터 CPU 활용률
sum(rate(container_cpu_usage_seconds_total{container!=""}[5m]))
/
sum(kube_node_status_allocatable{resource="cpu"})
* 100

# 클러스터 메모리 활용률
sum(container_memory_working_set_bytes{container!=""})
/
sum(kube_node_status_allocatable{resource="memory"})
* 100

# 노드당 Pod 밀도
count(kube_pod_info) by (node)
/
count(kube_node_info)

# Pending Pod 수 (리소스 부족 지표)
count(kube_pod_status_phase{phase="Pending"})
```

---

## 관련 문서

- [관측성 스택 운영](./09-observability-stack.md)
- [EKS 클러스터 생성](../eks/02-eks-cluster-creation-part1.md)
- [Karpenter 오토스케일링](../autoscaling/02-karpenter.md)
- [EKS Auto Mode](../eks-auto-mode/01-getting-started.md)

---

< [이전: 관측성 스택 운영](./09-observability-stack.md) | [목차](./README.md) | [다음: EKS 업그레이드](./11-upgrade-operations.md) >
