# Gestión del tráfico

Las capacidades de gestión del tráfico de Istio permiten controlar con precisión el flujo de tráfico dentro de la malla de servicios.

## Tabla de contenido

1. [Gateway y VirtualService](01-gateway-virtualservice.md)
2. [Enrutamiento](02-routing.md)
3. [DestinationRule](03-destination-rule.md) ⭐ Concepto esencial
4. [División del tráfico](04-traffic-splitting.md)
5. [Reintentos y tiempos de espera](05-retry-timeout.md)
6. [Balanceo de carga](06-load-balancing.md)
7. [Circuit Breaker](07-circuit-breaker.md)
8. [Inyección de fallos](08-fault-injection.md)
9. [Duplicación del tráfico](09-traffic-mirror.md)
10. [Afinidad de sesión](10-session-affinity.md)
11. [Control de salida](11-egress-control.md)
12. [ServiceEntry (gestión de servicios externos)](12-service-entry.md)
13. [WorkloadEntry (registro de máquinas virtuales)](13-workload-entry.md)

## Descripción general

Estos son ejemplos de configuración para el modo sidecar de una versión compatible de Istio. Gateway, VirtualService y DestinationRule son objetos de API que consumen los proxies, no saltos de red independientes. Un mirror es una copia adicional de las solicitudes seleccionadas, no la parte restante de una división 90/10; las respuestas duplicadas se descartan. Los diagramas muestran relaciones de configuración lógicas.

Los fragmentos son ejemplos alternativos, no un único manifiesto para aplicar en conjunto. Crea primero los Services y subconjuntos de DestinationRule a los que hacen referencia. Si una VirtualService no incluye una lista `gateways`, se aplica a la malla; las rutas de ingreso requieren una asociación explícita a un Gateway y un nombre de host coincidente. Para el modo ambient, usa el enrutamiento compatible de Gateway API/waypoint.

La gestión del tráfico es una de las funciones principales de Istio y permite realizar estas operaciones sin cambios en el código:

### Funciones principales

![Una solicitud del cliente entra por el Gateway, VirtualService la enruta, DestinationRule aplica la política de tráfico y, después, la solicitud se distribuye entre tres versiones del servicio: la versión principal, una canaria y una copia duplicada para pruebas en sombra.](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-readme-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-readme-0.html)

### 1. Enrutamiento inteligente

- **Basado en la ruta**: `/api/v1` → Service A, `/api/v2` → Service B
- **Basado en encabezados**: `User-Agent: Mobile` → versión móvil
- **Basado en cookies**: enruta usuarios específicos a versiones específicas
- **Basado en pesos**: distribuye el tráfico según una proporción

### 2. Estrategias de despliegue

**Despliegue canario**:
```yaml
# Only 10% to new version
route:
- destination:
    host: reviews
    subset: v1
  weight: 90
- destination:
    host: reviews
    subset: v2
  weight: 10
```

**Despliegue azul/verde**:
```yaml
# Instant switch
route:
- destination:
    host: reviews
    subset: v2  # Switch to Green
  weight: 100
```

### 3. Patrones de resiliencia

- **Circuit Breaker**: aislar los servicios que fallan
- **Reintentos**: reintentos automáticos
- **Tiempo de espera**: límites para el tiempo de respuesta
- **Limitación de velocidad**: controlar la tasa de solicitudes

### 4. Pruebas y depuración

- **Duplicación del tráfico**: replicar tráfico de producción para probarlo
- **Inyección de fallos**: inyectar fallos de forma intencional
- **Pruebas A/B**: ofrecer versiones distintas a grupos de usuarios distintos

## Recursos principales

### Gateway

Define el punto de entrada del tráfico externo a la malla.

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: my-gateway
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "myapp.example.com"
```

### VirtualService

Define cómo se enrutan las solicitudes.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - match:
    - uri:
        prefix: "/v2"
    route:
    - destination:
        host: reviews
        subset: v2
  - route:
    - destination:
        host: reviews
        subset: v1
```

### DestinationRule

Define las políticas del servicio de destino.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

## Ejemplos prácticos

### Despliegue canario seguro

```yaml
# Step 1: Start with 5% traffic
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-canary
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 95
    - destination:
        host: reviews
        subset: v2
      weight: 5
```

Después de supervisar el resultado, aumenta gradualmente el porcentaje si no hay problemas:
- 5% → 10% → 25% → 50% → 100%

### Enrutamiento basado en encabezados (pruebas para desarrolladores)

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-dev
spec:
  hosts:
  - reviews
  http:
  # Developers use new version
  - match:
    - headers:
        x-dev-user:
          exact: "true"
    route:
    - destination:
        host: reviews
        subset: v2
  # Regular users use stable version
  - route:
    - destination:
        host: reviews
        subset: v1
```

El encabezado del desarrollador es una indicación de enrutamiento que proporciona el cliente; no es autenticación ni un límite de autorización.

### Circuit Breaker + reintentos

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-resilient
spec:
  host: reviews
  trafficPolicy:
    # Connection Pool settings
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 2
    # Circuit Breaker
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
---
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
      attempts: 3
      perTryTimeout: 2s
      retryOn: 5xx,reset,connect-failure
    timeout: 10s
```

## Flujo de tráfico

![Una solicitud de usuario entra por el Gateway de ingreso, pasa por el enrutamiento de VirtualService (coincidencias por ruta, encabezado y, después, peso), se ajusta según las políticas de DestinationRule (balanceo de carga, circuit breaker y pool de conexiones) y finalmente llega a uno de los tres Pods de respaldo.](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-readme-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-readme-1.html)

## Ruta de aprendizaje

Para aprender eficazmente la gestión del tráfico, se recomienda seguir este orden:

1. **[Gateway y VirtualService](01-gateway-virtualservice.md)** ⭐ Punto de partida
   - Comprender los conceptos básicos
   - Gestionar el tráfico externo

2. **[Enrutamiento](02-routing.md)**
   - Patrones de enrutamiento avanzados
   - Enrutamiento condicional

3. **[DestinationRule](03-destination-rule.md)** ⭐ Concepto esencial
   - Comprender el concepto de subconjunto
   - Fundamentos de la política de tráfico
   - Integración con VirtualService

4. **[División del tráfico](04-traffic-splitting.md)**
   - Despliegue canario
   - Pruebas A/B

5. **[Reintentos y tiempos de espera](05-retry-timeout.md)**
   - Recuperación ante fallos
   - Control del tiempo de respuesta

6. **[Balanceo de carga](06-load-balancing.md)**
   - Distintos algoritmos
   - Optimización del rendimiento

7. **[Circuit Breaker](07-circuit-breaker.md)**
   - Aislamiento de fallos
   - Prevención de fallos en cascada

8. **[Inyección de fallos](08-fault-injection.md)**
   - Pruebas de fallos
   - Ingeniería del caos

9. **[Duplicación del tráfico](09-traffic-mirror.md)**
   - Pruebas en producción
   - Validación de versiones nuevas

10. **[Afinidad de sesión](10-session-affinity.md)**
    - Sesión persistente
    - Conservación del estado

11. **[Control de salida](11-egress-control.md)**
    - Acceso a servicios externos
    - Refuerzo de la seguridad

12. **[ServiceEntry](12-service-entry.md)**
    - Registro de servicios externos
    - Integración con Egress Gateway

## Prácticas recomendadas

### 1. Despliegue gradual

```yaml
# ❌ Bad example: 100% at once
weight: 100

# ✅ Good example: Gradual increase
# 5% → Monitor → 10% → Monitor → ...
```

### 2. Define tiempos de espera adecuados para la carga de trabajo

```yaml
# ✅ Always set timeout
http:
- route:
  - destination:
      host: reviews
  timeout: 10s
```

Las solicitudes de streaming pueden necesitar tiempos de espera distintos. Un plazo HTTP corto no es adecuado para todos los streams de gRPC ni para respuestas de larga duración.

### 3. Usa los reintentos con cuidado

```yaml
# ✅ Only when idempotency is guaranteed
retries:
  attempts: 3
  perTryTimeout: 2s
  retryOn: 5xx,reset,connect-failure
```

### 4. Ajusta los umbrales del Circuit Breaker

```yaml
# ✅ Adjust according to service characteristics
outlierDetection:
  consecutive5xxErrors: 5      # Adjust per service
  interval: 30s
  baseEjectionTime: 30s
  maxEjectionPercent: 50    # Maximum 50% ejection
```

### 5. Supervisa las métricas

Supervisa siempre las métricas al cambiar la gestión del tráfico:
- **Tasa de solicitudes**: cambio en el número de solicitudes
- **Tasa de errores**: proporción de errores
- **Latencia**: latencia P50, P95 y P99
- **Tasa de éxito**: proporción de solicitudes correctas

## Solución de problemas

### El tráfico no se enruta

```bash
# 1. Check VirtualService
kubectl get virtualservice -n <namespace>
kubectl describe virtualservice <name> -n <namespace>

# 2. Check DestinationRule
kubectl get destinationrule -n <namespace>

# 3. Check pod labels
kubectl get pods --show-labels -n <namespace>

# 4. Analyze Istio configuration
istioctl analyze -n <namespace>
```

### No se aplica la ponderación

```bash
# Check Envoy configuration
istioctl proxy-config routes <pod-name> -n <namespace>

# Check cluster information
istioctl proxy-config clusters <pod-name> -n <namespace>
```

## Próximos pasos

1. **[Seguridad](../security/README.md)**: mTLS y autenticación/autorización
2. **[Observabilidad](../observability/README.md)**: métricas, registros y trazas
3. **[Resiliencia](../resilience/README.md)**: limitación de velocidad y enrutamiento con conocimiento de zona

## Referencias

- [Gestión del tráfico en Istio](https://istio.io/latest/docs/concepts/traffic-management/)
- [Referencia de VirtualService](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
- [Referencia de DestinationRule](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
- [Referencia de Gateway](https://istio.io/latest/docs/reference/config/networking/gateway/)

## Cuestionario

Para comprobar lo aprendido en este capítulo, intenta el [cuestionario de gestión del tráfico de Istio](../../../quizzes/service-mesh/istio/traffic-management.md).
