# 다층 방어와 침해 대응 퀴즈

> **마지막 업데이트**: 2026년 10월 15일

[본문과 공식 출처 보기](../../security/13-defense-in-depth-incident-response.md)

### 1. CVE-2025-1974에서 공개 WAF 외에 검토할 경로는 무엇인가?

- A) Pod 네트워크에서 도달하는 admission webhook
- B) CloudFront viewer 경로만
- C) DB 저장 암호화만
- D) DNS cache 크기만

<details>
<summary>정답 보기</summary>

**정답: A) Pod 네트워크에서 도달하는 admission webhook**

**설명:** webhook 도달성과 controller의 Secret 권한을 확인합니다. 당시 수정 버전과 이후 ingress-nginx 유지보수 종료도 구분합니다.

</details>

### 2. 2026년 신규 설계에서 ingress-nginx 유지보수 종료의 의미는?

- A) 과거 CVE 수정만 영구적으로 충분하다
- B) 유지보수되는 구현으로 이전을 계획한다
- C) WAF가 controller 패치를 보장한다
- D) 모든 Kubernetes webhook을 끈다

<details>
<summary>정답 보기</summary>

**정답: B) 유지보수되는 구현으로 이전을 계획한다**

**설명:** 종료 후 ingress-nginx의 보안 릴리스가 중단되므로 과거 패치 외에 유지보수·이전 계획이 필요합니다.

</details>

### 3. PAN-OS CVE-2026-0322의 영향 범위를 올바르게 설명한 것은?

- A) 모든 Palo Alto 제품이 예외 없이 영향
- B) 인증 없는 인터넷 사용자만 영향
- C) 명시한 제품군 관리면의 인증된 사용자 RCE
- D) WAF body 크기 문제

<details>
<summary>정답 보기</summary>

**정답: C) 명시한 제품군 관리면의 인증된 사용자 RCE**

**설명:** 해당 경보는 PA-Series·VM-Series·Panorama를 포함하고 Cloud NGFW·Prisma Access를 제외합니다. 자격 증명과 관리 경로를 함께 보호합니다.

</details>

### 4. Fortinet의 1월 28일 범위 정정을 어떻게 반영해야 하는가?

- A) 모든 SAML IdP가 영향받는다
- B) 어떤 Fortinet 제품도 영향받지 않는다
- C) 모든 SSO 취약점의 범위는 같다
- D) 명시한 문제에서 제3자 SAML IdP·FortiAuthenticator는 제외된다

<details>
<summary>정답 보기</summary>

**정답: D) 명시한 문제에서 제3자 SAML IdP·FortiAuthenticator는 제외된다**

**설명:** 초기 SAML 범위 문장 대신 수정된 범위를 사용합니다. FortiCloud SSO의 영향 여부는 별도로 확인합니다.

</details>

### 5. 일부 흐름을 중앙 TGW 검사로 라우팅했을 때 그 설정의 검사 범위는?

- A) 모든 같은 노드 Pod 통신
- B) 모든 PrivateLink 연결
- C) 모든 별도 peering 경로
- D) 실제 해당 검사 경로로 라우팅한 흐름

<details>
<summary>정답 보기</summary>

**정답: D) 실제 해당 검사 경로로 라우팅한 흐름**

**설명:** local·endpoint·peering·IPv6를 별도로 확인하고 CNI·IAM·SG·앱 통제를 연결합니다.

</details>

### 6. 패치 완료와 침해 제거 완료를 구분하는 증거는?

- A) reboot 시각만
- B) 무단 계정·설정·잔존 접근·노출 비밀 조사
- C) target healthy 상태만
- D) 새 버전 문자열만

<details>
<summary>정답 보기</summary>

**정답: B) 무단 계정·설정·잔존 접근·노출 비밀 조사**

**설명:** 패치 후 접근이 남을 수 있습니다. 제조사 절차에 따라 설정·계정·관련 자격 증명을 조사하고 복구합니다.

</details>

### 7. WAF 차단 건수 0만으로 무엇을 입증할 수 있는가?

- A) 모든 요청이 안전하다
- B) 모든 경로가 검사됐다
- C) 완전한 안전이나 경로 적용을 단독 입증하지 못한다
- D) 관리자 자격 증명이 유출되지 않았다

<details>
<summary>정답 보기</summary>

**정답: C) 완전한 안전이나 경로 적용을 단독 입증하지 못한다**

**설명:** 연결·action·canary·origin 경계·앱 로그를 연관합니다. 검사 누락 때문에 차단이 없을 수도 있습니다.

</details>

### 8. 복구 수용 기준으로 가장 적절한 증거는?

- A) 버전만
- B) 장비 화면 캡처만
- C) 로그인 한 번 성공
- D) 정상 설정·자격 증명과 업무·거부 경로·로그 재검증

<details>
<summary>정답 보기</summary>

**정답: D) 정상 설정·자격 증명과 업무·거부 경로·로그 재검증**

**설명:** 침해 제거 근거와 정상 기능·관리 접근 제한·검사·관측 복구를 함께 확인합니다.

</details>
