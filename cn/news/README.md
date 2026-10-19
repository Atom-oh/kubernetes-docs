# 新闻
> **最后更新**：2026年10月19日

本页面记录因 Kubernetes、Amazon EKS 和 CNCF 新闻而进行的文档变更。GitHub Actions 每周一 09:00 KST 准备更新，并在通过质量门禁后创建 PR。变更经审核、合并和部署后才会发布到网站。

周标签标识日志条目所属的周，可能与来源的发布日期不同。这些是历史记录；如需了解当前的支持情况、安全补丁和运行要求，请查阅链接的指南和官方来源。“无匹配文档”指当时的自动匹配结果。

<!-- news-dashboard -->

<details class="news-log">
<summary>展开完整更新日志</summary>

## 更新日志

- 2026-W43: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 发布了 Istio 1.31.2/1.30.6/1.29.9 补丁版本（包括 ISTIO-SECURITY-2026-007 安全补丁；该补丁已在此前审核时反映到文档中）([来源](https://istio.io/news/releases/1.31.x/announcing-1.31.2/))
- 2026-W43: [networking/cilium/README.md](../networking/cilium/README.md) — 已更新 Cilium 1.20.3/1.19.9/1.18.15 补丁版本（修复了包括 conntrack GC 和处理带有 `nodeSelector` 的 CNP 在内的问题）([来源](https://github.com/cilium/cilium/releases/tag/v1.20.3))
- 2026-W43: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已更新 Argo CD v3.5.5/v3.4.11/v3.3.16 错误修复补丁版本 ([来源](https://github.com/argoproj/argo-cd/releases/tag/v3.5.5))
- 2026-W43: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已更新 Argo CD v3.6.0-rc3 候选版本 ([来源](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc3))
- 2026-W43: [security/14-waf-edge-api-security.md](../security/14-waf-edge-api-security.md) — 已更新 CloudFront VPC origins 支持双栈（IPv6）的公告 ([来源](https://aws.amazon.com/about-aws/whats-new/2026/10/cloudfront-vpc-origin-dualstack/))
- 2026-W43: [blockchain/01-fundamentals.md](../blockchain/01-fundamentals.md) — 已更新 AWS Blockchain Snapshots 上线的消息（为 Ethereum/Solana 节点引导提供免费的预同步快照）([来源](https://aws.amazon.com/about-aws/whats-new/2026/10/blockchain-snapshots-node-bootstrapping/))
- 2026-W43: [security/01-kyverno-policy-management.md](../security/01-kyverno-policy-management.md) — 已更新 CNCF 博客对 Nirmata Runtime for Kyverno 的介绍（通过 eBPF/LSM 在内核级强制执行运行时策略）([来源](https://www.cncf.io/blog/2026/10/15/extending-kubernetes-policy-enforcement-to-runtime-security-for-ai-workloads/))
- 2026-W43: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 已更新 CNCF 博客提出的建议：将软件碳强度（SCI）作为 OpenTelemetry 语义约定 ([来源](https://www.cncf.io/blog/2026/10/15/carbon-as-a-first-class-signal-bringing-software-carbon-intensity-to-opentelemetry/))
- 2026-W43: 无匹配文档 — 使用 Headlamp 跟踪 Kueue 管理的 Jobs 的准入状态，Kubernetes 博客 ([来源](https://kubernetes.io/blog/2026/10/14/tracing-kueue-admission-with-headlamp/))
- 2026-W42: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 已更新 Karpenter v1.15.0 版本（支持重启的节点修复作为自愿性中断、KubeletConfiguration 中的 CEL、更广泛的 DRA 支持等）
- 2026-W42: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已更新 Argo CD v3.5.4/v3.4.10/v3.3.15 安全补丁版本（修复了四个 CRITICAL 问题，包括 repo-server 命令执行漏洞 CVE-2026-77459）
- 2026-W42: [kernel/01-container-primitives.md](../kernel/01-container-primitives.md) — 已更新 Kubernetes 博客中有关 cgroup v1 弃用状态的说明（从 v1.35 起，`failCgroupV1` 默认值为 `true`）
- 2026-W42: 无匹配文档 — 使用 NVMe SSD 支持的节点交换空间扩展 Kubernetes 工作负载（在 v1.34 中正式发布），Kubernetes 博客 ([来源](https://kubernetes.io/blog/2026/10/05/scaling-kubernetes-workloads-with-node-swap/))
- 2026-W42: 无匹配文档 — Meshery 成为 CNCF 孵化项目 ([来源](https://www.cncf.io/blog/2026/10/07/meshery-becomes-a-cncf-incubating-project/))
- 2026-W42: 无匹配文档 — AWS Batch 现已支持 Amazon EKS 访问条目身份验证 ([来源](https://aws.amazon.com/about-aws/whats-new/2026/10/aws-batch-access-entries/))
- 2026-W41: [eks/08-eks-upgrades.md](../eks/08-eks-upgrades.md) — 已更新 Amazon EKS 和 EKS Distro 对 Kubernetes 1.37 的支持（Metrics API 正式发布、DRA 设备污点正式发布、HPA 缩容至零进入 Beta）
- 2026-W41: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已更新 Argo CD 4.0 愿景规划启动和 ArgoCon North America 2026 相关新闻
- 2026-W41: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 已更新 Atlassian 基于 OTel、Kafka 和 Flink 重建事件检测系统的案例（CNCF 博客）
- 2026-W41: 无匹配文档 — Amazon ECS 为蓝绿、线性和金丝雀部署新增 Amazon VPC Lattice 支持 ([来源](https://aws.amazon.com/about-aws/whats-new/2026/10/amazon-ecs-vpc-lattice-blue-green-deployments))
- 2026-W41: 无匹配文档 — Amazon Managed Grafana 现已支持创建 Grafana 13.2 工作区 ([来源](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-managed-grafana-now-supports-creating-grafana-13-2-workspaces))
- 2026-W41: 无匹配文档 — Grafana Tempo 3.1 发布（新增 Kafka 功能、TraceQL 指标更新、轨迹数据脱敏等）([来源](https://grafana.com/blog/tempo-3-1-release-all-the-latest-features))
- 2026-W41: 无匹配文档 — 防护措施，而非关卡：重新思考平台团队中的策略，CNCF 博客 ([来源](https://www.cncf.io/blog/2026/10/01/guardrails-not-gates-rethinking-policy-in-platform-teams/))
- 2026-W40: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已更新 Kubernetes v1.37.1/v1.36.5/v1.35.9/v1.34.12 补丁版本，以及 v1.37 PVC `Unused` 状态（Beta）的博客文章
- 2026-W40: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 已更新 Istio 1.31.1/1.30.5/1.29.8 补丁版本（包括 BackendTLSPolicy 安全修复，解决故障时默认放行的问题 GHSA-qm8v-g4f9-qhjx）
- 2026-W40: [eks/04-eks-storage-part1.md](../eks/04-eks-storage-part1.md) — 已更新 EFS CSI 驱动程序挂载选项注入漏洞 CVE-2026-6437（已在 v3.0.1 中修复）
- 2026-W40: [ai-ml/08-llm-gateway.md](../ai-ml/08-llm-gateway.md) — 已更新 Amazon SageMaker HyperPod Inference Gateway 上线的消息（EKS 托管式附加组件、支持感知 GPU 的路由）
- 2026-W40: 无匹配文档 — Amazon EMR on EKS 现已支持 IPv6 Amazon EKS 集群 ([来源](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-emr-eks-ipv6-support))
- 2026-W40: 无匹配文档 — 使用 Spark Connect 在 Amazon EMR on EKS 上运行交互式工作负载 ([来源](https://aws.amazon.com/about-aws/whats-new/2026/09/emr-eks-spark-connect-interactive/))
- 2026-W40: 无匹配文档 — Amazon CloudWatch Omni 正式发布（AI 优先的可观测性体验、OpenTelemetry 互操作性）([来源](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-cloudwatch-omni-ai/))
- 2026-W39: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已更新 Kubernetes v1.37 三项功能的深入介绍（Memory QoS Beta、Pod 级资源管理器 Beta、emptyDir 权限和绑定挂载选项）
- 2026-W39: [networking/cilium/README.md](../networking/cilium/README.md) — 已更新 Cilium 1.20.2/1.19.8/1.18.14 补丁版本，以及 CNCF 博客对 1.20 功能的回顾
- 2026-W39: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已更新 Argo CD v3.5.3/v3.4.9 补丁版本和 v3.6.0-rc1
- 2026-W39: 无匹配文档 — Kubernetes CSI Changed Block Tracking（CBT）API 升级至 Beta，并介绍其与 Alpha 的差异，Kubernetes 博客 ([来源](https://kubernetes.io/blog/2026/09/14/csi-changed-block-tracking-beta/))
- 2026-W39: 无匹配文档 — AWS Resilience Hub 新增三项功能（包括在命名空间内根据 EKS 标签发现服务资源）([来源](https://aws.amazon.com/about-aws/whats-new/2026/09/resilience-hub-eks-dependency-policy/))
- 2026-W38: [core/08-scheduling-preemption-eviction.md](../core/08-scheduling-preemption-eviction.md) — 已更新 Kubernetes v1.37 中针对 Pod 原地调整大小的调度器抢占（Alpha）和工作负载感知调度的进展（Workload/PodGroup Beta、CompositePodGroup API）
- 2026-W38: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已更新 Kubernetes v1.37 Node 生命周期状态（用于排空、维护和优雅关机的五种已知状态）
- 2026-W38: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — 已更新 Kubernetes v1.37 组件指标的 Prometheus 原生直方图（Beta，默认启用）
- 2026-W38: [networking/cilium/README.md](../networking/cilium/README.md) — 已更新 Cilium 1.21.0-pre.2 预发布版本（Gateway API 会话持久性、AWS 托管前缀列表、默认启用 BPF 伪装）
- 2026-W38: 无匹配文档 — Karmada 成为 CNCF 毕业项目 ([来源](https://www.cncf.io/announcements/2026/09/07/cloud-native-computing-foundation-announces-karmada-graduation/))
- 2026-W38: 无匹配文档 — Kubernetes 灾难恢复：来自三个可复现故障场景的指导，CNCF 博客 ([来源](https://www.cncf.io/blog/2026/09/10/kubernetes-disaster-recovery-guidance-from-three-reproducible-failure-scenarios/))
- 2026-W38: 无匹配文档 — AWS Private CA EKS 附加组件和 Connector for AD 现已在 AWS GovCloud（美国）推出 ([来源](https://aws.amazon.com/about-aws/whats-new/2026/09/private-ca-eks-addon-ad-govcloud/))
- 2026-W36: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已更新 Kubernetes v1.37 “Garhwal” 版本（Pod 证书/ClusterTrustBundles 达到 Stable、Metrics API 正式发布、弃用 kube-dns 和 IPVS 模式等）
- 2026-W36: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 已更新 Istio 1.30.4/1.29.7 安全补丁版本（ISTIO-SECURITY-2026-006，涉及 13 个 Envoy CVE）
- 2026-W36: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已更新 ArgoCD v3.5.2/v3.4.8 补丁版本
- 2026-W36: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — 已更新 Linkerd edge-26.8.4（TLSRoute API 版本协商等）
- 2026-W36: 无匹配文档 — Amazon EKS 现已支持每个集群最多配置 10 个外部 OIDC 身份提供商 ([来源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-multiple-oidc-providers))
- 2026-W36: 无匹配文档 — 提前扩容，赶在峰值之前：在 Kubernetes 上为 GPU 工作负载进行预测性自动扩缩，CNCF 博客 ([来源](https://www.cncf.io/blog/2026/08/28/scale-before-the-spike-predictive-autoscaling-for-gpu-workloads-on-kubernetes/))
- 2026-W36: 无匹配文档 — 在 Kubernetes 上构建 AI 工厂，CNCF 博客 ([来源](https://www.cncf.io/blog/2026/08/27/building-an-ai-factory-on-kubernetes/))
- 2026-W35: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已更新 Amazon EKS 托管式 Argo CD 功能对自定义配置的支持（通过 `argocd-cm` ConfigMap）
- 2026-W35: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已更新 Kubernetes v1.36.4/v1.35.8/v1.34.11 补丁版本和 v1.37.0-rc.1
- 2026-W35: [networking/cilium/README.md](../networking/cilium/README.md) — 已更新 Cilium 1.20.1/1.19.7/1.18.13 补丁版本
- 2026-W35: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 已更新 Karpenter v1.14.1 补丁版本
- 2026-W35: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 已更新 Istio 1.31.0-rc.0 版本（1.31 进入 RC 阶段）
- 2026-W35: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 已更新 CNCF 博客中关于将慢 SQL 查询提炼为基于 OTel Span 的指标的指南
- 2026-W35: 无匹配文档 — Amazon EKS 现已支持通过自动化生命周期管理轮换证书颁发机构（CA）([来源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-certificate-authority-ca-rotation-automated-lifecycle-management))
- 2026-W35: 无匹配文档 — Kubeflow 在 CNCF 内部毕业 ([来源](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/))
- 2026-W34: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已更新 ArgoCD v3.5.0 正式发布，以及 v3.5.1/v3.4.7/v3.3.14 补丁版本
- 2026-W34: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 已更新 Istio 1.31.0-beta.1 版本（1.31 进入 Beta 阶段）
- 2026-W34: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — 已更新 Linkerd edge-26.8.2（支持 Gateway API 1.5.1，测试的最高 k8s 版本为 1.36）
- 2026-W34: 无匹配文档 — Amazon EKS 现已支持高级 Kubernetes 控制平面配置参数（调度器/controller manager/API server 调优）([来源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-control-plane-configuration-parameters))
- 2026-W34: 无匹配文档 — Cloud Native Buildpacks 成为 CNCF 毕业项目 ([来源](https://www.cncf.io/announcements/2026/08/11/cncf-announces-graduation-of-cloud-native-buildpacks-advancing-the-standard-for-container-builds/))
- 2026-W34: 无匹配文档 — KubeCon + CloudNativeCon North America 2026 日程公布，新增 AI Inference + Agentic 专题 ([来源](https://www.cncf.io/announcements/2026/08/10/cncf-reveals-kubecon-cloudnativecon-north-america-2026-schedule-adds-new-ai-inference-agentic-track/))
- 2026-W34: 无匹配文档 — 如何将 Kubernetes YAML 美化打印为 KYAML，Kubernetes 博客 ([来源](https://kubernetes.io/blog/2026/08/11/how-to-pretty-print-kubernetes-yaml-as-kyaml/))
- 2026-W33: [networking/04-gateway-api.md](../networking/04-gateway-api.md) — 已更新 Gateway API v1.6（TCPRoute/UDPRoute 升级至 Standard v1、特定通道中弃用 API 的提供方式变更）
- 2026-W33: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已更新 ArgoCD v3.5.0 正式发布（迁移至 Helm 4、Alpha 阶段的源完整性验证、ApplicationSet 改进）
- 2026-W33: [networking/cilium/README.md](../networking/cilium/README.md) — 已更新 Cilium 1.20.0 正式发布（Gateway API v1.6.1、KCNP、多池 IPAM 迁移）和 1.21.0-pre.0
- 2026-W33: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已更新 Kubernetes v1.37 前瞻、Docs Freeze 生效以及 v1.38.0-alpha.0 标签
- 2026-W33: 无匹配文档 — Amazon ECR 现已支持通过 Docker push 上传最大 200 GB 的镜像层 ([来源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-ecr-image-layers/))
- 2026-W33: 无匹配文档 — K8gb 成为 CNCF 孵化项目 ([来源](https://www.cncf.io/announcements/2026/08/05/k8gb-becomes-a-cncf-incubating-project/))
- 2026-W33: 无匹配文档 — OpenCost 1.121.0 新增 Kubernetes 推理成本跟踪功能 ([来源](https://www.cncf.io/blog/2026/08/05/opencost-1-121-0-first-of-a-kind-kubernetes-inference-cost-tracking/))
- 2026-W33: 无匹配文档 — Kubernetes DRA 会取代 HAMi 吗？，CNCF 博客 ([来源](https://www.cncf.io/blog/2026/08/07/does-kubernetes-dra-replace-hami/))
- 2026-W31: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已更新 Kubernetes v1.36.3/v1.35.7/v1.34.10 补丁版本，以及 v1.37 代码冻结生效
- 2026-W31: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — 已更新 EKS Auto Mode 节点池对 EFA 和 EC2 placement group 的支持
- 2026-W31: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 已更新 Karpenter 节点池对 EFA 和 EC2 placement group 的支持
- 2026-W31: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — 已更新 AMP 限额提高（15 亿个活跃时间序列、每个工作区 20 万条规则）
- 2026-W31: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 已更新 OpenTelemetry 从 CNCF 毕业的消息
- 2026-W31: [networking/calico/README.md](../networking/calico/README.md) — 已更新 Tigera 推出 Calico for VMs on Kubernetes 的消息（基于 eBPF 的 VM+容器统一网络）
- 2026-W31: [networking/cilium/README.md](../networking/cilium/README.md) — 已更新 Cilium 1.20.0-rc.1 候选版本
- 2026-W31: 无匹配文档 — Confidential Containers 成为 CNCF 孵化项目 ([来源](https://www.cncf.io/blog/2026/07/22/confidential-containers-becomes-a-cncf-incubating-project/))
- 2026-W31: 无匹配文档 — Kubernetes CSI 驱动程序中的两个路径遍历 CVE（CVE-2026-3864 NFS / CVE-2026-3865 SMB；已在 csi-driver-nfs v4.13.1、csi-driver-smb v1.20.1 中修复）([来源](https://www.sentinelone.com/blog/mount-here-read-there-twin-path-traversal-cves-in-kubernetes-storage/))
- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — 已更新 Cilium 1.19.6/1.18.12/1.17.18 补丁版本和 CVE-2026-56743（ipBlock NetworkPolicy 问题）
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 已更新 Istio 1.30.3/1.29.6 补丁版本
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — 已更新 Linkerd edge-26.7.1（禁止向未定义的 Service 端口发送请求，属于不兼容变更）
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — 已更新 EKS Auto Mode 对 ARC 可用区偏移/自动偏移的支持
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — 已更新 EKS Auto Mode 对 ARC 可用区偏移的支持
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 已更新适用于较旧版本线的 Karpenter 补丁版本（v1.3.8–v1.11.3）
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已更新 Kubernetes v1.37.0-beta.0 和 v1.37 发布计划
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已更新 ArgoCon Japan 2026 和即将举行的 Argo CD 3.5 路线图专题会议
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — 已更新 Kubernetes 博客中关于自定义指标导出器的指南
- 2026-W30: 无匹配文档 — HAMi 成为 CNCF 孵化项目 ([来源](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/))
- 2026-W30: 无匹配文档 — 在 Kubernetes 中使用 vLLM 运行自托管 LLM，CNCF 博客 ([来源](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/))
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — 已更新 ACM 对 ACME 协议的支持（现在可以从 cert-manager 使用 ACM 公有证书）
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 已更新面向 AI Agent 的 NGINX + OpenTelemetry 网络边界可观测性模式
- 2026-W29: 无匹配文档 — 面向 AI 原生工作负载演进平台工程，CNCF 博客 ([来源](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/))
- 2026年7月11日: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已更新 etcd v3.7.0 版本（RangeStream 等）
- 2026年7月11日: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — 已更新 EKS Auto Mode 的 GPU 管理费最高降低 60% 的消息
- 2026年7月11日: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 已更新 Karpenter v1.14.0 版本（CapacityBuffers API 等）
- 2026年7月11日: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — 已更新 CloudWatch Application Signals Service Events
- 2026年7月11日: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已更新 ArgoCD v3.4.5 补丁版本
- 2026年7月11日: 无匹配文档 — 了解 ingress-nginx 退役事宜（2026年3月），CNCF 博客 ([来源](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/))
- 2026年7月11日: 无匹配文档 — CNCF 发布《云原生 AI 中的数据存储》白皮书 ([来源](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/))
- 2026年7月11日: 无匹配文档 — Amazon EMR on EKS 现已支持 Apache Spark 故障排除 Agent ([来源](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/))
- 2026年7月11日: 无匹配文档 — AWS Systems Manager 混合云/多云节点定价全面调整（取消 Advanced Instances Tier）([来源](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/))

</details>
