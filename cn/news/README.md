# 新闻
> **最后更新**: August 24, 2026

此处不会将 Kubernetes、Amazon EKS 和 CNCF 生态系统新闻收集成单独的摘要文档。每周，GitHub Actions 会将相关新闻直接应用到其关联的现有文档中，而此更新日志仅记录发生变更的文档及原因。没有匹配文档的新闻仅在此处以链接形式记录。

## 更新日志

- 2026-W35: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已为 Amazon EKS 托管 Argo CD 功能应用自定义配置支持（通过 `argocd-cm` ConfigMap）
- 2026-W35: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已应用 Kubernetes v1.36.4/v1.35.8/v1.34.11 补丁版本以及 v1.37.0-rc.1
- 2026-W35: [networking/cilium/README.md](../networking/cilium/README.md) — 已应用 Cilium 1.20.1/1.19.7/1.18.13 补丁版本
- 2026-W35: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 已应用 Karpenter v1.14.1 补丁版本
- 2026-W35: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 已应用 Istio 1.31.0-rc.0 版本（1.31 进入 RC 阶段）
- 2026-W35: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 已应用 CNCF 博客中关于将缓慢 SQL 查询提炼为源自 OTel span 的指标的指南
- 2026-W35: 没有匹配的文档 — Amazon EKS 现支持通过自动化生命周期管理进行证书颁发机构（CA）轮换（[source](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-certificate-authority-ca-rotation-automated-lifecycle-management)）
- 2026-W35: 没有匹配的文档 — Kubeflow 从 CNCF 毕业（[source](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/)）
- 2026-W34: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已应用 ArgoCD v3.5.0 GA 版本和 v3.5.1/v3.4.7/v3.3.14 补丁版本
- 2026-W34: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 已应用 Istio 1.31.0-beta.1 版本（1.31 进入 beta 阶段）
- 2026-W34: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — 已应用 Linkerd edge-26.8.2（Gateway API 1.5.1 支持，已测试的最高 k8s 版本为 1.36）
- 2026-W34: 没有匹配的文档 — Amazon EKS 现支持高级 Kubernetes control plane 配置参数（scheduler/controller manager/API server 调优）（[source](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-control-plane-configuration-parameters)）
- 2026-W34: 没有匹配的文档 — Cloud Native Buildpacks 成为 CNCF 毕业项目（[source](https://www.cncf.io/announcements/2026/08/11/cncf-announces-graduation-of-cloud-native-buildpacks-advancing-the-standard-for-container-builds/)）
- 2026-W34: 没有匹配的文档 — KubeCon + CloudNativeCon North America 2026 日程公布，新增 AI Inference + Agentic 主题赛道（[source](https://www.cncf.io/announcements/2026/08/10/cncf-reveals-kubecon-cloudnativecon-north-america-2026-schedule-adds-new-ai-inference-agentic-track/)）
- 2026-W34: 没有匹配的文档 — 如何将 Kubernetes YAML 格式化输出为 KYAML，Kubernetes 博客（[source](https://kubernetes.io/blog/2026/08/11/how-to-pretty-print-kubernetes-yaml-as-kyaml/)）
- 2026-W33: [networking/04-gateway-api.md](../networking/04-gateway-api.md) — 已应用 Gateway API v1.6（TCPRoute/UDPRoute 毕业为 Standard v1，实验性资源已迁移至 x-k8s.io API group）
- 2026-W33: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已应用 ArgoCD v3.5.0 GA（Helm 4 迁移、源完整性验证 alpha、ApplicationSet 改进）
- 2026-W33: [networking/cilium/README.md](../networking/cilium/README.md) — 已应用 Cilium 1.20.0 GA（Gateway API v1.6.1、KCNP、多池 IPAM 迁移）和 1.21.0-pre.0
- 2026-W33: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已应用 Kubernetes v1.37 预览、Docs Freeze 生效以及 v1.38.0-alpha.0 标签
- 2026-W33: 没有匹配的文档 — Amazon ECR 现支持 Docker push 的镜像层最高达 200 GB（[source](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-ecr-image-layers/)）
- 2026-W33: 没有匹配的文档 — K8gb 成为 CNCF 孵化项目（[source](https://www.cncf.io/announcements/2026/08/05/k8gb-becomes-a-cncf-incubating-project/)）
- 2026-W33: 没有匹配的文档 — OpenCost 1.121.0 新增 Kubernetes 推理成本跟踪（[source](https://www.cncf.io/blog/2026/08/05/opencost-1-121-0-first-of-a-kind-kubernetes-inference-cost-tracking/)）
- 2026-W33: 没有匹配的文档 — Kubernetes DRA 是否会取代 HAMi？CNCF 博客（[source](https://www.cncf.io/blog/2026/08/07/does-kubernetes-dra-replace-hami/)）
- 2026-W31: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已应用 Kubernetes v1.36.3/v1.35.7/v1.34.10 补丁版本以及 v1.37 Code Freeze 生效
- 2026-W31: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — 已为 EKS Auto Mode node pool 应用 EFA 和 EC2 placement group 支持
- 2026-W31: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 已为 Karpenter node pool 应用 EFA 和 EC2 placement group 支持
- 2026-W31: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — 已应用 AMP 限额提高（15 亿活跃 series，每个 workspace 20 万 rules）
- 2026-W31: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 已应用 OpenTelemetry 从 CNCF 毕业
- 2026-W31: [networking/calico/README.md](../networking/calico/README.md) — 已应用 Tigera 推出 Kubernetes 上的 Calico for VMs（基于 eBPF 的 VM+container 统一网络）
- 2026-W31: [networking/cilium/README.md](../networking/cilium/README.md) — 已应用 Cilium 1.20.0-rc.1 release candidate
- 2026-W31: 没有匹配的文档 — Confidential Containers 成为 CNCF 孵化项目（[source](https://www.cncf.io/blog/2026/07/22/confidential-containers-becomes-a-cncf-incubating-project/)）
- 2026-W31: 没有匹配的文档 — Kubernetes CSI driver 中的双路径遍历 CVE（CVE-2026-3864 NFS / CVE-2026-3865 SMB；已在 csi-driver-nfs v4.13.1、csi-driver-smb v1.20.1 中修复）（[source](https://www.sentinelone.com/blog/mount-here-read-there-twin-path-traversal-cves-in-kubernetes-storage/)）
- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — 已应用 Cilium 1.19.6/1.18.12/1.17.18 补丁版本和 CVE-2026-56743（ipBlock NetworkPolicy 问题）
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 已应用 Istio 1.30.3/1.29.6 补丁版本
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — 已应用 Linkerd edge-26.7.1（不允许请求未定义的 Service port，存在破坏性变更）
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — 已为 EKS Auto Mode 应用 ARC zonal shift/autoshift 支持
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — 已为 EKS Auto Mode 应用 ARC zonal shift 支持
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 已应用所有维护版本线的协调 Karpenter 补丁版本（v1.3.8–v1.11.3）
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已应用 Kubernetes v1.37.0-beta.0 和 v1.37 发布计划
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已应用 ArgoCon Japan 2026 和即将举行的 Argo CD 3.5 路线图会议
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — 已应用 Kubernetes 博客的自定义指标 exporter 指南
- 2026-W30: 没有匹配的文档 — HAMi 成为 CNCF 孵化项目（[source](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/)）
- 2026-W30: 没有匹配的文档 — 使用 vLLM 在 Kubernetes 中运行自托管 LLM，CNCF 博客（[source](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/)）
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — 已应用 ACME protocol 的 ACM 支持（ACM public certificate 现可由 cert-manager 使用）
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 已应用面向 AI agent 的 NGINX + OpenTelemetry network-boundary observability 模式
- 2026-W29: 没有匹配的文档 — 面向 AI-native workload 的平台工程演进，CNCF 博客（[source](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/)）
- 2026-07-11: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已应用 etcd v3.7.0 版本（RangeStream 等）
- 2026-07-11: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — 已应用 EKS Auto Mode GPU 管理费用最高降低 60%
- 2026-07-11: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 已应用 Karpenter v1.14.0 版本（CapacityBuffers API 等）
- 2026-07-11: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — 已应用 CloudWatch Application Signals Service Events
- 2026-07-11: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已应用 ArgoCD v3.4.5 补丁版本
- 2026-07-11: 没有匹配的文档 — 应对 ingress-nginx 的弃用（2026 年 3 月），CNCF 博客（[source](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/)）
- 2026-07-11: 没有匹配的文档 — CNCF《Cloud Native AI 中的数据存储》白皮书已发布（[source](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/)）
- 2026-07-11: 没有匹配的文档 — Amazon EMR on EKS 现支持 Apache Spark 故障排除 agent（[source](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/)）
- 2026-07-11: 没有匹配的文档 — AWS Systems Manager hybrid/multicloud node 定价改革（取消 Advanced Instances Tier）（[source](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/))
