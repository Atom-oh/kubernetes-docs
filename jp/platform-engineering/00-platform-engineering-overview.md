# Platform Engineering 概要

> **最終更新**: February 23, 2026

## 1. Platform Engineering とは？

### 定義

Platform Engineering は、**開発者がセルフサービスで利用できるツール、ワークフロー、インフラストラクチャを設計、構築、運用する分野**です。Platform engineering チームは、開発者がインフラストラクチャの複雑さに直接対処することなく、アプリケーションを迅速かつ安全にデプロイできるようにする **Internal Developer Platform (IDP)** を構築します。

### Internal Developer Platform (IDP)

IDP は、インフラストラクチャのプロビジョニング、デプロイ、監視などの運用タスクを抽象化し、開発者がコードを書くことに集中できるようにするセルフサービスプラットフォームです。

**IDP の中核的価値:**

- **セルフサービス**: 開発者はチケットを起票せずにインフラストラクチャを直接プロビジョニングできる
- **ガードレール**: セキュリティとコンプライアンスがデフォルトで組み込まれている
- **標準化**: Golden Paths を通じた一貫したデプロイパターン
- **自動化**: 反復的なタスクを排除して認知負荷を削減する

### Platform Engineering vs DevOps vs SRE

| 観点 | Platform Engineering | DevOps | SRE |
|--------|---------------------|--------|-----|
| **焦点** | 開発者体験とセルフサービスプラットフォームの構築 | 開発と運用の文化的統合 | サービス信頼性と運用自動化 |
| **主要な成果物** | Internal Developer Platform | CI/CD pipelines, automation scripts | SLO/SLI, error budgets, toil automation |
| **主要指標** | 開発者生産性、オンボーディング時間 | デプロイ頻度、リードタイム | 可用性、error budget 消費率 |
| **チーム構造** | 専任の platform team | クロスファンクショナルチーム | SRE team または組み込み SRE |
| **関係性** | DevOps + SRE の上にあるプロダクト層 | 文化と方法論 | 運用エンジニアリングの実践 |

> **注記**: これら 3 つのアプローチは相互排他的ではなく、補完的なものです。Platform Engineering とは、**DevOps の原則と SRE の実践をプロダクトとしてパッケージ化すること**です。

### Platform Team の役割と構造

**主要な役割:**

| 役割 | 責任 |
|------|---------------|
| **Platform Product Manager** | 開発者のニーズを分析し、IDP ロードマップを管理し、成功指標を定義する |
| **Platform Engineer** | 中核となる IDP インフラストラクチャ、Kubernetes/cloud automation を構築する |
| **Platform SRE** | プラットフォーム自体の信頼性、監視、インシデント対応 |
| **Developer Experience (DX) Engineer** | CLI tools、ドキュメント、オンボーディングワークフロー |

---

## 2. AWS CAF Platform Perspective

### AWS Cloud Adoption Framework の紹介

[AWS Cloud Adoption Framework (CAF)](https://docs.aws.amazon.com/prescriptive-guidance/latest/aws-caf-platform-perspective/platform-eng.html) は、クラウド導入のための組織的なガイドラインを提供します。**Platform Perspective** は、次の 3 つの主要領域を扱います。

1. **Platform Engineering** -- このセクションの焦点
2. **Platform Architecture** -- クラウドアーキテクチャ設計の原則
3. **Data Architecture** -- データ管理と分析戦略

### 成熟度モデル: START → ADVANCE → EXCEL

AWS CAF は、クラウドプラットフォームの成熟度を 3 つの段階で定義しています。Kubernetes ecosystem tools が各段階にどのように対応するかを見ていきます。

#### START: 基盤構築

基盤となるインフラストラクチャを確立し、セキュリティガードレールを設定する段階です。

| 能力 | 説明 | Kubernetes Ecosystem Mapping |
|-----------|-------------|------------------------------|
| **Landing Zone & Guardrails** | マルチアカウント環境、予防的/検知的コントロール | EKS cluster configuration, [OPA Gatekeeper](../security/09-opa-gatekeeper.md) / [Kyverno](../security/01-kyverno-policy-management.md) |
| **Authentication** | 集中型 identity management、IdP integration | [K8s Authentication & Authorization](../security/02-kubernetes-auth-authz.md), OIDC, IRSA |
| **Networking** | 集中型 network management | VPC CNI, [Calico](../networking/calico/README.md), [Cilium](../networking/cilium/README.md) |
| **Logging** | クロスアカウント observability | [Prometheus](../observability/metrics/01-prometheus.md), [Loki](../observability/logging/01-loki.md), [OpenTelemetry](../observability/tracing/03-opentelemetry.md) |
| **Controls** | プログラム可能な security controls | [Pod Security Standards](../security/03-pod-security-standards.md), [Network Policies](../security/04-network-policies.md) |
| **Cost Management** | Tagging strategy、cost allocation | Resource Quotas, LimitRange, [EKS Cost Optimization](../eks/07-eks-cost-optimization.md) |

#### ADVANCE: 運用のスケーリング

自動化を拡張し、集中型 observability を構築する段階です。

| 能力 | 説明 | Kubernetes Ecosystem Mapping |
|-----------|-------------|------------------------------|
| **Infrastructure Automation** | IaC、セルフサービスプロダクト | [ACK](./02-ack.md), [KRO](./03-kro.md), Crossplane, [Helm](./01-helm.md) |
| **Central Observability** | Log/metric/trace の相関 | [Grafana](../observability/grafana/README.md) Stack, [CloudWatch](../observability/metrics/04-cloudwatch-metrics.md) |
| **Systems Management** | Image standardization、patch management | [Image Security](../security/07-image-security.md), [Kyverno](../security/01-kyverno-policy-management.md) |
| **Credential Management** | 一時 credentials、自動 rotation | [Secrets Management](../security/05-secrets-management.md), IRSA |
| **Security Tooling** | XDR、きめ細かな monitoring | [Runtime Security](../security/08-runtime-security.md), Trivy, GuardDuty |

#### EXCEL: 継続的最適化

自動化されたガバナンスと継続的改善を達成する段階です。

| 能力 | 説明 | Kubernetes Ecosystem Mapping |
|-----------|-------------|------------------------------|
| **Automated Identity Management** | IaC による version-controlled roles/policies | [GitOps](../gitops/README.md)-based RBAC management |
| **Anomaly Detection** | プロアクティブな脆弱性評価、異常パターン検知 | [Runtime Security](../security/08-runtime-security.md) (Falco), audit log analysis |
| **Threat Analysis** | 業界 benchmarks に対する継続的 monitoring | CIS Benchmark, kube-bench |
| **Permission Refinement** | 自動化された least privilege principle | K8s audit log-based RBAC optimization |
| **Platform Metrics** | 組織目標に整合した metrics | DORA metrics, SLI/SLO |

---

## 3. IDP Reference Architecture

### Kubernetes-Based IDP Layer Structure

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

### 各レイヤーの役割とツールの対応

| レイヤー | 役割 | 主要ツール | Repo Docs |
|-------|------|-----------|-----------|
| **Developer Interface** | 開発者が操作する UI/CLI | Backstage, Port, Argo Workflows UI | - |
| **Integration/Orchestration** | 宣言的な状態管理、deployment automation | ArgoCD, FluxCD, KRO | [GitOps](../gitops/README.md), [KRO](./03-kro.md) |
| **Resource** | cloud/K8s resources の抽象化 | ACK, Helm, Operators | [ACK](./02-ack.md), [Helm](./01-helm.md), [K8s Extensions](./04-kubernetes-extensions.md) |
| **Infrastructure** | 実際の compute/network/storage | EKS, VPC, IAM | [EKS](../eks/01-eks-introduction.md) |

### Self-Service Catalog Pattern (KRO RGD + ACK)

[KRO](./03-kro.md) の ResourceGraphDefinition (RGD) と [ACK](./02-ack.md) を組み合わせることで、強力なセルフサービスパターンが実現できます。

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

この単一の manifest から、KRO は内部で次を作成します。
1. **Deployment + Service** (Kubernetes native)
2. **RDS Instance** (AWS resource via ACK)
3. **IAM Role** (Permission setup via ACK)

詳細な例については、[ExampleCorp Integration Example](./05-example-corp-app.md) を参照してください。

### Golden Path の概念

Golden Path は、platform team によって提供される**推奨デプロイパス**です。

- **目的**: 検証済みの方法を使用して、開発者がすばやく開始できるように導く
- **特徴**: 推奨であり強制ではありません -- 開発者は必要に応じて逸脱できますが、多くの場合で最適な選択肢です
- **例**:
  - "New Microservice Deployment" Golden Path: Helm Chart template → ArgoCD integration → Automatic Prometheus metrics collection
  - "Database Provisioning" Golden Path: KRO RGD manifest → RDS creation via ACK → Automatic Secret injection

---

## 4. Platform Engineering Tool Ecosystem

このセクションでは、このリポジトリで扱うツールが platform engineering の全体像のどこに位置づけられるかを対応付けます。

| カテゴリ | ツール | Repo Doc Link |
|----------|-------|---------------|
| **Package Management** | Helm, Kustomize | [Helm](./01-helm.md) |
| **AWS IaC** | ACK, CloudFormation | [ACK](./02-ack.md) |
| **Resource Orchestration** | KRO, Crossplane | [KRO](./03-kro.md) |
| **Extension Mechanisms** | CRD, Operators | [Kubernetes Extension Mechanisms](./04-kubernetes-extensions.md) |
| **GitOps** | ArgoCD, FluxCD | [GitOps Section](../gitops/README.md) |
| **Policy/Governance** | Kyverno, OPA Gatekeeper | [Kyverno](../security/01-kyverno-policy-management.md), [OPA Gatekeeper](../security/09-opa-gatekeeper.md) |
| **Observability** | Prometheus, Grafana, OTel | [Observability Section](../observability/README.md) |
| **Autoscaling** | KEDA, Karpenter | [KEDA](../autoscaling/01-keda.md), [Karpenter](../autoscaling/02-karpenter.md) |
| **Service Mesh** | Istio, Cilium | [Istio](../service-mesh/istio/README.md), [Cilium Service Mesh](../service-mesh/cilium-service-mesh/README.md) |
| **Security** | Falco, Trivy, PSS | [Runtime Security](../security/08-runtime-security.md), [Image Security](../security/07-image-security.md), [PSS](../security/03-pod-security-standards.md) |

---

## 5. Platform Maturity Self-Assessment Checklist

組織の platform engineering 成熟度を評価します。各項目は、このリポジトリ内の関連ドキュメントにリンクしています。

### START Stage

| Check | 項目 | Related Docs |
|-------|------|-------------|
| [ ] | EKS clusters は標準化された方法で作成されていますか？ | [EKS Cluster Creation](../eks/02-eks-cluster-creation-part1.md) |
| [ ] | RBAC policies は定義され、適用されていますか？ | [Authentication & Authorization](../security/02-kubernetes-auth-authz.md) |
| [ ] | Network policies は適用されていますか？ | [Network Policies](../security/04-network-policies.md) |
| [ ] | 基本的な monitoring と logging は設定されていますか？ | [EKS Monitoring](../eks/06-eks-monitoring-logging.md) |
| [ ] | Pod Security Standards は適用されていますか？ | [PSS](../security/03-pod-security-standards.md) |
| [ ] | Resource quotas と limits は設定されていますか？ | [EKS Cost Optimization](../eks/07-eks-cost-optimization.md) |

### ADVANCE Stage

| Check | 項目 | Related Docs |
|-------|------|-------------|
| [ ] | インフラストラクチャは IaC で管理されていますか？ (ACK, Terraform, etc.) | [ACK](./02-ack.md) |
| [ ] | GitOps workflow は導入されていますか？ | [GitOps](../gitops/README.md) |
| [ ] | 集中型 observability stack は運用されていますか？ | [Observability](../observability/README.md) |
| [ ] | governance は policy engine によって自動化されていますか？ | [Kyverno](../security/01-kyverno-policy-management.md) |
| [ ] | secrets は external store から自動管理されていますか？ | [Secrets Management](../security/05-secrets-management.md) |
| [ ] | container image scanning は自動化されていますか？ | [Image Security](../security/07-image-security.md) |

### EXCEL Stage

| Check | 項目 | Related Docs |
|-------|------|-------------|
| [ ] | self-service catalog は開発者に提供されていますか？ | [KRO](./03-kro.md), [ExampleCorp](./05-example-corp-app.md) |
| [ ] | DORA metrics は測定され、改善されていますか？ | - |
| [ ] | runtime security monitoring は運用されていますか？ | [Runtime Security](../security/08-runtime-security.md) |
| [ ] | autoscaling は workloads 向けに最適化されていますか？ | [KEDA](../autoscaling/01-keda.md), [Karpenter](../autoscaling/02-karpenter.md) |
| [ ] | platform SLOs は定義され、追跡されていますか？ | [Observability Analysis](../ops/08-observability-analysis.md) |
| [ ] | Golden Paths は定義され、文書化されていますか？ | This document (Section 3) |

---

## 6. 参考資料

- [AWS CAF Platform Perspective - Platform Engineering](https://docs.aws.amazon.com/prescriptive-guidance/latest/aws-caf-platform-perspective/platform-eng.html)
- [CNCF Platform White Paper](https://tag-app-delivery.cncf.io/whitepapers/platforms/)
- [Platform Engineering on Kubernetes (O'Reilly)](https://www.oreilly.com/library/view/platform-engineering-on/9781617299322/)
- [Backstage.io - Open Source IDP Framework](https://backstage.io/)
- [Internal Developer Platform](https://internaldeveloperplatform.org/)
