# SageMaker Qwen プラットフォームアーキテクチャクイズ

## 選択式問題

1. この設計では、モデルの出力と Python による処理はどのように関係しますか？

   - A) モデルがすべての PII を確実に除去する
   - B) モデルが候補 TSV を出力し、コードが検証して置換する。検出漏れは別途評価する
   - C) 往復処理によって匿名性が証明される
   - D) モデルが project を削除する

<details>
<summary>回答を表示</summary>

**回答: B**

決定的な置換処理によって、モデルが見逃したエンティティが自動的に復元されるわけではありません。

</details>

2. 図と検証記録は、どのように解釈すべきですか？

   - A) 2つの GPU 経路がどちらも検証済みである
   - B) これは目標設計であり、ローカルテストと過去の AWS 上の観測を区別する
   - C) project の残存数がリアルタイムで表示されている
   - D) 学習済みモデルの F1 とコストが報告されている

<details>
<summary>回答を表示</summary>

**回答: B**

2026-09-01 の記録では、training の前に停止しています。ローカルテストでは、AWS の現在の状態や GPU の実行結果は証明されません。

</details>

3. モデル ID と seed が同じなら、環境間で結果を完全に再現できますか？

   - A) 常に再現できる
   - B) できない。revision、データ hash、image/依存関係、CUDA/ハードウェア、実行条件も検証する
   - C) EKS だけ seed が必要
   - D) QLoRA では tokenizer は関係ない

<details>
<summary>回答を表示</summary>

**回答: B**

直接指定した package pin だけでは、依存関係全体の lock にはなりません。また、GPU の決定性には追加の要件があります。

</details>

4. 通常の MLflow log や公開レポートから除外すべきものはどれですか？

   - A) Dataset hash
   - B) レビュー済み LoRA 設定
   - C) 未加工の source/completion、token mapping、presigned URL
   - D) 機密性のない集計値

<details>
<summary>回答を表示</summary>

**回答: C**

必要な非公開インベントリ ID/ARN と、公開情報を区別し、autologging/tracing を確認してください。

</details>

5. ガバナンスとモデルサイズについて、正しい説明はどれですか？

   - A) QLoRA には常に Unified Studio project が必要
   - B) ガバナンスはこの実験で選択した手順であり、active 3.3B はモデル全体のメモリ量を表さない
   - C) owner の割り当てによって、部分的な失敗がすべて自動的にロールバックされる
   - D) Job の上限が3時間なので、実験の全コストが制限される

<details>
<summary>回答を表示</summary>

**回答: B**

Model card には total 30.5B/active 3.3B と記載されています。readiness/ownership と、実際の GPU memory/コストはそれぞれ別に検証してください。

</details>

---

[学習資料に戻る](../../../ai-ml/sagemaker-ai/01-platform-architecture.md)
