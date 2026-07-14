# ArgoCD トラフィック管理クイズ

このクイズでは、ArgoCD と Argo Rollouts を使用した progressive delivery およびトラフィック管理についての理解度を確認します。

1. Argo Rollouts とは何ですか？
   - A) ArgoCD 用のロギングソリューション
   - B) progressive delivery 戦略のための Kubernetes controller
   - C) Git ブランチ管理ツール
   - D) トラフィック監視ダッシュボード

<details>
<summary>回答を表示</summary>

**回答: B) progressive delivery 戦略のための Kubernetes controller**

**解説:**
Argo Rollouts は、Canary Deployment、Blue-Green Deployment、自動分析を伴う progressive delivery などの高度な Deployment 機能を提供する Kubernetes controller です。

</details>

2. 旧バージョンから新バージョンへトラフィックを段階的に移行する Deployment 戦略はどれですか？
   - A) Recreate
   - B) Rolling Update
   - C) Canary
   - D) Blue-Green

<details>
<summary>回答を表示</summary>

**回答: C) Canary**

**解説:**
Canary Deployment では、トラフィックを旧バージョンから新バージョンへ段階的に移行します（例: 10%、25%、50%、100%）。これにより、各段階でテストと検証を行えます。

</details>

3. Argo Rollouts を使用した Blue-Green Deployment で、promotion 中に何が起こりますか？
   - A) blue 環境が削除される
   - B) トラフィックが stable (blue) Service から preview (green) Service に切り替えられる
   - C) 両方のバージョンが永久に同時実行される
   - D) 新しい環境が作成される

<details>
<summary>回答を表示</summary>

**回答: B) トラフィックが stable (blue) Service から preview (green) Service に切り替えられる**

**解説:**
Blue-Green Deployment では、active Service selector を更新することで、promotion により現在の stable version から preview version へトラフィックを切り替えます。古い ReplicaSet は promotion 後に scale down されます。

</details>

4. Argo Rollouts の AnalysisTemplate とは何ですか？
   - A) 新しいアプリケーションを作成するためのテンプレート
   - B) 自動 Canary analysis のための metrics と success criteria の定義
   - C) ログ設定
   - D) resource quota テンプレート

<details>
<summary>回答を表示</summary>

**回答: B) 自動 Canary analysis のための metrics と success criteria の定義**

**解説:**
AnalysisTemplates は、クエリ対象の metrics（Prometheus、Datadog など）と success/failure criteria を定義します。rollout 中に、AnalysisRuns がこれらの template を実行し、Deployment を進めるべきかどうかを自動的に判断します。

</details>

5. トラフィック分割のために Argo Rollouts と native integration を持つ Ingress controller はどれですか？
   - A) Traefik のみ
   - B) NGINX Ingress のみ
   - C) NGINX、ALB、Istio、Traefik を含む複数
   - D) なし。手動設定が必要

<details>
<summary>回答を表示</summary>

**回答: C) NGINX、ALB、Istio、Traefik を含む複数**

**解説:**
Argo Rollouts は、NGINX Ingress、AWS ALB、Istio、Linkerd、SMI、Traefik を含む複数の Ingress controller および service mesh と native traffic management integration を備えています。

</details>

6. Canary strategy の `setWeight` step は何を行いますか？
   - A) Pod の CPU weight を設定する
   - B) Canary version にルーティングするトラフィックの割合を設定する
   - C) Deployment の重要度を設定する
   - D) rollback threshold を設定する

<details>
<summary>回答を表示</summary>

**回答: B) Canary version にルーティングするトラフィックの割合を設定する**

**解説:**
Canary strategy の `setWeight` step は、トラフィックのうち Canary（新しい）version に route する割合を設定します。たとえば、`setWeight: 20` はトラフィックの 20% を Canary に route します。

</details>

7. Canary Deployment 中に AnalysisRun が失敗すると何が起こりますか？
   - A) Deployment は関係なく継続される
   - B) alert は送信されるが、それ以外は何も起こらない
   - C) rollout は自動的に中止され、rollback される
   - D) cluster が停止される

<details>
<summary>回答を表示</summary>

**回答: C) rollout は自動的に中止され、rollback される**

**解説:**
AnalysisRun が失敗すると（metrics が failure threshold を超えると）、Argo Rollouts は rollout を自動的に中止し、stable version への rollback を開始します。これにより、不適切な Deployment がすべてのトラフィックに影響することを防ぎます。

</details>

8. 手動検証のために、特定の step で Rollout を pause するにはどうすればよいですか？
   - A) duration を指定しない `pause` step を使用する
   - B) `stop` step を使用する
   - C) duration: forever を指定した `wait` step を使用する
   - D) 不可能

<details>
<summary>回答を表示</summary>

**回答: A) duration を指定しない `pause` step を使用する**

**解説:**
duration を指定せずに `pause` step を追加すると、無期限の pause が作成され、継続するには手動 promotion（CLI または UI 経由）が必要になります。これは Deployment プロセスにおける手動検証ゲートに役立ちます。

</details>
