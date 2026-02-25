# Docker Hub 퀴즈
> **마지막 업데이트**: 2026년 2월 25일

1. Docker Hub 무료 플랜에서 익명 사용자의 이미지 풀(pull) 제한은 어떻게 적용되나요?
   - A) 사용자당 시간당 100회
   - B) IP 주소당 6시간당 100회
   - C) 사용자당 하루 1000회
   - D) 제한 없음

<details>
<summary>정답 보기</summary>

**정답: B) IP 주소당 6시간당 100회**

**설명:**
Docker Hub는 익명 사용자에게 IP 주소 기준으로 6시간당 100회의 풀 제한을 적용합니다. 인증된 무료 사용자는 6시간당 200회로 제한이 완화됩니다.

</details>

2. Kubernetes에서 프라이빗 Docker Hub 레포지토리의 이미지를 풀하기 위해 사용하는 리소스는 무엇인가요?
   - A) ConfigMap
   - B) Secret (type: Opaque)
   - C) Secret (type: kubernetes.io/dockerconfigjson)
   - D) ServiceAccount

<details>
<summary>정답 보기</summary>

**정답: C) Secret (type: kubernetes.io/dockerconfigjson)**

**설명:**
프라이빗 레지스트리 인증 정보는 `kubernetes.io/dockerconfigjson` 타입의 Secret으로 저장하고, Pod 스펙의 `imagePullSecrets` 필드에서 참조합니다.

</details>

3. Docker Hub 레이트 리밋을 완화하기 위한 가장 효과적인 방법은 무엇인가요?
   - A) 더 빠른 네트워크 사용
   - B) Pull-through 캐시 프록시 구성
   - C) 이미지 태그를 자주 변경
   - D) 여러 Docker Hub 계정 사용

<details>
<summary>정답 보기</summary>

**정답: B) Pull-through 캐시 프록시 구성**

**설명:**
Pull-through 캐시(예: Harbor의 프록시 캐시, Amazon ECR의 풀스루 캐시)를 사용하면 Docker Hub에서 이미지를 한 번만 풀하고 이후에는 로컬 캐시에서 제공하므로 레이트 리밋 영향을 크게 줄일 수 있습니다.

</details>

4. Docker Hub의 Automated Builds 기능에 대한 설명으로 올바른 것은?
   - A) 모든 무료 플랜 사용자가 사용 가능하다
   - B) GitHub/GitLab 연동으로 코드 푸시 시 자동으로 이미지를 빌드한다
   - C) 빌드된 이미지는 자동으로 서명된다
   - D) 오직 공개 레포지토리에서만 작동한다

<details>
<summary>정답 보기</summary>

**정답: B) GitHub/GitLab 연동으로 코드 푸시 시 자동으로 이미지를 빌드한다**

**설명:**
Docker Hub의 Automated Builds는 GitHub 또는 GitLab 레포지토리와 연동하여 소스 코드 변경 시 자동으로 Docker 이미지를 빌드하고 푸시합니다. 이 기능은 유료 플랜에서 제공됩니다.

</details>

5. Docker Hub에서 "Official Images"의 특징으로 올바르지 않은 것은?
   - A) Docker Inc.에서 관리하고 검토한다
   - B) 보안 취약점에 대해 정기적으로 스캔된다
   - C) 사용자가 직접 Official Image를 등록할 수 있다
   - D) Best practices를 따르는 Dockerfile을 사용한다

<details>
<summary>정답 보기</summary>

**정답: C) 사용자가 직접 Official Image를 등록할 수 있다**

**설명:**
Official Images는 Docker Inc.가 관리하는 큐레이션된 이미지 세트로, 엄격한 검토 과정을 거칩니다. 일반 사용자가 직접 Official Image를 등록할 수 없으며, Docker 공식 팀의 승인이 필요합니다.

</details>

6. Docker Hub의 "Verified Publisher" 배지가 의미하는 것은?
   - A) 이미지가 취약점이 없음을 보장한다
   - B) Docker Inc.가 퍼블리셔의 신원과 콘텐츠를 검증했다
   - C) 이미지가 무료로 사용 가능하다
   - D) 이미지가 자동으로 업데이트된다

<details>
<summary>정답 보기</summary>

**정답: B) Docker Inc.가 퍼블리셔의 신원과 콘텐츠를 검증했다**

**설명:**
Verified Publisher 배지는 Docker Inc.가 해당 조직의 신원을 확인하고 콘텐츠의 품질과 보안 표준을 검토했음을 나타냅니다. 이는 신뢰할 수 있는 소스에서 이미지를 가져오고 있음을 의미합니다.

</details>

7. imagePullSecrets를 모든 Pod에 자동으로 적용하려면 어떻게 해야 하나요?
   - A) 클러스터 전역 설정에서 구성
   - B) ServiceAccount에 imagePullSecrets를 추가
   - C) ConfigMap에 설정
   - D) kube-system 네임스페이스에만 Secret 생성

<details>
<summary>정답 보기</summary>

**정답: B) ServiceAccount에 imagePullSecrets를 추가**

**설명:**
ServiceAccount에 `imagePullSecrets` 필드를 추가하면, 해당 ServiceAccount를 사용하는 모든 Pod에 자동으로 imagePullSecrets가 적용됩니다. 네임스페이스의 default ServiceAccount에 추가하면 해당 네임스페이스의 모든 Pod에 적용됩니다.

</details>

8. 공개 Docker Hub 이미지 사용 시 공급망 보안을 위한 권장 사항이 아닌 것은?
   - A) 이미지 다이제스트(SHA256)로 고정하여 사용
   - B) 신뢰할 수 있는 베이스 이미지 사용
   - C) 항상 :latest 태그 사용으로 최신 보안 패치 적용
   - D) 이미지 서명 검증 (Docker Content Trust)

<details>
<summary>정답 보기</summary>

**정답: C) 항상 :latest 태그 사용으로 최신 보안 패치 적용**

**설명:**
:latest 태그는 변경될 수 있어 빌드 재현성이 떨어지고, 예기치 않은 변경이 배포될 수 있습니다. 보안을 위해 이미지 다이제스트나 특정 버전 태그를 사용하고, 업데이트는 테스트 후 명시적으로 진행해야 합니다.

</details>

9. Docker Hub Pro 플랜과 Team 플랜의 차이점은?
   - A) Pro는 개인용, Team은 조직용으로 협업 기능 제공
   - B) Pro는 무제한 프라이빗 레포지토리, Team은 제한됨
   - C) Pro만 Automated Builds를 지원
   - D) Team은 레이트 리밋이 없음

<details>
<summary>정답 보기</summary>

**정답: A) Pro는 개인용, Team은 조직용으로 협업 기능 제공**

**설명:**
Docker Hub Pro는 개인 개발자를 위한 플랜이며, Team 플랜은 조직을 위한 것으로 역할 기반 접근 제어, 감사 로그, 조직 관리 기능 등 협업에 필요한 기능을 제공합니다.

</details>

10. Kubernetes 클러스터에서 Docker Hub 레이트 리밋 오류가 발생할 때 나타나는 HTTP 상태 코드는?
    - A) 401 Unauthorized
    - B) 403 Forbidden
    - C) 429 Too Many Requests
    - D) 503 Service Unavailable

<details>
<summary>정답 보기</summary>

**정답: C) 429 Too Many Requests**

**설명:**
Docker Hub 레이트 리밋에 도달하면 HTTP 429 (Too Many Requests) 오류가 반환됩니다. Kubernetes에서는 이미지 풀 실패로 나타나며, `kubectl describe pod` 명령으로 "toomanyrequests" 관련 오류 메시지를 확인할 수 있습니다.

</details>
