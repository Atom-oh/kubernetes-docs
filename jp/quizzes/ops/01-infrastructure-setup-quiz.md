# インフラストラクチャセットアップクイズ

> **関連ドキュメント**: [インフラストラクチャセットアップ](../../ops/01-infrastructure-setup.md)

## 選択問題

### 1. Terraform 3-Layer アーキテクチャの主な目的は何ですか？

- A) Terraform ファイルの数を減らすため
- B) ライフサイクルと影響範囲ごとにインフラストラクチャを分離するため
- C) デプロイ時間を短縮するため
- D) state 管理の必要性をなくすため

<details>
<summary>解答を表示</summary>

**解答: B) ライフサイクルと影響範囲ごとにインフラストラクチャを分離するため**

**解説:**
3-Layer アーキテクチャは、インフラストラクチャを Foundation (VPC, IAM)、Platform (EKS cluster)、Workload (applications) レイヤーに分離します。各レイヤーは変更頻度と影響範囲が異なるため、より安全で管理しやすいインフラストラクチャ変更が可能になります。

</details>

### 2. Terraform S3 backend 設定において、DynamoDB table の目的は何ですか？

- A) Terraform state ファイルを保存するため
- B) state locking と整合性を提供するため
- C) Terraform 設定をバックアップするため
- D) Terraform 操作をログに記録するため

<details>
<summary>解答を表示</summary>

**解答: B) state locking と整合性を提供するため**

**解説:**
DynamoDB table は state locking を有効にし、同じ state ファイルへの同時変更を防ぎます。これにより、複数のユーザーまたは CI/CD pipeline が同時にインフラストラクチャを変更しようとしたときの race condition を防止します。

</details>

### 3. `terraform_remote_state` data source では何ができますか？

- A) state ファイルをリモートの場所に保存する
- B) 別の Terraform state から outputs を参照する
- C) backend 間で state を移行する
- D) state ファイルを自動的に暗号化する

<details>
<summary>解答を表示</summary>

**解答: B) 別の Terraform state から outputs を参照する**

**解説:**
`terraform_remote_state` data source を使用すると、ある Terraform 設定が別の state ファイルから output 値を読み取ることができます。これにより、Platform レイヤーが Foundation レイヤーから VPC ID を読み取るような、レイヤー間参照が可能になります。

</details>

### 4. 本番用 EKS cluster に推奨される VPC CIDR block size はどれですか？

- A) /24 (256 addresses)
- B) /20 (4,096 addresses)
- C) /16 (65,536 addresses)
- D) /8 (16 million addresses)

<details>
<summary>解答を表示</summary>

**解答: C) /16 (65,536 addresses)**

**解説:**
/16 CIDR block は 65,536 個の IP addresses を提供し、本番用 EKS cluster に推奨されます。これにより、Pod IP 割り当て（特に VPC CNI 使用時）、将来の拡張、multi-AZ deployment に対応でき、IP 枯渇の懸念を避けられます。

</details>

### 5. Managed Node Groups と比較した EKS Auto Mode の主な特徴は何ですか？

- A) Auto Mode では手動での node provisioning が必要である
- B) Auto Mode は node lifecycle と scaling を自動的に管理する
- C) Auto Mode は Spot instances のみをサポートする
- D) Auto Mode は Pod の必要性をなくす

<details>
<summary>解答を表示</summary>

**解答: B) Auto Mode は node lifecycle と scaling を自動的に管理する**

**解説:**
EKS Auto Mode は、workload demand に基づいて node provisioning、scaling、lifecycle management を自動的に処理します。Managed Node Groups とは異なり、運用者が Auto Scaling Groups を設定したり、node updates を手動で管理したりする必要はありません。

</details>

### 6. Pod Identity は IRSA (IAM Roles for Service Accounts) とどのように異なりますか？

- A) Pod Identity は IAM roles をサポートしない
- B) Pod Identity は OIDC provider setup なしで EKS-managed credentials を使用する
- C) Pod Identity では手動の token rotation が必要である
- D) Pod Identity は Fargate でのみ動作する

<details>
<summary>解答を表示</summary>

**解答: B) Pod Identity は OIDC provider setup なしで EKS-managed credentials を使用する**

**解説:**
Pod Identity は、OIDC provider を設定する必要をなくすことで IAM 統合を簡素化します。AWS は Pod Identity Agent を通じて credential injection を管理するため、IRSA と比較してセットアップと保守が容易になります。

</details>

### 7. 3-Layer アーキテクチャでは、どのレイヤーに EKS cluster resource が含まれますか？

- A) Foundation Layer
- B) Platform Layer
- C) Workload Layer
- D) Network Layer

<details>
<summary>解答を表示</summary>

**解答: B) Platform Layer**

**解説:**
Platform Layer には EKS cluster、node groups、cluster add-ons が含まれます。これは Foundation Layer (VPC, subnets) に依存し、Workload Layer (applications, services) のための platform を提供します。

</details>

### 8. Terraform state を保存する S3 buckets では何を有効にすべきですか？

- A) Public access
- B) Versioning and encryption
- C) Static website hosting
- D) Cross-region replication only

<details>
<summary>解答を表示</summary>

**解答: B) Versioning and encryption**

**解説:**
Terraform state ファイルには機密情報が含まれるため、versioning（破損や誤変更から復旧するため）と encryption（保存時の secrets を保護するため）で保護する必要があります。Public access は常にブロックすべきです。

</details>

### 9. 複数環境管理に Terraform workspaces を使用する場合、主な制限は何ですか？

- A) Workspaces は variables を使用できない
- B) すべての環境が同じ backend configuration を共有する
- C) Workspaces は modules をサポートしない
- D) 使用できる workspaces は 2 つだけである

<details>
<summary>解答を表示</summary>

**解答: B) すべての環境が同じ backend configuration を共有する**

**解説:**
Terraform workspaces は同じ backend configuration と code を共有するため、development で作業しているときに誤って production に変更を加える可能性があります。多くのチームは、より強い分離のために、環境ごとに別々の directories または repositories を使用することを好みます。

</details>

### 10. Terraform provider versions を管理する推奨アプローチは何ですか？

- A) 制約なしで常に最新 version を使用する
- B) required_providers block で exact version constraints を使用する
- C) Terraform に providers を自動更新させる
- D) provider versions の指定を避ける

<details>
<summary>解答を表示</summary>

**解答: B) required_providers block で exact version constraints を使用する**

**解説:**
`required_providers` block で exact または pessimistic version constraints（例: `~> 5.0`）を指定すると、再現性のあるデプロイが保証され、provider updates による予期しない破壊的変更を防げます。これは本番環境では特に重要です。

</details>
