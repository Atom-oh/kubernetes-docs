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

- A) Creating an association creates the ServiceAccount automatically
- B) An association also grants Kubernetes RBAC permissions
- C) An association maps a cluster, namespace and ServiceAccount to an IAM role; it neither creates the ServiceAccount nor grants RBAC permissions
- D) An association is stored as a ServiceAccount annotation

<details>
<summary>Show Answer</summary>

**Answer: C) An association maps a cluster, namespace and ServiceAccount to an IAM role; it neither creates the ServiceAccount nor grants RBAC permissions**

**Explanation:**

An association is a cluster/namespace/ServiceAccount to IAM role mapping stored in the EKS API. It does not create the ServiceAccount, grant Kubernetes RBAC permissions, or create the IAM role or agent. The page's example checks existing associations with `list-pod-identity-associations` before creating one so it does not overwrite another owner's configuration.

</details>

### 2. How does the AWS SDK in a newly created, associated Pod obtain Pod Identity credentials?

- A) The agent transparently intercepts every AWS request from the Pod and signs it
- B) The SDK calls the agent endpoint (commonly 169.254.170.23/v1/credentials); the agent calls AssumeRoleForPodIdentity on EKS Auth and makes the credentials available to the SDK
- C) The SDK calls STS AssumeRoleWithWebIdentity directly with a web-identity token
- D) The SDK receives node role credentials from IMDSv2

<details>
<summary>Show Answer</summary>

**Answer: B) The SDK calls the agent endpoint (commonly 169.254.170.23/v1/credentials); the agent calls AssumeRoleForPodIdentity on EKS Auth and makes the credentials available to the SDK**

**Explanation:**

For an associated new Pod, EKS injects a token with audience `pods.eks.amazonaws.com`, a token-file environment variable and a container credentials URI. The SDK calls the agent endpoint, and the agent calls AssumeRoleForPodIdentity on EKS Auth and returns the credentials to the SDK. It is not a request interceptor; the application still calls AWS services directly with its credentials.

</details>

### 3. Which statement about the Pod Identity role trust example is correct?

- A) It names the IAM OIDC provider as the `Federated` principal
- B) It allows `sts:AssumeRole` and `sts:TagSession` for `pods.eks.amazonaws.com` and restricts cluster, namespace and ServiceAccount with `aws:RequestTag/...` conditions, so disabling session tags requires reviewing those conditions
- C) Allowing only `sts:AssumeRoleWithWebIdentity` is sufficient
- D) Trusting `pods.eks.amazonaws.com` without conditions is least privilege

<details>
<summary>Show Answer</summary>

**Answer: B) It allows `sts:AssumeRole` and `sts:TagSession` for `pods.eks.amazonaws.com` and restricts cluster, namespace and ServiceAccount with `aws:RequestTag/...` conditions, so disabling session tags requires reviewing those conditions**

**Explanation:**

The example trust policy allows `sts:AssumeRole` and `sts:TagSession` for the `pods.eks.amazonaws.com` service principal with `aws:RequestTag/eks-cluster-arn`, `kubernetes-namespace` and `kubernetes-service-account` conditions. These conditions rely on the default session tags, so disabling tags requires reviewing them. The caller that creates the association also needs `iam:PassRole` for the intended role.

</details>

### 4. Which statement about reaching resources in another account with Pod Identity is correct?

- A) Attach an arbitrary role from the other account directly as the association role
- B) Keep the association role in the EKS cluster account and chain to an optional target IAM role in the other account, with trust and assume-role permissions on both sides
- C) Pod Identity cannot do cross-account access, so always use IRSA
- D) With a target role, association changes reset the credential cache immediately

<details>
<summary>Show Answer</summary>

**Answer: B) Keep the association role in the EKS cluster account and chain to an optional target IAM role in the other account, with trust and assume-role permissions on both sides**

**Explanation:**

The association role must be in the EKS cluster account. An optional target IAM role can be in another account; Pod Identity chains from the same-account role to that target with both trust and assume-role permissions configured. The current guide documents cached credentials lasting 6 hours without a target role and 59 minutes with one, and association changes do not reset that cache. Recreating Pods can obtain the new configuration sooner.

</details>

### 5. When one ServiceAccount has both an IRSA annotation and a Pod Identity association, how does EKS inject credentials?

- A) New Pods receive both IRSA and Pod Identity variables and the SDK picks one at random
- B) New Pods receive only the Pod Identity variables, not the IRSA ones, and running Pods keep their IRSA variables until they are recreated
- C) Creating the association immediately rewrites the environment of running Pods
- D) The IRSA annotation always wins, so the association is ignored

<details>
<summary>Show Answer</summary>

**Answer: B) New Pods receive only the Pod Identity variables, not the IRSA ones, and running Pods keep their IRSA variables until they are recreated**

**Explanation:**

As verified in [Migrate EKS node IAM permissions to IRSA and Pod Identity](../../security/17-eks-workload-identity-migration.md#irsa-and-pod-identity-compared), with both settings the EKS webhook injects only `AWS_CONTAINER_CREDENTIALS_FULL_URI` and `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE` into new Pods. Running Pods keep their IRSA variables until recreated, so switch with a controlled rollout and remove the unused annotation. A get-caller-identity result showing the same role cannot distinguish the two mechanisms, so check the injected environment variable names.

</details>
