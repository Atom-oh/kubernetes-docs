# Descripción general de Platform Engineering

> **Última actualización**: September 12, 2026

## 1. ¿Qué es Platform Engineering?

### Definición

Platform Engineering es **la disciplina de diseñar, construir y operar herramientas, flujos de trabajo e infraestructura para el autoservicio de los desarrolladores**. Los equipos de platform engineering crean una **Internal Developer Platform (IDP)** que permite a los desarrolladores desplegar aplicaciones de forma rápida y segura sin enfrentarse directamente a la complejidad de la infraestructura.

### Internal Developer Platform (IDP)

Una IDP es una plataforma de autoservicio que abstrae tareas operativas como el aprovisionamiento de infraestructura, el despliegue y la monitorización, para que los desarrolladores puedan centrarse en escribir código.

**Valores fundamentales de una IDP:**

- **Autoservicio**: Solicitar recursos/acciones aprobados mediante APIs, CLIs o portales
- **Guardrails**: Implementar y verificar políticas de seguridad, rutas de aprobación y auditoría
- **Estandarización**: Patrones de despliegue coherentes mediante Golden Paths
- **Automatización**: Reducción de la carga cognitiva al eliminar tareas repetitivas

### Platform Engineering vs DevOps vs SRE

| Aspecto | Platform Engineering | DevOps | SRE |
|--------|---------------------|--------|-----|
| **Enfoque** | Experiencia del desarrollador y construcción de plataformas de autoservicio | Integración cultural del desarrollo y las operaciones | Fiabilidad del servicio y automatización operativa |
| **Entregables clave** | Internal Developer Platform | Pipelines de CI/CD, scripts de automatización | SLO/SLI, presupuestos de error, automatización de toil |
| **Métricas principales** | Productividad de los desarrolladores, tiempo de onboarding | Frecuencia de despliegue, lead time | Disponibilidad, tasa de consumo del presupuesto de error |
| **Estructura del equipo** | Equipo de plataforma dedicado | Equipos multifuncionales | Equipo de SRE o SREs integrados |
| **Relación** | Práctica de plataforma orientada al producto que colabora con DevOps y SRE | Cultura y metodología | Práctica de ingeniería operativa |

> **Nota**: Estos tres enfoques son complementarios, no mutuamente excluyentes. Platform Engineering consiste en **empaquetar los principios de DevOps y las prácticas de SRE como un producto**.

### Roles y estructura del equipo de plataforma

**Roles clave:**

| Rol | Responsabilidad |
|------|---------------|
| **Platform Product Manager** | Analizar las necesidades de los desarrolladores, gestionar el roadmap de la IDP, definir métricas de éxito |
| **Platform Engineer** | Construir la infraestructura central de la IDP, automatización de Kubernetes/cloud |
| **Platform SRE** | Fiabilidad de la propia plataforma, monitorización, respuesta ante incidentes |
| **Developer Experience (DX) Engineer** | Herramientas CLI, documentación, flujos de trabajo de onboarding |

---

## 2. Perspectiva de plataforma de AWS CAF

### Introducción a AWS Cloud Adoption Framework

La [perspectiva de plataforma de AWS CAF](https://docs.aws.amazon.com/whitepapers/latest/overview-aws-cloud-adoption-framework/platform-perspective.html) tiene siete capacidades: arquitectura de plataforma, arquitectura de datos, platform engineering, ingeniería de datos, aprovisionamiento y orquestación, desarrollo de aplicaciones modernas e integración continua/entrega continua. Esta guía se centra en platform engineering.

### Modelo de madurez: START → ADVANCE → EXCEL

La guía detallada de platform engineering de AWS organiza las tareas de mejora en Start, Advance y Excel. Las correspondencias/lista de verificación de Kubernetes que aparecen a continuación son ejemplos didácticos de esta guía, no un cuadro de puntuación de certificación oficial ni una secuencia obligatoria para cada organización.

#### START: Construcción de bases

La etapa de establecer la infraestructura fundamental y configurar guardrails de seguridad.

| Capacidad | Descripción | Correspondencia en el ecosistema Kubernetes |
|-----------|-------------|------------------------------|
| **Landing Zone & Guardrails** | Entorno multicuenta, controles preventivos/detectivos | Configuración del clúster EKS, [OPA Gatekeeper](../security/09-opa-gatekeeper.md) / [Kyverno](../security/01-kyverno-policy-management.md) |
| **Authentication** | Gestión centralizada de identidades, integración de IdP | [Autenticación y autorización de K8s](../security/02-kubernetes-auth-authz.md), OIDC, IRSA |
| **Networking** | Gestión centralizada de red | VPC CNI, [Calico](../networking/calico/README.md), [Cilium](../networking/cilium/README.md) |
| **Observability** | Recopilar/proteger logs, métricas y trazas | [Prometheus](../observability/metrics/01-prometheus.md), [Loki](../observability/logging/01-loki.md), [OpenTelemetry](../observability/tracing/03-opentelemetry.md) |
| **Controls** | Controles de seguridad programáticos | [Pod Security Standards](../security/03-pod-security-standards.md), [Network Policies](../security/04-network-policies.md) |
| **Cost Management** | Estrategia de etiquetado, asignación de costes | Etiquetas de facturación, asignación de uso y costes, [Optimización de costes de EKS](../eks/07-eks-cost-optimization.md) |

#### ADVANCE: Escalado operativo

La etapa de ampliar la automatización y crear observabilidad centralizada.

| Capacidad | Descripción | Correspondencia en el ecosistema Kubernetes |
|-----------|-------------|------------------------------|
| **Infrastructure Automation** | IaC, productos de autoservicio | [ACK](./02-ack.md), [KRO](./03-kro.md), Crossplane, [Helm](./01-helm.md) |
| **Central Observability** | Correlación de logs/métricas/trazas | Stack de [Grafana](../observability/grafana/README.md), [CloudWatch](../observability/metrics/04-cloudwatch-metrics.md) |
| **Systems Management** | Estandarización de imágenes, gestión de parches | [Seguridad de imágenes](../security/07-image-security.md), [Kyverno](../security/01-kyverno-policy-management.md) |
| **Credential Management** | Credenciales temporales, rotación automática | [Gestión de Secrets](../security/05-secrets-management.md), IRSA |
| **Security Tooling** | XDR, monitorización granular | [Runtime Security](../security/08-runtime-security.md), Trivy, GuardDuty |

#### EXCEL: Optimización continua

La etapa de lograr una gobernanza automatizada y una mejora continua.

| Capacidad | Descripción | Correspondencia en el ecosistema Kubernetes |
|-----------|-------------|------------------------------|
| **Automated Identity Management** | Roles/políticas controlados por versión mediante IaC | Gestión de RBAC basada en [GitOps](../gitops/README.md) |
| **Anomaly Detection** | Evaluación proactiva de vulnerabilidades, detección de patrones anómalos | [Runtime Security](../security/08-runtime-security.md) (Falco), análisis de logs de auditoría |
| **Threat Analysis** | Monitorización continua frente a benchmarks del sector | CIS Benchmark, kube-bench |
| **Permission Refinement** | Principio automatizado de mínimo privilegio | Optimización de RBAC basada en logs de auditoría de K8s |
| **Platform Metrics** | Métricas alineadas con los objetivos organizacionales | Métricas DORA, SLI/SLO |

---

## 3. Arquitectura de referencia de IDP

### Estructura de capas de una IDP basada en Kubernetes

```
┌─────────────────────────────────────────────────────┐
│            Developer Interface Layer                  │
│      (Backstage, Port, CLI, GitOps UI)               │
├─────────────────────────────────────────────────────┤
│         Integration/Orchestration Layer               │
│      (ArgoCD, FluxCD, Crossplane, KRO)               │
├─────────────────────────────────────────────────────┤
│                Resource Layer                         │
│      (ACK, Helm Charts, Operators, CRDs)             │
├─────────────────────────────────────────────────────┤
│              Infrastructure Layer                     │
│      (EKS, VPC, IAM, S3, RDS, ...)                   │
└─────────────────────────────────────────────────────┘
```

### Correspondencia de roles y herramientas para cada capa

| Capa | Rol | Herramientas clave | Documentación del repositorio |
|-------|------|-----------|-----------|
| **Developer Interface** | UI/CLI con la que interactúan los desarrolladores | Backstage, Port, Argo Workflows UI | [Backstage](./06-backstage-idp.md) |
| **Integration/Orchestration** | Gestión declarativa del estado, automatización de despliegues | ArgoCD, FluxCD, KRO | [GitOps](../gitops/README.md), [KRO](./03-kro.md) |
| **Resource** | Abstracción de recursos cloud/K8s | ACK, Helm, Operators | [ACK](./02-ack.md), [Helm](./01-helm.md), [Extensiones de K8s](./04-kubernetes-extensions.md) |
| **Infrastructure** | Cómputo/red/almacenamiento reales | EKS, VPC, IAM | [EKS](../eks/01-eks-introduction.md) |

### Patrón de catálogo de autoservicio (KRO RGD + ACK)

La combinación de ResourceGraphDefinition (RGD) de [KRO](./03-kro.md) con [ACK](./02-ack.md) permite un potente patrón de autoservicio:

```yaml
# Single manifest written by developers
apiVersion: kro.run/v1alpha1
kind: WebApplication
metadata:
  name: my-app
spec:
  name: my-app
  image: my-app:v1.0
  replicas: 3
  database:
    engine: postgresql
    instanceClass: db.t3.medium
```

La WebApplication anterior es una **API de plataforma personalizada que debe definirse previamente**, no un tipo integrado de Kubernetes/kro. Sin su RGD/CRD generado, el objeto no se puede aplicar. Esta descripción general no proporciona un RGD completo ni crea recursos.

Cuando un RGD declara explícitamente recursos de Deployment, Service y ACK RDS/IAM, kro gestiona los objetos/dependencias de Kubernetes y los controladores de servicio ACK relevantes llaman a las APIs de AWS. El conjunto de recursos resultante depende de ese RGD. Valide por separado los controladores/CRDs, RBAC/IAM, cuotas, disponibilidad/errores, entrega de credenciales y políticas de eliminación/retención. Crear un CR no garantiza la disponibilidad inmediata de AWS ni un aprovisionamiento transaccional. Consulte el [ejemplo de ExampleCorp](./05-example-corp-app.md) y la [guía de kro](./03-kro.md).

### Concepto de Golden Path

Un Golden Path es la **ruta de despliegue recomendada** proporcionada por el equipo de plataforma:

- **Propósito**: Guiar a los desarrolladores para comenzar rápidamente usando métodos validados
- **Características**: Ruta recomendada compatible; las excepciones siguen la aprobación organizacional y no pueden omitir las políticas obligatorias de seguridad/datos
- **Ejemplos**:
  - Golden Path de "New Microservice Deployment": plantilla Helm validada → integración de ArgoCD → publicación/recopilación de métricas configurada
  - Golden Path de "Database Provisioning": RGD validado → ciclo de vida de ACK RDS → entrega de credenciales aprobada

---

## 4. Ecosistema de herramientas de Platform Engineering

Esta sección muestra dónde encajan las herramientas cubiertas en este repositorio dentro del panorama de platform engineering.

| Categoría | Herramientas | Enlace a documentación del repositorio |
|----------|-------|---------------|
| **Gestión de paquetes** | Helm, Kustomize | [Helm](./01-helm.md) |
| **AWS IaC** | ACK, CloudFormation | [ACK](./02-ack.md) |
| **Orquestación de recursos** | KRO, Crossplane | [KRO](./03-kro.md) |
| **Mecanismos de extensión** | CRD, Operators | [Mecanismos de extensión de Kubernetes](./04-kubernetes-extensions.md) |
| **GitOps** | ArgoCD, FluxCD | [Sección de GitOps](../gitops/README.md) |
| **Políticas/Gobernanza** | Kyverno, OPA Gatekeeper | [Kyverno](../security/01-kyverno-policy-management.md), [OPA Gatekeeper](../security/09-opa-gatekeeper.md) |
| **Observabilidad** | Prometheus, Grafana, OTel | [Sección de observabilidad](../observability/README.md) |
| **Autoscaling** | KEDA, Karpenter | [KEDA](../autoscaling/01-keda.md), [Karpenter](../autoscaling/02-karpenter.md) |
| **Service Mesh** | Istio, Cilium | [Istio](../service-mesh/istio/README.md), [Cilium Service Mesh](../service-mesh/cilium-service-mesh/README.md) |
| **Seguridad** | Falco, Trivy, PSS | [Runtime Security](../security/08-runtime-security.md), [Seguridad de imágenes](../security/07-image-security.md), [PSS](../security/03-pod-security-standards.md) |

---

## 5. Lista de verificación de autoevaluación de la madurez de plataforma

Evalúe la madurez de platform engineering de su organización. Cada elemento enlaza con el documento correspondiente de este repositorio.

### Etapa START

| Verificación | Elemento | Documentos relacionados |
|-------|------|-------------|
| [ ] | ¿Los clústeres EKS se crean de forma estandarizada? | [Creación de clústeres EKS](../eks/02-eks-cluster-creation-part1.md) |
| [ ] | ¿Las políticas RBAC están definidas y se aplican? | [Autenticación y autorización](../security/02-kubernetes-auth-authz.md) |
| [ ] | ¿Se aplican Network Policies? | [Network Policies](../security/04-network-policies.md) |
| [ ] | ¿Está configurada la monitorización y el logging básicos? | [Monitorización de EKS](../eks/06-eks-monitoring-logging.md) |
| [ ] | ¿Se aplican Pod Security Standards? | [PSS](../security/03-pod-security-standards.md) |
| [ ] | ¿Se han establecido cuotas y límites de recursos? | [Optimización de costes de EKS](../eks/07-eks-cost-optimization.md) |

### Etapa ADVANCE

| Verificación | Elemento | Documentos relacionados |
|-------|------|-------------|
| [ ] | ¿La infraestructura se gestiona con IaC? (ACK, Terraform, etc.) | [ACK](./02-ack.md) |
| [ ] | ¿Existe un flujo de trabajo de GitOps? | [GitOps](../gitops/README.md) |
| [ ] | ¿Está operativa una pila de observabilidad centralizada? | [Observabilidad](../observability/README.md) |
| [ ] | ¿La gobernanza está automatizada con un motor de políticas? | [Kyverno](../security/01-kyverno-policy-management.md) |
| [ ] | ¿Los Secrets se gestionan automáticamente desde un almacén externo? | [Gestión de Secrets](../security/05-secrets-management.md) |
| [ ] | ¿Está automatizado el escaneo de imágenes de contenedor? | [Seguridad de imágenes](../security/07-image-security.md) |

### Etapa EXCEL

| Verificación | Elemento | Documentos relacionados |
|-------|------|-------------|
| [ ] | ¿Se proporciona un catálogo de autoservicio a los desarrolladores? | [KRO](./03-kro.md), [ExampleCorp](./05-example-corp-app.md) |
| [ ] | ¿Las métricas DORA se miden/mejoran en un ámbito de servicio adecuado? | [Definiciones actuales de DORA](https://dora.dev/guides/dora-metrics/) |
| [ ] | ¿Está operativa la monitorización de Runtime Security? | [Runtime Security](../security/08-runtime-security.md) |
| [ ] | ¿El autoscaling está optimizado para las cargas de trabajo? | [KEDA](../autoscaling/01-keda.md), [Karpenter](../autoscaling/02-karpenter.md) |
| [ ] | ¿Los SLO de la plataforma están definidos y se siguen? | [Análisis de observabilidad](../ops/08-observability-analysis.md) |
| [ ] | ¿Los Golden Paths están definidos y documentados? | Este documento (Sección 3) |

---

### Métricas y éxito del producto de plataforma

La guía actual de DORA describe cinco métricas: lead time de cambio, frecuencia de despliegue, tiempo de recuperación de despliegues fallidos, tasa de fallos de cambio y tasa de retrabajo de despliegues. No las mezcle con las cuatro métricas anteriores ni con el MTTR genérico. Úselas para mejorar la entrega y la estabilidad en el contexto de un servicio/equipo, no para clasificar a individuos. Mida también el tiempo de onboarding, el éxito de las tareas, la satisfacción de los usuarios y la adopción. La medición no tiene que esperar hasta Excel.

Una IDP es más que un portal: incluye APIs, CLIs, plantillas, documentación, soporte y responsabilidades operativas. No transfiere todas las responsabilidades de seguridad de las aplicaciones fuera de los equipos de desarrollo. Valide la aplicación de guardrails, las excepciones, los cambios y la recuperación.

## 6. Referencias

- [Perspectiva de plataforma de AWS CAF - Platform Engineering](https://docs.aws.amazon.com/prescriptive-guidance/latest/aws-caf-platform-perspective/platform-eng.html)
- [Documento técnico de plataformas de CNCF](https://tag-app-delivery.cncf.io/whitepapers/platforms/)
- [Backstage.io - Framework de IDP de código abierto](https://backstage.io/)
- [Internal Developer Platform](https://internaldeveloperplatform.org/)

- [Métricas DORA actuales](https://dora.dev/guides/dora-metrics/)
