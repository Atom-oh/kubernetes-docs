# 新闻
> **最后更新**: August 31, 2026

此处不会将 Kubernetes、Amazon EKS 和 CNCF 生态系统新闻汇集到单独的摘要文档中。每周，GitHub Actions 会将相关新闻直接应用到其对应的现有文档中，而此更新日志仅记录变更了哪个文档以及原因。没有匹配文档的新闻仅在此处作为链接记录。

## 更新日志

- 2026-W36: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已应用 Kubernetes v1.37 “Garhwal” 发布（Pod certificates/ClusterTrustBundles Stable、Metrics API GA、kube-dns 和 IPVS-mode 弃用等）
- 2026-W36: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 已应用 Istio 1.30.4/1.29.7 安全补丁发布（ISTIO-SECURITY-2026-006、13 个 Envoy CVE）
- 2026-W36: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已应用 ArgoCD v3.5.2/v3.4.8 补丁发布
- 2026-W36: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — 已应用 Linkerd edge-26.8.4（TLSRoute API 版本协商等）
- 2026-W36: 无匹配文档 — Amazon EKS 现在支持每个集群最多 10 个外部 OIDC 身份提供商（[来源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-multiple-oidc-providers)）
- 2026-W36: 无匹配文档 — 在峰值前扩缩容：Kubernetes 上 GPU 工作负载的预测性自动扩缩容，CNCF 博客（[来源](https://www.cncf.io/blog/2026/08/28/scale-before-the-spike-predictive-autoscaling-for-gpu-workloads-on-kubernetes/)）
- 2026-W36: 无匹配文档 — 在 Kubernetes 上构建 AI 工厂，CNCF 博客（[来源](https://www.cncf.io/blog/2026/08/27/building-an-ai-factory-on-kubernetes/)）
- 2026-W35: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已为 Amazon EKS 托管 Argo CD 功能应用自定义配置支持（通过 `argocd-cm` ConfigMap）
- 2026-W35: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已应用 Kubernetes v1.36.4/v1.35.8/v1.34.11 补丁发布和 v1.37.0-rc.1
- 2026-W35: [networking/cilium/README.md](../networking/cilium/README.md) — 已应用 Cilium 1.20.1/1.19.7/1.18.13 补丁发布
- 2026-W35: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 已应用 Karpenter v1.14.1 补丁发布
- 2026-W35: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 已应用 Istio 1.31.0-rc.0 发布（1.31 进入 RC）
- 2026-W35: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 已应用 CNCF 博客中将缓慢 SQL 查询提炼为 OTel span 派生指标的指南
- 2026-W35: 无匹配文档 — Amazon EKS 现已支持通过自动化生命周期管理进行证书颁发机构（CA）轮换（[来源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-certificate-authority-ca-rotation-automated-lifecycle-management)）
- 2026-W35: 无匹配文档 — Kubeflow 在 CNCF 中毕业（[来源](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/)）
- 2026-W34: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已应用 ArgoCD v3.5.0 GA 发布及 v3.5.1/v3.4.7/v3.3.14 补丁发布
- 2026-W34: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 已应用 Istio 1.31.0-beta.1 发布（1.31 进入 beta）
- 2026-W34: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — 已应用 Linkerd edge-26.8.2（Gateway API 1.5.1 支持，已测试的最高 k8s 版本为 1.36）
- 2026-W34: 无匹配文档 — Amazon EKS 现已支持高级 Kubernetes control plane 配置参数（scheduler/controller manager/API server 调优）（[来源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-control-plane-configuration-parameters)）
- 2026-W34: 无匹配文档 — Cloud Native Buildpacks 成为 CNCF 毕业项目（[来源](https://www.cncf.io/announcements/2026/08/11/cncf-announces-graduation-of-cloud-native-buildpacks-advancing-the-standard-for-container-builds/)）
- 2026-W34: 无匹配文档 — KubeCon + CloudNativeCon North America 2026 日程公布，新增 AI Inference + Agentic 专题（[来源](https://www.cncf.io/announcements/2026/08/10/cncf-reveals-kubecon-cloudnativecon-north-america-2026-schedule-adds-new-ai-inference-agentic-track/)）
- 2026-W34: 无匹配文档 — 如何将 Kubernetes YAML 美化输出为 KYAML，Kubernetes 博客（[来源](https://kubernetes.io/blog/2026/08/11/how-to-pretty-print-kubernetes-yaml-as-kyaml/)）
- 2026-W33: [networking/04-gateway-api.md](../networking/04-gateway-api.md) — 已应用 Gateway API v1.6（TCPRoute/UDPRoute 毕业为 Standard v1，实验性资源迁移至 x-k8s.io API group）
- 2026-W33: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已应用 ArgoCD v3.5.0 GA（Helm 4 迁移、source integrity verification alpha、ApplicationSet 改进）
- 2026-W33: [networking/cilium/README.md](../networking/cilium/README.md) — 已应用 Cilium 1.20.0 GA（Gateway API v1.6.1、KCNP、multi-pool IPAM 迁移）和 1.21.0-pre.0
- 2026-W33: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已应用 Kubernetes v1.37 前瞻、Docs Freeze 生效以及 v1.38.0-alpha.0 标签
- 2026-W33: 无匹配文档 — Amazon ECR 现已支持通过 Docker push 推送最大 200 GB 的镜像层（[来源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-ecr-image-layers/)）
- 2026-W33: 无匹配文档 — K8gb 成为 CNCF 孵化项目（[来源](https://www.cncf.io/announcements/2026/08/05/k8gb-becomes-a-cncf-incubating-project/)）
- 2026-W33: 无匹配文档 — OpenCost 1.121.0 新增 Kubernetes 推理成本跟踪（[来源](https://www.cncf.io/blog/2026/08/05/opencost-1-121-0-first-of-a-kind-kubernetes-inference-cost-tracking/)）
- 2026-W33: 无匹配文档 — Kubernetes DRA 会取代 HAMi 吗？，CNCF 博客（[来源](https://www.cncf.io/blog/2026/08/07/does-kubernetes-dra-replace-hami/)）
- 2026-W31: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已应用 Kubernetes v1.36.3/v1.35.7/v1.34.10 补丁发布以及 v1.37 Code Freeze 生效
- 2026-W31: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — 已应用 EKS Auto Mode node pool 对 EFA 和 EC2 placement group 的支持
- 2026-W31: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 已应用 Karpenter node pool 对 EFA 和 EC2 placement group 的支持
- 2026-W31: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — 已应用 AMP 限制提升（每个 workspace 15 亿个活跃 series、20 万条 rules）
- 2026-W31: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 已应用 OpenTelemetry 在 CNCF 毕业
- 2026-W31: [networking/calico/README.md](../networking/calico/README.md) — 已应用 Tigera 在 Kubernetes 上推出的 Calico for VMs（基于 eBPF 的 VM+container 统一网络）
- 2026-W31: [networking/cilium/README.md](../networking/cilium/README.md) — 已应用 Cilium 1.20.0-rc.1 release candidate
- 2026-W31: 无匹配文档 — Confidential Containers 成为 CNCF 孵化项目（[来源](https://www.cncf.io/blog/2026/07/22/confidential-containers-becomes-a-cncf-incubating-project/)）
- 2026-W31: 无匹配文档 — Kubernetes CSI driver 中的双路径遍历 CVE（CVE-2026-3864 NFS / CVE-2026-3865 SMB；已在 csi-driver-nfs v4.13.1、csi-driver-smb v1.20.1 中修复）（[来源](https://www.sentinelone.com/blog/mount-here-read-there-twin-path-traversal-cves-in-kubernetes-storage/)）
- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — 已应用 Cilium 1.19.6/1.18.12/1.17.18 补丁发布和 CVE-2026-56743（ipBlock NetworkPolicy 问题）
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 已应用 Istio 1.30.3/1.29.6 补丁发布
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — 已应用 Linkerd edge-26.7.1（不允许请求未定义的 Service port，破坏性变更）
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — 已应用 ARC zonal shift/autoshift 对 EKS Auto Mode 的支持
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — 已应用 ARC zonal shift 对 EKS Auto Mode 的支持
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 已应用所有维护分支的协调 Karpenter 补丁发布（v1.3.8–v1.11.3）
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已应用 Kubernetes v1.37.0-beta.0 及 v1.37 发布计划
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已应用 ArgoCon Japan 2026 和即将举行的 Argo CD 3.5 roadmap session
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — 已应用 Kubernetes 博客的 custom metrics exporter 指南
- 2026-W30: 无匹配文档 — HAMi 成为 CNCF 孵化项目（[来源](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/)）
- 2026-W30: 无匹配文档 — 使用 vLLM 在 Kubernetes 中运行 self-hosted LLM，CNCF 博客（[来源](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/)）
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — 已应用 ACM 对 ACME protocol 的支持（ACM public certificate 现在可由 cert-manager 使用）
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 已应用适用于 AI agent 的 NGINX + OpenTelemetry network-boundary observability 模式
- 2026-W29: 无匹配文档 — 为 AI-native workload 演进 platform engineering，CNCF 博客（[来源](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/)）
- 2026-07-11: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已应用 etcd v3.7.0 发布（RangeStream 等）
- 2026-07-11: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — 已应用 EKS Auto Mode GPU 管理费最高降低 60%
- 2026-07-11: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 已应用 Karpenter v1.14.0 发布（CapacityBuffers API 等）
- 2026-07-11: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — 已应用 CloudWatch Application Signals Service Events
- 2026-07-11: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已应用 ArgoCD v3.4.5 补丁发布
- 2026-07-11: 无匹配文档 — 应对 ingress-nginx 退役（2026 年 3 月），CNCF 博客（[来源](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/)）
- 2026-07-11: 无匹配文档 — 已发布 CNCF《Cloud Native AI 中的数据存储》白皮书（[来源](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/)）
- 2026-07-11: 无匹配文档 — Amazon EMR on EKS 现已支持 Apache Spark 故障排除 agent（[来源](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/)）
- 2026-07-11: 无匹配文档 — AWS Systems Manager hybrid/multicloud node 定价全面调整（取消 Advanced Instances Tier）（[来源](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/)）
