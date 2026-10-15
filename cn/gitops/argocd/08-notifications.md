# ArgoCD Notifications

> **Reviewed Against**: Argo CD 3.5.2（捆绑的 Notifications Engine 0cff13b8a717）；在审阅发行说明后更新至补丁版本 3.5.4，该版本固定使用相同的 Notifications Engine commit（示例未重新运行）
> **最后更新**: October 12, 2026

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Notification Services](#notification-services)
- [Triggers](#triggers)
- [Templates](#templates)
- [Subscriptions](#subscriptions)
- [Advanced Configuration](#advanced-configuration)
- [AWS Integration](#aws-integration)

## Overview

ArgoCD Notifications 是一个监控 ArgoCD 应用程序，并在满足特定条件时发送通知的组件。它支持多种通知服务，并提供灵活的模板功能。

### Key Features

| Feature | Description |
|---------|-------------|
| Multiple Services | Slack, Teams, Email, Webhook, GitHub, and more |
| Flexible Triggers | Condition-based notification triggers |
| Go Templates | Rich template syntax for message formatting |
| Subscription Model | Per-application notification subscriptions |
| Example Catalog | Optional trigger/template definitions to merge into your configuration |

## Architecture

![Flow diagram of ArgoCD notifications: Application events reach the Notifications Controller, which evaluates triggers and renders templates, then sends messages to the matching configured subscriptions.](../../.gitbook/assets/en-gitops-argocd-08-notifications-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-08-notifications-0.html)

### Controller and Configuration

完整的 Argo CD 3.5.4 安装包含 Notifications controller。请在安装配置/Helm values 中确认其已启用。notifications_catalog/install.yaml 文件包含示例配置；它不是用于安装缺失 controller 的安装程序。请将选定的 catalog 条目合并到现有的 ConfigMap 和 Secret 中。

```bash
kubectl get deployment argocd-notifications-controller -n argocd
```

## Notification Services

将这些数据片段组合到一个 argocd-notifications-cm 配置中；不要使用每个独立片段替换同一个 ConfigMap/Secret。将 token、已签名的 webhook URL 和私钥存储在 Git 之外受保护的 argocd-notifications-secret 值中。Service、template、trigger 和 subscription 名称必须彼此一致。

### Slack

配置 chat:write，并邀请 bot 加入目标 channel。仅当要发布到 bot 尚未加入的公共 channel 时，才需要 chat:write.public。signingSecret 不能替代 Incoming Webhook URL。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.slack: |
    token: $slack-token
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
2. 添加 `chat:write`；仅当所述使用场景需要时才使用 `chat:write.public`
3. 将 app 安装到 workspace
4. 复制 Bot User OAuth Token

### Microsoft Teams Workflows

使用带有 teams-workflows 的 Workflows endpoint，而非旧版 Office365 Connectors。验证实际的 endpoint 身份验证以及 flow 所有者/共同所有者生命周期。将其已签名 URL 保存在 Secret 中；不要假定旧版 MessageCard endpoint 可以互换使用。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.teams-workflows: |
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
  teams-webhook-deployments: REPLACE_WITH_TEAMS_WORKFLOWS_URL
  teams-webhook-alerts: REPLACE_WITH_TEAMS_WORKFLOWS_URL
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
    html: true
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
      value: $webhook-authorization
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
  webhook-authorization: Bearer REPLACE_WITH_RECEIVER_TOKEN
```

### GitHub (Commit Status)

在目标 repository 上安装 GitHub App，并授予 Commit statuses 写入权限。使用该安装的值替换示例 ID 和私钥。

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

使用具有所需 annotation-write 权限的 service-account token。此 engine 要求 apiUrl 包含 /api，并会追加 annotations。避免默认使用管理员 token 或不必要的超长有效期。

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

### PagerDuty Events API v2

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.pagerdutyv2: |
    serviceKeys:
      production: $pagerduty-key-prod
      staging: $pagerduty-key-staging
```

## Triggers

这些是显式定义的示例，而非关于自动安装 catalog 的假设。它们的 `send` 条目引用下方的 `template.app-status`。请将这些片段与选定的 service 设置一起**合并到一个 ConfigMap 中**。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  context: |
    argocdUrl: https://argocd.example.com
  trigger.on-sync-succeeded: |
    - when: app.status?.operationState?.phase == 'Succeeded'
      oncePer: app.status.operationState.startedAt
      send:
      - app-status
  trigger.on-sync-failed: |
    - when: app.status?.operationState?.phase in ['Failed', 'Error']
      oncePer: app.status.operationState.startedAt
      send:
      - app-status
  trigger.on-sync-running: |
    - when: app.status?.operationState?.phase == 'Running'
      oncePer: app.status.operationState.startedAt
      send:
      - app-status
  trigger.on-sync-status-unknown: |
    - when: app.status?.sync?.status == 'Unknown'
      send:
      - app-status
  trigger.on-health-degraded: |
    - when: app.status?.health?.status == 'Degraded'
      send:
      - app-status
  trigger.on-deployed: |
    - when: app.status?.operationState?.phase == 'Succeeded' && app.status?.sync?.status == 'Synced' && app.status?.health?.status
        == 'Healthy'
      oncePer: app.status.operationState.startedAt
      send:
      - app-status
```

`?.` 用于处理尚未具有 `status` 或 `operationState` 的 Application。仅 sync 成功并不表示应用程序已就绪。`on-deployed` 要求操作成功且处于**当前 Synced + Healthy**状态，从而排除使用较早成功操作的新 OutOfSync 更改。

### Custom Conditions

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  trigger.on-production-deployed: |
    - when: app.metadata?.labels?.environment == 'production' && app.status?.operationState?.phase == 'Succeeded' &&
        app.status?.sync?.status == 'Synced' && app.status?.health?.status == 'Healthy'
      oncePer: app.status.operationState.startedAt
      send:
      - app-status
  trigger.on-resource-failed: |
    - when: app.status?.resources != nil && any(app.status.resources, {#.health?.status == 'Degraded'})
      send:
      - app-status
  trigger.on-many-images: |
    - when: app.status?.summary?.images != nil && len(app.status.summary.images) > 5
      oncePer: app.metadata.generation
      send:
      - app-status
  trigger.on-long-sync: |
    - when: app.status?.operationState?.phase == 'Running' && app.status.operationState.startedAt != nil && time.Now().Sub(time.Parse(app.status.operationState.startedAt)).Minutes()
        > 10
      oncePer: app.status.operationState.startedAt
      send:
      - app-status
  trigger.on-declared-rollback: |
    - when: 'app.status?.operationState?.phase == ''Succeeded'' && app.status.operationState.operation?.info != nil
        && any(app.status.operationState.operation.info, {#.name == ''release-action'' && #.value == ''rollback''})'
      oncePer: app.status.operationState.startedAt
      send:
      - app-status
  trigger.on-critical-failure: |
    - when: app.status?.operationState?.phase in ['Failed', 'Error'] && app.metadata?.labels?.tier == 'critical'
      oncePer: app.status.operationState.startedAt
      send:
      - app-status
  trigger.on-production-namespace-failure: |
    - when: app.status?.operationState?.phase in ['Failed', 'Error'] && app.spec?.destination?.namespace != nil && app.spec.destination.namespace
        matches '^prod-.*$'
      oncePer: app.status.operationState.startedAt
      send:
      - app-status
  trigger.on-utc-window: |
    - when: app.status?.operationState?.phase == 'Succeeded' && time.Now().UTC().Hour() >= 9 && time.Now().UTC().Hour()
        < 18
      oncePer: app.status.operationState.startedAt
      send:
      - app-status
```

- `summary.images` 统计 image 数量，而非 replica 数量。对 resource 数组使用 `any(...)`，对正则表达式使用 `matches`。
- 时间条件会在 Application 被评估时运行。它们不是精确的十分钟计时器，也不会将通知排队到下一个 UTC 工作时段。
- revision 差异无法证明发生了 rollback。`on-declared-rollback` 读取显式操作信息。在 Git 中审阅恢复更改后，手动 sync 工作流可使用 `argocd app sync my-app --info release-action=rollback`。自动 sync 不会自动添加此标记。

### Sustained OutOfSync Monitoring

最后一次操作的 `finishedAt` 并不是 OutOfSync 开始的时间。对于持续三十分钟的条件，请使用 Prometheus 抓取 Argo CD metrics，并使用如下规则。它要求 Prometheus Operator，以及与 Prometheus `ruleSelector` 配置匹配的 labels/namespaces。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: argocd-sync-alerts
  namespace: monitoring
spec:
  groups:
  - name: argocd-sync
    rules:
    - alert: ArgoCDApplicationOutOfSync
      expr: argocd_app_info{sync_status="OutOfSync"} == 1
      for: 30m
      labels:
        severity: warning
      annotations:
        summary: Application {{ $labels.name }} has remained OutOfSync for 30 minutes
```

## Templates

此通用 template 定义了 Slack、Teams Workflows、HTML email、webhook 和 incident 格式。**Subscription 选择目标位置**；包含 service 格式并不会向所有 provider 广播。仅为失败或 Degraded trigger 订阅 PagerDuty/Opsgenie。此示例不会自动解决 incident。

此 engine 版本使用带有 Sprig 函数的 Go `text/template`。使用 `toJson` 转义 JSON 值，使用 `html` 转义 HTML 值。字段独立渲染，因此每个字段中都声明了局部变量。该 template 可处理缺失的 status、单个 operation revision 和多 source `revisions`。它不会将原始 operation error message 转发到外部 channel。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  template.app-status: |
    message: |
      {{- $status := default (dict) .app.status -}}
      {{- $sync := default (dict) $status.sync -}}
      {{- $health := default (dict) $status.health -}}
      {{- $op := default (dict) $status.operationState -}}
      {{- $result := default (dict) $op.syncResult -}}
      {{- $applied := default (list) $result.revisions -}}
      {{- if and (not $applied) $result.revision -}}{{- $applied = list $result.revision -}}{{- end -}}
      {{- $url := printf "%s/applications/%s/%s" (trimSuffix "/" .context.argocdUrl) .app.metadata.namespace .app.metadata.name -}}
      Application {{.app.metadata.namespace}}/{{.app.metadata.name}}: phase={{default "None" $op.phase}}, sync={{default "Unknown" $sync.status}}, health={{default "Unknown" $health.status}}.
      Details: {{$url}}
    slack:
      attachments: |
        {{- $status := default (dict) .app.status -}}
        {{- $sync := default (dict) $status.sync -}}
        {{- $health := default (dict) $status.health -}}
        {{- $op := default (dict) $status.operationState -}}
        {{- $result := default (dict) $op.syncResult -}}
        {{- $applied := default (list) $result.revisions -}}
        {{- if and (not $applied) $result.revision -}}{{- $applied = list $result.revision -}}{{- end -}}
        {{- $url := printf "%s/applications/%s/%s" (trimSuffix "/" .context.argocdUrl) .app.metadata.namespace .app.metadata.name -}}
        [{
          "color": "#f4c030",
          "title": {{.app.metadata.name | toJson}},
          "title_link": {{$url | toJson}},
          "fields": [
            {"title":"Sync","value":{{default "Unknown" $sync.status | toJson}},"short":true},
            {"title":"Health","value":{{default "Unknown" $health.status | toJson}},"short":true},
            {"title":"Operation revision(s)","value":{{join ", " $applied | toJson}},"short":false}
          ]
        }]
    teams-workflows:
      title: 'Application status changed: {{.app.metadata.name}}'
      text: |-
        {{- $status := default (dict) .app.status -}}
        {{- $sync := default (dict) $status.sync -}}
        {{- $health := default (dict) $status.health -}}
        {{- $op := default (dict) $status.operationState -}}
        {{- $result := default (dict) $op.syncResult -}}
        {{- $applied := default (list) $result.revisions -}}
        {{- if and (not $applied) $result.revision -}}{{- $applied = list $result.revision -}}{{- end -}}
        {{- $url := printf "%s/applications/%s/%s" (trimSuffix "/" .context.argocdUrl) .app.metadata.namespace .app.metadata.name -}}
        Application {{.app.metadata.namespace}}/{{.app.metadata.name}}
        {{$url}}
      themeColor: Accent
      facts: |-
        {{- $status := default (dict) .app.status -}}
        {{- $sync := default (dict) $status.sync -}}
        {{- $health := default (dict) $status.health -}}
        {{- $op := default (dict) $status.operationState -}}
        {{- $result := default (dict) $op.syncResult -}}
        {{- $applied := default (list) $result.revisions -}}
        {{- if and (not $applied) $result.revision -}}{{- $applied = list $result.revision -}}{{- end -}}
        {{- $url := printf "%s/applications/%s/%s" (trimSuffix "/" .context.argocdUrl) .app.metadata.namespace .app.metadata.name -}}
        [{"name":"Sync","value":{{default "Unknown" $sync.status | toJson}}},{"name":"Health","value":{{default "Unknown" $health.status | toJson}}}]
    email:
      subject: '[Argo CD] Application status changed: {{.app.metadata.name}}'
      body: |-
        {{- $status := default (dict) .app.status -}}
        {{- $sync := default (dict) $status.sync -}}
        {{- $health := default (dict) $status.health -}}
        {{- $op := default (dict) $status.operationState -}}
        {{- $result := default (dict) $op.syncResult -}}
        {{- $applied := default (list) $result.revisions -}}
        {{- if and (not $applied) $result.revision -}}{{- $applied = list $result.revision -}}{{- end -}}
        {{- $url := printf "%s/applications/%s/%s" (trimSuffix "/" .context.argocdUrl) .app.metadata.namespace .app.metadata.name -}}
        <h2>Application status changed</h2><p>Application: {{.app.metadata.namespace | html}}/{{.app.metadata.name | html}}</p><p>Sync: {{default "Unknown" $sync.status | html}}; health: {{default "Unknown" $health.status | html}}</p><a href="{{$url | html}}">View in Argo CD</a>
    webhook:
      custom:
        method: POST
        body: |
          {{- $status := default (dict) .app.status -}}
          {{- $sync := default (dict) $status.sync -}}
          {{- $health := default (dict) $status.health -}}
          {{- $op := default (dict) $status.operationState -}}
          {{- $result := default (dict) $op.syncResult -}}
          {{- $applied := default (list) $result.revisions -}}
          {{- if and (not $applied) $result.revision -}}{{- $applied = list $result.revision -}}{{- end -}}
          {{- $url := printf "%s/applications/%s/%s" (trimSuffix "/" .context.argocdUrl) .app.metadata.namespace .app.metadata.name -}}
          {{ dict "event" "application-status" "application" .app.metadata.name "namespace" .app.metadata.namespace "uid" (default "" .app.metadata.uid) "project" (default "default" .app.spec.project) "phase" (default "" $op.phase) "syncStatus" (default "Unknown" $sync.status) "healthStatus" (default "Unknown" $health.status) "appliedRevisions" $applied "operationStartedAt" (default "" $op.startedAt) "url" $url | toJson }}
    pagerdutyv2:
      summary: 'Application status changed: {{.app.metadata.namespace}}/{{.app.metadata.name}}'
      severity: error
      source: argocd
      dedupKey: argocd/{{.app.metadata.namespace}}/{{.app.metadata.name}}/application-status
    opsgenie:
      description: 'Application status changed: {{.app.metadata.namespace}}/{{.app.metadata.name}}'
      priority: P2
      alias: argocd/{{.app.metadata.namespace}}/{{.app.metadata.name}}/application-status
```

`service.email.html: true` 启用 HTML body。Teams 使用 `teams-workflows` 字段和 Adaptive Card color name。`service.webhook.custom` 的 service name 是 **custom**，其 body 位于 `webhook.custom` 下；请显式设置 `POST`。Grafana 对其 annotation 使用通用 `message`。

| Function | Purpose |
|---|---|
| `upper`, `lower` | Change letter case |
| `default`, `dict`, `list` | Defaults and collections |
| `join`, `splitList` | Join/split lists |
| `toJson` | Encode JSON values |
| `html` | Escape HTML special characters |

### GitHub Commit Status

对 commit status 使用独立的 triggers/templates。此示例仅限于一个 HTTPS GitHub source，并且仅在 operation result 标识其 repository 和 revision 时发布。multi-source、Helm/OCI 和 SSH source 需要显式映射。不会发布在记录 result revision 之前发生的失败。`status.label` 提供 GitHub status context；`context` 和 `description` 不是此 template schema 中的字段。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  trigger.on-github-deployed: |
    - when: app.spec?.source?.repoURL != nil && app.spec.source.repoURL startsWith 'https://github.com/' && app.spec?.sources
        == nil && app.status?.operationState?.syncResult?.revision != nil && app.status.operationState.syncResult?.source?.repoURL
        == app.spec.source.repoURL && app.status?.operationState?.phase == 'Succeeded' && app.status?.sync?.status ==
        'Synced' && app.status?.health?.status == 'Healthy'
      oncePer: app.status.operationState.startedAt
      send:
      - github-deployed
  trigger.on-github-failed: |
    - when: app.spec?.source?.repoURL != nil && app.spec.source.repoURL startsWith 'https://github.com/' && app.spec?.sources
        == nil && app.status?.operationState?.syncResult?.revision != nil && app.status.operationState.syncResult?.source?.repoURL
        == app.spec.source.repoURL && app.status?.operationState?.phase in ['Failed', 'Error']
      oncePer: app.status.operationState.startedAt
      send:
      - github-failed
  template.github-deployed: |
    github:
      repoURLPath: '{{.app.status.operationState.syncResult.source.repoURL}}'
      revisionPath: '{{.app.status.operationState.syncResult.revision}}'
      status:
        state: success
        label: argocd/{{.app.metadata.namespace}}/{{.app.metadata.name}}
        targetURL: '{{.context.argocdUrl}}/applications/{{.app.metadata.namespace}}/{{.app.metadata.name}}'
  template.github-failed: |
    github:
      repoURLPath: '{{.app.status.operationState.syncResult.source.repoURL}}'
      revisionPath: '{{.app.status.operationState.syncResult.revision}}'
      status:
        state: failure
        label: argocd/{{.app.metadata.namespace}}/{{.app.metadata.name}}
        targetURL: '{{.context.argocdUrl}}/applications/{{.app.metadata.namespace}}/{{.app.metadata.name}}'
```

## Subscriptions

### Application Annotations

将此 **metadata 片段合并到现有 Application** 中；它不是独立的 Application manifest。匹配每个 service 配置的 recipient name，并选择所需的 subscription。多个 recipient 使用**分号**分隔，而不是逗号。

```yaml
metadata:
  name: my-app
  namespace: argocd
  annotations:
    notifications.argoproj.io/subscribe.on-sync-succeeded.slack: deployments
    notifications.argoproj.io/subscribe.on-sync-failed.slack: deployments;alerts
    notifications.argoproj.io/subscribe.on-health-degraded.slack: alerts
    notifications.argoproj.io/subscribe.on-deployed.teams-workflows: deployments
    notifications.argoproj.io/subscribe.on-sync-failed.email: ops@example.com
    notifications.argoproj.io/subscribe.on-deployed.custom: ''
    notifications.argoproj.io/subscribe.on-github-deployed.github: ''
    notifications.argoproj.io/subscribe.on-github-failed.github: ''
```

### Default Triggers and Global Subscriptions

`defaultTriggers` 为诸如 `notifications.argoproj.io/subscribe.slack: alerts` 的 annotation 提供 trigger name。它不会在每个 Application 上创建 subscription。对于集中管理的 recipient，请使用 `subscriptions`；`selector` 匹配 **Application labels**。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  defaultTriggers: |
    - on-sync-failed
    - on-health-degraded
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

### AppProject Subscriptions

将此 metadata 片段合并到现有 AppProject 中，以涵盖其 Application，同时保留上一章中的 source/destination/RBAC policy。

```yaml
metadata:
  name: production
  namespace: argocd
  annotations:
    notifications.argoproj.io/subscribe.on-sync-failed.slack: production-alerts
    notifications.argoproj.io/subscribe.on-health-degraded.pagerdutyv2: production
```

## Advanced Configuration

### oncePer and Duplicate Handling

`oncePer` 使用表达式的值减少某个条件产生的重复通知。它不是每秒请求数限制，也不保证恰好一次投递。此处的 operation trigger 使用 `operationState.startedAt` 来区分同一 revision 的新 sync 尝试。在接收 service/bridge 处处理 rate limit，并使 webhook/SQS consumer 具有幂等性。

### Console Validation

将组合后的 ConfigMap 保存为 `notifications.yaml`。这些命令通过当前 kubeconfig 读取 Application/AppProject，并显式渲染到 `console:stdout`。实际的 Slack/Teams/GitHub/SQS permission 和投递需要单独的集成测试。

```bash
kubectl get application my-app -n argocd -o yaml > sample-application.yaml
argocd admin notifications trigger run on-deployed ./sample-application.yaml \
  --config-map ./notifications.yaml --secret :empty
argocd admin notifications template notify app-status ./sample-application.yaml \
  --config-map ./notifications.yaml --secret :empty --recipient console:stdout
```

## AWS Integration

### Native SQS Service

此版本提供 `awssqs` service。通用 webhook 中的 AWS API URL 或静态 `Authorization: AWS4-HMAC-SHA256 ...` 字符串不会对 SigV4 request 进行签名。仅有 IRSA/Pod Identity credential 并不会使通用 webhook 具备 signer 感知能力。

首先，在同一 account/region 中预配名为 `argocd-notifications` 的 **Standard queue**，并将 Notifications Controller service account 与 IRSA 或 EKS Pod Identity 关联。SDK default credential chain 可避免在此处使用静态 access key。替换 account/region/queue 值，并合并上方的 `context` 设置。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.awssqs: |
    queue: argocd-notifications
    region: ap-northeast-2
    account: '123456789012'
  trigger.on-aws-sync-completed: |
    - when: app.status?.operationState?.phase in ['Succeeded', 'Failed', 'Error']
      oncePer: app.status.operationState.startedAt
      send:
      - aws-app-event
  template.aws-app-event: |
    message: |
      {{- $status := default (dict) .app.status -}}
      {{- $sync := default (dict) $status.sync -}}
      {{- $health := default (dict) $status.health -}}
      {{- $op := default (dict) $status.operationState -}}
      {{- $result := default (dict) $op.syncResult -}}
      {{- $applied := default (list) $result.revisions -}}
      {{- if and (not $applied) $result.revision -}}{{- $applied = list $result.revision -}}{{- end -}}
      {{- $url := printf "%s/applications/%s/%s" (trimSuffix "/" .context.argocdUrl) .app.metadata.namespace .app.metadata.name -}}
      {{ dict "event" "sync-completed" "application" .app.metadata.name "namespace" .app.metadata.namespace "uid" (default "" .app.metadata.uid) "project" (default "default" .app.spec.project) "phase" (default "" $op.phase) "syncStatus" (default "Unknown" $sync.status) "healthStatus" (default "Unknown" $health.status) "appliedRevisions" $applied "operationStartedAt" (default "" $op.startedAt) "url" $url | toJson }}
```

假定使用 SQS 托管加密时，以下为 controller role 的示例发送方 permission。客户管理的 KMS key 还需要相应的 key policy 和 KMS permission。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sqs:GetQueueUrl",
        "sqs:SendMessage"
      ],
      "Resource": "arn:aws:sqs:ap-northeast-2:123456789012:argocd-notifications"
    }
  ]
}
```

将此条目添加到现有 Application 的 annotation 中。recipient 是 queue name，并会覆盖 service 的默认 queue。

```yaml
metadata:
  annotations:
    notifications.argoproj.io/subscribe.on-aws-sync-completed.awssqs: argocd-notifications
```

捆绑的 engine 会在 `SendMessage` 上设置十秒延迟。FIFO queue 不支持逐消息延迟，因此请勿在此示例中替换为 FIFO queue。不要假定配置的 `messageAttributes` 会被发送；请在 JSON message body 中包含所需 metadata。

### Lambda, SNS, and EventBridge Integration

受支持的集成路径是 **Notifications → SQS → Lambda → SNS or EventBridge**。请单独实现和部署下游 resource；ConfigMap 不会创建它们。

| Hop | Required configuration |
|---|---|
| SQS → Lambda | Same-region event source mapping; receive/delete/queue-attribute permissions; visibility timeout sized for processing; retries/DLQ |
| Lambda → SNS | Execution-role `sns:Publish` permission on the target topic; signed AWS SDK call |
| Lambda → EventBridge | `events:PutEvents` on the target bus; inspect `FailedEntryCount` and individual entry errors |
| Consumer | JSON validation; idempotency key considering Application UID, event, operationStartedAt and current status; SQS partial batch failure response configuration |

如果需要 API Gateway webhook，请构建单独进行身份验证的 bridge。仅有 API key/usage plan 并不构成身份验证。本章的审阅没有预配 AWS resource 或发送真实 message。

## References

- [Notifications](https://argo-cd.readthedocs.io/en/release-3.5/operator-manual/notifications/)
- [Triggers](https://argo-cd.readthedocs.io/en/release-3.5/operator-manual/notifications/triggers/)
- [Subscriptions](https://argo-cd.readthedocs.io/en/release-3.5/operator-manual/notifications/subscriptions/)
- [Teams Workflows](https://argo-cd.readthedocs.io/en/release-3.5/operator-manual/notifications/services/teams-workflows/)
- [Engine template implementation](https://github.com/argoproj/notifications-engine/blob/0cff13b8a717/pkg/templates/service.go)
- [Engine SQS implementation](https://github.com/argoproj/notifications-engine/blob/0cff13b8a717/pkg/services/awssqs.go)
- [Lambda with SQS](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html)

## Quiz

使用[通知测验](../../quizzes/gitops/argocd/08-notifications-quiz.md)测试你的理解。
