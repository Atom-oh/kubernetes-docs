# IRSA and the OIDC Provider Quiz

> **Last Updated**: November 21, 2026

This quiz checks your understanding of [IRSA and the OIDC Provider](../../eks/05-eks-security-irsa-oidc.md).

## Quiz Overview
- Cluster OIDC issuer and IAM OIDC provider
- IRSA token exchange
- Role trust conditions
- Discovery/JWKS and key rotation

## Multiple Choice Questions

### 1. An EKS cluster publishes an OIDC issuer and public signing keys. What else does IRSA need before a workload can assume a role?

- A) Nothing more; the issuer endpoint alone authorizes role assumption
- B) An external OIDC identity provider associated for Kubernetes user login
- C) An IAM OIDC provider, a role with matching trust and a compatible SDK
- D) The workload's target S3 permissions added to the node IAM role

<details>
<summary>Show Answer</summary>

**Answer: C) An IAM OIDC provider, a role with matching trust and a compatible SDK**

**Explanation:**

The cluster OIDC issuer endpoint that EKS publishes does not by itself create an IAM OIDC provider or authorize role assumption. IRSA needs the intended IAM OIDC provider in the role account, a role trusting it with the correct issuer/subject/audience conditions, and a compatible SDK. An external OIDC provider for Kubernetes user login is separate from IRSA.

</details>

### 2. With IRSA, which API does the SDK call to exchange the projected web-identity token for temporary AWS credentials?

- A) EKS Auth AssumeRoleForPodIdentity
- B) STS AssumeRoleWithWebIdentity
- C) IMDSv2 instance profile credentials
- D) STS GetSessionToken

<details>
<summary>Show Answer</summary>

**Answer: B) STS AssumeRoleWithWebIdentity**

**Explanation:**

The IRSA webhook adds a projected token and role configuration to an eligible Pod, and the SDK exchanges the token with STS using AssumeRoleWithWebIdentity. STS validates the issuer, signature, token and role trust, then returns temporary credentials. AssumeRoleForPodIdentity is the EKS Auth API that the Pod Identity agent calls. Kubernetes rotates the projected token and the SDK refreshes AWS credentials on different lifetimes.

</details>

### 3. In the scoped IRSA trust example, which conditions restrict the role to the `security-demo/irsa-reader` ServiceAccount?

- A) An `aws:RequestTag/kubernetes-service-account` session-tag condition
- B) Setting `Principal.Service` to `pods.eks.amazonaws.com`
- C) Naming the IAM role exactly after the ServiceAccount
- D) StringEquals conditions on `<issuer>:sub` and `<issuer>:aud`

<details>
<summary>Show Answer</summary>

**Answer: D) StringEquals conditions on `<issuer>:sub` and `<issuer>:aud`**

**Explanation:**

An IRSA role uses the IAM OIDC provider as its `Federated` principal and allows `sts:AssumeRoleWithWebIdentity`. StringEquals conditions prefixed by the complete issuer hostname/path bind the ServiceAccount and audience: `:sub` is `system:serviceaccount:security-demo:irsa-reader` and `:aud` is `sts.amazonaws.com`. `aws:RequestTag/...` conditions and `pods.eks.amazonaws.com` belong to Pod Identity trust. A role may trust several explicitly allowed ServiceAccounts or issuers; IRSA does not enforce one role per ServiceAccount.

</details>

### 4. When you build a validator that fetches the cluster OIDC discovery document and JWKS to verify tokens, which statement is correct?

- A) Cache keys per Cache-Control and handle key rotation and unknown kid values
- B) Fetch the JWKS once, hard-code it in the validator and reuse it forever
- C) Treat a successful JWKS fetch as proof that the token signature was validated
- D) Skip comparing the discovery document's issuer with the cluster issuer

<details>
<summary>Show Answer</summary>

**Answer: A) Cache keys per Cache-Control and handle key rotation and unknown kid values**

**Explanation:**

The page's diagnostic script fetches the public discovery/JWKS and checks the discovery issuer and HTTPS scheme; it validates neither a workload token signature nor IAM permissions. Automated validators must cache keys according to Cache-Control and handle signing-key rotation and unknown kid values using a reviewed JWT library. EKS rotates its OIDC signing key every seven days.

</details>

### 5. How can a validator without internet egress reach the cluster OIDC discovery document and JWKS?

- A) Create the EKS management API interface endpoint, which also serves OIDC
- B) Temporarily open 0.0.0.0/0 egress in the security group when needed
- C) Use the `oidc-eks` PrivateLink interface endpoint for discovery and JWKS
- D) Prepare no network path at all, because IRSA never needs the JWKS

<details>
<summary>Show Answer</summary>

**Answer: C) Use the `oidc-eks` PrivateLink interface endpoint for discovery and JWKS**

**Explanation:**

Current EKS supports a PrivateLink interface endpoint for cluster OIDC discovery/JWKS, `com.amazonaws.region-code.oidc-eks`, for validators without internet egress. Verify that endpoint's Region/DNS requirements; the EKS management API endpoint is a different service.

</details>
