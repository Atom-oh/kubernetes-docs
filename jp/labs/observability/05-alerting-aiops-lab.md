# パート 5: アラートと AIOps

> **難易度**: 上級 **推定所要時間**: 60 分 **最終更新**: February 22, 2026

## 学習目標

* 一般的な障害パターン向けに AlertManager 検出ルールを設定する
* インシデント管理用に Grafana OnCall をセットアップする
* AI を活用した分析に CloudWatch Investigations を使用する
* 自動化されたインシデント対応のために Lambda と Bedrock Claude を使用して AIOps Agent を構築する

## 前提条件

* [ ] [パート 4: 負荷テスト](04-load-testing-scaling-lab.md) を完了していること
* [ ] メトリクス、ログ、トレースを収集する Observability スタック
* [ ] 通知用に設定された SNS Topic
* [ ] AWS Bedrock アクセスが有効化されていること（AIOps セクション用）

***

## アーキテクチャ概要

![AIOps アーキテクチャ](../../.gitbook/assets/aiops-architecture.png)

```mermaid
flowchart TB
    subgraph Detection["Alert Detection"]
        AM["Alertmanager"]
        CWA["CloudWatch Alarms"]
        GO["Grafana OnCall"]
    end

    subgraph Analysis["AI Analysis"]
        CWI["CloudWatch Investigations"]
        AIOPS["AIOps Agent (Lambda)"]
        Bedrock["Bedrock Claude"]
    end

    subgraph Notification["Notification"]
        SNS["SNS Topic"]
        Email["Email"]
        Slack["Slack"]
        PD["PagerDuty"]
    end

    AM -->|webhook| GO
    AM -->|webhook| AIOPS
    CWA -->|trigger| SNS
    CWA -->|anomaly| CWI

    CWI -->|hypothesis| AIOPS
    AIOPS -->|query| Bedrock
    AIOPS -->|analysis| SNS

    SNS --> Email & Slack & PD
    GO -->|escalation| SNS
```

***

## 演習 1: AlertManager PrometheusRules

### 手順

**ステップ 1.1: 包括的なアラートルールを作成する**

```bash
kubectl config use-context $(kubectl config get-contexts -o name | grep obs-managed)

cat <<'EOF' | kubectl apply -f -
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: msa-alerts
  namespace: monitoring
  labels:
    prometheus: kube-prometheus-stack-prometheus
    role: alert-rules
spec:
  groups:
    - name: msa.availability
      rules:
        - alert: HighErrorRate
          expr: |
            (
              sum(rate(http_server_request_count{namespace="msa",http_status_code=~"5.."}[5m])) by (service)
              /
              sum(rate(http_server_request_count{namespace="msa"}[5m])) by (service)
            ) > 0.05
          for: 2m
          labels:
            severity: critical
            team: platform
          annotations:
            summary: "High error rate on {{ $labels.service }}"
            description: "Service {{ $labels.service }} has error rate of {{ $value | humanizePercentage }} (threshold: 5%)"
            runbook_url: "https://runbooks.obs-lab.io/high-error-rate"
            dashboard_url: "http://grafana.obs-lab.io/d/msa-overview?var-service={{ $labels.service }}"

        - alert: HighLatency
          expr: |
            histogram_quantile(0.99,
              sum(rate(http_server_request_duration_seconds_bucket{namespace="msa"}[5m])) by (le, service)
            ) > 1
          for: 5m
          labels:
            severity: warning
            team: platform
          annotations:
            summary: "High latency on {{ $labels.service }}"
            description: "P99 latency for {{ $labels.service }} is {{ $value | humanizeDuration }} (threshold: 1s)"
            runbook_url: "https://runbooks.obs-lab.io/high-latency"

        - alert: ServiceDown
          expr: |
            up{job=~".*msa.*"} == 0
          for: 1m
          labels:
            severity: critical
            team: platform
          annotations:
            summary: "Service {{ $labels.job }} is down"
            description: "Prometheus target {{ $labels.instance }} for job {{ $labels.job }} has been down for more than 1 minute"

    - name: msa.pods
      rules:
        - alert: PodCrashLoopBackOff
          expr: |
            max_over_time(kube_pod_container_status_waiting_reason{namespace="msa",reason="CrashLoopBackOff"}[5m]) >= 1
          for: 5m
          labels:
            severity: critical
            team: platform
          annotations:
            summary: "Pod {{ $labels.namespace }}/{{ $labels.pod }} is crash looping"
            description: "Container {{ $labels.container }} in pod {{ $labels.pod }} is in CrashLoopBackOff state"
            runbook_url: "https://runbooks.obs-lab.io/crashloop"

        - alert: PodHighMemoryUsage
          expr: |
            (
              container_memory_working_set_bytes{namespace="msa",container!=""}
              /
              container_spec_memory_limit_bytes{namespace="msa",container!=""}
            ) > 0.9
          for: 5m
          labels:
            severity: warning
            team: platform
          annotations:
            summary: "High memory usage in {{ $labels.pod }}"
            description: "Container {{ $labels.container }} memory usage is {{ $value | humanizePercentage }} of limit"

        - alert: PodHighCPUUsage
          expr: |
            (
              sum(rate(container_cpu_usage_seconds_total{namespace="msa",container!=""}[5m])) by (pod, container)
              /
              sum(container_spec_cpu_quota{namespace="msa",container!=""}/container_spec_cpu_period{namespace="msa",container!=""}) by (pod, container)
            ) > 0.9
          for: 10m
          labels:
            severity: warning
            team: platform
          annotations:
            summary: "High CPU usage in {{ $labels.pod }}"
            description: "Container {{ $labels.container }} CPU usage is {{ $value | humanizePercentage }} of limit"

    - name: msa.sqs
      rules:
        - alert: SQSQueueBacklog
          expr: |
            aws_sqs_approximate_number_of_messages_visible_average{queue_name="obs-lab-orders"} > 1000
          for: 5m
          labels:
            severity: warning
            team: platform
          annotations:
            summary: "SQS queue backlog detected"
            description: "Queue obs-lab-orders has {{ $value }} messages waiting (threshold: 1000)"
            runbook_url: "https://runbooks.obs-lab.io/sqs-backlog"

        - alert: SQSMessageAge
          expr: |
            aws_sqs_approximate_age_of_oldest_message_seconds_average{queue_name="obs-lab-orders"} > 300
          for: 5m
          labels:
            severity: critical
            team: platform
          annotations:
            summary: "SQS messages are aging"
            description: "Oldest message in obs-lab-orders is {{ $value | humanizeDuration }} old (threshold: 5m)"

    - name: msa.nodes
      rules:
        - alert: NodeNotReady
          expr: |
            kube_node_status_condition{condition="Ready",status="true"} == 0
          for: 5m
          labels:
            severity: critical
            team: infra
          annotations:
            summary: "Node {{ $labels.node }} is not ready"
            description: "Node {{ $labels.node }} has been in NotReady state for more than 5 minutes"

        - alert: NodeHighDiskUsage
          expr: |
            (
              node_filesystem_avail_bytes{fstype!~"tmpfs|overlay",mountpoint="/"}
              /
              node_filesystem_size_bytes{fstype!~"tmpfs|overlay",mountpoint="/"}
            ) < 0.1
          for: 10m
          labels:
            severity: warning
            team: infra
          annotations:
            summary: "Node {{ $labels.instance }} disk space low"
            description: "Node has only {{ $value | humanizePercentage }} disk space available"

    - name: msa.database
      rules:
        - alert: AuroraHighCPU
          expr: |
            aws_rds_cpuutilization_average{dbinstance_identifier=~"obs-lab-aurora.*"} > 80
          for: 10m
          labels:
            severity: warning
            team: database
          annotations:
            summary: "Aurora high CPU usage"
            description: "Aurora instance {{ $labels.dbinstance_identifier }} CPU is {{ $value }}%"

        - alert: AuroraHighConnections
          expr: |
            aws_rds_database_connections_average{dbinstance_identifier=~"obs-lab-aurora.*"} > 100
          for: 5m
          labels:
            severity: warning
            team: database
          annotations:
            summary: "Aurora high connection count"
            description: "Aurora instance {{ $labels.dbinstance_identifier }} has {{ $value }} connections"
EOF
```

**ステップ 1.2: アラート重要度マトリクス**

| アラート               | 重要度 | 対応時間 | エスカレーション         |
| ------------------- | -------- | ------------- | ------------------ |
| HighErrorRate       | 重大 | 5 分         | オンコールエンジニア   |
| HighLatency         | 警告  | 15 分        | Slack 通知 |
| PodCrashLoopBackOff | 重大 | 5 分         | オンコール + リード     |
| SQSQueueBacklog     | 警告  | 15 分        | Slack 通知 |
| NodeNotReady        | 重大 | 5 分         | インフラチーム         |
| AuroraHighCPU       | 警告  | 15 分        | データベースチーム      |

### 検証

```bash
# Check rules loaded
kubectl get prometheusrules -n monitoring

# Verify rules in Prometheus
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090 &
curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[].name'
```

***

## 演習 2: CloudWatch Alarms

### 手順

**ステップ 2.1: AWS サービス用の CloudWatch Alarms を作成する**

```bash
# Aurora CPU Alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "obs-lab-aurora-cpu-high" \
  --alarm-description "Aurora CPU utilization is high" \
  --metric-name CPUUtilization \
  --namespace AWS/RDS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=DBClusterIdentifier,Value=obs-lab-aurora \
  --evaluation-periods 2 \
  --alarm-actions $SNS_TOPIC_ARN \
  --ok-actions $SNS_TOPIC_ARN \
  --region $AWS_REGION

# SQS Message Age Alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "obs-lab-sqs-message-age" \
  --alarm-description "SQS messages are aging" \
  --metric-name ApproximateAgeOfOldestMessage \
  --namespace AWS/SQS \
  --statistic Maximum \
  --period 60 \
  --threshold 300 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=QueueName,Value=obs-lab-orders \
  --evaluation-periods 3 \
  --alarm-actions $SNS_TOPIC_ARN \
  --region $AWS_REGION

# OpenSearch Cluster Health Alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "obs-lab-opensearch-health" \
  --alarm-description "OpenSearch cluster health is not green" \
  --metric-name ClusterStatus.green \
  --namespace AWS/ES \
  --statistic Minimum \
  --period 60 \
  --threshold 1 \
  --comparison-operator LessThanThreshold \
  --dimensions Name=DomainName,Value=obs-lab-logs Name=ClientId,Value=$ACCOUNT_ID \
  --evaluation-periods 2 \
  --alarm-actions $SNS_TOPIC_ARN \
  --region $AWS_REGION
```

**ステップ 2.2: 複合アラームを作成する**

```bash
aws cloudwatch put-composite-alarm \
  --alarm-name "obs-lab-critical-composite" \
  --alarm-description "Critical issues detected across multiple services" \
  --alarm-rule "ALARM(obs-lab-aurora-cpu-high) OR ALARM(obs-lab-sqs-message-age)" \
  --alarm-actions $SNS_TOPIC_ARN \
  --region $AWS_REGION
```

### 検証

```bash
aws cloudwatch describe-alarms \
  --alarm-name-prefix "obs-lab" \
  --query "MetricAlarms[].{Name:AlarmName,State:StateValue}" \
  --output table
```

***

## 演習 3: Grafana OnCall のセットアップ

### 手順

**ステップ 3.1: Alertmanager との OnCall 統合を設定する**

```bash
# Get OnCall webhook URL (from Grafana OnCall UI after setup)
ONCALL_WEBHOOK_URL="http://grafana-oncall-engine.monitoring.svc.cluster.local:8080/integrations/v1/alertmanager/<integration-id>/"

# Update Alertmanager config
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: alertmanager-kube-prometheus-stack-alertmanager
  namespace: monitoring
stringData:
  alertmanager.yaml: |
    global:
      resolve_timeout: 5m

    route:
      receiver: 'oncall-default'
      group_by: ['alertname', 'namespace', 'severity']
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 4h
      routes:
        - match:
            severity: critical
          receiver: 'oncall-critical'
          continue: true
        - match:
            severity: warning
          receiver: 'oncall-warning'

    receivers:
      - name: 'oncall-default'
        webhook_configs:
          - url: '${ONCALL_WEBHOOK_URL}'
            send_resolved: true

      - name: 'oncall-critical'
        webhook_configs:
          - url: '${ONCALL_WEBHOOK_URL}'
            send_resolved: true
        sns_configs:
          - topic_arn: '${SNS_TOPIC_ARN}'
            sigv4:
              region: '${AWS_REGION}'
            subject: '[CRITICAL] {{ .GroupLabels.alertname }}'

      - name: 'oncall-warning'
        webhook_configs:
          - url: '${ONCALL_WEBHOOK_URL}'
            send_resolved: true

    inhibit_rules:
      - source_match:
          severity: 'critical'
        target_match:
          severity: 'warning'
        equal: ['alertname', 'namespace']
EOF
```

**ステップ 3.2: OnCall エスカレーションチェーンを作成する**

```yaml
# OnCall escalation chain (configure via UI or Terraform)
# Level 1: Slack notification (0 min)
# Level 2: On-call engineer page (5 min)
# Level 3: Team lead page (15 min)
# Level 4: Manager escalation (30 min)
```

***

## 演習 4: SNS Topic とメールサブスクリプション

### 手順

**ステップ 4.1: SNS Topic にメールサブスクリプションを追加する**

```bash
# Add email subscription
aws sns subscribe \
  --topic-arn $SNS_TOPIC_ARN \
  --protocol email \
  --notification-endpoint your-email@example.com \
  --region $AWS_REGION

echo "Check your email and confirm the subscription"
```

**ステップ 4.2: SMS サブスクリプションを追加する（任意）**

```bash
aws sns subscribe \
  --topic-arn $SNS_TOPIC_ARN \
  --protocol sms \
  --notification-endpoint +1234567890 \
  --region $AWS_REGION
```

***

## 演習 5: CloudWatch Investigations

### 手順

**ステップ 5.1: CloudWatch Investigations を有効にする**

CloudWatch Investigations は AI を使用して、異常を自動的に分析し、仮説を提示します。

```mermaid
stateDiagram-v2
    [*] --> AnomalyDetected: CloudWatch detects anomaly
    AnomalyDetected --> InvestigationStarted: Auto-create investigation
    InvestigationStarted --> DataCollection: Collect related signals
    DataCollection --> CorrelationAnalysis: Correlate metrics/logs/traces
    CorrelationAnalysis --> HypothesisGeneration: AI generates hypotheses
    HypothesisGeneration --> RootCauseProposal: Propose root cause
    RootCauseProposal --> RecommendedActions: Suggest remediation
    RecommendedActions --> [*]: Investigation complete
```

**ステップ 5.2: Investigation トリガーを作成する**

```bash
# Enable automatic investigation on critical alarms
aws cloudwatch put-anomaly-detector \
  --namespace "AWS/ApplicationSignals" \
  --metric-name "ErrorCount" \
  --dimensions Name=Service,Value=order-service \
  --stat "Sum" \
  --region $AWS_REGION

# Configure investigation settings
aws cloudwatch put-insight-rule \
  --rule-name "obs-lab-error-investigation" \
  --rule-state "ENABLED" \
  --rule-definition '{
    "Schema": {
      "Name": "CloudWatchLogRule",
      "Version": 1
    },
    "LogGroupNames": ["/obs-lab/kubernetes"],
    "LogFormat": "JSON",
    "Fields": {
      "level": "$.level",
      "message": "$.message",
      "traceId": "$.traceId",
      "service": "$.kubernetes.labels.app"
    },
    "Contribution": {
      "Keys": ["$.service"],
      "Filters": [
        {
          "Match": "$.level",
          "In": ["ERROR", "FATAL"]
        }
      ]
    },
    "AggregateOn": "Count"
  }' \
  --region $AWS_REGION
```

***

## 演習 6: Lambda と Bedrock を使用する AIOps Agent

### 手順

**ステップ 6.1: AIOps Agent アーキテクチャ**

```mermaid
sequenceDiagram
    participant AM as Alertmanager
    participant APIGW as API Gateway
    participant Lambda as Lambda Function
    participant CW as CloudWatch
    participant Loki as Loki
    participant Tempo as Tempo
    participant Bedrock as Bedrock Claude
    participant SNS as SNS

    AM->>APIGW: Alert webhook
    APIGW->>Lambda: Invoke
    activate Lambda

    par Collect Telemetry
        Lambda->>CW: Query metrics
        Lambda->>Loki: Query logs
        Lambda->>Tempo: Query traces
    end

    Lambda->>Lambda: Prepare context
    Lambda->>Bedrock: Analyze with Claude
    Bedrock-->>Lambda: Analysis result

    Lambda->>SNS: Send analysis report
    deactivate Lambda
    SNS->>SNS: Notify teams
```

**ステップ 6.2: Lambda 関数を作成する**

```bash
# Create Lambda execution role
aws iam create-role \
  --role-name obs-lab-aiops-lambda \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach policies
aws iam attach-role-policy \
  --role-name obs-lab-aiops-lambda \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy \
  --role-name obs-lab-aiops-lambda \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchReadOnlyAccess

# Create inline policy for Bedrock and SNS
aws iam put-role-policy \
  --role-name obs-lab-aiops-lambda \
  --policy-name aiops-permissions \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ],
        "Resource": "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-sonnet*"
      },
      {
        "Effect": "Allow",
        "Action": "sns:Publish",
        "Resource": "'$SNS_TOPIC_ARN'"
      },
      {
        "Effect": "Allow",
        "Action": [
          "logs:GetQueryResults",
          "logs:StartQuery",
          "logs:StopQuery"
        ],
        "Resource": "*"
      }
    ]
  }'
```

**ステップ 6.3: Lambda 関数コード**

```python
# aiops_handler.py
import json
import boto3
import os
from datetime import datetime, timedelta

bedrock = boto3.client('bedrock-runtime', region_name=os.environ['AWS_REGION'])
cloudwatch = boto3.client('cloudwatch', region_name=os.environ['AWS_REGION'])
logs = boto3.client('logs', region_name=os.environ['AWS_REGION'])
sns = boto3.client('sns', region_name=os.environ['AWS_REGION'])

SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']
GRAFANA_URL = os.environ.get('GRAFANA_URL', 'http://grafana.obs-lab.io')

def lambda_handler(event, context):
    """Process Alertmanager webhook and perform AI analysis."""

    # Parse alert
    alert = json.loads(event['body'])
    alerts = alert.get('alerts', [])

    if not alerts:
        return {'statusCode': 200, 'body': 'No alerts to process'}

    for alert_item in alerts:
        if alert_item.get('status') != 'firing':
            continue

        analysis = analyze_alert(alert_item)
        send_analysis_report(alert_item, analysis)

    return {'statusCode': 200, 'body': 'Analysis complete'}

def analyze_alert(alert):
    """Collect telemetry and analyze with Bedrock Claude."""

    labels = alert.get('labels', {})
    annotations = alert.get('annotations', {})

    service = labels.get('service', 'unknown')
    namespace = labels.get('namespace', 'msa')
    alert_name = labels.get('alertname', 'unknown')

    # Collect metrics
    metrics_data = collect_metrics(service, namespace)

    # Collect logs
    logs_data = collect_logs(service, namespace)

    # Prepare prompt for Claude
    prompt = f"""You are an SRE expert analyzing a Kubernetes alert. Provide a concise root cause analysis and recommended actions.

## Alert Information
- Alert Name: {alert_name}
- Service: {service}
- Namespace: {namespace}
- Summary: {annotations.get('summary', 'N/A')}
- Description: {annotations.get('description', 'N/A')}
- Severity: {labels.get('severity', 'unknown')}

## Recent Metrics
{json.dumps(metrics_data, indent=2)}

## Recent Error Logs
{logs_data[:5000]}

## Analysis Required
1. Identify the most likely root cause
2. List any correlated issues
3. Provide 3-5 specific remediation steps
4. Estimate the blast radius (affected services/users)
5. Suggest preventive measures

Format your response as:
### Root Cause
[Your analysis]

### Correlated Issues
[List any related problems]

### Remediation Steps
1. [Step 1]
2. [Step 2]
...

### Blast Radius
[Impact assessment]

### Prevention
[Future prevention measures]
"""

    # Call Bedrock Claude
    response = bedrock.invoke_model(
        modelId='anthropic.claude-3-sonnet-20240229-v1:0',
        contentType='application/json',
        accept='application/json',
        body=json.dumps({
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': 2000,
            'messages': [
                {'role': 'user', 'content': prompt}
            ]
        })
    )

    result = json.loads(response['body'].read())
    return result['content'][0]['text']

def collect_metrics(service, namespace):
    """Collect relevant metrics from CloudWatch."""

    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=30)

    metrics = {}

    # Request rate
    try:
        response = cloudwatch.get_metric_statistics(
            Namespace='ContainerInsights',
            MetricName='pod_cpu_utilization',
            Dimensions=[
                {'Name': 'Namespace', 'Value': namespace},
                {'Name': 'Service', 'Value': service}
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=300,
            Statistics=['Average', 'Maximum']
        )
        metrics['cpu_utilization'] = response.get('Datapoints', [])
    except Exception as e:
        metrics['cpu_error'] = str(e)

    return metrics

def collect_logs(service, namespace):
    """Collect recent error logs from CloudWatch Logs."""

    log_group = f'/obs-lab/kubernetes'

    try:
        query = f"""
        fields @timestamp, @message
        | filter kubernetes.labels.app = '{service}'
        | filter level = 'ERROR' or level = 'FATAL'
        | sort @timestamp desc
        | limit 50
        """

        response = logs.start_query(
            logGroupName=log_group,
            startTime=int((datetime.utcnow() - timedelta(hours=1)).timestamp()),
            endTime=int(datetime.utcnow().timestamp()),
            queryString=query
        )

        query_id = response['queryId']

        # Wait for query to complete (simplified)
        import time
        time.sleep(5)

        results = logs.get_query_results(queryId=query_id)

        log_messages = []
        for result in results.get('results', []):
            for field in result:
                if field['field'] == '@message':
                    log_messages.append(field['value'])

        return '\n'.join(log_messages)
    except Exception as e:
        return f"Error collecting logs: {str(e)}"

def send_analysis_report(alert, analysis):
    """Send analysis report via SNS."""

    labels = alert.get('labels', {})
    annotations = alert.get('annotations', {})

    message = f"""
=== AIOps Alert Analysis Report ===

Alert: {labels.get('alertname')}
Service: {labels.get('service')}
Severity: {labels.get('severity')}
Time: {datetime.utcnow().isoformat()}

{analysis}

---
Dashboard: {GRAFANA_URL}/d/msa-overview?var-service={labels.get('service')}
Runbook: {annotations.get('runbook_url', 'N/A')}

Generated by obs-lab AIOps Agent
"""

    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=f"[AIOps] Analysis: {labels.get('alertname')} - {labels.get('service')}",
        Message=message
    )
```

**ステップ 6.4: Lambda 関数をデプロイする**

```bash
# Create deployment package
mkdir -p /tmp/aiops-lambda
cat > /tmp/aiops-lambda/aiops_handler.py << 'PYEOF'
# [Insert the Python code from Step 6.3 above]
PYEOF

cd /tmp/aiops-lambda
zip -r function.zip aiops_handler.py

# Create Lambda function
aws lambda create-function \
  --function-name obs-lab-aiops-agent \
  --runtime python3.11 \
  --role arn:aws:iam::${ACCOUNT_ID}:role/obs-lab-aiops-lambda \
  --handler aiops_handler.lambda_handler \
  --zip-file fileb://function.zip \
  --timeout 60 \
  --memory-size 256 \
  --environment "Variables={SNS_TOPIC_ARN=${SNS_TOPIC_ARN},AWS_REGION=${AWS_REGION}}" \
  --region $AWS_REGION

# Create API Gateway trigger
aws apigateway create-rest-api \
  --name obs-lab-aiops-webhook \
  --region $AWS_REGION
```

***

## 演習 7: 負荷と障害の注入

### 手順

**ステップ 7.1: アラートをトリガーするために障害を注入する**

```bash
# Inject high error rate
kubectl exec -n msa deployment/order-service -- \
  curl -X POST localhost:8000/admin/chaos/error-rate -d '{"rate": 0.3}'

# Inject latency
kubectl exec -n msa deployment/order-service -- \
  curl -X POST localhost:8000/admin/chaos/latency -d '{"delay_ms": 2000}'

# Simulate pod crash
kubectl delete pod -n msa -l app=order-service --wait=false
```

**ステップ 7.2: 発火中のアラートを監視する**

```bash
# Watch Alertmanager
kubectl port-forward -n monitoring svc/kube-prometheus-stack-alertmanager 9093:9093 &
curl -s http://localhost:9093/api/v2/alerts | jq '.[].labels.alertname'

# Watch for SNS notifications
# Check email for alerts
```

***

## 演習 8: AIOps パイプラインを検証する

### 手順

**ステップ 8.1: CloudWatch Investigations を確認する**

```bash
# List recent investigations
aws cloudwatch list-dashboards --region $AWS_REGION

# In AWS Console:
# 1. Go to CloudWatch > Investigations
# 2. View auto-generated hypotheses
# 3. Check correlated signals
```

**ステップ 8.2: Lambda 実行を確認する**

```bash
# Get Lambda logs
aws logs tail /aws/lambda/obs-lab-aiops-agent --follow --region $AWS_REGION
```

**ステップ 8.3: SNS 配信を検証する**

AIOps 分析レポートが届いているかメールを確認してください。

***

## 演習 9: （上級）A2A マルチエージェントパターン

### 手順

**ステップ 9.1: 複雑なインシデント向けのマルチエージェントアーキテクチャ**

```mermaid
flowchart TB
    Alert[Alert Received]

    subgraph Coordinator["Coordinator Agent"]
        Triage[Triage Alert]
        Assign[Assign Specialists]
        Synthesize[Synthesize Results]
    end

    subgraph Specialists["Specialist Agents"]
        Metrics["Metrics Analyst<br/>(Prometheus Expert)"]
        Logs["Log Analyst<br/>(Loki Expert)"]
        Traces["Trace Analyst<br/>(Tempo Expert)"]
        Infra["Infra Analyst<br/>(K8s/AWS Expert)"]
    end

    Alert --> Triage
    Triage --> Assign
    Assign --> Metrics & Logs & Traces & Infra
    Metrics & Logs & Traces & Infra --> Synthesize
    Synthesize --> Report[Final Report]
```

この上級パターンでは、複数の専門 AI Agent が連携して複雑なインシデントに対応します。実装には以下が必要です。

1. オーケストレーション用の AWS Step Functions
2. 複数の Lambda 関数（各スペシャリストにつき 1 つ）
3. Agent 間通信のための SQS
4. 共有コンテキストのための DynamoDB

***

## まとめ

このラボでは、以下を行いました。

| タスク                         | ステータス     |
| ---------------------------- | ---------- |
| PrometheusRules（10 以上のアラート） | 作成済み    |
| CloudWatch Alarms            | 設定済み |
| Grafana OnCall               | セットアップ済み   |
| SNS 通知            | 有効化済み    |
| CloudWatch Investigations    | 設定済み |
| AIOps Lambda Agent           | デプロイ済み   |
| 障害注入テスト         | 完了  |

## 検証チェックリスト

* [ ] Alertmanager が高いエラー率でアラートを発火する
* [ ] OnCall がアラートを受信してルーティングする
* [ ] CloudWatch Investigations が仮説を生成する
* [ ] Lambda AIOps Agent がアラートを分析する
* [ ] SNS が分析レポートをメールに配信する

## クリーンアップ

クリーンアップは[パート 6](06-distributed-tracing-lab.md#cleanup)で実施します。

## トラブルシューティング

<details>

<summary>アラートが発火しない</summary>

* PrometheusRule 構文を確認します: `kubectl describe prometheusrules -n monitoring`
* メトリクスが存在することを確認します: Grafana Explore でクエリをテスト
* Prometheus ターゲットを確認します: `curl localhost:9090/api/v1/targets`

</details>

<details>

<summary>Lambda が webhook を受信しない</summary>

* API Gateway 設定を確認します
* Alertmanager webhook 設定を確認します
* Lambda CloudWatch ログにエラーがないか確認します

</details>

<details>

<summary>Bedrock の呼び出しに失敗する</summary>

* IAM role に bedrock:InvokeModel 権限があることを確認します
* model ID が正しいことを確認します
* リージョンで Bedrock が有効になっていることを確認します

</details>

## 次のステップ

[パート 6: 分散トレーシング分析](06-distributed-tracing-lab.md)に進み、詳細なトレース分析を実施してください。

## 参考資料

* [Alertmanager ドキュメント](../../observability/alerting/01-alertmanager.md)
* [Grafana OnCall ドキュメント](../../observability/alerting/03-grafana-oncall.md)
* [CloudWatch Alarms ドキュメント](../../observability/alerting/02-cloudwatch-alarms.md)
* [AWS Bedrock ドキュメント](https://docs.aws.amazon.com/bedrock/)
