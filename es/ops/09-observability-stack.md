# Configuración y operación de la plataforma de observabilidad

> **Última actualización**: 11 de septiembre de 2026: Loki 3.7.7, Tempo 3.0.3, Alloy 1.19.2,
> OpenTelemetry Collector Contrib 0.160.0, kube-prometheus-stack 90.1.1.

Este capítulo configura recopilación, almacenamiento, permisos, retención y navegación entre señales.
Use los [ejemplos completos de instrumentación Go/Python y logs JSON de Java](./08-observability-analysis.md)
del capítulo anterior. Instalar Grafana no correlaciona por sí solo las tres señales.

## Alcance y requisitos

| Señal | Recopilación | Almacenamiento y consultas |
|---|---|---|
| Logs | JSON stdout de la aplicación → fuente API Kubernetes de Alloy | Loki → Grafana |
| Trazas | OTLP de aplicación → Collector → Tempo | Tempo → Grafana |
| Métricas | Scrape Prometheus; remote write opcional de métricas generadas por Tempo | Prometheus; AMP opcional |

Se usa `observability`. Prepare ese namespace, los CRD de Prometheus Operator y una StorageClass
`gp3` operativa. Auto Mode y EBS CSI ordinario usan provisionadores diferentes; el mismo nombre
no demuestra compatibilidad. Buckets S3 y roles IRSA son requisitos separados. Sustituya cuentas,
roles, buckets y workspaces. Separe buckets por finalidad y bloquee acceso público. Limite roles
Loki/Tempo al listado y lectura/escritura/eliminación de objetos necesarios; incluya los permisos
de la clave KMS elegida si usa SSE-KMS.

Estos ajustes son un punto de partida de configuración. El HTTP interno sin autenticación, la conexión
Kafka, los tamaños de recursos y la retención no son valores predeterminados universales de producción.
Valide el acceso de red, TLS/autenticación, capacidad y recuperación para su entorno. `ClusterIP` no
proporciona autenticación.

Las versiones de charts y aplicaciones difieren. Loki/Tempo usan el repositorio actual
`grafana-community`. Dar values distribuidos al antiguo chart monolítico `grafana/tempo`
no lo convierte en un despliegue distribuido.

```bash
helm repo add grafana-community https://grafana-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
```

## Loki: modos y almacenamiento S3

Loki indexa etiquetas de streams y guarda contenido en chunks. Buscar contenido todavía lee datos
de los streams seleccionados; etiquetas, intervalos y cachés de chunks/índices afectan al coste.
Las relaciones de compresión y umbrales diarios fijos requieren mediciones de la carga.

| Modo | Propósito y límites |
|---|---|
| Monolithic | Un proceso; HA exige almacenamiento compartido, replicación y rutas |
| SimpleScalable | Destinos read/write/backend separados; obsoleto, eliminación prevista en Loki 4.0 |
| Distributed | Componentes independientes; operación adicional de red, anillo, consultas y almacenamiento |

El ejemplo distribuido usa tres ingesters y un compactor. `zoneAwareReplication: false` implica
que tres réplicas no garantizan aislamiento entre AZ. Valide ubicación, cuórum, PDB y rollouts
conjuntamente. Las cachés están deshabilitadas para reducir la validación inicial; dimensione
las de producción mediante pruebas de carga.

La fecha de esquema corresponde a un almacén nuevo. En uno existente, conserve entradas históricas
y siga el procedimiento para añadir una futura. `auth_enabled: false` selecciona el único tenant
`fake`. Activar multitenancy no autentica usuarios; un proxy autenticador debe validar y fijar las cabeceras de tenant.

```yaml
# loki-values.yaml
deploymentMode: Distributed
loki:
  image:
    tag: 3.7.7
  auth_enabled: false
  commonConfig:
    replication_factor: 3
  schemaConfig:
    configs:
    - from: '2026-09-01'
      store: tsdb
      object_store: s3
      schema: v13
      index:
        prefix: loki_index_
        period: 24h
  storage:
    type: s3
    bucketNames:
      chunks: REPLACE_WITH_UNIQUE_LOKI_CHUNKS_BUCKET
      ruler: REPLACE_WITH_UNIQUE_LOKI_RULER_BUCKET
    s3:
      region: ap-northeast-2
  ingester:
    chunk_encoding: snappy
  compactor:
    retention_enabled: true
    delete_request_store: s3
    retention_delete_delay: 2h
  limits_config:
    retention_period: 720h
    allow_structured_metadata: true
  analytics:
    reporting_enabled: false
serviceAccount:
  create: true
  name: loki
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/docs-loki-s3
singleBinary:
  replicas: 0
read:
  replicas: 0
write:
  replicas: 0
backend:
  replicas: 0
ingester:
  replicas: 3
  zoneAwareReplication:
    enabled: false
  persistence:
    enabled: true
    claims:
    - name: data
      accessModes: &id001
      - ReadWriteOnce
      size: 20Gi
      storageClass: gp3
distributor:
  replicas: 2
querier:
  replicas: 2
queryFrontend:
  replicas: 2
queryScheduler:
  replicas: 2
indexGateway:
  replicas: 2
compactor:
  replicas: 1
  persistence:
    enabled: true
    claims:
    - name: data
      accessModes: *id001
      size: 20Gi
      storageClass: gp3
gateway:
  enabled: true
  replicas: 2
chunksCache:
  enabled: false
resultsCache:
  enabled: false
sidecar:
  rules:
    enabled: false
```

```bash
helm template loki grafana-community/loki --version 18.12.2   --namespace observability -f loki-values.yaml > loki-rendered.yaml
helm upgrade --install loki grafana-community/loki --version 18.12.2   --namespace observability -f loki-values.yaml
```

En chart 18.12.2, configure los PVC de ingester/compactor mediante `persistence.claims`.
Incluya `accessModes` al sustituir la lista. Compruebe `volumeClaimTemplates` y binding real,
no solo la salida de Helm. El Service gateway usa **80**; el proceso Loki usa HTTP **3100**.

### Retención

Configure conjuntamente TSDB v13 con índice de 24 horas, `compactor.retention_enabled`,
`delete_request_store` y `limits_config.retention_period`. La eliminación es asíncrona y respeta
`retention_delete_delay`. Conserve marcadores y estado del compactor al reiniciar. Cambiar
retención no reorganiza necesariamente datos existentes de forma retroactiva.

Las anulaciones por inquilino pertenecen a `loki.runtimeConfig.overrides` del chart.
El ejemplo de un solo inquilino utiliza `fake`. El siguiente fragmento sustituye el valor
predeterminado de 30 días por siete días; aplíquelo solo después de comprobar sus requisitos de retención.

```yaml
loki:
  runtimeConfig:
    overrides:
      fake:
        retention_period: 168h
```

La caducidad de objetos de todo el bucket puede dañar índices, solicitudes de borrado y reglas.
Si necesita una protección adicional de ciclo de vida, limítela a prefijos de chunks y fije una
caducidad mayor que retención más demora de borrado. Evalúe versionado/backup y requisitos de
eliminación por separado; habilitar versionado no prueba recuperación.

## Recopilación de logs y etiquetas con Alloy

Promtail llegó al fin de vida el 2026-03-02. Los ejemplos nuevos usan Alloy.
Esta configuración lee Pods `app=correlation-api` de `observability` del
[capítulo anterior](./08-observability-analysis.md) mediante la API de logs Kubernetes.
No sigue archivos de nodos ni necesita hostPath o `stage.cri`.

Una réplica Deployment con `Recreate` evita duplicación estable y durante rollouts.
No es HA y las actualizaciones pueden interrumpir la recopilación. Para escalar, configure clustering
Alloy y soporte de la fuente, o limite destinos por nodo. Un DaemonSet donde cada Pod descubre
todos los Pods de aplicaciones duplica la recopilación.

```yaml
# alloy-rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: alloy-logs
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: alloy-logs
  namespace: observability
rules:
  - apiGroups: [""]
    resources: [pods]
    verbs: [get, list, watch]
  - apiGroups: [""]
    resources: [pods/log]
    verbs: [get]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: alloy-logs
  namespace: observability
subjects:
  - kind: ServiceAccount
    name: alloy-logs
    namespace: observability
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: alloy-logs
```

```alloy
// logs.alloy
// Kubernetes API log source: configure its ServiceAccount permissions first.
discovery.kubernetes "application" {
  role = "pod"
  namespaces {
    names = ["observability"]
  }
  selectors {
    role  = "pod"
    label = "app=correlation-api"
  }
}

discovery.relabel "application_logs" {
  targets = discovery.kubernetes.application.targets
  rule {
    source_labels = ["__meta_kubernetes_namespace"]
    target_label  = "namespace"
  }
  rule {
    source_labels = ["__meta_kubernetes_pod_label_app"]
    target_label  = "service_name"
  }
  rule {
    source_labels = ["__meta_kubernetes_pod_container_name"]
    target_label  = "container"
  }
}

loki.source.kubernetes "application" {
  targets    = discovery.relabel.application_logs.output
  forward_to = [loki.process.application.receiver]
}

loki.process "application" {
  stage.json {
    expressions = {
      level = "level",
    }
  }
  stage.labels {
    values = {
      level = "",
    }
  }
  // Keep the complete JSON body, including trace_id/span_id. They are not
  // indexed stream labels and remain available for parsing/correlation.
  forward_to = [loki.write.backend.receiver]
}

loki.write "backend" {
  endpoint {
    url = "http://loki-gateway.observability.svc:80/loki/api/v1/push"
  }
}
```

Guarde los values como `alloy-values.yaml` e inyecte el archivo anterior con `--set-file`.
Así no duplica la configuración Alloy dentro de una cadena YAML.

```yaml
controller:
  type: deployment
  replicas: 1
  updateStrategy:
    type: Recreate
alloy:
  enableReporting: false
  configMap:
    content: ''
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      memory: 512Mi
rbac:
  create: false
serviceAccount:
  create: false
  name: alloy-logs
crds:
  create: false
```

```bash
kubectl apply -f alloy-rbac.yaml
helm upgrade --install alloy grafana/alloy --version 1.12.1   --namespace observability -f alloy-values.yaml   --set-file alloy.configMap.content=logs.alloy
```

Prefiera etiquetas acotadas como `namespace`, `service_name` y `container`.
Mantenga `trace_id` y `request_id` en JSON o metadatos estructurados. Los nombres Pod no están
prohibidos universalmente, pero su duración y cambios afectan a streams. Importa el producto de
combinaciones, no un número fijo de etiquetas. El ejemplo conserva la línea JSON completa e indexa
`level`; normalice valores ilimitados y elimine datos personales en aplicación o recopilación.

### LogQL y alertas

Excluya errores JSON y campos numéricos inválidos antes de agregar. La latencia siguiente está en
milisegundos. `rate` cuenta líneas por segundo; `bytes_rate`, bytes por segundo.

```logql
{service_name="correlation-api"} | json | __error__="" | level="ERROR"
```

```logql
sum(rate({service_name="correlation-api"}[5m]))
```

```logql
sum(bytes_rate({service_name="correlation-api"}[5m]))
```

```logql
avg_over_time({service_name="correlation-api"} | json | latency_ms >= 0 | __error__="" | unwrap latency_ms | __error__="" [5m])
```

```logql
quantile_over_time(0.95, {service_name="correlation-api"} | json | latency_ms >= 0 | __error__="" | unwrap latency_ms | __error__="" [5m])
```

Loki Ruler evalúa reglas LogQL y envía alertas a Alertmanager. Introducir LogQL en un
PrometheusRule o añadir una etiqueta ConfigMap arbitraria `loki_rule` no carga reglas.
La configuración base anterior tiene cero réplicas de ruler. Configure un despliegue de ruler, su almacén/API
de reglas o montajes, el intervalo de evaluación y el endpoint de Alertmanager antes de probar la evaluación.

Texto genérico `"error"` o `"unauthorized"` no demuestra caída o ataque. Para CrashLoopBackOff
consulte el estado de contenedores en kube-state-metrics, no solo logs de aplicación. Las proporciones
requieren ámbitos coincidentes, manejo de errores de análisis, cero tráfico y series de error ausentes.
Conéctelas con las [pruebas de rutas e inhibición de alertas](./07-observability-alerts.md).

## Tempo 3: operación monolítica y distribuida

Tempo permite buscar por trace ID y atributos TraceQL. metrics-generator deriva métricas de
trazas seleccionadas; no es el interruptor que habilita búsquedas.

| Componente | Función distribuida en Tempo 3 |
|---|---|
| Distributor | Escribe spans entrantes en Kafka |
| Block-builder | Consume Kafka y crea bloques en objetos |
| Live-store | Atiende consultas de datos recientes |
| Backend-scheduler / backend-worker | Mantenimiento, compactación y retención de bloques |
| Query-frontend / querier | Consulta datos recientes y objetos |

Se eliminaron ingester/compactor 2.x y el modo scalable single binary. El modo monolítico de un
proceso no necesita Kafka. Aumentar `replicas` no es una conversión soportada a HA distribuida.

### Laboratorio de instancia única

`tempo-lab-values.yaml` usa PVC local sin Kafka. Un fallo de proceso/PVC puede interrumpir
servicio; no mezcle estos values con los distribuidos S3. En chart 3.0.0, desactive protocolos Jaeger
individuales con `null`; borrar el padre rompe el render. El Service puede conservar puertos
heredados; restrinja acceso según receivers y políticas reales.

```yaml
# tempo-lab-values.yaml
replicas: 1
tempo:
  tag: 3.0.3
  reportingEnabled: false
  retention: 336h
  receivers:
    jaeger:
      protocols:
        grpc: null
        thrift_binary: null
        thrift_compact: null
        thrift_http: null
    otlp:
      protocols:
        grpc:
          endpoint: 0.0.0.0:4317
        http:
          endpoint: 0.0.0.0:4318
  resources:
    requests:
      cpu: 250m
      memory: 512Mi
    limits:
      memory: 2Gi
  metricsGenerator:
    enabled: true
    storage:
      path: /var/tempo/metrics
      remote_write:
      - url: http://prometheus-kube-prometheus-prometheus.observability.svc:9090/api/v1/write
        send_exemplars: true
  overrides:
    defaults:
      metrics_generator:
        processors:
        - service-graphs
        - span-metrics
persistence:
  enabled: true
  storageClassName: gp3
  size: 20Gi
```

```bash
helm upgrade --install tempo grafana-community/tempo --version 3.0.0   --namespace observability -f tempo-lab-values.yaml
```

### Configuración distribuida para revisión

Este archivo es una alternativa al chart de instancia única, no una superposición para él.
Kafka y S3 ya deben existir. El ejemplo utiliza un endpoint Kafka interno en un entorno
de validación aislado. Confirme primero sus requisitos de TLS/autenticación de Kafka en producción frente
a la compatibilidad del cliente de Tempo 3.0.3. No se admiten campos arbitrarios `tls` ni MSK IAM bajo
el `ingest.kafka` de esta versión. La compatibilidad con usuario/contraseña SASL no implica cifrado de transporte.

Con `partitions_per_instance: 1`, tres particiones requieren tres block-builders; el ejemplo también
usa tres live-stores. Cambiar `auto_create_topic_default_partitions` no redimensiona un tema
existente. Sin creación automática, configure particiones, replicación, ISR mínimo, retención y
capacidad aparte. Añadir `persistence` no soportado no crea PVC para esos componentes.
Pruebe recuperación con el almacenamiento real del chart y la ventana de replay Kafka.

```yaml
# tempo-distributed-values.yaml
reportingEnabled: false
multitenancyEnabled: false
tempo:
  image:
    tag: 3.0.3
ingest:
  kafka:
    address: kafka.kafka.svc.cluster.local:9092
    topic: tempo-traces
    auto_create_topic_enabled: false
    auto_create_topic_default_partitions: 3
blockBuilder:
  replicas: 3
liveStore:
  replicas: 3
backendScheduler:
  enabled: true
  config:
    provider:
      compaction:
        compaction:
          block_retention: 336h
  persistence:
    enabled: true
    size: 20Gi
    storageClass: gp3
backendWorker:
  replicas: 2
  podDisruptionBudget:
    enabled: true
distributor:
  replicas: 2
querier:
  replicas: 2
queryFrontend:
  replicas: 2
traces:
  otlp:
    grpc:
      enabled: true
    http:
      enabled: true
storage:
  trace:
    backend: s3
    s3:
      bucket: REPLACE_WITH_UNIQUE_TEMPO_BUCKET
      endpoint: s3.ap-northeast-2.amazonaws.com
      region: ap-northeast-2
serviceAccount:
  create: true
  name: tempo
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/docs-tempo-s3
metricsGenerator:
  enabled: true
  kind: StatefulSet
  persistence:
    enabled: true
    storageClass: gp3
    size: 20Gi
  config:
    storage:
      remote_write:
      - url: http://prometheus-kube-prometheus-prometheus.observability.svc:9090/api/v1/write
        send_exemplars: true
overrides:
  defaults:
    metrics_generator:
      processors:
      - service-graphs
      - span-metrics
gateway:
  enabled: true
```

```bash
helm template tempo grafana-community/tempo-distributed --version 3.5.1   --namespace observability -f tempo-distributed-values.yaml > tempo-rendered.yaml
```

`backendWorker.podDisruptionBudget.enabled` es explícito para evitar un default ausente del
PDB 3.5.1. El render no prueba Kafka, permisos S3, scheduling ni escritura/consulta completas.
La ingesta usa `tempo-distributor:4318` y las consultas `tempo-query-frontend:3200`;
actualice las URL del Collector y Grafana del laboratorio.

### Migración de 2.x a 3.x

En monolítico, revise `tempo-cli migrate config --mode=monolithic`. En distribuido,
despliegue en paralelo, valide y migre tráfico. Retire `ingester`, `ingester_client`, `compactor`,
`metrics_generator_client` y `local_blocks`. Los datos históricos necesitan bloques vParquet4 o posteriores.

No active dos sistemas de compactación sobre almacenamiento compartido. Establezca
`compaction_disabled` en defaults 3.x y cada tenant, y retírelo tras detener compactors 2.x.
Los overrides no heredan simplemente los campos omitidos. Verifique trace ID antiguos y nuevos
antes del cambio. Las métricas TraceQL tienen restricciones como cobertura de bloques RF1;
disponer de trazas históricas no implica la misma cobertura de métricas históricas.

## Collector y muestreo

La configuración valida tail sampling en un Collector. Las aplicaciones deben definir `service.name`.
No añade metadatos Kubernetes automáticamente: k8sattributes necesita asociación de Pods y RBAC
separados. Los eventos Kubernetes son logs; `k8s_events` no es receiver de trazas.

La eliminación de atributos sensibles ocurre antes del buffer tail y solo cubre claves indicadas,
no todo log/evento/atributo sensible. Hashear `db.statement` no garantiza privacidad ni protección de secretos.

```yaml
# collector.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 768
    spike_limit_mib: 128
  attributes/remove-secrets:
    actions:
      - key: http.request.header.authorization
        action: delete
      - key: db.statement
        action: delete
      - key: db.query.text
        action: delete
  tail_sampling:
    decision_wait: 30s
    num_traces: 20000
    expected_new_traces_per_sec: 500
    policies:
      - name: errors
        type: status_code
        status_code:
          status_codes: [ERROR]
      - name: slow
        type: latency
        latency:
          threshold_ms: 2000
      - name: baseline
        type: probabilistic
        probabilistic:
          sampling_percentage: 10
  batch:
    send_batch_size: 512
    send_batch_max_size: 1024
    timeout: 1s
exporters:
  otlphttp/tempo:
    endpoint: http://tempo.observability.svc:4318
    retry_on_failure:
      enabled: true
    sending_queue:
      enabled: true
      queue_size: 1000
extensions:
  health_check:
    endpoint: 0.0.0.0:13133
service:
  extensions: [health_check]
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, attributes/remove-secrets, tail_sampling, batch]
      exporters: [otlphttp/tempo]
  telemetry:
    metrics:
      readers:
        - pull:
            exporter:
              prometheus:
                host: 0.0.0.0
                port: 8888
```

```yaml
# collector-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-collector
  namespace: observability
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: otel-collector
  template:
    metadata:
      labels:
        app: otel-collector
    spec:
      automountServiceAccountToken: false
      containers:
        - name: collector
          image: otel/opentelemetry-collector-contrib:0.160.0
          args: ["--config=/etc/otel/collector.yaml"]
          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              memory: 1Gi
          ports:
            - {name: otlp-grpc, containerPort: 4317}
            - {name: otlp-http, containerPort: 4318}
            - {name: metrics, containerPort: 8888}
            - {name: health, containerPort: 13133}
          readinessProbe:
            httpGet:
              path: /
              port: health
          livenessProbe:
            httpGet:
              path: /
              port: health
          volumeMounts:
            - {name: config, mountPath: /etc/otel, readOnly: true}
      volumes:
        - name: config
          configMap:
            name: otel-collector
---
apiVersion: v1
kind: Service
metadata:
  name: otel-collector
  namespace: observability
spec:
  selector:
    app: otel-collector
  ports:
    - {name: otlp-grpc, port: 4317, targetPort: otlp-grpc}
    - {name: otlp-http, port: 4318, targetPort: otlp-http}
    - {name: metrics, port: 8888, targetPort: metrics}
```

```bash
kubectl create configmap otel-collector --namespace observability   --from-file=collector.yaml --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f collector-deployment.yaml
```

Collector Contrib 0.160.0 usa `service.telemetry.metrics.readers` para métricas internas.
No conserve `metrics.address`, el procesador independiente inexistente `rate_limiting` ni el
exportador eliminado `loki`. Los manifiestos conectan ConfigMap, Service y puertos.
El laboratorio usa `Recreate`; actualizar puede perder trazas y colas en memoria.

| Ajuste | Significado |
|---|---|
| Muestreo head | Decide al inicio; no conoce aún error/latencia final |
| Muestreo tail | Decide con spans recibidos durante `decision_wait`; no garantiza integridad |
| Políticas error/latencia/base | Aquí se combinan con OR; una política de tasa aparte no limita globalmente |
| `spans_per_second` | Spans por segundo, no trazas; no es un procesador independiente |
| `num_traces` | Capacidad del buffer pendiente; desbordamiento, retrasos y reinicios pueden perder spans |
| `send_batch_size` | Disparador de envío; `send_batch_max_size` es el máximo |

Varios tail samplers necesitan rutas por trace ID para reunir todos los spans. Un Service aleatorio
puede dividir trazas. Tail no recupera spans descartados por head. Límites de cola, spans tardíos y
fallos de recepción impiden garantizar conservar todos los errores. `UNSET` no es error; incluirlo
puede retener muchos spans normales. Grafos y métricas generadas dependen del muestreo;
use métricas instrumentadas aparte para medir toda la población de solicitudes.

## TraceQL, grafos y correlación con logs

Estas son consultas de búsqueda de trazas individuales. `span:duration` mide un span, no toda la traza.
Los atributos HTTP dependen de la versión de las convenciones semánticas del SDK: el ejemplo Go probado
del capítulo anterior utiliza `http.response.status_code`, mientras que la instrumentación predeterminada
de Python utiliza `http.status_code`.

```traceql
{ resource.service.name = "correlation-api" && span:status = error }
```

```traceql
{ resource.service.name = "correlation-api" && span:duration > 2s }
```

```traceql
{ resource.service.name = "api-gateway" } >> { resource.service.name = "order-service" }
```

```traceql
{ resource.service.name = "correlation-api" } | by(span:status) | count() > 1
```

`>>` significa descendiente y `>` hijo directo. `| by(...) | count()` agrega conjuntos de spans.
Funciones de métricas TraceQL como `rate()` devuelven series temporales, no búsquedas individuales.
Para un ID conocido use el modo trace-ID de Grafana o la API Tempo; no use un atributo intrínseco
inválido y un ID incompleto como `{ trace:id = "abc123" }`.

Los ejemplos conectan service-graphs/span-metrics en configuración y overrides y envían resultados
al receiver remote-write de Prometheus. Los grafos necesitan SpanKind client/server adecuados y
nombres coherentes. `http.target` bruto, URL completas e ID de usuario pueden inflar cardinalidad.

Reutilice los [ejemplos probados Java MDC/Logback y Go/Python de trazas/exemplars](./08-observability-analysis.md).
Puede existir contexto válido no muestreado cuando `is_recording()` es false. No descarte logs
ordinarios por falta de span ni borre valores MDC ajenos con `MDC.clear()`.

## Prometheus y Grafana

Estos values activan remote-write para métricas Tempo y almacenamiento de exemplars.
Restrinja el receiver a remitentes fiables como Tempo. Las métricas de aplicación aún necesitan
scrape/ServiceMonitor y el contrato de métricas/etiquetas de `correlation-api` del capítulo anterior.

Grafana usa UID explícitos `prometheus`, `loki`, `tempo`, `tracesToLogsV2`, regex de trace ID de
32 caracteres minúsculos tolerante a espacios y escape de `$` en provisioning. El destino de
`serviceMap` debe contener realmente métricas generadas de grafos.

```yaml
# prometheus-values.yaml
prometheus:
  prometheusSpec:
    enableFeatures:
    - exemplar-storage
    exemplars:
      maxSize: 100000
    enableRemoteWriteReceiver: true
    retention: 7d
    walCompression: true
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: gp3
          accessModes:
          - ReadWriteOnce
          resources:
            requests:
              storage: 50Gi
grafana:
  sidecar:
    dashboards:
      enabled: true
      label: grafana_dashboard
      labelValue: '1'
      searchNamespace: observability
    datasources:
      enabled: true
      defaultDatasourceEnabled: false
      alertmanager:
        enabled: false
  additionalDataSources:
  - name: Prometheus
    uid: prometheus
    type: prometheus
    access: proxy
    url: http://prometheus-kube-prometheus-prometheus.observability.svc:9090
    jsonData:
      httpMethod: POST
      exemplarTraceIdDestinations:
      - name: trace_id
        datasourceUid: tempo
        urlDisplayLabel: View trace
    isDefault: true
  - name: Loki
    uid: loki
    type: loki
    access: proxy
    url: http://loki-gateway.observability.svc:80
    jsonData:
      derivedFields:
      - name: TraceID
        matcherRegex: '"trace_id"\s*:\s*"([0-9a-f]{32})"'
        datasourceUid: tempo
        url: $${__value.raw}
        urlDisplayLabel: View trace
  - name: Tempo
    uid: tempo
    type: tempo
    access: proxy
    url: http://tempo.observability.svc:3200
    jsonData:
      tracesToLogsV2:
        datasourceUid: loki
        spanStartTimeShift: -5m
        spanEndTimeShift: 5m
        tags:
        - key: service.name
          value: service_name
        filterByTraceID: true
        filterBySpanID: false
        customQuery: false
      tracesToMetrics:
        datasourceUid: prometheus
        spanStartTimeShift: -5m
        spanEndTimeShift: 5m
        tags:
        - key: service.name
          value: service
        queries:
        - name: Request rate
          query: sum(rate(http_requests_total{$$__tags}[5m]))
      serviceMap:
        datasourceUid: prometheus
```

```bash
helm upgrade --install prometheus prometheus-community/kube-prometheus-stack   --version 90.1.1 --namespace observability -f prometheus-values.yaml
```

Los exemplars necesitan asociación trace/span, exposición OpenMetrics, soporte de almacenamiento
Prometheus y mapeo UID Grafana. HTTP/2 o histogramas solos no los crean. Muestreo, retención,
tenant o permisos pueden hacer inaccesible una traza enlazada.

Para automatizar dashboards, coloque el JSON del dashboard en el valor ConfigMap. No use el
wrapper API `dashboard` ni confunda YAML de proveedor con JSON. Se seleccionan ConfigMaps
`grafana_dashboard: "1"` en `observability`. No combine proveedor/montaje manual con un sidecar
superpuesto. El JSON completo anterior puede colocarse en este ConfigMap.

## AMP: permisos separados de escritura y lectura

AMP proporciona almacenamiento y consultas compatibles con Prometheus. No recopila métricas del clúster
sin un recopilador configurado o un recolector gestionado. El Terraform siguiente crea un espacio de trabajo
y roles IRSA separados de escritura/lectura; el proveedor OIDC de EKS ya debe existir.
Las métricas de CloudWatch no se incluyen automáticamente sin una ruta de recopilación separada.

```hcl
# amp.tf
terraform {
  required_version = ">= 1.15.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.64.0"
    }
  }
}

provider "aws" {
  region = var.region
}

variable "region" {
  type    = string
  default = "ap-northeast-2"
}

variable "oidc_provider_arn" {
  type = string
}

variable "oidc_issuer" {
  type        = string
  description = "EKS OIDC issuer without https:// or a trailing slash."
  validation {
    condition     = can(regex("^oidc\\.eks\\.[a-z0-9-]+\\.amazonaws\\.com/id/[A-Za-z0-9]+$", var.oidc_issuer))
    error_message = "Use the cluster's exact OIDC issuer host/path without https://."
  }
}

resource "aws_prometheus_workspace" "docs" {
  alias = "docs-observability"
}

locals {
  clients = {
    writer = {
      service_account = "prometheus-amp"
      actions         = ["aps:RemoteWrite"]
    }
    reader = {
      service_account = "grafana-amp"
      actions         = ["aps:QueryMetrics", "aps:GetLabels", "aps:GetSeries", "aps:GetMetricMetadata"]
    }
  }
}

resource "aws_iam_role" "amp" {
  for_each = local.clients
  name     = "docs-amp-${each.key}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = var.oidc_provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${var.oidc_issuer}:sub" = "system:serviceaccount:observability:${each.value.service_account}"
          "${var.oidc_issuer}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "amp" {
  for_each = local.clients
  role     = aws_iam_role.amp[each.key].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = each.value.actions
      Resource = aws_prometheus_workspace.docs.arn
    }]
  })
}

output "workspace_id" {
  value = aws_prometheus_workspace.docs.id
}

output "workspace_endpoint" {
  value = aws_prometheus_workspace.docs.prometheus_endpoint
}

output "client_role_arns" {
  value = { for k, v in aws_iam_role.amp : k => v.arn }
}
```

`oidc_provider_arn` y `oidc_issuer` sin esquema deben identificar el mismo EKS. Writer confía en
`observability:prometheus-amp`, reader en `observability:grafana-amp`, ambos con
`aud=sts.amazonaws.com`. Las políticas solo apuntan al ARN del workspace. RemoteWrite sin
QueryMetrics no permite consultas Grafana.

Este es el overlay AMP principal de `prometheus-values.yaml`. Helm sustituye toda
`additionalDataSources`; conserve las tres entradas base antes de añadir AMP. Se sigue usando Prometheus local.

```yaml
prometheus:
  serviceAccount:
    create: true
    name: prometheus-amp
    annotations:
      eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/docs-amp-writer
  prometheusSpec:
    replicas: 2
    replicaExternalLabelName: __replica__
    externalLabels:
      cluster: production-seoul-prometheus
    remoteWrite:
    - url: https://aps-workspaces.ap-northeast-2.amazonaws.com/workspaces/REPLACE_WORKSPACE_ID/api/v1/remote_write
      sigv4:
        region: ap-northeast-2
      queueConfig:
        maxSamplesPerSend: 1000
        capacity: 5000
        maxShards: 20
grafana:
  serviceAccount:
    create: true
    name: grafana-amp
    annotations:
      eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/docs-amp-reader
  env:
    GF_AUTH_SIGV4_AUTH_ENABLED: 'true'
  additionalDataSources:
  - name: AMP
    uid: amp
    type: prometheus
    access: proxy
    url: https://aps-workspaces.ap-northeast-2.amazonaws.com/workspaces/REPLACE_WORKSPACE_ID/
    jsonData:
      httpMethod: POST
      sigV4Auth: true
      sigV4AuthType: default
      sigV4Region: ap-northeast-2
```

Guarde el fragmento como `amp-overlay.yaml` y después construya explícitamente la lista de fuentes de datos
utilizando Python con PyYAML instalado. Este programa solo combina esa lista; no reimplementa
el comportamiento general de fusión de Helm. Sustituya los ARN de roles IAM y el endpoint del espacio de trabajo antes de aplicar.

```python
import yaml
from pathlib import Path

base = yaml.safe_load(Path("prometheus-values.yaml").read_text())
overlay = yaml.safe_load(Path("amp-overlay.yaml").read_text())
overlay["grafana"]["additionalDataSources"] = (
    base["grafana"]["additionalDataSources"]
    + overlay["grafana"]["additionalDataSources"]
)
Path("amp-values.yaml").write_text(yaml.safe_dump(overlay, sort_keys=False))
```

```bash
helm template prometheus prometheus-community/kube-prometheus-stack   --version 90.1.1 --namespace observability   -f prometheus-values.yaml -f amp-values.yaml > amp-rendered.yaml
```

### HA, colas y retención

La deduplicación HA usa `cluster` y `__replica__`. Réplicas de los mismos datos necesitan el mismo
`cluster` y distintos `__replica__`. Agrupar instancias independientes con cobertura distinta puede
perder datos. Compruebe conflictos con la etiqueta `cluster` de la métrica. Planifique etiquetas
de workspace/grupo HA entre clústeres; workspaces separados no se federan automáticamente.

Shards y capacidad de cola afectan a rendimiento/memoria. WAL y reintentos no son buffers
ilimitados ni garantía de entrega. Retener siete días localmente no garantiza replay tras siete días
de caída remote-write. Vigile retraso, fallos, rechazos y WAL, y pruebe recuperación. Filtros keep de
namespace pueden eliminar métricas de nodo/clúster sin esa etiqueta; `labeldrop` puede fusionar
series distintas. Las reglas de grabación añaden agregados y no reducen automáticamente la cardinalidad original.

AMP permite retención hasta 1,095 días. Es incorrecto afirmar un máximo estricto de 150 días
que obligue a Thanos. Ampliarla no restaura métricas caducadas.

| Área | AMP | Thanos |
|---|---|---|
| Almacenamiento y operación | Administrado; el usuario conserva recopilación, IAM, cuotas, coste y reglas | Operar integración de objetos y componentes query/store/compactor |
| Retención | Configuración y límites del servicio | Políticas compactor, objetos y presupuesto |
| HA y multiclúster | Etiquetas HA y diseño de workspace explícitos | Etiquetas de réplica, deduplicación y conexiones |
| Reducción de resolución | No asumir downsampling automático al estilo Thanos | Revisar resolución/retención y consultas |

SigV4 autentica solicitudes AWS, no sustituye TLS. Verifique conjuntamente activación SigV4 en
Grafana, credenciales, confianza IRSA y permisos de consulta. Amazon Managed Grafana y Grafana
propio tienen procedimientos de roles distintos.

## Después de aplicar

1. Compruebe imágenes, PVC, puertos, montajes ConfigMap y ServiceAccounts renderizados.
2. Consulte un log, una traza y una métrica instrumentada directamente en sus backends.
3. Verifique enlaces traza-log, log-traza y exemplars, incluidos tenant y tiempo.
4. Pruebe reinicio Collector, replay Kafka, fallos IAM S3 y corte/recuperación remote-write fuera de producción.
5. Observe borrado de retención Loki, mantenimiento Tempo, avisos, cuotas y costes.

La revisión usó render fijado, parsers nativos Loki/Tempo/Collector/Alloy, comprobaciones de
PVC/Service/identidad y mocks Terraform. No desplegó EKS/Kafka/S3 ni demostró login Grafana
o acceso AWS real de lectura/escritura.

## Referencias oficiales

- [Modos Loki](https://grafana.com/docs/loki/latest/get-started/deployment-modes/)
- [Retención Loki](https://grafana.com/docs/loki/latest/operations/storage/retention/)
- [Charts comunitarios Grafana](https://github.com/grafana-community/helm-charts)
- [Ciclo de vida Promtail](https://grafana.com/docs/loki/latest/send-data/promtail/)
- [Migración Tempo 3](https://grafana.com/docs/tempo/latest/set-up-for-tracing/setup-tempo/migrate-to-3/)
- [Kafka en Tempo 3.0.3](https://github.com/grafana/tempo/blob/v3.0.3/pkg/ingest/config.go)
- [Tail sampling del Collector](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.160.0/processor/tailsamplingprocessor)
- [Procesador batch](https://github.com/open-telemetry/opentelemetry-collector/tree/v0.160.0/processor/batchprocessor)
- [Configuración de workspace AMP](https://docs.aws.amazon.com/prometheus/latest/userguide/AMP-workspace-configuration.html)
- [Alta disponibilidad AMP](https://docs.aws.amazon.com/prometheus/latest/userguide/Send-high-availability-data.html)

---

< [Anterior: Análisis de observabilidad](./08-observability-analysis.md) | [Contenido](./README.md) | [Siguiente: Optimización de recursos](./10-resource-optimization.md) >
