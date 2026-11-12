# ニュース
> **最終更新日**: 2026年10月26日

このページでは、Kubernetes、Amazon EKS、CNCFのニュースを受けて行ったドキュメントの変更を記録しています。GitHub Actionsは毎週月曜日の09:00 KSTに更新を準備し、品質ゲートに合格するとPRを作成します。レビュー、マージ、デプロイの後、変更がサイトに反映されます。

週ラベルはログ項目の週を示すもので、情報源の公開日とは異なる場合があります。これらは過去の記録です。現在のサポート状況、セキュリティパッチ、運用要件については、リンク先のガイドと公式情報を確認してください。「対応する文書なし」は、その時点で自動照合した結果を示します。

<!-- news-dashboard -->

<details class="news-log">
<summary>更新ログ全体を展開</summary>

## 更新ログ

- 2026-W44: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.3/1.30.7/1.29.10のセキュリティパッチリリースを反映（ISTIO-SECURITY-2026-008、CVE-2026-111943: 侵害されたeMudhra中間CA証明書を信頼しないように変更。1.29.10はEOL後の例外的なリリース） ([source](https://istio.io/latest/news/security/istio-security-2026-008/))
- 2026-W44: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.4/1.19.10/1.18.16の臨時セキュリティパッチリリースを反映（CVE-2026-111943。Go 1.26.10では、侵害されたeMudhra中間CA証明書が信頼されなくなった） ([source](https://github.com/cilium/cilium/releases/tag/v1.20.4))
- 2026-W44: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.5.6/v3.4.12/v3.3.17のバグ修正パッチリリースと、侵害されたeMudhra CA証明書への信頼を削除するセキュリティ修正を含むv3.3.18を反映 ([source](https://github.com/argoproj/argo-cd/releases/tag/v3.3.18))
- 2026-W44: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.6.0-rc4のリリース候補版を反映 ([source](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc4))
- 2026-W44: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.15.1のパッチリリースとv1.14.2/v1.14.3/v1.9.3のLTSパッチリリースを反映（バグ修正。すべての系列がGo 1.26.10に移行し、侵害されたeMudhra中間CA証明書が信頼されなくなった） ([source](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.15.1))
- 2026-W44: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — OpenTelemetry CollectorでAIエージェントのテレメトリーをフィルタリングおよび削減する方法について、CNCFブログのガイドを反映 ([source](https://www.cncf.io/blog/2026/10/22/filtering-and-reducing-ai-agent-telemetry-with-the-opentelemetry-collector/))
- 2026-W44: 対応する文書なし — Amazon EMR on EKSでEMR料金（vCPU時間あたりおよびGB時間あたり）が30パーセント引き下げ。基盤となるEKS料金に変更はなし ([source](https://aws.amazon.com/about-aws/whats-new/2026/10/emr-eks-reduces-emr-charge-30-percent/))
- 2026-W44: 対応する文書なし — AIワークロードがKubernetesのオートスケーリングをどのように変えているか、CNCFブログ ([source](https://www.cncf.io/blog/2026/10/19/how-ai-workloads-are-reshaping-kubernetes-autoscaling/))
- 2026-W43: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.2/1.30.6/1.29.9のパッチリリースが公開（ISTIO-SECURITY-2026-007のセキュリティパッチを含む。以前のレビューでドキュメントにはすでに反映済み） ([source](https://istio.io/news/releases/1.31.x/announcing-1.31.2/))
- 2026-W43: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.3/1.19.9/1.18.15のパッチリリースを反映（conntrack GCや`nodeSelector`を使用するCNPの処理などのバグ修正） ([source](https://github.com/cilium/cilium/releases/tag/v1.20.3))
- 2026-W43: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.5.5/v3.4.11/v3.3.16のバグ修正パッチリリースを反映 ([source](https://github.com/argoproj/argo-cd/releases/tag/v3.5.5))
- 2026-W43: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.6.0-rc3のリリース候補版を反映 ([source](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc3))
- 2026-W43: [security/14-waf-edge-api-security.md](../security/14-waf-edge-api-security.md) — CloudFront VPC originsのデュアルスタック（IPv6）サポートの発表を反映 ([source](https://aws.amazon.com/about-aws/whats-new/2026/10/cloudfront-vpc-origin-dualstack/))
- 2026-W43: [blockchain/01-fundamentals.md](../blockchain/01-fundamentals.md) — AWSでのBlockchain Snapshotsの提供開始を反映（Ethereum/Solanaノードのブートストラップ向け、事前同期済みの無料スナップショット） ([source](https://aws.amazon.com/about-aws/whats-new/2026/10/blockchain-snapshots-node-bootstrapping/))
- 2026-W43: [security/01-kyverno-policy-management.md](../security/01-kyverno-policy-management.md) — Kyverno向けNirmata Runtimeの紹介を行うCNCFブログを反映（eBPF/LSMを介したカーネルレベルのランタイムポリシー適用） ([source](https://www.cncf.io/blog/2026/10/15/extending-kubernetes-policy-enforcement-to-runtime-security-for-ai-workloads/))
- 2026-W43: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — Software Carbon Intensity（SCI）をOpenTelemetryのセマンティック規約として扱う提案を行うCNCFブログを反映 ([source](https://www.cncf.io/blog/2026/10/15/carbon-as-a-first-class-signal-bringing-software-carbon-intensity-to-opentelemetry/))
- 2026-W43: 対応する文書なし — Headlampを使用してKueueが管理するJobのadmission状態を追跡する方法、Kubernetesブログ ([source](https://kubernetes.io/blog/2026/10/14/tracing-kueue-admission-with-headlamp/))
- 2026-W42: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.15.0のリリースを反映（再起動をサポートする任意の中断としてのノード修復、KubeletConfigurationでのCEL、DRAサポートの拡大など）
- 2026-W42: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.5.4/v3.4.10/v3.3.15のセキュリティパッチリリースを反映（repo-serverのコマンド実行、CVE-2026-77459を含む4件のCRITICAL問題）
- 2026-W42: [kernel/01-container-primitives.md](../kernel/01-container-primitives.md) — cgroup v1の非推奨化状況に関するKubernetesブログの内容を反映（v1.35から`failCgroupV1`のデフォルト値が`true`に）
- 2026-W42: 対応する文書なし — NVMe SSDを使ったノードスワップによるKubernetesワークロードのスケーリング（v1.34でGA）、Kubernetesブログ ([source](https://kubernetes.io/blog/2026/10/05/scaling-kubernetes-workloads-with-node-swap/))
- 2026-W42: 対応する文書なし — MesheryがCNCFのインキュベーションプロジェクトに ([source](https://www.cncf.io/blog/2026/10/07/meshery-becomes-a-cncf-incubating-project/))
- 2026-W42: 対応する文書なし — AWS BatchがAmazon EKSのアクセスエントリー認証に対応 ([source](https://aws.amazon.com/about-aws/whats-new/2026/10/aws-batch-access-entries/))
- 2026-W41: [eks/08-eks-upgrades.md](../eks/08-eks-upgrades.md) — Amazon EKSとEKS DistroでのKubernetes 1.37サポートを反映（Metrics APIがGA、DRAデバイスtaintがGA、HPAのゼロへのスケールがベータ）
- 2026-W41: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD 4.0のビジョン策定開始とArgoCon North America 2026のニュースを反映
- 2026-W41: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — OTel、Kafka、Flinkを用いたAtlassianのインシデント検出の再構築を反映（CNCFブログ）
- 2026-W41: 対応する文書なし — Amazon ECSがblue/green、linear、canaryのデプロイでAmazon VPC Latticeをサポート ([source](https://aws.amazon.com/about-aws/whats-new/2026/10/amazon-ecs-vpc-lattice-blue-green-deployments))
- 2026-W41: 対応する文書なし — Amazon Managed GrafanaでGrafana 13.2ワークスペースの作成が可能に ([source](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-managed-grafana-now-supports-creating-grafana-13-2-workspaces))
- 2026-W41: 対応する文書なし — Grafana Tempo 3.1のリリース（Kafkaの新機能、TraceQLメトリクスの更新、トレースの秘匿化など） ([source](https://grafana.com/blog/tempo-3-1-release-all-the-latest-features))
- 2026-W41: 対応する文書なし — ゲートではなくガードレール：プラットフォームチームにおけるポリシーの再考、CNCFブログ ([source](https://www.cncf.io/blog/2026/10/01/guardrails-not-gates-rethinking-policy-in-platform-teams/))
- 2026-W40: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37.1/v1.36.5/v1.35.9/v1.34.12のパッチリリースと、v1.37のPVC `Unused` condition（ベータ）に関するブログ記事を反映
- 2026-W40: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.1/1.30.5/1.29.8のパッチリリースを反映（BackendTLSPolicyのfail-openに関するセキュリティ修正GHSA-qm8v-g4f9-qhjxを含む）
- 2026-W40: [eks/04-eks-storage-part1.md](../eks/04-eks-storage-part1.md) — EFS CSI driverのマウントオプション注入の脆弱性CVE-2026-6437を反映（v3.0.1で修正）
- 2026-W40: [ai-ml/08-llm-gateway.md](../ai-ml/08-llm-gateway.md) — Amazon SageMaker HyperPod Inference Gatewayの提供開始を反映（EKS管理アドオン、GPUを考慮したルーティング）
- 2026-W40: 対応する文書なし — Amazon EMR on EKSがIPv6のAmazon EKSクラスターに対応 ([source](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-emr-eks-ipv6-support))
- 2026-W40: 対応する文書なし — Spark Connectを使ってAmazon EMR on EKSでインタラクティブなワークロードを実行 ([source](https://aws.amazon.com/about-aws/whats-new/2026/09/emr-eks-spark-connect-interactive/))
- 2026-W40: 対応する文書なし — Amazon CloudWatch Omniが一般提供開始（AIを中心に据えたオブザーバビリティ体験、OpenTelemetryとの相互運用性） ([source](https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-cloudwatch-omni-ai/))
- 2026-W39: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37の3つの機能を詳しく解説した内容を反映（Memory QoSがベータ、Pod-Level Resource Managersがベータ、emptyDirの権限とbind mountオプション）
- 2026-W39: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.2/1.19.8/1.18.14のパッチリリースと、CNCFブログの1.20機能まとめを反映
- 2026-W39: [gitops/argocd/README.md](../gitops/argocd/README.md) — Argo CD v3.5.3/v3.4.9のパッチリリースとv3.6.0-rc1を反映
- 2026-W39: 対応する文書なし — Kubernetes CSI Changed Block Tracking（CBT）APIがベータに昇格。アルファ版との違いについて、Kubernetesブログ ([source](https://kubernetes.io/blog/2026/09/14/csi-changed-block-tracking-beta/))
- 2026-W39: 対応する文書なし — AWS Resilience Hubに3つの新機能が追加（EKSラベルに基づく、namespace内のサービスリソース検出など） ([source](https://aws.amazon.com/about-aws/whats-new/2026/09/resilience-hub-eks-dependency-policy/))
- 2026-W38: [core/08-scheduling-preemption-eviction.md](../core/08-scheduling-preemption-eviction.md) — Kubernetes v1.37でのインプレースPodサイズ変更に対するschedulerのpreemption（アルファ）と、Workload-Aware Schedulingの進展（Workload/PodGroupがベータ、CompositePodGroup API）を反映
- 2026-W38: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37のNodeライフサイクルconditionを反映（drain、メンテナンス、グレースフルシャットダウン向けの、よく知られた5つのcondition）
- 2026-W38: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — Kubernetes v1.37のコンポーネントメトリクス向けPrometheusネイティブヒストグラムを反映（ベータ、デフォルトで有効）
- 2026-W38: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.21.0-pre.2のプレリリースを反映（Gateway APIのセッション維持、AWSの管理プレフィックスリスト、デフォルトでのBPF masquerading）
- 2026-W38: 対応する文書なし — KarmadaがCNCFのGraduatedプロジェクトに ([source](https://www.cncf.io/announcements/2026/09/07/cloud-native-computing-foundation-announces-karmada-graduation/))
- 2026-W38: 対応する文書なし — Kubernetesの災害復旧：再現可能な3つの障害シナリオから得たガイダンス、CNCFブログ ([source](https://www.cncf.io/blog/2026/09/10/kubernetes-disaster-recovery-guidance-from-three-reproducible-failure-scenarios/))
- 2026-W38: 対応する文書なし — AWS GovCloud (US)でAWS Private CA EKS add-onとConnector for ADが利用可能に ([source](https://aws.amazon.com/about-aws/whats-new/2026/09/private-ca-eks-addon-ad-govcloud/))
- 2026-W36: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37「Garhwal」リリースを反映（Pod certificates/ClusterTrustBundlesがStable、Metrics APIがGA、kube-dnsおよびIPVSモードの非推奨化など）
- 2026-W36: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.30.4/1.29.7のセキュリティパッチリリースを反映（ISTIO-SECURITY-2026-006、EnvoyのCVE 13件）
- 2026-W36: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.5.2/v3.4.8のパッチリリースを反映
- 2026-W36: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.8.4を反映（TLSRoute APIバージョンのネゴシエーションなど）
- 2026-W36: 対応する文書なし — Amazon EKSでクラスターあたり最大10個の外部OIDC IDプロバイダーをサポート ([source](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-multiple-oidc-providers))
- 2026-W36: 対応する文書なし — 急増の前にスケールする：KubernetesのGPUワークロード向け予測オートスケーリング、CNCFブログ ([source](https://www.cncf.io/blog/2026/08/28/scale-before-the-spike-predictive-autoscaling-for-gpu-workloads-on-kubernetes/))
- 2026-W36: 対応する文書なし — Kubernetes上にAIファクトリーを構築する、CNCFブログ ([source](https://www.cncf.io/blog/2026/08/27/building-an-ai-factory-on-kubernetes/))
- 2026-W35: [gitops/argocd/README.md](../gitops/argocd/README.md) — Amazon EKS管理のArgo CD機能でのカスタム設定サポート（`argocd-cm` ConfigMap経由）を反映
- 2026-W35: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.36.4/v1.35.8/v1.34.11のパッチリリースとv1.37.0-rc.1を反映
- 2026-W35: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.1/1.19.7/1.18.13のパッチリリースを反映
- 2026-W35: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.14.1のパッチリリースを反映
- 2026-W35: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.0-rc.0のリリースを反映（1.31がRC段階に移行）
- 2026-W35: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 遅いSQLクエリをOTel span由来のメトリクスに変換するCNCFブログのガイドを反映
- 2026-W35: 対応する文書なし — Amazon EKSが自動ライフサイクル管理による証明機関（CA）のローテーションに対応 ([source](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-certificate-authority-ca-rotation-automated-lifecycle-management))
- 2026-W35: 対応する文書なし — KubeflowがCNCF内でGraduatedに昇格 ([source](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/))
- 2026-W34: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.5.0のGAリリースとv3.5.1/v3.4.7/v3.3.14のパッチリリースを反映
- 2026-W34: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.0-beta.1のリリースを反映（1.31がベータ段階に移行）
- 2026-W34: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.8.2を反映（Gateway API 1.5.1のサポート、テスト済みの最大k8sバージョンは1.36）
- 2026-W34: 対応する文書なし — Amazon EKSがKubernetes control planeの高度な設定パラメーター（scheduler/controller manager/API serverのチューニング）に対応 ([source](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-control-plane-configuration-parameters))
- 2026-W34: 対応する文書なし — Cloud Native BuildpacksがCNCFのGraduatedプロジェクトに ([source](https://www.cncf.io/announcements/2026/08/11/cncf-announces-graduation-of-cloud-native-buildpacks-advancing-the-standard-for-container-builds/))
- 2026-W34: 対応する文書なし — KubeCon + CloudNativeCon North America 2026のスケジュールを公開。新たにAI Inference + Agenticトラックを追加 ([source](https://www.cncf.io/announcements/2026/08/10/cncf-reveals-kubecon-cloudnativecon-north-america-2026-schedule-adds-new-ai-inference-agentic-track/))
- 2026-W34: 対応する文書なし — Kubernetes YAMLをKYAMLとして整形出力する方法、Kubernetesブログ ([source](https://kubernetes.io/blog/2026/08/11/how-to-pretty-print-kubernetes-yaml-as-kyaml/))
- 2026-W33: [networking/04-gateway-api.md](../networking/04-gateway-api.md) — Gateway API v1.6を反映（TCPRoute/UDPRouteがStandard v1に昇格、チャネル固有の非推奨API提供方法の変更）
- 2026-W33: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.5.0のGAを反映（Helm 4への移行、ソース整合性検証のアルファ機能、ApplicationSetの改善）
- 2026-W33: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.0のGA（Gateway API v1.6.1、KCNP、マルチプールIPAMの移行）と1.21.0-pre.0を反映
- 2026-W33: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37の先行情報、Docs Freezeの開始、v1.38.0-alpha.0タグを反映
- 2026-W33: 対応する文書なし — Amazon ECRがDocker pushで最大200 GBのイメージレイヤーに対応 ([source](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-ecr-image-layers/))
- 2026-W33: 対応する文書なし — K8gbがCNCFのインキュベーションプロジェクトに ([source](https://www.cncf.io/announcements/2026/08/05/k8gb-becomes-a-cncf-incubating-project/))
- 2026-W33: 対応する文書なし — OpenCost 1.121.0でKubernetesの推論コスト追跡機能を追加 ([source](https://www.cncf.io/blog/2026/08/05/opencost-1-121-0-first-of-a-kind-kubernetes-inference-cost-tracking/))
- 2026-W33: 対応する文書なし — Kubernetes DRAはHAMiに取って代わるのか？、CNCFブログ ([source](https://www.cncf.io/blog/2026/08/07/does-kubernetes-dra-replace-hami/))
- 2026-W31: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.36.3/v1.35.7/v1.34.10のパッチリリースと、v1.37のCode Freeze開始を反映
- 2026-W31: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — EKS Auto ModeのノードプールでのEFAおよびEC2 placement groupのサポートを反映
- 2026-W31: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — KarpenterのノードプールでのEFAおよびEC2 placement groupのサポートを反映
- 2026-W31: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — AMPの上限引き上げを反映（アクティブ系列15億件、ワークスペースあたりルール20万件）
- 2026-W31: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — OpenTelemetryのCNCF Graduatedへの昇格を反映
- 2026-W31: [networking/calico/README.md](../networking/calico/README.md) — TigeraによるKubernetes上のVM向けCalicoの提供開始を反映（eBPFベースのVMとコンテナの統合ネットワーキング）
- 2026-W31: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.0-rc.1のリリース候補版を反映
- 2026-W31: 対応する文書なし — Confidential ContainersがCNCFのインキュベーションプロジェクトに ([source](https://www.cncf.io/blog/2026/07/22/confidential-containers-becomes-a-cncf-incubating-project/))
- 2026-W31: 対応する文書なし — Kubernetes CSI driverで発見された2件のパストラバーサルCVE（CVE-2026-3864 NFS / CVE-2026-3865 SMB。csi-driver-nfs v4.13.1、csi-driver-smb v1.20.1で修正） ([source](https://www.sentinelone.com/blog/mount-here-read-there-twin-path-traversal-cves-in-kubernetes-storage/))
- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.19.6/1.18.12/1.17.18のパッチリリースとCVE-2026-56743（ipBlock NetworkPolicyの問題）を反映
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.30.3/1.29.6のパッチリリースを反映
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.7.1を反映（未定義のServiceポートへのリクエストを許可しない、互換性を損なう変更）
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — EKS Auto ModeでのARC zonal shift/autoshiftサポートを反映
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — EKS Auto ModeでのARC zonal shiftサポートを反映
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — 古い系列向けのKarpenterパッチリリース（v1.3.8–v1.11.3）を反映
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37.0-beta.0とv1.37のリリーススケジュールを反映
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCon Japan 2026と、今後開催されるArgo CD 3.5ロードマップセッションを反映
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — カスタムメトリクスexporterに関するKubernetesブログのガイドを反映
- 2026-W30: 対応する文書なし — HAMiがCNCFのインキュベーションプロジェクトに ([source](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/))
- 2026-W30: 対応する文書なし — vLLMを使ってKubernetesでセルフホスト型LLMを実行する方法、CNCFブログ ([source](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/))
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — ACMEプロトコルのACMサポートを反映（ACMのパブリック証明書をcert-managerから利用可能に）
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — AIエージェント向けの、NGINX + OpenTelemetryを用いたネットワーク境界のオブザーバビリティパターンを反映
- 2026-W29: 対応する文書なし — AIネイティブなワークロードに向けたプラットフォームエンジニアリングの進化、CNCFブログ ([source](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/))
- 2026年7月11日: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — etcd v3.7.0のリリースを反映（RangeStreamなど）
- 2026年7月11日: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — EKS Auto ModeのGPU管理料金が最大60%引き下げられたことを反映
- 2026年7月11日: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.14.0のリリースを反映（CapacityBuffers APIなど）
- 2026年7月11日: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — CloudWatch Application Signals Service Eventsを反映
- 2026年7月11日: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.4.5のパッチリリースを反映
- 2026年7月11日: 対応する文書なし — ingress-nginxの廃止への対応（2026年3月）、CNCFブログ ([source](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/))
- 2026年7月11日: 対応する文書なし — CNCFの「Data Storage in Cloud Native AI」ホワイトペーパーを公開 ([source](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/))
- 2026年7月11日: 対応する文書なし — Amazon EMR on EKSがApache Sparkトラブルシューティングエージェントに対応 ([source](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/))
- 2026年7月11日: 対応する文書なし — AWS Systems Managerのハイブリッド/マルチクラウドノードの料金体系を刷新（Advanced Instances Tierを廃止） ([source](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/))

</details>
