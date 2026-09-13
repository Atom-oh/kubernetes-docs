<span id="quiz-questions"></span>

# Container Image Security Quiz
> **Last Updated**: September 13, 2026

<span id="_1-what-is-the-correct-command-to-scan-a-container-image-with-trivy"></span>

### 1. Which command scans a given image reference with Trivy?

A. trivy scan "$IMAGE_REF"
B. trivy image "$IMAGE_REF"
C. trivy container "$IMAGE_REF"
D. trivy check "$IMAGE_REF"

<details>
<summary>Show Answer</summary>

**Answer: B. trivy image "$IMAGE_REF"**

trivy image is the image-scanning command. Set IMAGE_REF to a real digest reference. Valid syntax alone does not establish registry access, database freshness, or package-detection coverage.

</details>

<span id="_2-which-tool-is-used-for-image-signing-and-verification"></span>

### 2. Which tool verifies a relationship between an image digest and an approved signer?

A. Trivy’s CVE database
B. Cosign/Sigstore
C. Clair’s package scanner
D. Docker imagePullPolicy

<details>
<summary>Show Answer</summary>

**Answer: B. Cosign/Sigstore**

Cosign verifies a key or OIDC identity/issuer, digest, and required transparency evidence. Signatures do not guarantee the absence of known vulnerabilities.

</details>

<span id="_3-what-does-the-shift-left-security-approach-mean"></span>

### 3. What does shift-left security mean?

A. Deferring checks until production
B. Checking earlier in development, PRs, and builds
C. Restricting source access to the security team
D. Removing production rescanning

<details>
<summary>Show Answer</summary>

**Answer: B. Checking earlier in development, PRs, and builds**

Earlier checks shorten feedback loops. New CVEs and runtime behavior still require registry rescanning and runtime detection after release.

</details>

<span id="_4-what-is-the-main-characteristic-of-distroless-images"></span>

### 4. What characterizes a standard distroless runtime image?

A. Every Linux utility is included
B. A minimal set of application runtime components
C. A shell and debugger are always included
D. A package manager is mandatory

<details>
<summary>Show Answer</summary>

**Answer: B. A minimal set of application runtime components**

Standard runtimes omit shells/package managers; debug variants differ. Application binaries and libraries can still contain vulnerabilities.

</details>

<span id="_5-what-are-the-two-types-of-amazon-ecr-image-scanning"></span>

### 5. How do current ECR Basic and Enhanced scanning differ?

A. Basic uses AWS-native OS scanning; Enhanced uses Inspector for OS/language packages
B. Basic always uses Clair; Enhanced scans only OS packages
C. Both automatically reject pushes
D. Enhanced scans every image forever

<details>
<summary>Show Answer</summary>

**Answer: A. Basic uses AWS-native OS scanning; Enhanced uses Inspector for OS/language packages**

Basic supports manual/scan-on-push; Enhanced supports scan-on-push/continuous. Distinguish findings from enhancedFindings and ECR from Inspector events.

</details>

<span id="_6-what-is-sbom-software-bill-of-materials"></span>

### 6. What does an SBOM provide?

A. Certification that no vulnerabilities exist
B. An inventory of software components detected by a tool
C. Automatic proof of an approved signer
D. Deployment authorization

<details>
<summary>Show Answer</summary>

**Answer: B. An inventory of software components detected by a tool**

SBOMs record components and relationships but may have incomplete coverage. Assess signed attestations binding them to a digest and the verification policy separately.

</details>

<span id="_7-what-policy-type-verifies-image-signatures-in-kyverno"></span>

### 7. Which rule performs image signature checks in legacy Kyverno ClusterPolicy?

A. validate only
B. mutate only
C. verifyImages
D. generate only

<details>
<summary>Show Answer</summary>

**Answer: C. verifyImages**

Distinguish legacy verifyImages from the newer ImageValidatingPolicy. The Kyverno 1.19.1 example uses CEL policies alongside registry/digest restrictions covering ordinary, init, and ephemeral containers.

</details>

<span id="_8-why-should-you-use-digests-instead-of-image-tags"></span>

### 8. Why pin an image digest instead of a tag?

A. It is always shorter
B. It identifies specific image content
C. It automatically verifies signatures
D. It removes CVEs

<details>
<summary>Show Answer</summary>

**Answer: B. It identifies specific image content**

Tags can move; digests identify content. This supports reproducible artifact selection but does not replace signer trust, vulnerability checks, or availability validation.

</details>

<span id="_9-what-does-trivy-not-scan"></span>

### 9. Which area is separate from Trivy’s static checks?

A. OS package identification
B. Language-dependency scanning
C. Live syscall/process behavior detection
D. Source-secret detection

<details>
<summary>Show Answer</summary>

**Answer: C. Live syscall/process behavior detection**

Package, misconfiguration, and secret scanning differ from runtime behavior detection. Design runtime tooling such as Falco separately.

</details>

<span id="_10-which-is-not-a-container-image-registry-security-best-practice"></span>

### 10. Which registry access practice is inappropriate?

A. Approved pull identities for private images
B. Digest/signature verification for public images
C. Allowing arbitrary anonymous image pushes/deletes
D. Separating registry, admission, and scan-gate permissions

<details>
<summary>Show Answer</summary>

**Answer: C. Allowing arbitrary anonymous image pushes/deletes**

Anonymous reads of intentionally public images are not inherently vulnerabilities. Control confidentiality, write/delete permissions, provenance, and rate limits separately.

</details>

<span id="_11-what-is-the-recommended-action-when-image-scanning-fails-in-ci-cd-pipeline"></span>

### 11. What should happen when the agreed CI scan gate does not pass?

A. Always ignore it
B. Stop before publishing/signing and inspect the cause
C. Rebuild another image and push without scanning
D. Force exit code 0

<details>
<summary>Show Answer</summary>

**Answer: B. Stop before publishing/signing and inspect the cause**

Distinguish policy violations from scanner/database/permission errors and retain results. Do not deploy a different artifact rebuilt after the scan. Exceptions need rationale, ownership, and expiry.

</details>

<span id="_12-what-is-not-an-advantage-of-alpine-base-images"></span>

### 12. Which assumption about Alpine is incorrect?

A. It uses musl libc
B. It uses the apk package manager
C. It is always fully compatible with glibc-dependent applications
D. The selected release’s support lifetime must be checked

<details>
<summary>Show Answer</summary>

**Answer: C. It is always fully compatible with glibc-dependent applications**

Alpine uses musl, so glibc-dependent binaries can have compatibility issues. Image size alone guarantees neither vulnerability counts nor build speed.

</details>
