# Service Mesh 솔루션 비교

> **마지막 검토**: 2026년 9월 11일
> **API/artifact 검증**: Istio 1.31.0; Linkerd edge-26.9.1; Kong Mesh/Kuma 2.14.4; Consul/chart 2.0.4

버전은 예제 검증에 사용한 출처를 식별하며 **공통 Kubernetes 호환성 표**나 운영 배포 검증을 뜻하지 않습니다. 원래 Istio 1.24/Linkerd 2.15/Kong Mesh 2.8/Consul 1.19 성능 수치는 아래에 과거 미검증 자료로 구분해 보존합니다.

## 목차

1. [아키텍처](#아키텍처)
2. [성능 근거](#성능-근거)
3. [트래픽 관리](#트래픽-관리)
4. [보안](#보안)
5. [관측성](#관측성)
6. [멀티 클러스터](#멀티-클러스터)
7. [설치와 운영](#설치와-운영)
8. [비용과 라이선스](#비용과-라이선스)
9. [선택과 검증](#선택과-검증)

## 아키텍처

Service mesh는 통신 기능 일부를 infrastructure component로 옮깁니다. 앱 코드에 투명하게 트래픽을 가로챌 수 있지만 protocol, traffic ownership, workload identity와 policy는 구성해야 합니다. 분산 추적에는 context 전파/instrumentation도 필요합니다. Mesh가 임의의 앱 retry를 안전하게 만들지는 않습니다.

![Control plane이 서비스 사이의 proxy를 구성하는 개념적인 sidecar 구조입니다. 필요한 정책과 telemetry 설정은 본문에서 설명합니다.](../../../.gitbook/assets/ko-service-mesh-istio-comparison-01-service-mesh-comparison-0.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-comparison-01-service-mesh-comparison-0.html)

설정된 sidecar 배포의 개념도입니다. 모든 기능이 기본 활성화되거나 ambient/Cilium도 같은 Pod별 토폴로지를 사용한다는 뜻은 아닙니다.

### Istio

![Istiod가 설정을 읽어 Envoy sidecar에 xDS 설정을 제공하고 등록된 workload 사이의 트래픽을 처리하는 구조입니다.](../../../.gitbook/assets/ko-service-mesh-istio-comparison-01-service-mesh-comparison-2.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-comparison-01-service-mesh-comparison-2.html)

Istiod는 과거 Pilot, Citadel, Galley에 연결되던 설정/discovery·identity 기능을 통합합니다. 현재 세 deployment가 별도로 더 필요하다는 뜻은 아닙니다. Sidecar data plane은 Envoy를 사용하고 ambient는 L4용 노드별 ztunnel과 지원되는 L7 처리용 Envoy waypoint를 사용합니다. Ingress/egress gateway는 명시적으로 선택한 경계 경로를 구현합니다.

Kubernetes와 문서화된 VM 통합을 지원하며 network/trust 전제조건이 있습니다. Ambient 핵심 기능의 GA가 sidecar와의 전체 기능 동등성을 뜻하지 않습니다. Waypoint 정책 연결, EnvoyFilter 지원과 multicluster 성숙도가 다릅니다. Resource·복잡도를 추정하기 전에 모드와 필요한 API 동작을 선택하세요.

### Linkerd

![Destination, Identity, Proxy Injector가 Rust linkerd2-proxy sidecar에 discovery, workload certificate와 injection을 제공하는 구조입니다.](../../../.gitbook/assets/ko-service-mesh-istio-comparison-01-service-mesh-comparison-3.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-comparison-01-service-mesh-comparison-3.html)

Linkerd는 전용 Rust proxy와 Kubernetes resource, annotation, CRD를 사용합니다. 현재 Gateway API request routing, timeout/retry, per-route authorization과 local rate limiting을 제공합니다. Annotation만 사용하거나 “기본 기능만 있는 mesh”라는 설명은 부정확합니다.

Non-Kubernetes mesh expansion은 ExternalWorkload, 외부 머신의 proxy, 호환 SPIFFE/SPIRE identity, DNS·network 접근을 사용하도록 문서화되어 있습니다. “VM 미지원”이 아니며 외부 IP를 등록하기만 하면 proxy가 설치·인증되는 것도 아닙니다.

### Kong Mesh와 Kuma

![Kong Mesh control plane이 Kubernetes·VM의 Envoy data-plane proxy를 구성합니다. Multi-zone 모델에는 global control plane을 사용합니다.](../../../.gitbook/assets/ko-service-mesh-istio-comparison-01-service-mesh-comparison-4.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-comparison-01-service-mesh-comparison-4.html)

Kong Mesh는 Kuma를 기반으로 합니다. Kubernetes mode는 Kubernetes resource/storage를, Universal mode는 VM/bare-metal 환경과 설정된 database를 사용합니다. 자체 운영 또는 관리형 global control plane을 선택할 수 있으며 edition 기능·지원 조건은 upstream Kuma와 구분해야 합니다.

Multi-zone에서는 global·zone control plane이 KDS로 resource를 교환하고 각 zone이 local proxy에 xDS를 제공합니다. Cross-zone data traffic은 목적지 zone ingress와, 구성한 경우 출발지 zone egress를 거칩니다. Global control plane이 Prometheus/tracing metric을 자동 집계하는 backend는 아닙니다.

서비스 discovery 자체가 local 80%/remote 20% 분할을 정하지 않습니다. Legacy endpoint weighting과 현재 MeshLoadBalancingStrategy locality 설정은 기본 동작이 다릅니다. 그림의 weight를 내장 동작으로 해석하지 말고 선택한 policy, eligible endpoint와 cross-zone/failover 설정을 확인하세요.

목적에 맞게 MeshHTTPRoute, MeshTrafficPermission, MeshRetry, MeshTimeout, MeshMetric, MeshTrace, MeshAccessLog 같은 현재 policy를 사용합니다. TrafficRoute와 TrafficPermission은 legacy/deprecated interface이며 검증한 release에서 반드시 제거된 API라는 뜻은 아닙니다. 의존 policy를 함께 migration하고 구 TrafficPermission과 MeshTrafficPermission은 혼합하지 마세요. Policy type만으로 “global” 또는 “zone-only” ownership/전파가 결정되지 않습니다.

Global control plane 장애에서는 기존 data traffic이 동작해도 policy와 remote-service 변경 전파가 멈출 수 있습니다. Zone control plane 장애는 새 proxy, 설정 갱신과 certificate refresh를 막을 수 있습니다. 보관된 설정이 무기한 가용성을 보장하지 않습니다. 실제 실패 조건에서 등록, 갱신, drain과 만료를 검증하세요.

### Consul Service Mesh

Consul은 discovery, configuration과 identity 기능 및 Envoy 지원을 제공합니다. 현재 Kubernetes 통합은 일반적으로 consul-dataplane이 sidecar를 관리하므로 과거 client-agent-per-node 그림이 유일하거나 기본인 Kubernetes 구조는 아닙니다.

공식 proxy 개요에는 개발/시험용 built-in L4 proxy도 설명되어 있으며 운영 사용을 권장하지 않습니다. 이를 Envoy의 운영 L7 기능과 동등하게 표현하거나 release 근거 없이 제거되었다고 쓰면 안 됩니다. Consul은 Kubernetes 외에 VM과 다른 runtime 통합도 문서화합니다.

### 함께 평가할 Cilium

Cilium은 eBPF network datapath와 Envoy 같은 L7 proxy를 조합합니다. L7 전체가 proxy 없이 동작하는 networking은 아닙니다. Cilium 1.20.1 out-of-band mutual authentication은 Beta이며 out-of-band handshake를 사용합니다. WireGuard/IPsec 암호화는 별도 요구사항입니다. 실제 기능과 Cluster Mesh 제약은 [Cilium mesh 가이드](../../cilium-service-mesh/README.md)를 참고하세요.

Cilium 1.20.1에는 `encryption.type: ztunnel`로 선택하는 별도의 [ztunnel 투명 암호화 베타](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ztunnel.rst)도 있습니다. Namespace 등록으로 TCP 워크로드 mTLS를 제공하며 양쪽 엔드포인트가 모두 등록되어야 합니다. ClusterMesh와 hostNetwork Pod는 지원하지 않고, 릴리스 문서는 이 경로에서 HBONE 포트 15008을 대상으로 하는 경우 외에는 일반 L4 정책이 동작하지 않는다고 명시합니다. 별도의 CA·bootstrap 요건을 가진 배포 선택지입니다.

## 성능 근거

### 원래 수치: 과거 미검증 자료

기존 문서는 **노드 3개, EKS 1.28, m5.xlarge, 서비스 100개, 1,000 RPS** 시험과 Istio 1.24, Linkerd 2.15, Kong Mesh 2.8, Consul 1.19를 명시했습니다. 하지만 raw sample, 재현 가능한 harness, 정확한 patch/proxy version이나 원본 benchmark가 없습니다. 현재 제품 순위를 뒷받침하지 못하는 수치입니다.

| 원래 항목 | p50 | p95 | p99 | CPU 주장 | 메모리 주장 |
|---|---:|---:|---:|---:|---:|
| Baseline |0.1 ms|0.2 ms|0.3 ms|—|—|
| Linkerd |+0.5 ms|+0.8 ms|+1.2 ms|+3–8%|+20–50 MB|
| Istio |+1.0 ms|+2.5 ms|+3.5 ms|+5–15%|+50–150 MB|
| Kong Mesh |+0.8 ms|+2.0 ms|+3.0 ms|+5–12%|+40–120 MB|
| Consul |+1.0 ms|+2.5 ms|+3.5 ms|+6–14%|+50–140 MB|

기존 control-plane 추정값은 Istio 0.5–1 CPU/1–2 GB, Linkerd 0.1–0.3 CPU/200–500 MB, Kong 0.2–0.5 CPU/500 MB–1 GB, Consul 0.5–1 CPU/1–2 GB였습니다. Proxy CPU 추정값도 Linkerd 20–100m에서 Istio/Consul 100–500m까지였습니다. 기본값·실측·용량 권장값이 아닌 미검증 입력입니다. Linkerd의 서로 다른 component 개수를 한 component의 replica 수와 비교해서도 안 됩니다.

제거한 처리량 그림은 근거 없이 baseline 대비 Linkerd 95–98%, Kong 90–95%, Istio/Consul 85–92%라고 주장했습니다. “Linkerd가 가장 빠르다”거나 고정 resource 비율·최소 fleet 크기를 정하는 근거가 될 수 없습니다.

### 재현 가능한 비교

실제 product/proxy/Kubernetes 버전, hardware와 전체 설정을 결과에 붙입니다. Protocol/payload/concurrency, TLS/authentication, policy, telemetry와 resource limit을 맞추세요. Baseline·mesh의 절대 latency 분포, 정한 error/SLO 한도에서의 throughput, component별 CPU/메모리와 반복 시험 변동성을 기록합니다.

Rollout, drain, connection reuse, telemetry 누락과 control-plane 장애를 포함해 동등한 HA·실패 동작을 비교합니다. 원시 오류와 retry 후 client-visible 결과를 분리해 측정하세요. 실험을 다시 실행하고 보존하지 않은 채 과거 version label만 새 버전으로 바꾸면 안 됩니다.

## 트래픽 관리

| 기능 | 구체적으로 비교할 항목 |
|---|---|
| Weight/header routing | Istio VirtualService, Linkerd HTTPRoute, Kong MeshHTTPRoute, Consul router/splitter/resolver 동작 |
| Blue/Green·canary | Route는 일부일 뿐이며 rollout controller/배포 절차가 revision, 분석과 복구를 관리해야 함 |
| Retry/timeout | 지원 request/protocol 범위, default policy, budget과 앱 멱등성 |
| Rate limiting | Local/shared counter, identity, 실패 정책과 실제 replica 범위 |
| Fault·mirroring | 지원 API/filter와 생성된 설정; write mirroring은 부작용 가능 |

Linkerd는 HTTPLocalRateLimitPolicy의 identity별 제한 등을 포함한 local rate limiting과 요청 속성 기반 dynamic routing을 지원합니다. Proxy별 local limit은 global service quota가 아닙니다. Consul·Kong 기능도 edition/API에 따라 다를 수 있어 단순 “기본/enterprise/없음” 표로 판단할 수 없습니다.

### 독립적인 Read-only Routing 예제

적절한 mesh에서 **대안으로** 사용하는 예제이며 동일 workload를 controller 여러 개가 겹쳐 관리하지 않습니다. `mesh-demo`에 기존 reviews Pod, 실제 version label, HTTP 9080 listener와 mesh 등록이 있다고 가정합니다. 다음 Service는 port를 명시하지만 앱을 생성하지 않습니다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: reviews
  namespace: mesh-demo
spec:
  selector:
    app: reviews
  ports:
  - name: http
    port: 9080
    targetPort: 9080
    appProtocol: http
---
apiVersion: v1
kind: Service
metadata:
  name: reviews-v1
  namespace: mesh-demo
spec:
  selector:
    app: reviews
    version: v1
  ports:
  - name: http
    port: 9080
    targetPort: 9080
    appProtocol: http
---
apiVersion: v1
kind: Service
metadata:
  name: reviews-v2
  namespace: mesh-demo
spec:
  selector:
    app: reviews
    version: v2
  ports:
  - name: http
    port: 9080
    targetPort: 9080
    appProtocol: http
```

Read-only review 요청을 비교합니다. Write를 routing하기 전에 상속한 mesh/client retry와 멱등성을 별도로 감사해야 합니다. Routing header는 client가 제어하는 입력이며 인증이 아닙니다.

#### Istio

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
  namespace: mesh-demo
spec:
  hosts:
  - reviews
  http:
  - name: canary-header
    match:
    - headers:
        x-release:
          exact: canary
    route:
    - destination:
        host: reviews
        subset: v2
        port:
          number: 9080
      weight: 100
    retries:
      attempts: 0
  - name: weighted
    route:
    - destination:
        host: reviews
        subset: v1
        port:
          number: 9080
      weight: 90
    - destination:
        host: reviews
        subset: v2
        port:
          number: 9080
      weight: 10
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
  namespace: mesh-demo
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

두 route 모두 mesh retry를 명시적으로 비활성화합니다. Subset label이 실제 endpoint와 일치해야 하며 weight는 version 생성·확장을 수행하지 않습니다. Gateway 노출에는 별도 host/TLS binding이 필요합니다.

#### Linkerd

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: reviews-outbound
  namespace: mesh-demo
spec:
  parentRefs:
  - group: ''
    kind: Service
    name: reviews
    port: 9080
  rules:
  - matches:
    - headers:
      - name: x-release
        type: Exact
        value: canary
    backendRefs:
    - group: ''
      kind: Service
      name: reviews-v2
      port: 9080
      weight: 100
  - backendRefs:
    - group: ''
      kind: Service
      name: reviews-v1
      port: 9080
      weight: 90
    - group: ''
      kind: Service
      name: reviews-v2
      port: 9080
      weight: 10
```

Gateway API producer route가 Service에 연결되어 meshed **client**를 구성합니다. Core Service의 group은 빈 문자열입니다. Deprecated SMI TrafficSplit extension을 필요로 하지 않습니다. 같은 Service에 ServiceProfile이 있으면 outbound HTTPRoute보다 우선하므로 ownership을 조율해야 합니다. Accepted/ResolvedRefs와 실제 routing을 확인하세요.

#### Kong Mesh

```yaml
apiVersion: kuma.io/v1alpha1
kind: MeshHTTPRoute
metadata:
  name: reviews-weighted
  namespace: mesh-demo
  labels:
    kuma.io/mesh: default
spec:
  targetRef:
    kind: Dataplane
    labels:
      app: productpage
  to:
  - targetRef:
      kind: MeshService
      name: reviews
      sectionName: http
    rules:
    - matches:
      - path:
          type: PathPrefix
          value: /
      default:
        backendRefs:
        - kind: MeshService
          name: reviews-v1
          port: 9080
          weight: 90
        - kind: MeshService
          name: reviews-v2
          port: 9080
          weight: 10
```

여기서 reviews, reviews-v1, reviews-v2는 **실제 MeshService resource 이름**입니다. 생성된 이름이 항상 Kubernetes Service 이름과 같다고 가정하면 안 됩니다. 설치 환경의 이름, namespace/port section과 backend readiness를 확인하세요. Caller Dataplane에 app label이 있어야 하며 HTTP Service port에는 지원 protocol을 선언해야 합니다. 이 예제는 weight를 바꾸며 locality priority나 용량을 바꾸지 않습니다.

#### Consul

```yaml
apiVersion: consul.hashicorp.com/v1alpha1
kind: ServiceDefaults
metadata:
  name: reviews
  namespace: mesh-demo
spec:
  protocol: http
---
apiVersion: consul.hashicorp.com/v1alpha1
kind: ServiceResolver
metadata:
  name: reviews
  namespace: mesh-demo
spec:
  subsets:
    v1:
      filter: Service.Meta.version == v1
      onlyPassing: true
    v2:
      filter: Service.Meta.version == v2
      onlyPassing: true
---
apiVersion: consul.hashicorp.com/v1alpha1
kind: ServiceSplitter
metadata:
  name: reviews
  namespace: mesh-demo
spec:
  splits:
  - weight: 90
    service: reviews
    serviceSubset: v1
  - weight: 10
    service: reviews
    serviceSubset: v2
```

Consul config entry의 Kubernetes CRD 형식이며 controller/RBAC 설정이 필요합니다. Consul catalog의 Service metadata에 실제로 version=v1/v2가 있어야 합니다. Kubernetes Pod label만으로 catalog metadata가 증명되지는 않습니다. HTTP protocol과 resolver subset이 split 정의를 완성합니다. 같은 config entry에 여러 owner를 적용하지 말고 Kubernetes↔Consul namespace/service mapping과 정상 endpoint를 확인하세요.


## 보안

암호화, peer identity, caller 인가와 앱 인증은 별도 제어입니다. 등록된 proxy 사이의 자동 mTLS가 모든 unmeshed traffic 거부나 모든 caller 인가를 뜻하지 않습니다.

### Istio: Inbound mTLS와 요청 인가

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: reviews-strict
  namespace: mesh-demo
spec:
  selector:
    matchLabels:
      app: reviews
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: reviews-read
  namespace: mesh-demo
spec:
  selector:
    matchLabels:
      app: reviews
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/mesh-demo/sa/productpage
    to:
    - operation:
        methods:
        - GET
        paths:
        - /reviews/*
```

Sidecar 예제로 실제 productpage ServiceAccount identity와 reviews workload가 필요합니다. Auto mTLS가 적절한 outbound transport를 선택할 수 있으므로 광범위한 `*.local` ISTIO_MUTUAL DestinationRule은 필요하지 않으며 무관한 plaintext destination을 깨뜨릴 수 있습니다. STRICT는 inbound 강제이고 ALLOW는 표시한 identity/method/path를 제어합니다.

AuthorizationPolicy의 문자열은 exact, prefix, suffix, presence matching입니다. `*Mobile*`는 일반 substring regex가 아니며 User-Agent도 workload identity가 아닙니다. Ambient L7에서는 sidecar selector를 그대로 복사하지 말고 지원되는 waypoint 정책 연결 방식을 사용해야 합니다.

### Linkerd: 명시적 Inbound 정책

```yaml
apiVersion: policy.linkerd.io/v1beta3
kind: Server
metadata:
  name: reviews-http
  namespace: mesh-demo
spec:
  podSelector:
    matchLabels:
      app: reviews
  port: 9080
  proxyProtocol: HTTP/1
  accessPolicy: deny
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: reviews-read
  namespace: mesh-demo
spec:
  parentRefs:
  - group: policy.linkerd.io
    kind: Server
    name: reviews-http
  rules:
  - matches:
    - method: GET
      path:
        type: PathPrefix
        value: /reviews/
---
apiVersion: policy.linkerd.io/v1alpha1
kind: AuthorizationPolicy
metadata:
  name: reviews-read
  namespace: mesh-demo
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: reviews-read
  requiredAuthenticationRefs:
  - kind: ServiceAccount
    name: productpage
```

Server는 실제 선언된 Pod port를 선택하고 여기서는 기본 deny를 사용합니다. Inbound HTTPRoute는 `/reviews/` 아래 GET을 선택하며 AuthorizationPolicy는 productpage ServiceAccount를 요구합니다. Target API group을 명시합니다. Group 생략은 core group이며 Linkerd Server를 자동 추론하지 않습니다. 누락되거나 잘못된 참조는 인가를 만들지 않습니다.

검증한 edge CRD는 Server v1beta3와 v1beta1 등 구버전을 serve합니다. 구 API가 제거되었다는 뜻은 아닙니다. 선택한 artifact가 지원하는 API를 사용하세요. Namespace/Pod의 기본 all-unauthenticated 정책은 meshed peer 사이의 자동 암호화나 이 명시적 Server 정책과 별개입니다.

### Kong Mesh: 권한과 함께 mTLS 구성

기본 설치만으로 모든 service traffic이 암호화되지는 않습니다. 기존 workload에 mTLS를 켜기 전에 권한을 계획해야 하며 일치하는 권한이 없으면 통신이 차단될 수 있습니다. 최소 Mesh 설정은 다음과 같습니다.

```yaml
apiVersion: kuma.io/v1alpha1
kind: Mesh
metadata:
  name: default
spec:
  mtls:
    enabledBackend: ca-1
    backends:
    - name: ca-1
      type: builtin
```

제한된 service-level 권한 예제입니다.

```yaml
apiVersion: kuma.io/v1alpha1
kind: MeshTrafficPermission
metadata:
  name: productpage-to-reviews
  namespace: mesh-demo
  labels:
    kuma.io/mesh: default
spec:
  targetRef:
    kind: Dataplane
    labels:
      app: reviews
  from:
  - targetRef:
      kind: MeshSubset
      tags:
        kuma.io/service: productpage
    default:
      action: Allow
```

productpage를 실제 출발지 `kuma.io/service` identity tag로 바꾸고 target Dataplane label/namespace를 확인하세요. 이 tag가 단순 Kubernetes Service 이름과 같다는 보장은 없습니다. Service-level 인가이며 위 Istio/Linkerd의 GET/path 규칙과 동등하지 않습니다. 구 TrafficPermission과 혼합하지 마세요. 운영 강제를 바꾸기 전에 필요한 transport, identity와 policy resource를 준비해야 합니다.

### Consul: L7 Intentions

```yaml
apiVersion: consul.hashicorp.com/v1alpha1
kind: ServiceIntentions
metadata:
  name: reviews
  namespace: mesh-demo
spec:
  destination:
    name: reviews
  sources:
  - name: productpage
    permissions:
    - action: allow
      http:
        methods:
        - GET
        pathPrefix: /reviews/
```

Consul service identity와 HTTP protocol 설정이 catalog·실제 proxy와 일치해야 합니다. L7 permission이 있으므로 Consul은 기본 service-level 인가만 한다는 설명은 부정확합니다. 한 source의 L4 action과 L7 permissions를 독립적으로 함께 적용하는 것처럼 혼합하면 안 됩니다. 다른 intentions/default policy, namespace/partition과 controller mapping도 확인하세요.

Mesh config entry의 TLS minimum은 TLS 설정을 바꿀 뿐 앱 등록, proxy 설치나 전체 CA/ACL 구성을 수행하지 않습니다. Envoy extension과 escape-hatch API에도 해당 Consul release의 권한이 필요하며 2.0.4는 코드 실행 extension에 대한 mesh:write 요구를 강화했습니다.

## 관측성

Metric 개수는 고정 순위를 정할 근거가 아닙니다. 활성화한 stat, dimension, policy, scraping과 앱 instrumentation이 신호·overhead를 바꿉니다. EnvoyFilter는 무제한 telemetry 확장 API가 아니며 protocol/exporter 호환성 없이 모든 tracing backend를 서로 바꿀 수는 없습니다.

| Mesh | 구성·확인할 항목 |
|---|---|
| Istio | Telemetry API, 실제 proxy/control-plane metric, access log 형식, tracing provider/backend, 선택적 Kiali/Grafana |
| Linkerd | Proxy golden/per-route metric, 선택한 viz/외부 monitoring, 설정된 proxy·앱 tracing |
| Kong Mesh | MeshMetric, MeshTrace, MeshAccessLog와 지원 backend; GUI/control-plane 접근 별도 구성 |
| Consul | Proxy/agent metric, tracing과 실제 endpoint/authentication을 사용하는 UI metrics provider |

End-to-end trace에는 앱 호출 간 context 전파, 필요한 trace 시작·sampling, collector/backend 전달이 필요합니다. Linkerd도 이를 명시하며 proxy span 하나가 전체 앱 trace는 아닙니다. OpenTelemetry collector가 지원 protocol을 연결할 수는 있지만 모든 product/backend 조합이 검증되는 것은 아닙니다.

관련 component가 설치되고 접근 권한이 있다면 다음을 확인할 수 있습니다.

```bash
istioctl dashboard kiali -n istio-system
linkerd viz check
linkerd viz stat deploy -n mesh-demo
linkerd viz dashboard
```

Dashboard나 backend를 설치하는 명령은 아닙니다. Kiali 현재 설정·호환성도 별도 확인해야 하며 구 accessible_namespaces와 legacy Istio bundled-addon 값은 현재 설치법이 아닙니다. 유지보수되는 설정과 검증 한계는 [관측성 가이드](../observability/README.md)를 참고하세요. 빈 Mesh metrics backend만으로 Kong GUI가 활성화되지 않으며 Consul UI metric URL은 실제 server 환경에서 해석되어야 합니다.

## 멀티 클러스터

| 시스템 | Discovery/data 경로 | 주요 경계 |
|---|---|---|
| Istio | 각 primary가 허용된 Kubernetes API를 조회; 다른 network에는 구성된 east-west gateway 사용 | Remote secret은 CRD 복사나 network/trust 구성이 아님. Sidecar·ambient 지원 토폴로지 구분 |
| Linkerd | Local mirror Service가 remote를 표현; hierarchical은 **목적지** gateway, flat은 직접 Pod 경로 | Mirror는 출발지 cluster에 있음. Source gateway가 필수는 아님. Federated Service는 flat이며 headless member 미지원 |
| Kong Mesh | KDS로 zone/service 교환; 목적지 zone ingress와 선택적 출발지 zone egress 사용 | 적용 policy·eligible endpoint가 locality/failover 결정; 내장 80/20이나 무조건적 failover가 아님 |
| Consul | 선택한 cluster peering 또는 WAN federation의 discovery·mesh-gateway 경로 | 실제 토폴로지에 맞는 trust, export service, authorization/routing 필요; 이름만으로 연결되지 않음 |

![Consul server와 mesh gateway를 사용하는 WAN federation datacenter 개념도입니다. Cluster peering은 별도 구성 모델입니다.](../../../.gitbook/assets/ko-service-mesh-istio-comparison-01-service-mesh-comparison-16.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-comparison-01-service-mesh-comparison-16.html)

기존 “Linkerd 최대 약 10개 cluster”나 일반적인 “수십 개” 제한에는 quota/부하 시험 근거가 없습니다. 용량은 control/data-plane 토폴로지, service/endpoint 수, update 빈도와 resource에 따릅니다. 자동 discovery가 정책 복제나 앱/데이터 재해 복구를 자동으로 수행하지는 않습니다.

Remote API/gateway 접근, certificate trust, DNS, namespace/service identity, exported service와 양방향 실패 동작을 확인합니다. 기존 meshID label 설치 명령 두 개와 secret 하나는 전체 mesh 구성이 아니므로 [유지보수되는 Istio multicluster 가이드](../advanced/02-multi-cluster.md)를 따르세요.

## 설치와 운영

### 버전은 각각 검증해야 합니다

| 검증한 출처/artifact | 호환성 근거와 한계 |
|---|---|
| Istio 1.31.0 | Kubernetes 1.32–1.36 지원; 실제 upgrade/skew 규칙과 platform 요구사항 준수 |
| Linkerd edge-26.9.1 CLI/CRD | 해당 edge의 권고 확인. 별도 **2.20** 표는 Kubernetes 1.31–1.35, Gateway API 1.2.1–1.5.1이며 모든 후속 edge/vendor build의 범위로 자동 대입하지 않음 |
| Kong Mesh/chart 2.14.4 | 9월 3일 Kuma 2.14.4와 공개됨. 공개 Kubernetes 검증 표는 현재 2.13까지만 있어 render로 2.14 호환성을 인증하지 않음. Support 표는 별도로 2.13 LTS를 명시 |
| Consul/chart 2.0.4 | 앱과 Helm artifact 별도 확인. Chart 최소 Kubernetes metadata가 전체 지원 표나 upgrade 검토를 대체하지 않음 |

Gateway API CRD는 여러 controller가 공유하는 cluster 전체 의존성입니다. 모든 consumer를 확인하지 않고 catalog 최신값을 설치하거나 기존 bundle을 downgrade하면 안 됩니다.

### Istio Revision 전환

같은 버전 CLI와 설치된 버전에서 지원되는 upgrade 경로를 사용합니다. 이 문서의 과거 1.24 label은 1.31로 직접 건너뛰라는 뜻이 아닙니다. 검토된 설치값, gateway/CNI와 revision ownership을 보존하세요.

Default profile에서 control-plane resource/HPA를 조정하는 입력 예제입니다.

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  profile: default
  components:
    pilot:
      k8s:
        hpaSpec:
          minReplicas: 3
          maxReplicas: 10
        resources:
          requests:
            cpu: 2000m
            memory: 4Gi
```

내장 production profile은 없습니다. CPU/메모리/replica는 sizing 입력값이며 운영 용량 보장이 아닙니다. 다른 revision을 설치하는 것만으로 기존 proxy가 갱신되지 않습니다.

```bash
istioctl install -f reviewed-istio.yaml --revision 1-31-0
kubectl label namespace mesh-demo istio-injection-
kubectl label namespace mesh-demo istio.io/rev=1-31-0 --overwrite
: "${DEPLOYMENT:?Set the actual staged Deployment name}"
kubectl rollout restart deployment/"$DEPLOYMENT" -n mesh-demo
kubectl rollout status deployment/"$DEPLOYMENT" -n mesh-demo
```

전환 전에 기존 namespace/Pod override를 검토합니다. Legacy injection label이 revision 선택보다 우선할 수 있습니다. 의도한 workload 집합만 restart하며 gateway·ambient component는 각각의 upgrade 절차를 따릅니다. Canary revision이 모든 앱 rollout의 오류 0을 보장하지 않습니다.

### Linkerd 설치·업그레이드

명시적인 edge/vendor artifact와 호환 Gateway API를 먼저 선택합니다. 현재 upstream CLI 절차는 다음과 같습니다.

```bash
linkerd check --pre
linkerd install --crds > linkerd-crds.yaml
kubectl apply -f linkerd-crds.yaml
linkerd install > linkerd-control-plane.yaml
kubectl apply -f linkerd-control-plane.yaml
linkerd check
```

Lab용 CLI 흐름이며 운영 설치 지침은 재현성과 검토된 identity 설정을 위한 Helm을 권장합니다. Namespace annotation은 새 Pod의 injection을 활성화하며 실행 중인 Pod에 즉시 proxy를 넣지 않습니다. 선택한 release 절차로 CRD/control plane을 갱신한 뒤 workload를 명시적으로 rollout해 data-plane proxy를 바꿉니다. 자동 workload rollout을 뜻하지 않습니다.

### Kong·Consul Chart 검토

검증한 정확한 chart를 받아 검토용으로 render하는 명령이며 운영 시스템을 배포하지 않습니다.

```bash
helm repo add kong-mesh https://kong.github.io/kong-mesh-charts
helm repo add hashicorp https://helm.releases.hashicorp.com
helm repo update kong-mesh hashicorp
helm show values kong-mesh/kong-mesh --version 2.14.4 > kong-values.reference.yaml
helm show values hashicorp/consul --version 2.0.4 > consul-values.reference.yaml
helm template kong-mesh kong-mesh/kong-mesh --version 2.14.4   --namespace kong-mesh-system --include-crds --values reviewed-kong-values.yaml
helm template consul hashicorp/consul --version 2.0.4   --namespace consul --include-crds --values reviewed-consul-values.yaml
```

Reviewed values 파일은 환경별 입력이며 이 비교 문서가 제공하는 파일이 아닙니다. Kubernetes 지원, edition/license, CA/ACL/bootstrap identity, storage, HA, injector/controller와 upgrade note를 확인한 뒤 제품별 설치 가이드를 따르세요. Render 성공은 runtime readiness나 안전한 in-place upgrade의 증명이 아닙니다.

### 트러블슈팅

```bash
istioctl proxy-status
istioctl analyze -n mesh-demo
istioctl proxy-config clusters "$POD" -n mesh-demo
linkerd check
linkerd viz stat deploy -n mesh-demo
kubectl get meshhttproutes,meshtrafficpermissions -n mesh-demo
kubectl get servicedefaults,serviceresolvers,servicesplitters -n mesh-demo
```

제품별 명령은 의도한 설치 환경에서만 사용합니다. 모든 Consul sidecar의 이름을 과거 container 이름으로 가정하지 말고 실제 component와 log를 확인하세요. Tap/debug log에는 요청 정보가 포함될 수 있으므로 범위를 정하고 일시적 진단 설정은 복구합니다. 모든 조직에 8시간 또는 5분 설치를 주장하지 말고 실제 절차에 드는 팀의 노력을 측정하세요.


## 비용과 라이선스

### 원래 비용 입력은 견적이 아닙니다

기존 100-Pod/m5.xlarge 표는 baseline $300에 다음 월 비용을 더했습니다.

| 원래 제품 입력 | Control-plane CPU/메모리 | Proxy 전체 CPU/메모리 | 과거 추가 월 비용 |
|---|---|---|---:|
| Linkerd |300m / 500 MB|2 vCPU / 5 GB|$50|
| Istio |1 vCPU / 2 GB|10 vCPU / 15 GB|$150|
| Kong Mesh |500m / 1 GB|8 vCPU / 12 GB|$120|
| Consul |1 vCPU / 2 GB|10 vCPU / 14 GB|$145|

Region, 노드 수, 운영 시간, 구매 방식, 할당 공식과 billing data가 제시되지 않은 가격입니다. Resource request가 자동으로 EC2 노드의 일부를 구매하는 것은 아니며 여유 용량이 생겨도 청구액은 줄지 않을 수 있습니다. 과거 가정 입력으로만 보존하며 가장 저렴한 제품을 선택하는 근거로 사용하지 않습니다.

기존 staffing 가정은 Istio/Linkerd/Kong/Consul 순서로 초기 설정 40/8/20/24시간, 월 운영 20/5/10/12시간, 월 troubleshooting 15/3/8/10시간, 분기 upgrade 8/2/4/5시간이었습니다. 팀 생산성 실측이 아니며 초기 설정은 매월 반복하는 비용도 아닙니다.

의미 있는 비용 모델에는 실제 유지할 용량, HA·autoscaling 제약, LB/전송, storage/telemetry, platform 비용, support subscription과 관측한 엔지니어링 노력을 사용합니다. 같은 workload·보안·가용성 요구를 비교하고 단위·가격·날짜를 명시하세요. 근거가 있는 차이와 migration 비용으로만 ROI를 계산합니다.

### Artifact와 제품 License

| Component | 구분할 내용 |
|---|---|
| Istio | Apache license의 upstream project; hosted/상용 배포는 별도 조건·비용 |
| Linkerd | Apache license의 upstream project; upstream edge와 vendor stable은 별도 release/support 선택 |
| Kuma / Kong Mesh | Upstream Kuma와 상용 Kong Mesh는 다른 제품이며 선택한 edition·지원 계약 확인 |
| Consul | 검증한 **Consul 2.0.4 앱**은 use grant와 이후 MPL 전환 조건이 있는 Business Source License 1.1이며 현재 MPL-2.0으로만 표시하면 안 됨 |

Consul Helm chart의 MPL 표시는 해당 artifact의 metadata이며 앱 binary license를 덮어쓰지 않습니다. 정확한 artifact/version 조건을 확인하세요. Linkerd HA control-plane 구성이 반드시 enterprise 전용인 것도 아닙니다. 유료 support/SLA·제품 기능과 upstream 기능을 구분하고 vendor 하나의 이름이나 달러 기호 등급으로 지원을 추론하지 마세요.

## 선택과 검증

| 상황 | 선택을 결정할 질문 |
|---|---|
| 대규모 배포 | 필요한 routing/security API, endpoint/update 규모와 HA 동작은 무엇인가? |
| 작은 팀·빠른 시작 | Identity와 upgrade를 포함해 운영 가능한 lifecycle/troubleshooting 절차는 무엇인가? |
| Resource 제약 | 동일 policy의 실제 workload가 proxy, waypoint, gateway, telemetry까지 포함해 얼마나 쓰는가? |
| VM·legacy workload | 문서화된 identity/network/runtime 통합이 맞는가? Istio와 Linkerd에도 VM 통합 경로가 있음 |
| Multicloud·multicluster | 필요한 trust, API, data plane, policy 배포와 재해 복구 경계는 무엇인가? |
| 상세 관측성 | 필요한 앱/proxy 신호, collector/exporter, retention과 접근 제어는 무엇인가? |

Service ExternalName 하나가 VM을 mesh에 등록하거나 proxy identity를 만들지는 않습니다. Data-plane binary에도 지원되는 등록 절차, credential, network redirection과 실제 control-plane 연결이 필요합니다. Istio 설치 두 개에 meshID/network 문자열을 지정하는 것도 완전한 multicluster 설계가 아닙니다.

실제 workload와 필요한 정책으로 bounded PoC를 수행하고 재현 가능한 측정값을 보관하며 실패·복구를 시험합니다. 관련 기준은 [비교 인덱스](README.md)와 [Istio vs VPC Lattice](02-istio-vs-lattice.md)를 참고하세요. Service 수, 일반적인 “가장 많은 기능” 또는 근거 없는 빠른 ROI 주장만으로 제품을 선택할 수 없습니다.


## 공식 근거

- [Istio architecture](https://istio.io/latest/docs/ops/deployment/architecture/) and [supported releases](https://istio.io/latest/docs/releases/supported-releases/)
- [Istio VM integration](https://istio.io/latest/docs/setup/install/virtual-machine/) and [multicluster](https://istio.io/latest/docs/setup/install/multicluster/)
- [Linkerd releases](https://linkerd.io/releases/), [Kubernetes compatibility](https://linkerd.io/docs/reference/k8s-versions/) and [Gateway API compatibility](https://linkerd.io/docs/features/gateway-api/)
- [Linkerd request routing](https://linkerd.io/docs/features/request-routing/), [HTTPRoute](https://linkerd.io/docs/reference/httproute/), [authorization](https://linkerd.io/docs/reference/authorization-policy/) and [rate limiting](https://linkerd.io/docs/features/rate-limiting/)
- [Linkerd multicluster](https://linkerd.io/docs/features/multicluster/), [VM expansion](https://linkerd.io/docs/tasks/adding-non-kubernetes-workloads/) and [tracing](https://linkerd.io/docs/features/distributed-tracing/)
- [Kong Mesh changelog](https://developer.konghq.com/mesh/changelog/), [support](https://developer.konghq.com/mesh/support-policy/) and [validated versions](https://developer.konghq.com/mesh/version-compatibility/)
- [Kong MeshHTTPRoute](https://developer.konghq.com/mesh/policies/meshhttproute/), [MeshTrafficPermission](https://developer.konghq.com/mesh/policies/meshtrafficpermission/) and [load-balancing policy](https://developer.konghq.com/mesh/policies/meshloadbalancingstrategy/)
- [Kong multi-zone deployment](https://developer.konghq.com/mesh/mesh-multizone-service-deployment/) and [installation](https://developer.konghq.com/mesh/deploy-mesh-self-managed/)
- [Consul proxies](https://developer.hashicorp.com/consul/docs/connect/proxy), [service defaults](https://developer.hashicorp.com/consul/docs/reference/config-entry/service-defaults), [resolver](https://developer.hashicorp.com/consul/docs/reference/config-entry/service-resolver), [splitter](https://developer.hashicorp.com/consul/docs/reference/config-entry/service-splitter) and [intentions](https://developer.hashicorp.com/consul/docs/reference/config-entry/service-intentions)
- [Consul 2.0.4 application license](https://raw.githubusercontent.com/hashicorp/consul/v2.0.4/LICENSE)
- [Istio architecture in this guide](../03-architecture.md)
