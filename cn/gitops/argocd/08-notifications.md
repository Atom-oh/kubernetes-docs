# ArgoCD 通知

> **支持的版本**: ArgoCD v2.9+, ArgoCD Notifications v1.2+
> **最后更新**: February 22, 2026

## 目录
- [概述](#overview)
- [架构](#architecture)
- [通知服务](#notification-services)
- [触发器](#triggers)
- [模板](#templates)
- [订阅](#subscriptions)
- [高级配置](#advanced-configuration)
- [AWS 集成](#aws-integration)

## 概述

ArgoCD Notifications 是一个监控 ArgoCD Application 并在满足特定条件时发送通知的组件。它支持多种通知服务，并提供灵活的模板功能。

### 主要功能

| 功能 | 描述 |
|---------|-------------|
| 多种服务 | Slack、Teams、Email、Webhook、GitHub 等 |
| 灵活的触发器 | 基于条件的通知触发器 |
| Go 模板 | 用于消息格式化的丰富模板语法 |
| 订阅模型 | 按 Application 配置的通知订阅 |
| 内置触发器 | 为常见事件预先配置的触发器 |

## 架构

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

### 安装

ArgoCD v2.4+ 已包含 ArgoCD Notifications。对于较旧版本：

```bash
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/notifications_catalog/install.yaml
```

## 通知服务

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

Slack Bot 设置：
1. 在 https://api.slack.com/apps 创建 Slack App
2. 添加 OAuth scope：`chat:write`、`chat:write.public`
3. 将 App 安装到工作区
4. 复制 Bot User OAuth Token

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

### Email（SMTP）

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

### GitHub（Commit Status）

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

## 触发器

触发器根据 Application 状态定义何时发送通知。

### 内置触发器

| 触发器 | 描述 |
|---------|-------------|
| `on-created` | Application 已创建 |
| `on-deleted` | Application 已删除 |
| `on-deployed` | Application 已同步且健康 |
| `on-health-degraded` | Application 健康状态已降级 |
| `on-sync-failed` | 同步操作失败 |
| `on-sync-running` | 同步操作已开始 |
| `on-sync-status-unknown` | 同步状态未知 |
| `on-sync-succeeded` | 同步操作成功 |

### 自定义触发器

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

### 触发器条件

触发器使用 expr 语言编写条件：

```yaml
trigger.custom: |
  - when: |
      app.status.health.status == 'Degraded' and
      app.metadata.labels.tier == 'critical' and
      time.Now().Hour() >= 9 and time.Now().Hour() < 17
    send: [critical-alert]
```

可用字段：
- `app.metadata.*` - Application 元数据
- `app.spec.*` - Application spec
- `app.status.*` - Application 状态
- `app.operation.*` - 当前操作
- `time.Now()` - 当前时间

## 模板

模板使用 Go 模板定义通知消息格式。

### Slack 模板

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

### Teams 模板

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

### Email 模板

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

### GitHub Commit Status 模板

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

### 模板函数

模板中的可用函数：

| 函数 | 描述 |
|----------|-------------|
| `substr start end` | 子字符串 |
| `toUpper` | 转换为大写 |
| `toLower` | 转换为小写 |
| `replace old new` | 替换字符串 |
| `split delimiter` | 分割字符串 |
| `join delimiter` | 连接数组 |
| `first` | 第一个元素 |
| `last` | 最后一个元素 |
| `default value` | 为空时使用默认值 |
| `indent spaces` | 缩进文本 |
| `nindent spaces` | 换行 + 缩进 |

## 订阅

### Application 级订阅

向 Application 添加 annotation：

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

### 默认订阅

为所有 Application 配置默认订阅：

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

### Project 级订阅

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

## 高级配置

### 上下文变量

添加自定义上下文变量：

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

在模板中使用：

```yaml
template.custom: |
  message: |
    Environment: {{.context.environment}}
    Team: {{.context.team}}
```

### 条件通知

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

### 使用 oncePer 进行速率限制

防止重复通知：

```yaml
trigger.on-sync-status-change: |
  - when: app.status.sync.status != 'Synced'
    send: [sync-status-change]
    oncePer: app.status.sync.revision
```

## AWS 集成

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

### 完整的 AWS 通知设置

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

## 测验

要测试所学内容，请尝试 [ArgoCD 通知测验](../../quizzes/gitops/argocd/08-notifications-quiz.md)。
