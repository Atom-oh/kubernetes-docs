# ニュース
> **最終更新**: August 17, 2026

Kubernetes、Amazon EKS、CNCF エコシステムのニュースは、ここでは個別のダイジェスト文書として収集していません。毎週、GitHub Actions が関連ニュースを対応する既存のドキュメントに直接適用し、この更新ログには変更されたドキュメントとその理由のみを記録します。対応するドキュメントがないニュースは、リンクのみここに記録します。

## 更新ログ

- 2026-W34: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.5.0 GA リリースおよび v3.5.1/v3.4.7/v3.3.14 パッチリリースを適用
- 2026-W34: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.0-beta.1 リリース（1.31 がベータに移行）を適用
- 2026-W34: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.8.2（Gateway API 1.5.1 サポート、テスト済み最大 k8s 1.36）を適用
- 2026-W34: 対応するドキュメントなし — Amazon EKS が高度な Kubernetes control plane 設定パラメータ（scheduler/controller manager/API server のチューニング）をサポート開始（[出典](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-control-plane-configuration-parameters)）
- 2026-W34: 対応するドキュメントなし — Cloud Native Buildpacks が CNCF の卒業プロジェクトに昇格（[出典](https://www.cncf.io/announcements/2026/08/11/cncf-announces-graduation-of-cloud-native-buildpacks-advancing-the-standard-for-container-builds/)）
- 2026-W34: 対応するドキュメントなし — KubeCon + CloudNativeCon North America 2026 のスケジュールが公開され、新たに AI Inference + Agentic トラックを追加（[出典](https://www.cncf.io/announcements/2026/08/10/cncf-reveals-kubecon-cloudnativecon-north-america-2026-schedule-adds-new-ai-inference-agentic-track/)）
- 2026-W34: 対応するドキュメントなし — Kubernetes YAML を KYAML として整形出力する方法、Kubernetes ブログ（[出典](https://kubernetes.io/blog/2026/08/11/how-to-pretty-print-kubernetes-yaml-as-kyaml/)）
- 2026-W33: [networking/04-gateway-api.md](../networking/04-gateway-api.md) — Gateway API v1.6（TCPRoute/UDPRoute が Standard v1 に昇格、実験的リソースが x-k8s.io API グループへ移動）を適用
- 2026-W33: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.5.0 GA（Helm 4 移行、source integrity verification alpha、ApplicationSet の改善）を適用
- 2026-W33: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.0 GA（Gateway API v1.6.1、KCNP、multi-pool IPAM 移行）および 1.21.0-pre.0 を適用
- 2026-W33: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37 の先行公開、Docs Freeze の発効、および v1.38.0-alpha.0 タグを適用
- 2026-W33: 対応するドキュメントなし — Amazon ECR が Docker push 向けに最大 200 GB の image layer をサポート開始（[出典](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-ecr-image-layers/)）
- 2026-W33: 対応するドキュメントなし — K8gb が CNCF のインキュベーティングプロジェクトに昇格（[出典](https://www.cncf.io/announcements/2026/08/05/k8gb-becomes-a-cncf-incubating-project/)）
- 2026-W33: 対応するドキュメントなし — OpenCost 1.121.0 が Kubernetes inference cost tracking を追加（[出典](https://www.cncf.io/blog/2026/08/05/opencost-1-121-0-first-of-a-kind-kubernetes-inference-cost-tracking/)）
- 2026-W33: 対応するドキュメントなし — Kubernetes DRA は HAMi を置き換えるか？、CNCF ブログ（[出典](https://www.cncf.io/blog/2026/08/07/does-kubernetes-dra-replace-hami/)）
- 2026-W31: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.36.3/v1.35.7/v1.34.10 パッチリリースおよび v1.37 Code Freeze の発効を適用
- 2026-W31: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — EKS Auto Mode node pool 向けの EFA および EC2 placement group サポートを適用
- 2026-W31: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter node pool 向けの EFA および EC2 placement group サポートを適用
- 2026-W31: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — AMP 制限引き上げ（1.5B active series、workspace あたり 200K rules）を適用
- 2026-W31: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — OpenTelemetry の CNCF 卒業を適用
- 2026-W31: [networking/calico/README.md](../networking/calico/README.md) — Tigera による Kubernetes 上の Calico for VMs のローンチ（eBPF ベースの VM+container 統合ネットワーク）を適用
- 2026-W31: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.0-rc.1 release candidate を適用
- 2026-W31: 対応するドキュメントなし — Confidential Containers が CNCF のインキュベーティングプロジェクトに昇格（[出典](https://www.cncf.io/blog/2026/07/22/confidential-containers-becomes-a-cncf-incubating-project/)）
- 2026-W31: 対応するドキュメントなし — Kubernetes CSI driver における twin path traversal CVE（CVE-2026-3864 NFS / CVE-2026-3865 SMB、csi-driver-nfs v4.13.1 および csi-driver-smb v1.20.1 で修正）（[出典](https://www.sentinelone.com/blog/mount-here-read-there-twin-path-traversal-cves-in-kubernetes-storage/)）
- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.19.6/1.18.12/1.17.18 パッチリリースおよび CVE-2026-56743（ipBlock NetworkPolicy の問題）を適用
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.30.3/1.29.6 パッチリリースを適用
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.7.1（未定義の Service port への request を禁止、破壊的変更）を適用
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — EKS Auto Mode 向けの ARC zonal shift/autoshift サポートを適用
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — EKS Auto Mode 向けの ARC zonal shift サポートを適用
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — すべてのメンテナンス対象ラインにまたがる Karpenter パッチリリースの協調（v1.3.8–v1.11.3）を適用
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37.0-beta.0 および v1.37 リリーススケジュールを適用
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCon Japan 2026 および今後の Argo CD 3.5 ロードマップセッションを適用
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — Kubernetes ブログの custom metrics exporter ガイドを適用
- 2026-W30: 対応するドキュメントなし — HAMi が CNCF のインキュベーティングプロジェクトに昇格（[出典](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/)）
- 2026-W30: 対応するドキュメントなし — vLLM を使用して Kubernetes で self-hosted LLM を実行、CNCF ブログ（[出典](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/)）
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — ACME protocol 向けの ACM サポート（ACM public certificate を cert-manager から利用可能）を適用
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — AI agent 向けの NGINX + OpenTelemetry network-boundary observability パターンを適用
- 2026-W29: 対応するドキュメントなし — AI-native workload 向け platform engineering の進化、CNCF ブログ（[出典](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/)）
- 2026-07-11: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — etcd v3.7.0 リリース（RangeStream など）を適用
- 2026-07-11: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — EKS Auto Mode の GPU management fee を最大 60% 削減を適用
- 2026-07-11: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.14.0 リリース（CapacityBuffers API など）を適用
- 2026-07-11: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — CloudWatch Application Signals Service Events を適用
- 2026-07-11: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.4.5 パッチリリースを適用
- 2026-07-11: 対応するドキュメントなし — ingress-nginx の廃止への対応（2026年3月）、CNCF ブログ（[出典](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/)）
- 2026-07-11: 対応するドキュメントなし — CNCF の Cloud Native AI における Data Storage ホワイトペーパーを公開（[出典](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/)）
- 2026-07-11: 対応するドキュメントなし — Amazon EMR on EKS が Apache Spark troubleshooting agent をサポート開始（[出典](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/)）
- 2026-07-11: 対応するドキュメントなし — AWS Systems Manager の hybrid/multicloud node 料金改定（Advanced Instances Tier を廃止）（[出典](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/)）
