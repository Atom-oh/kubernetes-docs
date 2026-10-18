# Grafana Tempo クイズ

> **最終更新日**: 2026年9月13日

基準バージョン: Tempo 3.0.3、Helm チャート 3.6.0。

---

1. Tempo のストレージと検索を最も正確に説明しているものはどれですか？

   - A) すべての属性を Elasticsearch にインデックス化する必要がある
   - B) オブジェクトストレージ上の Parquet ブロックは TraceID/TraceQL に対応するが、保存や検索には引き続きコストがかかる
   - C) ID がわかれば、破棄された span をすべて復元できる
   - D) Tempo はトレースを永久に保持する

<details>
<summary>回答を表示</summary>

**回答: B) オブジェクトストレージ上の Parquet ブロックは TraceID/TraceQL に対応するが、保存や検索には引き続きコストがかかる**

専用カラム、メタデータ、キャッシュがあっても、インデックス化や検索のコストがなくなるわけではありません。正常に取り込まれ、保持されているデータだけを利用できます。

</details>

---

2. Tempo 3 の分散書き込み経路で、Kafka にコミットする前にトレースデータを受信して検証するコンポーネントはどれですか？

   - A) `block-builder`
   - B) `querier`
   - C) Distributor
   - D) `backend worker`

<details>
<summary>回答を表示</summary>

**回答: C) Distributor**

Distributor が Kafka に書き込みます。Live-store、block-builder、任意の metrics-generator は、それぞれ別に Kafka からデータを読み取ります。これは Tempo 2 の ingester 経路とは異なります。

</details>

---

3. エラーステータスの span を選択する TraceQL クエリはどれですか？

   - A) `{ duration > 1s }`
   - B) `{ status = error }`
   - C) `{ status = ok }`
   - D) `{ span.http.response.status_code = 200 }`

<details>
<summary>回答を表示</summary>

**回答: B) `{ status = error }`**

span のステータスが error であることは、レイテンシーのしきい値や任意の HTTP レスポンス条件とは別の判定です。

</details>

---

4. この EKS/S3 の例では、どの ID 認証設定を使用していますか？

   - A) Helm の values に記述した固定アクセスキー
   - B) すべてのワークロードで共有されるノードロール
   - C) OIDC の sub/aud を正確に指定し、S3 権限を必要な範囲に限定して `monitoring:tempo` に関連付けた IRSA
   - D) Pod に関連付けられていない無関係な ServiceAccount

<details>
<summary>回答を表示</summary>

**回答: C) OIDC の sub/aud を正確に指定し、S3 権限を必要な範囲に限定して `monitoring:tempo` に関連付けた IRSA**

ロールのアノテーションと、すべての Tempo Pod が使用する ServiceAccount を一致させる必要があります。他のワークロード ID 方式を使う場合は、それぞれについて固定したコンテナイメージとの互換性を確認してください。

</details>

---

5. 図に示された metrics-generator のプロセッサーでは、トレースから生成されないものはどれですか？

   - A) サービスグラフのメトリクス
   - B) span のメトリクス
   - C) 任意のアプリケーションログのメトリクス
   - D) span から算出するレート、エラー、継続時間のメトリクス

<details>
<summary>回答を表示</summary>

**回答: C) 任意のアプリケーションログのメトリクス**

span のメトリクスとサービスグラフを生成するには、プロセッサーを明示的に有効化し、remote write を設定する必要があります。これらの機能は、任意のログをメトリクスに変換するものではありません。

</details>

---

6. Tempo 3 のデータ耐久性について、正しい記述はどれですか？

   - A) Tempo のレプリカが3つあれば、常にデータ損失ゼロが保証される
   - B) マイクロサービスモードでは Kafka を使う。レプリケーション、ISR、保持期間、復旧は個別に設計する必要がある
   - C) モノリシックモードでは常に Kafka が必要である
   - D) すべての StatefulSet に永続 PVC が自動的に作成される

<details>
<summary>回答を表示</summary>

**回答: B) マイクロサービスモードでは Kafka を使う。レプリケーション、ISR、保持期間、復旧は個別に設計する必要がある**

チャートでは live-store と block-builder のデータ保存に `emptyDir` を使います。Tempo のレプリカ数だけでは Kafka の耐久性は保証されません。モノリシックモードでは Kafka は不要です。

</details>

---

7. Grafana の相関リンクの向きとして正しいものはどれですか？

   - A) namespace が同じであれば自動的に相関リンクが作成される
   - B) Tempo の `tracesToLogsV2` はトレースからログへ、Loki の `derivedFields` はログからトレースへのリンクを提供する
   - C) 両方のシステムで同じ S3 バケットを共有する必要がある
   - D) `derivedFields` によってアプリケーションが TraceID を生成する

<details>
<summary>回答を表示</summary>

**回答: B) Tempo の `tracesToLogsV2` はトレースからログへ、Loki の `derivedFields` はログからトレースへのリンクを提供する**

識別子、データソース UID、ラベル、検索対象の期間を、実際のデータに合わせる必要があります。リンクを設定しても、欠落したテレメトリは復元できません。

</details>

---

8. Tempo 3 のバックグラウンド圧縮とデータ保持を担当するコンポーネントはどれですか？

   - A) Grafana のブラウザータブ
   - B) OTLP クライアント
   - C) バックエンドスケジューラーとバックエンドワーカー
   - D) 古い設定をそのままコピーした compactor 構成

<details>
<summary>回答を表示</summary>

**回答: C) バックエンドスケジューラーとバックエンドワーカー**

これらのコンポーネントは従来の compactor 構成に代わるものです。データ保持処理は非同期です。別途設定した包括的な S3 有効期限ルールは、バックエンドの処理と競合する可能性があります。

</details>

---

9. `{ resource.service.name = "A" } >> { resource.service.name = "B" }` は何を選択しますか？

   - A) 異なるトレースに属する任意の2つの span
   - B) 条件に一致した A の span の子孫にあたる、条件に一致した B の span
   - C) A の親 span だけを選び、B は含めない
   - D) B の直接の子 span だけを選ぶ

<details>
<summary>回答を表示</summary>

**回答: B) 条件に一致した A の span の子孫にあたる、条件に一致した B の span**

検索結果は右辺の条件に一致した span です。直接の子だけを対象にするには `>` を使います。同一の親を持つ span の検索や、同じトレースに属するかどうかの判定とは意味が異なります。

</details>

---

10. クエリが遅く、直近の検索結果が空に見えるとき、最初に行う最も安全な対応はどれですか？

   - A) Tempo 2 の `ingester.max_block_duration: 30m` をコピーする
   - B) 遅延対策と直近クエリ保護をすべて無効にする
   - C) 設定を調整する前に、検索期間、実際の受信データ、遅延、スキャン量、制限値を確認する
   - D) テレメトリ欠落とトラフィックゼロを、必ず正常な値として扱う

<details>
<summary>回答を表示</summary>

**回答: C) 設定を調整する前に、検索期間、実際の受信データ、遅延、スキャン量、制限値を確認する**

Tempo 3 ではコンポーネント構成と既定値が異なります。検索結果が空であること、トラフィックがゼロであること、処理が失敗したことは、それぞれ別の状態です。設定ファイルが正しくレンダリングされたとしても、本番システムが動作している証拠にはなりません。

</details>

---

[Tempo ガイドを確認する](../../../observability/tracing/01-tempo.md)。
