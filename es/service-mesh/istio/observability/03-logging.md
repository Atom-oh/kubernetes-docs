# Registros de Istio

> **Versiones compatibles**: Istio 1.31
> **Última actualización**: 11 de septiembre de 2026

> **Alcance de validación**: Configuraciones de laboratorio verificadas con referencias oficiales y validadores offline, sin desplegar clúster. Los supuestos de namespace, identidad, almacenamiento, backend y carga se indican por ejemplo y deben verificarse para el destino.

Los logs de acceso configurados registran metadatos de solicitudes/conexiones observadas. Son distintos de diagnósticos Envoy/istiod y logs de aplicación; no capturan toda actividad de malla ni cuerpos completos. Los ejemplos usan sidecars; logs L7 ambient necesitan waypoint, mientras ztunnel tiene logs L4 separados.

## Índice

1. [Descripción de logs](#logging-overview)
2. [Configuración de acceso](#access-log-configuration)
3. [Personalización con Telemetry API](#log-customization-with-telemetry-api)
4. [Filtrado y muestreo](#log-filtering-and-sampling)
5. [Ajustar nivel Envoy](#envoy-log-level-adjustment)
6. [Integración Alloy + Loki](#alloy--loki-integration)
7. [Dashboard de logs Grafana](#grafana-log-dashboard)
8. [Integración con métricas/trazas](#log-integration-with-metricstraces)
9. [Optimización](#performance-optimization)
10. [Resolución de problemas](#troubleshooting)

## Descripción de logs {#logging-overview}

### Capas de logs Istio

Envoy → stdout estructurado → recogida Kubernetes Alloy → Loki → Grafana. Como alternativa, un proveedor OTLP de acceso Envoy envía a OpenTelemetry Collector. Elija una ruta de entrega por log para evitar duplicados. Istiod distribuye ajustes Telemetry/proveedor seleccionados.

### Tipos de logs

1. **Acceso**: Metadatos HTTP o de conexión TCP configurados
2. **Proxy Envoy**: Operación interna de Envoy
3. **Istiod**: Logs del plano de control
4. **Aplicación**: Logs propios de la aplicación

## Configuración de acceso {#access-log-configuration}

### 1. Definir un proveedor de logs de acceso

Combine una definición de proveedor siguiente con la instalación existente mediante `istioctl install -f logging-install.yaml`. Conserve otros ajustes/proveedores. Son entradas de instalación, no recursos Kubernetes IstioOperator. Seleccione el proveedor instalado con Telemetry; texto y JSON son alternativas.

#### Formato de texto básico

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: logging
spec:
  meshConfig:
    extensionProviders:
    - name: mesh-text
      envoyFileAccessLog:
        path: /dev/stdout
        logFormat:
          text: '[%START_TIME%] "%REQ(:METHOD)% %REQ_WITHOUT_QUERY(:PATH)% %PROTOCOL%" %RESPONSE_CODE%
            %RESPONSE_FLAGS% %DURATION% trace=%TRACE_ID% request=%REQ(X-REQUEST-ID)%'
```

#### Formato JSON usado por los ejemplos Loki

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: logging
spec:
  meshConfig:
    extensionProviders:
    - name: mesh-json
      envoyFileAccessLog:
        path: /dev/stdout
        logFormat:
          labels:
            log_type: access
            start_time: '%START_TIME%'
            method: '%REQ(:METHOD)%'
            path: '%REQ_WITHOUT_QUERY(X-ENVOY-ORIGINAL-PATH?:PATH)%'
            protocol: '%PROTOCOL%'
            response_code: '%RESPONSE_CODE%'
            response_code_details: '%RESPONSE_CODE_DETAILS%'
            response_flags: '%RESPONSE_FLAGS%'
            bytes_received: '%BYTES_RECEIVED%'
            bytes_sent: '%BYTES_SENT%'
            duration: '%DURATION%'
            request_id: '%REQ(X-REQUEST-ID)%'
            trace_id: '%TRACE_ID%'
            authority: '%REQ(:AUTHORITY)%'
            upstream_host: '%UPSTREAM_HOST%'
            upstream_cluster: '%UPSTREAM_CLUSTER%'
            route_name: '%ROUTE_NAME%'
            downstream_tls_version: '%DOWNSTREAM_TLS_VERSION%'
            peer_uri_san: '%DOWNSTREAM_PEER_URI_SAN%'
```

El formato crea campos JSON; el filtro Telemetry selecciona eventos. `duration` es milisegundos en el log, mientras CEL `request.duration` es un valor de duración. `trace_id` es el ID activo real cuando hay trazado; `request_id` correlaciona solicitudes separadamente. Se omiten query strings; revise cabeceras adicionales antes de registrarlas.

Las actualizaciones se entregan en configuración de proxy; reiniciar todo istiod/cargas no es el paso normal. Revise listeners efectivos y una solicitud de prueba. Los cambios bootstrap de nivel de log posteriores necesitan rollout de proxies seleccionados.

### 2. Control fino con Telemetry API

Telemetry selecciona logs por namespace/carga. Los ejemplos son alternativas: combine ajustes en un solo recurso sin selector por namespace. Se usa SERVER para acceso entrante, evitando duplicar saltos cliente/servidor. Gateway/salida pueden usar CLIENT aparte y no deben mezclarse en tasas de servicio. Con `mesh-text`, selecciónelo en vez de `mesh-json`.

#### Habilitar acceso JSON en toda la malla

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: mesh-logging
  namespace: istio-system
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
```

#### Configuración por namespace

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: production-logging
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    # Log only errors and slow requests
    filter:
      expression: |
        response.code >= 400 ||
        request.duration > duration("1s")
```

#### Logs detallados por carga

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: payment-service-logging
  namespace: production
spec:
  selector:
    matchLabels:
      app: payment-service
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    # Log all requests + additional custom fields
    filter:
      expression: "true"
```

## Personalización con Telemetry API {#log-customization-with-telemetry-api}

### Proveedor personalizado

#### 1. Enviar logs por OpenTelemetry

Alternativa a recoger los mismos logs stdout con Alloy. Instale el proveedor y selecciónelo en Telemetry de namespace:

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: logging
spec:
  meshConfig:
    extensionProviders:
    - name: otel-logging
      envoyOtelAls:
        service: otel-collector.observability.svc.cluster.local
        port: 4317
        logFormat:
          text: '%REQ(:METHOD)% %REQ_WITHOUT_QUERY(:PATH)% %RESPONSE_CODE%'
          labels:
            log_type: access
            start_time: '%START_TIME%'
            method: '%REQ(:METHOD)%'
            path: '%REQ_WITHOUT_QUERY(X-ENVOY-ORIGINAL-PATH?:PATH)%'
            protocol: '%PROTOCOL%'
            response_code: '%RESPONSE_CODE%'
            response_code_details: '%RESPONSE_CODE_DETAILS%'
            response_flags: '%RESPONSE_FLAGS%'
            bytes_received: '%BYTES_RECEIVED%'
            bytes_sent: '%BYTES_SENT%'
            duration: '%DURATION%'
            request_id: '%REQ(X-REQUEST-ID)%'
            trace_id: '%TRACE_ID%'
            authority: '%REQ(:AUTHORITY)%'
            upstream_host: '%UPSTREAM_HOST%'
            upstream_cluster: '%UPSTREAM_CLUSTER%'
            route_name: '%ROUTE_NAME%'
            downstream_tls_version: '%DOWNSTREAM_TLS_VERSION%'
            peer_uri_san: '%DOWNSTREAM_PEER_URI_SAN%'
```

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: otel-access-logging
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: otel-logging
```

El Collector de la [guía de trazas](02-tracing.md) ya define receptor OTLP, limitador de memoria y batch. Combine este pipeline/exporter de logs y recargue/redespliegue. Loki 3.7.7 acepta OTLP/HTTP en `/otlp/v1/logs`; el exporter añade `/v1/logs`. TSDB v13 soporta metadatos estructurados. Los atributos OTLP pasan a metadatos, no cuerpo JSON stdout, así que adapte consultas en vez de copiar `| json` ciegamente.

```yaml
exporters:
  otlp_http/loki:
    endpoint: http://loki.observability.svc.cluster.local:3100/otlp
service:
  pipelines:
    logs:
      receivers:
      - otlp
      processors:
      - memory_limiter
      - batch
      exporters:
      - otlp_http/loki
```

#### 2. Logs en archivo y volumen compartido

Una ruta de archivo del proveedor no crea ni monta un volumen. El Pod opcional monta `emptyDir` acotado en el proxy inyectado; sustituya la imagen de aplicación. Otro lector debe montar el mismo volumen y gestionar rotación/envío. `kubectl logs` no devuelve esos archivos y `emptyDir` desaparece con el Pod. El ejemplo principal usa stdout.

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: logging
spec:
  meshConfig:
    extensionProviders:
    - name: envoy-file-logger
      envoyFileAccessLog:
        path: /var/log/istio/access.log
        logFormat:
          labels:
            log_type: access
            start_time: '%START_TIME%'
            method: '%REQ(:METHOD)%'
            path: '%REQ_WITHOUT_QUERY(X-ENVOY-ORIGINAL-PATH?:PATH)%'
            protocol: '%PROTOCOL%'
            response_code: '%RESPONSE_CODE%'
            response_code_details: '%RESPONSE_CODE_DETAILS%'
            response_flags: '%RESPONSE_FLAGS%'
            bytes_received: '%BYTES_RECEIVED%'
            bytes_sent: '%BYTES_SENT%'
            duration: '%DURATION%'
            request_id: '%REQ(X-REQUEST-ID)%'
            trace_id: '%TRACE_ID%'
            authority: '%REQ(:AUTHORITY)%'
            upstream_host: '%UPSTREAM_HOST%'
            upstream_cluster: '%UPSTREAM_CLUSTER%'
            route_name: '%ROUTE_NAME%'
            downstream_tls_version: '%DOWNSTREAM_TLS_VERSION%'
            peer_uri_san: '%DOWNSTREAM_PEER_URI_SAN%'
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: file-logging-example
  namespace: production
  labels:
    app: file-logging-example
  annotations:
    sidecar.istio.io/inject: 'true'
    sidecar.istio.io/userVolumeMount: '[{"name":"istio-logs","mountPath":"/var/log/istio"}]'
spec:
  securityContext:
    fsGroup: 1337
  containers:
  - name: app
    image: registry.example.com/team/app:REPLACE_WITH_TESTED_TAG
  volumes:
  - name: istio-logs
    emptyDir:
      sizeLimit: 100Mi
---
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: file-logging
  namespace: production
spec:
  selector:
    matchLabels:
      app: file-logging-example
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: envoy-file-logger
```

### Personalizar formato

#### Filtrado de eventos con CEL

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: custom-log-format
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: "true"
```

**Variables disponibles**:

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `request.method` | Método HTTP | GET, POST |
| `request.path` | Ruta de solicitud | /api/v1/users |
| `request.url_path` | Ruta sin query | /api/v1/users |
| `request.headers` | Cabeceras de solicitud | `request.headers['user-agent']` |
| `response.code` | Código HTTP | 200, 404, 500 |
| `response.headers` | Cabeceras de respuesta | `response.headers['content-type']` |
| `response.flags` | Máscara de bits entera | `response.flags != 0` |
| `request.duration` | Valor de duración | `duration("1s")` |
| `connection.mtls` | Uso de mTLS | true, false |
| `connection.uri_san_peer_certificate` | URI SAN del peer downstream, si existe | spiffe://... |
| `connection.uri_san_local_certificate` | URI SAN del certificado local downstream | spiffe://... |

## Filtrado y muestreo {#log-filtering-and-sampling}

### 1. Logs condicionales

#### Solo errores y solicitudes lentas

Los filtros HTTP aplican a HTTP. Para TCP use atributos de conexión o una expresión protegida ante campos HTTP ausentes. CEL selecciona eventos; no define formato de campos JSON.

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: error-slow-logging
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: |
        response.code >= 400 ||
        response.code == 0 ||
        request.duration > duration("1s")
```

#### Excluir rutas concretas

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: filter-health-checks
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: |
        !(request.url_path.startsWith('/health') ||
          request.url_path.startsWith('/ready') ||
          request.url_path.startsWith('/live') ||
          request.url_path == '/metrics')
```

#### Filtrar por método HTTP

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: critical-methods-only
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: |
        request.method in ['POST', 'PUT', 'DELETE', 'PATCH']
```

#### Solo tráfico sin mTLS para auditoría

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: non-mtls-logging
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: |
        !connection.mtls
```

### 2. Muestreo en el collector

Use `stage.sampling` admitido por Alloy; Telemetry CEL no documenta una función `random()` de muestreo. Añada esta etapa dentro de `loki.process` para retener uniformemente 10%:

```alloy
stage.sampling {
  rate = 0.1
  drop_counter_reason = "uniform_sampling"
}
```

Para conservar 1% de accesos exitosos inferiores a un segundo, manteniendo errores/lentos/no clasificados, analice enteros JSON, clasifique con etiquetas temporales, muestree y quite etiquetas antes de escribir. Sustituya las etapas principales por esta alternativa conservando `forward_to`:

```alloy
stage.json {
  expressions = { log_type = "log_type", response_code = "response_code", duration = "duration" }
}
stage.labels {
  values = { log_type = "log_type", sample_status = "response_code", sample_duration_ms = "duration" }
}
stage.match {
  selector = "{log_type=\"access\", sample_status=~\"[123][0-9]{2}\", sample_duration_ms=~\"[0-9]{1,3}\"}"
  stage.sampling {
    rate = 0.01
    drop_counter_reason = "normal_access_sampled"
  }
}
stage.label_drop {
  values = ["sample_status", "sample_duration_ms"]
}
```

`stage.match` admite selectores de flujo y filtros de línea, no un pipeline completo LogQL de etiquetas. La etiqueta temporal duration nunca llega a Loki. Muestrear en collector reduce ingesta/almacenamiento, no generación en proxy. Conteos, cuantiles y ratios retenidos están sesgados; use métricas Istio sin muestrear para SLI totales. Los dashboards/alertas siguientes requieren acceso sin muestreo.

### 3. Logs diferenciados por namespace

```yaml
# Production: Log only errors
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: production-logging
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: "response.code >= 400"
---
# Staging: Log all requests
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: staging-logging
  namespace: staging
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: "true"
---
# Development: Disable logging
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: dev-logging
  namespace: development
spec:
  accessLogging:
  - disabled: true
```

## Ajustar nivel de log Envoy {#envoy-log-level-adjustment}

### Cambiar nivel dinámicamente

#### Nivel global Envoy

```bash
# Change to Debug level
istioctl proxy-config log <pod-name> -n <namespace> --level debug

# Restore to Info level
istioctl proxy-config log <pod-name> -n <namespace> --level info

# Change to Warning level
istioctl proxy-config log <pod-name> -n <namespace> --level warning
```

#### Nivel por componente

```bash
# Debug HTTP connections only
istioctl proxy-config log <pod-name> -n <namespace> --level http:debug

# Debug Router and Connection components only
istioctl proxy-config log <pod-name> -n <namespace> --level router:debug,connection:debug

# Multiple component combinations
istioctl proxy-config log <pod-name> -n <namespace> \
  --level http:debug,router:info,upstream:debug,connection:trace
```

Use `istioctl proxy-config log <pod-name> -n <namespace>` para listar componentes de esa versión; no todo build expone todos los ejemplos.

### Componentes de log Envoy

| Componente | Descripción | Uso |
|-----------|-------------|----------|
| `admin` | Interfaz administrativa | Depuración API admin |
| `aws` | Integración AWS | Problemas de servicios AWS |
| `connection` | Conexiones TCP | Diagnóstico de conexiones |
| `filter` | Filtros HTTP | Análisis de cadena |
| `forward_proxy` | Proxy directo | Seguimiento de comportamiento |
| `grpc` | gRPC | Problemas de comunicación |
| `hc` | Comprobaciones de salud | Fallos de probes |
| `http` | HTTP | Seguimiento de solicitudes/respuestas |
| `http2` | HTTP/2 | Problemas de protocolo |
| `jwt` | Autenticación JWT | Verificación de tokens |
| `lua` | Scripts Lua | Depuración de filtros |
| `main` | Lógica principal | Operación general Envoy |
| `router` | Enrutamiento | Decisiones de ruta |
| `runtime` | Configuración runtime | Cambios dinámicos |
| `upstream` | Clústeres upstream | Conexión backend |
| `client` | Cliente HTTP | Solicitudes salientes |
| `pool` | Pool de conexiones | Gestión del pool |
| `rbac` | Filtro RBAC | Problemas de permisos |

### Configuración persistente de nivel

Combine values de instalación y despliegue proxies seleccionados; antes de cambios temporales inspeccione niveles existentes y restáurelos después. Los niveles no activan logs de acceso.

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: proxy-log-levels
spec:
  values:
    global:
      proxy:
        logLevel: info
        componentLogLevel: http:debug,router:info,upstream:debug
```

### Debug solo para una carga

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-app
  annotations:
    sidecar.istio.io/componentLogLevel: "http:debug,router:debug"
    sidecar.istio.io/logLevel: "debug"
spec:
  containers:
  - name: app
    image: registry.example.com/team/my-app:REPLACE_WITH_TESTED_TAG
```



## Integración Alloy + Loki {#alloy--loki-integration}

Promtail llegó al fin de vida el **2 de marzo de 2026**. Use Alloy u otro cliente admitido en despliegues nuevos. El ejemplo sustituye file-tail Promtail por recogida API Kubernetes de Alloy; no necesita rutas Docker, contenedores privilegiados ni montajes del sistema de archivos del nodo.

### 1. Instalar Loki en binario único

Es un ejemplo nuevo, de una réplica y tenant, con Loki 3.7.7, TSDB v13 y filesystem. Es **binario único**, no Simple Scalable. Cree `observability` primero. En EKS debe existir StorageClass `gp3` con EBS CSI funcional; en otras plataformas use su clase persistente. Fargate no monta EBS: ejecute Loki en nodos EC2 adecuados o use servicio externo compatible.

Con `auth_enabled: false`, acceso de red da acceso a logs del tenant. Mantenga endpoints privados y configure gateway de autenticación/TLS admitido en producción. Conserve entradas históricas del esquema al actualizar; la fecha inicial 2024 siguiente es válida, no fecha de release. La retención Compactor exige estado persistente y `delete_request_store`.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: loki-config
  namespace: observability
data:
  loki.yaml: |
    auth_enabled: false
    server:
      http_listen_port: 3100
      grpc_listen_port: 9096
    common:
      path_prefix: /loki
      storage:
        filesystem:
          chunks_directory: /loki/chunks
          rules_directory: /loki/rules
      replication_factor: 1
      ring:
        kvstore:
          store: inmemory
    schema_config:
      configs:
      - from: 2024-01-01
        store: tsdb
        object_store: filesystem
        schema: v13
        index:
          prefix: index_
          period: 24h
    limits_config:
      retention_period: 168h
      ingestion_rate_mb: 16
      ingestion_burst_size_mb: 32
      max_query_length: 721h
      max_query_lookback: 721h
      max_streams_per_user: 10000
      max_global_streams_per_user: 0
      reject_old_samples: true
      reject_old_samples_max_age: 168h
    compactor:
      working_directory: /loki/compactor
      compaction_interval: 10m
      retention_enabled: true
      retention_delete_delay: 2h
      retention_delete_worker_count: 150
      delete_request_store: filesystem
    querier:
      max_concurrent: 4
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: loki
  namespace: observability
spec:
  serviceName: loki-headless
  replicas: 1
  selector:
    matchLabels:
      app: loki
  template:
    metadata:
      labels:
        app: loki
        sidecar.istio.io/inject: 'false'
    spec:
      containers:
      - name: loki
        image: grafana/loki:3.7.7
        args:
        - -config.file=/etc/loki/loki.yaml
        ports:
        - containerPort: 3100
          name: http
        - containerPort: 9096
          name: grpc
        volumeMounts:
        - name: config
          mountPath: /etc/loki
        - name: storage
          mountPath: /loki
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 4Gi
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          initialDelaySeconds: 10
          periodSeconds: 10
      volumes:
      - name: config
        configMap:
          name: loki-config
      securityContext:
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001
        runAsNonRoot: true
  volumeClaimTemplates:
  - metadata:
      name: storage
    spec:
      accessModes:
      - ReadWriteOnce
      resources:
        requests:
          storage: 100Gi
      storageClassName: gp3
---
apiVersion: v1
kind: Service
metadata:
  name: loki
  namespace: observability
spec:
  selector:
    app: loki
  ports:
  - name: http
    port: 3100
    targetPort: 3100
  - name: grpc
    port: 9096
    targetPort: 9096
  type: ClusterIP
---
apiVersion: v1
kind: Service
metadata:
  name: loki-headless
  namespace: observability
spec:
  clusterIP: None
  selector:
    app: loki
  ports:
  - name: http
    port: 3100
    targetPort: http
```

### 2. Recoger logs Pod con Alloy

Cree namespaces de aplicación antes de aplicar RoleBindings, o limite descubrimiento y bindings a existentes. Alloy solo lee metadatos y `pods/log` en esos namespaces. La fuente API ya recibe contenido sin envoltura CRI/Docker; una fuente de archivos necesita parsing runtime y rutas locales de nodo.

Una réplica recoge logs sidecar, istiod y aplicación excluyendo init containers. Solo etiqueta namespace/pod/container/app/version y `log_type` acotado; request IDs, trace IDs, rutas y duración son campos, no índices Loki. El proveedor JSON emite `log_type="access"`, distinguiendo accesos de diagnósticos en el mismo contenedor.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: alloy
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: alloy-pod-logs
rules:
- apiGroups:
  - ''
  resources:
  - pods
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - ''
  resources:
  - pods/log
  verbs:
  - get
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: alloy-pod-logs
  namespace: default
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: alloy-pod-logs
subjects:
- kind: ServiceAccount
  name: alloy
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: alloy-pod-logs
  namespace: app
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: alloy-pod-logs
subjects:
- kind: ServiceAccount
  name: alloy
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: alloy-pod-logs
  namespace: production
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: alloy-pod-logs
subjects:
- kind: ServiceAccount
  name: alloy
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: alloy-pod-logs
  namespace: staging
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: alloy-pod-logs
subjects:
- kind: ServiceAccount
  name: alloy
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: alloy-pod-logs
  namespace: istio-system
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: alloy-pod-logs
subjects:
- kind: ServiceAccount
  name: alloy
  namespace: observability
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: alloy-config
  namespace: observability
data:
  config.alloy: |
    discovery.kubernetes "pods" {
      role = "pod"
      namespaces {
        names = ["default", "app", "production", "staging", "istio-system"]
      }
    }

    discovery.relabel "logs" {
      targets = discovery.kubernetes.pods.targets
      rule {
        source_labels = ["__meta_kubernetes_pod_phase"]
        regex = "Running"
        action = "keep"
      }
      rule {
        source_labels = ["__meta_kubernetes_pod_container_name"]
        regex = "istio-init"
        action = "drop"
      }
      rule {
        source_labels = ["__meta_kubernetes_namespace"]
        target_label = "namespace"
      }
      rule {
        source_labels = ["__meta_kubernetes_pod_name"]
        target_label = "pod"
      }
      rule {
        source_labels = ["__meta_kubernetes_pod_container_name"]
        target_label = "container"
      }
      rule {
        source_labels = ["__meta_kubernetes_pod_label_app"]
        target_label = "app"
      }
      rule {
        source_labels = ["__meta_kubernetes_pod_label_version"]
        target_label = "version"
      }
    }

    loki.source.kubernetes "pods" {
      targets = discovery.relabel.logs.output
      forward_to = [loki.process.logs.receiver]
    }

    loki.process "logs" {
      stage.json {
        expressions = { log_type = "log_type" }
      }
      stage.labels {
        values = { log_type = "log_type" }
      }
      forward_to = [loki.write.local.receiver]
    }

    loki.write "local" {
      endpoint {
        url = "http://loki.observability.svc.cluster.local:3100/loki/api/v1/push"
        batch_wait = "1s"
        batch_size = "1MiB"
        min_backoff_period = "500ms"
        max_backoff_period = "5m"
        max_backoff_retries = 10
        remote_timeout = "10s"
      }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: alloy
  namespace: observability
spec:
  replicas: 1
  selector:
    matchLabels:
      app: alloy
  template:
    metadata:
      labels:
        app: alloy
        sidecar.istio.io/inject: 'false'
    spec:
      serviceAccountName: alloy
      containers:
      - name: alloy
        image: grafana/alloy:v1.19.2
        args:
        - run
        - --server.http.listen-addr=0.0.0.0:12345
        - --storage.path=/var/lib/alloy
        - /etc/alloy/config.alloy
        ports:
        - containerPort: 12345
          name: http-metrics
        volumeMounts:
        - name: config
          mountPath: /etc/alloy
          readOnly: true
        - name: state
          mountPath: /var/lib/alloy
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
      volumes:
      - name: config
        configMap:
          name: alloy-config
      - name: state
        emptyDir:
          sizeLimit: 256Mi
```

La ruta API evita restricciones DaemonSet para Pods Fargate, pero no recoge logs de nodo. Aumenta trabajo API/kubelet; instalaciones grandes deben evaluar recogida local o clustering Alloy con propiedad de targets coordinada. No añada simplemente réplicas idénticas que lean cada Pod. `emptyDir` y reintentos acotados no garantizan entrega sin pérdidas en reinicios/caídas; configure buffers/WAL persistentes y pruebe recuperación productiva.

### 3. Consultas LogQL

Usan proveedor JSON stdout y logs SERVER sin muestreo. Un selector de contenedor incluye diagnósticos; `log_type="access"` selecciona accesos. Las estadísticas HTTP excluyen métodos vacíos/`-`, pues logs de conexión TCP no son solicitudes HTTP. Compare números como números y use `__error__=""` para excluir errores de parsing/conversión antes de agregar.

#### Consultas básicas

```logql
{namespace="production"}

{app="payment-service"}

{container="istio-proxy",log_type="access"}

{namespace="production"} |~ "(?i)error"

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | response_code >= 500 | response_code < 600 | __error__=""
```

#### Filtrado avanzado

```logql
{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | method="POST" | __error__=""

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | duration > 1000 | __error__=""

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | response_flags=~".*UO.*" | __error__=""

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | response_flags=~".*URX.*" | __error__=""

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | downstream_tls_version=~"(-)?" | __error__=""

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | path=~"/api/v1/.*" | __error__=""
```

`UO` significa overflow upstream; `URX`, agotamiento de retry/intentos de conexión. `downstream_tls_version` distingue texto plano/TLS; `peer_uri_san` aporta identidad autenticada cuando existe. Ninguno es contador universal de fallos de handshake, que pueden ocurrir antes de un log HTTP. La consulta antigua `connection_security_policy` referenciaba una etiqueta métrica ausente de estos logs.

#### Agregación y estadísticas

```logql
sum by (namespace, app) (rate({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | __error__="" [5m]))

sum by (response_code) (count_over_time({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | __error__="" [5m]))

quantile_over_time(0.95, {container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | unwrap duration | __error__="" [5m]) by (namespace, app)

sum by (namespace, app) (rate({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | response_code >= 500 | response_code < 600 | __error__="" [5m])) / sum by (namespace, app) (rate({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | __error__="" [5m]))

avg_over_time({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | unwrap duration | __error__="" [5m]) by (namespace, app)
```

Describen entradas retenidas. Logging selectivo, muestreo, pérdidas, rutas distintas y logs gateway afectan al resultado; para SLO de todo el servicio use métricas estándar del capítulo correspondiente.

## Dashboard de logs Grafana {#grafana-log-dashboard}

### 1. Añadir datasource Loki

Monte el archivo bajo `provisioning/datasources` de Grafana o use provisioning admitido del chart. ConfigMap solo no se consume automáticamente. UID `tempo` debe referir a datasource existente. Se correlaciona con `trace_id` JSON; los UUID de solicitud no son trace IDs. IDs vacíos no crean enlaces.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: observability
data:
  loki.yaml: |
    apiVersion: 1
    datasources:
    - name: Loki
      uid: loki
      type: loki
      access: proxy
      url: http://loki.observability.svc.cluster.local:3100
      jsonData:
        maxLines: 1000
        derivedFields:
        - datasourceUid: tempo
          matcherRegex: '"trace_id"\s*:\s*"([0-9a-fA-F]{32})"'
          name: TraceID
          url: $${__value.raw}
          urlDisplayLabel: View trace
```

### 2. Dashboard de acceso Istio

#### JSON del dashboard

Importe el objeto o móntelo con un proveedor. Es archivo dashboard, no wrapper HTTP API. Deben existir UID `loki` y `prometheus`; alinee etiqueta log `app` con canonical-service de métricas. El heatmap usa buckets Prometheus reales; duraciones brutas de logs no contienen etiqueta bucket `le`.

```json
{
  "title": "Istio Access Logs",
  "tags": [
    "istio",
    "logs"
  ],
  "timezone": "browser",
  "panels": [
    {
      "title": "Logged HTTP Request Rate",
      "type": "timeseries",
      "targets": [
        {
          "expr": "sum by (namespace, app) (rate({container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | __error__=\"\" [5m]))",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 0
      },
      "id": 1,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "Response Code Distribution",
      "type": "piechart",
      "targets": [
        {
          "expr": "sum by (response_code) (count_over_time({container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | __error__=\"\" [5m]))",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 0
      },
      "id": 2,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "P50/P95/P99 Latency",
      "type": "timeseries",
      "targets": [
        {
          "expr": "quantile_over_time(0.5, {container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | unwrap duration | __error__=\"\" [5m]) by (namespace, app)",
          "legendFormat": "P50",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        },
        {
          "expr": "quantile_over_time(0.95, {container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | unwrap duration | __error__=\"\" [5m]) by (namespace, app)",
          "legendFormat": "P95",
          "refId": "B",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        },
        {
          "expr": "quantile_over_time(0.99, {container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | unwrap duration | __error__=\"\" [5m]) by (namespace, app)",
          "legendFormat": "P99",
          "refId": "C",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 24,
        "x": 0,
        "y": 8
      },
      "id": 3,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "HTTP Error Fraction in Retained Logs",
      "type": "stat",
      "targets": [
        {
          "expr": "sum by (namespace, app) (rate({container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | response_code >= 500 | response_code < 600 | __error__=\"\" [5m])) / sum by (namespace, app) (rate({container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | __error__=\"\" [5m]))",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 4,
        "w": 6,
        "x": 0,
        "y": 16
      },
      "id": 4,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "Top 10 Routes by Average Logged Duration",
      "type": "table",
      "targets": [
        {
          "expr": "topk(10, avg_over_time({container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | unwrap duration | __error__=\"\" [5m]) by (namespace, app, route_name, method))",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 20
      },
      "id": 5,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "Error Logs",
      "type": "logs",
      "targets": [
        {
          "expr": "{container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | response_code >= 400 | __error__=\"\"",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 20
      },
      "id": 6,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "Upstream Overflow Events",
      "type": "logs",
      "targets": [
        {
          "expr": "{container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | response_flags=~\".*UO.*\" | __error__=\"\"",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 24,
        "x": 0,
        "y": 28
      },
      "id": 7,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "HTTP Duration Histogram (Prometheus)",
      "type": "heatmap",
      "targets": [
        {
          "expr": "sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter=\"destination\",destination_workload_namespace=\"$namespace\",destination_canonical_service=\"$service\"}[5m]))",
          "format": "heatmap",
          "refId": "A",
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 24,
        "x": 0,
        "y": 36
      },
      "id": 8,
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      }
    }
  ],
  "templating": {
    "list": [
      {
        "name": "namespace",
        "type": "query",
        "query": "label_values({container=\"istio-proxy\"}, namespace)",
        "datasource": {
          "type": "loki",
          "uid": "loki"
        }
      },
      {
        "name": "service",
        "type": "query",
        "query": "label_values({container=\"istio-proxy\", namespace=\"$namespace\"}, app)",
        "datasource": {
          "type": "loki",
          "uid": "loki"
        }
      }
    ]
  },
  "uid": "istio-access-logs"
}
```

### 3. Alertas Loki Ruler

YAML `groups`/`alert`/`expr` de estilo Prometheus configura Loki ruler. Alertas gestionadas por Grafana usan su UID, condición y formato query-data; expórtelas desde Grafana si elige esa vía. Para ruler, cree ConfigMap, combine ajustes en `loki.yaml` y volúmenes en StatefulSet existente conservando montajes de configuración/almacenamiento. Debe existir Alertmanager en la dirección configurada.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: loki-rules
  namespace: observability
data:
  istio-logging-alerts.yaml: |
    groups:
    - name: istio-logging-alerts
      interval: 1m
      rules:
      - alert: HighHTTPErrorFractionInLogs
        expr: sum by (namespace, app) (rate({container="istio-proxy",log_type="access"} | json | method!=""
          | method!="-" | response_code >= 500 | response_code < 600 | __error__="" [5m])) / sum by (namespace,
          app) (rate({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | __error__=""
          [5m])) > 0.05
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: Retained HTTP logs show more than 5% server errors
      - alert: CircuitBreakerOverflow
        expr: sum by (namespace, app) (count_over_time({container="istio-proxy",log_type="access"} | json
          | method!="" | method!="-" | response_flags=~".*UO.*" | __error__="" [1m])) > 10
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: Upstream overflow events in access logs
      - alert: SlowLoggedRequests
        expr: quantile_over_time(0.95, {container="istio-proxy",log_type="access"} | json | method!="" | method!="-"
          | unwrap duration | __error__="" [5m]) by (namespace, app) > 2000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: P95 of logged HTTP durations exceeds 2000ms
      - alert: PlaintextHTTPObserved
        expr: sum by (namespace, app) (count_over_time({container="istio-proxy",log_type="access"} | json
          | method!="" | method!="-" | downstream_tls_version=~"(-)?" | __error__="" [5m])) > 0
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: HTTP access logs show a plaintext downstream connection
```

```yaml
ruler:
  storage:
    type: local
    local:
      directory: /etc/loki/rules
  rule_path: /loki/ruler-scratch
  alertmanager_url: http://alertmanager.observability.svc.cluster.local:9093
  ring:
    kvstore:
      store: inmemory
  enable_api: true
```

```yaml
spec:
  template:
    spec:
      containers:
      - name: loki
        volumeMounts:
        - name: loki-rules
          mountPath: /etc/loki/rules
          readOnly: true
      volumes:
      - name: loki-rules
        configMap:
          name: loki-rules
          items:
          - key: istio-logging-alerts.yaml
            path: fake/istio-logging-alerts.yaml
```

Loki de tenant único usa `fake`, por eso el archivo local se coloca bajo `fake/`. El almacenamiento local de reglas es de solo lectura mediante la API ruler. Las alertas requieren todo el flujo de acceso; solo errores o muestras no dan fracción de errores ni cuantil de latencia sin sesgo. Planifique monitorización de no-data y fallos de entrega aparte.



## Integración con métricas/trazas {#log-integration-with-metricstraces}

### 1. Saltar de logs a trazas

Use el campo derivado `trace_id` del datasource. Solo enlaza si hay trazado, ID y la misma traza retenida en Tempo. `x-request-id` no es intercambiable con W3C trace ID. Muestreo y retención pueden dejar un log válido sin traza recuperable.

### 2. Correlación de métricas

Los exemplars Prometheus vinculan **métricas con trazas** cuando hay una etiqueta trace ID real; no crean enlace a logs. Configure `exemplarTraceIdDestinations.name` con la etiqueta observada, normalmente `trace_id`, no un `TraceID` inventado. Para métricas→logs, configure correlaciones/data links Grafana con etiquetas namespace/servicio coincidentes. Datasources no fabrican exemplars.

### 3. Consultas integradas

Use un panel Prometheus para tasa de todo el tráfico y uno Loki para accesos de la carga elegida. Configure variables coherentes; Istio usa `destination_canonical_service`/namespace de carga, no una etiqueta métrica `app` universal.

```promql
sum(rate(istio_requests_total{reporter="destination",destination_workload_namespace="$namespace",destination_canonical_service="$service"}[5m]))
```

```logql
{container="istio-proxy",log_type="access",namespace="$namespace",app="$service"} | json | __error__=""
```

Use enlaces Explore generados por Grafana o correlaciones, no JSON sin codificar en una URL. Asegure que app de Loki y service de métricas identifiquen la misma carga.

## Optimización {#performance-optimization}

### 1. Reducir volumen de logs

Mida proporciones reales de health checks, errores y tráfico normal antes de filtrar/muestrear. No hay reducción universal 50–90% o 30–50%. Filtrar en proxy reduce generación; muestrear en collector reduce ingesta/almacenamiento posterior. Mantenga métricas completas y auditoría crítica independientes de muestras de logs.

Puede combinar una exclusión HTTP de salud con el filtro Telemetry existente; considere campos HTTP ausentes en TCP:

```yaml
filter:
  expression: '!has(request.url_path) || !(request.url_path.startsWith("/health") || request.url_path.startsWith("/ready")
    || request.url_path.startsWith("/live") || request.url_path == "/metrics" || request.url_path == "/favicon.ico")'
```

### 2. Rendimiento Loki

```yaml
limits_config:
  # Ingestion limits; these do not directly set chunk size
  ingestion_rate_strategy: global
  ingestion_rate_mb: 32  # Example, size for the workload
  ingestion_burst_size_mb: 64  # Example burst budget

  # Query performance
  max_query_parallelism: 32
  max_query_series: 10000
  max_query_lookback: 720h

  # Stream limits
  max_streams_per_user: 10000
  max_global_streams_per_user: 0

  # Label cardinality limits
  max_label_names_per_series: 30
  max_label_value_length: 2048
```

### 3. Lotes y reintentos Alloy

```alloy
// loki.write endpoint fragment: merge with the endpoint's existing URL.
batch_wait = "1s"
batch_size = "1MiB"
min_backoff_period = "500ms"
max_backoff_period = "5m"
max_backoff_retries = 10
remote_timeout = "10s"
```

## Resolución de problemas {#troubleshooting}

### Logs de acceso no visibles

Inspeccione listeners dinámicos efectivos, proveedores y una solicitud conocida. Los logs internos no prueban configuración de acceso, y la primera línea de contenedor no tiene por qué ser JSON:

```bash
kubectl get telemetry -A
istioctl proxy-config listeners <pod-name> -n <namespace> -o json | \
  jq '.. | objects | select(has("accessLog")) | .accessLog'
kubectl logs <pod-name> -n <namespace> -c istio-proxy --tail=100 | \
  jq -R 'fromjson? | select(.log_type == "access")'
```

### Fallo de entrega del collector o almacenamiento

Revise descubrimiento Alloy, RoleBindings y permiso de logs Pod. La fuente API no necesita archivos de host. Examine logs/métricas de Alloy para lotes descartados/reintentados y consulte flujos Loki con range-query. Ejecute port-forwards en terminales separados:

```bash
kubectl logs -n observability deployment/alloy --tail=100
kubectl port-forward -n observability deployment/alloy 12345:12345
# Another terminal:
curl -fsS http://localhost:12345/metrics | rg 'loki_(write|process)_'
# Separate terminal:
kubectl port-forward -n observability svc/loki 3100:3100
```

```bash
curl -fsSG http://localhost:3100/loki/api/v1/query_range \
  --data-urlencode 'query={container="istio-proxy",log_type="access"}' \
  --data-urlencode 'limit=20' | jq '.data.result'
```

### Volumen y cardinalidad

`kubectl top` mide consumo de recursos, no logs. Calcule tasa de bytes desde registros retenidos e inspeccione conjuntos de flujos en un intervalo acotado. `/labels` cuenta nombres de etiquetas, no flujos; evite consultas `/series` ilimitadas de alta cardinalidad en instalaciones grandes.

```logql
topk(10, sum by (namespace, app) (bytes_rate({container="istio-proxy"} [5m])))

topk(10, sum by (namespace, app) (count_over_time({container="istio-proxy"} [1h])))
```

Inspeccione campos parseados antes de filtrar números. Tras `unwrap`, excluya `__error__` antes de agregar. Entradas muestreadas/filtradas/perdidas no pueden reconstruirse de lo retenido.

## Referencias

- [Logs de acceso Istio](https://istio.io/latest/docs/tasks/observability/logs/access-log/)
- [Telemetry API](https://istio.io/latest/docs/reference/config/telemetry/)
- [Logs de acceso Envoy](https://www.envoyproxy.io/docs/envoy/latest/configuration/observability/access_log/usage)
- [Documentación Grafana Loki](https://grafana.com/docs/loki/latest/)
- [Fuente de logs Kubernetes Alloy](https://grafana.com/docs/alloy/latest/reference/components/loki/loki.source.kubernetes/)
- [Ciclo de vida Promtail](https://grafana.com/docs/loki/latest/send-data/promtail/)
- [Lenguaje de consultas LogQL](https://grafana.com/docs/loki/latest/query/)
- [Lenguaje de expresiones CEL](https://github.com/google/cel-spec)
