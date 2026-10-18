# 合成 PII データとトークン化クイズ

## 選択式問題

1. モデル出力の契約と、その限界は何ですか？

   - A) 正しい匿名化文書を常に生成する
   - B) すべての source string が PII である
   - C) TYPE/TAB/ORIGINAL の候補行を出力し、見落とし/誤分類は別途評価する
   - D) project membership を返す

<details>
<summary>回答を表示</summary>

**回答: C**

Source matching で確認できるのは出現箇所であり、意味的な正しさや完全な検出ではありません。

</details>

2. 空白の異なる名前と、既存の [PERSON_1] はどのように処理されますか？

   - A) どの表記も1つの mapping 値で上書きする
   - B) 表記ごとに復元可能な token を使い、既存の marker 名は避ける
   - C) 古い marker を常に新しい名前として復元する
   - D) source を任意に短くする

<details>
<summary>回答を表示</summary>

**回答: B**

同じ type/表記には同じ token を再利用し、異なる表記にはそれぞれ別の token を割り当て、実際の source text に対応付けます。

</details>

3. データの split と検証範囲について、正しい説明はどれですか？

   - A) レコード数は1,600/200/400であり、template/名前は split 間で共有される場合がある
   - B) hash が異なれば実ワークロードへの汎化が証明される
   - C) checksum の失敗は、公式な割り当てがないことを証明する
   - D) すべての PHONE が公式に予約された番号である

<details>
<summary>回答を表示</summary>

**回答: A**

既存の generator-1.0.0 hash は維持します。合成 template のテストと、実ワークロードでの評価を区別してください。

</details>

4. 正解が Alpha Beta なのに Alpha だけを masking した場合、修正後の leakage 評価では何を行いますか？

   - A) 文字列全体が消えたので、常にゼロと報告する
   - B) 正解 source span に未カバーの部分があることを検出する
   - C) placeholder 名だけを検索する
   - D) 往復処理に成功したら leakage をゼロに上書きする

<details>
<summary>回答を表示</summary>

**回答: B**

replacement の union が source span 全体を覆うか確認します。復元と完全な検出は別々の指標です。

</details>

5. 回答 TSV を使う2,200件の oracle check で確認できるのは何ですか？

   - A) fine-tuned model の実測 F1
   - B) GPU throughput
   - C) evaluator/restoration/hash の妥当性であり、モデル出力の品質ではない
   - D) 実際の PII をすべて検出できる保証

<details>
<summary>回答を表示</summary>

**回答: C**

ローカルテスト50件と oracle check は合格しました。GPU training も fine-tuned model の評価も実行されていません。

</details>

---

[学習資料に戻る](../../../ai-ml/sagemaker-ai/02-pii-data-tokenization.md)
