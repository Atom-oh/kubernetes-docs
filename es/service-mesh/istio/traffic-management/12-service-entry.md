# ServiceEntry

ServiceEntry registra servicios externos en la malla de Istio para que puedan gestionarse como servicios internos.

## Tabla de contenidos

1. [¿Por qué ServiceEntry?](#why-serviceentry)
2. [Descripción general de ServiceEntry](#serviceentry-overview)
3. [Modos de resolución](#resolution-modes)
4. [Configuración de ubicación](#location-settings)
5. [Ejemplos prácticos](#practical-examples)
6. [Combinación con Egress Gateway](#combining-with-egress-gateway)
7. [Seguridad y TLS](#security-and-tls)
8. [Supervisión y control](#monitoring-and-control)
9. [Prácticas recomendadas](#best-practices)

## ¿Por qué ServiceEntry? {#why-serviceentry}

### La necesidad de gestionar servicios externos

Con ALLOW_ANY, los destinos externos desconocidos pueden recibir tráfico, aunque con políticas y telemetría más limitadas. ServiceEntry registra un destino para que se puedan configurar políticas compatibles en los proxies; no es una regla de control de acceso.

El registro permite configurar cada destino por separado; la supervisión, TLS y el control del tráfico dependen del protocolo y de las políticas aplicadas.

### Ventajas principales

| Función | Sin ServiceEntry | Con ServiceEntry |
|---------|---------------------|-------------------|
| **Supervisión** | Telemetría limitada del tráfico de paso | Telemetría según el protocolo; HTTP requiere visibilidad L7 |
| **Control del tráfico** | No disponible | Tiempos de espera, reintentos y circuit breaker |
| **Seguridad** | TLS de la aplicación sigue siendo posible | TLS/mTLS se configura por separado; no se emiten certificados externos automáticamente |
| **Control de salida** | Depende de las políticas de salida y de red | Configuración del registro y del enrutamiento; la aplicación de controles de red es independiente |
| **Descubrimiento de servicios** | Administración manual | Búsqueda automática en DNS |

## Descripción general de ServiceEntry {#serviceentry-overview}

Estos ejemplos son configuraciones alternativas para sidecars. istiod y los proxies consumen ServiceEntry; no es un salto de red. `addresses` clasifica el tráfico del servicio o de su VIP, mientras que `endpoints` identifica los backends de destino. El modo de resolución controla cómo busca el proxy, no el DNS de la aplicación; configura registros DNS o captura DNS para los hosts sintéticos. ServiceEntry no incorpora un proxy de VM ni emite sus credenciales de identidad.

ServiceEntry añade servicios externos al registro de servicios de Istio.

![Una aplicación dentro de la malla de servicios envía una solicitud mediante un registro ServiceEntry, que aplica controles de tráfico, supervisión y seguridad antes de distribuirla entre una API externa y una base de datos externa.](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-12-service-entry-1.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-12-service-entry-1.html)

### Estructura básica

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
spec:
  hosts:                  # External service hostname
  - api.example.com
  ports:                  # Port and protocol
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL # External/internal location
  resolution: DNS         # Address resolution method
```

## Modos de resolución {#resolution-modes}

La API de Istio 1.31 define cinco modos de resolución.

### 1. Resolución DNS

Es el modo más común: resuelve direcciones IP dinámicamente mediante DNS.

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api-dns
spec:
  hosts:
  - api.example.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS  # DNS lookup
```

**Casos de uso**:
- APIs públicas (AWS S3, Google Cloud Storage)
- Servicios SaaS (Stripe, SendGrid)
- Servicios administrados en la nube

### 2. Resolución STATIC

Especifica explícitamente direcciones IP fijas.

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api-static
spec:
  hosts:
  - legacy-api.company.internal
  addresses:
  - 10.10.10.10
  - 10.10.10.11
  ports:
  - number: 8080
    name: http
    protocol: HTTP
  location: MESH_EXTERNAL
  resolution: STATIC  # Fixed IP
  endpoints:
  - address: 10.10.10.10
  - address: 10.10.10.11
```

**Casos de uso**:
- Sistemas heredados sin DNS
- Requisitos de cumplimiento que exigen IP fijas
- Servicios de centros de datos internos

### 3. Resolución NONE

Este modo no resuelve direcciones: utiliza tal cual la dirección proporcionada por el cliente.

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: wildcard-api
spec:
  hosts:
  - "*.api.example.com"  # Wildcard
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: NONE  # No address resolution
```

**Casos de uso**:
- Dominios comodín
- Balanceo de carga del lado del cliente
- Proxy TCP/TLS

### 4. Resolución DNS_ROUND_ROBIN

Este modo es compatible y no está obsoleto. A diferencia del modo DNS, que obtiene el conjunto completo de endpoints, utiliza la primera dirección DNS al abrir una conexión nueva y mantiene las conexiones existentes aunque cambien los registros DNS. Es útil para servicios respaldados por DNS cuyos endpoints cambian a menudo y no deberían provocar el vaciado continuo de los grupos de conexiones.

### 5. Resolución DYNAMIC_DNS

Este modo resuelve un destino comodín a partir de HTTP Host/SNI en el momento de la solicitud. Su compatibilidad depende de la versión, del plano de datos y de la configuración de waypoint; no se aplica al tráfico TCP opaco del que no se puede recuperar el nombre del host. Comprueba los requisitos específicos del modo antes de utilizarlo. El ejemplo comodín concreto que aparece más abajo usa el modo NONE en un sidecar.

## Configuración de ubicación {#location-settings}

### MESH_EXTERNAL (servicio externo)

Registra servicios que están fuera de la malla.

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-service
spec:
  hosts:
  - external-api.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL  # External service
  resolution: DNS
```

**Características**:
- Es posible usar TLS/mTLS externo con un DestinationRule adecuado y la configuración de confianza del servidor
- El tráfico puede salir a través de Egress Gateway
- Se clasifica como tráfico externo

### MESH_INTERNAL (servicio interno)

Trata el servicio como interno de la malla (uso poco frecuente).

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: internal-vm-service
spec:
  hosts:
  - vm-service.internal
  ports:
  - number: 8080
    name: http
    protocol: HTTP
  location: MESH_INTERNAL  # Treat as internal service
  resolution: STATIC
  endpoints:
  - address: 10.0.0.5
    labels:
      app: vm-service
```

**Casos de uso**:
- Incorporar cargas de trabajo de VM a la malla
- Entornos multiclúster
- Configuraciones de nube híbrida

## Ejemplos prácticos {#practical-examples}

### 1. Registro de una API REST externa

#### Escenario: API de pasarela de pagos

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: payment-gateway-api
  namespace: production
spec:
  hosts:
  - api.payment-gateway.com
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
  resolution: DNS
---
# VirtualService: Timeout and Retry settings
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: payment-gateway-routing
  namespace: production
spec:
  hosts:
  - api.payment-gateway.com
  http:
  - match:
    - method:
        regex: "^(GET|HEAD)$"
    route:
    - destination:
        host: api.payment-gateway.com
    timeout: 10s
    retries:
      attempts: 3
      perTryTimeout: 3s
      retryOn: connect-failure,refused-stream
  - route:
    - destination:
        host: api.payment-gateway.com
    timeout: 10s
    retries:
      attempts: 0
---
# DestinationRule: Circuit Breaker
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: payment-gateway-circuit-breaker
  namespace: production
spec:
  host: api.payment-gateway.com
  trafficPolicy:
    connectionPool:
      http:
        http1MaxPendingRequests: 10
        maxRequestsPerConnection: 1
    outlierDetection:
      consecutive5xxErrors: 3
      interval: 30s
      baseEjectionTime: 120s
    tls:
      mode: SIMPLE
      sni: api.payment-gateway.com
      subjectAltNames: [api.payment-gateway.com]
```

En este diseño de originación, la aplicación envía HTTP al sidecar local y el proxy envía HTTPS verificado al servicio externo. No combines este diseño con HTTPS iniciado por la aplicación. Antes de habilitar reintentos para operaciones de pago de escritura, la aplicación debe contar con un contrato de idempotencia.

### 2. Registro de una base de datos externa

#### Escenario: AWS RDS MySQL

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: aws-rds-mysql
spec:
  hosts:
  - mydb.abc123.us-west-2.rds.amazonaws.com
  ports:
  - number: 3306
    name: tcp
    protocol: TCP
  location: MESH_EXTERNAL
  resolution: DNS
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: aws-rds-mysql-circuit-breaker
spec:
  host: mydb.abc123.us-west-2.rds.amazonaws.com
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 5s
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 60s
      baseEjectionTime: 60s
```

### 3. Registro de un dominio comodín

Configura TLS de RDS y la verificación del certificado en el controlador de la base de datos con el paquete de CA de RDS vigente. El registro TCP no configura la autenticación de la base de datos ni la negociación SSL. Para varias bases de datos externas que usan el mismo puerto, utiliza captura DNS o VIP de servicio únicas para evitar ambigüedades basadas solo en el puerto.

#### Escenario: acceso a un bucket de AWS S3

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: aws-s3-buckets
spec:
  hosts:
  - "*.s3.amazonaws.com"
  - "*.s3.us-west-2.amazonaws.com"
  - "s3.us-west-2.amazonaws.com"
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: NONE  # Use NONE for wildcards
```

El prefijo comodín solo puede ir al principio; enumera los sufijos de endpoint regionales reales en lugar de colocar `*` dentro del nombre. Este ejemplo es para sidecar y no cubre todas las familias de endpoints de S3 ni concede permisos de IAM.

### 4. Servicio externo con varios endpoints

#### Escenario: API multirregional

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: multi-region-api
spec:
  hosts:
  - api.global-service.com
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
  resolution: DNS
  endpoints:
  - address: us-west.api.global-service.com
    labels:
      region: us-west
  - address: eu-central.api.global-service.com
    labels:
      region: eu-central
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: multi-region-api
spec:
  host: api.global-service.com
  trafficPolicy:
    tls:
      mode: SIMPLE
      sni: api.global-service.com
      subjectAltNames: [api.global-service.com]
  subsets:
  - name: us-west
    labels:
      region: us-west
  - name: eu-central
    labels:
      region: eu-central
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: multi-region-routing
spec:
  hosts:
  - api.global-service.com
  http:
  - match:
    - headers:
        x-region:
          exact: us-west
    route:
    - destination:
        host: api.global-service.com
        subset: us-west
  - match:
    - headers:
        x-region:
          exact: eu-central
    route:
    - destination:
        host: api.global-service.com
        subset: eu-central
  - route:
    - destination:
        host: api.global-service.com
```

Ambos endpoints regionales deben ofrecer el mismo nombre de host canónico de la API y el certificado correspondiente. Cambiar solo el encabezado HTTP Host no cambia el endpoint DNS que selecciona el proxy. La aplicación utiliza HTTP localmente; como se muestra, el proxy origina TLS hacia el upstream.

### 5. Registro de un servicio TCP

#### Escenario: clúster Redis externo

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-redis
spec:
  hosts:
  - redis-primary.external-cluster.com
  addresses:
  - 203.0.113.10
  ports:
  - number: 6379
    name: tcp
    protocol: TCP
  location: MESH_EXTERNAL
  resolution: STATIC
  endpoints:
  - address: 203.0.113.10
    labels:
      instance: primary
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-redis-lb
spec:
  host: redis-primary.external-cluster.com
  trafficPolicy:
    loadBalancer:
      simple: ROUND_ROBIN
    connectionPool:
      tcp:
        maxConnections: 50
        connectTimeout: 3s
```

Este ejemplo selecciona únicamente el nodo principal de escritura. Registra los nodos réplica por separado para el tráfico de lectura o utiliza un cliente de clúster que entienda Redis; el balanceo round robin genérico no conserva la semántica de nodo principal/réplica ni de fragmentación de Redis. Sustituye las IP de ejemplo por endpoints accesibles.

## Combinación con Egress Gateway {#combining-with-egress-gateway}

Controla centralmente el tráfico externo mediante Egress Gateway.

### Configuración básica de Egress Gateway

```yaml
# ServiceEntry: Register external service
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
spec:
  hosts:
  - api.example.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
---
# Gateway: Egress Gateway configuration
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: egress-gateway
  namespace: istio-system
spec:
  selector:
    istio: egressgateway
  servers:
  - port:
      number: 443
      name: tls
      protocol: TLS
    hosts:
    - api.example.com
    tls:
      mode: PASSTHROUGH
---
# VirtualService: Mesh internal -> Egress Gateway
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: direct-api-through-egress
spec:
  hosts:
  - api.example.com
  gateways:
  - mesh
  - istio-system/egress-gateway
  tls:
  - match:
    - gateways:
      - mesh
      port: 443
      sniHosts:
      - api.example.com
    route:
    - destination:
        host: istio-egressgateway.istio-system.svc.cluster.local
        port:
          number: 443
  - match:
    - gateways:
      - istio-system/egress-gateway
      port: 443
      sniHosts:
      - api.example.com
    route:
    - destination:
        host: api.example.com
        port:
          number: 443
```

### Originación TLS (HTTP interno, HTTPS externo)

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-http-to-https
spec:
  hosts:
  - api.secure-service.com
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: originate-tls
spec:
  host: api.secure-service.com
  trafficPolicy:
    portLevelSettings:
    - port:
        number: 80
      tls:
        mode: SIMPLE  # HTTP -> HTTPS conversion
```

## Seguridad y TLS {#security-and-tls}

### mTLS con un servicio externo

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: mtls-external-service
spec:
  hosts:
  - mtls-api.example.com
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
  name: mtls-external-tls
spec:
  host: mtls-api.example.com
  trafficPolicy:
    tls:
      mode: MUTUAL
      sni: mtls-api.example.com
      subjectAltNames: [mtls-api.example.com]
      clientCertificate: /etc/certs/client-cert.pem
      privateKey: /etc/certs/client-key.pem
      caCertificates: /etc/certs/ca-cert.pem
```

Monta estos archivos de certificado y clave en el contenedor del proxy y rótalos mediante tu proceso de administración de certificados. El servidor externo debe confiar en la CA del cliente; ServiceEntry no emite estas credenciales. Este es mTLS originado por el proxy a partir de HTTP local, no una segunda capa sobre el TLS de la aplicación.

### Enrutamiento SNI

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: egress-sni-gateway
  namespace: istio-system
spec:
  selector:
    istio: egressgateway
  servers:
  - port:
      number: 443
      name: tls
      protocol: TLS
    hosts:
    - api.example.com
    - api2.example.com
    tls:
      mode: PASSTHROUGH
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: sni-routing
spec:
  hosts:
  - api.example.com
  - api2.example.com
  gateways:
  - mesh
  - istio-system/egress-sni-gateway
  tls:
  - match:
    - gateways:
      - mesh
      port: 443
      sniHosts:
      - api.example.com
    route:
    - destination:
        host: istio-egressgateway.istio-system.svc.cluster.local
        port:
          number: 443
  - match:
    - gateways:
      - istio-system/egress-sni-gateway
      port: 443
      sniHosts:
      - api.example.com
    route:
    - destination:
        host: api.example.com
        port:
          number: 443
  - match:
    - gateways:
      - mesh
      port: 443
      sniHosts:
      - api2.example.com
    route:
    - destination:
        host: istio-egressgateway.istio-system.svc.cluster.local
        port:
          number: 443
  - match:
    - gateways:
      - istio-system/egress-sni-gateway
      port: 443
      sniHosts:
      - api2.example.com
    route:
    - destination:
        host: api2.example.com
        port:
          number: 443
```

Instala la carga de trabajo de Egress Gateway y el servicio ClusterIP como se muestra en [Control de salida](11-egress-control.md), y registra ambos hosts externos mediante ServiceEntry. Las rutas SNI configuran el reenvío, pero no obligan a que todo el tráfico pase por la gateway; utiliza controles de red para imponer ese límite.

## Supervisión y control {#monitoring-and-control}

### Recopilación de métricas

```bash
# Check ServiceEntry traffic
kubectl exec -it <pod-name> -c istio-proxy -- \
  curl localhost:15000/stats/prometheus | grep "api.example.com"

# Egress traffic metrics
istio_requests_total{reporter="source",destination_service_name="api.example.com"}
```

### Consultas de Prometheus

Inspecciona las etiquetas de métricas reales antes de consultarlas. Las métricas HTTP de solicitudes, errores y latencia requieren visibilidad L7 (por ejemplo, originación TLS); HTTPS/TCP opaco solo expone métricas de conexiones y bytes. No des por sentado que el campo de espacio de nombres de un ServiceEntry externo está vacío.

```promql
# External service request count
sum(rate(istio_requests_total{reporter="source",destination_service_name="api.example.com"}[5m]))

# External service error rate
sum(rate(istio_requests_total{reporter="source",destination_service_name="api.example.com",response_code=~"5.."}[5m])) /
sum(rate(istio_requests_total{reporter="source",destination_service_name="api.example.com"}[5m]))

# External service response time
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket{reporter="source",destination_service_name="api.example.com"}[5m])) by (le)
)
```

### Detección de destinos no registrados

```yaml
# Registry/configuration control, not a firewall
apiVersion: networking.istio.io/v1
kind: Sidecar
metadata:
  name: default
  namespace: default
spec:
  egress:
  - hosts:
    - "./*"  # Allow only same namespace
    - "istio-system/*"  # Allow istio-system
  outboundTrafficPolicy:
    mode: REGISTRY_ONLY  # Known Kubernetes and ServiceEntry destinations
```

El ámbito de importación de sidecar y REGISTRY_ONLY no son límites de seguridad. Para exigir el control del tráfico de salida, utiliza políticas de red o firewalls, y AuthorizationPolicy cuando corresponda.

## Prácticas recomendadas {#best-practices}

### 1. Registra explícitamente cada ServiceEntry

```yaml
# Good example: Explicit registration
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: payment-api
  namespace: production
  annotations:
    description: "Payment gateway API"
    owner: "payments-team"
    sla: "99.9%"
spec:
  hosts:
  - api.payment.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

### 2. Ajusta la resiliencia al protocolo

```yaml
# Always apply Circuit Breaker for external services
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-api-protection
spec:
  host: api.example.com
  trafficPolicy:
    connectionPool:
      http:
        http1MaxPendingRequests: 10
        maxRequestsPerConnection: 1
    outlierDetection:
      consecutive5xxErrors: 3
      interval: 30s
      baseEjectionTime: 120s
```

### 3. Configura los tiempos de espera

```yaml
# Set explicit Timeout for external services
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-api-timeout
spec:
  hosts:
  - api.example.com
  http:
  - route:
    - destination:
        host: api.example.com
    timeout: 10s  # Explicit Timeout
    retries:
      attempts: 2
      perTryTimeout: 5s
```

### 4. Utiliza Egress Gateway en producción

```yaml
# Control external traffic through Egress Gateway in production
# - Centralized monitoring
# - Easy IP whitelist management
# - Consistent security policies
```

### 5. Configura la visibilidad entre espacios de nombres

```yaml
# Isolate ServiceEntry by namespace
apiVersion: networking.istio.io/v1
kind: Sidecar
metadata:
  name: default
  namespace: team-a
spec:
  egress:
  - hosts:
    - "team-a/*"  # Only own namespace
    - "istio-system/*"
    - "external/*"  # Shared external services
  outboundTrafficPolicy:
    mode: REGISTRY_ONLY
```

### 6. Plantilla de documentación

```yaml
# Metadata excerpt; replace illustrative SLA/cost values with the actual service contract
metadata:
  name: external-service
  annotations:
    # Service information
    service-description: "Third-party payment API"
    service-owner: "payments-team@company.com"
    service-documentation: "https://wiki.company.com/payment-api"

    # SLA information
    sla-availability: "99.9%"
    sla-latency-p95: "500ms"
    rate-limit: "1000 req/min"

    # Cost information
    cost-per-request: "$0.01"
    monthly-budget: "$10000"

    # Incident response
    oncall: "payments-oncall"
    escalation: "CTO"
    fallback-strategy: "Use cached data"
```

## Referencias

- [ServiceEntry de Istio](https://istio.io/latest/docs/reference/config/networking/service-entry/)
- [Tráfico de salida de Istio](https://istio.io/latest/docs/tasks/traffic-management/egress/)
- [Originación TLS de Istio](https://istio.io/latest/docs/tasks/traffic-management/egress/egress-tls-origination/)
- [Servicios externos de Envoy](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/service_discovery)

- [Referencia principal 1](https://istio.io/latest/docs/reference/config/networking/service-entry/)
- [Referencia principal 2](https://istio.io/latest/docs/ops/configuration/traffic-management/dns-proxy/)
- [Referencia principal 3](https://istio.io/latest/docs/reference/config/networking/sidecar/)
- [Referencia principal 4](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
- [Referencia principal 5](https://istio.io/latest/docs/tasks/traffic-management/egress/egress-gateway/)
- [Referencia principal 6](https://istio.io/latest/docs/tasks/traffic-management/egress/egress-tls-origination/)
- [Referencia principal 7](https://docs.aws.amazon.com/AmazonS3/latest/userguide/VirtualHosting.html)
- [Referencia principal 8](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.SSL.html)
