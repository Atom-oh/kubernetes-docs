# Circuit Breaker

Un circuit breaker aísla automáticamente los servicios que fallan para evitar que el fallo se propague en cascada.

## Tabla de contenido

1. [¿Por qué usar un circuit breaker?](#why-circuit-breaker)
2. [Descripción general](#circuit-breaker-overview)
3. [Configuración de los grupos de conexiones](#connection-pool-settings)
4. [Detección de instancias con fallos](#outlier-detection)
5. [Combinación con una política de reintentos](#combination-with-retry-policy)
6. [Ejemplos prácticos](#practical-examples)
7. [Circuit breakers para servicios externos](#external-service-circuit-breaker)
8. [Monitorización y depuración](#monitoring-and-debugging)
9. [Consideraciones importantes](#important-considerations)
10. [Buenas prácticas](#best-practices)

## ¿Por qué usar un circuit breaker? {#why-circuit-breaker}

### Prevención de fallos en cascada

En una arquitectura de microservicios, este mecanismo evita que el fallo de un servicio se propague a otros.

![Comparación de una cadena de microservicios sin circuit breaker, donde los tiempos de espera de Service A al llamar al Service B averiado agotan sus recursos y provocan fallos en Service C y D, y otra con circuit breaker, donde las llamadas a B fallan rápidamente mientras C y D siguen funcionando.](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-07-circuit-breaker-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-07-circuit-breaker-0.html)

### Beneficios principales

| Problema | Sin circuit breaker | Con circuit breaker |
|---------|------------------------|----------------------|
| **Tiempo de respuesta** | Espera hasta agotar el tiempo de espera (30 s o más) | Rechazo rápido al alcanzar los límites configurados |
| **Uso de recursos** | Agotamiento de hilos y conexiones | Protección de los recursos |
| **Propagación de fallos** | Fallos en cascada | Aislamiento de los fallos |
| **Tiempo de recuperación** | Requiere intervención manual | Intentos de recuperación automática |

## Descripción general del circuit breaker {#circuit-breaker-overview}

El diagrama muestra el patrón genérico de bibliotecas con estados Closed, Open y Half-Open. Istio implementa circuit breakers que limitan los recursos del grupo de conexiones y la exclusión pasiva de endpoints con fallos. No expone un único mecanismo con esos tres estados para toda la malla. Los límites y las observaciones de salud son locales a cada proxy y a cada clúster upstream y nivel de prioridad; la concurrencia puede provocar que se sobrepasen temporalmente los límites. La exclusión de un endpoint lo retira de la selección de destinos durante un tiempo; no elimina el Pod. Los ejemplos siguientes son alternativas entre sí.

![Máquina de estados en la que el circuit breaker pasa de Closed a Open al superar el umbral de errores consecutivos, de Open a HalfOpen cuando transcurre el tiempo de espera y, según el resultado de la prueba, vuelve a Closed si tiene éxito o a Open si falla.](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-07-circuit-breaker-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-07-circuit-breaker-1.html)

## Configuración de los grupos de conexiones {#connection-pool-settings}

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-circuit-breaker
spec:
  host: reviews
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 2
```

## Detección de instancias con fallos {#outlier-detection}

La detección de instancias con fallos, denominada Outlier Detection, excluye temporalmente los endpoints no saludables del balanceo de carga, según los límites de exclusión y el comportamiento en modo de pánico.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-outlier
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5        # 5 consecutive errors
      interval: 30s               # Check every 30 seconds
      baseEjectionTime: 30s       # Minimum; repeated ejection can last longer
      maxEjectionPercent: 50      # Remove up to 50%
      minHealthPercent: 40        # Below this, disable outlier isolation and use all hosts
```

### Configuración avanzada de Outlier Detection

La detección de errores consecutivos puede excluir un endpoint en el momento de observarlos; `interval` controla las revisiones periódicas y no impone una espera antes de cada exclusión. `minHealthPercent` es un umbral de fail-open: permite volver a utilizar todos los destinos, en lugar de reservar una capacidad mínima saludable. `maxEjectionTime` es un campo de Envoy que esta API de DestinationRule de Istio no expone; no lo añada a estos manifiestos.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: advanced-outlier
spec:
  host: api-service
  trafficPolicy:
    outlierDetection:
      # Consecutive error based
      consecutiveGatewayErrors: 3    # HTTP 502/503/504
      consecutive5xxErrors: 5        # All HTTP 5xx

      # Time intervals
      interval: 10s                  # Check every 10 seconds
      baseEjectionTime: 30s          # First ejection time

      # Rate limits
      maxEjectionPercent: 50         # Remove up to 50%
      minHealthPercent: 30           # Fail-open/panic threshold, not a health guarantee

      # Separate local connection errors from upstream response errors
      splitExternalLocalOriginErrors: true
```

## Combinación con una política de reintentos {#combination-with-retry-policy}

Combine un circuit breaker con reintentos para aumentar la resiliencia.

### Combinación básica

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-retry
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
    retries:
      attempts: 3                    # 3 retries
      perTryTimeout: 2s              # 2 second timeout per attempt
      retryOn: 5xx,reset,connect-failure
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-circuit-breaker
spec:
  host: reviews
  trafficPolicy:
    connectionPool:
      http:
        http1MaxPendingRequests: 10
        maxRequestsPerConnection: 2
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
```

### Patrón de presupuesto de reintentos

Este presupuesto limita los reintentos simultáneos en relación con las solicitudes activas y pendientes de cada clúster del proxy; no limita las solicitudes por segundo. La política de reintentos se aplica a lecturas que admiten reintentos de forma segura, mientras que los demás métodos los deshabilitan explícitamente.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: payment-retry-budget
spec:
  hosts:
  - payment-service
  http:
  - match:
    - method:
        regex: "^(GET|HEAD)$"
    route:
    - destination:
        host: payment-service
    retries:
      attempts: 2                    # Minimize retries
      perTryTimeout: 1s              # Fast fail
      retryOn: connect-failure,refused-stream
  - route:
    - destination:
        host: payment-service
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: payment-circuit-breaker
spec:
  host: payment-service
  trafficPolicy:
    retryBudget:
      percent: 20
      minRetryConcurrency: 3
    connectionPool:
      http:
        http1MaxPendingRequests: 5   # Low queue
        maxRequestsPerConnection: 1  # 1 request per connection
    outlierDetection:
      consecutive5xxErrors: 3           # Fast blocking
      interval: 5s
      baseEjectionTime: 60s          # Long recovery time
```

## Ejemplos prácticos {#practical-examples}

### 1. Circuit breaker para servicios dentro de la malla

#### Escenario: protección de un servicio de base de datos

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: database-service-circuit-breaker
  namespace: production
spec:
  host: database-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100          # Maximum 100 connections
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

**Casos de uso**:
- Evitar el agotamiento del grupo de conexiones de la base de datos
- Impedir que las consultas lentas provoquen fallos en cascada
- Retirar automáticamente de la selección las instancias no saludables

Aquí, los protocolos nativos de las bases de datos solo utilizan los límites TCP y las observaciones de fallos correspondientes. El límite de conexiones de cada proxy no equivale al tamaño global del grupo de conexiones de la base de datos, ni permite inspeccionar consultas SQL lentas.

### 2. Patrón maxConnections: 1 (una única conexión)

#### Escenario: sistema heredado o servicio con recursos limitados

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: legacy-system-protection
spec:
  host: legacy-api-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 1            # Limit to 1 connection
      http:
        http1MaxPendingRequests: 1   # 1 pending request
        maxRequestsPerConnection: 1  # 1 request per connection
        h2UpgradePolicy: DO_NOT_UPGRADE  # Prevent HTTP/2 upgrade
    outlierDetection:
      consecutive5xxErrors: 1           # Block immediately on 1 error
      interval: 10s
      baseEjectionTime: 60s
```

**Casos de uso**:
- Sistemas heredados que no pueden gestionar conexiones simultáneas
- API externas con límites de solicitudes muy estrictos
- Operaciones que requieren procesamiento secuencial mediante una única conexión

`maxConnections: 1` no serializa las operaciones de toda la malla ni aplica una cuota global de una API externa. Cada proxy tiene sus propios límites, HTTP/2 puede multiplexar solicitudes y `maxRequestsPerConnection: 1` deshabilita la reutilización de conexiones, pero no garantiza una única ejecución. Para coordinar las operaciones globalmente, utilice una cola o un limitador de solicitudes en la aplicación.

### 3. Circuit breaker por subconjunto de destinos

#### Escenario: distintas configuraciones para cada versión

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-subset-circuit-breaker
spec:
  host: reviews
  trafficPolicy:
    # Default policy (all subsets)
    connectionPool:
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 2
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
  subsets:
  - name: v1
    labels:
      version: v1
    # v1 uses default policy

  - name: v2
    labels:
      version: v2
    trafficPolicy:
      # v2 has stricter policy (new version testing)
      connectionPool:
        http:
          http1MaxPendingRequests: 10
          maxRequestsPerConnection: 1
      outlierDetection:
        consecutive5xxErrors: 3
        interval: 10s
        baseEjectionTime: 60s

  - name: v3-canary
    labels:
      version: v3
    trafficPolicy:
      # v3 Canary is very strict (initial deployment)
      connectionPool:
        http:
          http1MaxPendingRequests: 5
          maxRequestsPerConnection: 1
      outlierDetection:
        consecutive5xxErrors: 1
        interval: 5s
        baseEjectionTime: 120s
```

### 4. Patrón avanzado de grupos de conexiones

#### Escenario: servicio de alto rendimiento

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: high-performance-service
spec:
  host: api-gateway
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 1000         # High concurrent connections
        connectTimeout: 3s
        tcpKeepalive:
          time: 7200s
          interval: 75s
          probes: 9
      http:
        http1MaxPendingRequests: 500
        http2MaxRequests: 1000
        maxRequestsPerConnection: 100  # Connection reuse
        idleTimeout: 300s
        h2UpgradePolicy: UPGRADE       # Use HTTP/2
    outlierDetection:
      consecutive5xxErrors: 10          # Lenient setting
      interval: 60s
      baseEjectionTime: 30s
      maxEjectionPercent: 20         # Remove up to 20% only
```

### 5. Circuit breaker basado en comprobaciones de salud

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: health-check-circuit-breaker
spec:
  host: payment-service
  trafficPolicy:
    outlierDetection:
      # HTTP status code based
      consecutiveGatewayErrors: 5    # 502, 503, 504
      consecutive5xxErrors: 3        # 500~599

      # Performance based
      interval: 10s
      baseEjectionTime: 30s

      # Dynamic adjustment
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 5
```

## Circuit breakers para servicios externos {#external-service-circuit-breaker}

Los ejemplos HTTP siguientes suponen que la aplicación envía HTTP sin cifrar a su sidecar, que inicia una conexión TLS con verificación hacia el host externo real en el puerto 443. Si la aplicación ya utiliza TLS, evite una segunda capa de TLS y aplique únicamente las políticas que puedan actuar sobre la información visible en esa capa. La configuración de TLS y autenticación nativos de MongoDB sigue siendo un requisito independiente del cliente y del servidor.

Utilice un circuit breaker junto con ServiceEntry para proteger los servicios externos.

### 1. Circuit breaker para una API externa

```yaml
# ServiceEntry: Register external API
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-payment-api
spec:
  hosts:
  - api.payment-provider.com
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
  resolution: DNS
---
# DestinationRule: Apply Circuit Breaker
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-payment-api-circuit-breaker
spec:
  host: api.payment-provider.com
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 10           # External API is limited
      http:
        http1MaxPendingRequests: 5
        maxRequestsPerConnection: 1  # Minimize connection reuse
    outlierDetection:
      consecutive5xxErrors: 3           # Fast blocking
      interval: 30s
      baseEjectionTime: 120s         # Long recovery time
      maxEjectionPercent: 100        # Can completely block
    tls:
      mode: SIMPLE
      sni: api.payment-provider.com
      subjectAltNames:
      - api.payment-provider.com
```

### 2. Circuit breaker para una base de datos externa

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-mongodb
spec:
  hosts:
  - mongodb.external-cluster.com
  ports:
  - number: 27017
    name: tcp
    protocol: TCP
  location: MESH_EXTERNAL
  resolution: DNS
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-mongodb-circuit-breaker
spec:
  host: mongodb.external-cluster.com
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 50
        connectTimeout: 5s
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 60s
      baseEjectionTime: 60s
```

### 3. Servicio externo con límite de solicitudes

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: rate-limited-api
spec:
  hosts:
  - api.rate-limited-service.com
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
  resolution: DNS
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: rate-limited-api-protection
spec:
  host: api.rate-limited-service.com
  trafficPolicy:
    connectionPool:
      http:
        http1MaxPendingRequests: 1   # Minimize queue
        maxRequestsPerConnection: 0  # Reuse connections; not a quota limiter
        idleTimeout: 1s              # Fast connection release
    outlierDetection:
      consecutive5xxErrors: 3           # Default HTTP 5xx detection; not 429
      interval: 60s
      baseEjectionTime: 30s          # Independent of provider Retry-After
    tls:
      mode: SIMPLE
      sni: api.rate-limited-service.com
      subjectAltNames:
      - api.rate-limited-service.com
---
# VirtualService: Retry settings
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: rate-limited-api-retry
spec:
  hosts:
  - api.rate-limited-service.com
  http:
  - route:
    - destination:
        host: api.rate-limited-service.com
    retries:
      attempts: 0                    # Disable retry (rate limit)
    timeout: 10s
```

Las respuestas HTTP 429 requieren limitar las solicitudes según las reglas del proveedor y respetar Retry-After. La detección predeterminada de errores 5xx y la apertura y cierre de conexiones no aplican una cuota de API ni permiten deducir cuándo se restablece.

## Monitorización y depuración {#monitoring-and-debugging}

### Consulta de las métricas de Envoy

```bash
# Check Circuit Breaker status
kubectl exec -it <pod-name> -c istio-proxy -- \
  curl localhost:15000/stats/prometheus | grep circuit_breakers

# Outlier Detection status
kubectl exec -it <pod-name> -c istio-proxy -- \
  curl localhost:15000/stats/prometheus | grep outlier_detection

# Connection Pool status
kubectl exec -it <pod-name> -c istio-proxy -- \
  curl localhost:15000/stats/prometheus | grep upstream_rq
```

### Métricas principales

```promql
# Prometheus queries
# Requests circuit-open gauge (0/1)
envoy_cluster_circuit_breakers_default_rq_open

# Pending-request circuit-open gauge (0/1)
envoy_cluster_circuit_breakers_default_rq_pending_open

# Outlier Detection Ejection
envoy_cluster_outlier_detection_ejections_active

# Connection pool overflow
envoy_cluster_upstream_rq_pending_overflow

# Retry count
envoy_cluster_upstream_rq_retry
```

### Panel de Grafana

```yaml
# Circuit Breaker Dashboard
- expr: envoy_cluster_circuit_breakers_default_rq_open
  legend: "Circuit Breaker Open State"

- expr: envoy_cluster_outlier_detection_ejections_active
  legend: "Ejected Instances"

- expr: rate(envoy_cluster_upstream_rq_pending_overflow[5m])
  legend: "Connection Pool Overflow"
```

### Comandos de istioctl

```bash
# Check Proxy configuration
istioctl proxy-config clusters <pod-name> --fqdn reviews.default.svc.cluster.local

# Check Circuit Breaker settings
istioctl proxy-config clusters <pod-name> -o json | \
  jq '.[] | select(.name=="outbound|9080||reviews.default.svc.cluster.local") | .circuitBreakers'

# Check Outlier Detection settings
istioctl proxy-config clusters <pod-name> -o json | \
  jq '.[] | select(.name=="outbound|9080||reviews.default.svc.cluster.local") | .outlierDetection'
```

## Consideraciones importantes {#important-considerations}

### Un circuit breaker no garantiza la consistencia de los datos

**Principio fundamental**: un circuit breaker es una herramienta de **aislamiento de fallos**. No evita por sí solo las **solicitudes duplicadas** ni **garantiza la consistencia de los datos**.

#### Funciones y limitaciones del circuit breaker

![Circuit breaker conectado a las funciones que realiza —aislar servicios con fallos, evitar fallos en cascada, proteger recursos e intentar la recuperación automática— y, mediante líneas discontinuas, a las que no realiza: prevención de duplicados, consistencia de datos, transacciones e idempotencia.](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-07-circuit-breaker-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-07-circuit-breaker-2.html)

#### Escenario problemático: reintentos y circuit breaker

![Secuencia de un POST de pago que el proxy de Istio reintenta tras perder cada respuesta: cada intento vuelve a insertar el pago, por lo que quedan tres registros duplicados antes de alcanzar los cinco errores consecutivos necesarios para activar el circuit breaker.](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-07-circuit-breaker-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-07-circuit-breaker-3.html)

**Problema**: antes de que se active el circuit breaker, tras cinco errores consecutivos, ya se han producido **tres pagos duplicados**.

#### Ejemplo de uso incorrecto

```yaml
# Dangerous: POST request + Retry + Circuit Breaker
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: payment-dangerous
spec:
  hosts:
  - payment-service
  http:
  - route:
    - destination:
        host: payment-service
    retries:
      attempts: 3  # 3 retries on POST
      perTryTimeout: 2s
      retryOn: 5xx,reset
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: payment-circuit-breaker
spec:
  host: payment-service
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s

# Result:
# - attempts: 3 allows up to 4 deliveries per original request; the ejection threshold is not a multiplier
# - Critical operations like payment, inventory deduction get duplicated
# - Data consistency destroyed
```

#### Patrones de uso correctos

**Patrón 1: reintentos seguros para lecturas; sin reintentos de la malla para escrituras**

```yaml
# Safe: Read-only + Circuit Breaker
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: product-catalog-safe
spec:
  hosts:
  - product-catalog
  http:
  - match:
    - method:
        regex: "GET|HEAD|OPTIONS"  # Read-only only
    route:
    - destination:
        host: product-catalog
    retries:
      attempts: 3  # GET is safe
      perTryTimeout: 2s
      retryOn: 5xx,reset,connect-failure
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: product-catalog-circuit-breaker
spec:
  host: product-catalog
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
```

```yaml
# Safe: Disable Retry for POST
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: payment-safe
spec:
  hosts:
  - payment-service
  http:
  - match:
    - method:
        exact: POST
    route:
    - destination:
        host: payment-service
    timeout: 10s
    retries:
      attempts: 0  # Disable Retry for POST
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: payment-circuit-breaker
spec:
  host: payment-service
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
```

**Patrón 2: idempotencia en la aplicación y circuit breaker**

La clave de idempotencia debe vincularse al llamante autenticado y al contenido de la solicitud, y registrarse de forma atómica junto con la modificación de negocio y su resultado. Comprobar la existencia de una clave en Redis, ejecutar el pago y escribir por separado en la caché permite condiciones de carrera; no es una implementación segura. Utilice el [flujo de idempotencia atómica](05-retry-timeout.md) y, cuando sea necesario, un contrato de idempotencia con el servicio de destino o un patrón outbox. Solo entonces aplique la política de reintentos siguiente: la mera presencia de la cabecera no basta.



```yaml
# Istio: Retry is safe when Idempotency is guaranteed
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: payment-with-idempotency
spec:
  hosts:
  - payment-service
  http:
  - match:
    - headers:
        x-idempotency-key:
          regex: ".+"  # Idempotency Key required
    route:
    - destination:
        host: payment-service
    retries:
      attempts: 3  # Safe with Idempotency
      perTryTimeout: 2s
      retryOn: 5xx,reset
  - route:  # Disable Retry without Idempotency Key
    - destination:
        host: payment-service
    retries:
      attempts: 0
```

#### Estrategia de seguridad según el tipo de servicio

| Tipo de servicio | Reintentos | Circuit breaker | Idempotencia necesaria |
|-------------|-------|----------------|---------------------|
| **Catálogo de productos** | 3 veces | Necesario | No es necesaria |
| **Carrito de compras** | Solo lecturas de forma predeterminada | Ajustar según sea necesario | Necesaria para modificaciones que admitan reintentos |
| **Creación de pedidos** | 0 veces | Necesario | Necesaria |
| **Pago** | 0 veces | Necesario | Necesaria |
| **Descuento de inventario** | 0 veces | Necesario | Necesaria |
| **Acumulación de puntos** | 0 veces | Necesario | Necesaria |
| **Envío de notificaciones** | Solo con eliminación de entregas duplicadas | Ajustar según sea necesario | Idempotencia de la entrega o del mensaje necesaria |

#### Grupos de conexiones y consistencia de los datos

La configuración de los grupos de conexiones tampoco **garantiza la consistencia de los datos**. Solo limita el número de conexiones simultáneas.

```yaml
# Misconception: Does maxConnections=1 prevent duplicates?
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: payment-single-connection
spec:
  host: payment-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 1  # Does NOT prevent duplicates
      http:
        http1MaxPendingRequests: 1

# maxConnections=1:
# - Only limits concurrent connections
# - Cannot prevent duplicate requests from Retry
# - Retries after network timeout are separate connections
```

#### Lista de comprobaciones prácticas

**Verificación antes del despliegue**:

- [ ] Revise la configuración de reintentos para solicitudes POST/PUT/DELETE/PATCH
- [ ] Establezca `attempts: 0` para escrituras no idempotentes, salvo que un contrato verificado de la aplicación permita reintentarlas
- [ ] Revise la posibilidad de duplicados al combinar un circuit breaker con reintentos
- [ ] Implemente claves de idempotencia para operaciones críticas, como pagos o cambios en el inventario
- [ ] Confirme que exista lógica de validación en la aplicación
- [ ] Simule fallos en un entorno de pruebas

**Monitorización**:

```bash
# Check Retry occurrence count
kubectl exec -n <namespace> <pod> -c istio-proxy -- \
  curl -s localhost:15000/stats/prometheus | grep upstream_rq_retry

# Check Circuit Breaker activation
kubectl exec -n <namespace> <pod> -c istio-proxy -- \
  curl -s localhost:15000/stats/prometheus | grep circuit_breakers

# Check logs for suspected duplicate requests
kubectl logs -n <namespace> <pod> | grep -i "duplicate\|idempotency"
```

## Buenas prácticas {#best-practices}

### 1. Configuración gradual

```yaml
# Stage 1: Start with lenient settings
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: service-circuit-breaker-stage1
spec:
  host: my-service
  trafficPolicy:
    connectionPool:
      http:
        http1MaxPendingRequests: 100
        maxRequestsPerConnection: 10
    outlierDetection:
      consecutive5xxErrors: 10        # Lenient
      interval: 60s
      baseEjectionTime: 30s
```

```yaml
# Stage 2: Adjust after monitoring
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: service-circuit-breaker-stage2
spec:
  host: my-service
  trafficPolicy:
    connectionPool:
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 5
    outlierDetection:
      consecutive5xxErrors: 5         # Moderate
      interval: 30s
      baseEjectionTime: 30s
```

### 2. Configuración según el tipo de servicio

```yaml
# Frontend service: Lenient
connectionPool:
  http:
    http1MaxPendingRequests: 100
    maxRequestsPerConnection: 10
outlierDetection:
  consecutive5xxErrors: 10
```

```yaml
# Backend service: Moderate
connectionPool:
  http:
    http1MaxPendingRequests: 50
    maxRequestsPerConnection: 5
outlierDetection:
  consecutive5xxErrors: 5
```

```yaml
# Native database/cache TCP example
connectionPool:
  tcp:
    maxConnections: 10
outlierDetection:
  consecutive5xxErrors: 3
```

```yaml
# External API: Very strict
connectionPool:
  http:
    http1MaxPendingRequests: 5
    maxRequestsPerConnection: 1
outlierDetection:
  consecutive5xxErrors: 1
```

### 3. Configuración de alertas

```yaml
# Prometheus Alert Rules
groups:
- name: circuit-breaker
  rules:
  - alert: CircuitBreakerOpen
    expr: envoy_cluster_circuit_breakers_default_rq_open > 0
    for: 1m
    annotations:
      summary: "Circuit breaker is open"

  - alert: HighConnectionPoolOverflow
    expr: rate(envoy_cluster_upstream_rq_pending_overflow[5m]) > 10
    for: 2m
    annotations:
      summary: "Connection pool overflow rate is high"

  - alert: HighOutlierEjectionRate
    expr: rate(envoy_cluster_outlier_detection_ejections_enforced_total[5m]) > 5
    for: 3m
    annotations:
      summary: "High outlier ejection rate"
```

### 4. Escenarios de prueba

Ejecute las pruebas de carga únicamente contra un servicio de pruebas preparado para ello. Observe por separado las métricas en tiempo real: proxy-config muestra los umbrales configurados, pero no indica si el circuit breaker está abierto en ese momento. Esperar 30 segundos no garantiza que un endpoint se recupere después de exclusiones repetidas.

```bash
#!/bin/bash
# Circuit Breaker test

# 1. Normal traffic
echo "=== Normal Traffic ==="
for i in {1..10}; do
  curl -s http://service/api | jq .status
  sleep 0.1
done

# 2. Increased load
echo "=== Increased Load ==="
for i in {1..100}; do
  curl -s http://service/api &
done
wait

# 3. Check Circuit Breaker status
echo "=== Circuit Breaker Status ==="
istioctl proxy-config clusters <pod> -o json | jq '.[] | .circuitBreakers'

# 4. Wait for recovery
echo "=== Waiting for Recovery ==="
sleep 30

# 5. Verify recovery
echo "=== Recovery Check ==="
curl -s http://service/api | jq .status
```

### 5. Plantilla de documentación

Sustituya las cifras ilustrativas de carga y recuperación por mediciones reales; no son garantías fijas de Istio. Habilite las estadísticas necesarias de Envoy y, si la imagen del proxy no incluye curl, utilice un reenvío de puertos local hacia la interfaz de administración o `istioctl dashboard envoy`.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: my-service-circuit-breaker
  annotations:
    # Configuration purpose
    purpose: "Protect database connection pool"

    # Threshold rationale
    threshold-rationale: |
      - maxConnections: 100 (DB connection pool size)
      - consecutive5xxErrors: 5 (observed error pattern)
      - baseEjectionTime: 30s (average recovery time)

    # Test results
    test-results: |
      - Load test: 1000 RPS without overflow
      - Failure test: Circuit opens after 5 errors
      - Recovery test: Auto-recovery after 30s

    # Operations guide
    operations: |
      - Monitor: envoy_cluster_circuit_breakers_*
      - Alert: Circuit open > 1min
      - Rollback: restore the reviewed previous DestinationRule configuration
spec:
  host: my-service
```

## Referencias

- [Circuit breakers en Istio](https://istio.io/latest/docs/tasks/traffic-management/circuit-breaking/)
- [Circuit breakers en Envoy](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/circuit_breaking)
- [Detección de instancias con fallos en Envoy](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/outlier)
- [Netflix Hystrix](https://github.com/Netflix/Hystrix/wiki/How-it-Works)

- [Referencia principal 1](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
- [Referencia principal 2](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/circuit_breaking)
- [Referencia principal 3](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/outlier)
- [Referencia principal 4](https://www.envoyproxy.io/docs/envoy/latest/configuration/upstream/cluster_manager/cluster_stats)
- [Referencia principal 5](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)
- [Referencia principal 6](https://istio.io/latest/docs/tasks/traffic-management/egress/egress-tls-origination/)
