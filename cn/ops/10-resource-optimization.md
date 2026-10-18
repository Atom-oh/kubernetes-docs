# 资源优化：requests、limits 与语言运行时

> **最后更新**：October 16, 2026。示例已根据 Kubernetes 1.36 schemas、Java 21 / Spring Boot 4.1.1、Python 3.12 / Gunicorn 26.2.0、Node.js 24.22、Go 1.27.2 和 Rust 1.98 / Tokio 1.53.1 进行检查。

不要仅根据语言名称或固定百分比来确定工作负载的资源配置。在有代表性的负载、启动、重启、GC 和故障条件下，测量吞吐量和延迟 SLO。将 requests、limits、副本数和运行时并发配置一起调整。示例百分比和阈值是测试起点，并非性能保证。

## 1. Requests、limits 与 QoS

| 资源 | Requests | Limits |
|---|---|---|
| CPU | 用于调度核算，以及发生争用时的相对权重 | Linux cgroup CPU 配额可以限制执行 |
| 内存 | 用于调度核算 | 当回收无法满足需求时，分配压力可能导致 cgroup OOM |
| 未指定 | Admission 默认值和更高层级的策略仍然会产生影响 | 容器可能没有 limit，但节点/上级 cgroup 限制仍然适用 |

request 不是物理 CPU 绑定或预分配内存，也不保证应用程序性能。如果只提供了 limit，且没有其他 admission 默认值设置 request，Kubernetes 会将 limit 复制到 request。应用 LimitRange 和其他策略后，请检查经过 admission 处理的 Pod。

这些示例使用容器级资源，而非 Pod 级资源。
先创建 `resource-demo`，并在没有 LimitRange 注入资源默认值的情况下比较 QoS。
Guaranteed 要求 CPU 和内存的 requests/limits 均为正值且相等，并满足常规容器和 init 容器的适用条件。

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

BestEffort 没有 CPU/内存 requests 或 limits；其他配置可能属于 Burstable。
使用 Pod 级资源或 sidecar/init 资源核算时，请检查特定版本的规则。

QoS 并不意味着绝对的驱逐顺序。在内存压力下，kubelet 会考虑用量是否超过 requests、Pod Priority，以及用量相对于 requests 的情况。Guaranteed 和用量未超过 request 的 Burstable Pod 往往较晚被考虑驱逐，但 Guaranteed 并不总是最后一个被驱逐的对象。
请区分 DiskPressure 驱逐和容器 limit 导致的 OOM。OOMKilled 通常是容器终止原因，而不是 Pod phase。单个进程可能会被杀死；如果 PID 1 退出，重启策略会决定容器的重启行为。

### CPU 配额与内存边界

cgroup v1 使用 `cpu.cfs_quota_us` / `cpu.cfs_period_us`；v2 使用 `cpu.max`。
100ms 是常见的配额周期，并非普遍适用的固定值。使用 500m 和 100ms 周期时，所有线程共享 50ms 的总执行时间预算。限流可能同时影响延迟和吞吐量。限流周期比率衡量的是包含限流的周期，而不是损失的 CPU 时间。

内存 limit 不是堆大小限制。请区分 cgroup v1 的 `memory.limit_in_bytes` 和 v2 的 `memory.max`。考虑 RSS、原生内存分配、线程栈、页缓存以及内存支持的 emptyDir 用量。当内存接近某个阈值时重启应用的 liveness probe 可能会掩盖根因并造成重启循环；它不是通用的 OOM 解决方案。

移除 CPU limit 可以减少该容器的配额限流，但不会消除资源争用、上级配额或节点限制。应综合评估 requests、priority、隔离、策略和 SLO。

### Namespace 默认值与预算

LimitRange 控制 admission 默认值和每种资源的约束。ResourceQuota 控制 namespace 中 requests、limits 和对象数量的 admission 预算。它们不会直接计量或限制实时 CPU 用量或成本。应用这些策略前，先创建 `production` namespace。

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

## 2. 测量与 VPA

在有代表性的时间段内观察分布、峰值、启动成本和内存增长。
P70 requests 和 P99 limits 是待验证的假设，并非通用默认值。
即使是同一种语言，GC、模型加载、JIT、加密、sidecar 和批量输入大小也会有所不同。
不要只靠提高 limits 来掩盖内存泄漏，也不要自动将空闲的备用/灾难恢复 Pod 判定为浪费。

有关固定版本的 VPA 和 Goldilocks 安装，请参阅[扩缩容章节](./06-scaling-strategies.md)。
Goldilocks 会为选定的 namespace/workload 创建/显示 VPA；安装后不会自动优化所有内容。此 VPA 会监控下方所示的 `resource-java` Deployment。

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

`Off` 只提供建议。`target` 是 request 建议值；上下界表示建议范围。不要将 upperBound 直接视为内存 limit，也不要将 uncappedTarget 直接视为已应用的值。`RequestsAndLimits` 可以在保留现有比例的同时调整 limits；它不会将 upperBound 复制到 limits。

在 VPA 1.8.0 中，已弃用的 `Auto` 行为与 `Recreate` 相同。请检查使用 `InPlaceOrRecreate`/`InPlace` 的前提条件以及 Kubernetes 原地更新支持情况。`Initial` 仍会更改新 Pod 的 requests，因此也会更改基于 request 的 HPA 利用率分母。
它与 HPA 配合时不会自动避免冲突。

如果一个 Pod 能在满足所需 SLO 的情况下持续处理 200 RPS，那么稳定状态下处理 1,000 RPS 需要五个 Pod。要在丢失一个 Pod 后仍维持该吞吐量，至少需要六个 Pod。这并不能保证整个 AZ 故障时仍能正常运行。还要区分增加 20% 容量和让 20% 的可用容量保持闲置；后者需要 `ceil(1000 / (200 × 0.8)) = 7`。

## 3. JVM：堆与容器内存

`MaxRAMPercentage` 是 JVM 根据检测到的内存进行堆大小优化时使用的输入值。
75% 并非普遍适用的最优值，也不是能在 Pod limit 变更后立即跟随调整的实时缩放器。`-Xmx`、`-XX:MaxRAM` 和小堆优化也会产生影响。
Metaspace、代码缓存、栈、直接缓冲区、JNI 和分配器都会消耗堆外内存。
固定的 25% 并不能保证非堆内存容量充足。

JVM 不会自动读取 `JAVA_OPTS`；镜像的 entrypoint 必须将其传递给命令。此示例使用 JVM 识别的 `JAVA_TOOL_OPTIONS` 和显式的 `java -jar` 命令。
60% 是性能分析的起始值。

下面的完整 Spring Boot 示例使用 Java 21 和 Boot 4.1.1 构建。
将文件保存到指定的项目路径。

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

这个最小项目不包含 wrapper 文件；除非添加 wrapper，否则请使用 `mvn package`。
镜像必须包含位于 `/app/resource-api.jar` 的构建后 jar 文件，以及兼容 Java 21 的运行时。
下方的 `registry.example.com` 镜像是占位符，需要替换。
创建 namespace、构建镜像和访问 registry 是彼此独立的前提条件。
Readiness/liveness 路径与应用程序实际的 Actuator endpoints 一致。

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

Prometheus 配置路径为 `management.prometheus.metrics.export`。
不要不加区分地暴露 metrics 和详细健康信息。
只有发布了 histogram 的 metrics 才能支持 `_bucket` 查询；对各 Pod 的客户端计算百分位数取平均，并不能得到全局百分位数。
Micrometer Timer 已提供 count/sum，因此同一项测量无需再添加重复的 Counter。

HeapDumpOnOutOfMemoryError 用于处理 JVM Java OOME。内核 SIGKILL 无法执行 heap-dump 或 shutdown hooks。删除 Pod 后，emptyDir 中的诊断文件也会消失；还应处理文件名冲突和磁盘耗尽问题。Heap dump 可能包含敏感应用数据，因此应限制访问和保留时间。
`ScheduleAnyway` 表示一种调度倾向，而非严格的 AZ 分布要求。

### GC 与 CPU

| 选项 | 需要验证的内容 |
|---|---|
| G1 | 常见的起始选择；暂停目标并非最大延迟保证 |
| ZGC | 特定 JDK 版本的分代行为以及 CPU/内存预算 |
| Shenandoah | 所选 JDK 发行版和版本是否提供该选项 |
| Parallel / Serial | 根据吞吐量或小堆工作负载需求进行比较 |

Java 21 支持通过 `-XX:+UseZGC -XX:+ZGenerational` 启用分代 ZGC。
分代模式在 Java 23 中成为默认设置；Java 24 移除了非分代模式，并使选择标志过时。请区分 Java 25 中的过时警告与未来标志失效。
不要将此标志复制到 Java 17。在仅支持分代模式的当前 JDK 上，使用 `-XX:+UseZGC`，并在确切的版本上验证启动情况。固定的 GC 延迟/吞吐量数据需要通过基准测试得出。

`availableProcessors()` 并不总是 GC worker 数量。配额、CPU 亲和性、JDK 版本和收集器优化都会产生影响。增加 GC 线程可能会更快耗尽较小的 CPU 配额。
如果启动缓慢，请使用 startupProbe 并测量 JIT/GC/CPU 行为。

### JMX 与 JFR

在镜像中包含 JMX exporter 1.6.0 jar，或获取官方 artifact 并验证其校验和。以下配置已针对实际的内存、线程和 GC MBeans 进行测试。
JMX 和 Micrometer 使用不同的 metric 名称；不要在 dashboard 中不加区分地混用。
GC CollectionTime 会从毫秒转换为秒。

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

此本地诊断命令会绑定到 loopback。从另一个 Pod 采集数据需要显式配置 metrics 端口、ServiceMonitor 和访问控制。若 agent jar 不存在，JVM 将无法启动。
NMT 需要在启动时设置 `-XX:NativeMemoryTracking=summary`；它并不能完整核算所有外部原生库分配所占用的 RSS。

实时 JFR 采集需要 JDK 工具、适当的同用户权限、attach 支持以及可写的目标路径。将 `PID` 替换为 Java 进程 ID，不要想当然地认为 PID 1 就是它。

```bash
jcmd PID VM.native_memory summary
jcmd PID JFR.start name=profile settings=profile duration=60s filename=/diagnostics/profile.jfr
jfr summary /diagnostics/profile.jfr
```

从容器复制文件时，请考虑所选容器，以及 `kubectl cp` 是否有可用的 `tar`。
录制结束后再复制；进程/Pod 被替换后，并不能保证 heap 或 JFR 文件仍然存在。

## 4. Python：workers 与性能分析

将 `2 × CPU + 1` 应用于主机的 `multiprocessing.cpu_count()` 可能导致容器 CPU 配额超额使用。
测试 CPU/IO 行为、GIL/原生扩展、每个 worker 的 RSS 和请求并发情况。
不存在普遍适用的每 CPU worker 数公式。
此 WSGI Flask 示例会实际读取 `WEB_CONCURRENCY`，并以一个 worker 和两个线程启动。

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

这些健康检查 endpoint 只检查示例进程。请为应用实现依赖项 readiness 检查。不要使用 Flask 中已移除的 `before_first_request` hook。
此最小示例禁用了 Gunicorn 26 的本地管理 control socket。

请区分 WSGI Flask 和 FastAPI 等 ASGI 应用。Gunicorn 26 也有 ASGI worker；如果选择 Uvicorn，请区分已弃用的 `uvicorn.workers` 和独立的 `uvicorn-worker` 包。不要将 gthread 设置原样应用于 ASGI 应用。
评估 preload 的写时复制优势时，也要考虑在 fork 前初始化的线程/连接/客户端。
回收 worker 不能从根本上解决内存泄漏。

tracemalloc 只能观察受跟踪的 Python 分配，无法涵盖所有原生/RSS 用量。
以下是显式的本地诊断示例，不是公开暴露的 HTTP 调试 endpoint。

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

## 5. Node.js：old space 与进程内存

`--max-old-space-size` 以 MiB 为单位，控制 V8 old space。
它不是 RSS 上限；young generation、external/Buffer 和原生内存也需要预留容量。
使用多个 worker 进程时，应为每个进程的堆分别预留资源。
Node.js 20 已于 2026 年 4 月结束生命周期，因此新示例使用受支持的 Node.js 24 系列。

此单进程示例实现了健康检查 endpoint、内存监控和 SIGTERM 处理。
仅根据百分比反复调用 `global.gc()` 并非通用优化方法。
经测试的 Node 24 接受在 NODE_OPTIONS 中设置 `--expose-gc`；但这并不能证明强制 GC 在生产环境中有益。

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

`UV_THREADPOOL_SIZE` 会影响使用 libuv 线程池的操作，包括文件系统 I/O、部分 DNS 操作和加密。它不涵盖所有网络 I/O。
更多线程可能会增加栈内存和并发操作的内存用量。应在启动前设置，并使用实际工作负载进行测试。

如果使用 Node cluster，请优先使用 `isPrimary` 并明确限制 worker 数量。
不要认为 `os.cpus().length`、PM2 的 `instances: max` 或 `availableParallelism()` 对所有 cgroup 配额都适用。
重启循环需要退避机制，并且在关闭期间不得重新创建 worker。
同时使用 Pod 副本和进程副本会使 worker 数量和内存预算成倍增加。

## 6. Go 与 Rust

### Go

Go 1.25 在 Linux 上引入了感知 cgroup 的默认 GOMAXPROCS。
`go.mod` 的语言版本和 GODEBUG 兼容性默认设置也很重要；要使用这些默认值，请使用 `go 1.25.0` 或更高版本。此示例已使用 Go 1.27.2 进行测试。
在环境中显式设置 GOMAXPROCS，或调用参数为正数的 `runtime.GOMAXPROCS(n)`，都会禁用自动更新。使用 `runtime.GOMAXPROCS(0)` 查询不会更改其值。

当前运行时会将配额向上取整，并同时考虑逻辑 CPU 和亲和性。
如果逻辑 CPU/亲和性数量允许两个，它通常不会选择低于两个的值，因此“`500m always means 1`”是不正确的。不要将 automaxprocs 的版本/取整行为等同于 Go 内置默认值，也不要不加判断地同时启用两者。CPU requests 不是配额。

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

GOMEMLIMIT 是 Go 运行时管理内存的软限制，近似于
`MemStats.Sys - HeapReleased`。它不是涵盖 cgo、mmap 或外部库的整个进程 RSS 上限。运行时可能会超出此限制以降低 GC 开销。
将其设为容器内存的 80–90% 并不能保证避免 OOM；若远低于活动堆大小，则可能导致过度 GC。此程序只报告设置，不会读取或修改 cgroup。

### Rust

没有 GC 并不意味着内存用量或延迟具有确定性。应观察分配器行为、碎片、并发工作、缓冲区、阻塞工作和 OS 调度。
是否更换为 jemalloc 等分配器，应依据性能分析结果和平台支持情况进行评估，不要假设它能普遍提升性能。

这个小型 Tokio 程序用于验证运行时设置；它不是 HTTP server。
显式设置 `worker_threads()` 会覆盖环境变量，因此示例中省略了它。
worker 线程数量并不限制 `spawn_blocking` 或外部库线程的数量。

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

如果新项目还没有 lockfile，请运行 `cargo build`，然后检查并提交 lockfile。
后续可复现构建可以使用 `--locked`。
使用有界队列/并发，而不是创建数量不受限的 CPU 密集型异步任务。
没有可比基准测试时，不要发布针对整个语言的内存/启动/速度排名。

## 7. PromQL 与告警

这些规则假设 kube-prometheus-stack 使用 `job="kubelet"`、`metrics_path="/metrics/cadvisor"` 和聚合的 `cpu="total"` series，并且使用 kube-state-metrics。
请根据每 CPU 采集情况调整聚合方式，并根据实际 label 约定调整 selectors。

该示例使用每个容器的 max 聚合，以避免对重复的 scrape 观测求和。
请检查同一个 Pod/container 名称下多个 runtime ID 重叠的重启时间窗口；
这些观测并非精确的 CPU 计费数据。
多个集群需要在采集/remote-write 路径中提供真实的 `cluster` label；
PromQL 不会凭空生成缺失的集群标识。

这些有序规则使用一致的 request/limit 分母，并排除零值。
Working set 不是精确的 OOM 预测指标；请检查页缓存和回收行为。
最近一次终止原因是 gauge，因此 `increase(reason)` 并不是 OOM 计数。
OOM 告警将最近一次重启与最后记录的 OOM 原因结合起来；它不会统计时间间隔内发生的每一次 OOM。

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

将 `release: prometheus` 和 `observability` namespace 与 Prometheus rule selector 匹配。
阈值仅为示例。较高的限流周期比率并不自动意味着应该调高 limit；应结合延迟、吞吐量、并发和节点争用情况进行分析。

`cluster:pending_pods:count` 对 0/1 phase gauge 求和。
`count(kube_pod_status_phase{phase="Pending"})` 也会统计值为零的样本。
Pending 可能包含已调度但正在等待镜像/存储的 Pod，因此不等同于资源不足。
`node:pods:count` 已经是每节点的计数；不要再除以集群节点数。

聚合 Deployment 时，请使用 kube-state-metrics 的 Pod→ReplicaSet→Deployment 所有权关系或经过验证的 recording rules，而不是猜测 Pod 名称正则表达式所表示的所有权。
长期配置资源时，应评估 rollout、假期、备用容量和 SLO；观测到低用量并不意味着应自动驱逐。

### JVM 查询与 dashboard

这些查询针对使用上述 Micrometer 配置的 JVM。
请通过 Prometheus 的 instance label 区分进程，并在实际 scrape 中验证 metric 名称。

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

`jvm_gc_pause_seconds_sum` 的 rate 表示每秒墙钟时间内观测到的暂停秒数。
将其除以进程 CPU 得不到有效的 GC CPU 百分比，也无法涵盖所有并发 GC 工作。`jvm_classes_loaded_classes` 是当前已加载类的 gauge；
经测试的 Micrometer 累积计数器是 `jvm_classes_loaded_count_classes_total`。
更改 JDK/库版本时，请检查实际的 exposition。

请使用[上一章](./09-observability-stack.md)中明确指定的 datasource UID 和 dashboard provisioning。
使用 percentunit 显示比率，或者将比率乘以 100 并使用 percent。
不要在 heatmap 中将原始利用率 gauge 当作 histogram bucket。
不要把不完整的 panel JSON 片段描述为可完整导入的 dashboard。

## 8. EKS Auto Mode 与备用容量

请考虑 requests、实际 Node allocatable、DaemonSet/系统开销、Pod 开销、端口、卷、拓扑和 taints。4-vCPU 实例不一定能为应用程序 requests 提供四个可分配 CPU。较大的实例不总是更高效，较小的实例也不总是更便宜。应评估故障影响、可用性、定价和碎片化情况。

Auto Mode NodePools 使用 `karpenter.sh/v1`；NodeClass 的 group 是 `eks.amazonaws.com`。
此示例引用现有 Auto Mode `default` NodeClass。
请分别验证 NodeClass、子网、IAM role 和区域内实例可用性。

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

Consolidation 会考虑 requests、调度可行性、价格和中断约束；
观测到 CPU 使用率低于 30%，并不保证节点会进行 consolidation。
PDB 不能阻止所有终止操作，也不能保证强制终止期间服务不间断。
如果 request 保持不变，普通 scheduler 不会自动预留超大的 limit。

占位 Pod 可以鼓励系统为更高优先级的工作保留备用容量。
Priority -1 低于默认值 0，但并非可能的最低优先级。
`preemptionPolicy: Never` 可防止占位 Pod 抢占其他 Pod；但不能防止占位 Pod 本身被抢占。这不是 EC2 Capacity Reservation，也不是可用性保证；其拓扑、taints 和资源规格必须适合实际工作负载。

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

## 部署顺序与验证限制

1. 在有代表性的负载下，测量延迟、吞吐量、配额行为、总内存和重启原因。
2. 使用 VPA 和观测结果提出 requests 建议，并同时考虑 HPA 和运行时并发。
3. 在调整 limits 和预留容量前，在生产环境之外测试启动、峰值负载、故障和重启。
4. 在 canary 期间观察 SLO、成本、部署位置和中断情况；保留回滚所需的配置。

验证过程在本地运行了 Java/Spring/JMX metrics 和 JFR/NMT、Gunicorn/Node 健康检查及 SIGTERM 行为、Go 运行时报告和 Tokio worker 配置。
PromQL 计算案例覆盖了重复 scrape、多集群、零分母、历史 OOM 状态和 Pending 的 0/1 gauge。
验证过程没有部署 EKS、修改 cgroup 配额、强制触发 OOM 或进行性能基准测试。

## 官方参考资料

- [Kubernetes 资源](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [节点压力驱逐](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)
- [Go 容器感知的 GOMAXPROCS](https://go.dev/blog/container-aware-gomaxprocs)
- [Go GC 指南](https://go.dev/doc/gc-guide)
- [Java 21 选项](https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html)
- [JEP 474](https://openjdk.org/jeps/474)
- [JEP 490](https://openjdk.org/jeps/490)
- [Spring Boot 属性](https://docs.spring.io/spring-boot/appendix/application-properties/index.html)
- [JMX exporter 1.6.0](https://github.com/prometheus/jmx_exporter/releases/tag/1.6.0)
- [Gunicorn 设置](https://gunicorn.org/reference/settings/)
- [Flask 更新日志](https://flask.palletsprojects.com/en/stable/changes/)
- [Node.js 24 CLI](https://nodejs.org/download/release/v24.22.0/docs/api/cli.html)
- [Tokio runtime builder](https://docs.rs/tokio/1.53.1/tokio/runtime/struct.Builder.html)

---

< [上一章：可观测性栈](./09-observability-stack.md) | [目录](./README.md) | [下一章：EKS 升级](./11-upgrade-operations.md) >
