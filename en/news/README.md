# News
> **Last Updated**: August 31, 2026

Kubernetes, Amazon EKS, and CNCF ecosystem news isn't collected into separate digest documents here. Each week, GitHub Actions applies relevant news directly to the existing doc it relates to, and this update log records only which doc changed and why. News with no matching doc is recorded here as a link only.

## Update Log

- 2026-W36: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — applied the Kubernetes v1.37 "Garhwal" release (Pod certificates/ClusterTrustBundles Stable, Metrics API GA, kube-dns and IPVS-mode deprecations, and more)
- 2026-W36: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — applied the Istio 1.30.4/1.29.7 security patch releases (ISTIO-SECURITY-2026-006, 13 Envoy CVEs)
- 2026-W36: [gitops/argocd/README.md](../gitops/argocd/README.md) — applied the ArgoCD v3.5.2/v3.4.8 patch releases
- 2026-W36: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — applied Linkerd edge-26.8.4 (TLSRoute API version negotiation, and more)
- 2026-W36: no matching doc — Amazon EKS now supports up to 10 external OIDC identity providers per cluster ([source](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-multiple-oidc-providers))
- 2026-W36: no matching doc — Scale before the spike: predictive autoscaling for GPU workloads on Kubernetes, CNCF blog ([source](https://www.cncf.io/blog/2026/08/28/scale-before-the-spike-predictive-autoscaling-for-gpu-workloads-on-kubernetes/))
- 2026-W36: no matching doc — Building an AI factory on Kubernetes, CNCF blog ([source](https://www.cncf.io/blog/2026/08/27/building-an-ai-factory-on-kubernetes/))
- 2026-W35: [gitops/argocd/README.md](../gitops/argocd/README.md) — applied custom configuration support (via the `argocd-cm` ConfigMap) for the Amazon EKS managed Argo CD capability
- 2026-W35: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — applied Kubernetes v1.36.4/v1.35.8/v1.34.11 patch releases and v1.37.0-rc.1
- 2026-W35: [networking/cilium/README.md](../networking/cilium/README.md) — applied Cilium 1.20.1/1.19.7/1.18.13 patch releases
- 2026-W35: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — applied the Karpenter v1.14.1 patch release
- 2026-W35: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — applied the Istio 1.31.0-rc.0 release (1.31 entering RC)
- 2026-W35: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — applied the CNCF blog guide on distilling slow SQL queries into OTel span-derived metrics
- 2026-W35: no matching doc — Amazon EKS now supports certificate authority (CA) rotation with automated lifecycle management ([source](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-certificate-authority-ca-rotation-automated-lifecycle-management))
- 2026-W35: no matching doc — Kubeflow graduates within the CNCF ([source](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/))
- 2026-W34: [gitops/argocd/README.md](../gitops/argocd/README.md) — applied the ArgoCD v3.5.0 GA release and the v3.5.1/v3.4.7/v3.3.14 patch releases
- 2026-W34: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — applied the Istio 1.31.0-beta.1 release (1.31 entering beta)
- 2026-W34: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — applied Linkerd edge-26.8.2 (Gateway API 1.5.1 support, tested max k8s 1.36)
- 2026-W34: no matching doc — Amazon EKS now supports advanced Kubernetes control plane configuration parameters (scheduler/controller manager/API server tuning) ([source](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-control-plane-configuration-parameters))
- 2026-W34: no matching doc — Cloud Native Buildpacks becomes a CNCF graduated project ([source](https://www.cncf.io/announcements/2026/08/11/cncf-announces-graduation-of-cloud-native-buildpacks-advancing-the-standard-for-container-builds/))
- 2026-W34: no matching doc — KubeCon + CloudNativeCon North America 2026 schedule revealed, new AI Inference + Agentic track added ([source](https://www.cncf.io/announcements/2026/08/10/cncf-reveals-kubecon-cloudnativecon-north-america-2026-schedule-adds-new-ai-inference-agentic-track/))
- 2026-W34: no matching doc — How to pretty-print your Kubernetes YAML as KYAML, Kubernetes blog ([source](https://kubernetes.io/blog/2026/08/11/how-to-pretty-print-kubernetes-yaml-as-kyaml/))
- 2026-W33: [networking/04-gateway-api.md](../networking/04-gateway-api.md) — applied Gateway API v1.6 (TCPRoute/UDPRoute graduated to Standard v1, experimental resources moved to the x-k8s.io API group)
- 2026-W33: [gitops/argocd/README.md](../gitops/argocd/README.md) — applied ArgoCD v3.5.0 GA (Helm 4 migration, source integrity verification alpha, ApplicationSet improvements)
- 2026-W33: [networking/cilium/README.md](../networking/cilium/README.md) — applied Cilium 1.20.0 GA (Gateway API v1.6.1, KCNP, multi-pool IPAM migration) and 1.21.0-pre.0
- 2026-W33: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — applied the Kubernetes v1.37 sneak peek, Docs Freeze taking effect, and the v1.38.0-alpha.0 tag
- 2026-W33: no matching doc — Amazon ECR now supports image layers up to 200 GB for Docker push ([source](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-ecr-image-layers/))
- 2026-W33: no matching doc — K8gb becomes a CNCF incubating project ([source](https://www.cncf.io/announcements/2026/08/05/k8gb-becomes-a-cncf-incubating-project/))
- 2026-W33: no matching doc — OpenCost 1.121.0 adds Kubernetes inference cost tracking ([source](https://www.cncf.io/blog/2026/08/05/opencost-1-121-0-first-of-a-kind-kubernetes-inference-cost-tracking/))
- 2026-W33: no matching doc — Does Kubernetes DRA Replace HAMi?, CNCF blog ([source](https://www.cncf.io/blog/2026/08/07/does-kubernetes-dra-replace-hami/))
- 2026-W31: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — applied Kubernetes v1.36.3/v1.35.7/v1.34.10 patch releases and the v1.37 Code Freeze taking effect
- 2026-W31: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — applied EFA and EC2 placement group support for EKS Auto Mode node pools
- 2026-W31: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — applied EFA and EC2 placement group support for Karpenter node pools
- 2026-W31: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — applied AMP limit increases (1.5B active series, 200K rules per workspace)
- 2026-W31: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — applied OpenTelemetry's CNCF graduation
- 2026-W31: [networking/calico/README.md](../networking/calico/README.md) — applied Tigera's Calico for VMs on Kubernetes launch (eBPF-based VM+container unified networking)
- 2026-W31: [networking/cilium/README.md](../networking/cilium/README.md) — applied Cilium 1.20.0-rc.1 release candidate
- 2026-W31: no matching doc — Confidential Containers becomes a CNCF incubating project ([source](https://www.cncf.io/blog/2026/07/22/confidential-containers-becomes-a-cncf-incubating-project/))
- 2026-W31: no matching doc — Twin path traversal CVEs in Kubernetes CSI drivers (CVE-2026-3864 NFS / CVE-2026-3865 SMB; fixed in csi-driver-nfs v4.13.1, csi-driver-smb v1.20.1) ([source](https://www.sentinelone.com/blog/mount-here-read-there-twin-path-traversal-cves-in-kubernetes-storage/))
- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — applied Cilium 1.19.6/1.18.12/1.17.18 patch releases and CVE-2026-56743 (ipBlock NetworkPolicy issue)
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — applied Istio 1.30.3/1.29.6 patch releases
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — applied Linkerd edge-26.7.1 (requests to undefined service ports disallowed, breaking)
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — applied ARC zonal shift/autoshift support for EKS Auto Mode
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — applied ARC zonal shift support for EKS Auto Mode
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — applied coordinated Karpenter patch releases across all maintained lines (v1.3.8–v1.11.3)
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — applied Kubernetes v1.37.0-beta.0 and the v1.37 release schedule
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — applied ArgoCon Japan 2026 and the upcoming Argo CD 3.5 roadmap session
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — applied the Kubernetes blog's custom metrics exporter guide
- 2026-W30: no matching doc — HAMi becomes a CNCF incubating project ([source](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/))
- 2026-W30: no matching doc — Running a self-hosted LLM in Kubernetes with vLLM, CNCF blog ([source](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/))
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — applied ACM support for the ACME protocol (ACM public certificates now consumable from cert-manager)
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — applied NGINX + OpenTelemetry network-boundary observability pattern for AI agents
- 2026-W29: no matching doc — Evolving platform engineering for AI-native workloads, CNCF blog ([source](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/))
- 2026-07-11: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — applied etcd v3.7.0 release (RangeStream and more)
- 2026-07-11: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — applied EKS Auto Mode GPU management fee reduction of up to 60%
- 2026-07-11: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — applied Karpenter v1.14.0 release (CapacityBuffers API and more)
- 2026-07-11: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — applied CloudWatch Application Signals Service Events
- 2026-07-11: [gitops/argocd/README.md](../gitops/argocd/README.md) — applied ArgoCD v3.4.5 patch release
- 2026-07-11: no matching doc — Navigating the ingress-nginx retirement (March 2026), CNCF blog ([source](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/))
- 2026-07-11: no matching doc — CNCF Data Storage in Cloud Native AI white paper published ([source](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/))
- 2026-07-11: no matching doc — Amazon EMR on EKS now supports an Apache Spark troubleshooting agent ([source](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/))
- 2026-07-11: no matching doc — AWS Systems Manager hybrid/multicloud node pricing overhaul (Advanced Instances Tier eliminated) ([source](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/))
