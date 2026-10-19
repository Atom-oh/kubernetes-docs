# Noticias
> **Última actualización**: 19 de octubre de 2026

Esta página registra los cambios en la documentación motivados por noticias de Kubernetes, Amazon EKS y CNCF. GitHub Actions prepara actualizaciones cada lunes a las 09:00 KST y abre un PR cuando se supera el control de calidad. Los cambios llegan al sitio después de la revisión, la fusión y el despliegue.

Las etiquetas de semana identifican las semanas de las entradas del registro y pueden diferir de las fechas de publicación de las fuentes. Estos son registros históricos; consulta las guías enlazadas y las fuentes oficiales para conocer el soporte, los parches de seguridad y los requisitos operativos vigentes. «Sin documentación coincidente» describe el resultado de la búsqueda automatizada en ese momento.

<!-- news-dashboard -->

<details class="news-log">
<summary>Ampliar el registro completo de actualizaciones</summary>

## Registro de actualizaciones

- 2026-W43: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — se publicaron las versiones de parche de Istio 1.31.2/1.30.6/1.29.9 (incluido el parche de seguridad ISTIO-SECURITY-2026-007, ya reflejado en el documento tras una revisión anterior) ([fuente](https://istio.io/news/releases/1.31.x/announcing-1.31.2/))
- 2026-W43: [networking/cilium/README.md](../networking/cilium/README.md) — se aplicaron las versiones de parche de Cilium 1.20.3/1.19.9/1.18.15 (correcciones de errores, incluidas la recolección de basura de conntrack y la gestión de CNP con `nodeSelector`) ([fuente](https://github.com/cilium/cilium/releases/tag/v1.20.3))
- 2026-W43: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicaron las versiones de parche de corrección de errores de Argo CD v3.5.5/v3.4.11/v3.3.16 ([fuente](https://github.com/argoproj/argo-cd/releases/tag/v3.5.5))
- 2026-W43: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicó la versión candidata de Argo CD v3.6.0-rc3 ([fuente](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc3))
- 2026-W43: [security/14-waf-edge-api-security.md](../security/14-waf-edge-api-security.md) — se aplicó el anuncio de compatibilidad con doble pila (IPv6) para los orígenes VPC de CloudFront ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/10/cloudfront-vpc-origin-dualstack/))
- 2026-W43: [blockchain/01-fundamentals.md](../blockchain/01-fundamentals.md) — se aplicó el lanzamiento de Blockchain Snapshots en AWS (instantáneas gratuitas y presincronizadas para iniciar nodos de Ethereum/Solana) ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/10/blockchain-snapshots-node-bootstrapping/))
- 2026-W43: [security/01-kyverno-policy-management.md](../security/01-kyverno-policy-management.md) — se aplicó la presentación de Nirmata Runtime para Kyverno en el blog de CNCF (aplicación de políticas de runtime a nivel del kernel mediante eBPF/LSM) ([fuente](https://www.cncf.io/blog/2026/10/15/extending-kubernetes-policy-enforcement-to-runtime-security-for-ai-workloads/))
- 2026-W43: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — se aplicó la propuesta del blog de CNCF de tratar Software Carbon Intensity (SCI) como convenciones semánticas de OpenTelemetry ([fuente](https://www.cncf.io/blog/2026/10/15/carbon-as-a-first-class-signal-bringing-software-carbon-intensity-to-opentelemetry/))
- 2026-W43: sin documentación coincidente — Seguimiento del estado de admisión de Jobs gestionados por Kueue con Headlamp, blog de Kubernetes ([fuente](https://kubernetes.io/blog/2026/10/14/tracing-kueue-admission-with-headlamp/))
- 2026-W42: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — se aplicó el lanzamiento de Karpenter v1.15.0 (reparación de nodos como interrupción voluntaria con soporte para reinicios, CEL en KubeletConfiguration, mayor compatibilidad con DRA y más)
- 2026-W42: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicaron las versiones de parche de seguridad de Argo CD v3.5.4/v3.4.10/v3.3.15 (cuatro problemas CRITICAL, incluida la ejecución de comandos en repo-server, CVE-2026-77459)
- 2026-W42: [kernel/01-container-primitives.md](../kernel/01-container-primitives.md) — se aplicó el estado de la obsolescencia de cgroup v1 indicado en el blog de Kubernetes (`failCgroupV1` tiene el valor predeterminado `true` desde v1.35)
- 2026-W42: sin documentación coincidente — Escalado de cargas de trabajo de Kubernetes con el intercambio de nodos respaldado por SSD NVMe (GA en v1.34), blog de Kubernetes ([fuente](https://kubernetes.io/blog/2026/10/05/scaling-kubernetes-workloads-with-node-swap/))
- 2026-W42: sin documentación coincidente — Meshery pasa a ser un proyecto incubador de CNCF ([fuente](https://www.cncf.io/blog/2026/10/07/meshery-becomes-a-cncf-incubating-project/))
- 2026-W42: sin documentación coincidente — AWS Batch ahora admite la autenticación mediante entradas de acceso de Amazon EKS ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/10/aws-batch-access-entries/))
- 2026-W41: [eks/08-eks-upgrades.md](../eks/08-eks-upgrades.md) — se aplicó la compatibilidad con Kubernetes 1.37 en Amazon EKS y EKS Distro (Metrics API en GA, taints de dispositivos DRA en GA, escalado de HPA a cero en beta)
- 2026-W41: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicaron las noticias sobre el inicio de la planificación de Argo CD 4.0 y ArgoCon North America 2026
- 2026-W41: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — se aplicó la reconstrucción de la detección de incidentes de Atlassian con OTel, Kafka y Flink (blog de CNCF)
- 2026-W41: sin documentación coincidente — Amazon ECS añade compatibilidad con Amazon VPC Lattice para despliegues blue/green, lineales y canary ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/10/amazon-ecs-vpc-lattice-blue-green-deployments))
- 2026-W41: sin documentación coincidente — Amazon Managed Grafana ahora permite crear espacios de trabajo de Grafana 13.2 ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-managed-grafana-now-supports-creating-grafana-13-2-workspaces))
- 2026-W41: sin documentación coincidente — Lanzamiento de Grafana Tempo 3.1 (nuevas funciones de Kafka, actualizaciones de métricas de TraceQL, enmascaramiento de trazas y más) ([fuente](https://grafana.com/blog/tempo-3-1-release-all-the-latest-features))
- 2026-W41: sin documentación coincidente — Salvaguardas, no barreras: replanteamiento de las políticas en los equipos de plataforma, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/10/01/guardrails-not-gates-rethinking-policy-in-platform-teams/))
- 2026-W40: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicaron las versiones de parche de Kubernetes v1.37.1/v1.36.5/v1.35.9/v1.34.12 y la publicación del blog sobre la condición `Unused` de PVC en v1.37 (Beta)
- 2026-W40: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — se aplicaron las versiones de parche de Istio 1.31.1/1.30.5/1.29.8 (incluida la corrección de seguridad de BackendTLSPolicy que falla en modo abierto, GHSA-qm8v-g4f9-qhjx)
- 2026-W40: [eks/04-eks-storage-part1.md](../eks/04-eks-storage-part1.md) — se aplicó la vulnerabilidad de inyección de opciones de montaje del controlador CSI de EFS, CVE-2026-6437 (corregida en v3.0.1)
- 2026-W40: [ai-ml/08-llm-gateway.md](../ai-ml/08-llm-gateway.md) — se aplicó el lanzamiento de Amazon SageMaker HyperPod Inference Gateway (complemento gestionado de EKS, enrutamiento con conocimiento de GPU)
- 2026-W40: sin documentación coincidente — Amazon EMR en EKS ahora admite clústeres de Amazon EKS con IPv6 ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-emr-eks-ipv6-support))
- 2026-W40: sin documentación coincidente — Ejecución de cargas de trabajo interactivas en Amazon EMR en EKS con Spark Connect ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/09/emr-eks-spark-connect-interactive/))
- 2026-W40: sin documentación coincidente — Disponibilidad general de Amazon CloudWatch Omni (experiencia de observabilidad con IA como prioridad e interoperabilidad con OpenTelemetry) ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-cloudwatch-omni-ai/))
- 2026-W39: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicaron tres análisis detallados de funciones de Kubernetes v1.37 (Memory QoS en Beta, administradores de recursos a nivel de Pod en Beta, permisos de emptyDir y opciones de bind mount)
- 2026-W39: [networking/cilium/README.md](../networking/cilium/README.md) — se aplicaron las versiones de parche de Cilium 1.20.2/1.19.8/1.18.14 y el resumen de funciones de la versión 1.20 del blog de CNCF
- 2026-W39: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicaron las versiones de parche de Argo CD v3.5.3/v3.4.9 y v3.6.0-rc1
- 2026-W39: sin documentación coincidente — La API Kubernetes CSI Changed Block Tracking (CBT) pasa a Beta, con diferencias respecto a Alpha, blog de Kubernetes ([fuente](https://kubernetes.io/blog/2026/09/14/csi-changed-block-tracking-beta/))
- 2026-W39: sin documentación coincidente — AWS Resilience Hub añade tres nuevas capacidades (incluido el descubrimiento de recursos de servicio basado en etiquetas de EKS dentro de un espacio de nombres) ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/09/resilience-hub-eks-dependency-policy/))
- 2026-W38: [core/08-scheduling-preemption-eviction.md](../core/08-scheduling-preemption-eviction.md) — se aplicaron la prioridad del planificador de Kubernetes v1.37 para el redimensionamiento in situ de Pod (Alpha) y los avances de Workload-Aware Scheduling (Workload/PodGroup en Beta, API CompositePodGroup)
- 2026-W38: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicaron las condiciones del ciclo de vida de Node de Kubernetes v1.37 (cinco condiciones conocidas para el drenaje, el mantenimiento y el apagado gradual)
- 2026-W38: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — se aplicaron los histogramas nativos de Prometheus para las métricas de componentes de Kubernetes v1.37 (Beta, habilitados de forma predeterminada)
- 2026-W38: [networking/cilium/README.md](../networking/cilium/README.md) — se aplicó la versión preliminar Cilium 1.21.0-pre.2 (persistencia de sesiones de Gateway API, listas de prefijos gestionadas por AWS, enmascaramiento BPF de forma predeterminada)
- 2026-W38: sin documentación coincidente — Karmada pasa a ser un proyecto graduado de CNCF ([fuente](https://www.cncf.io/announcements/2026/09/07/cloud-native-computing-foundation-announces-karmada-graduation/))
- 2026-W38: sin documentación coincidente — Recuperación ante desastres de Kubernetes: recomendaciones basadas en tres escenarios de fallo reproducibles, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/09/10/kubernetes-disaster-recovery-guidance-from-three-reproducible-failure-scenarios/))
- 2026-W38: sin documentación coincidente — Complemento Private CA EKS de AWS y Connector for AD ya disponibles en AWS GovCloud (EE. UU.) ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/09/private-ca-eks-addon-ad-govcloud/))
- 2026-W36: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicó el lanzamiento «Garhwal» de Kubernetes v1.37 (certificados de Pod/ClusterTrustBundles en Stable, Metrics API en GA, obsolescencia de kube-dns y del modo IPVS, y más)
- 2026-W36: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — se aplicaron las versiones de parche de seguridad de Istio 1.30.4/1.29.7 (ISTIO-SECURITY-2026-006, 13 CVE de Envoy)
- 2026-W36: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicaron las versiones de parche de ArgoCD v3.5.2/v3.4.8
- 2026-W36: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — se aplicó Linkerd edge-26.8.4 (negociación de la versión de la API TLSRoute y más)
- 2026-W36: sin documentación coincidente — Amazon EKS ahora admite hasta 10 proveedores externos de identidad OIDC por clúster ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-multiple-oidc-providers))
- 2026-W36: sin documentación coincidente — Escalar antes del pico: escalado automático predictivo para cargas de trabajo de GPU en Kubernetes, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/08/28/scale-before-the-spike-predictive-autoscaling-for-gpu-workloads-on-kubernetes/))
- 2026-W36: sin documentación coincidente — Creación de una fábrica de IA en Kubernetes, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/08/27/building-an-ai-factory-on-kubernetes/))
- 2026-W35: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicó la compatibilidad con la configuración personalizada (mediante el ConfigMap `argocd-cm`) para la capacidad Argo CD gestionada de Amazon EKS
- 2026-W35: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicaron las versiones de parche de Kubernetes v1.36.4/v1.35.8/v1.34.11 y v1.37.0-rc.1
- 2026-W35: [networking/cilium/README.md](../networking/cilium/README.md) — se aplicaron las versiones de parche de Cilium 1.20.1/1.19.7/1.18.13
- 2026-W35: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — se aplicó la versión de parche de Karpenter v1.14.1
- 2026-W35: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — se aplicó el lanzamiento de Istio 1.31.0-rc.0 (la versión 1.31 entra en RC)
- 2026-W35: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — se aplicó la guía del blog de CNCF para convertir consultas SQL lentas en métricas derivadas de spans de OTel
- 2026-W35: sin documentación coincidente — Amazon EKS ahora admite la rotación de la autoridad certificadora (CA) con gestión automatizada del ciclo de vida ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-certificate-authority-ca-rotation-automated-lifecycle-management))
- 2026-W35: sin documentación coincidente — Kubeflow se gradúa dentro de CNCF ([fuente](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/))
- 2026-W34: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicó el lanzamiento GA de ArgoCD v3.5.0 y las versiones de parche v3.5.1/v3.4.7/v3.3.14
- 2026-W34: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — se aplicó el lanzamiento beta.1 de Istio 1.31.0 (la versión 1.31 entra en beta)
- 2026-W34: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — se aplicó Linkerd edge-26.8.2 (compatibilidad con Gateway API 1.5.1, versión máxima de k8s probada: 1.36)
- 2026-W34: sin documentación coincidente — Amazon EKS ahora admite parámetros avanzados de configuración del plano de control de Kubernetes (ajuste del scheduler/controller manager/API server) ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-control-plane-configuration-parameters))
- 2026-W34: sin documentación coincidente — Cloud Native Buildpacks pasa a ser un proyecto graduado de CNCF ([fuente](https://www.cncf.io/announcements/2026/08/11/cncf-announces-graduation-of-cloud-native-buildpacks-advancing-the-standard-for-container-builds/))
- 2026-W34: sin documentación coincidente — Se publica el programa de KubeCon + CloudNativeCon North America 2026 y se añade una nueva sesión sobre inferencia de IA y agentes ([fuente](https://www.cncf.io/announcements/2026/08/10/cncf-reveals-kubecon-cloudnativecon-north-america-2026-schedule-adds-new-ai-inference-agentic-track/))
- 2026-W34: sin documentación coincidente — Cómo dar formato legible a YAML de Kubernetes como KYAML, blog de Kubernetes ([fuente](https://kubernetes.io/blog/2026/08/11/how-to-pretty-print-kubernetes-yaml-as-kyaml/))
- 2026-W33: [networking/04-gateway-api.md](../networking/04-gateway-api.md) — se aplicó Gateway API v1.6 (TCPRoute/UDPRoute pasan a Standard v1, cambios en la publicación de API obsoletas específicos de cada canal)
- 2026-W33: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicó ArgoCD v3.5.0 GA (migración a Helm 4, verificación de integridad de origen en Alpha, mejoras de ApplicationSet)
- 2026-W33: [networking/cilium/README.md](../networking/cilium/README.md) — se aplicó Cilium 1.20.0 GA (Gateway API v1.6.1, KCNP, migración de IPAM con varios pools) y 1.21.0-pre.0
- 2026-W33: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicó el adelanto de Kubernetes v1.37, la entrada en vigor de Docs Freeze y la etiqueta v1.38.0-alpha.0
- 2026-W33: sin documentación coincidente — Amazon ECR ahora admite capas de imagen de hasta 200 GB para Docker push ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-ecr-image-layers/))
- 2026-W33: sin documentación coincidente — K8gb pasa a ser un proyecto incubador de CNCF ([fuente](https://www.cncf.io/announcements/2026/08/05/k8gb-becomes-a-cncf-incubating-project/))
- 2026-W33: sin documentación coincidente — OpenCost 1.121.0 añade el seguimiento del coste de inferencia de Kubernetes ([fuente](https://www.cncf.io/blog/2026/08/05/opencost-1-121-0-first-of-a-kind-kubernetes-inference-cost-tracking/))
- 2026-W33: sin documentación coincidente — ¿DRA de Kubernetes reemplaza a HAMi?, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/08/07/does-kubernetes-dra-replace-hami/))
- 2026-W31: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicaron las versiones de parche de Kubernetes v1.36.3/v1.35.7/v1.34.10 y la entrada en vigor de Code Freeze para v1.37
- 2026-W31: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — se aplicó la compatibilidad con EFA y grupos de ubicación de EC2 para los pools de nodos de EKS Auto Mode
- 2026-W31: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — se aplicó la compatibilidad con EFA y grupos de ubicación de EC2 para los pools de nodos de Karpenter
- 2026-W31: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — se aplicaron los aumentos de límites de AMP (1.500 millones de series activas, 200.000 reglas por espacio de trabajo)
- 2026-W31: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — se aplicó la graduación de OpenTelemetry en CNCF
- 2026-W31: [networking/calico/README.md](../networking/calico/README.md) — se aplicó el lanzamiento de Calico for VMs on Kubernetes de Tigera (red unificada de máquinas virtuales y contenedores basada en eBPF)
- 2026-W31: [networking/cilium/README.md](../networking/cilium/README.md) — se aplicó la versión candidata Cilium 1.20.0-rc.1
- 2026-W31: sin documentación coincidente — Confidential Containers pasa a ser un proyecto incubador de CNCF ([fuente](https://www.cncf.io/blog/2026/07/22/confidential-containers-becomes-a-cncf-incubating-project/))
- 2026-W31: sin documentación coincidente — Dos CVE de recorrido de rutas en controladores CSI de Kubernetes (CVE-2026-3864 NFS / CVE-2026-3865 SMB; corregidas en csi-driver-nfs v4.13.1 y csi-driver-smb v1.20.1) ([fuente](https://www.sentinelone.com/blog/mount-here-read-there-twin-path-traversal-cves-in-kubernetes-storage/))
- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — se aplicaron las versiones de parche de Cilium 1.19.6/1.18.12/1.17.18 y CVE-2026-56743 (problema de ipBlock en NetworkPolicy)
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — se aplicaron las versiones de parche de Istio 1.30.3/1.29.6
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — se aplicó Linkerd edge-26.7.1 (se prohíben las solicitudes a puertos de servicio no definidos; cambio incompatible)
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — se aplicó la compatibilidad con ARC zonal shift/autoshift para EKS Auto Mode
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — se aplicó la compatibilidad con ARC zonal shift para EKS Auto Mode
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — se aplicaron las versiones de parche de Karpenter para ramas anteriores (v1.3.8–v1.11.3)
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicaron Kubernetes v1.37.0-beta.0 y el calendario de lanzamiento de v1.37
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicaron ArgoCon Japan 2026 y la próxima sesión sobre la hoja de ruta de Argo CD 3.5
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — se aplicó la guía del blog de Kubernetes sobre exportadores de métricas personalizadas
- 2026-W30: sin documentación coincidente — HAMi pasa a ser un proyecto incubador de CNCF ([fuente](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/))
- 2026-W30: sin documentación coincidente — Ejecución de un LLM autohospedado en Kubernetes con vLLM, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/))
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — se aplicó la compatibilidad de ACM con el protocolo ACME (los certificados públicos de ACM ya se pueden usar desde cert-manager)
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — se aplicó el patrón de observabilidad de límites de red con NGINX + OpenTelemetry para agentes de IA
- 2026-W29: sin documentación coincidente — Evolución de la ingeniería de plataformas para cargas de trabajo nativas de IA, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/))
- 2026-07-11: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicó el lanzamiento de etcd v3.7.0 (RangeStream y más)
- 2026-07-11: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — se aplicó la reducción de hasta un 60 % de la tarifa de gestión de GPU de EKS Auto Mode
- 2026-07-11: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — se aplicó el lanzamiento de Karpenter v1.14.0 (API CapacityBuffers y más)
- 2026-07-11: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — se aplicaron los eventos de servicio de CloudWatch Application Signals
- 2026-07-11: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicó la versión de parche de ArgoCD v3.4.5
- 2026-07-11: sin documentación coincidente — Cómo afrontar la retirada de ingress-nginx (marzo de 2026), blog de CNCF ([fuente](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/))
- 2026-07-11: sin documentación coincidente — Publicación del documento técnico de CNCF sobre almacenamiento de datos para IA nativa de la nube ([fuente](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/))
- 2026-07-11: sin documentación coincidente — Amazon EMR en EKS ahora admite un agente de resolución de problemas de Apache Spark ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/))
- 2026-07-11: sin documentación coincidente — Revisión de precios de nodos híbridos/multinube de AWS Systems Manager (se elimina el nivel Advanced Instances) ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/))

</details>
