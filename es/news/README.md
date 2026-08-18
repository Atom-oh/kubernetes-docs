# Noticias
> **Última actualización**: August 17, 2026

Las noticias del ecosistema de Kubernetes, Amazon EKS y CNCF no se recopilan aquí en documentos de resumen independientes. Cada semana, GitHub Actions aplica las noticias relevantes directamente al documento existente al que se relacionan, y este registro de actualizaciones registra únicamente qué documento cambió y por qué. Las noticias sin un documento coincidente se registran aquí solo como un enlace.

## Registro de actualizaciones

- 2026-W34: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicaron la versión GA de ArgoCD v3.5.0 y las versiones de parche v3.5.1/v3.4.7/v3.3.14
- 2026-W34: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — se aplicó la versión Istio 1.31.0-beta.1 (1.31 entra en beta)
- 2026-W34: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — se aplicó Linkerd edge-26.8.2 (compatibilidad con Gateway API 1.5.1, k8s 1.36 máximo probado)
- 2026-W34: sin documento coincidente — Amazon EKS ahora admite parámetros avanzados de configuración del plano de control de Kubernetes (ajuste del scheduler/controller manager/API server) ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-control-plane-configuration-parameters))
- 2026-W34: sin documento coincidente — Cloud Native Buildpacks se convierte en un proyecto graduado de CNCF ([fuente](https://www.cncf.io/announcements/2026/08/11/cncf-announces-graduation-of-cloud-native-buildpacks-advancing-the-standard-for-container-builds/))
- 2026-W34: sin documento coincidente — Se revela el calendario de KubeCon + CloudNativeCon North America 2026 y se añade una nueva categoría de AI Inference + Agentic ([fuente](https://www.cncf.io/announcements/2026/08/10/cncf-reveals-kubecon-cloudnativecon-north-america-2026-schedule-adds-new-ai-inference-agentic-track/))
- 2026-W34: sin documento coincidente — Cómo aplicar formato bonito a tu YAML de Kubernetes como KYAML, blog de Kubernetes ([fuente](https://kubernetes.io/blog/2026/08/11/how-to-pretty-print-kubernetes-yaml-as-kyaml/))
- 2026-W33: [networking/04-gateway-api.md](../networking/04-gateway-api.md) — se aplicó Gateway API v1.6 (TCPRoute/UDPRoute graduados a Standard v1, recursos experimentales movidos al grupo de API x-k8s.io)
- 2026-W33: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicó ArgoCD v3.5.0 GA (migración a Helm 4, alfa de verificación de integridad de fuente, mejoras en ApplicationSet)
- 2026-W33: [networking/cilium/README.md](../networking/cilium/README.md) — se aplicaron Cilium 1.20.0 GA (Gateway API v1.6.1, KCNP, migración de IPAM multi-pool) y 1.21.0-pre.0
- 2026-W33: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicaron el adelanto de Kubernetes v1.37, la entrada en vigor de Docs Freeze y la etiqueta v1.38.0-alpha.0
- 2026-W33: sin documento coincidente — Amazon ECR ahora admite capas de imagen de hasta 200 GB para Docker push ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-ecr-image-layers/))
- 2026-W33: sin documento coincidente — K8gb se convierte en un proyecto incubado de CNCF ([fuente](https://www.cncf.io/announcements/2026/08/05/k8gb-becomes-a-cncf-incubating-project/))
- 2026-W33: sin documento coincidente — OpenCost 1.121.0 añade seguimiento de costos de inferencia de Kubernetes ([fuente](https://www.cncf.io/blog/2026/08/05/opencost-1-121-0-first-of-a-kind-kubernetes-inference-cost-tracking/))
- 2026-W33: sin documento coincidente — ¿Kubernetes DRA reemplaza a HAMi?, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/08/07/does-kubernetes-dra-replace-hami/))
- 2026-W31: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicaron las versiones de parche Kubernetes v1.36.3/v1.35.7/v1.34.10 y la entrada en vigor de Code Freeze de v1.37
- 2026-W31: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — se aplicó la compatibilidad con grupos de colocación EFA y EC2 para los node pools de EKS Auto Mode
- 2026-W31: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — se aplicó la compatibilidad con grupos de colocación EFA y EC2 para los node pools de Karpenter
- 2026-W31: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — se aplicaron los aumentos de límites de AMP (1.5B de series activas, 200K de reglas por espacio de trabajo)
- 2026-W31: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — se aplicó la graduación de OpenTelemetry en CNCF
- 2026-W31: [networking/calico/README.md](../networking/calico/README.md) — se aplicó el lanzamiento de Calico for VMs on Kubernetes de Tigera (red unificada de VM+contenedores basada en eBPF)
- 2026-W31: [networking/cilium/README.md](../networking/cilium/README.md) — se aplicó la candidata de lanzamiento Cilium 1.20.0-rc.1
- 2026-W31: sin documento coincidente — Confidential Containers se convierte en un proyecto incubado de CNCF ([fuente](https://www.cncf.io/blog/2026/07/22/confidential-containers-becomes-a-cncf-incubating-project/))
- 2026-W31: sin documento coincidente — CVE gemelos de recorrido de ruta en drivers CSI de Kubernetes (CVE-2026-3864 NFS / CVE-2026-3865 SMB; corregidos en csi-driver-nfs v4.13.1, csi-driver-smb v1.20.1) ([fuente](https://www.sentinelone.com/blog/mount-here-read-there-twin-path-traversal-cves-in-kubernetes-storage/))
- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — se aplicaron las versiones de parche Cilium 1.19.6/1.18.12/1.17.18 y CVE-2026-56743 (problema de ipBlock NetworkPolicy)
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — se aplicaron las versiones de parche Istio 1.30.3/1.29.6
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — se aplicó Linkerd edge-26.7.1 (solicitudes a puertos de Service no definidos no permitidas, cambio incompatible)
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — se aplicó la compatibilidad con ARC zonal shift/autoshift para EKS Auto Mode
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — se aplicó la compatibilidad con ARC zonal shift para EKS Auto Mode
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — se aplicaron versiones de parche coordinadas de Karpenter en todas las líneas mantenidas (v1.3.8–v1.11.3)
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicaron Kubernetes v1.37.0-beta.0 y el calendario de lanzamiento de v1.37
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicaron ArgoCon Japan 2026 y la próxima sesión sobre la hoja de ruta de Argo CD 3.5
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — se aplicó la guía del blog de Kubernetes sobre exportadores de métricas personalizados
- 2026-W30: sin documento coincidente — HAMi se convierte en un proyecto incubado de CNCF ([fuente](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/))
- 2026-W30: sin documento coincidente — Ejecución de un LLM autohospedado en Kubernetes con vLLM, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/))
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — se aplicó la compatibilidad de ACM con el protocolo ACME (los certificados públicos de ACM ahora se pueden consumir desde cert-manager)
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — se aplicó el patrón de observabilidad en el límite de red NGINX + OpenTelemetry para agentes de AI
- 2026-W29: sin documento coincidente — Evolución de la ingeniería de plataformas para cargas de trabajo nativas de AI, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/))
- 2026-07-11: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicó la versión etcd v3.7.0 (RangeStream y más)
- 2026-07-11: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — se aplicó la reducción de hasta un 60 % de la tarifa de administración de GPU de EKS Auto Mode
- 2026-07-11: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — se aplicó la versión Karpenter v1.14.0 (API CapacityBuffers y más)
- 2026-07-11: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — se aplicó CloudWatch Application Signals Service Events
- 2026-07-11: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicó la versión de parche ArgoCD v3.4.5
- 2026-07-11: sin documento coincidente — Cómo afrontar el retiro de ingress-nginx (marzo de 2026), blog de CNCF ([fuente](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/))
- 2026-07-11: sin documento coincidente — Publicado el documento técnico de CNCF sobre Data Storage in Cloud Native AI ([fuente](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/))
- 2026-07-11: sin documento coincidente — Amazon EMR on EKS ahora admite un agente de solución de problemas de Apache Spark ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/))
- 2026-07-11: sin documento coincidente — Revisión de precios de nodos híbridos/multicloud de AWS Systems Manager (se elimina Advanced Instances Tier) ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/))
