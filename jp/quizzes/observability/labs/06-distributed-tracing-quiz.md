# Observability Lab Part 6 クイズ

> **最終更新**: September 13, 2026

1. トレース全体の duration と個々の Span の duration はどのように区別されますか？
   - A) 常に同一です。
   - B) trace:duration と span:duration。
   - C) span.duration は常に intrinsic です。
   - D) ログ行を数えます。

<details>
<summary>回答を表示</summary>

**回答: B) trace:duration と span:duration。**

明示的な intrinsic にはコロンを使用し、span. は属性スコープです。

</details>

---

2. 現在の HTTP response status 属性を使用するクエリはどれですか？
   - A) { order by status desc }
   - B) { span.http.response.status_code >= 500 }
   - C) { duration > p99 }
   - D) { select 500 }

<details>
<summary>回答を表示</summary>

**回答: B) { span.http.response.status_code >= 500 }**

SDK が依然として http.status_code を出力する場合は、そのデータを確認し、適切な legacy query を使用してください。

</details>

---

3. A >> B は何を選択しますか？
   - A) A より前のすべてのログ。
   - B) A Span から派生する B Span。
   - C) A と B の平均。
   - D) B は必ず A と同じ Span。

<details>
<summary>回答を表示</summary>

**回答: B) A Span から派生する B Span。**

派生する DB 処理を見つけるには、左に Service selector、右に DB selector を配置します。

</details>

---

4. 古い例にある SQL-style の order by/limit は、どのように置き換えるべきですか？
   - A) 変更せずに実行する。
   - B) 有効な TraceQL と Grafana の検索ソート/limit 設定。
   - C) Prometheus に送信する。
   - D) クエリに DB password を追加する。

<details>
<summary>回答を表示</summary>

**回答: B) 有効な TraceQL と Grafana の検索ソート/limit 設定。**

実際の Tempo3.0.3 parser は、これらの古い sort/order-by/limit の例を拒否します。

</details>

---

5. Service graph には何が必要ですか？
   - A) Tempo のインストールのみ。
   - B) 接続された Span、service-graphs processor、metrics backend、および datasource linking。
   - C) trace ID をログ label として保存することのみ。
   - D) 赤いノードを手動で描画すること。

<details>
<summary>回答を表示</summary>

**回答: B) 接続された Span、service-graphs processor、metrics backend、および datasource linking。**

トレースの取り込みと graph metrics の配信は、個別に検証してください。

</details>

---

6. 1.8 秒の DB Span 単体で何を確立できますか？
   - A) index が確実に不足していること。
   - B) 観測された operation duration。原因には追加の証拠が必要です。
   - C) network が正常であること。
   - D) すべての親 duration と合計しても安全であること。

<details>
<summary>回答を表示</summary>

**回答: B) 観測された operation duration。原因には追加の証拠が必要です。**

lock、pool、network、query plan を確認し、重複する Span の二重計上を避けてください。

</details>

---

7. Grafana provisioning で derived-field link expression はどのように記述すべきですか？
   - A) envsubst ですべての dollar variable を削除する。
   - B) $${__value.raw} で provisioning substitution をエスケープする。
   - C) すべての stream label に trace ID を追加する。
   - D) LogQL SQL clause として time bound を追加する。

<details>
<summary>回答を表示</summary>

**回答: B) $${__value.raw} で provisioning substitution をエスケープする。**

実際の trace-ID field name と datasource UID も一致している必要があります。

</details>

---

8. exemplar はどのような request につながりますか？
   - A) 必ず正確な p99 境界の request。
   - B) その trace が引き続き保持されている必要がある代表的な observation。
   - C) すべての request のコピー。
   - D) trace sampling にかかわらず常に取得可能。

<details>
<summary>回答を表示</summary>

**回答: B) その trace が引き続き保持されている必要がある代表的な observation。**

sampling と retention により、exemplar ID と trace availability が異なる場合があります。

</details>

---

9. 最初の lab day における [30d] クエリは何を証明しますか？
   - A) 30 日間の SLO を満たしたこと。
   - B) 利用可能な observation を集計するものであり、30 日間の履歴を作成するものではないこと。
   - C) 100% の availability。
   - D) 無制限の error budget。

<details>
<summary>回答を表示</summary>

**回答: B) 利用可能な observation を集計するものであり、30 日間の履歴を作成するものではないこと。**

実際の期間、denominator、および欠損/トラフィックなしの interval を記録してください。

</details>

---

10. 現在の DB attributes とデータ処理の正しい組み合わせはどれですか？
   - A) db.statement は永続的に唯一の standard です。
   - B) 実際の SDK に対して db.system.name/db.query.text を確認し、query を sanitize する。
   - C) すべての password を記録する。
   - D) query の名前変更により、すべての古いデータが変換される。

<details>
<summary>回答を表示</summary>

**回答: B) 実際の SDK に対して db.system.name/db.query.text を確認し、query を sanitize する。**

legacy attributes はデータ内に残る場合があります。migration と sensitive-data handling は別のものです。

</details>

---

[ガイドに戻る](../../../labs/observability/06-distributed-tracing-lab.md)
