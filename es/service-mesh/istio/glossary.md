# Glosario de Istio

> **Versión revisada**: Istio 1.31.0
> **Última actualización**: September 13, 2026

Este glosario organiza los términos clave relacionados con Istio y las mallas de servicios en secciones de referencia agrupadas.

> **Idioma de referencia**: Los enlaces a secciones de las guías de Architecture y DestinationRule que aparecen a continuación apuntan a las versiones en inglés que se mantienen actualizadas. Estos enlaces ofrecen la referencia vigente cuando las traducciones locales aún no se han sincronizado.

## Índice

- [A-C](#a-c)
- [D-F](#d-f)
- [G-I](#g-i)
- [J-L](#j-l)
- [M-O](#m-o)
- [P-R](#p-r)
- [S-U](#s-u)
- [V-Z](#v-z)

---

## A-C {#a-c}

### AuthorizationPolicy {#authorizationpolicy}

Política de seguridad de Istio que define el comportamiento ALLOW, DENY, CUSTOM o AUDIT para cargas de trabajo o recursos de destino seleccionados. La autenticación y la autorización son independientes; las políticas de waypoint utilizan targetRefs.

### Plano de control {#control-plane}

Capa de configuración, descubrimiento y gestión de identidades implementada por istiod. Los datos de las aplicaciones circulan por los proxies del plano de datos, no por istiod.

### Modo Ambient {#ambient-mode}

Modo del plano de datos que se publicó primero como alpha en Istio 1.18 y está disponible de forma general desde Istio 1.24; proporciona funciones de malla de servicios sin proxies sidecar.

**Funciones**:
- No requiere contenedores sidecar
- Utiliza ztunnel a nivel de nodo
- Mayor eficiencia de recursos
- Separación de funciones L4 y L7

**Documentación relacionada**: [Modo Ambient](advanced/01-ambient-mode.md)

---

### Autoridad de certificación (CA) {#certificate-authority-ca}

Autoridad que emite y administra certificados para la comunicación mTLS entre servicios.

**Función en Istio**:
- La función Citadel de Istiod desempeña el papel de CA
- Emite certificados basados en SPIFFE ID
- Renovación automática de certificados (TTL predeterminado: 24 horas)

**Términos relacionados**: [Citadel](#citadel), [SPIFFE](#spiffe-secure-production-identity-framework-for-everyone), [mTLS](#mtls-mutual-tls)

---

### Circuit Breaker

Patrón que bloquea solicitudes hacia servicios averiados para impedir que los fallos se propaguen por todo el sistema.

**Funcionamiento**:
1. **Closed**: funcionamiento normal
2. **Open**: bloquea solicitudes tras fallos consecutivos
3. **Half-Open**: permite algunas solicitudes después de cierto tiempo

**Implementación en Istio**: la limitación de los pools de conexiones y la expulsión de endpoints anómalos no exponen literalmente esta máquina de tres estados.
```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: glossary-example-1
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
```

**Documentación relacionada**: [Circuit Breaker](traffic-management/07-circuit-breaker.md)

---

### Citadel {#citadel}

Componente de seguridad que existía de forma independiente hasta Istio 1.4 inclusive. Actualmente está integrado en Istiod.

**Funciones principales**:
- Gestión de la autoridad de certificación (CA)
- Emisión y gestión de SPIFFE ID
- Generación y renovación de certificados X.509

**Estado actual**: existe como función interna de Istiod en Istio 1.5+

**Términos relacionados**: [Istiod](#istiod), [Autoridad de certificación](#certificate-authority-ca)

---

### CDS (Cluster Discovery Service) {#cds-cluster-discovery-service}

Una de las API xDS que permite a Envoy recibir dinámicamente la configuración de servicios ascendentes (clústeres).

**Información proporcionada**:
- Nombre y tipo del clúster
- Política de equilibrio de carga
- Ajustes de comprobación de salud
- Ajustes de circuit breaker
- Ajustes TLS

**Términos relacionados**: [xDS](#xds-discovery-service), [Envoy](#envoy-proxy)

---

## D-F {#d-f}

### Plano de datos

Capa que gestiona el tráfico real de una malla de servicios.

**Plano de datos de Istio**:
- Sidecars Envoy, o ztunnel de ambient más waypoints L7 opcionales
- Gestiona el tráfico incorporado a la malla; se aplican exclusiones y límites de protocolo
- Cifrado/descifrado mTLS
- Recopilación de métricas

**Términos relacionados**: [Plano de control](#control-plane), [Envoy](#envoy-proxy)

---

### DestinationRule

CRD de Istio que define políticas para el tráfico enrutado por VirtualService.

**Funciones principales**:
- Definición de subconjuntos (versión, región, etc.)
- Política de equilibrio de carga
- Ajustes del pool de conexiones
- Ajustes de circuit breaker
- Ajustes TLS

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

**Documentación relacionada**: [DestinationRule](traffic-management/03-destination-rule.md)

---

### eBPF (Extended Berkeley Packet Filter) {#ebpf-extended-berkeley-packet-filter}

Tecnología que permite ejecutar programas de forma segura dentro del kernel de Linux.

Istio puede coexistir con un CNI principal basado en eBPF, como Cilium. Istio CNI es un plugin encadenado/agente de nodo independiente que configura la redirección; ambient no requiere eBPF ni sustituye al CNI principal.

**Ventajas**:
- Baja sobrecarga
- Procesamiento a nivel de kernel
- Capacidad de programación dinámica

**Términos relacionados**: [Modo Ambient](#ambient-mode), [iptables](#iptables)

---

### EDS (Endpoint Discovery Service) {#eds-endpoint-discovery-service}

Una de las API xDS que proporciona dinámicamente los endpoints reales (IP de Pods) de un clúster.

**Información proporcionada**:
- Direcciones IP y puertos de endpoints
- Estado de salud
- Pesos de equilibrio de carga
- Información de localidad

**Ejemplo**:
```json
{
  "cluster_name": "outbound|9080||reviews",
  "endpoints": [
    {
      "lb_endpoints": [
        {"endpoint": {"address": {"socket_address": {"address": "10.244.1.5", "port_value": 9080}}}},
        {"endpoint": {"address": {"socket_address": {"address": "10.244.2.8", "port_value": 9080}}}}
      ]
    }
  ]
}
```

**Términos relacionados**: [xDS](#xds-discovery-service), [CDS](#cds-cluster-discovery-service)

---

### Proxy Envoy {#envoy-proxy}

Proxy L7 de alto rendimiento que forma el plano de datos de Istio.

**Historia**:
- Desarrollado por Matt Klein en Lyft en 2016
- Proyecto en incubación de CNCF en 2017
- Proyecto graduado de CNCF en 2018

**Características principales**:
- Proxy de alto rendimiento escrito en C++
- Configuración dinámica mediante la API xDS
- Compatibilidad con HTTP/1.1, HTTP/2 y gRPC
- Amplias funciones de observabilidad

**Componentes**:
- Listeners: escucha de puertos
- Filtros: procesamiento de solicitudes/respuestas
- Routers: decisiones de enrutamiento
- Clústeres: servicios ascendentes

**Documentación relacionada**: [Arquitectura - Proxy Envoy](https://www.atomai.click/kubernetes-docs/en/service-mesh/istio/03-architecture#data-plane-envoy-proxy)

---

## G-I {#g-i}

### Galley

Componente de validación de configuración que existía de forma independiente hasta Istio 1.4 inclusive. Actualmente está integrado en Istiod.

**Funciones principales**:
- Validación de la configuración de Istio
- Procesamiento de recursos Kubernetes
- Comprobación de errores antes de desplegar la configuración

**Estado actual**: existe como función interna de Istiod en Istio 1.5+

**Términos relacionados**: [Istiod](#istiod)

---

### Gateway

CRD de Istio que define los puntos de entrada del tráfico externo a la malla de servicios.

**Tipos**:
1. **Ingress Gateway**: tráfico del exterior al interior
2. **Egress Gateway**: tráfico del interior al exterior

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
    - "example.com"
```

**Documentación relacionada**: [Gateway y VirtualService](traffic-management/01-gateway-virtualservice.md)

---

### gRPC

Framework RPC (llamada a procedimiento remoto) de alto rendimiento desarrollado por Google.

**Relación con Istio**:
- La API xDS está basada en gRPC
- Se utiliza para la comunicación de Istiod con Envoy
- Basado en HTTP/2 (admite multiplexación)

**Ventajas**:
- Streaming bidireccional
- Baja latencia
- Utiliza Protocol Buffers

**Términos relacionados**: [xDS](#xds-discovery-service)

---

### Identidad {#identity}

Representa la identidad de una carga de trabajo dentro de la malla de servicios.

**Identidad en Istio**:
- Utiliza el formato SPIFFE ID
- Se basa en ServiceAccount de Kubernetes
- Se demuestra mediante certificados X.509

**Ejemplo**:
```
spiffe://cluster.local/ns/default/sa/reviews
```

**Términos relacionados**: [SPIFFE](#spiffe-secure-production-identity-framework-for-everyone), [mTLS](#mtls-mutual-tls)

---

### iptables {#iptables}

Herramienta de cortafuegos que controla el tráfico de red en Linux.

**Función en Istio**:
- istio-init o el agente de nodo Istio CNI configura la redirección del tráfico
- Redirige todo el tráfico del Pod a Envoy
- Utiliza la tabla NAT (cadenas PREROUTING y OUTPUT)

**Reglas simplificadas (ilustración, no un script de instalación)**:
```bash
# Outbound: All traffic except Envoy -> 15001
iptables -t nat -A OUTPUT -p tcp -m owner ! --uid-owner 1337 -j REDIRECT --to-port 15001

# Inbound: All traffic -> 15006
iptables -t nat -A PREROUTING -p tcp -j REDIRECT --to-port 15006
```

**Alternativa de configuración**: Istio CNI realiza la configuración de red con privilegios a nivel de nodo.

**Documentación relacionada**: [Arquitectura - iptables](https://www.atomai.click/kubernetes-docs/en/service-mesh/istio/03-architecture#iptables-and-traffic-interception)

---

### Istiod {#istiod}

Componente unificado del plano de control en Istio 1.5+.

**Funciones integradas**:
- **Pilot**: descubrimiento de servicios y gestión de tráfico
- **Citadel**: autoridad de certificación e identidad
- **Galley**: validación de configuración

**Método de ejecución**:
- Un único binario Go: `pilot-discovery`
- Todas las funciones se ejecutan dentro de un solo proceso
- Puertos predeterminados: 15012 (xDS), 15017 (Webhook)

**Ventajas**:
- Menor complejidad
- Operaciones simplificadas
- Eficiencia de recursos

**Documentación relacionada**: [Arquitectura - Istiod](https://www.atomai.click/kubernetes-docs/en/service-mesh/istio/03-architecture#control-plane-istiod)

---

## J-L {#j-l}

### LDS (Listener Discovery Service) {#lds-listener-discovery-service}

Una de las API xDS que permite a Envoy recibir dinámicamente los puertos de escucha y las cadenas de filtros.

**Información proporcionada**:
- Dirección y puerto del listener
- Protocolo (HTTP, TCP)
- Configuración de la cadena de filtros
- Ajustes TLS

**Listeners predeterminados de Istio**:
- `0.0.0.0:15001`: TCP saliente
- `0.0.0.0:15006`: TCP entrante
- `0.0.0.0:15021`: comprobación de salud
- `0.0.0.0:15090`: métricas Prometheus

**Términos relacionados**: [xDS](#xds-discovery-service), [Envoy](#envoy-proxy)

---

### Equilibrio de carga consciente de la localidad {#locality-aware-load-balancing}

Método de equilibrio de carga que considera información de localidad (región, zona).

**Prioridad**:
1. Endpoints de la misma zona
2. Otra zona de la misma región
3. Otra región

**Ejemplo de configuración**:
```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: glossary-example-2
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-west/zone-1a/*
          to:
            "us-west/zone-1a/*": 80
            "us-west/zone-1b/*": 20
```

**Documentación relacionada**: [Enrutamiento consciente de zonas](resilience/03-zone-aware-routing.md)

---

## M-O {#m-o}

### Mixer

Componente de políticas y telemetría que existía hasta Istio 1.4 inclusive.

**Funciones principales**:
- Aplicación de políticas (limitación de tasa, control de acceso)
- Recopilación de telemetría

**Motivos de eliminación**:
- Sobrecarga de rendimiento (llamada a Mixer en cada solicitud)
- Arquitectura compleja

**Estado actual**: quedó obsoleto durante la transición a 1.5; las funciones restantes de Mixer se eliminaron en 1.8

**Términos relacionados**: [Istiod](#istiod)

---

### mTLS (TLS mutuo) {#mtls-mutual-tls}

Método de comunicación TLS bidireccional en el que el cliente y el servidor se autentican mutuamente.

**mTLS de Istio**:
- Emisión y renovación automática de certificados
- Autenticación basada en SPIFFE ID
- El cifrado TLS se negocia; no está fijado a AES-256-GCM

**Modos**:
1. **STRICT**: solo permite mTLS
2. **PERMISSIVE**: permite mTLS y texto sin cifrar (para migraciones)
3. **DISABLE**: deshabilita el mTLS de transporte de Istio en modo sidecar; no se admite en ambient

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: STRICT
```

**Documentación relacionada**: [mTLS](security/01-mtls.md)

---

### Detección de endpoints anómalos

Función que excluye automáticamente los endpoints que presentan un comportamiento anómalo.

**Condiciones de detección**:
- Número de errores consecutivos
- Tasa de errores
- Fallos de conexión/tiempos de espera agotados; la latencia por sí sola no es un umbral de expulsión de endpoints anómalos

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: glossary-example-3
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

**Documentación relacionada**: [Detección de endpoints anómalos](resilience/01-outlier-detection.md)

---

## P-R {#p-r}

### Downstream {#downstream}

Desde la perspectiva de Envoy, se refiere a **la parte que envía solicitudes**, es decir, el cliente que inicia una conexión con Envoy.

**Downstream de Envoy**:
- Conexiones que entran en Envoy (entrantes)
- Cliente que envía solicitudes
- Conexiones recibidas por el listener

**Flujo de tráfico**:
```
Downstream (Client)  ->  Envoy Proxy  ->  Upstream (Backend)
```

**Escenarios de ejemplo**:

#### 1. Modo sidecar - Solicitud saliente

![En modo sidecar, la aplicación (downstream) envía una solicitud al sidecar Envoy del mismo Pod, y Envoy la reenvía al servicio backend (upstream).](../../.gitbook/assets/en-service-mesh-istio-glossary-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-glossary-0.html)

**Perspectiva**:
- **Desde Envoy**: la aplicación es downstream (envía solicitudes)
- **Desde Envoy**: el servicio backend es upstream (recibe solicitudes)

#### 2. Ingress Gateway - Solicitud externa

![Desde la perspectiva del Envoy de Ingress Gateway, un cliente externo es downstream y el servicio interno al que enruta es upstream.](../../.gitbook/assets/en-service-mesh-istio-glossary-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-glossary-1.html)

**Configuración de Envoy relacionada con downstream**:

```yaml
# Listener - Receive Downstream connections
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: downstream-config
  namespace: default
spec:
  workloadSelector:
    labels:
      app: reviews
  configPatches:
  - applyTo: LISTENER
    match:
      context: SIDECAR_INBOUND
    patch:
      operation: MERGE
      value:
        per_connection_buffer_limit_bytes: 32768  # Downstream buffer
```

**Métricas downstream**:
```bash
# Downstream connection count
envoy_listener_downstream_cx_active

# Downstream request count
envoy_http_downstream_rq_total

# Downstream response time
envoy_http_downstream_rq_time
```

**Términos relacionados**: [Upstream](#upstream), [Envoy](#envoy-proxy), [Listener](#lds-listener-discovery-service)

---

### Upstream {#upstream}

Desde la perspectiva de Envoy, se refiere a **la parte que recibe solicitudes**, es decir, el servicio backend con el que Envoy inicia una conexión.

**Upstream de Envoy**:
- Conexiones que salen de Envoy (salientes)
- Servicio backend que procesa solicitudes
- Endpoints administrados por un Cluster

**Flujo de tráfico**:
```
Downstream (Client)  ->  Envoy Proxy  ->  Upstream (Backend)
```

**Componentes upstream**:

#### 1. Cluster (grupo upstream)

```yaml
# Define Upstream Cluster with DestinationRule
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews  # Upstream service
  trafficPolicy:
    loadBalancer:
      simple: ROUND_ROBIN
    connectionPool:
      tcp:
        maxConnections: 100      # Upstream connection limit
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
    outlierDetection:
      consecutive5xxErrors: 5        # Upstream failure detection
      interval: 30s
```

#### 2. Endpoint (instancia upstream real)

```bash
# Check upstream endpoints
istioctl proxy-config endpoints <pod-name> | grep reviews

# Example output:
# ENDPOINT              STATUS      CLUSTER
# 10.244.1.5:9080       HEALTHY     outbound|9080||reviews.default.svc.cluster.local
# 10.244.2.8:9080       HEALTHY     outbound|9080||reviews.default.svc.cluster.local
# 10.244.3.12:9080      UNHEALTHY   outbound|9080||reviews.default.svc.cluster.local
```

**Política de tráfico upstream**:

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: glossary-example-4
spec:
  host: reviews
  trafficPolicy:
    # Upstream load balancing
    loadBalancer:
      consistentHash:
        httpHeaderName: "x-user-id"

    # Upstream connection pool
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 30s
      http:
        h2UpgradePolicy: UPGRADE

    # Upstream TLS
    tls:
      mode: ISTIO_MUTUAL

    # Upstream Circuit Breaker
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
```

**Comparación de upstream y downstream**:

| Elemento | Downstream | Upstream |
|------|-----------|----------|
| **Dirección** | Entra en Envoy (entrante) | Sale de Envoy (saliente) |
| **Función** | Envía solicitudes (cliente) | Recibe solicitudes (servidor) |
| **Configuración de Envoy** | Listener, cadena de filtros | Cluster, Endpoint |
| **Ejemplos** | Usuarios externos, otros servicios | API backend, base de datos |
| **Métricas** | `downstream_cx_*`, `downstream_rq_*` | `upstream_cx_*`, `upstream_rq_*` |

**Ejemplos reales**:

#### Escenario 1: llamada de Service A -> Service B

```
+---------------------------------------------------------+
| Service A Pod                                           |
|                                                         |
|  App --> Envoy Sidecar                                 |
|          |                                              |
|          | Downstream: App                              |
|          | Upstream: Service B                          |
+----------|-------------------------------------------------+
           |
           v
+---------------------------------------------------------+
| Service B Pod                                           |
|                                                         |
|          Envoy Sidecar --> App                          |
|          |                                              |
|          | Downstream: Service A Envoy                  |
|          | Upstream: Local App (Service B)              |
+---------------------------------------------------------+
```

**Perspectiva del Envoy de Service A**:
- Downstream: aplicación de Service A
- Upstream: Service B

**Perspectiva del Envoy de Service B**:
- Downstream: Envoy de Service A
- Upstream: aplicación de Service B (local)

#### Escenario 2: Ingress Gateway

```
External Client (Downstream)
        |
Ingress Gateway (Envoy)
        |
Internal Service (Upstream)
```

**Métricas upstream**:

```bash
# Upstream connection count
envoy_cluster_upstream_cx_active

# Upstream request counter; derive success/error rates from response-class counters
envoy_cluster_upstream_rq_total

# Upstream response time
envoy_cluster_upstream_rq_time

# Upstream health check
envoy_cluster_health_check_success

# Upstream Circuit Breaker
envoy_cluster_circuit_breakers_default_remaining_rq
```

**Detección pasiva de salud upstream**: las estadísticas de comprobación activa de salud requieren configuración separada.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: glossary-example-5
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      # Upstream health detection
      consecutiveGatewayErrors: 5
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

**Depuración**:

```bash
# 1. Check upstream cluster
istioctl proxy-config clusters <pod-name> --fqdn reviews.default.svc.cluster.local

# 2. Check upstream endpoint status
istioctl proxy-config endpoints <pod-name> --cluster "outbound|9080||reviews.default.svc.cluster.local"

# 3. Check upstream metrics
kubectl exec <pod-name> -c istio-proxy -- \
  curl -s localhost:15000/stats/prometheus | grep upstream

# 4. Check upstream connections
istioctl proxy-config all <pod-name> -o json | \
  jq '.configs[] | select(.["@type"] | contains("ClustersConfigDump"))'
```

**Términos relacionados**: [Downstream](#downstream), [Envoy](#envoy-proxy), [Cluster](#cds-cluster-discovery-service), [Endpoint](#eds-endpoint-discovery-service)

---

### Pilot

Componente de gestión de tráfico que existía de forma independiente hasta Istio 1.4 inclusive. Actualmente está integrado en Istiod.

**Funciones principales**:
- Descubrimiento de servicios
- Gestión de tráfico (procesamiento de VirtualService y DestinationRule)
- Servidor xDS

**Estado actual**: existe como función interna de Istiod en Istio 1.5+

**Términos relacionados**: [Istiod](#istiod), [xDS](#xds-discovery-service)

---

### RDS (Route Discovery Service)

Una de las API xDS que proporciona dinámicamente reglas de enrutamiento HTTP.

**Información proporcionada**:
- Reglas de coincidencia de rutas (ruta, cabeceras, etc.)
- Enrutamiento basado en pesos
- Reglas de redirección y reescritura
- Ajustes de tiempo de espera y reintentos

**Relación con VirtualService**:
- VirtualService -> conversión por Istiod -> configuración RDS

**Términos relacionados**: [xDS](#xds-discovery-service), [VirtualService](#virtualservice)

---

### Limitación de tasa

Función que limita el número de solicitudes permitidas por unidad de tiempo.

**Métodos de implementación**:
1. **Limitación de tasa local**: Envoy la procesa localmente
2. **Limitación de tasa global**: utiliza un servicio externo de limitación de tasa

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: filter-local-ratelimit
  namespace: default
spec:
  workloadSelector:
    labels:
      app: reviews
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
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
          "@type": type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 100
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
```

**Documentación relacionada**: [Limitación de tasa](resilience/02-rate-limiting.md)

---

## S-U {#s-u}

### SDS (Secret Discovery Service)

Una de las API xDS que proporciona dinámicamente certificados y claves TLS.

**Información proporcionada**:
- Certificados X.509
- Clave privada
- Certificado raíz de CA

**Ventajas**:
- No requiere sistema de archivos
- Renovación automática de certificados
- Renovación sin interrupciones

**Términos relacionados**: [xDS](#xds-discovery-service), [mTLS](#mtls-mutual-tls)

---

### Service Entry {#service-entry}

CRD de Istio que registra en la malla servicios externos a ella.

**Casos de uso**:
- Control de acceso a API externas
- Aplicar funciones de Istio a servicios externos (reintentos, tiempos de espera, etc.)
- Integración con Egress Gateway

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
spec:
  hosts:
  - api.external.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

**Documentación relacionada**: [ServiceEntry](traffic-management/12-service-entry.md)

---

### Malla de servicios

Capa de infraestructura que gestiona la comunicación entre microservicios.

**Funciones principales**:
- Gestión de tráfico (enrutamiento, equilibrio de carga)
- Seguridad (mTLS, autenticación/autorización)
- Observabilidad (métricas, registros, trazas)
- Resiliencia (reintentos, circuit breaker)

**Implementaciones principales**:
- Istio
- Linkerd
- Consul Connect
- AWS App Mesh ([el soporte finaliza el September 30, 2026](https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html))

---

### SigV4 (AWS Signature Version 4)

Protocolo de firma para autenticar solicitudes a API de AWS.

**Funcionamiento**:

![Diagrama de secuencia que muestra cómo Envoy firma de forma transparente una solicitud saliente del cliente con credenciales AWS SigV4 antes de reenviarla a un servicio AWS y devolver la respuesta.](../../.gitbook/assets/en-service-mesh-istio-glossary-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-glossary-2.html)

**Componentes de la firma**:

1. **Canonical Request**: formato normalizado de la solicitud
   - Método HTTP
   - Ruta URI
   - Cadena de consulta
   - Cabeceras
   - Hash del payload

2. **String to Sign**: cadena que se va a firmar
   - Algoritmo: `AWS4-HMAC-SHA256`
   - Marca temporal
   - Alcance de las credenciales
   - Hash de Canonical Request

3. **Signing Key**: cálculo de la clave de firma
   ```
   HMAC(HMAC(HMAC(HMAC("AWS4" + SecretKey, Date), Region), Service), "aws4_request")
   ```

4. **Signature**: firma final
   ```
   HMAC(SigningKey, StringToSign)
   ```

**Integración con Istio**:

Los SDK de AWS y AWS CLI firman solicitudes HTTPS utilizando credenciales temporales proporcionadas por IRSA o EKS Pod Identity. Esto mantiene la firma asociada a los permisos AWS de la carga de trabajo. La identidad mTLS de Istio y la identidad IAM de AWS son independientes.

El filtro HTTP `aws_request_signing` de Envoy es una alternativa avanzada. Necesita una compilación de Envoy que incluya la extensión, credenciales disponibles para el **contenedor del proxy**, el servicio y la región AWS correctos y una coincidencia de filtro restringida al destino AWS previsto. Insértelo antes del router y después de cualquier reescritura de cabeceras o rutas que afecte a la firma. El HTTPS originado por la aplicación es opaco para este filtro HTTP: Envoy no puede añadir una firma dentro del TLS cifrado. Un diseño de firma mediante proxy debe presentar HTTP al proxy firmante y originar TLS verificado hacia el servidor upstream; evite originar TLS dos veces o exponer HTTP sin firmar fuera de la ruta local del proxy prevista.

El diagrama anterior describe esta ruta de proxy firmante configurada explícitamente, no una capacidad predeterminada de Istio. Una anotación IRSA en el ServiceAccount de la aplicación no demuestra por sí sola que un gateway o sidecar disponga del entorno de credenciales y del montaje de token necesarios.

**La autenticación no es validación JWT**:

SigV4 es una firma HMAC de solicitudes, no un JWT. `https://sts.amazonaws.com/.well-known/jwks` no es un endpoint de emisor JWT para validar firmas de API AWS. RequestAuthentication de Istio valida JWT de un emisor OIDC real. Una AuthorizationPolicy CUSTOM también requiere un servicio `extensionProviders` configurado que implemente autorización externa; no puede validar SigV4 sin esa implementación. Prefiera endpoints AWS autenticados mediante IAM o el SDK de AWS para acceder a API AWS.

**Ejemplo de verificación de solo lectura** (AWS CLI instalada en la carga de trabajo, con su rol IAM previsto):

```bash
aws sts get-caller-identity
aws s3api head-object --bucket my-bucket --key object.txt --region us-west-2
```

**Consideraciones operativas**:

- Conceda a la carga de trabajo únicamente las acciones y recursos AWS necesarios. Evite depender de un rol de instancia de nodo compartido.
- Confirme que el proveedor de credenciales elegido admite credenciales temporales y su renovación. La duración de la sesión es configurable, no es universalmente de una hora.
- Los eventos de administración y de datos de CloudTrail tienen coberturas distintas; acceder a objetos S3 requiere la configuración de eventos de datos apropiada.
- Inspeccione la configuración del proxy para confirmar la ubicación del filtro. Un volcado de configuración no muestra la cabecera Authorization de cada solicitud real, y un curl sin firmar sobre HTTPS no es una prueba de SigV4.
- Mida la sobrecarga de firma, almacenamiento en búfer y obtención de credenciales con los tamaños reales de solicitud; no se garantiza una sobrecarga fija en milisegundos.

**Términos relacionados**: [AuthorizationPolicy](#authorizationpolicy), [ServiceEntry](#service-entry), [EnvoyFilter](advanced/03-envoy-filter.md)

**Referencias**:
- [AWS Signature Version 4](https://docs.aws.amazon.com/general/latest/gr/signature-version-4.html)
- [Firma de solicitudes AWS de Envoy](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/aws_request_signing_filter)
- [Integración con AWS](04-aws-integration.md)

---

### Sidecar

Patrón de contenedor auxiliar desplegado junto a un contenedor de aplicación.

**Sidecar de Istio**:
- Nombre del contenedor: `istio-proxy`
- Imagen: `istio/proxyv2`
- Ejecuta el proxy Envoy
- Intercepta el tráfico configurado mediante la redirección del contenedor de inicialización o de Istio CNI

**Métodos de inyección**:
1. **Automático**: etiqueta del espacio de nombres
2. **Manual**: `istioctl kube-inject`

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: example-mesh
  labels:
    istio-injection: enabled  # Automatic injection
```

**Documentación relacionada**: [Inyección de sidecars](advanced/07-sidecar-injection.md)

---

### Recurso Sidecar

CRD de Istio que limita la información de servicios que recibe Envoy.

**Objetivo**:
- Reducir el uso de memoria
- Acortar el tiempo de envío de configuración
- Delimitar la configuración; no es una frontera de seguridad de red

```yaml
apiVersion: networking.istio.io/v1
kind: Sidecar
metadata:
  name: default
  namespace: default
spec:
  egress:
  - hosts:
    - "./*"  # Same namespace only
    - "istio-system/*"
```

**Efecto**:
- Importar menos servicios puede reducir la memoria y el trabajo de configuración; mida el ahorro real.

**Documentación relacionada**: [Arquitectura - Recurso Sidecar](https://www.atomai.click/kubernetes-docs/en/service-mesh/istio/03-architecture#optimization-with-sidecar-resource)

---

### SPIFFE (Secure Production Identity Framework for Everyone) {#spiffe-secure-production-identity-framework-for-everyone}

Estándar para demostrar la identidad de cargas de trabajo en entornos nativos de la nube.

**Formato de SPIFFE ID**:
```
spiffe://trust-domain/path
```

**Ejemplo de Istio**:
```
spiffe://cluster.local/ns/default/sa/reviews
  |         |           |     |      |    |
  |         |           |     |      |    +- ServiceAccount name
  |         |           |     |      +----- "sa" (ServiceAccount)
  |         |           |     +------------ Namespace name
  |         |           +------------------ "ns" (Namespace)
  |         +------------------------------ Trust Domain
  +---------------------------------------- Protocol
```

**Componentes**:
- **SPIFFE ID**: identificador de carga de trabajo
- **SVID (SPIFFE Verifiable Identity Document)**: X.509-SVID o JWT-SVID; mTLS de Istio utiliza X.509-SVID

**Términos relacionados**: [Identidad](#identity), [mTLS](#mtls-mutual-tls)

---

### Subconjunto

Agrupación lógica de servicios definida en DestinationRule.

**Usos habituales**:
- Por versión: `v1`, `v2`, `v3`
- Por etapa del despliegue: `stable`, `canary`, `test`
- Por región: `us-west`, `us-east`, `eu-central`

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: glossary-example-6
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

**Documentación relacionada**: [DestinationRule - Concepto de subconjunto](https://www.atomai.click/kubernetes-docs/en/service-mesh/istio/traffic-management/03-destination-rule#subset-concept)

---

## V-Z {#v-z}

### Proxy waypoint {#waypoint-proxy}

Proxy opcional que proporciona funciones L7 en modo Ambient.

**Función**:
- Se selecciona mediante etiquetas de espacio de nombres, Service o Pod; no automáticamente por ServiceAccount
- Basado en el proxy Envoy
- Dedicado a funciones de gestión de tráfico L7
- Funciona junto con ztunnel

**Funciones proporcionadas**:
- Enrutamiento L7 (basado en rutas y cabeceras)
- Reintentos y tiempos de espera
- Circuit breaker
- Inyección de fallos
- Manipulación de cabeceras

**Ejemplo de despliegue**:
```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: reviews-waypoint
  namespace: default
spec:
  gatewayClassName: istio-waypoint
  listeners:
  - name: mesh
    port: 15008
    protocol: HBONE
```

**Características**:
- ztunnel solo gestiona L4; waypoint gestiona L7
- Uso selectivo solo para los servicios que lo necesitan
- Mayor eficiencia de recursos que sidecar (enfoque compartido)
- Se selecciona mediante etiquetas de espacio de nombres, Service o Pod; no automáticamente por ServiceAccount

**Términos relacionados**: [Modo Ambient](#ambient-mode), [ztunnel](#ztunnel-zero-trust-tunnel)

---

Después de crear el waypoint, incorpore el servicio previsto, por ejemplo con `kubectl label service reviews istio.io/use-waypoint=reviews-waypoint --overwrite`. Desplegar un Gateway por sí solo no enruta el tráfico a través de él.

### VirtualService {#virtualservice}

CRD de Istio que define cómo se enruta el tráfico dentro de la malla de servicios.

**Funciones principales**:
- Enrutamiento basado en URI, cabeceras y parámetros de consulta
- Distribución del tráfico basada en pesos
- Ajustes de reintentos y tiempos de espera
- Inyección de fallos

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

**Documentación relacionada**: [Gateway y VirtualService](traffic-management/01-gateway-virtualservice.md)

---

### WASM (WebAssembly)

Formato de instrucciones binarias diseñado para ejecutarse en navegadores web. En Istio se utiliza para ampliar las funciones del proxy Envoy.

**Uso en Istio**:
- Añadir lógica personalizada como filtro Envoy
- Ampliar funciones dinámicamente sin volver a desplegar
- Puede escribirse en varios lenguajes (Rust, C++, Go, etc.)
- Se ejecuta de forma segura en un entorno sandbox

**Casos de uso principales**:
1. **Autenticación/autorización personalizada**: implementar lógica de negocio compleja
2. **Transformación de solicitudes/respuestas**: manipulación de cabeceras y transformación del payload
3. **Enrutamiento avanzado**: lógica de enrutamiento personalizada
4. **Recopilación de métricas**: telemetría especializada

Las URL de registro, los digests, las credenciales y los campos pluginConfig siguientes son marcadores de posición para un plugin que usted haya compilado; Istio no proporciona esas imágenes de ejemplo ni interpreta opciones específicas del plugin. Un módulo file:// debe existir dentro del contenedor del proxy.

**Ejemplo de plugin WASM**:
```yaml
apiVersion: extensions.istio.io/v1alpha1
kind: WasmPlugin
metadata:
  name: custom-auth
  namespace: istio-system
spec:
  selector:
    matchLabels:
      istio: ingressgateway
  url: oci://ghcr.io/my-org/custom-auth:v1.0.0
  phase: AUTHN
  pluginConfig:
    api_key_header: "X-API-Key"
    validate_endpoint: "https://auth.example.com/validate"
```

**Métodos de despliegue**:

#### 1. Despliegue mediante registro OCI (recomendado)

```yaml
apiVersion: extensions.istio.io/v1alpha1
kind: WasmPlugin
metadata:
  name: rate-limiter
spec:
  url: oci://ghcr.io/my-org/rate-limit:v1.0.0
  imagePullPolicy: Always
  imagePullSecret: registry-credential
```

#### 2. Despliegue mediante URL HTTP

```yaml
apiVersion: extensions.istio.io/v1alpha1
kind: WasmPlugin
metadata:
  name: custom-filter
spec:
  url: https://example.com/filters/custom-filter.wasm
  # Add sha256: with the actual 64-character module digest before deployment
```

#### 3. Despliegue desde archivo local

```yaml
apiVersion: extensions.istio.io/v1alpha1
kind: WasmPlugin
metadata:
  name: local-filter
spec:
  url: file:///etc/istio/filters/custom.wasm
```

**Ejemplo de desarrollo WASM (Rust)**:

```rust
use proxy_wasm::traits::*;
use proxy_wasm::types::*;

proxy_wasm::main! {{
    proxy_wasm::set_http_context(|_, _| -> Box<dyn HttpContext> {
        Box::new(CustomFilter)
    });
}}

struct CustomFilter;
impl Context for CustomFilter {}

impl HttpContext for CustomFilter {
    fn on_http_request_headers(&mut self, _: usize, _: bool) -> Action {
        // Demonstrate header mutation, not production API-key authentication.
        self.set_http_request_header("x-mesh-demo", Some("wasm"));
        Action::Continue
    }
}
```

**Requisitos de compilación y despliegue**:

Utilice un crate Rust `cdylib` con una dependencia `proxy-wasm` compatible y una versión de dependencia bloqueada. El callback anterior sigue el [ejemplo oficial del SDK Rust](https://github.com/proxy-wasm/proxy-wasm-rust-sdk/tree/main/examples/http_headers). Instale el destino `wasm32-unknown-unknown`, compile el módulo y empaquete el `.wasm` resultante en una imagen OCI Wasm compatible antes de referenciarla desde WasmPlugin. Un `docker build` genérico sin Dockerfile no realiza ese empaquetado.

```bash
rustup target add wasm32-unknown-unknown
cargo build --target wasm32-unknown-unknown --release
```

Mida el tiempo de inicio, la memoria y la sobrecarga por solicitud del plugin concreto. Wasm se ejecuta en un sandbox del entorno de ejecución dentro del proceso del proxy; no es un proceso separado ni una garantía incondicional de seguridad o rendimiento.

**Compatibilidad con modo Ambient**:

```yaml
apiVersion: extensions.istio.io/v1alpha1
kind: WasmPlugin
metadata:
  name: waypoint-filter
spec:
  targetRefs:
  - group: gateway.networking.k8s.io
    kind: Gateway
    name: reviews-waypoint
  url: oci://ghcr.io/filters/custom:latest
  phase: AUTHN
```

**Depuración**:

```bash
# Check WASM plugin status
kubectl get wasmplugin -A

# Check WASM-related logs in Envoy logs
kubectl logs <pod-name> -c istio-proxy | grep wasm

# Check WASM module load
istioctl proxy-config all <pod-name> -o json | jq '.. | objects | select(has("@type")) | select(.["@type"] | test("wasm"; "i"))'
```

**Consideraciones de seguridad**:
1. **Aislamiento sandbox**: sandbox del entorno de ejecución dentro de Envoy; revise la confianza en el plugin y su uso de recursos
2. **Límites de recursos**: pueden configurarse límites de CPU y memoria
3. **Verificación de integridad**: SHA256 comprueba el contenido; no autentica al publicador
4. **Mínimo privilegio**: conceder solo los permisos necesarios

**Ventajas**:
- Alto rendimiento (al nivel de código nativo)
- Ejecución segura en sandbox
- Actualizable sin volver a desplegar
- Compatibilidad con varios lenguajes
- Formato estándar de imagen OCI

**Limitaciones**:
- Algunas llamadas al sistema están restringidas
- E/S de archivos limitada
- Llamadas de red únicamente mediante la API de Envoy

**Términos relacionados**: [Envoy](#envoy-proxy), [Proxy waypoint](#waypoint-proxy), [Modo Ambient](#ambient-mode)

**Referencias**:
- [Plugin WASM de Istio](https://istio.io/latest/docs/reference/config/proxy_extensions/wasm-plugin/)
- [SDK Proxy-Wasm](https://github.com/proxy-wasm)
- [Sitio oficial de WebAssembly](https://webassembly.org/)
- [Modo Ambient - WASM](https://istio.io/latest/docs/ambient/usage/extend-waypoint-wasm/)

---

### xDS (servicio de descubrimiento) {#xds-discovery-service}

Conjunto de API para configurar dinámicamente el proxy Envoy.

**Significado de «xDS»**:
- `x`: variable que representa distintos tipos
- `DS`: servicio de descubrimiento

**Tipos de API xDS**:

| API | Nombre | Función |
|-----|------|------|
| **LDS** | Listener Discovery Service | Puertos de escucha y cadenas de filtros |
| **RDS** | Route Discovery Service | Reglas de enrutamiento HTTP |
| **CDS** | Cluster Discovery Service | Configuración de servicios upstream |
| **EDS** | Endpoint Discovery Service | Lista de IP reales de Pods |
| **SDS** | Secret Discovery Service | Certificados y claves TLS |

**Método de comunicación**:
- Protocolo: gRPC
- Puerto: 15012 (Istiod)
- Streaming bidireccional

**Orden**:
```
Agent bootstraps identity -> Envoy subscribes to ADS resources
Istiod pushes LDS/CDS/EDS/RDS updates; local agent serves SDS certificates
```

**Documentación relacionada**: [Arquitectura - Comunicación mediante API xDS](https://www.atomai.click/kubernetes-docs/en/service-mesh/istio/03-architecture#xds-api-communication)

---

### Zona

Representa una zona de disponibilidad de Kubernetes.

**Formato de etiqueta**:
```yaml
topology.kubernetes.io/zone: us-west-1a
```

**Uso en Istio**:
- Equilibrio de carga consciente de la localidad
- Enrutamiento consciente de zonas
- Enrutamiento que prioriza la misma zona

**Términos relacionados**: [Equilibrio de carga consciente de la localidad](#locality-aware-load-balancing)

---

### ztunnel (Zero Trust Tunnel) {#ztunnel-zero-trust-tunnel}

Componente principal de modo Ambient: un proxy L4 ligero que se ejecuta a nivel de nodo.

**Función**:
- Se despliega como DaemonSet en cada nodo
- Gestiona el tráfico L4 de todos los Pods
- Proporciona funciones de malla de servicios sin sidecar
- Se integra con el plugin CNI

**Funciones proporcionadas**:
- **mTLS**: cifrado/descifrado automático
- **Telemetría L4**: recopilación de métricas
- **Identidad**: autenticación basada en ServiceAccount
- **Equilibrio de carga L4**: equilibrio de carga básico

**Características técnicas**:
- Escrito en Rust (alto rendimiento)
- Redirección del tráfico gestionada por Istio CNI
- No requiere contenedor de inicialización
- Recursos del proxy L4 compartidos; dimensionar según la carga medida del nodo

**Ejemplo de despliegue**:
```bash
# Use the reviewed istioctl version and the complete ambient installation profile
istioctl install --set profile=ambient
kubectl rollout status daemonset/ztunnel -n istio-system
```

Para una carga de trabajo sidecar existente, elimine las etiquetas de inyección/revisión y reinicie los Pods para retirar los sidecars antes de incorporarla a ambient; una carga nueva sin sidecar no necesita reiniciarse.

**Activación del espacio de nombres**:
```bash
# Enable Ambient Mode
kubectl label namespace default istio-injection- istio.io/rev-
kubectl label namespace default istio.io/dataplane-mode=ambient --overwrite
```

**Ventajas**:
- El posible ahorro de memoria depende del nodo, la carga de trabajo y la capacidad del waypoint
- No requiere reiniciar Pods
- Transparencia para la aplicación
- Latencia inicial minimizada

**Limitaciones**:
- Las funciones L7 requieren un proxy waypoint
- Requiere una plataforma Linux Kubernetes compatible, un CNI principal y los requisitos previos de Istio CNI

**Términos relacionados**: [Modo Ambient](#ambient-mode), [Proxy waypoint](#waypoint-proxy), [eBPF](#ebpf-extended-berkeley-packet-filter)

---

## Referencias

### Documentación oficial
- [Glosario de Istio](https://istio.io/latest/docs/reference/glossary/)
- [Terminología de Envoy](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/intro/terminology)
- [Especificación SPIFFE](https://github.com/spiffe/spiffe/tree/main/standards)

### Documentación relacionada
- [Arquitectura de Istio](03-architecture.md)
- [Gestión de tráfico](traffic-management/README.md)
- [Seguridad](security/README.md)
- [Observabilidad](observability/README.md)

---

**Última actualización**: September 13, 2026

- [Destination Rule](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
- [Instalar el agente de nodo Istio CNI](https://istio.io/latest/docs/setup/additional-setup/cni/)
- [Redirección del tráfico de ztunnel](https://istio.io/latest/docs/ambient/architecture/traffic-redirection/)
- [Instalar con istioctl](https://istio.io/latest/docs/ambient/install/istioctl/)
- [Configurar proxies waypoint](https://istio.io/latest/docs/ambient/usage/waypoint/)
- [Habilitar límites de tasa mediante Envoy](https://istio.io/latest/docs/tasks/policy-enforcement/rate-limit/)
- [Plugin Wasm](https://istio.io/latest/docs/reference/config/proxy_extensions/wasm-plugin/)
- [Ejemplo HTTP del SDK Rust Proxy-Wasm](https://raw.githubusercontent.com/proxy-wasm/proxy-wasm-rust-sdk/main/examples/http_headers/src/lib.rs)
- [AWS Signature Version 4 para solicitudes de API - AWS Identity and Access Management](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_sigv.html)
- [Firma de solicitudes AWS](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/aws_request_signing_filter)
- [Estadísticas](https://www.envoyproxy.io/docs/envoy/latest/configuration/upstream/cluster_manager/cluster_stats)
- [Notas de cambios de Istio 1.8](https://istio.io/latest/news/releases/1.8.x/announcing-1.8/change-notes/)
- [¿Qué es AWS App Mesh? - AWS App Mesh](https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html)

- [Cobertura de eventos de datos de CloudTrail](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/logging-data-events-with-cloudtrail.html)
