# EKS 集群访问身份验证测验

> **最后更新**：2026年11月21日

本测验用于检查你对 [EKS 集群访问身份验证：IAM 和访问条目](../../eks/05-eks-security-cluster-access.md) 的理解。

## 测验概览
- IAM 身份验证和 Kubernetes 授权
- EKS 集群角色和预置调用方
- 身份验证模式和访问条目
- 访问策略范围和验证

## 单选题

### 1. 对于 IAM 用户或角色，哪种 EKS 配置能正确结合身份验证和 Kubernetes 授权？

- A) 仅使用 IAM 管理权限
- B) 创建 RBAC 规则，但不配置该身份的身份验证路径
- C) 配置 IAM 集群访问，以及适当的 RBAC 和/或 EKS 访问策略
- D) 仅使用 API 端点网络限制

<details>
<summary>显示答案</summary>

**答案：C) 配置 IAM 集群访问，以及适当的 RBAC 和/或 EKS 访问策略**

**说明：**

IAM 会通过已配置的 EKS 访问路径验证预期的人类/自动化身份。Kubernetes RBAC 和 EKS 访问策略负责授权 Kubernetes 操作；两者授予的权限会叠加。网络限制属于另一层，不会取代授权。Pod 对 Kubernetes 的身份验证通常使用其 ServiceAccount 令牌；IRSA/Pod Identity 则会为工作负载提供 AWS 凭证。

EKS 集群服务角色和人类开发人员角色用途不同。向开发人员附加 AmazonEKSClusterPolicy 不会授予 Kubernetes 访问权限，而 DescribeCluster/ListClusters 权限或 kubeconfig 文件也不会授予工作负载权限。

**范围限定的实施方案：** 经授权的平台操作员为一个现有且已获批准的开发人员 IAM 角色准备以下命名空间和 RBAC。集群必须已支持访问条目。保留现有管理员/节点映射，并审查身份验证模式迁移；不要用示例 ConfigMap 覆盖 aws-auth。

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

访问条目中的组名必须与 RoleBinding 的 subject 匹配。此角色仅允许在 security-demo 中执行所列操作；其他现有授权可能会扩大访问范围。在该命名空间中创建 Deployments/Jobs，可能会间接使用 Secrets、PVC 和 ServiceAccounts，因此没有直接的 Secret 读取规则并不构成租户安全边界。应隔离租户，并通过准入和所有权控制来限制工作负载身份与资源使用。

经过单独审查的只读访问者也可以改为使用命名空间范围的 AmazonEKSViewPolicy 关联。添加之前，请检查现有访问策略；此策略不会撤销更广泛的 RBAC 或其他访问策略授予的权限。`eks:namespaces` 用于筛选访问策略关联请求，而不是一般的 kubectl 请求。

**验证实际登录：** 调用方必须能够发现集群并承担已批准的角色。此操作会创建临时 kubeconfig，而不会替换默认上下文：

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

请根据预期授权检查结果，并调查意外的跨命名空间权限。`--as` 测试的是模拟身份/RBAC，并不能证明 IAM 访问策略路径有效。本测验未执行实时 IAM 登录或 Kubernetes 授权测试；本地证据是 Schema/ shell 检查和模拟的访问条目流程。

参考资料：[EKS 访问条目](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)、[EKS 访问策略](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html)、[Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)。

</details>

### 2. 关于从 CONFIG_MAP 身份验证模式迁移到 API_AND_CONFIG_MAP 或 API，哪种说法正确？

- A) 不能随意回退；应保留管理员/节点映射并规划恢复路径
- B) 之后总能切换回去，因此无需事先审查即可切换模式
- C) 先用一个省略节点角色的简短示例 ConfigMap 覆盖 aws-auth
- D) API 模式会自动将所有 aws-auth 映射迁移为访问条目，因此可以跳过所有检查

<details>
<summary>显示答案</summary>

**答案：A) 不能随意回退；应保留管理员/节点映射并规划恢复路径**

**说明：**

通过 `describe-cluster` 的 `accessConfig` 检查当前身份验证模式，并在迁移前保留现有管理员/节点映射。从 CONFIG_MAP 迁移到 API_AND_CONFIG_MAP/API 并不是可以随意回退的切换。不要用省略节点角色的简短示例覆盖 aws-auth；在选择仅使用 API 的模式前，应审查所有身份、策略、节点，并规划恢复路径。

</details>

### 3. 关于标准 EKS 集群 IAM 角色和开发人员权限，哪种说法正确？

- A) 在 kubectl 能正常工作之前，集群角色必须信任开发人员 IAM 用户
- B) 在开发人员角色上附加 AmazonEKSClusterPolicy 会授予对每个命名空间的访问权限
- C) CreateCluster 支持按资源 ARN 限定范围，因此仅限定为集群 ARN 就足够了
- D) 集群角色信任 `eks.amazonaws.com` 服务，而不是开发人员身份

<details>
<summary>显示答案</summary>

**答案：D) 集群角色信任 `eks.amazonaws.com` 服务，而不是开发人员身份**

**说明：**

标准 EKS 集群角色的信任关系允许服务主体 `eks.amazonaws.com` 执行 `sts:AssumeRole`；它不是开发人员的权限策略。预置调用方需要根据所选配置分别具备相应操作权限，并拥有对预期角色执行 PassRole 的权限。当前授权参考列出的 CreateCluster 不支持资源 ARN 范围限定，因此应在此处使用受支持的请求条件。向开发人员角色附加 AmazonEKSClusterPolicy 不会授予 Kubernetes 应用访问权限。

</details>

### 4. 配置开发人员的访问条目和 RBAC 后，`kubectl auth can-i --as=...` 的结果说明什么？

- A) 证明真实 IAM 登录和访问策略路径都有效
- B) 只能说明 Kubernetes 模拟身份/RBAC 有效，不能证明 IAM 访问策略路径有效
- C) 无需进行其他操作，因为 kubeconfig 本身就授予了这些权限
- D) 只能说明 IAM 策略评估结果，因为 `--as` 会完全绕过 RBAC

<details>
<summary>显示答案</summary>

**答案：B) 只能说明 Kubernetes 模拟身份/RBAC 有效，不能证明 IAM 访问策略路径有效**

**说明：**

`kubectl --as` 测试的是 Kubernetes 模拟身份和 RBAC，而不能证明 IAM 访问策略路径有效。更新可能需要一段时间才能传播，因此应使用实际预期的 IAM 登录身份进行测试。kubeconfig 会为客户端指定集群和凭证机制；它本身不会授予任何权限。

</details>

### 5. 关于命名空间范围的 AmazonEKSViewPolicy 关联和 `eks:namespaces` 条件，哪种说法正确？

- A) 添加 View 会撤销主体已有的更广泛 RBAC 授权
- B) `eks:namespaces` 会将每个 kubectl API 调用限制在所列命名空间内
- C) `eks:AccessKubernetesApi` 是适用于 kubectl 的通用命名空间 RBAC 权限
- D) 添加 View 不会撤销任何权限；`eks:namespaces` 用于筛选关联请求

<details>
<summary>显示答案</summary>

**答案：D) 添加 View 不会撤销任何权限；`eks:namespaces` 用于筛选关联请求**

**说明：**

添加授权之前，请使用 `list-associated-access-policies` 检查条目现有的组和关联策略。添加 View 不会撤销更广泛的 RBAC/访问策略授权。`eks:namespaces` 条件用于筛选访问策略关联请求；它不是适用于 kubectl API 调用的通用命名空间筛选器。`eks:AccessKubernetesApi` 是控制台查看权限。

</details>
