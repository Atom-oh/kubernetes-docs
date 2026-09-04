# 기반 개념 — link-local과 SNI

> **지원 버전**: Amazon VPC Lattice (GA), AWS Gateway API Controller v1.1+
> **마지막 업데이트**: 2026년 9월 3일

## 이 문서에서 다루는 것

- link-local 주소가 무엇이고, Lattice가 왜 그것을 골랐는가 — 그리고 그 선택에서 파생되는 두 가지 운영 문제
- SNI가 왜 평문으로 전송되어야 하는가 — 인증서 선택의 닭-달걀 문제
- HTTPS listener와 TLS Passthrough에서 Lattice가 각각 볼 수 있는 정보, 그리고 Raw TCP가 지원되지 않는 근본 이유

## link-local 주소

### 무엇인가

link-local 주소는 **하나의 링크(같은 브로드캐스트 도메인) 안에서만 유효한** 주소 대역입니다. 라우터를 넘어가지 않는 것이 정의입니다.

| 대역 | 프로토콜 | 범위 | 근거 |
|---|---|---|---|
| `169.254.0.0/16` | IPv4 | link-local | RFC 3927 |
| `fe80::/10` | IPv6 | link-local | RFC 4291 |

이 대역이 존재하는 이유는 **"DHCP 서버가 없어도, 라우팅 설정이 없어도, 인접한 것과는 통신할 수 있어야 한다"**는 요구입니다. 그래서 이 주소는 전역적으로 유일할 필요가 없고, 각 링크마다 같은 주소가 재사용될 수 있습니다.

### AWS에서 이미 쓰이고 있는 곳

이 구조는 EC2를 써온 사람에게 이미 익숙합니다.

| 주소 | 용도 |
|---|---|
| `169.254.169.254` | **EC2 Instance Metadata Service (IMDS)** — 인스턴스 자신의 메타데이터와 IAM Role credential |
| `169.254.170.2` | ECS 태스크 credential 엔드포인트 |
| `169.254.170.23` | **EKS Pod Identity Agent** (IPv4) |
| `fd00:ec2::23` | EKS Pod Identity Agent (IPv6) |
| `169.254.171.0/24` | **VPC Lattice** (IPv4) |

이들의 공통점은 **주소가 어디로도 라우팅되지 않는다**는 것입니다. `169.254.169.254`로 보낸 패킷은 네트워크를 타고 어딘가로 가는 것이 아니라, **인스턴스가 앉아 있는 하이퍼바이저(또는 노드의 로컬 에이전트)가 가로채서** 응답합니다.

이것이 핵심 아이디어입니다. **link-local 주소는 "이 패킷은 인프라가 처리한다"는 표시**입니다. 클라이언트는 평범한 HTTP 요청을 보내는 것처럼 동작하고, 인프라가 그 주소를 알아보고 개입합니다.

### Lattice의 주소 대역 — IPv4와 IPv6는 성격이 다릅니다

VPC Lattice 서비스의 DNS 이름은 두 종류의 주소로 해석됩니다.

| 대역 | 종류 | 성격 |
|---|---|---|
| `169.254.171.0/24` | IPv4 | **link-local** (`169.254.0.0/16` 안) |
| `fd00:ec2:80::/64` | IPv6 | **Unique Local Address (ULA)** (`fc00::/7` 안, RFC 4193) — link-local이 **아님** |

> **자주 오해되는 지점입니다.** IPv6 쪽 대역은 `fe80::/10`(link-local)이 아니라 **ULA**입니다. 두 대역의 차이는 **범위(scope)**입니다.
>
> - `fe80::/10` link-local은 **링크 범위**입니다. 라우터를 넘을 수 없고, 주소만으로는 어느 인터페이스를 쓸지 결정할 수 없어 zone index(`%eth0`)가 필요합니다.
> - `fd00::/8` ULA는 **사이트 범위**입니다. 전역 인터넷으로는 라우팅되지 않지만 **사설 네트워크 내부에서는 라우팅됩니다.**
>
> Lattice가 IPv6에서 link-local이 아니라 ULA를 고른 이유가 여기 있습니다. Lattice 트래픽은 VPC 안에서 인그레스 엔드포인트까지 **가야** 하므로 링크 범위로는 부족합니다. IPv4 쪽은 `169.254.0.0/16`이 이미 AWS 인프라 서비스의 관례로 자리잡아 그것을 따랐고, IPv6에는 대응하는 관례가 없어 라우팅 가능한 사설 대역인 ULA를 쓴 것으로 이해할 수 있습니다.

이름은 다르지만 실무적으로 중요한 성질은 두 대역이 공유합니다 — **전역적으로 고유하지 않고, 각 VPC 안에서 재사용되며, 인프라가 가로채는 대상**이라는 점입니다.

### 왜 Lattice가 이 방식을 쓰는가

[01번 문서](./01-appmesh-vs-lattice.md)에서 본 대로 Lattice는 **sidecar 없이** 트래픽을 처리해야 합니다. 사이드카가 없다면 누가 트래픽을 가로챌 것인가 — 이 질문에 대한 답이 link-local 주소입니다.

구조는 이렇게 됩니다.

1. 클라이언트가 Lattice 서비스의 DNS 이름을 조회합니다
2. DNS가 `169.254.171.x`(또는 `fd00:ec2:80::` 대역) 주소를 응답합니다
3. 클라이언트가 그 주소로 평범하게 연결합니다 — **애플리케이션은 Lattice의 존재를 모릅니다**
4. 그 대역으로 향하는 패킷은 **VPC 안의 Lattice 인그레스 엔드포인트로 유도**됩니다
5. Lattice가 listener rule을 평가해 Target을 고르고, 실제 Pod IP로 전달합니다

애플리케이션 코드도, Pod 스펙도, iptables 규칙도 건드리지 않고 트래픽이 인프라를 경유합니다. **sidecar를 제거하면서도 트래픽 개입 지점을 확보하는 방법**이 이 주소 대역인 것입니다.

## link-local 선택에서 파생되는 두 가지 문제

이 설계는 우아하지만 대가가 있습니다. 두 문제 모두 전환 계획에 반드시 들어가야 합니다.

### 문제 1 — Envoy iptables 인터셉트와의 충돌

sidecar 메시(App Mesh, Istio)는 Pod의 트래픽을 프록시로 유도하기 위해 **init container가 iptables 규칙을 심습니다.** 전형적으로 "이 Pod에서 나가는 모든 outbound 트래픽을 Envoy의 포트로 리다이렉트"하는 형태입니다.

여기서 충돌이 발생합니다. **Lattice로 향하는 트래픽도 "나가는 트래픽"이므로 Envoy가 가로채 버립니다.** Envoy는 그 목적지를 자신의 설정에서 찾을 수 없으므로 요청이 실패합니다.

해결책은 **예외 CIDR 등록**입니다. Lattice 대역을 인터셉트 대상에서 제외해 그 트래픽이 Envoy를 우회하도록 만듭니다.

| 메시 | 예외 등록 방법 |
|---|---|
| App Mesh | App Mesh CNI/init container 설정의 egress 무시 CIDR 목록에 Lattice 대역 추가 |
| Istio | `traffic.sidecar.istio.io/excludeOutboundIPRanges` 애노테이션에 Lattice 대역 추가 |

이 설정은 **전환 기간 동안 두 모델이 공존할 때 반드시 필요합니다.** App Mesh를 걷어내기 전에 일부 호출만 Lattice로 옮겨보는 단계적 전환에서, 이 예외가 없으면 Lattice 호출이 통째로 실패합니다. IPv6도 쓴다면 `fd00:ec2:80::/64`도 함께 제외해야 합니다.

역방향 활용도 가능합니다. [03번 문서](./03-auth-flow.md)의 egress proxy 패턴은 iptables로 **Lattice 대역만 골라** 서명 프록시로 보냅니다. 같은 도구를 반대 목적으로 쓰는 것입니다.

### 문제 2 — 목적지 IP 기반 관측과 통제가 무의미해진다

link-local 주소는 **전역적으로 고유하지 않고, 서비스를 식별하지도 않습니다.** 이것이 기존 운영 도구들의 전제를 깨뜨립니다.

| 깨지는 것 | 이유 |
|---|---|
| **flow log의 목적지 IP로 통신 상대 식별** | 목적지가 `169.254.171.x`로만 보임. 어느 Lattice 서비스로 갔는지 알 수 없음 |
| **목적지 CIDR 기반 Security Group egress 규칙** | 모든 Lattice 서비스가 같은 대역. 서비스별로 구분해 허용/차단할 수 없음 |
| **목적지 IP 기반 NetworkPolicy** | 위와 동일. Kubernetes NetworkPolicy의 `ipBlock`으로 Lattice 서비스를 구분할 수 없음 |
| **IP 기반 모니터링 대시보드와 알람** | 서비스 단위 집계가 불가능 |
| **IP 대역 기반 자산 인벤토리** | Lattice 서비스가 인벤토리에 IP로 나타나지 않음 |

**대안은 통제 계층을 옮기는 것입니다.**

- **인가는 IP가 아니라 auth policy로** 표현합니다. principal, 경로, 메서드, 헤더 조건을 씁니다 ([03번 문서](./03-auth-flow.md))
- **관측은 flow log가 아니라 Lattice access log로** 합니다. 여기에 어느 서비스로 갔는지가 기록됩니다
- **Security Group은 CIDR이 아니라 managed prefix list로** 엽니다 (아래)

이 전환은 단순한 도구 교체가 아니라 **통제 모델의 이동**입니다. "IP와 포트로 통제한다"에서 "신원과 정책으로 통제한다"로 옮겨가는 것이고, 네트워크 팀의 기존 운영 자산 상당 부분이 이 대역에서는 작동하지 않습니다. 금융권 환경에서는 이것이 조직 간 책임 경계 문제로 번질 수 있어, 전환 초기에 네트워크 팀과 합의해야 합니다.

### Security Group은 prefix list로 열어야 합니다

Lattice에서 대상으로 들어오는 트래픽을 받으려면 노드 Security Group이 그것을 허용해야 합니다. 이때 CIDR을 직접 쓰는 대신 **AWS가 관리하는 prefix list**를 쓰는 것이 정석입니다.

| Prefix list 이름 | 용도 |
|---|---|
| `com.amazonaws.<region>.vpc-lattice` | IPv4 |
| `com.amazonaws.<region>.ipv6.vpc-lattice` | IPv6 |

```bash
# 노드 SG에 Lattice IPv4 prefix list로부터의 인바운드 허용
PREFIX_LIST_ID=$(aws ec2 describe-managed-prefix-lists \
  --query "PrefixLists[?PrefixListName=='com.amazonaws.$AWS_REGION.vpc-lattice'].PrefixListId" \
  --output text)
aws ec2 authorize-security-group-ingress --group-id $CLUSTER_SG \
  --ip-permissions "PrefixListIds=[{PrefixListId=${PREFIX_LIST_ID}}],IpProtocol=-1"
```

prefix list를 쓰는 이유는 **대역이 바뀌어도 SG 규칙을 고치지 않아도 되기 때문**입니다. AWS가 prefix list 내용을 관리합니다. CIDR을 하드코딩하면 대역 변경 시 조용히 깨집니다.

## SNI — Server Name Indication

### 왜 도메인을 평문으로 실어보내야 하는가

SNI는 TLS `ClientHello`에 **접속하려는 서버의 도메인 이름을 평문으로** 담아 보내는 확장입니다. 암호화 프로토콜의 첫 메시지에 목적지 도메인이 평문으로 들어간다는 것이 이상해 보이지만, 여기에는 피할 수 없는 순환 구조가 있습니다.

**닭-달걀 문제:**

1. 서버가 TLS 연결을 시작하려면 **어떤 인증서를 제시할지** 골라야 합니다
2. 인증서는 도메인에 묶여 있습니다 (`api.example.com`의 인증서와 `www.example.com`의 인증서는 다름)
3. 하나의 IP·포트에서 여러 도메인을 서비스한다면, **클라이언트가 어느 도메인을 원하는지 알아야** 인증서를 고를 수 있습니다
4. 그런데 클라이언트가 원하는 도메인은 HTTP `Host` 헤더에 있고, **`Host` 헤더는 TLS 안에 암호화되어 들어옵니다**
5. 즉 **암호화를 시작하려면 도메인을 알아야 하고, 도메인을 알려면 암호화를 시작해야 합니다**

이 순환을 끊는 유일한 방법이 **암호화가 시작되기 전에, 즉 `ClientHello`에 도메인을 평문으로 담아 보내는 것**입니다. 이것이 SNI입니다.

정리하면 **SNI의 평문 노출은 설계 실수가 아니라 순환을 끊기 위한 의도적 타협**입니다. 그리고 이 타협 덕분에 **TLS를 종료하지 않는 중간 장비도 목적지 도메인만은 알 수 있게** 되었습니다 — 이것이 TLS Passthrough 라우팅의 기반입니다.

### Lattice가 SNI로 하는 일

TLS Passthrough listener에서 Lattice는 TLS를 종료하지 않습니다. 그러면 **무엇을 근거로 Target을 고를 것인가?** 답이 SNI입니다. `ClientHello`의 평문 SNI 필드를 읽어 그것만으로 라우팅합니다.

## HTTPS listener vs TLS Passthrough — Lattice가 볼 수 있는 정보

| 정보 | HTTPS listener (TLS Terminate) | TLS Passthrough |
|---|---|---|
| **SNI (도메인)** | ✅ | ✅ |
| **HTTP 경로** | ✅ | ❌ |
| **HTTP 메서드** | ✅ | ❌ |
| **HTTP 헤더** | ✅ | ❌ |
| **쿼리 문자열** | ✅ | ❌ |
| **`Authorization` 헤더 (SigV4)** | ✅ → **IAM Auth 가능** | ❌ → **IAM Auth 불가** |
| **요청 body** | ✅ (경유) | ❌ |
| **경로·헤더 기반 라우팅** | ✅ | ❌ (SNI만) |
| **경로·메서드·헤더 condition key** | ✅ | ❌ |
| **access log의 HTTP 상세** | ✅ | 제한적 |
| **종단간 암호화 유지** | ❌ (Lattice에서 한 번 종료) | ✅ |
| **엔드포인트의 자체 mTLS** | ❌ (Lattice가 client cert를 요구하지 않음) | ✅ (엔드포인트가 직접 수행) |
| **Target Group 프로토콜** | HTTP / HTTPS | **TCP** |
| **Gateway API 리소스** | `HTTPRoute` / `GRPCRoute` (`tls.mode: Terminate`) | `TLSRoute` (`tls.mode: Passthrough`) |

이 표가 이 섹션의 가장 중요한 트레이드오프를 담고 있습니다.

> **종단간 암호화를 유지하려면(TLS Passthrough) L7 라우팅과 IAM Auth를 포기해야 하고, L7 라우팅과 IAM Auth를 쓰려면(HTTPS listener) Lattice에서 TLS가 한 번 종료되는 것을 받아들여야 합니다.**

둘 중 하나를 골라야 하며, **하나의 서비스에서 둘을 동시에 가질 수 없습니다.** 이것이 [06번 문서](./06-constraints.md)의 첫 번째 제약이고, 금융권 환경에서 실제로 가장 먼저 부딪히는 지점입니다.

## Lattice가 지원하는 프로토콜

| Listener protocol | Application protocol | Target Group protocol |
|---|---|---|
| **HTTP** | HTTP/1.1 | HTTP |
| **HTTPS** | HTTP/1.1, HTTP/2, gRPC (**ALPN으로 협상**, ALPN 없으면 HTTP/1.1) | HTTP / HTTPS |
| **TLS_PASSTHROUGH** | (Lattice가 해석하지 않음) | **TCP** |

**독립적인 Raw TCP listener는 없습니다.** TCP는 TLS_PASSTHROUGH의 Target Group 프로토콜로만 존재합니다.

### Raw TCP를 지원하지 않는 근본 이유

이것은 기능 누락이 아니라 **논리적 필연**입니다.

Lattice가 하는 일의 최소 단위는 **"이 연결을 어느 Target으로 보낼지 결정하는 것"**입니다. 그 결정에는 근거가 필요합니다.

- **HTTP/HTTPS**: 경로, 헤더, 메서드 → 근거 풍부
- **TLS Passthrough**: SNI → 근거 하나 있음
- **Raw TCP**: **아무것도 없음**

평문 TCP 연결에는 도메인 정보가 없습니다. TLS가 없으면 `ClientHello`가 없고, `ClientHello`가 없으면 SNI가 없습니다. 목적지 IP도 link-local이라 서비스를 식별하지 않습니다. 남는 것은 포트 번호뿐인데, 포트만으로는 여러 서비스를 다중화할 수 없습니다.

> **정리: TLS가 없으면 SNI가 없고, SNI가 없으면 라우팅의 근거가 없습니다.** 그래서 Lattice는 Raw TCP를 지원하지 않습니다.

이것이 **원리적 제약이므로 향후에도 쉽게 해소되지 않을 성질**입니다. 평문 TCP 프로토콜(일부 DB 프로토콜, 커스텀 바이너리 프로토콜, 평문 Redis 등)을 쓰는 서비스는 Lattice의 대상이 아니며, NLB 등 다른 수단이 필요합니다 ([06번 문서](./06-constraints.md)의 Hybrid 구성).

## 보안 참고 — SNI 평문 노출의 함의

### 무엇이 노출되는가

TLS로 통신 내용은 보호되지만, **어느 도메인에 접속했는지는 경로상의 관찰자에게 보입니다.** 이것은 Lattice의 특성이 아니라 TLS와 SNI의 일반적 성질입니다.

VPC 내부 통신이므로 외부 관찰자를 걱정할 상황은 아니지만, 두 가지를 인지해야 합니다.

- **내부 관찰자에게 서비스 호출 관계가 보입니다.** VPC 내에서 트래픽을 관측할 수 있는 주체는 SNI로 호출 그래프를 재구성할 수 있습니다.
- **flow log의 목적지 IP는 무의미하지만 SNI는 유의미합니다.** 앞에서 본 "목적지 IP 기반 관측이 깨진다"는 문제를 SNI 기반 관측으로 일부 보완할 수 있다는 뜻이기도 합니다.

### ECH — SNI 평문 노출에 대한 해법

**Encrypted Client Hello (ECH)**는 `ClientHello` 자체를 암호화해 SNI 노출을 막는 표준입니다. 서버의 공개키를 DNS로 미리 배포해 그 키로 `ClientHello`의 민감한 부분을 암호화하는 방식으로, 앞의 닭-달걀 문제를 **DNS를 이용해 우회**합니다.

::: warning 확인 필요
VPC Lattice가 ECH를 지원하는지는 공식 문서에서 확인하지 못했습니다. **지원한다고 가정하지 마십시오.** 현재는 SNI가 평문으로 노출되는 것을 전제로 설계하는 것이 안전합니다.
:::

### SNI 기반 통제 장비를 쓰는 환경에 미치는 영향

금융권을 포함해 많은 조직이 **SNI를 보고 트래픽을 통제하는 장비**를 운영합니다 — 허용 도메인 화이트리스트, SNI 기반 로깅, 도메인별 정책 적용 등. 이런 환경에서 Lattice 도입은 두 방향으로 영향을 줍니다.

| 구성 | SNI 통제 장비 관점의 영향 |
|---|---|
| **HTTPS listener** | 클라이언트가 보내는 SNI는 Lattice 서비스의 도메인. 기존 화이트리스트에 **Lattice 도메인(`*.vpc-lattice-svcs.<region>.on.aws` 또는 custom domain)을 추가**해야 함. 그 뒤 Lattice→Target 구간은 장비의 관측 범위 밖 |
| **TLS Passthrough** | SNI가 종단까지 유지되므로 SNI 기반 통제와 궁합이 좋음. 단 IAM Auth를 포기해야 함 |
| **link-local 대역** | 목적지 IP 기반 통제 장비는 무력화됨 (앞의 "문제 2") |

**custom domain을 쓸 경우 여기서 [03번 문서](./03-auth-flow.md)의 Host 헤더 함정과 만납니다.** SNI 통제를 위해 custom domain을 붙였는데 서명 로직이 Lattice 생성 도메인을 쓰고 있으면 403이 납니다. custom domain 도입은 SNI 통제, 서명 대상 Host, 인증서 관리 세 가지를 함께 결정해야 하는 항목입니다.

## 정리

- link-local 주소는 **"이 패킷은 인프라가 처리한다"는 표시**입니다. IMDS·Pod Identity Agent와 같은 계열이며, Lattice가 sidecar 없이 트래픽에 개입하는 수단입니다.
- IPv4는 `169.254.171.0/24`(link-local)이지만 **IPv6는 `fd00:ec2:80::/64`로 link-local이 아닌 ULA**입니다. Lattice 트래픽은 VPC 안에서 라우팅되어야 하므로 링크 범위로는 부족합니다.
- 파생 문제 두 개: **Envoy iptables 인터셉트와 충돌**(예외 CIDR 등록 필요), **목적지 IP 기반 관측·통제가 무의미해짐**(auth policy와 access log로 이동, SG는 prefix list로).
- SNI가 평문인 이유는 **인증서 선택의 닭-달걀 문제**를 끊기 위한 의도적 타협이며, 그 덕분에 TLS Passthrough 라우팅이 가능합니다.
- **TLS를 종료하지 않으면 헤더를 볼 수 없으므로 IAM Auth를 쓸 수 없습니다.** 종단간 암호화와 L7 기능·IAM Auth는 하나를 골라야 하는 트레이드오프입니다.
- **Raw TCP 미지원은 원리적 제약입니다** — TLS가 없으면 SNI가 없고, SNI가 없으면 라우팅 근거가 없습니다.

다음: [워크로드 신원 모델 전환](./05-spiffe-to-iam.md)에서 SPIRE가 하던 일을 IAM이 어디까지 대신할 수 있는지 봅니다.

## 참고 자료

- [Managing DNS resolution with Amazon VPC Lattice and VPC resources](https://aws.amazon.com/blogs/networking-and-content-delivery/managing-dns-resolution-with-amazon-vpc-lattice-and-vpc-resources/)
- [Amazon VPC Lattice DNS migration strategies and best practices](https://aws.amazon.com/blogs/networking-and-content-delivery/amazon-vpc-lattice-dns-migration-strategies-and-best-practices/)
- [AWS Gateway API Controller — Deploy the controller (prefix list 설정)](https://www.gateway-api-controller.eks.aws.dev/latest/guides/deploy/)
- [AWS Gateway API Controller — TLS Passthrough](https://www.gateway-api-controller.eks.aws.dev/latest/guides/tls-passthrough/)
- [Enabling end-to-end encryption with Amazon VPC Lattice TLS passthrough](https://aws.amazon.com/blogs/networking-and-content-delivery/enabling-end-to-end-encryption-with-amazon-vpc-lattice-tls-passthrough/)
- [HTTPS listeners for VPC Lattice services](https://docs.aws.amazon.com/vpc-lattice/latest/ug/https-listeners.html)
- [RFC 3927 — IPv4 Link-Local Addresses](https://datatracker.ietf.org/doc/html/rfc3927) / [RFC 4193 — Unique Local IPv6 Unicast Addresses](https://datatracker.ietf.org/doc/html/rfc4193)
- [RFC 6066 — TLS Extensions: Server Name Indication](https://datatracker.ietf.org/doc/html/rfc6066)
- [네트워크 기초 Part 2: 전송 계층과 TLS](../../basics/06-network-fundamentals-part2.md)
