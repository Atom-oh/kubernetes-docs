# ArgoCD 보안 퀴즈

이 퀴즈는 ArgoCD 보안 기능과 모범 사례에 대한 이해도를 테스트합니다.

1. ArgoCD는 기본적으로 Git 리포지토리의 시크릿을 어떻게 처리하나요?
   - A) 자동으로 암호화
   - B) Git의 시크릿을 자동 암호화하지 않음
   - C) Kubernetes Secrets API 사용
   - D) 시크릿 관리자 필요

<details>
<summary>정답 보기</summary>

**정답: B) Git의 시크릿을 자동 암호화하지 않음**

**설명:**
ArgoCD 자체는 시크릿 암호화를 제공하지 않습니다. Sealed Secrets/SOPS는 암호문을 Git에 두는 방식입니다. ESO/Vault 연동은 외부 저장소의 참조를 Git에 두고 값을 가져올 수도 있으며 Git 파일을 자동 암호화하는 기능과 다릅니다. base64도 암호화가 아닙니다.

</details>

2. 컨트롤러의 공개키를 사용해 Kubernetes Secret을 봉인하는 도구는 무엇인가요?
   - A) SOPS
   - B) Sealed Secrets
   - C) Vault
   - D) KMS

<details>
<summary>정답 보기</summary>

**정답: B) Sealed Secrets**

**설명:**
Sealed Secrets는 컨트롤러의 공개/비공개 키로 봉인·복호화합니다. 기본 strict 범위는 이름과 Namespace에도 묶이며, 실제 복호화 신뢰 영역은 보유한 키에 따라 결정됩니다. 암호화된 SealedSecret은 Git에 안전하게 저장할 수 있으며 클러스터의 Sealed Secrets 컨트롤러에 의해 복호화됩니다.

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
Dex는 OpenID Connect(OIDC) 인증을 제공하는 ID 서비스입니다. ArgoCD가 LDAP, SAML, GitHub 등의 제공자를 OIDC로 중계합니다. Argo CD가 direct OIDC를 쓰는 경우 Dex가 항상 필요한 것은 아닙니다.

</details>

4. Application이 관리할 수 있는 네임스페이스 범위 리소스 종류를 어떻게 제한할 수 있나요?
   - A) Kubernetes ResourceQuotas 사용
   - B) AppProject의 namespaceResourceBlacklist 또는 namespaceResourceWhitelist 사용
   - C) Pod의 requests/limits만 변경
   - D) ArgoCD에서는 불가능

<details>
<summary>정답 보기</summary>

**정답: B) AppProject의 namespaceResourceBlacklist 또는 namespaceResourceWhitelist 사용**

**설명:**
AppProjects는 `namespaceResourceBlacklist`(특정 리소스 거부) 또는 `namespaceResourceWhitelist`(특정 리소스만 허용)를 정의하여 Applications가 관리할 수 있는 namespaced 리소스 종류를 제어합니다. 클러스터 범위는 별도 목록을 사용하며 Pod의 privileged 설정을 검사하는 admission 정책과는 다릅니다.

</details>

5. ArgoCD API 서버 노출에 권장되는 방법은 무엇인가요?
   - A) 기본 인증으로 공개 노출
   - B) 보호된 접근 경로와 TLS·인증을 구성
   - C) 인증 없이 실행
   - D) 포트 포워딩을 통해서만 접근

<details>
<summary>정답 보기</summary>

**정답: B) 보호된 접근 경로와 TLS·인증을 구성**

**설명:**
Argo CD API는 TLS와 적절한 인증을 가진 Ingress/Gateway 또는 보호된 내부 경로로 접근합니다. 프런트 TLS 종료만으로 백엔드 TLS까지 검증되는 것은 아닙니다. 민감한 환경에서는 VPN 접근 또는 IP 화이트리스팅과 같은 추가 조치가 권장됩니다.

</details>
