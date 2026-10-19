# Cuestionario de observabilidad

> **Última actualización**: 12 de octubre de 2026
>
> **Versiones**: Istio 1.31, compatible con Kubernetes 1.32–1.37.
> Consulta los capítulos de instalación y paneles para conocer los límites de compatibilidad de EKS y Kiali.

Este cuestionario abarca la telemetría configurada para sidecars y waypoints. Cada ejemplo es independiente y presupone que existen los backends, espacios de nombres, permisos y tráfico indicados. Las comprobaciones de YAML, API y consultas no son pruebas de producción ni de un clúster en ejecución. ztunnel en L4, los sidecars nativos y los despliegues de alta disponibilidad requieren una configuración de recopilación específica.

## Preguntas de opción múltiple (1-5)

### Pregunta 1: Métricas de Prometheus

¿Cuál **no es un nombre o familia estándar de métricas de servicio de Istio**?

A. istio\_requests\_total (recuento total de solicitudes)\
B. istio\_request\_duration\_milliseconds (latencia de solicitudes)\
C. istio\_request\_bytes (tamaño de solicitud)\
D. istio\_pod\_cpu\_usage (uso de CPU del Pod)

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D**

Las métricas de servicio estándar de Istio describen el tráfico; Envoy también expone estadísticas internas del proxy. Prometheus obtiene el uso de CPU de contenedores desde kubelet/cAdvisor (o la canalización de recursos del tiempo de ejecución). Metrics Server proporciona métricas de recursos para el autoescalado y `kubectl top`; kube-state-metrics expone el estado de los objetos y los valores configurados de requests y límites, no el consumo de CPU medido.

**Explicación:**

**Métricas recopiladas por Istio:**

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

* Esta no es una métrica de Istio
* Métrica de Kubernetes: `container_cpu_usage_seconds_total`
* Recopila métricas de kubelet/cAdvisor; kube-state-metrics resulta útil para comparar el uso con los límites configurados

**Categorías de métricas de Istio:**

| Categoría     | Métrica de ejemplo                             | Descripción                   |
| ------------ | --------------------------------------------- | ----------------------------- |
| **Solicitud**  | istio\_requests\_total                        | Recuento de solicitudes, códigos de respuesta |
| **Duración** | istio\_request\_duration\_milliseconds        | Distribución de latencia          |
| **Tamaño**     | istio\_request\_bytes, istio\_response\_bytes | Tamaño del tráfico                  |
| **TCP**      | istio\_tcp\_connections\_opened\_total        | Conexiones TCP               |

**Ejemplos de las señales doradas (Golden Signals):**

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

**Comprobación de métricas:**

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

Con un proveedor y un backend de trazas operativos, ¿qué responsabilidad debe asumir la aplicación para correlacionar los spans del proxy entre llamadas a servicios?

A. La aplicación debe generar identificadores de traza\
B. La aplicación debe propagar los encabezados HTTP\
C. El cliente Jaeger debe instalarse en todos los servicios\
D. Envoy gestiona todo automáticamente

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B**

Los proxies configurados pueden generar spans e identificadores de traza, pero la aplicación debe propagar el contexto de traza en sus llamadas salientes. Un SDK debe inyectar el contexto activo; así, los identificadores de los spans secundarios pueden cambiar mientras se conserva el identificador de traza. Las aplicaciones que no tienen instrumentación propia pueden reenviar los encabezados de propagación seleccionados.

**Explicación:**

**Cómo funciona el trazado distribuido:**

![Diagrama que muestra al Ingress Gateway creando encabezados de traza en una solicitud entrante, a cada servicio descendente (A, B, C) propagando el contexto de trazado al siguiente salto y a cada salto enviando también su span a Jaeger.](../../../.gitbook/assets/en-quizzes-service-mesh-istio-observability-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-quizzes-service-mesh-istio-observability-0.html)

El diagrama ilustra la propagación B3 hacia un backend Jaeger configurado. También se admiten la propagación W3C y un OpenTelemetry Collector intermedio; las aplicaciones instrumentadas inyectan su contexto de span activo en vez de copiar todos los encabezados sin cambios.

**Encabezados HTTP que se deben propagar:**

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

**Análisis de las opciones:**

* **A (X)**: Envoy genera automáticamente identificadores de traza
* **B (O)**: La aplicación debe propagar encabezados HTTP (obligatorio)
* **C (X)**: No se necesita cliente Jaeger, Envoy envía spans
* **D (X)**: Envoy crea y envía spans, pero la propagación de encabezados es responsabilidad de la aplicación

**Configuración de muestreo:**

Esto presupone el proveedor `otel-tracing` del capítulo de trazado. `1.0` significa 1 %, no 100 %; la configuración del proveedor/exportador y la propagación de contexto son requisitos independientes.

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

### Pregunta 3: Visualización con Kiali

¿Qué función **NO** ofrece Kiali?

A. Visualización de topología de servicios\
B. Análisis de flujo de tráfico\
C. Ejecución automática de despliegue Canary\
D. Validación de configuración de Istio

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C**

Kiali es una **herramienta de observación y análisis**; la ejecución de despliegues progresivos corresponde a herramientas como **Argo Rollouts**.

**Explicación:**

**Funciones principales de Kiali:**

**1. Visualización de topología de servicios (A - O)**

```bash
# Open Kiali dashboard
istioctl dashboard kiali

# Features:
# - Real-time service connection display
# - Traffic flow direction display
# - Service status (healthy/error)
# - Response time display
```

**Ejemplo de vista Graph:**

```
Frontend → Backend → Database
   ↓
External API

Color codes:
- Green: Normal
- Red: Error
- Gray: No traffic
```

**2. Análisis de flujo de tráfico (B - O)**

Kiali muestra:

* Recuento de solicitudes (RPS)
* Tasa de errores (%)
* Latencia P50/P95/P99
* Recuento de conexiones TCP

**3. Ejecución automática de despliegue Canary (C - X)**

* Kiali puede mostrar tráfico y, con permiso, editar la configuración de Istio/usar asistentes de tráfico
* No sustituye a un controlador automatizado de entrega progresiva
* Ejecución de despliegue: Argo Rollouts, Flagger

**4. Validación de configuración de Istio (D - O)**

Ejemplos del [catálogo de validación de Kiali](https://kiali.io/docs/features/validations/):

- VirtualService: subset no definido (`KIA1107`).
- DestinationRule: definiciones host/subset superpuestas (`KIA0201`).
- AuthorizationPolicy: no se encuentra el espacio de nombres referenciado (`KIA0101`), o el principal no está asociado a una cuenta de servicio de una carga de trabajo detectada (`KIA0106`).

Las comprobaciones dependen de la versión de Kiali, el alcance del descubrimiento y los permisos de acceso. Revisa el código y el mensaje concretos, así como la política efectiva del proxy. Kiali no demuestra por sí solo que dos políticas cualesquiera entren en conflicto ni que funcionen todos los certificados y las rutas en tiempo de ejecución.

**Instalación de Kiali:**

Consulta el [capítulo de paneles](../../../service-mesh/istio/observability/04-dashboards.md) para conocer la versión de operador, los requisitos de autenticación y los límites de compatibilidad actuales. Kiali se instala por separado; los complementos de ejemplo son demostraciones, y una instalación de Helm sin configuración de backend y RBAC no constituye una configuración de producción.

**Menús principales de Kiali:**

```
1. Overview: Service summary by Namespace
2. Graph: Service topology
3. Applications: Application list
4. Workloads: Deployment, StatefulSet, etc.
5. Services: Kubernetes Service
6. Istio Config: VirtualService, DestinationRule, etc.
```

**Kiali frente a otras herramientas:**

| Herramienta | Función | Entrega progresiva automatizada |
| ----------------- | ----------------------------------- | -------------------- |
| **Kiali**         | Visualización, análisis, validación | No                   |
| **Argo Rollouts** | Entrega progresiva                | Sí                  |
| **Flagger**       | Despliegue Canary automático         | Sí                  |
| **Grafana**       | Paneles de métricas                    | No                   |
| **Jaeger**        | Trazado distribuido                 | No                   |

**Ejemplo de uso práctico:**

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
* [Documentación oficial de Kiali](https://kiali.io/docs/)

</details>

***

### Pregunta 4: Configuración del registro de acceso

¿Cómo se configura en Istio la salida del registro de acceso en formato **JSON**?

A. Establecer meshConfig.accessLogEncoding en JSON en IstioOperator\
B. Modificar directamente Envoy ConfigMap\
C. Añadir una anotación a cada Pod\
D. Convertir a JSON mediante una consulta de Prometheus

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A**

La opción A es un método válido de MeshConfig: configura `accessLogEncoding: JSON` y habilita el registro en el archivo de entrada de `istioctl install -f`. No se trata de un recurso del operador instalado dentro del clúster. El capítulo de registro describe otro método admitido: un proveedor personalizado `envoyFileAccessLog.logFormat.labels`.

**Explicación:**

**Configuración del registro de acceso en formato JSON:**

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

**Configuración por espacio de nombres:**

Para esta alternativa, define primero `mesh-json` como se explica en el capítulo de registro. Telemetry selecciona el proveedor y el ámbito; por sí mismo no cambia el formato del proveedor.

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

**Variables de formato de Envoy:**

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

**Integración con CloudWatch Logs:**

Este es únicamente un fragmento de salida para un agente Fluent Bit ya desplegado, con etiquetas de entrada coincidentes, análisis de CRI/JSON, credenciales de IAM y volúmenes de registros montados. Un ConfigMap por sí solo no recopila registros. EKS Fargate requiere la configuración de enrutador de registros admitida.

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

**Comprobación de registros:**

```bash
# Check Pod's Access Log
kubectl logs <pod-name> -c istio-proxy

# Real-time monitoring
kubectl logs -f <pod-name> -c istio-proxy | jq -R 'fromjson?'

# Filter specific response codes
kubectl logs <pod-name> -c istio-proxy | \
  jq -R 'fromjson? | select((.response_code | tonumber?) == 500)'
```

**Formato TEXT frente a formato JSON:**

| Elemento            | TEXT         | JSON            |
| --------------- | ------------ | --------------- |
| **Legibilidad** | Alta (humana) | Baja (humana)     |
| **Procesamiento** | Difícil    | Fácil (por máquina)  |
| **Tamaño**        | Pequeño        | Grande           |
| **Estructura**   | No estructurada | Estructurada      |
| **Consulta**    | Difícil    | Fácil (jq, etc.) |

**Ejemplo de formato TEXT:**

```
[2025-01-20T10:30:00.123Z] "GET /api/users HTTP/1.1" 200 - "-" "-" 0 1234 42 40 "192.168.1.100" "Mozilla/5.0" "abc-123-def" "example.com" "10.0.1.20:8080" outbound|8080||backend.default.svc.cluster.local 10.0.1.10:54321 10.0.1.10:8080 10.0.1.5:12345 - default
```

**Referencia:**

* [Registro](../../../service-mesh/istio/observability/03-logging.md)
* [Formato del registro de acceso de Envoy](https://www.envoyproxy.io/docs/envoy/latest/configuration/observability/access_log/usage)

</details>

***

### Pregunta 5: Paneles de Grafana

¿Qué panel **no** forma parte del conjunto de paneles de Grafana publicado por Istio?

A. Istio Service Dashboard\
B. Istio Workload Dashboard\
C. Istio Performance Dashboard\
D. Istio Cost Dashboard

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D**

La opción D es correcta. Istio publica paneles de tráfico y del plano de control, pero Grafana es un complemento independiente; instalar Istio no instala automáticamente estos paneles.

**Explicación:**

El catálogo de Istio 1.31 incluye Service7636, Workload7630, Mesh7639, Performance11829, Control Plane7645, Wasm13277 y Ztunnel21306. Performance se centra en el uso de recursos y datos; los paneles xDS y webhook pertenecen principalmente a Control Plane. Mesh incluye el tráfico global y las versiones de los componentes, no todos los paneles de latencia que se mencionaban antes. Elige la revisión correspondiente a la versión de Istio instalada.

El costo no se puede calcular multiplicando `istio_requests_total` por un precio por GB transferido: las solicitudes no son bytes, y `source_cluster`/`destination_cluster` identifican clústeres, no zonas de disponibilidad. La memoria del proxy es uso, no una factura. El cálculo de costos de red necesita mediciones de bytes facturables y reglas de ubicación/servicio de origen/destino reales; la asignación de costos de recursos necesita precios de nodos, tiempo y un modelo de asignación explícito. Concilia las estimaciones con los datos de facturación/CUR de AWS y los precios aplicables en vez de afirmar una fórmula fija.

Consulta el [capítulo de paneles](../../../service-mesh/istio/observability/04-dashboards.md) para revisiones verificadas del catálogo y ejemplos completos de JSON y aprovisionamiento personalizado. Los ConfigMaps y las etiquetas por sí solos no instalan un cargador de paneles ni configuran las fuentes de datos.

</details>

***

## Preguntas de respuesta corta (6-10)

### Pregunta 6: Supervisión de las señales doradas

Explica cómo supervisar con Istio y Prometheus las **señales doradas** de Google SRE: latencia, tráfico, errores y saturación. Incluye **consultas de Prometheus** y **reglas de alerta** para cada señal.

<details>

<summary>Mostrar respuesta</summary>

Usa un solo reporter para cada cálculo entre servicios y conserva el espacio de nombres del servicio (y el clúster cuando corresponda). Las métricas del lado de destino miden las solicitudes que recibe el servicio; las del lado de origen hacen falta para contabilizar fallos aguas arriba que nunca llegan al destino. HTTP 5xx es solo una definición de error; los fallos de gRPC requieren `grpc_response_status` y reglas SLI específicas de la aplicación. Las latencias siguientes están en milisegundos y las tasas, en solicitudes por segundo:

```promql
histogram_quantile(0.95, sum by (destination_service_name, destination_service_namespace, le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination"}[5m])))

histogram_quantile(0.99, sum by (destination_service_name, destination_service_namespace, le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination"}[5m])))

sum by (destination_service_name, destination_service_namespace) (rate(istio_requests_total{reporter="destination"}[5m]))

sum by (destination_service_name, destination_service_namespace) (rate(istio_requests_total{reporter="destination",response_code=~"5.."}[5m])) / sum by (destination_service_name, destination_service_namespace) (rate(istio_requests_total{reporter="destination"}[5m]))
```

En un despliegue clásico con sidecars en un solo clúster, para calcular las proporciones de uso respecto del límite hacen falta kubelet/cAdvisor y kube-state-metrics. Excluye los límites ausentes o iguales a cero. Los sidecars nativos pueden exponer los límites declarados en las series de recursos de init containers; confirma cuál es la familia de métricas real antes de usar estas expresiones:

```promql
sum by (namespace, pod, container) (rate(container_cpu_usage_seconds_total{container="istio-proxy"}[5m])) / on (namespace, pod, container) (max by (namespace, pod, container) (kube_pod_container_resource_limits{container="istio-proxy",resource="cpu",unit="core"}) > 0)

max by (namespace, pod, container) (container_memory_working_set_bytes{container="istio-proxy"}) / on (namespace, pod, container) (max by (namespace, pod, container) (kube_pod_container_resource_limits{container="istio-proxy",resource="memory",unit="byte"}) > 0)

envoy_cluster_upstream_cx_active
envoy_cluster_upstream_rq_pending_active
envoy_cluster_circuit_breakers_default_cx_open
```

La métrica `_cx_open` es un gauge de estado de 0/1; dividir las conexiones activas por ese valor no mide la utilización. Si necesitas proporciones de capacidad, revisa los umbrales configurados del disyuntor (circuit breaker). La tasa de CPU se expresa en núcleos antes de dividirla; el conjunto de trabajo de memoria, en bytes. Para desglosar por método, primero añade mediante Telemetry una etiqueta `request_method` con cardinalidad acotada.

El Prometheus Operator instalado debe seleccionar el siguiente recurso PrometheusRule. Los umbrales y las ventanas de comparación son ilustrativos. La estacionalidad del tráfico, la falta de datos, los fallos de recopilación y el volumen mínimo requieren un tratamiento específico del entorno. Comparar con la hora anterior no equivale a una línea base normal aprendida.

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

Crea paneles separados para la tasa de solicitudes, la proporción de errores, la latencia y las unidades de recursos con la [plantilla de panel verificada](../../../service-mesh/istio/observability/04-dashboards.md). No representes los núcleos de CPU y los bytes de memoria en una misma escala sin etiquetarla.

</details>

***

### Pregunta 7: Detección de cuellos de botella de rendimiento con Jaeger

Explica cómo usar Jaeger, la herramienta de trazado distribuido, para encontrar **cuellos de botella de rendimiento** en una arquitectura de microservicios. Incluye **métodos de análisis de trazas** y **escenarios prácticos de depuración**.

<details>

<summary>Mostrar respuesta</summary>

Empieza por la [configuración de trazado Jaeger 2/OTLP](../../../service-mesh/istio/observability/02-tracing.md), un proveedor Telemetry configurado y la propagación de contexto de la aplicación. No des por hecho que un complemento antiguo de Jaeger, un puerto de Zipkin o un valor de muestreo, por sí solos, habilitan el trazado. Los spans de aplicación/base de datos requieren instrumentación de SDK o agente; los spans de proxy no pueden revelar los detalles internos de una consulta de base de datos.

1. Localiza el servicio y el intervalo afectados mediante una consulta de latencia de Prometheus limitada al espacio de nombres y, después, busca en Jaeger trazas representativas lentas y normales. Una consulta de histograma de Prometheus devuelve estadísticas agregadas, no identificadores de traza.
2. Sigue la ruta crítica y distingue la duración padre del tiempo exclusivo. Un padre largo incluye sus hijos; no es automáticamente la causa.
3. Compara los errores, los reintentos, las esperas de conexión, la ejecución de consultas y el paralelismo. La temporización de las trazas, el muestreo y los spans ausentes limitan las conclusiones.

```promql
histogram_quantile(0.99, sum by (destination_service_name, destination_service_namespace, le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination"}[5m]))) > 2000
```

```bash
kubectl port-forward -n observability svc/jaeger-query 16686:16686
```

Estos escenarios son hipotéticos: no son resultados de pruebas de rendimiento ni respuestas literales de la API de Jaeger:

| Observación | Qué verificar | Respuesta adecuada |
|---|---|---|
|Solicitud de 2.1 s con una operación de base de datos instrumentada de 1.8 s|Separa la espera en el pool, el tiempo de consulta, los bloqueos y la demora de red; verifica el plan de ejecución de la base de datos|Corrige la causa medida. Un ConfigMap llamado `redis.conf` no añade caché a la aplicación|
|Solicitud de unos 10 s con timeout del pool de conexiones|Inspecciona el pool del cliente de base de datos de la aplicación, la concurrencia y la capacidad de la base de datos|Ajusta el pool de conexiones de la aplicación o de la base de datos y corrige las fugas. Un Envoy DestinationRule no configura el pool de conexiones de la aplicación, y los ajustes del pool HTTP no configuran PostgreSQL|
|Llamadas independientes de 2 s + 2 s + 1 s ejecutadas en serie|Confirma las dependencias, los límites de carga y el contexto de trazado|Paraleliza solo las operaciones de E/S independientes, con clientes realmente asíncronos o hilos acotados. El tiempo puede acercarse al de la llamada más larga más el procesamiento adicional; no se garantizan 2 s|

Para los callbacks de E/S síncrona existentes, este fragmento de Python 3.9 o posterior conserva el orden de los resultados y utiliza hilos de trabajo. La aplicación debe proporcionar los callbacks y aplicar sus propios límites de tiempo; cancelar la tarea que espera no detiene un hilo que ya está ejecutándose:

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

Los límites de tiempo acotan la espera, pero no arreglan una base de datos lenta; los reintentos pueden amplificar la carga. Si muestras un timeout de VirtualService, incluye el destino real de la ruta y configura reintentos solo después de considerar la idempotencia y la carga. Los mapas persistentes de dependencias de Jaeger pueden requerir agregación adicional; la cascada de una traza y el mapa global de dependencias son vistas distintas. Comprueba una posible corrección con tráfico repetido y métricas y trazas, no con una sola traza llamativa.

</details>

***

### Pregunta 8: Solución de problemas de Service Mesh con Kiali

Explica cómo diagnosticar y resolver **problemas comunes** (errores de configuración, anomalías de tráfico, conflictos de políticas de seguridad) en el service mesh de Istio usando Kiali.

<details>

<summary>Mostrar respuesta</summary>

Utiliza las comprobaciones de configuración de Kiali, el tráfico observado, los logs de Pod y las trazas como evidencia y, después, verifica la configuración efectiva del proxy. El capítulo de paneles documenta los requisitos de versión y autenticación. No atribuyas una advertencia a Kiali por la forma del gráfico ni interpretes un icono verde como garantía de funcionamiento.

| Síntoma | Interpretación y comprobaciones correctas |
|---|---|
|Falta un servicio o subconjunto|En `default`, `reviews` y `reviews.default.svc.cluster.local` se resuelven al mismo host. Usar un nombre más corto no crea un Service que no existe. KIA1107 identifica un subset no definido; comprueba Service/EndpointSlice, DestinationRule y las etiquetas reales del Pod|
|La etiqueta del subconjunto no coincide|El valor de la etiqueta `1.0` no es incorrecto por sí mismo; haz que las etiquetas de Deployment coincidan con las del subconjunto previsto. Al escribir DestinationRules completos, incluye metadata, host y separadores de documentos|
|Se observa una distribución 90/10 en vez de la configuración 50/50|Comprueba los pesos efectivos, las reglas coincidentes, la afinidad de conexión, los reintentos, el estado de los endpoints y su expulsión (ejection), y el intervalo observado. Que haya menos réplicas listas no modifica por sí solo los pesos de los subconjuntos de VirtualService ni garantiza después una distribución 50/50|
|Ciclo A↔B|Un gráfico bidireccional no demuestra que haya llamadas recursivas, un interbloqueo (deadlock) ni una alerta automática de Kiali. Usa una traza para confirmar un ciclo no deseado antes de rediseñar la aplicación|
|Respuesta HTTP 403|Inspecciona la política, la identidad y los detalles de la respuesta en el proxy que la aplica. Una AuthorizationPolicy con spec vacío es una política ALLOW sin reglas coincidentes; otra política ALLOW puede permitir una excepción. No es una política DENY que anule las demás|
|Fallo de mTLS|PeerAuthentication describe la política del receptor. Comprueba la configuración TLS del emisor, la política del receptor, la identidad inscrita, el certificado y la cadena de confianza, y el protocolo del puerto para la dirección concreta. Que los receptores usen modos distintos no constituye automáticamente un conflicto; aplicar STRICT en todas partes es una decisión de migración, no una solución genérica|

Una política de denegación predeterminada limitada, con una excepción para el frontend, es válida si mTLS proporciona el principal frontend indicado y ninguna política CUSTOM o DENY previa rechaza la solicitud:

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

La animación del tráfico resume el intervalo seleccionado; no inspecciona paquetes ni mide bytes exactos. Si la hipótesis no se confirma, repite el ciclo de diagnóstico, configuración y prueba en lugar de reiniciar cargas a ciegas.

![Bucle de solución de problemas de Kiali que abre la vista Graph, clasifica el síntoma en sin tráfico, errores, respuesta lenta o seguridad denegada, comprueba la configuración de Istio, logs, trazas o política de seguridad, y después corrige y prueba la configuración, repitiendo el diagnóstico si no se resuelve.](../../../.gitbook/assets/en-quizzes-service-mesh-istio-observability-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-quizzes-service-mesh-istio-observability-1.html)

</details>

***

### Pregunta 9: Configuración de una pila de observabilidad de producción

Explica cómo desplegar en producción una pila de observabilidad de Istio (Prometheus, Grafana, Jaeger y Kiali) con **alta disponibilidad (HA)**. Incluye estrategias de **almacenamiento persistente**, **escalado** y **copias de seguridad**.

<details>

<summary>Mostrar respuesta</summary>

Una pila de producción con alta disponibilidad (HA) debe diseñarse y verificarse para cada entorno. Lo siguiente cubre los requisitos principales, pero no es un paquete de despliegue probado en producción. Fija versiones compatibles de Kubernetes, Istio, el operador, los charts y el backend; revisa los valores de chart que se usan realmente y valida el comportamiento ante fallos y durante la restauración antes del despliegue. El [capítulo de paneles](../../../service-mesh/istio/observability/04-dashboards.md) registra la brecha actual de compatibilidad de Kiali; no supongas que hay compatibilidad solo porque una versión sea la más reciente.

| Componente | Requisitos de estado y HA |
|---|---|
|Prometheus|Ejecuta réplicas independientes con un PVC por réplica, etiquetas de clúster comunes a las réplicas de ese clúster y etiquetas de réplica distintas (las demás etiquetas deben coincidir para poder deduplicar). Distribuye las réplicas entre dominios de fallo y dimensiona la retención según la ingesta observada. Un balanceador de carga no fusiona los historiales|
|Thanos|Los sidecars exponen StoreAPI y pueden cargar bloques. Query descubre los endpoints StoreAPI reales y deduplica según la etiqueta de réplica configurada. Store Gateway lee del almacenamiento de objetos. Compactor gestiona la compactación y retención de bloques con una estrategia adecuada de escritor único y fragmentación (sharding)|
|Grafana|Dos réplicas requieren una base de datos PostgreSQL o MySQL compartida y de alta disponibilidad, una configuración coherente de aprovisionamiento, plugins y secretos, y un balanceador de carga. Dos réplicas que comparten SQLite o un volumen EBS ReadWriteOnce entre nodos no proporcionan alta disponibilidad de Grafana|
|Alertmanager|Las réplicas necesitan configuración de pares y deduplicación de notificaciones, estado persistente y credenciales protegidas para los receptores. Incluir un webhook de Slack en los valores del chart no basta para diseñar correctamente los secretos y las notificaciones|
|Jaeger2/collector|Usa réplicas sin estado de consulta y recopilación con un backend persistente admitido, y configura por separado su alta disponibilidad, TLS y credenciales. Los muestreadores de cola (tail samplers) necesitan afinidad por identificador de traza; varias réplicas detrás de un Service con balanceo aleatorio no reciben trazas completas|
|Kiali|Usa un operador y servidor compatibles, comparte la configuración y el secreto de sesión, y ubica los Pods adecuadamente. Protege las API del backend y limita los permisos del usuario por espacio de nombres. La estrategia de tokens es para un solo clúster; cuando se necesite, elige un método documentado de autenticación multiclúster|

**Almacenamiento y conexión con el almacén de objetos**:

- Mantén el almacenamiento persistente local de Prometheus aunque uses almacenamiento de objetos: es posible que los datos recientes de head/WAL aún no se hayan cargado. Para las cargas desde sidecars, sigue los requisitos de compactación local y duración de bloques de la versión instalada de Thanos.
- Deben existir el bucket de S3, el endpoint regional, el cifrado, la retención y los permisos de IAM. Asocia la cuenta de servicio que obtiene las credenciales con los Pods que ejecutan realmente sidecar, Store o Compactor. Un comentario YAML que diga “IRSA” no crea credenciales. La configuración actual de S3 de Thanos puede usar `aws_sdk_auth: true` con la cadena de credenciales admitida por AWS SDK.
- En los valores actuales de kube-prometheus-stack, se indica el Secret existente del almacén de objetos en `prometheus.prometheusSpec.thanos.objectStorageConfig.existingSecret` usando el nombre y la clave reales. Montar la clave `thanos.yaml` no crea un archivo llamado `objstore.yaml`. Verifica las rutas de los archivos, los puertos gRPC con nombre del Service y los destinos DNS-SRV.
- Thanos Query actual utiliza `--endpoint` y `--query.replica-label` para la configuración de endpoint/deduplicación. No reutilices un ejemplo antiguo con `--store` sin comprobar la versión elegida. Kiali que consulta un backend compatible con Prometheus también puede necesitar los ajustes `thanos_proxy` documentados.
- Cada Deployment o StatefulSet necesita selectores y etiquetas de Pod coherentes, además de Services coincidentes; los recursos originales incompletos no podían formar una topología StoreAPI funcional. En EKS, el almacenamiento con EBS requiere una ubicación compatible en EC2 y la configuración CSI correspondiente. Fargate no monta EBS ni permite ejecutar DaemonSets arbitrarios.

**Configuración, copias de seguridad y verificación**:

1. Configura los selectores reales de monitores y reglas, así como los objetivos de recopilación. En kube-prometheus-stack, `alertmanager.config` está al mismo nivel que `alertmanager.alertmanagerSpec`; comprueba el esquema del chart fijado. Guarda las contraseñas y los webhooks en referencias a Secrets admitidas.
2. Respalda la base de datos, la configuración, los paneles aprovisionados y los plugins de Grafana; el estado de Prometheus que corresponda; y el almacenamiento de Jaeger, mediante procedimientos coherentes con cada aplicación. La retención del almacén de objetos, por sí sola, no permite restaurar todos los componentes.
3. Los manifiestos PVC/PV de Velero no demuestran por sí solos que se hayan copiado los datos de los volúmenes. Configura la ruta admitida para snapshots o el traslado de datos CSI, o la copia del sistema de archivos; las clases y los complementos de snapshots; las credenciales; y los recursos necesarios para restaurar las cargas. Revisa el estado de las copias y prueba restauraciones aisladas.
4. Un Job de copia de seguridad debe usar una imagen probada que incluya las herramientas necesarias, una URL de origen correcta, una identidad con permisos limitados, un bucket de destino y manejo de fallos. La imagen antigua de AWS CLI y el CronJob supuesto con curl, jq y S3 no constituían una solución de copia de seguridad verificada.
5. Supervisa fallos de receptores y exportadores, colas, estado de recopilación y métricas reales de capacidad de los PVC. `prometheus_tsdb_storage_blocks_bytes_total` no es un denominador de capacidad válido. Una pila no puede informar de forma fiable de su propia caída total; usa una señal de actividad o un observador independiente, y distingue las series ausentes o sin datos de `up == 0`.
6. Prueba la pérdida de una réplica, un nodo o una zona; la interrupción del almacenamiento; los fallos del backend o la autenticación; las actualizaciones y la restauración. Los PDB ayudan a gestionar interrupciones planificadas, pero no proporcionan alta disponibilidad de la base de datos ni de la zona. Registra el RPO, el RTO y la capacidad observada; no los deduzcas del número de réplicas.

Consulta [la guía de alta disponibilidad de Grafana](https://grafana.com/docs/grafana/latest/setup-grafana/set-up-for-high-availability/), [Thanos Sidecar](https://thanos.io/tip/components/sidecar.md/), [Thanos Query](https://thanos.io/tip/components/query.md/), [Thanos storage](https://thanos.io/tip/thanos/storage.md/) y [Velero CSI backup](https://velero.io/docs/main/csi/).

</details>

***

### Pregunta 10: Métricas personalizadas y creación de paneles

Explica cómo recopilar **métricas de negocio** (por ejemplo, el número de pedidos y la tasa de pagos exitosos) además de las métricas predeterminadas de Istio Envoy, y cómo crear un panel personalizado de Grafana.

<details>

<summary>Mostrar respuesta</summary>

Define el evento de negocio y qué se va a contar antes de elegir las métricas. Envoy conoce las solicitudes, pero no sabe si un pedido se guardó de forma duradera o si un pago se liquidó. Los siguientes **fragmentos de integración cuentan intentos de procesamiento completados**, no pedidos únicos ni ingresos contables. La aplicación debe proporcionar sus funciones de procesamiento y definir el contrato de errores; también debe gestionar la idempotencia y la validación. Para medir realmente los pagos exitosos, instrumenta sus resultados en el punto en que se procesa el pago y calcula la proporción a partir de contadores de resultados; un Gauge que no se actualiza de forma fiable no mide una tasa de éxito.

Usa etiquetas acotadas de categoría y estado, un Counter para los intentos e Histograms para importes y duraciones no negativos. Registra la duración en `finally` para incluir también los fallos. No uses como etiquetas los identificadores de pedido o usuario ni las URL sin procesar. Estos ejemplos usan un solo proceso; para agregar varios workers hace falta la configuración admitida por la biblioteca cliente.

**Python/Flask** (la aplicación proporciona `process_order` y `PaymentException`):

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

**Node.js/Express**: el paquete mantenido es `@prometheus-io/client` (API de ejemplo comprobada con 0.16.1 en Node 22). `prom-client` está obsoleto en favor de este paquete; los proyectos existentes deben revisar el changelog de migración. Configura el middleware JSON y espera `register.metrics()`:

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

**Recopilación en Kubernetes**: este laboratorio con sidecar usa el endpoint combinado de Istio y no presupone que la recopilación en texto plano desde la aplicación pueda atravesar mTLS en modo STRICT. Integra estas etiquetas y anotaciones en el Deployment `order-service` real de `default`; la imagen debe incluir la aplicación y exponer `/metrics` en el puerto 8080. La malla debe tener habilitada la combinación de métricas de Prometheus. El endpoint del agente en el puerto 15020 transmite datos sin cifrar, así que restringe el acceso de red. Si un recolector existente ya obtiene estas métricas de negocio, no añadas otro monitor.

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

El recurso Prometheus debe seleccionar el ServiceMonitor de `istio-system`, que descubre el Service de `default`. Conservar solo las familias de métricas de negocio evita duplicar las métricas de proxy que ya se recopilan en otro lugar. `targetLabels` añade explícitamente la etiqueta `app` del Service. Este ejemplo usa sidecars; la recopilación directa con ambient o TLS requiere un diseño compatible propio.

**Consultas** (en orden: recuento de intentos del intervalo, intentos/segundo, fracción de éxito, P95 de importe observado, P99 de duración, tasa por categoría, fracción de fallos de pago entre intentos de pedido):

```promql
sum(increase(orders_total{namespace="default",app="order-service"}[5m]))

sum(rate(orders_total{namespace="default",app="order-service"}[5m]))

sum(rate(orders_total{namespace="default",app="order-service",status="success"}[5m])) / sum(rate(orders_total{namespace="default",app="order-service"}[5m]))

histogram_quantile(0.95, sum by (le) (rate(order_amount_dollars_bucket{namespace="default",app="order-service"}[5m])))

histogram_quantile(0.99, sum by (le) (rate(order_processing_duration_seconds_bucket{namespace="default",app="order-service"}[5m])))

sum by (product_category) (rate(orders_total{namespace="default",app="order-service"}[5m]))

sum(rate(orders_total{namespace="default",app="order-service",status="payment_failed"}[5m])) / sum(rate(orders_total{namespace="default",app="order-service"}[5m]))
```

`increase` estima el total del intervalo; `rate` calcula una tasa por segundo. Los reinicios de procesos, los reintentos y las recopilaciones perdidas hacen que los contadores y las sumas de importes operativos no sean un libro contable. Para conocer los pedidos únicos confirmados o los ingresos, concilia con el sistema de negocio duradero; no supongas que la telemetría garantiza exactamente una vez.

**Grafana**: este objeto de panel completo espera el UID `prometheus` de la fuente de datos y las etiquetas del monitor anterior. Guárdalo sin una envoltura de API y sigue el [aprovisionamiento documentado de paneles desde archivos](../../../service-mesh/istio/observability/04-dashboards.md). Una etiqueta en el ConfigMap no configura por sí sola un proveedor.

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

**Alertas**: el Prometheus Operator instalado debe seleccionar esta regla. El volumen mínimo de tráfico evita alertas basadas en proporciones cuando no hay tráfico; la ausencia de datos o los fallos de recopilación requieren una señal aparte. Los umbrales son ejemplos, no garantías de SLO de negocio.

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

Consulta la documentación del [cliente de Python](https://prometheus.github.io/client_python/) y del [cliente JavaScript](https://github.com/prometheus/client_js) para tipos de métrica, exposición y modelos de proceso.

</details>

***

## Cálculo de la puntuación

* Opción múltiple 1-5: 10 puntos cada una (Total 50 puntos)
* Respuesta corta 6-10: 10 puntos cada una (Total 50 puntos)
* **Total: 100 puntos**

**Criterios de evaluación:**

* 90–100 puntos: Excelente comprensión de estos temas
* 80–89 puntos: Buena comprensión; la validación del despliegue debe hacerse por separado
* 70–79 puntos: Nivel medio (se recomienda seguir estudiando)
* 60–69 puntos: Por debajo del nivel esperado (conviene repasar los conceptos básicos)
* 0–59 puntos: Es necesario volver a estudiar

## Recursos de aprendizaje

* [Métricas](../../../service-mesh/istio/observability/01-metrics.md)
* [Trazado distribuido](../../../service-mesh/istio/observability/02-tracing.md)
* [Logging](../../../service-mesh/istio/observability/03-logging.md)
* [Visualización](../../../service-mesh/istio/observability/04-dashboards.md)
