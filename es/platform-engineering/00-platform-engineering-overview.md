# Descripción general de Platform Engineering

> **Última actualización**: February 23, 2026

## 1. ¿Qué es Platform Engineering?

### Definición

Platform Engineering (ingeniería de plataformas) es **la disciplina de diseñar, construir y operar herramientas, flujos de trabajo e infraestructura para el autoservicio de los desarrolladores**. Los equipos de platform engineering construyen una **Internal Developer Platform (IDP)** que permite a los desarrolladores desplegar aplicaciones de forma rápida y segura sin tratar directamente con la complejidad de la infraestructura.

### Internal Developer Platform (IDP)

Una IDP es una plataforma de autoservicio que abstrae tareas operativas como el aprovisionamiento de infraestructura, el despliegue y el monitoreo, para que los desarrolladores puedan centrarse en escribir código.

**Valores fundamentales de una IDP:**

- **Autoservicio**: Los desarrolladores aprovisionan infraestructura directamente sin crear tickets
- **Guardrails**: Seguridad y cumplimiento integrados de forma predeterminada
- **Estandarización**: Patrones de despliegue coherentes mediante Golden Paths
- **Automatización**: Reducción de la carga cognitiva al eliminar tareas repetitivas

### Platform Engineering vs DevOps vs SRE

| Aspecto | Platform Engineering | DevOps | SRE |
|--------|---------------------|--------|-----|
| **Enfoque** | Experiencia del desarrollador y construcción de plataformas de autoservicio | Integración cultural del desarrollo y las operaciones | Confiabilidad del servicio y automatización operativa |
| **Entregables clave** | Internal Developer Platform | Pipelines de CI/CD, scripts de automatización | SLO/SLI, presupuestos de error, automatización del toil |
| **Métricas principales** | Productividad del desarrollador, tiempo de onboarding | Frecuencia de despliegue, lead time | Disponibilidad, tasa de consumo del presupuesto de error |
| **Estructura del equipo** | Equipo de plataforma dedicado | Equipos multifuncionales | Equipo SRE o SREs integrados |
| **Relación** | Capa de producto sobre DevOps + SRE | Cultura y metodología | Práctica de ingeniería operativa |

> **Nota**: Estos tres enfoques son complementarios, no mutuamente excluyentes. Platform Engineering trata de **empaquetar los principios de DevOps y las prácticas de SRE como un producto**.

### Roles y estructura del equipo de plataforma

**Roles clave:**

| Rol | Responsabilidad |
|------|---------------|
| **Platform Product Manager** | Analizar las necesidades de los desarrolladores, gestionar el roadmap de la IDP, definir métricas de éxito |
| **Platform Engineer** | Construir la infraestructura principal de la IDP, automatización de Kubernetes/cloud |
| **Platform SRE** | Confiabilidad de la propia plataforma, monitoreo, respuesta a incidentes |
| **Developer Experience (DX) Engineer** | Herramientas CLI, documentación, flujos de onboarding |

---

## 2. Perspectiva de plataforma de AWS CAF

### Introducción a AWS Cloud Adoption Framework

El [AWS Cloud Adoption Framework (CAF)](https://docs.aws.amazon.com/prescriptive-guidance/latest/aws-caf-platform-perspective/platform-eng.html) proporciona directrices organizacionales para la adopción de la nube. La **Perspectiva de plataforma** cubre tres áreas clave:

1. **Platform Engineering** -- El enfoque de esta sección
2. **Platform Architecture** -- Principios de diseño de arquitectura cloud
3. **Data Architecture** -- Estrategia de gestión de datos y analítica

### Modelo de madurez: START → ADVANCE → EXCEL

AWS CAF define la madurez de una plataforma cloud en tres etapas. Examinemos cómo las herramientas del ecosistema Kubernetes se asignan a cada etapa.

#### START: Construcción de fundamentos

La etapa de establecer infraestructura fundacional y configurar guardrails de seguridad.

| Capacidad | Descripción | Mapeo del ecosistema Kubernetes |
|-----------|-------------|------------------------------|
| **Landing Zone & Guardrails** | Entorno multi-account, controles preventivos/detectivos | Configuración de clústeres EKS, [OPA Gatekeeper](../security/09-opa-gatekeeper.md) / [Kyverno](../security/01-kyverno-policy-management.md) |
| **Autenticación** | Gestión de identidad centralizada, integración con IdP | [Autenticación y autorización de K8s](../security/02-kubernetes-auth-authz.md), OIDC, IRSA |
| **Networking** | Gestión de red centralizada | VPC CNI, [Calico](../networking/calico/README.md), [Cilium](../networking/cilium/README.md) |
| **Logging** | Observabilidad cross-account | [Prometheus](../observability/metrics/01-prometheus.md), [Loki](../observability/logging/01-loki.md), [OpenTelemetry](../observability/tracing/03-opentelemetry.md) |
| **Controles** | Controles de seguridad programáticos | [Pod Security Standards](../security/03-pod-security-standards.md), [Network Policies](../security/04-network-policies.md) |
| **Gestión de costos** | Estrategia de etiquetado, asignación de costos | Resource Quotas, LimitRange, [Optimización de costos de EKS](../eks/07-eks-cost-optimization.md) |

#### ADVANCE: Escalado operativo

La etapa de expandir la automatización y construir observabilidad centralizada.

| Capacidad | Descripción | Mapeo del ecosistema Kubernetes |
|-----------|-------------|------------------------------|
| **Automatización de infraestructura** | IaC, productos de autoservicio | [ACK](./02-ack.md), [KRO](./03-kro.md), Crossplane, [Helm](./01-helm.md) |
| **Observabilidad central** | Correlación de logs/métricas/trazas | Stack de [Grafana](../observability/grafana/README.md), [CloudWatch](../observability/metrics/04-cloudwatch-metrics.md) |
| **Gestión de sistemas** | Estandarización de imágenes, gestión de parches | [Seguridad de imágenes](../security/07-image-security.md), [Kyverno](../security/01-kyverno-policy-management.md) |
| **Gestión de credenciales** | Credenciales temporales, rotación automática | [Gestión de Secrets](../security/05-secrets-management.md), IRSA |
| **Herramientas de seguridad** | XDR, monitoreo granular | [Seguridad en runtime](../security/08-runtime-security.md), Trivy, GuardDuty |

#### EXCEL: Optimización continua

La etapa de lograr gobernanza automatizada y mejora continua.

| Capacidad | Descripción | Mapeo del ecosistema Kubernetes |
|-----------|-------------|------------------------------|
| **Gestión automatizada de identidades** | Roles/policies versionados mediante IaC | Gestión de RBAC basada en [GitOps](../gitops/README.md) |
| **Detección de anomalías** | Evaluación proactiva de vulnerabilidades, detección de patrones anómalos | [Seguridad en runtime](../security/08-runtime-security.md) (Falco), análisis de audit logs |
| **Análisis de amenazas** | Monitoreo continuo frente a benchmarks de la industria | CIS Benchmark, kube-bench |
| **Refinamiento de permisos** | Principio de mínimo privilegio automatizado | Optimización de RBAC basada en audit logs de K8s |
| **Métricas de plataforma** | Métricas alineadas con los objetivos organizacionales | Métricas DORA, SLI/SLO |

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

### Mapeo de roles y herramientas para cada capa

| Capa | Rol | Herramientas clave | Documentos del repo |
|-------|------|-----------|-----------|
| **Interfaz de desarrollador** | UI/CLI con la que interactúan los desarrolladores | Backstage, Port, Argo Workflows UI | - |
| **Integración/Orquestación** | Gestión declarativa del estado, automatización de despliegues | ArgoCD, FluxCD, KRO | [GitOps](../gitops/README.md), [KRO](./03-kro.md) |
| **Recurso** | Abstracción de recursos cloud/K8s | ACK, Helm, Operators | [ACK](./02-ack.md), [Helm](./01-helm.md), [Extensiones de K8s](./04-kubernetes-extensions.md) |
| **Infraestructura** | Cómputo/red/almacenamiento reales | EKS, VPC, IAM | [EKS](../eks/01-eks-introduction.md) |

### Patrón de catálogo de autoservicio (KRO RGD + ACK)

Combinar la ResourceGraphDefinition (RGD) de [KRO](./03-kro.md) con [ACK](./02-ack.md) permite un patrón de autoservicio potente:

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

A partir de este único manifest, KRO crea internamente:
1. **Deployment + Service** (Kubernetes nativo)
2. **RDS Instance** (recurso de AWS mediante ACK)
3. **IAM Role** (configuración de permisos mediante ACK)

Para ver ejemplos detallados, consulta el [Ejemplo de integración de ExampleCorp](./05-example-corp-app.md).

### Concepto de Golden Path

Un Golden Path es la **ruta de despliegue recomendada** proporcionada por el equipo de plataforma:

- **Propósito**: Guiar a los desarrolladores para empezar rápidamente usando métodos validados
- **Características**: Recomendado, no impuesto -- los desarrolladores pueden desviarse cuando sea necesario, pero es la opción óptima en la mayoría de los casos
- **Ejemplos**:
  - Golden Path de "Despliegue de nuevo microservicio": plantilla de Helm Chart → integración con ArgoCD → recopilación automática de métricas de Prometheus
  - Golden Path de "Aprovisionamiento de base de datos": manifest de KRO RGD → creación de RDS mediante ACK → inyección automática de Secret

---

## 4. Ecosistema de herramientas de Platform Engineering

Esta sección mapea dónde encajan las herramientas cubiertas en este repositorio dentro del panorama de platform engineering.

| Categoría | Herramientas | Enlace al documento del repo |
|----------|-------|---------------|
| **Gestión de paquetes** | Helm, Kustomize | [Helm](./01-helm.md) |
| **IaC de AWS** | ACK, CloudFormation | [ACK](./02-ack.md) |
| **Orquestación de recursos** | KRO, Crossplane | [KRO](./03-kro.md) |
| **Mecanismos de extensión** | CRD, Operators | [Mecanismos de extensión de Kubernetes](./04-kubernetes-extensions.md) |
| **GitOps** | ArgoCD, FluxCD | [Sección de GitOps](../gitops/README.md) |
| **Policy/Governance** | Kyverno, OPA Gatekeeper | [Kyverno](../security/01-kyverno-policy-management.md), [OPA Gatekeeper](../security/09-opa-gatekeeper.md) |
| **Observabilidad** | Prometheus, Grafana, OTel | [Sección de observabilidad](../observability/README.md) |
| **Autoscaling** | KEDA, Karpenter | [KEDA](../autoscaling/01-keda.md), [Karpenter](../autoscaling/02-karpenter.md) |
| **Service Mesh** | Istio, Cilium | [Istio](../service-mesh/istio/README.md), [Cilium Service Mesh](../service-mesh/cilium-service-mesh/README.md) |
| **Seguridad** | Falco, Trivy, PSS | [Seguridad en runtime](../security/08-runtime-security.md), [Seguridad de imágenes](../security/07-image-security.md), [PSS](../security/03-pod-security-standards.md) |

---

## 5. Checklist de autoevaluación de madurez de plataforma

Evalúa la madurez de platform engineering de tu organización. Cada elemento enlaza al documento relevante en este repositorio.

### Etapa START

| Verificación | Elemento | Documentos relacionados |
|-------|------|-------------|
| [ ] | ¿Los clústeres EKS se crean de forma estandarizada? | [Creación de clúster EKS](../eks/02-eks-cluster-creation-part1.md) |
| [ ] | ¿Las políticas RBAC están definidas y se aplican? | [Autenticación y autorización](../security/02-kubernetes-auth-authz.md) |
| [ ] | ¿Se aplican Network Policies? | [Network Policies](../security/04-network-policies.md) |
| [ ] | ¿Está configurado el monitoreo y logging básicos? | [Monitoreo de EKS](../eks/06-eks-monitoring-logging.md) |
| [ ] | ¿Se aplican Pod Security Standards? | [PSS](../security/03-pod-security-standards.md) |
| [ ] | ¿Están configurados los resource quotas y limits? | [Optimización de costos de EKS](../eks/07-eks-cost-optimization.md) |

### Etapa ADVANCE

| Verificación | Elemento | Documentos relacionados |
|-------|------|-------------|
| [ ] | ¿La infraestructura se gestiona con IaC? (ACK, Terraform, etc.) | [ACK](./02-ack.md) |
| [ ] | ¿Existe un flujo de trabajo GitOps? | [GitOps](../gitops/README.md) |
| [ ] | ¿Está operativo un stack de observabilidad centralizado? | [Observabilidad](../observability/README.md) |
| [ ] | ¿La gobernanza está automatizada con un policy engine? | [Kyverno](../security/01-kyverno-policy-management.md) |
| [ ] | ¿Los secrets se gestionan automáticamente desde un almacén externo? | [Gestión de Secrets](../security/05-secrets-management.md) |
| [ ] | ¿Está automatizado el escaneo de imágenes de contenedores? | [Seguridad de imágenes](../security/07-image-security.md) |

### Etapa EXCEL

| Verificación | Elemento | Documentos relacionados |
|-------|------|-------------|
| [ ] | ¿Se proporciona a los desarrolladores un catálogo de autoservicio? | [KRO](./03-kro.md), [ExampleCorp](./05-example-corp-app.md) |
| [ ] | ¿Se miden y mejoran las métricas DORA? | - |
| [ ] | ¿Está operativo el monitoreo de seguridad en runtime? | [Seguridad en runtime](../security/08-runtime-security.md) |
| [ ] | ¿El autoscaling está optimizado para las workloads? | [KEDA](../autoscaling/01-keda.md), [Karpenter](../autoscaling/02-karpenter.md) |
| [ ] | ¿Los SLOs de plataforma están definidos y se hace seguimiento de ellos? | [Análisis de observabilidad](../ops/08-observability-analysis.md) |
| [ ] | ¿Los Golden Paths están definidos y documentados? | Este documento (Sección 3) |

---

## 6. Referencias

- [AWS CAF Platform Perspective - Platform Engineering](https://docs.aws.amazon.com/prescriptive-guidance/latest/aws-caf-platform-perspective/platform-eng.html)
- [CNCF Platform White Paper](https://tag-app-delivery.cncf.io/whitepapers/platforms/)
- [Platform Engineering on Kubernetes (O'Reilly)](https://www.oreilly.com/library/view/platform-engineering-on/9781617299322/)
- [Backstage.io - Open Source IDP Framework](https://backstage.io/)
- [Internal Developer Platform](https://internaldeveloperplatform.org/)
