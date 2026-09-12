# Part 5: Network Policy

> **검토 기준**: Calico 3.32.2; Calico 3.32의 Kubernetes 테스트 범위는 1.34–1.36입니다. **마지막 업데이트**: 2026년 9월 12일.
>
> 표준 Calico API 서버(`projectcalico.org/v3`), Kubernetes datastore와 호환되는 정책 적용 데이터 평면을 전제로 합니다. 전용 `calico-demo` namespace에서 워크로드 레이블·준비된 endpoint·기본 연결을 확인한 뒤 정책을 적용하세요. 각 절은 독립적인 패턴이며 한 번에 적용하는 매니페스트 묶음이 아닙니다. 기존 상위 정책, DNS 구현, Service NAT, 호스트 정책, 애플리케이션 동작도 결과에 영향을 줍니다. 이번 검토에서는 운영 클러스터·admission 서버·실제 패킷 전달을 실행하지 않았습니다.

## 개요

Network Policy는 워크로드와 다른 endpoint 사이의 허용 연결을 제어합니다. Calico는 표준 Kubernetes API에 정책 순서, 명시적 action, 전역 범위, HostEndpoint 제어를 추가합니다. 기능은 제품과 적용 경로에 따라 다릅니다. DNS 도메인 정책은 상용 확장이며 Open Source HTTP 정책에는 문서화된 Istio/Dikastes 통합이 필요합니다.

## Kubernetes NetworkPolicy 기본

### 표준 NetworkPolicy 구조

Kubernetes NetworkPolicy는 namespace 범위에서 Pod를 선택합니다. ingress와 egress 격리는 독립적이며 각 방향의 허용 범위는 일치하는 Kubernetes 정책들의 합집합입니다. 양쪽이 격리되면 새 연결에 송신 egress와 수신 ingress 허용이 모두 필요합니다. 허용된 연결의 응답에는 별도의 반대 방향 허용 규칙이 필요하지 않습니다.

`from`/`to` 목록의 항목끼리는 **OR**, 한 항목 안의 `namespaceSelector`와 `podSelector`는 **AND**입니다. namespace selector 없는 pod selector는 해당 정책의 namespace를 선택합니다.

일치하는 Kubernetes 정책이 없다는 것은 그 API가 해당 방향을 격리하지 않는다는 뜻이며 호스트 방화벽·Calico 정책 등 다른 제어를 무시하지 않습니다. 정책 변경이 기존 연결에 미치는 영향은 구현에 따라 다르므로 새 연결로 확인하세요. Service/LB NAT 전후에 `ipBlock`이 보게 되는 주소도 구현에 영향을 받습니다.

```yaml
# 기본 Kubernetes NetworkPolicy 예시
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: calico-demo
spec:
  # 정책이 적용될 Pod 선택
  podSelector:
    matchLabels:
      app: backend
      tier: api

  # 정책 유형 (Ingress, Egress, 또는 둘 다)
  policyTypes:
    - Ingress
    - Egress

  # Ingress 규칙 (들어오는 트래픽)
  ingress:
    # 규칙 1: frontend에서 8080 포트로 접근 허용
    - from:
        - podSelector:
            matchLabels:
              app: frontend
          namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: calico-demo
      ports:
        - protocol: TCP
          port: 8080

    # 규칙 2: monitoring 네임스페이스에서 메트릭 수집 허용
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: monitoring
      ports:
        - protocol: TCP
          port: 9090

  # Egress 규칙 (나가는 트래픽)
  egress:
    # DNS 허용
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

    # 데이터베이스 접근 허용
    - to:
        - podSelector:
            matchLabels:
              app: database
      ports:
        - protocol: TCP
          port: 5432
```

### Kubernetes NetworkPolicy의 한계

| 기능 | Kubernetes NetworkPolicy | Calico 확장·전제 |
| --- | --- | --- |
| 범위 | namespace 안의 Pod | GlobalNetworkPolicy로 여러 namespace의 워크로드·HostEndpoint 선택 |
| 순서·action | 허용 규칙의 합집합, 사용자 지정 정책 순서 없음 | Tier/order와 Allow·Deny·Log·Pass |
| 포트 | TCP/UDP/SCTP, named port, `endPort` 숫자 범위(1.25부터 stable, 플러그인 지원 필요) | Calico 포트 범위 표현과 추가 IP 프로토콜·ICMP 매칭 |
| HTTP 메서드·경로 | 이 API에 없음 | Open Source의 `http` 규칙에는 Istio/Dikastes 적용 경로 필요 |
| DNS 도메인 | 이 API에 없음 | 예: Calico Enterprise 도메인 정책. Open Source 3.32 CRD에는 `domains` 없음 |
| 호스트 인터페이스 | 일반 노드 방화벽이 아님 | HostEndpoint의 local·forwarded·failsafe 동작을 별도 고려 |

표준 NetworkPolicy 객체와 새 Kubernetes 클러스터 정책 API는 구분해야 합니다. 모든 Kubernetes 네트워크 보안 API가 namespace 전용이라는 뜻은 아닙니다. 스키마가 필드를 허용해도 실제 데이터 평면의 프로토콜·로깅 지원을 확인해야 합니다.

## Calico NetworkPolicy

### 기본 구조

Calico NetworkPolicy는 Kubernetes NetworkPolicy를 확장합니다.

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: advanced-backend-policy
  namespace: calico-demo
spec:
  # Calico 셀렉터 문법 (표현식 기반)
  selector: app == 'backend' && tier == 'api'

  # 정책 순서 (낮을수록 먼저 평가, 기본값: 무한대)
  order: 100

  # Ingress 규칙
  ingress:
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'frontend'
      destination:
        ports:
          - 8080

  # Egress 규칙
  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: app == 'database'
        ports:
          - 5432
```

### 셀렉터 문법

Calico는 강력한 표현식 기반 셀렉터를 제공합니다.

| 표현식 | 의미 |
| --- | --- |
| `app == 'frontend'` | 정확한 값 일치 |
| `app == 'backend' && env == 'production'` | 두 조건 모두 일치 |
| `app == 'frontend' \|\| app == 'backend'` | 어느 조건이든 일치 |
| `app != 'legacy'` | 다른 값 또는 레이블 없음 |
| `has(app)` / `!has(internal)` | 레이블 존재 / 부재 |
| `app in {'frontend', 'backend'}` | 집합에 속하는 값 |
| `env not in {'dev', 'staging'}` | 집합 밖의 값 또는 레이블 없음 |
| `all()` / `!all()` | 범위 안의 모든 리소스 / 아무 리소스도 선택하지 않음 |

한 `spec`에 `selector` 키를 여러 번 쓰지 말고 표현식 하나를 선택하거나 `&&`·`||`로 결합하세요. YAML 문자열이 `!`로 시작하면 따옴표로 감쌉니다.

`selector: !has(x)`는 알려진 리소스 중 레이블이 없는 대상을 선택합니다. `notSelector: has(x)`는 패킷 매칭을 부정하므로 해당 selector에 속하지 않는 외부 주소도 매칭할 수 있습니다. 규칙의 `selector: all()`도 모든 패킷을 뜻하지 않으며, 모든 패킷을 매칭하려면 해당 endpoint selector 조건을 생략합니다.

### Action 유형

Calico 정책은 네 가지 action을 사용합니다. 일반 정책에서 Allow/Deny는 해당 endpoint 방향의 정책 평가를 끝내고 Log는 다음 규칙으로 진행합니다. Pass는 같은 Tier의 **나머지 정책까지 건너뛰므로** 뒤에 배치한 보안 규칙도 실행되지 않습니다. 적용 가능한 다음 Tier로 이동하고 마지막 Tier에서 Pass하면 Profile 평가로 넘어갑니다. Host pre-DNAT/untracked 경로에는 별도 기본 동작이 있습니다.

```yaml
# Allow - 트래픽 허용
- action: Allow
  protocol: TCP
  destination:
    ports:
      - 8080

# Deny - 트래픽 명시적 거부
- action: Deny
  source:
    selector: "has(untrusted)"

# Log - 트래픽 로깅 (처리는 다음 규칙으로)
- action: Log
  protocol: TCP
  destination:
    ports:
      - 22

# Pass - 다음 Tier로 전달 (Tier 사용 시)
- action: Pass
```

### 프로토콜 및 포트 지정

SCTP 예시는 호환되는 classic 데이터 평면이 필요합니다. Calico 3.32 eBPF는 SCTP 정책·Service를 지원하지 않습니다.

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: protocol-examples
  namespace: calico-demo
spec:
  selector: app == 'backend'

  ingress:
    # TCP 특정 포트
    - action: Allow
      protocol: TCP
      destination:
        ports:
          - 80
          - 443
          - "8080:8090"  # 포트 범위

    # UDP
    - action: Allow
      protocol: UDP
      destination:
        ports:
          - 53

    # ICMP (IPv4)
    - action: Allow
      protocol: ICMP
      icmp:
        type: 8  # Echo Request
        code: 0

    # ICMPv6
    - action: Allow
      protocol: ICMPv6
      icmp:
        type: 128  # Echo Request
        code: 0

    # SCTP
    - action: Allow
      protocol: SCTP
      destination:
        ports:
          - 36412  # S1AP

    # TCP 전체 포트 (다른 프로토콜까지 허용하는 것은 아님)
    - action: Allow
      protocol: TCP
      destination:
        ports:
          - "1:65535"  # 모든 포트
```

### Source/Destination 지정

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: source-dest-examples
  namespace: calico-demo
spec:
  selector: app == 'backend'

  ingress:
    # Pod 셀렉터
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'frontend'
      destination:
        ports:
          - 8080

    # 네임스페이스 셀렉터
    - action: Allow
      protocol: TCP
      source:
        namespaceSelector: env == 'production'
      destination:
        ports:
          - 8080

    # 네임스페이스 + Pod 셀렉터 조합
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'api-gateway'
        namespaceSelector: kubernetes.io/metadata.name == 'ingress'
      destination:
        ports:
          - 8080

    # CIDR 블록
    - action: Allow
      protocol: TCP
      source:
        nets:
          - 10.0.0.0/8
          - 172.16.0.0/12
        notNets:
          - 10.0.100.0/24  # 제외할 서브넷
      destination:
        ports:
          - 8080

    # 서비스 계정 기반
    - action: Allow
      source:
        serviceAccounts:
          names:
            - frontend-sa
            - api-gateway-sa
          selector: role == 'frontend'
```

## GlobalNetworkPolicy

GlobalNetworkPolicy는 namespace에 속하지 않으며 여러 namespace의 워크로드나 HostEndpoint를 선택할 수 있습니다. `selector: all()`만으로 “애플리케이션 Pod만 전체 선택”하는 것은 아닙니다. 아래 예시는 demo namespace의 워크로드로 범위를 제한하여 시스템·호스트 트래픽을 분리합니다.

### 기본 거부와 명시적 예외

빈 정책은 양쪽 방향을 선택합니다. order를 생략하면 명시한 정책들보다 나중에 평가하며 10,000이 특별한 “최하위 우선순위” 값은 아닙니다. 빈 규칙은 앞선 최종 Allow를 덮어쓰지 않습니다. 애플리케이션 정책이 우회하면 안 되는 제한은 별도 관리하는 앞쪽 Tier에 배치하세요.

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default.demo-default-deny
spec:
  tier: default
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  types: [Ingress, Egress]
  ingress: []
  egress: []
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default.demo-essential-egress
spec:
  tier: default
  order: 100
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  selector: needs-platform == 'true'
  types: [Egress]
  egress:
    - action: Allow
      protocol: UDP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      destination:
        services:
          name: kubernetes
          namespace: default
```

플랫폼 egress는 `needs-platform=true` 레이블을 가진 워크로드에만 허용합니다. Service 매칭은 **Kubernetes datastore**에서 실제 `kubernetes/default` endpoint와 포트를 사용하며 etcd datastore에서는 무시됩니다. 해당 Service 매칭에 destination ports·CIDR·selector를 함께 지정하지 마세요. API 네트워크 연결과 API 인증·RBAC은 별개입니다.

실제 DNS 배포를 확인하세요. namespace와 Pod selector를 함께 사용하면 다른 namespace의 임의 `kube-dns` 레이블 Pod를 resolver로 신뢰하지 않습니다. 노드 로컬 DNS에는 실제 경로에 맞는 매칭이 필요합니다. 시스템 의존성을 파악하기 전에 `kube-system`에 빈 정책을 적용하면 클러스터가 중단될 수 있으므로 별도 테스트 namespace에서 패턴을 확인하세요.

### 앞쪽 Tier의 egress 제한

다음 독립 예시는 demo 워크로드의 IPv4 메타데이터 주소를 차단하고 Tier 끝에서 다른 트래픽을 위임합니다. 전체 SSRF 방어, privileged/hostNetwork 프로세스 보호, 모든 플랫폼 메타데이터 주소의 차단을 보장하는 예시는 아닙니다.

```yaml
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: egress-guardrail
spec:
  order: 50
  defaultAction: Pass
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: egress-guardrail.block-imds-v4
spec:
  tier: egress-guardrail
  order: 10
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  types: [Egress]
  egress:
    - action: Deny
      destination:
        nets: [169.254.169.254/32]
```

같은 Tier의 뒤쪽 제한보다 먼저 무조건 Pass를 넣지 마세요. 플랫폼에 필요한 identity·DNS 경로를 유지하고 실제 workload-to-host 적용 동작을 확인해야 합니다.

## NetworkSet / GlobalNetworkSet

NetworkSet은 IP/CIDR 집합에 레이블을 붙여 정책에서 재사용합니다. 객체 이름이 아닌 레이블 selector로 참조하며, 같은 레이블의 endpoint도 매칭될 수 있으므로 레이블 관리 권한과 namespace/global 범위를 함께 확인하세요. 예시 주소는 실제 국가별 주소 목록이나 위협 정보가 아닙니다.

namespaced 정책에서 GlobalNetworkSet을 선택하려면 entity의 `namespaceSelector: global()`과 별도 레이블 selector를 사용합니다. namespaced NetworkSet은 선택한 namespace 안에서 매칭됩니다. 신뢰·차단 범위가 겹치면 먼저 Deny를 평가해야 하며 앞선 Allow는 최종 결정입니다.

### NetworkSet (네임스페이스 범위)

```yaml
# 외부 데이터베이스 IP 집합
apiVersion: projectcalico.org/v3
kind: NetworkSet
metadata:
  name: external-databases
  namespace: calico-demo
  labels:
    service-type: database
    environment: production
spec:
  nets:
    - 10.100.10.10/32  # Primary PostgreSQL
    - 10.100.10.11/32  # Secondary PostgreSQL
    - 10.100.20.10/32  # MongoDB Primary
    - 10.100.20.11/32  # MongoDB Secondary
    - 10.100.30.0/24   # Redis Cluster
---
# NetworkSet 참조 정책
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: allow-database-access
  namespace: calico-demo
spec:
  selector: app == 'backend'

  egress:
    - action: Allow
      protocol: TCP
      destination:
        # NetworkSet 참조 (레이블 셀렉터 사용)
        selector: service-type == 'database'
        namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
        ports:
          - 5432  # PostgreSQL
          - 27017 # MongoDB
          - 6379  # Redis
```

### GlobalNetworkSet (클러스터 전역)

```yaml
# 신뢰할 수 있는 파트너 IP
apiVersion: projectcalico.org/v3
kind: GlobalNetworkSet
metadata:
  name: trusted-partners
  labels:
    partner: trusted
    access-level: external
spec:
  nets:
    - 203.0.113.0/24    # Partner A 네트워크
    - 198.51.100.0/24   # Partner B 네트워크
    - 192.0.2.10/32     # Partner C 단일 IP
---
# 차단해야 할 악성 IP
apiVersion: projectcalico.org/v3
kind: GlobalNetworkSet
metadata:
  name: blocked-ips
  labels:
    threat: malicious
spec:
  nets:
    - 192.0.2.128/25    # 문서용 차단 예시, 실제 위협 정보 아님
    - 192.0.2.100/32    # 문서용 단일 주소
---
# GlobalNetworkSet 참조 정책
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: block-malicious-traffic
spec:
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  selector: all()
  order: 10  # 가장 먼저 평가

  ingress:
    # 악성 IP 차단
    - action: Deny
      source:
        namespaceSelector: global()
        selector: "threat == 'malicious'"

    # 신뢰할 수 있는 파트너 허용
    - action: Allow
      protocol: TCP
      source:
        namespaceSelector: global()
        selector: "partner == 'trusted'"
      destination:
        ports:
          - 443
```

## Tier 기반 정책

Tier는 Calico Open Source 3.32에서도 지원합니다. namespaced·global Calico 정책을 묶는 기능이며 Kubernetes NetworkPolicy에서 GlobalNetworkPolicy로 기능이 순차 확장되는 계층은 아닙니다.

### 평가 순서와 기본 동작

일반 endpoint 정책에서는 Tier의 `order`, Tier 안의 정책 `order`가 낮은 순서로 평가합니다. 정책 order를 생략하면 명시한 정책들보다 뒤에서 평가합니다. 대상 endpoint뿐 아니라 **트래픽 방향**도 구분하세요.

| 상황 | 결과 |
| --- | --- |
| 해당 endpoint·방향을 선택하는 정책이 Tier에 없음 | Tier 건너뛰기 |
| 규칙이 Allow/Deny | 해당 endpoint·방향의 정책 판단 종료 |
| 규칙이 Log | 다음 규칙 계속 평가 |
| 규칙이 Pass | 같은 Tier의 나머지 정책까지 건너뛰고 다음 적용 가능한 Tier로 이동 |
| 적용되는 Tier에서 최종 action에 일치하지 않음 | Tier의 `defaultAction` 적용. 기본값은 Deny |
| 마지막 적용 Tier에서 Pass | endpoint Profile 평가. 허용하는 Profile이 없으면 거부 |

“규칙이 안 맞으면 언제나 다음 Tier”가 아닙니다. 한 endpoint의 Allow도 반대쪽 endpoint 정책까지 우회하지는 않습니다. Host pre-DNAT·untracked 경로의 fall-through는 뒤에서 별도로 다룹니다.

기본 `default` Tier의 고정 order는 **1,000,000**이며 1,000이나 무한대가 아닙니다. Kubernetes NetworkPolicy와 Tier를 지정하지 않은 Calico 정책이 들어갑니다. 현재 Kubernetes 클러스터 정책 통합의 `kube-admin`·`kube-baseline` Tier는 각각 1,000·10,000,000과 Pass 기본 동작을 사용하므로 `default`가 모든 구성에서 무조건 마지막인 것도 아닙니다.

### 보안·플랫폼·애플리케이션 판단 분리

다음 예시는 security/platform Tier 끝의 Pass로 위임합니다. 그래야 각 Tier의 적용 가능한 규칙을 모두 검사한 뒤 다음 Tier로 넘어갑니다. Tier 생성·순서 변경 권한은 중앙에서 통제하세요.

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
  order: 500
  defaultAction: Deny
```

아래 문서용 위협 주소 차단 뒤에는 별도의 제한 데이터 규칙이 있습니다. 첫 보안 정책 끝에 Pass를 넣으면 두 번째 정책을 건너뛰므로 **Tier 끝에서 위임**합니다. 데이터 범위 레이블은 분할 예시이며 완전한 PCI DSS 준수 구현이 아닙니다.

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkSet
metadata:
  name: demo-threats
  labels:
    network-group: demo-threat
spec:
  nets:
    - 192.0.2.100/32
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: security.block-threats
spec:
  tier: security
  order: 10
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  types: [Ingress, Egress]
  ingress:
    - action: Deny
      source:
        namespaceSelector: global()
        selector: network-group == 'demo-threat'
  egress:
    - action: Deny
      destination:
        namespaceSelector: global()
        selector: network-group == 'demo-threat'
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: security.restricted-data
spec:
  tier: security
  order: 20
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  selector: data-scope == 'restricted'
  types: [Ingress]
  ingress:
    - action: Deny
      source:
        notSelector: data-scope == 'restricted'
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: platform.dns
spec:
  tier: platform
  order: 10
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  types: [Egress]
  egress:
    - action: Allow
      protocol: UDP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
---
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: application.frontend
  namespace: calico-demo
spec:
  tier: application
  order: 10
  selector: app == 'frontend'
  types: [Ingress, Egress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'gateway'
      destination:
        ports: [8080]
  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: app == 'backend'
        ports: [8080]
```

GlobalNetworkSet은 `namespaceSelector: global()`과 별도의 레이블 selector로 선택합니다. `global(label == 'value')`는 올바른 구문이 아닙니다. 플랫폼 DNS Allow는 선택된 워크로드 egress의 의도적인 최종 허용이므로 이후 application Tier에서 다시 제한하지 못합니다. 애플리케이션 정책은 선택된 frontend에만 적용하며 namespace의 모든 워크로드를 보호하지는 않습니다.

DNS 예시는 namespace·레이블을 확인한 일반 CoreDNS Pod를 전제로 합니다. NodeLocal DNSCache나 EKS Auto Mode의 노드 로컬 DNS에는 실제 resolver 경로에 맞는 규칙이 필요합니다. Pod selector를 그대로 복사하지 말고 필요한 resolver 접근과 UDP·TCP 질의를 모두 검증하세요.

### Tier RBAC 통합

Calico Tier RBAC은 `tier.networkpolicies`·`tier.globalnetworkpolicies`라는 pseudo-resource와 해당 Tier의 `get` 권한을 사용합니다. Calico authorizer가 `application.*` 같은 합성 이름을 명시적으로 검사합니다. 일반 `networkpolicies`에 적용되는 Kubernetes `resourceNames` 와일드카드가 아닙니다.

다음 완전한 binding 예시는 서비스 계정 하나에 calico-demo namespace·application Tier의 정책 편집을 허용합니다. Tier 생성·재정렬이나 전역 정책 관리 권한은 부여하지 않습니다.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: policy-editor
  namespace: calico-demo
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: demo-get-application-tier
rules:
  - apiGroups: ["projectcalico.org"]
    resources: ["tiers"]
    resourceNames: ["application"]
    verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: demo-get-application-tier
subjects:
  - kind: ServiceAccount
    name: policy-editor
    namespace: calico-demo
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: demo-get-application-tier
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: demo-edit-application-policies
  namespace: calico-demo
rules:
  - apiGroups: ["projectcalico.org"]
    resources: ["tier.networkpolicies"]
    resourceNames: ["application.*"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: demo-edit-application-policies
  namespace: calico-demo
subjects:
  - kind: ServiceAccount
    name: policy-editor
    namespace: calico-demo
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: demo-edit-application-policies
```

전역 정책 편집은 의도한 범위의 ClusterRole/ClusterRoleBinding에서 `tier.globalnetworkpolicies`로 별도 부여합니다. Tier를 조회할 `get`과 Tier 순서를 수정할 권한은 구분하세요.

예시는 표준 Calico aggregated API 서버를 전제로 합니다. native v3 CRD의 Tier 권한은 admission webhook이 create/update/delete에 적용하며 GET/LIST/WATCH는 제한하지 못하므로 같은 읽기 격리를 보장하지 않습니다. 일반 `kubectl auth can-i`만으로 Calico의 복합 Tier 권한을 검증할 수 없습니다. 더 넓은 binding이 없는 테스트 주체로 허용·거부되어야 하는 실제 요청을 격리 환경에서 확인하세요. Kubernetes RBAC은 합집합이므로 기존 광범위한 권한이 제한을 무력화할 수 있습니다.

## FQDN 기반 Egress 정책

Open Source 3.32 CRD에는 `destination.domains`와 Felix `dnsTrustedServers` 필드가 없습니다. `policySyncPathPrefix`는 애플리케이션 계층 통합에서 사용하는 policy-sync 경로이며 이를 설정해도 Open Source에 DNS 도메인 정책이 추가되지는 않습니다.

Calico Enterprise 3.23은 **egress Allow** 규칙의 도메인 매칭을 문서화합니다. 신뢰한 DNS의 A/AAAA/CNAME 응답에서 학습한 목적지 IP에 정책을 적용합니다. HTTPS 호스트 인증이 아니므로 공유 목적지 IP와 애플리케이션 인증도 별도로 고려해야 합니다. 클러스터 내부 서비스에는 워크로드·Service selector를 사용하세요.

다음 상용 예시는 해당 기능, 신뢰할 resolver, 앞선 최종 Allow가 없는 평가 경로를 전제로 합니다. 규칙마다 `destination` map은 하나만 사용합니다. YAML 키를 중복하면 도메인 제한이 사라질 수 있습니다.

```yaml
# Calico Enterprise 3.23 example; NOT an Open Source 3.32 resource.
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: allow-approved-domains
  namespace: calico-demo
spec:
  selector: app == 'external-api-client'
  types: [Egress]
  egress:
    - action: Allow
      protocol: UDP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      protocol: TCP
      destination:
        domains:
          - api.github.com
          - "*.example.com"
        ports: [443]
```

문서용 도메인은 실제 승인한 도메인으로 바꾸세요. `*.example.com`은 `api.example.com`과 `deep.api.example.com`을 모두 매칭하지만 최상위 `example.com`은 매칭하지 않습니다. 와일드카드는 구성요소 전체를 차지해야 하고 하나만 지원합니다. Inline DNS 정책 모드는 앞쪽 와일드카드를 지원하며 중간 위치 패턴은 해당 패턴을 지원하는 별도 모드가 필요합니다. `*.amazonaws.com` 같은 넓은 접미사는 AWS 계정·IAM 경계가 아닙니다.

실제 resolver의 UDP·TCP 접근과 trusted DNS IP 구성을 함께 확인하세요. 노드 로컬 resolver에는 배포별 설정이 필요합니다. 상용 가이드는 egress-gateway Pod의 egress hook에서 도메인 정책을 지원하지 않는다고 명시합니다. 노드 단위 DNS 캐시 때문에 매칭이 없거나 간헐적일 수 있기 때문입니다.

Open Source에서는 자체 애플리케이션 권한 검사를 갖춘 egress proxy/gateway나 관리되는 IP/CIDR NetworkSet을 필요에 맞게 사용합니다. 한 번 조회한 DNS IP를 지속적인 도메인 정책의 대체물로 취급하지 마세요.

## L7 (HTTP) 정책

Calico Open Source 3.32도 문서화된 **Istio + Dikastes** 통합으로 HTTP 정책을 지원합니다. 임의의 Envoy를 설치하거나 일반 CNI 정책에 `http` 필드만 추가해도 L7 적용이 활성화되는 것은 아닙니다.

Felix Policy Sync API, Calico CSI socket mount, Dikastes injection, 해당 트래픽 경로의 Envoy external authorization이 필요합니다. 현재 통합 가이드는 Kubernetes native-sidecar 기반 Istio injection과 Istio 1.28.1을 권장하지만 모든 새 Istio 버전과의 호환성을 보장하지는 않습니다. 운영 조합은 유지 중인 [Istio 설치 가이드](../../service-mesh/istio/01-installation.md), 양쪽 지원 기간, 실제 통합을 함께 확인하세요. 여기서는 통합 배포를 실행하지 않았습니다.

아래는 통합을 이미 구성한 워크로드의 **ingress Allow** 예시입니다. HTTPS 메서드·경로를 검사하려면 적용 proxy가 TLS 종료 후 HTTP 요청을 볼 수 있어야 합니다. Pod 레이블은 워크로드 식별자이지 최종 사용자 인증이 아닙니다. 신뢰하는 워크로드 identity/mTLS 경로와 DNS·Istio 제어 평면에 필요한 연결을 구성하고, 허용·거부 요청 및 proxy·인가 서비스 장애 동작을 확인해야 합니다.

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: l7-api-policy
  namespace: calico-demo
spec:
  selector: app == 'api-server'

  ingress:
    # GET 요청만 허용 (읽기 전용)
    - action: Allow
      protocol: TCP
      source:
        selector: role == 'reader'
      destination:
        ports:
          - 8080
      http:
        methods:
          - GET
          - HEAD
        paths:
          - prefix: "/api/v1/read"

    # admin 레이블 워크로드에 열거한 메서드 허용
    - action: Allow
      protocol: TCP
      source:
        selector: role == 'admin'
      destination:
        ports:
          - 8080
      http:
        methods:
          - GET
          - POST
          - PUT
          - DELETE
          - PATCH
        paths:
          - prefix: "/api/"

    # /health 엔드포인트는 모두 허용
    - action: Allow
      protocol: TCP
      destination:
        ports:
          - 8080
      http:
        methods:
          - GET
        paths:
          - exact: "/health"
          - exact: "/ready"
```

## HostEndpoint 보호

HostEndpoint는 Calico가 관리하는 노드 인터페이스를 나타냅니다. 생성 즉시 호스트 연결에 영향을 줄 수 있습니다. `defaultEndpointToHostAction`은 워크로드에서 로컬 호스트로 가는 동작을 제어하며 HostEndpoint를 만들지 않습니다. `Installation.calicoNetwork.hostPorts`도 hostPort 지원 설정이지 자동 호스트 보호 설정이 아닙니다.

### 수동 HostEndpoint와 정책

다음은 **완전한 호스트 방화벽이 아닌 필드 예시**입니다. 자체 관리 테스트 worker `demo-worker`의 주소 `10.0.1.10`, bastion `10.0.0.100`, 제어 평면 소스 `10.0.1.5`, 인터페이스 `eth0`을 가정합니다. 확인한 실제 값으로 바꾸고 HostEndpoint 생성 전에 관리·DNS·DHCP·BGP·API·상태 검사·egress 규칙을 모두 준비하세요. EKS가 관리하는 제어 평면 노드의 구성을 의미하지 않습니다.

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default.demo-worker-ingress
spec:
  order: 100
  selector: host-demo == 'true' && !has(projectcalico.org/namespace)
  types: [Ingress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        nets: [10.0.0.100/32]
      destination:
        ports: [22]
    - action: Allow
      protocol: TCP
      source:
        nets: [10.0.1.5/32]
      destination:
        ports: [10250]
---
apiVersion: projectcalico.org/v3
kind: HostEndpoint
metadata:
  name: demo-worker-eth0
  labels:
    host-demo: "true"
spec:
  node: demo-worker
  interfaceName: eth0
  expectedIPs: [10.0.1.10]
```

kubelet 규칙은 worker의 인증된 10250 endpoint를 대상으로 합니다. 이전의 인증 없는 10255 read-only 포트를 기본 요구 사항처럼 열지 마세요. 예시는 ingress만 정의하므로 수동 HostEndpoint에 egress 정책·Profile이 없으면 호스트에서 시작하는 트래픽이 거부될 수 있습니다. 실제 연결 baseline을 먼저 완성해야 합니다.

Calico 기본 failsafe에는 inbound TCP 22 등 연결 유지 포트가 포함됩니다. 따라서 위 SSH 규칙만으로 bastion 전용 접근을 보장하지 않습니다. failsafe 변경 전 실제 목록과 검증한 복구 경로를 확인하고 무조건 빈 목록으로 바꾸지 마세요.

### 자동 HostEndpoint

자동 생성은 node controller의 `KubeControllersConfiguration.spec.controllers.node.hostEndpoint.autoCreate`가 제어합니다. 다른 controller 설정을 보존하도록 merge patch를 사용합니다.

```bash
kubectl get kubecontrollersconfiguration.projectcalico.org default -o yaml
# Apply only after reviewing existing host endpoints and global policies.
kubectl patch kubecontrollersconfiguration.projectcalico.org default --type=merge \
  -p '{"spec":{"controllers":{"node":{"hostEndpoint":{"autoCreate":"Enabled"}}}}}'
```

적합한 모든 노드에 영향을 줄 수 있습니다. 자동 endpoint에는 일반적으로 default-allow Profile이 있지만 일치하는 정책 Deny를 덮어쓰지 않습니다. custom template과 `createDefaultHostEndpoint`로 생성 범위를 조정할 수 있으나 기존 배포에서 변경하기 전 endpoint·정책을 확인해야 합니다.

### 로컬·전달 트래픽 구분

일반 host 정책의 `applyOnForward` 기본값은 false입니다. true이면 전달 트래픽에도 적용하지만 관련 워크로드 정책 역시 통과해야 합니다. 해당 endpoint·방향을 선택하는 forward 정책이 없으면 전달 트래픽은 기본 허용하고, 선택하는 정책이 있는데 허용 규칙이 없으면 거부합니다. 호스트에서 종료되는 트래픽에는 별도의 기본 거부 동작과 Profile·failsafe가 적용됩니다.

## DoNotTrack / PreDNAT 정책

다음은 Linux 호스트 정책 패턴입니다. HostEndpoint에 적용하며 일반 Pod를 선택해 conntrack을 끄는 설정이 아닙니다. 사용한 데이터 평면의 지원을 확인하세요. `doNotTrack`과 `preDNAT`을 동시에 true로 설정할 수 없고 둘 중 하나라도 true이면 `applyOnForward: true`가 필요합니다.

### DoNotTrack

untracked Allow는 매칭 트래픽의 연결 추적을 생략합니다. 항상 성능이 향상되는 것은 아니며 conntrack이 필요한 Service/NAT 경로와 충돌할 수 있습니다. 요청·응답 규칙을 모두 정의해야 합니다. 아래는 테스트 호스트의 DNS 프로세스가 신뢰한 클라이언트 서브넷에 직접 서비스하는 가정입니다.

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default.demo-untracked-dns
spec:
  selector: host-demo == 'true' && !has(projectcalico.org/namespace)
  order: 10
  types: [Ingress, Egress]
  doNotTrack: true
  applyOnForward: true
  ingress:
    - action: Allow
      protocol: UDP
      source:
        nets: [10.0.0.0/24]
      destination:
        ports: [53]
    - action: Allow
      protocol: TCP
      source:
        nets: [10.0.0.0/24]
      destination:
        ports: [53]
  egress:
    - action: Allow
      protocol: UDP
      source:
        ports: [53]
      destination:
        nets: [10.0.0.0/24]
    - action: Allow
      protocol: TCP
      source:
        ports: [53]
      destination:
        nets: [10.0.0.0/24]
```

일반 endpoint 정책과 달리 untracked 단계에서 매칭하지 않아도 Tier 끝에서 기본 drop하지 않으며 이후 tracked 정책이 적용될 수 있습니다. 이 예시는 호스트 전체의 암묵적 deny-all 방화벽이 아닙니다.

### PreDNAT

pre-DNAT 정책은 DNAT 전 원래 목적지 IP·포트를 봅니다. ingress만 정의할 수 있고 허용된 응답에는 일반 conntrack을 사용합니다. 다음은 선택한 호스트 경로의 TCP NodePort 30080 하나를 보호하는 예시입니다.

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default.demo-nodeport
spec:
  selector: host-demo == 'true' && !has(projectcalico.org/namespace)
  order: 20
  types: [Ingress]
  preDNAT: true
  applyOnForward: true
  ingress:
    - action: Allow
      protocol: TCP
      source:
        nets: [10.0.0.0/24]
      destination:
        ports: [30080]
    - action: Deny
      protocol: TCP
      destination:
        ports: [30080]
```

pre-DNAT 단계 자체에는 기본 drop이 없습니다. 미일치 트래픽은 뒤의 host/workload 정책으로 진행합니다. 두 번째 명시적 규칙은 해당 NodePort의 비신뢰 소스를 거부하며 다른 포트는 예시 범위 밖입니다. 해당 호스트 NodePort를 거치지 않고 Pod로 직접 가는 경로도 이 규칙의 대상이 아닙니다.

## 정책 디버깅

실제 레이블·namespace·Service endpoint·모든 적용 Tier·양쪽 방향을 확인합니다. 표준 Calico API 서버는 Tier selector 없는 목록을 `default` Tier로 제한할 수 있습니다. `-A`는 모든 namespace라는 뜻이며 모든 Tier까지 자동 조회한다는 뜻이 아닙니다.

```bash
kubectl get networkpolicies.networking.k8s.io -n calico-demo -o yaml
kubectl get tiers.projectcalico.org -o yaml
for CALICO_TIER in $(kubectl get tiers.projectcalico.org -o jsonpath='{.items[*].metadata.name}'); do
  kubectl get networkpolicies.projectcalico.org -n calico-demo \
    -l "projectcalico.org/tier=$CALICO_TIER" -o yaml
  kubectl get globalnetworkpolicies.projectcalico.org \
    -l "projectcalico.org/tier=$CALICO_TIER" -o yaml
done
calicoctl get workloadendpoint -n calico-demo \
  --selector="app == 'frontend'" -o yaml
```

```bash
CALICO_NAMESPACE=calico-system
CALICO_NODE=demo-worker
CALICO_POD="$(kubectl -n "$CALICO_NAMESPACE" get pods -l k8s-app=calico-node \
  --field-selector "spec.nodeName=$CALICO_NODE" -o jsonpath='{.items[0].metadata.name}')"
test -n "$CALICO_POD"
kubectl -n "$CALICO_NAMESPACE" logs "$CALICO_POD" -c calico-node --tail=200
kubectl -n "$CALICO_NAMESPACE" exec "$CALICO_POD" -c calico-node -- \
  calico-node -felix-ready
```

```bash
# Assumes named, ready test Pods and an nc binary in the client image.
TARGET_POD=backend-test
TARGET_IP="$(kubectl -n calico-demo get pod "$TARGET_POD" -o jsonpath='{.status.podIP}')"
test -n "$TARGET_IP"
kubectl -n calico-demo exec frontend-client -- nc -z -w 3 "$TARGET_IP" 8080
```

`calico-node -felix-ready`는 준비 상태 검사이며 정책 trace나 패킷별 평가 시간 측정 명령이 아닙니다. 릴리스된 Open Source `calicoctl`에는 이전 예시의 `policy-trace` 명령이 없습니다. endpoint 조회나 정책 텍스트 검색만으로 전체 유효 정책을 계산하지도 않습니다.

허용 클라이언트, 비신뢰 클라이언트, 잘못된 포트, 다른 namespace, resolver 접근을 **새 연결**로 확인하세요. 서버 목적지 포트와 클라이언트의 임시 소스 포트를 구분합니다. Pod IP와 Service 주소를 별도로 검사하면 정책과 endpoint/NAT/전달 문제를 구분할 수 있으므로 kube-proxy나 대체 구현도 관련이 있습니다.

iptables 데이터 평면은 대상 노드·네트워크 namespace의 실제 `cali-` 체인을 확인합니다. 예시 hash는 실제 체인 이름이 아닙니다. iptables Log action은 호스트 커널 로그로 출력하며 Felix stdout은 주로 컴포넌트·컨트롤러 진단입니다. stdout 메시지 부재나 0 카운터만으로 모든 경로에서 정책이 사용되지 않았다고 판단하지 마세요. eBPF/nftables에는 해당 backend 진단이 필요하며 `tc filter show`만으로 전체 정책 verdict를 설명할 수 없습니다.

### 적용 전 staged policy

Open Source 3.32에는 `StagedNetworkPolicy`, `StagedGlobalNetworkPolicy`, `StagedKubernetesNetworkPolicy`가 있습니다. staged 리소스는 패킷 결정을 강제하지 않습니다. flow-log/Whisker 경로를 구성했다면 `policies.pending`에서 관찰한 영향을 확인할 수 있습니다.

```yaml
apiVersion: projectcalico.org/v3
kind: StagedNetworkPolicy
metadata:
  name: default.preview-backend-egress
  namespace: calico-demo
spec:
  tier: default
  order: 100
  selector: app == 'frontend'
  types: [Egress]
  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: app == 'backend'
        ports: [8080]
```

이 preview는 backend 연결만 포함합니다. 실제 enforced 정책을 만들기 전에 DNS나 다른 필수 연결이 거부되는지 확인하세요. 관찰된 트래픽이 없다는 사실만으로 의존성이 불필요하다고 단정하지 않습니다. `action: Log`만 사용해도 평가가 계속되어 마지막에 거부될 수 있으므로 보편적인 audit-only 모드는 아닙니다.

## 일반적인 정책 패턴

### Frontend → Backend → Database

표시한 레이블과 listener를 가진 준비된 워크로드를 전제로 합니다. 서버 포트는 **destination** port이며 `source.ports: [8080]`을 사용하면 임시 소스 포트를 쓰는 클라이언트가 보통 거부됩니다. 숫자 포트 규칙에는 TCP를 지정합니다. gateway는 demo 애플리케이션이며 특정 ingress controller의 실제 레이블을 가정하지 않습니다.

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: default.frontend
  namespace: calico-demo
spec:
  order: 100
  selector: app == 'frontend'
  types: [Ingress, Egress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'gateway'
      destination:
        ports: [8080]
  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: app == 'backend'
        ports: [8080]
---
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: default.backend
  namespace: calico-demo
spec:
  order: 100
  selector: app == 'backend'
  types: [Ingress, Egress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'frontend'
      destination:
        ports: [8080]
  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: app == 'database'
        ports: [5432]
---
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: default.database
  namespace: calico-demo
spec:
  order: 100
  selector: app == 'database'
  types: [Ingress, Egress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'backend'
      destination:
        ports: [5432]
  egress: []
```

DNS가 필요한 클라이언트에는 앞의 필수 egress 패턴과 해당 레이블로 resolver 접근을 별도 허용하세요. 단순화한 데이터베이스는 새 egress 연결을 시작하지 않으며 상태 추적된 응답은 가능합니다. 백업·복제·외부 의존성은 별도 규칙이 필요합니다.

### 테넌트 격리

Calico selector는 `$(namespace.tenant)`, `${namespace.labels.tenant}`, `${namespace.name}`를 동적으로 치환하지 않습니다. 테넌트 값을 명시한 정책을 각각 생성하거나 같은 namespace 격리에는 namespaced 정책을 사용하세요.

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default.team-a-isolation
spec:
  order: 500
  namespaceSelector: tenant == 'team-a'
  types: [Ingress, Egress]
  ingress:
    - action: Allow
      source:
        namespaceSelector: tenant == 'team-a'
  egress:
    - action: Allow
      destination:
        namespaceSelector: tenant == 'team-a'
    - action: Allow
      protocol: UDP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
```

같은 레이블의 여러 namespace를 포함하여 team-a 내부 트래픽을 모두 허용하는 예시입니다. namespace 레이블·정책 편집 권한을 통제해야 하며 앞선 Allow가 격리 의도를 무력화할 수 있습니다. 다른 테넌트와 레이블 없는 namespace도 음성 테스트에 포함하세요.

### 같은 namespace와 공유 서비스

namespaced 정책의 entity selector에서 namespace selector를 생략하면 `calico-demo` 안으로 범위가 제한됩니다. 이 예시는 제한적인 마이크로서비스 패턴의 대안이며 위에 추가로 겹쳐 적용하는 정책이 아닙니다.

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: default.namespace-and-shared
  namespace: calico-demo
spec:
  order: 200
  selector: all()
  types: [Ingress, Egress]
  ingress:
    - action: Allow
      source:
        selector: all()
  egress:
    - action: Allow
      destination:
        selector: all()
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'logging'
        selector: app == 'log-receiver'
        ports: [24224]
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'auth'
        selector: app == 'identity-provider'
        ports: [8080]
```

필요한 resolver 규칙은 별도 추가하고 목적지 쪽 정책도 클라이언트를 허용하는지 확인하세요. 로깅 포트·인증 서비스 레이블은 demo 가정이므로 실제 수신 프로토콜·포트·애플리케이션 인증을 검증해야 합니다.

### Open Source egress 제어

주소 계약이 있는 외부 서비스는 NetworkSet에서 승인한 주소를 관리할 수 있습니다. 아래 IP는 문서용이며 실제 API 주소나 영구적인 DNS 조회 결과가 아닙니다.

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkSet
metadata:
  name: approved-api-ips
  namespace: calico-demo
  labels:
    destination-group: approved-api
spec:
  nets: [203.0.113.10/32]
---
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: default.approved-api-egress
  namespace: calico-demo
spec:
  order: 100
  selector: app == 'external-api-client'
  types: [Egress]
  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: destination-group == 'approved-api'
        ports: [443]
```

이름을 조회하는 애플리케이션에는 앞의 DNS 규칙을 별도로 적용합니다. 동적 외부 서비스에는 적절한 권한 검사를 갖춘 proxy나 별도 문서화한 상용 도메인 정책을 사용하세요. RFC1918 전체 허용은 “이 클러스터만” 허용한다는 뜻이 아니며 다른 사설 네트워크까지 열 수 있습니다.

### 보안 설계의 일부인 기본 거부

범위를 제한한 default-deny와 필요한 연결, 레이블·RBAC 소유권, 애플리케이션 인증을 함께 구성하세요. 네트워크 분할만으로 전체 zero-trust나 규정 준수를 구현한 것은 아닙니다. staged policy와 음성 테스트를 거쳐 적용해야 합니다.

## 정책 성능 최적화

정책 수만으로 처리 용량을 판단할 수 없습니다. endpoint 수, selector 변경, 규칙 구조, 활성 연결, 업데이트 빈도, 데이터 평면이 비용에 영향을 줍니다. “1,000개 이상은 매우 느림” 같은 기존 표에는 측정 환경이나 원자료가 없었습니다.

동등 비교, 집합 membership, 레이블 존재 selector는 모두 최적화 대상이 될 수 있습니다. 객체 수를 줄이려고 허용 범위를 넓히는 정책 통합을 하지 마세요. 관리되는 NetworkSet을 재사용하고 로그량을 제한하며 대표 변경 부하에서 수렴 시간을 측정합니다.

readiness 검사, “Policy sync” 검색, `iptables -L` 출력 줄 수는 정책 평가 지연을 측정하지 않습니다. 문서화된 Felix metrics endpoint를 활성화·수집하고 TYPE/HELP·단위를 확인하여 제어한 워크로드의 정책 반영 시간과 연결하세요.

```bash
# After enabling the documented Felix metrics endpoint through its config owner:
kubectl -n "$CALICO_NAMESPACE" port-forward "pod/$CALICO_POD" 9091:9091
```

```bash
# In another terminal while the localhost port-forward remains active:
curl --fail --silent --show-error http://127.0.0.1:9091/metrics
```

Felix metrics는 기본 비활성화이므로 설정 소유자를 통해 `prometheusMetricsEnabled`를 먼저 활성화해야 합니다. 대상 노드에서 endpoint에 접근 가능해야 합니다. 위 명령은 메트릭 탐색이며 발표한 성능 측정 결과가 아닙니다. 정책 변경 중 허용·거부 경로를 검사하고 Calico/Kubernetes/kernel 버전, 데이터 평면, 토폴로지, 부하, 측정값을 함께 보존하세요.

## 운영 원칙

1. 격리 namespace에서 필수 연결을 파악하고 staged policy를 거쳐 적용합니다.
2. Pod·namespace 레이블과 정책 편집 RBAC을 권한 경계의 일부로 관리합니다.
3. Tier 추가·재정렬 시 최종 Allow와 Pass의 영향을 재검토합니다.
4. 호스트 관리·failsafe·Service/DNS 전제를 애플리케이션 규칙과 구분합니다.
5. 네트워크 분할과 워크로드·최종 사용자 인증을 함께 사용하며 IP 규칙만으로 모든 SSRF·규정 준수 문제를 해결했다고 주장하지 않습니다.

***

## 참고 자료

* [Calico NetworkPolicy API](https://docs.tigera.io/calico/latest/reference/resources/networkpolicy)
* [GlobalNetworkPolicy API](https://docs.tigera.io/calico/latest/reference/resources/globalnetworkpolicy)
* [Tier evaluation](https://docs.tigera.io/calico/latest/reference/resources/tier)
* [Tier RBAC](https://docs.tigera.io/calico/latest/network-policy/policy-tiers/rbac-tiered-policies)
* [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
* [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
* [Open Source Istio/Dikastes application policy](https://docs.tigera.io/calico/latest/network-policy/istio/app-layer-policy)
* [Enterprise domain policy](https://docs.tigera.io/calico-enterprise/latest/network-policy/domain-based-policy)
* [Staged policies](https://docs.tigera.io/calico/latest/network-policy/staged-network-policies)
* [Host failsafes](https://docs.tigera.io/calico/latest/reference/host-endpoints/failsafe)
* [Pre-DNAT](https://docs.tigera.io/calico/latest/reference/host-endpoints/pre-dnat)
* [Forwarded host traffic](https://docs.tigera.io/calico/latest/reference/host-endpoints/forwarded)
* [KubeControllersConfiguration](https://docs.tigera.io/calico/latest/reference/resources/kubecontrollersconfig)
* [Policy logging](https://docs.tigera.io/calico/latest/network-policy/policy-rules/log-rules)
* [Component metrics](https://docs.tigera.io/calico/latest/operations/monitor/monitor-component-metrics)

[이전: Part 4 - BGP 아키텍처 심화](04-bgp-deep-dive.md) | [다음: Part 6 - eBPF 데이터플레인](06-ebpf-dataplane.md) | [메인 페이지로 돌아가기](./README.md)

* [Calico eBPF protocol support](https://docs.tigera.io/calico/latest/operations/ebpf/install)
