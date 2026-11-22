# EKS Pod Identity 퀴즈

> **마지막 업데이트**: 2026년 11월 21일

이 퀴즈는 [EKS Pod Identity](../../eks/05-eks-security-pod-identity.md)의 내용을 확인합니다.

## 퀴즈 개요
- Association의 역할
- Agent와 자격 증명 흐름
- 역할 신뢰와 session tag
- 교차 계정과 캐시
- IRSA와의 공존과 이전

## 객관식 문제

### 1. EKS Pod Identity association에 대한 설명으로 옳은 것은 무엇인가요?

- A) Association을 만들면 대상 ServiceAccount가 네임스페이스에 자동 생성된다
- B) Association은 IAM 역할과 함께 Kubernetes RBAC 권한도 부여한다
- C) Association은 ServiceAccount의 annotation으로 Kubernetes에 저장된다
- D) 클러스터·네임스페이스·ServiceAccount를 IAM 역할에 매핑하는 EKS API 리소스다

<details>
<summary>정답 보기</summary>

**정답: D) 클러스터·네임스페이스·ServiceAccount를 IAM 역할에 매핑하는 EKS API 리소스다**

**설명:**

Association은 EKS API에 저장되는 클러스터/네임스페이스/ServiceAccount → IAM 역할 매핑입니다. ServiceAccount를 만들거나 Kubernetes RBAC 권한을 주지 않으며 IAM 역할·agent를 생성하지도 않습니다. 문서 예제는 생성 전에 `list-pod-identity-associations`로 기존 association을 확인해 덮어쓰지 않습니다.

</details>

### 2. Association이 있는 새 Pod에서 AWS SDK가 Pod Identity 자격 증명을 얻는 경로로 옳은 것은 무엇인가요?

- A) SDK가 노드 agent endpoint를 호출하고 agent가 EKS Auth에서 자격 증명을 받는다
- B) Agent가 Pod의 모든 AWS 요청을 투명하게 가로채 대신 서명한다
- C) SDK가 web-identity token으로 STS AssumeRoleWithWebIdentity를 호출한다
- D) SDK가 노드의 IMDSv2에서 노드 IAM 역할 자격 증명을 받아 사용한다

<details>
<summary>정답 보기</summary>

**정답: A) SDK가 노드 agent endpoint를 호출하고 agent가 EKS Auth에서 자격 증명을 받는다**

**설명:**

EKS는 association이 있는 새 Pod에 audience가 `pods.eks.amazonaws.com`인 token, token-file 환경 변수와 container credentials URI를 주입합니다. SDK는 agent endpoint(일반적으로 `169.254.170.23/v1/credentials`)를 호출하고 agent는 EKS Auth의 AssumeRoleForPodIdentity로 받은 자격 증명을 SDK에 제공합니다. 앱 요청을 가로채는 방식이 아니며 앱은 그 자격 증명으로 AWS 서비스에 직접 요청합니다.

</details>

### 3. Pod Identity 역할 신뢰 예제에 대한 설명으로 옳은 것은 무엇인가요?

- A) IAM OIDC provider를 `Federated` principal로 지정해 클러스터별로 신뢰를 제한한다
- B) `sts:AssumeRoleWithWebIdentity` 하나만 허용하면 Pod Identity에 충분하다
- C) `pods.eks.amazonaws.com`에 AssumeRole·TagSession을 허용하고 태그로 제한한다
- D) 조건 없이 `pods.eks.amazonaws.com`만 신뢰하는 것이 가장 좁은 최소 권한 구성이다

<details>
<summary>정답 보기</summary>

**정답: C) `pods.eks.amazonaws.com`에 AssumeRole·TagSession을 허용하고 태그로 제한한다**

**설명:**

예제 신뢰 정책은 서비스 principal `pods.eks.amazonaws.com`에 `sts:AssumeRole`·`sts:TagSession`을 허용하고 `aws:RequestTag/eks-cluster-arn`, `kubernetes-namespace`, `kubernetes-service-account` 조건을 겁니다. 이 조건은 기본 session tag에 의존하므로 tag를 비활성화하면 재검토해야 합니다. Association을 만드는 호출자에게는 대상 역할의 `iam:PassRole`도 필요합니다.

</details>

### 4. Pod Identity로 다른 계정의 리소스에 접근하려 할 때 옳은 설명은 무엇인가요?

- A) 다른 계정의 임의 IAM 역할을 association 역할로 직접 지정해 사용한다
- B) Association 역할은 클러스터 계정에 두고 다른 계정의 target role로 chaining한다
- C) Pod Identity는 교차 계정을 지원하지 않으므로 그런 워크로드는 항상 IRSA를 사용한다
- D) Target role을 지정하면 association을 바꿀 때마다 자격 증명 캐시가 즉시 초기화된다

<details>
<summary>정답 보기</summary>

**정답: B) Association 역할은 클러스터 계정에 두고 다른 계정의 target role로 chaining한다**

**설명:**

Association 역할은 EKS 클러스터 계정에 있어야 합니다. 선택적 target IAM role은 다른 계정에 둘 수 있으며, 양쪽 신뢰와 assume-role 권한으로 같은 계정의 역할에서 target으로 chaining합니다. 현재 안내는 target이 없으면 6시간, 있으면 59분 자격 증명 캐시를 설명하며 association 변경이 캐시를 초기화하지 않습니다. Pod를 재생성하면 새 구성을 더 빨리 받을 수 있습니다.

</details>

### 5. 같은 ServiceAccount에 IRSA annotation과 Pod Identity association이 모두 있을 때 EKS의 주입 동작으로 옳은 것은 무엇인가요?

- A) 새 Pod에는 Pod Identity 변수만 주입되고 실행 중인 Pod는 IRSA 변수를 유지한다
- B) 새 Pod에 IRSA와 Pod Identity 변수가 모두 주입되고 SDK가 임의로 고른다
- C) Association을 만드는 즉시 실행 중인 Pod의 환경 변수가 Pod Identity로 바뀐다
- D) IRSA annotation이 항상 우선하므로 새 Pod에서도 association은 무시된다

<details>
<summary>정답 보기</summary>

**정답: A) 새 Pod에는 Pod Identity 변수만 주입되고 실행 중인 Pod는 IRSA 변수를 유지한다**

**설명:**

[EKS 노드 IAM 권한을 IRSA와 Pod Identity로 이전하기](../../security/17-eks-workload-identity-migration.md#irsa와-pod-identity-비교)의 검증 결과처럼 두 설정이 함께 있으면 EKS 웹훅은 새 Pod에 `AWS_CONTAINER_CREDENTIALS_FULL_URI`·`AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`만 주입합니다. 실행 중인 Pod는 재생성 전까지 IRSA 변수를 유지하므로 통제된 rollout으로 전환하고 쓰지 않는 annotation을 지웁니다. 같은 역할이 표시되는 get-caller-identity 성공만으로 두 방식을 구별할 수는 없으므로 주입된 환경 변수 이름을 확인합니다.

</details>
