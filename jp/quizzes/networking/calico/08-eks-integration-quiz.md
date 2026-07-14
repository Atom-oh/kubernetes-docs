# EKS 統合クイズ

> **関連ドキュメント**: [EKS 統合](../../../networking/calico/08-eks-integration.md)
> **最終更新**: February 22, 2026

## クイズ

1. EKS で VPC CNI と Calico を使用する場合の、一般的な役割分担は何ですか？
   - A) VPC CNI が policy を処理し、Calico が networking を処理する
   - B) VPC CNI が networking（IP allocation）を処理し、Calico が network policy を処理する
   - C) VPC CNI と Calico の両方が冗長に networking を処理する
   - D) Calico が VPC CNI を完全に置き換える

<details>
<summary>回答を表示</summary>

**回答: B) VPC CNI が networking（IP allocation）を処理し、Calico が network policy を処理する**

**解説:**
最も一般的な EKS 構成では、AWS VPC CNI が VPC から IP を割り当てることで Pod networking を処理し、Calico は network policy enforcement を提供するために「policy-only」モードでインストールされます。これにより、ネイティブな VPC 統合と Calico の強力な policy 機能を組み合わせられます。

</details>

2. EKS に Calico をインストールする主な 3 つの方法は何ですか？
   - A) kubectl apply、Docker、AWS CLI
   - B) EKS Add-on、Tigera Operator、Helm chart
   - C) CloudFormation、Terraform、Pulumi
   - D) eksctl、AWS Console、SDK

<details>
<summary>回答を表示</summary>

**回答: B) EKS Add-on、Tigera Operator、Helm chart**

**解説:**
Calico は、1) EKS managed add-on（policy-only モードでは最も簡単）、2) Tigera Operator（Calico の全機能に推奨）、3) Helm chart（柔軟な構成）のいずれかを使用して EKS にインストールできます。各方法には、シンプルさとカスタマイズ性の点で異なるトレードオフがあります。

</details>

3. ネイティブの Network Policy Controller は、どの EKS バージョンから利用可能ですか？
   - A) EKS 1.12
   - B) EKS 1.14
   - C) EKS 1.18
   - D) EKS 1.24

<details>
<summary>回答を表示</summary>

**回答: B) EKS 1.14**

**解説:**
EKS はバージョン 1.14 からネイティブの Network Policy Controller を導入しました。この controller は基本的な Kubernetes NetworkPolicy サポートを提供します。ただし、Calico はネイティブ controller の機能を超える GlobalNetworkPolicy や policy tier などの追加 policy 機能を提供します。

</details>

4. EKS Fargate で Calico を実行する際の主な制限は何ですか？
   - A) Fargate はいかなる networking もサポートしない
   - B) Calico は Fargate Pod に network policy を適用できない
   - C) Fargate は IPv6 のみをサポートする
   - D) Calico には root access が必要であり、Fargate はそれを提供する

<details>
<summary>回答を表示</summary>

**回答: B) Calico は Fargate Pod に network policy を適用できない**

**解説:**
Fargate Pod は AWS が管理する隔離された microVM で実行され、ユーザーは DaemonSet をインストールしたり、基盤となる host を変更したりできません。Calico の Felix agent は DaemonSet として実行されるため、Fargate node にデプロイできず、Fargate Pod では network policy enforcement を利用できません。

</details>

5. EKS 上の Calico において、IRSA とは何ですか？
   - A) Internal Route Service Allocation
   - B) IAM Roles for Service Accounts - Pod が AWS IAM role を引き受けられるようにする仕組み
   - C) Ingress Resource Security Association
   - D) IP Range Subnet Assignment

<details>
<summary>回答を表示</summary>

**回答: B) IAM Roles for Service Accounts - Pod が AWS IAM role を引き受けられるようにする仕組み**

**解説:**
IRSA（IAM Roles for Service Accounts）により、Kubernetes service account は AWS IAM role を引き受けられます。Calico component が AWS API へのアクセスを必要とする場合（例: cloud provider 統合）、IRSA は credential を Pod に埋め込むことなく、安全で細かなアクセス制御を提供します。

</details>

6. Security Group と Calico network policy は、スコープの点でどのように異なりますか？
   - A) 機能的には同一である
   - B) Security Group は VPC/ENI レベルで動作し、Calico policy は Pod/container レベルで動作する
   - C) Security Group は ingress 専用で、Calico は egress 専用である
   - D) Security Group は Calico に置き換えられ非推奨となっている

<details>
<summary>回答を表示</summary>

**回答: B) Security Group は VPC/ENI レベルで動作し、Calico policy は Pod/container レベルで動作する**

**解説:**
AWS Security Group は VPC networking layer で動作し、ENI（Elastic Network Interface）への／からの traffic を制御します。Calico network policy は label-based selector を使用して Kubernetes Pod レベルで動作します。両方を defense-in-depth のために併用でき、SG は VPC レベルの制御を、Calico は application レベルの policy を提供します。

</details>

7. Calico を実行している EKS cluster を upgrade する際に考慮すべきことは何ですか？
   - A) upgrade の前に Calico を uninstall する必要がある
   - B) 対象の EKS バージョンと Calico バージョンの互換性を確認する
   - C) EKS upgrade により Calico も自動的に upgrade される
   - D) Calico は偶数で終わる特定の EKS バージョンのみをサポートする

<details>
<summary>回答を表示</summary>

**回答: B) 対象の EKS バージョンと Calico バージョンの互換性を確認する**

**解説:**
EKS を upgrade する際は、Calico のバージョンが対象の Kubernetes/EKS バージョンと互換性があることを確認する必要があります。Calico の compatibility matrix を確認し、文書化された upgrade 手順に従って、必要に応じて EKS upgrade の前または後に Calico を upgrade してください。

</details>

8. EKS インストールでは、kubernetesProvider 設定を何に構成すべきですか？
   - A) kubernetesProvider: AWS
   - B) kubernetesProvider: EKS
   - C) kubernetesProvider: Amazon
   - D) kubernetesProvider: None（自動検出）

<details>
<summary>回答を表示</summary>

**回答: B) kubernetesProvider: EKS**

**解説:**
EKS に Calico をインストールする場合、Installation resource の `kubernetesProvider` は `EKS` に設定する必要があります。これにより、Calico は EKS 固有の構成と最適化を使用し、managed Kubernetes service との適切な統合を確保します。

</details>

9. EKS の Calico Installation resource における cni.type 設定は何を制御しますか？
   - A) 使用する CNI specification のバージョン
   - B) Calico が CNI を管理するか、別の CNI plugin に委ねるか
   - C) network encryption の種類
   - D) container runtime 統合モード

<details>
<summary>回答を表示</summary>

**回答: B) Calico が CNI を管理するか、別の CNI plugin に委ねるか**

**解説:**
`cni.type` 設定は Calico の CNI 動作を決定します。`cni.type: AmazonVPC` を設定すると、Calico は policy のみを処理し、networking を VPC CNI に委ねるようになります。`cni.type: Calico` を設定すると、Calico が networking と policy の両方を処理します。

</details>

10. EKS 上の Calico における「policy-only mode」とは何ですか？
    - A) GlobalNetworkPolicy のみが適用されるモード
    - B) Calico が network policy を処理する一方で、Pod networking は処理しないモード
    - C) すべての egress policy を無効にするモード
    - D) audit-only policy evaluation 用のモード

<details>
<summary>回答を表示</summary>

**回答: B) Calico が network policy を処理する一方で、Pod networking は処理しないモード**

**解説:**
policy-only mode は、VPC CNI が引き続き Pod IP allocation と routing を処理し、Calico が network policy enforcement のみを担当する Calico deployment 構成です。ネイティブな VPC networking の利点を維持できるため、これは EKS 上で最も一般的な Calico deployment パターンです。

</details>
