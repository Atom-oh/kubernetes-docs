# Cuestionario de observabilidad

> **Última actualización**: 11 de septiembre de 2026 · Istio 1.31 · Kubernetes 1.32–1.36. Consulte instalación y dashboards para límites de compatibilidad EKS/Kiali.

El cuestionario cubre telemetría configurada de sidecars/waypoints. Cada ejemplo es independiente y supone que existen backends, namespaces, permisos y tráfico indicados. Comprobar YAML/API/consultas no equivale a pruebas productivas o de clúster real; ztunnel L4, sidecars nativos y HA necesitan su recogida específica.

## Preguntas de opción múltiple (1-5)

### Pregunta 1: Métricas Prometheus

¿Cuál **no es un nombre/familia de métricas estándar de servicio de Istio**?

A. istio\_requests\_total (total de solicitudes)\
B. istio\_request\_duration\_milliseconds (latencia de solicitud)\
C. istio\_request\_bytes (tamaño de solicitud)\
D. istio\_pod\_cpu\_usage (uso CPU del Pod)

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D**

Las métricas estándar Istio describen tráfico; Envoy también expone estadísticas internas. Prometheus obtiene CPU de contenedores de kubelet/cAdvisor o del pipeline de recursos del runtime. Metrics Server sirve métricas para autoscaling y `kubectl top`; kube-state-metrics expone estado de objetos y requests/limits configurados, no CPU medida.

**Explicación:**

**Métricas recogidas por Istio:**

1. **istio\_requests\_total (A - O)**

```promql
# Request rate by service (per second)
sum(rate(istio_requests_total{reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
```

2. **istio\_request\_duration\_milliseconds (B - O)**

```promql
# P95 latency
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket{reporter="destination"}[5m])) by (le)
)
```

3. **istio\_request\_bytes (C - O)**

```promql
# Request body byte rate (bytes/second), not mean request size
sum(rate(istio_request_bytes_sum{reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
```

4. **istio\_pod\_cpu\_usage (D - X)**

* No es una métrica Istio
* Métrica Kubernetes: `container_cpu_usage_seconds_total`
* Recoja kubelet/cAdvisor; kube-state-metrics ayuda a comparar uso y límites configurados

**Categorías de métricas Istio:**

| Categoría | Métrica de ejemplo | Descripción |
| ------------ | --------------------------------------------- | ----------------------------- |
| **Solicitud** | istio\_requests\_total | Número de solicitudes, códigos de respuesta |
| **Duración** | istio\_request\_duration\_milliseconds | Distribución de latencia |
| **Tamaño** | istio\_request\_bytes, istio\_response\_bytes | Tamaño de tráfico |
| **TCP** | istio\_tcp\_connections\_opened\_total | Conexiones TCP |

**Ejemplos de señales doradas:**

```promql
# 1. Latency
histogram_quantile(0.95,
  sum(rate(
    istio_request_duration_milliseconds_bucket{reporter="destination",
      destination_service_name="reviews", destination_service_namespace="default"
    }[5m]
  )) by (le)
)

# 2. Traffic
sum(rate(
  istio_requests_total{reporter="destination",
    destination_service_name="reviews", destination_service_namespace="default"
  }[5m]
))

# 3. Errors (error rate)
sum(rate(
  istio_requests_total{reporter="destination",
    destination_service_name="reviews", destination_service_namespace="default",
    response_code=~"5.."
  }[5m]
))
/
sum(rate(
  istio_requests_total{reporter="destination",
    destination_service_name="reviews", destination_service_namespace="default"
  }[5m]
))

# 4. Saturation - Uses Kubernetes metrics
sum(rate(
  container_cpu_usage_seconds_total{
    namespace="default", container="istio-proxy", pod=~"reviews-.*"
  }[5m]
))
```

**Comprobar métricas:**

```bash
# Check metrics via Envoy Admin API
istioctl x envoy-stats <pod-name>.default --output prom

# Check in Prometheus
kubectl port-forward -n istio-system svc/prometheus 9090:9090
# Query at http://localhost:9090
```

**Referencia:**

* [Métricas](../../../service-mesh/istio/observability/01-metrics.md)

</details>

***

### Pregunta 2: Trazado distribuido

Con proveedor/backend funcional, ¿qué responsabilidad de la aplicación permite unir spans de proxy entre llamadas de servicios?

A. La aplicación debe generar trace IDs\
B. La aplicación debe propagar cabeceras HTTP\
C. Debe instalarse cliente Jaeger en todos los servicios\
D. Envoy lo gestiona todo automáticamente

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B**

Los proxies configurados pueden generar spans y trace IDs, pero la aplicación debe propagar contexto a sus llamadas salientes. El SDK debe inyectar contexto activo; los IDs de spans hijos pueden cambiar conservando el trace ID. Aplicaciones transparentes sin spans propios pueden reenviar las cabeceras de propagación seleccionadas.

**Explicación:**

**Funcionamiento del trazado distribuido:**

![El Ingress Gateway genera cabeceras de trazado para una solicitud entrante; cada servicio A, B y C propaga contexto al siguiente salto, y todos envían su span a Jaeger.](../../../.gitbook/assets/en-quizzes-service-mesh-istio-observability-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-quizzes-service-mesh-istio-observability-0.html)

La figura muestra propagación B3 a Jaeger configurado. También se admiten W3C y un OpenTelemetry Collector intermedio; las aplicaciones instrumentadas inyectan contexto activo, no copian todas las cabeceras sin cambios.

**Cabeceras HTTP que propagar:**

```text
W3C: traceparent, tracestate
B3 (if configured): b3 OR x-b3-traceid, x-b3-spanid, x-b3-parentspanid, x-b3-sampled
Istio correlation: x-request-id
B3 debug flag: x-b3-flags (do not force debug sampling on ordinary traffic)
```

**Ejemplos de código de aplicación:**

```python
# Python Flask example
from flask import Flask, request
import requests

app = Flask(__name__)

@app.route('/api/users')
def get_users():
    # 1. Extract received headers
    headers = {}
    for header in ['x-request-id', 'traceparent', 'tracestate', 'b3', 'x-b3-traceid', 'x-b3-spanid',
                   'x-b3-parentspanid', 'x-b3-sampled', 'x-b3-flags']:
        if header in request.headers:
            headers[header] = request.headers[header]

    # 2. Propagate headers when calling next service
    response = requests.get(
        'http://user-service/users',
        headers=headers, timeout=3  # Selected propagation format
    )

    response.raise_for_status()
    return response.json()
```

```javascript
// Node.js Express example
const express = require('express');
const axios = require('axios');
const app = express();

app.get('/api/users', async (req, res) => {
  // 1. Extract received headers
  const tracingHeaders = {};
  ['x-request-id', 'traceparent', 'tracestate', 'b3', 'x-b3-traceid', 'x-b3-spanid',
   'x-b3-parentspanid', 'x-b3-sampled', 'x-b3-flags'].forEach(header => {
    if (req.headers[header]) {
      tracingHeaders[header] = req.headers[header];
    }
  });

  // 2. Propagate headers when calling next service
  try {
    const response = await axios.get('http://user-service/users', {
      headers: tracingHeaders, timeout: 3000
    });
    res.json(response.data);
  } catch (error) {
    res.status(502).json({error: 'Downstream request failed'});
  }
});
```

**Análisis de opciones:**

* **A (X)**: Envoy genera trace IDs automáticamente
* **B (O)**: La aplicación debe propagar cabeceras HTTP (obligatorio)
* **C (X)**: No hace falta cliente Jaeger; Envoy envía spans
* **D (X)**: Envoy crea/envía spans, pero propagar cabeceras corresponde a la aplicación

**Configuración de muestreo:**

Se supone el proveedor `otel-tracing` del capítulo de trazas. `1.0` significa 1%, no 100%; proveedor/exporter y propagación son requisitos separados.

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: tracing-sample
  namespace: default
spec:
  tracing:
  - providers:
    - name: otel-tracing
    randomSamplingPercentage: 1.0
```

**Acceso a Jaeger:**

```bash
kubectl port-forward -n observability svc/jaeger-query 16686:16686
```

**Referencia:**

* [Trazado distribuido](../../../service-mesh/istio/observability/02-tracing.md)

</details>

***

### Pregunta 3: Visualización Kiali

¿Qué función **NO** proporciona Kiali?

A. Visualización de topología de servicios\
B. Análisis de flujos de tráfico\
C. Ejecución automática de despliegues canary\
D. Validación de configuración Istio

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C**

Kiali es una **herramienta de observación y análisis**; herramientas como **Argo Rollouts** ejecutan despliegues.

**Explicación:**

**Funciones principales de Kiali:**

**1. Visualización de topología (A - O)**

```bash
# Open Kiali dashboard
istioctl dashboard kiali

# Features:
# - Real-time service connection display
# - Traffic flow direction display
# - Service status (healthy/error)
# - Response time display
```

**Ejemplo de vista de grafo:**

```
Frontend → Backend → Database
   ↓
External API

Color codes:
- Green: Normal
- Red: Error
- Gray: No traffic
```

**2. Análisis de tráfico (B - O)**

Kiali muestra:

* Solicitudes (RPS)
* Tasa de errores (%)
* Latencia P50/P95/P99
* Conexiones TCP

**3. Ejecución automática de canary (C - X)**

* Kiali muestra tráfico y, con permisos, edita configuración Istio/usa asistentes de tráfico
* No sustituye un controlador automatizado de entrega progresiva
* Ejecución de despliegues: Argo Rollouts, Flagger

**4. Validación de configuración Istio (D - O)**

Ejemplos del [catálogo de validaciones Kiali](https://kiali.io/docs/features/validations/):

- VirtualService: subset indefinido (`KIA1107`).
- DestinationRule: definiciones host/subset superpuestas (`KIA0201`).
- AuthorizationPolicy: namespace referenciado no encontrado (`KIA0101`) o principal no asociado a una ServiceAccount descubierta (`KIA0106`).

Las comprobaciones dependen de versión, alcance de descubrimiento y acceso. Inspeccione código/mensaje real y política efectiva; Kiali no demuestra conflictos arbitrarios ni que todo certificado y ruta runtime funcione.

**Instalación Kiali:**

Siga el [capítulo de dashboards](../../../service-mesh/istio/observability/04-dashboards.md) para operador fijado, autenticación y límites actuales. Kiali se instala aparte; los addons de muestra son demos, y Helm sin backend/RBAC no es producción.

**Menús principales:**

```
1. Overview: Service summary by Namespace
2. Graph: Service topology
3. Applications: Application list
4. Workloads: Deployment, StatefulSet, etc.
5. Services: Kubernetes Service
6. Istio Config: VirtualService, DestinationRule, etc.
```

**Kiali frente a otras herramientas:**

| Herramienta | Rol | Entrega progresiva automatizada |
| ----------------- | ----------------------------------- | -------------------- |
| **Kiali** | Visualización, análisis, validación | No |
| **Argo Rollouts** | Entrega progresiva | Sí |
| **Flagger** | Canary automático | Sí |
| **Grafana** | Dashboard de métricas | No |
| **Jaeger** | Trazado distribuido | No |

**Ejemplo práctico:**

```bash
# 1. Check service topology in Kiali
istioctl dashboard kiali

# 2. Detect anomalies in Graph view
#    - reviews service error rate 5%
#    - productpage → reviews latency increase

# 3. Check details in Workload view
#    - Check reviews-v2 Pod logs
#    - Check Envoy metrics

# 4. Validate configuration in Istio Config view
#    - Found typo in VirtualService
#    - Fix and redeploy
```

**Referencia:**

* [Visualización](../../../service-mesh/istio/observability/04-dashboards.md)
* [Documentación oficial Kiali](https://kiali.io/docs/)

</details>

***

### Pregunta 4: Configuración de registros de acceso

¿Cómo configura salida de acceso en **formato JSON** en Istio?

A. Establecer meshConfig.accessLogEncoding a JSON en IstioOperator\
B. Modificar directamente Envoy ConfigMap\
C. Añadir anotación a cada Pod\
D. Convertir a JSON mediante consulta Prometheus

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A**

A es un método MeshConfig válido: use `accessLogEncoding: JSON` con logs habilitados en una entrada `istioctl install -f`. No es un recurso operador dentro del clúster. Un proveedor personalizado `envoyFileAccessLog.logFormat.labels` es otra vía admitida descrita en el capítulo de logs.

**Explicación:**

**Configuración de acceso JSON:**

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    # Enable Access Log
    accessLogFile: /dev/stdout

    # Output in JSON format
    accessLogEncoding: JSON

    # Define custom JSON format
    accessLogFormat: |
      {
        "log_type": "access",
        "start_time": "%START_TIME%",
        "method": "%REQ(:METHOD)%",
        "path": "%REQ_WITHOUT_QUERY(X-ENVOY-ORIGINAL-PATH?:PATH)%",
        "protocol": "%PROTOCOL%",
        "response_code": "%RESPONSE_CODE%",
        "response_flags": "%RESPONSE_FLAGS%",
        "bytes_received": "%BYTES_RECEIVED%",
        "bytes_sent": "%BYTES_SENT%",
        "duration": "%DURATION%",
        "upstream_service_time": "%RESP(X-ENVOY-UPSTREAM-SERVICE-TIME)%",
        "x_forwarded_for": "%REQ(X-FORWARDED-FOR)%",
        "user_agent": "%REQ(USER-AGENT)%",
        "request_id": "%REQ(X-REQUEST-ID)%",
        "authority": "%REQ(:AUTHORITY)%",
        "upstream_host": "%UPSTREAM_HOST%",
        "upstream_cluster": "%UPSTREAM_CLUSTER%",
        "upstream_local_address": "%UPSTREAM_LOCAL_ADDRESS%",
        "downstream_local_address": "%DOWNSTREAM_LOCAL_ADDRESS%",
        "downstream_remote_address": "%DOWNSTREAM_REMOTE_ADDRESS%",
        "requested_server_name": "%REQUESTED_SERVER_NAME%",
        "route_name": "%ROUTE_NAME%"
      }
```

**Ejemplo de salida:**

```json
{
  "log_type": "access",
  "start_time": "2025-01-20T10:30:00.123Z",
  "method": "GET",
  "path": "/api/users",
  "protocol": "HTTP/1.1",
  "response_code": 200,
  "response_flags": "-",
  "bytes_received": 0,
  "bytes_sent": 1234,
  "duration": 42,
  "upstream_service_time": "40",
  "x_forwarded_for": "192.168.1.100",
  "user_agent": "Mozilla/5.0",
  "request_id": "abc-123-def",
  "authority": "example.com",
  "upstream_host": "10.0.1.20:8080",
  "upstream_cluster": "outbound|8080||backend.default.svc.cluster.local",
  "upstream_local_address": "10.0.1.10:54321",
  "downstream_local_address": "10.0.1.10:8080",
  "downstream_remote_address": "10.0.1.5:12345",
  "requested_server_name": "-",
  "route_name": "default"
}
```

**Configuración por namespace:**

Para esta alternativa, defina primero `mesh-json` como en el capítulo de logs. Telemetry selecciona proveedor/alcance; no cambia por sí mismo el formato.

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: access-logging
  namespace: production
spec:
  accessLogging:
  - providers:
    - name: mesh-json
    # Select the already-defined JSON provider
```

**Variables de formato Envoy:**

```text
# Key variables:
%START_TIME%: Request start time
%REQ(HEADER)%: Request header
%RESP(HEADER)%: Response header
%RESPONSE_CODE%: HTTP response code
%DURATION%: Total duration (ms)
%BYTES_RECEIVED%: Bytes received
%BYTES_SENT%: Bytes sent
%UPSTREAM_HOST%: Upstream server address
%DOWNSTREAM_REMOTE_ADDRESS%: Client address
```

**Integración CloudWatch Logs:**

Solo es un fragmento de salida de un agente Fluent Bit ya desplegado con etiquetas de entrada, parsing CRI/JSON, credenciales IAM y montajes coincidentes. Un ConfigMap no recoge logs por sí solo. EKS Fargate necesita su configuración admitida de log-router.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: istio-system
data:
  output.conf: |
    [OUTPUT]
        Name cloudwatch_logs
        Match *
        region us-east-1
        log_group_name /aws/eks/istio/access-logs
        log_stream_prefix istio-
        auto_create_group true
```

**Comprobar logs:**

```bash
# Check Pod's Access Log
kubectl logs <pod-name> -c istio-proxy

# Real-time monitoring
kubectl logs -f <pod-name> -c istio-proxy | jq -R 'fromjson?'

# Filter specific response codes
kubectl logs <pod-name> -c istio-proxy | \
  jq -R 'fromjson? | select((.response_code | tonumber?) == 500)'
```

**Formato TEXT frente a JSON:**

| Elemento | TEXT | JSON |
| --------------- | ------------ | --------------- |
| **Legibilidad** | Alta para humanos | Baja para humanos |
| **Parsing** | Difícil | Fácil para máquinas |
| **Tamaño** | Pequeño | Grande |
| **Estructura** | No estructurado | Estructurado |
| **Consultas** | Difíciles | Fáciles con jq, etc. |

**Ejemplo TEXT:**

```
[2025-01-20T10:30:00.123Z] "GET /api/users HTTP/1.1" 200 - "-" "-" 0 1234 42 40 "192.168.1.100" "Mozilla/5.0" "abc-123-def" "example.com" "10.0.1.20:8080" outbound|8080||backend.default.svc.cluster.local 10.0.1.10:54321 10.0.1.10:8080 10.0.1.5:12345 - default
```

**Referencia:**

* [Registros](../../../service-mesh/istio/observability/03-logging.md)
* [Formato de acceso Envoy](https://www.envoyproxy.io/docs/envoy/latest/configuration/observability/access_log/usage)

</details>

***

### Pregunta 5: Dashboards Grafana

¿Qué dashboard **no** forma parte del conjunto Grafana publicado por Istio?

A. Dashboard de servicios Istio\
B. Dashboard de cargas Istio\
C. Dashboard de rendimiento Istio\
D. Dashboard de costes Istio

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D**

D. Istio publica dashboards de tráfico/plano de control, pero Grafana es un addon independiente; instalar Istio no instala automáticamente estos dashboards.

**Explicación:**

El catálogo 1.31 incluye Service7636, Workload7630, Mesh7639, Performance11829, Control Plane7645, Wasm13277 y Ztunnel21306. Performance se centra en recursos/datos; paneles xDS/webhook corresponden principalmente a Control Plane. Mesh incluye tráfico global y versiones, no todos los paneles de latencia antes listados. Seleccione la revisión correspondiente a su Istio.

No se calcula coste multiplicando `istio_requests_total` por precio de transferencia GB: solicitudes no son bytes, y `source_cluster`/`destination_cluster` identifican clústeres, no AZ. Memoria de proxy es uso, no factura. Costear red exige bytes facturables y reglas reales de ubicación/servicio origen/destino; asignar recursos exige precios de nodo, tiempo y modelo explícito. Concilie con AWS billing/CUR y precios aplicables, sin afirmar una fórmula fija.

Use el [capítulo de dashboards](../../../service-mesh/istio/observability/04-dashboards.md) para revisiones verificadas y ejemplos completos JSON/provisioning. ConfigMaps y etiquetas no instalan por sí solos un cargador ni resuelven entradas de datasource.

</details>

***

## Preguntas breves (6-10)

### Pregunta 6: Monitorización de señales doradas

Explique cómo monitorizar las **señales doradas** de Google SRE (latencia, tráfico, errores, saturación) con Istio y Prometheus. Incluya **consultas Prometheus** y **reglas de alerta** para cada señal.

<details>

<summary>Mostrar respuesta</summary>

Use un reporter por cálculo de salto y conserve namespace de servicio y clúster cuando corresponda. Destination mide solicitudes recibidas; source es necesario para fallos upstream que nunca llegan. HTTP5xx es solo una definición; gRPC requiere `grpc_response_status` y SLI específicos. La latencia siguiente es milisegundos y las tasas por segundo:

```promql
histogram_quantile(0.95, sum by (destination_service_name, destination_service_namespace, le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination"}[5m])))

histogram_quantile(0.99, sum by (destination_service_name, destination_service_namespace, le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination"}[5m])))

sum by (destination_service_name, destination_service_namespace) (rate(istio_requests_total{reporter="destination"}[5m]))

sum by (destination_service_name, destination_service_namespace) (rate(istio_requests_total{reporter="destination",response_code=~"5.."}[5m])) / sum by (destination_service_name, destination_service_namespace) (rate(istio_requests_total{reporter="destination"}[5m]))
```

En un clúster sidecar clásico, las proporciones uso/limit necesitan kubelet/cAdvisor y kube-state-metrics. Excluya límites ausentes/cero. Sidecars nativos pueden declarar límites en series de recursos init; confirme la familia real antes de usar:

```promql
sum by (namespace, pod, container) (rate(container_cpu_usage_seconds_total{container="istio-proxy"}[5m])) / on (namespace, pod, container) (max by (namespace, pod, container) (kube_pod_container_resource_limits{container="istio-proxy",resource="cpu",unit="core"}) > 0)

max by (namespace, pod, container) (container_memory_working_set_bytes{container="istio-proxy"}) / on (namespace, pod, container) (max by (namespace, pod, container) (kube_pod_container_resource_limits{container="istio-proxy",resource="memory",unit="byte"}) > 0)

envoy_cluster_upstream_cx_active
envoy_cluster_upstream_rq_pending_active
envoy_cluster_circuit_breakers_default_cx_open
```

`_cx_open` es gauge de estado 0/1; dividir conexiones activas por él no da utilización. Inspeccione umbrales configurados del breaker para proporciones de capacidad. CPU rate se mide en núcleos antes de dividir; working set, en bytes. Desglosar por método requiere añadir previamente una etiqueta Telemetry `request_method` acotada.

El Prometheus Operator instalado debe seleccionar la PrometheusRule. Umbrales y ventanas son ilustrativos; estacionalidad, no-data, fallos de scrape y volumen mínimo requieren tratamiento propio. La hora anterior no es una base normal aprendida.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: istio-golden-signals
  namespace: monitoring
spec:
  groups:
  - name: golden-signals
    rules:
    - alert: HighLatency
      expr: histogram_quantile(0.95, sum by (destination_service_name, destination_service_namespace,
        le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination"}[5m]))) > 500
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: P95 request duration exceeds500ms
    - alert: TrafficSpike
      expr: sum by (destination_service_name, destination_service_namespace) (rate(istio_requests_total{reporter="destination"}[5m]))
        > 2 * sum by (destination_service_name, destination_service_namespace) (rate(istio_requests_total{reporter="destination"}[1h]
        offset 1h))
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Traffic exceeds the previous comparison window
    - alert: HighErrorRate
      expr: sum by (destination_service_name, destination_service_namespace) (rate(istio_requests_total{reporter="destination",response_code=~"5.."}[5m]))
        / sum by (destination_service_name, destination_service_namespace) (rate(istio_requests_total{reporter="destination"}[5m]))
        > 0.01
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: HTTP5xx fraction exceeds1%
    - alert: HighEnvoyCPU
      expr: sum by (namespace, pod, container) (rate(container_cpu_usage_seconds_total{container="istio-proxy"}[5m]))
        / on (namespace, pod, container) (max by (namespace, pod, container) (kube_pod_container_resource_limits{container="istio-proxy",resource="cpu",unit="core"})
        > 0) > 0.8
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Proxy CPU consumption exceeds80% of its configured limit
    - alert: HighEnvoyMemory
      expr: max by (namespace, pod, container) (container_memory_working_set_bytes{container="istio-proxy"})
        / on (namespace, pod, container) (max by (namespace, pod, container) (kube_pod_container_resource_limits{container="istio-proxy",resource="memory",unit="byte"})
        > 0) > 0.8
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Proxy working set exceeds80% of its configured limit
    - alert: ConnectionBreakerAtCapacity
      expr: envoy_cluster_circuit_breakers_default_cx_open == 1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Connection breaker at capacity
```

Cree paneles separados para tasa, fracción de errores, latencia y unidades de recursos usando la [plantilla verificada](../../../service-mesh/istio/observability/04-dashboards.md). No comparta una escala sin etiquetas entre núcleos CPU y bytes de memoria.

</details>

***

### Pregunta 7: Encontrar cuellos de botella con Jaeger

Explique cómo usar Jaeger para detectar **cuellos de botella de rendimiento** en microservicios. Incluya **métodos de análisis de trazas** y **escenarios prácticos de depuración**.

<details>

<summary>Mostrar respuesta</summary>

Comience por [Jaeger2/OTLP](../../../service-mesh/istio/observability/02-tracing.md), proveedor Telemetry configurado y propagación de contexto. No asuma que un addon Jaeger antiguo/puerto Zipkin o una tasa de muestreo despliegan trazas. Los spans de aplicación/DB requieren SDK/agente; los spans de proxy no revelan el interior de una consulta SQL.

1. Localice servicio/ventana afectados con una consulta de latencia Prometheus por namespace y busque trazas lentas y normales representativas en Jaeger. Un histograma devuelve estadísticas agregadas, no trace IDs.
2. Siga el camino crítico y distinga duración padre de tiempo exclusivo. Un padre largo incluye hijos; no es automáticamente la causa.
3. Compare errores, reintentos, espera de conexión, ejecución de consultas y paralelismo. Tiempos, muestreo y spans ausentes limitan las conclusiones.

```promql
histogram_quantile(0.99, sum by (destination_service_name, destination_service_namespace, le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination"}[5m]))) > 2000
```

```bash
kubectl port-forward -n observability svc/jaeger-query 16686:16686
```

Son escenarios hipotéticos, no benchmarks ni respuestas literales de la API Jaeger:

| Observación | Qué verificar | Respuesta adecuada |
|---|---|---|
| Solicitud de 2.1s con operación DB instrumentada de 1.8s | Separar espera de pool, consulta, bloqueos y red; verificar plan DB | Corregir la causa medida. Un ConfigMap `redis.conf` no añade caché a la aplicación |
| Solicitud de ~10s con timeout de pool | Inspeccionar pool cliente DB, concurrencia y capacidad | Ajustar pool aplicación/DB y reparar fugas; DestinationRule no configura el pool de aplicación y los ajustes HTTP no afinan PostgreSQL |
| Llamadas independientes 2s+2s+1s secuenciales | Confirmar dependencias, límites y contexto | Paralelizar solo E/S independiente con clientes async reales o hilos acotados; puede acercarse a la llamada más larga más sobrecarga, no garantiza 2s |

Para callbacks síncronos existentes, este fragmento Python3.9+ conserva el orden de retorno y usa hilos. La aplicación debe proporcionar callbacks y sus timeouts; cancelar la tarea que espera no detiene un hilo ya activo:

```python
import asyncio

async def get_user_data(user_id):
    # Application-owned synchronous I/O functions; each must enforce its timeout.
    profile, orders, recommendations = await asyncio.gather(
        asyncio.to_thread(call_backend_a, user_id),
        asyncio.to_thread(call_backend_b, user_id),
        asyncio.to_thread(call_backend_c, user_id),
    )
    return merge(profile, orders, recommendations)
```

Timeouts acotan espera, no reparan una DB lenta; reintentar puede amplificar carga. Al mostrar timeout VirtualService, incluya destino real y use reintentos considerando idempotencia/carga. Los mapas persistentes de dependencias Jaeger pueden necesitar agregación adicional; una cascada de traza y un mapa global son vistas distintas. Valide una posible corrección con tráfico repetido y métricas/trazas, no una sola traza atractiva.

</details>

***

### Pregunta 8: Diagnóstico de malla con Kiali

Explique cómo diagnosticar y resolver **problemas comunes** de Istio (errores de configuración, anomalías de tráfico, conflictos de seguridad) con Kiali.

<details>

<summary>Mostrar respuesta</summary>

Use comprobaciones de configuración, tráfico observado, logs Pod y trazas como evidencia y verifique la configuración efectiva. El capítulo dashboards documenta versión/autenticación. No invente una advertencia por la forma del grafo ni trate un icono verde como garantía runtime.

| Síntoma | Interpretación y comprobaciones correctas |
|---|---|
| Servicio/subset ausente | En `default`, `reviews` y `reviews.default.svc.cluster.local` resuelven al mismo host. Acortar el nombre no crea Service. KIA1107 identifica subset indefinido; revise Service/EndpointSlice, DestinationRule y etiquetas Pod |
| Etiqueta subset no coincide | `1.0` no es intrínsecamente erróneo; haga coincidir etiquetas Deployment y subset. Incluya metadata, host y separadores al escribir DestinationRules completas |
| Se observa 90/10 en vez de 50/50 | Revise pesos efectivos, reglas, afinidad, reintentos, endpoints/expulsión y ventana. Menos réplicas listas no redefinen pesos ni garantizan un reparto posterior 50/50 |
| Ciclo A↔B | Un grafo bidireccional no demuestra recursión, deadlock ni alerta automática. Identifique un ciclo real no deseado en trazas antes de rediseñar |
| HTTP403 | Inspeccione política, identidad y respuesta del proxy que aplica el control. AuthorizationPolicy con spec vacío es ALLOW sin reglas; otra ALLOW puede conceder excepción. No es un DENY dominante |
| Fallo mTLS | PeerAuthentication describe al receptor. Revise TLS del emisor, política receptora, inscripción, certificado/confianza y protocolo para esa dirección. Modos receptores distintos no son automáticamente conflicto; STRICT general es migración, no arreglo genérico |

Una base de denegación por defecto con excepción frontend es válida si mTLS aporta el principal frontend nombrado y ningún CUSTOM/DENY anterior rechaza:

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-default-deny
  namespace: default
spec:
  selector:
    matchLabels:
      app: backend
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-allow-frontend
  namespace: default
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/default/sa/frontend
```

```bash
kubectl get service reviews -n default
kubectl get endpointslice -n default -l kubernetes.io/service-name=reviews
kubectl get pods -n default -l app=reviews --show-labels
istioctl analyze -n default
istioctl proxy-config clusters <source-pod> -n default --fqdn reviews.default.svc.cluster.local -o json
istioctl x authz check <backend-pod>.default
```

La animación resume una ventana; no inspecciona paquetes byte a byte. Si falla la hipótesis, repita diagnóstico/configuración/prueba, no reinicie cargas a ciegas.

![Bucle Kiali: abrir Graph, clasificar ausencia de tráfico, errores, lentitud o rechazo; revisar configuración, logs, trazas o políticas; corregir, probar y repetir si no se resuelve.](../../../.gitbook/assets/en-quizzes-service-mesh-istio-observability-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-quizzes-service-mesh-istio-observability-1.html)

</details>

***

### Pregunta 9: Stack de observabilidad de producción

Explique cómo desplegar Prometheus, Grafana, Jaeger y Kiali en **alta disponibilidad (HA)** para Kubernetes de producción. Incluya **almacenamiento persistente**, **escalado** y **copias de seguridad**.

<details>

<summary>Mostrar respuesta</summary>

Un stack HA productivo requiere diseño y verificación propios. Lo siguiente cubre requisitos principales, no un paquete probado en producción. Fije versiones compatibles Kubernetes/Istio/operador/chart/backend, revise values reales y valide fallos/restauración antes del despliegue. El [capítulo dashboards](../../../service-mesh/istio/observability/04-dashboards.md) registra la brecha actual de compatibilidad Kiali; latest no la demuestra.

| Componente | Estado y requisitos HA |
|---|---|
| Prometheus | Réplicas independientes con PVC por réplica, misma etiqueta de clúster y etiquetas de réplica distintas; el resto debe coincidir para deduplicar. Distribuya dominios de fallo y dimensione retención por ingesta. Un LB no fusiona historiales |
| Thanos | Sidecars exponen StoreAPI y opcionalmente suben bloques; Query descubre endpoints reales y deduplica la etiqueta configurada. Store Gateway lee objetos; Compactor compacta/retiene con propiedad adecuada de escritor único/sharding |
| Grafana | Dos réplicas necesitan PostgreSQL/MySQL compartido HA, provisioning/plugins/secretos coherentes y LB. Compartir SQLite o un EBS ReadWriteOnce entre nodos no es HA |
| Alertmanager | Réplicas requieren peers/deduplicación de notificaciones, estado persistente y credenciales seguras; un webhook Slack en values no es diseño completo |
| Jaeger2/collector | Réplicas query/collector sin estado con backend duradero admitido y su HA/TLS/credenciales. Tail sampling necesita afinidad trace ID; Service aleatorio no entrega trazas completas a cada sampler |
| Kiali | Operador/servidor compatible, configuración/secreto de sesión compartidos y ubicación adecuada. Proteja API backend y permisos de namespaces. Estrategia token es de un clúster; use autenticación multiclúster documentada cuando haga falta |

**Conexión del almacenamiento y object store**:

- Mantenga persistencia local Prometheus aunque use objetos: head/WAL reciente puede no haberse subido. Para sidecars, siga requisitos de compactación local/duración de bloques de su Thanos.
- Deben existir bucket S3, endpoint regional, cifrado, retención e IAM. Vincule la ServiceAccount con credenciales a Pods que ejecutan sidecar/Store/Compactor. Un comentario «IRSA» no crea credenciales. Thanos S3 actual puede usar `aws_sdk_auth: true` con su cadena AWS SDK compatible.
- En kube-prometheus-stack actual, seleccione el Secret existente bajo `prometheus.prometheusSpec.thanos.objectStorageConfig.existingSecret` con nombre/clave reales. Montar `thanos.yaml` no crea `objstore.yaml`. Verifique rutas, puertos gRPC nombrados y destinos DNS-SRV.
- Thanos Query actual usa `--endpoint` y `--query.replica-label`. No arrastre `--store` antiguo sin verificar versión. Kiali con backend Prometheus compatible puede necesitar `thanos_proxy` documentado.
- Cada Deployment/StatefulSet necesita selectores/etiquetas y Services coincidentes; los antiguos recursos incompletos no formaban una topología StoreAPI funcional. En EKS, estado EBS requiere ubicación EC2/CSI compatible; Fargate no monta EBS ni ejecuta DaemonSets arbitrarios.

**Configuración, respaldo y evidencia**:

1. Configure selectores monitor/reglas y targets reales. En kube-prometheus-stack, `alertmanager.config` es hermano de `alertmanager.alertmanagerSpec`; verifique esquema fijado. Mantenga contraseñas/webhooks en referencias Secret admitidas.
2. Respalde base/configuración/dashboards/plugins Grafana, estado Prometheus necesario y almacenamiento Jaeger con procedimientos consistentes con la aplicación. Retención de objetos no restaura por sí sola todos los componentes.
3. Manifiestos PVC/PV Velero no demuestran captura de datos. Configure snapshots CSI/data-mover o backups de archivos admitidos, clases/plugins, credenciales y recursos de restauración. Inspeccione estado y restaure en aislamiento.
4. Un Job de backup necesita imagen probada con herramientas, URL correcta, identidad limitada, bucket y manejo de errores. El antiguo CronJob con imagen AWS CLI y curl+jq supuestos no era una solución verificada.
5. Monitorice fallos de receptores/exporters, colas, scrapes y capacidad PVC real. `prometheus_tsdb_storage_blocks_bytes_total` no es denominador válido. Un stack no informa fiablemente de su caída total; use heartbeat/observador independiente y distinga series ausentes/no-data de `up == 0`.
6. Pruebe pérdida de réplica/nodo/zona, interrupción de almacenamiento, fallo backend/autenticación, rollout y restauración. PDB ayuda con interrupciones planificadas; no crea HA de DB o zona. Registre RPO/RTO y capacidad observada, no los deduzca de réplicas.

Consulte [Grafana HA](https://grafana.com/docs/grafana/latest/setup-grafana/set-up-for-high-availability/), [Thanos Sidecar](https://thanos.io/tip/components/sidecar.md/), [Thanos Query](https://thanos.io/tip/components/query.md/), [almacenamiento Thanos](https://thanos.io/tip/thanos/storage.md/) y [backup CSI Velero](https://velero.io/docs/main/csi/).

</details>

***

### Pregunta 10: Métricas personalizadas y dashboards

Explique cómo recoger **métricas de negocio**, como pedidos o éxito de pagos, además de las predeterminadas de Envoy Istio, y crear un dashboard Grafana.

<details>

<summary>Mostrar respuesta</summary>

Defina evento y límite de conteo antes de elegir métricas. Envoy conoce solicitudes, no si se creó un pedido de forma duradera o se liquidó un pago. Los siguientes **fragmentos cuentan intentos de procesamiento completados**, no pedidos únicos ni ingresos contables. La aplicación debe aportar funciones/contrato de errores, idempotencia y validación. Para éxito de pagos real, instrumente resultados en el límite de pago y derive una proporción de contadores; un Gauge sin mantener no es una tasa de éxito.

Use etiquetas de categoría/estado acotadas, Counter para intentos e Histograms para importes/duración no negativos. Observe duración en `finally` para incluir fallos. No etiquete con IDs de pedido/usuario ni URL brutas. Son ejemplos de un proceso; varios workers necesitan la configuración admitida por la biblioteca.

**Python/Flask** (la aplicación aporta `process_order` y `PaymentException`):

```python
from flask import Flask, request, jsonify, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time

# Integration fragment: your application supplies process_order and PaymentException.
# process_order returns a validated nonnegative USD amount and category after processing.
app = Flask(__name__)
CATEGORIES = {"books", "electronics", "other"}
STATUSES = ("success", "payment_failed", "error")
orders_total = Counter("orders_total", "Completed order-processing attempts", ["status", "product_category"])
order_amount = Histogram("order_amount_dollars", "Observed amounts of successful attempts in USD",
                         buckets=[10, 50, 100, 500, 1000, 5000])
order_duration = Histogram("order_processing_duration_seconds", "Order attempt duration, including failures",
                           buckets=[0.1, 0.5, 1.0, 2.0, 5.0])
for status in STATUSES:
    for category in CATEGORIES:
        orders_total.labels(status=status, product_category=category).inc(0)

@app.post("/api/orders")
def create_order():
    payload = request.get_json()
    started = time.perf_counter()
    try:
        order = process_order(payload)
        category = order["category"] if order["category"] in CATEGORIES else "other"
        orders_total.labels(status="success", product_category=category).inc()
        order_amount.observe(order["amount"])
        return jsonify(order), 201
    except PaymentException:
        orders_total.labels(status="payment_failed", product_category="other").inc()
        return jsonify({"error": "Payment failed"}), 400
    except Exception:
        orders_total.labels(status="error", product_category="other").inc()
        return jsonify({"error": "Order processing failed"}), 500
    finally:
        order_duration.observe(time.perf_counter() - started)

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), content_type=CONTENT_TYPE_LATEST)

# Use the application's server lifecycle. Do not treat a Flask development server
# or process-local counters as a production accounting system.
```

**Node.js/Express**: el paquete mantenido es `@prometheus-io/client`, con API comprobada en 0.16.1 sobre Node 22. `prom-client` está obsoleto en su favor; los proyectos existentes deben revisar el changelog de migración. Configure middleware JSON y espere `register.metrics()`:

```javascript
const express = require('express');
const client = require('@prometheus-io/client'); // Example verified with 0.16.1, Node 22
const app = express();
app.use(express.json());
const register = new client.Registry();
const categories = new Set(['books', 'electronics', 'other']);
const ordersTotal = new client.Counter({
  name: 'orders_total', help: 'Completed order-processing attempts',
  labelNames: ['status', 'product_category'], registers: [register]
});
const orderAmount = new client.Histogram({
  name: 'order_amount_dollars', help: 'Observed successful attempt amounts in USD',
  buckets: [10, 50, 100, 500, 1000, 5000], registers: [register]
});
const orderDuration = new client.Histogram({
  name: 'order_processing_duration_seconds', help: 'Order attempt duration, including failures',
  buckets: [0.1, 0.5, 1, 2, 5], registers: [register]
});
for (const status of ['success', 'payment_failed', 'error']) {
  for (const product_category of categories) ordersTotal.inc({status, product_category}, 0);
}
// The application supplies async processOrder with validated amount/category output.
app.post('/api/orders', async (req, res) => {
  const end = orderDuration.startTimer();
  try {
    const order = await processOrder(req.body);
    const product_category = categories.has(order.category) ? order.category : 'other';
    ordersTotal.inc({status: 'success', product_category});
    orderAmount.observe(order.amount);
    res.status(201).json(order);
  } catch (error) {
    const status = error.code === 'PAYMENT_FAILED' ? 'payment_failed' : 'error';
    ordersTotal.inc({status, product_category: 'other'});
    res.status(status === 'payment_failed' ? 400 : 500).json({error: 'Order processing failed'});
  } finally {
    end();
  }
});
app.get('/metrics', async (req, res) => {
  try {
    res.set('Content-Type', register.contentType);
    res.end(await register.metrics());
  } catch (error) {
    res.status(500).end();
  }
});
// Integrate app.listen/shutdown with the application's server lifecycle.
```

**Recogida Kubernetes**: este laboratorio sidecar usa el endpoint fusionado Istio, sin asumir que un scrape de aplicación en texto plano atraviese STRICT mTLS. Combine etiquetas/anotaciones en el Deployment real `order-service` de `default`; su imagen debe incluir la aplicación y exponer `/metrics` en 8080. Debe habilitarse Prometheus merging. El endpoint de agente 15020 es texto plano: restrinja red. Si ya se recogen estas métricas, no añada monitor duplicado.

```yaml
spec:
  template:
    metadata:
      labels:
        app: order-service
      annotations:
        prometheus.io/scrape: 'true'
        prometheus.io/path: /metrics
        prometheus.io/port: '8080'
        prometheus.istio.io/merge-metrics: 'true'
```

```yaml
apiVersion: v1
kind: Service
metadata:
  name: order-service
  namespace: default
  labels:
    app: order-service
spec:
  selector:
    app: order-service
  ports:
  - name: http
    port: 8080
    targetPort: 8080
  - name: merged-metrics
    port: 15020
    targetPort: 15020
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: order-service-metrics
  namespace: istio-system
spec:
  namespaceSelector:
    matchNames:
    - default
  selector:
    matchLabels:
      app: order-service
  targetLabels:
  - app
  endpoints:
  - port: merged-metrics
    path: /stats/prometheus
    interval: 30s
    metricRelabelings:
    - sourceLabels:
      - __name__
      regex: orders_total|order_amount_dollars_(bucket|sum|count)|order_processing_duration_seconds_(bucket|sum|count)
      action: keep
```

Prometheus debe seleccionar ServiceMonitor de `istio-system`, que descubre Service en `default`. Conservar solo familias de negocio evita duplicar métricas de proxy recogidas por otra vía. `targetLabels` añade explícitamente `app` del Service. Es un ejemplo sidecar; scraping ambient/TLS directo requiere otro diseño admitido.

**Consultas** (en orden: intentos del intervalo, intentos/segundo, fracción de éxito, P95 de importe observado, P99 de duración, tasa por categoría, fracción de fallo de pago entre intentos de pedido):

```promql
sum(increase(orders_total{namespace="default",app="order-service"}[5m]))

sum(rate(orders_total{namespace="default",app="order-service"}[5m]))

sum(rate(orders_total{namespace="default",app="order-service",status="success"}[5m])) / sum(rate(orders_total{namespace="default",app="order-service"}[5m]))

histogram_quantile(0.95, sum by (le) (rate(order_amount_dollars_bucket{namespace="default",app="order-service"}[5m])))

histogram_quantile(0.99, sum by (le) (rate(order_processing_duration_seconds_bucket{namespace="default",app="order-service"}[5m])))

sum by (product_category) (rate(orders_total{namespace="default",app="order-service"}[5m]))

sum(rate(orders_total{namespace="default",app="order-service",status="payment_failed"}[5m])) / sum(rate(orders_total{namespace="default",app="order-service"}[5m]))
```

`increase` estima total del intervalo; `rate` es por segundo. Reinicios, reintentos y scrapes perdidos significan que contadores/importes operativos no son un libro contable. Para pedidos únicos confirmados o ingresos, concilie con el sistema duradero, sin asumir telemetría exactamente una vez.

**Grafana**: el objeto completo espera UID datasource `prometheus` y etiquetas del monitor. Guárdelo sin wrapper API y use el [provisioning documentado de archivos](../../../service-mesh/istio/observability/04-dashboards.md). Una etiqueta ConfigMap no configura por sí sola un proveedor.

```json
{
  "uid": "order-business-metrics",
  "title": "Order Processing Operational Metrics",
  "timezone": "browser",
  "panels": [
    {
      "id": 1,
      "title": "Completed Attempts per Minute",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "sum(rate(orders_total{namespace=\"default\",app=\"order-service\"}[5m])) * 60",
          "refId": "A"
        }
      ],
      "gridPos": {
        "x": 0,
        "y": 0,
        "w": 12,
        "h": 8
      }
    },
    {
      "id": 2,
      "title": "Attempt Success Fraction",
      "type": "gauge",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "sum(rate(orders_total{namespace=\"default\",app=\"order-service\",status=\"success\"}[5m])) / sum(rate(orders_total{namespace=\"default\",app=\"order-service\"}[5m]))",
          "refId": "A"
        }
      ],
      "gridPos": {
        "x": 12,
        "y": 0,
        "w": 12,
        "h": 8
      },
      "fieldConfig": {
        "defaults": {
          "unit": "percentunit"
        }
      }
    },
    {
      "id": 3,
      "title": "Processing P95",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "histogram_quantile(0.95, sum by (le) (rate(order_processing_duration_seconds_bucket{namespace=\"default\",app=\"order-service\"}[5m])))",
          "refId": "A"
        }
      ],
      "gridPos": {
        "x": 0,
        "y": 8,
        "w": 12,
        "h": 8
      },
      "fieldConfig": {
        "defaults": {
          "unit": "s"
        }
      }
    },
    {
      "id": 4,
      "title": "Observed Successful Attempt Amount (Last Hour)",
      "type": "stat",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "sum(increase(order_amount_dollars_sum{namespace=\"default\",app=\"order-service\"}[1h]))",
          "refId": "A"
        }
      ],
      "gridPos": {
        "x": 12,
        "y": 8,
        "w": 12,
        "h": 8
      },
      "fieldConfig": {
        "defaults": {
          "unit": "currencyUSD"
        }
      }
    }
  ],
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "refresh": "30s"
}
```

**Alertas**: seleccione la regla con Prometheus Operator. El mínimo de tráfico evita alertar por proporción sin tráfico; ausencia/fallo de scrape necesita otra señal. Los umbrales son ejemplos, no garantías SLO.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: business-metrics-alerts
  namespace: istio-system
spec:
  groups:
  - name: business-metrics
    rules:
    - alert: LowOrderAttemptSuccessFraction
      expr: (sum(rate(orders_total{namespace="default",app="order-service",status="success"}[5m])) / sum(rate(orders_total{namespace="default",app="order-service"}[5m]))
        < 0.95) and (sum(rate(orders_total{namespace="default",app="order-service"}[5m])) > 0.1)
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Order-processing attempt success fraction below95%
    - alert: SlowOrderProcessing
      expr: histogram_quantile(0.95, sum by (le) (rate(order_processing_duration_seconds_bucket{namespace="default",app="order-service"}[5m])))
        > 2
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: P95 processing attempt duration exceeds2s
```

Consulte el [cliente Python](https://prometheus.github.io/client_python/) y el [cliente JavaScript](https://github.com/prometheus/client_js) para tipos, exposición y modelos de proceso.

</details>

***

## Cálculo de puntuación

* Opción múltiple 1-5: 10 puntos cada una (50 en total)
* Respuesta breve 6-10: 10 puntos cada una (50 en total)
* **Total: 100 puntos**

**Criterios de evaluación:**

* 90-100 puntos: Excelente comprensión de estos temas
* 80-89 puntos: Buena comprensión; validar despliegues sigue siendo independiente
* 70-79 puntos: Media (se recomienda seguir aprendiendo)
* 60-69 puntos: Por debajo de la media (repasar conceptos básicos)
* 0-59 puntos: Necesita volver a estudiar

## Recursos de aprendizaje

* [Métricas](../../../service-mesh/istio/observability/01-metrics.md)
* [Trazado distribuido](../../../service-mesh/istio/observability/02-tracing.md)
* [Registros](../../../service-mesh/istio/observability/03-logging.md)
* [Visualización](../../../service-mesh/istio/observability/04-dashboards.md)
