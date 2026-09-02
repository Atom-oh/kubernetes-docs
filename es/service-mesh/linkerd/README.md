# Linkerd

> **Versiones compatibles**: Linkerd 2.16+ **Última actualización**: August 31, 2026

### Actualización de agosto de 2026: edge-26.8.4

La versión edge-26.8.4, publicada el 25 de agosto de 2026, protege frente a un ExternalWorkload nil en el manejo de protocolos opacos, hace que el controller de políticas negocie la versión de la API TLSRoute con el cluster y actualiza Go a 1.26.7. Consulta las [notas de la versión](https://github.com/linkerd/linkerd2/releases/tag/edge-26.8.4) para obtener más detalles.

### Actualización de agosto de 2026: edge-26.8.2 — Compatibilidad con Gateway API 1.5.1

La versión edge-26.8.2, publicada el 14 de agosto de 2026, añade compatibilidad con Gateway API 1.5.1 (a través de linkerd-kubert 0.27.0) y actualiza la versión máxima de Kubernetes probada a 1.36. También incluye correcciones de estabilidad: elimina un informer Job duplicado en el controller de destino y hace que el controller de políticas finalice si su tarea de observación de lease muere. Consulta las [notas de la versión](https://github.com/linkerd/linkerd2/releases/tag/edge-26.8.2) para obtener más detalles.

### Actualización de julio de 2026: edge-26.7.1 — Solicitudes a puertos de Service no definidos no permitidas

La versión edge-26.7.1, publicada el 16 de julio de 2026, incluye una **corrección que cambia el comportamiento (incompatible)**. Antes, si se definía un ServiceProfile para el Service de destino, las solicitudes a puertos no definidos en el Service seguían estando permitidas. El controller de destino ahora devuelve un `DestinationProfile` vacío para las solicitudes `GetProfile` en puertos no definidos en el Service, lo que hace que el proxy vuelva a la API de políticas del cliente, la cual devuelve correctamente un filtro Forbidden y deniega la conexión. Si algún workload se comunica mediante puertos no declarados en sus recursos Service, limpia las definiciones de puertos antes de actualizar. Consulta las [notas de la versión](https://github.com/linkerd/linkerd2/releases/tag/edge-26.7.1) para obtener más detalles.

## Descripción general

Linkerd es un proyecto graduado de CNCF (Cloud Native Computing Foundation) y una solución ligera de service mesh. Desarrollado originalmente por Buoyant en 2016, fue el proyecto que acuñó por primera vez el término "service mesh". Los valores fundamentales de Linkerd son la simplicidad, la seguridad de forma predeterminada y una sobrecarga mínima de recursos, lo que hace que la comunicación entre servicios en entornos Kubernetes sea segura y confiable.

### Propuestas de valor principales

| Valor                   | Descripción                                                              |
| ----------------------- | ------------------------------------------------------------------------ |
| **Simplicidad**         | Valores predeterminados razonables que funcionan de inmediato sin configuración compleja |
| **Seguridad predeterminada** | Cifrado mTLS automático sin ninguna configuración                      |
| **Ligero**              | Micro-proxy escrito en Rust con uso mínimo de recursos (\~10MB de memoria)  |
| **Rendimiento rápido**  | Menos de 1ms de sobrecarga de latencia p99                                       |
| **Facilidad operativa** | Actualizaciones sencillas y herramientas de depuración intuitivas                            |

## Descripción general de la arquitectura de Linkerd

![Diagrama que muestra cómo los componentes del control plane de Linkerd (Destination, Identity, Proxy Injector) configuran y protegen los sidecars linkerd-proxy inyectados en los Pods de aplicaciones, que intercambian tráfico mediante TLS mutuo, mientras la extensión Viz observa ambos proxies.](../../.gitbook/assets/en-service-mesh-linkerd-README-0.png)

## Comparación de service mesh

Compara Linkerd, Istio y Cilium Service Mesh para comprender las características de cada solución.

| Característica                | Linkerd               | Istio                  | Cilium Service Mesh     |
| ---------------------- | --------------------- | ---------------------- | ----------------------- |
| **Proxy**              | linkerd2-proxy (Rust) | Envoy (C++)            | eBPF + Envoy (opcional) |
| **Uso de recursos**     | Muy bajo (\~10MB)     | Alto (\~50-100MB)      | Bajo (modo eBPF)         |
| **Sobrecarga de latencia**   | <1ms p99              | 2-5ms p99              | <1ms (modo eBPF)        |
| **Complejidad**         | Baja                   | Alta                   | Media                  |
| **mTLS**               | Automático (predeterminado)   | Se requiere configuración | Se requiere configuración  |
| **Gestión de tráfico** | Básica (SMI)           | Muy completa              | Básica                   |
| **Observabilidad**      | Buena (integrada)       | Excelente              | Buena (Hubble)           |
| **Multi-cluster**      | Service Mirroring     | Configuración compleja          | ClusterMesh             |
| **Integración de CNI**    | Independiente              | Independiente               | Nativa                  |
| **Estado de CNCF**        | Graduado             | Graduado              | Graduado               |
| **Curva de aprendizaje**     | Suave                | Pronunciada                  | Media                  |
| **Comunidad**          | Activa                | Muy activa            | Activa                  |

## Cuándo elegir Linkerd

### Casos de uso adecuados

1. **Cuando la simplicidad es importante**
   * Cuando se necesitan capacidades básicas de service mesh en lugar de funciones complejas de gestión de tráfico
   * Equipos de operaciones pequeños o equipos con experiencia limitada en service mesh
   * Cuando la adopción rápida y una curva de aprendizaje baja son prioridades
2. **Cuando la eficiencia de recursos es crítica**
   * Entornos que ejecutan muchos Pods por nodo
   * Cuando se debe minimizar la sobrecarga de los sidecars
   * Aplicaciones sensibles a la latencia
3. **Cuando la seguridad debe ser predeterminada**
   * Cuando se necesita mTLS automático sin configuración
   * Implementación de redes de confianza cero
   * Requisitos de cifrado para cumplimiento normativo
4. **Cuando se requiere simplicidad operativa**
   * Preferencia por procesos de actualización sencillos
   * Mínimos CRDs y configuración
   * Herramientas CLI intuitivas

### Casos de uso menos adecuados

1. **Necesidades avanzadas de gestión de tráfico**
   * Reglas de enrutamiento complejas, manipulación de encabezados
   * Algoritmos avanzados de balanceo de carga
   * Compatibilidad extensa con protocolos (más allá de gRPC)
2. **Integración de workloads de VM**
   * Integración con workloads fuera de Kubernetes
   * Entornos mixtos de VM y contenedores
3. **Entornos multi-protocolo a gran escala**
   * Necesidad de compatibilidad con diversos protocolos (Kafka, MongoDB, etc.)
   * Requisitos complejos de extensiones Wasm

## Estructura de la documentación

Esta sección cubre las principales características y métodos operativos de Linkerd:

| Documento                                       | Descripción                                                                         |
| ---------------------------------------------- | ----------------------------------------------------------------------------------- |
| [Instalación y configuración](01-installation.md)   | Instalación de CLI, instalación del control plane, configuración de HA, extensiones          |
| [Arquitectura](02-architecture.md)             | Detalles sobre el control plane, el data plane y la jerarquía de certificados                            |
| [Gestión de tráfico](03-traffic-management.md) | ServiceProfile, TrafficSplit, reintentos, tiempos de espera, despliegues canary                 |
| [Seguridad](04-security.md)                     | mTLS, políticas de autorización, gestión de certificados, integración de CA externa       |
| [Observabilidad](05-observability.md)           | Métricas, dashboards, herramientas CLI, integración con Prometheus/Grafana, trazabilidad distribuida |
| [Multi-cluster](06-multi-cluster.md)           | Service mirroring, vinculación de clusters, failover                                        |
| [Prácticas recomendadas](07-best-practices.md)         | Lista de verificación de producción, ajuste de rendimiento, solución de problemas                           |

## Inicio rápido

### 1. Instalar Linkerd CLI

```bash
# Linux/macOS
curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh
export PATH=$HOME/.linkerd2/bin:$PATH

# Verify installation
linkerd version
```

### 2. Validación previa del cluster

```bash
# Verify cluster meets Linkerd requirements
linkerd check --pre
```

### 3. Instalar Linkerd

```bash
# Install CRDs
linkerd install --crds | kubectl apply -f -

# Install control plane
linkerd install | kubectl apply -f -

# Verify installation
linkerd check
```

### 4. Añadir la aplicación al mesh

```bash
# Enable automatic injection for namespace
kubectl annotate namespace my-app linkerd.io/inject=enabled

# Restart existing deployments to inject proxy
kubectl rollout restart deployment -n my-app

# Or manually inject
kubectl get deploy -n my-app -o yaml | linkerd inject - | kubectl apply -f -
```

### 5. Instalar y acceder al dashboard

```bash
# Install Viz extension
linkerd viz install | kubectl apply -f -

# Open dashboard
linkerd viz dashboard
```

## Comprobación del estado de los componentes de Linkerd

```bash
# Full status check
linkerd check

# Control plane status
linkerd check --proxy

# Data plane proxy status
linkerd viz stat deploy -n my-app

# Real-time traffic monitoring
linkerd viz tap deploy/my-app -n my-app
```

## Conceptos principales

### Proxy de data plane

Linkerd inyecta un contenedor sidecar llamado `linkerd-proxy` en cada Pod. Este proxy:

* Está escrito en Rust para ofrecer seguridad de memoria y alto rendimiento
* Utiliza solo \~10MB de memoria
* Añade menos de 1ms de latencia
* Gestiona todo el tráfico entrante/saliente
* Aplica automáticamente cifrado mTLS

### Descubrimiento de servicios

El componente Destination supervisa los servicios de Kubernetes y proporciona información de endpoints a los proxies:

* Actualizaciones de endpoints en tiempo real
* Información de enrutamiento basada en ServiceProfile
* Distribución de políticas de división de tráfico

### mTLS automático

Linkerd cifra automáticamente todo el tráfico del mesh sin configuración:

1. El componente Identity emite certificados para cada proxy
2. Autenticación TLS mutua entre proxies
3. Renovación automática de certificados (valor predeterminado de 24 horas)

## Próximos pasos

1. [**Instalación y configuración**](01-installation.md): Guía detallada para instalar Linkerd en tu cluster
2. [**Arquitectura**](02-architecture.md): Comprender la estructura interna de Linkerd
3. [**Cuestionarios**](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/service-mesh/linkerd/README.md): Pon a prueba tus conocimientos

## Referencias

* [Documentación oficial de Linkerd](https://linkerd.io/2/overview/)
* [Linkerd GitHub](https://github.com/linkerd/linkerd2)
* [Página del proyecto Linkerd de CNCF](https://www.cncf.io/projects/linkerd/)
* [Comunidad de Slack de Linkerd](https://slack.linkerd.io/)
* [Blog de Buoyant](https://buoyant.io/blog)
