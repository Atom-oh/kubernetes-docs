# ArgoCD Notifications

> **サポート対象バージョン**: ArgoCD v2.9+, ArgoCD Notifications v1.2+
> **最終更新**: February 22, 2026

## 目次
- [概要](#overview)
- [アーキテクチャ](#architecture)
- [通知サービス](#notification-services)
- [トリガー](#triggers)
- [テンプレート](#templates)
- [サブスクリプション](#subscriptions)
- [高度な設定](#advanced-configuration)
- [AWS 統合](#aws-integration)

## 概要

ArgoCD Notifications は、ArgoCD Application を監視し、特定の条件が満たされたときに通知を送信するコンポーネントです。複数の通知サービスをサポートし、柔軟なテンプレート機能を提供します。

### 主な機能

| 機能 | 説明 |
|---------|-------------|
| 複数サービス | Slack、Teams、Email、Webhook、GitHub など |
| 柔軟なトリガー | 条件ベースの通知トリガー |
| Go Templates | メッセージ整形のための豊富なテンプレート構文 |
| サブスクリプションモデル | Application ごとの通知サブスクリプション |
| 組み込みトリガー | 一般的なイベント向けに事前設定されたトリガー |

## アーキテクチャ

```mermaid
flowchart LR
    subgraph ARGOCD["ArgoCD"]
        APPS["Applications"]
        CTRL["App Controller"]
    end

    subgraph NOTIFICATIONS["Notifications Controller"]
        WATCH["Watch Apps"]
        EVAL["Evaluate Triggers"]
        SEND["Send Notifications"]
    end

    subgraph SERVICES["Notification Services"]
        SLACK["Slack"]
        TEAMS["Teams"]
        EMAIL["Email"]
        WEBHOOK["Webhook"]
        GITHUB["GitHub"]
    end

    APPS --> CTRL
    CTRL --> WATCH
    WATCH --> EVAL
    EVAL -->|"trigger matched"| SEND
    SEND --> SLACK
    SEND --> TEAMS
    SEND --> EMAIL
    SEND --> WEBHOOK
    SEND --> GITHUB

    classDef argocd fill:#EB6E85,stroke:#333,color:white
    classDef notif fill:#6c757d,stroke:#333,color:white
    classDef service fill:#28a745,stroke:#333,color:white

    class APPS,CTRL argocd
    class WATCH,EVAL,SEND notif
    class SLACK,TEAMS,EMAIL,WEBHOOK,GITHUB service
```

### インストール

ArgoCD Notifications は ArgoCD v2.4+ に含まれています。古いバージョンの場合:

```bash
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/notifications_catalog/install.yaml
```

## 通知サービス

### Slack

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.slack: |
    token: $slack-token
    signingSecret: $slack-signing-secret  # Optional, for verification
---
apiVersion: v1
kind: Secret
metadata:
  name: argocd-notifications-secret
  namespace: argocd
type: Opaque
stringData:
  slack-token: xoxb-your-bot-token
```

Slack Bot のセットアップ:
1. https://api.slack.com/apps で Slack App を作成します
2. OAuth スコープを追加します: `chat:write`、`chat:write.public`
3. App をワークスペースにインストールします
4. Bot User OAuth Token をコピーします

### Microsoft Teams

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.teams: |
    recipientUrls:
      deployments: $teams-webhook-deployments
      alerts: $teams-webhook-alerts
---
apiVersion: v1
kind: Secret
metadata:
  name: argocd-notifications-secret
  namespace: argocd
type: Opaque
stringData:
  teams-webhook-deployments: https://outlook.office.com/webhook/xxx
  teams-webhook-alerts: https://outlook.office.com/webhook/yyy
```

### Email (SMTP)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.email: |
    host: smtp.example.com
    port: 587
    username: $email-username
    password: $email-password
    from: argocd@example.com
---
apiVersion: v1
kind: Secret
metadata:
  name: argocd-notifications-secret
  namespace: argocd
type: Opaque
stringData:
  email-username: argocd@example.com
  email-password: your-smtp-password
```

### Webhook

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.webhook.custom: |
    url: https://api.example.com/webhooks/argocd
    headers:
      - name: Authorization
        value: Bearer $webhook-token
      - name: Content-Type
        value: application/json
---
apiVersion: v1
kind: Secret
metadata:
  name: argocd-notifications-secret
  namespace: argocd
type: Opaque
stringData:
  webhook-token: your-api-token
```

### GitHub (Commit Status)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.github: |
    appID: 123456
    installationID: 12345678
    privateKey: $github-privateKey
---
apiVersion: v1
kind: Secret
metadata:
  name: argocd-notifications-secret
  namespace: argocd
type: Opaque
stringData:
  github-privateKey: |
    -----BEGIN RSA PRIVATE KEY-----
    ...
    -----END RSA PRIVATE KEY-----
```

### Grafana

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.grafana: |
    apiUrl: https://grafana.example.com/api
    apiKey: $grafana-api-key
```

### PagerDuty

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.pagerduty: |
    serviceKeys:
      production: $pagerduty-key-prod
      staging: $pagerduty-key-staging
```

## トリガー

トリガーは、Application の状態に基づいて通知を送信するタイミングを定義します。

### 組み込みトリガー

| トリガー | 説明 |
|---------|-------------|
| `on-created` | Application が作成された |
| `on-deleted` | Application が削除された |
| `on-deployed` | Application が同期され、正常な状態である |
| `on-health-degraded` | Application のヘルスが低下している |
| `on-sync-failed` | Sync 操作が失敗した |
| `on-sync-running` | Sync 操作が開始された |
| `on-sync-status-unknown` | Sync ステータスが不明である |
| `on-sync-succeeded` | Sync 操作が成功した |

### カスタムトリガー

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  # Trigger when app becomes healthy
  trigger.on-deployed: |
    - when: app.status.operationState.phase in ['Succeeded'] and app.status.health.status == 'Healthy'
      send: [app-deployed]

  # Trigger on sync failure
  trigger.on-sync-failed: |
    - when: app.status.operationState != nil and app.status.operationState.phase in ['Error', 'Failed']
      send: [app-sync-failed]

  # Trigger on health degradation
  trigger.on-health-degraded: |
    - when: app.status.health.status == 'Degraded'
      send: [app-health-degraded]

  # Custom trigger: High replica count
  trigger.on-high-replicas: |
    - when: app.status.summary.images | length > 5
      send: [high-image-count]

  # Custom trigger: Production deployment
  trigger.on-prod-deployed: |
    - when: app.metadata.labels.environment == 'production' and app.status.operationState.phase == 'Succeeded'
      send: [prod-deployment-success]
      oncePer: app.status.sync.revision

  # Trigger with time-based condition
  trigger.on-long-sync: |
    - when: time.Now().Sub(time.Parse(app.status.operationState.startedAt)).Minutes() > 10
      send: [long-sync-warning]
```

### トリガー条件

トリガーは条件に expr 言語を使用します:

```yaml
trigger.custom: |
  - when: |
      app.status.health.status == 'Degraded' and
      app.metadata.labels.tier == 'critical' and
      time.Now().Hour() >= 9 and time.Now().Hour() < 17
    send: [critical-alert]
```

使用可能なフィールド:
- `app.metadata.*` - Application メタデータ
- `app.spec.*` - Application spec
- `app.status.*` - Application ステータス
- `app.operation.*` - 現在の操作
- `time.Now()` - 現在時刻

## テンプレート

テンプレートは、Go templates を使用して通知メッセージの形式を定義します。

### Slack テンプレート

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  template.app-deployed: |
    message: |
      :white_check_mark: Application *{{.app.metadata.name}}* is now healthy!
    slack:
      attachments: |
        [{
          "color": "#18be52",
          "title": "{{.app.metadata.name}}",
          "title_link": "{{.context.argocdUrl}}/applications/{{.app.metadata.name}}",
          "fields": [
            {
              "title": "Sync Status",
              "value": "{{.app.status.sync.status}}",
              "short": true
            },
            {
              "title": "Health Status",
              "value": "{{.app.status.health.status}}",
              "short": true
            },
            {
              "title": "Revision",
              "value": "{{.app.status.sync.revision | substr 0 7}}",
              "short": true
            },
            {
              "title": "Repository",
              "value": "{{.app.spec.source.repoURL}}",
              "short": true
            }
          ]
        }]

  template.app-sync-failed: |
    message: |
      :x: Application *{{.app.metadata.name}}* sync failed!
    slack:
      attachments: |
        [{
          "color": "#E96D76",
          "title": "{{.app.metadata.name}} - Sync Failed",
          "title_link": "{{.context.argocdUrl}}/applications/{{.app.metadata.name}}",
          "fields": [
            {
              "title": "Error",
              "value": "{{.app.status.operationState.message}}",
              "short": false
            },
            {
              "title": "Revision",
              "value": "{{.app.status.sync.revision | substr 0 7}}",
              "short": true
            }
          ]
        }]

  template.app-health-degraded: |
    message: |
      :warning: Application *{{.app.metadata.name}}* health is degraded!
    slack:
      attachments: |
        [{
          "color": "#f4c030",
          "title": "{{.app.metadata.name}} - Health Degraded",
          "title_link": "{{.context.argocdUrl}}/applications/{{.app.metadata.name}}",
          "fields": [
            {
              "title": "Health Status",
              "value": "{{.app.status.health.status}}",
              "short": true
            },
            {
              "title": "Message",
              "value": "{{.app.status.health.message}}",
              "short": false
            }
          ]
        }]
```

### Teams テンプレート

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  template.app-deployed-teams: |
    teams:
      themeColor: "#18be52"
      title: "Application Deployed"
      text: "Application **{{.app.metadata.name}}** has been deployed successfully."
      sections: |
        [{
          "facts": [
            {
              "name": "Application",
              "value": "{{.app.metadata.name}}"
            },
            {
              "name": "Health Status",
              "value": "{{.app.status.health.status}}"
            },
            {
              "name": "Sync Status",
              "value": "{{.app.status.sync.status}}"
            },
            {
              "name": "Revision",
              "value": "{{.app.status.sync.revision | substr 0 7}}"
            }
          ]
        }]
      potentialAction: |
        [{
          "@type": "OpenUri",
          "name": "View in ArgoCD",
          "targets": [{
            "os": "default",
            "uri": "{{.context.argocdUrl}}/applications/{{.app.metadata.name}}"
          }]
        }]
```

### Email テンプレート

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  template.app-deployed-email: |
    email:
      subject: "[ArgoCD] Application {{.app.metadata.name}} Deployed"
    message: |
      <html>
      <body>
        <h2>Application Deployment Successful</h2>
        <table border="1" cellpadding="5">
          <tr>
            <th>Application</th>
            <td>{{.app.metadata.name}}</td>
          </tr>
          <tr>
            <th>Health Status</th>
            <td>{{.app.status.health.status}}</td>
          </tr>
          <tr>
            <th>Sync Status</th>
            <td>{{.app.status.sync.status}}</td>
          </tr>
          <tr>
            <th>Revision</th>
            <td>{{.app.status.sync.revision}}</td>
          </tr>
          <tr>
            <th>Repository</th>
            <td>{{.app.spec.source.repoURL}}</td>
          </tr>
        </table>
        <p>
          <a href="{{.context.argocdUrl}}/applications/{{.app.metadata.name}}">
            View in ArgoCD
          </a>
        </p>
      </body>
      </html>
```

### GitHub Commit Status テンプレート

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  template.github-commit-status: |
    github:
      status:
        state: "{{if eq .app.status.sync.status \"Synced\"}}success{{else}}failure{{end}}"
        context: "argocd/{{.app.metadata.name}}"
        description: "{{.app.metadata.name}} - {{.app.status.sync.status}}"
        targetURL: "{{.context.argocdUrl}}/applications/{{.app.metadata.name}}"
      repoURLPath: "{{.app.spec.source.repoURL}}"
      revisionPath: "{{.app.status.sync.revision}}"
```

### テンプレート関数

テンプレートで使用可能な関数:

| 関数 | 説明 |
|----------|-------------|
| `substr start end` | 部分文字列 |
| `toUpper` | 大文字に変換 |
| `toLower` | 小文字に変換 |
| `replace old new` | 文字列を置換 |
| `split delimiter` | 文字列を分割 |
| `join delimiter` | 配列を結合 |
| `first` | 最初の要素 |
| `last` | 最後の要素 |
| `default value` | 空の場合のデフォルト値 |
| `indent spaces` | テキストをインデント |
| `nindent spaces` | 改行してインデント |

## サブスクリプション

### Application レベルのサブスクリプション

Application にアノテーションを追加します:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
  annotations:
    # Subscribe to triggers with service destinations
    notifications.argoproj.io/subscribe.on-sync-succeeded.slack: deployments
    notifications.argoproj.io/subscribe.on-sync-failed.slack: deployments,alerts
    notifications.argoproj.io/subscribe.on-health-degraded.slack: alerts
    notifications.argoproj.io/subscribe.on-deployed.teams: deployments
    notifications.argoproj.io/subscribe.on-sync-failed.email: ops@example.com
spec:
  # ...
```

### デフォルトサブスクリプション

すべての Application のデフォルトサブスクリプションを設定します:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  # Default triggers for all applications
  defaultTriggers: |
    - on-sync-failed
    - on-health-degraded

  # Default subscriptions
  subscriptions: |
    - recipients:
        - slack:alerts
      triggers:
        - on-sync-failed
        - on-health-degraded
    - recipients:
        - email:ops@example.com
      triggers:
        - on-sync-failed
      selector: environment=production
```

### Project レベルのサブスクリプション

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: production
  namespace: argocd
  annotations:
    notifications.argoproj.io/subscribe.on-sync-failed.slack: production-alerts
    notifications.argoproj.io/subscribe.on-health-degraded.pagerduty: production
spec:
  # ...
```

## 高度な設定

### コンテキスト変数

カスタムコンテキスト変数を追加します:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  context: |
    argocdUrl: https://argocd.example.com
    environment: production
    team: platform
    slackChannel: "#deployments"
```

テンプレートで使用します:

```yaml
template.custom: |
  message: |
    Environment: {{.context.environment}}
    Team: {{.context.team}}
```

### 条件付き通知

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  trigger.on-critical-failure: |
    - when: |
        app.status.operationState.phase == 'Failed' and
        app.metadata.labels.tier == 'critical'
      send: [critical-failure]
      oncePer: app.status.sync.revision

  template.critical-failure: |
    message: |
      :rotating_light: CRITICAL APPLICATION FAILURE :rotating_light:
      Application *{{.app.metadata.name}}* has failed!
      {{if .app.status.operationState.message}}
      Error: {{.app.status.operationState.message}}
      {{end}}
    slack:
      attachments: |
        [{
          "color": "#dc3545",
          "title": "{{.app.metadata.name}} - CRITICAL FAILURE",
          "title_link": "{{.context.argocdUrl}}/applications/{{.app.metadata.name}}"
        }]
```

### oncePer によるレート制限

重複通知を防止します:

```yaml
trigger.on-sync-status-change: |
  - when: app.status.sync.status != 'Synced'
    send: [sync-status-change]
    oncePer: app.status.sync.revision
```

## AWS 統合

### Amazon SNS

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.webhook.sns: |
    url: https://sns.us-west-2.amazonaws.com
    headers:
      - name: Content-Type
        value: application/x-www-form-urlencoded

  template.sns-notification: |
    webhook:
      sns:
        method: POST
        body: |
          Action=Publish&TopicArn=arn:aws:sns:us-west-2:123456789012:argocd-notifications&Message={{.app.metadata.name}} - {{.app.status.sync.status}}
```

### Amazon SQS

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.webhook.sqs: |
    url: https://sqs.us-west-2.amazonaws.com/123456789012/argocd-notifications
    headers:
      - name: Content-Type
        value: application/x-www-form-urlencoded

  template.sqs-notification: |
    webhook:
      sqs:
        method: POST
        body: |
          Action=SendMessage&MessageBody={"app":"{{.app.metadata.name}}","status":"{{.app.status.sync.status}}","revision":"{{.app.status.sync.revision}}"}
```

### Lambda Webhook

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.webhook.lambda: |
    url: https://xxxxx.execute-api.us-west-2.amazonaws.com/prod/argocd-webhook
    headers:
      - name: x-api-key
        value: $lambda-api-key
      - name: Content-Type
        value: application/json

  template.lambda-notification: |
    webhook:
      lambda:
        method: POST
        body: |
          {
            "application": "{{.app.metadata.name}}",
            "project": "{{.app.spec.project}}",
            "syncStatus": "{{.app.status.sync.status}}",
            "healthStatus": "{{.app.status.health.status}}",
            "revision": "{{.app.status.sync.revision}}",
            "repoURL": "{{.app.spec.source.repoURL}}",
            "timestamp": "{{.app.status.operationState.finishedAt}}"
          }
```

### AWS 通知の完全なセットアップ

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  context: |
    argocdUrl: https://argocd.example.com
    awsRegion: us-west-2
    environment: production

  service.webhook.eventbridge: |
    url: https://events.us-west-2.amazonaws.com
    headers:
      - name: Content-Type
        value: application/x-amz-json-1.1
      - name: X-Amz-Target
        value: AWSEvents.PutEvents

  trigger.on-sync-completed: |
    - when: app.status.operationState.phase in ['Succeeded', 'Failed']
      send: [aws-eventbridge]

  template.aws-eventbridge: |
    webhook:
      eventbridge:
        method: POST
        body: |
          {
            "Entries": [{
              "Source": "argocd",
              "DetailType": "Application Sync Event",
              "Detail": "{\"application\":\"{{.app.metadata.name}}\",\"status\":\"{{.app.status.operationState.phase}}\",\"revision\":\"{{.app.status.sync.revision}}\"}",
              "EventBusName": "argocd-events"
            }]
          }
```

## クイズ

学んだ内容を確認するには、[ArgoCD notifications クイズ](../../quizzes/gitops/argocd/08-notifications-quiz.md)に挑戦してください。
