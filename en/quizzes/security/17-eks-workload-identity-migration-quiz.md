# EKS workload IAM migration quiz

> **Last Updated**: November 21, 2026

[Read the workbook and live demo](../../security/17-eks-workload-identity-migration.md)

### 1. What is the main problem with attaching an app's S3 permission to the node IAM role?

- A) S3 requests get slower
- B) Every Pod on that node that can reach IMDS uses the same permission
- C) The node can no longer join the cluster
- D) The S3 bucket becomes public

<details>
<summary>Show Answer</summary>

**Answer: B) Every Pod on that node that can reach IMDS uses the same permission**

**Explanation:** The node role is attached to the whole node through the instance profile. With a hop limit of 2 or more, ordinary Pods can get node-role credentials through IMDSv2. CloudTrail records only the node instance session, so workloads are hard to tell apart.

</details>

### 2. In the AWS SDK default credential chain, where do the IRSA and Pod Identity providers sit relative to IMDS?

- A) IMDS comes first
- B) IRSA (web identity) and Pod Identity (container provider) both come before IMDS
- C) The order is random
- D) Only Pod Identity comes before IMDS

<details>
<summary>Show Answer</summary>

**Answer: B) IRSA (web identity) and Pod Identity (container provider) both come before IMDS**

**Explanation:** Environment keys, the web identity token and the container credential provider precede IMDS. A new Pod into which EKS injected the variables uses the new role without code changes; a Pod with nothing injected falls through to the node role from IMDS.

</details>

### 3. Why can STS trust the projected token in IRSA?

- A) The token contains IAM access keys
- B) The cluster issuer is registered as an IAM OIDC provider, and the role trust policy checks `aud` and `sub`
- C) The Pod Identity Agent signs the token
- D) The node role calls STS on the Pod's behalf

<details>
<summary>Show Answer</summary>

**Answer: B) The cluster issuer is registered as an IAM OIDC provider, and the role trust policy checks `aud` and `sub`**

**Explanation:** STS `AssumeRoleWithWebIdentity` verifies the token signature with the issuer keys registered through the OIDC provider and checks the trust conditions: `aud` is `sts.amazonaws.com` and `sub` is `system:serviceaccount:<namespace>:<serviceaccount>`.

</details>

### 4. With Pod Identity, which permission must stay on the node role?

- A) The app's S3 read permission
- B) `sts:AssumeRoleWithWebIdentity`
- C) `eks-auth:AssumeRoleForPodIdentity` for the agent to call EKS Auth (part of `AmazonEKSWorkerNodePolicy`)
- D) None at all

<details>
<summary>Show Answer</summary>

**Answer: C) `eks-auth:AssumeRoleForPodIdentity` for the agent to call EKS Auth (part of `AmazonEKSWorkerNodePolicy`)**

**Explanation:** The Pod Identity Agent calls EKS Auth with this node-role permission. The app's business permission belongs on the Pod Identity role named in the association.

</details>

### 5. In the demo's `diff`, which claim distinguished the IRSA token from the Pod Identity token?

- A) `iss`
- B) `aud`
- C) `exp`
- D) They were identical

<details>
<summary>Show Answer</summary>

**Answer: B) `aud`**

**Explanation:** Both are ServiceAccount tokens signed by the same cluster issuer. The IRSA token's audience is `sts.amazonaws.com`; the Pod Identity token's is `pods.eks.amazonaws.com`. `sub` differs per ServiceAccount.

</details>

### 6. Which method lets one IAM role serve ten new clusters without trust policy changes?

- A) IRSA
- B) EKS Pod Identity
- C) Neither needs changes
- D) Both need per-cluster edits

<details>
<summary>Show Answer</summary>

**Answer: B) EKS Pod Identity**

**Explanation:** A Pod Identity role trusts only `pods.eks.amazonaws.com`; associations and session tags set the cluster scope. IRSA needs an OIDC provider and a trust statement per cluster, and the default 2,048-character trust policy typically fits about four bindings.

</details>

### 7. A Pod running on Fargate needs a workload role. Which method do you use?

- A) EKS Pod Identity
- B) IRSA
- C) The node role
- D) Neither works

<details>
<summary>Show Answer</summary>

**Answer: B) IRSA**

**Explanation:** EKS Pod Identity supports only Linux EC2 nodes in EKS. Use IRSA on Fargate, Windows EC2 nodes, Outposts and EKS Anywhere.

</details>

### 8. You created an association and rolled out immediately, but the new Pod still uses the node role. What is the most likely cause?

- A) The bucket policy denied it
- B) The association had not yet reached Pod admission, so nothing was injected
- C) The Pod Identity Agent blocked IMDS
- D) An IRSA annotation is also required

<details>
<summary>Show Answer</summary>

**Answer: B) The association had not yet reached Pod admission, so nothing was injected**

**Explanation:** Associations are eventually consistent and can take several seconds. In the demo's first rehearsal a rollout right after creation got no injection; in the second, injection took 5 seconds to appear. Check the Pod template with `kubectl create --dry-run=server` before rolling out.

</details>

### 9. You add a Pod Identity association to a ServiceAccount that already has an IRSA annotation, then create a new Pod. Which credentials does the new Pod use?

- A) Pod Identity: the webhook injects only the Pod Identity variables
- B) IRSA: the web identity provider comes first in the chain
- C) They alternate per request
- D) The Pod fails to start because of the conflict

<details>
<summary>Show Answer</summary>

**Answer: A) Pod Identity: the webhook injects only the Pod Identity variables**

**Explanation:** With an association, the EKS webhook injects only `AWS_CONTAINER_CREDENTIALS_FULL_URI` and `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE` into new Pods, not the IRSA variables, as the dry-run on the demo cluster showed. Chain order (B) only matters when both sets are present; Pods created before the association keep using IRSA until recreated.

</details>

### 10. Right after you remove the node role's S3 policy, the legacy Pod's read is denied. Can you declare the migration done?

- A) Yes, a single denial is final
- B) No, IAM changes are eventually consistent and results can mix for minutes, so keep watching
- C) Yes, once the node restarts
- D) No, you must delete the node role

<details>
<summary>Show Answer</summary>

**Answer: B) No, IAM changes are eventually consistent and results can mix for minutes, so keep watching**

**Explanation:** In the demo the legacy Pod was denied after 13 seconds, yet two more allowed reads appeared about 4.5 minutes later. Watch for several minutes including scheduled runs, and keep an exact copy of the policy for rollback.

</details>
