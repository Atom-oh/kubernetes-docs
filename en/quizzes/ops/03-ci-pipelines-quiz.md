# CI Pipelines Quiz

> **Related document**: [CI Pipelines](../../ops/03-ci-pipelines.md)

## Multiple Choice Questions

### 1. Why do release images and BuildKit cache use separate ECR repositories?

- A) Cache images do not require IAM authentication
- B) Immutable release tags and mutable cache references need different policies
- C) ECR supports only one tag
- D) Caching removes the need for scanning

<details>
<summary>Show Answer</summary>

**Answer: B) Immutable release tags and mutable cache references need different policies**

**Explanation:** The example makes the application repository IMMUTABLE and build-cache MUTABLE. A commit-SHA-shaped tag alone does not prevent overwrites; deployments consume the verified digest.

</details>

### 2. What does a separate Pod per GitLab Kubernetes-executor job provide?

- A) Complete isolation even for privileged jobs
- B) Removal of every node-access risk
- C) Separate job lifecycles and resources, without guaranteeing a complete security boundary
- D) Safe inherited AWS publishing access for untrusted PRs

<details>
<summary>Show Answer</summary>

**Answer: C) Separate job lifecycles and resources, without guaranteeing a complete security boundary**

**Explanation:** This guide's privileged DinD configuration is for trusted protected jobs. Pod separation, dedicated CI nodes, and least-privilege roles are distinct controls; none alone proves arbitrary untrusted code is safe.

</details>

### 3. How do poll_interval and check_interval differ?

- A) poll_interval checks Kubernetes Pod status; check_interval concerns coordinator job polling
- B) They are aliases for the same setting
- C) Both expire Docker image caches
- D) poll_interval restarts Pods

<details>
<summary>Show Answer</summary>

**Answer: A) poll_interval checks Kubernetes Pod status; check_interval concerns coordinator job polling**

**Explanation:** The Kubernetes executor uses poll_interval while waiting for a job Pod to become ready. The Runner-wide check_interval controls a different polling path; changing one does not substitute for changing the other.

</details>

### 4. Why separate the GitLab manager and build Pod AWS roles?

- A) To give the manager every AWS permission
- B) Because Pod Identity automatically creates ServiceAccounts
- C) Because build Pods must store long-lived keys
- D) To scope manager S3-cache access separately from build Pod ECR publishing access

<details>
<summary>Show Answer</summary>

**Answer: D) To scope manager S3-cache access separately from build Pod ECR publishing access**

**Explanation:** Without RoleARN, the example's S3 cache uses the manager credential chain. Build Pods receive a different ECR role. ServiceAccounts must be created separately; the AWS Pod Identity token is distinct from the normal Kubernetes API token.

</details>

### 5. How does the current ARC example receive and route jobs?

- A) It installs only RunnerDeployment and HorizontalRunnerAutoscaler
- B) It uses official scale-set charts/listeners and matches runs-on to the actual scale-set name
- C) An organization runner-group name is always a job label
- D) minRunners=0 removes every cluster cost

<details>
<summary>Show Answer</summary>

**Answer: B) It uses official scale-set charts/listeners and matches runs-on to the actual scale-set name**

**Explanation:** Do not mix the legacy CRD model with current scale-set charts. ARC 0.14.2 also supports scaleSetLabels. minRunners concerns idle runners; it does not remove controller/listener costs or guarantee no startup latency.

</details>

### 6. Which GitHub jobs acquire the example's AWS OIDC credentials?

- A) Every external PR test
- B) A pull_request_target job that executes arbitrary PR code
- C) Trusted push publishing jobs after tests pass
- D) Every self-hosted runner when it boots

<details>
<summary>Show Answer</summary>

**Answer: C) Trusted push publishing jobs after tests pass**

**Explanation:** PR tests run on GitHub-hosted runners without requesting publishing credentials. The role trust restricts the exact repository and main/protected tags, and ARC Pods do not inherit an AWS publishing role.

</details>

### 7. Which sequence preserves the scan-to-publish contract?

- A) Build → successfully scan the same image → publish → create an index from approved digests
- B) Publish → ignore scan failure → deploy latest
- C) Scan source → rebuild a different image → always publish
- D) Treat the existence of any JSON file as a successful scan

<details>
<summary>Show Answer</summary>

**Answer: A) Build → successfully scan the same image → publish → create an index from approved digests**

**Explanation:** GitLab passes image archives through architecture-specific 1:1 dependencies. GitHub scans its locally built image before pushing it. Trivy errors or vulnerability-gate failures prevent publishing; native Trivy JSON is not mislabeled as GitLab's report schema.

</details>

### 8. Which statement correctly compares native runners and QEMU?

- A) A platform flag alone makes every foreign instruction executable
- B) QEMU itself is the application's cross compiler
- C) An AMD64 image becomes ARM64 by retagging
- D) Native runners build on the target CPU; QEMU emulates another CPU's instructions

<details>
<summary>Show Answer</summary>

**Answer: D) Native runners build on the target CPU; QEMU emulates another CPU's instructions**

**Explanation:** Align manager/job node selectors, runner tags, and helper architecture. The final index must reference independently checked platform digests. Cross-compilation requires a deliberately configured toolchain and Dockerfile.

</details>

### 9. What does the Next.js standalone example require?

- A) npm ci --omit=dev is sufficient for every build
- B) Standalone output, build dependencies, copied static assets, and the correct server path
- C) public and .next/static are always copied into standalone automatically
- D) Every monorepo starts at root/server.js

<details>
<summary>Show Answer</summary>

**Answer: B) Standalone output, build dependencies, copied static assets, and the correct server path**

**Explanation:** The example assumes one app root and an npm lockfile. It copies public and .next/static into the runtime layout and binds to 0.0.0.0. Monorepos need their own tracing-root and nested-output-path checks.

</details>

### 10. Which statement about Kaniko and rootless BuildKit is correct?

- A) Daemonless guarantees every build runs without root and is completely isolated
- B) Renaming the privileged DinD image completes a rootless setup
- C) Check maintenance status and node user-namespace, mount, and security-policy support
- D) no-process-sandbox strengthens process isolation

<details>
<summary>Show Answer</summary>

**Answer: C) Check maintenance status and node user-namespace, mount, and security-policy support**

**Explanation:** The Google Kaniko repository is archived. The optional rootless BuildKit fragment needs a separately validated runner. no-process-sandbox weakens daemon-container process isolation and cleanup; registry cache also does not automatically persist every cache mount.

</details>
