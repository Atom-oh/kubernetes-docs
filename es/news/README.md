# Noticias
> **Última actualización**: September 12, 2026

Esta página registra los cambios en la documentación motivados por noticias de Kubernetes, Amazon EKS y CNCF. GitHub Actions prepara actualizaciones cada lunes a las 09:00 KST y abre una PR después de superar su control de calidad. Los cambios llegan al sitio después de la revisión, la integración y el despliegue.

Las etiquetas de semana identifican las semanas de las entradas del registro y pueden diferir de las fechas de publicación de las fuentes. Estos son registros históricos; consulte las guías enlazadas y las fuentes oficiales para conocer el soporte, los parches de seguridad y los requisitos operativos actuales. «Sin documento coincidente» describe la coincidencia automática en aquel momento.

## Registro de actualizaciones

- 2026-W36: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se incorporó la versión Kubernetes v1.37 «Garhwal» (certificados de Pod/ClusterTrustBundles estables, Metrics API con disponibilidad general, obsolescencia de kube-dns y del modo IPVS, entre otros cambios)
- 2026-W36: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — se incorporaron los parches de seguridad Istio 1.30.4/1.29.7 (ISTIO-SECURITY-2026-006, 13 CVE de Envoy)
- 2026-W36: [gitops/argocd/README.md](../gitops/argocd/README.md) — se incorporaron los parches ArgoCD v3.5.2/v3.4.8
- 2026-W36: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — se incorporó Linkerd edge-26.8.4 (negociación de versiones de la API TLSRoute, entre otros cambios)
- 2026-W36: sin documento coincidente — Amazon EKS ahora admite hasta 10 proveedores externos de identidad OIDC por clúster ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-multiple-oidc-providers))
- 2026-W36: sin documento coincidente — Escalar antes del pico: escalado automático predictivo para cargas de GPU en Kubernetes, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/08/28/scale-before-the-spike-predictive-autoscaling-for-gpu-workloads-on-kubernetes/))
- 2026-W36: sin documento coincidente — Construcción de una fábrica de IA en Kubernetes, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/08/27/building-an-ai-factory-on-kubernetes/))
- 2026-W35: [gitops/argocd/README.md](../gitops/argocd/README.md) — se incorporó el soporte de configuración personalizada (mediante el ConfigMap `argocd-cm`) para la funcionalidad gestionada de Argo CD de Amazon EKS
- 2026-W35: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se incorporaron los parches Kubernetes v1.36.4/v1.35.8/v1.34.11 y v1.37.0-rc.1
- 2026-W35: [networking/cilium/README.md](../networking/cilium/README.md) — se incorporaron los parches Cilium 1.20.1/1.19.7/1.18.13
- 2026-W35: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — se incorporó el parche Karpenter v1.14.1
- 2026-W35: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — se incorporó la versión Istio 1.31.0-rc.0 (entrada de 1.31 en fase RC)
- 2026-W35: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — se incorporó la guía del blog de CNCF para convertir consultas SQL lentas en métricas derivadas de spans de OTel
- 2026-W35: sin documento coincidente — Amazon EKS ahora admite la rotación de la autoridad de certificación (CA) con gestión automática del ciclo de vida ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-certificate-authority-ca-rotation-automated-lifecycle-management))
- 2026-W35: sin documento coincidente — Kubeflow se gradúa en CNCF ([fuente](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/))
- 2026-W34: [gitops/argocd/README.md](../gitops/argocd/README.md) — se incorporaron la versión de disponibilidad general ArgoCD v3.5.0 y los parches v3.5.1/v3.4.7/v3.3.14
- 2026-W34: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — se incorporó la versión Istio 1.31.0-beta.1 (entrada de 1.31 en fase beta)
- 2026-W34: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — se incorporó Linkerd edge-26.8.2 (soporte de Gateway API 1.5.1, versión máxima de k8s probada: 1.36)
- 2026-W34: sin documento coincidente — Amazon EKS ahora admite parámetros avanzados de configuración del plano de control de Kubernetes (ajustes del scheduler, controller manager y API server) ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-control-plane-configuration-parameters))
- 2026-W34: sin documento coincidente — Cloud Native Buildpacks se convierte en un proyecto graduado de CNCF ([fuente](https://www.cncf.io/announcements/2026/08/11/cncf-announces-graduation-of-cloud-native-buildpacks-advancing-the-standard-for-container-builds/))
- 2026-W34: sin documento coincidente — Se anuncia el programa de KubeCon + CloudNativeCon North America 2026 y se añade un nuevo itinerario de AI Inference + Agentic ([fuente](https://www.cncf.io/announcements/2026/08/10/cncf-reveals-kubecon-cloudnativecon-north-america-2026-schedule-adds-new-ai-inference-agentic-track/))
- 2026-W34: sin documento coincidente — Cómo dar formato legible al YAML de Kubernetes como KYAML, blog de Kubernetes ([fuente](https://kubernetes.io/blog/2026/08/11/how-to-pretty-print-kubernetes-yaml-as-kyaml/))
- 2026-W33: [networking/04-gateway-api.md](../networking/04-gateway-api.md) — se incorporó Gateway API v1.6 (TCPRoute/UDPRoute pasaron a Standard v1 y cambios por canal en la disponibilidad de API obsoletas)
- 2026-W33: [gitops/argocd/README.md](../gitops/argocd/README.md) — se incorporó ArgoCD v3.5.0 con disponibilidad general (migración a Helm 4, verificación de integridad de fuentes en fase alfa y mejoras de ApplicationSet)
- 2026-W33: [networking/cilium/README.md](../networking/cilium/README.md) — se incorporaron Cilium 1.20.0 con disponibilidad general (Gateway API v1.6.1, KCNP y migración de IPAM con múltiples pools) y 1.21.0-pre.0
- 2026-W33: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se incorporaron el adelanto de Kubernetes v1.37, la entrada en vigor de Docs Freeze y la etiqueta v1.38.0-alpha.0
- 2026-W33: sin documento coincidente — Amazon ECR ahora admite capas de imagen de hasta 200 GB para Docker push ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-ecr-image-layers/))
- 2026-W33: sin documento coincidente — K8gb se convierte en un proyecto en incubación de CNCF ([fuente](https://www.cncf.io/announcements/2026/08/05/k8gb-becomes-a-cncf-incubating-project/))
- 2026-W33: sin documento coincidente — OpenCost 1.121.0 añade seguimiento de costes de inferencia en Kubernetes ([fuente](https://www.cncf.io/blog/2026/08/05/opencost-1-121-0-first-of-a-kind-kubernetes-inference-cost-tracking/))
- 2026-W33: sin documento coincidente — ¿Sustituye Kubernetes DRA a HAMi?, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/08/07/does-kubernetes-dra-replace-hami/))
- 2026-W31: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se incorporaron los parches Kubernetes v1.36.3/v1.35.7/v1.34.10 y la entrada en vigor de Code Freeze de v1.37
- 2026-W31: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — se incorporó el soporte de EFA y grupos de colocación EC2 para los pools de nodos de EKS Auto Mode
- 2026-W31: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — se incorporó el soporte de EFA y grupos de colocación EC2 para los pools de nodos de Karpenter
- 2026-W31: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — se incorporaron los aumentos de límites de AMP (1.500 millones de series activas y 200.000 reglas por espacio de trabajo)
- 2026-W31: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — se incorporó la graduación de OpenTelemetry en CNCF
- 2026-W31: [networking/calico/README.md](../networking/calico/README.md) — se incorporó el lanzamiento de Calico for VMs on Kubernetes de Tigera (red unificada de máquinas virtuales y contenedores basada en eBPF)
- 2026-W31: [networking/cilium/README.md](../networking/cilium/README.md) — se incorporó la versión candidata Cilium 1.20.0-rc.1
- 2026-W31: sin documento coincidente — Confidential Containers se convierte en un proyecto en incubación de CNCF ([fuente](https://www.cncf.io/blog/2026/07/22/confidential-containers-becomes-a-cncf-incubating-project/))
- 2026-W31: sin documento coincidente — Dos CVE de recorrido de rutas en controladores CSI de Kubernetes (CVE-2026-3864 NFS / CVE-2026-3865 SMB; corregidas en csi-driver-nfs v4.13.1 y csi-driver-smb v1.20.1) ([fuente](https://www.sentinelone.com/blog/mount-here-read-there-twin-path-traversal-cves-in-kubernetes-storage/))
- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — se incorporaron los parches Cilium 1.19.6/1.18.12/1.17.18 y CVE-2026-56743 (problema de ipBlock en NetworkPolicy)
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — se incorporaron los parches Istio 1.30.3/1.29.6
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — se incorporó Linkerd edge-26.7.1 (prohibición de solicitudes a puertos de servicio no definidos, cambio incompatible)
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — se incorporó el soporte de zonal shift/autoshift de ARC para EKS Auto Mode
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — se incorporó el soporte de zonal shift de ARC para EKS Auto Mode
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — se incorporaron los parches de Karpenter para ramas anteriores (v1.3.8–v1.11.3)
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se incorporaron Kubernetes v1.37.0-beta.0 y el calendario de lanzamiento de v1.37
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — se incorporaron ArgoCon Japan 2026 y la próxima sesión sobre la hoja de ruta de Argo CD 3.5
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — se incorporó la guía del blog de Kubernetes sobre exportadores de métricas personalizadas
- 2026-W30: sin documento coincidente — HAMi se convierte en un proyecto en incubación de CNCF ([fuente](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/))
- 2026-W30: sin documento coincidente — Ejecución de un LLM autohospedado en Kubernetes con vLLM, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/))
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — se incorporó el soporte de ACM para el protocolo ACME (cert-manager ya puede utilizar los certificados públicos de ACM)
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — se incorporó el patrón de observabilidad de límites de red con NGINX + OpenTelemetry para agentes de IA
- 2026-W29: sin documento coincidente — Evolución de la ingeniería de plataformas para cargas nativas de IA, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/))
- 2026-07-11: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se incorporó la versión etcd v3.7.0 (RangeStream, entre otros cambios)
- 2026-07-11: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — se incorporó la reducción de hasta el 60% de la tarifa de gestión de GPU de EKS Auto Mode
- 2026-07-11: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — se incorporó la versión Karpenter v1.14.0 (API CapacityBuffers, entre otros cambios)
- 2026-07-11: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — se incorporaron los Service Events de CloudWatch Application Signals
- 2026-07-11: [gitops/argocd/README.md](../gitops/argocd/README.md) — se incorporó el parche ArgoCD v3.4.5
- 2026-07-11: sin documento coincidente — Cómo afrontar la retirada de ingress-nginx (marzo de 2026), blog de CNCF ([fuente](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/))
- 2026-07-11: sin documento coincidente — Publicación del documento técnico de CNCF sobre almacenamiento de datos en IA nativa de la nube ([fuente](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/))
- 2026-07-11: sin documento coincidente — Amazon EMR on EKS ahora admite un agente para resolver problemas de Apache Spark ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/))
- 2026-07-11: sin documento coincidente — Revisión de los precios de nodos híbridos/multinube de AWS Systems Manager (eliminación de Advanced Instances Tier) ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/))
