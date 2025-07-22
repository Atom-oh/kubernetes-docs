# Amazon EKS 모니터링 및 로깅 퀴즈

이 퀴즈는 Amazon EKS의 모니터링 및 로깅 기능, 도구, 모범 사례에 대한 이해를 테스트합니다.

## 퀴즈 개요
- EKS 클러스터 모니터링
- 컨테이너 및 애플리케이션 로깅
- 성능 메트릭 수집 및 분석
- 알림 및 이상 탐지
- 모니터링 및 로깅 아키텍처
- 모범 사례 및 도구

## 객관식 문제

### 1. Amazon EKS 클러스터에서 포괄적인 모니터링 솔루션을 구축하기 위한 가장 효과적인 접근 방식은 무엇인가요?

A. CloudWatch만 사용  
B. Prometheus와 Grafana만 사용  
C. CloudWatch, Prometheus, Grafana 및 X-Ray의 통합 사용  
D. 사용자 지정 모니터링 스크립트 작성  

<details>
<summary>정답 및 설명</summary>

**정답: C. CloudWatch, Prometheus, Grafana 및 X-Ray의 통합 사용**

**설명:**
Amazon EKS 클러스터에서 포괄적인 모니터링 솔루션을 구축하기 위한 가장 효과적인 접근 방식은 CloudWatch, Prometheus, Grafana 및 X-Ray를 통합하여 사용하는 것입니다. 이 통합 접근 방식은 인프라, 클러스터, 애플리케이션 및 분산 추적 수준에서 완전한 가시성을 제공합니다.

**통합 모니터링 솔루션의 주요 이점:**

1. **다중 계층 모니터링**:
   - AWS 인프라 수준 메트릭 (CloudWatch)
   - Kubernetes 클러스터 수준 메트릭 (Prometheus)
   - 애플리케이션 수준 메트릭 (CloudWatch, Prometheus)
   - 분산 추적 (X-Ray)

2. **포괄적인 데이터 수집**:
   - 시스템 메트릭 (CPU, 메모리, 디스크, 네트워크)
   - Kubernetes 리소스 메트릭 (파드, 노드, 컨트롤러)
   - 사용자 정의 애플리케이션 메트릭
   - 분산 서비스 간 트랜잭션 추적

3. **유연한 시각화 및 분석**:
   - 사전 구성된 대시보드 (CloudWatch, Grafana)
   - 사용자 정의 대시보드 (Grafana)
   - 고급 쿼리 및 알림 (PromQL, CloudWatch Alarms)
   - 서비스 맵 및 트레이스 분석 (X-Ray)

**구현 방법:**

1. **CloudWatch Container Insights 설정**:
   ```bash
   # CloudWatch 에이전트 설치
   kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluentd-quickstart.yaml
   ```

2. **Prometheus 및 Grafana 설치**:
   ```bash
   # Prometheus 네임스페이스 생성
   kubectl create namespace prometheus

   # Helm을 사용하여 Prometheus 설치
   helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   helm install prometheus prometheus-community/prometheus \
     --namespace prometheus \
     --set alertmanager.persistentVolume.storageClass="gp2" \
     --set server.persistentVolume.storageClass="gp2"

   # Grafana 설치
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

3. **AWS Distro for OpenTelemetry(ADOT) 및 X-Ray 설정**:
   ```bash
   # ADOT 연산자 설치
   kubectl apply -f https://github.com/aws-observability/aws-otel-collector/releases/latest/download/opentelemetry-operator.yaml

   # X-Ray와 통합된 ADOT 수집기 구성
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

4. **CloudWatch와 Prometheus 통합**:
   ```bash
   # Amazon Managed Prometheus 워크스페이스 생성
   aws amp create-workspace --alias eks-monitoring

   # CloudWatch 에이전트 구성
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

**주요 모니터링 구성 요소:**

1. **CloudWatch Container Insights**:
   - 클러스터, 노드, 파드 수준 메트릭
   - 컨테이너 로그 수집
   - 자동 대시보드 및 알림

2. **Prometheus 및 Grafana**:
   - 세분화된 Kubernetes 메트릭
   - 사용자 정의 메트릭 및 대시보드
   - 고급 쿼리 및 알림

3. **AWS X-Ray**:
   - 분산 추적
   - 서비스 맵
   - 요청 경로 분석

4. **AWS Distro for OpenTelemetry**:
   - 표준화된 텔레메트리 수집
   - 다양한 백엔드 지원
   - 벤더 중립적 계측

**모범 사례:**

1. **계층화된 모니터링 전략 구현**:
   - 인프라 수준: 노드, 네트워크, 스토리지
   - 클러스터 수준: 컨트롤 플레인, 노드, 파드
   - 애플리케이션 수준: 서비스, 엔드포인트, 비즈니스 메트릭

2. **효과적인 알림 전략 수립**:
   - 중요도 기반 알림 설정
   - 알림 피로 방지
   - 에스컬레이션 경로 정의

3. **자동화된 대응 구현**:
   - 자동 스케일링 트리거
   - 자가 복구 메커니즘
   - 사전 예방적 유지 관리

4. **비용 최적화**:
   - 필요한 메트릭만 수집
   - 적절한 샘플링 및 집계
   - 데이터 보존 정책 최적화

**실제 구현 예시:**

1. **종합 모니터링 아키텍처**:
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

2. **Terraform을 사용한 모니터링 인프라 구성**:
   ```hcl
   # Amazon Managed Prometheus 워크스페이스
   resource "aws_prometheus_workspace" "eks_monitoring" {
     alias = "eks-monitoring"
   }
   
   # Amazon Managed Grafana 워크스페이스
   resource "aws_grafana_workspace" "eks_monitoring" {
     name                     = "eks-monitoring"
     account_access_type      = "CURRENT_ACCOUNT"
     authentication_providers = ["AWS_SSO"]
     permission_type          = "SERVICE_MANAGED"
     data_sources             = ["PROMETHEUS", "CLOUDWATCH", "XRAY"]
   }
   
   # CloudWatch 로그 그룹
   resource "aws_cloudwatch_log_group" "eks_logs" {
     name              = "/aws/eks/my-cluster/logs"
     retention_in_days = 30
   }
   ```

다른 옵션들의 문제점:
- **A. CloudWatch만 사용**: CloudWatch는 AWS 인프라 및 기본 컨테이너 메트릭을 제공하지만, Kubernetes 특화 메트릭이나 세분화된 애플리케이션 수준 모니터링에 제한이 있습니다.
- **B. Prometheus와 Grafana만 사용**: 이 조합은 강력한 Kubernetes 모니터링을 제공하지만, AWS 서비스와의 통합이나 분산 추적 기능이 부족합니다.
- **D. 사용자 지정 모니터링 스크립트 작성**: 사용자 지정 스크립트는 유지 관리가 어렵고, 확장성이 떨어지며, 업계 표준 도구의 풍부한 기능을 활용하지 못합니다.
</details>
### 2. Amazon EKS에서 컨테이너 로그를 효과적으로 수집하고 분석하기 위한 가장 좋은 방법은 무엇인가요?

A. 각 노드에서 수동으로 로그 파일 검색  
B. 컨테이너 내에서 로그 파일 직접 읽기  
C. Fluentd/Fluent Bit를 사용하여 CloudWatch Logs 또는 Elasticsearch로 로그 전송  
D. 로그를 표준 출력으로만 전송  

<details>
<summary>정답 및 설명</summary>

**정답: C. Fluentd/Fluent Bit를 사용하여 CloudWatch Logs 또는 Elasticsearch로 로그 전송**

**설명:**
Amazon EKS에서 컨테이너 로그를 효과적으로 수집하고 분석하기 위한 가장 좋은 방법은 Fluentd 또는 Fluent Bit와 같은 로그 수집기를 사용하여 CloudWatch Logs, Amazon OpenSearch Service(이전의 Elasticsearch Service) 또는 기타 로그 분석 시스템으로 로그를 전송하는 것입니다. 이 접근 방식은 확장성, 중앙 집중화, 검색 및 분석 기능을 제공합니다.

**Fluentd/Fluent Bit 기반 로깅의 주요 이점:**

1. **중앙 집중식 로그 관리**:
   - 모든 컨테이너 로그를 단일 위치에 수집
   - 클러스터 전체 로그 검색 및 분석
   - 장기 로그 보존 및 아카이빙

2. **확장성 및 신뢰성**:
   - 대규모 클러스터 지원
   - 버퍼링 및 재시도 메커니즘
   - 로그 손실 최소화

3. **유연한 로그 처리**:
   - 로그 필터링 및 변환
   - 구조화된 로깅 지원
   - 다양한 출력 대상 지원

4. **통합 분석 및 시각화**:
   - CloudWatch Logs Insights
   - OpenSearch Dashboards(이전의 Kibana)
   - 고급 검색 및 쿼리

**구현 방법:**

1. **Fluent Bit를 사용한 CloudWatch Logs 통합**:
   ```bash
   # Fluent Bit 네임스페이스 생성
   kubectl create namespace amazon-cloudwatch

   # AWS for Fluent Bit 설치
   kubectl apply -f https://raw.githubusercontent.com/aws/aws-for-fluent-bit/master/eks/cloudwatch-namespace.yaml
   kubectl apply -f https://raw.githubusercontent.com/aws/aws-for-fluent-bit/master/eks/fluent-bit-service-account.yaml
   kubectl apply -f https://raw.githubusercontent.com/aws/aws-for-fluent-bit/master/eks/fluent-bit-role.yaml
   kubectl apply -f https://raw.githubusercontent.com/aws/aws-for-fluent-bit/master/eks/fluent-bit-role-binding.yaml
   
   # Fluent Bit ConfigMap 및 DaemonSet 배포
   kubectl apply -f https://raw.githubusercontent.com/aws/aws-for-fluent-bit/master/eks/fluent-bit-configmap.yaml
   kubectl apply -f https://raw.githubusercontent.com/aws/aws-for-fluent-bit/master/eks/fluent-bit-ds.yaml
   ```

2. **Fluentd를 사용한 Amazon OpenSearch Service 통합**:
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

3. **AWS Distro for OpenTelemetry(ADOT)를 사용한 로그 수집**:
   ```yaml
   # ADOT 수집기 구성
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

**로그 수집 및 분석 모범 사례:**

1. **구조화된 로깅 구현**:
   - JSON 형식 로그 사용
   - 일관된 로그 필드 및 형식
   - 상관 관계 ID 포함

2. **로그 수준 최적화**:
   - 적절한 로그 수준 설정
   - 프로덕션에서 디버그 로그 최소화
   - 중요 이벤트에 대한 충분한 컨텍스트 제공

3. **로그 보존 및 아카이빙 전략**:
   - 비용과 규정 준수 요구 사항 균형
   - 계층화된 스토리지 사용
   - 자동 아카이빙 구성

4. **로그 보안 고려 사항**:
   - 민감한 정보 필터링
   - 로그 액세스 제어
   - 로그 무결성 보장

**실제 구현 예시:**

1. **다중 출력 대상을 가진 Fluent Bit 구성**:
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

2. **로그 분석을 위한 CloudWatch Logs Insights 쿼리**:
   ```
   fields @timestamp, @message, kubernetes.pod_name, kubernetes.namespace_name, log
   | filter kubernetes.namespace_name = "production"
   | filter @message like /ERROR/
   | sort @timestamp desc
   | limit 100
   ```

3. **Terraform을 사용한 로깅 인프라 구성**:
   ```hcl
   # CloudWatch 로그 그룹
   resource "aws_cloudwatch_log_group" "eks_logs" {
     name              = "/aws/eks/my-cluster/logs"
     retention_in_days = 30
     tags = {
       Environment = "production"
       Application = "eks-cluster"
     }
   }
   
   # OpenSearch 도메인
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

다른 옵션들의 문제점:
- **A. 각 노드에서 수동으로 로그 파일 검색**: 확장성이 떨어지고, 자동화되지 않으며, 노드 장애 시 로그가 손실될 수 있습니다.
- **B. 컨테이너 내에서 로그 파일 직접 읽기**: 컨테이너가 종료되면 로그에 액세스할 수 없으며, 중앙 집중식 분석이 어렵습니다.
- **D. 로그를 표준 출력으로만 전송**: 표준 출력으로 로그를 전송하는 것은 좋은 관행이지만, 이러한 로그를 수집하고 중앙 집중화하는 메커니즘이 없으면 효과적인 분석이 어렵습니다.
</details>
### 3. Amazon EKS에서 효과적인 알림 시스템을 구축하기 위한 가장 좋은 접근 방식은 무엇인가요?

A. 로그 파일을 수동으로 검토  
B. CloudWatch 알람만 사용  
C. Prometheus AlertManager만 사용  
D. CloudWatch 알람, Prometheus AlertManager 및 EventBridge를 통합하여 다양한 알림 채널 지원  

<details>
<summary>정답 및 설명</summary>

**정답: D. CloudWatch 알람, Prometheus AlertManager 및 EventBridge를 통합하여 다양한 알림 채널 지원**

**설명:**
Amazon EKS에서 효과적인 알림 시스템을 구축하기 위한 가장 좋은 접근 방식은 CloudWatch 알람, Prometheus AlertManager 및 EventBridge를 통합하여 다양한 알림 채널을 지원하는 것입니다. 이 통합 접근 방식은 인프라, 클러스터 및 애플리케이션 수준에서 포괄적인 알림을 제공하고 다양한 알림 채널과 대응 메커니즘을 지원합니다.

**통합 알림 시스템의 주요 이점:**

1. **다중 계층 알림**:
   - AWS 인프라 수준 알림 (CloudWatch)
   - Kubernetes 클러스터 수준 알림 (Prometheus)
   - 애플리케이션 수준 알림 (사용자 정의 메트릭)
   - 이벤트 기반 알림 (EventBridge)

2. **다양한 알림 채널 지원**:
   - 이메일, SMS (SNS)
   - Slack, Microsoft Teams (웹훅)
   - PagerDuty, OpsGenie (인시던트 관리)
   - 사용자 정의 Lambda 함수

3. **지능적인 알림 관리**:
   - 알림 그룹화 및 중복 제거
   - 알림 라우팅 및 에스컬레이션
   - 알림 억제 및 사일런싱

**구현 방법:**

1. **CloudWatch 알람 설정**:
   ```bash
   # 노드 CPU 사용량에 대한 CloudWatch 알람 생성
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

2. **Prometheus AlertManager 구성**:
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

3. **Prometheus 알림 규칙 정의**:
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

4. **EventBridge 규칙 설정**:
   ```bash
   # EKS 이벤트에 대한 EventBridge 규칙 생성
   aws events put-rule \
     --name EKS-Control-Plane-Events \
     --event-pattern '{"source":["aws.eks"],"detail-type":["EKS Cluster Control Plane Health"]}'
   
   # SNS 주제를 대상으로 설정
   aws events put-targets \
     --rule EKS-Control-Plane-Events \
     --targets 'Id"="1","Arn"="arn:aws:sns:us-west-2:123456789012:eks-alerts"'
   ```

**알림 통합 및 라우팅:**

1. **SNS 주제를 통한 알림 통합**:
   ```bash
   # SNS 주제 생성
   aws sns create-topic --name eks-alerts
   
   # 이메일 구독 추가
   aws sns subscribe \
     --topic-arn arn:aws:sns:us-west-2:123456789012:eks-alerts \
     --protocol email \
     --notification-endpoint ops-team@example.com
   
   # Lambda 구독 추가
   aws sns subscribe \
     --topic-arn arn:aws:sns:us-west-2:123456789012:eks-alerts \
     --protocol lambda \
     --notification-endpoint arn:aws:lambda:us-west-2:123456789012:function:process-eks-alerts
   ```

2. **Lambda를 사용한 알림 처리 및 라우팅**:
   ```python
   import json
   import boto3
   import requests
   
   def lambda_handler(event, context):
       message = json.loads(event['Records'][0]['Sns']['Message'])
       
       # 알림 심각도에 따라 다른 채널로 라우팅
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
       # PagerDuty API 호출 구현
       pass
   
   def send_to_slack(message, channel):
       # Slack 웹훅 호출 구현
       pass
   ```

**알림 모범 사례:**

1. **알림 피로 방지**:
   - 중요한 알림에만 집중
   - 알림 그룹화 및 중복 제거
   - 알림 빈도 제한

2. **명확한 알림 내용 제공**:
   - 문제 설명 및 영향
   - 문제 해결을 위한 권장 조치
   - 관련 리소스 및 컨텍스트

3. **알림 우선순위 및 에스컬레이션**:
   - 심각도 기반 알림 분류
   - 명확한 에스컬레이션 경로
   - 응답 시간 목표 설정

4. **알림 테스트 및 검증**:
   - 정기적인 알림 테스트
   - 가짜 양성 및 음성 모니터링
   - 알림 효과성 검토

**실제 구현 예시:**

1. **종합 알림 아키텍처**:
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

2. **Terraform을 사용한 알림 인프라 구성**:
   ```hcl
   # SNS 주제
   resource "aws_sns_topic" "eks_alerts" {
     name = "eks-alerts"
   }
   
   # CloudWatch 알람
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
   
   # EventBridge 규칙
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

다른 옵션들의 문제점:
- **A. 로그 파일을 수동으로 검토**: 수동 검토는 확장성이 떨어지고, 실시간 알림을 제공하지 않으며, 자동화된 대응을 지원하지 않습니다.
- **B. CloudWatch 알람만 사용**: CloudWatch 알람은 AWS 인프라 수준의 알림에 유용하지만, Kubernetes 특화 메트릭이나 애플리케이션 수준의 세부적인 알림에 제한이 있습니다.
- **C. Prometheus AlertManager만 사용**: Prometheus AlertManager는 Kubernetes 메트릭에 대한 강력한 알림을 제공하지만, AWS 서비스 이벤트나 인프라 수준의 알림과의 통합이 제한적입니다.
</details>
### 4. Amazon EKS에서 애플리케이션 성능 모니터링을 위한 가장 효과적인 접근 방식은 무엇인가요?

A. 기본 시스템 메트릭만 모니터링  
B. 사용자 정의 애플리케이션 메트릭 수집 및 분석  
C. 분산 추적, 메트릭, 로그를 포함한 통합 관찰성 구현  
D. 주기적인 수동 성능 테스트 수행  

<details>
<summary>정답 및 설명</summary>

**정답: C. 분산 추적, 메트릭, 로그를 포함한 통합 관찰성 구현**

**설명:**
Amazon EKS에서 애플리케이션 성능 모니터링을 위한 가장 효과적인 접근 방식은 분산 추적, 메트릭, 로그를 포함한 통합 관찰성을 구현하는 것입니다. 이 포괄적인 접근 방식은 애플리케이션 성능에 대한 완전한 가시성을 제공하고, 문제 해결 및 최적화를 위한 상세한 정보를 제공합니다.

**통합 관찰성의 주요 구성 요소:**

1. **분산 추적(Distributed Tracing)**:
   - 서비스 간 요청 흐름 추적
   - 지연 시간 병목 현상 식별
   - 오류 전파 경로 파악

2. **메트릭(Metrics)**:
   - 시스템 및 리소스 사용량
   - 애플리케이션 성능 지표
   - 비즈니스 메트릭

3. **로그(Logs)**:
   - 상세한 애플리케이션 이벤트
   - 오류 및 예외 정보
   - 디버깅 컨텍스트

4. **프로파일링(Profiling)**:
   - CPU 및 메모리 사용량 분석
   - 핫스팟 및 병목 현상 식별
   - 코드 수준 최적화 기회 발견

**구현 방법:**

1. **AWS Distro for OpenTelemetry(ADOT) 설정**:
   ```bash
   # ADOT 연산자 설치
   kubectl apply -f https://github.com/aws-observability/aws-otel-collector/releases/latest/download/opentelemetry-operator.yaml

   # ADOT 수집기 구성
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

2. **애플리케이션 계측**:
   ```java
   // Java 애플리케이션 예시 (Spring Boot)
   
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
   # Python 애플리케이션 예시
   from opentelemetry import trace
   from opentelemetry.sdk.trace import TracerProvider
   from opentelemetry.sdk.trace.export import BatchSpanProcessor
   from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
   from opentelemetry.sdk.resources import SERVICE_NAME, Resource
   
   # 리소스 및 트레이서 설정
   resource = Resource(attributes={
       SERVICE_NAME: "payment-service"
   })
   
   tracer_provider = TracerProvider(resource=resource)
   processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="adot-collector:4317"))
   tracer_provider.add_span_processor(processor)
   trace.set_tracer_provider(tracer_provider)
   
   # 트레이서 사용
   tracer = trace.get_tracer(__name__)
   
   @app.route('/process-payment', methods=['POST'])
   def process_payment():
       with tracer.start_as_current_span("process-payment") as span:
           span.set_attribute("payment.amount", request.json.get('amount'))
           # 비즈니스 로직 수행
           result = process_transaction(request.json)
           span.set_attribute("payment.status", result['status'])
           return jsonify(result)
   ```

3. **Amazon Managed Grafana 대시보드 설정**:
   ```bash
   # Amazon Managed Grafana 워크스페이스 생성
   aws grafana create-workspace \
     --name eks-monitoring \
     --authentication-providers AWS_SSO \
     --permission-type SERVICE_MANAGED \
     --data-sources PROMETHEUS CLOUDWATCH XRAY
   ```

4. **X-Ray 서비스 맵 및 추적 분석**:
   ```bash
   # X-Ray 그룹 생성
   aws xray create-group \
     --group-name "EKS-Applications" \
     --filter-expression "service(\"order-service\") OR service(\"payment-service\")"
   ```

**주요 관찰성 지표 및 차원:**

1. **핵심 애플리케이션 성능 지표**:
   - 요청 지연 시간 (p50, p90, p99)
   - 요청 처리량 (RPS)
   - 오류율
   - 포화도 (리소스 사용률)

2. **중요 차원 및 레이블**:
   - 서비스 및 엔드포인트
   - 클러스터, 네임스페이스, 파드
   - 버전 및 환경
   - 고객 또는 테넌트 ID

3. **사용자 경험 지표**:
   - 페이지 로드 시간
   - API 응답 시간
   - 사용자 상호 작용 지연 시간
   - 클라이언트 오류율

**모범 사례:**

1. **표준화된 계측 구현**:
   - OpenTelemetry와 같은 표준 사용
   - 일관된 명명 규칙 및 레이블
   - 자동 및 수동 계측 결합

2. **컨텍스트 전파 보장**:
   - 서비스 간 추적 컨텍스트 전달
   - 비동기 작업에서 컨텍스트 유지
   - 외부 시스템과의 통합

3. **샘플링 전략 최적화**:
   - 비용과 가시성 균형
   - 오류 및 지연 기반 샘플링
   - 중요 트랜잭션 우선 순위 지정

4. **관찰성 데이터 상관 관계**:
   - 추적, 메트릭, 로그 간 연결
   - 공통 식별자 및 레이블 사용
   - 통합 대시보드 및 분석

**실제 구현 예시:**

1. **마이크로서비스 아키텍처의 통합 관찰성**:
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

2. **Terraform을 사용한 관찰성 인프라 구성**:
   ```hcl
   # Amazon Managed Service for Prometheus 워크스페이스
   resource "aws_prometheus_workspace" "eks_monitoring" {
     alias = "eks-monitoring"
   }
   
   # Amazon Managed Grafana 워크스페이스
   resource "aws_grafana_workspace" "eks_monitoring" {
     name                     = "eks-monitoring"
     account_access_type      = "CURRENT_ACCOUNT"
     authentication_providers = ["AWS_SSO"]
     permission_type          = "SERVICE_MANAGED"
     data_sources             = ["PROMETHEUS", "CLOUDWATCH", "XRAY"]
   }
   
   # X-Ray 그룹
   resource "aws_xray_group" "eks_applications" {
     group_name        = "EKS-Applications"
     filter_expression = "service(\"order-service\") OR service(\"payment-service\")"
   }
   
   # CloudWatch 로그 그룹
   resource "aws_cloudwatch_log_group" "application_logs" {
     name              = "/aws/eks/my-cluster/application-logs"
     retention_in_days = 30
   }
   
   # IAM 역할 및 정책
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

다른 옵션들의 문제점:
- **A. 기본 시스템 메트릭만 모니터링**: 시스템 메트릭은 인프라 상태를 이해하는 데 중요하지만, 애플리케이션 성능 문제의 근본 원인을 식별하기에는 충분하지 않습니다.
- **B. 사용자 정의 애플리케이션 메트릭 수집 및 분석**: 애플리케이션 메트릭은 중요하지만, 분산 시스템에서 서비스 간 상호 작용을 이해하기 위해서는 추적과 로그도 필요합니다.
- **D. 주기적인 수동 성능 테스트 수행**: 성능 테스트는 중요하지만, 실시간 프로덕션 환경에서의 지속적인 모니터링을 대체할 수 없으며, 실제 사용자 패턴을 완전히 시뮬레이션하기 어렵습니다.
</details>
### 5. Amazon EKS에서 컨트롤 플레인 로그를 효과적으로 모니터링하기 위한 가장 좋은 방법은 무엇인가요?

A. SSH를 통해 컨트롤 플레인 노드에 직접 액세스  
B. EKS 컨트롤 플레인 로깅을 활성화하고 CloudWatch Logs로 전송  
C. 사용자 지정 로그 수집기 배포  
D. 주기적으로 AWS 지원팀에 로그 요청  

<details>
<summary>정답 및 설명</summary>

**정답: B. EKS 컨트롤 플레인 로깅을 활성화하고 CloudWatch Logs로 전송**

**설명:**
Amazon EKS에서 컨트롤 플레인 로그를 효과적으로 모니터링하기 위한 가장 좋은 방법은 EKS 컨트롤 플레인 로깅을 활성화하고 CloudWatch Logs로 전송하는 것입니다. 이 방법은 관리형 서비스로서 EKS의 특성을 활용하여 컨트롤 플레인 구성 요소의 로그에 쉽게 액세스하고 분석할 수 있게 해줍니다.

**EKS 컨트롤 플레인 로깅의 주요 이점:**

1. **포괄적인 로그 수집**:
   - API 서버 로그
   - 감사 로그
   - 인증자 로그
   - 컨트롤러 관리자 로그
   - 스케줄러 로그

2. **관리형 솔루션**:
   - AWS에서 관리하는 로그 수집
   - 추가 에이전트 불필요
   - 컨트롤 플레인에 직접 액세스 불필요

3. **통합 분석 및 알림**:
   - CloudWatch Logs Insights를 통한 쿼리 및 분석
   - CloudWatch 알람과의 통합
   - 장기 로그 보존 및 아카이빙

**구현 방법:**

1. **EKS 클러스터 생성 시 로깅 활성화**:
   ```bash
   # 모든 로그 유형이 활성화된 EKS 클러스터 생성
   aws eks create-cluster \
     --name my-cluster \
     --role-arn arn:aws:iam::123456789012:role/EKSClusterRole \
     --resources-vpc-config subnetIds=subnet-12345,subnet-67890,securityGroupIds=sg-12345 \
     --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
   ```

2. **기존 EKS 클러스터에 로깅 활성화**:
   ```bash
   # 기존 클러스터에 모든 로그 유형 활성화
   aws eks update-cluster-config \
     --name my-cluster \
     --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
   ```

3. **특정 로그 유형만 활성화**:
   ```bash
   # API 서버 및 감사 로그만 활성화
   aws eks update-cluster-config \
     --name my-cluster \
     --logging '{"clusterLogging":[{"types":["api","audit"],"enabled":true},{"types":["authenticator","controllerManager","scheduler"],"enabled":false}]}'
   ```

**주요 로그 유형 및 용도:**

1. **API 서버 로그 (api)**:
   - API 요청 및 응답
   - 리소스 생성, 수정, 삭제
   - 오류 및 경고 메시지

2. **감사 로그 (audit)**:
   - 모든 API 호출의 상세 기록
   - 누가, 무엇을, 언제, 어디서 수행했는지 추적
   - 보안 및 규정 준수 요구 사항 충족

3. **인증자 로그 (authenticator)**:
   - AWS IAM 인증 정보를 사용한 인증 요청
   - 인증 성공 및 실패
   - 권한 문제 디버깅

4. **컨트롤러 관리자 로그 (controllerManager)**:
   - 컨트롤러 작업 및 상태
   - 리소스 조정 활동
   - 컨트롤러 오류 및 재시도

5. **스케줄러 로그 (scheduler)**:
   - 파드 스케줄링 결정
   - 스케줄링 실패 및 이유
   - 리소스 할당 문제

**로그 분석 및 모니터링:**

1. **CloudWatch Logs Insights를 사용한 쿼리**:
   ```
   # API 서버 오류 검색
   fields @timestamp, @message
   | filter @logStream like /kube-apiserver-/
   | filter @message like /Error/
   | sort @timestamp desc
   | limit 100
   
   # 특정 사용자의 감사 로그 검색
   fields @timestamp, @message
   | filter @logStream like /kube-apiserver-audit/
   | parse @message "user.username*:*" as user_prefix, username
   | filter username like /admin/
   | sort @timestamp desc
   | limit 100
   
   # 인증 실패 검색
   fields @timestamp, @message
   | filter @logStream like /authenticator/
   | filter @message like /failed/
   | sort @timestamp desc
   | limit 100
   ```

2. **CloudWatch 대시보드 생성**:
   ```bash
   # API 서버 오류율을 모니터링하는 대시보드 생성
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

3. **CloudWatch 알람 설정**:
   ```bash
   # API 서버 오류 알람 생성
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

**모범 사례:**

1. **선택적 로그 활성화**:
   - 필요한 로그 유형만 활성화
   - 감사 로그는 규정 준수 요구 사항에 따라 활성화
   - 비용과 가시성 균형 유지

2. **로그 보존 정책 설정**:
   ```bash
   # CloudWatch 로그 그룹 보존 기간 설정
   aws logs put-retention-policy \
     --log-group-name /aws/eks/my-cluster/cluster \
     --retention-in-days 90
   ```

3. **로그 암호화 구성**:
   ```bash
   # CloudWatch 로그 그룹 암호화 설정
   aws logs associate-kms-key \
     --log-group-name /aws/eks/my-cluster/cluster \
     --kms-key-id arn:aws:kms:us-west-2:123456789012:key/1234abcd-12ab-34cd-56ef-1234567890ab
   ```

4. **로그 액세스 제어**:
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

**실제 구현 예시:**

1. **Terraform을 사용한 EKS 클러스터 로깅 구성**:
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

2. **CloudWatch Logs Insights 대시보드**:
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

다른 옵션들의 문제점:
- **A. SSH를 통해 컨트롤 플레인 노드에 직접 액세스**: EKS는 관리형 서비스로, 컨트롤 플레인 노드에 직접 액세스할 수 없습니다.
- **C. 사용자 지정 로그 수집기 배포**: 컨트롤 플레인은 AWS에서 관리하므로, 사용자 지정 로그 수집기를 배포해도 컨트롤 플레인 로그에 액세스할 수 없습니다.
- **D. 주기적으로 AWS 지원팀에 로그 요청**: 비효율적이고 실시간 모니터링이 불가능하며, 자동화된 분석 및 알림을 제공하지 않습니다.
</details>
### 6. Amazon EKS에서 비용 최적화를 위한 모니터링 전략으로 가장 효과적인 것은 무엇인가요?

A. 모든 가능한 메트릭 수집  
B. 리소스 사용량, 비용 할당 태그 및 유휴 리소스에 초점을 맞춘 모니터링  
C. 비용 모니터링 없이 성능에만 집중  
D. 월별 AWS 청구서만 검토  

<details>
<summary>정답 및 설명</summary>

**정답: B. 리소스 사용량, 비용 할당 태그 및 유휴 리소스에 초점을 맞춘 모니터링**

**설명:**
Amazon EKS에서 비용 최적화를 위한 가장 효과적인 모니터링 전략은 리소스 사용량, 비용 할당 태그 및 유휴 리소스에 초점을 맞춘 모니터링입니다. 이 접근 방식은 클러스터 리소스의 효율적인 사용을 보장하고, 비용 할당을 명확히 하며, 낭비되는 리소스를 식별하여 비용을 최적화합니다.

**비용 최적화 모니터링의 주요 구성 요소:**

1. **리소스 사용량 모니터링**:
   - CPU, 메모리, 스토리지 사용률
   - 실제 사용량 대비 요청 및 제한
   - 리소스 사용 추세 및 패턴

2. **비용 할당 및 태깅**:
   - 네임스페이스, 서비스, 팀별 비용 분석
   - 비용 할당 태그 구현 및 모니터링
   - 비용 센터 및 프로젝트별 지출 추적

3. **유휴 및 낭비되는 리소스 식별**:
   - 사용되지 않는 EBS 볼륨
   - 과도하게 프로비저닝된 리소스
   - 유휴 노드 및 파드

4. **비용 이상 탐지**:
   - 예상치 못한 비용 증가 알림
   - 비용 추세 분석
   - 예산 대비 실제 지출 모니터링

**구현 방법:**

1. **Kubernetes 리소스 사용량 모니터링**:
   ```yaml
   # Prometheus를 사용한 리소스 사용량 모니터링
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

2. **비용 할당 태그 구현**:
   ```bash
   # 비용 할당 태그 활성화
   aws ce update-cost-allocation-tags-status \
     --cost-allocation-tags-status '[{"TagKey": "kubernetes.io/cluster/my-cluster", "Status": "Active"}, {"TagKey": "kubernetes.io/namespace", "Status": "Active"}, {"TagKey": "app", "Status": "Active"}, {"TagKey": "team", "Status": "Active"}]'
   
   # 노드에 태그 지정
   aws ec2 create-tags \
     --resources i-1234567890abcdef0 \
     --tags Key=team,Value=platform Key=environment,Value=production
   ```

3. **Kubecost 배포**:
   ```bash
   # Helm을 사용하여 Kubecost 설치
   helm repo add kubecost https://kubecost.github.io/cost-analyzer/
   helm install kubecost kubecost/cost-analyzer \
     --namespace kubecost \
     --create-namespace \
     --set kubecostToken="<YOUR_KUBECOST_TOKEN>" \
     --set prometheus.server.persistentVolume.size=100Gi \
     --set prometheus.nodeExporter.enabled=true \
     --set serviceMonitor.enabled=true
   ```

4. **AWS Cost Explorer 대시보드 설정**:
   ```bash
   # AWS Cost Explorer 대시보드 생성
   aws ce create-cost-category \
     --name EKS-Clusters \
     --rule-version "CostCategoryExpression.v1" \
     --rules '[{"Value": "my-cluster-prod", "Rule": {"Tags": {"Key": "kubernetes.io/cluster/my-cluster-prod", "Values": ["owned", "shared"], "MatchOptions": ["EQUALS"]}}}, {"Value": "my-cluster-dev", "Rule": {"Tags": {"Key": "kubernetes.io/cluster/my-cluster-dev", "Values": ["owned", "shared"], "MatchOptions": ["EQUALS"]}}}]'
   ```

**주요 모니터링 메트릭 및 차원:**

1. **리소스 효율성 메트릭**:
   - CPU 사용률 = 사용된 CPU / 요청된 CPU
   - 메모리 사용률 = 사용된 메모리 / 요청된 메모리
   - 리소스 요청 vs 제한 비율

2. **비용 할당 차원**:
   - 클러스터
   - 네임스페이스
   - 배포/스테이트풀셋
   - 레이블 (팀, 애플리케이션, 환경)

3. **낭비 식별 메트릭**:
   - 유휴 파드 수 (CPU/메모리 사용률 < 5%)
   - 연결되지 않은 EBS 볼륨
   - 사용되지 않는 로드 밸런서

**모범 사례:**

1. **리소스 요청 및 제한 최적화**:
   - 실제 사용량 기반 리소스 요청 설정
   - Vertical Pod Autoscaler 활용
   - 정기적인 리소스 요청 검토

2. **효과적인 태깅 전략 구현**:
   ```yaml
   # 네임스페이스 레이블 예시
   apiVersion: v1
   kind: Namespace
   metadata:
     name: team-a
     labels:
       team: team-a
       cost-center: cc-123
       environment: production
   ```

3. **자동 스케일링 최적화**:
   - Cluster Autoscaler 구성 조정
   - Karpenter 활용
   - 스팟 인스턴스 활용

4. **정기적인 비용 검토 및 최적화**:
   - 주간/월간 비용 검토 회의
   - 비용 절감 목표 설정
   - 최적화 조치 추적

**실제 구현 예시:**

1. **Grafana 비용 대시보드**:
   ```bash
   # Grafana 대시보드 가져오기
   kubectl -n monitoring create configmap cost-dashboard \
     --from-file=cost-dashboard.json
   ```

2. **리소스 요청 vs 사용량 모니터링 쿼리**:
   ```
   # Prometheus 쿼리 예시
   # CPU 요청 대비 사용률
   sum(rate(container_cpu_usage_seconds_total{namespace="production"}[5m])) by (pod) / 
   sum(kube_pod_container_resource_requests{resource="cpu", namespace="production"}) by (pod)
   
   # 메모리 요청 대비 사용률
   sum(container_memory_working_set_bytes{namespace="production"}) by (pod) / 
   sum(kube_pod_container_resource_requests{resource="memory", namespace="production"}) by (pod)
   ```

3. **비용 최적화 자동화 스크립트**:
   ```python
   # 유휴 리소스 식별 및 보고 스크립트 예시
   import boto3
   import kubernetes
   from kubernetes import client, config
   
   # Kubernetes 클라이언트 설정
   config.load_kube_config()
   v1 = client.CoreV1Api()
   
   # AWS 클라이언트 설정
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
           # 메트릭 API 또는 Prometheus에서 사용량 데이터 가져오기
           # 사용률이 낮은 파드 식별
           pass
       return underutilized
   
   # 메인 함수
   def main():
       unused_volumes = find_unused_volumes()
       underutilized_pods = find_underutilized_pods()
       
       # 보고서 생성 및 알림
       generate_report(unused_volumes, underutilized_pods)
   
   if __name__ == "__main__":
       main()
   ```

4. **Terraform을 사용한 비용 모니터링 인프라 구성**:
   ```hcl
   # AWS 예산 알림 설정
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
   
   # CloudWatch 대시보드
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

다른 옵션들의 문제점:
- **A. 모든 가능한 메트릭 수집**: 모든 메트릭을 수집하면 스토리지 비용이 증가하고, 중요한 비용 최적화 신호가 노이즈에 묻힐 수 있으며, 분석이 복잡해집니다.
- **C. 비용 모니터링 없이 성능에만 집중**: 성능은 중요하지만, 비용 최적화 없이는 불필요한 지출이 발생할 수 있습니다.
- **D. 월별 AWS 청구서만 검토**: 월별 청구서 검토는 사후 대응적이며, 세부적인 비용 할당 정보를 제공하지 않고, 실시간 최적화 기회를 놓칠 수 있습니다.
</details>
