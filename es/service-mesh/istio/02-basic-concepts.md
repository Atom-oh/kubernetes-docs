# Conceptos básicos

Este documento explica los conceptos fundamentales y la arquitectura de Istio. Comprender estos conceptos básicos es importante para usar Istio eficazmente.

## Índice

1. [Contexto e historia](02-basic-concepts.md#background-and-history)
2. [¿Por qué Istio?](02-basic-concepts.md#why-istio)
3. [Arquitectura de Istio](02-basic-concepts.md#istio-architecture)
4. [Modos de despliegue: Sidecar vs Ambient](02-basic-concepts.md#deployment-modes-sidecar-vs-ambient)
5. [Recursos principales](02-basic-concepts.md#core-resources)
6. [Conceptos de gestión de tráfico](02-basic-concepts.md#traffic-management-concepts)
7. [Conceptos de seguridad](02-basic-concepts.md#security-concepts)
8. [Conceptos de observabilidad](02-basic-concepts.md#observability-concepts)
9. [Namespaces y Service Mesh](02-basic-concepts.md#namespaces-and-service-mesh)
10. [Siguientes pasos](02-basic-concepts.md#next-steps)

## Contexto e historia

### El nacimiento de Service Mesh

#### Desafíos de los microservicios

A principios de la década de 2010, las empresas comenzaron a descomponer las aplicaciones monolíticas en microservicios.

```mermaid
flowchart TB
    subgraph Before[Monolithic Era]
        M[Monolithic<br/>Application]
        M -->|Single process| M
    end

    subgraph After[Microservices Era]
        S1[Service A]
        S2[Service B]
        S3[Service C]
        S4[Service D]
        S5[Service E]

        S1 --> S2
        S1 --> S3
        S2 --> S4
        S3 --> S4
        S4 --> S5
    end

    Before -.->|Transition| After

    %% Style definitions
    classDef monolith fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;
    classDef micro fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class M monolith;
    class S1,S2,S3,S4,S5 micro;
```

**Nuevos problemas**:

| Problema                         | Descripción                                  | Impacto                         |
| ------------------------------- | -------------------------------------------- | ------------------------------ |
| **Comunicación entre servicios** | Aumento de las llamadas de red               | Latencia, propagación de fallos |
| **Observabilidad**               | Necesidad de trazabilidad distribuida        | Depuración difícil             |
| **Seguridad**                    | Autenticación/cifrado entre servicios        | Complejidad de implementación de mTLS |
| **Control de tráfico**           | Despliegues Canary, pruebas A/B              | Modificaciones al código de la aplicación |
| **Manejo de fallos**             | Circuit Breaker, Retry                       | Implementación por servicio     |

#### Solución inicial: bibliotecas

**Problemas**:

* Necesidad de desarrollar bibliotecas para cada lenguaje (Hystrix para Java, biblioteca independiente para Go...)
* Acoplamiento estrecho con el código de la aplicación
* Requiere volver a desplegar todos los servicios para las actualizaciones
* Gestión de versiones compleja

```mermaid
flowchart LR
    subgraph App1[Java Service]
        J[Application Code]
        H[Hystrix<br/>Netflix OSS]
    end

    subgraph App2[Go Service]
        G[Application Code]
        L[Go Library]
    end

    subgraph App3[Python Service]
        P[Application Code]
        R[Requests + Retry]
    end

    J --- H
    G --- L
    P --- R

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef lib fill:#FF6B6B,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class J,G,P app;
    class H,L,R lib;
```

**Idea de Service Mesh**: trasladar la lógica de red de la aplicación a una capa de infraestructura

### El nacimiento de Envoy Proxy

#### El problema de Lyft

**En 2015, Lyft** enfrentaba los siguientes problemas:

* Operaba más de 200 microservicios
* Diversos lenguajes y frameworks (Python, Go, Java, etc.)
* Los proxies existentes (HAProxy, NGINX) eran insuficientes
  * Cambios de configuración dinámica difíciles
  * Falta de observabilidad
  * Funcionalidades avanzadas de enrutamiento limitadas

#### Matt Klein y Envoy

**Matt Klein** (ingeniero de Lyft) publicó Envoy como código abierto en 2016.

**Problemas que Envoy resolvió**:

```mermaid
flowchart TB
    subgraph Problems[Existing Proxy Problems]
        P1[Static configuration<br/>File-based]
        P2[Limited<br/>metrics]
        P3[Complex<br/>restart]
        P4[Simple<br/>routing]
    end

    subgraph Solutions[Envoy's Solutions]
        S1[Dynamic API<br/>xDS Protocol]
        S2[Rich<br/>statistics/tracing]
        S3[Hot Restart<br/>Zero downtime]
        S4[Advanced L7<br/>routing]
    end

    P1 -.->|Solved| S1
    P2 -.->|Solved| S2
    P3 -.->|Solved| S3
    P4 -.->|Solved| S4

    %% Style definitions
    classDef problem fill:#FF6B6B,stroke:#333,stroke-width:1px,color:white;
    classDef solution fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class P1,P2,P3,P4 problem;
    class S1,S2,S3,S4 solution;
```

**Características principales de Envoy**:

1. **Arquitectura fuera de proceso**: proceso independiente de la aplicación
2. **APIs xDS**: actualizaciones de configuración dinámica
3. **Proxy L7**: soporte para HTTP/2, gRPC y WebSocket
4. **Observabilidad**: métricas detalladas, trazabilidad y registros
5. **Rendimiento**: escrito en C++, alto rendimiento

#### Adopción por CNCF

**Cronología**:

* **Septiembre de 2016**: Envoy se publica como código abierto
* **Septiembre de 2017**: aceptado como proyecto CNCF (Incubating)
* **Noviembre de 2018**: promovido a proyecto CNCF Graduated

### El nacimiento y la historia de Istio

#### Colaboración entre Google, IBM y Lyft

**En mayo de 2017**, Google, IBM y Lyft colaboraron para anunciar Istio.

```mermaid
flowchart LR
    subgraph Companies[Participating Companies]
        G[Google<br/>Kubernetes experience]
        I[IBM<br/>Enterprise requirements]
        L[Lyft<br/>Envoy Proxy]
    end

    subgraph Istio[Istio Service Mesh]
        CP[Control Plane<br/>Google led]
        DP[Data Plane<br/>Envoy-based]
    end

    G --> CP
    I --> CP
    L --> DP

    %% Style definitions
    classDef company fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef component fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class G,I,L company;
    class CP,DP component;
```

**Contribuciones de cada empresa**:

| Empresa    | Contribución principal    | Motivo                           |
| ---------- | -------------------- | -------------------------------- |
| **Google** | Diseño de Control Plane | Experiencia con Borg y Kubernetes      |
| **IBM**    | Funcionalidades empresariales  | Requisitos de clientes empresariales |
| **Lyft**   | Envoy Proxy          | Proxy probado en producción          |

#### Historial de versiones de Istio

**Hitos principales**:

```mermaid
timeline
    title Istio Major Version History
    2017-05 : Istio 0.1 announced
    2018-07 : Istio 1.0 : Production ready
    2019-03 : Istio 1.1 : Performance improvements
    2020-03 : Istio 1.5 : Istiod consolidation
    2021-05 : Istio 1.10 : Discovery Selectors
    2022-02 : Istio 1.13 : Gateway API support
    2023-11 : Istio 1.20 : Ambient Mode
    2024-05 : Istio 1.22 : Stability improvements
    2025-01 : Istio 1.28 : Current version
```

**Versión 1.5 (marzo de 2020): punto de inflexión importante**:

Arquitectura anterior (Istio 1.4 y versiones anteriores):

```
Separated into individual components:
- Mixer (policy/telemetry)
- Pilot (traffic management)
- Citadel (certificate management)
- Galley (configuration validation)
```

Nueva arquitectura (Istio 1.5+, actual 1.28):

```
Istiod (consolidated into single binary)
├── Pilot functionality (Service Discovery, Traffic Management)
├── Citadel functionality (Certificate Authority, Identity)
└── Galley functionality (Configuration Validation)

Mixer completely removed (functionality moved to Envoy)
```

**Motivos del cambio**:

* Complejidad reducida (4 componentes → 1)
* Rendimiento mejorado (reducción del 50 % de la latencia al eliminar Mixer)
* Operaciones simplificadas (gestión de un único proceso)
* Eficiencia de recursos (menor uso de memoria y CPU)

## ¿Por qué Istio?

Kubernetes proporciona orquestación de contenedores, pero tiene limitaciones para gestionar la comunicación compleja entre microservicios. Istio es una solución de Service Mesh para abordar estos problemas.

### Desafíos de los microservicios

```mermaid
flowchart TB
    subgraph Problems["Microservices Challenges"]
        P1[Traffic Management<br/>Complex routing]
        P2[Security<br/>Inter-service encryption]
        P3[Observability<br/>Difficult debugging]
        P4[Resilience<br/>Failure handling]
    end

    subgraph Without["Without Istio"]
        W1[Direct implementation<br/>in application code]
        W2[Duplicate code<br/>in each service]
        W3[Inconsistent<br/>implementation]
        W4[Difficult<br/>maintenance]
    end

    subgraph With["Using Istio"]
        I1[Automatic handling<br/>at infrastructure level]
        I2[Central management<br/>with declarative config]
        I3[Consistent<br/>policy application]
        I4[Add features<br/>without code changes]
    end

    P1 & P2 & P3 & P4 -->|Traditional approach| W1
    W1 --> W2 --> W3 --> W4

    P1 & P2 & P3 & P4 -->|Istio| I1
    I1 --> I2 --> I3 --> I4

    %% Style definitions
    classDef problem fill:#FF6B6B,stroke:#333,stroke-width:1px,color:white;
    classDef without fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;
    classDef with fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class P1,P2,P3,P4 problem;
    class W1,W2,W3,W4 without;
    class I1,I2,I3,I4 with;
```

### Valores principales que proporciona Istio

#### 1. Gestión de tráfico

**Problema**: se desea realizar una transición segura del tráfico al desplegar nuevas versiones.

**Solución de Istio**:

```yaml
# Canary deployment without code changes
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 90  # Existing version 90%
    - destination:
        host: reviews
        subset: v2
      weight: 10  # New version 10%
```

**Beneficios**:

* No se requiere modificar el código de la aplicación
* Ajuste de división de tráfico en tiempo real
* Posibilidad de rollback automático
* Soporte para pruebas A/B y despliegue Blue/Green

#### 2. Seguridad

**Problema**: se desea cifrar y autenticar la comunicación entre servicios.

**Solución de Istio**:

```yaml
# Automatic mTLS enablement
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # Automatic encryption for all inter-service communication
```

**Beneficios**:

* Emisión y renovación automática de certificados
* Verificación automática de identidad del servicio
* Control de permisos granular
* Implementación de red Zero Trust

#### 3. Observabilidad

**Problema**: es difícil rastrear el flujo de solicitudes entre decenas de microservicios.

**Solución de Istio**:

* Generación automática de métricas (Latency, Traffic, Errors, Saturation)
* Trazabilidad distribuida
* Visualización de la topología de servicios

**Beneficios**:

* Identificación automática de cuellos de botella
* Identificación rápida de la causa raíz de los errores
* Supervisión del estado de los servicios en tiempo real

#### 4. Resiliencia

**Problema**: el fallo de un servicio se propaga a todo el sistema.

**Solución de Istio**:

```yaml
# Automatic Circuit Breaker configuration
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
```

**Beneficios**:

* Aislamiento de fallos (Circuit Breaker)
* Retry y timeout automáticos
* Eliminación automática de instancias no saludables
* Limitación de tráfico (Rate Limiting)

### Cuándo usar Istio

**✅ Cuándo Istio es adecuado:**

1. **Arquitectura de microservicios**
   * 10 o más servicios
   * Dependencias complejas entre servicios
   * Despliegues frecuentes
2. **Se necesita gestión avanzada de tráfico**
   * Despliegues Canary, pruebas A/B
   * Control de enrutamiento granular
   * Traffic Mirroring
3. **Requisitos sólidos de seguridad**
   * Cifrado entre servicios obligatorio
   * Control de acceso granular
   * Cumplimiento normativo
4. **Observabilidad y depuración**
   * Seguimiento de problemas complejos entre servicios
   * Identificación de cuellos de botella de rendimiento
   * Supervisión de SLO/SLA

**❌ Cuándo Istio puede ser excesivo:**

1. **Aplicaciones simples**
   * Pocos servicios (menos de 5)
   * Requisitos simples
   * Kubernetes Ingress es suficiente
2. **Restricciones de recursos**
   * Cluster pequeño
   * No se puede asumir la sobrecarga de recursos
   * Carga de coste de memoria de Sidecar
3. **Falta de capacidad operativa**
   * Tiempo de aprendizaje insuficiente
   * Sin equipo de plataforma dedicado
   * Se prefieren soluciones más simples

### Comparación de alternativas

#### Kubernetes Ingress vs Istio

| Característica           | Kubernetes Ingress | Istio                             |
| ----------------- | ------------------ | --------------------------------- |
| **Alcance**         | Externo → Cluster | Externo + entre servicios internos |
| **Enrutamiento**       | Básico (Path, Host) | Avanzado (Header, Cookie, etc.)   |
| **mTLS**          | Configuración manual       | Automático                         |
| **Observabilidad** | Limitada            | Completa                              |
| **Complejidad**    | Baja                | Alta                              |
| **Caso de uso**      | Aplicaciones simples        | Microservicios                     |

#### AWS VPC Lattice vs Istio

Para una comparación detallada, consulta el documento de [integración con AWS](04-aws-integration.md#istio-vs-other-solutions-comparison).

**Resumen rápido:**

* **VPC Lattice**: administrado por AWS, simple, comunicación entre VPC/cuentas
* **Istio**: código abierto, funcionalidades potentes, solo para Kubernetes, control granular

#### Linkerd vs Istio

| Propiedad           | Istio     | Linkerd            |
| ------------------ | --------- | ------------------ |
| **Complejidad**     | Alta      | Baja                |
| **Funcionalidades**       | Muy completas | Solo funcionalidades principales |
| **Recursos**      | Altos      | Bajos                |
| **Curva de aprendizaje** | Pronunciada     | Suave             |
| **Comunidad**      | Grande     | Pequeña              |

**Guía de selección:**

* Se necesitan funcionalidades avanzadas y flexibilidad → **Istio**
* Se necesita una malla simple y ligera → **Linkerd**

## Modos de despliegue: Sidecar vs Ambient

Istio admite dos modos de despliegue: **Sidecar Mode** y **Ambient Mode**.

### Sidecar Mode (predeterminado)

Inyecta un proxy Envoy como contenedor sidecar en cada Pod de la aplicación.

```mermaid
flowchart LR
    subgraph Pod["Pod"]
        App[Application<br/>Container]
        Envoy[Envoy Proxy<br/>Sidecar]
    end

    External[External Request] -->|Traffic| Envoy
    Envoy -->|Local| App
    App -->|Outbound call| Envoy
    Envoy -->|Network| Target[Target Service]

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class App app;
    class Envoy proxy;
    class External,Target default;
```

**Ventajas:**

* Maduro y estable
* Compatibilidad con todas las funcionalidades de Istio
* Control granular por Pod

**Desventajas:**

* Sobrecarga de recursos (Envoy por Pod)
* Mayor tiempo de inicio (Init Container)
* Configuración de permisos compleja (iptables)

### Ambient Mode (nuevo enfoque)

Gestiona el tráfico en el nivel de nodo sin sidecars.

```mermaid
flowchart TB
    subgraph Node["Worker Node"]
        subgraph Pod1["Pod 1"]
            App1[Application<br/>No sidecar]
        end

        subgraph Pod2["Pod 2"]
            App2[Application<br/>No sidecar]
        end

        Ztunnel[ztunnel<br/>1 per node<br/>L4 proxy]
        Waypoint[Waypoint Proxy<br/>L7 proxy<br/>Optional]
    end

    App1 <-->|Transparent redirect| Ztunnel
    App2 <-->|Transparent redirect| Ztunnel
    Ztunnel <-->|When L7 needed| Waypoint

    %% Style definitions
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class App1,App2 userApp;
    class Ztunnel,Waypoint proxy;
```

**Ventajas:**

* Bajo uso de recursos (1 por nodo)
* Inicio rápido de Pod
* Operaciones simples
* Posibilidad de aplicación gradual de funcionalidades L7

**Desventajas:**

* Tecnología relativamente nueva (menos madura)
* Algunas funcionalidades avanzadas son limitadas
* Control granular por Pod difícil

### Tabla comparativa

| Propiedad                   | Sidecar Mode                | Ambient Mode                   |
| -------------------------- | --------------------------- | ------------------------------ |
| **Uso de recursos**         | Alto (por Pod)              | Bajo (por nodo)                 |
| **Tiempo de inicio**           | Lento (Init Container)       | Rápido                           |
| **Complejidad operativa** | Alta                        | Baja                            |
| **Funcionalidades L4**            | Compatibles                   | Compatibles                      |
| **Funcionalidades L7**            | Compatibilidad completa                | Opcional (Waypoint)            |
| **Madurez**               | Alta                        | Media                         |
| **Migración**              | -                           | Posible desde Sidecar existente |
| **Uso recomendado**        | Se necesitan funcionalidades L7 avanzadas | Prioridad: eficiencia de recursos   |

### Guía de selección

**Elige Sidecar Mode:**

* Se necesita utilizar todas las funcionalidades de Istio
* Se necesita control de políticas granular por Pod
* Se necesita estabilidad probada en producción

**Elige Ambient Mode:**

* La eficiencia de recursos es importante
* Solo se necesitan funcionalidades L4 simples
* Se planea añadir gradualmente funcionalidades L7

**Para más detalles**, consulta el documento [Avanzado: Ambient Mode](advanced/01-ambient-mode.md).

## Arquitectura de Istio

Istio consta de dos componentes principales: **Control Plane** y **Data Plane**.

| Componente                    | Descripción                                                                                                  |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **Control Plane (istiod)**   | Sistema de control central responsable del descubrimiento de servicios, la distribución de configuración y la gestión de certificados |
| **Data Plane (Envoy Proxy)** | Desplegado como sidecar en cada Pod; gestiona el tráfico real (enrutamiento, mTLS y métricas)                             |

**Para conocer en detalle la estructura de la arquitectura, los principios de funcionamiento interno y los mecanismos de interceptación de tráfico**, consulta el [documento de arquitectura](03-architecture.md).

## Recursos principales

Istio utiliza Kubernetes Custom Resource Definitions (CRDs) para gestionar la configuración.

### 1. VirtualService

VirtualService define cómo se enrutan las solicitudes a los servicios.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-route
spec:
  hosts:
  - reviews  # Target service
  http:
  - match:
    - headers:
        end-user:
          exact: jason
    route:
    - destination:
        host: reviews
        subset: v2  # Route specific user to v2
  - route:
    - destination:
        host: reviews
        subset: v1  # Route to v1 by default
```

**Características principales**:

* Enrutamiento basado en Path (Path, Header, Query Parameter)
* División de tráfico (Canary, pruebas A/B)
* Retry, Timeout, Fault Injection
* URL Rewrite, manipulación de Header

### 2. DestinationRule

DestinationRule define subconjuntos (versiones) de servicios y aplica políticas de tráfico.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-destination
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST  # Load balancing algorithm
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 2
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
  - name: v3
    labels:
      version: v3
```

**Características principales**:

* Definición de versión (subset) de servicio
* Algoritmo de balanceo de carga
* Configuración de Connection Pool
* Circuit Breaker (Outlier Detection)
* Configuración de TLS

### 3. Gateway

Gateway gestiona el tráfico externo que entra en la malla.

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: bookinfo-gateway
spec:
  selector:
    istio: ingressgateway  # Select Ingress Gateway pod
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "bookinfo.example.com"
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: bookinfo-credential  # TLS certificate
    hosts:
    - "bookinfo.example.com"
```

**Características principales**:

* Definir el punto de entrada de tráfico externo
* Configuración de host, puerto y protocolo
* Terminación TLS
* Enrutamiento SNI

### 4. ServiceEntry

ServiceEntry permite usar servicios externos fuera de la malla como servicios internos.

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

**Características principales**:

* Registro de servicios externos
* Control de tráfico para servicios externos
* Gestión de tráfico de salida

### 5. PeerAuthentication

PeerAuthentication define las políticas de autenticación entre servicios.

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: default
spec:
  mtls:
    mode: STRICT  # STRICT, PERMISSIVE, DISABLE
```

### 6. AuthorizationPolicy

AuthorizationPolicy define los permisos de acceso a los servicios.

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-ratings
  namespace: default
spec:
  selector:
    matchLabels:
      app: ratings
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/reviews"]
    to:
    - operation:
        methods: ["GET"]
```

## Conceptos de gestión de tráfico

### Flujo de enrutamiento de tráfico

```mermaid
flowchart LR
    Client[Client] -->|1. HTTP Request| Gateway[Gateway<br/>Ingress]
    Gateway -->|2. VirtualService<br/>Apply routing rules| VS[VirtualService]
    VS -->|3. Determine destination| DR[DestinationRule]
    DR -->|4. Select subset<br/>Apply traffic policy| Service[Kubernetes<br/>Service]
    Service -->|5. Endpoint<br/>routing| Pod1[Pod v1]
    Service -->|5. Endpoint<br/>routing| Pod2[Pod v2]

    %% Style definitions
    classDef gateway fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef istioResource fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef k8sResource fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class Gateway gateway;
    class VS,DR istioResource;
    class Service,Pod1,Pod2 k8sResource;
    class Client default;
```

### División de tráfico (despliegue Canary)

```yaml
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
      weight: 90  # 90% of traffic
    - destination:
        host: reviews
        subset: v2
      weight: 10  # 10% of traffic (canary)
```

### Circuit Breaker

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
        http1MaxPendingRequests: 10
        maxRequestsPerConnection: 2
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

## Conceptos de seguridad

### mTLS (TLS mutuo)

Istio cifra automáticamente la comunicación entre servicios.

```mermaid
flowchart LR
    subgraph Pod1["Pod A"]
        App1[App]
        Envoy1[Envoy]
    end

    subgraph Pod2["Pod B"]
        Envoy2[Envoy]
        App2[App]
    end

    App1 -->|Plaintext| Envoy1
    Envoy1 <-->|mTLS Encrypted| Envoy2
    Envoy2 -->|Plaintext| App2

    Citadel[istiod<br/>Citadel] -.->|Certificate issuance| Envoy1
    Citadel -.->|Certificate issuance| Envoy2

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef controlPlane fill:#FF9900,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class App1,App2 app;
    class Envoy1,Envoy2 proxy;
    class Citadel controlPlane;
```

**Modos de mTLS**:

* **STRICT**: solo se permite mTLS
* **PERMISSIVE**: se permiten tanto mTLS como texto sin cifrar (para migración)
* **DISABLE**: mTLS deshabilitado

### Autenticación y autorización

```yaml
# JWT Authentication
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-auth
spec:
  jwtRules:
  - issuer: "https://accounts.google.com"
    jwksUri: "https://www.googleapis.com/oauth2/v3/certs"
---
# Authorization Policy
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: require-jwt
spec:
  action: DENY
  rules:
  - from:
    - source:
        notRequestPrincipals: ["*"]
```

## Conceptos de observabilidad

Istio genera automáticamente métricas, registros y trazas.

### Métricas generadas automáticamente

```mermaid
flowchart TB
    subgraph Pod["Pod"]
        App[Application]
        Envoy[Envoy Proxy]
    end

    App <-->|Traffic| Envoy

    Envoy -->|Metrics| Prometheus[Prometheus<br/>Metric Collection]
    Envoy -->|Traces| Jaeger[Jaeger<br/>Distributed Tracing]
    Envoy -->|Logs| Logging[Logging System]

    Prometheus -->|Visualization| Grafana[Grafana<br/>Dashboard]
    Jaeger -->|Analysis| JaegerUI[Jaeger UI]

    Kiali[Kiali<br/>Service Mesh Dashboard] -->|Query| Prometheus

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef monitoring fill:#E6522C,stroke:#333,stroke-width:1px,color:white;
    classDef visualization fill:#F8B52A,stroke:#333,stroke-width:1px,color:black;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class App app;
    class Envoy proxy;
    class Prometheus,Jaeger,Logging monitoring;
    class Grafana,JaegerUI,Kiali visualization;
```

### Métricas principales

| Métrica                                | Descripción          |
| ------------------------------------- | -------------------- |
| `istio_requests_total`                | Número total de solicitudes  |
| `istio_request_duration_milliseconds` | Latencia de solicitud      |
| `istio_request_bytes`                 | Tamaño de solicitud         |
| `istio_response_bytes`                | Tamaño de respuesta        |
| `istio_tcp_connections_opened_total`  | Número de conexiones TCP |

### Trazabilidad distribuida

```yaml
# Enable tracing in Envoy
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    enableTracing: true
    defaultConfig:
      tracing:
        sampling: 100.0  # 100% sampling
        zipkin:
          address: jaeger-collector.istio-system:9411
```

## Namespaces y Service Mesh

### Aislamiento de Namespace

```yaml
# Per-namespace mTLS policy
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: production
spec:
  mtls:
    mode: STRICT
---
# Per-namespace authorization policy
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-all
  namespace: production
spec:
  action: DENY
  rules:
  - {}
```

### Alcance de Service Mesh

```bash
# Include only specific namespaces in the mesh
kubectl label namespace default istio-injection=enabled
kubectl label namespace staging istio-injection=enabled

# Exclude specific namespace
kubectl label namespace kube-system istio-injection=disabled
```

### Multi-tenancy

```yaml
# Restrict mesh scope with Sidecar resource
apiVersion: networking.istio.io/v1
kind: Sidecar
metadata:
  name: default
  namespace: production
spec:
  egress:
  - hosts:
    - "production/*"  # Only production namespace accessible
    - "istio-system/*"
```

## Registro de cargas de trabajo de VM

Istio puede registrar no solo Pods de Kubernetes, sino también **cargas de trabajo de Virtual Machine (VM)** en la Service Mesh. Esto permite que las aplicaciones heredadas o los servicios fuera del cluster aprovechen las funcionalidades de gestión de tráfico, seguridad y observabilidad de Istio.

### Por qué se necesitan las cargas de trabajo de VM

```mermaid
flowchart TB
    subgraph Legacy[Legacy Environment]
        VM1[VM<br/>Legacy App]
        VM2[VM<br/>Database]
        VM3[VM<br/>External Service]
    end

    subgraph K8S[Kubernetes Cluster]
        subgraph Pod1[Pod]
            App1[New App]
            Envoy1[Envoy]
        end

        subgraph Pod2[Pod]
            App2[Microservice]
            Envoy2[Envoy]
        end
    end

    subgraph Istiod[Control Plane]
        CP[istiod]
    end

    VM1 -->|Before migration<br/>Direct communication| App1
    App1 -.->|After mesh registration<br/>mTLS, policy applied| VM1

    CP -.->|Configuration delivery| Envoy1
    CP -.->|Configuration delivery| Envoy2
    CP -.->|VM can also be registered| VM1

    %% Style definitions
    classDef vm fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;
    classDef k8sApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef controlPlane fill:#FF9900,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class VM1,VM2,VM3 vm;
    class App1,App2 k8sApp;
    class Envoy1,Envoy2 proxy;
    class CP controlPlane;
```

**Escenarios de uso**:

* Migración gradual de aplicaciones heredadas
* Inclusión de servidores de bases de datos en la malla
* Integración de servicios fuera del cluster
* Configuración de entorno de nube híbrida

### Arquitectura de registro de VM

```mermaid
flowchart LR
    subgraph VM[Virtual Machine]
        LegacyApp[Legacy<br/>Application]
        EnvoyVM[Envoy<br/>Sidecar]
    end

    subgraph K8S[Kubernetes Cluster]
        subgraph Pod[Pod]
            App[Application]
            EnvoyPod[Envoy<br/>Sidecar]
        end

        Istiod[istiod<br/>Control Plane]
    end

    LegacyApp <-->|Local communication| EnvoyVM
    App <-->|Local communication| EnvoyPod

    EnvoyVM <-->|mTLS| EnvoyPod

    Istiod -.->|xDS configuration| EnvoyVM
    Istiod -.->|xDS configuration| EnvoyPod
    Istiod -.->|Certificate issuance| EnvoyVM

    %% Style definitions
    classDef vmApp fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;
    classDef k8sApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef controlPlane fill:#FF9900,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class LegacyApp vmApp;
    class App k8sApp;
    class EnvoyVM,EnvoyPod proxy;
    class Istiod controlPlane;
```

### Recurso WorkloadEntry

Las cargas de trabajo de VM se registran con el recurso **WorkloadEntry**.

```yaml
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: legacy-database
  namespace: default
spec:
  address: 192.168.1.100  # VM IP address
  labels:
    app: mysql
    version: v5.7
  serviceAccount: database-sa
  ports:
    mysql: 3306
```

**Campos principales de WorkloadEntry**:

* `address`: dirección IP de VM
* `labels`: coincide con el selector de servicio
* `serviceAccount`: cuenta de servicio para autenticación mTLS
* `ports`: definición de puertos expuestos

### Integración con ServiceEntry

WorkloadEntry se usa con ServiceEntry para registrar servicios de VM en la malla.

```yaml
# Define service with ServiceEntry
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: legacy-database
spec:
  hosts:
  - database.legacy.com
  ports:
  - number: 3306
    name: mysql
    protocol: TCP
  location: MESH_INTERNAL  # Register as internal mesh service
  resolution: STATIC
  workloadSelector:
    labels:
      app: mysql
---
# Register VM instance with WorkloadEntry
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: mysql-vm-1
  namespace: default
spec:
  address: 192.168.1.100
  labels:
    app: mysql
    version: v5.7
  serviceAccount: mysql-sa
```

### Comparación entre registro de VM y Multi-Cluster

| Característica                    | Registro de carga de trabajo de VM | Multi-Cluster                  | Kubernetes Pod      |
| -------------------------- | ------------------------ | ------------------------------ | ------------------- |
| **Ubicación de la carga de trabajo**      | VM fuera del cluster       | Cluster de Kubernetes diferente   | Dentro del cluster      |
| **Instalación de Envoy**     | Instalación manual      | Automática (sidecar)            | Automática (sidecar) |
| **Método de registro**    | WorkloadEntry            | ServiceEntry + EndpointSlice   | Service + Pod       |
| **mTLS**                   | Compatible                | Compatible                      | Compatible           |
| **Descubrimiento de servicios**      | Manual (IP especificada)    | Automático                      | Automático           |
| **Escenario de uso**         | Aplicaciones heredadas, DB          | Multi-cloud, recuperación ante desastres | Aplicaciones cloud-native   |
| **Complejidad operativa** | Alta                     | Media                         | Baja                 |

### Beneficios del registro de VM

#### 1. Migración gradual

```mermaid
flowchart LR
    subgraph Phase1[Phase 1: Legacy Environment]
        VM1[VM<br/>Monolith App]
    end

    subgraph Phase2[Phase 2: VM Mesh Registration]
        VM2[VM<br/>Monolith App<br/>+ Envoy]
    end

    subgraph Phase3[Phase 3: Hybrid]
        VM3[VM<br/>Legacy Module]
        K8S1[K8s<br/>New Microservices]
        VM3 <-->|mTLS| K8S1
    end

    subgraph Phase4[Phase 4: Complete Migration]
        K8S2[K8s<br/>All Microservices]
    end

    Phase1 -->|VM registration| Phase2
    Phase2 -->|Partial migration| Phase3
    Phase3 -->|Complete| Phase4

    %% Style definitions
    classDef vm fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;
    classDef k8s fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class VM1,VM2,VM3 vm;
    class K8S1,K8S2 k8s;
```

**Beneficios**:

* Integrar aplicaciones de VM existentes en la malla sin modificaciones
* Migrar a Kubernetes por etapas
* Mantener seguridad y observabilidad consistentes durante la migración

#### 2. Política de seguridad unificada

```yaml
# mTLS policy applied to both VMs and pods
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: default
spec:
  mtls:
    mode: STRICT  # Enforce mTLS for both VMs and pods
---
# VM database access control
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: database-access
  namespace: default
spec:
  selector:
    matchLabels:
      app: mysql  # WorkloadEntry label
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/app-sa"]
    to:
    - operation:
        methods: ["*"]
```

#### 3. Observabilidad consistente

Las cargas de trabajo de VM proporcionan las mismas métricas, registros y trazabilidad distribuida que los Pods de Kubernetes.

```promql
# Unified metric query for VMs and pods
sum(rate(istio_requests_total{destination_workload="mysql-vm-1"}[5m]))

# Error rate from VM
sum(rate(istio_requests_total{destination_workload="mysql-vm-1",response_code="500"}[5m]))
/
sum(rate(istio_requests_total{destination_workload="mysql-vm-1"}[5m]))
```

### Limitaciones del registro de VM

1. **Instalación manual de Envoy**: se debe instalar y configurar manualmente el proxy Envoy en la VM
2. **Conectividad de red**: se requiere conexión de red entre la VM y el cluster de Kubernetes
3. **Gestión de certificados**: los certificados de cuenta de servicio deben desplegarse en la VM
4. **Carga operativa**: se requiere gestión y actualización de la versión de Envoy en la VM
5. **Limitación de auto-scaling**: no hay auto-scaling como Kubernetes HPA

### Ejemplo de uso práctico

#### Escenario: integración de base de datos heredada

```yaml
# 1. Define database service with ServiceEntry
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: legacy-postgres
  namespace: production
spec:
  hosts:
  - postgres.production.svc.cluster.local
  addresses:
  - 240.240.1.10  # Virtual IP
  ports:
  - number: 5432
    name: postgresql
    protocol: TCP
  location: MESH_INTERNAL
  resolution: STATIC
  workloadSelector:
    labels:
      app: postgres
      tier: database
---
# 2. Register VM instance with WorkloadEntry
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: postgres-vm-1
  namespace: production
spec:
  address: 10.0.1.100  # Actual VM IP
  labels:
    app: postgres
    tier: database
    version: v13
  serviceAccount: postgres-sa
  ports:
    postgresql: 5432
---
# 3. Access control policy
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: postgres-access-control
  namespace: production
spec:
  selector:
    matchLabels:
      app: postgres
  action: ALLOW
  rules:
  - from:
    - source:
        namespaces: ["production"]
        principals: ["cluster.local/ns/production/sa/api-service"]
    to:
    - operation:
        ports: ["5432"]
```

**Resultado**:

* Los Pods de Kubernetes acceden a la base de datos mediante `postgres.production.svc.cluster.local`
* Cifrado mTLS automático entre la VM y los Pods
* Política de control de acceso aplicada
* Métricas y trazabilidad distribuida recopiladas automáticamente

### Resumen de la comparación de registro de cargas de trabajo

```mermaid
flowchart TB
    subgraph Types[Workload Types]
        K8S[Kubernetes Pod<br/>Inside cluster]
        MC[Multi-Cluster<br/>Different cluster]
        VM[Virtual Machine<br/>Outside cluster]
    end

    subgraph Features[Common Features]
        mTLS[mTLS Encryption]
        Traffic[Traffic Management]
        Policy[Security Policy]
        Metrics[Metrics & Tracing]
    end

    K8S & MC & VM --> mTLS
    K8S & MC & VM --> Traffic
    K8S & MC & VM --> Policy
    K8S & MC & VM --> Metrics

    %% Style definitions
    classDef workload fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef feature fill:#326CE5,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class K8S,MC,VM workload;
    class mTLS,Traffic,Policy,Metrics feature;
```

Mediante las capacidades flexibles de registro de cargas de trabajo de Istio:

* **Kubernetes Pod**: aplicaciones cloud-native
* **Multi-Cluster**: multi-cloud, distribución regional, recuperación ante desastres
* **Virtual Machine**: aplicaciones heredadas, bases de datos, entornos híbridos

Todas las cargas de trabajo reciben funcionalidades coherentes de seguridad, gestión de tráfico y observabilidad.

## Siguientes pasos

Ahora comprendes los conceptos básicos de Istio. Aprende a usarlos en la práctica mediante los siguientes documentos:

### Funcionalidades principales

1. [**Gestión de tráfico**](traffic-management/README.md)
   * Uso de Gateway y VirtualService
   * Definición de DestinationRule y subset
   * ServiceEntry y WorkloadEntry (registro de VM)
   * Patrones de enrutamiento avanzados (Canary, pruebas A/B)
   * Traffic Mirroring y Shadowing
2. [**Seguridad**](security/README.md)
   * Configuración de mTLS y PeerAuthentication
   * Autenticación (RequestAuthentication, JWT)
   * Autorización (AuthorizationPolicy)
   * Gestión de políticas de seguridad
   * Integración de autenticación externa
3. [**Observabilidad**](observability/README.md)
   * Recopilación de métricas (Prometheus)
   * Trazabilidad distribuida (Jaeger, Zipkin)
   * Configuración de registros
   * Visualización de Service Mesh con Kiali
   * Dashboards de Grafana
4. [**Resiliencia**](resilience/README.md)
   * Patrón Circuit Breaker
   * Configuración de Retry y Timeout
   * Rate Limiting
   * Outlier Detection
   * Pruebas de Fault Injection

### Temas avanzados

5. [**Temas avanzados**](advanced/README.md)
   * Ambient Mode (malla sin sidecar)
   * Configuración Multi-Cluster
   * Personalización de EnvoyFilter
   * DNS Proxy y Caching
   * Configuración detallada de cargas de trabajo de VM
   * Desarrollo de plugins WASM

## Referencias

* [Documentación oficial de Istio - Conceptos](https://istio.io/latest/docs/concepts/)
* [Documentación oficial de Istio - Gestión de tráfico](https://istio.io/latest/docs/concepts/traffic-management/)
* [Documentación oficial de Istio - Seguridad](https://istio.io/latest/docs/concepts/security/)
* [Documentación oficial de Istio - Observabilidad](https://istio.io/latest/docs/concepts/observability/)
* [Documentación oficial de Envoy Proxy](https://www.envoyproxy.io/docs/envoy/latest/)
