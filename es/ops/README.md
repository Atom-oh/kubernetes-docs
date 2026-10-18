# Guía de operaciones

> **Última actualización**: 12 de septiembre de 2026

Esta sección ofrece una guía de operaciones de producción para entornos de EKS Auto Mode. Abarca el aprovisionamiento de infraestructura con Terraform, los procesos de CI/CD, la implementación mediante GitOps, el escalado, la observabilidad, la optimización de recursos y las actualizaciones.

---

## Público objetivo

- **Ingenieros de plataforma** que crean entornos de producción con EKS Auto Mode
- **Ingenieros de infraestructura** que operan infraestructura como código basada en Terraform/Terragrunt
- **Ingenieros de DevOps** que crean procesos de CI/CD con GitLab CI y ArgoCD
- **Ingenieros de SRE** que operan pilas de observabilidad con Prometheus, Grafana y Loki

---

## Requisitos previos

Antes de empezar esta guía de operaciones, asegúrate de conocer:

- [Primeros pasos con EKS Auto Mode](../eks-auto-mode/01-getting-started.md)
- Los conceptos básicos de Terraform (recursos, módulos y gestión del estado)
- [Conceptos fundamentales de Kubernetes](../core/01-cluster-architecture.md)
- El uso de las CLI de kubectl y Helm

---

## Tabla de contenido

| N.º | Documento | Temas principales |
|---|----------|------------|
| 01 | [Configuración de infraestructura en tres capas con Terraform](./01-infrastructure-setup.md) | VPC, EKS Auto Mode e identidad de pods con Terraform en tres capas |
| 02 | [Enrutamiento ponderado de NLB y despliegues azul/verde](./02-infrastructure-advanced.md) | Arquitectura de clústeres duales, ponderación de NLB y enrutamiento DNS |
| 03 | [Procesos de CI](./03-ci-pipelines.md) | ECR, GitLab Runner, GitHub ARC y compilaciones multiplataforma |
| 04 | [ArgoCD multiclúster](./04-gitops-multi-cluster.md) | Arquitectura concentrador-radial, ApplicationSet e inicio de sesión único con IAM Identity Center |
| 05 | [Automatización de GitOps](./05-gitops-automation.md) | Atlantis, FluxCD, Terraform Cloud y AIOps |
| 06 | [Estrategias de escalado](./06-scaling-strategies.md) | Métricas personalizadas de HPA, KEDA, VPA y uso de instancias Spot |
| 07 | [Configuración de alertas operativas](./07-observability-alerts.md) | Alertas de red, CPU, disco y terminación de nodos de Auto Mode |
| 08 | [Análisis de observabilidad](./08-observability-analysis.md) | Correlación de registros, métricas y trazas; PromQL, LogQL y TraceQL |
| 09 | [Operaciones de la pila de observabilidad](./09-observability-stack.md) | Instalación y operación de Loki, Tempo y Prometheus/AMP |
| 10 | [Optimización de recursos](./10-resource-optimization.md) | Solicitudes y límites, ajuste de JVM y guía específica para cada marco de trabajo |
| 11 | [Actualizaciones de EKS](./11-upgrade-operations.md) | Actualizaciones escalonadas de Auto Mode y estrategia azul/verde |
| 12 | [Planificación de capacidad para eventos](./12-event-capacity-planning.md) | Eventos de tráfico, planificación de capacidad y recuperación |
| 13 | [Gestión de costos con FinOps](./13-finops-cost-platform.md) | Visibilidad, asignación y optimización de costos |
| 14 | [Procesos de Tekton](./14-tekton-pipelines.md) | Procesos de CI nativos de Kubernetes |
| 15 | [Operaciones de clústeres zonales](./15-zonal-operations-guide.md) | Ajuste de pesos de balanceadores y TargetGroupBinding, reversión nativa y lecturas de Kafka/Redis/Aurora con afinidad de zona de disponibilidad |
| 16 | [Guía de resolución de problemas](./16-troubleshooting-playbook.md) | Síntoma → diagnóstico → causa → solución: Pending, ImagePull, CrashLoop, NotReady, PVC, IRSA, VPC CNI, Karpenter y guía rápida de kubectl |
| 17 | [Experimentos de producción con EKS Spot](./17-spot-production-experiments.md) | Interrupciones, recuperación simultánea, alternativa, registros de resultados, evaluación de SLO/costos y reversión |

---

## Ruta de aprendizaje

### Orden recomendado

1. **Infraestructura** (01–02): aprovisionar VPC/EKS con Terraform
2. **CI/CD** (03–05): crear procesos de CI e implementar con GitOps
3. **Escalado** (06): definir estrategias de escalado para las cargas de trabajo
4. **Observabilidad** (07–09): crear sistemas de supervisión, alertas y análisis
5. **Optimización** (10): mejorar la eficiencia de los recursos y optimizar costos
6. **Actualizaciones** (11): validar la disponibilidad y los procedimientos de recuperación
7. **Operaciones especializadas** (12–16): eventos de capacidad, FinOps, Tekton, operaciones zonales y resolución de problemas

### Según el puesto

| Puesto | Documentos prioritarios |
|------|-------------------|
| Ingeniero de plataforma | 01, 02, 04, 11 |
| Ingeniero de DevOps | 03, 04, 05 |
| Ingeniero de SRE | 06, 07, 08, 09, 10 |
| Ingeniero de infraestructura | 01, 02, 11 |

---

## Relación con la documentación existente

Esta guía complementa la documentación conceptual existente con guías prácticas centradas en el código:

### Documentación conceptual
- [EKS Auto Mode](../eks-auto-mode/README.md): arquitectura y conceptos
- [ArgoCD](../gitops/argocd/README.md): fundamentos de GitOps
- [KEDA](../autoscaling/01-keda.md): conceptos de escalado basado en eventos
- [Karpenter](../autoscaling/02-karpenter.md): conceptos de aprovisionamiento de nodos

### Esta guía de operaciones
- Código HCL de Terraform para infraestructura de producción
- Manifiestos YAML para recursos de Kubernetes
- Consultas PromQL/LogQL para observabilidad
- Scripts de Bash para automatización operativa
- Procedimientos paso a paso con validación

---

## Referencia rápida

### Operaciones habituales

| Tarea | Documento | Sección |
|------|----------|---------|
| Crear un clúster de EKS | [01-configuración-de-infraestructura](./01-infrastructure-setup.md) | Terraform en tres capas |
| Añadir una aplicación a ArgoCD | [04-ArgoCD-multiclúster](./04-gitops-multi-cluster.md) | ApplicationSet |
| Configurar HPA con métricas personalizadas | [06-estrategias-de-escalado](./06-scaling-strategies.md) | Métricas personalizadas |
| Configurar alertas para un servicio nuevo | [07-alertas-de-observabilidad](./07-observability-alerts.md) | Reglas de alertas |
| Actualizar la versión de EKS | [11-actualizaciones-de-EKS](./11-upgrade-operations.md) | Actualización de Auto Mode |

### Procedimientos de emergencia

| Situación | Documento | Sección |
|----------|----------|---------|
| Revertir una implementación | [04-ArgoCD-multiclúster](./04-gitops-multi-cluster.md) | Reversión |
| Revertir una actualización de EKS | [11-actualizaciones-de-EKS](./11-upgrade-operations.md) | Criterios para la reversión nativa o vuelta atrás de azul/verde |
| Ajustar la capacidad después de comprobar la demanda y la disponibilidad | [06-estrategias-de-escalado](./06-scaling-strategies.md) | Capacidad y política de escalado |
| Diagnosticar pods con fallos | [16-guía-de-resolución-de-problemas](./16-troubleshooting-playbook.md) | Diagnóstico según el síntoma |

---

## Contribuciones

Al añadir procedimientos operativos:

1. Incluye ejemplos prácticos de código (Terraform, YAML y Bash)
2. Proporciona pasos de validación para cada procedimiento
3. Documenta los procedimientos de reversión cuando corresponda
4. Añade consultas pertinentes de PromQL/LogQL para la supervisión
5. Incluye referencias cruzadas a la documentación conceptual relacionada
