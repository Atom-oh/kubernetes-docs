# EKS 워크로드 IAM 이전 퀴즈

> **마지막 업데이트**: 2026년 11월 21일

[본문과 라이브 데모 보기](../../security/17-eks-workload-identity-migration.md)

### 1. 노드 IAM 역할에 앱의 S3 권한을 붙였을 때 가장 큰 문제는?

- A) S3 요청이 느려진다
- B) 그 노드에서 IMDS에 접근할 수 있는 모든 Pod가 같은 권한을 쓴다
- C) 노드가 클러스터에 등록되지 않는다
- D) S3 버킷이 공개된다

<details>
<summary>정답 보기</summary>

**정답: B) 그 노드에서 IMDS에 접근할 수 있는 모든 Pod가 같은 권한을 쓴다**

**설명:** 노드 역할은 인스턴스 프로파일로 노드 전체에 붙습니다. hop limit이 2 이상이면 일반 Pod도 IMDSv2로 노드 역할 자격 증명을 받습니다. CloudTrail에도 노드 인스턴스 세션으로만 남아 워크로드를 구분하기 어렵습니다.

</details>

### 2. AWS SDK 기본 자격 증명 체인에서 IMDS와 비교한 IRSA·Pod Identity 공급자의 순서는?

- A) IMDS가 가장 먼저다
- B) IRSA(웹 ID)와 Pod Identity(컨테이너 공급자)가 IMDS보다 먼저다
- C) 순서는 무작위다
- D) Pod Identity만 IMDS보다 먼저다

<details>
<summary>정답 보기</summary>

**정답: B) IRSA(웹 ID)와 Pod Identity(컨테이너 공급자)가 IMDS보다 먼저다**

**설명:** 환경 변수 키, 웹 ID 토큰, 컨테이너 자격 증명 공급자가 IMDS보다 앞에 있습니다. 그래서 EKS가 변수를 주입한 새 Pod는 코드 변경 없이 새 역할을 씁니다. 아무것도 주입되지 않으면 마지막 단계인 IMDS의 노드 역할을 받습니다.

</details>

### 3. IRSA에서 STS가 projected 토큰을 믿을 수 있는 근거는?

- A) 토큰에 IAM 액세스 키가 들어 있다
- B) 클러스터 issuer를 IAM OIDC provider로 등록했고, 역할 신뢰 정책이 `aud`와 `sub`를 확인한다
- C) Pod Identity Agent가 토큰을 서명한다
- D) 노드 역할이 STS를 대신 호출한다

<details>
<summary>정답 보기</summary>

**정답: B) 클러스터 issuer를 IAM OIDC provider로 등록했고, 역할 신뢰 정책이 `aud`와 `sub`를 확인한다**

**설명:** STS `AssumeRoleWithWebIdentity`는 OIDC provider에 등록된 issuer의 키로 토큰 서명을 검증하고, `aud`가 `sts.amazonaws.com`, `sub`가 `system:serviceaccount:<namespace>:<serviceaccount>`인지 신뢰 정책 조건으로 확인합니다.

</details>

### 4. Pod Identity에서 노드 역할에 남아야 하는 권한은?

- A) 앱의 S3 읽기 권한
- B) `sts:AssumeRoleWithWebIdentity`
- C) 에이전트가 EKS Auth를 부르는 `eks-auth:AssumeRoleForPodIdentity` (`AmazonEKSWorkerNodePolicy`에 포함)
- D) 아무 권한도 필요 없다

<details>
<summary>정답 보기</summary>

**정답: C) 에이전트가 EKS Auth를 부르는 `eks-auth:AssumeRoleForPodIdentity` (`AmazonEKSWorkerNodePolicy`에 포함)**

**설명:** Pod Identity Agent는 노드 역할의 이 권한으로 EKS Auth를 호출합니다. 앱의 업무 권한은 association에 지정한 Pod Identity 역할에 둡니다.

</details>

### 5. 데모의 `diff`에서 IRSA 토큰과 Pod Identity 토큰을 구분한 클레임은?

- A) `iss`
- B) `aud`
- C) `exp`
- D) 둘은 완전히 같다

<details>
<summary>정답 보기</summary>

**정답: B) `aud`**

**설명:** 두 토큰 모두 같은 클러스터 issuer가 서명한 ServiceAccount 토큰입니다. IRSA 토큰의 대상은 `sts.amazonaws.com`, Pod Identity 토큰의 대상은 `pods.eks.amazonaws.com`입니다. `sub`는 ServiceAccount마다 다릅니다.

</details>

### 6. 같은 IAM 역할을 새 클러스터 10개에서 쓰려 할 때 신뢰 정책 변경이 필요 없는 방식은?

- A) IRSA
- B) EKS Pod Identity
- C) 둘 다 필요 없다
- D) 둘 다 클러스터마다 수정해야 한다

<details>
<summary>정답 보기</summary>

**정답: B) EKS Pod Identity**

**설명:** Pod Identity 역할은 `pods.eks.amazonaws.com` 하나를 신뢰하고 클러스터 범위는 association과 세션 태그로 정합니다. IRSA는 클러스터마다 OIDC provider와 신뢰 정책 문장이 필요하고, 기본 2,048자 신뢰 정책에는 보통 4개 안팎의 연결만 들어갑니다.

</details>

### 7. Fargate에서 실행되는 Pod에 워크로드 역할을 줘야 한다면?

- A) EKS Pod Identity
- B) IRSA
- C) 노드 역할
- D) 둘 다 쓸 수 없다

<details>
<summary>정답 보기</summary>

**정답: B) IRSA**

**설명:** EKS Pod Identity는 EKS의 Linux EC2 노드와 EKS Hybrid Nodes(Agent의 하이브리드 DaemonSet과 노드 자격 증명 파일 설정 필요)에서 지원됩니다. Fargate, Windows EC2 노드, Outposts, EKS Anywhere에서는 IRSA를 씁니다.

</details>

### 8. association을 만들고 곧바로 rollout했는데 새 Pod가 여전히 노드 역할을 쓴다. 가장 가능성 높은 원인은?

- A) S3 버킷 정책이 거부했다
- B) association이 아직 Pod 생성(admission)에 반영되지 않아 변수가 주입되지 않았다
- C) Pod Identity Agent가 IMDS를 차단했다
- D) IRSA 주석이 필요하다

<details>
<summary>정답 보기</summary>

**정답: B) association이 아직 Pod 생성(admission)에 반영되지 않아 변수가 주입되지 않았다**

**설명:** association은 eventual consistency로 몇 초 늦게 반영될 수 있습니다. 데모의 첫 리허설에서도 association을 만든 직후 rollout한 Pod에는 주입되지 않았고, 두 번째 리허설에서는 주입이 보이기까지 5초가 걸렸습니다. `kubectl create --dry-run=server`로 Pod 템플릿의 주입 결과를 확인하고 rollout합니다.

</details>

### 9. IRSA 주석이 붙은 ServiceAccount에 Pod Identity association을 추가하고 Pod를 새로 만들었다. 새 Pod는 어떤 자격 증명을 쓰는가?

- A) Pod Identity. 웹훅이 Pod Identity 변수만 주입한다
- B) IRSA. 기본 체인에서 웹 ID 공급자가 먼저다
- C) 요청마다 번갈아 쓴다
- D) 두 설정이 충돌해 Pod가 시작하지 않는다

<details>
<summary>정답 보기</summary>

**정답: A) Pod Identity. 웹훅이 Pod Identity 변수만 주입한다**

**설명:** association이 있으면 EKS 웹훅은 새 Pod에 `AWS_CONTAINER_CREDENTIALS_FULL_URI`와 `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`만 넣고 IRSA 변수는 넣지 않습니다. 데모 클러스터의 dry-run에서도 그렇게 주입됐습니다. 체인 순서(B)는 두 변수가 모두 있을 때의 이야기이고, association을 추가하기 전에 만든 Pod는 다시 만들기 전까지 IRSA를 계속 씁니다.

</details>

### 10. 노드 역할의 S3 정책을 회수한 직후 레거시 Pod의 읽기가 거부됐다. 바로 이전 완료로 판단해도 되는가?

- A) 된다. 한 번 거부되면 고정된다
- B) 안 된다. IAM 변경은 eventual consistency라 몇 분 동안 결과가 섞일 수 있으므로 관찰을 이어 간다
- C) 된다. 노드를 재시작하면 확정된다
- D) 안 된다. 노드 역할을 삭제해야 한다

<details>
<summary>정답 보기</summary>

**정답: B) 안 된다. IAM 변경은 eventual consistency라 몇 분 동안 결과가 섞일 수 있으므로 관찰을 이어 간다**

**설명:** 데모에서 레거시 Pod는 13초 만에 거부됐지만 약 4분 30초 뒤에 허용 응답이 두 번 더 나왔습니다. 크론 실행까지 포함해 수 분 이상 관찰하고, 롤백용 정책 복원본을 준비해 둡니다.

</details>
