# ニュース
> **最終更新**: August 10, 2026

Kubernetes、Amazon EKS、および CNCF エコシステムのニュースは、ここでは個別のダイジェスト文書にまとめていません。毎週、GitHub Actions が関連ニュースを該当する既存のドキュメントに直接反映し、この更新ログには変更されたドキュメントとその理由のみを記録します。該当するドキュメントがないニュースは、リンクのみをここに記録します。

## 更新ログ

- 2026-W33: [networking/04-gateway-api.md](../networking/04-gateway-api.md) — Gateway API v1.6 を反映（TCPRoute/UDPRoute は Standard v1 に昇格、experimental リソースは x-k8s.io API グループへ移動）
- 2026-W33: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.5.0 GA を反映（Helm 4 移行、ソース整合性検証 alpha、ApplicationSet の改善）
- 2026-W33: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.0 GA（Gateway API v1.6.1、KCNP、multi-pool IPAM 移行）および 1.21.0-pre.0 を反映
- 2026-W33: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37 の先行公開、Docs Freeze の発効、および v1.38.0-alpha.0 タグを反映
- 2026-W33: 該当するドキュメントなし — Amazon ECR が Docker push のイメージレイヤーを最大 200 GB までサポート（[出典](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-ecr-image-layers/)）
- 2026-W33: 該当するドキュメントなし — K8gb が CNCF インキュベーティングプロジェクトに移行（[出典](https://www.cncf.io/announcements/2026/08/05/k8gb-becomes-a-cncf-incubating-project/)）
- 2026-W33: 該当するドキュメントなし — OpenCost 1.121.0 が Kubernetes 推論コストの追跡を追加（[出典](https://www.cncf.io/blog/2026/08/05/opencost-1-121-0-first-of-a-kind-kubernetes-inference-cost-tracking/)）
- 2026-W33: 該当するドキュメントなし — Kubernetes DRA は HAMi を置き換えるのか？、CNCF ブログ（[出典](https://www.cncf.io/blog/2026/08/07/does-kubernetes-dra-replace-hami/)）
- 2026-W31: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.36.3/v1.35.7/v1.34.10 パッチリリースおよび v1.37 Code Freeze の発効を反映
- 2026-W31: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — EKS Auto Mode ノードプールに対する EFA および EC2 プレイスメントグループのサポートを反映
- 2026-W31: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter ノードプールに対する EFA および EC2 プレイスメントグループのサポートを反映
- 2026-W31: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — AMP の上限引き上げ（アクティブシリーズ 1.5B、ワークスペースあたりルール 200K）を反映
- 2026-W31: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — OpenTelemetry の CNCF 卒業を反映
- 2026-W31: [networking/calico/README.md](../networking/calico/README.md) — Tigera による Kubernetes 上の VM 向け Calico のリリース（eBPF ベースの VM+コンテナ統合ネットワーキング）を反映
- 2026-W31: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.0-rc.1 リリース候補を反映
- 2026-W31: 該当するドキュメントなし — Confidential Containers が CNCF インキュベーティングプロジェクトに移行（[出典](https://www.cncf.io/blog/2026/07/22/confidential-containers-becomes-a-cncf-incubating-project/)）
- 2026-W31: 該当するドキュメントなし — Kubernetes CSI ドライバーにおける 2 件のパストラバーサル CVE（CVE-2026-3864 NFS / CVE-2026-3865 SMB。csi-driver-nfs v4.13.1、csi-driver-smb v1.20.1 で修正済み）（[出典](https://www.sentinelone.com/blog/mount-here-read-there-twin-path-traversal-cves-in-kubernetes-storage/)）
- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.19.6/1.18.12/1.17.18 パッチリリースおよび CVE-2026-56743（ipBlock NetworkPolicy の問題）を反映
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.30.3/1.29.6 パッチリリースを反映
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.7.1（未定義の Service ポートへのリクエストを禁止、破壊的変更）を反映
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — EKS Auto Mode 向け ARC ゾーンシフト/autoshift サポートを反映
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — EKS Auto Mode 向け ARC ゾーンシフトサポートを反映
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — すべての保守対象ラインにおける Karpenter パッチリリースの協調リリース（v1.3.8–v1.11.3）を反映
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37.0-beta.0 および v1.37 リリーススケジュールを反映
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCon Japan 2026 および今後予定されている Argo CD 3.5 ロードマップセッションを反映
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — Kubernetes ブログのカスタムメトリクス exporter ガイドを反映
- 2026-W30: 該当するドキュメントなし — HAMi が CNCF インキュベーティングプロジェクトに移行（[出典](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/)）
- 2026-W30: 該当するドキュメントなし — vLLM を使用して Kubernetes でセルフホスト型 LLM を実行、CNCF ブログ（[出典](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/)）
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — ACME プロトコルに対する ACM サポート（ACM パブリック証明書が cert-manager から利用可能に）を反映
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — AI エージェント向けの NGINX + OpenTelemetry ネットワーク境界オブザーバビリティパターンを反映
- 2026-W29: 該当するドキュメントなし — AI ネイティブワークロード向けプラットフォームエンジニアリングの進化、CNCF ブログ（[出典](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/)）
- 2026-07-11: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — etcd v3.7.0 リリース（RangeStream など）を反映
- 2026-07-11: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — EKS Auto Mode の GPU 管理料金を最大 60% 削減したことを反映
- 2026-07-11: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.14.0 リリース（CapacityBuffers API など）を反映
- 2026-07-11: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — CloudWatch Application Signals Service Events を反映
- 2026-07-11: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.4.5 パッチリリースを反映
- 2026-07-11: 該当するドキュメントなし — ingress-nginx の廃止（2026 年 3 月）を理解する、CNCF ブログ（[出典](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/)）
- 2026-07-11: 該当するドキュメントなし — Cloud Native AI における CNCF Data Storage ホワイトペーパーを公開（[出典](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/)）
- 2026-07-11: 該当するドキュメントなし — Amazon EMR on EKS が Apache Spark トラブルシューティングエージェントをサポート（[出典](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/)）
- 2026-07-11: 該当するドキュメントなし — AWS Systems Manager のハイブリッド/マルチクラウドノード料金体系を刷新（Advanced Instances Tier を廃止）（[出典](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/))
