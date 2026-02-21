# CI 파이프라인 구성 퀴즈

> **관련 문서**: [CI 파이프라인 구성](../../ops/03-ci-pipelines.md)

## 객관식 문제

### 1. GitLab Runner on EKS 설정에서 runner executor를 kubernetes로 설정하는 주요 이점은 무엇인가요?

- A) GitLab 서버와의 통신 속도 향상
- B) 각 CI 작업이 독립적인 Pod에서 실행되어 격리성 확보
- C) 로컬 캐시 사용 가능
- D) 멀티 클라우드 지원

<details>
<summary>정답 보기</summary>

**정답: B) 각 CI 작업이 독립적인 Pod에서 실행되어 격리성 확보**

**설명:**
Kubernetes executor를 사용하면 각 CI 작업이 별도의 Pod에서 실행되어 작업 간 격리성이 보장됩니다. 작업 완료 후 Pod가 삭제되므로 깨끗한 환경이 유지되고, 리소스 사용량에 따라 자동 스케일링도 가능합니다.

</details>

### 2. ECR Lifecycle Policy에서 imageCountMoreThan 규칙의 역할은 무엇인가요?

- A) 이미지 빌드 횟수 제한
- B) 지정된 개수 이상의 오래된 이미지 자동 삭제
- C) 이미지 푸시 권한 제한
- D) 이미지 태그 개수 제한

<details>
<summary>정답 보기</summary>

**정답: B) 지정된 개수 이상의 오래된 이미지 자동 삭제**

**설명:**
ECR Lifecycle Policy의 imageCountMoreThan 규칙은 저장소에 지정된 개수 이상의 이미지가 있을 때 가장 오래된 이미지부터 자동으로 삭제합니다. 예를 들어 countNumber가 30이면 31번째 이미지부터 삭제됩니다. 이를 통해 스토리지 비용을 관리할 수 있습니다.

</details>

### 3. GitHub Actions Runner Controller (ARC)에서 RunnerDeployment 리소스의 역할은 무엇인가요?

- A) GitHub 저장소 생성
- B) Self-hosted Runner Pod의 배포 및 스케일링 관리
- C) GitHub Actions 워크플로우 정의
- D) 빌드 아티팩트 저장

<details>
<summary>정답 보기</summary>

**정답: B) Self-hosted Runner Pod의 배포 및 스케일링 관리**

**설명:**
RunnerDeployment는 GitHub Actions Self-hosted Runner Pod를 Kubernetes 클러스터에 배포하고 관리합니다. replicas로 동시 실행 가능한 Runner 수를 지정하고, HorizontalRunnerAutoscaler와 연동하여 워크플로우 수요에 따라 자동 스케일링할 수 있습니다.

</details>

### 4. Docker 멀티 플랫폼 빌드에서 buildx와 QEMU를 함께 사용하는 이유는 무엇인가요?

- A) 빌드 속도 향상
- B) 다른 CPU 아키텍처(ARM, AMD64)용 이미지를 단일 머신에서 빌드
- C) 이미지 크기 최적화
- D) 빌드 캐시 공유

<details>
<summary>정답 보기</summary>

**정답: B) 다른 CPU 아키텍처(ARM, AMD64)용 이미지를 단일 머신에서 빌드**

**설명:**
buildx는 Docker의 멀티 플랫폼 빌드 도구이고, QEMU는 CPU 에뮬레이터입니다. AMD64 머신에서 ARM64 이미지를 빌드하거나 그 반대의 경우, QEMU가 다른 아키텍처를 에뮬레이션하여 크로스 컴파일을 가능하게 합니다.

</details>

### 5. GitLab CI에서 ECR에 이미지를 푸시하기 전에 필요한 인증 단계는 무엇인가요?

- A) docker login만 실행
- B) aws ecr get-login-password로 토큰 획득 후 docker login
- C) kubectl 인증
- D) GitLab 토큰만 사용

<details>
<summary>정답 보기</summary>

**정답: B) aws ecr get-login-password로 토큰 획득 후 docker login**

**설명:**
ECR에 이미지를 푸시하려면 먼저 `aws ecr get-login-password` 명령으로 임시 인증 토큰을 획득하고, 이를 `docker login` 명령에 전달해야 합니다. 이 토큰은 12시간 동안 유효하며, CI/CD 파이프라인에서는 매 실행마다 새로 획득하는 것이 좋습니다.

</details>

### 6. BuildKit 캐시에서 --cache-to와 --cache-from 옵션의 역할은 무엇인가요?

- A) 로컬 파일 시스템에만 캐시 저장
- B) 빌드 레이어 캐시를 원격 저장소에 저장하고 재사용
- C) 이미지 압축 설정
- D) 빌드 로그 저장

<details>
<summary>정답 보기</summary>

**정답: B) 빌드 레이어 캐시를 원격 저장소에 저장하고 재사용**

**설명:**
BuildKit의 --cache-to는 빌드 레이어 캐시를 ECR 같은 원격 저장소에 저장하고, --cache-from은 저장된 캐시를 다음 빌드에서 재사용합니다. 이를 통해 CI/CD 환경에서도 캐시를 유지하여 빌드 시간을 크게 단축할 수 있습니다.

</details>

### 7. Kaniko가 Docker 대신 CI 환경에서 선호되는 이유는 무엇인가요?

- A) 빌드 속도가 더 빠름
- B) Docker daemon 없이 컨테이너 이미지 빌드 가능 (rootless)
- C) 더 작은 이미지 생성
- D) 더 많은 베이스 이미지 지원

<details>
<summary>정답 보기</summary>

**정답: B) Docker daemon 없이 컨테이너 이미지 빌드 가능 (rootless)**

**설명:**
Kaniko는 Docker daemon 없이 Dockerfile을 빌드하고 이미지를 생성할 수 있습니다. 이는 Kubernetes 환경에서 특권(privileged) 컨테이너 없이 안전하게 빌드할 수 있음을 의미합니다. 보안 요구사항이 엄격한 환경에서 특히 유용합니다.

</details>

### 8. GitLab Runner의 config.toml에서 poll_interval 설정의 역할은 무엇인가요?

- A) 이미지 빌드 간격
- B) Runner가 GitLab 서버에서 새 작업을 확인하는 주기
- C) Pod 재시작 간격
- D) 로그 수집 간격

<details>
<summary>정답 보기</summary>

**정답: B) Runner가 GitLab 서버에서 새 작업을 확인하는 주기**

**설명:**
poll_interval(또는 check_interval)은 GitLab Runner가 GitLab 서버에 새로운 CI 작업이 있는지 확인하는 주기를 초 단위로 설정합니다. 값이 작을수록 작업이 더 빨리 시작되지만 서버 부하가 증가합니다.

</details>

### 9. GitHub ARC에서 HorizontalRunnerAutoscaler의 scaleDownDelaySecondsAfterScaleOut 설정의 역할은 무엇인가요?

- A) Runner Pod 시작 지연 시간
- B) 스케일 아웃 후 스케일 다운까지의 대기 시간 (떨림 방지)
- C) 워크플로우 실행 시간 제한
- D) GitHub API 호출 간격

<details>
<summary>정답 보기</summary>

**정답: B) 스케일 아웃 후 스케일 다운까지의 대기 시간 (떨림 방지)**

**설명:**
scaleDownDelaySecondsAfterScaleOut은 Runner가 스케일 아웃된 후 최소한 지정된 시간 동안은 스케일 다운되지 않도록 합니다. 이를 통해 연속적인 워크플로우 실행 시 Runner가 불필요하게 생성/삭제되는 "떨림(thrashing)"을 방지합니다.

</details>

### 10. CI 파이프라인에서 이미지 태그로 Git commit SHA를 사용하는 이점이 아닌 것은 무엇인가요?

- A) 어떤 코드 버전으로 빌드되었는지 추적 가능
- B) 이미지 불변성 보장
- C) 캐시 효율성 최대화
- D) 롤백 시 정확한 버전 식별 가능

<details>
<summary>정답 보기</summary>

**정답: C) 캐시 효율성 최대화**

**설명:**
Git commit SHA를 태그로 사용하면 모든 커밋마다 새로운 태그가 생성되어 오히려 캐시 효율성이 떨어질 수 있습니다. 하지만 정확한 코드 버전 추적, 이미지 불변성 보장, 롤백 시 정확한 버전 식별이 가능하다는 장점이 있어 프로덕션 환경에서 권장됩니다.

</details>
