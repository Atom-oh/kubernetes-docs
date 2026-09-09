# Shared VPC와 Connectivity

> **마지막 업데이트**: 2026년 9월 9일

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

**Flow Logs 가시성이 양방향으로 비대칭적입니다.** SG·NACL·route·NetworkPolicy·Flow Logs로 VPC 내부 통신을 통제하려면, **owner가 subnet 단위 flow log를 소유하고 participant의 개별 flow log 생성을 SCP로 금지**해야 합니다. 그렇지 않으면 비용이 중복으로 발생하면서도 전체 트래픽 그림은 어느 Account에서도 완전하게 보이지 않습니다.

**VPC·subnet의 태그는 participant에게 공유되지 않습니다.** AWS Load Balancer Controller의 subnet 자동 탐색은 `kubernetes.io/role/elb`, `kubernetes.io/role/internal-elb` 태그에 의존하는데, Shared VPC에서 이 태그는 owner 소유이므로 participant Account에서 보인다고 보장할 수 없습니다. **Shared VPC + EKS 조합에서는 subnet 자동 탐색에 의존하지 말고, Ingress/Service 리소스에 subnet ID를 명시적으로 annotation하는 것을 표준으로** 두는 것이 안전합니다.

Security Group은 allow rule만 지원하고, 여러 SG의 rule은 합쳐집니다 — 다른 SG의 넓은 Allow를 중앙 SG로 상쇄할 수 없습니다. SG당 rule은 60개(inbound/outbound × IPv4/IPv6 각각), ENI당 SG는 5개이며, **"rule 수 × ENI당 SG 수 ≤ 1,000"** 제약이 있습니다. Firewall Manager의 공통 SG 정책도 이 예산을 소비합니다.

Participant가 만든 리소스의 quota(ENI: AZ당 5,000, SG: Region당 2,500)는 **participant Account에 계산**됩니다. 즉 Shared VPC라도 이 두 quota는 병목이 되지 않습니다. "participant가 SG를 통제하는 게 걱정된다"는 우려는 quota 문제가 아니라 권한 문제로 좁혀서 다뤄야 합니다(Firewall Manager audit policy로 위반을 탐지).

## 2. Shared VPC의 실제 상한 — CIDR이 아니다

Shared VPC를 설계할 때 "IPv4 CIDR을 몇 개까지 붙일 수 있는가"에 집중하기 쉽지만, 실제로는 **다른 quota가 훨씬 먼저 막힙니다.** 대표적인 대규모 hub-and-spoke 구성(중앙 Transit Gateway + Shared VPC)에서 도달하는 순서는 다음과 같습니다.

| 순위 | Quota | 기본값 | 조정 | 왜 먼저 막히는가 |
|---|---|---|---|---|
| **1** | **VPC 라우팅 테이블당 전파(propagated) route** | **100** | **불가** | 중앙 TGW hub에서 route propagation을 켜면 VPC + on-prem prefix 합계가 100을 넘는 순간 정지. **유일한 조정 불가 항목이자 실제 첫 병목** |
| 2 | VPC당 participant Account 수 | 100 | 가능 | 팀×환경 조합이면 조기 도달 |
| 3 | Account당 공유받을 수 있는 subnet 수 | 100 | 가능 | AZ×trust zone×용도별로 증가 |
| 4 | VPC당 NAU(Network Address Usage) | 64,000 | 256,000까지 | EKS Pod는 ENI가 아니지만 IP는 NAU로 계산됨. Pod 밀도가 높으면 도달 |
| 5 | VPC당 subnet·route table 수 | 각 200 | 가능 | |
| 6 | VPC당 IPv4 CIDR 수 | 5 | 50까지 | 실제로는 **가장 늦게** 도달 |

즉 CIDR 부족보다 훨씬 먼저, **전파 route 100개**에서 막힙니다. 회피 수단으로 default route(`0.0.0.0/0`) 광고나 static route를 쓸 수 있지만, 그러면 route 기반 세분화 통제(중앙 inspection 강제 경로)와 충돌합니다. **Shared VPC를 도입하는 POC의 첫 측정 항목은 "현재 및 3년 후 예상 전파 prefix 수"로 잡아야 합니다.**

### 최소 Shared VPC Pool vs Workload별 전용 Shared VPC

"모든 워크로드를 하나의 Shared VPC에 몰아넣는 최소 구성"과 "워크로드 그룹별로 전용 Shared VPC를 여러 개 두는 구성"을 비교할 때, 흔히 놓치는 관점이 하나 있습니다.

- **동일 VPC에 TGW attachment는 1개만 허용됩니다(조정 불가).** attachment 하나는 AZ당 최대 100 Gbps(양방향 각각)/7,500,000 PPS의 처리량 상한을 가집니다.
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
| **동일 VPC에 대한 VPC attachment 수** | **1** | **불가** |

**MTU 불일치도 확인이 필요합니다.** TGW의 MTU는 8,500바이트지만 VPN 경로는 1,500바이트입니다. on-prem VPN 연결을 VPC Peering에서 TGW로 옮기는 구간에서 이 불일치 때문에 비대칭적인 패킷 드롭이 발생할 수 있습니다 — 양쪽 VPC를 동시에 변경해야 하며, TGW는 모든 패킷에 MSS clamping을 적용합니다.

VPC Peering을 쓰는 경우 Peered NAU 한도는 128,000(최대 512,000)이며, 이는 **동일 Region 내 모든 peered VPC의 합계**에 적용됩니다(Cross-Region peering은 포함되지 않습니다).

## 3. AZ ID와 Shared VPC

AZ 이름(`ap-northeast-2a` 등)은 Account마다 실제 물리 AZ에 대한 mapping이 다를 수 있습니다. cross-account로 리소스를 배치할 때는 **AZ 이름이 아니라 AZ ID(`apne2-az*`)로 관리**해야 합니다.

VPC CNI의 custom networking을 쓰면 이건 원칙이 아니라 **동작 요구사항**이 됩니다 — `ENIConfig`를 중앙 네트워크 Account가 게시한 AZ ID mapping 기준으로 만들어야 하기 때문입니다. 개인정보 경계를 분리하려고 secondary CIDR을 쓰는 경우 custom networking을 함께 쓰게 될 가능성이 높으므로, 이 관계를 미리 확인해두는 것이 좋습니다.

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

서비스·Region·기능별로 endpoint(Gateway/Interface) 지원 여부와 endpoint policy 지원 여부가 다릅니다. Endpoint policy를 지정하지 않으면 기본적으로 full-access policy가 적용됩니다. 이 coverage matrix는 사람이 주기적으로 조사하는 대신 `aws ec2 describe-vpc-endpoint-services`를 정기적으로 자동 대조하는 방식으로 유지하는 것을 권장합니다.

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
| Transit Gateway | 다수 VPC·on-prem·중앙 inspection | 전파 route 100(불가), VPC당 attachment 1개(불가), AZ당 100 Gbps/7.5M PPS |
| PrivateLink | 특정 서비스를 단방향으로 노출 | endpoint 비용, provider/consumer 양쪽의 반복 운영 |
| **VPC Lattice** | 애플리케이션 단위 service network·인증, **CIDR이 겹치는 VPC 간 연결**(대체 수단 없음) | 아래 표 참고 |
| Same-VPC local routing | 같은 trust zone, 동일 VPC에 배치 가능한 경우 | route·DNS·IP 장애를 공유 |

### VPC Lattice 제약

Lattice는 종종 실제보다 가볍게 설명되지만, 확인된 제약은 다음과 같습니다.

| 항목 | 값 | 영향 |
|---|---|---|
| VPC당 service network association | **1개만** | 여러 network가 필요하면 service-network 유형 VPC endpoint 필요 |
| **Lattice service의 최대 연결 수명** | **10분** | **장기 연결(gRPC streaming, WebSocket, 긴 배치 호출)이 10분마다 강제로 끊김** — 애플리케이션이 재연결을 처리해야 함 |
| Lattice service idle timeout | 기본 60초 (60~600초) | |
| Lattice resource idle timeout | 350초, 연결 수명 제한 없음 | TCP resource는 제약이 적음 |
| Service당 AZ당 대역폭/RPS | 10 Gbps / 10,000 RPS (증가 가능) | |
| Service당 listener 수 / listener당 rule 수 | 2 / 10 | |
| Service network / Region | 50 | |
| MTU | 8,500바이트 | |

**장기 연결을 쓰는 구간은 Lattice 대상에서 제외해야 합니다.** 반대로 CIDR이 겹치는 레거시·인수 환경 연결에는 Lattice가 Private NAT나 CNI custom networking보다 나은 선택일 수 있습니다(link-local 주소 공간에서 동작하기 때문입니다).

## 9. East-west inspection 선택지

| 선택지 | 구성 |
|---|---|
| 분산 정책 통제 | SG/NACL/route/NetworkPolicy + Flow Logs |
| VPC별 분산 firewall | 각 VPC에 독립적인 firewall |
| TGW 중앙 inspection | Transit Gateway 경로에서 일괄 검사 |
| **Hybrid** | trust zone 내부는 분산, trust zone 간·규제 경로는 중앙 |

Shared VPC를 쓴다면, 분산 정책 통제 방식에도 앞서 언급한 "owner가 subnet flow log 소유 + participant 개별 flow log 생성 SCP 금지" 규칙이 함께 필요합니다.

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
