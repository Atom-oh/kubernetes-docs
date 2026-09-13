# Shared VPC와 Connectivity

> **마지막 업데이트**: 2026년 9월 13일

## 1. Shared VPC의 owner/participant 권한 — 흔히 오해하는 부분

Shared VPC(AWS RAM으로 subnet을 여러 Account에 공유)를 도입할 때 가장 많이 오해하는 부분은 "공유하면 양쪽이 동등하게 볼 수 있다"는 가정입니다. 실제로는 리소스별로 owner와 participant의 권한이 크게 다릅니다.

| 리소스 | Participant 권한 | Owner 권한 |
|---|---|---|
| Subnet | describe만 | 전권 |
| Route table | describe만 | 전권 |
| NACL | describe만 (owner가 만든 것) | 전권 |
| **NAT Gateway** | **describe조차 불가** | 전권 |
| Internet Gateway | describe만 (Egress-only IGW는 describe도 불가) | 전권 |
| TGW attachment | 생성 불가 | owner만 가능 |
| ENI | 자기 것 전권 | 남의 것 describe만 |
| Security Group | 자기 것 전권 + owner 공유분 사용 | 남의 것 describe만 |
| Flow Logs | 자기 ENI만 | subnet + 모든 ENI 가능 (단 participant가 만든 flow log는 owner도 describe·삭제 불가) |

이 표에서 두 가지 실무적 함의가 나옵니다.

**Flow Logs 소유권은 비대칭적입니다.** owner의 subnet/VPC 로그를 중앙 증거로 수집하고 participant ENI 로그의 목적·보존·비용을 함께 관리할 수 있습니다. participant의 개별 로그를 모두 SCP로 금지해야 한다는 AWS 요구사항은 없습니다. Flow Logs는 관측 자료이며 트래픽 차단 수단은 아닙니다.

**VPC·subnet 태그는 participant에게 공유되지 않습니다.** Load Balancer Controller의 버전·discovery 모드·IAM 권한에 따라 탐색 결과를 검증하세요. 명시적 subnet ID annotation은 선택할 수 있는 예측 가능한 방식이며, 모든 버전의 자동 탐색이 반드시 실패한다는 뜻은 아닙니다.

Security Group은 allow rule만 지원하고, 여러 SG의 rule은 합쳐집니다 — 다른 SG의 넓은 Allow를 중앙 SG로 상쇄할 수 없습니다. 기본 SG당 rule은 60개(inbound/outbound × IPv4/IPv6 각각), ENI당 SG는 5개이며 두 quota는 조정 가능하고, **"rule 수 × ENI당 SG 수 ≤ 1,000"** 제약이 있습니다. Firewall Manager의 공통 SG 정책도 이 예산을 소비합니다.

Participant의 ENI·SG quota는 해당 participant Account에 계산됩니다. 기본 ENI 5,000/AZ와 SG 2,500/Region은 각 Account에서 여전히 병목이 될 수 있으며 조정 가능합니다. quota 용량과 SG 권한 통제는 별도로 검토합니다.

<span id="_2-shared-vpc의-실제-상한-—-cidr이-아니다"></span>

## 2. Shared VPC quota는 적용 범위를 나눠 계산한다

병목 순서는 workload에 따라 달라집니다. 기본값과 승인된 값을 구분하고 현재·성장 예상치를 각 범위에 적용합니다.

| 범위 | 기본 quota | 판단 |
|---|---|---|
| VPC route table의 non-propagated route | IPv4/IPv6 각각500, 최대1,000까지 조정 | TGW 방향 static route도 여기서 계산 |
| VPC route table의 propagated route | 100, 조정 불가 | VGW 전파 경로의 제한이며 TGW route-table 총량과 다름 |
| 모든 TGW route table의 static+dynamic route 합계 | TGW당10,000 | 증설은 SA/TAM 문의 |
| Participant Account / VPC | 100, 조정 가능 | 공유 대상 수 |
| 공유받는 subnet / Account | 100, 조정 가능 | AZ·용도 조합 |
| NAU / VPC | 64,000, 최대256,000 | Pod IP·ENI·prefix-list 항목 등 |
| Subnet·route table / VPC | 각각200, 조정 가능 | 구성 수 |
| IPv4 CIDR / VPC | 5, 최대50 | 실제 주소 소모와 단편화 함께 확인 |

**TGW route는 VPC route table로 자동 전파되지 않습니다.** VPC owner가 TGW를 대상으로 static route를 만들고, attachment propagation은 TGW route table에서 관리합니다. 따라서 “TGW prefix가100개를 넘으면 Shared VPC가 멈춘다”는 판정은 잘못입니다. default route가 inspection을 보장하거나 우회하는지도 실제 route association·return path에 따라 확인해야 합니다.

### 최소 Shared VPC Pool vs Workload별 전용 Shared VPC

"모든 워크로드를 하나의 Shared VPC에 몰아넣는 최소 구성"과 "워크로드 그룹별로 전용 Shared VPC를 여러 개 두는 구성"을 비교할 때, 흔히 놓치는 관점이 하나 있습니다.

- **동일 TGW–VPC 쌍에는 VPC attachment1개만 허용됩니다.** 한 VPC는 최대5개의 TGW에 연결할 수 있습니다. attachment의 기본 처리량은 AZ당 각 방향 최대100Gbps/7.5MPPS이며 추가 용량은 SA/TAM과 확인합니다.
- 최소 구성에서는 여러 워크로드의 on-prem·외부 트래픽이 이 attachment 하나로 집약됩니다 — 장애 영향뿐 아니라 **대역폭·PPS 상한까지 공유**하게 됩니다.
- 워크로드 그룹별 전용 Shared VPC 구성은 VPC마다 별도 attachment를 가지므로, 이 처리량 상한을 나눠 갖습니다. **TGW 처리량 상한을 분리할 수 있다는 점이 "여러 개의 전용 Shared VPC"를 선택하는 실질적인 이유**입니다.

결국 최소 구성과 전용 구성의 선택은 "비용 vs 격리"보다 **"중앙 네트워크 파이프라인의 변경 위험 vs VPC 단위 공통 장애 위험"의 교환**으로 이해하는 것이 더 정확합니다. 어느 쪽을 택해도 파이프라인 품질에 의존하므로, "중앙 파이프라인의 잘못된 route 변경을 얼마나 빨리 탐지·복구하는가"를 두 안 모두에서 측정해야 실제 선택 기준이 나옵니다. trust zone별로 다르게 적용(일반 워크로드는 최소 구성, on-prem/외부 연동이 많은 워크로드는 전용 구성)하는 절충안도 고려할 수 있습니다.

### Transit Gateway 주요 quota

| Quota | 기본값 | 조정 |
|---|---|---|
| TGW / Account | 5 | 가능 |
| Attachment / TGW | 5,000 | 가능 |
| **TGW / VPC** | **5** | **불가** |
| TGW route table / TGW | 20 | 가능 |
| 전체 route / TGW | 10,000 | SA/TAM 문의 |
| **동일 TGW–VPC 쌍의 attachment** | **1** | **불가** |

**MTU는 경로 전체에서 확인합니다.** TGW의 VPC·DX·Connect·peering 구간은8,500바이트이며 VPN에는 별도 터널 MTU 제한이 있습니다. VPC peering에서 TGW로 바꿀 때 양쪽 endpoint의 jumbo-frame 설정과 PMTUD를 함께 시험합니다. MSS clamping은 TCP에 관한 동작이며 UDP 등 모든 packet의 MTU 문제를 해결한다고 가정하지 않습니다.

Peered NAU는 기준 VPC와 직접 peering된 같은 Region VPC의 합계에 적용됩니다(기본128,000, 최대512,000). 모든 조직 내 VPC나 전이적으로 연결된 그래프 전체의 합계는 아닙니다.

## 3. AZ ID와 Shared VPC

AZ 이름(`ap-northeast-2a` 등)은 Account마다 실제 물리 AZ에 대한 mapping이 다를 수 있습니다. cross-account로 리소스를 배치할 때는 **AZ 이름이 아니라 AZ ID(`apne2-az*`)로 관리**해야 합니다.

VPC CNI custom networking은 AZ ID로 owner subnet과 participant node의 물리 AZ를 대응시킵니다. ENIConfig 이름은 선택한 node annotation/label과 일치해야 합니다. `ENI_CONFIG_LABEL_DEF=topology.kubernetes.io/zone`이면 이름에는 node의 AZ 이름을 사용하고, 해당 AZ ID에 맞는 subnet ID를 spec에 넣습니다. AZ ID를 이름에 무조건 복사하면 이 lookup과 맞지 않을 수 있습니다. secondary CIDR 자체는 보안 경계가 아닙니다.

## 4. Regional NAT Gateway

| 항목 | 동작 |
|---|---|
| 확장 방식 | 하나의 ID로 자동 확장·축소, public subnet 불필요 |
| Private NAT | 미지원 |
| 확장 지연 | 최대 60분 (그동안 cross-AZ 처리 발생 가능) |
| Zonal → Regional 전환 | connection reset, IP 변경 발생 가능 |
| Constrained AZ | **지원되지 않음** — 사전 확인 필요 |

Regional NAT Gateway는 Zonal보다 IP·연결 한도가 유리합니다 — Regional은 AZ당 IP 32개(Zonal은 8개), IP 1개당 동일 목적지(dest IP+port+protocol)로 동시 연결 55,000개가 늘어납니다. 이건 특정 SaaS·외부 API처럼 **소수 목적지로 대량 연결이 몰리는 패턴**(결제 대행사, 배송 연동사 등)에서 port exhaustion을 방지하는 데 직접적인 효과가 있습니다.

Automatic mode(AWS가 IP/AZ 확장을 관리, 권장)와 Manual mode(직접 관리) 중 하나를 선택할 수 있습니다. **고정 egress IP를 외부 파트너의 allowlist에 등록해야 한다면 Manual mode 또는 IPAM public IPv4 allocation policy 연동이 필요**합니다. Regional NAT Gateway의 라우팅 테이블은 TGW를 유효한 route로 지원하므로, 중앙 TGW inspection과 Regional NAT를 함께 조합할 수 있습니다 — 서로 배타적이지 않습니다.

## 5. TGW + Network Firewall (중앙 inspection)

East-west 트래픽을 중앙에서 검사하는 방식은 두 가지입니다.

- **Inspection VPC 경유**: appliance mode + 양방향 route가 필요합니다.
- **TGW-attached Network Firewall 직접 attachment**: appliance mode가 항상 적용됩니다.

Network Firewall은 **asymmetric routing을 지원하지 않습니다.** TGW owner Account와 firewall owner Account가 다르면 삭제 권한과 가시성에 제약이 생깁니다.

AWS 관점에서 중앙 inspection이 무조건 필수인 조건은 없습니다. **trust zone 내부는 분산 통제, trust zone 간·규제 경로만 중앙 강제**하는 Hybrid 방식이 대부분의 경우 합리적입니다.

## 6. AWS API와 VPC endpoint

서비스·Region·기능별 endpoint와 endpoint-policy 지원을 대조합니다. 기본 full-access endpoint policy도 IAM 권한을 새로 부여하지는 않습니다. describe-vpc-endpoint-services로 inventory를 수집하고 서비스 문서·private DNS·실제 승인/거부 검증을 함께 사용합니다.

## 7. Route 53 Profiles와 Hybrid DNS

Route 53 Profile에는 Private Hosted Zone, Resolver rule(forwarding/system), DNS Firewall rule group, **interface VPC endpoint**, VPC Resolver query logging config를 연결할 수 있습니다. VPC에는 Profile을 1개만 연결할 수 있습니다.

**가장 오해하기 쉬운 부분은 우선순위 규칙입니다.** "local VPC가 항상 우선"이 아니라, **"더 구체적인(specific) 이름이 우선"**입니다.

| DNS query | Profile rule | VPC local rule | 적용되는 rule |
|---|---|---|---|
| `example.com` | `example.com` | `example.com` | Local VPC (동일 이름이면 local 우선) |
| `test.example.com` | `test.example.com` | `example.com` | **Profile (더 구체적인 이름 우선)** |
| `marketing.example.com` | 없음 | `marketing.example.com` | Local VPC |

두 번째 행에서 보듯, **중앙 Profile에 등록된 더 구체적인 이름이 워크로드의 local rule을 덮어씁니다.** 이를 모르고 설계하면 워크로드가 원인 불명의 이름 해석 오류를 겪게 됩니다. **"중앙 Profile은 워크로드가 위임받은 namespace보다 구체적인 이름을 갖지 않는다"를 명문 규칙으로 두는 것을 권장합니다.** 실무적으로는 namespace governance는 중앙에서, 그 하위 subdomain은 워크로드 팀에 위임하는 조합이 잘 맞습니다. Route 53 Profiles는 서울 리전에서 지원됩니다.

## 8. VPC 간 Connectivity 선택지

서로 배타적인 선택지가 아니라, 트래픽 요구에 따라 edge마다 선택하는 조건별 적용 패턴입니다.

| 선택지 | 적합한 상황 | 제약 |
|---|---|---|
| VPC Peering | 소수 VPC 간 직접 양방향 연결 | Peered NAU 128,000(→512,000) 한도, CIDR overlap 불가, non-transitive |
| Transit Gateway | 다수 VPC·on-prem·중앙 inspection | TGW table 총량·VPC static route·동일 TGW–VPC 쌍 attachment 및 처리량을 각각 계산 |
| PrivateLink | 특정 서비스를 단방향으로 노출 | endpoint 비용, provider/consumer 양쪽의 반복 운영 |
| **VPC Lattice** | 애플리케이션 service/resource 연결, 겹치는 CIDR 환경도 검토 가능 | PrivateLink·NAT 등 대안과 protocol·인증·비용 비교 |
| Same-VPC local routing | 같은 trust zone, 동일 VPC에 배치 가능한 경우 | route·DNS·IP 장애를 공유 |

### VPC Lattice 제약

Lattice는 종종 실제보다 가볍게 설명되지만, 확인된 제약은 다음과 같습니다.

| 항목 | 값 | 영향 |
|---|---|---|
| VPC당 service network association | **1개만** | 여러 network가 필요하면 service-network 유형 VPC endpoint 필요 |
| **Lattice service의 최대 연결 수명** | **10분** | 재연결·재시도·중복 처리 검증; resource 연결과 구분 |
| Lattice service idle timeout | 기본 60초 (60~600초) | |
| Lattice resource idle timeout | 350초, 연결 수명 제한 없음 | TCP resource는 제약이 적음 |
| Service당 AZ당 대역폭/RPS | 10 Gbps / 10,000 RPS (증가 가능) | |
| Service당 listener 수 / listener당 rule 수 | 2 / 10 | |
| Service network / Region | 50 | |
| MTU | 8,500바이트 | |

장기 연결을 일괄 제외하지 말고 service와 resource 연결을 구분합니다. service의10분 lifetime과 resource의350초 idle timeout은 다른 제한입니다. WebSocket은 HTTP/HTTPS listener에서 기본 지원되지 않지만 TLS listener 또는 Lattice resource 경로를 검토할 수 있습니다. protocol·재연결·SNI·인증 요구와 실제 부하를 확인한 뒤 선택합니다.

## 9. East-west inspection 선택지

| 선택지 | 구성 |
|---|---|
| 분산 정책 통제 | SG/NACL/route/NetworkPolicy + Flow Logs |
| VPC별 분산 firewall | 각 VPC에 독립적인 firewall |
| TGW 중앙 inspection | Transit Gateway 경로에서 일괄 검사 |
| **Hybrid** | trust zone 내부는 분산, trust zone 간·규제 경로는 중앙 |

Shared VPC의 로그 소유권·열람 경로·보존 기간·중복 비용을 명시합니다. owner와 participant의 로그를 중앙으로 수집하는 설계도 가능하며 개별 로그 생성 금지가 전제는 아닙니다.

## 다음

VPC 경계가 정해졌다면, 그 위에서 데이터와 보안 경계를 어떻게 그을지가 남은 결정입니다 → [Data·Security 경계](./05-data-security-boundaries.md)

## 참고 자료

- [VPC quotas](https://docs.aws.amazon.com/vpc/latest/userguide/amazon-vpc-limits.html)
- [Shared VPC owner/participant 책임](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-share-limitations.html)
- [Shared subnet 지원 서비스](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-sharing-service-behavior.html)
- [Shared subnet AZ ID](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-sharing-share-subnet-working-with.html)
- [Security Group 공유](https://docs.aws.amazon.com/vpc/latest/userguide/security-group-sharing.html)
- [Security Group rules](https://docs.aws.amazon.com/vpc/latest/userguide/security-group-rules.html)
- [Firewall Manager 공통 SG 정책](https://docs.aws.amazon.com/waf/latest/developerguide/security-group-policies-common.html)
- [Firewall Manager SG audit 정책](https://docs.aws.amazon.com/waf/latest/developerguide/security-group-policies-audit.html)
- [Regional NAT Gateway](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateways-regional.html)
- [TGW quotas](https://docs.aws.amazon.com/vpc/latest/tgw/transit-gateway-quotas.html)
- [Transit Gateway 개요](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-transit-gateways.html)
- [TGW-attached Network Firewall](https://docs.aws.amazon.com/network-firewall/latest/developerguide/tgw-firewall.html)
- [Network Firewall asymmetric routing](https://docs.aws.amazon.com/network-firewall/latest/developerguide/asymmetric-routing.html)
- [VPC Lattice quotas](https://docs.aws.amazon.com/vpc-lattice/latest/ug/quotas.html)
- [VPC Lattice 개요](https://docs.aws.amazon.com/vpc-lattice/latest/ug/what-is-vpc-lattice.html)
- [PrivateLink 지원 서비스](https://docs.aws.amazon.com/vpc/latest/privatelink/aws-services-privatelink-support.html)
- [VPC Peering](https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-basics.html)
- [VPC connectivity options whitepaper](https://docs.aws.amazon.com/whitepapers/latest/aws-vpc-connectivity-options/amazon-vpc-to-amazon-vpc-connectivity-options.html)
- [Centralized VPC inspection](https://docs.aws.amazon.com/whitepapers/latest/building-scalable-secure-multi-vpc-network-infrastructure/centralized-network-security-for-vpc-to-vpc-and-on-premises-to-vpc-traffic.html)
- [Route 53 Profiles](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/profiles.html)
- [Route 53 Resolver hybrid DNS](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html)
- [TGW route propagation FAQ](https://aws.amazon.com/transit-gateway/faqs/)
- [ENIConfig label mapping](https://docs.aws.amazon.com/eks/latest/best-practices/custom-networking.html)
- [Lattice listener protocols](https://docs.aws.amazon.com/vpc-lattice/latest/ug/listeners.html)
