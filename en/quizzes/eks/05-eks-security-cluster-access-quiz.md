# EKS Cluster Access Authentication Quiz

> **Last Updated**: November 21, 2026

This quiz checks your understanding of [EKS Cluster Access Authentication: IAM and Access Entries](../../eks/05-eks-security-cluster-access.md).

## Quiz Overview
- IAM authentication and Kubernetes authorization
- EKS cluster role and provisioning caller
- Authentication mode and access entries
- Access policy scope and verification

## Multiple Choice Questions

### 1. For an IAM user or role, which EKS setup correctly combines identity authentication and Kubernetes authorization?

- A) Use only IAM management permissions
- B) Create RBAC rules without configuring the identity’s authentication path
- C) Configure IAM cluster access plus appropriate RBAC and/or EKS access policies
- D) Use only API endpoint network restrictions

<details>
<summary>Show Answer</summary>

**Answer: C) Configure IAM cluster access plus appropriate RBAC and/or EKS access policies**

**Explanation:**

IAM authenticates the intended human/automation identity through the configured EKS access path. Kubernetes RBAC and EKS access policies authorize Kubernetes operations; their grants are additive. Network restrictions are another layer and do not replace authorization. Pod-to-Kubernetes authentication normally uses its ServiceAccount token; IRSA/Pod Identity instead supplies workload AWS credentials.

An EKS cluster service role and a human developer role have different purposes. Attaching AmazonEKSClusterPolicy to the developer does not grant Kubernetes access, and DescribeCluster/ListClusters permissions or a kubeconfig file do not grant workload permissions.

**Scoped implementation:** an authorized platform operator prepares the namespace and RBAC below for an existing approved developer IAM role. The cluster must already support access entries. Preserve existing administrator/node mappings and review authentication-mode migration; do not overwrite aws-auth with a sample ConfigMap.

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

The group name in the access entry must match the RoleBinding subject. This role permits the listed operations only in security-demo; other existing grants can broaden access. Creating Deployments/Jobs can indirectly use Secrets, PVCs and ServiceAccounts in that namespace, so the absence of a direct Secret-read rule is not a tenant security boundary. Separate tenants and constrain workload identity/resource use through admission and ownership controls.

A separately reviewed viewer can instead use a namespace-scoped AmazonEKSViewPolicy association. Inspect existing access policies before adding it; it does not revoke broader RBAC or other access-policy grants. `eks:namespaces` filters access-policy association requests, not general kubectl requests.

**Validate the actual login:** the caller must be able to discover the cluster and assume the approved role. This creates a temporary kubeconfig rather than replacing the default context:

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

Inspect the results against the intended grants and investigate unexpected cross-namespace permission. `--as` tests impersonation/RBAC and does not establish that the IAM access-policy path works. No live IAM login or Kubernetes authorization test was executed for this quiz; schema/shell checks and mocked access-entry flows are the local evidence.

References: [EKS access entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html), [EKS access policies](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html), [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/).

</details>

### 2. Which statement about moving from the CONFIG_MAP authentication mode to API_AND_CONFIG_MAP or API is correct?

- A) It is not freely reversible; preserve admin/node mappings and plan a recovery path
- B) It can always be flipped back later, so switch modes without any prior review
- C) Overwrite aws-auth first with a short sample ConfigMap that omits the node roles
- D) API mode auto-migrates every aws-auth mapping to access entries, so skip all checks

<details>
<summary>Show Answer</summary>

**Answer: A) It is not freely reversible; preserve admin/node mappings and plan a recovery path**

**Explanation:**

Inspect the current authentication mode in `describe-cluster`'s `accessConfig` and preserve existing administrator/node mappings before migration. Moving from CONFIG_MAP to API_AND_CONFIG_MAP/API is not a freely reversible switch. Do not overwrite aws-auth with a short sample that omits node roles; review all identities, policies, nodes and a recovery path before choosing API-only mode.

</details>

### 3. Which statement about the standard EKS cluster IAM role and developer permissions is correct?

- A) The cluster role must trust the developer IAM user before kubectl can work
- B) AmazonEKSClusterPolicy on a developer role grants access to every namespace
- C) CreateCluster supports resource-ARN scoping, so scoping to the cluster ARN alone suffices
- D) The cluster role trusts the `eks.amazonaws.com` service, not developer identities

<details>
<summary>Show Answer</summary>

**Answer: D) The cluster role trusts the `eks.amazonaws.com` service, not developer identities**

**Explanation:**

The standard EKS cluster role's trust relationship allows `sts:AssumeRole` for the `eks.amazonaws.com` service principal; it is not the developer's permissions policy. The provisioning caller separately needs the actions for the selected configuration and PassRole for the intended role. The current authorization reference lists CreateCluster without resource-ARN scoping, so use supported request conditions there. Attaching AmazonEKSClusterPolicy to a developer role does not grant Kubernetes application access.

</details>

### 4. After configuring a developer's access entry and RBAC, what does a `kubectl auth can-i --as=...` result tell you?

- A) Proof that both the real IAM login and the access-policy path work
- B) Only Kubernetes impersonation/RBAC, not proof of the IAM access-policy path
- C) Nothing extra is needed, because the kubeconfig itself grants the permissions
- D) Only the IAM policy evaluation, since `--as` bypasses RBAC entirely

<details>
<summary>Show Answer</summary>

**Answer: B) Only Kubernetes impersonation/RBAC, not proof of the IAM access-policy path**

**Explanation:**

`kubectl --as` tests Kubernetes impersonation and RBAC rather than proving the IAM access-policy path. Updates can take time to propagate, so test with the actual intended IAM login. A kubeconfig points the client to a cluster and credential mechanism; it grants no permissions by itself.

</details>

### 5. Which statement about a namespace-scoped AmazonEKSViewPolicy association and the `eks:namespaces` condition is correct?

- A) Adding View revokes the principal's broader existing RBAC grants
- B) `eks:namespaces` limits every kubectl API call to the listed namespaces
- C) `eks:AccessKubernetesApi` is a general namespace RBAC permission for kubectl
- D) Adding View revokes nothing; `eks:namespaces` filters association requests

<details>
<summary>Show Answer</summary>

**Answer: D) Adding View revokes nothing; `eks:namespaces` filters association requests**

**Explanation:**

Inspect the entry's current groups and associated policies with `list-associated-access-policies` before adding the grant. Adding View does not revoke broader RBAC/access-policy grants. The `eks:namespaces` condition filters access-policy association requests; it is not a general namespace filter on kubectl API calls. `eks:AccessKubernetesApi` is a console-view permission.

</details>
