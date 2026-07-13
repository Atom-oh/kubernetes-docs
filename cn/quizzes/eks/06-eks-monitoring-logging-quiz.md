# Amazon EKS 监控和日志记录测验

本测验测试你对 Amazon EKS 监控和日志记录功能、工具以及最佳实践的理解。

## 测验概览
- EKS Cluster 监控
- Container 和 Application 日志记录
- Performance Metrics 收集与分析
- Alerting 和异常检测
- 监控和日志记录架构
- 最佳实践和工具

## 选择题

### 1. 为 Amazon EKS cluster 构建全面监控解决方案的最有效方法是什么？

A. 仅使用 CloudWatch
B. 仅使用 Prometheus 和 Grafana
C. 集成使用 CloudWatch、Prometheus、Grafana 和 X-Ray
D. 编写自定义监控脚本

<details>
<summary>查看答案</summary>

**答案：C. 集成使用 CloudWatch、Prometheus、Grafana 和 X-Ray**

**解释：**
为 Amazon EKS cluster 构建全面监控解决方案的最有效方法是集成 CloudWatch、Prometheus、Grafana 和 X-Ray。这种集成方法可在基础设施、cluster、application 和分布式追踪层面提供完整可见性。

**集成监控解决方案的主要优势：**

1. **多层监控**：
   - AWS 基础设施级 metrics (CloudWatch)
   - Kubernetes cluster 级 metrics (Prometheus)
   - Application 级 metrics (CloudWatch, Prometheus)
   - 分布式追踪 (X-Ray)

2. **全面的数据收集**：
   - System metrics (CPU, memory, disk, network)
   - Kubernetes resource metrics (pods, nodes, controllers)
   - 自定义 application metrics
   - 分布式 Service transaction tracing

3. **灵活的可视化和分析**：
   - 预配置 dashboard (CloudWatch, Grafana)
   - 自定义 dashboard (Grafana)
   - 高级查询和 alert (PromQL, CloudWatch Alarms)
   - Service map 和 trace analysis (X-Ray)

**实施方法：**

1. **设置 CloudWatch Container Insights**：
   ```bash
   # Install CloudWatch agent
   kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluentd-quickstart.yaml
   ```

2. **安装 Prometheus 和 Grafana**：
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

3. **设置 AWS Distro for OpenTelemetry (ADOT) 和 X-Ray**：
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

4. **将 CloudWatch 与 Prometheus 集成**：
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

**关键监控组件：**

1. **CloudWatch Container Insights**：
   - Cluster、node、pod 级 metrics
   - Container log 收集
   - 自动 dashboard 和 alert

2. **Prometheus 和 Grafana**：
   - 细粒度 Kubernetes metrics
   - 自定义 metrics 和 dashboard
   - 高级查询和 alert

3. **AWS X-Ray**：
   - 分布式追踪
   - Service map
   - Request path analysis

4. **AWS Distro for OpenTelemetry**：
   - 标准化 telemetry 收集
   - 支持多种 backend
   - Vendor-neutral instrumentation

**最佳实践：**

1. **实施分层监控策略**：
   - Infrastructure level: nodes, network, storage
   - Cluster level: control plane, nodes, pods
   - Application level: services, endpoints, business metrics

2. **建立有效的 Alerting 策略**：
   - 根据优先级设置 alert
   - 防止 alert fatigue
   - 定义 escalation path

3. **实施自动化响应**：
   - Auto-scaling trigger
   - Self-healing mechanism
   - 主动维护

4. **成本优化**：
   - 仅收集必要 metrics
   - 适当的 sampling 和 aggregation
   - 优化 data retention policy

**实际实施示例：**

1. **全面监控架构**：
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

2. **使用 Terraform 配置监控基础设施**：
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

其他选项的问题：
- **A. 仅使用 CloudWatch**：CloudWatch 提供 AWS infrastructure 和基本 container metrics，但在 Kubernetes-specific metrics 或细粒度 application-level monitoring 方面有限制。
- **B. 仅使用 Prometheus 和 Grafana**：这种组合提供强大的 Kubernetes monitoring，但缺少与 AWS services 或 distributed tracing 功能的集成。
- **D. 编写自定义监控脚本**：自定义脚本难以维护、扩展性差，并且无法利用行业标准工具的丰富功能。
</details>
### 2. 在 Amazon EKS 中有效收集和分析 container logs 的最佳方法是什么？

A. 从每个 node 手动检索 log files
B. 直接从 containers 内部读取 log files
C. 使用 Fluentd/Fluent Bit 将 logs 发送到 CloudWatch Logs 或 Elasticsearch
D. 仅将 logs 发送到 standard output

<details>
<summary>查看答案</summary>

**答案：C. 使用 Fluentd/Fluent Bit 将 logs 发送到 CloudWatch Logs 或 Elasticsearch**

**解释：**
在 Amazon EKS 中有效收集和分析 container logs 的最佳方法是使用 Fluentd 或 Fluent Bit 等 log collector，将 logs 发送到 CloudWatch Logs、Amazon OpenSearch Service（以前称为 Elasticsearch Service）或其他 log analysis systems。此方法提供可扩展性、集中化以及搜索和分析能力。

**基于 Fluentd/Fluent Bit 的日志记录的主要优势：**

1. **集中式 Log Management**：
   - 在单一位置收集所有 container logs
   - Cluster-wide log search and analysis
   - 长期 log retention 和归档

2. **可扩展性和可靠性**：
   - 支持大规模 clusters
   - Buffering 和 retry mechanism
   - 尽量减少 log loss

3. **灵活的 Log Processing**：
   - Log filtering 和 transformation
   - 支持 structured logging
   - 支持多种 output destination

4. **集成分析和可视化**：
   - CloudWatch Logs Insights
   - OpenSearch Dashboards（以前称为 Kibana）
   - 高级搜索和查询

**实施方法：**

1. **Fluent Bit 与 CloudWatch Logs 集成**：
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

2. **Fluentd 与 Amazon OpenSearch Service 集成**：
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

3. **使用 AWS Distro for OpenTelemetry (ADOT) 收集 Logs**：
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

**Log 收集和分析最佳实践：**

1. **实施 Structured Logging**：
   - 使用 JSON 格式 logs
   - 一致的 log fields 和 formats
   - 包含 correlation IDs

2. **优化 Log Levels**：
   - 设置适当的 log levels
   - 在生产环境中尽量减少 debug logs
   - 为重要事件提供足够上下文

3. **Log Retention 和归档策略**：
   - 平衡成本和合规要求
   - 使用分层存储
   - 配置自动归档

4. **Log Security Considerations**：
   - 过滤敏感信息
   - 控制 log access
   - 确保 log integrity

**实际实施示例：**

1. **包含多个 Output Destinations 的 Fluent Bit 配置**：
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

2. **用于 Log Analysis 的 CloudWatch Logs Insights Query**：
   ```
   fields @timestamp, @message, kubernetes.pod_name, kubernetes.namespace_name, log
   | filter kubernetes.namespace_name = "production"
   | filter @message like /ERROR/
   | sort @timestamp desc
   | limit 100
   ```

3. **使用 Terraform 配置 Logging Infrastructure**：
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

其他选项的问题：
- **A. 从每个 node 手动检索 log files**：不可扩展、没有自动化，并且如果 nodes 发生故障，logs 可能会丢失。
- **B. 直接从 containers 内部读取 log files**：当 containers 终止时无法访问 logs，并且集中分析很困难。
- **D. 仅将 logs 发送到 standard output**：将 logs 发送到 standard output 是一种良好实践，但如果没有收集并集中这些 logs 的机制，就很难进行有效分析。
</details>
### 3. 在 Amazon EKS 中构建有效 alerting system 的最佳方法是什么？

A. 手动审查 log files
B. 仅使用 CloudWatch Alarms
C. 仅使用 Prometheus AlertManager
D. 集成 CloudWatch Alarms、Prometheus AlertManager 和 EventBridge，以支持多种 notification channels

<details>
<summary>查看答案</summary>

**答案：D. 集成 CloudWatch Alarms、Prometheus AlertManager 和 EventBridge，以支持多种 notification channels**

**解释：**
在 Amazon EKS 中构建有效 alerting system 的最佳方法是集成 CloudWatch Alarms、Prometheus AlertManager 和 EventBridge，以支持多种 notification channels。这种集成方法在 infrastructure、cluster 和 application 层面提供全面 alerting，并支持多种 notification channels 和 response mechanisms。

**集成 Alerting System 的主要优势：**

1. **多层 Alerting**：
   - AWS infrastructure-level alerts (CloudWatch)
   - Kubernetes cluster-level alerts (Prometheus)
   - Application-level alerts (custom metrics)
   - Event-based alerts (EventBridge)

2. **支持多种 Notification Channels**：
   - Email, SMS (SNS)
   - Slack, Microsoft Teams (webhooks)
   - PagerDuty, OpsGenie (incident management)
   - 自定义 Lambda functions

3. **智能 Alert Management**：
   - Alert grouping 和 deduplication
   - Alert routing 和 escalation
   - Alert suppression 和 silencing

**实施方法：**

1. **设置 CloudWatch Alarms**：
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

2. **配置 Prometheus AlertManager**：
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

3. **定义 Prometheus Alert Rules**：
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

4. **设置 EventBridge Rules**：
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

**Alert Integration 和 Routing：**

1. **通过 SNS Topics 集成 Alert**：
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

2. **使用 Lambda 进行 Alert Processing 和 Routing**：
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

**Alerting 最佳实践：**

1. **防止 Alert Fatigue**：
   - 仅关注重要 alert
   - 对 alert 进行 grouping 和 deduplication
   - 限制 alert frequency

2. **提供清晰的 Alert Content**：
   - 问题描述和影响
   - 推荐的解决操作
   - 相关资源和上下文

3. **Alert Priority 和 Escalation**：
   - 根据 severity 对 alerts 分类
   - 清晰的 escalation paths
   - 设置 response time targets

4. **测试和验证 Alerts**：
   - 定期测试 alerts
   - 监控 false positives 和 negatives
   - 审查 alert effectiveness

**实际实施示例：**

1. **全面 Alerting 架构**：
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

2. **使用 Terraform 配置 Alerting Infrastructure**：
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

其他选项的问题：
- **A. 手动审查 log files**：手动审查不可扩展，不能提供实时 alerting，也不支持自动响应。
- **B. 仅使用 CloudWatch Alarms**：CloudWatch Alarms 对 AWS infrastructure-level alerting 很有用，但在 Kubernetes-specific metrics 或详细 application-level alerting 方面有限制。
- **C. 仅使用 Prometheus AlertManager**：Prometheus AlertManager 为 Kubernetes metrics 提供强大的 alerting，但与 AWS service events 或 infrastructure-level alerting 的集成有限。
</details>
### 4. 在 Amazon EKS 中进行 application performance monitoring 的最有效方法是什么？

A. 仅监控基本 system metrics
B. 收集并分析自定义 application metrics
C. 实施包含 distributed tracing、metrics 和 logs 的集成 observability
D. 定期执行手动 performance tests

<details>
<summary>查看答案</summary>

**答案：C. 实施包含 distributed tracing、metrics 和 logs 的集成 observability**

**解释：**
在 Amazon EKS 中进行 application performance monitoring 的最有效方法是实施包含 distributed tracing、metrics 和 logs 的集成 observability。这种全面方法可提供 application performance 的完整可见性，并为 troubleshooting 和 optimization 提供详细信息。

**集成 Observability 的关键组件：**

1. **Distributed Tracing**：
   - 跟踪 services 之间的 request flow
   - 识别 latency bottlenecks
   - 理解 error propagation paths

2. **Metrics**：
   - System 和 resource usage
   - Application performance indicators
   - Business metrics

3. **Logs**：
   - 详细 application events
   - Error 和 exception information
   - Debugging context

4. **Profiling**：
   - CPU 和 memory usage analysis
   - 识别 hotspots 和 bottlenecks
   - 发现 code-level optimization opportunities

**实施方法：**

1. **设置 AWS Distro for OpenTelemetry (ADOT)**：
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

2. **Application Instrumentation**：
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

3. **设置 Amazon Managed Grafana Dashboard**：
   ```bash
   # Create Amazon Managed Grafana workspace
   aws grafana create-workspace \
     --name eks-monitoring \
     --authentication-providers AWS_SSO \
     --permission-type SERVICE_MANAGED \
     --data-sources PROMETHEUS CLOUDWATCH XRAY
   ```

4. **X-Ray Service Map 和 Trace Analysis**：
   ```bash
   # Create X-Ray group
   aws xray create-group \
     --group-name "EKS-Applications" \
     --filter-expression "service(\"order-service\") OR service(\"payment-service\")"
   ```

**关键 Observability Metrics 和 Dimensions：**

1. **核心 Application Performance Indicators**：
   - Request latency (p50, p90, p99)
   - Request throughput (RPS)
   - Error rate
   - Saturation (resource utilization)

2. **关键 Dimensions 和 Labels**：
   - Service 和 endpoint
   - Cluster, namespace, pod
   - Version 和 environment
   - Customer 或 tenant ID

3. **User Experience Metrics**：
   - Page load time
   - API response time
   - User interaction latency
   - Client error rate

**最佳实践：**

1. **实施标准化 Instrumentation**：
   - 使用 OpenTelemetry 等标准
   - 一致的 naming conventions 和 labels
   - 结合 automatic 和 manual instrumentation

2. **确保 Context Propagation**：
   - 在 services 之间传递 trace context
   - 在 asynchronous operations 中保持 context
   - 与 external systems 集成

3. **优化 Sampling Strategy**：
   - 平衡成本和可见性
   - 基于 error 和 latency 的 sampling
   - 优先处理 critical transactions

4. **关联 Observability Data**：
   - 连接 traces、metrics 和 logs
   - 使用 common identifiers 和 labels
   - 集成 dashboard 和 analysis

**实际实施示例：**

1. **Microservices Architecture 的集成 Observability**：
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

2. **使用 Terraform 配置 Observability Infrastructure**：
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

其他选项的问题：
- **A. 仅监控基本 system metrics**：System metrics 对理解 infrastructure status 很重要，但不足以识别 application performance issues 的 root causes。
- **B. 收集并分析自定义 application metrics**：Application metrics 很重要，但理解 distributed systems 中的 service interactions 还需要 tracing 和 logs。
- **D. 定期执行手动 performance tests**：Performance tests 很重要，但它们无法替代实时生产环境中的持续监控，也无法完全模拟真实 user patterns。
</details>
### 5. 在 Amazon EKS 中有效监控 control plane logs 的最佳方式是什么？

A. 通过 SSH 直接访问 control plane nodes
B. 启用 EKS control plane logging 并发送到 CloudWatch Logs
C. 部署自定义 log collectors
D. 定期向 AWS support team 请求 logs

<details>
<summary>查看答案</summary>

**答案：B. 启用 EKS control plane logging 并发送到 CloudWatch Logs**

**解释：**
在 Amazon EKS 中有效监控 control plane logs 的最佳方式是启用 EKS control plane logging，并将 logs 发送到 CloudWatch Logs。此方法利用 EKS 作为 managed service 的特性，能够轻松访问和分析 control plane component logs。

**EKS Control Plane Logging 的主要优势：**

1. **全面 Log Collection**：
   - API server logs
   - Audit logs
   - Authenticator logs
   - Controller manager logs
   - Scheduler logs

2. **Managed Solution**：
   - AWS-managed log collection
   - 无需额外 agents
   - 无需直接访问 control plane

3. **集成分析和 Alerting**：
   - 通过 CloudWatch Logs Insights 进行查询和分析
   - 与 CloudWatch Alarms 集成
   - 长期 log retention 和归档

**实施方法：**

1. **创建 EKS Cluster 时启用 Logging**：
   ```bash
   # Create EKS cluster with all log types enabled
   aws eks create-cluster \
     --name my-cluster \
     --role-arn arn:aws:iam::123456789012:role/EKSClusterRole \
     --resources-vpc-config subnetIds=subnet-12345,subnet-67890,securityGroupIds=sg-12345 \
     --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
   ```

2. **为现有 EKS Cluster 启用 Logging**：
   ```bash
   # Enable all log types for existing cluster
   aws eks update-cluster-config \
     --name my-cluster \
     --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
   ```

3. **仅启用特定 Log Types**：
   ```bash
   # Enable only API server and audit logs
   aws eks update-cluster-config \
     --name my-cluster \
     --logging '{"clusterLogging":[{"types":["api","audit"],"enabled":true},{"types":["authenticator","controllerManager","scheduler"],"enabled":false}]}'
   ```

**关键 Log Types 和用途：**

1. **API Server Logs (api)**：
   - API requests 和 responses
   - Resource creation、modification、deletion
   - Error 和 warning messages

2. **Audit Logs (audit)**：
   - 所有 API calls 的详细记录
   - 跟踪 who、what、when 和 where
   - 满足 security 和 compliance requirements

3. **Authenticator Logs (authenticator)**：
   - 使用 AWS IAM credentials 的 authentication requests
   - Authentication successes 和 failures
   - 调试 permission issues

4. **Controller Manager Logs (controllerManager)**：
   - Controller operations 和 status
   - Resource reconciliation activities
   - Controller errors 和 retries

5. **Scheduler Logs (scheduler)**：
   - Pod scheduling decisions
   - Scheduling failures 和 reasons
   - Resource allocation issues

**Log Analysis 和 Monitoring：**

1. **使用 CloudWatch Logs Insights 查询**：
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

2. **创建 CloudWatch Dashboard**：
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

3. **设置 CloudWatch Alarms**：
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

**最佳实践：**

1. **Selective Log Enablement**：
   - 仅启用必要的 log types
   - 根据 compliance requirements 启用 audit logs
   - 平衡成本和可见性

2. **设置 Log Retention Policy**：
   ```bash
   # Set CloudWatch log group retention period
   aws logs put-retention-policy \
     --log-group-name /aws/eks/my-cluster/cluster \
     --retention-in-days 90
   ```

3. **配置 Log Encryption**：
   ```bash
   # Set CloudWatch log group encryption
   aws logs associate-kms-key \
     --log-group-name /aws/eks/my-cluster/cluster \
     --kms-key-id arn:aws:kms:us-west-2:123456789012:key/1234abcd-12ab-34cd-56ef-1234567890ab
   ```

4. **控制 Log Access**：
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

**实际实施示例：**

1. **使用 Terraform 配置 EKS Cluster Logging**：
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

2. **CloudWatch Logs Insights Dashboard**：
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

其他选项的问题：
- **A. 通过 SSH 直接访问 control plane nodes**：EKS 是 managed service，因此你无法直接访问 control plane nodes。
- **C. 部署自定义 log collectors**：由于 control plane 由 AWS 管理，部署自定义 log collectors 不会让你访问 control plane logs。
- **D. 定期向 AWS support team 请求 logs**：这种方式效率低，不能提供实时监控，也不支持自动分析和 alerting。
</details>
### 6. 在 Amazon EKS 中用于成本优化的最有效监控策略是什么？

A. 收集所有可能的 metrics
B. 专注于监控 resource usage、cost allocation tags 和 idle resources
C. 只关注 performance，不进行 cost monitoring
D. 只查看每月 AWS bills

<details>
<summary>查看答案</summary>

**答案：B. 专注于监控 resource usage、cost allocation tags 和 idle resources**

**解释：**
在 Amazon EKS 中用于成本优化的最有效监控策略是专注于监控 resource usage、cost allocation tags 和 idle resources。这种方法可确保 cluster resources 的高效使用，明确 cost allocation，并通过识别浪费资源来优化成本。

**Cost Optimization Monitoring 的关键组件：**

1. **Resource Usage Monitoring**：
   - CPU、memory、storage utilization
   - Actual usage vs. requests and limits
   - Resource usage trends and patterns

2. **Cost Allocation 和 Tagging**：
   - 按 namespace、service、team 进行 cost analysis
   - 实施并监控 cost allocation tags
   - 按 cost center 和 project 跟踪支出

3. **识别 Idle 和 Wasted Resources**：
   - 未使用的 EBS volumes
   - Over-provisioned resources
   - Idle nodes 和 pods

4. **Cost Anomaly Detection**：
   - 对 unexpected cost increases 发出 alert
   - Cost trend analysis
   - 监控 actual spending vs. budget

**实施方法：**

1. **监控 Kubernetes Resource Usage**：
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

2. **实施 Cost Allocation Tags**：
   ```bash
   # Enable cost allocation tags
   aws ce update-cost-allocation-tags-status \
     --cost-allocation-tags-status '[{"TagKey": "kubernetes.io/cluster/my-cluster", "Status": "Active"}, {"TagKey": "kubernetes.io/namespace", "Status": "Active"}, {"TagKey": "app", "Status": "Active"}, {"TagKey": "team", "Status": "Active"}]'

   # Tag nodes
   aws ec2 create-tags \
     --resources i-1234567890abcdef0 \
     --tags Key=team,Value=platform Key=environment,Value=production
   ```

3. **部署 Kubecost**：
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

4. **设置 AWS Cost Explorer Dashboard**：
   ```bash
   # Create AWS Cost Explorer dashboard
   aws ce create-cost-category \
     --name EKS-Clusters \
     --rule-version "CostCategoryExpression.v1" \
     --rules '[{"Value": "my-cluster-prod", "Rule": {"Tags": {"Key": "kubernetes.io/cluster/my-cluster-prod", "Values": ["owned", "shared"], "MatchOptions": ["EQUALS"]}}}, {"Value": "my-cluster-dev", "Rule": {"Tags": {"Key": "kubernetes.io/cluster/my-cluster-dev", "Values": ["owned", "shared"], "MatchOptions": ["EQUALS"]}}}]'
   ```

**关键 Monitoring Metrics 和 Dimensions：**

1. **Resource Efficiency Metrics**：
   - CPU utilization = used CPU / requested CPU
   - Memory utilization = used memory / requested memory
   - Resource requests vs. limits ratio

2. **Cost Allocation Dimensions**：
   - Cluster
   - Namespace
   - Deployment/StatefulSet
   - Labels (team, application, environment)

3. **Waste Identification Metrics**：
   - Idle pods 的数量（CPU/memory utilization < 5%）
   - Unattached EBS volumes
   - 未使用的 load balancers

**最佳实践：**

1. **优化 Resource Requests 和 Limits**：
   - 根据 actual usage 设置 resource requests
   - 使用 Vertical Pod Autoscaler
   - 定期审查 resource requests

2. **实施有效的 Tagging Strategy**：
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

3. **优化 Auto-scaling**：
   - 调整 Cluster Autoscaler configuration
   - 使用 Karpenter
   - 使用 spot instances

4. **定期成本审查和优化**：
   - 每周/每月成本审查会议
   - 设置成本降低目标
   - 跟踪优化操作

**实际实施示例：**

1. **Grafana Cost Dashboard**：
   ```bash
   # Import Grafana dashboard
   kubectl -n monitoring create configmap cost-dashboard \
     --from-file=cost-dashboard.json
   ```

2. **Resource Request vs. Usage Monitoring Queries**：
   ```
   # Prometheus query examples
   # CPU utilization vs. requests
   sum(rate(container_cpu_usage_seconds_total{namespace="production"}[5m])) by (pod) /
   sum(kube_pod_container_resource_requests{resource="cpu", namespace="production"}) by (pod)

   # Memory utilization vs. requests
   sum(container_memory_working_set_bytes{namespace="production"}) by (pod) /
   sum(kube_pod_container_resource_requests{resource="memory", namespace="production"}) by (pod)
   ```

3. **Cost Optimization Automation Script**：
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

4. **使用 Terraform 配置 Cost Monitoring Infrastructure**：
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

其他选项的问题：
- **A. 收集所有可能的 metrics**：收集所有 metrics 会增加存储成本，重要的 cost optimization signals 可能被埋没在噪音中，并且分析会变得更复杂。
- **C. 只关注 performance，不进行 cost monitoring**：Performance 很重要，但如果没有 cost optimization，可能会产生不必要的支出。
- **D. 只查看每月 AWS bills**：每月账单审查是被动的，不能提供详细的 cost allocation 信息，并且可能错过实时 optimization opportunities。
</details>
