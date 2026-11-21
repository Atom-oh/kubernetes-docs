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

- A) Nothing; the issuer endpoint alone authorizes role assumption
- B) An IAM OIDC provider in the role account, a role whose trust has the correct issuer/subject/audience conditions, and a compatible SDK
- C) An external OIDC identity provider associated for Kubernetes user login
- D) The target S3 permissions on the node IAM role

<details>
<summary>Show Answer</summary>

**Answer: B) An IAM OIDC provider in the role account, a role whose trust has the correct issuer/subject/audience conditions, and a compatible SDK**

**Explanation:**

The cluster OIDC issuer endpoint that EKS publishes does not by itself create an IAM OIDC provider or authorize role assumption. IRSA needs the intended IAM OIDC provider in the role account, a role trusting it with the correct issuer/subject/audience conditions, and a compatible SDK. An external OIDC provider for Kubernetes user login is separate from IRSA.

</details>

### 2. With IRSA, which API does the SDK call to exchange the projected web-identity token for temporary AWS credentials?

- A) STS AssumeRoleWithWebIdentity
- B) EKS Auth AssumeRoleForPodIdentity
- C) Instance profile credentials from IMDSv2
- D) STS GetSessionToken

<details>
<summary>Show Answer</summary>

**Answer: A) STS AssumeRoleWithWebIdentity**

**Explanation:**

The IRSA webhook adds a projected token and role configuration to an eligible Pod, and the SDK exchanges the token with STS using AssumeRoleWithWebIdentity. STS validates the issuer, signature, token and role trust, then returns temporary credentials. AssumeRoleForPodIdentity is the EKS Auth API that the Pod Identity agent calls. Kubernetes rotates the projected token and the SDK refreshes AWS credentials on different lifetimes.

</details>

### 3. In the scoped IRSA trust example, which conditions restrict the role to the `security-demo/irsa-reader` ServiceAccount?

- A) An `aws:RequestTag/kubernetes-service-account` condition
- B) StringEquals conditions where `<issuer>:sub` is `system:serviceaccount:security-demo:irsa-reader` and `<issuer>:aud` is `sts.amazonaws.com`
- C) Setting `Principal.Service` to `pods.eks.amazonaws.com`
- D) Naming the IAM role after the ServiceAccount

<details>
<summary>Show Answer</summary>

**Answer: B) StringEquals conditions where `<issuer>:sub` is `system:serviceaccount:security-demo:irsa-reader` and `<issuer>:aud` is `sts.amazonaws.com`**

**Explanation:**

An IRSA role uses the IAM OIDC provider as its `Federated` principal, allows `sts:AssumeRoleWithWebIdentity`, and scopes the ServiceAccount and audience with `:sub` and `:aud` conditions prefixed by the complete issuer hostname/path. `aws:RequestTag/...` conditions and `pods.eks.amazonaws.com` belong to Pod Identity trust. A role may trust several explicitly allowed ServiceAccounts or issuers; IRSA does not enforce one role per ServiceAccount.

</details>

### 4. When you build a validator that fetches the cluster OIDC discovery document and JWKS to verify tokens, which statement is correct?

- A) Fetch the JWKS once and hard-code it
- B) A successful JWKS fetch means the workload token signature was validated
- C) EKS rotates its OIDC signing key every seven days, so cache keys according to Cache-Control and handle rotation and unknown kid values with a reviewed JWT library
- D) The discovery document's issuer does not need checking

<details>
<summary>Show Answer</summary>

**Answer: C) EKS rotates its OIDC signing key every seven days, so cache keys according to Cache-Control and handle rotation and unknown kid values with a reviewed JWT library**

**Explanation:**

The page's diagnostic script fetches the public discovery/JWKS and checks the discovery issuer and HTTPS scheme; it validates neither a workload token signature nor IAM permissions. Automated validators must cache keys according to Cache-Control and handle signing-key rotation and unknown kid values using a reviewed JWT library. EKS rotates its OIDC signing key every seven days.

</details>

### 5. How can a validator without internet egress reach the cluster OIDC discovery document and JWKS?

- A) The EKS management API interface endpoint also serves OIDC discovery
- B) Use the `com.amazonaws.region-code.oidc-eks` PrivateLink interface endpoint and verify its Region/DNS requirements
- C) Temporarily open 0.0.0.0/0 egress in the security group
- D) IRSA never needs the JWKS, so no path is required

<details>
<summary>Show Answer</summary>

**Answer: B) Use the `com.amazonaws.region-code.oidc-eks` PrivateLink interface endpoint and verify its Region/DNS requirements**

**Explanation:**

Current EKS supports a PrivateLink interface endpoint for cluster OIDC discovery/JWKS, `com.amazonaws.region-code.oidc-eks`, for validators without internet egress. Verify that endpoint's Region/DNS requirements; the EKS management API endpoint is a different service.

</details>
