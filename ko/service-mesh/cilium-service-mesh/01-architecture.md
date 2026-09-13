# Cilium Service Mesh 아키텍처

> **검토 기준**: Cilium 1.20.1, 2026년 9월 11일. 일반 Kubernetes 테스트 범위는 1.33–1.36이며, 해당 릴리스의 EKS CI 범위는 1.33–1.35입니다. 플랫폼·커널·설치 모드별 요건은 별도로 확인해야 합니다. [개요](./README.md)를 참고하세요.

## 개요

Cilium은 eBPF 기반 L3/L4 데이터패스와 HTTP 등 지원되는 L7 처리를 위한 Envoy를 결합합니다. Envoy는 Agent가 관리하는 프로세스 또는 별도의 `cilium-envoy` DaemonSet으로 실행할 수 있습니다. 프록시 공유는 배포와 장애 범위를 바꾸지만, 일정한 메모리 절감량이나 지연 시간을 보장하지는 않습니다.

## 전체 아키텍처

![Kubernetes 제어 평면, 노드별 Cilium Agent, eBPF 데이터패스와 공유 Envoy 사이의 논리적 관계.](../../.gitbook/assets/ko-service-mesh-cilium-service-mesh-01-architecture-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-cilium-service-mesh-01-architecture-0.html)

위쪽 상자는 제어 평면 기능을 묶어 표현합니다. **Kubernetes API 서버와 Cilium Operator는 별도 구성 요소**입니다. Operator는 클러스터 전체 작업을 담당하는 Deployment이며, 노드마다 실행되는 Agent나 API 서버 대체물이 아닙니다.

| 구성 요소 | 역할 |
|---|---|
| Cilium Agent | 로컬 엔드포인트, eBPF 프로그램·맵, 정책과 Envoy 설정 관리 |
| Cilium Operator | Identity 가비지 컬렉션, CRD 등록, 해당 IPAM 모드에서의 IP 할당 등 클러스터 전체 작업 |
| Envoy | 리다이렉트된 L7 트래픽 처리. 별도 DaemonSet으로 배포하면 프록시 수명 주기를 독립적으로 관리 가능 |
| Kubernetes API | 원하는 리소스 상태를 저장하고 워크로드·Service 상태를 컨트롤러에 제공 |
| Hubble | 지원되는 데이터패스·프록시 이벤트 관찰. Relay/UI를 활성화하면 별도 구성 요소가 추가됨 |

## eBPF 데이터패스

### 프로그램과 훅

eBPF 프로그램은 검증을 거쳐 정해진 커널 훅에서 실행됩니다. 모든 L3/L4 패킷에 사용자 공간 프록시 홉을 추가하지 않고 패킷 필터링, 리다이렉션과 Service 변환을 구현할 수 있습니다.

![일반 네트워킹 경로와 선택적인 eBPF 전달 최적화의 개념 비교.](../../.gitbook/assets/ko-service-mesh-cilium-service-mesh-01-architecture-1.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-cilium-service-mesh-01-architecture-1.html)

우회 화살표는 가능한 최적화를 나타내며, Cilium이 Linux 네트워킹 계층 전체를 항상 건너뛴다는 뜻이 아닙니다. Pod의 소켓 스택, 라우팅 모드, 커널 기능과 통합 요건도 경로에 영향을 줍니다.

| 훅 또는 경로 | Cilium에서의 용도와 조건 |
|---|---|
| TC/TCX와 엔드포인트 데이터패스 | 패킷 단위 정책, 전달과 Service 처리. 부착 방식은 커널·데이터패스 모드에 따라 달라짐 |
| cgroup 소켓 훅 | TCP `connect()` 등의 소켓 수준 Service 변환. 패킷 수준 TC 로드 밸런싱과 구분 |
| XDP | 지원 장치에서 NodePort/LoadBalancer 가속 등의 조기 처리에 선택적으로 사용. Cilium 설치만으로 모든 경로에 활성화되는 기능이 아님 |
| veth/netkit | 서로 다른 요건을 가진 엔드포인트 장치·데이터패스 선택지. 하나의 보편적인 훅 순서를 의미하지 않음 |

### 연결 추적과 정책

Cilium은 연결 상태를 BPF 맵에 저장합니다. 이를 이용해 상태 기반 처리, 응답 인식, NAT·프록시 관련 정보를 관리합니다. 그렇다고 **첫 패킷의 허용 결정을 이후 모든 패킷에 영구 캐시하는 것은 아닙니다**. 릴리스된 엔드포인트 데이터패스는 명시적인 예외를 제외하고 연결을 시작한 방향의 `CT_NEW`와 `CT_ESTABLISHED` 모두에 정책을 검사합니다. 인식된 응답·관련 트래픽은 상태 기반 반환 처리를 따릅니다. 정책 변경, 프록시 리다이렉션과 최적화 경로는 실제 설정에서 확인해야 합니다.

다음은 개념 설명이며 C 구조체나 맵 ABI 정의가 아닙니다.

| 맵 정보 | 목적 |
|---|---|
| CT 튜플 키와 연결 상태 값 | 흐름·방향 식별, 상태·수명·변환 관련 정보 유지 |
| Service 프런트엔드·백엔드 맵 | Service 주소·포트·프로토콜 정보를 백엔드 항목으로 해석 |
| 정책 맵 | 컴파일된 Identity·방향·포트·프로토콜 정책과 관련 프록시·인증 정보 표현 |
| IP 캐시 | 주소·프리픽스를 보안 Identity 및 라우팅 정보와 연결 |

원시 맵을 읽을 때는 해당 릴리스의 BPF 정의를 사용하세요. IPv4/IPv6 키, 값, 바이트 순서와 레이아웃은 다릅니다. 튜플과 상태를 임의로 합친 `ct_entry`를 실제 디코딩 명세로 사용하면 안 됩니다.

### kube-proxy 대체

다음은 **설치 모드 설정 조각**이며 마이그레이션 절차가 아닙니다. Service 변환이 준비되기 전에도 접근할 수 있는 API 호스트와 포트로 바꾸세요. 6443은 예시이며 EKS API 엔드포인트는 일반적으로 HTTPS 443을 사용합니다. 선택한 플랫폼의 IPAM·라우팅·CNI 설정을 유지해야 합니다.

```yaml
kubeProxyReplacement: true
k8sServiceHost: <reachable-api-server-host>
k8sServicePort: 6443
loadBalancer:
  algorithm: maglev
```

`loadBalancer.algorithm: maglev`는 해당되는 외부 north–south 트래픽에서 일관된 백엔드 선택을 제공합니다. 이 모드에서 Cilium의 소켓 수준 east–west Service 연결에는 Maglev가 적용되지 않습니다. Kubernetes의 `Service.spec.sessionAffinity: ClientIP`는 별도 기능입니다. Maglev는 쿠키 고정이나 제거된 백엔드와의 연결 유지를 보장하는 기능이 아닙니다.

| 주제 | 아키텍처 구분 |
|---|---|
| Service 변환 | kube-proxy에는 iptables·nftables 등의 구현이 있고, Cilium은 BPF 및 활성화된 경우 소켓 수준 변환을 사용 |
| 연결 상태 | Linux conntrack과 Cilium BPF CT 맵은 별도 메커니즘 |
| DSR | `loadBalancer.mode: dsr`로 백엔드가 Service 주소를 사용해 직접 응답할 수 있음. 지원되는 dispatch·라우팅 조합, MTU와 클라우드 네트워크 확인 필요 |
| 성능 | 알고리즘 조회 특성만으로 전체 요청 지연·처리량·CPU 사용량을 단정할 수 없음 |

Cilium 1.20.1의 DSR option dispatch에는 native routing이 필요합니다. Geneve dispatch는 native 또는 Geneve tunnel routing을 지원하며, VXLAN tunnel routing은 지원되는 DSR 조합이 아닙니다. AWS의 source/destination check도 영향을 줄 수 있습니다. [모드별 요건](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/kubernetes/kubeproxy-free.rst)을 확인하지 않고 임의의 EKS 설치에 `mode: dsr`를 추가하면 안 됩니다.

## 공유 Envoy 프록시

### 배포와 리소스 설정

다음 Helm 오버레이는 이미 설계된 Cilium 설치에서 별도 Envoy DaemonSet과 직접적인 CEC 관리를 활성화합니다. 설치별로 검토한 values와 병합하세요. 리소스 수치는 requests/limits 예시이며 벤치마크 측정값이나 보편적인 권장 용량이 아닙니다.

```yaml
l7Proxy: true
envoyConfig:
  enabled: true
envoy:
  enabled: true
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: 2000m
      memory: 2Gi
```

```bash
kubectl -n kube-system get daemonset cilium cilium-envoy
kubectl -n kube-system get deployment cilium-operator
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
```

Desired/Ready 개수는 배치 가능한 노드 수에 따라 달라집니다. 내장 Envoy 모드는 프로세스 수명 주기가 다르며 별도 DaemonSet이 필요하지 않습니다.

### L7 처리 흐름

HTTP L7 네트워크 정책은 해당 트래픽을 정책 적용 프록시로 리다이렉트합니다. CEC Service 로드 밸런싱, Ingress와 Gateway API도 경로에 Envoy를 추가할 수 있으므로, “L7 네트워크 정책이 있는 트래픽만 Envoy를 사용한다”는 설명은 충분하지 않습니다.

![클라이언트 노드의 egress L7 정책과 동일한 프록시 연결을 통해 반환되는 HTTP 응답의 예시.](../../.gitbook/assets/ko-service-mesh-cilium-service-mesh-01-architecture-12.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-cilium-service-mesh-01-architecture-12.html)

이 그림은 **egress** 정책 예시입니다. Ingress 정책은 수신 측에서 적용하며, 양쪽 모두 설정할 수도 있습니다. 프록시를 거친 HTTP 응답은 기존 프록시 연결로 돌아옵니다. 응답마다 독립적으로 리다이렉트 또는 우회를 선택하는 모델이 아닙니다. 애플리케이션이 TLS로 암호화한 HTTP 필드를 검사하려면 해당되는 TLS/L7 구성이 필요합니다.

### 설정 소유권

Helm으로 생성하는 Agent 설정은 설치 values를 통해 관리하세요. `cilium-config`를 짧은 수동 ConfigMap으로 교체하면 필수 플랫폼 설정을 누락할 수 있습니다.

다음은 기존 릴리스와 Agent를 조회하는 명령입니다. 먼저 아래 Identity 절의 방법으로 `CILIUM_POD`를 설정하세요.

```bash
helm get values cilium -n kube-system -a
kubectl -n kube-system get configmap cilium-config -o yaml
kubectl -n kube-system logs "$CILIUM_POD" -c cilium-agent --since=10m
```

Chart 1.20.1은 `envoy.connectTimeoutSeconds`, `envoy.clusterMaxConnections`, `envoy.clusterMaxPendingRequests`, `envoy.clusterMaxRequests`를 사용합니다. `envoy.connectTimeout`, `maxConnectionsPerHost`, `envoy.cluster.*`, `envoy.proxy.protocol.*` 같은 키로는 해당 기능이 설정되지 않습니다. HTTP/2와 TLS는 임의의 Helm 스위치가 아니라 지원되는 컨트롤러·Envoy API로 구성합니다.

## CRD 모델

| 리소스 | 범위와 역할 |
|---|---|
| `CiliumNetworkPolicy` | 지원되는 L7 규칙 등을 포함하는 네임스페이스 범위 엔드포인트 정책 |
| `CiliumClusterwideNetworkPolicy` | 클러스터 범위 엔드포인트 정책. 실제 대상은 여전히 selector로 결정 |
| `CiliumEnvoyConfig` (CEC) | 네임스페이스 범위의 저수준 Envoy 리소스와 Service 리다이렉션 |
| `CiliumClusterwideEnvoyConfig` (CCEC) | 클러스터 범위 Envoy 설정. 개별 Service를 명시적으로 식별해야 함 |
| `CiliumEndpoint` | Cilium이 관리하는 네임스페이스 범위 엔드포인트 상태 |
| `CiliumIdentity` | 레이블 집합의 보안 Identity를 할당하는 클러스터 범위 리소스 |

이 리소스들이 모두 “CiliumEndpoint로 변환되는” 것은 아닙니다. 일반적인 ingress·라우팅에는 지원되는 Gateway API를 사용할 수 있으며, 직접적인 CEC/CCEC 관리는 Envoy 지식이 필요한 저수준 선택지입니다.

### CiliumEnvoyConfig

이 예시는 Cilium이 관리하는 **`default/my-service` Service에 프런트엔드 포트 8080과 준비된 HTTP 백엔드가 있는 상태**를 전제로 합니다. 해당 프런트엔드를 Listener로 보내고, RDS RouteConfiguration과 그 경로가 참조하는 EDS Cluster를 정의합니다. 워크로드와 Service는 여기서 생성하지 않습니다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: http-filter
  namespace: default
spec:
  services:
  - name: my-service
    namespace: default
    ports:
    - 8080
    listener: http-listener
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: http-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: my-service
          rds:
            route_config_name: http-route
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.route.v3.RouteConfiguration
    name: http-route
    virtual_hosts:
    - name: my-service
      domains:
      - '*'
      routes:
      - match:
          prefix: /
        route:
          cluster: default/my-service
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/my-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

`services` 항목은 EDS를 통한 백엔드 동기화도 구성합니다. `backendServices`는 자체 프런트엔드 트래픽을 리다이렉트하지 않으면서 추가 백엔드를 동기화할 때 사용합니다. CEC의 프런트엔드 Service 네임스페이스는 CEC 네임스페이스로 제한됩니다. Listener의 주소 생략은 의도적입니다. Cilium이 프록시 포트를 할당하고 xDS 소스를 보완합니다. 독립 Envoy bootstrap 파일과 구분해야 합니다.

### CiliumClusterwideEnvoyConfig

다음 독립 예시는 기존 **`default/rate-limited-service:8080`**을 대상으로 합니다. 초기 1,000개 요청의 burst와 초당 100개 토큰 보충을 갖는 로컬 버킷을 적용하며, 요청 100%에 대해 필터 활성화와 강제 적용을 명시합니다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterwideEnvoyConfig
metadata:
  name: local-rate-limit
spec:
  services:
  - name: rate-limited-service
    namespace: default
    ports:
    - 8080
    listener: http-listener
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: http-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: rate-limited-service
          rds:
            route_config_name: http-route
          http_filters:
          - name: envoy.filters.http.local_ratelimit
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
              stat_prefix: http_local_rate_limiter
              token_bucket:
                max_tokens: 1000
                tokens_per_fill: 100
                fill_interval: 1s
              filter_enabled:
                default_value:
                  numerator: 100
                  denominator: HUNDRED
              filter_enforced:
                default_value:
                  numerator: 100
                  denominator: HUNDRED
              local_rate_limit_per_downstream_connection: false
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.route.v3.RouteConfiguration
    name: http-route
    virtual_hosts:
    - name: rate-limited-service
      domains:
      - '*'
      routes:
      - match:
          prefix: /
        route:
          cluster: default/rate-limited-service
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/rate-limited-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

CCEC가 클러스터 범위라고 해서 `"*"`가 Service·네임스페이스 와일드카드가 되지는 않습니다. `nodeSelector`를 생략하면 해당되는 모든 노드에 설정을 배포하지만, 모든 Service를 선택하는 의미는 아닙니다.

위 버킷은 **각 Envoy 프로세스 내부의 worker thread 사이에서** 공유되며, 클러스터의 모든 프록시가 공유하지는 않습니다. 전체 허용량은 트래픽 분포와 참여 프로세스 수에 따라 달라지므로 클러스터 전체의 글로벌 쿼터가 아닙니다. `filter_enabled`와 `filter_enforced`의 기본값은 모두 0%이므로 버킷만 추가해서는 제한이 적용되지 않습니다.

Kubernetes는 `spec.resources` 내부의 알 수 없는 필드를 보존합니다. 따라서 `kubectl apply` 성공만으로 Envoy가 설정을 수락했다고 판단할 수 없습니다. Agent 경고·오류, xDS 수락 상태와 실제 요청을 확인하세요. 직접 작성한 CEC와 Ingress/Gateway 컨트롤러 소유 설정의 충돌도 피해야 합니다.

### HTTP 규칙을 사용하는 CiliumNetworkPolicy

다음 정책은 `default`의 `app=backend`를 선택하고, 같은 네임스페이스의 `app=frontend`에서 오는 명시된 HTTP 작업과 외부로 나가는 데이터베이스·DNS 트래픽을 허용합니다. DNS는 `kube-system`의 `k8s-app=kube-dns` 레이블을 가진 CoreDNS 엔드포인트를 가정합니다. NodeLocal DNS 등 다른 resolver 구성에는 별도로 검증한 egress 규칙이 필요합니다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: l7-policy
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: frontend
        k8s:io.kubernetes.pod.namespace: default
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/api/v1/.*$
          headers:
          - X-Request-ID
        - method: ^POST$
          path: ^/api/v1/users$
        - method: ^DELETE$
          path: ^/api/v1/users/[0-9]+$
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:app: database
        k8s:io.kubernetes.pod.namespace: default
    toPorts:
    - ports:
      - port: '5432'
        protocol: TCP
  - toEndpoints:
    - matchLabels:
        k8s:k8s-app: kube-dns
        k8s:io.kubernetes.pod.namespace: kube-system
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
```

`headers`는 문자열 목록입니다. `"X-Request-ID"`는 헤더 존재를 요구할 뿐, 신원이나 권한을 증명하지 않습니다. 정확한 값·Secret 비교에는 별도 구조화 API인 `headerMatches`를 사용합니다. HTTP 규칙은 OR 관계이므로 위 헤더 조건은 GET에만 적용됩니다. 쓰기 작업에는 애플리케이션 인증·인가가 여전히 필요합니다.

Ingress와 egress 절은 선택한 엔드포인트의 해당 방향에 기본 거부 동작을 활성화하되, 다른 적용 정책의 허용 규칙도 영향을 줍니다. 완전한 애플리케이션 의존성 정책은 아닙니다. 헬스 체크, 외부 서비스와 추가 클라이언트를 별도로 모델링해야 합니다.

## Agent, Identity와 SPIFFE

### Agent 역할

![Cilium Agent의 로컬 네트워크, 정책, 프록시 설정과 관측성 책임을 묶은 논리도.](../../.gitbook/assets/ko-service-mesh-cilium-service-mesh-01-architecture-7.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-cilium-service-mesh-01-architecture-7.html)

상자는 책임 구분이며 배타적인 이벤트 경로가 아닙니다. 관측성에는 여러 데이터패스·프록시 구성 요소의 이벤트가 나타날 수 있습니다. 클러스터 전체 Operator 작업과도 구분하세요.

### 보안 Identity

Cilium은 Identity에 영향을 주는 레이블 집합에 숫자 보안 Identity를 할당합니다. 같은 집합을 가진 Pod는 Identity를 공유할 수 있습니다. 네임스페이스·ServiceAccount 레이블이 포함될 수 있지만, 이 숫자는 사용자가 계산하는 해시나 영구적인 Pod별 식별자가 아닙니다. Cilium이 엔드포인트 변경에 맞춰 주소와 Identity의 관계를 관리합니다.

ID를 임의로 지정한 `CiliumIdentity`를 생성하기보다 실제 할당 결과를 조회하세요.

```bash
kubectl -n default get ciliumendpoints
kubectl get ciliumidentities
CILIUM_POD='<agent-pod-on-the-node-being-inspected>'
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg identity list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
```

예약 ID 1, 2, 3, 4는 각각 `host`, `world`, `unmanaged`, `health`를 뜻합니다. Dual-stack에서는 IP 주소 계열별 world Identity도 사용합니다. 워크로드 ID는 환경에 따라 달라지므로 고정 정책 상수로 복사하면 안 됩니다.

### SPIRE 통합과 보안 경계

Cilium의 베타 out-of-band 상호 인증에서는 Cilium Agent가 Cilium 보안 Identity를 대신하여 인증 정보를 얻고 검증합니다. 기본 trust domain에서 ID 형식은 다음과 같습니다.

```text
spiffe://spiffe.cilium/identity/<numeric-security-identity>
```

Istio의 namespace/service-account 경로와 다릅니다. `authentication.mutual.spire.trustDomain`을 바꾸면 trust-domain 부분도 달라집니다.

```yaml
authentication:
  enabled: true
  mutual:
    spire:
      enabled: true
      trustDomain: spiffe.cilium
      agentSocketPath: /run/spire/sockets/agent/agent.sock
      install:
        enabled: true
        server:
          dataStorage:
            enabled: true
            size: 1Gi
```

이 선택적 오버레이에는 SPIRE 영구 저장소용 StorageClass/PV와 선택한 트래픽에 대한 명시적 인증 정책이 필요합니다. SPIRE 활성화만으로 모든 연결에 상호 인증을 요구하지는 않습니다.

인증 핸드셰이크는 데이터 경로 밖에서 수행됩니다. **애플리케이션 트래픽 암호화는 별도의 WireGuard/IPsec 설정**이며 플랫폼·경로별 제한이 있습니다. Cilium은 상호 인증을 베타·미완성 기능으로 문서화하고 ClusterMesh 및 외부 mTLS 상호 운용 제한을 명시합니다. 이를 모든 트래픽에 적용된 사이드카 mTLS와 동등하다고 설명하면 안 됩니다.

### 별도의 ztunnel 암호화 베타

Cilium 1.20.1에는 `encryption.type: ztunnel`로 선택하는 별도의 [ztunnel 투명 암호화 베타](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ztunnel.rst)도 있습니다. Namespace 등록으로 TCP 워크로드 mTLS를 제공하며 양쪽 엔드포인트가 모두 등록되어야 합니다. ClusterMesh와 hostNetwork Pod는 지원하지 않고, 릴리스 문서는 이 경로에서 HBONE 포트 15008을 대상으로 하는 경우 외에는 일반 L4 정책이 동작하지 않는다고 명시합니다. 별도의 CA·bootstrap 요건을 가진 배포 선택지입니다.

위 숫자 SPIFFE Identity 예시는 out-of-band 인증에 해당합니다. Ztunnel 통합은 별도의 namespace/service-account 워크로드 Identity 모델을 사용하고 기본 CA 선택지는 Cilium 내부 CA이므로 이 기본 구성에 SPIRE가 필수인 것은 아닙니다.

## 시나리오별 패킷 흐름

### 동일 노드의 Pod

![eBPF 연결 상태와 정책 검사를 거치는 로컬 veth 전달 경로의 예시.](../../.gitbook/assets/ko-service-mesh-cilium-service-mesh-01-architecture-10.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-cilium-service-mesh-01-architecture-10.html)

이 그림은 단순화한 veth fast path입니다. BPF host routing은 요건을 충족할 때 **호스트** 상위 스택과 netfilter 훅을 우회할 수 있지만, Pod 자체의 프로토콜 스택은 남아 있습니다. Legacy host routing, netkit, 프록시 리다이렉션과 통합 구성에 따라 경로가 달라집니다. 호스트 netfilter 훅에 의존하는 기능은 특히 주의해야 하며, 이 그림은 보편적인 0.1ms 지연을 보장하지 않습니다.

### 서로 다른 노드의 Pod

Tunnel routing은 송신 노드에서 VXLAN 또는 Geneve로 캡슐화하고 수신 노드에서 역캡슐화합니다. Native routing은 그 오버레이 캡슐화 없이 Pod 주소로 향하는 underlay 경로를 사용합니다. 노드 접근성, PodCIDR 경로, MTU, 방화벽 규칙과 선택적 암호화가 실제 통신 가능 여부를 결정합니다.

### HTTP 정책 또는 Service 프록시 처리

적용되는 egress·ingress 정책이나 Service 프런트엔드가 트래픽을 Envoy로 보낼 수 있습니다. 프록시는 지원 프로토콜을 해석해 허용·라우팅된 요청을 전달하고, 응답은 기존 연결로 반환합니다. 모든 흐름이 클라이언트 측과 서버 측 Envoy를 모두 거쳐야 한다는 뜻은 아닙니다.

## Istio와 비교

| 항목 | Cilium Service Mesh | Istio 사이드카 모드 |
|---|---|---|
| 프록시 위치 | 해당 L7 트래픽에 Agent 관리 또는 별도 노드 공유 Envoy 사용 | 메시 워크로드 옆에 Envoy 배치 |
| L3/L4 데이터패스 | eBPF 네트워크·정책과 모드별 커널 경로 | 메시 범위 내 워크로드 트래픽 캡처와 Envoy 처리 |
| L7 설정 | CNP, 지원 Gateway API·컨트롤러 또는 직접 CEC/CCEC | Gateway API와 Istio 트래픽·보안 API |
| 인증·암호화 | Out-of-band 상호 인증·WireGuard/IPsec과 별도의 ztunnel mTLS 베타 | Envoy 워크로드 mTLS |
| 리소스 집계 | Agent, BPF 맵, Envoy, Operator, 선택적 Hubble/SPIRE 포함 | 사이드카, 제어 평면, 선택적 게이트웨이·텔레메트리 포함 |

Istio에는 ztunnel과 선택적 waypoint를 사용하는 ambient 모드도 있으므로 사이드카 비교만으로 모든 Istio 아키텍처를 설명할 수 없습니다. 동일한 워크로드·트래픽·보안·관측성 설정으로 비교하고 버전, 노드 수, 요청률과 지연 백분위수를 기록하세요. 기존의 50MB/Pod, 100MB/노드와 고정 밀리초 합계에는 재현 가능한 벤치마크 근거가 없어 용량 산정 지침으로 사용하지 않습니다.

## 확장성 고려 사항

### BPF 맵 용량

맵 용량은 클러스터 노드 수만이 아니라 동시 흐름, Identity, Service·백엔드와 노드 메모리에 따라 결정됩니다. 다음 명시적 Helm 값은 조절 방법의 예시이며 모든 1,000노드 클러스터에 대한 권장값이 아닙니다.

```yaml
bpf:
  ctTcpMax: 524288
  ctAnyMax: 262144
  natMax: 524288
  policyMapMax: 16384
```

CT/NAT를 명시적으로 설정할 때 NAT 용량은 TCP와 non-TCP CT 합계의 3분의 2를 넘으면 안 됩니다. 위 예시는 이 조건을 만족합니다. `bpf.mapDynamicSizeRatio`는 대신 노드 메모리로 여러 맵의 용량을 계산합니다. 0.0025는 해당 맵을 위한 전체 노드 메모리의 0.25%이며, Cilium 전체 스택의 메모리 비율이 아닙니다. 엔드포인트별 정책 맵은 별도로 검토해야 합니다.

튜닝 전에 맵 사용 압력과 할당 실패를 관찰하세요. 맵 확대·재생성은 메모리를 많이 사용하거나 기존 트래픽을 끊을 수 있습니다. `cluster.id`는 클러스터 식별·ClusterMesh 설계용이며 일반 성능 스위치가 아닙니다. 폐기된 `sockops-enable`이나 존재하지 않는 `hubble-disable` 예시는 복사하지 마세요.

### Envoy 용량

실제 chart 키를 사용한 오버레이 예시입니다.

```yaml
envoy:
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: 4000m
      memory: 4Gi
  extraArgs:
  - --concurrency 4
  connectTimeoutSeconds: 5
  clusterMaxConnections: 10000
  clusterMaxPendingRequests: 10000
  clusterMaxRequests: 10000
```

Requests/limits와 worker 4개는 예시이며 노드 용량과 측정 부하에 맞춰야 합니다. `envoy.extraArgs`는 별도 Envoy 프로세스에 worker 옵션을 전달합니다. `envoy.concurrency`는 chart 1.20.1 설정이 아닙니다. Agent 관리 Envoy는 수명 주기가 다릅니다. Cluster 연결·대기 요청 제한은 circuit breaker 설정이며 메시 전체의 글로벌 요청 쿼터가 아닙니다. Listener별 버퍼링은 해당 Envoy 리소스에서 설정하며 `envoy.perConnectionBufferLimitBytes`로 설정하지 않습니다.

## 다음 단계

- [트래픽 관리](./02-traffic-management.md)
- [보안](./03-security.md)
- [관측성](./04-observability.md)
- [아키텍처 퀴즈](../../quizzes/service-mesh/cilium-service-mesh/architecture.md)

## 참고 자료

- [Cilium 1.20.1 architecture and Envoy](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/proxy/envoy.rst)
- [kube-proxy replacement, Maglev, DSR and socket LB](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/kubernetes/kubeproxy-free.rst)
- [Released datapath policy checks](https://github.com/cilium/cilium/blob/v1.20.1/bpf/bpf_lxc.c)
- [Routing and encapsulation](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/routing.rst)
- [eBPF performance options and limitations](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/operations/performance/tuning.rst)
- [BPF map capacity](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/ebpf/maps.rst)
- [Cilium Operator](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/internals/cilium_operator.rst)
- [Envoy traffic-management example](https://github.com/cilium/cilium/blob/v1.20.1/examples/kubernetes/servicemesh/envoy/envoy-traffic-management-test.yaml)
- [CEC resource parser](https://github.com/cilium/cilium/blob/v1.20.1/pkg/ciliumenvoyconfig/cec_resource_parser.go)
- [CEC schema](https://github.com/cilium/cilium/blob/v1.20.1/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumenvoyconfigs.yaml)
- [CNP schema](https://github.com/cilium/cilium/blob/v1.20.1/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnetworkpolicies.yaml)
- [Helm 1.20.1 values](https://github.com/cilium/cilium/blob/v1.20.1/install/kubernetes/cilium/values.yaml)
- [Identity-based security](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/identity.rst)
- [SPIFFE ID construction](https://github.com/cilium/cilium/blob/v1.20.1/pkg/auth/spire/certificate_provider.go)
- [Mutual authentication status and limitations](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
- [Envoy 1.37.5 local rate-limit API](https://github.com/envoyproxy/envoy/blob/v1.37.5/api/envoy/extensions/filters/http/local_ratelimit/v3/local_rate_limit.proto)
