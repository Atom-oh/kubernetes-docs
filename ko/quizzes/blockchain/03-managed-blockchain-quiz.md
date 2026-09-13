# Amazon Managed Blockchain 퀴즈

이 퀴즈는 AMB의 구성, 관리형과 자체 운영의 경계, 서비스 종료 위험에 대한 이해도를 테스트합니다.

## 객관식 문제

1. AMB 제공 방식은 어떻게 비교해야 합니까?
   - A) 세 구성요소 모두 같은 문제를 다른 가격대로 해결한다
   - B) Fabric/전용 node·serverless Access·Query API를 구분하고 제공 방식별 과금과 기능을 확인한다
   - C) 개발·스테이징·프로덕션 환경별로 나뉜다
   - D) 퍼블릭·프라이빗·하이브리드 체인별로 나뉜다

<details>

<summary>정답 보기</summary>

**정답: B) Fabric/전용 node·serverless Access·Query API를 구분하고 제공 방식별 과금과 기능을 확인한다**

**설명:**
AMB 전체가 node별 과금은 아닙니다. 전용 자원·serverless RPC 요청·indexed Query API는 가격과 지원 범위가 다릅니다.
</details>

2. AMB 관리형 노드로 해결되지 않는 것 중 가장 중요한 구분은?
   - A) CloudWatch 메트릭 수집
   - B) 검증자(validator) 운영 — 관리형 노드는 조회·거래 제출용이며 PoS 스테이킹은 키 관리·서명 가용성·slashing 위험이라는 다른 요구사항
   - C) IAM 기반 접근 제어
   - D) VPC 사설 연결

<details>

<summary>정답 보기</summary>

**정답: B) 검증자(validator) 운영 — 관리형 노드는 조회·거래 제출용이며 PoS 스테이킹은 키 관리·서명 가용성·slashing 위험이라는 다른 요구사항**

**설명:**
AMB Access의 public-chain node는 체인 데이터를 읽고 거래를 제출하는 용도입니다. PoS validation에는 서명 가용성과 slashing protection이 추가로 필요합니다. 조정되지 않은 signer는 같은 validator에 충돌하는 slashable 메시지를 만들 수 있지만 동일 서명의 중복이 자동으로 slashing 대상이 되지는 않습니다. 일반 배포는 활성 signer 하나와 fencing failover·보존된 slashing 이력을 사용하며 분산 signer에는 검증된 조정이 필요합니다. AMB node 접근이 이 validator 설계를 제공하지는 않으므로 staking에는 별도 운영 또는 전문 서비스가 필요합니다.
</details>

3. 관리형 vs 자체 운영 의사결정에서 1단계로 제시된 질문은?
   - A) 비용이 얼마인가
   - B) 노드가 정말 필요한가 — 데이터 조회만이면 AMB Query나 서드파티 RPC로 충분할 수 있음
   - C) 어떤 체인을 쓸 것인가
   - D) 운영 인력이 몇 명인가

<details>

<summary>정답 보기</summary>

**정답: B) 노드가 정말 필요한가 — 데이터 조회만이면 AMB Query나 서드파티 RPC로 충분할 수 있음**

**설명:**
의사결정 순서는 ① 노드가 정말 필요한가 → ② 통제가 필요한가 → ③ 비용 → ④ 혼합 가능한가입니다. 노드 운영은 비용과 부담이 큰 선택이므로 필요성을 먼저 확인해야 하고, **1단계에서 걸러지는 경우가 많습니다.** 2단계에서는 클라이언트 선택·튜닝·아카이브·검증자 참여 중 하나라도 필요하면 자체 운영입니다.
</details>

4. Amazon QLDB 사례가 아키텍처 결정에 주는 교훈은?
   - A) 관리형 서비스는 항상 자체 운영보다 저렴하다
   - B) 관리형 서비스도 종료될 수 있고, 제시되는 마이그레이션 경로가 기능적으로 동등하지 않을 수 있다 — Aurora PostgreSQL로 옮기면 암호학적 검증 가능성을 잃는다
   - C) 원장 데이터베이스는 블록체인으로만 구현해야 한다
   - D) AWS 서비스는 GA 후 5년간 지원이 보장된다

<details>

<summary>정답 보기</summary>

**정답: B) 관리형 서비스도 종료될 수 있고, 제시되는 마이그레이션 경로가 기능적으로 동등하지 않을 수 있다 — Aurora PostgreSQL로 옮기면 암호학적 검증 가능성을 잃는다**

**설명:**
QLDB는 2018년 발표, 2019년 GA되었고 2024년 7월 지원 종료가 발표되어 **2025년 7월 31일 서비스가 종료**되었습니다. AWS가 제시한 경로는 Aurora PostgreSQL이었는데, 원장 유사 기능은 확장으로 구현할 수 있지만 QLDB의 핵심 가치였던 "변조되지 않았음을 수학적으로 증명"하는 부분은 대체되지 않습니다. 교훈은 ① 관리형에도 종료 위험이 있다 ② "대체 서비스 있음"이 "같은 것을 제공함"은 아니다 ③ 통보 기간이 짧을 수 있다 ④ 표준 기술은 이전이 쉽다입니다.
</details>

5. 서비스 종료 위험에 대한 가장 실효성 있는 완화 방법은?
   - A) 여러 클라우드 제공자에 동시 배포
   - B) 표준 프로토콜 사용 + 추상화 계층 — 애플리케이션이 표준 RPC 인터페이스로 말하게 하면 백엔드를 AMB·자체 노드·서드파티로 바꿀 수 있음
   - C) 관리형 서비스를 쓰지 않음
   - D) AWS와 장기 계약 체결

<details>

<summary>정답 보기</summary>

**정답: B) 표준 프로토콜 사용 + 추상화 계층 — 애플리케이션이 표준 RPC 인터페이스로 말하게 하면 백엔드를 AMB·자체 노드·서드파티로 바꿀 수 있음**

**설명:**
Ethereum JSON-RPC 같은 표준 인터페이스는 호환 backend 교체를 쉽게 만들 수 있지만 AMB 고유 API는 결합을 만듭니다. 필요한 데이터를 독립 보관하고 resync/이전 시간을 측정합니다. 사용 전에 키 복구와 종료를 계획해야 하며 **KMS 개인 signing key는 export할 수 없습니다**. Public-key download·imported key material의 backup·CloudHSM extractability/wrapping 규칙·account/contract rotation을 구분합니다. 관리형 키를 선택한다고 이전 가능한 private-key backup이 자동 제공되지는 않습니다.
</details>

6. AMB의 IAM 통합이 실질적 이점인 이유는?
   - A) IAM이 블록체인 거래에 서명해 주기 때문
   - B) 자체 운영 노드의 RPC 엔드포인트는 별도 인증 체계를 만들거나 네트워크 계층으로만 통제해야 하는데, AMB는 사내 권한 체계와 일관되게 IAM으로 통제할 수 있기 때문
   - C) IAM이 키를 자동 백업하기 때문
   - D) IAM 정책으로 체인 데이터를 수정할 수 있기 때문

<details>

<summary>정답 보기</summary>

**정답: B) 자체 운영 노드의 RPC 엔드포인트는 별도 인증 체계를 만들거나 네트워크 계층으로만 통제해야 하는데, AMB는 사내 권한 체계와 일관되게 IAM으로 통제할 수 있기 때문**

**설명:**
자체 운영 노드의 RPC 엔드포인트에 접근 제어를 걸려면 별도 인증 체계를 구축하거나 Security Group·NetworkPolicy 같은 네트워크 계층으로만 통제해야 합니다. AMB는 IAM 정책으로 접근을 통제할 수 있어 사내 권한 체계와 일관되게 관리됩니다. 여기에 CloudWatch 메트릭·로그, CloudTrail 관리 API 감사, VPC 엔드포인트/PrivateLink 사설 연결, KMS 키 관리 통합이 더해집니다.
</details>

7. AMB 문서에서 `확인 필요`로 표시된 항목은?
   - A) AMB Query가 API로 데이터를 제공한다는 점
   - B) AMB의 지원 체인 목록·리전 가용성·프리뷰/GA 상태와, AMB의 향후 로드맵·서비스 지속 계획
   - C) QLDB가 2025년 7월 31일 종료되었다는 점
   - D) AMB가 Hyperledger Fabric을 지원한다는 점

<details>

<summary>정답 보기</summary>

**정답: B) AMB의 지원 체인 목록·리전 가용성·프리뷰/GA 상태와, AMB의 향후 로드맵·서비스 지속 계획**

**설명:**
지원 체인과 상태는 시점에 따라 변합니다 — 확인된 변경으로 Ethereum Goerli 테스트넷 종료(2024년 4월 1일)와 Polygon Mumbai 테스트넷 종료(2024년 4월 15일)가 있고, Polygon PoS 메인넷은 한때 Public Preview였습니다. 또한 조사 시점에 AMB 전체의 지원 종료 발표는 확인되지 않았으나 이는 "종료 계획이 없다"는 증거가 아니라 "발표를 찾지 못했다"는 뜻이므로, 장기 시스템이라면 AWS 계정 담당자에게 로드맵을 직접 확인해야 합니다.
</details>
