# ArgoCD 보안 퀴즈

이 퀴즈는 ArgoCD 보안 기능과 모범 사례에 대한 이해도를 테스트합니다.

1. ArgoCD는 기본적으로 Git 리포지토리의 시크릿을 어떻게 처리하나요?
   - A) 자동으로 암호화
   - B) 시크릿을 특별히 처리하지 않음 - 일반 텍스트로 저장
   - C) Kubernetes Secrets API 사용
   - D) 시크릿 관리자 필요

<details>
<summary>정답 보기</summary>

**정답: B) 시크릿을 특별히 처리하지 않음 - 일반 텍스트로 저장**

**설명:**
ArgoCD 자체는 시크릿 암호화를 제공하지 않습니다. Git의 시크릿은 Git에 커밋하기 전에 Sealed Secrets, SOPS, External Secrets Operator 또는 Vault와 같은 도구를 사용하여 암호화해야 합니다.

</details>

2. 클러스터별 키를 사용하여 Kubernetes Secrets를 암호화하는 도구는 무엇인가요?
   - A) SOPS
   - B) Sealed Secrets
   - C) Vault
   - D) KMS

<details>
<summary>정답 보기</summary>

**정답: B) Sealed Secrets**

**설명:**
Sealed Secrets는 클러스터별 키 쌍을 사용하여 시크릿을 암호화합니다. 암호화된 SealedSecret은 Git에 안전하게 저장할 수 있으며 클러스터의 Sealed Secrets 컨트롤러에 의해 복호화됩니다.

</details>

3. ArgoCD의 Dex 컴포넌트의 목적은 무엇인가요?
   - A) 컨테이너 이미지 스캔
   - B) OpenID Connect 인증 및 SSO
   - C) 네트워크 정책 적용
   - D) 시크릿 로테이션

<details>
<summary>정답 보기</summary>

**정답: B) OpenID Connect 인증 및 SSO**

**설명:**
Dex는 OpenID Connect(OIDC) 인증을 제공하는 ID 서비스입니다. ArgoCD가 싱글 사인온을 위해 다양한 ID 제공자(LDAP, SAML, GitHub 등)와 통합할 수 있게 합니다.

</details>

4. Application이 생성할 수 있는 Kubernetes 리소스를 어떻게 제한할 수 있나요?
   - A) Kubernetes ResourceQuotas 사용
   - B) AppProject의 namespaceResourceBlacklist 또는 namespaceResourceWhitelist 사용
   - C) Pod Security Policies 사용
   - D) ArgoCD에서는 불가능

<details>
<summary>정답 보기</summary>

**정답: B) AppProject의 namespaceResourceBlacklist 또는 namespaceResourceWhitelist 사용**

**설명:**
AppProjects는 `namespaceResourceBlacklist`(특정 리소스 거부) 또는 `namespaceResourceWhitelist`(특정 리소스만 허용)를 정의하여 Applications가 관리할 수 있는 Kubernetes 리소스 유형을 제어할 수 있습니다.

</details>

5. ArgoCD API 서버 노출에 권장되는 방법은 무엇인가요?
   - A) 기본 인증으로 공개 노출
   - B) 내부에 유지하고 TLS 및 인증이 있는 ingress 사용
   - C) 인증 없이 실행
   - D) 포트 포워딩을 통해서만 접근

<details>
<summary>정답 보기</summary>

**정답: B) 내부에 유지하고 TLS 및 인증이 있는 ingress 사용**

**설명:**
ArgoCD API 서버는 TLS 종료와 적절한 인증(SSO/OIDC)이 있는 ingress를 통해 노출해야 합니다. 민감한 환경에서는 VPN 접근 또는 IP 화이트리스팅과 같은 추가 조치가 권장됩니다.

</details>
