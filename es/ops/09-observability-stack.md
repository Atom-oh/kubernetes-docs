# Configuración y operación de la pila de observabilidad

> **Última actualización**: 16 de octubre de 2026: Loki 3.7.8, Tempo 3.0.3, Alloy 1.20.1,
> OpenTelemetry Collector Contrib 0.162.0, kube-prometheus-stack 92.9.0.

Este capítulo configura la recopilación, el almacenamiento, los permisos, la retención y la navegación entre señales.
Use los [ejemplos completos de instrumentación Go/Python y de registros JSON en Java](./08-observability-analysis.md)
del capítulo anterior. Instalar Grafana por sí solo no correlaciona las tres señales.

## Alcance y requisitos previos

| Señal | Ruta de recopilación | Almacenamiento y consultas |
|---|---|---|
| Registros | JSON por stdout de la aplicación → fuente de la API de registros de Kubernetes de Alloy | Loki → Grafana |
| Trazas | OTLP de la aplicación → Collector → Tempo | Tempo → Grafana |
| Métricas | Scrape de Prometheus; escritura remota opcional de métricas generadas por Tempo | Prometheus; AMP opcional |

Los ejemplos usan el namespace `observability`. Prepare ese namespace, los CRD de Prometheus Operator
y una StorageClass `gp3` funcional. EKS Auto Mode y el controlador EBS CSI habitual usan provisionadores
distintos; que una clase tenga el mismo nombre no demuestra que sea compatible. Los buckets de S3 y los
roles IRSA son requisitos previos independientes. Sustituya los marcadores de cuenta, rol, bucket y espacio
de trabajo. Use buckets separados según su propósito y bloquee el acceso público. Limite los roles de
Loki/Tempo a las operaciones necesarias de listado de buckets y lectura, escritura y eliminación de objetos;
incluya los permisos de la clave KMS elegida si usa SSE-KMS.

Estos ajustes son un punto de partida de configuración. El HTTP interno sin autenticación, la conexión
con Kafka, los tamaños de recursos y la retención no son valores predeterminados universales para producción.
Valide el acceso de red, TLS/autenticación, la capacidad y la recuperación en su entorno. `ClusterIP` no
proporciona autenticación.

Las versiones de los charts y de las aplicaciones son distintas. Los ejemplos de Loki y Tempo usan el
repositorio actual `grafana-community`. Proporcionar valores distribuidos al antiguo chart monolítico
`grafana/tempo` no lo convierte en una implementación distribuida.

```bash
helm repo add grafana-community https://grafana-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
```

## Loki: modos de implementación y almacenamiento en S3

Loki indexa las etiquetas de los streams y almacena el contenido de los registros en chunks. Las búsquedas
de contenido siguen leyendo datos de los streams seleccionados, por lo que la selección de etiquetas,
los intervalos de tiempo y las cachés de índices/chunks afectan al costo de las consultas. Las tasas de
compresión y los límites fijos de volumen diario requieren mediciones específicas de la carga de trabajo.

| Modo | Propósito y limitaciones |
|---|---|
| Monolithic | Componentes en un proceso; la alta disponibilidad (HA) requiere almacenamiento de objetos compartido, replicación y enrutamiento |
| SimpleScalable | Destinos separados de lectura/escritura/backend; está obsoleto y se prevé eliminarlo en Loki 4.0 |
| Distributed | Componentes independientes; requiere operaciones adicionales de red, anillo, ruta de consultas y almacenamiento |

El ejemplo usa el modo Distributed con tres ingesters y un compactor. `zoneAwareReplication: false`
significa que tres réplicas por sí solas no garantizan el aislamiento entre zonas de disponibilidad (AZ).
Valide conjuntamente la ubicación en AZ/nodos, el quórum, los PDB y las actualizaciones graduales. Las
cachés están desactivadas para reducir la carga inicial de validación; elija su capacidad mediante
pruebas de carga en producción.

La fecha del esquema corresponde a un almacén nuevo. En una instalación existente, no sustituya las
entradas históricas del esquema: consérvelas y siga el procedimiento para añadir una entrada con fecha
futura. `auth_enabled: false` selecciona el único tenant `fake` en este ejemplo interno. Habilitar la
multitenencia no añade autenticación de usuarios; un proxy de autenticación debe validar y establecer
los encabezados del tenant.

```yaml
# loki-values.yaml
deploymentMode: Distributed
loki:
  image:
    tag: 3.7.8
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

Para el chart 18.12.2, configure los PVC de ingester y compactor mediante `persistence.claims`.
Incluya `accessModes` al reemplazar la lista. Compruebe los `volumeClaimTemplates` renderizados y
que los PVC se hayan enlazado realmente; no se fíe solo del código de salida de Helm. El Service
del gateway usa el puerto **80**; el puerto HTTP del proceso de Loki es **3100**.

### Retención

Configure en conjunto un esquema TSDB v13 con un período de índice de 24 horas,
`compactor.retention_enabled`, `delete_request_store` y `limits_config.retention_period`.
La eliminación es asíncrona y respeta `retention_delete_delay`. Conserve los marcadores de eliminación
y el estado del compactor entre reinicios. No dé por sentado que un cambio de retención reorganiza
retroactivamente los datos existentes.

Las anulaciones por tenant se definen en `loki.runtimeConfig.overrides` del chart. El ejemplo
monotenant usa `fake`. El siguiente fragmento cambia el valor predeterminado de 30 días a siete días;
aplíquelo solo después de comprobar sus requisitos de retención.

```yaml
loki:
  runtimeConfig:
    overrides:
      fake:
        retention_period: 168h
```

La expiración del ciclo de vida aplicada a todo el bucket puede dañar los índices, las solicitudes
de eliminación y la configuración del ruler. Si necesita una medida de seguridad con el ciclo de vida,
limítela a los prefijos de chunks y establezca una expiración superior al período de retención más la
demora de eliminación. Evalúe por separado los costos del versionado/las copias de seguridad y los
requisitos de eliminación; habilitar el versionado no es una prueba de recuperación.

## Recopilación de registros y etiquetas con Alloy

Promtail llegó al fin de su vida útil el 2 de marzo de 2026. Los ejemplos nuevos usan Alloy.
Esta configuración lee los pods `app=correlation-api` del namespace `observability` del
[capítulo anterior](./08-observability-analysis.md) mediante la API de registros de Kubernetes.
No lee archivos de los nodos ni requiere montajes hostPath o `stage.cri`.

Una única réplica de Deployment con `Recreate` evita la duplicación en estado estable y durante las
actualizaciones. No proporciona alta disponibilidad y las actualizaciones pueden interrumpir la
recopilación. Para escalar, configure tanto el clustering de Alloy como la compatibilidad de la fuente
con el clustering, o limite los destinos por nodo. Un DaemonSet en el que cada pod descubre todos los
pods de aplicaciones duplica la recopilación.

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

Guarde estos valores como `alloy-values.yaml` e inyecte el archivo anterior con `--set-file`.
Así se evita duplicar la configuración de Alloy dentro de una cadena YAML.

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
helm upgrade --install alloy grafana/alloy --version 1.13.1   --namespace observability -f alloy-values.yaml   --set-file alloy.configMap.content=logs.alloy
```

Prefiera etiquetas acotadas como `namespace`, `service_name` y `container`. Mantenga `trace_id`
y `request_id` en el contenido JSON o en metadatos estructurados. Los nombres de pods no están
prohibidos en todos los casos, pero su duración y rotación afectan la cantidad de streams. Lo que
importa es el producto de las combinaciones de etiquetas; un número fijo de etiquetas no garantiza
la seguridad. Este ejemplo conserva la línea JSON completa y además indexa `level`. Normalice los
valores no acotados de `level` y elimine los datos personales en la aplicación o en la capa de recopilación.

### LogQL y alertas de registros

Elimine los errores de análisis JSON y los campos numéricos no válidos antes de agregarlos. El campo
de latencia siguiente se mide en milisegundos. `rate` cuenta líneas de registro por segundo; use
`bytes_rate` para obtener bytes por segundo.

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

Loki Ruler evalúa reglas LogQL y envía alertas a Alertmanager. Incluir LogQL en un PrometheusRule
o añadir una etiqueta arbitraria `loki_rule` a un ConfigMap no carga reglas. La configuración base
anterior tiene cero réplicas de ruler. Antes de probar la evaluación, configure una implementación
del ruler, su almacén/API de reglas o sus montajes, el intervalo de evaluación y el endpoint de Alertmanager.

La presencia del texto genérico `"error"` o `"unauthorized"` no demuestra una interrupción ni un
ataque. Compruebe el estado de los contenedores en kube-state-metrics para detectar CrashLoopBackOff,
en vez de confiar solo en los registros de la aplicación. Las alertas de proporción requieren ámbitos
coincidentes para numerador y denominador, gestión de errores de análisis, tratamiento del tráfico cero
y comportamiento definido cuando falte la serie de errores. Conéctelas con las
[pruebas de enrutamiento e inhibición de alertas](./07-observability-alerts.md).

## Tempo 3: operación monolítica y distribuida

Tempo permite buscar por ID de traza y por atributos con TraceQL. El metrics-generator deriva métricas
de las trazas seleccionadas; no es el mecanismo que habilita las búsquedas.

| Componente | Responsabilidad distribuida en Tempo 3 |
|---|---|
| Distributor | Escribe los spans entrantes en Kafka |
| Block-builder | Consume Kafka y crea bloques en el almacén de objetos |
| Live-store | Sirve consultas de datos recientes |
| Backend-scheduler / backend-worker | Mantenimiento, compactación y retención de bloques |
| Query-frontend / querier | Consulta los datos recientes y el almacén de objetos |

Se eliminaron los destinos ingester y compactor de 2.x, así como el modo scalable single binary.
El modo monolítico de un solo proceso no requiere Kafka. Aumentar `replicas` no es una conversión
compatible a alta disponibilidad distribuida.

### Laboratorio de instancia única

`tempo-lab-values.yaml` usa un PVC local sin Kafka. Un fallo del proceso o del PVC puede interrumpir
la disponibilidad; no mezcle esta configuración con los valores de implementación distribuida en S3.
En el chart 3.0.0, desactive protocolos Jaeger individuales con `null` en lugar de eliminar el nodo
padre, lo que impide renderizar el chart. El Service puede conservar puertos heredados; limite el acceso
según la configuración real de receptores y las políticas de red.

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

Este archivo es una alternativa al chart de instancia única, no una capa superpuesta para ese chart.
Kafka y S3 ya deben existir. El ejemplo usa un endpoint interno de Kafka en un entorno aislado de
validación. Primero confirme que los requisitos de TLS/autenticación de Kafka en producción sean
compatibles con el cliente de Tempo 3.0.3. En esta versión no se admiten campos `tls` arbitrarios
ni campos de MSK IAM en `ingest.kafka`. La compatibilidad con usuario y contraseña SASL no implica
cifrado del transporte.

Con el valor predeterminado `partitions_per_instance: 1`, tres particiones de Kafka requieren tres
block-builders. Este ejemplo del chart también usa tres live-stores. Cambiar
`auto_create_topic_default_partitions` no redimensiona un topic existente. Si la creación automática
está desactivada, configure por separado el número real de particiones, la replicación, el mínimo de
ISR, la retención y la capacidad. Añadir claves `persistence` no compatibles a los valores de
block-builder/live-store no crea PVC. Pruebe la recuperación con el comportamiento de almacenamiento
real del chart y la ventana de repetición de Kafka.

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

`backendWorker.podDisruptionBudget.enabled` se establece explícitamente para evitar que falte el
valor predeterminado en la plantilla PDB 3.5.1. El renderizado no comprueba la conectividad con Kafka,
los permisos de S3, la planificación ni las escrituras/consultas de extremo a extremo. La ingesta
distribuida usa `tempo-distributor:4318` y las consultas, `tempo-query-frontend:3200`; actualice
las URL del Collector y de Grafana del laboratorio.

### Migración de 2.x a 3.x

En el modo monolítico, revise el resultado de `tempo-cli migrate config --mode=monolithic`.
En el modo distribuido, use una implementación paralela, valide y migre el tráfico. Elimine la
configuración `ingester`, `ingester_client`, `compactor`, `metrics_generator_client` y la opción
retirada `local_blocks`. El almacenamiento histórico debe usar bloques vParquet4 o posteriores.

No habilite dos sistemas de compactación simultáneamente sobre el mismo almacenamiento compartido.
Establezca `compaction_disabled` en los valores predeterminados de 3.x y en cada anulación por tenant;
retírelo después de detener los compactors de 2.x. Las anulaciones de tenants no heredan sin más
los campos que se omiten en ellas. Verifique los ID de las trazas históricas y nuevas antes de cambiar
el tráfico. Las métricas TraceQL tienen restricciones de migración, como la cobertura de bloques RF1;
que las trazas históricas estén disponibles no implica que se conserve la misma cobertura histórica de métricas.

## Collector y muestreo

Esta configuración valida el muestreo tail en un único Collector. Las aplicaciones deben establecer
`service.name` en sus recursos. La configuración no añade automáticamente metadatos de Kubernetes;
para añadir k8sattributes, se requiere una estrategia de asociación con pods y permisos RBAC separados.
Los eventos de Kubernetes son una señal de registros; `k8s_events` no es un receptor de trazas.

La eliminación de atributos sensibles ocurre antes del búfer tail. Solo cubre las claves enumeradas,
no todos los registros, eventos ni atributos que puedan contener datos sensibles. Aplicar un hash a
`db.statement` por sí solo no garantiza privacidad ni protección de secretos.

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
          image: otel/opentelemetry-collector-contrib:0.162.0
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

Collector Contrib 0.162.0 usa `service.telemetry.metrics.readers` para sus métricas internas.
No conserve el antiguo `metrics.address`, el procesador `rate_limiting` independiente que no existe,
ni el exportador `loki` que se eliminó. Los manifiestos conectan el ConfigMap, el Service y los puertos.
Este laboratorio de instancia única usa `Recreate`; las actualizaciones pueden perder trazas en búferes
y colas en memoria.

| Ajuste | Significado |
|---|---|
| Muestreo head | Decide al inicio; aún no puede seleccionar según un error o una latencia final que todavía se desconoce |
| Muestreo tail | Decide a partir de los spans recibidos durante `decision_wait`; no garantiza que estén todos |
| Políticas de error/latencia/línea base | Aquí se combinan con OR; una política de limitación de tasa separada no impone un límite global |
| `spans_per_second` | Spans por segundo, no trazas; no es un procesador independiente |
| `num_traces` | Capacidad del búfer de trazas pendientes; el desbordamiento, los datos tardíos y los reinicios pueden hacer que se pierdan spans |
| `send_batch_size` | Disparador del envío; `send_batch_max_size` es el límite máximo del lote |

Se requiere enrutamiento por ID de traza para varios samplers tail, de modo que todos los spans de una
traza lleguen al mismo sampler. Un balanceo aleatorio ordinario del Service puede dividir las trazas.
El muestreo tail no puede recuperar spans descartados por el muestreo head. Los límites de cola,
los spans tardíos y los fallos de recepción impiden garantizar que se conserve toda traza con errores.
`UNSET` no es un estado de error; incluirlo puede retener grandes volúmenes de spans normales. Los
grafos de servicios y las métricas generadas dependen del muestreo; use métricas instrumentadas por
separado cuando necesite mediciones de toda la población de solicitudes.

## TraceQL, grafos de servicios y correlación con registros

Estas son consultas de búsqueda de trazas individuales. `span:duration` mide un span, no la traza
completa. Los atributos HTTP dependen de la versión de las convenciones semánticas del SDK: el ejemplo
de Go probado en el capítulo anterior usa `http.response.status_code`, mientras que la instrumentación
predeterminada de Python usa `http.status_code`.

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

`>>` significa descendiente; `>` significa hijo directo. `| by(...) | count()` agrega conjuntos de
spans. Las funciones de métricas de TraceQL, como `rate()`, devuelven series temporales y son distintas
de las búsquedas de trazas individuales. Para un ID conocido, use el modo de ID de traza de Grafana
o la API de Tempo; no use un atributo intrínseco no válido y un ID incompleto como
`{ trace:id = "abc123" }`.

Los ejemplos conectan los service-graphs y las span-metrics tanto en la configuración de implementación
como en las anulaciones, y luego envían los resultados al receptor de escritura remota de Prometheus.
Los grafos de servicios requieren valores adecuados de SpanKind client/server y nombres de servicios
coherentes. Añadir `http.target` sin procesar, URL completas o ID de usuario como dimensiones puede
aumentar la cardinalidad.

Reutilice los [ejemplos probados de MDC/Logback en Java y de trazas/exemplars en Go/Python](./08-observability-analysis.md).
Puede existir un contexto válido no muestreado aunque `is_recording()` sea false. No descarte los
registros ordinarios cuando no haya un span ni borre valores MDC ajenos con `MDC.clear()`.

## Prometheus y Grafana

Los siguientes valores de kube-prometheus-stack habilitan el receptor de escritura remota para las
métricas generadas por Tempo y el almacenamiento de exemplars. Restrinja el receptor a emisores de
confianza, como Tempo. Las métricas de aplicación siguen necesitando un destino de scrape/ServiceMonitor
y el contrato de métricas/etiquetas de `correlation-api` del capítulo anterior.

Grafana usa los UID explícitos `prometheus`, `loki` y `tempo`, `tracesToLogsV2`, una expresión regular
de 32 caracteres en minúsculas para el ID de traza que admite espacios en blanco y el escape de `$` en
el aprovisionamiento. El destino `serviceMap` debe contener realmente las métricas generadas del grafo
de servicios.

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
helm upgrade --install prometheus prometheus-community/kube-prometheus-stack   --version 92.9.0 --namespace observability -f prometheus-values.yaml
```

Los exemplars requieren asociación con trace/span durante la instrumentación, exposición OpenMetrics,
compatibilidad de almacenamiento en Prometheus y mapeo de UID en Grafana. HTTP/2 o configurar
histogramas por sí solos no crea exemplars. El muestreo, la retención, la tenencia o los permisos aún
pueden impedir el acceso a una traza enlazada.

Para automatizar dashboards, coloque el JSON del propio dashboard en el valor del ConfigMap.
No use el contenedor `dashboard` de una respuesta de API ni trate el YAML del proveedor como JSON
del dashboard. Estos valores seleccionan ConfigMaps con `grafana_dashboard: "1"` en `observability`.
Evite combinar un proveedor/montaje administrado manualmente con una configuración superpuesta de
sidecar. El JSON completo del dashboard del capítulo anterior se puede colocar en este ConfigMap.

## AMP: permisos independientes para escritura y lectura

AMP proporciona almacenamiento y consultas compatibles con Prometheus. No recopila métricas del
clúster sin un recopilador configurado o un scraper administrado. El siguiente Terraform crea un
espacio de trabajo y roles IRSA separados para escritura y lectura; el proveedor OIDC de EKS ya debe
existir. Las métricas de CloudWatch no se incluyen automáticamente sin una ruta de recopilación separada.

```hcl
# amp.tf
terraform {
  required_version = ">= 1.15.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.69.1"
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

`oidc_provider_arn` y `oidc_issuer`, sin esquema, deben identificar el mismo clúster de EKS.
El rol de escritura confía en `observability:prometheus-amp`; el de lectura, en
`observability:grafana-amp`; y ambos limitan `aud=sts.amazonaws.com`. Las políticas se aplican
únicamente al ARN de este espacio de trabajo. Un rol de Grafana con RemoteWrite pero sin QueryMetrics
no puede consultar métricas.

Lo siguiente es la capa de AMP principal para `prometheus-values.yaml`. Helm reemplaza la lista
completa de `additionalDataSources`, así que conserve las tres entradas base antes de añadir AMP.
El ejemplo también sigue usando Prometheus local.

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

Guarde el fragmento como `amp-overlay.yaml` y después ensamble explícitamente la lista de fuentes
de datos con Python y PyYAML instalado. Este programa solo combina esa lista; no vuelve a implementar
el comportamiento general de fusión de Helm. Sustituya los ARN de roles IAM y el endpoint del espacio
de trabajo antes de aplicar los cambios.

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
helm template prometheus prometheus-community/kube-prometheus-stack   --version 92.9.0 --namespace observability   -f prometheus-values.yaml -f amp-values.yaml > amp-rendered.yaml
```

### Alta disponibilidad, colas y retención

La deduplicación de alta disponibilidad de AMP usa `cluster` y `__replica__`. Las réplicas de los
mismos datos necesitan el mismo `cluster` y valores distintos de `__replica__`. Agrupar instancias
independientes de Prometheus con coberturas de scrape distintas puede provocar pérdida de datos.
Compruebe si hay conflictos con la etiqueta `cluster` propia de una métrica. Planifique las etiquetas
de los espacios de trabajo y grupos de alta disponibilidad entre clústeres; los espacios de trabajo
independientes no se federan automáticamente.

La cantidad y la capacidad de los shards de la cola afectan al rendimiento y la memoria. WAL y los
reintentos no son un búfer ilimitado ni garantizan la entrega. Siete días de retención local no
aseguran siete días de repetición tras una interrupción de escritura remota. Supervise el retraso,
los fallos, los rechazos y el comportamiento de WAL; además, pruebe la recuperación. Los filtros
keep de namespace pueden eliminar métricas de nodos o clústeres que no tengan esa etiqueta;
`labeldrop` puede fusionar series que antes eran distintas. Las reglas de grabación añaden series
agregadas, pero no eliminan automáticamente la cardinalidad de origen.

La retención de espacios de trabajo de AMP se puede configurar hasta 1.095 días. Es incorrecto
afirmar que 150 días es un límite estricto que obliga a usar Thanos. Aumentar la retención no puede
restaurar métricas que ya expiraron.

| Área | AMP | Thanos |
|---|---|---|
| Almacenamiento y operación | Almacenamiento administrado; el usuario sigue siendo responsable de la recopilación, IAM, las cuotas, el costo y las reglas | Operar la integración con el almacén de objetos y los componentes query/store/compactor |
| Retención | Configuración del espacio de trabajo y límites del servicio | Políticas del compactor, almacén de objetos y presupuesto |
| Alta disponibilidad y varios clústeres | Diseño explícito de etiquetas de alta disponibilidad y espacios de trabajo | Etiquetas de réplicas, deduplicación y conexiones con los almacenes |
| Reducción de resolución | No dé por sentado que incluye downsampling automático al estilo de Thanos | Revise la resolución/retención del compactor y el comportamiento de las consultas |

SigV4 autentica las solicitudes de AWS; no sustituye el cifrado TLS. Verifique en conjunto que el
proceso de Grafana tenga SigV4 habilitado, las credenciales, la confianza de IRSA y los permisos de
consulta del espacio de trabajo. Amazon Managed Grafana y Grafana autogestionado tienen flujos de
configuración de roles distintos.

## Después de aplicar los cambios

1. Compruebe las imágenes, los PVC, los puertos de Service, los montajes de ConfigMap y los ServiceAccount renderizados.
2. Consulte un registro, una traza y una métrica instrumentada directamente en sus respectivos backends.
3. Compruebe los enlaces de traza a registro, de registro a traza y de exemplars, incluidos el tenant y los intervalos de tiempo.
4. Pruebe fuera de producción el reinicio del Collector, la repetición de Kafka, los fallos de permisos de S3 y la interrupción/recuperación de la escritura remota.
5. Observe las eliminaciones de retención de Loki, el mantenimiento de bloques de Tempo, las advertencias, las cuotas y los costos.

Esta revisión usó renderizado con versiones fijadas, analizadores nativos de la configuración de
Loki/Tempo/Collector/Alloy, comprobaciones de PVC/Service/identidad renderizados y pruebas simuladas
de Terraform. No desplegó EKS/Kafka/S3 ni demostró el inicio de sesión en Grafana ni el acceso real
de lectura/escritura a AWS.

## Referencias oficiales

- [Modos de implementación de Loki](https://grafana.com/docs/loki/latest/get-started/deployment-modes/)
- [Retención de Loki](https://grafana.com/docs/loki/latest/operations/storage/retention/)
- [Charts comunitarios de Grafana](https://github.com/grafana-community/helm-charts)
- [Ciclo de vida de Promtail](https://grafana.com/docs/loki/latest/send-data/promtail/)
- [Migración a Tempo 3](https://grafana.com/docs/tempo/latest/set-up-for-tracing/setup-tempo/migrate-to-3/)
- [Configuración de Kafka en Tempo 3.0.3](https://github.com/grafana/tempo/blob/v3.0.3/pkg/ingest/config.go)
- [Muestreo tail de Collector](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.162.0/processor/tailsamplingprocessor)
- [Procesador batch de Collector](https://github.com/open-telemetry/opentelemetry-collector/tree/v0.162.0/processor/batchprocessor)
- [Configuración de espacios de trabajo de AMP](https://docs.aws.amazon.com/prometheus/latest/userguide/AMP-workspace-configuration.html)
- [Alta disponibilidad de AMP](https://docs.aws.amazon.com/prometheus/latest/userguide/Send-high-availability-data.html)

---

< [Anterior: Análisis de observabilidad](./08-observability-analysis.md) | [Contenido](./README.md) | [Siguiente: Optimización de recursos](./10-resource-optimization.md) >
