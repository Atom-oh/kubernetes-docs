# SPIFFE/SPIRE 퀴즈

> **마지막 업데이트**: 2026년 9월 13일

## 문제

<span id="_1-spiffe-id의-올바른-형식은"></span>

### 1. 올바른 SPIFFE ID 형식은?

- A) `https://example.org/app`
- B) `spiffe://example.org/app`
- C) `spiffe://example.org:8443/app`
- D) `spiffe://example.org/app?role=admin`

<details>
<summary>정답 보기</summary>

**정답: B) spiffe://example.org/app**

scheme은 spiffe이며 trust domain과 선택적 path를 사용합니다. port·query·fragment는 허용되지 않습니다. path 계층은 조직이 정하며 /ns/.../sa/...만 가능한 것은 아닙니다.

</details>

<span id="_2-x-509-svid와-jwt-svid의-주요-차이점은"></span>

### 2. X.509-SVID와 JWT-SVID 검증에 대한 올바른 설명은?

- A) X.509의 CN만 검사
- B) JWT는 서명만 맞으면 audience 불필요
- C) X.509는 URI SAN·chain을, JWT는 서명·sub·audience·expiry를 검증
- D) JWT audience 검사는 모든 replay를 차단

<details>
<summary>정답 보기</summary>

**정답: C) X.509는 URI SAN·chain을, JWT는 서명·sub·audience·expiry를 검증**

인증서 CN은 SPIFFE 신원 기준이 아닙니다. JWT bearer token은 audience가 맞아도 재사용될 수 있습니다. TTL은 정책별이며 이 장의 X.509/JWT 범위와 별도 Incubating WIT-SVID 사양을 구분합니다.

</details>

<span id="_3-spire-server의-주요-역할은"></span>

### 3. SPIRE Server의 역할은?

- A) 모든 앱 네트워크를 자동 암호화
- B) Agent attestation·registration과 SVID 서명 관리
- C) 모든 서비스 요청 권한을 자동 결정
- D) CSI로 모든 Pod에 개인키 파일 배포

<details>
<summary>정답 보기</summary>

**정답: B) Agent attestation·registration과 SVID 서명 관리**

Server의 CA/JWT 서명과 DataStore·KeyManager 책임을 구분합니다. AWS PCA upstream은 SPIRE 중간 CA를 서명하며 local leaf 서명과 signing key가 사라지는 것은 아닙니다.

</details>

<span id="_4-spire-agent의-주요-역할은"></span>

### 4. Workload API를 호출한 앱의 신원을 확인하는 주체는?

- A) 로컬 SPIRE Agent의 workload attestor
- B) DNS resolver
- C) CSI가 파일명만 확인
- D) 앱이 선언한 SPIFFE ID 문자열만 신뢰

<details>
<summary>정답 보기</summary>

**정답: A) 로컬 SPIRE Agent의 workload attestor**

호출 프로세스 PID/cgroup·Pod metadata 등을 확인하고 허용 entry·cache와 매칭합니다. Agent Pod 내부에서 실행한 fetch는 그 호출자를 검증하므로 실제 앱 context 검증을 대신하지 않습니다.

</details>

<span id="_5-eks-환경에서-spire-노드-어테스테이션에-권장되는-방식은"></span>

### 5. k8s_psat의 토큰을 Server가 검증하는 경로는?

- A) IRSA IAM role의 S3 권한 검사
- B) Kubernetes TokenReview와 설정한 audience·SA allowlist 확인
- C) 토큰 문자열만 base64 decode
- D) 만료 없는 join token으로 변환

<details>
<summary>정답 보기</summary>

**정답: B) Kubernetes TokenReview와 설정한 audience·SA allowlist 확인**

Server/Agent logical cluster 이름·token audience·SA allowlist·TokenReview 권한이 맞아야 합니다. aws_iid는 다른 신뢰 가정의 대안이며 무조건 더 강하다거나 EKS에서 사용할 수 없다고 단정하지 않습니다.

</details>

<span id="_6-kubernetes-워크로드-어테스테이션에서-사용되는-셀렉터-형식은"></span>

### 6. k8s:container-image:nginx:* selector의 해석은?

- A) 모든 nginx 태그를 자동 glob 매칭
- B) 단순 selector 문자열이며 wildcard를 가정하면 안 됨
- C) 이미지 서명 검증 완료 의미
- D) namespace RBAC를 자동 강제

<details>
<summary>정답 보기</summary>

**정답: B) 단순 selector 문자열이며 wildcard를 가정하면 안 됨**

Kubernetes가 보고하는 실제 image/ImageID와 일치해야 합니다. tag 이름만으로 supply-chain 신뢰를 보장하지 않습니다. Pod·SA·label 생성/변경 권한도 identity 발급 범위에 영향을 줍니다.

</details>

<span id="_7-spiffe-csi-driver의-주요-목적은"></span>

### 7. SPIFFE CSI 0.2.13이 Pod에 mount하는 것은?

- A) 자동 갱신되는 svid.pem·svid.key 파일
- B) Workload API Unix socket이 있는 디렉터리
- C) SPIRE CA 개인키
- D) 공유 PostgreSQL 데이터

<details>
<summary>정답 보기</summary>

**정답: B) Workload API Unix socket이 있는 디렉터리**

CSI는 API socket 전달을 돕습니다. 인증서 파일이 필요한 앱은 별도 adapter와 reload 처리가 필요합니다. 앱 또는 proxy가 API를 사용해야 하므로 모든 앱이 변경 없이 자동 통합되는 것은 아닙니다.

</details>

<span id="_8-spiffe-페더레이션의-주요-기능은"></span>

### 8. https_spiffe 페더레이션 bootstrap에 필요한 것은?

- A) endpoint URL만 입력
- B) 신뢰할 초기 bundle과 올바른 endpoint SPIFFE ID
- C) 두 도메인의 CA 개인키 교환
- D) 원격 도메인 모든 workload 권한 자동 허용

<details>
<summary>정답 보기</summary>

**정답: B) 신뢰할 초기 bundle과 올바른 endpoint SPIFFE ID**

신뢰 관계는 방향별로 구성합니다. bundle 갱신·네트워크·TLS 검증과 workload authorization은 별도 책임입니다. https_web은 해당 endpoint의 Web PKI 검증 경로를 사용합니다.

</details>

<span id="_9-spiffe-spire와-aws-irsa-iam-roles-for-service-accounts-비교-시-spiffe의-장점은"></span>

### 9. IRSA와 SPIFFE/SPIRE를 함께 설명한 올바른 내용은?

- A) IRSA 갱신에는 항상 Pod 재시작 필요
- B) SPIFFE를 쓰면 AWS IAM 정책 불필요
- C) IRSA는 AWS API credential 경로, SPIFFE는 workload identity 경로이며 각각 검증 필요
- D) Pod annotation만 붙이면 IRSA와 CSI 파일 발급 완료

<details>
<summary>정답 보기</summary>

**정답: C) IRSA는 AWS API credential 경로, SPIFFE는 workload identity 경로이며 각각 검증 필요**

IRSA는 지원 SDK/projected token으로 갱신하고 cross-account 구성이 가능합니다. ServiceAccount annotation·trust aud/sub·실제 AWS 권한을 확인합니다. SPIFFE mTLS도 앱/프록시의 credential 사용과 상대 ID 허용이 필요합니다.

</details>

<span id="_10-spiffe-trust-domain-네이밍-모범-사례는"></span>

### 10. Trust domain과 CA 키 교체에 대한 올바른 설명은?

- A) Trust domain은 반드시 실제 DNS 이름이어야 함
- B) bundle set을 실행하면 CA 개인키가 자동 교체
- C) 안정된 이름을 선택하고 bundle 변경과 CA 키 회전을 구분
- D) 숫자나 IPv4 형태 trust domain은 항상 parser에서 거부

<details>
<summary>정답 보기</summary>

**정답: C) 안정된 이름을 선택하고 bundle 변경과 CA 키 회전을 구분**

DNS-like naming은 운영 권고이며 사양상 유효한 이름 범위와 같지 않습니다. bundle은 공개 신뢰 자료이고 key rotation은 별도 수명주기입니다. 이전·새 authority의 겹치는 기간과 소비자 갱신을 검증합니다.

</details>

## 점수 계산

- 9–10개: 핵심 개념 이해
- 7–8개: 신뢰·권한·전달 경로 복습
- 6개 이하: 본문과 검증 예제로 복습

## 관련 문서

- [SPIFFE/SPIRE](../../security/12-spiffe-spire.md)
