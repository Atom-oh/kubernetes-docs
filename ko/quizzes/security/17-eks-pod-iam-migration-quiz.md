# IRSA·EKS Pod Identity 마이그레이션 퀴즈

> **마지막 업데이트**: 2026년 11월 19일

[본문과 공식 출처 보기](../../security/17-eks-pod-iam-migration.md)

### 1. 일부 워크로드를 IRSA·Pod Identity로 옮긴 뒤에도 권한을 받지 않은 `default/neighbor` Pod가 S3를 읽을 수 있는 이유는?

- A) Pod Identity Agent가 모든 Pod에 자격 증명을 나눠 주기 때문
- B) 노드 Role에 앱 권한이 남아 있고 Pod가 IMDS로 노드 Role 자격 증명을 받을 수 있기 때문
- C) IRSA OIDC provider가 클러스터 전체를 신뢰하기 때문
- D) S3 bucket이 public이기 때문

<details>
<summary>정답 보기</summary>

**정답: B) 노드 Role에 앱 권한이 남아 있고 Pod가 IMDS로 노드 Role 자격 증명을 받을 수 있기 때문**

**설명:** 아무것도 주입되지 않은 Pod의 SDK는 credential chain 끝에서 IMDS(169.254.169.254)에 묻고 노드 instance profile 자격 증명을 받습니다. IRSA·Pod Identity를 추가하는 것만으로는 이 경로가 사라지지 않으며, 노드 Role 정리와 IMDS 차단(Phase 4)이 필요합니다.

</details>

### 2. IMDSv2 required와 `HttpPutResponseHopLimit=1`을 설정했을 때의 효과는?

- A) 노드 자신도 IMDS를 쓸 수 없다
- B) 자체 network namespace를 가진 Pod에는 토큰 응답이 도달하지 않지만 hostNetwork Pod는 여전히 접근할 수 있다
- C) 모든 Pod의 IMDS 접근이 차단되며 hostNetwork Pod도 예외가 없다
- D) Pod Identity Agent가 동작하지 않는다

<details>
<summary>정답 보기</summary>

**정답: B) 자체 network namespace를 가진 Pod에는 토큰 응답이 도달하지 않지만 hostNetwork Pod는 여전히 접근할 수 있다**

**설명:** PUT 토큰 응답은 IP TTL만큼만 이동하므로 한 hop을 더 거치는 Pod에는 닿지 않습니다. hostNetwork Pod는 노드와 같은 namespace라 막히지 않습니다. Pod Identity Agent는 169.254.170.23을 쓰므로 hop limit의 영향을 받지 않습니다.

</details>

### 3. IRSA Role trust policy에서 `sub`·`aud` 조건으로 올바른 것은?

- A) `sub = system:serviceaccount:<ns>:<sa>`, `aud = sts.amazonaws.com`
- B) `sub = <pod 이름>`, `aud = pods.eks.amazonaws.com`
- C) `sub = arn:aws:iam::<acct>:role/<node role>`, `aud = ec2.amazonaws.com`
- D) `sub = *`, `aud = *`

<details>
<summary>정답 보기</summary>

**정답: A) `sub = system:serviceaccount:<ns>:<sa>`, `aud = sts.amazonaws.com`**

**설명:** STS는 클러스터별 OIDC provider로 JWT를 검증한 뒤 trust policy의 `sub`·`aud`를 평가합니다. `StringEquals`로 namespace와 SA를 고정해야 하며, `StringLike`와 `*`로 넓히면 다른 SA도 Role을 가져갈 수 있습니다.

</details>

### 4. Pod Identity에서 Pod가 자격 증명을 받는 경로는?

- A) Pod → STS `AssumeRoleWithWebIdentity`
- B) Pod → IMDS 169.254.169.254
- C) Pod → `169.254.170.23`의 Pod Identity Agent → EKS Auth API `AssumeRoleForPodIdentity` → STS
- D) Pod → kube-apiserver → IAM

<details>
<summary>정답 보기</summary>

**정답: C) Pod → `169.254.170.23`의 Pod Identity Agent → EKS Auth API `AssumeRoleForPodIdentity` → STS**

**설명:** SDK는 `AWS_CONTAINER_CREDENTIALS_FULL_URI`(http://169.254.170.23/v1/credentials)로 토큰을 보냅니다. hostNetwork DaemonSet인 Agent가 노드 Role로 EKS Auth API를 호출하고, EKS가 association을 조회해 Role을 assume합니다.

</details>

### 5. Pod Identity용 IAM Role trust policy로 올바른 것은?

- A) `Principal: { Federated: <OIDC provider ARN> }`, `sts:AssumeRoleWithWebIdentity`
- B) `Principal: { Service: pods.eks.amazonaws.com }`, `sts:AssumeRole` + `sts:TagSession`
- C) `Principal: { Service: ec2.amazonaws.com }`, `sts:AssumeRole`
- D) `Principal: { Service: eks.amazonaws.com }`, `sts:AssumeRole`만

<details>
<summary>정답 보기</summary>

**정답: B) `Principal: { Service: pods.eks.amazonaws.com }`, `sts:AssumeRole` + `sts:TagSession`**

**설명:** trust policy에 클러스터 정보가 없어 여러 클러스터에서 재사용할 수 있습니다. EKS가 session tag를 붙이므로 `sts:TagSession`이 필요합니다. 어떤 SA가 Role을 쓸지는 association이 결정합니다.

</details>

### 6. 같은 SA에 IRSA annotation과 Pod Identity association이 모두 있을 때 일반적인 AWS SDK가 쓰는 것은?

- A) Pod Identity, 항상 우선한다
- B) IRSA, default chain에서 web identity가 container credentials보다 먼저 평가된다
- C) 둘 다 실패하고 IMDS를 쓴다
- D) 무작위로 선택한다

<details>
<summary>정답 보기</summary>

**정답: B) IRSA, default chain에서 web identity가 container credentials보다 먼저 평가된다**

**설명:** 그래서 IRSA → Pod Identity 전환 시 association을 만든 뒤 annotation을 제거하고 Pod를 재시작해야 실제로 바뀝니다. 정적 키 env가 있으면 둘 다 무시된다는 점도 함께 확인합니다.

</details>

### 7. SA에 annotation을 추가하거나 association을 만든 직후 실행 중인 Pod에 대해 해야 할 일은?

- A) 아무것도 없다, 즉시 반영된다
- B) kubelet을 재시작한다
- C) Pod를 재시작(`rollout restart`)한다, webhook은 Pod 생성 시에만 env와 token을 주입한다
- D) 노드를 교체한다

<details>
<summary>정답 보기</summary>

**정답: C) Pod를 재시작(`rollout restart`)한다, webhook은 Pod 생성 시에만 env와 token을 주입한다**

**설명:** Pod Identity Webhook은 mutating admission webhook이라 새로 생성되는 Pod만 변경합니다. 방식 전환·롤백 모두 재시작이 필요합니다.

</details>

### 8. 다음 중 본문 내용과 맞는 것은?

- A) Pod Identity는 Fargate를 지원하고 IRSA는 지원하지 않는다
- B) IRSA는 Fargate에서 쓸 수 있고, Pod Identity는 session tag(`kubernetes-namespace` 등)로 ABAC를 구현할 수 있다
- C) Pod Identity는 EKS 밖 Kubernetes에서도 OIDC만 있으면 쓸 수 있다
- D) IRSA는 trust policy 변경 없이 여러 클러스터에서 Role을 재사용할 수 있다

<details>
<summary>정답 보기</summary>

**정답: B) IRSA는 Fargate에서 쓸 수 있고, Pod Identity는 session tag(`kubernetes-namespace` 등)로 ABAC를 구현할 수 있다**

**설명:** Pod Identity는 EC2 노드의 Agent에 의존하므로 Fargate를 지원하지 않고 EKS 전용입니다. 대신 `${aws:PrincipalTag/kubernetes-namespace}` 같은 session tag로 하나의 Role이 namespace별 리소스만 허용하게 만들 수 있습니다. 여러 클러스터 재사용 시 trust 변경이 필요 없는 쪽은 Pod Identity입니다.

</details>
