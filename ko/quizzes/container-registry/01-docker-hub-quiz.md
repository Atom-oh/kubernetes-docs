# Docker Hub 퀴즈
> **마지막 업데이트**: 2026년 9월 11일

1. 공용 NAT 뒤의 노드가 Docker Hub에 익명으로 접근할 때 pull 제한의 집계 기준은 무엇인가요?
   - A) 각 Pod별
   - B) 송신 IPv4 주소 또는 IPv6 /64 대역
   - C) Kubernetes namespace별
   - D) 제한 없음

<details>
<summary>정답 보기</summary>

**정답: B) 송신 IPv4 주소 또는 IPv6 /64 대역**

**설명:**
익명 요청은 송신 IPv4 주소 또는 IPv6 /64 기준으로 집계되므로 NAT를 공유하는 노드가 같은 버킷을 사용할 수 있습니다. 구체적인 횟수와 시간 창은 현재 공식 정책과 rate-limit 응답 헤더에서 확인합니다.

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
Pull-through 캐시는 캐시된 레이어의 반복 다운로드를 줄입니다. 캐시 미스, 태그 갱신과 재검증은 여전히 upstream 요청을 발생시키므로 제한을 완전히 없애는 것은 아닙니다.

</details>

4. 2026년 9월 기준 Docker Hub Automated Builds의 운영 방침으로 올바른 것은?
   - A) 모든 무료 플랜 사용자가 사용 가능하다
   - B) 폐기 예정 기능이므로 2027-04-01 종료 전에 외부 CI/CD로 이전한다
   - C) 빌드된 이미지는 자동으로 서명된다
   - D) 오직 공개 레포지토리에서만 작동한다

<details>
<summary>정답 보기</summary>

**정답: B) 폐기 예정 기능이므로 2027-04-01 종료 전에 외부 CI/CD로 이전한다**

**설명:**
공식 안내는 Automated Builds를 deprecated로 표시하고 2027-04-01 종료를 공지합니다. 기존 네이티브 연동은 GitHub/Bitbucket이며 GitLab은 GitLab CI에서 빌드 후 push하는 방식으로 구성합니다.

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
Official Images는 Docker와 upstream/community 관리자가 큐레이션하는 이미지입니다. 기여자가 등록을 제안할 수는 있지만 검토 없이 스스로 공식 배지를 붙일 수는 없습니다. 공식 배지도 개별 태그의 취약점 부재를 보장하지 않습니다.

</details>

6. Docker Hub의 "Verified Publisher" 배지가 의미하는 것은?
   - A) 이미지가 취약점이 없음을 보장한다
   - B) 게시자 검증 프로그램을 통과한 조직임을 나타낸다
   - C) 이미지가 무료로 사용 가능하다
   - D) 이미지가 자동으로 업데이트된다

<details>
<summary>정답 보기</summary>

**정답: B) 게시자 검증 프로그램을 통과한 조직임을 나타낸다**

**설명:**
게시자 신원을 확인하는 신호이며 각 이미지가 취약점이 없거나 서명됐다는 보장은 아닙니다. 선택한 태그/digest의 유지보수 상태, 스캔 및 서명을 별도로 확인합니다.

</details>

7. 특정 ServiceAccount를 사용하는 새 Pod가 기본 pull 자격 증명을 받게 하려면 어떻게 해야 하나요?
   - A) 클러스터 전역 설정에서 구성
   - B) ServiceAccount에 imagePullSecrets를 추가
   - C) ConfigMap에 설정
   - D) kube-system 네임스페이스에만 Secret 생성

<details>
<summary>정답 보기</summary>

**정답: B) ServiceAccount에 imagePullSecrets를 추가**

**설명:**
같은 namespace의 ServiceAccount에 `imagePullSecrets`를 설정하면, 이를 사용하는 새 Pod 중 자체 pull-secret 목록이 없는 Pod가 해당 목록을 받습니다. 기존 Pod, 다른 ServiceAccount, 다른 namespace에는 소급 적용되지 않습니다.

</details>

8. 공개 Docker Hub 이미지 사용 시 공급망 보안을 위한 권장 사항이 아닌 것은?
   - A) 이미지 다이제스트(SHA256)로 고정하여 사용
   - B) 신뢰할 수 있는 베이스 이미지 사용
   - C) 항상 :latest 태그 사용으로 최신 보안 패치 적용
   - D) 신뢰할 서명자를 지정한 런타임·admission 검증

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
   - D) Team만 pull이 무제한이고 Pro는 항상 제한됨

<details>
<summary>정답 보기</summary>

**정답: A) Pro는 개인용, Team은 조직용으로 협업 기능 제공**

**설명:**
Pro는 개인 개발자용이고 Team은 조직 협업을 위한 플랜입니다. 구체적인 권한·감사·SSO 제공 범위는 현재 플랜 표를 확인하며, pull 제한만으로 두 플랜을 구분하지 않습니다.

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
