# Guía de operaciones

> **Última actualización**: February 23, 2026

Esta sección proporciona una guía de operaciones de producción para entornos de EKS Auto Mode. Cubre el aprovisionamiento de infraestructura con Terraform, pipelines de CI/CD, deployment basado en GitOps, scaling, observabilidad, optimización de recursos y upgrades.

---

## Audiencia objetivo

- **Platform Engineers** que construyen entornos de producción con EKS Auto Mode
- **Infrastructure Engineers** que operan IaC basada en Terraform/Terragrunt
- **DevOps Engineers** que construyen pipelines de CI/CD con GitLab CI y ArgoCD
- **SREs** que operan stacks de observabilidad con Prometheus, Grafana y Loki

---

## Requisitos previos

Antes de comenzar esta guía de operaciones, asegúrate de estar familiarizado con:

- [Primeros pasos con EKS Auto Mode](../eks-auto-mode/01-getting-started.md)
- Conceptos básicos de Terraform (resources, modules, gestión de state)
- [Conceptos principales de Kubernetes](../core/01-cluster-architecture.md)
- Experiencia con las CLI de kubectl y Helm

---

## Tabla de contenido

| # | Documento | Temas clave |
|---|----------|------------|
| 01 | [Configuración de infraestructura Terraform de 3 capas](./01-infrastructure-setup.md) | VPC, EKS Auto Mode, Pod Identity con Terraform de 3 capas |
| 02 | [Routing ponderado de NLB y Blue/Green](./02-infrastructure-advanced.md) | Arquitectura de doble cluster, pesos de NLB, routing DNS |
| 03 | [Pipelines de CI](./03-ci-pipelines.md) | ECR, GitLab Runner, GitHub ARC, builds multiplataforma |
| 04 | [ArgoCD Multi-Cluster](./04-gitops-multi-cluster.md) | Hub-spoke, ApplicationSet, IAM Identity Center SSO |
| 05 | [Automatización GitOps](./05-gitops-automation.md) | Atlantis, FluxCD, Terraform Cloud, AIOps |
| 06 | [Estrategias de Scaling](./06-scaling-strategies.md) | Métricas personalizadas de HPA, KEDA, VPA, uso de Spot |
| 07 | [Configuración de alertas operativas](./07-observability-alerts.md) | Alertas de Network/CPU/Disk/terminación de node de Auto Mode |
| 08 | [Análisis de observabilidad](./08-observability-analysis.md) | Correlación de Logs/Metrics/Traces, PromQL, LogQL, TraceQL |
| 09 | [Operaciones del stack de observabilidad](./09-observability-stack.md) | Instalación y operaciones de Loki, Tempo, Prometheus/AMP |
| 10 | [Optimización de recursos](./10-resource-optimization.md) | Requests/Limits, tuning de JVM, guía específica por framework |
| 11 | [EKS Upgrades](./11-upgrade-operations.md) | Upgrade sin downtime de Auto Mode, estrategia blue/green |

---

## Ruta de aprendizaje

### Orden recomendado

1. **Infraestructura** (01-02): Aprovisionar VPC/EKS con Terraform
2. **CI/CD** (03-05): Construir pipelines y deployment GitOps
3. **Scaling** (06): Establecer estrategias de scaling para workloads
4. **Observabilidad** (07-09): Construir sistemas de monitoring, alertas y análisis
5. **Optimización** (10): Eficiencia de recursos y optimización de costos
6. **Upgrades** (11): Establecer procedimientos de upgrade sin downtime

### Por rol

| Rol | Documentos prioritarios |
|------|-------------------|
| Platform Engineer | 01, 02, 04, 11 |
| DevOps Engineer | 03, 04, 05 |
| SRE | 06, 07, 08, 09, 10 |
| Infrastructure Engineer | 01, 02, 11 |

---

## Relación con la documentación existente

Esta guía de operaciones complementa la documentación conceptual existente con guías prácticas enfocadas en código:

### Documentación conceptual
- [EKS Auto Mode](../eks-auto-mode/README.md) - Arquitectura y conceptos
- [ArgoCD](../gitops/argocd/README.md) - Fundamentos de GitOps
- [KEDA](../autoscaling/01-keda.md) - Conceptos de autoscaling basado en eventos
- [Karpenter](../autoscaling/02-karpenter.md) - Conceptos de aprovisionamiento de node

### Esta guía de operaciones
- Código Terraform HCL para infraestructura de producción
- Manifests YAML para recursos de Kubernetes
- Consultas PromQL/LogQL para observabilidad
- Scripts Bash para automatización operativa
- Procedimientos paso a paso con validación

---

## Referencia rápida

### Operaciones comunes

| Tarea | Documento | Sección |
|------|----------|---------|
| Crear un nuevo EKS cluster | [01-infrastructure-setup](./01-infrastructure-setup.md) | Terraform de 3 capas |
| Agregar una nueva aplicación a ArgoCD | [04-gitops-multi-cluster](./04-gitops-multi-cluster.md) | ApplicationSet |
| Configurar HPA con métricas personalizadas | [06-scaling-strategies](./06-scaling-strategies.md) | Métricas personalizadas |
| Configurar alertas para un nuevo service | [07-observability-alerts](./07-observability-alerts.md) | Reglas de alerta |
| Actualizar la versión de EKS | [11-upgrade-operations](./11-upgrade-operations.md) | Upgrade de Auto Mode |

### Procedimientos de emergencia

| Escenario | Documento | Sección |
|----------|----------|---------|
| Rollback de Deployment | [04-gitops-multi-cluster](./04-gitops-multi-cluster.md) | Rollback |
| Rollback de upgrade de EKS | [11-upgrade-operations](./11-upgrade-operations.md) | Rollback Blue/Green |
| Reducir escala por costos | [06-scaling-strategies](./06-scaling-strategies.md) | Scaling de emergencia |
| Depurar Pods con fallos | [08-observability-analysis](./08-observability-analysis.md) | Análisis de logs |

---

## Contribuir

Al agregar nuevos procedimientos operativos:

1. Incluye ejemplos prácticos de código (Terraform, YAML, bash)
2. Proporciona pasos de validación para cada procedimiento
3. Documenta procedimientos de rollback donde corresponda
4. Agrega consultas PromQL/LogQL relevantes para monitoring
5. Referencia de forma cruzada la documentación conceptual relacionada
