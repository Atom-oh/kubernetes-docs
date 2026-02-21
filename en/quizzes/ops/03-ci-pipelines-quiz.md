# CI Pipelines Quiz

> **Related Document**: [CI Pipelines](../../ops/03-ci-pipelines.md)

## Multiple Choice Questions

### 1. What is the primary purpose of ECR lifecycle policies?

- A) To automatically build container images
- B) To manage image retention and reduce storage costs
- C) To scan images for vulnerabilities
- D) To replicate images across regions

<details>
<summary>Show Answer</summary>

**Answer: B) To manage image retention and reduce storage costs**

**Explanation:**
ECR lifecycle policies automatically expire and delete old images based on rules like age or count. This prevents unbounded storage growth and reduces costs while retaining important images (like production tags) indefinitely.

</details>

### 2. When running GitLab Runner on EKS, which executor type is recommended for isolation?

- A) Shell executor
- B) Docker executor
- C) Kubernetes executor
- D) SSH executor

<details>
<summary>Show Answer</summary>

**Answer: C) Kubernetes executor**

**Explanation:**
The Kubernetes executor runs each CI job in a separate pod, providing strong isolation between jobs. It automatically cleans up resources after jobs complete and can leverage Kubernetes features like node selectors and tolerations.

</details>

### 3. What is GitHub Actions Runner Controller (ARC)?

- A) A GitHub-hosted runner service
- B) A Kubernetes operator for self-hosted GitHub runners
- C) A GitHub API client library
- D) A container registry controller

<details>
<summary>Show Answer</summary>

**Answer: B) A Kubernetes operator for self-hosted GitHub runners**

**Explanation:**
ARC is a Kubernetes operator that automatically scales self-hosted GitHub Actions runners based on workflow demand. It creates runner pods when jobs are queued and cleans them up after completion.

</details>

### 4. What is the benefit of multi-platform container builds (linux/amd64, linux/arm64)?

- A) Smaller image sizes
- B) Faster build times
- C) Support for different CPU architectures (x86 and Graviton)
- D) Better security scanning

<details>
<summary>Show Answer</summary>

**Answer: C) Support for different CPU architectures (x86 and Graviton)**

**Explanation:**
Multi-platform builds create images that work on both x86 (amd64) and ARM (arm64/Graviton) processors. This enables cost optimization by using Graviton instances and supports diverse deployment environments.

</details>

### 5. How does BuildKit cache improve container build performance?

- A) By skipping all build steps
- B) By caching layer artifacts and reusing unchanged layers
- C) By compressing images smaller
- D) By parallelizing all operations

<details>
<summary>Show Answer</summary>

**Answer: B) By caching layer artifacts and reusing unchanged layers**

**Explanation:**
BuildKit intelligently caches build artifacts and layer outputs. When source files haven't changed, it reuses cached layers instead of rebuilding. Cache can be stored in registries, S3, or local storage for sharing across builds.

</details>

### 6. What is Kaniko primarily used for?

- A) Container orchestration
- B) Building container images without Docker daemon
- C) Container runtime security
- D) Image vulnerability scanning

<details>
<summary>Show Answer</summary>

**Answer: B) Building container images without Docker daemon**

**Explanation:**
Kaniko builds container images from Dockerfiles without requiring a Docker daemon or privileged mode. This makes it ideal for CI/CD environments where running Docker-in-Docker poses security concerns or isn't available.

</details>

### 7. In GitLab CI, what is the purpose of the `services` keyword?

- A) To define deployment targets
- B) To spin up auxiliary containers (like databases) for testing
- C) To configure GitLab Pages
- D) To set up monitoring

<details>
<summary>Show Answer</summary>

**Answer: B) To spin up auxiliary containers (like databases) for testing**

**Explanation:**
The `services` keyword defines containers that run alongside the main job container. These are commonly used for test dependencies like databases (PostgreSQL, MySQL) or caches (Redis) that tests need to interact with.

</details>

### 8. What is the recommended approach for storing container build cache in CI/CD?

- A) Local disk only
- B) Registry-based cache with --cache-to and --cache-from flags
- C) Never use cache in CI/CD
- D) Store cache in git repository

<details>
<summary>Show Answer</summary>

**Answer: B) Registry-based cache with --cache-to and --cache-from flags**

**Explanation:**
Registry-based caching stores build cache layers in a container registry, making it accessible across different CI runners. BuildKit's `--cache-to` and `--cache-from` flags enable this pattern for consistent build acceleration.

</details>

### 9. When configuring GitHub ARC, what does the `minRunners` setting control?

- A) Maximum concurrent jobs
- B) Minimum number of idle runners maintained
- C) Runner memory allocation
- D) Job timeout duration

<details>
<summary>Show Answer</summary>

**Answer: B) Minimum number of idle runners maintained**

**Explanation:**
`minRunners` ensures a baseline of warm runners are always available, reducing job startup latency. Setting this above zero prevents cold-start delays for time-sensitive workflows but increases idle resource costs.

</details>

### 10. What is the security benefit of using IAM roles for CI/CD runners instead of long-lived credentials?

- A) Faster authentication
- B) Automatic credential rotation and reduced exposure risk
- C) Simpler configuration
- D) Cross-account access

<details>
<summary>Show Answer</summary>

**Answer: B) Automatic credential rotation and reduced exposure risk**

**Explanation:**
IAM roles provide temporary credentials that automatically rotate, eliminating the risk of long-lived access keys being leaked or compromised. Combined with Pod Identity or IRSA, runners get scoped permissions without storing secrets.

</details>
