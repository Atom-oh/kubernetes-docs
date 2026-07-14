# Cuestionario de gestión de tráfico de Linkerd

Este cuestionario evalúa tu comprensión de la gestión de tráfico de Linkerd.

## Preguntas del cuestionario

### 1. ¿Qué no se puede configurar por ruta en un ServiceProfile?

A. Tiempo de espera
B. Capacidad de reintento
C. Algoritmo de balanceador de carga
D. Condición de ruta

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Algoritmo de balanceador de carga**

**Explicación:**
ServiceProfile puede configurar el tiempo de espera, la capacidad de reintento (isRetryable) y las condiciones de ruta (method, pathRegex) por ruta. El algoritmo de balanceador de carga es una configuración global de Linkerd que utiliza EWMA.

</details>

### 2. ¿Qué algoritmo de balanceo de carga utiliza Linkerd?

A. Round Robin
B. Menor cantidad de conexiones
C. EWMA (Exponentially Weighted Moving Average)
D. Aleatorio

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. EWMA (Exponentially Weighted Moving Average)**

**Explicación:**
Linkerd utiliza el algoritmo EWMA para preferir endpoints con una latencia de respuesta más rápida. Se adapta al estado de los endpoints en tiempo real y reduce automáticamente el tráfico hacia los endpoints lentos.

</details>

### 3. ¿Qué especificación estándar sigue TrafficSplit?

A. CNCF
B. SMI (Service Mesh Interface)
C. OpenAPI
D. gRPC

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. SMI (Service Mesh Interface)**

**Explicación:**
TrafficSplit es un CRD que sigue el estándar SMI (Service Mesh Interface). SMI define interfaces comunes para que los service meshes proporcionen compatibilidad entre diferentes implementaciones de mesh.

</details>

### 4. ¿Qué significa un retryRatio de retryBudget de 0.2?

A. Solo se reintenta el 20 % de todas las solicitudes
B. Solo se reintenta el 20 % de las solicitudes fallidas
C. Se permiten hasta un 20 % de reintentos adicionales respecto a las solicitudes originales
D. El presupuesto de reintentos se restablece cada 20 segundos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Se permiten hasta un 20 % de reintentos adicionales respecto a las solicitudes originales**

**Explicación:**
Un retryRatio de 0.2 permite hasta un 20 % de reintentos adicionales respecto al número original de solicitudes. Ejemplo: se permiten hasta 20 reintentos adicionales para 100 solicitudes. Esto evita la sobrecarga causada por los reintentos.

</details>

### 5. ¿Cuál NO es un método para generar automáticamente un ServiceProfile?

A. Generar a partir de una especificación OpenAPI/Swagger
B. Generar a partir de tráfico en vivo con tap
C. Generar a partir de una definición Protobuf
D. Generar automáticamente a partir de un Kubernetes Service

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Generar automáticamente a partir de un Kubernetes Service**

**Explicación:**
Los ServiceProfiles se pueden generar con los comandos `linkerd profile --open-api`, `linkerd viz profile --tap` y `linkerd profile --proto`. No se generan automáticamente a partir de Kubernetes Services y se deben definir explícitamente.

</details>

### 6. ¿Cuál debe ser la suma de los pesos de backend de TrafficSplit para un canary deployment?

A. Debe ser exactamente 100
B. Debe ser exactamente 1
C. Cualquier valor funciona (se calcula como proporción)
D. Debe ser exactamente 1000

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Cualquier valor funciona (se calcula como proporción)**

**Explicación:**
Los pesos de TrafficSplit se calculan como proporciones relativas. weight: 90 y weight: 10 equivalen a weight: 9 y weight: 1. La suma no tiene que ser 100.

</details>

### 7. ¿Qué condición de enrutamiento NO es compatible con HTTPRoute (Gateway API)?

A. Enrutamiento basado en headers
B. Enrutamiento basado en rutas
C. Enrutamiento basado en cookies
D. Enrutamiento basado en IP de origen

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Enrutamiento basado en IP de origen**

**Explicación:**
HTTPRoute admite el enrutamiento basado en headers, rutas, métodos y cookies (mediante headers). El enrutamiento basado en IP de origen queda fuera del alcance del enrutamiento L7 y se gestiona mediante NetworkPolicy u otros mecanismos.

</details>

### 8. ¿Qué servidor de métricas se utiliza al integrar Flagger con Linkerd?

A. Metrics Server
B. Prometheus
C. InfluxDB
D. Datadog

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Prometheus**

**Explicación:**
Flagger obtiene métricas (tasa de éxito, latencia, etc.) del Prometheus de Linkerd Viz para el análisis canary. Al instalar Flagger, conéctalo con `--set metricsServer=http://prometheus.linkerd-viz:9090`.

</details>

### 9. ¿Qué sucede en una ruta donde isRetryable de ServiceProfile es false?

A. Todas las solicitudes fallan
B. No se producen reintentos
C. Los tiempos de espera se ignoran
D. La ruta se deshabilita

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. No se producen reintentos**

**Explicación:**
isRetryable: false significa que las solicitudes de esa ruta no se reintentarán aunque fallen. Esto es adecuado para operaciones no idempotentes como las solicitudes POST. La solicitud en sí se procesa normalmente.

</details>

### 10. ¿Cómo se implementa el patrón Circuit Breaker en Linkerd?

A. Circuit Breaker CRD
B. Failure Accrual
C. Rate Limiter
D. Política de tiempo de espera

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Failure Accrual**

**Explicación:**
Linkerd implementa el patrón circuit breaker mediante failure accrual. Ante fallos consecutivos, excluye temporalmente el endpoint, reintenta con backoff exponencial y vuelve al estado normal cuando tiene éxito.

</details>

### 11. ¿Cómo se envía tráfico a un servicio mirror sin división de tráfico?

A. Usar TrafficMirror CRD
B. Llamar directamente al DNS del servicio mirror
C. Todo el tráfico se replica automáticamente
D. Linkerd no admite la réplica de tráfico

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Llamar directamente al DNS del servicio mirror**

**Explicación:**
Linkerd no tiene por sí mismo funcionalidad de réplica de tráfico como Istio. Los servicios mirror multi-cluster (por ejemplo, web-west) se deben llamar directamente mediante DNS o configurar con pesos de TrafficSplit.

</details>

### 12. ¿Qué sucede en una ruta donde no se establece el tiempo de espera de ServiceProfile?

A. Se aplica un tiempo de espera predeterminado de 5 segundos
B. Sin tiempo de espera (ilimitado)
C. La solicitud falla inmediatamente
D. Se aplica el tiempo de espera global

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Sin tiempo de espera (ilimitado)**

**Explicación:**
Las rutas sin un tiempo de espera especificado en ServiceProfile esperan indefinidamente sin tiempo de espera. Esto es adecuado para operaciones de streaming o de larga duración, pero en general se recomienda establecer explícitamente los tiempos de espera.

</details>
