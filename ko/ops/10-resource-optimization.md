# 리소스 최적화: Requests/Limits와 언어별 런타임

> 검토: 2026-09-11. 예제 검증 환경은 Kubernetes 1.36 스키마,
> Java 21 / Spring Boot 4.1.1, Python 3.12 / Gunicorn 26.2.0,
> Node.js 24.21, Go 1.27.1, Rust 1.98 / Tokio 1.53.1입니다.

리소스 크기는 언어 이름이나 고정 비율만으로 정하지 않습니다. 대표 부하·시작·재시작·GC·
장애 상황에서 처리량과 지연 SLO를 측정하고 requests, limits, 복제본, 런타임 동시성을 함께 조정합니다.
예제의 메모리 비율과 임계값은 시험 시작점이며 성능 보장이 아닙니다.

## 1. Requests, limits와 QoS

| 항목 | Requests | Limits |
|---|---|---|
| CPU | 스케줄링 계산과 CPU 경합 시 상대적 가중치에 사용 | Linux cgroup CPU quota로 실행량 제한 가능 |
| 메모리 | 스케줄링 계산에 사용 | reclaim으로 해결하지 못하는 할당 압박에서 cgroup OOM 발생 가능 |
| 미설정 | admission 기본값과 상위 정책 확인 필요 | 해당 컨테이너 한도가 없을 수 있지만 노드·상위 cgroup 한도는 존재 |

request는 물리 CPU 고정이나 메모리의 선할당이 아니며 애플리케이션 성능을 절대 보장하지 않습니다.
limit만 지정하면 다른 admission 기본값이 없는 경우 같은 값이 request로 복사됩니다.
LimitRange 등을 거친 **실제 Pod 사양**을 확인합니다.

아래는 Pod-level resources를 사용하지 않는 컨테이너 수준 예제입니다.
`resource-demo` 네임스페이스를 먼저 만들고, 기본 리소스를 주입하는 LimitRange가 없는 환경에서
QoS를 비교합니다. Guaranteed는 CPU·메모리의 request와 limit이 모두 양수이고 같아야 하며,
일반·init 컨테이너 등의 조건도 함께 충족해야 합니다.

```yaml
# qos-pods.yaml
apiVersion: v1
kind: Pod
metadata:
  name: guaranteed
  namespace: resource-demo
spec:
  containers:
  - name: app
    image: ghcr.io/stefanprodan/podinfo:6.15.0@sha256:ec73780a8425f59ea49f5bc8cdff0d598805a224fbaa1f86c67a244f250fa9da
    resources:
      requests:
        cpu: 500m
        memory: 256Mi
      limits:
        cpu: 500m
        memory: 256Mi
---
apiVersion: v1
kind: Pod
metadata:
  name: burstable
  namespace: resource-demo
spec:
  containers:
  - name: app
    image: ghcr.io/stefanprodan/podinfo:6.15.0@sha256:ec73780a8425f59ea49f5bc8cdff0d598805a224fbaa1f86c67a244f250fa9da
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        memory: 256Mi
---
apiVersion: v1
kind: Pod
metadata:
  name: besteffort
  namespace: resource-demo
spec:
  containers:
  - name: app
    image: ghcr.io/stefanprodan/podinfo:6.15.0@sha256:ec73780a8425f59ea49f5bc8cdff0d598805a224fbaa1f86c67a244f250fa9da
    resources: {}
```

BestEffort는 CPU·메모리 request/limit이 모두 없는 경우이며 나머지는 Burstable이 될 수 있습니다.
Pod-level resources나 sidecar/init 자원 계산을 사용하는 경우 해당 버전의 규칙도 확인합니다.

**QoS는 절대적인 eviction 순서가 아닙니다.** 메모리 압박 시 kubelet은 request 초과 여부,
Pod Priority, request 대비 사용량을 고려합니다. Guaranteed와 request 이내 Burstable이
나중에 고려되는 경향은 있지만 “Guaranteed는 어떤 상황에도 마지막”이라고 보장할 수 없습니다.
DiskPressure의 ephemeral-storage 퇴거와 컨테이너 limit OOM도 구별합니다.
OOMKilled는 보통 컨테이너의 종료 reason이며 Pod phase 이름이 아닙니다.
프로세스 일부가 종료되거나, PID 1 종료 후 restartPolicy에 따라 컨테이너가 재시작할 수 있습니다.

### CPU quota와 메모리 한계

cgroup v1은 `cpu.cfs_quota_us` / `cpu.cfs_period_us`, v2는 `cpu.max`를 사용합니다.
100ms는 흔한 quota period이지 모든 환경의 고정값이 아닙니다.
500m, 100ms 예제의 실행 예산은 period당 총 50ms이며 여러 스레드가 이를 함께 소모합니다.
Throttling은 지연뿐 아니라 처리량에도 영향을 줄 수 있습니다.
throttled-period 비율은 “스로틀링이 있었던 period의 비율”이며 손실 CPU 시간 비율이 아닙니다.

메모리 limit은 힙 크기와 같지 않습니다. cgroup v1의 `memory.limit_in_bytes`와 v2의
`memory.max` 경로를 혼용하지 않습니다. 런타임의 전체 RSS, native 할당, thread stack,
page cache와 memory-backed emptyDir 등을 함께 살펴봅니다.
limit 접근 때 메모리 사용량을 검사하는 liveness probe로 먼저 재시작시키면 OOM 원인을 숨기고
재시작 루프를 만들 수 있으므로 일반적인 해결책으로 사용하지 않습니다.

CPU limit을 없애면 해당 컨테이너 quota로 인한 제한은 줄일 수 있지만 CPU 경합·상위 quota·
노드 한계까지 없어지지 않습니다. request, 우선순위, 격리, 정책과 SLO를 함께 검토합니다.

### 네임스페이스 기본값과 총량

LimitRange는 admission 기본값/개별 리소스 제약, ResourceQuota는 네임스페이스의
리소스 요청·한도·객체 수 등에 대한 admission 총량입니다. 실제 CPU 사용량이나 비용을
실시간으로 제한하는 기능은 아닙니다. 다음 정책은 `production` 네임스페이스가 있어야 적용됩니다.

```yaml
# namespace-policy.yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: defaults
  namespace: production
spec:
  limits:
  - type: Container
    default:
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 128Mi
    min:
      memory: 16Mi
    max:
      memory: 4Gi
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: budget
  namespace: production
spec:
  hard:
    requests.cpu: '8'
    requests.memory: 16Gi
    limits.memory: 32Gi
    pods: '20'
```

## 2. 측정과 VPA

평균만 보지 않고 대표 기간의 분포, 피크, 시작 비용과 메모리 증가를 관찰합니다.
P70 request/P99 limit 같은 정책은 조직의 가설로 시험할 수 있지만 모든 워크로드의 정답은 아닙니다.
GC·model load·JIT·암호화·sidecar·배치 입력 크기 때문에 같은 언어에서도 결과가 크게 다릅니다.
메모리 누수를 limit 증가만으로 덮거나, 유휴 상태의 재해 복구/대기 Pod를 낭비로 자동 분류하지 않습니다.

VPA 설치와 Goldilocks의 버전 고정 예제는 [스케일링 장](./06-scaling-strategies.md)을 사용합니다.
Goldilocks는 대상 네임스페이스/워크로드에 VPA를 생성·표시하며 설치만으로 모든 워크로드가
자동 최적화되는 것은 아닙니다. 다음 VPA는 뒤의 `resource-java` Deployment를 관찰합니다.

```yaml
# vpa.yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: resource-java
  namespace: production
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: resource-java
  updatePolicy:
    updateMode: 'Off'
  resourcePolicy:
    containerPolicies:
    - containerName: app
      controlledValues: RequestsOnly
      minAllowed:
        cpu: 100m
        memory: 256Mi
      maxAllowed:
        cpu: '4'
        memory: 4Gi
```

`Off`는 추천만 제공합니다. `target`은 request 추천이며 lower/upper bound는 추천 범위입니다.
upperBound를 그대로 메모리 limit으로 쓰거나 uncappedTarget을 실제 적용값으로 오해하지 않습니다.
`RequestsAndLimits`는 기존 비율에 따라 limit도 조정할 수 있는 정책이지 upperBound를 limit으로
복사하는 기능이 아닙니다.

VPA 1.7.1에서 `Auto`는 deprecated인 `Recreate` 동작입니다. in-place 지원은
`InPlaceOrRecreate`/`InPlace`의 조건과 Kubernetes 기능 지원을 확인합니다.
`Initial`도 새 Pod의 request를 바꾸므로 request 기반 HPA의 분모에 영향을 줍니다.
“Initial이면 HPA와 무조건 충돌하지 않는다”는 설명은 부정확합니다.

Pod 한 개가 SLO를 지키며 200 RPS를 처리하고 목표가 1,000 RPS라면 정상 상태에는 5개가 필요합니다.
Pod 한 개 손실 후에도 같은 처리량이 필요하면 최소 6개가 필요합니다.
이것은 3개 AZ 중 하나의 상실까지 보장하는 계산이 아닙니다.
“20% 여유”가 추가 용량 20%인지, 가용 용량의 20%를 비워 두겠다는 뜻인지도 구분합니다.
후자의 계산은 `ceil(1000 / (200 × 0.8)) = 7`입니다.

## 3. JVM: 힙과 컨테이너 메모리

`MaxRAMPercentage`는 JVM이 감지한 메모리 기준의 힙 ergonomics 입력입니다.
항상 75%가 최적이거나 Pod limit 변경을 즉시 재추적하는 자동 크기 조절기는 아닙니다.
`-Xmx`, `-XX:MaxRAM`, 작은 힙에 대한 ergonomics 등 다른 옵션도 영향을 줍니다.
힙 밖에는 metaspace, code cache, stack, direct buffer, JNI와 allocator 메모리가 필요합니다.
일정한 25%가 모든 애플리케이션의 non-heap을 충당한다는 보장은 없습니다.

`JAVA_OPTS`는 JVM이 자동으로 읽는 표준 환경 변수가 아닙니다.
이미지 entrypoint가 이를 명령줄에 추가해야 동작합니다. 아래는 JVM이 읽는
`JAVA_TOOL_OPTIONS`와 직접적인 `java -jar` 명령을 사용합니다.
60%는 검증 시작점이며 실제 profile로 조정합니다.

다음 Spring Boot 예제는 Java 21과 Boot 4.1.1로 빌드했습니다.
프로젝트 경로대로 파일을 저장합니다. 실행에 필요한 전체 Maven 설정과 애플리케이션입니다.

```xml
<!-- java/pom.xml -->
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>4.1.1</version>
    <relativePath/>
  </parent>
  <groupId>example</groupId>
  <artifactId>resource-api</artifactId>
  <version>1.0.0</version>
  <properties>
    <java.version>21</java.version>
  </properties>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-webmvc</artifactId>
    </dependency>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-actuator</artifactId>
    </dependency>
    <dependency>
      <groupId>io.micrometer</groupId>
      <artifactId>micrometer-registry-prometheus</artifactId>
    </dependency>
  </dependencies>
  <build>
    <plugins>
      <plugin>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-maven-plugin</artifactId>
      </plugin>
    </plugins>
  </build>
</project>
```

```java
// java/src/main/java/example/ResourceApi.java
package example;

import java.util.Map;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@SpringBootApplication
@RestController
public class ResourceApi {
    private final Timer workTimer;

    public ResourceApi(MeterRegistry registry) {
        workTimer = Timer.builder("demo.work")
                .description("Synthetic work duration")
                .publishPercentileHistogram()
                .register(registry);
    }

    @GetMapping("/work")
    public Map<String, String> work() {
        return workTimer.record(() -> Map.of("status", "ok"));
    }

    public static void main(String[] args) {
        SpringApplication.run(ResourceApi.class, args);
    }
}
```

```yaml
# java/src/main/resources/application.yaml
spring:
  application:
    name: resource-api
management:
  endpoints:
    web:
      exposure:
        include: health,prometheus
  endpoint:
    health:
      show-details: never
      probes:
        enabled: true
  prometheus:
    metrics:
      export:
        enabled: true
  metrics:
    tags:
      application: ${spring.application.name}
    distribution:
      percentiles-histogram:
        http.server.requests: true
        jvm.gc.pause: true
      slo:
        http.server.requests: 10ms,50ms,100ms,500ms,1s
```

```bash
mvn -f java/pom.xml package
java -jar java/target/resource-api-1.0.0.jar
```

위 최소 프로젝트는 Maven wrapper 파일을 포함하지 않으므로 직접 만든 wrapper가 없으면
`mvn package`를 사용합니다. 이미지에는 빌드한 jar를 `/app/resource-api.jar`로 넣고
Java 21 호환 런타임을 포함해야 합니다. 아래 `registry.example.com` 이미지는 **교체할 자리**입니다.
namespace, 레지스트리 접근과 이미지 빌드는 별도 준비 항목입니다.
readiness/liveness는 실제 제공되는 Actuator endpoint와 연결했습니다.

```yaml
# java-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: resource-java
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: resource-java
  template:
    metadata:
      labels:
        app: resource-java
    spec:
      terminationGracePeriodSeconds: 30
      containers:
      - name: app
        image: registry.example.com/team/resource-java:1.0.0
        command:
        - java
        - -jar
        - /app/resource-api.jar
        env:
        - name: JAVA_TOOL_OPTIONS
          value: -XX:+UseContainerSupport -XX:MaxRAMPercentage=60.0 -XX:+UseG1GC -XX:+HeapDumpOnOutOfMemoryError
            -XX:HeapDumpPath=/diagnostics
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: '2'
            memory: 2Gi
        ports:
        - name: http
          containerPort: 8080
        startupProbe:
          httpGet:
            path: /actuator/health/liveness
            port: http
          periodSeconds: 5
          failureThreshold: 30
        livenessProbe:
          httpGet:
            path: /actuator/health/liveness
            port: http
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /actuator/health/readiness
            port: http
          periodSeconds: 5
        volumeMounts:
        - name: diagnostics
          mountPath: /diagnostics
      volumes:
      - name: diagnostics
        emptyDir:
          sizeLimit: 3Gi
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: resource-java
```

Actuator의 Prometheus 설정은 `management.prometheus.metrics.export` 경로입니다.
메트릭과 health detail을 무조건 외부에 공개하지 않습니다.
`percentiles-histogram`을 켠 metric만 `_bucket` 기반 쿼리를 사용할 수 있으며,
클라이언트 계산 percentile을 여러 Pod에서 단순 평균내어 전체 percentile로 만들 수 없습니다.
Micrometer Timer 자체가 count/sum을 제공하므로 같은 의미의 Counter를 중복 등록할 필요는 없습니다.

HeapDumpOnOutOfMemoryError는 JVM의 Java OOME에 대한 옵션입니다. 커널 SIGKILL에서는
힙 덤프나 종료 hook 실행을 기대할 수 없습니다. emptyDir 진단 파일은 Pod 삭제 시 사라지고
동일 파일명 충돌·디스크 부족도 처리해야 합니다. 힙 덤프에는 민감한 애플리케이션 데이터가
포함될 수 있으므로 접근·보존을 제한합니다.
`ScheduleAnyway`는 선호이며 엄격한 AZ 분산 보장이 아닙니다.

### GC와 CPU

| 선택 | 확인할 조건 |
|---|---|
| G1 | 일반적인 시작점. pause target은 목표이지 최대 지연 보장이 아님 |
| ZGC | 사용하는 JDK 버전의 generational 모드와 CPU/메모리 예산 검증 |
| Shenandoah | 선택한 JDK 배포판·버전에서 실제 제공하는지 확인 |
| Parallel / Serial | 처리량·작은 힙 등 워크로드 조건으로 비교 |

Java 21에서 generational ZGC는 `-XX:+UseZGC -XX:+ZGenerational`로 사용할 수 있습니다.
Java 23은 generational 기본값, Java 24는 non-generational 제거로 해당 선택 옵션이 obsolete입니다.
Java 25에서도 obsolete 경고와 향후 만료를 구별해야 합니다. Java 17에 위 옵션을 그대로 넣지 않습니다.
현행 generational-only JDK에서는 `-XX:+UseZGC`를 사용하고 정확한 버전에서 시작을 검증합니다.
고정된 GC별 지연·처리량 숫자는 벤치마크 없이 보장하지 않습니다.

`availableProcessors()`와 GC worker 수가 항상 같지는 않습니다.
quota·affinity·JDK 버전·collector ergonomics가 영향을 줍니다.
무조건 GC thread 수를 늘리면 낮은 CPU quota에서 더 빠르게 예산을 소모할 수 있습니다.
시작 시간이 긴 경우 startupProbe와 실제 JIT/GC/CPU 관측을 함께 사용합니다.

### JMX와 JFR

JMX exporter 1.6.0 jar를 이미지에 포함하거나 공식 배포 파일과 체크섬을 확인해 준비합니다.
아래 설정은 실제 JVM의 메모리·thread·GC MBean에서 검증했습니다.
Micrometer 메트릭 이름과 JMX 메트릭 이름은 별개이므로 대시보드에서 혼용하지 않습니다.
GC CollectionTime은 ms에서 seconds로 변환했습니다.

```yaml
# jmx-config.yaml
startDelaySeconds: 0
lowercaseOutputName: true
lowercaseOutputLabelNames: true
includeObjectNames:
  - "java.lang:type=Memory"
  - "java.lang:type=Threading"
  - "java.lang:type=GarbageCollector,name=*"
rules:
  - pattern: 'java.lang<type=Memory><HeapMemoryUsage>(used|committed|max)'
    name: demo_jmx_heap_$1_bytes
    type: GAUGE
  - pattern: 'java.lang<type=Threading><>ThreadCount'
    name: demo_jmx_threads
    type: GAUGE
  - pattern: 'java.lang<name=(.+), type=GarbageCollector><>CollectionCount'
    name: demo_jmx_gc_collections_total
    labels:
      gc: "$1"
    type: COUNTER
  - pattern: 'java.lang<name=(.+), type=GarbageCollector><>CollectionTime'
    name: demo_jmx_gc_collection_seconds_total
    valueFactor: 0.001
    labels:
      gc: "$1"
    type: COUNTER
```

```bash
java -javaagent:jmx_prometheus_javaagent-1.6.0.jar=127.0.0.1:9404:jmx-config.yaml   -jar java/target/resource-api-1.0.0.jar
```

이 명령은 로컬 진단용으로 loopback에 바인딩합니다. Prometheus가 다른 Pod에서 읽는 구성이라면
명시적 수집 포트·ServiceMonitor·접근 제어를 추가합니다.
JMX exporter가 jar 경로에 없으면 JVM은 시작하지 않습니다.
NMT는 JVM 시작 시 `-XX:NativeMemoryTracking=summary`를 지정해야 하며, JVM 밖의 모든
라이브러리 할당을 완전히 설명하는 RSS 회계는 아닙니다.

JFR을 실행 중에 수집할 때는 JDK 도구, 같은 사용자 권한, attach 허용과 쓰기 가능한 경로가 필요합니다.
아래 `PID`는 실제 Java PID로 교체합니다. PID 1이라고 가정하지 않습니다.

```bash
jcmd PID VM.native_memory summary
jcmd PID JFR.start name=profile settings=profile duration=60s filename=/diagnostics/profile.jfr
jfr summary /diagnostics/profile.jfr
```

컨테이너에서 `kubectl cp`를 사용할 때는 선택한 container와 tar 설치 여부도 확인합니다.
recording 종료 후 복사하며 heap/JFR 파일이 프로세스 종료나 Pod 교체까지 보존된다고 가정하지 않습니다.

## 4. Python: worker 수와 프로파일링

호스트 `multiprocessing.cpu_count()`에 `2 × CPU + 1`을 적용하면 컨테이너 quota보다
많은 프로세스를 만들 수 있습니다. CPU-bound/IO-bound 구분, GIL/확장 모듈,
worker당 RSS와 요청 동시성으로 시험합니다. “CPU당 2–4개가 항상 정답”이라는 공식은 없습니다.
아래 WSGI Flask 예제는 `WEB_CONCURRENCY`를 실제로 읽으며 기본 1개 worker, 2개 thread에서 시작합니다.

```text
# python/requirements.txt
Flask==3.1.3
gunicorn==26.2.0
```

```python
# python/app.py
from flask import Flask


def create_app():
    app = Flask(__name__)

    @app.get("/health/live")
    @app.get("/health/ready")
    def health():
        # Process-only health for this minimal example.
        return {"status": "ok"}

    return app
```

```python
# python/gunicorn.conf.py
import os


def positive_int(name, default):
    value = os.environ.get(name, str(default))
    if not value.isdecimal() or int(value) < 1:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


bind = os.environ.get("HTTP_BIND", "0.0.0.0:8000")
workers = positive_int("WEB_CONCURRENCY", 1)
threads = positive_int("GUNICORN_THREADS", 2)
worker_class = "gthread"  # WSGI Flask, not an ASGI worker.
control_socket_disable = True  # No local administration socket in this example.
preload_app = False
timeout = 30
graceful_timeout = 25
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
accesslog = "-"
errorlog = "-"
loglevel = "info"
```

```bash
python -m venv .venv
.venv/bin/python -m pip install -r python/requirements.txt
WEB_CONCURRENCY=2 GUNICORN_THREADS=2   .venv/bin/python -m gunicorn --chdir python   --config python/gunicorn.conf.py 'app:create_app()'
```

이 health endpoint는 예제 프로세스만 확인합니다. 실제 의존 서비스 readiness는 애플리케이션에 맞게
구현합니다. Flask 3에는 제거된 `before_first_request`를 쓰지 않습니다.
Gunicorn 26의 관리용 control socket은 이 최소 예제에서 껐습니다.

Flask WSGI와 FastAPI 등의 ASGI를 구별합니다. Gunicorn 26에는 ASGI worker도 있으며,
Uvicorn을 선택할 경우 deprecated인 `uvicorn.workers`와 별도 `uvicorn-worker` 패키지를 구별합니다.
예제의 gthread 설정을 ASGI 앱에 그대로 적용하지 않습니다.
`preload_app`은 copy-on-write 이점과 fork 이전에 생성한 thread/connection/client의 문제를 함께 검토합니다.
worker 재시작 횟수 제한은 누수의 근본 해결책이 아닙니다.

tracemalloc은 Python이 추적하는 할당을 관찰하며 전체 native/RSS를 설명하지 않습니다.
다음은 명시적으로 실행하는 로컬 진단입니다. HTTP debug endpoint로 외부에 노출하지 않습니다.

```python
# python/profile_allocations.py
import tracemalloc


def profile_allocation_delta(workload):
    """Run an explicit local diagnostic; this is not an HTTP debug endpoint."""
    tracemalloc.start(10)
    try:
        before = tracemalloc.take_snapshot()
        result = workload()
        after = tracemalloc.take_snapshot()
        for statistic in after.compare_to(before, "lineno")[:10]:
            print(statistic)
        return result
    finally:
        tracemalloc.stop()


if __name__ == "__main__":
    profile_allocation_delta(lambda: [bytearray(1024) for _ in range(100)])
```

## 5. Node.js: old space와 전체 메모리

`--max-old-space-size` 단위는 MiB이며 V8 old-space 설정입니다.
전체 RSS 상한이 아니고 young generation, external/Buffer, native 메모리 등이 별도로 필요합니다.
여러 worker 프로세스가 있으면 각 프로세스의 힙 예산도 합산해야 합니다.
Node.js 20은 2026년 4월 EOL이므로 새 예제는 지원 중인 Node.js 24를 사용합니다.

다음은 단일 Node 프로세스에서 health endpoint, 메모리 관찰과 SIGTERM 종료를 구현한 예제입니다.
비율만 보고 `global.gc()`를 반복 호출하는 것을 일반적인 최적화로 제시하지 않습니다.
`--expose-gc`는 검증한 Node 24에서 NODE_OPTIONS로 허용되지만, 사용 가능하다는 것과
운영에서 강제 GC가 효과적이라는 것은 별개입니다.

```javascript
// node/server.cjs
const http = require('node:http');

const port = Number(process.env.PORT || 3000);
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error('PORT must be an integer between 1 and 65535');
}
let draining = false;
const server = http.createServer((req, res) => {
  if (!['/health/live', '/health/ready'].includes(req.url)) {
    res.writeHead(404).end();
    return;
  }
  const status = draining && req.url === '/health/ready' ? 503 : 200;
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ status: status === 200 ? 'ok' : 'draining' }));
});
server.listen(port, process.env.HTTP_HOST || '0.0.0.0');

const monitor = setInterval(() => {
  const { rss, heapUsed, heapTotal, external, arrayBuffers } = process.memoryUsage();
  console.log(JSON.stringify({ rss, heapUsed, heapTotal, external, arrayBuffers }));
}, 30000);
monitor.unref();

function shutdown() {
  if (draining) return;
  draining = true;
  clearInterval(monitor);
  server.close(() => process.exit(0));
  setTimeout(() => {
    server.closeAllConnections();
    process.exit(1);
  }, 10000).unref();
}
process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
```

```bash
NODE_OPTIONS="--max-old-space-size=512" node node/server.cjs
```

`UV_THREADPOOL_SIZE`는 libuv thread pool을 사용하는 파일 I/O·일부 DNS·암호화 작업 등에
영향을 줍니다. 모든 네트워크 I/O가 이 pool에서 실행되는 것은 아닙니다.
thread 수를 늘리면 stack·동시 작업 메모리도 늘 수 있습니다.
프로세스 시작 전에 설정하고 실제 부하로 평가합니다.

Node cluster를 쓴다면 `isPrimary`를 사용하고 worker 수를 명시적으로 제한합니다.
`os.cpus().length`나 PM2 `instances: max`가 quota를 정확히 반영한다고 가정하지 않습니다.
`availableParallelism()`도 모든 cgroup 제약을 정확히 환산하는 worker 공식으로 간주하지 않습니다.
worker crash 재시작에는 backoff와 종료 중 재생성 방지가 필요하며, Kubernetes의 Pod 복제와
프로세스 복제를 함께 사용하면 전체 worker 수와 메모리를 곱해서 계산합니다.

## 6. Go와 Rust

### Go

Go 1.25부터 기본 GOMAXPROCS가 Linux cgroup CPU quota를 고려합니다.
`go.mod` 언어 버전과 GODEBUG 호환성 기본값도 영향을 주며 새 예제는 `go 1.25.0` 이상을 사용합니다.
현재 검증은 Go 1.27.1로 수행했습니다.
수동 GOMAXPROCS 환경 변수나 양수 `runtime.GOMAXPROCS(n)` 호출은 자동 갱신을 끕니다.
조회용 `runtime.GOMAXPROCS(0)`는 변경하지 않습니다.

현재 런타임은 quota를 올림하고 logical CPU/affinity 등도 고려합니다.
논리 CPU와 affinity가 충분한 경우 기본값 2 미만으로 내려가지 않는 조건도 있어
`500m → 항상 1` 같은 단순 공식은 맞지 않습니다.
`automaxprocs`의 버전/반올림 정책과 Go 내장 기본값을 동일하게 취급하거나 둘을 무조건 중복 적용하지 않습니다.
CPU request만으로 quota를 계산하지 않습니다.

```text
// go/go.mod
module example.com/resource-probe

go 1.25.0
```

```go
// go/main.go
package main

import (
	"encoding/json"
	"os"
	"runtime"
	"runtime/debug"
)

func main() {
	var memory runtime.MemStats
	runtime.ReadMemStats(&memory)
	// A negative value queries the current setting without changing it.
	limit := debug.SetMemoryLimit(-1)
	result := map[string]any{
		"gomaxprocs":           runtime.GOMAXPROCS(0),
		"goroutines":           runtime.NumGoroutine(),
		"go_managed_bytes":     memory.Sys - memory.HeapReleased,
		"go_soft_memory_limit": limit,
		"runtime_version":      runtime.Version(),
	}
	if err := json.NewEncoder(os.Stdout).Encode(result); err != nil {
		panic(err)
	}
}
```

```bash
go -C go build -o resource-probe .
GOMEMLIMIT=450MiB ./go/resource-probe
```

GOMEMLIMIT은 Go runtime 관리 메모리의 **soft limit**입니다.
대략 `MemStats.Sys - HeapReleased` 범위이며 cgo·mmap·외부 라이브러리 등 전체 RSS 한도가 아닙니다.
GC 비용 제한 때문에 목표를 초과할 수도 있습니다.
컨테이너 limit의 80–90%면 OOM을 방지한다는 보장은 없고, live heap보다 지나치게 작은 값은
GC 부담을 크게 만들 수 있습니다.
위 프로그램은 현재 값 조회용이며 cgroup을 직접 읽거나 바꾸지 않습니다.

### Rust

GC가 없다고 메모리 사용이나 지연이 결정적인 것은 아닙니다. allocator, fragmentation,
동시 작업, buffer, blocking 작업과 OS 스케줄링을 관찰합니다.
jemalloc 같은 allocator 교체는 프로파일 결과와 플랫폼 지원을 근거로 시험하며
모든 서비스에 더 빠르다는 전제를 두지 않습니다.

다음 Tokio 예제는 runtime 설정을 검증하는 작은 프로그램이며 HTTP 서버 예제는 아닙니다.
`worker_threads()`를 직접 지정하면 환경 변수보다 우선하므로 여기서는 생략했습니다.
worker thread 수는 `spawn_blocking` pool이나 별도 라이브러리 thread의 총량 제한이 아닙니다.

```toml
# rust/Cargo.toml
[package]
name = "resource-probe"
version = "0.1.0"
edition = "2024"

[dependencies]
tokio = { version = "=1.53.1", features = ["rt-multi-thread", "time"] }
```

```rust
// rust/src/main.rs
use std::time::Duration;
use tokio::runtime::Builder;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Without worker_threads(), Tokio can honor TOKIO_WORKER_THREADS.
    // This example rejects invalid values before building the runtime.
    if let Ok(value) = std::env::var("TOKIO_WORKER_THREADS") {
        let workers: usize = value.parse()?;
        if workers == 0 {
            return Err("TOKIO_WORKER_THREADS must be positive".into());
        }
    }
    let runtime = Builder::new_multi_thread()
        .enable_time()
        .build()?;
    println!("worker_threads={}", runtime.metrics().num_workers());
    runtime.block_on(async {
        tokio::time::sleep(Duration::from_millis(10)).await;
    });
    Ok(())
}
```

```bash
cargo build --manifest-path rust/Cargo.toml
TOKIO_WORKER_THREADS=2 ./rust/target/debug/resource-probe
```

처음 만드는 프로젝트에는 lockfile이 없으므로 `cargo build`로 생성하고 검토·커밋합니다.
그 이후 재현 가능한 빌드는 `--locked`를 사용합니다.
CPU 작업을 무제한 async task로 생성하는 대신 bounded queue·동시성 제한을 설계합니다.
언어별 “몇 MB, 몇 ms, 몇 배 빠름” 표는 실제 같은 조건의 벤치마크 없이는 사용하지 않습니다.

## 7. PromQL과 알림

다음 규칙은 kube-prometheus-stack의 `job="kubelet"`, `metrics_path="/metrics/cadvisor"`와
aggregate `cpu="total"` 시계열을 전제로 합니다. per-CPU 수집이면 그 수집 방식에 맞게 집계합니다.
kube-state-metrics도 필요합니다. 사용자 label 계약이 다르면 selector를 실제 데이터에 맞춥니다.

동일 관측값의 중복 scrape를 더하지 않도록 예제는 container 단위 max 집계를 사용합니다.
여러 런타임 ID가 같은 Pod/container 이름 아래 겹치는 재시작 구간은 별도 확인하고,
이 값들을 정밀한 CPU 사용량 청구 자료로 사용하지 않습니다.
다중 클러스터에는 실제 수집/remote-write 경로의 `cluster` 구분이 있어야 하며,
없는 cluster label을 PromQL이 만들어 주지는 않습니다.

규칙 순서대로 request/limit 분모를 맞추고 0을 제외합니다.
메모리 working set은 정확한 OOM 예측값이 아니며 page cache와 reclaim 동작도 확인합니다.
마지막 종료 reason은 gauge이므로 `increase(reason)`으로 OOM 횟수를 계산하지 않습니다.
아래 OOM 알림은 **최근 재시작 + 마지막 기록된 OOM reason**이며 기간 내 모든 OOM의 정확한 횟수는 아닙니다.

```yaml
# resource-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: resource-review
  namespace: observability
  labels:
    release: prometheus
spec:
  groups:
  - name: resource-review
    interval: 1m
    rules:
    - record: resource:cpu_cores:rate5m
      expr: max by (cluster, namespace, pod, container) (rate(container_cpu_usage_seconds_total{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD",pod!="",cpu="total"}[5m]))
    - record: resource:cpu_requests:cores
      expr: max by (cluster, namespace, pod, container) (kube_pod_container_resource_requests{resource="cpu",unit="core"})
    - record: resource:memory_working_set:bytes
      expr: max by (cluster, namespace, pod, container) (container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD",pod!=""})
    - record: resource:memory_limit:bytes
      expr: max by (cluster, namespace, pod, container) (kube_pod_container_resource_limits{resource="memory",unit="byte"})
    - record: resource:cpu_request_ratio
      expr: resource:cpu_cores:rate5m / (resource:cpu_requests:cores > 0)
    - record: resource:memory_limit_ratio
      expr: resource:memory_working_set:bytes / (resource:memory_limit:bytes > 0)
    - record: resource:cfs_throttled:rate5m
      expr: max by (cluster, namespace, pod, container) (rate(container_cpu_cfs_throttled_periods_total{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD",pod!=""}[5m]))
    - record: resource:cfs_periods:rate5m
      expr: max by (cluster, namespace, pod, container) (rate(container_cpu_cfs_periods_total{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD",pod!=""}[5m]))
    - record: resource:cfs_throttled_period_ratio
      expr: resource:cfs_throttled:rate5m / (resource:cfs_periods:rate5m > 0)
    - record: resource:recent_restart_last_oom
      expr: (max by (cluster, namespace, pod, container) (increase(kube_pod_container_status_restarts_total[5m]))
        > 0) and on (cluster, namespace, pod, container) (max by (cluster, namespace,
        pod, container) (kube_pod_container_status_last_terminated_reason{reason="OOMKilled"})
        == 1)
    - record: cluster:pending_pods:count
      expr: sum by (cluster) (max by (cluster, namespace, pod) (kube_pod_status_phase{phase="Pending"}))
    - record: node:pods:count
      expr: count by (cluster, node) (max by (cluster, node, namespace, pod) (kube_pod_info{node!=""}))
    - alert: HighCPUThrottledPeriodRatio
      expr: resource:cfs_throttled_period_ratio > 0.25
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: HighCPUThrottledPeriodRatio
        description: A high fraction of quota periods were throttled; correlate with
          latency and throughput.
    - alert: MemoryWorkingSetNearLimit
      expr: resource:memory_limit_ratio > 0.9
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: MemoryWorkingSetNearLimit
        description: Working set is near the configured limit; this is not an exact
          OOM prediction.
    - alert: RecentRestartWithLastReasonOOM
      expr: resource:recent_restart_last_oom > 0
      for: 0m
      labels:
        severity: warning
      annotations:
        summary: RecentRestartWithLastReasonOOM
        description: A recent restart has OOMKilled as its last recorded reason; inspect
          termination state.
```

`release: prometheus`와 `observability` 네임스페이스는 해당 Prometheus의 rule selector와
맞춰야 합니다. 임계값은 예시이며 `HighCPUThrottledPeriodRatio`가 곧바로 limit 증가를
요구하는 것은 아닙니다. 지연·처리량·동시성·노드 경합을 함께 확인합니다.

`cluster:pending_pods:count`는 0/1 phase gauge의 값을 합산합니다.
`count(kube_pod_status_phase{phase="Pending"})`는 0인 값도 세므로 Pending Pod 수가 아닙니다.
Pending에는 이미 스케줄된 뒤 이미지/스토리지를 기다리는 Pod도 포함되어 리소스 부족과 동일하지 않습니다.
`node:pods:count`는 노드별 Pod 수이며 이를 전체 노드 수로 다시 나누지 않습니다.

Deployment별 분석은 Pod 이름 정규식으로 소유자를 추측하지 말고 kube-state-metrics의
Pod→ReplicaSet→Deployment owner 관계 또는 검증된 recording rule을 사용합니다.
장기간 과잉 예약 분석은 롤아웃·휴일·예비 용량과 SLO를 함께 평가하며 자동 eviction 기준으로 쓰지 않습니다.

### JVM 쿼리와 대시보드 연결

다음 쿼리는 위 Micrometer 설정을 사용하는 JVM을 대상으로 합니다.
Prometheus가 붙이는 instance로 프로세스를 구분하고, scrape에서 얻은 실제 metric 이름을 확인합니다.

```promql
sum by (instance, application) (jvm_memory_used_bytes{area="heap"})
/
sum by (instance, application) (jvm_memory_max_bytes{area="heap"} > 0)
```

```promql
histogram_quantile(0.99,
  sum by (le, instance, application) (rate(jvm_gc_pause_seconds_bucket[5m]))
)
```

```promql
sum by (instance, application) (rate(jvm_gc_pause_seconds_sum[5m]))
```

```promql
rate(jvm_classes_loaded_count_classes_total[5m])
```

`jvm_gc_pause_seconds_sum`의 rate는 관찰한 pause 초/벽시계 초이며
process CPU로 나눈 “GC CPU 비율”이 아닙니다. 동시 GC 전체 비용을 모두 포함하지도 않습니다.
`jvm_classes_loaded_classes`는 현재 로드된 class 수 gauge이고,
검증한 Micrometer의 누적 로드 counter는 `jvm_classes_loaded_count_classes_total`입니다.
JDK/라이브러리 버전이 다르면 이름을 실제 노출값과 맞춥니다.

Grafana에는 [앞 장](./09-observability-stack.md)의 명시적 datasource UID와
dashboard provisioning을 사용합니다. 위 rule의 ratio에는 percentunit 또는 `×100` 후 percent를
선택해 단위를 맞춥니다. raw utilization gauge를 histogram bucket인 것처럼 heatmap에 넣지 않습니다.
부분 panel JSON을 완성된 import용 dashboard라고 안내하지 않습니다.

## 8. EKS Auto Mode와 여유 용량

Auto Mode도 Pod request, 실제 Node allocatable, DaemonSet/시스템 overhead, Pod overhead,
포트·볼륨·토폴로지·taint 등 배치 제약을 고려해야 합니다.
4 vCPU 인스턴스의 allocatable이 정확히 4 CPU라고 가정해 4 CPU request를 꽉 채우는 계산은 부정확합니다.
인스턴스가 클수록 언제나 효율적이거나 작을수록 항상 저렴한 것도 아닙니다.
장애 영향 범위·사용 가능한 타입·가격·fragmentation을 함께 평가합니다.

Auto Mode NodePool의 API는 `karpenter.sh/v1`이고 NodeClass의 group은 `eks.amazonaws.com`입니다.
아래는 이미 존재하는 Auto Mode `default` NodeClass를 참조합니다.
NodeClass·서브넷·역할·해당 리전의 인스턴스 가용성은 별도로 확인합니다.

```yaml
# auto-nodepool.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: resource-demo
spec:
  template:
    spec:
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      requirements:
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - m7i.large
        - m7i.xlarge
        - m7i.2xlarge
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
```

노드 통합은 request와 배치 가능성·가격·disruption 제약 등을 바탕으로 결정하며
“실측 CPU 30% 미만이면 반드시 통합”하는 규칙이 아닙니다.
PDB가 모든 종료를 막거나 강제 종료까지 무중단을 보장하지 않습니다.
limit이 매우 커도 request가 같다면 일반 스케줄러가 그 limit을 그대로 예약하는 것은 아닙니다.

다음 placeholder Pod는 높은 우선순위의 실제 작업이 사용할 여유 용량을 유도할 수 있습니다.
Priority -1은 기본 0보다 낮지만 가능한 모든 Priority 중 최저값은 아닙니다.
`preemptionPolicy: Never`는 이 Pod가 다른 Pod를 선점하지 않도록 하며, 자신이 선점되는 것을 막지 않습니다.
EC2 Capacity Reservation이나 가용 용량 보장이 아니고, topology/taint/리소스 모양이 실제 작업과 맞아야 합니다.

```yaml
# capacity-buffer.yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: capacity-buffer
value: -1
preemptionPolicy: Never
globalDefault: false
description: Lower priority placeholder capacity; not a reservation guarantee.
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: capacity-buffer
  namespace: production
spec:
  replicas: 2
  selector:
    matchLabels:
      app: capacity-buffer
  template:
    metadata:
      labels:
        app: capacity-buffer
    spec:
      priorityClassName: capacity-buffer
      containers:
      - name: pause
        image: registry.k8s.io/pause:3.10.2
        resources:
          requests:
            cpu: '2'
            memory: 4Gi
```

## 적용 순서와 검증 한계

1. 대표 부하에서 지연·처리량·CPU quota·전체 메모리와 재시작 원인을 측정합니다.
2. VPA 추천·운영 관측으로 request 후보를 만들고 HPA와 런타임 동시성을 함께 검토합니다.
3. 시작·피크·실패·재시작을 포함한 비운영 시험으로 limit과 여유 용량을 조정합니다.
4. Canary에서 SLO·비용·노드 배치·eviction/중단 변화를 관찰하고 되돌릴 설정을 보관합니다.

검토에서는 Java/Spring/JMX의 실제 메트릭·JFR/NMT, Gunicorn/Node health와 SIGTERM,
Go 런타임 값, Tokio worker 설정을 로컬에서 실행했습니다. PromQL 계산은 중복 scrape,
다중 클러스터, 0 분모, 과거 OOM, Pending 0/1 gauge 입력으로 시험했습니다.
이것은 실제 EKS 배포, cgroup quota 변경 시험, OOM 강제 발생, 성능 벤치마크를 수행했다는 뜻은 아닙니다.

## 공식 자료

- [Kubernetes resources](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Node-pressure eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)
- [Go container-aware GOMAXPROCS](https://go.dev/blog/container-aware-gomaxprocs)
- [Go GC guide](https://go.dev/doc/gc-guide)
- [Java 21 options](https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html)
- [JEP 474](https://openjdk.org/jeps/474)
- [JEP 490](https://openjdk.org/jeps/490)
- [Spring Boot properties](https://docs.spring.io/spring-boot/appendix/application-properties/index.html)
- [JMX exporter 1.6.0](https://github.com/prometheus/jmx_exporter/releases/tag/1.6.0)
- [Gunicorn settings](https://gunicorn.org/reference/settings/)
- [Flask changelog](https://flask.palletsprojects.com/en/stable/changes/)
- [Node.js 24 CLI](https://nodejs.org/download/release/v24.21.0/docs/api/cli.html)
- [Tokio runtime builder](https://docs.rs/tokio/1.53.1/tokio/runtime/struct.Builder.html)

---

< [이전: Observability 스택](./09-observability-stack.md) | [목차](./README.md) | [다음: EKS 업그레이드](./11-upgrade-operations.md) >
