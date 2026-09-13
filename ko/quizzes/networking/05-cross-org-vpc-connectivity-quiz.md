# Cross-Org VPC 연결 퀴즈

보고된 측정값과 AWS 플랫폼 요구사항을 구분해 확인하세요.

## 1. 소유자 Organization 밖의 계정에 TGW를 공유할 때 필요한 것은 무엇인가요?

- A. 두 Organization 병합
- B. 공유에서 외부 principal을 허용하고 수신 계정에서 RAM 초대 수락
- C. 관리 계정 간 VPN 연결
- D. 지원 티켓 승인

<details>
<summary>정답 보기</summary>

B. 공유가 외부 계정을 허용해야 하고 수신자가 초대를 수락한 뒤 공유 리소스를 사용할 수 있습니다. CreateResourceShare의 allowExternalPrincipals 기본값은 true이므로 --allow-external-principals라는 CLI 플래그 자체가 항상 필요한 것은 아닙니다. 실제 구성과 IAM/공유 제한을 확인하세요.

</details>

## 2. AutoAcceptSharedAttachments가 비활성일 때, 공유 TGW의 유효한 계정 간 VPC attachment에는 어떤 절차가 필요한가요?

- A. 수락이 필요 없음
- B. TGW 소유자가 pending 공유 attachment 수락
- C. 서로 다른 Organization에서는 attachment 생성 불가
- D. 항상 24시간 후 활성화

<details>
<summary>정답 보기</summary>

B. 공유 attachment 자동 수락은 기본 비활성입니다. RAM 공유 수락과 VPC attachment 수락은 별도 단계이며 자동 수락을 켜면 두 번째 절차가 달라집니다. TGW 소유자가 TGW 라우트 테이블을 통제하지만 수신 계정도 자신의 VPC 라우트와 보안 설정을 통제합니다.

</details>

## 3. 보고서의 TCP_RR M3−M2 비교에서 직접 알 수 있는 것은 무엇인가요?

- A. 모든 TGW 홉에 동일한 편도 지연이 추가됨
- B. 보고된 경로 중앙값 차이는 0.619−0.048 = 0.571ms
- C. AWS가 보장하는 지연 SLA
- D. GPU 학습 처리량

<details>
<summary>정답 보기</summary>

B. 보고된 왕복 중앙값의 관측 차이이며 순수 구성 요소 측정이나 홉당 상수가 아닙니다. 같은 회차에서 두 TGW 경로의 TCP_RR 중앙값은 한 TGW 경로보다 낮습니다. 더 넓은 결론에는 원시 표본, 불확실성과 실제 워크로드 측정이 필요하며 이번 검토는 벤치마크를 재현하지 않았습니다.

</details>

## 4. 시험한 Lattice HTTP 서비스/VPC 연결 경로의 대상 SG에서 확인할 것은 무엇인가요?

- A. 모든 인바운드·아웃바운드 포트 개방
- B. 실제 대상·상태 검사 포트에 올바른 리전/IP 계열 관리형 접두사 목록 허용
- C. 보안 그룹을 NACL로 대체
- D. 백엔드와 무관하게 TCP 443만 허용

<details>
<summary>정답 보기</summary>

B. Lattice 트래픽은 관리형 접두사 목록의 주소에서 도착할 수 있으므로 클라이언트 VPC CIDR만 허용하면 충분하지 않습니다. 과거 169.254.171.0/24 예제는 전체 주소의 보편적 정의가 아닙니다. 문서화된 목록과 구성 포트를 사용하고 엔드포인트/리소스 게이트웨이 경로의 별도 제어도 확인하세요.

</details>

## 5. 비교한 패턴 중 겹치는 주소 범위를 직접 라우팅하지 않고 중복 VPC CIDR 간 서비스를 노출할 수 있는 것은 무엇인가요?

- A. 직접 VPC peering
- B. 변경 없는 직접 TGW 라우팅
- C. PrivateLink 서비스 접근 또는 VPC Lattice 서비스 접근
- D. 어떤 아키텍처로도 주소 중복 처리 불가

<details>
<summary>정답 보기</summary>

C. 이는 무제한 양방향 VPC 라우팅이 아니라 서비스 접근입니다. 직접 VPC peering은 중복 CIDR를 연결할 수 없고 라우팅 설계에는 모호하지 않은 주소 계획이 필요합니다. NAT와 주소 재설계도 대안이므로 PrivateLink/Lattice만이 유일한 가능한 아키텍처는 아닙니다.

</details>

## 6. 직접 TGW-to-TGW peering의 라우팅 설명으로 맞는 것은 무엇인가요?

- A. Peering이 BGP로 모든 라우트를 자동 전파
- B. 정적 피어 라우트와 필요한 VPC 라우트를 명시적으로 구성
- C. VPC 테이블만 중요
- D. 수락하면 모든 필요한 라우트가 자동 생성

<details>
<summary>정답 보기</summary>

B. Peering attachment는 정적 라우트를 사용하며 자동화로 관리할 수 있습니다. TGW는 가장 구체적인 접두사를 먼저 고르고 같은 접두사에서는 정적 라우트가 전파 라우트보다 우선합니다. 수락자 리전에서 pending peering 요청의 attachment ID로 수락하세요. NotFound만으로 요청자/수락자 ID가 반드시 다르다고 판단할 수는 없습니다.

</details>

[본문으로 돌아가기](../../networking/05-cross-org-vpc-connectivity.md)
