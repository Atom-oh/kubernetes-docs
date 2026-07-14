# Upgrade Operations クイズ

> **関連ドキュメント**: [Upgrade Operations](../../ops/11-upgrade-operations.md)

## 選択問題

### 1. AWS は各 EKS Kubernetes version を standard support でどのくらいの期間サポートしますか？

- A) 6 か月
- B) 12 か月
- C) 14 か月
- D) 24 か月

<details>
<summary>答えを表示</summary>

**回答: C) 14 か月**

**解説:**
AWS は EKS 上の各 Kubernetes version に対して 14 か月の standard support を提供します。その後、clusters は extended support（追加費用）に移行するか、upgrade する必要があります。standard support window 内で upgrade を計画することが推奨されます。

</details>

### 2. cluster 内の deprecated Kubernetes APIs を検出する tool は何ですか？

- A) kubectl
- B) Pluto
- C) Helm
- D) Terraform

<details>
<summary>答えを表示</summary>

**回答: B) Pluto**

**解説:**
Pluto は Kubernetes manifests、Helm releases、live clusters を scan し、deprecated または削除された API versions を検出します。これにより、それらの APIs が存在しなくなる version へ upgrade する前に、更新が必要な resources を特定できます。

</details>

### 3. EKS upgrade operations における Velero の目的は何ですか？

- A) Kubernetes version を upgrade するため
- B) upgrade 前に cluster resources を backup および restore するため
- C) cluster performance を monitor するため
- D) node groups を管理するため

<details>
<summary>答えを表示</summary>

**回答: B) upgrade 前に cluster resources を backup および restore するため**

**解説:**
Velero は Kubernetes resources と persistent volumes の backup および restore 機能を提供します。upgrades の前に Velero backup を取得しておくことで、upgrade によって問題が発生した場合に recovery が可能になり、operation の safety net を提供します。

</details>

### 4. Terraform 3-Layer architecture では、正しい upgrade order は何ですか？

- A) Workload -> Platform -> Foundation
- B) Platform -> Foundation -> Workload
- C) Foundation -> Platform -> Workload
- D) すべての layers を同時に実施する

<details>
<summary>答えを表示</summary>

**回答: C) Foundation -> Platform -> Workload**

**解説:**
upgrade order は dependencies に従います。Platform は Foundation に依存するため Foundation (VPC, IAM) が最初、Workload は Platform に依存するため次に Platform (EKS cluster)、最後に Workload (applications) です。これにより、各 layer の dependencies がすでに upgrade されていることを保証します。

</details>

### 5. EKS Auto Mode では、Kubernetes version upgrade 中に nodes はどうなりますか？

- A) nodes は restart なしで in-place upgrade される
- B) nodes は新しい version の nodes に自動的に置き換えられる
- C) nodes は手動で削除する必要がある
- D) nodes は version upgrades の影響を受けない

<details>
<summary>答えを表示</summary>

**回答: B) nodes は新しい version の nodes に自動的に置き換えられる**

**解説:**
EKS control plane を upgrade した後、Auto Mode は新しい version に合わせて nodes を自動的に rotate します。この process では古い nodes を cordon し、workloads を drain して、更新された kubelet version を持つ新しい nodes を provision します。

</details>

### 6. upgrade 前に Pod Disruption Budgets (PDBs) で何を確認すべきですか？

- A) PDBs が存在しないこと
- B) PDBs が rolling node replacement に十分な disruption を許可していること
- C) PDBs が zero に設定されていること
- D) PDBs が正しい API versions を参照していること

<details>
<summary>答えを表示</summary>

**回答: B) PDBs が rolling node replacement に十分な disruption を許可していること**

**解説:**
制約が強すぎる PDBs（例: maxUnavailable: 0 かつ minAvailable: 100%）は、upgrades 中の node draining を block する可能性があります。upgrade 前に、PDBs が rolling replacement process を進めるために十分な disruption を許可していることを確認してください。

</details>

### 7. EKS clusters の blue/green upgrade strategy とは何ですか？

- A) 両方の clusters を同時に upgrade すること
- B) 新しい version の新しい cluster を作成し、traffic を段階的に移行すること
- C) rollback capability を備えて in-place upgrade すること
- D) 同じ nodes 上で両方の versions を実行すること

<details>
<summary>答えを表示</summary>

**回答: B) 新しい version の新しい cluster を作成し、traffic を段階的に移行すること**

**解説:**
blue/green upgrade は、既存の「blue」cluster と並行して、target Kubernetes version を実行する新しい「green」cluster を作成します。weighted routing を使用して traffic を段階的に移行し、問題が発生した場合は traffic を blue に戻すことで簡単に rollback できます。

</details>

### 8. upgrade 後にはどのような validation を実施すべきですか？

- A) pods が running であることだけを確認する
- B) node status、pod health、addon functionality、application behavior を verify する
- C) validation は不要である
- D) Pluto をもう一度実行するだけ

<details>
<summary>答えを表示</summary>

**回答: B) node status、pod health、addon functionality、application behavior を verify する**

**解説:**
upgrade 後の validation には、すべての nodes が Ready、pods が Running、cluster addons (CoreDNS, kube-proxy, CNI) が functional、ingress/egress が動作、storage operations が成功、application-specific health checks が pass していることを含めるべきです。

</details>

### 9. EKS extended support は standard support とどのように異なりますか？

- A) extended support は無料である
- B) extended support は追加費用で standard を超える追加月数を提供する
- C) extended support は security patches のみを対象とする
- D) extended support は Fargate 専用である

<details>
<summary>答えを表示</summary>

**回答: B) extended support は追加費用で standard を超える追加月数を提供する**

**解説:**
EKS extended support により、clusters は 14 か月の standard window を超えて古い Kubernetes versions で実行できますが、追加の per-cluster-hour cost が発生します。これにより、upgrade により多くの時間を必要とする organizations に flexibility が提供されます。

</details>

### 10. upgrade 時に addon compatibility を確認することが重要なのはなぜですか？

- A) addons は自動的に upgrade されるため
- B) 一部の addon versions は特定の Kubernetes versions とのみ compatible であるため
- C) addons は upgrades に影響しないため
- D) addons は upgrade 前に削除する必要があるため

<details>
<summary>答えを表示</summary>

**回答: B) 一部の addon versions は特定の Kubernetes versions とのみ compatible であるため**

**解説:**
EKS managed addons (VPC CNI, CoreDNS, kube-proxy) と third-party addons には、Kubernetes versions との version compatibility matrices があります。compatible でない addon version に upgrade すると、cluster functionality が壊れる可能性があります。cluster upgrade とあわせて addon upgrades を確認し、計画してください。

</details>
