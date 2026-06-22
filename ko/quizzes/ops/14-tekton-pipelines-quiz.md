# Tekton Pipelines 퀴즈

1. Tekton이 Jenkins나 GitHub Actions 대비 Kubernetes 환경에서 유리한 점은?
   - A) Tekton이 더 많은 플러그인을 제공
   - B) CRD 기반으로 파이프라인을 Kubernetes 리소스로 관리하여 GitOps, RBAC, 네임스페이스 격리 적용 가능
   - C) Tekton이 더 빠른 실행 속도를 제공
   - D) Tekton이 무료이고 다른 도구는 유료

<details>
<summary>정답 보기</summary>

**정답: B) CRD 기반으로 파이프라인을 Kubernetes 리소스로 관리하여 GitOps, RBAC, 네임스페이스 격리 적용 가능**

**설명:**
Tekton은 Task, Pipeline, PipelineRun 등을 Kubernetes CRD로 정의합니다. 이를 통해 파이프라인을 Git에서 선언적으로 관리(GitOps), Kubernetes RBAC로 접근 제어, 네임스페이스별 격리, kubectl로 관리할 수 있습니다. 각 Step이 별도 컨테이너에서 실행되어 격리성도 높습니다.

</details>

---

2. Tekton Pipeline에서 Task 간 데이터를 공유하는 방법은?
   - A) 환경 변수로 전달
   - B) Workspace(PVC)를 통해 파일 시스템을 공유하고, Results로 작은 데이터를 전달
   - C) ConfigMap에 저장
   - D) Task 간 직접 네트워크 통신

<details>
<summary>정답 보기</summary>

**정답: B) Workspace(PVC)를 통해 파일 시스템을 공유하고, Results로 작은 데이터를 전달**

**설명:**
Workspace는 PVC 기반으로 Task 간 파일 시스템을 공유합니다. 소스 코드 클론 후 빌드 Task에서 사용하는 패턴에 적합합니다. Results는 작은 문자열 데이터(이미지 태그, 커밋 SHA 등)를 Task 간 전달할 때 사용하며, `$(tasks.task-name.results.result-name)`으로 참조합니다.

</details>

---

3. Tekton Triggers의 EventListener가 하는 역할은?
   - A) 이벤트를 생성하여 외부 시스템으로 전송
   - B) Webhook 요청을 수신하고, TriggerBinding/TriggerTemplate을 통해 PipelineRun을 자동 생성
   - C) 파이프라인 실행 결과를 모니터링
   - D) Git 리포지토리를 주기적으로 폴링

<details>
<summary>정답 보기</summary>

**정답: B) Webhook 요청을 수신하고, TriggerBinding/TriggerTemplate을 통해 PipelineRun을 자동 생성**

**설명:**
EventListener는 HTTP 엔드포인트로 Webhook 요청(GitHub Push, PR 이벤트 등)을 수신합니다. Interceptor가 요청을 검증/필터링하고, TriggerBinding이 페이로드에서 파라미터를 추출하며, TriggerTemplate이 이 파라미터로 PipelineRun을 생성합니다.

</details>

---

4. Tekton Chains가 제공하는 Supply Chain Security 기능은?
   - A) 컨테이너 이미지의 취약점을 스캔
   - B) TaskRun/PipelineRun의 결과물(이미지)에 자동으로 서명하고 SLSA Provenance를 생성
   - C) 네트워크 트래픽을 암호화
   - D) RBAC 정책을 자동 생성

<details>
<summary>정답 보기</summary>

**정답: B) TaskRun/PipelineRun의 결과물(이미지)에 자동으로 서명하고 SLSA Provenance를 생성**

**설명:**
Tekton Chains는 TaskRun이 완료된 후 자동으로 OCI 이미지에 Cosign/Sigstore로 서명하고, SLSA Provenance(빌드 메타데이터, 소스 정보, 빌드 단계 등)를 생성합니다. 이를 통해 소프트웨어 공급망 보안을 강화하고, 이미지의 출처와 무결성을 검증할 수 있습니다.

</details>

---

5. Tekton Pipeline에서 `finally` Task의 목적은?
   - A) 파이프라인의 첫 번째 Task로 실행
   - B) 파이프라인의 성공/실패와 관계없이 항상 마지막에 실행되는 정리 작업
   - C) 조건부로 실행되는 Task
   - D) 병렬로 실행되는 Task

<details>
<summary>정답 보기</summary>

**정답: B) 파이프라인의 성공/실패와 관계없이 항상 마지막에 실행되는 정리 작업**

**설명:**
`finally` Task는 파이프라인의 다른 모든 Task가 완료된 후 항상 실행됩니다. 빌드 실패 시에도 실행되므로, 임시 리소스 정리, 알림 전송, 테스트 결과 보고 등의 작업에 적합합니다. try-catch-finally 패턴의 finally 블록과 유사합니다.

</details>

---

6. ArgoCD + Tekton 통합 아키텍처에서 CI/CD를 분리하는 이유는?
   - A) Tekton이 CD를 지원하지 않으므로
   - B) CI(빌드/테스트)와 CD(배포)의 관심사를 분리하여 보안, 감사, 롤백을 개선
   - C) ArgoCD가 CI를 지원하지 않으므로
   - D) 두 도구의 라이선스가 다르므로

<details>
<summary>정답 보기</summary>

**정답: B) CI(빌드/테스트)와 CD(배포)의 관심사를 분리하여 보안, 감사, 롤백을 개선**

**설명:**
Tekton이 CI(소스 클론, 테스트, 빌드, 이미지 Push)를 담당하고, ArgoCD가 CD(Git 기반 선언적 배포)를 담당하는 분리 아키텍처를 구성합니다. CI는 이미지 태그를 Git에 커밋하고, ArgoCD가 이 변경을 감지하여 배포합니다. 이를 통해 배포 권한 분리, Git 기반 감사 추적, 선언적 롤백이 가능합니다.

</details>

---

7. Tekton의 Interceptor 중 CEL Interceptor의 활용 사례는?
   - A) GitHub 서명을 검증
   - B) CEL 표현식으로 Webhook 페이로드를 필터링하고 변환 (특정 브랜치, 파일 경로 등)
   - C) GitLab 토큰을 검증
   - D) Bitbucket 이벤트를 처리

<details>
<summary>정답 보기</summary>

**정답: B) CEL 표현식으로 Webhook 페이로드를 필터링하고 변환 (특정 브랜치, 파일 경로 등)**

**설명:**
CEL(Common Expression Language) Interceptor는 Webhook 페이로드에 대해 CEL 표현식으로 필터링과 변환을 수행합니다. 예를 들어 `body.ref == 'refs/heads/main'`으로 main 브랜치 Push만 필터링하거나, `body.commits.exists(c, c.modified.exists(f, f.startsWith('src/')))`로 특정 경로 변경만 트리거할 수 있습니다.

</details>

---

8. Tekton의 PipelineRun 정리(Cleanup) 전략으로 적절한 것은?
   - A) 모든 PipelineRun을 영구적으로 보관
   - B) TTL 기반 자동 삭제와 성공/실패별 보존 기간을 설정하여 리소스를 관리
   - C) 수동으로만 삭제
   - D) PipelineRun은 자동으로 삭제됨

<details>
<summary>정답 보기</summary>

**정답: B) TTL 기반 자동 삭제와 성공/실패별 보존 기간을 설정하여 리소스를 관리**

**설명:**
PipelineRun과 TaskRun은 실행 후 etcd에 남아 스토리지를 소비합니다. Tekton의 결과 정리 설정(`keep`, `keep-since`)이나 CronJob 기반 정리 스크립트로 오래된 실행 기록을 자동 삭제합니다. 실패한 실행은 디버깅을 위해 더 오래 보존하는 것이 일반적입니다.

</details>
