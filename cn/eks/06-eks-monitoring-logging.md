# Amazon EKS 监控和日志记录

> **最后更新**: July 3, 2026

有效的监控和日志记录对于维护 Amazon EKS clusters 的可靠性、可用性和性能至关重要。本文档介绍在 EKS clusters 中实施监控和日志记录的各种工具、技术和最佳实践。

## 目录

1. [监控和日志记录概述](#monitoring-and-logging-overview)
2. [EKS Control Plane 日志记录](#eks-control-plane-logging)
3. [Container 日志记录](#container-logging)
4. [Cluster 监控](#cluster-monitoring)
5. [告警和事件管理](#alerting-and-event-management)
6. [日志分析和可视化](#log-analysis-and-visualization)
7. [监控和日志记录最佳实践](#monitoring-and-logging-best-practices)
8. [故障排查和调试](#troubleshooting-and-debugging)

## 监控和日志记录概述

### 监控和日志记录的重要性

Amazon EKS clusters 中的监控和日志记录非常重要，原因如下：

1. **可见性**: 提供对 cluster 状态、性能和行为的可见性
2. **问题检测**: 在问题变得严重之前及早检测
3. **趋势分析**: 识别一段时间内的性能和资源使用趋势
4. **容量规划**: 预测并规划资源需求
5. **安全和审计**: 检测安全事件并满足合规要求
6. **故障排查**: 在问题发生时实现快速诊断和解决

### 监控和日志记录架构

EKS cluster 的全面监控和日志记录架构由以下组件组成：

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

### 监控和日志记录策略

按照以下步骤制定有效的监控和日志记录策略：

1. **定义目标**: 定义监控和日志记录目标与需求
2. **识别 Metrics 和 Logs**: 识别要收集的关键 metrics 和 logs
3. **选择工具**: 选择满足需求的监控和日志记录工具
4. **建立基线**: 为正常行为建立基线
5. **配置 Alerts**: 为重要事件和阈值配置 alerts
6. **自动化**: 尽可能自动化监控和日志记录流程
7. **定期审查**: 定期审查并改进监控和日志记录策略

## EKS Control Plane 日志记录

Amazon EKS 提供将 cluster Control Plane logs 发送到 Amazon CloudWatch Logs 的能力。这提供了对 cluster control components 的可见性。

### Control Plane Log 类型

EKS 支持以下 Control Plane log 类型：

1. **API Server (api)**: Kubernetes API server logs
2. **Audit (audit)**: Kubernetes audit logs
3. **Authenticator (authenticator)**: AWS IAM authenticator logs
4. **Controller Manager (controllerManager)**: Controller manager logs
5. **Scheduler (scheduler)**: Kubernetes scheduler logs

### 启用 Control Plane Logging

你可以使用 AWS Management Console、AWS CLI 或 eksctl 启用 Control Plane logging：

#### 使用 AWS CLI

```bash
aws eks update-cluster-config \
  --region us-west-2 \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

#### 使用 eksctl

```bash
eksctl utils update-cluster-logging \
  --region us-west-2 \
  --cluster my-cluster \
  --enable-types api,audit,authenticator,controllerManager,scheduler
```

### 查询 Control Plane Logs

你可以使用 CloudWatch Logs Insights 查询 Control Plane logs：

#### API Server 错误查询

```
fields @timestamp, @message
| filter @message like /Error/
| sort @timestamp desc
| limit 20
```

#### 身份验证失败查询

```
fields @timestamp, @message
| filter @message like /authentication failed/
| sort @timestamp desc
| limit 20
```

#### Audit Log 查询

```
fields @timestamp, @message
| filter @message like /responseStatus.code="403"/
| sort @timestamp desc
| limit 20
```

### Control Plane Log 保留和成本管理

你可以在 CloudWatch Logs 中配置 log 保留周期以管理成本：

```bash
aws logs put-retention-policy \
  --log-group-name /aws/eks/my-cluster/cluster \
  --retention-in-days 30
```

### EKS Capabilities Logging (GitOps, ACK, kro)

EKS Capabilities 在 EKS Control Plane 上将 Argo CD、AWS Controllers for Kubernetes (ACK) 和 kro 作为托管 controllers 运行。它们的 controller logs 现在可以直接传送到 CloudWatch Logs、S3 或 Kinesis Data Firehose，使用与 Control Plane logging 相同的传送选项，而无需在 cluster 中运行单独的 log collector 来抓取 controller pods。

这弥补了过去需要直接检查 controller pods 的可见性缺口：

- **GitOps sync 错误** from Argo CD
- **失败的 resource reconciliation** from ACK
- **Workflow state transitions** from kro

为你运行的 capabilities 启用 log delivery，并同时启用标准 Control Plane logging，然后用 CloudWatch Logs Insights 以查询 API server 或 audit logs 相同的方式查询结果。有关当前支持的 capability log types 列表，请参阅 [公告](https://aws.amazon.com/about-aws/whats-new/2026/06/amazon-eks-capabilities-logging/)（June 4, 2026）。

## Container 日志记录

Container logs 为诊断和解决 application 问题提供重要信息。在 EKS 中，你可以通过多种方式收集和管理 container logs。

### 日志记录架构

EKS 中典型的 container logging 架构如下：

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

### 使用 Fluent Bit 收集 Logs

Fluent Bit 是一种轻量级 log collector，广泛用于在 EKS clusters 中收集 container logs：

#### Fluent Bit 安装

使用 Helm 安装 Fluent Bit：

```bash
helm repo add aws-for-fluent-bit https://aws.github.io/eks-charts
helm repo update
helm install aws-for-fluent-bit aws-for-fluent-bit/aws-for-fluent-bit \
  --namespace kube-system \
  --set cloudWatch.region=us-west-2 \
  --set cloudWatch.logGroupName=/aws/eks/my-cluster/fluentbit
```

#### Fluent Bit 配置

用于自定义配置的 ConfigMap：

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

CloudWatch Container Insights 收集、聚合并汇总来自 containerized applications 和 microservices 的 metrics 和 logs：

#### 安装 Container Insights

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

在 CloudWatch console 中访问 Container Insights dashboard，以监控：
- Node、pod 和 container 级别的 CPU 与内存使用量
- 网络和磁盘 I/O
- Pod 和 container 状态
- Cluster 故障和事件

### 自定义日志记录方案

你可以针对特定需求实施自定义日志记录方案：

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

### Log 结构化和解析

建议使用结构化 log 格式以实现有效的 log 分析：

#### JSON Log 格式

从你的 application 以 JSON 格式输出 logs：

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

#### Log Parser 配置

Fluent Bit 中的 log parsing 配置：

```
[PARSER]
    Name        json
    Format      json
    Time_Key    timestamp
    Time_Format %Y-%m-%dT%H:%M:%S%z
```

## Cluster 监控

有效的 cluster 监控对于跟踪 EKS cluster 的状态、性能和资源使用情况至关重要。本节探讨用于监控 EKS clusters 的各种工具和技术。

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

Amazon CloudWatch Container Insights 收集、聚合并汇总来自 containerized applications 和 microservices 的 metrics、logs 和 events：

#### 启用 Container Insights

使用 CloudWatch agent 启用 Container Insights：

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

Container Insights 收集以下 metrics：

- **Cluster level**: Node count、pod count、failed pod count
- **Node level**: CPU usage、memory usage、network I/O、disk I/O
- **Pod level**: CPU usage、memory usage、network I/O
- **Service level**: Pod count、CPU usage、memory usage

#### Container Insights Dashboard

在 CloudWatch console 中访问 Container Insights dashboard，以可视化 cluster performance：

1. 登录 AWS Management Console
2. 导航到 CloudWatch service
3. 从左侧导航窗格选择 "Insights" > "Container Insights"
4. 选择 cluster、node、pod 或 service 视图

#### Container Insights Alerts

设置 CloudWatch alarms，以便在 metrics 超过特定阈值时接收通知：

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

#### CloudWatch Observability Add-on 5.0.0

从 `amazon-cloudwatch-observability` EKS add-on 的 5.0.0 版本（February 2026）开始，Application Signals (APM) 默认处于 **enabled by default** 状态，而不再需要手动 opt-in。该 add-on 现在将 Enhanced Container Insights、Container Logs 和 Application Signals 打包为一个单一 package，并且无需 pod annotations 即可为 workloads 检测 traces、metrics 和 logs：

```bash
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name amazon-cloudwatch-observability \
  --addon-version v5.0.0-eksbuild.1
```

如果你正在从 Application Signals 仍为 opt-in 的 add-on 版本升级，请参阅 [release notes](https://aws.amazon.com/about-aws/whats-new/2026/02/application-performance-monitoring-cloudwatch-eks/)（February 26, 2026）获取升级指导。有关基于 OTel 的新版 Container Insights metric collection 演进，请参阅 [CloudWatch Metrics](../observability/metrics/04-cloudwatch-metrics.md#opentelemetry-based-container-insights-preview)。

### EKS Node Monitoring Agent

EKS Node Monitoring Agent 会监视 worker nodes 的 system、storage、network 和 accelerator (GPU) 问题，并将它们发布为 Kubernetes Node Conditions，EKS auto node repair 功能可以自动对这些 Conditions 采取操作。截至 February 2026，该 agent 的源代码已在 GitHub 上公开，因此可以在内置检查之外进行自定义或扩展。

该 agent 默认包含在 EKS Auto Mode 中，也可以作为标准 managed node groups 的独立 add-on 使用：

```bash
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name eks-node-monitoring-agent
```

使用以下命令检查它报告的 conditions：

```bash
kubectl get nodes -o custom-columns='NAME:.metadata.name,CONDITIONS:.status.conditions[*].type'
kubectl describe node <node-name>
```

有关 GitHub repository 和支持的 condition types，请参阅 [公告](https://aws.amazon.com/about-aws/whats-new/2026/02/amazon-eks-node-monitoring-agent-open-source/)（February 24, 2026）。

### Prometheus 和 Grafana

Prometheus 是一个 time-series database 和监控系统，Grafana 是用于可视化 metrics 的 dashboard 工具。你可以将这两个工具结合使用，对 EKS cluster 进行全面监控。

#### Amazon Managed Service for Prometheus 和 Grafana

AWS 为 Prometheus 和 Grafana 提供 managed services：

1. **Amazon Managed Service for Prometheus (AMP)** 设置：

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

2. **Amazon Managed Grafana (AMG)** 设置：

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

#### Self-Managed Prometheus 和 Grafana

你也可以将 self-managed Prometheus 和 Grafana 部署到你的 EKS cluster：

1. **安装 kube-prometheus-stack**：

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set grafana.service.type=LoadBalancer
```

2. **访问 Grafana**：

```bash
# Get Grafana service URL
kubectl get svc -n monitoring monitoring-grafana -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

# Get default username and password
kubectl get secret -n monitoring monitoring-grafana -o jsonpath='{.data.admin-user}' | base64 --decode
kubectl get secret -n monitoring monitoring-grafana -o jsonpath='{.data.admin-password}' | base64 --decode
```

#### 关键 Prometheus Metrics

Prometheus 收集以下重要 Kubernetes metrics：

- **Node metrics**: CPU、memory、disk、network usage
- **Pod metrics**: CPU、memory usage、restart count
- **Container metrics**: CPU、memory usage、filesystem usage
- **API server metrics**: Request latency、request count、error rate
- **etcd metrics**: Latency、disk I/O、leader changes

#### 有用的 Grafana Dashboards

你可以在 Grafana 中导入以下有用 dashboards：

1. **Kubernetes Cluster Monitoring** (ID: 15661)
2. **Node Exporter Full** (ID: 1860)
3. **Kubernetes Pod Monitoring** (ID: 6417)
4. **Kubernetes API Server** (ID: 12006)
5. **Kubernetes Resource Requests/Limits** (ID: 13770)

#### PromQL 查询示例

你可以使用 Prometheus Query Language (PromQL) 编写有用的查询：

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
### 使用 AWS X-Ray 进行分布式追踪

AWS X-Ray 收集有关 application 处理的 requests 的数据，并使用这些数据识别 application 问题和优化机会。

#### X-Ray 设置

1. **安装 X-Ray daemon**：

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

2. **将 X-Ray SDK 集成到你的 application 中**：

Java application 示例：

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

使用 X-Ray service map 可视化 microservices 架构中组件之间的关系和通信：

1. 登录 AWS Management Console
2. 导航到 X-Ray service
3. 从左侧导航窗格选择 "Service Map"
4. 检查 services 之间的 latency、errors 和 fault points

#### X-Ray Analysis and Insights

使用 X-Ray Analytics 分析 trace data 并识别性能瓶颈：

1. 在 AWS Management Console 中导航到 X-Ray service
2. 从左侧导航窗格选择 "Analytics"
3. 分析 response time distribution、error rate 和 fault points

### Kubernetes Dashboard

Kubernetes Dashboard 提供用于管理 cluster resources 和排查问题的 web-based UI：

#### 安装 Kubernetes Dashboard

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

#### 访问 Dashboard

```bash
# Start dashboard proxy
kubectl proxy

# Access the following URL in browser
# http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/
```

### Custom Metrics 和监控

你可以实现自定义方案来收集和监控 application-specific metrics：

#### Prometheus Client Library 集成

将 Prometheus client libraries 集成到你的 application 中以暴露 custom metrics：

Java application 示例：

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

#### 收集 Custom Metrics

使用 Prometheus ServiceMonitor 收集 custom metrics：

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

在 Grafana 中创建 custom dashboards 以可视化 application metrics：

1. 登录 Grafana
2. 点击 "+" 图标并选择 "Dashboard"
3. 点击 "Add panel"
4. 选择 "Prometheus" 作为 data source
5. 编写 PromQL query（例如 `rate(app_requests_total[5m])`）
6. 配置 panel title、description 和 visualization type
7. 点击 "Save"
## 告警和事件管理

有效的告警和事件管理对于快速检测并响应 EKS cluster 中的问题至关重要。本节探讨用于在 EKS clusters 中管理 alerts 和 events 的各种工具与技术。

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

使用 Amazon CloudWatch alarms，在 metrics 超过特定阈值时接收通知：

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

Prometheus Alertmanager 处理 Prometheus 生成的 alerts，并将它们路由到适当的 notification channels：

#### Alertmanager 配置

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

#### Alert Rules 配置

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

使用 Amazon EventBridge 创建 rules，以响应 EKS cluster 中的 events：

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

### Kubernetes Event 监控

Kubernetes events 提供有关 cluster 中发生的重要活动的信息：

#### 安装 Event Monitoring Tools

```bash
# Install event-exporter
kubectl apply -f https://raw.githubusercontent.com/opsgenie/kubernetes-event-exporter/master/deploy/01-cluster-role.yaml
kubectl apply -f https://raw.githubusercontent.com/opsgenie/kubernetes-event-exporter/master/deploy/02-service-account.yaml
kubectl apply -f https://raw.githubusercontent.com/opsgenie/kubernetes-event-exporter/master/deploy/03-cluster-role-binding.yaml
```

#### Event Exporter 配置

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

### Notification Channel 集成

你可以集成各种 notification channels，将 alerts 传递给你的团队：

#### Slack 集成

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

#### PagerDuty 集成

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

#### Email 集成

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

### Alert 管理和升级

实施策略以有效管理和升级 alerts：

#### Alert 严重性级别

将 alerts 分类为以下严重性级别：

- **Critical**: 需要立即采取行动的严重问题
- **Warning**: 需要关注但不需要立即行动的问题
- **Info**: 信息性 alerts

#### Alert 升级策略

使用 PagerDuty 等工具实施 alert escalation policies：

1. **First Response**: 通知 on-call engineer
2. **Escalation 1**: 如果 15 分钟后无响应，则通知 backup engineer
3. **Escalation 2**: 如果 30 分钟后无响应，则通知 team lead
4. **Escalation 3**: 如果 45 分钟后无响应，则通知 manager

#### 减少 Alert Fatigue

实施减少 alert fatigue 的策略：

1. **Alert Grouping**: 将相关 alerts 分组以减少重复通知
2. **Alert Filtering**: 过滤以仅传递重要 alerts
3. **Alert Throttling**: 限制重复 alerts 的频率
4. **Alert Time Windows**: 仅在工作时间传递非业务关键 alerts
## 日志分析和可视化

日志分析和可视化在诊断并解决 EKS cluster 中发生的问题方面发挥重要作用。本节探讨用于在 EKS clusters 中分析和可视化 logs 的各种工具与技术。

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

使用 CloudWatch Logs Insights 查询并分析来自 EKS cluster 的 logs：

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

使用 Amazon OpenSearch Service（以前称为 Amazon Elasticsearch Service）存储、分析并可视化来自 EKS cluster 的 logs：

#### 创建 OpenSearch Domain

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

#### 使用 Fluent Bit 将 Logs 发送到 OpenSearch

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

#### 使用 OpenSearch Dashboards 进行 Log 可视化

在 OpenSearch Dashboards 中创建以下 visualizations：

1. **Log Explorer**: Log search 和 filtering
2. **Dashboards**: 基于 log data 创建 dashboards
3. **Visualizations**: 基于 log data 创建 charts 和 graphs
4. **Alerts**: 基于 log patterns 配置 alerts

### Grafana Loki

Grafana Loki 是一个 log aggregation system，使用类似 Prometheus 的 label-based 方法：

#### 安装 Loki

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

#### LogQL 查询示例

```
# Search error logs in a specific namespace
{namespace="default"} |= "ERROR"

# Search logs for a specific pod
{namespace="default", pod=~"app-.*"} | json

# Count logs by log level
sum by (level) (count_over_time({namespace="default"} | json | level=~"info|warn|error" [5m]))
```

#### 创建 Grafana Dashboards

使用 Loki data source 在 Grafana 中创建 log dashboards：

1. 登录 Grafana
2. 点击 "+" 图标并选择 "Dashboard"
3. 点击 "Add panel"
4. 选择 "Loki" 作为 data source
5. 编写 LogQL query
6. 配置 panel title、description 和 visualization type
7. 点击 "Save"

### AWS CloudTrail

使用 AWS CloudTrail 记录并分析与你的 EKS cluster 相关的 AWS API calls：

#### 创建 CloudTrail Trail

```bash
aws cloudtrail create-trail \
  --name eks-api-trail \
  --s3-bucket-name my-cloudtrail-bucket \
  --is-multi-region-trail \
  --include-global-service-events

aws cloudtrail start-logging --name eks-api-trail
```

#### 过滤 CloudTrail Events

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

### Log 分析最佳实践

有效分析来自 EKS cluster 的 logs 的最佳实践：

#### 结构化 Logging

在你的 applications 中使用结构化 log 格式（例如 JSON）：

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

使用 correlation IDs 跟踪 distributed systems 中的 requests：

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

#### 使用 Log Levels

使用适当的 log levels 表示 logs 的重要性：

- **ERROR**: Application errors 和 exceptions
- **WARN**: 潜在问题或意外情况
- **INFO**: 一般 application events
- **DEBUG**: 对 debugging 有用的详细信息
- **TRACE**: 非常详细的 debugging 信息

#### Log Retention Policy

根据成本和合规要求设置 log retention policies：

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
## 监控和日志记录最佳实践

让我们探讨在 EKS clusters 中有效实施监控和日志记录的最佳实践。

### 监控最佳实践

#### 多层监控

监控 EKS cluster 的所有层：

1. **Infrastructure Layer**: EC2 instances、VPC、subnets、security groups
2. **Cluster Layer**: Control plane、nodes、pods、services
3. **Application Layer**: Application performance、user experience

#### Golden Signals 监控

重点关注 Google SRE 书中建议的 “4 Golden Signals”：

1. **Latency**: 处理 requests 所需的时间
2. **Traffic**: 到系统的 requests 数量
3. **Errors**: 失败 requests 的比例
4. **Saturation**: 系统“有多满”（例如 memory usage）

#### 主动监控

实施主动监控，以在问题发生前检测它们：

1. **Trend Analysis**: 分析一段时间内的资源使用趋势
2. **Anomaly Detection**: 检测异常 patterns
3. **Predictive Analysis**: 预测未来资源需求

#### Automated Scaling

基于 monitoring data 实施 automated scaling：

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

#### Business Metrics 监控

除了 technical metrics 之外，还监控 business metrics：

1. **User Activity**: 活跃用户数量、session length
2. **Transactions**: Transaction count、transaction value
3. **Conversion Rate**: User conversion rate、churn rate
4. **SLA Compliance**: Service Level Objectives (SLOs) 是否得到满足

### Logging 最佳实践

#### Centralized Logging

将所有 logs 聚合到一个中心位置：

1. **Consistent Format**: 在所有 applications 中使用一致的 log format
2. **Central Repository**: 使用 CloudWatch Logs、OpenSearch 或 Loki 等 central log repository
3. **Log Forwarding**: 使用 Fluent Bit 或 Fluentd 等 log forwarding agents

#### 包含上下文信息

在 logs 中包含足够的上下文信息：

1. **Timestamp**: 准确的 timestamp（推荐 ISO 8601 格式）
2. **Request ID**: 用于 distributed systems 中 request tracking 的唯一 ID
3. **User Information**: User ID 或 session ID（不包括 personally identifiable information）
4. **Service Information**: Service name、version、instance ID
5. **Error Details**: Error code、error message、stack trace

#### Log Level Filtering

根据环境设置适当的 log levels：

1. **Development Environment**: DEBUG 或 TRACE level
2. **Staging Environment**: INFO level
3. **Production Environment**: INFO 或 WARN level（可按需启用 DEBUG）

#### 保护敏感信息

保护 logs 中的敏感信息：

1. **PII Masking**: 屏蔽 personally identifiable information (PII)
2. **Exclude Credentials**: 排除 passwords、tokens、API keys 等 credentials
3. **Encryption**: 对静态和传输中的 logs 进行加密

### Alerting 最佳实践

#### Alert 优先级

对 alerts 进行优先级排序以减少 alert fatigue：

1. **P1 (Critical)**: 需要立即采取行动的严重问题
2. **P2 (High)**: 需要在工作时间内采取行动的重要问题
3. **P3 (Medium)**: 需要在计划维护期间采取行动的问题
4. **P4 (Low)**: 信息性 alerts

#### Alert Grouping

将相关 alerts 分组以减少重复通知：

```yaml
route:
  group_by: ['alertname', 'job', 'instance']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
```

#### 可操作的 Alerts

在 alerts 中包含足够的信息用于故障排查：

1. **Clear Title**: 清晰描述问题的标题
2. **Detailed Description**: 对原因和影响的详细描述
3. **Troubleshooting Steps**: 用于 troubleshooting 的步骤或链接
4. **Related Metrics and Logs**: 对诊断有用的 metrics 和 logs 链接

#### Alert Testing

定期测试你的 alerting system：

1. **Alert Simulation**: 生成 test alerts
2. **Escalation Testing**: 测试 escalation paths
3. **Fault Injection**: 在受控环境中注入 faults

### 成本优化最佳实践

#### Log Volume Optimization

优化 log volume 以降低成本：

1. **Sampling**: 对高容量 logs 进行 sampling
2. **Filtering**: 过滤不必要的 logs
3. **Compression**: 压缩 logs

#### Metric Cardinality Management

管理 metric cardinality 以降低成本：

1. **Label Limits**: 限制 metrics 中使用的 labels 数量
2. **Aggregation**: 将详细 metrics 聚合到更高层级
3. **Sampling**: 对高分辨率 metrics 进行 sampling

#### Storage Tiering

实施成本效益高的 storage tiering：

1. **Hot Storage**: 最近的 logs 和频繁访问的 logs
2. **Warm Storage**: 较少访问的 logs
3. **Cold Storage**: Archived logs

## 故障排查和调试

让我们探讨在 EKS clusters 中排查和调试问题的各种技术。

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

### Cluster 故障排查

#### 检查 Cluster 状态

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

#### Node 故障排查

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

#### Pod 故障排查

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

### Networking 故障排查

#### Service 故障排查

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

#### Network Policy 故障排查

```bash
# Check network policies
kubectl get networkpolicies -A
kubectl describe networkpolicy <policy-name> -n <namespace>

# Test network connectivity
kubectl run -it --rm --restart=Never busybox --image=busybox:1.28 -- wget -O- <service-name>.<namespace>.svc.cluster.local

# Packet capture
kubectl debug node/<node-name> -it --image=nicolaka/netshoot -- tcpdump -i any port 80
```

### Logging 和 Monitoring 故障排查

#### Fluent Bit 故障排查

```bash
# Check Fluent Bit pod status
kubectl get pods -n kube-system -l app=aws-for-fluent-bit

# Check Fluent Bit logs
kubectl logs -n kube-system -l app=aws-for-fluent-bit

# Check Fluent Bit configuration
kubectl get cm -n kube-system fluent-bit-config -o yaml
```

#### Prometheus 故障排查

```bash
# Check Prometheus pod status
kubectl get pods -n monitoring -l app=prometheus

# Check Prometheus logs
kubectl logs -n monitoring -l app=prometheus-server

# Check Prometheus targets
kubectl port-forward -n monitoring svc/prometheus-server 9090:80
# Access http://localhost:9090/targets in browser
```

#### Grafana 故障排查

```bash
# Check Grafana pod status
kubectl get pods -n monitoring -l app=grafana

# Check Grafana logs
kubectl logs -n monitoring -l app=grafana

# Check Grafana data sources
kubectl port-forward -n monitoring svc/grafana 3000:80
# Access http://localhost:3000/datasources in browser
```

### 常见问题和解决方案

#### ImagePullBackOff Error

问题：Pod stuck in ImagePullBackOff state

解决方案：
1. 验证 image name 和 tag 是否正确
2. 检查 private registries 的 image pull secret
3. 验证 node 是否具有 internet access

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

问题：Pod 在 CrashLoopBackOff state 中反复重启

解决方案：
1. 检查 pod logs
2. 检查 resource limits
3. 检查 application configuration

```bash
# Check pod logs
kubectl logs <pod-name> -n <namespace>

# Check pod events
kubectl describe pod <pod-name> -n <namespace>

# Add debug container
kubectl debug <pod-name> -n <namespace> --image=busybox:1.28 --target=<container-name>
```

#### Node NotReady State

问题：Node 显示为 NotReady state

解决方案：
1. 检查 node status 和 events
2. 检查 kubelet logs
3. 检查 node resource usage

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

问题：无法连接到 service

解决方案：
1. 检查 service 和 endpoints
2. 检查 pod labels 和 selectors
3. 检查 network policies

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

## 结论

在本文档中，我们探讨了用于 Amazon EKS clusters 监控和日志记录的各种工具、技术和最佳实践。实施有效的监控和日志记录策略，可以让你持续了解 cluster 的状态，及早发现问题，并在问题发生时快速响应。

涵盖的关键主题：

1. **Monitoring and Logging Overview**: 监控和日志记录的重要性与架构
2. **EKS Control Plane Logging**: Control Plane log 类型以及启用方法
3. **Container Logging**: 使用 Fluent Bit 和 CloudWatch Container Insights 进行 container log collection
4. **Cluster Monitoring**: 使用 CloudWatch、Prometheus 和 Grafana 进行 cluster monitoring
5. **Alerting and Event Management**: 使用 CloudWatch alarms 和 Prometheus Alertmanager 进行 alert configuration
6. **Log Analysis and Visualization**: 使用 CloudWatch Logs Insights、OpenSearch 和 Grafana Loki 进行 log analysis
7. **Monitoring and Logging Best Practices**: 有效监控和日志记录的最佳实践
8. **Troubleshooting and Debugging**: 常见问题和解决方案

EKS clusters 中的监控和日志记录是一个持续过程，应不断改进，以满足你的 cluster 和 applications 的要求。

## 参考资料

- [Amazon EKS Monitoring Best Practices](https://aws.github.io/aws-eks-best-practices/observability/monitoring/)
- [Amazon EKS Logging Best Practices](https://aws.github.io/aws-eks-best-practices/observability/logging/)
- [Kubernetes Monitoring Architecture](https://kubernetes.io/docs/tasks/debug-application-cluster/resource-usage-monitoring/)
- [Prometheus Documentation](https://prometheus.io/docs/introduction/overview/)
- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
- [Fluent Bit Documentation](https://docs.fluentbit.io/manual/)
- [Amazon CloudWatch Documentation](https://docs.aws.amazon.com/cloudwatch/)
- [Amazon OpenSearch Service Documentation](https://docs.aws.amazon.com/opensearch-service/)

## 测验

要测试你在本章学到的内容，请尝试 [topic quiz](../quizzes/eks/06-eks-monitoring-logging-quiz.md)。
