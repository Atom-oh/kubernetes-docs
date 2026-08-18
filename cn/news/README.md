# 新闻
> **最后更新**: August 10, 2026

此处不会将 Kubernetes、Amazon EKS 和 CNCF 生态系统新闻汇总为单独的摘要文档。每周，GitHub Actions 都会将相关新闻直接应用到其对应的现有文档中；此更新日志仅记录哪些文档发生了更改及其原因。没有匹配文档的新闻仅在此以链接形式记录。

## 更新日志

- 2026-W33: [networking/04-gateway-api.md](../networking/04-gateway-api.md) — 已应用 Gateway API v1.6（TCPRoute/UDPRoute 升级为 Standard v1，实验性资源迁移至 x-k8s.io API 组）
- 2026-W33: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已应用 ArgoCD v3.5.0 GA（迁移至 Helm 4、源完整性验证 alpha、ApplicationSet 改进）
- 2026-W33: [networking/cilium/README.md](../networking/cilium/README.md) — 已应用 Cilium 1.20.0 GA（Gateway API v1.6.1、KCNP、多池 IPAM 迁移）和 1.21.0-pre.0
- 2026-W33: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已应用 Kubernetes v1.37 前瞻、Docs Freeze 生效以及 v1.38.0-alpha.0 标签
- 2026-W33: 无匹配文档 — Amazon ECR 现已支持用于 Docker push 的最大 200 GB 镜像层（[来源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-ecr-image-layers/)）
- 2026-W33: 无匹配文档 — K8gb 成为 CNCF 孵化项目（[来源](https://www.cncf.io/announcements/2026/08/05/k8gb-becomes-a-cncf-incubating-project/)）
- 2026-W33: 无匹配文档 — OpenCost 1.121.0 新增 Kubernetes 推理成本跟踪（[来源](https://www.cncf.io/blog/2026/08/05/opencost-1-121-0-first-of-a-kind-kubernetes-inference-cost-tracking/)）
- 2026-W33: 无匹配文档 — Kubernetes DRA 是否会取代 HAMi？CNCF 博客（[来源](https://www.cncf.io/blog/2026/08/07/does-kubernetes-dra-replace-hami/)）
- 2026-W31: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已应用 Kubernetes v1.36.3/v1.35.7/v1.34.10 补丁版本以及 v1.37 Code Freeze 生效
- 2026-W31: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — 已应用 EKS Auto Mode node pool 对 EFA 和 EC2 placement group 的支持
- 2026-W31: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 已应用 Karpenter node pool 对 EFA 和 EC2 placement group 的支持
- 2026-W31: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — 已应用 AMP 限制提升（每个 workspace 15 亿活跃 series、20 万条 rules）
- 2026-W31: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 已应用 OpenTelemetry 从 CNCF 毕业
- 2026-W31: [networking/calico/README.md](../networking/calico/README.md) — 已应用 Tigera 推出的 Kubernetes 上用于 VM 的 Calico（基于 eBPF 的 VM+container 统一网络）
- 2026-W31: [networking/cilium/README.md](../networking/cilium/README.md) — 已应用 Cilium 1.20.0-rc.1 release candidate
- 2026-W31: 无匹配文档 — Confidential Containers 成为 CNCF 孵化项目（[来源](https://www.cncf.io/blog/2026/07/22/confidential-containers-becomes-a-cncf-incubating-project/)）
- 2026-W31: 无匹配文档 — Kubernetes CSI driver 中的双路径遍历 CVE（CVE-2026-3864 NFS / CVE-2026-3865 SMB；已在 csi-driver-nfs v4.13.1、csi-driver-smb v1.20.1 中修复）（[来源](https://www.sentinelone.com/blog/mount-here-read-there-twin-path-traversal-cves-in-kubernetes-storage/)）
- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — 已应用 Cilium 1.19.6/1.18.12/1.17.18 补丁版本以及 CVE-2026-56743（ipBlock NetworkPolicy 问题）
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 已应用 Istio 1.30.3/1.29.6 补丁版本
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — 已应用 Linkerd edge-26.7.1（不允许请求未定义的 Service port，存在破坏性变更）
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — 已应用 EKS Auto Mode 对 ARC zonal shift/autoshift 的支持
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — 已应用 EKS Auto Mode 对 ARC zonal shift 的支持
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 已应用所有受维护版本线的协调 Karpenter 补丁发布（v1.3.8–v1.11.3）
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已应用 Kubernetes v1.37.0-beta.0 和 v1.37 发布计划
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已应用 ArgoCon Japan 2026 及即将举行的 Argo CD 3.5 路线图会议
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — 已应用 Kubernetes 博客的自定义 metrics exporter 指南
- 2026-W30: 无匹配文档 — HAMi 成为 CNCF 孵化项目（[来源](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/)）
- 2026-W30: 无匹配文档 — 使用 vLLM 在 Kubernetes 中运行自托管 LLM，CNCF 博客（[来源](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/)）
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — 已应用 ACM 对 ACME protocol 的支持（ACM public certificate 现可从 cert-manager 使用）
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 已应用面向 AI agent 的 NGINX + OpenTelemetry network-boundary observability 模式
- 2026-W29: 无匹配文档 — 面向 AI-native workload 的平台工程演进，CNCF 博客（[来源](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/)）
- 2026-07-11: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已应用 etcd v3.7.0 发布（RangeStream 等）
- 2026-07-11: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — 已应用 EKS Auto Mode GPU 管理费最高降低 60%
- 2026-07-11: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 已应用 Karpenter v1.14.0 发布（CapacityBuffers API 等）
- 2026-07-11: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — 已应用 CloudWatch Application Signals Service Events
- 2026-07-11: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已应用 ArgoCD v3.4.5 补丁版本
- 2026-07-11: 无匹配文档 — ingress-nginx 停止维护指南（2026 年 3 月），CNCF 博客（[来源](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/)）
- 2026-07-11: 无匹配文档 — 已发布 CNCF《Cloud Native AI 中的数据存储》白皮书（[来源](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/)）
- 2026-07-11: 无匹配文档 — Amazon EMR on EKS 现已支持 Apache Spark 故障排除 agent（[来源](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/)）
- 2026-07-11: 无匹配文档 — AWS Systems Manager hybrid/multicloud node 定价全面调整（取消 Advanced Instances Tier）（[来源](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/)）
