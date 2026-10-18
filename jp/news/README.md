# ニュース
> **最終更新**: 2026年10月12日

このページは、Kubernetes、Amazon EKS、CNCF のニュースを受けて実施したドキュメント変更を記録しています。GitHub Actions は毎週月曜日の KST 09:00 に更新を準備し、品質ゲート通過後に PR を作成します。変更はレビュー、マージ、デプロイ後にサイトへ反映されます。

週ラベルはログエントリの週を表しており、ソースの公開日と異なる場合があります。これらは履歴記録です。現在のサポート、セキュリティパッチ、運用要件については、リンク先のガイドと公式ソースを参照してください。「該当ドキュメントなし」は、その時点の自動照合結果を示します。

<!-- news-dashboard -->

<details class="news-log">
<summary>更新ログ全体を展開する</summary>

## 更新ログ

- 2026-W42: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.15.0 リリースを反映（再起動をサポートする自発的な中断としてのノード修復、KubeletConfiguration での CEL、より広範な DRA サポートなど）
- 2026-W42: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.5.4/v3.4.10/v3.3.15 のセキュリティパッチリリースを反映（repo-server でのコマンド実行、CVE-2026-77459 を含む 4 件の CRITICAL 問題）
- 2026-W42: [kernel/01-container-primitives.md](../kernel/01-container-primitives.md) — Kubernetes ブログの cgroup v1 非推奨ステータスを反映（`failCgroupV1` は v1.35 からデフォルトで `true`）
- 2026-W42: 該当ドキュメントなし — NVMe SSD 搭載ノードスワップによる Kubernetes ワークロードのスケーリング（v1.34 で GA）、Kubernetes ブログ（[出典](https://kubernetes.io/blog/2026/10/05/scaling-kubernetes-workloads-with-node-swap/)）
- 2026-W42: 該当ドキュメントなし — Meshery が CNCF インキュベーティングプロジェクトに昇格（[出典](https://www.cncf.io/blog/2026/10/07/meshery-becomes-a-cncf-incubating-project/)）
- 2026-W42: 該当ドキュメントなし — AWS Batch が Amazon EKS アクセスエントリ認証をサポート開始（[出典](https://aws.amazon.com/about-aws/whats-new/2026/10/aws-batch-access-entries/)）
- 2026-W41: [eks/08-eks-upgrades.md](../eks/08-eks-upgrades.md) — Amazon EKS および EKS Distro での Kubernetes 1.37 サポートを反映（Metrics API の GA、DRA デバイス taint の GA、HPA のゼロスケールの Beta）
- 2026-W41: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD 4.0 のビジョン策定開始と ArgoCon North America 2026 のニュースを反映
- 2026-W41: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — OTel、Kafka、Flink による Atlassian のインシデント検知再構築を反映（CNCF ブログ）
- 2026-W41: 該当ドキュメントなし — Amazon ECS がブルー/グリーン、リニア、カナリアデプロイメント向けの Amazon VPC Lattice サポートを追加（[出典](https://aws.amazon.com/about-aws/whats-new/2026/10/amazon-ecs-vpc-lattice-blue-green-deployments)）
- 2026-W41: 該当ドキュメントなし — Amazon Managed Grafana が Grafana 13.2 ワークスペースの作成をサポート開始（[出典](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-managed-grafana-now-supports-creating-grafana-13-2-workspaces)）
- 2026-W41: 該当ドキュメントなし — Grafana Tempo 3.1 リリース（新しい Kafka 機能、TraceQL メトリクスの更新、トレースのマスキングなど）（[出典](https://grafana.com/blog/tempo-3-1-release-all-the-latest-features)）
- 2026-W41: 該当ドキュメントなし — ゲートではなくガードレール: プラットフォームチームにおけるポリシーの再考、CNCF ブログ（[出典](https://www.cncf.io/blog/2026/10/01/guardrails-not-gates-rethinking-policy-in-platform-teams/)）
- 2026-W40: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37.1/v1.36.5/v1.35.9/v1.34.12 のパッチリリースおよび v1.37 PVC の `Unused` 条件（Beta）に関するブログ記事を反映
- 2026-W40: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.1/1.30.5/1.29.8 のパッチリリースを反映（BackendTLSPolicy fail-open セキュリティ修正 GHSA-qm8v-g4f9-qhjx を含む）
- 2026-W40: [eks/04-eks-storage-part1.md](../eks/04-eks-storage-part1.md) — EFS CSI ドライバーのマウントオプションインジェクション脆弱性 CVE-2026-6437 を反映（v3.0.1 で修正）
- 2026-W40: [ai-ml/08-llm-gateway.md](../ai-ml/08-llm-gateway.md) — Amazon SageMaker HyperPod Inference Gateway のローンチを反映（EKS のマネージドアドオン、GPU 対応ルーティング）
- 2026-W40: 該当ドキュメントなし — Amazon EMR on EKS が IPv6 Amazon EKS クラスターをサポート開始（[出典](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-emr-eks-ipv6-support)）
- 2026-W40: 該当ドキュメントなし — Spark Connect を使用して Amazon EMR on EKS でインタラクティブワークロードを実行（[出典](https://aws.amazon.com/about-aws/whats-new/2026/09/emr-eks-spark-connect-interactive/)）
- 2026-W40: 該当ドキュメントなし — Amazon CloudWatch Omni の一般提供開始（AI ファーストのオブザーバビリティ体験、OpenTelemetry 相互運用性）（[出典](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-cloudwatch-omni-ai/)）
- 2026-W39: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37 の 3 件の機能詳細解説を反映（Memory QoS Beta、Pod-Level Resource Managers Beta、emptyDir の権限と bind mount オプション）
- 2026-W39: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.2/1.19.8/1.18.14 のパッチリリースおよび CNCF ブログの 1.20 機能総括を反映
- 2026-W39: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.5.3/v3.4.9 のパッチリリースおよび v3.6.0-rc1 を反映
- 2026-W39: 該当ドキュメントなし — Kubernetes CSI Changed Block Tracking（CBT）API が Alpha との差異とともに Beta へ昇格、Kubernetes ブログ（[出典](https://kubernetes.io/blog/2026/09/14/csi-changed-block-tracking-beta/)）
- 2026-W39: 該当ドキュメントなし — AWS Resilience Hub が 3 つの新機能を追加（namespace 内での EKS ラベルベースの Service リソース検出を含む）（[出典](https://aws.amazon.com/about-aws/whats-new/2026/09/resilience-hub-eks-dependency-policy/)）
- 2026-W38: [core/08-scheduling-preemption-eviction.md](../core/08-scheduling-preemption-eviction.md) — インプレース Pod リサイズ向け Kubernetes v1.37 スケジューラーのプリエンプション（Alpha）および Workload-Aware Scheduling の進展（Workload/PodGroup Beta、CompositePodGroup API）を反映
- 2026-W38: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37 ノードのライフサイクル条件を反映（drain、メンテナンス、graceful shutdown 向けの既知の 5 条件）
- 2026-W38: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — Kubernetes v1.37 コンポーネントメトリクス向け Prometheus ネイティブヒストグラムを反映（Beta、デフォルトで有効）
- 2026-W38: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.21.0-pre.2 プレリリースを反映（Gateway API セッション永続化、AWS マネージドプレフィックスリスト、デフォルトの BPF マスカレード）
- 2026-W38: 該当ドキュメントなし — Karmada が CNCF 卒業プロジェクトに昇格（[出典](https://www.cncf.io/announcements/2026/09/07/cloud-native-computing-foundation-announces-karmada-graduation/)）
- 2026-W38: 該当ドキュメントなし — Kubernetes 災害復旧: 3 つの再現可能な障害シナリオからのガイダンス、CNCF ブログ（[出典](https://www.cncf.io/blog/2026/09/10/kubernetes-disaster-recovery-guidance-from-three-reproducible-failure-scenarios/)）
- 2026-W38: 該当ドキュメントなし — AWS Private CA EKS add-on と Connector for AD が AWS GovCloud（US）で利用可能に（[出典](https://aws.amazon.com/about-aws/whats-new/2026/09/private-ca-eks-addon-ad-govcloud/)）
- 2026-W36: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37 "Garhwal" リリースを反映（Pod certificates/ClusterTrustBundles Stable、Metrics API GA、kube-dns および IPVS-mode の非推奨化など）
- 2026-W36: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.30.4/1.29.7 のセキュリティパッチリリースを反映（ISTIO-SECURITY-2026-006、13 件の Envoy CVE）
- 2026-W36: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.5.2/v3.4.8 のパッチリリースを反映
- 2026-W36: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.8.4 を反映（TLSRoute API バージョンネゴシエーションなど）
- 2026-W36: 該当ドキュメントなし — Amazon EKS がクラスターあたり最大 10 個の外部 OIDC アイデンティティプロバイダーをサポート開始（[出典](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-multiple-oidc-providers)）
- 2026-W36: 該当ドキュメントなし — ピーク前にスケール: Kubernetes 上の GPU ワークロード向け予測スケーリング、CNCF ブログ（[出典](https://www.cncf.io/blog/2026/08/28/scale-before-the-spike-predictive-autoscaling-for-gpu-workloads-on-kubernetes/)）
- 2026-W36: 該当ドキュメントなし — Kubernetes 上での AI ファクトリーの構築、CNCF ブログ（[出典](https://www.cncf.io/blog/2026/08/27/building-an-ai-factory-on-kubernetes/)）
- 2026-W35: [gitops/argocd/README.md](../gitops/argocd/README.md) — Amazon EKS マネージド Argo CD 機能向けのカスタム設定サポート（`argocd-cm` ConfigMap 経由）を反映
- 2026-W35: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.36.4/v1.35.8/v1.34.11 のパッチリリースおよび v1.37.0-rc.1 を反映
- 2026-W35: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.1/1.19.7/1.18.13 のパッチリリースを反映
- 2026-W35: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.14.1 パッチリリースを反映
- 2026-W35: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.0-rc.0 リリースを反映（1.31 が RC 入り）
- 2026-W35: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 低速な SQL クエリを OTel span 由来のメトリクスに抽出する CNCF ブログのガイドを反映
- 2026-W35: 該当ドキュメントなし — Amazon EKS が自動ライフサイクル管理による certificate authority（CA）ローテーションをサポート開始（[出典](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-certificate-authority-ca-rotation-automated-lifecycle-management)）
- 2026-W35: 該当ドキュメントなし — Kubeflow が CNCF 内で卒業（[出典](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/)）
- 2026-W34: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.5.0 GA リリースおよび v3.5.1/v3.4.7/v3.3.14 のパッチリリースを反映
- 2026-W34: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.0-beta.1 リリースを反映（1.31 が beta 入り）
- 2026-W34: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.8.2 を反映（Gateway API 1.5.1 サポート、テスト済み最大 k8s 1.36）
- 2026-W34: 該当ドキュメントなし — Amazon EKS が高度な Kubernetes コントロールプレーン設定パラメータをサポート開始（scheduler/controller manager/API server のチューニング）（[出典](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-control-plane-configuration-parameters)）
- 2026-W34: 該当ドキュメントなし — Cloud Native Buildpacks が CNCF 卒業プロジェクトに昇格（[出典](https://www.cncf.io/announcements/2026/08/11/cncf-announces-graduation-of-cloud-native-buildpacks-advancing-the-standard-for-container-builds/)）
- 2026-W34: 該当ドキュメントなし — KubeCon + CloudNativeCon North America 2026 のスケジュール公開、新しい AI Inference + Agentic トラックを追加（[出典](https://www.cncf.io/announcements/2026/08/10/cncf-reveals-kubecon-cloudnativecon-north-america-2026-schedule-adds-new-ai-inference-agentic-track/)）
- 2026-W34: 該当ドキュメントなし — Kubernetes YAML を KYAML で整形表示する方法、Kubernetes ブログ（[出典](https://kubernetes.io/blog/2026/08/11/how-to-pretty-print-kubernetes-yaml-as-kyaml/)）
- 2026-W33: [networking/04-gateway-api.md](../networking/04-gateway-api.md) — Gateway API v1.6 を反映（TCPRoute/UDPRoute が Standard v1 に昇格、チャネルごとに異なる非推奨 API の提供方法を変更）
- 2026-W33: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.5.0 GA を反映（Helm 4 移行、ソース整合性検証 alpha、ApplicationSet の改善）
- 2026-W33: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.0 GA（Gateway API v1.6.1、KCNP、マルチプール IPAM への移行）および 1.21.0-pre.0 を反映
- 2026-W33: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37 の先行紹介、Docs Freeze の発効、および v1.38.0-alpha.0 タグを反映
- 2026-W33: 該当ドキュメントなし — Amazon ECR が Docker push 向けに最大 200 GB のイメージレイヤーをサポート開始（[出典](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-ecr-image-layers/)）
- 2026-W33: 該当ドキュメントなし — K8gb が CNCF インキュベーティングプロジェクトに昇格（[出典](https://www.cncf.io/announcements/2026/08/05/k8gb-becomes-a-cncf-incubating-project/)）
- 2026-W33: 該当ドキュメントなし — OpenCost 1.121.0 が Kubernetes 推論コスト追跡を追加（[出典](https://www.cncf.io/blog/2026/08/05/opencost-1-121-0-first-of-a-kind-kubernetes-inference-cost-tracking/)）
- 2026-W33: 該当ドキュメントなし — Kubernetes DRA は HAMi を置き換えるのか？、CNCF ブログ（[出典](https://www.cncf.io/blog/2026/08/07/does-kubernetes-dra-replace-hami/)）
- 2026-W31: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.36.3/v1.35.7/v1.34.10 のパッチリリースおよび v1.37 Code Freeze の発効を反映
- 2026-W31: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — EKS Auto Mode のノードプール向け EFA および EC2 プレースメントグループのサポートを反映
- 2026-W31: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter のノードプール向け EFA および EC2 プレースメントグループのサポートを反映
- 2026-W31: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — AMP の上限引き上げを反映（アクティブな時系列数 15 億、ワークスペースあたりのルール数 20 万）
- 2026-W31: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — OpenTelemetry の CNCF 卒業を反映
- 2026-W31: [networking/calico/README.md](../networking/calico/README.md) — Kubernetes 上の VM 向け Tigera Calico の提供開始を反映（eBPF ベースで VM とコンテナを統合するネットワーキング）
- 2026-W31: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.0-rc.1 リリース候補を反映
- 2026-W31: 該当ドキュメントなし — Confidential Containers が CNCF インキュベーティングプロジェクトに昇格（[出典](https://www.cncf.io/blog/2026/07/22/confidential-containers-becomes-a-cncf-incubating-project/)）
- 2026-W31: 該当ドキュメントなし — Kubernetes CSI ドライバーにおける 2 件のパストラバーサル CVE（CVE-2026-3864 NFS / CVE-2026-3865 SMB、csi-driver-nfs v4.13.1 と csi-driver-smb v1.20.1 で修正）（[出典](https://www.sentinelone.com/blog/mount-here-read-there-twin-path-traversal-cves-in-kubernetes-storage/)）
- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.19.6/1.18.12/1.17.18 のパッチリリースおよび CVE-2026-56743（ipBlock NetworkPolicy の問題）を反映
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.30.3/1.29.6 のパッチリリースを反映
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.7.1 を反映（未定義の Service ポートへのリクエストを禁止、破壊的変更）
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — EKS Auto Mode 向け ARC zonal shift/autoshift サポートを反映
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — EKS Auto Mode 向け ARC zonal shift サポートを反映
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 旧系列向け Karpenter パッチリリースを反映（v1.3.8–v1.11.3）
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37.0-beta.0 および v1.37 リリーススケジュールを反映
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCon Japan 2026 および今後の Argo CD 3.5 ロードマップセッションを反映
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — Kubernetes ブログのカスタムメトリクスエクスポーターガイドを反映
- 2026-W30: 該当ドキュメントなし — HAMi が CNCF インキュベーティングプロジェクトに昇格（[出典](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/)）
- 2026-W30: 該当ドキュメントなし — vLLM を使用して Kubernetes でセルフホスト LLM を実行、CNCF ブログ（[出典](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/)）
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — ACME プロトコル向け ACM サポートを反映（ACM パブリック証明書を cert-manager から使用可能に）
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — AI エージェント向け NGINX + OpenTelemetry ネットワーク境界の可観測性パターンを反映
- 2026-W29: 該当ドキュメントなし — AI ネイティブワークロードに向けたプラットフォームエンジニアリングの進化、CNCF ブログ（[出典](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/)）
- 2026-07-11: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — etcd v3.7.0 リリースを反映（RangeStream など）
- 2026-07-11: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — EKS Auto Mode の GPU 管理料金を最大 60% 削減したことを反映
- 2026-07-11: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.14.0 リリースを反映（CapacityBuffers API など）
- 2026-07-11: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — CloudWatch Application Signals Service Events を反映
- 2026-07-11: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.4.5 パッチリリースを反映
- 2026-07-11: 該当ドキュメントなし — ingress-nginx の廃止への対応（2026 年 3 月）、CNCF ブログ（[出典](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/)）
- 2026-07-11: 該当ドキュメントなし — Cloud Native AI における CNCF Data Storage ホワイトペーパーを公開（[出典](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/)）
- 2026-07-11: 該当ドキュメントなし — Amazon EMR on EKS が Apache Spark トラブルシューティングエージェントをサポート開始（[出典](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/)）
- 2026-07-11: 該当ドキュメントなし — AWS Systems Manager のハイブリッド/マルチクラウドノード料金を刷新（Advanced Instances Tier を廃止）（[出典](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/)）

</details>
