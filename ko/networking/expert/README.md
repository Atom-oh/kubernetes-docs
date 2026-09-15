# 네트워크 전문가 과정

> **자료 확인일**: 2026년 9월 15일
>
> **학습 환경**: 호스트 실습은 Ubuntu Server 24.04 LTS 또는 Rocky Linux 9의 폐기 가능한 VM. 라우팅·EVPN 도구와 클라우드 환경은 장별로 준비합니다.

[입문 과정](../beginner/README.md) 다음에 공부할 심화 워크북입니다. 프로토콜의 원리를 코드·패킷과 연결하고, 라우팅 정책·Linux 성능·클라우드 설계를 실제 증거로 평가합니다.

여기서 전문가 수준의 목표는 **무엇이 정상이어야 하는지 정의하고, 관측으로 가설을 검증하며, 변경의 영향과 복구를 설명하는 능력**입니다. 특정 기간의 수강이나 자격증 취득만으로 그 능력이 보장된다는 뜻은 아닙니다.

## 시작 조건 {#entry-check}

다음 항목을 설명하고 재현할 수 있으면 1장으로 진행합니다.

- IP·서브넷·게이트웨이·DNS와 MAC/ARP의 역할을 구분합니다.
- `ip route get`, `ss`, 제한된 `tcpdump` 캡처를 읽고 관측 위치를 말합니다.
- SSH 키 로그인과 실습 방화벽 정책을 검증하고 원래 상태로 돌립니다.
- HTTP 오류, 연결 실패, 이름 해석 실패를 구분합니다.
- 관리 경로와 실습 경로를 분리하고, 자신의 실습 파일·VM·컨테이너를 식별합니다.

막히는 항목은 [입문 종합 실습](../beginner/08-container-cloud-capstone.md)으로 돌아가 확인합니다. 호스트 도구가 없으면 [게스트 도구 준비](../beginner/README.md#guest-tools)를 먼저 마칩니다.

## 여섯 개의 워크북 {#course-map}

각 행은 **읽기 → 실험 또는 설계 검증 → 증거 기록 → 해설 퀴즈** 순서입니다. 외부 강의는 읽을 범위를 제공하고, 이 워크북은 자신의 결과를 평가하는 방법을 제공합니다.

| 순서 | 워크북 | 남길 결과물 |
|---|---|---|
| 1 | [프로토콜·구현 프로젝트](01-protocol-projects.md) · [퀴즈](../../quizzes/networking/expert/01-protocol-projects-quiz.md) | 요청 경로, probe와 응답의 대응, 프로토콜 경계·예외 사례 |
| 2 | [라우팅 정책과 장애 수렴](02-routing-policy-convergence.md) · [퀴즈](../../quizzes/networking/expert/02-routing-policy-convergence-quiz.md) | 의도한 광고·선택 경로, RIB/FIB와 실제 전달, 장애·복구 타임라인 |
| 3 | [데이터센터 EVPN/VXLAN](03-datacenter-evpn.md) · [퀴즈](../../quizzes/networking/expert/03-datacenter-evpn-quiz.md) | underlay/overlay 대응, VRF별 허용·금지 통신, 경로·캡슐화 증거 |
| 4 | [Linux 패킷 경로와 성능](04-linux-performance.md) · [퀴즈](../../quizzes/networking/expert/04-linux-performance-quiz.md) | 큐·카운터·패킷의 시간대 비교, 측정 조건과 한계, 복구 기록 |
| 5 | [클라우드·CNI 설계](05-cloud-cni-design.md) · [퀴즈](../../quizzes/networking/expert/05-cloud-cni-design-quiz.md) | DNS부터 backend·반환 경로까지의 설계와 관측 근거 |
| 6 | [자동화와 종합 평가](06-automation-capstone.md) · [퀴즈](../../quizzes/networking/expert/06-automation-capstone-quiz.md) | 정상·금지·장애·복구를 검증하는 증거 묶음과 변경 검토서 |

기존 설명서도 연결합니다. [프로토콜 기초](../../basics/06-network-fundamentals-part1.md), [커널 네트워킹](../../kernel/02-network-stack.md), [Calico BGP](../calico/04-bgp-deep-dive.md), [Cilium](../cilium/README.md), [VPC CNI](../01-vpc-cni.md)는 필요한 개념을 찾아볼 심화 자료입니다.

## 목표에 따른 진행 {#tracks}

| 방향 | 우선 진행 | 이후 심화 |
|---|---|---|
| 클라우드 네트워크·SRE | 1 → 2 → 4 → 5 → 6 | CNI·DNS·로드밸런서·하이브리드 경계의 성능과 장애 분석 |
| 기업·데이터센터 네트워크 | 1 → 2 → 3 → 6 | Cisco 공식 학습 범위로 L2/L3·보안·가상화·자동화의 빈 영역 점검 |
| 프로토콜·네트워크 소프트웨어 | 1 → 4 → 6 | C/C++ 기초를 갖춘 뒤 전송 프로토콜·커널 구현 프로젝트 |

3장과 5장은 서로 다른 전문화 방향입니다. 하나를 선택해 종합 평가를 마친 뒤 다른 방향을 추가할 수 있습니다. 주당 시간을 정할 때는 읽기뿐 아니라 환경 준비·실패 원인 분석·재현·보고서 시간을 포함합니다.

## 실습 환경과 소유권 {#lab-contract}

하나의 환경에서 모든 명령을 순서대로 실행하지 않습니다.

| 환경 | 준비와 경계 | 완료 전에 확인할 것 |
|---|---|---|
| 호스트 관측 | 입문 과정의 폐기 가능한 VM, 설치된 도구, 자신의 트래픽 | 인터페이스·프로세스·캡처 대상, 실행 시간, 자신의 파일 정리 |
| 라우팅·EVPN | 별도의 Linux 실습 VM과 선택한 netlab/provider의 설치·이미지 조건 | upstream revision, 도구/이미지 버전, 자신의 lab ID·생성 자원·복구 명령 |
| 클라우드 | 접근이 승인된 기존 실습 계정·클러스터와 읽기 권한 | 계정/리전/context/namespace, 리소스 소유자, 비용·권한·검증 범위 |
| 설계·제공 증거 분석 | 실제 장비가 없어도 명시된 가정·입력 자료로 수행 | 설계 검토와 실제 통신 검증을 구분하고 미관측 항목 표시 |

netlab이나 containerlab이 만든 장치의 주소·이름을 입문 VM의 NIC에 복사하지 않습니다. 상용 NOS 이미지, 가상화 지원, 추가 보드가 필요한 실습도 있으므로 **각 장의 준비 조건과 upstream 안내를 먼저 확인**합니다. 전역 Docker prune, 다른 lab을 포함한 정리, 운영망 장애 주입은 이 과정의 기본 절차가 아닙니다.

모든 실험 전에 아래 기록을 만듭니다. 버전과 리비전을 고정했다는 것은 실제로 확인한 값을 남긴다는 뜻이지, 모든 조합의 호환성을 보장한다는 뜻이 아닙니다.

| 기록 | 예시 형식 |
|---|---|
| 실험 ID·담당자 | 자신이 구분할 수 있는 ID와 역할 |
| 환경·권한 | 로컬 VM / lab container / 승인된 cloud read-only |
| 토폴로지 | 노드·인터페이스·주소·VRF·관측 지점과 관리 경로 |
| 도구·입력 | OS·커널·도구·이미지 버전, upstream commit, 입력 파일 해시 |
| 트래픽 범위 | 출발지·목적지·프로토콜·포트·최대 실행 시간 |
| 사전 상태 | 현재 경로·정책·서비스 상태와 복구용 설정 |
| 가설·변경 | 예상 결과와 이번에 바꿀 단 하나의 항목 |
| 중단·복구 조건 | 관리 경로 이상, 예상 밖 자원, 복구 명령과 재확인 방법 |

## 공식 자료를 선택하는 방법 {#resources}

아래는 2026년 9월 15일 확인한 학습 방향입니다. 학기 페이지·등록·채점기·교육 일정의 접근 범위는 별도로 확인합니다.

| 자료 | 이 과정에서의 역할 | 이용 전 확인 |
|---|---|---|
| [Berkeley CS168](https://www.cs168.io/) | 인터넷 구조·라우팅·전송·데이터센터 원리와 프로젝트의 큰 줄기 | 자료가 채워진 공개 학기를 선택하고 과제 설명·코드·채점기의 접근 범위를 각각 확인 |
| [BGP Labs](https://bgplabs.net/) | BGP 설정·정책·장애 실험의 순차 실습 | [설치 안내](https://bgplabs.net/install/), lab revision과 provider/image 조건 |
| [netlab EVPN](https://netlab.tools/module/evpn/) | EVPN/VRF/IRB 설계와 지원 기능을 검증하는 자료 | 선택 장치가 필요한 기능을 지원하는지와 실제 데이터 플레인 구성 |
| [Bootlin Linux Networking](https://bootlin.com/training/networking/) | 커널·드라이버·사용자 공간과 성능 분석 심화 | 공개 자료와 유료 교육을 구분; C·커널 선수 지식과 보드 기반 실습 조건 |
| [Cisco Enterprise Infrastructure](https://www.cisco.com/site/us/en/learn/training-certifications/certifications/enterprise/ccie-enterprise-infrastructure/index.html) | 기업망 설계·운영·자동화에서 빠진 범위를 점검 | 현재 공식 blueprint를 선택; FRR 실습이 상용 장비·ASIC 동작 전체를 대체하지 않음 |
| [AWS Advanced Networking](https://docs.aws.amazon.com/aws-certification/latest/advanced-networking-specialty-01/advanced-networking-specialty-01.html) | 클라우드·하이브리드 설계·구현·운영·보안의 범위 지도 | 시험 준비와 실환경 구현을 구분; 별도 계정·권한·비용·정리 조건 |
| [Stanford CS144](https://online.stanford.edu/courses/cs144-introduction-computer-networking) | 프로토콜 구현에 관심이 있을 때 참고할 C/C++ 심화 방향 | 수강·공개 과제·현재 저장소 접근 가능 여부를 직접 확인 |

이 저장소는 외부 강의의 비공개 자료나 정답을 제공하지 않습니다. 프로젝트의 요구사항을 읽고 자신의 구현·검증·설계 근거를 작성합니다.

## 증거를 읽는 규칙 {#evidence-rules}

- **실측:** 자신이 명시한 환경·시각·트래픽에서 관측한 값입니다.
- **제공 자료:** 다른 사람이 수집한 자료이며 출처·범위·원본과의 관계를 기록합니다.
- **설명용·합성 자료:** 계산이나 검증 프로그램의 동작을 설명하는 입력입니다. 실제 통신 성공으로 보고하지 않습니다.
- **설계 가정:** 실험하지 않은 설계 조건입니다. 미확인 상태로 남깁니다.

관측이 없으면 `unknown`입니다. 빈 라우팅 출력, 누락된 패킷, `ping` 타임아웃만으로 정책 차단이나 종단 간 장애의 원인이 입증되지는 않습니다. BGP 세션이 수립되어도 의도한 prefix와 실제 전달 경로는 따로 확인합니다.

## 최종 포트폴리오 {#portfolio}

다음 결과물을 자신의 환경에서 연결합니다.

1. 요청 하나의 정방향·반환 경로와 각 관측 지점.
2. 정상 통신과 **금지되어야 하는 통신**의 검증 자료.
3. 한 가지 장애 또는 정책 변경의 전·중·후 기록.
4. 측정 조건, 누락된 증거, 기각한 가설과 그 이유.
5. 좁은 변경 범위와 복구 후 재확인.
6. [종합 평가](06-automation-capstone.md)의 자동 검증 결과와 사람이 판단할 한계.

단계별 원본 자료는 승인된 위치에 보관하고, 공개 노트에는 일관된 별칭을 사용합니다. 패킷·로그·계정·토폴로지 원본을 그대로 공개하지 않습니다.

**다음:** [1장 — 프로토콜·구현 프로젝트](01-protocol-projects.md)
