# 最新のデータパイプラインの構造クイズ

> **最終更新日**: September 12, 2026

1. Kafka offset を再生する前に、何を確認する必要がありますか？
   - A) 必要なレコードが retention/compaction 後も残っているか
   - B) Kafka がすべての外部 sink の重複を自動的に排除するか
   - C) すべての batch input が削除されたか
   - D) すべての event が常に永久に残るか

<details>
<summary>回答を表示</summary>

**回答: A) 必要なレコードが retention/compaction 後も残っているか**

再生には、保持された入力と一貫した状態の復旧が必要です。エンドツーエンドの exactly-once は、sink の transaction、idempotency、外部への副作用にも依存します。

</details>

2. ETL と ELT の違いは何ですか？
   - A) Lake を使うかどうか
   - B) ETL は送信先へのロード前に変換し、ELT はロード後に変換する
   - C) Kafka を使うかどうか
   - D) ELT は常に厳密で、ETL は常に近似的である

<details>
<summary>回答を表示</summary>

**回答: B) ETL は送信先へのロード前に変換し、ELT はロード後に変換する**

整備済みデータを warehouse に移すだけで、処理方式が ELT になるわけではありません。変換の順序と送信先を確認してください。

</details>

3. Batch と stream の精度について、正しい説明はどれですか？
   - A) Streaming は常に近似的である
   - B) Batch は常に厳密である
   - C) 遅れて届くデータ、重複、状態、出力契約によって異なる。高速な暫定結果の後に確定処理を行うこともできる
   - D) Checkpoint によって外部 API の副作用が自動的に exactly-once になる

<details>
<summary>回答を表示</summary>

**回答: C) 遅れて届くデータ、重複、状態、出力契約によって異なる。高速な暫定結果の後に確定処理を行うこともできる**

Event time、watermark、許容する遅延、sink の意味論を設計してください。Spark と Flink がそれぞれ1つの処理モードに限定されるわけではありません。

</details>

4. Schema Registry の互換性チェックについて、正しい説明はどれですか？
   - A) すべての database DDL と意味的な変更を自動的にブロックする
   - B) 適用した登録/serialization/CI の経路を検証するが、consumer test も引き続き必要である
   - C) 1回の登録で、すべてのバージョン間の推移的な互換性が自動的に保証される
   - D) 互換性ルールによりデータ品質チェックが不要になる

<details>
<summary>回答を表示</summary>

**回答: B) 適用した登録/serialization/CI の経路を検証するが、consumer test も引き続き必要である**

迂回経路とビジネス上の意味の変更には、別途検証が必要です。後方/前方互換性と推移的設定の適用範囲を確認してください。

</details>

[学習資料](../../data-on-eks/01-data-pipeline-anatomy.md) | [Kafka クイズ](./kafka/01-kafka-fundamentals-quiz.md)
