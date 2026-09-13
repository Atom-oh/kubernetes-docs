# Cross-Org VPC 연결

> **원 보고서 표기일**: 2026년 9월 1일
>
> **마지막 업데이트**: 2026년 9월 12일

기존 환경과 별도로 관리하는 GPU 환경처럼 **서로 다른 AWS Organizations의 계정**을 연결하는 다섯 패턴을 비교합니다. 표의 측정값은 이전 문서가 보고한 값을 유지합니다. 이번 검토는 AWS 동작과 산술을 확인했으며 새 실배포나 벤치마크 재현을 수행했다고 주장하지 않습니다.

## 목차

1. [왜 Cross-Org 연결이 필요한가](#왜-cross-org-연결이-필요한가)
2. [5가지 연결 옵션 비교](#5가지-연결-옵션-비교)
3. [보고된 검증 결과](#보고된-검증-결과)
4. [Latency 실측 (M1~M7)](#latency-실측-m1m7)
5. [운영 시 확인할 사항](#운영-시-확인할-사항)
6. [요구사항별 아키텍처 선택](#요구사항별-아키텍처-선택)
7. [한계와 후속 검증](#한계와-후속-검증)

## 왜 Cross-Org 연결이 필요한가

계약상 소유권, 인수합병, 독립적인 거버넌스나 격리 요구로 GPU 워크로드와 기존 서비스가 서로 다른 Organization에 있을 수 있습니다. 조직 구조는 이 요구를 따라 결정해야 하며, Organization을 하나 더 만들면 GPU 할인·쿼터·규제 준수가 자동으로 개선된다고 가정하면 안 됩니다.

EC2 리소스 쿼터는 일반적으로 **계정과 리전** 기준이므로 다른 Organization 없이도 계정을 분리해 해당 범위를 나눌 수 있습니다. 결제 통합, 협상된 할인과 거버넌스 중복 비용도 검토하세요. Organization 경계가 애플리케이션 인가, 네트워크 분리나 감사 제어를 대체하지는 않습니다.

EKS에서는 데이터 파이프라인/추론 API의 일반 IP 접근과 GPU 집단 통신을 구분해야 합니다. CPU 인스턴스의 요청/응답 벤치마크는 NCCL, 처리량이나 RDMA 성능을 증명하지 않습니다. **EFA OS-bypass 트래픽은 VPC나 가용 영역을 넘을 수 없으며**, ENA 인터페이스의 일반 IP 트래픽은 라우팅할 수 있습니다.

<span id="5가지-연결-옵션-비교"></span>

## 5가지 연결 옵션 비교

PrivateLink와 Lattice 열은 **시험한 NLB 기반 엔드포인트 서비스와 HTTP 서비스 패턴**을 설명합니다. PrivateLink에는 리소스·서비스 네트워크 엔드포인트도 있고 Lattice에는 TCP 리소스 구성도 있습니다. 제품 전체가 각각 “NLB 필수”, “L7 전용”인 것은 아닙니다.

| 항목 | ① TGW RAM 공유 | ② VPC Peering | ③ PrivateLink 엔드포인트 서비스 | ④ TGW Peering | ⑤ VPC Lattice HTTP 서비스 |
|---|---|---|---|---|---|
| 연결 방식 | 외부 계정에 TGW 공유 | VPC 쌍 직접 연결 | 소비자 인터페이스 엔드포인트 → 공급자 NLB/서비스 | 각 소유자의 TGW 연결 | 서비스와 클라이언트 VPC를 서비스 네트워크에 연결 |
| 주소 중복 | 직접 라우팅에는 모호하지 않은 주소 계획 필요 | CIDR가 겹치는 VPC는 피어링 불가 | 중복 VPC CIDR 간 서비스 접근 가능 | 직접 라우팅에는 모호하지 않은 주소 계획 필요 | 중복 VPC CIDR 간 서비스 접근 가능 |
| 연결 모델 | 허용된 양방향 IP 라우팅 | 허용된 양방향 IP 라우팅 | 소비자가 연결 시작, 같은 연결로 응답 가능 | 허용된 양방향 IP 라우팅 | 클라이언트가 공개한 서비스에 요청, 역방향 접근은 별도 구성 |
| 라우팅 구성 | VPC 라우트와 TGW 테이블/연결 | 양측 라우트, VPC 전이 피어링 없음 | 일반 VPC 전이 대신 엔드포인트/서비스 권한과 네트워크 제어 | 피어 정적 라우트와 VPC 라우트 명시 | 일반 VPC 전이 대신 서비스/네트워크 연결과 정책 |
| 통제 주체 | 소유자가 TGW 테이블 관리, 소비자는 자신의 VPC 제어 유지 | 각 VPC 소유자 | 공급자는 서비스 권한/대상, 소비자는 자신의 엔드포인트 제어 | 라우트를 조율하는 각 TGW 소유자 | 네트워크/서비스 소유자와 클라이언트 네트워크 제어 |
| 원 보고서 구성 소요 | TGW 약 3분과 수락 절차 | 1분 미만 | 엔드포인트 약 3분 | 약 7분 | 약 5분 |

구성 시간은 원 보고서의 관측값이며 SLA나 전체 구축 기간 추정치가 아닙니다. 라우팅 행은 이 장의 두 TGW 구성을 설명하며 임의의 여러 피어 연결을 무제한 전이할 수 있다고 주장하지 않습니다. NAT나 주소 재설계도 중복 주소의 대안이며 별도 설계가 필요합니다.

## 보고된 검증 결과

원 보고서는 서로 다른 두 Organization에서 다섯 패턴을 구축하고 트래픽을 교환했다고 기술합니다. AWS 문서도 이 패턴의 계정 간 구성을 지원하며 같은 Organization이 필수인 것은 아닙니다. 다만 IAM/SCP/공유 제한은 구성을 차단할 수 있고 실제 통신에는 라우트, 보안 그룹, NACL, DNS와 서비스 인가가 적용됩니다. 계정 ID와 수락만으로 충분하지 않습니다.

![원 조직 간 토폴로지에서 Peering·TGW·PrivateLink는 TCP_RR p50, Lattice HTTP 서비스는 HTTP keep-alive p50을 표시합니다.](../.gitbook/assets/ko-networking-05-cross-org-vpc-connectivity-0.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-networking-05-cross-org-vpc-connectivity-0.html)

그림은 원 관측값을 유지합니다. Lattice 값은 **HTTP KA**, 나머지 표시 값은 **TCP_RR**이므로 동일 지표의 직접 비교가 아닙니다. “GPU”는 제안된 환경을 나타내며 GPU 벤치마크를 뜻하지 않습니다.

<span id="latency-실측-m1m7"></span>

## Latency 실측 (M1~M7)

**보고된 구성:** `ap-northeast-2`, 계정 간 같은 ZoneId `apne2-az1`, `c7g.large`, nginx로 고정 HTTP 200을 반환하는 EC2 응답자 한 대입니다. 보고서는 경로별 서브넷/리턴 라우트의 ENI 세 개, 라운드로빈 인터리브 다섯 라운드, 경로당 persistent TCP_RR 1,500개·ICMP 100개·HTTP keep-alive 275개 표본을 설명합니다.

nginx 설명은 HTTP 응답자를 가리키며 이 페이지에는 TCP_RR 구현이나 메시지 크기가 명시되어 있지 않습니다. 원시 표본, 소프트웨어/커널 버전, 타이머 경계와 Linux 반환 경로 정책 설정도 연결되어 있지 않습니다. 지속 연결은 반복 설정 비용을 줄이려는 설계지만 표만으로 타이머 경계를 독립 검증할 수는 없습니다.

**아래 지연 값은 모두 밀리초이며 TTL은 별도 패킷 필드입니다.** TCP_RR과 ICMP는 요청/응답 왕복 측정이고 HTTP KA에는 애플리케이션 처리가 포함됩니다. 두 측정 회차는 별도로 해석해야 합니다.

| ID | 경로 | ICMP p50 | TCP_RR p50 | RR p99 | RR sd | HTTP KA p50 | TTL |
|---|---|---|---|---|---|---|---|
| M1 | 동일 VPC → EC2 (기준선) | 0.121 | **0.049** | 0.062 | 0.007 | 0.087 | 127 |
| M2 | ② VPC Peering → EC2 | 0.125 | **0.048** | 0.057 | 0.011 | 0.080 | 127 |
| M3 | ① 공유 TGW(RAM) → EC2 | 0.535 | **0.619** | 0.695 | 0.141 | 0.686 | 126 |
| M4 | ④ TGW Peering(두 TGW) → EC2 | 0.912 | **0.599** | 0.855 | 0.133 | 0.488 | 125 |
| M5 | ③ PrivateLink → NLB → EC2 | 미측정 | **0.961** | 1.084 | 0.035 | 0.711 | — |
| M6 | ⑤ VPC Lattice → EC2 타깃 | 미측정 | 해당 HTTP 서비스에서는 미측정 | — | — | **1.635** | — |
| M7 | ② Peering → NLB → EC2 (NLB 홉 분리) | 미측정 | **0.841** | 0.909 | 0.119 | 0.883 | — |

### 보고된 중앙값 간 차이

이는 **경로 중앙값의 차이**이며 독립적인 편도 홉 비용이나 ENI/프록시 구성 요소 자체의 측정값이 아닙니다.

| 관측 경로 비교 | 차이 | Δ TCP_RR p50 | Δ ICMP p50 | Δ HTTP KA p50 |
|---|---|---|---|---|
| Peering과 동일 VPC 기준선 | M2 − M1 | -0.001 | +0.004 | -0.007 |
| 공유 TGW 경로와 Peering | M3 − M2 | +0.571 | +0.410 | +0.606 |
| 두 TGW 경로와 Peering | M4 − M2 | +0.551 | +0.787 | +0.408 |
| NLB를 둔 Peering과 직접 Peering | M7 − M2 | +0.793 | — | +0.803 |
| PrivateLink/NLB와 Peering/NLB | M5 − M7 | +0.120 | — | -0.172 |
| Lattice HTTP 서비스와 직접 Peering HTTP | M6 − M2 | — | — | +1.555 |

- M2는 동일 VPC 기준선에 가깝지만 표만으로 통계적 동등성이나 오버헤드 0을 증명할 수 없습니다.
- 두 TGW 경로의 TCP_RR 중앙값은 공유 TGW 하나인 경로보다 낮습니다. 따라서 보편적인 “TGW 홉당 0.4~0.6ms”나 선형 홉 비용 공식은 이 자료로 뒷받침되지 않습니다.
- M5−M7은 **TCP_RR +0.120ms, HTTP KA −0.172ms**입니다. 이를 순수 PrivateLink ENI 비용이라고 부를 수 없습니다.
- Lattice 비교는 TCP_RR가 아니라 **HTTP +1.555ms**이며 이 HTTP 서비스 시험을 설명할 뿐 모든 Lattice 모드의 비용이 아닙니다.
- 초기 TTL과 관련 네트워크 동작을 모르면 TTL만으로 경로 홉 수를 알 수 없습니다.

### 별도 서비스 프런트 측정

원 보고서는 각 L3 경로에 NLB를 둔 측정도 제시합니다. 해당 서비스 노출 패턴에는 유용하지만 모든 운영 Peering/TGW 배포에 NLB가 필요한 것은 아닙니다.

| 구성 | TCP_RR p50 | HTTP KA p50 |
|---|---|---|
| ② Peering → NLB → EC2 | **0.622** | 0.648 |
| ③ PrivateLink → NLB → EC2 | **0.658** | 0.845 |
| ① 공유 TGW → NLB → EC2 | **1.273** | 1.257 |
| ④ TGW Peering → NLB → EC2 | **1.425** | 1.279 |
| ⑤ Lattice HTTP 서비스 (이 시험에서는 별도 NLB 없음) | — | **1.680** |

이 회차의 PrivateLink/NLB − Peering/NLB 차이는 **TCP_RR +0.036ms, HTTP KA +0.197ms**입니다. 공유 TGW와 peering TGW의 TCP_RR 중앙값은 PrivateLink의 각각 **1.93배, 2.17배**이고 HTTP 비율은 **1.49배, 1.51배**입니다. 이는 지연 비율이지 처리량 배수나 경로 동등성 증명이 아닙니다.

Lattice HTTP 중앙값은 공유 TGW/NLB와 peering TGW/NLB보다 각각 **+0.423ms, +0.401ms** 높습니다. 같은 Peering/NLB 중앙값도 회차별로 다르므로 이 회차와 M1~M7을 섞어 구성 요소 비용을 산출하지 마세요.

원 보고서는 버스터블 인스턴스·NLB→ALB·매번 새 curl 연결을 사용한 폐기한 파일럿의 p95 약 **7ms**, 최초 흐름 증가분 **0.6~1.6ms**도 언급합니다. 연결된 원시 표본이 없는 보고서 관측값이며 AWS 보장이 아닙니다. 실제 애플리케이션의 연결 수립과 정상 상태 동작을 구분해 측정하세요.

## 운영 시 확인할 사항

1. **RAM 외부 공유:** 외부 principal이 허용되어야 하고 Organization 외부 계정은 공유 초대를 수락해야 합니다. `CreateResourceShare` API의 `allowExternalPrincipals` 기본값은 **true**입니다. `--allow-external-principals` 명시는 의도를 나타내지만 해당 CLI 플래그 생략이 항상 실패 원인은 아닙니다. 실제 공유 구성과 권한을 확인하세요.
2. **공유 TGW VPC attachment 수락:** 기본값처럼 `AutoAcceptSharedAttachments`가 비활성화되면 TGW 소유자가 공유 attachment를 수락해야 합니다. 활성화하면 흐름이 달라집니다. RAM 공유 수락과 TGW attachment 수락은 별도 단계입니다. 소비자는 소유자의 TGW 라우트 테이블을 바꿀 수 없지만 자신의 VPC 라우트와 보안 설정은 통제합니다.
3. **TGW peering 수락:** 같은 계정의 peering도 수락자 TGW 소유자가 **수락자 리전**에서 pending 요청을 수락합니다. 해당 요청의 `TransitGatewayAttachmentId`를 사용하고 TGW ID나 VPC attachment ID와 혼동하지 마세요. `NotFound` 응답만으로 양측이 다른 ID를 요구한다는 규칙을 만들 수는 없습니다. 원 보고서의 약 2분 가시성 지연은 관측값이며 고정 대기 시간 보장이 아닙니다.
4. **Peering 라우트:** 직접 TGW-to-TGW peering에는 BGP 전파 대신 정적 라우트를 명시적으로 구성합니다. 양방향의 해당 TGW 및 VPC 라우트 테이블을 구성해야 하며 정적 라우트도 자동화로 관리할 수 있습니다.
5. **라우트 우선순위:** 가장 긴 접두사 매칭이 먼저입니다. **같은 목적지 접두사**에서는 정적 라우트가 전파 라우트보다 우선하지만 더 넓은 정적 라우트가 더 구체적인 전파 라우트를 덮어쓰지는 않습니다.
6. **Lattice 대상 보안 그룹:** 문서화된 VPC 연결 서비스 경로는 리전/IP 계열에 맞는 관리형 접두사 목록(`com.amazonaws.REGION.vpc-lattice`, `com.amazonaws.REGION.ipv6.vpc-lattice`)을 실제 대상·상태 검사 포트에 허용합니다. 원 `169.254.171.0/24` 예제는 전체 목록의 보편적 정의가 아니며 관리형 목록에는 link-local 또는 라우팅할 수 없는 public 주소도 포함될 수 있습니다. 엔드포인트/리소스 게이트웨이 경로에는 별도 제어가 있습니다. VPC 연결만으로 IAM 서비스 인증이 활성화되는 것도 아닙니다.
7. **정리 소유권:** 원 보고서는 GuardDuty 관리 네트워킹 의존성, IAM 정책 연결과 남은 Lattice 리소스가 정리에 영향을 준 사례를 기록합니다. 실제 의존 리소스 ID와 소유 서비스를 확인한 뒤 조치하세요. VPC/역할 삭제를 강제하기 위해 관리형 보안 제어를 끄거나 무관한 리소스를 삭제하지 마세요.

## 요구사항별 아키텍처 선택

| 요구사항 | 후보 패턴 | 중요한 확인 사항 |
|---|---|---|
| 각 Organization이 자신의 TGW 라우팅 권한 유지 | ④ TGW Peering | 정적 라우트 조율, 주소 계획, 처리량, 가용성, 검사와 전송 요금 |
| 소수 추론/서비스 엔드포인트 노출 | ③ PrivateLink 엔드포인트 서비스 | 지원 프로토콜/모델, 엔드포인트 수락, 애플리케이션 인증, DNS, 비용과 실제 페이로드/동시성 |
| 중복 CIDR 간 서비스 접근 | ③ PrivateLink 또는 ⑤ Lattice | 서비스/리소스 범위, 더 넓은 IP 라우팅에는 NAT/주소 재설계 평가 |
| 다른 계정이 중앙 통제 허브 사용 가능 | ① TGW RAM 공유 | 외부 공유 정책, 수락 설정과 소유자의 TGW 제어 모델 |
| 적은 수의 직접 VPC 쌍 | ② VPC Peering | 비중복 CIDR, 쌍별 라우트 관리, 쿼터와 데이터 전송 요금 |
| 관리형 HTTP 서비스 신원/탐색/거버넌스 필요 | ⑤ VPC Lattice | 명시적 IAM 인증 정책, 서명 요청, 서비스 연결과 워크로드 측정 |

TGW peering과 PrivateLink 조합은 독립적인 네트워크 거버넌스와 제한적인 API 노출에 맞을 수 있습니다. 공개된 지연 표가 대부분의 GPU 환경에서 최적임을 증명하지는 않습니다. 필요한 연결과 제어를 기준으로 선택한 뒤 실제 워크로드를 측정하세요.

## 한계와 후속 검증

원 보고서에는 Network Firewall 검사 경로, 리전 간 지연, 처리량/동시성 측정이 없습니다. 주소 중복의 기능 확인을 보고했지만 중복 환경의 지연 값은 공개하지 않았습니다. GPU 집단 통신, EFA/RDMA, 대표 페이로드 크기, 불확실성 추정과 완전한 재현 자료도 이 페이지로 입증되지 않습니다.

보고된 숫자는 과거 결과의 맥락으로 유지하세요. 배포 전 대상 계정의 정책과 지원 연결 모델, 필요한 양방향 라우트 또는 서비스 접근, 장애 동작과 애플리케이션의 지연/처리량 예산을 검증해야 합니다. 이번 검토는 AWS 프로비저닝이나 실시간 벤치마크를 실행하지 않았습니다.

## 참고 자료

- [다중 VPC 네트워킹 백서](https://docs.aws.amazon.com/whitepapers/latest/building-scalable-secure-multi-vpc-network-infrastructure/welcome.html)
- [계정 간 TGW 공유](https://docs.aws.amazon.com/prescriptive-guidance/latest/integrate-third-party-services/architecture-3-1.html)
- [단일/복수 Organizations 선택](https://aws.amazon.com/blogs/architecture/choosing-between-single-or-multiple-organizations-in-aws-organizations/)
- [RAM CreateResourceShare API](https://docs.aws.amazon.com/ram/latest/APIReference/API_CreateResourceShare.html)
- [TGW 수락 옵션](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_TransitGatewayRequestOptions.html)
- [TGW peering 수락](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-peering-accept-reject.html)
- [TGW 라우팅과 평가 순서](https://docs.aws.amazon.com/vpc/latest/tgw/how-transit-gateways-work.html)
- [PrivateLink 엔드포인트 유형](https://docs.aws.amazon.com/vpc/latest/privatelink/what-is-privatelink.html)
- [Private NAT와 중복 네트워크](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-scenarios.html)
- [Lattice 보안 그룹](https://docs.aws.amazon.com/vpc-lattice/latest/ug/security-groups.html)
- [EC2 계정/리전 쿼터](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-resource-limits.html)
- [EFA 제한](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa.html)
- [VPC Lattice 문서](02-vpc-lattice.md)
- [Cross-Org 퀴즈](../quizzes/networking/05-cross-org-vpc-connectivity-quiz.md)
