# Platform Engineering の概要

> **最終更新**: September 12, 2026

## 1. Platform Engineering とは？

### 定義

Platform Engineering は、**開発者のセルフサービスのためのツール、ワークフロー、インフラストラクチャを設計、構築、運用する分野**です。Platform Engineering チームは、開発者がインフラストラクチャの複雑さを直接扱うことなく、迅速かつ安全にアプリケーションをデプロイできるようにする **Internal Developer Platform (IDP)** を構築します。

### Internal Developer Platform (IDP)

IDP は、インフラストラクチャのプロビジョニング、デプロイ、モニタリングなどの運用タスクを抽象化するセルフサービスプラットフォームであり、開発者がコード作成に集中できるようにします。

**IDP のコアバリュー:**

- **セルフサービス**: API、CLI、またはポータルを通じて承認済みのリソースやアクションをリクエストする
- **ガードレール**: セキュリティポリシー、承認、監査経路を実装および検証する
- **標準化**: Golden Path を通じて一貫したデプロイパターンを提供する
- **自動化**: 反復タスクを排除して認知負荷を軽減する

### Platform Engineering vs DevOps vs SRE

| 観点 | Platform Engineering | DevOps | SRE |
|--------|---------------------|--------|-----|
| **焦点** | 開発者体験とセルフサービスプラットフォームの構築 | 開発と運用の文化的統合 | サービス信頼性と運用自動化 |
| **主な成果物** | Internal Developer Platform | CI/CD パイプライン、自動化スクリプト | SLO/SLI、エラーバジェット、トイル自動化 |
| **主要メトリクス** | 開発者の生産性、オンボーディング時間 | デプロイ頻度、リードタイム | 可用性、エラーバジェット消費率 |
| **チーム構造** | 専任のプラットフォームチーム | クロスファンクショナルチーム | SRE チームまたは組み込み SRE |
| **関係性** | DevOps および SRE と連携するプロダクト指向のプラットフォームプラクティス | 文化と方法論 | 運用エンジニアリングのプラクティス |

> **注記**: これら3つのアプローチは相互排他的ではなく、補完的です。Platform Engineering とは、**DevOps の原則と SRE のプラクティスをプロダクトとしてパッケージ化すること**です。

### プラットフォームチームの役割と構造

**主な役割:**

| 役割 | 責任 |
|------|---------------|
| **Platform Product Manager** | 開発者ニーズの分析、IDP ロードマップの管理、成功メトリクスの定義 |
| **Platform Engineer** | コア IDP インフラストラクチャ、Kubernetes/クラウド自動化の構築 |
| **Platform SRE** | プラットフォーム自体の信頼性、モニタリング、インシデント対応 |
| **Developer Experience (DX) Engineer** | CLI ツール、ドキュメント、オンボーディングワークフロー |

---

## 2. AWS CAF の Platform 観点

### AWS Cloud Adoption Framework の概要

[AWS CAF Platform perspective](https://docs.aws.amazon.com/whitepapers/latest/overview-aws-cloud-adoption-framework/platform-perspective.html) には、プラットフォームアーキテクチャ、データアーキテクチャ、Platform Engineering、データエンジニアリング、プロビジョニングとオーケストレーション、モダンアプリケーション開発、継続的インテグレーション/継続的デリバリーの7つのケイパビリティがあります。本ガイドでは Platform Engineering に焦点を当てます。

### 成熟度モデル: START → ADVANCE → EXCEL

AWS の詳細な Platform Engineering ガイドでは、改善タスクを Start、Advance、Excel に分類しています。以下の Kubernetes マッピング/チェックリストは本ガイドの学習用の例であり、公式の認定スコアカードや、すべての組織に必須の順序ではありません。

#### START: 基盤の構築

基盤インフラストラクチャを確立し、セキュリティガードレールを設定する段階です。

| ケイパビリティ | 説明 | Kubernetes エコシステムのマッピング |
|-----------|-------------|------------------------------|
| **Landing Zone & Guardrails** | マルチアカウント環境、予防的/検出的コントロール | EKS クラスター設定、[OPA Gatekeeper](../security/09-opa-gatekeeper.md) / [Kyverno](../security/01-kyverno-policy-management.md) |
| **Authentication** | 一元化されたアイデンティティ管理、IdP 統合 | [K8s Authentication & Authorization](../security/02-kubernetes-auth-authz.md)、OIDC、IRSA |
| **Networking** | 一元化されたネットワーク管理 | VPC CNI、[Calico](../networking/calico/README.md)、[Cilium](../networking/cilium/README.md) |
| **Observability** | ログ、メトリクス、トレースの収集と保護 | [Prometheus](../observability/metrics/01-prometheus.md)、[Loki](../observability/logging/01-loki.md)、[OpenTelemetry](../observability/tracing/03-opentelemetry.md) |
| **Controls** | プログラムによるセキュリティコントロール | [Pod Security Standards](../security/03-pod-security-standards.md)、[Network Policies](../security/04-network-policies.md) |
| **Cost Management** | タギング戦略、コスト配分 | 請求タグ、使用量とコストの配分、[EKS Cost Optimization](../eks/07-eks-cost-optimization.md) |

#### ADVANCE: 運用のスケーリング

自動化を拡張し、一元化された Observability を構築する段階です。

| ケイパビリティ | 説明 | Kubernetes エコシステムのマッピング |
|-----------|-------------|------------------------------|
| **Infrastructure Automation** | IaC、セルフサービスプロダクト | [ACK](./02-ack.md)、[KRO](./03-kro.md)、Crossplane、[Helm](./01-helm.md) |
| **Central Observability** | ログ/メトリクス/トレースの相関付け | [Grafana](../observability/grafana/README.md) Stack、[CloudWatch](../observability/metrics/04-cloudwatch-metrics.md) |
| **Systems Management** | イメージの標準化、パッチ管理 | [Image Security](../security/07-image-security.md)、[Kyverno](../security/01-kyverno-policy-management.md) |
| **Credential Management** | 一時的な認証情報、自動ローテーション | [Secrets Management](../security/05-secrets-management.md)、IRSA |
| **Security Tooling** | XDR、粒度の高いモニタリング | [Runtime Security](../security/08-runtime-security.md)、Trivy、GuardDuty |

#### EXCEL: 継続的最適化

自動化されたガバナンスと継続的改善を実現する段階です。

| ケイパビリティ | 説明 | Kubernetes エコシステムのマッピング |
|-----------|-------------|------------------------------|
| **Automated Identity Management** | IaC によるバージョン管理されたロール/ポリシー | [GitOps](../gitops/README.md) ベースの RBAC 管理 |
| **Anomaly Detection** | プロアクティブな脆弱性評価、異常パターン検出 | [Runtime Security](../security/08-runtime-security.md) (Falco)、監査ログ分析 |
| **Threat Analysis** | 業界ベンチマークに対する継続的モニタリング | CIS Benchmark、kube-bench |
| **Permission Refinement** | 最小権限の原則の自動化 | K8s 監査ログベースの RBAC 最適化 |
| **Platform Metrics** | 組織目標に整合したメトリクス | DORA メトリクス、SLI/SLO |

---

## 3. IDP リファレンスアーキテクチャ

### Kubernetes ベースの IDP レイヤー構造

```
┌─────────────────────────────────────────────────────┐
│            Developer Interface Layer                  │
│      (Backstage, Port, CLI, GitOps UI)               │
├─────────────────────────────────────────────────────┤
│         Integration/Orchestration Layer               │
│      (ArgoCD, FluxCD, Crossplane, KRO)               │
├─────────────────────────────────────────────────────┤
│                Resource Layer                         │
│      (ACK, Helm Charts, Operators, CRDs)             │
├─────────────────────────────────────────────────────┤
│              Infrastructure Layer                     │
│      (EKS, VPC, IAM, S3, RDS, ...)                   │
└─────────────────────────────────────────────────────┘
```

### 各レイヤーの役割とツールのマッピング

| レイヤー | 役割 | 主要ツール | リポジトリドキュメント |
|-------|------|-----------|-----------|
| **Developer Interface** | 開発者が操作する UI/CLI | Backstage、Port、Argo Workflows UI | [Backstage](./06-backstage-idp.md) |
| **Integration/Orchestration** | 宣言的な状態管理、デプロイ自動化 | ArgoCD、FluxCD、KRO | [GitOps](../gitops/README.md)、[KRO](./03-kro.md) |
| **Resource** | クラウド/K8s リソースの抽象化 | ACK、Helm、Operators | [ACK](./02-ack.md)、[Helm](./01-helm.md)、[K8s Extensions](./04-kubernetes-extensions.md) |
| **Infrastructure** | 実際のコンピュート/ネットワーク/ストレージ | EKS、VPC、IAM | [EKS](../eks/01-eks-introduction.md) |

### セルフサービスカタログパターン (KRO RGD + ACK)

[KRO](./03-kro.md) の ResourceGraphDefinition (RGD) と [ACK](./02-ack.md) を組み合わせることで、強力なセルフサービスパターンを実現できます。

```yaml
# Single manifest written by developers
apiVersion: kro.run/v1alpha1
kind: WebApplication
metadata:
  name: my-app
spec:
  name: my-app
  image: my-app:v1.0
  replicas: 3
  database:
    engine: postgresql
    instanceClass: db.t3.medium
```

上記の WebApplication は、Kubernetes/kro に組み込まれた kind ではなく、**事前に定義する必要があるカスタムプラットフォーム API** です。その RGD/生成された CRD がなければ、このオブジェクトは適用できません。この概要では、完全な RGD の提供やリソースの作成は行いません。

RGD が Deployment、Service、ACK RDS/IAM リソースを明示的に宣言すると、kro は Kubernetes オブジェクト/依存関係を管理し、関連する ACK サービスコントローラーが AWS API を呼び出します。結果として得られるリソースセットは、その RGD に依存します。コントローラー/CRD、RBAC/IAM、クォータ、準備状態/エラー、認証情報の配布、削除/保持ポリシーをそれぞれ検証してください。1つの CR を作成しても、AWS の即時の準備完了やトランザクション型のプロビジョニングが保証されるわけではありません。[ExampleCorp example](./05-example-corp-app.md) と [kro guide](./03-kro.md) を参照してください。

### Golden Path の概念

Golden Path は、プラットフォームチームが提供する**推奨デプロイパス**です。

- **目的**: 検証済みの方法を用いて開発者を迅速に開始へ導く
- **特性**: サポート対象の推奨パス。例外は組織の承認に従い、必須のセキュリティ/データポリシーを回避できない
- **例**:
  - 「新規 Microservice のデプロイ」Golden Path: 検証済み Helm テンプレート → ArgoCD 統合 → 設定済みのメトリクス公開/収集
  - 「データベースのプロビジョニング」Golden Path: 検証済み RGD → ACK RDS ライフサイクル → 承認済みの認証情報配布

---

## 4. Platform Engineering ツールエコシステム

このセクションでは、このリポジトリで扱うツールが Platform Engineering の全体像のどこに位置付くかを示します。

| カテゴリ | ツール | リポジトリドキュメントリンク |
|----------|-------|---------------|
| **パッケージ管理** | Helm、Kustomize | [Helm](./01-helm.md) |
| **AWS IaC** | ACK、CloudFormation | [ACK](./02-ack.md) |
| **リソースオーケストレーション** | KRO、Crossplane | [KRO](./03-kro.md) |
| **拡張メカニズム** | CRD、Operators | [Kubernetes Extension Mechanisms](./04-kubernetes-extensions.md) |
| **GitOps** | ArgoCD、FluxCD | [GitOps Section](../gitops/README.md) |
| **ポリシー/ガバナンス** | Kyverno、OPA Gatekeeper | [Kyverno](../security/01-kyverno-policy-management.md)、[OPA Gatekeeper](../security/09-opa-gatekeeper.md) |
| **Observability** | Prometheus、Grafana、OTel | [Observability Section](../observability/README.md) |
| **自動スケーリング** | KEDA、Karpenter | [KEDA](../autoscaling/01-keda.md)、[Karpenter](../autoscaling/02-karpenter.md) |
| **Service Mesh** | Istio、Cilium | [Istio](../service-mesh/istio/README.md)、[Cilium Service Mesh](../service-mesh/cilium-service-mesh/README.md) |
| **セキュリティ** | Falco、Trivy、PSS | [Runtime Security](../security/08-runtime-security.md)、[Image Security](../security/07-image-security.md)、[PSS](../security/03-pod-security-standards.md) |

---

## 5. Platform 成熟度セルフアセスメントチェックリスト

組織の Platform Engineering の成熟度を評価してください。各項目は、このリポジトリ内の関連ドキュメントにリンクしています。

### START ステージ

| チェック | 項目 | 関連ドキュメント |
|-------|------|-------------|
| [ ] | EKS クラスターは標準化された方法で作成されていますか？ | [EKS Cluster Creation](../eks/02-eks-cluster-creation-part1.md) |
| [ ] | RBAC ポリシーは定義および適用されていますか？ | [Authentication & Authorization](../security/02-kubernetes-auth-authz.md) |
| [ ] | Network Policies は適用されていますか？ | [Network Policies](../security/04-network-policies.md) |
| [ ] | 基本的なモニタリングとロギングは設定されていますか？ | [EKS Monitoring](../eks/06-eks-monitoring-logging.md) |
| [ ] | Pod Security Standards は適用されていますか？ | [PSS](../security/03-pod-security-standards.md) |
| [ ] | リソースクォータと上限は設定されていますか？ | [EKS Cost Optimization](../eks/07-eks-cost-optimization.md) |

### ADVANCE ステージ

| チェック | 項目 | 関連ドキュメント |
|-------|------|-------------|
| [ ] | インフラストラクチャは IaC で管理されていますか？ (ACK、Terraform など) | [ACK](./02-ack.md) |
| [ ] | GitOps ワークフローは導入されていますか？ | [GitOps](../gitops/README.md) |
| [ ] | 一元化された Observability スタックは運用されていますか？ | [Observability](../observability/README.md) |
| [ ] | ポリシーエンジンによってガバナンスは自動化されていますか？ | [Kyverno](../security/01-kyverno-policy-management.md) |
| [ ] | 外部ストアから Secret は自動的に管理されていますか？ | [Secrets Management](../security/05-secrets-management.md) |
| [ ] | コンテナイメージスキャンは自動化されていますか？ | [Image Security](../security/07-image-security.md) |

### EXCEL ステージ

| チェック | 項目 | 関連ドキュメント |
|-------|------|-------------|
| [ ] | 開発者にセルフサービスカタログが提供されていますか？ | [KRO](./03-kro.md)、[ExampleCorp](./05-example-corp-app.md) |
| [ ] | 適切なサービススコープで DORA メトリクスが測定/改善されていますか？ | [Current DORA definitions](https://dora.dev/guides/dora-metrics/) |
| [ ] | Runtime Security モニタリングは運用されていますか？ | [Runtime Security](../security/08-runtime-security.md) |
| [ ] | ワークロードに対して自動スケーリングは最適化されていますか？ | [KEDA](../autoscaling/01-keda.md)、[Karpenter](../autoscaling/02-karpenter.md) |
| [ ] | プラットフォーム SLO は定義および追跡されていますか？ | [Observability Analysis](../ops/08-observability-analysis.md) |
| [ ] | Golden Path は定義およびドキュメント化されていますか？ | このドキュメント（セクション3） |

---

### メトリクスとプラットフォームプロダクトの成功

現在の DORA ガイダンスでは、変更リードタイム、デプロイ頻度、失敗したデプロイの復旧時間、変更失敗率、デプロイの手戻り率という5つのメトリクスを説明しています。古い4つのメトリクスや汎用的な MTTR を現在の定義と混在させないでください。これらは個人のランキングではなく、サービス/チームのコンテキスト内でデリバリーと安定性を改善するために使用してください。また、オンボーディング時間、タスク成功率、ユーザー満足度、採用状況も測定してください。測定は Excel まで待つ必要はありません。

IDP はポータル以上のものです。API、CLI、テンプレート、ドキュメント、サポート、運用責任を含みます。アプリケーションセキュリティの責任すべてを開発チームから移管するものではありません。ガードレールの適用、例外、変更、復旧を検証してください。

## 6. 参考資料

- [AWS CAF Platform Perspective - Platform Engineering](https://docs.aws.amazon.com/prescriptive-guidance/latest/aws-caf-platform-perspective/platform-eng.html)
- [CNCF Platform White Paper](https://tag-app-delivery.cncf.io/whitepapers/platforms/)
- [Backstage.io - Open Source IDP Framework](https://backstage.io/)
- [Internal Developer Platform](https://internaldeveloperplatform.org/)

- [Current DORA metrics](https://dora.dev/guides/dora-metrics/)
