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

2. 古いバージョンから新しいバージョンへトラフィックを段階的に移行する Deployment 戦略はどれですか？
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
   - B) トラフィックが stable（blue）Service から preview（green）Service へ切り替わる
   - C) 両方のバージョンが永久に同時実行される
   - D) 新しい環境が作成される

<details>
<summary>答えを表示</summary>

**答え: B) トラフィックが stable（blue）Service から preview（green）Service へ切り替わる**

**解説:**
Blue-Green deployment では、active Service selector を更新することで、promotion により現在の stable バージョンから preview バージョンへトラフィックを切り替えます。古い ReplicaSet は promotion 後にスケールダウンされます。

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

5. トラフィック分割のために Argo Rollouts とネイティブ統合している Ingress controller はどれですか？
   - A) Traefik のみ
   - B) NGINX Ingress のみ
   - C) NGINX、ALB、Istio、Traefik を含む複数
   - D) なし。手動設定が必要

<details>
<summary>答えを表示</summary>

**答え: C) NGINX、ALB、Istio、Traefik を含む複数**

**解説:**
Argo Rollouts は、NGINX Ingress、AWS ALB、Istio、Linkerd、SMI、Traefik を含む複数の Ingress controller および Service mesh とネイティブのトラフィック管理統合を提供します。

</details>

6. Canary 戦略の `setWeight` ステップは何を行いますか？
   - A) Pod の CPU ウェイトを設定する
   - B) Canary バージョンへルーティングするトラフィックの割合を設定する
   - C) Deployment の重要度を設定する
   - D) rollback のしきい値を設定する

<details>
<summary>答えを表示</summary>

**答え: B) Canary バージョンへルーティングするトラフィックの割合を設定する**

**解説:**
Canary 戦略の `setWeight` ステップは、Canary（新しい）バージョンへルーティングするトラフィックの割合を設定します。たとえば、`setWeight: 20` はトラフィックの 20% を Canary へルーティングします。

</details>

7. Canary deployment 中に AnalysisRun が失敗すると、何が起こりますか？
   - A) Deployment は関係なく続行される
   - B) アラートは送信されるが、それ以外は何も起こらない
   - C) Rollout が自動的に中止され、rollback される
   - D) cluster がシャットダウンされる

<details>
<summary>答えを表示</summary>

**答え: C) Rollout が自動的に中止され、rollback される**

**解説:**
AnalysisRun が失敗すると（メトリクスが失敗しきい値を超えると）、Argo Rollouts は自動的に Rollout を中止し、stable バージョンへの rollback を開始します。これにより、不適切な Deployment がすべてのトラフィックに影響するのを防ぎます。

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
Kong にはネイティブの Argo Rollouts 統合はありません。`trafficRouting.kong` フィールドは存在しません。Kong は、標準の HTTPRoute リソースを操作する argoproj-labs の Gateway API plugin を介してのみサポートされます。Traefik や kgateway など、その他の Gateway API 準拠 controller も同じ plugin を使用します。

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
Gateway API plugin は、各 setWeight ステップで標準 Gateway API HTTPRoute リソースの `backendRefs[].weight` 値を直接更新します。これは、Kong、Traefik、kgateway など、Gateway API を実装するあらゆる controller に同様に適用される汎用的な仕組みです。

</details>
