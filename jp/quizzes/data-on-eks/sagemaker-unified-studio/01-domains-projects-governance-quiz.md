# Unified Studio の Domain と Project ガバナンスクイズ

## 選択式問題

1. project profile を正しく説明しているのはどれですか？

   - A) GPU driver だけを選択する
   - B) blueprint を組み合わせ、作成時またはオンデマンドで使うツールを設定する
   - C) All capabilities によって、すべてのツールが直ちに使用可能になる
   - D) あらゆる IAM 権限を置き換える

<details>
<summary>回答を表示</summary>

**回答: B**

意図した profile ID、domain type、必要な blueprint/account/Region を確認してください。

</details>

2. IAM の DeleteProject 権限と通常の contributor membership があれば、削除が保証されますか？

   - A) 常に保証される
   - B) されない。削除経路で必要な owner/admin の権限と、その他の IAM/service policy を確認する
   - C) EKS namespace が一致すれば保証される
   - D) project 名が一意なら保証される

<details>
<summary>回答を表示</summary>

**回答: B**

Project の所有権、API の認可、実際のデータ/リソース権限は、それぞれ別の境界です。

</details>

3. projectStatus=ACTIVE はどのように解釈すべきですか？

   - A) すべての環境と GPU tool が使用可能である
   - B) project の状態を示すものであり、必要な environmentDeploymentDetails と tool access は別途確認する
   - C) すべてのオンデマンド機能がすでにプロビジョニング済みである
   - D) Training が成功した

<details>
<summary>回答を表示</summary>

**回答: B**

意図的にプロビジョニングしていないオンデマンドツールと、実際の失敗を区別してください。

</details>

4. CreateProject の membershipAssignments member に設定する内容はどれですか？

   - A) 常に userIdentifier と groupIdentifier の両方
   - B) 意図した profile に合う userIdentifier または groupIdentifier のどちらか1つ
   - C) IAM secret access key
   - D) group profile ID の代わりに任意の IAM role ARN

<details>
<summary>回答を表示</summary>

**回答: B**

これは tagged union です。同一リクエスト内での割り当てによって、すべての環境プロビジョニングが atomic にロールバックされる保証はありません。結果を確認してください。

</details>

5. 残っている project の削除は、どのように確認すべきですか？

   - A) AccessDenied を存在しないことの証拠として扱う
   - B) 許可された get/list の範囲、domain、filter/pagination、所有リソースのインベントリを確認する
   - C) 9月初旬の記録が現在の状態を証明する
   - D) tag の失敗後、同じ prefix を持つ共有 bucket/role をすべて削除する

<details>
<summary>回答を表示</summary>

**回答: B**

過去の記録は、現在の確認の代わりにはなりません。クリーンアップは、実行の所有者と保持ポリシーに従ってください。

</details>

---

[学習資料に戻る](../../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md)
