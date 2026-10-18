# データとセキュリティの境界クイズ

> このクイズでは、[データとセキュリティの境界](../../governance/05-data-security-boundaries.md)の理解度を確認します。

---

1. Multi-AZ DB cluster の snapshot を共有できないことから、何が分かりますか？
   - A) すべての復旧経路が利用できない
   - B) その RDS 共有経路は利用できないため、engine 固有の代替復旧方法を検証する
   - C) ワークロードが所有するデータベースが必須である
   - D) すべての AWS Backup vault の動作は同じである

<details>
<summary>回答を表示</summary>

**回答: B) その RDS 共有経路は利用できないため、engine 固有の代替復旧方法を検証する**

**解説:**
1つの API の制約によって、論理バックアップやレプリケーションによる代替手段がすべて排除されるわけではありません。所有者を決める前に、サポート状況と RTO/RPO を検証してください。

</details>

---

2. インシデント後のコピーを必要とする復旧経路では、RTO に何を含める必要がありますか？
   - A) タグの命名規則のみ
   - B) コピー、復元、アプリケーション検証にかかる時間
   - C) 過去の保持期間のみ
   - D) Security Hub のスコアのみ

<details>
<summary>回答を表示</summary>

**回答: B) コピー、復元、アプリケーション検証にかかる時間**

**解説:**
コピーが事前に作成されている場合、コピーの間隔が RPO に影響します。受信側のコピーを必要としない、共有エアギャップ vault からの復元経路と区別してください。

</details>

---

3. クロスアカウントバックアップを有効にした後の認可について、正しい説明はどれですか？
   - A) すべてのユーザーが IAM の Deny を回避できる
   - B) IAM、vault、KMS、コピー先の条件、RAM 共有を合わせて確認する
   - C) Vault が公開される
   - D) Organization から離脱すると、コピーされたバックアップが削除される

<details>
<summary>回答を表示</summary>

**回答: B) IAM、vault、KMS、コピー先の条件、RAM 共有を合わせて確認する**

**解説:**
機能を有効にしても権限は付与されません。標準 vault のコピーとエアギャップ vault の共有は別の経路です。承認済みのコピー先と、ソースが利用できない場合の動作をテストしてください。

</details>

---

4. Security Hub CSPM が Config に依存するとは、どういう意味ですか？
   - A) Config なしですべての control が機能する
   - B) ほとんどの CSPM control では記録が必要だが、これは Identity Center サービスの依存関係ではない
   - C) GuardDuty を置き換える
   - D) すべての AWS MCP request で Config が必要である

<details>
<summary>回答を表示</summary>

**回答: B) ほとんどの CSPM control では記録が必要だが、これは Identity Center サービスの依存関係ではない**

**解説:**
Control Tower が管理するベースラインの依存関係と、Identity Center サービスの要件を区別してください。Security Hub の機能範囲と Region のカバレッジを確認します。

</details>
