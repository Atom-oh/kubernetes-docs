# 新闻
> **最后更新**：2026 年 10 月 12 日

本页面记录由 Kubernetes、Amazon EKS 和 CNCF 新闻推动的文档变更。GitHub Actions 会在每周一 KST 09:00 准备更新，并在质量门禁通过后创建 PR。变更经审核、合并和部署后会发布到站点。

周标签表示日志条目所在周，可能与源发布日期不同。这些是历史记录；有关当前支持情况、安全补丁和运行要求，请参阅链接的指南和官方来源。“无匹配文档”描述的是当时的自动匹配结果。

<!-- news-dashboard -->

<details class="news-log">
<summary>展开完整更新日志</summary>

## 更新日志

- 2026-W42: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 应用了 Karpenter v1.15.0 版本（节点修复作为支持重启的自愿中断、KubeletConfiguration 中的 CEL、更广泛的 DRA 支持等）
- 2026-W42: [gitops/argocd/README.md](../gitops/argocd/README.md) — 应用了 Argo CD v3.5.4/v3.4.10/v3.3.15 安全补丁版本（包括 repo-server 命令执行在内的四个 CRITICAL 问题，CVE-2026-77459）
- 2026-W42: [kernel/01-container-primitives.md](../kernel/01-container-primitives.md) — 应用了 Kubernetes 博客中关于 cgroup v1 弃用状态的更新（从 v1.35 起，`failCgroupV1` 默认值为 `true`）
- 2026-W42: 无匹配文档 — 使用 NVMe SSD 支持的节点交换空间扩展 Kubernetes 工作负载（v1.34 中 GA），Kubernetes 博客（[来源](https://kubernetes.io/blog/2026/10/05/scaling-kubernetes-workloads-with-node-swap/)）
- 2026-W42: 无匹配文档 — Meshery 成为 CNCF 孵化项目（[来源](https://www.cncf.io/blog/2026/10/07/meshery-becomes-a-cncf-incubating-project/)）
- 2026-W42: 无匹配文档 — AWS Batch 现支持 Amazon EKS 访问条目认证（[来源](https://aws.amazon.com/about-aws/whats-new/2026/10/aws-batch-access-entries/)）
- 2026-W41: [eks/08-eks-upgrades.md](../eks/08-eks-upgrades.md) — 应用了 Amazon EKS 和 EKS Distro 对 Kubernetes 1.37 的支持（Metrics API GA、DRA 设备污点 GA、HPA scale-to-zero beta）
- 2026-W41: [gitops/argocd/README.md](../gitops/argocd/README.md) — 应用了 Argo CD 4.0 愿景规划的启动以及 ArgoCon North America 2026 新闻
- 2026-W41: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 应用了 Atlassian 基于 OTel、Kafka 和 Flink 重建事件检测的内容（CNCF 博客）
- 2026-W41: 无匹配文档 — Amazon ECS 为蓝绿、线性和金丝雀部署新增 Amazon VPC Lattice 支持（[来源](https://aws.amazon.com/about-aws/whats-new/2026/10/amazon-ecs-vpc-lattice-blue-green-deployments))
- 2026-W41: 无匹配文档 — Amazon Managed Grafana 现支持创建 Grafana 13.2 工作区（[来源](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-managed-grafana-now-supports-creating-grafana-13-2-workspaces))
- 2026-W41: 无匹配文档 — Grafana Tempo 3.1 版本（新的 Kafka 功能、TraceQL 指标更新、追踪脱敏等）（[来源](https://grafana.com/blog/tempo-3-1-release-all-the-latest-features))
- 2026-W41: 无匹配文档 — 护栏而非关卡：重新思考平台团队中的策略，CNCF 博客（[来源](https://www.cncf.io/blog/2026/10/01/guardrails-not-gates-rethinking-policy-in-platform-teams/)）
- 2026-W40: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 应用了 Kubernetes v1.37.1/v1.36.5/v1.35.9/v1.34.12 补丁版本以及关于 v1.37 PVC `Unused` 条件（Beta）的博客文章
- 2026-W40: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 应用了 Istio 1.31.1/1.30.5/1.29.8 补丁版本（包括 BackendTLSPolicy fail-open 安全修复 GHSA-qm8v-g4f9-qhjx）
- 2026-W40: [eks/04-eks-storage-part1.md](../eks/04-eks-storage-part1.md) — 应用了 EFS CSI driver 挂载选项注入漏洞 CVE-2026-6437（已在 v3.0.1 修复）
- 2026-W40: [ai-ml/08-llm-gateway.md](../ai-ml/08-llm-gateway.md) — 应用了 Amazon SageMaker HyperPod Inference Gateway 发布（EKS 托管附加组件、GPU 感知路由）
- 2026-W40: 无匹配文档 — Amazon EMR on EKS 现支持 IPv6 Amazon EKS 集群（[来源](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-emr-eks-ipv6-support))
- 2026-W40: 无匹配文档 — 通过 Spark Connect 在 Amazon EMR on EKS 上运行交互式工作负载（[来源](https://aws.amazon.com/about-aws/whats-new/2026/09/emr-eks-spark-connect-interactive/))
- 2026-W40: 无匹配文档 — Amazon CloudWatch Omni 正式发布（AI 优先的可观测性体验、OpenTelemetry 互操作性）（[来源](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-cloudwatch-omni-ai/))
- 2026-W39: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 应用了三篇 Kubernetes v1.37 功能深度解析（Memory QoS Beta、Pod-Level Resource Managers Beta、emptyDir 权限和 bind mount 选项）
- 2026-W39: [networking/cilium/README.md](../networking/cilium/README.md) — 应用了 Cilium 1.20.2/1.19.8/1.18.14 补丁版本以及 CNCF 博客的 1.20 功能回顾
- 2026-W39: [gitops/argocd/README.md](../gitops/argocd/README.md) — 应用了 Argo CD v3.5.3/v3.4.9 补丁版本和 v3.6.0-rc1
- 2026-W39: 无匹配文档 — Kubernetes CSI Changed Block Tracking (CBT) API 升级至 Beta，与 Alpha 存在差异，Kubernetes 博客（[来源](https://kubernetes.io/blog/2026/09/14/csi-changed-block-tracking-beta/)）
- 2026-W39: 无匹配文档 — AWS Resilience Hub 新增三项功能（包括命名空间内基于 EKS 标签的服务资源发现）（[来源](https://aws.amazon.com/about-aws/whats-new/2026/09/resilience-hub-eks-dependency-policy/))
- 2026-W38: [core/08-scheduling-preemption-eviction.md](../core/08-scheduling-preemption-eviction.md) — 应用了 Kubernetes v1.37 调度器针对原地 Pod 调整大小的抢占功能（Alpha）以及 Workload-Aware Scheduling 的进展（Workload/PodGroup Beta、CompositePodGroup API）
- 2026-W38: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 应用了 Kubernetes v1.37 Node 生命周期条件（用于 drain、维护和优雅关机的五个众所周知条件）
- 2026-W38: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — 应用了适用于 Kubernetes v1.37 组件指标的 Prometheus 原生直方图（Beta，默认启用）
- 2026-W38: [networking/cilium/README.md](../networking/cilium/README.md) — 应用了 Cilium 1.21.0-pre.2 预发布版本（Gateway API 会话持久性、AWS 托管前缀列表、默认 BPF 伪装）
- 2026-W38: 无匹配文档 — Karmada 成为 CNCF 毕业项目（[来源](https://www.cncf.io/announcements/2026/09/07/cloud-native-computing-foundation-announces-karmada-graduation/)）
- 2026-W38: 无匹配文档 — Kubernetes 灾难恢复：来自三个可复现故障场景的指导，CNCF 博客（[来源](https://www.cncf.io/blog/2026/09/10/kubernetes-disaster-recovery-guidance-from-three-reproducible-failure-scenarios/)）
- 2026-W38: 无匹配文档 — AWS Private CA EKS 附加组件和 Connector for AD 现可用于 AWS GovCloud (US)（[来源](https://aws.amazon.com/about-aws/whats-new/2026/09/private-ca-eks-addon-ad-govcloud/))
- 2026-W36: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 应用了 Kubernetes v1.37 “Garhwal” 版本（Pod certificates/ClusterTrustBundles Stable、Metrics API GA、kube-dns 和 IPVS-mode 弃用等）
- 2026-W36: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 应用了 Istio 1.30.4/1.29.7 安全补丁版本（ISTIO-SECURITY-2026-006、13 个 Envoy CVE）
- 2026-W36: [gitops/argocd/README.md](../gitops/argocd/README.md) — 应用了 ArgoCD v3.5.2/v3.4.8 补丁版本
- 2026-W36: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — 应用了 Linkerd edge-26.8.4（TLSRoute API 版本协商等）
- 2026-W36: 无匹配文档 — Amazon EKS 现支持每个集群最多 10 个外部 OIDC 身份提供商（[来源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-multiple-oidc-providers))
- 2026-W36: 无匹配文档 — 在峰值前扩缩容：Kubernetes 上 GPU 工作负载的预测性自动扩缩容，CNCF 博客（[来源](https://www.cncf.io/blog/2026/08/28/scale-before-the-spike-predictive-autoscaling-for-gpu-workloads-on-kubernetes/)）
- 2026-W36: 无匹配文档 — 在 Kubernetes 上构建 AI 工厂，CNCF 博客（[来源](https://www.cncf.io/blog/2026/08/27/building-an-ai-factory-on-kubernetes/)）
- 2026-W35: [gitops/argocd/README.md](../gitops/argocd/README.md) — 应用了适用于 Amazon EKS 托管 Argo CD 功能的自定义配置支持（通过 `argocd-cm` ConfigMap）
- 2026-W35: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 应用了 Kubernetes v1.36.4/v1.35.8/v1.34.11 补丁版本和 v1.37.0-rc.1
- 2026-W35: [networking/cilium/README.md](../networking/cilium/README.md) — 应用了 Cilium 1.20.1/1.19.7/1.18.13 补丁版本
- 2026-W35: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 应用了 Karpenter v1.14.1 补丁版本
- 2026-W35: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 应用了 Istio 1.31.0-rc.0 版本（1.31 进入 RC）
- 2026-W35: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 应用了 CNCF 博客中将缓慢 SQL 查询提炼为 OTel span 派生指标的指南
- 2026-W35: 无匹配文档 — Amazon EKS 现支持通过自动化生命周期管理进行证书颁发机构（CA）轮换（[来源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-certificate-authority-ca-rotation-automated-lifecycle-management))
- 2026-W35: 无匹配文档 — Kubeflow 在 CNCF 内毕业（[来源](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/))
- 2026-W34: [gitops/argocd/README.md](../gitops/argocd/README.md) — 应用了 ArgoCD v3.5.0 GA 版本以及 v3.5.1/v3.4.7/v3.3.14 补丁版本
- 2026-W34: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 应用了 Istio 1.31.0-beta.1 版本（1.31 进入 beta）
- 2026-W34: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — 应用了 Linkerd edge-26.8.2（Gateway API 1.5.1 支持，测试的最高 k8s 版本为 1.36）
- 2026-W34: 无匹配文档 — Amazon EKS 现支持高级 Kubernetes 控制平面配置参数（scheduler/controller manager/API server 调优）（[来源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-control-plane-configuration-parameters))
- 2026-W34: 无匹配文档 — Cloud Native Buildpacks 成为 CNCF 毕业项目（[来源](https://www.cncf.io/announcements/2026/08/11/cncf-announces-graduation-of-cloud-native-buildpacks-advancing-the-standard-for-container-builds/))
- 2026-W34: 无匹配文档 — KubeCon + CloudNativeCon North America 2026 日程公布，新增 AI Inference + Agentic 专题（[来源](https://www.cncf.io/announcements/2026/08/10/cncf-reveals-kubecon-cloudnativecon-north-america-2026-schedule-adds-new-ai-inference-agentic-track/))
- 2026-W34: 无匹配文档 — 如何将 Kubernetes YAML 美化打印为 KYAML，Kubernetes 博客（[来源](https://kubernetes.io/blog/2026/08/11/how-to-pretty-print-kubernetes-yaml-as-kyaml/))
- 2026-W33: [networking/04-gateway-api.md](../networking/04-gateway-api.md) — 应用了 Gateway API v1.6（TCPRoute/UDPRoute 升级至 Standard v1、特定通道的弃用 API 服务变更）
- 2026-W33: [gitops/argocd/README.md](../gitops/argocd/README.md) — 应用了 ArgoCD v3.5.0 GA（Helm 4 迁移、源完整性验证 alpha、ApplicationSet 改进）
- 2026-W33: [networking/cilium/README.md](../networking/cilium/README.md) — 应用了 Cilium 1.20.0 GA（Gateway API v1.6.1、KCNP、多池 IPAM 迁移）和 1.21.0-pre.0
- 2026-W33: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 应用了 Kubernetes v1.37 前瞻、Docs Freeze 生效以及 v1.38.0-alpha.0 标签
- 2026-W33: 无匹配文档 — Amazon ECR 现支持 Docker push 的镜像层最大达到 200 GB（[来源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-ecr-image-layers/))
- 2026-W33: 无匹配文档 — K8gb 成为 CNCF 孵化项目（[来源](https://www.cncf.io/announcements/2026/08/05/k8gb-becomes-a-cncf-incubating-project/))
- 2026-W33: 无匹配文档 — OpenCost 1.121.0 新增 Kubernetes 推理成本跟踪（[来源](https://www.cncf.io/blog/2026/08/05/opencost-1-121-0-first-of-a-kind-kubernetes-inference-cost-tracking/))
- 2026-W33: 无匹配文档 — Kubernetes DRA 会取代 HAMi 吗？CNCF 博客（[来源](https://www.cncf.io/blog/2026/08/07/does-kubernetes-dra-replace-hami/))
- 2026-W31: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 应用了 Kubernetes v1.36.3/v1.35.7/v1.34.10 补丁版本以及 v1.37 Code Freeze 生效
- 2026-W31: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — 应用了 EKS Auto Mode 节点池对 EFA 和 EC2 placement group 的支持
- 2026-W31: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 应用了 Karpenter 节点池对 EFA 和 EC2 placement group 的支持
- 2026-W31: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — 应用了 AMP 限额提高（每个工作区 15 亿个活动时间序列、20 万条规则）
- 2026-W31: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 应用了 OpenTelemetry 从 CNCF 毕业的内容
- 2026-W31: [networking/calico/README.md](../networking/calico/README.md) — 应用了 Tigera 在 Kubernetes 上推出的 Calico for VMs（基于 eBPF 的 VM+container 统一网络）
- 2026-W31: [networking/cilium/README.md](../networking/cilium/README.md) — 应用了 Cilium 1.20.0-rc.1 release candidate
- 2026-W31: 无匹配文档 — Confidential Containers 成为 CNCF 孵化项目（[来源](https://www.cncf.io/blog/2026/07/22/confidential-containers-becomes-a-cncf-incubating-project/)）
- 2026-W31: 无匹配文档 — Kubernetes CSI drivers 中的两个路径遍历 CVE（CVE-2026-3864 NFS / CVE-2026-3865 SMB；已在 csi-driver-nfs v4.13.1、csi-driver-smb v1.20.1 中修复）（[来源](https://www.sentinelone.com/blog/mount-here-read-there-twin-path-traversal-cves-in-kubernetes-storage/))
- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — 应用了 Cilium 1.19.6/1.18.12/1.17.18 补丁版本和 CVE-2026-56743（ipBlock NetworkPolicy 问题）
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 应用了 Istio 1.30.3/1.29.6 补丁版本
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — 应用了 Linkerd edge-26.7.1（不允许向未定义的服务端口发出请求，破坏性变更）
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — 应用了 EKS Auto Mode 对 ARC zonal shift/autoshift 的支持
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — 应用了 EKS Auto Mode 对 ARC zonal shift 的支持
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 应用了适用于旧版本线的 Karpenter 补丁版本（v1.3.8–v1.11.3）
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 应用了 Kubernetes v1.37.0-beta.0 以及 v1.37 发布日程
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — 应用了 ArgoCon Japan 2026 以及即将举行的 Argo CD 3.5 路线图会议
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — 应用了 Kubernetes 博客的自定义指标 exporter 指南
- 2026-W30: 无匹配文档 — HAMi 成为 CNCF 孵化项目（[来源](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/)）
- 2026-W30: 无匹配文档 — 使用 vLLM 在 Kubernetes 中运行自托管 LLM，CNCF 博客（[来源](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/)）
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — 应用了 ACM 对 ACME 协议的支持（cert-manager 现可使用 ACM 公有证书）
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 应用了面向 AI agents 的 NGINX + OpenTelemetry 网络边界可观测性模式
- 2026-W29: 无匹配文档 — 为 AI 原生工作负载演进平台工程，CNCF 博客（[来源](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/)）
- 2026-07-11: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 应用了 etcd v3.7.0 版本（RangeStream 等）
- 2026-07-11: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — 应用了 EKS Auto Mode GPU 管理费最高降低 60%
- 2026-07-11: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 应用了 Karpenter v1.14.0 版本（CapacityBuffers API 等）
- 2026-07-11: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — 应用了 CloudWatch Application Signals Service Events
- 2026-07-11: [gitops/argocd/README.md](../gitops/argocd/README.md) — 应用了 ArgoCD v3.4.5 补丁版本
- 2026-07-11: 无匹配文档 — 解读 ingress-nginx 退役（2026 年 3 月），CNCF 博客（[来源](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/)）
- 2026-07-11: 无匹配文档 — 发布 CNCF 《云原生 AI 中的数据存储》白皮书（[来源](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/)）
- 2026-07-11: 无匹配文档 — Amazon EMR on EKS 现支持 Apache Spark 故障排除 agent（[来源](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/))
- 2026-07-11: 无匹配文档 — AWS Systems Manager 混合/多云节点定价全面调整（取消 Advanced Instances Tier）（[来源](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/))

</details>
