# Paneles de Istio

> **Base de revisión**: Istio 1.31; la compatibilidad de Kiali se detalla a continuación.
> **Última actualización**: September 11, 2026

Utilice Grafana, Kiali y Prometheus para inspeccionar la telemetría configurada. Los ejemplos son patrones de configuración de laboratorio comprobados con referencias oficiales y validación sin conexión; no se desplegaron ni se probaron con carga de producción. La disponibilidad del backend, la autenticación, los permisos de los espacios de nombres, el almacenamiento y la compatibilidad de versiones son requisitos previos explícitos.

## Índice

1. [Descripción general de los paneles](#dashboard-overview)
2. [Kiali](#kiali)
3. [Paneles de Grafana](#grafana-dashboards)
4. [Prometheus](#prometheus)
5. [Crear paneles personalizados](#creating-custom-dashboards)
6. [Integración de paneles](#dashboard-integration)
7. [Buenas prácticas](#best-practices)

## Descripción general de los paneles {#dashboard-overview}

### Arquitectura de la pila de observabilidad

Kiali lee los recursos de Istio desde la API de Kubernetes y consulta Prometheus; istiod configura los proxies en vez de enviar configuración a Kiali. Grafana consulta los backends de métricas/registros/trazas configurados. Prometheus recopila métricas de los proxies, los recopiladores entregan registros de acceso/spans y las aplicaciones con trazado deben propagar el contexto.

### Propósito de cada herramienta

| Herramienta | Uso principal | Fuente de datos |
|------|-------------|-------------|
| **Kiali** | Topología de servicios, análisis del tráfico, validación de configuración | Prometheus, configuración de Istio |
| **Grafana** | Visualización de métricas, alertas, análisis de registros | Prometheus, Loki, Tempo |
| **Prometheus** | Recopilación y consulta de métricas | Envoy, istiod |
| **Jaeger** | Análisis de trazas distribuidas | Spans de Envoy |

## Kiali {#kiali}

<p align="center">
  <img src="https://istio.io/latest/docs/tasks/observability/kiali/kiali-graph.png" alt="Gráfico de servicios de Kiali" width="900">
</p>

Kiali es una **consola de observabilidad** para la malla de servicios Istio. Visualiza la topología de servicios en tiempo real, analiza el flujo de tráfico y valida configuraciones de Istio.

### Valor principal de Kiali

1. **Visualización del gráfico de servicios**: representa intuitivamente las relaciones y el flujo de tráfico entre microservicios
2. **Monitorización en tiempo real**: permite ver la tasa de solicitudes, la tasa de errores y el tiempo de respuesta en tiempo real
3. **Validación de configuración**: detecta errores en CRD de Istio como VirtualService y DestinationRule
4. **Verificación del estado de mTLS**: confirma visualmente la aplicación de mTLS entre servicios
5. **Integración del trazado distribuido**: permite ver trazas directamente desde el gráfico de servicios mediante la integración con Jaeger

### Ejemplo de instalación y compatibilidad

Kiali 2.31.0 y su operador se publicaron el August 23, 2026. La tabla de compatibilidad publicada enumera actualmente Istio 1.30 con Kiali 2.26+ e Istio 1.29 con Kiali 2.21+; **todavía no enumera explícitamente Istio 1.31**. Considere lo siguiente como un ejemplo de configuración de Kiali 2.31 para un despliegue de Istio con compatibilidad documentada. Confirme la compatibilidad con 1.31 mediante las indicaciones actuales de los mantenedores y un laboratorio representativo antes de utilizar esa combinación; ni la coincidencia de números de versión ni «latest» demuestran compatibilidad. No rebaje la versión de una malla existente solo para seguir este ejemplo.

#### 1. Instalar el operador de Kiali

```bash
helm repo add kiali https://kiali.org/helm-charts
helm repo update kiali
helm install kiali-operator kiali/kiali-operator \
  --namespace kiali-operator --create-namespace --version 2.31.0
kubectl get pods -n kiali-operator
```

#### 2. Crear un CR de Kiali con ámbito limitado y solo de consulta

Ya debe existir un Prometheus accesible que contenga las métricas de Istio; adapte la URL si su Service tiene otro nombre. El ejemplo de Prometheus Operator posterior define `prometheus` en `istio-system`. El operador da a Kiali acceso a su propio espacio de nombres y a los que coincidan con los selectores de descubrimiento. Con `cluster_wide_access: false`, crea acceso por espacio de nombres en vez de conceder al servidor acceso a todo el clúster. El RBAC del usuario final puede reducir aún más los espacios de nombres visibles.

```yaml
apiVersion: kiali.io/v1alpha1
kind: Kiali
metadata:
  name: kiali
  namespace: istio-system
spec:
  deployment:
    cluster_wide_access: false
    discovery_selectors:
      default:
      - matchExpressions:
        - key: kubernetes.io/metadata.name
          operator: In
          values:
          - default
          - app
          - production
    view_only_mode: true
    replicas: 1
    resources:
      requests:
        cpu: 100m
        memory: 256Mi
      limits:
        cpu: 500m
        memory: 1Gi
  auth:
    strategy: token
  external_services:
    prometheus:
      url: http://prometheus.istio-system.svc.cluster.local:9090
    grafana:
      enabled: false
    tracing:
      enabled: false
```

Guárdelo como `kiali-cr.yaml` y aplíquelo. Cree los espacios de nombres de aplicaciones previstos antes de la reconciliación. Kiali no hereda automáticamente los selectores de descubrimiento de Istio. El antiguo campo `accessible_namespaces` se eliminó en Kiali 2.0. Las integraciones de backend Grafana/trazado permanecen deshabilitadas hasta configurar sus endpoints, credenciales y compatibilidad.

```bash
kubectl apply -f kiali-cr.yaml
kubectl get kiali,pods -n istio-system
kubectl port-forward -n istio-system svc/kiali 20001:20001
```

Para acceso externo, configure por separado un ingress/gateway mantenido, certificados TLS, autenticación y URL accesibles desde el navegador. El ejemplo no instala un controlador ingress, un emisor de cert-manager ni un endpoint público. Las funciones de estado de proxies pueden depender de la API de depuración de istiod; si está deshabilitada deliberadamente, establezca `external_services.istio.istio_api_enabled: false` y acepte esas limitaciones en vez de suponer que todas las vistas están disponibles.

### Acceder a Kiali

Abra `http://localhost:20001` después del reenvío de puertos. La autenticación por token utiliza un token de ServiceAccount de Kubernetes y respeta los permisos de espacio de nombres de la cuenta. Utilice una identidad de consulta dedicada con el RBAC previsto; no utilice el ServiceAccount del servidor/operador de Kiali como inicio de sesión de administrador por comodidad. Para una cuenta ya creada y vinculada correctamente:

```bash
kubectl create token kiali-viewer -n default --duration=1h
```

El servidor de API determina la duración real del token. La estrategia de token admite un solo clúster. Los despliegues multiclúster/OIDC requieren su configuración de autenticación documentada, una URI de redirección registrada y autorización por espacio de nombres; un ID de cliente y una URL de emisor por sí solos no constituyen una configuración de producción completa. Consulte los [requisitos previos de Kiali](https://kiali.io/docs/installation/installation-guide/prerequisites/) y la [gestión de espacios de nombres](https://kiali.io/docs/configuration/namespace-management/).

### Funciones principales de Kiali

#### 1. Gráfico de servicios (Graph)

**Descripción general**:
- Visualizar la topología de servicios por espacio de nombres
- Mostrar el flujo de tráfico y la tasa de solicitudes (RPS)
- Visualizar la tasa de errores y el tiempo de respuesta
- Verificar la distribución del tráfico por versión

La animación del tráfico ilustra el tráfico agregado durante la ventana temporal y el intervalo de actualización seleccionados. No es una captura de paquetes ni un punto por solicitud. Utilice las métricas de las aristas para el análisis cuantitativo.

**Tipos de vista de gráfico**:

| Tipo de vista | Descripción | Escenario de uso |
|-----------|-------------|--------------|
| **Gráfico de aplicaciones** | Nivel de aplicación | Comprender las dependencias entre servicios |
| **Gráfico de aplicaciones por versión** | Aplicación por versión | Monitorización de despliegues canary |
| **Gráfico de cargas de trabajo** | Nivel de carga de trabajo | Análisis a nivel de Deployment/StatefulSet |
| **Gráfico de servicios** | Nivel de servicio | Vista centrada en Service de Kubernetes |

**Opciones de filtro del gráfico**:

```yaml
# Edge label display
- Request percentage: Traffic distribution rate (%)
- Request rate: Request rate (RPS)
- Response time: Selected latency statistic
- Throughput: Throughput (bytes/sec)

# Display options
- Traffic Animation: Real-time traffic flow
- Service Nodes: Show service nodes
- Traffic Distribution: Version-based traffic distribution
- Security: mTLS lock icon
- Circuit Breakers: Circuit breaker status
- Virtual Services: VirtualService icon
```

**Función de búsqueda/ocultación**:
```
# Find slow edges
Find: response time > 1s
Expression: rt > 1000

# Find unhealthy nodes
Find: unhealthy nodes
Expression: ! healthy

# Hide specific services
Hide: kube-system namespace
```

#### 2. Vista de aplicaciones

Información detallada de cada aplicación:

- **Descripción general**: resumen del estado global
- **Tráfico**: métricas de tráfico entrante/saliente
  - Volumen de solicitudes (RPS)
  - Duración de solicitudes (P50, P95, P99)
  - Tamaño de solicitud / tamaño de respuesta
- **Métricas de entrada**: análisis del tráfico entrante
  - Cargas de trabajo de origen
  - Protocolos de solicitud (HTTP/gRPC/TCP)
  - Códigos de respuesta
- **Métricas de salida**: análisis del tráfico saliente
  - Servicios de destino
  - Tiempos de respuesta
  - Tasas de errores

#### 3. Vista de cargas de trabajo

Información detallada por carga de trabajo (Deployment, StatefulSet, etc.):

- **Pods**: lista y estado de Pods
- **Servicios**: lista de Services conectados
- **Registros**: registros de pods en tiempo real (Envoy + aplicación)
- **Métricas**: métricas de cargas de trabajo
  - Volumen de solicitudes
  - Duración (P50/P95/P99)
  - Tasa de errores
- **Trazas**: trazado distribuido con integración de Jaeger
- **Envoy**: verificación de la configuración de Envoy
  - Clústeres
  - Listeners
  - Rutas
  - Configuración de arranque

#### 4. Vista de servicios

Información detallada por Service de Kubernetes:

- **Descripción general**: metadatos del servicio
- **Tráfico**: métricas de tráfico
- **Métricas de entrada**: análisis de solicitudes por cliente
- **Trazas**: trazado de llamadas al servicio

#### 5. Validación de la configuración de Istio (Istio Config)

Kiali valida los recursos de Istio compatibles usando el estado del clúster disponible. El ejemplo de solo consulta permite inspeccionar la configuración; editarla requiere permisos autorizados por separado. Una marca verde significa que se superaron las comprobaciones implementadas, no que se haya demostrado la corrección durante la ejecución.

**Objetivos de validación**:
- VirtualService
- DestinationRule
- Gateway
- ServiceEntry
- Sidecar
- PeerAuthentication
- RequestAuthentication
- AuthorizationPolicy
- Telemetry

**Niveles de validación**:

| Icono | Nivel | Descripción |
|------|-------|-------------|
| ✅ | Válido | Se superaron las comprobaciones disponibles |
| ⚠️ | Advertencia | Posible problema (incumplimiento de buenas prácticas) |
| ❌ | Error | Error de configuración detectado; la admisión de la API puede aun así tener éxito |

**Ejemplo de validación: KIA1107, subconjunto no encontrado**

En el espacio de nombres `default`, el host corto `reviews` se resuelve como `reviews.default.svc.cluster.local`; utilizar solo esas dos formas no implica una discrepancia de host. KIA0101 significa que no se encontró un espacio de nombres referenciado en una AuthorizationPolicy. El siguiente ejemplo, deliberadamente incorrecto, enruta a `v2` cuando solo está definido `v1`:

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
  namespace: default
spec:
  hosts:
  - reviews.default.svc.cluster.local
  http:
  - route:
    - destination:
        host: reviews.default.svc.cluster.local
        subset: v2
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
  namespace: default
spec:
  host: reviews.default.svc.cluster.local
  subsets:
  - name: v1
    labels:
      version: v1
```

Defina el subconjunto referenciado y despliegue endpoints de servicio coincidentes, o enrute al subconjunto existente previsto. Suponiendo que existan ambas versiones de Bookinfo, este DestinationRule proporciona ambas etiquetas:

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
  namespace: default
spec:
  host: reviews.default.svc.cluster.local
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

Kubernetes puede aceptar un manifiesto con errores semánticos de enrutamiento, por lo que las advertencias/errores de configuración no son idénticos a los fallos de admisión de la API.

#### 6. Seguridad

**Verificación del estado de mTLS**

Utilice los indicadores de seguridad del gráfico junto con la ventana de tráfico seleccionada y la PeerAuthentication efectiva. Observar tráfico mTLS no demuestra que se prohíba el texto sin cifrar: PERMISSIVE puede transportar tráfico completamente cifrado durante una ventana de observación. La ausencia de tráfico/telemetría no demuestra que un servicio sea seguro, y una etiqueta de política por sí sola no establece la eficacia de la autorización. Confírmelo mediante la configuración y pruebas de tráfico permitido/denegado.

**Panel de seguridad**:
- Estado de mTLS por espacio de nombres
- Estado de aplicación de la política PeerAuthentication
- Efectos de AuthorizationPolicy

#### 7. Integración del trazado distribuido

Kiali se integra con Jaeger para ver trazas directamente desde el gráfico de servicios.

**Modo de uso**:
1. Haga clic en un nodo de servicio del gráfico
2. Haga clic en el enlace «Ver trazas»
3. Navegue automáticamente a la interfaz de Jaeger para ver las trazas de ese servicio

**Detalles de las trazas**:
- Duración del span (tiempo de procesamiento de cada servicio)
- Atributos/eventos instrumentados del span (las cabeceras no se capturan automáticamente)
- Detalles de errores
- Mapa de dependencias de servicios

### Funciones avanzadas de Kiali

#### Visualización del desplazamiento de tráfico

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-canary
  namespace: default
spec:
  hosts:
  - reviews.default.svc.cluster.local
  http:
  - route:
    - destination:
        host: reviews.default.svc.cluster.local
        subset: v1
      weight: 90
    - destination:
        host: reviews.default.svc.cluster.local
        subset: v2
      weight: 10
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
  namespace: default
spec:
  host: reviews.default.svc.cluster.local
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

Los pesos configurados son 90/10; Kiali muestra las tasas de solicitudes observadas para la ventana seleccionada. La variación de muestreo, los errores y las condiciones de enrutamiento pueden hacer que las proporciones observadas difieran. Este ejemplo presupone que ambos subconjuntos tienen endpoints coincidentes.

**Monitorización de despliegues canary**:
- Tasa de solicitudes observada por versión frente a los pesos 90/10 configurados
- Comparación de la tasa de errores por versión
- Tiempo de respuesta por versión (P50, P95, P99)
- Verificar la distribución con animación del tráfico en tiempo real

#### Aislamiento de espacios de nombres y control de acceso

Esta es una configuración alternativa de selectores para la misma instancia de Kiali, no un despliegue adicional superpuesto. Con el acceso a todo el clúster deshabilitado, limita el acceso del servidor a `team-a` más su propio espacio de nombres del plano de control; el RBAC de usuario sigue siendo aplicable. La configuración de OpenID es una tarea de autenticación independiente y Keycloak moderno utiliza `/realms/...` de forma predeterminada salvo que se configure un prefijo `/auth` personalizado.

```yaml
apiVersion: kiali.io/v1alpha1
kind: Kiali
metadata:
  name: kiali
  namespace: istio-system
spec:
  deployment:
    cluster_wide_access: false
    discovery_selectors:
      default:
      - matchLabels:
          kubernetes.io/metadata.name: team-a
    view_only_mode: true
    replicas: 1
    resources:
      requests:
        cpu: 100m
        memory: 256Mi
      limits:
        cpu: 500m
        memory: 1Gi
  auth:
    strategy: token
```

## Paneles de Grafana {#grafana-dashboards}

### Paneles oficiales de Istio

El catálogo siguiente se comprobó con las **revisiones de Istio 1.31.0** descargadas, no solo con los títulos de los paneles. Seleccione la revisión correspondiente a la versión de Istio instalada y asigne su fuente de datos Prometheus al importar. La revisión más reciente de un panel no es automáticamente compatible con una malla anterior.

| Panel | ID | Revisión verificada | Ámbito |
|---|---:|---:|---|
| Istio Mesh | 7639 | 330 | Tráfico global, éxitos/4xx/5xx, resumen de cargas de trabajo y versiones de componentes |
| Istio Service | 7636 | 329 | Volumen, duración, tamaño, tráfico TCP y cargas de trabajo de origen/destino del cliente/servidor |
| Istio Workload | 7630 | 330 | Métricas HTTP y TCP entrantes/salientes de cargas de trabajo |
| Istio Performance | 11829 | 329 | vCPU, memoria, disco, tasas de datos y goroutines de proxies/istiod |
| Istio Control Plane | 7645 | 329 | Recursos, envíos/errores/tiempos de xDS, webhooks de validación e inyección |
| Istio Wasm Extension | 13277 | 287 | Estado de VM/entorno de ejecución/caché/carga remota de Wasm |
| Istio Ztunnel | 21306 | 97 | Conexiones L4, bytes, DNS, xDS y recursos de procesos de Ambient |

La variable `service` del panel Service es un host de servicio y su revisión 1.31 tiene filtros `srcns`/`dstns`, en vez de una variable `namespace` genérica. El panel Workload tiene `namespace` y `workload`. Inspeccione las variables de la revisión descargada antes de configurar enlaces directos. Los ID 7636, 11829 y 13277 corresponden respectivamente a **Service, Performance y Wasm**, no a Workload, Mesh genérico y Gateway.

Importe mediante la interfaz de paneles de Grafana y elija la fuente de datos. Para un entorno de prueba nuevo, el `samples/addons/grafana.yaml` de la versión fijada de Istio incluye sus paneles; esa muestra no está reforzada para producción. Para un despliegue existente, utilice su mecanismo de aprovisionamiento documentado en vez de instalar un segundo Grafana.

### Panel comunitario de Loki 14876

La entrada verificada del catálogo es **Grafana Loki Dashboard for Istio Service Mesh**, revisión 3. Utiliza un analizador `pattern` para un formato de texto específico de Envoy, con `status_code` y `req_id`, y variables de fuente de datos/etiqueta/trabajo/instancia. Sus paneles incluyen recuentos de solicitudes/estados, bytes, solicitudes recientes, duración y resúmenes de visitantes/rutas/agentes de usuario. No establece la seguridad mTLS ni proporciona todos los paneles que antes se afirmaban aquí.

```bash
curl -fL -o istio-loki-dashboard.json \
  https://grafana.com/api/dashboards/14876/revisions/3/download
```

Revise el archivo, impórtelo mediante la interfaz y vincule su fuente de datos Loki. Crear un ConfigMap etiquetado no resuelve las entradas de fuentes de datos ni instala un cargador de paneles. Esta revisión comunitaria no es directamente compatible con el proveedor JSON/las etiquetas Alloy de esta guía. Utilice el [panel y las consultas comprobados del capítulo de registros](03-logging.md) para ese formato, o adapte explícitamente el analizador, los campos y las etiquetas. Las estadísticas derivadas de registros describen los registros conservados y pueden estar sesgadas por el filtrado/muestreo.

### Reglas de alertas de métricas

Lo siguiente es un **PrometheusRule de Prometheus Operator**, no aprovisionamiento de alertas gestionadas por Grafana. Las reglas gestionadas por Grafana utilizan campos de datos de consulta/condición/UID; configúrelas en Grafana y exporte el formato compatible si elige esa vía. El operador siguiente selecciona reglas en `istio-system`. Los umbrales son ejemplos que deben ajustarse a los SLO y al volumen de tráfico; HTTP5xx no es la definición completa de un fallo de gRPC/aplicación.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: istio-alerts
  namespace: istio-system
spec:
  groups:
  - name: istio-service-alerts
    rules:
    - alert: HighErrorRate
      expr: sum by (destination_service_name, destination_service_namespace) (rate(istio_requests_total{reporter="destination",response_code=~"5.."}[5m]))
        / sum by (destination_service_name, destination_service_namespace) (rate(istio_requests_total{reporter="destination"}[5m]))
        > 0.05
      for: 2m
      labels:
        severity: warning
      annotations:
        summary: High HTTP error fraction for {{ $labels.destination_service_name }}
        description: Error fraction is {{ $value | humanizePercentage }}
    - alert: HighLatency
      expr: histogram_quantile(0.95, sum by (destination_service_name, destination_service_namespace,
        le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination"}[5m]))) > 1000
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: P95 HTTP duration exceeds1000ms
    - alert: UpstreamOverflow
      expr: sum by (destination_service_name, destination_service_namespace) (rate(istio_requests_total{response_flags=~".*UO.*",reporter="source"}[5m]))
        > 0
      for: 1m
      labels:
        severity: warning
      annotations:
        summary: Source proxy reports upstream overflow
    - alert: PlaintextMeshTraffic
      expr: sum by (source_workload, source_workload_namespace, destination_workload, destination_workload_namespace)
        (rate(istio_requests_total{connection_security_policy="none",reporter="destination"}[5m])) > 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Observed plaintext traffic; inspect intended PeerAuthentication
```

La expresión de error sigue siendo una fracción, por lo que `humanizePercentage` la muestra correctamente. Se utilizan informes de origen para el desbordamiento ascendente que puede no llegar nunca al destino. La ausencia de métricas de texto sin cifrar no demuestra la aplicación de STRICT.

## Prometheus {#prometheus}

### Configuración de laboratorio de Prometheus Operator

Esto presupone un Prometheus Operator y CRD compatibles instalados por separado y un StorageClass `gp3` operativo en nodos EC2 de EKS (o la clase apropiada en otra plataforma). No instala el operador, aprovisiona EBS ni configura un diseño de almacenamiento/alta disponibilidad de producción. Los valores de memoria/CPU/almacenamiento son ilustrativos. Utilice esto o un despliegue de Prometheus existente, no pilas de recopilación duplicadas.

Los selectores de ServiceMonitor, PodMonitor y PrometheusRule siguientes coinciden de forma predeterminada con todos los recursos correspondientes del espacio de nombres de este CR. Por tanto, incluyen los monitores del [capítulo de métricas](01-metrics.md), que no llevaban las etiquetas discordantes del antiguo ejemplo. La selección de recursos de monitor y los espacios de nombres de cargas de trabajo que descubre cada monitor son ajustes independientes. El RBAC siguiente es para el descubrimiento de destinos de Kubernetes; otros tipos de recopilación pueden necesitar permisos distintos.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: prometheus-istio
  namespace: istio-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: prometheus-istio-discovery
rules:
- apiGroups:
  - ''
  resources:
  - services
  - endpoints
  - pods
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - discovery.k8s.io
  resources:
  - endpointslices
  verbs:
  - get
  - list
  - watch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: prometheus-istio-discovery
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: prometheus-istio-discovery
subjects:
- kind: ServiceAccount
  name: prometheus-istio
  namespace: istio-system
---
apiVersion: monitoring.coreos.com/v1
kind: Prometheus
metadata:
  name: istio
  namespace: istio-system
spec:
  replicas: 1
  retention: 15d
  retentionSize: 50GB
  serviceAccountName: prometheus-istio
  podMetadata:
    labels:
      monitoring-stack: istio
  serviceMonitorSelector: {}
  podMonitorSelector: {}
  ruleSelector: {}
  resources:
    requests:
      cpu: 1000m
      memory: 4Gi
    limits:
      cpu: 2000m
      memory: 8Gi
  storage:
    volumeClaimTemplate:
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
  name: prometheus
  namespace: istio-system
spec:
  selector:
    monitoring-stack: istio
  ports:
  - name: http
    port: 9090
    targetPort: 9090
  type: ClusterIP
```

Para almacenamiento a largo plazo, combine un bloque de escritura remota solo después de desplegar y proteger el destino. La URL siguiente presupone un Service VictoriaMetrics en `observability`; adáptela al backend real. Dos réplicas de Prometheus recopilan los mismos destinos, por lo que el almacenamiento remoto necesita un diseño deliberado de alta disponibilidad/deduplicación y etiquetas de réplica. Cambiar `replicas` a 2 por sí solo no hace correctas las métricas remotas sumadas. Verifique la persistencia, el comportamiento ante fallos y la capacidad en el entorno de destino.

```yaml
spec:
  remoteWrite:
  - url: http://victoria-metrics.observability.svc.cluster.local:8428/api/v1/write
    queueConfig:
      capacity: 10000
      maxShards: 5
      minShards: 1
      maxSamplesPerSend: 5000
```

### Ejemplos de consultas de Prometheus

#### Señales de oro

La latencia está en milisegundos. Los ejemplos de saturación muestran conexiones activas y un indicador del estado del disyuntor; no existe una métrica estándar `cx_max` para obtener automáticamente un denominador de utilización.

```promql
# 1. Latency
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket{
    reporter="destination"
  }[5m])) by (destination_service_name, destination_service_namespace, le)
)

# 2. Traffic
sum(rate(istio_requests_total{reporter="destination"}[1m])) by (destination_service_name, destination_service_namespace)

# 3. Errors (error rate)
sum(rate(istio_requests_total{response_code=~"5..", reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
/
sum(rate(istio_requests_total{reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
* 100

# 4. Saturation
envoy_cluster_upstream_cx_active
envoy_cluster_circuit_breakers_default_cx_open
```

## Crear paneles personalizados {#creating-custom-dashboards}

### Plantilla JSON de panel de Grafana

Este es un objeto de panel clásico para importación/aprovisionamiento mediante archivos. Proporcione un UID de fuente de datos `prometheus` existente. Todos los paneles filtran por espacio de nombres y servicio; la tabla por origen también conserva el espacio de nombres de origen.

```json
{
  "title": "Custom Istio Service Dashboard",
  "tags": [
    "istio",
    "custom"
  ],
  "timezone": "browser",
  "version": 1,
  "panels": [
    {
      "id": 1,
      "title": "Request Rate",
      "type": "timeseries",
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 0
      },
      "targets": [
        {
          "expr": "sum(rate(istio_requests_total{reporter=\"destination\",destination_service_namespace=\"$namespace\",destination_service_name=\"$service\"}[5m])) by (response_code)",
          "legendFormat": "{{ response_code }}",
          "refId": "A",
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          }
        }
      ],
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "palette-classic"
          },
          "custom": {
            "drawStyle": "line",
            "lineInterpolation": "linear",
            "fillOpacity": 10
          },
          "unit": "reqps"
        }
      },
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      }
    },
    {
      "id": 2,
      "title": "P95 Latency",
      "type": "gauge",
      "gridPos": {
        "h": 8,
        "w": 6,
        "x": 12,
        "y": 0
      },
      "targets": [
        {
          "expr": "histogram_quantile(0.95, sum(rate(istio_request_duration_milliseconds_bucket{reporter=\"destination\",destination_service_namespace=\"$namespace\",destination_service_name=\"$service\"}[5m])) by (le))",
          "refId": "A",
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          }
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "ms",
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {
                "value": 0,
                "color": "green"
              },
              {
                "value": 500,
                "color": "yellow"
              },
              {
                "value": 1000,
                "color": "red"
              }
            ]
          },
          "max": 2000
        }
      },
      "options": {
        "showThresholdLabels": true,
        "showThresholdMarkers": true
      },
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      }
    },
    {
      "id": 3,
      "title": "Error Rate",
      "type": "stat",
      "gridPos": {
        "h": 8,
        "w": 6,
        "x": 18,
        "y": 0
      },
      "targets": [
        {
          "expr": "sum(rate(istio_requests_total{reporter=\"destination\",destination_service_namespace=\"$namespace\",destination_service_name=\"$service\", response_code=~\"5..\"}[5m])) / sum(rate(istio_requests_total{reporter=\"destination\",destination_service_namespace=\"$namespace\",destination_service_name=\"$service\"}[5m])) * 100",
          "refId": "A",
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          }
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "percent",
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {
                "value": 0,
                "color": "green"
              },
              {
                "value": 1,
                "color": "yellow"
              },
              {
                "value": 5,
                "color": "red"
              }
            ]
          }
        }
      },
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      }
    },
    {
      "id": 4,
      "title": "Request by Source",
      "type": "table",
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 8
      },
      "targets": [
        {
          "expr": "sum(rate(istio_requests_total{reporter=\"destination\",destination_service_namespace=\"$namespace\",destination_service_name=\"$service\"}[5m])) by (source_workload, source_workload_namespace, response_code)",
          "format": "table",
          "instant": true,
          "refId": "A",
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          }
        }
      ],
      "transformations": [
        {
          "id": "organize",
          "options": {
            "excludeByName": {
              "Time": true
            },
            "indexByName": {
              "source_workload": 0,
              "response_code": 1,
              "Value": 2
            },
            "renameByName": {
              "source_workload": "Source",
              "response_code": "Code",
              "Value": "RPS"
            }
          }
        }
      ],
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      }
    },
    {
      "id": 5,
      "title": "Upstream Overflow and Retry Exhaustion",
      "type": "timeseries",
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 8
      },
      "targets": [
        {
          "expr": "sum(rate(istio_requests_total{reporter=\"source\",destination_service_namespace=\"$namespace\",destination_service_name=\"$service\", response_flags=~\".*UO.*\"}[5m]))",
          "legendFormat": "Upstream overflow",
          "refId": "A",
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          }
        },
        {
          "expr": "sum(rate(istio_requests_total{reporter=\"source\",destination_service_namespace=\"$namespace\",destination_service_name=\"$service\", response_flags=~\".*URX.*\"}[5m]))",
          "legendFormat": "Retry/connect attempts exhausted",
          "refId": "B",
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          }
        }
      ],
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
        "query": "label_values(istio_requests_total, destination_service_namespace)",
        "datasource": {
          "type": "prometheus",
          "uid": "prometheus"
        },
        "current": {
          "selected": true,
          "text": "default",
          "value": "default"
        },
        "multi": false
      },
      {
        "name": "service",
        "type": "query",
        "query": "label_values(istio_requests_total{destination_service_namespace=\"$namespace\"}, destination_service_name)",
        "datasource": {
          "type": "prometheus",
          "uid": "prometheus"
        },
        "current": {},
        "multi": false
      }
    ]
  },
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "refresh": "30s",
  "uid": "custom-istio-service"
}
```

### Aprovisionamiento de paneles mediante archivos

Guarde el objeto JSON completo anterior como `custom-istio-service.json`. No introduzca puntos suspensivos ni un contenedor de API HTTP `{ "dashboard": ... }` en un archivo de panel aprovisionado.

```bash
kubectl create configmap grafana-dashboard-custom-istio \
  --from-file=custom-istio-service.json -n observability \
  --dry-run=client -o yaml | kubectl apply -f -
```

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-istio-provider
  namespace: observability
data:
  istio.yaml: |
    apiVersion: 1
    providers:
    - name: istio
      orgId: 1
      folder: Istio
      type: file
      disableDeletion: false
      editable: false
      options:
        path: /var/lib/grafana/istio-dashboards
```

Combine estos montajes con los valores existentes de Deployment/Helm de Grafana, conservando su imagen, credenciales, almacenamiento, sondas y otros contenedores. El nombre del contenedor debe coincidir con el Deployment real. El proveedor montado con `subPath` requiere un despliegue controlado de pods cuando cambia ese archivo de proveedor. Si utiliza un sidecar de paneles ya configurado, siga los ajustes de su chart; una etiqueta `grafana_dashboard` por sí sola no instala ni configura un cargador.

```yaml
spec:
  template:
    spec:
      containers:
      - name: grafana
        volumeMounts:
        - name: istio-dashboards
          mountPath: /var/lib/grafana/istio-dashboards
          readOnly: true
        - name: istio-provider
          mountPath: /etc/grafana/provisioning/dashboards/istio.yaml
          subPath: istio.yaml
          readOnly: true
      volumes:
      - name: istio-dashboards
        configMap:
          name: grafana-dashboard-custom-istio
      - name: istio-provider
        configMap:
          name: grafana-istio-provider
```

## Integración de paneles {#dashboard-integration}

### Enlaces de Kiali → Grafana y trazas

Estos son fragmentos opcionales del CR de Kiali para combinar con el ejemplo anterior. `internal_url` debe ser accesible desde el servidor Kiali; `external_url` debe ser accesible desde el navegador del usuario. Kiali debe autenticarse en la API de Grafana y encontrar los nombres exactos de los paneles. Configure credenciales mediante las referencias a Secrets compatibles de Kiali y confíe en la CA privada cuando corresponda; este fragmento no crea credenciales ni un endpoint público.

```yaml
spec:
  external_services:
    grafana:
      enabled: true
      internal_url: http://grafana.observability.svc.cluster.local:3000
      external_url: https://grafana.example.com
      datasource_uid: prometheus
      dashboards:
      - name: Istio Service Dashboard
        variables:
          datasource: var-datasource
          service: var-service
      - name: Istio Workload Dashboard
        variables:
          datasource: var-datasource
          namespace: var-namespace
          workload: var-workload
```

Para el endpoint de consultas HTTP de Jaeger del capítulo de trazado, la configuración actual pertenece a `external_services.tracing`, con `use_grpc: false` para el puerto 16686. Valide la compatibilidad y la autenticación del backend/API antes de habilitarlo; la inyección de OAuth2 solo es compatible con transporte HTTP. Las integraciones de Jaeger y Tempo son configuraciones opcionales independientes. Los paneles personalizados de Kiali tienen su propio esquema; no se puede insertar JSON de Grafana como una lista `external_services.custom_dashboards`.

```yaml
spec:
  external_services:
    tracing:
      enabled: true
      provider: jaeger
      internal_url: http://jaeger-query.observability.svc.cluster.local:16686
      external_url: https://jaeger.example.com
      use_grpc: false
```

### Enlace de Grafana → Jaeger

Combine la correspondencia de ejemplares con una fuente de datos Prometheus existente. El nombre debe coincidir con una etiqueta real de ejemplar (normalmente `trace_id`) y `jaeger` debe ser un UID de fuente de datos existente; esto no genera ejemplares.

```yaml
# Prometheus datasource configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
data:
  prometheus.yaml: |
    apiVersion: 1
    datasources:
    - name: Prometheus
      type: prometheus
      jsonData:
        exemplarTraceIdDestinations:
        - datasourceUid: jaeger
          name: trace_id
```

### Integración de Loki → Tempo

Combine los siguientes campos con la fuente de datos Loki existente. Requieren el campo real de registro `trace_id`, trazado habilitado y la misma traza conservada en Tempo; `request_id` no es un ID de traza.

```yaml
# Loki datasource configuration
apiVersion: 1
datasources:
- name: Loki
  type: loki
  jsonData:
    derivedFields:
    - datasourceUid: tempo
      matcherRegex: '"trace_id"\s*:\s*"([0-9a-fA-F]{32})"'
      name: TraceID
      url: '$${__value.raw}'
      urlDisplayLabel: 'View Trace'
```

## Buenas prácticas {#best-practices}

### 1. Organización de paneles

```
Grafana Folder Structure:
├── Istio/
│   ├── Overview/
│   │   ├── Istio Mesh Dashboard
│   │   └── Istio Control Plane Dashboard
│   ├── Services/
│   │   ├── Istio Service Dashboard
│   │   └── Custom Service Dashboards
│   ├── Workloads/
│   │   └── Istio Workload Dashboard
│   ├── Gateways/
│   │   └── Istio Gateway Dashboard
│   └── Logs/
│       ├── Loki Istio Dashboard (#14876)
│       └── Access Log Analysis
```

### 2. Uso de variables

Utilice variables coherentes en todos los paneles:

```json
{
  "templating": {
    "list": [
      {"name": "datasource", "type": "datasource"},
      {"name": "namespace", "type": "query"},
      {"name": "service", "type": "query"},
      {"name": "workload", "type": "query"},
      {"name": "interval", "type": "interval", "auto": true}
    ]
  }
}
```

### 3. Gestión de alertas

- **Alertas por niveles**: crítico (PagerDuty) → advertencia (Slack) → informativo (correo electrónico)
- **Agrupación de alertas**: agrupar por servicio y espacio de nombres
- **Reglas de silenciamiento**: silenciar las alertas durante el mantenimiento

### 4. Optimización del rendimiento

```ini
# Grafana configuration
[dashboards]
min_refresh_interval = 10s

[panels]
disable_sanitize_html = false

[dataproxy]
timeout = 30
```

**Optimización de consultas**:
- Utilice reglas de grabación para calcular previamente las consultas frecuentes
- Utilice `$__rate_interval` para las ventanas de tasas de Prometheus; `$__interval` controla el paso/agrupamiento de la consulta
- Utilice `rate()` para tasas por segundo e `increase()` para totales del intervalo; ambos tienen en cuenta los reinicios de contadores

### 5. Control de acceso

Estos ajustes deshabilitan el acceso anónimo/registro de usuarios y asignan el rol de organización Viewer predeterminado; no son una política RBAC completa por recurso. Configure la credencial de administrador del despliegue existente mediante un Secret de Kubernetes y el mecanismo de secretos documentado de Grafana antes de exponerlo. Este ConfigMap por sí solo no establece una contraseña.

```yaml
# Grafana authentication and default organization role
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-config
data:
  grafana.ini: |
    [auth]
    disable_login_form = false

    [auth.anonymous]
    enabled = false

    [auth.basic]
    enabled = true

    [users]
    allow_sign_up = false
    auto_assign_org = true
    auto_assign_org_role = Viewer

    [security]
    admin_user = admin
```

### 6. Copias de seguridad y recuperación

Haga copias de seguridad de los archivos de paneles/fuentes de datos aprovisionados y exporte los paneles gestionados por la interfaz utilizando la interfaz/API compatible de Grafana. La recuperación completa también necesita la base de datos, la configuración y los plugins de Grafana mediante un procedimiento de copia coherente con la aplicación. No existe el comando `grafana-cli admin export-dashboard`.

Las instantáneas de Prometheus utilizan su API HTTP de administración, no `promtool tsdb snapshot`. La API debe habilitarse deliberadamente en un endpoint de mantenimiento protegido. Tras reenviar el pod de Prometheus seleccionado a localhost, un ejemplo de mantenimiento es:

```bash
curl -fsS -X POST http://localhost:9090/api/v1/admin/tsdb/snapshot
```

La respuesta proporciona el directorio de la instantánea dentro del directorio de datos del servidor. Copie esa instantánea terminada al destino de copia de seguridad; una instantánea en el mismo disco no es una copia de seguridad independiente. Valide por separado la restauración, la retención y la recuperación de escritura remota. No se ejecutó ninguna operación de copia de seguridad/despliegue para esta auditoría documental.

## Referencias

### Documentación oficial
- [Documentación de Kiali](https://kiali.io/docs/)
- [Observabilidad de Istio](https://istio.io/latest/docs/tasks/observability/)
- [Paneles de Grafana](https://grafana.com/grafana/dashboards/)
- [Prometheus Operator](https://prometheus-operator.dev/)

### Paneles de la comunidad
- [Panel Grafana Loki para Istio (#14876)](https://grafana.com/grafana/dashboards/14876)
- [Panel Istio Workload (#7630)](https://grafana.com/grafana/dashboards/7630)
- [Panel Istio Performance (#11829)](https://grafana.com/grafana/dashboards/11829)
- [Panel Istio Wasm Extension (#13277)](https://grafana.com/grafana/dashboards/13277)

### Material de referencia
- [Arquitectura de Kiali](https://kiali.io/docs/architecture/architecture/)
- [Buenas prácticas de Grafana](https://grafana.com/docs/grafana/latest/best-practices/)
- [Ejemplos de consultas de Prometheus](https://prometheus.io/docs/prometheus/latest/querying/examples/)
