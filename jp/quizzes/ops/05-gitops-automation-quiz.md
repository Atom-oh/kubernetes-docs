# GitOps 自動化クイズ

> **関連ドキュメント**: [GitOps 自動化](../../ops/05-gitops-automation.md)

## 選択式問題

### 1. Terraform 自動化の文脈において、Atlantis とは何ですか？

- A) クラウドプロバイダー
- B) Terraform 用の pull request 自動化ツール
- C) Terraform module registry
- D) state file 暗号化サービス

<details>
<summary>回答を表示</summary>

**回答: B) Terraform 用の pull request 自動化ツール**

**解説:**
Atlantis は、Terraform の pull request を監視し、`terraform plan` と `apply` を自動的に実行する self-hosted アプリケーションです。plan の出力を PR コメントとして提供し、変更を適用する前に承認ワークフローを強制します。

</details>

### 2. self-hosted Terraform と比べた Terraform Cloud の主な利点は何ですか？

- A) 無料で無制限に利用できること
- B) managed state、run、コラボレーション機能
- C) より速い実行速度
- D) より多くの provider のサポート

<details>
<summary>回答を表示</summary>

**回答: B) managed state、run、コラボレーション機能**

**解説:**
Terraform Cloud は、managed remote state storage、run execution、team collaboration、policy enforcement (Sentinel)、private module registry を提供します。これらの managed 機能により、self-hosted 構成と比べて運用上の負担を軽減できます。

</details>

### 3. FluxCD は、そのアーキテクチャにおいて ArgoCD とどのように異なりますか？

- A) FluxCD には UI がない
- B) FluxCD は central server を持たない pull-based の分散アーキテクチャを使用する
- C) FluxCD は Helm のみをサポートする
- D) FluxCD には database が必要である

<details>
<summary>回答を表示</summary>

**回答: B) FluxCD は central server を持たない pull-based の分散アーキテクチャを使用する**

**解説:**
FluxCD は各 cluster 内で controller を直接実行し、git から pull します。一方、ArgoCD は centralized server model を使用します。FluxCD のアプローチはより軽量で、central hub なしに multi-cluster シナリオで自然にスケールします。

</details>

### 4. Flux Image Automation Controller は何をしますか？

- A) container image を build する
- B) registry を scan し、新しい image tag で git を更新する
- C) image を Kubernetes に deploy する
- D) image pull secret を管理する

<details>
<summary>回答を表示</summary>

**回答: B) registry を scan し、新しい image tag で git を更新する**

**解説:**
Image Automation Controller は、新しい image tag がないか container registry を監視し、その後 git repository に更新を自動的に commit します。これにより、新しい image が push されたときに、GitOps の原則を維持しながら完全に自動化された deployment が可能になります。

</details>

### 5. Atlantis workflow では、PR が承認され merge されると何が起こりますか？

- A) Terraform plan が自動的に実行される
- B) Atlantis が merge された code に対して terraform apply を実行する
- C) PR は何もせずに close される
- D) 新しい branch が作成される

<details>
<summary>回答を表示</summary>

**回答: B) Atlantis が merge された code に対して terraform apply を実行する**

**解説:**
auto-apply が設定されている場合、または明示的な承認後に、Atlantis は PR merge 後に `terraform apply` を実行します。これにより、infrastructure の変更は code review と承認後にのみ適用され、change control が維持されます。

</details>

### 6. GitOps workflow における AIOps の主な利点は何ですか？

- A) git の必要性をなくすこと
- B) 自動化された anomaly detection と response recommendation
- C) より速い container build
- D) storage cost の削減

<details>
<summary>回答を表示</summary>

**回答: B) 自動化された anomaly detection と response recommendation**

**解説:**
AIOps は machine learning を適用して、metrics と logs の anomaly を検出し、event を相関させ、response を推奨または自動化します。GitOps では、これに scaling 変更や traffic weight 調整のための PR を自動生成することが含まれます。

</details>

### 7. AIOps は blue/green deployment で traffic weight の変更をどのように自動化できますか？

- A) load balancer 設定を直接変更することによって
- B) anomaly を検出し、git 内の weight 設定を更新する PR を作成することによって
- C) 失敗した pod を restart することによって
- D) DNS record を変更することによって

<details>
<summary>回答を表示</summary>

**回答: B) anomaly を検出し、git 内の weight 設定を更新する PR を作成することによって**

**解説:**
AIOps は metrics を監視し、green deployment の問題（error rate、latency）を検出し、traffic weight を blue に戻す PR を自動的に作成できます。これにより、自動化された incident response を可能にしながら GitOps の原則を維持します。

</details>

### 8. Flux の GitRepository resource の目的は何ですか？

- A) git repository を作成するため
- B) Flux が変更を監視する git source を定義するため
- C) Kubernetes resource を git に backup するため
- D) git credential を管理するため

<details>
<summary>回答を表示</summary>

**回答: B) Flux が変更を監視する git source を定義するため**

**解説:**
GitRepository は、git repository URL、branch、polling interval を指定する Flux custom resource です。Flux controller はこれらの source を監視し、変更が検出されると reconciliation を trigger します。

</details>

### 9. FluxCD と ArgoCD を比較した場合、どの記述が正確ですか？

- A) ArgoCD は Project model を通じてより優れた multi-tenancy を提供する
- B) FluxCD はより豊富な built-in UI を持つ
- C) ArgoCD は GitOps を使用するが FluxCD は使用しない
- D) FluxCD には external database が必要である

<details>
<summary>回答を表示</summary>

**回答: A) ArgoCD は Project model を通じてより優れた multi-tenancy を提供する**

**解説:**
ArgoCD の Project resource は、repository、cluster、namespace に対する fine-grained access control を備えた堅牢な multi-tenancy を提供します。FluxCD は namespace isolation によって multi-tenancy を実現しますが、制御の粒度は低くなります。

</details>

### 10. Terraform Cloud における Sentinel policy とは何ですか？

- A) backup strategy
- B) governance と compliance のための policy-as-code framework
- C) state encryption method
- D) module versioning system

<details>
<summary>回答を表示</summary>

**回答: B) governance と compliance のための policy-as-code framework**

**解説:**
Sentinel は、Terraform が変更を適用する前に rule を強制する HashiCorp の policy-as-code framework です。policy は tagging を必須にしたり、instance type を制限したり、encryption を要求したり、任意の custom compliance requirement を強制したりできます。

</details>
