# Amazon EKS Monitoring and Logging

Effective monitoring and logging are essential for maintaining the reliability, availability, and performance of Amazon EKS clusters. This document covers various tools, techniques, and best practices for implementing monitoring and logging in EKS clusters.

## Table of Contents

1. [Monitoring and Logging Overview](#monitoring-and-logging-overview)
2. [EKS Control Plane Logging](#eks-control-plane-logging)
3. [Container Logging](#container-logging)
4. [Cluster Monitoring](#cluster-monitoring)
5. [Alerting and Event Management](#alerting-and-event-management)
6. [Log Analysis and Visualization](#log-analysis-and-visualization)
7. [Monitoring and Logging Best Practices](#monitoring-and-logging-best-practices)
8. [Troubleshooting and Debugging](#troubleshooting-and-debugging)

## Monitoring and Logging Overview

### Importance of Monitoring and Logging

Monitoring and logging in Amazon EKS clusters are important for the following reasons:

1. **Visibility**: Provides visibility into cluster status, performance, and behavior
2. **Issue Detection**: Detects issues early before they become critical
3. **Trend Analysis**: Identifies performance and resource usage trends over time
4. **Capacity Planning**: Forecasts and plans for resource requirements
5. **Security and Auditing**: Detects security events and meets compliance requirements
6. **Troubleshooting**: Enables rapid diagnosis and resolution when issues occur

### Monitoring and Logging Architecture

A comprehensive monitoring and logging architecture for an EKS cluster consists of the following components:

```mermaid
flowchart TD
    subgraph EKS["Amazon EKS Cluster"]
        CP[Control Plane Logs] --> CWL
        subgraph Nodes["Worker Nodes"]
            Pods[Pods/Containers] --> Fluent
            NodeExporter[Node Exporter] --> Prometheus
            kubelet --> Prometheus
        end
    end

    subgraph AWS["AWS Services"]
        CWL[CloudWatch Logs]
        CWM[CloudWatch Metrics]
        XRay[X-Ray]
        ES[Amazon OpenSearch]
    end

    subgraph Monitoring["Monitoring Stack"]
        Prometheus[Prometheus] --> Alertmanager
        Alertmanager[Alertmanager] --> Notification[Notification Channels]
        Prometheus --> Grafana
    end

    subgraph Logging["Logging Stack"]
        Fluent[Fluent Bit/Fluentd] --> CWL
        Fluent --> ES
        ES --> Kibana[OpenSearch Dashboards]
    end

    CWL --> ES
    Prometheus --> CWM

    %% Class definitions
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class CWL,CWM,XRay,ES awsService;
    class CP,Pods,NodeExporter,kubelet,Prometheus,Alertmanager k8sComponent;
    class Fluent,Grafana,Kibana,Notification userApp;
```

### Monitoring and Logging Strategy

Follow these steps to develop an effective monitoring and logging strategy:

1. **Define Objectives**: Define monitoring and logging objectives and requirements
2. **Identify Metrics and Logs**: Identify key metrics and logs to collect
3. **Select Tools**: Select monitoring and logging tools that meet requirements
4. **Establish Baselines**: Establish baselines for normal behavior
5. **Configure Alerts**: Configure alerts for important events and thresholds
6. **Automate**: Automate monitoring and logging processes as much as possible
7. **Regular Review**: Regularly review and improve monitoring and logging strategy

## EKS Control Plane Logging

Amazon EKS provides the ability to send cluster control plane logs to Amazon CloudWatch Logs. This provides visibility into the cluster's control components.

### Control Plane Log Types

EKS supports the following control plane log types:

1. **API Server (api)**: Kubernetes API server logs
2. **Audit (audit)**: Kubernetes audit logs
3. **Authenticator (authenticator)**: AWS IAM authenticator logs
4. **Controller Manager (controllerManager)**: Controller manager logs
5. **Scheduler (scheduler)**: Kubernetes scheduler logs

### Enabling Control Plane Logging

You can enable control plane logging using the AWS Management Console, AWS CLI, or eksctl:

#### Using AWS CLI

```bash
aws eks update-cluster-config \
  --region us-west-2 \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

#### Using eksctl

```bash
eksctl utils update-cluster-logging \
  --region us-west-2 \
  --cluster my-cluster \
  --enable-types api,audit,authenticator,controllerManager,scheduler
```

### Querying Control Plane Logs

You can query control plane logs using CloudWatch Logs Insights:

#### API Server Error Query

```
fields @timestamp, @message
| filter @message like /Error/
| sort @timestamp desc
| limit 20
```

#### Authentication Failure Query

```
fields @timestamp, @message
| filter @message like /authentication failed/
| sort @timestamp desc
| limit 20
```

#### Audit Log Query

```
fields @timestamp, @message
| filter @message like /responseStatus.code="403"/
| sort @timestamp desc
| limit 20
```

### Control Plane Log Retention and Cost Management

You can configure log retention periods in CloudWatch Logs to manage costs:

```bash
aws logs put-retention-policy \
  --log-group-name /aws/eks/my-cluster/cluster \
  --retention-in-days 30
```

## Container Logging

Container logs provide important information for diagnosing and resolving application issues. In EKS, you can collect and manage container logs in various ways.

### Logging Architecture

A typical container logging architecture in EKS looks like this:

```mermaid
flowchart LR
    subgraph Node["Worker Node"]
        Containers[Containers] --> |stdout/stderr| kubelet
        kubelet --> |/var/log/containers/| LogAgent[Log Agent]
    end

    LogAgent --> CWL[CloudWatch Logs]
    LogAgent --> ES[Amazon OpenSearch]
    LogAgent --> S3[Amazon S3]

    %% Class definitions
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class CWL,ES,S3 awsService;
    class kubelet k8sComponent;
    class Containers userApp;
    class LogAgent default;
```

### Log Collection with Fluent Bit

Fluent Bit is a lightweight log collector widely used for collecting container logs in EKS clusters:

#### Fluent Bit Installation

Install Fluent Bit using Helm:

```bash
helm repo add aws-for-fluent-bit https://aws.github.io/eks-charts
helm repo update
helm install aws-for-fluent-bit aws-for-fluent-bit/aws-for-fluent-bit \
  --namespace kube-system \
  --set cloudWatch.region=us-west-2 \
  --set cloudWatch.logGroupName=/aws/eks/my-cluster/fluentbit
```

#### Fluent Bit Configuration

ConfigMap for custom configuration:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: kube-system
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush         5
        Log_Level     info
        Daemon        off
        Parsers_File  parsers.conf

    [INPUT]
        Name              tail
        Tag               kube.*
        Path              /var/log/containers/*.log
        Parser            docker
        DB                /var/log/flb_kube.db
        Mem_Buf_Limit     5MB
        Skip_Long_Lines   On
        Refresh_Interval  10

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
        Name              cloudwatch
        Match             kube.*
        region            us-west-2
        log_group_name    /aws/eks/my-cluster/fluentbit
        log_stream_prefix container-
        auto_create_group true

    [OUTPUT]
        Name              es
        Match             kube.*
        Host              search-my-es-domain.us-west-2.es.amazonaws.com
        Port              443
        TLS               On
        AWS_Auth          On
        AWS_Region        us-west-2
        Index             eks-logs
        Suppress_Type_Name On
```

### CloudWatch Container Insights

CloudWatch Container Insights collects, aggregates, and summarizes metrics and logs from containerized applications and microservices:

#### Installing Container Insights

```bash
ClusterName=my-cluster
RegionName=us-west-2
FluentBitHttpPort='2020'
FluentBitReadFromHead='Off'
[[ ${FluentBitReadFromHead} = 'On' ]] && FluentBitReadFromTail='Off'|| FluentBitReadFromTail='On'
[[ -z ${FluentBitHttpPort} ]] && FluentBitHttpServer='Off' || FluentBitHttpServer='On'

kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluent-bit-quickstart.yaml
```

#### Container Insights Dashboard

Access the Container Insights dashboard in the CloudWatch console to monitor:
- Node, pod, and container-level CPU and memory usage
- Network and disk I/O
- Pod and container status
- Cluster failures and events

### Custom Logging Solutions

You can implement custom logging solutions for specific requirements:

#### EFK (Elasticsearch, Fluentd, Kibana) Stack

```bash
# Install Elasticsearch
helm repo add elastic https://helm.elastic.co
helm repo update
helm install elasticsearch elastic/elasticsearch \
  --namespace logging \
  --create-namespace \
  --set replicas=3

# Install Fluentd
helm install fluentd stable/fluentd \
  --namespace logging \
  --set output.host=elasticsearch-master.logging.svc.cluster.local

# Install Kibana
helm install kibana elastic/kibana \
  --namespace logging \
  --set service.type=LoadBalancer
```

#### PLG (Promtail, Loki, Grafana) Stack

```bash
# Install Loki and Promtail
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
helm install loki grafana/loki-stack \
  --namespace logging \
  --create-namespace \
  --set grafana.enabled=true \
  --set promtail.enabled=true \
  --set loki.persistence.enabled=true \
  --set loki.persistence.size=10Gi
```

### Log Structuring and Parsing

It's recommended to use structured log formats for effective log analysis:

#### JSON Log Format

Output logs in JSON format from your application:

```json
{
  "timestamp": "2025-07-11T13:00:00Z",
  "level": "INFO",
  "message": "Request processed successfully",
  "request_id": "12345",
  "user_id": "user-789",
  "duration_ms": 45,
  "status_code": 200
}
```

#### Log Parser Configuration

Configuration for log parsing in Fluent Bit:

```
[PARSER]
    Name        json
    Format      json
    Time_Key    timestamp
    Time_Format %Y-%m-%dT%H:%M:%S%z
```

## Cluster Monitoring

Effective cluster monitoring is essential for tracking the status, performance, and resource usage of your EKS cluster. This section explores various tools and techniques for monitoring EKS clusters.

```mermaid
flowchart TD
    subgraph Monitoring_Solutions ["Monitoring Solutions"]
        subgraph AWS_Solutions ["AWS Solutions"]
            CW_CI["CloudWatch
                Container Insights"]
            CW_LA["CloudWatch
                Logs Insights"]
            CW_Alarms["CloudWatch
                Alarms"]
            AMP["Amazon Managed
                Prometheus"]
            AMG["Amazon Managed
                Grafana"]
        end

        subgraph K8s_Solutions ["Kubernetes Solutions"]
            Prometheus[Prometheus]
            Grafana[Grafana]
            Kube_State[kube-state-metrics]
            Node_Exporter[Node Exporter]
            K8s_Dashboard["Kubernetes
                Dashboard"]
        end

        subgraph Tracing_Solutions ["Tracing Solutions"]
            XRay[AWS X-Ray]
            Jaeger[Jaeger]
            OpenTelemetry[OpenTelemetry]
        end
    end

    subgraph Monitoring_Targets ["Monitoring Targets"]
        subgraph Cluster_Level ["Cluster Level"]
            Control_Plane[Control Plane]
            API_Server[API Server]
            Scheduler[Scheduler]
            Controller[Controller Manager]
        end

        subgraph Node_Level ["Node Level"]
            CPU[CPU Usage]
            Memory[Memory Usage]
            Disk[Disk I/O]
            Network[Network I/O]
        end

        subgraph Pod_Level ["Pod Level"]
            Pod_CPU[Pod CPU]
            Pod_Memory[Pod Memory]
            Pod_Network[Pod Network]
            Restarts[Restart Count]
        end
    end

    CW_CI --> Cluster_Level
    CW_CI --> Node_Level
    CW_CI --> Pod_Level

    Prometheus --> Kube_State
    Prometheus --> Node_Exporter
    Kube_State --> Cluster_Level
    Node_Exporter --> Node_Level

    Prometheus --> Grafana
    AMP --> AMG

    XRay --> API_Server
    OpenTelemetry --> Pod_Level

    %% Class definitions
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class CW_CI,CW_LA,CW_Alarms,AMP,AMG,XRay awsService;
    class Prometheus,Grafana,Kube_State,Node_Exporter,K8s_Dashboard,Control_Plane,API_Server,Scheduler,Controller k8sComponent;
    class Jaeger,OpenTelemetry userApp;
    class CPU,Memory,Disk,Network,Pod_CPU,Pod_Memory,Pod_Network,Restarts default;
```

### CloudWatch Container Insights

Amazon CloudWatch Container Insights collects, aggregates, and summarizes metrics, logs, and events from containerized applications and microservices:

#### Enabling Container Insights

Enable Container Insights using the CloudWatch agent:

```bash
ClusterName=my-cluster
RegionName=us-west-2
FluentBitHttpPort='2020'
FluentBitReadFromHead='Off'
[[ ${FluentBitReadFromHead} = 'On' ]] && FluentBitReadFromTail='Off'|| FluentBitReadFromTail='On'
[[ -z ${FluentBitHttpPort} ]] && FluentBitHttpServer='Off' || FluentBitHttpServer='On'

curl https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluent-bit-quickstart.yaml | sed 's/{{cluster_name}}/'${ClusterName}'/;s/{{region_name}}/'${RegionName}'/;s/{{http_server_toggle}}/"'${FluentBitHttpServer}'"/;s/{{http_server_port}}/"'${FluentBitHttpPort}'"/;s/{{read_from_head}}/"'${FluentBitReadFromHead}'"/;s/{{read_from_tail}}/"'${FluentBitReadFromTail}'"/' | kubectl apply -f -
```

#### Container Insights Metrics

Container Insights collects the following metrics:

- **Cluster level**: Node count, pod count, failed pod count
- **Node level**: CPU usage, memory usage, network I/O, disk I/O
- **Pod level**: CPU usage, memory usage, network I/O
- **Service level**: Pod count, CPU usage, memory usage

#### Container Insights Dashboard

Access the Container Insights dashboard in the CloudWatch console to visualize cluster performance:

1. Log in to AWS Management Console
2. Navigate to CloudWatch service
3. Select "Insights" > "Container Insights" from the left navigation pane
4. Select cluster, node, pod, or service view

#### Container Insights Alerts

Set up CloudWatch alarms to receive notifications when metrics exceed specific thresholds:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "High-CPU-Cluster" \
  --alarm-description "Alarm when cluster CPU exceeds 80%" \
  --metric-name pod_cpu_utilization \
  --namespace ContainerInsights \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ClusterName,Value=my-cluster \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-west-2:123456789012:my-topic
```
### Prometheus and Grafana

Prometheus is a time-series database and monitoring system, and Grafana is a dashboard tool for visualizing metrics. You can use these two tools together for comprehensive monitoring of your EKS cluster.

#### Amazon Managed Service for Prometheus and Grafana

AWS provides managed services for Prometheus and Grafana:

1. **Amazon Managed Service for Prometheus (AMP)** setup:

```bash
# Create AMP workspace
aws amp create-workspace --alias my-amp-workspace

# Install Prometheus server and configure remote write to AMP
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/prometheus \
  --namespace prometheus \
  --create-namespace \
  --set server.remoteWrite[0].url=https://aps-workspaces.us-west-2.amazonaws.com/workspaces/ws-12345678-1234-1234-1234-123456789012/api/v1/remote_write \
  --set server.remoteWrite[0].sigv4.region=us-west-2
```

2. **Amazon Managed Grafana (AMG)** setup:

```bash
# Create AMG workspace
aws grafana create-workspace \
  --name my-grafana-workspace \
  --authentication-providers AWS_SSO \
  --permission-type SERVICE_MANAGED

# Add AMP data source
aws grafana create-workspace-service-account \
  --workspace-id g-12345678 \
  --name amp-datasource \
  --service-account-role ADMIN
```

#### Self-Managed Prometheus and Grafana

You can also deploy self-managed Prometheus and Grafana to your EKS cluster:

1. **Install kube-prometheus-stack**:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set grafana.service.type=LoadBalancer
```

2. **Access Grafana**:

```bash
# Get Grafana service URL
kubectl get svc -n monitoring monitoring-grafana -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

# Get default username and password
kubectl get secret -n monitoring monitoring-grafana -o jsonpath='{.data.admin-user}' | base64 --decode
kubectl get secret -n monitoring monitoring-grafana -o jsonpath='{.data.admin-password}' | base64 --decode
```

#### Key Prometheus Metrics

Prometheus collects the following important Kubernetes metrics:

- **Node metrics**: CPU, memory, disk, network usage
- **Pod metrics**: CPU, memory usage, restart count
- **Container metrics**: CPU, memory usage, filesystem usage
- **API server metrics**: Request latency, request count, error rate
- **etcd metrics**: Latency, disk I/O, leader changes

#### Useful Grafana Dashboards

You can import the following useful dashboards in Grafana:

1. **Kubernetes Cluster Monitoring** (ID: 15661)
2. **Node Exporter Full** (ID: 1860)
3. **Kubernetes Pod Monitoring** (ID: 6417)
4. **Kubernetes API Server** (ID: 12006)
5. **Kubernetes Resource Requests/Limits** (ID: 13770)

#### PromQL Query Examples

You can write useful queries using Prometheus Query Language (PromQL):

```
# CPU usage by node
sum(rate(node_cpu_seconds_total{mode!="idle"}[5m])) by (instance) / count(node_cpu_seconds_total{mode="idle"}) by (instance) * 100

# Memory usage by pod (top 10)
topk(10, sum(container_memory_usage_bytes{container!=""}) by (pod))

# Container restart count
sum(kube_pod_container_status_restarts_total) by (pod)

# Disk usage percentage by node
100 - ((node_filesystem_avail_bytes{mountpoint="/"} * 100) / node_filesystem_size_bytes{mountpoint="/"})
```
### Distributed Tracing with AWS X-Ray

AWS X-Ray collects data about the requests that your application processes and uses this to identify application issues and optimization opportunities.

#### X-Ray Setup

1. **Install X-Ray daemon**:

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: xray-daemon
  namespace: default
spec:
  selector:
    matchLabels:
      app: xray-daemon
  template:
    metadata:
      labels:
        app: xray-daemon
    spec:
      containers:
      - name: xray-daemon
        image: amazon/aws-xray-daemon:latest
        ports:
        - containerPort: 2000
          hostPort: 2000
          protocol: UDP
        resources:
          limits:
            memory: 256Mi
          requests:
            memory: 256Mi
        env:
        - name: AWS_REGION
          value: us-west-2
      serviceAccountName: xray-daemon
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: xray-daemon
  namespace: default
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: xray-daemon
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: xray-daemon
  namespace: default
```

2. **Integrate X-Ray SDK into your application**:

Java application example:

```java
import com.amazonaws.xray.AWSXRay;
import com.amazonaws.xray.AWSXRayRecorderBuilder;
import com.amazonaws.xray.plugins.EKSPlugin;

public class Application {
    static {
        AWSXRayRecorderBuilder builder = AWSXRayRecorderBuilder.standard().withPlugin(new EKSPlugin());
        AWSXRay.setGlobalRecorder(builder.build());
    }

    // Application code
}
```

#### X-Ray Service Map

Use the X-Ray service map to visualize relationships and communication between components in your microservices architecture:

1. Log in to AWS Management Console
2. Navigate to X-Ray service
3. Select "Service Map" from the left navigation pane
4. Check latency, errors, and fault points between services

#### X-Ray Analysis and Insights

Use X-Ray Analytics to analyze trace data and identify performance bottlenecks:

1. Navigate to X-Ray service in AWS Management Console
2. Select "Analytics" from the left navigation pane
3. Analyze response time distribution, error rate, and fault points

### Kubernetes Dashboard

The Kubernetes Dashboard provides a web-based UI for managing cluster resources and troubleshooting issues:

#### Installing Kubernetes Dashboard

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml

# Create service account and cluster role binding for dashboard access
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: admin-user
  namespace: kubernetes-dashboard
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: admin-user
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: admin-user
  namespace: kubernetes-dashboard
EOF

# Generate access token
kubectl -n kubernetes-dashboard create token admin-user
```

#### Accessing the Dashboard

```bash
# Start dashboard proxy
kubectl proxy

# Access the following URL in browser
# http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/
```

### Custom Metrics and Monitoring

You can implement custom solutions for collecting and monitoring application-specific metrics:

#### Prometheus Client Library Integration

Integrate Prometheus client libraries into your application to expose custom metrics:

Java application example:

```java
import io.prometheus.client.Counter;
import io.prometheus.client.Histogram;
import io.prometheus.client.exporter.HTTPServer;

public class Application {
    static final Counter requests = Counter.build()
        .name("app_requests_total")
        .help("Total requests.")
        .register();

    static final Histogram requestLatency = Histogram.build()
        .name("app_request_latency_seconds")
        .help("Request latency in seconds.")
        .register();

    public static void main(String[] args) throws IOException {
        HTTPServer server = new HTTPServer(8080);
        // Application code
    }

    public void processRequest() {
        requests.inc();
        Histogram.Timer timer = requestLatency.startTimer();
        try {
            // Process request
        } finally {
            timer.observeDuration();
        }
    }
}
```

#### Collecting Custom Metrics

Use Prometheus ServiceMonitor to collect custom metrics:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: app-monitor
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: my-app
  endpoints:
  - port: metrics
    interval: 15s
    path: /metrics
```

#### Custom Dashboards

Create custom dashboards in Grafana to visualize application metrics:

1. Log in to Grafana
2. Click the "+" icon and select "Dashboard"
3. Click "Add panel"
4. Select "Prometheus" as the data source
5. Write a PromQL query (e.g., `rate(app_requests_total[5m])`)
6. Configure panel title, description, and visualization type
7. Click "Save"
## Alerting and Event Management

Effective alerting and event management are essential for rapidly detecting and responding to issues in your EKS cluster. This section explores various tools and techniques for managing alerts and events in EKS clusters.

```mermaid
flowchart TD
    subgraph Alert_Sources ["Alert Sources"]
        subgraph Metrics ["Metric-based"]
            CW_Metrics[CloudWatch Metrics]
            Prom_Metrics[Prometheus Metrics]
            Custom_Metrics[Custom Metrics]
        end

        subgraph Logs ["Log-based"]
            CW_Logs[CloudWatch Logs]
            ES_Logs[OpenSearch Logs]
            Loki_Logs[Loki Logs]
        end

        subgraph Events ["Event-based"]
            K8s_Events[Kubernetes Events]
            AWS_Events[AWS Events]
            App_Events[Application Events]
        end
    end

    subgraph Alert_Processing ["Alert Processing"]
        CW_Alarms[CloudWatch Alarms]
        Prom_AM["Prometheus
                Alertmanager"]
        EventBridge[Amazon EventBridge]
        Event_Router[Event Router]
    end

    subgraph Notification_Channels ["Notification Channels"]
        SNS[Amazon SNS]
        SQS[Amazon SQS]
        Lambda[AWS Lambda]
        Email[Email]
        Slack[Slack]
        PagerDuty[PagerDuty]
        OpsGenie[OpsGenie]
    end

    CW_Metrics --> CW_Alarms
    Prom_Metrics --> Prom_AM
    Custom_Metrics --> Prom_AM

    CW_Logs --> CW_Alarms
    ES_Logs --> Event_Router
    Loki_Logs --> Prom_AM

    K8s_Events --> Event_Router
    AWS_Events --> EventBridge
    App_Events --> Event_Router

    CW_Alarms --> SNS
    Prom_AM --> Slack
    Prom_AM --> PagerDuty
    EventBridge --> Lambda
    EventBridge --> SNS
    Event_Router --> OpsGenie

    SNS --> Email
    SNS --> SQS

    %% Class definitions
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class CW_Metrics,CW_Logs,CW_Alarms,EventBridge,SNS,SQS,Lambda,AWS_Events awsService;
    class K8s_Events,Prom_AM k8sComponent;
    class Prom_Metrics,Custom_Metrics,ES_Logs,Loki_Logs,App_Events,Event_Router,Email,Slack,PagerDuty,OpsGenie userApp;
```

### CloudWatch Alarms

Use Amazon CloudWatch alarms to receive notifications when metrics exceed specific thresholds:

#### Cluster CPU Usage Alarm

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "EKS-Cluster-High-CPU" \
  --alarm-description "Alarm when cluster CPU exceeds 80%" \
  --metric-name pod_cpu_utilization \
  --namespace ContainerInsights \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ClusterName,Value=my-cluster \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-west-2:123456789012:my-topic
```

#### Memory Usage Alarm

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "EKS-Cluster-High-Memory" \
  --alarm-description "Alarm when cluster memory exceeds 80%" \
  --metric-name pod_memory_utilization \
  --namespace ContainerInsights \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ClusterName,Value=my-cluster \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-west-2:123456789012:my-topic
```

#### Disk Usage Alarm

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "EKS-Node-High-Disk" \
  --alarm-description "Alarm when node disk usage exceeds 85%" \
  --metric-name node_filesystem_utilization \
  --namespace ContainerInsights \
  --statistic Maximum \
  --period 300 \
  --threshold 85 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ClusterName,Value=my-cluster \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-west-2:123456789012:my-topic
```

### Prometheus Alertmanager

Prometheus Alertmanager handles alerts generated by Prometheus and routes them to appropriate notification channels:

#### Alertmanager Configuration

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-config
  namespace: monitoring
data:
  alertmanager.yml: |
    global:
      resolve_timeout: 5m
      slack_api_url: 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX'

    route:
      group_by: ['alertname', 'job']
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 12h
      receiver: 'slack-notifications'
      routes:
      - match:
          severity: critical
        receiver: 'slack-notifications'
        continue: true

    receivers:
    - name: 'slack-notifications'
      slack_configs:
      - channel: '#eks-alerts'
        send_resolved: true
        title: '[{{ .Status | toUpper }}] {{ .CommonLabels.alertname }}'
        text: >-
          {{ range .Alerts }}
            *Alert:* {{ .Annotations.summary }}
            *Description:* {{ .Annotations.description }}
            *Severity:* {{ .Labels.severity }}
            *Details:*
            {{ range .Labels.SortedPairs }} • *{{ .Name }}:* `{{ .Value }}`
            {{ end }}
          {{ end }}
```

#### Alert Rules Configuration

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: kubernetes-alerts
  namespace: monitoring
spec:
  groups:
  - name: kubernetes
    rules:
    - alert: KubernetesPodCrashLooping
      expr: rate(kube_pod_container_status_restarts_total[5m]) * 60 * 5 > 5
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "Pod {{ $labels.namespace }}/{{ $labels.pod }} is crash looping"
        description: "Pod {{ $labels.namespace }}/{{ $labels.pod }} is restarting {{ $value }} times / 5 minutes"

    - alert: KubernetesNodeMemoryPressure
      expr: kube_node_status_condition{condition="MemoryPressure", status="true"} == 1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Node {{ $labels.node }} is under memory pressure"
        description: "Node {{ $labels.node }} has been under memory pressure for more than 5 minutes"

    - alert: KubernetesNodeDiskPressure
      expr: kube_node_status_condition{condition="DiskPressure", status="true"} == 1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Node {{ $labels.node }} is under disk pressure"
        description: "Node {{ $labels.node }} has been under disk pressure for more than 5 minutes"
```

### EventBridge Event Rules

Use Amazon EventBridge to create rules that respond to events in your EKS cluster:

#### EKS Cluster State Change Event Rule

```bash
aws events put-rule \
  --name "EKS-Cluster-State-Change" \
  --event-pattern '{
    "source": ["aws.eks"],
    "detail-type": ["EKS Cluster State Change"],
    "detail": {
      "clusterName": ["my-cluster"]
    }
  }'

aws events put-targets \
  --rule "EKS-Cluster-State-Change" \
  --targets '[
    {
      "Id": "1",
      "Arn": "arn:aws:sns:us-west-2:123456789012:my-topic"
    }
  ]'
```

#### EKS Node Group Event Rule

```bash
aws events put-rule \
  --name "EKS-NodeGroup-Events" \
  --event-pattern '{
    "source": ["aws.eks"],
    "detail-type": ["EKS Node Group State Change"],
    "detail": {
      "clusterName": ["my-cluster"]
    }
  }'

aws events put-targets \
  --rule "EKS-NodeGroup-Events" \
  --targets '[
    {
      "Id": "1",
      "Arn": "arn:aws:sns:us-west-2:123456789012:my-topic"
    }
  ]'
```

### Kubernetes Event Monitoring

Kubernetes events provide information about important activities occurring in the cluster:

#### Installing Event Monitoring Tools

```bash
# Install event-exporter
kubectl apply -f https://raw.githubusercontent.com/opsgenie/kubernetes-event-exporter/master/deploy/01-cluster-role.yaml
kubectl apply -f https://raw.githubusercontent.com/opsgenie/kubernetes-event-exporter/master/deploy/02-service-account.yaml
kubectl apply -f https://raw.githubusercontent.com/opsgenie/kubernetes-event-exporter/master/deploy/03-cluster-role-binding.yaml
```

#### Event Exporter Configuration

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: event-exporter-config
  namespace: default
data:
  config.yaml: |
    logLevel: info
    logFormat: json
    route:
      routes:
        - match:
            - type: "Warning"
          receivers:
            - webhook:
                endpoint: "http://alertmanager:9093/api/v1/alerts"
                headers:
                  Content-Type: application/json
        - match:
            - type: "Normal"
              reason: "Created|Started|Killing|Scheduled|Pulled"
          receivers:
            - file:
                path: "/tmp/normal-events.log"
    receivers:
      - name: "dump"
        file:
          path: "/tmp/all-events.log"
      - name: "slack"
        slack:
          channel: "#kubernetes-events"
          token: "xoxb-1234-1234-1234"
```

#### Event Exporter Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: event-exporter
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: event-exporter
  template:
    metadata:
      labels:
        app: event-exporter
    spec:
      serviceAccountName: event-exporter
      containers:
      - name: event-exporter
        image: opsgenie/kubernetes-event-exporter:latest
        args:
        - -conf=/etc/config/config.yaml
        volumeMounts:
        - name: config
          mountPath: /etc/config
      volumes:
      - name: config
        configMap:
          name: event-exporter-config
```

### Notification Channel Integration

You can integrate various notification channels to deliver alerts to your team:

#### Slack Integration

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: slack-webhook
  namespace: monitoring
type: Opaque
stringData:
  url: https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
---
apiVersion: notification.toolkit.fluxcd.io/v1beta1
kind: Provider
metadata:
  name: slack
  namespace: monitoring
spec:
  type: slack
  channel: eks-alerts
  secretRef:
    name: slack-webhook
```

#### PagerDuty Integration

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: pagerduty-api-key
  namespace: monitoring
type: Opaque
stringData:
  token: your-pagerduty-api-key
---
apiVersion: notification.toolkit.fluxcd.io/v1beta1
kind: Provider
metadata:
  name: pagerduty
  namespace: monitoring
spec:
  type: pagerduty
  serviceKey: your-pagerduty-service-key
  secretRef:
    name: pagerduty-api-key
```

#### Email Integration

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: smtp-credentials
  namespace: monitoring
type: Opaque
stringData:
  username: your-smtp-username
  password: your-smtp-password
---
apiVersion: notification.toolkit.fluxcd.io/v1beta1
kind: Provider
metadata:
  name: email
  namespace: monitoring
spec:
  type: smtp
  server: smtp.example.com
  port: "587"
  from: eks-alerts@example.com
  to:
  - team@example.com
  secretRef:
    name: smtp-credentials
```

### Alert Management and Escalation

Implement strategies for effectively managing and escalating alerts:

#### Alert Severity Levels

Classify alerts into the following severity levels:

- **Critical**: Severe issues requiring immediate action
- **Warning**: Issues requiring attention but not immediate action
- **Info**: Informational alerts

#### Alert Escalation Policy

Implement alert escalation policies using tools like PagerDuty:

1. **First Response**: Alert on-call engineer
2. **Escalation 1**: Alert backup engineer if no response after 15 minutes
3. **Escalation 2**: Alert team lead if no response after 30 minutes
4. **Escalation 3**: Alert manager if no response after 45 minutes

#### Reducing Alert Fatigue

Implement strategies to reduce alert fatigue:

1. **Alert Grouping**: Group related alerts to reduce duplicate notifications
2. **Alert Filtering**: Filter to deliver only important alerts
3. **Alert Throttling**: Limit frequency of repeated alerts
4. **Alert Time Windows**: Deliver non-business-critical alerts only during business hours
## Log Analysis and Visualization

Log analysis and visualization play an important role in diagnosing and resolving issues occurring in your EKS cluster. This section explores various tools and techniques for analyzing and visualizing logs in EKS clusters.

```mermaid
flowchart TD
    subgraph Log_Sources ["Log Sources"]
        CP_Logs[Control Plane Logs]
        Container_Logs[Container Logs]
        App_Logs[Application Logs]
        AWS_Service_Logs[AWS Service Logs]
    end

    subgraph Log_Collection ["Log Collection"]
        Fluent_Bit[Fluent Bit]
        Fluentd[Fluentd]
        CloudWatch_Agent[CloudWatch Agent]
        Vector[Vector]
    end

    subgraph Log_Storage ["Log Storage"]
        CW_Logs[CloudWatch Logs]
        OpenSearch[Amazon OpenSearch]
        S3[Amazon S3]
        Loki[Grafana Loki]
    end

    subgraph Log_Analysis ["Log Analysis"]
        CW_Insights[CloudWatch Logs Insights]
        OS_Dashboards[OpenSearch Dashboards]
        Athena[Amazon Athena]
        Grafana_Explore[Grafana Explore]
    end

    subgraph Visualization ["Visualization"]
        OS_Visualizations[OpenSearch Visualizations]
        Grafana_Dashboards[Grafana Dashboards]
        QuickSight[Amazon QuickSight]
        Custom_Dashboards[Custom Dashboards]
    end

    CP_Logs --> CW_Logs
    Container_Logs --> Fluent_Bit
    App_Logs --> Fluent_Bit
    AWS_Service_Logs --> CW_Logs

    Fluent_Bit --> CW_Logs
    Fluent_Bit --> OpenSearch
    Fluent_Bit --> S3
    Fluentd --> Loki
    CloudWatch_Agent --> CW_Logs
    Vector --> OpenSearch

    CW_Logs --> CW_Insights
    OpenSearch --> OS_Dashboards
    S3 --> Athena
    Loki --> Grafana_Explore

    CW_Insights --> Custom_Dashboards
    OS_Dashboards --> OS_Visualizations
    Athena --> QuickSight
    Grafana_Explore --> Grafana_Dashboards

    %% Class definitions
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class CW_Logs,CW_Insights,OpenSearch,S3,Athena,QuickSight,CloudWatch_Agent,AWS_Service_Logs awsService;
    class CP_Logs k8sComponent;
    class Fluent_Bit,Fluentd,Vector,Container_Logs,App_Logs userApp;
    class OS_Dashboards,OS_Visualizations,Grafana_Dashboards,Grafana_Explore,Custom_Dashboards,Loki dataStore;
```

### CloudWatch Logs Insights

Use CloudWatch Logs Insights to query and analyze logs from your EKS cluster:

#### Container Log Query

```
fields @timestamp, kubernetes.pod_name, log
| filter kubernetes.namespace_name = "default"
| filter kubernetes.container_name = "app"
| filter log like /ERROR/
| sort @timestamp desc
| limit 20
```

#### API Server Error Query

```
fields @timestamp, @message
| filter @logStream like /kube-apiserver/
| filter @message like /Error/
| sort @timestamp desc
| limit 20
```

#### Authentication Failure Query

```
fields @timestamp, @message
| filter @logStream like /authenticator/
| filter @message like /authentication failed/
| sort @timestamp desc
| limit 20
```

#### Log Pattern Analysis

```
fields @timestamp, @message
| parse @message "* * * [*] *" as date, time, level, component, message
| stats count(*) as count by level, component
| sort count desc
```

### Amazon OpenSearch Service

Use Amazon OpenSearch Service (formerly Amazon Elasticsearch Service) to store, analyze, and visualize logs from your EKS cluster:

#### Creating OpenSearch Domain

```bash
aws opensearch create-domain \
  --domain-name eks-logs \
  --engine-version OpenSearch_1.3 \
  --cluster-config InstanceType=r6g.large.search,InstanceCount=2 \
  --ebs-options EBSEnabled=true,VolumeType=gp3,VolumeSize=100 \
  --node-to-node-encryption-options Enabled=true \
  --encryption-at-rest-options Enabled=true \
  --domain-endpoint-options EnforceHTTPS=true \
  --advanced-security-options Enabled=true,InternalUserDatabaseEnabled=true,MasterUserOptions='{MasterUserName=admin,MasterUserPassword=Admin123!}' \
  --access-policies '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":"*"},"Action":"es:*","Resource":"arn:aws:es:us-west-2:123456789012:domain/eks-logs/*"}]}'
```

#### Sending Logs to OpenSearch Using Fluent Bit

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: kube-system
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush         5
        Log_Level     info
        Daemon        off
        Parsers_File  parsers.conf

    [INPUT]
        Name              tail
        Tag               kube.*
        Path              /var/log/containers/*.log
        Parser            docker
        DB                /var/log/flb_kube.db
        Mem_Buf_Limit     5MB
        Skip_Long_Lines   On
        Refresh_Interval  10

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
        Name            es
        Match           kube.*
        Host            search-eks-logs-abcdefghijklmnopqrstuvwxyz.us-west-2.es.amazonaws.com
        Port            443
        TLS             On
        AWS_Auth        On
        AWS_Region      us-west-2
        Index           eks-logs
        Suppress_Type_Name On
```

#### Log Visualization with OpenSearch Dashboards

Create the following visualizations in OpenSearch Dashboards:

1. **Log Explorer**: Log search and filtering
2. **Dashboards**: Create dashboards based on log data
3. **Visualizations**: Create charts and graphs based on log data
4. **Alerts**: Configure alerts based on log patterns

### Grafana Loki

Grafana Loki is a log aggregation system that uses a label-based approach similar to Prometheus:

#### Installing Loki

```bash
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
helm install loki grafana/loki-stack \
  --namespace logging \
  --create-namespace \
  --set grafana.enabled=true \
  --set promtail.enabled=true \
  --set loki.persistence.enabled=true \
  --set loki.persistence.size=10Gi
```

#### LogQL Query Examples

```
# Search error logs in a specific namespace
{namespace="default"} |= "ERROR"

# Search logs for a specific pod
{namespace="default", pod=~"app-.*"} | json

# Count logs by log level
sum by (level) (count_over_time({namespace="default"} | json | level=~"info|warn|error" [5m]))
```

#### Creating Grafana Dashboards

Create log dashboards in Grafana using the Loki data source:

1. Log in to Grafana
2. Click the "+" icon and select "Dashboard"
3. Click "Add panel"
4. Select "Loki" as the data source
5. Write a LogQL query
6. Configure panel title, description, and visualization type
7. Click "Save"

### AWS CloudTrail

Use AWS CloudTrail to log and analyze AWS API calls related to your EKS cluster:

#### Creating CloudTrail Trail

```bash
aws cloudtrail create-trail \
  --name eks-api-trail \
  --s3-bucket-name my-cloudtrail-bucket \
  --is-multi-region-trail \
  --include-global-service-events

aws cloudtrail start-logging --name eks-api-trail
```

#### Filtering CloudTrail Events

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventSource,AttributeValue=eks.amazonaws.com
```

#### CloudTrail Lake Query

```sql
SELECT eventTime, eventName, userIdentity.arn, requestParameters
FROM eks_events
WHERE eventSource = 'eks.amazonaws.com'
  AND eventName LIKE '%Cluster%'
  AND eventTime >= '2025-07-01T00:00:00Z'
  AND eventTime <= '2025-07-11T23:59:59Z'
ORDER BY eventTime DESC
```

### Log Analysis Best Practices

Best practices for effectively analyzing logs from your EKS cluster:

#### Structured Logging

Use structured log formats (e.g., JSON) in your applications:

```json
{
  "timestamp": "2025-07-11T13:00:00Z",
  "level": "INFO",
  "message": "Request processed successfully",
  "request_id": "12345",
  "user_id": "user-789",
  "duration_ms": 45,
  "status_code": 200
}
```

#### Correlation IDs

Use correlation IDs to track requests across distributed systems:

```java
import org.slf4j.MDC;

public class RequestHandler {
    public void handleRequest(Request request) {
        String correlationId = request.getHeader("X-Correlation-ID");
        if (correlationId == null) {
            correlationId = UUID.randomUUID().toString();
        }

        MDC.put("correlation_id", correlationId);

        try {
            // Process request
        } finally {
            MDC.remove("correlation_id");
        }
    }
}
```

#### Using Log Levels

Use appropriate log levels to indicate the importance of logs:

- **ERROR**: Application errors and exceptions
- **WARN**: Potential problems or unexpected situations
- **INFO**: General application events
- **DEBUG**: Detailed information useful for debugging
- **TRACE**: Very detailed debugging information

#### Log Retention Policy

Set log retention policies based on cost and compliance requirements:

```bash
# Set CloudWatch Logs log group retention period
aws logs put-retention-policy \
  --log-group-name /aws/eks/my-cluster/cluster \
  --retention-in-days 30

# Set S3 bucket lifecycle policy
aws s3api put-bucket-lifecycle-configuration \
  --bucket my-logs-bucket \
  --lifecycle-configuration file://lifecycle-config.json
```

lifecycle-config.json:
```json
{
  "Rules": [
    {
      "ID": "Delete old logs",
      "Status": "Enabled",
      "Prefix": "logs/",
      "Expiration": {
        "Days": 90
      }
    },
    {
      "ID": "Archive old logs",
      "Status": "Enabled",
      "Prefix": "logs/",
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        },
        {
          "Days": 60,
          "StorageClass": "GLACIER"
        }
      ]
    }
  ]
}
```
## Monitoring and Logging Best Practices

Let's explore best practices for effectively implementing monitoring and logging in EKS clusters.

### Monitoring Best Practices

#### Multi-Layer Monitoring

Monitor all layers of your EKS cluster:

1. **Infrastructure Layer**: EC2 instances, VPC, subnets, security groups
2. **Cluster Layer**: Control plane, nodes, pods, services
3. **Application Layer**: Application performance, user experience

#### Golden Signals Monitoring

Focus on the "4 Golden Signals" suggested in Google's SRE book:

1. **Latency**: Time taken to process requests
2. **Traffic**: Number of requests to the system
3. **Errors**: Rate of failed requests
4. **Saturation**: How "full" the system is (e.g., memory usage)

#### Proactive Monitoring

Implement proactive monitoring to detect issues before they occur:

1. **Trend Analysis**: Analyze resource usage trends over time
2. **Anomaly Detection**: Detect abnormal patterns
3. **Predictive Analysis**: Forecast future resource requirements

#### Automated Scaling

Implement automated scaling based on monitoring data:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

#### Business Metrics Monitoring

Monitor business metrics in addition to technical metrics:

1. **User Activity**: Number of active users, session length
2. **Transactions**: Transaction count, transaction value
3. **Conversion Rate**: User conversion rate, churn rate
4. **SLA Compliance**: Whether Service Level Objectives (SLOs) are being met

### Logging Best Practices

#### Centralized Logging

Aggregate all logs in a central location:

1. **Consistent Format**: Use consistent log format across all applications
2. **Central Repository**: Use central log repository like CloudWatch Logs, OpenSearch, or Loki
3. **Log Forwarding**: Use log forwarding agents like Fluent Bit or Fluentd

#### Include Context Information

Include sufficient context information in logs:

1. **Timestamp**: Accurate timestamp (ISO 8601 format recommended)
2. **Request ID**: Unique ID for request tracking in distributed systems
3. **User Information**: User ID or session ID (excluding personally identifiable information)
4. **Service Information**: Service name, version, instance ID
5. **Error Details**: Error code, error message, stack trace

#### Log Level Filtering

Set appropriate log levels based on environment:

1. **Development Environment**: DEBUG or TRACE level
2. **Staging Environment**: INFO level
3. **Production Environment**: INFO or WARN level (DEBUG can be enabled as needed)

#### Protecting Sensitive Information

Protect sensitive information in logs:

1. **PII Masking**: Mask personally identifiable information (PII)
2. **Exclude Credentials**: Exclude credentials like passwords, tokens, API keys
3. **Encryption**: Encrypt logs at rest and in transit

### Alerting Best Practices

#### Alert Priority

Prioritize alerts to reduce alert fatigue:

1. **P1 (Critical)**: Severe issues requiring immediate action
2. **P2 (High)**: Important issues requiring action within business hours
3. **P3 (Medium)**: Issues requiring action during scheduled maintenance
4. **P4 (Low)**: Informational alerts

#### Alert Grouping

Group related alerts to reduce duplicate notifications:

```yaml
route:
  group_by: ['alertname', 'job', 'instance']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
```

#### Actionable Alerts

Include sufficient information in alerts for troubleshooting:

1. **Clear Title**: Title that clearly describes the issue
2. **Detailed Description**: Detailed description of the cause and impact
3. **Troubleshooting Steps**: Steps or links for troubleshooting
4. **Related Metrics and Logs**: Links to metrics and logs useful for diagnosis

#### Alert Testing

Regularly test your alerting system:

1. **Alert Simulation**: Generate test alerts
2. **Escalation Testing**: Test escalation paths
3. **Fault Injection**: Inject faults in controlled environments

### Cost Optimization Best Practices

#### Log Volume Optimization

Optimize log volume to reduce costs:

1. **Sampling**: Sample high-volume logs
2. **Filtering**: Filter unnecessary logs
3. **Compression**: Compress logs

#### Metric Cardinality Management

Manage metric cardinality to reduce costs:

1. **Label Limits**: Limit the number of labels used in metrics
2. **Aggregation**: Aggregate detailed metrics to higher levels
3. **Sampling**: Sample high-resolution metrics

#### Storage Tiering

Implement cost-effective storage tiering:

1. **Hot Storage**: Recent logs and frequently accessed logs
2. **Warm Storage**: Less frequently accessed logs
3. **Cold Storage**: Archived logs

## Troubleshooting and Debugging

Let's explore various techniques for troubleshooting and debugging issues in EKS clusters.

```mermaid
flowchart TD
    subgraph Troubleshooting_Areas ["Troubleshooting Areas"]
        subgraph Cluster_Issues ["Cluster Issues"]
            Control_Plane[Control Plane Issues]
            Node_Issues[Node Issues]
            Networking[Networking Issues]
            Auth_Issues[Authentication/Authorization Issues]
        end

        subgraph Workload_Issues ["Workload Issues"]
            Pod_Issues[Pod Issues]
            Service_Issues[Service Issues]
            Deployment_Issues[Deployment Issues]
            Resource_Issues[Resource Issues]
        end

        subgraph Common_Problems ["Common Problems"]
            ImagePull[ImagePullBackOff]
            CrashLoop[CrashLoopBackOff]
            NodeNotReady[Node NotReady]
            Connection[Service Connection Issues]
        end
    end

    subgraph Debugging_Tools ["Debugging Tools"]
        subgraph K8s_Tools ["Kubernetes Tools"]
            Kubectl[kubectl]
            K8s_Debug[kubectl debug]
            K8s_Events[kubectl events]
            K8s_Logs[kubectl logs]
        end

        subgraph AWS_Tools ["AWS Tools"]
            AWS_CLI[AWS CLI]
            CloudWatch[CloudWatch]
            CloudTrail[CloudTrail]
            X_Ray[X-Ray]
        end

        subgraph Network_Tools ["Network Tools"]
            Netshoot[Netshoot]
            TCPDump[tcpdump]
            Dig[dig/nslookup]
            Curl[curl/wget]
        end
    end

    Control_Plane --> Kubectl
    Control_Plane --> AWS_CLI
    Control_Plane --> CloudWatch

    Node_Issues --> K8s_Debug
    Node_Issues --> AWS_CLI

    Networking --> Netshoot
    Networking --> TCPDump

    Pod_Issues --> K8s_Logs
    Pod_Issues --> K8s_Debug

    Service_Issues --> K8s_Events
    Service_Issues --> Dig
    Service_Issues --> Curl

    ImagePull --> K8s_Events
    ImagePull --> K8s_Logs

    CrashLoop --> K8s_Logs
    CrashLoop --> K8s_Debug

    NodeNotReady --> AWS_CLI
    NodeNotReady --> K8s_Events

    Connection --> Netshoot
    Connection --> TCPDump

    %% Class definitions
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class AWS_CLI,CloudWatch,CloudTrail,X_Ray awsService;
    class Kubectl,K8s_Debug,K8s_Events,K8s_Logs,Control_Plane,Node_Issues,Pod_Issues,Service_Issues,Deployment_Issues k8sComponent;
    class Netshoot,TCPDump,Dig,Curl userApp;
    class ImagePull,CrashLoop,NodeNotReady,Connection,Networking,Auth_Issues,Resource_Issues default;
```

### Cluster Troubleshooting

#### Checking Cluster Status

```bash
# Check cluster status
aws eks describe-cluster --name my-cluster --query "cluster.status"

# Check cluster endpoint
aws eks describe-cluster --name my-cluster --query "cluster.endpoint"

# Check cluster logs
aws eks update-cluster-config \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# Check cluster logs in CloudWatch Logs
aws logs get-log-events \
  --log-group-name /aws/eks/my-cluster/cluster \
  --log-stream-name kube-apiserver-12345abcde \
  --limit 10
```

#### Node Troubleshooting

```bash
# Check node status
kubectl get nodes
kubectl describe node <node-name>

# Check node group status
aws eks describe-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup

# Check node logs
aws ec2 get-console-output \
  --instance-id i-1234567890abcdef0

# Access node via SSH
ssh -i ~/.ssh/my-key.pem ec2-user@<node-ip>
```

#### Pod Troubleshooting

```bash
# Check pod status
kubectl get pods -A
kubectl describe pod <pod-name> -n <namespace>

# Check pod logs
kubectl logs <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace> --previous  # Logs from previous container

# Check pod events
kubectl get events -n <namespace> --sort-by='.lastTimestamp'

# Access pod shell
kubectl exec -it <pod-name> -n <namespace> -- /bin/bash
```

### Networking Troubleshooting

#### Service Troubleshooting

```bash
# Check service status
kubectl get svc -A
kubectl describe svc <service-name> -n <namespace>

# Check endpoints
kubectl get endpoints <service-name> -n <namespace>

# DNS check
kubectl run -it --rm --restart=Never busybox --image=busybox:1.28 -- nslookup <service-name>.<namespace>.svc.cluster.local

# Port forwarding
kubectl port-forward svc/<service-name> 8080:80 -n <namespace>
```

#### Network Policy Troubleshooting

```bash
# Check network policies
kubectl get networkpolicies -A
kubectl describe networkpolicy <policy-name> -n <namespace>

# Test network connectivity
kubectl run -it --rm --restart=Never busybox --image=busybox:1.28 -- wget -O- <service-name>.<namespace>.svc.cluster.local

# Packet capture
kubectl debug node/<node-name> -it --image=nicolaka/netshoot -- tcpdump -i any port 80
```

### Logging and Monitoring Troubleshooting

#### Fluent Bit Troubleshooting

```bash
# Check Fluent Bit pod status
kubectl get pods -n kube-system -l app=aws-for-fluent-bit

# Check Fluent Bit logs
kubectl logs -n kube-system -l app=aws-for-fluent-bit

# Check Fluent Bit configuration
kubectl get cm -n kube-system fluent-bit-config -o yaml
```

#### Prometheus Troubleshooting

```bash
# Check Prometheus pod status
kubectl get pods -n monitoring -l app=prometheus

# Check Prometheus logs
kubectl logs -n monitoring -l app=prometheus-server

# Check Prometheus targets
kubectl port-forward -n monitoring svc/prometheus-server 9090:80
# Access http://localhost:9090/targets in browser
```

#### Grafana Troubleshooting

```bash
# Check Grafana pod status
kubectl get pods -n monitoring -l app=grafana

# Check Grafana logs
kubectl logs -n monitoring -l app=grafana

# Check Grafana data sources
kubectl port-forward -n monitoring svc/grafana 3000:80
# Access http://localhost:3000/datasources in browser
```

### Common Issues and Solutions

#### ImagePullBackOff Error

Issue: Pod stuck in ImagePullBackOff state

Solutions:
1. Verify image name and tag are correct
2. Check image pull secret for private registries
3. Verify node has internet access

```bash
# Create image pull secret
kubectl create secret docker-registry regcred \
  --docker-server=<registry-server> \
  --docker-username=<username> \
  --docker-password=<password> \
  --docker-email=<email>

# Apply secret to pod
kubectl patch serviceaccount default -p '{"imagePullSecrets": [{"name": "regcred"}]}'
```

#### CrashLoopBackOff Error

Issue: Pod repeatedly restarting in CrashLoopBackOff state

Solutions:
1. Check pod logs
2. Check resource limits
3. Check application configuration

```bash
# Check pod logs
kubectl logs <pod-name> -n <namespace>

# Check pod events
kubectl describe pod <pod-name> -n <namespace>

# Add debug container
kubectl debug <pod-name> -n <namespace> --image=busybox:1.28 --target=<container-name>
```

#### Node NotReady State

Issue: Node displayed as NotReady state

Solutions:
1. Check node status and events
2. Check kubelet logs
3. Check node resource usage

```bash
# Check node status
kubectl describe node <node-name>

# Access node via SSH
ssh -i ~/.ssh/my-key.pem ec2-user@<node-ip>

# Check kubelet logs
sudo journalctl -u kubelet

# Check node resource usage
top
df -h
```

#### Service Connection Issues

Issue: Unable to connect to service

Solutions:
1. Check service and endpoints
2. Check pod labels and selectors
3. Check network policies

```bash
# Check service and endpoints
kubectl get svc <service-name> -n <namespace>
kubectl get endpoints <service-name> -n <namespace>

# Check pod labels
kubectl get pods -n <namespace> --show-labels

# Check service selector
kubectl get svc <service-name> -n <namespace> -o jsonpath='{.spec.selector}'

# Check network policies
kubectl get networkpolicies -n <namespace>
```

### Debugging Tools

#### kubectl Debugging Tools

```bash
# Pod debugging
kubectl debug <pod-name> -n <namespace> --image=busybox:1.28 --target=<container-name>

# Node debugging
kubectl debug node/<node-name> -it --image=busybox:1.28

# Create temporary debugging pod
kubectl run debug --rm -it --image=nicolaka/netshoot -- /bin/bash
```

#### AWS CLI Debugging Tools

```bash
# Describe EKS cluster
aws eks describe-cluster --name my-cluster

# Describe EKS node group
aws eks describe-nodegroup --cluster-name my-cluster --nodegroup-name my-nodegroup

# CloudWatch Logs query
aws logs start-query \
  --log-group-name /aws/eks/my-cluster/cluster \
  --start-time $(date -u -v-1H +%s) \
  --end-time $(date -u +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /Error/'
```

#### Network Debugging Tools

```bash
# Create network debugging pod
kubectl run netshoot --rm -it --image=nicolaka/netshoot -- /bin/bash

# Test network connectivity
nc -zv <service-name> <port>
curl -v <service-name>:<port>

# DNS check
dig <service-name>.<namespace>.svc.cluster.local

# Packet capture
tcpdump -i any port <port> -w capture.pcap
```

## Conclusion

In this document, we explored various tools, techniques, and best practices for monitoring and logging in Amazon EKS clusters. Implementing an effective monitoring and logging strategy allows you to continuously understand the state of your cluster, detect issues early, and respond quickly when problems occur.

Key topics covered:

1. **Monitoring and Logging Overview**: Importance and architecture of monitoring and logging
2. **EKS Control Plane Logging**: Control plane log types and how to enable them
3. **Container Logging**: Container log collection using Fluent Bit and CloudWatch Container Insights
4. **Cluster Monitoring**: Cluster monitoring using CloudWatch, Prometheus, and Grafana
5. **Alerting and Event Management**: Alert configuration using CloudWatch alarms and Prometheus Alertmanager
6. **Log Analysis and Visualization**: Log analysis using CloudWatch Logs Insights, OpenSearch, and Grafana Loki
7. **Monitoring and Logging Best Practices**: Best practices for effective monitoring and logging
8. **Troubleshooting and Debugging**: Common issues and solutions

Monitoring and logging in EKS clusters is an ongoing process that should be continuously improved to meet the requirements of your cluster and applications.

## References

- [Amazon EKS Monitoring Best Practices](https://aws.github.io/aws-eks-best-practices/observability/monitoring/)
- [Amazon EKS Logging Best Practices](https://aws.github.io/aws-eks-best-practices/observability/logging/)
- [Kubernetes Monitoring Architecture](https://kubernetes.io/docs/tasks/debug-application-cluster/resource-usage-monitoring/)
- [Prometheus Documentation](https://prometheus.io/docs/introduction/overview/)
- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
- [Fluent Bit Documentation](https://docs.fluentbit.io/manual/)
- [Amazon CloudWatch Documentation](https://docs.aws.amazon.com/cloudwatch/)
- [Amazon OpenSearch Service Documentation](https://docs.aws.amazon.com/opensearch-service/)

## Quiz

To test what you learned in this chapter, try the [topic quiz](../quizzes/eks/06-eks-monitoring-logging-quiz.md).
