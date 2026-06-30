# Tekton Pipelines Quiz

1. What advantage does Tekton have over Jenkins or GitHub Actions in Kubernetes environments?
   - A) Tekton provides more plugins
   - B) CRD-based pipelines are managed as Kubernetes resources, enabling GitOps, RBAC, and namespace isolation
   - C) Tekton provides faster execution speed
   - D) Tekton is free while other tools are paid

<details>
<summary>Show Answer</summary>

**Answer: B) CRD-based pipelines are managed as Kubernetes resources, enabling GitOps, RBAC, and namespace isolation**

**Explanation:**
Tekton defines Tasks, Pipelines, and PipelineRuns as Kubernetes CRDs. This enables declarative pipeline management in Git (GitOps), access control via Kubernetes RBAC, namespace-level isolation, and management via kubectl. Each Step runs in a separate container for strong isolation.

</details>

---

2. How do you share data between Tasks in a Tekton Pipeline?
   - A) Pass via environment variables
   - B) Share file systems through Workspaces (PVC) and pass small data via Results
   - C) Store in ConfigMaps
   - D) Direct network communication between Tasks

<details>
<summary>Show Answer</summary>

**Answer: B) Share file systems through Workspaces (PVC) and pass small data via Results**

**Explanation:**
Workspaces are PVC-based file system sharing between Tasks, ideal for patterns like cloning source code then building. Results pass small string data (image tags, commit SHAs, etc.) between Tasks, referenced as `$(tasks.task-name.results.result-name)`.

</details>

---

3. What does Tekton Triggers' EventListener do?
   - A) Generate events and send them to external systems
   - B) Receive webhook requests and automatically create PipelineRuns via TriggerBinding/TriggerTemplate
   - C) Monitor pipeline execution results
   - D) Periodically poll Git repositories

<details>
<summary>Show Answer</summary>

**Answer: B) Receive webhook requests and automatically create PipelineRuns via TriggerBinding/TriggerTemplate**

**Explanation:**
The EventListener is an HTTP endpoint that receives webhook requests (GitHub Push, PR events, etc.). Interceptors validate/filter the request, TriggerBinding extracts parameters from the payload, and TriggerTemplate creates a PipelineRun with those parameters.

</details>

---

4. What Supply Chain Security feature does Tekton Chains provide?
   - A) Scan container images for vulnerabilities
   - B) Automatically sign TaskRun/PipelineRun artifacts (images) and generate SLSA Provenance
   - C) Encrypt network traffic
   - D) Auto-generate RBAC policies

<details>
<summary>Show Answer</summary>

**Answer: B) Automatically sign TaskRun/PipelineRun artifacts (images) and generate SLSA Provenance**

**Explanation:**
Tekton Chains automatically signs OCI images with Cosign/Sigstore after TaskRun completion and generates SLSA Provenance (build metadata, source information, build steps, etc.). This strengthens software supply chain security and enables verification of image origin and integrity.

</details>

---

5. What is the purpose of `finally` Tasks in a Tekton Pipeline?
   - A) Execute as the first Task in the pipeline
   - B) Cleanup tasks that always run last regardless of pipeline success/failure
   - C) Conditionally executed Tasks
   - D) Tasks that run in parallel

<details>
<summary>Show Answer</summary>

**Answer: B) Cleanup tasks that always run last regardless of pipeline success/failure**

**Explanation:**
`finally` Tasks run after all other Tasks in the pipeline complete, regardless of success or failure. Since they execute even on build failures, they're ideal for temporary resource cleanup, notification sending, and test result reporting. Similar to a try-catch-finally pattern.

</details>

---

6. Why separate CI/CD in an ArgoCD + Tekton integration architecture?
   - A) Because Tekton doesn't support CD
   - B) Separating CI (build/test) and CD (deploy) concerns improves security, auditing, and rollback
   - C) Because ArgoCD doesn't support CI
   - D) Because the tools have different licenses

<details>
<summary>Show Answer</summary>

**Answer: B) Separating CI (build/test) and CD (deploy) concerns improves security, auditing, and rollback**

**Explanation:**
Tekton handles CI (source clone, test, build, image push) while ArgoCD handles CD (Git-based declarative deployment). CI commits the image tag to Git, and ArgoCD detects this change to deploy. This enables deployment permission separation, Git-based audit trails, and declarative rollback.

</details>

---

7. What is a use case for the CEL Interceptor in Tekton?
   - A) Verify GitHub signatures
   - B) Filter and transform webhook payloads using CEL expressions (specific branches, file paths, etc.)
   - C) Verify GitLab tokens
   - D) Process Bitbucket events

<details>
<summary>Show Answer</summary>

**Answer: B) Filter and transform webhook payloads using CEL expressions (specific branches, file paths, etc.)**

**Explanation:**
The CEL (Common Expression Language) Interceptor performs filtering and transformation on webhook payloads using CEL expressions. For example, `body.ref == 'refs/heads/main'` filters only main branch pushes, or `body.commits.exists(c, c.modified.exists(f, f.startsWith('src/')))` triggers only on specific path changes.

</details>

---

8. What is an appropriate cleanup strategy for Tekton PipelineRuns?
   - A) Keep all PipelineRuns permanently
   - B) Set TTL-based auto-deletion with different retention periods for success/failure to manage resources
   - C) Delete manually only
   - D) PipelineRuns are automatically deleted

<details>
<summary>Show Answer</summary>

**Answer: B) Set TTL-based auto-deletion with different retention periods for success/failure to manage resources**

**Explanation:**
PipelineRuns and TaskRuns remain in etcd after execution, consuming storage. Use Tekton's cleanup settings (`keep`, `keep-since`) or CronJob-based cleanup scripts to automatically delete old execution records. Failed runs are typically retained longer for debugging purposes.

</details>
