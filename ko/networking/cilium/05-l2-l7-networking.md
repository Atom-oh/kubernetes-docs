# L2–L7 네트워킹 및 로드 밸런싱

> **검토 기준**: Cilium 1.20.1, CLI 0.20.0. Istio 예제는 1.31 API를 사용합니다.
> **최종 검토**: 2026년 9월 12일

## 실습 환경 설정

[설치](README.md)·[네트워킹](03-networking.md) 가이드로 준비한 일회용 클러스터에서 플랫폼·커널 지원과 kubectl 버전 차이를 확인합니다. HTTP 실습에는 스케줄링 가능한 Linux 노드 두 개가 필요합니다. DSR/Maglev 실험에는 준비된 kube-proxy-free 클러스터, 실제 API 서버 연결과 지원되는 네트워크 경로가 추가로 필요합니다.

실험에 맞는 전체 설치 값을 선택합니다. `cilium install --config ...` 반복은 실행 중 기능 전환 절차가 아니며 임의 설치 후 kube-proxy를 삭제하는 것도 안전한 지름길이 아닙니다.

## OSI 계층 이해

OSI는 개념적 모델이며 Cilium 프로세스 일곱 개나 고정된 정책 훅 순서를 뜻하지 않습니다.

| 계층 | 역할·예 | Cilium과의 관계 |
|---|---|---|
| L1 물리 | Bit, 매체, transceiver, repeater | 기반 하드웨어·네트워크 조건 |
| L2 데이터 링크 | Ethernet frame, MAC 주소, bridge·switch | 패킷 처리와 명시적으로 구성한 L2 Service 광고 |
| L3 네트워크 | IP packet, routing, ICMP | 라우팅, identity·CIDR 정책, 지원 fragment 처리 |
| L4 전송 | TCP segment·신뢰할 수 있는 stream, 전달·순서 보장이 없는 UDP datagram | Port·protocol 정책, 연결 상태, Service 변환 |
| L5 세션 | Session·dialog 조직 | 실제 애플리케이션·프로토콜 안에 구현되는 개념적 기능 |
| L6 표현 | 표현·인코딩·암호 변환 | TLS를 개념적으로 배치하기도 하지만 보편적인 별도 Linux 계층은 아님 |
| L7 응용 | HTTP, DNS, gRPC 등 | 지원 proxy 정책. 프로토콜이 존재한다고 Cilium 정책 parser가 있는 것은 아님 |

### 실제 계층별 기능

- **L2:** L2 Announcements는 적격 Service IP에 ARP/NDP로 응답하는 설정형 beta 기능입니다. Kube-proxy 대체와 적절한 장치·로컬 네트워크 연결이 필요하며 선출된 노드가 해당 Service 트래픽을 받습니다. 임의 MAC/VLAN ACL이나 일반 L2 bridge·모든 패킷 캡처 보장이 아닙니다. `externalTrafficPolicy: Local`과의 비호환성이 문서화되어 있습니다.
- **L3:** IP·identity 정책과 라우팅에는 모드별 조건이 있습니다. Multicast는 VXLAN이 필요한 별도 beta 기능이며 문서상 최소 커널은 AMD64 5.10, AArch64 6.0입니다. 모든 라우팅 모드에서 된다고 가정하지 않습니다.
- **L4:** TCP/UDP port 정책, conntrack, socket·packet Service LB, 지원 affinity는 다른 훅에서 작동합니다. Socket 선택은 패킷 생성 전일 수 있습니다.
- **L7:** 현재 내장 정책 그룹은 HTTP와 DNS입니다. gRPC는 지원 HTTP/2 경로를 사용하고 Kafka L7 규칙은 제거되었습니다. TLS/SNI 기능에는 문서화된 proxy 설정이 필요하며 암호화된 내용을 자동 검사하지 않습니다.

HTTP/gRPC 정책은 Envoy, DNS는 Cilium DNS proxy가 담당합니다. Envoy는 values·upgrade compatibility에 따라 agent 관리 프로세스 또는 `cilium-envoy` DaemonSet일 수 있습니다. L7을 켠 새 1.20 chart 기본값은 DaemonSet을 사용하며 아래 프로필은 이를 명시합니다. 정책 추가가 모든 설치 설정을 덮어쓰지는 않습니다.

## HTTP 정책 실습

새 namespace와 일치하는 workload를 만듭니다. 이미지·digest와 확인된 server readiness 경로는 공식 CLI 테스트 배포 정의에 근거합니다.

```bash
set -euo pipefail
kubectl create namespace cilium-l2l7-demo
kubectl label namespace cilium-l2l7-demo docs-audit-lab=cilium-l2l7-05
```

이미 존재하면 중단하고 모든 곳에 새 이름을 일관되게 사용합니다. 다른 실행의 리소스를 재사용하지 않습니다.

**`l7-app.yaml`**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: cilium-l2l7-demo
  labels:
    app: client
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
  namespace: cilium-l2l7-demo
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
  name: app1
  namespace: cilium-l2l7-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: app1
  template:
    metadata:
      labels:
        app: app1
    spec:
      automountServiceAccountToken: false
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: client
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
  name: app1-service
  namespace: cilium-l2l7-demo
spec:
  selector:
    app: app1
  ports:
  - name: http
    port: 80
    targetPort: http
    protocol: TCP
```


```bash
kubectl apply -f l7-app.yaml
kubectl -n cilium-l2l7-demo wait --for=condition=Ready pod/client pod/outsider --timeout=120s
kubectl -n cilium-l2l7-demo rollout status deployment/app1 --timeout=120s
kubectl -n cilium-l2l7-demo get pods,services -o wide
kubectl -n cilium-l2l7-demo exec client -- \
  curl --fail --silent --show-error --max-time 5 http://app1-service/
```

Outsider의 기준 연결도 확인합니다. Service는 80을 노출하지만 backend는 **8080**을 수신하므로 Pod ingress 정책은 backend port를 사용합니다. 이전의 없거나 맞지 않는 앱 설정과 정책 label·entrypoint가 다른 client Pod를 교정한 예제입니다.

**`app1-http.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: app1-http
  namespace: cilium-l2l7-demo
spec:
  endpointSelector:
    matchLabels:
      app: app1
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-l2l7-demo
        k8s:app: client
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/$
        - method: ^POST$
          path: ^/api/v1$
          headerMatches:
          - name: x-demo-tenant
            value: team-a
```


```bash
kubectl apply -f app1-http.yaml
kubectl -n cilium-l2l7-demo get cnp app1-http -o yaml
```

정책 실현 후 지정 client의 GET `/`를 허용합니다. POST `/api/v1`은 이 규칙상 정확한 `x-demo-tenant: team-a`가 있어야 하며 backend도 해당 API를 구현해야 합니다. 다른 method·path·peer 거부는 다른 적용 정책의 허용이 없는 범위에서 성립합니다. 애플리케이션 응답과 실현 정책·플로우를 함께 확인합니다.

이 header는 **실습용 필터이지 인증이 아닙니다**. 이전 32문자 “토큰” 조건은 신원·서명·발급자·만료·인가를 검증하지 않습니다. 릴리스 구현에서 값이 있는 `headers` 문자열은 리터럴 비교입니다. `X-Auth-Token: ^[a-zA-Z0-9]{32}$`는 정규식 토큰 검증기가 아닙니다. 정확한 값·존재 조건에는 명시적인 `headerMatches`를 사용하고 사용자 인증은 애플리케이션·적절한 인증 계층에서 처리합니다.

Method·path는 정규식을 지원합니다. 내장 Cilium HTTP 정책에는 임의 요청 본문 조건이 없습니다. Header 존재, 정확한 값, URL 필터, 애플리케이션 인가는 다른 제어입니다.

## 서비스 메시 통합

Cilium은 네트워킹·지원 네트워크 정책을, Istio는 구성한 proxy·mesh 동작을 담당합니다. 통합으로 Istio sidecar를 자동 우회하거나 mTLS 비용을 제거하거나 모든 trace를 합치거나 요청 성능 향상을 보장하지 않습니다.

```text
설정: istiod --> Istio Envoy proxy
요청: app --> source sidecar --> Cilium/network --> destination sidecar --> app
```

### Istio 트래픽 경로 보존

현재 Cilium 통합 가이드는 kube-proxy 공존과 신중히 구성한 완전 대체 방식을 제공합니다. 공존 설정 조각은 다음과 같습니다.

**`istio-cilium-values.yaml`**

```yaml
kubeProxyReplacement: false
socketLB:
  hostNamespaceOnly: true
cni:
  exclusive: false
```


의도적으로 준비한 대체 구성의 `kubeProxyReplacement: true`에는 실제 API endpoint와 대체 조건이 추가로 필요합니다. Pod socket 변환이 Istio 경로를 우회하지 않도록 `socketLB.hostNamespaceOnly: true`, 노드 CNI 설정을 공유할 때 `cni.exclusive: false`를 유지합니다.

Istio sidecar redirection은 init container 또는 Istio CNI node agent를 사용할 수 있고 ambient는 해당 node·CNI 경로를 사용합니다. [유지보수되는 Istio 설치 가이드](../../service-mesh/istio/01-installation.md)에서 한 모드를 선택합니다. Kubernetes API 서버가 Istio admission webhook에 도달해야 합니다. 관리형 제어플레인·overlay 환경에는 문서화된 routing·host-network 대책이 필요할 수 있지만 모든 overlay에 `istiod hostNetwork: true`를 처방하지 않습니다.

### mTLS 유지와 L7 책임 분리

Istio가 암호화한 workload 트래픽에 평문 Cilium HTTP 검사를 적용하지 않습니다. 아래 예제는 Istio mTLS·L7 routing을 유지하고 Cilium에는 **L3/L4 정책만** 사용합니다. 이전 이중 L7 예제를 통과시키려고 mTLS를 끄면 보안 설계가 바뀝니다.

이미 준비된 `istio-cilium-demo` namespace에 `productpage`, `reviews`, 9080 reviews Service와 `version: v1`/`v2` Pod가 있는 **sidecar 모드** 구성입니다. 완전한 Bookinfo 배포가 아닙니다.

**`istio-reviews.yaml`**

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-route
  namespace: istio-cilium-demo
spec:
  hosts:
  - reviews.istio-cilium-demo.svc.cluster.local
  http:
  - match:
    - headers:
        end-user:
          exact: jason
    route:
    - destination:
        host: reviews.istio-cilium-demo.svc.cluster.local
        subset: v2
        port:
          number: 9080
  - route:
    - destination:
        host: reviews.istio-cilium-demo.svc.cluster.local
        subset: v1
        port:
          number: 9080
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-subsets
  namespace: istio-cilium-demo
spec:
  host: reviews.istio-cilium-demo.svc.cluster.local
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
---
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-cilium-demo
spec:
  mtls:
    mode: STRICT
---
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: reviews-l4
  namespace: istio-cilium-demo
spec:
  endpointSelector:
    matchLabels:
      app: reviews
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: istio-cilium-demo
        k8s:app: productpage
    toPorts:
    - ports:
      - port: '9080'
        protocol: TCP
```


DestinationRule이 VirtualService의 subset을 정의합니다. `end-user: jason`은 실습 route 선택이며 인증된 identity가 아닙니다. 실제 주입, endpoint label, subset readiness와 mesh telemetry를 확인합니다.

9080 Cilium 규칙을 ambient 예제로 재사용하지 않습니다. Ambient HBONE은 15008의 암호화된 터널이며 관측 트래픽·identity 경계가 달라집니다. 해당 topology의 Istio 정책과 플랫폼별 Cilium 네트워크 제어를 적용합니다.

## 로드 밸런싱 아키텍처

Cilium service map, backend map, reverse-NAT 상태와 conntrack은 서로 다른 전달 단계를 담당합니다. L7 Envoy LB는 다른 구성 요소이므로 BPF Service datapath와 알고리즘 목록을 합치지 않습니다.

### BPF 전달 모드와 알고리즘

| 설정·메커니즘 | 의미와 경계 |
|---|---|
| `loadBalancer.mode: snat` | 기본 전달 모드. 해당 외부 Service 경로에 직접 반환 대신 소스 변환·역방향 상태 사용 |
| `dsr` | 원격 backend 응답이 진입 LB 노드를 우회할 수 있음. 반환 경로가 허용되어야 하며 앞단 proxy가 바꾼 client IP를 복구하지 못함 |
| `hybrid` | TCP는 DSR, UDP는 SNAT. 잘못된 tunnel/auto-direct-routing 조합과 다른 유효한 LB 기능 |
| Annotation 기반 전달 | 선택적 Service별 동작. Forwarding annotation은 생성 시 선택하며 변경하면 연결이 끊길 수 있음 |
| `loadBalancer.algorithm: random` | 기본 BPF backend 선택 알고리즘 |
| `maglev` | 지원되는 외부 N–S 경로와 XDP의 일관된 선택. 일반 socket-LB E–W 연결에는 적용되지 않음 |
| `sessionAffinity: ClientIP` | 별도 Kubernetes Service affinity. 외부 source IP 또는 해당 내부 socket-LB 경로의 client network-namespace cookie 사용 |

Maglev가 backend 제거 후 session 생존을 보장하지 않습니다. 노드의 backend 상태·table size·seed가 일치해야 합니다. 기본 크기는 16381이며 아래 65521은 허용 값이지 보편적 권장값은 아닙니다. 큰 table은 메모리를 더 사용하고 affinity 만료·연결 상태는 hashing과 별개입니다.

DSR dispatch는 native-routing IP option, 문서화된 native/Geneve-overlay의 Geneve 또는 native 전용 IPIP/IP6IP6 경로를 사용할 수 있습니다. VXLAN overlay를 Geneve DSR로 그대로 바꿔 생각하면 안 됩니다. IPIP에는 별도 port·변환 제약이 있으므로 선택 전 릴리스 가이드를 확인합니다.

XDP 가속에는 지원 장치·driver가 필요합니다. `native`는 선택 장치의 지원을 전제로 하고 `best-effort`는 지원 장치에서만 켭니다. 예전 `enable-xdp-acceleration` 키만 쓰면 되는 기능이 아니며 초기 XDP 전달은 후단 tcpdump 지점에 보이지 않을 수 있습니다.

### Cilium과 kube-proxy

| 항목 | 올바른 비교 |
|---|---|
| Linux Service 구현 | Cilium은 BPF hook·map, kube-proxy는 iptables·nftables 및 Kubernetes 1.35부터 폐기 예정인 IPVS |
| 플랫폼 | Cilium의 Linux·kernel 조건 적용. Windows kernelspace kube-proxy는 별도 구현 |
| 연결 상태 | Cilium BPF conntrack·NAT와 Linux netfilter conntrack은 다름. “선택적 대 항상”은 지나친 단순화 |
| L7 | Cilium은 지원 proxy를 통합하며 kube-proxy Service 전달은 HTTP 정책 엔진이 아님 |
| 성능 | 동일 workload·설정으로 측정. 제품 이름으로 고정 순위가 결정되지 않음 |

Linux IPVS 하위 시스템에 direct-routing 기능이 있다고 kube-proxy에도 동일한 DSR 설정이 있다고 추론하지 않습니다.

## 준비된 DSR/Maglev 실습

새로 준비한 kube-proxy-free **IPv4 Geneve-overlay** 테스트 클러스터용 프로필입니다. 기존 CNI 전환, kube-proxy 제거, 클라우드 anti-spoofing·routing 설정을 수행하지 않습니다. 겹치지 않는 Pod CIDR과 외부 반환 경로를 검증합니다.

**`lb-values.yaml`**

```yaml
kubeProxyReplacement: true
routingMode: tunnel
tunnelProtocol: geneve
ipv4:
  enabled: true
ipv6:
  enabled: false
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
loadBalancer:
  mode: dsr
  dsrDispatch: geneve
  algorithm: maglev
  acceleration: disabled
maglev:
  tableSize: 65521
bpf:
  masquerade: true
enableIPv4Masquerade: true
enableIPv6Masquerade: false
l7Proxy: true
envoy:
  enabled: true
hubble:
  enabled: true
  relay:
    enabled: true
```


실제 API endpoint와 클러스터별로 보존한 Maglev seed를 지정합니다. Seed는 무작위 12바이트의 base64 인코딩입니다. 한 번 생성해 cluster values와 함께 보존·재사용하며 업그레이드마다 다시 만들지 않습니다.

```bash
: "${API_SERVER_HOST:?Set the reachable real API server host, not its ClusterIP}"
: "${API_SERVER_PORT:?Set the actual API server port}"
: "${MAGLEV_SEED:?Set the persisted base64 encoding of 12 random bytes}"
helm repo add cilium https://helm.cilium.io/
helm repo update cilium
helm install cilium cilium/cilium --version 1.20.1 --namespace kube-system \
  --values lb-values.yaml \
  --set-string k8sServiceHost="$API_SERVER_HOST" \
  --set k8sServicePort="$API_SERVER_PORT" \
  --set-string maglev.hashSeed="$MAGLEV_SEED"
cilium status --wait
```

선택한 클러스터에서 이 가이드가 만든 namespace를 사용합니다. 다른 일회용 클러스터라면 먼저 해당 클러스터에서 namespace 생성·label 단계를 반복합니다. 앞선 client 전용 HTTP 정책이 실험을 막지 않도록 HTTP 앱과 외부 LB backend의 label을 구분했습니다.

**`lb-echo.yaml`**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lb-echo
  namespace: cilium-l2l7-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: lb-echo
  template:
    metadata:
      labels:
        app: lb-echo
    spec:
      automountServiceAccountToken: false
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
  name: lb-echo
  namespace: cilium-l2l7-demo
spec:
  type: NodePort
  selector:
    app: lb-echo
  ports:
  - name: http
    port: 80
    targetPort: http
    protocol: TCP
```


```bash
kubectl apply -f lb-echo.yaml
kubectl -n cilium-l2l7-demo rollout status deployment/lb-echo --timeout=120s
kubectl -n cilium-l2l7-demo get pods -l app=lb-echo -o wide
kubectl -n cilium-l2l7-demo get service lb-echo -o wide
NODEPORT=$(kubectl -n cilium-l2l7-demo get service lb-echo -o jsonpath='{.spec.ports[0].nodePort}')
```

**Backend와 다른 진입 노드** 및 클러스터 socket LB의 영향을 받지 않는 외부 client를 사용합니다. 실제 값으로 `http://ENTRY_NODE_IP:NODEPORT/`를 요청합니다. Pod→ClusterIP curl로 외부 DSR·Maglev 동작을 증명하지 못합니다. HTTP 성공만 보지 말고 요청·응답 경로와 backend·연결 상태를 검증합니다.

## 마스커레이딩

Pod egress masquerading은 설정된 외부 경로에서 필요한 경우 source 주소를 변환합니다. 암호화·방화벽이 아니며 Service DNAT·DSR과 구분합니다.

다음 조각은 **실제로 해당 Pod source·반환 경로를 지원하는 네트워크에서만** 예시 목적지 `10.0.0.0/8`을 source masquerading에서 제외합니다.

**`masquerade-values.yaml`**

```yaml
bpf:
  masquerade: true
enableIPv4Masquerade: true
enableIPv6Masquerade: false
ipv4NativeRoutingCIDR: 10.0.0.0/8
```


`ipv4NativeRoutingCIDR`은 라우팅 가능하다고 가정한 범위와 masquerade 제외를 지정합니다. Route를 설치하거나 전체 datapath를 native 모드로 바꾸지 않습니다. 반환 경로 없이 넓게 제외하면 연결이 깨질 수 있습니다.

- 이 릴리스의 BPF masquerading은 BPF NodePort에 의존하고 프로그램이 붙은 장치에서만 적용됩니다. 실제 장치를 확인하고 필요하면 문서화된 `devices` 설정을 사용합니다.
- Iptables 구현에는 `egressMasqueradeInterfaces` 동작이 있습니다. 이를 예전 일반 `masquerade-interfaces`·`masquerade-all` 예제와 함께 모든 BPF 경로의 공통 제어로 생각하지 않습니다.
- IPv6 BPF masquerading은 beta입니다. 어느 구현도 Cilium 플랫폼·커널 조건을 없애지 않으며 둘 다 결국 커널에서 처리됩니다.
- 노드 주소 예외, ip-masq-agent 제외와 후단 cloud/NAT gateway가 관측 source에 영향을 줍니다. 통제된 관측 서버와 노드 상태·캡처를 함께 사용합니다. 임의 공용 사이트 접속 성공은 특정 NAT 구현의 증거가 아닙니다.

관련 에이전트에서 확인합니다.

```bash
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
export CILIUM_POD=cilium-REPLACE-WITH-AGENT-ON-TARGET-NODE
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf nat list
```

## Fragment 처리와 MTU

릴리스된 fragment tracker는 제한된 LRU map에 datagram 식별자와 L4 source·destination port를 저장합니다. L4 header가 없는 후속 fragment의 port 문맥을 복원할 수 있지만 **BPF payload 재조립 엔진**이나 fragment 공격 방지 보장이 아닙니다.

문서화된 기능은 해당 flag로 기본 활성화되는 IPv4·IPv6 tracking을 포함하며 beta로 표시됩니다. IPv4 flag `enable-ipv4-fragment-tracking`은 여전히 유효합니다. `bpf-fragments-map-max`는 추적 datagram map 용량이며 이전 `fragment-tracking-timeout`, `max-fragments-per-flow`는 릴리스 설정 계약이 아닙니다.

Chart의 추가 설정 map을 사용하는 명시적 예입니다.

**`fragment-values.yaml`**

```yaml
extraConfig:
  enable-ipv4-fragment-tracking: 'true'
  bpf-fragments-map-max: '8192'
```


8192는 용량 예시이며 flow별 fragment 수 한도가 아닙니다. 용량 진단에는 `cilium_ipv4_frag_datagrams` / `cilium_ipv6_frag_datagrams`와 pressure를 확인합니다. Pressure가 재조립 성공·공격 차단 카운터는 아닙니다.

올바른 packet 크기와 작동하는 PMTUD 경로를 우선합니다. PMTUD는 관련 오류 신호와 네트워크 동작에 의존하며 어디서나 자동 최적 크기를 보장하지 않습니다. Cilium `MTU`는 **기반 네트워크 override**입니다. [네트워킹 가이드](03-networking.md)처럼 일반 VXLAN 오버헤드는 IPv4 underlay 50바이트, IPv6 70바이트이며 1500 경로의 기반 값을 무조건 1450으로 설정하면 두 번 뺄 수 있습니다.

## 관측과 문제 해결

올바른 노드, 실제 Envoy 배포 방식, 의도한 정책, 실현 endpoint 상태와 새 트래픽을 확인합니다. Agent 로컬 작업에는 `cilium-dbg`, cluster 작업에는 독립 CLI를 사용합니다. 제거된 `policy trace`나 강제 endpoint 재생성부터 시작하지 않습니다.

활성 Hubble Relay의 port-forward를 별도 터미널에서 유지하고 관련 플로우를 관찰합니다.

```bash
cilium hubble port-forward
```

```bash
hubble observe --namespace cilium-l2l7-demo --protocol http --last 20
hubble observe --namespace cilium-l2l7-demo --verdict DROPPED --last 20
```

HTTP 정책 거부는 패킷 DROPPED 대신 HTTP 403일 수 있습니다. Timeout은 readiness, DNS, routing, TLS, 관측 문제일 수도 있으므로 모든 오류를 정책 성공으로 해석하지 말고 계층별 근거를 대조합니다.

## 검증 한계와 참고 자료

릴리스 소스·schema와 제한된 로컬 fixture로 확인한 예제이며 운영 검증 플랫폼·실제 클러스터 벤치마크가 아닙니다. 이미지 실행, webhook 연결, mTLS 트래픽, DSR 반환, NAT·fragment 동작은 준비한 환경에서 검증해야 합니다. 이번 실행의 label을 가진 애플리케이션 리소스만 정리하고 실습 종료 목적으로 클러스터 CNI를 제거하지 않습니다.

- [Cilium kube-proxy replacement/DSR/Maglev](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/kubernetes/kubeproxy-free.rst), [masquerading](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/masquerading.rst), [fragment handling](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/fragmentation.rst), [fragment map implementation](https://github.com/cilium/cilium/blob/v1.20.1/pkg/maps/fragmap/fragmap.go)
- [L2 Announcements](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/l2-announcements.rst), [multicast](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/multicast.rst), [HTTP rule translator](https://github.com/cilium/cilium/blob/v1.20.1/pkg/envoy/policy/envoy_l7_rules_translator.go), [Envoy chart defaults](https://github.com/cilium/cilium/blob/v1.20.1/install/kubernetes/cilium/templates/_helpers.tpl)
- [Cilium/Istio integration](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/istio.rst), [Istio CNI/init-container modes](https://istio.io/latest/docs/setup/additional-setup/cni/), [webhook requirements](https://istio.io/latest/docs/ops/configuration/mesh/webhook/), [Istio 1.31 schemas](https://github.com/istio/istio/blob/1.31.0/manifests/charts/base/files/crd-all.gen.yaml)
- [Kubernetes Service proxy modes/affinity](https://kubernetes.io/docs/reference/networking/virtual-ips/), [Cilium 1.20.1 values](https://github.com/cilium/cilium/blob/v1.20.1/install/kubernetes/cilium/values.yaml)


[메인 페이지로 돌아가기](README.md)

## 퀴즈

[L2–L7·로드 밸런싱 문제 확인](../../quizzes/networking/cilium/05-l2-l7-networking-quiz.md).
