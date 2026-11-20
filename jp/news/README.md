# ニュース
> **最終更新日**: 2026年11月16日

このページでは、Kubernetes、Amazon EKS、CNCFのニュースを受けて行ったドキュメントの変更を記録しています。GitHub Actionsは毎週月曜日の09:00 KSTに更新を準備し、品質ゲートに合格するとPRを作成します。レビュー、マージ、デプロイの後、変更がサイトに反映されます。

週のラベルはログ項目の週を示しており、情報源の公開日とは異なる場合があります。これらは過去の記録です。現在のサポート状況、セキュリティパッチ、運用要件については、リンク先のガイドと公式情報を確認してください。「該当ドキュメントなし」は、その時点での自動照合結果を示しています。

<!-- news-dashboard -->

<details class="news-log">
<summary>更新ログ全体を展開</summary>

## 更新ログ

- 2026-W47: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.32.0 GAリリースを反映（同じ週にリリースされた1.31.4/1.30.8パッチリリースも含む）([情報源](https://istio.io/latest/news/releases/1.32.x/announcing-1.32/))
- 2026-W47: [eks-auto-mode/README.md](../eks-auto-mode/README.md) · [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — EKS Auto ModeとKarpenterでのNVIDIA GPUおよびEFAのDynamic Resource Allocation（DRA）サポートの発表を反映（KarpenterではすべてのKubernetesバージョン、Auto Modeでは1.36以降）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-eks-auto-mode-karpenter-dra/))
- 2026-W47: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — EKS Auto ModeでのPod向けセキュリティグループのサポート発表を反映（個別のノードプールを設けずにPod単位でネットワークを分離）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-eks-auto-mode-security-groups-for-pods/))
- 2026-W47: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Amazon EKS Provisioned Control Planeの4XL/8XLティアにおけるetcdデータベース容量の拡大（16 GBから24 GB）を反映（EKS 1.34以降、既存クラスターは自動アップグレード）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-eks-provisioned-control-plane-larger-etcd-database/))
- 2026-W47: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.15.2パッチリリースを反映（DRAインスタンスタイプのメタデータのみ：g7/g7e NVIDIA GPUメタデータを追加し、EFAメタデータの対象を29から302のインスタンスタイプに拡大、Go 1.26.11）([情報源](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.15.2))
- 2026-W47: 該当ドキュメントなし — AWS Nitro Sandboxesが提供開始。Nitro Hypervisorが管理する軽量VMで、Amazon EKSのPod、ECSタスク、VMをハードウェアで分離し、その中で動作するAIエージェントも対象となる ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/11/nitro-sandboxes-eks-ecs-ec2/))
- 2026-W47: [security/03-pod-security-standards.md](../security/03-pod-security-standards.md) — AWS Batch on Amazon EKSに、Linux capabilities、seccompプロファイル、Podレベルの設定など、Kubernetesのセキュリティコンテキストのサポートが追加されたことを反映（Pod Security Standardsのrestrictedプロファイルを適用しているクラスターでジョブを実行可能）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/11/aws-batch-eks-security-context/))
- 2026-W47: 該当ドキュメントなし — PostgreSQL OperatorのCloudNativePGがCNCFのインキュベーションプロジェクトに ([情報源](https://www.cncf.io/blog/2026/11/10/cloudnativepg-becomes-a-cncf-incubating-project/))
- 2026-W47: 該当ドキュメントなし — Rayワークロード向けKubernetes OperatorのKubeRayがCNCFに寄贈されると発表 ([情報源](https://www.cncf.io/blog/2026/11/10/donating-kuberay-to-cncf/))
- 2026-W44: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.3/1.30.7/1.29.10のセキュリティパッチリリースを反映（ISTIO-SECURITY-2026-008、CVE-2026-111943：侵害されたeMudhra中間CA証明書を信頼しないように変更。1.29.10はEOL後の例外的なリリース）([情報源](https://istio.io/latest/news/security/istio-security-2026-008/))
- 2026-W44: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.4/1.19.10/1.18.16の帯域外セキュリティパッチリリースを反映（CVE-2026-111943：Go 1.26.10は侵害されたeMudhra中間CA証明書を信頼しない）([情報源](https://github.com/cilium/cilium/releases/tag/v1.20.4))
- 2026-W44: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.5.6/v3.4.12/v3.3.17のバグ修正パッチリリースと、侵害されたeMudhra CA証明書への信頼を削除するセキュリティ修正を含むv3.3.18を反映 ([情報源](https://github.com/argoproj/argo-cd/releases/tag/v3.3.18))
- 2026-W44: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.6.0-rc4リリース候補を反映 ([情報源](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc4))
- 2026-W44: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.15.1パッチとv1.14.2/v1.14.3/v1.9.3 LTSパッチリリースを反映（バグ修正。すべての系列がGo 1.26.10に移行し、侵害されたeMudhra中間CA証明書を信頼しない）([情報源](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.15.1))
- 2026-W44: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — OpenTelemetry CollectorでAIエージェントのテレメトリーをフィルタリングおよび削減するCNCFブログのガイドを反映 ([情報源](https://www.cncf.io/blog/2026/10/22/filtering-and-reducing-ai-agent-telemetry-with-the-opentelemetry-collector/))
- 2026-W44: 該当ドキュメントなし — Amazon EMR on EKSのEMR料金（vCPU時間あたり、GB時間あたり）が30パーセント引き下げ。基盤となるEKS料金に変更はなし ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/10/emr-eks-reduces-emr-charge-30-percent/))
- 2026-W44: 該当ドキュメントなし — AIワークロードがKubernetesのオートスケーリングをどう変えているか、CNCFブログ ([情報源](https://www.cncf.io/blog/2026/10/19/how-ai-workloads-are-reshaping-kubernetes-autoscaling/))
- 2026-W43: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.2/1.30.6/1.29.9のパッチリリースが公開（ISTIO-SECURITY-2026-007セキュリティパッチを含む。以前のレビューですでにドキュメントに反映済み）([情報源](https://istio.io/news/releases/1.31.x/announcing-1.31.2/))
- 2026-W43: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.3/1.19.9/1.18.15のパッチリリースを反映（`nodeSelector`を含むCNPの処理やconntrack GCなどのバグ修正）([情報源](https://github.com/cilium/cilium/releases/tag/v1.20.3))
- 2026-W43: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.5.5/v3.4.11/v3.3.16のバグ修正パッチリリースを反映 ([情報源](https://github.com/argoproj/argo-cd/releases/tag/v3.5.5))
- 2026-W43: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.6.0-rc3リリース候補を反映 ([情報源](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc3))
- 2026-W43: [security/14-waf-edge-api-security.md](../security/14-waf-edge-api-security.md) — CloudFront VPC originsのデュアルスタック（IPv6）対応の発表を反映 ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/10/cloudfront-vpc-origin-dualstack/))
- 2026-W43: [blockchain/01-fundamentals.md](../blockchain/01-fundamentals.md) — AWSでのBlockchain Snapshotsの提供開始を反映（Ethereum/Solanaノードのブートストラップ用の、事前同期済みスナップショットを無料で提供）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/10/blockchain-snapshots-node-bootstrapping/))
- 2026-W43: [security/01-kyverno-policy-management.md](../security/01-kyverno-policy-management.md) — Kyverno向けNirmata Runtimeを紹介するCNCFブログを反映（eBPF/LSMによるカーネルレベルのランタイムポリシー適用）([情報源](https://www.cncf.io/blog/2026/10/15/extending-kubernetes-policy-enforcement-to-runtime-security-for-ai-workloads/))
- 2026-W43: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — Software Carbon Intensity（SCI）をOpenTelemetryのセマンティック規約として扱う提案を紹介するCNCFブログを反映 ([情報源](https://www.cncf.io/blog/2026/10/15/carbon-as-a-first-class-signal-bringing-software-carbon-intensity-to-opentelemetry/))
- 2026-W43: 該当ドキュメントなし — Headlampを使ってKueue管理下のJobsのadmission状態を追跡する、Kubernetesブログ ([情報源](https://kubernetes.io/blog/2026/10/14/tracing-kueue-admission-with-headlamp/))
- 2026-W42: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.15.0リリースを反映（再起動をサポートする任意の中断としてのノード修復、KubeletConfigurationでのCEL、DRAサポートの拡大など）
- 2026-W42: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.5.4/v3.4.10/v3.3.15のセキュリティパッチリリースを反映（repo-serverのコマンド実行を含む4件のCRITICAL問題、CVE-2026-77459）
- 2026-W42: [kernel/01-container-primitives.md](../kernel/01-container-primitives.md) — cgroup v1の非推奨化状況に関するKubernetesブログの情報を反映（v1.35から`failCgroupV1`のデフォルト値が`true`）
- 2026-W42: 該当ドキュメントなし — NVMe SSDを使用したノードスワップでKubernetesワークロードをスケーリング（v1.34でGA）、Kubernetesブログ ([情報源](https://kubernetes.io/blog/2026/10/05/scaling-kubernetes-workloads-with-node-swap/))
- 2026-W42: 該当ドキュメントなし — MesheryがCNCFのインキュベーションプロジェクトに ([情報源](https://www.cncf.io/blog/2026/10/07/meshery-becomes-a-cncf-incubating-project/))
- 2026-W42: 該当ドキュメントなし — AWS BatchがAmazon EKSのアクセスエントリー認証に対応 ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/10/aws-batch-access-entries/))
- 2026-W41: [eks/08-eks-upgrades.md](../eks/08-eks-upgrades.md) — Amazon EKSとEKS DistroでのKubernetes 1.37サポートを反映（Metrics API GA、DRA device taints GA、HPAのscale-to-zeroがベータ）
- 2026-W41: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD 4.0のビジョン策定開始とArgoCon North America 2026のニュースを反映
- 2026-W41: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — OTel、Kafka、Flinkを利用したAtlassianのインシデント検出システム再構築を反映（CNCFブログ）
- 2026-W41: 該当ドキュメントなし — Amazon ECSが、blue/green、linear、canaryの各デプロイでAmazon VPC Latticeに対応 ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/10/amazon-ecs-vpc-lattice-blue-green-deployments))
- 2026-W41: 該当ドキュメントなし — Amazon Managed GrafanaでGrafana 13.2のワークスペースを作成可能に ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-managed-grafana-now-supports-creating-grafana-13-2-workspaces))
- 2026-W41: 該当ドキュメントなし — Grafana Tempo 3.1リリース（Kafkaの新機能、TraceQLメトリクスの更新、トレースのマスキングなど）([情報源](https://grafana.com/blog/tempo-3-1-release-all-the-latest-features))
- 2026-W41: 該当ドキュメントなし — ゲートではなくガードレール：プラットフォームチームのポリシーを見直す、CNCFブログ ([情報源](https://www.cncf.io/blog/2026/10/01/guardrails-not-gates-rethinking-policy-in-platform-teams/))
- 2026-W40: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37.1/v1.36.5/v1.35.9/v1.34.12のパッチリリースと、v1.37のPVC `Unused`条件（ベータ）に関するブログ記事を反映
- 2026-W40: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.1/1.30.5/1.29.8のパッチリリースを反映（BackendTLSPolicyのfail-openに関するセキュリティ修正GHSA-qm8v-g4f9-qhjxを含む）
- 2026-W40: [eks/04-eks-storage-part1.md](../eks/04-eks-storage-part1.md) — EFS CSI driverのマウントオプション注入の脆弱性CVE-2026-6437を反映（v3.0.1で修正）
- 2026-W40: [ai-ml/08-llm-gateway.md](../ai-ml/08-llm-gateway.md) — Amazon SageMaker HyperPod Inference Gatewayの提供開始を反映（EKS管理アドオン、GPUを考慮したルーティング）
- 2026-W40: 該当ドキュメントなし — Amazon EMR on EKSがIPv6のAmazon EKSクラスターに対応 ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-emr-eks-ipv6-support))
- 2026-W40: 該当ドキュメントなし — Spark Connectを使ってAmazon EMR on EKSで対話型ワークロードを実行 ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/09/emr-eks-spark-connect-interactive/))
- 2026-W40: 該当ドキュメントなし — Amazon CloudWatch Omniが一般提供開始（AIを中心としたオブザーバビリティ体験、OpenTelemetryとの相互運用性）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-cloudwatch-omni-ai/))
- 2026-W39: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37の3つの機能を詳しく解説する内容を反映（Memory QoSベータ、Pod-Level Resource Managersベータ、emptyDirの権限とbind mountオプション）
- 2026-W39: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.2/1.19.8/1.18.14のパッチリリースと、1.20の機能を振り返るCNCFブログを反映
- 2026-W39: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.5.3/v3.4.9のパッチリリースとv3.6.0-rc1を反映
- 2026-W39: 該当ドキュメントなし — Kubernetes CSI Changed Block Tracking（CBT）APIがベータに昇格。アルファとの違いについてのKubernetesブログ ([情報源](https://kubernetes.io/blog/2026/09/14/csi-changed-block-tracking-beta/))
- 2026-W39: 該当ドキュメントなし — AWS Resilience Hubに3つの新機能を追加（EKSラベルに基づいて名前空間内のサービスリソースを検出する機能など）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/09/resilience-hub-eks-dependency-policy/))
- 2026-W38: [core/08-scheduling-preemption-eviction.md](../core/08-scheduling-preemption-eviction.md) — Kubernetes v1.37のインプレースPodリサイズにおけるスケジューラーのプリエンプション（アルファ）と、Workload-Aware Schedulingの進展（Workload/PodGroupベータ、CompositePodGroup API）を反映
- 2026-W38: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37のNodeライフサイクル条件を反映（drain、メンテナンス、正常なシャットダウンのための5つの既知の条件）
- 2026-W38: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — Kubernetes v1.37コンポーネントのメトリクスでのPrometheusネイティブヒストグラムを反映（ベータ、デフォルトで有効）
- 2026-W38: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.21.0-pre.2のプレリリースを反映（Gateway APIのセッション永続化、AWS管理プレフィックスリスト、デフォルトでのBPF masquerading）
- 2026-W38: 該当ドキュメントなし — KarmadaがCNCFの卒業プロジェクトに ([情報源](https://www.cncf.io/announcements/2026/09/07/cloud-native-computing-foundation-announces-karmada-graduation/))
- 2026-W38: 該当ドキュメントなし — 再現可能な3つの障害シナリオから得たKubernetesの災害復旧ガイダンス、CNCFブログ ([情報源](https://www.cncf.io/blog/2026/09/10/kubernetes-disaster-recovery-guidance-from-three-reproducible-failure-scenarios/))
- 2026-W38: 該当ドキュメントなし — AWS Private CA EKS add-onおよびConnector for ADがAWS GovCloud（US）で利用可能に ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/09/private-ca-eks-addon-ad-govcloud/))
- 2026-W36: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37「Garhwal」リリースを反映（Pod certificates/ClusterTrustBundlesがStable、Metrics API GA、kube-dnsおよびIPVSモードの非推奨化など）
- 2026-W36: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.30.4/1.29.7のセキュリティパッチリリースを反映（ISTIO-SECURITY-2026-006、EnvoyのCVE 13件）
- 2026-W36: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.5.2/v3.4.8のパッチリリースを反映
- 2026-W36: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.8.4を反映（TLSRoute APIバージョンネゴシエーションなど）
- 2026-W36: 該当ドキュメントなし — Amazon EKSでクラスターあたり最大10個の外部OIDC IDプロバイダーをサポート ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-multiple-oidc-providers))
- 2026-W36: 該当ドキュメントなし — スパイクの前にスケール：Kubernetes上のGPUワークロード向け予測オートスケーリング、CNCFブログ ([情報源](https://www.cncf.io/blog/2026/08/28/scale-before-the-spike-predictive-autoscaling-for-gpu-workloads-on-kubernetes/))
- 2026-W36: 該当ドキュメントなし — Kubernetes上にAIファクトリーを構築する、CNCFブログ ([情報源](https://www.cncf.io/blog/2026/08/27/building-an-ai-factory-on-kubernetes/))
- 2026-W35: [gitops/argocd/README.md](../gitops/argocd/README.md) — Amazon EKS管理のArgo CD機能でのカスタム設定（`argocd-cm` ConfigMap経由）のサポートを反映
- 2026-W35: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.36.4/v1.35.8/v1.34.11のパッチリリースとv1.37.0-rc.1を反映
- 2026-W35: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.1/1.19.7/1.18.13のパッチリリースを反映
- 2026-W35: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.14.1パッチリリースを反映
- 2026-W35: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.0-rc.0リリースを反映（1.31がRC段階に移行）
- 2026-W35: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 遅いSQLクエリからOTel span由来のメトリクスを抽出するCNCFブログのガイドを反映
- 2026-W35: 該当ドキュメントなし — Amazon EKSで自動ライフサイクル管理による認証局（CA）のローテーションに対応 ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-certificate-authority-ca-rotation-automated-lifecycle-management))
- 2026-W35: 該当ドキュメントなし — KubeflowがCNCF内で卒業 ([情報源](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/))
- 2026-W34: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.5.0 GAリリースとv3.5.1/v3.4.7/v3.3.14のパッチリリースを反映
- 2026-W34: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.0-beta.1リリースを反映（1.31がベータ段階に移行）
- 2026-W34: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.8.2を反映（Gateway API 1.5.1対応、テスト済みの最大Kubernetesバージョンは1.36）
- 2026-W34: 該当ドキュメントなし — Amazon EKSで高度なKubernetesコントロールプレーン構成パラメーターに対応（scheduler/controller manager/API serverの調整）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-control-plane-configuration-parameters))
- 2026-W34: 該当ドキュメントなし — Cloud Native BuildpacksがCNCFの卒業プロジェクトに ([情報源](https://www.cncf.io/announcements/2026/08/11/cncf-announces-graduation-of-cloud-native-buildpacks-advancing-the-standard-for-container-builds/))
- 2026-W34: 該当ドキュメントなし — KubeCon + CloudNativeCon North America 2026のスケジュールが公開。新たにAI Inference + Agenticトラックを追加 ([情報源](https://www.cncf.io/announcements/2026/08/10/cncf-reveals-kubecon-cloudnativecon-north-america-2026-schedule-adds-new-ai-inference-agentic-track/))
- 2026-W34: 該当ドキュメントなし — Kubernetes YAMLをKYAMLとして見やすく整形する方法、Kubernetesブログ ([情報源](https://kubernetes.io/blog/2026/08/11/how-to-pretty-print-kubernetes-yaml-as-kyaml/))
- 2026-W33: [networking/04-gateway-api.md](../networking/04-gateway-api.md) — Gateway API v1.6を反映（TCPRoute/UDPRouteがStandard v1に昇格、チャネル固有の非推奨API提供方法の変更）
- 2026-W33: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.5.0 GAを反映（Helm 4への移行、ソース整合性検証のアルファ、ApplicationSetの改善）
- 2026-W33: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.0 GA（Gateway API v1.6.1、KCNP、マルチプールIPAMの移行）と1.21.0-pre.0を反映
- 2026-W33: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37の先行紹介、Docs Freezeの開始、v1.38.0-alpha.0タグを反映
- 2026-W33: 該当ドキュメントなし — Amazon ECRでDocker push時に最大200 GBのイメージレイヤーをサポート ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-ecr-image-layers/))
- 2026-W33: 該当ドキュメントなし — K8gbがCNCFのインキュベーションプロジェクトに ([情報源](https://www.cncf.io/announcements/2026/08/05/k8gb-becomes-a-cncf-incubating-project/))
- 2026-W33: 該当ドキュメントなし — OpenCost 1.121.0でKubernetesの推論コスト追跡機能を追加 ([情報源](https://www.cncf.io/blog/2026/08/05/opencost-1-121-0-first-of-a-kind-kubernetes-inference-cost-tracking/))
- 2026-W33: 該当ドキュメントなし — Kubernetes DRAはHAMiに取って代わるのか？CNCFブログ ([情報源](https://www.cncf.io/blog/2026/08/07/does-kubernetes-dra-replace-hami/))
- 2026-W31: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.36.3/v1.35.7/v1.34.10のパッチリリースとv1.37 Code Freezeの開始を反映
- 2026-W31: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — EKS Auto ModeのノードプールでEFAおよびEC2プレイスメントグループをサポートしたことを反映
- 2026-W31: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — KarpenterのノードプールでEFAおよびEC2プレイスメントグループをサポートしたことを反映
- 2026-W31: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — AMPの上限引き上げを反映（アクティブ系列15億、ワークスペースあたりのルール20万件）
- 2026-W31: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — OpenTelemetryのCNCF卒業を反映
- 2026-W31: [networking/calico/README.md](../networking/calico/README.md) — TigeraによるKubernetes上のVM向けCalicoの提供開始を反映（eBPFを基盤とするVMとコンテナの統合ネットワーキング）
- 2026-W31: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.0-rc.1リリース候補を反映
- 2026-W31: 該当ドキュメントなし — Confidential ContainersがCNCFのインキュベーションプロジェクトに ([情報源](https://www.cncf.io/blog/2026/07/22/confidential-containers-becomes-a-cncf-incubating-project/))
- 2026-W31: 該当ドキュメントなし — Kubernetes CSI driverで2件のパストラバーサルCVE（CVE-2026-3864 NFS / CVE-2026-3865 SMB。csi-driver-nfs v4.13.1、csi-driver-smb v1.20.1で修正）([情報源](https://www.sentinelone.com/blog/mount-here-read-there-twin-path-traversal-cves-in-kubernetes-storage/))
- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.19.6/1.18.12/1.17.18のパッチリリースとCVE-2026-56743（ipBlock NetworkPolicyの問題）を反映
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.30.3/1.29.6のパッチリリースを反映
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.7.1を反映（未定義のServiceポートへのリクエストが許可されなくなり、互換性を損なう変更）
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — EKS Auto ModeでのARCゾーンシフトと自動ゾーンシフトのサポートを反映
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — EKS Auto ModeでのARCゾーンシフトのサポートを反映
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenterの旧系列向けパッチリリース（v1.3.8～v1.11.3）を反映
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37.0-beta.0とv1.37のリリーススケジュールを反映
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCon Japan 2026と、今後開催されるArgo CD 3.5のロードマップセッションを反映
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — カスタムメトリクスエクスポーターに関するKubernetesブログのガイドを反映
- 2026-W30: 該当ドキュメントなし — HAMiがCNCFのインキュベーションプロジェクトに ([情報源](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/))
- 2026-W30: 該当ドキュメントなし — vLLMを使ってKubernetesでセルフホスト型LLMを実行する、CNCFブログ ([情報源](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/))
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — ACMEプロトコルのACMサポートを反映（ACMのパブリック証明書をcert-managerから利用可能に）
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — AIエージェント向けNGINX + OpenTelemetryのネットワーク境界オブザーバビリティパターンを反映
- 2026-W29: 該当ドキュメントなし — AIネイティブなワークロードに向けたプラットフォームエンジニアリングの進化、CNCFブログ ([情報源](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/))
- 2026年7月11日: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — etcd v3.7.0リリースを反映（RangeStreamなど）
- 2026年7月11日: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — EKS Auto ModeのGPU管理料金が最大60%引き下げられたことを反映
- 2026年7月11日: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.14.0リリースを反映（CapacityBuffers APIなど）
- 2026年7月11日: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — CloudWatch Application Signals Service Eventsを反映
- 2026年7月11日: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.4.5パッチリリースを反映
- 2026年7月11日: 該当ドキュメントなし — ingress-nginxの廃止（2026年3月）への対応、CNCFブログ ([情報源](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/))
- 2026年7月11日: 該当ドキュメントなし — CNCFの「Cloud Native AIにおけるデータストレージ」ホワイトペーパーを公開 ([情報源](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/))
- 2026年7月11日: 該当ドキュメントなし — Amazon EMR on EKSでApache Sparkのトラブルシューティングエージェントに対応 ([情報源](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/))
- 2026年7月11日: 該当ドキュメントなし — AWS Systems Managerのハイブリッド/マルチクラウドノード料金を大幅改定（Advanced Instances Tierを廃止）([情報源](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/))

</details>
