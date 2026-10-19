# Registros de Istio

> **Versiones compatibles**: Istio 1.31
> **Última actualización**: 11 de septiembre de 2026

> **Alcance de la validación**: Estas configuraciones de laboratorio se comprobaron con referencias oficiales y validadores locales, sin desplegar un clúster. Cada ejemplo indica sus supuestos sobre namespaces, identidad, almacenamiento, backend y carga; compruébelos en el entorno de destino.

Los logs de acceso configurados registran metadatos de las solicitudes o conexiones observadas. Son distintos de los diagnósticos de Envoy/istiod y de los logs de la aplicación; no capturan toda la actividad de la malla ni los cuerpos completos de las solicitudes y respuestas. Estos ejemplos utilizan sidecars. En ambient, los logs L7 requieren asociar un waypoint, mientras que ztunnel proporciona logs L4 independientes.

## Índice

1. [Descripción general de los logs](#logging-overview)
2. [Configuración de logs de acceso](#access-log-configuration)
3. [Personalización con Telemetry API](#log-customization-with-telemetry-api)
4. [Filtrado y muestreo](#log-filtering-and-sampling)
5. [Ajuste del nivel de log de Envoy](#envoy-log-level-adjustment)
6. [Integración de Alloy + Loki](#alloy--loki-integration)
7. [Dashboard de logs en Grafana](#grafana-log-dashboard)
8. [Integración de logs con métricas y trazas](#log-integration-with-metricstraces)
9. [Optimización del rendimiento](#performance-optimization)
10. [Resolución de problemas](#troubleshooting)

## Descripción general de los logs {#logging-overview}

### Capas de logs de Istio

Envoy → stdout estructurado → recopilación de logs de Kubernetes con Alloy → Loki → Grafana. Como alternativa, un proveedor de logs de acceso OTLP de Envoy puede enviar los registros a un OpenTelemetry Collector. Elija una sola vía de entrega para los mismos logs y evite duplicarlos. Istiod distribuye la configuración de Telemetry y de los proveedores seleccionados.

### Tipos de logs

1. **Log de acceso**: Metadatos configurados de solicitudes HTTP o conexiones TCP
2. **Log del proxy Envoy**: Registros del funcionamiento interno de Envoy
3. **Log de Istiod**: Registros del plano de control
4. **Log de la aplicación**: Registros propios de la aplicación

## Configuración de logs de acceso {#access-log-configuration}

### 1. Definir un proveedor de logs de acceso

Integre una de las siguientes definiciones de proveedor en la configuración de instalación existente de Istio mediante `istioctl install -f logging-install.yaml`. Conserve los demás ajustes y proveedores de la malla. Son datos de entrada para la instalación, no recursos Kubernetes IstioOperator. Seleccione después el proveedor instalado mediante Telemetry; los formatos de texto y JSON son alternativas.

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

El formato del proveedor genera los campos JSON; el filtro de Telemetry selecciona qué eventos se escriben. `duration` se expresa en milisegundos en el log, mientras que `request.duration` en CEL es un valor de tipo duración. `trace_id` contiene el ID de la traza activa cuando el sistema de tracing lo proporciona; `request_id` es un valor independiente para correlacionar solicitudes. Se omiten los parámetros de consulta de la URL; revise cualquier encabezado adicional antes de registrarlo.

Los cambios de logging se distribuyen mediante la configuración del proxy. Reiniciar todos los componentes istiod y las cargas de trabajo no es el procedimiento habitual para activarlos. Compruebe los listeners efectivos y envíe una solicitud de prueba. Los cambios de nivel de log en la configuración de arranque, descritos más adelante, requieren renovar los proxies seleccionados.

### 2. Control detallado con Telemetry API

Telemetry selecciona los logs por namespace o carga de trabajo. Estos ejemplos son alternativas: integre los ajustes de modo que exista un solo recurso sin selector por namespace. La guía utiliza el modo SERVER para los logs de entrada del servicio y evita contar dos veces un salto por sus registros de cliente y servidor. Los diagnósticos de gateways o tráfico saliente pueden usar políticas CLIENT independientes; sepárelos del cálculo de la tasa de solicitudes del servicio. Si instala `mesh-text`, seleccione ese proveedor en lugar de `mesh-json`.

#### Habilitar logs de acceso JSON en toda la malla

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

#### Logs detallados por carga de trabajo

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

### Proveedor personalizado de logs

#### 1. Enviar logs por OpenTelemetry

Esta opción es una alternativa a recopilar los mismos logs de stdout con Alloy. Instale el proveedor y selecciónelo después mediante un recurso Telemetry del namespace:

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

El Collector de la [guía de trazas](02-tracing.md) ya define el receptor OTLP, el limitador de memoria y el procesador de lotes. Integre este pipeline de logs y su exportador en la configuración, y recargue o vuelva a desplegar el Collector. Loki 3.7.7 acepta logs OTLP/HTTP en `/otlp/v1/logs`; el exportador añade `/v1/logs` al endpoint configurado. El esquema TSDB v13 admite metadatos estructurados. Los atributos OTLP se convierten en metadatos, en vez de formar el cuerpo JSON de stdout; adapte las consultas en lugar de reutilizar sin comprobar los ejemplos con `| json`.

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

Indicar una ruta de archivo en el proveedor no crea ni monta un volumen. Este ejemplo opcional de Pod monta un `emptyDir` de tamaño limitado en el proxy inyectado; sustituya la imagen de la aplicación. Un lector independiente debe montar el mismo volumen y gestionar la rotación y el envío de los archivos. `kubectl logs` no devuelve esos archivos y el `emptyDir` desaparece al eliminar el Pod. El ejemplo principal de recopilación utiliza stdout.

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

### Personalización del formato de logs

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
| `request.path` | Ruta de la solicitud | /api/v1/users |
| `request.url_path` | Ruta de la URL sin parámetros de consulta | /api/v1/users |
| `request.headers` | Encabezados de la solicitud | `request.headers['user-agent']` |
| `response.code` | Código de estado HTTP | 200, 404, 500 |
| `response.headers` | Encabezados de la respuesta | `response.headers['content-type']` |
| `response.flags` | Máscara de bits representada como entero | `response.flags != 0` |
| `request.duration` | Valor de tipo duración de la solicitud | `duration("1s")` |
| `connection.mtls` | Uso de mTLS | true, false |
| `connection.uri_san_peer_certificate` | URI SAN del peer downstream, cuando está presente | spiffe://... |
| `connection.uri_san_local_certificate` | URI SAN del certificado local de la conexión downstream | spiffe://... |

## Filtrado y muestreo {#log-filtering-and-sampling}

### 1. Logs condicionales

#### Solo errores y solicitudes lentas

Los filtros de atributos HTTP se aplican al tráfico HTTP. Para logs TCP, use atributos de conexión o una expresión que compruebe explícitamente la posible ausencia de campos HTTP. CEL selecciona eventos; no define el formato de los campos JSON.

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

Use la etapa `stage.sampling` que admite Alloy; la interfaz CEL de Telemetry no documenta una función `random()` para muestreo. Añada la etapa siguiente dentro de `loki.process` para conservar de forma uniforme el 10 % de los registros:

```alloy
stage.sampling {
  rate = 0.1
  drop_counter_reason = "uniform_sampling"
}
```

Para conservar el 1 % de los logs de acceso de solicitudes correctas de menos de un segundo, y mantener los errores y los registros lentos o sin clasificar, extraiga los campos enteros del proveedor JSON, clasifique con etiquetas temporales, aplique el muestreo y retire esas etiquetas antes de escribir. Sustituya las etapas del proceso principal por esta alternativa y conserve su `forward_to`:

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

`stage.match` admite selectores de flujo y filtros de línea, pero no un pipeline completo de filtros de etiquetas de LogQL. La etiqueta temporal de duración nunca llega a Loki. El muestreo en el Collector reduce la ingesta y el almacenamiento, sin reducir el coste de generar logs en el proxy. Los recuentos, cuantiles y proporciones de errores calculados con esos registros están sesgados; use las métricas de Istio sin muestreo para los SLI de todo el tráfico. Los ejemplos siguientes de dashboards y alertas requieren logs de acceso sin muestreo.

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

## Ajuste del nivel de log de Envoy {#envoy-log-level-adjustment}

### Cambiar el nivel de log dinámicamente

#### Nivel global de log de Envoy

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

Use `istioctl proxy-config log <pod-name> -n <namespace>` para consultar los componentes disponibles en esa versión del proxy. Cada compilación puede exponer un conjunto diferente de los componentes del ejemplo.

### Componentes principales de los logs de Envoy

| Componente | Descripción | Caso de uso |
|-----------|-------------|----------|
| `admin` | Interfaz de administración | Depurar la API de administración |
| `aws` | Integración con AWS | Investigar problemas con servicios AWS |
| `connection` | Conexiones TCP | Depurar problemas de conexión |
| `filter` | Filtros HTTP | Analizar la cadena de filtros |
| `forward_proxy` | Proxy de salida | Seguir el comportamiento del proxy |
| `grpc` | gRPC | Investigar problemas de comunicación gRPC |
| `hc` | Comprobaciones de salud | Investigar fallos en las comprobaciones de salud |
| `http` | HTTP | Seguir solicitudes y respuestas HTTP |
| `http2` | HTTP/2 | Investigar problemas del protocolo HTTP/2 |
| `jwt` | Autenticación JWT | Verificar tokens JWT |
| `lua` | Scripts Lua | Depurar filtros Lua |
| `main` | Lógica principal | Examinar el funcionamiento general de Envoy |
| `router` | Enrutamiento | Seguir las decisiones de enrutamiento |
| `runtime` | Configuración en ejecución | Examinar cambios dinámicos de configuración |
| `upstream` | Clústeres upstream | Investigar problemas de conexión con el backend |
| `client` | Cliente HTTP | Examinar solicitudes salientes |
| `pool` | Pool de conexiones | Examinar la gestión del pool de conexiones |
| `rbac` | Filtro RBAC | Depurar problemas de permisos |

### Configuración persistente del nivel de log

Integre estos valores en la configuración de instalación y renueve los proxies seleccionados. Antes de un cambio temporal, consulte los niveles actuales de cada componente y restáurelos al terminar. Cambiar el nivel de log no activa los logs de acceso.

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

### Activar logs de depuración solo para una carga de trabajo

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

<span id="alloy--loki-integration"></span>

## Integración de Alloy + Loki

Promtail llegó al final de su vida útil el **2 de marzo de 2026**. Use Alloy u otro cliente con soporte para los nuevos despliegues. Este ejemplo sustituye la lectura de archivos de Promtail por la recopilación de logs mediante la API de Kubernetes con Alloy; no necesita rutas de Docker, contenedores privilegiados ni montajes del sistema de archivos del nodo.

### 1. Instalar Loki en modo de binario único

El siguiente ejemplo corresponde a una instalación nueva con una réplica y un tenant, Loki 3.7.7, TSDB v13 y almacenamiento en el sistema de archivos. Utiliza el modo de **binario único**, no Simple Scalable. Cree primero el namespace `observability`. En EKS debe existir la StorageClass `gp3` con un controlador EBS CSI operativo; en otras plataformas, utilice la clase de almacenamiento persistente correspondiente. Fargate no puede montar volúmenes EBS: ejecute Loki en nodos EC2 adecuados o use un servicio Loki externo con soporte.

Con `auth_enabled: false`, tener acceso de red permite acceder a los logs del tenant. Mantenga los endpoints privados y configure un gateway de autenticación y TLS compatible para producción. Al actualizar una instalación existente, conserve las entradas históricas del esquema; la fecha de inicio de 2024 que aparece abajo es válida y no corresponde a una fecha de lanzamiento. La retención mediante Compactor requiere estado persistente y `delete_request_store`.

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

### 2. Recopilar logs de Pods con Alloy

Cree los namespaces de las aplicaciones indicados antes de aplicar sus RoleBindings, o limite tanto el descubrimiento como los bindings a namespaces existentes. Alloy solo lee los metadatos de Pods y `pods/log` en esos namespaces. La fuente basada en la API ya recibe el contenido de los logs sin el formato envolvente CRI/Docker; una fuente basada en archivos necesita interpretar el formato del runtime y usar rutas de archivos locales de cada nodo.

El ejemplo de una réplica recopila logs de sidecars, istiod y aplicaciones, y excluye los contenedores de inicialización. Solo usa como etiquetas namespace/pod/container/app/version y un `log_type` de valores limitados; los ID de solicitudes y trazas, las rutas y la duración permanecen como campos, no como etiquetas del índice de Loki. El proveedor JSON anterior emite `log_type="access"` para distinguir los logs de acceso de los diagnósticos del proxy en el mismo contenedor.

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

Esta recopilación mediante la API evita las restricciones de DaemonSet para Pods de aplicaciones en Fargate, pero no recopila logs de los nodos. Aumenta el trabajo de la API de Kubernetes y de kubelet. En instalaciones grandes, evalúe la recopilación local por nodo o un clúster de Alloy con la responsabilidad sobre cada destino coordinada. Añadir réplicas idénticas que lean todos los Pods duplicaría la recopilación. El estado en `emptyDir` y los reintentos limitados no garantizan una entrega sin pérdidas durante reinicios o interrupciones; configure buffers o WAL persistentes y pruebe la recuperación para producción.

### 3. Consultas LogQL

Los ejemplos siguientes usan el proveedor JSON de stdout y logs de acceso SERVER sin muestreo. Un selector de contenedor por sí solo también incluye diagnósticos del proxy; `log_type="access"` selecciona los registros de acceso. Las estadísticas HTTP excluyen además los métodos vacíos o `-`, porque un log de conexión TCP no representa una solicitud HTTP. Use números en las comparaciones numéricas y `__error__=""` para excluir errores de interpretación o conversión antes de agregar métricas.

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

`UO` indica desbordamiento upstream; `URX` significa que se agotaron los reintentos o los intentos de conexión. `downstream_tls_version` distingue entre texto sin cifrar y TLS en la conexión registrada; `peer_uri_san` aporta información del peer autenticado cuando está disponible. Ninguno es un contador universal de fallos de negociación TLS, que pueden ocurrir antes de que exista un registro de acceso HTTP. La antigua consulta con `connection_security_policy` utilizaba una etiqueta de métricas ausente de estos logs.

#### Agregación y estadísticas

```logql
sum by (namespace, app) (rate({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | __error__="" [5m]))

sum by (response_code) (count_over_time({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | __error__="" [5m]))

quantile_over_time(0.95, {container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | unwrap duration | __error__="" [5m]) by (namespace, app)

sum by (namespace, app) (rate({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | response_code >= 500 | response_code < 600 | __error__="" [5m])) / sum by (namespace, app) (rate({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | __error__="" [5m]))

avg_over_time({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | unwrap duration | __error__="" [5m]) by (namespace, app)
```

Estos resultados describen los registros conservados. El logging selectivo, el muestreo, las pérdidas de entrega, las distintas rutas de llamadas y los logs de gateways afectan al resultado. Use las métricas estándar del capítulo de métricas para evaluar los SLO del servicio completo.

## Dashboard de logs en Grafana {#grafana-log-dashboard}

### 1. Añadir una fuente de datos Loki

Monte el archivo de la fuente de datos en `provisioning/datasources` de Grafana o utilice la configuración de aprovisionamiento compatible del chart. Grafana no consume automáticamente un ConfigMap por el mero hecho de existir. El UID `tempo` debe identificar una fuente de datos Tempo existente. La correlación utiliza el `trace_id` del proveedor JSON; los UUID de solicitudes no son ID de trazas y los ID vacíos no generan enlaces.

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

### 2. Dashboard de logs de acceso de Istio

#### JSON del dashboard

Importe el objeto de dashboard siguiente o móntelo mediante un proveedor de dashboards. Es un archivo de dashboard, no un objeto envolvente para la API HTTP. Deben existir los UID de fuentes de datos `loki` y `prometheus`; haga corresponder la etiqueta `app` del log con el valor canonical-service de las métricas. El mapa de calor usa buckets reales del histograma de Prometheus; las duraciones sin procesar de los logs no contienen una etiqueta de bucket `le`.

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

### 3. Alertas con Loki Ruler

El YAML con `groups`/`alert`/`expr`, de estilo Prometheus, configura Loki Ruler. El aprovisionamiento de alertas administradas por Grafana utiliza otro formato documentado, con UID, condición y datos de consulta; exporte las reglas desde Grafana si elige esa vía. Para evaluar reglas con Loki Ruler, cree este ConfigMap, integre sus ajustes en `loki.yaml` y añada el fragmento de volúmenes al StatefulSet existente, preservando los montajes de configuración y almacenamiento. Debe existir un Alertmanager en la dirección configurada.

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

Loki con un único tenant utiliza el ID `fake`; por eso el archivo local de reglas se coloca bajo `fake/`. El almacenamiento local de reglas es de solo lectura mediante la API de Ruler. Estas alertas requieren el flujo completo de logs de acceso: registrar solo errores o aplicar muestreo impide obtener proporciones de errores o cuantiles de latencia sin sesgo. Planifique por separado cómo detectar la ausencia de datos y los fallos de entrega.

<span id="log-integration-with-metricstraces"></span>

## Integración de logs con métricas y trazas

### 1. Ir de los logs a las trazas

Use el campo derivado `trace_id` de la fuente de datos Loki anterior. Solo genera un enlace si el tracing está habilitado, el ID está presente y Tempo ha conservado esa misma traza. El `x-request-id` de una solicitud no es intercambiable con un ID de traza W3C. El muestreo y la retención del backend pueden dejar un log válido cuya traza ya no sea recuperable.

### 2. Correlación de métricas

Los exemplars de Prometheus vinculan **métricas con trazas** cuando contienen una etiqueta real con el ID de traza; no crean un enlace de métricas a logs. Configure `exemplarTraceIdDestinations.name` con el nombre de etiqueta observado, normalmente `trace_id`, en lugar de inventar un campo `TraceID`. Para navegar de métricas a logs, configure correlaciones o enlaces de datos en Grafana con etiquetas coincidentes de namespace y servicio. La configuración de la fuente de datos no genera exemplars por sí sola.

### 3. Consultas integradas

Use un panel de Prometheus para la tasa de solicitudes de todo el tráfico y uno de Loki para los logs de acceso de la carga seleccionada. Configure las variables del dashboard de forma coherente: Istio utiliza `destination_canonical_service` y el namespace de la carga, en vez de una etiqueta de métricas `app` universal.

```promql
sum(rate(istio_requests_total{reporter="destination",destination_workload_namespace="$namespace",destination_canonical_service="$service"}[5m]))
```

```logql
{container="istio-proxy",log_type="access",namespace="$namespace",app="$service"} | json | __error__=""
```

Use enlaces de Explore generados por Grafana o correlaciones, en lugar de insertar JSON sin codificar en una URL. Compruebe que la etiqueta app de Loki y la etiqueta de servicio de las métricas identifiquen la misma carga de trabajo.

## Optimización del rendimiento {#performance-optimization}

### 1. Reducir el volumen de logs

Mida la proporción real de comprobaciones de salud, errores y tráfico habitual antes de elegir filtros o muestreo en Alloy. No existe una reducción universal del 50–90 % o del 30–50 %. Los filtros en el proxy reducen los logs generados; el muestreo en el Collector reduce la ingesta y el almacenamiento posteriores. Mantenga las métricas de todo el tráfico y los eventos de auditoría críticos independientes de un flujo de logs muestreado.

Puede integrar la exclusión de rutas HTTP de comprobación de salud en el filtro Telemetry existente; tenga en cuenta que los logs de conexiones TCP pueden carecer de campos HTTP:

```yaml
filter:
  expression: '!has(request.url_path) || !(request.url_path.startsWith("/health") || request.url_path.startsWith("/ready")
    || request.url_path.startsWith("/live") || request.url_path == "/metrics" || request.url_path == "/favicon.ico")'
```

### 2. Ajustar el rendimiento de Loki

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

### 3. Lotes y reintentos de Alloy

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

Inspeccione los listeners dinámicos efectivos, los proveedores seleccionados y una solicitud de prueba conocida. Los logs internos del proxy no demuestran que los logs de acceso estén configurados, y la primera línea del log de un contenedor no tiene por qué ser JSON:

```bash
kubectl get telemetry -A
istioctl proxy-config listeners <pod-name> -n <namespace> -o json | \
  jq '.. | objects | select(has("accessLog")) | .accessLog'
kubectl logs <pod-name> -n <namespace> -c istio-proxy --tail=100 | \
  jq -R 'fromjson? | select(.log_type == "access")'
```

### Fallos de entrega en el Collector o el almacenamiento

Compruebe el descubrimiento de destinos de Alloy, los RoleBindings y el permiso para leer logs de Pods. La fuente basada en la API no requiere archivos de logs del host. Examine los logs y las métricas de Alloy para detectar lotes descartados o reintentados; después, consulte los flujos de logs de Loki mediante su endpoint de consulta de rangos. Ejecute cada port-forward en una terminal independiente:

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

`kubectl top` mide el consumo de recursos, no el volumen de logs. Mida la tasa de bytes de los logs conservados e inspeccione los conjuntos de flujos reales durante un intervalo limitado. `/labels` cuenta nombres de etiquetas, no flujos. Evite consultas `/series` sin límites y de alta cardinalidad en instalaciones grandes.

```logql
topk(10, sum by (namespace, app) (bytes_rate({container="istio-proxy"} [5m])))

topk(10, sum by (namespace, app) (count_over_time({container="istio-proxy"} [1h])))
```

Inspeccione los campos interpretados antes de aplicar filtros numéricos. Después de `unwrap`, excluya `__error__` antes de agregar. Las entradas descartadas por muestreo o filtrado, o perdidas durante la entrega, no se pueden reconstruir a partir de los logs conservados.

## Referencias

- [Logs de acceso Istio](https://istio.io/latest/docs/tasks/observability/logs/access-log/)
- [Telemetry API](https://istio.io/latest/docs/reference/config/telemetry/)
- [Logs de acceso Envoy](https://www.envoyproxy.io/docs/envoy/latest/configuration/observability/access_log/usage)
- [Documentación Grafana Loki](https://grafana.com/docs/loki/latest/)
- [Fuente de logs Kubernetes Alloy](https://grafana.com/docs/alloy/latest/reference/components/loki/loki.source.kubernetes/)
- [Ciclo de vida Promtail](https://grafana.com/docs/loki/latest/send-data/promtail/)
- [Lenguaje de consultas LogQL](https://grafana.com/docs/loki/latest/query/)
- [Lenguaje de expresiones CEL](https://github.com/google/cel-spec)
