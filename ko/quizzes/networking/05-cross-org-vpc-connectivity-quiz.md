# Cross-Org VPC 연결 퀴즈

이 퀴즈는 서로 다른 AWS Organization 간 VPC 연결 5가지 옵션에 대한 이해도를 테스트합니다.

## 객관식 문제

1. 다른 Organization의 계정에 Transit Gateway를 공유할 때 반드시 필요한 것은?
   - A) 두 Organization을 하나로 병합
   - B) `--allow-external-principals` 옵션과 수신 측의 초대 수락
   - C) 양쪽 Organization 관리 계정 간 VPN 연결
   - D) AWS Support 티켓을 통한 수동 승인

<details>

<summary>정답 보기</summary>

**정답: B) `--allow-external-principals` 옵션과 수신 측의 초대 수락**

**설명:**
AWS RAM으로 조직 외부 계정에 리소스를 공유하려면 리소스 공유 생성 시 `--allow-external-principals`를 명시해야 하며, 수신 계정이 `accept-resource-share-invitation`으로 초대를 수락하기 전까지 리소스가 보이지 않습니다. 같은 조직 내부의 OU 기반 자동 공유와 달리, 조직 경계를 넘는 공유는 계정 ID 명시 + 명시적 수락이라는 절차가 강제됩니다.
</details>

2. 공유된 TGW에 다른 Organization의 계정이 VPC attachment를 생성하면 어떤 상태가 되는가?
   - A) 즉시 available 상태로 활성화된다
   - B) pendingAcceptance 상태로 멈추고 TGW 소유 계정이 수락해야 활성화된다
   - C) 요청이 거부되어 attachment를 만들 수 없다
   - D) 24시간 후 자동으로 활성화된다

<details>

<summary>정답 보기</summary>

**정답: B) pendingAcceptance 상태로 멈추고 TGW 소유 계정이 수락해야 활성화된다**

**설명:**
TGW의 auto-accept가 비활성(기본값)일 때, 타 계정의 attachment는 `pendingAcceptance`에서 멈추고 TGW 소유자가 `accept-transit-gateway-vpc-attachment`를 실행해야 활성화됩니다. 이것이 "TGW 소유 계정이 네트워크를 중앙 통제한다"는 모델이 API 레벨에서 강제되는 지점입니다. 공유받은 계정은 attachment 생성만 가능하고 라우트 테이블은 변경할 수 없습니다.
</details>

3. 동일 AZ에서 실측한 결과, Transit Gateway 홉당 추가되는 지연(p50)의 수준은?
   - A) 약 0.02ms — 사실상 0
   - B) 약 0.4~0.6ms — sub-millisecond 수준
   - C) 약 3~5ms
   - D) 약 10ms 이상

<details>

<summary>정답 보기</summary>

**정답: B) 약 0.4~0.6ms — sub-millisecond 수준**

**설명:**
c7g.large + 순수 EC2 응답자 + TCP_RR persistent(1,500샘플/경로) 실측에서 TGW 1홉 비용은 TCP_RR +0.571ms / ICMP +0.410ms로 나타났습니다. 참고로 VPC Peering의 지연 비용은 측정 한계 내 0(기준선과 동일)이고, NLB 홉은 +0.79ms로 TGW 홉보다 오히려 큽니다. 버스터블 인스턴스나 다단 프록시를 끼운 측정은 이 sub-ms 신호를 노이즈에 묻어버리므로 측정 설계가 중요합니다.
</details>

4. VPC Lattice 타깃 인스턴스의 Security Group 설정에서 흔히 빠지는 함정은?
   - A) 아웃바운드 규칙을 모두 열어야 한다
   - B) Lattice data plane이 link-local(169.254.171.0/24)에서 오므로 관리형 프리픽스 리스트를 허용해야 한다
   - C) SG 대신 NACL만 사용해야 한다
   - D) 포트 443만 허용하면 된다

<details>

<summary>정답 보기</summary>

**정답: B) Lattice data plane이 link-local(169.254.171.0/24)에서 오므로 관리형 프리픽스 리스트를 허용해야 한다**

**설명:**
VPC Lattice의 트래픽(헬스체크 포함)은 VPC CIDR가 아닌 link-local 대역 169.254.171.0/24에서 도착합니다. 타깃 SG가 VPC CIDR만 허용하면 헬스체크가 전부 UNHEALTHY가 됩니다. 해결책은 관리형 프리픽스 리스트 `com.amazonaws.<region>.vpc-lattice`를 SG 인바운드에 추가하는 것입니다.
</details>

5. IP CIDR가 겹치는 두 Organization의 VPC를 연결해야 할 때 사용 가능한 옵션은?
   - A) VPC Peering과 TGW Peering
   - B) TGW RAM 공유
   - C) PrivateLink와 VPC Lattice
   - D) 어떤 옵션으로도 불가능하다

<details>

<summary>정답 보기</summary>

**정답: C) PrivateLink와 VPC Lattice**

**설명:**
VPC Peering, TGW RAM 공유, TGW Peering은 모두 L3 라우팅 기반이므로 CIDR가 겹치면 사용할 수 없습니다. PrivateLink는 Consumer VPC 안의 ENI로, VPC Lattice는 link-local 주소 기반으로 동작하므로 양쪽 CIDR가 겹쳐도 무관합니다. M&A나 MSP 전환처럼 IP 재설계가 불가능한 상황에서 이 두 옵션이 유일한 선택지입니다.
</details>

6. TGW Peering 구성 시 라우팅에 대한 설명으로 올바른 것은?
   - A) BGP로 라우트가 자동 전파된다
   - B) BGP 미지원이므로 양쪽 TGW 라우트 테이블에 정적 라우트를 수동 등록해야 한다
   - C) VPC 라우트 테이블만 수정하면 된다
   - D) 라우팅 설정이 전혀 필요 없다

<details>

<summary>정답 보기</summary>

**정답: B) BGP 미지원이므로 양쪽 TGW 라우트 테이블에 정적 라우트를 수동 등록해야 한다**

**설명:**
TGW Peering attachment는 BGP를 지원하지 않아 라우트 자동 전파가 없습니다. 양쪽 TGW 라우트 테이블에 상대측 CIDR로 향하는 정적 라우트를 직접 넣어야 하며, 실측에서도 정적 라우트 등록 전에는 트래픽이 흐르지 않았습니다. 추가로 TGW에서는 정적 라우트가 전파(propagated) 라우트보다 우선한다는 점, 그리고 피어링 attachment ID가 요청자/수락자 측에서 서로 다르다는 점도 운영 시 주의할 포인트입니다.
</details>
