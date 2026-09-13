# Observability Lab 03 クイズ

<span id="observability-lab-part-3-msa-deployment-and-canary-quiz"></span>

> **最終更新**: September 13, 2026

1. order/outbox のトランザクション境界とは何ですか？
   - A) order をコミットしてから、失敗したメッセージングを無視する。
   - B) 1 つの DB トランザクションで両方をコミットするか、ロールバックする。
   - C) SNS と DB は自動的にアトミックになる。
   - D) リクエストごとに DB を初期化する。

<details>
<summary>回答を表示</summary>

**回答: B) 1 つの DB トランザクションで両方をコミットするか、ロールバックする。**

DB のロールバックと、未公開の outbox レコードが保持されることを検証します。

</details>

---

2. payment ワークロードを所有するのは誰ですか？
   - A) Deployment と Rollout が同時に所有する。
   - B) 単一の Rollout。
   - C) KEDA と Rollout がレプリカをめぐって競合する。
   - D) Grafana。

<details>
<summary>回答を表示</summary>

**回答: B) 単一の Rollout。**

コントローラーの所有権と Git の望ましい状態を明確に保ちます。

</details>

---

3. notification キューと analytics キューを分ける理由は何ですか？
   - A) 1 つのキューでの競合は fanout であるため。
   - B) 各コンシューマーが同じイベントを独立して受け取れるようにするため。
   - C) SQS は 1 つのキューしかサポートしないため。
   - D) すべての重複を排除するため。

<details>
<summary>回答を表示</summary>

**回答: B) 各コンシューマーが同じイベントを独立して受け取れるようにするため。**

SNS fanout と各コンシューマーの event-ID の重複排除は、別々の責務です。

</details>

---

4. 同一の synthetic payment が繰り返された場合、どうなりますか？
   - A) 常に新しい payment を作成する。
   - B) 保存済みの結果を再利用し、競合する値には return409 を返す。
   - C) 実際のカードに課金する。
   - D) order がなくても常に成功する。

<details>
<summary>回答を表示</summary>

**回答: B) 保存済みの結果を再利用し、競合する値には return409 を返す。**

このラボでは実際の payment gateway を実装していません。

</details>

---

5. SNS への公開後、DB のマーク前にクラッシュが発生した場合はどうなりますか？
   - A) exactly once は自動的に保証される。
   - B) 再配信される可能性があるため、コンシューマーには重複排除が必要である。
   - C) すべての outbox 行を削除する。
   - D) 常にメッセージを確認応答する。

<details>
<summary>回答を表示</summary>

**回答: B) 再配信される可能性があるため、コンシューマーには重複排除が必要である。**

外部副作用には追加の冪等性コントラクトが必要です。

</details>

---

6. SQS backlog に応じてスケールするワークロードはどれですか？
   - A) 常に API producer のみ。
   - B) そのキューの consumer。
   - C) database admin。
   - D) NLB。

<details>
<summary>回答を表示</summary>

**回答: B) そのキューの consumer。**

KEDA はキュー属性を読み取ります。メッセージを消費するわけではありません。

</details>

---

7. canary の成功クエリでは何を選択すべきですか？
   - A) すべての stable トラフィックと canary トラフィック。
   - B) 新しい pod-template revision のみ。
   - C) すべての namespace。
   - D) デプロイ前の平均のみ。

<details>
<summary>回答を表示</summary>

**回答: B) 新しい pod-template revision のみ。**

大量の stable トラフィックで失敗している canary を隠してはいけません。

</details>

---

8. 空の結果、NaN、Inf の結果はどのように扱うべきですか？
   - A) 常に 100% の成功として扱う。
   - B) 成功条件を満たしたことにしない。
   - C) すべてゼロに変換して合格させる。
   - D) メトリクスは不要である。

<details>
<summary>回答を表示</summary>

**回答: B) 成功条件を満たしたことにしない。**

最小リクエスト数と observability を併せて確認します。

</details>

---

9. メトリクスに含めるべきラベルはどれですか？
   - A) すべての order ID。
   - B) Service、上限のある route、status、revision。
   - C) customer/card データ。
   - D) 完全なリクエスト本文。

<details>
<summary>回答を表示</summary>

**回答: B) Service、上限のある route、status、revision。**

一意の ID は cardinality とプライバシーの問題を生むため、trace/log の相関を適切に使用します。

</details>

---

10. Rollout の abort は何を意味しますか？
   - A) Git が自動的に revert する。
   - B) Git の revert や望ましい image の復元とは別であるため、source of truth を明示的に復元する。
   - C) すべての DB 書き込みがロールバックされる。
   - D) 新しい image が完全に削除される。

<details>
<summary>回答を表示</summary>

**回答: B) Git の revert や望ましい image の復元とは別であるため、source of truth を明示的に復元する。**

直接的な Helm と ArgoCD を同時の所有者として使用しないでください。

</details>

---

[ガイドに戻る](../../../labs/observability/03-msa-deployment-lab.md)
