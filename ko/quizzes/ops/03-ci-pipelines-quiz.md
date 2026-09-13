# CI 파이프라인 구성 퀴즈

> **관련 문서**: [CI 파이프라인 구성](../../ops/03-ci-pipelines.md)

## 객관식 문제

### 1. 릴리스 이미지와 BuildKit 캐시를 다른 ECR 리포지터리에 두는 이유는 무엇인가요?

- A) 캐시 이미지는 IAM 인증이 필요 없기 때문에
- B) 불변 릴리스 태그와 계속 갱신하는 캐시 태그의 정책을 분리하기 위해
- C) ECR은 하나의 태그만 지원하기 때문에
- D) 캐시를 쓰면 보안 검사가 필요 없기 때문에

<details>
<summary>정답 보기</summary>

**정답: B) 불변 릴리스 태그와 계속 갱신하는 캐시 태그의 정책을 분리하기 위해**

**설명:** 예제는 application 리포지터리를 IMMUTABLE, build-cache를 MUTABLE로 구성합니다. commit SHA를 태그에 넣는 것만으로 덮어쓰기를 막지는 못하며, 배포에는 검증한 digest를 사용합니다.

</details>

### 2. GitLab Kubernetes executor가 작업별 Pod를 만들 때 올바른 설명은 무엇인가요?

- A) privileged 작업도 완전히 격리된다
- B) 모든 노드 접근 위험이 사라진다
- C) 작업 수명과 자원을 분리하지만 Pod만으로 완전한 보안 경계를 보장하지 않는다
- D) 비신뢰 PR에 AWS 게시 역할을 주어도 안전하다

<details>
<summary>정답 보기</summary>

**정답: C) 작업 수명과 자원을 분리하지만 Pod만으로 완전한 보안 경계를 보장하지 않는다**

**설명:** 이 가이드의 DinD는 privileged이며 신뢰하는 보호된 작업용입니다. 별도 Pod, 전용 CI 노드, 최소 권한은 서로 다른 통제이며 어느 하나만으로 비신뢰 코드를 안전하게 실행한다고 단정하지 않습니다.

</details>

### 3. GitLab Runner의 poll_interval과 check_interval은 어떻게 다른가요?

- A) poll_interval은 Kubernetes Pod 상태 확인, check_interval은 coordinator 작업 확인에 관계한다
- B) 두 이름은 같은 설정의 별칭이다
- C) 둘 다 Docker 이미지 캐시 만료 시간이다
- D) poll_interval이 Pod를 재시작한다

<details>
<summary>정답 보기</summary>

**정답: A) poll_interval은 Kubernetes Pod 상태 확인, check_interval은 coordinator 작업 확인에 관계한다**

**설명:** Kubernetes executor의 poll_interval은 작업 Pod가 준비되는지 확인하는 주기입니다. Runner 전역의 check_interval을 동일한 설정으로 설명하면 문제의 원인과 조정 대상이 달라집니다.

</details>

### 4. GitLab 예제에서 manager와 build Pod의 AWS 역할을 분리한 이유는 무엇인가요?

- A) manager에 모든 AWS 권한을 주기 위해
- B) Pod Identity association이 ServiceAccount도 자동 생성하기 때문에
- C) build Pod가 장기 액세스 키를 저장해야 하기 때문에
- D) manager의 S3 캐시 접근과 build Pod의 ECR 게시 접근을 각각 필요한 범위로 제한하기 위해

<details>
<summary>정답 보기</summary>

**정답: D) manager의 S3 캐시 접근과 build Pod의 ECR 게시 접근을 각각 필요한 범위로 제한하기 위해**

**설명:** 예제의 S3 캐시는 RoleARN 없이 manager 자격 증명 체인을 사용합니다. build Pod에는 별도 ECR 역할을 연결합니다. ServiceAccount는 따로 만들며 Pod Identity의 AWS용 토큰은 일반 Kubernetes API 토큰과 다릅니다.

</details>

### 5. 현재 ARC runner scale set 예제의 작업 배정 방식은 무엇인가요?

- A) RunnerDeployment와 HorizontalRunnerAutoscaler만 설치한다
- B) 공식 scale-set 차트와 listener를 사용하고 runs-on을 실제 scale-set 이름에 맞춘다
- C) 조직 runner group 이름이 언제나 작업 label이 된다
- D) minRunners=0이면 클러스터의 모든 비용이 0이 된다

<details>
<summary>정답 보기</summary>

**정답: B) 공식 scale-set 차트와 listener를 사용하고 runs-on을 실제 scale-set 이름에 맞춘다**

**설명:** 레거시 CRD 모델과 현재 scale-set 차트를 섞지 않습니다. ARC 0.14.2에는 scaleSetLabels도 있습니다. minRunners는 유휴 runner 수에 관계하며 controller/listener 비용이나 시작 지연을 없애는 설정은 아닙니다.

</details>

### 6. GitHub 예제에서 AWS OIDC 자격 증명을 받는 작업은 무엇인가요?

- A) 모든 외부 PR의 테스트
- B) pull_request_target에서 임의 PR 코드를 실행하는 작업
- C) 테스트를 통과한 신뢰하는 push의 게시 작업
- D) 모든 self-hosted runner가 부팅할 때

<details>
<summary>정답 보기</summary>

**정답: C) 테스트를 통과한 신뢰하는 push의 게시 작업**

**설명:** PR 테스트는 GitHub-hosted runner에서 실행하며 게시용 AWS 권한을 요청하지 않습니다. 게시 역할 trust는 정확한 저장소와 main/보호된 태그로 제한하고, ARC Pod에 상속되는 게시 역할도 두지 않습니다.

</details>

### 7. 이미지 스캔과 게시를 올바르게 연결한 순서는 무엇인가요?

- A) 이미지 빌드 → 동일 이미지 검사 성공 → 게시 → 승인된 digest로 index 생성
- B) 게시 → 스캔 실패를 무시 → latest 배포
- C) 소스만 검사 → 별도 이미지를 다시 빌드해 무조건 게시
- D) JSON 파일만 만들면 검사 성공으로 간주

<details>
<summary>정답 보기</summary>

**정답: A) 이미지 빌드 → 동일 이미지 검사 성공 → 게시 → 승인된 digest로 index 생성**

**설명:** GitLab은 image archive를 아키텍처별 1:1 의존성으로 전달합니다. GitHub도 로컬에 빌드한 이미지를 검사한 뒤 게시합니다. Trivy의 오류나 취약점 게이트 실패는 게시를 막으며, native JSON을 GitLab 보고서 스키마로 잘못 표시하지 않습니다.

</details>

### 8. 네이티브 AMD64/ARM64 runner와 QEMU에 대한 설명으로 맞는 것은 무엇인가요?

- A) platform 플래그만 주면 모든 외부 아키텍처 명령이 실행된다
- B) QEMU 자체가 애플리케이션의 크로스 컴파일러다
- C) AMD64 결과에 ARM64 태그만 붙이면 된다
- D) 네이티브 runner는 해당 CPU에서 빌드하며 QEMU는 다른 CPU 명령을 에뮬레이션한다

<details>
<summary>정답 보기</summary>

**정답: D) 네이티브 runner는 해당 CPU에서 빌드하며 QEMU는 다른 CPU 명령을 에뮬레이션한다**

**설명:** manager/job의 node selector, runner 태그와 helper 아키텍처를 함께 맞춥니다. 최종 index에는 각각 검증한 플랫폼 digest가 들어가야 합니다. 크로스 컴파일은 도구 체인과 Dockerfile을 별도로 구성하는 방식입니다.

</details>

### 9. Next.js standalone 이미지 예제에 필요한 조건은 무엇인가요?

- A) npm ci --omit=dev만 실행하면 모든 빌드가 된다
- B) output: standalone, 빌드 의존성, 정적 파일 복사와 올바른 서버 경로가 필요하다
- C) public과 .next/static은 언제나 standalone에 자동 복사된다
- D) monorepo도 항상 root/server.js에서 시작한다

<details>
<summary>정답 보기</summary>

**정답: B) output: standalone, 빌드 의존성, 정적 파일 복사와 올바른 서버 경로가 필요하다**

**설명:** 예제는 단일 앱 root와 npm lockfile을 전제로 합니다. standalone 출력에 public과 .next/static을 복사하며 0.0.0.0에 바인딩합니다. Monorepo는 tracing root와 중첩된 출력 경로를 따로 확인해야 합니다.

</details>

### 10. Kaniko와 rootless BuildKit에 대해 맞는 설명은 무엇인가요?

- A) daemonless이면 모든 빌드가 root 없이 완전히 격리된다
- B) privileged DinD의 이미지 이름만 바꾸면 rootless 구성이 완성된다
- C) 유지보수 상태와 노드의 user namespace·mount·보안 정책을 확인해야 한다
- D) no-process-sandbox 옵션은 격리를 더 강화한다

<details>
<summary>정답 보기</summary>

**정답: C) 유지보수 상태와 노드의 user namespace·mount·보안 정책을 확인해야 한다**

**설명:** Google Kaniko 저장소는 보관 상태입니다. 선택적 rootless BuildKit 예제는 별도로 검증한 runner용이며, no-process-sandbox는 daemon 컨테이너 내부 프로세스 격리와 정리에 제약을 만듭니다. Registry cache가 모든 cache mount를 자동으로 보존하는 것도 아닙니다.

</details>
