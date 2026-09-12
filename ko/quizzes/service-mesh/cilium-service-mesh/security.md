# Cilium Service Mesh 보안 퀴즈

Cilium 1.20.1 기준입니다. [보안 본문](../../../service-mesh/cilium-service-mesh/03-security.md)에서 out-of-band 인증, 전송 암호화와 ztunnel 베타의 구분 및 공식 근거를 확인하세요.

### 1. Cilium out-of-band 상호 인증에서 SPIRE가 제공하는 것은?

- **A.** 모든 Pod의 Istio 사이드카
- **B.** Agent 인증 메커니즘에 사용할 SVID 신원 증명
- **C.** 그 자체로 모든 애플리케이션 트래픽의 자동 암호화
- **D.** Kubernetes API 서버 대체

<details>
<summary>정답 및 설명</summary>

**정답: B. Agent 인증 메커니즘에 사용할 SVID 신원 증명**

Out-of-band 베타 방식에서 SPIRE는 SVID 신원 증명을 제공하고 Cilium Agent는 애플리케이션 연결과 별개로 상대를 인증합니다. WireGuard/IPsec 암호화는 별도 선택입니다. Cilium 1.20.1에는 자체 CA·bootstrap·등록·정책 제약을 가진 별도의 ztunnel mTLS 베타도 있습니다.

</details>

### 2. CiliumNetworkPolicy에서 authentication mode가 'required'로 설정되면 어떻게 동작하나요?

- **A.** 인증 없이 모든 트래픽 허용
- **B.** 상호 인증이 성공한 트래픽만 허용
- **C.** 인증 실패 시 경고만 로깅
- **D.** mTLS 비활성화

<details>
<summary>정답 및 설명</summary>

**정답: B. 상호 인증이 성공한 트래픽만 허용**

일치하는 허용 규칙이 성공적인 인증을 요구합니다. 클러스터 전체 스위치가 아니며 애플리케이션 payload를 자체적으로 TLS 암호화하지 않습니다. 다른 인가·애플리케이션 인증도 필요합니다. API는 배열이 아니라 authentication: {mode: required} 객체입니다.

</details>

### 3. Cilium WireGuard만으로 암호화하지 않는 트래픽은?

- **A.** 서로 다른 노드 사이의 지원 Pod 트래픽
- **B.** 노드 암호화가 활성화된 지원 원격 노드 트래픽
- **C.** 같은 노드의 Pod 트래픽과 외부 클라이언트→클러스터 구간
- **D.** ClusterIP Service를 통한 지원 원격 Pod 경로

<details>
<summary>정답 및 설명</summary>

**정답: C. 같은 노드의 Pod 트래픽과 외부 클라이언트→클러스터 구간**

Cilium WireGuard는 같은 노드의 Pod 트래픽과 외부 클라이언트→클러스터 구간을 암호화하지 않습니다. 원격 노드 범위는 선택한 모드와 문서화된 예외에 따라 달라집니다. 커널 지원이 필요하며 chart에는 userspaceFallback 옵션이 없습니다.

</details>

### 4. CiliumNetworkPolicy에서 L7 HTTP 규칙으로 특정 경로와 메서드를 제한하는 올바른 구성은?

- **A.** toEndpoints에 path와 method 지정
- **B.** toPorts.rules.http에 method와 path 지정
- **C.** ingress.http에 직접 지정
- **D.** spec.http에 규칙 정의

<details>
<summary>정답 및 설명</summary>

**정답: B. toPorts.rules.http에 method와 path 지정**

HTTP 규칙은 ingress/egress의 toPorts.rules.http 아래에 있습니다. 지원되는 method·path·header를 검사하지만 헤더 존재나 Bearer 형태의 문자열로 JWT를 검증하거나 최종 사용자를 인가하지는 못합니다.

</details>

### 5. Cilium Identity 기반 정책의 이점은?

- **A.** Pod IP 변경에도 정책 레이블 selector를 유지할 수 있음
- **B.** 레이블 대신 MAC 주소 사용
- **C.** 모든 숫자 ID를 모든 재시작 뒤 영구 유지
- **D.** 주소·Identity 상태 갱신 제거

<details>
<summary>정답 및 설명</summary>

**정답: A. Pod IP 변경에도 정책 레이블 selector를 유지할 수 있음**

정책은 Pod IP 목록을 수동 관리하는 대신 Identity 관련 레이블 집합을 사용합니다. 여러 Pod가 Identity를 공유할 수 있지만 Cilium은 주소·Identity 상태를 갱신하고 ID를 정리·재할당할 수 있습니다. 재시작 후 같은 숫자 ID가 영구 유지된다는 보장은 아닙니다.

</details>

### 6. Cilium에서 DNS L7 정책을 사용하여 외부 도메인 접근을 제한할 때 사용하는 규칙은?

- **A.** toFQDNs와 dns rules 조합
- **B.** toEndpoints만 사용
- **C.** toCIDR만 사용
- **D.** toEntities만 사용

<details>
<summary>정답 및 설명</summary>

**정답: A. toFQDNs와 dns rules 조합**

DNS 규칙은 선택한 resolver의 질의를 제한하고, toFQDNs와 포트 규칙은 학습한 주소로의 연결을 별도로 제어합니다. 실제 UDP/TCP resolver 동작과 검색 목록 이름도 포함해야 합니다. Service 이름에는 서비스와 namespace가 모두 있고 DNS 허용은 범용 연결 허용이 아닙니다.

</details>

### 7. 기본 거부 정책을 도입할 때 무엇을 허용해야 하나요?

- **A.** 모든 외부 목적지
- **B.** 필요한 실제 resolver·probe 등 명시적인 워크로드 의존성
- **C.** 보편적인 최소 요건으로 모든 호스트 트래픽
- **D.** DNS가 과거에 반환한 모든 주소

<details>
<summary>정답 및 설명</summary>

**정답: B. 필요한 실제 resolver·probe 등 명시적인 워크로드 의존성**

실제 DNS resolver의 UDP/TCP53, 필요한 probe 등 워크로드·토폴로지에서 확인한 의존성만 허용합니다. 모든 호스트 네트워크 접근이 보편적인 최소 요건은 아닙니다. Cilium 정책의 방향별 규칙 배열이 비어 있으면 enableDefaultDeny를 명시해야 합니다.

</details>

### 8. SPIRE에서 workload attestation의 역할은?

- **A.** 인증서 발급
- **B.** 워크로드의 신원 확인
- **C.** 네트워크 정책 적용
- **D.** 트래픽 암호화

<details>
<summary>정답 및 설명</summary>

**정답: B. 워크로드의 신원 확인**

SPIRE Agent는 구성한 attestor·selector로 워크로드를 증명하고, Server는 Agent를 증명하며 SVID에 서명합니다. Cilium out-of-band 통합에는 위임 Identity 조회와 Cilium 보안 Identity 항목도 사용합니다. 애플리케이션 payload의 자동 암호화를 의미하지 않습니다.

</details>

### 9. Cilium에서 감사 모드(audit mode)로 네트워크 정책을 테스트할 때의 동작은?

- **A.** 모든 트래픽 차단
- **B.** 정책 위반을 로깅만 하고 트래픽은 허용
- **C.** 정책 완전 비활성화
- **D.** 알림만 전송

<details>
<summary>정답 및 설명</summary>

**정답: B. 정책 위반을 로깅만 하고 트래픽은 허용**

실제 변경 가능한 엔드포인트 옵션 PolicyAuditMode로 격리된 시험의 데이터패스 정책 적용을 바꿉니다. cilium.io/audit-mode는 지원되는 정책별 어노테이션이 아닙니다. 시험 후 차단을 복구하고 L7 동작은 별도 검증하세요. enableDefaultDeny:false도 범용 감사 모드가 아닙니다.

</details>

### 10. 3-tier 백엔드의 최소 권한 정책에서 모델링해야 하는 것은?

- **A.** 제한 없는 모든 트래픽
- **B.** 필요한 frontend ingress, database egress와 DNS 등 명시적 의존성
- **C.** Frontend를 포함한 모든 ingress 거부
- **D.** 무제한 인터넷 접근

<details>
<summary>정답 및 설명</summary>

**정답: B. 필요한 frontend ingress, database egress와 DNS 등 명시적 의존성**

백엔드는 필요한 frontend 호출자와 database 목적지에 더해 DNS 등의 명시적 의존성을 허용합니다. 본문의 database는 egress 허용 규칙 없이 egress 기본 거부를 명시합니다. 상태 기반 응답은 가능하며 네트워크 분리는 완전한 애플리케이션 인가나 데이터 유출 방지가 아닙니다.

</details>

### 11. IPsec의 keyRotationDuration: 5m은 무엇을 뜻하나요?

- **A.** 5분마다 새로운 키 생성
- **B.** 5분마다 모든 워크로드 인증서 교체
- **C.** 키 변경 후 전환·이전 키 정리 유예 기간
- **D.** 하나의 글로벌 키를 영구 재사용

<details>
<summary>정답 및 설명</summary>

**정답: C. 키 변경 후 전환·이전 키 정리 유예 기간**

IPsec의 keyRotationDuration은 키 자료 변경 후 전환·이전 키 제거 유예 기간입니다. 주기적으로 키를 생성하지 않습니다. 지원되는 절차로 키·ID를 조율하여 교체하고 '+'가 있는 터널별 파생 키 형식을 사용해야 합니다. WireGuard는 노드가 생성한 키 쌍을 관리합니다.

</details>

### 12. 원인을 살펴보기 전에 거부된 flow를 선택하는 Hubble 명령은?

- **A.** hubble observe --verdict FORWARDED
- **B.** hubble observe --verdict DROPPED
- **C.** hubble policy list
- **D.** hubble status --violations

<details>
<summary>정답 및 설명</summary>

**정답: B. hubble observe --verdict DROPPED**

DROPPED는 다양한 원인의 거부된 flow를 선택합니다. 보고된 정책 거부 drop에는 --drop-reason-desc POLICY_DENIED를 추가하고 L7·애플리케이션 실패는 별도로 관찰하세요. AUDIT는 별도 verdict이며 --last는 제한된 이력으로 Relay의 Hubble 인스턴스마다 반환될 수 있습니다.

</details>
