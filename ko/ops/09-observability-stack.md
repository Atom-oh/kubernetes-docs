# Observability 스택 구성과 운영

> 검토 기준: 2026-09-11. Loki 3.7.7, Tempo 3.0.3, Alloy 1.19.2,
> OpenTelemetry Collector Contrib 0.160.0, kube-prometheus-stack 90.1.1.

이 장은 로그·트레이스·메트릭의 **수집 경로, 저장, 권한, 보존, 조회 연결**을
구성합니다. 애플리케이션의 Go/Python 계측과 Java JSON 로그는
[앞 장의 실행 가능한 예제](./08-observability-analysis.md)를 사용합니다.
Grafana를 설치하는 것만으로 세 신호가 연결되지는 않습니다.

## 구성 범위와 준비

| 신호 | 수집 경로 | 저장·조회 |
|---|---|---|
| 로그 | 애플리케이션 JSON stdout → Alloy의 Kubernetes 로그 API 수집 | Loki → Grafana |
| 트레이스 | 애플리케이션 OTLP → Collector → Tempo | Tempo → Grafana |
| 메트릭 | Prometheus scrape, 선택적으로 Tempo 생성 메트릭 remote write | Prometheus, 선택적으로 AMP |

예제 네임스페이스는 `observability`입니다. 해당 네임스페이스와 Prometheus Operator
CRD, 정상 동작하는 `gp3` StorageClass를 먼저 준비합니다. EKS Auto Mode의 StorageClass와
일반 EBS CSI StorageClass는 provisioner가 다릅니다. 이름만 같다고 호환되는 것은 아닙니다.
S3 버킷과 IRSA 역할은 별도 준비 항목이며, 예제의 계정·역할·버킷·워크스페이스 값을 교체합니다.
버킷은 용도별로 구분하고 퍼블릭 액세스를 차단합니다. Loki/Tempo 역할에는 필요한 버킷의
목록 조회와 객체 읽기·쓰기·삭제 권한을 부여하며, SSE-KMS 사용 시 해당 키 권한도 검토합니다.

아래 설정은 **구성을 검증하기 위한 시작점**입니다. 무인증 내부 HTTP, Kafka 연결, 리소스
크기와 보존 정책을 그대로 운영 기준으로 삼지 않습니다. 네트워크 접근 제어, TLS/인증,
저장 용량과 장애 복구는 실제 환경에서 검증합니다. `ClusterIP`만으로 인증이 생기지 않습니다.

Helm 차트 버전과 애플리케이션 버전은 다릅니다. Loki와 Tempo 예제는 현재의
`grafana-community` 저장소를 사용합니다. 과거 `grafana/tempo` 차트에 분산용 값을 넣는
방식은 단일 바이너리를 분산 배포로 바꾸지 않습니다.

```bash
helm repo add grafana-community https://grafana-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
```

## Loki: 배포 모드와 S3 저장

Loki는 스트림 레이블을 인덱싱하고 로그를 청크로 저장합니다. 콘텐츠 검색은 선택한 스트림의
데이터를 읽으므로 레이블 선택, 시간 범위, 청크·인덱스 캐시가 쿼리 비용에 영향을 줍니다.
압축률이나 “하루 몇 GB 이상이면 반드시 분산”이라는 숫자는 워크로드와 벤치마크 없이 보장할 수 없습니다.

| 모드 | 용도와 제약 |
|---|---|
| Monolithic | 하나의 프로세스에 구성 요소 포함. HA 구성은 공유 객체 저장소·복제·라우팅 설계 필요 |
| SimpleScalable | read/write/backend 분리. 현재 deprecated이며 Loki 4.0에서 제거 예정 |
| Distributed | 구성 요소별 확장. 네트워크·링·쿼리 경로·저장 운영 부담도 증가 |

새 예제는 Distributed를 사용합니다. 아래는 ingester 3개와 compactor 1개를 렌더링합니다.
`zoneAwareReplication: false`이므로 3개 복제본만으로 AZ 장애 분리가 보장되지는 않습니다.
운영 시 AZ/노드 배치, quorum과 PDB, 롤링 업데이트를 함께 검증합니다.
캐시는 초기 검증 범위를 줄이기 위해 껐으며, 운영 용량 시험에서 필요성과 크기를 결정합니다.

`schemaConfig`의 날짜는 **새 저장소 예제**입니다. 기존 데이터가 있는 설치의 과거 스키마를
덮어쓰지 않습니다. 마이그레이션은 기존 항목을 유지하고 미래 날짜의 항목을 추가하는 절차를 따릅니다.
`auth_enabled: false`는 단일 tenant `fake`를 사용하는 내부 예제입니다.
멀티테넌시를 켜도 Loki가 사용자 로그인을 제공하는 것은 아니며, 인증 프록시가 tenant 헤더를
검증·설정해야 합니다.

```yaml
# loki-values.yaml
deploymentMode: Distributed
loki:
  image:
    tag: 3.7.7
  auth_enabled: false
  commonConfig:
    replication_factor: 3
  schemaConfig:
    configs:
    - from: '2026-09-01'
      store: tsdb
      object_store: s3
      schema: v13
      index:
        prefix: loki_index_
        period: 24h
  storage:
    type: s3
    bucketNames:
      chunks: REPLACE_WITH_UNIQUE_LOKI_CHUNKS_BUCKET
      ruler: REPLACE_WITH_UNIQUE_LOKI_RULER_BUCKET
    s3:
      region: ap-northeast-2
  ingester:
    chunk_encoding: snappy
  compactor:
    retention_enabled: true
    delete_request_store: s3
    retention_delete_delay: 2h
  limits_config:
    retention_period: 720h
    allow_structured_metadata: true
  analytics:
    reporting_enabled: false
serviceAccount:
  create: true
  name: loki
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/docs-loki-s3
singleBinary:
  replicas: 0
read:
  replicas: 0
write:
  replicas: 0
backend:
  replicas: 0
ingester:
  replicas: 3
  zoneAwareReplication:
    enabled: false
  persistence:
    enabled: true
    claims:
    - name: data
      accessModes: &id001
      - ReadWriteOnce
      size: 20Gi
      storageClass: gp3
distributor:
  replicas: 2
querier:
  replicas: 2
queryFrontend:
  replicas: 2
queryScheduler:
  replicas: 2
indexGateway:
  replicas: 2
compactor:
  replicas: 1
  persistence:
    enabled: true
    claims:
    - name: data
      accessModes: *id001
      size: 20Gi
      storageClass: gp3
gateway:
  enabled: true
  replicas: 2
chunksCache:
  enabled: false
resultsCache:
  enabled: false
sidecar:
  rules:
    enabled: false
```

```bash
helm template loki grafana-community/loki --version 18.12.2   --namespace observability -f loki-values.yaml > loki-rendered.yaml
helm upgrade --install loki grafana-community/loki --version 18.12.2   --namespace observability -f loki-values.yaml
```

차트 18.12.2의 ingester·compactor PVC는 `persistence.claims`에서 설정합니다.
리스트를 교체할 때 `accessModes`도 포함해야 합니다. `helm template` 성공만 확인하지 말고,
생성된 `volumeClaimTemplates`의 StorageClass·크기·접근 모드와 실제 PVC 바인딩을 확인합니다.
Loki gateway Service는 이 예제에서 **80**, Loki 프로세스 HTTP 포트는 **3100**입니다.

### 보존 정책

TSDB v13의 24시간 인덱스와 `compactor.retention_enabled`, `delete_request_store`,
`limits_config.retention_period`를 함께 설정합니다. 삭제는 비동기이며 `retention_delete_delay`가 있습니다.
compactor의 삭제 marker와 상태를 재시작 후에도 유지하도록 저장소를 확인합니다.
보존 기간 변경이 기존 데이터를 원하는 형태로 소급 정리한다고 가정하지 않습니다.

테넌트 override는 차트의 `loki.runtimeConfig.overrides`에 둡니다.
단일 tenant 예제에서 적용 대상은 `fake`입니다. 아래 조각을 적용하면 **기본 30일보다
우선하는 7일 정책**이 되므로 보존 요구를 확인한 뒤 사용합니다.

```yaml
loki:
  runtimeConfig:
    overrides:
      fake:
        retention_period: 168h
```

객체 저장소 lifecycle로 버킷 전체를 일괄 만료시키면 인덱스·삭제 요청·ruler 설정을
손상시킬 수 있습니다. 필요하다면 청크 prefix로 제한하고 보존 기간과 삭제 지연보다 길게 설정합니다.
S3 versioning과 백업도 보존 비용·삭제 요구를 별도로 검토해야 하며, versioning을 켠 것만으로 복구 시험이 완료되지는 않습니다.

## Alloy 로그 수집과 레이블

Promtail은 2026-03-02에 EOL에 도달했습니다. 신규 예제는 Alloy를 사용합니다.
다음 구성은 [앞 장](./08-observability-analysis.md)의 `observability` 네임스페이스,
`app=correlation-api` Pod를 Kubernetes 로그 API로 읽습니다. 노드 파일 tail이 아니므로
hostPath와 `stage.cri`를 추가하지 않습니다.

Deployment 한 개에 `Recreate`를 사용해 정상 상태와 업데이트 중의 중복 수집을 피합니다.
이는 HA 구성이 아니며 업데이트 중 수집 공백이 생길 수 있습니다. 여러 복제본으로 확장할 때는
Alloy clustering과 해당 source의 clustering 설정을 함께 구성하거나 노드별 대상 범위를 제한합니다.
모든 노드의 DaemonSet이 모든 Pod를 수집하면 중복 전송됩니다.

```yaml
# alloy-rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: alloy-logs
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: alloy-logs
  namespace: observability
rules:
  - apiGroups: [""]
    resources: [pods]
    verbs: [get, list, watch]
  - apiGroups: [""]
    resources: [pods/log]
    verbs: [get]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: alloy-logs
  namespace: observability
subjects:
  - kind: ServiceAccount
    name: alloy-logs
    namespace: observability
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: alloy-logs
```

```alloy
// logs.alloy
// Kubernetes API log source: configure its ServiceAccount permissions first.
discovery.kubernetes "application" {
  role = "pod"
  namespaces {
    names = ["observability"]
  }
  selectors {
    role  = "pod"
    label = "app=correlation-api"
  }
}

discovery.relabel "application_logs" {
  targets = discovery.kubernetes.application.targets
  rule {
    source_labels = ["__meta_kubernetes_namespace"]
    target_label  = "namespace"
  }
  rule {
    source_labels = ["__meta_kubernetes_pod_label_app"]
    target_label  = "service_name"
  }
  rule {
    source_labels = ["__meta_kubernetes_pod_container_name"]
    target_label  = "container"
  }
}

loki.source.kubernetes "application" {
  targets    = discovery.relabel.application_logs.output
  forward_to = [loki.process.application.receiver]
}

loki.process "application" {
  stage.json {
    expressions = {
      level = "level",
    }
  }
  stage.labels {
    values = {
      level = "",
    }
  }
  // Keep the complete JSON body, including trace_id/span_id. They are not
  // indexed stream labels and remain available for parsing/correlation.
  forward_to = [loki.write.backend.receiver]
}

loki.write "backend" {
  endpoint {
    url = "http://loki-gateway.observability.svc:80/loki/api/v1/push"
  }
}
```

아래 값을 `alloy-values.yaml`로 저장하고 `--set-file`로 앞의 파일을 주입합니다.
이 방식은 긴 Alloy 설정을 YAML 문자열로 다시 복사할 필요가 없습니다.

```yaml
controller:
  type: deployment
  replicas: 1
  updateStrategy:
    type: Recreate
alloy:
  enableReporting: false
  configMap:
    content: ''
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      memory: 512Mi
rbac:
  create: false
serviceAccount:
  create: false
  name: alloy-logs
crds:
  create: false
```

```bash
kubectl apply -f alloy-rbac.yaml
helm upgrade --install alloy grafana/alloy --version 1.12.1   --namespace observability -f alloy-values.yaml   --set-file alloy.configMap.content=logs.alloy
```

`namespace`·`service_name`·`container`처럼 범위가 제한된 레이블을 우선 사용합니다.
`trace_id`·`request_id`는 JSON 본문이나 structured metadata에 보관합니다.
Pod 이름도 무조건 금지되는 값은 아니지만 수명과 churn이 스트림 수에 미치는 영향을 계산해야 합니다.
label 조합의 곱이 중요하며 “레이블 5개면 안전” 같은 기준은 없습니다.
이 예제는 전체 JSON 본문을 보존하고 `level`만 추가 인덱싱합니다. 허용되지 않은 자유 형식
level 값이나 개인정보는 애플리케이션·수집 단계에서 정규화/제거합니다.

### LogQL과 로그 알림

숫자 집계 전에는 JSON 파싱 오류와 잘못된 숫자를 제거합니다. 아래 지연 필드의 단위는 **ms**입니다.
`rate`는 로그 행 수/초이며 바이트/초는 `bytes_rate`입니다.

```logql
{service_name="correlation-api"} | json | __error__="" | level="ERROR"
```

```logql
sum(rate({service_name="correlation-api"}[5m]))
```

```logql
sum(bytes_rate({service_name="correlation-api"}[5m]))
```

```logql
avg_over_time({service_name="correlation-api"} | json | latency_ms >= 0 | __error__="" | unwrap latency_ms | __error__="" [5m])
```

```logql
quantile_over_time(0.95, {service_name="correlation-api"} | json | latency_ms >= 0 | __error__="" | unwrap latency_ms | __error__="" [5m])
```

Loki Ruler는 LogQL 규칙을 평가하고 Alertmanager에 알림을 보냅니다. PrometheusRule에
LogQL을 넣거나 임의 ConfigMap에 `loki_rule` 레이블을 붙이는 것만으로 규칙이 로드되지는 않습니다.
위 기본 값은 ruler 복제본이 0입니다. 별도 ruler 배포, 규칙 저장소/API 또는 마운트,
규칙 평가 주기와 Alertmanager 주소를 구성한 뒤 검증합니다.

일반 문자열 `"error"`·`"unauthorized"`가 보였다는 것만으로 장애나 공격을 확정하지 않습니다.
CrashLoopBackOff는 애플리케이션 로그보다 kube-state-metrics의 컨테이너 상태를 확인합니다.
로그 비율 알림은 분자·분모의 같은 범위, 파싱 실패, 무트래픽, 누락 error 시계열을 처리하고
[알림 장](./07-observability-alerts.md)의 라우팅·억제 시험과 연결합니다.

## Tempo 3: 단일 인스턴스와 분산 운영

Tempo는 trace ID 조회뿐 아니라 **TraceQL 속성 검색**도 제공합니다.
metrics-generator는 선택한 트레이스에서 메트릭을 생성하는 구성 요소이며 검색을 켜는 스위치가 아닙니다.

Tempo 3의 분산 경로는 다음과 같습니다.

| 구성 요소 | 역할 |
|---|---|
| Distributor | 수신 span을 Kafka에 기록 |
| Block-builder | Kafka에서 읽어 객체 저장소 블록 생성 |
| Live-store | 최근 데이터 조회 |
| Backend-scheduler / backend-worker | 블록 정리·compaction·보존 처리 |
| Query-frontend / querier | 최근 데이터와 객체 저장소 조회 |

2.x의 ingester·compactor target과 scalable single binary 모드는 제거되었습니다.
**단일 프로세스 monolithic 모드는 Kafka가 필요하지 않습니다.**
단일 예제의 `replicas`를 늘려 분산 HA로 바꾸지 않습니다.

### 단일 인스턴스 실습

`tempo-lab-values.yaml`은 Kafka 없이 로컬 PVC를 쓰는 실습입니다. 프로세스/PVC 장애로
사용이 중단될 수 있으며, 이 예제를 S3 분산 운영과 혼용하지 않습니다.
차트 3.0.0에서 Jaeger를 비활성화할 때는 부모를 `null`로 지우는 대신 하위 protocol을
`null`로 지정합니다. 차트의 Service에는 legacy 포트가 남을 수 있으므로 실제 receiver 설정과
네트워크 정책을 기준으로 접근을 제한합니다.

```yaml
# tempo-lab-values.yaml
replicas: 1
tempo:
  tag: 3.0.3
  reportingEnabled: false
  retention: 336h
  receivers:
    jaeger:
      protocols:
        grpc: null
        thrift_binary: null
        thrift_compact: null
        thrift_http: null
    otlp:
      protocols:
        grpc:
          endpoint: 0.0.0.0:4317
        http:
          endpoint: 0.0.0.0:4318
  resources:
    requests:
      cpu: 250m
      memory: 512Mi
    limits:
      memory: 2Gi
  metricsGenerator:
    enabled: true
    storage:
      path: /var/tempo/metrics
      remote_write:
      - url: http://prometheus-kube-prometheus-prometheus.observability.svc:9090/api/v1/write
        send_exemplars: true
  overrides:
    defaults:
      metrics_generator:
        processors:
        - service-graphs
        - span-metrics
persistence:
  enabled: true
  storageClassName: gp3
  size: 20Gi
```

```bash
helm upgrade --install tempo grafana-community/tempo --version 3.0.0   --namespace observability -f tempo-lab-values.yaml
```

### 분산 구성 검토용 예제

다음 파일은 **위 단일 차트의 추가 값이 아닌 대안**입니다.
Kafka와 S3가 이미 존재해야 합니다. 예제는 격리된 검증 환경의 내부 Kafka 주소를 사용합니다.
운영 Kafka의 TLS·인증 방식과 Tempo 3.0.3 클라이언트 지원을 먼저 확인합니다.
이 버전의 `ingest.kafka`에는 임의 `tls` 또는 MSK IAM 필드를 넣을 수 없습니다.
`sasl_username`·`sasl_password` 지원을 TLS 암호화 지원으로 오해하지 않습니다.

기본 `partitions_per_instance: 1`에서 Kafka topic 3개 partition에 맞춰 block-builder 3개를 둡니다.
아래 chart의 live-store도 3개로 맞춥니다. 기존 Kafka topic의 partition 수는
`auto_create_topic_default_partitions` 값을 바꿔도 수정되지 않습니다.
자동 생성을 끄고 Kafka의 실제 partition·복제·최소 ISR·retention·용량을 따로 설정합니다.
block-builder/live-store에 존재하지 않는 `persistence` Helm 키를 추가해도 PVC가 생기지 않습니다.
현재 차트의 실제 저장 방식과 Kafka 재생 가능 기간을 바탕으로 복구를 시험합니다.

```yaml
# tempo-distributed-values.yaml
reportingEnabled: false
multitenancyEnabled: false
tempo:
  image:
    tag: 3.0.3
ingest:
  kafka:
    address: kafka.kafka.svc.cluster.local:9092
    topic: tempo-traces
    auto_create_topic_enabled: false
    auto_create_topic_default_partitions: 3
blockBuilder:
  replicas: 3
liveStore:
  replicas: 3
backendScheduler:
  enabled: true
  config:
    provider:
      compaction:
        compaction:
          block_retention: 336h
  persistence:
    enabled: true
    size: 20Gi
    storageClass: gp3
backendWorker:
  replicas: 2
  podDisruptionBudget:
    enabled: true
distributor:
  replicas: 2
querier:
  replicas: 2
queryFrontend:
  replicas: 2
traces:
  otlp:
    grpc:
      enabled: true
    http:
      enabled: true
storage:
  trace:
    backend: s3
    s3:
      bucket: REPLACE_WITH_UNIQUE_TEMPO_BUCKET
      endpoint: s3.ap-northeast-2.amazonaws.com
      region: ap-northeast-2
serviceAccount:
  create: true
  name: tempo
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/docs-tempo-s3
metricsGenerator:
  enabled: true
  kind: StatefulSet
  persistence:
    enabled: true
    storageClass: gp3
    size: 20Gi
  config:
    storage:
      remote_write:
      - url: http://prometheus-kube-prometheus-prometheus.observability.svc:9090/api/v1/write
        send_exemplars: true
overrides:
  defaults:
    metrics_generator:
      processors:
      - service-graphs
      - span-metrics
gateway:
  enabled: true
```

```bash
helm template tempo grafana-community/tempo-distributed --version 3.5.1   --namespace observability -f tempo-distributed-values.yaml > tempo-rendered.yaml
```

3.5.1 차트의 backend-worker PDB 템플릿이 기본값 누락으로 실패하지 않도록
`backendWorker.podDisruptionBudget.enabled`를 명시했습니다. 렌더링 후에도 Kafka 연결,
S3 권한, Pod 배치와 실제 쓰기·조회는 별도 시험입니다.
분산 설치에서 수신 주소는 `tempo-distributor:4318`, 조회 주소는
`tempo-query-frontend:3200`입니다. 아래 단일 실습용 Collector와 Grafana 주소를 함께 변경합니다.

### 2.x → 3.x 마이그레이션

단일 모드는 `tempo-cli migrate config --mode=monolithic`으로 변환 결과를 검토합니다.
분산 모드는 병렬 배포·검증·트래픽 전환 절차를 사용합니다. `ingester`, `ingester_client`,
`compactor`, `metrics_generator_client`와 제거된 `local_blocks` 설정을 그대로 가져오지 않습니다.
기존 데이터의 block format은 vParquet4 이상이어야 합니다.

공유 버킷을 사용하는 병렬 운영에서는 두 compaction 시스템을 동시에 활성화하지 않습니다.
3.x의 `compaction_disabled`를 defaults와 **각 tenant override 모두**에 적용하고,
2.x compactor 종료 후 해제합니다. tenant override가 defaults의 일부 필드만 상속한다고 가정하지 않습니다.
이전 trace ID와 신규 trace ID 조회를 모두 검증한 뒤 전환합니다.
TraceQL metrics는 RF1 블록 범위 등 마이그레이션 제약이 있으므로 과거 전체 데이터가
자동으로 동일한 메트릭 범위를 제공한다고 보장하지 않습니다.

## Collector와 샘플링

다음은 단일 Collector에서 tail sampling을 검증하는 구성입니다. 애플리케이션이 전송하는
resource에 `service.name`을 설정합니다. Kubernetes metadata를 자동으로 추가한다고
주장하지 않으며, 이를 추가할 때는 k8sattributes의 Pod 연관 기준과 별도 RBAC가 필요합니다.
Kubernetes 이벤트는 로그 신호이며 `k8s_events`를 traces receiver로 사용할 수 없습니다.

민감한 속성 삭제는 tail buffer보다 앞에 둡니다. 이것은 예시 키에만 적용되므로 로그·이벤트·
다른 속성의 민감정보까지 모두 지워지는 것은 아닙니다. `db.statement`를 hash하는 것만으로
비밀이나 개인정보가 안전해졌다고 간주하지 않습니다.

```yaml
# collector.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 768
    spike_limit_mib: 128
  attributes/remove-secrets:
    actions:
      - key: http.request.header.authorization
        action: delete
      - key: db.statement
        action: delete
      - key: db.query.text
        action: delete
  tail_sampling:
    decision_wait: 30s
    num_traces: 20000
    expected_new_traces_per_sec: 500
    policies:
      - name: errors
        type: status_code
        status_code:
          status_codes: [ERROR]
      - name: slow
        type: latency
        latency:
          threshold_ms: 2000
      - name: baseline
        type: probabilistic
        probabilistic:
          sampling_percentage: 10
  batch:
    send_batch_size: 512
    send_batch_max_size: 1024
    timeout: 1s
exporters:
  otlphttp/tempo:
    endpoint: http://tempo.observability.svc:4318
    retry_on_failure:
      enabled: true
    sending_queue:
      enabled: true
      queue_size: 1000
extensions:
  health_check:
    endpoint: 0.0.0.0:13133
service:
  extensions: [health_check]
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, attributes/remove-secrets, tail_sampling, batch]
      exporters: [otlphttp/tempo]
  telemetry:
    metrics:
      readers:
        - pull:
            exporter:
              prometheus:
                host: 0.0.0.0
                port: 8888
```

```yaml
# collector-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-collector
  namespace: observability
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: otel-collector
  template:
    metadata:
      labels:
        app: otel-collector
    spec:
      automountServiceAccountToken: false
      containers:
        - name: collector
          image: otel/opentelemetry-collector-contrib:0.160.0
          args: ["--config=/etc/otel/collector.yaml"]
          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              memory: 1Gi
          ports:
            - {name: otlp-grpc, containerPort: 4317}
            - {name: otlp-http, containerPort: 4318}
            - {name: metrics, containerPort: 8888}
            - {name: health, containerPort: 13133}
          readinessProbe:
            httpGet:
              path: /
              port: health
          livenessProbe:
            httpGet:
              path: /
              port: health
          volumeMounts:
            - {name: config, mountPath: /etc/otel, readOnly: true}
      volumes:
        - name: config
          configMap:
            name: otel-collector
---
apiVersion: v1
kind: Service
metadata:
  name: otel-collector
  namespace: observability
spec:
  selector:
    app: otel-collector
  ports:
    - {name: otlp-grpc, port: 4317, targetPort: otlp-grpc}
    - {name: otlp-http, port: 4318, targetPort: otlp-http}
    - {name: metrics, port: 8888, targetPort: metrics}
```

```bash
kubectl create configmap otel-collector --namespace observability   --from-file=collector.yaml --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f collector-deployment.yaml
```

Collector Contrib 0.160.0의 자체 메트릭은 `service.telemetry.metrics.readers`로 설정합니다.
과거 `metrics.address`, 독립 `rate_limiting` processor와 구형 `loki` exporter를 그대로 사용하지 않습니다.
배포 파일은 ConfigMap·Service·포트가 연결되어 있으며, 단일 인스턴스 실습이라 `Recreate`를
사용합니다. 업데이트는 buffer와 인메모리 queue를 잃을 수 있습니다.

| 항목 | 올바른 해석 |
|---|---|
| Head sampling | 시작 시점에 결정. 그때 알 수 없는 최종 오류·지연을 조건으로 보존할 수 없음 |
| Tail sampling | `decision_wait` 동안 받은 span을 보고 결정. 완전한 trace 수신을 보장하지 않음 |
| 오류/지연/baseline 정책 | 이 예제는 OR 결합. rate limit을 별도 정책으로 추가해도 전체 상한이 되지 않음 |
| `spans_per_second` | span/초. trace/초가 아니며 독립 processor 설정도 아님 |
| `num_traces` | 대기 trace buffer 크기. 초과·지연·재시작으로 데이터 손실 가능 |
| `send_batch_size` | 전송 trigger. 최대 배치 크기는 `send_batch_max_size` |

여러 tail sampler로 확장하려면 같은 trace의 span을 같은 sampler로 보내는 trace-ID 기반
라우팅이 필요합니다. 단순 Service의 무작위 분산은 trace를 나눌 수 있습니다.
Head 단계에서 버린 span은 tail 단계에서 복구할 수 없고, “모든 오류 trace를 보존”한다는
보장은 queue 한계·늦게 도착한 span·수신 실패를 포함하면 성립하지 않습니다.
`ERROR`와 `UNSET`은 다르며 `UNSET`을 오류 정책에 넣으면 정상 span까지 대량 보존할 수 있습니다.
서비스 그래프와 생성 메트릭은 샘플링 결과에 영향을 받으므로 전체 요청의 정확한 지표에는
별도의 직접 계측 메트릭을 사용합니다.

## TraceQL·서비스 그래프·로그 연결

아래는 개별 trace 검색입니다. `span:duration`은 span 지연이며 `trace:duration`과 다릅니다.
HTTP 속성은 SDK semantic conventions 버전에 따라 다릅니다. 앞 장에서 검증한 Go 계측은
`http.response.status_code`, Python 기본 계측은 `http.status_code`를 사용합니다.

```traceql
{ resource.service.name = "correlation-api" && span:status = error }
```

```traceql
{ resource.service.name = "correlation-api" && span:duration > 2s }
```

```traceql
{ resource.service.name = "api-gateway" } >> { resource.service.name = "order-service" }
```

```traceql
{ resource.service.name = "correlation-api" } | by(span:status) | count() > 1
```

`>>`는 descendant이며 직접 child는 `>`입니다. `| by(...) | count()`는 span 집합 집계이고,
TraceQL metrics의 `rate()` 등은 시간 시계열을 반환하므로 개별 trace 검색과 구별합니다.
이미 아는 trace ID는 Grafana trace ID 조회나 Tempo trace API로 찾습니다.
`{ trace:id = "abc123" }`처럼 잘못된 intrinsic과 불완전한 ID를 사용하지 않습니다.

위 Tempo 설정은 service-graphs와 span-metrics processor를 **배포 설정과 overrides 양쪽**에서
연결하고 Prometheus remote-write receiver로 전송합니다. service graph에는 적절한 client/server
SpanKind와 일치하는 서비스 이름이 필요합니다. `http.target`·전체 URL·user ID를 추가 dimension으로
넣으면 카디널리티가 커질 수 있습니다.

Java MDC/Logback, Go/Python의 유효한 trace ID와 exemplar는
[앞 장](./08-observability-analysis.md)의 검증된 예제를 재사용합니다. `is_recording()`이 false여도
유효한 비샘플링 trace context는 존재할 수 있습니다. 컨텍스트가 없다고 일반 로그를 버리지 않습니다.
MDC를 정리할 때도 다른 코드의 값을 모두 지우는 `MDC.clear()`를 피합니다.

## Prometheus와 Grafana

다음 `prometheus-values.yaml`은 kube-prometheus-stack용입니다. Tempo가 생성한 메트릭을
받는 remote-write receiver와 exemplar 저장을 켭니다. 수신 API 접근은 Tempo 등 신뢰하는
송신자로 제한해야 합니다. 앱 메트릭은 별도 scrape 대상/ServiceMonitor가 있어야 하며,
앞 장의 `correlation-api` 계측과 같은 label·metric 이름을 사용합니다.

Grafana 데이터 소스 UID `prometheus`·`loki`·`tempo`를 명시하고, `tracesToLogsV2`,
정확한 32자리 소문자 trace ID regex와 `$` escaping을 연결했습니다.
서비스 그래프는 `serviceMap`이 가리키는 Prometheus에 실제 생성 메트릭이 있어야 표시됩니다.

```yaml
# prometheus-values.yaml
prometheus:
  prometheusSpec:
    enableFeatures:
    - exemplar-storage
    exemplars:
      maxSize: 100000
    enableRemoteWriteReceiver: true
    retention: 7d
    walCompression: true
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: gp3
          accessModes:
          - ReadWriteOnce
          resources:
            requests:
              storage: 50Gi
grafana:
  sidecar:
    dashboards:
      enabled: true
      label: grafana_dashboard
      labelValue: '1'
      searchNamespace: observability
    datasources:
      enabled: true
      defaultDatasourceEnabled: false
      alertmanager:
        enabled: false
  additionalDataSources:
  - name: Prometheus
    uid: prometheus
    type: prometheus
    access: proxy
    url: http://prometheus-kube-prometheus-prometheus.observability.svc:9090
    jsonData:
      httpMethod: POST
      exemplarTraceIdDestinations:
      - name: trace_id
        datasourceUid: tempo
        urlDisplayLabel: View trace
    isDefault: true
  - name: Loki
    uid: loki
    type: loki
    access: proxy
    url: http://loki-gateway.observability.svc:80
    jsonData:
      derivedFields:
      - name: TraceID
        matcherRegex: '"trace_id"\s*:\s*"([0-9a-f]{32})"'
        datasourceUid: tempo
        url: $${__value.raw}
        urlDisplayLabel: View trace
  - name: Tempo
    uid: tempo
    type: tempo
    access: proxy
    url: http://tempo.observability.svc:3200
    jsonData:
      tracesToLogsV2:
        datasourceUid: loki
        spanStartTimeShift: -5m
        spanEndTimeShift: 5m
        tags:
        - key: service.name
          value: service_name
        filterByTraceID: true
        filterBySpanID: false
        customQuery: false
      tracesToMetrics:
        datasourceUid: prometheus
        spanStartTimeShift: -5m
        spanEndTimeShift: 5m
        tags:
        - key: service.name
          value: service
        queries:
        - name: Request rate
          query: sum(rate(http_requests_total{$$__tags}[5m]))
      serviceMap:
        datasourceUid: prometheus
```

```bash
helm upgrade --install prometheus prometheus-community/kube-prometheus-stack   --version 90.1.1 --namespace observability -f prometheus-values.yaml
```

Exemplar에는 계측 라이브러리의 trace/span 연결, OpenMetrics 노출, Prometheus 저장 기능,
Grafana UID mapping이 모두 필요합니다. HTTP/2나 histogram 활성화만으로 exemplar가 생성되지는 않습니다.
링크가 있어도 샘플링·보존·tenant·권한 차이로 trace가 없을 수 있습니다.

대시보드 자동화에서는 sidecar가 선택하는 ConfigMap의 값에 **dashboard JSON 본문**을 넣습니다.
API 응답의 `dashboard` wrapper나 provider YAML을 dashboard JSON으로 넣지 않습니다.
위 값은 `grafana_dashboard: "1"` 레이블을 가진 `observability` ConfigMap을 선택합니다.
provider 경로·mount를 직접 관리하는 방식과 sidecar 방식을 중복 설정하지 않습니다.
앞 장의 완전한 dashboard JSON을 이 ConfigMap에 넣을 수 있습니다.

## AMP: 별도 writer·reader 권한

AMP는 Prometheus 호환 저장/조회 서비스입니다. 별도 수집기/managed collector 설정 없이
클러스터 메트릭을 자동 수집하지 않습니다. 아래 Terraform은 workspace와 IRSA writer/reader
역할을 만듭니다. EKS OIDC provider는 이미 존재해야 합니다.
CloudWatch 메트릭도 별도 경로 없이 AMP에 자동 포함되지 않습니다.

```hcl
# amp.tf
terraform {
  required_version = ">= 1.15.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.64.0"
    }
  }
}

provider "aws" {
  region = var.region
}

variable "region" {
  type    = string
  default = "ap-northeast-2"
}

variable "oidc_provider_arn" {
  type = string
}

variable "oidc_issuer" {
  type        = string
  description = "EKS OIDC issuer without https:// or a trailing slash."
  validation {
    condition     = can(regex("^oidc\\.eks\\.[a-z0-9-]+\\.amazonaws\\.com/id/[A-Za-z0-9]+$", var.oidc_issuer))
    error_message = "Use the cluster's exact OIDC issuer host/path without https://."
  }
}

resource "aws_prometheus_workspace" "docs" {
  alias = "docs-observability"
}

locals {
  clients = {
    writer = {
      service_account = "prometheus-amp"
      actions         = ["aps:RemoteWrite"]
    }
    reader = {
      service_account = "grafana-amp"
      actions         = ["aps:QueryMetrics", "aps:GetLabels", "aps:GetSeries", "aps:GetMetricMetadata"]
    }
  }
}

resource "aws_iam_role" "amp" {
  for_each = local.clients
  name     = "docs-amp-${each.key}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = var.oidc_provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${var.oidc_issuer}:sub" = "system:serviceaccount:observability:${each.value.service_account}"
          "${var.oidc_issuer}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "amp" {
  for_each = local.clients
  role     = aws_iam_role.amp[each.key].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = each.value.actions
      Resource = aws_prometheus_workspace.docs.arn
    }]
  })
}

output "workspace_id" {
  value = aws_prometheus_workspace.docs.id
}

output "workspace_endpoint" {
  value = aws_prometheus_workspace.docs.prometheus_endpoint
}

output "client_role_arns" {
  value = { for k, v in aws_iam_role.amp : k => v.arn }
}
```

`oidc_provider_arn`과 scheme 없는 `oidc_issuer`는 같은 EKS 클러스터의 값이어야 합니다.
writer의 subject는 `observability:prometheus-amp`, reader는 `observability:grafana-amp`이며
`aud=sts.amazonaws.com`도 제한합니다. 정책은 이 workspace ARN만 대상으로 합니다.
Grafana IAM 역할에 `QueryMetrics`를 빼고 RemoteWrite만 부여하면 조회할 수 없습니다.

아래는 기본 `prometheus-values.yaml`에 추가할 `amp-values.yaml`의 핵심입니다.
Grafana의 `additionalDataSources` 리스트는 Helm merge에서 **전체 교체**되므로 기본 세
데이터 소스를 유지한 뒤 AMP 항목을 추가합니다. 예제는 로컬 Prometheus도 계속 사용합니다.

```yaml
prometheus:
  serviceAccount:
    create: true
    name: prometheus-amp
    annotations:
      eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/docs-amp-writer
  prometheusSpec:
    replicas: 2
    replicaExternalLabelName: __replica__
    externalLabels:
      cluster: production-seoul-prometheus
    remoteWrite:
    - url: https://aps-workspaces.ap-northeast-2.amazonaws.com/workspaces/REPLACE_WORKSPACE_ID/api/v1/remote_write
      sigv4:
        region: ap-northeast-2
      queueConfig:
        maxSamplesPerSend: 1000
        capacity: 5000
        maxShards: 20
grafana:
  serviceAccount:
    create: true
    name: grafana-amp
    annotations:
      eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/docs-amp-reader
  env:
    GF_AUTH_SIGV4_AUTH_ENABLED: 'true'
  additionalDataSources:
  - name: AMP
    uid: amp
    type: prometheus
    access: proxy
    url: https://aps-workspaces.ap-northeast-2.amazonaws.com/workspaces/REPLACE_WORKSPACE_ID/
    jsonData:
      httpMethod: POST
      sigV4Auth: true
      sigV4AuthType: default
      sigV4Region: ap-northeast-2
```

위 조각을 `amp-overlay.yaml`에 저장한 뒤, PyYAML이 설치된 환경에서 다음처럼 리스트를 합칩니다.
프로그램은 일반적인 Helm merge를 재구현하지 않으며 데이터 소스 목록 한 곳만 명시적으로 합칩니다.
실제 IAM role ARN과 workspace endpoint도 적용 전에 변경합니다.

```python
import yaml
from pathlib import Path

base = yaml.safe_load(Path("prometheus-values.yaml").read_text())
overlay = yaml.safe_load(Path("amp-overlay.yaml").read_text())
overlay["grafana"]["additionalDataSources"] = (
    base["grafana"]["additionalDataSources"]
    + overlay["grafana"]["additionalDataSources"]
)
Path("amp-values.yaml").write_text(yaml.safe_dump(overlay, sort_keys=False))
```

```bash
helm template prometheus prometheus-community/kube-prometheus-stack   --version 90.1.1 --namespace observability   -f prometheus-values.yaml -f amp-values.yaml > amp-rendered.yaml
```

### HA·queue·보존

AMP HA 중복 제거는 `cluster`와 `__replica__` 레이블을 사용합니다.
같은 데이터의 복제본은 같은 `cluster`, 서로 다른 `__replica__`를 가져야 합니다.
다른 scrape 범위의 독립 Prometheus를 같은 HA 그룹으로 묶으면 데이터가 빠질 수 있습니다.
metric 자체가 가진 `cluster` 레이블 충돌도 확인합니다. 다중 클러스터는 workspace와
HA 그룹 레이블을 계획해 구분하며, workspace 여러 개가 자동 federation되는 것은 아닙니다.

remote-write queue의 shard·capacity는 처리량과 메모리에 영향을 줍니다.
WAL과 retry가 있어도 무한한 버퍼나 전달 보장은 아닙니다. `retention: 7d`가
remote-write 장애 7일을 항상 재생한다는 뜻도 아닙니다.
전송 지연·실패·거부·WAL 상태를 관찰하고 복구 시험을 합니다.
namespace keep 필터는 namespace가 없는 node·cluster 메트릭을 제거할 수 있고,
`labeldrop`은 서로 다른 시계열을 충돌시킬 수 있습니다.
recording rule은 추가 집계 시계열을 만들며 원본 카디널리티를 자동 제거하지 않습니다.

AMP 보존 기간은 workspace에서 변경할 수 있으며 최대 **1,095일**입니다.
“150일이 하드 한도라 그 이상은 반드시 Thanos”라는 기준은 잘못되었습니다.
보존을 늘려도 이미 만료된 메트릭이 복구되지는 않습니다.

| 항목 | AMP | Thanos |
|---|---|---|
| 저장·운영 | 서비스가 저장 계층 운영; 수집·IAM·쿼터·비용·규칙은 사용자 책임 | 객체 저장소와 query/store/compactor 등 구성 요소 운영 |
| 보존 | workspace 설정과 서비스 한도 | compactor 정책·객체 저장소·예산에 따른 구성 |
| HA·다중 클러스터 | 명시적 HA 레이블과 workspace 설계 | replica label·dedup·store 연결 설계 |
| Downsampling | Thanos 방식의 자동 downsampling을 전제로 하지 않음 | compactor의 해상도/보존 설정과 query 동작 검토 |

SigV4는 AWS 요청 인증이며 TLS 암호화를 대신하지 않습니다.
Grafana 프로세스의 SigV4 활성화·자격 증명·IRSA trust·workspace 읽기 권한을 함께 검증합니다.
Amazon Managed Grafana와 자체 설치 Grafana의 역할 연결 절차도 구별합니다.

## 적용 후 확인

1. rendered manifest의 image·PVC·Service 포트·ConfigMap mount·ServiceAccount가 의도와 일치하는지 확인합니다.
2. 로그 한 줄, trace 하나, 직접 계측 메트릭 하나를 각 backend에서 먼저 조회합니다.
3. Grafana의 trace→log, log→trace, exemplar→trace 링크와 tenant·시간 범위를 확인합니다.
4. Collector 재시작, Kafka 재생, S3 권한 거부, remote-write 중단과 복구를 비운영 환경에서 시험합니다.
5. Loki 보존 삭제와 Tempo block maintenance가 진행되는지, 경고·quota·비용을 점검합니다.

이 장의 검토에서는 버전 고정 차트 렌더링, Loki/Tempo/Collector/Alloy의 실제 설정 파서,
생성된 PVC·Service·identity 연결과 Terraform mock 테스트를 사용했습니다.
실제 EKS/Kafka/S3 배포나 Grafana 로그인·AWS 쓰기/조회 성공을 시험한 것은 아닙니다.

## 공식 자료

- [Loki deployment modes](https://grafana.com/docs/loki/latest/get-started/deployment-modes/)
- [Loki retention](https://grafana.com/docs/loki/latest/operations/storage/retention/)
- [Grafana community Helm charts](https://github.com/grafana-community/helm-charts)
- [Promtail lifecycle](https://grafana.com/docs/loki/latest/send-data/promtail/)
- [Tempo 3 migration](https://grafana.com/docs/tempo/latest/set-up-for-tracing/setup-tempo/migrate-to-3/)
- [Tempo 3.0.3 Kafka configuration](https://github.com/grafana/tempo/blob/v3.0.3/pkg/ingest/config.go)
- [Collector tail sampling](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.160.0/processor/tailsamplingprocessor)
- [Collector batch processor](https://github.com/open-telemetry/opentelemetry-collector/tree/v0.160.0/processor/batchprocessor)
- [AMP workspace configuration](https://docs.aws.amazon.com/prometheus/latest/userguide/AMP-workspace-configuration.html)
- [AMP high availability](https://docs.aws.amazon.com/prometheus/latest/userguide/Send-high-availability-data.html)

---

< [이전: Observability 분석](./08-observability-analysis.md) | [목차](./README.md) | [다음: 리소스 최적화](./10-resource-optimization.md) >
