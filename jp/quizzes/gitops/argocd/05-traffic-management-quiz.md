# ArgoCD トラフィック管理クイズ

このクイズでは、ArgoCD および Argo Rollouts を使用した progressive delivery とトラフィック管理についての理解を確認します。

1. Argo Rollouts とは何ですか？
   - A) ArgoCD 向けのロギングソリューション
   - B) progressive delivery 戦略のための Kubernetes controller
   - C) Git ブランチ管理ツール
   - D) トラフィック監視ダッシュボード

<details>
<summary>答えを表示</summary>

**答え: B) progressive delivery 戦略のための Kubernetes controller**

**解説:**
Argo Rollouts は、Canary deployment、Blue-Green deployment、および自動分析を伴う progressive delivery などの高度な Deployment 機能を提供する Kubernetes controller です。

</details>

2. 明示的なトラフィック重みの各段階と分析ゲートを使って新しいバージョンを検証する戦略はどれですか？
   - A) Recreate
   - B) Rolling Update
   - C) Canary
   - D) Blue-Green

<details>
<summary>答えを表示</summary>

**答え: C) Canary**

**解説:**
Canary deployment は、古いバージョンから新しいバージョンへトラフィックを段階的に移行します（例: 10%、25%、50%、100%）。これにより、各ステップでテストと検証を行えます。

</details>

3. Argo Rollouts を使用した Blue-Green deployment では、promotion 中に何が起こりますか？
   - A) blue 環境が削除される
   - B) active Service の selector が新しい ReplicaSet に切り替わる
   - C) 両方のバージョンが永久に同時実行される
   - D) 新しい環境が作成される

<details>
<summary>答えを表示</summary>

**答え: B) active Service の selector が新しい ReplicaSet に切り替わる**

**解説:**
Blue-Green deployment の promotion では、active Service の selector を新しい ReplicaSet に切り替えます。古い ReplicaSet のスケールダウンは、分析と遅延の設定に従います。データプレーンへの反映は瞬時ではありません。

</details>

4. Argo Rollouts における AnalysisTemplate とは何ですか？
   - A) 新しいアプリケーションを作成するためのテンプレート
   - B) 自動 Canary 分析のためのメトリクスと成功条件の定義
   - C) ロギング設定
   - D) リソースクォータテンプレート

<details>
<summary>答えを表示</summary>

**答え: B) 自動 Canary 分析のためのメトリクスと成功条件の定義**

**解説:**
AnalysisTemplate は、クエリするメトリクス（Prometheus、Datadog など）と成功／失敗の条件を定義します。Rollout 中に AnalysisRun がこれらのテンプレートを実行し、Deployment を続行すべきかどうかを自動的に判断します。

</details>

5. Argo Rollouts にネイティブなトラフィック管理統合を提供するプロバイダーはどれですか？
   - A) Traefik のみ
   - B) NGINX Ingress のみ
   - C) NGINX、ALB、Istio、Traefik を含む複数
   - D) なし。手動設定が必要

<details>
<summary>答えを表示</summary>

**答え: C) NGINX、ALB、Istio、Traefik を含む複数**

**解説:**
Argo Rollouts は、AWS ALB、Istio、Traefik、APISIX など、複数の Ingress controller と Service mesh にネイティブなトラフィック管理統合を提供します。ingress-nginx や SMI の API が引き続きサポートされていても、それらのプロジェクトが今も保守されているとは限りません。Linkerd 用の独立したネイティブフィールドはありません。

</details>

6. トラフィックルーターがあり、既定の `maxTrafficWeight=100` を使う場合、`setWeight` は何を設定しますか？
   - A) Pod の CPU ウェイトを設定する
   - B) Canary バージョンへルーティングするトラフィックの割合を設定する
   - C) Deployment の重要度を設定する
   - D) rollback のしきい値を設定する

<details>
<summary>答えを表示</summary>

**答え: B) Canary バージョンへルーティングするトラフィックの割合を設定する**

**解説:**
Canary 戦略の `setWeight` ステップは、Canary（新しい）バージョンへ送るトラフィックの割合を指定します。たとえば、`setWeight: 20` は 20/100 の相対的な重みを要求します。実際に観測される割合は、サンプル数、接続、cookie によって異なります。トラフィックルーターがない場合は、Pod 数でおおよその比率を実現します。

</details>

7. Rollout に関連付けられた分析が AnalysisRun の `Failed` フェーズに達すると、何が起こりますか？
   - A) Deployment は関係なく続行される
   - B) アラートは送信されるが、それ以外は何も起こらない
   - C) Rollout が自動的に中止され、rollback される
   - D) cluster がシャットダウンされる

<details>
<summary>答えを表示</summary>

**答え: C) Rollout が自動的に中止され、rollback される**

**解説:**
AnalysisRun が失敗フェーズに達すると、Argo Rollouts は Rollout を中止してトラフィックを stable に戻します。ただし、Git やデータベースの変更は巻き戻しません。`failureLimit` は失敗した測定値と AnalysisRun 自体の失敗を区別します。`Inconclusive` は調査のために一時停止します。

</details>

8. 手動検証のために特定のステップで Rollout を一時停止するにはどうしますか？
   - A) duration を指定しない `pause` ステップを使用する
   - B) `stop` ステップを使用する
   - C) duration: forever を指定した `wait` ステップを使用する
   - D) 不可能

<details>
<summary>答えを表示</summary>

**答え: A) duration を指定しない `pause` ステップを使用する**

**解説:**
duration を指定しない `pause` ステップを追加すると、無期限の一時停止が作成され、続行するには手動での promotion（CLI または UI 経由）が必要になります。これは Deployment プロセスにおける手動検証ゲートに役立ちます。

</details>

9. Kong Ingress Controller を通じて Canary トラフィックを分割するにはどうしますか？
   - A) `trafficRouting.kong` フィールドを直接使用する
   - B) Gateway API plugin（`trafficRouting.plugins`）を介して HTTPRoute を操作する
   - C) Kong を Argo Rollouts と統合することはできない
   - D) Istio VirtualService を使用して迂回させる

<details>
<summary>答えを表示</summary>

**答え: B) Gateway API plugin（`trafficRouting.plugins`）を介して HTTPRoute を操作する**

**解説:**
Kong には Argo Rollouts とのネイティブ統合がなく、`trafficRouting.kong` フィールドもありません。この章では argoproj-labs の Gateway API plugin を使い、標準の HTTPRoute リソースを操作します。Traefik や kgateway など、ほかの Gateway API 準拠 controller も同じ plugin を使用します。

</details>

10. Argo Rollouts Gateway API plugin は、各 Canary weight ステップで実際にどのリソースを更新しますか？
    - A) Service の `selector` ラベル
    - B) Ingress の `canary-weight` annotation
    - C) HTTPRoute の `backendRefs[].weight`
    - D) DestinationRule の subset ラベル

<details>
<summary>答えを表示</summary>

**答え: C) HTTPRoute の `backendRefs[].weight`**

**解説:**
Gateway API plugin は、各 `setWeight` ステップで標準 Gateway API の HTTPRoute リソースにある `backendRefs[].weight` 値を直接更新します。対応する controller で機能する仕組みですが、導入済み CRD、サポートされる Route 機能、実際のデータプレーンへの反映を確認してください。

</details>
