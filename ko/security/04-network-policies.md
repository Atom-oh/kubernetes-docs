# 네트워크 정책 (Network Policies)

> **지원 버전**: Kubernetes 1.31, 1.32, 1.33
> **마지막 업데이트**: 2025년 2월 21일

Kubernetes 네트워크 정책은 Pod 간 트래픽을 제어하는 방화벽 규칙입니다. 이 문서에서는 기본 NetworkPolicy부터 Cilium과 Calico의 확장 기능까지 상세히 다룹니다.

## 목차

1. [네트워크 정책 개요](#네트워크-정책-개요)
2. [Kubernetes NetworkPolicy 스펙](#kubernetes-networkpolicy-스펙)
3. [기본 거부 정책](#기본-거부-정책)
4. [정책 순서 및 평가](#정책-순서-및-평가)
5. [Cilium 네트워크 정책 확장](#cilium-네트워크-정책-확장)
6. [Calico 네트워크 정책 확장](#calico-네트워크-정책-확장)
7. [설계 패턴](#설계-패턴)
8. [네트워크 정책 테스트](#네트워크-정책-테스트)
9. [EKS 고려사항](#eks-고려사항)
10. [시각화 도구](#시각화-도구)

---

## 네트워크 정책 개요

### 네트워크 정책이란?

네트워크 정책은 Kubernetes에서 Pod 수준의 방화벽 역할을 합니다. 기본적으로 Kubernetes Pod는 모든 다른 Pod와 자유롭게 통신할 수 있지만, 네트워크 정책을 통해 이 트래픽을 제한할 수 있습니다.

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
| **추가적(Additive)** | 여러 정책이 있으면 모든 정책의 합집합이 적용 |
| **선택적 적용** | podSelector로 대상 Pod 지정 |
| **방향별 제어** | Ingress(수신)와 Egress(송신) 별도 제어 |
| **CNI 의존** | CNI 플러그인이 NetworkPolicy를 지원해야 함 |

### CNI별 NetworkPolicy 지원

| CNI | 기본 NetworkPolicy | 확장 기능 | L7 정책 |
|-----|-------------------|----------|--------|
| **Cilium** | ✓ | CiliumNetworkPolicy, CiliumClusterwideNetworkPolicy | ✓ |
| **Calico** | ✓ | GlobalNetworkPolicy, NetworkSet | ✓ (Enterprise) |
| **Weave Net** | ✓ | 제한적 | ✗ |
| **Flannel** | ✗ | ✗ | ✗ |
| **Amazon VPC CNI** | ✗ (별도 설치 필요) | Security Groups for Pods | ✗ |

---

## Kubernetes NetworkPolicy 스펙

### 기본 구조

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

정책이 적용될 Pod를 선택합니다.

```yaml
# 특정 레이블을 가진 Pod에 적용
spec:
  podSelector:
    matchLabels:
      app: api
      version: v1

# 모든 Pod에 적용 (빈 셀렉터)
spec:
  podSelector: {}

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

다른 네임스페이스의 Pod를 선택합니다.

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
              name: monitoring
        # production 네임스페이스의 특정 Pod 허용
        - namespaceSelector:
            matchLabels:
              name: production
          podSelector:
            matchLabels:
              role: frontend
```

**주의:** `namespaceSelector`와 `podSelector`를 함께 사용할 때 AND vs OR 구분:

```yaml
# OR 조건 (두 개의 별도 규칙)
ingress:
  - from:
      - namespaceSelector:    # 규칙 1
          matchLabels:
            name: team-a
      - podSelector:          # 규칙 2
          matchLabels:
            role: frontend

# AND 조건 (하나의 규칙)
ingress:
  - from:
      - namespaceSelector:    # 두 조건 모두 충족해야 함
          matchLabels:
            name: team-a
        podSelector:
          matchLabels:
            role: frontend
```

### ipBlock

특정 IP 범위를 허용하거나 차단합니다.

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

## 기본 거부 정책

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

Egress를 차단할 때 DNS 조회를 허용하는 일반적인 패턴:

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
    # kube-dns/CoreDNS 접근 허용
    - to:
        - namespaceSelector: {}
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

```yaml
---
# 1. 모든 트래픽 기본 거부
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
---
# 2. DNS만 허용
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
      ports:
        - protocol: UDP
          port: 53
---
# 3. 필요한 통신만 명시적으로 허용
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
```

---

## 정책 순서 및 평가

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
              name: monitoring
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

## Cilium 네트워크 정책 확장

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
            - port: "8080"
              protocol: TCP
          rules:
            http:
              # GET 요청만 허용
              - method: GET
                path: "/api/v1/products"

              # 특정 경로 패턴 허용
              - method: GET
                path: "/api/v1/products/[0-9]+"

              # POST는 특정 헤더가 있을 때만 허용
              - method: POST
                path: "/api/v1/orders"
                headers:
                  - "X-API-Key: .*"
                  - "Content-Type: application/json"

              # PUT/DELETE는 admin만 허용
              - method: "PUT|DELETE"
                path: "/api/v1/.*"
                headers:
                  - "X-User-Role: admin"
```

### L7 Kafka 정책

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: kafka-policy
  namespace: data
spec:
  endpointSelector:
    matchLabels:
      app: kafka

  ingress:
    - fromEndpoints:
        - matchLabels:
            app: producer
      toPorts:
        - ports:
            - port: "9092"
              protocol: TCP
          rules:
            kafka:
              # 특정 토픽에만 produce 허용
              - role: produce
                topic: "orders"
              - role: produce
                topic: "events"

    - fromEndpoints:
        - matchLabels:
            app: consumer
      toPorts:
        - ports:
            - port: "9092"
              protocol: TCP
          rules:
            kafka:
              # 특정 토픽에서만 consume 허용
              - role: consume
                topic: "orders"
                clientID: "order-processor-.*"
```

### L7 DNS 정책

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
    # DNS 조회 허용
    - toEndpoints:
        - matchLabels:
            k8s:io.kubernetes.pod.namespace: kube-system
            k8s-app: kube-dns
      toPorts:
        - ports:
            - port: "53"
              protocol: UDP
          rules:
            dns:
              # 특정 도메인만 조회 허용
              - matchPattern: "*.amazonaws.com"
              - matchPattern: "api.example.com"
              - matchName: "database.production.svc.cluster.local"

    # 조회한 도메인으로의 연결 허용
    - toFQDNs:
        - matchPattern: "*.amazonaws.com"
        - matchName: "api.example.com"
      toPorts:
        - ports:
            - port: "443"
              protocol: TCP
```

### CiliumClusterwideNetworkPolicy

클러스터 전체에 적용되는 정책:

```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: cluster-default-deny
spec:
  # 모든 엔드포인트에 적용
  endpointSelector: {}

  ingress:
    - fromEntities:
        - cluster  # 클러스터 내부 트래픽만 허용

  egress:
    - toEntities:
        - cluster
        - world  # 외부 트래픽 허용 (필요시)
    - toEndpoints:
        - matchLabels:
            k8s:io.kubernetes.pod.namespace: kube-system
      toPorts:
        - ports:
            - port: "53"
              protocol: UDP
```

### Cilium 엔티티 기반 정책

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: entity-based-policy
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      app: web

  ingress:
    - fromEntities:
        - world      # 클러스터 외부
        - cluster    # 클러스터 내부

  egress:
    - toEntities:
        - world      # 인터넷
      toPorts:
        - ports:
            - port: "443"
              protocol: TCP

    - toEntities:
        - host       # 노드 자체
      toPorts:
        - ports:
            - port: "10250"  # kubelet
              protocol: TCP

    - toEntities:
        - kube-apiserver  # API 서버
```

---

## Calico 네트워크 정책 확장

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

클러스터 전체에 적용되는 Calico 정책:

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default-deny-all
spec:
  # 네임스페이스가 아닌 전체 셀렉터
  selector: all()

  order: 1000  # 낮은 우선순위 (다른 정책이 먼저 평가됨)

  types:
    - Ingress
    - Egress

  # 규칙 없음 = 모든 트래픽 차단

---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: allow-dns
spec:
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

재사용 가능한 IP 집합 정의:

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkSet
metadata:
  name: external-apis
  namespace: production
spec:
  nets:
    - 203.0.113.0/24     # 외부 API 서버
    - 198.51.100.10/32   # 특정 서비스

---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkSet
metadata:
  name: blocked-ips
spec:
  nets:
    - 192.0.2.0/24       # 차단할 IP 대역
    - 10.0.0.5/32        # 특정 차단 IP
```

NetworkSet 사용:

```yaml
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
      destination:
        selector: projectcalico.org/name == 'external-apis'
        namespaceSelector: projectcalico.org/name == 'production'
```

### Tier 기반 정책

Calico Enterprise에서 지원하는 계층형 정책:

```yaml
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: security
spec:
  order: 100

---
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: platform
spec:
  order: 200

---
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: application
spec:
  order: 300

---
# Security Tier 정책 (가장 먼저 평가)
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: security.block-known-threats
spec:
  tier: security
  order: 100
  selector: all()
  types:
    - Ingress
  ingress:
    - action: Deny
      source:
        selector: global(name == 'blocked-ips')

---
# Platform Tier 정책
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: platform.allow-dns
spec:
  tier: platform
  order: 100
  selector: all()
  types:
    - Egress
  egress:
    - action: Allow
      protocol: UDP
      destination:
        ports:
          - 53
```

---

## 설계 패턴

### 마이크로세그멘테이션

각 서비스를 개별적으로 격리:

```yaml
---
# 1. 네임스페이스 기본 거부
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
---
# 2. DNS 허용
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
      ports:
        - protocol: UDP
          port: 53
---
# 3. Frontend -> API
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
# 4. API -> Database
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
# 5. API 외부 접근 (필요시)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-external-access
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Egress
  egress:
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
            except:
              - 10.0.0.0/8
              - 172.16.0.0/12
              - 192.168.0.0/16
      ports:
        - protocol: TCP
          port: 443
```

### 네임스페이스 격리

```yaml
---
# 1. 네임스페이스 레이블 설정
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
  labels:
    team: team-a
    environment: production
---
# 2. 같은 팀 내부만 통신 허용
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-same-team
  namespace: team-a
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              team: team-a
---
# 3. 다른 팀의 특정 서비스 접근 허용
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
              shared-services: "true"
          podSelector:
            matchLabels:
              exposed: "true"
```

### 데이터베이스 보호

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
    # 애플리케이션에서만 접근 허용
    - from:
        - namespaceSelector:
            matchLabels:
              environment: production
          podSelector:
            matchLabels:
              database-access: "true"
      ports:
        - protocol: TCP
          port: 5432
    # 모니터링 접근 허용
    - from:
        - namespaceSelector:
            matchLabels:
              name: monitoring
          podSelector:
            matchLabels:
              app: prometheus
      ports:
        - protocol: TCP
          port: 9187  # postgres_exporter
  egress:
    # 복제용 다른 DB 인스턴스 접근
    - to:
        - podSelector:
            matchLabels:
              app: postgresql
      ports:
        - protocol: TCP
          port: 5432
    # DNS
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
      ports:
        - protocol: UDP
          port: 53
```

### 3-Tier 아키텍처 정책

```yaml
---
# Web Tier
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
    # 외부(Ingress Controller)에서 접근 허용
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - protocol: TCP
          port: 80
  egress:
    # App Tier로만 통신
    - to:
        - podSelector:
            matchLabels:
              tier: app
      ports:
        - protocol: TCP
          port: 8080
    # DNS
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
---
# App Tier
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
    # Web Tier에서만 접근 허용
    - from:
        - podSelector:
            matchLabels:
              tier: web
      ports:
        - protocol: TCP
          port: 8080
  egress:
    # Data Tier로만 통신
    - to:
        - podSelector:
            matchLabels:
              tier: data
      ports:
        - protocol: TCP
          port: 5432
        - protocol: TCP
          port: 6379
    # DNS
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
---
# Data Tier
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
    # App Tier에서만 접근 허용
    - from:
        - podSelector:
            matchLabels:
              tier: app
      ports:
        - protocol: TCP
          port: 5432
        - protocol: TCP
          port: 6379
  egress:
    # 같은 tier 내 복제 통신
    - to:
        - podSelector:
            matchLabels:
              tier: data
```

---

## 네트워크 정책 테스트

### netshoot을 사용한 테스트

```bash
# netshoot Pod 배포
kubectl run netshoot --image=nicolaka/netshoot -it --rm -- /bin/bash

# 연결 테스트
curl -v http://api-service:8080/health
nc -zv database-service 5432
nslookup api-service.production.svc.cluster.local

# TCP 연결 테스트
curl --connect-timeout 5 http://target-service:8080
```

### kubectl exec을 사용한 테스트

```bash
# Pod에서 다른 서비스로 연결 테스트
kubectl exec -it frontend-pod -- curl -v http://api-service:8080

# DNS 확인
kubectl exec -it frontend-pod -- nslookup api-service

# 포트 스캔
kubectl exec -it frontend-pod -- nc -zv api-service 8080
```

### Cilium Connectivity Test

```bash
# Cilium 연결성 테스트 실행
cilium connectivity test

# 특정 테스트만 실행
cilium connectivity test --test pod-to-pod
cilium connectivity test --test pod-to-service

# 정책 테스트
cilium connectivity test --test to-entities-world
cilium connectivity test --test to-cidr-external
```

### 자동화된 테스트 스크립트

```bash
#!/bin/bash
# network-policy-test.sh

echo "=== Network Policy Test Suite ==="

# 테스트용 Pod 생성
kubectl run test-pod --image=nicolaka/netshoot --restart=Never --labels="app=test" -- sleep 3600

# Pod가 준비될 때까지 대기
kubectl wait --for=condition=Ready pod/test-pod --timeout=60s

# 테스트 케이스 실행
run_test() {
    local name=$1
    local command=$2
    local expected=$3

    echo -n "Testing: $name... "
    result=$(kubectl exec test-pod -- timeout 5 sh -c "$command" 2>&1)

    if [[ "$expected" == "success" && $? -eq 0 ]]; then
        echo "PASS"
    elif [[ "$expected" == "fail" && $? -ne 0 ]]; then
        echo "PASS (correctly blocked)"
    else
        echo "FAIL"
        echo "  Result: $result"
    fi
}

# 테스트 케이스
run_test "DNS resolution" "nslookup kubernetes.default" "success"
run_test "API server access" "curl -k https://kubernetes.default/healthz" "success"
run_test "External access blocked" "curl -s --connect-timeout 3 http://example.com" "fail"
run_test "Database access" "nc -zv database-service 5432" "success"

# 정리
kubectl delete pod test-pod --force --grace-period=0
```

---

## EKS 고려사항

### Amazon VPC CNI와 NetworkPolicy

Amazon VPC CNI는 기본적으로 NetworkPolicy를 지원하지 않습니다. NetworkPolicy를 사용하려면 추가 구성이 필요합니다:

```bash
# 옵션 1: VPC CNI의 NetworkPolicy 지원 활성화 (v1.14.0+)
kubectl set env daemonset aws-node -n kube-system ENABLE_NETWORK_POLICY=true

# VPC CNI 버전 확인
kubectl describe daemonset aws-node -n kube-system | grep Image

# 옵션 2: Calico 정책 엔진 추가 설치
kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-operator.yaml
kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-crs.yaml
```

### Security Groups for Pods

EKS에서 Pod에 직접 Security Group을 적용할 수 있습니다:

```yaml
# SecurityGroupPolicy 정의
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
      - sg-0123456789abcdef0  # 데이터베이스용 Security Group
---
# Pod가 자동으로 Security Group 적용
apiVersion: v1
kind: Pod
metadata:
  name: database-pod
  namespace: production
  labels:
    app: database
spec:
  containers:
    - name: postgres
      image: postgres:15
```

Security Group 설정 예시:

```hcl
# Terraform으로 Security Group 정의
resource "aws_security_group" "database_pods" {
  name_prefix = "database-pods-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app_pods.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

### VPC 레벨 제어와 NetworkPolicy 조합

```yaml
# NetworkPolicy (Pod 레벨)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-policy
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
              database-access: "true"
      ports:
        - protocol: TCP
          port: 5432
```

```hcl
# Security Group (VPC 레벨)
# 추가적인 네트워크 격리 제공
resource "aws_security_group" "database_pods" {
  # ... (위 예시 참조)
}

# NACL (서브넷 레벨)
# 서브넷 간 트래픽 제어
resource "aws_network_acl_rule" "database_subnet" {
  network_acl_id = aws_network_acl.database.id
  rule_number    = 100
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "10.0.0.0/16"
  from_port      = 5432
  to_port        = 5432
}
```

### EKS에서 Cilium 사용

```bash
# VPC CNI 제거 (선택적)
kubectl delete daemonset aws-node -n kube-system

# Cilium 설치
helm repo add cilium https://helm.cilium.io/
helm install cilium cilium/cilium --version 1.15.0 \
    --namespace kube-system \
    --set eni.enabled=true \
    --set ipam.mode=eni \
    --set egressMasqueradeInterfaces=eth0 \
    --set routingMode=native
```

---

## 시각화 도구

### Cilium Network Policy Editor

Cilium은 웹 기반 정책 편집기를 제공합니다:

```bash
# Cilium Hubble UI 활성화
cilium hubble enable --ui

# Hubble UI 접근
cilium hubble ui

# 또는 포트 포워딩
kubectl port-forward -n kube-system svc/hubble-ui 12000:80
```

### Cilium Policy Verdict 확인

```bash
# 실시간 정책 결정 확인
hubble observe --verdict DROPPED
hubble observe --verdict FORWARDED

# 특정 Pod의 트래픽 확인
hubble observe --pod production/api-server

# JSON 형식으로 출력
hubble observe --output json | jq '.flow.verdict'
```

### Calico Enterprise UI

Calico Enterprise는 정책 시각화 UI를 제공합니다:

```bash
# Calico Enterprise 대시보드 접근
kubectl port-forward -n calico-system svc/cnx-manager 9443:443
```

### Network Policy 시각화 도구

```bash
# kubectl-np-viewer 설치
kubectl krew install np-viewer

# 정책 시각화
kubectl np-viewer -n production

# 특정 Pod의 정책 확인
kubectl np-viewer -n production --pod api-server
```

### Kube-hunter를 사용한 보안 테스트

```bash
# 클러스터 보안 스캔
kubectl run kube-hunter --image=aquasec/kube-hunter --restart=Never -- --pod

# 결과 확인
kubectl logs kube-hunter
```

---

## 모범 사례

### 1. 기본 거부 정책 적용

```yaml
# 모든 프로덕션 네임스페이스에 적용
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
    last-reviewed: "2026-02-21"
spec:
  # ...
```

### 4. 정기적인 정책 감사

```bash
#!/bin/bash
# audit-network-policies.sh

echo "=== Network Policy Audit ==="

# 정책이 없는 네임스페이스 찾기
for ns in $(kubectl get namespaces -o jsonpath='{.items[*].metadata.name}'); do
    policies=$(kubectl get networkpolicies -n "$ns" --no-headers 2>/dev/null | wc -l)
    if [[ $policies -eq 0 ]]; then
        echo "WARNING: No NetworkPolicy in namespace: $ns"
    fi
done

# 기본 거부 정책 확인
for ns in $(kubectl get namespaces -o jsonpath='{.items[*].metadata.name}'); do
    deny_policy=$(kubectl get networkpolicies -n "$ns" -o json | jq -r '.items[] | select(.spec.podSelector == {} and .spec.ingress == null) | .metadata.name')
    if [[ -z "$deny_policy" ]]; then
        echo "INFO: No default-deny policy in namespace: $ns"
    fi
done
```

---

## 요약

Kubernetes 네트워크 정책은 클러스터 내 Pod 통신을 제어하는 핵심 보안 메커니즘입니다:

1. **기본 NetworkPolicy**: 네임스페이스 범위, podSelector/namespaceSelector/ipBlock 지원
2. **Cilium 확장**: L7 정책, DNS FQDN 기반 정책, 클러스터 와이드 정책
3. **Calico 확장**: GlobalNetworkPolicy, NetworkSet, Tier 기반 정책
4. **EKS 고려사항**: VPC CNI NetworkPolicy 활성화, Security Groups for Pods

### 권장 사항

- 모든 프로덕션 네임스페이스에 기본 거부 정책 적용
- 최소 권한 원칙에 따라 필요한 트래픽만 허용
- 정기적인 정책 감사 및 테스트
- L7 정책이 필요한 경우 Cilium 사용 고려

---

## 참고 자료

- [Kubernetes Network Policies 공식 문서](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Cilium Network Policy 문서](https://docs.cilium.io/en/stable/security/policy/)
- [Calico Network Policy 문서](https://docs.tigera.io/calico/latest/network-policy/)
- [EKS Security Best Practices - Network Security](https://aws.github.io/aws-eks-best-practices/security/docs/network/)
