# 네트워크 정책 퀴즈

> **마지막 업데이트**: 2026년 9월 13일

이 퀴즈는 Kubernetes 네트워크 정책, Cilium 네트워크 정책, 마이크로세그멘테이션에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. Kubernetes NetworkPolicy의 기본 동작은?

A. 모든 트래픽 차단
B. 해당 방향에 선택 정책이 없으면 NetworkPolicy로 격리되지 않음
C. 인바운드만 차단
D. 아웃바운드만 차단

<details>
<summary>정답 보기</summary>

**정답: B. 해당 방향에 선택 정책이 없으면 NetworkPolicy로 격리되지 않음**

**설명:**
Ingress·egress를 따로 평가합니다. 특정 방향의 선택 정책이 없으면 그 방향은 NetworkPolicy로 격리되지 않지만 CNI/route/SG/NACL이나 다른 정책이 연결을 막을 수 있습니다. Ingress 전용 정책은 egress까지 격리하지 않습니다. Pod 간 연결은 출발지 egress와 목적지 ingress를 모두 만족해야 합니다.

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
B. spec.ingress[].toPorts[].rules.http
C. spec.rules.http
D. spec.layer7.http

<details>
<summary>정답 보기</summary>

**정답: B. spec.ingress[].toPorts[].rules.http**

**설명:**
HTTP 규칙은 ingress 규칙의 `toPorts[].rules.http` 아래에 있으며 egress 규칙에도 사용할 수 있습니다. 지원되는 L7 proxy 경로가 필요하고 end-to-end TLS를 자동 해독하거나 사용자 입력 역할/API-key 헤더를 인증으로 바꾸지 않습니다. Cilium의 AWS VPC CNI chaining에는 L7 제한이 문서화되어 있습니다.

</details>

<span id="_5-기본-거부-정책을-구현하는-올바른-networkpolicy는"></span>

### 5. 네임스페이스 전체의 양쪽 방향 기본 거부 기준선을 만드는 방법은?

A. policyTypes에 Ingress만 지정
B. podSelector를 빈 값으로, policyTypes에 Ingress와 Egress 지정
C. ingress와 egress 규칙을 비워둠
D. B와 C 모두

<details>
<summary>정답 보기</summary>

**정답: D. B와 C 모두**

**설명:**
네임스페이스 전체의 **양쪽 방향** 기준선에는 B와 C를 함께 사용합니다. 빈 셀렉터는 정책 자신의 네임스페이스 Pod 전체를 고르고 Ingress/Egress를 명시한 뒤 허용 규칙을 비우면 양쪽을 격리합니다. 다른 Kubernetes NetworkPolicy가 허용을 추가할 수 있으며 기준선이 이를 덮어쓰지는 않습니다. 의도에 따라 ingress 전용 기준선도 가능합니다.

</details>

### 6. CiliumClusterwideNetworkPolicy의 특징은?

A. 범위 선택을 위해 metadata.namespace가 필수
B. 클러스터 범위 리소스이며 endpoint selector로 대상을 제한
C. 외부 트래픽만 제어
D. L7 정책만 지원

<details>
<summary>정답 보기</summary>

**정답: B. 클러스터 범위 리소스이며 endpoint selector로 대상을 제한**

**설명:**
CiliumClusterwideNetworkPolicy는 네임스페이스 리소스가 아닙니다. endpoint selector로 여러 네임스페이스 또는 특정 네임스페이스·앱만 선택할 수 있습니다. 클러스터 범위가 모든 엔드포인트 자동 선택이나 넓은 `cluster`/`world` 허용을 default-deny로 만든다는 뜻은 아닙니다.

</details>

### 7. NetworkPolicy에서 특정 네임스페이스의 모든 Pod를 허용하는 방법은?

A. namespaceSelector만 사용
B. podSelector만 사용
C. namespaceSelector와 app=api를 요구하는 podSelector 조합
D. namespace 필드 사용

<details>
<summary>정답 보기</summary>

**정답: A. namespaceSelector만 사용**

**설명:**
`namespaceSelector.matchLabels.kubernetes.io/metadata.name: monitoring`으로 해당 네임스페이스의 Pod 전체를 선택합니다. 같은 peer에 **빈** podSelector를 추가해도 전체 선택이지만 C는 `app=api`만 선택합니다. 한 peer의 두 셀렉터는 AND, 별도 peer 항목은 OR이며 사용자 정의 `name` 레이블은 자동 생성되지 않습니다.

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
`toFQDNs`는 DNS에서 학습한 IP와 지정 포트 규칙을 사용합니다. 실제 resolver 경로와 필요한 질의를 별도로 허용하며 UDP뿐 아니라 TCP53도 고려합니다. 캐시·TTL·검색 접미사·공유 목적지 IP와 TLS/앱 권한 확인은 여전히 필요합니다. 도메인 일치만으로 SaaS 테넌트 identity를 인증하지 않습니다.

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
같은 Pod의 컨테이너는 네트워크 네임스페이스를 공유하므로 localhost 통신은 일반 Kubernetes NetworkPolicy 집행 범위 밖입니다. 노드·hostNetwork 처리와 TCP/UDP/SCTP 외 프로토콜에는 구현별 제한이 있습니다. Pod 정책만으로 호스트 전체 격리를 추론하지 않습니다.

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
레이블 기반 엔드포인트 정책은 일시적인 Pod IP를 하드코딩하지 않아도 됩니다. datapath가 현재 엔드포인트와 관련 레이블 집합의 security identity를 연결합니다. 숫자 identity는 재할당될 수 있으며 영구 앱 식별자가 아닙니다. 레이블 변경·네임스페이스/클러스터 문맥·전파도 고려해야 합니다.

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
C는 백엔드의 앱 경로인 frontend ingress와 DB egress를 뜻하며 검토한 포트로 제한합니다. frontend egress·DB ingress와 필요한 DNS·health·monitoring 경로도 함께 허용해야 합니다. 반대편의 default-deny가 연결을 막을 수 있기 때문입니다. 허용된 연결의 응답 트래픽은 암묵적으로 허용됩니다.

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
`except`는 해당 ipBlock 허용 규칙에서 CIDR을 제외합니다. 전역 deny가 아니므로 다른 선택 정책이 제외 주소를 허용할 수 있습니다. 주소 변환으로 플러그인이 평가하는 IP가 달라질 수 있어 실제 CNI·로드밸런서/Service 경로를 확인합니다.

</details>

---

[네트워크 정책 가이드](../../security/04-network-policies.md)
