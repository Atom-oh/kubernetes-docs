# Observability ラボ パート 6 クイズ

> **最終更新**: 2026年9月13日

1. トレース全体と個々の Span の duration はどのように区別されますか？
   - A) 常に同一です。
   - B) trace:duration と span:duration。
   - C) span.duration は常に intrinsic です。
   - D) ログ行を数えます。

<details>
<summary>回答を表示</summary>

**回答: B) trace:duration と span:duration。**

明示的な intrinsic にはコロンを使い、span. は属性のスコープを表します。

</details>

---

2. 現行の HTTP response status 属性を使うクエリはどれですか？
   - A) { order by status desc }
   - B) { span.http.response.status_code >= 500 }
   - C) { duration > p99 }
   - D) { select 500 }

<details>
<summary>回答を表示</summary>

**回答: B) { span.http.response.status_code >= 500 }**

SDK が引き続き http.status_code を出力する場合は、実際のデータを確認し、適切な旧形式のクエリを使用してください。

</details>

---

3. A >> B は何を選択しますか？
   - A) A より前のすべてのログ。
   - B) A Span の子孫にあたる B Span。
   - C) A と B の平均。
   - D) B は必ず A と同じ Span。

<details>
<summary>回答を表示</summary>

**回答: B) A Span から派生する B Span。**

子孫にあたる DB 処理を見つけるには、左側にサービスの selector、右側に DB の selector を配置します。

</details>

---

4. 古い例にある SQL 形式の order by/limit は、どのように置き換えるべきですか？
   - A) 変更せずに実行する。
   - B) 有効な TraceQL と Grafana の検索におけるソート/limit 設定。
   - C) Prometheus に送信する。
   - D) クエリに DB password を追加する。

<details>
<summary>回答を表示</summary>

**回答: B) 有効な TraceQL と Grafana の検索ソート/limit 設定。**

Tempo 3.0.3 の parser は、古い sort/order-by/limit の例を実際に拒否します。

</details>

---

5. サービスグラフには何が必要ですか？
   - A) Tempo のインストールのみ。
   - B) 接続された Span、service-graphs processor、メトリクスバックエンド、およびデータソースのリンク。
   - C) trace ID をログ label として保存することのみ。
   - D) 赤いノードを手動で描画すること。

<details>
<summary>回答を表示</summary>

**回答: B) 接続された Span、service-graphs processor、metrics backend、および datasource linking。**

トレースの取り込みとグラフ用メトリクスの配信は、個別に検証してください。

</details>

---

6. 1.8 秒の DB Span だけで何が分かりますか？
   - A) index が確実に不足していること。
   - B) 観測された処理時間。原因を特定するには追加の証拠が必要です。
   - C) network が正常であること。
   - D) すべての親 duration と合計しても安全であること。

<details>
<summary>回答を表示</summary>

**回答: B) 観測された operation duration。原因には追加の証拠が必要です。**

ロック、接続プール、ネットワーク、クエリプランを確認し、重なり合う Span を二重計上しないでください。

</details>

---

7. Grafana の provisioning で derived-field のリンク式はどのように記述すべきですか？
   - A) envsubst ですべての dollar variable を削除する。
   - B) $${__value.raw} を使って provisioning による置換をエスケープする。
   - C) すべての stream label に trace ID を追加する。
   - D) LogQL SQL clause として time bound を追加する。

<details>
<summary>回答を表示</summary>

**回答: B) $${__value.raw} で provisioning substitution をエスケープする。**

実際の trace ID のフィールド名とデータソース UID も一致している必要があります。

</details>

---

8. exemplar からどのようなリクエストにたどり着けますか？
   - A) 必ず正確な p99 境界の request。
   - B) 代表的な観測データであり、対応する trace が保持されている必要がある。
   - C) すべての request のコピー。
   - D) trace sampling にかかわらず常に取得可能。

<details>
<summary>回答を表示</summary>

**回答: B) その trace が引き続き保持されている必要がある代表的な observation。**

サンプリングや保持期間によって、exemplar ID と trace の可用性が異なる場合があります。

</details>

---

9. ラボ初日に [30d] クエリを実行すると何が分かりますか？
   - A) 30 日間の SLO を満たしたこと。
   - B) 利用可能な観測データを集計するものであり、30 日分の履歴を作り出すわけではない。
   - C) 100% の availability。
   - D) 無制限の error budget。

<details>
<summary>回答を表示</summary>

**回答: B) 利用可能な observation を集計するものであり、30 日間の履歴を作成するものではないこと。**

実際に対象となった期間、分母、欠損期間やトラフィックのない期間を記録してください。

</details>

---

10. 現行の DB 属性とデータの取り扱いについて、正しい組み合わせはどれですか？
   - A) db.statement は永続的に唯一の standard です。
   - B) 実際の SDK が出力する db.system.name/db.query.text を確認し、クエリをサニタイズする。
   - C) すべての password を記録する。
   - D) query の名前変更により、すべての古いデータが変換される。

<details>
<summary>回答を表示</summary>

**回答: B) 実際の SDK に対して db.system.name/db.query.text を確認し、query を sanitize する。**

旧形式の属性がデータ内に残っている場合があります。移行と機密データの取り扱いは別々に検討してください。

</details>

---

[ガイドに戻る](../../../labs/observability/06-distributed-tracing-lab.md)
