# Reintentos y tiempos de espera

El reintento y el tiempo de espera son mecanismos fundamentales para mejorar la resiliencia de los microservicios. Con Istio, puede configurar estas políticas sin modificar el código de la aplicación.

## Tabla de contenido

1. [Descripción general](#overview)
2. [Configuración del tiempo de espera](#timeout-configuration)
3. [Configuración de reintentos](#retry-configuration)
4. [Combinación de reintentos y tiempo de espera](#combining-retry-and-timeout)
5. [Ejemplos prácticos](#practical-examples)
6. [Advertencias importantes](#important-warnings)
7. [Prácticas recomendadas](#best-practices)
8. [Solución de problemas](#troubleshooting)

## Descripción general {#overview}

Los ejemplos presentan políticas HTTP alternativas para sidecars y presuponen operaciones seguras para reintentar, salvo que se muestre una política de escritura. SQL nativo y HTTPS opaco generado por la aplicación no pueden usar estas reglas HTTP de reintentos y tiempos de espera. Establezca también un plazo límite en el cliente; los reintentos en varias capas multiplican los intentos que llegan al backend y pueden exceder el tiempo de espera local de una capa.

### ¿Por qué usar tiempos de espera y reintentos?

![Sin tiempos de espera ni reintentos, el cliente espera indefinidamente a un servicio que no responde y desperdicia recursos; con el tiempo de espera y los reintentos de Istio, se detiene tras 1 s, reintenta en otra instancia y la solicitud tiene éxito.](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-05-retry-timeout-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-05-retry-timeout-0.html)

## Configuración del tiempo de espera {#timeout-configuration}

### Tiempo de espera básico

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-timeout
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
    timeout: 10s  # Timeout after 10 seconds
```

### Tiempo de espera específico por ruta

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-timeouts
spec:
  hosts:
  - api.example.com
  http:
  # Fast response API - short timeout
  - match:
    - uri:
        prefix: "/api/quick"
    route:
    - destination:
        host: api-service
    timeout: 1s

  # Standard API
  - match:
    - uri:
        prefix: "/api/standard"
    route:
    - destination:
        host: api-service
    timeout: 5s

  # Heavy operations - long timeout
  - match:
    - uri:
        prefix: "/api/batch"
    route:
    - destination:
        host: api-service
    timeout: 30s
```

## Configuración de reintentos {#retry-configuration}

> **Importante:** Omitir `retries` no significa necesariamente que los reintentos estén desactivados. El valor predeterminado renderizado de Istio 1.31.0 es `attempts: 2` y `retryOn: connect-failure,refused-stream,unavailable,cancelled,retriable-status-codes`. `attempts` cuenta los **reintentos adicionales después de la solicitud original**, por lo que pueden producirse tres entregas en total. Configure `attempts: 0` en la ruta para desactivar explícitamente los reintentos del proxy.

La referencia de HTTPRetry abrevia esa lista; la implementación publicada de reintentos también habilita `retriable-status-codes` para los códigos configurados. Los valores predeterminados del clúster se pueden sobrescribir. Una política de reintentos explícita debe indicar las condiciones previstas; no suponga que se reintenta ante cualquier tiempo de espera ni que siempre habrá otro endpoint en buen estado.

### Reintento básico

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
      attempts: 3  # Maximum 3 retries
      perTryTimeout: 2s  # 2s timeout per attempt
      retryOn: 5xx,reset,connect-failure,refused-stream  # Retry conditions
```

### Condiciones de reintento

| Condición | Descripción |
|-----------|-------------|
| `5xx` | Errores HTTP 5xx |
| `gateway-error` | Errores 502, 503 y 504 |
| `reset` | Conexión restablecida |
| `connect-failure` | Fallo de conexión |
| `refused-stream` | HTTP/2 REFUSED_STREAM |
| `retriable-4xx` | 409 Conflict |
| `retriable-status-codes` | Códigos de estado personalizados |

### Configuración avanzada de reintentos

`payment-service` acepta escrituras no idempotentes (envío de cargos), por lo que una sola política de reintentos aplicada a todos los métodos permitiría que la malla repitiera un POST tras `reset` o `5xx`, precisamente el riesgo de repetición ambigua que advierte esta página. En su lugar, divida la ruta por método: permita reintentos generosos para las consultas de estado de solo lectura y desactive por completo los reintentos de la malla en la ruta de escritura.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: advanced-retry
spec:
  hosts:
  - payment-service
  http:
  - name: reads-retryable
    match:
    - method:
        regex: "^(GET|HEAD)$"
    route:
    - destination:
        host: payment-service
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: connect-failure,refused-stream
      retryRemoteLocalities: true  # Retry to other regions
  - name: writes-no-mesh-retry
    match:
    - method:
        regex: "^(POST|PUT|PATCH|DELETE)$"
    route:
    - destination:
        host: payment-service
    retries:
      attempts: 0
```

## Combinación de reintentos y tiempo de espera {#combining-retry-and-timeout}

### Tiempos de espera en capas

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: layered-timeouts
spec:
  hosts:
  - frontend
  http:
  - route:
    - destination:
        host: frontend
    timeout: 10s  # Total timeout
    retries:
      attempts: 3
      perTryTimeout: 3s  # Timeout for each delivery, including the original
```

**Cálculo**: el límite teórico del tiempo de entrega es `(1 + attempts) × perTryTimeout = 4 × 3s = 12s`, pero primero se aplica el `timeout: 10s` de nivel de ruta. El retroceso y el tiempo de espera restante de la ruta pueden reducir el número de reintentos que realmente se intentan.

### Dividir la política de reintentos por método HTTP

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: order-service
spec:
  hosts:
  - order-service
  http:
  # POST/PATCH: do not replay an ambiguous write in the mesh
  - name: writes-no-mesh-retry
    match:
    - method:
        regex: "^(POST|PUT|PATCH|DELETE)$"
    route:
    - destination:
        host: order-service
    timeout: 10s
    retries:
      attempts: 0

  # GET/HEAD: retry only connection establishment and REFUSED_STREAM failures
  - name: reads-limited-retry
    match:
    - method:
        regex: "^(GET|HEAD)$"
    route:
    - destination:
        host: order-service
    timeout: 5s
    retries:
      attempts: 2
      perTryTimeout: 2s
      retryOn: connect-failure,refused-stream
```

Desactive de forma predeterminada los reintentos de la malla para POST/PATCH y para cualquier operación que el dominio defina como escritura. No deduzca que PUT o DELETE son seguros solo por el método HTTP: reinténtelos únicamente cuando el contrato real de la aplicación garantice que la ejecución repetida es segura.

## Ejemplos prácticos {#practical-examples}

### Ejemplo 1: Cadena de microservicios

```yaml
# Frontend → Backend → Database
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: frontend
spec:
  hosts:
  - frontend
  http:
  - route:
    - destination:
        host: frontend
    timeout: 15s  # Consider entire chain
    retries:
      attempts: 2
      perTryTimeout: 7s
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: backend
spec:
  hosts:
  - backend
  http:
  - route:
    - destination:
        host: backend
    timeout: 10s  # Consider database call
    retries:
      attempts: 3
      perTryTimeout: 3s
      retryOn: 5xx,reset
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: database
spec:
  hosts:
  - database
  http:
  - route:
    - destination:
        host: database
    timeout: 5s
    retries:
      attempts: 2
      perTryTimeout: 2s
      retryOn: connect-failure,refused-stream
```

### Ejemplo 2: Llamada a una API externa

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-api
spec:
  hosts:
  - api.external.com
  http:
  - route:
    - destination:
        host: api.external.com
    timeout: 30s  # External APIs can be slow
    retries:
      attempts: 5  # External APIs have frequent transient failures
      perTryTimeout: 5s
      retryOn: 5xx,reset,connect-failure,gateway-error
---
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
spec:
  hosts:
  - api.external.com
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
  name: external-api-tls
spec:
  host: api.external.com
  trafficPolicy:
    tls:
      mode: SIMPLE
      sni: api.external.com
      subjectAltNames:
      - api.external.com
```

Para este ejemplo de llamada saliente, invoque `http://api.external.com` desde la aplicación y sustituya el nombre de host por el del servicio real. Si la aplicación ya inicia una conexión HTTPS, no se pueden inspeccionar sus mensajes HTTP cifrados para aplicar estas condiciones de reintento.

### Ejemplo 3: Combinación con Circuit Breaker

`payment` procesa escrituras no idempotentes, por lo que este ejemplo divide las rutas por método, igual que el ejemplo anterior de `payment-service`: los reintentos se permiten ampliamente para las lecturas, se desactivan en la malla para las escrituras y el Circuit Breaker siguiente se aplica a ambas.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: resilient-service
spec:
  hosts:
  - payment
  http:
  - name: reads-retryable
    match:
    - method:
        regex: "^(GET|HEAD)$"
    route:
    - destination:
        host: payment
    timeout: 10s
    retries:
      attempts: 3
      perTryTimeout: 3s
      retryOn: connect-failure,refused-stream
  - name: writes-no-mesh-retry
    match:
    - method:
        regex: "^(POST|PUT|PATCH|DELETE)$"
    route:
    - destination:
        host: payment
    timeout: 10s
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: payment-circuit-breaker
spec:
  host: payment
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 2
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

## Advertencias importantes {#important-warnings}

### Riesgos de reintento para solicitudes no idempotentes

**Principio fundamental**: Los reintentos automáticos de Istio Proxy para POST/PATCH y para escrituras no idempotentes definidas por el dominio pueden causar **problemas de coherencia de datos**. Trate PUT/DELETE como excepciones solo cuando el contrato real de la aplicación garantice la idempotencia.

#### Escenario del problema

![Una orden POST tiene éxito, pero la pérdida de la respuesta hace que el proxy de Istio reintente automáticamente y cree un pedido duplicado, mientras todos ven 200 OK.](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-05-retry-timeout-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-05-retry-timeout-1.html)

#### ¿Por qué es peligroso?

1. **Creación duplicada**: La solicitud POST tuvo éxito, pero la respuesta se perdió por problemas de red; el proxy vuelve a intentarlo y crea **registros duplicados**.
2. **Cambios de estado incorrectos**: Las operaciones críticas para el negocio, como los **pagos y las deducciones de inventario**, pueden ejecutarse varias veces.
3. **No se puede verificar**: Istio Proxy no puede confirmar si la solicitud tuvo éxito.

#### Estrategia segura de reintentos

**Recomendación: desactive los reintentos de la malla y aplique la deduplicación en la aplicación.**

```yaml
# Istio: explicitly do not retry a non-idempotent write
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: order-service
spec:
  hosts:
  - order-service
  http:
  - match:
    - method:
        exact: POST
    route:
    - destination:
        host: order-service
    timeout: 10s
    retries:
      attempts: 0  # No delivery after the original request
```

`reset`, `503` y un tiempo de espera no demuestran que el servidor haya rechazado la solicitud. El servidor puede confirmar la transacción de la base de datos y perder únicamente la respuesta, por lo que el proxy no puede determinar si es seguro repetirla. Tras un resultado ambiguo, la aplicación debe consultar el estado de la operación en vez de reenviar la solicitud a ciegas.

```python
# Client excerpt: requires an API with an atomic idempotency contract.
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def create_order_with_idempotency(order_data, idempotency_key):
    # Persist one key per logical order; reuse it after ambiguous failures.
    if not idempotency_key:
        raise ValueError("A persisted operation idempotency key is required")
    retries = Retry(
        total=3,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["POST"],
        backoff_factor=1,
    )
    with requests.Session() as session:
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        response = session.post(
            "http://order-service/orders",
            json=order_data,
            headers={"X-Idempotency-Key": idempotency_key},
            timeout=(3, 10),
        )
        response.raise_for_status()
        return response.json()
```

El servidor debe aplicar el contrato de forma atómica. Comprobar `exists` en Redis, crear el pedido y escribir por separado en la caché permite que se creen pedidos duplicados de forma concurrente y genera ventanas de fallo; no es una implementación segura de deduplicación.

1. Valide la clave y vincúlela con el usuario autenticado y una huella de la carga útil de la solicitud.
2. Use una restricción de unicidad en la base de datos para reservar la clave y serialice los intentos concurrentes.
3. Confirme en una sola transacción la modificación del pedido y el estado/respuesta guardados junto con esa clave.
4. Devuelva el resultado guardado si se repite la misma clave y carga útil; rechace el uso de esa clave con una carga útil diferente.
5. Coordine los efectos externos irreversibles mediante una outbox o una API descendente idempotente. Defina la retención para cubrir la ventana de reintentos admitida.

El ejemplo del cliente presupone que este contrato ya existe en el servidor. La cabecera por sí sola no hace que POST sea seguro; además, el tiempo de espera de Requests se aplica a cada intento y a las fases de conexión/lectura, no a todo el plazo de reintentos.

Combine estas salvaguardas para las API de escritura de producción:

- una `Idempotency-Key` respaldada por una restricción de unicidad en la base de datos dentro de la misma transacción
- `ETag`/`If-Match` o una operación de comparación e intercambio del campo de versión para las actualizaciones
- consulta del estado por ID de transacción o ID de comando después de un tiempo de espera o un restablecimiento
- una transactional outbox para efectos descendentes irreversibles, como pagos o publicación de eventos

#### Seguridad de los reintentos según el método HTTP

| Método | Idempotente | Seguridad de reintento de Istio | Configuración recomendada |
|--------|------------|-------------------|---------------------|
| **GET** | Sí | Seguro | `attempts: 3, retryOn: 5xx,reset` |
| **HEAD** | Sí | Seguro | `attempts: 3, retryOn: 5xx,reset` |
| **OPTIONS** | Sí | Seguro | `attempts: 3, retryOn: 5xx,reset` |
| **PUT** | Depende del contrato | Precaución | Contrato de idempotencia real + actualización condicional |
| **DELETE** | Depende del contrato | Precaución | Contrato de idempotencia real + consulta del resultado |
| **POST** | Por lo general, no | Peligroso | `attempts: 0`, Idempotency Key |
| **PATCH** | Por lo general, no | Peligroso | `attempts: 0`, versión/ETag |

#### Casos en los que es seguro reintentar

```yaml
# Read-only requests - safe
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-service-reads
spec:
  hosts:
  - api-service
  http:
  - match:
    - method:
        regex: "GET|HEAD|OPTIONS"
    route:
    - destination:
        host: api-service
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: 5xx,reset,connect-failure
```

```yaml
# Write requests with idempotency guaranteed
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: idempotent-writes
spec:
  hosts:
  - api-service
  http:
  - match:
    - method:
        exact: PUT
      headers:
        x-idempotency-key:
          regex: ".+"  # Only when Idempotency Key present
    route:
    - destination:
        host: api-service
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: 5xx,reset
```

#### Precaución al usarlo con Circuit Breaker

Circuit Breaker es eficaz para **aislar fallos**, pero **no puede evitar la ejecución duplicada** de solicitudes no idempotentes.

```yaml
# Bad example: POST + Circuit Breaker + Retry
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: payment-service
spec:
  hosts:
  - payment-service
  http:
  - route:
    - destination:
        host: payment-service
    retries:
      attempts: 3  # 3 retries for POST is dangerous
      retryOn: 5xx
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
      baseEjectionTime: 30s

# Result: Before the Circuit Breaker opens,
# duplicate payments can occur 3 times!
```

```yaml
# Good example: Use Circuit Breaker only, retry at application level
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: payment-service
spec:
  hosts:
  - payment-service
  http:
  - route:
    - destination:
        host: payment-service
    timeout: 10s
    retries:
      attempts: 0  # Completely disable retry
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
      baseEjectionTime: 30s
```

#### Directrices prácticas

1. **GET/HEAD/OPTIONS**: Se pueden usar reintentos de Istio Proxy.
2. **POST/PATCH**: Desactive los reintentos de Istio; use reintentos en la aplicación y una Idempotency Key.
3. **PUT/DELETE**: Use reintentos de Istio solo si la idempotencia está garantizada.
4. **Operaciones críticas (pagos/inventario/puntos)**: Deben incluir validación en la aplicación y una Idempotency Key.

## Prácticas recomendadas {#best-practices}

### 1. Guía para configurar tiempos de espera

```yaml
# Good example: Appropriate timeout per layer
# Frontend: 15s
# API Gateway: 10s
# Backend Service: 5s
# Database: 3s

apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-gateway
spec:
  hosts:
  - api-gateway
  http:
  - route:
    - destination:
        host: api-gateway
    timeout: 10s
    retries:
      attempts: 2
      perTryTimeout: 4s
```

```yaml
# Bad example: Timeout too long
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-gateway
spec:
  hosts:
  - api-gateway
  http:
  - route:
    - destination:
        host: api-gateway
    timeout: 300s  # Illustrative poor fit for a short interactive request; streaming differs
```

### 2. Estrategia de reintentos

```yaml
# Good example: Consider idempotency
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-service
spec:
  hosts:
  - api-service
  http:
  # GET - safe to retry
  - match:
    - method:
        exact: GET
    route:
    - destination:
        host: api-service
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: 5xx,reset,connect-failure

  # POST/PATCH - explicitly disable mesh retry
  - match:
    - method:
        regex: "^(POST|PUT|PATCH|DELETE)$"
    route:
    - destination:
        host: api-service
    retries:
      attempts: 0
```

### 3. Retroceso exponencial

Envoy usa un retroceso exponencial con jitter completo y un intervalo base predeterminado de 25 ms; los retrasos reales no siguen una secuencia fija de 25/50/100 ms. El ejemplo configura una base personalizada para las lecturas y desactiva explícitamente los reintentos en la ruta de escritura:

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: backoff-retry
spec:
  hosts:
  - payment
  http:
  - match:
    - method:
        regex: "^(GET|HEAD)$"
    route:
    - destination:
        host: payment
    retries:
      attempts: 5
      perTryTimeout: 2s
      retryOn: connect-failure,refused-stream
      backoff: 100ms
  - route:
    - destination:
        host: payment
    retries:
      attempts: 0
```

### 4. Cálculo del tiempo de espera total del sistema

```yaml
# Frontend → API Gateway → Backend → Database
# Frontend: 20s
# API Gateway: 15s (must be less than Frontend)
# Backend: 10s (must be less than API Gateway)
# Database: 5s (must be less than Backend)

# Each layer should consider downstream timeout + overhead
```

## Solución de problemas {#troubleshooting}

### El tiempo de espera no funciona

```bash
# 1. Check VirtualService
kubectl get virtualservice -n <namespace>
kubectl describe virtualservice <name> -n <namespace>

# 2. Check Envoy configuration
istioctl proxy-config routes <pod-name> -n <namespace> -o json | grep timeout

# 3. Test actual timeout
kubectl exec -it <pod-name> -n <namespace> -c <app-container> -- \
  curl -v --max-time 15 http://backend-service
```

### Hay demasiados reintentos

Genere tráfico desde un contenedor de la aplicación que tenga `curl` instalado, no desde el UID de `istio-proxy` (que puede omitir la interceptación). Para la prueba, configure el plazo de `curl` por encima del tiempo de espera de la ruta. Mida los reintentos con los contadores de Envoy, habilitados mediante el proxy stats matcher; la marca de respuesta `UR` significa restablecimiento remoto del upstream, no es un contador de reintentos.

```promql
sum(rate(envoy_cluster_upstream_rq_retry[5m]))
```

### Cómo evitar tormentas de reintentos

```yaml
# Use with Circuit Breaker
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: prevent-retry-storm
spec:
  host: backend
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 10  # Limit pending requests
        http2MaxRequests: 100
        maxRequestsPerConnection: 1
    outlierDetection:
      consecutive5xxErrors: 3  # Fast circuit break
      interval: 10s
      baseEjectionTime: 30s
```

## Referencias

- [Tiempo de espera de Istio](https://istio.io/latest/docs/reference/config/networking/virtual-service/#HTTPRoute)
- [Reintentos de Istio](https://istio.io/latest/docs/reference/config/networking/virtual-service/#HTTPRetry)
- [Política de reintentos de Envoy](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/router_filter#config-http-filters-router-x-envoy-retry-on)
- [RFC 9110: métodos idempotentes](https://www.rfc-editor.org/rfc/rfc9110.html#name-idempotent-methods)

- [Referencia primaria 1](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
- [Referencia primaria 2](https://raw.githubusercontent.com/istio/istio/1.31.0/pilot/pkg/networking/core/route/retry/retry.go)
- [Referencia primaria 3](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/router_filter)
- [Referencia primaria 4](https://www.rfc-editor.org/rfc/rfc9110.html#name-idempotent-methods)
- [Referencia primaria 5](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)
- [Referencia primaria 6](https://raw.githubusercontent.com/psf/requests/main/docs/user/advanced.rst)
- [Referencia primaria 7](https://raw.githubusercontent.com/urllib3/urllib3/main/src/urllib3/util/retry.py)
- [Referencia primaria 8](https://istio.io/latest/docs/tasks/traffic-management/egress/egress-tls-origination/)
