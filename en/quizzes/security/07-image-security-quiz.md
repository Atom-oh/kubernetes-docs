# Container Image Security Quiz

This quiz tests your understanding of image scanning, image signing, supply chain security, and base image selection.

## Quiz Questions

### 1. What is the correct command to scan a container image with Trivy?

A. trivy scan nginx:latest
B. trivy image nginx:latest
C. trivy container nginx:latest
D. trivy check nginx:latest

<details>
<summary>Show Answer</summary>

**Answer: B. trivy image nginx:latest**

**Explanation:**
Trivy's image scanning command:
```bash
trivy image nginx:latest
trivy image --severity HIGH,CRITICAL nginx:latest
trivy image --format json nginx:latest
```

`trivy image` scans container images for vulnerabilities.

</details>

### 2. Which tool is used for image signing and verification?

A. Trivy
B. Cosign/Sigstore
C. Clair
D. Anchore

<details>
<summary>Show Answer</summary>

**Answer: B. Cosign/Sigstore**

**Explanation:**
Cosign is part of the Sigstore project, a tool for container image signing and verification:
```bash
# Sign image
cosign sign --key cosign.key myregistry/myimage:tag

# Verify signature
cosign verify --key cosign.pub myregistry/myimage:tag
```

Trivy, Clair, and Anchore are vulnerability scanners.

</details>

### 3. What does the "Shift-Left" security approach mean?

A. Defer security to operations phase
B. Move security to early development stages
C. Security team only responsible
D. Remove automation

<details>
<summary>Show Answer</summary>

**Answer: B. Move security to early development stages**

**Explanation:**
Shift-Left security moves security checks to the earliest possible stage in the development cycle:
- Scanning at IDE stage
- Build gates in CI/CD pipeline
- Security checks during PR review

The earlier problems are found, the lower the cost to fix.

</details>

### 4. What is the main characteristic of Distroless images?

A. Include all Linux utilities
B. Include only minimal components needed to run applications
C. Include debugging tools
D. Include package managers

<details>
<summary>Show Answer</summary>

**Answer: B. Include only minimal components needed to run applications**

**Explanation:**
Distroless images have:
- No shell (bash, sh, etc.)
- No package manager
- No unnecessary utilities
- Minimal attack surface
- Only application runtime

Benefits in security and image size.

</details>

### 5. What are the two types of Amazon ECR image scanning?

A. Basic scanning, Enhanced scanning
B. Automatic scanning, Manual scanning
C. Quick scanning, Deep scanning
D. Free scanning, Paid scanning

<details>
<summary>Show Answer</summary>

**Answer: A. Basic scanning, Enhanced scanning**

**Explanation:**
Amazon ECR scanning types:
- **Basic scanning**: Clair-based, OS package vulnerability scan
- **Enhanced scanning**: Amazon Inspector-based, OS + programming language packages, continuous scanning

Enhanced scanning has additional cost but is more comprehensive.

</details>

### 6. What is SBOM (Software Bill of Materials)?

A. List of software licenses
B. List of software components
C. List of security vulnerabilities
D. List of build commands

<details>
<summary>Show Answer</summary>

**Answer: B. List of software components**

**Explanation:**
SBOM is a list of all components (libraries, dependencies, versions, etc.) included in software. Essential for supply chain security and vulnerability management:
```bash
# Generate SBOM with Trivy
trivy image --format spdx-json -o sbom.json nginx:latest
```

</details>

### 7. What policy type verifies image signatures in Kyverno?

A. validate
B. mutate
C. verifyImages
D. generate

<details>
<summary>Show Answer</summary>

**Answer: C. verifyImages**

**Explanation:**
Kyverno's `verifyImages` rule verifies container image signatures:
```yaml
spec:
  rules:
  - name: verify-signature
    verifyImages:
    - imageReferences:
      - "myregistry/*"
      attestors:
      - entries:
        - keys:
            publicKeys: |-
              -----BEGIN PUBLIC KEY-----
              ...
              -----END PUBLIC KEY-----
```

</details>

### 8. Why should you use digests instead of image tags?

A. Shorter names
B. Guaranteed immutability
C. Faster pulling
D. Save storage space

<details>
<summary>Show Answer</summary>

**Answer: B. Guaranteed immutability**

**Explanation:**
Tags (e.g., `nginx:latest`) can be changed to point to different images. Digests (e.g., `nginx@sha256:abc123...`) are hashes of specific image content and are immutable:
```yaml
image: nginx@sha256:abc123def456...
```

This ensures reproducibility and security.

</details>

### 9. What does Trivy NOT scan?

A. OS package vulnerabilities
B. Language-specific dependencies
C. Runtime behavior
D. Secret detection

<details>
<summary>Show Answer</summary>

**Answer: C. Runtime behavior**

**Explanation:**
Trivy is a static analysis tool that scans:
- OS package vulnerabilities
- Language-specific dependencies (npm, pip, go, etc.)
- IaC misconfigurations
- Hardcoded secrets
- Licenses

Runtime behavior analysis is the domain of runtime security tools like Falco.

</details>

### 10. Which is NOT a container image registry security best practice?

A. Use private registry
B. Enable image scanning
C. Allow anonymous pulling
D. Block vulnerable image push

<details>
<summary>Show Answer</summary>

**Answer: C. Allow anonymous pulling**

**Explanation:**
Registry security best practices:
- Use private registry
- IAM-based authentication
- Enable image scanning
- Block vulnerable image push/pull
- Image signature verification
- Use immutable tags or digests

Anonymous pulling is a security risk and should be disabled in production environments.

</details>

### 11. What is the recommended action when image scanning fails in CI/CD pipeline?

A. Log warning only
B. Stop the build
C. Auto-fix
D. Ignore and proceed

<details>
<summary>Show Answer</summary>

**Answer: B. Stop the build**

**Explanation:**
In CI/CD pipelines, builds should stop when Critical/High vulnerabilities are found:
```bash
trivy image --exit-code 1 --severity HIGH,CRITICAL myimage:tag
```

`--exit-code 1` returns a non-zero exit code when vulnerabilities are found, failing the pipeline.

</details>

### 12. What is NOT an advantage of Alpine base images?

A. Small size
B. Fewer vulnerabilities
C. glibc compatibility
D. Fast builds

<details>
<summary>Show Answer</summary>

**Answer: C. glibc compatibility**

**Explanation:**
Alpine Linux characteristics:
- Small size (~5MB)
- Minimal packages
- Uses musl libc (not glibc)

Alpine uses musl libc instead of glibc, so some applications that depend on glibc may have compatibility issues.

</details>
