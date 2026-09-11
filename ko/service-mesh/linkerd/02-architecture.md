# Linkerd 아키텍처

> **검토일**: 2026년 9월 11일 · Linkerd edge-26.9.1 / proxy release/v2.368.0

현재 구성 요소의 역할, identity 계층, 트래픽 캡처와 주입 수명 주기를 설명합니다. 지원 release/cluster 조합과 고정 산출물은 [설치 가이드](01-installation.md)를 확인하세요. 예시는 설정 설명이며 이번 감사에서 실제 배포나 CA 회전을 수행하지 않았습니다.

## 전체 아키텍처

![핵심 Linkerd Deployment 3개와 mesh peer 2개의 단순화한 구조입니다. Policy controller는 Destination과 함께 실행되며 별도 표시되지 않았고 일부 연결만 그렸습니다.](../../.gitbook/assets/ko-service-mesh-linkerd-02-architecture-0.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-linkerd-02-architecture-0.html)

기본 control-plane namespace는 linkerd입니다. 고정한 chart에는 linkerd-destination, linkerd-identity, linkerd-proxy-injector의 핵심 Deployment 3개가 있습니다. Destination에는 policy와 ServiceProfile-validator container도 포함됩니다. 논리적 controller 역할과 별도 Deployment 수는 다릅니다. 선택적 Viz·multicluster는 자체 수명 주기를 가집니다.

Data plane은 등록한 앱 옆의 Rust proxy를 사용합니다. 이 릴리스는 native sidecar가 기본입니다. Identity Deployment는 시작 대기를 끈 일반 proxy를 의도적으로 사용하므로 containers와 initContainers를 모두 검사해야 합니다.

## 컨트롤 플레인

### Destination Controller

Destination은 discovery 상태를 감시하고 streaming API로 endpoint 주소, 예상 identity와 profile 정보를 제공합니다. 현재 기본값은 EndpointSlice입니다. ServiceProfile은 이전 설정 방식으로 계속 지원되며 Gateway API routing·인가에는 policy controller도 관여합니다. 현재 라우팅을 SMI TrafficSplit만으로 설명하거나 Destination이 그 옛 확장 리소스를 직접 감시한다고 가정하면 안 됩니다.

| 책임 | 의미 |
|---|---|
| Discovery | 요청한 Service endpoint의 추가·삭제와 metadata |
| 예상 identity | Outbound proxy가 선택한 peer를 인증할 때 사용하는 정보 |
| Profile | 지원되는 route/profile의 metric·retry·timeout 설정 |
| Load-balancing 입력 | Endpoint와 구성한 weight 정보. 실제 지연 관측과 요청·연결 선택은 proxy에서 수행 |

다음은 Go가 아닌 **Protocol Buffers service 발췌**입니다. Message 정의와 import는 고정된 proxy API 소스에 있습니다:

```protobuf
// Excerpt: message definitions/imports are in the linked API source.
service Destination {
  rpc Get(GetDestination) returns (stream Update) {}
  rpc GetProfile(GetDestination) returns (stream DestinationProfile) {}
}
```

Get은 destination update, GetProfile은 profile update를 streaming합니다. Stream이나 local cache가 설정을 즉시 전파하거나 사용 불가 endpoint 처리를 없애지는 않습니다.

### Identity Controller

기본 Kubernetes identity 흐름은 다음과 같습니다:

1. Proxy 시작 과정에서 로컬 개인 키·CSR 자료를 준비합니다.
2. Identity client가 CSR, 요청 identity와 ServiceAccount token을 제출합니다.
3. Identity는 Kubernetes TokenReview로 token을 검증하고 DNS 형식 identity를 만듭니다.
4. 구성한 **issuer 서명 credential**, 보통 중간 issuer가 workload 인증서를 서명합니다.
5. Client가 인증서·chain을 적재하고 만료 전에 갱신합니다.

Trust anchor는 chain 검증의 신뢰 기반입니다. Linkerd identity controller에는 그 root 개인 키가 필요하지 않으며 root가 모든 workload CSR의 온라인 서명자로 동작하지 않습니다.

다음은 설치 소유 도구를 위한 **Helm values 조각**입니다:

```yaml
identity:
  issuer:
    issuanceLifetime: 24h0m0s
    clockSkewAllowance: 20s
    scheme: linkerd.io/tls
```

기본 issuer scheme은 linkerd.io/tls입니다. kubernetes.io/tls 통합은 대응하는 외부 관리 Secret 형식을 사용합니다. Credential 소유와 key를 맞추지 않고 scheme만 바꾸거나, 부분 identity ConfigMap으로 linkerd-config의 전체 values를 덮어쓰지 마세요.

### Proxy Injector

![Linkerd CNI를 사용하지 않는 대상 Pod의 admission 개념 흐름입니다. API server가 injector mutation을 적용하며 native proxy 위치와 제외 조건은 본문에서 설명합니다.](../../.gitbook/assets/ko-service-mesh-linkerd-02-architecture-3.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-linkerd-02-architecture-3.html)

Injector는 mutating admission webhook입니다. API server가 응답의 mutation을 적용하며 그림은 개념 흐름이지 wire-format 예제가 아닙니다. 실제 webhook 선택, Pod override와 platform 대상 조건이 적용됩니다.

선택한 namespace 활성화:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
  annotations:
    linkerd.io/inject: enabled
```

Deployment override는 **Pod template**에 둡니다. 다음은 기존 workload 정의 안에 넣는 조각입니다:

```yaml
spec:
  template:
    metadata:
      annotations:
        linkerd.io/inject: enabled
        config.linkerd.io/proxy-cpu-request: 100m
        config.linkerd.io/proxy-memory-request: 64Mi
        config.linkerd.io/proxy-cpu-limit: '1'
        config.linkerd.io/proxy-memory-limit: 250Mi
        config.linkerd.io/proxy-log-level: warn,linkerd=info
```

enabled|disabled가 아니라 enabled 또는 disabled 중 하나의 실제 값을 사용하세요. Annotation 추가가 기존 Pod를 바꾸지는 않습니다. Webhook은 지정된 시스템 namespace를 제외하고, Pod override는 namespace의 활성화 요청을 비활성화할 수 있습니다.

| 주입·설정 항목 | 역할 |
|---|---|
| linkerd-init | Linkerd CNI를 사용하지 않을 때 Pod network 캡처 설정 |
| linkerd-proxy | 이 릴리스에서 보통 restartable init container인 data-plane proxy |
| Projected identity token·로컬 identity 저장 | Bootstrap과 workload 인증서 사용. Proxy 키를 공유 workload Secret으로 배포하지 않음 |
| 환경 변수·probe·resource | 주입 과정에서 생성하는 버전별 runtime 설정 |

### Policy Controller

Policy는 inbound 인가와 지원 outbound/request-routing 동작을 제어합니다. 예시는 app: web인 Pod의 선언된 http port를 선택하고 my-app의 meshed api-gateway ServiceAccount를 허용합니다:

```yaml
apiVersion: policy.linkerd.io/v1beta3
kind: Server
metadata:
  name: web-http
  namespace: my-app
spec:
  podSelector:
    matchLabels:
      app: web
  port: http
  proxyProtocol: HTTP/1
  accessPolicy: deny
---
apiVersion: policy.linkerd.io/v1alpha1
kind: AuthorizationPolicy
metadata:
  name: web-api-gateway
  namespace: my-app
spec:
  targetRef:
    group: policy.linkerd.io
    kind: Server
    name: web-http
  requiredAuthenticationRefs:
  - kind: ServiceAccount
    name: api-gateway
```

Server는 기존 Pod/port를 선택하며 앱, Service나 listener를 생성하지 않습니다. 해당 named port가 있어야 합니다. 선택된 트래픽은 관련 허용 정책이나 명시적인 다른 access policy가 없으면 기본 deny입니다. 적용 범위를 단계적으로 검사한 뒤 강제하세요.

AuthorizationPolicy는 Server나 지원 route를 대상으로 합니다. ServiceAccount 참조는 간단한 인증 조건이며 MeshTLSAuthentication·NetworkAuthentication으로 identity·network 집합을 표현할 수 있습니다. 한 정책 안의 required authentication ref는 모두 충족해야 합니다. 다른 허용 정책도 전체적으로 검토하세요.

기존 ServerAuthorization 방식에는 다음이 지원되는 **대안**입니다. 앞의 authorization과 함께 적용해야 하는 추가 필수 조건은 아닙니다:

```yaml
apiVersion: policy.linkerd.io/v1beta1
kind: ServerAuthorization
metadata:
  name: web-authz-legacy
  namespace: my-app
spec:
  server:
    name: web-http
  client:
    meshTLS:
      serviceAccounts:
      - name: api-gateway
        namespace: my-app
```

릴리스 CRD는 원문의 ServerAuthorization v1beta2가 아닌 v1beta1을 제공합니다. Server v1beta2는 여전히 제공되며 예시는 현재 storage version인 v1beta3을 사용합니다. AuthorizationPolicy가 더 유연한 권장 interface입니다. 다른 API group에 있는 같은 이름의 Istio 리소스와 혼동하지 마세요.

## 데이터 플레인

### Proxy 동작과 protocol 범위

linkerd2-proxy는 mesh 용도로 작성한 Rust proxy이며 HTTP/1.1, HTTP/2, gRPC와 TCP를 지원합니다. HTTP routing·metric에는 해석 가능한 HTTP가 필요합니다. 앱이 시작한 TLS는 opaque이며 UDP/QUIC·skip 트래픽은 TCP proxy 경로의 범위가 아닙니다.

해당 meshed TCP peer 사이에 transport mTLS를 제공합니다. Unmeshed peer와 명시적인 capture 우회는 별도 고려가 필요합니다. 기본 inbound policy는 unmeshed plaintext를 허용하므로 자동 mTLS가 모든 출발지에 인증을 강제한다는 뜻은 아닙니다.

Proxy는 HTTP 요청에 지연을 고려한 balancing, opaque TCP에 연결 단위 balancing을 적용합니다. Endpoint weight·routing rule과 runtime 지연 추정은 별개입니다. EWMA를 모든 요청이 항상 가장 빠른 한 endpoint로 간다는 보장으로 해석하지 마세요.

보편적인 10MB memory, 1ms 미만 p99나 고정 binary 크기는 없습니다. Version/build, architecture, 연결 수, policy/configuration, workload와 계측에 따라 측정해야 합니다.

### 프록시 트래픽 흐름

![새 mesh 연결의 HTTP 요청 흐름입니다. Outbound proxy가 목적지를 선택하고 proxy 간 mTLS와 inbound 정책 검사 뒤 앱에 전달합니다. 기존 연결은 재사용할 수 있습니다.](../../.gitbook/assets/ko-service-mesh-linkerd-02-architecture-5.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-linkerd-02-architecture-5.html)

Outbound의 discovery, routing/balancing, retry·timeout과 inbound 인가는 다른 책임입니다. 새 연결은 discovery·mTLS 설정이 필요할 수 있고 기존 연결·cache 설정은 재사용할 수 있습니다. 특히 쓰기의 안전한 retry 여부는 애플리케이션·protocol 의미에 따라 결정해야 합니다.

### 트래픽 캡처: linkerd-init 또는 CNI

생성된 proxy-init 또는 Linkerd CNI 설정을 사용하세요. 다음은 개념 순서이며 **호스트에서 실행할 iptables 명령이 아닙니다**:

```text
Inside the Pod network namespace:
  outbound TCP -> evaluate proxy-UID and configured bypass rules first
               -> redirect intercepted traffic to the outbound proxy (default 4140)
  inbound TCP  -> evaluate configured bypass rules
               -> redirect intercepted traffic to the inbound proxy (default 4143)

Linkerd CNI: installs the Linkerd-specific capture setup through the CNI chain.
linkerd-init: performs the setup at Pod startup when Linkerd CNI is not used.
```

원문은 모든 TCP REDIRECT 뒤에 proxy UID 우회를 추가해 proxy 자체 outbound를 보호하지 못했습니다. Host namespace에 그런 규칙을 적용하는 것도 Pod별 Linkerd 설정이 아닙니다. 실제 구현에는 추가 제외·chain과 설정한 iptables mode가 있습니다.

Opaque port는 protocol detection을 생략하면서 proxy 전송 처리를 유지합니다. Skip port는 proxy와 mesh 기능을 우회합니다. Server-first 트래픽을 위해 올바른 opaque/protocol 설정 대신 skip을 사용하지 마세요.

### Proxy를 수동 조립하기보다 생성된 Pod 확인

이전 수동 Pod에는 identity/bootstrap 자료가 빠졌고 제공되지 않는 upstream stable-2.16.0 이미지가 쓰였습니다. 선택한 CLI와 설치된 control-plane 설정으로 생성·검사하세요:

```bash
# The input is a complete, reviewed application manifest.
# Default mode adds the injection annotation for server-side admission.
linkerd inject web.yaml > web-annotated.yaml

# Manual mode materializes the proxy spec using the selected cluster configuration.
# Use CLI options for overrides; proxy config annotations are not applied in this mode.
linkerd inject --manual --native-sidecar \
  --proxy-cpu-request 100m --proxy-memory-request 64Mi \
  --proxy-cpu-limit 1 --proxy-memory-limit 250Mi \
  web.yaml > web-manually-injected.yaml
```

기본 inject는 annotation 변환입니다. Manual은 proxy spec을 만들고 override에 CLI option을 사용하며 server-side 주입처럼 proxy 설정 annotation을 적용하지 않습니다. 축약 proxy container를 완전한 설치로 복사하지 말고 생성 결과를 배포 전에 검토하세요.

```bash
: "${APP_POD:?Set an application Pod name in my-app}"
kubectl -n my-app get pod "$APP_POD" -o json |
  jq '{pod: .metadata.name, proxies: ([.spec.containers[]?, .spec.initContainers[]?] | map(select(.name == "linkerd-proxy") | {image, restartPolicy, resources, startupProbe, readinessProbe, livenessProbe}))}'
```

Native sidecar는 restartPolicy: Always로 initContainers에 나타납니다. CNI 경로를 구성하면 linkerd-init은 빠집니다. Proxy health endpoint는 설정한 admin port(기본 4191)의 /live와 /ready입니다. Native startup/readiness와 애플리케이션 readiness는 별개입니다.

## 인증서 체계

| 자료 | 기본 역할·저장 위치 |
|---|---|
| Trust anchor 인증서·bundle | 공개 신뢰 기반. linkerd-identity-trust-roots ConfigMap의 ca-bundle.crt |
| Root CA 개인 키 | PKI 소유자의 자료. Linkerd 실행에는 필요하지 않음 |
| Issuer 인증서·개인 키 | linkerd-identity-issuer Secret. 기본 crt.pem/key.pem |
| Kubernetes TLS issuer 통합 | 대응 scheme과 tls.crt/tls.key를 의도적으로 구성하는 대안 |
| Workload 키·인증서 | Proxy 로컬 credential. 명목 인증서 유효기간 24시간, 자동 갱신 |

Issuer·trust anchor 유효기간은 PKI 설정에 달려 있습니다. CLI 기본 생성 root/issuer는 1년이며 사용자 지정 10년 예시는 기본값이나 보편적 권장이 아닙니다. 고정된 예시 날짜를 복사하지 말고 실제 인증서 날짜를 검사하세요.

### Kubernetes workload identity

기본 Kubernetes identity 방식은 DNS 형식입니다:

```text
<service-account>.<namespace>.serviceaccount.identity.<linkerd-namespace>.<identity-trust-domain>

web-service.my-app.serviceaccount.identity.linkerd.cluster.local
```

같은 ServiceAccount의 여러 Pod는 이 identity를 공유하면서 각각 로컬 credential을 보유합니다. Identity trust domain은 설정 가능한 개념이며 바꾼 Kubernetes DNS suffix와 반드시 같지는 않습니다.

원문의 spiffe://root.linkerd.cluster.local/ns/.../sa/...는 기본 Kubernetes identity 형식이 아니었습니다. SPIFFE/SPIRE identity는 별도의 [외부 workload mesh-expansion 경로](https://linkerd.io/docs/tasks/adding-non-kubernetes-workloads/)에서 지원합니다. 그 identity/bootstrap 모델을 Kubernetes TokenReview와 바꿔 설명하면 안 됩니다.

### 갱신과 회전

Proxy release/v2.368.0의 identity client는 보통 **남은** 유효기간의 70% 뒤에 다음 인증서 요청을 예약하며 설정한 min/max refresh interval로 제한합니다. 오류·만료 경로에는 최소 지연을 사용할 수 있습니다. 모든 인증서에 대한 고정된 시각 보장이 아닙니다.

해당 client는 갱신 요청에 적재한 key/CSR 자료를 재사용합니다. 인증서 갱신과 개인 키·issuer·trust anchor 회전은 같은 작업이 아닙니다.

```bash
set -euo pipefail
kubectl -n linkerd get configmap linkerd-identity-trust-roots \
  -o jsonpath='{.data.ca-bundle\.crt}' > trust-bundle.pem
openssl crl2pkcs7 -nocrl -certfile trust-bundle.pem |
  openssl pkcs7 -print_certs -text -noout
kubectl -n linkerd get secret linkerd-identity-issuer -o json |
  jq -er '.data["crt.pem"] // .data["tls.crt"]' |
  base64 -d | openssl x509 -noout -dates
```

완전한 trust anchor 전환에는 여러 단계가 필요합니다:

1. 현재 유효한 root, issuer, 전체 consumer와 설치·PKI 소유 도구를 확인합니다.
2. 소유 도구로 기존 root 옆에 새 root를 추가합니다. 대상 proxy/control plane과 multicluster peer가 실제 overlap bundle을 적재했는지 확인하세요.
3. 새 root가 서명한 issuer credential로 회전하고 identity service 적재를 확인합니다.
4. 설정 공급 방식에 따라 consumer를 갱신·재생성하고 실제 새 credential과 해당 경로의 mTLS를 검증합니다.
5. 필요한 peer가 기존 root에 더 의존하지 않을 때만 제거하고 최종 bundle 전파 후 재검증합니다.

기존의 ConfigMap 갱신과 한 namespace 재시작은 issuer 전환·옛 root 제거까지 포함하지 않아 완전한 회전 절차가 아니었습니다. Helm/cert-manager/trust-manager 소유와 충돌하는 직접 변경을 피하세요. 이미 만료된 root는 정상 rollover가 아니라 복구 절차가 필요합니다.

```bash
linkerd check
linkerd check --proxy
kubectl -n linkerd get events --field-selector reason=IssuerUpdated
# Inspect each affected namespace/workload and its actual proxy version/identity.
kubectl -n my-app get pods -o wide
```

IssuerUpdated event 하나는 모든 proxy·원격 cluster가 전환되었다는 증거가 아닙니다. cert-manager가 issuer 갱신을 자동화하고 trust-manager가 bundle을 배포할 수 있지만 root 전환 검증은 여전히 조율해야 합니다. 실제 PKI 설계에 맞는 [수동](https://linkerd.io/docs/tasks/manually-rotating-control-plane-tls-credentials/) 또는 [관리형 credential 절차](https://linkerd.io/docs/tasks/automatically-rotating-control-plane-tls-credentials/)를 사용하세요. 이 장에서는 회전을 실행하지 않았습니다.

## 사이드카 주입 상세

![Namespace 의도, Pod-template override와 대상 여부를 결합해 Pod 생성 전에 주입을 결정합니다. Annotation 하나가 모든 Pod의 주입을 보장하지 않습니다.](../../.gitbook/assets/ko-service-mesh-linkerd-02-architecture-8.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-linkerd-02-architecture-8.html)

Controller workload는 Pod-template annotation을 사용하고 생성한 Pod를 확인합니다. 하나의 YAML mapping에 중복 metadata를 두면 충돌·덮어쓰기가 생기므로 namespace와 workload 예제를 별도 리소스·조각으로 구분하세요.

앞의 resource/log annotation은 proxy request·limit과 log 설정이며 실제 소비량 측정치가 아닙니다. Opaque-port override는 database port 2개를 더하는 것이 아니라 기본 목록을 대체하므로 필요한 port를 모두 유지하세요. Skip-port override는 해당 트래픽을 의도적으로 mesh 처리에서 제외합니다.

## 컴포넌트 간 통신

![Discovery, identity 검증, policy, admission의 일부 통신 역할입니다. 현재 기본값은 EndpointSlice와 TokenReview를 사용하며 포트 표에는 opaque TCP도 포함됩니다.](../../.gitbook/assets/ko-service-mesh-linkerd-02-architecture-9.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-linkerd-02-architecture-9.html)

| 구성 요소·경로 | 기본 port | Protocol·목적 |
|---|---|---|
| Destination Service | 8086 | Discovery/profile streaming gRPC |
| Identity Service | 8080 | 인증서 API gRPC |
| Policy Service | 8090 | Policy gRPC |
| Proxy Injector | Service 443 → Pod 8443 | HTTPS admission webhook |
| Proxy inbound | 4143 | HTTP/gRPC·opaque를 포함한 캡처 TCP |
| Proxy outbound | 4140 | 캡처한 outbound TCP |
| Proxy admin | 4191 | HTTP metric·health endpoint |

포트는 설정 가능하며 무조건적인 network 허용 목록이 아닙니다. Admin endpoint는 Envoy 같은 routing configuration interface가 아니며 정책·설정은 control-plane API로 전달됩니다.

## Istio 아키텍처와 비교

| 항목 | Linkerd | Istio |
|---|---|---|
| Control-plane 구성 | 이 릴리스의 핵심 Deployment 3개 안에 여러 논리 controller | 주요 기능을 통합한 Istiod와 모드별 구성 요소 |
| Data plane | Mesh용 Rust proxy | Envoy sidecar 또는 ambient ztunnel·선택적 waypoint |
| 설정 | Linkerd streaming gRPC API와 지원 리소스 | Envoy의 xDS와 지원 Istio/Gateway API 설정 |
| 확장 | 지원되는 Linkerd 기능·API 확인 | 모드·버전별 Envoy/Wasm/Lua 지원과 부착 확인 |
| Resource·성능 비교 | 같은 workload와 실제 설정으로 측정 | 같은 workload와 실제 설정으로 측정 |

xDS도 보통 gRPC를 사용하므로 protocol 이름이 본질적인 복잡성 순위는 아닙니다. CRD 수는 버전·확장에 따라 달라지고 runtime overhead를 측정하지 않습니다. Request/limit은 설정한 예약·상한이며 관측 memory·latency가 아닙니다. 같은 workload, traffic, protocol, policy와 실패 예산으로 비교하세요. [유지 관리되는 비교 가이드](../istio/comparison/README.md)를 참고하세요.

## 다음 단계와 근거

- [트래픽 관리](03-traffic-management.md), [보안](04-security.md), [관측성](05-observability.md)
- [아키텍처 퀴즈](../../quizzes/service-mesh/linkerd/architecture.md)
- [공식 아키텍처](https://linkerd.io/docs/reference/architecture/), [주입](https://linkerd.io/docs/features/proxy-injection/), [정책 참조](https://linkerd.io/docs/reference/authorization-policy/)
- [자동 mTLS](https://linkerd.io/docs/features/automatic-mtls/), [protocol 처리](https://linkerd.io/docs/features/protocol-detection/), [load balancing](https://linkerd.io/docs/features/load-balancing/)
- [고정 Destination API](https://github.com/linkerd/linkerd2-proxy-api/blob/v0.20.0/proto/destination.proto)
- [Kubernetes token 검증](https://github.com/linkerd/linkerd2/blob/edge-26.9.1/controller/identity/validator.go)과 [identity 형식](https://github.com/linkerd/linkerd2/blob/edge-26.9.1/controller/identity/domain.go)
- [고정 인증서 refresh 구현](https://github.com/linkerd/linkerd2-proxy/blob/a66af8117769df060adda6233302a2d1c4142229/linkerd/proxy/identity-client/src/certify.rs)
