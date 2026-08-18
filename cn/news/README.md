# 新闻
> **最后更新**: August 17, 2026

此处不会将 Kubernetes、Amazon EKS 和 CNCF 生态系统新闻汇编为单独的摘要文档。每周，GitHub Actions 会将相关新闻直接应用到其对应的现有文档中，而此更新日志仅记录哪些文档发生了变更及其原因。没有匹配文档的新闻仅在此处以链接形式记录。

## 更新日志

- 2026-W34: [gitops/argocd/README.md](../gitops/argocd/README.md) — 应用了 ArgoCD v3.5.0 GA 发布版以及 v3.5.1/v3.4.7/v3.3.14 补丁发布版
- 2026-W34: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 应用了 Istio 1.31.0-beta.1 发布版（1.31 进入 beta 阶段）
- 2026-W34: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — 应用了 Linkerd edge-26.8.2（支持 Gateway API 1.5.1，已测试的最高 k8s 版本为 1.36）
- 2026-W34: 没有匹配文档 — Amazon EKS 现支持高级 Kubernetes 控制平面配置参数（scheduler/controller manager/API server 调优）([source](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-control-plane-configuration-parameters))
- 2026-W34: 没有匹配文档 — Cloud Native Buildpacks 成为 CNCF 毕业项目 ([source](https://www.cncf.io/announcements/2026/08/11/cncf-announces-graduation-of-cloud-native-buildpacks-advancing-the-standard-for-container-builds/))
- 2026-W34: 没有匹配文档 — KubeCon + CloudNativeCon North America 2026 日程公布，新增 AI Inference + Agentic 专题赛道 ([source](https://www.cncf.io/announcements/2026/08/10/cncf-reveals-kubecon-cloudnativecon-north-america-2026-schedule-adds-new-ai-inference-agentic-track/))
- 2026-W34: 没有匹配文档 — 如何将 Kubernetes YAML 格式化输出为 KYAML，Kubernetes 博客 ([source](https://kubernetes.io/blog/2026/08/11/how-to-pretty-print-kubernetes-yaml-as-kyaml/))
- 2026-W33: [networking/04-gateway-api.md](../networking/04-gateway-api.md) — 应用了 Gateway API v1.6（TCPRoute/UDPRoute 毕业为 Standard v1，实验性资源移至 x-k8s.io API group）
- 2026-W33: [gitops/argocd/README.md](../gitops/argocd/README.md) — 应用了 ArgoCD v3.5.0 GA（Helm 4 迁移、源完整性验证 alpha、ApplicationSet 改进）
- 2026-W33: [networking/cilium/README.md](../networking/cilium/README.md) — 应用了 Cilium 1.20.0 GA（Gateway API v1.6.1、KCNP、多池 IPAM 迁移）以及 1.21.0-pre.0
- 2026-W33: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 应用了 Kubernetes v1.37 预览、Docs Freeze 生效以及 v1.38.0-alpha.0 标签
- 2026-W33: 没有匹配文档 — Amazon ECR 现支持 Docker push 的镜像层大小最高达 200 GB ([source](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-ecr-image-layers/))
- 2026-W33: 没有匹配文档 — K8gb 成为 CNCF 孵化项目 ([source](https://www.cncf.io/announcements/2026/08/05/k8gb-becomes-a-cncf-incubating-project/))
- 2026-W33: 没有匹配文档 — OpenCost 1.121.0 新增 Kubernetes inference 成本跟踪 ([source](https://www.cncf.io/blog/2026/08/05/opencost-1-121-0-first-of-a-kind-kubernetes-inference-cost-tracking/))
- 2026-W33: 没有匹配文档 — Kubernetes DRA 会取代 HAMi 吗？，CNCF 博客 ([source](https://www.cncf.io/blog/2026/08/07/does-kubernetes-dra-replace-hami/))
- 2026-W31: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 应用了 Kubernetes v1.36.3/v1.35.7/v1.34.10 补丁发布版以及 v1.37 Code Freeze 生效
- 2026-W31: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — 应用了对 EKS Auto Mode 节点池的 EFA 和 EC2 placement group 支持
- 2026-W31: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 应用了对 Karpenter 节点池的 EFA 和 EC2 placement group 支持
- 2026-W31: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — 应用了 AMP 限制提高（15 亿活跃 series，每个 workspace 20 万条规则）
- 2026-W31: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 应用了 OpenTelemetry 的 CNCF 毕业
- 2026-W31: [networking/calico/README.md](../networking/calico/README.md) — 应用了 Tigera 推出的 Calico for VMs on Kubernetes（基于 eBPF 的 VM+container 统一网络）
- 2026-W31: [networking/cilium/README.md](../networking/cilium/README.md) — 应用了 Cilium 1.20.0-rc.1 release candidate
- 2026-W31: 没有匹配文档 — Confidential Containers 成为 CNCF 孵化项目 ([source](https://www.cncf.io/blog/2026/07/22/confidential-containers-becomes-a-cncf-incubating-project/))
- 2026-W31: 没有匹配文档 — Kubernetes CSI driver 中的双路径遍历 CVE（CVE-2026-3864 NFS / CVE-2026-3865 SMB；已在 csi-driver-nfs v4.13.1、csi-driver-smb v1.20.1 中修复）([source](https://www.sentinelone.com/blog/mount-here-read-there-twin-path-traversal-cves-in-kubernetes-storage/))
- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — 应用了 Cilium 1.19.6/1.18.12/1.17.18 补丁发布版以及 CVE-2026-56743（ipBlock NetworkPolicy 问题）
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — 应用了 Istio 1.30.3/1.29.6 补丁发布版
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — 应用了 Linkerd edge-26.7.1（禁止请求未定义的 Service 端口，属于破坏性变更）
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — 应用了针对 EKS Auto Mode 的 ARC zonal shift/autoshift 支持
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — 应用了针对 EKS Auto Mode 的 ARC zonal shift 支持
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 应用了所有维护分支的协调 Karpenter 补丁发布版（v1.3.8–v1.11.3）
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 应用了 Kubernetes v1.37.0-beta.0 和 v1.37 发布计划
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — 应用了 ArgoCon Japan 2026 以及即将举行的 Argo CD 3.5 roadmap session
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — 应用了 Kubernetes 博客的自定义 metrics exporter 指南
- 2026-W30: 没有匹配文档 — HAMi 成为 CNCF 孵化项目 ([source](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/))
- 2026-W30: 没有匹配文档 — 使用 vLLM 在 Kubernetes 中运行自托管 LLM，CNCF 博客 ([source](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/))
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — 应用了 ACM 对 ACME protocol 的支持（ACM public certificates 现可通过 cert-manager 使用）
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 应用了面向 AI agent 的 NGINX + OpenTelemetry 网络边界可观测性模式
- 2026-W29: 没有匹配文档 — 面向 AI-native workload 的平台工程演进，CNCF 博客 ([source](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/))
- 2026-07-11: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — 应用了 etcd v3.7.0 发布版（RangeStream 等）
- 2026-07-11: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — 应用了 EKS Auto Mode GPU 管理费用最高降低 60%
- 2026-07-11: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 应用了 Karpenter v1.14.0 发布版（CapacityBuffers API 等）
- 2026-07-11: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — 应用了 CloudWatch Application Signals Service Events
- 2026-07-11: [gitops/argocd/README.md](../gitops/argocd/README.md) — 应用了 ArgoCD v3.4.5 补丁发布版
- 2026-07-11: 没有匹配文档 — 关于 ingress-nginx 退役的应对指南（2026 年 3 月），CNCF 博客 ([source](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/))
- 2026-07-11: 没有匹配文档 — CNCF《Cloud Native AI 中的数据存储》白皮书发布 ([source](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/))
- 2026-07-11: 没有匹配文档 — Amazon EMR on EKS 现支持 Apache Spark 故障排除 agent ([source](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/))
- 2026-07-11: 没有匹配文档 — AWS Systems Manager hybrid/multicloud 节点定价全面调整（取消 Advanced Instances Tier）([source](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/))
