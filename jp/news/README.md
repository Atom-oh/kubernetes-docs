# ニュース
> **最終更新**: August 24, 2026

Kubernetes、Amazon EKS、CNCF エコシステムのニュースは、ここでは個別のダイジェスト文書にはまとめていません。毎週、GitHub Actions が関連ニュースを該当する既存ドキュメントに直接反映し、この更新ログには変更されたドキュメントとその理由のみを記録します。一致するドキュメントがないニュースは、リンクのみをここに記録します。

## 更新ログ

- 2026-W35: [gitops/argocd/README.md](../gitops/argocd/README.md) — Amazon EKS 管理 Argo CD 機能向けのカスタム設定サポート（`argocd-cm` ConfigMap 経由）を反映
- 2026-W35: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.36.4/v1.35.8/v1.34.11 パッチリリースおよび v1.37.0-rc.1 を反映
- 2026-W35: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.1/1.19.7/1.18.13 パッチリリースを反映
- 2026-W35: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.14.1 パッチリリースを反映
- 2026-W35: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.0-rc.0 リリース（1.31 が RC に移行）を反映
- 2026-W35: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 遅い SQL クエリを OTel span 派生メトリクスに要約する CNCF ブログのガイドを反映
- 2026-W35: 一致するドキュメントなし — Amazon EKS が、自動ライフサイクル管理による認証局（CA）ローテーションをサポート開始 ([source](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-certificate-authority-ca-rotation-automated-lifecycle-management))
- 2026-W35: 一致するドキュメントなし — Kubeflow が CNCF 内で卒業 ([source](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/))
- 2026-W34: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.5.0 GA リリースおよび v3.5.1/v3.4.7/v3.3.14 パッチリリースを反映
- 2026-W34: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.0-beta.1 リリース（1.31 が beta に移行）を反映
- 2026-W34: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.8.2（Gateway API 1.5.1 サポート、テスト済み最大 k8s 1.36）を反映
- 2026-W34: 一致するドキュメントなし — Amazon EKS が高度な Kubernetes control plane 設定パラメータ（scheduler/controller manager/API server のチューニング）をサポート開始 ([source](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-control-plane-configuration-parameters))
- 2026-W34: 一致するドキュメントなし — Cloud Native Buildpacks が CNCF の卒業プロジェクトに ([source](https://www.cncf.io/announcements/2026/08/11/cncf-announces-graduation-of-cloud-native-buildpacks-advancing-the-standard-for-container-builds/))
- 2026-W34: 一致するドキュメントなし — KubeCon + CloudNativeCon North America 2026 のスケジュールを公開し、新しい AI Inference + Agentic トラックを追加 ([source](https://www.cncf.io/announcements/2026/08/10/cncf-reveals-kubecon-cloudnativecon-north-america-2026-schedule-adds-new-ai-inference-agentic-track/))
- 2026-W34: 一致するドキュメントなし — Kubernetes YAML を KYAML として整形出力する方法、Kubernetes ブログ ([source](https://kubernetes.io/blog/2026/08/11/how-to-pretty-print-kubernetes-yaml-as-kyaml/))
- 2026-W33: [networking/04-gateway-api.md](../networking/04-gateway-api.md) — Gateway API v1.6（TCPRoute/UDPRoute が Standard v1 に卒業、experimental リソースが x-k8s.io API group に移動）を反映
- 2026-W33: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.5.0 GA（Helm 4 移行、source integrity verification alpha、ApplicationSet 改善）を反映
- 2026-W33: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.0 GA（Gateway API v1.6.1、KCNP、multi-pool IPAM migration）および 1.21.0-pre.0 を反映
- 2026-W33: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37 の先行紹介、Docs Freeze の発効、および v1.38.0-alpha.0 タグを反映
- 2026-W33: 一致するドキュメントなし — Amazon ECR が Docker push 向けに最大 200 GB のイメージレイヤーをサポート開始 ([source](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-ecr-image-layers/))
- 2026-W33: 一致するドキュメントなし — K8gb が CNCF インキュベーションプロジェクトに ([source](https://www.cncf.io/announcements/2026/08/05/k8gb-becomes-a-cncf-incubating-project/))
- 2026-W33: 一致するドキュメントなし — OpenCost 1.121.0 が Kubernetes inference cost tracking を追加 ([source](https://www.cncf.io/blog/2026/08/05/opencost-1-121-0-first-of-a-kind-kubernetes-inference-cost-tracking/))
- 2026-W33: 一致するドキュメントなし — Kubernetes DRA は HAMi を置き換えるのか？、CNCF ブログ ([source](https://www.cncf.io/blog/2026/08/07/does-kubernetes-dra-replace-hami/))
- 2026-W31: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.36.3/v1.35.7/v1.34.10 パッチリリースおよび v1.37 Code Freeze の発効を反映
- 2026-W31: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — EKS Auto Mode node pool 向けの EFA および EC2 placement group サポートを反映
- 2026-W31: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter node pool 向けの EFA および EC2 placement group サポートを反映
- 2026-W31: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — AMP 制限引き上げ（1.5B active series、workspace あたり 200K rules）を反映
- 2026-W31: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — OpenTelemetry の CNCF 卒業を反映
- 2026-W31: [networking/calico/README.md](../networking/calico/README.md) — Tigera の Kubernetes 上の VM 向け Calico のローンチ（eBPF ベースの VM+container 統合ネットワーク）を反映
- 2026-W31: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.0-rc.1 リリース候補を反映
- 2026-W31: 一致するドキュメントなし — Confidential Containers が CNCF インキュベーションプロジェクトに ([source](https://www.cncf.io/blog/2026/07/22/confidential-containers-becomes-a-cncf-incubating-project/))
- 2026-W31: 一致するドキュメントなし — Kubernetes CSI driver の twin path traversal CVE（CVE-2026-3864 NFS / CVE-2026-3865 SMB、csi-driver-nfs v4.13.1 および csi-driver-smb v1.20.1 で修正） ([source](https://www.sentinelone.com/blog/mount-here-read-there-twin-path-traversal-cves-in-kubernetes-storage/))
- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.19.6/1.18.12/1.17.18 パッチリリースおよび CVE-2026-56743（ipBlock NetworkPolicy の問題）を反映
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.30.3/1.29.6 パッチリリースを反映
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.7.1（未定義 Service port へのリクエストを禁止、破壊的変更）を反映
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — EKS Auto Mode 向けの ARC zonal shift/autoshift サポートを反映
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — EKS Auto Mode 向けの ARC zonal shift サポートを反映
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 保守対象の全ラインにわたる協調的な Karpenter パッチリリース（v1.3.8–v1.11.3）を反映
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37.0-beta.0 および v1.37 リリーススケジュールを反映
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCon Japan 2026 および今後の Argo CD 3.5 ロードマップセッションを反映
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — Kubernetes ブログの custom metrics exporter ガイドを反映
- 2026-W30: 一致するドキュメントなし — HAMi が CNCF インキュベーションプロジェクトに ([source](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/))
- 2026-W30: 一致するドキュメントなし — vLLM を使用して Kubernetes で self-hosted LLM を実行、CNCF ブログ ([source](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/))
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — ACME protocol 向けの ACM サポート（ACM public certificate を cert-manager から利用可能に）を反映
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — AI agent 向けの NGINX + OpenTelemetry network-boundary observability パターンを反映
- 2026-W29: 一致するドキュメントなし — AI-native workload 向け platform engineering の進化、CNCF ブログ ([source](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/))
- 2026-07-11: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — etcd v3.7.0 リリース（RangeStream など）を反映
- 2026-07-11: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — EKS Auto Mode の GPU 管理料金を最大 60% 削減を反映
- 2026-07-11: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.14.0 リリース（CapacityBuffers API など）を反映
- 2026-07-11: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — CloudWatch Application Signals Service Events を反映
- 2026-07-11: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.4.5 パッチリリースを反映
- 2026-07-11: 一致するドキュメントなし — ingress-nginx の廃止への対応（2026 年 3 月）、CNCF ブログ ([source](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/))
- 2026-07-11: 一致するドキュメントなし — CNCF Data Storage in Cloud Native AI ホワイトペーパーを公開 ([source](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/))
- 2026-07-11: 一致するドキュメントなし — Amazon EMR on EKS が Apache Spark トラブルシューティング agent をサポート開始 ([source](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/))
- 2026-07-11: 一致するドキュメントなし — AWS Systems Manager の hybrid/multicloud node 料金体系を刷新（Advanced Instances Tier を廃止） ([source](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/))
