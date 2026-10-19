# Cuestionario de resiliencia

> **Última actualización**: 12 de octubre de 2026
>
> **Versiones**: Istio 1.31, compatible con Kubernetes 1.32–1.37.
> Consulte el capítulo de instalación para conocer la compatibilidad con EKS.

Este cuestionario evalúa su comprensión de las funciones de resiliencia de Istio.

Cada ejemplo es independiente y presupone que existen los Services, las etiquetas, los namespaces y las aplicaciones con sidecar que atienden HTTP en el puerto 8080 indicados. Los valores sirven de ejemplo; las comprobaciones locales de esquemas y consultas no sustituyen las pruebas en producción ni las pruebas de carga. Los ejemplos de localidad usan `localityLbSetting`, no la API independiente `zoneAwareLbSetting`.

## Preguntas de opción múltiple (1-5)

### Pregunta 1: Conceptos básicos de Outlier Detection

¿Cuál de las siguientes opciones **NO** es un propósito principal de Outlier Detection?

A. Detectar automáticamente instancias con comportamiento anómalo\
B. Excluirlas temporalmente cuando lo permitan el umbral de fallos configurado y el límite de expulsiones\
C. Eliminar permanentemente las instancias retiradas\
D. Permitir que un host excluido temporalmente vuelva a recibir tráfico cuando termine su período de expulsión

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C**

Outlier Detection **no elimina instancias**: las excluye temporalmente del conjunto de destinos que pueden recibir tráfico.

**Explicación:**

**Cómo funciona Outlier Detection:**


**Características principales:**

1. **Detección automática**: Cuenta los fallos HTTP o de transporte consecutivos que cumplen los criterios configurados
2. **Expulsión automática**: Excluye temporalmente un destino del tráfico cuando se supera el umbral
3. **Reincorporación**: Al vencer el período de expulsión, el destino vuelve a ser elegible; esto no envía una sonda activa ni demuestra que se haya recuperado
4. **Medida temporal**: Impide que el destino reciba tráfico sin eliminar la instancia

**Por qué la opción C es incorrecta:**

* Outlier Detection es un patrón de circuit breaker
* **Excluye temporalmente** las instancias sin eliminarlas
* El tráfico posterior que termina correctamente confirma la recuperación; nuevos fallos pueden provocar expulsiones más prolongadas

**Referencia:**

* [Outlier Detection](../../../service-mesh/istio/resilience/01-outlier-detection.md)

</details>

***

### Pregunta 2: Comparación de tipos de Rate Limiting

¿Qué afirmación compara correctamente Local Rate Limiting y Global Rate Limiting?

A. Local Rate Limiting tiene mayor precisión\
B. Global Rate Limiting tiene un rendimiento más rápido\
C. Local Rate Limiting limita las solicitudes de forma independiente en cada proxy Envoy\
D. Global Rate Limiting funciona sin servicios externos

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C**

Local Rate Limiting limita las solicitudes **de forma independiente en cada proxy Envoy**.

**Explicación:**

**Comparación entre Local y Global Rate Limiting:**

| Característica | Local Rate Limiting | Global Rate Limiting |
| --- | --- | --- |
| **Ámbito de la cuota** | Depósito local configurado | Dominio, descriptor y ventana compartidos |
| **Rendimiento** | Muy rápido | Ligeramente más lento |
| **Complejidad** | Baja | Alta: requiere un servicio externo |
| **Caso de uso** | Protección general | Límites que requieren precisión |

**Características de Local Rate Limiting:**

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: local-ratelimit
  namespace: default
spec:
  workloadSelector:
    labels:
      app: myapp
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        portNumber: 8080
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 100
            tokens_per_fill: 10
            fill_interval: 1s
          filter_enabled:
            default_value:
              numerator: 100
              denominator: HUNDRED
          filter_enforced:
            default_value:
              numerator: 100
              denominator: HUNDRED
```

El depósito del ejemplo comienza con 100 tokens y recibe 10 tokens por segundo. Con una distribución adecuada de la carga, tres réplicas pueden admitir unas 30 solicitudes por segundo en conjunto, además de sus ráfagas independientes. Esto no equivale a un límite compartido de 30 solicitudes por segundo.

**Características de Global Rate Limiting:**

```yaml
# Configured shared descriptor quota:100 per backend second-window
# Actual enforcement depends on the shared backend, window and failure policy
# Requires an actual gRPC rate-limit service plus shared counter storage such as Redis
```

**Algoritmo Token Bucket:**

![Funcionamiento de un limitador de tasa con un depósito de tokens: el depósito admite como máximo 100 tokens y recibe 10 por segundo. Cada solicitud consume un token para ser admitida o recibe HTTP 429 cuando no quedan tokens.](../../../.gitbook/assets/en-quizzes-service-mesh-istio-resilience-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-quizzes-service-mesh-istio-resilience-1.html)

**Referencia:**

* [Rate Limiting](../../../service-mesh/istio/resilience/02-rate-limiting.md)

</details>

***

### Pregunta 3: Beneficios de Zone Aware Routing

¿Cuál **NO** es un beneficio de usar Zone Aware Routing?

A. Menor latencia al comunicarse dentro de la misma AZ\
B. Ahorro en la transferencia de datos entre AZ\
C. Mejora garantizada de la disponibilidad al colocar todas las réplicas de un servicio en una sola AZ\
D. Conmutación a endpoints sanos y accesibles cuando existen la política y la capacidad necesarias

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C**

La opción C no ofrece esa garantía. La localidad depende del cliente que realiza la llamada y puede concentrar su tráfico en la zona local. Colocar todas las réplicas en una sola AZ crea un dominio de fallo compartido y puede sobrecargar esa zona.

**Explicación:**

**Comportamiento correcto de Zone Aware Routing:**


**Beneficios reales de Zone Aware Routing:**

El enrutamiento dentro de la misma zona puede reducir la latencia de red y los bytes facturables entre zonas. La latencia, los precios y el ahorro concretos dependen del despliegue. Una distribución 80/10/10 envía tráfico normal a las tres zonas sanas: las dos porciones del 10% no son capacidad en espera para una conmutación por fallo. Las otras zonas deben tener endpoints accesibles y capacidad disponible.

**Ejemplo de configuración de DestinationRule:**

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            us-east-1/us-east-1a/*: 80
            us-east-1/us-east-1b/*: 10
            us-east-1/us-east-1c/*: 10
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 0
```

**Referencia:**

* [Zone Aware Routing](../../../service-mesh/istio/resilience/03-zone-aware-routing.md)

</details>

***

### Pregunta 4: Parámetros de Outlier Detection

¿Cuál es la condición para expulsar una instancia con la siguiente configuración de Outlier Detection?

```yaml
outlierDetection:
  consecutive5xxErrors: 5
  interval: 30s
  baseEjectionTime: 30s
  maxEjectionPercent: 50
```

A. Cuando se producen errores durante 5 segundos\
B. Cuando 5 fallos 5xx consecutivos que cumplen los criterios alcanzan el umbral, sujeto al límite de expulsiones\
C. Cuando la tasa de errores supera el 50% durante 30 segundos\
D. Expulsar incondicionalmente cada 30 segundos

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B**

La opción B identifica el desencadenante. Cinco fallos consecutivos que cumplen los criterios pueden activar la expulsión al detectarse; `interval` fija la frecuencia del barrido periódico y `maxEjectionPercent` puede impedir que se aplique la expulsión. Una respuesta correcta pero lenta no constituye por sí sola un caso de latencia anómala.

**Explicación:**

**Parámetros principales de Outlier Detection:**

| Parámetro              | Descripción                 | Predeterminado | Rango de ejemplo |
| ---------------------- | --------------------------- | ------- | ----------- |
| **consecutive5xxErrors**  | Umbral de errores consecutivos | 5       | 3-10        |
| **interval**           | Intervalo de análisis           | 10s     | 10s-60s     |
| **baseEjectionTime**   | Tiempo mínimo de expulsión       | 30s     | 30s-300s    |
| **maxEjectionPercent** | Proporción máxima de expulsión      | 10%     | 10%-50%     |

**Explicación detallada de los parámetros:**

**consecutive5xxErrors**

```yaml
# Sensitive service (fast detection)
consecutive5xxErrors: 3

# General service
---
consecutive5xxErrors: 5

# Lenient setting (prevent false positives)
---
consecutive5xxErrors: 10
```

**interval**

```yaml
# Fast detection (high load)
interval: 10s

# Typical case
---
interval: 30s

# Stable service
---
interval: 60s
```

**baseEjectionTime**

```yaml
# Quick recovery attempt
baseEjectionTime: 30s

# Typical case
---
baseEjectionTime: 60s

# Cautious recovery
---
baseEjectionTime: 300s
```

**maxEjectionPercent**

```yaml
# Conservative (stability priority)
maxEjectionPercent: 10

# Balanced setting
---
maxEjectionPercent: 30

# Aggressive (performance priority)
---
maxEjectionPercent: 50
```

**Ejemplo completo de DestinationRule:**

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-outlier
  namespace: default
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 0
```

**Ejemplo de funcionamiento:**

Una operación que termina correctamente reinicia la secuencia de fallos consecutivos correspondiente. Si un host alcanza el umbral, puede ser expulsado cuando el límite lo permita; vuelve a ser elegible al terminar su período real de expulsión. Las expulsiones repetidas prolongan ese período mediante el multiplicador y el límite de Envoy. `minHealthPercent` es un umbral para el modo de pánico o fail-open, no una garantía de que cierta fracción de los Pods esté sana; el valor 0 deshabilita ese umbral.

**Referencia:**

* [Outlier Detection](../../../service-mesh/istio/resilience/01-outlier-detection.md)

</details>

***

### Pregunta 5: Algoritmo Token Bucket

Con un token por solicitud y demanda sostenida, ¿qué tasa media de admisión permite la reposición de tokens una vez consumida la ráfaga inicial?

```yaml
token_bucket:
  max_tokens: 100
  tokens_per_fill: 10
  fill_interval: 1s
```

A. 10 req/s\
B. 100 req/s\
C. 110 req/s\
D. 1000 req/s

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A**

Con `tokens_per_fill: 10` y `fill_interval: 1s`, **se agregan 10 tokens por segundo**, por lo que el promedio es **10 req/s**.

**Explicación:**

**Parámetros del algoritmo Token Bucket:**

* **max\_tokens**: Número máximo de tokens almacenados en el depósito; determina la ráfaga admisible
* **tokens\_per\_fill**: Tokens añadidos en cada fill\_interval; determina la **tasa media de admisión**
* **fill\_interval**: Intervalo entre reposiciones de tokens

**Método de cálculo:**

```
Average request rate = tokens_per_fill / fill_interval
                     = 10 / 1s
                     = 10 req/s

Burst throughput = max_tokens
                 = 100 req (for a brief moment)
```

**Comportamiento a lo largo del tiempo:**

```
T=0: 100 tokens in bucket (initial state)
     Can admit up to100 immediate requests if the bucket is full; backend concurrency is separate

T=0.1s: Bucket empty (0 tokens)
        Additional requests rejected

T=1s: 10 tokens added (Refill)
      Can handle 10 requests

T=2s: 10 tokens added
      Can handle 10 requests

Average: 10 req/s (sustainable throughput)
Burst allowance:100 requests from a full bucket, not a sustained req/s rate
```

**Ejemplos prácticos de configuración:**

```yaml
# Scenario 1: General API endpoint
token_bucket:
  max_tokens: 100        # Allow burst of 100
  tokens_per_fill: 10    # Average 10 req/s
  fill_interval: 1s

# Scenario 2: High-performance API
---
token_bucket:
  max_tokens: 1000       # Allow burst of 1000
  tokens_per_fill: 100   # Average 100 req/s
  fill_interval: 1s

# Scenario 3: Limited resource
---
token_bucket:
  max_tokens: 10         # Only 10 burst
  tokens_per_fill: 1     # Average 1 req/s
  fill_interval: 1s
```

**Ejemplo completo de EnvoyFilter:**

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: local-ratelimit
  namespace: default
spec:
  workloadSelector:
    labels:
      app: myapp
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        portNumber: 8080
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 100
            tokens_per_fill: 10
            fill_interval: 1s
          filter_enabled:
            default_value:
              numerator: 100
              denominator: HUNDRED
          filter_enforced:
            default_value:
              numerator: 100
              denominator: HUNDRED
```

**Referencia:**

* [Rate Limiting](../../../service-mesh/istio/resilience/02-rate-limiting.md)

</details>

***

## Preguntas de respuesta corta (6-10)

### Pregunta 6: Implementación de Outlier Detection

El servicio `product-service`, que se ejecuta en producción, presenta lentitud intermitente y fallos por tiempo de espera. Desea usar Outlier Detection para excluir automáticamente las instancias problemáticas. Escriba una DestinationRule que cumpla los siguientes requisitos:

**Requisitos:**

* Expulsar después de 3 errores consecutivos
* Realizar un barrido periódico cada 20 segundos; los fallos consecutivos pueden detectarse al producirse
* Establecer en 60 segundos la duración base inicial de la expulsión
* Permitir expulsar como máximo el 30% de las instancias
* Detectar también los errores de gateway 502, 503 y 504

<details>

<summary>Mostrar respuesta</summary>

Las respuestas lentas no cumplen por sí solas un criterio de Outlier Detection. El ejemplo distingue los errores HTTP de los fallos de transporte observados localmente; para observar tiempos de espera agotados debe existir un límite de tiempo real en la ruta o el cliente.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: product-service-outlier
  namespace: production
spec:
  host: product-service
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 3
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 3
      interval: 20s
      baseEjectionTime: 60s
      maxEjectionPercent: 30
      minHealthPercent: 0
      consecutiveGatewayErrors: 3
```

Los errores de gateway 502, 503 y 504 ya forman parte de los errores 5xx. Usar el mismo umbral de 3 para ambos grupos es redundante, aunque válido; un umbral menor para los errores de gateway permitiría expulsar antes por ese subconjunto. `interval: 20s` no retrasa la detección de errores consecutivos. `baseEjectionTime: 60s` fija la duración mínima inicial y no realiza una sonda activa de salud. El límite del 30% restringe las expulsiones, pero no mantiene sanos los endpoints restantes. `minHealthPercent: 70` activaría el modo de pánico al caer por debajo de ese umbral; no conservaría un 70% de capacidad sana. Los campos `enforcing*` no admitidos pertenecen a la configuración interna de Envoy, no a esta API de DestinationRule.

En un ejemplo con diez hosts, tres expulsiones pueden alcanzar el límite. También importan el tamaño del conjunto descubierto, el redondeo y su estado actual: inspeccione los contadores reales de expulsiones detectadas, aplicadas y bloqueadas por el límite. Un host reincorporado debe atender tráfico correctamente para demostrar que se ha recuperado.

```bash
istioctl proxy-config clusters <caller-pod> -n production --fqdn product-service.production.svc.cluster.local -o json
istioctl x envoy-stats <caller-pod> -n production --output prom | grep outlier_detection
```

```promql
envoy_cluster_outlier_detection_ejections_active{namespace="production"}
rate(envoy_cluster_outlier_detection_ejections_enforced_total{namespace="production"}[5m])
```

Habilite las estadísticas y su recopilación opcional como indica el [capítulo de Outlier Detection](../../../service-mesh/istio/resilience/01-outlier-detection.md). Ajuste los umbrales según los errores medidos y la capacidad disponible; no existe un valor universal adecuado para toda producción.

</details>

***

### Pregunta 7: Aplicación de Local Rate Limiting

Una aplicación llamada `api-gateway`, con un sidecar inyectado, recibe demasiado tráfico HTTP. Desea aplicar Local Rate Limiting para limitar cada proxy Envoy a 50 solicitudes por segundo, con una ráfaga de hasta 200 solicitudes. Escriba el EnvoyFilter.

Requisitos adicionales:

* Agregar el encabezado `X-RateLimit-Limit` cuando se aplique el límite de tasa
* Incluir el encabezado `Retry-After: 1` en las respuestas 429

<details>

<summary>Mostrar respuesta</summary>

Suponga que `api-gateway` es una aplicación con sidecar que atiende HTTP en el puerto 8080, en el namespace `production`. El filtro protege las solicitudes HTTP seleccionadas una vez que llegan a Envoy; no proporciona una protección completa contra DDoS ni protege por completo las conexiones o TLS. Para un gateway de entrada real de Istio, use su namespace, su selector y el contexto `GATEWAY`, como indica el capítulo de límites de tasa.

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: api-gateway-ratelimit
  namespace: production
spec:
  workloadSelector:
    labels:
      app: api-gateway
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        portNumber: 8080
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 200
            tokens_per_fill: 50
            fill_interval: 1s
          filter_enabled:
            default_value:
              numerator: 100
              denominator: HUNDRED
          filter_enforced:
            default_value:
              numerator: 100
              denominator: HUNDRED
          response_headers_to_add:
          - append_action: OVERWRITE_IF_EXISTS_OR_ADD
            header:
              key: X-RateLimit-Limit
              value: '50'
          - append_action: OVERWRITE_IF_EXISTS_OR_ADD
            header:
              key: X-Local-Rate-Limit
              value: 'true'
          - append_action: OVERWRITE_IF_EXISTS_OR_ADD
            header:
              key: Retry-After
              value: '1'
```

Un depósito lleno permite admitir hasta 200 solicitudes de inmediato y luego recibe 50 tokens por segundo. Si llegan 100 solicitudes por segundo de forma sostenida después de agotarlo, pueden admitirse unas 50 por segundo, suponiendo un token por solicitud y ningún otro límite. Una demanda uniforme de 40 solicitudes por segundo puede quedar dentro del límite, pero ese promedio no garantiza que se acepten todas las ráfagas. Admitir una solicitud tampoco garantiza que el backend la procese correctamente.

El filtro devuelve HTTP 429 de forma predeterminada y añade estos encabezados únicamente a las respuestas que genera al aplicar el límite de tasa. Esta configuración no añade esos encabezados a una respuesta normal con estado 200. `Retry-After: 1` recomienda esperar un segundo: no reserva capacidad ni garantiza que el siguiente intento tenga éxito. El ejemplo no crea los metadatos dinámicos `tokens_remaining`, por lo que se omite un encabezado Remaining que dependería de datos inexistentes.

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 50
X-Local-Rate-Limit: true
Retry-After: 1
```

Para asignar depósitos distintos según el prefijo de la ruta, use esta **alternativa** en lugar de añadir un segundo filtro superpuesto. La API de Envoy incluida en la versión indicada de Istio 1.31 admite el generador explícito de descriptores. Si la ruta falta o no coincide, se aplica el depósito predeterminado, que también tiene un límite. La coincidencia por prefijo incluye las rutas más largas que comiencen con el texto indicado.

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: path-based-ratelimit
  namespace: production
spec:
  workloadSelector:
    labels:
      app: api-gateway
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        portNumber: 8080
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 30
            tokens_per_fill: 10
            fill_interval: 1s
          filter_enabled:
            default_value:
              numerator: 100
              denominator: HUNDRED
          filter_enforced:
            default_value:
              numerator: 100
              denominator: HUNDRED
          always_consume_default_token_bucket: false
          descriptors:
          - entries:
            - key: header_match
              value: /api/login
            token_bucket:
              max_tokens: 30
              tokens_per_fill: 10
              fill_interval: 1s
          - entries:
            - key: header_match
              value: /api/search
            token_bucket:
              max_tokens: 300
              tokens_per_fill: 100
              fill_interval: 1s
          rate_limits:
          - actions:
            - header_value_match:
                descriptor_value: /api/login
                headers:
                - name: :path
                  string_match:
                    prefix: /api/login
          - actions:
            - header_value_match:
                descriptor_value: /api/search
                headers:
                - name: :path
                  string_match:
                    prefix: /api/search
```

```promql
sum by (pod) (rate({__name__=~"envoy_.*http_local_rate_limit_enforced",namespace="production"}[5m]))
```

Consulte el capítulo de [límites de tasa](../../../service-mesh/istio/resilience/02-rate-limiting.md) para conocer la recopilación de estadísticas opcionales, los requisitos del servicio global y Redis, y el tratamiento de identidades de confianza.

</details>

***

### Pregunta 8: Configuración de Zone Aware Routing

Su clúster de AWS EKS está distribuido en 3 AZ (us-east-1a, us-east-1b, us-east-1c). Desea configurar Zone Aware Routing para `order-service` a fin de reducir los costos de transferencia de datos entre AZ.

**Requisitos:**

* Enviar el 70% del tráfico a Pods de la misma AZ
* Distribuir el 15% a cada una de las otras AZ
* Explicar una alternativa independiente de conmutación por prioridad y las limitaciones de una caída completa de una AZ
* Explicar por qué minHealthPercent 50 no garantiza que el 50% de los Pods esté sano ni activa el enrutamiento por localidad

<details>

<summary>Mostrar respuesta</summary>

Estos requisitos combinan una distribución ponderada, una conmutación por prioridad y una garantía de capacidad sana. No pueden implementarse todos mezclando campos en una única política de localidad. Use la siguiente política para distribuir el tráfico normal en proporción 70/15/15; `minHealthPercent` no activa la localidad solo cuando la mitad de los Pods está sana.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: order-service-locality
  namespace: production
spec:
  host: order-service
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            us-east-1/us-east-1a/*: 70
            us-east-1/us-east-1b/*: 15
            us-east-1/us-east-1c/*: 15
        - from: us-east-1/us-east-1b/*
          to:
            us-east-1/us-east-1a/*: 15
            us-east-1/us-east-1b/*: 70
            us-east-1/us-east-1c/*: 15
        - from: us-east-1/us-east-1c/*
          to:
            us-east-1/us-east-1a/*: 15
            us-east-1/us-east-1b/*: 15
            us-east-1/us-east-1c/*: 70
    outlierDetection:
      consecutive5xxErrors: 5
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 0
```

Si desea dar prioridad a la zona local y derivar el tráfico que no pueda atender, aplique esta **alternativa** en lugar de usar ambas políticas. `localityLbSetting.failover` acepta nombres de región, no rutas `region/zone`. En esta API, `distribute` y los modos de prioridad son mutuamente excluyentes.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: order-service-failover
  namespace: production
spec:
  host: order-service
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        failoverPriority:
        - topology.kubernetes.io/region
        - topology.kubernetes.io/zone
    outlierDetection:
      consecutive5xxErrors: 5
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

La caída completa de una zona también afecta a los clientes que están en ella: se necesita un cliente o punto de entrada que sobreviva, o que se vuelva a crear, en otra zona. La capacidad de los endpoints sanos restantes, la detección, la reutilización de conexiones y la conectividad de red determinan la conmutación. La política no garantiza enviar el 100% a zoneB ni recuperarse de inmediato. `minHealthPercent: 0` deshabilita el uso de hosts no sanos en modo de pánico, y un límite del 100% permite expulsar todos los endpoints si todos fallan. Ninguno de estos valores crea capacidad sana.

Consulte el [capítulo de enrutamiento por zona](../../../service-mesh/istio/resilience/03-zone-aware-routing.md) para comprobar la topología Node→Pod, las topologySpreadConstraints correspondientes, los grupos de nodos de EKS y los diagnósticos de EDS. No asigne manualmente etiquetas de topología de la nube solo para que el ejemplo coincida. Las métricas estándar de Istio no contienen `source_cluster_zone`/`destination_cluster_zone`; las consultas por zona requieren un enriquecimiento verificado, independiente del enrutamiento.

**Ejemplo de cálculo de costos**: suponga que 1 TB decimal equivale a 1000 GB, que el cargo efectivo es de $0.01 por GB facturable y que la fracción del tráfico entre zonas pasa de 2/3 a 0.30. Son supuestos simplificados; no constituyen una tarifa de AWS, un ahorro medido ni una factura de red completa.

| Tráfico mensual | Antes | Después | Ahorro mensual | Ahorro anual |
|---|---:|---:|---:|---:|
|1TB|$6.67|$3.00|$3.67|$44.00|
|100TB|$666.67|$300.00|$366.67|$4,400.00|

La reducción calculada es del 55%. Use las fracciones exactas y redondee únicamente los importes mostrados: no calcule el ahorro anual multiplicando un ahorro mensual redondeado antes de tiempo a $367. Para conocer las direcciones facturables, los volúmenes de bytes, la región y los cargos de procesamiento de los servicios, necesita datos de facturación y de flujo.

```bash
kubectl get nodes -L topology.kubernetes.io/region,topology.kubernetes.io/zone
istioctl proxy-config bootstrap <caller-pod> -n production -o json
istioctl proxy-config all <caller-pod> -n production -o json
```

</details>

***

### Pregunta 9: Estrategia de resiliencia combinada

El servicio `payment-service` es crítico y llama a API de pago externas. Implemente la siguiente estrategia combinada de resiliencia:

1. **Outlier Detection**: Expulsar la instancia después de 3 errores consecutivos
2. **Retry**: Permitir hasta 3 reintentos ante errores 502, 503 o 504 para lecturas cuya idempotencia se haya verificado; deshabilitar explícitamente los reintentos de escritura
3. **Timeout**: Establecer un tiempo de espera de 5 segundos por solicitud
4. **Circuit Breaker**: Explicar por qué «bloquear todo el servicio cuando los errores superen el 50%» no corresponde al circuit breaker del pool de esta API y mostrar los límites de concurrencia admitidos

Escriba el DestinationRule y el VirtualService.

<details>

<summary>Mostrar respuesta</summary>

Una DestinationRule no puede «bloquear globalmente este servicio cuando los errores superen el 50%» mediante los campos de tasa de éxito enumerados. Esos campos no se admiten aquí, y la desviación estadística no equivale a un umbral fijo de porcentaje de errores. Los circuit breakers del pool limitan las conexiones y solicitudes simultáneas del clúster upstream de cada proxy que realiza las llamadas; Outlier Detection determina qué hosts pueden recibir tráfico. Un circuit breaker coordinado para todo el servicio, basado en la proporción de errores, requiere un mecanismo de aplicación o controlador diseñado por separado.

Esta respuesta se aplica a **caller→payment-service HTTP8080**. La llamada que el servicio realiza a la API de pago externa necesita su propia política de destino y visibilidad TLS, como explica el [capítulo de Outlier Detection](../../../service-mesh/istio/resilience/01-outlier-detection.md). Los reintentos de la malla no proporcionan idempotencia de pagos.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: payment-service-resilience
  namespace: production
spec:
  host: payment-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 1s
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 0
        maxRetries: 3
    outlierDetection:
      consecutive5xxErrors: 3
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 3
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 0
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: payment-service-retry
  namespace: production
spec:
  hosts:
  - payment-service
  http:
  - name: writes-no-retry
    match:
    - method:
        regex: ^(POST|PUT|PATCH|DELETE)$
    route:
    - destination:
        host: payment-service
        port:
          number: 8080
    timeout: 5s
    retries:
      attempts: 0
  - name: idempotent-reads
    match:
    - method:
        regex: ^(GET|HEAD|OPTIONS)$
    route:
    - destination:
        host: payment-service
        port:
          number: 8080
    timeout: 5s
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: gateway-error,connect-failure,refused-stream
  - name: other-methods-no-retry
    route:
    - destination:
        host: payment-service
        port:
          number: 8080
    timeout: 5s
    retries:
      attempts: 0
```

Las reglas explícitas de escritura y de último recurso deshabilitan los reintentos heredados de la malla. Reintente únicamente las lecturas que coincidan y cuya semántica permita repetirlas de forma segura. `gateway-error` cubre los errores 502, 503 y 504; no se añaden condiciones amplias de restablecimiento de conexión ni de errores 5xx o 4xx a las escrituras de pago. Un error de transporte no permite saber si el pago se confirmó.

`attempts: 3` permite hasta tres reintentos **después** del intento inicial. Cuatro intentos completos de 2 segundos, más las esperas entre reintentos, no caben en 5 segundos; el límite total de la ruta los interrumpe antes. Los plazos de la aplicación también deben cubrir la carga de datos, la transmisión y el trabajo de los servicios posteriores. El ejemplo no describe una secuencia exacta de fallos ni garantiza un estado HTTP final concreto.

`maxRetries: 3` limita los reintentos simultáneos pendientes de ese proxy y clúster, no el número de reintentos por solicitud. `http2MaxRequests` también se aplica a HTTP/1.1. `maxRequestsPerConnection: 0` permite reutilizar la conexión sin ese límite de solicitudes. Superar el límite de solicitudes pendientes o activas puede provocar el rechazo de solicitudes HTTP; alcanzar el límite de conexiones puede primero hacer que se encolen. Ninguno de estos valores implementa un circuit breaker global que se active al superar el 50% de errores.

| Observación | Interpretación correcta |
| --- | --- |
| Una lectura segura recibe 502 y luego tiene éxito al reintentarse | El reintento puede ayudar, pero puede dirigirse al mismo host y no garantiza el éxito |
| Un host alcanza su umbral de fallos | El proxy que realiza la llamada puede expulsarlo si el límite lo permite; los demás proxies mantienen su propio estado |
| Fallan todos los endpoints | Puede no quedar ningún destino sano; el temporizador de expulsión no repara el servicio ni implementa una prueba coordinada del estado semiabierto |

```promql
sum(rate(envoy_cluster_upstream_rq_retry{namespace="production"}[5m]))
envoy_cluster_circuit_breakers_default_rq_pending_open{namespace="production"}
sum(rate(envoy_cluster_outlier_detection_ejections_enforced_total{namespace="production"}[5m]))
sum(rate(istio_requests_total{reporter="source",destination_service_name="payment-service",destination_service_namespace="production",response_flags=~".*UT.*"}[5m]))
```

La serie `_open` es una métrica gauge con valores 0 o 1, no un contador al que se deba aplicar `rate`. Delimite las etiquetas de los clústeres de Envoy y habilite las estadísticas correspondientes. Consulte los capítulos de [reintentos y tiempos de espera](../../../service-mesh/istio/traffic-management/05-retry-timeout.md) y [circuit breakers](../../../service-mesh/istio/traffic-management/07-circuit-breaker.md) para evaluar sus efectos operativos.

</details>

***

### Pregunta 10: Optimización de rendimiento y reducción de costos

En un entorno de microservicios a gran escala, los costos mensuales de red ascienden a $5,000. Diseñe una estrategia integral para mejorar el rendimiento y reducir los costos mediante las funciones de resiliencia de Istio.

**Situación actual:**

* 100 servicios distribuidos uniformemente en 3 AZ
* Tráfico mensual: 500 TB
* Tiempo de respuesta medio: 150 ms
* Tasa de errores: 3%

**Objetivos:**

* Reducir el 50% de los costos entre AZ
* Alcanzar un tiempo de respuesta medio inferior a 100 ms
* Mantener la tasa de errores por debajo del 1%

<details>

<summary>Mostrar respuesta</summary>

Considere los 100 servicios, los 500 TB al mes, la factura de $5,000, los 150 ms de latencia y el 3% de errores como una **situación inicial hipotética**; no son resultados medidos en esta revisión. Primero identifique los componentes de tráfico facturables y el alcance del SLI que refleja la experiencia del usuario. La latencia de un salto entre proxies no equivale automáticamente a la latencia de extremo a extremo de la solicitud.

**1. Consolidar una política de destino por servicio revisado**

El ejemplo de `api-service` combina límites del pool, ponderaciones por localidad y Outlier Detection admitido en una única DestinationRule. Evite aplicar varias reglas con comodines que compitan entre sí o dirigir todos los servicios a un backend genérico. Dimensione los valores para cada cliente y destino; el ejemplo no ofrece valores predeterminados para producción.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-service-resilience
  namespace: production
spec:
  host: api-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 1s
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 0
        maxRetries: 3
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            us-east-1/us-east-1a/*: 80
            us-east-1/us-east-1b/*: 10
            us-east-1/us-east-1c/*: 10
        - from: us-east-1/us-east-1b/*
          to:
            us-east-1/us-east-1a/*: 10
            us-east-1/us-east-1b/*: 80
            us-east-1/us-east-1c/*: 10
        - from: us-east-1/us-east-1c/*
          to:
            us-east-1/us-east-1a/*: 10
            us-east-1/us-east-1b/*: 10
            us-east-1/us-east-1c/*: 80
    outlierDetection:
      consecutive5xxErrors: 3
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 3
      interval: 10s
      baseEjectionTime: 60s
      maxEjectionPercent: 30
      minHealthPercent: 0
      consecutiveGatewayErrors: 2
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-service-routing
  namespace: production
spec:
  hosts:
  - api-service
  http:
  - name: writes-no-retry
    match:
    - method:
        regex: ^(POST|PUT|PATCH|DELETE)$
    route:
    - destination:
        host: api-service
        port:
          number: 8080
    timeout: 3s
    retries:
      attempts: 0
  - name: idempotent-reads
    match:
    - method:
        regex: ^(GET|HEAD|OPTIONS)$
    route:
    - destination:
        host: api-service
        port:
          number: 8080
    timeout: 3s
    retries:
      attempts: 2
      perTryTimeout: 1s
      retryOn: gateway-error,connect-failure,refused-stream
  - name: other-methods-no-retry
    route:
    - destination:
        host: api-service
        port:
          number: 8080
    timeout: 3s
    retries:
      attempts: 0
```

**2. Límites de tasa como controles de admisión medidos**

Los depósitos son independientes por proxy y se aplican al tráfico HTTP del puerto 8080 en `production`. Verifique las etiquetas de nivel y la capacidad: una etiqueta «critical» no justifica por sí sola una tasa concreta. Estos límites no imponen una cuota compartida por servicio o cuenta ni sustituyen la protección del perímetro.

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: critical-service-ratelimit
  namespace: production
spec:
  workloadSelector:
    labels:
      tier: critical
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        portNumber: 8080
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 500
            tokens_per_fill: 100
            fill_interval: 1s
          filter_enabled:
            default_value:
              numerator: 100
              denominator: HUNDRED
          filter_enforced:
            default_value:
              numerator: 100
              denominator: HUNDRED
---
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: standard-service-ratelimit
  namespace: production
spec:
  workloadSelector:
    labels:
      tier: standard
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        portNumber: 8080
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 200
            tokens_per_fill: 50
            fill_interval: 1s
          filter_enabled:
            default_value:
              numerator: 100
              denominator: HUNDRED
          filter_enforced:
            default_value:
              numerator: 100
              denominator: HUNDRED
```

**3. Separar un modelo ilustrativo de una factura real**

Suponga que 500 TB decimales equivalen a 500,000 GB, que la fracción del tráfico entre AZ pasa de 2/3 a 0.20 y que el **cargo efectivo supuesto** es de $0.015 por GB facturable. El componente variable calculado es:

| Modelo | Cálculo | Importe mensual |
|---|---|---:|
|Antes|500,000 × 2/3 × 0.015|$5,000|
|Después|500,000 × 0.20 × 0.015|$1,500|
|Diferencia|5,000 − 1,500|$3,500 (70%)|

El cálculo coincide con la factura inicial completa de $5,000 solo si toda la factura corresponde a ese componente variable. Una factura de red real puede incluir otras direcciones de tráfico, procesamiento de balanceadores de carga y NAT, transferencias hacia Internet o entre regiones y costos fijos. Las proporciones de solicitudes no tienen por qué coincidir con las de bytes si varían los tamaños de las solicitudes y respuestas. Compare el ahorro calculado con los datos facturables de flujo o CUR y con los precios vigentes; no prometa una reducción del 70% en la factura total.

Si se suponen latencias de un salto de 0.3 ms dentro de la misma AZ y de 1.5 ms entre AZ, una distribución uniforme entre tres zonas da 0.3×1/3+1.5×2/3=1.10 ms; una distribución 80/20 da 0.54 ms. Esta reducción de 0.56 ms en un componente no demuestra una mejora de extremo a extremo de 150 ms a 100 ms. Rastree la ruta crítica real, las esperas de bases de datos y pools, el trabajo de la aplicación y el tráfico adicional causado por los reintentos.

**4. Validar cambios por etapas**

| Etapa de ejemplo | Evidencia necesaria antes de ampliar el alcance |
| --- | --- |
| Semanas 1–2: topología y localidad | Correspondencia real entre Node, Pod y EDS, capacidad por zona, distribución de solicitudes y bytes facturables, comportamiento ante fallos |
| Semanas 3–4: límites de Outlier Detection y del pool | Expulsiones aplicadas, endpoints restantes, límites superados, latencia y causas de los errores de la aplicación |
| Semanas 5–6: límites de tasa | Rechazo de la sobrecarga real sin rechazar una cantidad inaceptable de solicitudes legítimas; observación de los reintentos de los clientes |

El calendario sirve de ejemplo. Defina cuándo detener los cambios o revertirlos y mida el resultado después de cada modificación. Outlier Detection puede reducir la capacidad o revelar un fallo existente; no garantiza una tasa de errores inferior al 1%. Cambiar un tiempo de espera puede generar más fallos en lugar de acelerar el trabajo.

**5. Usar métricas con tipo y ámbito correctos**

Las siguientes consultas por servicio permiten diagnosticar el servicio del ejemplo. Mida por separado el SLI que refleja la experiencia del usuario. La latencia media se calcula a partir de la suma y el recuento del histograma, no del P50. Las expulsiones activas se representan con una métrica gauge; los eventos de expulsión aplicada, con un contador.

```promql
# Per-service mean request duration, milliseconds
sum(rate(istio_request_duration_milliseconds_sum{reporter="destination",destination_service_name="api-service",destination_service_namespace="production"}[5m])) /
sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_service_name="api-service",destination_service_namespace="production"}[5m]))

# Per-service HTTP5xx percentage (define gRPC/application failures separately)
100 * sum(rate(istio_requests_total{reporter="destination",destination_service_name="api-service",destination_service_namespace="production",response_code=~"5.."}[5m])) /
sum(rate(istio_requests_total{reporter="destination",destination_service_name="api-service",destination_service_namespace="production"}[5m]))

envoy_cluster_outlier_detection_ejections_active{namespace="production"}
sum(rate(envoy_cluster_outlier_detection_ejections_enforced_total{namespace="production"}[5m]))
sum by (pod) (rate({__name__=~"envoy_.*http_local_rate_limit_enforced",namespace="production"}[5m]))
```

Habilite las estadísticas opcionales y gestione la ausencia de tráfico y los fallos de recopilación. Una consulta entre AZ requiere un enriquecimiento real con datos de zona; `source_cluster_zone!=destination_cluster_zone` no es PromQL válido. Consulte el [capítulo de enrutamiento por zona](../../../service-mesh/istio/resilience/03-zone-aware-routing.md) para conocer las consultas condicionales con alcance explícito.

**Todavía debe comprobarse el cumplimiento de los objetivos**: reducir un 50% el costo entre AZ, mantener la latencia media percibida por el usuario en 100 ms o menos y los errores por debajo del 1% son criterios de aceptación, no resultados previstos. La ubicación de la caché puede reducir la distancia, pero no aumenta por sí sola su tasa de aciertos. Evalúe los requisitos de funciones y capacidad de ambient antes de comparar su sobrecarga; no se ha demostrado un ahorro general del 30–50%. Un HPA que controla un Deployment distribuido entre zonas no escala cada zona de forma independiente; para hacerlo se necesita un diseño explícito de las cargas de trabajo y sus controladores.

Referencias: [Outlier Detection](../../../service-mesh/istio/resilience/01-outlier-detection.md), [límites de tasa](../../../service-mesh/istio/resilience/02-rate-limiting.md) y [optimización de costos de red de EKS](https://docs.aws.amazon.com/eks/latest/best-practices/cost-opt-networking.html).

</details>

***

## Cálculo de puntuación

* Opción múltiple 1-5: 10 puntos cada una (50 puntos en total)
* Respuesta corta 6-10: 10 puntos cada una (50 puntos en total)
* **Total: 100 puntos**

**Criterios de evaluación:**

* 90-100 puntos: Excelente; dominio de la resiliencia de Istio
* 80-89 puntos: Buena comprensión; la validación del despliegue requiere una evaluación independiente
* 70-79 puntos: Nivel medio; se recomienda seguir estudiando
* 60-69 puntos: Nivel inferior al esperado; repase los conceptos básicos
* 0-59 puntos: Es necesario volver a estudiar el material

## Recursos de aprendizaje

* [Outlier Detection](../../../service-mesh/istio/resilience/01-outlier-detection.md)
* [Rate Limiting](../../../service-mesh/istio/resilience/02-rate-limiting.md)
* [Zone Aware Routing](../../../service-mesh/istio/resilience/03-zone-aware-routing.md)
