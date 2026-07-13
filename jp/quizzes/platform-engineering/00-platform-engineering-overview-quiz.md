# Platform Engineering 概要クイズ

> このクイズでは、[Platform Engineering 概要](../../platform-engineering/00-platform-engineering-overview.md)ドキュメントの理解度を確認します。

---

1. Platform Engineering の中核的な目標は何ですか？
   - A) すべての開発者がインフラストラクチャを直接管理できるようにトレーニングすること
   - B) 開発者のセルフサービスのために Internal Developer Platform (IDP) を構築すること
   - C) オペレーションチームの役割を自動化で完全に置き換えること
   - D) すべてのアプリケーションをサーバーレスへ移行すること

<details>
<summary>答えを表示</summary>

**答え: B) 開発者のセルフサービスのために Internal Developer Platform (IDP) を構築すること**

**解説:**
Platform Engineering は、開発者がインフラストラクチャの複雑さに直接対処することなく、アプリケーションを迅速かつ安全にデプロイできるようにする IDP を構築する分野です。目標は、開発者にインフラストラクチャ管理を教えることではなく、抽象化されたセルフサービスインターフェースを提供することです。

</details>

---

2. AWS CAF 成熟度モデルにおいて、「IaC によるインフラストラクチャ自動化」と「セルフサービスのプロダクト提供」に対応するステージはどれですか？
   - A) START
   - B) ADVANCE
   - C) EXCEL
   - D) すべてのステージに共通

<details>
<summary>答えを表示</summary>

**答え: B) ADVANCE**

**解説:**
AWS CAF 成熟度モデルでは、ADVANCE ステージは自動化の拡大と中央集権的な可観測性の構築に重点を置きます。インフラストラクチャ自動化 (IaC、セルフサービスプロダクト) は、START の基盤の上に構築される ADVANCE のケイパビリティです。START は基盤構築を対象とし、EXCEL は継続的な最適化を対象とします。

</details>

---

3. Platform Engineering、DevOps、SRE の関係を正しく説明している文はどれですか？
   - A) 3つは相互に排他的なアプローチである
   - B) Platform Engineering は DevOps と SRE を置き換える
   - C) Platform Engineering は DevOps の原則と SRE のプラクティスをプロダクトとしてパッケージ化する
   - D) SRE は Platform Engineering と DevOps を包含する上位集合である

<details>
<summary>答えを表示</summary>

**答え: C) Platform Engineering は DevOps の原則と SRE のプラクティスをプロダクトとしてパッケージ化する**

**解説:**
3つのアプローチは相互補完的です。DevOps は文化と方法論を提供し、SRE は運用エンジニアリングのプラクティスを提供し、Platform Engineering はこれらを Internal Developer Platform と呼ばれるプロダクトとしてパッケージ化します。

</details>

---

4. Kubernetes ベースの IDP リファレンスアーキテクチャにおいて、ArgoCD、FluxCD、KRO はどのレイヤーに属しますか？
   - A) Developer Interface Layer
   - B) Integration/Orchestration Layer
   - C) Resource Layer
   - D) Infrastructure Layer

<details>
<summary>答えを表示</summary>

**答え: B) Integration/Orchestration Layer**

**解説:**
Integration/Orchestration Layer は宣言的な状態管理とデプロイ自動化を扱います。ArgoCD と FluxCD は GitOps ベースのデプロイを提供し、KRO はリソースグラフのオーケストレーションを提供します。Developer Interface Layer は Backstage のような UI/CLI のためのもので、Resource Layer は ACK/Helm/Operators のためのもの、Infrastructure Layer は EKS/VPC/IAM のためのものです。

</details>

---

5. Golden Paths について正しくない説明はどれですか？
   - A) プラットフォームチームが提供する推奨デプロイパスである
   - B) 開発者が従わなければならない必須ルールである
   - C) 検証済みの方法を使って開発者がすばやく開始できるように導く
   - D) 必要に応じて開発者は逸脱できるが、ほとんどの場合で最適な選択肢である

<details>
<summary>答えを表示</summary>

**答え: B) 開発者が従わなければならない必須ルールである**

**解説:**
Golden Paths は「強制」ではなく「推奨」です。プラットフォームチームが検証し最適化したデプロイ方法を提供しますが、必要に応じて開発者は別のアプローチを選択できます。目標は、ほとんどのユースケースにおいて Golden Paths が最適な選択肢となるように設計することです。

</details>

---

6. KRO の ResourceGraphDefinition (RGD) と ACK を組み合わせたセルフサービスパターンでは、開発者が単一のマニフェストを送信すると、どのリソースの組み合わせが自動的に作成されますか？
   - A) Deployment + ConfigMap + PVC
   - B) Deployment + Service + RDS Instance + IAM Role
   - C) StatefulSet + Service + DynamoDB Table
   - D) Pod + Ingress + S3 Bucket

<details>
<summary>答えを表示</summary>

**答え: B) Deployment + Service + RDS Instance + IAM Role**

**解説:**
KRO RGD + ACK のセルフサービスパターンでは、開発者の単一の WebApplication マニフェストが KRO をトリガーし、Kubernetes ネイティブリソース (Deployment + Service) と、ACK 経由の AWS リソース (RDS Instance、IAM Role) を自動的に作成します。これが IDP の中核的な価値、すなわちインフラストラクチャの複雑さを抽象化することです。

</details>

---

7. AWS CAF 成熟度モデルにおいて、DORA metrics はどのステージおよびケイパビリティ領域に属しますか？
   - A) START - Cost Management
   - B) ADVANCE - Central Observability
   - C) EXCEL - Platform Metrics
   - D) すべてのステージに共通

<details>
<summary>答えを表示</summary>

**答え: C) EXCEL - Platform Metrics**

**解説:**
DORA metrics (Deployment Frequency、Lead Time、MTTR、Change Failure Rate) は、EXCEL ステージの「Platform Metrics」ケイパビリティに属します。これは最も高い成熟度レベルを表し、組織目標に沿った metrics を通じて継続的な最適化を達成します。

</details>

---

8. IDP の中核的価値のうち、開発者が明示的なセキュリティ設定をしなくても安全な環境で作業できるように、セキュリティとコンプライアンスをデフォルトで組み込むものはどれですか？
   - A) Self-Service
   - B) Guardrails
   - C) Standardization
   - D) Automation

<details>
<summary>答えを表示</summary>

**答え: B) Guardrails**

**解説:**
Guardrails は、セキュリティとコンプライアンスをデフォルトでプラットフォームに組み込みます。開発者が明示的にセキュリティを設定しなくても、プラットフォームはセキュリティポリシー (Pod Security Standards、ネットワークポリシー、イメージスキャンなど) を自動的に適用します。Self-Service は直接プロビジョニングに、Standardization は Golden Paths に、Automation は反復作業の排除に関連します。

</details>
