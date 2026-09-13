# Detección de valores atípicos

> **Última actualización**: September 11, 2026 · Istio 1.31. Ejemplos de sidecar independientes; cree los espacios de nombres indicados y cargas de trabajo/endpoints reales antes de probar. Los ejemplos para el mismo host son alternativas. Los valores son ilustrativos y no se han probado bajo carga.

La detección de valores atípicos es una forma del patrón de disyuntor que detecta automáticamente instancias de servicio con comportamiento anómalo y las elimina del grupo de tráfico.

## Índice

1. [Descripción general](#overview)
2. [Funcionamiento](#how-it-works)
3. [Configuración básica](#basic-configuration)
4. [Configuración avanzada](#advanced-configuration)
5. [Protección de servicios externos (ServiceEntry)](#protecting-external-services-serviceentry)
6. [Ejemplos prácticos](#practical-examples)
7. [Monitorización](#monitoring)
8. [Solución de problemas](#troubleshooting)

## Descripción general {#overview}

La detección de valores atípicos es pasiva y local a cada proxy observador. Con visibilidad HTTP, cuenta las respuestas ascendentes que cumplen los criterios y/o los fallos locales de conexión. No utiliza un umbral de latencia de DestinationRule ni envía sondas periódicas de recuperación. La expulsión cambia la elegibilidad para el equilibrio de carga de ese proxy; no elimina un Pod ni repara el servicio.


### Funciones principales

1. **Detección**: cuenta los fallos HTTP o de transporte consecutivos configurados.
2. **Expulsión**: excluye un host si lo permiten el límite de expulsión y su aplicación.
3. **Reincorporación**: vuelve a hacer elegible al host después de su período de expulsión; la recuperación real sigue requiriendo tráfico exitoso.

## Funcionamiento {#how-it-works}

### Proceso de detección de valores atípicos

Un éxito reinicia la secuencia de errores consecutivos correspondiente. Un fallo que cumpla los criterios y alcance el umbral puede activar la expulsión inmediatamente, sin esperar a `interval`. La duración de expulsión aumenta con las expulsiones repetidas (duración base × multiplicador, limitada por Envoy); no se trata de una sonda fija de 30 segundos ni de una duplicación exponencial.


### Métodos de detección

| Método | Descripción | Escenario de uso |
|--------|-------------|--------------|
| **Errores consecutivos** | Detectar errores 5xx consecutivos | Fallo de aplicación |
| **Errores de gateway** | Detectar errores 502, 503, 504 | Sobrecarga del servicio |
| **Fallos de conexión** | Detectar fallos de conexión TCP | Problemas de red |
| **Latencia** | No es un umbral de valores atípicos de DestinationRule | Observar la latencia; configurar por separado tiempos de espera de aplicación/ruta |

## Configuración básica {#basic-configuration}

### Detección basada en errores consecutivos

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

### Descripción de los parámetros principales

#### consecutive5xxErrors
- **Descripción**: umbral de ocurrencias de errores consecutivos
- **Valor predeterminado**: 5
- **Intervalo de ajuste ilustrativo**: 3-10 (según las características del servicio)

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

#### interval
- **Descripción**: intervalo del barrido periódico de expulsiones; la detección de errores consecutivos se ejecuta inmediatamente
- **Valor predeterminado**: 10s
- **Intervalo de ajuste ilustrativo**: 10s-60s

```yaml
# Fast detection (high load)
interval: 10s

# General case
---
interval: 30s

# Stable service
---
interval: 60s
```

#### baseEjectionTime
- **Descripción**: tiempo mínimo durante el que se expulsa una instancia
- **Valor predeterminado**: 30s
- **Intervalo de ajuste ilustrativo**: 30s-300s

```yaml
# Fast recovery attempt
baseEjectionTime: 30s

# General case
---
baseEjectionTime: 60s

# Cautious recovery
---
baseEjectionTime: 300s
```

#### maxEjectionPercent
- **Descripción**: porcentaje máximo de instancias que pueden expulsarse simultáneamente
- **Valor predeterminado**: 10%
- **Intervalo de ajuste ilustrativo**: 10%-50%

```yaml
# Conservative (stability first)
maxEjectionPercent: 10

# Balanced setting
---
maxEjectionPercent: 30

# Aggressive (quality first)
---
maxEjectionPercent: 50
```

## Configuración avanzada {#advanced-configuration}

### Detección basada en errores de gateway

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-gateway-errors
  namespace: default
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutiveGatewayErrors: 3
      interval: 10s
      baseEjectionTime: 60s
      maxEjectionPercent: 50
      minHealthPercent: 0
```

### Umbral de pánico del grupo sano

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-panic-threshold-example
  namespace: default
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      minHealthPercent: 50
      maxEjectionPercent: 30
```

`minHealthPercent: 50` es una elección de apertura ante fallos/pánico: por debajo del umbral de hosts sanos, el proxy también puede utilizar hosts no sanos. No es un número mínimo de solicitudes, una garantía de capacidad sana ni prevención de cerebro dividido. El valor predeterminado de Istio es 0; otros ejemplos utilizan 0 para deshabilitar este umbral de pánico. El límite de expulsión no hace que los endpoints restantes estén sanos.

### Detección basada en fallos de conexión

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-connection-errors
  namespace: default
spec:
  host: reviews
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 10
        maxRequestsPerConnection: 2
    outlierDetection:
      consecutiveLocalOriginFailures: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      splitExternalLocalOriginErrors: true
      minHealthPercent: 0
```

### Detección basada en la tasa de éxito (avanzada)

Envoy tiene detección estadística de tasa de éxito, con parámetros de número mínimo de hosts/volumen de solicitudes y desviación; no es simplemente «por debajo del 95%». La API DestinationRule de Istio 1.31 no expone `enforcingConsecutiveErrors`/`enforcingSuccessRate` ni esos umbrales estadísticos. La [implementación publicada](https://github.com/istio/istio/blob/1.31.0/pilot/pkg/networking/core/cluster_traffic_policy.go) deshabilita explícitamente la aplicación basada en tasa de éxito. `splitExternalLocalOriginErrors` separa clases de errores; no es un número mínimo de solicitudes. Utilice aquí los campos compatibles de errores consecutivos. Los cambios avanzados con EnvoyFilter requieren configuración específica de la versión y validación durante la ejecución.

## Protección de servicios externos (ServiceEntry) {#protecting-external-services-serviceentry}

Registre API externas o sistemas heredados como ServiceEntry y aplique detección de valores atípicos para evitar la propagación de fallos.

### Arquitectura de protección de API externas

![El sidecar Envoy de un pod de aplicación aplica detección de valores atípicos a tres instancias de API externa registradas como ServiceEntry, continúa enviando tráfico a las dos instancias sanas y expulsa la que devuelve errores.](../../../.gitbook/assets/en-service-mesh-istio-resilience-01-outlier-detection-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-resilience-01-outlier-detection-2.html)

Estos ejemplos de API externas con visibilidad HTTP requieren que la aplicación llame al **puerto HTTP 80** y que el sidecar origine TLS hacia el puerto de destino 443. Establecen SNI/SAN y utilizan el almacén de confianza del sistema operativo del proxy; monte un paquete de CA apropiado para una CA privada. El tráfico de la aplicación al sidecar va sin cifrar, por lo que esto no es adecuado cuando ese tramo también debe estar cifrado. Para HTTPS originado en la aplicación, utilice paso directo sin otra capa TLS SIMPLE; Envoy verá entonces fallos de transporte, no estado/latencia HTTP ni reglas de reintento HTTP. Verifique la incorporación, el enrutamiento y la validación de certificados antes de enviar credenciales. Los hosts/IP siguientes son ejemplos, no servicios aprovisionados; sustitúyalos por endpoints autorizados.

### Ejemplo 1: API externa única (basada en DNS)

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-payment-api
  namespace: payment
spec:
  hosts:
  - api.payment-provider.com
  resolution: DNS
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-payment-api
  namespace: payment
spec:
  host: api.payment-provider.com
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 3s
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 10
        maxRetries: 3
    outlierDetection:
      consecutive5xxErrors: 3
      consecutiveGatewayErrors: 2
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 3
      minHealthPercent: 0
    portLevelSettings:
    - port:
        number: 80
      tls:
        mode: SIMPLE
        sni: api.payment-provider.com
        subjectAltNames:
        - api.payment-provider.com
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-payment-api
  namespace: payment
spec:
  hosts:
  - api.payment-provider.com
  http:
  - name: no-retries
    route:
    - destination:
        host: api.payment-provider.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
```

**Ejemplo de uso**:
```go
package payment

import (
    "bytes"
    "context"
    "fmt"
    "io"
    "net/http"
    "time"
)

var paymentClient = &http.Client{
    Timeout: 5 * time.Second,
    CheckRedirect: func(req *http.Request, via []*http.Request) error {
        return http.ErrUseLastResponse
    },
}

// payload, authentication and payment-provider idempotency are application concerns.
// Requires the port80-to443 sidecar TLS-origination policy above.
func processPayment(ctx context.Context, payload []byte) error {
    req, err := http.NewRequestWithContext(ctx, http.MethodPost,
        "http://api.payment-provider.com/v1/charge", bytes.NewReader(payload))
    if err != nil { return err }
    req.Header.Set("Content-Type", "application/json")
    resp, err := paymentClient.Do(req)
    if err != nil { return fmt.Errorf("payment transport failed: %w", err) }
    defer resp.Body.Close()
    _, _ = io.Copy(io.Discard, io.LimitReader(resp.Body, 1<<20))
    if resp.StatusCode < 200 || resp.StatusCode >= 300 {
        return fmt.Errorf("payment endpoint returned HTTP %d", resp.StatusCode)
    }
    return nil
}
```

La detección de valores atípicos afecta a la selección posterior del host; no reintenta ni deduplica un pago. El VirtualService deshabilita explícitamente los reintentos de la malla. Un nombre DNS puede exponer un solo host de Envoy; la expulsión no garantiza que exista otro endpoint del proveedor. Un error de transporte no establece si la transacción remota se confirmó.

### Ejemplo 2: varios endpoints de API externa

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-weather-api
  namespace: weather
spec:
  hosts:
  - weather.api.com
  resolution: STATIC
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
  endpoints:
  - address: 203.0.113.10
    labels:
      region: us-east-1
    locality: us-east-1
  - address: 203.0.113.20
    labels:
      region: us-west-2
    locality: us-west-2
  - address: 203.0.113.30
    labels:
      region: eu-central-1
    locality: eu-central-1
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-weather-api
  namespace: weather
spec:
  host: weather.api.com
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
    connectionPool:
      tcp:
        maxConnections: 50
        connectTimeout: 5s
      http:
        http1MaxPendingRequests: 20
        maxRequestsPerConnection: 5
    outlierDetection:
      consecutive5xxErrors: 5
      consecutiveGatewayErrors: 3
      consecutiveLocalOriginFailures: 5
      interval: 30s
      baseEjectionTime: 60s
      maxEjectionPercent: 33
      splitExternalLocalOriginErrors: true
      minHealthPercent: 0
    portLevelSettings:
    - port:
        number: 80
      tls:
        mode: SIMPLE
        sni: weather.api.com
        subjectAltNames:
        - weather.api.com
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-weather-api
  namespace: weather
spec:
  hosts:
  - weather.api.com
  http:
  - name: no-retries
    route:
    - destination:
        host: weather.api.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
```

Las tres IP de documentación representan miembros de un grupo ascendente. `maxEjectionPercent` es un límite del grupo, no «uno por región». Las etiquetas son metadatos; `locality` proporciona la topología. El redondeo, el número de hosts descubiertos y las expulsiones actuales afectan a lo que realmente se elimina.

### Ejemplo 3: protección de una base de datos heredada

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: legacy-postgres
  namespace: database
spec:
  hosts:
  - legacy-db.company.internal
  resolution: DNS
  ports:
  - number: 5432
    name: tcp-postgres
    protocol: TCP
  location: MESH_EXTERNAL
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: legacy-postgres
  namespace: database
spec:
  host: legacy-db.company.internal
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 50
        connectTimeout: 10s
    outlierDetection:
      consecutive5xxErrors: 10
      consecutiveLocalOriginFailures: 5
      interval: 60s
      baseEjectionTime: 300s
      maxEjectionPercent: 20
      splitExternalLocalOriginErrors: true
      minHealthPercent: 0
```

Este ejemplo TCP observa fallos de conexión/transporte, no errores SQL, bloqueos ni latencia de consultas. Asegúrese de que el ServiceEntry identifique inequívocamente el destino; los puertos TCP compartidos pueden necesitar un diseño de captura DNS/VIP. No elige un primario de base de datos con capacidad de escritura ni hace segura la conmutación de réplicas.

### Ejemplo 4: API externa con reintentos

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-geocoding-api
  namespace: location
spec:
  hosts:
  - maps.googleapis.com
  resolution: DNS
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-geocoding-api
  namespace: location
spec:
  hosts:
  - maps.googleapis.com
  http:
  - name: writes-no-retry
    match:
    - method:
        regex: ^(POST|PUT|PATCH|DELETE)$
    route:
    - destination:
        host: maps.googleapis.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
  - timeout: 5s
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: gateway-error,connect-failure,refused-stream
    route:
    - destination:
        host: maps.googleapis.com
        port:
          number: 80
    name: idempotent-reads
    match:
    - method:
        regex: ^(GET|HEAD|OPTIONS)$
  - name: other-methods-no-retry
    route:
    - destination:
        host: maps.googleapis.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-geocoding-api
  namespace: location
spec:
  host: maps.googleapis.com
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 3s
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 10
        maxRetries: 3
    outlierDetection:
      consecutive5xxErrors: 3
      consecutiveGatewayErrors: 2
      consecutiveLocalOriginFailures: 3
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      splitExternalLocalOriginErrors: true
      minHealthPercent: 0
    portLevelSettings:
    - port:
        number: 80
      tls:
        mode: SIMPLE
        sni: maps.googleapis.com
        subjectAltNames:
        - maps.googleapis.com
```

El ejemplo de geocodificación solo reintenta lecturas idempotentes que coinciden. Llame a la ruta del puerto HTTP 80 para que el proxy pueda ver el método; el paso directo HTTPS no puede utilizar esta política HTTP. Tres reintentos más el intento inicial no caben todos si cada intento dura 2s dentro del tiempo de espera total de 5s.

### Ejemplo 5: servicio externo con limitación de tasa

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-rate-limited-api
  namespace: api
spec:
  hosts:
  - api.third-party.com
  resolution: DNS
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: ratelimit-config
  namespace: api
data:
  config.yaml: "domain: external-api-ratelimit\ndescriptors:\n- key: destination_cluster\n  value: outbound|80||api.third-party.com\n  rate_limit:\n    unit: second\n    requests_per_unit: 100\n"
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-rate-limited-api
  namespace: api
spec:
  host: api.third-party.com
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 10
    outlierDetection:
      consecutive5xxErrors: 3
      consecutiveGatewayErrors: 2
      interval: 10s
      baseEjectionTime: 60s
      maxEjectionPercent: 50
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 3
      minHealthPercent: 0
    portLevelSettings:
    - port:
        number: 80
      tls:
        mode: SIMPLE
        sni: api.third-party.com
        subjectAltNames:
        - api.third-party.com
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-rate-limited-api
  namespace: api
spec:
  hosts:
  - api.third-party.com
  http:
  - name: no-retries
    route:
    - destination:
        host: api.third-party.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
```

El ConfigMap es únicamente un fragmento de configuración del servicio de limitación de tasa. Debe montarse en un servicio compatible en ejecución con su almacén de respaldo, el filtro de limitación de tasa saliente de Envoy y un descriptor `destination_cluster` coincidente. Por sí solo no aplica nada. Los errores de gateway son 502/503/504, no 429; la detección estándar de 5xx no trata 429 como un error de gateway. El tiempo de expulsión no se sincroniza con el restablecimiento de cuota del proveedor. Prefiera un tratamiento consciente de las cuotas y Retry-After/esperas progresivas de la aplicación a expulsar todos los hosts sanos limitados por cuota.

### Buenas prácticas de detección de valores atípicos de servicios externos

#### 1. Distinguir los tipos de errores

```yaml
outlierDetection:
  # Gateway errors (502, 503, 504)
  consecutiveGatewayErrors: 2  # Detect quickly

  # 5xx errors (500, 501, etc.)
  consecutive5xxErrors: 3

  # Local errors (timeout, connection failure)
  consecutiveLocalOriginFailures: 3

  # Track local and remote errors separately
  splitExternalLocalOriginErrors: true
```

**Importante**: al establecer `splitExternalLocalOriginErrors: true`:
- **Fallos de origen local**: tiempo de espera/reinicio/rechazo de conexión atribuido a un host ascendente; un fallo de resolución DNS puede dejar sin host que expulsar
- **Fallos ascendentes**: errores 5xx devueltos por la API externa

Se cuentan por separado para una detección más precisa.

#### 2. Configuración de tiempos de espera

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
  namespace: default
spec:
  hosts:
  - api.external.com
  location: MESH_EXTERNAL
  resolution: DNS
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-api
  namespace: default
spec:
  hosts:
  - api.external.com
  http:
  - name: writes-no-retry
    match:
    - method:
        regex: ^(POST|PUT|PATCH|DELETE)$
    route:
    - destination:
        host: api.external.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
  - timeout: 5s
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: gateway-error,connect-failure,refused-stream
    route:
    - destination:
        host: api.external.com
        port:
          number: 80
    name: idempotent-reads
    match:
    - method:
        regex: ^(GET|HEAD|OPTIONS)$
  - name: other-methods-no-retry
    route:
    - destination:
        host: api.external.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-api
  namespace: default
spec:
  host: api.external.com
  trafficPolicy:
    connectionPool:
      tcp:
        connectTimeout: 3s
    outlierDetection:
      consecutiveLocalOriginFailures: 3
      splitExternalLocalOriginErrors: true
      minHealthPercent: 0
    portLevelSettings:
    - port:
        number: 80
      tls:
        mode: SIMPLE
        sni: api.external.com
        subjectAltNames:
        - api.external.com
```

#### 3. Monitorización de servicios externos

```promql
# Outlier Detection metrics
# 1. Ejected external endpoints
envoy_cluster_outlier_detection_ejections_active{
  namespace="default", cluster_name=~"outbound.*api\\.external\\.com.*"
}

# 2. Local errors (timeout, connection failure)
rate(envoy_cluster_upstream_rq_timeout{
  namespace="default", cluster_name=~"outbound.*api\\.external\\.com.*"
}[5m])

# 3. External API 5xx errors
rate(istio_requests_total{
  reporter="source", source_workload_namespace="default",
  destination_service="api.external.com",
  response_code=~"5.."
}[5m])

# 4. External API response time
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket{
    reporter="source", source_workload_namespace="default",
    destination_service="api.external.com"
  }[5m])) by (le)
)
```

#### 4. Configuración de alertas

Este es un fragmento de archivo de reglas de Prometheus, no un recurso de Kubernetes. Móntelo/selecciónelo en Prometheus (o envuelva los grupos en un PrometheusRule seleccionado). Los umbrales requieren tratamiento del volumen de tráfico, la ausencia de datos y el estado de la recopilación; no son SLO validados. La latencia siguiente está en milisegundos y las tasas son por segundo.


```yaml
# Prometheus Alert Rules
groups:
- name: external_api_alerts
  interval: 1m
  rules:
  # High external API error rate
  - alert: ExternalAPIHighErrorRate
    expr: |
      (sum(rate(istio_requests_total{
        reporter="source", source_workload_namespace="default",
        destination_service=~".*external.*",
        response_code=~"5.."
      }[5m])) by (destination_service)
      /
      sum(rate(istio_requests_total{
        reporter="source", source_workload_namespace="default",
        destination_service=~".*external.*"
      }[5m])) by (destination_service))
      * 100 > 5
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate for external API {{ $labels.destination_service }}"
      description: "Error rate is {{ $value }}%"

  # External API instance ejected
  - alert: ExternalAPIInstanceEjected
    expr: |
      envoy_cluster_outlier_detection_ejections_active{
        namespace="default", cluster_name=~"outbound.*external.*"
      } > 0
    for: 1m
    labels:
      severity: warning
    annotations:
      summary: "External API instance ejected"
      description: "{{ $value }} instances ejected from {{ $labels.cluster_name }}"

  # Increased external API timeouts
  - alert: ExternalAPIHighTimeout
    expr: |
      rate(envoy_cluster_upstream_rq_timeout{
        namespace="default", cluster_name=~"outbound.*external.*"
      }[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High timeout rate for external API"
      description: "Timeout rate is {{ $value }} req/s"
```

#### 5. Solución de problemas

Ejecute el diagnóstico en el proxy que realiza la llamada. El comando de conectividad requiere curl en un contenedor autorizado de aplicación/prueba y un endpoint de estado real de solo lectura; ejecutar curl dentro de `istio-proxy` puede eludir la ruta de tráfico de la aplicación. Estas consultas genéricas de monitorización se refieren al ejemplo independiente `default`/`api.external.com`; ajuste el ámbito para los demás ejemplos.


```bash
# 1. Check ServiceEntry
kubectl get serviceentry -A
kubectl describe serviceentry external-api -n <namespace>

# 2. Verify DestinationRule application
istioctl proxy-config clusters <pod-name> -n <namespace> --fqdn api.external.com -o json | \
  jq '.[] | {name: .name, outlierDetection: .outlierDetection}'

# 3. Test external API connection
kubectl exec <client-pod> -n default -c <app-container> -- \
  curl --max-time 5 -v http://api.external.com/health

# 4. Check Envoy statistics
istioctl x envoy-stats <pod-name> -n <namespace> --output prom | grep "outbound.*external"

# 5. Outlier Detection status
istioctl x envoy-stats <pod-name> -n <namespace> --type clusters
```

### Escenarios de fallo de servicios externos

#### Escenario 1: fallo temporal de API externa

```yaml
# Configuration: Fast detection and recovery
outlierDetection:
  consecutive5xxErrors: 3           # 3 consecutive errors
  consecutiveGatewayErrors: 2    # 2 gateway errors
  interval: 10s                  # Evaluate every 10 seconds
  baseEjectionTime: 30s          # Recovery attempt after 30 seconds
  maxEjectionPercent: 50         # Maximum 50% ejection
```

**Comportamiento esperado, sujeto a los límites efectivos**:

1. Las respuestas 502/503 que cumplen los criterios cuentan para el umbral de gateway.
2. Alcanzar dos fallos de gateway consecutivos puede expulsar al host si lo permiten la aplicación y el límite.
3. El host vuelve a ser elegible después de su período de expulsión; aquí no se configura ninguna sonda activa.
4. Las expulsiones repetidas aumentan la duración mediante el multiplicador/límite de Envoy. Volver al grupo no demuestra que el proveedor se haya recuperado.

#### Escenario 2: caída completa de la API externa

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api-ha
  namespace: default
spec:
  hosts:
  - api.external.com
  resolution: STATIC
  endpoints:
  - address: 203.0.113.10
    labels:
      tier: primary
  - address: 203.0.113.20
    labels:
      tier: secondary
  - address: 203.0.113.30
    labels:
      tier: tertiary
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-api-ha
  namespace: default
spec:
  host: api.external.com
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 3
      consecutiveLocalOriginFailures: 3
      interval: 10s
      baseEjectionTime: 60s
      maxEjectionPercent: 66
      minHealthPercent: 0
      splitExternalLocalOriginErrors: true
    portLevelSettings:
    - port:
        number: 80
      tls:
        mode: SIMPLE
        sni: api.external.com
        subjectAltNames:
        - api.external.com
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-api-ha
  namespace: default
spec:
  hosts:
  - api.external.com
  http:
  - name: no-retries
    route:
    - destination:
        host: api.external.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
```

**Interpretación**:

Los tres endpoints son miembros de un grupo. Las etiquetas `tier: primary/secondary/tertiary` no definen prioridades de conmutación por error; el equilibrio de carga normal puede seleccionar cualquier endpoint elegible. Un endpoint fallido puede expulsarse localmente y seleccionarse otro, pero el enrutamiento no puede reparar un servicio externo completamente fallido. `minHealthPercent: 0` deshabilita el uso de hosts no sanos en modo pánico; el límite porcentual no garantiza que sobreviva uno sano. Utilice prioridades de localidad diseñadas explícitamente o un mecanismo de conmutación de la aplicación/proveedor si necesita conmutación ordenada. Las IP de documentación deben sustituirse antes de cualquier prueba de conectividad.

## Ejemplos prácticos {#practical-examples}

### Ejemplo 1: cadena de microservicios

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: backend-outlier
  namespace: default
spec:
  host: backend
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 3
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 0
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: database-outlier
  namespace: default
spec:
  host: database
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 10
      interval: 60s
      baseEjectionTime: 300s
      maxEjectionPercent: 20
      minHealthPercent: 0
```

### Ejemplo 2: uso con despliegue canary

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-canary
  namespace: default
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 90
    - destination:
        host: reviews
        subset: v2
      weight: 10
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
  namespace: default
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
    trafficPolicy:
      outlierDetection:
        consecutive5xxErrors: 3
        interval: 10s
        baseEjectionTime: 60s
        maxEjectionPercent: 100
        minHealthPercent: 0
```

Expulsar todos los endpoints v2 no transfiere su peso de ruta del 10% a v1. Las solicitudes seleccionadas para un subconjunto canary vacío pueden fallar; un controlador de despliegue debe cambiar el peso de la ruta/revertir según el estado observado. Las etiquetas de las cargas de trabajo deben coincidir con ambos subconjuntos.

### Ejemplo 3: despliegue multirregión

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-multi-region
  namespace: default
spec:
  host: api
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/*
          to:
            us-east-1/*: 80
            us-west-2/*: 20
    outlierDetection:
      consecutive5xxErrors: 10
      interval: 60s
      baseEjectionTime: 120s
      maxEjectionPercent: 30
      minHealthPercent: 0
```

Esta política 80/20 envía tráfico deliberadamente a ambas regiones sanas. No es una conmutación a una reserva y requiere metadatos reales de localidad de región, conectividad entre regiones y capacidad. Un nombre de región por sí solo no crea una malla multiclúster.

### Ejemplo 4: grupo de conexiones + detección de valores atípicos

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-full-protection
  namespace: default
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
    outlierDetection:
      consecutive5xxErrors: 5
      consecutiveGatewayErrors: 3
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 0
```

## Monitorización {#monitoring}

### Métricas de Prometheus

Habilite las estadísticas opcionales del proxy y las etiquetas de recopilación como se describe en la [descripción general de resiliencia](README.md#resilience-metrics). Estos ejemplos conservan `pod`/`cluster_name` de cada proxy; sumar las expulsiones entre clientes no cuenta Pods de servidor distintos. El arranque de Istio publicado utiliza `cluster_name`; verifique las etiquetas después del reetiquetado de su recopilador. Los contadores `enforced_*` cuentan expulsiones reales, mientras que `detected_*` pueden aumentar cuando un límite bloquea la expulsión.

```promql
# Current ejections, not a cumulative event counter
envoy_cluster_outlier_detection_ejections_active{namespace="default"}

# Enforced ejection events per second
rate(envoy_cluster_outlier_detection_ejections_enforced_total{namespace="default"}[5m])

# Percentage of the total observed pool, excluding zero-size pools
100 * envoy_cluster_outlier_detection_ejections_active{namespace="default"} /
(envoy_cluster_membership_total{namespace="default"} > 0)

rate(envoy_cluster_outlier_detection_ejections_enforced_consecutive_5xx{namespace="default"}[5m])
rate(envoy_cluster_outlier_detection_ejections_enforced_consecutive_gateway_failure{namespace="default"}[5m])
rate(envoy_cluster_outlier_detection_ejections_enforced_consecutive_local_origin_failure{namespace="default"}[5m])
```

### Ejemplo de panel de Grafana

Guarde este objeto de panel mediante el flujo de [aprovisionamiento de paneles mediante archivos](../observability/04-dashboards.md). Espera el UID de fuente de datos `prometheus` y etiquetas reales `namespace`/`pod`/`cluster_name`. Un ConfigMap por sí solo no carga paneles.

```json
{
  "uid": "istio-outlier-detection",
  "title": "Istio Outlier Detection",
  "panels": [
    {
      "id": 1,
      "title": "Ejected Hosts",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "envoy_cluster_outlier_detection_ejections_active{namespace=\"default\"}",
          "legendFormat": "{{pod}} / {{cluster_name}}",
          "refId": "A"
        }
      ],
      "gridPos": {
        "x": 0,
        "y": 0,
        "w": 24,
        "h": 8
      },
      "fieldConfig": {
        "defaults": {
          "unit": "short"
        }
      }
    },
    {
      "id": 2,
      "title": "Enforced Ejections per Second",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "rate(envoy_cluster_outlier_detection_ejections_enforced_total{namespace=\"default\"}[5m])",
          "legendFormat": "{{pod}} / {{cluster_name}}",
          "refId": "A"
        }
      ],
      "gridPos": {
        "x": 0,
        "y": 8,
        "w": 24,
        "h": 8
      },
      "fieldConfig": {
        "defaults": {
          "unit": "short"
        }
      }
    },
    {
      "id": 3,
      "title": "Ejected Pool Percentage",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "100 * envoy_cluster_outlier_detection_ejections_active{namespace=\"default\"} / (envoy_cluster_membership_total{namespace=\"default\"} > 0)",
          "legendFormat": "{{pod}} / {{cluster_name}}",
          "refId": "A"
        }
      ],
      "gridPos": {
        "x": 0,
        "y": 16,
        "w": 24,
        "h": 8
      },
      "fieldConfig": {
        "defaults": {
          "unit": "percent"
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

### Monitorización en tiempo real

```bash
# Check Envoy statistics
istioctl x envoy-stats <pod-name> -n <namespace> --output prom | grep outlier

# Key metrics:
# envoy_cluster_outlier_detection_ejections_active: Currently ejected instances
# envoy_cluster_outlier_detection_ejections_enforced_total: Total ejection count
# envoy_cluster_outlier_detection_ejections_enforced_consecutive_5xx: Ejections due to 5xx errors
```

### Verificar en Kiali

```bash
# Access Kiali
istioctl dashboard kiali

# Things to check:
# 1. Graph → Select service → Traffic tab
# 2. Graph health is aggregate telemetry, not every caller proxy’s ejection state
# 3. Check Outlier Detection metrics
```

## Solución de problemas {#troubleshooting}

### La detección de valores atípicos no funciona

```bash
# 1. Check DestinationRule
kubectl get destinationrule -n <namespace>
kubectl describe destinationrule <name> -n <namespace>

# 2. Check Envoy cluster configuration
istioctl proxy-config clusters <pod-name> -n <namespace> --fqdn <service-fqdn> -o json | \
  jq '.[] | .outlierDetection'

# 3. Check Envoy logs
kubectl logs -n <namespace> <pod-name> -c istio-proxy | grep outlier

# 4. Validate control-plane configuration (istiod does not perform per-proxy ejections)
istioctl analyze -n <namespace>
```

### Se expulsan demasiadas instancias

Inspeccione los contadores de expulsión aplicada/detectada/desbordamiento, la capacidad restante y los tipos de error reales antes de cambiar los umbrales. Aumente un umbral de errores consecutivos si la aplicación puede tolerar los fallos observados; reduzca el límite solo con una decisión explícita sobre la disponibilidad. Aumentar `interval` no retrasa la expulsión inmediata por errores consecutivos.

```yaml
# DestinationRule trafficPolicy fragment; illustrative values
outlierDetection:
  consecutive5xxErrors: 10
  interval: 30s
  baseEjectionTime: 30s
  maxEjectionPercent: 30
  minHealthPercent: 0
```

### No hay hosts ascendentes sanos

Esto no es un caso de cerebro dividido de base de datos. Compruebe la disponibilidad, el descubrimiento, el enrutamiento, el estado de los endpoints y las expulsiones locales del cliente. Establecer `minHealthPercent: 50` puede permitir el uso de hosts no sanos ante fallos; no los restaura. Un subconjunto canary expulsado al 100% puede requerir revertir la ruta. Utilice el estado efectivo de endpoints/clústeres, no solo el YAML de DestinationRule ni un icono de Kiali.

### Recuperación demasiado lenta tras la expulsión

Revise el historial de expulsiones repetidas y el límite efectivo de duración de Envoy. Reducir `baseEjectionTime` puede hacer que el tráfico vuelva antes a un host no sano; no es una reparación. La comprobación activa del estado es una función independiente y este DestinationRule no la habilita.

### Falsos positivos por errores temporales

Distinga los fallos de conexión de los fallos de aplicación y compruebe si los reintentos los amplifican. Un 5xx puede ser una respuesta intencionada, mientras que una respuesta lenta pero exitosa por sí sola no es un valor atípico basado en latencia. Limite el ámbito del despliegue y verifique la configuración modificada del proxy; los registros predeterminados no tienen por qué contener eventos de valores atípicos.

## Buenas prácticas

### 1. Configuración por tipo de servicio

```yaml
# Critical service (fast detection)
outlierDetection:
  consecutive5xxErrors: 3
  interval: 10s
  baseEjectionTime: 30s
  maxEjectionPercent: 50

# General service
---
outlierDetection:
  consecutive5xxErrors: 5
  interval: 30s
  baseEjectionTime: 60s
  maxEjectionPercent: 30

# Stable service (lenient settings)
---
outlierDetection:
  consecutive5xxErrors: 10
  interval: 60s
  baseEjectionTime: 120s
  maxEjectionPercent: 20
```

### 2. Combinar con grupos de conexiones cuando sea necesario

```yaml
# Independent limits; size against measured caller/endpoint capacity
trafficPolicy:
  connectionPool:
    tcp:
      maxConnections: 100
    http:
      http1MaxPendingRequests: 50
  outlierDetection:
    consecutive5xxErrors: 5
    interval: 30s
```

### 3. Elegir deliberadamente el comportamiento de pánico

`minHealthPercent: 0` es el valor predeterminado de Istio y deshabilita el umbral de pánico de hosts no sanos. Los valores distintos de cero permiten equilibrar disponibilidad y aislamiento; no garantizan que algunos hosts sigan sanos. Los disyuntores de grupos de conexiones y la detección de valores atípicos son controles independientes.

### 4. Despliegue gradual

Recopile una base de referencia, verifique las políticas efectivas de malla/espacio de nombres/carga de trabajo y aplique después un ajuste medido a un grupo de prueba aislado; amplíelo solo tras validar. No utilice `maxEjectionPercent: 0` como interruptor de solo monitorización: en la [implementación de Istio 1.31](https://github.com/istio/istio/blob/1.31.0/pilot/pkg/networking/core/cluster_traffic_policy.go), solo los valores mayores que 0 establecen el campo de Envoy, por lo que 0 deja el valor predeterminado de Envoy en vez de deshabilitar las expulsiones. Los ajustes omitidos también pueden heredar un valor predeterminado de la malla. Observe los eventos aplicados reales y los endpoints restantes antes de ampliar el despliegue.

### 5. Monitorización y alertas

```yaml
# Prometheus Alerting Rule
groups:
- name: istio_outlier_detection
  rules:
  - alert: HighEjectionRate
    expr: rate(envoy_cluster_outlier_detection_ejections_enforced_total{namespace="default"}[5m]) > 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High outlier ejection rate"
      description: "{{ $labels.cluster_name }} has enforced ejection rate > 0.1 events/s"
```

## Referencias

- [Detección de valores atípicos de Istio](https://istio.io/latest/docs/reference/config/networking/destination-rule/#OutlierDetection)
- [Detección de valores atípicos de Envoy](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/outlier)
- [Disyuntores](https://istio.io/latest/docs/tasks/traffic-management/circuit-breaking/)
