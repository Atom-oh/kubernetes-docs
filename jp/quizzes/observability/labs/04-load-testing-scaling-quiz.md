# Observability ラボ パート 4 クイズ

> **最終更新**: September 13, 2026

1. k6 VU は RPS とどのような関係がありますか？
   - A) 1 つの VU は常に 1 RPS に等しい。
   - B) VU は同時実行コンテキストであり、RPS はリクエスト、レイテンシ、sleep にも依存する。
   - C) VU は Node 数に等しい。
   - D) RPS はレスポンスタイムに依存しない。

<details>
<summary>回答を表示</summary>

**回答: B) VU は同時実行コンテキストであり、RPS はリクエスト、レイテンシ、sleep にも依存する。**

異なるワークロードと待機時間では、VU が同数であってもスループットが同じとは限りません。

</details>

---

2. 失敗した k6 check は CI をどのように失敗させるべきですか？
   - A) check を呼び出すと常にコード 1 で終了する。
   - B) checks/failure-rate のしきい値を設定し、終了コードを確認する。
   - C) summary JSON ファイルが成功を証明する。
   - D) HTTP 200 レスポンスのみを数える。

<details>
<summary>回答を表示</summary>

**回答: B) checks/failure-rate のしきい値を設定し、終了コードを確認する。**

HTTP の成功とビジネス上の成功は異なります。JSON、ID、支払い状態も検証してください。

</details>

---

3. 負荷テストはどの order ID を読み取るべきですか？
   - A) 1 から 1000 までのランダムな ID。
   - B) テストで実際に作成した ID。
   - C) Customer ID。
   - D) HTTP ステータスコード。

<details>
<summary>回答を表示</summary>

**回答: B) テストで実際に作成した ID。**

ランダムな 404 がワークロードに混入しないよう、作成レスポンスの ID を使用してください。

</details>

---

4. SQS バックログに直接連動してスケールすべきものは何ですか？
   - A) 常に API producer のみ。
   - B) その queue を処理する consumer。
   - C) Alertmanager replica。
   - D) queue 名。

<details>
<summary>回答を表示</summary>

**回答: B) その queue を処理する consumer。**

KEDA は queue attribute を読み取り、HPA によるスケーリングを管理します。メッセージを消費するわけではありません。

</details>

---

5. KEDA cooldownPeriod はいつ適用されますか？
   - A) すべての 10 から 9 への replica 変更時。
   - B) 最後のアクティブな trigger の後にゼロへスケールする時。
   - C) EC2 の起動遅延時。
   - D) Log の保持期間。

<details>
<summary>回答を表示</summary>

**回答: B) 最後のアクティブな trigger の後にゼロへスケールする時。**

1..N replicas の範囲でのスケーリングについては、HPA behavior と stabilization window を確認してください。

</details>

---

6. HPA の scale-down stabilization window は何をしますか？
   - A) すべての Node を停止する。
   - B) window 内で最も高い replica 推奨値を考慮する。
   - C) 瞬間的な CPU のみを使用する。
   - D) 設定された interval ごとに Pod を 1 つ削除する。

<details>
<summary>回答を表示</summary>

**回答: B) window 内で最も高い replica 推奨値を考慮する。**

これは単純な無条件の固定遅延ではありません。policy と推奨値の履歴が重要です。

</details>

---

7. Karpenter が通常対処できる問題はどれですか？
   - A) スペルミスのある image 名。
   - B) NodePool と互換性のある capacity を必要とするスケジュール不能な Pod。
   - C) application の構文エラー。
   - D) 誤った database password。

<details>
<summary>回答を表示</summary>

**回答: B) NodePool と互換性のある capacity を必要とするスケジュール不能な Pod。**

Node を増やしても image pull や application bug は解決しません。最初に scheduling reason を確認してください。

</details>

---

8. kube_deployment_status_replicas は何を測定しますか？
   - A) 常に ready な replica。
   - B) ready replica とは異なる、Deployment replica の合計数。
   - C) Rollout を含むすべての controller replica。
   - D) Node 数。

<details>
<summary>回答を表示</summary>

**回答: B) ready replica とは異なる、Deployment replica の合計数。**

ready replica には kube_deployment_status_replicas_ready を使用してください。Rollout には専用の state/exporter が必要です。

</details>

---

9. phase metric から Running Pod をどのようにカウントすべきですか？
   - A) 値でフィルタリングせずに、すべての Running series を数える。
   - B) Running phase の 0/1 gauge を直接合計する。
   - C) Pod 名の長さを合計する。
   - D) 常に 3 を返す。

<details>
<summary>回答を表示</summary>

**回答: B) Running phase の 0/1 gauge を直接合計する。**

Running phase series は値がゼロでも存在しうるため、フィルタリングなしのカウントでは過大計上になります。gauge を合計すると、すべて Pending の Pod ではゼロが返され、telemetry が欠けている場合は存在しないままです。

</details>

---

10. 負荷実験の成功を示す証拠は何ですか？
   - A) 期待される documentation の数値からコピーした表。
   - B) 測定されたリクエスト、エラー、レイテンシ、queue、replica、Node、終了ステータス。
   - C) Job 作成の成功。
   - D) Node 数が少ないことだけ。

<details>
<summary>回答を表示</summary>

**回答: B) 測定されたリクエスト、エラー、レイテンシ、queue、replica、Node、終了ステータス。**

測定していないスループット、可用性、コスト削減を結果として提示しないでください。

</details>

---

[ガイドに戻る](../../../labs/observability/04-load-testing-scaling-lab.md)
