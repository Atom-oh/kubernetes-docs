# EKS 클러스터 접근 인증 퀴즈

> **마지막 업데이트**: 2026년 11월 21일

이 퀴즈는 [EKS 클러스터 접근 인증: IAM과 Access Entry](../../eks/05-eks-security-cluster-access.md)의 내용을 확인합니다.

## 퀴즈 개요
- IAM 인증과 Kubernetes 권한 부여
- EKS cluster role과 생성 호출자
- Authentication mode와 access entry
- Access policy 범위와 검증

## 객관식 문제

### 1. IAM 사용자·역할에 대해 신원 인증과 Kubernetes 권한 부여를 올바르게 결합하는 EKS 구성은 무엇인가요?

- A) IAM 관리 권한만 사용
- B) 신원 인증 경로 없이 RBAC 규칙만 생성
- C) IAM 클러스터 접근과 적절한 RBAC·EKS access policy 구성
- D) API endpoint 네트워크 제한만 사용

<details>
<summary>정답 보기</summary>

**정답: C) IAM 클러스터 접근과 적절한 RBAC·EKS access policy 구성**

**설명:**

IAM은 구성한 EKS 접근 경로에서 의도한 사람·자동화 신원을 인증합니다. Kubernetes RBAC와 EKS access policy는 Kubernetes 작업 권한을 부여하며 grant는 합산됩니다. 네트워크 제한은 별도 계층이며 권한 부여를 대체하지 않습니다. Pod의 Kubernetes 인증은 일반적으로 ServiceAccount token을 사용하고 IRSA·Pod Identity는 워크로드 AWS 자격 증명을 제공합니다.

EKS cluster 서비스 역할과 개발자 역할의 목적은 다릅니다. 개발자에게 AmazonEKSClusterPolicy를 붙여도 Kubernetes 접근 권한이 생기지 않으며 DescribeCluster·ListClusters나 kubeconfig 파일만으로 workload 작업이 허용되지는 않습니다.

**범위가 있는 구현:** 권한 있는 플랫폼 운영자가 승인된 기존 개발자 IAM 역할을 위해 아래 namespace·RBAC를 준비합니다. 클러스터는 access entry를 이미 지원해야 합니다. 관리자·노드 매핑을 보존하고 authentication mode migration을 검토하며 sample ConfigMap으로 aws-auth를 덮어쓰지 않습니다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: security-demo
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
```



```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster name}"
: "${AWS_REGION:?Set its Region}"
: "${DEVELOPER_ROLE_ARN:?Set a prepared IAM role ARN, not an STS session ARN}"
MODE=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.accessConfig.authenticationMode --output text)
case "$MODE" in
  API|API_AND_CONFIG_MAP) ;;
  *) echo "Access entries are not enabled; review the migration first"; exit 1 ;;
esac
aws eks list-access-entries --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --output json > security-access-entries.json
python3 - "$DEVELOPER_ROLE_ARN" <<'PY'
import json, sys
with open("security-access-entries.json") as stream:
    existing = json.load(stream)["accessEntries"]
if sys.argv[1] in existing:
    raise SystemExit("Entry already exists; inspect its groups/policies instead of overwriting")
PY
aws eks create-access-entry --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --principal-arn "$DEVELOPER_ROLE_ARN" --type STANDARD \
  --kubernetes-groups security-demo-developers
```



```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: developer
  namespace: security-demo
rules:
- apiGroups:
  - ''
  resources:
  - pods
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - apps
  resources:
  - deployments
  verbs:
  - get
  - list
  - watch
  - create
  - update
  - patch
- apiGroups:
  - batch
  resources:
  - jobs
  verbs:
  - get
  - list
  - watch
  - create
  - update
  - patch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: developer
  namespace: security-demo
subjects:
- kind: Group
  name: security-demo-developers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: developer
  apiGroup: rbac.authorization.k8s.io
```

Access entry의 그룹 이름과 RoleBinding subject가 일치해야 합니다. 이 Role은 security-demo 안에서 표시한 작업을 허용하지만 기존 다른 grant가 접근 범위를 넓힐 수 있습니다. Deployment·Job 생성자는 namespace의 Secret·PVC·ServiceAccount를 간접적으로 사용할 수 있으므로 Secret 직접 읽기 규칙이 없다는 사실만으로 tenant 경계가 보장되지는 않습니다. Tenant를 분리하고 admission·소유권 제어로 workload 신원·리소스 사용을 제한합니다.

별도 검토한 viewer는 namespace 범위 AmazonEKSViewPolicy association을 사용할 수도 있습니다. 추가 전에 기존 access policy를 확인하며 이 grant가 더 넓은 RBAC·다른 access policy 권한을 취소하지는 않습니다. `eks:namespaces`는 일반 kubectl 요청이 아닌 access policy association 요청을 필터링합니다.

**실제 로그인 검증:** 호출자는 cluster 조회와 승인된 역할 assume 권한이 있어야 합니다. 다음은 기본 context를 대체하지 않고 임시 kubeconfig를 만듭니다:

```bash
set -euo pipefail
umask 077
: "${CLUSTER_NAME:?Set the reviewed cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
: "${DEVELOPER_ROLE_ARN:?Set the intended IAM role ARN}"
review_dir=$(mktemp -d "${TMPDIR:-/tmp}/eks-login-check.XXXXXXXX")
trap 'rm -rf -- "$review_dir"' EXIT
aws eks update-kubeconfig --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --role-arn "$DEVELOPER_ROLE_ARN" --kubeconfig "$review_dir/config"
kubectl --kubeconfig "$review_dir/config" auth can-i list pods -n security-demo
kubectl --kubeconfig "$review_dir/config" auth can-i create jobs -n security-demo
kubectl --kubeconfig "$review_dir/config" auth can-i list pods -n another-team
```

의도한 grant와 결과를 비교하고 예상하지 못한 다른 namespace 권한을 조사합니다. `--as`는 impersonation·RBAC를 검사하며 IAM access policy 경로의 동작 증명이 아닙니다. 이 퀴즈에서 실제 IAM 로그인·Kubernetes 권한 시험은 실행하지 않았으며 로컬 증거는 schema·shell 검사와 mocked access entry 흐름입니다.

참고: [EKS access entry](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html), [EKS access policy](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html), [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/).

</details>

### 2. CONFIG_MAP 인증 모드에서 API_AND_CONFIG_MAP 또는 API로 전환할 때 올바른 설명은 무엇인가요?

- A) 언제든 이전 모드로 되돌릴 수 있는 스위치이므로 사전 검토가 필요 없다
- B) 자유롭게 되돌리는 스위치가 아니므로 관리자·노드 매핑을 보존하고 API-only 전에 신원·정책·노드·복구 경로를 검토한다
- C) 전환 전에 노드 역할이 빠진 짧은 예제로 aws-auth를 덮어써 정리한다
- D) API 모드로 바꾸면 기존 aws-auth 매핑이 access entry로 자동 이전되므로 확인할 것이 없다

<details>
<summary>정답 보기</summary>

**정답: B) 자유롭게 되돌리는 스위치가 아니므로 관리자·노드 매핑을 보존하고 API-only 전에 신원·정책·노드·복구 경로를 검토한다**

**설명:**

현재 authentication mode를 `describe-cluster`의 `accessConfig`로 조회하고, 이전 전에 관리자·노드 매핑을 보존합니다. CONFIG_MAP에서 API_AND_CONFIG_MAP/API로의 전환은 자유롭게 되돌리는 스위치가 아닙니다. 노드 역할이 빠진 짧은 예제로 aws-auth를 덮어쓰지 말고, API-only를 선택하기 전에 전체 신원·정책·노드·복구 경로를 검토합니다.

</details>

### 3. 일반 EKS cluster IAM role과 개발자 권한에 대한 설명으로 옳은 것은 무엇인가요?

- A) Cluster role은 `eks.amazonaws.com` 서비스를 신뢰하며, 개발자 역할에 AmazonEKSClusterPolicy를 붙여도 Kubernetes 앱 접근 권한은 생기지 않는다
- B) Cluster role은 개발자 IAM 사용자를 신뢰해야 kubectl을 사용할 수 있다
- C) 개발자 역할에 AmazonEKSClusterPolicy를 붙이면 모든 네임스페이스의 Kubernetes 권한이 생긴다
- D) CreateCluster는 resource ARN 범위를 지원하므로 클러스터 ARN으로만 제한하면 충분하다

<details>
<summary>정답 보기</summary>

**정답: A) Cluster role은 `eks.amazonaws.com` 서비스를 신뢰하며, 개발자 역할에 AmazonEKSClusterPolicy를 붙여도 Kubernetes 앱 접근 권한은 생기지 않는다**

**설명:**

일반 EKS cluster role의 신뢰 관계는 `eks.amazonaws.com` 서비스 Principal에 `sts:AssumeRole`을 허용하며, 이는 개발자의 권한 정책이 아닙니다. 생성 호출자는 선택한 구성의 작업 권한과 대상 역할의 PassRole 권한이 별도로 필요합니다. 현재 권한 참조에서 CreateCluster는 resource ARN 범위를 지원하지 않으므로 지원되는 request condition을 사용합니다. 개발자 역할에 AmazonEKSClusterPolicy를 연결해도 Kubernetes 앱 접근 권한이 생기지는 않습니다.

</details>

### 4. Access entry와 RBAC로 개발자 권한을 구성한 뒤 `kubectl auth can-i --as=...`로 확인한 결과는 무엇을 의미하나요?

- A) 실제 IAM 로그인과 access policy 경로가 모두 정상이라는 증거다
- B) Kubernetes impersonation·RBAC 검사 결과일 뿐 IAM access-policy 경로의 증거는 아니므로 의도한 실제 IAM 로그인으로도 검증해야 한다
- C) kubeconfig가 권한을 부여하므로 별도 검증이 필요 없다
- D) `--as` 결과는 RBAC와 무관하다

<details>
<summary>정답 보기</summary>

**정답: B) Kubernetes impersonation·RBAC 검사 결과일 뿐 IAM access-policy 경로의 증거는 아니므로 의도한 실제 IAM 로그인으로도 검증해야 한다**

**설명:**

`kubectl --as`는 Kubernetes impersonation과 RBAC를 검사하며 IAM access-policy 경로를 증명하지 않습니다. 변경 전파에 시간이 걸릴 수 있으므로 의도한 실제 IAM 로그인으로 검증합니다. Kubeconfig는 클러스터와 자격 증명 경로를 가리킬 뿐 자체적으로 권한을 부여하지 않습니다.

</details>

### 5. 네임스페이스 범위 AmazonEKSViewPolicy association과 `eks:namespaces` 조건에 대한 설명으로 옳은 것은 무엇인가요?

- A) View association을 추가하면 같은 주체의 더 넓은 기존 RBAC 권한이 취소된다
- B) `eks:namespaces`는 모든 kubectl API 호출을 네임스페이스로 필터링하는 IAM 조건이다
- C) 허용 권한은 합산되므로 View 추가가 더 넓은 기존 권한을 취소하지 않으며, `eks:namespaces`는 access-policy association 요청을 필터링하는 조건이다
- D) `eks:AccessKubernetesApi`는 kubectl용 일반 네임스페이스 RBAC 권한이다

<details>
<summary>정답 보기</summary>

**정답: C) 허용 권한은 합산되므로 View 추가가 더 넓은 기존 권한을 취소하지 않으며, `eks:namespaces`는 access-policy association 요청을 필터링하는 조건이다**

**설명:**

추가 전에 `list-associated-access-policies`로 현재 그룹·연결 정책을 조회합니다. View 추가는 더 넓은 RBAC·access-policy 권한을 취소하지 않습니다. `eks:namespaces` 조건은 access-policy association 요청을 필터링하며 kubectl API 호출의 범용 네임스페이스 필터가 아닙니다. `eks:AccessKubernetesApi`는 콘솔 조회 권한입니다.

</details>
