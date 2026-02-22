# GitOps 도구 비교 퀴즈

이 퀴즈는 GitOps 도구와 선택 방법에 대한 이해도를 테스트합니다.

1. 어떤 GitOps 도구가 기본으로 내장된 Web UI를 제공하나요?
   - A) FluxCD
   - B) ArgoCD
   - C) 둘 다
   - D) 둘 다 아님

<details>
<summary>정답 보기</summary>

**정답: B) ArgoCD**

**설명:**
ArgoCD는 애플리케이션 관리를 위한 내장된 기능이 풍부한 Web UI를 포함합니다. FluxCD는 CLI 우선이며 내장 UI를 포함하지 않지만, Weave GitOps와 같은 타사 UI를 추가할 수 있습니다.

</details>

2. 배포 소스로서 OCI 아티팩트에 대한 네이티브 지원이 더 좋은 도구는 무엇인가요?
   - A) ArgoCD
   - B) FluxCD
   - C) 둘 다 동등한 지원
   - D) 둘 다 OCI 지원 안 함

<details>
<summary>정답 보기</summary>

**정답: B) FluxCD**

**설명:**
FluxCD는 OCIRepository 소스 유형을 통해 OCI 아티팩트에 대한 일급 지원을 제공하여 OCI 호환 레지스트리에서 저장하고 배포할 수 있습니다. ArgoCD의 OCI 지원은 Helm 차트로 제한됩니다.

</details>

3. 어떤 도구가 내장 이미지 자동화(새 이미지에 대한 자동 Git 업데이트)를 제공하나요?
   - A) ArgoCD (네이티브)
   - B) FluxCD (네이티브)
   - C) 둘 다 네이티브 지원
   - D) 둘 다 네이티브 지원 없음

<details>
<summary>정답 보기</summary>

**정답: B) FluxCD (네이티브)**

**설명:**
FluxCD는 Image Reflector 및 Image Automation 컨트롤러를 통해 내장 이미지 자동화를 제공합니다. ArgoCD는 유사한 기능을 위해 별도의 Argo Image Updater 프로젝트가 필요합니다.

</details>

4. ArgoCD가 더 나은 선택인 사용 사례는 무엇인가요?
   - A) UI 요구 사항 없는 CLI 기반 워크플로우
   - B) 시각적 배포 관리와 SSO 통합이 필요한 팀
   - C) 최소한의 리소스 풋프린트 요구 사항
   - D) OCI 아티팩트 기반 배포

<details>
<summary>정답 보기</summary>

**정답: B) 시각적 배포 관리와 SSO 통합이 필요한 팀**

**설명:**
ArgoCD는 팀이 Web UI를 통한 시각적 피드백, 포괄적인 RBAC, 엔터프라이즈 ID 제공자와의 SSO 통합이 필요한 환경에서 뛰어납니다.

</details>

5. ArgoCD와 FluxCD를 같은 클러스터에서 함께 사용할 수 있나요?
   - A) 아니오, 상호 배타적
   - B) 예, 서로 보완할 수 있음
   - C) 개발 환경에서만
   - D) 특별한 구성에서만

<details>
<summary>정답 보기</summary>

**정답: B) 예, 서로 보완할 수 있음**

**설명:**
ArgoCD와 FluxCD는 함께 사용할 수 있습니다. 일반적인 패턴은 FluxCD를 인프라 관리 및 이미지 자동화에 사용하고 ArgoCD를 UI와 함께 애플리케이션 배포에 사용하는 것입니다.

</details>
