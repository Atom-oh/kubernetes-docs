# Noticias
> **Última actualización**: 12 de octubre de 2026

Esta página registra los cambios de documentación motivados por noticias de Kubernetes, Amazon EKS y CNCF. El flujo de GitHub Actions prepara actualizaciones cada lunes a las 09:00 KST y abre una solicitud de cambios (PR) tras superar el control de calidad. Los cambios se publican en el sitio después de revisarlos, fusionar la PR y desplegarlos.

Las etiquetas de semana identifican las semanas de las entradas del registro y pueden diferir de las fechas de publicación de las fuentes. Estos son registros históricos; consulte las guías enlazadas y las fuentes oficiales para obtener información actual sobre soporte, parches de seguridad y requisitos operativos. «Sin documento coincidente» describe la coincidencia automatizada en ese momento.

<!-- news-dashboard -->

<details class="news-log">
<summary>Expandir el registro completo de actualizaciones</summary>

## Registro de actualizaciones

- 2026-W42: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — se aplicó el lanzamiento de Karpenter v1.15.0 (reparación de nodos como disrupción voluntaria con compatibilidad con reinicios, CEL en KubeletConfiguration, compatibilidad ampliada con DRA y otras mejoras)
- 2026-W42: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicaron los lanzamientos de parches de seguridad de Argo CD v3.5.4/v3.4.10/v3.3.15 (cuatro problemas críticos, incluida la ejecución de comandos en repo-server, CVE-2026-77459)
- 2026-W42: [kernel/01-container-primitives.md](../kernel/01-container-primitives.md) — se aplicó el estado de desuso de cgroup v1 del blog de Kubernetes (`failCgroupV1` tiene como valor predeterminado `true` desde v1.35)
- 2026-W42: sin documento coincidente — Escalado de cargas de trabajo de Kubernetes mediante intercambio de memoria (swap) en nodos respaldados por SSD NVMe (GA en v1.34), blog de Kubernetes ([fuente](https://kubernetes.io/blog/2026/10/05/scaling-kubernetes-workloads-with-node-swap/))
- 2026-W42: sin documento coincidente — Meshery se convierte en un proyecto incubado de CNCF ([fuente](https://www.cncf.io/blog/2026/10/07/meshery-becomes-a-cncf-incubating-project/))
- 2026-W42: sin documento coincidente — AWS Batch ahora admite la autenticación mediante entradas de acceso de Amazon EKS ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/10/aws-batch-access-entries/))
- 2026-W41: [eks/08-eks-upgrades.md](../eks/08-eks-upgrades.md) — se aplicó la compatibilidad con Kubernetes 1.37 en Amazon EKS y EKS Distro (API de métricas GA, taints de dispositivos DRA GA, HPA con escalado hasta cero en Beta)
- 2026-W41: [gitops/argocd/README.md](../gitops/argocd/README.md) — se incorporaron las primeras conversaciones sobre la visión de Argo CD 4.0 y las noticias de ArgoCon North America 2026
- 2026-W41: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — se aplicó la reconstrucción del sistema de detección de incidentes de Atlassian con OTel, Kafka y Flink (blog de CNCF)
- 2026-W41: sin documento coincidente — Amazon ECS añade compatibilidad con Amazon VPC Lattice para implementaciones blue/green, lineales y canary ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/10/amazon-ecs-vpc-lattice-blue-green-deployments))
- 2026-W41: sin documento coincidente — Amazon Managed Grafana ahora permite crear espacios de trabajo de Grafana 13.2 ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-managed-grafana-now-supports-creating-grafana-13-2-workspaces))
- 2026-W41: sin documento coincidente — Lanzamiento de Grafana Tempo 3.1 (nuevas funciones de Kafka, mejoras en las métricas de TraceQL, redacción de datos en las trazas y otras novedades) ([fuente](https://grafana.com/blog/tempo-3-1-release-all-the-latest-features))
- 2026-W41: sin documento coincidente — Controles orientativos, no barreras: replanteamiento de las políticas en los equipos de plataforma, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/10/01/guardrails-not-gates-rethinking-policy-in-platform-teams/))
- 2026-W40: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicaron los lanzamientos de parches de Kubernetes v1.37.1/v1.36.5/v1.35.9/v1.34.12 y la entrada del blog sobre la condición `Unused` de los PVC de v1.37 (Beta)
- 2026-W40: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — se aplicaron los lanzamientos de parches de Istio 1.31.1/1.30.5/1.29.8 (incluida la corrección de seguridad que elimina el comportamiento fail-open de BackendTLSPolicy GHSA-qm8v-g4f9-qhjx)
- 2026-W40: [eks/04-eks-storage-part1.md](../eks/04-eks-storage-part1.md) — se aplicó la vulnerabilidad de inyección de opciones de montaje del controlador EFS CSI CVE-2026-6437 (corregida en v3.0.1)
- 2026-W40: [ai-ml/08-llm-gateway.md](../ai-ml/08-llm-gateway.md) — se aplicó el lanzamiento de Amazon SageMaker HyperPod Inference Gateway (complemento administrado de EKS, enrutamiento basado en GPU)
- 2026-W40: sin documento coincidente — Amazon EMR en EKS ahora admite clústeres de Amazon EKS con IPv6 ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-emr-eks-ipv6-support))
- 2026-W40: sin documento coincidente — Ejecute cargas de trabajo interactivas en Amazon EMR en EKS con Spark Connect ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/09/emr-eks-spark-connect-interactive/))
- 2026-W40: sin documento coincidente — Disponibilidad general de Amazon CloudWatch Omni (experiencia de observabilidad centrada en IA, interoperabilidad con OpenTelemetry) ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-cloudwatch-omni-ai/))
- 2026-W39: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicaron tres análisis detallados de características de Kubernetes v1.37 (Memory QoS Beta, Pod-Level Resource Managers Beta, permisos de emptyDir y opciones de montaje bind)
- 2026-W39: [networking/cilium/README.md](../networking/cilium/README.md) — se aplicaron los lanzamientos de parches de Cilium 1.20.2/1.19.8/1.18.14 y el resumen de características de 1.20 del blog de CNCF
- 2026-W39: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicaron los lanzamientos de parches de Argo CD v3.5.3/v3.4.9 y v3.6.0-rc1
- 2026-W39: sin documento coincidente — La API de seguimiento de bloques modificados de CSI (Changed Block Tracking, CBT) pasa a Beta, con diferencias frente a Alpha, blog de Kubernetes ([fuente](https://kubernetes.io/blog/2026/09/14/csi-changed-block-tracking-beta/))
- 2026-W39: sin documento coincidente — AWS Resilience Hub añade tres nuevas capacidades (incluido el descubrimiento de recursos de Service según etiquetas de EKS dentro de un espacio de nombres) ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/09/resilience-hub-eks-dependency-policy/))
- 2026-W38: [core/08-scheduling-preemption-eviction.md](../core/08-scheduling-preemption-eviction.md) — se incorporaron las novedades sobre el desalojo preventivo del planificador de Kubernetes v1.37 para redimensionar Pods in situ (Alpha) y los avances en la programación consciente de las cargas de trabajo (Workload-Aware Scheduling: Workload/PodGroup Beta, API CompositePodGroup)
- 2026-W38: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicaron las condiciones del ciclo de vida de los nodos de Kubernetes v1.37 (cinco condiciones conocidas para drenaje, mantenimiento y apagado ordenado)
- 2026-W38: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — se aplicaron los histogramas nativos de Prometheus para las métricas de componentes de Kubernetes v1.37 (Beta, habilitados de forma predeterminada)
- 2026-W38: [networking/cilium/README.md](../networking/cilium/README.md) — se aplicó la versión preliminar de Cilium 1.21.0-pre.2 (persistencia de sesión de Gateway API, listas de prefijos administradas de AWS, enmascaramiento BPF de forma predeterminada)
- 2026-W38: sin documento coincidente — Karmada se convierte en un proyecto graduado de CNCF ([fuente](https://www.cncf.io/announcements/2026/09/07/cloud-native-computing-foundation-announces-karmada-graduation/))
- 2026-W38: sin documento coincidente — Recuperación ante desastres de Kubernetes: guía a partir de tres escenarios de fallo reproducibles, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/09/10/kubernetes-disaster-recovery-guidance-from-three-reproducible-failure-scenarios/))
- 2026-W38: sin documento coincidente — El complemento AWS Private CA EKS y Connector for AD ya están disponibles en AWS GovCloud (US) ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/09/private-ca-eks-addon-ad-govcloud/))
- 2026-W36: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicó el lanzamiento de Kubernetes v1.37 «Garhwal» (certificados de Pod/ClusterTrustBundles en estado Stable, API de métricas GA, obsolescencia de kube-dns y del modo IPVS, entre otras novedades)
- 2026-W36: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — se aplicaron los lanzamientos de parches de seguridad de Istio 1.30.4/1.29.7 (ISTIO-SECURITY-2026-006, 13 CVE de Envoy)
- 2026-W36: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicaron los lanzamientos de parches de ArgoCD v3.5.2/v3.4.8
- 2026-W36: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — se aplicó Linkerd edge-26.8.4 (negociación de versión de la API TLSRoute y más)
- 2026-W36: sin documento coincidente — Amazon EKS ahora admite hasta 10 proveedores de identidad OIDC externos por clúster ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-multiple-oidc-providers))
- 2026-W36: sin documento coincidente — Escale antes del pico: escalado automático predictivo para cargas de trabajo con GPU en Kubernetes, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/08/28/scale-before-the-spike-predictive-autoscaling-for-gpu-workloads-on-kubernetes/))
- 2026-W36: sin documento coincidente — Construir una fábrica de IA en Kubernetes, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/08/27/building-an-ai-factory-on-kubernetes/))
- 2026-W35: [gitops/argocd/README.md](../gitops/argocd/README.md) — se incorporó la compatibilidad con la configuración personalizada (mediante el ConfigMap `argocd-cm`) para la oferta administrada de Argo CD de Amazon EKS
- 2026-W35: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicaron los lanzamientos de parches de Kubernetes v1.36.4/v1.35.8/v1.34.11 y v1.37.0-rc.1
- 2026-W35: [networking/cilium/README.md](../networking/cilium/README.md) — se aplicaron los lanzamientos de parches de Cilium 1.20.1/1.19.7/1.18.13
- 2026-W35: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — se aplicó la versión correctiva de Karpenter v1.14.1
- 2026-W35: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — se aplicó el lanzamiento de Istio 1.31.0-rc.0 (1.31 entra en fase RC)
- 2026-W35: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — se aplicó la guía del blog de CNCF sobre convertir consultas SQL lentas en métricas derivadas de spans de OTel
- 2026-W35: sin documento coincidente — Amazon EKS ahora admite la rotación de la autoridad certificadora (CA) con gestión automatizada del ciclo de vida ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-certificate-authority-ca-rotation-automated-lifecycle-management))
- 2026-W35: sin documento coincidente — Kubeflow se gradúa como proyecto de CNCF ([fuente](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/))
- 2026-W34: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicaron el lanzamiento GA de ArgoCD v3.5.0 y las versiones correctivas v3.5.1/v3.4.7/v3.3.14
- 2026-W34: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — se aplicó el lanzamiento de Istio 1.31.0-beta.1 (1.31 entra en fase beta)
- 2026-W34: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — se aplicó Linkerd edge-26.8.2 (compatibilidad con Gateway API 1.5.1, versión máxima probada de k8s: 1.36)
- 2026-W34: sin documento coincidente — Amazon EKS ahora admite parámetros avanzados de configuración del plano de control de Kubernetes (ajuste del planificador, el administrador de controladores y el servidor de API) ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-control-plane-configuration-parameters))
- 2026-W34: sin documento coincidente — Cloud Native Buildpacks se convierte en un proyecto graduado de CNCF ([fuente](https://www.cncf.io/announcements/2026/08/11/cncf-announces-graduation-of-cloud-native-buildpacks-advancing-the-standard-for-container-builds/))
- 2026-W34: sin documento coincidente — Se revela el calendario de KubeCon + CloudNativeCon North America 2026; se añade un nuevo eje temático de inferencia de IA y agentes ([fuente](https://www.cncf.io/announcements/2026/08/10/cncf-reveals-kubecon-cloudnativecon-north-america-2026-schedule-adds-new-ai-inference-agentic-track/))
- 2026-W34: sin documento coincidente — Cómo imprimir con formato el YAML de Kubernetes como KYAML, blog de Kubernetes ([fuente](https://kubernetes.io/blog/2026/08/11/how-to-pretty-print-kubernetes-yaml-as-kyaml/))
- 2026-W33: [networking/04-gateway-api.md](../networking/04-gateway-api.md) — se aplicó Gateway API v1.6 (TCPRoute/UDPRoute alcanzan el nivel Standard v1, cambios específicos de cada canal en la publicación de API obsoletas)
- 2026-W33: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicó ArgoCD v3.5.0 GA (migración a Helm 4, verificación de integridad de fuentes en fase Alpha, mejoras de ApplicationSet)
- 2026-W33: [networking/cilium/README.md](../networking/cilium/README.md) — se aplicó Cilium 1.20.0 GA (Gateway API v1.6.1, KCNP, migración de IPAM multipool) y 1.21.0-pre.0
- 2026-W33: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se incorporaron el adelanto de Kubernetes v1.37, el inicio de la congelación de documentación (Docs Freeze) y la etiqueta v1.38.0-alpha.0
- 2026-W33: sin documento coincidente — Amazon ECR ahora admite capas de imagen de hasta 200 GB para insertar imágenes mediante Docker push ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-ecr-image-layers/))
- 2026-W33: sin documento coincidente — K8gb se convierte en un proyecto incubado de CNCF ([fuente](https://www.cncf.io/announcements/2026/08/05/k8gb-becomes-a-cncf-incubating-project/))
- 2026-W33: sin documento coincidente — OpenCost 1.121.0 añade seguimiento de costes de inferencia de Kubernetes ([fuente](https://www.cncf.io/blog/2026/08/05/opencost-1-121-0-first-of-a-kind-kubernetes-inference-cost-tracking/))
- 2026-W33: sin documento coincidente — ¿DRA de Kubernetes reemplaza a HAMi?, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/08/07/does-kubernetes-dra-replace-hami/))
- 2026-W31: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicaron los lanzamientos de parches de Kubernetes v1.36.3/v1.35.7/v1.34.10 y el inicio del Code Freeze de v1.37
- 2026-W31: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — se aplicó la compatibilidad con EFA y grupos de ubicación de EC2 para los grupos de nodos de EKS Auto Mode
- 2026-W31: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — se aplicó la compatibilidad con EFA y grupos de ubicación de EC2 para los grupos de nodos de Karpenter
- 2026-W31: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — se aplicaron los aumentos de límites de AMP (1.500 millones de series activas, 200.000 reglas por espacio de trabajo)
- 2026-W31: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — se aplicó la graduación de OpenTelemetry en CNCF
- 2026-W31: [networking/calico/README.md](../networking/calico/README.md) — se aplicó el lanzamiento de Calico for VMs on Kubernetes de Tigera (redes unificadas para máquinas virtuales y contenedores basadas en eBPF)
- 2026-W31: [networking/cilium/README.md](../networking/cilium/README.md) — se aplicó la versión candidata de Cilium 1.20.0-rc.1
- 2026-W31: sin documento coincidente — Confidential Containers se convierte en un proyecto incubado de CNCF ([fuente](https://www.cncf.io/blog/2026/07/22/confidential-containers-becomes-a-cncf-incubating-project/))
- 2026-W31: sin documento coincidente — dos CVE de recorrido de rutas en controladores CSI de Kubernetes (CVE-2026-3864 NFS / CVE-2026-3865 SMB; corregidas en csi-driver-nfs v4.13.1, csi-driver-smb v1.20.1) ([fuente](https://www.sentinelone.com/blog/mount-here-read-there-twin-path-traversal-cves-in-kubernetes-storage/))
- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — se aplicaron los lanzamientos de parches de Cilium 1.19.6/1.18.12/1.17.18 y CVE-2026-56743 (problema de NetworkPolicy con ipBlock)
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — se aplicaron los lanzamientos de parches de Istio 1.30.3/1.29.6
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — se aplicó Linkerd edge-26.7.1 (se prohíben las solicitudes a puertos de Service no definidos; cambio incompatible)
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — se aplicó la compatibilidad con ARC zonal shift y AutoShift para EKS Auto Mode
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — se aplicó la compatibilidad con ARC zonal shift para EKS Auto Mode
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — se aplicaron los lanzamientos de parches de Karpenter para líneas anteriores (v1.3.8–v1.11.3)
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se incorporaron Kubernetes v1.37.0-beta.0 y el calendario de publicación de v1.37
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — se actualizaron las referencias a ArgoCon Japan 2026 y a la próxima sesión sobre la hoja de ruta de Argo CD 3.5
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — se aplicó la guía del blog de Kubernetes sobre el exportador de métricas personalizadas
- 2026-W30: sin documento coincidente — HAMi se convierte en un proyecto incubado de CNCF ([fuente](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/))
- 2026-W30: sin documento coincidente — Ejecutar un LLM autoalojado en Kubernetes con vLLM, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/))
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — se incorporó la compatibilidad de ACM con el protocolo ACME (los certificados públicos de ACM ahora se pueden utilizar desde cert-manager)
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — se aplicó el patrón de observabilidad de límites de red NGINX + OpenTelemetry para agentes de IA
- 2026-W29: sin documento coincidente — Evolución de la ingeniería de plataformas para cargas de trabajo nativas de IA, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/))
- 2026-07-11: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicó el lanzamiento de etcd v3.7.0 (RangeStream y otras novedades)
- 2026-07-11: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — se aplicó una reducción de hasta el 60 % en la tarifa de administración de GPU de EKS Auto Mode
- 2026-07-11: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — se aplicó el lanzamiento de Karpenter v1.14.0 (API CapacityBuffers y más)
- 2026-07-11: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — se aplicaron los eventos de servicio de CloudWatch Application Signals
- 2026-07-11: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicó la actualización correctiva de ArgoCD v3.4.5
- 2026-07-11: sin documento coincidente — Cómo afrontar la retirada de ingress-nginx (marzo de 2026), blog de CNCF ([fuente](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/))
- 2026-07-11: sin documento coincidente — Se publicó el informe técnico de CNCF «Data Storage in Cloud Native AI» ([fuente](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/))
- 2026-07-11: sin documento coincidente — Amazon EMR en EKS ahora admite un agente de resolución de problemas de Apache Spark ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/))
- 2026-07-11: sin documento coincidente — Revisión de los precios de nodos híbridos y multinube de AWS Systems Manager (se elimina el nivel Advanced Instances) ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/))

</details>
