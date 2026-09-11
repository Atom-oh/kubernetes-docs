# ArgoCD 퀴즈

이 퀴즈는 ArgoCD와 GitOps에 대한 이해도를 테스트합니다.

## 문제 1: GitOps 기본 원칙

<details>
<summary>GitOps의 4가지 핵심 원칙은 무엇인가요?</summary>

**답변:**
1. **선언적 구성**: 시스템의 원하는 상태를 코드로 정의
2. **버전 관리와 불변성**: 원하는 상태의 버전·전체 이력·불변성을 보존
3. **자동 Pull**: 에이전트가 소스에서 원하는 상태 선언을 자동으로 가져옴
4. **지속적 조정**: 실제 상태를 관찰하고 원하는 상태 적용을 지속적으로 시도

이러한 원칙들은 GitOps가 단순한 배포 도구를 넘어서 전체 운영 모델로 작동할 수 있게 합니다.
</details>

## 문제 2: ArgoCD 아키텍처

<details>
<summary>ArgoCD의 주요 구성 요소와 각각의 역할은?</summary>

**답변:**
- **API Server**: REST API 및 웹 UI 제공, 인증 및 권한 관리
- **Repository Server**: Git 저장소 연결 및 매니페스트 생성
- **Application Controller**: 애플리케이션 상태 모니터링 및 동기화 수행
- **Redis**: 재구성 가능한 캐시
- **Dex**: OIDC 인증 서버 (선택사항)

구성 요소별 확장 방식이 다릅니다. Application Controller는 shard를 나누고, ApplicationSet은 leader election을 사용합니다. 번들 Dex는 in-memory 저장소이므로 replica만 늘리는 방식이 안전하지 않습니다.
</details>

## 문제 3: Application 리소스

<details>
<summary>ArgoCD Application 리소스의 필수 구성 요소는?</summary>

**답변:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/example/app-config
    targetRevision: HEAD
    path: k8s
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

**필수 요소:**
- `source`: Git 저장소 정보
- `destination`: 배포 대상 클러스터 및 네임스페이스
- `project`: ArgoCD 프로젝트 (권한 관리)
</details>

## 문제 4: 동기화 정책

<details>
<summary>ArgoCD의 자동 동기화와 수동 동기화의 차이점은?</summary>

**답변:**
**자동 동기화 (Automated Sync):**
```yaml
syncPolicy:
  automated:
    prune: true      # 불필요한 리소스 자동 삭제
    selfHeal: true   # 드리프트 자동 복구
```
- Git 변경 시 자동으로 클러스터에 적용
- 드리프트 감지 시 자동 복구
- 프로덕션 환경에서는 신중하게 사용

**수동 동기화 (Manual Sync):**
- 사용자가 명시적으로 동기화 실행
- 변경 사항을 검토한 후 적용
- 검토·승인 절차와 운영 부담은 별도로 설계해야 함
</details>

## 문제 5: ApplicationSet

<details>
<summary>ArgoCD ApplicationSet의 용도와 주요 생성기(Generator) 유형은?</summary>

**답변:**
**용도:**
- 다중 클러스터 배포 자동화
- 템플릿 기반 Application 생성
- 환경별 구성 관리

**주요 생성기:**
- **List Generator**: 정적 값 목록 기반
- **Cluster Generator**: 등록된 클러스터 기반
- **Git Generator**: Git 저장소 구조 기반
- **Matrix Generator**: 여러 생성기 조합
- **Pull Request Generator**: PR 기반 임시 환경

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: demo-cluster-apps
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions: ["missingkey=error"]
  generators:
  - clusters:
      selector:
        matchLabels:
          environment: demo
  template:
    metadata:
      name: '{{.nameNormalized}}-guestbook'
    spec:
      project: default
      source:
        repoURL: https://github.com/argoproj/argocd-example-apps.git
        targetRevision: HEAD
        path: guestbook
      destination:
        server: '{{.server}}'
        namespace: guestbook
      syncPolicy:
        syncOptions: [CreateNamespace=true]
```
</details>

## 문제 6: 보안 모범 사례

<details>
<summary>ArgoCD 보안을 강화하기 위한 주요 방법들은?</summary>

**답변:**
1. **RBAC 구성**:
   ```yaml
   policy.default: role:authenticated
   policy.csv: |
     p, role:dev, applications, get, dev/*, allow
     p, role:dev, projects, get, dev, allow
     g, dev-team, role:dev
   ```

2. **SSO 통합**:
   - OIDC 직접 연동 또는 Dex 등 지원 커넥터를 통한 다른 IdP 연동
   - 중앙 집중식 인증 관리

3. **네트워크 보안**:
   - Ingress TLS 설정
   - 네트워크 정책 적용
   - 프라이빗 Git 저장소 사용

4. **시크릿 관리**:
   - External Secrets Operator 사용
   - Sealed Secrets 또는 Helm Secrets
   - 평문 시크릿을 Git에서 제외하고 외부 Secret 저장소 또는 적절한 암호화·키 관리를 사용

5. **감사 로깅**:
   - 모든 변경 사항 추적
   - 액세스 로그 모니터링
</details>

## 문제 7: 멀티 클러스터 관리

<details>
<summary>ArgoCD에서 여러 클러스터를 관리하는 방법은?</summary>

**답변:**
1. **클러스터 등록**:
   ```bash
   argocd cluster add my-cluster-context
   ```

2. **클러스터별 Application 배포**:
   ```yaml
   destination:
     server: https://my-cluster-api-server
     namespace: production
   ```

3. **ApplicationSet을 통한 자동화**:
   ```yaml
   generators:
   - clusters:
       selector:
         matchLabels:
           environment: production
   ```

4. **클러스터 권한 관리**:
   - 클러스터별 서비스 계정 구성
   - 최소 권한 원칙 적용
   - 네임스페이스 기반 격리

5. **모니터링 및 알림**:
   - 클러스터별 상태 대시보드
   - 동기화 실패 알림
   - 리소스 사용량 모니터링
</details>

## 문제 8: 문제 해결

<details>
<summary>ArgoCD 애플리케이션이 "OutOfSync" 상태일 때 확인해야 할 사항은?</summary>

**답변:**
1. **Git 저장소 상태 확인**:
   ```bash
   # 저장소 접근 권한 확인
   argocd repo list
   argocd repo get "$REPO_URL"
   ```

2. **매니페스트 유효성 검증**:
   ```bash
   # 로컬에서 매니페스트 검증
   kubectl --context "$TARGET_CONTEXT" apply --server-side --dry-run=server -f manifests/
   ```

3. **동기화 정책 확인**:
   - 자동 동기화 설정 여부
   - Prune 및 SelfHeal 옵션
   - 동기화 조건 (Sync Windows)

4. **리소스 상태 분석**:
   ```bash
   # 애플리케이션 상세 정보 확인
   argocd app get "$APP_NAME"
   argocd app diff "$APP_NAME"
   ```

5. **로그 확인**:
   ```bash
   # ArgoCD 컨트롤러 로그
   kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller
   ```

6. **수동 동기화 시도**:
   ```bash
   argocd app sync "$APP_NAME" --dry-run
   ```
</details>

## 문제 9: GitOps 확장 운영 패턴

<details>
<summary>가이드에서 다루는 GitOps 확장 운영 패턴은?</summary>

**답변:**
1. **멀티 클러스터 GitOps**:
   - ApplicationSets를 통한 다중 클러스터 배포 자동화
   - 클러스터 간 구성 동기화 및 정책 적용

2. **하이브리드 및 멀티 클라우드 GitOps**:
   - 온프레미스와 클라우드 환경의 일관된 배포 전략
   - 다양한 클라우드 제공업체 간 워크로드 이식성

3. **GitOps와 정책 관리 통합**:
   - OPA(Open Policy Agent)와 Kyverno 통합
   - 규정 준수 및 거버넌스 자동화
   - 보안 정책의 코드화 및 버전 관리

4. **Progressive Delivery**:
   - Canary 및 Blue-Green 배포 자동화
   - Argo Rollouts와의 통합
   - 메트릭 기반 자동 롤백
</details>

## 문제 10: Amazon EKS 통합

<details>
<summary>ArgoCD를 Amazon EKS와 통합할 때 고려사항은?</summary>

**답변:**
1. **IAM 권한 설정**:
   ```yaml
   # IRSA (IAM Roles for Service Accounts) 구성
   controller:
     serviceAccount:
       annotations:
         eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ArgoCD-Management
   ```

2. **ALB Ingress 구성**:
   ```yaml
   metadata:
     annotations:
       alb.ingress.kubernetes.io/scheme: internal
       alb.ingress.kubernetes.io/target-type: ip
   spec:
     ingressClassName: alb
   ```

3. **EKS 클러스터 등록**:
   ```bash
   # EKS 클러스터를 ArgoCD에 등록
   argocd cluster add "$TARGET_CONTEXT"
   ```

4. **ECR 통합**:
   - ECR 이미지 자동 업데이트
   - Image Updater 구성

5. **AWS Load Balancer Controller**:
   - 서비스 로드 밸런싱 최적화
   - Target Group Binding 활용

6. **보안 고려사항**:
   - VPC 엔드포인트 사용
   - 보안 그룹 구성
   - 네트워크 정책 적용
</details>

---

**점수 계산:**
- 8-10개 정답: 이 퀴즈의 핵심 개념 이해
- 6-7개 정답: 양호 (추가 학습 권장)
- 4-5개 정답: 보통 (기본 개념 복습 필요)
- 0-3개 정답: 기본 개념 복습 후 실습 권장


예제의 `REPO_URL`, `APP_NAME`, `TARGET_CONTEXT`는 실제 값으로 설정합니다. `TARGET_CONTEXT`는 kubeconfig context이며 EKS 기본 context 이름이 ARN인 경우도 있습니다. `cluster add`의 대상 RBAC 변경과 sync/prune의 차이를 확인합니다. 위 dry run은 변경 검토용이고, `--prune`은 삭제를 포함하므로 별도 확인 후 선택합니다. IRSA annotation만으로 신뢰 정책·EKS Access Entry가 구성되지 않으며, ALB에는 인증서·TLS·접근 경로도 필요합니다. ApplicationSet의 `environment: demo`는 등록된 클러스터 Secret의 라벨입니다. 기본 `role:authenticated`에는 전역 readonly 권한을 추가하지 않으며 `dev-team`에 필요한 범위만 부여합니다.
