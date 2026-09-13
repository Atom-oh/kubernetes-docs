# SPIFFE/SPIRE Quiz

> **Last Updated**: September 13, 2026

## Questions

<span id="_1-what-is-the-correct-format-for-a-spiffe-id"></span>

### 1. Which is a valid SPIFFE ID?

- A) `https://example.org/app`
- B) `spiffe://example.org/app`
- C) `spiffe://example.org:8443/app`
- D) `spiffe://example.org/app?role=admin`

<details>
<summary>Show Answer</summary>

**Answer: B) spiffe://example.org/app**

Use the spiffe scheme, a trust domain, and an optional path. Ports, queries, and fragments are disallowed. Path structure is site-defined, not limited to /ns/.../sa/... .

</details>

<span id="_2-what-is-the-key-difference-between-x-509-svid-and-jwt-svid"></span>

### 2. Which statement correctly describes X.509/JWT-SVID validation?

- A) Only inspect X.509 CN
- B) A valid JWT signature makes audience unnecessary
- C) Validate X.509 URI SAN/chain and JWT signature/sub/audience/expiry
- D) JWT audience checks prevent every replay

<details>
<summary>Show Answer</summary>

**Answer: C) Validate X.509 URI SAN/chain and JWT signature/sub/audience/expiry**

Certificate CN is not the SPIFFE identity. A JWT bearer token may be replayed despite a matching audience. Lifetimes are policy-dependent; this chapter’s X.509/JWT scope is separate from the Incubating WIT-SVID specification.

</details>

<span id="_3-what-is-the-primary-role-of-the-spire-server"></span>

### 3. What is the role of SPIRE Server?

- A) Automatically encrypt every application connection
- B) Manage agent attestation, registration, and SVID signing
- C) Automatically authorize every service request
- D) Distribute private-key files to all Pods through CSI

<details>
<summary>Show Answer</summary>

**Answer: B) Manage agent attestation, registration, and SVID signing**

Distinguish CA/JWT signing, DataStore, and KeyManager responsibilities. An AWS PCA upstream signs SPIRE intermediate CAs; it does not eliminate local leaf signing or key management.

</details>

<span id="_4-what-is-the-primary-role-of-the-spire-agent"></span>

### 4. Who identifies the application calling the Workload API?

- A) The local SPIRE agent’s workload attestor
- B) A DNS resolver
- C) CSI checking filenames
- D) The application’s self-declared SPIFFE ID alone

<details>
<summary>Show Answer</summary>

**Answer: A) The local SPIRE agent’s workload attestor**

The agent examines caller PID/cgroups/Pod metadata and matches authorized entries/cache. Fetching inside an agent Pod attests that caller, not the actual application context.

</details>

<span id="_5-which-node-attestation-method-is-recommended-for-amazon-eks"></span>

### 5. How does the server validate a k8s_psat token?

- A) Checking an IRSA role’s S3 permissions
- B) Kubernetes TokenReview plus configured audience/SA allowlist
- C) Only base64 decoding the token
- D) Converting it to a non-expiring join token

<details>
<summary>Show Answer</summary>

**Answer: B) Kubernetes TokenReview plus configured audience/SA allowlist**

Match server/agent logical cluster names, token audience, SA allowlist, and TokenReview permissions. aws_iid is an alternative with different trust assumptions, not universally stronger or prohibited on EKS.

</details>

<span id="_6-what-selector-types-does-k8s-workload-attestation-support"></span>

### 6. How should k8s:container-image:nginx:* be interpreted?

- A) Automatic glob matching for every nginx tag
- B) A selector value; do not assume wildcard matching
- C) Proof that the image signature is verified
- D) Automatic enforcement of namespace RBAC

<details>
<summary>Show Answer</summary>

**Answer: B) A selector value; do not assume wildcard matching**

Match actual Kubernetes-reported image/ImageID values. Tags alone do not establish supply-chain trust. Pod/SA/label creation and modification permissions also influence identity eligibility.

</details>

<span id="_7-what-is-the-purpose-of-the-spiffe-csi-driver"></span>

### 7. What does SPIFFE CSI 0.2.13 mount into a Pod?

- A) Automatically generated svid.pem/svid.key files
- B) A directory containing the Workload API Unix socket
- C) The SPIRE CA private key
- D) Shared PostgreSQL data

<details>
<summary>Show Answer</summary>

**Answer: B) A directory containing the Workload API Unix socket**

CSI delivers access to the API socket. File-based applications need a separate adapter and reload handling. Applications or proxies still consume the API; integration is not universally automatic.

</details>

<span id="_8-what-does-spiffe-federation-enable"></span>

### 8. What is required to bootstrap https_spiffe federation?

- A) Only an endpoint URL
- B) An initial trusted bundle and correct endpoint SPIFFE ID
- C) Exchange both CA private keys
- D) Automatically authorize every remote workload

<details>
<summary>Show Answer</summary>

**Answer: B) An initial trusted bundle and correct endpoint SPIFFE ID**

Configure each trust direction. Bundle refresh, connectivity, TLS verification, and workload authorization are separate responsibilities. https_web uses the endpoint’s Web PKI validation path.

</details>

<span id="_9-how-does-spiffe-spire-compare-to-iam-roles-for-service-accounts-irsa"></span>

### 9. Which statement correctly compares IRSA and SPIFFE/SPIRE?

- A) IRSA refresh always requires Pod restart
- B) SPIFFE removes the need for AWS IAM policy
- C) IRSA is an AWS credential path; SPIFFE is workload identity, each requiring validation
- D) A Pod annotation completes IRSA and CSI certificate-file delivery

<details>
<summary>Show Answer</summary>

**Answer: C) IRSA is an AWS credential path; SPIFFE is workload identity, each requiring validation**

IRSA refreshes through supported SDK/projected-token behavior and supports cross-account designs. Validate ServiceAccount annotations, aud/sub trust, and AWS permissions. SPIFFE mTLS also requires credential consumption and peer authorization.

</details>

<span id="_10-what-are-best-practices-for-naming-trust-domains-in-spiffe"></span>

### 10. Which statement about trust domains and CA rotation is correct?

- A) A trust domain must be a resolvable DNS name
- B) bundle set automatically rotates the CA private key
- C) Choose stable names and distinguish bundle changes from CA-key rotation
- D) Numeric or IPv4-shaped domains are always rejected by the parser

<details>
<summary>Show Answer</summary>

**Answer: C) Choose stable names and distinguish bundle changes from CA-key rotation**

DNS-like naming is guidance, not the entire syntax rule. Bundles are public trust material; key rotation is a separate lifecycle. Verify authority overlap and consumer updates.

</details>

## Score Calculation

- 9–10: Strong understanding
- 7–8: Revisit trust, authorization, and delivery paths
- 6 or fewer: Review the guide and validated examples

## Related Documentation

- [SPIFFE/SPIRE](../../security/12-spiffe-spire.md)
