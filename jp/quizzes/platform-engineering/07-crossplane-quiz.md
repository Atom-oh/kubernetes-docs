# Crossplane クイズ

1. Crossplane Compositions が解決する中核的な問題は何ですか？
   - A) Kubernetes cluster networking の設定
   - B) 複数の infrastructure resource を、self-service 用の単一の抽象化 API にまとめること
   - C) container image build の自動化
   - D) Pod resource requests の最適化

<details>
<summary>回答を表示</summary>

**回答: B) 複数の infrastructure resource を、self-service 用の単一の抽象化 API にまとめること**

**解説:**
Compositions は、複数の Managed Resources（RDS instance、SecurityGroup、SubnetGroup など）を単一の Composite Resource（XR）にパッケージ化します。開発者は複雑な infrastructure の詳細を理解する必要なく、シンプルな Claims を通じて必要な infrastructure を provision できます。

</details>

---

2. Crossplane Claims（XC）と Composite Resources（XR）の関係は何ですか？
   - A) Claims は cluster-scoped で、XRs は namespace-scoped である
   - B) Claims は namespace-scoped な request で、XRs は cluster-scoped な実際の resource である
   - C) Claims と XRs は同一の resource である
   - D) XRs は Claims の backup copy である

<details>
<summary>回答を表示</summary>

**回答: B) Claims は namespace-scoped な request で、XRs は cluster-scoped な実際の resource である**

**解説:**
Claims（XC）は、開発者が infrastructure を request するための namespace-scoped interface です。Claim が作成されると、対応する Composite Resource（XR）が cluster scope で作成され、XR は Composition に従って実際の Managed Resources を provision します。

</details>

---

3. Crossplane で AWS resources を管理する際に IRSA（IAM Roles for Service Accounts）を使用する理由は何ですか？
   - A) Crossplane の license cost を削減するため
   - B) AWS credentials を Pods に安全に渡し、最小権限の原則を適用するため
   - C) Crossplane の performance を向上させるため
   - D) multi-cluster support のため

<details>
<summary>回答を表示</summary>

**回答: B) AWS credentials を Pods に安全に渡し、最小権限の原則を適用するため**

**解説:**
IRSA は、IAM Roles を Kubernetes ServiceAccounts に関連付けて一時 credentials を自動的に注入することで、AWS Access Keys を直接管理する必要をなくします。これにより security が向上し、Provider ごとに必要な最小限の IAM permissions だけを付与できます。

</details>

---

4. Terraform と Crossplane の最大の architecture 上の違いは何ですか？
   - A) Terraform は YAML を使用し、Crossplane は HCL を使用する
   - B) Terraform は imperative execution（apply/destroy）を使用し、Crossplane は Kubernetes controllers による continuous reconciliation を使用する
   - C) Terraform は cloud のみを support し、Crossplane は on-premises のみを support する
   - D) Terraform は無料で、Crossplane は有料である

<details>
<summary>回答を表示</summary>

**回答: B) Terraform は imperative execution（apply/destroy）を使用し、Crossplane は Kubernetes controllers による continuous reconciliation を使用する**

**解説:**
Terraform は `terraform apply`/`destroy` commands で実行される workflow-based tool です。Crossplane は Kubernetes controller pattern を使用して動作し、宣言された状態と実際の状態を継続的に比較して差分を reconcile します。これにより、自動的な drift detection と correction が可能になります。

</details>

---

5. ACK と Crossplane を一緒に使用するのはどのような scenario ですか？
   - A) ACK と Crossplane は互換性がないため、どちらか一方だけを使用する
   - B) シンプルな AWS resources には ACK を使用し、複雑な multi-resource abstraction には Crossplane Compositions を使用する
   - C) ACK は development 用、Crossplane は production 専用である
   - D) ACK は networking を管理し、Crossplane は storage のみを管理する

<details>
<summary>回答を表示</summary>

**回答: B) シンプルな AWS resources には ACK を使用し、複雑な multi-resource abstraction には Crossplane Compositions を使用する**

**解説:**
ACK は AWS API に 1:1 で対応するシンプルな resource 管理に適している一方で、Crossplane は Compositions を通じて複数の resources を単一の抽象化 API にパッケージ化することに優れています。シンプルな S3 buckets は ACK で管理でき、RDS+SecurityGroup+SubnetGroup のような package は Crossplane Compositions により適しています。

</details>

---

6. Crossplane Connection Details が重要な理由は何ですか？
   - A) network connection status を監視する
   - B) provision された resource の access info（endpoints、passwords など）を含む Kubernetes Secrets を自動生成する
   - C) Crossplane Providers 間の connections を管理する
   - D) multi-cluster 間の network connections を設定する

<details>
<summary>回答を表示</summary>

**回答: B) provision された resource の access info（endpoints、passwords など）を含む Kubernetes Secrets を自動生成する**

**解説:**
Connection Details は、provision された resource の access information（database endpoint、port、username、password など）を Kubernetes Secrets に自動的に保存します。Applications はこれらの Secrets を mount して、provision された infrastructure に接続できます。

</details>

---

7. Backstage + Crossplane integration における正しい developer self-service workflow の順序はどれですか？
   - A) ArgoCD deployment → Backstage catalog registration → Crossplane Claim creation
   - B) Backstage Template が Crossplane Claim YAML を生成 → Git push → ArgoCD sync → Crossplane provisioning
   - C) Crossplane provisioning → Backstage Template creation → Git push
   - D) Git push → Backstage catalog registration → ArgoCD deployment

<details>
<summary>回答を表示</summary>

**回答: B) Backstage Template が Crossplane Claim YAML を生成 → Git push → ArgoCD sync → Crossplane provisioning**

**解説:**
開発者が Backstage Template に parameters（DB size、environment など）を入力すると、Template は Crossplane Claim YAML を生成し、それを Git repository に push します。ArgoCD が change を検出して cluster に sync し、そこで Crossplane が Claim を処理して実際の infrastructure を provision します。

</details>

---

8. Terraform と比較して、Crossplane の drift detection はどのように優れていますか？
   - A) Terraform は drift detection を support していない
   - B) Crossplane controllers は実際の状態を継続的に監視して自動修正する一方、Terraform では手動の `plan`/`apply` が必要である
   - C) Crossplane の方が provision が速い
   - D) Crossplane はより多くの clouds を support している

<details>
<summary>回答を表示</summary>

**回答: B) Crossplane controllers は実際の状態を継続的に監視して自動修正する一方、Terraform では手動の `plan`/`apply` が必要である**

**解説:**
Crossplane controllers は cloud resources の実際の状態を定期的に確認し、宣言された状態からの drift を自動的に修正します。Terraform では drift を検出するために `terraform plan` を、修正するために `terraform apply` を手動で実行する必要があるため、Crossplane の approach は GitOps workflows により適しています。

</details>
