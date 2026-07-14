# Grafana Loki

> **Versiones compatibles**: Loki 3.x
> **Última actualización**: February 20, 2026

Grafana Loki es un sistema de agregación de logs escalable horizontalmente inspirado en Prometheus. Proporciona almacenamiento y consultas de logs rentables al indexar únicamente las etiquetas en lugar del contenido de los logs.

## Tabla de contenidos

1. [Descripción general](#overview)
2. [Arquitectura](#architecture)
3. [Modos de despliegue](#deployment-modes)
4. [Instalación con Helm](#helm-installation)
5. [Configuración del backend de S3](#s3-backend-configuration)
6. [Consultas LogQL](#logql-queries)
7. [Diseño de etiquetas](#label-design)
8. [Ajuste de rendimiento](#performance-tuning)
9. [Políticas de retención](#retention-policies)
10. [Solución de problemas](#troubleshooting)

---

## Descripción general

### Filosofía principal de Loki

Loki se diseñó con la filosofía de «gestionar los logs como Prometheus»:

- **Indexación basada en etiquetas**: Solo indexa metadatos (etiquetas), no el contenido de los logs
- **Eficiencia de costos**: Costos operativos 10x+ más bajos en comparación con Elasticsearch
- **Simplicidad**: Elimina la complejidad de los motores de búsqueda de texto completo
- **Integración con Grafana**: Análisis unificado de logs, métricas y trazas

### Características clave

| Característica | Descripción |
|---------|-------------|
| **Escalado horizontal** | Cada componente se puede escalar de forma independiente |
| **Multitenencia** | Admite el aislamiento de datos a nivel de tenant |
| **Almacenamiento de objetos** | Aprovecha almacenamiento económico como S3, GCS y Azure Blob |
| **LogQL** | Lenguaje de consulta intuitivo con estilo PromQL |
| **Alta disponibilidad** | Replicación y failover integrados |

### Loki frente a Elasticsearch

```
+---------------------+------------------+------------------+
|       Item          |      Loki        |   Elasticsearch  |
+---------------------+------------------+------------------+
| Indexing method     | Labels only      | Full-text        |
| Storage cost        | Low (object)     | High (SSD rec.)  |
| Query complexity    | Simple (LogQL)   | Complex (Lucene) |
| Full-text search    | Limited          | Excellent        |
| Operational complex.| Low              | High             |
| Memory requirements | Low              | High             |
| Grafana integration | Native           | Plugin           |
+---------------------+------------------+------------------+
```

---

## Arquitectura

### Descripción general de componentes

```mermaid
flowchart TB
    subgraph Clients["Clients"]
        PROMTAIL[Promtail]
        FLUENTBIT[FluentBit]
        ALLOY[Grafana Alloy]
    end

    subgraph Write["Write Path"]
        DIST[Distributor]
        ING[Ingester]
    end

    subgraph Read["Read Path"]
        QF[Query Frontend]
        QS[Query Scheduler]
        QUERIER[Querier]
    end

    subgraph Backend["Backend"]
        COMP[Compactor]
        S3[(S3 Storage)]
        CACHE[(Redis/Memcached)]
    end

    subgraph Viz["Visualization"]
        GRAFANA[Grafana]
    end

    PROMTAIL --> DIST
    FLUENTBIT --> DIST
    ALLOY --> DIST

    DIST --> ING
    ING --> S3

    GRAFANA --> QF
    QF --> QS
    QS --> QUERIER
    QUERIER --> ING
    QUERIER --> S3
    QUERIER --> CACHE

    COMP --> S3

    classDef client fill:#4CAF50,stroke:#333,color:white
    classDef write fill:#2196F3,stroke:#333,color:white
    classDef read fill:#FF9800,stroke:#333,color:white
    classDef backend fill:#9C27B0,stroke:#333,color:white
    classDef viz fill:#F44336,stroke:#333,color:white

    class PROMTAIL,FLUENTBIT,ALLOY client
    class DIST,ING write
    class QF,QS,QUERIER read
    class COMP,S3,CACHE backend
    class GRAFANA viz
```

### Detalles de los componentes

#### 1. Distributor

El primer componente que recibe flujos de logs de los clientes.

**Responsabilidades:**
- Validación de flujos de logs
- Normalización de etiquetas
- Limitación de tasa
- Enrutamiento a Ingesters mediante hashing consistente

```yaml
# Distributor configuration example
distributor:
  ring:
    kvstore:
      store: memberlist
  rate_limit_strategy: local
  rate_limit:
    enabled: true
    # Max streams per second per tenant
    ingestion_rate_limit_mb: 4
    ingestion_burst_size_mb: 6
```

#### 2. Ingester

Almacena en búfer los datos de logs en memoria y los escribe en almacenamiento a largo plazo.

**Responsabilidades:**
- Creación de chunks de datos de logs
- Gestión de WAL (Write-Ahead Log)
- Volcado de chunks al almacenamiento
- Atención de consultas en tiempo real

```yaml
# Ingester configuration example
ingester:
  lifecycler:
    ring:
      replication_factor: 3
      kvstore:
        store: memberlist
    heartbeat_period: 5s
  chunk_idle_period: 30m
  chunk_block_size: 262144
  chunk_retain_period: 1m
  max_transfer_retries: 0
  wal:
    enabled: true
    dir: /var/loki/wal
```

#### 3. Querier

Ejecuta consultas LogQL y devuelve resultados.

**Responsabilidades:**
- Consultar datos en tiempo real de Ingesters
- Consultar datos históricos desde el almacenamiento a largo plazo
- Combinar y eliminar duplicados de los resultados

```yaml
# Querier configuration example
querier:
  max_concurrent: 10
  query_timeout: 5m
  engine:
    timeout: 5m
    max_look_back_period: 30d
```

#### 4. Query Frontend

Gestiona la optimización y el almacenamiento en caché de consultas.

**Responsabilidades:**
- Dividir consultas grandes
- Almacenar resultados en caché
- Gestionar colas de consultas
- Gestionar reintentos

```yaml
# Query Frontend configuration example
query_frontend:
  max_outstanding_per_tenant: 2048
  compress_responses: true
  log_queries_longer_than: 5s
  query_stats_enabled: true
```

#### 5. Compactor

Optimiza los datos almacenados.

**Responsabilidades:**
- Combinar chunks pequeños en chunks más grandes
- Optimizar índices
- Aplicar políticas de retención (eliminación de datos)

```yaml
# Compactor configuration example
compactor:
  working_directory: /var/loki/compactor
  shared_store: s3
  compaction_interval: 10m
  retention_enabled: true
  retention_delete_delay: 2h
  retention_delete_worker_count: 150
```

---

## Modos de despliegue

Loki ofrece tres modos de despliegue:

### 1. Modo monolítico

Todos los componentes se ejecutan en un único proceso.

```yaml
# values-monolithic.yaml
deploymentMode: SingleBinary

singleBinary:
  replicas: 1
  resources:
    limits:
      cpu: 2
      memory: 4Gi
    requests:
      cpu: 1
      memory: 2Gi

loki:
  auth_enabled: false
  commonConfig:
    replication_factor: 1
```

**Ideal para:**
- Entornos de desarrollo/prueba
- Volumen diario de logs < 100GB
- Creación rápida de prototipos

### 2. Modo escalable simple (recomendado)

Proporciona escalabilidad al separar las rutas de lectura/escritura.

```yaml
# values-simple-scalable.yaml
deploymentMode: SimpleScalable

read:
  replicas: 3
  resources:
    limits:
      cpu: 2
      memory: 4Gi
    requests:
      cpu: 1
      memory: 2Gi

write:
  replicas: 3
  resources:
    limits:
      cpu: 2
      memory: 4Gi
    requests:
      cpu: 1
      memory: 2Gi

backend:
  replicas: 2
  resources:
    limits:
      cpu: 1
      memory: 2Gi
    requests:
      cpu: 500m
      memory: 1Gi
```

**Ideal para:**
- Entornos de producción
- Volumen diario de logs de 100GB ~ 10TB
- La mayoría de los clusters de EKS

### 3. Modo de microservicios

Despliega cada componente de manera independiente.

```yaml
# values-microservices.yaml
deploymentMode: Distributed

distributor:
  replicas: 3
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10

ingester:
  replicas: 3
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 20
  persistence:
    enabled: true
    size: 50Gi

querier:
  replicas: 3
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 15

queryFrontend:
  replicas: 2
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 5

compactor:
  replicas: 1
```

**Ideal para:**
- Entornos de producción a gran escala
- Volumen diario de logs > 10TB
- Gestión detallada de recursos por componente

---

## Instalación con Helm

### Requisitos previos

```bash
# Add Helm repository
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Create namespace
kubectl create namespace loki
```

### Instalación del modo escalable simple (recomendada para EKS)

```yaml
# values-eks-production.yaml
deploymentMode: SimpleScalable

loki:
  auth_enabled: false

  schemaConfig:
    configs:
      - from: "2024-01-01"
        store: tsdb
        object_store: s3
        schema: v13
        index:
          prefix: loki_index_
          period: 24h

  storage:
    type: s3
    bucketNames:
      chunks: my-loki-chunks
      ruler: my-loki-ruler
      admin: my-loki-admin
    s3:
      region: ap-northeast-2
      # endpoint auto-configured when using IRSA

  commonConfig:
    replication_factor: 3

  limits_config:
    retention_period: 744h  # 31 days
    max_query_length: 721h
    max_query_parallelism: 32
    ingestion_rate_mb: 10
    ingestion_burst_size_mb: 20
    per_stream_rate_limit: 5MB
    per_stream_rate_limit_burst: 15MB

  rulerConfig:
    storage:
      type: s3
      s3:
        bucketnames: my-loki-ruler

# Read path
read:
  replicas: 3
  resources:
    limits:
      cpu: 2
      memory: 4Gi
    requests:
      cpu: 1
      memory: 2Gi
  affinity:
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 100
          podAffinityTerm:
            labelSelector:
              matchLabels:
                app.kubernetes.io/component: read
            topologyKey: topology.kubernetes.io/zone

# Write path
write:
  replicas: 3
  resources:
    limits:
      cpu: 2
      memory: 4Gi
    requests:
      cpu: 1
      memory: 2Gi
  persistence:
    enabled: true
    size: 50Gi
    storageClass: gp3
  affinity:
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 100
          podAffinityTerm:
            labelSelector:
              matchLabels:
                app.kubernetes.io/component: write
            topologyKey: topology.kubernetes.io/zone

# Backend
backend:
  replicas: 2
  resources:
    limits:
      cpu: 1
      memory: 2Gi
    requests:
      cpu: 500m
      memory: 1Gi
  persistence:
    enabled: true
    size: 20Gi
    storageClass: gp3

# Gateway
gateway:
  enabled: true
  replicas: 2
  resources:
    limits:
      cpu: 500m
      memory: 512Mi
    requests:
      cpu: 100m
      memory: 128Mi
  ingress:
    enabled: true
    ingressClassName: alb
    annotations:
      alb.ingress.kubernetes.io/scheme: internal
      alb.ingress.kubernetes.io/target-type: ip
    hosts:
      - host: loki.internal.example.com
        paths:
          - path: /
            pathType: Prefix

# Results caching
resultsCache:
  enabled: true
  defaultValidity: 12h
  # External Redis recommended for production
  # host: redis.example.com:6379

# Chunks caching
chunksCache:
  enabled: true
  defaultValidity: 12h

# Monitoring
monitoring:
  serviceMonitor:
    enabled: true
    labels:
      release: prometheus
  selfMonitoring:
    enabled: true
    grafanaAgent:
      installOperator: false

# Disable tests
test:
  enabled: false
```

### Ejecutar la instalación

```bash
# Install
helm install loki grafana/loki \
  --namespace loki \
  --values values-eks-production.yaml \
  --version 6.x.x

# Upgrade
helm upgrade loki grafana/loki \
  --namespace loki \
  --values values-eks-production.yaml

# Check status
kubectl get pods -n loki
kubectl get svc -n loki
```

---

## Configuración del backend de S3

### Configuración de IRSA (IAM Roles for Service Accounts)

```bash
# 1. Create IAM policy
cat > loki-s3-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": [
        "arn:aws:s3:::my-loki-chunks",
        "arn:aws:s3:::my-loki-ruler",
        "arn:aws:s3:::my-loki-admin"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::my-loki-chunks/*",
        "arn:aws:s3:::my-loki-ruler/*",
        "arn:aws:s3:::my-loki-admin/*"
      ]
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name LokiS3Policy \
  --policy-document file://loki-s3-policy.json

# 2. Setup IRSA
eksctl create iamserviceaccount \
  --cluster=my-cluster \
  --namespace=loki \
  --name=loki \
  --attach-policy-arn=arn:aws:iam::123456789012:policy/LokiS3Policy \
  --approve
```

### Creación de bucket de S3 (Terraform)

```hcl
# s3.tf
resource "aws_s3_bucket" "loki_chunks" {
  bucket = "my-loki-chunks"

  tags = {
    Name        = "Loki Chunks"
    Environment = "production"
  }
}

resource "aws_s3_bucket" "loki_ruler" {
  bucket = "my-loki-ruler"

  tags = {
    Name        = "Loki Ruler"
    Environment = "production"
  }
}

resource "aws_s3_bucket_versioning" "loki_chunks" {
  bucket = aws_s3_bucket.loki_chunks.id
  versioning_configuration {
    status = "Disabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "loki_chunks" {
  bucket = aws_s3_bucket.loki_chunks.id

  rule {
    id     = "transition-to-ia"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "loki_chunks" {
  bucket = aws_s3_bucket.loki_chunks.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "loki_chunks" {
  bucket = aws_s3_bucket.loki_chunks.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
```

### Configuración de almacenamiento de Loki

```yaml
# loki-config.yaml
storage_config:
  tsdb_shipper:
    active_index_directory: /var/loki/tsdb-index
    cache_location: /var/loki/tsdb-cache
    shared_store: s3

  aws:
    s3: s3://ap-northeast-2/my-loki-chunks
    bucketnames: my-loki-chunks
    region: ap-northeast-2
    # access_key_id and secret_access_key not needed with IRSA
    s3forcepathstyle: false
    insecure: false
    sse_encryption: true

  boltdb_shipper:
    active_index_directory: /var/loki/boltdb-index
    cache_location: /var/loki/boltdb-cache
    shared_store: s3
```

---

## Consultas LogQL

### Sintaxis básica

LogQL admite dos tipos de consultas:

1. **Consultas de logs**: Devuelven líneas de logs
2. **Consultas de métricas**: Devuelven valores calculados a partir de logs

### Selectores de flujos

```logql
# Basic stream selection
{namespace="production"}

# Multiple label combinations
{namespace="production", app="nginx"}

# Label matching operators
{namespace="production", app=~"nginx|apache"}  # Regex match
{namespace!="kube-system"}                      # Negation
{app!~"test.*"}                                 # Regex negation
```

### Filtros de líneas

```logql
# Contains
{app="nginx"} |= "error"

# Does not contain
{app="nginx"} != "healthcheck"

# Regex match
{app="nginx"} |~ "status=[45][0-9]{2}"

# Regex does not match
{app="nginx"} !~ "GET /health"

# Chaining
{app="nginx"} |= "error" != "timeout" |~ "user_id=\\d+"
```

### Parsers

```logql
# JSON parser
{app="api"} | json

# Extract specific fields only
{app="api"} | json level, message, user_id

# Logfmt parser
{app="api"} | logfmt

# Regex parser
{app="nginx"} | regexp `(?P<ip>[\d.]+) - - \[(?P<timestamp>[^\]]+)\]`

# Pattern parser (faster)
{app="nginx"} | pattern `<ip> - - [<_>] "<method> <path> <_>" <status> <size>`

# Unpack (Promtail pack stage result)
{app="api"} | unpack
```

### Filtros de etiquetas

```logql
# Filter after JSON parsing
{app="api"} | json | level="error"

# Numeric comparison
{app="api"} | json | response_time > 1000

# Multiple conditions
{app="api"} | json | level="error" and user_id!=""

# IP filtering
{app="nginx"} | pattern `<ip> - -` | ip != "10.0.0.1"
```

### Formato de línea

```logql
# Reconstruct log line
{app="api"} | json | line_format "{{.level}}: {{.message}}"

# Conditional format
{app="api"} | json | line_format `{{ if eq .level "error" }}ERROR: {{ end }}{{.message}}`

# Template functions
{app="api"} | json | line_format `{{ .timestamp | toDate "2006-01-02T15:04:05Z07:00" | date "15:04:05" }}`
```

### Consultas de métricas

```logql
# Log lines per second
rate({app="nginx"}[5m])

# Error ratio
sum(rate({app="nginx"} |= "error" [5m])) / sum(rate({app="nginx"}[5m]))

# Response time percentiles
quantile_over_time(0.99,
  {app="api"} | json | unwrap response_time [5m]
) by (endpoint)

# Top 10 errors
topk(10, sum by (error_type) (
  count_over_time({app="api"} | json | level="error" [1h])
))

# Average response size
avg_over_time(
  {app="nginx"} | pattern `<_> <_> <size>` | unwrap size [5m]
) by (path)

# Error count aggregation
sum(count_over_time({namespace="production"} |= "error" [1h])) by (app)

# Absent log detection
absent_over_time({app="critical-service"}[5m])
```

### Ejemplos de consultas prácticas

```logql
# Analyze Kubernetes pod restart causes
{namespace="production"} |= "OOMKilled" or |= "CrashLoopBackOff"

# Find slow API requests
{app="api"} | json | response_time > 5000 | line_format `{{.method}} {{.path}}: {{.response_time}}ms`

# Track specific user activity
{app="api"} | json | user_id="user-12345" | line_format `{{.timestamp}} {{.action}}`

# HTTP 5xx error analysis
{app="nginx"} | pattern `<_> "<method> <path> <_>" <status>` | status >= 500

# Error patterns by time
sum by (hour) (
  count_over_time({app="api"} |= "error" [1h])
  | label_format hour="{{ __timestamp__ | date \"15\" }}"
)

# Detect error spike after deployment
sum(increase(
  count_over_time({app="api"} |= "error" [5m])
)) > 100
```

---

## Diseño de etiquetas

### Principios de diseño de etiquetas

Un buen diseño de etiquetas es clave para el rendimiento de Loki.

#### Etiquetas recomendadas

```yaml
# Good labels (low cardinality)
labels:
  - namespace     # ~10-50 values
  - app           # ~50-200 values
  - environment   # dev, staging, production
  - component     # api, worker, scheduler
  - log_level     # debug, info, warn, error
```

#### Etiquetas que se deben evitar

```yaml
# Bad labels (high cardinality)
labels:
  - pod_name      # Thousands of unique values
  - request_id    # Unique per request
  - user_id       # Millions of users
  - timestamp     # Never use as label
  - ip_address    # Very high cardinality
```

### Gestión de cardinalidad

```mermaid
graph LR
    A[Number of Labels] --> B{Total Streams}
    C[Label Value Types] --> B
    B --> D[Index Size]
    B --> E[Query Performance]
    B --> F[Memory Usage]

    style B fill:#FF9800,stroke:#333
```

**Cálculo de cantidad de flujos:**
```
Total streams = namespace values x app values x component values x ...
```

**Recomendaciones:**
- Flujos totales por cluster: < 100,000
- Flujos activos por tenant: < 10,000
- Valores únicos por etiqueta: < 1,000

### Configuración de etiquetas de Promtail

```yaml
# promtail-config.yaml
scrape_configs:
  - job_name: kubernetes-pods
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      # Namespace label
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace

      # App label (from Kubernetes labels)
      - source_labels: [__meta_kubernetes_pod_label_app]
        target_label: app

      # Component label
      - source_labels: [__meta_kubernetes_pod_label_component]
        target_label: component

      # Container name
      - source_labels: [__meta_kubernetes_pod_container_name]
        target_label: container

      # Do not add pod_name as label (high cardinality)
      # Include in log line instead

    pipeline_stages:
      - json:
          expressions:
            level: level
      - labels:
          level:
```

### Etiquetado dinámico

```yaml
# Extract labels from log content
pipeline_stages:
  - json:
      expressions:
        level: level
        service: service

  - labels:
      level:
      service:

  # High cardinality values as structured metadata
  - structured_metadata:
      user_id:
      request_id:
```

---

## Ajuste de rendimiento

### Ajuste de Ingester

```yaml
ingester:
  # Chunk settings
  chunk_idle_period: 30m      # Wait time before flushing idle stream
  chunk_block_size: 262144    # Chunk block size (256KB)
  chunk_target_size: 1572864  # Target chunk size (1.5MB)
  chunk_retain_period: 1m     # Memory retention time after flush

  # Concurrency
  max_chunk_age: 2h           # Maximum chunk age
  concurrent_flushes: 32      # Concurrent flush count

  # WAL
  wal:
    enabled: true
    dir: /var/loki/wal
    flush_on_shutdown: true
    replay_memory_ceiling: 4GB
```

### Ajuste de Querier

```yaml
querier:
  max_concurrent: 16          # Concurrent queries
  query_timeout: 5m           # Query timeout

  engine:
    timeout: 5m
    max_look_back_period: 30d

query_range:
  align_queries_with_step: true
  cache_results: true
  max_retries: 5
  parallelise_shardable_queries: true

  results_cache:
    cache:
      embedded_cache:
        enabled: true
        max_size_mb: 500
```

### Ajuste de Frontend

```yaml
query_frontend:
  max_outstanding_per_tenant: 4096
  compress_responses: true
  log_queries_longer_than: 10s

  # Query splitting
  split_queries_by_interval: 30m

query_scheduler:
  max_outstanding_requests_per_tenant: 2048
  grpc_client_config:
    max_recv_msg_size: 104857600  # 100MB
```

### Guía de recursos

```yaml
# Small (daily < 100GB)
write:
  replicas: 2
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 1
      memory: 2Gi

read:
  replicas: 2
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 1
      memory: 2Gi

---
# Medium (daily 100GB - 1TB)
write:
  replicas: 3
  resources:
    requests:
      cpu: 1
      memory: 2Gi
    limits:
      cpu: 2
      memory: 4Gi

read:
  replicas: 3
  resources:
    requests:
      cpu: 1
      memory: 2Gi
    limits:
      cpu: 2
      memory: 4Gi

---
# Large (daily > 1TB)
write:
  replicas: 5
  autoscaling:
    enabled: true
    minReplicas: 5
    maxReplicas: 20
  resources:
    requests:
      cpu: 2
      memory: 4Gi
    limits:
      cpu: 4
      memory: 8Gi

read:
  replicas: 5
  autoscaling:
    enabled: true
    minReplicas: 5
    maxReplicas: 15
  resources:
    requests:
      cpu: 2
      memory: 4Gi
    limits:
      cpu: 4
      memory: 8Gi
```

---

## Políticas de retención

### Política de retención global

```yaml
# loki-config.yaml
limits_config:
  retention_period: 744h  # 31 days (default)

compactor:
  working_directory: /var/loki/compactor
  shared_store: s3
  retention_enabled: true
  retention_delete_delay: 2h
  retention_delete_worker_count: 150
  delete_request_store: s3
```

### Política de retención por tenant

```yaml
# runtime-config.yaml
overrides:
  tenant-production:
    retention_period: 2160h   # 90 days

  tenant-development:
    retention_period: 168h    # 7 days

  tenant-compliance:
    retention_period: 8760h   # 365 days
```

### Política de retención por flujo

```yaml
limits_config:
  retention_stream:
    - selector: '{namespace="production", level="error"}'
      priority: 1
      period: 2160h  # 90 days - production errors

    - selector: '{namespace="development"}'
      priority: 2
      period: 72h    # 3 days - development

    - selector: '{app="audit-log"}'
      priority: 1
      period: 8760h  # 365 days - audit logs
```

---

## Solución de problemas

### Problemas comunes y soluciones

#### 1. "too many outstanding requests"

```yaml
# Symptom: Query failures, 503 errors
# Cause: Frontend/scheduler overload

# Solution
query_frontend:
  max_outstanding_per_tenant: 4096  # Increase from default 2048

query_scheduler:
  max_outstanding_requests_per_tenant: 2048

# Or increase querier replicas
querier:
  replicas: 5  # From 3 to 5
```

#### 2. "rate limit exceeded"

```yaml
# Symptom: Log collection failures, 429 errors
# Cause: Ingestion rate limit exceeded

# Solution
limits_config:
  ingestion_rate_mb: 20           # Increase from default 4
  ingestion_burst_size_mb: 30     # Increase from default 6
  per_stream_rate_limit: 10MB     # Per-stream limit
  per_stream_rate_limit_burst: 30MB
```

#### 3. "max streams limit exceeded"

```yaml
# Symptom: New stream creation fails
# Cause: High cardinality labels

# Solution 1: Increase limit (temporary)
limits_config:
  max_streams_per_user: 20000     # Default 10000

# Solution 2: Reduce label cardinality (recommended)
# Remove high cardinality labels in promtail config
```

#### 4. Degradación del rendimiento de consultas

```bash
# Diagnostics
# 1. Check query stats
curl -s "http://loki:3100/loki/api/v1/query_range" \
  -G --data-urlencode 'query={app="nginx"}' \
  --data-urlencode 'start=1h' | jq '.data.stats'

# 2. Check stream count
curl -s "http://loki:3100/loki/api/v1/series" \
  -G --data-urlencode 'match[]={namespace="production"}' | jq '.data | length'
```

```yaml
# Solution
query_range:
  parallelise_shardable_queries: true
  split_queries_by_interval: 15m  # From 30m to 15m

limits_config:
  max_query_parallelism: 64       # From 32 to 64
```

#### 5. OOM de Ingester

```yaml
# Symptom: Ingester pod restarts, OOM Killed
# Cause: Insufficient memory settings or chunk configuration issues

# Solution 1: Increase memory
ingester:
  resources:
    limits:
      memory: 8Gi   # Increase from 4Gi
    requests:
      memory: 4Gi

# Solution 2: Adjust chunk settings
ingester:
  chunk_idle_period: 15m     # Decrease from 30m
  chunk_target_size: 1048576 # Smaller chunks
  max_chunk_age: 1h          # Decrease from 2h
```

### Comandos de diagnóstico útiles

```bash
# Check Loki status
kubectl exec -it loki-read-0 -n loki -- wget -qO- http://localhost:3100/ready

# Check ring membership
kubectl exec -it loki-write-0 -n loki -- wget -qO- http://localhost:3100/ring

# Check flush status
kubectl exec -it loki-write-0 -n loki -- wget -qO- http://localhost:3100/flush

# Check metrics
kubectl exec -it loki-write-0 -n loki -- wget -qO- http://localhost:3100/metrics | grep loki_ingester

# Check configuration
kubectl exec -it loki-read-0 -n loki -- wget -qO- http://localhost:3100/config
```

### Configuración del dashboard de Grafana

```json
{
  "annotations": {
    "list": []
  },
  "panels": [
    {
      "title": "Ingestion Rate",
      "targets": [
        {
          "expr": "sum(rate(loki_distributor_bytes_received_total[5m]))",
          "legendFormat": "bytes/s"
        }
      ]
    },
    {
      "title": "Active Streams",
      "targets": [
        {
          "expr": "sum(loki_ingester_memory_streams)",
          "legendFormat": "streams"
        }
      ]
    },
    {
      "title": "Query Latency",
      "targets": [
        {
          "expr": "histogram_quantile(0.99, sum(rate(loki_request_duration_seconds_bucket{route=~\"loki_api_v1_query.*\"}[5m])) by (le))",
          "legendFormat": "p99"
        }
      ]
    }
  ]
}
```

---

## Resumen de prácticas recomendadas

### Recomendaciones

1. **Mantén las etiquetas al mínimo**: Usa solo namespace, app, component y level
2. **Adopta logs JSON**: Reduce la sobrecarga de parsing con logs estructurados
3. **Configura el ciclo de vida de S3**: Configura la clasificación por niveles para optimizar costos
4. **Usa IRSA**: Usa IAM Role en lugar de Access Keys
5. **Habilita el almacenamiento en caché**: Mejora el rendimiento con la caché de resultados de consultas y chunks
6. **Configura la monitorización**: Recopila las métricas de Loki y configura alertas

### Prácticas que se deben evitar

1. **Evita etiquetas de alta cardinalidad**: pod_name, request_id, etc.
2. **Evita rangos de consulta ilimitados**: Los límites de rango de tiempo son esenciales
3. **Evita el despliegue en un único nodo**: Mínimo de 3 réplicas para producción
4. **No deshabilites WAL**: Es esencial para prevenir la pérdida de datos
5. **No despliegues sin límites de recursos**: Evita OOM

---

## Cuestionario

Pon a prueba tus conocimientos con el [Cuestionario de Loki](../../quizzes/observability/logging/01-loki-quiz.md).
