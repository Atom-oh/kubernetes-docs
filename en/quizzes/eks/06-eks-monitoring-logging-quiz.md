# Amazon EKS Monitoring and Logging Quiz

This quiz tests your understanding of Amazon EKS monitoring and logging features, tools, and best practices.

## Quiz Overview
- EKS Cluster Monitoring
- Container and Application Logging
- Performance Metrics Collection and Analysis
- Alerting and Anomaly Detection
- Monitoring and Logging Architecture
- Best Practices and Tools

## Multiple Choice Questions

### 1. What is the most effective approach to build a comprehensive monitoring solution for an Amazon EKS cluster?

A. Use only CloudWatch
B. Use only Prometheus and Grafana
C. Use integrated CloudWatch, Prometheus, Grafana, and X-Ray
D. Write custom monitoring scripts

<details>
<summary>Show Answer</summary>

**Answer: C. Use integrated CloudWatch, Prometheus, Grafana, and X-Ray**

**Explanation:**
The most effective approach to build a comprehensive monitoring solution for an Amazon EKS cluster is to integrate CloudWatch, Prometheus, Grafana, and X-Ray. This integrated approach provides complete visibility at the infrastructure, cluster, application, and distributed tracing levels.

**Key Benefits of an Integrated Monitoring Solution:**

1. **Multi-layer Monitoring**:
   - AWS infrastructure-level metrics (CloudWatch)
   - Kubernetes cluster-level metrics (Prometheus)
   - Application-level metrics (CloudWatch, Prometheus)
   - Distributed tracing (X-Ray)

2. **Comprehensive Data Collection**:
   - System metrics (CPU, memory, disk, network)
   - Kubernetes resource metrics (pods, nodes, controllers)
   - Custom application metrics
   - Distributed service transaction tracing

3. **Flexible Visualization and Analysis**:
   - Pre-configured dashboards (CloudWatch, Grafana)
   - Custom dashboards (Grafana)
   - Advanced queries and alerts (PromQL, CloudWatch Alarms)
   - Service maps and trace analysis (X-Ray)

**Implementation Methods:**

1. **Set up CloudWatch Container Insights**:
   ```bash
   # Install CloudWatch agent
   kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluentd-quickstart.yaml
   ```

2. **Install Prometheus and Grafana**:
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

3. **Set up AWS Distro for OpenTelemetry (ADOT) and X-Ray**:
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

4. **Integrate CloudWatch with Prometheus**:
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
   - Cluster, node, pod level metrics
   - Container log collection
   - Automatic dashboards and alerts

2. **Prometheus and Grafana**:
   - Fine-grained Kubernetes metrics
   - Custom metrics and dashboards
   - Advanced queries and alerts

3. **AWS X-Ray**:
   - Distributed tracing
   - Service maps
   - Request path analysis

4. **AWS Distro for OpenTelemetry**:
   - Standardized telemetry collection
   - Support for various backends
   - Vendor-neutral instrumentation

**Best Practices:**

1. **Implement Layered Monitoring Strategy**:
   - Infrastructure level: nodes, network, storage
   - Cluster level: control plane, nodes, pods
   - Application level: services, endpoints, business metrics

2. **Establish Effective Alerting Strategy**:
   - Set alerts based on priority
   - Prevent alert fatigue
   - Define escalation paths

3. **Implement Automated Responses**:
   - Auto-scaling triggers
   - Self-healing mechanisms
   - Proactive maintenance

4. **Cost Optimization**:
   - Collect only necessary metrics
   - Appropriate sampling and aggregation
   - Optimize data retention policies

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

2. **Configure Monitoring Infrastructure with Terraform**:
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

Issues with other options:
- **A. Use only CloudWatch**: CloudWatch provides AWS infrastructure and basic container metrics but has limitations for Kubernetes-specific metrics or fine-grained application-level monitoring.
- **B. Use only Prometheus and Grafana**: This combination provides powerful Kubernetes monitoring but lacks integration with AWS services or distributed tracing capabilities.
- **D. Write custom monitoring scripts**: Custom scripts are difficult to maintain, don't scale well, and fail to leverage the rich features of industry-standard tools.
</details>
### 2. What is the best approach to effectively collect and analyze container logs in Amazon EKS?

A. Manually retrieve log files from each node
B. Read log files directly from within containers
C. Use Fluentd/Fluent Bit to send logs to CloudWatch Logs or Elasticsearch
D. Send logs only to standard output

<details>
<summary>Show Answer</summary>

**Answer: C. Use Fluentd/Fluent Bit to send logs to CloudWatch Logs or Elasticsearch**

**Explanation:**
The best approach to effectively collect and analyze container logs in Amazon EKS is to use log collectors like Fluentd or Fluent Bit to send logs to CloudWatch Logs, Amazon OpenSearch Service (formerly Elasticsearch Service), or other log analysis systems. This approach provides scalability, centralization, and search and analysis capabilities.

**Key Benefits of Fluentd/Fluent Bit-based Logging:**

1. **Centralized Log Management**:
   - Collect all container logs in a single location
   - Cluster-wide log search and analysis
   - Long-term log retention and archiving

2. **Scalability and Reliability**:
   - Support for large-scale clusters
   - Buffering and retry mechanisms
   - Minimize log loss

3. **Flexible Log Processing**:
   - Log filtering and transformation
   - Structured logging support
   - Support for various output destinations

4. **Integrated Analysis and Visualization**:
   - CloudWatch Logs Insights
   - OpenSearch Dashboards (formerly Kibana)
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

3. **Log Collection Using AWS Distro for OpenTelemetry (ADOT)**:
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

1. **Implement Structured Logging**:
   - Use JSON format logs
   - Consistent log fields and formats
   - Include correlation IDs

2. **Optimize Log Levels**:
   - Set appropriate log levels
   - Minimize debug logs in production
   - Provide sufficient context for important events

3. **Log Retention and Archiving Strategy**:
   - Balance cost and compliance requirements
   - Use tiered storage
   - Configure automatic archiving

4. **Log Security Considerations**:
   - Filter sensitive information
   - Control log access
   - Ensure log integrity

**Practical Implementation Examples:**

1. **Fluent Bit Configuration with Multiple Output Destinations**:
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

2. **CloudWatch Logs Insights Query for Log Analysis**:
   ```
   fields @timestamp, @message, kubernetes.pod_name, kubernetes.namespace_name, log
   | filter kubernetes.namespace_name = "production"
   | filter @message like /ERROR/
   | sort @timestamp desc
   | limit 100
   ```

3. **Configure Logging Infrastructure with Terraform**:
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

Issues with other options:
- **A. Manually retrieve log files from each node**: Not scalable, not automated, and logs can be lost if nodes fail.
- **B. Read log files directly from within containers**: Cannot access logs when containers terminate, and centralized analysis is difficult.
- **D. Send logs only to standard output**: Sending logs to standard output is a good practice, but without a mechanism to collect and centralize these logs, effective analysis is difficult.
</details>
### 3. What is the best approach to build an effective alerting system in Amazon EKS?

A. Manually review log files
B. Use only CloudWatch Alarms
C. Use only Prometheus AlertManager
D. Integrate CloudWatch Alarms, Prometheus AlertManager, and EventBridge to support various notification channels

<details>
<summary>Show Answer</summary>

**Answer: D. Integrate CloudWatch Alarms, Prometheus AlertManager, and EventBridge to support various notification channels**

**Explanation:**
The best approach to build an effective alerting system in Amazon EKS is to integrate CloudWatch Alarms, Prometheus AlertManager, and EventBridge to support various notification channels. This integrated approach provides comprehensive alerting at the infrastructure, cluster, and application levels and supports various notification channels and response mechanisms.

**Key Benefits of an Integrated Alerting System:**

1. **Multi-layer Alerting**:
   - AWS infrastructure-level alerts (CloudWatch)
   - Kubernetes cluster-level alerts (Prometheus)
   - Application-level alerts (custom metrics)
   - Event-based alerts (EventBridge)

2. **Support for Various Notification Channels**:
   - Email, SMS (SNS)
   - Slack, Microsoft Teams (webhooks)
   - PagerDuty, OpsGenie (incident management)
   - Custom Lambda functions

3. **Intelligent Alert Management**:
   - Alert grouping and deduplication
   - Alert routing and escalation
   - Alert suppression and silencing

**Implementation Methods:**

1. **Set up CloudWatch Alarms**:
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

2. **Configure Prometheus AlertManager**:
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

3. **Define Prometheus Alert Rules**:
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

4. **Set up EventBridge Rules**:
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

1. **Alert Integration via SNS Topics**:
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

2. **Alert Processing and Routing Using Lambda**:
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

1. **Prevent Alert Fatigue**:
   - Focus on important alerts only
   - Group and deduplicate alerts
   - Limit alert frequency

2. **Provide Clear Alert Content**:
   - Problem description and impact
   - Recommended actions for resolution
   - Related resources and context

3. **Alert Priority and Escalation**:
   - Classify alerts based on severity
   - Clear escalation paths
   - Set response time targets

4. **Test and Validate Alerts**:
   - Regularly test alerts
   - Monitor false positives and negatives
   - Review alert effectiveness

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

2. **Configure Alerting Infrastructure with Terraform**:
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

Issues with other options:
- **A. Manually review log files**: Manual review is not scalable, doesn't provide real-time alerting, and doesn't support automated responses.
- **B. Use only CloudWatch Alarms**: CloudWatch Alarms are useful for AWS infrastructure-level alerting but have limitations for Kubernetes-specific metrics or detailed application-level alerting.
- **C. Use only Prometheus AlertManager**: Prometheus AlertManager provides powerful alerting for Kubernetes metrics but has limited integration with AWS service events or infrastructure-level alerting.
</details>
### 4. What is the most effective approach for application performance monitoring in Amazon EKS?

A. Monitor only basic system metrics
B. Collect and analyze custom application metrics
C. Implement integrated observability including distributed tracing, metrics, and logs
D. Perform periodic manual performance tests

<details>
<summary>Show Answer</summary>

**Answer: C. Implement integrated observability including distributed tracing, metrics, and logs**

**Explanation:**
The most effective approach for application performance monitoring in Amazon EKS is to implement integrated observability including distributed tracing, metrics, and logs. This comprehensive approach provides complete visibility into application performance and detailed information for troubleshooting and optimization.

**Key Components of Integrated Observability:**

1. **Distributed Tracing**:
   - Track request flow between services
   - Identify latency bottlenecks
   - Understand error propagation paths

2. **Metrics**:
   - System and resource usage
   - Application performance indicators
   - Business metrics

3. **Logs**:
   - Detailed application events
   - Error and exception information
   - Debugging context

4. **Profiling**:
   - CPU and memory usage analysis
   - Identify hotspots and bottlenecks
   - Discover code-level optimization opportunities

**Implementation Methods:**

1. **Set up AWS Distro for OpenTelemetry (ADOT)**:
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

3. **Set up Amazon Managed Grafana Dashboard**:
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

1. **Implement Standardized Instrumentation**:
   - Use standards like OpenTelemetry
   - Consistent naming conventions and labels
   - Combine automatic and manual instrumentation

2. **Ensure Context Propagation**:
   - Pass trace context between services
   - Maintain context in asynchronous operations
   - Integration with external systems

3. **Optimize Sampling Strategy**:
   - Balance cost and visibility
   - Error and latency-based sampling
   - Prioritize critical transactions

4. **Correlate Observability Data**:
   - Connect traces, metrics, and logs
   - Use common identifiers and labels
   - Integrated dashboards and analysis

**Practical Implementation Examples:**

1. **Integrated Observability for Microservices Architecture**:
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

2. **Configure Observability Infrastructure with Terraform**:
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

Issues with other options:
- **A. Monitor only basic system metrics**: System metrics are important for understanding infrastructure status, but they're insufficient for identifying root causes of application performance issues.
- **B. Collect and analyze custom application metrics**: Application metrics are important, but understanding service interactions in distributed systems also requires tracing and logs.
- **D. Perform periodic manual performance tests**: Performance tests are important, but they cannot replace continuous monitoring in real-time production environments and cannot fully simulate actual user patterns.
</details>
### 5. What is the best way to effectively monitor control plane logs in Amazon EKS?

A. Access control plane nodes directly via SSH
B. Enable EKS control plane logging and send to CloudWatch Logs
C. Deploy custom log collectors
D. Periodically request logs from AWS support team

<details>
<summary>Show Answer</summary>

**Answer: B. Enable EKS control plane logging and send to CloudWatch Logs**

**Explanation:**
The best way to effectively monitor control plane logs in Amazon EKS is to enable EKS control plane logging and send logs to CloudWatch Logs. This method leverages the characteristics of EKS as a managed service to easily access and analyze control plane component logs.

**Key Benefits of EKS Control Plane Logging:**

1. **Comprehensive Log Collection**:
   - API server logs
   - Audit logs
   - Authenticator logs
   - Controller manager logs
   - Scheduler logs

2. **Managed Solution**:
   - AWS-managed log collection
   - No additional agents required
   - No direct access to control plane needed

3. **Integrated Analysis and Alerting**:
   - Queries and analysis through CloudWatch Logs Insights
   - Integration with CloudWatch Alarms
   - Long-term log retention and archiving

**Implementation Methods:**

1. **Enable Logging When Creating EKS Cluster**:
   ```bash
   # Create EKS cluster with all log types enabled
   aws eks create-cluster \
     --name my-cluster \
     --role-arn arn:aws:iam::123456789012:role/EKSClusterRole \
     --resources-vpc-config subnetIds=subnet-12345,subnet-67890,securityGroupIds=sg-12345 \
     --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
   ```

2. **Enable Logging for Existing EKS Cluster**:
   ```bash
   # Enable all log types for existing cluster
   aws eks update-cluster-config \
     --name my-cluster \
     --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
   ```

3. **Enable Only Specific Log Types**:
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
   - Detailed records of all API calls
   - Track who, what, when, and where
   - Meet security and compliance requirements

3. **Authenticator Logs (authenticator)**:
   - Authentication requests using AWS IAM credentials
   - Authentication successes and failures
   - Debug permission issues

4. **Controller Manager Logs (controllerManager)**:
   - Controller operations and status
   - Resource reconciliation activities
   - Controller errors and retries

5. **Scheduler Logs (scheduler)**:
   - Pod scheduling decisions
   - Scheduling failures and reasons
   - Resource allocation issues

**Log Analysis and Monitoring:**

1. **Queries Using CloudWatch Logs Insights**:
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

2. **Create CloudWatch Dashboard**:
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

3. **Set up CloudWatch Alarms**:
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
   - Enable only necessary log types
   - Enable audit logs according to compliance requirements
   - Balance cost and visibility

2. **Set Log Retention Policy**:
   ```bash
   # Set CloudWatch log group retention period
   aws logs put-retention-policy \
     --log-group-name /aws/eks/my-cluster/cluster \
     --retention-in-days 90
   ```

3. **Configure Log Encryption**:
   ```bash
   # Set CloudWatch log group encryption
   aws logs associate-kms-key \
     --log-group-name /aws/eks/my-cluster/cluster \
     --kms-key-id arn:aws:kms:us-west-2:123456789012:key/1234abcd-12ab-34cd-56ef-1234567890ab
   ```

4. **Control Log Access**:
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

1. **Configure EKS Cluster Logging with Terraform**:
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

Issues with other options:
- **A. Access control plane nodes directly via SSH**: EKS is a managed service, so you cannot directly access control plane nodes.
- **C. Deploy custom log collectors**: Since the control plane is managed by AWS, deploying custom log collectors won't give you access to control plane logs.
- **D. Periodically request logs from AWS support team**: This is inefficient, doesn't provide real-time monitoring, and doesn't support automated analysis and alerting.
</details>
### 6. What is the most effective monitoring strategy for cost optimization in Amazon EKS?

A. Collect all possible metrics
B. Focus on monitoring resource usage, cost allocation tags, and idle resources
C. Focus only on performance without cost monitoring
D. Review only monthly AWS bills

<details>
<summary>Show Answer</summary>

**Answer: B. Focus on monitoring resource usage, cost allocation tags, and idle resources**

**Explanation:**
The most effective monitoring strategy for cost optimization in Amazon EKS is to focus on monitoring resource usage, cost allocation tags, and idle resources. This approach ensures efficient use of cluster resources, clarifies cost allocation, and optimizes costs by identifying wasted resources.

**Key Components of Cost Optimization Monitoring:**

1. **Resource Usage Monitoring**:
   - CPU, memory, storage utilization
   - Actual usage vs. requests and limits
   - Resource usage trends and patterns

2. **Cost Allocation and Tagging**:
   - Cost analysis by namespace, service, team
   - Implement and monitor cost allocation tags
   - Track spending by cost center and project

3. **Identify Idle and Wasted Resources**:
   - Unused EBS volumes
   - Over-provisioned resources
   - Idle nodes and pods

4. **Cost Anomaly Detection**:
   - Alert on unexpected cost increases
   - Cost trend analysis
   - Monitor actual spending vs. budget

**Implementation Methods:**

1. **Monitor Kubernetes Resource Usage**:
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

2. **Implement Cost Allocation Tags**:
   ```bash
   # Enable cost allocation tags
   aws ce update-cost-allocation-tags-status \
     --cost-allocation-tags-status '[{"TagKey": "kubernetes.io/cluster/my-cluster", "Status": "Active"}, {"TagKey": "kubernetes.io/namespace", "Status": "Active"}, {"TagKey": "app", "Status": "Active"}, {"TagKey": "team", "Status": "Active"}]'

   # Tag nodes
   aws ec2 create-tags \
     --resources i-1234567890abcdef0 \
     --tags Key=team,Value=platform Key=environment,Value=production
   ```

3. **Deploy Kubecost**:
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

4. **Set up AWS Cost Explorer Dashboard**:
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
   - Number of idle pods (CPU/memory utilization < 5%)
   - Unattached EBS volumes
   - Unused load balancers

**Best Practices:**

1. **Optimize Resource Requests and Limits**:
   - Set resource requests based on actual usage
   - Utilize Vertical Pod Autoscaler
   - Regularly review resource requests

2. **Implement Effective Tagging Strategy**:
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

3. **Optimize Auto-scaling**:
   - Adjust Cluster Autoscaler configuration
   - Utilize Karpenter
   - Utilize spot instances

4. **Regular Cost Review and Optimization**:
   - Weekly/monthly cost review meetings
   - Set cost reduction targets
   - Track optimization actions

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

4. **Configure Cost Monitoring Infrastructure with Terraform**:
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

Issues with other options:
- **A. Collect all possible metrics**: Collecting all metrics increases storage costs, important cost optimization signals can be buried in noise, and analysis becomes more complex.
- **C. Focus only on performance without cost monitoring**: Performance is important, but without cost optimization, unnecessary spending can occur.
- **D. Review only monthly AWS bills**: Monthly bill review is reactive, doesn't provide detailed cost allocation information, and may miss real-time optimization opportunities.
</details>
