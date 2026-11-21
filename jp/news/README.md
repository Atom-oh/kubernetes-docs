# ニュース
> **最終更新日**: 2026年11月19日

このページでは、Kubernetes、Amazon EKS、CNCFのニュースを受けて行ったドキュメントの変更を記録しています。GitHub Actionsは毎週月曜日の09:00 KSTに更新を準備し、品質ゲートを通過するとPRを作成します。変更はレビュー、マージ、デプロイの後にサイトへ反映されます。

週ラベルはログエントリーの週を示しており、情報源の公開日とは異なる場合があります。これらは過去の記録です。現在のサポート状況、セキュリティパッチ、運用要件については、リンク先のガイドと公式情報を確認してください。「該当ドキュメントなし」は、その時点で自動照合した結果を示します。

<!-- news-dashboard -->

<details class="news-log">
<summary>更新ログ全体を展開</summary>

## 更新ログ

- 2026-W47: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.32.0のGAリリースを反映（同じ週の1.31.4/1.30.8パッチリリースを含む）([情報源](https://istio.io/latest/news/releases/1.32.x/announcing-1.32/))
- 2026-W47: [eks-auto-mode/README.md](../eks-auto-mode/README.md) · [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — EKS Auto ModeおよびKarpenterでのNVIDIA GPUとEFAのDynamic Resource Allocation（DRA）サポートに関する発表を反映（KarpenterではすべてのKubernetesバージョン、Auto Modeでは1.36以降）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-eks-auto-mode-karpenter-dra/))
- 2026-W47: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — EKS Auto ModeでのPod向けセキュリティグループのサポートに関する発表を反映（個別のノードプールを設けずにPod単位のネットワーク分離を実現）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-eks-auto-mode-security-groups-for-pods/))
- 2026-W47: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Amazon EKS Provisioned Control Planeの4XL/8XLティアで、etcdデータベースが16 GBから24 GBに拡大したことを反映（EKS 1.34以降。既存クラスターは自動的にアップグレード）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-eks-provisioned-control-plane-larger-etcd-database/))
- 2026-W47: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.15.2のパッチリリースを反映（DRAのインスタンスタイプメタデータのみ。g7/g7eのNVIDIA GPUメタデータ追加、EFAメタデータの対象を29から302種類のインスタンスタイプに拡大、Go 1.26.11）([情報源](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.15.2))
- 2026-W47: 該当ドキュメントなし — AWS Nitro Sandboxesが提供開始。Nitro Hypervisorが管理する軽量VMで、内部で稼働するAIエージェントを含め、Amazon EKSのPod、ECSタスク、VMをハードウェアレベルで分離する ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/11/nitro-sandboxes-eks-ecs-ec2/))
- 2026-W47: [security/03-pod-security-standards.md](../security/03-pod-security-standards.md) — AWS Batch on Amazon EKSに、Linux capabilities、seccompプロファイル、Podレベルの設定などのKubernetesセキュリティコンテキストのサポートが追加されたことを反映（Pod Security Standardsのrestrictedプロファイルを適用するクラスターでジョブを実行可能）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/11/aws-batch-eks-security-context/))
- 2026-W47: 該当ドキュメントなし — PostgreSQL OperatorであるCloudNativePGがCNCFのインキュベーションプロジェクトに ([情報源](https://www.cncf.io/blog/2026/11/10/cloudnativepg-becomes-a-cncf-incubating-project/))
- 2026-W47: 該当ドキュメントなし — Rayワークロード向けKubernetes OperatorのKubeRayがCNCFに寄贈されることを発表 ([情報源](https://www.cncf.io/blog/2026/11/10/donating-kuberay-to-cncf/))
- 2026-W46: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.6.0のGAリリース（ApplicationSetの段階的同期に関するメトリクス/条件、設定可能なDexのストレージ/TLS設定など）と、その後の2026-11-04にリリースされたバグ修正パッチv3.6.1を反映 ([情報源](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0))
- 2026-W46: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.5.7/v3.4.13/v3.3.19のバグ修正パッチリリースを反映 ([情報源](https://github.com/argoproj/argo-cd/releases/tag/v3.5.7))
- 2026-W46: [eks/13-eks-capabilities.md](../eks/13-eks-capabilities.md) · [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD向けEKS CapabilityでのArgo CD Notificationsサポートを反映（Slack、Amazon SQS、EventBridgeを含む16サービス、IAM Capability Role認証、Secrets Managerの認証情報参照）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-eks-argo-cd-notifications/))
- 2026-W46: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — Prometheus 3.16.0のリリースを反映（平滑化/アンカー付きベクトルセレクターがStableに昇格、クエリコストの推定と実行制限がExperimentalに、`integral()`関数がExperimentalに、AgentモードのメタデータWALレコード）([情報源](https://github.com/prometheus/prometheus/releases/tag/v3.16.0))
- 2026-W46: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.21.0-pre.4のプレリリースを反映（BGPのunnumberedピアリング、BPF masqueradingのデフォルト有効化、Gateway APIのフロントエンドmTLSとリスナーTLSバージョンのオプション、複数プールのResource IPAM、Gateway API Inference Extension）([情報源](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.4))
- 2026-W46: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.38.0-beta.0のプレリリースを反映（v1.38最初のベータ版。GAは2026-12-16を予定）([情報源](https://github.com/kubernetes/kubernetes/releases/tag/v1.38.0-beta.0))
- 2026-W44: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.3/1.30.7/1.29.10のセキュリティパッチリリースを反映（ISTIO-SECURITY-2026-008、CVE-2026-111943：侵害されたeMudhra中間CA証明書を信頼しないように変更。1.29.10はEOL後の例外的なリリース）([情報源](https://istio.io/latest/news/security/istio-security-2026-008/))
- 2026-W44: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.4/1.19.10/1.18.16の帯域外セキュリティパッチリリースを反映（CVE-2026-111943。Go 1.26.10では侵害されたeMudhra中間CA証明書が信頼されなくなった）([情報源](https://github.com/cilium/cilium/releases/tag/v1.20.4))
- 2026-W44: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.5.6/v3.4.12/v3.3.17のバグ修正パッチリリースと、侵害されたeMudhra CA証明書への信頼を取り除くセキュリティ修正を含むv3.3.18を反映 ([情報源](https://github.com/argoproj/argo-cd/releases/tag/v3.3.18))
- 2026-W44: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.6.0-rc4のリリース候補版を反映 ([情報源](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc4))
- 2026-W44: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.15.1のパッチとv1.14.2/v1.14.3/v1.9.3のLTSパッチリリースを反映（バグ修正。すべての系列がGo 1.26.10に移行し、侵害されたeMudhra中間CA証明書が信頼されなくなった）([情報源](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.15.1))
- 2026-W44: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — OpenTelemetry CollectorでAIエージェントのテレメトリをフィルタリングし、削減する方法に関するCNCFブログのガイドを反映 ([情報源](https://www.cncf.io/blog/2026/10/22/filtering-and-reducing-ai-agent-telemetry-with-the-opentelemetry-collector/))
- 2026-W44: 該当ドキュメントなし — Amazon EMR on EKSのEMR料金（vCPU時間あたり、GB時間あたり）が30パーセント値下げ。基盤となるEKS料金に変更はなし ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/10/emr-eks-reduces-emr-charge-30-percent/))
- 2026-W44: 該当ドキュメントなし — AIワークロードがKubernetesのオートスケーリングをどのように変えているか、CNCFブログ ([情報源](https://www.cncf.io/blog/2026/10/19/how-ai-workloads-are-reshaping-kubernetes-autoscaling/))
- 2026-W43: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.2/1.30.6/1.29.9のパッチリリースが公開（ISTIO-SECURITY-2026-007のセキュリティパッチを含む。以前のレビューですでにドキュメントに反映済み）([情報源](https://istio.io/news/releases/1.31.x/announcing-1.31.2/))
- 2026-W43: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.3/1.19.9/1.18.15のパッチリリースを反映（conntrack GCや`nodeSelector`を含むCNPの処理に関するバグ修正）([情報源](https://github.com/cilium/cilium/releases/tag/v1.20.3))
- 2026-W43: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.5.5/v3.4.11/v3.3.16のバグ修正パッチリリースを反映 ([情報源](https://github.com/argoproj/argo-cd/releases/tag/v3.5.5))
- 2026-W43: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.6.0-rc3のリリース候補版を反映 ([情報源](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc3))
- 2026-W43: [security/14-waf-edge-api-security.md](../security/14-waf-edge-api-security.md) — CloudFront VPC originsのデュアルスタック（IPv6）サポートに関する発表を反映 ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/10/cloudfront-vpc-origin-dualstack/))
- 2026-W43: [blockchain/01-fundamentals.md](../blockchain/01-fundamentals.md) — AWSでのBlockchain Snapshotsの提供開始を反映（Ethereum/Solanaノードのブートストラップ向け、同期済みスナップショットを無料で提供）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/10/blockchain-snapshots-node-bootstrapping/))
- 2026-W43: [security/01-kyverno-policy-management.md](../security/01-kyverno-policy-management.md) — Kyverno向けNirmata Runtimeの紹介を掲載したCNCFブログを反映（eBPF/LSMを介したカーネルレベルのランタイムポリシー適用）([情報源](https://www.cncf.io/blog/2026/10/15/extending-kubernetes-policy-enforcement-to-runtime-security-for-ai-workloads/))
- 2026-W43: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — Software Carbon Intensity（SCI）をOpenTelemetryのセマンティック規約として扱う提案を掲載したCNCFブログを反映 ([情報源](https://www.cncf.io/blog/2026/10/15/carbon-as-a-first-class-signal-bringing-software-carbon-intensity-to-opentelemetry/))
- 2026-W43: 該当ドキュメントなし — Headlampを使ってKueue管理下のJobsのアドミッション状態を追跡する方法、Kubernetesブログ ([情報源](https://kubernetes.io/blog/2026/10/14/tracing-kueue-admission-with-headlamp/))
- 2026-W42: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.15.0のリリースを反映（再起動をサポートする、自発的な中断としてのノード修復、KubeletConfigurationでのCEL、DRAサポートの拡大など）
- 2026-W42: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.5.4/v3.4.10/v3.3.15のセキュリティパッチリリースを反映（repo-serverのコマンド実行、CVE-2026-77459を含む4件のCRITICAL問題）
- 2026-W42: [kernel/01-container-primitives.md](../kernel/01-container-primitives.md) — Kubernetesブログのcgroup v1非推奨化の状況を反映（v1.35から`failCgroupV1`のデフォルト値が`true`）
- 2026-W42: 該当ドキュメントなし — NVMe SSDを搭載したノードのスワップを使ってKubernetesワークロードをスケーリングする方法（v1.34でGA）、Kubernetesブログ ([情報源](https://kubernetes.io/blog/2026/10/05/scaling-kubernetes-workloads-with-node-swap/))
- 2026-W42: 該当ドキュメントなし — MesheryがCNCFのインキュベーションプロジェクトに ([情報源](https://www.cncf.io/blog/2026/10/07/meshery-becomes-a-cncf-incubating-project/))
- 2026-W42: 該当ドキュメントなし — AWS BatchがAmazon EKSのアクセスエントリー認証をサポート ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/10/aws-batch-access-entries/))
- 2026-W41: [eks/08-eks-upgrades.md](../eks/08-eks-upgrades.md) — Amazon EKSおよびEKS DistroでのKubernetes 1.37サポートを反映（Metrics APIがGA、DRA device taintsがGA、HPAのゼロへのスケールがベータ）
- 2026-W41: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD 4.0の構想策定の開始とArgoCon North America 2026のニュースを反映
- 2026-W41: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — OTel、Kafka、Flinkを基盤とするAtlassianのインシデント検出システム再構築を反映（CNCFブログ）
- 2026-W41: 該当ドキュメントなし — Amazon ECSがブルー/グリーン、リニア、カナリアのデプロイにAmazon VPC Latticeのサポートを追加 ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/10/amazon-ecs-vpc-lattice-blue-green-deployments))
- 2026-W41: 該当ドキュメントなし — Amazon Managed GrafanaがGrafana 13.2のワークスペース作成をサポート ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-managed-grafana-now-supports-creating-grafana-13-2-workspaces))
- 2026-W41: 該当ドキュメントなし — Grafana Tempo 3.1のリリース（新しいKafka機能、TraceQLメトリクスの更新、トレースの秘匿化など）([情報源](https://grafana.com/blog/tempo-3-1-release-all-the-latest-features))
- 2026-W41: 該当ドキュメントなし — ゲートではなくガードレール：プラットフォームチームのポリシーを再考する、CNCFブログ ([情報源](https://www.cncf.io/blog/2026/10/01/guardrails-not-gates-rethinking-policy-in-platform-teams/))
- 2026-W40: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37.1/v1.36.5/v1.35.9/v1.34.12のパッチリリースと、v1.37 PVCの`Unused`条件（ベータ）に関するブログ記事を反映
- 2026-W40: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.1/1.30.5/1.29.8のパッチリリースを反映（BackendTLSPolicyのフェイルオープンに関するセキュリティ修正GHSA-qm8v-g4f9-qhjxを含む）
- 2026-W40: [eks/04-eks-storage-part1.md](../eks/04-eks-storage-part1.md) — EFS CSI driverのマウントオプション注入の脆弱性CVE-2026-6437を反映（v3.0.1で修正）
- 2026-W40: [ai-ml/08-llm-gateway.md](../ai-ml/08-llm-gateway.md) — Amazon SageMaker HyperPod Inference Gatewayの提供開始を反映（EKS管理アドオン、GPUを考慮したルーティング）
- 2026-W40: 該当ドキュメントなし — Amazon EMR on EKSがIPv6のAmazon EKSクラスターをサポート ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-emr-eks-ipv6-support))
- 2026-W40: 該当ドキュメントなし — Spark Connectを使ってAmazon EMR on EKSでインタラクティブなワークロードを実行する ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/09/emr-eks-spark-connect-interactive/))
- 2026-W40: 該当ドキュメントなし — Amazon CloudWatch Omniが一般提供開始（AIを最優先したオブザーバビリティ体験、OpenTelemetryとの相互運用性）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-cloudwatch-omni-ai/))
- 2026-W39: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37の3つの機能を掘り下げた解説を反映（Memory QoSがベータ、Pod-Level Resource Managersがベータ、emptyDirの権限とbind mountのオプション）
- 2026-W39: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.2/1.19.8/1.18.14のパッチリリースと、CNCFブログの1.20機能まとめを反映
- 2026-W39: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.5.3/v3.4.9のパッチリリースとv3.6.0-rc1を反映
- 2026-W39: 該当ドキュメントなし — Kubernetes CSI Changed Block Tracking（CBT）APIがベータに昇格し、アルファ版との違いを解説、Kubernetesブログ ([情報源](https://kubernetes.io/blog/2026/09/14/csi-changed-block-tracking-beta/))
- 2026-W39: 該当ドキュメントなし — AWS Resilience Hubが3つの新機能を追加（EKSラベルに基づき、名前空間内でサービスリソースを検出する機能など）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/09/resilience-hub-eks-dependency-policy/))
- 2026-W38: [core/08-scheduling-preemption-eviction.md](../core/08-scheduling-preemption-eviction.md) — Kubernetes v1.37のインプレースPodリサイズ向けスケジューラープリエンプション（アルファ）と、Workload-Aware Schedulingの進展（Workload/PodGroupがベータ、CompositePodGroup API）を反映
- 2026-W38: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37のNodeライフサイクル条件を反映（ドレイン、メンテナンス、グレースフルシャットダウン向けの既知の条件5つ）
- 2026-W38: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — Kubernetes v1.37のコンポーネントメトリクスでのPrometheusネイティブヒストグラムを反映（ベータ、デフォルトで有効）
- 2026-W38: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.21.0-pre.2のプレリリースを反映（Gateway APIのセッション永続性、AWS管理プレフィックスリスト、BPF masqueradingのデフォルト有効化）
- 2026-W38: 該当ドキュメントなし — KarmadaがCNCFのGraduatedプロジェクトに ([情報源](https://www.cncf.io/announcements/2026/09/07/cloud-native-computing-foundation-announces-karmada-graduation/))
- 2026-W38: 該当ドキュメントなし — Kubernetesの災害復旧：再現可能な3つの障害シナリオから得たガイダンス、CNCFブログ ([情報源](https://www.cncf.io/blog/2026/09/10/kubernetes-disaster-recovery-guidance-from-three-reproducible-failure-scenarios/))
- 2026-W38: 該当ドキュメントなし — AWS Private CA EKSアドオンとConnector for ADがAWS GovCloud (US)で利用可能に ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/09/private-ca-eks-addon-ad-govcloud/))
- 2026-W36: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37「Garhwal」リリースを反映（Pod certificates/ClusterTrustBundlesがStable、Metrics APIがGA、kube-dnsとIPVSモードの非推奨化など）
- 2026-W36: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.30.4/1.29.7のセキュリティパッチリリースを反映（ISTIO-SECURITY-2026-006、EnvoyのCVE 13件）
- 2026-W36: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.5.2/v3.4.8のパッチリリースを反映
- 2026-W36: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.8.4を反映（TLSRoute APIバージョンのネゴシエーションなど）
- 2026-W36: 該当ドキュメントなし — Amazon EKSがクラスターあたり最大10個の外部OIDC IDプロバイダーをサポート ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-multiple-oidc-providers))
- 2026-W36: 該当ドキュメントなし — スパイクの前にスケールする：KubernetesのGPUワークロード向け予測的オートスケーリング、CNCFブログ ([情報源](https://www.cncf.io/blog/2026/08/28/scale-before-the-spike-predictive-autoscaling-for-gpu-workloads-on-kubernetes/))
- 2026-W36: 該当ドキュメントなし — Kubernetes上にAIファクトリーを構築する、CNCFブログ ([情報源](https://www.cncf.io/blog/2026/08/27/building-an-ai-factory-on-kubernetes/))
- 2026-W35: [gitops/argocd/README.md](../gitops/argocd/README.md) — Amazon EKS管理のArgo CD capabilityにおけるカスタム設定のサポートを反映（`argocd-cm` ConfigMap経由）
- 2026-W35: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.36.4/v1.35.8/v1.34.11のパッチリリースとv1.37.0-rc.1を反映
- 2026-W35: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.1/1.19.7/1.18.13のパッチリリースを反映
- 2026-W35: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.14.1のパッチリリースを反映
- 2026-W35: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.0-rc.0のリリースを反映（1.31がRC段階に移行）
- 2026-W35: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 遅いSQLクエリをOTelのspanから導出したメトリクスに要約する方法に関するCNCFブログのガイドを反映
- 2026-W35: 該当ドキュメントなし — Amazon EKSが自動ライフサイクル管理による認証局（CA）のローテーションをサポート ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-certificate-authority-ca-rotation-automated-lifecycle-management))
- 2026-W35: 該当ドキュメントなし — KubeflowがCNCF内でGraduatedに昇格 ([情報源](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/))
- 2026-W34: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.5.0のGAリリースとv3.5.1/v3.4.7/v3.3.14のパッチリリースを反映
- 2026-W34: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.0-beta.1のリリースを反映（1.31がベータ段階に移行）
- 2026-W34: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.8.2を反映（Gateway API 1.5.1をサポート、テスト済みのk8s最大バージョンは1.36）
- 2026-W34: 該当ドキュメントなし — Amazon EKSがKubernetesコントロールプレーンの高度な設定パラメーターをサポート（scheduler/controller manager/API serverのチューニング）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-control-plane-configuration-parameters))
- 2026-W34: 該当ドキュメントなし — Cloud Native BuildpacksがCNCFのGraduatedプロジェクトに ([情報源](https://www.cncf.io/announcements/2026/08/11/cncf-announces-graduation-of-cloud-native-buildpacks-advancing-the-standard-for-container-builds/))
- 2026-W34: 該当ドキュメントなし — KubeCon + CloudNativeCon North America 2026のスケジュールが公開され、新たにAI Inference + Agenticトラックが追加 ([情報源](https://www.cncf.io/announcements/2026/08/10/cncf-reveals-kubecon-cloudnativecon-north-america-2026-schedule-adds-new-ai-inference-agentic-track/))
- 2026-W34: 該当ドキュメントなし — Kubernetes YAMLをKYAMLとして整形出力する方法、Kubernetesブログ ([情報源](https://kubernetes.io/blog/2026/08/11/how-to-pretty-print-kubernetes-yaml-as-kyaml/))
- 2026-W33: [networking/04-gateway-api.md](../networking/04-gateway-api.md) — Gateway API v1.6を反映（TCPRoute/UDPRouteがStandard v1に昇格、チャネル固有の非推奨API提供動作の変更）
- 2026-W33: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.5.0 GAを反映（Helm 4への移行、ソース整合性検証のアルファ版、ApplicationSetの改善）
- 2026-W33: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.0 GA（Gateway API v1.6.1、KCNP、複数プールIPAMの移行）と1.21.0-pre.0を反映
- 2026-W33: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37の先行紹介、Docs Freezeの開始、v1.38.0-alpha.0タグを反映
- 2026-W33: 該当ドキュメントなし — Amazon ECRがDocker pushで最大200 GBのイメージレイヤーをサポート ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-ecr-image-layers/))
- 2026-W33: 該当ドキュメントなし — K8gbがCNCFのインキュベーションプロジェクトに ([情報源](https://www.cncf.io/announcements/2026/08/05/k8gb-becomes-a-cncf-incubating-project/))
- 2026-W33: 該当ドキュメントなし — OpenCost 1.121.0でKubernetesの推論コスト追跡機能を追加 ([情報源](https://www.cncf.io/blog/2026/08/05/opencost-1-121-0-first-of-a-kind-kubernetes-inference-cost-tracking/))
- 2026-W33: 該当ドキュメントなし — Kubernetes DRAはHAMiに取って代わるのか？、CNCFブログ ([情報源](https://www.cncf.io/blog/2026/08/07/does-kubernetes-dra-replace-hami/))
- 2026-W31: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.36.3/v1.35.7/v1.34.10のパッチリリースと、v1.37のCode Freeze開始を反映
- 2026-W31: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — EKS Auto ModeのノードプールでのEFAおよびEC2 placement groupのサポートを反映
- 2026-W31: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — KarpenterのノードプールでのEFAおよびEC2 placement groupのサポートを反映
- 2026-W31: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — AMPの制限引き上げを反映（アクティブシリーズ15億件、ワークスペースあたりのルール20万件）
- 2026-W31: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — OpenTelemetryのCNCF Graduatedへの昇格を反映
- 2026-W31: [networking/calico/README.md](../networking/calico/README.md) — Kubernetes上のVM向けTigera Calicoの提供開始を反映（eBPFベースのVMとコンテナの統合ネットワーキング）
- 2026-W31: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.0-rc.1のリリース候補版を反映
- 2026-W31: 該当ドキュメントなし — Confidential ContainersがCNCFのインキュベーションプロジェクトに ([情報源](https://www.cncf.io/blog/2026/07/22/confidential-containers-becomes-a-cncf-incubating-project/))
- 2026-W31: 該当ドキュメントなし — Kubernetes CSI driverにおける2件のパストラバーサルCVE（CVE-2026-3864 NFS / CVE-2026-3865 SMB。csi-driver-nfs v4.13.1、csi-driver-smb v1.20.1で修正）([情報源](https://www.sentinelone.com/blog/mount-here-read-there-twin-path-traversal-cves-in-kubernetes-storage/))
- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.19.6/1.18.12/1.17.18のパッチリリースとCVE-2026-56743（ipBlock NetworkPolicyの問題）を反映
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.30.3/1.29.6のパッチリリースを反映
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.7.1を反映（未定義のServiceポートへのリクエストを許可しない、後方互換性を破る変更）
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — EKS Auto ModeのARCゾーンシフト/自動ゾーンシフトのサポートを反映
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — EKS Auto ModeのARCゾーンシフトのサポートを反映
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 古い系列向けのKarpenterパッチリリース（v1.3.8–v1.11.3）を反映
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37.0-beta.0とv1.37のリリーススケジュールを反映
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCon Japan 2026と、開催予定のArgo CD 3.5ロードマップセッションを反映
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — KubernetesブログのカスタムメトリクスExporterガイドを反映
- 2026-W30: 該当ドキュメントなし — HAMiがCNCFのインキュベーションプロジェクトに ([情報源](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/))
- 2026-W30: 該当ドキュメントなし — vLLMを使ってKubernetesでセルフホスト型LLMを実行する、CNCFブログ ([情報源](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/))
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — ACMEプロトコルのACMサポートを反映（ACMのパブリック証明書をcert-managerから利用可能に）
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — AIエージェント向けのNGINX + OpenTelemetryによるネットワーク境界のオブザーバビリティパターンを反映
- 2026-W29: 該当ドキュメントなし — AIネイティブなワークロードに向けたプラットフォームエンジニアリングの進化、CNCFブログ ([情報源](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/))
- 2026-07-11: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — etcd v3.7.0のリリースを反映（RangeStreamなど）
- 2026-07-11: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — EKS Auto ModeのGPU管理料金が最大60%引き下げられたことを反映
- 2026-07-11: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.14.0のリリースを反映（CapacityBuffers APIなど）
- 2026-07-11: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — CloudWatch Application Signals Service Eventsを反映
- 2026-07-11: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.4.5のパッチリリースを反映
- 2026-07-11: 該当ドキュメントなし — ingress-nginxの廃止への対応（2026年3月）、CNCFブログ ([情報源](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/))
- 2026-07-11: 該当ドキュメントなし — CNCFの「クラウドネイティブAIにおけるデータストレージ」ホワイトペーパーを公開 ([情報源](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/))
- 2026-07-11: 該当ドキュメントなし — Amazon EMR on EKSがApache Sparkのトラブルシューティングエージェントをサポート ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/))
- 2026-07-11: 該当ドキュメントなし — AWS Systems Managerのハイブリッド/マルチクラウドノード料金を改定（Advanced Instances Tierを廃止）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/))

</details>
