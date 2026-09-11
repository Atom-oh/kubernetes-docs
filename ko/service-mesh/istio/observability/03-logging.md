# Istio 로깅 (Logging)

> **지원 버전**: Istio 1.31
> **검토일**: 2026년 9월 11일

> **검증 범위**: 실습 설정은 공식 자료와 오프라인 검증기로 확인했으며 클러스터에 배포해 실행하지 않았습니다. 각 예제의 네임스페이스·신원·스토리지·백엔드·부하 전제 조건은 대상 환경에서 확인해야 합니다.

설정한 access log는 관측한 요청·연결의 메타데이터를 기록합니다. Envoy/istiod 진단·애플리케이션 로그와 별도이며 메시 전체 활동이나 요청·응답 본문 전체를 기록하지 않습니다. 예제는 사이드카 기준입니다. Ambient L7 로깅은 waypoint 연결이 필요하며 ztunnel은 별도 L4 로그를 제공합니다.

## 목차

1. [로깅 개요](#로깅-개요)
2. [Access Log 설정](#access-log-설정)
3. [Telemetry API로 로그 커스터마이징](#telemetry-api로-로그-커스터마이징)
4. [로그 필터링 및 샘플링](#로그-필터링-및-샘플링)
5. [Envoy 로그 레벨 조정](#envoy-로그-레벨-조정)
6. [Alloy + Loki 통합](#alloy--loki-통합)
7. [Grafana 로그 대시보드](#grafana-로그-대시보드)
8. [로그와 메트릭/트레이스 연동](#로그와-메트릭트레이스-연동)
9. [성능 최적화](#성능-최적화)
10. [문제 해결](#문제-해결)

## 로깅 개요

### Istio 로그 계층

Envoy → 구조화된 stdout → Alloy Kubernetes 로그 수집 → Loki → Grafana 순서입니다. 대안으로 Envoy OTLP access-log 제공자에서 OpenTelemetry Collector로 전송할 수 있습니다. 같은 로그에는 한 전송 경로를 선택해 중복을 피합니다. Istiod는 Telemetry·제공자 설정을 배포합니다.

### 로그 유형

1. **Access Log**: 설정한 HTTP 요청 또는 TCP 연결 메타데이터
2. **Envoy Proxy Log**: Envoy 내부 동작 로그
3. **Istiod Log**: 컨트롤 플레인 로그
4. **Application Log**: 애플리케이션 자체 로그

## Access Log 설정

### 1. Access-Log 제공자 정의

다음 제공자 중 하나를 기존 Istio 설치 설정에 병합하고 `istioctl install -f logging-install.yaml`로 적용합니다. 다른 메시 설정·제공자는 유지합니다. 이는 Kubernetes IstioOperator 리소스가 아닌 설치 입력입니다. 아래 Telemetry에서 설치된 제공자를 선택하며 텍스트·JSON은 대안 형식입니다.

#### 기본 텍스트 포맷

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: logging
spec:
  meshConfig:
    extensionProviders:
    - name: mesh-text
      envoyFileAccessLog:
        path: /dev/stdout
        logFormat:
          text: '[%START_TIME%] "%REQ(:METHOD)% %REQ_WITHOUT_QUERY(:PATH)% %PROTOCOL%" %RESPONSE_CODE%
            %RESPONSE_FLAGS% %DURATION% trace=%TRACE_ID% request=%REQ(X-REQUEST-ID)%'
```

#### JSON 포맷 (Loki 예제에서 사용)

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: logging
spec:
  meshConfig:
    extensionProviders:
    - name: mesh-json
      envoyFileAccessLog:
        path: /dev/stdout
        logFormat:
          labels:
            log_type: access
            start_time: '%START_TIME%'
            method: '%REQ(:METHOD)%'
            path: '%REQ_WITHOUT_QUERY(X-ENVOY-ORIGINAL-PATH?:PATH)%'
            protocol: '%PROTOCOL%'
            response_code: '%RESPONSE_CODE%'
            response_code_details: '%RESPONSE_CODE_DETAILS%'
            response_flags: '%RESPONSE_FLAGS%'
            bytes_received: '%BYTES_RECEIVED%'
            bytes_sent: '%BYTES_SENT%'
            duration: '%DURATION%'
            request_id: '%REQ(X-REQUEST-ID)%'
            trace_id: '%TRACE_ID%'
            authority: '%REQ(:AUTHORITY)%'
            upstream_host: '%UPSTREAM_HOST%'
            upstream_cluster: '%UPSTREAM_CLUSTER%'
            route_name: '%ROUTE_NAME%'
            downstream_tls_version: '%DOWNSTREAM_TLS_VERSION%'
            peer_uri_san: '%DOWNSTREAM_PEER_URI_SAN%'
```

JSON 필드는 제공자 형식에서 만들고 Telemetry 필터는 기록할 이벤트를 선택합니다. 로그의 `duration`은 밀리초이고 CEL `request.duration`은 duration 타입입니다. `trace_id`는 추적 제공자가 제공하는 실제 trace ID이며 `request_id`는 별도 요청 상관관계 값입니다. 쿼리 문자열은 제외하고 추가 헤더는 기록 전에 검토합니다.

로깅 변경은 프록시 설정으로 전달되며 전체 istiod·워크로드 재시작이 일반적인 활성화 단계는 아닙니다. 실제 listener와 테스트 요청을 확인합니다. 뒤의 bootstrap 로그 레벨 변경에는 대상 프록시 교체가 필요합니다.

### 2. Telemetry API로 세밀한 제어

Telemetry는 네임스페이스·워크로드별 로깅을 선택합니다. 예제는 대안이며 네임스페이스마다 selector 없는 리소스 하나에 병합합니다. 이 문서는 서비스 inbound 로그에 SERVER 모드를 사용해 송신·수신 중복 집계를 피합니다. 게이트웨이·outbound 진단은 별도 CLIENT 정책을 사용할 수 있으며 서비스 요청률에 섞어 계산하지 않습니다. 텍스트 형식은 `mesh-json` 대신 `mesh-text` 제공자를 선택합니다.

#### 전체 메시에 JSON Access Log 활성화

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: mesh-logging
  namespace: istio-system
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
```

#### 네임스페이스별 로그 설정

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: production-logging
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    # 에러와 느린 요청만 로깅
    filter:
      expression: |
        response.code >= 400 ||
        request.duration > duration("1s")
```

#### 워크로드별 상세 로깅

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: payment-service-logging
  namespace: production
spec:
  selector:
    matchLabels:
      app: payment-service
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    # 모든 요청 로깅 + 추가 커스텀 필드
    filter:
      expression: "true"
```

## Telemetry API로 로그 커스터마이징

### 커스텀 로그 제공자 (Custom Log Provider)

#### 1. OpenTelemetry로 로그 전송

같은 stdout 로그를 Alloy로 수집하는 방식의 대안입니다. 제공자를 설치한 뒤 네임스페이스 Telemetry에서 선택합니다:

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: logging
spec:
  meshConfig:
    extensionProviders:
    - name: otel-logging
      envoyOtelAls:
        service: otel-collector.observability.svc.cluster.local
        port: 4317
        logFormat:
          text: '%REQ(:METHOD)% %REQ_WITHOUT_QUERY(:PATH)% %RESPONSE_CODE%'
          labels:
            log_type: access
            start_time: '%START_TIME%'
            method: '%REQ(:METHOD)%'
            path: '%REQ_WITHOUT_QUERY(X-ENVOY-ORIGINAL-PATH?:PATH)%'
            protocol: '%PROTOCOL%'
            response_code: '%RESPONSE_CODE%'
            response_code_details: '%RESPONSE_CODE_DETAILS%'
            response_flags: '%RESPONSE_FLAGS%'
            bytes_received: '%BYTES_RECEIVED%'
            bytes_sent: '%BYTES_SENT%'
            duration: '%DURATION%'
            request_id: '%REQ(X-REQUEST-ID)%'
            trace_id: '%TRACE_ID%'
            authority: '%REQ(:AUTHORITY)%'
            upstream_host: '%UPSTREAM_HOST%'
            upstream_cluster: '%UPSTREAM_CLUSTER%'
            route_name: '%ROUTE_NAME%'
            downstream_tls_version: '%DOWNSTREAM_TLS_VERSION%'
            peer_uri_san: '%DOWNSTREAM_PEER_URI_SAN%'
```

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: otel-access-logging
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: otel-logging
```

[추적 가이드](02-tracing.md)의 collector에는 OTLP receiver, memory limiter, batch processor가 정의되어 있습니다. 다음 logs pipeline·exporter를 기존 설정에 병합하고 재로드·재배포합니다. Loki 3.7.7은 `/otlp/v1/logs`에서 OTLP/HTTP 로그를 받으며 exporter가 `/v1/logs`를 덧붙입니다. TSDB v13은 structured metadata를 지원합니다. OTLP 속성은 stdout JSON 본문이 아닌 메타데이터가 되므로 `| json` 쿼리를 그대로 사용하지 말고 맞춰야 합니다.

```yaml
exporters:
  otlp_http/loki:
    endpoint: http://loki.observability.svc.cluster.local:3100/otlp
service:
  pipelines:
    logs:
      receivers:
      - otlp
      processors:
      - memory_limiter
      - batch
      exporters:
      - otlp_http/loki
```

#### 2. 파일 로깅과 공유 볼륨

제공자의 파일 경로만으로 볼륨이 생성·마운트되지 않습니다. 선택적인 아래 예제는 크기가 제한된 `emptyDir`을 주입된 프록시에 마운트하며 애플리케이션 이미지를 교체해야 합니다. 별도 reader가 같은 볼륨을 마운트하고 순환·전송을 처리해야 합니다. 파일은 `kubectl logs`에 나오지 않으며 파드가 사라지면 `emptyDir`도 사라집니다. 이 문서의 기본 수집 예제는 stdout을 사용합니다.

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: logging
spec:
  meshConfig:
    extensionProviders:
    - name: envoy-file-logger
      envoyFileAccessLog:
        path: /var/log/istio/access.log
        logFormat:
          labels:
            log_type: access
            start_time: '%START_TIME%'
            method: '%REQ(:METHOD)%'
            path: '%REQ_WITHOUT_QUERY(X-ENVOY-ORIGINAL-PATH?:PATH)%'
            protocol: '%PROTOCOL%'
            response_code: '%RESPONSE_CODE%'
            response_code_details: '%RESPONSE_CODE_DETAILS%'
            response_flags: '%RESPONSE_FLAGS%'
            bytes_received: '%BYTES_RECEIVED%'
            bytes_sent: '%BYTES_SENT%'
            duration: '%DURATION%'
            request_id: '%REQ(X-REQUEST-ID)%'
            trace_id: '%TRACE_ID%'
            authority: '%REQ(:AUTHORITY)%'
            upstream_host: '%UPSTREAM_HOST%'
            upstream_cluster: '%UPSTREAM_CLUSTER%'
            route_name: '%ROUTE_NAME%'
            downstream_tls_version: '%DOWNSTREAM_TLS_VERSION%'
            peer_uri_san: '%DOWNSTREAM_PEER_URI_SAN%'
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: file-logging-example
  namespace: production
  labels:
    app: file-logging-example
  annotations:
    sidecar.istio.io/inject: 'true'
    sidecar.istio.io/userVolumeMount: '[{"name":"istio-logs","mountPath":"/var/log/istio"}]'
spec:
  securityContext:
    fsGroup: 1337
  containers:
  - name: app
    image: registry.example.com/team/app:REPLACE_WITH_TESTED_TAG
  volumes:
  - name: istio-logs
    emptyDir:
      sizeLimit: 100Mi
---
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: file-logging
  namespace: production
spec:
  selector:
    matchLabels:
      app: file-logging-example
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: envoy-file-logger
```

### 로그 포맷 커스터마이징

#### CEL 이벤트 필터링

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: custom-log-format
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: "true"
```

**사용 가능한 변수**:

| 변수 | 설명 | 예제 |
|------|------|------|
| `request.method` | HTTP 메서드 | GET, POST |
| `request.path` | 요청 경로 | /api/v1/users |
| `request.url_path` | URL 경로 (쿼리 제외) | /api/v1/users |
| `request.headers` | 요청 헤더 | `request.headers['user-agent']` |
| `response.code` | HTTP 상태 코드 | 200, 404, 500 |
| `response.headers` | 응답 헤더 | `response.headers['content-type']` |
| `response.flags` | 정수 bitmask | `response.flags != 0` |
| `request.duration` | 요청 duration 값 | `duration("1s")` |
| `connection.mtls` | mTLS 사용 여부 | true, false |
| `connection.uri_san_peer_certificate` | 제공되는 경우 downstream peer URI SAN | spiffe://... |
| `connection.uri_san_local_certificate` | downstream 로컬 인증서 URI SAN | spiffe://... |

## 로그 필터링 및 샘플링

### 1. 조건부 로깅

#### 에러와 느린 요청만 로깅

HTTP 속성 필터는 HTTP 트래픽용입니다. TCP 로깅은 connection 속성 또는 HTTP 필드 누락을 처리하는 표현식을 사용합니다. CEL은 이벤트를 선택하며 JSON 필드 형식을 정의하지 않습니다.

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: error-slow-logging
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: |
        response.code >= 400 ||
        response.code == 0 ||
        request.duration > duration("1s")
```

#### 특정 경로 제외

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: filter-health-checks
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: |
        !(request.url_path.startsWith('/health') ||
          request.url_path.startsWith('/ready') ||
          request.url_path.startsWith('/live') ||
          request.url_path == '/metrics')
```

#### HTTP 메서드 필터링

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: critical-methods-only
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: |
        request.method in ['POST', 'PUT', 'DELETE', 'PATCH']
```

#### mTLS가 아닌 트래픽만 로깅 (보안 감사)

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: non-mtls-logging
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: |
        !connection.mtls
```

### 2. Collector에서 샘플링

지원되는 Alloy `stage.sampling`을 사용합니다. Telemetry CEL 인터페이스에는 문서화된 `random()` 샘플링 함수가 없습니다. 균일하게 10%를 보관하려면 `loki.process`에 다음 stage를 넣습니다:

```alloy
stage.sampling {
  rate = 0.1
  drop_counter_reason = "uniform_sampling"
}
```

오류·느린·분류 불가 로그는 유지하고 성공·1초 미만 access log의 1%만 보관하려면 JSON 제공자의 정수 필드를 읽어 임시 레이블로 분류·샘플링한 뒤 쓰기 전에 제거합니다. 기본 process stage를 다음 대안으로 교체하고 `forward_to`는 유지합니다:

```alloy
stage.json {
  expressions = { log_type = "log_type", response_code = "response_code", duration = "duration" }
}
stage.labels {
  values = { log_type = "log_type", sample_status = "response_code", sample_duration_ms = "duration" }
}
stage.match {
  selector = "{log_type=\"access\", sample_status=~\"[123][0-9]{2}\", sample_duration_ms=~\"[0-9]{1,3}\"}"
  stage.sampling {
    rate = 0.01
    drop_counter_reason = "normal_access_sampled"
  }
}
stage.label_drop {
  values = ["sample_status", "sample_duration_ms"]
}
```

`stage.match`는 stream selector·line filter를 지원하지만 전체 LogQL label-filter pipeline은 지원하지 않습니다. 임시 duration 레이블은 Loki에 저장되지 않습니다. Collector 샘플링은 수집·저장량을 줄이며 프록시 로그 생성 비용은 줄이지 않습니다. 보관된 로그의 수·분위수·에러율은 편향되므로 전체 트래픽 SLI에는 비샘플링 Istio 메트릭을 사용하고 아래 로그 대시보드·알림은 비샘플링 access log를 전제합니다.

### 3. 네임스페이스별 차등 로깅

```yaml
# Production: 에러만 로깅
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: production-logging
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: "response.code >= 400"
---
# Staging: 모든 요청 로깅
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: staging-logging
  namespace: staging
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: "true"
---
# Development: 로깅 비활성화
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: dev-logging
  namespace: development
spec:
  accessLogging:
  - disabled: true
```

## Envoy 로그 레벨 조정

### 동적으로 로그 레벨 변경

#### 전체 Envoy 로그 레벨

```bash
# Debug 레벨로 변경
istioctl proxy-config log <pod-name> -n <namespace> --level debug

# Info 레벨로 복구
istioctl proxy-config log <pod-name> -n <namespace> --level info

# Warning 레벨로 변경
istioctl proxy-config log <pod-name> -n <namespace> --level warning
```

#### 컴포넌트별 로그 레벨

```bash
# HTTP 연결만 debug
istioctl proxy-config log <pod-name> -n <namespace> --level http:debug

# Router와 Connection 컴포넌트만 debug
istioctl proxy-config log <pod-name> -n <namespace> --level router:debug,connection:debug

# 여러 컴포넌트 조합
istioctl proxy-config log <pod-name> -n <namespace> \
  --level http:debug,router:info,upstream:debug,connection:trace
```

`istioctl proxy-config log <pod-name> -n <namespace>`로 해당 프록시 버전이 지원하는 컴포넌트를 조회합니다. 모든 빌드가 아래 예시 전체를 노출하지는 않습니다.

### 주요 Envoy 로그 컴포넌트

| 컴포넌트 | 설명 | 사용 사례 |
|----------|------|-----------|
| `admin` | Admin 인터페이스 | Admin API 디버깅 |
| `aws` | AWS 통합 | AWS 서비스 문제 |
| `connection` | TCP 연결 | 연결 문제 디버깅 |
| `filter` | HTTP 필터 | 필터 체인 분석 |
| `forward_proxy` | Forward 프록시 | 프록시 동작 추적 |
| `grpc` | gRPC | gRPC 통신 문제 |
| `hc` | Health check | Health check 실패 |
| `http` | HTTP | HTTP 요청/응답 추적 |
| `http2` | HTTP/2 | HTTP/2 프로토콜 이슈 |
| `jwt` | JWT 인증 | JWT 토큰 검증 |
| `lua` | Lua 스크립트 | Lua 필터 디버깅 |
| `main` | 메인 로직 | 일반적인 Envoy 동작 |
| `router` | 라우팅 | 라우팅 결정 추적 |
| `runtime` | 런타임 구성 | 동적 구성 변경 |
| `upstream` | Upstream 클러스터 | Backend 연결 문제 |
| `client` | HTTP 클라이언트 | 아웃바운드 요청 |
| `pool` | 연결 풀 | 연결 풀 관리 |
| `rbac` | RBAC 필터 | 권한 문제 디버깅 |

### 영구적인 로그 레벨 설정

다음 설치 값을 병합하고 대상 프록시를 순차 교체합니다. 임시 변경 전 기존 컴포넌트 레벨을 조회하고 이후 원래 값으로 복구합니다. 로그 레벨이 access logging을 활성화하지는 않습니다.

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: proxy-log-levels
spec:
  values:
    global:
      proxy:
        logLevel: info
        componentLogLevel: http:debug,router:info,upstream:debug
```

### 특정 워크로드에만 디버그 로그 적용

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-app
  annotations:
    sidecar.istio.io/componentLogLevel: "http:debug,router:debug"
    sidecar.istio.io/logLevel: "debug"
spec:
  containers:
  - name: app
    image: registry.example.com/team/my-app:REPLACE_WITH_TESTED_TAG
```

## Alloy + Loki 통합

Promtail은 **2026년 3월 2일** 지원이 종료되었습니다. 새 배포에는 Alloy 또는 지원되는 클라이언트를 사용합니다. 아래는 기존 Promtail 파일 tail 설정을 Alloy의 Kubernetes API 로그 수집으로 대체하며 Docker 경로·privileged 컨테이너·노드 파일시스템 마운트가 필요하지 않습니다.

### 1. Loki 설치 (Single Binary)

Loki 3.7.7, TSDB v13, filesystem 저장소를 사용하는 새 단일 replica·tenant 예제입니다. Simple Scalable 모드가 아닌 **single binary**입니다. 먼저 `observability` 네임스페이스를 생성합니다. EKS에서는 정상 EBS CSI driver와 `gp3` StorageClass가 필요하며 다른 플랫폼은 해당 영속 StorageClass를 사용합니다. Fargate는 EBS 볼륨을 마운트할 수 없으므로 Loki 저장소는 적합한 EC2 노드 또는 외부 지원 서비스에서 실행합니다.

`auth_enabled: false`에서는 네트워크 접근자가 tenant 로그에 접근할 수 있습니다. Endpoint를 비공개로 두고 운영에는 지원되는 인증 gateway·TLS를 구성합니다. 기존 Loki 업그레이드 시 과거 schema 항목을 보존합니다. 아래 2024년 schema 시작일은 유효하며 릴리스 날짜가 아닙니다. Compactor 보존에는 영속 상태와 `delete_request_store`가 필요합니다.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: loki-config
  namespace: observability
data:
  loki.yaml: |
    auth_enabled: false
    server:
      http_listen_port: 3100
      grpc_listen_port: 9096
    common:
      path_prefix: /loki
      storage:
        filesystem:
          chunks_directory: /loki/chunks
          rules_directory: /loki/rules
      replication_factor: 1
      ring:
        kvstore:
          store: inmemory
    schema_config:
      configs:
      - from: 2024-01-01
        store: tsdb
        object_store: filesystem
        schema: v13
        index:
          prefix: index_
          period: 24h
    limits_config:
      retention_period: 168h
      ingestion_rate_mb: 16
      ingestion_burst_size_mb: 32
      max_query_length: 721h
      max_query_lookback: 721h
      max_streams_per_user: 10000
      max_global_streams_per_user: 0
      reject_old_samples: true
      reject_old_samples_max_age: 168h
    compactor:
      working_directory: /loki/compactor
      compaction_interval: 10m
      retention_enabled: true
      retention_delete_delay: 2h
      retention_delete_worker_count: 150
      delete_request_store: filesystem
    querier:
      max_concurrent: 4
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: loki
  namespace: observability
spec:
  serviceName: loki-headless
  replicas: 1
  selector:
    matchLabels:
      app: loki
  template:
    metadata:
      labels:
        app: loki
        sidecar.istio.io/inject: 'false'
    spec:
      containers:
      - name: loki
        image: grafana/loki:3.7.7
        args:
        - -config.file=/etc/loki/loki.yaml
        ports:
        - containerPort: 3100
          name: http
        - containerPort: 9096
          name: grpc
        volumeMounts:
        - name: config
          mountPath: /etc/loki
        - name: storage
          mountPath: /loki
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 4Gi
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          initialDelaySeconds: 10
          periodSeconds: 10
      volumes:
      - name: config
        configMap:
          name: loki-config
      securityContext:
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001
        runAsNonRoot: true
  volumeClaimTemplates:
  - metadata:
      name: storage
    spec:
      accessModes:
      - ReadWriteOnce
      resources:
        requests:
          storage: 100Gi
      storageClassName: gp3
---
apiVersion: v1
kind: Service
metadata:
  name: loki
  namespace: observability
spec:
  selector:
    app: loki
  ports:
  - name: http
    port: 3100
    targetPort: 3100
  - name: grpc
    port: 9096
    targetPort: 9096
  type: ClusterIP
---
apiVersion: v1
kind: Service
metadata:
  name: loki-headless
  namespace: observability
spec:
  clusterIP: None
  selector:
    app: loki
  ports:
  - name: http
    port: 3100
    targetPort: http
```

### 2. Alloy로 Pod 로그 수집

RoleBinding 적용 전에 아래 애플리케이션 네임스페이스를 생성하거나 검색·binding을 실제 네임스페이스로 줄입니다. Alloy는 해당 네임스페이스의 파드 메타데이터와 `pods/log`만 읽습니다. API source는 CRI/Docker wrapper가 제거된 컨테이너 로그를 받습니다. 파일 source를 사용하면 런타임 파싱과 노드별 실제 파일 경로가 필요합니다.

단일 replica 예제는 init 컨테이너를 제외하고 사이드카·istiod·애플리케이션 로그를 수집합니다. Namespace/pod/container/app/version과 제한된 `log_type`만 레이블로 사용하며 request ID·trace ID·path·duration은 Loki index label이 아닌 필드로 유지합니다. 앞의 JSON 제공자가 `log_type="access"`를 출력하므로 같은 컨테이너의 프록시 진단 로그와 구분됩니다.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: alloy
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: alloy-pod-logs
rules:
- apiGroups:
  - ''
  resources:
  - pods
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - ''
  resources:
  - pods/log
  verbs:
  - get
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: alloy-pod-logs
  namespace: default
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: alloy-pod-logs
subjects:
- kind: ServiceAccount
  name: alloy
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: alloy-pod-logs
  namespace: app
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: alloy-pod-logs
subjects:
- kind: ServiceAccount
  name: alloy
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: alloy-pod-logs
  namespace: production
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: alloy-pod-logs
subjects:
- kind: ServiceAccount
  name: alloy
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: alloy-pod-logs
  namespace: staging
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: alloy-pod-logs
subjects:
- kind: ServiceAccount
  name: alloy
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: alloy-pod-logs
  namespace: istio-system
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: alloy-pod-logs
subjects:
- kind: ServiceAccount
  name: alloy
  namespace: observability
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: alloy-config
  namespace: observability
data:
  config.alloy: |
    discovery.kubernetes "pods" {
      role = "pod"
      namespaces {
        names = ["default", "app", "production", "staging", "istio-system"]
      }
    }

    discovery.relabel "logs" {
      targets = discovery.kubernetes.pods.targets
      rule {
        source_labels = ["__meta_kubernetes_pod_phase"]
        regex = "Running"
        action = "keep"
      }
      rule {
        source_labels = ["__meta_kubernetes_pod_container_name"]
        regex = "istio-init"
        action = "drop"
      }
      rule {
        source_labels = ["__meta_kubernetes_namespace"]
        target_label = "namespace"
      }
      rule {
        source_labels = ["__meta_kubernetes_pod_name"]
        target_label = "pod"
      }
      rule {
        source_labels = ["__meta_kubernetes_pod_container_name"]
        target_label = "container"
      }
      rule {
        source_labels = ["__meta_kubernetes_pod_label_app"]
        target_label = "app"
      }
      rule {
        source_labels = ["__meta_kubernetes_pod_label_version"]
        target_label = "version"
      }
    }

    loki.source.kubernetes "pods" {
      targets = discovery.relabel.logs.output
      forward_to = [loki.process.logs.receiver]
    }

    loki.process "logs" {
      stage.json {
        expressions = { log_type = "log_type" }
      }
      stage.labels {
        values = { log_type = "log_type" }
      }
      forward_to = [loki.write.local.receiver]
    }

    loki.write "local" {
      endpoint {
        url = "http://loki.observability.svc.cluster.local:3100/loki/api/v1/push"
        batch_wait = "1s"
        batch_size = "1MiB"
        min_backoff_period = "500ms"
        max_backoff_period = "5m"
        max_backoff_retries = 10
        remote_timeout = "10s"
      }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: alloy
  namespace: observability
spec:
  replicas: 1
  selector:
    matchLabels:
      app: alloy
  template:
    metadata:
      labels:
        app: alloy
        sidecar.istio.io/inject: 'false'
    spec:
      serviceAccountName: alloy
      containers:
      - name: alloy
        image: grafana/alloy:v1.19.2
        args:
        - run
        - --server.http.listen-addr=0.0.0.0:12345
        - --storage.path=/var/lib/alloy
        - /etc/alloy/config.alloy
        ports:
        - containerPort: 12345
          name: http-metrics
        volumeMounts:
        - name: config
          mountPath: /etc/alloy
          readOnly: true
        - name: state
          mountPath: /var/lib/alloy
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
      volumes:
      - name: config
        configMap:
          name: alloy-config
      - name: state
        emptyDir:
          sizeLimit: 256Mi
```

이 API 경로는 Fargate 애플리케이션 파드 수집 시 DaemonSet 제한도 피하지만 노드 로그는 수집하지 않습니다. Kubernetes API·kubelet 부하가 증가하므로 대규모 환경은 노드 로컬 수집 또는 대상 소유권을 조정하는 Alloy clustering을 검토합니다. 모든 파드를 tail하는 동일 replica를 단순 추가하지 않습니다. 예제의 `emptyDir` 상태와 제한된 재시도는 재시작·장애 시 무손실 전달을 보장하지 않으므로 운영에는 영속 버퍼·WAL과 복구 검증이 필요합니다.

### 3. LogQL 쿼리 예제

다음은 stdout JSON 제공자와 비샘플링 SERVER access log를 사용합니다. 컨테이너 selector만으로는 프록시 진단 로그도 포함되므로 `log_type="access"`로 구분합니다. HTTP 통계에서는 TCP 연결 로그를 제외하기 위해 빈·`-` 메서드도 제외합니다. 숫자는 숫자로 비교하고 메트릭 집계 전에 `__error__=""`로 파싱·변환 실패를 제외합니다.

#### 기본 쿼리

```logql
{namespace="production"}

{app="payment-service"}

{container="istio-proxy",log_type="access"}

{namespace="production"} |~ "(?i)error"

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | response_code >= 500 | response_code < 600 | __error__=""
```

#### 고급 필터링

```logql
{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | method="POST" | __error__=""

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | duration > 1000 | __error__=""

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | response_flags=~".*UO.*" | __error__=""

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | response_flags=~".*URX.*" | __error__=""

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | downstream_tls_version=~"(-)?" | __error__=""

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | path=~"/api/v1/.*" | __error__=""
```

`UO`는 upstream overflow, `URX`는 재시도·연결 시도 소진입니다. `downstream_tls_version`은 기록된 연결의 평문·TLS를 구분하고 `peer_uri_san`은 제공되는 경우 인증된 peer 정보를 나타냅니다. 둘 다 보편적인 TLS 핸드셰이크 실패 카운터는 아니며 HTTP access log 전에 핸드셰이크가 실패할 수도 있습니다. 기존 `connection_security_policy` 쿼리는 이 로그에 없는 메트릭 레이블을 참조했습니다.

#### 집계 및 통계

```logql
sum by (namespace, app) (rate({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | __error__="" [5m]))

sum by (response_code) (count_over_time({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | __error__="" [5m]))

quantile_over_time(0.95, {container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | unwrap duration | __error__="" [5m]) by (namespace, app)

sum by (namespace, app) (rate({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | response_code >= 500 | response_code < 600 | __error__="" [5m])) / sum by (namespace, app) (rate({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | __error__="" [5m]))

avg_over_time({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | unwrap duration | __error__="" [5m]) by (namespace, app)
```

보관된 로그 항목의 통계입니다. 선택적 로깅·샘플링·전송 손실·호출 경로·게이트웨이 로그가 결과에 영향을 주므로 전체 서비스 SLO에는 메트릭 장의 표준 메트릭을 사용합니다.

## Grafana 로그 대시보드

### 1. Loki 데이터소스 추가

Datasource 파일을 Grafana의 `provisioning/datasources`에 마운트하거나 차트의 지원되는 provisioning을 사용합니다. ConfigMap만으로 자동 로드되지 않습니다. `tempo` UID는 기존 Tempo datasource여야 합니다. JSON 제공자의 `trace_id`로 연동하며 request UUID는 trace ID가 아닙니다. 빈 ID에는 trace 링크가 생성되지 않습니다.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: observability
data:
  loki.yaml: |
    apiVersion: 1
    datasources:
    - name: Loki
      uid: loki
      type: loki
      access: proxy
      url: http://loki.observability.svc.cluster.local:3100
      jsonData:
        maxLines: 1000
        derivedFields:
        - datasourceUid: tempo
          matcherRegex: '"trace_id"\s*:\s*"([0-9a-fA-F]{32})"'
          name: TraceID
          url: $${__value.raw}
          urlDisplayLabel: View trace
```

### 2. Istio Access Log 대시보드

#### 대시보드 JSON

아래 dashboard 객체를 가져오거나 dashboard provider로 파일을 마운트합니다. HTTP API wrapper가 아닌 dashboard 파일입니다. Datasource UID `loki`·`prometheus`가 있어야 하며 로그 `app`과 메트릭 canonical-service 값을 맞춥니다. Heatmap은 실제 Prometheus histogram bucket을 사용합니다. 원시 로그 duration에는 `le` bucket 레이블이 없습니다.

```json
{
  "title": "Istio Access Logs",
  "tags": [
    "istio",
    "logs"
  ],
  "timezone": "browser",
  "panels": [
    {
      "title": "Logged HTTP Request Rate",
      "type": "timeseries",
      "targets": [
        {
          "expr": "sum by (namespace, app) (rate({container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | __error__=\"\" [5m]))",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 0
      },
      "id": 1,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "Response Code Distribution",
      "type": "piechart",
      "targets": [
        {
          "expr": "sum by (response_code) (count_over_time({container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | __error__=\"\" [5m]))",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 0
      },
      "id": 2,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "P50/P95/P99 Latency",
      "type": "timeseries",
      "targets": [
        {
          "expr": "quantile_over_time(0.5, {container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | unwrap duration | __error__=\"\" [5m]) by (namespace, app)",
          "legendFormat": "P50",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        },
        {
          "expr": "quantile_over_time(0.95, {container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | unwrap duration | __error__=\"\" [5m]) by (namespace, app)",
          "legendFormat": "P95",
          "refId": "B",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        },
        {
          "expr": "quantile_over_time(0.99, {container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | unwrap duration | __error__=\"\" [5m]) by (namespace, app)",
          "legendFormat": "P99",
          "refId": "C",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 24,
        "x": 0,
        "y": 8
      },
      "id": 3,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "HTTP Error Fraction in Retained Logs",
      "type": "stat",
      "targets": [
        {
          "expr": "sum by (namespace, app) (rate({container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | response_code >= 500 | response_code < 600 | __error__=\"\" [5m])) / sum by (namespace, app) (rate({container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | __error__=\"\" [5m]))",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 4,
        "w": 6,
        "x": 0,
        "y": 16
      },
      "id": 4,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "Top 10 Routes by Average Logged Duration",
      "type": "table",
      "targets": [
        {
          "expr": "topk(10, avg_over_time({container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | unwrap duration | __error__=\"\" [5m]) by (namespace, app, route_name, method))",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 20
      },
      "id": 5,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "Error Logs",
      "type": "logs",
      "targets": [
        {
          "expr": "{container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | response_code >= 400 | __error__=\"\"",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 20
      },
      "id": 6,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "Upstream Overflow Events",
      "type": "logs",
      "targets": [
        {
          "expr": "{container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | response_flags=~\".*UO.*\" | __error__=\"\"",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 24,
        "x": 0,
        "y": 28
      },
      "id": 7,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "HTTP Duration Histogram (Prometheus)",
      "type": "heatmap",
      "targets": [
        {
          "expr": "sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter=\"destination\",destination_workload_namespace=\"$namespace\",destination_canonical_service=\"$service\"}[5m]))",
          "format": "heatmap",
          "refId": "A",
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 24,
        "x": 0,
        "y": 36
      },
      "id": 8,
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      }
    }
  ],
  "templating": {
    "list": [
      {
        "name": "namespace",
        "type": "query",
        "query": "label_values({container=\"istio-proxy\"}, namespace)",
        "datasource": {
          "type": "loki",
          "uid": "loki"
        }
      },
      {
        "name": "service",
        "type": "query",
        "query": "label_values({container=\"istio-proxy\", namespace=\"$namespace\"}, app)",
        "datasource": {
          "type": "loki",
          "uid": "loki"
        }
      }
    ]
  },
  "uid": "istio-access-logs"
}
```

### 3. Loki Ruler 알림

Prometheus 형태의 `groups`/`alert`/`expr` YAML은 Loki ruler 설정입니다. Grafana 관리 알림 provisioning은 문서화된 UID·condition·query-data 형식을 사용하므로 그 경로를 쓰면 Grafana에서 규칙을 export합니다. Loki ruler로 평가하려면 다음 ConfigMap을 생성하고 ruler 설정을 `loki.yaml`에 병합하며 기존 config·storage 마운트를 유지한 채 StatefulSet에 volume 조각을 병합합니다. 설정한 주소에 Alertmanager가 먼저 있어야 합니다.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: loki-rules
  namespace: observability
data:
  istio-logging-alerts.yaml: |
    groups:
    - name: istio-logging-alerts
      interval: 1m
      rules:
      - alert: HighHTTPErrorFractionInLogs
        expr: sum by (namespace, app) (rate({container="istio-proxy",log_type="access"} | json | method!=""
          | method!="-" | response_code >= 500 | response_code < 600 | __error__="" [5m])) / sum by (namespace,
          app) (rate({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | __error__=""
          [5m])) > 0.05
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: Retained HTTP logs show more than 5% server errors
      - alert: CircuitBreakerOverflow
        expr: sum by (namespace, app) (count_over_time({container="istio-proxy",log_type="access"} | json
          | method!="" | method!="-" | response_flags=~".*UO.*" | __error__="" [1m])) > 10
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: Upstream overflow events in access logs
      - alert: SlowLoggedRequests
        expr: quantile_over_time(0.95, {container="istio-proxy",log_type="access"} | json | method!="" | method!="-"
          | unwrap duration | __error__="" [5m]) by (namespace, app) > 2000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: P95 of logged HTTP durations exceeds 2000ms
      - alert: PlaintextHTTPObserved
        expr: sum by (namespace, app) (count_over_time({container="istio-proxy",log_type="access"} | json
          | method!="" | method!="-" | downstream_tls_version=~"(-)?" | __error__="" [5m])) > 0
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: HTTP access logs show a plaintext downstream connection
```

```yaml
ruler:
  storage:
    type: local
    local:
      directory: /etc/loki/rules
  rule_path: /loki/ruler-scratch
  alertmanager_url: http://alertmanager.observability.svc.cluster.local:9093
  ring:
    kvstore:
      store: inmemory
  enable_api: true
```

```yaml
spec:
  template:
    spec:
      containers:
      - name: loki
        volumeMounts:
        - name: loki-rules
          mountPath: /etc/loki/rules
          readOnly: true
      volumes:
      - name: loki-rules
        configMap:
          name: loki-rules
          items:
          - key: istio-logging-alerts.yaml
            path: fake/istio-logging-alerts.yaml
```

단일 tenant Loki의 ID는 `fake`이므로 로컬 규칙 파일을 `fake/` 아래에 배치합니다. 로컬 rule storage는 ruler API로 수정할 수 없습니다. 이 알림은 전체 access-log stream을 전제합니다. 에러만 또는 샘플링된 stream으로는 편향 없는 에러율·지연 분위수를 얻을 수 없습니다. 데이터 부재·전송 실패 모니터링도 별도로 구성합니다.

## 로그와 메트릭/트레이스 연동

### 1. 로그에서 트레이스로 점프

앞의 Loki datasource에서 `trace_id` derived field를 사용합니다. 추적이 활성화되고 ID가 있으며 동일 trace가 Tempo에 보관된 경우에만 조회할 수 있습니다. `x-request-id`는 W3C trace ID와 서로 바꿔 쓸 수 없습니다. 샘플링·백엔드 보존 때문에 정상 로그에도 조회 가능한 trace가 없을 수 있습니다.

### 2. 메트릭 연동

Prometheus exemplar는 실제 trace-ID 레이블이 있을 때 **메트릭→트레이스**를 연결하며 메트릭→로그 링크를 만들지는 않습니다. `exemplarTraceIdDestinations.name`은 임의 `TraceID`가 아닌 관측한 exemplar 레이블(일반적으로 `trace_id`)로 지정합니다. 메트릭→로그는 namespace/service 레이블을 맞춘 Grafana correlation/data link로 구성합니다. Datasource 설정만으로 exemplar가 생성되지는 않습니다.

### 3. 통합 대시보드 쿼리

전체 트래픽 요청률은 Prometheus 패널, 선택한 워크로드 access record는 Loki 패널로 표시합니다. Dashboard 변수를 일관되게 설정하며 Istio 메트릭은 보편적 `app` 레이블 대신 `destination_canonical_service`·workload namespace를 사용합니다.

```promql
sum(rate(istio_requests_total{reporter="destination",destination_workload_namespace="$namespace",destination_canonical_service="$service"}[5m]))
```

```logql
{container="istio-proxy",log_type="access",namespace="$namespace",app="$service"} | json | __error__=""
```

URL에 인코딩되지 않은 JSON을 넣는 대신 Grafana가 생성한 Explore 링크·correlation을 사용합니다. Loki app 레이블과 메트릭 service 레이블이 같은 워크로드를 나타내는지 확인합니다.

## 성능 최적화

### 1. 로그 볼륨 줄이기

필터·Alloy 샘플링을 선택하기 전에 상태 확인·오류·일상 트래픽의 실제 비중을 측정합니다. 보편적인 50–90%·30–50% 감소율은 없습니다. 프록시 필터링은 생성량, collector 샘플링은 이후 수집·저장량을 줄입니다. 전체 트래픽 메트릭과 중요한 감사 이벤트는 샘플링 로그와 분리해 확보합니다.

HTTP 상태 확인 경로 제외를 기존 Telemetry 필터에 병합할 수 있으며 TCP 연결은 HTTP 필드 누락을 고려합니다:

```yaml
filter:
  expression: '!has(request.url_path) || !(request.url_path.startsWith("/health") || request.url_path.startsWith("/ready")
    || request.url_path.startsWith("/live") || request.url_path == "/metrics" || request.url_path == "/favicon.ico")'
```

### 2. Loki 성능 튜닝

```yaml
limits_config:
  # 수집 제한이며 chunk 크기를 직접 설정하지 않음
  ingestion_rate_strategy: global
  ingestion_rate_mb: 32  # 워크로드에 맞출 예시
  ingestion_burst_size_mb: 64  # 예시 burst 예산

  # 쿼리 성능
  max_query_parallelism: 32
  max_query_series: 10000
  max_query_lookback: 720h

  # 스트림 제한
  max_streams_per_user: 10000
  max_global_streams_per_user: 0

  # 레이블 카디널리티 제한
  max_label_names_per_series: 30
  max_label_value_length: 2048
```

### 3. Alloy 배치와 재시도

```alloy
// loki.write endpoint fragment: merge with the endpoint's existing URL.
batch_wait = "1s"
batch_size = "1MiB"
min_backoff_period = "500ms"
max_backoff_period = "5m"
max_backoff_retries = 10
remote_timeout = "10s"
```

## 문제 해결

### Access Log가 보이지 않을 때

실제 동적 listener·선택한 제공자·알려진 테스트 요청을 확인합니다. 내부 프록시 로그가 있다고 access logging이 설정된 것은 아니며 컨테이너의 첫 로그가 JSON일 필요도 없습니다:

```bash
kubectl get telemetry -A
istioctl proxy-config listeners <pod-name> -n <namespace> -o json | \
  jq '.. | objects | select(has("accessLog")) | .accessLog'
kubectl logs <pod-name> -n <namespace> -c istio-proxy --tail=100 | \
  jq -R 'fromjson? | select(.log_type == "access")'
```

### Collector·저장소 전달 실패

Alloy 대상 검색·RoleBinding·pod-log 권한을 확인합니다. API source에는 호스트 로그 파일이 필요하지 않습니다. Alloy 로그·메트릭에서 drop·재시도 배치를 확인하고 Loki의 log stream은 range-query endpoint로 조회합니다. Port-forward는 별도 터미널에서 실행합니다:

```bash
kubectl logs -n observability deployment/alloy --tail=100
kubectl port-forward -n observability deployment/alloy 12345:12345
# Another terminal:
curl -fsS http://localhost:12345/metrics | rg 'loki_(write|process)_'
# Separate terminal:
kubectl port-forward -n observability svc/loki 3100:3100
```

```bash
curl -fsSG http://localhost:3100/loki/api/v1/query_range \
  --data-urlencode 'query={container="istio-proxy",log_type="access"}' \
  --data-urlencode 'limit=20' | jq '.data.result'
```

### 로그 볼륨과 카디널리티

`kubectl top`은 로그량이 아닌 자원 사용량입니다. 보관된 로그의 byte rate를 조회하고 제한된 시간의 실제 stream 집합을 검사합니다. `/labels`는 stream 수가 아닌 레이블 이름 수이며 대규모 환경에서 제한 없는 고카디널리티 `/series` 조회를 피합니다.

```logql
topk(10, sum by (namespace, app) (bytes_rate({container="istio-proxy"} [5m])))

topk(10, sum by (namespace, app) (count_over_time({container="istio-proxy"} [1h])))
```

숫자 필터 전에 파싱된 필드를 확인하고 `unwrap` 뒤 집계 전에 `__error__`를 제외합니다. 샘플링·필터링·유실된 항목은 보관 로그에서 복구할 수 없습니다.

## 참고 자료

- [Istio Access Logging](https://istio.io/latest/docs/tasks/observability/logs/access-log/)
- [Telemetry API](https://istio.io/latest/docs/reference/config/telemetry/)
- [Envoy Access Logging](https://www.envoyproxy.io/docs/envoy/latest/configuration/observability/access_log/usage)
- [Grafana Loki Documentation](https://grafana.com/docs/loki/latest/)
- [Alloy Kubernetes log source](https://grafana.com/docs/alloy/latest/reference/components/loki/loki.source.kubernetes/)
- [Promtail lifecycle](https://grafana.com/docs/loki/latest/send-data/promtail/)
- [LogQL Query Language](https://grafana.com/docs/loki/latest/query/)
- [CEL Expression Language](https://github.com/google/cel-spec)
