# Linkerd 보안 퀴즈

이 퀴즈는 Linkerd 보안 기능에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. Linkerd에서 mTLS가 활성화되는 방식은?

A. 수동으로 각 서비스에 설정 필요
B. 자동으로 모든 메시 트래픽에 적용
C. Kubernetes Secret으로 설정 필요
D. 네임스페이스별로 활성화 필요

<details>
<summary>정답 및 설명</summary>

**정답: B. 자동으로 모든 메시 트래픽에 적용**

**설명:**
Linkerd의 핵심 가치 중 하나는 "보안이 기본값"입니다. 메시에 포함된 모든 서비스 간 트래픽은 별도 설정 없이 자동으로 mTLS가 적용됩니다.

</details>

### 2. Server 리소스의 역할은?

A. 외부 서버 연결 정의
B. 인바운드 트래픽 포트 및 프로토콜 정의
C. 서버 인증서 저장
D. 로드 밸런서 설정

<details>
<summary>정답 및 설명</summary>

**정답: B. 인바운드 트래픽 포트 및 프로토콜 정의**

**설명:**
Server 리소스는 특정 Pod의 인바운드 트래픽을 정의합니다. podSelector로 대상 Pod를, port로 포트를, proxyProtocol로 프로토콜(HTTP/1, HTTP/2, gRPC, opaque)을 지정합니다.

</details>

### 3. ServerAuthorization에서 meshTLS.serviceAccounts가 지정하는 것은?

A. 서버가 사용할 ServiceAccount
B. 접근이 허용된 클라이언트 ServiceAccount
C. 인증서 발급 권한이 있는 ServiceAccount
D. 메트릭 수집 권한이 있는 ServiceAccount

<details>
<summary>정답 및 설명</summary>

**정답: B. 접근이 허용된 클라이언트 ServiceAccount**

**설명:**
ServerAuthorization의 meshTLS.serviceAccounts는 해당 Server에 접근할 수 있는 클라이언트의 ServiceAccount를 지정합니다. 지정된 ServiceAccount를 가진 워크로드만 접근이 허용됩니다.

</details>

### 4. default-deny 정책 모드에서 트래픽 허용 방법은?

A. 모든 트래픽이 자동으로 허용됨
B. 명시적 ServerAuthorization 정의 필요
C. 네임스페이스 레이블로 허용
D. ConfigMap에서 화이트리스트 설정

<details>
<summary>정답 및 설명</summary>

**정답: B. 명시적 ServerAuthorization 정의 필요**

**설명:**
default-deny 모드에서는 모든 트래픽이 기본적으로 거부됩니다. 트래픽을 허용하려면 Server와 ServerAuthorization을 명시적으로 정의해야 합니다. 이는 제로 트러스트 보안 모델입니다.

</details>

### 5. Trust Anchor의 권장 유효 기간은?

A. 24시간
B. 1년
C. 1-10년
D. 무제한

<details>
<summary>정답 및 설명</summary>

**정답: C. 1-10년**

**설명:**
Trust Anchor(Root CA)는 장기간 유효해야 합니다. 일반적으로 1-10년을 권장합니다. Trust Anchor 교체는 복잡하므로 충분히 긴 유효 기간을 설정하되, 보안 요구사항에 따라 조정합니다.

</details>

### 6. 비인증 클라이언트(메시 외부)를 허용하는 ServerAuthorization 설정은?

A. `meshTLS.identities: ["*"]`
B. `unauthenticated: true`
C. `external: allowed`
D. `client: any`

<details>
<summary>정답 및 설명</summary>

**정답: B. `unauthenticated: true`**

**설명:**
`client.unauthenticated: true`를 설정하면 mTLS 인증 없는 클라이언트(메시 외부)의 접근을 허용합니다. 헬스체크나 인그레스에서 오는 트래픽에 사용됩니다.

</details>

### 7. Identity Issuer 인증서 갱신 시 필요한 작업은?

A. 모든 프록시 재시작 필요
B. Trust Anchor도 함께 교체 필요
C. Kubernetes Secret 업데이트 후 Identity Controller 재시작
D. 클러스터 전체 재시작 필요

<details>
<summary>정답 및 설명</summary>

**정답: C. Kubernetes Secret 업데이트 후 Identity Controller 재시작**

**설명:**
Identity Issuer 갱신 시: 1) 새 인증서로 Secret 업데이트, 2) Identity Controller 재시작. 프록시는 자동으로 새 인증서로 갱신됩니다. Trust Anchor가 동일하면 교체 불필요합니다.

</details>

### 8. 정책 모드 중 메시 내부 mTLS 트래픽만 허용하는 것은?

A. deny
B. all-unauthenticated
C. all-authenticated
D. cluster-unauthenticated

<details>
<summary>정답 및 설명</summary>

**정답: C. all-authenticated**

**설명:**
`all-authenticated` 모드는 메시 내부의 mTLS 인증된 트래픽만 허용합니다. 메시 외부에서 오는 비인증 트래픽은 거부됩니다.

</details>

### 9. cert-manager와 Linkerd 통합 시 Certificate 리소스에 필요한 설정은?

A. isCA: false
B. isCA: true
C. usages: [digital signature]
D. algorithm: RSA

<details>
<summary>정답 및 설명</summary>

**정답: B. isCA: true**

**설명:**
Linkerd Identity Issuer는 중간 CA 역할을 하므로 cert-manager Certificate에 `isCA: true`를 설정해야 합니다. 이 인증서가 워크로드 인증서를 서명하기 때문입니다.

</details>

### 10. linkerd viz edges 명령어로 확인할 수 있는 것은?

A. 네트워크 에지 라우터 상태
B. 서비스 간 mTLS 연결 상태
C. 클러스터 경계 정책
D. DNS 엣지 캐시 상태

<details>
<summary>정답 및 설명</summary>

**정답: B. 서비스 간 mTLS 연결 상태**

**설명:**
`linkerd viz edges`는 서비스 간 연결(엣지)을 보여주며, SECURED 열에서 mTLS 적용 여부를 확인할 수 있습니다. 메시 외부 트래픽은 SECURED가 X로 표시됩니다.

</details>

### 11. Linkerd 보안과 애플리케이션 보안의 관계로 올바른 것은?

A. Linkerd가 모든 보안을 처리하므로 애플리케이션 보안 불필요
B. Linkerd는 전송 계층, 애플리케이션은 비즈니스 로직 보안 담당
C. 애플리케이션 보안만으로 충분하며 Linkerd 보안은 선택적
D. 두 보안은 완전히 독립적이며 상호작용 없음

<details>
<summary>정답 및 설명</summary>

**정답: B. Linkerd는 전송 계층, 애플리케이션은 비즈니스 로직 보안 담당**

**설명:**
심층 방어 원칙에 따라 Linkerd는 전송 암호화(mTLS)와 서비스 인가를 담당하고, 애플리케이션은 사용자 인증(JWT), RBAC, 입력 검증 등 비즈니스 로직 보안을 담당합니다.

</details>

### 12. Prometheus 알림으로 모니터링해야 할 Linkerd 보안 메트릭이 아닌 것은?

A. 인증서 만료 시간
B. 비mTLS 트래픽 비율
C. 애플리케이션 로그인 실패 횟수
D. 인가 거부된 요청 수

<details>
<summary>정답 및 설명</summary>

**정답: C. 애플리케이션 로그인 실패 횟수**

**설명:**
Linkerd 보안 메트릭: 인증서 만료 시간, 비mTLS 트래픽 비율, 인가 거부 요청 수. 애플리케이션 로그인 실패는 애플리케이션 레벨 메트릭으로 Linkerd 범위 외입니다.

</details>
