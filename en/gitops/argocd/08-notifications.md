# ArgoCD Notifications

> **Supported Versions**: ArgoCD v2.9+, ArgoCD Notifications v1.2+
> **Last Updated**: February 22, 2026

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

ArgoCD Notifications is a component that monitors ArgoCD applications and sends notifications when certain conditions are met. It supports multiple notification services and provides flexible templating.

### Key Features

| Feature | Description |
|---------|-------------|
| Multiple Services | Slack, Teams, Email, Webhook, GitHub, and more |
| Flexible Triggers | Condition-based notification triggers |
| Go Templates | Rich template syntax for message formatting |
| Subscription Model | Per-application notification subscriptions |
| Built-in Triggers | Pre-configured triggers for common events |

## Architecture

![Flow diagram of ArgoCD's notification pipeline: the Application Controller watches Applications, hands events to the Notifications Controller which watches apps and evaluates trigger conditions, and once a trigger matches, dispatches messages out to Slack, Teams, Email, a webhook, and GitHub.](../../../assets/diagrams/rendered/en-gitops-argocd-08-notifications-0.svg)

### Installation

ArgoCD Notifications is included in ArgoCD v2.4+. For older versions:

```bash
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/notifications_catalog/install.yaml
```

## Notification Services

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

Slack Bot Setup:
1. Create a Slack App at https://api.slack.com/apps
2. Add OAuth scopes: `chat:write`, `chat:write.public`
3. Install app to workspace
4. Copy Bot User OAuth Token

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

## Triggers

Triggers define when to send notifications based on application state.

### Built-in Triggers

| Trigger | Description |
|---------|-------------|
| `on-created` | Application is created |
| `on-deleted` | Application is deleted |
| `on-deployed` | Application is synced and healthy |
| `on-health-degraded` | Application health is degraded |
| `on-sync-failed` | Sync operation failed |
| `on-sync-running` | Sync operation started |
| `on-sync-status-unknown` | Sync status is unknown |
| `on-sync-succeeded` | Sync operation succeeded |

### Custom Triggers

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

### Trigger Conditions

Triggers use expr language for conditions:

```yaml
trigger.custom: |
  - when: |
      app.status.health.status == 'Degraded' and
      app.metadata.labels.tier == 'critical' and
      time.Now().Hour() >= 9 and time.Now().Hour() < 17
    send: [critical-alert]
```

Available fields:
- `app.metadata.*` - Application metadata
- `app.spec.*` - Application spec
- `app.status.*` - Application status
- `app.operation.*` - Current operation
- `time.Now()` - Current time

## Templates

Templates define the notification message format using Go templates.

### Slack Template

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

### Teams Template

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

### Email Template

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

### GitHub Commit Status Template

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

### Template Functions

Available functions in templates:

| Function | Description |
|----------|-------------|
| `substr start end` | Substring |
| `toUpper` | Convert to uppercase |
| `toLower` | Convert to lowercase |
| `replace old new` | Replace string |
| `split delimiter` | Split string |
| `join delimiter` | Join array |
| `first` | First element |
| `last` | Last element |
| `default value` | Default if empty |
| `indent spaces` | Indent text |
| `nindent spaces` | Newline + indent |

## Subscriptions

### Application-Level Subscriptions

Add annotations to applications:

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

### Default Subscriptions

Configure default subscriptions for all applications:

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

### Project-Level Subscriptions

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

## Advanced Configuration

### Context Variables

Add custom context variables:

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

Use in templates:

```yaml
template.custom: |
  message: |
    Environment: {{.context.environment}}
    Team: {{.context.team}}
```

### Conditional Notifications

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

### Rate Limiting with oncePer

Prevent duplicate notifications:

```yaml
trigger.on-sync-status-change: |
  - when: app.status.sync.status != 'Synced'
    send: [sync-status-change]
    oncePer: app.status.sync.revision
```

## AWS Integration

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

### Complete AWS Notification Setup

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

## Quiz

To test what you've learned, try the [ArgoCD notifications quiz](../../quizzes/gitops/argocd/08-notifications-quiz.md).
