# 03. 데이터센터 EVPN — 퀴즈

> **마지막 업데이트**: 2026년 9월 15일

[워크북](../../../networking/expert/03-datacenter-evpn.md)으로 돌아갑니다.
답 하나를 고르고 유효한 부정 검사와 고장 난 lab을 구분할 긍정 대조군을 제시합니다.

1. Fabric의 access 경로가 예상과 달리 차단되어 있습니다. EVPN 장애로 단정하기 전에 확인할 선행 조건은?
   - A) VLAN 소속과, 해당 기능을 구성했다면 실제 STP 상태 및 LAG member 상태.
   - B) BGP hold timer만 확인합니다.
   - C) 단일 flow가 모든 LACP member를 동시에 쓰는지 확인합니다.

<details>
<summary>정답 보기</summary>

**정답: A**

**설명:** Tenant 연결과 로컬 포워딩은 overlay의 선행 조건입니다. LACP hashing은 한 flow를 모든 member에 분산한다고 보장하지 않습니다. 선택한 소규모 lab은 LACP나 중복 STP 토폴로지를 구성하지 않으므로 해당 기능을 검증했다는 근거가 될 수 없습니다.

</details>

2. h1에서 h2로 가는 VXLAN 패킷에서 원격 캡슐화 끝점을 식별하는 것은 보통 무엇인가요?
   - A) 외부 목적지는 반드시 h2의 tenant IP입니다.
   - B) 원격 VTEP IP가 외부 목적지이고 VNI가 가상 세그먼트를 식별합니다.
   - C) RD를 외부 IP 목적지 필드에 넣습니다.

<details>
<summary>정답 보기</summary>

**정답: B**

**설명:** 외부 transport와 내부 tenant 트래픽을 구분합니다. VTEP 쌍, VNI, 내부 주소를 캡처하여 매핑표와 대조합니다. 관리 주소 ping은 이 tenant 경로 증거를 대신하지 못합니다.

</details>

3. 두 광고가 서로 다른 RD를 가지지만 같은 VRF가 import하는 RT를 포함합니다. 올바른 설명은?
   - A) RD가 다르므로 반드시 다른 VPN에 속합니다.
   - B) VRF가 import하려면 RD가 같아야 합니다.
   - C) RD는 경로 식별자를 구분하며 일치하는 import/export RT 정책으로 같은 VPN에 속할 수 있습니다.

<details>
<summary>정답 보기</summary>

**정답: C**

**설명:** 경로 식별과 소속은 서로 다른 기능입니다. RT 정책이 import를 제어하고 RD가 겹치는 경로를 구분합니다. 그래도 import된 경로, FIB, 트래픽을 확인해야 합니다. RT는 패킷 방화벽이나 포워딩 보장이 아닙니다.

</details>

4. 올바른 route-type 대응은?
   - A) Type 2는 MAC/선택적 IP, Type 3은 IMET 참여 정보, Type 5는 IP prefix를 전달합니다.
   - B) Type 2는 underlay OSPF 경로만 전달하고 Type 3은 tenant 라우팅 서비스를 보장합니다.
   - C) 모든 bridging-only lab에 Type 5가 반드시 있어야 합니다.

<details>
<summary>정답 보기</summary>

**정답: A**

**설명:** 각 route type을 서비스 모델과 연결합니다. Host 학습 전에는 트래픽을 생성하고 L2에서는 replication/FDB 상태, Stage B에서는 Type-5 import를 추적합니다. 선택한 모델에 필요 없는 type은 근거 있는 N/A가 가능하지만 거짓 PASS는 안 됩니다.

</details>

5. Symmetric IRB와 단순한 EVPN BGP 존재의 차이는?
   - A) EVPN 세션이 있으면 anycast gateway가 자동 활성화됩니다.
   - B) Symmetric IRB에는 양 끝의 tenant 라우팅과 그 사이의 L3VNI가 필요합니다.
   - C) Symmetric IRB는 두 VTEP가 동일한 RD를 쓴다는 뜻입니다.

<details>
<summary>정답 보기</summary>

**정답: B**

**설명:** IRB는 BGP address family만이 아니라 bridge/라우팅 경계의 포워딩에 관한 개념입니다. 관련 SVI/VRF/VNI 연결을 확인합니다. Stage B는 routed host link를 가진 L3-only 모델이므로 access-VLAN anycast IRB나 이동성을 그 자체로 검증하지 않습니다.

</details>

6. Stage A upstream은 EOS/Cumulus를 선택하지만 워크북의 FRR 경로를 사용하려 합니다. 필요한 것은?
   - A) 오래된 FRR 컨테이너 아무거나 사용합니다. 모든 provider의 데이터 평면은 같습니다.
   - B) Linux bridge/VTEP 준비 없이 image 이름만 바꿉니다.
   - C) s1/s2를 명시적으로 FRR로 바꾸고 지원하는 clab/커널 조합, 버전/digest, 생성된 데이터 평면 객체를 확인합니다.

<details>
<summary>정답 보기</summary>

**정답: C**

**설명:** Provider, image, netlab template, VM 커널이 함께 실습을 구현합니다. FRR은 모든 인터페이스를 직접 만들기보다 Linux interface 상태를 학습합니다. 필요한 커널 기능이 없는 제한 환경은 BGP daemon이 시작되어도 차단 상태입니다.

</details>

7. Stage A에서 h1→h3는 실패하지만 같은 VLAN의 두 쌍도 통신하지 못합니다. 어떻게 분류하나요?
   - A) 격리 검증 성공이 아닙니다. 먼저 긍정 대조군 실패를 조사합니다.
   - B) Cross-VLAN probe 실패는 항상 격리를 증명하므로 PASS입니다.
   - C) EVPN 세션이 established이므로 PASS입니다.

<details>
<summary>정답 보기</summary>

**정답: A**

**설명:** 죽은 host나 고장 난 fabric도 같은 부정 probe를 만듭니다. 의도한 두 쌍의 성공, 올바른 연결, 차단 경로 설명이 필요합니다. 경로/probe 부재는 서비스·격리 계약을 독립적으로 증명하지 못합니다.

</details>

8. RT 실험에서 원래 import RT를 제거하기 전에 미사용 수동 RT를 추가하는 이유는?
   - A) RD를 몰래 바꾸기 위해서입니다.
   - B) 수동 목록이 비면서 자동 RT로 돌아가는 것을 방지하기 위해서이며 유효 목록은 별도로 확인해야 합니다.
   - C) 모든 EVPN peer를 종료하기 위해서입니다.

<details>
<summary>정답 보기</summary>

**정답: B**

**설명:** 자동 RT 동작 때문에 단순 삭제 실험이 성립하지 않을 수 있습니다. 원래 소속이 더 이상 유효하지 않고 임시 RT를 export하는 경로가 없는지 확인합니다. 복원할 때는 s1 red import 목록에 원래 RT를 추가한 뒤 임시 항목만 제거합니다.

</details>

9. s1 underlay MTU 축소 후 작은 probe가 성공하고 큰 probe도 외부 단편화와 함께 성공합니다. 보고서에는 무엇을 써야 하나요?
   - A) 손실이 없으므로 MTU 영향이 없었습니다.
   - B) 내부 DF가 설정되었으므로 반드시 black hole이 발생했습니다.
   - C) 관찰된 영향은 단편화이며 내부 DF만으로 외부 DF 동작이 확정되지는 않았습니다.

<details>
<summary>정답 보기</summary>

**정답: C**

**설명:** 캡슐화 크기, 외부 단편화, 오류, 인접 관계 변화를 기록합니다. 모델과 구현이 영향을 결정하므로 고정된 손실 결과를 만들어내면 안 됩니다. 알려진 인터페이스 사전 상태 1600바이트로 복원하고 두 크기와 VRF 대조군을 재검사합니다.

</details>

10. RT 장애 주입과 회복 성공을 뒷받침하는 증거는?
   - A) 장애 중 전역 경로는 유지되고 red import/probe는 실패하지만 blue와 h2의 로컬 gateway는 정상이며 복원 후 원래 RT·경로·red probe가 회복됩니다.
   - B) 빈 전역 테이블 하나만 있습니다.
   - C) 초기화 반복과 global prune 끝에 오류가 보이지 않습니다.

<details>
<summary>정답 보기</summary>

**정답: A**

**설명:** 정상 대조군이 import 정책 장애와 전체 장애를 구분합니다. 지정 객체의 정확한 복원이 필요합니다. FRR VLAN/VRF 초기화가 멱등적이라고 가정하지 않으며 관측 누락이나 광범위한 정리는 복구 증거가 아닙니다.

</details>

완료 기준: revision과 복원 결과가 포함된 L2/L3/RT/MTU 증거 행렬을 제출하거나 실습을 명시적으로 **미실행**으로 표시합니다.
