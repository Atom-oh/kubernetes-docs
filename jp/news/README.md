# ニュース
> **最終更新日**: 2026年11月21日

このページでは、Kubernetes、Amazon EKS、CNCFのニュースを受けて行ったドキュメントの変更を記録します。GitHub Actionsは毎週月曜日の09:00 KSTに更新を準備し、品質ゲートを通過するとPRを作成します。レビュー、マージ、デプロイの後に変更がサイトに反映されます。

週のラベルはログの記録週を示しており、情報源の公開日と異なる場合があります。これらは過去の記録です。現在のサポート状況、セキュリティパッチ、運用要件については、リンク先のガイドと公式情報を確認してください。「該当するドキュメントなし」は、その時点での自動照合結果を示します。

<!-- news-dashboard -->

<details class="news-log">
<summary>更新ログ全体を展開</summary>

## 更新ログ

- 2026-W47: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.32.0 GAリリースを反映（同じ週の1.31.4/1.30.8パッチリリースを含む）([情報源](https://istio.io/latest/news/releases/1.32.x/announcing-1.32/))
- 2026-W47: [eks-auto-mode/README.md](../eks-auto-mode/README.md) · [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — EKS Auto ModeおよびKarpenterでNVIDIA GPUとEFAのDynamic Resource Allocation（DRA）サポートが発表されたことを反映（KarpenterではすべてのKubernetesバージョン、Auto Modeでは1.36以降）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-eks-auto-mode-karpenter-dra/))
- 2026-W47: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — EKS Auto ModeでPodのセキュリティグループがサポートされたことを反映（個別のノードプールを設けずにPodごとのネットワークセグメンテーションが可能）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-eks-auto-mode-security-groups-for-pods/))
- 2026-W47: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Amazon EKS Provisioned Control Planeの4XL/8XLティアでetcdデータベースが24 GBに拡大されたことを反映（16 GBから増加。EKS 1.34以降が対象で、既存クラスターは自動的にアップグレード）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-eks-provisioned-control-plane-larger-etcd-database/))
- 2026-W47: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.15.2パッチリリースを反映（DRAのインスタンスタイプメタデータのみ。g7/g7e NVIDIA GPUメタデータの追加、EFAメタデータの対象を29から302のインスタンスタイプに拡大、Go 1.26.11）([情報源](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.15.2))
- 2026-W47: 該当するドキュメントなし — AWS Nitro Sandboxesが提供開始。Nitro Hypervisorで管理される軽量VMで、内部で実行されるAIエージェントを含め、Amazon EKSのPod、ECSタスク、VMをハードウェアで分離する ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/11/nitro-sandboxes-eks-ecs-ec2/))
- 2026-W47: [security/03-pod-security-standards.md](../security/03-pod-security-standards.md) — AWS Batch on Amazon EKSに、Linux capabilities、seccompプロファイル、Podレベルの設定など、Kubernetesのセキュリティコンテキストのサポートが追加されたことを反映（Pod Security Standardsのrestrictedプロファイルを適用するクラスターでジョブを実行可能）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/11/aws-batch-eks-security-context/))
- 2026-W47: 該当するドキュメントなし — PostgreSQL OperatorのCloudNativePGがCNCFのインキュベーションプロジェクトに昇格 ([情報源](https://www.cncf.io/blog/2026/11/10/cloudnativepg-becomes-a-cncf-incubating-project/))
- 2026-W47: 該当するドキュメントなし — Rayワークロード向けKubernetes OperatorのKubeRayがCNCFに寄贈されると発表 ([情報源](https://www.cncf.io/blog/2026/11/10/donating-kuberay-to-cncf/))
- 2026-W46: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.6.0 GAリリース（ApplicationSetのプログレッシブ同期メトリクス/条件、設定可能なDexストレージ/TLS設定など）と、その後2026-11-04にリリースされたバグ修正パッチv3.6.1を反映 ([情報源](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0))
- 2026-W46: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.5.7/v3.4.13/v3.3.19のバグ修正パッチリリースを反映 ([情報源](https://github.com/argoproj/argo-cd/releases/tag/v3.5.7))
- 2026-W46: [eks/13-eks-capabilities.md](../eks/13-eks-capabilities.md) · [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD向けEKS CapabilityでArgo CD Notificationsがサポートされたことを反映（Slack、Amazon SQS、EventBridgeを含む16のサービス、IAM Capability Role認証、Secrets Managerの認証情報参照）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-eks-argo-cd-notifications/))
- 2026-W46: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — Prometheus 3.16.0リリースを反映（平滑化/アンカー付きベクトルセレクターがStableに昇格、クエリコスト推定と実行制限が実験的機能として追加、`integral()`関数が実験的機能として追加、AgentモードのメタデータWALレコード）([情報源](https://github.com/prometheus/prometheus/releases/tag/v3.16.0))
- 2026-W46: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.21.0-pre.4プレリリースを反映（BGPのunnumbered peering、デフォルトで有効なBPF masquerading、Gateway API frontendのmTLSとリスナーTLSバージョンのオプション、複数プールのResource IPAM、Gateway API Inference Extension）([情報源](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.4))
- 2026-W46: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.38.0-beta.0のプレリリースを反映（v1.38初のベータ版。GAは2026-12-16を予定）([情報源](https://github.com/kubernetes/kubernetes/releases/tag/v1.38.0-beta.0))
- 2026-W45: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37.2/v1.36.6/v1.35.10/v1.34.13のパッチリリースを反映（侵害されたeMudhra中間CA証明書を信頼しなくなるGo 1.26.10を採用。v1.34.13は、2026-10-27にEOLを迎えた1.34系列の最終パッチ）([情報源](https://github.com/kubernetes/kubernetes/releases/tag/v1.37.2))
- 2026-W45: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.32.0-rc.0/rc.1リリース候補が公開（ドキュメントでは、その後のGAレビューを通じて1.32.0 RCサイクルをすでに扱っている）([情報源](https://github.com/istio/istio/releases/tag/1.32.0-rc.0))
- 2026-W45: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.10.2リリースを反映（GOAWAYを回避するためpolicy-controllerのgRPC HTTP/2接続ウィンドウを拡大、tap APIサーバーのクライアントTLSを修正、proxy v2.372.0、Go 1.26.9、proxy-init v2.4.11/CNI plugin v1.7.1）([情報源](https://github.com/linkerd/linkerd2/releases/tag/edge-26.10.2))
- 2026-W45: 該当するドキュメントなし — Kubernetes上でワークロードが実行時にどのように動作するかを定める共通標準であるWorkload Conformance Working Groupの発足を発表（Kubernetesブログ）([情報源](https://kubernetes.io/blog/2026/10/27/announcing-workload-conformance-wg/))
- 2026-W45: 該当するドキュメントなし — AI ConformanceがWorking GroupからSIG Architectureのサブプロジェクトに移行（Kubernetesブログの特集）([情報源](https://kubernetes.io/blog/2026/10/29/sig-arch-ai-conformance-2026/))
- 2026-W44: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.3/1.30.7/1.29.10のセキュリティパッチリリースを反映（ISTIO-SECURITY-2026-008、CVE-2026-111943：侵害されたeMudhra中間CA証明書を信頼しないよう変更。1.29.10はEOL後の例外的なリリース）([情報源](https://istio.io/latest/news/security/istio-security-2026-008/))
- 2026-W44: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.4/1.19.10/1.18.16の臨時セキュリティパッチリリースを反映（CVE-2026-111943。Go 1.26.10は侵害されたeMudhra中間CA証明書を信頼しなくなった）([情報源](https://github.com/cilium/cilium/releases/tag/v1.20.4))
- 2026-W44: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.5.6/v3.4.12/v3.3.17のバグ修正パッチリリースと、侵害されたeMudhra CA証明書への信頼を削除するセキュリティ修正を含むv3.3.18を反映 ([情報源](https://github.com/argoproj/argo-cd/releases/tag/v3.3.18))
- 2026-W44: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.6.0-rc4リリース候補を反映 ([情報源](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc4))
- 2026-W44: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.15.1パッチとv1.14.2/v1.14.3/v1.9.3 LTSパッチリリースを反映（バグ修正。すべての系列で、侵害されたeMudhra中間CA証明書を信頼しなくなるGo 1.26.10に移行）([情報源](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.15.1))
- 2026-W44: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — OpenTelemetry CollectorでAIエージェントのテレメトリをフィルタリングし、削減する方法に関するCNCFブログのガイドを反映 ([情報源](https://www.cncf.io/blog/2026/10/22/filtering-and-reducing-ai-agent-telemetry-with-the-opentelemetry-collector/))
- 2026-W44: 該当するドキュメントなし — Amazon EMR on EKSでEMR料金（vCPU時間あたりおよびGB時間あたり）が30パーセント値下げ。基盤となるEKS料金に変更なし ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/10/emr-eks-reduces-emr-charge-30-percent/))
- 2026-W44: 該当するドキュメントなし — AIワークロードがKubernetesのオートスケーリングをどう変えているか（CNCFブログ）([情報源](https://www.cncf.io/blog/2026/10/19/how-ai-workloads-are-reshaping-kubernetes-autoscaling/))
- 2026-W43: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.2/1.30.6/1.29.9のパッチリリースが公開（ISTIO-SECURITY-2026-007のセキュリティパッチを含む。以前のレビューでドキュメントにはすでに反映済み）([情報源](https://istio.io/news/releases/1.31.x/announcing-1.31.2/))
- 2026-W43: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.3/1.19.9/1.18.15のパッチリリースを反映（conntrack GCや`nodeSelector`を含むCNPの処理などのバグ修正）([情報源](https://github.com/cilium/cilium/releases/tag/v1.20.3))
- 2026-W43: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.5.5/v3.4.11/v3.3.16のバグ修正パッチリリースを反映 ([情報源](https://github.com/argoproj/argo-cd/releases/tag/v3.5.5))
- 2026-W43: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.6.0-rc3リリース候補を反映 ([情報源](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc3))
- 2026-W43: [security/14-waf-edge-api-security.md](../security/14-waf-edge-api-security.md) — CloudFront VPC originsでデュアルスタック（IPv6）がサポートされたことを反映 ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/10/cloudfront-vpc-origin-dualstack/))
- 2026-W43: [blockchain/01-fundamentals.md](../blockchain/01-fundamentals.md) — AWS Blockchain Snapshotsの提供開始を反映（Ethereum/Solanaノードのブートストラップに使える、事前同期済みの無料スナップショット）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/10/blockchain-snapshots-node-bootstrapping/))
- 2026-W43: [security/01-kyverno-policy-management.md](../security/01-kyverno-policy-management.md) — Kyverno向けNirmata Runtimeを紹介するCNCFブログを反映（eBPF/LSMによるカーネルレベルの実行時ポリシー適用）([情報源](https://www.cncf.io/blog/2026/10/15/extending-kubernetes-policy-enforcement-to-runtime-security-for-ai-workloads/))
- 2026-W43: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — Software Carbon Intensity（SCI）をOpenTelemetryのセマンティック規約として扱う提案を紹介するCNCFブログを反映 ([情報源](https://www.cncf.io/blog/2026/10/15/carbon-as-a-first-class-signal-bringing-software-carbon-intensity-to-opentelemetry/))
- 2026-W43: 該当するドキュメントなし — Headlampを使ってKueue管理下のJobのadmission状態を追跡する方法（Kubernetesブログ）([情報源](https://kubernetes.io/blog/2026/10/14/tracing-kueue-admission-with-headlamp/))
- 2026-W42: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.15.0リリースを反映（再起動をサポートする、任意の中断としてのノード修復、KubeletConfigurationでのCEL、DRAサポートの拡大など）
- 2026-W42: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.5.4/v3.4.10/v3.3.15のセキュリティパッチリリースを反映（repo-serverでのコマンド実行を含む4件のCRITICAL問題、CVE-2026-77459）
- 2026-W42: [kernel/01-container-primitives.md](../kernel/01-container-primitives.md) — cgroup v1の非推奨化状況に関するKubernetesブログを反映（v1.35から`failCgroupV1`のデフォルト値が`true`）
- 2026-W42: 該当するドキュメントなし — NVMe SSDベースのノードスワップによるKubernetesワークロードのスケーリング（v1.34でGA、Kubernetesブログ）([情報源](https://kubernetes.io/blog/2026/10/05/scaling-kubernetes-workloads-with-node-swap/))
- 2026-W42: 該当するドキュメントなし — MesheryがCNCFのインキュベーションプロジェクトに昇格 ([情報源](https://www.cncf.io/blog/2026/10/07/meshery-becomes-a-cncf-incubating-project/))
- 2026-W42: 該当するドキュメントなし — AWS BatchがAmazon EKS access entry認証をサポート ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/10/aws-batch-access-entries/))
- 2026-W41: [eks/08-eks-upgrades.md](../eks/08-eks-upgrades.md) — Amazon EKSおよびEKS DistroでのKubernetes 1.37サポートを反映（Metrics API GA、DRA device taints GA、HPAによるゼロへのスケーリングがベータ）
- 2026-W41: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD 4.0のビジョン策定開始とArgoCon North America 2026のニュースを反映
- 2026-W41: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — AtlassianがOTel、Kafka、Flinkを基盤にインシデント検知を再構築した事例を反映（CNCFブログ）
- 2026-W41: 該当するドキュメントなし — Amazon ECSがblue/green、linear、canaryデプロイメントでAmazon VPC Latticeのサポートを追加 ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/10/amazon-ecs-vpc-lattice-blue-green-deployments))
- 2026-W41: 該当するドキュメントなし — Amazon Managed GrafanaでGrafana 13.2ワークスペースの作成が可能に ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-managed-grafana-now-supports-creating-grafana-13-2-workspaces))
- 2026-W41: 該当するドキュメントなし — Grafana Tempo 3.1リリース（Kafkaの新機能、TraceQLメトリクスの更新、トレースのマスキングなど）([情報源](https://grafana.com/blog/tempo-3-1-release-all-the-latest-features))
- 2026-W41: 該当するドキュメントなし — ゲートではなくガードレール：プラットフォームチームにおけるポリシーを再考する（CNCFブログ）([情報源](https://www.cncf.io/blog/2026/10/01/guardrails-not-gates-rethinking-policy-in-platform-teams/))
- 2026-W40: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37.1/v1.36.5/v1.35.9/v1.34.12のパッチリリースと、v1.37のPVC `Unused`条件（ベータ）に関するブログ記事を反映
- 2026-W40: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.1/1.30.5/1.29.8のパッチリリースを反映（BackendTLSPolicyのfail-openに関するセキュリティ修正GHSA-qm8v-g4f9-qhjxを含む）
- 2026-W40: [eks/04-eks-storage-part1.md](../eks/04-eks-storage-part1.md) — EFS CSI driverのマウントオプション注入の脆弱性CVE-2026-6437を反映（v3.0.1で修正）
- 2026-W40: [ai-ml/08-llm-gateway.md](../ai-ml/08-llm-gateway.md) — Amazon SageMaker HyperPod Inference Gatewayの提供開始を反映（EKS管理アドオン、GPUを考慮したルーティング）
- 2026-W40: 該当するドキュメントなし — Amazon EMR on EKSがIPv6のAmazon EKSクラスターをサポート ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-emr-eks-ipv6-support))
- 2026-W40: 該当するドキュメントなし — Spark Connectを使ってAmazon EMR on EKSで対話型ワークロードを実行 ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/09/emr-eks-spark-connect-interactive/))
- 2026-W40: 該当するドキュメントなし — Amazon CloudWatch Omniが一般提供開始（AIを第一に据えたオブザーバビリティ体験、OpenTelemetryとの相互運用性）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-cloudwatch-omni-ai/))
- 2026-W39: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37の機能を掘り下げる記事3件を反映（Memory QoS Beta、Pod-Level Resource Managers Beta、emptyDirの権限とbind mountオプション）
- 2026-W39: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.2/1.19.8/1.18.14のパッチリリースと、1.20の機能を振り返るCNCFブログを反映
- 2026-W39: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.5.3/v3.4.9のパッチリリースとv3.6.0-rc1を反映
- 2026-W39: 該当するドキュメントなし — Kubernetes CSI Changed Block Tracking（CBT）APIがベータに昇格。アルファ版との違いについて（Kubernetesブログ）([情報源](https://kubernetes.io/blog/2026/09/14/csi-changed-block-tracking-beta/))
- 2026-W39: 該当するドキュメントなし — AWS Resilience Hubに3つの新機能が追加（EKSラベルに基づく、名前空間内のサービスリソース検出を含む）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/09/resilience-hub-eks-dependency-policy/))
- 2026-W38: [core/08-scheduling-preemption-eviction.md](../core/08-scheduling-preemption-eviction.md) — Kubernetes v1.37でのインプレースPodサイズ変更に対するスケジューラーのプリエンプション（アルファ）と、Workload-Aware Schedulingの進展（Workload/PodGroup Beta、CompositePodGroup API）を反映
- 2026-W38: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37のNodeライフサイクル条件を反映（drain、メンテナンス、graceful shutdownのための既知の条件5種類）
- 2026-W38: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — Kubernetes v1.37コンポーネントのメトリクスに対するPrometheusネイティブヒストグラムを反映（ベータ、デフォルトで有効）
- 2026-W38: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.21.0-pre.2プレリリースを反映（Gateway APIのセッション永続化、AWSマネージドプレフィックスリスト、デフォルトでのBPF masquerading）
- 2026-W38: 該当するドキュメントなし — KarmadaがCNCFのGraduatedプロジェクトに昇格 ([情報源](https://www.cncf.io/announcements/2026/09/07/cloud-native-computing-foundation-announces-karmada-graduation/))
- 2026-W38: 該当するドキュメントなし — Kubernetesの災害復旧：再現可能な3つの障害シナリオに基づくガイダンス（CNCFブログ）([情報源](https://www.cncf.io/blog/2026/09/10/kubernetes-disaster-recovery-guidance-from-three-reproducible-failure-scenarios/))
- 2026-W38: 該当するドキュメントなし — AWS Private CA EKS add-onおよびConnector for ADがAWS GovCloud (US)で利用可能に ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/09/private-ca-eks-addon-ad-govcloud/))
- 2026-W36: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37「Garhwal」リリースを反映（Pod certificates/ClusterTrustBundlesがStableに、Metrics API GA、kube-dnsとIPVSモードの非推奨化など）
- 2026-W36: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.30.4/1.29.7のセキュリティパッチリリースを反映（ISTIO-SECURITY-2026-006、EnvoyのCVE 13件）
- 2026-W36: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.5.2/v3.4.8のパッチリリースを反映
- 2026-W36: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.8.4を反映（TLSRoute APIバージョンネゴシエーションなど）
- 2026-W36: 該当するドキュメントなし — Amazon EKSでクラスターあたり最大10個の外部OIDC IDプロバイダーがサポートされるように ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-multiple-oidc-providers))
- 2026-W36: 該当するドキュメントなし — 急増前にスケール：Kubernetes上のGPUワークロード向け予測的オートスケーリング（CNCFブログ）([情報源](https://www.cncf.io/blog/2026/08/28/scale-before-the-spike-predictive-autoscaling-for-gpu-workloads-on-kubernetes/))
- 2026-W36: 該当するドキュメントなし — Kubernetes上にAIファクトリーを構築（CNCFブログ）([情報源](https://www.cncf.io/blog/2026/08/27/building-an-ai-factory-on-kubernetes/))
- 2026-W35: [gitops/argocd/README.md](../gitops/argocd/README.md) — Amazon EKSマネージドArgo CD capabilityでカスタム設定がサポートされたことを反映（`argocd-cm` ConfigMap経由）
- 2026-W35: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.36.4/v1.35.8/v1.34.11のパッチリリースとv1.37.0-rc.1を反映
- 2026-W35: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.1/1.19.7/1.18.13のパッチリリースを反映
- 2026-W35: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.14.1パッチリリースを反映
- 2026-W35: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.0-rc.0リリースを反映（1.31がRC段階に移行）
- 2026-W35: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 遅いSQLクエリをOTel span由来のメトリクスに変換するCNCFブログのガイドを反映
- 2026-W35: 該当するドキュメントなし — Amazon EKSでライフサイクル管理を自動化した認証局（CA）ローテーションがサポートされるように ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-certificate-authority-ca-rotation-automated-lifecycle-management))
- 2026-W35: 該当するドキュメントなし — KubeflowがCNCFでGraduatedプロジェクトに昇格 ([情報源](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/))
- 2026-W34: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.5.0 GAリリースとv3.5.1/v3.4.7/v3.3.14のパッチリリースを反映
- 2026-W34: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.0-beta.1リリースを反映（1.31がベータ段階に移行）
- 2026-W34: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.8.2を反映（Gateway API 1.5.1サポート、テスト済みのKubernetes最大バージョンは1.36）
- 2026-W34: 該当するドキュメントなし — Amazon EKSで高度なKubernetesコントロールプレーン設定パラメーターがサポートされるように（scheduler/controller manager/API serverのチューニング）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-control-plane-configuration-parameters))
- 2026-W34: 該当するドキュメントなし — Cloud Native BuildpacksがCNCFのGraduatedプロジェクトに昇格 ([情報源](https://www.cncf.io/announcements/2026/08/11/cncf-announces-graduation-of-cloud-native-buildpacks-advancing-the-standard-for-container-builds/))
- 2026-W34: 該当するドキュメントなし — KubeCon + CloudNativeCon North America 2026のスケジュールを公開。AI Inference + Agenticトラックを新設 ([情報源](https://www.cncf.io/announcements/2026/08/10/cncf-reveals-kubecon-cloudnativecon-north-america-2026-schedule-adds-new-ai-inference-agentic-track/))
- 2026-W34: 該当するドキュメントなし — Kubernetes YAMLをKYAMLとして整形出力する方法（Kubernetesブログ）([情報源](https://kubernetes.io/blog/2026/08/11/how-to-pretty-print-kubernetes-yaml-as-kyaml/))
- 2026-W33: [networking/04-gateway-api.md](../networking/04-gateway-api.md) — Gateway API v1.6を反映（TCPRoute/UDPRouteがStandard v1に昇格、チャネルごとの非推奨API提供方法の変更）
- 2026-W33: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.5.0 GAを反映（Helm 4への移行、ソース整合性検証のアルファ機能、ApplicationSetの改善）
- 2026-W33: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.0 GA（Gateway API v1.6.1、KCNP、複数プールIPAMの移行）および1.21.0-pre.0を反映
- 2026-W33: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37の先行情報、Docs Freezeの開始、およびv1.38.0-alpha.0タグを反映
- 2026-W33: 該当するドキュメントなし — Amazon ECRでDocker push時に最大200 GBのイメージレイヤーがサポートされるように ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-ecr-image-layers/))
- 2026-W33: 該当するドキュメントなし — K8gbがCNCFのインキュベーションプロジェクトに昇格 ([情報源](https://www.cncf.io/announcements/2026/08/05/k8gb-becomes-a-cncf-incubating-project/))
- 2026-W33: 該当するドキュメントなし — OpenCost 1.121.0でKubernetesの推論コスト追跡が追加 ([情報源](https://www.cncf.io/blog/2026/08/05/opencost-1-121-0-first-of-a-kind-kubernetes-inference-cost-tracking/))
- 2026-W33: 該当するドキュメントなし — Kubernetes DRAはHAMiに取って代わるのか？（CNCFブログ）([情報源](https://www.cncf.io/blog/2026/08/07/does-kubernetes-dra-replace-hami/))
- 2026-W31: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.36.3/v1.35.7/v1.34.10のパッチリリースと、v1.37のCode Freeze開始を反映
- 2026-W31: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — EKS Auto ModeのノードプールでEFAとEC2 placement groupがサポートされたことを反映
- 2026-W31: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — KarpenterのノードプールでEFAとEC2 placement groupがサポートされたことを反映
- 2026-W31: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — AMPの上限引き上げを反映（アクティブ系列15億、ワークスペースあたり20万ルール）
- 2026-W31: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — OpenTelemetryのCNCF Graduated昇格を反映
- 2026-W31: [networking/calico/README.md](../networking/calico/README.md) — Kubernetes上のVM向けTigera Calicoの提供開始を反映（eBPFベースのVMとコンテナの統合ネットワーキング）
- 2026-W31: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.0-rc.1リリース候補を反映
- 2026-W31: 該当するドキュメントなし — Confidential ContainersがCNCFのインキュベーションプロジェクトに昇格 ([情報源](https://www.cncf.io/blog/2026/07/22/confidential-containers-becomes-a-cncf-incubating-project/))
- 2026-W31: 該当するドキュメントなし — Kubernetes CSIドライバーでパストラバーサル脆弱性が2件発見（CVE-2026-3864 NFS / CVE-2026-3865 SMB。csi-driver-nfs v4.13.1、csi-driver-smb v1.20.1で修正）([情報源](https://www.sentinelone.com/blog/mount-here-read-there-twin-path-traversal-cves-in-kubernetes-storage/))
- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.19.6/1.18.12/1.17.18のパッチリリースとCVE-2026-56743（ipBlock NetworkPolicyの問題）を反映
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.30.3/1.29.6のパッチリリースを反映
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.7.1を反映（未定義のサービスポートへのリクエストを禁止。互換性を損なう変更）
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — EKS Auto ModeのARC zonal shift/autoshiftサポートを反映
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — EKS Auto ModeのARC zonal shiftサポートを反映
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 古い系列向けKarpenterパッチリリース（v1.3.8–v1.11.3）を反映
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37.0-beta.0とv1.37のリリーススケジュールを反映
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCon Japan 2026と、開催予定のArgo CD 3.5ロードマップセッションを反映
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — カスタムメトリクスエクスポーターに関するKubernetesブログのガイドを反映
- 2026-W30: 該当するドキュメントなし — HAMiがCNCFのインキュベーションプロジェクトに昇格 ([情報源](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/))
- 2026-W30: 該当するドキュメントなし — vLLMを使ってKubernetes上でセルフホスト型LLMを実行（CNCFブログ）([情報源](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/))
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — ACMEプロトコルのACMサポートを反映（ACMのパブリック証明書をcert-managerから利用可能に）
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — AIエージェント向けのNGINX + OpenTelemetryによるネットワーク境界のオブザーバビリティパターンを反映
- 2026-W29: 該当するドキュメントなし — AIネイティブなワークロードに向けたプラットフォームエンジニアリングの進化（CNCFブログ）([情報源](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/))
- 2026-07-11: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — etcd v3.7.0リリースを反映（RangeStreamなど）
- 2026-07-11: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — EKS Auto ModeのGPU管理料金が最大60%引き下げられたことを反映
- 2026-07-11: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.14.0リリースを反映（CapacityBuffers APIなど）
- 2026-07-11: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — CloudWatch Application Signals Service Eventsを反映
- 2026-07-11: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.4.5パッチリリースを反映
- 2026-07-11: 該当するドキュメントなし — ingress-nginxの廃止への対応（2026年3月、CNCFブログ）([情報源](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/))
- 2026-07-11: 該当するドキュメントなし — CNCFの「Data Storage in Cloud Native AI」ホワイトペーパーを公開 ([情報源](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/))
- 2026-07-11: 該当するドキュメントなし — Amazon EMR on EKSでApache Sparkのトラブルシューティングエージェントがサポートされるように ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/))
- 2026-07-11: 該当するドキュメントなし — AWS Systems Managerのハイブリッド/マルチクラウドノード料金を大幅改定（Advanced Instances Tierを廃止）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/))

</details>
