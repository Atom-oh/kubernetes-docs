# 보안 및 가시성

> **검토 기준**: Cilium 1.20.1, Cilium CLI 0.20.0, Hubble CLI 1.19.4.
> **최종 검토**: 2026년 9월 12일. Cilium 1.20의 Kubernetes 호환 범위는 1.33–1.36이며, kubectl은 API 서버의 지원 버전 차이 범위에 맞춥니다.

## 실습 환경 설정

스케줄링 가능한 Linux 노드가 최소 2개이고 DNS와 정책 적용이 정상인 기존 Cilium 1.20.1 테스트 클러스터를 사용합니다. EKS 제약과 검증된 CLI 다운로드를 포함한 [설치 및 플랫폼 전제 조건](README.md)을 먼저 확인합니다. 이 예제는 CNI를 설치하거나 교체하지 않습니다. Helm, kubectl, Cilium/Hubble CLI와 jq가 필요합니다.

실습은 `kube-system`의 `k8s-app=kube-dns` 레이블을 가진 CoreDNS Pod를 가정합니다. 실제 DNS 경로를 확인해야 하며, NodeLocal DNS나 다른 배포판은 목적지와 포트가 다를 수 있습니다. 기존 정책, 프록시 구성과 플랫폼 제약도 결과에 영향을 줍니다.

### Hubble 설치 및 설정

`hubble-values.yaml`로 저장합니다. 로컬 서버, Relay, UI와 선택한 메트릭 플러그인을 활성화하는 설정 조각입니다. 기존 값을 먼저 검토한 뒤 **같은 차트 버전의 기존 릴리스**에 적용합니다. 버전을 올리는 경우에는 이전 값을 그대로 재사용하지 말고 업그레이드 절차를 따릅니다.

```yaml
# hubble-values.yaml
hubble:
  enabled: true
  relay:
    enabled: true
  ui:
    enabled: true
  metrics:
    enabled:
    - dns
    - drop
    - tcp
    - flow
    - httpV2
    serviceMonitor:
      enabled: false
```
```bash
helm upgrade cilium cilium/cilium --namespace kube-system \
  --version 1.20.1 --reuse-values --values hubble-values.yaml --wait
cilium status --wait
# Terminal 1: keep this process running; stop it with Ctrl-C.
cilium hubble port-forward
```

다른 터미널에서 API 연결을 확인합니다. 포트 포워딩은 로컬 연결이며 Relay나 UI를 공인 LoadBalancer로 노출하지 않습니다.

```bash
# Terminal 2
hubble status
hubble observe --last 20
# Optional UI; keep its local forwarding process running while using it.
cilium hubble ui
```

## Cilium의 보안 기능

Cilium은 네트워크 정책, 엔드포인트 ID와 선택적 암호화를 제공합니다. Hubble은 그 결과 발생하는 네트워크 이벤트를 관측합니다. 보안 요구 사항을 검토할 때 각 기능의 범위를 구분해야 합니다.

### Cilium 보안 아키텍처

| 책임 | 구성 요소와 범위 |
| --- | --- |
| 네트워크 마이크로세그멘테이션 | Cilium L3/L4 정책이 ID, 주소, 포트와 방향을 선택합니다. 네임스페이스 범위의 CiliumNetworkPolicy는 해당 네임스페이스의 엔드포인트를 선택합니다. |
| HTTP 정책 | Cilium의 Envoy 연동이 HTTP를 볼 수 있는 경로에서 메서드, 경로와 헤더를 검사합니다. DNS 정책은 DNS 프록시를 사용합니다. |
| DNS/FQDN 제어 | DNS 규칙은 질의를 제어하고, `toFQDNs`는 관측한 DNS 응답에서 학습한 목적지 IP를 허용합니다. 악성 도메인 평판 피드가 자동으로 제공되는 것은 아닙니다. |
| 노드 전송 암호화 | IPsec 또는 WireGuard가 지원되는 노드 간 트래픽을 보호합니다. 적용 범위는 모드와 구성에 따라 달라집니다. |
| 네트워크 조사 | Hubble이 흐름 메타데이터와 정책 판정을 기록하고 Relay, CLI, UI로 제공합니다. |
| 프로세스와 시스템 호출 보안 | **Tetragon**은 런타임 이벤트와 구성된 정책 집행을 담당하는 별도 프로젝트입니다. Hubble 활성화가 Tetragon 설치를 뜻하지 않습니다. |
| 위협 탐지와 대응 | 외부 알림 규칙, SIEM/WAF, 대응 컨트롤러를 탐지 목적과 동작에 맞게 별도로 구성합니다. |

### 네트워크 및 애플리케이션 보안

최소 권한 정책으로 횡적 이동을 제한하고 명시적 egress 정책으로 의존성을 제한합니다. 보안 ID는 보안 관련 레이블 집합에서 도출되므로 Pod마다 반드시 고유한 것은 아니며, 최종 사용자를 인증하지도 않습니다.

현재 Cilium 정책은 HTTP와 DNS L7 규칙을 지원합니다. gRPC는 HTTP/2 트래픽이 보이는 경로에서 HTTP 메서드·경로·헤더 규칙을 사용할 수 있습니다. Kafka 토픽 정책은 더 이상 지원되지 않습니다. HTTP `headers`의 값은 리터럴 일치 조건이며 정규식 기반 인증이 아닙니다. `Authorization` 헤더의 존재나 형태만으로 JWT 서명, 발급자 또는 인가 클레임을 검증할 수 없습니다. 애플리케이션 인증 계층이나 구성된 게이트웨이를 사용합니다.

8443 포트에 HTTP 규칙을 지정해도 HTTPS가 복호화되지는 않습니다. 암호화된 애플리케이션 데이터를 HTTP 정책으로 평가하려면 TLS 종료 또는 별도로 지원되는 검사 구성이 필요합니다. L7 검사를 위해 서비스 메시 암호화를 우회하지 않습니다.

### ID, 인증과 암호화

SPIRE 기반 Cilium **상호 인증은 Beta**이며 보안 ID에 대한 별도 경로의 핸드셰이크를 수행합니다. 이 핸드셰이크 자체는 애플리케이션 트래픽을 암호화하지 않습니다. 문서화된 제약에는 ClusterMesh 미지원과 임의의 외부 mTLS 시스템과의 비호환이 포함됩니다. 별도의 **ztunnel 워크로드 mTLS도 Beta**이며 등록과 인증서 전제 조건이 따로 있습니다. ID 선택자만으로 어느 기능도 자동 활성화되지 않습니다.

### 암호화 구성

다음은 **둘 중 하나를 선택하는 Helm 설정 조각**입니다. 함께 켜는 설정이 아닙니다. 설치나 변경을 계획할 때 하나를 선택하고 커널, 라우팅, 플랫폼 전제 조건을 검증합니다.

```yaml
# wireguard-values.yaml
encryption:
  enabled: true
  type: wireguard
  nodeEncryption: false
```
```yaml
# ipsec-values.yaml
encryption:
  enabled: true
  type: ipsec
  nodeEncryption: false
  ipsec:
    secretName: cilium-ipsec-keys
```

WireGuard에는 커널 지원과 노드 간 UDP 51871 경로가 필요합니다. IPsec 활성화 전에는 Cilium 네임스페이스에 올바른 형식으로 안전하게 관리되는 `cilium-ipsec-keys` Secret이 있어야 합니다. 공식 키 생성·교체 절차를 따릅니다. ConfigMap에 키 파일 이름만 지정해도 키와 볼륨이 생성되는 것은 아닙니다.

기본적으로 이 모드는 노드를 가로지르는 지원 대상 Cilium 관리 Pod 트래픽을 보호하며, 같은 노드의 트래픽은 이러한 노드 터널로 암호화되지 않습니다. 임의의 외부 목적지 트래픽도 자동 보호되지 않습니다. WireGuard의 노드 간 암호화 확장은 별도 Beta 옵션입니다. 기본적으로 컨트롤 플레인 노드는 이 확장에서 제외되지만, 해당 노드의 Cilium 관리 Pod 간 트래픽은 다른 노드를 통과할 때 암호화될 수 있습니다. 실제 패킷 경로를 검증하고 필요한 곳에는 애플리케이션 TLS를 사용합니다. 호스트 방화벽 호환성도 암호화 모드에 따라 다릅니다.

## Hubble을 통한 네트워크 가시성

Hubble은 데이터 경로, 프록시, 에이전트 이벤트를 받아 Kubernetes 메타데이터를 추가합니다. 모든 eBPF 맵을 주기적으로 읽기만 하는 도구가 아닙니다.

```text
커널/데이터 경로 이벤트 + 프록시/에이전트 이벤트
                         |
                         v
              각 Cilium 에이전트의 Hubble 서버
                  |          |             |
             유한 흐름 버퍼  메트릭 엔드포인트  선택적 파일 내보내기
                  |          TCP 9965        |
              Relay 질의      ^          로그 수집기/저장소
                  ^          | 스크레이프
                  |       Prometheus <--- Grafana 질의
               CLI / UI
```

서버의 메모리 이력은 유한합니다. Relay는 여러 서버를 질의하며 영구 데이터베이스가 아닙니다. UI는 흐름과 서비스 의존성 맵을 제공하고 CLI는 명시적 필터를 지원합니다. 조회 결과가 없으면 트래픽 부재뿐 아니라 잘못된 필터, 피어 장애, L7 가시성 부재, 버퍼 덮어쓰기나 이벤트 손실도 확인합니다.

### Hubble CLI 사용 예제

```bash
hubble observe --namespace cilium-security-demo --last 100
hubble observe --from-pod cilium-security-demo/frontend \
  --to-service cilium-security-demo/backend --last 100
hubble observe --namespace cilium-security-demo --protocol http \
  --http-status '4+' --http-status '5+' --last 100
hubble observe --namespace cilium-deny-demo --verdict DROPPED \
  --drop-reason-desc POLICY_DENIED --last 100
hubble observe --pod cilium-security-demo/frontend --follow
```

`--pod namespace/name`은 양쪽 엔드포인트를 선택합니다. 방향을 지정하려면 `--from-pod`/`--to-pod`를 사용합니다. Pod 이름은 레이블 선택자가 아니며 레이블에는 `--from-label`/`--to-label`을 사용합니다. `--namespace`와 `--from-pod`/`--to-pod`를 함께 지정하면 CLI가 거부합니다.

`DROPPED`는 판정이고 `POLICY_DENIED`는 `--drop-reason-desc`로 선택하는 드롭 사유입니다. HTTP 상태 접두사는 `4..`/`5..`가 아니라 `4+`/`5+`입니다. HTTP 필터에는 프록시가 생성한 L7 이벤트가 필요하며, TCP 연결이 차단되면 HTTP 상태가 없을 수도 있습니다.

## 네트워크 가시성 및 모니터링

### Hubble 메트릭

플러그인마다 관측 대상이 다릅니다.

| 플러그인 | 메트릭 예 | 의미와 제약 |
| --- | --- | --- |
| `flow` | `hubble_flows_processed_total` | 프로토콜·유형·판정별 처리된 흐름 이벤트이며 모든 경로의 고유 요청이나 패킷 수가 아닙니다. |
| `drop` | `hubble_drop_total{reason="POLICY_DENIED"}` | 관측된 드롭이며 사유 레이블은 enum 이름입니다. |
| `tcp` | `hubble_tcp_flags_total` | 관측된 TCP 플래그이며 일반적인 RTT·재전송·동시 연결 수 메트릭이 아닙니다. |
| `dns` | `hubble_dns_queries_total`, `hubble_dns_responses_total` | DNS 질의·응답·응답 코드이며 일반적인 DNS 지연 히스토그램이 아닙니다. |
| `httpV2` | `hubble_http_requests_total`, `hubble_http_request_duration_seconds` | HTTP 응답 흐름으로부터 요청 수·상태와 초 단위 시간을 기록합니다. HTTP 가시성이 필요합니다. |

`http`와 `httpV2`를 동시에 활성화하지 않습니다. 출발지·목적지 레이블의 카디널리티를 관리하고 요청 헤더나 민감한 ID는 목적 없이 추가하지 않습니다. 이벤트 부재를 트래픽 부재의 증거로 해석하기 전에 `hubble_lost_events_total`과 피어 상태를 확인합니다.

### Prometheus 통합

차트는 Cilium 네임스페이스에 기본 포트 **9965**의 헤드리스 `hubble-metrics` Service를 생성합니다. Service의 `k8s-app=hubble` 레이블은 탐색에 사용되며, Service 자체는 `k8s-app=cilium` 에이전트 Pod를 선택합니다. Prometheus는 단일 정적 DNS 주소에 의존하지 말고 개별 엔드포인트를 탐색해야 합니다.

Prometheus Operator와 ServiceMonitor CRD가 이미 있다면 다음 조각을 릴리스 값에 병합합니다. `release: monitoring`은 예시이며 Prometheus의 `serviceMonitorSelector`와 일치해야 합니다. 네임스페이스 선택자에도 ServiceMonitor의 네임스페이스가 포함되어야 합니다. 선택되지 않은 리소스는 스크레이프되지 않습니다.

```yaml
# hubble-servicemonitor-values.yaml
hubble:
  metrics:
    serviceMonitor:
      enabled: true
      labels:
        release: monitoring
```

차트의 ServiceMonitor는 `hubble-metrics`라는 포트 이름과 Cilium 네임스페이스의 엔드포인트를 사용합니다. Operator가 없다면 실제 Prometheus 설정에 동등한 Kubernetes 서비스 탐색을 구성합니다. 연결되지 않은 ConfigMap 생성만으로 Prometheus가 설정되지는 않습니다. `*.hubble-metrics.cilium.io`는 메트릭 TLS ID 구성에 쓰이며 9091 포트의 공인 스크레이프 대상이 아닙니다.

Grafana 대시보드는 Prometheus 메트릭을, Hubble UI 서비스 맵은 Relay를 질의합니다. 활성화한 플러그인과 레이블에 맞는 대시보드를 가져옵니다. HTTP 페이로드를 관측할 수 없는 트래픽은 HTTP 대시보드에 나타나지 않습니다.

### 흐름 내보내기와 보존

노드 로컬 순환 파일이 필요하면 `hubble-export-values.yaml`을 선택적으로 병합합니다. 필드 마스크는 네트워크 메타데이터만 유지하며 전체 HTTP 헤더를 내보내지 않습니다.

```yaml
# hubble-export-values.yaml
hubble:
  export:
    static:
      enabled: true
      filePath: /var/run/cilium/hubble/events.log
      fileMaxSizeMb: 10
      fileMaxBackups: 5
      fieldMask:
      - time
      - source.namespace
      - source.pod_name
      - destination.namespace
      - destination.pod_name
      - l4
      - IP
      - node_name
      - is_reply
      - verdict
      - drop_reason_desc
```

정적 exporter는 노드마다 파일을 쓰고 설정에 따라 순환시킵니다. 노드 손실 뒤에도 이벤트가 필요하면 별도 수집기, 접근 제어와 저장소 보존 정책을 구성합니다. 정적 설정 변경에는 에이전트 롤아웃이 필요하며 동적 exporter의 갱신 방식은 다릅니다. 필터와 필드 마스크는 이벤트나 필드를 의도적으로 생략할 수 있고 유한 버퍼에서 관측 데이터가 손실될 수도 있습니다.

## 실시간 위협 탐지

Hubble은 조사 근거를 제공하지만 완전한 IDS, WAF 또는 자동 격리 시스템을 활성화하는 스위치는 제공하지 않습니다. `enable-threat-detection`, `enable-anomaly-detection`, `alert-to-slack`은 지원되는 Cilium 설정이 아닙니다.

여러 목적지에 대한 반복 거부는 스캔 의심의 근거가 될 수 있고 트래픽 급증도 조사할 가치가 있습니다. 그 자체가 공격의 증거는 아닙니다. 애플리케이션 인증 로그, 워크로드 변경, API 감사 이벤트, 배포되어 있다면 Tetragon 런타임 이벤트와 연관 분석합니다. SQL 삽입, XSS, 명령 삽입은 적절한 애플리케이션/WAF/탐지 규칙이 필요하며 일반 HTTP 흐름 기록만으로 분류되지 않습니다.

알림을 위해서는 정상 트래픽, 데이터 부재와 이벤트 손실을 포함해 외부 Prometheus/SIEM 규칙을 정의하고 시험합니다. 속도 제한, 방화벽 격리와 대응 자동화는 별도 제어입니다. 대응 범위를 제한하고 복구 경로를 마련하며 드롭이 관측된 모든 Pod를 자동 격리하지 않습니다.

## 실습: Hubble 설치 및 활용

넓은 허용 규칙이 기본 거부 실습을 무효화하지 않도록 **서로 다른 새 네임스페이스 2개**를 사용합니다. 데이터베이스나 외부 API는 생성하지 않습니다. 명령은 테스트 클러스터에서 실행할 예시이며, 문서 감사에서는 스키마와 로컬 fixture를 검증했고 실제 배포는 하지 않았습니다.

### 1. 워크로드 생성과 기준 상태 확인

`visibility-app.yaml`로 저장합니다. 클라이언트와 서버 이미지는 Cilium CLI의 버전별 테스트 기본값을 사용합니다. 백엔드 안티어피니티 때문에 두 번째 스케줄 가능 노드가 필요하며 frontend에서 backend로의 경로가 노드를 가로지릅니다.

```yaml
# visibility-app.yaml
apiVersion: v1
kind: Pod
metadata:
  name: frontend
  labels:
    app: frontend
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
---
apiVersion: v1
kind: Pod
metadata:
  name: outsider
  labels:
    app: outsider
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  replicas: 1
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      automountServiceAccountToken: false
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: frontend
            topologyKey: kubernetes.io/hostname
      containers:
      - name: http
        image: quay.io/cilium/json-mock:v1.4.1@sha256:6a66df90808a39c02e7a9d58af7bf0e54d8f8b7d4bc528f48c891969a7049195
        ports:
        - containerPort: 8080
          name: http
        readinessProbe:
          httpGet:
            path: /
            port: http
---
apiVersion: v1
kind: Service
metadata:
  name: backend
spec:
  selector:
    app: backend
  ports:
  - name: http
    port: 8080
    targetPort: http
    protocol: TCP
```
```bash
set -eu
for ns in cilium-security-demo cilium-deny-demo; do
  kubectl create namespace "$ns"
  kubectl label namespace "$ns" audit-lab=security-visibility
  kubectl --namespace "$ns" apply -f visibility-app.yaml
  kubectl --namespace "$ns" wait --for=condition=Ready pod/frontend pod/outsider --timeout=120s
  kubectl --namespace "$ns" rollout status deployment/backend --timeout=120s
  for client in frontend outsider; do
    kubectl --namespace "$ns" exec "$client" -- \
      curl --fail --silent --show-error --max-time 5 http://backend:8080/
  done
done
```

정책 적용 전에 두 네임스페이스의 두 클라이언트 모두 백엔드에 접근할 수 있어야 합니다. 그렇지 않으면 준비 상태, 스케줄링, DNS와 네트워크부터 해결합니다. 임의의 curl 오류를 정책 차단의 증거로 해석하지 않습니다.

### 2. HTTP 정책 적용과 관찰

`backend-http.yaml`로 저장합니다. `frontend` ID가 백엔드 TCP 8080에 `GET /`를 보내도록 허용합니다. L4 허용 규칙이 겹치면 L7 제한을 우회할 수 있으므로 넓은 ingress 허용 규칙을 함께 두지 않습니다.

```yaml
# backend-http.yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-http
  namespace: cilium-security-demo
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-security-demo
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: GET
          path: /
```
```bash
kubectl apply -f backend-http.yaml
# After the endpoint has realized the policy:
kubectl -n cilium-security-demo exec frontend -- \
  curl --fail --silent --show-error --max-time 5 http://backend:8080/
# Display the HTTP response code; do not use --fail here.
kubectl -n cilium-security-demo exec frontend -- \
  curl --silent --show-error --max-time 5 --output /dev/null \
    --write-out '%{http_code}\n' --request POST http://backend:8080/
# A separate client is not in the allowed identity selector.
kubectl -n cilium-security-demo exec outsider -- \
  curl --silent --show-error --max-time 5 http://backend:8080/
hubble observe --namespace cilium-security-demo --verdict DROPPED --last 100
```

정책이 실제 적용된 뒤에는 frontend의 `GET /`가 성공하고 `POST /`는 프록시의 HTTP 403을 받아야 합니다. outsider의 새 연결은 L3/L4에서 거부되어야 합니다. 요청 시각, 엔드포인트와 Hubble 이벤트를 대조합니다. DNS 오류, 컨테이너 부재나 무관한 HTTP 오류는 거부 시험의 성공이 아닙니다. Hubble UI에서 생성된 의존성 연결과 드롭을 확인합니다.

데이터베이스와 외부 API가 필요한 실제 백엔드에는 다음 **선택적 의존성 정책**을 참고할 수 있습니다. 실습에서는 적용하지 않으며 `database`와 `api.example.com`은 실제 의존성으로 바꿔야 합니다. DNS 엔드포인트부터 확인합니다.

```yaml
# backend-dependencies.yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-dependencies
  namespace: cilium-security-demo
spec:
  endpointSelector:
    matchLabels:
      app: backend
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
      rules:
        dns:
        - matchPattern: '*'
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-security-demo
        k8s:app: database
    toPorts:
    - ports:
      - port: '3306'
        protocol: TCP
  - toFQDNs:
    - matchName: api.example.com
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

TCP/UDP DNS를 허용하고 DNS 프록시 규칙으로 응답을 관측해 `toFQDNs`에 사용합니다. DNS 질의 허용과 이후 해석된 IP로의 연결 허용은 별개입니다. 이 정책의 DNS `*`는 모든 질의 이름을 허용하며 도메인 차단 목록이 아닙니다.

### 3. 기본 거부를 별도로 검증

`deny-except-dns.yaml`로 저장합니다. 명시적 `policyTypes`가 양방향 격리를 활성화하고 `ingress: []`에는 **ingress 허용 규칙이 없습니다**. 유일한 egress 예외는 선택한 DNS Pod로의 DNS 트래픽입니다.

```yaml
# deny-except-dns.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-except-dns
  namespace: cilium-deny-demo
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```
```bash
kubectl apply -f deny-except-dns.yaml
kubectl -n cilium-deny-demo exec frontend -- \
  curl --silent --show-error --max-time 5 http://backend:8080/
hubble observe --namespace cilium-deny-demo --verdict DROPPED \
  --drop-reason-desc POLICY_DENIED --last 100
```

빈 ingress 목록을 `ingress: [{}]`로 바꾸지 않습니다. 후자는 모든 ingress를 허용합니다. 표준 NetworkPolicy의 허용은 합산되므로 다른 정책이 트래픽을 열 수 있습니다. Cilium 거부 규칙이나 클러스터 정책은 추가 제한을 줄 수 있습니다. 이 네임스페이스 실습은 hostNetwork 트래픽이나 모든 호스트 출발 경로의 격리를 보장하지 않습니다.

### 4. JSON 확인과 로컬 요약

다음을 `flow-summary.jq`로 저장합니다. `--output jsonpb`는 `.flow`가 포함된 protobuf 응답 구조를 사용하므로 CLI의 레거시 `json` 호환 설정에 의존하지 않습니다.

```text
[.[] | select(.flow != null) | .flow] as $flows
| {
    flow_records: ($flows | length),
    other_records: (length - ($flows | length)),
    policy_denied_records: (
      [$flows[] | select(.verdict == "DROPPED"
                        and .drop_reason_desc == "POLICY_DENIED")] | length
    ),
    dropped_by_reason: (
      [$flows[] | select(.verdict == "DROPPED")]
      | group_by(.drop_reason_desc // "UNKNOWN")
      | map({reason: (.[0].drop_reason_desc // "UNKNOWN"), records: length})
    )
  }
```

```bash
set -eu
hubble observe --namespace cilium-deny-demo --last 100 --output jsonpb > flows.jsonl
jq --slurp --from-file flow-summary.jq flows.jsonl
```

결과는 **이 유한 표본의 흐름 레코드 수**이며 고유 공격, 연결 또는 전체 클러스터 패킷 수가 아닙니다. 흐름 이외 레코드 수도 따로 세므로 손실·상태 정보를 확인합니다. 실시간 로컬 필터는 다음과 같습니다.

```bash
hubble observe --namespace cilium-deny-demo --follow --output jsonpb |
  jq --unbuffered -c 'select(.flow.verdict == "DROPPED"
    and .flow.drop_reason_desc == "POLICY_DENIED")'
```

이 파이프라인은 로컬에 출력합니다. 알림에는 별도로 구성한 연동, 자격 증명, 재시도·중복 제거 정책과 스트림 장애 처리가 필요합니다.

### 5. 테스트 네임스페이스 정리

네임스페이스 이름을 확인한 뒤 이 실습의 워크로드와 정책만 제거합니다. 소유 레이블 조회 실패나 불일치 시 검사가 중단됩니다.

```bash
set -eu
for ns in cilium-security-demo cilium-deny-demo; do
  LAB_OWNER=$(kubectl get namespace "$ns" -o jsonpath='{.metadata.labels.audit-lab}')
  test "$LAB_OWNER" = security-visibility
  kubectl delete namespace "$ns"
done
```

## 공식 근거

- [Cilium policy enforcement](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/security/policy/intro.rst)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [HTTP policy](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/security/policy/layer7.rst)
- [DNS policy](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/security/dns.rst)
- [Hubble setup](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/observability/hubble/setup.rst)
- [Metrics](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/observability/metrics.rst)
- [Flow exporter](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/observability/hubble/configuration/export.rst)
- [WireGuard](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/security/network/encryption-wireguard.rst)
- [IPsec](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/security/network/encryption-ipsec.rst)
- [Mutual authentication](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
- [ztunnel](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/security/network/encryption-ztunnel.rst)
- [Tetragon](https://raw.githubusercontent.com/cilium/tetragon/main/README.md)
- [Hubble CLI filters](https://raw.githubusercontent.com/cilium/hubble/v1.19.4/vendor/github.com/cilium/cilium/hubble/cmd/observe/flows.go)

[메인 페이지로 돌아가기](README.md)

## 퀴즈

[주제 퀴즈](../../quizzes/networking/cilium/06-security-visibility-quiz.md)에서 정책, 암호화와 관측성의 범위를 확인합니다.
