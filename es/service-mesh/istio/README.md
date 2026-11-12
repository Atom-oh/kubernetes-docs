# Istio

> **Última actualización**: 26 de octubre de 2026

Una guía práctica para utilizar Istio Service Mesh en Amazon EKS.

### Actualización de seguridad de octubre de 2026: versiones 1.31.3, 1.30.7 y 1.29.10

El 22 de octubre de 2026 se publicaron versiones con parches de seguridad para [ISTIO-SECURITY-2026-008](https://istio.io/latest/news/security/istio-security-2026-008/) (CVE-2026-111943): **1.31.3**, **1.30.7** y **1.29.10**; esta última es una versión excepcional, ya que 1.29 llegó al fin de su vida útil el 15 de octubre de 2026. El 20 de octubre de 2026 se reveló que las claves privadas de ocho certificados de CA intermedias de eMudhra estaban comprometidas. Envoy, Go y ztunnel no hacen cumplir la Transparencia de Certificados, por lo que quien poseyera esas claves podría emitir certificados para cualquier dominio de confianza a través de los paquetes de CA públicos incluidos en las imágenes de Istio. Los parches eliminan las CA intermedias comprometidas de los paquetes de CA de las imágenes, compilan istiod, `istioctl` y `pilot-agent` con Go 1.26.10 en 1.30/1.31 (que rechaza las cadenas que contienen las claves comprometidas) y actualizan `rustls-webpki` de ztunnel. Las configuraciones que confían en el paquete de CA del sistema podrían verse afectadas; por ejemplo, un `DestinationRule` con `tls.mode: SIMPLE` y sin `caCertificates`, o las solicitudes de obtención de `jwksUri` de `RequestAuthentication`. Los certificados mTLS de la propia malla de Istio no se ven afectados. Ese mismo día se publicó Istio 1.32.0-beta.0.

### Revisión de octubre de 2026: versiones compatibles

Istio 1.31.0 ya está disponible con carácter general (GA); su [anuncio de lanzamiento](https://istio.io/latest/news/releases/1.31.x/announcing-1.31/) se publicó el 31 de agosto de 2026. El parche actual es **1.31.3**, publicado el 22 de octubre (consulta la actualización de seguridad de octubre de 2026 anterior). El parche 1.31.2, publicado el 15 de octubre, incluye las correcciones de seguridad de [ISTIO-SECURITY-2026-007](https://istio.io/latest/news/security/istio-security-2026-007/) ([anuncio de lanzamiento](https://istio.io/latest/news/releases/1.31.x/announcing-1.31.2/)). Un parche anterior, 1.31.1, se publicó el 21 de septiembre; su [anuncio de lanzamiento](https://istio.io/latest/news/releases/1.31.x/announcing-1.31.1/) documenta una corrección que impide que una referencia de CA no resuelta de `BackendTLSPolicy` provoque una conexión de respaldo en texto sin cifrar con el backend.

Los comandos de instalación nueva de esta guía utilizan la versión 1.31.2. El rango de compatibilidad publicado de Istio 1.31 con Kubernetes es 1.32–1.37; la compatibilidad estándar de EKS abarca actualmente las versiones 1.34–1.37. La intersección de sus rangos de compatibilidad estándar es 1.34–1.37; de las versiones de EKS con compatibilidad extendida (1.31–1.33), 1.32 y 1.33 también están dentro del rango de Istio 1.31. Antes de instalar, vuelve a consultar la [matriz de compatibilidad de Istio](https://istio.io/latest/docs/releases/supported-releases/) y el [ciclo de vida de las versiones de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html).

Istio 1.30 y 1.29 siguen apareciendo como versiones compatibles en la matriz al momento de esta revisión; la fecha de fin de vida útil de 1.29 figura como el 12 de octubre de 2026 (prevista). Verifica su estado antes de instalar o actualizar. Las instalaciones existentes en esas ramas necesitan al menos la versión 1.30.4 o 1.29.7 para [ISTIO-SECURITY-2026-006](https://istio.io/latest/news/security/istio-security-2026-006/), que cubre vulnerabilidades de Envoy, una condición de apertura ante errores de BackendTLSPolicy y una denegación de servicio del plano de control mediante EnvoyFilter. [ISTIO-SECURITY-2026-007](https://istio.io/latest/news/security/istio-security-2026-007/), publicado el 15 de octubre, afecta a las versiones 1.31.0–1.31.1, 1.30.0–1.30.5 y 1.29.0–1.29.8; las primeras versiones que la matriz señala sin CVE conocidos son 1.31.2, 1.30.6 y 1.29.9. Istio 1.28 ya no tiene soporte. Los charts de Istio 1.31 utilizan `https://blob.istio.io/istio-release/charts`; el repositorio anterior alojado en Google ya no recibe nuevas versiones.

### Actualización de septiembre de 2026: parches 1.31.1, 1.30.5 y 1.29.8

El 21 de septiembre de 2026 se publicaron parches para las tres ramas compatibles: [1.31.1](https://istio.io/latest/news/releases/1.31.x/announcing-1.31.1/), 1.30.5 y 1.29.8. La versión 1.31.1 incluye la corrección de seguridad [GHSA-qm8v-g4f9-qhjx](https://github.com/istio/istio/security/advisories/GHSA-qm8v-g4f9-qhjx) (CVSS 6.8, moderada): `BackendTLSPolicy` permite conexiones en texto sin cifrar en los proxies sidecar cuando no se resuelve su referencia de CA. Otras correcciones incluyen el cambio del backend de iptables autodetectado por el agente CNI de nodos del modo ambient (legacy frente a nft) entre reinicios del agente, el aumento del uso de CPU de istiod a medida que crece el número de `AuthorizationPolicies` y una fuga de memoria en el modo ambient multinube al rotar las credenciales de un clúster remoto. Las instalaciones nuevas y las instalaciones existentes de 1.31 deben actualizarse a 1.31.1.

## Tabla de contenido

1. [¿Realmente necesitas una Service Mesh?](#do-you-really-need-a-service-mesh)
2. [Instalación y configuración inicial](01-installation.md)
3. [Conceptos básicos](02-basic-concepts.md)
4. [Arquitectura](03-architecture.md)
5. [Integración con AWS](04-aws-integration.md)
6. [Glosario](glossary.md)
7. [Gestión del tráfico](traffic-management/README.md)
8. [Seguridad](security/README.md)
9. [Observabilidad](observability/README.md)
10. [Resiliencia](resilience/README.md)
11. [Temas avanzados](advanced/README.md)
12. [Solución de problemas](troubleshooting/common-errors.md)
13. [Prácticas recomendadas](best-practices.md)
14. [Comparación de alternativas](comparison/README.md)

## ¿Qué es Istio?

Istio es una plataforma de malla de servicios de código abierto para conectar, proteger, controlar y observar microservicios. Gestiona la comunicación entre servicios en arquitecturas de microservicios complejas y proporciona control del tráfico, seguridad y observabilidad.

### Concepto de Service Mesh

<div align="center"><img src="https://istio.io/latest/img/service-mesh.svg" alt="Istio Service Mesh" width="800"></div>

Una malla de servicios es una capa de infraestructura que gestiona la comunicación entre microservicios. Istio admite sidecars de Envoy y el modo ambient (ztunnel a nivel de nodo más waypoints L7 opcionales). Los proxies gestionan el tráfico incluido en la malla; el tráfico excluido y los protocolos no compatibles quedan fuera de esa cobertura. Esto proporciona las siguientes capacidades sin modificar el código de la aplicación:

* **Enrutamiento del tráfico**: enrutamiento inteligente, balanceo de carga y despliegues canary
* **Seguridad**: mTLS automático, autenticación y autorización
* **Observabilidad**: métricas, registros y trazas distribuidas
* **Resiliencia**: Circuit Breaking, reintentos y tiempos de espera

### Ejemplos prácticos de uso

<p align="center"><img src="https://istio.io/latest/docs/examples/bookinfo/noistio.svg" alt="Application without Istio"><br><em>Aplicación sin Istio</em></p>

<p align="center"><img src="https://istio.io/latest/docs/examples/bookinfo/withistio.svg" alt="Application with Istio"><br><em>Aplicación con Istio: Envoy Proxy desplegado como sidecar en cada servicio</em></p>

Estos diagramas de Bookinfo ilustran el modo sidecar. La inyección automática añade Envoy solo a los pods que se creen en espacios de nombres o cargas de trabajo que la hayan habilitado; el modo ambient no inyecta un sidecar.

## ¿Realmente necesitas una Service Mesh?

Los umbrales de cantidad de servicios y las puntuaciones de las listas de comprobación que aparecen a continuación son puntos de partida para el debate, no requisitos de Istio. Una malla pequeña también puede justificarse por necesidades de seguridad. Los diagramas de decisión utilizan los mismos umbrales ilustrativos.

Una malla de servicios es una herramienta potente, pero no es adecuada para todas las situaciones. Antes de adoptarla, es necesario evaluar cuidadosamente las circunstancias.

### Flujo de decisión

![Flujo de decisión para adoptar una malla de servicios: evaluar sucesivamente si existe una arquitectura de microservicios, si hay 10 o más servicios, si existen necesidades complejas de tráfico/seguridad/observabilidad y si se cuenta con recursos operativos. El proceso conduce a recomendar la malla, no necesitarla, considerar alternativas o hacer una evaluación cuidadosa.](../../.gitbook/assets/en-service-mesh-istio-overview-0.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-0.html)

### Cuándo se necesita una Service Mesh ✅

#### 1. Entorno de microservicios complejo

![Comparación en paralelo de cuatro servicios que configuran manualmente mTLS, reintentos y registros sin una malla, frente a una Service Mesh que gestiona y controla automáticamente la comunicación entre los mismos cuatro servicios.](../../.gitbook/assets/en-service-mesh-istio-overview-1.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-1.html)

**Criterios recomendados**:

* ✅ 10 o más microservicios
* ✅ Comunicación frecuente entre servicios (tráfico este-oeste)
* ✅ Uso de varios lenguajes de programación (políglota)
* ✅ Varios equipos desarrollan servicios de forma independiente

#### 2. Requisitos de seguridad Zero Trust

**Lo que proporciona una Service Mesh**:

* Cifrado mTLS automático entre servicios
* Gestión de identidades basada en SPIFFE
* Políticas detalladas de autenticación y autorización
* Tráfico de malla cifrado cuando se exige mTLS; el mTLS automático por sí solo no rechaza a los clientes que usan texto sin cifrar

**Aspectos difíciles de lograr sin alternativas**:

* Duplicación de la lógica de seguridad en cada servicio
* Complejidad de la gestión manual de certificados
* Políticas de seguridad incoherentes

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

* Despliegues canary y pruebas A/B
* Enrutamiento basado en encabezados o rutas
* Reflejo del tráfico (pruebas en sombra)
* Inyección de fallos (ingeniería del caos)
* Circuit Breaking, reintentos y tiempos de espera

#### 4. Observabilidad unificada

**Ventajas de una Service Mesh**:

* Recopilación automática de métricas sin modificar el código de la aplicación
* Los proxies generan segmentos de traza; las aplicaciones deben propagar los encabezados de traza para correlacionar las solicitudes
* Formato de registro unificado
* Visualización de la topología de servicios (Kiali)

### Cuándo no se necesita una Service Mesh ❌

#### 1. Arquitectura sencilla

![Una solicitud de usuario que pasa por un balanceador de carga (Ingress Controller) hasta una única aplicación monolítica y su base de datos: la arquitectura es lo bastante sencilla como para que baste un controlador Ingress, sin una malla de servicios.](../../.gitbook/assets/en-service-mesh-istio-overview-2.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-2.html)

**En su lugar, utiliza**:

* Un controlador de Kubernetes Gateway API o Ingress con mantenimiento
* Un balanceador de carga sencillo
* Una implementación en la capa de la aplicación

#### 2. Pocos microservicios (<10)

**Los costos generales superan las ventajas**:

* La complejidad operativa de la Service Mesh es mayor que las ventajas que aporta
* De 5 a 10 servicios se pueden gestionar manualmente
* NetworkPolicy puede proporcionar aislamiento L3/L4 cuando lo hace cumplir el CNI; no proporciona mTLS ni autorización HTTP

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

#### 3. Recursos operativos insuficientes

**Requisitos operativos de una Service Mesh**:

* Conocimientos de Istio/Envoy
* Supervisión y gestión del plano de control
* Gestión de actualizaciones y parches
* Capacidad para solucionar problemas (mayor complejidad de depuración)

**Preparación necesaria del equipo**:

* Al menos 1 o 2 especialistas en Service Mesh
* Aprendizaje continuo y seguimiento de las actualizaciones
* Entorno de pruebas suficiente

#### 4. Cuando el rendimiento es extremadamente crítico

**Costos generales de una Service Mesh**:

Mide la latencia, la CPU y la memoria con tráfico representativo, la configuración de los proxies y los ajustes de telemetría. La [página oficial sobre rendimiento](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/) registra un benchmark de Istio 1.24; esos resultados históricos no garantizan el rendimiento de otras versiones o cargas de trabajo.

**Considera alternativas**:

* Modo ambient (proxies L4 compartidos; el ahorro depende del tráfico y del despliegue de waypoints)
* Soluciones basadas en CNI (Cilium)
* Optimización en la capa de la aplicación

### Comparación de soluciones alternativas

| Característica             | Service Mesh                                 | CNI (Cilium)    | Ingress Controller | Nivel de aplicación      |
| -------------------------- | -------------------------------------------- | --------------- | ------------------ | ------------------------ |
| **Gestión del tráfico L7** | ✅ Compatibilidad completa                    | ⚠️ Limitada     | ⚠️ Solo Ingress    | ✅ Posible                |
| **Automatización de mTLS**  | ✅ Compatibilidad completa                    | ⚠️ La autenticación mutua y el cifrado son independientes | ❌ No compatible  | ❌ Implementación manual |
| **Trazado distribuido**     | ⚠️ Requiere propagación del contexto de traza | ❌ No compatible | ❌ No compatible   | ⚠️ Implementación manual |
| **Políticas L3/L4**         | ✅ Compatible                                 | ✅ Compatibilidad completa | ❌ No compatible   | ❌ No compatible         |
| **Complejidad operativa**   | 🔴 Alta                                       | 🟡 Media        | 🟢 Baja            | 🟡 Media                 |
| **Costos de recursos**      | <p>🔴 Altos (sidecar)<br>🟢 Bajos (ambient)</p> | 🟢 Bajos       | 🟢 Bajos           | 🟢 Ninguno               |
| **Escala adecuada**         | Depende de los requisitos                     | Cualquier escala | Escala pequeña    | Escala pequeña           |

### Solución basada en CNI (Cilium)

Cilium ofrece muchas funciones a **nivel de red** basadas en eBPF:

![Comparación entre la malla de servicios de Istio basada en proxy L7 y el CNI de Cilium a nivel del kernel con eBPF, junto con los escenarios de uso: la lógica L7 compleja favorece una malla de servicios, las políticas y el rendimiento favorecen Cilium, y las grandes empresas utilizan ambas soluciones.](../../.gitbook/assets/en-service-mesh-istio-overview-3.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-3.html)

**Cuándo Cilium es más adecuado**:

* El objetivo principal son las políticas de red L3/L4
* El rendimiento medido con los ajustes de política y cifrado necesarios satisface las necesidades de la carga de trabajo
* Se quiere reutilizar un despliegue de Cilium existente cuyas funciones compatibles satisfacen los requisitos
* Las necesidades principales son las políticas de red y la observabilidad; la autenticación mutua fuera de banda de Cilium requiere cifrado independiente con WireGuard/IPsec para mantener la confidencialidad de los datos

Cilium 1.20.1 también ofrece una [versión beta independiente de cifrado transparente con ztunnel](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ztunnel.rst), que se selecciona con `encryption.type: ztunnel`. Proporciona mTLS para cargas de trabajo TCP con incorporación por espacio de nombres; ambos extremos deben estar incorporados. Excluye ClusterMesh y los Pods que utilizan la red del host, y la guía publicada advierte que las políticas L4 habituales no funcionan con esta ruta, salvo cuando se dirigen al puerto HBONE 15008. Es una opción de despliegue distinta, con sus propios requisitos de CA e inicialización.

El diagrama destaca la función del CNI; Cilium también ofrece funciones L7 con Envoy. El número de componentes y el costo operativo dependen del modo elegido.

**Referencia**: [Documentación de Cilium](../../networking/cilium/README.md)

### Lista de comprobación para la decisión

Responde las siguientes preguntas antes de adoptar la solución:

**Arquitectura**:

* [ ] ¿Tienes 10 o más microservicios?
* [ ] ¿Es compleja la comunicación entre servicios?
* [ ] ¿Se utilizan varios lenguajes de programación?

**Seguridad**:

* [ ] ¿Se necesita un modelo de seguridad Zero Trust?
* [ ] ¿Es obligatorio el cifrado mTLS entre servicios?
* [ ] ¿Se necesita un control de acceso detallado?

**Gestión del tráfico**:

* [ ] ¿Se necesitan despliegues canary y pruebas A/B?
* [ ] ¿Se necesitan reglas de enrutamiento avanzadas?
* [ ] ¿Se necesitan Circuit Breaking y reintentos para muchos servicios?

**Observabilidad**:

* [ ] ¿Es obligatorio el trazado distribuido?
* [ ] ¿Se necesita una recopilación unificada de métricas?
* [ ] ¿Se necesita visualizar la topología de servicios?

**Operaciones**:

* [ ] ¿Tienes especialistas en Service Mesh?
* [ ] ¿Puedes gestionar la complejidad operativa?
* [ ] ¿Puedes aceptar el consumo adicional de recursos?

**Resultados**:

* ✅ 10 o más respuestas marcadas: se recomienda encarecidamente una Service Mesh
* 🟡 De 5 a 9 respuestas marcadas: se necesita una evaluación cuidadosa; empieza poco a poco (se recomienda el modo ambient)
* ❌ 4 respuestas marcadas o menos: considera soluciones alternativas (CNI, Ingress o nivel de aplicación)

### Estrategia de adopción gradual

Si determinas que necesitas una Service Mesh, adóptala gradualmente:

![Despliegue en cuatro fases: desde la recopilación de métricas exclusivamente para observabilidad, pasando por la seguridad mTLS y la gestión de tráfico canary, hasta el conjunto completo de funciones avanzadas. Cada fase está condicionada a una validación.](../../.gitbook/assets/en-service-mesh-istio-overview-4.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-4.html)

**Orden recomendado**:

1. **Proyecto piloto** (1 o 2 espacios de nombres)
2. **Primero la observabilidad** (métricas, registros y trazas)
3. **Aplicar la seguridad** (mTLS PERMISSIVE → STRICT)
4. **Gestión del tráfico** (VirtualService, DestinationRule)
5. **Ampliación a toda la empresa**

### Funciones principales

1.  **Gestión del tráfico**

    VirtualService selecciona las rutas; DestinationRule define los subconjuntos y las políticas de tráfico de destino.

    * Enrutamiento inteligente y balanceo de carga
    * Pruebas A/B, despliegues canary y despliegues Blue/Green
    * Control de Circuit Breaking, reintentos y tiempos de espera
    * Reflejo del tráfico e inyección de fallos
2.  **Seguridad**

    <div align="center"><img src="https://istio.io/latest/docs/concepts/security/arch-sec.svg" alt="Security Architecture" width="600"></div>

    * Cifrado mTLS automático entre servicios
    * Autenticación y autorización sólidas
    * Políticas detalladas de control de acceso
    * Aislamiento de red y políticas de seguridad
3.  **Observabilidad**

    <div align="center"><img src="https://istio.io/latest/docs/tasks/observability/kiali/kiali-graph.png" alt="Kiali Service Graph" width="700"></div>

    * Métricas de los proxies y registros de acceso y trazas configurables
    * Integración con Prometheus, Grafana, Jaeger y Kiali
    * Visualización de la topología de servicios
    * Supervisión del tráfico en tiempo real
4. **Resiliencia**
   * Patrón Circuit Breaker
   * Limitación de la tasa
   * Detección de valores atípicos
   * Enrutamiento consciente de la zona

### Arquitectura de Istio

<div align="center"><img src="https://istio.io/latest/docs/ops/deployment/architecture/arch.svg" alt="Istio Architecture" width="700"></div>

Istio consta de un plano de control y un plano de datos:

![Planos de control y de datos de Istio: Pilot de istiod envía la configuración de enrutamiento y Citadel emite certificados al sidecar de Envoy de cada pod. Los Envoy interceptan las solicitudes de la aplicación e intercambian tráfico cifrado con mTLS.](../../.gitbook/assets/en-service-mesh-istio-overview-5.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-5.html)

**Plano de control (istiod)**:

* Descubrimiento de servicios y configuración de proxies (históricamente, Pilot)
* Autoridad de certificación y gestión de identidades (históricamente, Citadel)
* Validación de la configuración; Galley es un componente independiente retirado, no un servicio actual separado

**Plano de datos**:

* **Modo sidecar**: Envoy en cada pod incorporado
* **Modo ambient**: ztunnel en cada nodo para la seguridad L4 y proxies waypoint opcionales para el procesamiento L7

### Ventajas de usar Istio en Amazon EKS

1. **Gestión sencilla de microservicios**
   * Gestión del tráfico sin modificar el código de la aplicación
   * Aplicación coherente de políticas con configuración declarativa
   * Utiliza la API nativa de Kubernetes
2. **Seguridad mejorada**
   * Cifrado automático entre servicios
   * Acceso a la API de AWS mediante EKS Pod Identity o IRSA; la identidad de las cargas de trabajo de Istio sigue basándose en cuentas de servicio
   * Control detallado de permisos
3. **Observabilidad mejorada**
   * Integración con Amazon CloudWatch
   * Trazado distribuido mediante AWS X-Ray
   * Métricas y registros detallados
4. **Integración con servicios de AWS**
   * Integración con Application Load Balancer (ALB)
   * Integración con AWS Certificate Manager (ACM)
   * Compatible con Amazon EBS CSI Driver

### Primeros pasos

[Guía de Gateway API](https://istio.io/latest/docs/tasks/traffic-management/ingress/gateway-api/)

Si estás empezando con Istio, lee los documentos en el siguiente orden:

1. [**Instalación y configuración inicial**](01-installation.md): instala Istio en un clúster de EKS
2. [**Conceptos básicos**](02-basic-concepts.md): comprende los conceptos fundamentales de Istio
3. [**Gestión del tráfico**](traffic-management/README.md): aprende sobre Gateway, VirtualService y DestinationRule
4. [**Seguridad**](security/README.md): configura mTLS, autenticación y autorización
5. [**Observabilidad**](observability/README.md): recopila métricas, registros y trazas
6. [**Prácticas recomendadas**](best-practices.md): recomendaciones para entornos de producción

### Ejemplos prácticos

Estos fragmentos de enrutamiento requieren Services y subconjuntos de DestinationRule (`v1`/`v2`) correspondientes; consulta los capítulos sobre gestión del tráfico.

Cada sección incluye ejemplos YAML funcionales. Todos los ejemplos están estructurados para que se puedan copiar con un clic:

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
* [GitHub de Istio](https://github.com/istio/istio)
* [Guía de Istio para la plataforma EKS](https://istio.io/latest/docs/setup/platform-setup/amazon-eks/)
* [Comunidad de Istio](https://istio.io/latest/get-involved/)


* [Trazado y propagación de encabezados de la aplicación](https://istio.io/latest/docs/tasks/observability/distributed-tracing/overview/)
* [Capacidades de Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
* [Autenticación mutua de Cilium](https://docs.cilium.io/en/stable/network/servicemesh/mutual-authentication/mutual-authentication/)

### Cuestionarios

Para comprobar lo que has aprendido en este capítulo, prueba los siguientes cuestionarios:

* [Cuestionario sobre gestión del tráfico](../../quizzes/service-mesh/istio/traffic-management.md)
* [Cuestionario sobre seguridad](../../quizzes/service-mesh/istio/security.md)
* [Cuestionario sobre observabilidad](../../quizzes/service-mesh/istio/observability.md)
* [Cuestionario sobre resiliencia](../../quizzes/service-mesh/istio/resilience.md)
* [Cuestionario sobre temas avanzados](../../quizzes/service-mesh/istio/advanced.md)
