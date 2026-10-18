# SageMaker AI と MLflow の実行クイズ

## 選択式問題

1. 新しいマネージド MLflow デプロイで使うリソースはどれですか？
   - A) 従来の Tracking Server のみ
   - B) SageMaker MLflow App
   - C) Public EKS LoadBalancer
   - D) ローカルの SQLite file のみ

<details>
<summary>回答を表示</summary>

**回答: B**

マネージド経路では、現行の SageMaker MLflow App API を使用します。
</details>

2. 完全な実行の前に必要なことは何ですか？
   - A) Smoke run を完了し、raw PII の logging をスキャンする
   - B) Project membership を削除する
   - C) 直ちに最大 step 数で実行する
   - D) Teardown を無効にする

<details>
<summary>回答を表示</summary>

**回答: A**

まず smoke の完了、logging の安全性、集計結果、adapter のインベントリを確認します。
</details>

3. EKS Job の失敗と deadline に関する契約はどれですか？
   - A) Retry は無制限で deadline はない
   - B) `backoffLimit: 0` と `activeDeadlineSeconds: 10800`
   - C) 10回 retry し、1時間で終了する
   - D) 永続的な Deployment

<details>
<summary>回答を表示</summary>

**回答: B**

これらは retry と Job deadline の設定です。Controller や node の障害によって回収が遅れる場合があり、3時間以内にすべてのリソースが消える保証や総コストの上限にはなりません。
</details>

4. どのような場合に cleanup の検証を失敗とすべきですか？
   - A) リソースが残っていない
   - B) リソースが残っている、またはエラーのため状態を確認できない
   - C) Smoke test が成功した
   - D) Dataset hash が一致する

<details>
<summary>回答を表示</summary>

**回答: B**

照会に失敗している場合、残存数がゼロであるだけでは不十分です。不明な状態はそのまま記録し、所有権の証拠がない古いインベントリから、名前だけを根拠に削除しないでください。
</details>

5. 9月1日に実際に実行されたのは何ですか？
   - A) 完全な SageMaker Training Job
   - B) 完全な EKS GPU Job
   - C) Provisioning と cleanup の経路
   - D) 調整済みモデルの評価

<details>
<summary>回答を表示</summary>

**回答: C**

どちらの GPU Job も送信前に停止しました。
</details>

6. 2026年9月12日時点で GPU 実行がブロックされているのはなぜですか？
   - A) 固定された PyTorch 2.8 DLC の patch support が8月6日に終了した
   - B) Source bundling に料金がかかる
   - C) すべての MLflow App が削除された
   - D) ローカルの unit test に GPU が必要である

<details>
<summary>回答を表示</summary>

**回答: A**

サポート対象の DLC、torch、依存関係の組み合わせ、GPU smoke run を検証してください。日付チェックだけを削除しても、upgrade したことにはなりません。
</details>

7. `--execute` を指定しない場合、SageMaker launcher は何をしますか？
   - A) 完全な Job を直ちに送信する
   - B) Request JSON だけを書き出す
   - C) 既存の Job を削除する
   - D) コスト見積もりを保証する

<details>
<summary>回答を表示</summary>

**回答: B**

デフォルトでは request preview を行います。実際に送信するには、runtime support check と別途のレビューが必要です。
</details>

8. EKS MLflow の metric/parameter JSON を保存するだけで十分ですか？
   - A) はい。Adapter weight も自動的に含まれる
   - B) 最終 adapter と集約 artifact をダウンロードし、hash を検証する
   - C) `emptyDir` は cluster の削除後も残る
   - D) Log の末尾から model を再構築できる

<details>
<summary>回答を表示</summary>

**回答: B**

Metadata の export はファイルの保持とは異なります。Export に失敗した後も cluster を保持する場合は、コストに注意し、その後 cleanup する必要があります。
</details>

---

[学習資料に戻る](../../../ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md)
