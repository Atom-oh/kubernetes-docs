# 네트워크 기초 Part 1 퀴즈 — 계층 모델과 링크·라우팅

> **마지막 업데이트**: 2026년 9월 11일

링크 계층과 인터넷·라우팅 계층 11개 프로토콜과 메커니즘에 대한 이해도를 테스트합니다.

## 객관식 문제

1. VPN이나 오버레이 네트워크 위에서 "핑은 되는데 큰 응답만 멈춘다"는 장애가 발생했습니다. 가장 먼저 의심해야 할 원인은 무엇인가요?
   - A) DNS TTL이 너무 길다
   - B) 캡슐화 헤더로 인한 실효 MTU 감소와 ICMP 차단(MTU 블랙홀)
   - C) TCP 혼잡 제어 알고리즘 불일치
   - D) ARP 캐시 만료

<details>
<summary>정답 보기</summary>

**정답: B) 캡슐화 헤더로 인한 실효 MTU 감소와 ICMP 차단(MTU 블랙홀)**

**설명:**
캡슐화는 경로에 실을 수 있는 내부 패킷 크기를 줄입니다. DF가 설정된 IPv4 패킷은 라우터가 단편화할 수 없어 전통적 PMTUD에 ICMP Type 3 Code 4가 필요합니다. IPv6 라우터는 단편화하지 않으며 ICMPv6 Packet Too Big(Type 2)를 사용합니다. 이를 차단하면 블랙홀이 생길 수 있지만 PLPMTUD는 ICMP에 의존하지 않고 크기를 탐색할 수 있습니다.

</details>

2. VIP 기반 HA 구성에서 페일오버 직후 새 액티브 노드가 Gratuitous ARP를 보내는 이유는 무엇인가요?
   - A) 자신의 IP 주소를 DHCP 서버에 재등록하기 위해
   - B) 스위치와 이웃 호스트의 MAC 테이블/ARP 캐시를 새 노드로 갱신하기 위해
   - C) 게이트웨이의 라우팅 테이블을 다시 계산시키기 위해
   - D) TLS 세션을 재협상하기 위해

<details>
<summary>정답 보기</summary>

**정답: B) 스위치와 이웃 호스트의 MAC 테이블/ARP 캐시를 새 노드로 갱신하기 위해**

**설명:**
VIP는 그대로지만 소유 노드나 MAC/포트 위치가 바뀝니다. Gratuitous ARP는 이웃에 IP-to-MAC 정보를 알리고 스위치는 새 포트의 source MAC을 학습할 수 있습니다. 같은 가상 MAC을 유지하는 HA 방식도 있습니다. 이 갱신이 지연되면 페일오버 전환이 느려집니다.

</details>

3. OSPF와 BGP의 차이를 가장 정확하게 설명한 것은 무엇인가요?
   - A) OSPF는 정책 기반 경로 선택, BGP는 최단 경로 계산에 집중한다
   - B) OSPF는 AS 간 라우팅, BGP는 AS 내부 라우팅에 쓰인다
   - C) OSPF는 AS 내부에서 다익스트라로 최단 경로를 계산하고, BGP는 AS 간에 정책 기반으로 경로를 선택한다
   - D) 둘 다 링크 상태 프로토콜이며 용도만 다르다

<details>
<summary>정답 보기</summary>

**정답: C) OSPF는 AS 내부에서 다익스트라로 최단 경로를 계산하고, BGP는 AS 간에 정책 기반으로 경로를 선택한다**

**설명:**
OSPF는 링크 상태 기반 IGP로, 영역 내 모든 라우터가 동일한 토폴로지에서 최단 경로를 계산합니다. BGP는 경로 벡터 프로토콜로 AS_PATH, Local Preference, MED 같은 속성으로 "정책적으로 원하는 길"을 고릅니다. Direct Connect는 BGP를 사용하며 Site-to-Site VPN은 지원되는 구성에서 BGP 또는 정적 라우팅을 사용합니다. BGP에는 AS 내부의 iBGP 세션도 있습니다.

</details>

4. NAT가 "계층 모델을 위반한다"고 평가받는 이유로 가장 적절한 것은 무엇인가요?
   - A) 링크 계층 프레임을 직접 수정하기 때문에
   - B) L3 장비이면서 L4 포트를 변환하고, 종단 간 연결성이라는 전제를 깨뜨리기 때문에
   - C) 암호화된 패킷을 복호화하기 때문에
   - D) 라우팅 테이블을 사용하지 않기 때문에

<details>
<summary>정답 보기</summary>

**정답: B) L3 장비이면서 L4 포트를 변환하고, 종단 간 연결성이라는 전제를 깨뜨리기 때문에**

**설명:**
포트를 변환하는 NAT(PAT/NAPT)는 IP 주소뿐 아니라 포트까지 변환하며 세션별 매핑 테이블에 의존합니다. 그 결과 P2P 직접 연결이 어려워졌고, WebRTC는 STUN/TURN(ICE)으로 이를 우회합니다. 클라우드에서는 NAT Gateway의 포트 고갈과 데이터 처리 비용이 실무 이슈입니다.

</details>

5. 듀얼 스택으로 IPv6를 도입한 조직에서 확인해야 할 보안 공백은 무엇인가요?
   - A) IPv6는 암호화를 지원하지 않는다
   - B) IPv4 방화벽 규칙만 관리되고 IPv6 경로에 대한 규칙이 누락된다
   - C) IPv6 주소는 스캔이 더 쉽다
   - D) SLAAC가 DHCP 서버를 무력화한다

<details>
<summary>정답 보기</summary>

**정답: B) IPv4 방화벽 규칙만 관리되고 IPv6 경로에 대한 규칙이 누락된다**

**설명:**
듀얼 스택은 방화벽 규칙과 보안 정책을 두 벌 관리해야 한다는 뜻입니다. IPv6 규칙 누락은 위험하지만 IPv6 주소만으로 인터넷에서 접근 가능해지는 것은 아닙니다. 라우트, 보안 그룹과 NACL이 적용되며 egress-only internet gateway로 외부의 새 IPv6 연결을 막을 수 있습니다.

</details>

---

[학습 자료로 돌아가기](../../basics/06-network-fundamentals-part1.md) | [다음 퀴즈: Part 2](./06-network-fundamentals-part2-quiz.md)

## 검증 참고 자료

- https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/network_mtu.html
- https://www.rfc-editor.org/rfc/rfc894
- https://www.rfc-editor.org/rfc/rfc6691
- https://www.rfc-editor.org/rfc/rfc4638
- https://www.rfc-editor.org/rfc/rfc5227
- https://www.rfc-editor.org/rfc/rfc792
- https://www.rfc-editor.org/rfc/rfc8899
- https://www.rfc-editor.org/rfc/rfc2328
- https://www.rfc-editor.org/rfc/rfc6811
- https://docs.kernel.org/networking/bridge.html
- https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html
- https://docs.aws.amazon.com/vpc/latest/userguide/egress-only-internet-gateway.html
- https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNRoutingTypes.html
- https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-scenarios.html
- https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-pricing.html
