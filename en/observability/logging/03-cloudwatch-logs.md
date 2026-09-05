# CloudWatch Logs

> **Last Updated**: February 20, 2026

Amazon CloudWatch Logs is a fully managed log monitoring service from AWS. It natively integrates with EKS, enabling log collection, storage, and analysis without separate infrastructure management.

## Table of Contents

1. [Overview](#overview)
2. [EKS Control Plane Logging](#eks-control-plane-logging)
3. [Container Insights](#container-insights)
4. [FluentBit Integration](#fluentbit-integration)
5. [CloudWatch Logs Insights](#cloudwatch-logs-insights)
6. [Subscription Filters](#subscription-filters)
7. [Cost Optimization](#cost-optimization)

---

## Overview

### CloudWatch Logs Features

| Feature | Description |
|---------|-------------|
| **Fully Managed** | No infrastructure management required |
| **AWS Integration** | Native integration with EKS, Lambda, EC2, etc. |
| **Security** | IAM, KMS encryption, VPC endpoints |
| **Scalability** | Unlimited log collection/storage |
| **Real-time** | Real-time log streaming and alerting |

### Key Concepts

![EKS, application, and Lambda logs flow into one CloudWatch Log Group that stores Log Streams, serves Logs Insights queries, raises alarms via Metric Filters, and streams via Subscription Filters to S3, Kinesis Data Firehose (OpenSearch), and Lambda.](../../.gitbook/assets/en-observability-logging-03-cloudwatch-logs-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-logging-03-cloudwatch-logs-0.html)

### Terminology

| Term | Description | Example |
|------|-------------|---------|
| **Log Group** | Logical group of log streams | `/aws/eks/my-cluster/cluster` |
| **Log Stream** | Log sequence from a single source | `kube-apiserver-xxx` |
| **Log Event** | Individual log entry | Timestamp + message |
| **Retention** | Log retention period | 1 day ~ forever |

---

## EKS Control Plane Logging

### Log Types

| Log Type | Description | Recommended |
|----------|-------------|-------------|
| **api** | Kubernetes API server logs | Required |
| **audit** | API call audit logs | Required (security) |
| **authenticator** | IAM authentication logs | Recommended |
| **controllerManager** | Controller manager logs | Optional |
| **scheduler** | Scheduler logs | Optional |

### Enable via AWS CLI

```bash
# Enable all control plane logs
aws eks update-cluster-config \
  --name my-cluster \
  --region ap-northeast-2 \
  --logging '{
    "clusterLogging": [
      {
        "types": ["api", "audit", "authenticator", "controllerManager", "scheduler"],
        "enabled": true
      }
    ]
  }'

# Enable specific logs only
aws eks update-cluster-config \
  --name my-cluster \
  --region ap-northeast-2 \
  --logging '{
    "clusterLogging": [
      {
        "types": ["api", "audit", "authenticator"],
        "enabled": true
      },
      {
        "types": ["controllerManager", "scheduler"],
        "enabled": false
      }
    ]
  }'
```

### Configure with Terraform

```hcl
resource "aws_eks_cluster" "main" {
  name     = "my-cluster"
  role_arn = aws_iam_role.eks_cluster.arn
  version  = "1.29"

  vpc_config {
    subnet_ids              = var.subnet_ids
    endpoint_private_access = true
    endpoint_public_access  = true
  }

  enabled_cluster_log_types = [
    "api",
    "audit",
    "authenticator"
  ]

  tags = {
    Environment = "production"
  }
}

# Set log group retention period
resource "aws_cloudwatch_log_group" "eks" {
  name              = "/aws/eks/my-cluster/cluster"
  retention_in_days = 30

  tags = {
    Environment = "production"
    Cluster     = "my-cluster"
  }
}
```

### Log Group Structure

```
/aws/eks/my-cluster/cluster
+-- kube-apiserver-xxx           # API server logs
+-- kube-apiserver-audit-xxx     # Audit logs
+-- authenticator-xxx            # Authentication logs
+-- kube-controller-manager-xxx  # Controller manager
+-- kube-scheduler-xxx           # Scheduler
```

---

## Container Insights

### Container Insights Overview

Container Insights collects, aggregates, and summarizes metrics and logs from containerized applications and microservices on EKS clusters.

### Installation Methods

#### CloudWatch Agent + FluentBit (Recommended)

```bash
# Create namespace
kubectl create namespace amazon-cloudwatch

# Install CloudWatch Agent
kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluent-bit-quickstart.yaml
```

#### Install via Helm Chart

```bash
# Add Helm repository
helm repo add aws-observability https://aws-observability.github.io/aws-otel-helm-charts
helm repo update

# Install
helm install container-insights aws-observability/adot-exporter-for-eks-on-ec2 \
  --namespace amazon-cloudwatch \
  --set clusterName=my-cluster \
  --set awsRegion=ap-northeast-2 \
  --set serviceAccount.create=true \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::123456789012:role/ContainerInsightsRole
```

### IRSA Setup

```bash
# Create IAM policy
cat > container-insights-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "ec2:DescribeInstances",
        "ec2:DescribeTags",
        "ec2:DescribeVolumes"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name ContainerInsightsPolicy \
  --policy-document file://container-insights-policy.json

# Setup IRSA
eksctl create iamserviceaccount \
  --cluster=my-cluster \
  --namespace=amazon-cloudwatch \
  --name=cloudwatch-agent \
  --attach-policy-arn=arn:aws:iam::123456789012:policy/ContainerInsightsPolicy \
  --approve
```

### Collected Logs

| Log Type | Log Group | Description |
|----------|-----------|-------------|
| **Application** | `/aws/containerinsights/cluster/application` | Container stdout/stderr |
| **Host** | `/aws/containerinsights/cluster/host` | Node system logs |
| **Dataplane** | `/aws/containerinsights/cluster/dataplane` | kubelet, kube-proxy |
| **Performance** | `/aws/containerinsights/cluster/performance` | Performance metrics |

---

## FluentBit Integration

### FluentBit ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: amazon-cloudwatch
  labels:
    k8s-app: fluent-bit
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush                     5
        Grace                     30
        Log_Level                 info
        Daemon                    off
        Parsers_File              parsers.conf
        HTTP_Server               On
        HTTP_Listen               0.0.0.0
        HTTP_Port                 2020
        storage.path              /var/fluent-bit/state/flb-storage/
        storage.sync              normal
        storage.checksum          off
        storage.backlog.mem_limit 5M

    @INCLUDE application-log.conf
    @INCLUDE dataplane-log.conf
    @INCLUDE host-log.conf

  application-log.conf: |
    [INPUT]
        Name                tail
        Tag                 application.*
        Exclude_Path        /var/log/containers/cloudwatch-agent*, /var/log/containers/fluent-bit*, /var/log/containers/aws-node*, /var/log/containers/kube-proxy*
        Path                /var/log/containers/*.log
        multiline.parser    docker, cri
        DB                  /var/fluent-bit/state/flb_container.db
        Mem_Buf_Limit       50MB
        Skip_Long_Lines     On
        Refresh_Interval    10
        Rotate_Wait         30
        storage.type        filesystem
        Read_from_Head      Off

    [FILTER]
        Name                kubernetes
        Match               application.*
        Kube_URL            https://kubernetes.default.svc:443
        Kube_Tag_Prefix     application.var.log.containers.
        Merge_Log           On
        Merge_Log_Key       log_processed
        K8S-Logging.Parser  On
        K8S-Logging.Exclude Off
        Labels              Off
        Annotations         Off
        Use_Kubelet         On
        Kubelet_Port        10250
        Buffer_Size         0

    [OUTPUT]
        Name                cloudwatch_logs
        Match               application.*
        region              ${AWS_REGION}
        log_group_name      /aws/containerinsights/${CLUSTER_NAME}/application
        log_stream_prefix   ${HOST_NAME}-
        auto_create_group   true
        extra_user_agent    container-insights
        log_retention_days  30

  dataplane-log.conf: |
    [INPUT]
        Name                systemd
        Tag                 dataplane.systemd.*
        Systemd_Filter      _SYSTEMD_UNIT=docker.service
        Systemd_Filter      _SYSTEMD_UNIT=containerd.service
        Systemd_Filter      _SYSTEMD_UNIT=kubelet.service
        DB                  /var/fluent-bit/state/systemd.db
        Path                /var/log/journal
        Read_From_Tail      On

    [INPUT]
        Name                tail
        Tag                 dataplane.tail.*
        Path                /var/log/containers/aws-node*, /var/log/containers/kube-proxy*
        multiline.parser    docker, cri
        DB                  /var/fluent-bit/state/flb_dataplane_tail.db
        Mem_Buf_Limit       50MB
        Skip_Long_Lines     On
        Refresh_Interval    10
        Rotate_Wait         30
        storage.type        filesystem
        Read_from_Head      Off

    [OUTPUT]
        Name                cloudwatch_logs
        Match               dataplane.*
        region              ${AWS_REGION}
        log_group_name      /aws/containerinsights/${CLUSTER_NAME}/dataplane
        log_stream_prefix   ${HOST_NAME}-
        auto_create_group   true
        extra_user_agent    container-insights
        log_retention_days  30

  host-log.conf: |
    [INPUT]
        Name                tail
        Tag                 host.dmesg
        Path                /var/log/dmesg
        Key                 message
        DB                  /var/fluent-bit/state/flb_dmesg.db
        Mem_Buf_Limit       5MB
        Skip_Long_Lines     On
        Refresh_Interval    10
        Read_from_Head      Off

    [INPUT]
        Name                tail
        Tag                 host.messages
        Path                /var/log/messages
        Parser              syslog
        DB                  /var/fluent-bit/state/flb_messages.db
        Mem_Buf_Limit       5MB
        Skip_Long_Lines     On
        Refresh_Interval    10
        Read_from_Head      Off

    [INPUT]
        Name                tail
        Tag                 host.secure
        Path                /var/log/secure
        Parser              syslog
        DB                  /var/fluent-bit/state/flb_secure.db
        Mem_Buf_Limit       5MB
        Skip_Long_Lines     On
        Refresh_Interval    10
        Read_from_Head      Off

    [OUTPUT]
        Name                cloudwatch_logs
        Match               host.*
        region              ${AWS_REGION}
        log_group_name      /aws/containerinsights/${CLUSTER_NAME}/host
        log_stream_prefix   ${HOST_NAME}.
        auto_create_group   true
        extra_user_agent    container-insights
        log_retention_days  30

  parsers.conf: |
    [PARSER]
        Name                docker
        Format              json
        Time_Key            time
        Time_Format         %Y-%m-%dT%H:%M:%S.%LZ

    [PARSER]
        Name                cri
        Format              regex
        Regex               ^(?<time>[^ ]+) (?<stream>stdout|stderr) (?<logtag>[^ ]*) (?<log>.*)$
        Time_Key            time
        Time_Format         %Y-%m-%dT%H:%M:%S.%L%z

    [PARSER]
        Name                syslog
        Format              regex
        Regex               ^(?<time>[^ ]* {1,2}[^ ]* [^ ]*) (?<host>[^ ]*) (?<ident>[a-zA-Z0-9_\/\.\-]*)(?:\[(?<pid>[0-9]+)\])?(?:[^\:]*\:)? *(?<message>.*)$
        Time_Key            time
        Time_Format         %b %d %H:%M:%S
```

### FluentBit DaemonSet

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
  namespace: amazon-cloudwatch
  labels:
    k8s-app: fluent-bit
spec:
  selector:
    matchLabels:
      k8s-app: fluent-bit
  template:
    metadata:
      labels:
        k8s-app: fluent-bit
    spec:
      serviceAccountName: fluent-bit
      terminationGracePeriodSeconds: 10
      hostNetwork: true
      dnsPolicy: ClusterFirstWithHostNet
      tolerations:
        - key: node-role.kubernetes.io/master
          operator: Exists
          effect: NoSchedule
        - operator: Exists
          effect: NoExecute
        - operator: Exists
          effect: NoSchedule
      containers:
        - name: fluent-bit
          image: public.ecr.aws/aws-observability/aws-for-fluent-bit:stable
          imagePullPolicy: Always
          env:
            - name: AWS_REGION
              value: "ap-northeast-2"
            - name: CLUSTER_NAME
              value: "my-cluster"
            - name: HOST_NAME
              valueFrom:
                fieldRef:
                  fieldPath: spec.nodeName
          resources:
            limits:
              cpu: 500m
              memory: 250Mi
            requests:
              cpu: 50m
              memory: 50Mi
          volumeMounts:
            - name: fluentbitstate
              mountPath: /var/fluent-bit/state
            - name: varlog
              mountPath: /var/log
              readOnly: true
            - name: varlibdockercontainers
              mountPath: /var/lib/docker/containers
              readOnly: true
            - name: fluent-bit-config
              mountPath: /fluent-bit/etc/
            - name: runlogjournal
              mountPath: /run/log/journal
              readOnly: true
            - name: dmesg
              mountPath: /var/log/dmesg
              readOnly: true
      volumes:
        - name: fluentbitstate
          hostPath:
            path: /var/fluent-bit/state
        - name: varlog
          hostPath:
            path: /var/log
        - name: varlibdockercontainers
          hostPath:
            path: /var/lib/docker/containers
        - name: fluent-bit-config
          configMap:
            name: fluent-bit-config
        - name: runlogjournal
          hostPath:
            path: /run/log/journal
        - name: dmesg
          hostPath:
            path: /var/log/dmesg
```

---

## CloudWatch Logs Insights

### Basic Query Syntax

```sql
-- Basic filtering
fields @timestamp, @message
| filter @message like /error/i
| sort @timestamp desc
| limit 100

-- Field extraction (JSON)
fields @timestamp, @message
| parse @message '{"level":"*","message":"*"}' as level, msg
| filter level = "ERROR"
| sort @timestamp desc

-- Regex parsing
fields @timestamp, @message
| parse @message /user_id=(?<user_id>\d+)/
| filter user_id = "12345"
```

### EKS Log Query Examples

```sql
-- API server errors
fields @timestamp, @message
| filter @logStream like /kube-apiserver/
| filter @message like /error|Error|ERROR/
| sort @timestamp desc
| limit 50

-- Audit logs: specific user activity
fields @timestamp, @message
| filter @logStream like /kube-apiserver-audit/
| parse @message '"user":{"username":"*"' as username
| filter username = "admin"
| sort @timestamp desc

-- Authentication failures
fields @timestamp, @message
| filter @logStream like /authenticator/
| filter @message like /AccessDenied|Forbidden|unauthorized/
| sort @timestamp desc

-- Pod create/delete events
fields @timestamp, @message
| filter @logStream like /kube-apiserver-audit/
| filter @message like /"verb":"create"/ or @message like /"verb":"delete"/
| filter @message like /"resource":"pods"/
| sort @timestamp desc
```

### Application Log Queries

```sql
-- Errors by namespace
fields @timestamp, @message, kubernetes.namespace_name
| filter @message like /error/i
| stats count(*) as error_count by kubernetes.namespace_name
| sort error_count desc

-- Response time analysis (JSON logs)
fields @timestamp, @message
| filter kubernetes.container_name = "api"
| parse @message '{"response_time":*,' as response_time
| filter response_time > 1000
| sort response_time desc

-- Log volume by time
fields @timestamp
| stats count(*) as log_count by bin(1h)
| sort @timestamp

-- Top error messages
fields @timestamp, @message
| filter @message like /error/i
| stats count(*) as count by @message
| sort count desc
| limit 10
```

### Advanced Queries

```sql
-- Percentile calculation
fields @timestamp, @message
| filter kubernetes.container_name = "nginx"
| parse @message '* * * * * * * * * * "*" * * * * *' as date, time, remote_addr, dash1, dash2, request, status, body_bytes, referer, user_agent
| parse request '"* * *"' as method, path, protocol
| parse @message '* * * * * * * * * * * * * * * * * * * * * * *  * * * * * * * * * * * * * * * * * * * * * * * *' as d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14,d15,d16,d17,d18,d19,d20,d21,d22,d23,d24,d25,d26,d27,d28,d29,d30,d31,d32,d33,d34,d35,d36,response_time_ms
| stats percentile(response_time_ms, 50) as p50,
        percentile(response_time_ms, 90) as p90,
        percentile(response_time_ms, 99) as p99
  by bin(5m)

-- Container restart detection
fields @timestamp, @message, kubernetes.pod_name
| filter @message like /Back-off restarting failed container/
| stats count(*) as restart_count by kubernetes.pod_name
| sort restart_count desc

-- Multi log group query (Cross-account)
SOURCE '/aws/containerinsights/cluster-a/application'
     | '/aws/containerinsights/cluster-b/application'
| fields @timestamp, @message, @logStream
| filter @message like /error/i
| sort @timestamp desc
```

---

## Subscription Filters

### Export to S3

```hcl
# Export to S3 via Kinesis Data Firehose
resource "aws_kinesis_firehose_delivery_stream" "logs_to_s3" {
  name        = "cloudwatch-logs-to-s3"
  destination = "extended_s3"

  extended_s3_configuration {
    role_arn            = aws_iam_role.firehose.arn
    bucket_arn          = aws_s3_bucket.logs.arn
    prefix              = "logs/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/"
    error_output_prefix = "errors/!{firehose:error-output-type}/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/"
    buffering_size      = 64
    buffering_interval  = 300
    compression_format  = "GZIP"

    cloudwatch_logging_options {
      enabled         = true
      log_group_name  = aws_cloudwatch_log_group.firehose.name
      log_stream_name = "S3Delivery"
    }
  }
}

# Subscription Filter
resource "aws_cloudwatch_log_subscription_filter" "logs_to_s3" {
  name            = "logs-to-s3"
  log_group_name  = "/aws/containerinsights/my-cluster/application"
  filter_pattern  = ""  # All logs
  destination_arn = aws_kinesis_firehose_delivery_stream.logs_to_s3.arn
  role_arn        = aws_iam_role.cloudwatch_to_firehose.arn
}
```

### Process with Lambda

```python
# lambda_function.py
import json
import gzip
import base64
import boto3

def lambda_handler(event, context):
    # Decode CloudWatch Logs data
    compressed_payload = base64.b64decode(event['awslogs']['data'])
    uncompressed_payload = gzip.decompress(compressed_payload)
    log_data = json.loads(uncompressed_payload)

    for log_event in log_data['logEvents']:
        message = log_event['message']

        # Alert on error logs
        if 'ERROR' in message or 'error' in message:
            send_alert(log_data['logGroup'], message)

    return {
        'statusCode': 200,
        'body': json.dumps('Processed successfully')
    }

def send_alert(log_group, message):
    sns = boto3.client('sns')
    sns.publish(
        TopicArn='arn:aws:sns:ap-northeast-2:123456789012:alerts',
        Subject=f'Error in {log_group}',
        Message=message[:1000]  # SNS message size limit
    )
```

```hcl
# Lambda Subscription Filter
resource "aws_cloudwatch_log_subscription_filter" "logs_to_lambda" {
  name            = "logs-to-lambda"
  log_group_name  = "/aws/containerinsights/my-cluster/application"
  filter_pattern  = "?ERROR ?error ?Error"
  destination_arn = aws_lambda_function.log_processor.arn
}

resource "aws_lambda_permission" "cloudwatch" {
  statement_id  = "AllowCloudWatchLogs"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.log_processor.function_name
  principal     = "logs.ap-northeast-2.amazonaws.com"
  source_arn    = "${aws_cloudwatch_log_group.app.arn}:*"
}
```

### Create Alerts with Metric Filters

```hcl
# Error count metric
resource "aws_cloudwatch_log_metric_filter" "error_count" {
  name           = "ErrorCount"
  pattern        = "[timestamp, requestid, level=ERROR, ...]"
  log_group_name = "/aws/containerinsights/my-cluster/application"

  metric_transformation {
    name          = "ErrorCount"
    namespace     = "Application/Logs"
    value         = "1"
    default_value = "0"
  }
}

# Alert configuration
resource "aws_cloudwatch_metric_alarm" "high_error_rate" {
  alarm_name          = "HighErrorRate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ErrorCount"
  namespace           = "Application/Logs"
  period              = 300
  statistic           = "Sum"
  threshold           = 100
  alarm_description   = "Error count exceeded 100 in 5 minutes"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
```

---

## Cost Optimization

### Cost Structure

```
CloudWatch Logs pricing (ap-northeast-2):

+---------------------+-----------------+---------------------+
|        Item         |     Price       |        Notes        |
+---------------------+-----------------+---------------------+
| Ingestion           | $0.50/GB        | Pre-compression size|
| Storage             | $0.03/GB/month  | Post-compression    |
| Analysis (Insights) | $0.005/GB scan  | Data scanned/query  |
| Logs to S3          | $0.00/GB        | Free (S3 cost sep.) |
+---------------------+-----------------+---------------------+

Example: 100GB/day ingestion, 30-day retention
+-- Ingestion: 100GB x $0.50 x 30 days = $1,500
+-- Storage: ~50GB x $0.03 x 30 days = $45 (50% compression)
+-- Analysis: ~200GB x $0.005 = $1 (daily avg)
+-- Total monthly cost: ~$1,576
```

### Cost Reduction Strategies

#### 1. Log Filtering

```yaml
# Exclude unnecessary logs in FluentBit
[FILTER]
    Name     grep
    Match    *
    Exclude  log healthcheck
    Exclude  log readiness
    Exclude  log liveness

[FILTER]
    Name     grep
    Match    *
    Exclude  kubernetes_namespace_name kube-system
```

#### 2. Retention Period Optimization

```hcl
# Set retention period by environment
resource "aws_cloudwatch_log_group" "production" {
  name              = "/aws/containerinsights/prod-cluster/application"
  retention_in_days = 30  # Production: 30 days
}

resource "aws_cloudwatch_log_group" "development" {
  name              = "/aws/containerinsights/dev-cluster/application"
  retention_in_days = 7   # Development: 7 days
}

resource "aws_cloudwatch_log_group" "audit" {
  name              = "/aws/eks/my-cluster/cluster"
  retention_in_days = 365  # Audit logs: 1 year
}
```

#### 3. Archive to S3

```hcl
# Archive long-retention logs to S3
resource "aws_cloudwatch_log_subscription_filter" "archive" {
  name            = "archive-to-s3"
  log_group_name  = aws_cloudwatch_log_group.audit.name
  filter_pattern  = ""
  destination_arn = aws_kinesis_firehose_delivery_stream.archive.arn
  role_arn        = aws_iam_role.cloudwatch_to_firehose.arn
}

# Transition to S3 Glacier
resource "aws_s3_bucket_lifecycle_configuration" "archive" {
  bucket = aws_s3_bucket.logs_archive.id

  rule {
    id     = "archive"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}
```

#### 4. Adjust Log Levels

```yaml
# Disable DEBUG logs in production
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  LOG_LEVEL: "INFO"  # DEBUG, INFO, WARN, ERROR
```

### Cost Monitoring

```sql
-- Check CloudWatch Logs usage (Logs Insights)
fields @timestamp, @ingestionTime, @message
| stats sum(@billedDuration) as total_billed by bin(1d)

-- Track costs via AWS Cost Explorer API
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-01-31 \
  --granularity MONTHLY \
  --metrics "BlendedCost" \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["AmazonCloudWatch"]}}'
```

---

## Quiz

Test your knowledge with the [CloudWatch Logs Quiz](../../quizzes/observability/logging/03-cloudwatch-logs-quiz.md).
