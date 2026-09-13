# Cuestionario de resiliencia

> **Última actualización**: 11 de septiembre de 2026 · Istio1.31 · Kubernetes1.32–1.36; consulte la instalación para compatibilidad EKS.

Este cuestionario evalúa las funciones de resiliencia de Istio.

Cada ejemplo es independiente y supone Services, etiquetas, namespaces y cargas sidecar HTTP8080 existentes. Los valores son ilustrativos; validar esquemas/consultas offline no es probar producción/carga. Los ejemplos usan `localityLbSetting`, no la API separada `zoneAwareLbSetting`.

## Preguntas de opción múltiple (1-5)

### Pregunta 1: Conceptos de detección de valores atípicos

¿Cuál **NO** es un objetivo principal?

A. Detectar instancias anómalas automáticamente\
B. Excluir temporalmente cuando umbral y límite lo permitan\
C. Eliminar permanentemente las instancias retiradas\
D. Volver a habilitar un host al terminar la exclusión

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C**

La detección **no elimina instancias**; las retira temporalmente del grupo de tráfico.

**Explicación:**

**Funcionamiento:**


**Funciones principales:**

1. **Detección automática**: Cuenta fallos HTTP/transporte consecutivos configurados y pertinentes
2. **Exclusión automática**: Retira temporalmente al superar el umbral
3. **Reincorporación**: Expira la exclusión; no envía una sonda ni demuestra recuperación
4. **Medida temporal**: Solo bloquea tráfico, sin borrar instancias

**Por qué C es incorrecta:**

* Es un patrón de circuit breaker
* **Excluye temporalmente** sin eliminar
* El tráfico posterior exitoso confirma recuperación; fallos repetidos pueden alargar exclusiones

**Referencia:**

* [Detección de valores atípicos](../../../service-mesh/istio/resilience/01-outlier-detection.md)

</details>

***

### Pregunta 2: Tipos de limitación de tasa

¿Qué comparación de limitación local y global es correcta?

A. La limitación de tasa local tiene mayor precisión\
B. La limitación de tasa global ofrece mayor velocidad\
C. La limitación de tasa local limita las solicitudes de forma independiente en cada proxy Envoy\
D. La limitación de tasa global funciona sin servicios externos

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C**

La limitación local actúa **independientemente en cada proxy Envoy**.

**Explicación:**

**Comparación:**

| Característica | Local | Global |
| --------------- | ------------------- | -------------------------------- |
| **Ámbito de cuota** | Bucket local configurado | Domain/descriptor y ventana compartidos |
| **Rendimiento** | Muy rápido | Algo más lento |
| **Complejidad** | Baja | Alta, necesita servicio externo |
| **Uso** | Protección general | Limitación precisa |

**Características locales:**

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

El bucket empieza con 100 tokens y repone 10/s. Tres réplicas pueden sostener aproximadamente 30/s con reparto adecuado y ráfagas separadas; no es un máximo compartido de 30/s.

**Características globales:**

```yaml
# Configured shared descriptor quota:100 per backend second-window
# Actual enforcement depends on the shared backend, window and failure policy
# Requires an actual gRPC rate-limit service plus shared counter storage such as Redis
```

**Algoritmo token bucket:**

![Flujo de trabajo de un limitador de tasa con depósito de tokens: un depósito limitado a 100 tokens se repone a 10 tokens por segundo, y cada solicitud entrante se permite consumiendo un token o se rechaza con HTTP 429 cuando no queda ninguno.](../../../.gitbook/assets/en-quizzes-service-mesh-istio-resilience-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-quizzes-service-mesh-istio-resilience-1.html)

**Referencia:**

* [Limitación de tasa](../../../service-mesh/istio/resilience/02-rate-limiting.md)

</details>

***

### Pregunta 3: Beneficios del enrutamiento por zona

¿Cuál **NO** es un beneficio?

A. Menor latencia mediante la misma AZ\
B. Ahorro de transferencia entre AZ\
C. Disponibilidad garantizada poniendo todas las réplicas en una AZ\
D. Failover a endpoints sanos accesibles con política y capacidad adecuadas

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C**

C no es una garantía. La localidad es relativa al caller y puede concentrar su tráfico local. Mover todas las réplicas a una AZ comparte el dominio de fallo y puede sobrecargarla.

**Explicación:**

**Comportamiento correcto:**


**Beneficios reales:**

La misma zona puede reducir componente de red y bytes facturables, pero latencias/precios/ahorros dependen del despliegue. 80/10/10 envía tráfico normal a las tres zonas sanas; las porciones 10% no son reserva de failover. Otras zonas necesitan endpoints accesibles y capacidad libre.

**Ejemplo DestinationRule:**

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

* [Enrutamiento por zona](../../../service-mesh/istio/resilience/03-zone-aware-routing.md)

</details>

***

### Pregunta 4: Parámetros de detección

¿Bajo qué condición se excluye una instancia con esta configuración?

```yaml
outlierDetection:
  consecutive5xxErrors: 5
  interval: 30s
  baseEjectionTime: 30s
  maxEjectionPercent: 50
```

A. Tras errores durante 5 segundos\
B. Tras 5 fallos 5xx consecutivos pertinentes, sujeto al límite de exclusión\
C. Al superar 50% de errores durante 30 segundos\
D. Incondicionalmente cada 30 segundos

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B**

B identifica el disparador. Cinco fallos pertinentes pueden excluir inmediatamente; `interval` es el barrido periódico y `maxEjectionPercent` puede impedir la aplicación. Una respuesta lenta exitosa no es un valor atípico de latencia por sí sola.

**Explicación:**

**Parámetros principales:**

| Parámetro | Descripción | Predeterminado | Rango de ejemplo |
| ---------------------- | --------------------------- | ------- | ----------- |
| **consecutive5xxErrors** | Umbral de errores consecutivos | 5 | 3-10 |
| **interval** | Intervalo de análisis | 10s | 10s-60s |
| **baseEjectionTime** | Tiempo mínimo de exclusión | 30s | 30s-300s |
| **maxEjectionPercent** | Proporción máxima excluida | 10% | 10%-50% |

**Detalle de parámetros:**

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

**DestinationRule completo:**

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

**Ejemplo de operación:**

Un éxito reinicia la secuencia correspondiente. Al alcanzar el umbral se excluye si el máximo lo permite; el host vuelve a ser elegible tras su duración real. Repeticiones aumentan duración con multiplicador/límite Envoy. `minHealthPercent` es umbral panic/fail-open, no fracción garantizada de Pods sanos; 0 lo desactiva.

**Referencia:**

* [Detección de valores atípicos](../../../service-mesh/istio/resilience/01-outlier-detection.md)

</details>

***

### Pregunta 5: Token bucket

Con un token por solicitud y demanda sostenida, ¿cuál es la tasa a largo plazo limitada por reposición tras la ráfaga inicial?

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

Con `tokens_per_fill: 10` y `fill_interval: 1s`, se **añaden 10 tokens por segundo**, por lo que la media es **10 req/s**.

**Explicación:**

**Parámetros:**

* **max\_tokens**: Tokens máximos almacenados, que permiten ráfagas
* **tokens\_per\_fill**: Tokens añadidos por fill\_interval (**rendimiento medio**)
* **fill\_interval**: Intervalo de reposición

**Cálculo:**

```
Average request rate = tokens_per_fill / fill_interval
                     = 10 / 1s
                     = 10 req/s

Burst throughput = max_tokens
                 = 100 req (for a brief moment)
```

**Comportamiento temporal:**

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

**Configuraciones prácticas:**

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

**EnvoyFilter completo:**

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

* [Limitación de tasa](../../../service-mesh/istio/resilience/02-rate-limiting.md)

</details>

***

## Preguntas breves (6-10)

### Pregunta 6: Implementar detección de valores atípicos

Un `product-service` que se ejecuta en producción se ralentiza intermitentemente y experimenta tiempos de espera agotados. Quiere implementar detección de valores atípicos para expulsar automáticamente las instancias problemáticas. Escriba un DestinationRule que cumpla los siguientes requisitos:

**Requisitos:**

* Excluir tras 3 errores consecutivos
* Barrido periódico de 20 segundos; detección consecutiva inmediata
* Duración base inicial de 60 segundos
* Máximo de exclusión 30%
* Detectar también errores 502, 503 y 504

<details>

<summary>Mostrar respuesta</summary>

La lentitud sola no es criterio de outlier. El ejemplo separa HTTP de fallos de transporte locales; debe existir un timeout real de ruta/cliente para observarlos.

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

502/503/504 ya están dentro de 5xx. Umbrales iguales de 3 son redundantes pero válidos; uno menor para gateway excluye antes por ese subconjunto. `interval: 20s` no demora detección consecutiva. `baseEjectionTime: 60s` es mínimo inicial, no sonda activa. El máximo 30% limita exclusiones, pero no mantiene sanos los demás. `minHealthPercent: 70` activa pánico bajo el umbral, no conserva 70% de capacidad saludable. `enforcing*` son campos internos Envoy no soportados por esta API.

Diez hosts pueden alcanzar el límite tras tres exclusiones, pero importan tamaño descubierto, redondeo y salud. Inspeccione contadores enforced/detected/overflow reales. Un host que vuelve necesita tráfico exitoso para demostrar recuperación.

```bash
istioctl proxy-config clusters <caller-pod> -n production --fqdn product-service.production.svc.cluster.local -o json
istioctl x envoy-stats <caller-pod> -n production --output prom | grep outlier_detection
```

```promql
envoy_cluster_outlier_detection_ejections_active{namespace="production"}
rate(envoy_cluster_outlier_detection_ejections_enforced_total{namespace="production"}[5m])
```

Active estadísticas/scrape según el [capítulo de outliers](../../../service-mesh/istio/resilience/01-outlier-detection.md). Ajuste con errores medidos y reserva; no hay un valor universal de producción.

</details>

***

### Pregunta 7: Aplicar limitación local

Una aplicación llamada `api-gateway` con un sidecar inyectado recibe tráfico HTTP excesivo. Quiere aplicar limitación de tasa local para limitar cada proxy Envoy a 50 solicitudes por segundo con ráfagas de hasta 200. Escriba el EnvoyFilter.

Requisitos adicionales:

* Añadir `X-RateLimit-Limit` al aplicar la limitación
* Incluir `Retry-After: 1` en respuestas 429

<details>

<summary>Mostrar respuesta</summary>

Suponga `api-gateway` con sidecar HTTP8080 en `production`. Protege solicitudes seleccionadas después de llegar a Envoy; no es protección completa DDoS/conexiones/TLS. Para un ingress gateway real use su namespace/selector y contexto `GATEWAY` como en la guía.

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

Un bucket lleno admite 200 inmediatamente y repone 50 tokens/s. Con demanda sostenida de 100/s después de vaciarse, puede admitir aproximadamente 50/s, suponiendo un token y sin otros límites. Demanda uniforme de 40/s cabe, pero una media de 40/s no garantiza aceptar toda ráfaga. Admitir no garantiza procesamiento exitoso del backend.

El filtro utiliza HTTP429 de forma predeterminada y añade estas cabeceras solo a las respuestas en las que aplica la limitación de tasa. Una respuesta normal 200 no recibe estas cabeceras de esta configuración. `Retry-After: 1` es un retraso orientativo, no una reserva ni una garantía de éxito un segundo después. Este ejemplo no crea metadatos dinámicos `tokens_remaining`, por lo que se omite una cabecera Remaining inventada.

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 50
X-Local-Rate-Limit: true
Retry-After: 1
```

Para buckets por prefijo use esta **alternativa**, no un filtro superpuesto. El generador explícito de descriptors está soportado por Envoy fijado en Istio1.31. Rutas ausentes/no coincidentes usan el bucket predeterminado limitado; el prefijo también coincide con rutas más largas que comiencen igual.

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

Consulte [limitación de tasa](../../../service-mesh/istio/resilience/02-rate-limiting.md) para estadísticas opcionales, servicio global/Redis e identidad fiable.

</details>

***

### Pregunta 8: Enrutamiento por zona

Un EKS ocupa 3 AZ (us-east-1a, us-east-1b, us-east-1c). Configure `order-service` para reducir transferencia entre AZ.

**Requisitos:**

* Enviar 70% a Pods de la misma AZ
* Repartir 15% a cada otra AZ
* Explicar alternativa de failover prioritario y límites de caída completa de AZ
* Explicar por qué minHealthPercent50 no garantiza 50% saludable ni activa localidad

<details>

<summary>Mostrar respuesta</summary>

Estos requisitos mezclan distribución ponderada, conmutación por prioridades y una garantía de capacidad sana. No pueden expresarse todos combinando campos en una política de localidad. Utilice la siguiente política de distribución para tráfico normal 70/15/15; `minHealthPercent` no es un interruptor que activa la localidad solo cuando la mitad de los Pods están sanos.

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

Para prioridad local con desbordamiento, use esta **alternativa**, no ambas. `localityLbSetting.failover` acepta regiones, no rutas `region/zone`. `distribute` y modos prioritarios son excluyentes.

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

La caída de zona afecta también al cliente: se necesita uno superviviente/recreado o una entrada en otro lugar. Capacidad sana restante, detección, reutilización y conectividad determinan failover; no promete 100% a zoneB ni recuperación instantánea. `minHealthPercent: 0` desactiva usar hosts enfermos por pánico; un máximo 100% permite excluir todos si fallan. Ninguno crea capacidad sana.

Consulte el [capítulo de zonas](../../../service-mesh/istio/resilience/03-zone-aware-routing.md) para topología Node→Pod, topologySpreadConstraints, grupos EKS y EDS. No asigne etiquetas cloud manualmente solo para que encaje el ejemplo. Las métricas estándar no contienen `source_cluster_zone`/`destination_cluster_zone`; necesitan enriquecimiento validado separado del routing.

**Aritmética ilustrativa de costes**: suponga 1TB decimal=1000GB, tarifa efectiva $0.01 por GB facturable, fracción inicial 2/3 y final 0.30. Es una simplificación, no precio AWS, ahorro medido ni factura completa.

| Tráfico mensual | Antes | Después | Ahorro mensual | Ahorro anual |
|---|---:|---:|---:|---:|
|1TB|$6.67|$3.00|$3.67|$44.00|
|100TB|$666.67|$300.00|$366.67|$4,400.00|

La reducción modelada es 55%. Calcule con fracciones exactas y redondee solo la moneda mostrada; no multiplique un mensual prematuramente redondeado a $367. Direcciones facturables, bytes, región y procesamiento necesitan evidencia de flujos/facturas.

```bash
kubectl get nodes -L topology.kubernetes.io/region,topology.kubernetes.io/zone
istioctl proxy-config bootstrap <caller-pod> -n production -o json
istioctl proxy-config all <caller-pod> -n production -o json
```

</details>

***

### Pregunta 9: Estrategia combinada

`payment-service` es crítico y llama API externas de pago. Implemente:

1. **Outlier Detection**: Excluir tras 3 errores consecutivos
2. **Retry**: Hasta 3 reintentos de 502/503/504 en lecturas verificadas idempotentes; desactivar explícitamente escrituras
3. **Timeout**: 5 segundos por solicitud
4. **Circuit Breaker**: Explicar por qué «bloquear todo el servicio sobre 50% de errores» no es el breaker de pool de esta API; mostrar límites de concurrencia soportados

Escriba DestinationRule y VirtualService.

<details>

<summary>Mostrar respuesta</summary>

DestinationRule no implementa ese bloqueo global mediante los campos de éxito indicados: no están soportados aquí y desviación estadística no es umbral fijo de error. Los breakers limitan conexiones/solicitudes concurrentes por clúster upstream del proxy caller; outlier cambia elegibilidad de hosts. Un breaker coordinado por ratio global requiere otro mecanismo de aplicación/controlador diseñado aparte.

Se aplica a **caller→payment-service HTTP8080**. La llamada externa saliente requiere su propia política y visibilidad TLS según el [capítulo de outliers](../../../service-mesh/istio/resilience/01-outlier-detection.md). Los reintentos mesh no proporcionan idempotencia de pagos.

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

Las reglas write/fallback desactivan reintentos heredados. Reintente solo lecturas coincidentes seguras. `gateway-error` cubre 502/503/504; no se añaden condiciones amplias reset/5xx/4xx a pagos escritos. Un error de transporte no determina si el pago se confirmó.

`attempts: 3` permite tres reintentos **después** del inicial. Cuatro intentos completos de 2s más backoff no caben en 5s, así que el presupuesto total detiene antes. Los plazos de aplicación deben cubrir subida/streaming y trabajo posterior. No es una cronología exacta ni promesa de un estado HTTP final concreto.

`maxRetries: 3` limita reintentos pendientes concurrentes del proxy/clúster, no por solicitud. `http2MaxRequests` también afecta HTTP/1.1. `maxRequestsPerConnection: 0` permite reutilizar sin ese máximo. Desbordar solicitudes pendientes/activas puede rechazarlas; alcanzar el límite de conexiones puede primero generar cola. Ninguno es un circuito global por 50% de errores.

| Observación | Interpretación |
|---|---|
|Lectura segura recibe 502 y luego éxito|Reintentar puede ayudar, puede volver al mismo host y no garantiza éxito|
|Host alcanza el umbral|Ese caller puede excluirlo si el límite lo permite; otros mantienen su estado|
|Todos fallan|Puede no quedar destino sano; el temporizador no repara ni realiza una prueba half-open coordinada|

```promql
sum(rate(envoy_cluster_upstream_rq_retry{namespace="production"}[5m]))
envoy_cluster_circuit_breakers_default_rq_pending_open{namespace="production"}
sum(rate(envoy_cluster_outlier_detection_ejections_enforced_total{namespace="production"}[5m]))
sum(rate(istio_requests_total{reporter="source",destination_service_name="payment-service",destination_service_namespace="production",response_flags=~".*UT.*"}[5m]))
```

`_open` es gauge 0/1, no contador para `rate`. Limite etiquetas de clúster Envoy y active estadísticas. Consulte [retry/timeout](../../../service-mesh/istio/traffic-management/05-retry-timeout.md) y [circuit breaking](../../../service-mesh/istio/traffic-management/07-circuit-breaker.md) para compromisos operativos seguros.

</details>

***

### Pregunta 10: Rendimiento y reducción de costes

En un entorno grande los costes mensuales de red son $5,000. Diseñe una estrategia integral de rendimiento y ahorro con resiliencia Istio.

**Situación:**

* 100 servicios repartidos uniformemente en 3 AZ
* Tráfico mensual: 500TB
* Respuesta media: 150ms
* Error: 3%

**Objetivos:**

* Reducir 50% el coste entre AZ
* Respuesta media inferior a 100ms
* Error inferior a 1%

<details>

<summary>Mostrar respuesta</summary>

Trate los 100 servicios, 500TB/mes, factura de $5,000, latencia de 150ms y 3% de errores proporcionados como una **base hipotética**, no como resultados medidos por esta auditoría. Identifique primero los componentes de tráfico facturables y el límite del SLI de cara al usuario. La latencia de un salto de proxy no es automáticamente la latencia de solicitud de extremo a extremo.

**1. Consolidar una política de destino por servicio revisado**

El ejemplo representativo `api-service` combina límites de grupos de conexiones, ponderación por localidad y detección de valores atípicos compatible en un DestinationRule. No aplique varias reglas comodín competidoras ni enrute todos los servicios a un backend genérico. Dimensione los valores para cada cliente y destino; la muestra no es un valor predeterminado de producción.

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

**2. Límites como controles de admisión medidos**

Estos son depósitos independientes por proxy en HTTP8080 en `production`. Verifique las etiquetas de nivel y la capacidad; una etiqueta «critical» por sí sola no justifica una tasa concreta. No imponen una cuota compartida de servicio/cuenta ni sustituyen la protección del borde.

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

**3. Separar modelo y factura**

Suponga 500TB decimal=500,000GB, fracción inicial 2/3, final 0.20 y tarifa **efectiva supuesta** $0.015/GB. El componente variable es:

| Modelo | Cálculo | Mensual |
|---|---|---:|
|Antes|500,000 × 2/3 × 0.015|$5,000|
|Después|500,000 × 0.20 × 0.015|$1,500|
|Diferencia|5,000 − 1,500|$3,500 (70%)|

Esto coincide con la base completa de $5,000 solo si toda esa factura corresponde a este componente variable. Las facturas reales de red pueden incluir otras direcciones, procesamiento de equilibrador de carga/NAT, transferencia por internet/entre regiones y costes fijos. Los pesos de solicitudes no tienen por qué equivaler a fracciones de bytes cuando difieren los tamaños de solicitudes/respuestas. Valide los ahorros modelados con datos de flujos facturables/CUR y precios actuales; no prometa un ahorro del 70% de la factura total.

Con latencias ilustrativas de un salto de 0.3ms local y 1.5ms entre AZ, el reparto uniforme da 0.3×1/3+1.5×2/3=1.10ms; 80/20 da 0.54ms. Ese cambio de 0.56ms no demuestra mejora total de 150ms→100ms. Trace ruta crítica, esperas DB/pool, trabajo y amplificación de retry reales.

**4. Validar cambios graduales**

| Etapa ilustrativa | Evidencia antes de ampliar |
|---|---|
|Semanas1–2: topología/localidad|Mapeo Node/Pod/EDS, capacidad zonal, solicitudes/bytes facturables y fallos|
|Semanas3–4: outlier/pool|Exclusiones aplicadas, endpoints restantes, overflow, latencia y causas de error|
|Semanas5–6: rate limits|Rechazar sobrecarga sin rechazo legítimo inaceptable; observar reintentos cliente|

El calendario es ilustrativo. Defina parada/rollback y mida tras cada cambio. Outliers pueden retirar capacidad o revelar fallos; no garantizan error menor a 1%. Un timeout distinto puede aumentar fallos en lugar de acelerar trabajo.

**5. Métricas con tipos y ámbitos correctos**

Las siguientes consultas por servicio diagnostican el servicio representativo. Mida por separado el SLI de cara al usuario. La latencia media utiliza la suma/recuento del histograma, no P50; las expulsiones activas son un indicador, mientras que los eventos de expulsión aplicados son un contador.

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

Active estadísticas y maneje ausencia de tráfico/scrape. Consultas entre AZ necesitan enriquecimiento real; `source_cluster_zone!=destination_cluster_zone` no es PromQL válido. Consulte [zonas](../../../service-mesh/istio/resilience/03-zone-aware-routing.md) para consultas condicionales acotadas.

**Los objetivos aún deben medirse**: coste entre AZ−50%, latencia media de usuario≤100ms y errores<1% son aceptación, no predicciones. Ubicar caché reduce distancia, no necesariamente aumenta aciertos. Evalúe funciones/capacidad ambient antes de comparar sobrecarga; no se demuestra ahorro genérico 30–50%. Un HPA multizona no escala cada zona independientemente; necesita diseño explícito de cargas/controladores.

Referencias: [Outliers](../../../service-mesh/istio/resilience/01-outlier-detection.md), [limitación](../../../service-mesh/istio/resilience/02-rate-limiting.md), [costes de red EKS](https://docs.aws.amazon.com/eks/latest/best-practices/cost-opt-networking.html).

</details>

***

## Cálculo de puntuación

* Opción múltiple 1-5: 10 puntos cada una (50 total)
* Preguntas breves 6-10: 10 puntos cada una (50 total)
* **Total: 100 puntos**

**Criterios:**

* 90-100: Excelente (experto en resiliencia Istio)
* 80-89: Buena comprensión; validar despliegues es aparte
* 70-79: Medio (se recomienda ampliar estudio)
* 60-69: Inferior a la media (repasar fundamentos)
* 0-59: Necesita volver a estudiar

## Recursos de aprendizaje

* [Detección de valores atípicos](../../../service-mesh/istio/resilience/01-outlier-detection.md)
* [Limitación de tasa](../../../service-mesh/istio/resilience/02-rate-limiting.md)
* [Enrutamiento por zona](../../../service-mesh/istio/resilience/03-zone-aware-routing.md)
