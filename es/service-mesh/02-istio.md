# Istio

> **Versiones compatibles**: Istio 1.28.0
> **Versión de EKS**: 1.34 (Kubernetes 1.28+)
> **Última actualización**: February 23, 2026

## Índice

- [Introducción](#introduction)
- [Características principales](#key-features)
- [Descripción general de la arquitectura](#architecture-overview)
- [Documentación detallada](#detailed-documentation)
- [Inicio rápido](#quick-start)
- [Recursos de aprendizaje](#learning-resources)

## Introducción

Istio es una plataforma de service mesh de código abierto para aplicaciones de microservicios. Un service mesh es una capa de infraestructura que gestiona la comunicación entre servicios, lo que permite controlar y observar la comunicación entre servicios sin modificar el código de la aplicación.

### ¿Qué es un Service Mesh?

Un service mesh proporciona las siguientes capacidades principales:

1. **Gestión del tráfico**: Controla el flujo de tráfico entre servicios
2. **Seguridad**: Cifrado y autenticación de la comunicación entre servicios
3. **Observabilidad**: Visibilidad de la comunicación entre servicios

### Beneficios principales de Istio

- **Independencia de la plataforma**: Funciona en diversos entornos (Kubernetes, VM, etc.)
- **Integración transparente**: Puede aplicarse sin cambios en el código de la aplicación
- **mTLS automático**: Cifrado automático de la comunicación entre servicios
- **Gestión avanzada del tráfico**: Enrutamiento, balanceo de carga, inyección de fallos, etc.
- **Métricas detalladas**: Métricas detalladas sobre la comunicación entre servicios
- **Aplicación de políticas**: Control de acceso y limitación de tasa

## Características principales

### 1. Gestión del tráfico

Istio proporciona potentes capacidades de gestión del tráfico:

- **Gateway**: Enruta el tráfico externo hacia el mesh
- **VirtualService**: Define reglas de enrutamiento entre servicios
- **DestinationRule**: Configura el balanceo de carga y los grupos de conexiones
- **División del tráfico**: Compatibilidad con deployments Canary y pruebas A/B
- **Integración con Argo Rollouts**: Entrega progresiva automatizada

### 2. Seguridad

Características de seguridad integrales:

- **mTLS**: Cifrado automático entre servicios
- **Authorization Policy**: Control de acceso detallado
- **Request Authentication**: Autenticación basada en JWT
- **Peer Authentication**: Políticas de autenticación entre servicios

### 3. Observabilidad

Visibilidad completa del service mesh:

- **Métricas**: Integración con Prometheus
- **Trazado distribuido**: Compatibilidad con Jaeger/Zipkin
- **Registro**: Registros de acceso y registro estructurado
- **Visualización**: Panel de Kiali

### 4. Resiliencia

Patrones de resiliencia de servicios:

- **Circuit Breaker**: Prevención de sobrecargas
- **Retry**: Reintentos automáticos
- **Timeout**: Configuración del tiempo de espera de solicitudes
- **Outlier Detection**: Excluye instancias no saludables
- **Rate Limiting**: Limitación de la tasa de solicitudes

## Descripción general de la arquitectura

Istio consta de un **Control Plane** y un **Data Plane**.

```mermaid
flowchart TB
    subgraph ControlPlane[Control Plane]
        Istiod[istiod<br/>Service Discovery, Configuration Management, Certificate Management]
    end

    subgraph DataPlane[Data Plane]
        subgraph Pod1[Pod A]
            App1[App Container]
            Proxy1[Envoy Proxy]
        end

        subgraph Pod2[Pod B]
            App2[App Container]
            Proxy2[Envoy Proxy]
        end

        subgraph Pod3[Pod C]
            App3[App Container]
            Proxy3[Envoy Proxy]
        end
    end

    Istiod -->|Configuration Distribution| Proxy1
    Istiod -->|Configuration Distribution| Proxy2
    Istiod -->|Configuration Distribution| Proxy3

    Proxy1 <-->|mTLS| Proxy2
    Proxy2 <-->|mTLS| Proxy3
    Proxy1 <-->|mTLS| Proxy3

    %% Style definitions
    classDef controlPlane fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef dataPlane fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef app fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class Istiod controlPlane;
    class Proxy1,Proxy2,Proxy3 dataPlane;
    class App1,App2,App3 app;
```

### Control Plane (istiod)

istiod es el componente de control central de Istio y proporciona:

- **Service Discovery**: Mantiene el registro de servicios del mesh
- **Configuration Management**: Almacena y distribuye la configuración de Istio
- **Certificate Management**: Genera y rota certificados para mTLS

### Data Plane (Envoy Proxy)

Envoy es un proxy de alto rendimiento implementado como sidecar en cada Pod:

- **Enrutamiento del tráfico**: Controla el tráfico entre servicios
- **Balanceo de carga**: Distribuye el tráfico entre instancias de servicios
- **Seguridad**: Cifrado y autenticación mTLS
- **Observabilidad**: Recopila métricas, registros y trazas

## Documentación detallada

Guías detalladas para todas las características de Istio.

### 📚 Documentación básica

| Documento | Descripción |
|----------|-------------|
| [Guía de instalación](istio/installation.md) | Instalación y configuración inicial de Istio |
| [Conceptos principales](istio/core-concepts.md) | Conceptos básicos y terminología de Istio |
| [Componentes](istio/components.md) | Arquitectura y componentes de Istio |

### 🚦 Gestión del tráfico

| Documento | Descripción |
|----------|-------------|
| [Gateway y VirtualService](istio/traffic-management/01-gateway-virtualservice.md) | Configuración de Gateway de Ingress/Egress |
| [Enrutamiento](istio/traffic-management/02-routing.md) | Reglas de enrutamiento de VirtualService |
| [DestinationRule](istio/traffic-management/03-destination-rule.md) | Políticas de tráfico de servicios |
| [División del tráfico](istio/traffic-management/04-traffic-splitting.md) | Deployment Canary y pruebas A/B |
| [Timeout y Retry](istio/traffic-management/05-retry-timeout.md) | Políticas de Timeout y Retry |
| [Balanceo de carga](istio/traffic-management/06-load-balancing.md) | Diversas estrategias de balanceo de carga |
| [Circuit Breaker](istio/traffic-management/07-circuit-breaker.md) | Implementación del patrón Circuit Breaker |
| [Inyección de fallos](istio/traffic-management/08-fault-injection.md) | Ingeniería del caos |
| [Duplicación de tráfico](istio/traffic-management/09-traffic-mirror.md) | Duplicación de tráfico y pruebas shadow |
| [Afinidad de sesión](istio/traffic-management/10-session-affinity.md) | Configuración de afinidad de sesión |

### 🔐 Seguridad

| Documento | Descripción |
|----------|-------------|
| [mTLS](istio/security/01-mtls.md) | Configuración de mTLS entre servicios |
| [Authorization Policy](istio/security/02-authorization-policy.md) | Políticas de control de acceso |
| [Request Authentication](istio/security/03-request-authentication.md) | Autenticación basada en JWT |
| [Peer Authentication](istio/security/04-peer-authentication.md) | Autenticación entre servicios |

### 📊 Observabilidad

| Documento | Descripción |
|----------|-------------|
| [Métricas](istio/observability/01-metrics.md) | Recopilación de métricas de Prometheus |
| [Trazado distribuido](istio/observability/02-distributed-tracing.md) | Integración con Jaeger/Zipkin |
| [Registro](istio/observability/03-logging.md) | Registros de acceso y registro estructurado |
| [Visualización](istio/observability/04-visualization.md) | Paneles de Kiali y Grafana |

### 💪 Resiliencia

| Documento | Descripción |
|----------|-------------|
| [Outlier Detection](istio/resilience/01-outlier-detection.md) | Detección de instancias no saludables |
| [Rate Limiting](istio/resilience/02-rate-limiting.md) | Limitación de tasa local y global |
| [Enrutamiento según la zona](istio/resilience/03-zone-aware-routing.md) | Enrutamiento con reconocimiento de localidad |

### 🚀 Temas avanzados

| Documento | Descripción |
|----------|-------------|
| [Modo Ambient](istio/advanced/01-ambient-mode.md) | Service mesh sin sidecar |
| [Multi-cluster](istio/advanced/02-multi-cluster.md) | Configuración de mesh Multi-cluster |
| [EnvoyFilter](istio/advanced/03-envoy-filter.md) | Personalización de Envoy |
| [Caché de DNS](istio/advanced/04-dns-cache.md) | Mejora del rendimiento con caché de DNS |
| [gRPC](istio/advanced/05-grpc.md) | Compatibilidad con el protocolo gRPC |
| [WebSocket](istio/advanced/06-websocket.md) | Compatibilidad con conexiones WebSocket |
| [Inyección de sidecar](istio/advanced/07-sidecar-injection.md) | Mecanismo de inyección de sidecar |
| [Argo Rollouts](istio/advanced/08-argo-rollouts.md) | Integración de entrega progresiva |

### ✅ Prácticas recomendadas

| Documento | Descripción |
|----------|-------------|
| [Prácticas recomendadas](istio/best-practices.md) | Lista de verificación y recomendaciones para producción |

## Inicio rápido

### 1. Requisitos previos

- Clúster de Kubernetes (v1.28+)
- kubectl configurado
- Privilegios de administrador

### 2. Instalar Istio

```bash
# Download Istioctl
curl -L https://istio.io/downloadIstio | sh -
cd istio-1.28.0
export PATH=$PWD/bin:$PATH

# Install with default profile
istioctl install --set profile=default -y

# Enable Sidecar injection on namespace
kubectl label namespace default istio-injection=enabled
```

### 3. Implementar la aplicación de ejemplo

```bash
# Deploy Bookinfo sample application
kubectl apply -f samples/bookinfo/platform/kube/bookinfo.yaml

# Create Gateway
kubectl apply -f samples/bookinfo/networking/bookinfo-gateway.yaml

# Verify installation
kubectl get pods
kubectl get svc istio-ingressgateway -n istio-system
```

### 4. Enviar tráfico

```bash
# Check Ingress Gateway address
export INGRESS_HOST=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
export INGRESS_PORT=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.spec.ports[?(@.name=="http2")].port}')
export GATEWAY_URL=$INGRESS_HOST:$INGRESS_PORT

# Access application
curl -s "http://${GATEWAY_URL}/productpage"
```

### 5. Acceder a las herramientas de observabilidad

```bash
# Kiali dashboard
istioctl dashboard kiali

# Prometheus
istioctl dashboard prometheus

# Grafana
istioctl dashboard grafana

# Jaeger
istioctl dashboard jaeger
```

## Recursos de aprendizaje

### Documentación oficial

- [Documentación oficial de Istio](https://istio.io/latest/docs/)
- [Repositorio de GitHub de Istio](https://github.com/istio/istio)
- [Documentación de Envoy Proxy](https://www.envoyproxy.io/docs/envoy/latest/)

### Relacionado con AWS

- [AWS EKS Workshop - Istio](https://www.eksworkshop.com/docs/security/servicemesh/)
- [AWS App Mesh frente a Istio](https://aws.amazon.com/blogs/containers/choosing-between-aws-app-mesh-and-istio/)

### Comunidad

- [Istio Discuss](https://discuss.istio.io/)
- [Istio Slack](https://istio.slack.com/)
- [Grupo de trabajo de CNCF sobre Istio](https://github.com/cncf/tag-app-delivery)

### Recursos adicionales

- [Patrones de Service Mesh (O'Reilly)](https://www.oreilly.com/library/view/service-mesh-patterns/9781492086444/)
- [Istio en acción (Manning)](https://www.manning.com/books/istio-in-action)
- [Guía de optimización del rendimiento de Istio](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/)

## Cuestionario

Para evaluar tu comprensión de Istio, prueba el [Cuestionario de Istio](../quizzes/service-mesh/02-istio-quiz.md).

El cuestionario abarca los siguientes temas:

- Conceptos básicos de service mesh
- Arquitectura de Istio
- Gestión del tráfico (deployment Canary)
- Seguridad (mTLS)
- Gateway e Ingress
- Herramientas de observabilidad
- Tendencias recientes de service mesh
- Rate Limiting
- Enrutamiento por localidad
- Integración con Amazon EKS

---

**Próximos pasos**: Consulta la [Guía de instalación](istio/installation.md) para instalar Istio y aprende los conceptos básicos en [Conceptos principales](istio/core-concepts.md).
