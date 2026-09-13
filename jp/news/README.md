# ニュース
> **最終更新**: September 12, 2026

Kubernetes、Amazon EKS、CNCFニュースを契機とした文書変更を記録します。GitHub Actionsは毎週月曜09:00 KSTに更新を準備し、品質判定通過後にPRを作成します。レビュー、マージ、デプロイ後にサイトへ反映されます。

週ラベルは記録週を示し、出典公開日と異なる場合があります。過去の記録です。現在のサポート、セキュリティパッチ、運用要件はリンク先ガイドと公式出典を確認してください。「該当文書なし」は当時の自動照合結果です。

## 更新履歴

- 2026-W36: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37「Garhwal」リリースを反映（Pod証明書/ClusterTrustBundleの安定化、Metrics API GA、kube-dnsとIPVSモードの非推奨化など）
- 2026-W36: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.30.4/1.29.7セキュリティパッチを反映（ISTIO-SECURITY-2026-006、Envoy CVE 13件）
- 2026-W36: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.5.2/v3.4.8パッチを反映
- 2026-W36: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.8.4を反映（TLSRoute API版のネゴシエーションなど）
- 2026-W36: 該当文書なし — Amazon EKSがクラスターあたり最大10外部OIDC identity providerをサポート（[出典](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-multiple-oidc-providers)）
- 2026-W36: 該当文書なし — 急増前にスケール: Kubernetes GPUワークロードの予測自動スケーリング、CNCFブログ（[出典](https://www.cncf.io/blog/2026/08/28/scale-before-the-spike-predictive-autoscaling-for-gpu-workloads-on-kubernetes/)）
- 2026-W36: 該当文書なし — Kubernetes上でAIファクトリーを構築、CNCFブログ（[出典](https://www.cncf.io/blog/2026/08/27/building-an-ai-factory-on-kubernetes/)）
- 2026-W35: [gitops/argocd/README.md](../gitops/argocd/README.md) — Amazon EKSのマネージドArgo CD機能のカスタム設定対応を反映（`argocd-cm` ConfigMap経由）
- 2026-W35: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.36.4/v1.35.8/v1.34.11パッチとv1.37.0-rc.1を反映
- 2026-W35: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.1/1.19.7/1.18.13パッチを反映
- 2026-W35: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.14.1パッチを反映
- 2026-W35: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.0-rc.0を反映（1.31がRC段階へ）
- 2026-W35: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — 遅いSQLクエリをOTelスパン由来メトリクスにまとめるCNCFブログガイドを反映
- 2026-W35: 該当文書なし — Amazon EKSが自動ライフサイクル管理による認証局（CA）ローテーションをサポート（[出典](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-certificate-authority-ca-rotation-automated-lifecycle-management)）
- 2026-W35: 該当文書なし — KubeflowがCNCFを卒業（[出典](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/)）
- 2026-W34: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.5.0 GAとv3.5.1/v3.4.7/v3.3.14パッチを反映
- 2026-W34: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.0-beta.1を反映（1.31がベータ段階へ）
- 2026-W34: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.8.2を反映（Gateway API 1.5.1対応、テスト最大k8s 1.36）
- 2026-W34: 該当文書なし — Amazon EKSが高度なKubernetes control-plane設定パラメーターをサポート（scheduler/controller manager/API server調整）（[出典](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-control-plane-configuration-parameters)）
- 2026-W34: 該当文書なし — Cloud Native BuildpacksがCNCF卒業プロジェクトに（[出典](https://www.cncf.io/announcements/2026/08/11/cncf-announces-graduation-of-cloud-native-buildpacks-advancing-the-standard-for-container-builds/)）
- 2026-W34: 該当文書なし — KubeCon + CloudNativeCon North America 2026の予定公開、新AI Inference + Agenticトラック追加（[出典](https://www.cncf.io/announcements/2026/08/10/cncf-reveals-kubecon-cloudnativecon-north-america-2026-schedule-adds-new-ai-inference-agentic-track/)）
- 2026-W34: 該当文書なし — Kubernetes YAMLをKYAMLできれいに整形する方法、Kubernetesブログ（[出典](https://kubernetes.io/blog/2026/08/11/how-to-pretty-print-kubernetes-yaml-as-kyaml/)）
- 2026-W33: [networking/04-gateway-api.md](../networking/04-gateway-api.md) — Gateway API v1.6を反映（TCPRoute/UDPRouteがStandard v1へ昇格、チャネル別の非推奨API提供変更）
- 2026-W33: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.5.0 GAを反映（Helm 4移行、source整合性検証alpha、ApplicationSet改善）
- 2026-W33: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.0 GA（Gateway API v1.6.1、KCNP、multi-pool IPAM移行）と1.21.0-pre.0を反映
- 2026-W33: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37の先行紹介、Docs Freeze開始、v1.38.0-alpha.0タグを反映
- 2026-W33: 該当文書なし — Amazon ECRがDocker pushで最大200 GBのimage layerをサポート（[出典](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-ecr-image-layers/)）
- 2026-W33: 該当文書なし — K8gbがCNCFインキュベーションプロジェクトに（[出典](https://www.cncf.io/announcements/2026/08/05/k8gb-becomes-a-cncf-incubating-project/)）
- 2026-W33: 該当文書なし — OpenCost 1.121.0がKubernetes推論費用追跡を追加（[出典](https://www.cncf.io/blog/2026/08/05/opencost-1-121-0-first-of-a-kind-kubernetes-inference-cost-tracking/)）
- 2026-W33: 該当文書なし — Kubernetes DRAはHAMiを置き換えるのか、CNCFブログ（[出典](https://www.cncf.io/blog/2026/08/07/does-kubernetes-dra-replace-hami/)）
- 2026-W31: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.36.3/v1.35.7/v1.34.10パッチとv1.37 Code Freeze開始を反映
- 2026-W31: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — EKS Auto Mode node poolのEFA/EC2配置グループ対応を反映
- 2026-W31: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter node poolのEFA/EC2配置グループ対応を反映
- 2026-W31: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — AMP上限引き上げを反映（1ワークスペースあたり1.5B active series、200Kルール）
- 2026-W31: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — OpenTelemetryのCNCF卒業を反映
- 2026-W31: [networking/calico/README.md](../networking/calico/README.md) — TigeraのKubernetes上VM向けCalico公開を反映（eBPFベースのVM+container統合network）
- 2026-W31: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.0-rc.1リリース候補を反映
- 2026-W31: 該当文書なし — Confidential ContainersがCNCFインキュベーションプロジェクトに（[出典](https://www.cncf.io/blog/2026/07/22/confidential-containers-becomes-a-cncf-incubating-project/)）
- 2026-W31: 該当文書なし — Kubernetes CSI driverの2つのpath traversal CVE（CVE-2026-3864 NFS / CVE-2026-3865 SMB。csi-driver-nfs v4.13.1、csi-driver-smb v1.20.1で修正）（[出典](https://www.sentinelone.com/blog/mount-here-read-there-twin-path-traversal-cves-in-kubernetes-storage/)）
- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.19.6/1.18.12/1.17.18パッチとCVE-2026-56743を反映（ipBlock NetworkPolicy問題）
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.30.3/1.29.6パッチを反映
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.7.1を反映（未定義Service portへの要求禁止、破壊的変更）
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — EKS Auto ModeのARC zonal shift/autoshift対応を反映
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — EKS Auto ModeのARC zonal shift対応を反映
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter旧系列のパッチを反映（v1.3.8–v1.11.3）
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37.0-beta.0とv1.37リリース予定を反映
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCon Japan 2026と今後のArgo CD 3.5 roadmapセッションを反映
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — Kubernetesブログのカスタムmetrics exporterガイドを反映
- 2026-W30: 該当文書なし — HAMiがCNCFインキュベーションプロジェクトに（[出典](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/)）
- 2026-W30: 該当文書なし — vLLMでKubernetesに自己ホストLLMを実行、CNCFブログ（[出典](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/)）
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — ACMのACMEプロトコル対応を反映（cert-managerからACM公開証明書を利用可能）
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — AI agent向けNGINX + OpenTelemetryのnetwork境界可観測性パターンを反映
- 2026-W29: 該当文書なし — AIネイティブworkloadに向けたplatform engineeringの進化、CNCFブログ（[出典](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/)）
- 2026-07-11: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — etcd v3.7.0を反映（RangeStreamなど）
- 2026-07-11: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — EKS Auto Mode GPU管理料の最大60%削減を反映
- 2026-07-11: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.14.0を反映（CapacityBuffers APIなど）
- 2026-07-11: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — CloudWatch Application Signals Service Eventsを反映
- 2026-07-11: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.4.5パッチを反映
- 2026-07-11: 該当文書なし — ingress-nginx終了（March 2026）への対応、CNCFブログ（[出典](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/)）
- 2026-07-11: 該当文書なし — CNCF「クラウドネイティブAIにおけるデータストレージ」白書公開（[出典](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/)）
- 2026-07-11: 該当文書なし — Amazon EMR on EKSがApache Sparkトラブルシューティングagentをサポート（[出典](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/)）
- 2026-07-11: 該当文書なし — AWS Systems Managerのhybrid/multicloud node料金体系刷新（Advanced Instances Tier廃止）（[出典](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/)）
