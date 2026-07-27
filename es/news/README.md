# Noticias
> **Última actualización**: July 27, 2026

Las noticias del ecosistema de Kubernetes, Amazon EKS y CNCF no se recopilan aquí en documentos de resumen independientes. Cada semana, GitHub Actions aplica las noticias relevantes directamente al documento existente al que se relacionan, y este registro de actualizaciones solo registra qué documento cambió y por qué. Las noticias sin un documento correspondiente se registran aquí únicamente como un enlace.

## Registro de actualizaciones

- 2026-W31: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicaron las versiones de parche Kubernetes v1.36.3/v1.35.7/v1.34.10 y la entrada en vigor del Code Freeze de v1.37
- 2026-W31: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — se aplicó la compatibilidad con EFA y grupos de ubicación de EC2 para los node pools de EKS Auto Mode
- 2026-W31: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — se aplicó la compatibilidad con EFA y grupos de ubicación de EC2 para los node pools de Karpenter
- 2026-W31: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — se aplicaron los aumentos de límites de AMP (1.5B de series activas, 200K reglas por workspace)
- 2026-W31: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — se aplicó la graduación de OpenTelemetry en CNCF
- 2026-W31: [networking/calico/README.md](../networking/calico/README.md) — se aplicó el lanzamiento de Calico for VMs on Kubernetes de Tigera (red unificada de VM+container basada en eBPF)
- 2026-W31: [networking/cilium/README.md](../networking/cilium/README.md) — se aplicó la versión candidata Cilium 1.20.0-rc.1
- 2026-W31: sin documento correspondiente — Confidential Containers se convierte en un proyecto en incubación de CNCF ([fuente](https://www.cncf.io/blog/2026/07/22/confidential-containers-becomes-a-cncf-incubating-project/))
- 2026-W31: sin documento correspondiente — CVE de path traversal gemelos en los drivers CSI de Kubernetes (CVE-2026-3864 NFS / CVE-2026-3865 SMB; corregidos en csi-driver-nfs v4.13.1, csi-driver-smb v1.20.1) ([fuente](https://www.sentinelone.com/blog/mount-here-read-there-twin-path-traversal-cves-in-kubernetes-storage/))
- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — se aplicaron las versiones de parche Cilium 1.19.6/1.18.12/1.17.18 y CVE-2026-56743 (problema de ipBlock NetworkPolicy)
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — se aplicaron las versiones de parche Istio 1.30.3/1.29.6
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — se aplicó Linkerd edge-26.7.1 (solicitudes a puertos de Service no definidos no permitidas, cambio incompatible)
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — se aplicó la compatibilidad con ARC zonal shift/autoshift para EKS Auto Mode
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — se aplicó la compatibilidad con ARC zonal shift para EKS Auto Mode
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — se aplicaron versiones de parche coordinadas de Karpenter en todas las líneas mantenidas (v1.3.8–v1.11.3)
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicaron Kubernetes v1.37.0-beta.0 y el calendario de lanzamiento de v1.37
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicaron ArgoCon Japan 2026 y la próxima sesión sobre la hoja de ruta de Argo CD 3.5
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — se aplicó la guía del blog de Kubernetes sobre custom metrics exporter
- 2026-W30: sin documento correspondiente — HAMi se convierte en un proyecto en incubación de CNCF ([fuente](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/))
- 2026-W30: sin documento correspondiente — Ejecución de un LLM autohospedado en Kubernetes con vLLM, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/))
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — se aplicó la compatibilidad de ACM con el protocolo ACME (los certificados públicos de ACM ahora se pueden consumir desde cert-manager)
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — se aplicó el patrón de observabilidad de límite de red NGINX + OpenTelemetry para agentes de AI
- 2026-W29: sin documento correspondiente — Evolución de la ingeniería de plataformas para cargas de trabajo AI-native, blog de CNCF ([fuente](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/))
- 2026-07-11: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — se aplicó la versión etcd v3.7.0 (RangeStream y más)
- 2026-07-11: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — se aplicó la reducción de hasta un 60 % en la tarifa de administración de GPU de EKS Auto Mode
- 2026-07-11: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — se aplicó la versión Karpenter v1.14.0 (API CapacityBuffers y más)
- 2026-07-11: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — se aplicó CloudWatch Application Signals Service Events
- 2026-07-11: [gitops/argocd/README.md](../gitops/argocd/README.md) — se aplicó la versión de parche ArgoCD v3.4.5
- 2026-07-11: sin documento correspondiente — Cómo abordar la retirada de ingress-nginx (marzo de 2026), blog de CNCF ([fuente](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/))
- 2026-07-11: sin documento correspondiente — Se publicó el documento técnico de CNCF Data Storage in Cloud Native AI ([fuente](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/))
- 2026-07-11: sin documento correspondiente — Amazon EMR on EKS ahora admite un agente de resolución de problemas de Apache Spark ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/))
- 2026-07-11: sin documento correspondiente — Revisión de precios de nodos híbridos/multicloud de AWS Systems Manager (se eliminó el nivel Advanced Instances) ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/))
