# 커널 데이터패스 퀴즈

이 퀴즈는 link-local 인터셉트의 커널 계층, iptables 충돌, conntrack 거동에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Lattice의 link-local 대역 사용이 "link-local 의미론을 엄격히 따르는 것이 아니다"라고 말하는 이유는?
   - A) 주소가 실제로는 공인 IP이기 때문
   - B) `169.254.0.0/16`은 원래 라우팅되지 않는 대역인데, Lattice 트래픽은 VPC 안의 인그레스 엔드포인트까지 도달해야 하므로 인프라가 유도한다
   - C) IPv4만 지원하기 때문
   - D) DNS가 이 대역을 해석하지 않기 때문

<details>

<summary>정답 보기</summary>

**정답: B) `169.254.0.0/16`은 원래 라우팅되지 않는 대역인데, Lattice 트래픽은 VPC 안의 인그레스 엔드포인트까지 도달해야 하므로 인프라가 유도한다**

**설명:**
Lattice는 link-local 대역을 "라우팅되지 않는 주소"라는 원래 의미로 쓰는 것이 아니라 **"인프라가 가로챈다"는 신호로 재사용**합니다. 실제로 패킷은 VPC 안의 인그레스 엔드포인트까지 가야 합니다. 같은 이유로 IPv6에서는 link-local(`fe80::/10`)이 아니라 라우팅 가능한 ULA(`fd00:ec2:80::/64`)를 골랐습니다 — 링크 범위로는 부족하기 때문입니다.
</details>

2. 사이드카 메시와 Lattice 트래픽의 충돌이 일어나는 정확한 커널 지점은?
   - A) 노드 net namespace의 `POSTROUTING`
   - B) Pod net namespace의 `OUTPUT` 훅 — Lattice 트래픽도 outbound이므로 REDIRECT 규칙에 걸림
   - C) NIC 드라이버의 ring buffer
   - D) 노드의 라우팅 테이블

<details>

<summary>정답 보기</summary>

**정답: B) Pod net namespace의 `OUTPUT` 훅 — Lattice 트래픽도 outbound이므로 REDIRECT 규칙에 걸림**

**설명:**
메시 init container는 Pod의 net namespace 안에서 "이 Pod에서 나가는 모든 outbound 트래픽을 Envoy 포트로 REDIRECT"하는 iptables 규칙을 심습니다. Lattice로 향하는 트래픽도 outbound이므로 이 규칙에 걸리고, Envoy는 `169.254.171.x`를 자기 클러스터 설정에서 찾을 수 없어 실패합니다. netfilter 규칙이 net namespace별이라는 성질 때문에 이 충돌이 Pod 안에서 발생합니다.
</details>

3. Interception된 요청은 어떻게 진단해야 합니까?
   - A) 커널 패닉이 발생하기 때문
   - B) 실제 Envoy outbound policy·route·오류를 확인하며 미등록 대상은 전달 또는 거부될 수 있다
   - C) Pod가 즉시 CrashLoopBackOff에 빠지기 때문
   - D) kube-proxy가 경고 로그를 남기기 때문

<details>

<summary>정답 보기</summary>

**정답: B) 실제 Envoy outbound policy·route·오류를 확인하며 미등록 대상은 전달 또는 거부될 수 있다**

**설명:**
Proxy log에 요청이 보이면 통과 사실은 알 수 있지만 유일한 실패 원인은 아닙니다. 즉시 실패를 가정하지 말고 선택한 bypass/서명 동작을 확인합니다.
</details>

4. 예외 CIDR을 등록했는데도 "가끔 실패"하는 증상의 가장 유력한 원인은?
   - A) 규칙 순서가 잘못됨
   - B) IPv6 대역(`fd00:ec2:80::/64`) 누락 — dual-stack에서 클라이언트가 IPv6로 연결하면 그 경로는 여전히 인터셉트됨
   - C) Pod를 재시작하지 않음
   - D) Security Group 설정 누락

<details>

<summary>정답 보기</summary>

**정답: B) IPv6 대역(`fd00:ec2:80::/64`) 누락 — dual-stack에서 클라이언트가 IPv6로 연결하면 그 경로는 여전히 인터셉트됨**

**설명:**
IPv4만 제외하고 dual-stack 클러스터를 운영하면, 클라이언트가 AAAA 레코드를 받아 IPv6로 연결을 시도할 때 그 경로는 여전히 인터셉트됩니다. **증상이 "가끔 실패"인 것이 특징**인데, DNS 응답 순서나 클라이언트의 주소 선택에 따라 갈리기 때문입니다. C도 실제 원인이 될 수 있지만 그 경우는 해당 Pod가 항상 실패하므로 "가끔"이 아닙니다.
</details>

5. egress proxy 방식에서 UID 기반 예외 규칙이 필수인 이유는?
   - A) 보안 정책상 프록시는 비특권 UID로 실행해야 하기 때문
   - B) 프록시가 서명해 내보내는 패킷도 목적지가 Lattice 대역이므로, UID 예외가 없으면 자기 자신에게 다시 리다이렉트되어 루프가 돈다
   - C) SigV4 서명에 UID 정보가 포함되기 때문
   - D) conntrack이 UID별로 항목을 구분하기 때문

<details>

<summary>정답 보기</summary>

**정답: B) 프록시가 서명해 내보내는 패킷도 목적지가 Lattice 대역이므로, UID 예외가 없으면 자기 자신에게 다시 리다이렉트되어 루프가 돈다**

**설명:**
프록시가 서명을 붙여 Lattice로 내보내는 패킷의 목적지도 `169.254.171.x`입니다. UID 예외가 없으면 그 패킷이 다시 REDIRECT 규칙에 걸려 루프가 돕니다. 그래서 프록시를 전용 UID로 실행하고(레퍼런스 구현은 101) 그 UID에서 나온 트래픽은 netfilter의 `owner` 매치(`-m owner --uid-owner`)로 `RETURN`시킵니다. **프록시 컨테이너의 `runAsUser`와 iptables 규칙의 UID가 반드시 일치**해야 하며, 매니페스트 커스터마이즈 시 가장 깨지기 쉬운 연결입니다.
</details>

6. egress proxy 방식이 공통 라이브러리 방식보다 conntrack 부담이 큰 이유는?
   - A) 프록시가 연결을 더 오래 유지하기 때문
   - B) Pod net namespace의 REDIRECT가 DNAT이므로 되돌릴 정보를 기억해야 하고, 프록시→Lattice 연결 항목도 추가로 생김
   - C) 프록시가 UDP를 함께 쓰기 때문
   - D) 프록시가 conntrack 타임아웃을 늘리기 때문

<details>

<summary>정답 보기</summary>

**정답: B) Pod net namespace의 REDIRECT가 DNAT이므로 되돌릴 정보를 기억해야 하고, 프록시→Lattice 연결 항목도 추가로 생김**

**설명:**
Signing proxy는 local/upstream 연결 구간을 만들지만 pooling과 namespace/NAT 선택에 따라 tracking 비용이 달라집니다. Node table의 고정 증가를 가정하지 말고 Pod/node table과 eBPF map을 확인합니다.
</details>

7. Packet capture 가시성으로 무엇을 판단할 수 있습니까?
   - A) conntrack 포화
   - B) 송수신 측·방향·interface·namespace별로 capture를 해석하고 다른 증거와 연결한다
   - C) qdisc 드롭
   - D) Lattice 인증 실패

<details>

<summary>정답 보기</summary>

**정답: B) 송수신 측·방향·interface·namespace별로 capture를 해석하고 다른 증거와 연결한다**

**설명:**
전달 전에 거부된 inbound packet은 수신 측에 없지만 outbound packet은 외부 SG drop 전에 송신 측에서 보일 수 있습니다. 응답 부재만으로 SG 실패가 증명되지는 않습니다.
</details>

8. "일부 노드에서만 Lattice 호출이 실패한다"는 패턴이 진단에 주는 정보는?
   - A) Lattice 서비스 설정 오류
   - B) 노드 상태 불일치 — SG 차이, 커널 버전 혼재, conntrack 설정 차이, 시각 동기화, Pod 재시작 여부
   - C) auth policy 설정 오류
   - D) DNS 전파 지연

<details>

<summary>정답 보기</summary>

**정답: B) 노드 상태 불일치 — SG 차이, 커널 버전 혼재, conntrack 설정 차이, 시각 동기화, Pod 재시작 여부**

**설명:**
전체 실패는 설정·인증 문제이고, **노드 단위 실패는 노드 상태 불일치**입니다. 후보는 노드 그룹별 SG 적용 차이, `kernel-default` AMI로 인한 6.1/6.18 혼재, 부트스트랩 시점에 따른 conntrack 설정 차이, `x-amz-date` 5분 오차를 유발하는 시각 동기화 문제, 그리고 애노테이션 변경이 구 Pod에 미적용된 경우입니다. "일부 노드"라는 패턴 자체가 범위를 좁혀주는 진단 정보입니다.
</details>
