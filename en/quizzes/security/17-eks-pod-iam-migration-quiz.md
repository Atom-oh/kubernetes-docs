# IRSA and EKS Pod Identity Migration Quiz

> **Last Updated**: November 19, 2026

[Read the chapter and primary sources](../../security/17-eks-pod-iam-migration.md)

### 1. After moving some workloads to IRSA and Pod Identity, why can the ungranted `default/neighbor` Pod still read S3?

- A) The Pod Identity Agent hands credentials to every Pod
- B) The node role still has the application permission and the Pod can get node role credentials from IMDS
- C) The IRSA OIDC provider trusts the whole cluster
- D) The S3 bucket is public

<details>
<summary>Show Answer</summary>

**Answer: B) The node role still has the application permission and the Pod can get node role credentials from IMDS**

**Explanation:** With nothing injected, the SDK reaches the end of its credential chain, asks IMDS (169.254.169.254) and receives the node instance profile credentials. Adding IRSA or Pod Identity does not remove that path; you need to clean up the node role and block IMDS (Phase 4).

</details>

### 2. What is the effect of IMDSv2 required with `HttpPutResponseHopLimit=1`?

- A) The node itself can no longer use IMDS
- B) The token response does not reach Pods with their own network namespace, but hostNetwork Pods can still reach IMDS
- C) IMDS is blocked for all Pods, including hostNetwork Pods
- D) The Pod Identity Agent stops working

<details>
<summary>Show Answer</summary>

**Answer: B) The token response does not reach Pods with their own network namespace, but hostNetwork Pods can still reach IMDS**

**Explanation:** The PUT token response travels only as far as its IP TTL, so it never reaches a Pod one hop away. hostNetwork Pods share the node namespace and are not blocked. The Pod Identity Agent uses 169.254.170.23 and is unaffected by the hop limit.

</details>

### 3. Which `sub` and `aud` conditions are correct in an IRSA role trust policy?

- A) `sub = system:serviceaccount:<ns>:<sa>`, `aud = sts.amazonaws.com`
- B) `sub = <pod name>`, `aud = pods.eks.amazonaws.com`
- C) `sub = arn:aws:iam::<acct>:role/<node role>`, `aud = ec2.amazonaws.com`
- D) `sub = *`, `aud = *`

<details>
<summary>Show Answer</summary>

**Answer: A) `sub = system:serviceaccount:<ns>:<sa>`, `aud = sts.amazonaws.com`**

**Explanation:** STS verifies the JWT against the per-cluster OIDC provider and then evaluates `sub` and `aud` in the trust policy. Pin the namespace and SA with `StringEquals`; widening with `StringLike` and `*` lets other SAs take the role.

</details>

### 4. With Pod Identity, how does a Pod obtain credentials?

- A) Pod → STS `AssumeRoleWithWebIdentity`
- B) Pod → IMDS 169.254.169.254
- C) Pod → Pod Identity Agent on `169.254.170.23` → EKS Auth API `AssumeRoleForPodIdentity` → STS
- D) Pod → kube-apiserver → IAM

<details>
<summary>Show Answer</summary>

**Answer: C) Pod → Pod Identity Agent on `169.254.170.23` → EKS Auth API `AssumeRoleForPodIdentity` → STS**

**Explanation:** The SDK sends its token to `AWS_CONTAINER_CREDENTIALS_FULL_URI` (http://169.254.170.23/v1/credentials). The agent, a hostNetwork DaemonSet, calls the EKS Auth API with the node role, and EKS looks up the association and assumes the role.

</details>

### 5. Which IAM role trust policy is correct for Pod Identity?

- A) `Principal: { Federated: <OIDC provider ARN> }`, `sts:AssumeRoleWithWebIdentity`
- B) `Principal: { Service: pods.eks.amazonaws.com }`, `sts:AssumeRole` + `sts:TagSession`
- C) `Principal: { Service: ec2.amazonaws.com }`, `sts:AssumeRole`
- D) `Principal: { Service: eks.amazonaws.com }`, `sts:AssumeRole` only

<details>
<summary>Show Answer</summary>

**Answer: B) `Principal: { Service: pods.eks.amazonaws.com }`, `sts:AssumeRole` + `sts:TagSession`**

**Explanation:** The trust policy contains no cluster information, so the role can be reused across clusters. `sts:TagSession` is required because EKS attaches session tags. The association decides which SA may use the role.

</details>

### 6. If an SA has both an IRSA annotation and a Pod Identity association, which one does a typical AWS SDK use?

- A) Pod Identity, it always takes precedence
- B) IRSA, because the default chain evaluates web identity before container credentials
- C) Both fail and IMDS is used
- D) One is chosen at random

<details>
<summary>Show Answer</summary>

**Answer: B) IRSA, because the default chain evaluates web identity before container credentials**

**Explanation:** That is why an IRSA → Pod Identity switch only takes effect after creating the association, removing the annotation and restarting the Pods. Also remember that static key env vars override both.

</details>

### 7. Right after annotating an SA or creating an association, what must you do for running Pods?

- A) Nothing, it applies immediately
- B) Restart the kubelet
- C) Restart the Pods (`rollout restart`), because the webhook injects env vars and the token only at Pod creation
- D) Replace the nodes

<details>
<summary>Show Answer</summary>

**Answer: C) Restart the Pods (`rollout restart`), because the webhook injects env vars and the token only at Pod creation**

**Explanation:** The Pod Identity Webhook is a mutating admission webhook, so it changes only newly created Pods. Both switching and rolling back require a restart.

</details>

### 8. Which statement matches the chapter?

- A) Pod Identity supports Fargate and IRSA does not
- B) IRSA works on Fargate, and Pod Identity can implement ABAC with session tags such as `kubernetes-namespace`
- C) Pod Identity works on Kubernetes outside EKS as long as there is an OIDC issuer
- D) IRSA lets you reuse a role across clusters without changing the trust policy

<details>
<summary>Show Answer</summary>

**Answer: B) IRSA works on Fargate, and Pod Identity can implement ABAC with session tags such as `kubernetes-namespace`**

**Explanation:** Pod Identity depends on the agent on EC2 nodes, so it does not support Fargate and is EKS-only. In return, session tags like `${aws:PrincipalTag/kubernetes-namespace}` let one role allow only each namespace's resources. Pod Identity, not IRSA, is the one that needs no trust change for multi-cluster reuse.

</details>
