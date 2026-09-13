# Amazon Managed Blockchain

> **마지막 업데이트**: 2026년 9월 12일

## 이 문서에서 다루는 것

- Amazon Managed Blockchain(AMB)이 [자체 운영](./02-nodes-on-eks.md)의 어떤 부담을 대신해 주고 무엇을 못 하는가
- 관리형과 자체 운영의 선택 기준 — 그리고 이 판단에 반드시 넣어야 할 변수
- AWS 원장·블록체인 서비스 포트폴리오의 변화가 아키텍처 결정에 시사하는 것

## AMB의 구성

AMB는 하나의 서비스가 아니라 성격이 다른 구성요소들의 묶음입니다.

| 제공 방식 | 제공 기능 | 비용/운영 경계 |
|---|---|---|
| **Hyperledger Fabric** | Permissioned network/member/peer 리소스 | Component/node/storage·network 요금. 고객 앱·channel·identity 책임 유지 |
| **전용 Ethereum node** | 지원 network의 관리형 node 접근 | 해당 node/storage/network 요금 |
| **Serverless AMB Access** | 전용 node provisioning 없는 지원 public-chain RPC | 요청 과금. 현재 chain·method·Region 확인 |
| **AMB Query** | Indexed blockchain-data API | API/요청 과금과 query 지원 범위 확인. 임의 full-node RPC 대체는 아님 |

제공 방식마다 provisioning·API·과금·책임 모델이 다릅니다. 필요한 network와 method부터 선택하고 AMB 전체를 하나의 node별 과금 서비스로 취급하지 않습니다.

::: warning 확인 필요
AMB의 구성요소별 **지원 프레임워크·체인 목록, 리전 가용성, 프리뷰/GA 상태는 시점에 따라 변합니다.** 확인된 변경 사례로는 Ethereum Goerli 테스트넷 지원 종료(2024년 4월 1일)와 Polygon Mumbai 테스트넷 지원 종료(2024년 4월 15일)가 있으며, Polygon PoS 메인넷은 한때 **Public Preview** 상태로 제공되었습니다.

**설계 확정 전에 [AMB 공식 문서](https://docs.aws.amazon.com/managed-blockchain/)와 리전별 가용성을 직접 확인**하십시오. 이 문서는 특정 체인의 현재 지원 상태를 단정하지 않습니다.
:::

## 무엇을 대신해 주는가

[자체 운영 문서](./02-nodes-on-eks.md)에서 다룬 부담과 대조하면 경계가 분명해집니다.

| 자체 운영의 부담 | AMB에서 |
|---|---|
| StatefulSet·볼륨·스토리지 클래스 설계 | **대신해 줌** |
| 디스크 증가 감시와 볼륨 확장 | **대신해 줌** |
| 초기 동기화와 스냅샷 관리 | **대신해 줌** |
| P2P 노출·광고 주소 설정 | **대신해 줌** |
| 클라이언트 버전 업그레이드 | **대신해 줌** |
| 하드포크 대응 | **대신해 줌** (관리형 노드) |
| Fabric 인증서 발급 체계 | **상당 부분 대신해 줌** (관리형 CA) |
| 노드 가용성·모니터링 기반 | **대신해 줌** |

관리형 제공자는 선택한 제공 방식에서 약속한 node/service 유지보수를 담당합니다. 지원 network·upgrade notice·API 동작·고객 앱 책임을 확인하며 프로토콜 주기 자체가 AWS 서비스 보장을 정의하지는 않습니다.

## 무엇을 못 하는가

여기가 판단의 핵심입니다.

| 항목 | 제약 |
|---|---|
| **클라이언트 선택** | AMB가 제공하는 클라이언트·버전으로 제한. [클라이언트 다양성](./02-nodes-on-eks.md) 전략을 직접 통제할 수 없음 |
| **세밀한 튜닝** | 캐시 크기, 프루닝 모드, 커널 파라미터 등을 조정할 수 없음 |
| **지원 체인** | AMB가 지원하는 것만. 신규·소규모 체인은 대개 미지원 |
| **아카이브 모드** | 제공 범위가 제한적일 수 있음 |
| **검증자 운영** | 관리형 노드는 대개 **조회·거래 제출용**. 스테이킹 검증자 운영은 별개 문제 |
| **리전·네트워크 구성** | AMB가 지원하는 리전과 연결 방식 |
| **비용 구조** | 제공 방식에 따라 provisioned node/component 비용 또는 serverless request/API 요금. 동일한 기능 범위와 사용량 비교 필요 |

**검증자 운영이 특히 중요한 구분**입니다. AMB Access의 퍼블릭 체인 노드는 체인 데이터를 읽고 거래를 제출하는 용도이며, **PoS 검증자로 참여해 스테이킹 보상을 받는 것은 다른 요구사항**입니다(키 관리, 서명 가용성, slashing 위험). 스테이킹이 목적이라면 AMB로 해결되지 않습니다.

## 선택 기준

| 상황 | 권고 |
|---|---|
| 체인 데이터를 **읽기만** 함 | **AMB Query** — 노드 자체가 불필요 |
| 조회 + 거래 제출, 운영 인력 제한적 | **AMB Access 관리형 노드** |
| 특정 클라이언트·튜닝이 필요 | **자체 운영** |
| **검증자·스테이킹** | **자체 운영** (또는 전문 스테이킹 서비스) |
| AMB 미지원 체인 | **자체 운영** |
| 컨소시엄 Fabric, 빠른 시작 | **AMB Access Fabric** |
| Fabric에 세밀한 제어 필요 | **자체 운영 + 오퍼레이터** |
| 대량 트래픽, 비용 최적화 목표 | **자체 운영** (비교 필요) |

### 의사결정 순서

**1단계 — 노드가 정말 필요한가?** 데이터 조회만이면 AMB Query나 서드파티 RPC 제공자로 충분할 수 있습니다. 노드 운영은 비용과 부담이 큰 선택이므로 **필요성을 먼저 확인**하십시오.

**2단계 — 통제가 필요한가?** 클라이언트 선택, 튜닝, 아카이브, 검증자 참여 중 하나라도 필요하면 자체 운영입니다.

**3단계 — 비용은?** 선택한 제공 방식의 전용 자원·serverless request·Query API 요금을 적용합니다. 같은 기능 범위와 가용성 조건에서 EC2/EKS·storage·transfer·redundancy·운영 인력 비용을 비교하며 node 수만으로 결정되는 보편적 손익분기 실측은 없습니다.

**4단계 — 혼합 가능한가?** 대개 가능하고, 실무에서 합리적인 경우가 많습니다 — 예를 들어 일반 조회는 관리형, 특수 용도는 자체 운영.

## AWS 원장·블록체인 포트폴리오의 변화 — 반드시 고려할 변수

이 문서에서 가장 중요한 부분입니다. **기술 비교만으로 결정하면 놓치는 리스크**가 있습니다.

### Amazon QLDB의 종료

Amazon QLDB(Quantum Ledger Database)는 **암호학적으로 검증 가능한 변조 불가 트랜잭션 로그**를 제공하는 관리형 원장 데이터베이스였습니다. 2018년 re:Invent에서 발표되고 2019년 GA되었습니다.

| 시점 | 사건 |
|---|---|
| 2018년 | re:Invent에서 발표 |
| 2019년 | GA |
| 2024년 7월 | 지원 종료 발표 |
| **2025년 7월 31일** | **서비스 종료** |

AWS가 제시한 마이그레이션 경로는 **Amazon Aurora PostgreSQL**이었습니다. 그런데 여기에 중요한 지점이 있습니다 — **Aurora PostgreSQL로 옮기면 QLDB의 핵심 가치였던 암호학적 검증 가능성을 잃습니다.** 원장 유사 기능은 확장으로 구현할 수 있지만, "변조되지 않았음을 수학적으로 증명"하는 부분은 대체되지 않습니다.

### 이것이 시사하는 것

QLDB와 AMB는 다른 서비스이고, **QLDB의 종료가 AMB의 종료를 의미하지는 않습니다.** 그러나 아키텍처 결정에 넣어야 할 교훈이 있습니다.

| 교훈 | 실무 적용 |
|---|---|
| **관리형 서비스에도 종료 위험이 있다** | 특히 채택률이 낮은 특수 목적 서비스 |
| **마이그레이션 경로가 기능적으로 동등하지 않을 수 있다** | "대체 서비스 있음"이 "같은 것을 제공함"은 아님 |
| **종료 통보 기간이 짧을 수 있다** | 이전 작업에 필요한 시간을 미리 계산 |
| **표준 기술은 이전이 쉽다** | 오픈소스 프로토콜 기반이면 자체 운영으로 이전 가능 |

::: warning 확인 필요
**AMB의 향후 로드맵과 서비스 지속 계획은 이 문서에서 확인하지 못했습니다.** 조사 시점에 AMB 전체의 지원 종료 발표는 확인되지 않았으나, 이는 "종료 계획이 없다"는 증거가 아니라 **"발표를 찾지 못했다"**는 뜻입니다.

**장기 시스템을 설계한다면 AWS 계정 담당자나 솔루션 아키텍트에게 서비스 로드맵을 직접 확인**하시기 바랍니다. 특히 금융권처럼 시스템 수명이 긴 환경에서는 이 확인이 기술 비교보다 중요할 수 있습니다.
:::

### 종료 위험을 줄이는 설계

이 리스크는 제거할 수 없고 **완화**할 수 있습니다.

| 완화 방법 | 내용 |
|---|---|
| **표준 프로토콜 유지** | Ethereum·Fabric 같은 오픈 프로토콜을 쓰면, 관리형이 사라져도 자체 운영이나 다른 제공자로 이전 가능 |
| **추상화 계층** | 애플리케이션이 AMB API에 직접 의존하지 않게 함. RPC 인터페이스를 추상화하면 백엔드 교체가 쉬움 |
| **데이터 독립성 확보** | 체인 데이터를 자체 인덱스·웨어하우스에도 보관. 제공자가 바뀌어도 과거 데이터 유지 |
| **키 복구와 종료 전략** | KMS 개인 signing key는 export할 수 없습니다. 자금 입금/신원 등록 전에 복구·종료를 설계하고 public-key download·imported-key backup·CloudHSM backup/wrapping 규칙·account/contract rotation을 구분 |
| **이전 시간 산정** | 노드 재동기화, 데이터 이전에 걸리는 시간을 미리 측정해 두면 통보 기간 내 대응 가능성을 판단할 수 있음 |

**"추상화 계층"이 가장 실효성 있는 대응**입니다. 애플리케이션이 표준 RPC 인터페이스(Ethereum JSON-RPC 등)로 말하게 하면, 백엔드가 AMB든 자체 노드든 서드파티든 바꿀 수 있습니다. AMB 고유 API에 직접 결합하면 이 유연성을 잃습니다.

## AWS 서비스와의 연계

AMB의 실질적 이점 중 하나가 AWS 생태계 통합입니다.

| 연계 | 용도 |
|---|---|
| **IAM** | 접근 제어 — 체인 노드 접근에 IAM 정책 적용 |
| **CloudWatch** | 메트릭·로그 |
| **CloudTrail** | 관리 API 호출 감사 |
| **VPC 엔드포인트 / PrivateLink** | 사설 연결 |
| **KMS** | 키 관리 |

**IAM 통합이 특히 유용합니다.** 자체 운영 노드의 RPC 엔드포인트는 별도 인증 체계를 만들어야 하는데(또는 네트워크 계층으로만 통제), AMB는 IAM으로 통제할 수 있습니다. 사내 권한 체계와 일관되게 관리된다는 뜻입니다.

사설 연결 관련해서는 [VPC Lattice 섹션](../service-mesh/vpc-lattice/README.md)에서 다룬 개념들이 적용될 수 있습니다 — 다만 **AMB와 Lattice의 직접 연계 지원 여부는 별개 확인이 필요한 항목**입니다([VPC Lattice 제약사항](../service-mesh/vpc-lattice/06-constraints.md)의 미확정 항목과 같은 성격).

## 자체 운영과의 비교 정리

| 항목 | AMB | 자체 운영 (EKS/EC2) |
|---|---|---|
| **초기 구축 시간** | 짧음 | 길음 (동기화 포함) |
| **운영 인력** | 적음 | 많음 |
| **하드포크 대응** | AWS | **직접** |
| **디스크 증가 관리** | AWS | **직접** |
| **클라이언트 선택** | 제한 | **자유** |
| **튜닝 가능 범위** | 제한 | **전체** |
| **검증자 운영** | 어려움 | **가능** |
| **지원 체인** | AMB 목록 | **제약 없음** |
| **비용 구조** | 제공 방식에 따라 provisioned node/component 비용 또는 serverless request/API 요금. 동일한 기능 범위와 사용량 비교 필요 |
| **IAM 통합** | **기본 제공** | 직접 구축 |
| **서비스 수명 위험** | 관리형 제공 방식의 가용성/지원 변경 가능 | Open-source/client 유지보수·protocol·인프라 의존성도 존재 |
| **이전 가능성** | 표준 프로토콜이면 가능 | — |

## 정리

- AMB는 **AMB Access Fabric**(컨소시엄 네트워크), **AMB Access 퍼블릭 노드**(노드 운영 대행), **AMB Query**(노드 없는 데이터 조회)의 묶음이고, 각각 다른 문제를 풉니다.
- 관리형 유지보수는 node 운영 작업을 줄일 수 있지만 제공 방식별 책임·upgrade notice·앱 검증은 여전히 필요합니다.
- 못 하는 것 중 가장 중요한 구분은 **검증자 운영**입니다. 관리형 노드는 조회·제출용이며 스테이킹은 다른 요구사항입니다.
- 의사결정 순서: **① 노드가 정말 필요한가 → ② 통제가 필요한가 → ③ 비용 → ④ 혼합 가능한가.** 1단계에서 걸러지는 경우가 많습니다.
- **QLDB가 2025년 7월 31일 종료**되었고, 마이그레이션 경로(Aurora PostgreSQL)는 **암호학적 검증 가능성을 제공하지 않습니다.** 관리형 서비스에도 종료 위험이 있고, 대체 서비스가 기능적으로 동등하지 않을 수 있다는 사례입니다.
- 이 리스크의 가장 실효성 있는 완화는 **표준 프로토콜 사용 + 추상화 계층**입니다. AMB 고유 API에 직접 결합하지 않으면 백엔드를 바꿀 수 있습니다.
- **장기 시스템이라면 AWS 계정 담당자에게 서비스 로드맵을 직접 확인**하십시오. 기술 비교보다 중요할 수 있습니다.

다음: [금융권 관점](./04-financial-services.md)에서 규제·프라이버시·심의 쟁점을 다룹니다.

## 참고 자료

- [Amazon Managed Blockchain 문서](https://docs.aws.amazon.com/managed-blockchain/)
- [AMB Hyperledger Fabric Developer Guide](https://docs.aws.amazon.com/managed-blockchain/latest/hyperledger-fabric-dev/what-is-managed-blockchain.html)
- [Amazon Managed Blockchain FAQs](https://aws.amazon.com/managed-blockchain/faqs/)
- [AMB Query 문서 이력](https://docs.aws.amazon.com/managed-blockchain/latest/ambq-dg/doc-history.html)
- [AMB Access Polygon 문서 이력](https://docs.aws.amazon.com/managed-blockchain/latest/ambp-dg/doc-history.html)
- [EKS에서 블록체인 노드 운영](./02-nodes-on-eks.md) — 자체 운영 시의 부담

- [제공 방식별 AMB 요금](https://aws.amazon.com/managed-blockchain/pricing/)
- [AWS KMS 비대칭 키 명세](https://docs.aws.amazon.com/kms/latest/developerguide/asymmetric-key-specs.html) — public key 접근과 private key export는 다름
