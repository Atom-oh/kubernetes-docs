# MLflow Model Registry クイズ

## 選択式問題

1. Registered Model とは何ですか？
   - A) GPU エンドポイント
   - B) 論理名のもとにある Model Versions のコレクション
   - C) トレーニングデータのコピー
   - D) 1 つの Run のみを許可するレコード

<details>
<summary>回答を表示</summary>

**回答: B**

たとえば、fraud-detector は複数のバージョンとエイリアスを 1 つの名前のもとにまとめます。
</details>

2. Model Version の変更に関する正しい説明はどれですか？
   - A) すべてのフィールドとソースバイトは永続的に不変である
   - B) バージョン番号を受け取り、説明とタグは変更でき、artifact の保持は別である
   - C) すべてのバージョンは 30 日後に期限切れになる
   - D) すべての新しいモデルは以前のバージョンにマージされる

<details>
<summary>回答を表示</summary>

**回答: B**

新しい結果をバージョン管理する実践と、ストレージレベルの不変性を分けて考えてください。
</details>

3. すべての Model Version にはトレーニング Run へのリンクがありますか？
   - A) 常にあり、そのリンクは削除できない
   - B) model_id はデータセットのスナップショットを自動的に保持する
   - C) いいえ。create_model_version の run_id/model_id フィールドは任意である
   - D) registry はオリジンへのリンクをサポートしない

<details>
<summary>回答を表示</summary>

**回答: C**

直接のソース URI が許可されています。完全なリネージには、明示的な記録と保持が必要です。
</details>

4. エイリアスとは何ですか？
   - A) 複数のバージョンにまたがる組み込みのトラフィック割合
   - B) 1 つのバージョンを指す変更可能な名前
   - C) 固定されたデータベースアドレス
   - D) 変更不可能なコンテンツハッシュ

<details>
<summary>回答を表示</summary>

**回答: B**

複数のエイリアスが 1 つのバージョンを参照でき、エイリアスは別のバージョンへ移動できます。
</details>

5. レガシー stage API のステータスは何ですか？
   - A) 2.9.0 以降非推奨だが、3.16.0 にはまだ存在する
   - B) すべての MLflow バージョンから削除されている
   - C) エイリアスと同等のアクセス制御ポリシー
   - D) Production のみがサポートされる

<details>
<summary>回答を表示</summary>

**回答: A**

レガシー stages は None/Staging/Production/Archived です。新しいフローはエイリアス、タグ、明示的な権限を使って設計してください。
</details>

6. モデルをログ記録する際、どのように登録できますか？
   - A) タグのみを設定する
   - B) flavor の log_model に registered_model_name を渡す
   - C) エイリアスを削除する
   - D) ファイル名を champion に変更する

<details>
<summary>回答を表示</summary>

**回答: B**

ログ記録後に register_model を使って登録する方法もあります。登録自体はエイリアスを移動しません。
</details>

7. champion への昇格を制御するものは何ですか？
   - A) MLflow は最大のバージョンを自動的に承認する
   - B) review_state タグだけで権限の分離を完了できる
   - C) 評価・承認の証拠、および実行者の認証・認可
   - D) すべてのトレーナーが常にエイリアスを変更する

<details>
<summary>回答を表示</summary>

**回答: C**

タグ文字列は、承認ワークフローにもアクセス制御にも代わりません。
</details>

8. エイリアスが変更された直後、すでにロードされているモデルはどうなりますか？
   - A) 常に即座に置き換えられる
   - B) 自動的に再トレーニングされる
   - C) シャドートラフィックが自動的に現れる
   - D) リロード、Deployment、またはキャッシュポリシーによって変更されるまで、提供を続ける場合がある

<details>
<summary>回答を表示</summary>

**回答: D**

新たな解決と、既存のロード済みインスタンスのライフサイクルは別のものです。
</details>

## 短答式問題

9. READY だけで推論の互換性とモデル品質が証明されますか？

<details>
<summary>回答を表示</summary>

いいえ。これは登録ステータスであり、メタデータ fixture は READY になる可能性があります。実際の flavor、weights、依存関係のロード、品質をそれぞれ検証してください。
</details>

10. なぜ registry は常に正確なコードとデータのリネージを再構築できないのですか？

<details>
<summary>回答を表示</summary>

Run とモデルのリンクは任意であり、ソースファイル、Runs、artifact は変更されたり失われたりする可能性があります。提供するバージョン、ハッシュ、commit、データセットスナップショット、依存関係、承認を保持してください。
</details>

---

[学習教材に戻る](../../../ai-ml/mlflow/02-model-registry.md)
