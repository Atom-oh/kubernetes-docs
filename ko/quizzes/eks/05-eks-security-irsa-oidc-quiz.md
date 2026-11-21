# IRSA와 OIDC Provider 퀴즈

> **마지막 업데이트**: 2026년 11월 21일

이 퀴즈는 [IRSA와 OIDC Provider](../../eks/05-eks-security-irsa-oidc.md)의 내용을 확인합니다.

## 퀴즈 개요
- 클러스터 OIDC issuer와 IAM OIDC provider
- IRSA 토큰 교환
- 역할 신뢰 조건
- Discovery·JWKS와 키 교체

## 객관식 문제

### 1. EKS 클러스터가 OIDC issuer와 공개 서명 키를 게시하고 있을 때, IRSA로 역할을 맡으려면 추가로 무엇이 필요한가요?

- A) 추가 구성은 필요 없고 issuer endpoint만으로 역할 전환이 허용된다
- B) Kubernetes 사용자 로그인을 위한 외부 OIDC identity provider 연결
- C) 역할 계정의 IAM OIDC provider, 신뢰 조건을 갖춘 역할, 호환 SDK
- D) 노드 IAM 역할에 워크로드가 사용할 대상 S3 권한 추가

<details>
<summary>정답 보기</summary>

**정답: C) 역할 계정의 IAM OIDC provider, 신뢰 조건을 갖춘 역할, 호환 SDK**

**설명:**

EKS가 게시하는 클러스터 OIDC issuer endpoint만으로 IAM OIDC provider가 생성되거나 역할 전환이 허용되지는 않습니다. IRSA에는 역할 계정의 대상 IAM OIDC provider, 올바른 issuer/subject/audience 신뢰 조건과 호환 SDK가 필요합니다. Kubernetes 사용자 로그인용 외부 OIDC provider는 IRSA와 별개입니다.

</details>

### 2. IRSA에서 SDK가 projected web-identity token을 임시 AWS 자격 증명으로 교환할 때 호출하는 API는 무엇인가요?

- A) EKS Auth AssumeRoleForPodIdentity
- B) STS AssumeRoleWithWebIdentity
- C) IMDSv2 인스턴스 프로파일 자격 증명
- D) STS GetSessionToken

<details>
<summary>정답 보기</summary>

**정답: B) STS AssumeRoleWithWebIdentity**

**설명:**

IRSA webhook은 대상 Pod에 projected token과 role 설정을 추가하고, SDK는 AssumeRoleWithWebIdentity로 token을 STS와 교환합니다. STS가 issuer·서명·토큰·역할 신뢰를 검증하면 임시 자격 증명을 반환합니다. AssumeRoleForPodIdentity는 Pod Identity agent가 EKS Auth에 호출하는 API입니다. Kubernetes의 projected token 갱신과 SDK의 AWS 자격 증명 갱신은 수명이 다릅니다.

</details>

### 3. 범위를 제한한 IRSA 역할 신뢰 예제에서 `security-demo/irsa-reader` ServiceAccount만 역할을 맡도록 제한하는 조건은 무엇인가요?

- A) `aws:RequestTag/kubernetes-service-account` 세션 태그 조건
- B) `Principal.Service`를 `pods.eks.amazonaws.com`으로 지정
- C) ServiceAccount 이름과 같은 이름으로 IAM 역할 생성
- D) `<issuer>:sub`와 `<issuer>:aud`를 제한하는 StringEquals 조건

<details>
<summary>정답 보기</summary>

**정답: D) `<issuer>:sub`와 `<issuer>:aud`를 제한하는 StringEquals 조건**

**설명:**

IRSA 역할은 IAM OIDC provider를 `Federated` principal로 두고 `sts:AssumeRoleWithWebIdentity`를 허용합니다. 전체 issuer hostname/path를 접두사로 한 `:sub`를 `system:serviceaccount:security-demo:irsa-reader`로, `:aud`를 `sts.amazonaws.com`으로 제한하는 StringEquals 조건이 ServiceAccount와 audience를 묶습니다. `aws:RequestTag/...` 조건과 `pods.eks.amazonaws.com`은 Pod Identity 신뢰 방식입니다. 역할은 명시적으로 허용한 여러 ServiceAccount·issuer를 신뢰할 수 있으며 IRSA가 ServiceAccount당 역할 하나를 강제하지는 않습니다.

</details>

### 4. 클러스터 OIDC discovery·JWKS를 직접 조회해 토큰을 검증하는 validator를 만들 때 옳은 설명은 무엇인가요?

- A) Cache-Control에 따라 키를 캐시하고 키 교체와 알 수 없는 kid를 처리한다
- B) JWKS를 한 번 받아 validator 설정에 하드코딩하고 계속 재사용한다
- C) JWKS 조회에 성공하면 워크로드 토큰 서명도 함께 검증된 것으로 본다
- D) Discovery 문서의 issuer 값은 클러스터 issuer와 비교하지 않아도 된다

<details>
<summary>정답 보기</summary>

**정답: A) Cache-Control에 따라 키를 캐시하고 키 교체와 알 수 없는 kid를 처리한다**

**설명:**

문서의 진단 스크립트는 공개 discovery/JWKS를 조회하고 discovery issuer와 HTTPS scheme을 확인할 뿐 워크로드 토큰 서명이나 IAM 권한을 검증하지 않습니다. 자동 validator는 Cache-Control에 따라 키를 캐시하고 검토한 JWT 라이브러리로 서명 키 교체와 알 수 없는 kid를 처리해야 합니다. EKS OIDC 서명 키는 7일마다 교체됩니다.

</details>

### 5. 인터넷 egress가 없는 환경의 validator가 클러스터 OIDC discovery/JWKS에 접근하는 방법으로 옳은 것은 무엇인가요?

- A) EKS 관리 API interface endpoint를 만들면 OIDC discovery도 함께 제공
- B) 보안 그룹에 0.0.0.0/0 egress를 열어 필요할 때만 임시로 조회
- C) `oidc-eks` PrivateLink interface endpoint를 사용한다
- D) IRSA에는 JWKS가 필요 없으므로 별도 경로를 준비하지 않음

<details>
<summary>정답 보기</summary>

**정답: C) `oidc-eks` PrivateLink interface endpoint를 사용한다**

**설명:**

현재 EKS는 인터넷 egress가 없는 validator용 클러스터 OIDC discovery/JWKS PrivateLink interface endpoint인 `com.amazonaws.region-code.oidc-eks`를 지원합니다. 해당 endpoint의 리전·DNS 조건을 확인해야 하며, EKS 관리 API endpoint와는 다른 서비스입니다.

</details>
