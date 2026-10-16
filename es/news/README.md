# Noticias
> **Última actualización**: October 12, 2026

Esta página registra los cambios de documentación motivados por las noticias de Kubernetes, Amazon EKS y CNCF. GitHub Actions prepara actualizaciones cada lunes a las 09:00 KST y abre una PR después de que supere su control de calidad. Los cambios llegan al sitio tras la revisión, la fusión y el despliegue.

Las etiquetas de semana identifican las semanas de las entradas del registro y pueden diferir de las fechas de publicación de las fuentes. Estos son registros históricos; consulte las guías enlazadas y las fuentes oficiales para obtener información actual sobre soporte, parches de seguridad y requisitos operativos. «Sin documento coincidente» describe la coincidencia automatizada en ese momento.

<!-- news-dashboard -->

<details class="news-log">
<summary>Expandir el registro completo de actualizaciones</summary>

## Registro de actualizaciones

- 2026-W42: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — se aplicó el lanzamiento de Karpenter v1.15.0 (reparación de nodos como una interrupción voluntaria con soporte de reinicio, CEL en KubeletConfiguration, soporte DRA más amplio y más)
- 2026-W42: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicaron los lanzamientos de parches de seguridad de Argo CD v3.5.4/v3.4.10/v3.3.15 (cuatro problemas CRITICAL, incluida la ejecución de comandos de repo-server, CVE-2026-77459)
- 2026-W42: [kernel/01-container-primitives.md](../kernel/01-container-primitives.md) — se aplicó el estado de desuso de cgroup v1 del blog de Kubernetes (`failCgroupV1` tiene como valor predeterminado `true` desde v1.35)
- 2026-W42: sin documento coincidente — Escalado de workloads de Kubernetes con node swap respaldado por NVMe SSD (GA en v1.34), blog de Kubernetes ([fuente](https://kubernetes.io/blog/2026/10/05/scaling-kubernetes-workloads-with-node-swap/))
- 2026-W42: sin documento coincidente — Meshery se convierte en un proyecto incubado de CNCF ([fuente](https://www.cncf.io/blog/2026/10/07/meshery-becomes-a-cncf-incubating-project/))
- 2026-W42: sin documento coincidente — AWS Batch ahora admite autenticación de entradas de acceso de Amazon EKS ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/10/aws-batch-access-entries/))
- 2026-W41: [eks/08-eks-upgrades.md](../eks/08-eks-upgrades.md) — se aplicó el soporte de Kubernetes 1.37 en Amazon EKS y EKS Distro (Metrics API GA, DRA device taints GA, HPA scale-to-zero beta)
- 2026-W41: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicó el inicio de la visión para Argo CD 4.0 y las noticias de ArgoCon North America 2026
- 2026-W41: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — se aplicó la reconstrucción de Atlassian para la detección de incidentes basada en OTel, Kafka y Flink (blog de CNCF)
- 2026-W41: sin documento coincidente — Amazon ECS añade soporte de Amazon VPC Lattice para deployments blue/green, lineales y canary ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/10/amazon-ecs-vpc-lattice-blue-green-deployments))
- 2026-W41: sin documento coincidente — Amazon Managed Grafana ahora permite crear workspaces de Grafana 13.2 ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-managed-grafana-now-supports-creating-grafana-13-2-workspaces))
- 2026-W41: sin documento coincidente — Lanzamiento de Grafana Tempo 3.1 (nuevas características de Kafka, actualizaciones de métricas TraceQL, enmascaramiento de trazas y más) ([fuente](https://grafana.com/blog/tempo-3-1-release-all-the-latest-features))
- 2026-W41: sin documento coincidente — Barreras de protección, no puertas: replanteamiento de las políticas en los equipos de plataforma, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/10/01/guardrails-not-gates-rethinking-policy-in-platform-teams/))
- 2026-W40: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicaron los lanzamientos de parches de Kubernetes v1.37.1/v1.36.5/v1.35.9/v1.34.12 y la publicación del blog sobre la condición PVC `Unused` de v1.37 (Beta)
- 2026-W40: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — se aplicaron los lanzamientos de parches de Istio 1.31.1/1.30.5/1.29.8 (incluida la corrección de seguridad fail-open de BackendTLSPolicy GHSA-qm8v-g4f9-qhjx)
- 2026-W40: [eks/04-eks-storage-part1.md](../eks/04-eks-storage-part1.md) — se aplicó la vulnerabilidad de inyección de opciones de montaje del driver EFS CSI CVE-2026-6437 (corregida en v3.0.1)
- 2026-W40: [ai-ml/08-llm-gateway.md](../ai-ml/08-llm-gateway.md) — se aplicó el lanzamiento de Amazon SageMaker HyperPod Inference Gateway (add-on administrado de EKS, enrutamiento consciente de GPU)
- 2026-W40: sin documento coincidente — Amazon EMR en EKS ahora admite clusters de Amazon EKS con IPv6 ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-emr-eks-ipv6-support))
- 2026-W40: sin documento coincidente — Ejecute workloads interactivos en Amazon EMR en EKS con Spark Connect ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/09/emr-eks-spark-connect-interactive/))
- 2026-W40: sin documento coincidente — Disponibilidad general de Amazon CloudWatch Omni (experiencia de observabilidad AI-first, interoperabilidad con OpenTelemetry) ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-cloudwatch-omni-ai/))
- 2026-W39: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicaron tres análisis detallados de características de Kubernetes v1.37 (Memory QoS Beta, Pod-Level Resource Managers Beta, permisos de emptyDir y opciones de bind mount)
- 2026-W39: [networking/cilium/README.md](../networking/cilium/README.md) — se aplicaron los lanzamientos de parches de Cilium 1.20.2/1.19.8/1.18.14 y el resumen de características de 1.20 del blog de CNCF
- 2026-W39: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicaron los lanzamientos de parches de Argo CD v3.5.3/v3.4.9 y v3.6.0-rc1
- 2026-W39: sin documento coincidente — La API Kubernetes CSI Changed Block Tracking (CBT) pasa a Beta, con diferencias respecto a Alpha, blog de Kubernetes ([fuente](https://kubernetes.io/blog/2026/09/14/csi-changed-block-tracking-beta/))
- 2026-W39: sin documento coincidente — AWS Resilience Hub añade tres nuevas capacidades (incluido el descubrimiento de recursos de Service basado en etiquetas de EKS dentro de un namespace) ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/09/resilience-hub-eks-dependency-policy/))
- 2026-W38: [core/08-scheduling-preemption-eviction.md](../core/08-scheduling-preemption-eviction.md) — se aplicaron la preemption del scheduler de Kubernetes v1.37 para el cambio de tamaño in-place de Pod (Alpha) y los avances de Workload-Aware Scheduling (Workload/PodGroup Beta, API CompositePodGroup)
- 2026-W38: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicaron las condiciones del ciclo de vida de Node de Kubernetes v1.37 (cinco condiciones conocidas para drain, mantenimiento y apagado ordenado)
- 2026-W38: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — se aplicaron los histogramas nativos de Prometheus para las métricas de componentes de Kubernetes v1.37 (Beta, habilitados de forma predeterminada)
- 2026-W38: [networking/cilium/README.md](../networking/cilium/README.md) — se aplicó la versión preliminar Cilium 1.21.0-pre.2 (persistencia de sesión de Gateway API, listas de prefijos administradas de AWS, BPF masquerading de forma predeterminada)
- 2026-W38: sin documento coincidente — Karmada se convierte en un proyecto graduado de CNCF ([fuente](https://www.cncf.io/announcements/2026/09/07/cloud-native-computing-foundation-announces-karmada-graduation/))
- 2026-W38: sin documento coincidente — Recuperación ante desastres de Kubernetes: guía a partir de tres escenarios de fallo reproducibles, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/09/10/kubernetes-disaster-recovery-guidance-from-three-reproducible-failure-scenarios/))
- 2026-W38: sin documento coincidente — El add-on AWS Private CA EKS y Connector for AD ya están disponibles en AWS GovCloud (US) ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/09/private-ca-eks-addon-ad-govcloud/))
- 2026-W36: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicó el lanzamiento Kubernetes v1.37 «Garhwal» (certificados de Pod/ClusterTrustBundles Stable, Metrics API GA, desusos de kube-dns y modo IPVS, y más)
- 2026-W36: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — se aplicaron los lanzamientos de parches de seguridad de Istio 1.30.4/1.29.7 (ISTIO-SECURITY-2026-006, 13 CVE de Envoy)
- 2026-W36: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicaron los lanzamientos de parches de ArgoCD v3.5.2/v3.4.8
- 2026-W36: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — se aplicó Linkerd edge-26.8.4 (negociación de versión de la API TLSRoute y más)
- 2026-W36: sin documento coincidente — Amazon EKS ahora admite hasta 10 proveedores de identidad OIDC externos por cluster ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-multiple-oidc-providers))
- 2026-W36: sin documento coincidente — Escale antes del pico: autoscaling predictivo para workloads de GPU en Kubernetes, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/08/28/scale-before-the-spike-predictive-autoscaling-for-gpu-workloads-on-kubernetes/))
- 2026-W36: sin documento coincidente — Construir una fábrica de AI en Kubernetes, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/08/27/building-an-ai-factory-on-kubernetes/))
- 2026-W35: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicó el soporte de configuración personalizada (mediante el ConfigMap `argocd-cm`) para la capacidad administrada de Argo CD de Amazon EKS
- 2026-W35: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicaron los lanzamientos de parches de Kubernetes v1.36.4/v1.35.8/v1.34.11 y v1.37.0-rc.1
- 2026-W35: [networking/cilium/README.md](../networking/cilium/README.md) — se aplicaron los lanzamientos de parches de Cilium 1.20.1/1.19.7/1.18.13
- 2026-W35: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — se aplicó el lanzamiento de parche de Karpenter v1.14.1
- 2026-W35: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — se aplicó el lanzamiento de Istio 1.31.0-rc.0 (1.31 entra en RC)
- 2026-W35: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — se aplicó la guía del blog de CNCF sobre destilar consultas SQL lentas en métricas derivadas de spans de OTel
- 2026-W35: sin documento coincidente — Amazon EKS ahora admite la rotación de certificate authority (CA) con gestión automatizada del ciclo de vida ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-certificate-authority-ca-rotation-automated-lifecycle-management))
- 2026-W35: sin documento coincidente — Kubeflow se gradúa dentro de CNCF ([fuente](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/))
- 2026-W34: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicaron el lanzamiento GA de ArgoCD v3.5.0 y los lanzamientos de parches v3.5.1/v3.4.7/v3.3.14
- 2026-W34: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — se aplicó el lanzamiento de Istio 1.31.0-beta.1 (1.31 entra en beta)
- 2026-W34: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — se aplicó Linkerd edge-26.8.2 (soporte de Gateway API 1.5.1, máximo de k8s 1.36 probado)
- 2026-W34: sin documento coincidente — Amazon EKS ahora admite parámetros avanzados de configuración del control plane de Kubernetes (ajuste de scheduler/controller manager/API server) ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-control-plane-configuration-parameters))
- 2026-W34: sin documento coincidente — Cloud Native Buildpacks se convierte en un proyecto graduado de CNCF ([fuente](https://www.cncf.io/announcements/2026/08/11/cncf-announces-graduation-of-cloud-native-buildpacks-advancing-the-standard-for-container-builds/))
- 2026-W34: sin documento coincidente — Se revela el calendario de KubeCon + CloudNativeCon North America 2026; se añade una nueva pista de AI Inference + Agentic ([fuente](https://www.cncf.io/announcements/2026/08/10/cncf-reveals-kubecon-cloudnativecon-north-america-2026-schedule-adds-new-ai-inference-agentic-track/))
- 2026-W34: sin documento coincidente — Cómo imprimir con formato su Kubernetes YAML como KYAML, blog de Kubernetes ([fuente](https://kubernetes.io/blog/2026/08/11/how-to-pretty-print-kubernetes-yaml-as-kyaml/))
- 2026-W33: [networking/04-gateway-api.md](../networking/04-gateway-api.md) — se aplicó Gateway API v1.6 (TCPRoute/UDPRoute se gradúan a Standard v1, cambios específicos del canal en el servicio de API obsoletas)
- 2026-W33: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicó ArgoCD v3.5.0 GA (migración a Helm 4, alpha de verificación de integridad de fuentes, mejoras de ApplicationSet)
- 2026-W33: [networking/cilium/README.md](../networking/cilium/README.md) — se aplicó Cilium 1.20.0 GA (Gateway API v1.6.1, KCNP, migración IPAM multi-pool) y 1.21.0-pre.0
- 2026-W33: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicaron el adelanto de Kubernetes v1.37, la entrada en vigor de Docs Freeze y la etiqueta v1.38.0-alpha.0
- 2026-W33: sin documento coincidente — Amazon ECR ahora admite capas de imagen de hasta 200 GB para Docker push ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-ecr-image-layers/))
- 2026-W33: sin documento coincidente — K8gb se convierte en un proyecto incubado de CNCF ([fuente](https://www.cncf.io/announcements/2026/08/05/k8gb-becomes-a-cncf-incubating-project/))
- 2026-W33: sin documento coincidente — OpenCost 1.121.0 añade seguimiento de costes de inferencia de Kubernetes ([fuente](https://www.cncf.io/blog/2026/08/05/opencost-1-121-0-first-of-a-kind-kubernetes-inference-cost-tracking/))
- 2026-W33: sin documento coincidente — ¿Kubernetes DRA reemplaza a HAMi?, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/08/07/does-kubernetes-dra-replace-hami/))
- 2026-W31: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicaron los lanzamientos de parches de Kubernetes v1.36.3/v1.35.7/v1.34.10 y la entrada en vigor de Code Freeze de v1.37
- 2026-W31: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — se aplicó el soporte de EFA y EC2 placement group para los node pools de EKS Auto Mode
- 2026-W31: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — se aplicó el soporte de EFA y EC2 placement group para los node pools de Karpenter
- 2026-W31: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — se aplicaron los aumentos de límites de AMP (1.5B series activas, 200K reglas por workspace)
- 2026-W31: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — se aplicó la graduación de OpenTelemetry en CNCF
- 2026-W31: [networking/calico/README.md](../networking/calico/README.md) — se aplicó el lanzamiento de Calico for VMs on Kubernetes de Tigera (redes unificadas VM+container basadas en eBPF)
- 2026-W31: [networking/cilium/README.md](../networking/cilium/README.md) — se aplicó la release candidate de Cilium 1.20.0-rc.1
- 2026-W31: sin documento coincidente — Confidential Containers se convierte en un proyecto incubado de CNCF ([fuente](https://www.cncf.io/blog/2026/07/22/confidential-containers-becomes-a-cncf-incubating-project/))
- 2026-W31: sin documento coincidente — CVE de path traversal gemelas en drivers Kubernetes CSI (CVE-2026-3864 NFS / CVE-2026-3865 SMB; corregidas en csi-driver-nfs v4.13.1, csi-driver-smb v1.20.1) ([fuente](https://www.sentinelone.com/blog/mount-here-read-there-twin-path-traversal-cves-in-kubernetes-storage/))
- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — se aplicaron los lanzamientos de parches de Cilium 1.19.6/1.18.12/1.17.18 y CVE-2026-56743 (problema de ipBlock NetworkPolicy)
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — se aplicaron los lanzamientos de parches de Istio 1.30.3/1.29.6
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — se aplicó Linkerd edge-26.7.1 (solicitudes a puertos de Service no definidos no permitidas, cambio incompatible)
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — se aplicó el soporte de ARC zonal shift/autoshift para EKS Auto Mode
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — se aplicó el soporte de ARC zonal shift para EKS Auto Mode
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — se aplicaron los lanzamientos de parches de Karpenter para líneas anteriores (v1.3.8–v1.11.3)
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicaron Kubernetes v1.37.0-beta.0 y el calendario de lanzamiento de v1.37
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicaron ArgoCon Japan 2026 y la próxima sesión de roadmap de Argo CD 3.5
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — se aplicó la guía del blog de Kubernetes sobre el exportador de métricas personalizadas
- 2026-W30: sin documento coincidente — HAMi se convierte en un proyecto incubado de CNCF ([fuente](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/))
- 2026-W30: sin documento coincidente — Ejecutar un LLM autoalojado en Kubernetes con vLLM, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/))
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — se aplicó el soporte de ACM para el protocolo ACME (los certificados públicos de ACM ahora se pueden utilizar desde cert-manager)
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — se aplicó el patrón de observabilidad de límites de red NGINX + OpenTelemetry para agentes de AI
- 2026-W29: sin documento coincidente — Evolución de la ingeniería de plataformas para workloads nativos de AI, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/))
- 2026-07-11: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicó el lanzamiento de etcd v3.7.0 (RangeStream y más)
- 2026-07-11: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — se aplicó la reducción de hasta un 60 % de la tarifa de gestión de GPU de EKS Auto Mode
- 2026-07-11: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — se aplicó el lanzamiento de Karpenter v1.14.0 (API CapacityBuffers y más)
- 2026-07-11: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — se aplicaron los Service Events de CloudWatch Application Signals
- 2026-07-11: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicó el lanzamiento de parche de ArgoCD v3.4.5
- 2026-07-11: sin documento coincidente — Cómo afrontar la retirada de ingress-nginx (marzo de 2026), blog de CNCF ([fuente](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/))
- 2026-07-11: sin documento coincidente — Se publicó el white paper de CNCF Data Storage in Cloud Native AI ([fuente](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/))
- 2026-07-11: sin documento coincidente — Amazon EMR en EKS ahora admite un agente de resolución de problemas de Apache Spark ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/))
- 2026-07-11: sin documento coincidente — Revisión de precios de nodos híbridos/multicloud de AWS Systems Manager (se elimina el nivel Advanced Instances) ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/))

</details>
