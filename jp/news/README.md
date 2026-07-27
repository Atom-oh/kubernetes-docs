# ニュース
> **最終更新**: July 27, 2026

Kubernetes、Amazon EKS、CNCF エコシステムのニュースは、ここでは個別のダイジェスト文書にはまとめていません。毎週、GitHub Actions が関連するニュースを該当する既存ドキュメントに直接適用し、この更新ログには変更されたドキュメントとその理由のみを記録します。該当するドキュメントがないニュースは、リンクのみをここに記録します。

## 更新ログ

- 2026-W31: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.36.3/v1.35.7/v1.34.10 のパッチリリースと、v1.37 Code Freeze の発効を適用
- 2026-W31: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — EKS Auto Mode node pool 向けの EFA および EC2 placement group サポートを適用
- 2026-W31: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter node pool 向けの EFA および EC2 placement group サポートを適用
- 2026-W31: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — AMP の制限引き上げ（アクティブ series 15 億、workspace あたり rule 20 万件）を適用
- 2026-W31: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — OpenTelemetry の CNCF 卒業を適用
- 2026-W31: [networking/calico/README.md](../networking/calico/README.md) — Tigera による Kubernetes 上の Calico for VMs のローンチ（eBPF ベースの VM+container 統合ネットワーキング）を適用
- 2026-W31: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.0-rc.1 リリース候補を適用
- 2026-W31: 該当するドキュメントなし — Confidential Containers が CNCF インキュベーティングプロジェクトに移行 ([source](https://www.cncf.io/blog/2026/07/22/confidential-containers-becomes-a-cncf-incubating-project/))
- 2026-W31: 該当するドキュメントなし — Kubernetes CSI driver における 2 件の path traversal CVE（CVE-2026-3864 NFS / CVE-2026-3865 SMB、csi-driver-nfs v4.13.1、csi-driver-smb v1.20.1 で修正済み） ([source](https://www.sentinelone.com/blog/mount-here-read-there-twin-path-traversal-cves-in-kubernetes-storage/))
- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.19.6/1.18.12/1.17.18 のパッチリリースと CVE-2026-56743（ipBlock NetworkPolicy の問題）を適用
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.30.3/1.29.6 のパッチリリースを適用
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.7.1（未定義の Service port への request を禁止、破壊的変更）を適用
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — EKS Auto Mode 向けの ARC zonal shift/autoshift サポートを適用
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — EKS Auto Mode 向けの ARC zonal shift サポートを適用
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — すべての保守対象ラインにまたがる調整済み Karpenter パッチリリース（v1.3.8–v1.11.3）を適用
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37.0-beta.0 と v1.37 リリーススケジュールを適用
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCon Japan 2026 と今後開催される Argo CD 3.5 ロードマップセッションを適用
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — Kubernetes blog の custom metrics exporter ガイドを適用
- 2026-W30: 該当するドキュメントなし — HAMi が CNCF インキュベーティングプロジェクトに移行 ([source](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/))
- 2026-W30: 該当するドキュメントなし — vLLM を使用して Kubernetes で self-hosted LLM を実行、CNCF blog ([source](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/))
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — ACME protocol 向けの ACM サポート（ACM public certificate を cert-manager から利用可能）を適用
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — AI agent 向けの NGINX + OpenTelemetry network-boundary observability パターンを適用
- 2026-W29: 該当するドキュメントなし — AI-native workload 向け platform engineering の進化、CNCF blog ([source](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/))
- 2026-07-11: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — etcd v3.7.0 リリース（RangeStream など）を適用
- 2026-07-11: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — EKS Auto Mode の GPU management fee を最大 60% 削減する変更を適用
- 2026-07-11: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.14.0 リリース（CapacityBuffers API など）を適用
- 2026-07-11: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — CloudWatch Application Signals Service Events を適用
- 2026-07-11: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.4.5 パッチリリースを適用
- 2026-07-11: 該当するドキュメントなし — ingress-nginx の廃止（2026 年 3 月）への対応、CNCF blog ([source](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/))
- 2026-07-11: 該当するドキュメントなし — CNCF Data Storage in Cloud Native AI ホワイトペーパーを公開 ([source](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/))
- 2026-07-11: 該当するドキュメントなし — Amazon EMR on EKS が Apache Spark troubleshooting agent をサポート開始 ([source](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/))
- 2026-07-11: 該当するドキュメントなし — AWS Systems Manager の hybrid/multicloud node 料金体系を刷新（Advanced Instances Tier を廃止） ([source](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/))
