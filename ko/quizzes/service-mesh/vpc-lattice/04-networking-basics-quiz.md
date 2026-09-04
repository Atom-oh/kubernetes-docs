# 기반 개념 — link-local과 SNI 퀴즈

이 퀴즈는 link-local/ULA 주소, SNI의 원리, 프로토콜 지원 범위에 대한 이해도를 테스트합니다.

## 객관식 문제

1. VPC Lattice 서비스 DNS가 해석되는 주소 대역에 대한 설명으로 올바른 것은?
   - A) IPv4 `169.254.171.0/24`와 IPv6 `fe80::/10` 모두 link-local이다
   - B) IPv4 `169.254.171.0/24`는 link-local이고, IPv6 `fd00:ec2:80::/64`는 link-local이 아니라 Unique Local Address(ULA)다
   - C) 두 대역 모두 전역적으로 고유한 공인 주소다
   - D) IPv6는 지원되지 않는다

<details>

<summary>정답 보기</summary>

**정답: B) IPv4 `169.254.171.0/24`는 link-local이고, IPv6 `fd00:ec2:80::/64`는 link-local이 아니라 Unique Local Address(ULA)다**

**설명:**
IPv4 쪽은 `169.254.0.0/16`(RFC 3927, link-local) 안의 대역이지만, IPv6 쪽은 `fe80::/10`(link-local)이 아니라 `fc00::/7` ULA 대역(RFC 4193) 안의 `fd00:ec2:80::/64`입니다. 차이는 범위(scope)입니다 — link-local은 링크 범위라 라우터를 넘을 수 없고, ULA는 사이트 범위라 사설 네트워크 내부에서 라우팅됩니다. Lattice 트래픽은 VPC 안에서 인그레스 엔드포인트까지 가야 하므로 링크 범위로는 부족합니다.
</details>

2. Lattice가 link-local 주소 대역을 사용하는 근본적인 이유는?
   - A) IP 주소를 절약하기 위해
   - B) sidecar 없이 인프라가 트래픽을 가로채는 지점을 확보하기 위해 — 이 대역은 "이 패킷은 인프라가 처리한다"는 표시다
   - C) IPv4 주소 고갈에 대응하기 위해
   - D) 클라이언트가 목적지를 명시적으로 인식하게 하기 위해

<details>

<summary>정답 보기</summary>

**정답: B) sidecar 없이 인프라가 트래픽을 가로채는 지점을 확보하기 위해 — 이 대역은 "이 패킷은 인프라가 처리한다"는 표시다**

**설명:**
사이드카가 없다면 누가 트래픽을 가로챌 것인가에 대한 답이 link-local 주소입니다. EC2 IMDS(`169.254.169.254`)나 EKS Pod Identity Agent(`169.254.170.23`)와 같은 계열이며, 공통점은 주소가 어디로도 라우팅되지 않고 인프라가 가로채서 처리한다는 것입니다. 클라이언트는 평범한 HTTP 요청을 보내고 애플리케이션은 Lattice의 존재를 모릅니다 — 코드, Pod 스펙, iptables를 건드리지 않고 트래픽이 인프라를 경유합니다.
</details>

3. App Mesh와 Lattice를 병행 운영할 때 Lattice 호출이 통째로 실패하는 흔한 원인은?
   - A) Lattice의 quotas 초과
   - B) App Mesh init container가 심은 iptables 규칙이 Lattice 향 트래픽까지 Envoy로 가로채는데, 예외 CIDR이 등록되지 않은 경우
   - C) Gateway API CRD 버전 불일치
   - D) Target Group 프로토콜 설정 오류

<details>

<summary>정답 보기</summary>

**정답: B) App Mesh init container가 심은 iptables 규칙이 Lattice 향 트래픽까지 Envoy로 가로채는데, 예외 CIDR이 등록되지 않은 경우**

**설명:**
sidecar 메시는 "이 Pod에서 나가는 모든 outbound 트래픽을 Envoy 포트로 리다이렉트"하는 iptables 규칙을 심습니다. Lattice 향 트래픽도 outbound이므로 Envoy가 가로채지만 Envoy는 그 목적지를 설정에서 찾을 수 없어 실패합니다. 해결책은 Lattice 대역(`169.254.171.0/24`, IPv6를 쓰면 `fd00:ec2:80::/64`도)을 인터셉트 대상에서 제외하는 것입니다. Istio는 `traffic.sidecar.istio.io/excludeOutboundIPRanges` 애노테이션을 씁니다.
</details>

4. Lattice 도입 후 목적지 IP 기반 관측·통제가 무의미해지는 이유와 대안으로 올바른 것은?
   - A) 목적지 IP가 암호화되기 때문 — 대안은 없다
   - B) 모든 Lattice 서비스가 같은 link-local 대역으로 보여 서비스를 식별하지 못하기 때문 — 인가는 auth policy로, 관측은 access log로, SG는 managed prefix list로 옮긴다
   - C) flow log가 비활성화되기 때문 — flow log를 켜면 해결된다
   - D) VPC CNI가 IP를 재사용하기 때문 — IP 할당 정책을 변경하면 된다

<details>

<summary>정답 보기</summary>

**정답: B) 모든 Lattice 서비스가 같은 link-local 대역으로 보여 서비스를 식별하지 못하기 때문 — 인가는 auth policy로, 관측은 access log로, SG는 managed prefix list로 옮긴다**

**설명:**
link-local 주소는 전역적으로 고유하지 않고 서비스를 식별하지도 않습니다. 따라서 flow log의 목적지 IP로 통신 상대를 알 수 없고, 목적지 CIDR 기반 SG egress 규칙이나 NetworkPolicy `ipBlock`으로 서비스를 구분할 수 없습니다. 대안은 통제 계층을 옮기는 것입니다 — 인가는 auth policy의 principal·경로·메서드·헤더 조건으로, 관측은 Lattice access log로, SG는 `com.amazonaws.<region>.vpc-lattice` prefix list로. 이는 "IP와 포트로 통제"에서 "신원과 정책으로 통제"로의 이동입니다.
</details>

5. SNI가 TLS `ClientHello`에 평문으로 담기는 이유는?
   - A) TLS 설계 초기의 보안 취약점이 그대로 남은 것이다
   - B) 인증서 선택의 닭-달걀 문제 때문 — 암호화를 시작하려면 도메인을 알아야 하고, 도메인은 암호화된 `Host` 헤더 안에 있으므로 암호화 시작 전에 평문으로 보내야 순환이 끊긴다
   - C) 성능을 위해 SNI 암호화를 생략한 것이다
   - D) 방화벽 통과를 위해 의도적으로 노출한 것이다

<details>

<summary>정답 보기</summary>

**정답: B) 인증서 선택의 닭-달걀 문제 때문 — 암호화를 시작하려면 도메인을 알아야 하고, 도메인은 암호화된 `Host` 헤더 안에 있으므로 암호화 시작 전에 평문으로 보내야 순환이 끊긴다**

**설명:**
하나의 IP·포트에서 여러 도메인을 서비스하려면 서버가 어떤 인증서를 제시할지 골라야 하고, 그러려면 클라이언트가 원하는 도메인을 알아야 합니다. 그런데 그 도메인은 HTTP `Host` 헤더에 있고 `Host`는 TLS 안에 암호화되어 들어옵니다. 이 순환을 끊는 유일한 방법이 암호화 시작 전에 `ClientHello`에 도메인을 평문으로 담는 것입니다. 즉 설계 실수가 아니라 의도적 타협이며, 덕분에 TLS를 종료하지 않는 중간 장비도 목적지 도메인을 알 수 있어 TLS Passthrough 라우팅이 가능해집니다.
</details>

6. Lattice가 독립적인 Raw TCP listener를 지원하지 않는 근본 이유는?
   - A) TCP는 AWS 네트워크에서 지원되지 않는 프로토콜이기 때문
   - B) TLS가 없으면 `ClientHello`가 없고 따라서 SNI가 없어 라우팅의 근거가 전혀 없기 때문 — 목적지 IP도 link-local이라 서비스를 식별하지 않는다
   - C) NLB가 이미 그 역할을 하므로 중복이기 때문
   - D) 보안 규정상 평문 통신이 금지되어 있기 때문

<details>

<summary>정답 보기</summary>

**정답: B) TLS가 없으면 `ClientHello`가 없고 따라서 SNI가 없어 라우팅의 근거가 전혀 없기 때문 — 목적지 IP도 link-local이라 서비스를 식별하지 않는다**

**설명:**
Lattice가 하는 일의 최소 단위는 "이 연결을 어느 Target으로 보낼지 결정"하는 것이고 그 결정에는 근거가 필요합니다. HTTP/HTTPS는 경로·헤더·메서드라는 풍부한 근거가 있고, TLS Passthrough는 SNI라는 근거가 하나 있습니다. Raw TCP는 아무것도 없습니다 — 남는 것은 포트뿐인데 포트만으로는 여러 서비스를 다중화할 수 없습니다. 이는 원리적 제약이므로 향후에도 해소를 기대하기 어렵고, 평문 TCP 서비스는 NLB 등 Hybrid 구성이 필요합니다.
</details>

7. HTTPS listener와 TLS Passthrough의 트레이드오프를 올바르게 서술한 것은?
   - A) TLS Passthrough가 모든 면에서 우수하다
   - B) 종단간 암호화를 유지하려면 L7 라우팅과 IAM Auth를 포기해야 하고, L7 라우팅과 IAM Auth를 쓰려면 Lattice에서 TLS가 한 번 종료되는 것을 받아들여야 한다
   - C) 둘을 하나의 서비스에서 동시에 적용할 수 있다
   - D) HTTPS listener는 SNI를 볼 수 없다

<details>

<summary>정답 보기</summary>

**정답: B) 종단간 암호화를 유지하려면 L7 라우팅과 IAM Auth를 포기해야 하고, L7 라우팅과 IAM Auth를 쓰려면 Lattice에서 TLS가 한 번 종료되는 것을 받아들여야 한다**

**설명:**
HTTPS listener는 TLS를 종료하므로 경로·헤더·메서드와 `Authorization` 헤더를 볼 수 있어 L7 라우팅과 IAM Auth가 가능하지만, Lattice에서 평문이 되는 지점이 생깁니다. TLS Passthrough는 종단간 암호화와 엔드포인트 자체 mTLS를 유지하지만 Lattice가 SNI만 보므로 L7 라우팅과 IAM Auth가 불가능합니다. 둘 중 하나를 골라야 하며 하나의 서비스에서 동시에 가질 수 없습니다. 참고로 SNI는 두 방식 모두에서 볼 수 있습니다.
</details>
