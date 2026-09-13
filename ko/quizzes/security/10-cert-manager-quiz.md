# cert-manager 퀴즈

> **마지막 업데이트**: 2026년 9월 13일

인증서 발급·갱신·신뢰 배포와 AWS 연동의 경계를 확인하는 10문제입니다.

## 문제

### 1. cert-manager 프로젝트의 CNCF 상태는?

- A) Sandbox
- B) Incubating
- C) Graduated
- D) Archived

<details>
<summary>정답 보기</summary>

**정답: C) Graduated**

2024년 9월 29일 Graduated로 승격됐습니다. 2022년 9월 19일은 Incubating 승격일입니다. 프로젝트 성숙도와 개별 설치의 보안·가용성 검증은 구분합니다.

</details>

<span id="_2-cert-manager의-핵심-구성요소가-아닌-것은"></span>

### 2. Certificate를 감시하고 발급·갱신을 조정하는 구성요소는?

- A) cainjector
- B) webhook
- C) controller
- D) scheduler

<details>
<summary>정답 보기</summary>

**정답: C) controller**

controller가 인증서 수명주기를 조정합니다. webhook은 커스텀 리소스 검증·defaulting·변환, cainjector는 지원되는 API/webhook 설정의 CA bundle 주입을 담당합니다.

</details>

### 3. Issuer와 ClusterIssuer의 주요 차이점은?

- A) Issuer만 ACME 지원
- B) Issuer는 namespace 범위, ClusterIssuer는 cluster 범위
- C) ClusterIssuer만 자동 갱신
- D) ClusterIssuer를 만들면 SAN 정책이 자동 강제됨

<details>
<summary>정답 보기</summary>

**정답: B) Issuer는 namespace 범위, ClusterIssuer는 cluster 범위**

Issuer는 같은 namespace에서 참조합니다. ClusterIssuer의 인증·CA Secret은 controller의 cluster-resource namespace(기본 cert-manager)에 있습니다. 범위만으로 요청자의 SAN·issuerRef 권한을 제한하지 않으므로 별도 승인·admission 정책이 필요합니다.

</details>

<span id="_4-acme-챌린지-방식-중-와일드카드-인증서를-지원하는-것은"></span>

### 4. 일반적인 Let’s Encrypt ACME 와일드카드 발급에 사용하는 검증 방식은?

- A) HTTP-01
- B) DNS-01
- C) TLS-ALPN-01
- D) 포트 443 연결만 확인

<details>
<summary>정답 보기</summary>

**정답: B) DNS-01**

DNS-01은 TXT 레코드로 도메인 제어를 검증합니다. HTTP-01은 포트 80 접근이 필요하고 와일드카드를 지원하지 않습니다. DNS API 권한은 지정된 zone·TXT 이름으로 제한합니다. 재사용 authorization이나 ACM 사전 검증에서는 매번 새 Challenge가 필요하지 않을 수 있습니다.

</details>

<span id="_5-certificate-리소스의-secretname-필드의-역할은"></span>

### 5. Certificate.spec.secretName의 역할은?

- A) ACME 계정 키 Secret
- B) 같은 namespace의 인증서·개인키 출력 Secret
- C) 항상 root CA를 배포할 ConfigMap
- D) Issuer 인증 Secret

<details>
<summary>정답 보기</summary>

**정답: B) 같은 namespace의 인증서·개인키 출력 Secret**

출력 Secret의 tls.crt·tls.key를 지정합니다. ca.crt는 발급 경로에 따라 없을 수 있고 클라이언트 신뢰 배포를 대체하지 않습니다. privateKey.rotationPolicy 기본값은 1.18부터 Always이며, Secret 갱신 후 애플리케이션 reload는 별도 확인합니다.

</details>

<span id="_6-aws-private-ca-pca-를-kubernetes에서-사용하기-위한-cert-manager-확장은"></span>

### 6. AWS Private CA를 cert-manager 외부 Issuer로 연결하는 확장은?

- A) aws-pca-controller
- B) aws-privateca-issuer
- C) acmesolver
- D) trust-manager

<details>
<summary>정답 보기</summary>

**정답: B) aws-privateca-issuer**

aws-privateca-issuer가 AWSPCAIssuer/AWSPCAClusterIssuer를 처리합니다. CA ARN으로 범위를 제한한 IAM 권한과 workload identity, 요청 승인, CA 모드·template·수명 확인이 필요합니다. 사설 CA 인증서는 일반 브라우저의 공개 신뢰나 무료 발급을 보장하지 않습니다.

</details>

### 7. trust-manager의 주요 기능은?

- A) 인증서와 개인키 발급
- B) 선택한 namespace에 CA bundle 배포
- C) CA 개인키를 모든 Pod에 복제
- D) 인증서 자동 폐기

<details>
<summary>정답 보기</summary>

**정답: B) 선택한 namespace에 CA bundle 배포**

기본 0.25.0 chart는 Bundle v1alpha1을 사용합니다. source는 설정된 trust namespace에서 읽고 namespaceSelector로 배포 범위를 제한합니다. ConfigMap target을 사용할 수 있고 Secret target은 별도 활성화·RBAC가 필요합니다. subPath mount는 갱신을 전달하지 않으며 directory mount도 process reload를 보장하지 않습니다.

</details>

<span id="_8-certificate-리소스의-renewbefore-필드-설정-시-갱신-동작은"></span>

### 8. 요청 duration은 90일이지만 실제 인증서는 45일이고 갱신 설정·ARI가 없다면 기본 갱신 시점은?

- A) 실제 유효기간 시작 후 약 30일
- B) 요청한 90일 기준 60일
- C) 항상 만료 30일 전
- D) 항상 발급 75일 후

<details>
<summary>정답 보기</summary>

**정답: A) 실제 유효기간 시작 후 약 30일**

기본값은 실제 X.509 수명의 2/3 지점입니다. 실제 90일 인증서에 renewBefore:360h가 적용되면 75일째라는 계산이 맞습니다. renewBefore와 renewBeforePercentage는 동시에 지정하지 않습니다. 1.21의 renewal policy/windows 또는 지원되는 ARI 경로가 있으면 status.renewalTime을 확인해야 합니다.

</details>

<span id="_9-istio-서비스-메시와-cert-manager를-연동하는-컴포넌트는"></span>

### 9. Istio sidecar 인증서 발급 경로를 올바르게 설명한 것은?

- A) Envoy가 CA 개인키로 직접 서명
- B) istio-agent → istio-csr → CertificateRequest/Issuer, SDS로 Envoy에 전달
- C) 애플리케이션과 같은 Pod의 모든 통신이 자동 mTLS
- D) rootCAFile 경로만 있으면 실제 CA mount 불필요

<details>
<summary>정답 보기</summary>

**정답: B) istio-agent → istio-csr → CertificateRequest/Issuer, SDS로 Envoy에 전달**

istio-agent가 CSR을 만들고 istio-csr가 cert-manager 발급 경로에 연결합니다. 프록시 간 mTLS와 로컬 애플리케이션 hop을 구분합니다. 실제 신뢰 root mount·Issuer 준비·Istio external CA 설정이 필요하며 별도 Kubernetes CSR RA 모드를 혼합하지 않습니다.

</details>

<span id="_10-cert-manager와-aws-acm-certificate-manager-비교-시-cert-manager의-장점은"></span>

### 10. ACM과 cert-manager의 현재 동작에 대한 올바른 설명은?

- A) ACM 인증서는 Pod·온프레미스에서 절대 사용 불가
- B) ALB는 Kubernetes TLS Secret을 직접 읽음
- C) ACM exportable 인증서는 명시적 내보내기로 사용 가능하며 ACM ACME는 별도 lifecycle·제약이 있음
- D) ACM ACME는 server URL만 바꾸면 등록 완료

<details>
<summary>정답 보기</summary>

**정답: C) ACM exportable 인증서는 명시적 내보내기로 사용 가능하며 ACM ACME는 별도 lifecycle·제약이 있음**

ACK ACM export는 options.export:ENABLED, exportTo, 출력 Secret과 별도 도메인 검증이 필요합니다. ACM ACME는 사전 검증 도메인·EAB 등록과 client의 키·갱신 관리가 필요하며 45일 인증서를 직접 ALB/CloudFront/API Gateway 통합에 연결하지 못합니다. cert-manager는 Kubernetes Secret과 여러 Issuer를 조정하지만 controller와 CA 신뢰·비용을 운영해야 합니다.

</details>

## 점수 계산

- 9–10개: 핵심 개념을 잘 이해했습니다.
- 7–8개: 틀린 항목의 발급·신뢰 경로를 다시 확인하세요.
- 6개 이하: 본문과 예제를 함께 복습하세요.

## 관련 문서

- [cert-manager를 활용한 인증서 관리](../../security/10-cert-manager.md)
