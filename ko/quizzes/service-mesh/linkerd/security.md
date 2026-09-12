# Linkerd 보안 퀴즈

2026년 9월 11일 검토한 [보안 가이드](../../../service-mesh/linkerd/04-security.md)를 기준으로 합니다.

### 1. Linkerd가 mesh mTLS를 활성화하는 방식은?

- A. 각 서비스가 Linkerd TLS를 직접 구현
- B. 참여하는 mesh Pod 사이의 대상 TCP 트래픽에 자동 적용
- C. Kubernetes Secret만 있으면 모든 경로가 암호화됨
- D. 모든 UDP 트래픽 자동 보호

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** 양쪽 proxy가 참여하고 인증서 체인을 신뢰해야 합니다. Mesh 밖 endpoint와 skip port에 Linkerd mTLS가 자동 적용되지는 않습니다. 기본 설정은 inbound 평문을 허용할 수 있으므로 인증된 접근이 필요하면 적합한 정책으로 강제합니다.

</details>

### 2. Server 리소스가 선택하는 것은?

- A. 외부 DNS record
- B. 같은 namespace의 대상 Pod에 있는 inbound port/protocol
- C. 인증서 Secret
- D. Outbound 로드 밸런서 알고리즘

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** Server는 Pod/port 대상을 선택합니다. 애플리케이션 port를 선언하고 Server 중복을 피합니다. accessPolicy로 바꾸지 않으면 미일치 트래픽은 기본 거부입니다. Proxy admin port 4191에 Server를 정의해도 interception 우회가 사라지지는 않습니다.

</details>

### 3. ServerAuthorization의 meshTLS.serviceAccounts가 정의하는 것은?

- A. 서버의 serviceAccountName
- B. 허용하는 인증된 client ServiceAccount
- C. 모든 인증서를 발급하는 계정
- D. 지표 수집 전용 계정

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** 해당 허용 정책은 일치하는 mesh client identity를 허용합니다. 다른 정책도 접근을 넓힐 수 있습니다. 선택한 버전의 ServerAuthorization은 v1beta1이며 AuthorizationPolicy에서 ServiceAccount를 직접 참조하는 대안도 있습니다.

</details>

### 4. Default-deny에서 의도한 business 트래픽을 허용하는 방법은?

- A. 모든 요청이 계속 자동 허용됨
- B. 대상과 일치하는 인가 허용 정책 정의
- C. 일반 namespace label로 모든 caller 허용
- D. 임의의 ConfigMap whitelist만 있으면 됨

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** Server와 AuthorizationPolicy를 사용하는 것이 현재 방식이며 ServerAuthorization은 이전 대안입니다. 반드시 순차 연결할 필요는 없습니다. 하나의 AuthorizationPolicy의 requiredAuthenticationRefs는 모두 일치해야 하며 probe 접근도 적절히 처리해야 합니다.

</details>

### 5. Trust anchor의 수명을 정하는 기준은?

- A. 항상 정확히 24시간
- B. 항상 무제한
- C. CA 정책·교체·복구 요구사항으로 결정하며 CLI 기본값은 1년
- D. 모든 cluster에 필수인 범용 1–10년 권장값

<details>
<summary>정답 및 설명</summary>

**정답: C**

**설명:** 수동으로 10년 root를 제공할 수 있지만 자동적인 모범 사례는 아닙니다. 체인의 모든 만료를 추적하고 issuer 수명과 갱신이 CA에 맞는지 확인합니다. Root 교체에는 linked cluster를 포함한 모든 사용자에게 겹치는 trust bundle을 배포해야 합니다.

</details>

### 6. ServerAuthorization의 client.unauthenticated:true가 허용하는 것은?

- A. Wildcard에 일치하는 인증된 identity만
- B. Mesh 인증을 요구하지 않는 client
- C. 특수 external header가 있는 caller만
- D. 대상과 무관하게 readiness URL만

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** 해당 target 범위에서 mesh 인증 없이 접근을 허용하며 자동으로 health path에만 제한되지는 않습니다. meshTLS.identities:["*"]는 다릅니다. 넓은 mesh identity 집합을 허용하지만 mesh 인증은 계속 요구합니다.

</details>

### 7. 같은 신뢰 root 아래에서 유효한 issuer를 갱신하면 보통 어떤 일이 일어나는가?

- A. 모든 proxy를 즉시 재시작해야 함
- B. Root도 항상 교체해야 함
- C. 소유자가 issuer Secret을 갱신하고 Identity가 파일을 검증/reload하며 proxy는 정상 leaf 갱신 수행
- D. 전체 cluster 재시작

<details>
<summary>정답 및 설명</summary>

**정답: C**

**설명:** IssuerUpdated를 확인하고 skipped/invalid 갱신을 조사합니다. 체인이 유효하면 기존 leaf가 정상 갱신 시점까지 이전 issuer를 사용할 수 있습니다. 매번 Identity 재시작이 필수는 아니며 trust anchor 교체는 별도의 단계적 절차입니다.

</details>

### 8. 올바르게 신뢰하는 multicluster client를 포함하여 인증된 mesh client를 요구하는 기본 정책은?

- A. deny
- B. all-unauthenticated
- C. all-authenticated
- D. cluster-unauthenticated

<details>
<summary>정답 및 설명</summary>

**정답: C**

**설명:** all-authenticated는 mesh 인증을 요구하지만 특정 caller만 허용하는 좁은 목록은 아닙니다. 명시적 Server 정책과 인가 허용도 중요하며 namespace 기본 annotation은 proxy 초기화 시 적용됩니다.

</details>

### 9. Cert-manager가 Linkerd signing issuer 인증서를 발급할 때 필요한 것은?

- A. isCA:false
- B. isCA:true 및 적절한 ECDSA P-256 credential과 유효한 chain
- C. 임의의 leaf에 digital-signature usage만
- D. 항상 RSA private key

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** Identity에는 workload 인증서에 서명할 intermediate CA가 필요합니다. rotationPolicy, Secret 형식/소유권, CA 수명을 확인하고 Identity가 결과를 읽는지 검증합니다. 요청에 isCA:true가 있다고 일반 Vault leaf 서명 경로가 CA를 발급함이 증명되지는 않습니다.

</details>

### 10. linkerd viz edges로 확인할 수 있는 것은?

- A. 모든 edge router의 hardware 상태
- B. 관찰된 resource edge와 mTLS/보안 상태
- C. 가능한 모든 경로와 idle 경로가 암호화되었다는 증명
- D. 최종 사용자 인증의 전체 감사

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** SECURED 표시는 관찰된 edge의 근거이며 전체 네트워크 목록은 아닙니다. 공개 인증서는 linkerd identity, 접근 판단은 정책 진단/지표로 확인합니다. CLI 표시를 Prometheus TLS label의 실제 값과 동일시하지 않습니다.

</details>

### 11. Linkerd와 애플리케이션 보안의 관계는?

- A. Mesh mTLS가 애플리케이션 보안을 대체
- B. Mesh의 workload/전송 제어와 사용자·tenant·business 인가가 상호 보완
- C. 허용된 ServiceAccount이면 모든 caller가 관리자임
- D. Mesh가 입력을 자동 검증

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** Linkerd는 workload 인증, 대상 전송 구간 암호화, inbound 인가를 제공합니다. 애플리케이션은 사용자 credential, 권한, 입력을 계속 검증해야 합니다. Network/admission 제어도 proxy 우회와 mesh 미등록 경로를 다뤄야 합니다.

</details>

### 12. 애플리케이션 계측이나 애플리케이션을 이해하는 별도 출처가 필요한 지표는?

- A. Proxy workload 인증서 만료
- B. Mesh client identity가 없는 관찰 HTTP 응답
- C. 애플리케이션 로그인 실패
- D. Proxy inbound 인가 거부 counter

<details>
<summary>정답 및 설명</summary>

**정답: C**

**설명:** Linkerd가 애플리케이션 로그인 결과를 자동으로 알지는 못합니다. 자체 알림에서도 leaf 만료 시각과 issuer TTL 시간을 구분하고 범위를 정한 rate 비율, identity label, 누락/무트래픽 처리를 사용해야 합니다.

</details>
