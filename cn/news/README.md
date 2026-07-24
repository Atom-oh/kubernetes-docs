# 新闻
> **最后更新**: July 21, 2026

这里不会将 Kubernetes、Amazon EKS 和 CNCF 生态系统新闻汇集成单独的摘要文档。每周，GitHub Actions 会将相关新闻直接应用到其所关联的现有文档中，而此更新日志仅记录哪些文档发生变更及其原因。没有匹配文档的新闻仅在此以链接形式记录。

## 更新日志

- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — 已应用 Cilium 1.19.6/1.18.12/1.17.18 补丁版本发布，以及 CVE-2026-56743（ipBlock NetworkPolicy 问题）
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 已应用 Istio 1.30.3/1.29.6 补丁版本发布
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — 已应用 Linkerd edge-26.7.1（不再允许对未定义 Service 端口发起请求，存在破坏性变更）
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — 已应用 EKS Auto Mode 对 ARC zonal shift/autoshift 的支持
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — 已应用 EKS Auto Mode 的 ARC zonal shift 支持
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 已应用所有受维护版本线的协调 Karpenter 补丁版本发布（v1.3.8–v1.11.3）
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已应用 Kubernetes v1.37.0-beta.0 及 v1.37 发布计划
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已应用 ArgoCon Japan 2026 及即将举行的 Argo CD 3.5 路线图会议
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — 已应用 Kubernetes 博客的自定义指标 exporter 指南
- 2026-W30: 无匹配文档 — HAMi 成为 CNCF 孵化项目（[来源](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/)）
- 2026-W30: 无匹配文档 — 在 Kubernetes 中使用 vLLM 运行自托管 LLM，CNCF 博客（[来源](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/)）
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — 已应用对 ACME protocol 的 ACM 支持（ACM public certificates 现可由 cert-manager 使用）
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 已应用适用于 AI agents 的 NGINX + OpenTelemetry 网络边界可观测性模式
- 2026-W29: 无匹配文档 — 面向 AI-native workloads 的平台工程演进，CNCF 博客（[来源](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/)）
- 2026-07-11: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 已应用 etcd v3.7.0 发布（RangeStream 等）
- 2026-07-11: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — 已应用 EKS Auto Mode GPU 管理费用最高降低 60%
- 2026-07-11: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 已应用 Karpenter v1.14.0 发布（CapacityBuffers API 等）
- 2026-07-11: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — 已应用 CloudWatch Application Signals Service Events
- 2026-07-11: [gitops/argocd/README.md](../gitops/argocd/README.md) — 已应用 ArgoCD v3.4.5 补丁版本发布
- 2026-07-11: 无匹配文档 — ingress-nginx 退役导航（2026 年 3 月），CNCF 博客（[来源](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/)）
- 2026-07-11: 无匹配文档 — CNCF《Cloud Native AI 中的数据存储》白皮书已发布（[来源](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/)）
- 2026-07-11: 无匹配文档 — Amazon EMR on EKS 现支持 Apache Spark 故障排除 agent（[来源](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/)）
- 2026-07-11: 无匹配文档 — AWS Systems Manager hybrid/multicloud node 定价改革（取消 Advanced Instances Tier）（[来源](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/))
