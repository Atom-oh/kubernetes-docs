# Istio

> **Última actualización**: October 12, 2026

Una guía práctica para utilizar Istio Service Mesh en Amazon EKS.

### Revisión de octubre de 2026: versiones compatibles

Istio 1.31.0 es GA; su [anuncio de lanzamiento](https://istio.io/latest/news/releases/1.31.x/announcing-1.31/) se publicó el 31 de agosto de 2026. El parche actual es **1.31.1**, publicado el 21 de septiembre. Su [anuncio de lanzamiento](https://istio.io/latest/news/releases/1.31.x/announcing-1.31.1/) documenta una corrección que evita que una referencia de CA `BackendTLSPolicy` sin resolver recurra a conexiones de backend en texto plano.

Los comandos de instalación nueva de esta guía usan 1.31.1. El rango de soporte de Kubernetes publicado para Istio 1.31 es 1.32–1.37; el soporte estándar de EKS actualmente cubre 1.34–1.37. Su superposición de soporte estándar es 1.34–1.37; de las versiones de soporte extendido de EKS (1.31–1.33), 1.32 y 1.33 también están dentro del rango de Istio 1.31. Vuelva a comprobar la [matriz de soporte de Istio](https://istio.io/latest/docs/releases/supported-releases/) y el [ciclo de vida de versiones de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html) antes de la instalación.

Istio 1.30 y 1.29 siguen figurando como compatibles en la matriz en el momento de esta revisión; la fecha prevista de fin de vida de 1.29 es hoy, 12 de octubre de 2026. Verifique su estado antes de instalar o actualizar. Las instalaciones existentes en esas ramas necesitan al menos 1.30.4 o 1.29.7 para [ISTIO-SECURITY-2026-006](https://istio.io/latest/news/security/istio-security-2026-006/), que cubre vulnerabilidades de Envoy, una conmutación por error abierta de BackendTLSPolicy y una denegación de servicio del Control Plane mediante EnvoyFilter. Istio 1.28 está fuera de soporte. Los charts de Istio 1.31 usan `https://blob.istio.io/istio-release/charts`; el repositorio anterior alojado en Google ya no recibe nuevas versiones.

## Tabla de contenido

1. [¿Realmente necesita un Service Mesh?](#do-you-really-need-a-service-mesh)
2. [Instalación y configuración inicial](01-installation.md)
3. [Conceptos básicos](02-basic-concepts.md)
4. [Arquitectura](03-architecture.md)
5. [Integración con AWS](04-aws-integration.md)
6. [Glosario](glossary.md)
7. [Gestión de tráfico](traffic-management/README.md)
8. [Seguridad](security/README.md)
9. [Observabilidad](observability/README.md)
10. [Resiliencia](resilience/README.md)
11. [Avanzado](advanced/README.md)
12. [Solución de problemas](troubleshooting/common-errors.md)
13. [Prácticas recomendadas](best-practices.md)
14. [Comparación de alternativas](comparison/README.md)

## ¿Qué es Istio?

Istio es una plataforma de service mesh de código abierto para conectar, proteger, controlar y observar microservicios. Gestiona la comunicación entre servicios en arquitecturas complejas de microservicios y proporciona control de tráfico, seguridad y observabilidad.

### Concepto de Service Mesh

<div align="center"><img src="https://istio.io/latest/img/service-mesh.svg" alt="Istio Service Mesh" width="800"></div>

Un service mesh es una capa de infraestructura que gestiona la comunicación entre microservicios. Istio admite sidecars de Envoy y modo ambient (ztunnel a nivel de nodo más waypoints L7 opcionales). Los proxies manejan el tráfico inscrito en el mesh; el tráfico excluido y los protocolos no compatibles quedan fuera de esa cobertura. Esto proporciona las siguientes capacidades sin modificar el código de la aplicación:

* **Enrutamiento de tráfico**: Enrutamiento inteligente, balanceo de carga, deployments Canary
* **Seguridad**: mTLS automático, autenticación, autorización
* **Observabilidad**: Métricas, logs, tracing distribuido
* **Resiliencia**: Circuit Breaking, Retry, Timeout

### Ejemplos de uso prácticos

<p align="center"><img src="https://istio.io/latest/docs/examples/bookinfo/noistio.svg" alt="Aplicación sin Istio"><br><em>Aplicación sin Istio</em></p>

<p align="center"><img src="https://istio.io/latest/docs/examples/bookinfo/withistio.svg" alt="Aplicación con Istio"><br><em>Aplicación con Istio - Envoy Proxy desplegado como Sidecar en cada servicio</em></p>

Estos diagramas de Bookinfo ilustran el modo sidecar. La inyección automática añade Envoy solo a los pods recién creados en namespaces o workloads que se adhieren; el modo ambient no inyecta un sidecar.

## ¿Realmente necesita un Service Mesh?

Los umbrales de cantidad de servicios y las puntuaciones de la lista de verificación siguientes son puntos para debatir, no requisitos de Istio. Un mesh pequeño aún puede justificarse por necesidades de seguridad. Los diagramas de decisión utilizan los mismos umbrales ilustrativos.

Un service mesh es una herramienta potente, pero no es adecuado para todas las situaciones. Se requiere una consideración cuidadosa antes de adoptarlo.

### Flujo de decisión

![Flujo de decisión para adoptar un service mesh: comprobar sucesivamente una arquitectura de microservicios, más de 10 servicios, necesidades complejas de tráfico/seguridad/observabilidad y recursos operativos conduce a mesh recomendado, no necesario, alternativas o revisión cuidadosa.](../../.gitbook/assets/en-service-mesh-istio-overview-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-0.html)

### Cuándo se necesita un Service Mesh ✅

#### 1. Entorno de microservicios complejo

![Comparación lado a lado de cuatro servicios que conectan manualmente mTLS, reintentos y logging sin un mesh frente a un Service Mesh que maneja y controla automáticamente la comunicación entre los mismos cuatro servicios.](../../.gitbook/assets/en-service-mesh-istio-overview-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-1.html)

**Criterios recomendados**:

* ✅ 10 o más microservicios
* ✅ Comunicación frecuente entre servicios (tráfico East-West)
* ✅ Uso de varios lenguajes de programación (Polyglot)
* ✅ Varios equipos que desarrollan servicios de forma independiente

#### 2. Requisitos de seguridad Zero Trust

**El Service Mesh proporciona**:

* Cifrado mTLS automático entre servicios
* Gestión de identidad basada en SPIFFE
* Políticas de autenticación/autorización granulares
* Tráfico del mesh cifrado cuando se aplica mTLS; mTLS automático por sí solo no rechaza clientes en texto plano

**Difícil de conseguir sin alternativas**:

* Implementación de lógica de seguridad duplicada en cada servicio
* Complejidad de la gestión manual de certificados
* Políticas de seguridad incoherentes

#### 3. Gestión avanzada de tráfico

```yaml
# Canary Deployment (Traffic Distribution)
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
      weight: 90
    - destination:
        host: reviews
        subset: v2
      weight: 10  # Only 10% to new version
```

**Cuándo se necesita**:

* Deployments Canary, pruebas A/B
* Enrutamiento basado en header/ruta
* Traffic Mirroring (Shadow Testing)
* Fault Injection (Chaos Engineering)
* Circuit Breaking, Retry, Timeout

#### 4. Observabilidad unificada

**Ventajas del Service Mesh**:

* Recopilación automática de métricas sin modificar el código de la aplicación
* Spans de trace generados por proxy; las aplicaciones deben propagar headers de trace para correlacionar solicitudes
* Formato de logging unificado
* Visualización de topología de servicios (Kiali)

### Cuándo no se necesita un Service Mesh ❌

#### 1. Arquitectura simple

![Una solicitud de usuario que pasa por un balanceador de carga (Ingress Controller) a una única aplicación monolítica y su base de datos — lo bastante simple como para que un ingress controller sea suficiente sin un service mesh.](../../.gitbook/assets/en-service-mesh-istio-overview-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-2.html)

**Use en su lugar**:

* Un Gateway API de Kubernetes o ingress controller mantenido
* Balanceador de carga simple
* Implementación a nivel de aplicación

#### 2. Pocos microservicios (<10)

**La sobrecarga es mayor**:

* Complejidad operativa del Service Mesh > beneficios obtenidos
* 5-10 servicios se pueden gestionar manualmente
* NetworkPolicy puede proporcionar aislamiento L3/L4 cuando el CNI lo aplica; no proporciona mTLS ni autorización HTTP

**Alternativa**:

```yaml
# L3/L4 ingress isolation; requires a NetworkPolicy-capable CNI
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
spec:
  podSelector:
    matchLabels:
      app: backend
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
```

#### 3. Recursos de operaciones insuficientes

**Requisitos operativos del Service Mesh**:

* Experiencia en Istio/Envoy
* Monitorización y gestión del Control Plane
* Gestión de actualizaciones y parches
* Capacidad de solución de problemas (mayor complejidad de depuración)

**Preparación necesaria del equipo**:

* Al menos 1-2 expertos en Service Mesh
* Aprendizaje continuo y seguimiento de actualizaciones
* Entorno de pruebas suficiente

#### 4. Cuando el rendimiento es extremadamente crítico

**Sobrecarga del Service Mesh**:

Mida la latencia, CPU y memoria con tráfico representativo, configuración de proxy y ajustes de telemetría. La [página oficial de rendimiento](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/) registra un benchmark de Istio 1.24; esos resultados históricos no son garantías para otras versiones o workloads.

**Considere alternativas**:

* Modo ambient (proxies L4 compartidos; el ahorro depende del tráfico y del despliegue de waypoint)
* Soluciones basadas en CNI (Cilium)
* Optimización a nivel de aplicación

### Comparación de soluciones alternativas

| Función                    | Service Mesh                                 | CNI (Cilium)    | Ingress Controller | A nivel de aplicación                |
| -------------------------- | -------------------------------------------- | --------------- | ------------------ | ------------------------ |
| **Gestión de tráfico L7**  | ✅ Compatibilidad completa                               | ⚠️ Limitada      | ⚠️ Solo Ingress    | ✅ Posible               |
| **Automatización de mTLS**        | ✅ Compatibilidad completa                               | ⚠️ La autenticación mutua y el cifrado son independientes      | ❌ No compatible    | ❌ Implementación manual  |
| **Tracing distribuido**    | ⚠️ Requiere propagación del contexto de trace                                  | ❌ No compatible | ❌ No compatible    | ⚠️ Implementación manual |
| **Políticas L3/L4**         | ✅ Compatible                                  | ✅ Compatibilidad completa  | ❌ No compatible    | ❌ No compatible          |
| **Complejidad operativa** | 🔴 Alta                                      | 🟡 Media       | 🟢 Baja             | 🟡 Media                |
| **Sobrecarga de recursos**      | <p>🔴 Alta (Sidecar)<br>🟢 Baja (Ambient)</p> | 🟢 Baja          | 🟢 Baja             | 🟢 Ninguna                  |
| **Escala adecuada**         | Depende de los requisitos                                 | Todas las escalas      | Escala pequeña        | Escala pequeña              |

### Solución basada en CNI (Cilium)

Cilium proporciona muchas características a **nivel de red** basadas en eBPF:

![Comparación entre el service mesh basado en proxy L7 de Istio y el CNI a nivel de kernel eBPF de Cilium, vinculada a los escenarios de uso donde la lógica L7 compleja requiere un service mesh, las políticas y el rendimiento requieren Cilium, y las grandes empresas usan ambos.](../../.gitbook/assets/en-service-mesh-istio-overview-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-3.html)

**Cuándo Cilium es más adecuado**:

* Las políticas de red L3/L4 son el propósito principal
* El rendimiento medido con los ajustes de política/cifrado requeridos satisface las necesidades del workload
* Reutilizar un despliegue de Cilium existente cuyas características compatibles satisfacen los requisitos
* La política de red y la observabilidad son necesidades principales; la autenticación mutua out-of-band de Cilium requiere cifrado WireGuard/IPsec independiente para la confidencialidad de la carga útil

Cilium 1.20.1 también proporciona una [beta de cifrado transparente ztunnel](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ztunnel.rst) independiente, seleccionada con `encryption.type: ztunnel`. Proporciona mTLS de workload TCP con inscripción de namespace; ambos endpoints deben estar inscritos. Excluye ClusterMesh y Pods en host network, y la guía publicada advierte que las políticas L4 ordinarias no funcionan en esta ruta salvo cuando se dirigen al puerto HBONE 15008. Esta es una opción de despliegue distinta con sus propios requisitos de CA/bootstrap.

El diagrama enfatiza el rol de CNI; Cilium también tiene características L7 de Envoy. La cantidad de componentes y el coste operativo dependen del modo seleccionado.

**Referencia**: [Documentación de Cilium](../../networking/cilium/README.md)

### Lista de verificación para la decisión

Responda las siguientes preguntas antes de adoptarlo:

**Arquitectura**:

* [ ] ¿Tiene 10 o más microservicios?
* [ ] ¿Es compleja la comunicación entre servicios?
* [ ] ¿Se utilizan varios lenguajes de programación?

**Seguridad**:

* [ ] ¿Se necesita un modelo de seguridad Zero Trust?
* [ ] ¿Es obligatorio el cifrado mTLS entre servicios?
* [ ] ¿Se necesita control de acceso granular?

**Gestión de tráfico**:

* [ ] ¿Se necesitan deployments Canary y pruebas A/B?
* [ ] ¿Se necesitan reglas de enrutamiento avanzadas?
* [ ] ¿Se necesitan Circuit Breaking y Retry para muchos servicios?

**Observabilidad**:

* [ ] ¿Es obligatorio el tracing distribuido?
* [ ] ¿Se necesita recopilación de métricas unificada?
* [ ] ¿Se necesita visualización de topología de servicios?

**Operaciones**:

* [ ] ¿Tiene expertos en Service Mesh?
* [ ] ¿Puede manejar la complejidad operativa?
* [ ] ¿Puede aceptar la sobrecarga de recursos?

**Resultados**:

* ✅ 10 o más marcados: Service Mesh muy recomendado
* 🟡 5-9 marcados: Se necesita una evaluación cuidadosa, comience poco a poco (se recomienda Ambient Mode)
* ❌ 4 o menos marcados: Considere soluciones alternativas (CNI, Ingress, a nivel de aplicación)

### Estrategia de adopción gradual

Si determina que se necesita un Service Mesh, adóptelo gradualmente:

![Despliegue en cuatro fases que pasa de la recopilación de métricas solo para observabilidad, a la seguridad mTLS, a la gestión de tráfico Canary y, por último, al conjunto completo de características avanzadas — cada fase condicionada a validación.](../../.gitbook/assets/en-service-mesh-istio-overview-4.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-4.html)

**Orden recomendado**:

1. **Proyecto piloto** (1-2 namespaces)
2. **Observabilidad primero** (métricas, logs, traces)
3. **Aplicar seguridad** (mTLS PERMISSIVE → STRICT)
4. **Gestión de tráfico** (VirtualService, DestinationRule)
5. **Expansión en toda la empresa**

### Características principales

1.  **Gestión de tráfico**

    VirtualService selecciona rutas; DestinationRule define subsets y políticas de tráfico de destino.

    * Enrutamiento inteligente y balanceo de carga
    * Pruebas A/B, deployment Canary, deployment Blue/Green
    * Control de Circuit Breaking, Retry, Timeout
    * Traffic Mirroring y Fault Injection
2.  **Seguridad**

    <div align="center"><img src="https://istio.io/latest/docs/concepts/security/arch-sec.svg" alt="Arquitectura de seguridad" width="600"></div>

    * Cifrado mTLS automático entre servicios
    * Autenticación y autorización sólidas
    * Políticas de control de acceso granulares
    * Aislamiento de red y políticas de seguridad
3.  **Observabilidad**

    <div align="center"><img src="https://istio.io/latest/docs/tasks/observability/kiali/kiali-graph.png" alt="Grafo de servicios de Kiali" width="700"></div>

    * Métricas de proxy y logs de acceso y tracing configurables
    * Integración con Prometheus, Grafana, Jaeger, Kiali
    * Visualización de topología de servicios
    * Monitorización de tráfico en tiempo real
4. **Resiliencia**
   * Patrón Circuit Breaker
   * Rate Limiting
   * Outlier Detection
   * Zone Aware Routing

### Arquitectura de Istio

<div align="center"><img src="https://istio.io/latest/docs/ops/deployment/architecture/arch.svg" alt="Arquitectura de Istio" width="700"></div>

Istio consta de un Control Plane y un Data Plane:

![Control Plane y Data Plane de Istio: Pilot de istiod envía la configuración de enrutamiento y Citadel emite certificados al sidecar Envoy de cada pod, y los Envoy interceptan las solicitudes de la aplicación e intercambian tráfico cifrado con mTLS.](../../.gitbook/assets/en-service-mesh-istio-overview-5.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-5.html)

**Control Plane (istiod)**:

* Descubrimiento de servicios y configuración de proxy (históricamente Pilot)
* Autoridad de certificados y gestión de identidad (históricamente Citadel)
* Validación de configuración; Galley es un componente independiente retirado, no un servicio independiente actual

**Data Plane**:

* **Modo sidecar**: Envoy por pod inscrito
* **Modo ambient**: ztunnel por nodo para seguridad L4 y proxies waypoint opcionales para procesamiento L7

### Beneficios de usar Istio en Amazon EKS

1. **Gestión sencilla de microservicios**
   * Gestión de tráfico sin modificar el código de la aplicación
   * Aplicación coherente de políticas con configuración declarativa
   * Usa Kubernetes Native API
2. **Seguridad mejorada**
   * Cifrado automático entre servicios
   * Acceso a AWS API mediante EKS Pod Identity o IRSA; la identidad de workload de Istio continúa basada en service account
   * Control de permisos granular
3. **Observabilidad mejorada**
   * Integración con Amazon CloudWatch
   * Tracing distribuido mediante AWS X-Ray
   * Métricas y logs detallados
4. **Integración con servicios de AWS**
   * Integración con Application Load Balancer (ALB)
   * Integración con AWS Certificate Manager (ACM)
   * Compatible con Amazon EBS CSI Driver

### Primeros pasos

[Guía de Gateway API](https://istio.io/latest/docs/tasks/traffic-management/ingress/gateway-api/)

Si es nuevo en Istio, lea los documentos en el siguiente orden:

1. [**Instalación y configuración inicial**](01-installation.md): Instale Istio en un cluster de EKS
2. [**Conceptos básicos**](02-basic-concepts.md): Comprenda los conceptos principales de Istio
3. [**Gestión de tráfico**](traffic-management/README.md): Aprenda Gateway, VirtualService, DestinationRule
4. [**Seguridad**](security/README.md): Configure mTLS, autenticación, autorización
5. [**Observabilidad**](observability/README.md): Recopile métricas, logs, traces
6. [**Prácticas recomendadas**](best-practices.md): Recomendaciones para entornos de producción

### Ejemplos prácticos

Estos extractos de enrutamiento requieren Services y subsets de DestinationRule (`v1`/`v2`) coincidentes; consulte los capítulos de gestión de tráfico.

Cada sección incluye ejemplos YAML funcionales. Todos los ejemplos están estructurados para copiarse con un clic:

```yaml
# Example VirtualService
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
```

### Referencias

* [Documentación oficial de Istio](https://istio.io/latest/docs/)
* [Istio GitHub](https://github.com/istio/istio)
* [Guía de plataforma de Istio para EKS](https://istio.io/latest/docs/setup/platform-setup/amazon-eks/)
* [Comunidad de Istio](https://istio.io/latest/get-involved/)


* [Tracing y propagación de headers de aplicación](https://istio.io/latest/docs/tasks/observability/distributed-tracing/overview/)
* [Capacidades de Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
* [Autenticación mutua de Cilium](https://docs.cilium.io/en/stable/network/servicemesh/mutual-authentication/mutual-authentication/)

### Cuestionarios

Para comprobar lo que ha aprendido en este capítulo, pruebe los siguientes cuestionarios:

* [Cuestionario de gestión de tráfico](../../quizzes/service-mesh/istio/traffic-management.md)
* [Cuestionario de seguridad](../../quizzes/service-mesh/istio/security.md)
* [Cuestionario de observabilidad](../../quizzes/service-mesh/istio/observability.md)
* [Cuestionario de resiliencia](../../quizzes/service-mesh/istio/resilience.md)
* [Cuestionario avanzado](../../quizzes/service-mesh/istio/advanced.md)
