# Flagger プログレッシブデリバリー クイズ

1. Flagger の Canary deployment で、`stepWeight: 10`、`maxWeight: 50` は何を意味しますか？
   - A) トラフィックを 10% で開始し、50% まで段階的に増加させた後、100% に昇格させる
   - B) 10 個の Pod を作成し、最大 50 個までスケールアップする
   - C) 10 秒間隔でトラフィックを 50% に切り替える
   - D) 最大 10% のエラー率を許容し、50% でロールバックする

<details>
<summary>回答を表示</summary>

**回答: A) トラフィックを 10% で開始し、50% まで段階的に増加させた後、100% に昇格させる**

**解説:**
`stepWeight` は各分析ステップで増加させるトラフィックの割合であり、`maxWeight` は Canary が受信できるトラフィックの最大割合です。トラフィックは 10% → 20% → 30% → 40% → 50% と増加し、すべてのメトリクスが合格すると 100% に昇格します。

</details>

---

2. Flagger はどのような条件で Canary deployment を自動的にロールバックしますか？
   - A) CPU 使用率が 80% を超えた場合
   - B) 設定された連続失敗回数にわたってメトリクスのしきい値を超えた場合
   - C) Pod 数が maxReplicas を超えた場合
   - D) deployment 時間が 30 分を超えた場合

<details>
<summary>回答を表示</summary>

**回答: B) 設定された連続失敗回数にわたってメトリクスのしきい値を超えた場合**

**解説:**
Flagger は各分析ステップで定義されたメトリクス（request-success-rate、request-duration など）を評価します。連続失敗回数が `threshold` に達すると、自動的にロールバックを実行し、Canary トラフィックを 0% に戻して元のバージョンを維持します。

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
Flagger は Flux/Flagger エコシステムの一部であり、FluxCD を使用した GitOps ワークフローに自然に統合されます。Argo Rollouts は ArgoCD とともに Argo エコシステムの一部です。どちらも Canary、Blue-Green、A/B Testing 戦略をサポートし、さまざまな service mesh と ingress controller で動作します。

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
`mirror: true` は、本番トラフィックのコピーを新しいバージョン（Green）に送信し、実際のトラフィックパターンでテストします。ミラーリングされたレスポンスはクライアントに返されないため、ユーザーに影響を与えずに新しいバージョンの動作を検証できます。

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
pre-rollout Webhook は、トラフィック切り替えの開始前に呼び出されます。通常は Flagger loadtester を介して load test（hey、wrk）または Helm test を実行し、新しいバージョンを実際のユーザーに公開する前に、基本操作が正しく実行されることを検証します。

</details>

---

7. FluxCD Image Automation と Flagger を使用する際の正しい順序は何ですか？
   - A) 新しい image tag を検出 → Git commit → Flux sync → Flagger Canary 分析
   - B) Flagger Canary 分析 → 新しい image tag を検出 → Git commit
   - C) Git commit → 新しい image tag を検出 → Flux sync
   - D) Flux sync → Flagger Canary 分析 → 新しい image tag を検出

<details>
<summary>回答を表示</summary>

**回答: A) 新しい image tag を検出 → Git commit → Flux sync → Flagger Canary 分析**

**解説:**
Flux Image Automation は registry 内の新しい image tag を検出し、Git repository 内の manifest を更新する commit を作成します。Flux がこの変更を sync すると Deployment が更新され、Flagger はその変更を検出して Canary 分析プロセスを自動的に開始します。

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
A/B Testing では、トラフィックは `spec.analysis.match` で定義された HTTP header または cookie 条件に基づいて分類されます。これらの条件に一致するリクエストのみが新しいバージョンにルーティングされるため、他のユーザーが stable version を引き続き使用する一方で、特定のユーザーグループ（beta tester、社内従業員など）に新機能を公開できます。

</details>
