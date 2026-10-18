# SageMaker Qwen 検証結果クイズ

## 選択式問題

1. 9月2日の再確認で何が分かりましたか？
   - A) 残存リソースはゼロ
   - B) Unified Studio project が1つ `ACTIVE` のまま
   - C) EKS GPU cluster が1つ稼働中
   - D) Training Job が完了

<details>
<summary>回答を表示</summary>

**回答: B**

過去の記録では、App、S3、IAM リソースは回収済みで、project が1つ残っていたと報告されています。9月12日のドキュメント確認では、AWS の現在の状態を再照会していません。
</details>

2. 試行3で主な失敗となったのは何ですか？
   - A) モデル ID の誤記
   - B) project membership の欠落
   - C) dataset hash の不一致
   - D) CUDA out of memory

<details>
<summary>回答を表示</summary>

**回答: B**

呼び出し元の role group profile が owner/member として割り当てられていませんでした。
</details>

3. 公開されなかった結果はどれですか？
   - A) レコード数
   - B) MLflow App のバージョン
   - C) fine-tuned F1 と GPU コスト
   - D) Python のテスト件数

<details>
<summary>回答を表示</summary>

**回答: C**

GPU training は実行されなかったため、これらの比較値は測定されていません。これは、MLflow App や S3 などのリソースにかかる総コストがゼロだったことを意味しません。
</details>

4. 再実行前の最初のゲートは何ですか？
   - A) 完全な Job を送信する
   - B) インベントリを照合し、残存または不明な実験所有リソースを解決する
   - C) EKS cluster を作成する
   - D) 調整済みメトリクスを公開する

<details>
<summary>回答を表示</summary>

**回答: B**

権限エラーや一覧に表示されないことは、削除の証明にはなりません。共有の名前プレフィックスがあるからといって、他者のリソースを削除する権限が得られるわけではありません。
</details>

5. 目標アーキテクチャと実際のワークフローには、どのような違いがありますか？
   - A) どちらも完了を証明する
   - B) 一方は再実行の設計を示し、もう一方は実際に停止した時点を記録する
   - C) どちらもコストレポートである
   - D) 実際のワークフローには完了済み GPU training が示されている

<details>
<summary>回答を表示</summary>

**回答: B**

過去のワークフローは GPU training の前に停止しています。AWS account の現在の状態や、実験の総コストがゼロであることは証明していません。
</details>

---

[学習資料に戻る](../../../ai-ml/sagemaker-ai/04-validation-results.md)
