# 네트워크 정책 퀴즈

이 퀴즈는 Kubernetes 네트워크 정책, Cilium 네트워크 정책, 마이크로세그멘테이션에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. Kubernetes NetworkPolicy의 기본 동작은?

A. 모든 트래픽 차단
B. 모든 트래픽 허용
C. 인바운드만 차단
D. 아웃바운드만 차단

<details>
<summary>정답 보기</summary>

**정답: B. 모든 트래픽 허용**

**설명:**
NetworkPolicy가 없는 경우, Kubernetes는 기본적으로 모든 Pod 간 트래픽을 허용합니다. NetworkPolicy를 생성하면 해당 정책의 podSelector에 매칭되는 Pod에 대해 "기본 거부" 동작이 활성화됩니다.

</details>

### 2. NetworkPolicy에서 특정 Pod를 선택하는 필드는?

A. selector
B. podSelector
C. matchLabels
D. targetPods

<details>
<summary>정답 보기</summary>

**정답: B. podSelector**

**설명:**
NetworkPolicy의 `spec.podSelector` 필드는 정책이 적용될 Pod를 선택합니다:
```yaml
spec:
  podSelector:
    matchLabels:
      app: web
```

빈 podSelector(`{}`)는 네임스페이스의 모든 Pod를 선택합니다.

</details>

### 3. NetworkPolicy에서 인바운드와 아웃바운드 규칙을 정의하는 필드는?

A. inbound/outbound
B. ingress/egress
C. input/output
D. incoming/outgoing

<details>
<summary>정답 보기</summary>

**정답: B. ingress/egress**

**설명:**
- **ingress**: 인바운드(들어오는) 트래픽 규칙
- **egress**: 아웃바운드(나가는) 트래픽 규칙

```yaml
spec:
  ingress:
    - from:
        - podSelector:
            matchLabels:
              role: frontend
  egress:
    - to:
        - podSelector:
            matchLabels:
              role: database
```

</details>

### 4. CiliumNetworkPolicy에서 L7 HTTP 규칙을 정의하는 위치는?

A. spec.http
B. spec.ingress.toPorts.rules.http
C. spec.rules.http
D. spec.layer7.http

<details>
<summary>정답 보기</summary>

**정답: B. spec.ingress.toPorts.rules.http**

**설명:**
CiliumNetworkPolicy의 L7 규칙은 toPorts 내의 rules 섹션에 정의됩니다:
```yaml
spec:
  ingress:
    - toPorts:
        - ports:
            - port: "80"
          rules:
            http:
              - method: GET
                path: "/api/.*"
```

</details>

### 5. 기본 거부 정책을 구현하는 올바른 NetworkPolicy는?

A. policyTypes에 Ingress만 지정
B. podSelector를 빈 값으로, policyTypes에 Ingress와 Egress 지정
C. ingress와 egress 규칙을 비워둠
D. B와 C 모두

<details>
<summary>정답 보기</summary>

**정답: D. B와 C 모두**

**설명:**
기본 거부 정책 예시:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}  # 모든 Pod 선택
  policyTypes:
    - Ingress
    - Egress
  # ingress와 egress 규칙 없음 = 모든 트래픽 차단
```

빈 podSelector는 모든 Pod를 선택하고, 규칙이 없으면 해당 트래픽 유형이 차단됩니다.

</details>

### 6. CiliumClusterwideNetworkPolicy의 특징은?

A. 특정 네임스페이스에만 적용
B. 클러스터 전체에 적용
C. 외부 트래픽만 제어
D. L7 정책만 지원

<details>
<summary>정답 보기</summary>

**정답: B. 클러스터 전체에 적용**

**설명:**
CiliumClusterwideNetworkPolicy는 네임스페이스에 관계없이 클러스터 전체에 적용되는 정책입니다. 일반적인 보안 규칙(예: 모든 네임스페이스에서 메타데이터 서비스 접근 차단)을 구현할 때 유용합니다.

</details>

### 7. NetworkPolicy에서 특정 네임스페이스의 모든 Pod를 허용하는 방법은?

A. namespaceSelector만 사용
B. podSelector만 사용
C. namespaceSelector와 빈 podSelector 조합
D. namespace 필드 사용

<details>
<summary>정답 보기</summary>

**정답: A. namespaceSelector만 사용**

**설명:**
```yaml
ingress:
  - from:
      - namespaceSelector:
          matchLabels:
            name: monitoring
```

namespaceSelector만 지정하면 해당 네임스페이스의 모든 Pod가 허용됩니다. podSelector를 함께 사용하면 해당 네임스페이스 내의 특정 Pod만 선택됩니다.

</details>

### 8. CiliumNetworkPolicy에서 FQDN 기반 이그레스 규칙을 정의하는 필드는?

A. toFQDNs
B. toDomains
C. toHosts
D. toEndpoints

<details>
<summary>정답 보기</summary>

**정답: A. toFQDNs**

**설명:**
CiliumNetworkPolicy의 toFQDNs는 DNS 이름 기반으로 이그레스 트래픽을 허용합니다:
```yaml
spec:
  egress:
    - toFQDNs:
        - matchName: "api.example.com"
        - matchPattern: "*.amazonaws.com"
      toPorts:
        - ports:
            - port: "443"
```

</details>

### 9. NetworkPolicy가 적용되지 않는 트래픽은?

A. Pod 간 트래픽
B. 동일 Pod 내 컨테이너 간 트래픽 (localhost)
C. 서비스를 통한 트래픽
D. 외부에서 들어오는 트래픽

<details>
<summary>정답 보기</summary>

**정답: B. 동일 Pod 내 컨테이너 간 트래픽 (localhost)**

**설명:**
NetworkPolicy는 Pod 간 네트워크 트래픽에 적용됩니다. 동일 Pod 내의 컨테이너 간 localhost 통신은 NetworkPolicy의 범위 밖입니다. 또한, 노드의 hostNetwork를 사용하는 Pod도 일부 제한이 있습니다.

</details>

### 10. Cilium의 Identity 기반 정책의 장점은?

A. IP 주소 변경에 영향받지 않음
B. 더 빠른 처리 속도
C. 더 적은 메모리 사용
D. DNS 조회 불필요

<details>
<summary>정답 보기</summary>

**정답: A. IP 주소 변경에 영향받지 않음**

**설명:**
Cilium Identity는 Pod의 레이블을 기반으로 생성됩니다. Pod가 재시작되어 IP가 변경되더라도 동일한 레이블을 가지면 같은 Identity를 유지합니다. 이는 IP 기반 정책의 한계를 극복합니다.

</details>

### 11. 3-tier 아키텍처에서 백엔드 계층의 올바른 네트워크 정책은?

A. 모든 트래픽 허용
B. 프론트엔드에서 인그레스만 허용
C. 프론트엔드에서 인그레스 허용, 데이터베이스로 이그레스 허용
D. 데이터베이스로 이그레스만 허용

<details>
<summary>정답 보기</summary>

**정답: C. 프론트엔드에서 인그레스 허용, 데이터베이스로 이그레스 허용**

**설명:**
3-tier 마이크로세그멘테이션에서 백엔드:
- **인그레스**: 프론트엔드 계층에서만 허용
- **이그레스**: 데이터베이스 계층으로만 허용

이는 최소 권한 원칙을 따르며, 각 계층 간의 트래픽 흐름을 명확히 제어합니다.

</details>

### 12. NetworkPolicy에서 ipBlock을 사용하여 CIDR 범위를 지정할 때, 특정 IP를 제외하는 필드는?

A. exclude
B. except
C. notIn
D. excludeCIDR

<details>
<summary>정답 보기</summary>

**정답: B. except**

**설명:**
ipBlock의 except 필드로 특정 CIDR을 제외할 수 있습니다:
```yaml
ingress:
  - from:
      - ipBlock:
          cidr: 10.0.0.0/8
          except:
            - 10.0.1.0/24
            - 10.0.2.0/24
```

이는 10.0.0.0/8 범위에서 10.0.1.0/24와 10.0.2.0/24를 제외한 트래픽을 허용합니다.

</details>
