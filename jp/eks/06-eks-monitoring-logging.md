# Amazon EKS Monitoring and Logging

> **最終更新**: July 3, 2026

Amazon EKS clusters の信頼性、可用性、性能を維持するには、効果的な monitoring と logging が不可欠です。このドキュメントでは、EKS clusters で monitoring と logging を実装するためのさまざまな tools、techniques、best practices について説明します。

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

Amazon EKS clusters における monitoring と logging は、次の理由で重要です。

1. **Visibility**: cluster の status、performance、behavior への可視性を提供します
2. **Issue Detection**: 問題が重大になる前に早期検出します
3. **Trend Analysis**: 時間の経過に伴う performance と resource usage の傾向を特定します
4. **Capacity Planning**: resource requirements を予測し、計画します
5. **Security and Auditing**: security events を検出し、compliance requirements を満たします
6. **Troubleshooting**: 問題発生時に迅速な診断と解決を可能にします

### Monitoring and Logging Architecture

EKS cluster の包括的な monitoring と logging architecture は、次の components で構成されます。

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

効果的な monitoring と logging strategy を策定するには、次の steps に従います。

1. **Define Objectives**: monitoring と logging の objectives と requirements を定義します
2. **Identify Metrics and Logs**: 収集する主要な metrics と logs を特定します
3. **Select Tools**: requirements を満たす monitoring と logging tools を選択します
4. **Establish Baselines**: 通常の behavior の baselines を確立します
5. **Configure Alerts**: 重要な events と thresholds に対する alerts を設定します
6. **Automate**: monitoring と logging processes を可能な限り自動化します
7. **Regular Review**: monitoring と logging strategy を定期的に見直し、改善します

## EKS Control Plane Logging

Amazon EKS は、cluster control plane logs を Amazon CloudWatch Logs に送信する機能を提供します。これにより、cluster の control components を可視化できます。

### Control Plane Log Types

EKS は次の control plane log types をサポートしています。

1. **API Server (api)**: Kubernetes API server logs
2. **Audit (audit)**: Kubernetes audit logs
3. **Authenticator (authenticator)**: AWS IAM authenticator logs
4. **Controller Manager (controllerManager)**: Controller manager logs
5. **Scheduler (scheduler)**: Kubernetes scheduler logs

### Enabling Control Plane Logging

AWS Management Console、AWS CLI、または eksctl を使用して control plane logging を有効化できます。

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

CloudWatch Logs Insights を使用して control plane logs を query できます。

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

CloudWatch Logs で log retention periods を設定してコストを管理できます。

```bash
aws logs put-retention-policy \
  --log-group-name /aws/eks/my-cluster/cluster \
  --retention-in-days 30
```

### EKS Capabilities Logging (GitOps, ACK, kro)

EKS Capabilities は、EKS control plane 上の managed controllers として Argo CD、AWS Controllers for Kubernetes (ACK)、kro を実行します。これらの controller logs は、cluster 内で controller pods を scrape するための別個の log collector を実行しなくても、control plane logging と同じ delivery options である CloudWatch Logs、S3、または Kinesis Data Firehose に直接配信できるようになりました。

これにより、以前は controller pods を直接検査する必要があった visibility gap が解消されます。

- Argo CD からの **GitOps sync errors**
- ACK からの **Failed resource reconciliation**
- kro からの **Workflow state transitions**

標準の control plane logging と併せて、実行している capabilities の log delivery を有効化し、API server または audit logs を query する場合と同じ方法で CloudWatch Logs Insights を使用して結果を query します。サポートされている capability log types の最新リストについては、[発表](https://aws.amazon.com/about-aws/whats-new/2026/06/amazon-eks-capabilities-logging/) (June 4, 2026) を参照してください。

## Container Logging

Container logs は、application issues を診断および解決するための重要な情報を提供します。EKS では、container logs をさまざまな方法で収集および管理できます。

### Logging Architecture

EKS における一般的な container logging architecture は次のようになります。

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

Fluent Bit は、EKS clusters で container logs を収集するために広く使用されている lightweight log collector です。

#### Fluent Bit Installation

Helm を使用して Fluent Bit をインストールします。

```bash
helm repo add aws-for-fluent-bit https://aws.github.io/eks-charts
helm repo update
helm install aws-for-fluent-bit aws-for-fluent-bit/aws-for-fluent-bit \
  --namespace kube-system \
  --set cloudWatch.region=us-west-2 \
  --set cloudWatch.logGroupName=/aws/eks/my-cluster/fluentbit
```

#### Fluent Bit Configuration

custom configuration 用の ConfigMap:

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

CloudWatch Container Insights は、containerized applications と microservices から metrics と logs を収集、集約、要約します。

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

CloudWatch console の Container Insights dashboard にアクセスして、次を monitor します。
- Node、pod、container level の CPU と memory usage
- Network と disk I/O
- Pod と container status
- Cluster failures と events

### Custom Logging Solutions

特定の requirements に合わせて custom logging solutions を実装できます。

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

効果的な log analysis のために、structured log formats を使用することを推奨します。

#### JSON Log Format

application から JSON format で logs を出力します。

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

Fluent Bit で log parsing を行うための configuration:

```
[PARSER]
    Name        json
    Format      json
    Time_Key    timestamp
    Time_Format %Y-%m-%dT%H:%M:%S%z
```

## Cluster Monitoring

EKS cluster の status、performance、resource usage を追跡するには、効果的な cluster monitoring が不可欠です。この section では、EKS clusters を monitor するためのさまざまな tools と techniques を説明します。

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

Amazon CloudWatch Container Insights は、containerized applications と microservices から metrics、logs、events を収集、集約、要約します。

#### Enabling Container Insights

CloudWatch agent を使用して Container Insights を有効化します。

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

Container Insights は次の metrics を収集します。

- **Cluster level**: Node count、pod count、failed pod count
- **Node level**: CPU usage、memory usage、network I/O、disk I/O
- **Pod level**: CPU usage、memory usage、network I/O
- **Service level**: Pod count、CPU usage、memory usage

#### Container Insights Dashboard

CloudWatch console の Container Insights dashboard にアクセスして cluster performance を visual 化します。

1. AWS Management Console に log in します
2. CloudWatch service に移動します
3. 左側の navigation pane から "Insights" > "Container Insights" を選択します
4. cluster、node、pod、または service view を選択します

#### Container Insights Alerts

metrics が特定の thresholds を超えたときに notifications を受け取るため、CloudWatch alarms を設定します。

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

`amazon-cloudwatch-observability` EKS add-on の version 5.0.0 (February 2026) から、Application Signals (APM) は手動 opt-in を必要とせず、**default で enabled** として提供されます。この add-on は Enhanced Container Insights、Container Logs、Application Signals を単一の package にまとめ、pod annotations を必要とせずに workloads を traces、metrics、logs 用に instrument します。

```bash
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name amazon-cloudwatch-observability \
  --addon-version v5.0.0-eksbuild.1
```

Application Signals が opt-in だった add-on version から移行する場合の upgrade guidance については、[release notes](https://aws.amazon.com/about-aws/whats-new/2026/02/application-performance-monitoring-cloudwatch-eks/) (February 26, 2026) を参照してください。Container Insights metric collection の新しい OTel-based evolution については、[CloudWatch Metrics](../observability/metrics/04-cloudwatch-metrics.md#opentelemetry-based-container-insights-preview) を参照してください。

### EKS Node Monitoring Agent

EKS Node Monitoring Agent は、worker nodes の system、storage、network、accelerator (GPU) issues を監視し、それらを Kubernetes Node Conditions として公開します。EKS auto node repair feature はこれらに基づいて自動的に対応できます。February 2026 時点で、agent の source は GitHub で公開されているため、built-in checks を超えて customize または extend できます。

この agent は EKS Auto Mode に default で含まれており、standard managed node groups 向けの standalone add-on としても利用できます。

```bash
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name eks-node-monitoring-agent
```

報告される conditions を次のコマンドで確認します。

```bash
kubectl get nodes -o custom-columns='NAME:.metadata.name,CONDITIONS:.status.conditions[*].type'
kubectl describe node <node-name>
```

GitHub repository と supported condition types については、[発表](https://aws.amazon.com/about-aws/whats-new/2026/02/amazon-eks-node-monitoring-agent-open-source/) (February 24, 2026) を参照してください。

### Prometheus and Grafana

Prometheus は time-series database と monitoring system であり、Grafana は metrics を visual 化する dashboard tool です。この 2 つの tools を組み合わせて、EKS cluster を包括的に monitor できます。

#### Amazon Managed Service for Prometheus and Grafana

AWS は Prometheus と Grafana の managed services を提供します。

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

self-managed Prometheus と Grafana を EKS cluster に deploy することもできます。

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

Prometheus は次の重要な Kubernetes metrics を収集します。

- **Node metrics**: CPU、memory、disk、network usage
- **Pod metrics**: CPU、memory usage、restart count
- **Container metrics**: CPU、memory usage、filesystem usage
- **API server metrics**: Request latency、request count、error rate
- **etcd metrics**: Latency、disk I/O、leader changes

#### Useful Grafana Dashboards

Grafana に次の便利な dashboards を import できます。

1. **Kubernetes Cluster Monitoring** (ID: 15661)
2. **Node Exporter Full** (ID: 1860)
3. **Kubernetes Pod Monitoring** (ID: 6417)
4. **Kubernetes API Server** (ID: 12006)
5. **Kubernetes Resource Requests/Limits** (ID: 13770)

#### PromQL Query Examples

Prometheus Query Language (PromQL) を使用して便利な queries を記述できます。

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

AWS X-Ray は、application が処理する requests に関する data を収集し、それを使用して application issues と optimization opportunities を特定します。

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

X-Ray service map を使用して、microservices architecture 内の components 間の relationships と communication を visual 化します。

1. AWS Management Console に log in します
2. X-Ray service に移動します
3. 左側の navigation pane から "Service Map" を選択します
4. services 間の latency、errors、fault points を確認します

#### X-Ray Analysis and Insights

X-Ray Analytics を使用して trace data を分析し、performance bottlenecks を特定します。

1. AWS Management Console で X-Ray service に移動します
2. 左側の navigation pane から "Analytics" を選択します
3. response time distribution、error rate、fault points を分析します

### Kubernetes Dashboard

Kubernetes Dashboard は、cluster resources を管理し、issues を troubleshoot するための web-based UI を提供します。

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

application-specific metrics を収集および monitor するための custom solutions を実装できます。

#### Prometheus Client Library Integration

Prometheus client libraries を application に統合して custom metrics を公開します。

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

Prometheus ServiceMonitor を使用して custom metrics を収集します。

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

Grafana で custom dashboards を作成して application metrics を visual 化します。

1. Grafana に log in します
2. "+" icon をクリックし、"Dashboard" を選択します
3. "Add panel" をクリックします
4. data source として "Prometheus" を選択します
5. PromQL query を記述します (例: `rate(app_requests_total[5m])`)
6. panel title、description、visualization type を設定します
7. "Save" をクリックします
## Alerting and Event Management

EKS cluster 内の issues を迅速に検出し対応するには、効果的な alerting と event management が不可欠です。この section では、EKS clusters で alerts と events を管理するためのさまざまな tools と techniques を説明します。

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

Amazon CloudWatch alarms を使用して、metrics が特定の thresholds を超えたときに notifications を受け取ります。

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

Prometheus Alertmanager は、Prometheus によって生成された alerts を処理し、適切な notification channels に route します。

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

Amazon EventBridge を使用して、EKS cluster 内の events に応答する rules を作成します。

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

Kubernetes events は、cluster 内で発生している重要な activities に関する情報を提供します。

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

alerts を team に配信するために、さまざまな notification channels を統合できます。

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

alerts を効果的に管理し escalate するための strategies を実装します。

#### Alert Severity Levels

alerts を次の severity levels に分類します。

- **Critical**: immediate action が必要な重大な issues
- **Warning**: attention は必要だが immediate action は不要な issues
- **Info**: informational alerts

#### Alert Escalation Policy

PagerDuty などの tools を使用して alert escalation policies を実装します。

1. **First Response**: on-call engineer に alert します
2. **Escalation 1**: 15 分後に応答がない場合、backup engineer に alert します
3. **Escalation 2**: 30 分後に応答がない場合、team lead に alert します
4. **Escalation 3**: 45 分後に応答がない場合、manager に alert します

#### Reducing Alert Fatigue

alert fatigue を軽減するための strategies を実装します。

1. **Alert Grouping**: duplicate notifications を減らすために関連 alerts を group 化します
2. **Alert Filtering**: 重要な alerts のみを配信するよう filter します
3. **Alert Throttling**: repeated alerts の頻度を制限します
4. **Alert Time Windows**: business critical ではない alerts は business hours のみに配信します
## Log Analysis and Visualization

Log analysis と visualization は、EKS cluster 内で発生する issues の診断と解決に重要な役割を果たします。この section では、EKS clusters で logs を分析および visual 化するためのさまざまな tools と techniques を説明します。

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

CloudWatch Logs Insights を使用して、EKS cluster からの logs を query および analyze します。

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

Amazon OpenSearch Service (formerly Amazon Elasticsearch Service) を使用して、EKS cluster からの logs を保存、分析、visual 化します。

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

OpenSearch Dashboards で次の visualizations を作成します。

1. **Log Explorer**: Log search と filtering
2. **Dashboards**: log data に基づく dashboards を作成します
3. **Visualizations**: log data に基づく charts と graphs を作成します
4. **Alerts**: log patterns に基づく alerts を設定します

### Grafana Loki

Grafana Loki は、Prometheus に似た label-based approach を使用する log aggregation system です。

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

Loki data source を使用して Grafana で log dashboards を作成します。

1. Grafana に log in します
2. "+" icon をクリックし、"Dashboard" を選択します
3. "Add panel" をクリックします
4. data source として "Loki" を選択します
5. LogQL query を記述します
6. panel title、description、visualization type を設定します
7. "Save" をクリックします

### AWS CloudTrail

AWS CloudTrail を使用して、EKS cluster に関連する AWS API calls を log および analyze します。

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

EKS cluster からの logs を効果的に analyze するための best practices:

#### Structured Logging

applications で structured log formats (例: JSON) を使用します。

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

distributed systems 全体で requests を追跡するために correlation IDs を使用します。

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

logs の重要度を示すために適切な log levels を使用します。

- **ERROR**: Application errors と exceptions
- **WARN**: 潜在的な problems または予期しない situations
- **INFO**: General application events
- **DEBUG**: debugging に役立つ詳細情報
- **TRACE**: 非常に詳細な debugging information

#### Log Retention Policy

cost と compliance requirements に基づいて log retention policies を設定します。

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

EKS clusters で monitoring と logging を効果的に実装するための best practices を見ていきましょう。

### Monitoring Best Practices

#### Multi-Layer Monitoring

EKS cluster のすべての layers を monitor します。

1. **Infrastructure Layer**: EC2 instances、VPC、subnets、security groups
2. **Cluster Layer**: Control plane、nodes、pods、services
3. **Application Layer**: Application performance、user experience

#### Golden Signals Monitoring

Google の SRE book で提案されている "4 Golden Signals" に注目します。

1. **Latency**: requests の処理にかかる時間
2. **Traffic**: system への requests 数
3. **Errors**: failed requests の rate
4. **Saturation**: system がどの程度「満杯」か (例: memory usage)

#### Proactive Monitoring

issues が発生する前に検出するため、proactive monitoring を実装します。

1. **Trend Analysis**: 時間の経過に伴う resource usage trends を分析します
2. **Anomaly Detection**: abnormal patterns を検出します
3. **Predictive Analysis**: 将来の resource requirements を予測します

#### Automated Scaling

monitoring data に基づく automated scaling を実装します。

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

technical metrics に加えて business metrics も monitor します。

1. **User Activity**: active users の数、session length
2. **Transactions**: Transaction count、transaction value
3. **Conversion Rate**: User conversion rate、churn rate
4. **SLA Compliance**: Service Level Objectives (SLOs) が満たされているか

### Logging Best Practices

#### Centralized Logging

すべての logs を central location に集約します。

1. **Consistent Format**: すべての applications で一貫した log format を使用します
2. **Central Repository**: CloudWatch Logs、OpenSearch、Loki などの central log repository を使用します
3. **Log Forwarding**: Fluent Bit や Fluentd などの log forwarding agents を使用します

#### Include Context Information

logs に十分な context information を含めます。

1. **Timestamp**: 正確な timestamp (ISO 8601 format 推奨)
2. **Request ID**: distributed systems で request tracking を行うための unique ID
3. **User Information**: User ID または session ID (personally identifiable information は除外)
4. **Service Information**: Service name、version、instance ID
5. **Error Details**: Error code、error message、stack trace

#### Log Level Filtering

environment に基づいて適切な log levels を設定します。

1. **Development Environment**: DEBUG または TRACE level
2. **Staging Environment**: INFO level
3. **Production Environment**: INFO または WARN level (必要に応じて DEBUG を有効化可能)

#### Protecting Sensitive Information

logs 内の sensitive information を保護します。

1. **PII Masking**: personally identifiable information (PII) を mask します
2. **Exclude Credentials**: passwords、tokens、API keys などの credentials を除外します
3. **Encryption**: logs を at rest と in transit で暗号化します

### Alerting Best Practices

#### Alert Priority

alert fatigue を減らすため、alerts に優先順位を付けます。

1. **P1 (Critical)**: immediate action が必要な重大な issues
2. **P2 (High)**: business hours 内で action が必要な重要な issues
3. **P3 (Medium)**: scheduled maintenance 中に action が必要な issues
4. **P4 (Low)**: Informational alerts

#### Alert Grouping

duplicate notifications を減らすため、関連 alerts を group 化します。

```yaml
route:
  group_by: ['alertname', 'job', 'instance']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
```

#### Actionable Alerts

troubleshooting のために alerts に十分な情報を含めます。

1. **Clear Title**: issue を明確に説明する title
2. **Detailed Description**: cause と impact の詳細な description
3. **Troubleshooting Steps**: troubleshooting のための steps または links
4. **Related Metrics and Logs**: 診断に役立つ metrics と logs への links

#### Alert Testing

alerting system を定期的に test します。

1. **Alert Simulation**: test alerts を生成します
2. **Escalation Testing**: escalation paths を test します
3. **Fault Injection**: controlled environments で faults を inject します

### Cost Optimization Best Practices

#### Log Volume Optimization

costs を削減するために log volume を最適化します。

1. **Sampling**: high-volume logs を sample します
2. **Filtering**: 不要な logs を filter します
3. **Compression**: logs を圧縮します

#### Metric Cardinality Management

costs を削減するために metric cardinality を管理します。

1. **Label Limits**: metrics で使用する labels 数を制限します
2. **Aggregation**: detailed metrics を higher levels に aggregate します
3. **Sampling**: high-resolution metrics を sample します

#### Storage Tiering

cost-effective な storage tiering を実装します。

1. **Hot Storage**: recent logs と頻繁に access される logs
2. **Warm Storage**: access 頻度が低い logs
3. **Cold Storage**: archived logs

## Troubleshooting and Debugging

EKS clusters の issues を troubleshoot および debug するためのさまざまな techniques を見ていきましょう。

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

Issue: Pod が ImagePullBackOff state のままになる

Solutions:
1. image name と tag が正しいことを確認します
2. private registries 用の image pull secret を確認します
3. node に internet access があることを確認します

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

Issue: Pod が CrashLoopBackOff state で繰り返し restart している

Solutions:
1. pod logs を確認します
2. resource limits を確認します
3. application configuration を確認します

```bash
# Check pod logs
kubectl logs <pod-name> -n <namespace>

# Check pod events
kubectl describe pod <pod-name> -n <namespace>

# Add debug container
kubectl debug <pod-name> -n <namespace> --image=busybox:1.28 --target=<container-name>
```

#### Node NotReady State

Issue: Node が NotReady state として表示される

Solutions:
1. node status と events を確認します
2. kubelet logs を確認します
3. node resource usage を確認します

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

Issue: service に接続できない

Solutions:
1. service と endpoints を確認します
2. pod labels と selectors を確認します
3. network policies を確認します

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

このドキュメントでは、Amazon EKS clusters における monitoring と logging のためのさまざまな tools、techniques、best practices について説明しました。効果的な monitoring と logging strategy を実装することで、cluster の状態を継続的に把握し、issues を早期に検出し、problems 発生時に迅速に対応できます。

取り上げた主なトピック:

1. **Monitoring and Logging Overview**: monitoring と logging の重要性と architecture
2. **EKS Control Plane Logging**: Control plane log types とそれらを有効化する方法
3. **Container Logging**: Fluent Bit と CloudWatch Container Insights を使用した container log collection
4. **Cluster Monitoring**: CloudWatch、Prometheus、Grafana を使用した cluster monitoring
5. **Alerting and Event Management**: CloudWatch alarms と Prometheus Alertmanager を使用した alert configuration
6. **Log Analysis and Visualization**: CloudWatch Logs Insights、OpenSearch、Grafana Loki を使用した log analysis
7. **Monitoring and Logging Best Practices**: 効果的な monitoring と logging のための best practices
8. **Troubleshooting and Debugging**: Common issues と solutions

EKS clusters における monitoring と logging は、cluster と applications の requirements を満たすために継続的に改善すべき ongoing process です。

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

この章で学んだ内容を確認するには、[トピッククイズ](../quizzes/eks/06-eks-monitoring-logging-quiz.md) に挑戦してください。
