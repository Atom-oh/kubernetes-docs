# Istio

> **Última actualización**: August 31, 2026

Una guía práctica para utilizar Istio Service Mesh en Amazon EKS.

### Actualización de agosto de 2026: lanzamientos de parches de seguridad de Istio 1.30.4 / 1.29.7

El 27 de agosto de 2026 se publicaron los lanzamientos de parches de Istio 1.30.4 y 1.29.7. Estos lanzamientos **contienen correcciones de seguridad ([ISTIO-SECURITY-2026-006](https://istio.io/latest/news/security/istio-security-2026-006/)), por lo que se recomienda actualizar con prontitud**:

- **Se corrigieron 13 CVE de Envoy**: incluidos un use-after-free del heap en el manejo de trailers de HTTP/2 (CVE-2026-73513), una omisión de RBAC mediante `ignore_path_parameters_in_path_matching` (CVE-2026-73553) y agotamiento de memoria de HTTP/2 mediante encabezados Host duplicados descartados (CVE-2026-73550)
- **Se corrigió 1 CVE de Istio**: `BackendTLSPolicy` recurría a texto plano de forma permisiva en proxies sidecar cuando su referencia de CA no se resolvía (GHSA-qm8v-g4f9-qhjx)
- Además, se incluyen numerosas correcciones de estabilidad, como un error de multicluster por el que la gateway/endpoints de red de un clúster remoto podía desaparecer después de la rotación de credenciales

Mientras tanto, los candidatos de lanzamiento de la siguiente versión, 1.31, continuaron desde rc.2 hasta rc.4 entre el 25 y el 27 de agosto, por lo que el lanzamiento oficial está cerca. Consulta el [anuncio oficial de 1.30.4](https://istio.io/latest/news/releases/1.30.x/announcing-1.30.4/) para obtener más detalles.

### Actualización de agosto de 2026: Istio 1.31 entra en RC

El 19 de agosto de 2026, a 1.31.0-beta.2 le siguió el mismo día el primer candidato de lanzamiento, [1.31.0-rc.0](https://github.com/istio/istio/releases), llevando la siguiente versión menor, 1.31, a la etapa de candidato de lanzamiento. Un RC es una versión preliminar para la validación final justo antes de GA: una señal de que el lanzamiento oficial está cerca. Sigue utilizando lanzamientos GA en producción.

### Actualización de agosto de 2026: Istio 1.31 entra en Beta

El proceso de lanzamiento de la siguiente versión menor, Istio 1.31, está en marcha: 1.31.0-alpha.2 se publicó el 11 de agosto de 2026, seguido de 1.31.0-beta.0 el 13 de agosto y 1.31.0-beta.1 el 14 de agosto. Las compilaciones alpha/beta son versiones preliminares para validación temprana, no para uso en producción; utilízalas solo si quieres probar nuevas funcionalidades antes del lanzamiento GA. Consulta la [página de lanzamientos de Istio](https://github.com/istio/istio/releases) para obtener más detalles.

### Actualización de julio de 2026: lanzamientos de parches de Istio 1.30.3 / 1.29.6

El 16 de julio de 2026 se publicaron los lanzamientos de parches de Istio 1.30.3 y 1.29.6. Aspectos destacados de 1.30.3:

- Se mejoró la escalabilidad de istiod en modo ambient al limitar los envíos de XDS de cambios de dirección de workload/service únicamente a los waypoints afectados
- Se corrigió un error por el que istiod no detectaba secretos actualizados de clústeres remotos (por ejemplo, durante la rotación de credenciales/token) hasta reiniciarse
- El nombre del taint del controlador de eliminación de taints de nodos pilot ahora se puede personalizar mediante la variable de entorno `PILOT_NODE_UNTAINT_CONTROLLERS_TAINT_NAME`

Consulta el [anuncio oficial](https://istio.io/latest/news/releases/1.30.x/announcing-1.30.3/) para obtener más detalles.

## Tabla de contenidos

1. [¿Realmente necesitas un Service Mesh?](#do-you-really-need-a-service-mesh)
2. [Instalación y configuración inicial](01-installation.md)
3. [Conceptos básicos](02-basic-concepts.md)
4. [Arquitectura](03-architecture.md)
5. [Integración con AWS](04-aws-integration.md)
6. [Glosario](glossary.md)
7. [Gestión del tráfico](traffic-management/README.md)
8. [Seguridad](security/README.md)
9. [Observabilidad](observability/README.md)
10. [Resiliencia](resilience/README.md)
11. [Avanzado](advanced/README.md)
12. [Solución de problemas](troubleshooting/common-errors.md)
13. [Mejores prácticas](best-practices.md)
14. [Comparación de alternativas](comparison/README.md)

## ¿Qué es Istio?

Istio es una plataforma open source de Service Mesh para conectar, proteger, controlar y observar microservicios. Gestiona la comunicación entre servicios en arquitecturas complejas de microservicios y proporciona control de tráfico, seguridad y observabilidad.

### Concepto de Service Mesh

<div align="center"><img src="https://istio.io/latest/img/service-mesh.svg" alt="Istio Service Mesh" width="800"></div>

Un Service Mesh es una capa de infraestructura que gestiona la comunicación entre microservicios. Istio despliega un Sidecar Proxy (Envoy) junto a cada servicio para interceptar y controlar todo el tráfico de red. Esto proporciona las siguientes capacidades sin modificar el código de la aplicación:

* **Enrutamiento de tráfico**: enrutamiento inteligente, balanceo de carga, despliegues Canary
* **Seguridad**: mTLS automático, autenticación, autorización
* **Observabilidad**: métricas, logs, tracing distribuido
* **Resiliencia**: Circuit Breaking, Retry, Timeout

### Ejemplos prácticos de uso

<p align="center"><img src="https://istio.io/latest/docs/examples/bookinfo/noistio.svg" alt="Aplicación sin Istio"><br><em>Aplicación sin Istio</em></p>

<p align="center"><img src="https://istio.io/latest/docs/examples/bookinfo/withistio.svg" alt="Aplicación con Istio"><br><em>Aplicación con Istio - Envoy Proxy desplegado como Sidecar en cada servicio</em></p>

Cuando se aplica Istio, un Envoy Proxy se despliega automáticamente como un contenedor sidecar en cada microservicio, interceptando y controlando de forma transparente todo el tráfico de red.

## ¿Realmente necesitas un Service Mesh?

Un Service Mesh es una herramienta potente, pero no es adecuado para todas las situaciones. Es necesario considerarlo cuidadosamente antes de adoptarlo.

### Flujo de decisión

![Diagrama de flujo de decisión sobre si adoptar un Service Mesh, basado en el número de microservicios, luego en necesidades complejas de tráfico/seguridad/observabilidad y, por último, en los recursos operativos disponibles.](../../.gitbook/assets/en-service-mesh-istio-README-0.png)

### Cuándo se necesita un Service Mesh ✅

#### 1. Entorno complejo de microservicios

![Comparación que muestra cuatro servicios configurando manualmente mTLS, reintentos y logs sin un mesh, frente a un único Service Mesh que aplica esos controles automáticamente a los mismos cuatro servicios.](../../.gitbook/assets/en-service-mesh-istio-README-1.png)

**Criterios recomendados**:

* ✅ 10 o más microservicios
* ✅ Comunicación frecuente entre servicios (tráfico East-West)
* ✅ Uso de múltiples lenguajes de programación (Polyglot)
* ✅ Varios equipos que desarrollan servicios de forma independiente

#### 2. Requisitos de seguridad Zero Trust

**El Service Mesh proporciona**:

* Cifrado mTLS automático entre servicios
* Gestión de identidad basada en SPIFFE
* Políticas de autenticación/autorización detalladas
* Comunicación cifrada garantizada

**Difícil de lograr sin alternativas**:

* Implementación de lógica de seguridad duplicada en cada servicio
* Complejidad de la gestión manual de certificados
* Políticas de seguridad inconsistentes

#### 3. Gestión avanzada del tráfico

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

* Despliegues Canary, pruebas A/B
* Enrutamiento basado en headers/path
* Traffic Mirroring (Shadow Testing)
* Fault Injection (Chaos Engineering)
* Circuit Breaking, Retry, Timeout

#### 4. Observabilidad unificada

**Ventajas del Service Mesh**:

* Recopilación automática de métricas sin modificación del código de la aplicación
* Implementación automática de Distributed Tracing
* Formato de logging unificado
* Visualización de la topología de servicios (Kiali)

### Cuándo no se necesita un Service Mesh ❌

#### 1. Arquitectura simple

![Una solicitud de usuario que pasa por un balanceador de carga hacia una única aplicación monolítica y su base de datos; lo suficientemente simple como para que un controlador Ingress sea suficiente sin un Service Mesh.](../../.gitbook/assets/en-service-mesh-istio-README-2.png)

**Usa en su lugar**:

* Kubernetes Ingress Controller (NGINX, Traefik)
* Balanceador de carga simple
* Implementación a nivel de aplicación

#### 2. Pocos microservicios (<10)

**La sobrecarga es mayor**:

* La complejidad operativa del Service Mesh > los beneficios obtenidos
* 5-10 servicios se pueden gestionar manualmente
* NetworkPolicy proporciona seguridad suficiente

**Alternativa**:

```yaml
# Kubernetes NetworkPolicy is sufficient
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

#### 3. Recursos operativos insuficientes

**Requisitos operativos del Service Mesh**:

* Experiencia en Istio/Envoy
* Monitoreo y gestión del Control Plane
* Gestión de actualizaciones y parches
* Capacidad de solución de problemas (mayor complejidad de depuración)

**Preparación necesaria del equipo**:

* Al menos 1-2 expertos en Service Mesh
* Aprendizaje continuo y seguimiento de actualizaciones
* Entorno de prueba suficiente

#### 4. Cuando el rendimiento es extremadamente crítico

**Sobrecarga del Service Mesh**:

* Latencia: +1-3ms (P50), +5-10ms (P99)
* CPU: +10-20% por pod
* Memoria: +50-100MB por pod (modo Sidecar)

**Considera alternativas**:

* Ambient Mode (reducción del 90 % en el uso de recursos)
* Soluciones basadas en CNI (Cilium)
* Optimización a nivel de aplicación

### Comparación de soluciones alternativas

| Funcionalidad                    | Service Mesh                                 | CNI (Cilium)    | Ingress Controller | A nivel de aplicación                |
| -------------------------- | -------------------------------------------- | --------------- | ------------------ | ------------------------ |
| **Gestión de tráfico L7**  | ✅ Compatibilidad completa                               | ⚠️ Limitada      | ⚠️ Solo Ingress    | ✅ Posible               |
| **Automatización de mTLS**        | ✅ Compatibilidad completa                               | ✅ Posible      | ❌ No compatible    | ❌ Implementación manual  |
| **Distributed Tracing**    | ✅ Automático                                  | ❌ No compatible | ❌ No compatible    | ⚠️ Implementación manual |
| **Políticas L3/L4**         | ✅ Compatible                                  | ✅ Compatibilidad completa  | ❌ No compatible    | ❌ No compatible          |
| **Complejidad operativa** | 🔴 Alta                                      | 🟡 Media       | 🟢 Baja             | 🟡 Media                |
| **Sobrecarga de recursos**      | <p>🔴 Alta (Sidecar)<br>🟢 Baja (Ambient)</p> | 🟢 Baja          | 🟢 Baja             | 🟢 Ninguna                  |
| **Escala adecuada**         | 10+ servicios                                 | Todas las escalas      | Escala pequeña        | Escala pequeña              |

### Solución basada en CNI (Cilium)

Cilium proporciona muchas funcionalidades en el **nivel de red** basadas en eBPF:

![Comparación tripartita del control de tráfico L7 basado en proxy de Istio, la red a nivel de kernel eBPF de Cilium y los escenarios de uso en los que cada uno —o ambos juntos— es la opción correcta.](../../.gitbook/assets/en-service-mesh-istio-README-3.png)

**Cuándo Cilium es más adecuado**:

* Las políticas de red L3/L4 son el objetivo principal
* El alto rendimiento es un requisito esencial
* Evitar la carga operativa del Service Mesh
* Solo se necesitan mTLS y observabilidad simples

**Referencia**: [Documentación de Cilium](../../networking/cilium/README.md)

### Lista de verificación para la decisión

Responde las siguientes preguntas antes de adoptarlo:

**Arquitectura**:

* [ ] ¿Tienes 10 o más microservicios?
* [ ] ¿La comunicación entre servicios es compleja?
* [ ] ¿Se utilizan múltiples lenguajes de programación?

**Seguridad**:

* [ ] ¿Se necesita un modelo de seguridad Zero Trust?
* [ ] ¿Es obligatorio el cifrado mTLS entre servicios?
* [ ] ¿Se necesita control de acceso detallado?

**Gestión del tráfico**:

* [ ] ¿Se necesitan despliegues Canary y pruebas A/B?
* [ ] ¿Se necesitan reglas de enrutamiento avanzadas?
* [ ] ¿Se necesitan Circuit Breaking y Retry para muchos servicios?

**Observabilidad**:

* [ ] ¿Es obligatorio el tracing distribuido?
* [ ] ¿Se necesita recopilación unificada de métricas?
* [ ] ¿Se necesita visualización de la topología de servicios?

**Operaciones**:

* [ ] ¿Tienes expertos en Service Mesh?
* [ ] ¿Puedes gestionar la complejidad operativa?
* [ ] ¿Puedes aceptar la sobrecarga de recursos?

**Resultados**:

* ✅ 10 o más marcadas: Service Mesh muy recomendado
* 🟡 5-9 marcadas: se necesita una evaluación cuidadosa, empieza poco a poco (se recomienda Ambient Mode)
* ❌ 4 o menos marcadas: considera soluciones alternativas (CNI, Ingress, a nivel de aplicación)

### Estrategia de adopción gradual

Si determinas que se necesita un Service Mesh, adóptalo gradualmente:

![Despliegue en cuatro fases que avanza desde la recopilación de métricas solo para observabilidad, a la seguridad mTLS, a la gestión de tráfico Canary y, finalmente, al conjunto completo de funcionalidades avanzadas; cada fase está condicionada por la validación.](../../.gitbook/assets/en-service-mesh-istio-README-4.png)

**Orden recomendado**:

1. **Proyecto piloto** (1-2 namespaces)
2. **Observabilidad primero** (métricas, logs, traces)
3. **Aplicar seguridad** (mTLS PERMISSIVE → STRICT)
4. **Gestión del tráfico** (VirtualService, DestinationRule)
5. **Expansión en toda la empresa**

### Características principales

1.  **Gestión del tráfico**

    <div align="center"><img src="https://istio.io/latest/docs/concepts/traffic-management/request-routing.svg" alt="Enrutamiento de tráfico" width="500"></div>

    * Enrutamiento inteligente y balanceo de carga
    * Pruebas A/B, despliegue Canary, despliegue Blue/Green
    * Control de Circuit Breaking, Retry, Timeout
    * Traffic Mirroring y Fault Injection
2.  **Seguridad**

    <div align="center"><img src="https://istio.io/latest/docs/concepts/security/arch-sec.svg" alt="Arquitectura de seguridad" width="600"></div>

    * Cifrado mTLS automático entre servicios
    * Autenticación y autorización sólidas
    * Políticas de control de acceso detalladas
    * Aislamiento de red y políticas de seguridad
3.  **Observabilidad**

    <div align="center"><img src="https://istio.io/latest/docs/tasks/observability/kiali/kiali-graph.png" alt="Grafo de servicios de Kiali" width="700"></div>

    * Generación automática de métricas, logs y traces
    * Integración con Prometheus, Grafana, Jaeger y Kiali
    * Visualización de la topología de servicios
    * Monitoreo de tráfico en tiempo real
4. **Resiliencia**
   * Patrón Circuit Breaker
   * Rate Limiting
   * Outlier Detection
   * Zone Aware Routing

### Arquitectura de Istio

<div align="center"><img src="https://istio.io/latest/docs/ops/deployment/architecture/arch.svg" alt="Arquitectura de Istio" width="700"></div>

Istio consta de un Control Plane y un Data Plane:

![Arquitectura que muestra Pilot y Citadel de istiod enviando configuración y certificados a proxies sidecar de Envoy, que transportan las solicitudes de cada aplicación e intercambian tráfico cifrado con mTLS entre pods.](../../.gitbook/assets/en-service-mesh-istio-README-5.png)

**Control Plane (istiod)**:

* **Pilot**: descubrimiento de servicios, gestión de reglas de enrutamiento de tráfico
* **Citadel**: generación y gestión de certificados, habilitación de mTLS
* **Galley**: validación y despliegue de configuración

**Data Plane**:

* **Envoy Proxy**: desplegado como sidecar en cada pod, interceptando y controlando todo el tráfico de red

### Beneficios de usar Istio en Amazon EKS

1. **Gestión sencilla de microservicios**
   * Gestión de tráfico sin modificar el código de la aplicación
   * Aplicación de políticas coherentes con configuración declarativa
   * Utiliza Kubernetes Native API
2. **Seguridad mejorada**
   * Cifrado automático entre servicios
   * Autenticación integrada con AWS IAM
   * Control de permisos detallado
3. **Observabilidad mejorada**
   * Integración con Amazon CloudWatch
   * Tracing distribuido mediante AWS X-Ray
   * Métricas y logs detallados
4. **Integración con servicios de AWS**
   * Integración con Application Load Balancer (ALB)
   * Integración con AWS Certificate Manager (ACM)
   * Compatible con Amazon EBS CSI Driver

### Primeros pasos

<div align="center"><img src="https://istio.io/latest/docs/tasks/traffic-management/ingress/ingress-gateway-example/gateway-api-topology.svg" alt="Arquitectura de Gateway API" width="600"></div>

Si eres nuevo en Istio, lee los documentos en el siguiente orden:

1. [**Instalación y configuración inicial**](01-installation.md): instala Istio en el clúster EKS
2. [**Conceptos básicos**](02-basic-concepts.md): comprende los conceptos principales de Istio
3. [**Gestión del tráfico**](traffic-management/README.md): aprende sobre Gateway, VirtualService, DestinationRule
4. [**Seguridad**](security/README.md): configura mTLS, autenticación y autorización
5. [**Observabilidad**](observability/README.md): recopila métricas, logs y traces
6. [**Mejores prácticas**](best-practices.md): recomendaciones para entornos de producción

### Ejemplos prácticos

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
* [AWS EKS Workshop - Istio](https://www.eksworkshop.com/intermediate/330_servicemesh_using_istio/)
* [Comunidad de Istio](https://discuss.istio.io/)

### Cuestionarios

Para comprobar lo que has aprendido en este capítulo, prueba los siguientes cuestionarios:

* [Cuestionario de gestión del tráfico](../../quizzes/service-mesh/istio/traffic-management.md)
* [Cuestionario de seguridad](../../quizzes/service-mesh/istio/security.md)
* [Cuestionario de observabilidad](../../quizzes/service-mesh/istio/observability.md)
* [Cuestionario de resiliencia](../../quizzes/service-mesh/istio/resilience.md)
* [Cuestionario avanzado](../../quizzes/service-mesh/istio/advanced.md)
