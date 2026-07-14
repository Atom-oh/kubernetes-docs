# Cuestionario de observabilidad de Linkerd

Este cuestionario evalúa tu comprensión de las características de observabilidad de Linkerd.

## Preguntas del cuestionario

### 1. ¿Cuál NO es una métrica dorada recopilada automáticamente por Linkerd?

A. Tasa de éxito
B. Tasa de solicitudes (RPS)
C. Latencia
D. Uso de CPU

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Uso de CPU**

**Explicación:**
Linkerd recopila automáticamente tres métricas doradas: tasa de éxito, tasa de solicitudes (RPS) y latencia (p50, p95, p99). El uso de CPU es una métrica de Kubernetes que debe recopilarse por separado.

</details>

### 2. ¿Qué NO se incluye en la salida del comando `linkerd viz stat`?

A. SUCCESS (tasa de éxito)
B. RPS (tasa de solicitudes)
C. LATENCY_P99
D. ERROR_TYPE

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. ERROR_TYPE**

**Explicación:**
`linkerd viz stat` muestra MESHED, SUCCESS, RPS, LATENCY_P50/P95/P99. Los tipos de errores deben comprobarse mediante `linkerd viz tap` o los logs.

</details>

### 3. ¿Cuál es el propósito del comando `linkerd viz tap`?

A. Captura de paquetes de red
B. Ver el flujo de solicitudes en tiempo real
C. Cambiar la configuración del proxy
D. Renovar certificados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Ver el flujo de solicitudes en tiempo real**

**Explicación:**
`linkerd viz tap` transmite solicitudes en tiempo real. Muestra el método de solicitud, la ruta, el código de estado, la latencia, el estado de mTLS y más.

</details>

### 4. ¿Qué métricas adicionales se pueden obtener al definir un ServiceProfile?

A. Uso de recursos de Pod
B. Métricas por ruta
C. Ancho de banda de red
D. E/S de disco

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Métricas por ruta**

**Explicación:**
Definir un ServiceProfile permite recopilar métricas por ruta (p. ej., GET /api/users, POST /api/orders) de tasa de éxito, tasa de solicitudes y latencia. Visualízalas con el comando `linkerd viz routes`.

</details>

### 5. ¿Cuál es el método predeterminado para acceder al Prometheus de la extensión Viz?

A. Servicio NodePort
B. Servicio LoadBalancer
C. kubectl port-forward
D. URL pública

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. kubectl port-forward**

**Explicación:**
El Prometheus de Viz se implementa como un servicio ClusterIP. Accede mediante `kubectl port-forward -n linkerd-viz svc/prometheus 9090:9090`. No se recomienda la exposición externa por seguridad.

</details>

### 6. ¿Qué header NO es necesario para la propagación de tracing distribuido?

A. x-b3-traceid
B. x-request-id
C. x-linkerd-proxy
D. x-b3-spanid

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. x-linkerd-proxy**

**Explicación:**
Los headers necesarios para el tracing distribuido son: x-request-id, x-b3-traceid, x-b3-spanid, x-b3-parentspanid, x-b3-sampled, b3, etc. x-linkerd-proxy no existe.

</details>

### 7. ¿Qué muestra el comando `linkerd viz top`?

A. Pods que utilizan más recursos
B. Rutas de solicitud más activas
C. Mensajes de error principales
D. Entradas de log más recientes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Rutas de solicitud más activas**

**Explicación:**
`linkerd viz top` muestra las rutas de solicitud más activas en tiempo real. Muestra Source, Destination, Method, Path, Count, Latency, Success Rate, etc.

</details>

### 8. ¿Qué annotation establece el nivel de log del proxy?

A. config.linkerd.io/log-level
B. config.linkerd.io/proxy-log-level
C. linkerd.io/proxy-log
D. proxy.linkerd.io/log-level

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. config.linkerd.io/proxy-log-level**

**Explicación:**
La annotation `config.linkerd.io/proxy-log-level` establece el nivel de log del proxy. Ejemplo: "warn,linkerd=info,linkerd_proxy=debug"

</details>

### 9. ¿Cuál es la consulta correcta de Prometheus para calcular la tasa de éxito de Linkerd?

A. `sum(response_total{classification="success"}) / sum(response_total)`
B. `rate(success_total[5m]) / rate(request_total[5m])`
C. `sum(rate(response_total{classification="success"}[5m])) / sum(rate(response_total[5m]))`
D. `avg(success_rate)`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. `sum(rate(response_total{classification="success"}[5m])) / sum(rate(response_total[5m]))`**

**Explicación:**
La tasa de éxito se calcula dividiendo la tasa de respuestas exitosas por la tasa total de respuestas. La función rate() calcula la tasa por segundo dentro del intervalo de tiempo, y sum() agrega los resultados.

</details>

### 10. ¿Cuál es la función principal de la extensión Jaeger?

A. Recopilación de métricas
B. Agregación de logs
C. Tracing distribuido
D. División de tráfico

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Tracing distribuido**

**Explicación:**
La extensión Jaeger proporciona tracing distribuido. Visualiza la ruta completa de las solicitudes a través de varios servicios y analiza la latencia en cada paso.

</details>

### 11. ¿Qué vista NO proporciona el comando linkerd viz dashboard?

A. Topology
B. Deployments
C. Pod Logs
D. Routes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Pod Logs**

**Explicación:**
El dashboard de Viz proporciona las vistas Namespace, Deployments, Pods, TCP, Routes, Topology y Tap. Los logs de Pod deben comprobarse mediante kubectl logs o un sistema de logging independiente.

</details>

### 12. ¿Qué opción de instalación de Viz se utiliza al integrarlo con Grafana externo?

A. `--set grafana.external=true`
B. `--set grafana.enabled=false`
C. `--set grafana.url=external`
D. `--set monitoring=external`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `--set grafana.enabled=false`**

**Explicación:**
Al usar Grafana externo, desactiva el Grafana integrado de Viz. Usa `helm install linkerd-viz linkerd/linkerd-viz --set grafana.enabled=false` o configúralo en el archivo de values.

</details>
