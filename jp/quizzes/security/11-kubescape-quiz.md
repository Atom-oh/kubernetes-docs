# Kubescape クイズ

> **最終更新**: September 13, 2026

## 問題

<span id="_1-what-is-kubescape-s-project-status-in-the-cncf"></span>

### 1. Kubescape の現在の CNCF 成熟度レベルは何ですか？

- A) 卒業
- B) インキュベーティング
- C) サンドボックス
- D) アーカイブ済み

<details>
<summary>回答を表示</summary>

**回答: B) インキュベーティング**

Kubescape は 2022 年 12 月 13 日に CNCF に参加し、2025 年 1 月 13 日に Incubating になりました。これは、個別のインストールのセキュリティまたは可用性を保証するものではありません。

</details>

<span id="_2-which-security-frameworks-does-kubescape-support-for-compliance-scanning"></span>

### 2. フレームワーク名とコントロール数は、どのように検証すべきですか？

- A) 常に古い CIS エイリアスを使用する
- B) バイナリ／ポリシーのバージョンを記録し、実際のリストを確認する
- C) NSA のコントロール数は変更されない
- D) SOC2 スキャンに合格すれば認定は完了する

<details>
<summary>回答を表示</summary>

**回答: B) バイナリ／ポリシーのバージョンを記録し、実際のリストを確認する**

kubescape list frameworks および list controls --framework NSA を使用します。レビューした NSA スナップショットには 26 個のコントロールが含まれており、適用可能性は入力によって決まります。スコアを比較する際は、ポリシーハッシュを保持してください。

</details>

<span id="_3-what-is-the-correct-cli-syntax-to-scan-a-kubernetes-cluster-with-kubescape"></span>

### 3. kubescape scan でローカルファイルのターゲットを省略すると、どうなりますか？

- A) 常に失敗する
- B) 現在の kubeconfig クラスターをスキャンできる
- C) 常にローカルファイルのみをスキャンする
- D) 常に dry run を実行する

<details>
<summary>回答を表示</summary>

**回答: B) 現在の kubeconfig クラスターをスキャンできる**

CI では、存在する明示的なローカルファイルを渡し、空または存在しないターゲットを拒否する必要があります。--keep-local、分離されたキャッシュ、固定されたポリシーは、入力スコープの確認に代わるものではありません。

</details>

<span id="_4-what-is-the-key-difference-between-kubescape-operator-and-cli-modes"></span>

### 4. Operator と CLI の動作を正しく区別している記述はどれですか？

- A) Operator は GUI のみを提供する
- B) CLI は明示的／アドホックなスキャンを処理し、Operator は有効化された継続的／スケジュールされた機能を実行する
- C) Operator をインストールすれば、すべてのランタイム機能が動作することを証明できる
- D) CLI と Operator のイメージは常に同じバージョンである

<details>
<summary>回答を表示</summary>

**回答: B) CLI は明示的／アドホックなスキャンを処理し、Operator は有効化された継続的／スケジュールされた機能を実行する**

Chart 1.40.4 は scanner image 4.0.13 をレンダリングしますが、テスト済みのローカル CLI は 4.0.14 です。Node／image／runtime／remediation のスコープと権限には、個別の選択と検証が必要です。

</details>

<span id="_5-how-does-kubescape-calculate-risk-scores-for-controls"></span>

### 5. score と complianceScore はどのような関係にありますか？

- A) 常に等しい
- B) 常に合計が 100 になる
- C) 結果スキーマでは別々の集計値である
- D) どちらも平均 CVSS 値である

<details>
<summary>回答を表示</summary>

**回答: C) 結果スキーマでは別々の集計値である**

合成された安全でない Pod では、compliance は 55、score は 62.5 になりました。summaryDetails.complianceScore と summaryDetails.score を参照してください。これらのローカル値は、実際のクラスターのセキュリティを測定するものではありません。

</details>

<span id="_6-which-flag-enforces-a-compliance-threshold-in-ci-cd-pipelines"></span>

### 6. compliance が 55 で --compliance-threshold 56 の場合、どうなりますか？

- A) 最大リスク制限であるため、合格する
- B) 最低 compliance を満たさないため、終了コード 1 で終了する
- C) 常に終了コード 2 で終了する
- D) 現在の --fail-threshold 0 ゲートと同等である

<details>
<summary>回答を表示</summary>

**回答: B) 最低 compliance を満たさないため、終了コード 1 で終了する**

同じフィクスチャは、しきい値 55 では終了コード 0 を返し、56 では終了コード 1 を返しました。バージョン 4.0.14 は非推奨の --fail-threshold を受け入れますが、その値は無視します。ゲートとして使用しないでください。

</details>

<span id="_7-how-does-kubescape-differ-from-kube-bench"></span>

### 7. kube-bench と Kubescape を比較するための妥当な基準は何ですか？

- A) 名前に基づき、一方がすべてのチェックを置き換えると想定する
- B) 実際の Node／CIS と workload／config のスコープおよびアクセスを比較する
- C) どちらもアクセスなしですべての control plane 設定を検査できる
- D) Kubescape の合格は CIS 証明書である

<details>
<summary>回答を表示</summary>

**回答: B) 実際の Node／CIS と workload／config のスコープおよびアクセスを比較する**

管理された EKS control plane、ローカルマニフェスト、Node ファイルへのアクセスでは、可視性が異なります。利用不可／未評価のチェックと合格を区別し、それに応じてツールを選択してください。

</details>

<span id="_8-what-feature-does-kubescape-provide-for-rbac-security-analysis"></span>

### 8. RBAC コントロールに関する正しい記述はどれですか？

- A) C-0036 は常にワイルドカード RBAC をチェックする
- B) RoleBinding はすべての Namespace でアクセスを付与する
- C) 現在のコントロール ID／名前と収集スコープを確認する
- D) scan rbac はレビュー対象の CLI では別のサブコマンドである

<details>
<summary>回答を表示</summary>

**回答: C) 現在のコントロール ID／名前と収集スコープを確認する**

レビューしたバンドルでは、C-0035 は Administrative Roles に、C-0036／0039 は validating／mutating admission チェックにマッピングされています。RoleBinding は Namespace ごとのものです。静的解析では、外部 IAM が自動的に検証されるわけではありません。

</details>

<span id="_9-which-vulnerability-scanner-does-kubescape-integrate-with-for-image-scanning"></span>

### 9. image スキャンと host スキャンを正しく区別している記述はどれですか？

- A) host スキャンは image CVE のみをチェックする
- B) 明示的な image スキャンには registry／DB へのアクセスが必要であり、host スキャンには別のスコープがある
- C) Grype は SBOM のみを生成する
- D) image／platform／database のバージョンは重要ではない

<details>
<summary>回答を表示</summary>

**回答: B) 明示的な image スキャンには registry／DB へのアクセスが必要であり、host スキャンには別のスコープがある**

CLI は Grype と Syft を使用します。Operator の kubevuln は個別にバージョン管理されています。host スキャンには追加のリソース／権限が必要になる場合があります。この監査では、image pull も host スキャンも実行されませんでした。

</details>

<span id="_10-how-does-kubescape-handle-control-exceptions"></span>

### 10. 正しい CLI と in-cluster の例外形式は何ですか？

- A) CLI は任意の ConfigMap を直接使用する
- B) CLI JSON 配列の alertOnly と v1beta1 SecurityException の alert_only を区別する
- C) すべての ignore annotation は自動的に例外となる
- D) 例外を記録すれば問題は修正される

<details>
<summary>回答を表示</summary>

**回答: B) CLI JSON 配列の alertOnly と v1beta1 SecurityException の alert_only を区別する**

テストでは、alertOnly は compliance を変更せずに失敗を認識しました。exclude-controls は評価の分母を変更します。remediation とは別に、所有者、スコープ、有効期限、および再レビューを追跡してください。

</details>

## スコア計算

- 9～10: 十分に理解している
- 7～8: 見落としたスコープ／ゲートの概念を復習する
- 6 以下: ガイドとテスト済みの例を確認する

## 関連ドキュメント

- [Kubescape](../../security/11-kubescape.md)
