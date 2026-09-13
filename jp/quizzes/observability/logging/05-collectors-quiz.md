# ログコレクター比較クイズ

> **最終更新**: September 13, 2026

1. コレクターのリソース要件はどのように比較すべきですか？

   - A) 実装言語からメモリ使用量の順位を固定的に想定する
   - B) 同一のレコード、処理、宛先、障害時設定でベンチマークする
   - C) すべての Go 製コレクターを同一のものとして扱う
   - D) 公開されている 1 秒あたりのイベント数という単一の数値を使う

<details>
<summary>回答を表示</summary>

**回答: B) 同一のレコード、処理、宛先、障害時設定でベンチマークする**

バッファー上限、メタデータキャッシュ、バッチ処理、リトライ、並行度はリソース使用量に影響します。言語や圧縮形式だけでスループットが保証されるわけではありません。

</details>

---

2. Pod と namespace のメタデータを付与する Fluent Bit の filter はどれですか？

   - A) modify
   - B) parser
   - C) kubernetes
   - D) record_modifier のみ

<details>
<summary>回答を表示</summary>

**回答: C) kubernetes**

kubernetes filter には正しいタグと、認可されたメタデータアクセスが必要です。Use_Kubelet を有効にする場合は、kubelet への接続性と権限を個別に確認する必要があります。

</details>

---

3. Promtail に対する現時点で正しい対応はどれですか？

   - A) 移行する。2026 年 3 月 2 日に EOL に到達した
   - B) 新規の Loki 環境ではすべて Promtail を選択する
   - C) 既存のインストールは今後もアップデートを受け取ると想定する
   - D) この廃止には lambda-promtail も自動的に含まれる

<details>
<summary>回答を表示</summary>

**回答: A) 移行する。2026 年 3 月 2 日に EOL に到達した**

公式のライフサイクル告知は Alloy またはサポートされている別のクライアントへの移行を促しており、独立したクライアントである lambda-promtail はその告知の対象外であると明示しています。

</details>

---

4. Grafana Alloy はどの構文を使用しますか？

   - A) 変換なしで使える任意の Kubernetes YAML
   - B) Alloy 設定構文（旧称 River）
   - C) すべての Terraform provider が使える Terraform HCL
   - D) INI のみ

<details>
<summary>回答を表示</summary>

**回答: B) Alloy 設定構文（旧称 River）**

構文は HCL 風ですが、Alloy のコンポーネントグラフは Terraform ファイルと相互に置き換えられるものではありません。選択した Alloy バイナリで検証してください。

</details>

---

5. 一般的な Collector のパイプライン順序はどれですか？

   - A) Exporters → Receivers → Processors
   - B) Processors → Exporters → Receivers
   - C) Receivers → Processors → Exporters
   - D) すべてのコンポーネントが任意の順序で実行される

<details>
<summary>回答を表示</summary>

**回答: C) Receivers → Processors → Exporters**

Connectors はパイプライン同士を接続できます。現在の Loki 向け経路は OTLP HTTP を使用し、削除された loki exporter は Contrib0.160.0 には存在しません。

</details>

---

6. 例に示された Lua による変換が保証するものは何ですか？

   - A) 任意のテキストからあらゆる機密情報を除去すること
   - B) ノード上の元のログファイルを削除すること
   - C) Exactly-once 配信
   - D) 選択した構造化キーのマスキングと、生の重複データの削除

<details>
<summary>回答を表示</summary>

**回答: D) 選択した構造化キーのマスキングと、生の重複データの削除**

これは汎用的な PII 検出器でも、fail-closed な境界でもありません。プレーンテキストや自由記述のメッセージ値には、依然として機密データが含まれる可能性があります。

</details>

---

7. 従来の Promtail と Alloy のドロップ用ステージ名を正しく区別しているのはどれですか？

   - A) どちらも Promtail の YAML キーとして stage.drop を使う
   - B) Promtail の YAML は drop、Alloy は stage.drop
   - C) Promtail は filter.exclude、Alloy は ignore
   - D) どちらもレコードのドロップをサポートしていない

<details>
<summary>回答を表示</summary>

**回答: B) Promtail の YAML は drop、Alloy は stage.drop**

parser、template、labels、output の各ステージにも、順序や保持されるフィールドに関する影響があります。ステージの一覧を、どこでも通用する単一の処理チェーンとして扱わないでください。

</details>

---

8. 2 つの AWS 宛先に対応する Fluent Bit のネイティブ output plugin 名はどれですか？

   - A) cloudwatch_logs と opensearch
   - B) cloudwatch と elastic のみ
   - C) stage.cloudwatch と stage.opensearch
   - D) Loki の tenant_id が両方の AWS 宛先を作成する

<details>
<summary>回答を表示</summary>

**回答: A) cloudwatch_logs と opensearch**

plugin が利用できることは IAM 権限が付与されることを意味しません。実際の ServiceAccount の ID、リージョン、エンドポイント、TLS、事前作成されたリソースの所有関係を一致させてください。

</details>

---

9. メモリ逼迫時に memory_limiter は何を行いますか？

   - A) プロセスが OOM にならないことを保証する
   - B) ノードのメモリを追加で作り出す
   - C) リトライ可能なエラーでデータを拒否し、ガベージコレクションを要求できる
   - D) すべてのソースレコードを自動的に永続化する

<details>
<summary>回答を表示</summary>

**回答: C) リトライ可能なエラーでデータを拒否し、ガベージコレクションを要求できる**

receiver のリトライ動作、上限、キューが重要になります。filelog のリトライ期間には上限があり、期限切れになると失敗したバッチは破棄されます。

</details>

---

10. Promtail から Alloy への変換が成功した後に必ず行うべきことは何ですか？

   - A) ただちに配信内容とメトリクスが同一であると宣言する
   - B) すべての診断警告を無視する
   - C) 同じログに対して両方のエージェントを無期限に実行し続ける
   - D) パース結果、状態、所有関係、認証、自己メトリクス、実際のバックエンド上のレコードを検証する

<details>
<summary>回答を表示</summary>

**回答: D) パース結果、状態、所有関係、認証、自己メトリクス、実際のバックエンド上のレコードを検証する**

コンバーターはグローバルなレート制限をパイプラインごとの制限に変更する場合があり、ホストのマウントや Kubernetes の権限は検証しません。重複収集を避けるため、ファイルと API のどちらで所有するかを選択してください。

</details>

---

[ガイドに戻る](../../../observability/logging/05-collectors.md)
