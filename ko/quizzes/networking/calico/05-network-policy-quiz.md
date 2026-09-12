# Calico Network Policy 퀴즈

> **관련 문서**: [Calico Network Policy](../../../networking/calico/05-network-policy.md)
> **마지막 업데이트**: 2026년 9월 12일

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
표준 Kubernetes NetworkPolicy 객체는 namespace 범위의 L3/L4 허용 규칙을 지원하며 named port와 지원 플러그인의 endPort 범위도 사용할 수 있습니다. 이 객체의 제약을 새 Kubernetes 클러스터 정책 API 전체의 제약으로 확대하지 마세요. Calico Open Source HTTP 정책에는 Istio/Dikastes 적용 경로가 필요합니다.

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
Allow/Deny는 해당 endpoint·방향의 일반 정책 결정을 종료합니다. Log는 이후 평가를 계속하므로 거부될 수도 있습니다. Pass는 같은 Tier의 나머지 정책까지 건너뛰며 마지막 적용 Tier 이후에는 Profile을 평가합니다.

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
namespaced NetworkPolicy는 해당 namespace의 워크로드를 선택합니다. GlobalNetworkPolicy는 여러 namespace의 워크로드와 HostEndpoint를 선택할 수 있습니다. 전역 리소스라고 모든 endpoint가 항상 선택되는 것은 아니며 대상 범위를 명시해야 합니다.

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
NetworkSet은 레이블이 있는 IP/CIDR 집합입니다. namespaced NetworkSet과 GlobalNetworkSet은 매칭 범위가 다릅니다. 전역 집합에는 entity의 namespaceSelector: global()과 별도 selector를 사용하며 global(label-expression)은 올바른 구문이 아닙니다.

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
Tier와 같은 Tier 안의 정책을 각각 낮은 order부터 평가합니다. endpoint·방향을 선택하는 정책이 없는 Tier는 건너뜁니다. 적용되는 Tier의 미일치는 defaultAction으로 처리하며 기본은 Deny입니다. default Tier의 고정 order는 1,000,000입니다.

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
Pass는 같은 Tier 뒤에 있는 보안 규칙까지 건너뜁니다. deny-only 제한을 모두 검사한 후 위임하려면 앞선 무조건 Pass보다 Tier의 defaultAction: Pass가 적합할 수 있습니다.

</details>

8. Calico Enterprise 3.23의 FQDN egress 정책 동작으로 올바른 것은?
   - A) DNS 쿼리를 차단
   - B) DNS 응답을 모니터링하여 해당 IP로의 트래픽 허용/거부
   - C) 호스트 파일을 수정
   - D) DNS 서버로 직접 연결

<details>
<summary>정답 보기</summary>

**정답: B) DNS 응답을 모니터링하여 해당 IP로의 트래픽 허용/거부**

**설명:**
신뢰하는 DNS의 A/AAAA/CNAME 응답에서 목적지 IP를 학습하여 egress Allow에 사용합니다. Open Source 3.32 CRD에는 domains 필드가 없고 policySyncPathPrefix 설정으로 추가되지 않습니다. IP 기반 매칭이 HTTPS 호스트 인증을 의미하지는 않습니다.

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
HostEndpoint 정책의 applyOnForward: true는 전달 트래픽에도 적용합니다. doNotTrack 또는 preDNAT이면 필수입니다. 호스트의 Allow가 적용되는 워크로드 정책까지 우회하지 않습니다.

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
doNotTrack은 HostEndpoint용이며 applyOnForward: true가 필요합니다. 매칭 Allow 트래픽은 연결 추적을 생략하므로 요청·응답을 모두 허용해야 합니다. 항상 성능이 높아지는 것은 아니며 conntrack이 필요한 Service/NAT 경로와 충돌할 수 있습니다.

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
preDNAT은 DNAT 전 원래 목적지 IP·포트를 기준으로 host ingress를 평가합니다. egress 규칙을 넣을 수 없고 applyOnForward: true가 필요하며 doNotTrack과 동시에 활성화할 수 없습니다. 이 단계에서 미일치했다고 기본 drop하는 것은 아니고 뒤의 host/workload 정책이 적용됩니다.

</details>

12. 앞선 명시적 허용 이후 선택한 워크로드의 양방향 기본 거부를 지정하는 방법은?
    - A) types에 Ingress만 지정한 정책 생성
    - B) 규칙 없이 types에 Ingress/Egress만 지정한 정책 생성
    - C) action: DenyAll 규칙 생성
    - D) selector: none() 정책 생성

<details>
<summary>정답 보기</summary>

**정답: B) 규칙 없이 types에 Ingress/Egress만 지정한 정책 생성**

**설명:**
대상 namespace·워크로드와 types: [Ingress, Egress]를 명시하고 규칙을 비웁니다. order 생략 시 명시한 정책 뒤에 평가하며 앞선 최종 Allow를 덮어쓰지는 않습니다. selector: all()만 사용한 전역 예시는 HostEndpoint·시스템 트래픽까지 선택할 수 있으므로 범위를 제한해야 합니다.

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
HostEndpoint는 관리되는 호스트의 인터페이스를 나타냅니다. 수동 생성 시 기본 거부, 자동 생성 시 기본 허용 Profile, 별도의 failsafe 등을 고려해야 합니다. Installation.hostPorts는 자동 HostEndpoint 생성 설정이 아닙니다.

</details>

15. Calico Open Source 3.32에서 제공되지 않는 진단 명령은?
    - A) calicoctl get networkpolicy
    - B) calicoctl get workloadendpoint
    - C) kubectl logs로 Felix 로그 확인
    - D) calicoctl policy-trace

<details>
<summary>정답 보기</summary>

**정답: D) calicoctl policy-trace**

**설명:**
릴리스된 Open Source calicoctl에는 policy-trace 명령이 없습니다. 실제 레이블, 모든 적용 Tier, backend·로그와 새 연결을 확인합니다. Service/NAT 경로 문제에는 kube-proxy나 대체 구현도 관련이 있으며 Felix readiness 검사는 성능 측정이 아닙니다.

</details>

16. 표준 Calico API 서버에서 application Tier 정책 편집 권한을 부여하는 올바른 구조는?
    - A) 일반 networkpolicies에 application.* 이름 제한만 지정
    - B) application Tier의 get과 tier.networkpolicies의 application.* 및 의도한 namespace binding
    - C) verbs: ["*"]가 있는 임의 Role
    - D) application이라는 namespace 생성

<details>
<summary>정답 보기</summary>

**정답: B) application Tier의 get과 tier.networkpolicies의 application.* 및 의도한 namespace binding**

**설명:**
Calico authorizer는 tier.networkpolicies pseudo-resource의 합성 이름 application.* 또는 정책 이름과 Tier get을 함께 검사합니다. 일반 Kubernetes resourceNames glob이 아닙니다. 추가된 광범위한 binding과 native v3의 읽기 제한 차이도 확인해야 합니다.

</details>

17. 클라이언트가 소스 포트 49152로 backend의 8080에 연결할 때 서버 listener를 표현하는 ingress 매칭은?
    - A) source.ports: [8080]
    - B) 모든 클라이언트에 source.ports: [49152] 고정
    - C) protocol TCP와 destination.ports: [8080]
    - D) protocol 없이 전체 source 포트 허용

<details>
<summary>정답 보기</summary>

**정답: C) protocol TCP와 destination.ports: [8080]**

**설명:**
서버 listener는 목적지 포트 8080이며 클라이언트 소스 포트는 달라집니다. 숫자 포트에는 포트를 지원하는 protocol을 지정해야 합니다. source 포트 매칭은 명시적인 untracked DNS 응답 같은 다른 상황에 사용합니다.

</details>
