# Parte 5: Alertas y AIOps

> **Dificultad**: Avanzado **Tiempo estimado**: 60 minutos **Última actualización**: February 22, 2026

## Objetivos de aprendizaje

* Configurar reglas de detección de AlertManager para patrones de fallos comunes
* Configurar Grafana OnCall para la gestión de incidentes
* Usar CloudWatch Investigations para análisis impulsados por IA
* Crear un Agente de AIOps con Lambda y Bedrock Claude para la respuesta automatizada a incidentes

## Requisitos previos

* [ ] Haber completado la [Parte 4: Pruebas de carga](04-load-testing-scaling-lab.md)
* [ ] Stack de observabilidad que recopile métricas, logs y trazas
* [ ] SNS Topic configurado para notificaciones
* [ ] Acceso a AWS Bedrock habilitado (para la sección de AIOps)

***

## Descripción general de la arquitectura

![Arquitectura de AIOps](../../.gitbook/assets/aiops-architecture.png)

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

## Ejercicio 1: PrometheusRules de AlertManager

### Pasos

**Paso 1.1: Crear reglas de alerta integrales**

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

**Paso 1.2: Matriz de gravedad de alertas**

| Alerta               | Gravedad | Tiempo de respuesta | Escalación                  |
| -------------------- | -------- | ------------------- | --------------------------- |
| HighErrorRate        | Crítica  | 5 min               | Ingeniero de guardia        |
| HighLatency          | Advertencia | 15 min           | Notificación de Slack       |
| PodCrashLoopBackOff  | Crítica  | 5 min               | Guardia + Líder             |
| SQSQueueBacklog      | Advertencia | 15 min           | Notificación de Slack       |
| NodeNotReady         | Crítica  | 5 min               | Equipo de infraestructura   |
| AuroraHighCPU        | Advertencia | 15 min           | Equipo de bases de datos    |

### Verificación

```bash
# Check rules loaded
kubectl get prometheusrules -n monitoring

# Verify rules in Prometheus
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090 &
curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[].name'
```

***

## Ejercicio 2: Alarmas de CloudWatch

### Pasos

**Paso 2.1: Crear alarmas de CloudWatch para servicios de AWS**

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

**Paso 2.2: Crear alarma compuesta**

```bash
aws cloudwatch put-composite-alarm \
  --alarm-name "obs-lab-critical-composite" \
  --alarm-description "Critical issues detected across multiple services" \
  --alarm-rule "ALARM(obs-lab-aurora-cpu-high) OR ALARM(obs-lab-sqs-message-age)" \
  --alarm-actions $SNS_TOPIC_ARN \
  --region $AWS_REGION
```

### Verificación

```bash
aws cloudwatch describe-alarms \
  --alarm-name-prefix "obs-lab" \
  --query "MetricAlarms[].{Name:AlarmName,State:StateValue}" \
  --output table
```

***

## Ejercicio 3: Configuración de Grafana OnCall

### Pasos

**Paso 3.1: Configurar la integración de OnCall con Alertmanager**

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

**Paso 3.2: Crear una cadena de escalación de OnCall**

```yaml
# OnCall escalation chain (configure via UI or Terraform)
# Level 1: Slack notification (0 min)
# Level 2: On-call engineer page (5 min)
# Level 3: Team lead page (15 min)
# Level 4: Manager escalation (30 min)
```

***

## Ejercicio 4: SNS Topic y suscripción por correo electrónico

### Pasos

**Paso 4.1: Agregar una suscripción por correo electrónico al SNS Topic**

```bash
# Add email subscription
aws sns subscribe \
  --topic-arn $SNS_TOPIC_ARN \
  --protocol email \
  --notification-endpoint your-email@example.com \
  --region $AWS_REGION

echo "Check your email and confirm the subscription"
```

**Paso 4.2: Agregar una suscripción por SMS (opcional)**

```bash
aws sns subscribe \
  --topic-arn $SNS_TOPIC_ARN \
  --protocol sms \
  --notification-endpoint +1234567890 \
  --region $AWS_REGION
```

***

## Ejercicio 5: CloudWatch Investigations

### Pasos

**Paso 5.1: Habilitar CloudWatch Investigations**

CloudWatch Investigations usa IA para analizar automáticamente anomalías y proporcionar hipótesis.

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

**Paso 5.2: Crear un desencadenador de investigación**

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

## Ejercicio 6: Agente de AIOps con Lambda y Bedrock

### Pasos

**Paso 6.1: Arquitectura del Agente de AIOps**

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

**Paso 6.2: Crear la función Lambda**

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

**Paso 6.3: Código de la función Lambda**

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

**Paso 6.4: Implementar la función Lambda**

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

## Ejercicio 7: Inyección de carga y fallos

### Pasos

**Paso 7.1: Inyectar fallos para activar alertas**

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

**Paso 7.2: Supervisar la activación de alertas**

```bash
# Watch Alertmanager
kubectl port-forward -n monitoring svc/kube-prometheus-stack-alertmanager 9093:9093 &
curl -s http://localhost:9093/api/v2/alerts | jq '.[].labels.alertname'

# Watch for SNS notifications
# Check email for alerts
```

***

## Ejercicio 8: Verificar el pipeline de AIOps

### Pasos

**Paso 8.1: Comprobar CloudWatch Investigations**

```bash
# List recent investigations
aws cloudwatch list-dashboards --region $AWS_REGION

# In AWS Console:
# 1. Go to CloudWatch > Investigations
# 2. View auto-generated hypotheses
# 3. Check correlated signals
```

**Paso 8.2: Comprobar la ejecución de Lambda**

```bash
# Get Lambda logs
aws logs tail /aws/lambda/obs-lab-aiops-agent --follow --region $AWS_REGION
```

**Paso 8.3: Verificar la entrega de SNS**

Revise su correo electrónico para ver el informe de análisis de AIOps.

***

## Ejercicio 9: (Avanzado) Patrón multiagente A2A

### Pasos

**Paso 9.1: Arquitectura multiagente para incidentes complejos**

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

Este patrón avanzado utiliza varios agentes de IA especializados que colaboran en incidentes complejos. La implementación requiere:

1. AWS Step Functions para la orquestación
2. Varias funciones Lambda (una por especialista)
3. SQS para la comunicación entre agentes
4. DynamoDB para el contexto compartido

***

## Resumen

En este laboratorio, usted ha:

| Tarea                         | Estado        |
| ----------------------------- | ------------- |
| PrometheusRules (10+ alertas) | Creado        |
| Alarmas de CloudWatch         | Configuradas  |
| Grafana OnCall                | Configurado   |
| Notificaciones de SNS         | Habilitadas   |
| CloudWatch Investigations     | Configurado   |
| Agente Lambda de AIOps        | Implementado  |
| Prueba de inyección de fallos | Completada    |

## Lista de verificación

* [ ] Alertmanager activa alertas ante una tasa alta de errores
* [ ] OnCall recibe y enruta las alertas
* [ ] CloudWatch Investigations genera hipótesis
* [ ] El agente de AIOps Lambda analiza las alertas
* [ ] SNS entrega informes de análisis al correo electrónico

## Limpieza

La limpieza se realizará en la [Parte 6](06-distributed-tracing-lab.md#cleanup).

## Solución de problemas

<details>

<summary>Las alertas no se activan</summary>

* Compruebe la sintaxis de PrometheusRule: `kubectl describe prometheusrules -n monitoring`
* Verifique que existan métricas: pruebe la consulta en Grafana Explore
* Compruebe los targets de Prometheus: `curl localhost:9090/api/v1/targets`

</details>

<details>

<summary>Lambda no recibe webhooks</summary>

* Compruebe la configuración de API Gateway
* Verifique la configuración del webhook de Alertmanager
* Compruebe los logs de Lambda CloudWatch en busca de errores

</details>

<details>

<summary>Falla la invocación de Bedrock</summary>

* Verifique que el rol de IAM tenga permiso bedrock:InvokeModel
* Compruebe que el ID del modelo sea correcto
* Asegúrese de que Bedrock esté habilitado en su región

</details>

## Próximos pasos

Continúe con la [Parte 6: Análisis de trazas distribuidas](06-distributed-tracing-lab.md) para realizar un análisis profundo de trazas.

## Referencias

* [Documentación de Alertmanager](../../observability/alerting/01-alertmanager.md)
* [Documentación de Grafana OnCall](../../observability/alerting/03-grafana-oncall.md)
* [Documentación de alarmas de CloudWatch](../../observability/alerting/02-cloudwatch-alarms.md)
* [Documentación de AWS Bedrock](https://docs.aws.amazon.com/bedrock/)
