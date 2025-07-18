# Amazon EKS 모니터링 및 로깅

효과적인 모니터링 및 로깅은 Amazon EKS 클러스터의 안정성, 가용성 및 성능을 유지하는 데 필수적입니다. 이 문서에서는 EKS 클러스터에서 모니터링 및 로깅을 구현하기 위한 다양한 도구, 기술 및 모범 사례를 다룹니다.

## 목차

1. [모니터링 및 로깅 개요](#모니터링-및-로깅-개요)
2. [EKS 컨트롤 플레인 로깅](#eks-컨트롤-플레인-로깅)
3. [컨테이너 로깅](#컨테이너-로깅)
4. [클러스터 모니터링](#클러스터-모니터링)
5. [알림 및 이벤트 관리](#알림-및-이벤트-관리)
6. [로그 분석 및 시각화](#로그-분석-및-시각화)
7. [모니터링 및 로깅 모범 사례](#모니터링-및-로깅-모범-사례)
8. [문제 해결 및 디버깅](#문제-해결-및-디버깅)

## 모니터링 및 로깅 개요

### 모니터링과 로깅의 중요성

Amazon EKS 클러스터에서 모니터링과 로깅은 다음과 같은 이유로 중요합니다:

1. **가시성 확보**: 클러스터의 상태, 성능 및 동작에 대한 가시성 제공
2. **문제 감지**: 문제가 심각해지기 전에 조기 감지
3. **트렌드 분석**: 시간에 따른 성능 및 리소스 사용량 추세 파악
4. **용량 계획**: 리소스 요구사항 예측 및 계획
5. **보안 및 감사**: 보안 이벤트 감지 및 규정 준수 요구사항 충족
6. **문제 해결**: 문제 발생 시 신속한 진단 및 해결

### 모니터링 및 로깅 아키텍처

EKS 클러스터의 포괄적인 모니터링 및 로깅 아키텍처는 다음과 같은 구성 요소로 이루어집니다:

```mermaid
flowchart TD
    subgraph EKS["Amazon EKS 클러스터"]
        CP[컨트롤 플레인 로그] --> CWL
        subgraph Nodes["워커 노드"]
            Pods[파드/컨테이너] --> Fluent
            NodeExporter[노드 익스포터] --> Prometheus
            kubelet --> Prometheus
        end
    end
    
    subgraph AWS["AWS 서비스"]
        CWL[CloudWatch Logs]
        CWM[CloudWatch Metrics]
        XRay[X-Ray]
        ES[Amazon OpenSearch]
    end
    
    subgraph Monitoring["모니터링 스택"]
        Prometheus[Prometheus] --> Alertmanager
        Alertmanager[Alertmanager] --> Notification[알림 채널]
        Prometheus --> Grafana
    end
    
    subgraph Logging["로깅 스택"]
        Fluent[Fluent Bit/Fluentd] --> CWL
        Fluent --> ES
        ES --> Kibana[OpenSearch Dashboards]
    end
    
    CWL --> ES
    Prometheus --> CWM
    
    %% 클래스 정의
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    
    %% 클래스 적용
    class CWL,CWM,XRay,ES awsService;
    class CP,Pods,NodeExporter,kubelet,Prometheus,Alertmanager k8sComponent;
    class Fluent,Grafana,Kibana,Notification userApp;
```

### 모니터링 및 로깅 전략

효과적인 모니터링 및 로깅 전략을 개발하려면 다음 단계를 따르세요:

1. **목표 정의**: 모니터링 및 로깅의 목표와 요구사항 정의
2. **지표 및 로그 식별**: 수집할 핵심 지표 및 로그 식별
3. **도구 선택**: 요구사항에 맞는 모니터링 및 로깅 도구 선택
4. **기준선 설정**: 정상 동작에 대한 기준선 설정
5. **알림 구성**: 중요한 이벤트 및 임계값에 대한 알림 구성
6. **자동화**: 가능한 한 모니터링 및 로깅 프로세스 자동화
7. **정기적인 검토**: 모니터링 및 로깅 전략 정기적 검토 및 개선

## EKS 컨트롤 플레인 로깅

Amazon EKS는 클러스터의 컨트롤 플레인 로그를 Amazon CloudWatch Logs로 전송하는 기능을 제공합니다. 이를 통해 클러스터의 제어 구성 요소에 대한 가시성을 확보할 수 있습니다.

### 컨트롤 플레인 로그 유형

EKS는 다음과 같은 컨트롤 플레인 로그 유형을 지원합니다:

1. **API 서버(api)**: Kubernetes API 서버의 로그
2. **감사(audit)**: Kubernetes 감사 로그
3. **인증자(authenticator)**: AWS IAM 인증자의 로그
4. **컨트롤러 관리자(controllerManager)**: 컨트롤러 관리자의 로그
5. **스케줄러(scheduler)**: Kubernetes 스케줄러의 로그

### 컨트롤 플레인 로깅 활성화

AWS Management Console, AWS CLI 또는 eksctl을 사용하여 컨트롤 플레인 로깅을 활성화할 수 있습니다:

#### AWS CLI 사용

```bash
aws eks update-cluster-config \
  --region us-west-2 \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

#### eksctl 사용

```bash
eksctl utils update-cluster-logging \
  --region us-west-2 \
  --cluster my-cluster \
  --enable-types api,audit,authenticator,controllerManager,scheduler
```

### 컨트롤 플레인 로그 쿼리

CloudWatch Logs Insights를 사용하여 컨트롤 플레인 로그를 쿼리할 수 있습니다:

#### API 서버 오류 쿼리

```
fields @timestamp, @message
| filter @message like /Error/
| sort @timestamp desc
| limit 20
```

#### 인증 실패 쿼리

```
fields @timestamp, @message
| filter @message like /authentication failed/
| sort @timestamp desc
| limit 20
```

#### 감사 로그 쿼리

```
fields @timestamp, @message
| filter @message like /responseStatus.code="403"/
| sort @timestamp desc
| limit 20
```

### 컨트롤 플레인 로그 보존 및 비용 관리

CloudWatch Logs의 로그 보존 기간을 구성하여 비용을 관리할 수 있습니다:

```bash
aws logs put-retention-policy \
  --log-group-name /aws/eks/my-cluster/cluster \
  --retention-in-days 30
```

## 컨테이너 로깅

컨테이너 로그는 애플리케이션 문제를 진단하고 해결하는 데 중요한 정보를 제공합니다. EKS에서는 다양한 방법으로 컨테이너 로그를 수집하고 관리할 수 있습니다.

### 로깅 아키텍처

EKS에서 일반적인 컨테이너 로깅 아키텍처는 다음과 같습니다:

```mermaid
flowchart LR
    subgraph Node["워커 노드"]
        Containers[컨테이너] --> |stdout/stderr| kubelet
        kubelet --> |/var/log/containers/| LogAgent[로그 에이전트]
    end
    
    LogAgent --> CWL[CloudWatch Logs]
    LogAgent --> ES[Amazon OpenSearch]
    LogAgent --> S3[Amazon S3]
    
    %% 클래스 정의
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    
    %% 클래스 적용
    class CWL,ES,S3 awsService;
    class kubelet k8sComponent;
    class Containers userApp;
    class LogAgent default;
```

### Fluent Bit를 사용한 로그 수집

Fluent Bit는 경량 로그 수집기로, EKS 클러스터에서 컨테이너 로그를 수집하는 데 널리 사용됩니다:

#### Fluent Bit 설치

Helm을 사용하여 Fluent Bit를 설치합니다:

```bash
helm repo add aws-for-fluent-bit https://aws.github.io/eks-charts
helm repo update
helm install aws-for-fluent-bit aws-for-fluent-bit/aws-for-fluent-bit \
  --namespace kube-system \
  --set cloudWatch.region=us-west-2 \
  --set cloudWatch.logGroupName=/aws/eks/my-cluster/fluentbit
```

#### Fluent Bit 구성

사용자 정의 구성을 위한 ConfigMap:

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

CloudWatch Container Insights는 컨테이너화된 애플리케이션 및 마이크로서비스의 지표 및 로그를 수집, 집계 및 요약합니다:

#### Container Insights 설치

```bash
ClusterName=my-cluster
RegionName=us-west-2
FluentBitHttpPort='2020'
FluentBitReadFromHead='Off'
[[ ${FluentBitReadFromHead} = 'On' ]] && FluentBitReadFromTail='Off'|| FluentBitReadFromTail='On'
[[ -z ${FluentBitHttpPort} ]] && FluentBitHttpServer='Off' || FluentBitHttpServer='On'

kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluent-bit-quickstart.yaml
```

#### Container Insights 대시보드

CloudWatch 콘솔에서 Container Insights 대시보드에 액세스하여 다음을 모니터링할 수 있습니다:
- 노드, 파드, 컨테이너 수준의 CPU 및 메모리 사용량
- 네트워크 및 디스크 I/O
- 파드 및 컨테이너 상태
- 클러스터 실패 및 이벤트

### 사용자 정의 로깅 솔루션

특정 요구사항에 맞는 사용자 정의 로깅 솔루션을 구현할 수 있습니다:

#### EFK(Elasticsearch, Fluentd, Kibana) 스택

```bash
# Elasticsearch 설치
helm repo add elastic https://helm.elastic.co
helm repo update
helm install elasticsearch elastic/elasticsearch \
  --namespace logging \
  --create-namespace \
  --set replicas=3

# Fluentd 설치
helm install fluentd stable/fluentd \
  --namespace logging \
  --set output.host=elasticsearch-master.logging.svc.cluster.local

# Kibana 설치
helm install kibana elastic/kibana \
  --namespace logging \
  --set service.type=LoadBalancer
```

#### PLG(Promtail, Loki, Grafana) 스택

```bash
# Loki 및 Promtail 설치
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

### 로그 구조화 및 파싱

효과적인 로그 분석을 위해 구조화된 로그 형식을 사용하는 것이 좋습니다:

#### JSON 로그 형식

애플리케이션에서 JSON 형식의 로그를 출력합니다:

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

#### 로그 파서 구성

Fluent Bit에서 로그 파싱을 위한 구성:

```
[PARSER]
    Name        json
    Format      json
    Time_Key    timestamp
    Time_Format %Y-%m-%dT%H:%M:%S%z
```

## 클러스터 모니터링

효과적인 클러스터 모니터링은 EKS 클러스터의 상태, 성능 및 리소스 사용량을 추적하는 데 필수적입니다. 이 섹션에서는 EKS 클러스터를 모니터링하기 위한 다양한 도구와 기술을 살펴봅니다.

```mermaid
flowchart TD
    subgraph Monitoring_Solutions ["모니터링 솔루션"]
        subgraph AWS_Solutions ["AWS 솔루션"]
            CW_CI["CloudWatch
                Container Insights"]
            CW_LA["CloudWatch
                Logs Insights"]
            CW_Alarms["CloudWatch
                경보"]
            AMP["Amazon Managed
                Prometheus"]
            AMG["Amazon Managed
                Grafana"]
        end
        
        subgraph K8s_Solutions ["Kubernetes 솔루션"]
            Prometheus[Prometheus]
            Grafana[Grafana]
            Kube_State[kube-state-metrics]
            Node_Exporter[Node Exporter]
            K8s_Dashboard["Kubernetes
                대시보드"]
        end
        
        subgraph Tracing_Solutions ["추적 솔루션"]
            XRay[AWS X-Ray]
            Jaeger[Jaeger]
            OpenTelemetry[OpenTelemetry]
        end
    end
    
    subgraph Monitoring_Targets ["모니터링 대상"]
        subgraph Cluster_Level ["클러스터 수준"]
            Control_Plane[컨트롤 플레인]
            API_Server[API 서버]
            Scheduler[스케줄러]
            Controller[컨트롤러 관리자]
        end
        
        subgraph Node_Level ["노드 수준"]
            CPU[CPU 사용량]
            Memory[메모리 사용량]
            Disk[디스크 I/O]
            Network[네트워크 I/O]
        end
        
        subgraph Pod_Level ["파드 수준"]
            Pod_CPU[파드 CPU]
            Pod_Memory[파드 메모리]
            Pod_Network[파드 네트워크]
            Restarts[재시작 횟수]
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
    
    %% 클래스 정의
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    
    %% 클래스 적용
    class CW_CI,CW_LA,CW_Alarms,AMP,AMG,XRay awsService;
    class Prometheus,Grafana,Kube_State,Node_Exporter,K8s_Dashboard,Control_Plane,API_Server,Scheduler,Controller k8sComponent;
    class Jaeger,OpenTelemetry userApp;
    class CPU,Memory,Disk,Network,Pod_CPU,Pod_Memory,Pod_Network,Restarts default;
```

### CloudWatch Container Insights

Amazon CloudWatch Container Insights는 컨테이너화된 애플리케이션 및 마이크로서비스의 지표, 로그 및 이벤트를 수집, 집계 및 요약합니다:

#### Container Insights 활성화

CloudWatch 에이전트를 사용하여 Container Insights를 활성화합니다:

```bash
ClusterName=my-cluster
RegionName=us-west-2
FluentBitHttpPort='2020'
FluentBitReadFromHead='Off'
[[ ${FluentBitReadFromHead} = 'On' ]] && FluentBitReadFromTail='Off'|| FluentBitReadFromTail='On'
[[ -z ${FluentBitHttpPort} ]] && FluentBitHttpServer='Off' || FluentBitHttpServer='On'

curl https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluent-bit-quickstart.yaml | sed 's/{{cluster_name}}/'${ClusterName}'/;s/{{region_name}}/'${RegionName}'/;s/{{http_server_toggle}}/"'${FluentBitHttpServer}'"/;s/{{http_server_port}}/"'${FluentBitHttpPort}'"/;s/{{read_from_head}}/"'${FluentBitReadFromHead}'"/;s/{{read_from_tail}}/"'${FluentBitReadFromTail}'"/' | kubectl apply -f -
```

#### Container Insights 지표

Container Insights는 다음과 같은 지표를 수집합니다:

- **클러스터 수준**: 노드 수, 파드 수, 실패한 파드 수
- **노드 수준**: CPU 사용량, 메모리 사용량, 네트워크 I/O, 디스크 I/O
- **파드 수준**: CPU 사용량, 메모리 사용량, 네트워크 I/O
- **서비스 수준**: 파드 수, CPU 사용량, 메모리 사용량

#### Container Insights 대시보드

CloudWatch 콘솔에서 Container Insights 대시보드에 액세스하여 클러스터 성능을 시각화할 수 있습니다:

1. AWS Management Console에 로그인
2. CloudWatch 서비스로 이동
3. 왼쪽 탐색 창에서 "Insights" > "Container Insights" 선택
4. 클러스터, 노드, 파드 또는 서비스 보기 선택

#### Container Insights 알림

CloudWatch 경보를 설정하여 지표가 특정 임계값을 초과할 때 알림을 받을 수 있습니다:

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
### Prometheus 및 Grafana

Prometheus는 시계열 데이터베이스 및 모니터링 시스템이며, Grafana는 지표를 시각화하기 위한 대시보드 도구입니다. 이 두 도구를 함께 사용하여 EKS 클러스터를 포괄적으로 모니터링할 수 있습니다.

#### Amazon Managed Service for Prometheus 및 Grafana

AWS는 Prometheus 및 Grafana의 관리형 서비스를 제공합니다:

1. **Amazon Managed Service for Prometheus(AMP)** 설정:

```bash
# AMP 작업 영역 생성
aws amp create-workspace --alias my-amp-workspace

# Prometheus 서버 설치 및 AMP로 원격 쓰기 구성
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/prometheus \
  --namespace prometheus \
  --create-namespace \
  --set server.remoteWrite[0].url=https://aps-workspaces.us-west-2.amazonaws.com/workspaces/ws-12345678-1234-1234-1234-123456789012/api/v1/remote_write \
  --set server.remoteWrite[0].sigv4.region=us-west-2
```

2. **Amazon Managed Grafana(AMG)** 설정:

```bash
# AMG 작업 영역 생성
aws grafana create-workspace \
  --name my-grafana-workspace \
  --authentication-providers AWS_SSO \
  --permission-type SERVICE_MANAGED

# AMP 데이터 소스 추가
aws grafana create-workspace-service-account \
  --workspace-id g-12345678 \
  --name amp-datasource \
  --service-account-role ADMIN
```

#### 자체 관리형 Prometheus 및 Grafana

자체 관리형 Prometheus 및 Grafana를 EKS 클러스터에 배포할 수도 있습니다:

1. **kube-prometheus-stack 설치**:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set grafana.service.type=LoadBalancer
```

2. **Grafana 액세스**:

```bash
# Grafana 서비스 URL 가져오기
kubectl get svc -n monitoring monitoring-grafana -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

# 기본 사용자 이름 및 암호 가져오기
kubectl get secret -n monitoring monitoring-grafana -o jsonpath='{.data.admin-user}' | base64 --decode
kubectl get secret -n monitoring monitoring-grafana -o jsonpath='{.data.admin-password}' | base64 --decode
```

#### 주요 Prometheus 지표

Prometheus는 다음과 같은 중요한 Kubernetes 지표를 수집합니다:

- **노드 지표**: CPU, 메모리, 디스크, 네트워크 사용량
- **파드 지표**: CPU, 메모리 사용량, 재시작 횟수
- **컨테이너 지표**: CPU, 메모리 사용량, 파일 시스템 사용량
- **API 서버 지표**: 요청 지연 시간, 요청 수, 오류율
- **etcd 지표**: 지연 시간, 디스크 I/O, 리더 변경

#### 유용한 Grafana 대시보드

Grafana에서 다음과 같은 유용한 대시보드를 가져올 수 있습니다:

1. **Kubernetes 클러스터 모니터링** (ID: 15661)
2. **노드 익스포터 전체** (ID: 1860)
3. **Kubernetes 파드 모니터링** (ID: 6417)
4. **Kubernetes API 서버** (ID: 12006)
5. **Kubernetes 리소스 요청/한도** (ID: 13770)

#### PromQL 쿼리 예시

Prometheus Query Language(PromQL)를 사용하여 유용한 쿼리를 작성할 수 있습니다:

```
# 노드별 CPU 사용량
sum(rate(node_cpu_seconds_total{mode!="idle"}[5m])) by (instance) / count(node_cpu_seconds_total{mode="idle"}) by (instance) * 100

# 파드별 메모리 사용량 (상위 10개)
topk(10, sum(container_memory_usage_bytes{container!=""}) by (pod))

# 컨테이너 재시작 횟수
sum(kube_pod_container_status_restarts_total) by (pod)

# 노드별 디스크 사용량 비율
100 - ((node_filesystem_avail_bytes{mountpoint="/"} * 100) / node_filesystem_size_bytes{mountpoint="/"})
```
### AWS X-Ray를 사용한 분산 추적

AWS X-Ray는 애플리케이션이 처리하는 요청에 대한 데이터를 수집하고, 이를 사용하여 애플리케이션 문제를 식별하고 최적화 기회를 찾는 데 도움이 됩니다.

#### X-Ray 설정

1. **X-Ray 데몬 설치**:

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

2. **애플리케이션에 X-Ray SDK 통합**:

Java 애플리케이션 예시:

```java
import com.amazonaws.xray.AWSXRay;
import com.amazonaws.xray.AWSXRayRecorderBuilder;
import com.amazonaws.xray.plugins.EKSPlugin;

public class Application {
    static {
        AWSXRayRecorderBuilder builder = AWSXRayRecorderBuilder.standard().withPlugin(new EKSPlugin());
        AWSXRay.setGlobalRecorder(builder.build());
    }
    
    // 애플리케이션 코드
}
```

#### X-Ray 서비스 맵

X-Ray 서비스 맵을 사용하여 마이크로서비스 아키텍처의 구성 요소 간 관계와 통신을 시각화할 수 있습니다:

1. AWS Management Console에 로그인
2. X-Ray 서비스로 이동
3. 왼쪽 탐색 창에서 "서비스 맵" 선택
4. 서비스 간 지연 시간, 오류 및 장애 지점 확인

#### X-Ray 분석 및 인사이트

X-Ray Analytics를 사용하여 추적 데이터를 분석하고 성능 병목 현상을 식별할 수 있습니다:

1. AWS Management Console에서 X-Ray 서비스로 이동
2. 왼쪽 탐색 창에서 "Analytics" 선택
3. 응답 시간 분포, 오류율 및 장애 지점 분석

### Kubernetes 대시보드

Kubernetes 대시보드는 클러스터 리소스를 관리하고 문제를 해결하기 위한 웹 기반 UI를 제공합니다:

#### Kubernetes 대시보드 설치

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml

# 대시보드 액세스를 위한 서비스 계정 및 클러스터 역할 바인딩 생성
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

# 액세스 토큰 생성
kubectl -n kubernetes-dashboard create token admin-user
```

#### 대시보드 액세스

```bash
# 대시보드 프록시 시작
kubectl proxy

# 브라우저에서 다음 URL 액세스
# http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/
```

### 사용자 정의 지표 및 모니터링

애플리케이션별 지표를 수집하고 모니터링하기 위한 사용자 정의 솔루션을 구현할 수 있습니다:

#### Prometheus 클라이언트 라이브러리 통합

애플리케이션에 Prometheus 클라이언트 라이브러리를 통합하여 사용자 정의 지표를 노출합니다:

Java 애플리케이션 예시:

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
        // 애플리케이션 코드
    }
    
    public void processRequest() {
        requests.inc();
        Histogram.Timer timer = requestLatency.startTimer();
        try {
            // 요청 처리
        } finally {
            timer.observeDuration();
        }
    }
}
```

#### 사용자 정의 지표 수집

Prometheus ServiceMonitor를 사용하여 사용자 정의 지표를 수집합니다:

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

#### 사용자 정의 대시보드

Grafana에서 사용자 정의 대시보드를 생성하여 애플리케이션 지표를 시각화합니다:

1. Grafana에 로그인
2. "+" 아이콘을 클릭하고 "대시보드" 선택
3. "패널 추가" 클릭
4. 데이터 소스로 "Prometheus" 선택
5. PromQL 쿼리 작성(예: `rate(app_requests_total[5m])`)
6. 패널 제목, 설명 및 시각화 유형 구성
7. "저장" 클릭
## 알림 및 이벤트 관리

효과적인 알림 및 이벤트 관리는 EKS 클러스터에서 문제를 신속하게 감지하고 대응하는 데 필수적입니다. 이 섹션에서는 EKS 클러스터에서 알림 및 이벤트를 관리하기 위한 다양한 도구와 기술을 살펴봅니다.

```mermaid
flowchart TD
    subgraph Alert_Sources ["알림 소스"]
        subgraph Metrics ["지표 기반"]
            CW_Metrics[CloudWatch 지표]
            Prom_Metrics[Prometheus 지표]
            Custom_Metrics[사용자 정의 지표]
        end
        
        subgraph Logs ["로그 기반"]
            CW_Logs[CloudWatch 로그]
            ES_Logs[OpenSearch 로그]
            Loki_Logs[Loki 로그]
        end
        
        subgraph Events ["이벤트 기반"]
            K8s_Events[Kubernetes 이벤트]
            AWS_Events[AWS 이벤트]
            App_Events[애플리케이션 이벤트]
        end
    end
    
    subgraph Alert_Processing ["알림 처리"]
        CW_Alarms[CloudWatch 경보]
        Prom_AM["Prometheus
                Alertmanager"]
        EventBridge[Amazon EventBridge]
        Event_Router[이벤트 라우터]
    end
    
    subgraph Notification_Channels ["알림 채널"]
        SNS[Amazon SNS]
        SQS[Amazon SQS]
        Lambda[AWS Lambda]
        Email[이메일]
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
    
    %% 클래스 정의
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    
    %% 클래스 적용
    class CW_Metrics,CW_Logs,CW_Alarms,EventBridge,SNS,SQS,Lambda,AWS_Events awsService;
    class K8s_Events,Prom_AM k8sComponent;
    class Prom_Metrics,Custom_Metrics,ES_Logs,Loki_Logs,App_Events,Event_Router,Email,Slack,PagerDuty,OpsGenie userApp;
```

### CloudWatch 경보

Amazon CloudWatch 경보를 사용하여 지표가 특정 임계값을 초과할 때 알림을 받을 수 있습니다:

#### 클러스터 CPU 사용량 경보

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

#### 메모리 사용량 경보

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

#### 디스크 사용량 경보

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

Prometheus Alertmanager는 Prometheus에서 생성된 알림을 처리하고 적절한 알림 채널로 라우팅합니다:

#### Alertmanager 구성

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

#### 알림 규칙 구성

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

### EventBridge 이벤트 규칙

Amazon EventBridge를 사용하여 EKS 클러스터의 이벤트에 대응하는 규칙을 생성할 수 있습니다:

#### EKS 클러스터 상태 변경 이벤트 규칙

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

#### EKS 노드 그룹 이벤트 규칙

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

### Kubernetes 이벤트 모니터링

Kubernetes 이벤트는 클러스터에서 발생하는 중요한 활동에 대한 정보를 제공합니다:

#### 이벤트 모니터링 도구 설치

```bash
# event-exporter 설치
kubectl apply -f https://raw.githubusercontent.com/opsgenie/kubernetes-event-exporter/master/deploy/01-cluster-role.yaml
kubectl apply -f https://raw.githubusercontent.com/opsgenie/kubernetes-event-exporter/master/deploy/02-service-account.yaml
kubectl apply -f https://raw.githubusercontent.com/opsgenie/kubernetes-event-exporter/master/deploy/03-cluster-role-binding.yaml
```

#### 이벤트 내보내기 구성

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

#### 이벤트 내보내기 배포

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

### 알림 채널 통합

다양한 알림 채널을 통합하여 팀에 알림을 전달할 수 있습니다:

#### Slack 통합

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

#### PagerDuty 통합

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

#### 이메일 통합

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

### 알림 관리 및 에스컬레이션

알림을 효과적으로 관리하고 에스컬레이션하기 위한 전략을 구현할 수 있습니다:

#### 알림 심각도 수준

알림을 다음과 같은 심각도 수준으로 분류합니다:

- **Critical**: 즉각적인 조치가 필요한 심각한 문제
- **Warning**: 주의가 필요하지만 즉각적인 조치가 필요하지 않은 문제
- **Info**: 정보 제공 목적의 알림

#### 알림 에스컬레이션 정책

PagerDuty와 같은 도구를 사용하여 알림 에스컬레이션 정책을 구현합니다:

1. **1차 대응**: 온콜 엔지니어에게 알림
2. **에스컬레이션 1**: 15분 후 응답이 없으면 백업 엔지니어에게 알림
3. **에스컬레이션 2**: 30분 후 응답이 없으면 팀 리더에게 알림
4. **에스컬레이션 3**: 45분 후 응답이 없으면 관리자에게 알림

#### 알림 피로 감소

알림 피로를 줄이기 위한 전략을 구현합니다:

1. **알림 그룹화**: 관련 알림을 그룹화하여 중복 알림 감소
2. **알림 필터링**: 중요한 알림만 전달하도록 필터링
3. **알림 조절**: 반복되는 알림의 빈도 제한
4. **알림 시간대**: 비즈니스 크리티컬하지 않은 알림은 업무 시간에만 전달
## 로그 분석 및 시각화

로그 분석 및 시각화는 EKS 클러스터에서 발생하는 문제를 진단하고 해결하는 데 중요한 역할을 합니다. 이 섹션에서는 EKS 클러스터의 로그를 분석하고 시각화하기 위한 다양한 도구와 기술을 살펴봅니다.

```mermaid
flowchart TD
    subgraph Log_Sources ["로그 소스"]
        CP_Logs[컨트롤 플레인 로그]
        Container_Logs[컨테이너 로그]
        App_Logs[애플리케이션 로그]
        AWS_Service_Logs[AWS 서비스 로그]
    end
    
    subgraph Log_Collection ["로그 수집"]
        Fluent_Bit[Fluent Bit]
        Fluentd[Fluentd]
        CloudWatch_Agent[CloudWatch 에이전트]
        Vector[Vector]
    end
    
    subgraph Log_Storage ["로그 저장"]
        CW_Logs[CloudWatch Logs]
        OpenSearch[Amazon OpenSearch]
        S3[Amazon S3]
        Loki[Grafana Loki]
    end
    
    subgraph Log_Analysis ["로그 분석"]
        CW_Insights[CloudWatch Logs Insights]
        OS_Dashboards[OpenSearch Dashboards]
        Athena[Amazon Athena]
        Grafana_Explore[Grafana Explore]
    end
    
    subgraph Visualization ["시각화"]
        OS_Visualizations[OpenSearch 시각화]
        Grafana_Dashboards[Grafana 대시보드]
        QuickSight[Amazon QuickSight]
        Custom_Dashboards[사용자 정의 대시보드]
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
    
    %% 클래스 정의
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    
    %% 클래스 적용
    class CW_Logs,CW_Insights,OpenSearch,S3,Athena,QuickSight,CloudWatch_Agent,AWS_Service_Logs awsService;
    class CP_Logs k8sComponent;
    class Fluent_Bit,Fluentd,Vector,Container_Logs,App_Logs userApp;
    class OS_Dashboards,OS_Visualizations,Grafana_Dashboards,Grafana_Explore,Custom_Dashboards,Loki dataStore;
```

### CloudWatch Logs Insights

CloudWatch Logs Insights를 사용하여 EKS 클러스터의 로그를 쿼리하고 분석할 수 있습니다:

#### 컨테이너 로그 쿼리

```
fields @timestamp, kubernetes.pod_name, log
| filter kubernetes.namespace_name = "default"
| filter kubernetes.container_name = "app"
| filter log like /ERROR/
| sort @timestamp desc
| limit 20
```

#### API 서버 오류 쿼리

```
fields @timestamp, @message
| filter @logStream like /kube-apiserver/
| filter @message like /Error/
| sort @timestamp desc
| limit 20
```

#### 인증 실패 쿼리

```
fields @timestamp, @message
| filter @logStream like /authenticator/
| filter @message like /authentication failed/
| sort @timestamp desc
| limit 20
```

#### 로그 패턴 분석

```
fields @timestamp, @message
| parse @message "* * * [*] *" as date, time, level, component, message
| stats count(*) as count by level, component
| sort count desc
```

### Amazon OpenSearch Service

Amazon OpenSearch Service(이전의 Amazon Elasticsearch Service)를 사용하여 EKS 클러스터의 로그를 저장, 분석 및 시각화할 수 있습니다:

#### OpenSearch 도메인 생성

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

#### Fluent Bit를 사용하여 OpenSearch로 로그 전송

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

#### OpenSearch Dashboards를 사용한 로그 시각화

OpenSearch Dashboards에서 다음과 같은 시각화를 생성할 수 있습니다:

1. **로그 탐색기**: 로그 검색 및 필터링
2. **대시보드**: 로그 데이터를 기반으로 한 대시보드 생성
3. **시각화**: 로그 데이터를 기반으로 한 차트 및 그래프 생성
4. **알림**: 로그 패턴에 기반한 알림 구성

### Grafana Loki

Grafana Loki는 로그 집계 시스템으로, Prometheus와 유사한 레이블 기반 접근 방식을 사용합니다:

#### Loki 설치

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

#### LogQL 쿼리 예시

```
# 특정 네임스페이스의 오류 로그 검색
{namespace="default"} |= "ERROR"

# 특정 파드의 로그 검색
{namespace="default", pod=~"app-.*"} | json

# 로그 레벨별 로그 수 계산
sum by (level) (count_over_time({namespace="default"} | json | level=~"info|warn|error" [5m]))
```

#### Grafana 대시보드 생성

Grafana에서 Loki 데이터 소스를 사용하여 로그 대시보드를 생성할 수 있습니다:

1. Grafana에 로그인
2. "+" 아이콘을 클릭하고 "대시보드" 선택
3. "패널 추가" 클릭
4. 데이터 소스로 "Loki" 선택
5. LogQL 쿼리 작성
6. 패널 제목, 설명 및 시각화 유형 구성
7. "저장" 클릭

### AWS CloudTrail

AWS CloudTrail을 사용하여 EKS 클러스터와 관련된 AWS API 호출을 로깅하고 분석할 수 있습니다:

#### CloudTrail 추적 생성

```bash
aws cloudtrail create-trail \
  --name eks-api-trail \
  --s3-bucket-name my-cloudtrail-bucket \
  --is-multi-region-trail \
  --include-global-service-events

aws cloudtrail start-logging --name eks-api-trail
```

#### CloudTrail 이벤트 필터링

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventSource,AttributeValue=eks.amazonaws.com
```

#### CloudTrail Lake 쿼리

```sql
SELECT eventTime, eventName, userIdentity.arn, requestParameters
FROM eks_events
WHERE eventSource = 'eks.amazonaws.com'
  AND eventName LIKE '%Cluster%'
  AND eventTime >= '2025-07-01T00:00:00Z'
  AND eventTime <= '2025-07-11T23:59:59Z'
ORDER BY eventTime DESC
```

### 로그 분석 모범 사례

EKS 클러스터의 로그를 효과적으로 분석하기 위한 모범 사례:

#### 구조화된 로깅

애플리케이션에서 구조화된 로그 형식(예: JSON)을 사용합니다:

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

#### 상관 ID

분산 시스템에서 요청을 추적하기 위해 상관 ID를 사용합니다:

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
            // 요청 처리
        } finally {
            MDC.remove("correlation_id");
        }
    }
}
```

#### 로그 수준 사용

적절한 로그 수준을 사용하여 로그의 중요도를 나타냅니다:

- **ERROR**: 애플리케이션 오류 및 예외
- **WARN**: 잠재적인 문제 또는 예상치 못한 상황
- **INFO**: 일반적인 애플리케이션 이벤트
- **DEBUG**: 디버깅에 유용한 상세 정보
- **TRACE**: 매우 상세한 디버깅 정보

#### 로그 보존 정책

비용 및 규정 준수 요구사항에 따라 로그 보존 정책을 설정합니다:

```bash
# CloudWatch Logs 로그 그룹 보존 기간 설정
aws logs put-retention-policy \
  --log-group-name /aws/eks/my-cluster/cluster \
  --retention-in-days 30

# S3 버킷 수명 주기 정책 설정
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
## 모니터링 및 로깅 모범 사례

EKS 클러스터의 모니터링 및 로깅을 효과적으로 구현하기 위한 모범 사례를 살펴보겠습니다.

### 모니터링 모범 사례

#### 다중 계층 모니터링

EKS 클러스터의 모든 계층을 모니터링합니다:

1. **인프라 계층**: EC2 인스턴스, VPC, 서브넷, 보안 그룹
2. **클러스터 계층**: 컨트롤 플레인, 노드, 파드, 서비스
3. **애플리케이션 계층**: 애플리케이션 성능, 사용자 경험

#### 골든 시그널 모니터링

Google의 SRE 책에서 제안하는 "4개의 골든 시그널"에 초점을 맞춥니다:

1. **지연 시간**: 요청을 처리하는 데 걸리는 시간
2. **트래픽**: 시스템에 대한 요청 수
3. **오류**: 실패한 요청의 비율
4. **포화도**: 시스템이 얼마나 "가득 찼는지"(예: 메모리 사용량)

#### 프로액티브 모니터링

문제가 발생하기 전에 감지하기 위한 프로액티브 모니터링을 구현합니다:

1. **추세 분석**: 시간에 따른 리소스 사용량 추세 분석
2. **이상 탐지**: 비정상적인 패턴 감지
3. **예측 분석**: 미래 리소스 요구사항 예측

#### 자동화된 스케일링

모니터링 데이터를 기반으로 자동화된 스케일링을 구현합니다:

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

#### 비즈니스 지표 모니터링

기술적 지표뿐만 아니라 비즈니스 지표도 모니터링합니다:

1. **사용자 활동**: 활성 사용자 수, 세션 길이
2. **트랜잭션**: 트랜잭션 수, 트랜잭션 값
3. **전환율**: 사용자 전환율, 이탈률
4. **SLA 준수**: 서비스 수준 목표(SLO) 달성 여부

### 로깅 모범 사례

#### 중앙 집중식 로깅

모든 로그를 중앙 위치에 집계합니다:

1. **일관된 형식**: 모든 애플리케이션에서 일관된 로그 형식 사용
2. **중앙 저장소**: CloudWatch Logs, OpenSearch, Loki와 같은 중앙 로그 저장소 사용
3. **로그 전송**: Fluent Bit, Fluentd와 같은 로그 전송 에이전트 사용

#### 컨텍스트 정보 포함

로그에 충분한 컨텍스트 정보를 포함합니다:

1. **타임스탬프**: 정확한 타임스탬프(ISO 8601 형식 권장)
2. **요청 ID**: 분산 시스템에서 요청 추적을 위한 고유 ID
3. **사용자 정보**: 사용자 ID 또는 세션 ID(개인 식별 정보 제외)
4. **서비스 정보**: 서비스 이름, 버전, 인스턴스 ID
5. **오류 세부 정보**: 오류 코드, 오류 메시지, 스택 트레이스

#### 로그 수준 필터링

환경에 따라 적절한 로그 수준을 설정합니다:

1. **개발 환경**: DEBUG 또는 TRACE 수준
2. **스테이징 환경**: INFO 수준
3. **프로덕션 환경**: INFO 또는 WARN 수준(필요에 따라 DEBUG 활성화 가능)

#### 민감 정보 보호

로그에서 민감한 정보를 보호합니다:

1. **PII 마스킹**: 개인 식별 정보(PII) 마스킹
2. **자격 증명 제외**: 암호, 토큰, API 키와 같은 자격 증명 제외
3. **암호화**: 저장 및 전송 중인 로그 암호화

### 알림 모범 사례

#### 알림 우선순위 지정

알림의 우선순위를 지정하여 알림 피로를 줄입니다:

1. **P1(Critical)**: 즉각적인 조치가 필요한 심각한 문제
2. **P2(High)**: 업무 시간 내에 조치가 필요한 중요한 문제
3. **P3(Medium)**: 계획된 유지 관리 중에 조치가 필요한 문제
4. **P4(Low)**: 정보 제공 목적의 알림

#### 알림 그룹화

관련 알림을 그룹화하여 중복 알림을 줄입니다:

```yaml
route:
  group_by: ['alertname', 'job', 'instance']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
```

#### 실행 가능한 알림

알림에 문제 해결을 위한 충분한 정보를 포함합니다:

1. **명확한 제목**: 문제를 명확하게 설명하는 제목
2. **상세한 설명**: 문제의 원인과 영향에 대한 상세한 설명
3. **문제 해결 단계**: 문제 해결을 위한 단계 또는 링크
4. **관련 지표 및 로그**: 문제 진단에 도움이 되는 지표 및 로그 링크

#### 알림 테스트

알림 시스템을 정기적으로 테스트합니다:

1. **알림 시뮬레이션**: 테스트 알림 생성
2. **에스컬레이션 테스트**: 에스컬레이션 경로 테스트
3. **장애 주입**: 제어된 환경에서 장애 주입

### 비용 최적화 모범 사례

#### 로그 볼륨 최적화

로그 볼륨을 최적화하여 비용을 절감합니다:

1. **샘플링**: 높은 볼륨의 로그 샘플링
2. **필터링**: 불필요한 로그 필터링
3. **압축**: 로그 압축

#### 지표 카디널리티 관리

지표 카디널리티를 관리하여 비용을 절감합니다:

1. **레이블 제한**: 지표에 사용되는 레이블 수 제한
2. **집계**: 상세 지표를 더 높은 수준으로 집계
3. **샘플링**: 고해상도 지표 샘플링

#### 스토리지 계층화

비용 효율적인 스토리지 계층화를 구현합니다:

1. **핫 스토리지**: 최근 로그 및 자주 액세스하는 로그
2. **웜 스토리지**: 덜 자주 액세스하는 로그
3. **콜드 스토리지**: 아카이브된 로그

## 문제 해결 및 디버깅

EKS 클러스터에서 발생하는 문제를 해결하고 디버깅하기 위한 다양한 기술을 살펴보겠습니다.

```mermaid
flowchart TD
    subgraph Troubleshooting_Areas ["문제 해결 영역"]
        subgraph Cluster_Issues ["클러스터 문제"]
            Control_Plane[컨트롤 플레인 문제]
            Node_Issues[노드 문제]
            Networking[네트워킹 문제]
            Auth_Issues[인증/인가 문제]
        end
        
        subgraph Workload_Issues ["워크로드 문제"]
            Pod_Issues[파드 문제]
            Service_Issues[서비스 문제]
            Deployment_Issues[배포 문제]
            Resource_Issues[리소스 문제]
        end
        
        subgraph Common_Problems ["일반적인 문제"]
            ImagePull[ImagePullBackOff]
            CrashLoop[CrashLoopBackOff]
            NodeNotReady[노드 NotReady]
            Connection[서비스 연결 문제]
        end
    end
    
    subgraph Debugging_Tools ["디버깅 도구"]
        subgraph K8s_Tools ["Kubernetes 도구"]
            Kubectl[kubectl]
            K8s_Debug[kubectl debug]
            K8s_Events[kubectl events]
            K8s_Logs[kubectl logs]
        end
        
        subgraph AWS_Tools ["AWS 도구"]
            AWS_CLI[AWS CLI]
            CloudWatch[CloudWatch]
            CloudTrail[CloudTrail]
            X_Ray[X-Ray]
        end
        
        subgraph Network_Tools ["네트워크 도구"]
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
    
    %% 클래스 정의
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    
    %% 클래스 적용
    class AWS_CLI,CloudWatch,CloudTrail,X_Ray awsService;
    class Kubectl,K8s_Debug,K8s_Events,K8s_Logs,Control_Plane,Node_Issues,Pod_Issues,Service_Issues,Deployment_Issues k8sComponent;
    class Netshoot,TCPDump,Dig,Curl userApp;
    class ImagePull,CrashLoop,NodeNotReady,Connection,Networking,Auth_Issues,Resource_Issues default;
```

### 클러스터 문제 해결

#### 클러스터 상태 확인

```bash
# 클러스터 상태 확인
aws eks describe-cluster --name my-cluster --query "cluster.status"

# 클러스터 엔드포인트 확인
aws eks describe-cluster --name my-cluster --query "cluster.endpoint"

# 클러스터 로그 확인
aws eks update-cluster-config \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# CloudWatch Logs에서 클러스터 로그 확인
aws logs get-log-events \
  --log-group-name /aws/eks/my-cluster/cluster \
  --log-stream-name kube-apiserver-12345abcde \
  --limit 10
```

#### 노드 문제 해결

```bash
# 노드 상태 확인
kubectl get nodes
kubectl describe node <node-name>

# 노드 그룹 상태 확인
aws eks describe-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup

# 노드 로그 확인
aws ec2 get-console-output \
  --instance-id i-1234567890abcdef0

# SSH를 통한 노드 액세스
ssh -i ~/.ssh/my-key.pem ec2-user@<node-ip>
```

#### 파드 문제 해결

```bash
# 파드 상태 확인
kubectl get pods -A
kubectl describe pod <pod-name> -n <namespace>

# 파드 로그 확인
kubectl logs <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace> --previous  # 이전 컨테이너의 로그

# 파드 이벤트 확인
kubectl get events -n <namespace> --sort-by='.lastTimestamp'

# 파드 셸 액세스
kubectl exec -it <pod-name> -n <namespace> -- /bin/bash
```

### 네트워킹 문제 해결

#### 서비스 문제 해결

```bash
# 서비스 상태 확인
kubectl get svc -A
kubectl describe svc <service-name> -n <namespace>

# 엔드포인트 확인
kubectl get endpoints <service-name> -n <namespace>

# DNS 확인
kubectl run -it --rm --restart=Never busybox --image=busybox:1.28 -- nslookup <service-name>.<namespace>.svc.cluster.local

# 포트 포워딩
kubectl port-forward svc/<service-name> 8080:80 -n <namespace>
```

#### 네트워크 정책 문제 해결

```bash
# 네트워크 정책 확인
kubectl get networkpolicies -A
kubectl describe networkpolicy <policy-name> -n <namespace>

# 네트워크 연결 테스트
kubectl run -it --rm --restart=Never busybox --image=busybox:1.28 -- wget -O- <service-name>.<namespace>.svc.cluster.local

# 패킷 캡처
kubectl debug node/<node-name> -it --image=nicolaka/netshoot -- tcpdump -i any port 80
```

### 로깅 및 모니터링 문제 해결

#### Fluent Bit 문제 해결

```bash
# Fluent Bit 파드 상태 확인
kubectl get pods -n kube-system -l app=aws-for-fluent-bit

# Fluent Bit 로그 확인
kubectl logs -n kube-system -l app=aws-for-fluent-bit

# Fluent Bit 구성 확인
kubectl get cm -n kube-system fluent-bit-config -o yaml
```

#### Prometheus 문제 해결

```bash
# Prometheus 파드 상태 확인
kubectl get pods -n monitoring -l app=prometheus

# Prometheus 로그 확인
kubectl logs -n monitoring -l app=prometheus-server

# Prometheus 타겟 확인
kubectl port-forward -n monitoring svc/prometheus-server 9090:80
# 브라우저에서 http://localhost:9090/targets 접속
```

#### Grafana 문제 해결

```bash
# Grafana 파드 상태 확인
kubectl get pods -n monitoring -l app=grafana

# Grafana 로그 확인
kubectl logs -n monitoring -l app=grafana

# Grafana 데이터 소스 확인
kubectl port-forward -n monitoring svc/grafana 3000:80
# 브라우저에서 http://localhost:3000/datasources 접속
```

### 일반적인 문제 및 해결 방법

#### ImagePullBackOff 오류

문제: 파드가 ImagePullBackOff 상태로 멈춤

해결 방법:
1. 이미지 이름과 태그가 올바른지 확인
2. 프라이빗 레지스트리의 경우 이미지 풀 시크릿 확인
3. 노드에 인터넷 액세스 권한이 있는지 확인

```bash
# 이미지 풀 시크릿 생성
kubectl create secret docker-registry regcred \
  --docker-server=<registry-server> \
  --docker-username=<username> \
  --docker-password=<password> \
  --docker-email=<email>

# 파드에 시크릿 적용
kubectl patch serviceaccount default -p '{"imagePullSecrets": [{"name": "regcred"}]}'
```

#### CrashLoopBackOff 오류

문제: 파드가 CrashLoopBackOff 상태로 반복적으로 재시작

해결 방법:
1. 파드 로그 확인
2. 리소스 제한 확인
3. 애플리케이션 구성 확인

```bash
# 파드 로그 확인
kubectl logs <pod-name> -n <namespace>

# 파드 이벤트 확인
kubectl describe pod <pod-name> -n <namespace>

# 디버그 컨테이너 추가
kubectl debug <pod-name> -n <namespace> --image=busybox:1.28 --target=<container-name>
```

#### 노드 NotReady 상태

문제: 노드가 NotReady 상태로 표시됨

해결 방법:
1. 노드 상태 및 이벤트 확인
2. kubelet 로그 확인
3. 노드 리소스 사용량 확인

```bash
# 노드 상태 확인
kubectl describe node <node-name>

# SSH를 통한 노드 액세스
ssh -i ~/.ssh/my-key.pem ec2-user@<node-ip>

# kubelet 로그 확인
sudo journalctl -u kubelet

# 노드 리소스 사용량 확인
top
df -h
```

#### 서비스 연결 문제

문제: 서비스에 연결할 수 없음

해결 방법:
1. 서비스 및 엔드포인트 확인
2. 파드 레이블 및 선택기 확인
3. 네트워크 정책 확인

```bash
# 서비스 및 엔드포인트 확인
kubectl get svc <service-name> -n <namespace>
kubectl get endpoints <service-name> -n <namespace>

# 파드 레이블 확인
kubectl get pods -n <namespace> --show-labels

# 서비스 선택기 확인
kubectl get svc <service-name> -n <namespace> -o jsonpath='{.spec.selector}'

# 네트워크 정책 확인
kubectl get networkpolicies -n <namespace>
```

### 디버깅 도구

#### kubectl 디버깅 도구

```bash
# 파드 디버깅
kubectl debug <pod-name> -n <namespace> --image=busybox:1.28 --target=<container-name>

# 노드 디버깅
kubectl debug node/<node-name> -it --image=busybox:1.28

# 임시 디버깅 파드 생성
kubectl run debug --rm -it --image=nicolaka/netshoot -- /bin/bash
```

#### AWS CLI 디버깅 도구

```bash
# EKS 클러스터 설명
aws eks describe-cluster --name my-cluster

# EKS 노드 그룹 설명
aws eks describe-nodegroup --cluster-name my-cluster --nodegroup-name my-nodegroup

# CloudWatch Logs 쿼리
aws logs start-query \
  --log-group-name /aws/eks/my-cluster/cluster \
  --start-time $(date -u -v-1H +%s) \
  --end-time $(date -u +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /Error/'
```

#### 네트워크 디버깅 도구

```bash
# 네트워크 디버깅 파드 생성
kubectl run netshoot --rm -it --image=nicolaka/netshoot -- /bin/bash

# 네트워크 연결 테스트
nc -zv <service-name> <port>
curl -v <service-name>:<port>

# DNS 확인
dig <service-name>.<namespace>.svc.cluster.local

# 패킷 캡처
tcpdump -i any port <port> -w capture.pcap
```

## 결론

이 문서에서는 Amazon EKS 클러스터의 모니터링 및 로깅을 위한 다양한 도구, 기술 및 모범 사례를 살펴보았습니다. 효과적인 모니터링 및 로깅 전략을 구현하면 클러스터의 상태를 지속적으로 파악하고, 문제를 조기에 감지하며, 문제가 발생했을 때 신속하게 대응할 수 있습니다.

주요 내용:

1. **모니터링 및 로깅 개요**: 모니터링과 로깅의 중요성 및 아키텍처
2. **EKS 컨트롤 플레인 로깅**: 컨트롤 플레인 로그 유형 및 활성화 방법
3. **컨테이너 로깅**: Fluent Bit, CloudWatch Container Insights를 사용한 컨테이너 로그 수집
4. **클러스터 모니터링**: CloudWatch, Prometheus, Grafana를 사용한 클러스터 모니터링
5. **알림 및 이벤트 관리**: CloudWatch 경보, Prometheus Alertmanager를 사용한 알림 구성
6. **로그 분석 및 시각화**: CloudWatch Logs Insights, OpenSearch, Grafana Loki를 사용한 로그 분석
7. **모니터링 및 로깅 모범 사례**: 효과적인 모니터링 및 로깅을 위한 모범 사례
8. **문제 해결 및 디버깅**: 일반적인 문제 및 해결 방법

EKS 클러스터의 모니터링 및 로깅은 지속적인 프로세스로, 클러스터 및 애플리케이션의 요구사항에 맞게 지속적으로 개선해야 합니다.

## 참고 자료

- [Amazon EKS 모니터링 모범 사례](https://aws.github.io/aws-eks-best-practices/observability/monitoring/)
- [Amazon EKS 로깅 모범 사례](https://aws.github.io/aws-eks-best-practices/observability/logging/)
- [Kubernetes 모니터링 아키텍처](https://kubernetes.io/docs/tasks/debug-application-cluster/resource-usage-monitoring/)
- [Prometheus 문서](https://prometheus.io/docs/introduction/overview/)
- [Grafana 문서](https://grafana.com/docs/grafana/latest/)
- [Fluent Bit 문서](https://docs.fluentbit.io/manual/)
- [Amazon CloudWatch 문서](https://docs.aws.amazon.com/cloudwatch/)
- [Amazon OpenSearch Service 문서](https://docs.aws.amazon.com/opensearch-service/)
