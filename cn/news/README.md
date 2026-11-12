# 新闻
> **最后更新**：2026年10月26日

本页面记录由 Kubernetes、Amazon EKS 和 CNCF 新闻促成的文档变更。GitHub Actions 每周一 KST 09:00 准备更新，并在通过质量门禁后创建 PR。变更经审核、合并和部署后会发布到网站。

周标签标识日志条目所属的周，可能与来源的发布日期不同。这些是历史记录；如需了解当前的支持、安全补丁和运行要求，请查阅链接的指南和官方来源。“没有匹配的文档”描述的是当时自动匹配的结果。

<!-- news-dashboard -->

<details class="news-log">
<summary>展开完整更新日志</summary>

## 更新日志

- 2026-W44: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 更新了 Istio 1.31.3/1.30.7/1.29.10 安全补丁版本（ISTIO-SECURITY-2026-008，CVE-2026-111943：不再信任已遭入侵的 eMudhra 中间 CA 证书；1.29.10 是一个特殊的 EOL 后版本）([来源](https://istio.io/latest/news/security/istio-security-2026-008/))
- 2026-W44: [networking/cilium/README.md](../networking/cilium/README.md) — 更新了 Cilium 1.20.4/1.19.10/1.18.16 带外安全补丁版本（CVE-2026-111943；Go 1.26.10 不再信任已遭入侵的 eMudhra 中间 CA 证书）([来源](https://github.com/cilium/cilium/releases/tag/v1.20.4))
- 2026-W44: [gitops/argocd/README.md](../gitops/argocd/README.md) — 更新了 Argo CD v3.5.6/v3.4.12/v3.3.17 错误修复补丁版本，以及包含安全修复的 v3.3.18，该修复移除了对已遭入侵的 eMudhra CA 证书的信任 ([来源](https://github.com/argoproj/argo-cd/releases/tag/v3.3.18))
- 2026-W44: [gitops/argocd/README.md](../gitops/argocd/README.md) — 更新了 Argo CD v3.6.0-rc4 候选发布版 ([来源](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc4))
- 2026-W44: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 更新了 Karpenter v1.15.1 补丁版本和 v1.14.2/v1.14.3/v1.9.3 LTS 补丁版本（错误修复；所有版本线均升级到 Go 1.26.10，该版本不再信任已遭入侵的 eMudhra 中间 CA 证书）([来源](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.15.1))
- 2026-W44: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 更新了 CNCF 博客中关于在 OpenTelemetry Collector 中筛选和减少 AI 代理遥测数据的指南 ([来源](https://www.cncf.io/blog/2026/10/22/filtering-and-reducing-ai-agent-telemetry-with-the-opentelemetry-collector/))
- 2026-W44: 没有匹配的文档 — Amazon EMR on EKS 将 EMR 费用（每 vCPU 小时和每 GB 小时）降低 30%；底层 EKS 费用不变 ([来源](https://aws.amazon.com/about-aws/whats-new/2026/10/emr-eks-reduces-emr-charge-30-percent/))
- 2026-W44: 没有匹配的文档 — AI 工作负载如何重塑 Kubernetes 自动扩缩容，CNCF 博客 ([来源](https://www.cncf.io/blog/2026/10/19/how-ai-workloads-are-reshaping-kubernetes-autoscaling/))
- 2026-W43: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 发布了 Istio 1.31.2/1.30.6/1.29.9 补丁版本（包括 ISTIO-SECURITY-2026-007 安全补丁；此前审核时已在文档中反映）([来源](https://istio.io/news/releases/1.31.x/announcing-1.31.2/))
- 2026-W43: [networking/cilium/README.md](../networking/cilium/README.md) — 更新了 Cilium 1.20.3/1.19.9/1.18.15 补丁版本（错误修复，包括 conntrack GC 和对带有 `nodeSelector` 的 CNP 的处理）([来源](https://github.com/cilium/cilium/releases/tag/v1.20.3))
- 2026-W43: [gitops/argocd/README.md](../gitops/argocd/README.md) — 更新了 Argo CD v3.5.5/v3.4.11/v3.3.16 错误修复补丁版本 ([来源](https://github.com/argoproj/argo-cd/releases/tag/v3.5.5))
- 2026-W43: [gitops/argocd/README.md](../gitops/argocd/README.md) — 更新了 Argo CD v3.6.0-rc3 候选发布版 ([来源](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc3))
- 2026-W43: [security/14-waf-edge-api-security.md](../security/14-waf-edge-api-security.md) — 更新了 CloudFront VPC origins 支持双栈（IPv6）的公告 ([来源](https://aws.amazon.com/about-aws/whats-new/2026/10/cloudfront-vpc-origin-dualstack/))
- 2026-W43: [blockchain/01-fundamentals.md](../blockchain/01-fundamentals.md) — 更新了 AWS 上的 Blockchain Snapshots 上线信息（用于启动 Ethereum/Solana 节点的免费预同步快照）([来源](https://aws.amazon.com/about-aws/whats-new/2026/10/blockchain-snapshots-node-bootstrapping/))
- 2026-W43: [security/01-kyverno-policy-management.md](../security/01-kyverno-policy-management.md) — 更新了 CNCF 博客对 Nirmata Runtime for Kyverno 的介绍（通过 eBPF/LSM 在内核层执行运行时策略）([来源](https://www.cncf.io/blog/2026/10/15/extending-kubernetes-policy-enforcement-to-runtime-security-for-ai-workloads/))
- 2026-W43: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 更新了 CNCF 博客中的提议：将 Software Carbon Intensity (SCI) 作为 OpenTelemetry 语义约定 ([来源](https://www.cncf.io/blog/2026/10/15/carbon-as-a-first-class-signal-bringing-software-carbon-intensity-to-opentelemetry/))
- 2026-W43: 没有匹配的文档 — 使用 Headlamp 跟踪 Kueue 管理的 Jobs 的准入状态，Kubernetes 博客 ([来源](https://kubernetes.io/blog/2026/10/14/tracing-kueue-admission-with-headlamp/))
- 2026-W42: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 更新了 Karpenter v1.15.0 版本（节点修复作为自愿中断，支持重启；KubeletConfiguration 中支持 CEL；扩展 DRA 支持等）
- 2026-W42: [gitops/argocd/README.md](../gitops/argocd/README.md) — 更新了 Argo CD v3.5.4/v3.4.10/v3.3.15 安全补丁版本（四项 CRITICAL 问题，包括 repo-server 命令执行漏洞 CVE-2026-77459）
- 2026-W42: [kernel/01-container-primitives.md](../kernel/01-container-primitives.md) — 更新了 Kubernetes 博客中关于 cgroup v1 弃用状态的信息（从 v1.35 起，`failCgroupV1` 默认为 `true`）
- 2026-W42: 没有匹配的文档 — 使用 NVMe SSD 支持的节点交换空间扩展 Kubernetes 工作负载（在 v1.34 中正式发布），Kubernetes 博客 ([来源](https://kubernetes.io/blog/2026/10/05/scaling-kubernetes-workloads-with-node-swap/))
- 2026-W42: 没有匹配的文档 — Meshery 成为 CNCF 孵化项目 ([来源](https://www.cncf.io/blog/2026/10/07/meshery-becomes-a-cncf-incubating-project/))
- 2026-W42: 没有匹配的文档 — AWS Batch 现已支持 Amazon EKS access entry 身份验证 ([来源](https://aws.amazon.com/about-aws/whats-new/2026/10/aws-batch-access-entries/))
- 2026-W41: [eks/08-eks-upgrades.md](../eks/08-eks-upgrades.md) — 更新了 Amazon EKS 和 EKS Distro 对 Kubernetes 1.37 的支持（Metrics API 正式发布、DRA 设备污点正式发布、HPA 缩放到零进入 Beta）
- 2026-W41: [gitops/argocd/README.md](../gitops/argocd/README.md) — 更新了 Argo CD 4.0 愿景规划启动和 ArgoCon North America 2026 新闻
- 2026-W41: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 更新了 Atlassian 基于 OTel、Kafka 和 Flink 重建事件检测系统的内容（CNCF 博客）
- 2026-W41: 没有匹配的文档 — Amazon ECS 增加了对 Amazon VPC Lattice 的支持，可用于蓝绿、线性和金丝雀发布 ([来源](https://aws.amazon.com/about-aws/whats-new/2026/10/amazon-ecs-vpc-lattice-blue-green-deployments))
- 2026-W41: 没有匹配的文档 — Amazon Managed Grafana 现已支持创建 Grafana 13.2 工作区 ([来源](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-managed-grafana-now-supports-creating-grafana-13-2-workspaces))
- 2026-W41: 没有匹配的文档 — Grafana Tempo 3.1 发布（新增 Kafka 功能、TraceQL 指标更新、跟踪数据隐私处理等）([来源](https://grafana.com/blog/tempo-3-1-release-all-the-latest-features))
- 2026-W41: 没有匹配的文档 — 防护措施，而非关卡：重新思考平台团队中的策略，CNCF 博客 ([来源](https://www.cncf.io/blog/2026/10/01/guardrails-not-gates-rethinking-policy-in-platform-teams/))
- 2026-W40: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 更新了 Kubernetes v1.37.1/v1.36.5/v1.35.9/v1.34.12 补丁版本，以及 v1.37 PVC `Unused` 条件（Beta）的博客文章
- 2026-W40: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 更新了 Istio 1.31.1/1.30.5/1.29.8 补丁版本（包括 BackendTLSPolicy 故障开放安全修复 GHSA-qm8v-g4f9-qhjx）
- 2026-W40: [eks/04-eks-storage-part1.md](../eks/04-eks-storage-part1.md) — 更新了 EFS CSI 驱动程序挂载选项注入漏洞 CVE-2026-6437（已在 v3.0.1 中修复）
- 2026-W40: [ai-ml/08-llm-gateway.md](../ai-ml/08-llm-gateway.md) — 更新了 Amazon SageMaker HyperPod Inference Gateway 上线信息（EKS 托管插件，支持 GPU 感知路由）
- 2026-W40: 没有匹配的文档 — Amazon EMR on EKS 现已支持 IPv6 Amazon EKS 集群 ([来源](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-emr-eks-ipv6-support))
- 2026-W40: 没有匹配的文档 — 使用 Spark Connect 在 Amazon EMR on EKS 上运行交互式工作负载 ([来源](https://aws.amazon.com/about-aws/whats-new/2026/09/emr-eks-spark-connect-interactive/))
- 2026-W40: 没有匹配的文档 — Amazon CloudWatch Omni 正式发布（AI 优先的可观测性体验，支持 OpenTelemetry 互操作）([来源](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-cloudwatch-omni-ai/))
- 2026-W39: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 更新了 Kubernetes v1.37 三项功能的深入介绍（Memory QoS Beta、Pod 级资源管理器 Beta、emptyDir 权限和绑定挂载选项）
- 2026-W39: [networking/cilium/README.md](../networking/cilium/README.md) — 更新了 Cilium 1.20.2/1.19.8/1.18.14 补丁版本，以及 CNCF 博客对 1.20 功能的回顾
- 2026-W39: [gitops/argocd/README.md](../gitops/argocd/README.md) — 更新了 Argo CD v3.5.3/v3.4.9 补丁版本和 v3.6.0-rc1
- 2026-W39: 没有匹配的文档 — Kubernetes CSI Changed Block Tracking (CBT) API 升级为 Beta，并介绍其与 Alpha 版本的差异，Kubernetes 博客 ([来源](https://kubernetes.io/blog/2026/09/14/csi-changed-block-tracking-beta/))
- 2026-W39: 没有匹配的文档 — AWS Resilience Hub 新增三项功能（包括在命名空间内根据 EKS 标签发现服务资源）([来源](https://aws.amazon.com/about-aws/whats-new/2026/09/resilience-hub-eks-dependency-policy/))
- 2026-W38: [core/08-scheduling-preemption-eviction.md](../core/08-scheduling-preemption-eviction.md) — 更新了 Kubernetes v1.37 调度器对原地调整 Pod 大小的抢占支持（Alpha），以及工作负载感知调度的进展（Workload/PodGroup Beta、CompositePodGroup API）
- 2026-W38: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 更新了 Kubernetes v1.37 Node 生命周期条件（用于排空、维护和优雅关机的五种已知条件）
- 2026-W38: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — 更新了 Kubernetes v1.37 组件指标的 Prometheus 原生直方图（Beta，默认启用）
- 2026-W38: [networking/cilium/README.md](../networking/cilium/README.md) — 更新了 Cilium 1.21.0-pre.2 预发布版（Gateway API 会话持久性、AWS 托管前缀列表、默认启用 BPF 伪装）
- 2026-W38: 没有匹配的文档 — Karmada 成为 CNCF 毕业项目 ([来源](https://www.cncf.io/announcements/2026/09/07/cloud-native-computing-foundation-announces-karmada-graduation/))
- 2026-W38: 没有匹配的文档 — Kubernetes 灾难恢复：来自三个可复现故障场景的指导，CNCF 博客 ([来源](https://www.cncf.io/blog/2026/09/10/kubernetes-disaster-recovery-guidance-from-three-reproducible-failure-scenarios/))
- 2026-W38: 没有匹配的文档 — AWS GovCloud (US) 现已提供 AWS Private CA EKS 插件和 Connector for AD ([来源](https://aws.amazon.com/about-aws/whats-new/2026/09/private-ca-eks-addon-ad-govcloud/))
- 2026-W36: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 更新了 Kubernetes v1.37“Garhwal”版本（Pod 证书/ClusterTrustBundles 正式发布、Metrics API 正式发布、弃用 kube-dns 和 IPVS 模式等）
- 2026-W36: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 更新了 Istio 1.30.4/1.29.7 安全补丁版本（ISTIO-SECURITY-2026-006，13 个 Envoy CVE）
- 2026-W36: [gitops/argocd/README.md](../gitops/argocd/README.md) — 更新了 ArgoCD v3.5.2/v3.4.8 补丁版本
- 2026-W36: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — 更新了 Linkerd edge-26.8.4（TLSRoute API 版本协商等）
- 2026-W36: 没有匹配的文档 — Amazon EKS 现已支持每个集群最多配置 10 个外部 OIDC 身份提供商 ([来源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-multiple-oidc-providers))
- 2026-W36: 没有匹配的文档 — 在峰值到来前扩容：Kubernetes 上 GPU 工作负载的预测性自动扩缩容，CNCF 博客 ([来源](https://www.cncf.io/blog/2026/08/28/scale-before-the-spike-predictive-autoscaling-for-gpu-workloads-on-kubernetes/))
- 2026-W36: 没有匹配的文档 — 在 Kubernetes 上构建 AI 工厂，CNCF 博客 ([来源](https://www.cncf.io/blog/2026/08/27/building-an-ai-factory-on-kubernetes/))
- 2026-W35: [gitops/argocd/README.md](../gitops/argocd/README.md) — 更新了 Amazon EKS 托管 Argo CD 功能对自定义配置的支持（通过 `argocd-cm` ConfigMap）
- 2026-W35: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 更新了 Kubernetes v1.36.4/v1.35.8/v1.34.11 补丁版本和 v1.37.0-rc.1
- 2026-W35: [networking/cilium/README.md](../networking/cilium/README.md) — 更新了 Cilium 1.20.1/1.19.7/1.18.13 补丁版本
- 2026-W35: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 更新了 Karpenter v1.14.1 补丁版本
- 2026-W35: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 更新了 Istio 1.31.0-rc.0 版本（1.31 进入 RC 阶段）
- 2026-W35: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 更新了 CNCF 博客中关于将慢 SQL 查询提炼为基于 OTel Span 的指标的指南
- 2026-W35: 没有匹配的文档 — Amazon EKS 现已支持通过自动化生命周期管理轮换证书颁发机构 (CA) ([来源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-certificate-authority-ca-rotation-automated-lifecycle-management))
- 2026-W35: 没有匹配的文档 — Kubeflow 在 CNCF 中毕业 ([来源](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/))
- 2026-W34: [gitops/argocd/README.md](../gitops/argocd/README.md) — 更新了 ArgoCD v3.5.0 GA 版本，以及 v3.5.1/v3.4.7/v3.3.14 补丁版本
- 2026-W34: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 更新了 Istio 1.31.0-beta.1 版本（1.31 进入 Beta 阶段）
- 2026-W34: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — 更新了 Linkerd edge-26.8.2（支持 Gateway API 1.5.1，已测试的最高 k8s 版本为 1.36）
- 2026-W34: 没有匹配的文档 — Amazon EKS 现已支持高级 Kubernetes 控制平面配置参数（调优 scheduler/controller manager/API server）([来源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-control-plane-configuration-parameters))
- 2026-W34: 没有匹配的文档 — Cloud Native Buildpacks 成为 CNCF 毕业项目 ([来源](https://www.cncf.io/announcements/2026/08/11/cncf-announces-graduation-of-cloud-native-buildpacks-advancing-the-standard-for-container-builds/))
- 2026-W34: 没有匹配的文档 — KubeCon + CloudNativeCon North America 2026 日程公布，新增 AI Inference + Agentic 主题分会场 ([来源](https://www.cncf.io/announcements/2026/08/10/cncf-reveals-kubecon-cloudnativecon-north-america-2026-schedule-adds-new-ai-inference-agentic-track/))
- 2026-W34: 没有匹配的文档 — 如何将 Kubernetes YAML 美化输出为 KYAML，Kubernetes 博客 ([来源](https://kubernetes.io/blog/2026/08/11/how-to-pretty-print-kubernetes-yaml-as-kyaml/))
- 2026-W33: [networking/04-gateway-api.md](../networking/04-gateway-api.md) — 更新了 Gateway API v1.6（TCPRoute/UDPRoute 升级为 Standard v1，各渠道特定的弃用 API 服务变更）
- 2026-W33: [gitops/argocd/README.md](../gitops/argocd/README.md) — 更新了 ArgoCD v3.5.0 GA 版本（迁移到 Helm 4、源完整性验证 Alpha、ApplicationSet 改进）
- 2026-W33: [networking/cilium/README.md](../networking/cilium/README.md) — 更新了 Cilium 1.20.0 GA 版本（Gateway API v1.6.1、KCNP、多池 IPAM 迁移）和 1.21.0-pre.0
- 2026-W33: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 更新了 Kubernetes v1.37 预览、Docs Freeze 生效以及 v1.38.0-alpha.0 标签
- 2026-W33: 没有匹配的文档 — Amazon ECR 现已支持 Docker push 使用最大 200 GB 的镜像层 ([来源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-ecr-image-layers/))
- 2026-W33: 没有匹配的文档 — K8gb 成为 CNCF 孵化项目 ([来源](https://www.cncf.io/announcements/2026/08/05/k8gb-becomes-a-cncf-incubating-project/))
- 2026-W33: 没有匹配的文档 — OpenCost 1.121.0 新增 Kubernetes 推理成本跟踪功能 ([来源](https://www.cncf.io/blog/2026/08/05/opencost-1-121-0-first-of-a-kind-kubernetes-inference-cost-tracking/))
- 2026-W33: 没有匹配的文档 — Kubernetes DRA 会取代 HAMi 吗？，CNCF 博客 ([来源](https://www.cncf.io/blog/2026/08/07/does-kubernetes-dra-replace-hami/))
- 2026-W31: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 更新了 Kubernetes v1.36.3/v1.35.7/v1.34.10 补丁版本，以及 v1.37 Code Freeze 生效信息
- 2026-W31: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — 更新了 EKS Auto Mode 节点池对 EFA 和 EC2 placement group 的支持
- 2026-W31: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 更新了 Karpenter 节点池对 EFA 和 EC2 placement group 的支持
- 2026-W31: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — 更新了 AMP 限额上调信息（15 亿个活跃序列、每个工作区 20 万条规则）
- 2026-W31: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 更新了 OpenTelemetry 从 CNCF 毕业的信息
- 2026-W31: [networking/calico/README.md](../networking/calico/README.md) — 更新了 Tigera 推出适用于 Kubernetes 上虚拟机的 Calico（基于 eBPF 的虚拟机与容器统一网络）
- 2026-W31: [networking/cilium/README.md](../networking/cilium/README.md) — 更新了 Cilium 1.20.0-rc.1 候选发布版
- 2026-W31: 没有匹配的文档 — Confidential Containers 成为 CNCF 孵化项目 ([来源](https://www.cncf.io/blog/2026/07/22/confidential-containers-becomes-a-cncf-incubating-project/))
- 2026-W31: 没有匹配的文档 — Kubernetes CSI 驱动程序中的两项路径遍历 CVE（CVE-2026-3864 NFS / CVE-2026-3865 SMB；已在 csi-driver-nfs v4.13.1、csi-driver-smb v1.20.1 中修复）([来源](https://www.sentinelone.com/blog/mount-here-read-there-twin-path-traversal-cves-in-kubernetes-storage/))
- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — 更新了 Cilium 1.19.6/1.18.12/1.17.18 补丁版本和 CVE-2026-56743（ipBlock NetworkPolicy 问题）
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 更新了 Istio 1.30.3/1.29.6 补丁版本
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — 更新了 Linkerd edge-26.7.1（禁止向未定义的 Service 端口发送请求，属于破坏性变更）
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — 更新了 EKS Auto Mode 对 ARC 可用区迁移/自动迁移的支持
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — 更新了 EKS Auto Mode 对 ARC 可用区迁移的支持
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 更新了适用于较旧版本线的 Karpenter 补丁版本（v1.3.8–v1.11.3）
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 更新了 Kubernetes v1.37.0-beta.0 和 v1.37 发布计划
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — 更新了 ArgoCon Japan 2026 和即将举行的 Argo CD 3.5 路线图专题会议
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — 更新了 Kubernetes 博客中关于自定义指标导出器的指南
- 2026-W30: 没有匹配的文档 — HAMi 成为 CNCF 孵化项目 ([来源](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/))
- 2026-W30: 没有匹配的文档 — 在 Kubernetes 中使用 vLLM 运行自托管 LLM，CNCF 博客 ([来源](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/))
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — 更新了 ACM 对 ACME 协议的支持（现在可以从 cert-manager 使用 ACM 公有证书）
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 更新了适用于 AI 代理的 NGINX + OpenTelemetry 网络边界可观测性模式
- 2026-W29: 没有匹配的文档 — 面向 AI 原生工作负载演进平台工程，CNCF 博客 ([来源](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/))
- 2026-07-11: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 更新了 etcd v3.7.0 版本（RangeStream 等）
- 2026-07-11: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — 更新了 EKS Auto Mode GPU 管理费最高降低 60% 的信息
- 2026-07-11: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 更新了 Karpenter v1.14.0 版本（CapacityBuffers API 等）
- 2026-07-11: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — 更新了 CloudWatch Application Signals Service Events
- 2026-07-11: [gitops/argocd/README.md](../gitops/argocd/README.md) — 更新了 ArgoCD v3.4.5 补丁版本
- 2026-07-11: 没有匹配的文档 — 应对 ingress-nginx 退役（2026年3月），CNCF 博客 ([来源](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/))
- 2026-07-11: 没有匹配的文档 — CNCF《云原生 AI 中的数据存储》白皮书发布 ([来源](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/))
- 2026-07-11: 没有匹配的文档 — Amazon EMR on EKS 现已支持 Apache Spark 故障排查代理 ([来源](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/))
- 2026-07-11: 没有匹配的文档 — AWS Systems Manager 混合/多云节点定价全面调整（取消 Advanced Instances Tier）([来源](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/))

</details>
