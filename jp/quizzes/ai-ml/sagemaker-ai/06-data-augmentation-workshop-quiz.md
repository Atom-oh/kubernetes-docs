# 合成 PII データと拡張クイズ

> **最終更新日**: 2026年9月15日

## 選択式問題

1. 同じ source の paraphrase と OCR variant は、どの順序で扱うべきですか？

   - A) すべての variant を生成してから、record ID をランダムに分割する
   - B) まず source family を split に割り当て、その後 training のみを拡張する
   - C) 各 variant を別々の split に割り当てる
   - D) Test で失敗した結果を最初に training へコピーする

<details>
<summary>回答を表示</summary>

**回答: B**

Split 間で source/variant が漏れるのを防ぐため、すべての派生データを元の source family と同じ split に残します。

</details>

2. 24 family それぞれに base 1件と variant 2件がある場合、training record は何件になりますか？

   - A) 24
   - B) 48
   - C) 72
   - D) 120

<details>
<summary>回答を表示</summary>

**回答: C**

24 × 3 = 72 です。Validation/test の8 family では、それぞれ base のみを残します。

</details>

3. 合成名を置き換える場合に必要なことは何ですか？

   - A) Record ID だけを変更する
   - B) Source を変更し、TSV はそのままにする
   - C) TSV を変更し、source はそのままにする
   - D) Source、entity、TSV を合わせて更新し、lineage を記録する

<details>
<summary>回答を表示</summary>

**回答: D**

変換後の source に対して正解データを再生成してください。文字列が存在することだけでは、意味的な正しさや完全な annotation は証明されません。

</details>

4. Family と完全一致する source を分離することで、このラボから確認できるのは何ですか？

   - A) Family と同一の NFC source が split をまたがない
   - B) 人物と identifier がすべての split で重複しない
   - C) Template がすべての split で重複しない
   - D) 実環境での汎化が検証される

<details>
<summary>回答を表示</summary>

**回答: A**

一部の名前、template、domain は共有されています。Entity/template/domain を holdout する設計は別途必要です。

</details>

5. この policy で除外される代表電話番号だけを含む negative document を変換した場合、target はどうすべきですか？

   - A) 代表電話を PHONE として追加する
   - B) Entity と target_tsv を空のままにする
   - C) UNKNOWN type を追加する
   - D) すべての数字を ACCOUNT として追加する

<details>
<summary>回答を表示</summary>

**回答: B**

Entity を含まない例も重要です。Domain ごとに negative の定義を設け、実際の training で空の回答に対する EOS supervision を確認してください。

</details>

6. File hash を再計算した後でも、このラボが annotation の漏れを見つけられるのはなぜですか？

   - A) Hash がデータ作成者を認証する
   - B) 任意の顧客文書に含まれる PII をすべて検出する
   - C) Seed と固定された family recipe を使って content も再確認する
   - D) Model F1 を自動的に測定する

<details>
<summary>回答を表示</summary>

**回答: C**

これは固定された合成データの演習を再現できるか確認するものであり、任意の annotation や作成者の身元を検証するものではありません。

</details>

7. Original training と augmentation 後の training を比較する際、何を固定するか記録する必要がありますか？

   - A) Test を繰り返し確認し、最良の結果を選ぶ
   - B) File 数だけを比較する
   - C) Generation の成功だけを比較する
   - D) 同じ validation/decoding を使い、example/token/step の予算を記録する

<details>
<summary>回答を表示</summary>

**回答: D**

Step 数が同じでも、モデルが見るデータの長さや量は異なる場合があります。候補の選択には validation を使ってください。

</details>

8. 過去の pairwise overlap 22、36、9を合計した値が、split 間の一意な source group 51件と異なるのはなぜですか？

   - A) 3つすべての split にある source は、複数の pairwise intersection に含まれる
   - B) NFC source は常に別々の document を識別する
   - C) すべての record ID が同じである
   - D) 51 は学習済み model の error 数である

<details>
<summary>回答を表示</summary>

**回答: A**

Pairwise intersection の合計は、一意な source group の数ではありません。これらは CPU でのデータ観測値であり、model performance の値ではありません。

</details>

---

[学習資料に戻る](../../../ai-ml/sagemaker-ai/06-data-augmentation-workshop.md)
