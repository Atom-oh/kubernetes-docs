# Resource optimization: requests, limits and language runtimes

> Reviewed 2026-09-11. Examples were checked with Kubernetes 1.36 schemas,
> Java 21 / Spring Boot 4.1.1, Python 3.12 / Gunicorn 26.2.0,
> Node.js 24.21, Go 1.27.1 and Rust 1.98 / Tokio 1.53.1.

Do not size workloads from a language name or fixed percentage alone. Measure throughput and
latency SLOs under representative load, startup, restart, GC and failure conditions. Tune requests,
limits, replicas and runtime concurrency together. Example percentages and thresholds are test
starting points, not performance guarantees.

## 1. Requests, limits and QoS

| Resource | Requests | Limits |
|---|---|---|
| CPU | Scheduling accounting and relative weight under contention | Linux cgroup CPU quota can restrict execution |
| Memory | Scheduling accounting | Allocation pressure can cause cgroup OOM when reclaim cannot satisfy it |
| Unspecified | Admission defaults and higher-level policies still matter | No container limit may exist, but node/ancestor cgroup limits still apply |

A request is not physical CPU pinning or preallocated memory, and it does not guarantee application
performance. If only a limit is supplied and no other admission default sets the request, Kubernetes
copies the limit into the request. Inspect the admitted Pod after LimitRange and other policies.

These examples use container-level resources, not Pod-level resources.
Create `resource-demo` first and compare QoS without a LimitRange injecting resource defaults.
Guaranteed requires positive equal CPU and memory requests/limits and the applicable conditions
for regular and init containers.

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

BestEffort has no CPU/memory requests or limits; other configurations can be Burstable.
Check version-specific rules when using Pod-level resources or sidecar/init resource accounting.

QoS is not an absolute eviction ordering. Under memory pressure, kubelet considers whether usage
exceeds requests, Pod Priority and usage relative to requests. Guaranteed and within-request
Burstable pods tend to be considered later, but Guaranteed is not always the last victim.
Distinguish DiskPressure eviction from container-limit OOM. OOMKilled is normally a container
termination reason, not a Pod phase. An individual process may be killed; if PID 1 exits,
the restart policy determines container restart behavior.

### CPU quota and memory boundaries

cgroup v1 uses `cpu.cfs_quota_us` / `cpu.cfs_period_us`; v2 uses `cpu.max`.
100ms is a common quota period, not a universal constant. With 500m and a 100ms period,
all threads share 50ms of aggregate execution budget. Throttling can affect both latency and
throughput. The throttled-period ratio measures periods containing throttling, not lost CPU time.

A memory limit is not a heap limit. Distinguish cgroup v1 `memory.limit_in_bytes` from v2
`memory.max`. Consider RSS, native allocation, thread stacks, page cache and memory-backed
emptyDir usage. A liveness probe that restarts the application when memory approaches a threshold
can hide the cause and create restart loops; it is not a general OOM solution.

Removing a CPU limit can reduce that container's quota throttling, but does not remove contention,
ancestor quotas or node limits. Assess requests, priority, isolation, policy and SLOs together.

### Namespace defaults and budgets

LimitRange controls admission defaults and per-resource constraints. ResourceQuota controls
namespace admission budgets for requests, limits and object counts. They do not directly meter
or cap live CPU usage or cost. Create the `production` namespace before applying these policies.

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

## 2. Measurement and VPA

Observe distributions, peaks, startup cost and memory growth across a representative period.
P70 requests and P99 limits are hypotheses to test, not universal defaults.
GC, model loading, JIT, cryptography, sidecars and batch-input sizes vary even within one language.
Do not hide a leak by only raising limits or automatically classify idle standby/disaster-recovery pods as waste.

Use the [scaling chapter](./06-scaling-strategies.md) for pinned VPA and Goldilocks installation.
Goldilocks creates/displays VPAs for selected namespaces/workloads; installation does not automatically
optimize everything. This VPA observes the `resource-java` Deployment shown below.

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

`Off` only recommends. `target` is a request recommendation; lower/upper bounds describe the
recommendation range. Do not directly treat upperBound as the memory limit or uncappedTarget as
the applied value. `RequestsAndLimits` can adjust limits while preserving an existing ratio;
it does not copy upperBound into limits.

In VPA 1.7.1, deprecated `Auto` behaves as `Recreate`. Check the prerequisites for
`InPlaceOrRecreate`/`InPlace` and Kubernetes in-place support. `Initial` still changes requests
on new pods and therefore the denominator of request-based HPA utilization.
It is not automatically conflict-free with HPA.

If one pod sustains 200 RPS at the required SLO, 1,000 RPS needs five pods in steady state.
Maintaining that throughput after losing one pod requires at least six. That does not guarantee
survival of an entire AZ. Also distinguish adding 20% capacity from leaving 20% of available
capacity unused; the latter requires `ceil(1000 / (200 × 0.8)) = 7`.

## 3. JVM: heap and container memory

`MaxRAMPercentage` is an input to JVM heap ergonomics based on detected memory.
75% is not universally optimal, and it is not a live resizer that immediately follows Pod limit
changes. `-Xmx`, `-XX:MaxRAM` and small-heap ergonomics also matter.
Metaspace, code cache, stacks, direct buffers, JNI and allocators consume memory outside the heap.
A fixed 25% does not guarantee enough non-heap capacity.

The JVM does not automatically read `JAVA_OPTS`; the image entrypoint must pass it to the command.
This example uses the JVM-recognized `JAVA_TOOL_OPTIONS` and an explicit `java -jar` command.
60% is a profiling starting point.

The complete Spring Boot example below was built with Java 21 and Boot 4.1.1.
Save the files at the indicated project paths.

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

The minimal project does not include wrapper files; use `mvn package` unless you add a wrapper.
Your image must contain the built jar at `/app/resource-api.jar` and a Java 21-compatible runtime.
The `registry.example.com` image below is a placeholder to replace.
Namespace creation, image building and registry access are separate prerequisites.
Readiness/liveness paths match the application's actual Actuator endpoints.

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

The Prometheus configuration path is `management.prometheus.metrics.export`.
Do not expose metrics and detailed health information indiscriminately.
Only metrics with histogram publication can support `_bucket` queries; averaging client-computed
percentiles across pods does not produce a global percentile.
A Micrometer Timer already supplies count/sum, so a duplicate Counter is unnecessary for the same measurement.

HeapDumpOnOutOfMemoryError handles JVM Java OOME. Kernel SIGKILL cannot run heap-dump or shutdown
hooks. Diagnostic files in emptyDir disappear with Pod deletion; handle filename collisions and
disk exhaustion. Heap dumps can contain sensitive application data, so restrict access and retention.
`ScheduleAnyway` expresses a preference, not strict AZ distribution.

### GC and CPU

| Choice | What to validate |
|---|---|
| G1 | Common starting point; pause targets are not maximum-latency guarantees |
| ZGC | JDK-specific generational behavior and CPU/memory budget |
| Shenandoah | Availability in the selected JDK distribution and version |
| Parallel / Serial | Compare for throughput or small-heap workload requirements |

Java 21 supports generational ZGC with `-XX:+UseZGC -XX:+ZGenerational`.
Generational mode became the default in Java 23; Java 24 removed non-generational mode and
made the selection flag obsolete. Distinguish an obsolete warning in Java 25 from future flag expiry.
Do not copy this flag into Java 17. On current generational-only JDKs, use `-XX:+UseZGC` and
verify startup on the exact version. Fixed GC latency/throughput numbers require benchmarks.

`availableProcessors()` is not always the GC worker count. Quota, affinity, JDK version and
collector ergonomics matter. Adding GC threads can exhaust a small CPU quota sooner.
For slow startup, use a startupProbe and measure JIT/GC/CPU behavior.

### JMX and JFR

Include the JMX exporter 1.6.0 jar in the image or obtain the official artifact and verify its
checksum. The following configuration was tested against actual memory, threading and GC MBeans.
JMX and Micrometer use different metric names; do not silently mix them in dashboards.
GC CollectionTime is converted from milliseconds to seconds.

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

This local diagnostic command binds to loopback. Collection from another pod needs an explicit
metrics port, ServiceMonitor and access controls. The JVM cannot start if the agent jar is absent.
NMT requires `-XX:NativeMemoryTracking=summary` at startup; it is not a complete RSS accounting
system for every external native-library allocation.

Live JFR collection requires JDK tools, appropriate same-user permissions, attach support and
a writable destination. Replace `PID` with the Java process ID rather than assuming PID 1.

```bash
jcmd PID VM.native_memory summary
jcmd PID JFR.start name=profile settings=profile duration=60s filename=/diagnostics/profile.jfr
jfr summary /diagnostics/profile.jfr
```

When copying from a container, account for the selected container and the availability of `tar`
for `kubectl cp`. Copy after the recording finishes; process/Pod replacement does not guarantee
that heap or JFR files survive.

## 4. Python: workers and profiling

Applying `2 × CPU + 1` to host `multiprocessing.cpu_count()` can oversubscribe a container quota.
Test CPU/IO behavior, the GIL/native extensions, per-worker RSS and request concurrency.
There is no universally correct workers-per-CPU formula.
This WSGI Flask example actually reads `WEB_CONCURRENCY` and starts with one worker and two threads.

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

These health endpoints only check the example process. Implement dependency readiness for your
application. Do not use Flask's removed `before_first_request` hook.
Gunicorn 26's local administration control socket is disabled in this minimal example.

Distinguish WSGI Flask from ASGI applications such as FastAPI. Gunicorn 26 also has an ASGI worker;
if choosing Uvicorn, distinguish deprecated `uvicorn.workers` from the separate `uvicorn-worker`
package. Do not apply gthread settings unchanged to an ASGI app.
Evaluate preload copy-on-write benefits alongside threads/connections/clients initialized before fork.
Worker recycling is not a root-cause fix for a leak.

tracemalloc observes tracked Python allocations, not all native/RSS usage.
The following is an explicit local diagnostic, not a publicly exposed HTTP debug endpoint.

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

## 5. Node.js: old space and process memory

`--max-old-space-size` is measured in MiB and controls V8 old space.
It is not an RSS ceiling; young generation, external/Buffer and native memory also need capacity.
With multiple worker processes, budget every process's heap.
Node.js 20 reached EOL in April 2026, so new examples use the supported Node.js 24 line.

This single-process example implements health endpoints, memory observation and SIGTERM handling.
Repeated `global.gc()` calls based only on a percentage are not a general optimization.
The tested Node 24 accepts `--expose-gc` in NODE_OPTIONS; that does not establish a production
benefit from forced GC.

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

`UV_THREADPOOL_SIZE` affects operations that use libuv's thread pool, including filesystem I/O,
some DNS work and cryptography. It does not cover all network I/O.
More threads can increase stack and concurrent-operation memory. Set it before startup and
test with the real workload.

If using Node cluster, prefer `isPrimary` and explicitly bound worker count.
Do not assume `os.cpus().length`, PM2 `instances: max` or `availableParallelism()` is an exact
formula for every cgroup quota. Restart loops need backoff and must not recreate workers during
shutdown. Combining Pod replicas and process replicas multiplies worker and memory budgets.

## 6. Go and Rust

### Go

Go 1.25 introduced cgroup-aware default GOMAXPROCS on Linux.
The `go.mod` language version and GODEBUG compatibility defaults matter; use `go 1.25.0` or newer
for these defaults. This example was tested with Go 1.27.1.
Setting GOMAXPROCS explicitly in the environment or calling positive `runtime.GOMAXPROCS(n)`
disables automatic updates. Querying with `runtime.GOMAXPROCS(0)` does not change it.

The current runtime rounds quota up and also considers logical CPUs and affinity.
It generally does not choose fewer than two when logical CPU/affinity counts allow two, so
`500m always means 1` is incorrect. Do not equate automaxprocs version/rounding behavior with
Go's built-in defaults or blindly enable both. CPU requests are not quota.

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

GOMEMLIMIT is a soft limit for Go-runtime-managed memory, approximately
`MemStats.Sys - HeapReleased`. It is not a whole-process RSS ceiling covering cgo, mmap or
external libraries. The runtime may exceed it to limit GC overhead.
Setting it to 80–90% of container memory does not guarantee OOM prevention; setting it far below
the live heap can cause excessive GC. This program only reports settings and does not read or mutate cgroups.

### Rust

Absence of GC does not make memory use or latency deterministic. Observe allocator behavior,
fragmentation, concurrent work, buffers, blocking work and OS scheduling.
Evaluate allocator changes such as jemalloc from profiles and platform support rather than
assuming a universal performance improvement.

This small Tokio program validates runtime settings; it is not an HTTP server.
An explicit `worker_threads()` overrides the environment, so the example omits it.
Worker-thread count is not a limit on `spawn_blocking` or external-library threads.

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

For a new project without a lockfile, run `cargo build`, then review and commit the lockfile.
Subsequent reproducible builds can use `--locked`.
Use bounded queues/concurrency rather than creating unlimited CPU-heavy async tasks.
Do not publish language-wide memory/startup/speed rankings without comparable benchmarks.

## 7. PromQL and alerts

These rules assume kube-prometheus-stack's `job="kubelet"`, `metrics_path="/metrics/cadvisor"`
and aggregate `cpu="total"` series, plus kube-state-metrics.
Adapt aggregation for per-CPU collection and selectors for your actual label contract.

The example uses per-container max aggregation to avoid summing duplicate scrape observations.
Inspect restart windows where multiple runtime IDs overlap under one Pod/container name;
these observations are not precise CPU billing data.
Multiple clusters need a real `cluster` label in the collection/remote-write path;
PromQL does not invent a missing cluster identity.

The ordered rules align request/limit denominators and exclude zero.
Working set is not an exact OOM predictor; investigate page cache and reclaim behavior.
Last termination reason is a gauge, so `increase(reason)` is not an OOM count.
The OOM alert combines a recent restart with the last recorded OOM reason; it does not count
every OOM within the interval.

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

Match `release: prometheus` and the `observability` namespace to your Prometheus rule selector.
Thresholds are examples. High throttled-period ratio does not automatically prescribe a larger
limit; correlate latency, throughput, concurrency and node contention.

`cluster:pending_pods:count` sums the 0/1 phase gauge.
`count(kube_pod_status_phase{phase="Pending"})` also counts zero-valued samples.
Pending can include scheduled pods waiting for images/storage, so it is not equivalent to
insufficient resources. `node:pods:count` is already a per-node count; do not divide it by
the cluster's node count.

For Deployment aggregation, use kube-state-metrics Pod→ReplicaSet→Deployment ownership or
validated recording rules instead of guessing ownership from Pod-name regexes.
Assess rollouts, holidays, standby capacity and SLOs in long-term sizing; observed low usage is
not an automatic eviction policy.

### JVM queries and dashboards

These queries target JVMs using the Micrometer configuration above.
Distinguish processes by Prometheus's instance label and verify the metric names in real scrapes.

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

The rate of `jvm_gc_pause_seconds_sum` measures observed pause seconds per wall-clock second.
Dividing it by process CPU does not yield a valid GC CPU percentage, and it does not capture all
concurrent GC work. `jvm_classes_loaded_classes` is a gauge of currently loaded classes;
the tested Micrometer cumulative counter is `jvm_classes_loaded_count_classes_total`.
Check actual exposition when changing JDK/library versions.

Use the [preceding chapter's](./09-observability-stack.md) explicit datasource UIDs and dashboard
provisioning. Display ratios with percentunit, or multiply by 100 and use percent.
Do not treat raw utilization gauges as histogram buckets in a heatmap.
Do not describe a partial panel JSON fragment as a complete importable dashboard.

## 8. EKS Auto Mode and spare capacity

Account for requests, actual Node allocatable, DaemonSet/system overhead, Pod overhead,
ports, volumes, topology and taints. A 4-vCPU instance does not necessarily expose four allocatable
CPUs for application requests. Larger instances are not always more efficient, nor are smaller
instances always cheaper. Evaluate failure impact, availability, pricing and fragmentation.

Auto Mode NodePools use `karpenter.sh/v1`; the NodeClass group is `eks.amazonaws.com`.
This example references an existing Auto Mode `default` NodeClass.
Validate that NodeClass, subnets, IAM role and regional instance availability separately.

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

Consolidation considers requests, scheduling feasibility, price and disruption constraints;
observed CPU below 30% is not a guarantee that a node will consolidate.
PDBs do not prevent every termination or guarantee uninterrupted forced termination.
An oversized limit is not automatically reserved by the ordinary scheduler when the request is unchanged.

Placeholder pods can encourage spare capacity for higher-priority work.
Priority -1 is below default 0, not the lowest possible priority.
`preemptionPolicy: Never` stops the placeholder from preempting others; it does not prevent the
placeholder from being preempted. This is not an EC2 Capacity Reservation or availability guarantee,
and its topology, taints and resource shape must fit the real workload.

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

## Rollout sequence and validation limits

1. Measure latency, throughput, quota behavior, total memory and restart causes under representative load.
2. Use VPA and observations to propose requests, considering HPA and runtime concurrency together.
3. Test startup, peak load, failures and restarts outside production before tuning limits and headroom.
4. Observe SLOs, cost, placement and disruption during a canary; retain the configuration needed to roll back.

Validation ran Java/Spring/JMX metrics and JFR/NMT, Gunicorn/Node health and SIGTERM behavior,
Go runtime reporting and Tokio worker configuration locally.
PromQL calculation cases covered duplicate scrapes, multiple clusters, zero denominators,
historical OOM state and Pending 0/1 gauges.
This did not deploy EKS, mutate cgroup quotas, force OOM or benchmark performance.

## Official references

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

< [Previous: Observability stack](./09-observability-stack.md) | [Contents](./README.md) | [Next: EKS upgrades](./11-upgrade-operations.md) >
