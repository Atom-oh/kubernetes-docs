# 07. WAN과 하이브리드 연결 설계 퀴즈

> **마지막 업데이트**: 2026년 11월 19일

[워크북](../../../networking/expert/07-wan-hybrid-connectivity.md)으로 돌아갑니다.
문항마다 답 하나를 고르고 워크북의 어떤 규칙이 답을 뒷받침하는지 설명합니다.
설계 추론 문제이며 실제 연결을 구성했다는 주장이 아닙니다.

1. Transit Gateway가 `10.10.0.0/16`을 Direct Connect 게이트웨이 attachment와 BGP VPN attachment 양쪽에서 받습니다. 온프레미스는 DX 쪽 광고에 AS_PATH prepend를 세 번 붙였습니다. VPC에서 온프레미스로 가는 트래픽은 어디로 가나요?
   - A) VPN. AS_PATH가 더 짧기 때문입니다.
   - B) DX. 같은 CIDR이면 attachment 유형 순서가 AS_PATH 비교보다 먼저이고, DX 게이트웨이 전파 경로가 VPN 전파 경로보다 우선합니다.
   - C) 두 경로에 ECMP로 나뉩니다.

<details>
<summary>정답 보기</summary>

**정답: B) DX. 같은 CIDR이면 attachment 유형 순서가 AS_PATH 비교보다 먼저이고, DX 게이트웨이 전파 경로가 VPN 전파 경로보다 우선합니다.**

**설명:** TGW는 가장 긴 prefix를 먼저 고르고, 같은 CIDR이 서로 다른 유형에서 오면 정적, 시스템, prefix list, VPC 전파, DX 게이트웨이 전파, Connect, VPN 순으로 우선합니다. AS_PATH와 MED는 같은 유형 안에서만 비교됩니다. ECMP도 서로 다른 attachment 유형 사이에서는 지원하지 않습니다.

</details>

2. 백업 VPN을 만들면서 TGW 라우트 테이블에 `10.10.0.0/16` → VPN attachment **정적 경로**를 넣었습니다. DX 게이트웨이도 같은 경로를 전파합니다. 정상 상태의 결과는?
   - A) DX가 주 경로로 남습니다. DX가 항상 VPN보다 우선하기 때문입니다.
   - B) TGW가 두 경로를 번갈아 씁니다.
   - C) 정적 경로가 전파 경로보다 우선하므로 VPN이 의도치 않게 주 경로가 됩니다.

<details>
<summary>정답 보기</summary>

**정답: C) 정적 경로가 전파 경로보다 우선하므로 VPN이 의도치 않게 주 경로가 됩니다.**

**설명:** TGW 평가 순서의 첫 단계는 정적 경로입니다. 같은 목적지에 정적 경로가 있으면 전파 경로는 테이블에 나타나지도 않습니다. 백업 VPN은 BGP로 구성해 DX 게이트웨이 전파 경로보다 낮은 순위에 두어야 합니다.

</details>

3. DX 게이트웨이의 허용 prefix를 `10.0.0.0/8`로 요약했고, VPN으로는 TGW 라우트 테이블의 `10.20.0.0/16`이 광고됩니다. 온프레미스 라우터는 DX로 배운 경로에 LOCAL_PREF 200, VPN 경로에 100을 줍니다. `10.20.1.10`으로 가는 트래픽은?
   - A) VPN. 더 긴 prefix인 `10.20.0.0/16`이 먼저 일치하고, LOCAL_PREF는 같은 prefix 사이에서만 비교됩니다.
   - B) DX. LOCAL_PREF가 더 높기 때문입니다.
   - C) 두 경로 모두 버려집니다.

<details>
<summary>정답 보기</summary>

**정답: A) VPN. 더 긴 prefix인 `10.20.0.0/16`이 먼저 일치하고, LOCAL_PREF는 같은 prefix 사이에서만 비교됩니다.**

**설명:** Transit Gateway 연결에서는 허용 prefix가 그대로 온프레미스에 광고되므로 고객 라우터는 `10.0.0.0/8`(DX)과 `10.20.0.0/16`(VPN)을 서로 다른 경로로 받습니다. 포워딩은 최장 prefix 일치를 따르므로 VPN으로 샙니다. 허용 prefix 길이를 VPN 쪽과 맞추거나 고객 라우터에서 같은 요약으로 맞춥니다.

</details>

4. 두 DX VIF를 AWS에서 온프레미스로 돌아오는 트래픽 기준으로 active/passive로 쓰려 합니다. 올바른 설정은?
   - A) 주 VIF에만 낮은 MED를 붙입니다.
   - B) 주 VIF의 prefix에 `7224:7300`, 백업 VIF의 prefix에 `7224:7100`을 표준 community로 붙입니다.
   - C) route target 확장 community로 우선순위를 표시합니다.

<details>
<summary>정답 보기</summary>

**정답: B) 주 VIF의 prefix에 `7224:7300`, 백업 VIF의 prefix에 `7224:7100`을 표준 community로 붙입니다.**

**설명:** AWS는 private·transit VIF에서 가장 긴 prefix, local preference community, AS_PATH, MED 순으로 비교하며 community는 AS_PATH보다 먼저 평가됩니다. MED는 우선순위가 낮아 AWS가 권장하지 않습니다. 확장 community는 경로 우선순위에 평가되지 않으며 제거될 수 있습니다.

</details>

5. Direct Connect의 BFD에 대한 올바른 설명은?
   - A) AWS 쪽에서 자동으로 켜지므로 고객 라우터 설정 없이도 동작합니다.
   - B) Direct Connect는 BFD를 지원하지 않으므로 BGP hold time만 씁니다.
   - C) AWS 쪽에 비동기 BFD가 자동으로 켜져 있지만 고객 라우터에 구성해야 동작하며, 기본 최소 간격은 300 ms, 배수는 3입니다.

<details>
<summary>정답 보기</summary>

**정답: C) AWS 쪽에 비동기 BFD가 자동으로 켜져 있지만 고객 라우터에 구성해야 동작하며, 기본 최소 간격은 300 ms, 배수는 3입니다.**

**설명:** BFD를 구성하지 않으면 BGP는 hold time 90초 동안 keepalive가 오지 않아야 세션을 내립니다. 그래서 설계 과제의 "BFD 미구성" 시나리오는 5초 목표를 지키지 못합니다.

</details>

6. BFD 300 ms × 3으로 장애를 약 0.9초 만에 감지합니다. 설계 문서에 쓸 수 있는 정당한 문장은?
   - A) 감지는 약 0.9초이며, 경로 철회·전파, 양쪽 FIB 반영, 반대 방향 전환 시간은 측정 전 가정으로 둡니다.
   - B) 장애 조치 시간은 0.9초입니다.
   - C) BFD를 켜도 BGP hold time 90초가 지나야 경로가 바뀝니다.

<details>
<summary>정답 보기</summary>

**정답: A) 감지는 약 0.9초이며, 경로 철회·전파, 양쪽 FIB 반영, 반대 방향 전환 시간은 측정 전 가정으로 둡니다.**

**설명:** RFC 5880에서 감지 시간은 배수와 협상된 간격의 곱입니다. 감지 시간은 복구 시간의 일부일 뿐이며, 나머지 단계는 AWS가 고정 값을 공개하지 않습니다. BFD가 세션을 내리면 hold time 만료를 기다리지 않습니다.

</details>

7. Direct Connect LAG에 대한 올바른 설명은?
   - A) 서로 다른 DX 로케이션의 연결을 하나의 LAG로 묶어 로케이션 장애에 대비합니다.
   - B) 같은 대역의 전용 연결을 같은 엔드포인트에서 묶으며(100 Gbps 미만 최대 4개, 100·400 Gbps 최대 2개), MLAG를 지원하지 않으므로 용량은 늘리지만 로케이션 이중화는 아닙니다.
   - C) 호스티드 연결도 LAG에 넣을 수 있습니다.

<details>
<summary>정답 보기</summary>

**정답: B) 같은 대역의 전용 연결을 같은 엔드포인트에서 묶으며(100 Gbps 미만 최대 4개, 100·400 Gbps 최대 2개), MLAG를 지원하지 않으므로 용량은 늘리지만 로케이션 이중화는 아닙니다.**

**설명:** LAG의 모든 연결은 전용 연결이어야 하고 같은 Direct Connect 엔드포인트에서 종료됩니다. 로케이션 이중화는 Resiliency Toolkit의 High·Maximum resiliency 모델처럼 여러 로케이션에 연결을 나눠 설계합니다. 최소 연결 수 속성(기본 0)을 정하면 남은 연결의 과부하를 막을 수 있습니다.

</details>

8. "Site-to-Site VPN 연결 하나에 터널이 두 개이므로 이중화가 끝났다"는 보고서의 문제는?
   - A) 문제없습니다. 두 터널이 고객 게이트웨이까지 이중화합니다.
   - B) AWS는 두 터널 모두에 ECMP로 송신하므로 비대칭 라우팅 설정이 필요 없습니다.
   - C) 두 터널은 서로 다른 가용 영역의 AWS 쪽 엔드포인트를 이중화할 뿐이며, 고객 게이트웨이 하나와 회선 하나를 공유하면 그 둘이 단일 장애점입니다.

<details>
<summary>정답 보기</summary>

**정답: C) 두 터널은 서로 다른 가용 영역의 AWS 쪽 엔드포인트를 이중화할 뿐이며, 고객 게이트웨이 하나와 회선 하나를 공유하면 그 둘이 단일 장애점입니다.**

**설명:** 각 터널은 고유한 공인 IP를 쓰고 서로 다른 가용 영역에서 종료됩니다. AWS에서 온프레미스로 가는 트래픽은 한 터널을 선호하므로 고객 게이트웨이는 비대칭 라우팅을 허용해야 합니다. 고객 쪽 이중화에는 고객 게이트웨이와 VPN 연결을 하나 더 둡니다.

</details>

9. Transit VIF MTU 8500으로 DX를 쓰던 TCP 연결이 VPN(AES-GCM, NAT-T 꺼짐)으로 넘어갑니다. 큰 패킷이 사라지는 문제를 막는 설계는?
   - A) MSS를 백업 경로 기준(이 조합에서 1406)으로 고객 라우터에서 clamping하거나, VPN이 백업인 동안 VIF를 1500으로 유지합니다.
   - B) TGW가 모든 attachment에서 PMTUD를 지원하므로 그대로 둡니다.
   - C) VPN에 점보 프레임을 켭니다.

<details>
<summary>정답 보기</summary>

**정답: A) MSS를 백업 경로 기준(이 조합에서 1406)으로 고객 라우터에서 clamping하거나, VPN이 백업인 동안 VIF를 1500으로 유지합니다.**

**설명:** Site-to-Site VPN은 최대 MTU 1446, MSS 1406이며 점보 프레임과 PMTUD를 지원하지 않습니다. TGW의 PMTUD는 VPC와 Connect attachment로 들어오는 트래픽에만 적용됩니다. 장애 조치 설계에서 적용되는 MTU는 백업 경로의 MTU입니다.

</details>

10. 온프레미스 라우터가 transit VIF의 BGP 세션 하나로 IPv4 prefix 150개를 광고합니다. prefix 할당은 기본값입니다. 결과는?
   - A) AWS가 처음 100개만 받고 나머지는 무시합니다.
   - B) 할당(기본 100개)을 넘었으므로 BGP 세션이 idle 상태가 되어 DOWN으로 보고됩니다.
   - C) AWS가 자동으로 요약해 받습니다.

<details>
<summary>정답 보기</summary>

**정답: B) 할당(기본 100개)을 넘었으므로 BGP 세션이 idle 상태가 되어 DOWN으로 보고됩니다.**

**설명:** private·transit VIF의 BGP 세션당 경로는 IPv4·IPv6 각각 기본 100개이며 prefix 제어로 각각 1,000개까지 늘릴 수 있습니다. 경로 수 초과가 곧 세션 장애이므로 광고표를 할당량과 비교하는 것이 설계 과제의 첫 단계입니다.

</details>

11. Direct Connect 게이트웨이를 토폴로지 그림에 어떻게 그려야 하나요?
   - A) VIF와 Transit Gateway 사이에서 패킷을 전달하는 홉으로 그립니다.
   - B) Transit Gateway 라우트 테이블의 일부로 그립니다.
   - C) 데이터 경로 밖에서 동작하는 분산 BGP route reflector로, 세션 선만 연결합니다.

<details>
<summary>정답 보기</summary>

**정답: C) 데이터 경로 밖에서 동작하는 분산 BGP route reflector로, 세션 선만 연결합니다.**

**설명:** AWS 문서는 DX 게이트웨이를 데이터 트래픽 경로 밖에서 동작하는 분산 route reflector 집합으로 설명하므로 단일 장애점이 되지 않습니다. 애니메이션에서도 패킷은 DX 로케이션과 Transit Gateway에서만 멈춥니다.

</details>

12. "SD-WAN은 장애를 빨리 감지한다"는 문장을 제어·데이터 평면으로 정확히 고치면?
   - A) 라우터 사이의 IPsec 데이터 연결 위에서 BFD가 연결 장애를 감지하며, 컨트롤러 이중화는 별도의 설계 항목입니다.
   - B) Controller의 OMP 세션이 데이터 터널의 패킷 손실을 직접 측정합니다.
   - C) MEF 70.2가 BFD 타이머 값을 정합니다.

<details>
<summary>정답 보기</summary>

**정답: A) 라우터 사이의 IPsec 데이터 연결 위에서 BFD가 연결 장애를 감지하며, 컨트롤러 이중화는 별도의 설계 항목입니다.**

**설명:** Cisco Catalyst SD-WAN에서 Controller는 제어 평면을 조율하고 Validator는 장비 인증과 제어 연결을 조율합니다. 데이터는 라우터 사이의 IPsec 연결로 흐르고 BFD는 그 연결 위에서 자동으로 동작합니다. MEF 70.2는 서비스 속성(터널, 정책 등)을 정의하는 문서입니다.

</details>

완료 기준: 모든 답을 워크북의 규칙으로 설명하고, 설계 과제의 시나리오 표를 첨부하거나 **설계 검토**로 표시합니다.
