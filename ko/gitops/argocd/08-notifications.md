# ArgoCD 알림

> **지원 버전**: ArgoCD v2.9+
> **마지막 업데이트**: 2025년 2월 21일

## 목차

- [ArgoCD Notifications 개요](#argocd-notifications-개요)
- [알림 서비스](#알림-서비스)
- [트리거 구성](#트리거-구성)
- [템플릿](#템플릿)
- [구독 설정](#구독-설정)
- [AWS 통합](#aws-통합)

## ArgoCD Notifications 개요

ArgoCD Notifications Controller는 Application 이벤트를 다양한 서비스로 전송합니다.

```mermaid
flowchart LR
    subgraph ArgoCD ["ArgoCD"]
        App[Application]
        Controller[Notifications<br/>Controller]
    end

    subgraph Services ["알림 서비스"]
        Slack[Slack]
        Teams[Microsoft Teams]
        Email[Email]
        Webhook[Webhook]
        GitHub[GitHub]
    end

    App -->|이벤트| Controller
    Controller --> Slack
    Controller --> Teams
    Controller --> Email
    Controller --> Webhook
    Controller --> GitHub

    style Controller fill:#EB6E85,stroke:#333,color:#fff
```

### 아키텍처

| 구성 요소 | 설명 |
|-----------|------|
| **Trigger** | 알림을 발생시키는 조건 |
| **Template** | 알림 메시지 형식 |
| **Service** | 알림 대상 (Slack, Email 등) |
| **Subscription** | Application과 알림 연결 |

## 알림 서비스

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
    # 또는 Webhook 사용
    # signingSecret: $slack-signing-secret
---
apiVersion: v1
kind: Secret
metadata:
  name: argocd-notifications-secret
  namespace: argocd
type: Opaque
stringData:
  slack-token: xoxb-xxxxxxxxxx-xxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx
```

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
      devops-channel: https://myorg.webhook.office.com/webhookb2/xxx/IncomingWebhook/xxx
      alerts-channel: https://myorg.webhook.office.com/webhookb2/yyy/IncomingWebhook/yyy
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
    host: smtp.gmail.com
    port: 587
    from: argocd@example.com
    username: $email-username
    password: $email-password
---
apiVersion: v1
kind: Secret
metadata:
  name: argocd-notifications-secret
  namespace: argocd
type: Opaque
stringData:
  email-username: argocd@example.com
  email-password: your-app-password
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
    url: https://api.example.com/webhook
    headers:
      - name: Authorization
        value: Bearer $webhook-token
      - name: Content-Type
        value: application/json
```

### GitHub

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
    privateKey: $github-private-key
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
      default: $pagerduty-service-key
```

### Opsgenie

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.opsgenie: |
    apiUrl: https://api.opsgenie.com
    apiKeys:
      default: $opsgenie-api-key
```

## 트리거 구성

### 내장 트리거

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  # 동기화 성공
  trigger.on-sync-succeeded: |
    - when: app.status.operationState.phase in ['Succeeded']
      send: [app-sync-succeeded]

  # 동기화 실패
  trigger.on-sync-failed: |
    - when: app.status.operationState.phase in ['Error', 'Failed']
      send: [app-sync-failed]

  # 동기화 실행 중
  trigger.on-sync-running: |
    - when: app.status.operationState.phase in ['Running']
      send: [app-sync-running]

  # 동기화 상태 변경
  trigger.on-sync-status-unknown: |
    - when: app.status.sync.status == 'Unknown'
      send: [app-sync-status-unknown]

  # 헬스 상태 변경
  trigger.on-health-degraded: |
    - when: app.status.health.status == 'Degraded'
      send: [app-health-degraded]

  # 배포됨
  trigger.on-deployed: |
    - when: app.status.operationState.phase in ['Succeeded'] and app.status.health.status == 'Healthy'
      send: [app-deployed]
```

### 커스텀 트리거

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  # 프로덕션 배포 알림
  trigger.on-production-deployed: |
    - when: app.metadata.labels.environment == 'production' and app.status.operationState.phase == 'Succeeded'
      send: [production-deployed]
      oncePer: app.status.sync.revision

  # 장시간 OutOfSync
  trigger.on-long-out-of-sync: |
    - when: app.status.sync.status == 'OutOfSync' and time.Now().Sub(time.Parse(app.status.operationState.finishedAt)).Minutes() > 30
      send: [long-out-of-sync-warning]

  # 특정 리소스 실패
  trigger.on-resource-failed: |
    - when: app.status.resources[].health.status == 'Degraded'
      send: [resource-degraded]

  # 롤백 감지
  trigger.on-rollback: |
    - when: app.status.operationState.operation.sync.revision != app.status.sync.revision and app.status.operationState.phase == 'Succeeded'
      send: [rollback-completed]
```

### 조건 표현식

```yaml
# 복합 조건
trigger.complex-condition: |
  - when: |
      app.metadata.labels.team == 'platform' and
      app.status.operationState.phase == 'Failed' and
      app.spec.destination.namespace =~ 'prod-.*'
    send: [platform-prod-failure]

# 시간 기반 조건
trigger.business-hours-only: |
  - when: |
      app.status.operationState.phase == 'Succeeded' and
      time.Now().Hour() >= 9 and time.Now().Hour() <= 18
    send: [business-hours-deployment]
```

## 템플릿

### Slack 템플릿

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  template.app-sync-succeeded: |
    message: |
      Application {{.app.metadata.name}} has been successfully synced.
    slack:
      attachments: |
        [{
          "color": "#18be52",
          "title": "{{ .app.metadata.name }}",
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
          ],
          "footer": "ArgoCD",
          "footer_icon": "https://argo-cd.readthedocs.io/en/stable/assets/logo.png"
        }]

  template.app-sync-failed: |
    message: |
      Application {{.app.metadata.name}} sync failed.
    slack:
      attachments: |
        [{
          "color": "#E96D76",
          "title": "{{ .app.metadata.name }} - Sync Failed",
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
              "title": "Error Message",
              "value": "{{.app.status.operationState.message}}",
              "short": false
            }
          ]
        }]

  template.app-health-degraded: |
    message: |
      Application {{.app.metadata.name}} health is degraded.
    slack:
      attachments: |
        [{
          "color": "#f4c030",
          "title": "{{ .app.metadata.name }} - Health Degraded",
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

### Email 템플릿

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  template.app-sync-succeeded-email: |
    email:
      subject: "[ArgoCD] Application {{.app.metadata.name}} Synced Successfully"
      body: |
        <!DOCTYPE html>
        <html>
        <head>
          <style>
            body { font-family: Arial, sans-serif; }
            .success { color: #18be52; }
            .info { background: #f5f5f5; padding: 10px; border-radius: 5px; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #4CAF50; color: white; }
          </style>
        </head>
        <body>
          <h2 class="success">Sync Successful</h2>
          <div class="info">
            <table>
              <tr>
                <th>Application</th>
                <td>{{.app.metadata.name}}</td>
              </tr>
              <tr>
                <th>Project</th>
                <td>{{.app.spec.project}}</td>
              </tr>
              <tr>
                <th>Revision</th>
                <td>{{.app.status.sync.revision}}</td>
              </tr>
              <tr>
                <th>Repository</th>
                <td>{{.app.spec.source.repoURL}}</td>
              </tr>
              <tr>
                <th>Namespace</th>
                <td>{{.app.spec.destination.namespace}}</td>
              </tr>
            </table>
          </div>
          <p>
            <a href="{{.context.argocdUrl}}/applications/{{.app.metadata.name}}">
              View in ArgoCD
            </a>
          </p>
        </body>
        </html>
```

### Teams 템플릿

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  template.app-sync-succeeded-teams: |
    teams:
      title: "Application Synced: {{.app.metadata.name}}"
      text: "Sync completed successfully"
      sections: |
        [{
          "activityTitle": "{{.app.metadata.name}}",
          "facts": [
            {
              "name": "Sync Status",
              "value": "{{.app.status.sync.status}}"
            },
            {
              "name": "Health",
              "value": "{{.app.status.health.status}}"
            },
            {
              "name": "Revision",
              "value": "{{.app.status.sync.revision | substr 0 7}}"
            }
          ],
          "markdown": true
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

### Webhook 템플릿

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  template.app-sync-webhook: |
    webhook:
      custom:
        method: POST
        body: |
          {
            "event": "sync",
            "application": "{{.app.metadata.name}}",
            "project": "{{.app.spec.project}}",
            "status": "{{.app.status.operationState.phase}}",
            "revision": "{{.app.status.sync.revision}}",
            "health": "{{.app.status.health.status}}",
            "timestamp": "{{.app.status.operationState.finishedAt}}",
            "url": "{{.context.argocdUrl}}/applications/{{.app.metadata.name}}"
          }
```

### GitHub 템플릿 (커밋 상태)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  template.app-deployed-github: |
    github:
      status:
        state: success
        label: "argocd/{{.app.metadata.name}}"
        targetURL: "{{.context.argocdUrl}}/applications/{{.app.metadata.name}}"

  template.app-sync-failed-github: |
    github:
      status:
        state: failure
        label: "argocd/{{.app.metadata.name}}"
        targetURL: "{{.context.argocdUrl}}/applications/{{.app.metadata.name}}"
```

## 구독 설정

### Application 어노테이션

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
  annotations:
    # Slack 채널 구독
    notifications.argoproj.io/subscribe.on-sync-succeeded.slack: my-channel
    notifications.argoproj.io/subscribe.on-sync-failed.slack: alerts-channel
    notifications.argoproj.io/subscribe.on-health-degraded.slack: alerts-channel

    # Teams 채널 구독
    notifications.argoproj.io/subscribe.on-sync-succeeded.teams: devops-channel
    notifications.argoproj.io/subscribe.on-sync-failed.teams: alerts-channel

    # Email 구독
    notifications.argoproj.io/subscribe.on-sync-failed.email: team@example.com

    # Webhook 구독
    notifications.argoproj.io/subscribe.on-deployed.webhook.custom: ""

    # GitHub 상태 구독
    notifications.argoproj.io/subscribe.on-sync-succeeded.github: ""
    notifications.argoproj.io/subscribe.on-sync-failed.github: ""
spec:
  project: default
  source:
    repoURL: https://github.com/myorg/myapp.git
    targetRevision: main
    path: manifests
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
```

### 기본 구독 (모든 Application)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  # 기본 트리거 및 구독
  defaultTriggers: |
    - on-sync-succeeded
    - on-sync-failed
    - on-health-degraded

  subscriptions: |
    - recipients:
        - slack:alerts
      triggers:
        - on-sync-failed
        - on-health-degraded
    - recipients:
        - slack:deployments
      triggers:
        - on-sync-succeeded
```

### 프로젝트별 구독

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: production
  namespace: argocd
  annotations:
    # 프로젝트 레벨 구독
    notifications.argoproj.io/subscribe.on-sync-failed.slack: production-alerts
    notifications.argoproj.io/subscribe.on-health-degraded.pagerduty: default
spec:
  description: Production applications
```

## AWS 통합

### Amazon SNS

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.webhook.sns: |
    url: https://sns.ap-northeast-2.amazonaws.com
    headers:
      - name: X-Amz-Date
        value: "{{.timestamp}}"
      - name: Authorization
        value: "AWS4-HMAC-SHA256 ..."  # IRSA 사용 권장

  template.sns-notification: |
    webhook:
      sns:
        method: POST
        body: |
          Action=Publish
          &TopicArn=arn:aws:sns:ap-northeast-2:123456789012:argocd-notifications
          &Message={{.app.metadata.name}} sync {{.app.status.operationState.phase}}
```

### Amazon EventBridge

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.webhook.eventbridge: |
    url: https://events.ap-northeast-2.amazonaws.com
    headers:
      - name: Content-Type
        value: application/x-amz-json-1.1
      - name: X-Amz-Target
        value: AWSEvents.PutEvents

  template.eventbridge-notification: |
    webhook:
      eventbridge:
        method: POST
        body: |
          {
            "Entries": [{
              "Source": "argocd",
              "DetailType": "Application Sync",
              "Detail": "{\"application\": \"{{.app.metadata.name}}\", \"status\": \"{{.app.status.operationState.phase}}\"}",
              "EventBusName": "default"
            }]
          }
```

### Lambda 트리거

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.webhook.lambda: |
    url: https://lambda.ap-northeast-2.amazonaws.com/2015-03-31/functions/argocd-handler/invocations
    headers:
      - name: Content-Type
        value: application/json

  template.lambda-invoke: |
    webhook:
      lambda:
        method: POST
        body: |
          {
            "event": "sync",
            "application": "{{.app.metadata.name}}",
            "project": "{{.app.spec.project}}",
            "status": "{{.app.status.operationState.phase}}",
            "revision": "{{.app.status.sync.revision}}",
            "health": "{{.app.status.health.status}}"
          }
```

## 다음 단계

1. **[모범 사례](09-best-practices.md)**: 알림 구성 모범 사례를 학습하세요.

2. **[보안](07-security.md)**: 알림 시크릿을 안전하게 관리하세요.

3. **[프로젝트와 RBAC](06-projects-rbac.md)**: 프로젝트별 알림을 구성하세요.

## 참고 자료

- [ArgoCD Notifications](https://argo-cd.readthedocs.io/en/stable/operator-manual/notifications/)
- [Notification Services](https://argo-cd.readthedocs.io/en/stable/operator-manual/notifications/services/overview/)
- [Notification Templates](https://argo-cd.readthedocs.io/en/stable/operator-manual/notifications/templates/)
- [Notification Triggers](https://argo-cd.readthedocs.io/en/stable/operator-manual/notifications/triggers/)

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [알림 퀴즈](../../quizzes/gitops/argocd/08-notifications-quiz.md)를 풀어보세요.
