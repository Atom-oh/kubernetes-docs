# 네트워크 기초 Part 1 퀴즈 — 계층 모델과 링크·라우팅

> **마지막 업데이트**: 2026년 9월 14일

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

6. 일반적인 IPv4 브로드캐스트 서브넷에서 `192.0.2.130/26`의 네트워크·브로드캐스트·호스트 범위는 무엇인가요?
   - A) 네트워크 `.0`, 브로드캐스트 `.255`, 호스트 `.1`–`.254`
   - B) 네트워크 `.130`, 브로드캐스트 `.193`, 호스트 `.131`–`.192`
   - C) 네트워크 `.128`, 브로드캐스트 `.191`, 호스트 `.129`–`.190`
   - D) 네트워크 `.128`, 브로드캐스트 `.190`, 호스트 `.129`–`.189`

<details>
<summary>정답 보기</summary>

**정답: C) 네트워크 `.128`, 브로드캐스트 `.191`, 호스트 `.129`–`.190`**

**설명:**
마스크는 `255.255.255.192`입니다. 호스트 6비트로 주소 64개를 표현하며 `.130`은 `.128`–`.191` 블록에 속합니다. 네트워크·브로드캐스트 주소를 제외하면 일반 호스트 주소 62개가 남습니다. 여기의 주소는 모두 `192.0.2` 접두부를 공유하는 문서용 예제입니다.

</details>

7. `192.0.2.130/26` 호스트에 해당 서브넷의 on-link 경로가 있습니다. 선택된 라우팅 테이블에는 `198.51.100.0/24`는 `.129` 경유, `198.51.100.128/25`는 `.190` 경유, 기본 경로는 `.129` 경유로도 설정되어 있습니다(게이트웨이는 `192.0.2` 대역). 이웃 항목이 없을 때 목적지 `198.51.100.140`에 적용되는 경로와 ARP 대상은 무엇인가요?
   - A) 기본 경로; `192.0.2.129`를 ARP로 확인
   - B) `/25` 경로; `192.0.2.190`을 ARP로 확인
   - C) `/24` 경로; `198.51.100.140`을 ARP로 확인
   - D) `/25` 경로; `198.51.100.140`을 ARP로 확인

<details>
<summary>정답 보기</summary>

**정답: B) `/25` 경로; `192.0.2.190`을 ARP로 확인**

**설명:**
원격 경로 세 개가 모두 일치하지만 `/25`가 가장 긴 프리픽스입니다. ARP는 같은 링크의 게이트웨이 MAC을 확인합니다. 프레임은 그 MAC으로 전달하고 NAT가 없다면 IP 목적지는 `198.51.100.140` 그대로 유지합니다. 기본 경로의 metric이 더 낮아도 더 구체적인 경로보다 우선하지 않습니다.

</details>

8. `192.0.2.130/26` 호스트에 on-link `192.0.2.128/26` 경로와 `192.0.2.129` 경유 기본 경로가 있습니다. 더 구체적인 경로와 캐시된 이웃 항목이 없다면 `192.0.2.150`으로 어떻게 보내나요?
   - A) `192.0.2.150`을 ARP로 확인한 뒤 해당 MAC으로 직접 전송한다
   - B) 모든 IP 트래픽에는 게이트웨이가 필요하므로 `192.0.2.129`를 ARP로 확인한다
   - C) `192.0.2.191`을 ARP로 확인한 뒤 IP 패킷을 브로드캐스트한다
   - D) 링크 계층 목적지 없이 기본 게이트웨이에 전송한다

<details>
<summary>정답 보기</summary>

**정답: A) `192.0.2.150`을 ARP로 확인한 뒤 해당 MAC으로 직접 전송한다**

**설명:**
선택된 `/26` 경로가 목적지를 on-link로 지정하므로 목적지 호스트 자체가 다음 홉입니다. 기본 게이트웨이는 경로 조회가 그 경로를 선택할 때 사용합니다. 설정되어 있다는 이유만으로 로컬 트래픽까지 항상 경유하는 것은 아닙니다.

</details>

9. 일반적인 “전체 주소 수에서 두 개 빼기” 계산의 예외를 올바르게 설명한 것은 무엇인가요?
   - A) `/31`에는 언제나 사용할 수 있는 끝점이 없다
   - B) `/32`는 언제나 호스트 주소와 별도의 게이트웨이 주소를 제공한다
   - C) 모든 클라우드 `/26`은 일반 호스트 주소 62개를 전부 할당할 수 있다
   - D) 지원되는 점대점 `/31`은 두 주소를 사용하고, `/32`는 주소 하나를 식별하며, 클라우드 예약은 별도로 확인해야 한다

<details>
<summary>정답 보기</summary>

**정답: D) 지원되는 점대점 `/31`은 두 주소를 사용하고, `/32`는 주소 하나를 식별하며, 클라우드 예약은 별도로 확인해야 한다**

**설명:**
RFC 3021은 `/31`의 두 주소를 점대점 끝점으로 사용하도록 합니다. `/32` 호스트 경로는 주소 하나와 일치하며 그 자체로 on-link 도달 가능성을 만들지는 않습니다. 일반적인 AWS VPC IPv4 서브넷은 주소 다섯 개를 예약하므로 `/26`의 할당 가능 주소는 59개입니다. BYOIP 같은 방식에는 다른 규칙이 적용됩니다.

</details>

10. UDP traceroute가 중간 라우터에서 ICMP Type 11 Code 0을 받고, 이후 목적지에서 Type 3 Code 3을 받았습니다. 일반적으로 무엇을 의미하나요?
   - A) 전달 중 probe의 TTL이 만료되었고, 이후 probe는 목적지의 사용하지 않는 UDP 포트에 도착했다
   - B) 목적지가 모든 홉에서 UDP 데이터로 응답했다
   - C) 라우터가 경로 MTU 문제를 알렸고, 이후 목적지가 TLS를 완료했다
   - D) traceroute가 모든 송신 probe를 자동으로 ICMP Echo Request로 바꿨다

<details>
<summary>정답 보기</summary>

**정답: A) 전달 중 probe의 TTL이 만료되었고, 이후 probe는 목적지의 사용하지 않는 UDP 포트에 도착했다**

**설명:**
송신 probe와 응답의 프로토콜은 다를 수 있습니다. UDP probe에도 ICMP 오류가 돌아옵니다. ICMP Echo·TCP SYN 방식 역시 중간 홉에서 Time Exceeded를 이용하지만 최종 응답은 Echo Reply 또는 TCP SYN/ACK·RST일 수 있습니다. Fragmentation Needed는 이 문제의 코드들이 아닌 Type 3 Code 4입니다.

</details>

11. traceroute의 한 홉은 `* * *`로 표시되지만 이후 홉과 목적지는 응답합니다. 어떤 결론을 내릴 수 있나요?
   - A) 조용한 라우터가 종단 간 트래픽을 모두 버린다
   - B) 해당 probe의 대기 시간 안에 대응하는 응답을 받지 못했으며, 종단 간 손실을 주장하려면 추가 증거가 필요하다
   - C) 순방향과 반환 경로가 동일하다
   - D) 모든 애플리케이션 패킷 크기가 경로 MTU 안에 들어간다

<details>
<summary>정답 보기</summary>

**정답: B) 해당 probe의 대기 시간 안에 대응하는 응답을 받지 못했으며, 종단 간 손실을 주장하려면 추가 증거가 필요하다**

**설명:**
필터링, 응답 생략·속도 제한, 반환 경로 손실로도 타임아웃이 발생합니다. 반복 탐색을 목적지·애플리케이션 결과와 비교하세요. RTT에는 반환 경로가 포함되며 작은 probe의 성공이 큰 패킷의 PMTU 블랙홀을 배제하지는 않습니다.

</details>

---

[학습 자료로 돌아가기](../../basics/06-network-fundamentals-part1.md) | [다음 퀴즈: Part 2](./06-network-fundamentals-part2-quiz.md)

[CIDR 예제](../../basics/06-network-fundamentals-part1.md#ipv4-cidr-subnet), [다음 홉 판단](../../basics/06-network-fundamentals-part1.md#longest-prefix-next-hop), [ICMP 해석](../../basics/06-network-fundamentals-part1.md#icmp-traceroute-interpretation)과 각 절의 공식 참고 자료를 복습하세요.

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
