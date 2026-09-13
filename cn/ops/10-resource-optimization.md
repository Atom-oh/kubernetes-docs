# 资源优化：requests、limits 和语言运行时

> **最后更新**：2026 年 9 月 11 日。示例使用 Kubernetes 1.36 模式，
> Java 21 / Spring Boot 4.1.1、Python 3.12 / Gunicorn 26.2.0，
> Node.js 24.21、Go 1.27.1 和 Rust 1.98 / Tokio 1.53.1 进行了检查。

不要仅根据语言名称或固定百分比规划工作负载容量。应在有代表性的负载、启动、重启、GC 和故障条件下测量吞吐量与延迟 SLO。同时调整 requests、limits、副本数和运行时并发度。示例百分比和阈值是测试起点，不是性能保证。

## 1. Requests、limits 和 QoS

| 资源 | Requests | Limits |
|---|---|---|
| CPU | 调度记账和竞争时的相对权重 | Linux cgroup CPU 配额可限制执行 |
| 内存 | 调度记账 | 回收无法满足分配压力时，可能发生 cgroup OOM |
| 未指定 | 准入默认值和更高层策略仍然重要 | 可能没有容器限制，但节点/祖先 cgroup 限制仍适用 |

request 不是物理 CPU 绑定或预分配内存，也不保证应用性能。若仅提供 limit，且其他准入默认值未设置 request，Kubernetes 会将 limit 复制为 request。在 LimitRange 和其他策略处理后，检查获准的 Pod。

这些示例使用容器级资源，不是 Pod 级资源。先创建 `resource-demo`，并在没有 LimitRange 注入资源默认值的情况下比较 QoS。Guaranteed 要求 CPU 和内存 requests/limits 为正且相等，并满足普通容器和初始化容器的适用条件。

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

BestEffort 没有 CPU/内存 requests 或 limits；其他配置可能是 Burstable。使用 Pod 级资源或 Sidecar/初始化容器资源记账时，检查特定版本规则。

QoS 不是绝对驱逐顺序。内存压力下，kubelet 考虑用量是否超过 requests、Pod 优先级及相对 requests 的用量。Guaranteed 和未超 request 的 Burstable Pod 往往较晚考虑，但 Guaranteed 不总是最后被选中。区分 DiskPressure 驱逐与容器限制 OOM。OOMKilled 通常是容器终止原因，不是 Pod 阶段。单个进程可能被终止；若 PID 1 退出，则由重启策略决定容器重启行为。

### CPU 配额和内存边界

cgroup v1 使用 `cpu.cfs_quota_us` / `cpu.cfs_period_us`；v2 使用 `cpu.max`。100ms 是常见配额周期，不是通用常量。500m 配额、100ms 周期下，所有线程共享总计 50ms 执行预算。节流可同时影响延迟和吞吐量。被节流周期比率衡量包含节流的周期，不是损失的 CPU 时间。

内存限制不是堆限制。区分 cgroup v1 `memory.limit_in_bytes` 和 v2 `memory.max`。考虑 RSS、原生分配、线程栈、页缓存及内存型 emptyDir 用量。内存接近阈值时重启应用的存活探针可能掩盖原因并制造重启循环；它不是通用 OOM 解决方案。

移除 CPU limit 可减少该容器的配额节流，但不消除竞争、祖先配额或节点限制。应同时评估 requests、优先级、隔离、策略和 SLO。

### 命名空间默认值和预算

LimitRange 控制准入默认值及各资源约束。ResourceQuota 控制命名空间内 requests、limits 和对象数量的准入预算。它们不直接计量或限制实时 CPU 用量或成本。应用这些策略前，创建 `production` 命名空间。

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

## 2. 测量和 VPA

在有代表性的时间段内观察分布、峰值、启动成本和内存增长。P70 requests 和 P99 limits 是待测试假设，不是通用默认值。即使同一种语言，GC、模型加载、JIT、密码学运算、Sidecar 和批输入大小也不同。不要仅提高 limits 来掩盖泄漏，也不要自动将空闲备用/灾备 Pod 归为浪费。

固定版本 VPA 和 Goldilocks 安装参阅[扩缩容章节](./06-scaling-strategies.md)。Goldilocks 为所选命名空间/工作负载创建和展示 VPA；安装不会自动优化一切。此 VPA 观察下方 `resource-java` Deployment。

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

`Off` 仅提供建议。`target` 是 request 建议；上下界描述建议范围。不要直接将 upperBound 当作内存 limit，或将 uncappedTarget 当作已应用值。`RequestsAndLimits` 可在保留现有比率的同时调整 limits；不会把 upperBound 复制到 limits。

VPA 1.7.1 中，已弃用的 `Auto` 行为等同于 `Recreate`。检查 `InPlaceOrRecreate`/`InPlace` 的前提条件和 Kubernetes 原地更新支持。`Initial` 仍会更改新 Pod 的 requests，从而更改基于 request 的 HPA 利用率分母。它不会自动与 HPA 无冲突。

若一个 Pod 在所需 SLO 下持续处理 200 RPS，1,000 RPS 在稳态需要五个 Pod。失去一个 Pod 后仍保持该吞吐量，至少需要六个。这不保证承受整个可用区故障。还应区分增加 20% 容量与保留 20% 可用容量不用；后者需要 `ceil(1000 / (200 × 0.8)) = 7`。

## 3. JVM：堆和容器内存

`MaxRAMPercentage` 是 JVM 根据检测到的内存进行堆自适应调整的输入。75% 并非普遍最优，也不是立即跟随 Pod limit 变化的实时调整器。`-Xmx`、`-XX:MaxRAM` 和小堆自适应逻辑也很重要。元空间、代码缓存、栈、直接缓冲区、JNI 和分配器消耗堆外内存。固定 25% 不保证堆外容量充足。

JVM 不会自动读取 `JAVA_OPTS`；镜像入口必须将其传给命令。此示例使用 JVM 识别的 `JAVA_TOOL_OPTIONS` 及显式 `java -jar` 命令。60% 是性能剖析起点。

下方完整 Spring Boot 示例使用 Java 21 和 Boot 4.1.1 构建。将文件保存到指定项目路径。

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

最小项目不包含 wrapper 文件；除非添加 wrapper，否则使用 `mvn package`。镜像必须在 `/app/resource-api.jar` 包含构建出的 jar，并具有兼容 Java 21 的运行时。下方 `registry.example.com` 镜像是需替换的占位符。命名空间创建、镜像构建和仓库访问是独立前提条件。就绪/存活路径匹配应用实际 Actuator 端点。

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

Prometheus 配置路径为 `management.prometheus.metrics.export`。不要无差别暴露指标和详细健康信息。只有发布直方图的指标才支持 `_bucket` 查询；对各 Pod 客户端计算的百分位数求平均，不会得到全局百分位数。Micrometer Timer 已提供 count/sum，同一测量无需重复 Counter。

HeapDumpOnOutOfMemoryError 处理 JVM Java OOME。内核 SIGKILL 无法运行堆转储或关闭钩子。emptyDir 中的诊断文件随 Pod 删除而消失；应处理文件名冲突和磁盘耗尽。堆转储可能包含敏感应用数据，应限制访问和保留期。`ScheduleAnyway` 表示偏好，不是严格可用区分布。

### GC 和 CPU

| 选择 | 验证内容 |
|---|---|
| G1 | 常见起点；暂停目标不是最大延迟保证 |
| ZGC | JDK 专属分代行为及 CPU/内存预算 |
| Shenandoah | 在所选 JDK 发行版和版本中的可用性 |
| Parallel / Serial | 针对吞吐量或小堆工作负载需求比较 |

Java 21 通过 `-XX:+UseZGC -XX:+ZGenerational` 支持分代 ZGC。分代模式在 Java 23 成为默认；Java 24 移除非分代模式，使选择标志过时。应区分 Java 25 的过时警告与未来标志失效。不要将此标志复制到 Java 17。当前仅分代 JDK 使用 `-XX:+UseZGC`，并在确切版本上验证启动。固定 GC 延迟/吞吐量数据需要基准测试。

`availableProcessors()` 不总是 GC 工作线程数。配额、亲和性、JDK 版本和收集器自适应逻辑都重要。增加 GC 线程可能更快耗尽较小 CPU 配额。启动慢时使用 startupProbe，并测量 JIT/GC/CPU 行为。

### JMX 和 JFR

在镜像中包含 JMX exporter 1.6.0 jar，或获取官方制品并验证校验和。以下配置已对实际内存、线程和 GC MBean 测试。JMX 与 Micrometer 使用不同指标名；不要在仪表板中默默混用。GC CollectionTime 从毫秒转换为秒。

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

此本地诊断命令绑定回环地址。从另一 Pod 采集需要显式指标端口、ServiceMonitor 和访问控制。代理 jar 缺失时 JVM 无法启动。NMT 需要启动时设置 `-XX:NativeMemoryTracking=summary`；它不是覆盖所有外部原生库分配的完整 RSS 记账系统。

在线 JFR 采集需要 JDK 工具、适当的同用户权限、附加支持及可写目的地。将 `PID` 替换为 Java 进程 ID，不要假定为 PID 1。

```bash
jcmd PID VM.native_memory summary
jcmd PID JFR.start name=profile settings=profile duration=60s filename=/diagnostics/profile.jfr
jfr summary /diagnostics/profile.jfr
```

从容器复制时，考虑选定容器及 `kubectl cp` 所需 `tar` 是否可用。录制完成后再复制；进程/Pod 替换不保证堆或 JFR 文件保留。

## 4. Python：工作进程和性能剖析

将 `2 × CPU + 1` 应用于主机 `multiprocessing.cpu_count()`，可能超配容器配额。测试 CPU/IO 行为、GIL/原生扩展、每工作进程 RSS 和请求并发。不存在普遍正确的每 CPU 工作进程公式。此 WSGI Flask 示例实际读取 `WEB_CONCURRENCY`，并从一个工作进程、两个线程开始。

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

这些健康端点仅检查示例进程。应为应用实现依赖就绪检查。不要使用 Flask 已移除的 `before_first_request` 钩子。此最小示例禁用 Gunicorn 26 本地管理控制套接字。

区分 WSGI Flask 与 FastAPI 等 ASGI 应用。Gunicorn 26 也有 ASGI worker；若选择 Uvicorn，应区分已弃用的 `uvicorn.workers` 和独立 `uvicorn-worker` 包。不要将 gthread 设置原样用于 ASGI 应用。评估预加载的写时复制收益时，也要考虑 fork 前初始化的线程/连接/客户端。工作进程回收不是内存泄漏的根因修复。

tracemalloc 观察被跟踪的 Python 分配，不覆盖所有原生/RSS 用量。以下是显式本地诊断，不是公开暴露的 HTTP 调试端点。

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

## 5. Node.js：老生代空间和进程内存

`--max-old-space-size` 以 MiB 计，控制 V8 老生代空间。它不是 RSS 上限；新生代、外部/Buffer 及原生内存也需要容量。使用多个工作进程时，为每个进程的堆做预算。Node.js 20 于 2026 年 4 月结束生命周期，因此新示例使用受支持的 Node.js 24 系列。

此单进程示例实现健康端点、内存观察和 SIGTERM 处理。仅根据百分比反复调用 `global.gc()` 不是通用优化。已测试的 Node 24 在 NODE_OPTIONS 中接受 `--expose-gc`；这不能证明强制 GC 对生产有益。

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

`UV_THREADPOOL_SIZE` 影响使用 libuv 线程池的操作，包括文件系统 I/O、部分 DNS 工作和密码学运算。它不涵盖所有网络 I/O。更多线程可能增加栈及并发操作内存。启动前设置，并用真实工作负载测试。

若使用 Node cluster，优先使用 `isPrimary` 并显式限制工作进程数。不要假定 `os.cpus().length`、PM2 `instances: max` 或 `availableParallelism()` 是所有 cgroup 配额的精确公式。重启循环需要退避，关闭期间不得重新创建工作进程。组合 Pod 副本和进程副本会成倍增加工作进程及内存预算。

## 6. Go 和 Rust

### Go

Go 1.25 在 Linux 引入感知 cgroup 的默认 GOMAXPROCS。`go.mod` 语言版本和 GODEBUG 兼容默认值很重要；这些默认行为要求使用 `go 1.25.0` 或更新版本。此示例以 Go 1.27.1 测试。显式在环境中设置 GOMAXPROCS，或调用正值 `runtime.GOMAXPROCS(n)`，会禁用自动更新。使用 `runtime.GOMAXPROCS(0)` 查询不会更改它。

当前运行时将配额向上取整，同时考虑逻辑 CPU 和亲和性。当逻辑 CPU/亲和性数量允许两个时，通常不会选择少于两个，因此 `500m always means 1` 不正确。不要将 automaxprocs 版本/取整行为等同于 Go 内置默认值，也不要盲目同时启用两者。CPU requests 不是配额。

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

GOMEMLIMIT 是 Go 运行时管理内存的软限制，约为 `MemStats.Sys - HeapReleased`。它不是涵盖 cgo、mmap 或外部库的整个进程 RSS 上限。运行时可能超出它以限制 GC 开销。设为容器内存的 80–90% 不保证防止 OOM；远低于存活堆可能引起过度 GC。此程序仅报告设置，不读取或修改 cgroup。

### Rust

没有 GC 不意味着内存用量或延迟确定。观察分配器行为、碎片、并发工作、缓冲区、阻塞工作和操作系统调度。根据性能剖析和平台支持评估 jemalloc 等分配器更改，不要假定普遍提升性能。

此小型 Tokio 程序验证运行时设置；不是 HTTP 服务器。显式 `worker_threads()` 覆盖环境，因此示例省略它。工作线程数不限制 `spawn_blocking` 或外部库线程。

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

没有锁文件的新项目先运行 `cargo build`，再审核并提交锁文件。后续可复现构建可使用 `--locked`。使用有界队列/并发，不要创建无限 CPU 密集型异步任务。没有可比较基准测试，不要发布语言级内存/启动/速度排名。

## 7. PromQL 和警报

这些规则假定使用 kube-prometheus-stack 的 `job="kubelet"`、`metrics_path="/metrics/cadvisor"` 和聚合 `cpu="total"` 序列，以及 kube-state-metrics。针对每 CPU 采集调整聚合，并根据实际标签约定调整选择器。

示例使用每容器 max 聚合，避免重复抓取观测相加。检查同一 Pod/容器名下多个运行时 ID 重叠的重启窗口；这些观测不是精确 CPU 计费数据。多集群需要采集/远程写入路径中的真实 `cluster` 标签；PromQL 不会虚构缺失的集群身份。

有序规则对齐 request/limit 分母并排除零值。工作集不是精确 OOM 预测器；应调查页缓存和回收行为。最近终止原因是 gauge，因此 `increase(reason)` 不是 OOM 次数。OOM 警报结合近期重启及最近记录的 OOM 原因；不会统计间隔内每次 OOM。

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

让 `release: prometheus` 和 `observability` 命名空间匹配 Prometheus 规则选择器。阈值仅为示例。较高节流周期比率不自动意味着需要提高 limit；应关联延迟、吞吐量、并发和节点竞争。

`cluster:pending_pods:count` 对 0/1 阶段 gauge 求和。`count(kube_pod_status_phase{phase="Pending"})` 也会统计零值样本。Pending 可包含已调度但等待镜像/存储的 Pod，因此不等同于资源不足。`node:pods:count` 已是每节点计数；不要再除以集群节点数。

Deployment 聚合应使用 kube-state-metrics 的 Pod→ReplicaSet→Deployment 所有权关系，或已验证的记录规则，不要用 Pod 名正则猜测所有权。长期容量规划应评估滚动发布、节假日、备用容量和 SLO；观察到低用量不是自动驱逐策略。

### JVM 查询和仪表板

这些查询针对使用上方 Micrometer 配置的 JVM。通过 Prometheus instance 标签区分进程，并在真实抓取中验证指标名。

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

`jvm_gc_pause_seconds_sum` 的速率表示每秒墙钟时间观察到的暂停秒数。将其除以进程 CPU 不能得到有效 GC CPU 百分比，也不涵盖所有并发 GC 工作。`jvm_classes_loaded_classes` 是当前已加载类的 gauge；已测试 Micrometer 累计计数器为 `jvm_classes_loaded_count_classes_total`。更改 JDK/库版本时检查实际暴露数据。

使用[上一章](./09-observability-stack.md)的显式数据源 UID 和仪表板预置。比例使用 percentunit 显示，或乘以 100 后使用 percent。不要将原始利用率 gauge 当作热图中的直方图桶。不要将部分面板 JSON 片段描述为完整可导入仪表板。

## 8. EKS Auto Mode 和备用容量

考虑 requests、实际 Node allocatable、DaemonSet/系统开销、Pod 开销、端口、卷、拓扑和污点。4 vCPU 实例不一定为应用请求暴露四个可分配 CPU。大实例不总是更高效，小实例也不总是更便宜。评估故障影响、可用性、定价和碎片。

Auto Mode NodePool 使用 `karpenter.sh/v1`；NodeClass 组为 `eks.amazonaws.com`。此示例引用现有 Auto Mode `default` NodeClass。单独验证该 NodeClass、子网、IAM 角色和区域实例可用性。

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

整合考虑 requests、调度可行性、价格和中断约束；观察到 CPU 低于 30% 不保证节点会被整合。PDB 不阻止所有终止，也不保证强制终止不中断。当 request 未变时，普通调度器不会自动预留过大的 limit。

占位 Pod 可促使系统为更高优先级工作保留备用容量。优先级 -1 低于默认 0，不是可能的最低优先级。`preemptionPolicy: Never` 阻止占位 Pod 抢占其他 Pod；不阻止它被抢占。这不是 EC2 Capacity Reservation，也不是可用性保证，其拓扑、污点和资源形态必须适合真实工作负载。

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

## 发布顺序和验证限制

1. 在有代表性的负载下测量延迟、吞吐量、配额行为、总内存和重启原因。
2. 使用 VPA 和观测结果提出 requests，同时考虑 HPA 与运行时并发。
3. 调整 limits 和余量前，在生产之外测试启动、峰值负载、故障和重启。
4. 金丝雀期间观察 SLO、成本、放置和中断；保留回滚所需配置。

验证在本地运行了 Java/Spring/JMX 指标和 JFR/NMT、Gunicorn/Node 健康与 SIGTERM 行为、Go 运行时报告和 Tokio 工作线程配置。PromQL 计算用例涵盖重复抓取、多集群、零分母、历史 OOM 状态及 Pending 0/1 gauge。未部署 EKS、修改 cgroup 配额、强制触发 OOM 或进行性能基准测试。

## 官方参考资料

- [Kubernetes 资源](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [节点压力驱逐](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)
- [Go 容器感知 GOMAXPROCS](https://go.dev/blog/container-aware-gomaxprocs)
- [Go GC 指南](https://go.dev/doc/gc-guide)
- [Java 21 选项](https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html)
- [JEP 474](https://openjdk.org/jeps/474)
- [JEP 490](https://openjdk.org/jeps/490)
- [Spring Boot 属性](https://docs.spring.io/spring-boot/appendix/application-properties/index.html)
- [JMX exporter 1.6.0](https://github.com/prometheus/jmx_exporter/releases/tag/1.6.0)
- [Gunicorn 设置](https://gunicorn.org/reference/settings/)
- [Flask 变更日志](https://flask.palletsprojects.com/en/stable/changes/)
- [Node.js 24 CLI](https://nodejs.org/download/release/v24.21.0/docs/api/cli.html)
- [Tokio 运行时构建器](https://docs.rs/tokio/1.53.1/tokio/runtime/struct.Builder.html)

---

< [上一篇：可观测性技术栈](./09-observability-stack.md) | [目录](./README.md) | [下一篇：EKS 升级](./11-upgrade-operations.md) >
