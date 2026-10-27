# News
> **Last Updated**: October 26, 2026

This page records documentation changes prompted by Kubernetes, Amazon EKS and CNCF news. GitHub Actions prepares updates each Monday at 09:00 KST and opens a PR after its quality gate passes. Changes reach the site after review, merge and deployment.

Week labels identify log-entry weeks and may differ from source publication dates. These are historical records; consult the linked guides and official sources for current support, security patches and operating requirements. “No matching doc” describes the automated match at that time.

<!-- news-dashboard -->

<details class="news-log">
<summary>Expand the complete update log</summary>

## Update Log

- 2026-W44: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — applied the Istio 1.31.3/1.30.7/1.29.10 security patch releases (ISTIO-SECURITY-2026-008, CVE-2026-111943: distrust of the compromised eMudhra intermediate CA certificates; 1.29.10 is an exceptional post-EOL release) ([source](https://istio.io/latest/news/security/istio-security-2026-008/))
- 2026-W44: [networking/cilium/README.md](../networking/cilium/README.md) — applied the Cilium 1.20.4/1.19.10/1.18.16 out-of-band security patch releases (CVE-2026-111943; Go 1.26.10 no longer trusts the compromised eMudhra intermediate CA certificates) ([source](https://github.com/cilium/cilium/releases/tag/v1.20.4))
- 2026-W44: [gitops/argocd/README.md](../gitops/argocd/README.md) — applied the Argo CD v3.5.6/v3.4.12/v3.3.17 bug-fix patch releases and v3.3.18, which carries a security fix removing trust in the compromised eMudhra CA certificates ([source](https://github.com/argoproj/argo-cd/releases/tag/v3.3.18))
- 2026-W44: [gitops/argocd/README.md](../gitops/argocd/README.md) — applied the Argo CD v3.6.0-rc4 release candidate ([source](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc4))
- 2026-W44: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — applied the Karpenter v1.15.1 patch and the v1.14.2/v1.14.3/v1.9.3 LTS patch releases (bug fixes; all lines move to Go 1.26.10, which distrusts the compromised eMudhra intermediate CA certificates) ([source](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.15.1))
- 2026-W44: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — applied the CNCF blog guide on filtering and reducing AI agent telemetry in the OpenTelemetry Collector ([source](https://www.cncf.io/blog/2026/10/22/filtering-and-reducing-ai-agent-telemetry-with-the-opentelemetry-collector/))
- 2026-W44: no matching doc — Amazon EMR on EKS reduces the EMR charge (per-vCPU-hour and per-GB-hour) by 30 percent; underlying EKS charges unchanged ([source](https://aws.amazon.com/about-aws/whats-new/2026/10/emr-eks-reduces-emr-charge-30-percent/))
- 2026-W44: no matching doc — How AI workloads are reshaping Kubernetes autoscaling, CNCF blog ([source](https://www.cncf.io/blog/2026/10/19/how-ai-workloads-are-reshaping-kubernetes-autoscaling/))
- 2026-W43: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.2/1.30.6/1.29.9 patch releases published (including the ISTIO-SECURITY-2026-007 security patch; already reflected in the doc by its earlier review) ([source](https://istio.io/news/releases/1.31.x/announcing-1.31.2/))
- 2026-W43: [networking/cilium/README.md](../networking/cilium/README.md) — applied the Cilium 1.20.3/1.19.9/1.18.15 patch releases (bug fixes including conntrack GC and handling of CNPs with `nodeSelector`) ([source](https://github.com/cilium/cilium/releases/tag/v1.20.3))
- 2026-W43: [gitops/argocd/README.md](../gitops/argocd/README.md) — applied the Argo CD v3.5.5/v3.4.11/v3.3.16 bug-fix patch releases ([source](https://github.com/argoproj/argo-cd/releases/tag/v3.5.5))
- 2026-W43: [gitops/argocd/README.md](../gitops/argocd/README.md) — applied the Argo CD v3.6.0-rc3 release candidate ([source](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc3))
- 2026-W43: [security/14-waf-edge-api-security.md](../security/14-waf-edge-api-security.md) — applied the announcement of dual-stack (IPv6) support for CloudFront VPC origins ([source](https://aws.amazon.com/about-aws/whats-new/2026/10/cloudfront-vpc-origin-dualstack/))
- 2026-W43: [blockchain/01-fundamentals.md](../blockchain/01-fundamentals.md) — applied the launch of Blockchain Snapshots on AWS (free pre-synced snapshots for Ethereum/Solana node bootstrapping) ([source](https://aws.amazon.com/about-aws/whats-new/2026/10/blockchain-snapshots-node-bootstrapping/))
- 2026-W43: [security/01-kyverno-policy-management.md](../security/01-kyverno-policy-management.md) — applied the CNCF blog introduction of Nirmata Runtime for Kyverno (kernel-level runtime policy enforcement via eBPF/LSM) ([source](https://www.cncf.io/blog/2026/10/15/extending-kubernetes-policy-enforcement-to-runtime-security-for-ai-workloads/))
- 2026-W43: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — applied the CNCF blog proposal to treat Software Carbon Intensity (SCI) as OpenTelemetry semantic conventions ([source](https://www.cncf.io/blog/2026/10/15/carbon-as-a-first-class-signal-bringing-software-carbon-intensity-to-opentelemetry/))
- 2026-W43: no matching doc — Tracing the admission state of Kueue-managed Jobs with Headlamp, Kubernetes blog ([source](https://kubernetes.io/blog/2026/10/14/tracing-kueue-admission-with-headlamp/))
- 2026-W42: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — applied the Karpenter v1.15.0 release (node repair as a voluntary disruption with reboot support, CEL in KubeletConfiguration, broader DRA support, and more)
- 2026-W42: [gitops/argocd/README.md](../gitops/argocd/README.md) — applied the Argo CD v3.5.4/v3.4.10/v3.3.15 security patch releases (four CRITICAL issues including repo-server command execution, CVE-2026-77459)
- 2026-W42: [kernel/01-container-primitives.md](../kernel/01-container-primitives.md) — applied the Kubernetes blog's cgroup v1 deprecation status (`failCgroupV1` defaults to `true` from v1.35)
- 2026-W42: no matching doc — Scaling Kubernetes workloads with NVMe SSD-backed node swap (GA in v1.34), Kubernetes blog ([source](https://kubernetes.io/blog/2026/10/05/scaling-kubernetes-workloads-with-node-swap/))
- 2026-W42: no matching doc — Meshery becomes a CNCF incubating project ([source](https://www.cncf.io/blog/2026/10/07/meshery-becomes-a-cncf-incubating-project/))
- 2026-W42: no matching doc — AWS Batch now supports Amazon EKS access entry authentication ([source](https://aws.amazon.com/about-aws/whats-new/2026/10/aws-batch-access-entries/))
- 2026-W41: [eks/08-eks-upgrades.md](../eks/08-eks-upgrades.md) — applied Kubernetes 1.37 support on Amazon EKS and EKS Distro (Metrics API GA, DRA device taints GA, HPA scale-to-zero beta)
- 2026-W41: [gitops/argocd/README.md](../gitops/argocd/README.md) — applied the start of Argo CD 4.0 visioning and ArgoCon North America 2026 news
- 2026-W41: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — applied Atlassian's incident-detection rebuild on OTel, Kafka, and Flink (CNCF blog)
- 2026-W41: no matching doc — Amazon ECS adds Amazon VPC Lattice support for blue/green, linear, and canary deployments ([source](https://aws.amazon.com/about-aws/whats-new/2026/10/amazon-ecs-vpc-lattice-blue-green-deployments))
- 2026-W41: no matching doc — Amazon Managed Grafana now supports creating Grafana 13.2 workspaces ([source](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-managed-grafana-now-supports-creating-grafana-13-2-workspaces))
- 2026-W41: no matching doc — Grafana Tempo 3.1 release (new Kafka features, TraceQL metrics updates, trace redaction, and more) ([source](https://grafana.com/blog/tempo-3-1-release-all-the-latest-features))
- 2026-W41: no matching doc — Guardrails, not gates: rethinking policy in platform teams, CNCF blog ([source](https://www.cncf.io/blog/2026/10/01/guardrails-not-gates-rethinking-policy-in-platform-teams/))
- 2026-W40: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — applied the Kubernetes v1.37.1/v1.36.5/v1.35.9/v1.34.12 patch releases and the v1.37 PVC `Unused` condition (Beta) blog post
- 2026-W40: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — applied the Istio 1.31.1/1.30.5/1.29.8 patch releases (including the BackendTLSPolicy fail-open security fix GHSA-qm8v-g4f9-qhjx)
- 2026-W40: [eks/04-eks-storage-part1.md](../eks/04-eks-storage-part1.md) — applied the EFS CSI driver mount option injection vulnerability CVE-2026-6437 (fixed in v3.0.1)
- 2026-W40: [ai-ml/08-llm-gateway.md](../ai-ml/08-llm-gateway.md) — applied the Amazon SageMaker HyperPod Inference Gateway launch (EKS managed add-on, GPU-aware routing)
- 2026-W40: no matching doc — Amazon EMR on EKS now supports IPv6 Amazon EKS clusters ([source](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-emr-eks-ipv6-support))
- 2026-W40: no matching doc — Run interactive workloads on Amazon EMR on EKS with Spark Connect ([source](https://aws.amazon.com/about-aws/whats-new/2026/09/emr-eks-spark-connect-interactive/))
- 2026-W40: no matching doc — Amazon CloudWatch Omni general availability (AI-first observability experience, OpenTelemetry interoperability) ([source](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-cloudwatch-omni-ai/))
- 2026-W39: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — applied three Kubernetes v1.37 feature deep dives (Memory QoS Beta, Pod-Level Resource Managers Beta, emptyDir permissions and bind mount options)
- 2026-W39: [networking/cilium/README.md](../networking/cilium/README.md) — applied Cilium 1.20.2/1.19.8/1.18.14 patch releases and the CNCF blog's 1.20 feature recap
- 2026-W39: [gitops/argocd/README.md](../gitops/argocd/README.md) — applied Argo CD v3.5.3/v3.4.9 patch releases and v3.6.0-rc1
- 2026-W39: no matching doc — Kubernetes CSI Changed Block Tracking (CBT) API graduates to Beta, with differences from Alpha, Kubernetes blog ([source](https://kubernetes.io/blog/2026/09/14/csi-changed-block-tracking-beta/))
- 2026-W39: no matching doc — AWS Resilience Hub adds three new capabilities (including EKS-label-based service resource discovery within a namespace) ([source](https://aws.amazon.com/about-aws/whats-new/2026/09/resilience-hub-eks-dependency-policy/))
- 2026-W38: [core/08-scheduling-preemption-eviction.md](../core/08-scheduling-preemption-eviction.md) — applied Kubernetes v1.37 scheduler preemption for in-place Pod resize (Alpha) and Workload-Aware Scheduling advances (Workload/PodGroup Beta, CompositePodGroup API)
- 2026-W38: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — applied Kubernetes v1.37 Node lifecycle conditions (five well-known conditions for drain, maintenance and graceful shutdown)
- 2026-W38: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — applied Prometheus native histograms for Kubernetes v1.37 component metrics (Beta, enabled by default)
- 2026-W38: [networking/cilium/README.md](../networking/cilium/README.md) — applied the Cilium 1.21.0-pre.2 prerelease (Gateway API session persistence, AWS managed prefix lists, BPF masquerading by default)
- 2026-W38: no matching doc — Karmada becomes a CNCF graduated project ([source](https://www.cncf.io/announcements/2026/09/07/cloud-native-computing-foundation-announces-karmada-graduation/))
- 2026-W38: no matching doc — Kubernetes disaster recovery: guidance from three reproducible failure scenarios, CNCF blog ([source](https://www.cncf.io/blog/2026/09/10/kubernetes-disaster-recovery-guidance-from-three-reproducible-failure-scenarios/))
- 2026-W38: no matching doc — AWS Private CA EKS add-on and Connector for AD now available in AWS GovCloud (US) ([source](https://aws.amazon.com/about-aws/whats-new/2026/09/private-ca-eks-addon-ad-govcloud/))
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
- 2026-W33: [networking/04-gateway-api.md](../networking/04-gateway-api.md) — applied Gateway API v1.6 (TCPRoute/UDPRoute graduated to Standard v1, channel-specific deprecated API serving changes)
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
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — applied Karpenter patch releases for older lines (v1.3.8–v1.11.3)
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

</details>
