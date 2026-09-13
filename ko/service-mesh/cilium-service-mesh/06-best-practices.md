# Cilium Service Mesh 모범 사례

> **검토 기준**: Cilium 1.20.1, Cilium CLI 0.20.0.
> **최종 검토**: 2026년 9월 11일. Kubernetes, EKS, 선택 구성 요소의 호환성은 [설치 가이드](./README.md)에서 각각 확인합니다.

## 개요

운영 계획에서는 CNI 소유 관계, 프록시 기능, 정책 적용, 용량, 복구를 함께 검토해야 합니다. 아래 값은 특정 클러스터에 맞춰 검토할 예제이며, 프로덕션에서 검증한 사이징 보장이나 CNI 마이그레이션 절차, 완전한 EKS 설치 구성이 아닙니다.

## 프로덕션 배포 체크리스트

- [ ] 지원되는 Kubernetes/Cilium/플랫폼 조합, CPU 아키텍처, 노드 OS를 선택합니다. 일반 커널 최소 버전은 5.10 또는 RHEL 8.10의 4.18과 같은 문서화된 동등 버전이며, 고급 기능에는 더 새 커널이 필요할 수 있습니다.
- [ ] 현재 CNI, IPAM, Pod/Service/VPC CIDR, 라우팅, MTU, kube-proxy 관리 주체를 기록합니다. kube-proxy replacement를 켜기 전에 API 서버에 접근 가능한지 확인합니다.
- [ ] 워크로드별 L7 관리 주체를 선택합니다. Cilium Ingress/Gateway에는 문서화된 kube-proxy replacement와 L7 전제가 필요하며, Istio 공존 설정은 다릅니다.
- [ ] 인증·암호화·인가를 각각 선택합니다. 기본 거부 정책을 적용하기 전에 허용·거부 흐름과 DNS·필수 인프라 접근을 검증합니다.
- [ ] 메트릭 대상과 실제 레이블, 로그, 알림 전달, 인증서 갱신을 구성하고 데이터 부재 동작도 시험합니다.
- [ ] 복제본 배치와 유지보수를 위한 적격 노드를 확보합니다. Operator/Relay 준비 상태, 중단 예산, DaemonSet 업데이트 전략을 확인합니다.
- [ ] 검증한 롤백 지점과 차트·values·CRD, 워크로드·정책 목록을 보존하고 대표 환경에서 복구를 연습합니다.

### 검토할 Helm Values

이 **리소스·가용성 오버라이드**를 설치 가이드의 플랫폼 설정과 합칩니다. 모든 환경에 통용되는 IPAM 범위를 지정하거나 kube-proxy를 제거하고 모든 보안 기능을 켜는 구성이 아닙니다.

```yaml
agent: true
resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 2000m
    memory: 2Gi
operator:
  replicas: 2
  podDisruptionBudget:
    enabled: true
    maxUnavailable: 1
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 1000m
      memory: 1Gi
l7Proxy: true
envoy:
  enabled: true
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
  resources:
    requests:
      cpu: 200m
      memory: 256Mi
    limits:
      cpu: 2000m
      memory: 2Gi
hubble:
  enabled: true
  relay:
    enabled: true
    replicas: 2
    podDisruptionBudget:
      enabled: true
      maxUnavailable: 1
    affinity:
      podAntiAffinity:
        requiredDuringSchedulingIgnoredDuringExecution:
        - topologyKey: kubernetes.io/hostname
          labelSelector:
            matchLabels:
              k8s-app: hubble-relay
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 1000m
        memory: 1Gi
updateStrategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 1
```

`agent`는 boolean입니다. Agent 리소스 requests/limits는 `agent.resources`가 아니라 최상위 `resources`에 둡니다. 이전의 충돌하는 두 정의를 하나로 정리했습니다. CPU·메모리 수치는 시작 예제이며 정책 수, 변경 빈도, 트래픽, 장애 시나리오에서 측정해야 합니다.

Operator 차트의 affinity는 호스트 이름별로 복제본을 분리합니다. 여기의 Relay anti-affinity도 적격 노드 2개를 요구하지만 가용 영역 분산까지 강제하지는 않습니다. 클러스터에 맞는 토폴로지 요구를 추가합니다. 스케줄링 가능한 위치와 정상 의존성 없이 복제본 수만 2개로 늘려도 HA가 되지는 않습니다. PDB는 해당하는 자발적 eviction을 제한하며 모든 장애나 DaemonSet 컨트롤러 롤아웃을 제한하지 않습니다. 직접 Pod 삭제도 eviction 보호를 우회합니다.

외부 etcd는 별도 운영 전제를 가진 설계 선택이며 노드 수가 특정 기준을 넘었다고 필수로 추가하는 구성 요소가 아닙니다. 선택한 identity allocation mode를 일관되게 유지하고 변경 시 공식 마이그레이션 절차를 따릅니다.

### 인증과 암호화

다음은 **선택적** out-of-band 인증과 WireGuard 프로파일입니다.

```yaml
encryption:
  enabled: true
  type: wireguard
  nodeEncryption: false
authentication:
  enabled: true
  mutual:
    spire:
      enabled: true
```

[보안 가이드](./03-security.md)의 커널·포트·SPIRE 저장소·신원·정책 전제를 충족한 뒤 사용합니다. SPIRE 설정 외에 `authentication.enabled`가 필요하며 정책 규칙도 인증을 요구해야 실제로 강제됩니다. WireGuard는 적용 대상인 노드 간 트래픽을 보호합니다. SPIRE out-of-band 인증이 각 애플리케이션 연결을 Istio 방식의 mTLS 세션으로 바꾸지는 않습니다. `nodeEncryption`은 별도 조건을 확인해야 하므로 예제에서는 false를 유지합니다.

Cilium 1.20.1에는 보안 가이드에서 별도로 다루는 **Beta ztunnel 워크로드 mTLS**도 있습니다. 기본 내부 CA, 네임스페이스 등록, TCP/HBONE·정책 제약은 SPIRE out-of-band 경로와 다릅니다. 명시적인 설계를 선택해야 하며 체크박스 문구나 Helm 플래그만으로 동등한 보안 범위가 입증되지는 않습니다.

## 사이징 가이드라인

### 구성 요소별 측정

| 구성 요소 | 측정할 부하 요인 | 상한을 높이기 전 확인 |
|---|---|---|
| Agent | 엔드포인트·신원·정책 선택자/규칙, 연결 변경, BPF 맵, 이벤트량 | working set, CPU/스로틀링, 맵 압력, 정책 재생성, 드롭 원인 |
| Envoy | 동시 연결·스트림, TLS 작업, 요청·응답 크기, 버퍼, 필터 비용 | heap/RSS, CPU, 대기열, 업스트림 포화, 일정 부하의 p99 |
| Operator | IPAM·신원·노드 변경과 API 지연·호출 제한 | 조정 지연, EC2/Kubernetes 스로틀링, 할당 실패 |
| Hubble Relay/UI | 관측 흐름량, 동시 조회, 흐름 버퍼, 조회 범위 | 이벤트 손실, Relay 리소스, 조회 지연, 복제본 배치 |

이전 노드 수별 표와 `512Mi + Pod 수 × 1Mi`, `256Mi + 초당 연결 수 × 0.1Mi` 공식에는 벤치마크 근거가 없었습니다. 보편적인 메모리 계산식으로 사용할 수 없습니다. 최대 동시 연결, 버퍼 수명, 트래픽 구성, 정책 cardinality가 중요하며 초당 요청 수만으로 유지 메모리를 계산할 수 없습니다. 측정한 스케줄링 요구로 requests를 정하고 검증한 여유를 두며 순간 부하와 노드 1개 손실 상황에서 limits를 확인합니다.

### eBPF 맵 사이징

여러 대안을 하나의 YAML 키에 중복 정의하지 않은 정적 사이징 예제입니다.

```yaml
bpf:
  ctTcpMax: 2097152
  ctAnyMax: 1048576
  natMax: 2097152
  policyMapMax: 65536
```

현재 차트 키는 `ctTcpMax`, `ctAnyMax`, `natMax`입니다. 이전 `ctGlobalTcpMax`, `ctGlobalAnyMax`, `natGlobalMax` 값은 무시됩니다. Agent ConfigMap 플래그는 여전히 `bpf-ct-global-tcp-max` 같은 이름을 쓰므로 차트 키와 구분합니다. NAT 용량은 TCP/기타 CT 용량 합의 3분의 2를 넘으면 안 되며 위 값은 이 관계를 충족합니다. 맵 엔트리 상한은 애플리케이션 세션 수 보장이 아닙니다.

맵을 키우면 노드/커널 메모리를 사용합니다. 맵 크기나 구현 변경으로 상태와 연결이 끊길 수 있습니다. 렌더링한 ConfigMap과 실제 사용량을 확인하고, 노드 수나 사람이 읽는 CLI 출력의 줄 수로 정확한 점유율을 추정하지 않습니다.

## 성능 튜닝

### eBPF 설정

```yaml
bpf:
  preallocateMaps: true
  mapDynamicSizeRatio: 0.0025
bpfClockProbe: false
```

사전 할당은 초기 메모리를 더 사용하여 일부 할당 작업을 줄이는 절충이며 메모리 절약 스위치가 아닙니다. 이 대안은 동적 사이징 비율을 사용합니다. 명시적 크기가 계산값보다 우선하고 distributed LRU에는 추가 제약이 있으므로 앞선 정적 맵 예제와 무심코 합치지 않습니다. `bpfClockProbe`는 최상위 키이며 기존 CT 상태의 시계 표현을 변경할 때 공식 마이그레이션 주의사항이 적용됩니다.

`socketLB`도 `bpf` 아래가 아닌 최상위입니다. Istio 공존 시 `hostNamespaceOnly`가 중요하며 소켓 가속을 무조건 켜면 예상한 프록시 가로채기를 우회할 수 있습니다. 과거 `bpf.lbBypassFIBLookup`은 지원되는 차트 값이 아닙니다.

공식 튜닝 문서의 netkit/BIG TCP 프로파일에는 커널·NIC·마이그레이션 전제(해당 프로파일은 커널 6.8 포함)가 있습니다. 기존 veth Pod를 값 하나로 전환할 수 없습니다. 문서화된 노드별/새 노드 마이그레이션 경로를 사용하고 암호화·라우팅·애플리케이션 동작을 검증한 뒤 확대합니다.

### 네트워크 스택

먼저 현재 노드 설정을 읽습니다.

```bash
sysctl net.core.somaxconn net.ipv4.tcp_max_syn_backlog \
  net.core.netdev_max_backlog net.ipv4.tcp_fin_timeout net.ipv4.tcp_tw_reuse
```

관련 대기열이나 연결 상태의 병목을 확인하고 대상 커널의 의미를 검토한 후 sysctl을 변경합니다. 이전의 일괄 `sysctl -w` 목록은 워크로드별 튜닝 결과가 아니었습니다. 특히 `tcp_fin_timeout`은 범용 TIME_WAIT 정리 설정이 아니며 TIME_WAIT 재사용도 일반적인 지연 해결책이 아닙니다. 기존 값을 보존하고 관리되는 노드 설정으로 검토한 변경을 배포합니다.

### Envoy

`CiliumEnvoyConfig.spec.resources`는 지정된 xDS 리소스 종류를 받으며 Bootstrap 객체는 받지 않습니다. 이전 CEC 안의 overload-manager Bootstrap은 적용되지 않습니다. fixed-heap 모니터만으로 overload action까지 정의되는 것도 아닙니다.

리소스 제한은 차트에서, 연결 풀은 완전한 [연결 풀 예제](./05-ingress-gateway.md#연결-풀-설정)에서 각각 확인합니다. overload manager는 프로세스 bootstrap에 지원되는 action·임계값과 함께 설정합니다. `envoy.bootstrapConfigMap`을 사용한다면 Cilium에 필요한 bootstrap 연결 구성을 보존하고 정확한 릴리스 Envoy 이미지로 검증합니다. 전체 bootstrap 교체는 고급 연동이며 부분 CEC 패치처럼 취급하지 않습니다.

### 벤치마크 근거

이전 그림의 native/Cilium/Istio p99 0.1/0.3/2.5 ms에는 출처, 버전, 토폴로지, 부하, 암호화 설정, 재현 데이터가 없었습니다. 이를 과거 측정치로 보존하지 않습니다. 근거가 있는 실제 벤치마크는 원래 버전과 날짜를 유지하며 최신 버전으로 이름만 바꾸지 않습니다.

유용한 비교에는 하드웨어, 커널/CNI/메시 버전, 요청 크기, 동시성, 연결, TLS·정책·필터 설정, 준비 시간, 표본 수, 처리량, 오류율, 꼬리 지연을 기록합니다. 동등한 L4 또는 L7·보안 동작을 비교하며 모든 Cilium 경로가 Envoy 없는 메시라고 가정하지 않습니다.

## 사이드카 메시에서 마이그레이션

### CNI 전환과 메시 전환 분리

기존 CNI 옆에 두 번째 CNI를 설치하는 것만으로 전환되지 않습니다. 공식 dual-overlay 마이그레이션에는 분리된 Pod CIDR·캡슐화, 노드별 제어, 워크로드 재생성, 명시적인 정책 적용 절충이 필요하며 검증되지 않은 조합도 있습니다. 실제 플랫폼에서 연습해야 합니다. 이전 그림의 일반적인 “기존 CNI와 함께 설치” 단계는 핵심 전제를 누락했습니다.

Cilium이 이미 네트워킹을 제공한다면 메시 공존은 별도 작업입니다. Cilium Istio 연동 문서에는 kube-proxy를 유지하는 경로가 있습니다.

```yaml
kubeProxyReplacement: false
cni:
  exclusive: false
```

전체 kube-proxy replacement를 계획한 경로는 다음과 같습니다.

```yaml
kubeProxyReplacement: true
socketLB:
  hostNamespaceOnly: true
cni:
  exclusive: false
```

필요한 API 서버·CNI/IPAM·플랫폼 설정을 유지합니다. `cni.exclusive: false`는 Istio CNI 등 다른 CNI 설정을 보존하고, `socketLB.hostNamespaceOnly: true`는 Pod 수준 프록시 가로채기와의 충돌을 피합니다. 오래된 `tunnel: vxlan`은 현재 마이그레이션 절차가 아닙니다. 별도로 overlay를 선택한다면 현재 키 `routingMode`, `tunnelProtocol`과 라우팅·MTU 전제를 사용합니다.

### 워크로드별 전환

변경 전에 `istio-injection`, revision 레이블, Pod 주입 어노테이션, ambient 등록, 기존 사이드카를 기록합니다. 네임스페이스 레이블은 이후 admission에 적용되며 실행 중인 사이드카를 제거하지 않습니다. revision·개별 Pod 설정에 따라 단순 네임스페이스 계획과 다르게 동작할 수 있습니다. 대체 정책과 가용성을 검토한 후 선택한 워크로드만 재생성합니다.

전환 중에도 워크로드별 L7 정책 관리 주체를 하나로 유지합니다. Cilium은 Istio가 암호화한 내부 HTTP 규칙을 검사할 수 없습니다. HTTP 관측만을 위해 Istio mTLS를 끄면 보안이 달라지므로 자동 변환 단계로 삼지 않습니다. ambient HBONE도 Cilium이 L4에서 보는 대상을 바꿉니다. 이 경로를 유지한다면 워크로드 신원과 내부 트래픽 정책은 Istio가 담당하도록 합니다.

### 라우팅 변환 예제

전제는 `app: reviews`, `version: v1` 또는 `v2` 레이블을 갖고 Pod 포트 9080에서 HTTP를 제공하는 준비된 Pod입니다. 별도 Service로 버전 선택을 명시합니다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: reviews
  namespace: default
spec:
  selector:
    app: reviews
  ports:
  - name: http
    port: 9080
    targetPort: 9080
---
apiVersion: v1
kind: Service
metadata:
  name: reviews-v1
  namespace: default
spec:
  selector:
    app: reviews
    version: v1
  ports:
  - name: http
    port: 9080
    targetPort: 9080
---
apiVersion: v1
kind: Service
metadata:
  name: reviews-v2
  namespace: default
spec:
  selector:
    app: reviews
    version: v2
  ports:
  - name: http
    port: 9080
    targetPort: 9080
```

Istio 라우팅에는 VirtualService와 subset 정의가 모두 필요합니다.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-route
  namespace: default
spec:
  hosts:
  - reviews
  http:
  - match:
    - headers:
        end-user:
          exact: jason
    route:
    - destination:
        host: reviews
        subset: v2
  - route:
    - destination:
        host: reviews
        subset: v1
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-subsets
  namespace: default
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

L7 소유권을 이전한 워크로드에서는 완전한 Cilium CEC로 해당 헤더 선택 동작을 구성할 수 있습니다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: reviews-route
  namespace: default
spec:
  services:
  - name: reviews
    namespace: default
    ports:
    - 9080
    listener: reviews-listener
  backendServices:
  - name: reviews-v1
    namespace: default
  - name: reviews-v2
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: reviews-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: reviews-migration
          route_config:
            name: reviews-routes
            virtual_hosts:
            - name: reviews
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                  headers:
                  - name: end-user
                    string_match:
                      exact: jason
                route:
                  cluster: default/reviews-v2
              - match:
                  prefix: /
                route:
                  cluster: default/reviews-v1
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/reviews-v1
    type: EDS
    connect_timeout: 5s
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/reviews-v2
    type: EDS
    connect_timeout: 5s
```

CEC에 Listener, HCM/router, 두 EDS Cluster, 실제 백엔드 Service 참조가 있으며 Cilium이 동적 엔드포인트 설정을 제공합니다. `end-user: jason`은 신뢰되지 않은 라우팅 입력이지 인증이 아닙니다. 이 예제는 Istio의 모든 timeout·retry·mTLS·텔레메트리 동작을 복사하지 않습니다. 각각 비교하고 쓰기 보호에는 [재시도 가이드](./02-traffic-management.md#재시도-설정)를 확인합니다. 같은 활성 경로에 두 구현을 붙이고 동등한 소유 관계라고 가정하지 않습니다.

### 인가는 기계적인 번역이 아님

Pod 포트 8080의 Istio 관리 `app: httpbin` 워크로드에서는 수신 mTLS를 요구하고 인증한 특정 ServiceAccount principal을 허용합니다.

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: httpbin-strict
  namespace: default
spec:
  selector:
    matchLabels:
      app: httpbin
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: httpbin
  namespace: default
spec:
  selector:
    matchLabels:
      app: httpbin
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/default/sa/sleep
    to:
    - operation:
        methods:
        - GET
        paths:
        - /info*
        ports:
        - '8080'
```

동일한 네임스페이스·ServiceAccount 레이블 선택과 GET/경로 의도를 표현하는 Cilium 정책 후보는 다음과 같습니다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: httpbin
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:app: httpbin
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: default
        k8s:io.cilium.k8s.policy.serviceaccount: sleep
    authentication:
      mode: required
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/info.*$
```

별도 Cilium 인증 시스템이 필요하며 Istio 인증서 principal을 소비하지 않습니다. 보안 신원, trust domain, 인증 교환, 암호화 범위가 다릅니다. 포트는 임의로 가정한 Service 포트가 아닌 **Pod 목적지 포트**입니다. 다른 allow 정책이 두 시스템 모두에서 접근을 넓힐 수 있으며 이 ingress 규칙이 Cilium egress까지 거부하지는 않습니다. 허용 GET, 거부 메서드·경로, 잘못된 ServiceAccount, 인증 부재, 암호화·비암호화 경로를 시험한 뒤 동등성을 판단합니다.

### 롤백 계획

원래 워크로드 템플릿, 레이블, 정책, Secret·인증서 소유, Helm values를 배포 시스템에 보관합니다. 마이그레이션이 소유한 리소스를 정확히 기록합니다. 선택한 기존 트래픽·정책 경로를 먼저 복구하고 신원·강제를 확인한 후, 검증한 순서로 교체된 마이그레이션 리소스만 제거합니다.

이전 스크립트는 네임스페이스의 **모든 CiliumNetworkPolicy**를 삭제하여 무관한 기본 거부 보호까지 제거할 수 있으므로 삭제했습니다. 주입 레이블 하나를 켜고 모든 Deployment를 재시작하는 방식도 revision 주입, ambient 등록, StatefulSet, Job을 복구하기에 부족합니다. CNI/IPAM 롤백은 노드·Pod 재생성이 필요할 수 있는 별도 복구 절차입니다.

## 점진적 도입

Cilium이 L3/L4 네트워킹·정책만 담당한다면 관련 L7 기능을 명시적으로 비활성화합니다.

```yaml
l7Proxy: false
envoy:
  enabled: false
ingressController:
  enabled: false
gatewayAPI:
  enabled: false
```

`envoy.enabled: false`만 설정하면 L7이 활성화된 경우 embedded Envoy 모드를 선택하며 모든 Cilium L7 기능을 끄지 않습니다. 기존 L7 정책, Ingress/Gateway, CEC 목록을 확인한 후 기능을 제거합니다. Istio ambient에서는 일반 평문 트래픽과 달리 Cilium에 원래 내부 워크로드 흐름 대신 HBONE 전송이 보입니다.

| 단계 | L7 소유 관계와 완료 조건 |
|---|---|
| 네트워킹 확립 | 기존 메시의 의도한 소유 관계를 유지하면서 Cilium CNI/L3/L4 동작 검증 |
| 선택 워크로드 전환 | 워크로드별 소유 분리, 라우팅·신원·암호화·재시도·텔레메트리와 거부 테스트 비교 |
| 기존 구성 요소 종료 | 모든 의존 워크로드와 복구 절차를 확인한 후 제거 |

이전 전환 그림은 모든 정책 삭제 롤백과 단순화한 공존 절차를 반복하여 위 표로 대체했습니다.

## 모니터링 및 알림

### 명시적 수집 레이블

먼저 Prometheus Operator CRD와 ServiceMonitor/PrometheusRule 선택자를 구성합니다. 다음 오버라이드는 예제 job 이름과 cluster 레이블을 고정합니다. `example-cluster`는 실제 클러스터 식별자로 일관되게 교체하고 `release` 선택자도 맞춥니다.

```yaml
prometheus:
  enabled: true
  serviceMonitor:
    enabled: true
    labels:
      release: prometheus
    relabelings:
    - sourceLabels:
      - __meta_kubernetes_pod_node_name
      targetLabel: node
    - targetLabel: cluster
      replacement: example-cluster
    - targetLabel: job
      replacement: cilium-agent
envoy:
  prometheus:
    enabled: true
    serviceMonitor:
      enabled: true
      labels:
        release: prometheus
      relabelings:
      - sourceLabels:
        - __meta_kubernetes_pod_node_name
        targetLabel: node
      - targetLabel: cluster
        replacement: example-cluster
      - targetLabel: job
        replacement: cilium-envoy
```

Hubble HTTPv2 context와 기록 규칙은 [관측성 가이드](./04-observability.md)에서 별도로 구성합니다. 필요한 가시성이 있는 트래픽에만 L7 관측이 생깁니다. 신뢰한 내부 메트릭 경로를 사용하며 이 values가 원격 Prometheus 연결까지 설정하지는 않습니다.

### 운영 규칙

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: cilium-operational-signals
  namespace: monitoring
  labels:
    release: prometheus
spec:
  groups:
  - name: cilium.operational
    rules:
    - alert: CiliumMetricsScrapeFailed
      expr: up{job=~"cilium-agent|cilium-envoy"} == 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Known Cilium metrics target cannot be scraped
    - alert: HighObservedPacketDrops
      expr: sum by (cluster, node, direction, reason) (rate(cilium_drop_count_total[5m]))
        > 1000
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: High observed packet drop count
    - alert: HighBPFMapPressure
      expr: cilium_bpf_map_pressure > 0.8
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: High pressure in an instrumented BPF map
```

`up` 수집 실패는 대상 접근 실패이며 Agent/Envoy 프로세스 정지와 항상 같지는 않습니다. discovery에서 대상이 사라지면 `up` 시계열도 없어질 수 있으므로 예상 노드·DaemonSet 목록을 별도로 비교합니다. `cilium_proxy_redirects`는 설치된 리다이렉트 수로 정상적으로 0일 수 있으며 Envoy liveness가 아닙니다.

이전 `cilium_datapath_conntrack_active/max` 비율은 존재하지 않는 메트릭을 사용했습니다. CT GC 관측도 순간 전체 용량 게이지가 아닙니다. 맵 압력은 계측된 맵과 출력 조건에 따라 달라지므로 실제 존재하는 맵을 확인합니다. 위 드롭·압력 임계값은 설명용이며 트래픽, 원인, 지속 시간, 의도된 정책 거부에 맞게 조정합니다.

### 대시보드 가져오기

Grafana UI에 가져오는 독립 classic dashboard JSON이며 HTTP API wrapper가 아닙니다. Prometheus 데이터 소스를 선택하고 관측성 가이드의 `cilium_hubble:*` 기록 규칙을 먼저 설치합니다.

```json
{
  "__inputs": [
    {
      "name": "DS_PROMETHEUS",
      "label": "Prometheus",
      "type": "datasource",
      "pluginId": "prometheus",
      "pluginName": "Prometheus"
    }
  ],
  "id": null,
  "uid": "cilium-operational",
  "title": "Cilium operational signals",
  "tags": [
    "cilium",
    "hubble"
  ],
  "schemaVersion": 38,
  "version": 1,
  "timezone": "browser",
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "refresh": "30s",
  "panels": [
    {
      "id": 10,
      "title": "Successfully scraped agent targets",
      "type": "stat",
      "gridPos": {
        "x": 0,
        "y": 0,
        "w": 12,
        "h": 8
      },
      "datasource": {
        "type": "prometheus",
        "uid": "${DS_PROMETHEUS}"
      },
      "targets": [
        {
          "refId": "A",
          "expr": "sum by (cluster) (up{job=\"cilium-agent\"})",
          "legendFormat": "{{cluster}}"
        }
      ]
    },
    {
      "id": 1,
      "title": "Observed HTTP responses/s",
      "type": "timeseries",
      "gridPos": {
        "x": 12,
        "y": 0,
        "w": 12,
        "h": 8
      },
      "datasource": {
        "type": "prometheus",
        "uid": "${DS_PROMETHEUS}"
      },
      "targets": [
        {
          "refId": "A",
          "expr": "cilium_hubble:http_responses:rate5m",
          "legendFormat": "{{cluster}} / {{destination_namespace}} / {{destination_workload}}"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "reqps"
        },
        "overrides": []
      }
    },
    {
      "id": 2,
      "title": "Observed HTTP5xx (%)",
      "type": "timeseries",
      "gridPos": {
        "x": 0,
        "y": 8,
        "w": 12,
        "h": 8
      },
      "datasource": {
        "type": "prometheus",
        "uid": "${DS_PROMETHEUS}"
      },
      "targets": [
        {
          "refId": "A",
          "expr": "cilium_hubble:http_5xx_percent:rate5m",
          "legendFormat": "{{cluster}} / {{destination_namespace}} / {{destination_workload}}"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "percent"
        },
        "overrides": []
      }
    },
    {
      "id": 3,
      "title": "Observed HTTP P99",
      "type": "timeseries",
      "gridPos": {
        "x": 12,
        "y": 8,
        "w": 12,
        "h": 8
      },
      "datasource": {
        "type": "prometheus",
        "uid": "${DS_PROMETHEUS}"
      },
      "targets": [
        {
          "refId": "A",
          "expr": "histogram_quantile(0.99, cilium_hubble:http_latency_bucket:rate5m)",
          "legendFormat": "{{cluster}} / {{destination_namespace}} / {{destination_workload}}"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "s"
        },
        "overrides": []
      }
    }
  ]
}
```

상태 패널은 “정상 Pod 수”가 아니라 수집에 성공한 Agent 대상 수입니다. HTTP 패널은 기록 규칙의 서버 측 관측 경계, 네임스페이스·워크로드·클러스터 범위, 누락 분자 처리를 따릅니다. 데이터 없음은 실패 0이 아니며 명시한 데이터 소스와 레이블이 필요합니다.

## 업그레이드 전략

### 롤아웃 전 검토

Cilium이 시험한 업그레이드·롤백 경로는 **인접한 minor 릴리스 사이**입니다. 현재 minor의 최신 patch로 먼저 올리고 거치는 각 릴리스의 필수 변경을 읽습니다. 아래 대상은 1.20.1이며 과거 1.16/1.17 예제에서 직접 건너뛰는 지원 경로가 아닙니다.

`upgradeCompatibility`에는 임의의 현재·대상 버전이 아닌 **최초 설치 minor**를 기록합니다. 기존 사용자 values를 내보내고 이름 변경·제거된 키를 검토한 후 `reviewed-values.yaml`로 저장합니다. 민감한 내용이 포함될 수 있으므로 해당 파일과 내보낸 값을 보호합니다.

```bash
set -eu
umask 077
CILIUM_TARGET_VERSION=1.20.1
: "${INITIAL_CILIUM_MINOR:?Set the initial installed Cilium minor, for example 1.19}"
helm get values cilium -n kube-system -o yaml > old-values.yaml
helm history cilium -n kube-system
helm repo add cilium https://helm.cilium.io/
helm repo update cilium
test -s reviewed-values.yaml
helm template cilium cilium/cilium -n kube-system \
  --version "$CILIUM_TARGET_VERSION" -f reviewed-values.yaml \
  --set-string "upgradeCompatibility=$INITIAL_CILIUM_MINOR" > candidate.yaml
```

생성 리소스와 공식 preflight 절차를 검토한 후 다음 단계로 진행합니다. `helm diff`는 별도 설치하는 선택적 플러그인이지 Helm 내장 명령이 아닙니다. 버전 변경 시 `--reuse-values`는 새 차트 기본값을 숨길 수 있으므로 피합니다.

지원되는 경로와 유지보수·복구 계획을 확인한 후 같은 셸/세션에서 검토한 변경을 수행할 수 있습니다.

```bash
set -eu
: "${CILIUM_TARGET_VERSION:?Use the previously reviewed target version}"
: "${INITIAL_CILIUM_MINOR:?Use the previously reviewed initial installed minor}"
helm upgrade cilium cilium/cilium -n kube-system \
  --version "$CILIUM_TARGET_VERSION" -f reviewed-values.yaml \
  --set-string "upgradeCompatibility=$INITIAL_CILIUM_MINOR" --wait --timeout 10m
cilium status --wait
kubectl -n kube-system get daemonset cilium cilium-envoy
kubectl -n kube-system get deployment cilium-operator hubble-relay
```

`cilium connectivity test`는 테스트 워크로드와 네트워크 트래픽을 만드는 **능동 검증**입니다. 읽기 전용 상태 명령으로 가정하지 말고 계획한 테스트 환경에서 실행합니다. 구성 요소 준비 상태 외에도 애플리케이션별 거부 정책과 장기 연결을 검증합니다.

### 카나리 전략

노드 레이블만으로 Cilium 버전이 바뀌지 않습니다. Agent는 노드 네트워킹 리소스와 클러스터 설정을 공유하므로 겹치는 두 번째 Cilium DaemonSet을 배포해 카나리를 만들지 않습니다. 대표 테스트 클러스터에서 릴리스를 먼저 검증합니다. 노드별 제어 롤아웃도 지원되는 단일 관리 방식, Operator·공유 ConfigMap 변경, 제한된 임시 버전 차이를 고려해야 합니다. 정상 운영 상태에서는 모든 Cilium 구성 요소가 같은 릴리스여야 합니다.

### 롤백

새 CRD·기능·상태가 안전한 다운그레이드를 막는지 확인한 뒤 **검토한 호환 Helm revision**을 선택합니다.

```bash
set -eu
helm history cilium -n kube-system
: "${CILIUM_ROLLBACK_REVISION:?Set the reviewed, compatible Helm revision}"
helm rollback cilium "$CILIUM_ROLLBACK_REVISION" \
  -n kube-system --wait --timeout 10m
cilium status --wait
```

무조건 1.15로 내리거나 Helm revision 롤백이 노드 네트워킹, CRD 스키마, 새로 사용한 모든 기능까지 되돌린다고 가정하지 않습니다. 릴리스별 롤백 전제와 복구 테스트를 변경 기록에 함께 남깁니다.

## 트러블슈팅

### 노드와 정책 상태

```bash
cilium status --wait
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
kubectl -n kube-system exec ds/cilium -- cilium-dbg endpoint list
kubectl -n kube-system exec ds/cilium -- cilium-dbg policy get
kubectl -n kube-system exec ds/cilium -- cilium-dbg service list
kubectl -n kube-system exec ds/cilium -- cilium-dbg bpf ct list global
```

호스트의 `cilium` CLI는 설치를 관리하고 Agent 내부 `cilium-dbg`는 로컬 데이터 플레인을 조사합니다. `exec ds/cilium`은 Pod 하나를 선택하므로 장애 시 실제 영향받은 노드의 Pod를 지정합니다. CT 목록은 출력이 클 수 있고 `wc -l`이 신뢰할 수 있는 점유율 측정은 아닙니다.

### Envoy와 지연

```bash
kubectl -n kube-system exec ds/cilium -- cilium-dbg status --verbose
kubectl -n kube-system exec ds/cilium -- cilium-dbg envoy admin config listeners
kubectl -n kube-system exec ds/cilium -- cilium-dbg envoy admin config routes
kubectl -n kube-system exec ds/cilium -- cilium-dbg envoy admin config clusters
kubectl -n kube-system exec ds/cilium -- cilium-dbg envoy admin metrics
```

포트 9901의 인증 없는 TCP 리스너나 컨테이너 내부 `curl`을 가정하지 말고 지원되는 admin 명령·소켓 경로를 사용합니다. L7 리다이렉트 부재, 업스트림 불가, 정책 거부, 연결 포화, 느린 애플리케이션 응답을 구분합니다. Ingress/Gateway·관측성 가이드의 실제 히스토그램 단위와 레이블을 적용합니다.

### 임시 디버그와 로그

```yaml
debug:
  enabled: true
  verbose: flow envoy policy
```

`debug.verbose`는 boolean 맵이 아니라 공백으로 구분한 문자열입니다. 조사 기간에 필요한 그룹만 활성화하고 이후 원래 로그 수준으로 복구합니다.

```bash
kubectl -n kube-system logs -l k8s-app=cilium -c cilium-agent --since=30m --tail=1000
kubectl -n kube-system logs -l k8s-app=cilium-envoy -c cilium-envoy --since=30m --tail=1000
cilium sysdump --output-filename cilium-audit
```

별도 Envoy DaemonSet의 선택자는 `k8s-app=cilium-envoy`입니다. sysdump는 클러스터 접근을 사용하는 수집 작업이며 민감한 설정·로그가 포함될 수 있으므로 공유 전에 압축 파일을 검사합니다. 호스트에서 단순히 `cilium-bugtool`만 실행하는 명령이 아닙니다.

## EKS 전용 안내

### ENI 모드와 AWS VPC CNI Chaining

서로 다른 설계입니다. Cilium ENI IPAM은 Operator로 ENI·주소를 관리하고, AWS VPC CNI chaining은 주소 할당을 AWS VPC CNI에 맡기며 별도 L7·암호화 제약이 있습니다. 해당 설치 절차를 선택합니다.

IPv4 ENI 오버라이드는 다음과 같습니다.

```yaml
eni:
  enabled: true
ipam:
  mode: eni
routingMode: native
ipv4:
  enabled: true
ipv6:
  enabled: false
cluster:
  name: example-cluster
```

`eni.enabled`는 AWS Operator 동작과 관련 차트 기본값을 선택합니다. ENI garbage collection 소유 관계가 모호해지지 않도록 고유한 클러스터 이름을 유지합니다. ENI 모드에 범용 `10.0.0.0/8` cluster-pool 범위를 추가하지 않고, 실제 노드 장치·라우팅 전제를 확인하지 않은 masquerade 인터페이스를 고정하지 않습니다.

`enableAWSSecurityGroups`는 차트 값이 아닙니다. ENI 보안 그룹은 지원되는 `eni.nodeSpec.securityGroups`/`securityGroupTags`나 문서화된 상속 동작으로 정합니다. Kubernetes 정책을 AWS SecurityGroupPolicy로 자동 변환하는 기능이 아닙니다.

**일반 ENI IPAM 문서는 IPv6를 Beta로 설명**하며 dual-stack 서브넷·prefix·IAM 전제를 제공합니다. 반면 1.20.1 EKS 설치 페이지에는 IPv4 전용 문구가 남아 있습니다. 여기서는 IPv4 예제를 사용하고 이 근거 차이를 기록합니다. Beta 기능을 없다고 하거나 일반 문서만으로 완전히 검증한 EKS IPv6 절차라고 주장하지 않습니다.

EKS Auto Mode와 Fargate에는 이 대체 CNI DaemonSet 설치 경로를 적용할 수 없습니다. EKS Hybrid Nodes는 별도 AWS 지원 Cilium 안내·호환성 범위를 따르며, 그 지원 주장을 임의의 자체 관리 EC2 Cilium 릴리스로 확장하지 않습니다.

### 노드 OS와 용량

EKS는 **2025년 11월 26일** EKS 최적화 AL2 AMI 공개를 종료했고 마지막 Kubernetes 계열은 1.32였습니다. 적절한 지원 AL2023 또는 Bottlerocket AMI를 선택하고 실제 커널·아키텍처와 Cilium 기능 전제를 검증합니다. 일반 Linux 호환성 표에 AL2가 나온다는 사실이 현재 EKS AMI 지원을 뜻하지 않습니다.

측정한 CPU·메모리·네트워크/패킷 한계, ENI/IP 용량, 가용성, 비용으로 인스턴스 계열과 크기를 고릅니다. 이전의 고정 m6i/c6i/r6i 추천은 사이징 벤치마크가 아니었습니다. 혼합 아키텍처를 사용하면 모든 DaemonSet·워크로드 이미지가 AMD64와 Arm64를 지원하는지 확인합니다.

### IAM

지원되는 설치 신원 방식으로 Cilium Operator 전용 역할을 사용하고 trust policy와 자격 증명 접근을 별도로 검토합니다. 이전 정책에는 `AttachNetworkInterface`, `DescribeInstanceTypes`, `DescribeRouteTables`, `CreateTags` 등 필수 작업이 빠져 있어 완전한 ENI 할당 정책이 아니었습니다.

버전 고정 ENI 문서는 기본·조건부 API 권한을 구분합니다. ENI garbage collection, 초과 IP 반환, instance 필터, 선택적 IPv6 할당을 고려합니다. AWS 서비스 인가 지원에 따라 읽기·목록과 변경 권한을 나누고 지원되는 변경 작업은 의도한 리전·리소스·태그로 제한합니다. 일부 describe 작업에는 `Resource: "*"`가 필요하므로 wildcard 하나만으로 올바름이나 과도한 권한을 단정하지 않습니다. 계정별 최소 권한 정책에는 실제 IAM·리소스 문맥과 API 검증이 필요하며 이 문서에서 이를 프로비저닝했다고 주장하지 않습니다.

## 추가 자료

완전한 전제와 예제는 [보안](./03-security.md), [관측성](./04-observability.md), [Ingress/Gateway](./05-ingress-gateway.md) 가이드를 이어서 확인합니다.

- [Cilium 1.20.1 Helm values](https://github.com/cilium/cilium/blob/v1.20.1/install/kubernetes/cilium/values.yaml)
- [System requirements](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/operations/system_requirements.rst)
- [Performance tuning](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/operations/performance/tuning.rst)
- [Upgrade procedure](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/operations/upgrade.rst)
- [Upgrade and rollback restrictions](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/operations/upgrade-warning.rst)
- [Istio integration](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/istio.rst)
- [CNI migration](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/installation/k8s-install-migration.rst)
- [CEC resource parser](https://github.com/cilium/cilium/blob/v1.20.1/pkg/ciliumenvoyconfig/cec_resource_parser.go)
- [ENI allocation, security groups and permissions](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/ipam/eni.rst)
- [EKS installation caveats](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/installation/requirements-eks.rst)
- [EKS AL2 AMI retirement](https://docs.aws.amazon.com/eks/latest/userguide/eks-ami-deprecation-faqs.html)
- [EKS alternate CNI support](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)
- [Cilium Envoy diagnostics](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/cmdref/cilium-dbg_envoy_admin_config.md)
- [Linux TCP sysctls](https://docs.kernel.org/networking/ip-sysctl.html)
- [Kubernetes disruption budgets](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [IAM resource-level permission troubleshooting](https://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot_policies.html)
