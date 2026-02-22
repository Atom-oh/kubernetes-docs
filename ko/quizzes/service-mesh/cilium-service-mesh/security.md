# Cilium Service Mesh 보안 퀴즈

이 퀴즈는 Cilium Service Mesh의 mTLS, 네트워크 정책, 암호화, ID 기반 보안, 제로 트러스트 네트워킹에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. Cilium Service Mesh에서 투명한 mTLS를 구현하기 위해 사용하는 기술은?

A. Istio sidecar
B. SPIFFE/SPIRE 통합
C. Nginx proxy
D. HAProxy

<details>
<summary>정답 및 설명</summary>

**정답: B. SPIFFE/SPIRE 통합**

**설명:**
Cilium Service Mesh는 SPIFFE(Secure Production Identity Framework for Everyone)와 SPIRE를 통합하여 투명한 mTLS를 구현합니다. 이를 통해 애플리케이션 코드 변경 없이 워크로드 간 암호화된 통신이 가능합니다.

</details>

### 2. CiliumNetworkPolicy에서 authentication mode가 'required'로 설정되면 어떻게 동작하나요?

A. 인증 없이 모든 트래픽 허용
B. 상호 인증이 성공한 트래픽만 허용
C. 인증 실패 시 경고만 로깅
D. mTLS 비활성화

<details>
<summary>정답 및 설명</summary>

**정답: B. 상호 인증이 성공한 트래픽만 허용**

**설명:**
authentication mode가 'required'로 설정되면, 상호 인증(mutual authentication)이 성공한 트래픽만 허용됩니다. 인증에 실패한 트래픽은 차단됩니다. 이는 제로 트러스트 보안 모델을 구현하는 데 핵심적입니다.

</details>

### 3. Cilium에서 WireGuard 암호화의 장점이 아닌 것은?

A. 커널 레벨에서 동작하여 높은 성능
B. 자동 키 관리
C. IETF 표준 프로토콜
D. ChaCha20Poly1305 암호화

<details>
<summary>정답 및 설명</summary>

**정답: C. IETF 표준 프로토콜**

**설명:**
WireGuard는 비표준 프로토콜입니다. IETF 표준 프로토콜은 IPsec입니다. 그러나 WireGuard는 Linux 커널 5.6+에 빌트인되어 있으며, 높은 성능, 자동 키 관리, ChaCha20Poly1305 암호화를 제공합니다.

</details>

### 4. CiliumNetworkPolicy에서 L7 HTTP 규칙으로 특정 경로와 메서드를 제한하는 올바른 구성은?

A. toEndpoints에 path와 method 지정
B. toPorts.rules.http에 method와 path 지정
C. ingress.http에 직접 지정
D. spec.http에 규칙 정의

<details>
<summary>정답 및 설명</summary>

**정답: B. toPorts.rules.http에 method와 path 지정**

**설명:**
CiliumNetworkPolicy에서 L7 HTTP 규칙은 toPorts 섹션의 rules.http 하위에 정의합니다. 여기서 method(GET, POST 등)와 path(정규식 지원)를 지정하여 세밀한 접근 제어가 가능합니다.

</details>

### 5. Cilium Identity 기반 보안의 주요 장점은?

A. IP 주소 변경에 영향받지 않음
B. MAC 주소 기반으로 더 안전함
C. 수동 ID 관리가 가능함
D. VLAN 태깅 지원

<details>
<summary>정답 및 설명</summary>

**정답: A. IP 주소 변경에 영향받지 않음**

**설명:**
Cilium Identity는 Pod 레이블을 기반으로 생성되므로, Pod가 재시작되어 IP 주소가 변경되어도 동일한 Identity를 유지합니다. 이는 IP 기반 보안 정책의 한계를 극복합니다.

</details>

### 6. Cilium에서 DNS L7 정책을 사용하여 외부 도메인 접근을 제한할 때 사용하는 규칙은?

A. toFQDNs와 dns rules 조합
B. toEndpoints만 사용
C. toCIDR만 사용
D. toEntities만 사용

<details>
<summary>정답 및 설명</summary>

**정답: A. toFQDNs와 dns rules 조합**

**설명:**
외부 도메인 접근 제한은 두 단계로 구성합니다: 1) DNS L7 규칙으로 특정 도메인 쿼리만 허용 (toPorts.rules.dns), 2) toFQDNs로 해당 도메인에 대한 실제 연결 허용. 이 조합으로 워크로드의 외부 접근을 세밀하게 제어합니다.

</details>

### 7. CiliumClusterwideNetworkPolicy로 기본 거부 정책을 구현할 때 일반적으로 허용해야 하는 트래픽은?

A. 모든 외부 트래픽
B. DNS 쿼리와 호스트 네트워크 트래픽
C. 모든 인터넷 트래픽
D. 특정 IP 대역만

<details>
<summary>정답 및 설명</summary>

**정답: B. DNS 쿼리와 호스트 네트워크 트래픽**

**설명:**
기본 거부 정책을 구현할 때, 클러스터가 정상 작동하려면 최소한 kube-dns로의 DNS 쿼리(포트 53/UDP)와 호스트 네트워크 트래픽(reserved:host)을 허용해야 합니다. 이 없이는 서비스 디스커버리와 노드 통신이 불가능합니다.

</details>

### 8. SPIRE에서 workload attestation의 역할은?

A. 인증서 발급
B. 워크로드의 신원 확인
C. 네트워크 정책 적용
D. 트래픽 암호화

<details>
<summary>정답 및 설명</summary>

**정답: B. 워크로드의 신원 확인**

**설명:**
Workload attestation은 SPIRE Agent가 워크로드의 신원을 확인하는 프로세스입니다. Kubernetes 환경에서는 Pod의 서비스 어카운트, 네임스페이스, 레이블 등을 검증하여 해당 워크로드에 적절한 SVID(SPIFFE Verifiable Identity Document)를 발급합니다.

</details>

### 9. Cilium에서 감사 모드(audit mode)로 네트워크 정책을 테스트할 때의 동작은?

A. 모든 트래픽 차단
B. 정책 위반을 로깅만 하고 트래픽은 허용
C. 정책 완전 비활성화
D. 알림만 전송

<details>
<summary>정답 및 설명</summary>

**정답: B. 정책 위반을 로깅만 하고 트래픽은 허용**

**설명:**
감사 모드(cilium.io/audit-mode: "true" 어노테이션)에서는 정책 위반 트래픽을 차단하지 않고 로깅만 합니다. 이를 통해 새 정책을 프로덕션에 적용하기 전에 영향을 평가할 수 있습니다.

</details>

### 10. 3-tier 아키텍처에서 마이크로세그멘테이션을 구현할 때 백엔드 서비스의 올바른 정책은?

A. 모든 트래픽 허용
B. 프론트엔드에서만 인그레스 허용, 데이터베이스로만 이그레스 허용
C. 모든 인그레스 차단
D. 인터넷 접근 허용

<details>
<summary>정답 및 설명</summary>

**정답: B. 프론트엔드에서만 인그레스 허용, 데이터베이스로만 이그레스 허용**

**설명:**
마이크로세그멘테이션에서 백엔드 서비스는 최소 권한 원칙을 따릅니다: 프론트엔드 티어에서만 인그레스를 허용하고, 데이터베이스 티어로만 이그레스를 허용합니다. 이렇게 하면 각 티어 간의 트래픽이 명확히 정의되고 제어됩니다.

</details>

### 11. Cilium에서 IPsec과 WireGuard 암호화의 차이점으로 올바른 것은?

A. IPsec만 커널에서 동작
B. WireGuard는 수동 키 관리 필요
C. IPsec은 IETF 표준, WireGuard는 비표준
D. WireGuard만 노드 간 암호화 지원

<details>
<summary>정답 및 설명</summary>

**정답: C. IPsec은 IETF 표준, WireGuard는 비표준**

**설명:**
IPsec은 IETF 표준 프로토콜이고, WireGuard는 비표준입니다. 둘 다 커널에서 동작하며, WireGuard는 자동 키 관리를 제공합니다. 둘 다 노드 간 암호화를 지원합니다.

</details>

### 12. Hubble을 사용하여 정책 위반을 모니터링할 때 사용하는 명령은?

A. hubble observe --verdict FORWARDED
B. hubble observe --verdict DROPPED
C. hubble policy list
D. hubble status --violations

<details>
<summary>정답 및 설명</summary>

**정답: B. hubble observe --verdict DROPPED**

**설명:**
`hubble observe --verdict DROPPED` 명령을 사용하면 네트워크 정책에 의해 거부된(DROPPED) 트래픽을 모니터링할 수 있습니다. 이를 통해 정책 위반을 실시간으로 감지하고 분석할 수 있습니다.

</details>
