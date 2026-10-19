# ニュース
> **最終更新日**: 2026年10月19日

このページでは、Kubernetes、Amazon EKS、CNCFのニュースを受けて行ったドキュメントの変更を記録しています。GitHub Actionsは毎週月曜日の09:00 KSTに更新を準備し、品質ゲートを通過するとPRを作成します。変更はレビュー、マージ、デプロイ後にサイトへ反映されます。

週ラベルはログエントリーの週を示しており、情報源の公開日とは異なる場合があります。これらは過去の記録です。現在のサポート状況、セキュリティパッチ、運用要件については、リンク先のガイドと公式情報を確認してください。「該当するドキュメントなし」は、その時点で自動照合の結果、該当するドキュメントがなかったことを示します。

<!-- news-dashboard -->

<details class="news-log">
<summary>更新ログ全体を表示</summary>

## 更新ログ

- 2026-W43: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.2/1.30.6/1.29.9のパッチリリースを公開（ISTIO-SECURITY-2026-007セキュリティパッチを含む。このパッチは以前のレビューでドキュメントにすでに反映済み）([情報源](https://istio.io/news/releases/1.31.x/announcing-1.31.2/))
- 2026-W43: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.3/1.19.9/1.18.15のパッチリリースを反映（conntrack GCや`nodeSelector`を含むCNPの処理などのバグ修正）([情報源](https://github.com/cilium/cilium/releases/tag/v1.20.3))
- 2026-W43: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.5.5/v3.4.11/v3.3.16のバグ修正パッチリリースを反映 ([情報源](https://github.com/argoproj/argo-cd/releases/tag/v3.5.5))
- 2026-W43: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.6.0-rc3のリリース候補を反映 ([情報源](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc3))
- 2026-W43: [security/14-waf-edge-api-security.md](../security/14-waf-edge-api-security.md) — CloudFront VPC originsのデュアルスタック（IPv6）サポートの発表を反映 ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/10/cloudfront-vpc-origin-dualstack/))
- 2026-W43: [blockchain/01-fundamentals.md](../blockchain/01-fundamentals.md) — AWS上のBlockchain Snapshotsの提供開始を反映（Ethereum/Solanaノードのブートストラップ用に、同期済みスナップショットを無料で提供）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/10/blockchain-snapshots-node-bootstrapping/))
- 2026-W43: [security/01-kyverno-policy-management.md](../security/01-kyverno-policy-management.md) — Kyverno向けNirmata Runtimeを紹介するCNCFブログを反映（eBPF/LSMを介したカーネルレベルのランタイムポリシー適用）([情報源](https://www.cncf.io/blog/2026/10/15/extending-kubernetes-policy-enforcement-to-runtime-security-for-ai-workloads/))
- 2026-W43: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — Software Carbon Intensity（SCI）をOpenTelemetryのセマンティック規約として扱う提案を紹介するCNCFブログを反映 ([情報源](https://www.cncf.io/blog/2026/10/15/carbon-as-a-first-class-signal-bringing-software-carbon-intensity-to-opentelemetry/))
- 2026-W43: 該当するドキュメントなし — Headlampを使ってKueue管理下のJobのアドミッション状態を追跡する方法、Kubernetesブログ ([情報源](https://kubernetes.io/blog/2026/10/14/tracing-kueue-admission-with-headlamp/))
- 2026-W42: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.15.0リリースを反映（再起動をサポートする任意の中断としてのノード修復、KubeletConfigurationでのCEL、DRAサポートの拡大など）
- 2026-W42: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.5.4/v3.4.10/v3.3.15のセキュリティパッチリリースを反映（repo-serverのコマンド実行を含む4件の重大（CRITICAL）な問題、CVE-2026-77459）
- 2026-W42: [kernel/01-container-primitives.md](../kernel/01-container-primitives.md) — cgroup v1の非推奨化に関するKubernetesブログの状況を反映（v1.35から`failCgroupV1`のデフォルト値が`true`）
- 2026-W42: 該当するドキュメントなし — NVMe SSDベースのノードスワップを使用したKubernetesワークロードのスケーリング（v1.34でGA）、Kubernetesブログ ([情報源](https://kubernetes.io/blog/2026/10/05/scaling-kubernetes-workloads-with-node-swap/))
- 2026-W42: 該当するドキュメントなし — MesheryがCNCFのインキュベーションプロジェクトに ([情報源](https://www.cncf.io/blog/2026/10/07/meshery-becomes-a-cncf-incubating-project/))
- 2026-W42: 該当するドキュメントなし — AWS BatchがAmazon EKSのアクセスエントリー認証に対応 ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/10/aws-batch-access-entries/))
- 2026-W41: [eks/08-eks-upgrades.md](../eks/08-eks-upgrades.md) — Amazon EKSおよびEKS DistroでのKubernetes 1.37サポートを反映（Metrics APIのGA、DRAデバイスタイントのGA、HPAのゼロへのスケールがベータ）
- 2026-W41: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD 4.0のビジョン策定開始とArgoCon North America 2026のニュースを反映
- 2026-W41: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — OTel、Kafka、Flinkを活用したAtlassianのインシデント検出再構築を反映（CNCFブログ）
- 2026-W41: 該当するドキュメントなし — Amazon ECSがブルー/グリーン、リニア、カナリアデプロイにAmazon VPC Latticeのサポートを追加 ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/10/amazon-ecs-vpc-lattice-blue-green-deployments))
- 2026-W41: 該当するドキュメントなし — Amazon Managed GrafanaがGrafana 13.2のワークスペース作成に対応 ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-managed-grafana-now-supports-creating-grafana-13-2-workspaces))
- 2026-W41: 該当するドキュメントなし — Grafana Tempo 3.1リリース（Kafkaの新機能、TraceQLメトリクスの更新、トレースの機微情報のマスキングなど）([情報源](https://grafana.com/blog/tempo-3-1-release-all-the-latest-features))
- 2026-W41: 該当するドキュメントなし — ゲートではなくガードレール：プラットフォームチームにおけるポリシーの再考、CNCFブログ ([情報源](https://www.cncf.io/blog/2026/10/01/guardrails-not-gates-rethinking-policy-in-platform-teams/))
- 2026-W40: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37.1/v1.36.5/v1.35.9/v1.34.12のパッチリリースと、v1.37のPVC `Unused`状態（ベータ）に関するブログ記事を反映
- 2026-W40: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.1/1.30.5/1.29.8のパッチリリースを反映（BackendTLSPolicyのフェイルオープンに関するセキュリティ修正GHSA-qm8v-g4f9-qhjxを含む）
- 2026-W40: [eks/04-eks-storage-part1.md](../eks/04-eks-storage-part1.md) — EFS CSIドライバーのマウントオプション注入の脆弱性CVE-2026-6437を反映（v3.0.1で修正）
- 2026-W40: [ai-ml/08-llm-gateway.md](../ai-ml/08-llm-gateway.md) — Amazon SageMaker HyperPod Inference Gatewayの提供開始を反映（EKS管理アドオン、GPUを考慮したルーティング）
- 2026-W40: 該当するドキュメントなし — Amazon EMR on EKSがIPv6対応のAmazon EKSクラスターに対応 ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-emr-eks-ipv6-support))
- 2026-W40: 該当するドキュメントなし — Spark Connectを使ってAmazon EMR on EKSで対話型ワークロードを実行 ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/09/emr-eks-spark-connect-interactive/))
- 2026-W40: 該当するドキュメントなし — Amazon CloudWatch Omniが一般提供開始（AIファーストのオブザーバビリティ体験、OpenTelemetryとの相互運用性）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-cloudwatch-omni-ai/))
- 2026-W39: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37の3つの機能を詳しく解説する記事を反映（Memory QoSベータ、PodレベルのResource Managerベータ、emptyDirの権限とバインドマウントのオプション）
- 2026-W39: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.2/1.19.8/1.18.14のパッチリリースとCNCFブログの1.20機能まとめを反映
- 2026-W39: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.5.3/v3.4.9のパッチリリースとv3.6.0-rc1を反映
- 2026-W39: 該当するドキュメントなし — Kubernetes CSI Changed Block Tracking（CBT）APIがベータに昇格。アルファ版との違い、Kubernetesブログ ([情報源](https://kubernetes.io/blog/2026/09/14/csi-changed-block-tracking-beta/))
- 2026-W39: 該当するドキュメントなし — AWS Resilience Hubが3つの新機能を追加（名前空間内でEKSラベルに基づいてサービスリソースを検出する機能など）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/09/resilience-hub-eks-dependency-policy/))
- 2026-W38: [core/08-scheduling-preemption-eviction.md](../core/08-scheduling-preemption-eviction.md) — Kubernetes v1.37のインプレースPodリサイズに対するスケジューラーのプリエンプション（アルファ）と、Workload-Aware Schedulingの進展（Workload/PodGroupがベータ、CompositePodGroup API）を反映
- 2026-W38: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37のNodeライフサイクル状態を反映（ドレイン、メンテナンス、グレースフルシャットダウン向けの既知の状態5種類）
- 2026-W38: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — Kubernetes v1.37のコンポーネントメトリクス向けPrometheusネイティブヒストグラムを反映（ベータ、デフォルトで有効）
- 2026-W38: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.21.0-pre.2のプレリリースを反映（Gateway APIのセッション永続性、AWS管理プレフィックスリスト、デフォルトでのBPFマスカレード）
- 2026-W38: 該当するドキュメントなし — KarmadaがCNCFの卒業プロジェクトに ([情報源](https://www.cncf.io/announcements/2026/09/07/cloud-native-computing-foundation-announces-karmada-graduation/))
- 2026-W38: 該当するドキュメントなし — Kubernetesの災害復旧：再現可能な3つの障害シナリオから得られたガイダンス、CNCFブログ ([情報源](https://www.cncf.io/blog/2026/09/10/kubernetes-disaster-recovery-guidance-from-three-reproducible-failure-scenarios/))
- 2026-W38: 該当するドキュメントなし — AWS Private CA EKSアドオンおよびConnector for ADがAWS GovCloud（米国）で利用可能に ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/09/private-ca-eks-addon-ad-govcloud/))
- 2026-W36: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37「Garhwal」リリースを反映（Pod証明書/ClusterTrustBundlesがStable、Metrics APIのGA、kube-dnsとIPVSモードの非推奨化など）
- 2026-W36: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.30.4/1.29.7のセキュリティパッチリリースを反映（ISTIO-SECURITY-2026-006、EnvoyのCVE 13件）
- 2026-W36: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.5.2/v3.4.8のパッチリリースを反映
- 2026-W36: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.8.4を反映（TLSRoute APIバージョンのネゴシエーションなど）
- 2026-W36: 該当するドキュメントなし — Amazon EKSがクラスターあたり最大10個の外部OIDCアイデンティティプロバイダーに対応 ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-multiple-oidc-providers))
- 2026-W36: 該当するドキュメントなし — 急増前にスケールする：Kubernetes上のGPUワークロードに対する予測オートスケーリング、CNCFブログ ([情報源](https://www.cncf.io/blog/2026/08/28/scale-before-the-spike-predictive-autoscaling-for-gpu-workloads-on-kubernetes/))
- 2026-W36: 該当するドキュメントなし — KubernetesでAIファクトリーを構築する、CNCFブログ ([情報源](https://www.cncf.io/blog/2026/08/27/building-an-ai-factory-on-kubernetes/))
- 2026-W35: [gitops/argocd/README.md](../gitops/argocd/README.md) — Amazon EKS管理のArgo CD機能で、`argocd-cm` ConfigMapを介したカスタム設定をサポートする機能を反映
- 2026-W35: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.36.4/v1.35.8/v1.34.11のパッチリリースとv1.37.0-rc.1を反映
- 2026-W35: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.1/1.19.7/1.18.13のパッチリリースを反映
- 2026-W35: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.14.1のパッチリリースを反映
- 2026-W35: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.0-rc.0のリリースを反映（1.31がRC段階に移行）
- 2026-W35: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 遅いSQLクエリをOTelのスパン由来メトリクスにまとめるCNCFブログのガイドを反映
- 2026-W35: 該当するドキュメントなし — Amazon EKSがライフサイクル管理の自動化を伴う認証局（CA）のローテーションに対応 ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-certificate-authority-ca-rotation-automated-lifecycle-management))
- 2026-W35: 該当するドキュメントなし — KubeflowがCNCFを卒業 ([情報源](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/))
- 2026-W34: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.5.0のGAリリースとv3.5.1/v3.4.7/v3.3.14のパッチリリースを反映
- 2026-W34: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.0-beta.1のリリースを反映（1.31がベータ段階に移行）
- 2026-W34: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.8.2を反映（Gateway API 1.5.1サポート、テスト済みの最大Kubernetesバージョンは1.36）
- 2026-W34: 該当するドキュメントなし — Amazon EKSが高度なKubernetesコントロールプレーン設定パラメーターに対応（scheduler/controller manager/API serverのチューニング）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-control-plane-configuration-parameters))
- 2026-W34: 該当するドキュメントなし — Cloud Native BuildpacksがCNCFの卒業プロジェクトに ([情報源](https://www.cncf.io/announcements/2026/08/11/cncf-announces-graduation-of-cloud-native-buildpacks-advancing-the-standard-for-container-builds/))
- 2026-W34: 該当するドキュメントなし — KubeCon + CloudNativeCon North America 2026のスケジュールを公開、新たにAI Inference + Agenticトラックを追加 ([情報源](https://www.cncf.io/announcements/2026/08/10/cncf-reveals-kubecon-cloudnativecon-north-america-2026-schedule-adds-new-ai-inference-agentic-track/))
- 2026-W34: 該当するドキュメントなし — Kubernetes YAMLをKYAMLとして整形出力する方法、Kubernetesブログ ([情報源](https://kubernetes.io/blog/2026/08/11/how-to-pretty-print-kubernetes-yaml-as-kyaml/))
- 2026-W33: [networking/04-gateway-api.md](../networking/04-gateway-api.md) — Gateway API v1.6を反映（TCPRoute/UDPRouteがStandard v1に昇格、チャネル固有の非推奨API提供方法の変更）
- 2026-W33: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.5.0 GAを反映（Helm 4への移行、ソース整合性検証アルファ、ApplicationSetの改善）
- 2026-W33: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.0 GA（Gateway API v1.6.1、KCNP、マルチプールIPAMの移行）と1.21.0-pre.0を反映
- 2026-W33: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37の先行情報、Docs Freezeの適用開始、v1.38.0-alpha.0タグを反映
- 2026-W33: 該当するドキュメントなし — Amazon ECRがDocker pushで最大200 GBのイメージレイヤーに対応 ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-ecr-image-layers/))
- 2026-W33: 該当するドキュメントなし — K8gbがCNCFのインキュベーションプロジェクトに ([情報源](https://www.cncf.io/announcements/2026/08/05/k8gb-becomes-a-cncf-incubating-project/))
- 2026-W33: 該当するドキュメントなし — OpenCost 1.121.0でKubernetesの推論コスト追跡機能を追加 ([情報源](https://www.cncf.io/blog/2026/08/05/opencost-1-121-0-first-of-a-kind-kubernetes-inference-cost-tracking/))
- 2026-W33: 該当するドキュメントなし — Kubernetes DRAはHAMiに取って代わるのか？、CNCFブログ ([情報源](https://www.cncf.io/blog/2026/08/07/does-kubernetes-dra-replace-hami/))
- 2026-W31: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.36.3/v1.35.7/v1.34.10のパッチリリースと、v1.37のコードフリーズ適用開始を反映
- 2026-W31: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — EKS Auto ModeのノードプールでEFAとEC2プレイスメントグループのサポートを反映
- 2026-W31: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — KarpenterのノードプールでEFAとEC2プレイスメントグループのサポートを反映
- 2026-W31: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — AMPの上限引き上げを反映（アクティブシリーズ15億件、ワークスペースあたりルール20万件）
- 2026-W31: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — OpenTelemetryのCNCF卒業を反映
- 2026-W31: [networking/calico/README.md](../networking/calico/README.md) — Kubernetes上のVM向けTigera Calicoの提供開始を反映（eBPFベースのVMとコンテナの統合ネットワーク）
- 2026-W31: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.0-rc.1のリリース候補を反映
- 2026-W31: 該当するドキュメントなし — Confidential ContainersがCNCFのインキュベーションプロジェクトに ([情報源](https://www.cncf.io/blog/2026/07/22/confidential-containers-becomes-a-cncf-incubating-project/))
- 2026-W31: 該当するドキュメントなし — Kubernetes CSIドライバーでパストラバーサルのCVEが2件発見（CVE-2026-3864 NFS / CVE-2026-3865 SMB。csi-driver-nfs v4.13.1、csi-driver-smb v1.20.1で修正）([情報源](https://www.sentinelone.com/blog/mount-here-read-there-twin-path-traversal-cves-in-kubernetes-storage/))
- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.19.6/1.18.12/1.17.18のパッチリリースとCVE-2026-56743（ipBlock NetworkPolicyの問題）を反映
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.30.3/1.29.6のパッチリリースを反映
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.7.1を反映（未定義のServiceポートへのリクエストを拒否する破壊的変更）
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — EKS Auto ModeのARCゾーンシフト/自動シフトのサポートを反映
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — EKS Auto ModeのARCゾーンシフトサポートを反映
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 旧バージョン系列向けのKarpenterパッチリリース（v1.3.8–v1.11.3）を反映
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37.0-beta.0とv1.37のリリーススケジュールを反映
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCon Japan 2026と、開催予定のArgo CD 3.5ロードマップセッションを反映
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — Kubernetesブログのカスタムメトリクスエクスポーターガイドを反映
- 2026-W30: 該当するドキュメントなし — HAMiがCNCFのインキュベーションプロジェクトに ([情報源](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/))
- 2026-W30: 該当するドキュメントなし — vLLMを使ってKubernetes上でセルフホスト型LLMを実行する、CNCFブログ ([情報源](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/))
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — ACMEプロトコルのACMサポートを反映（ACMのパブリック証明書をcert-managerから利用可能に）
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — AIエージェント向けのNGINX + OpenTelemetryによるネットワーク境界のオブザーバビリティパターンを反映
- 2026-W29: 該当するドキュメントなし — AIネイティブワークロードに対応するプラットフォームエンジニアリングの進化、CNCFブログ ([情報源](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/))
- 2026-07-11: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — etcd v3.7.0リリースを反映（RangeStreamなど）
- 2026-07-11: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — EKS Auto ModeのGPU管理料金が最大60%引き下げられたことを反映
- 2026-07-11: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.14.0リリースを反映（CapacityBuffers APIなど）
- 2026-07-11: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — CloudWatch Application Signals Service Eventsを反映
- 2026-07-11: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.4.5のパッチリリースを反映
- 2026-07-11: 該当するドキュメントなし — ingress-nginxの廃止への対応（2026年3月）、CNCFブログ ([情報源](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/))
- 2026-07-11: 該当するドキュメントなし — CNCFの「クラウドネイティブAIにおけるデータストレージ」ホワイトペーパーを公開 ([情報源](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/))
- 2026-07-11: 該当するドキュメントなし — Amazon EMR on EKSがApache Sparkトラブルシューティングエージェントに対応 ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/))
- 2026-07-11: 該当するドキュメントなし — AWS Systems Managerのハイブリッド/マルチクラウドノードの料金体系を大幅改定（Advanced Instances Tierを廃止）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/))

</details>
