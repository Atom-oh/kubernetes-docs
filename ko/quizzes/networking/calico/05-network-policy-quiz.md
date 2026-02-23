# Calico Network Policy 퀴즈

> **관련 문서**: [Calico Network Policy](../../../networking/calico/05-network-policy.md)
> **마지막 업데이트**: 2026년 2월 22일

## 퀴즈

1. Kubernetes 표준 NetworkPolicy의 한계점이 아닌 것은?
   - A) L7(애플리케이션 계층) 정책 미지원
   - B) 클러스터 전역 정책 미지원
   - C) L3/L4 정책 미지원
   - D) FQDN 기반 정책 미지원

<details>
<summary>정답 보기</summary>

**정답: C) L3/L4 정책 미지원**

**설명:**
Kubernetes 표준 NetworkPolicy는 L3/L4(IP, Port) 정책을 지원합니다. 한계점은 L7 정책, 클러스터 전역 정책, FQDN 기반 정책, 명시적 Deny 규칙 등을 지원하지 않는 것입니다.

</details>

2. Calico NetworkPolicy의 selector 문법으로 올바른 것은?
   - A) matchLabels: app: frontend
   - B) app == 'frontend'
   - C) labels.app = frontend
   - D) selector: app/frontend

<details>
<summary>정답 보기</summary>

**정답: B) app == 'frontend'**

**설명:**
Calico NetworkPolicy는 자체 selector 문법을 사용합니다. `app == 'frontend'`와 같은 표현식 문법을 사용하며, `&&`, `||`, `!`, `has()` 등의 연산자도 지원합니다.

</details>

3. Calico NetworkPolicy의 action 유형이 아닌 것은?
   - A) Allow
   - B) Deny
   - C) Log
   - D) Drop

<details>
<summary>정답 보기</summary>

**정답: D) Drop**

**설명:**
Calico NetworkPolicy의 action 유형은 Allow, Deny, Log, Pass입니다. Drop은 유효한 action이 아닙니다. Deny가 패킷을 드롭하는 역할을 합니다.

</details>

4. GlobalNetworkPolicy와 NetworkPolicy의 주요 차이점은?
   - A) GlobalNetworkPolicy는 더 빠름
   - B) GlobalNetworkPolicy는 네임스페이스에 속하지 않고 클러스터 전체에 적용
   - C) NetworkPolicy는 egress만 지원
   - D) GlobalNetworkPolicy는 Kubernetes 표준

<details>
<summary>정답 보기</summary>

**정답: B) GlobalNetworkPolicy는 네임스페이스에 속하지 않고 클러스터 전체에 적용**

**설명:**
NetworkPolicy는 특정 네임스페이스에 속하고 해당 네임스페이스의 Pod에만 적용됩니다. GlobalNetworkPolicy는 네임스페이스에 속하지 않으며 클러스터 전체의 Pod에 적용할 수 있습니다.

</details>

5. NetworkSet의 용도는 무엇입니까?
   - A) 네트워크 인터페이스 그룹화
   - B) IP 주소 집합을 정의하여 정책에서 재사용
   - C) BGP 피어 그룹화
   - D) Pod 네트워크 설정 그룹화

<details>
<summary>정답 보기</summary>

**정답: B) IP 주소 집합을 정의하여 정책에서 재사용**

**설명:**
NetworkSet은 IP 주소나 CIDR 블록의 집합을 정의하여 레이블을 붙일 수 있습니다. 이를 통해 여러 정책에서 동일한 IP 집합을 참조하여 재사용할 수 있습니다.

</details>

6. Tier에서 order 값이 낮을수록 어떤 의미입니까?
   - A) 나중에 평가됨
   - B) 먼저 평가됨
   - C) 우선순위가 낮음
   - D) 적용 범위가 좁음

<details>
<summary>정답 보기</summary>

**정답: B) 먼저 평가됨**

**설명:**
Tier의 order 값이 낮을수록 먼저 평가됩니다. 예를 들어, order: 100인 Security Tier가 order: 200인 Platform Tier보다 먼저 평가됩니다.

</details>

7. Pass action의 의미는 무엇입니까?
   - A) 패킷을 허용
   - B) 패킷을 거부
   - C) 현재 Tier에서 결정하지 않고 다음 Tier로 전달
   - D) 패킷을 로깅 후 허용

<details>
<summary>정답 보기</summary>

**정답: C) 현재 Tier에서 결정하지 않고 다음 Tier로 전달**

**설명:**
Pass action은 현재 Tier에서 Allow/Deny 결정을 내리지 않고 다음 Tier의 정책으로 평가를 넘깁니다. 이를 통해 계층적 정책 구조를 구현할 수 있습니다.

</details>

8. FQDN 기반 정책의 동작 방식으로 올바른 것은?
   - A) DNS 쿼리를 차단
   - B) DNS 응답을 모니터링하여 해당 IP로의 트래픽 허용/거부
   - C) 호스트 파일을 수정
   - D) DNS 서버로 직접 연결

<details>
<summary>정답 보기</summary>

**정답: B) DNS 응답을 모니터링하여 해당 IP로의 트래픽 허용/거부**

**설명:**
FQDN 기반 정책은 DNS 응답을 모니터링하여 도메인에 해당하는 IP 주소를 학습하고, 해당 IP로의 트래픽을 허용하거나 거부합니다. 예: `domains: ["*.amazonaws.com"]`

</details>

9. applyOnForward의 의미는 무엇입니까?
   - A) 정책을 Pod의 ingress에만 적용
   - B) 정책을 노드를 통과하는(forwarded) 트래픽에도 적용
   - C) 정책을 우선 적용
   - D) 정책을 즉시 적용

<details>
<summary>정답 보기</summary>

**정답: B) 정책을 노드를 통과하는(forwarded) 트래픽에도 적용**

**설명:**
applyOnForward: true를 설정하면 Host Endpoint를 통해 노드를 통과하는 트래픽에도 정책이 적용됩니다. 이는 노드가 라우터처럼 동작하는 경우 유용합니다.

</details>

10. doNotTrack 정책의 사용 사례는 무엇입니까?
    - A) 모든 트래픽 로깅 비활성화
    - B) conntrack을 우회하여 고성능 처리가 필요한 경우
    - C) Network Policy 평가 건너뛰기
    - D) DNS 트래픽 추적 비활성화

<details>
<summary>정답 보기</summary>

**정답: B) conntrack을 우회하여 고성능 처리가 필요한 경우**

**설명:**
doNotTrack 정책은 Linux conntrack(연결 추적)을 우회합니다. 고성능이 필요하고 stateless 처리가 가능한 경우(예: 대용량 로드밸런서)에 사용됩니다. 단, stateless이므로 응답 트래픽도 별도 규칙이 필요합니다.

</details>

11. preDNAT 정책의 사용 사례는 무엇입니까?
    - A) DNS 쿼리 필터링
    - B) NodePort/LoadBalancer로 들어오는 트래픽을 DNAT 전에 필터링
    - C) Pod egress 트래픽 필터링
    - D) DNS 응답 수정

<details>
<summary>정답 보기</summary>

**정답: B) NodePort/LoadBalancer로 들어오는 트래픽을 DNAT 전에 필터링**

**설명:**
preDNAT 정책은 Destination NAT가 적용되기 전에 트래픽을 필터링합니다. 이는 외부에서 NodePort나 LoadBalancer Service로 들어오는 트래픽의 원본 소스 IP를 기준으로 필터링할 때 유용합니다.

</details>

12. 기본 거부(default deny) 정책을 구현하는 올바른 방법은?
    - A) 빈 ingress/egress 배열을 가진 정책 생성
    - B) 규칙 없이 types에 Ingress/Egress만 지정한 정책 생성
    - C) action: DenyAll 규칙 생성
    - D) selector: none() 정책 생성

<details>
<summary>정답 보기</summary>

**정답: B) 규칙 없이 types에 Ingress/Egress만 지정한 정책 생성**

**설명:**
기본 거부 정책은 `types: [Ingress, Egress]`를 지정하되 ingress/egress 규칙을 포함하지 않는 정책을 생성합니다. 이렇게 하면 해당 Pod에 대한 모든 트래픽이 기본적으로 거부됩니다.

</details>

13. Calico NetworkPolicy의 order 필드 역할은 무엇입니까?
    - A) Tier 내에서 정책 평가 순서 결정
    - B) 정책 생성 순서 지정
    - C) 정책 적용 대상 수 제한
    - D) 정책 만료 시간 설정

<details>
<summary>정답 보기</summary>

**정답: A) Tier 내에서 정책 평가 순서 결정**

**설명:**
order 필드는 같은 Tier 내에서 정책들의 평가 순서를 결정합니다. order 값이 낮은 정책이 먼저 평가되며, 먼저 매칭되는 규칙이 적용됩니다.

</details>

14. Host Endpoint 보호의 목적은 무엇입니까?
    - A) Pod 네트워크 보호
    - B) 노드(호스트) 자체의 네트워크 인터페이스 보호
    - C) Service 엔드포인트 보호
    - D) BGP 피어 보호

<details>
<summary>정답 보기</summary>

**정답: B) 노드(호스트) 자체의 네트워크 인터페이스 보호**

**설명:**
Host Endpoint는 노드의 네트워크 인터페이스(eth0 등)를 나타내며, 이에 정책을 적용하여 노드 자체로 들어오거나 나가는 트래픽을 제어할 수 있습니다.

</details>

15. Network Policy 디버깅 시 사용하는 도구와 방법이 아닌 것은?
    - A) calicoctl get networkpolicy
    - B) calicoctl get workloadendpoint
    - C) kubectl logs로 Felix 로그 확인
    - D) kubectl exec으로 kube-proxy 상태 확인

<details>
<summary>정답 보기</summary>

**정답: D) kubectl exec으로 kube-proxy 상태 확인**

**설명:**
Network Policy 디버깅에 kube-proxy는 관련이 없습니다. Calico Network Policy 문제 해결에는 calicoctl로 정책/엔드포인트 확인, Felix 로그 확인, iptables/eBPF 규칙 확인 등을 사용합니다.

</details>
