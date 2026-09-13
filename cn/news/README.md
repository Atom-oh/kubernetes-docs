# 新闻
> **最后更新**：2026 年 9 月 12 日

本页记录 Kubernetes、Amazon EKS 和 CNCF 新闻引发的文档更改。GitHub Actions 每周一 09:00 KST 准备更新，通过质量门禁后创建 PR。更改经审查、合并和部署后发布到站点。

周标签标识日志条目所属周，可能与来源发布日期不同。这些是历史记录；当前支持、安全补丁和运维要求请查阅链接指南及官方来源。“未匹配文档”描述当时自动匹配的结果。

## 更新日志

- 2026-W36: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已更新 Kubernetes v1.37“Garhwal”发布内容（Pod 证书/ClusterTrustBundle 稳定、Metrics API GA、kube-dns 和 IPVS 模式弃用等）
- 2026-W36: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 已更新 Istio 1.30.4/1.29.7 安全补丁发布（ISTIO-SECURITY-2026-006，13 个 Envoy CVE）
- 2026-W36: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已更新 ArgoCD v3.5.2/v3.4.8 补丁发布
- 2026-W36: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — 已更新 Linkerd edge-26.8.4（TLSRoute API 版本协商等）
- 2026-W36: 未匹配文档 — Amazon EKS 现支持每集群最多 10 个外部 OIDC 身份提供程序 ([来源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-multiple-oidc-providers))
- 2026-W36: 未匹配文档 — 在峰值前扩容：Kubernetes GPU 工作负载的预测性自动扩缩容，CNCF 博客 ([来源](https://www.cncf.io/blog/2026/08/28/scale-before-the-spike-predictive-autoscaling-for-gpu-workloads-on-kubernetes/))
- 2026-W36: 未匹配文档 — 在 Kubernetes 上构建 AI 工厂，CNCF 博客 ([来源](https://www.cncf.io/blog/2026/08/27/building-an-ai-factory-on-kubernetes/))
- 2026-W35: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已更新 Amazon EKS 托管 Argo CD 能力的自定义配置支持（通过 `argocd-cm` ConfigMap）
- 2026-W35: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已更新 Kubernetes v1.36.4/v1.35.8/v1.34.11 补丁发布及 v1.37.0-rc.1
- 2026-W35: [networking/cilium/README.md](../networking/cilium/README.md) — 已更新 Cilium 1.20.1/1.19.7/1.18.13 补丁发布
- 2026-W35: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 已更新 Karpenter v1.14.1 补丁发布
- 2026-W35: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 已更新 Istio 1.31.0-rc.0 发布（1.31 进入 RC）
- 2026-W35: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 已更新 CNCF 博客指南：将慢 SQL 查询提炼为 OTel span 派生指标
- 2026-W35: 未匹配文档 — Amazon EKS 现支持带自动生命周期管理的证书颁发机构（CA）轮换 ([来源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-certificate-authority-ca-rotation-automated-lifecycle-management))
- 2026-W35: 未匹配文档 — Kubeflow 在 CNCF 毕业 ([来源](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/))
- 2026-W34: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已更新 ArgoCD v3.5.0 GA 发布及 v3.5.1/v3.4.7/v3.3.14 补丁发布
- 2026-W34: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 已更新 Istio 1.31.0-beta.1 发布（1.31 进入 beta）
- 2026-W34: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — 已更新 Linkerd edge-26.8.2（支持 Gateway API 1.5.1，已测试最高 k8s 1.36）
- 2026-W34: 未匹配文档 — Amazon EKS 现支持高级 Kubernetes 控制平面配置参数（调度器/控制器管理器/API 服务器调优） ([来源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-control-plane-configuration-parameters))
- 2026-W34: 未匹配文档 — Cloud Native Buildpacks 成为 CNCF 毕业项目 ([来源](https://www.cncf.io/announcements/2026/08/11/cncf-announces-graduation-of-cloud-native-buildpacks-advancing-the-standard-for-container-builds/))
- 2026-W34: 未匹配文档 — KubeCon + CloudNativeCon North America 2026 日程公布，新增 AI 推理 + 智能体专题 ([来源](https://www.cncf.io/announcements/2026/08/10/cncf-reveals-kubecon-cloudnativecon-north-america-2026-schedule-adds-new-ai-inference-agentic-track/))
- 2026-W34: 未匹配文档 — 如何将 Kubernetes YAML 美化输出为 KYAML，Kubernetes 博客 ([来源](https://kubernetes.io/blog/2026/08/11/how-to-pretty-print-kubernetes-yaml-as-kyaml/))
- 2026-W33: [networking/04-gateway-api.md](../networking/04-gateway-api.md) — 已更新 Gateway API v1.6（TCPRoute/UDPRoute 晋升 Standard v1，各渠道已弃用 API 服务变化）
- 2026-W33: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已更新 ArgoCD v3.5.0 GA（Helm 4 迁移、源完整性验证 alpha、ApplicationSet 改进）
- 2026-W33: [networking/cilium/README.md](../networking/cilium/README.md) — 已更新 Cilium 1.20.0 GA（Gateway API v1.6.1、KCNP、多池 IPAM 迁移）及 1.21.0-pre.0
- 2026-W33: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已更新 Kubernetes v1.37 前瞻、文档冻结生效及 v1.38.0-alpha.0 标签
- 2026-W33: 未匹配文档 — Amazon ECR 现支持 Docker push 最大 200 GB 镜像层 ([来源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-ecr-image-layers/))
- 2026-W33: 未匹配文档 — K8gb 成为 CNCF 孵化项目 ([来源](https://www.cncf.io/announcements/2026/08/05/k8gb-becomes-a-cncf-incubating-project/))
- 2026-W33: 未匹配文档 — OpenCost 1.121.0 添加 Kubernetes 推理成本跟踪 ([来源](https://www.cncf.io/blog/2026/08/05/opencost-1-121-0-first-of-a-kind-kubernetes-inference-cost-tracking/))
- 2026-W33: 未匹配文档 — Kubernetes DRA 会替代 HAMi 吗？CNCF 博客 ([来源](https://www.cncf.io/blog/2026/08/07/does-kubernetes-dra-replace-hami/))
- 2026-W31: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已更新 Kubernetes v1.36.3/v1.35.7/v1.34.10 补丁发布及 v1.37 代码冻结生效
- 2026-W31: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — 已更新 EKS Auto Mode 节点池的 EFA 和 EC2 置放群组支持
- 2026-W31: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 已更新 Karpenter 节点池的 EFA 和 EC2 置放群组支持
- 2026-W31: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — 已更新 AMP 限制提高（1.5B 活动序列，每工作区 200K 规则）
- 2026-W31: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 已更新 OpenTelemetry 在 CNCF 毕业
- 2026-W31: [networking/calico/README.md](../networking/calico/README.md) — 已更新 Tigera 面向 Kubernetes 虚拟机的 Calico 发布（基于 eBPF 的虚拟机+容器统一网络）
- 2026-W31: [networking/cilium/README.md](../networking/cilium/README.md) — 已更新 Cilium 1.20.0-rc.1 候选发布
- 2026-W31: 未匹配文档 — Confidential Containers 成为 CNCF 孵化项目 ([来源](https://www.cncf.io/blog/2026/07/22/confidential-containers-becomes-a-cncf-incubating-project/))
- 2026-W31: 未匹配文档 — Kubernetes CSI 驱动的两个路径遍历 CVE（CVE-2026-3864 NFS / CVE-2026-3865 SMB；已在 csi-driver-nfs v4.13.1、csi-driver-smb v1.20.1 修复） ([来源](https://www.sentinelone.com/blog/mount-here-read-there-twin-path-traversal-cves-in-kubernetes-storage/))
- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — 已更新 Cilium 1.19.6/1.18.12/1.17.18 补丁发布及 CVE-2026-56743（ipBlock NetworkPolicy 问题）
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 已更新 Istio 1.30.3/1.29.6 补丁发布
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — 已更新 Linkerd edge-26.7.1（禁止访问未定义服务端口，破坏性变更）
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — 已更新 EKS Auto Mode 的 ARC 可用区转移/自动转移支持
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — 已更新 EKS Auto Mode 的 ARC 可用区转移支持
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 已更新 Karpenter 旧版本系列补丁发布（v1.3.8–v1.11.3）
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已更新 Kubernetes v1.37.0-beta.0 和 v1.37 发布日程
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已更新 ArgoCon Japan 2026 及即将举行的 Argo CD 3.5 路线图会议
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — 已更新 Kubernetes 博客的自定义指标导出器指南
- 2026-W30: 未匹配文档 — HAMi 成为 CNCF 孵化项目 ([来源](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/))
- 2026-W30: 未匹配文档 — 使用 vLLM 在 Kubernetes 运行自托管 LLM，CNCF 博客 ([来源](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/))
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — 已更新 ACM 对 ACME 协议的支持（cert-manager 现在可使用 ACM 公有证书）
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 已更新面向 AI 智能体的 NGINX + OpenTelemetry 网络边界可观测性模式
- 2026-W29: 未匹配文档 — 面向 AI 原生工作负载的平台工程演进，CNCF 博客 ([来源](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/))
- 2026-07-11: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已更新 etcd v3.7.0 发布（RangeStream 等）
- 2026-07-11: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — 已更新 EKS Auto Mode GPU 管理费最高降低 60%
- 2026-07-11: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 已更新 Karpenter v1.14.0 发布（CapacityBuffers API 等）
- 2026-07-11: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — 已更新 CloudWatch Application Signals 服务事件
- 2026-07-11: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已更新 ArgoCD v3.4.5 补丁发布
- 2026-07-11: 未匹配文档 — 应对 ingress-nginx 退役（2026 年 3 月），CNCF 博客 ([来源](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/))
- 2026-07-11: 未匹配文档 — CNCF《云原生 AI 中的数据存储》白皮书发布 ([来源](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/))
- 2026-07-11: 未匹配文档 — Amazon EMR on EKS 现支持 Apache Spark 故障排除智能体 ([来源](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/))
- 2026-07-11: 未匹配文档 — AWS Systems Manager 混合/多云节点定价调整（取消 Advanced Instances Tier） ([来源](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/))
