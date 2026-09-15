# 02. 라우팅 정책과 수렴 시간 측정 — 퀴즈

> **마지막 업데이트**: 2026년 9월 15일

[워크북](../../../networking/expert/02-routing-policy-convergence.md)으로 돌아갑니다.
문항마다 답 하나를 고르고 어떤 관찰이 답을 뒷받침하는지 설명합니다.
추론 문제이며 실습을 실행했다는 주장이 아닙니다.

1. 선택한 BGP 실습이 AS65000 내부에서 OSPF도 사용하는 이유는 무엇인가요?
   - A) OSPF가 모든 BGP 정책 결정을 대체합니다.
   - B) OSPF가 iBGP loopback을 포함한 내부 도달 가능성을 제공합니다.
   - C) OSPF가 LOCAL_PREF를 외부 제공자에게 전달합니다.

<details>
<summary>정답 보기</summary>

**정답: B**

**설명:** 이 설계에서 BGP는 정책 속성을 가진 목적지 정보를 전달하고 OSPF는 내부 경로를 제공합니다. OSPF 인접 관계뿐 아니라 실제 BGP next hop으로 가는 경로도 확인해야 합니다. 인접 관계만으로 필요한 prefix가 존재한다고 볼 수 없습니다.

</details>

2. iBGP로 배운 prefix가 BGP 테이블에 있지만 NEXT_HOP을 해석할 수 없습니다. 다음 조치로 가장 적절한 것은?
   - A) 해당 next hop의 경로, next-hop 정책, 커널 조회 결과를 확인합니다.
   - B) 세션이 established이므로 포워딩 성공을 선언합니다.
   - C) 도달할 수 없는 next hop이 도달 가능해질 때까지 LOCAL_PREF를 높입니다.

<details>
<summary>정답 보기</summary>

**정답: A**

**설명:** 선호도는 도달 가능성을 만들지 않습니다. 실제 NEXT_HOP을 식별하고 라우팅 테이블을 통해 인터페이스/이웃까지 해석합니다. 이어서 유효성, 선택 경로, FIB, 출발지를 지정한 트래픽 증거를 비교합니다.

</details>

3. c2가 c1을 통해 LOCAL_PREF 200인 유효 경로를, x2를 통해 100인 경로를 배웁니다. 내부 홉이 늘어도 c1을 선호할 수 있는 이유는?
   - A) BGP는 항상 가장 작은 IP 주소를 선택합니다.
   - B) c1의 weight 200이 자동 전파되었습니다.
   - C) LOCAL_PREF는 AS 내부 정책을 표현하고 이 FRR 선택 과정에서 AS-path 길이보다 먼저 평가됩니다.

<details>
<summary>정답 보기</summary>

**정답: C**

**설명:** BGP 선택은 단순한 IGP 홉 수 계산이 아닙니다. LOCAL_PREF는 내부에 전달되지만 weight는 구현/라우터 로컬 값입니다. 후보 두 개가 모두 유효하며 더 앞선 선택 기준이나 다른 정책이 전제를 바꾸지 않는지도 확인합니다.

</details>

4. Route reflector가 해결하는 문제와 여전히 확인해야 할 사항의 올바른 조합은?
   - A) 누락된 underlay 경로를 모두 만들므로 client에는 IGP가 필요 없습니다.
   - B) 필요한 iBGP 세션 수를 줄이지만 client의 next hop과 포워딩 증거는 별도로 확인해야 합니다.
   - C) 모든 client가 모든 대안 경로를 보도록 보장합니다.

<details>
<summary>정답 보기</summary>

**정답: B**

**설명:** Reflection은 광고 규칙을 바꾸고 ORIGINATOR_ID/CLUSTER_LIST로 루프를 방지합니다. Next-hop 도달 가능성을 복구하거나 대안 경로의 완전한 가시성을 보장하지 않습니다. Reflector가 반드시 tenant 데이터 트래픽을 운반하는 것도 아닙니다.

</details>

5. 제안한 export 필터가 정확히 `192.168.42.0/24`만 허용합니다. 이 계약에서 거부해야 하는 후보는?
   - A) `192.168.42.0/25`. 정확한 prefix/길이 일치가 more-specific을 자동 포함하지 않기 때문입니다.
   - B) 없습니다. Allowlist는 명시적으로 거부하지 않은 모든 경로를 허용합니다.
   - C) MED가 큰 경로만 거부합니다.

<details>
<summary>정답 보기</summary>

**정답: A**

**설명:** 계약은 prefix와 길이 하나만 허용합니다. `/25`, 제공자의 `192.168.100.0/24`, default route는 범위 밖입니다. 실제 광고는 별도로 확인해야 하며 문서에 작성한 필터 설계는 설치된 필터가 아닙니다.

</details>

6. BGP 정책 속성에 대한 타당한 설명은?
   - A) Community를 붙이면 의도한 동작이 항상 강제됩니다.
   - B) MED는 언제나 모든 이웃 AS 사이에서 비교됩니다.
   - C) Community에는 해석하는 정책이 필요하고 MED 비교는 수신자 규칙에 의존합니다.

<details>
<summary>정답 보기</summary>

**정답: C**

**설명:** Community는 표식을 전달하며 수신 정책이 운영 의미를 부여합니다. MED와 AS-path prepending도 수신자의 결정 과정 안에서만 영향을 줍니다. 다른 AS에 대한 무조건적인 명령이 아닙니다.

</details>

7. 이 FRR/clab 실습에서 라우팅 CLI로 들어가는 올바른 순서는?
   - A) VM 셸에서 바로 `show ip route`를 실행합니다.
   - B) 실습 디렉터리에서 `netlab connect c1`, 이어서 c1 Linux 셸에서 `vtysh`를 실행합니다.
   - C) `c1(config-router)#`에서 `ip route get`을 실행합니다.

<details>
<summary>정답 보기</summary>

**정답: B**

**설명:** 연결은 FRR 컨테이너의 Linux 셸을 엽니다. `vtysh`가 FRR CLI를 제공하며 Linux의 `ip`, `ping`은 셸 명령입니다. 단일 FRR show 명령에는 검증된 VM 측 `netlab connect c1 --show ip route`도 사용할 수 있습니다.

</details>

8. 정책 변경 전에 c1에 이미 local preference 150이 명시되어 있습니다. 어떻게 해야 하나요?
   - A) 기존 정책을 삭제하지 말고 중단하여 의도한 기준 상태부터 확립합니다.
   - B) 흔한 기본값이므로 100이라고 가정합니다.
   - C) 200을 적용한 뒤 설정을 삭제하고 정확한 복원이라고 합니다.

<details>
<summary>정답 보기</summary>

**정답: A**

**설명:** 제시한 역연산은 명시적 설정이 없고 유효 선호도가 100인 상태를 전제로 합니다. 기존 150을 제거하면 원래 상태로 복원되지 않습니다. 알려진 사전 상태는 선택적 주석이 아니라 권한 범위와 재현성의 일부입니다.

</details>

9. Peer shutdown 동안 200 ms 간격의 타임스탬프 probe에서 손실이 없었습니다. 정당한 결론은?
   - A) 수렴 시간은 정확히 0 ms였습니다.
   - B) 모든 애플리케이션과 패킷 크기가 영향을 받지 않았습니다.
   - C) 이 샘플링으로 중단을 포착하지 못했습니다. 경로/FIB 관찰을 보존하고 측정 한계를 보고합니다.

<details>
<summary>정답 보기</summary>

**정답: C**

**설명:** 샘플링은 짧은 중단을 놓칠 수 있습니다. 관리 명령 shutdown은 무응답 장애나 timer 만료와도 다릅니다. 보편적인 timer 결론을 내리지 말고 조작, 관찰한 경로/FIB 변화, probe 간격, 지속 회복 기준을 보고합니다.

</details>

10. 장애 실험을 완료할 수 있는 결과 집합은?
   - A) Probe 출력을 보존하지 않았지만 BGP가 다시 established입니다.
   - B) 정확한 peer/정책 변경을 되돌렸고 기준 경로·FIB·probe가 회복되었으며 측정 한계를 기록했습니다.
   - C) Wildcard clear와 호스트 전체 route flush 후 출력이 정상처럼 보입니다.

<details>
<summary>정답 보기</summary>

**정답: B**

**설명:** c1의 지정 peer를 먼저 복원하고 추가했던 local-preference 설정을 되돌린 뒤 원래 동작을 검증합니다. 관측 누락은 성공이 아닙니다. 소유 clone/revision을 보존하고 범위 없는 정리나 upstream의 c2=50 validator 통과 주장 없이 실패를 보고합니다.

</details>

완료 기준: 모든 답을 설명하고 워크북의 기준/변경/장애/복원 행렬을 첨부하거나 실습을 **미실행**으로 표시합니다.
