# Grafana Mimir

> **Versiones compatibles**: Mimir 2.x
> **Última actualización**: February 20, 2026

## Tabla de contenido

- [Introducción](#introduction)
- [Arquitectura](#architecture)
- [Componentes principales](#core-components)
- [Multi-tenancy](#multi-tenancy)
- [Instalación con Helm](#helm-installation)
- [Configuración del backend S3](#s3-backend-configuration)
- [Consultas y retención de datos](#query-and-data-retention)
- [Comparación con VictoriaMetrics](#comparison-with-victoriametrics)
- [Ajuste de rendimiento](#performance-tuning)
- [Prácticas recomendadas](#best-practices)
- [Solución de problemas](#troubleshooting)

## Introducción

Grafana Mimir es un almacenamiento de métricas a largo plazo, de código abierto y escalable horizontalmente, desarrollado por Grafana Labs. Como almacenamiento de nivel empresarial para métricas de Prometheus, proporciona multi-tenancy, alta disponibilidad y escalabilidad ilimitada mediante Object Storage.

### Características principales

| Característica | Descripción |
|---------|-------------|
| **Escalado horizontal** | Escalable a miles de millones de series temporales activas |
| **Multi-tenancy** | Soporte nativo de aislamiento de tenants |
| **Alta disponibilidad** | Replicación a nivel de componente y failover automático |
| **Object Storage** | Compatible con S3, GCS, Azure Blob, etc. |
| **100% compatible con PromQL** | Compatible con todas las consultas PromQL |
| **Retención a largo plazo** | Período de retención de datos ilimitado |
| **Integración con Grafana** | Integración nativa con Grafana |

### Mimir vs Cortex vs Thanos

Mimir es el sucesor de Cortex y ofrece mejor rendimiento y operabilidad:

```mermaid
flowchart LR
    subgraph HISTORY["Evolution"]
        direction TB
        C[Cortex<br/>2016]
        M[Mimir<br/>2022]
        T[Thanos<br/>2017]
    end

    subgraph APPROACH["Approach"]
        CA[Centralized<br/>Remote Write]
        TA[Sidecar-based<br/>Federated Query]
    end

    C --> M
    C -.-> CA
    T -.-> TA
    M -.-> CA

    classDef legacy fill:#95A5A6,stroke:#333,stroke-width:1px,color:white
    classDef current fill:#3498DB,stroke:#333,stroke-width:1px,color:white
    classDef approach fill:#27AE60,stroke:#333,stroke-width:1px,color:white

    class C legacy
    class M,T current
    class CA,TA approach
```

| Elemento | Mimir | Cortex | Thanos |
|------|-------|--------|--------|
| Arquitectura | Centralizada | Centralizada | Basada en Sidecar |
| Complejidad | Media | Alta | Media |
| Rendimiento de consultas | Rápido | Medio | Medio |
| Sobrecarga operativa | Baja | Alta | Media |
| Modificación de Prometheus | No requerida | No requerida | Requiere Sidecar |
| Multi-tenancy | Nativa | Nativa | Limitada |

## Arquitectura

### Arquitectura general

```mermaid
flowchart TB
    subgraph WRITE["Write Path"]
        P1[Prometheus 1]
        P2[Prometheus 2]
        P3[Prometheus 3]
    end

    subgraph MIMIR["Grafana Mimir"]
        subgraph DIST["Distributor"]
            D1[Distributor 1]
            D2[Distributor 2]
        end

        subgraph ING["Ingester"]
            I1[Ingester 1]
            I2[Ingester 2]
            I3[Ingester 3]
        end

        subgraph STORE["Store-gateway"]
            SG1[Store-gateway 1]
            SG2[Store-gateway 2]
        end

        subgraph COMPACT["Compactor"]
            C1[Compactor]
        end

        subgraph QUERY["Querier"]
            Q1[Querier 1]
            Q2[Querier 2]
        end

        subgraph QF["Query-frontend"]
            QF1[Query-frontend]
        end
    end

    subgraph STORAGE["Object Storage"]
        S3[(S3/GCS/Azure)]
    end

    subgraph READ["Read Path"]
        G[Grafana]
    end

    P1 & P2 & P3 -->|remote_write| D1 & D2
    D1 & D2 --> I1 & I2 & I3
    I1 & I2 & I3 -->|Block upload| S3
    C1 -->|Compaction| S3
    SG1 & SG2 -->|Block read| S3
    Q1 & Q2 --> I1 & I2 & I3
    Q1 & Q2 --> SG1 & SG2
    QF1 --> Q1 & Q2
    G --> QF1

    classDef prometheus fill:#E6522C,stroke:#333,stroke-width:1px,color:white
    classDef mimir fill:#F46800,stroke:#333,stroke-width:1px,color:white
    classDef storage fill:#4285F4,stroke:#333,stroke-width:1px,color:white
    classDef client fill:#F8B52A,stroke:#333,stroke-width:1px,color:black

    class P1,P2,P3 prometheus
    class D1,D2,I1,I2,I3,SG1,SG2,C1,Q1,Q2,QF1 mimir
    class S3 storage
    class G client
```

### Flujo de datos

1. **Write Path**:
   - Prometheus envía métricas mediante remote_write
   - Distributor valida el tenant y distribuye las muestras
   - Ingester almacena en memoria y carga bloques periódicamente

2. **Read Path**:
   - Query-frontend divide las consultas y las almacena en caché
   - Querier consulta Ingester (datos recientes) y Store-gateway (datos históricos)
   - Los resultados se combinan y devuelven

3. **Procesos en segundo plano**:
   - Compactor combina bloques pequeños en bloques más grandes
   - Aplica políticas de downsampling y retención

## Componentes principales

### Distributor

El primer punto de entrada para solicitudes de escritura, que gestiona la validación de tenants y la distribución de muestras.

```yaml
# Distributor configuration
distributor:
  ring:
    kvstore:
      store: memberlist
  instance_limits:
    max_inflight_push_requests: 30000
    max_ingestion_rate: 100000
```

**Funciones**:
- Validación de ID de tenant
- Validación de series temporales (labels, valores de muestra)
- Distribución de Ingester basada en hash ring
- Replicación basada en el factor de replicación

### Ingester

Almacena datos de series temporales en memoria y los carga periódicamente a Object Storage.

```yaml
# Ingester configuration
ingester:
  ring:
    replication_factor: 3
    kvstore:
      store: memberlist
  instance_limits:
    max_series: 5000000
    max_inflight_push_requests: 30000

blocks_storage:
  tsdb:
    block_ranges_period: [2h]
    retention_period: 24h
    ship_interval: 1m
```

**Funciones**:
- Almacenar datos de series temporales en memoria
- Mantener WAL (Write-Ahead Log)
- Crear y cargar bloques TSDB
- Procesar consultas de datos recientes

### Store-gateway

Almacena en caché y consulta bloques desde Object Storage.

```yaml
# Store-gateway configuration
store_gateway:
  sharding_ring:
    replication_factor: 3
    kvstore:
      store: memberlist

blocks_storage:
  bucket_store:
    sync_interval: 15m
    bucket_index:
      enabled: true
    chunks_cache:
      backend: memcached
      memcached:
        addresses: dns+memcached:11211
    metadata_cache:
      backend: memcached
      memcached:
        addresses: dns+memcached:11211
```

**Funciones**:
- Almacenar en caché índices de bloques de Object Storage
- Procesar consultas de datos históricos
- Almacenar en caché los metadatos y chunks de bloques

### Compactor

Realiza compactación de bloques y downsampling.

```yaml
# Compactor configuration
compactor:
  data_dir: /data/compactor
  sharding_ring:
    kvstore:
      store: memberlist
  compaction_interval: 1h
  block_ranges: [2h, 12h, 24h]
  deletion_delay: 12h
```

**Funciones**:
- Combinar bloques pequeños en bloques más grandes
- Eliminar datos duplicados
- Eliminar datos según las políticas de retención
- Optimizar índices de bloques

### Querier

Consulta y combina datos de Ingester y Store-gateway.

```yaml
# Querier configuration
querier:
  max_concurrent: 20
  timeout: 2m
  query_ingesters_within: 13h
```

**Funciones**:
- Ejecutar consultas PromQL
- Consultar en paralelo a Ingester/Store-gateway
- Combinar resultados y eliminar duplicados

### Query-frontend

Gestiona la optimización y el almacenamiento en caché de consultas.

```yaml
# Query-frontend configuration
query_frontend:
  align_querier_with_step: true
  cache_results: true
  results_cache:
    backend: memcached
    memcached:
      addresses: dns+memcached:11211
      timeout: 500ms
  split_queries_by_interval: 24h
  max_retries: 5
```

**Funciones**:
- Dividir consultas grandes
- Almacenar resultados en caché
- Gestionar colas de consultas
- Gestionar reintentos

## Multi-tenancy

Mimir admite multi-tenancy nativa para aislar las métricas de varios equipos u organizaciones.

### Configuración de tenant

```yaml
# Add tenant header to Prometheus remote_write
remote_write:
  - url: http://mimir:8080/api/v1/push
    headers:
      X-Scope-OrgID: tenant-1

# Or identify tenant via basic auth
remote_write:
  - url: http://mimir:8080/api/v1/push
    basic_auth:
      username: tenant-1
      password: secret
```

### Límites por tenant

```yaml
# Mimir configuration
limits:
  # Default limits (all tenants)
  ingestion_rate: 100000
  ingestion_burst_size: 200000
  max_global_series_per_user: 5000000
  max_global_series_per_metric: 50000
  max_label_names_per_series: 30
  max_label_value_length: 2048

# Per-tenant overrides
overrides:
  tenant-1:
    ingestion_rate: 200000
    max_global_series_per_user: 10000000
  tenant-2:
    ingestion_rate: 50000
    max_global_series_per_user: 1000000
```

### Aislamiento de tenants

```mermaid
flowchart TD
    subgraph TENANTS["Tenants"]
        T1[Tenant A<br/>Team A]
        T2[Tenant B<br/>Team B]
        T3[Tenant C<br/>Team C]
    end

    subgraph MIMIR["Mimir"]
        D[Distributor]
        I[Ingester]
    end

    subgraph STORAGE["Object Storage"]
        B1[tenant-a/blocks/]
        B2[tenant-b/blocks/]
        B3[tenant-c/blocks/]
    end

    T1 -->|X-Scope-OrgID: tenant-a| D
    T2 -->|X-Scope-OrgID: tenant-b| D
    T3 -->|X-Scope-OrgID: tenant-c| D

    D --> I
    I --> B1 & B2 & B3

    classDef tenant fill:#00C7B7,stroke:#333,stroke-width:1px,color:white
    classDef mimir fill:#F46800,stroke:#333,stroke-width:1px,color:white
    classDef storage fill:#4285F4,stroke:#333,stroke-width:1px,color:white

    class T1,T2,T3 tenant
    class D,I mimir
    class B1,B2,B3 storage
```

## Instalación con Helm

### Instalar mimir-distributed

```bash
# Add Helm repository
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Install
helm install mimir grafana/mimir-distributed \
  --namespace monitoring \
  --create-namespace \
  -f values.yaml
```

### values.yaml

```yaml
# Global configuration
global:
  # Object storage configuration
  extraEnvFrom:
    - secretRef:
        name: mimir-s3-credentials

# Distributor
distributor:
  replicas: 3
  resources:
    requests:
      cpu: 100m
      memory: 512Mi
    limits:
      cpu: 1000m
      memory: 2Gi

# Ingester
ingester:
  replicas: 3
  persistentVolume:
    enabled: true
    storageClass: gp3
    size: 50Gi
  resources:
    requests:
      cpu: 500m
      memory: 2Gi
    limits:
      cpu: 2000m
      memory: 8Gi
  zoneAwareReplication:
    enabled: true
    zones:
      - name: zone-a
        nodeSelector:
          topology.kubernetes.io/zone: ap-northeast-2a
      - name: zone-b
        nodeSelector:
          topology.kubernetes.io/zone: ap-northeast-2b
      - name: zone-c
        nodeSelector:
          topology.kubernetes.io/zone: ap-northeast-2c

# Store-gateway
store_gateway:
  replicas: 3
  persistentVolume:
    enabled: true
    storageClass: gp3
    size: 20Gi
  resources:
    requests:
      cpu: 200m
      memory: 1Gi
    limits:
      cpu: 1000m
      memory: 4Gi

# Compactor
compactor:
  replicas: 1
  persistentVolume:
    enabled: true
    storageClass: gp3
    size: 50Gi
  resources:
    requests:
      cpu: 500m
      memory: 2Gi
    limits:
      cpu: 2000m
      memory: 8Gi

# Querier
querier:
  replicas: 3
  resources:
    requests:
      cpu: 200m
      memory: 512Mi
    limits:
      cpu: 1000m
      memory: 2Gi

# Query-frontend
query_frontend:
  replicas: 2
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: 500m
      memory: 1Gi

# Query-scheduler (optional)
query_scheduler:
  enabled: true
  replicas: 2

# Ruler (optional)
ruler:
  enabled: true
  replicas: 2

# Alertmanager (optional, Mimir built-in)
alertmanager:
  enabled: false

# Cache configuration
memcached:
  enabled: true

memcached-queries:
  enabled: true
  replicas: 2

memcached-metadata:
  enabled: true
  replicas: 2

# Minio (for testing, use S3 in production)
minio:
  enabled: false

# Structured configuration
mimir:
  structuredConfig:
    common:
      storage:
        backend: s3
        s3:
          endpoint: s3.ap-northeast-2.amazonaws.com
          region: ap-northeast-2
          bucket_name: my-mimir-bucket

    limits:
      ingestion_rate: 100000
      ingestion_burst_size: 200000
      max_global_series_per_user: 5000000
      compactor_blocks_retention_period: 365d

    blocks_storage:
      tsdb:
        dir: /data/tsdb
      bucket_store:
        sync_dir: /data/tsdb-sync

    compactor:
      data_dir: /data/compactor
```

## Configuración del backend S3

### Configuración de IRSA

```bash
# Check OIDC provider
aws eks describe-cluster --name my-cluster --query "cluster.identity.oidc.issuer" --output text

# Create IAM policy
cat <<EOF > mimir-s3-policy.json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::my-mimir-bucket",
                "arn:aws:s3:::my-mimir-bucket/*"
            ]
        }
    ]
}
EOF

aws iam create-policy \
  --policy-name MimirS3Policy \
  --policy-document file://mimir-s3-policy.json

# Create service account
eksctl create iamserviceaccount \
  --name mimir \
  --namespace monitoring \
  --cluster my-cluster \
  --attach-policy-arn arn:aws:iam::123456789012:policy/MimirS3Policy \
  --approve
```

### Configuración del bucket S3

```yaml
# Mimir S3 configuration
mimir:
  structuredConfig:
    common:
      storage:
        backend: s3
        s3:
          endpoint: s3.ap-northeast-2.amazonaws.com
          region: ap-northeast-2
          bucket_name: my-mimir-bucket
          # access_key and secret_key not needed with IRSA

    blocks_storage:
      s3:
        bucket_name: my-mimir-bucket

    ruler_storage:
      s3:
        bucket_name: my-mimir-bucket

    alertmanager_storage:
      s3:
        bucket_name: my-mimir-bucket
```

### Política de ciclo de vida del bucket S3

```json
{
  "Rules": [
    {
      "ID": "CleanupIncompleteMultipartUploads",
      "Status": "Enabled",
      "Filter": {},
      "AbortIncompleteMultipartUpload": {
        "DaysAfterInitiation": 7
      }
    },
    {
      "ID": "TransitionToIA",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "blocks/"
      },
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "STANDARD_IA"
        }
      ]
    }
  ]
}
```

## Consultas y retención de datos

### Configuración de la política de retención

```yaml
mimir:
  structuredConfig:
    limits:
      # Block retention period
      compactor_blocks_retention_period: 365d

    compactor:
      # Deletion delay (recovery time for mistakes)
      deletion_delay: 12h
```

### Configuración de optimización de consultas

```yaml
mimir:
  structuredConfig:
    query_frontend:
      # Query splitting
      split_queries_by_interval: 24h
      # Query step alignment
      align_querier_with_step: true
      # Result caching
      cache_results: true
      results_cache:
        backend: memcached
        memcached:
          addresses: dns+memcached:11211
          timeout: 500ms

    querier:
      # Concurrent queries
      max_concurrent: 20
      # Query timeout
      timeout: 2m
      # Ingester query range
      query_ingesters_within: 13h

    limits:
      # Maximum samples per query
      max_fetched_samples_per_query: 50000000
      # Query range limit
      max_query_length: 30d
      # Maximum query parallelism
      max_query_parallelism: 32
```

### Estrategia de caché de consultas

```mermaid
flowchart LR
    Q[Query] --> QF[Query-frontend]
    QF --> RC{Result Cache?}
    RC -->|Hit| R1[Cached Result]
    RC -->|Miss| QR[Querier]
    QR --> MC{Metadata<br/>Cache?}
    MC -->|Hit| M1[Cached Metadata]
    MC -->|Miss| SG[Store-gateway]
    SG --> CC{Chunk Cache?}
    CC -->|Hit| C1[Cached Chunk]
    CC -->|Miss| S3[S3]

    classDef cache fill:#27AE60,stroke:#333,stroke-width:1px,color:white
    classDef component fill:#F46800,stroke:#333,stroke-width:1px,color:white
    classDef storage fill:#4285F4,stroke:#333,stroke-width:1px,color:white

    class RC,MC,CC cache
    class Q,QF,QR,SG component
    class R1,M1,C1,S3 storage
```

## Comparación con VictoriaMetrics

### Comparación detallada

| Elemento | Grafana Mimir | VictoriaMetrics |
|------|---------------|-----------------|
| **Licencia** | AGPL v3 | Apache 2.0 |
| **Arquitectura** | Microservices | Monolítica/Cluster |
| **Almacenamiento** | Object Storage obligatorio | Disco local posible |
| **Complejidad operativa** | Alta | Baja-media |
| **Lenguaje de consulta** | PromQL | MetricsQL (superconjunto) |
| **Multi-tenancy** | Nativa | Compatible |
| **Compresión** | Buena | Muy buena |
| **Eficiencia de memoria** | Media | Alta |
| **Comunidad** | Grafana Labs | Código abierto activo |
| **Soporte comercial** | Grafana Cloud | VictoriaMetrics Inc. |

### Criterios de selección

```mermaid
flowchart TD
    A[Metrics Storage Selection] --> B{Grafana ecosystem<br/>centric?}

    B -->|Yes| C{Need enterprise<br/>multi-tenancy?}
    B -->|No| D{Operational simplicity<br/>priority?}

    C -->|Yes| E[Mimir]
    C -->|No| F{Want to use<br/>object storage?}

    D -->|Yes| G[VictoriaMetrics]
    D -->|No| H{Cloud storage<br/>cost?}

    F -->|Yes| E
    F -->|No| G

    H -->|Cost important| G
    H -->|Scalability important| E

    classDef decision fill:#F8B52A,stroke:#333,stroke-width:1px,color:black
    classDef solution fill:#3498DB,stroke:#333,stroke-width:1px,color:white

    class A,B,C,D,F,H decision
    class E,G solution
```

**Elija Mimir cuando**:
- Utilice Grafana Cloud o el ecosistema de Grafana
- Necesite multi-tenancy de nivel empresarial
- Quiera aprovechar Object Storage
- Pueda gestionar un entorno operativo complejo

**Elija VictoriaMetrics cuando**:
- Prefiera un entorno operativo sencillo
- Prefiera almacenamiento basado en disco local
- La máxima compresión y el rendimiento sean importantes
- La eficiencia de costos sea prioritaria

## Ajuste de rendimiento

### Ajuste de Ingester

```yaml
ingester:
  ring:
    replication_factor: 3
  instance_limits:
    max_series: 5000000
    max_inflight_push_requests: 30000

blocks_storage:
  tsdb:
    block_ranges_period: [2h]
    retention_period: 24h
    head_compaction_interval: 15m
    head_compaction_concurrency: 4
    wal_compression_enabled: true
```

### Ajuste de Store-gateway

```yaml
blocks_storage:
  bucket_store:
    sync_interval: 15m
    max_chunk_pool_bytes: 2147483648  # 2GB
    chunk_pool_min_bucket_size_bytes: 16384
    chunk_pool_max_bucket_size_bytes: 524288

    index_cache:
      backend: memcached
      memcached:
        addresses: dns+memcached:11211
        max_item_size: 5242880  # 5MB
        timeout: 450ms

    chunks_cache:
      backend: memcached
      memcached:
        addresses: dns+memcached:11211
        max_item_size: 1048576  # 1MB
        timeout: 450ms
```

### Ajuste de consultas

```yaml
query_frontend:
  parallelize_shardable_queries: true
  split_queries_by_interval: 24h
  max_retries: 5

  query_sharding:
    enabled: true
    total_shards: 16

querier:
  max_concurrent: 20
  timeout: 2m
```

## Prácticas recomendadas

### Lista de verificación para producción

1. **Alta disponibilidad**
   - Ingester: mínimo 3, replicación con reconocimiento de zona
   - Store-gateway: mínimo 2
   - Distributor: mínimo 2
   - Query-frontend: mínimo 2

2. **Caché**
   - Caché de resultados: memcached
   - Caché de metadatos: memcached
   - Caché de chunks: memcached

3. **Monitoreo**
   ```promql
   # Mimir self metrics
   cortex_ingester_active_series
   cortex_distributor_received_samples_total
   cortex_querier_request_duration_seconds
   cortex_compactor_runs_completed_total
   ```

4. **Reglas de alerta**
   ```yaml
   groups:
   - name: mimir
     rules:
     - alert: MimirIngesterUnhealthy
       expr: cortex_ring_members{state="Unhealthy"} > 0
       for: 5m
       labels:
         severity: critical

     - alert: MimirCompactorFailed
       expr: increase(cortex_compactor_runs_failed_total[1h]) > 0
       for: 5m
       labels:
         severity: warning
   ```

### Optimización de costos

```yaml
# Use S3 storage classes
blocks_storage:
  s3:
    storage_class: INTELLIGENT_TIERING

# Filter unnecessary metrics
limits:
  drop_labels:
    - pod_template_hash
    - controller_revision_hash

# Downsampling (Enterprise)
compactor:
  downsampling_enabled: true
```

## Solución de problemas

### Problemas comunes

#### 1. OOM de Ingester

```bash
# Check memory usage
kubectl top pod -l app.kubernetes.io/component=ingester -n monitoring

# Solution: Adjust time series limit
ingester:
  instance_limits:
    max_series: 3000000  # Reduce
```

#### 2. Timeout de consulta

```bash
# Check slow queries
curl http://query-frontend:8080/api/v1/status/buildinfo

# Solution: Query splitting and parallelization
query_frontend:
  split_queries_by_interval: 12h  # Smaller
  query_sharding:
    total_shards: 32  # Increase
```

#### 3. Retraso de Compactor

```bash
# Check Compactor status
curl http://compactor:8080/compactor/ring

# Solution: Increase resources
compactor:
  resources:
    limits:
      cpu: 4000m
      memory: 16Gi
```

### Comandos de depuración

```bash
# Check component status
curl http://distributor:8080/distributor/all_user_stats
curl http://ingester:8080/ingester/ring
curl http://store-gateway:8080/store-gateway/ring
curl http://compactor:8080/compactor/ring

# Check metrics
curl http://distributor:8080/metrics | grep cortex_
curl http://ingester:8080/metrics | grep cortex_

# Check configuration
curl http://distributor:8080/config
```

## Referencias

- [Documentación oficial de Grafana Mimir](https://grafana.com/docs/mimir/latest/)
- [Mimir GitHub](https://github.com/grafana/mimir)
- [Chart Helm de mimir-distributed](https://github.com/grafana/mimir/tree/main/operations/helm/charts/mimir-distributed)
- [Arquitectura de Mimir](https://grafana.com/docs/mimir/latest/references/architecture/)

## Cuestionario

Para comprobar su comprensión de este capítulo, pruebe el [Cuestionario de Grafana Mimir](../../quizzes/observability/metrics/03-mimir-quiz.md).
