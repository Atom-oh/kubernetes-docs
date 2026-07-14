# Kubernetes バージョン機能とロードマップクイズ

1. Kubernetes のリリース頻度はどれですか？
   - A) 主要機能を含めて年 1 回
   - B) 約 4 か月ごとに、年約 3 回のリリース
   - C) 月次のパッチリリースと四半期ごとの機能リリース
   - D) AWS re:Invent と Summit に合わせて年 2 回

<details>
<summary>答えを表示</summary>

**答え: B) 約 4 か月ごとに、年約 3 回のリリース**

**解説:**
Kubernetes は約 4 か月のリリースサイクルに従い、年に約 3 回の minor version リリースを行います。各リリースは enhancement freeze、code freeze、release candidate フェーズを経ます。最近のリリース: 1.33 (Apr 2025)、1.34 (Aug 2025)、1.35 (Dec 2025)、1.36 (Apr 2026)。その後、各バージョンは約 14 か月間、patch release でメンテナンスされます。

</details>

---

2. EKS Standard Support と Extended Support の違いは何ですか？
   - A) Standard は無料で、Extended には Enterprise ライセンスが必要
   - B) Standard は 14 か月間で $0.10/cluster/hour、Extended はさらに 12 か月間を $0.60/cluster/hour で追加
   - C) Standard は 3 バージョンをサポートし、Extended はすべてのバージョンをサポートする
   - D) Standard は月次でパッチを提供し、Extended は週次でパッチを提供する

<details>
<summary>答えを表示</summary>

**答え: B) Standard は 14 か月間で $0.10/cluster/hour、Extended はさらに 12 か月間を $0.60/cluster/hour で追加**

**解説:**
EKS 上の各 Kubernetes バージョンは 14 か月間の standard support ($0.10/cluster/hour) を受け、その後 12 か月間の extended support ($0.60/cluster/hour — コストは 6 倍) が続きます。バージョンごとの合計サポート期間は 26 か月です。Extended support はデフォルトで有効です。あるバージョンが extended support を終了すると、cluster は自動的にアップグレードされます。この料金差は、サポート対象バージョンに留まることを促します。

</details>

---

3. Sidecar Containers が GA に昇格した Kubernetes バージョンはどれですか？
   - A) 1.28 (alpha として初めて導入されたとき)
   - B) 1.31
   - C) 1.33
   - D) 1.35

<details>
<summary>答えを表示</summary>

**答え: C) 1.33**

**解説:**
Native Sidecar Containers (KEP-753) は次の昇格パスをたどりました: v1.28 (Aug 2023) で alpha、v1.29 (Dec 2023) で beta、v1.33 (Apr 2025) で GA。Sidecar は `restartPolicy: Always` を持つ init containers として定義され、application containers より前に起動し、Pod lifecycle 全体を通して実行され、main containers の後に終了することを保証します。これにより、Jobs における長年の "zombie sidecar" 問題を解決します。

</details>

---

4. In-Place Pod Resize 機能とは何で、いつ GA に到達しましたか？
   - A) 再デプロイなしで Pod replicas を変更できる機能。1.30 で GA
   - B) 実行中の Pods に対して restart なしで CPU/memory requests と limits を変更できる機能。1.35 で GA
   - C) PersistentVolumes をオンラインで resize できる機能。1.31 で GA
   - D) 実行中の Pods の container images を変更できる機能。1.34 で GA

<details>
<summary>答えを表示</summary>

**答え: B) 実行中の Pods に対して restart なしで CPU/memory requests と limits を変更できる機能。1.35 で GA**

**解説:**
In-Place Pod Resize (KEP-1287) は、実行中の Pods で CPU と memory の requests/limits を変更可能にします。昇格: v1.27 で alpha、v1.33 で beta、v1.35 (Dec 2025) で GA。v1.33 からは、変更に `/resize` subresource を使用します。`resizePolicy` field は、resource type ごとに container restart が必要かどうかを制御します。この機能は VPA integration にとって変革的であり、Pod disruption なしに resource right-sizing を可能にします。

</details>

---

5. Kubernetes 1.31 で Dynamic Resource Allocation (DRA) に起きた大きな変更は何ですか？
   - A) DRA が deprecated となり、Device Plugins v2 に置き換えられた
   - B) Classic DRA が削除され、Structured Parameters DRA のみが残った (これは後に 1.34 で GA に到達)
   - C) DRA が alpha から直接 GA に昇格した
   - D) DRA が GPUs に加えて network devices のサポートを追加した

<details>
<summary>答えを表示</summary>

**答え: B) Classic DRA が削除され、Structured Parameters DRA のみが残った (これは後に 1.34 で GA に到達)**

**解説:**
DRA は大幅に再設計されました。Classic DRA (KEP-3063、v1.26 以降 alpha) は、scheduler と cluster autoscaler が推論できない opaque vendor parameters を使用していました。Structured Parameters DRA (KEP-4381) は、`ResourceSlice` objects を使用する Kubernetes-native 形式でそれを置き換えました。v1.31 では、classic DRA が完全に削除されました。Structured DRA は v1.32 で beta、v1.34 で GA へ進みました。これは AI/ML workloads における GPU/accelerator scheduling にとって重要です。

</details>

---

6. Kubernetes 1.30 で GA に昇格し、webhooks なしで declarative admission control を可能にする機能はどれですか？
   - A) OPA Gatekeeper v4
   - B) Kyverno Native Policies
   - C) CEL expressions を使用する ValidatingAdmissionPolicy
   - D) Pod Security Standards enforcement

<details>
<summary>答えを表示</summary>

**答え: C) CEL expressions を使用する ValidatingAdmissionPolicy**

**解説:**
ValidatingAdmissionPolicy (KEP-3488) は Common Expression Language (CEL) expressions を使用した in-process validation を提供し、external webhook servers の必要性をなくします。昇格: v1.26 で alpha、v1.28 で beta、v1.30 (Apr 2024) で GA。これは 3 つの resource types を使用します: ValidatingAdmissionPolicy (rules)、ValidatingAdmissionPolicyBinding (resources への binding)、および optional parameter CRDs。これにより、webhook-based admission control と比較して latency、complexity、failure domains が削減されます。

</details>

---

7. KYAML とは何で、現在のステータスは何ですか？
   - A) Kubernetes YAML linter。1.35 で GA
   - B) strict formatting を使用する、Kubernetes 向けのより安全で曖昧さの少ない YAML subset。1.35 で beta、デフォルトで有効
   - C) YAML-to-JSON converter tool。1.34 で alpha
   - D) Kubernetes manifest validation schema。1.30 以降 stable

<details>
<summary>答えを表示</summary>

**答え: B) strict formatting を使用する、Kubernetes 向けのより安全で曖昧さの少ない YAML subset。1.35 で beta、デフォルトで有効**

**解説:**
KYAML は Kubernetes 専用に設計された、より厳格な YAML subset であり、YAML の悪名高い曖昧さを排除します。maps には curly brackets ({})、lists には square brackets ([])、すべての strings には double quotes を使用します。v1.34 で alpha として導入され、v1.35 (Dec 2025) で beta に昇格し、デフォルトで有効になっています。`KUBECTL_KYAML=false` で無効化できます。これは YAML における "Norway problem" (NO が boolean false と解釈される) のような長年の問題に対処します。

</details>

---

8. EKS clusters に推奨される version upgrade planning strategy はどれですか？
   - A) upgrade frequency を最小化するためにバージョンをスキップする (例: 1.29 → 1.33)
   - B) minor version を 1 つずつアップグレードし、staging で feature gates をテストし、本番前に API compatibility と add-on alignment を確認する
   - C) 常に latest version を使用し、rollback には extended support に依存する
   - D) stability を確保するため、アップグレード前にバージョンが extended support に到達するまで待つ

<details>
<summary>答えを表示</summary>

**答え: B) minor version を 1 つずつアップグレードし、staging で feature gates をテストし、本番前に API compatibility と add-on alignment を確認する**

**解説:**
EKS では minor version upgrades を順番に行う必要があります (1.33 → 1.34 → 1.35。スキップはサポートされていません)。Best practices: (1) 新しい feature gates と API changes をまず staging environments でテストする、(2) target version との add-on compatibility を確認する、(3) deprecated APIs を確認するために `kubectl convert` を実行する、(4) control plane を最初にアップグレードし、その後 add-ons、node groups の順にアップグレードする。Standard support に留まることで、extended support の 6 倍のコスト増を回避し、最新の security patches へのアクセスを確保できます。

</details>
