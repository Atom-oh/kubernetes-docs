# News
> **Last Updated**: July 27, 2026

Kubernetes, Amazon EKS, and CNCF ecosystem news isn't collected into separate digest documents here. Each week, GitHub Actions applies relevant news directly to the existing doc it relates to, and this update log records only which doc changed and why. News with no matching doc is recorded here as a link only.

## Update Log

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
