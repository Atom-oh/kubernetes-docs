# Optimización de recursos: solicitudes, límites y entornos de ejecución de lenguajes

> **Última actualización**: 16 de octubre de 2026. Ejemplos comprobados con esquemas de Kubernetes 1.36,
> Java 21 / Spring Boot 4.1.1, Python 3.12 / Gunicorn 26.2.0,
> Node.js 24.22, Go 1.27.2 y Rust 1.98 / Tokio 1.53.1.

No dimensione las cargas de trabajo basándose solo en el lenguaje o en un porcentaje fijo. Mida los SLO
de rendimiento y latencia con cargas representativas y durante el arranque, los reinicios, el GC y los fallos.
Ajuste conjuntamente las solicitudes, los límites, las réplicas y la concurrencia del entorno de ejecución.
Los porcentajes y umbrales de ejemplo son puntos de partida para pruebas, no garantías de rendimiento.

## 1. Solicitudes, límites y QoS

| Recurso | Solicitudes | Límites |
|---|---|---|
| CPU | Contabilización para la planificación y peso relativo cuando hay contención | La cuota de CPU de cgroup de Linux puede restringir la ejecución |
| Memoria | Contabilización para la planificación | La presión de asignación puede causar un OOM de cgroup cuando la recuperación no basta |
| Sin especificar | Siguen siendo pertinentes los valores predeterminados de admisión y las políticas de niveles superiores | Puede no haber un límite de contenedor, aunque sí límites de nodo o cgroup antecesor |

Una solicitud no fija físicamente la CPU ni preasigna memoria, y no garantiza el rendimiento de la aplicación.
Si solo se proporciona un límite y ningún otro valor predeterminado de admisión establece la solicitud,
Kubernetes copia el límite en la solicitud. Inspeccione el Pod admitido después de LimitRange y de las demás políticas.

Estos ejemplos usan recursos a nivel de contenedor, no de Pod. Cree primero `resource-demo` y compare
la QoS sin un LimitRange que inyecte valores predeterminados de recursos. Para obtener Guaranteed,
las solicitudes y los límites de CPU y memoria deben ser positivos e iguales, además de cumplir las
condiciones aplicables a los contenedores normales y de inicialización.

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

BestEffort no tiene solicitudes ni límites de CPU/memoria; las demás configuraciones pueden ser Burstable.
Compruebe las reglas específicas de la versión al usar recursos a nivel de Pod o contabilización de recursos
de sidecars y contenedores de inicialización.

La QoS no establece un orden absoluto de expulsión. Ante presión de memoria, kubelet tiene en cuenta si
el uso supera las solicitudes, la prioridad del Pod y el uso relativo a las solicitudes. Los Pods Guaranteed
y los Pods Burstable que se mantienen dentro de sus solicitudes suelen considerarse más tarde, pero un Pod
Guaranteed no siempre es la última víctima. Distinga la expulsión por DiskPressure del OOM causado por el
límite del contenedor. OOMKilled suele ser un motivo de terminación del contenedor, no una fase del Pod.
Se puede matar un proceso individual; si termina PID 1, la política de reinicio determina el comportamiento
del contenedor.

### Cuota de CPU y límites de memoria

cgroup v1 usa `cpu.cfs_quota_us` / `cpu.cfs_period_us`; v2 usa `cpu.max`. Un período de 100 ms es habitual,
pero no universal. Con 500m y un período de 100 ms, todos los hilos comparten un presupuesto agregado de
50 ms de ejecución. La limitación puede afectar tanto a la latencia como al rendimiento. La proporción de
períodos limitados mide cuántos períodos tuvieron limitación, no el tiempo de CPU perdido.

Un límite de memoria no es un límite del heap. Distinga `memory.limit_in_bytes` de cgroup v1 de
`memory.max` de v2. Tenga en cuenta el RSS, las asignaciones nativas, las pilas de hilos, la caché de páginas
y el uso de emptyDir respaldado por memoria. Una sonda de actividad que reinicia la aplicación cuando la
memoria se acerca a un umbral puede ocultar la causa y crear ciclos de reinicio; no es una solución general
para los OOM.

Quitar un límite de CPU puede reducir la limitación por cuota de ese contenedor, pero no elimina la
contención, las cuotas de cgroup antecesoras ni los límites del nodo. Evalúe en conjunto las solicitudes,
la prioridad, el aislamiento, las políticas y los SLO.

### Valores predeterminados y presupuestos de namespaces

LimitRange controla los valores predeterminados de admisión y las restricciones por recurso. ResourceQuota
controla los presupuestos de admisión del namespace para solicitudes, límites y cantidad de objetos.
No miden ni limitan directamente el uso real de CPU ni el costo. Cree el namespace `production` antes de
aplicar estas políticas.

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

Observe las distribuciones, los picos, el costo de arranque y el crecimiento de memoria durante un período
representativo. Las solicitudes P70 y los límites P99 son hipótesis que deben probarse, no valores
predeterminados universales. El GC, la carga de modelos, JIT, la criptografía, los sidecars y el tamaño de
las entradas por lotes varían incluso dentro de un mismo lenguaje. No oculte una fuga aumentando solo los
límites ni clasifique automáticamente como desperdicio los Pods inactivos de reserva o recuperación ante desastres.

Use el [capítulo de escalado](./06-scaling-strategies.md) para instalar las versiones fijadas de VPA y
Goldilocks. Goldilocks crea y muestra VPA para los namespaces y cargas de trabajo seleccionados; instalarlo
no optimiza todo automáticamente. Este VPA observa el Deployment `resource-java` que se muestra a continuación.

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

`Off` solo genera recomendaciones. `target` es una recomendación para la solicitud; los límites inferior
y superior describen el rango de la recomendación. No trate `upperBound` directamente como el límite de
memoria ni `uncappedTarget` como el valor aplicado. `RequestsAndLimits` puede ajustar los límites y
conservar una proporción existente; no copia `upperBound` en los límites.

En VPA 1.8.0, el modo obsoleto `Auto` se comporta como `Recreate`. Compruebe los requisitos previos
de `InPlaceOrRecreate`/`InPlace` y de la compatibilidad de Kubernetes con cambios in-place. `Initial`
sigue modificando las solicitudes de los Pods nuevos y, por tanto, el denominador de utilización de HPA
basada en solicitudes. No evita automáticamente los conflictos con HPA.

Si un Pod mantiene 200 RPS dentro del SLO requerido, 1.000 RPS necesitan cinco Pods en estado estable.
Para mantener ese rendimiento tras perder un Pod, hacen falta al menos seis. Esto no garantiza resistir
la pérdida de toda una AZ. Distinga entre añadir un 20 % de capacidad y dejar sin usar el 20 % de la
capacidad disponible; esto último requiere `ceil(1000 / (200 × 0.8)) = 7`.

## 3. JVM: heap y memoria del contenedor

`MaxRAMPercentage` es una entrada para la configuración automática del heap de la JVM basada en la
memoria detectada. El 75 % no es óptimo en todos los casos y no redimensiona el heap en vivo para seguir
de inmediato los cambios del límite del Pod. También influyen `-Xmx`, `-XX:MaxRAM` y la configuración
automática para heaps pequeños. Metaspace, la caché de código, las pilas, los búferes directos, JNI y los
asignadores consumen memoria fuera del heap. Un 25 % fijo no garantiza que haya suficiente memoria fuera del heap.

La JVM no lee `JAVA_OPTS` automáticamente; el entrypoint de la imagen debe pasarlo al comando. Este
ejemplo usa `JAVA_TOOL_OPTIONS`, que reconoce la JVM, y un comando `java -jar` explícito. El 60 % es
un punto de partida para el perfilado.

El siguiente ejemplo completo de Spring Boot se compiló con Java 21 y Boot 4.1.1. Guarde los archivos
en las rutas del proyecto indicadas.

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

El proyecto mínimo no incluye archivos wrapper; use `mvn package` a menos que añada uno. La imagen
debe contener el JAR compilado en `/app/resource-api.jar` y un entorno de ejecución compatible con
Java 21. La imagen `registry.example.com` que aparece a continuación es un marcador que debe sustituir.
La creación del namespace, la compilación de la imagen y el acceso al registro son requisitos previos
independientes. Las rutas de readiness/liveness corresponden a los endpoints Actuator reales de la aplicación.

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

La ruta de configuración de Prometheus es `management.prometheus.metrics.export`. No exponga
indiscriminadamente las métricas y la información detallada de estado. Solo las métricas que publican
histogramas permiten consultas `_bucket`; promediar percentiles calculados por clientes entre Pods no
produce un percentil global. Un Timer de Micrometer ya proporciona count/sum, así que no hace falta un
Counter duplicado para la misma medición.

HeapDumpOnOutOfMemoryError maneja los OOME de Java de la JVM. El SIGKILL del kernel no puede ejecutar
un volcado de heap ni los hooks de apagado. Los archivos de diagnóstico en emptyDir desaparecen al
eliminar el Pod; gestione las colisiones de nombres y el agotamiento de disco. Los volcados de heap
pueden contener datos sensibles de la aplicación, así que restrinja su acceso y retención.
`ScheduleAnyway` expresa una preferencia, no una distribución estricta entre AZ.

### GC y CPU

| Opción | Qué validar |
|---|---|
| G1 | Punto de partida habitual; los objetivos de pausa no garantizan la latencia máxima |
| ZGC | Comportamiento generacional específico del JDK y presupuesto de CPU/memoria |
| Shenandoah | Disponibilidad en la distribución y versión del JDK seleccionadas |
| Parallel / Serial | Comparar según los requisitos de rendimiento o de cargas con heap pequeño |

Java 21 admite ZGC generacional con `-XX:+UseZGC -XX:+ZGenerational`. El modo generacional pasó
a ser el predeterminado en Java 23; Java 24 eliminó el modo no generacional y dejó obsoleto el indicador
de selección. Distinga la advertencia de obsolescencia de Java 25 de la futura expiración del indicador.
No copie este indicador en Java 17. En los JDK actuales que solo admiten el modo generacional, use
`-XX:+UseZGC` y verifique el arranque en la versión exacta. Las cifras fijas de latencia/rendimiento
del GC requieren pruebas de rendimiento.

`availableProcessors()` no siempre indica la cantidad de hilos de trabajo del GC. Influyen la cuota,
la afinidad, la versión del JDK y la configuración automática del recolector. Añadir hilos del GC puede
agotar antes una cuota pequeña de CPU. Si el arranque es lento, use una startupProbe y mida el
comportamiento de JIT/GC/CPU.

### JMX y JFR

Incluya el JAR del JMX exporter 1.6.0 en la imagen u obtenga el artefacto oficial y verifique su checksum.
La siguiente configuración se probó con MBeans reales de memoria, hilos y GC. JMX y Micrometer usan
nombres de métricas distintos; no los mezcle silenciosamente en los dashboards. GC CollectionTime se
convierte de milisegundos a segundos.

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

Este comando de diagnóstico local se vincula a loopback. Para recopilar desde otro Pod hace falta un
puerto de métricas explícito, un ServiceMonitor y controles de acceso. La JVM no puede arrancar si falta
el JAR del agente. NMT requiere `-XX:NativeMemoryTracking=summary` al arrancar; no contabiliza por
completo el RSS de todas las asignaciones de bibliotecas nativas externas.

La captura de JFR en vivo requiere las herramientas del JDK, permisos apropiados del mismo usuario,
compatibilidad con attach y un destino donde se pueda escribir. Sustituya `PID` por el ID del proceso
Java, en lugar de dar por sentado que es PID 1.

```bash
jcmd PID VM.native_memory summary
jcmd PID JFR.start name=profile settings=profile duration=60s filename=/diagnostics/profile.jfr
jfr summary /diagnostics/profile.jfr
```

Al copiar desde un contenedor, tenga en cuenta cuál es el contenedor seleccionado y si `tar` está
disponible para `kubectl cp`. Copie después de que termine la grabación; que se sustituya el proceso
no garantiza que sobrevivan los archivos de heap o JFR.

## 4. Python: workers y perfilado

Aplicar `2 × CPU + 1` a `multiprocessing.cpu_count()` del host puede sobreasignar la cuota del
contenedor. Pruebe el comportamiento de CPU/E/S, el GIL y las extensiones nativas, el RSS por worker
y la concurrencia de solicitudes. No hay una fórmula universal de workers por CPU. Este ejemplo de
Flask WSGI realmente lee `WEB_CONCURRENCY` y empieza con un worker y dos hilos.

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

Estos endpoints de salud solo comprueban el proceso de ejemplo. Implemente la readiness de las
dependencias de su aplicación. No use el hook eliminado `before_first_request` de Flask. En este
ejemplo mínimo, el socket de control local de Gunicorn 26 está desactivado.

Distinga Flask WSGI de aplicaciones ASGI como FastAPI. Gunicorn 26 también tiene un worker ASGI;
si elige Uvicorn, distinga el módulo obsoleto `uvicorn.workers` del paquete independiente
`uvicorn-worker`. No aplique sin cambios la configuración de gthread a una aplicación ASGI. Evalúe
los beneficios copy-on-write de preload junto con los hilos, conexiones y clientes inicializados antes
del fork. Reciclar workers no corrige la causa de una fuga.

tracemalloc observa las asignaciones de Python que tiene registradas, no todo el uso nativo/RSS.
Lo siguiente es un diagnóstico local explícito, no un endpoint HTTP de depuración expuesto públicamente.

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

## 5. Node.js: old space y memoria del proceso

`--max-old-space-size` se mide en MiB y controla old space de V8. No es un límite del RSS: también
hace falta capacidad para la generación joven y la memoria externa, de Buffer y nativa. Si hay varios
procesos worker, presupueste el heap de cada proceso. Node.js 20 llegó al fin de su vida útil en abril
de 2026, así que los nuevos ejemplos usan la línea compatible Node.js 24.

Este ejemplo de un solo proceso implementa endpoints de salud, observación de memoria y gestión de
SIGTERM. Las llamadas repetidas a `global.gc()` basadas únicamente en un porcentaje no son una
optimización general. La versión probada de Node 24 acepta `--expose-gc` en NODE_OPTIONS; eso no
demuestra que forzar el GC aporte beneficios en producción.

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

`UV_THREADPOOL_SIZE` afecta a las operaciones que usan el pool de hilos de libuv, incluidas la E/S
de archivos, algunas tareas de DNS y la criptografía. No cubre toda la E/S de red. Añadir hilos puede
aumentar la memoria de las pilas y la cantidad de operaciones simultáneas. Establézcalo antes del
arranque y pruébelo con la carga real.

Si usa Node cluster, prefiera `isPrimary` y limite explícitamente la cantidad de workers. No dé por
sentado que `os.cpus().length`, PM2 `instances: max` o `availableParallelism()` sea una fórmula
exacta para todas las cuotas de cgroup. Los ciclos de reinicio necesitan backoff y no deben volver
a crear workers durante el apagado. Combinar réplicas de Pods y de procesos multiplica los workers
y el presupuesto de memoria.

## 6. Go y Rust

### Go

Go 1.25 introdujo en Linux un GOMAXPROCS predeterminado que tiene en cuenta los cgroups. Importan
la versión del lenguaje indicada en `go.mod` y los valores predeterminados de compatibilidad GODEBUG;
use `go 1.25.0` o posterior para obtener estos valores. Este ejemplo se probó con Go 1.27.2.
Establecer GOMAXPROCS explícitamente en el entorno o llamar a `runtime.GOMAXPROCS(n)` con un valor
positivo desactiva las actualizaciones automáticas. Consultar el valor con `runtime.GOMAXPROCS(0)`
no lo cambia.

El runtime actual redondea la cuota hacia arriba y también tiene en cuenta las CPU lógicas y la afinidad.
En general, no elige menos de dos cuando la cantidad de CPU lógicas/afinidad permite dos; por eso es
incorrecto afirmar que `500m` siempre significa 1. No equipare el comportamiento de versión/redondeo
de automaxprocs con los valores predeterminados integrados de Go ni habilite ambos a ciegas. Las
solicitudes de CPU no son cuotas.

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

GOMEMLIMIT es un límite flexible para la memoria administrada por el runtime de Go, aproximadamente
`MemStats.Sys - HeapReleased`. No es un límite del RSS de todo el proceso que incluya cgo, mmap o
bibliotecas externas. El runtime puede superarlo para limitar la sobrecarga del GC. Establecerlo en
el 80–90 % de la memoria del contenedor no garantiza evitar OOM; si queda muy por debajo del heap
activo puede provocar un GC excesivo. Este programa solo muestra los ajustes y no lee ni modifica cgroups.

### Rust

La ausencia de GC no vuelve deterministas el uso de memoria ni la latencia. Observe el comportamiento
del asignador, la fragmentación, el trabajo simultáneo, los búferes, el trabajo bloqueante y la
planificación del sistema operativo. Evalúe cambios del asignador, como jemalloc, a partir de perfiles
y de la compatibilidad de la plataforma; no suponga que mejorará el rendimiento en todos los casos.

Este pequeño programa de Tokio valida los ajustes del runtime; no es un servidor HTTP. Un valor
explícito de `worker_threads()` tiene prioridad sobre el entorno, por eso el ejemplo lo omite. La
cantidad de hilos de trabajo no limita `spawn_blocking` ni los hilos de bibliotecas externas.

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

En un proyecto nuevo sin lockfile, ejecute `cargo build`, revise el lockfile y confirme sus cambios.
Para compilaciones reproducibles posteriores, puede usar `--locked`. Use colas y concurrencia acotadas
en lugar de crear tareas asíncronas de uso intensivo de CPU sin límite.

No publique rankings de consumo de memoria, arranque o velocidad por lenguaje sin benchmarks comparables.

## 7. PromQL y alertas

Estas reglas suponen las series agregadas `job="kubelet"`, `metrics_path="/metrics/cadvisor"` y
`cpu="total"` de kube-prometheus-stack, además de kube-state-metrics. Adapte la agregación si recopila
por CPU y ajuste los selectores al contrato real de etiquetas.

El ejemplo usa la agregación máxima por contenedor para evitar sumar observaciones de scrape duplicadas.
Inspeccione los intervalos de reinicio en los que coinciden varios ID de runtime con el mismo nombre de
Pod/contenedor; estas observaciones no son datos precisos para facturar CPU. Varios clústeres requieren
una etiqueta real `cluster` en la ruta de recopilación/escritura remota; PromQL no inventa una identidad
que falta.

Las reglas ordenadas alinean los denominadores de solicitud/límite y excluyen el cero. El working set
no predice con exactitud los OOM; investigue la caché de páginas y el comportamiento de recuperación.
El último motivo de terminación es un gauge, por lo que `increase(reason)` no cuenta los OOM. La alerta
combina un reinicio reciente con el último motivo de OOM registrado; no cuenta todos los OOM del intervalo.

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

Haga coincidir `release: prometheus` y el namespace `observability` con el selector de reglas de
Prometheus. Los umbrales son ejemplos. Una proporción alta de períodos limitados no indica
automáticamente que deba aumentar el límite; correlacione la latencia, el rendimiento, la concurrencia
y la contención del nodo.

`cluster:pending_pods:count` suma el gauge de fase 0/1. `count(kube_pod_status_phase{phase="Pending"})`
también cuenta las muestras con valor cero. El estado Pending puede incluir Pods ya planificados que
esperan imágenes o almacenamiento, por lo que no equivale a falta de recursos. `node:pods:count` ya
es una cuenta por nodo; no la divida por la cantidad de nodos del clúster.

Para agregar por Deployment, use la relación de ownership Pod→ReplicaSet→Deployment de kube-state-metrics
o reglas de grabación validadas, en vez de adivinar el ownership con expresiones regulares sobre los
nombres de Pods. Al dimensionar a largo plazo, tenga en cuenta los despliegues graduales, los días
festivos, la capacidad de reserva y los SLO; observar un uso bajo no es una política automática de expulsión.

### Consultas y dashboards de JVM

Estas consultas apuntan a JVM que usan la configuración de Micrometer anterior. Distinga los procesos
mediante la etiqueta instance de Prometheus y compruebe los nombres de métricas en scrapes reales.

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

La tasa de `jvm_gc_pause_seconds_sum` mide segundos de pausa observados por segundo de tiempo real.
Dividirla por la CPU del proceso no produce un porcentaje válido de CPU de GC ni incluye todo el trabajo
de GC concurrente. `jvm_classes_loaded_classes` es un gauge de las clases cargadas actualmente;
el contador acumulativo de Micrometer que se probó es `jvm_classes_loaded_count_classes_total`.
Compruebe la exposición real al cambiar las versiones del JDK o las bibliotecas.

Use los UID explícitos de origen de datos y el aprovisionamiento de dashboards del [capítulo anterior](./09-observability-stack.md).
Muestre las proporciones con percentunit o multiplíquelas por 100 y use percent. No trate los gauges
de utilización sin procesar como buckets de histogramas en un heatmap. No describa un fragmento
parcial de JSON de panel como un dashboard completo que se pueda importar.

## 8. EKS Auto Mode y capacidad de reserva

Tenga en cuenta las solicitudes, el valor real de Node allocatable, la sobrecarga de DaemonSet/sistema,
del Pod, los puertos, los volúmenes, la topología y los taints. Una instancia de 4 vCPU no necesariamente
ofrece cuatro CPU asignables a las solicitudes de las aplicaciones. Las instancias más grandes no siempre
son más eficientes, ni las pequeñas siempre cuestan menos. Evalúe el impacto de fallos, la disponibilidad,
el precio y la fragmentación.

Los NodePools de Auto Mode usan `karpenter.sh/v1`; el grupo de NodeClass es `eks.amazonaws.com`.
Este ejemplo hace referencia a un NodeClass `default` de Auto Mode ya existente. Valide por separado
el NodeClass, las subredes, el rol IAM y la disponibilidad regional de las instancias.

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

La consolidación tiene en cuenta las solicitudes, la viabilidad de la planificación, el precio y las
restricciones de interrupción; que el CPU observado esté por debajo del 30 % no garantiza que se
consolide un nodo. Los PDB no impiden todas las terminaciones ni garantizan que una terminación forzada
no cause interrupciones. Si la solicitud no cambia, el scheduler ordinario no reserva automáticamente
el exceso indicado por un límite sobredimensionado.

Los Pods de relleno pueden favorecer la existencia de capacidad libre para tareas de mayor prioridad.
La prioridad -1 está por debajo de la predeterminada 0, pero no es el valor más bajo posible.
`preemptionPolicy: Never` impide que el Pod de relleno expulse a otros; no impide que lo expulsen a él.
Esto no es una EC2 Capacity Reservation ni una garantía de disponibilidad; la topología, los taints y
la forma de los recursos deben ajustarse a la carga real.

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

1. Mida la latencia, el rendimiento, el comportamiento de las cuotas, la memoria total y las causas de reinicio con carga representativa.
2. Use VPA y las observaciones para proponer solicitudes y tenga en cuenta conjuntamente HPA y la concurrencia del runtime.
3. Pruebe fuera de producción el arranque, la carga máxima, los fallos y los reinicios antes de ajustar los límites y el margen.
4. Durante un canary, observe los SLO, el costo, la ubicación y las interrupciones; conserve la configuración necesaria para revertir.

La validación ejecutó localmente métricas Java/Spring/JMX y JFR/NMT, el comportamiento de salud y
SIGTERM de Gunicorn/Node, informes del runtime de Go y la configuración de hilos de Tokio. Los casos
de cálculo PromQL cubrieron scrapes duplicados, varios clústeres, denominadores cero, estado OOM
histórico y gauges Pending 0/1. No se desplegó EKS, no se modificaron las cuotas de cgroup, no se forzó
un OOM ni se hicieron benchmarks de rendimiento.

## Referencias oficiales

- [Recursos de Kubernetes](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Expulsión por presión del nodo](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)
- [GOMAXPROCS de Go adaptado a contenedores](https://go.dev/blog/container-aware-gomaxprocs)
- [Guía del GC de Go](https://go.dev/doc/gc-guide)
- [Opciones de Java 21](https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html)
- [JEP 474](https://openjdk.org/jeps/474)
- [JEP 490](https://openjdk.org/jeps/490)
- [Propiedades de Spring Boot](https://docs.spring.io/spring-boot/appendix/application-properties/index.html)
- [JMX exporter 1.6.0](https://github.com/prometheus/jmx_exporter/releases/tag/1.6.0)
- [Configuración de Gunicorn](https://gunicorn.org/reference/settings/)
- [Historial de cambios de Flask](https://flask.palletsprojects.com/en/stable/changes/)
- [CLI de Node.js 24](https://nodejs.org/download/release/v24.22.0/docs/api/cli.html)
- [Constructor de runtime de Tokio](https://docs.rs/tokio/1.53.1/tokio/runtime/struct.Builder.html)

---

< [Anterior: Pila de observabilidad](./09-observability-stack.md) | [Contenido](./README.md) | [Siguiente: Actualizaciones de EKS](./11-upgrade-operations.md) >
