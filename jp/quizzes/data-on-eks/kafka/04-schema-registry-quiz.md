# Schema Registry クイズ

スキーマ契約、エンコーディング、互換性、復旧、およびデプロイ例について確認しましょう。

## 1. Kafka の基本的なレコード保存機能がスキーマ契約を強制しないのはなぜですか？

<details>
<summary>解答を表示</summary>

キーと値はバイト列として保存されます。構造やビジネスルールの検証は、シリアライザー、アプリケーション、検証経路に依存します。フィールドを追加しても、必ずコンシューマーが壊れるとは限りません。

</details>

## 2. レジストリを使わずに、実行時より前に JSON をバージョン管理して検証できますか？

<details>
<summary>解答を表示</summary>

できます。JSON Schema、CI チェック、バージョン管理された仕様で契約を定義できます。レジストリはガバナンスと配布を一元化しますが、バイナリーエンコーディングを使うかどうかは別の選択です。

</details>

## 3. 一般的な Confluent の schema ID ペイロード形式では、先頭の 5 バイトは何ですか？

<details>
<summary>解答を表示</summary>

マジックバイト 1 バイトと schema ID 4 バイトがあり、その後に値が続きます。Protobuf ではメッセージインデックスも含まれます。これは、すべてのレジストリやエンコーディングに共通する規則ではありません。

</details>

## 4. Karapace 6.2.4 がサポートする主なスキーマ形式は何ですか？

<details>
<summary>解答を表示</summary>

Avro、JSON Schema、Protobuf です。JSON Schema の draft やキーワードの検証と、互換性分析のサポートはそれぞれ個別に確認してください。

</details>

## 5. Apache-2.0 と Confluent コンポーネントのライセンスを確認するとき、何に注意すべきですか？

<details>
<summary>解答を表示</summary>

Apache-2.0 には、必要な告知を保持するなどの条件があります。Confluent のサーバーとクライアント／Avro モジュールでは、ライセンスが異なる場合があります。規模からライセンス条件を推測せず、実際に使用するコンポーネントとサポート契約を確認してください。

</details>

## 6. Avro のスキーマ進化を可能にする仕組みは何ですか？フィールドのデフォルト値は何に使いますか？

<details>
<summary>解答を表示</summary>

writer schema と reader schema の解決です。writer schema にフィールドがない場合、reader はそのフィールドのデフォルト値を使います。これは、writer が任意の必須フィールドを省略してよいという意味ではありません。

</details>

## 7. 削除した Protobuf のフィールド番号を、別の意味に再利用できますか？

<details>
<summary>解答を表示</summary>

再利用しないでください。古いデータやクライアントが、その番号を以前の意味として解釈する可能性があります。必要に応じて削除した番号や名前を予約し、wire type とアプリケーション上の意味も確認してください。

</details>

## 8. 後方互換性のあるスキーマ変更をロールアウトするとき、通常どの順序にしますか？

<details>
<summary>解答を表示</summary>

先にコンシューマーを更新します。新しい reader が、以前の writer によるデータを読める必要があります。ビジネス上の動作もテストしてください。また、互換性は topic 固有ではなく subject ごとに設定される点にも注意してください。

</details>

## 9. FORWARD 互換性では、どちら向きの読み取りを確認しますか？

<details>
<summary>解答を表示</summary>

以前の reader が、新しい writer によるデータを読めるかを確認します。通常は、先に producer を更新できます。ただし、これだけでは新しい reader が古いデータを再生できることは検証できません。

</details>

## 10. Avro フィールドを削除すると、必ず前方互換性が壊れますか？

<details>
<summary>解答を表示</summary>

いいえ。古い reader にデフォルト値があれば、新しい writer のデータにないフィールドにその値を補えます。デフォルト値がなければ失敗します。これは、新しい reader がそのフィールドを要求しなくなる後方互換性の方向とは区別してください。

</details>

## 11. キャッシュが空のコンシューマーとレジストリ移行について、何を確認する必要がありますか？

<details>
<summary>解答を表示</summary>

保持されているレコード内の ID が、同じ writer schema を指す必要があります。ID の対応関係、参照、subject strategy、エンコーディング、認証、クライアントのバージョンを確認してください。URL を変更しただけでは、同じスキーマを参照できる証拠にはなりません。

</details>

## 12. BACKWARD と FORWARD の両方を要求するモードは何ですか？その TRANSITIVE 版では何が追加されますか？

<details>
<summary>解答を表示</summary>

`FULL` です。`FULL_TRANSITIVE` は、両方向について過去のすべてのバージョンとの互換性を確認します。通常の `FULL` が比較するのは直前のバージョンです。どちらもビジネス上の意味やアプリケーションの動作までは保証しません。

</details>

## 13. Apicurio KafkaSQL は、完全なスナップショットファイルを snapshots topic に保存しますか？

<details>
<summary>解答を表示</summary>

いいえ。保存するのはファイルパスです。ファイルの永続性、共有、復旧は別途設計する必要があります。このラボでは、定期スナップショットを無効にし、再起動後に再生できるようジャーナル全体を保持します。

</details>

## 14. KafkaSQL 3.3.3 の既定構成で、journal／snapshots topic のチェックを満たす設定は何ですか？

<details>
<summary>解答を表示</summary>

`cleanup.policy=delete`、`retention.ms=-1`、`retention.bytes=-1` です。保持期間を無制限にする場合は、増加量を監視してください。一般的な `_schemas` の compaction 設定や、イベントの短い保持期間をそのまま流用しないでください。

</details>

## 15. Avro の producer と consumer では、どのプロパティが異なりますか？

<details>
<summary>解答を表示</summary>

producer は `value.serializer=io.confluent.kafka.serializers.KafkaAvroSerializer` を使い、consumer は `value.deserializer=io.confluent.kafka.serializers.KafkaAvroDeserializer` を使います。どちらにもレジストリ URL、ブローカーとの TLS／SASL 設定、ライブラリ依存関係が必要です。

</details>

## 16. timestamp-millis フィールドとデフォルト値付き discountCode フィールドの Avro 定義を書いてください。

<details>
<summary>解答を表示</summary>

```json
[
  {"name":"createdAt","type":{"type":"long","logicalType":"timestamp-millis"}},
  {"name":"discountCode","type":["null","string"],"default":null}
]
```

これはレコードの `fields` 配列に含める定義です。logical type は `type` オブジェクト内に記述します。追加したフィールドの `null` デフォルト値は、新しい reader が古いデータを読むときに使われます。

</details>

## 17. この章の order.avsc を orders-value subject に登録するにはどうしますか？

<details>
<summary>解答を表示</summary>

章にある `register.sh` の例に従います。JSON を解析し、schema 文字列と `schemaType: AVRO` を含むリクエストファイルを作成します。HTTP エラーを確認しながら、`/apis/ccompat/v7/subjects/orders-value/versions` に POST します。先に互換性を設定し、その後で最新バージョンを取得してください。既定の TopicNameStrategy は、topic 名が `orders` であることを前提とします。

</details>

## 18. この章の Apicurio デプロイメントを、先行する Strimzi 環境にどう接続しますか？

<details>
<summary>解答を表示</summary>

image 3.3.3、`APICURIO_STORAGE_KIND=kafkasql`、`my-cluster-kafka-bootstrap.kafka.svc:9093`、SASL_SSL／SCRAM-SHA-512、CA truststore、Secret から読み込む JAAS 設定、明示的なホスト名検証を使います。ストレージ用 topic を 3 つ、ユーザー ACL とともに事前作成し、自動 topic 作成を無効にします。management port 9000 のヘルスチェックと、HTTP API 用 port 8080 を区別してください。HTTP API の認証は Kafka の認証とは別です。このラボのサービスをパブリックに公開してはいけません。

</details>

---

[学習資料に戻る](../../../data-on-eks/kafka/04-schema-registry.md) | [次のクイズ](./05-kafka-connect-mirrormaker-quiz.md)
