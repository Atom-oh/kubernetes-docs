# ArgoCD Notifications クイズ

このクイズでは、ArgoCD notification system と alerting についての理解度を確認します。

1. ArgoCD で notifications を処理するコンポーネントはどれですか？
   - A) Application Controller
   - B) Notifications Controller (argocd-notifications)
   - C) API Server
   - D) Repo Server

<details>
<summary>回答を表示</summary>

**回答: B) Notifications Controller (argocd-notifications)**

**解説:**
ArgoCD Notifications Controller は ArgoCD Applications を監視し、設定された triggers と templates に基づいて notifications を送信します。これは core ArgoCD に統合された独立したコンポーネントです。

</details>

2. ArgoCD では notification の設定はどこに保存されますか？
   - A) 専用の CRD 内
   - B) argocd-notifications-cm ConfigMap 内
   - C) Application spec 内
   - D) environment variables 内

<details>
<summary>回答を表示</summary>

**回答: B) argocd-notifications-cm ConfigMap 内**

**解説:**
Notification services、templates、triggers は `argocd-notifications-cm` ConfigMap で設定します。webhook URLs などの機密データは `argocd-notifications-secret` に保存されます。

</details>

3. ArgoCD notifications における「trigger」とは何ですか？
   - A) 手動で notifications を送信するためのボタン
   - B) notification を送信するタイミングを決定する条件
   - C) webhook endpoint
   - D) notification template

<details>
<summary>回答を表示</summary>

**回答: B) notification を送信するタイミングを決定する条件**

**解説:**
Triggers は、notifications を送信するタイミングを決定する条件（sync status の変更、health の変更、sync failure など）を定義します。これらは notification content を整形する templates を参照します。

</details>

4. notifications を受信するように Application を subscribe するにはどうしますか？
   - A) notifications ConfigMap を編集する
   - B) notification subscriptions を含む annotations を Application に追加する
   - C) NotificationSubscription CRD を作成する
   - D) ArgoCD UI で設定する

<details>
<summary>回答を表示</summary>

**回答: B) notification subscriptions を含む annotations を Application に追加する**

**解説:**
Applications は、`notifications.argoproj.io/subscribe.on-sync-succeeded.slack: my-channel` のような annotations を使用して notifications を subscribe します。これにより trigger、service、recipient を指定します。

</details>

5. ArgoCD は標準でどの notification services をサポートしていますか？
   - A) Slack のみ
   - B) email のみ
   - C) Slack、Teams、email、webhooks などを含む複数のサービス
   - D) なし。すべて custom plugins が必要

<details>
<summary>回答を表示</summary>

**回答: C) Slack、Teams、email、webhooks などを含む複数のサービス**

**解説:**
ArgoCD notifications は、Slack、Microsoft Teams、Telegram、Opsgenie、Grafana、PagerDuty、GitHub、email (SMTP)、generic webhooks など、多くの services をサポートしています。

</details>
