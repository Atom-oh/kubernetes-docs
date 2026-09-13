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

2. Lattice 주소 대역은 어떻게 해석해야 합니까?
   - A) IP 주소를 절약하기 위해
   - B) AWS의 서비스별 주소 문서를 따르며 prefix를 link-local interception의 일반 정의로 삼지 않는다
   - C) IPv4 주소 고갈에 대응하기 위해
   - D) 클라이언트가 목적지를 명시적으로 인식하게 하기 위해

<details>

<summary>정답 보기</summary>

**정답: B) AWS의 서비스별 주소 문서를 따르며 prefix를 link-local interception의 일반 정의로 삼지 않는다**

**설명:**
서비스별 route와 association이 도달성을 결정합니다. ULA는 link-local이나 폐기된 site-local 클래스가 아니며 주소 scope와 routing 도달성은 다릅니다.
</details>

3. 공존 중 Lattice 요청이 Envoy log에 보입니다. 다음으로 무엇을 확인해야 합니까?
   - A) Lattice의 quotas 초과
   - B) Mesh interception과 설정된 outbound route/서명 정책이 실패를 설명하는지 확인한다
   - C) Gateway API CRD 버전 불일치
   - D) Target Group 프로토콜 설정 오류

<details>

<summary>정답 보기</summary>

**정답: B) Mesh interception과 설정된 outbound route/서명 정책이 실패를 설명하는지 확인한다**

**설명:**
Envoy 정책에 따라 미등록 대상을 거부하거나 전달합니다. 규칙·log를 확인한 후 bypass/forwarding 설계를 시험하며 공존 자체가 필연적 실패를 뜻하지는 않습니다.
</details>

4. 안정적인 서비스 신원·인가에 목적지 IP만으로 부족한 이유는 무엇입니까?
   - A) 목적지 IP가 암호화되기 때문 — 대안은 없다
   - B) IP만 의존하지 말고 서비스 신원·DNS/request 상관관계·검토한 network 규칙을 사용한다
   - C) flow log가 비활성화되기 때문 — flow log를 켜면 해결된다
   - D) VPC CNI가 IP를 재사용하기 때문 — IP 할당 정책을 변경하면 된다

<details>

<summary>정답 보기</summary>

**정답: B) IP만 의존하지 말고 서비스 신원·DNS/request 상관관계·검토한 network 규칙을 사용한다**

**설명:**
서비스 신원은 안정된 서비스별 CIDR 보안 경계가 아닙니다. Network 증거는 auth policy·서비스 log·request ID와 함께 유용합니다. SG 변경에는 검토한 IaC를 사용합니다.
</details>

5. 올바른 SNI/ECH 구분은 무엇입니까?
   - A) TLS 설계 초기의 보안 취약점이 그대로 남은 것이다
   - B) 일반 TLS는 인증서 선택을 위해 SNI를 노출하며 ECH는 다른 설계지만 Lattice TLS passthrough는 지원하지 않는다
   - C) 성능을 위해 SNI 암호화를 생략한 것이다
   - D) 방화벽 통과를 위해 의도적으로 노출한 것이다

<details>

<summary>정답 보기</summary>

**정답: B) 일반 TLS는 인증서 선택을 위해 SNI를 노출하며 ECH는 다른 설계지만 Lattice TLS passthrough는 지원하지 않는다**

**설명:**
TLS passthrough에는 SNI와 일치하는 custom domain이 필요합니다. AWS는 ECH/ESNI 미지원을 명시하므로 평문 SNI가 보편적으로 불가피하거나 Lattice 지원이 단순 미확인이라고 설명하지 않습니다.
</details>

6. VPC Lattice의 raw TCP에 대한 올바른 설명은 무엇입니까?
   - A) TCP는 AWS 네트워크에서 지원되지 않는 프로토콜이기 때문
   - B) Raw TCP 서비스 listener는 없지만 TCP resource configuration/resource gateway는 별도로 지원된다
   - C) NLB가 이미 그 역할을 하므로 중복이기 때문
   - D) 보안 규정상 평문 통신이 금지되어 있기 때문

<details>

<summary>정답 보기</summary>

**정답: B) Raw TCP 서비스 listener는 없지만 TCP resource configuration/resource gateway는 별도로 지원된다**

**설명:**
제품 전체의 수학적 불가능성으로 설명하지 않습니다. 별도 resource-connectivity 접근 모델·controller 지원·routing 요구를 비교하고 h2c gRPC를 임의 raw TCP와 동일시하지 않습니다.
</details>

7. HTTPS listener와 TLS Passthrough의 트레이드오프를 올바르게 서술한 것은?
   - A) TLS Passthrough가 모든 면에서 우수하다
   - B) Passthrough는 endpoint TLS를 유지하지만 HTTP SigV4 신원을 검사하지 못하며 익명 네트워크 문맥 정책은 별개이다
   - C) 두 listener type 모두 복호화 없이 암호화된 HTTP SigV4 header를 인증한다
   - D) HTTPS listener는 SNI를 볼 수 없다

<details>

<summary>정답 보기</summary>

**정답: B) Passthrough는 endpoint TLS를 유지하지만 HTTP SigV4 신원을 검사하지 못하며 익명 네트워크 문맥 정책은 별개이다**

**설명:**
제약은 인증된 HTTP 신원과 L7 검사이지 모든 auth policy의 부재가 아닙니다. Listener·endpoint 제어를 명시 선택하며 backend HTTPS 암호화가 Lattice의 target 인증서 검증을 의미하지는 않습니다.
</details>
