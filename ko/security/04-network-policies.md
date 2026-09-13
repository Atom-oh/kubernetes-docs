# 네트워크 정책 (Network Policies)

> **검토 기준**: Kubernetes 1.35 OpenAPI, Cilium 1.20.1, Calico 3.32.2와 현재 AWS 문서. 오프라인 검사는 클러스터 호환성 검증이 아닙니다.
> **마지막 업데이트**: 2026년 9월 13일

Kubernetes 네트워크 정책은 Pod 간 트래픽을 제어하는 방화벽 규칙입니다. 이 문서에서는 기본 NetworkPolicy부터 Cilium과 Calico의 확장 기능까지 상세히 다룹니다.

각 절은 독립적인 예제이며 모든 정책을 합치면 유효 권한이 달라집니다. 실제 클러스터·클라우드 배포나 온라인 연결 시험은 수행하지 않았습니다.

## 목차

1. [네트워크 정책 개요](#network-policy-overview)
2. [Kubernetes NetworkPolicy 스펙](#kubernetes-networkpolicy-spec)
3. [기본 거부 정책](#default-deny-policies)
4. [정책 순서 및 평가](#policy-order-and-evaluation)
5. [Cilium 네트워크 정책 확장](#cilium-network-policy-extensions)
6. [Calico 네트워크 정책 확장](#calico-network-policy-extensions)
7. [설계 패턴](#design-patterns)
8. [네트워크 정책 테스트](#testing-network-policies)
9. [EKS 고려사항](#eks-considerations)
10. [시각화 도구](#visualization-tools)

---

<span id="네트워크-정책-개요"></span>

## 네트워크 정책 개요 {#network-policy-overview}

### 네트워크 정책이란?

Kubernetes NetworkPolicy는 자신의 네임스페이스에 있는 Pod를 선택해 지원하는 ingress·egress 트래픽을 제어합니다. 특정 방향에 자신을 선택하는 정책이 없으면 그 방향은 NetworkPolicy로 격리되지 않습니다. 그래도 라우팅, Security Group, NACL, 다른 정책 엔진이 연결을 차단할 수 있습니다.

**양쪽 엔드포인트가 허용해야 합니다.** Pod 간 연결은 출발지의 유효 egress와 목적지의 유효 ingress를 모두 만족해야 하며, 허용된 연결의 응답 트래픽은 암묵적으로 허용됩니다. 지원 플러그인이 비동기로 정책을 구현하므로 API 오브젝트 생성만으로 집행을 입증할 수 없습니다. 노드·hostNetwork 트래픽과 TCP/UDP/SCTP 외 프로토콜은 구현별 범위를 확인합니다. 다음 그림은 정책 의도이며 도달 가능성을 보장하지 않습니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    네트워크 정책 없음 (기본 상태)                          │
│                                                                         │
│    ┌─────────┐        ┌─────────┐        ┌─────────┐                   │
│    │  Pod A  │◀──────▶│  Pod B  │◀──────▶│  Pod C  │                   │
│    └─────────┘        └─────────┘        └─────────┘                   │
│         ▲                  ▲                  ▲                         │
│         │                  │                  │                         │
│         └──────────────────┴──────────────────┘                         │
│              모든 Pod 간 자유로운 통신 가능                                │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    네트워크 정책 적용 후                                  │
│                                                                         │
│    ┌─────────┐        ┌─────────┐        ┌─────────┐                   │
│    │  Pod A  │───────▶│  Pod B  │        │  Pod C  │                   │
│    └─────────┘        └─────────┘        └─────────┘                   │
│                            ▲                                            │
│                            │ 허용                                       │
│                       ┌────┴────┐                                       │
│                       │ 정책에  │                                       │
│                       │ 의해    │                                       │
│                       │ 제어됨  │                                       │
│                       └─────────┘                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

### 네트워크 정책의 특징

| 특성 | 설명 |
|------|------|
| **네임스페이스 범위** | NetworkPolicy는 네임스페이스 내 리소스에 적용 |
| **추가적(Additive)** | 선택된 Kubernetes NetworkPolicy의 방향별 허용 규칙을 합칩니다. Cilium deny, Calico tier, AWS 관리 정책은 별도 의미를 가집니다 |
| **선택적 적용** | podSelector로 대상 Pod 지정 |
| **방향별 제어** | Ingress(수신)와 Egress(송신) 별도 제어 |
| **CNI 의존** | CNI 플러그인이 NetworkPolicy를 지원해야 함 |

### CNI별 NetworkPolicy 지원

| CNI | 기본 NetworkPolicy | 확장 기능 | L7 정책 |
|-----|-------------------|----------|--------|
| **Cilium** | ✓ | CiliumNetworkPolicy, CiliumClusterwideNetworkPolicy | ✓ |
| **Calico** | ✓ | GlobalNetworkPolicy, NetworkSet, Tier | 선택적 Istio/Dikastes 통합; 설치한 제품·버전 확인 필요 |
| **Weave Net (보관된 프로젝트)** | 과거 지원 | 신규 배포는 유지보수 중인 구현 검토 | ✗ |
| **Flannel 단독** | 자체 정책 집행 없음 | 별도로 지원되는 정책 엔진 필요 | ✗ |
| **Amazon VPC CNI** | ✓ 지원되는 EC2 Linux 노드에서 활성화 필요 | 표준 NetworkPolicy; VPC CNI 1.21+의 ClusterNetworkPolicy | EKS Auto Mode 노드의 DNS egress; EKS 고려사항 참고 |

---

<span id="kubernetes-networkpolicy-스펙"></span>

## Kubernetes NetworkPolicy 스펙 {#kubernetes-networkpolicy-spec}

### 기본 구조

`policyTypes`를 명시합니다. 생략하면 기본 Ingress에 실제 egress 규칙이 하나 이상 있을 때 Egress를 추가합니다. 빈 규칙 배열만으로 양쪽 방향 격리가 되는 것은 아닙니다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: example-policy
  namespace: default
spec:
  # 정책이 적용될 Pod 선택
  podSelector:
    matchLabels:
      app: web

  # 정책 유형 (생략 시 policyTypes 자동 추론)
  policyTypes:
    - Ingress
    - Egress

  # 인그레스 규칙 (수신 트래픽)
  ingress:
    - from:
        - podSelector:
            matchLabels:
              role: frontend
        - namespaceSelector:
            matchLabels:
              project: myproject
        - ipBlock:
            cidr: 172.17.0.0/16
            except:
              - 172.17.1.0/24
      ports:
        - protocol: TCP
          port: 80
        - protocol: TCP
          port: 443

  # 이그레스 규칙 (송신 트래픽)
  egress:
    - to:
        - podSelector:
            matchLabels:
              role: database
      ports:
        - protocol: TCP
          port: 5432
```

### podSelector

정책 자신의 네임스페이스에서 Pod를 선택합니다. 아래는 대안적인 spec 조각이며 단독 API 리소스가 아닙니다.

정책이 적용될 Pod를 선택합니다.

```yaml
# 특정 레이블을 가진 Pod에 적용
spec:
  podSelector:
    matchLabels:
      app: api
      version: v1

---
# 모든 Pod에 적용 (빈 셀렉터)
spec:
  podSelector: {}

---
# matchExpressions 사용
spec:
  podSelector:
    matchExpressions:
      - key: app
        operator: In
        values:
          - api
          - web
      - key: environment
        operator: NotIn
        values:
          - development
```

### namespaceSelector

레이블로 네임스페이스를 선택하며 조건을 만족하면 현재 네임스페이스도 포함합니다. `name`은 자동 생성되는 네임스페이스 레이블이 아닙니다. 이름을 정확히 고르려면 기본 불변 레이블 `kubernetes.io/metadata.name`을 사용하고, 사용자 정의 테넌트 레이블 변경 권한도 제한합니다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-monitoring
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
  ingress:
    - from:
        # monitoring 네임스페이스의 모든 Pod 허용
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: monitoring
        # production 네임스페이스의 특정 Pod 허용
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: production
          podSelector:
            matchLabels:
              role: frontend
```

**주의:** `namespaceSelector`와 `podSelector`를 함께 사용할 때 AND vs OR 구분:

```yaml
# OR 조건 (두 개의 별도 peer 항목)
ingress:
  - from:
      - namespaceSelector:    # 규칙 1
          matchLabels:
            kubernetes.io/metadata.name: team-a
      - podSelector:          # 규칙 2
          matchLabels:
            role: frontend

---
# AND 조건 (하나의 규칙)
ingress:
  - from:
      - namespaceSelector:    # 두 조건 모두 충족해야 함
          matchLabels:
            kubernetes.io/metadata.name: team-a
        podSelector:
          matchLabels:
            role: frontend
```

### ipBlock

`ipBlock`은 해당 규칙에서 CIDR 중 `except` 범위를 제외해 허용합니다. 예외는 전역 deny가 아니므로 다른 정책이 다시 허용할 수 있습니다. Service·로드밸런서의 주소 변환으로 CNI에 보이는 주소가 달라질 수 있어 실제 경로를 확인해야 합니다. 문서 CIDR은 설명용이며 실제 운영 엔드포인트가 아닙니다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-external-traffic
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: public-api
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        # 외부 로드밸런서 IP 범위 허용
        - ipBlock:
            cidr: 10.0.0.0/8
        # 특정 외부 IP 허용
        - ipBlock:
            cidr: 203.0.113.0/24
  egress:
    - to:
        # 외부 API 서버 접근 허용
        - ipBlock:
            cidr: 0.0.0.0/0
            except:
              - 10.0.0.0/8      # 내부 네트워크 제외
              - 172.16.0.0/12
              - 192.168.0.0/16
      ports:
        - protocol: TCP
          port: 443
```

### ports

`endPort`는 숫자 시작 포트와 CNI의 포트 범위 지원이 필요합니다. 이름 있는 포트로 범위를 시작할 수 없으며 API 접수가 모든 플러그인의 집행을 입증하지 않습니다.

허용할 포트와 프로토콜을 지정합니다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: port-specific-policy
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: web
  policyTypes:
    - Ingress
  ingress:
    - ports:
        # 특정 포트
        - protocol: TCP
          port: 80
        - protocol: TCP
          port: 443
        # 포트 범위 (Kubernetes 1.25+)
        - protocol: TCP
          port: 8000
          endPort: 8080
        # Named 포트
        - protocol: TCP
          port: http
```

---

<span id="기본-거부-정책"></span>

## 기본 거부 정책 {#default-deny-policies}

빈 기준선은 허용 규칙을 제공하지 않지만 다른 선택 정책은 트래픽을 허용할 수 있습니다. 정책 변경 시 이미 연결된 세션 처리도 구현별로 달라 별도 시험이 필요합니다.

### Ingress 기본 거부

모든 인바운드 트래픽을 차단하는 기본 정책:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: production
spec:
  podSelector: {}  # 모든 Pod에 적용
  policyTypes:
    - Ingress
  # ingress 규칙이 없으면 모든 인바운드 트래픽 차단
```

### Egress 기본 거부

모든 아웃바운드 트래픽을 차단하는 기본 정책:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-egress
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Egress
  # egress 규칙이 없으면 모든 아웃바운드 트래픽 차단
```

### 전체 거부 (Ingress + Egress)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

### DNS 허용과 함께 기본 거부

`kube-system`의 `k8s-app=kube-dns` 레이블을 가진 **Pod 기반 CoreDNS**를 가정하고 TCP·UDP 53을 모두 허용합니다. DNS Pod에도 ingress 격리가 있으면 클라이언트를 허용해야 합니다. NodeLocal DNSCache와 Auto Mode의 노드 로컬 CoreDNS는 실제 resolver 경로·IP에 맞는 별도 프로파일이 필요하므로 이 Pod 셀렉터를 그대로 쓰지 않습니다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-egress-allow-dns
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Egress
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

### Zero Trust 아키텍처 기본 정책

frontend→API의 출발지 egress·목적지 ingress를 모두 포함합니다. frontend 외부 유입이나 API→DB까지 허용하는 것은 아니므로 검토한 경로만 추가합니다. 앞의 Pod 기반 DNS 가정을 사용합니다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: zero-trust-default
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress: []
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Egress
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
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-api
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-api-egress
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 8080
```

<span id="정책-순서-및-평가"></span>

## 정책 순서 및 평가 {#policy-order-and-evaluation}

다음 흐름은 엔드포인트·방향별 **Kubernetes NetworkPolicy** 허용 규칙에 한정됩니다. 출발지 egress와 목적지 ingress 및 다른 네트워크 제어를 함께 확인합니다. Ingress 전용 정책은 egress를 격리하지 않습니다. 합집합 규칙을 Calico tier, Cilium deny, AWS 관리 정책에 일반화하지 않습니다.

### 정책 평가 규칙

NetworkPolicy는 다음 규칙에 따라 평가됩니다:

```
┌─────────────────────────────────────────────────────────────────┐
│                  NetworkPolicy 평가 흐름                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Pod에 적용되는 정책이 있는가?                                 │
│     │                                                           │
│     ├─ 없음 → 모든 트래픽 허용 (기본 동작)                        │
│     │                                                           │
│     └─ 있음 → 정책 평가 시작                                     │
│              │                                                  │
│              ▼                                                  │
│  2. 해당 방향(Ingress/Egress)의 정책이 있는가?                    │
│     │                                                           │
│     ├─ 없음 → 해당 방향 트래픽 허용                               │
│     │                                                           │
│     └─ 있음 → 규칙 매칭 시작                                     │
│              │                                                  │
│              ▼                                                  │
│  3. 트래픽이 하나 이상의 규칙과 매칭되는가?                        │
│     │                                                           │
│     ├─ 매칭됨 → 트래픽 허용                                      │
│     │                                                           │
│     └─ 매칭 안됨 → 트래픽 차단                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 여러 정책의 조합

여러 NetworkPolicy가 동일한 Pod에 적용될 때, 모든 정책의 규칙이 합쳐집니다 (Union):

```yaml
---
# 정책 1: frontend에서 오는 트래픽 허용
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
---
# 정책 2: monitoring에서 오는 트래픽 허용
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-monitoring
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: monitoring
      ports:
        - protocol: TCP
          port: 8080
        - protocol: TCP
          port: 9090
```

**결과:** `app: api` Pod는 frontend Pod의 8080 접근과 monitoring 네임스페이스의 8080, 9090 접근 모두 허용됩니다.

### 정책 평가 순서

NetworkPolicy에는 우선순위 개념이 없습니다. 모든 정책은 동등하게 처리됩니다:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   Policy A    Policy B    Policy C                              │
│   (allow X)   (allow Y)   (allow Z)                             │
│       │           │           │                                 │
│       └───────────┼───────────┘                                 │
│                   │                                             │
│                   ▼                                             │
│           ┌───────────────┐                                     │
│           │   합집합      │                                     │
│           │ (X OR Y OR Z) │                                     │
│           └───────────────┘                                     │
│                   │                                             │
│                   ▼                                             │
│           최종 허용 트래픽:                                      │
│           X, Y, Z 모두 허용                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

<span id="cilium-네트워크-정책-확장"></span>

## Cilium 네트워크 정책 확장 {#cilium-network-policy-extensions}

예제는 릴리스된 Cilium 1.20.1 정책 스키마 기준이며 모든 클러스터의 업그레이드 지시가 아닙니다. HTTP 규칙에는 지원되는 L7 proxy 경로가 필요합니다. AWS VPC CNI chaining에는 L7 정책 등 고급 기능의 제한이 문서화되어 있으므로 이 HTTP 예제가 그대로 동작한다고 가정하지 않습니다. 숫자 security identity는 레이블 집합에 할당된 값이며 영구 앱 ID가 아닙니다.

### CiliumNetworkPolicy

Cilium은 기본 NetworkPolicy를 확장하여 더 강력한 기능을 제공합니다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: cilium-l7-policy
  namespace: production
spec:
  # 엔드포인트 선택
  endpointSelector:
    matchLabels:
      app: api

  # L3/L4 규칙 (기본 NetworkPolicy와 유사)
  ingress:
    - fromEndpoints:
        - matchLabels:
            app: frontend
      toPorts:
        - ports:
            - port: "8080"
              protocol: TCP
          # L7 규칙 (Cilium 확장)
          rules:
            http:
              - method: GET
                path: "/api/v1/.*"
              - method: POST
                path: "/api/v1/users"
                headers:
                  - 'Content-Type: application/json'
```

### L7 HTTP 정책

Cilium HTTP 규칙은 L7 프록시가 볼 수 있는 요청을 필터링하며 API key 인증이나 관리자 권한 부여를 수행하지 않습니다. 호출자가 `X-User-Role` 헤더를 직접 넣을 수 있습니다. 아래 예제는 메서드·경로와 정확한 `Content-Type`만 제한합니다. 인증·인가는 애플리케이션 또는 인증된 gateway에서 수행합니다. 종단 간 TLS를 자동 복호화하여 HTTP를 검사하는 것도 아닙니다. 같은 트래픽을 L4에서 허용하는 다른 정책도 검토합니다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: http-api-policy
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      app: api-server
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: web-frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: GET
          path: /api/v1/products
        - method: GET
          path: /api/v1/products/[0-9]+
        - method: POST
          path: /api/v1/orders
          headerMatches:
          - name: Content-Type
            value: application/json
```

[HTTP API — Cilium 1.20.1](https://github.com/cilium/cilium/blob/v1.20.1/pkg/policy/api/http.go)

### L7 Kafka 정책

배포된 Cilium 1.20.1 CNP 스키마는 HTTP·DNS L7 규칙을 지원하지만 `rules.kafka`는 없습니다. 기존 `role`·`topic`·`clientID` 예제는 현재 배포 가능한 API가 아닙니다. 네트워크 정책으로 broker 연결을 제한하고 `orders`·`events` 토픽의 producer/consumer 권한은 Kafka 인증과 ACL로 구성합니다. client ID 자체는 인증된 주체가 아닙니다.

다음 L4 예제는 TCP 9093 TLS broker listener가 이미 구성되어 있고, 같은 네임스페이스 client의 egress·DNS가 별도로 허용됐다고 가정합니다. TLS·broker ACL·토픽 권한을 구성하지는 않습니다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: kafka-client-network-access
  namespace: data
spec:
  endpointSelector:
    matchLabels:
      app: kafka
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: producer
    - matchLabels:
        app: consumer
    toPorts:
    - ports:
      - port: '9093'
        protocol: TCP
```

[CNP schema — Cilium 1.20.1](https://github.com/cilium/cilium/blob/v1.20.1/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnetworkpolicies.yaml)

### L7 DNS 정책

Pod 기반 CoreDNS 예제이며 53번 포트의 `ANY`는 UDP·TCP를 포함합니다. DNS 질의 허용과 응답 IP 연결 허용은 별도이므로 아래 DB 이름을 조회해도 DB 연결이 허용되지는 않습니다. 예시 도메인을 바꾸고 검색 접미사·캐시·TTL 및 실제 resolver 프로파일을 확인합니다. FQDN 규칙은 DNS에서 IP를 학습하며 SaaS 테넌트 인증이나 TLS·앱 권한 확인을 대신하지 않습니다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: dns-policy
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      app: web
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: ANY
      rules:
        dns:
        - matchName: api.example.com
        - matchName: database.production.svc.cluster.local
  - toFQDNs:
    - matchName: api.example.com
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

### CiliumClusterwideNetworkPolicy

리소스는 클러스터 범위지만 셀렉터는 `production/app=api`로 제한합니다. gateway Pod의 TCP8080을 허용하는 ingress 전용 예제입니다. egress 격리·DNS와 gateway 자신의 egress에는 해당 정책이 필요합니다. 기존 전체 엔드포인트 cluster/world 허용 예제는 default-deny 정책이 아니었습니다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: production-api-from-edge
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: production
      app: api
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: gateway-system
        app: edge-proxy
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
```

### Cilium 엔티티 기반 정책

`host`는 로컬 노드와 해당 노드의 host-network 컨테이너를 포함하며 `cluster`도 일반 앱 Pod보다 넓습니다. `world`는 클러스터 밖 엔드포인트이며 세밀한 Internet·SaaS 허용 목록이 아닙니다. 외부 접근은 필요한 CIDR·FQDN으로 좁힙니다. 다음은 레이블을 붙인 Kubernetes API 클라이언트의 TCP443만 허용하며 실제 API 주소·TLS 신뢰·자격 증명·RBAC는 별도입니다. 관리형 컨트롤 플레인 경로에서 출발지 identity가 달라질 수 있어 실제 flow identity를 확인합니다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: kubernetes-api-client
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      app: kubernetes-api-client
  egress:
  - toEntities:
    - kube-apiserver
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

<span id="calico-네트워크-정책-확장"></span>

## Calico 네트워크 정책 확장 {#calico-network-policy-extensions}

정책·Tier 예제는 Calico Open Source3.32.2 리소스 기준입니다. `projectcalico.org/v3`는 지원 Calico API server 또는 일치하는 `calicoctl` 절차가 필요하며 Kubernetes의 원시 저장 CRD `crd.projectcalico.org/v1`과 구분합니다. 적용 전 설치된 datastore·API를 확인합니다. Calico의 순서 있는 action·tier 위임은 Kubernetes NetworkPolicy의 허용 합집합과 다릅니다.

현재 Open Source 문서에도 [Istio/Dikastes 애플리케이션 계층 통합](https://docs.tigera.io/calico/latest/network-policy/istio/app-layer-policy)이 있습니다. HTTPMatch API는 별도 구성이 필요하며 ingress Allow 규칙을 지원합니다. 아래 Calico 예제는 L3/L4 정책에 한정하며 L7 통합은 배포·시험하지 않았습니다.

### Calico NetworkPolicy

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: calico-policy
  namespace: production
spec:
  # 정책 순서 (낮을수록 먼저 평가)
  order: 100

  selector: app == 'api'

  types:
    - Ingress
    - Egress

  ingress:
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'frontend'
      destination:
        ports:
          - 8080

  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: app == 'database'
        ports:
          - 5432
```

### GlobalNetworkPolicy

다음 전역 리소스는 `production` 네임스페이스의 워크로드만 선택합니다. 범위를 제한하지 않은 `selector: all()`은 host endpoint에도 영향을 줄 수 있어 명시적 범위·복구 경로 없이 전역 deny를 적용하지 않습니다. 같은 tier에서는 낮은 `order`를 먼저 평가합니다. 예제는 Pod 기반 DNS와 deny 기준선을 제공하며 필요한 앱 경로·상위 tier action을 함께 검토해야 합니다.

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: production-default-deny
spec:
  namespaceSelector: projectcalico.org/name == 'production'
  selector: all()
  order: 1000
  types:
  - Ingress
  - Egress
  ingress: []
  egress: []
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: production-allow-dns
spec:
  namespaceSelector: projectcalico.org/name == 'production'
  selector: all()
  order: 100
  types:
  - Egress
  egress:
  - action: Allow
    protocol: UDP
    destination:
      selector: k8s-app == 'kube-dns'
      namespaceSelector: projectcalico.org/name == 'kube-system'
      ports:
      - 53
  - action: Allow
    protocol: TCP
    destination:
      selector: k8s-app == 'kube-dns'
      namespaceSelector: projectcalico.org/name == 'kube-system'
      ports:
      - 53
```

### NetworkSet

NetworkSet 셀렉터는 리소스 이름이 아니라 `metadata.labels`를 선택합니다. 첫 집합은 네임스페이스 범위이며 전역 차단 집합은 다음 security tier 예제에서 사용합니다. CIDR은 모두 문서용 대역이므로 검토한 목적지로 바꿉니다. egress 예제는 레이블을 가진 집합의 TCP443만 허용하며 DNS는 별도 규칙입니다.

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkSet
metadata:
  name: external-apis
  namespace: production
  labels:
    network-role: external-api
spec:
  nets:
  - 203.0.113.0/24
  - 198.51.100.10/32
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkSet
metadata:
  name: blocked-ips
  labels:
    network-role: blocked
spec:
  nets:
  - 192.0.2.0/24
---
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: allow-external-apis
  namespace: production
spec:
  selector: app == 'web'
  types:
  - Egress
  egress:
  - action: Allow
    protocol: TCP
    destination:
      selector: network-role == 'external-api'
      ports:
      - 443
```

### Tier 기반 정책

참조한 Calico Open Source 릴리스도 Tier를 지원합니다. 선택된 tier에서 규칙이 결정을 내리지 않으면 기본 action은 `Deny`입니다. 알려진 위협만 막는 tier는 `defaultAction: Pass`를 명시해 나머지 트래픽을 다음 정책으로 넘깁니다. `Pass`는 허용이 아닌 위임입니다. `global()`은 `namespaceSelector`에 쓰고 별도 레이블 셀렉터로 GlobalNetworkSet을 고릅니다. 배포 전 application tier 정책과 최종 profile/default tier 동작을 확인해야 하며 빈 Tier 생성만으로 앱 격리가 완성되지는 않습니다.

```yaml
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: security
spec:
  order: 100
  defaultAction: Pass
---
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: platform
spec:
  order: 200
  defaultAction: Pass
---
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: application
spec:
  order: 300
  defaultAction: Deny
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: security.block-known-threats
spec:
  tier: security
  order: 100
  selector: all()
  namespaceSelector: projectcalico.org/name == 'production'
  types:
  - Ingress
  ingress:
  - action: Deny
    source:
      selector: network-role == 'blocked'
      namespaceSelector: global()
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: platform.allow-dns
spec:
  tier: platform
  order: 100
  selector: all()
  namespaceSelector: projectcalico.org/name == 'production'
  types:
  - Egress
  egress:
  - action: Allow
    protocol: UDP
    destination:
      selector: k8s-app == 'kube-dns'
      namespaceSelector: projectcalico.org/name == 'kube-system'
      ports:
      - 53
  - action: Allow
    protocol: TCP
    destination:
      selector: k8s-app == 'kube-dns'
      namespaceSelector: projectcalico.org/name == 'kube-system'
      ports:
      - 53
```

<span id="설계-패턴"></span>

## 설계 패턴 {#design-patterns}

각 예제는 **서로 다른 정책 프로파일**이며 한꺼번에 적용할 묶음이 아닙니다. 같은 `production`을 사용해도 별도 예제의 허용 규칙은 누적됩니다. 네임스페이스·워크로드 레이블·실제 수신 포트·DNS 프로파일을 먼저 준비합니다. 로컬 스키마·정책 의도만 확인했으며 실제 클러스터 연결 시험은 수행하지 않았습니다.

### 마이크로세그멘테이션

frontend→API TCP8080, API→DB TCP5432를 양쪽에서 허용하고 DNS를 추가합니다. Internet egress나 frontend 외부 유입은 허용하지 않습니다. 필요하면 승인된 목적지 CIDR·포트 또는 인증된 egress gateway 프로파일을 추가합니다. 0.0.0.0/0에서 RFC1918만 제외하는 것은 SaaS 허용 목록이 아닙니다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress: []
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Egress
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
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-api-egress
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-to-api
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-to-database
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-from-api
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: database
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 5432
```

### 네임스페이스 격리

같은 팀 ingress·egress와 DNS를 모두 포함합니다. 공유 서비스 목적지에도 team-a ingress 허용과 실제 TLS443 수신기가 필요합니다. 네임스페이스 레이블 관리 권한을 제한해야 하며 팀 레이블만으로 신뢰 경계가 생기지는 않습니다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
  labels:
    team: team-a
    environment: production
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-same-team
  namespace: team-a
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - &id001
      namespaceSelector:
        matchLabels:
          team: team-a
  egress:
  - to:
    - *id001
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
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-shared-services
  namespace: team-a
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          shared-services: 'true'
      podSelector:
        matchLabels:
          exposed: 'true'
    ports:
    - protocol: TCP
      port: 443
```

### 데이터베이스 보호

`database` 네임스페이스가 있어야 합니다. 운영 앱·모니터링 Pod의 egress 허용은 별도로 필요합니다. 동료 Pod의 TCP5432는 가정한 PostgreSQL 복제 전송만 허용하며 DB 인증·TLS를 구성하지 않습니다. TCP9187은 별도 exporter가 설치되어 있다고 가정합니다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-protection
  namespace: database
spec:
  podSelector:
    matchLabels:
      app: postgresql
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          environment: production
      podSelector:
        matchLabels:
          database-access: 'true'
    ports:
    - protocol: TCP
      port: 5432
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: monitoring
      podSelector:
        matchLabels:
          app: prometheus
    ports:
    - protocol: TCP
      port: 9187
  - from:
    - podSelector:
        matchLabels:
          app: postgresql
    ports:
    - protocol: TCP
      port: 5432
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgresql
    ports:
    - protocol: TCP
      port: 5432
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

### 3-Tier 아키텍처 정책

기존 `gateway-system/app=edge-proxy`가 클라이언트 TLS를 종료하고 web Pod의 TCP80에 접근하는 프로파일입니다. gateway egress는 이 네임스페이스 밖에서 허용해야 합니다. data 동료 ingress·egress는 TCP5432/6379이며 실제 DB의 추가 복제·cluster-bus·백업 포트까지 보장하지 않습니다. 운영에서는 PostgreSQL·Redis 셀렉터를 분리합니다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: three-tier-default-deny
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress: []
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: web-tier-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      tier: web
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: gateway-system
      podSelector:
        matchLabels:
          app: edge-proxy
    ports:
    - protocol: TCP
      port: 80
  egress:
  - to:
    - podSelector:
        matchLabels:
          tier: app
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: app-tier-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      tier: app
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          tier: web
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector:
        matchLabels:
          tier: data
    ports:
    - protocol: TCP
      port: 5432
    - protocol: TCP
      port: 6379
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: data-tier-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      tier: data
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          tier: app
    ports:
    - protocol: TCP
      port: 5432
    - protocol: TCP
      port: 6379
  - from:
    - podSelector:
        matchLabels:
          tier: data
    ports:
    - protocol: TCP
      port: 5432
    - protocol: TCP
      port: 6379
  egress:
  - to:
    - podSelector:
        matchLabels:
          tier: data
    ports:
    - protocol: TCP
      port: 5432
    - protocol: TCP
      port: 6379
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: three-tier-dns
  namespace: production
spec:
  podSelector:
    matchExpressions:
    - key: tier
      operator: In
      values:
      - web
      - app
      - data
  policyTypes:
  - Egress
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

---

<span id="네트워크-정책-테스트"></span>

## 네트워크 정책 테스트 {#testing-network-policies}

### netshoot을 사용한 테스트

고정 이미지·권한을 검토해 이미 준비한 진단 Pod를 사용합니다. 실제 정책을 시험하는 출발지 레이블·네임스페이스·노드 배치를 선택해야 하며 임의의 레이블 없는 Pod는 앱을 대신하지 못합니다. netshoot 배포는 워크로드 생성이며 Pod Security admission과 충돌할 수 있습니다. 관측 스크립트에서 공유된 고정 이름 `test-pod`를 만들거나 삭제하지 않고 소유한 테스트 엔드포인트만 검사합니다.

### kubectl exec을 사용한 테스트

컨텍스트·네임스페이스·기존 Pod·컨테이너를 명시합니다. DNS 성공이 TCP 성공은 아니며 연결 거부·수신기 장애·TLS 오류·정책 drop을 구분합니다. 다음은 응답 본문을 출력하지 않는 연결 확인이며 이번 검토에서는 실제 클러스터에 실행하지 않았습니다.

```bash
# Both Pods already exist in the approved test environment.
kubectl --context="$CONTEXT" -n "$NAMESPACE" get pods --show-labels
kubectl --context="$CONTEXT" -n "$NAMESPACE" exec "$ALLOW_POD" \
  -c "$PROBE_CONTAINER" -- nslookup api-service.production.svc.cluster.local
kubectl --context="$CONTEXT" -n "$NAMESPACE" exec "$ALLOW_POD" \
  -c "$PROBE_CONTAINER" -- curl --silent --show-error --output /dev/null \
  --connect-timeout 3 --max-time 5 http://api-service.production.svc.cluster.local:8080/health
```

### Cilium Connectivity Test

`cilium connectivity test`는 테스트 리소스와 트래픽을 생성하며 읽기 전용 상태 조회가 아닙니다. 승인된 격리 클러스터·네임스페이스, 호환 CLI·이미지, 지정 외부 목적지와 정리 계획을 사용합니다. 과거 테스트 이름을 가정하지 말고 설치된 CLI의 `cilium connectivity test --help`로 필터를 확인합니다. 통과해도 모든 앱 정책이나 CNI chaining 기능이 검증되는 것은 아닙니다.

### 자동화된 테스트 스크립트

이 스크립트는 기존 Pod 두 개에서 제한 시간 있는 curl만 실행하며 클러스터 리소스를 생성·삭제하지 않습니다. `CONTEXT`, `NAMESPACE`, `ALLOW_POD`, `DENIED_POD`, `PROBE_CONTAINER`와 민감 정보 없는 `/health` URL인 `TARGET_URL`을 설정합니다. 양쪽 컨테이너에 `sh`·`curl`이 있어야 하고 첫 Pod는 같은 목적지에 허용된 양성 대조군입니다. 앱 상태 검사가 아니므로 HTTP 오류 응답도 네트워크 도달을 의미합니다.

종료1은 차단 대상의 예상 밖 연결, 종료2는 오류/판정 불가, 종료3은 추가 근거가 필요한 timeout입니다. timeout을 자동 PASS로 처리하지 않습니다. 동일 출발지·목적지·포트·시각의 CNI 정책 drop과 대조하고 엔드포인트 상태·라우팅·SG/NACL도 확인합니다. 로컬 mock 시험은 실제 정책 집행 검증이 아닙니다.

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${CONTEXT:?Set an approved kubectl context}"
: "${NAMESPACE:?Set the test namespace}"
: "${ALLOW_POD:?Set an existing positive-control Pod}"
: "${DENIED_POD:?Set a different existing policy-subject Pod}"
: "${PROBE_CONTAINER:?Set a container with sh and curl in both Pods}"
: "${TARGET_URL:?Set the same non-secret health URL for both probes}"
if [[ "$ALLOW_POD" == "$DENIED_POD" ||
      ! "$TARGET_URL" =~ ^https?://[A-Za-z0-9.-]+(:[0-9]+)?/health$ ]]; then
  echo "Invalid probe inputs: use different Pods and a plain /health URL." >&2
  exit 2
fi
work=$(mktemp -d "${TMPDIR:-/tmp}/network-policy-probe.XXXXXX")
trap 'rm -rf -- "$work"' EXIT
probe() {
  local pod=$1 result
  if ! result=$(kubectl --context="$CONTEXT" --request-timeout=15s \
      -n "$NAMESPACE" exec "$pod" -c "$PROBE_CONTAINER" -- \
      sh -c 'rc=0
        curl --silent --output /dev/null --connect-timeout 3 --max-time 5 "$1" || rc=$?
        printf "PROBE_EXIT=%s\n" "$rc"' sh "$TARGET_URL" \
      2>"$work/transport-error"); then
    echo "UNKNOWN: kubectl exec/authorization/transport failed." >&2
    return 2
  fi
  if [[ ! "$result" =~ ^PROBE_EXIT=([0-9]+)$ ]]; then
    echo "UNKNOWN: missing or malformed remote probe result." >&2
    return 2
  fi
  printf '%s\n' "${BASH_REMATCH[1]}"
}
allowed=$(probe "$ALLOW_POD") || exit 2
if [[ "$allowed" != 0 ]]; then
  echo "UNKNOWN: positive control could not reach the target." >&2
  exit 2
fi
denied=$(probe "$DENIED_POD") || exit 2
case "$denied" in
  0) echo "FAIL: the intended blocked Pod reached the target."; exit 1 ;;
  28) echo "INCONCLUSIVE: timeout; correlate an actual policy-drop verdict."; exit 3 ;;
  *) echo "UNKNOWN: DNS/TLS/refused/tool error is not proof of a policy drop."; exit 2 ;;
esac
```

<span id="eks-고려사항"></span>

## EKS 고려사항 {#eks-considerations}

### Amazon VPC CNI와 NetworkPolicy

Amazon VPC CNI는 활성화 후 네트워크 정책을 지원합니다. 현재 AWS 가이드는 표준·관리자 정책을 함께 사용할 때 VPC CNI 1.21 이상, 호환 EKS 플랫폼과 Linux kernel 5.10 이상을 요구합니다. 지원되는 EC2 Linux 노드에 적용되며 Fargate·Windows에는 적용되지 않습니다. 현재 지원되는 EKS 버전과 호환 add-on을 확인하고 upstream Kubernetes 릴리스로 EKS 지원 여부를 추정하지 않습니다.

**EKS 관리형** VPC CNI add-on은 기존 설정을 보존하면서 문서의 문자열 `"enableNetworkPolicy": "true"`를 설정합니다. 아래 명령은 검토 후 선택한 클러스터를 변경하지만 add-on 버전을 올리지는 않습니다. 설치 버전이 호환되지 않으면 중단하고 공식 업그레이드 절차를 먼저 따릅니다.

```bash
# Requires AWS CLI, kubectl and jq; use an approved test cluster.
set -euo pipefail
: "${CLUSTER_NAME:?Set the approved test-cluster name}"
umask 077
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni   --output json > vpc-cni-before.json
jq -e '(.addon.configurationValues // "{}") | if . == "" then {} else fromjson end
  | .enableNetworkPolicy = "true"' vpc-cni-before.json > vpc-cni-network-policy.json
# Review the saved current version/configuration and the complete merged JSON first.
aws eks update-addon --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni   --configuration-values file://vpc-cni-network-policy.json --resolve-conflicts PRESERVE
```

업데이트 상태와 정책 동작을 확인한 뒤 확대 적용합니다. `--resolve-conflicts PRESERVE`가 교체 JSON 문서를 자동 병합하는 것은 아니므로 예제에서 기존 값을 명시적으로 보존합니다. 복구용 스냅샷도 유지합니다. Helm이 소유한 설치는 검토한 chart/values의 `enableNetworkPolicy: true`를 사용하며 위 관리형 add-on 명령으로 소유권을 바꾸지 않습니다. `ENABLE_NETWORK_POLICY` 환경 변수 설정은 실제 활성화 절차가 아닙니다.

Standard 시작 모드는 새 Pod에 정책이 프로그래밍될 때까지 일시적으로 허용할 수 있습니다. `NETWORK_POLICY_ENFORCING_MODE=strict`는 해당 Pod를 거부 상태로 시작하므로 DNS를 포함한 완전한 허용 규칙이 필요하며 변경 시 워크로드를 중단시킬 수 있습니다. 테스트는 controller가 관리하는 Pod를 대상으로 합니다. 정책은 주 Pod 인터페이스에 적용되므로 추가 인터페이스·IPv6에서 IPv4로 나가는 경로·host networking·NAT는 별도로 검토합니다. 같은 표준 정책을 두 엔진이 관리하게 하거나 이전 편의를 위해 `aws-node`를 삭제하지 않습니다.

### EKS Enhanced Network Security Policies (2025년 12월)

> **발표일**: 2025년 12월 15일 · [출처](https://aws.amazon.com/ko/about-aws/whats-new/2025/12/amazon-eks-enhanced-network-security-policies/)

실제 제공되는 기능이지만 리소스 API 그룹은 **`networking.k8s.aws/v1alpha1`**입니다. 클러스터 범위 `ClusterNetworkPolicy`는 `tier`가 필수이며, 아래 네임스페이스 DNS egress 예제는 `ApplicationNetworkPolicy`를 사용합니다. EC2 Linux의 표준·관리자 VPC CNI 정책 지원을 모든 compute mode 지원으로 확대 해석하면 안 됩니다. DNS 규칙은 혼합 클러스터에서도 **Auto Mode가 시작한 EC2 인스턴스**에서만 적용됩니다.

**Auto Mode 선행 조건:** 아래 정책을 적용하기 전에 Auto Mode Network Policy Controller를 활성화해야 합니다. EKS 관리형 `vpc-cni` add-on 갱신은 별도 경로이며 순수 Auto Mode 클러스터의 정책 집행을 활성화하지 않습니다. 필요한 설정은 ConfigMap `kube-system/amazon-vpc-cni`의 `data.enable-network-policy-controller: "true"`입니다. 아래 절차는 기존 data를 merge patch로 보존하고 객체가 없을 때만 생성하며 읽기·쓰기 실패 시 중단합니다. 실행 전 cluster context와 기존 설정을 검토하세요.

```bash
set -euo pipefail
config="$(kubectl get configmap amazon-vpc-cni -n kube-system --ignore-not-found -o name)"
if [ -n "$config" ]; then
  kubectl patch configmap amazon-vpc-cni -n kube-system --type merge \
    -p '{"data":{"enable-network-policy-controller":"true"}}'
else
  kubectl create configmap amazon-vpc-cni -n kube-system \
    --from-literal=enable-network-policy-controller=true
fi
kubectl get configmap amazon-vpc-cni -n kube-system -o json \
  | jq -e '.data["enable-network-policy-controller"] == "true"'
```

활성화 후 해당 `PolicyEndpoints` 객체를 확인하고 선택한 Auto Mode 노드에서 허용·차단 트래픽을 모두 검증합니다. 설정값 저장이나 정책 객체 생성 성공만으로 실제 집행을 보장할 수 없습니다. [Auto Mode network policy 설정](https://docs.aws.amazon.com/eks/latest/userguide/auto-net-pol.html)을 따르세요. 이번 문서 감사에서는 실제 클러스터 집행 시험을 수행하지 않았습니다.

다음 Admin tier 예제는 namespace selector로 선택한 Pod에서 `isolated-demo`로 들어오는 통신을 거부하며, 같은 네임스페이스의 Pod도 포함합니다. 외부·host-network까지 포함하는 완전한 방화벽이나 DNS 허용 정책이 아닙니다. Admin Deny는 네임스페이스 NetworkPolicy가 덮어쓸 수 없습니다. 다른 action을 추가하기 전에 실제 설치 CRD를 확인합니다. 현재 AWS upstream controller 스키마는 허용 action을 `Accept`로 정의하지만 user guide 설명은 “Allow”라고 표현합니다.

```yaml
apiVersion: networking.k8s.aws/v1alpha1
kind: ClusterNetworkPolicy
metadata:
  name: isolate-demo-namespace
spec:
  tier: Admin
  priority: 10
  subject:
    namespaces:
      matchLabels:
        kubernetes.io/metadata.name: isolated-demo
  ingress:
  - name: deny-pod-ingress
    action: Deny
    from:
    - namespaces:
        matchLabels: {}
```

FQDN 예제는 `production`의 `app=backend`를 선택합니다. **`10.100.0.10/32`를 실제 클러스터 Auto Mode CoreDNS IP로 교체**합니다. Service CIDR의 network address에 10을 더한 주소이며 IPv6는 `::a/128`에 해당합니다. Pure Auto Mode의 CoreDNS는 노드에서 실행되므로 일반 CoreDNS Pod selector로 대체할 수 없습니다. TCP·UDP DNS를 모두 허용하고 같은 네임스페이스의 NetworkPolicy와 리소스 이름이 충돌하지 않게 합니다.

```yaml
apiVersion: networking.k8s.aws/v1alpha1
kind: ApplicationNetworkPolicy
metadata:
  name: approved-api-egress
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Egress
  egress:
  - to:
    - ipBlock:
        cidr: 10.100.0.10/32
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
  - to:
    - domainNames:
      - api.stripe.com
    ports:
    - protocol: TCP
      port: 443
```

DNS 프록시는 허용한 질의의 응답 IP와 TTL을 관찰하고 data path에서 학습한 목적지 IP·포트를 허용합니다. SaaS 계정 인증이나 HTTP 서버 신원 확인을 대신하지 않으므로 공유 IP·DNS 동작을 시험해야 합니다. TLS 인증서 검증, 애플리케이션 인가, 라우팅과 Route 53 DNS Firewall 규칙도 필요합니다. 다른 적용 정책과 backend 직접 접근 경로를 함께 검토합니다.

[AWS NetworkPolicy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html) · [Configuration](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html) · [Auto Mode policies](https://docs.aws.amazon.com/eks/latest/userguide/auto-net-pol.html)

### Security Groups for Pods

다음 바인딩은 EKS VPC Resource Controller와 **클러스터 역할** 권한, trunking 지원 EC2 Linux 노드 및 검토한 VPC CNI 구성을 가정합니다. 현재 AWS 문서는 Windows·EKS Auto Mode를 제외합니다. Fargate의 Pod SG 방식은 별도이며 보안 그룹이 있다고 VPC CNI NetworkPolicy 집행까지 제공되는 것은 아닙니다. 워크로드 소유자를 통해 새로 생성되는 일치 Pod에 적용하며 기존 Pod가 자동 변경되지는 않습니다.

Calico와 Pod SG 조합에는 AWS가 VPC CNI1.11.0 이상과 `POD_SECURITY_GROUP_ENFORCING_MODE=standard`를 명시합니다. 이 최소값을 권장 버전으로 고정하지 말고 현재 CNI 요건도 만족시킵니다. standard 모드의 외부 SNAT 경로는 Pod SG 대신 노드 SG를 사용할 수 있어 실제 경로를 확인합니다. 기존의 자격 증명·스토리지 없는 PostgreSQL Pod는 완성된 DB 배포 예제가 아니었습니다.

```yaml
# Binding example only: use an existing reviewed security group.
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: database-sg-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: database
  securityGroups:
    groupIds:
      - sg-0123456789abcdef0
```

Terraform 조각은 검토한 앱 SG의 DB ingress만 허용하고 새 egress 연결은 허용하지 않습니다. 기존 연결 응답은 SG의 stateful 처리로 허용되며 필요한 DNS·복제·백업·외부 egress만 별도로 추가합니다. 변수는 기존 운영자 입력이며 plan/apply를 실행하지 않았습니다.

```hcl
# Fragment for an existing reviewed Terraform configuration.
# Supply the actual VPC and application SG; this is not a standalone module.
resource "aws_security_group" "database_pods" {
  name_prefix = "database-pods-"
  vpc_id      = var.vpc_id
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.application_security_group_id]
  }
  egress = []
}
```

### VPC 레벨 제어와 NetworkPolicy 조합

NetworkPolicy·실제로 적용되는 SG·NACL이 해당 경로를 모두 허용해야 합니다. ingress 전용 정책은 DB egress를 제한하지 않으므로 선택한 egress 프로파일과 출발지 Pod egress를 별도로 구성합니다. 여러 SG의 허용 규칙은 합쳐집니다. NACL은 **stateless**이므로 inbound5432 외에도 클라이언트 임시 포트로의 응답 경로와 클라이언트 서브넷 규칙이 필요합니다. 다음 조각은 전체 ACL 규칙 검토를 대신하지 않습니다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: database
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              database-access: "true"
      ports:
        - protocol: TCP
          port: 5432
```

```hcl
# Fragments for a DB subnet NACL and an explicitly reviewed client CIDR.
# Choose the client's actual ephemeral port range; also review its subnet NACL.
resource "aws_network_acl_rule" "database_inbound" {
  network_acl_id = var.database_network_acl_id
  rule_number    = 100
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.application_subnet_cidr
  from_port      = 5432
  to_port        = 5432
}
resource "aws_network_acl_rule" "database_return" {
  network_acl_id = var.database_network_acl_id
  rule_number    = 100
  egress         = true
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.application_subnet_cidr
  from_port      = var.client_ephemeral_port_start
  to_port        = var.client_ephemeral_port_end
}
```

### EKS에서 Cilium 사용

**AWS VPC CNI chaining**과 별도 설계가 필요한 전체 CNI/IPAM 이전을 구분합니다. chaining에서는 AWS VPC CNI가 ENI/IPAM을 유지하고 Cilium이 datapath를 연결하므로 `aws-node`를 삭제하지 않습니다. 기존 애드온/Helm 소유자와 정책 집행 엔진의 중복을 검토합니다. 기존 Pod에는 chaining 정책이 자동 적용되지 않아 중단·롤백 계획에 따른 재생성이 필요합니다.

공식1.20.1 chaining 가이드의 values에는 L7/IPsec 제한도 함께 적용됩니다. 문서의 오래된 예시 출력이 현재 EKS 검증 결과는 아닙니다. 차트 저장소·패키지 출처를 확인하고 먼저 렌더링합니다:

```bash
# Render locally after verifying the official chart/package provenance.
# Rendering alone does not change a cluster or validate a migration.
helm template cilium cilium/cilium --version 1.20.1 \
  --namespace kube-system \
  --set cni.chainingMode=aws-cni \
  --set cni.exclusive=false \
  --set enableIPv4Masquerade=false \
  --set routingMode=native > cilium-reviewed.yaml
```

[AWS VPC CNI chaining — Cilium 1.20.1](https://docs.cilium.io/en/stable/installation/cni-chaining-aws-cni/)

<span id="시각화-도구"></span>

## 시각화 도구 {#visualization-tools}

### Cilium Network Policy Editor

정책 editor는 정책 작성을 돕고 **Hubble UI는 관측된 서비스 flow를 시각화**하므로 역할이 다릅니다. Hubble/UI 활성화는 클러스터 변경이며 설치 소유자가 관리합니다. 인증과 접근 제어를 갖춘 기존 Hubble 서비스라면 서비스 설정을 확인한 뒤 로컬 port-forward를 사용합니다. 디버깅을 위해 UI를 공개하지 않습니다.

```bash
kubectl --context="$CONTEXT" -n kube-system port-forward --address=127.0.0.1 svc/hubble-ui 12000:80
```

### Cilium Policy Verdict 확인

인증된 Hubble 연결을 사용합니다. `DROPPED`에는 정책 외 원인도 포함하므로 drop reason·엔드포인트 identity·시각·방향을 확인합니다. 한 지점의 `FORWARDED`가 전체 경로 전달을 보장하지는 않습니다.


```bash
# 관측된 정책 결정 확인
hubble observe --verdict DROPPED
hubble observe --verdict FORWARDED

# 특정 Pod의 트래픽 확인
hubble observe --pod production/api-server

# JSON 형식으로 출력
hubble observe --output json | jq '.flow.verdict'
```

### Calico Enterprise UI

Enterprise 관리 UI에는 해당 제품·라이선스와 실제 서비스/TLS/인증 구성이 필요하며 Calico Open Source 설치만으로 생기지 않습니다. port-forward 전에 설치된 서비스 이름·포트·접근 정책을 확인하고 모든 설치에 `cnx-manager`가 있다고 가정하지 않습니다.

### Network Policy 시각화 도구

`kubectl get networkpolicy -n <namespace>`와 `kubectl describe networkpolicy <name> -n <namespace>`로 Kubernetes 셀렉터·규칙을 확인하고 설치된 엔진의 인증된 flow 도구로 집행을 관측합니다. 외부 viewer/plugin의 존재·플래그는 해당 프로젝트의 현재 릴리스에서 확인해야 합니다. YAML 그래프만으로 dataplane 집행을 입증할 수 없습니다.

### Kube-hunter를 사용한 보안 테스트

kube-hunter는 클러스터 노출·보안 scanner이며 NetworkPolicy 허용/거부 검증기를 대신하지 않습니다. 침투적 트래픽을 만들 수 있으므로 명시적으로 승인한 대상·범위와 검토한 릴리스/이미지를 사용합니다. 일반 정책 문서에서 버전을 고정하지 않은 scanner를 운영 네임스페이스에 배포하지 않습니다. 이번 검토는 scanner를 실행하지 않았습니다.

## 모범 사례

### 1. 기본 거부 정책 적용

```yaml
# 이 production 네임스페이스에만 적용
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

### 2. 최소 권한 원칙

필요한 통신만 명시적으로 허용:

```yaml
# 명시적이고 구체적인 규칙
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-minimal-access
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - port: 8080
          protocol: TCP
```

### 3. 정책 문서화

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-ingress
  namespace: production
  annotations:
    description: "Allow traffic from frontend to API on port 8080"
    owner: "platform-team"
    review-ticket: "REPLACE_WITH_APPROVED_CHANGE"
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
```

### 4. 정기적인 정책 감사

읽기 전용 목록은 네임스페이스 전체를 선택하고 허용 규칙이 없는 기준선을 ingress·egress별로 구분합니다. 빈 `[]`와 생략한 규칙을 처리하지만 `{}` 규칙은 트래픽 허용이므로 deny로 세지 않습니다. API·권한 오류를 정책0개로 바꾸지 않고 실패 처리합니다. 기준선이 있어도 다른 허용·확장 정책, 미선택 Pod, CNI 상태를 검토해야 하므로 **격리 입증이 아닙니다**.

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${CONTEXT:?Set an approved kubectl context}"
work=$(mktemp -d "${TMPDIR:-/tmp}/network-policy-inventory.XXXXXX")
trap 'rm -rf -- "$work"' EXIT
if ! kubectl --context="$CONTEXT" --request-timeout=15s get namespaces -o json >"$work/namespaces.json"; then
  echo "UNKNOWN: namespace inventory failed." >&2
  exit 2
fi
if ! kubectl --context="$CONTEXT" --request-timeout=15s get networkpolicies -A -o json >"$work/policies.json"; then
  echo "UNKNOWN: policy inventory failed." >&2
  exit 2
fi
jq -n --slurpfile ns "$work/namespaces.json" --slurpfile np "$work/policies.json" '
  def directions:
    (.spec.policyTypes // []) as $types |
    if ($types | length) > 0 then $types
    else ["Ingress"] + (if ((.spec.egress // []) | length) > 0 then ["Egress"] else [] end)
    end;
  def selects_all:
    ((.spec.podSelector.matchLabels // {}) | length) == 0 and
    ((.spec.podSelector.matchExpressions // []) | length) == 0;
  def empty_baseline($direction; $rules):
    select(selects_all and ((directions | index($direction)) != null) and
           ((.spec[$rules] // []) | length) == 0) | .metadata.name;
  {
    note: "Inventory only: other allow rules, extension policies and CNI enforcement are not evaluated.",
    namespaces: [
      $ns[0].items[] | .metadata.name as $name |
      [$np[0].items[] | select(.metadata.namespace == $name)] as $policies |
      {
        namespace: $name,
        policyCount: ($policies | length),
        ingressBaselines: [$policies[] | empty_baseline("Ingress"; "ingress")],
        egressBaselines: [$policies[] | empty_baseline("Egress"; "egress")]
      }
    ]
  }
'
```

## 요약

Kubernetes 네트워크 정책은 클러스터 내 Pod 통신을 제어하는 핵심 보안 메커니즘입니다:

1. **기본 NetworkPolicy**: 네임스페이스 범위, podSelector/namespaceSelector/ipBlock 지원
2. **Cilium 확장**: L7 정책, DNS FQDN 기반 정책, 클러스터 와이드 정책
3. **Calico 확장**: GlobalNetworkPolicy, NetworkSet, Tier 기반 정책
4. **EKS 고려사항**: VPC CNI NetworkPolicy 활성화, Security Groups for Pods, ClusterNetworkPolicy 및 DNS(FQDN) 기반 Egress 제어

### 권장 사항

- 모든 프로덕션 네임스페이스에 기본 거부 정책 적용
- 최소 권한 원칙에 따라 필요한 트래픽만 허용
- 정기적인 정책 감사 및 테스트
- L7 정책이 필요한 경우 Cilium 사용 고려

---

## 참고 자료

- [Kubernetes Network Policies 공식 문서](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Cilium Network Policy 문서](https://docs.cilium.io/en/stable/security/policy/index.html)
- [Calico Network Policy 문서](https://docs.tigera.io/calico/latest/reference/resources/networkpolicy)
- [EKS Security Best Practices - Network Security](https://docs.aws.amazon.com/eks/latest/best-practices/network-security.html)
- [Amazon EKS Enhanced Network Security Policies (2025-12-15)](https://aws.amazon.com/ko/about-aws/whats-new/2025/12/amazon-eks-enhanced-network-security-policies/)

- [EKS Pod security groups](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
- [Calico Tier](https://docs.tigera.io/calico/latest/reference/resources/tier)
- [Calico NetworkSet](https://docs.tigera.io/calico/latest/reference/resources/networkset)
