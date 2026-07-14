# Grafana OnCall

> **最終更新**: February 20, 2026

## 目次

- [Grafana OnCall の概要](#grafana-oncall-overview)
- [アーキテクチャ](#architecture)
- [インストール](#installation)
- [統合のセットアップ](#integration-setup)
- [オンコールスケジュールの設定](#on-call-schedule-configuration)
- [エスカレーションチェーン](#escalation-chains)
- [アラートのグループ化とルーティング](#alert-grouping-and-routing)
- [ChatOps 統合](#chatops-integration)
- [Grafana IRM 統合](#grafana-irm-integration)
- [モバイルアプリ](#mobile-app)
- [PagerDuty/OpsGenie の比較](#pagerdutyopsgenie-comparison)
- [ベストプラクティス](#best-practices)

---

## Grafana OnCall の概要

Grafana OnCall は、アラートルーティング、オンコールスケジュール管理、エスカレーションポリシーを提供するオープンソースのオンコール管理ツールです。Grafana Cloud を通じて SaaS として利用することも、セルフホストすることもできます。

### 主な機能

1. **オンコールスケジュール管理**: ローテーション、オーバーライド、休暇管理
2. **エスカレーションチェーン**: 時間ベースの自動エスカレーション
3. **アラートのグループ化**: 関連するアラートを集約
4. **さまざまな統合**: Alertmanager、Grafana、CloudWatch、Webhook
5. **ChatOps**: Slack、MS Teams、Telegram との統合
6. **モバイルアプリ**: iOS/Android のプッシュ通知

### Grafana OnCall vs PagerDuty vs OpsGenie

| Feature | Grafana OnCall | PagerDuty | OpsGenie |
|---------|----------------|-----------|----------|
| **Type** | Open Source/SaaS | SaaS | SaaS |
| **Cost** | Free(OSS)/Paid(Cloud) | Paid | Paid |
| **Self-Hosting** | Yes | No | No |
| **Grafana Integration** | Native | Plugin | Plugin |
| **On-Call Schedule** | Yes | Advanced | Advanced |
| **Escalation** | Yes | Advanced | Advanced |
| **Analytics/Reporting** | Basic | Advanced | Advanced |
| **Enterprise Support** | Paid | Included | Included |

---

## アーキテクチャ

### Grafana OnCall のコンポーネント

```mermaid
graph TB
    subgraph Sources["Alert Sources"]
        AM[Alertmanager]
        GA[Grafana Alerting]
        CW[CloudWatch]
        WH[Webhook]
    end

    subgraph OnCall["Grafana OnCall"]
        subgraph Core["Core Components"]
            API[API Server]
            Engine[Alert Engine]
            Scheduler[Scheduler]
        end

        subgraph Data["Data Storage"]
            DB[(PostgreSQL)]
            Redis[(Redis)]
            Celery[Celery Workers]
        end

        subgraph Features["Features"]
            Routes[Routes]
            Escalation[Escalation Chains]
            Schedules[Schedules]
            Groups[Alert Groups]
        end
    end

    subgraph Notifications["Notification Channels"]
        Slack[Slack]
        Teams[MS Teams]
        Phone[Phone Call]
        SMS[SMS]
        Email[Email]
        Mobile[Mobile App]
    end

    AM --> API
    GA --> API
    CW --> API
    WH --> API

    API --> Engine
    Engine --> Routes
    Routes --> Escalation
    Escalation --> Schedules
    Schedules --> Groups

    Engine --> DB
    Engine --> Redis
    Celery --> Redis

    Groups --> Slack
    Groups --> Teams
    Groups --> Phone
    Groups --> SMS
    Groups --> Email
    Groups --> Mobile

    style Core fill:#ff5722,color:#ffffff
    style Data fill:#2196f3,color:#ffffff
    style Features fill:#4caf50,color:#ffffff
```

### アラート処理フロー

```mermaid
sequenceDiagram
    participant S as Alert Source
    participant O as OnCall
    participant R as Route
    participant E as Escalation Chain
    participant SC as Schedule
    participant N as Notification

    S->>O: Alert received
    O->>O: Alert grouping
    O->>R: Evaluate routing rules
    R->>E: Select escalation chain
    E->>SC: Query current on-call responder
    SC-->>E: Responder info
    E->>N: Send notification

    alt No response
        E->>E: Wait time elapsed
        E->>SC: Query next responder
        SC-->>E: Next responder
        E->>N: Escalation notification
    end

    N->>O: Responder acknowledges
    O->>S: Status update
```

---

## インストール

### Helm を使用したインストール（EKS）

```bash
# Add Helm repository
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Create namespace
kubectl create namespace oncall

# Install after creating values.yaml
helm install oncall grafana/oncall \
  --namespace oncall \
  -f oncall-values.yaml
```

### 基本的な values.yaml 設定

```yaml
# oncall-values.yaml
base_url: oncall.example.com

# Database settings
database:
  type: postgresql

postgresql:
  enabled: true
  auth:
    database: oncall
    username: oncall
    password: "secure-password"
  primary:
    persistence:
      enabled: true
      size: 10Gi

# Redis settings
redis:
  enabled: true
  architecture: standalone
  auth:
    enabled: true
    password: "redis-password"

# Celery workers
celery:
  replicaCount: 2
  resources:
    requests:
      memory: 256Mi
      cpu: 100m
    limits:
      memory: 512Mi
      cpu: 500m

# API server
oncall:
  replicaCount: 2
  resources:
    requests:
      memory: 512Mi
      cpu: 200m
    limits:
      memory: 1Gi
      cpu: 1000m

# Ingress settings
ingress:
  enabled: true
  className: alb
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:ap-northeast-2:xxx:certificate/xxx
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
  hosts:
    - host: oncall.example.com
      paths:
        - path: /
          pathType: Prefix

# Grafana integration
grafana:
  enabled: false  # When using existing Grafana

# Environment variables
env:
  - name: SECRET_KEY
    valueFrom:
      secretKeyRef:
        name: oncall-secrets
        key: secret-key
  - name: DJANGO_SETTINGS_MODULE
    value: settings.hobby
```

### 本番用 values.yaml

```yaml
# oncall-production-values.yaml
base_url: oncall.example.com

# External PostgreSQL (RDS)
database:
  type: postgresql

externalPostgresql:
  host: oncall-db.xxx.ap-northeast-2.rds.amazonaws.com
  port: 5432
  db: oncall
  user: oncall
  password:
    secretName: oncall-db-secret
    secretKey: password

postgresql:
  enabled: false

# External Redis (ElastiCache)
externalRedis:
  host: oncall-redis.xxx.cache.amazonaws.com
  port: 6379
  password:
    secretName: oncall-redis-secret
    secretKey: password

redis:
  enabled: false

# Celery workers (HA)
celery:
  replicaCount: 3
  resources:
    requests:
      memory: 512Mi
      cpu: 250m
    limits:
      memory: 1Gi
      cpu: 1000m
  affinity:
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 100
          podAffinityTerm:
            labelSelector:
              matchLabels:
                app.kubernetes.io/component: celery
            topologyKey: kubernetes.io/hostname

# API server (HA)
oncall:
  replicaCount: 3
  resources:
    requests:
      memory: 1Gi
      cpu: 500m
    limits:
      memory: 2Gi
      cpu: 2000m
  affinity:
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 100
          podAffinityTerm:
            labelSelector:
              matchLabels:
                app.kubernetes.io/component: oncall
            topologyKey: kubernetes.io/hostname

# Telegram/Twilio settings (for phone/SMS)
telegramPolling:
  enabled: true

twilio:
  enabled: true
  accountSid:
    secretName: twilio-secret
    secretKey: account-sid
  authToken:
    secretName: twilio-secret
    secretKey: auth-token
  phoneNumber:
    secretName: twilio-secret
    secretKey: phone-number
```

### Secret の作成

```bash
# OnCall secrets
kubectl create secret generic oncall-secrets \
  --namespace oncall \
  --from-literal=secret-key=$(openssl rand -base64 32)

# Database secret
kubectl create secret generic oncall-db-secret \
  --namespace oncall \
  --from-literal=password='db-password'

# Redis secret
kubectl create secret generic oncall-redis-secret \
  --namespace oncall \
  --from-literal=password='redis-password'

# Twilio secret (for phone/SMS)
kubectl create secret generic twilio-secret \
  --namespace oncall \
  --from-literal=account-sid='ACxxx' \
  --from-literal=auth-token='xxx' \
  --from-literal=phone-number='+1234567890'
```

---

## 統合のセットアップ

### Alertmanager 統合

```yaml
# Alertmanager configuration
receivers:
  - name: 'grafana-oncall'
    webhook_configs:
      - url: 'https://oncall.example.com/api/v1/webhook/<integration-id>/'
        send_resolved: true
        http_config:
          bearer_token: '<integration-token>'

route:
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'grafana-oncall'
    - match:
        severity: warning
      receiver: 'grafana-oncall'
```

### Grafana Alerting 統合

```yaml
# Grafana alerting configuration (grafana.ini)
[unified_alerting]
enabled = true

[alerting]
enabled = false

# Contact Point setup (in Grafana UI)
# 1. Alerting > Contact points
# 2. New contact point
# 3. Integration: Grafana OnCall
# 4. URL: https://oncall.example.com
# 5. Select Integration
```

### CloudWatch 統合

```bash
# Create SNS Topic
aws sns create-topic --name cloudwatch-to-oncall

# SNS subscription (OnCall Webhook)
aws sns subscribe \
  --topic-arn arn:aws:sns:ap-northeast-2:123456789012:cloudwatch-to-oncall \
  --protocol https \
  --notification-endpoint https://oncall.example.com/api/v1/webhook/<integration-id>/

# Connect CloudWatch Alarm to SNS
aws cloudwatch put-metric-alarm \
  --alarm-name "HighCPU" \
  --alarm-actions arn:aws:sns:ap-northeast-2:123456789012:cloudwatch-to-oncall \
  ...
```

### Webhook 統合

```python
# Custom alert sending example
import requests

webhook_url = "https://oncall.example.com/api/v1/webhook/<integration-id>/"
token = "<integration-token>"

alert = {
    "alert_uid": "unique-alert-id",
    "title": "High CPU Usage",
    "message": "CPU usage is above 90% on production server",
    "state": "alerting",  # alerting, ok
    "severity": "critical",  # critical, warning, info
    "link": "https://grafana.example.com/d/xxx",
    "labels": {
        "environment": "production",
        "service": "api-server"
    }
}

response = requests.post(
    webhook_url,
    json=alert,
    headers={"Authorization": f"Bearer {token}"}
)
```

---

## オンコールスケジュールの設定

### スケジュールの概念

```mermaid
graph TB
    subgraph Schedule["On-Call Schedule"]
        subgraph Rotation["Rotation"]
            R1[Day Rotation]
            R2[Night Rotation]
        end

        subgraph Layers["Layers"]
            L1[Primary Responder]
            L2[Secondary Responder]
            L3[Backup Responder]
        end

        subgraph Override["Override"]
            O1[Vacation Replacement]
            O2[Temporary Change]
        end
    end

    R1 --> L1
    R2 --> L1
    L1 --> Final[Final Schedule]
    L2 --> Final
    L3 --> Final
    O1 --> Final
    O2 --> Final

    style Schedule fill:#e3f2fd
```

### スケジュールの作成（API）

```bash
# Create schedule
curl -X POST https://oncall.example.com/api/v1/schedules/ \
  -H "Authorization: Bearer <api-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "SRE Team On-Call",
    "team_id": "<team-id>",
    "time_zone": "Asia/Seoul",
    "type": "web",
    "shifts": [
      {
        "type": "rolling_users",
        "start": "2025-02-17T09:00:00",
        "duration": 604800,
        "frequency": "weekly",
        "interval": 1,
        "rolling_users": [
          ["<user-id-1>"],
          ["<user-id-2>"],
          ["<user-id-3>"]
        ]
      }
    ]
  }'
```

### ローテーションのタイプ

```yaml
# Weekly rotation
weekly-rotation:
  type: rolling_users
  start: "2025-02-17T09:00:00"
  duration: 604800  # 7 days (seconds)
  frequency: weekly
  interval: 1
  rolling_users:
    - [user-1]
    - [user-2]
    - [user-3]

# Daily rotation
daily-rotation:
  type: rolling_users
  start: "2025-02-17T09:00:00"
  duration: 86400  # 1 day (seconds)
  frequency: daily
  interval: 1
  rolling_users:
    - [user-1]
    - [user-2]

# Shift rotation (8 hours x 3)
shift-rotation:
  shifts:
    - type: rolling_users
      start: "2025-02-17T00:00:00"
      duration: 28800  # 8 hours
      frequency: daily
      rolling_users:
        - [night-shift-1]
        - [night-shift-2]
    - type: rolling_users
      start: "2025-02-17T08:00:00"
      duration: 28800
      frequency: daily
      rolling_users:
        - [day-shift-1]
        - [day-shift-2]
    - type: rolling_users
      start: "2025-02-17T16:00:00"
      duration: 28800
      frequency: daily
      rolling_users:
        - [evening-shift-1]
        - [evening-shift-2]
```

### オーバーライド設定

```bash
# Change responder for specific period
curl -X POST https://oncall.example.com/api/v1/schedules/<schedule-id>/overrides/ \
  -H "Authorization: Bearer <api-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "start": "2025-02-25T09:00:00+09:00",
    "end": "2025-02-28T09:00:00+09:00",
    "user_id": "<replacement-user-id>"
  }'
```

---

## エスカレーションチェーン

### エスカレーションチェーンの構造

```mermaid
graph TB
    A[Alert Fired] --> B[Step 1: Current On-Call]

    B --> C{Response<br/>within 15min?}
    C -->|Yes| D[Alert Resolved]
    C -->|No| E[Step 2: Secondary On-Call]

    E --> F{Response<br/>within 15min?}
    F -->|Yes| D
    F -->|No| G[Step 3: Team Lead]

    G --> H{Response<br/>within 15min?}
    H -->|Yes| D
    H -->|No| I[Step 4: Entire Team]

    style B fill:#4caf50
    style E fill:#ff9800
    style G fill:#f44336
    style I fill:#9c27b0
```

### エスカレーションチェーンの作成

```bash
# Create escalation chain
curl -X POST https://oncall.example.com/api/v1/escalation_chains/ \
  -H "Authorization: Bearer <api-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Critical",
    "team_id": "<team-id>"
  }'

# Add escalation policy
curl -X POST https://oncall.example.com/api/v1/escalation_policies/ \
  -H "Authorization: Bearer <api-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "escalation_chain_id": "<chain-id>",
    "position": 0,
    "type": "notify_on_call_from_schedule",
    "notify_on_call_from_schedule": "<schedule-id>",
    "important": true
  }'

# Add wait step
curl -X POST https://oncall.example.com/api/v1/escalation_policies/ \
  -H "Authorization: Bearer <api-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "escalation_chain_id": "<chain-id>",
    "position": 1,
    "type": "wait",
    "duration": 900
  }'

# Add secondary escalation
curl -X POST https://oncall.example.com/api/v1/escalation_policies/ \
  -H "Authorization: Bearer <api-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "escalation_chain_id": "<chain-id>",
    "position": 2,
    "type": "notify_persons",
    "persons_to_notify": ["<user-id-1>", "<user-id-2>"],
    "important": true
  }'
```

### エスカレーションポリシーのタイプ

```yaml
escalation-policy-types:
  # Notify current on-call from schedule
  - type: notify_on_call_from_schedule
    notify_on_call_from_schedule: "<schedule-id>"
    important: true  # Important notification (send via all channels)

  # Notify specific users
  - type: notify_persons
    persons_to_notify:
      - "<user-id-1>"
      - "<user-id-2>"

  # Notify user group
  - type: notify_user_group
    group_to_notify: "<group-id>"

  # Wait time
  - type: wait
    duration: 900  # 15 minutes (seconds)

  # Notify next on-call responder
  - type: notify_on_call_from_schedule
    notify_on_call_from_schedule: "<schedule-id>"
    notify_if_time_from_start_matches: true

  # Repeat previous steps
  - type: repeat_escalation
    repeat_after: 3600  # Repeat after 1 hour

  # Trigger webhook
  - type: trigger_webhook
    webhook_id: "<webhook-id>"
```

### 重要度別のエスカレーションチェーン

```yaml
# For Critical alerts
critical-chain:
  policies:
    - position: 0
      type: notify_on_call_from_schedule
      schedule: primary-oncall
      important: true
    - position: 1
      type: wait
      duration: 300  # 5 minutes
    - position: 2
      type: notify_persons
      persons: [secondary-oncall, team-lead]
      important: true
    - position: 3
      type: wait
      duration: 300
    - position: 4
      type: notify_user_group
      group: entire-team
    - position: 5
      type: repeat_escalation
      repeat_after: 1800  # 30 minutes

# For Warning alerts
warning-chain:
  policies:
    - position: 0
      type: notify_on_call_from_schedule
      schedule: primary-oncall
      important: false  # Non-important (Slack only)
    - position: 1
      type: wait
      duration: 900  # 15 minutes
    - position: 2
      type: notify_on_call_from_schedule
      schedule: primary-oncall
      important: true
    - position: 3
      type: wait
      duration: 900
    - position: 4
      type: notify_persons
      persons: [team-lead]
```

---

## アラートのグループ化とルーティング

### ルート設定

```mermaid
graph TB
    A[Alert Received] --> B{Integration<br/>Type?}

    B -->|Alertmanager| C{Labels?}
    B -->|Grafana| D{Folder?}
    B -->|CloudWatch| E{Namespace?}

    C -->|severity=critical| F[Critical Chain]
    C -->|team=infra| G[Infra Chain]
    C -->|default| H[Default Chain]

    D -->|Production| F
    D -->|Staging| I[Low Priority Chain]

    E -->|AWS/EKS| G
    E -->|AWS/RDS| J[DBA Chain]

    style F fill:#f44336,color:#ffffff
    style G fill:#ff9800,color:#ffffff
    style H fill:#4caf50,color:#ffffff
```

### ルートの作成

```bash
# Create route
curl -X POST https://oncall.example.com/api/v1/routes/ \
  -H "Authorization: Bearer <api-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "integration_id": "<integration-id>",
    "routing_regex": "\"severity\":\\s*\"critical\"",
    "position": 0,
    "escalation_chain_id": "<critical-chain-id>",
    "slack_channel_id": "<critical-channel-id>"
  }'

# Team-based route
curl -X POST https://oncall.example.com/api/v1/routes/ \
  -H "Authorization: Bearer <api-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "integration_id": "<integration-id>",
    "routing_regex": "\"team\":\\s*\"infra\"",
    "position": 1,
    "escalation_chain_id": "<infra-chain-id>",
    "slack_channel_id": "<infra-channel-id>"
  }'
```

### アラートのグループ化設定

```yaml
# Define grouping rules in Integration settings
grouping:
  # Grouping key criteria
  grouping_key: "{{ payload.labels.alertname }}-{{ payload.labels.namespace }}"

  # Grouping time window
  group_wait: 30s     # First alert wait
  group_interval: 5m   # Additional alert wait
  resolve_timeout: 5m  # Resolution wait

# Template examples
templates:
  grouping_key: |
    {% if payload.labels %}
      {{ payload.labels.alertname }}-{{ payload.labels.namespace }}
    {% else %}
      {{ payload.alert_uid }}
    {% endif %}

  title: |
    [{{ payload.status | upper }}] {{ payload.labels.alertname }}

  message: |
    **Severity:** {{ payload.labels.severity }}
    **Namespace:** {{ payload.labels.namespace }}
    **Description:** {{ payload.annotations.description }}
```

---

## ChatOps 統合

### Slack 統合

```bash
# Slack App setup (in OnCall UI)
# 1. Settings > ChatOps > Slack
# 2. Install Slack App
# 3. Grant permissions

# Connect Slack channel (API)
curl -X POST https://oncall.example.com/api/v1/slack_channels/ \
  -H "Authorization: Bearer <api-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "slack_id": "C1234567890",
    "integration_id": "<integration-id>"
  }'
```

### Slack コマンド

```bash
# Available commands in Slack
/oncall                    # Check current on-call responder
/oncall schedule           # View schedule
/oncall escalate           # Escalate alert
/oncall ack                # Acknowledge alert
/oncall resolve            # Resolve alert
/oncall silence 2h         # Silence for 2 hours
/oncall unsilence          # Remove silence
```

### Slack ワークフロー

```mermaid
sequenceDiagram
    participant A as Alert
    participant O as OnCall
    participant S as Slack
    participant U as User

    A->>O: Alert fired
    O->>S: Send message to channel
    S->>U: Display alert (with buttons)

    alt Acknowledge
        U->>S: Click "Acknowledge" button
        S->>O: Acknowledge request
        O->>O: Update status
        O->>S: Update message
    end

    alt Resolve
        U->>S: Click "Resolve" button
        S->>O: Resolve request
        O->>O: Update status
        O->>S: Update message
        O->>A: Resolution notification
    end
```

### MS Teams 統合

```yaml
# MS Teams Connector setup
ms-teams:
  # 1. Add Incoming Webhook connector to MS Teams channel
  # 2. Copy Webhook URL
  # 3. Set up Outgoing Webhook in OnCall

  outgoing-webhook:
    url: "https://outlook.office.com/webhook/xxx"
    headers:
      Content-Type: "application/json"
    template: |
      {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "{{ 'FF0000' if alert.severity == 'critical' else 'FFA500' }}",
        "summary": "{{ alert.title }}",
        "sections": [{
          "activityTitle": "{{ alert.title }}",
          "facts": [
            {"name": "Severity", "value": "{{ alert.severity }}"},
            {"name": "Status", "value": "{{ alert.status }}"}
          ],
          "markdown": true
        }]
      }
```

### Telegram 統合

```bash
# Telegram Bot setup
# 1. Create bot with @BotFather
# 2. Get Bot Token
# 3. Enter Token in OnCall settings

# Enable Telegram in values.yaml
telegram:
  enabled: true
  token:
    secretName: telegram-secret
    secretKey: bot-token

# Connect user
# 1. User sends /start message to bot
# 2. Verify Telegram connection in OnCall UI
```

---

## Grafana IRM 統合

### インシデントレスポンス管理

Grafana IRM（旧 Grafana Incident）は、OnCall と統合して、アラートからインシデントまでのワークフロー全体を管理するインシデント管理ツールです。

```mermaid
graph LR
    subgraph OnCall["Grafana OnCall"]
        A[Alert] --> B[Alert Group]
        B --> C[Escalation]
    end

    subgraph IRM["Grafana IRM"]
        D[Incident Created]
        E[Investigation]
        F[Resolution]
        G[Post-mortem]
    end

    C -->|"High Severity"| D
    D --> E
    E --> F
    F --> G

    style OnCall fill:#ff5722
    style IRM fill:#2196f3
```

### インシデントの自動作成

```yaml
# IRM integration in escalation policy
escalation-policy:
  - position: 0
    type: notify_on_call_from_schedule
    schedule: primary-oncall
  - position: 1
    type: wait
    duration: 300
  - position: 2
    type: declare_incident  # Auto-create incident
    severity: major
    title_template: "{{ alert_group.title }}"
```

---

## モバイルアプリ

### モバイルアプリの機能

1. **プッシュ通知**: アラートを即時に受信
2. **アラート管理**: 確認、解決、サイレンス
3. **スケジュール表示**: オンコールスケジュールを表示
4. **チームステータス**: チームメンバーのオンコールステータスを確認

### モバイルアプリの設定

```yaml
# Configuration for mobile push notifications
mobile:
  # Automatic setup when using Grafana Cloud
  # For self-hosted, Firebase configuration required

  firebase:
    enabled: true
    credentials:
      secretName: firebase-credentials
      secretKey: service-account.json

# User notification preferences
user-preferences:
  notification-rules:
    - type: default
      important: true  # Important notifications
      methods:
        - push
        - slack
    - type: default
      important: false  # Normal notifications
      methods:
        - slack
```

### 通知チャネルの優先度

```mermaid
graph TB
    A[Alert Fired] --> B{Importance?}

    B -->|Important| C[All Channels]
    B -->|Default| D[Default Channels Only]

    C --> E[Push Notification]
    C --> F[Phone Call]
    C --> G[SMS]
    C --> H[Slack]
    C --> I[Email]

    D --> H
    D --> I

    style C fill:#f44336
    style D fill:#4caf50
```

---

## PagerDuty/OpsGenie の比較

### 機能比較

| Feature | Grafana OnCall | PagerDuty | OpsGenie |
|---------|----------------|-----------|----------|
| **Price** | OSS Free / Cloud Paid | $21-41/user/month | $9-29/user/month |
| **Self-Hosting** | Yes | No | No |
| **On-Call Schedule** | Yes | Advanced | Advanced |
| **Escalation** | Yes | Advanced | Advanced |
| **Integrations** | 30+ | 700+ | 200+ |
| **Analytics/Reporting** | Basic | Advanced | Advanced |
| **Grafana Integration** | Native | Plugin | Plugin |
| **AIOps** | Basic | Advanced | Medium |
| **Status Page** | No | Yes | Yes |
| **Mobile App** | Yes | Yes | Yes |
| **SSO/SAML** | Yes | Yes | Yes |

### 移行時の考慮事項

```mermaid
graph TB
    subgraph Current["Currently Using"]
        P[PagerDuty/OpsGenie]
    end

    subgraph Consider["Consider Grafana OnCall When"]
        A[Need Cost Reduction?]
        B[Using Grafana Stack?]
        C[Prefer Self-Hosting?]
        D[Basic Features Sufficient?]
    end

    subgraph Decision["Decision"]
        Y[Migrate to OnCall]
        N[Keep Current]
    end

    P --> A
    A -->|Yes| B
    A -->|No| N
    B -->|Yes| C
    B -->|No| N
    C -->|Yes| D
    C -->|No| D
    D -->|Yes| Y
    D -->|No| N

    style Y fill:#4caf50
    style N fill:#ff9800
```

### 移行チェックリスト

```yaml
migration-checklist:
  before:
    - [ ] Document current schedules
    - [ ] Document escalation policies
    - [ ] Verify integration list
    - [ ] Backup alert templates

  during:
    - [ ] Install and configure OnCall
    - [ ] Create teams/users
    - [ ] Recreate schedules
    - [ ] Set up escalation chains
    - [ ] Connect integrations
    - [ ] Send test alerts

  after:
    - [ ] Run in parallel (1-2 weeks)
    - [ ] Verify alert reception
    - [ ] Verify escalation behavior
    - [ ] Disable old system
    - [ ] Team training
```

---

## ベストプラクティス

### オンコールスケジュールの設計

```yaml
best-practices-schedule:
  # 1. Appropriate rotation cycle
  rotation:
    - Weekly rotation recommended (prevent burnout)
    - Rotate among at least 3-4 people
    - Provide shadowing period for new hires

  # 2. Backup responder
  backup:
    - Always designate secondary responder
    - Auto-override for vacations

  # 3. Handoff time
  handoff:
    - Handoff during business hours (09:00 recommended)
    - Conduct handoff meeting
    - Transfer ongoing issues
```

### エスカレーションの設計

```yaml
best-practices-escalation:
  # 1. Appropriate wait times
  wait-times:
    critical: 5-10 minutes
    warning: 15-30 minutes
    info: 1 hour

  # 2. Clear escalation path
  escalation-path:
    - 1st: Current on-call
    - 2nd: Backup on-call
    - 3rd: Team lead
    - 4th: Entire team

  # 3. Alert fatigue prevention
  fatigue-prevention:
    - Non-important alerts via Slack only
    - Phone only for Critical outside business hours
    - Adjust repeat alert intervals
```

### アラート品質の管理

```yaml
best-practices-alerts:
  # 1. Only actionable alerts
  actionable:
    - Include response method in all alerts
    - Runbook link required
    - Regularly remove unnecessary alerts

  # 2. Appropriate severity
  severity:
    - Critical: Immediate response needed
    - Warning: Response within business hours
    - Info: For reference only

  # 3. Regular review
  review:
    - Weekly alert review meeting
    - Monthly on-call retrospective
    - Quarterly policy improvement
```

### オンコールのウェルビーイング

```yaml
oncall-wellness:
  # 1. Appropriate compensation
  compensation:
    - Pay on-call allowance
    - Extra compensation for nights/weekends
    - Provide compensatory time off

  # 2. Workload management
  workload:
    - Minimize other work during on-call
    - Ensure recovery time after on-call
    - Monitor alert count

  # 3. Continuous improvement
  improvement:
    - Fix root cause of recurring alerts
    - Introduce automation
    - Improve runbooks
```

---

## クイズ

[Grafana OnCall クイズ](../../quizzes/observability/alerting/03-grafana-oncall-quiz.md)で知識をテストしましょう。
