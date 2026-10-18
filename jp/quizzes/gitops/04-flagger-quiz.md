# Flagger プログレッシブデリバリー クイズ

1. Flagger の Canary deployment で、`stepWeight: 10`、`maxWeight: 50` は何を意味しますか？
   - A) 分析対象のトラフィックを 10% ずつ増やし、50% を分析目標としてから昇格を行う
   - B) 10 個の Pod を作成し、最大 50 個までスケールアップする
   - C) 10 秒間隔でトラフィックを 50% に切り替える
   - D) 最大 10% のエラー率を許容し、50% でロールバックする

<details>
<summary>回答を表示</summary>

**回答: A) 分析対象のトラフィックを 10% ずつ増やし、50% を分析目標としてから昇格を行う**

**解説:**
`stepWeight` は分析ステップごとの重みの増分、`maxWeight` は分析時の目標重みです。チェックが進むにつれて 10% → 20% → 30% → 40% → 50% と増加し、その後、primary の更新とトラフィックの昇格を行います。昇格中は Canary が一時的にすべてのトラフィックを受ける場合があるため、50% は最終的なトラフィック上限ではありません。

</details>

---

2. Flagger はどのような条件で Canary deployment を自動的にロールバックしますか？
   - A) CPU 使用率が 80% を超えた場合
   - B) ある revision に対する失敗したチェックがしきい値に達した場合
   - C) Pod 数が maxReplicas を超えた場合
   - D) deployment 時間が 30 分を超えた場合

<details>
<summary>回答を表示</summary>

**回答: B) ある revision に対する失敗したチェックがしきい値に達した場合**

**解説:**
Flagger は各分析ステップで定義されたメトリクス（request-success-rate、request-duration など）を評価します。失敗したチェックは revision ごとに累積し、成功したチェックがあっても毎回リセットされるわけではありません。しきい値に達すると、その後の reconciliation でロールバックします。primary への昇格に失敗した場合は別の復旧処理が必要になることがあり、正常な Canary を維持する場合もあります。

</details>

---

3. Flagger と Argo Rollouts の主な違いは何ですか？
   - A) Flagger は Canary のみをサポートし、Argo Rollouts は Blue-Green のみをサポートする
   - B) Flagger は Flux エコシステムと統合され、Argo Rollouts は Argo エコシステムと統合される
   - C) Flagger は Istio のみをサポートし、Argo Rollouts はすべてのメッシュをサポートする
   - D) Flagger はメトリクス分析をサポートしていない

<details>
<summary>回答を表示</summary>

**回答: B) Flagger は Flux エコシステムと統合され、Argo Rollouts は Argo エコシステムと統合される**

**解説:**
Flagger は Flux/Flagger エコシステムの一部であり、FluxCD を使った GitOps ワークフローに自然に統合されます。Argo Rollouts は ArgoCD と並ぶ Argo エコシステムの一部です。ただし、この関係は必須の組み合わせを意味するものではありません。Flagger は Canary リソースを通じて既存のワークロードを制御し、Argo Rollouts は `Rollout` リソースと `workloadRef` を使用します。利用できるルーティングや実験機能はプロバイダーによって異なります。

</details>

---

4. Flagger の Blue-Green deployment における `spec.analysis.mirror: true` の役割は何ですか？
   - A) Blue 環境と Green 環境の間でログをミラーリングする
   - B) 本番トラフィックを Canary（Green）に複製し、実際のトラフィックでテストする
   - C) 同期のためにデータベースをミラーリングする
   - D) 両方の環境で設定を同一に保つ

<details>
<summary>回答を表示</summary>

**回答: B) 本番トラフィックを Canary（Green）に複製し、実際のトラフィックでテストする**

**解説:**
`mirror: true` は、本番トラフィックのコピーを新しいバージョン（Green）へ送り、実際のトラフィックパターンでテストします。応答は破棄されますが、データベースへの書き込み、メッセージ送信、決済処理、追加の負荷が発生する可能性があります。読み取り専用であることを確認したリクエストを使うか、分離や冪等性の対策を設けてください。

</details>

---

5. Flagger で Custom Metrics 分析を使用する際の `templateRef` の役割は何ですか？
   - A) Helm chart template を参照する
   - B) Prometheus/Datadog クエリを実行する MetricTemplate CR を参照する
   - C) Pod を作成するための Deployment template を参照する
   - D) ConfigMap template を参照する

<details>
<summary>回答を表示</summary>

**回答: B) Prometheus/Datadog クエリを実行する MetricTemplate CR を参照する**

**解説:**
`templateRef` は、Prometheus PromQL または Datadog クエリを含む MetricTemplate Custom Resource を参照します。分析フェーズ中に Flagger はこれらのクエリを実行し、結果をしきい値と比較します。これにより、標準的な HTTP メトリクスを超えたビジネスメトリクスに基づいて deployment の判断を行えます。

</details>

---

6. Flagger Webhook を使用した pre-rollout テストの目的は何ですか？
   - A) deployment 前にデータベース migration を実行する
   - B) トラフィック切り替え前に load test または conformance test を実行し、新しいバージョンを検証する
   - C) Git repository にタグを作成する
   - D) Slack 通知を送信する

<details>
<summary>回答を表示</summary>

**回答: B) トラフィック切り替え前に load test または conformance test を実行し、新しいバージョンを検証する**

**解説:**
pre-rollout Webhook は、トラフィックの切り替え開始前に呼び出されます。準備済みのツールと権限を使って、スモークテストや適合性テストを実行してください。非同期の `cmd` load-test が受け付けられたことは、テスト合格を意味しません。`bash` などのブロッキングテストは、設定されたタイムアウト内に完了する必要があります。

</details>

---

7. FluxCD Image Automation と Flagger を使用する際の正しい順序は何ですか？
   - A) イメージを選定 → Git の変更をレビューしてマージ → Flux が適用 → Flagger が分析
   - B) Flagger Canary 分析 → 新しい image tag を検出 → Git commit
   - C) Git commit → 新しい image tag を検出 → Flux sync
   - D) Flux sync → Flagger Canary 分析 → 新しい image tag を検出

<details>
<summary>回答を表示</summary>

**回答: A) イメージを選定 → Git の変更をレビューしてマージ → Flux が適用 → Flagger が分析**

**解説:**
image-reflector はタグとポリシーを評価し、image-automation は指定された YAML を更新します。変更を別ブランチへ push する構成では、PR のレビューとマージ後に Flux が source branch の変更を適用し、Flagger がワークロードの変更を検知します。Flagger が HelmRelease を直接 reconcile するわけではありません。

</details>

---

8. Flagger の A/B Testing における header-based routing は、通常の Canary deployment とどのように異なりますか？
   - A) A/B Testing は新しいバージョンをすべてのユーザーに公開する
   - B) 特定の HTTP header/cookie 条件に一致するリクエストのみが新しいバージョンにルーティングされる
   - C) A/B Testing はロールバックをサポートしていない
   - D) header-based routing は TCP トラフィックにのみ適用される

<details>
<summary>回答を表示</summary>

**回答: B) 特定の HTTP header/cookie 条件に一致するリクエストのみが新しいバージョンにルーティングされる**

**解説:**
A/B Testing では、トラフィックを `spec.analysis.match` で定義した HTTP header または cookie の条件で分類します。一致したリクエストだけが新しいバージョンにルーティングされ、他のリクエストは stable version に送られます。ただし、クライアントが設定できる header や cookie は、従業員であることの認証や機密機能の保護には使えません。

</details>
