# Amazon EKS Monitoring and Logging Quiz

このクイズでは、Amazon EKS の monitoring と logging の機能、tools、best practices に関する理解を確認します。

## Quiz Overview
- EKS Cluster Monitoring
- Container and Application Logging
- Performance Metrics Collection and Analysis
- Alerting and Anomaly Detection
- Monitoring and Logging Architecture
- Best Practices and Tools

## Multiple Choice Questions

### 1. What is the most effective approach to build a comprehensive monitoring solution for an Amazon EKS cluster?

A. CloudWatch のみを使用する
B. Prometheus と Grafana のみを使用する
C. CloudWatch、Prometheus、Grafana、X-Ray を統合して使用する
D. カスタム monitoring scripts を作成する

<details>
<summary>回答を表示</summary>

**回答: C. CloudWatch、Prometheus、Grafana、X-Ray を統合して使用する**

**解説:**
Amazon EKS cluster 向けの包括的な monitoring solution を構築する最も効果的な approach は、CloudWatch、Prometheus、Grafana、X-Ray を統合することです。この統合 approach により、infrastructure、cluster、application、distributed tracing の各 level で完全な可視性を得られます。

**統合 Monitoring Solution の主な利点:**

1. **Multi-layer Monitoring**:
   - AWS infrastructure-level metrics (CloudWatch)
   - Kubernetes cluster-level metrics (Prometheus)
   - Application-level metrics (CloudWatch, Prometheus)
   - Distributed tracing (X-Ray)

2. **包括的な Data Collection**:
   - System metrics (CPU, memory, disk, network)
   - Kubernetes resource metrics (pods, nodes, controllers)
   - Custom application metrics
   - Distributed service transaction tracing

3. **柔軟な Visualization と Analysis**:
   - Pre-configured dashboards (CloudWatch, Grafana)
   - Custom dashboards (Grafana)
   - Advanced queries and alerts (PromQL, CloudWatch Alarms)
   - Service maps and trace analysis (X-Ray)

**Implementation Methods:**

1. **CloudWatch Container Insights を設定する**:
   ```bash
   # Install CloudWatch agent
   kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluentd-quickstart.yaml
   ```

2. **Prometheus と Grafana をインストールする**:
   ```bash
   # Create Prometheus namespace
   kubectl create namespace prometheus

   # Install Prometheus using Helm
   helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   helm install prometheus prometheus-community/prometheus \
     --namespace prometheus \
     --set alertmanager.persistentVolume.storageClass="gp2" \
     --set server.persistentVolume.storageClass="gp2"

   # Install Grafana
   helm repo add grafana https://grafana.github.io/helm-charts
   helm install grafana grafana/grafana \
     --namespace prometheus \
     --set persistence.storageClassName="gp2" \
     --set persistence.enabled=true \
     --set adminPassword='EKS!sAWSome' \
     --set datasources."datasources\\.yaml".apiVersion=1 \
     --set datasources."datasources\\.yaml".datasources[0].name=Prometheus \
     --set datasources."datasources\\.yaml".datasources[0].type=prometheus \
     --set datasources."datasources\\.yaml".datasources[0].url=http://prometheus-server.prometheus.svc.cluster.local \
     --set datasources."datasources\\.yaml".datasources[0].access=proxy \
     --set datasources."datasources\\.yaml".datasources[0].isDefault=true
   ```

3. **AWS Distro for OpenTelemetry (ADOT) と X-Ray を設定する**:
   ```bash
   # Install ADOT operator
   kubectl apply -f https://github.com/aws-observability/aws-otel-collector/releases/latest/download/opentelemetry-operator.yaml

   # Configure ADOT collector with X-Ray integration
   cat <<EOF | kubectl apply -f -
   apiVersion: opentelemetry.io/v1alpha1
   kind: OpenTelemetryCollector
   metadata:
     name: adot-collector
   spec:
     mode: deployment
     serviceAccount: adot-collector
     config: |
       receivers:
         otlp:
           protocols:
             grpc:
               endpoint: 0.0.0.0:4317
             http:
               endpoint: 0.0.0.0:4318
       processors:
         batch:
           timeout: 1s
       exporters:
         awsxray:
           region: ${AWS_REGION}
         awsemf:
           region: ${AWS_REGION}
       service:
         pipelines:
           traces:
             receivers: [otlp]
             processors: [batch]
             exporters: [awsxray]
           metrics:
             receivers: [otlp]
             processors: [batch]
             exporters: [awsemf]
   EOF
   ```

4. **CloudWatch と Prometheus を統合する**:
   ```bash
   # Create Amazon Managed Prometheus workspace
   aws amp create-workspace --alias eks-monitoring

   # Configure CloudWatch agent
   cat <<EOF | kubectl apply -f -
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: prometheus-cwagent-config
     namespace: amazon-cloudwatch
   data:
     cwagentconfig.json: |
       {
         "logs": {
           "metrics_collected": {
             "prometheus": {
               "prometheus_config_path": "/etc/prometheusconfig/prometheus.yaml",
               "emf_processor": {
                 "metric_declaration": [
                   {
                     "source_labels": ["job", "pod_name"],
                     "label_matcher": "^kubernetes-pods;.*$",
                     "dimensions": [["ClusterName", "Namespace", "PodName"]],
                     "metric_selectors": ["^.*$"]
                   }
                 ]
               }
             }
           }
         }
       }
   EOF
   ```

**Key Monitoring Components:**

1. **CloudWatch Container Insights**:
   - Cluster、node、pod level metrics
   - Container log collection
   - Automatic dashboards and alerts

2. **Prometheus and Grafana**:
   - 詳細な Kubernetes metrics
   - Custom metrics and dashboards
   - Advanced queries and alerts

3. **AWS X-Ray**:
   - Distributed tracing
   - Service maps
   - Request path analysis

4. **AWS Distro for OpenTelemetry**:
   - 標準化された telemetry collection
   - さまざまな backends のサポート
   - Vendor-neutral instrumentation

**Best Practices:**

1. **Layered Monitoring Strategy を実装する**:
   - Infrastructure level: nodes, network, storage
   - Cluster level: control plane, nodes, pods
   - Application level: services, endpoints, business metrics

2. **効果的な Alerting Strategy を確立する**:
   - Priority に基づいて alerts を設定する
   - Alert fatigue を防止する
   - Escalation paths を定義する

3. **Automated Responses を実装する**:
   - Auto-scaling triggers
   - Self-healing mechanisms
   - Proactive maintenance

4. **Cost Optimization**:
   - 必要な metrics のみを収集する
   - 適切な sampling と aggregation
   - Data retention policies を最適化する

**Practical Implementation Examples:**

1. **Comprehensive Monitoring Architecture**:
   ```
   +-------------------+    +-------------------+    +-------------------+
   |                   |    |                   |    |                   |
   |  EKS Cluster      |    |  CloudWatch       |    |  Amazon Managed   |
   |                   |    |                   |    |  Prometheus       |
   +-------------------+    +-------------------+    +-------------------+
           |                        ^                        ^
           |                        |                        |
           v                        |                        |
   +-------------------+            |                        |
   |                   |            |                        |
   |  ADOT Collector   |------------+                        |
   |                   |                                     |
   +-------------------+                                     |
           |                                                 |
           v                                                 |
   +-------------------+                                     |
   |                   |                                     |
   |  Prometheus       |------------------------------------|
   |                   |
   +-------------------+
           |
           v
   +-------------------+    +-------------------+
   |                   |    |                   |
   |  Grafana          |    |  X-Ray           |
   |                   |    |                   |
   +-------------------+    +-------------------+
   ```

2. **Terraform で Monitoring Infrastructure を構成する**:
   ```hcl
   # Amazon Managed Prometheus workspace
   resource "aws_prometheus_workspace" "eks_monitoring" {
     alias = "eks-monitoring"
   }

   # Amazon Managed Grafana workspace
   resource "aws_grafana_workspace" "eks_monitoring" {
     name                     = "eks-monitoring"
     account_access_type      = "CURRENT_ACCOUNT"
     authentication_providers = ["AWS_SSO"]
     permission_type          = "SERVICE_MANAGED"
     data_sources             = ["PROMETHEUS", "CLOUDWATCH", "XRAY"]
   }

   # CloudWatch log group
   resource "aws_cloudwatch_log_group" "eks_logs" {
     name              = "/aws/eks/my-cluster/logs"
     retention_in_days = 30
   }
   ```

他の選択肢の問題点:
- **A. CloudWatch のみを使用する**: CloudWatch は AWS infrastructure と基本的な container metrics を提供しますが、Kubernetes-specific metrics や詳細な application-level monitoring には制限があります。
- **B. Prometheus と Grafana のみを使用する**: この組み合わせは強力な Kubernetes monitoring を提供しますが、AWS services との統合や distributed tracing capabilities が不足しています。
- **D. カスタム monitoring scripts を作成する**: Custom scripts は保守が難しく、scale しにくく、industry-standard tools の豊富な機能を活用できません。
</details>
### 2. What is the best approach to effectively collect and analyze container logs in Amazon EKS?

A. 各 node から log files を手動で取得する
B. Containers 内から log files を直接読み取る
C. Fluentd/Fluent Bit を使用して logs を CloudWatch Logs または Elasticsearch に送信する
D. Logs を standard output のみに送信する

<details>
<summary>回答を表示</summary>

**回答: C. Fluentd/Fluent Bit を使用して logs を CloudWatch Logs または Elasticsearch に送信する**

**解説:**
Amazon EKS で container logs を効果的に収集して分析する最適な approach は、Fluentd や Fluent Bit のような log collectors を使用して logs を CloudWatch Logs、Amazon OpenSearch Service (以前の Elasticsearch Service)、またはその他の log analysis systems に送信することです。この approach は scalability、centralization、search と analysis capabilities を提供します。

**Fluentd/Fluent Bit-based Logging の主な利点:**

1. **Centralized Log Management**:
   - すべての container logs を単一の場所に収集する
   - Cluster-wide log search and analysis
   - Long-term log retention and archiving

2. **Scalability and Reliability**:
   - Large-scale clusters のサポート
   - Buffering and retry mechanisms
   - Log loss を最小化する

3. **柔軟な Log Processing**:
   - Log filtering and transformation
   - Structured logging support
   - さまざまな output destinations のサポート

4. **Integrated Analysis and Visualization**:
   - CloudWatch Logs Insights
   - OpenSearch Dashboards (以前の Kibana)
   - Advanced search and queries

**Implementation Methods:**

1. **Fluent Bit Integration with CloudWatch Logs**:
   ```bash
   # Create Fluent Bit namespace
   kubectl create namespace amazon-cloudwatch

   # Install AWS for Fluent Bit
   kubectl apply -f https://raw.githubusercontent.com/aws/aws-for-fluent-bit/master/eks/cloudwatch-namespace.yaml
   kubectl apply -f https://raw.githubusercontent.com/aws/aws-for-fluent-bit/master/eks/fluent-bit-service-account.yaml
   kubectl apply -f https://raw.githubusercontent.com/aws/aws-for-fluent-bit/master/eks/fluent-bit-role.yaml
   kubectl apply -f https://raw.githubusercontent.com/aws/aws-for-fluent-bit/master/eks/fluent-bit-role-binding.yaml

   # Deploy Fluent Bit ConfigMap and DaemonSet
   kubectl apply -f https://raw.githubusercontent.com/aws/aws-for-fluent-bit/master/eks/fluent-bit-configmap.yaml
   kubectl apply -f https://raw.githubusercontent.com/aws/aws-for-fluent-bit/master/eks/fluent-bit-ds.yaml
   ```

2. **Fluentd Integration with Amazon OpenSearch Service**:
   ```yaml
   # Fluentd ConfigMap
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: fluentd-config
     namespace: kube-system
   data:
     fluent.conf: |
       <source>
         @type tail
         path /var/log/containers/*.log
         pos_file /var/log/fluentd-containers.log.pos
         tag kubernetes.*
         read_from_head true
         <parse>
           @type json
           time_format %Y-%m-%dT%H:%M:%S.%NZ
         </parse>
       </source>

       <filter kubernetes.**>
         @type kubernetes_metadata
         @id filter_kube_metadata
       </filter>

       <match kubernetes.**>
         @type elasticsearch
         host search-eks-logs.us-west-2.es.amazonaws.com
         port 443
         scheme https
         ssl_verify false
         index_name fluentd.${record['kubernetes']['namespace_name']}.${record['kubernetes']['pod_name']}
         type_name fluentd
         logstash_format true
         logstash_prefix fluentd.${record['kubernetes']['namespace_name']}
         <buffer>
           @type file
           path /var/log/fluentd-buffers/kubernetes.system.buffer
           flush_mode interval
           retry_type exponential_backoff
           flush_thread_count 2
           flush_interval 5s
           retry_forever
           retry_max_interval 30
           chunk_limit_size 2M
           queue_limit_length 8
           overflow_action block
         </buffer>
       </match>
   ```

3. **AWS Distro for OpenTelemetry (ADOT) を使用した Log Collection**:
   ```yaml
   # ADOT collector configuration
   apiVersion: opentelemetry.io/v1alpha1
   kind: OpenTelemetryCollector
   metadata:
     name: adot-collector
   spec:
     mode: daemonset
     serviceAccount: adot-collector
     config: |
       receivers:
         filelog:
           include: [ /var/log/containers/*.log ]
           start_at: beginning
           include_file_path: true
           operators:
             - type: json_parser
               timestamp:
                 parse_from: attributes.time
                 layout: '%Y-%m-%dT%H:%M:%S.%LZ'
       processors:
         batch:
           timeout: 1s
       exporters:
         awscloudwatchlogs:
           log_group_name: "/aws/eks/my-cluster/logs"
           log_stream_name: "{pod_name}.{container_name}"
           region: us-west-2
       service:
         pipelines:
           logs:
             receivers: [filelog]
             processors: [batch]
             exporters: [awscloudwatchlogs]
   ```

**Log Collection and Analysis Best Practices:**

1. **Structured Logging を実装する**:
   - JSON format logs を使用する
   - 一貫した log fields and formats
   - Correlation IDs を含める

2. **Log Levels を最適化する**:
   - 適切な log levels を設定する
   - Production で debug logs を最小化する
   - 重要な events に十分な context を提供する

3. **Log Retention and Archiving Strategy**:
   - Cost と compliance requirements のバランスを取る
   - Tiered storage を使用する
   - Automatic archiving を構成する

4. **Log Security Considerations**:
   - Sensitive information を filter する
   - Log access を制御する
   - Log integrity を確保する

**Practical Implementation Examples:**

1. **Multiple Output Destinations を持つ Fluent Bit Configuration**:
   ```
   [INPUT]
       Name                tail
       Tag                 kube.*
       Path                /var/log/containers/*.log
       Parser              docker
       DB                  /var/log/flb_kube.db
       Mem_Buf_Limit       5MB
       Skip_Long_Lines     On
       Refresh_Interval    10

   [FILTER]
       Name                kubernetes
       Match               kube.*
       Kube_URL            https://kubernetes.default.svc:443
       Kube_CA_File        /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
       Kube_Token_File     /var/run/secrets/kubernetes.io/serviceaccount/token
       Merge_Log           On
       K8S-Logging.Parser  On
       K8S-Logging.Exclude Off

   [OUTPUT]
       Name                cloudwatch_logs
       Match               kube.*
       region              us-west-2
       log_group_name      /aws/eks/my-cluster/logs
       log_stream_prefix   ${kubernetes['namespace_name']}.${kubernetes['pod_name']}.
       auto_create_group   true

   [OUTPUT]
       Name                es
       Match               kube.*
       Host                search-eks-logs.us-west-2.es.amazonaws.com
       Port                443
       TLS                 On
       Index               eks-logs
       Suppress_Type_Name  On
   ```

2. **Log Analysis のための CloudWatch Logs Insights Query**:
   ```
   fields @timestamp, @message, kubernetes.pod_name, kubernetes.namespace_name, log
   | filter kubernetes.namespace_name = "production"
   | filter @message like /ERROR/
   | sort @timestamp desc
   | limit 100
   ```

3. **Terraform で Logging Infrastructure を構成する**:
   ```hcl
   # CloudWatch log group
   resource "aws_cloudwatch_log_group" "eks_logs" {
     name              = "/aws/eks/my-cluster/logs"
     retention_in_days = 30
     tags = {
       Environment = "production"
       Application = "eks-cluster"
     }
   }

   # OpenSearch domain
   resource "aws_elasticsearch_domain" "eks_logs" {
     domain_name           = "eks-logs"
     elasticsearch_version = "OpenSearch_1.3"

     cluster_config {
       instance_type  = "m5.large.elasticsearch"
       instance_count = 3
     }

     ebs_options {
       ebs_enabled = true
       volume_size = 100
     }

     encrypt_at_rest {
       enabled = true
     }

     node_to_node_encryption {
       enabled = true
     }

     domain_endpoint_options {
       enforce_https       = true
       tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
     }

     advanced_security_options {
       enabled                        = true
       internal_user_database_enabled = true
       master_user_options {
         master_user_name     = "admin"
         master_user_password = var.opensearch_master_password
       }
     }
   }
   ```

他の選択肢の問題点:
- **A. 各 node から log files を手動で取得する**: Scale せず、自動化されておらず、nodes が failure した場合に logs が失われる可能性があります。
- **B. Containers 内から log files を直接読み取る**: Containers が終了すると logs に access できず、centralized analysis が困難です。
- **D. Logs を standard output のみに送信する**: Logs を standard output に送信することは good practice ですが、これらの logs を収集して一元化する mechanism がなければ、効果的な analysis は困難です。
</details>
### 3. What is the best approach to build an effective alerting system in Amazon EKS?

A. Log files を手動で確認する
B. CloudWatch Alarms のみを使用する
C. Prometheus AlertManager のみを使用する
D. CloudWatch Alarms、Prometheus AlertManager、EventBridge を統合して、さまざまな notification channels をサポートする

<details>
<summary>回答を表示</summary>

**回答: D. CloudWatch Alarms、Prometheus AlertManager、EventBridge を統合して、さまざまな notification channels をサポートする**

**解説:**
Amazon EKS で効果的な alerting system を構築する最適な approach は、CloudWatch Alarms、Prometheus AlertManager、EventBridge を統合して、さまざまな notification channels をサポートすることです。この統合 approach は infrastructure、cluster、application levels で包括的な alerting を提供し、さまざまな notification channels と response mechanisms をサポートします。

**統合 Alerting System の主な利点:**

1. **Multi-layer Alerting**:
   - AWS infrastructure-level alerts (CloudWatch)
   - Kubernetes cluster-level alerts (Prometheus)
   - Application-level alerts (custom metrics)
   - Event-based alerts (EventBridge)

2. **さまざまな Notification Channels のサポート**:
   - Email, SMS (SNS)
   - Slack, Microsoft Teams (webhooks)
   - PagerDuty, OpsGenie (incident management)
   - Custom Lambda functions

3. **Intelligent Alert Management**:
   - Alert grouping and deduplication
   - Alert routing and escalation
   - Alert suppression and silencing

**Implementation Methods:**

1. **CloudWatch Alarms を設定する**:
   ```bash
   # Create CloudWatch alarm for node CPU usage
   aws cloudwatch put-metric-alarm \
     --alarm-name EKS-Node-High-CPU \
     --alarm-description "Alarm when CPU exceeds 80%" \
     --metric-name CPUUtilization \
     --namespace AWS/EC2 \
     --dimensions Name=AutoScalingGroupName,Value=eks-node-group-1 \
     --statistic Average \
     --period 300 \
     --threshold 80 \
     --comparison-operator GreaterThanThreshold \
     --evaluation-periods 2 \
     --alarm-actions arn:aws:sns:us-west-2:123456789012:eks-alerts
   ```

2. **Prometheus AlertManager を構成する**:
   ```yaml
   # alertmanager-config.yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: alertmanager-config
     namespace: prometheus
   data:
     alertmanager.yml: |
       global:
         resolve_timeout: 5m
       route:
         group_by: ['alertname', 'job', 'severity']
         group_wait: 30s
         group_interval: 5m
         repeat_interval: 12h
         receiver: 'sns-forwarder'
         routes:
         - match:
             severity: critical
           receiver: 'pagerduty-critical'
         - match:
             severity: warning
           receiver: 'slack-warnings'
       receivers:
       - name: 'sns-forwarder'
         webhook_configs:
         - url: 'http://sns-forwarder.monitoring.svc.cluster.local:9087/alert'
       - name: 'pagerduty-critical'
         pagerduty_configs:
         - service_key: '<PAGERDUTY_SERVICE_KEY>'
       - name: 'slack-warnings'
         slack_configs:
         - api_url: '<SLACK_WEBHOOK_URL>'
           channel: '#eks-alerts'
           title: '{{ .GroupLabels.alertname }}'
           text: '{{ .CommonAnnotations.description }}'
   ```

3. **Prometheus Alert Rules を定義する**:
   ```yaml
   # prometheus-rules.yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: prometheus-rules
     namespace: prometheus
   data:
     alert-rules.yml: |
       groups:
       - name: node-alerts
         rules:
         - alert: NodeHighCPU
           expr: instance:node_cpu_utilization:rate5m > 80
           for: 5m
           labels:
             severity: warning
           annotations:
             summary: "High CPU usage on {{ $labels.instance }}"
             description: "CPU usage is above 80% for 5 minutes on {{ $labels.instance }}"

         - alert: NodeMemoryFilling
           expr: instance:node_memory_utilization:rate5m > 80
           for: 5m
           labels:
             severity: warning
           annotations:
             summary: "High memory usage on {{ $labels.instance }}"
             description: "Memory usage is above 80% for 5 minutes on {{ $labels.instance }}"

       - name: pod-alerts
         rules:
         - alert: PodCrashLooping
           expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
           for: 10m
           labels:
             severity: warning
           annotations:
             summary: "Pod {{ $labels.pod }} is crash looping"
             description: "Pod {{ $labels.pod }} in namespace {{ $labels.namespace }} is crash looping"

         - alert: PodNotReady
           expr: sum by (namespace, pod) (kube_pod_status_phase{phase=~"Pending|Unknown"}) > 0
           for: 15m
           labels:
             severity: warning
           annotations:
             summary: "Pod {{ $labels.pod }} is not ready"
             description: "Pod {{ $labels.pod }} in namespace {{ $labels.namespace }} has been in non-ready state for more than 15 minutes"
   ```

4. **EventBridge Rules を設定する**:
   ```bash
   # Create EventBridge rule for EKS events
   aws events put-rule \
     --name EKS-Control-Plane-Events \
     --event-pattern '{"source":["aws.eks"],"detail-type":["EKS Cluster Control Plane Health"]}'

   # Set SNS topic as target
   aws events put-targets \
     --rule EKS-Control-Plane-Events \
     --targets 'Id"="1","Arn"="arn:aws:sns:us-west-2:123456789012:eks-alerts"'
   ```

**Alert Integration and Routing:**

1. **SNS Topics による Alert Integration**:
   ```bash
   # Create SNS topic
   aws sns create-topic --name eks-alerts

   # Add email subscription
   aws sns subscribe \
     --topic-arn arn:aws:sns:us-west-2:123456789012:eks-alerts \
     --protocol email \
     --notification-endpoint ops-team@example.com

   # Add Lambda subscription
   aws sns subscribe \
     --topic-arn arn:aws:sns:us-west-2:123456789012:eks-alerts \
     --protocol lambda \
     --notification-endpoint arn:aws:lambda:us-west-2:123456789012:function:process-eks-alerts
   ```

2. **Lambda を使用した Alert Processing and Routing**:
   ```python
   import json
   import boto3
   import requests

   def lambda_handler(event, context):
       message = json.loads(event['Records'][0]['Sns']['Message'])

       # Route to different channels based on alert severity
       if 'AlarmName' in message:
           severity = get_alarm_severity(message['AlarmName'])
       else:
           severity = 'info'

       if severity == 'critical':
           send_to_pagerduty(message)
       elif severity == 'warning':
           send_to_slack(message, '#eks-warnings')
       else:
           send_to_slack(message, '#eks-info')

       return {
           'statusCode': 200,
           'body': json.dumps('Alert processed successfully!')
       }

   def get_alarm_severity(alarm_name):
       if 'Critical' in alarm_name:
           return 'critical'
       elif 'Warning' in alarm_name:
           return 'warning'
       else:
           return 'info'

   def send_to_pagerduty(message):
       # Implement PagerDuty API call
       pass

   def send_to_slack(message, channel):
       # Implement Slack webhook call
       pass
   ```

**Alerting Best Practices:**

1. **Alert Fatigue を防止する**:
   - 重要な alerts のみに集中する
   - Alerts を group 化し deduplicate する
   - Alert frequency を制限する

2. **明確な Alert Content を提供する**:
   - Problem description and impact
   - Resolution のための recommended actions
   - Related resources and context

3. **Alert Priority and Escalation**:
   - Severity に基づいて alerts を分類する
   - Clear escalation paths
   - Response time targets を設定する

4. **Alerts を Test and Validate する**:
   - Alerts を定期的に test する
   - False positives and negatives を monitor する
   - Alert effectiveness を review する

**Practical Implementation Examples:**

1. **Comprehensive Alerting Architecture**:
   ```
   +-------------------+    +-------------------+    +-------------------+
   |                   |    |                   |    |                   |
   |  CloudWatch       |    |  Prometheus       |    |  EventBridge      |
   |  Alarms           |    |  AlertManager     |    |  Rules            |
   +-------------------+    +-------------------+    +-------------------+
           |                        |                        |
           v                        v                        v
   +-------------------+    +-------------------+    +-------------------+
   |                   |    |                   |    |                   |
   |  SNS Topic        |<---|  Lambda           |<---|  SQS Queue        |
   |                   |    |  Forwarder        |    |                   |
   +-------------------+    +-------------------+    +-------------------+
           |
           v
   +-------------------+    +-------------------+    +-------------------+
   |                   |    |                   |    |                   |
   |  Email/SMS        |    |  Slack/Teams      |    |  PagerDuty        |
   |                   |    |                   |    |                   |
   +-------------------+    +-------------------+    +-------------------+
   ```

2. **Terraform で Alerting Infrastructure を構成する**:
   ```hcl
   # SNS topic
   resource "aws_sns_topic" "eks_alerts" {
     name = "eks-alerts"
   }

   # CloudWatch alarm
   resource "aws_cloudwatch_metric_alarm" "node_cpu" {
     alarm_name          = "EKS-Node-High-CPU"
     comparison_operator = "GreaterThanThreshold"
     evaluation_periods  = 2
     metric_name         = "CPUUtilization"
     namespace           = "AWS/EC2"
     period              = 300
     statistic           = "Average"
     threshold           = 80
     alarm_description   = "This metric monitors EC2 CPU utilization for EKS nodes"
     alarm_actions       = [aws_sns_topic.eks_alerts.arn]
     dimensions = {
       AutoScalingGroupName = "eks-node-group-1"
     }
   }

   # EventBridge rule
   resource "aws_cloudwatch_event_rule" "eks_events" {
     name        = "EKS-Control-Plane-Events"
     description = "Capture EKS control plane events"
     event_pattern = jsonencode({
       source      = ["aws.eks"]
       detail-type = ["EKS Cluster Control Plane Health"]
     })
   }

   resource "aws_cloudwatch_event_target" "sns" {
     rule      = aws_cloudwatch_event_rule.eks_events.name
     target_id = "SendToSNS"
     arn       = aws_sns_topic.eks_alerts.arn
   }
   ```

他の選択肢の問題点:
- **A. Log files を手動で確認する**: Manual review は scale せず、real-time alerting を提供せず、automated responses をサポートしません。
- **B. CloudWatch Alarms のみを使用する**: CloudWatch Alarms は AWS infrastructure-level alerting には有用ですが、Kubernetes-specific metrics や詳細な application-level alerting には制限があります。
- **C. Prometheus AlertManager のみを使用する**: Prometheus AlertManager は Kubernetes metrics 向けの強力な alerting を提供しますが、AWS service events や infrastructure-level alerting との統合は限定的です。
</details>
### 4. What is the most effective approach for application performance monitoring in Amazon EKS?

A. 基本的な system metrics のみを monitor する
B. Custom application metrics を収集して分析する
C. Distributed tracing、metrics、logs を含む integrated observability を実装する
D. 定期的な manual performance tests を実行する

<details>
<summary>回答を表示</summary>

**回答: C. Distributed tracing、metrics、logs を含む integrated observability を実装する**

**解説:**
Amazon EKS における application performance monitoring の最も効果的な approach は、distributed tracing、metrics、logs を含む integrated observability を実装することです。この包括的な approach により、application performance を完全に可視化し、troubleshooting と optimization のための詳細情報を得られます。

**Integrated Observability の主な Components:**

1. **Distributed Tracing**:
   - Services 間の request flow を追跡する
   - Latency bottlenecks を特定する
   - Error propagation paths を理解する

2. **Metrics**:
   - System and resource usage
   - Application performance indicators
   - Business metrics

3. **Logs**:
   - 詳細な application events
   - Error and exception information
   - Debugging context

4. **Profiling**:
   - CPU and memory usage analysis
   - Hotspots and bottlenecks を特定する
   - Code-level optimization opportunities を発見する

**Implementation Methods:**

1. **AWS Distro for OpenTelemetry (ADOT) を設定する**:
   ```bash
   # Install ADOT operator
   kubectl apply -f https://github.com/aws-observability/aws-otel-collector/releases/latest/download/opentelemetry-operator.yaml

   # Configure ADOT collector
   cat <<EOF | kubectl apply -f -
   apiVersion: opentelemetry.io/v1alpha1
   kind: OpenTelemetryCollector
   metadata:
     name: adot-collector
   spec:
     mode: deployment
     serviceAccount: adot-collector
     config: |
       receivers:
         otlp:
           protocols:
             grpc:
               endpoint: 0.0.0.0:4317
             http:
               endpoint: 0.0.0.0:4318
         prometheus:
           config:
             scrape_configs:
             - job_name: 'kubernetes-pods'
               kubernetes_sd_configs:
               - role: pod
               relabel_configs:
               - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
                 action: keep
                 regex: true

       processors:
         batch:
           timeout: 1s
         resource:
           attributes:
           - key: service.name
             action: upsert
             value: "${SERVICE_NAME}"

       exporters:
         awsxray:
           region: "${AWS_REGION}"
         awsemf:
           region: "${AWS_REGION}"
           namespace: EKSApplicationMetrics
         awscloudwatchlogs:
           region: "${AWS_REGION}"
           log_group_name: "/aws/eks/my-cluster/application-logs"

       service:
         pipelines:
           traces:
             receivers: [otlp]
             processors: [batch, resource]
             exporters: [awsxray]
           metrics:
             receivers: [otlp, prometheus]
             processors: [batch, resource]
             exporters: [awsemf]
           logs:
             receivers: [otlp]
             processors: [batch, resource]
             exporters: [awscloudwatchlogs]
   EOF
   ```

2. **Application Instrumentation**:
   ```java
   // Java application example (Spring Boot)

   // build.gradle
   dependencies {
       implementation 'io.opentelemetry:opentelemetry-api'
       implementation 'io.opentelemetry:opentelemetry-sdk'
       implementation 'io.opentelemetry:opentelemetry-exporter-otlp'
       implementation 'io.opentelemetry.instrumentation:opentelemetry-spring-boot-starter:1.18.0-alpha'
   }

   // application.properties
   otel.service.name=order-service
   otel.exporter.otlp.endpoint=http://adot-collector:4317
   ```

   ```python
   # Python application example
   from opentelemetry import trace
   from opentelemetry.sdk.trace import TracerProvider
   from opentelemetry.sdk.trace.export import BatchSpanProcessor
   from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
   from opentelemetry.sdk.resources import SERVICE_NAME, Resource

   # Set up resource and tracer
   resource = Resource(attributes={
       SERVICE_NAME: "payment-service"
   })

   tracer_provider = TracerProvider(resource=resource)
   processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="adot-collector:4317"))
   tracer_provider.add_span_processor(processor)
   trace.set_tracer_provider(tracer_provider)

   # Use tracer
   tracer = trace.get_tracer(__name__)

   @app.route('/process-payment', methods=['POST'])
   def process_payment():
       with tracer.start_as_current_span("process-payment") as span:
           span.set_attribute("payment.amount", request.json.get('amount'))
           # Perform business logic
           result = process_transaction(request.json)
           span.set_attribute("payment.status", result['status'])
           return jsonify(result)
   ```

3. **Amazon Managed Grafana Dashboard を設定する**:
   ```bash
   # Create Amazon Managed Grafana workspace
   aws grafana create-workspace \
     --name eks-monitoring \
     --authentication-providers AWS_SSO \
     --permission-type SERVICE_MANAGED \
     --data-sources PROMETHEUS CLOUDWATCH XRAY
   ```

4. **X-Ray Service Map and Trace Analysis**:
   ```bash
   # Create X-Ray group
   aws xray create-group \
     --group-name "EKS-Applications" \
     --filter-expression "service(\"order-service\") OR service(\"payment-service\")"
   ```

**Key Observability Metrics and Dimensions:**

1. **Core Application Performance Indicators**:
   - Request latency (p50, p90, p99)
   - Request throughput (RPS)
   - Error rate
   - Saturation (resource utilization)

2. **Key Dimensions and Labels**:
   - Service and endpoint
   - Cluster, namespace, pod
   - Version and environment
   - Customer or tenant ID

3. **User Experience Metrics**:
   - Page load time
   - API response time
   - User interaction latency
   - Client error rate

**Best Practices:**

1. **Standardized Instrumentation を実装する**:
   - OpenTelemetry のような standards を使用する
   - 一貫した naming conventions and labels
   - Automatic と manual instrumentation を組み合わせる

2. **Context Propagation を確保する**:
   - Services 間で trace context を渡す
   - Asynchronous operations で context を維持する
   - External systems との統合

3. **Sampling Strategy を最適化する**:
   - Cost と visibility のバランスを取る
   - Error and latency-based sampling
   - Critical transactions を優先する

4. **Observability Data を関連付ける**:
   - Traces、metrics、logs を接続する
   - Common identifiers and labels を使用する
   - Integrated dashboards and analysis

**Practical Implementation Examples:**

1. **Microservices Architecture 向け Integrated Observability**:
   ```
   +-------------------+    +-------------------+    +-------------------+
   |                   |    |                   |    |                   |
   |  Frontend         |    |  Order Service    |    |  Payment Service  |
   |  (React)          |    |  (Java)           |    |  (Python)         |
   +-------------------+    +-------------------+    +-------------------+
           |                        |                        |
           v                        v                        v
   +-------------------+    +-------------------+    +-------------------+
   |                   |    |                   |    |                   |
   |  Browser SDK      |    |  OpenTelemetry    |    |  OpenTelemetry    |
   |  (RUM)            |    |  SDK              |    |  SDK              |
   +-------------------+    +-------------------+    +-------------------+
           |                        |                        |
           v                        v                        v
   +---------------------------------------------------------------+
   |                                                               |
   |                  ADOT Collector                               |
   |                                                               |
   +---------------------------------------------------------------+
           |                        |                        |
           v                        v                        v
   +-------------------+    +-------------------+    +-------------------+
   |                   |    |                   |    |                   |
   |  AWS X-Ray        |    |  Amazon           |    |  CloudWatch       |
   |  (Traces)         |    |  Managed Service  |    |  Logs             |
   |                   |    |  for Prometheus   |    |                   |
   +-------------------+    +-------------------+    +-------------------+
                                     |
                                     v
                            +-------------------+
                            |                   |
                            |  Amazon           |
                            |  Managed Grafana  |
                            |                   |
                            +-------------------+
   ```

2. **Terraform で Observability Infrastructure を構成する**:
   ```hcl
   # Amazon Managed Service for Prometheus workspace
   resource "aws_prometheus_workspace" "eks_monitoring" {
     alias = "eks-monitoring"
   }

   # Amazon Managed Grafana workspace
   resource "aws_grafana_workspace" "eks_monitoring" {
     name                     = "eks-monitoring"
     account_access_type      = "CURRENT_ACCOUNT"
     authentication_providers = ["AWS_SSO"]
     permission_type          = "SERVICE_MANAGED"
     data_sources             = ["PROMETHEUS", "CLOUDWATCH", "XRAY"]
   }

   # X-Ray group
   resource "aws_xray_group" "eks_applications" {
     group_name        = "EKS-Applications"
     filter_expression = "service(\"order-service\") OR service(\"payment-service\")"
   }

   # CloudWatch log group
   resource "aws_cloudwatch_log_group" "application_logs" {
     name              = "/aws/eks/my-cluster/application-logs"
     retention_in_days = 30
   }

   # IAM role and policy
   resource "aws_iam_role" "adot_collector" {
     name = "adot-collector"
     assume_role_policy = jsonencode({
       Version = "2012-10-17",
       Statement = [{
         Effect = "Allow",
         Principal = {
           Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${module.eks.oidc_provider}"
         },
         Action = "sts:AssumeRoleWithWebIdentity",
         Condition = {
           StringEquals = {
             "${module.eks.oidc_provider}:sub" = "system:serviceaccount:opentelemetry:adot-collector"
           }
         }
       }]
     })
   }
   ```

他の選択肢の問題点:
- **A. 基本的な system metrics のみを monitor する**: System metrics は infrastructure status を理解するうえで重要ですが、application performance issues の root causes を特定するには不十分です。
- **B. Custom application metrics を収集して分析する**: Application metrics は重要ですが、distributed systems における service interactions を理解するには tracing と logs も必要です。
- **D. 定期的な manual performance tests を実行する**: Performance tests は重要ですが、real-time production environments における continuous monitoring の代替にはならず、actual user patterns を完全には simulate できません。
</details>
### 5. What is the best way to effectively monitor control plane logs in Amazon EKS?

A. SSH 経由で control plane nodes に直接 access する
B. EKS control plane logging を有効化し、CloudWatch Logs に送信する
C. Custom log collectors を deploy する
D. AWS support team に logs を定期的に依頼する

<details>
<summary>回答を表示</summary>

**回答: B. EKS control plane logging を有効化し、CloudWatch Logs に送信する**

**解説:**
Amazon EKS で control plane logs を効果的に monitor する最善の方法は、EKS control plane logging を有効化し、logs を CloudWatch Logs に送信することです。この方法は managed service としての EKS の特性を活用し、control plane component logs に簡単に access して分析できます。

**EKS Control Plane Logging の主な利点:**

1. **Comprehensive Log Collection**:
   - API server logs
   - Audit logs
   - Authenticator logs
   - Controller manager logs
   - Scheduler logs

2. **Managed Solution**:
   - AWS-managed log collection
   - 追加 agents は不要
   - Control plane への direct access は不要

3. **Integrated Analysis and Alerting**:
   - CloudWatch Logs Insights による queries and analysis
   - CloudWatch Alarms との統合
   - Long-term log retention and archiving

**Implementation Methods:**

1. **EKS Cluster 作成時に Logging を有効化する**:
   ```bash
   # Create EKS cluster with all log types enabled
   aws eks create-cluster \
     --name my-cluster \
     --role-arn arn:aws:iam::123456789012:role/EKSClusterRole \
     --resources-vpc-config subnetIds=subnet-12345,subnet-67890,securityGroupIds=sg-12345 \
     --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
   ```

2. **既存の EKS Cluster で Logging を有効化する**:
   ```bash
   # Enable all log types for existing cluster
   aws eks update-cluster-config \
     --name my-cluster \
     --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
   ```

3. **特定の Log Types のみを有効化する**:
   ```bash
   # Enable only API server and audit logs
   aws eks update-cluster-config \
     --name my-cluster \
     --logging '{"clusterLogging":[{"types":["api","audit"],"enabled":true},{"types":["authenticator","controllerManager","scheduler"],"enabled":false}]}'
   ```

**Key Log Types and Uses:**

1. **API Server Logs (api)**:
   - API requests and responses
   - Resource creation, modification, deletion
   - Error and warning messages

2. **Audit Logs (audit)**:
   - すべての API calls の詳細な records
   - Who、what、when、where を追跡する
   - Security and compliance requirements を満たす

3. **Authenticator Logs (authenticator)**:
   - AWS IAM credentials を使用した authentication requests
   - Authentication successes and failures
   - Permission issues を debug する

4. **Controller Manager Logs (controllerManager)**:
   - Controller operations and status
   - Resource reconciliation activities
   - Controller errors and retries

5. **Scheduler Logs (scheduler)**:
   - Pod scheduling decisions
   - Scheduling failures and reasons
   - Resource allocation issues

**Log Analysis and Monitoring:**

1. **CloudWatch Logs Insights を使用した Queries**:
   ```
   # Search for API server errors
   fields @timestamp, @message
   | filter @logStream like /kube-apiserver-/
   | filter @message like /Error/
   | sort @timestamp desc
   | limit 100

   # Search audit logs for specific user
   fields @timestamp, @message
   | filter @logStream like /kube-apiserver-audit/
   | parse @message "user.username*:*" as user_prefix, username
   | filter username like /admin/
   | sort @timestamp desc
   | limit 100

   # Search for authentication failures
   fields @timestamp, @message
   | filter @logStream like /authenticator/
   | filter @message like /failed/
   | sort @timestamp desc
   | limit 100
   ```

2. **CloudWatch Dashboard を作成する**:
   ```bash
   # Create dashboard monitoring API server error rate
   aws cloudwatch put-dashboard \
     --dashboard-name EKS-Control-Plane-Monitoring \
     --dashboard-body '{
       "widgets": [
         {
           "type": "log",
           "x": 0,
           "y": 0,
           "width": 24,
           "height": 6,
           "properties": {
             "query": "SOURCE \'/aws/eks/my-cluster/cluster\' | fields @timestamp, @message\n| filter @logStream like /kube-apiserver-/\n| filter @message like /Error/\n| stats count() as errorCount by bin(5m)",
             "region": "us-west-2",
             "title": "API Server Errors",
             "view": "timeSeries"
           }
         }
       ]
     }'
   ```

3. **CloudWatch Alarms を設定する**:
   ```bash
   # Create API server error alarm
   aws cloudwatch put-metric-alarm \
     --alarm-name EKS-APIServer-Errors \
     --alarm-description "Alarm when API server errors exceed threshold" \
     --metric-name ErrorCount \
     --namespace EKS \
     --statistic Sum \
     --period 300 \
     --threshold 10 \
     --comparison-operator GreaterThanThreshold \
     --evaluation-periods 1 \
     --alarm-actions arn:aws:sns:us-west-2:123456789012:eks-alerts \
     --dimensions Name=ClusterName,Value=my-cluster
   ```

**Best Practices:**

1. **Selective Log Enablement**:
   - 必要な log types のみを有効化する
   - Compliance requirements に応じて audit logs を有効化する
   - Cost と visibility のバランスを取る

2. **Log Retention Policy を設定する**:
   ```bash
   # Set CloudWatch log group retention period
   aws logs put-retention-policy \
     --log-group-name /aws/eks/my-cluster/cluster \
     --retention-in-days 90
   ```

3. **Log Encryption を構成する**:
   ```bash
   # Set CloudWatch log group encryption
   aws logs associate-kms-key \
     --log-group-name /aws/eks/my-cluster/cluster \
     --kms-key-id arn:aws:kms:us-west-2:123456789012:key/1234abcd-12ab-34cd-56ef-1234567890ab
   ```

4. **Log Access を制御する**:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "logs:GetLogEvents",
           "logs:FilterLogEvents",
           "logs:StartQuery",
           "logs:GetQueryResults"
         ],
         "Resource": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/eks/my-cluster/cluster:*"
       }
     ]
   }
   ```

**Practical Implementation Examples:**

1. **Terraform で EKS Cluster Logging を構成する**:
   ```hcl
   resource "aws_eks_cluster" "main" {
     name     = "my-cluster"
     role_arn = aws_iam_role.eks_cluster.arn

     vpc_config {
       subnet_ids         = var.subnet_ids
       security_group_ids = [aws_security_group.eks_cluster.id]
     }

     enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

     depends_on = [
       aws_iam_role_policy_attachment.eks_cluster_policy,
       aws_cloudwatch_log_group.eks_logs
     ]
   }

   resource "aws_cloudwatch_log_group" "eks_logs" {
     name              = "/aws/eks/my-cluster/cluster"
     retention_in_days = 90
     kms_key_id        = aws_kms_key.eks_logs.arn
   }

   resource "aws_kms_key" "eks_logs" {
     description             = "KMS key for EKS cluster logs encryption"
     deletion_window_in_days = 7
     enable_key_rotation     = true
   }
   ```

2. **CloudWatch Logs Insights Dashboard**:
   ```hcl
   resource "aws_cloudwatch_dashboard" "eks_control_plane" {
     dashboard_name = "EKS-Control-Plane-Monitoring"

     dashboard_body = jsonencode({
       widgets = [
         {
           type = "log"
           x    = 0
           y    = 0
           width = 24
           height = 6
           properties = {
             query = "SOURCE '/aws/eks/my-cluster/cluster' | fields @timestamp, @message\n| filter @logStream like /kube-apiserver-/\n| filter @message like /Error/\n| stats count() as errorCount by bin(5m)"
             region = "us-west-2"
             title = "API Server Errors"
             view = "timeSeries"
           }
         },
         {
           type = "log"
           x    = 0
           y    = 6
           width = 24
           height = 6
           properties = {
             query = "SOURCE '/aws/eks/my-cluster/cluster' | fields @timestamp, @message\n| filter @logStream like /kube-apiserver-audit/\n| stats count() as auditCount by bin(5m)"
             region = "us-west-2"
             title = "Audit Events"
             view = "timeSeries"
           }
         }
       ]
     })
   }
   ```

他の選択肢の問題点:
- **A. SSH 経由で control plane nodes に直接 access する**: EKS は managed service であるため、control plane nodes に直接 access することはできません。
- **C. Custom log collectors を deploy する**: Control plane は AWS によって managed されているため、custom log collectors を deploy しても control plane logs に access できません。
- **D. AWS support team に logs を定期的に依頼する**: これは非効率で、real-time monitoring を提供せず、automated analysis and alerting をサポートしません。
</details>
### 6. What is the most effective monitoring strategy for cost optimization in Amazon EKS?

A. 可能なすべての metrics を収集する
B. Resource usage、cost allocation tags、idle resources の monitoring に集中する
C. Cost monitoring なしで performance のみに集中する
D. Monthly AWS bills のみを review する

<details>
<summary>回答を表示</summary>

**回答: B. Resource usage、cost allocation tags、idle resources の monitoring に集中する**

**解説:**
Amazon EKS で cost optimization のための最も効果的な monitoring strategy は、resource usage、cost allocation tags、idle resources の monitoring に集中することです。この approach により、cluster resources を効率的に使用し、cost allocation を明確化し、wasted resources を特定して costs を最適化できます。

**Cost Optimization Monitoring の主な Components:**

1. **Resource Usage Monitoring**:
   - CPU, memory, storage utilization
   - Actual usage vs. requests and limits
   - Resource usage trends and patterns

2. **Cost Allocation and Tagging**:
   - Namespace、service、team 別の cost analysis
   - Cost allocation tags を実装し monitor する
   - Cost center and project 別の spending を追跡する

3. **Idle and Wasted Resources を特定する**:
   - Unused EBS volumes
   - Over-provisioned resources
   - Idle nodes and pods

4. **Cost Anomaly Detection**:
   - Unexpected cost increases に alert する
   - Cost trend analysis
   - Actual spending vs. budget を monitor する

**Implementation Methods:**

1. **Kubernetes Resource Usage を monitor する**:
   ```yaml
   # Monitor resource usage with Prometheus
   apiVersion: monitoring.coreos.com/v1
   kind: ServiceMonitor
   metadata:
     name: kubernetes-resources
     namespace: monitoring
   spec:
     selector:
       matchLabels:
         k8s-app: kubelet
     namespaceSelector:
       matchNames:
       - kube-system
     endpoints:
     - port: https-metrics
       scheme: https
       interval: 30s
       tlsConfig:
         insecureSkipVerify: true
       bearerTokenFile: /var/run/secrets/kubernetes.io/serviceaccount/token
     - port: cadvisor
       scheme: https
       interval: 30s
       tlsConfig:
         insecureSkipVerify: true
       bearerTokenFile: /var/run/secrets/kubernetes.io/serviceaccount/token
       metricRelabelings:
       - action: keep
         sourceLabels: [__name__]
         regex: container_cpu_usage_seconds_total|container_memory_working_set_bytes|container_fs_usage_bytes
   ```

2. **Cost Allocation Tags を実装する**:
   ```bash
   # Enable cost allocation tags
   aws ce update-cost-allocation-tags-status \
     --cost-allocation-tags-status '[{"TagKey": "kubernetes.io/cluster/my-cluster", "Status": "Active"}, {"TagKey": "kubernetes.io/namespace", "Status": "Active"}, {"TagKey": "app", "Status": "Active"}, {"TagKey": "team", "Status": "Active"}]'

   # Tag nodes
   aws ec2 create-tags \
     --resources i-1234567890abcdef0 \
     --tags Key=team,Value=platform Key=environment,Value=production
   ```

3. **Kubecost を deploy する**:
   ```bash
   # Install Kubecost using Helm
   helm repo add kubecost https://kubecost.github.io/cost-analyzer/
   helm install kubecost kubecost/cost-analyzer \
     --namespace kubecost \
     --create-namespace \
     --set kubecostToken="<YOUR_KUBECOST_TOKEN>" \
     --set prometheus.server.persistentVolume.size=100Gi \
     --set prometheus.nodeExporter.enabled=true \
     --set serviceMonitor.enabled=true
   ```

4. **AWS Cost Explorer Dashboard を設定する**:
   ```bash
   # Create AWS Cost Explorer dashboard
   aws ce create-cost-category \
     --name EKS-Clusters \
     --rule-version "CostCategoryExpression.v1" \
     --rules '[{"Value": "my-cluster-prod", "Rule": {"Tags": {"Key": "kubernetes.io/cluster/my-cluster-prod", "Values": ["owned", "shared"], "MatchOptions": ["EQUALS"]}}}, {"Value": "my-cluster-dev", "Rule": {"Tags": {"Key": "kubernetes.io/cluster/my-cluster-dev", "Values": ["owned", "shared"], "MatchOptions": ["EQUALS"]}}}]'
   ```

**Key Monitoring Metrics and Dimensions:**

1. **Resource Efficiency Metrics**:
   - CPU utilization = used CPU / requested CPU
   - Memory utilization = used memory / requested memory
   - Resource requests vs. limits ratio

2. **Cost Allocation Dimensions**:
   - Cluster
   - Namespace
   - Deployment/StatefulSet
   - Labels (team, application, environment)

3. **Waste Identification Metrics**:
   - Idle pods の数 (CPU/memory utilization < 5%)
   - Unattached EBS volumes
   - Unused load balancers

**Best Practices:**

1. **Resource Requests and Limits を最適化する**:
   - Actual usage に基づいて resource requests を設定する
   - Vertical Pod Autoscaler を利用する
   - Resource requests を定期的に review する

2. **効果的な Tagging Strategy を実装する**:
   ```yaml
   # Namespace labels example
   apiVersion: v1
   kind: Namespace
   metadata:
     name: team-a
     labels:
       team: team-a
       cost-center: cc-123
       environment: production
   ```

3. **Auto-scaling を最適化する**:
   - Cluster Autoscaler configuration を調整する
   - Karpenter を利用する
   - Spot instances を利用する

4. **定期的な Cost Review and Optimization**:
   - Weekly/monthly cost review meetings
   - Cost reduction targets を設定する
   - Optimization actions を追跡する

**Practical Implementation Examples:**

1. **Grafana Cost Dashboard**:
   ```bash
   # Import Grafana dashboard
   kubectl -n monitoring create configmap cost-dashboard \
     --from-file=cost-dashboard.json
   ```

2. **Resource Request vs. Usage Monitoring Queries**:
   ```
   # Prometheus query examples
   # CPU utilization vs. requests
   sum(rate(container_cpu_usage_seconds_total{namespace="production"}[5m])) by (pod) /
   sum(kube_pod_container_resource_requests{resource="cpu", namespace="production"}) by (pod)

   # Memory utilization vs. requests
   sum(container_memory_working_set_bytes{namespace="production"}) by (pod) /
   sum(kube_pod_container_resource_requests{resource="memory", namespace="production"}) by (pod)
   ```

3. **Cost Optimization Automation Script**:
   ```python
   # Script example for identifying and reporting idle resources
   import boto3
   import kubernetes
   from kubernetes import client, config

   # Set up Kubernetes client
   config.load_kube_config()
   v1 = client.CoreV1Api()

   # Set up AWS client
   ec2 = boto3.client('ec2')
   elb = boto3.client('elb')

   def find_unused_volumes():
       volumes = ec2.describe_volumes(
           Filters=[
               {'Name': 'status', 'Values': ['available']},
               {'Name': 'tag:kubernetes.io/cluster/my-cluster', 'Values': ['owned']}
           ]
       )
       return volumes['Volumes']

   def find_underutilized_pods():
       pods = v1.list_pod_for_all_namespaces(watch=False)
       underutilized = []
       for pod in pods.items:
           # Get usage data from metrics API or Prometheus
           # Identify pods with low utilization
           pass
       return underutilized

   # Main function
   def main():
       unused_volumes = find_unused_volumes()
       underutilized_pods = find_underutilized_pods()

       # Generate report and alert
       generate_report(unused_volumes, underutilized_pods)

   if __name__ == "__main__":
       main()
   ```

4. **Terraform で Cost Monitoring Infrastructure を構成する**:
   ```hcl
   # AWS budget alert setup
   resource "aws_budgets_budget" "eks_monthly" {
     name              = "eks-monthly-budget"
     budget_type       = "COST"
     limit_amount      = "1000"
     limit_unit        = "USD"
     time_unit         = "MONTHLY"
     time_period_start = "2023-01-01_00:00"

     cost_filter {
       name = "TagKeyValue"
       values = [
         "kubernetes.io/cluster/my-cluster$owned"
       ]
     }

     notification {
       comparison_operator        = "GREATER_THAN"
       threshold                  = 80
       threshold_type             = "PERCENTAGE"
       notification_type          = "ACTUAL"
       subscriber_email_addresses = ["team@example.com"]
     }
   }

   # CloudWatch dashboard
   resource "aws_cloudwatch_dashboard" "eks_cost" {
     dashboard_name = "EKS-Cost-Monitoring"

     dashboard_body = jsonencode({
       widgets = [
         {
           type   = "metric"
           x      = 0
           y      = 0
           width  = 12
           height = 6
           properties = {
             metrics = [
               ["AWS/EC2", "CPUUtilization", "AutoScalingGroupName", "eks-node-group-1", {"stat": "Average"}]
             ]
             period = 300
             region = "us-west-2"
             title  = "Node Group CPU Utilization"
           }
         },
         {
           type   = "metric"
           x      = 12
           y      = 0
           width  = 12
           height = 6
           properties = {
             metrics = [
               ["AWS/EC2", "NetworkIn", "AutoScalingGroupName", "eks-node-group-1", {"stat": "Sum"}],
               ["AWS/EC2", "NetworkOut", "AutoScalingGroupName", "eks-node-group-1", {"stat": "Sum"}]
             ]
             period = 300
             region = "us-west-2"
             title  = "Node Group Network Traffic"
           }
         }
       ]
     })
   }
   ```

他の選択肢の問題点:
- **A. 可能なすべての metrics を収集する**: すべての metrics を収集すると storage costs が増加し、重要な cost optimization signals が noise に埋もれ、analysis がより複雑になります。
- **C. Cost monitoring なしで performance のみに集中する**: Performance は重要ですが、cost optimization がなければ不要な spending が発生する可能性があります。
- **D. Monthly AWS bills のみを review する**: Monthly bill review は reactive で、詳細な cost allocation information を提供せず、real-time optimization opportunities を見逃す可能性があります。
</details>
