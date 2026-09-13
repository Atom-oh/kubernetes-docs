# Istio 일반적인 에러 및 해결 방법

> **마지막 업데이트**: 2026년 9월 11일 · CLI·설정 검증: Istio 1.31.0

관측한 실패, 적용된 설정과 워크로드 모드부터 확인합니다. 아래 명령은 진단 예시이며 메시 전체를 초기화하는 절차가 아닙니다. Kubernetes/EKS 버전은 [설치 호환성 안내](../01-installation.md)를 확인하세요.

예시는 기존 app 네임스페이스, 8080 포트의 myapp Deployment/Service, istio-ingress 게이트웨이 네임스페이스와 기본 클러스터 DNS suffix를 사용합니다. 실제 리소스와 도메인으로 바꾸세요. Deployment YAML은 새 애플리케이션 전체가 아닌 **기존 Deployment에 병합하는 strategic-merge 조각**입니다. 이번 검토에서 클러스터 배포나 운영 부하 검증은 수행하지 않았습니다.

```bash
NS=app
GW_NS=istio-ingress
ISTIO_NS=istio-system
: "${POD:?Set the exact application Pod name}"
kubectl config current-context
istioctl version
kubectl -n "$NS" get pod "$POD" -o wide
```

## 목차

1. [파드 종료 시 연결 에러](#파드-종료-시-연결-에러)
2. [Sidecar 주입 문제](#sidecar-주입-문제)
3. [mTLS 연결 실패](#mtls-연결-실패)
4. [VirtualService 라우팅 실패](#virtualservice-라우팅-실패)
5. [Gateway 설정 문제](#gateway-설정-문제)
6. [메모리 및 성능 문제](#메모리-및-성능-문제)
7. [인증서 만료](#인증서-만료)
8. [DNS 해석 실패](#dns-해석-실패)
9. [Envoy 초기화 타임아웃](#envoy-초기화-타임아웃)
10. [디버깅 도구](#디버깅-도구)

## 파드 종료 시 연결 에러

### 문제 설명

종료 중 connection reset, broken pipe, EOF, HTTP 503이 발생할 수 있습니다. 증상만으로 Envoy가 먼저 종료되었다고 확정할 수 없습니다. 애플리케이션·프록시 로그, 응답 플래그, Pod 삭제 시점과 EndpointSlice 변경을 함께 확인하세요.

### 발생 원인

일반 containers에 있는 애플리케이션과 기존 방식의 sidecar는 종료 순서가 보장되지 않습니다. 애플리케이션이 아직 프록시를 필요로 하는데 프록시가 종료될 수도 있고, 애플리케이션이 처리 중인 요청을 끝내기 전에 수신을 중단할 수도 있습니다. Kubernetes native sidecar는 initContainers의 restartPolicy: Always를 사용하며 주 컨테이너가 종료된 뒤 종료합니다.

Pod 종료 유예에는 preStop 실행이 포함됩니다. 언제나 30초인 것은 아니며 이미 종료된 프로세스를 나중에 다시 강제 종료하지도 않습니다. Endpoint 갱신, 로드 밸런서 전파와 장기 연결도 별도의 실패 구간을 만들 수 있습니다.

### 해결 방법

#### 방법 1: 애플리케이션과 프록시 종료 예산 설정

다음 annotation은 proxy drain을 설정합니다. preStop hook을 설치하거나 모든 활성 요청의 완료를 무조건 기다리는 것은 **아닙니다**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: app
spec:
  template:
    metadata:
      annotations:
        proxy.istio.io/config: |
          terminationDrainDuration: 30s
          holdApplicationUntilProxyStarts: true
      labels: {}
    spec:
      terminationGracePeriodSeconds: 60
```

30초·60초는 예시이며 보편적 최소값이 아닙니다. 애플리케이션 종료, hook과 proxy drain을 함께 계산하세요. holdApplicationUntilProxyStarts는 **시작**에 관한 설정이며 종료 순서 제어가 아닙니다. ProxyConfig 변경은 새 Pod에 적용됩니다.

1.31의 일반 terminationDrainDuration 경로는 시간 기반입니다. EXIT_ON_ZERO_ACTIVE_CONNECTIONS를 사용하면 agent가 최소 drain 기간 이후 downstream listener 연결 수를 확인하며, 이 경로는 일반 drain 타이머를 고정 상한으로 사용하지 않습니다. Kubernetes 종료 유예와 통계 누락·오류도 영향을 줍니다. 실제 연결 특성으로 검증해야 합니다.

#### 방법 2: Native sidecar 종료 순서 검토

지원되는 Kubernetes/Istio 조합에서 다음 annotation은 새로 생성되는 주입 대상 Pod에 native injection을 선택합니다:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: app
spec:
  template:
    metadata:
      annotations:
        sidecar.istio.io/nativeSidecar: 'true'
      labels: {}
    spec: {}
```

Kubernetes 기능은 1.33부터 stable이지만 Istio의 native-sidecar annotation은 Alpha로 문서화되어 있습니다. 실제 주입된 initContainers와 애플리케이션 종료 동작을 확인하세요. 순서만으로 요청 실패 0건이나 Pod 종료 유예를 넘는 무한 대기가 보장되지 않습니다. Ambient 워크로드에는 이 방식으로 설정할 Pod별 Envoy가 없습니다.

sidecar.istio.io/terminationGracePeriodSeconds는 문서화된 annotation이 아닙니다. 실제 spec.terminationGracePeriodSeconds를 설정해야 합니다.

#### 방법 3: 설치 범위 기본값

다음은 **istioctl 설치 입력**이며 제거된 클러스터 내 Istio operator로 reconcile하는 리소스가 아닙니다:

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      terminationDrainDuration: 30s
      holdApplicationUntilProxyStarts: true
```

설치 소유 도구를 통해 render 변경을 검토하고 영향받는 워크로드를 계획적으로 롤아웃하세요. 이전 shell/netstat preStop 루프는 시간 제한 없이 listening socket도 세고 proxy 이미지에 유틸리티가 있다고 가정했습니다. 애플리케이션 작업 완료를 신뢰할 수 있게 확인하는 방식이 아닙니다.

### 검증 방법

```bash
kubectl -n "$NS" get pod "$POD" -o json
kubectl -n "$NS" logs -f "$POD" -c istio-proxy
kubectl -n "$NS" get events --field-selector "involvedObject.name=$POD"
kubectl -n "$NS" get endpointslices.discovery.k8s.io \
  -l kubernetes.io/service-name=myapp -o yaml
```

Pod가 존재할 때 로그를 수집하세요. --previous는 같은 Pod의 이전 컨테이너 인스턴스를 의미하며 “현재 종료 중인 컨테이너”나 임의의 삭제된 Pod 로그를 뜻하지 않습니다.

### 모범 사례

애플리케이션 SIGTERM 처리와 실제 readiness 동작을 구현하세요. 애플리케이션이나 probe가 확인하지 않는 /tmp/not-ready 파일은 아무 효과가 없습니다. 제한된 preStop 지연은 전파 시간을 줄 수 있지만 endpoint 수렴 확인이나 애플리케이션 정상 종료의 대체재가 아닙니다. 애플리케이션 sleep을 항상 금지하거나 종료 유예 60초를 보편적 최소값으로 정할 수 없습니다. 쓰기 retry를 끄고 원시 HTTP·비HTTP 실패를 측정하세요. [롤아웃 비교](../comparison/03-sidecar-vs-ambient.md)를 참고하세요.

## Sidecar 주입 문제

### 문제 1: Sidecar가 주입되지 않음

프록시가 없다고 결론 내리기 전에 일반·native sidecar 위치를 모두 확인합니다:

```bash
kubectl -n "$NS" get pod "$POD" -o jsonpath='{.spec.containers[*].name}{"\n"}{.spec.initContainers[*].name}{"\n"}'
kubectl get namespace "$NS" --show-labels
kubectl -n "$NS" get deployment myapp -o yaml
istioctl x check-inject "$POD" -n "$NS"
kubectl get mutatingwebhookconfigurations
kubectl -n "$ISTIO_NS" get pods -l app=istiod --show-labels
kubectl -n "$ISTIO_NS" logs -l app=istiod --all-containers=true --tail=200
```

Ambient enrollment에는 의도적으로 애플리케이션 sidecar istio-proxy가 없습니다. Sidecar 모드는 namespace revision/tag, Pod template label, hostNetwork, webhook selector와 admission event를 확인하세요. 자동 주입은 host-network Pod와 지정된 시스템 namespace를 제외합니다.

[주입 가이드](../advanced/07-sidecar-injection.md)에 따라 설치에 맞는 revision/tag 또는 기존 injection label을 사용하세요. 충돌하는 istio-injection과 istio.io/rev 선택을 혼합하지 않습니다. Label은 새 Pod에 영향을 주며 기존 Pod에 sidecar를 추가하지 않습니다. 영향을 검토한 뒤 소유 rollout 도구로 의도한 워크로드만 재생성하세요.

Pod별 override는 workload의 Pod template 안에 있는 **label**을 권장합니다:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: app
spec:
  template:
    metadata:
      annotations: {}
      labels:
        sidecar.istio.io/inject: 'true'
    spec: {}
```

같은 이름의 annotation은 deprecated입니다. false label은 의도적인 제외일 수 있으므로 무조건 오류로 보고 덮어쓰지 마세요. true label도 모든 webhook 선택·플랫폼 제한을 우회하지는 않습니다. 주입은 Istiod가 처리하며 과거 app=sidecar-injector 로그 선택자는 현재 통합 injector를 찾지 못합니다.

### 문제 2: Sidecar 리소스 부족

컨테이너 종료 원인, event, 사용량과 throttling을 확인합니다. OOMKilled는 메모리 제한 문제일 수 있지만 CrashLoopBackOff는 다양한 원인의 재시작·대기 상태입니다. runAsNonRoot/non-numeric-user 검증 오류는 security context·image 문제이며 RAM 증설로 해결되지 않습니다.

측정상 리소스 변경이 필요하면 Pod template에서 request와 limit을 함께 설정합니다. 예시 수량은 워크로드에 맞게 조정해야 합니다:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: app
spec:
  template:
    metadata:
      annotations:
        sidecar.istio.io/proxyCPU: 200m
        sidecar.istio.io/proxyCPULimit: 1000m
        sidecar.istio.io/proxyMemory: 256Mi
        sidecar.istio.io/proxyMemoryLimit: 512Mi
      labels: {}
    spec: {}
```

새로 주입된 설정과 namespace LimitRange/ResourceQuota를 확인하세요. Admission을 통과하기 위해 이미지 보안 설정을 무작정 덮어쓰지 않습니다.

## mTLS 연결 실패

### 문제 설명

Upstream connect error, 503, WRONG_VERSION_NUMBER는 TLS, protocol, endpoint 또는 네트워크 원인일 수 있습니다. PeerAuthentication은 **수신 mTLS 허용 방식**을 제어합니다. DestinationRule TLS 설정은 client 측 Envoy의 송신 TLS를 제어합니다. Client의 PeerAuthentication STRICT가 그 client의 mTLS 송신을 강제하는 것은 아닙니다.

### PeerAuthentication과 DestinationRule

Auto mTLS가 켜져 있고 DestinationRule에 명시적인 TLS override가 없으면 Istio가 알려진 mesh endpoint에 워크로드 mTLS를 선택합니다. 명시적인 DISABLE override는 목적지 STRICT와 충돌할 수 있습니다. 소유 도구로 의도하지 않은 override를 제거하거나 의도적으로 구성한 Istio mTLS 목적지에 ISTIO_MUTUAL을 사용하세요. 임의의 외부 TLS·평문 서비스에 강제하지 않습니다.

다음 selector 없는 정책은 호출자들이 strict 적용 준비를 마친 뒤 **app namespace**에 적용하는 예시입니다:

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: app
spec:
  mtls:
    mode: STRICT
```

설정된 root namespace(보통 istio-system)의 selector 없는 정책은 그 namespace의 서비스만이 아니라 메시 전체 범위입니다. 적용 전 마이그레이션 영향을 확인하세요. Ambient의 transport mTLS는 PeerAuthentication DISABLE로 끌 수 없습니다. 인증과 AuthorizationPolicy는 별개이며 403이 항상 TLS 실패를 뜻하지 않습니다.

### 디버깅 명령어

```bash
istioctl x describe pod "$POD" -n "$NS"
kubectl get peerauthentication -A -o yaml
kubectl get destinationrule -A -o yaml
istioctl proxy-config clusters "$POD" -n "$NS" \
  --fqdn myapp.app.svc.cluster.local -o json
istioctl proxy-config secret "$POD" -n "$NS"
```

송신 cluster 설정은 해당 호출자 proxy, 수신 정책은 목적지 proxy에서 확인하세요. Experimental describe는 진단 보조이며 모든 경로 암호화의 증거가 아닙니다. 인증서 유효성, identity, trust domain, 실제 transport socket과 응답 플래그를 확인합니다. Waypoint와 ztunnel 진단은 서로 다르므로 [mTLS 가이드](../security/01-mtls.md)를 참고하세요.

## VirtualService 라우팅 실패

### 문제 1: 트래픽이 라우팅되지 않음

404는 Envoy나 애플리케이션이 반환할 수 있습니다. Route 변경 전 발생 지점과 응답 상세를 확인하세요. hosts: myapp.example.com에서 내부 Service myapp으로 보내는 VirtualService는 적절한 gateway에 연결되고 요청 Host/authority가 일치하면 **유효합니다**. Frontend host와 backend Service 이름이 같을 필요는 없습니다.

Mesh 트래픽은 요청한 service host를, ingress 트래픽은 gateway가 허용한 domain과 attachment를 확인합니다. 짧은 destination 이름은 설정 리소스의 namespace 기준으로 해석되므로 FQDN이 namespace 혼동을 줄입니다.

### 문제 2: Subset not found 또는 No healthy upstream

다음 완전한 두 리소스는 mesh 트래픽을 지정된 subset으로 보냅니다:

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp
  namespace: app
spec:
  hosts:
  - myapp.app.svc.cluster.local
  http:
  - route:
    - destination:
        host: myapp.app.svc.cluster.local
        subset: v1
        port:
          number: 8080
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp
  namespace: app
spec:
  host: myapp.app.svc.cluster.local
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

Service가 실제로 version: v1인 ready endpoint를 선택해야 합니다. DestinationRule subset 이름만 맞춰도 Pod가 생성되거나 Service selector·endpoint 상태가 고쳐지지는 않습니다. 목적지 Service port, protocol 선택, 정책 가시성과 경쟁 route를 확인하세요. 예시는 기본 cluster.local suffix를 가정합니다.

### 디버깅

```bash
istioctl analyze -n "$NS"
istioctl proxy-config routes "$POD" -n "$NS"
istioctl proxy-config endpoints "$POD" -n "$NS"
kubectl -n "$NS" get svc myapp -o yaml
kubectl -n "$NS" get pods -l app=myapp --show-labels
kubectl -n "$NS" get endpointslices.discovery.k8s.io \
  -l kubernetes.io/service-name=myapp -o yaml
```

Analyze는 정적 설정 검사 보조입니다. 실제 요청을 운반하는 proxy의 route/cluster/endpoint를 확인하세요. 설정은 즉시 전파되지 않습니다. Ingress가 Service로 보낸 요청에 별도의 mesh-only VirtualService subset 선택이 자동 상속되지도 않습니다.


## Gateway 설정 문제

### 문제 1: Gateway에 트래픽이 도달하지 않음

HTTP 응답 이전의 connection refused나 timeout은 DNS, listener/Service port 불일치, 로드 밸런서 target 누락 또는 네트워크 차단일 수 있습니다. 실제 gateway Deployment/Service부터 찾으세요. Namespace와 이름은 설치 방식에 따라 다릅니다.

```bash
kubectl -n "$GW_NS" get svc,pods --show-labels
kubectl -n "$GW_NS" get gateways.networking.istio.io -o yaml
kubectl -n "$NS" get virtualservice -o yaml
# For installations using Kubernetes Gateway API instead:
kubectl get gatewayclasses.gateway.networking.k8s.io
kubectl -n "$GW_NS" get gateways.gateway.networking.k8s.io -o yaml
kubectl -n "$NS" get httproutes.gateway.networking.k8s.io -o yaml
```

Service의 loadBalancer ingress를 확인합니다. Provider에 따라 IP, hostname 또는 둘 다 제공합니다. EKS에서는 실제 controller 설정에 맞춰 load balancer target health, target type, security group과 네트워크 경로도 확인하세요. Istiod 재시작으로 AWS target 비정상이 해결되지는 않습니다.

Istio Gateway(networking.istio.io)와 Kubernetes Gateway API(gateway.networking.k8s.io)는 다른 리소스입니다. Gateway API에서는 Accepted, Programmed와 HTTPRoute parent의 ResolvedRefs 같은 조건 및 controller event를 확인하세요. Gateway 이름 오타, listener 불일치, route attachment 거부는 외부 연결 장애와 다른 수정이 필요합니다.

### 문제 2: HTTPS와 Route 연결

다음 예시는 **Istio Gateway API**를 사용합니다. Selector를 실제 gateway Pod label로 바꾸고 소유한 domain과 유효한 인증서를 사용하며 Deployment의 Service가 443을 노출하는지 확인하세요. 앞 절에서 정의한 backend subset을 사용합니다:

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: myapp-gateway
  namespace: istio-ingress
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: myapp-tls-secret
    hosts:
    - myapp.example.com
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp-ingress
  namespace: app
spec:
  hosts:
  - myapp.example.com
  http:
  - route:
    - destination:
        host: myapp.app.svc.cluster.local
        subset: v1
        port:
          number: 8080
    retries:
      attempts: 0
  gateways:
  - istio-ingress/myapp-gateway
```

SIMPLE이 downstream TLS를 종료하므로 route는 http를 사용합니다. TLS PASSTHROUGH listener에는 적절한 TLS/SNI route가 필요합니다. TLS 종료 listener에 tls route만 연결하거나 암호화된 passthrough 내부의 HTTP path를 매칭하려고 하면 안 됩니다.

credentialName은 gateway workload가 접근할 credential을 가리킵니다. 이 예시의 gateway Pod와 TLS Secret은 istio-ingress에 있습니다:

```bash
kubectl -n "$GW_NS" create secret tls myapp-tls-secret   --cert=path/to/fullchain.pem   --key=path/to/key.pem
```

이미 관리 중인 Secret이면 인증서 소유 도구의 갱신 절차를 사용하세요. 이 명령은 인증서를 발급하거나 자체 서명 issuer를 신뢰하게 만들지 않습니다. Domain/SAN, 제공되는 chain, 만료, client trust와 gateway SDS 상태를 확인해야 합니다. 별도 Gateway 설정 객체의 namespace가 항상 gateway workload의 credential namespace를 대체하는 것은 아닙니다.

## 메모리 및 성능 문제

### 문제 1: Envoy 메모리 사용량 증가

실제 컨테이너 memory/CPU, limit, 연결 수, route/cluster/listener와 telemetry cardinality를 비교합니다. 관련 없는 큰 ConfigMap이나 Secret이 모든 proxy에 자동 적재되지는 않습니다. 해당 proxy가 소비하는 설정·데이터가 메모리 사용량과 연결되어야 합니다. Memory leak은 버전별 근거가 필요합니다.

사용하지 않는 설정이 주요 원인이면 Sidecar 리소스로 선택한 **sidecar** workload에 가져오는 설정 범위를 줄일 수 있습니다:

```yaml
apiVersion: networking.istio.io/v1
kind: Sidecar
metadata:
  name: myapp-scope
  namespace: app
spec:
  workloadSelector:
    labels:
      app: myapp
  egress:
  - hosts:
    - ./*
    - istio-system/*
```

예시는 app과 istio-system의 서비스만 포함합니다. 범위를 좁히기 전에 실제 namespace 간·외부 의존성을 확인하고 Sidecar selector 중첩을 피하세요. 설정 범위 제어이며 egress 방화벽이나 ambient waypoint 정책이 아닙니다. 관측한 동작에 따라 앞의 Pod-template annotation으로 메모리 request·limit을 조정하세요.

### 문제 2: 높은 지연 시간

P99 1초 초과는 정의한 워크로드 예산과 비교해야 의미가 있습니다. Timeout 변경 전에 애플리케이션 처리, upstream 지연, 포화, CPU throttling, 연결 풀, payload와 retry 증폭을 확인합니다.

다음은 앞의 myapp VirtualService를 **대체**하며 5초 route deadline과 명시적인 retry 비활성화를 추가합니다:

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp
  namespace: app
spec:
  hosts:
  - myapp.app.svc.cluster.local
  http:
  - route:
    - destination:
        host: myapp.app.svc.cluster.local
        subset: v1
        port:
          number: 8080
    retries:
      attempts: 0
    timeout: 5s
```

Deadline은 대기를 제한할 뿐 backend를 빠르게 만들지 않습니다. 무조건적인 retry는 과부하를 증폭하거나 미확정 쓰기를 반복할 수 있습니다. 특정 멱등 작업에 retry가 적합하면 종단 deadline 안에서 예산을 정하고 실제 시도를 측정하세요. [Retry 및 Timeout](../traffic-management/05-retry-timeout.md)을 참고하세요.

## 인증서 만료

### 문제 설명

x509 만료와 handshake 실패는 workload leaf, 서명 intermediate/root, ingress 인증서 또는 시계 오차 문제일 수 있습니다. 유효기간은 CA/provider와 설정에 따라 달라지므로 “10년”이나 “24시간”이 보편적인 진단 기준이 아닙니다.

### 진단과 복구

실제 공개 trust bundle과 적재된 workload 인증서를 확인합니다:

```bash
# Public trust bundle, not a private CA key.
kubectl -n "$NS" get configmap istio-ca-root-cert \
  -o jsonpath='{.data.root-cert\.pem}' > root-cert.pem
openssl crl2pkcs7 -nocrl -certfile root-cert.pem |
  openssl pkcs7 -print_certs -text -noout
istioctl proxy-config secret "$POD" -n "$NS"
kubectl -n "$ISTIO_NS" logs -l app=istiod --all-containers=true --tail=200
```

사용자 지정 통합이면 표준 trust ConfigMap과 다를 수 있으므로 실제 CA provider를 확인하세요. PKCS7 검사는 PEM bundle의 첫 인증서만이 아니라 모든 인증서를 표시합니다. 현재 UTC, CA/CSR 오류, identity token, Istiod/SDS 연결과 인증서 갱신 절차를 함께 확인합니다.

istioctl 1.31에는 x ca root 명령이 없습니다. Leaf가 만료되었다는 이유만으로 CA를 삭제·재생성하지 마세요. 계획하지 않은 trust root 교체는 의존하는 모든 workload를 단절시킬 수 있습니다. 실제 갱신·연결·provider 원인을 고치고 필요한 신뢰 중첩 기간을 포함한 지원 CA 회전 절차를 사용해야 합니다. 복구 절차에 필요한 경우에만 특정 영향받은 workload를 재시작하세요.

## DNS 해석 실패

### 문제 설명

No-such-host나 lookup timeout이면 애플리케이션 DNS, CoreDNS/upstream DNS, Service 존재·search suffix와 Istio DNS capture를 구분합니다.

```bash
kubectl -n kube-system get svc kube-dns
kubectl -n kube-system get pods -l k8s-app=kube-dns
kubectl -n kube-system get endpointslices.discovery.k8s.io \
  -l kubernetes.io/service-name=kube-dns
# Run from the affected app container only if it includes these tools.
kubectl -n "$NS" exec "$POD" -c myapp -- cat /etc/resolv.conf
kubectl -n "$NS" exec "$POD" -c myapp -- nslookup myapp.app.svc.cluster.local
```

최소 애플리케이션·proxy 이미지에 진단 도구가 있다고 가정하지 마세요. 필요하면 승인된 진단 컨테이너를 사용합니다. UDP/TCP 53 NetworkPolicy, 노드·resolver 연결과 대상 Pod의 dnsPolicy/search 설정을 확인하세요.

ServiceEntry는 Istio에 외부 서비스를 등록합니다. CoreDNS를 복구하거나 공개 DNS record를 만들고 미해결 upstream hostname을 해결해 주는 것은 아닙니다:

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
  namespace: app
spec:
  hosts:
  - api.example.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

api.example.com을 실제 외부 hostname으로 바꾸세요. DNS 해석은 upstream endpoint를 결정합니다. 모드·버전·설정에 따라 Istio DNS capture/IP 할당이 synthetic address로 응답할 수 있지만 실제 upstream의 이름 해석·연결 성공을 입증하지는 않습니다. [DNS capture 안내](../advanced/04-dns-cache.md)를 확인하세요. 이미 HTTPS를 보내는 애플리케이션이라면 여기의 HTTPS 선언 때문에 TLS origination을 한 번 더 추가할 필요는 없습니다.

## Envoy 초기화 타임아웃

### 문제 설명

“Waiting for Envoy proxy to be ready”는 xDS/CA 연결, 설정 거부, 리소스, 인증서·token 또는 bootstrap 문제일 수 있습니다. Probe 지연을 늘리기 전에 Pod/init-container 상태, proxy/Istiod 로그, event와 proxy-status를 확인하세요.

holdApplicationUntilProxyStarts는 proxy 준비까지 애플리케이션 시작을 지연합니다. 준비될 수 없는 Envoy의 원인을 고치지는 않습니다. initialDelaySeconds만 있는 readinessProbe는 probe action이 없어 유효하지 않습니다.

애플리케이션이 실제로 8080의 /ready를 구현한다면 다음 조각으로 구체적인 startup/readiness 동작을 구성할 수 있습니다:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: app
spec:
  template:
    metadata:
      annotations:
        proxy.istio.io/config: |
          holdApplicationUntilProxyStarts: true
      labels: {}
    spec:
      containers:
      - name: myapp
        startupProbe:
          httpGet:
            path: /ready
            port: 8080
          periodSeconds: 2
          failureThreshold: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          periodSeconds: 5
          failureThreshold: 3
```

Action과 임계값을 애플리케이션에 맞추세요. StartupProbe는 시작 허용 시간, readiness는 endpoint 자격을 제어합니다. 둘 다 Istiod 연결 장애를 고치지는 않습니다. 주입 후 probe rewrite와 실제 proxy readiness 설정을 확인한 뒤 애플리케이션 probe 실패를 Envoy 초기화 원인으로 판단하세요.

## 디버깅 도구

### istioctl 명령어

```bash
istioctl analyze -A
istioctl proxy-status
istioctl proxy-config all "$POD" -n "$NS"
istioctl proxy-config log "$POD" -n "$NS"
# Temporarily change levels only on the selected Envoy.
istioctl proxy-config log "$POD" -n "$NS" --level http:debug
# Restore the previously recorded levels afterwards; --reset restores defaults.
istioctl bug-report --include "$NS" --duration 10m

# Ambient has ztunnel diagnostics; Envoy commands apply to waypoints.
istioctl ztunnel-config workloads -n "$ISTIO_NS"
istioctl ztunnel-config certificates -n "$ISTIO_NS"
```

Experimental 명령은 바뀔 수 있고 실제 트래픽 검증을 대체하지 않습니다. 일시적인 debug 전에 로그 수준을 기록하고 나중에 복원하세요. Reset은 기본값이며 기존 사용자 지정 수준과 다를 수 있습니다. 진단 시간을 제한하고 bug-report archive를 공유하기 전에 수집한 설정·로그 데이터를 검토합니다.

### Envoy Admin API

Loopback에만 포워딩합니다:

```bash
# Keep this command running; use a second terminal for the HTTP requests.
kubectl -n "$NS" port-forward --address 127.0.0.1 "$POD" 15000:15000

```

다른 터미널:

```bash
curl --fail --silent --show-error http://127.0.0.1:15000/clusters
curl --fail --silent --show-error http://127.0.0.1:15000/stats/prometheus
curl --fail --silent --show-error http://127.0.0.1:15000/config_dump
```

Sidecar·waypoint의 Envoy용 명령이며 별도 admin 인터페이스를 가진 ztunnel용이 아닙니다. 마치면 port-forward를 종료하세요. 로그 변경에는 앞의 특정 proxy 대상 istioctl을 사용하고 기록한 수준으로 복원합니다.

### 일반적인 로그 확인

```bash
kubectl -n "$NS" logs "$POD" -c myapp
kubectl -n "$NS" logs "$POD" -c istio-proxy
# Only when that container has a prior instance in this same Pod:
kubectl -n "$NS" logs "$POD" -c istio-proxy --previous
kubectl -n "$NS" logs -f "$POD" -c istio-proxy
```

현재 Pod에서 수집하는 것만으로 삭제된 Pod의 로그가 보존되지는 않습니다. 요청 시점, trace/request ID, 응답 플래그와 관련 endpoint·설정 변경을 함께 사건 근거로 보관하세요.

## 참고 자료

- [주입 문제 해결](https://istio.io/latest/docs/ops/common-problems/injection/)과 [주입 설정](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)
- [네트워크 문제](https://istio.io/latest/docs/ops/common-problems/network-issues/)와 [TLS 방향·auto mTLS](https://istio.io/latest/docs/ops/configuration/traffic-management/tls-configuration/)
- [Istio annotation](https://istio.io/latest/docs/reference/config/annotations/)과 [릴리스 1.31 proxy 종료 코드](https://github.com/istio/istio/blob/1.31.0/pkg/envoy/agent.go)
- [Kubernetes Pod 종료](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)와 [native sidecar](https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/)
- [Proxy 진단](https://istio.io/latest/docs/ops/diagnostic-tools/proxy-cmd/), [CA 통합](https://istio.io/latest/docs/tasks/security/cert-management/plugin-ca-cert/), [보안 ingress](https://istio.io/latest/docs/tasks/traffic-management/ingress/secure-ingress/)
- [Kubernetes DNS 진단](https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/)과 [Istio DNS proxy](https://istio.io/latest/docs/ops/configuration/traffic-management/dns-proxy/)
- [Observability](../observability/README.md), [Security](../security/README.md), [Traffic Management](../traffic-management/README.md)
