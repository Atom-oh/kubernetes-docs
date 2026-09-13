# EKS セキュリティのベストプラクティスクイズ

> **最終更新**: September 13, 2026

以下の質問で Amazon EKS のセキュリティに関するベストプラクティスの理解度を確認しましょう。

***

## 問題

<span id="_1-what-authentication-method-does-a-pod-use-when-calling-aws-apis-with-irsa-iam-roles-for-service-accounts"></span>

### 1. Pod は IRSA を通じてどのように一時的な AWS 認証情報を取得しますか？

* A) IAM User Access Key
* B) EC2 Instance Profile
* C) OIDC トークンベースの AssumeRoleWithWebIdentity
* D) Kubernetes Secret に保存された認証情報

<details>

<summary>回答を表示</summary>

**回答: C) OIDC トークンベースの AssumeRoleWithWebIdentity**

**解説:** Kubernetes API server は投影された ServiceAccount JWT を発行します。対応する SDK がこれを STS AssumeRoleWithWebIdentity と交換します。STS は信頼された issuer/JWKS、audience、subject を確認し、一時的な AWS 認証情報を返します。IAM OIDC provider object はトークン issuer ではなく、JWT は AWS API 認証情報として直接置き換えられるものではありません。

</details>

***

### 2. IRSA と比較した EKS Pod Identity の主な利点は何ですか？

* A) より強力な暗号化
* B) より高速なパフォーマンス
* C) OIDC Provider のセットアップが不要で、管理が簡素化される
* D) より多くの AWS サービスをサポートする

<details>

<summary>回答を表示</summary>

**回答: C) OIDC Provider のセットアップが不要で、管理が簡素化される**

**解説:** Pod Identity はクラスターごとの IAM OIDC-provider のセットアップを不要にし、association、対応する agent/SDK、EKS Auth を使用します。Role には引き続き trust と最小権限の permissions が必要です。Auto Mode には agent が含まれますが、他のプラットフォームおよび cross-account/chained Role には固有の要件があります。これは IRSA を廃止するものでも、すべてのアプリケーションのセキュリティを自動的に強化するものでもありません。

</details>

***

<span id="_3-which-is-not-a-requirement-for-using-security-groups-for-pods"></span>

### 3. EC2 ベースの Security Groups for Pods パスで必要**ではない**ものはどれですか？

* A) trunking 対応の EC2 instance type
* B) Amazon VPC CNI plugin
* C) Fargate profile
* D) SecurityGroupPolicy の設定

<details>

<summary>回答を表示</summary>

**回答: C) Fargate profile**

**解説:** EC2 ベースのパスでは、trunking 対応のサポート対象 instance type、互換性のある Amazon VPC CNI、および SecurityGroupPolicy を使用します。すべての Nitro instance が対象となるわけではありません。VPC Resource Controller policy はクラスター Role に属します。Fargate には別のサポートモデルがあり、Windows と Auto Mode は現行の Pod-SG ドキュメントでは対象外です。ENIConfig は SecurityGroupPolicy の代替ではありません。

</details>

***

### 4. EKS クラスターの Kubernetes API server endpoint を private のみに設定した場合の影響は何ですか？

* A) kubectl をまったく使用できない
* B) VPC 内または接続されたネットワークからのみアクセスできる
* C) AWS Console からクラスターを管理できない
* D) Worker node が API server に接続できない

<details>

<summary>回答を表示</summary>

**回答: B) VPC 内または接続されたネットワークからのみアクセスできる**

**解説:** private API への到達には、接続されたネットワーク、DNS、routes、security groups に加え、IAM authentication/Kubernetes authorization が必要です。public access を削除する前に、operator、CI、recovery のアクセスをテストしてください。EKS management PrivateLink endpoint は private Kubernetes API endpoint の代わりにはなりません。

</details>

***

### 5. AWS GuardDuty EKS Protection で検出**されない**脅威タイプはどれですか？

* A) 悪意のある IP との通信
* B) Cryptocurrency mining activity
* C) Pod のリソース使用量が limits を超過すること
* D) Tor network connections

<details>

<summary>回答を表示</summary>

**回答: C) Pod のリソース使用量が limits を超過すること**

**解説:** EKS audit analysis、agent ベースの Runtime Monitoring、基本的な GuardDuty source を区別してください。カバレッジは有効化した plan とプラットフォームによって異なります。ECS Fargate のサポートは EKS Fargate のサポートを意味しません。CPU/memory limit の監視は運用 metrics ツールに属し、detector が静かであることは侵害がないことの証明にはなりません。

</details>

***

<span id="_6-which-aws-service-does-not-require-vpc-endpoints-in-an-eks-cluster"></span>

### 6. DNS と private AWS API access について考える正しい方法はどれですか？

* A) EKS management endpoint が Kubernetes API を置き換える
* B) Pod Identity は常に global STS endpoint を使用する
* C) すべての AWS Region が同じ endpoint 名をサポートする
* D) DNS resolution と Route 53 management API PrivateLink を区別する

<details>

<summary>回答を表示</summary>

**回答: D) DNS resolution と Route 53 management API PrivateLink を区別する**

**解説:** 通常の DNS resolution は、設定された resolver/network path を使用します。Route 53 management API 呼び出しは別のものであり、現行の EKS private-cluster ドキュメントには Route 53 PrivateLink service が記載されています。EKS Auth、regional STS、OIDC discovery、ECR/S3 にもそれぞれ異なるパスがあるため、実際の service/Region 要件を確認してください。

</details>

***

### 7. kube-bench で EKS クラスターのセキュリティを確認する際に使用される benchmark は何ですか？

* A) PCI-DSS
* B) 該当する CIS Amazon EKS benchmark profile
* C) NIST Cybersecurity Framework
* D) SOC 2

<details>

<summary>回答を表示</summary>

**回答: B) 該当する CIS Amazon EKS benchmark profile**

**解説:** 環境に適した CIS Amazon EKS benchmark edition と kube-bench profile を選択してください。kube-bench0.16.0 には複数の EKS profile が含まれています。単一の可変な upstream Job は fleet coverage の証明にはなりません。手動/該当なしの確認と managed control plane の制限は残り、quiz/tool のスコアは認定ではありません。

</details>

***

### 8. Service Account Token Volume Projection は EKS でどのようなセキュリティ上の利点をもたらしますか？

* A) token size の削減
* B) bound token と expiration time の設定
* C) token encryption
* D) 自動 token backup

<details>

<summary>回答を表示</summary>

**回答: B) bound token と expiration time の設定**

**解説:** Projection は、object binding を伴う audience と要求された lifetime をサポートします。token の実際の expiry と receiver validation を確認してください。すべての token が必ず 1 時間後に expire すると想定しないでください。盗まれた bearer token は受け入れられている間は replay される可能性があるため、Projection によって token-protection 要件がなくなるわけではありません。Projection 単独では完全な IRSA 設定にはなりません。

</details>

***

### 9. Amazon Inspector は EKS 環境で何を scan しますか？

* A) Kubernetes manifest
* B) Container image vulnerabilities
* C) IAM policy
* D) Network traffic

<details>

<summary>回答を表示</summary>

**回答: B) Container image vulnerabilities**

**解説:** ECR enhanced scanning は、対応する image package vulnerabilities に対して Inspector を使用します。実行中 image の usage information は、runtime behavior detection とは異なります。成功 status、completion timestamp、明示的な findings-count map が確認できた後にのみ、正確な digest を gate してください。pending/missing/error の結果を vulnerabilities がゼロとして扱ってはいけません。

</details>

***

### 10. EKS クラスターの Control Plane logs を CloudWatch に送信する際に、有効化**できない** log type はどれですか？

* A) api
* B) audit
* C) controllerManager
* D) kubelet

<details>

<summary>回答を表示</summary>

**回答: D) kubelet**

**解説:** 5 つの EKS control-plane category は、api、audit、authenticator、controllerManager、scheduler です。Kubelet/container logs には、別の node/runtime collection path が必要です。cluster owner を通じて exports を有効化し、非同期 update と実際の到着を確認して、retention と access を設定してください。

</details>

***

### 11. EKS で Node IAM Role と Pod IAM Role (IRSA) を分離すべき理由は何ですか？

* A) コスト削減
* B) 最小権限の原則を適用するため
* C) パフォーマンスの向上
* D) network latency の削減

<details>

<summary>回答を表示</summary>

**回答: B) 最小権限の原則を適用するため**

**解説:** Workload Role は、node responsibilities とは独立して application permissions を制限します。Node Role の露出は metadata への到達可能性と権限に依存し、すべての Pod が常にアクセスできるわけではありません。IRSA 単独では IMDS をブロックしません。IMDSv2、network controls、hostNetwork/privileged workloads、SDK credential precedence、node compromise を確認してください。

</details>

***

<span id="_12-which-component-is-responsible-for-integrating-kubernetes-rbac-with-aws-iam-in-eks"></span>

### 12. EKS developer に必要な namespace access のみを付与する方法はどれですか？

* A) すべての developer を system:masters に追加する
* B) すべての developer と node role を共有する
* C) scoped access policy または group/RBAC mapping を持つ access entry を使用する
* D) API authentication を無効化する

<details>

<summary>回答を表示</summary>

**回答: C) scoped access policy または group/RBAC mapping を持つ access entry を使用する**

**解説:** 必要な scoped EKS access policy または Kubernetes group/RBAC mapping を持つ access entry を使用してください。Authentication と authorization は別のものです。aws-auth ConfigMap は legacy path であり、authentication-mode migration には一方向の制約があります。通常の developer に system:masters を使用しないでください。EKS access policies と RBAC のいずれも、独立して operation を許可できます。

</details>

***

## スコア計算

各問題を 1 点として計算してください。

| スコア | 評価 |
| ----- | ---------------------------------------------------------- |
| 11-12 | 復習完了。次に運用シナリオを検証してください |
| 8-10  | 良好 - 基本概念を理解しています。高度な機能を復習してください |
| 5-7   | 平均 - 追加の学習を推奨します |
| 0-4   | 基礎学習が必要です |

***

## 関連ドキュメント

* [EKS Security Best Practices](../../security/06-eks-security-best-practices.md)
* [Pod Security Standards](../../security/03-pod-security-standards.md)
* [Secrets Management](../../security/05-secrets-management.md)
