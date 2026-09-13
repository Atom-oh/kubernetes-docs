# Amazon EKS 모니터링 및 로깅 퀴즈

> **마지막 업데이트**: 2026년 9월 12일

이 퀴즈는 Amazon EKS의 모니터링 및 로깅 기능, 도구, 모범 사례에 대한 이해를 테스트합니다.

## 퀴즈 개요
- EKS 클러스터 모니터링
- 컨테이너 및 애플리케이션 로깅
- 성능 메트릭 수집 및 분석
- 알림 및 이상 탐지
- 모니터링 및 로깅 아키텍처
- 모범 사례 및 도구

## 객관식 문제

### 1. EKS 모니터링 솔루션을 설계할 때 올바른 원칙은 무엇인가요?

- A. CloudWatch는 애플리케이션 trace를 수집할 수 없다.
- B. Grafana만 설치하면 모든 Pod metric이 자동 수집된다.
- C. 필요한 신호를 선택하고 소유한 collector·data source를 구성한 뒤 전달·포함 범위를 검증한다.
- D. CloudWatch·Prometheus·Grafana·X-Ray를 모두 설치하면 항상 완전한 가시성이 보장된다.

<details>
<summary>정답 및 설명</summary>

**정답: C. 신호·collector·backend 구성을 선택하고 검증한다.**

**설명:**

여러 도구의 조합은 유용할 수 있지만 필요한 신호·운영 조건이 설계를 결정합니다. CloudWatch는 기본 인프라 metric뿐 아니라 지원 workload의 Application Signals trace·APM도 제공합니다. Grafana는 AWS·tracing data source를 조회할 수 있지만 UI만으로 모든 신호를 수집하지는 않습니다. Collector·계측·신원·도달 가능한 endpoint·호환 구성을 명시적으로 연결해야 하며 도구 목록만으로 완전한 포함 범위가 보장되지는 않습니다.

**필요한 계층 유지:**

| 계층 | 신호 예시 | 주요 의존성 |
| --- | --- | --- |
| 인프라 | Node CPU·메모리·disk·network | 지원 node collector와 정확한 metric 차원 |
| Kubernetes | 객체 상태·readiness·API 활동 | Exporter·API·audit 권한과 실제 target |
| 애플리케이션 | Request 지연·오류·업무 metric | 앱 계측과 제한된 metric schema |
| 분산 요청 | Trace span·서비스 관계 | Context 전파·sampling·export 성공 |

**구현 순서:**

1. [본문](../../eks/06-eks-monitoring-logging.md)의 소유 CloudWatch add-on catalog·schema·신원 확인을 따릅니다. 5+ Auto Monitor·restart 설정을 검토하고 기존에 계측된 workload에 agent를 추가하기 전에 충돌을 확인합니다.
2. Prometheus 수집·query가 필요하면 본문의 KPS90.1.1 values와 준비한 storage·Grafana Secret·kubelet serving CA를 사용합니다. Operator가 ServiceMonitor·PrometheusRule을 처리하며 독립 Prometheus 설치와 동일하지 않습니다. 설치 후 실제 target을 검증합니다.
3. 명시적 ADOT 경로는 본문의 Operator0.158·Collector0.50 v1beta1 예제와 object config·TLS·준비한 ServiceAccount를 사용합니다. Collector release에는 Operator 설치 manifest가 없습니다. 이 trace 전용 경로는 X-Ray로 span을 보내며 앱 계측·전파도 필요합니다.
4. AMP는 실제 workspace remote-write endpoint·writer 신원을 구성합니다. Grafana·AMG의 data source·query 신원은 별도이며 AMG12+는 AMP plugin을 사용합니다. Awsemf exporter는 CloudWatch 경로로 게시하고 자동으로 AMP에 보내지 않습니다.

**데이터 경로 예시:**

```text
EKS control-plane logs -------------------------------> CloudWatch Logs
Container stdout/stderr -> chosen log collector ------> configured log store
Application spans ------> ADOT OTLP receiver ----------> X-Ray
Metric targets ----------> Prometheus -----------------> local TSDB
                              |-- SigV4 remote_write -> AMP
Grafana/AMG -- configured queries --> Prometheus / AMP / CloudWatch / X-Ray
```

이는 선택 가능한 경로이며 모든 collector가 모든 backend로 export한다는 뜻이 아닙니다. Dashboard에 의존하기 전에 권한·TLS·discovery·selector·drop 데이터·대표 query를 확인합니다. 경보 우선순위·escalation을 정하고 cardinality·sampling·retention을 관리하며 자동 대응은 별도로 시험합니다.

**Terraform 계획 예제:**

다음 resource 예제는 AWS provider6.64.0을 사용합니다. 선택한 account·Region, 기존에 검토한 Grafana workspace 역할, 지원 AMG 버전과 사용 가능한 IAM Identity Center 구성이 전제입니다. 기존 resource는 소유자의 import·변경 절차가 필요합니다. Application log-group 이름은 본문 collector 경로와 일치하며 add-on·다른 stack이 관리하는 group을 중복 소유하지 않습니다.

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.64.0"
    }
  }
}

variable "region" {
  type = string
}

variable "account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "Use the approved 12-digit AWS account ID."
  }
}

variable "cluster_name" {
  type = string
}

variable "grafana_workspace_role_arn" {
  type = string
}

variable "grafana_version" {
  type        = string
  description = "A reviewed AMG version supported in the selected Region."
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

resource "aws_prometheus_workspace" "eks_monitoring" {
  alias = "${var.cluster_name}-monitoring"
}

resource "aws_grafana_workspace" "eks_monitoring" {
  name                     = "${var.cluster_name}-monitoring"
  account_access_type      = "CURRENT_ACCOUNT"
  authentication_providers = ["AWS_SSO"]
  permission_type          = "CUSTOMER_MANAGED"
  role_arn                 = var.grafana_workspace_role_arn
  grafana_version          = var.grafana_version
}

resource "aws_cloudwatch_log_group" "application" {
  name              = "/aws/containerinsights/${var.cluster_name}/application"
  log_group_class   = "STANDARD"
  retention_in_days = 30
}

output "amp_workspace_id" {
  value = aws_prometheus_workspace.eks_monitoring.id
}

output "amp_prometheus_endpoint" {
  value = aws_prometheus_workspace.eks_monitoring.prometheus_endpoint
}

output "grafana_workspace_id" {
  value = aws_grafana_workspace.eks_monitoring.id
}
```

이는 resource 정의이며 동작하는 수집·로그인 경로가 아닙니다. 실제 workspace ARN에 대한 역할 query 권한, 사용자·group 할당, data source와 반환된 ID·endpoint를 이용한 collector 연결이 필요합니다. CUSTOMER_MANAGED는 IAM 관리를 소유자에게 명시적으로 남깁니다. 기존 SERVICE_MANAGED·data_sources fragment만으로 API로 만든 workspace의 역할·연결이 완료되었다고 볼 수 없습니다. 암호화·retention·접근·비용 조건도 별도로 검토합니다. 이번 감사에서는 Terraform plan·apply·로그인·실제 telemetry query를 실행하지 않았습니다.

**다른 선택지가 틀린 이유:** A는 현재 CloudWatch 기능을 과소평가하고, B는 시각화와 수집을 혼동하며, D는 설치를 포함 범위의 보장으로 취급합니다. 사용자 정의 script도 소유권·오류 처리·범위가 명확한 제한된 자동화·검사에 유용할 수 있습니다.

</details>

### 2. 컨테이너 log를 중앙 보존·분석 경로에 올바르게 연결하는 방법은 무엇인가요?

- A. 주기적으로 node file을 수동 복사하면 완전하고 영구적인 log pipeline이라고 간주한다.
- B. Container 내부 file은 container·node 교체 후에도 항상 남는다고 가정한다.
- C. 올바른 runtime parser·권한·저장·backend를 구성한 소유 collector를 사용한다.
- D. 같은 file에 collector를 두 개 설치하면 무손실 전달이 보장된다고 가정한다.

<details>
<summary>정답 및 설명</summary>

**정답: C. 소유한 수집 경로를 구성하고 검증한다.**

**설명:**

앱은 일반적으로 적절한 구조화 record를 stdout·stderr에 쓰고 platform이 수집·보존을 제공합니다. Stdout은 좋은 인터페이스지만 영구적인 중앙 저장소 자체는 아닙니다. Collector는 parsing·filter·buffer·routing을 제공할 수 있으나 rotation·유한 buffer·node 손실·retry는 포함 범위·중복에 영향을 줍니다. Collector가 무결성·무손실을 보장한다고 주장하기보다 접근·민감정보·retention을 관리합니다.

**연결된 Fluent Bit 기준:**

무관한 master branch raw manifest를 적용하기보다 [본문](../../eks/06-eks-monitoring-logging.md)의 경로를 사용합니다. 독립 예제는 AWS chart0.2.0·image3.4.14, 기본 cloudWatchLogs 설정, CRI parsing, 읽기 전용 node log, 별도 state·buffer와 검토한 RBAC post-renderer를 사용합니다. 실제 log group·IAM 신원을 준비합니다. CloudWatch add-on이 Fluent Bit을 소유하면 실수로 reader를 중복 생성하지 말고 해당 소유자의 구성을 사용합니다.

OpenSearch fan-out은 소유자의 설치·upgrade 절차에서 다음 본문 overlay와 완전한 base values·post-renderer를 함께 사용합니다:

```yaml
opensearch:
  enabled: true
  host: vpc-eks-logs-EXAMPLE.us-west-2.es.amazonaws.com
  port: '443'
  tls: 'On'
  awsAuth: 'On'
  awsRegion: us-west-2
  index: eks-logs
  generateId: 'On'
  suppressTypeName: 'On'
  extraOutputs: 'tls.verify On

    storage.total_limit_size 512M

    '
```

Endpoint·Region은 조회한 domain 값으로 바꿉니다. SigV4 권한·domain policy·FGAC role mapping·TLS 검증은 별도 조건이며 한 요청에서 basic-auth 자격 증명과 SigV4를 결합하지 않습니다. Output별 성공·retry가 독립적이므로 CloudWatch 성공이 OpenSearch 전달을 증명하지 않습니다. 지원 record-accessor template·fallback stream 이름을 사용하며 log_stream_prefix는 Kubernetes record의 임의 shell 형식 치환이 아닙니다.

**Fluentd 대안: 명시적인 Plugin·Input 조건:**

소유 image에 필요한 parser·Kubernetes metadata·OpenSearch plugin이 있으면 Fluentd도 사용할 수 있습니다. Containerd·CRI-O envelope를 해석한 뒤 앱 body를 JSON으로 처리해야 합니다. Tail input·metadata 권한·collector별 position·buffer 저장·mount 구성을 준비합니다. 다음은 OpenSearch output fragment이며 완전한 ConfigMap·DaemonSet 설치가 아닙니다:

```text
<match kubernetes.**>
  @type opensearch
  ssl_verify true
  logstash_format false
  include_timestamp true
  index_name eks-logs
  suppress_type_name true
  <endpoint>
    url "#{ENV.fetch('OPENSEARCH_URL')}"
    region "#{ENV.fetch('AWS_REGION')}"
    assume_role_arn "#{ENV.fetch('AWS_ROLE_ARN')}"
    assume_role_web_identity_token_file "#{ENV.fetch('AWS_WEB_IDENTITY_TOKEN_FILE')}"
  </endpoint>
  <buffer>
    @type file
    path /var/lib/fluentd/opensearch
    total_limit_size 256m
    chunk_limit_size 2m
    retry_timeout 1h
    overflow_action block
  </buffer>
</match>
```

공식 fluent-plugin-opensearch의 IRSA endpoint 필드와 고정 index를 사용합니다. OPENSEARCH_URL과 IRSA가 주입한 role·token-file 환경을 준비합니다. Logstash_format=true이면 index_name을 무시하므로 임의의 Pod별 index 식을 검증된 routing·retention 설계 대신 사용하지 않습니다. 제한된 index·alias와 rollover policy를 검토합니다. File buffer에는 적절하고 격리된 쓰기 가능 저장 경로가 필요하며 block·retry가 있어도 rotation·node 손실로 읽지 못한 log가 사라질 수 있습니다. 이번 감사에서 plugin·input 조합을 실행하지 않았습니다.

**선택한 구성 요소를 통한 ADOT Log 수집:**

ADOT0.50.0에는 filelog·file_storage·awscloudwatchlogs가 포함됩니다. 대응 upstream0.158 CloudWatch Logs exporter는 alpha로 표시되며 다음은 runtime 전제를 명시한 특정 버전 예제이지 운영 준비 완료 주장이 아닙니다. 선택한 dataset의 대체 collector로 사용하고 Fluent Bit과 실수로 중복 수집하지 않습니다.

Operator0.158, logging namespace와 검토한 IRSA 역할·AWS log-write 권한의 ServiceAccount adot-logs를 준비합니다. Trust를 이 클러스터 OIDC provider, sub=system:serviceaccount:logging:adot-logs·aud=sts.amazonaws.com으로 제한하고 필요한 STS·Logs 네트워크 경로를 제공합니다. 일반 Linux EC2 노드 예제이며 root node agent가 /var/log/pods를 읽고 전용 state directory에 쓰도록 admission이 허용해야 합니다. Default namespace include filter는 내보내는 데이터 범위이며 node 전체 host mount를 filesystem 보안 경계로 바꾸지는 않습니다. Node 배치·taint·file 소유권·namespace policy를 검토하고 배포 전에 실제 Region·log-group 값을 설정합니다:

```yaml
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: adot-logs
  namespace: logging
spec:
  mode: daemonset
  image: public.ecr.aws/aws-observability/aws-otel-collector:v0.50.0
  serviceAccount: adot-logs
  nodeSelector:
    kubernetes.io/os: linux
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: eks.amazonaws.com/compute-type
            operator: NotIn
            values: [fargate, auto, hybrid]
  env:
  - name: AWS_REGION
    value: us-west-2
  - name: AWS_EC2_METADATA_DISABLED
    value: "true"
  - name: K8S_NODE_NAME
    valueFrom:
      fieldRef:
        fieldPath: spec.nodeName
  - name: LOG_GROUP_NAME
    value: /aws/containerinsights/my-owned-cluster/application
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: "1"
      memory: 512Mi
  podSecurityContext:
    runAsUser: 0
    runAsGroup: 0
    runAsNonRoot: false
    seccompProfile:
      type: RuntimeDefault
  securityContext:
    allowPrivilegeEscalation: false
    readOnlyRootFilesystem: true
    capabilities:
      drop: [ALL]
  volumes:
  - name: pod-logs
    hostPath:
      path: /var/log/pods
      type: Directory
  - name: collector-state
    hostPath:
      path: /var/lib/adot-logs
      type: DirectoryOrCreate
  volumeMounts:
  - name: pod-logs
    mountPath: /var/log/pods
    readOnly: true
  - name: collector-state
    mountPath: /var/lib/adot-logs
  config:
    extensions:
      file_storage:
        directory: /var/lib/adot-logs/checkpoints
        create_directory: true
      health_check:
        endpoint: 0.0.0.0:13133
    receivers:
      filelog:
        include: [/var/log/pods/default_*/*/*.log]
        include_file_path: true
        start_at: end
        storage: file_storage
        retry_on_failure:
          enabled: true
          max_elapsed_time: 5m
        operators:
        - type: container
          add_metadata_from_filepath: true
          max_log_size: 1MiB
    processors:
      memory_limiter:
        check_interval: 1s
        limit_mib: 384
        spike_limit_mib: 64
      batch: {}
    exporters:
      awscloudwatchlogs:
        region: us-west-2
        log_group_name: ${env:LOG_GROUP_NAME}
        log_stream_name: ${env:K8S_NODE_NAME}
        log_retention: 30
        raw_log: false
        sending_queue:
          num_consumers: 2
          queue_size: 100
    service:
      extensions: [file_storage, health_check]
      pipelines:
        logs:
          receivers: [filelog]
          processors: [memory_limiter, batch]
          exporters: [awscloudwatchlogs]
```

Container operator는 CRI envelope·부분 record를 처리하고 log.file.path에서 Pod metadata를 얻습니다. Raw CRI line에 일반 JSON parser를 적용하는 것은 잘못입니다. Stream 이름은 미지원 {pod_name}.{container_name} placeholder가 아니라 Downward API의 node 이름을 Collector 환경 치환으로 사용합니다.

Exporter는 group·stream을 만들 수 있고 log_retention은 신규 group에 적용됩니다. 기존 retention은 log-group 소유자가 구성합니다. 문서화된 EMF 처리는 설정한 group·stream 이름을 재정의할 수 있으므로 IAM 목적지 범위를 제한하고 실제 data format을 확인합니다. Config 문자열만으로 권한 범위가 제한되는 것은 아닙니다.

File_storage는 receiver offset을 보존하며 아직 export하지 않은 모든 batch를 보존하지는 않습니다. 예제는 메모리 sending queue·유한 retry를 사용하므로 checkpoint·batch·hostPath data의 실패·수명 주기를 구분합니다. Start_at=end는 저장 offset이 없는 최초 읽기에서 기존 내용을 건너뜁니다. Retry·queue·drop·storage 오류·node 교체를 감시합니다. Collector process·mount·AWS 자격 증명 흐름·수집을 시험하지 않았습니다.

**분석·인프라 확인:**

본문 Fluent Bit schema는 실제 namespace·container 필드로 구조화 오류를 확인합니다. ADOT wrapper·다른 collector의 저장 schema는 다를 수 있습니다:

```
fields @timestamp, @log, kubernetes.pod_name, data.level, data.message
| filter kubernetes.namespace_name = "default"
| filter toupper(data.level) = "ERROR"
| sort @timestamp desc
| limit 100
```

독립적인 Terraform 조회 예제는 승인된 기존 OpenSearch domain을 읽습니다:

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.64.0"
    }
  }
}

variable "aws_region" {
  type    = string
  default = "us-west-2"
}

variable "opensearch_domain_name" {
  type        = string
  description = "Existing domain approved for this workload's logs"
}

provider "aws" {
  region = var.aws_region
}

data "aws_opensearch_domain" "eks_logs" {
  domain_name = var.opensearch_domain_name
}

output "opensearch_endpoint" {
  value = coalesce(
    data.aws_opensearch_domain.eks_logs.endpoint_v2,
    data.aws_opensearch_domain.eks_logs.endpoint
  )
}

output "opensearch_domain_arn" {
  value = data.aws_opensearch_domain.eks_logs.arn
}
```

Data source는 network·IAM·domain policy·FGAC·전달을 구성하지 않습니다. 관리와 수집을 구분하고 code·state에 master password를 넣지 않으며 resource·address migration을 검토합니다. Query·접근 시험에는 실제 환경이 필요하고 Terraform validate가 해당 검사를 수행하지는 않습니다.

**다른 선택지가 틀린 이유:** 수동 file 확인은 진단에 유용하지만 완전한 중앙 pipeline은 아닙니다. Container·node 수명과 volume 종류가 file 보존을 결정합니다. 중복 reader는 데이터·비용을 중복시키면서도 실패할 수 있으므로 buffer·retry에는 용량·실패 시험이 필요합니다.

참고: [ADOT 구성 요소](https://github.com/aws-observability/aws-otel-collector/tree/v0.50.0), [container parser](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.158.0/pkg/stanza/docs/operators/container.md), [CloudWatch Logs exporter](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.158.0/exporter/awscloudwatchlogsexporter), [Fluentd OpenSearch plugin](https://github.com/fluent/fluent-plugin-opensearch).

</details>

### 3. EKS에서 효과적이고 검증 가능한 경보 경로를 만드는 방법은 무엇인가요?

- A. 수동 log 검토가 즉각적인 탐지를 보장한다고 가정한다.
- B. CloudWatch 경보 하나로 모든 Kubernetes·앱 장애가 포함된다고 가정한다.
- C. 임의 alertmanager-config ConfigMap을 만들면 Operator가 자동으로 읽는다고 가정한다.
- D. 필요한 신호를 선택하고 metric·event rule과 권한 있는 receiver를 연결해 전달 경로별로 시험한다.

<details>
<summary>정답 및 설명</summary>

**정답: D. 필요한 경보 경로를 연결하고 검증한다.**

**설명:**

CloudWatch 경보·Prometheus/Alertmanager·EventBridge는 서로 다른 신호·routing 요구를 다루며 의도적으로 조합할 수 있습니다. CloudWatch는 앱·custom metric도 지원하고 Prometheus도 적절한 AWS exporter를 사용할 수 있으므로 “인프라 전용” 같은 일반화로 기능을 제한하지 않습니다. 설치만으로 metric 포함 범위·threshold·publisher 권한·전달 성공이 확인되지는 않습니다.

**Metric Rule은 실제 Series·단위와 일치해야 합니다:**

다음 PrometheusRule은 본문의 KPS selector와 실제 node-exporter·kube-state-metrics series를 사용합니다. CPU·available-memory 계산 결과를 명시적으로 백분율로 만들어 threshold80과 단위를 맞춥니다. CrashLoopBackOff는 단순 restart가 아닌 waiting reason을 사용합니다. Running Pod의 Ready=false도 포함하고 종료된 Pod는 제외합니다. 여러 클러스터를 합치면 안정적인 cluster 신원을 추가하고 중복 배포 전에 유사한 기본 rule을 확인합니다:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: eks-observability-alerts
  namespace: monitoring
  labels:
    release: monitoring
spec:
  groups:
  - name: eks-observability-example
    rules:
    - alert: NodeHighCPU
      expr: (100 * (1 - avg by (cluster, instance) (max by (cluster, instance, cpu) (rate(node_cpu_seconds_total{job="node-exporter",mode="idle"}[5m]))))) > 80
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: High non-idle CPU on {{ $labels.instance }}
        description: The node-exporter percentage has exceeded the example threshold; inspect workload and metric health.
    - alert: NodeMemoryFilling
      expr: (100 * (1 - max by (cluster, instance) (node_memory_MemAvailable_bytes{job="node-exporter"}) / max by (cluster, instance) (node_memory_MemTotal_bytes{job="node-exporter"}))) > 80 and on (cluster, instance) (max by (cluster, instance) (node_memory_MemTotal_bytes{job="node-exporter"}) > 0)
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Low available memory on {{ $labels.instance }}
        description: This is a MemAvailable-based estimate, not a MemoryPressure condition or Pod request utilization.
    - alert: KubernetesPodCrashLooping
      expr: max by (cluster, namespace, pod, uid, container) (max_over_time(kube_pod_container_status_waiting_reason{job="kube-state-metrics",reason="CrashLoopBackOff"}[5m])) >= 1
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: CrashLoopBackOff observed for {{ $labels.namespace }}/{{ $labels.pod }}
        description: Inspect container {{ $labels.container }} logs and events; the rule tracks recent waiting reasons, not a restart-count guarantee.
    - alert: PodNotReady
      expr: (max by (cluster, namespace, pod, uid) (kube_pod_status_ready{job="kube-state-metrics",condition="true"}) == 0) and on (cluster, namespace, pod, uid) (max by (cluster, namespace, pod, uid) (kube_pod_status_phase{job="kube-state-metrics",phase=~"Pending|Running|Unknown"}) == 1)
      for: 15m
      labels:
        severity: warning
      annotations:
        summary: Active Pod {{ $labels.namespace }}/{{ $labels.pod }} is not ready
        description: Inspect Ready conditions and probes; terminal Succeeded/Failed Pods are excluded from this example.
```

Threshold·대기 시간은 예시입니다. MemAvailable은 회수 가능한 메모리를 고려한 가용성 추정이며 kubelet MemoryPressure condition·Pod request 대비 비율과는 다릅니다. Series 부재·staleness가 정상·사용량0을 뜻하지는 않습니다. Scrape 실패·rule 평가를 별도로 감시합니다.

**실제 Alertmanager 구성 연결:**

본문의 alertmanager.yaml key를 가진 alertmanager-routing Secret, alertmanager-values.yaml과 notification-credentials mount를 사용합니다. 실제 Slack webhook·PagerDuty Events API v2 routing key를 해당 Secret에 준비합니다. 기본 SNS 경로는 실제 Alertmanager ServiceAccount의 AWS 신원과 topic 범위 publish·필요한 KMS 권한을 준비합니다. 다른 구성 요소의 IRSA 역할이 자동 공유되지는 않습니다.

사용 전에 예시 SNS account·Region·topic을 교체합니다. 다음 완전한 routing 예제는 critical을 PagerDuty, warning을 Slack, 일치하지 않는 경보를 SNS에 보냅니다. Watchdog는 별도 heartbeat monitor를 구성하기 전의 예제 discard 경로입니다:

```yaml
global:
  resolve_timeout: 5m
route:
  group_by:
  - cluster
  - namespace
  - alertname
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: sns-notifications
  routes:
  - matchers:
    - alertname="Watchdog"
    receiver: discard
  - matchers:
    - severity="critical"
    receiver: pagerduty-notifications
  - matchers:
    - severity="warning"
    receiver: slack-notifications
receivers:
- name: discard
- name: slack-notifications
  slack_configs:
  - api_url_file: /etc/alertmanager/secrets/notification-credentials/slack-url
    channel: '#eks-alerts'
    send_resolved: true
    title: '[{{ .Status | toUpper }}] {{ .CommonLabels.alertname }}'
    text: "{{ range .Alerts }}{{ .Annotations.summary }} \u2014 {{ .Annotations.description }}{{ \"\\n\" }}{{ end }}"
- name: sns-notifications
  sns_configs:
  - sigv4:
      region: us-west-2
    topic_arn: arn:aws:sns:us-west-2:123456789012:eks-alerts
    send_resolved: true
    subject: EKS {{ .CommonLabels.alertname }}
- name: pagerduty-notifications
  pagerduty_configs:
  - routing_key_file: /etc/alertmanager/secrets/notification-credentials/pagerduty-routing-key
    send_resolved: true
    severity: '{{ if eq .CommonLabels.severity "critical" }}critical{{ else }}warning{{ end }}'
    description: '{{ .CommonLabels.alertname }}'
```

기본 receiver는 fallback이며 하위 route가 일치할 때 자동 fan-out하지 않습니다. 의도한 fan-out이 필요할 때만 continue·명시적 sibling route를 구성합니다. 일치하는 amtool로 전체 file·route label을 시험합니다. 정의되지 않은 sns-forwarder service나 자격 증명을 담은 ConfigMap은 필요하지 않습니다.

**CloudWatch·EventBridge Publisher 권한:**

- Container Insights 경보는 본문의 실제 metric·차원을 사용합니다. Managed node-group 이름이 EC2 Auto Scaling group 이름과 같다고 가정하거나 AWS/EC2 차원 값을 임의로 만들지 않습니다.
- CloudWatch 경보 publisher에는 적절한 SNS topic policy가 필요합니다. 암호화된 topic에 대해 AWS는 alias/aws/sns만으로 CloudWatch 경보를 지원하지 못한다고 설명합니다. 필요한 publisher 작업을 적절히 제한해 허용하는 customer-managed KMS key를 사용합니다.
- EventBridge는 공개된 EKS add-on health event 또는 지원 CloudTrail API event를 사용합니다. EKS Cluster Control Plane Health는 EKS 직접 event catalog에 없습니다. API 시도가 update 완료를 입증하지는 않습니다.
- SNS target에는 EventBridge execution role 또는 문서화된 resource-policy 경로를 준비합니다. PutTargets 실패·전달 지표를 확인하며 topic 존재·rule API 성공을 전달 증거로 보지 않습니다.

**Terraform 계획 예제:**

다음 독립 예제는 기존 소유 standard SNS topic과 준비한 target 역할을 참조합니다. Topic·key policy, subscription과 실제 ContainerInsights 데이터가 전제입니다. Node CPU 경보는 선택한 ClusterName series의 Maximum을 사용하며 add-on event rule은 account·Region 전체 범위입니다. 검토를 위해 action·rule은 비활성 상태로 시작합니다:

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.64.0"
    }
  }
}

variable "region" {
  type = string
}

variable "account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "Use the approved 12-digit AWS account ID."
  }
}

variable "cluster_name" {
  type = string
}

variable "sns_topic_arn" {
  type        = string
  description = "Prepared standard SNS topic with reviewed publisher/subscription/key permissions."
}

variable "eventbridge_role_arn" {
  type        = string
  description = "Prepared target execution role allowed to publish to the selected topic."
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

resource "aws_cloudwatch_metric_alarm" "node_cpu" {
  alarm_name          = "${var.cluster_name}-node-cpu-warning"
  alarm_description   = "Example node CPU Maximum threshold; confirm actual ContainerInsights data."
  namespace           = "ContainerInsights"
  metric_name         = "node_cpu_utilization"
  dimensions          = { ClusterName = var.cluster_name }
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = 80
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "missing"
  actions_enabled     = false
  alarm_actions       = [var.sns_topic_arn]
}

resource "aws_cloudwatch_event_rule" "addon_health" {
  name_prefix = "eks-addon-health-"
  description = "Account/Region add-on health events; not filtered to a single cluster."
  state       = "DISABLED"
  event_pattern = jsonencode({
    source      = ["aws.eks"]
    account     = [var.account_id]
    region      = [var.region]
    detail-type = ["EKS Addon Health Degraded", "EKS Addon Health Restored"]
  })
}

resource "aws_cloudwatch_event_target" "sns" {
  rule      = aws_cloudwatch_event_rule.addon_health.name
  target_id = "ops-sns"
  arn       = var.sns_topic_arn
  role_arn  = var.eventbridge_role_arn
}
```

CPU 예제는 5분 Maximum 두 구간이 threshold를 넘는 조건이며 10분 내내80% 사용했다는 뜻이 아닙니다. Missing data를 자동 정상으로 취급하지 않습니다. 소유권·publisher 접근·metric 데이터·예상 알림을 검토한 뒤 소유자의 변경 절차로 활성화합니다. 이 예제는 topic policy를 생성·교체하거나 subscription을 구성하지 않으며 AWS에 plan·apply하지 않았습니다.

**SNS Subscription·선택적인 Lambda 처리:**

Email subscription은 확인이 필요합니다. Lambda subscription은 대상 SNS topic이 함수를 호출할 권한도 필요하며 subscription만으로 invocation 접근이 부여되지는 않습니다. SNS는 standard topic에서 Lambda를 비동기로 호출하고 중복 처리가 발생할 수 있습니다. Custom adapter에는 실제 전달 code·패키징 의존성·보호한 자격 증명·입력 검증·idempotency·실패·retry 처리·관측 가능한 결과가 필요합니다.

Send 함수가 pass뿐인데 “processed successfully”를 반환하는 기존 placeholder handler를 배포하면 안 됩니다. HTTP 형태의 statusCode 반환은 비동기 SNS invocation의 알림 전달 확인이 아닙니다. 전달 실패를 올바르게 드러내고 문서화된 SNS record 형식을 확인하며 임의 AlarmName 부분 문자열로 심각도를 추정하지 않습니다. Subscription 전달 실패와 Lambda 실행 실패를 별도로 처리합니다. SQS buffer도 실제 queue·event-source mapping·실패 제어가 필요한 선택 설계이며 아키텍처 그림만으로 생성되지 않습니다.

**구분한 경로:**

```text
CloudWatch alarm -----------------------------> SNS -> confirmed subscribers
EventBridge rule -- authorized target role ---> SNS -> confirmed subscribers
Prometheus -> Alertmanager -- default --------> SNS
                         |-- warning --------> Slack
                         |-- critical -------> PagerDuty
Optional SNS subscriber -> implemented Lambda adapter -> chosen external channel
```

관련 경보를 묶고 반복을 제한하며 심각도·응답 시간을 명시하고 증거·영향을 포함합니다. 승인된 시험 목적지에서 대표 firing·resolution·실패 경로를 시험합니다. 도구 설치만으로 완전한 포함 범위·전달 성공이 따라오지는 않습니다. 이번 감사에서는 topic·subscription·경보·Lambda invocation·notification을 생성하거나 실행하지 않았습니다.

참고: [본문](../../eks/06-eks-monitoring-logging.md), [Alertmanager receiver](https://prometheus.io/docs/alerting/latest/configuration/), [EKS event](https://docs.aws.amazon.com/eventbridge/latest/ref/events-ref-eks.html), [SNS·Lambda](https://docs.aws.amazon.com/lambda/latest/dg/with-sns.html), [CloudWatch 경보의 암호화 SNS](https://repost.aws/knowledge-center/cloudwatch-configure-alarm-sns).

</details>

### 4. 유용한 증거를 보존하는 애플리케이션 관찰성 설계는 무엇인가요?

- A. Node CPU만으로 모든 앱 지연 원인이 입증된다고 본다.
- B. 입력 service.name을 모두 공유 collector 이름 하나로 덮어쓴다.
- C. 서비스 신원을 보존하고 실제 경로를 검증하면서 선택한 metric·log·trace를 연계한다.
- D. 10% head sampler가 모든 오류·느린 요청을 항상 보존한다고 가정한다.

<details>
<summary>정답 및 설명</summary>

**정답: C. 신원을 합쳐 버리지 않고 검증한 신호 경로를 연계한다.**

**설명:**

Metric은 rate·분포·resource 상태를, log는 event 세부 정보를 제공하고 trace는 계측한 작업을 연결합니다. 조사에 도움이 되지만 완전한 가시성·원인 입증을 보장하지 않습니다. Profiling은 명시적으로 활성화·검토할 때 CPU·allocation·heap 증거를 더할 수 있으며 모든 trace collector가 자동 제공하는 기능은 아닙니다.

**올바른 Collector·신호 경로 사용:**

본문의 소유 Operator0.158·ADOT0.50 TLS trace 전용 구성과 Q2의 별도 범위 log 대안을 사용합니다. Operator manifest는 Collector release asset이 아니라 별도 Operator release에서 제공됩니다. Service.name은 앱 경계에서 정하며 공유 resource processor가 order-service·payment-service 등의 값을 전역 값 하나로 upsert하면 안 됩니다.

Prometheus metric은 본문의 연결된 ServiceMonitor·Service 경로나 별도로 검증한 Prometheus receiver를 사용합니다. Annotation discovery만으로 올바른 port·path·RBAC·replica별 target 분배가 구성되지는 않습니다. Awsemf는 CloudWatch로 export하고 AMP에는 실제 remote-write endpoint·SigV4 신원이 필요합니다. Awsemf만 구성한 상태에서 AMP 전달 경로를 그리지 않습니다.

**Java 계측 예제:**

Spring Boot starter의 대안 중 하나는 upstream OpenTelemetry Java agent입니다. 확인한 release는2.31.1이며 앱 build 절차에서 검토한 JAR·호환 앱·JVM을 준비합니다. Gradle 선언·application.properties를 Java source block에 혼합하거나 의존성 버전이 맞지 않는1.18-alpha starter를 복사하지 않습니다. CloudWatch Auto Monitor·다른 소유자가 이미 계측한 process에 agent를 중복 추가하지 않습니다.

다음은 앱 runtime 구성이며 감사용 test 명령이 아닙니다. 본문의 TLS receiver에 OTLP/HTTP trace를 보내고 별도 경로를 사용하는 SDK metric·log export는 끕니다. 신뢰하는 CA를 mount하고 앱에 필요한 다른 JVM 시작 옵션도 보존합니다:

```bash
set -euo pipefail
: "${OTEL_JAVA_AGENT_JAR:?Set the reviewed OpenTelemetry Java agent 2.31.1 JAR path}"
: "${APP_JAR:?Set the application JAR path}"
test -r "$OTEL_JAVA_AGENT_JAR"
test -r "$APP_JAR"
export OTEL_SERVICE_NAME=order-service
export OTEL_RESOURCE_ATTRIBUTES=k8s.cluster.name=my-owned-cluster
export OTEL_TRACES_EXPORTER=otlp
export OTEL_METRICS_EXPORTER=none
export OTEL_LOGS_EXPORTER=none
export OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://adot-traces-collector.tracing-demo.svc:4318/v1/traces
export OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE=/etc/otel/ca.crt
export OTEL_PROPAGATORS=tracecontext,baggage
export OTEL_TRACES_SAMPLER=parentbased_traceidratio
export OTEL_TRACES_SAMPLER_ARG=0.1
java "-javaagent:$OTEL_JAVA_AGENT_JAR" -jar "$APP_JAR"
```

Java agent2.x의 기본 protocol은 http/protobuf이며 예제는 이를 명시합니다. Signal별 HTTP endpoint에는 /v1/traces가 들어갑니다. 4317 gRPC endpoint는 protocol이 다르므로 port만 바꿔 대체할 수 없습니다. Release·구성 metadata를 확인했지만 여기서 Java agent·JDK·앱을 실행하지 않았습니다.

**Python 계측 예제:**

Python3.10+와 버전을 맞춘 SDK·HTTP exporter1.44.0에서 본문의 RequestTracing adapter를 사용합니다. 예시 cluster 이름을 바꾸고 신뢰하는 CA를 mount한 뒤 payment 앱 환경에 다음 값을 설정합니다:

```bash
export OTEL_SERVICE_NAME=payment-service
export CLUSTER_NAME=my-owned-cluster
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://adot-traces-collector.tracing-demo.svc:4318/v1/traces
export OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE=/etc/otel/ca.crt
```

Lifecycle·request 경계를 명시하기 위해 adapter를 다시 제시합니다:

```python
import os
from urllib.parse import urlsplit

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.trace import SpanKind
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


class RequestTracing:
    def __init__(self):
        endpoint = os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"]
        parsed = urlsplit(endpoint)
        if parsed.scheme != "https" or parsed.path != "/v1/traces":
            raise ValueError("Set the HTTPS OTLP/HTTP traces endpoint including /v1/traces")
        self.provider = TracerProvider(
            resource=Resource.create({
                "service.name": os.environ["OTEL_SERVICE_NAME"],
                "k8s.cluster.name": os.environ["CLUSTER_NAME"],
            }),
            sampler=ParentBased(TraceIdRatioBased(0.1)),
        )
        exporter = OTLPSpanExporter(
            endpoint=endpoint,
            certificate_file=os.environ["OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE"],
            timeout=10,
        )
        self.provider.add_span_processor(BatchSpanProcessor(exporter))
        self.tracer = self.provider.get_tracer("example.request-handler")
        self.propagator = TraceContextTextMapPropagator()

    def handle_request(self, incoming_headers, operation):
        parent = self.propagator.extract(incoming_headers)
        with self.tracer.start_as_current_span("request", context=parent, kind=SpanKind.SERVER):
            outgoing_headers = {}
            self.propagator.inject(outgoing_headers)
            return operation(outgoing_headers)

    def close(self):
        self.provider.shutdown()
```

앱 시작 시 instance 하나를 만들고 실제 framework handler에서 정규화한 입력 header 이름·실제 업무 작업을 handle_request에 전달하며 정상 종료 시 close를 호출합니다. Flask server·결제 구현이 아니며 app·request·jsonify·process_transaction이 존재한다고 암묵적으로 가정하지 않습니다. Framework가 지원하는 방법으로 실제 outbound call·비동기 작업에도 context를 전파합니다.

감사에서는 SDK export를 비활성화한 상태로 업무 결과·오류 보존과 순수 전파·sampling 검사를 수행했습니다. 실제 span export·Collector 배포의 증거는 아닙니다.

**IRSA Trust·권한·ServiceAccount 일치:**

다음 독립 Terraform 예제는 본문 collector의 tracing-demo/adot-traces 신원과 일치합니다. 선언한 입력과 실제 cluster issuer의 기존 IAM OIDC provider를 사용합니다. Trust 조건에는 sub·aud가 모두 있습니다. X-Ray PutTraceSegments는 resource-level ARN 범위를 지원하지 않으므로 필요한 wildcard resource에 action·Region 제한과 신원 제한 trust를 결합합니다. 무관한 CloudWatch·AMP 권한은 부여하지 않습니다:

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.64.0"
    }
  }
}

variable "region" {
  type = string
}

variable "account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "Use the approved 12-digit AWS account ID."
  }
}

variable "cluster_oidc_issuer_url" {
  type        = string
  description = "The actual EKS cluster OIDC issuer URL; its IAM OIDC provider must already exist."
  validation {
    condition     = startswith(var.cluster_oidc_issuer_url, "https://")
    error_message = "Use the HTTPS issuer returned by the owned cluster."
  }
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

data "aws_partition" "current" {}

locals {
  oidc_hostpath     = trimsuffix(trimprefix(var.cluster_oidc_issuer_url, "https://"), "/")
  oidc_provider_arn = "arn:${data.aws_partition.current.partition}:iam::${var.account_id}:oidc-provider/${local.oidc_hostpath}"
}

resource "aws_iam_role" "adot_traces" {
  name = "adot-traces-example"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = local.oidc_provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${local.oidc_hostpath}:aud" = "sts.amazonaws.com"
          "${local.oidc_hostpath}:sub" = "system:serviceaccount:tracing-demo:adot-traces"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "xray_write" {
  name = "xray-trace-write"
  role = aws_iam_role.adot_traces.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["xray:PutTraceSegments"]
      Resource = "*"
      Condition = {
        StringEquals = { "aws:RequestedRegion" = var.region }
      }
    }]
  })
}

resource "aws_xray_group" "applications" {
  group_name        = "EKS-Applications"
  filter_expression = "service(\"order-service\") OR service(\"payment-service\")"
}

output "adot_traces_role_arn" {
  value = aws_iam_role.adot_traces.arn
}
```

Collector 생성 전에 이미 준비한 namespace에서 신규 소유 ServiceAccount와 role annotation을 함께 생성할 수 있습니다. 기존 ServiceAccount·role은 소유자의 update·import 절차를 사용하고 다른 신원을 덮어쓰거나 무관한 Pod Identity association을 결합하지 않습니다:

```bash
set -euo pipefail
: "${ADOT_ROLE_ARN:?Set the reviewed role ARN from the owned Terraform stack}"
python3 - "$ADOT_ROLE_ARN" <<'PY' | kubectl create -f -
import json
import sys
print(json.dumps({
    "apiVersion": "v1",
    "kind": "ServiceAccount",
    "metadata": {
        "name": "adot-traces",
        "namespace": "tracing-demo",
        "annotations": {"eks.amazonaws.com/role-arn": sys.argv[1]},
    },
}))
PY
```

Annotation 변경이 실행 중인 Pod에 자격 증명을 소급 주입하지는 않으므로 필요한 rollout을 검토합니다. 실제 issuer·provider·token audience·assumed role·네트워크 경로를 확인합니다. X-Ray group은 일치하는 trace를 분류하며 앱을 계측하거나 collector 권한을 부여하지 않습니다. 불완전한 AMG create 명령을 중복 작성하지 말고 Q1의 workspace·data-source 구성을 사용합니다. 이번 감사에서 IAM role·group·ServiceAccount를 생성하지 않았습니다.

**Browser RUM은 별도 경로입니다:**

CloudWatch RUM web client는 PutRumEvents 데이터를 CloudWatch RUM으로 보내며 ADOT OTLP receiver에 자동 전달하지 않습니다. X-Ray tracing을 켜면 허용 HTTP 요청에 X-Amzn-Trace-Id를 추가할 수 있습니다. Client·server trace가 기본으로 연결되지는 않으므로 지원 server 전파·bridge와 CORS allowed header를 검토합니다. 위 W3C 예제가 X-Ray header를 자동 해석하지는 않습니다. 일반 OpenTelemetry browser client는 별도의 지원 OTLP endpoint·auth·CORS 설계가 필요합니다.

```text
Browser CloudWatch RUM client -----> CloudWatch RUM
                 | optional X-Ray header/segment integration
Java order-service <--- propagated requests ---> Python payment-service
       | OTLP/HTTP TLS                              | OTLP/HTTP TLS
       +--------------> ADOT traces collector <-----+
                              |
                              v
                            X-Ray
Application metrics -> configured Prometheus -> optional SigV4 remote_write -> AMP
Application stdout  -> chosen log collector -> configured log store
Grafana/AMG         -> queries the configured data sources
```

**포함 범위·Sampling·개인정보:**

- 정의한 대상·구간으로 지연 분포·처리량·오류율·포화도를 측정합니다. Sampling한 trace 집합이 자동으로 편향 없는 metric 분포가 되지는 않습니다.
- 제한된 service 이름·정규화한 route·version·environment·cluster·namespace 신원을 사용합니다. Customer·tenant ID·원문 URL은 cardinality·개인정보 문제를 만들 수 있어 기본 metric label로 사용하지 않습니다.
- Head sampling은 요청의 최종 결과 전에 결정하므로 모든 오류·느린 요청을 보장하지 못하고 tail sampling도 upstream에서 버린 span을 복구하지 못합니다. Tail sampling에는 trace별 routing·충분한 buffer·시간 구간이 필요합니다.
- RUM session·user data, log·span·profile에는 적절한 접근·동의·수집 policy·retention이 필요합니다. Correlation ID는 metadata이지 인증이 아닙니다.
- 성능 시험·profiling은 runtime 신호를 보완합니다. 예제가 신규 benchmark·운영 성능 결과를 주장하지 않습니다.

참고: [Java agent 구성](https://opentelemetry.io/docs/zero-code/java/agent/configuration/), [Java SDK 구성](https://opentelemetry.io/docs/languages/java/configuration/), [CloudWatch RUM·X-Ray](https://docs.aws.amazon.com/xray/latest/devguide/xray-services-RUM.html), [본문](../../eks/06-eks-monitoring-logging.md).

</details>

### 5. AWS가 관리하는 EKS control plane log는 어떻게 모니터링해야 하나요?

- A. AWS 관리 control-plane node에 직접 SSH로 접속한다.
- B. 필요한 EKS log type을 구성하고 CloudWatch Logs 전달·query·접근 제어를 검증한다.
- C. Worker-node DaemonSet이 managed control-plane filesystem을 읽는다고 가정한다.
- D. Log dashboard를 만들면 ErrorCount metric이 자동 게시된다고 가정한다.

<details>
<summary>정답 및 설명</summary>

**정답: B. Managed logging 경로를 구성하고 검증한다.**

**설명:**

EKS는 선택한 control-plane log type을 계정의 CloudWatch Logs로 직접 보냅니다. Worker collector가 이 managed log의 원천은 아닙니다. Control-plane SSH 없이 진단·audit 증거를 제공하지만 모든 API 호출 기록·규정 준수를 보장하지 않습니다. Audit policy·stage·활성화 시점·수집·retention이 사용 가능한 범위를 결정합니다.

**Log Type과 범위:**

| Type | 용도 |
| --- | --- |
| api | API-server 진단·오류이며 완전한 request·response archive는 아님 |
| audit | 기록된 Kubernetes API audit event와 신원·resource·status 필드 |
| authenticator | IAM 인증·mapping 진단이며 인증과 RBAC 권한 검사를 구분 |
| controllerManager | Controller reconciliation 진단 |
| scheduler | Scheduling 결정·실패 관련 진단 |

기존 cluster 구성을 먼저 확인합니다. 다섯 type 모두를 켜는 승인된 변경은 본문의 update ID·status 확인 절차를 사용하고 성공 후 실제 log 전달까지 확인합니다:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{ARN:arn,Status:status,Logging:logging}'
```



```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the reviewed cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
UPDATE_ID=$(aws eks update-cluster-config \
  --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query 'update.id' --output text)
if [[ -z "$UPDATE_ID" || "$UPDATE_ID" == None ]]; then
  printf '%s\n' 'No update ID returned; inspect the request result.' >&2
  exit 1
fi
aws eks describe-update --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --update-id "$UPDATE_ID" \
  --query 'update.{ID:id,Status:status,Errors:errors}'
```

마지막 DescribeUpdate는 상태 조회이며 waiter·수집 시험이 아닙니다. 일부 type만 선택해도 기존에 필요한 type을 보존해야 합니다. Api·audit를 켠다는 이유로 authenticator·controllerManager·scheduler를 명시적으로 끄는 block을 복사하지 않습니다. 신규 cluster는 검토한 생성·IaC 구성에 logging을 포함합니다. 모니터링 설정을 위해 불완전한 cluster를 새로 만들지 않습니다. EKS Capabilities controller log는 본문의 별도 delivery 경로를 사용합니다.

**실제 JSON 필드 조회:**

소유한 /aws/eks/CLUSTER/cluster group과 제한된 시간 구간을 선택합니다. 기록된 5xx 응답 예제:

```
fields @timestamp, auditID, user.username, verb, objectRef.resource, responseStatus.code
| filter apiVersion = "audit.k8s.io/v1" and stage = "ResponseComplete"
| filter responseStatus.code >= 500
| sort @timestamp desc
| limit 100
```

알려진 audit username은 user.username이라는 문자열을 parse하지 말고 중첩 JSON 필드를 사용합니다. 예시 username을 record에서 확인한 실제 신원으로 바꿉니다:

```
fields @timestamp, auditID, user.username, verb, objectRef.resource, responseStatus.code
| filter apiVersion = "audit.k8s.io/v1"
| filter user.username = "example-user"
| sort @timestamp desc
| limit 100
```

형식별 실패 filter를 정의하기 전에 authenticator record를 확인합니다. Failed·denied 부분 문자열은 실제 사례를 놓치거나 무관한 본문과 일치할 수 있으며 IAM 인증 message만으로 모든 Kubernetes 권한 결과를 설명할 수는 없습니다.

**Dashboard가 Metric을 게시하지는 않습니다:**

Logs Insights widget은 query를 실행합니다. Custom metric 경보에는 metric filter 같은 실제 publisher가 필요합니다. 다음 독립 Terraform 예제는 STANDARD log group·filter·metric·경보·dashboard를 연결합니다. 사용 전에 실제 소유자의 state에서 기존 log group을 관리·import하고 KMS key·SNS topic·publisher 권한을 준비합니다. 새 EKS cluster·KMS key를 만드는 예제는 아닙니다.

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.64.0"
    }
  }
}

variable "region" {
  type = string
}

variable "account_id" {
  type = string
}

variable "cluster_name" {
  type = string
}

variable "logs_kms_key_arn" {
  type        = string
  description = "Prepared symmetric key in the log-group Region with reviewed Logs/caller permissions."
}

variable "sns_topic_arn" {
  type        = string
  description = "Prepared standard SNS topic with confirmed subscriptions and publisher/key permissions."
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

locals {
  metric_namespace = "EKS/ControlPlane"
  metric_name      = "${var.cluster_name}-AuditResponse5xxCount"
  filter_pattern   = "{ ($.apiVersion = \"audit.k8s.io/v1\") && ($.stage = \"ResponseComplete\") && ($.responseStatus.code >= 500) }"
}

resource "aws_cloudwatch_log_group" "control_plane" {
  name              = "/aws/eks/${var.cluster_name}/cluster"
  log_group_class   = "STANDARD"
  retention_in_days = 90
  kms_key_id        = var.logs_kms_key_arn
}

resource "aws_cloudwatch_log_metric_filter" "audit_5xx" {
  name           = "${var.cluster_name}-audit-response-5xx"
  log_group_name = aws_cloudwatch_log_group.control_plane.name
  pattern        = local.filter_pattern

  metric_transformation {
    namespace     = local.metric_namespace
    name          = local.metric_name
    value         = "1"
    default_value = 0
    unit          = "Count"
  }
}

resource "aws_cloudwatch_metric_alarm" "audit_5xx" {
  alarm_name          = "${var.cluster_name}-audit-response-5xx"
  alarm_description   = "Example threshold for ingested audit ResponseComplete records with code>=500."
  namespace           = local.metric_namespace
  metric_name         = local.metric_name
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  threshold           = 10
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "missing"
  actions_enabled     = false
  alarm_actions       = [var.sns_topic_arn]
}

resource "aws_cloudwatch_dashboard" "control_plane" {
  dashboard_name = "${var.cluster_name}-control-plane"
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "log"
        x      = 0
        y      = 0
        width  = 24
        height = 6
        properties = {
          region = var.region
          title  = "Recorded audit 5xx responses per five minutes"
          view   = "timeSeries"
          query  = "SOURCE '${aws_cloudwatch_log_group.control_plane.name}' | fields @timestamp\n| filter apiVersion = \"audit.k8s.io/v1\" and stage = \"ResponseComplete\" and responseStatus.code >= 500\n| stats count(*) as recordedResponses by bin(5m)"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 24
        height = 6
        properties = {
          region  = var.region
          title   = "Metric filter: new ingested audit 5xx records"
          view    = "timeSeries"
          metrics = [[local.metric_namespace, local.metric_name]]
          period  = 300
          stat    = "Sum"
        }
      }
    ]
  })
}
```

Filter는 새로 수집한 audit ResponseComplete record 중 responseStatus.code>=500인 항목을 셉니다. Audit JSON에 없는 ClusterName 차원을 임의로 만들지 않고 cluster prefix metric 이름으로 구분합니다. Filter·경보·metric widget은 동일 namespace·이름을 사용하고 차원을 추가하지 않습니다. Dashboard query는 과거 record를 포함할 수 있지만 metric filter는 과거 데이터를 backfill하지 않습니다. 이는 기록된 event 수이며 API 오류율·중복 제거된 요청 총수가 아닙니다. 중복 전달도 발생할 수 있습니다.

Default_value0은 log가 들어왔지만 일치 항목이 없을 때 게시합니다. 들어오는 log가 없으면 여전히 missing data일 수 있습니다. Metric filter의 default value와 dimensions는 함께 쓸 수 없습니다. 경보는 의도적으로 action을 끄고 시작하며 missing data·예시 threshold를 명시합니다. 활성화 전에 신규 metric datapoint·권한·subscription·통제된 전달 시험을 확인합니다.

Jsonencode는 기존 dashboard 명령의 잘못된 shell quoting을 피합니다. CLI를 사용하면 --dashboard-body file://dashboard.json으로 유효 JSON file을 전달하고 DashboardValidationMessages를 확인합니다. PutDashboard는 기존 body를 교체하므로 소유자의 widget·구성을 보존합니다. 로컬 HCL·JSON 검증은 AWS filter·query engine 실행이 아닙니다.

**KMS·Retention:**

CloudWatch Logs는 log data를 기본 암호화합니다. Customer-managed symmetric KMS key 연결은 새 수집 데이터의 암호화 key를 바꾸는 것이며 최초 암호화 계층·과거 record 재암호화가 아닙니다. Log group과 같은 Region의 key를 사용하고 과거 데이터가 필요하면 이전 key·권한을 유지하며 연결 권한과 읽기 권한을 구분합니다. 연결 해제 후 신규 data는 기본 암호화로 돌아갑니다. 이전 key 비활성화·삭제는 보존된 해당 data를 읽지 못하게 할 수 있습니다.

Regional Logs service에는 key 사용 권한이 필요합니다. 다음은 key 소유자가 관리자·delegation statement를 유지하며 기존 policy에 병합할 statement fragment입니다. 모든 예시 식별자를 일치하게 교체하며 전체 key policy를 대체하는 문서로 사용하지 않습니다:

```json
{
  "Sid": "AllowLogsServiceForOneGroup",
  "Effect": "Allow",
  "Principal": {
    "Service": "logs.us-west-2.amazonaws.com"
  },
  "Action": [
    "kms:Encrypt",
    "kms:Decrypt",
    "kms:ReEncrypt*",
    "kms:GenerateDataKey*",
    "kms:DescribeKey"
  ],
  "Resource": "*",
  "Condition": {
    "ArnEquals": {
      "kms:EncryptionContext:aws:logs:arn": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/eks/my-cluster/cluster"
    }
  }
}
```

Encryption-context log-group ARN에는 뒤의 :*가 없습니다. Key를 연결하는 운영자에게는 문서화된 Logs 권한·kms:DescribeKey가 필요합니다. 읽기·쓰기 caller에는 regional Logs service를 통한 작업별 KMS 권한이 필요합니다. Key rotation·짧은 삭제 대기 기간이 과거 데이터의 decrypt 접근 유지 요구를 없애지는 않습니다. Retention90은 예시이며 규정 준수·불변성 보장이 아닙니다.

**읽기 접근 범위 지정:**

다음 신원 policy 예제는 선택한 group·stream과 Logs를 통한 key 하나의 decrypt를 허용합니다. Key policy도 의도한 principal을 허용해야 합니다. Log 관리·key 관리 action을 부여하지 않습니다:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadAndQueryThisLogGroup",
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogStreams",
        "logs:FilterLogEvents",
        "logs:StartQuery",
        "logs:GetQueryResults"
      ],
      "Resource": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/eks/my-cluster/cluster:*"
    },
    {
      "Sid": "ReadThisGroupStreams",
      "Effect": "Allow",
      "Action": "logs:GetLogEvents",
      "Resource": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/eks/my-cluster/cluster:log-stream:*"
    },
    {
      "Sid": "DecryptThisGroupsDataViaLogs",
      "Effect": "Allow",
      "Action": "kms:Decrypt",
      "Resource": "arn:aws:kms:us-west-2:123456789012:key/11111111-2222-3333-4444-555555555555",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "logs.us-west-2.amazonaws.com"
        },
        "ArnEquals": {
          "kms:EncryptionContext:aws:logs:arn": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/eks/my-cluster/cluster"
        }
      }
    }
  ]
}
```

현재 AWS 권한 문서는 StartQuery·GetQueryResults의 log-group 범위를 지원합니다. 과거 가정으로 Resource:*까지 넓히지 않습니다. DescribeLogStreams·FilterLogEvents는 group action, GetLogEvents는 stream action입니다. 대부분 IAM action용 LogGroup arn 형식은 :*를 포함하고 logGroupArn·encryption-context·tagging 용도는 이를 생략합니다. Console·discovery에는 추가 read action이 필요할 수 있습니다. DescribeLogGroups는 resource-level ARN을 지원하지 않는 별도 권한이며 위 policy가 암묵적으로 허용하지 않습니다.

이번 감사에서 cluster logging·retention·key policy·metric filter·dashboard·경보·cloud query를 변경하거나 실행하지 않았습니다. 참고: [CloudWatch metric filter](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/MonitoringLogData.html), [LogGroup ARN 형식](https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_LogGroup.html), [Logs IAM action](https://docs.aws.amazon.com/service-authorization/latest/reference/list_logs.html), [KMS log 암호화](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/encrypt-log-data-kms.html).

</details>

### 6. Amazon EKS의 비용 최적화를 가장 잘 지원하는 모니터링 전략은 무엇인가요?

- A. 활용 목적과 관계없이 가능한 모든 메트릭 수집
- B. 리소스 사용량, 청구 비용 할당, 소유자가 검토한 낭비 후보를 함께 분석
- C. 지출을 확인하지 않고 성능만 모니터링
- D. 최종 월별 청구서만 검토

<details>
<summary>정답 보기</summary>

**정답: B. 리소스 사용량, 청구 비용 할당, 소유자가 검토한 낭비 후보를 함께 분석**

**설명:** CPU·메모리·스토리지, requests/limits, 워크로드 추세를 할당 비용과 비교합니다. 이상 비용과 예산 편차는 리소스 소유자와 조사합니다. 이 신호는 개선 후보를 찾는 근거이며, 비용 절감이나 리소스 삭제 가능성을 보장하지 않습니다.

**리소스 효율과 비용 할당**

본문의 kube-prometheus-stack, kube-state-metrics, 서버 인증서를 검증하는 kubelet ServiceMonitor를 재사용합니다. cAdvisor는 kubelet HTTPS 메트릭 포트의 `/metrics/cadvisor` 경로를 사용하며 `cadvisor`라는 별도 Service 포트가 아닙니다. 수집을 위해 중복 모니터를 추가하거나 TLS 검증을 해제하지 않습니다.

다음 CPU·메모리 쿼리는 **컨테이너별 사용량/요청량 비율**이며 노드 용량 사용률이나 금액이 아닙니다. 1을 초과할 수 있고, requests가 0이거나 없으면 비율이 나오지 않습니다. 이를 사용량 0으로 해석하지 않습니다. `max`는 나열한 식별자가 같은 중복 수집본을 합치므로 실제 같은 워크로드인지 확인합니다. 이 예시는 한 클러스터의 로컬 Prometheus를 대상으로 합니다. 공유 백엔드에서는 두 메트릭 계열에 일치하는 cluster 레이블이 필요합니다. 기간 분석에서는 Pod 이름 재사용과 컨테이너 재시작도 고려합니다. 이 컨테이너 메트릭만으로 Pod 수준 리소스, init container, Pod overhead를 포함한 전체 스케줄러 예약량을 표현할 수 없습니다.

```promql
max by (cluster, namespace, pod, container) (
  rate(container_cpu_usage_seconds_total{job="kubelet",metrics_path="/metrics/cadvisor",namespace!="",container!="",container!="POD"}[5m])
)
/ on (cluster, namespace, pod, container)
(
  max by (cluster, namespace, pod, container) (
    kube_pod_container_resource_requests{job="kube-state-metrics",resource="cpu",unit="core",container!=""}
  ) > 0
)
```

```promql
max by (cluster, namespace, pod, container) (
  container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",namespace!="",container!="",container!="POD"}
)
/ on (cluster, namespace, pod, container)
(
  max by (cluster, namespace, pod, container) (
    kube_pod_container_resource_requests{job="kube-state-metrics",resource="memory",unit="byte",container!=""}
  ) > 0
)
```

Grafana의 기존 Prometheus 데이터 소스로 두 쿼리의 패널을 만들고, 대시보드를 **리소스 사용량과 요청량 비교**로 명명합니다. 비율/백분율 단위를 사용하고 cluster·namespace·Pod·container 식별자를 유지합니다. 제공되지 않은 `cost-dashboard.json`을 ConfigMap에 넣는 명령만으로는 대시보드가 만들어지지 않습니다. 본문의 Grafana sidecar로 검토한 JSON을 프로비저닝하려면 설정된 `grafana_dashboard: "1"` 레이블도 필요합니다.

**OpenCost 또는 Kubecost**

본문의 기존 Prometheus와 연동하는 새 OpenCost 평가 환경에서는 다음을 `opencost-values.yaml`로 저장합니다. 확인한 chart는 **2.5.31**, 애플리케이션은 **1.121.2**입니다. 실제 cluster ID와 Prometheus URL로 바꾸고, ServiceMonitor 레이블을 Prometheus selector와 맞추며 namespace 선택 범위에 `opencost`를 포함합니다. 별도 Prometheus/node exporter를 설치하는 구성은 아닙니다.

```yaml
service:
  type: ClusterIP
opencost:
  exporter:
    defaultClusterId: my-cluster
  prometheus:
    internal:
      enabled: false
    external:
      enabled: true
      url: http://monitoring-kube-prometheus-prometheus.monitoring.svc:9090
  metrics:
    serviceMonitor:
      enabled: true
      additionalLabels:
        release: monitoring
  cloudCost:
    enabled: false
  mcp:
    enabled: false
  ui:
    enabled: true
    ingress:
      enabled: false
```

```bash
helm repo add opencost https://opencost.github.io/opencost-helm-chart
helm repo update opencost
helm template opencost opencost/opencost --version 2.5.31 \
  --namespace opencost -f opencost-values.yaml > opencost-rendered.yaml
# After reviewing RBAC, images, resources, selectors, and network access:
helm install opencost opencost/opencost --version 2.5.31 \
  --namespace opencost --create-namespace -f opencost-values.yaml
kubectl -n opencost port-forward --address 127.0.0.1 svc/opencost 9090:9090
```

port-forward 실행 중 `http://localhost:9090`에 접속합니다. 이 기본 구성은 임시 exporter 캐시를 사용하고 Cloud Cost 수집과 MCP를 끄며 ClusterIP Service만 노출합니다. 공용 환경에서는 영속성, 용량, 인증/네트워크 접근, RBAC, 수집 상태를 검토해야 합니다. ClusterIP는 테넌트 인가 경계가 아닙니다. 온디맨드 가격 기반 추정치는 실제 청구, 할인, Spot 가격, 크레딧, 공용 비용, 스토리지 및 네트워크 요금과 대조해야 합니다. AWS 청구 연동은 별도 설정이며, 지원되는 AWS service-account/default-SDK 인증에 장기 액세스 키를 내장할 필요는 없습니다.

Kubecost는 별도 선택지입니다. 확인한 **3.2.4** chart는 `https://kubecost.github.io/kubecost/` 저장소의 `kubecost/kubecost`입니다. 기존 `cost-analyzer` 저장소와 2.x Prometheus values를 3.x 설치법으로 사용할 수 없습니다. 3.x는 ClickHouse와 finops-agent 직접 수집을 사용합니다. 설치/업그레이드 전에 라이선스, 스토리지, Kubernetes 호환성, 공식 2.x 마이그레이션 절차를 검토합니다. [FinOps 플랫폼 가이드](../../ops/13-finops-cost-platform.md)와 [Kubecost chart 문서](https://github.com/kubecost/cost-analyzer-helm-chart)를 참고하세요.

**레이블, 청구 태그, Cost Category**

Namespace 레이블은 Kubernetes 내부 그룹화에 활용합니다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
  labels:
    team: team-a
    cost-center: cc-123
    environment: production
```

이 레이블이 EC2/EBS에 자동으로 태그를 붙이거나 AWS 청구 태그를 활성화하지는 않습니다. 청구 담당자가 실제 AWS 리소스에 태그를 적용한 다음 해당 비용 할당 키를 활성화해야 합니다. 청구 처리 지연을 고려하고 Cost Explorer/CUR에 값이 나타나는지 확인합니다. AWS split cost allocation은 별도로 활성화하는 경로로, EKS Pod 수준 레코드와 `aws:eks:namespace` 같은 AWS 생성 속성을 제공합니다. 모든 namespace 레이블을 EC2 태그로 만드는 기능은 아닙니다. 데이터 소스 전제 조건과 보고서 용량 증가도 검토합니다.

비용 할당 태그 backfill은 **당시 리소스에 태그가 있었던 경우** 최대 12개월까지 가능하며, 없던 과거 태그를 생성하지 않습니다. Cost Category는 검토한 규칙에 따라 청구 레코드를 분류하며 대시보드가 아닙니다. 생성 CLI는 `aws ce create-cost-category-definition`이고 `create-cost-category`가 아닙니다. 실제 청구 데이터에 존재하는 키/값을 사용하고, Cost Explorer 저장 보고서나 대시보드는 별도로 구성합니다.

**연결되지 않은 볼륨의 읽기 전용 목록**

의도한 계정/리전과 기존 소유권 태그를 지정하여 다음을 실행합니다. AWS CLI 페이지네이션을 유지하며 JSON 후보 목록을 출력합니다. 태그 문법을 의도적으로 제한했으므로 실제 태그에 다른 문자가 있으면 JSON 필터로 조정합니다.

```bash
set -euo pipefail
: "${AWS_REGION:?Set the reviewed Region}"
: "${EXPECTED_ACCOUNT_ID:?Set the reviewed 12-digit account ID}"
: "${OWNER_TAG_KEY:?Set an existing ownership tag key}"
: "${OWNER_TAG_VALUE:?Set its exact value}"
[[ "$EXPECTED_ACCOUNT_ID" =~ ^[0-9]{12}$ ]]
# This example accepts a restricted literal subset, excluding wildcards/shorthand separators.
[[ "$OWNER_TAG_KEY" =~ ^[a-zA-Z0-9_./:@+-]+$ ]]
[[ "$OWNER_TAG_VALUE" =~ ^[a-zA-Z0-9_./:@+-]+$ ]]
actual_account=$(aws sts get-caller-identity --region "$AWS_REGION" \
  --query Account --output text --no-cli-pager)
[[ "$actual_account" == "$EXPECTED_ACCOUNT_ID" ]] || {
  echo "Account mismatch" >&2
  exit 1
}
aws ec2 describe-volumes --region "$AWS_REGION" --page-size 100 \
  --filters Name=status,Values=available \
    "Name=tag:$OWNER_TAG_KEY,Values=$OWNER_TAG_VALUE" \
  --query 'Volumes[].{id:VolumeId,zone:AvailabilityZone,sizeGiB:Size,created:CreateTime,state:State}' \
  --output json --no-cli-pager
```

`available`은 현재 연결되지 않았다는 뜻이며, 미사용 또는 삭제 가능하다는 뜻이 아닙니다. 생성 시각도 마지막 사용 시각이 아닙니다. 소유자와 PV/PVC 소유권, reclaim policy, 대기 워크로드, 백업, 스냅샷, 재해 복구 요구를 확인합니다. 임의의 5% 기준을 포함해 낮은 CPU/메모리 사용량만으로 Pod나 로드 밸런서가 불필요하다고 판단할 수 없습니다. 대표 기간의 이력과 애플리케이션/SLO 신호를 함께 확인하며, 메트릭 누락을 빈 “유휴 Pod” 결과로 바꾸지 않습니다.

**예산 예시**

다음 독립 Terraform 예시는 실제 활성화된 청구 태그와 승인된 수신자를 사용합니다. **월 1,000 USD 한도와 80% 알림**은 설정 예시이며 관측된 비용이 아닙니다. 기존 예산은 충돌하는 새 소유자를 만들지 말고 import/조정합니다. 선택한 비용 기준과 태그 범위를 검증하세요. 태그 필터는 태그 없는 비용이나 공용 비용을 누락할 수 있습니다. 적용하면 실제 알림 구성이 생성됩니다.

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.64.0"
    }
  }
}

variable "account_id" {
  type = string
}

variable "region" {
  type = string
}

variable "budget_name" {
  type = string
}

variable "activated_tag_key" {
  type = string
}

variable "tag_value" {
  type = string
}

variable "notification_email" {
  type        = string
  description = "Approved budget owner; applying this example configures real email notifications."
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

resource "aws_budgets_budget" "eks_monthly" {
  account_id   = var.account_id
  name         = var.budget_name
  budget_type  = "COST"
  limit_amount = "1000"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filter {
    name   = "TagKeyValue"
    values = [join("$", [var.activated_tag_key, var.tag_value])]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.notification_email]
  }
}
```

Budgets는 처리된 청구 데이터를 사용하며 지출을 강제로 제한하지 않습니다. Budget Actions는 IAM/SCP 제어 또는 지원되는 EC2/RDS 인스턴스를 대상으로 동작할 수 있지만, 별도 권한과 운영 검토가 필요합니다. 앞의 리소스 효율 대시보드는 청구 대시보드가 아닙니다.

VPA 권고와 피크/SLO 이력으로 requests를 검토하고 HPA와 노드 확장을 조율합니다. Karpenter/Cluster Autoscaler와 Spot의 절감 효과는 워크로드, 중단 허용, 용량, disruption 제약에 따라 달라집니다. requests를 줄이는 것만으로 청구액이 줄지는 않으며 실제 프로비저닝 용량이나 가격 조건이 바뀌어야 합니다. 정기적인 소유자 검토에서 합의한 조치와 측정 결과를 추적합니다.

나머지 선택지는 이런 피드백을 놓칩니다. 모든 메트릭 수집은 관측 비용/노이즈를 늘리고, 성능만으로는 지출을 알 수 없으며, 최종 월별 청구서만으로는 신속한 조사가 어렵습니다.

**공식 근거:** [OpenCost 설치](https://opencost.io/docs/installation/helm), [AWS 태그 활성화](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/activating-tags.html), [태그 backfill](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/cost-allocation-backfill.html), [split cost allocation](https://docs.aws.amazon.com/cur/latest/userguide/split-cost-allocation-data.html), [Budget Actions](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-controls.html).

</details>
