# Ray Train / Tune クイズ

## 選択式問題

1. Ray Train が自動的に実装しないものはどれですか？
   - A) 基盤となる worker の協調
   - B) Framework の process group セットアップ
   - C) すべての model/data partition/state save-and-restore ロジック
   - D) Ray リソースリクエスト

<details>
<summary>回答を表示</summary>

**回答: C**

model/data-loader の統合と、実際の model、optimizer、checkpoint ロジックを用意します。
</details>

2. 2.58.0 で確認された Train V2 のデフォルトはどれですか？
   - A) environment variable が未設定の場合は V2
   - B) V1 のみ実行可能
   - C) TorchTrainer の import が削除された
   - D) Ray extras が PyTorch を自動的にインストールする

<details>
<summary>回答を表示</summary>

**回答: A**

古い implementation を明示的に選択する実行と区別します。Framework は別途必要な dependency です。
</details>

3. V2 で legacy trainer_resources を設定すると何が起こりますか？
   - A) 常により多くの controller CPU を予約する
   - B) deprecation error が発生する
   - C) GPU 数が増加する
   - D) Tune trial 数が変わる

<details>
<summary>回答を表示</summary>

**回答: B**

controller、training worker、Tune driver のリソーススコープは異なります。
</details>

4. Checkpoint.from_directory は何をしますか？
   - A) すべての model/optimizer/RNG state を自動的にキャプチャする
   - B) ユーザーが用意した checkpoint directory 内のファイルを参照する
   - C) model をデプロイする
   - D) dataset を匿名化する

<details>
<summary>回答を表示</summary>

**回答: B**

recovery payload を実装し、get_checkpoint から返される checkpoint をロードします。
</details>

5. 2.58.0 の V2 report 参加ルールはどれですか？
   - A) rank 0 のみが呼び出す
   - B) すべての worker が同じ回数 barrier に到達する
   - C) すべての metric が自動的に平均化される
   - D) checkpoint なしでは呼び出せない

<details>
<summary>回答を表示</summary>

**回答: B**

rank 0 のみがファイルを保存する場合でも、他の worker は checkpoint=None を report します。
</details>

6. max_failures=0 はすべての retry を無効にしますか？
   - A) はい
   - B) いいえ。controller と preemption の retry には個別の設定があります
   - C) 常に無限 retry を意味する
   - D) Karpenter の retry のみを無効にする

<details>
<summary>回答を表示</summary>

**回答: B**

controller_failure_limit と max_preemption_failures の確認済みデフォルトはいずれも -1 です。
</details>

7. 現在の V2 Train/Tune 統合パターンはどれですか？
   - A) V2 Trainer instance を直接 Tuner に渡す
   - B) function trainable 内で Trainer を構築して fit し、必要に応じて callback を接続する
   - C) ライブラリを組み合わせることはできない
   - D) 常に別の Kubernetes cluster が必要である

<details>
<summary>回答を表示</summary>

**回答: B**

V2 Trainer を直接入力すると、native check で TuneError が発生しました。統合には wiring とリソース計画が必要です。
</details>

8. TuneReportCallback は何を転送しますか？
   - A) 自動的に平均化された worker metric
   - B) 2 回目の checkpoint upload
   - C) 最初の worker の metric dictionary と既存の checkpoint path
   - D) Tune session の外部でも常に動作する

<details>
<summary>回答を表示</summary>

**回答: C**

Tune session 内で構築します。metric aggregation は別途実行します。
</details>

## 短答式問題

9. なぜ trial driver と Train worker をまとめて予算化する必要があるのですか？

<details>
<summary>回答を表示</summary>

driver は、ネストされた worker または placement group に必要なリソースを占有する可能性があります。concurrency、worker bundle、cluster 境界、および node ごとの実現可能性をまとめて確認します。
</details>

10. scalar Tune の成功例だけでは何を確認できませんか？

<details>
<summary>回答を表示</summary>

これは model accuracy、PyTorch/DDP または GPU performance、multi-node checkpoint recovery、EKS autoscaling を証明するものではありません。API と 2 つの scalar trial 結果の収集を確認するものです。
</details>

---

[学習教材に戻る](../../../ai-ml/ray/03-ray-train-tune.md)
