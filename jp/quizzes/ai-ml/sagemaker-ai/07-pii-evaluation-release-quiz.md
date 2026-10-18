# PII 評価と redaction pipeline のクイズ

> **最終更新日**: September 15, 2026

## 選択式問題

1. Fixture candidate によって F1 が0.8に改善しました。すぐに deploy すべきでないのはなぜですか？

   - A) Recall がゼロだから
   - B) Negative document 番号を account として masking しており、評価対象が合成 document 2件だけだから
   - C) 正解の entity をすべて見逃しているから
   - D) Round-trip に失敗したから

<details>
<summary>回答を表示</summary>

**回答: B**

TP/FP/FN は2/1/0です。集計スコアの改善と、新しく発生した masking error を合わせて評価してください。

</details>

2. Round-trip rate が1.0であることから何が分かりますか？

   - A) 実際の PII がすべて検出された
   - B) Source に PII が含まれていなかった
   - C) Mapping により masked result から NFC source を再構築できた
   - D) Model が新しい顧客にも汎化する

<details>
<summary>回答を表示</summary>

**回答: C**

Restoration に成功しても、見落とされた PII が source に残っている可能性があります。

</details>

3. 現在の entities.over_redaction_rate の計算方法はどれですか？

   - A) 不必要に masking された文字数 / 全文字数
   - B) 漏洩した document 数 / 全 document 数
   - C) FN / 正解 pair 数
   - D) 余分に抽出された pair 数 / 予測 pair 数

<details>
<summary>回答を表示</summary>

**回答: D**

過去の名前とは異なり、文字単位の過剰な削除ではなく、余分に抽出された pair を測定します。

</details>

4. 厳密な serving parser は何をすべきですか？

   - A) すべての row/type/length/truncation を検証し、明示的な failure を返す
   - B) 1つの row が有効なら応答全体を受け入れる
   - C) 不正な row を削除し、PII がないと報告する
   - D) 見落とされた候補を追加で作る

<details>
<summary>回答を表示</summary>

**回答: A**

現在の寛容な parse が成功することと、厳密な契約を満たすことは異なります。Truncated result を完全な結果として扱わないでください。

</details>

5. Rank の選択に繰り返し使った test set は、どのように扱うべきですか？

   - A) 引き続き独立した最終 test とみなす
   - B) 開発/選択に使った evaluation set とみなす
   - C) Gradient 更新に使っていないため、影響はない
   - D) Hash が固定されているため、独立性は保たれる

<details>
<summary>回答を表示</summary>

**回答: B**

Gradient 更新をしていなくても、選択に使うと最終 test の独立性が損なわれる可能性があります。Validation と lock した test を分けてください。

</details>

6. Data 設計では max_sequence_length=1024 をどのように解釈すべきですか？

   - A) Document の文字を1,024文字だけ数える
   - B) Korean と English で文字/token の比率は同じ
   - C) Template、instruction、source、completion の tokenizer budget を確認する
   - D) Model がより大きな context をサポートしていれば、この設定は無視される

<details>
<summary>回答を表示</summary>

**回答: C**

Target/source の truncation による PII の欠落を確認し、Chunking 時の境界と offset の再構成を評価してください。

</details>

7. SageMaker Training Job が Completed になった後も必要なことは何ですか？

   - A) 品質を確認せずに、ただちに endpoint に接続する
   - B) Base model を使わず、adapter だけで推論する
   - C) すべての downstream log に mapping を添付する
   - D) 正確な base/tokenizer/adapter/parser の組み合わせを再読み込みし、評価して承認する

<details>
<summary>回答を表示</summary>

**回答: D**

Job の終了と、service の品質や redaction の承認は別です。完全な rollback の組み合わせに version を付けてください。

</details>

8. Gold data のない production document で、この evaluator は同じ漏洩率を計算できますか？

   - A) できない。レビュー済み annotation、残存確認、それぞれの測定範囲を区別する
   - B) できる。Model の出力をすべて gold として扱う
   - C) できる。Round-trip に成功すれば漏洩はゼロである
   - D) できる。出力が空なら PII はすべて除去された

<details>
<summary>回答を表示</summary>

**回答: A**

この指標は、Gold value のうち未検出のものを確認します。Gold がなければ、同じ完全性指標は利用できません。

</details>

---

[学習資料に戻る](../../../ai-ml/sagemaker-ai/07-pii-evaluation-release.md)
