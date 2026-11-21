# EKS Pod Identity Quiz

> **Last Updated**: November 21, 2026

This quiz checks your understanding of [EKS Pod Identity](../../eks/05-eks-security-pod-identity.md).

## Quiz Overview
- What an association does
- Agent and credential flow
- Role trust and session tags
- Cross-account and caching
- Coexistence with and migration from IRSA

## Multiple Choice Questions

### 1. Which statement about an EKS Pod Identity association is correct?

- A) Creating it automatically creates the ServiceAccount in the namespace
- B) It grants Kubernetes RBAC permissions along with the IAM role
- C) It is stored in Kubernetes as an annotation on the ServiceAccount object itself
- D) It maps a cluster, namespace and ServiceAccount to an IAM role in the EKS API

<details>
<summary>Show Answer</summary>

**Answer: D) It maps a cluster, namespace and ServiceAccount to an IAM role in the EKS API**

**Explanation:**

An association is a cluster/namespace/ServiceAccount to IAM role mapping stored in the EKS API. It does not create the ServiceAccount, grant Kubernetes RBAC permissions, or create the IAM role or agent. The page's example checks existing associations with `list-pod-identity-associations` before creating one so it does not overwrite another owner's configuration.

</details>

### 2. How does the AWS SDK in a newly created, associated Pod obtain Pod Identity credentials?

- A) The SDK calls the node agent, which gets the credentials from EKS Auth
- B) The agent transparently intercepts and signs every AWS request from the Pod
- C) The SDK calls STS AssumeRoleWithWebIdentity with a web-identity token
- D) The SDK uses node IAM role credentials that it receives from IMDSv2

<details>
<summary>Show Answer</summary>

**Answer: A) The SDK calls the node agent, which gets the credentials from EKS Auth**

**Explanation:**

For an associated new Pod, EKS injects a token with audience `pods.eks.amazonaws.com`, a token-file environment variable and a container credentials URI. The SDK calls the agent endpoint, commonly `169.254.170.23/v1/credentials`, and the agent calls AssumeRoleForPodIdentity on EKS Auth and returns the credentials to the SDK. It is not a request interceptor; the application still calls AWS services directly with its credentials.

</details>

### 3. Which statement about the Pod Identity role trust example is correct?

- A) It names the cluster's IAM OIDC provider as the `Federated` principal in the trust
- B) Allowing only `sts:AssumeRoleWithWebIdentity` is enough for Pod Identity
- C) It trusts `pods.eks.amazonaws.com` for AssumeRole/TagSession, scoped by tags
- D) Trusting `pods.eks.amazonaws.com` with no conditions is least privilege

<details>
<summary>Show Answer</summary>

**Answer: C) It trusts `pods.eks.amazonaws.com` for AssumeRole/TagSession, scoped by tags**

**Explanation:**

The example trust policy allows `sts:AssumeRole` and `sts:TagSession` for the `pods.eks.amazonaws.com` service principal with `aws:RequestTag/eks-cluster-arn`, `kubernetes-namespace` and `kubernetes-service-account` conditions. These conditions rely on the default session tags, so disabling tags requires reviewing them. The caller that creates the association also needs `iam:PassRole` for the intended role.

</details>

### 4. Which statement about reaching resources in another account with Pod Identity is correct?

- A) Attach any role from the other account directly as the association role
- B) Keep the association role in the cluster account and chain to a target role
- C) Pod Identity has no cross-account support, so always switch those workloads to IRSA
- D) With a target role, association changes reset the credential cache at once

<details>
<summary>Show Answer</summary>

**Answer: B) Keep the association role in the cluster account and chain to a target role**

**Explanation:**

The association role must be in the EKS cluster account. An optional target IAM role can be in another account; Pod Identity chains from the same-account role to that target with both trust and assume-role permissions configured. The current guide documents cached credentials lasting 6 hours without a target role and 59 minutes with one, and association changes do not reset that cache. Recreating Pods can obtain the new configuration sooner.

</details>

### 5. When one ServiceAccount has both an IRSA annotation and a Pod Identity association, how does EKS inject credentials?

- A) New Pods get only Pod Identity variables; running Pods keep their IRSA ones
- B) New Pods get both sets of variables, and the SDK picks one of them at random
- C) Creating the association immediately rewrites running Pods' environment
- D) The IRSA annotation always wins, so new Pods ignore the association

<details>
<summary>Show Answer</summary>

**Answer: A) New Pods get only Pod Identity variables; running Pods keep their IRSA ones**

**Explanation:**

As verified in [Migrate EKS node IAM permissions to IRSA and Pod Identity](../../security/17-eks-workload-identity-migration.md#irsa-and-pod-identity-compared), with both settings the EKS webhook injects only `AWS_CONTAINER_CREDENTIALS_FULL_URI` and `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE` into new Pods. Running Pods keep their IRSA variables until recreated, so switch with a controlled rollout and remove the unused annotation. A get-caller-identity result showing the same role cannot distinguish the two mechanisms, so check the injected environment variable names.

</details>
