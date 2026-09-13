# Optimización de recursos: requests, limits y runtimes de lenguaje

> **Última actualización**: 11 de septiembre de 2026. Ejemplos comprobados con esquemas Kubernetes 1.36,
> Java 21 / Spring Boot 4.1.1, Python 3.12 / Gunicorn 26.2.0,
> Node.js 24.21, Go 1.27.1 y Rust 1.98 / Tokio 1.53.1.

No dimensione cargas solo por el lenguaje o un porcentaje fijo. Mida los SLO de rendimiento y latencia bajo carga representativa, arranque, reinicio, GC y fallos. Ajuste requests, limits, réplicas y concurrencia del runtime conjuntamente. Los porcentajes y umbrales son puntos de partida de pruebas, no garantías de rendimiento.

## 1. Requests, limits y QoS

| Recurso | Requests | Limits |
|---|---|---|
| CPU | Contabilización para planificación y peso relativo bajo contención | La cuota CPU de cgroup Linux puede restringir la ejecución |
| Memoria | Contabilización para planificación | La presión de asignación puede causar OOM del cgroup si la recuperación de memoria no basta |
| Sin especificar | Siguen importando los valores de admisión y políticas superiores | Puede no haber límite de contenedor, pero sí de nodo/cgroup antecesor |

Un request no fija CPU física ni preasigna memoria, y no garantiza rendimiento. Si solo se proporciona un limit y ningún valor de admisión establece el request, Kubernetes copia el limit al request. Inspeccione el Pod admitido tras LimitRange y otras políticas.

Estos ejemplos usan recursos por contenedor, no por Pod. Cree primero `resource-demo` y compare QoS sin un LimitRange que inyecte valores. Guaranteed requiere requests/limits positivos e iguales de CPU y memoria, y las condiciones aplicables a contenedores ordinarios e init.

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

BestEffort no tiene requests ni limits de CPU/memoria; otras configuraciones pueden ser Burstable. Revise reglas por versión al usar recursos Pod o contabilización de sidecars/init.

QoS no es un orden absoluto de expulsión. Bajo presión de memoria, kubelet considera si el uso supera requests, Pod Priority y el uso relativo a requests. Guaranteed y Burstable dentro de requests suelen considerarse después, pero Guaranteed no siempre es la última víctima. Distinga expulsión DiskPressure de OOM por límite de contenedor. OOMKilled normalmente es una razón de terminación de contenedor, no una fase Pod. Puede terminar un proceso individual; si sale PID 1, la política de reinicio determina qué ocurre con el contenedor.

### Cuota CPU y límites de memoria

cgroup v1 usa `cpu.cfs_quota_us` / `cpu.cfs_period_us`; v2 usa `cpu.max`. 100ms es un período habitual, no universal. Con 500m y un período de 100ms, todos los hilos comparten 50ms de ejecución agregada. El throttling puede afectar a latencia y rendimiento. La proporción de períodos limitados mide períodos que contienen throttling, no tiempo CPU perdido.

Un límite de memoria no es un límite del heap. Distinga `memory.limit_in_bytes` de cgroup v1 y `memory.max` de v2. Considere RSS, asignación nativa, pilas, caché de páginas y emptyDir en memoria. Un liveness probe que reinicie cerca de un umbral puede ocultar la causa y crear bucles; no es una solución OOM general.

Eliminar un limit CPU puede reducir el throttling de cuota de ese contenedor, pero no elimina contención, cuotas antecesoras ni límites del nodo. Evalúe conjuntamente requests, prioridad, aislamiento, políticas y SLO.

### Valores predeterminados y presupuestos de namespace

LimitRange controla valores de admisión y restricciones por recurso. ResourceQuota controla presupuestos de admisión del namespace para requests, limits y objetos. No miden ni limitan directamente CPU real o coste. Cree `production` antes de aplicar estas políticas.

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

## 2. Medición y VPA

Observe distribuciones, picos, coste de arranque y crecimiento de memoria durante un período representativo. Requests P70 y limits P99 son hipótesis, no valores universales. GC, carga de modelos, JIT, criptografía, sidecars y entradas por lotes varían incluso dentro de un lenguaje. No oculte fugas aumentando límites ni clasifique automáticamente Pods de reserva/recuperación inactivos como desperdicio.

Use el [capítulo de escalado](./06-scaling-strategies.md) para instalar VPA y Goldilocks fijados. Goldilocks crea/muestra VPA para namespaces/cargas seleccionados; instalarlo no optimiza todo. Este VPA observa el Deployment `resource-java` posterior.

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

`Off` solo recomienda. `target` recomienda un request; los límites inferior/superior describen el intervalo recomendado. No trate upperBound directamente como limit de memoria ni uncappedTarget como valor aplicado. `RequestsAndLimits` puede ajustar limits conservando una proporción existente; no copia upperBound a limits.

En VPA 1.7.1, `Auto` obsoleto se comporta como `Recreate`. Revise requisitos de `InPlaceOrRecreate`/`InPlace` y soporte in-place Kubernetes. `Initial` sigue cambiando requests en Pods nuevos y, por tanto, el denominador de utilización HPA. No está automáticamente libre de conflictos con HPA.

Si un Pod sostiene 200 RPS con el SLO requerido, 1,000 RPS necesitan cinco Pods en estado estable. Mantenerlo tras perder uno requiere al menos seis. No garantiza soportar la pérdida de una AZ completa. Distinga añadir 20% de capacidad de dejar 20% sin usar; lo segundo requiere `ceil(1000 / (200 × 0.8)) = 7`.

## 3. JVM: heap y memoria del contenedor

`MaxRAMPercentage` es una entrada de la ergonomía del heap basada en memoria detectada. 75% no es universalmente óptimo ni un redimensionador que siga inmediatamente cambios del limit Pod. También importan `-Xmx`, `-XX:MaxRAM` y la ergonomía de heaps pequeños. Metaspace, caché de código, pilas, buffers directos, JNI y asignadores consumen fuera del heap. Un 25% fijo no garantiza capacidad suficiente fuera de él.

La JVM no lee automáticamente `JAVA_OPTS`; el entrypoint debe pasarlo al comando. El ejemplo usa `JAVA_TOOL_OPTIONS`, reconocido por la JVM, y `java -jar` explícito. 60% es un punto inicial de perfilado.

El ejemplo completo Spring Boot se compiló con Java 21 y Boot 4.1.1. Guarde los archivos en las rutas indicadas.

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

El proyecto mínimo no incluye wrapper; use `mvn package` salvo que añada uno. La imagen debe contener el jar compilado en `/app/resource-api.jar` y un runtime compatible con Java 21. La imagen `registry.example.com` es un marcador que sustituir. Crear el namespace, construir la imagen y acceder al registro son requisitos separados. Las rutas readiness/liveness coinciden con endpoints Actuator reales.

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

La ruta de configuración Prometheus es `management.prometheus.metrics.export`. No exponga indiscriminadamente métricas y detalles de salud. Solo las métricas que publican histogramas admiten consultas `_bucket`; promediar percentiles calculados por clientes entre Pods no produce un percentil global. Un Timer Micrometer ya aporta count/sum, por lo que no hace falta un Counter duplicado para la misma medición.

HeapDumpOnOutOfMemoryError maneja Java OOME de la JVM. SIGKILL del kernel no ejecuta hooks de heap dump o cierre. Los diagnósticos en emptyDir desaparecen al borrar el Pod; gestione colisiones de nombres y falta de disco. Los heap dumps pueden contener datos sensibles: restrinja acceso y retención. `ScheduleAnyway` expresa una preferencia, no distribución estricta entre AZ.

### GC y CPU

| Opción | Qué validar |
|---|---|
| G1 | Punto inicial habitual; objetivos de pausa no garantizan latencia máxima |
| ZGC | Comportamiento generacional específico del JDK y presupuesto CPU/memoria |
| Shenandoah | Disponibilidad en la distribución y versión JDK elegidas |
| Parallel / Serial | Comparar según necesidades de rendimiento o heap pequeño |

Java 21 admite ZGC generacional con `-XX:+UseZGC -XX:+ZGenerational`. Pasó a ser predeterminado en Java 23; Java 24 eliminó el modo no generacional y dejó obsoleto el selector. Distinga una advertencia de obsolescencia en Java 25 de su futura eliminación. No copie el flag a Java 17. En JDK actuales exclusivamente generacionales, use `-XX:+UseZGC` y verifique el arranque en la versión exacta. Las cifras fijas de GC requieren benchmarks.

`availableProcessors()` no siempre es el número de trabajadores GC. Importan cuota, afinidad, versión JDK y ergonomía del recolector. Añadir hilos GC puede agotar antes una cuota CPU pequeña. Para arranque lento, use startupProbe y mida JIT/GC/CPU.

### JMX y JFR

Incluya el jar JMX exporter 1.6.0 en la imagen, u obtenga el artefacto oficial y verifique su checksum. La configuración se probó con MBeans reales de memoria, hilos y GC. JMX y Micrometer usan nombres distintos; no los mezcle silenciosamente en dashboards. GC CollectionTime se convierte de milisegundos a segundos.

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

El comando local se vincula a loopback. Recoger desde otro Pod necesita puerto de métricas explícito, ServiceMonitor y controles. La JVM no arranca si falta el jar del agente. NMT requiere `-XX:NativeMemoryTracking=summary` al arrancar; no contabiliza completamente RSS de todas las asignaciones de bibliotecas nativas externas.

La captura JFR en vivo requiere herramientas JDK, permisos adecuados del mismo usuario, soporte de attach y destino escribible. Sustituya `PID` por el proceso Java en vez de asumir PID 1.

```bash
jcmd PID VM.native_memory summary
jcmd PID JFR.start name=profile settings=profile duration=60s filename=/diagnostics/profile.jfr
jfr summary /diagnostics/profile.jfr
```

Al copiar desde un contenedor, considere el contenedor elegido y la disponibilidad de `tar` para `kubectl cp`. Copie cuando finalice la grabación; reemplazar proceso/Pod no garantiza que sobrevivan archivos heap o JFR.

## 4. Python: workers y perfilado

Aplicar `2 × CPU + 1` al `multiprocessing.cpu_count()` del host puede sobrepasar la cuota del contenedor. Pruebe CPU/IO, GIL/extensiones nativas, RSS por worker y concurrencia. No hay fórmula universal de workers por CPU. Este ejemplo Flask WSGI lee realmente `WEB_CONCURRENCY` y empieza con un worker y dos hilos.

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

Los endpoints de salud solo comprueban el proceso de ejemplo. Implemente readiness de dependencias. No use el hook Flask eliminado `before_first_request`. El socket local de administración de Gunicorn 26 está desactivado en este ejemplo mínimo.

Distinga Flask WSGI de aplicaciones ASGI como FastAPI. Gunicorn 26 también tiene un worker ASGI; si usa Uvicorn, distinga `uvicorn.workers` obsoleto del paquete separado `uvicorn-worker`. No aplique ajustes gthread sin cambios a ASGI. Evalúe los beneficios copy-on-write de preload junto con hilos/conexiones/clientes inicializados antes de fork. Reciclar workers no corrige la causa de una fuga.

tracemalloc observa asignaciones Python registradas, no todo el uso nativo/RSS. Lo siguiente es diagnóstico local explícito, no un endpoint HTTP público de depuración.

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

## 5. Node.js: old space y memoria de proceso

`--max-old-space-size` se mide en MiB y controla old space de V8. No limita RSS: la generación joven, memoria externa/Buffer y nativa también necesitan capacidad. Con varios procesos worker, presupueste cada heap. Node.js 20 llegó a EOL en abril de 2026, por lo que los nuevos ejemplos usan Node.js 24 compatible.

Este ejemplo de un proceso implementa salud, observación de memoria y SIGTERM. Llamadas repetidas `global.gc()` basadas solo en un porcentaje no son una optimización general. Node 24 probado acepta `--expose-gc` en NODE_OPTIONS; eso no demuestra beneficio productivo de forzar GC.

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

`UV_THREADPOOL_SIZE` afecta a operaciones que usan el pool libuv, como E/S de archivos, parte de DNS y criptografía. No cubre toda E/S de red. Más hilos pueden aumentar memoria de pilas y operaciones concurrentes. Establézcalo antes del arranque y pruebe la carga real.

Si usa Node cluster, prefiera `isPrimary` y limite explícitamente workers. No asuma que `os.cpus().length`, PM2 `instances: max` o `availableParallelism()` sean fórmulas exactas para toda cuota cgroup. Los bucles de reinicio necesitan backoff y no deben recrear workers durante el cierre. Combinar réplicas Pod y de proceso multiplica workers y presupuestos de memoria.

## 6. Go y Rust

### Go

Go 1.25 introdujo GOMAXPROCS predeterminado consciente de cgroups en Linux. Importan la versión de lenguaje de `go.mod` y los valores de compatibilidad GODEBUG; use `go 1.25.0` o posterior para esos valores. Este ejemplo se probó con Go 1.27.1. Establecer GOMAXPROCS explícitamente o llamar a `runtime.GOMAXPROCS(n)` positivo desactiva actualizaciones automáticas. Consultarlo con `runtime.GOMAXPROCS(0)` no lo cambia.

El runtime actual redondea la cuota hacia arriba y considera CPU lógicas y afinidad. Generalmente no elige menos de dos cuando esas cantidades permiten dos, por lo que `500m always means 1` es incorrecto. No equipare versión/redondeo de automaxprocs con los valores integrados de Go ni active ambos a ciegas. Requests CPU no son cuota.

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

GOMEMLIMIT es un límite flexible de memoria gestionada por Go, aproximadamente `MemStats.Sys - HeapReleased`. No es un techo RSS de todo el proceso que incluya cgo, mmap o bibliotecas externas. El runtime puede superarlo para limitar coste GC. Establecerlo al 80–90% de memoria del contenedor no garantiza evitar OOM; muy por debajo del heap vivo puede causar GC excesivo. El programa solo informa ajustes, no lee ni modifica cgroups.

### Rust

No tener GC no hace deterministas memoria o latencia. Observe asignador, fragmentación, trabajo concurrente, buffers, tareas bloqueantes y planificación del SO. Evalúe cambios como jemalloc según perfiles y soporte, sin asumir una mejora universal.

Este pequeño programa Tokio valida ajustes del runtime; no es un servidor HTTP. `worker_threads()` explícito prevalece sobre el entorno, por lo que se omite. El número de hilos worker no limita `spawn_blocking` ni hilos de bibliotecas externas.

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

En proyectos nuevos sin lockfile, ejecute `cargo build`, revise y confirme el lockfile. Las compilaciones reproducibles posteriores pueden usar `--locked`. Use colas/concurrencia acotadas, no tareas async intensivas en CPU ilimitadas. No publique rankings por lenguaje de memoria/arranque/velocidad sin benchmarks comparables.

## 7. PromQL y alertas

Las reglas suponen `job="kubelet"`, `metrics_path="/metrics/cadvisor"` y series agregadas `cpu="total"` de kube-prometheus-stack, además de kube-state-metrics. Adapte la agregación a recogida por CPU y los selectores al contrato real de etiquetas.

El ejemplo usa max por contenedor para no sumar observaciones duplicadas. Inspeccione ventanas de reinicio donde varios IDs runtime se solapan con el mismo nombre Pod/contenedor; no son datos precisos de facturación CPU. Varios clústeres necesitan una etiqueta `cluster` real en recogida/remote-write; PromQL no inventa una identidad ausente.

Las reglas ordenadas alinean denominadores request/limit y excluyen cero. Working set no predice OOM exactamente; investigue caché de páginas y recuperación de memoria. La última razón de terminación es un gauge, así que `increase(reason)` no cuenta OOM. La alerta combina reinicio reciente y última razón OOM; no cuenta todos los OOM del intervalo.

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

Haga coincidir `release: prometheus` y namespace `observability` con su selector de reglas. Los umbrales son ejemplos. Una proporción alta de períodos limitados no prescribe automáticamente un limit mayor; correlacione latencia, rendimiento, concurrencia y contención de nodo.

`cluster:pending_pods:count` suma el gauge de fase 0/1. `count(kube_pod_status_phase{phase="Pending"})` también cuenta muestras cero. Pending puede incluir Pods ya programados esperando imágenes/almacenamiento; no equivale a recursos insuficientes. `node:pods:count` ya cuenta por nodo; no lo divida por el número de nodos del clúster.

Para agregar por Deployment, use la relación Pod→ReplicaSet→Deployment de kube-state-metrics o reglas validadas, no regex de nombres Pod. Evalúe rollouts, festivos, reserva y SLO en dimensionamiento a largo plazo; observar poco uso no es una política automática de expulsión.

### Consultas y dashboards JVM

Las consultas se dirigen a JVM con la configuración Micrometer anterior. Distinga procesos por la etiqueta instance y verifique nombres en scrapes reales.

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

La tasa de `jvm_gc_pause_seconds_sum` mide segundos de pausa por segundo de reloj. Dividirla por CPU del proceso no produce un porcentaje válido de CPU GC ni captura todo el trabajo GC concurrente. `jvm_classes_loaded_classes` es un gauge de clases actualmente cargadas; el contador acumulativo Micrometer probado es `jvm_classes_loaded_count_classes_total`. Revise exposición real al cambiar JDK/bibliotecas.

Use los UID explícitos y el aprovisionamiento del [capítulo anterior](./09-observability-stack.md). Muestre proporciones con percentunit, o multiplique por 100 y use percent. No trate gauges brutos de utilización como buckets de histograma en un heatmap. No describa un fragmento parcial JSON de panel como dashboard completo importable.

## 8. EKS Auto Mode y capacidad de reserva

Considere requests, Node allocatable real, sobrecarga DaemonSet/sistema/Pod, puertos, volúmenes, topología y taints. Una instancia de 4 vCPU no necesariamente expone cuatro CPU asignables a aplicaciones. Las grandes no siempre son más eficientes ni las pequeñas más baratas. Evalúe impacto de fallos, disponibilidad, precio y fragmentación.

Los NodePools Auto Mode usan `karpenter.sh/v1`; el grupo NodeClass es `eks.amazonaws.com`. El ejemplo referencia un NodeClass Auto Mode `default` existente. Valide por separado NodeClass, subredes, rol IAM y disponibilidad regional de instancias.

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

La consolidación considera requests, viabilidad de planificación, precio y restricciones de interrupción; CPU observada por debajo del 30% no garantiza consolidación. Los PDB no impiden toda terminación ni garantizan terminación forzada sin interrupción. Un limit sobredimensionado no se reserva automáticamente por el scheduler ordinario si el request no cambia.

Los Pods de relleno pueden favorecer capacidad de reserva para tareas prioritarias. Prioridad -1 está por debajo de la predeterminada 0, no es la mínima posible. `preemptionPolicy: Never` impide que el Pod de relleno desplace a otros; no evita que él sea desplazado. No es una EC2 Capacity Reservation ni garantía de disponibilidad; topología, taints y forma de recursos deben ajustarse a la carga real.

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

## Secuencia de despliegue y límites de validación

1. Mida latencia, rendimiento, cuotas, memoria total y causas de reinicio con carga representativa.
2. Use VPA y observaciones para proponer requests, considerando HPA y concurrencia conjuntamente.
3. Pruebe arranque, picos, fallos y reinicios fuera de producción antes de ajustar limits y margen.
4. Observe SLO, coste, ubicación e interrupción durante un canary; conserve la configuración de reversión.

La validación ejecutó localmente métricas Java/Spring/JMX, JFR/NMT, salud y SIGTERM de Gunicorn/Node, informes runtime Go y configuración de workers Tokio. Los casos PromQL cubrieron scrapes duplicados, varios clústeres, denominadores cero, estado OOM histórico y gauges Pending 0/1. No se desplegó EKS, no se modificaron cuotas cgroup, no se forzó OOM ni se midió rendimiento.

## Referencias oficiales

- [Recursos Kubernetes](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Expulsión por presión del nodo](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)
- [GOMAXPROCS de Go consciente de contenedores](https://go.dev/blog/container-aware-gomaxprocs)
- [Guía GC de Go](https://go.dev/doc/gc-guide)
- [Opciones Java 21](https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html)
- [JEP 474](https://openjdk.org/jeps/474)
- [JEP 490](https://openjdk.org/jeps/490)
- [Propiedades Spring Boot](https://docs.spring.io/spring-boot/appendix/application-properties/index.html)
- [JMX exporter 1.6.0](https://github.com/prometheus/jmx_exporter/releases/tag/1.6.0)
- [Ajustes Gunicorn](https://gunicorn.org/reference/settings/)
- [Historial de cambios Flask](https://flask.palletsprojects.com/en/stable/changes/)
- [CLI Node.js 24](https://nodejs.org/download/release/v24.21.0/docs/api/cli.html)
- [Constructor del runtime Tokio](https://docs.rs/tokio/1.53.1/tokio/runtime/struct.Builder.html)

---

< [Anterior: Stack de observabilidad](./09-observability-stack.md) | [Índice](./README.md) | [Siguiente: Actualizaciones EKS](./11-upgrade-operations.md) >
