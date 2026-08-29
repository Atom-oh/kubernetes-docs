# Guía de comparación

> **Última actualización**: July 7, 2026
> **Público objetivo**: Arquitectos, ingenieros DevOps, ingenieros de plataforma

Esta sección compara diversas soluciones de Service Mesh y redes, y presenta las ventajas y desventajas de cada solución, junto con los casos de uso adecuados.

## Tabla de contenidos

### 1. [Comparación de soluciones de Service Mesh](01-service-mesh-comparison.md)

Comparación de las principales soluciones de Service Mesh disponibles en entornos Kubernetes:

* **Istio** - Service Mesh de nivel empresarial y con abundantes funcionalidades
* **Linkerd** - Service Mesh ligero y fácil de usar
* **Kong Mesh** - Service Mesh universal basado en Kuma
* **Consul Connect** - Solución de Service Mesh de HashiCorp

**Criterios de comparación**:

* Arquitectura y componentes
* Rendimiento y uso de recursos
* Conjunto de funcionalidades (gestión de tráfico, seguridad, observabilidad)
* Curva de aprendizaje y complejidad operativa
* Soporte para múltiples clústeres
* Escalabilidad y soporte de plataformas

### 2. [Istio vs VPC Lattice](02-istio-vs-lattice.md)

Comparación entre Kubernetes Service Mesh (Istio) y las redes de servicios nativas de AWS (VPC Lattice):

**Istio Service Mesh**:

* Service Mesh centrado en Kubernetes
* Funcionalidades completas de gestión de tráfico y observabilidad
* Neutral respecto a la nube

**AWS VPC Lattice**:

* Redes de servicios nativas de AWS
* Arquitectura serverless
* Conectividad simplificada entre múltiples cuentas/VPC

**Criterios de comparación**:

* Arquitectura y modelo de implementación
* Funcionalidades de gestión de tráfico
* Modelo de seguridad
* Sobrecarga operativa
* Estructura de costes
* Soporte híbrido y multinube

### 3. [Guía de selección entre el modo Sidecar y Ambient](03-sidecar-vs-ambient.md)

Una guía de decisión basada en resultados de pruebas para elegir entre el modo sidecar y el modo ambient de Istio en EKS 1.36:

* Resultados de pruebas frente a 4 requisitos: mTLS, NetworkPolicy, latencia y rollout sin tiempo de inactividad (waypoint 503)
* Datos medidos que muestran una mayor tasa de 503 a través del waypoint ambient que del sidecar
* Una recomendación de implementación mixta por niveles según el nivel de workload (núcleo / seminúcleo / periferia)

**Criterios de comparación**:

* Aplicación y verificación de mTLS
* Interacción de NetworkPolicy con el puerto HBONE
* Tasa de 503 durante los rollouts (medida)
* Riesgo de la política de reintentos en API no idempotentes

## Guía de selección

### Criterios de selección de Service Mesh

![Diagrama de flujo de dos rutas de decisión para elegir un service mesh: una ruta que prioriza la plataforma Kubernetes y termina en Istio, Linkerd o Consul/Kong Mesh, y una ruta centrada en AWS que termina en VPC Lattice, Istio en EKS, Istio Multi-cluster o una solución regional.](../../../.gitbook/assets/en-service-mesh-istio-comparison-README-0.png)

### Recomendaciones de casos de uso

#### Gran empresa

**Recomendado**: Istio

* Conjunto de funcionalidades completo
* Control de tráfico granular
* Seguridad sólida (Authorization Policies, mTLS)
* Federación de múltiples clústeres
* Ecosistema y comunidad extensos

**Alternativa**: Kong Mesh (cuando se necesita un control plane universal)

#### Startup / inicio rápido

**Recomendado**: Linkerd

* Instalación y operación sencillas
* Baja sobrecarga de recursos
* Curva de aprendizaje rápida
* mTLS y métricas automáticas

**Alternativa**: VPC Lattice (para arquitecturas centradas en AWS)

#### Arquitectura nativa de AWS

**Recomendado**: VPC Lattice

* Servicio totalmente gestionado
* Sobrecarga operativa cero
* Integración con servicios de AWS (Lambda, ECS, EKS)
* Conectividad sencilla entre VPC/cuentas

**Alternativa**: Istio en EKS (cuando se necesitan funcionalidades más completas)

#### Multinube / híbrido

**Recomendado**: Istio o Consul Connect

* Neutral respecto a la nube
* Soporte para workloads de VM
* Federación de múltiples clústeres
* Políticas y observabilidad coherentes

#### Integración de sistemas heredados

**Recomendado**: Consul Connect o Kong Mesh

* Soporte prioritario para workloads de VM
* Migración gradual posible
* Integración con Service Discovery
* Soporte para diversas plataformas

#### Requisitos estrictos de observabilidad

**Recomendado**: Istio

* Métricas completas (Prometheus, OpenTelemetry)
* Trazado distribuido (Jaeger, Zipkin, Tempo)
* Registros de acceso detallados
* Integración con Kiali
* Dashboards de Grafana

**Alternativa**: Linkerd (para requisitos sencillos de observabilidad)

## Tablas de comparación rápida

### Comparación de Service Mesh

| Criterios               | Istio        | Linkerd        | Kong Mesh   | Consul Connect |
| ---------------------- | ------------ | -------------- | ----------- | -------------- |
| **Arquitectura**       | Envoy proxy  | Linkerd2-proxy | Envoy proxy | Consul proxy   |
| **Uso de recursos**     | Alto         | Bajo           | Medio       | Medio          |
| **Curva de aprendizaje**     | Pronunciada        | Suave         | Media       | Media          |
| **Riqueza de funcionalidades**   | 5/5          | 3/5            | 4/5         | 4/5            |
| **Múltiples clústeres**      | Excelente    | Compatible      | Excelente   | Excelente      |
| **Soporte de VM**         | Limitado      | Ninguno           | Excelente   | Excelente      |
| **Comunidad**          | Muy grande   | Mediana         | Mediana      | Grande          |
| **Soporte empresarial** | Google Cloud | Buoyant        | Kong        | HashiCorp      |

### Comparación de Istio vs VPC Lattice

| Criterios                   | Istio             | VPC Lattice                 |
| -------------------------- | ----------------- | --------------------------- |
| **Modelo de implementación**       | Autogestionado      | Totalmente gestionado               |
| **Plataforma**               | Kubernetes        | AWS (EKS, ECS, EC2, Lambda) |
| **Complejidad operativa** | Alta              | Baja                         |
| **Riqueza de funcionalidades**       | 5/5               | 3/5                         |
| **Control de tráfico**        | Muy granular | Básico                       |
| **Modelo de costes**             | Basado en recursos    | Basado en el uso                 |
| **Dependencia del proveedor**         | Baja               | Alta (AWS)                  |
| **Multinube**            | Compatible         | Solo AWS                    |

## Recursos relacionados

### Documentación de Istio

* [Arquitectura de Istio](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/service-mesh/istio/istio/architecture/README.md)
* [Gestión de tráfico de Istio](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/service-mesh/istio/istio/traffic-management/README.md)
* [Seguridad de Istio](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/service-mesh/istio/istio/security/README.md)
* [Observabilidad de Istio](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/service-mesh/istio/istio/observability/README.md)

### Documentación de VPC Lattice

* [Descripción general de VPC Lattice](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/service-mesh/istio/vpc-lattice.md)

### Referencias externas

* [Documentación oficial de Istio](https://istio.io/latest/docs/)
* [Documentación oficial de Linkerd](https://linkerd.io/2.15/overview/)
* [Documentación oficial de Kong Mesh](https://docs.konghq.com/mesh/)
* [Documentación de Consul Connect](https://www.consul.io/docs/connect)
* [Documentación de AWS VPC Lattice](https://docs.aws.amazon.com/vpc-lattice/)

## Guías de migración

### De Linkerd a Istio

* Cuando se necesitan más funcionalidades
* Migración gradual: transición por namespace
* Transición de configuración basada en anotaciones a Istio CRD

### De Kubernetes básico a Service Mesh

* Aumento de las necesidades de gestión de tráfico, seguridad y observabilidad
* Implementación Canary: comenzar con algunos servicios
* Evaluar el impacto de la inyección de sidecar

### De VPC Lattice a Istio (o viceversa)

* Requisitos multinube frente a preferencia por AWS nativo
* Riqueza de funcionalidades frente a simplicidad operativa
* Enfoque híbrido: uso simultáneo posible

## Preguntas frecuentes

<details>

<summary>P1: ¿Es absolutamente necesario Service Mesh?</summary>

**Respuesta**: Service Mesh se recomienda en los siguientes casos:

* Decenas o más microservicios
* Necesidad de control de tráfico granular (Canary, pruebas A/B)
* Requisitos estrictos de seguridad (mTLS, Authorization)
* Trazado distribuido y observabilidad
* Comunicación entre múltiples clústeres

Para **servicios pequeños** o **arquitecturas simples**, Kubernetes Service e Ingress básicos pueden ser suficientes.

</details>

<details>

<summary>P2: ¿Debo elegir Istio o Linkerd?</summary>

**Elegir Istio**:

* Cuando se necesitan funcionalidades completas
* Entornos de grandes empresas
* Control de tráfico y políticas granulares
* Federación de múltiples clústeres

**Elegir Linkerd**:

* Cuando se necesita un inicio sencillo y rápido
* Cuando la eficiencia de recursos es importante
* Cuando solo se necesitan funcionalidades básicas de Service Mesh
* Cuando se busca minimizar la complejidad operativa

</details>

<details>

<summary>P3: ¿Cuándo debo usar VPC Lattice?</summary>

**VPC Lattice recomendado**:

* Arquitectura centrada en AWS
* Entorno mixto de EKS + ECS + Lambda
* Estrategia que prioriza serverless
* Minimizar la sobrecarga operativa
* Conectividad simplificada entre múltiples VPC/cuentas

**Istio recomendado** (en lugar de VPC Lattice):

* Estrategia multinube
* Necesidad de control de tráfico granular
* Requisitos completos de observabilidad
* Arquitectura centrada en Kubernetes

</details>

<details>

<summary>P4: ¿Cuál es la sobrecarga de rendimiento de Service Mesh?</summary>

**Istio**:

* Aumento de latencia: 1-3ms (promedio)
* Sobrecarga de CPU: 5-15%
* Memoria: +50-150MB por pod

**Linkerd**:

* Aumento de latencia: 0.5-1ms (promedio)
* Sobrecarga de CPU: 3-8%
* Memoria: +20-50MB por pod

**VPC Lattice**:

* Sin sobrecarga de infraestructura al ser un servicio gestionado
* Ligero aumento de la latencia debido a un salto de red adicional
* Se incurre en un coste basado en el uso

</details>

<details>

<summary>P5: ¿Puedo usar varios Service Mesh simultáneamente?</summary>

**Respuesta**: Técnicamente es posible, pero no se recomienda.

**Problemas**:

* Posibles conflictos de sidecar
* Resolución de problemas compleja
* Sobrecarga doble
* Separación de responsabilidades poco clara

**Casos de uso excepcionales**:

* **Istio + VPC Lattice**: Istio para el interior del clúster, VPC Lattice para la conectividad entre clústeres/externa
* **Migración gradual**: de Linkerd a Istio (transición por namespace)

</details>

***

**Próximos pasos**: Lea los documentos de comparación detallados y seleccione la solución más adecuada para su entorno.
