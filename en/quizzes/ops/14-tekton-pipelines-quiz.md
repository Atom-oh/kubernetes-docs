# Tekton Pipelines Quiz

1. Which correctly describes Task, TaskRun and Workspace?
   - A) A Task definition is already a running Pod
   - B) A TaskRun executes a Task; a Workspace is a volume-binding field
   - C) Workspace is always a separate CRD
   - D) Steps in one Pod are completely isolated from each other

<details>
<summary>Show Answer</summary>

**Answer: B) A TaskRun executes a Task; a Workspace is a volume-binding field**

Tasks/Pipelines are definitions and Runs are executions. Steps in one Pod share networking and volumes, so they are not a trust boundary.

</details>

---

2. Which is correct when sharing source between TaskRuns?
   - A) emptyDir shares the same files across Pods
   - B) A per-run PVC can be used; RWO/RWX themselves are not trust boundaries
   - C) Different subPaths make one PVC safe to share between external PRs and releases
   - D) Results are always unlimited strings

<details>
<summary>Show Answer</summary>

**Answer: B) A per-run PVC can be used; RWO/RWX themselves are not trust boundaries**

Use volumeClaimTemplate for per-run storage and separate writable data across trust levels. Use Results for small values and artifact storage for large reports.

</details>

---

3. How should an external PR be handled after GitHub HMAC verification?
   - A) Use the release pipeline's IRSA and signing privileges
   - B) Use a separate execution trust level with limited permissions
   - C) Interpolate its shell commands directly into scripts because HMAC passed
   - D) A verified request is always a main-branch push

<details>
<summary>Show Answer</summary>

**Answer: B) Use a separate execution trust level with limited permissions**

HMAC validates delivery origin, not permission for code to deploy. This chapter's privileged CI path is limited to the approved repository's protected main push.

</details>

---

4. Which provenance version does Chains' slsa/v1 formatter produce?
   - A) SLSA provenance v1.0
   - B) SLSA provenance v0.2; v1.0 uses slsa/v2alpha3 or slsa/v2alpha4
   - C) The signing key automatically chooses any version
   - D) Always the same version as the Kubernetes v1 API

<details>
<summary>Show Answer</summary>

**Answer: B) SLSA provenance v0.2; v1.0 uses slsa/v2alpha3 or slsa/v2alpha4**

Formatter names and SLSA specification versions differ. Pipeline-level provenance is created after Pipeline completion and needs separate verification/promotion.

</details>

---

5. Which statement about finally Tasks is correct?
   - A) They execute under every error, cancellation and timeout
   - B) They run after ordinary Tasks but missing Results, cancellation or timeout can skip/prevent them
   - C) They always execute sequentially in declaration order
   - D) They automatically supply defaults for missing image Results

<details>
<summary>Show Answer</summary>

**Answer: B) They run after ordinary Tasks but missing Results, cancellation or timeout can skip/prevent them**

The final report only references the run name and tasks.status. Do not assume ordering among finally Tasks; account for timeout behavior.

</details>

---

6. What remains after CI succeeds and chains.tekton.dev/signed=true is observed?
   - A) Immediately deploy an arbitrary tag to production
   - B) Verify trusted key, digest, builder and source provenance, then review the GitOps change
   - C) Only base64-decode signature JSON without verification
   - D) Check that ArgoCD itself pulls the application image

<details>
<summary>Show Answer</summary>

**Answer: B) Verify trusted key, digest, builder and source provenance, then review the GitOps change**

The signed annotation is not cryptographic verification or approval. ArgoCD syncs manifests; kubelets/runtimes pull images.

</details>

---

7. Which controller ServiceMonitor port and counter apply in Pipelines 1.16?
   - A) metrics / pipelinerun_count
   - B) http-metrics / tekton_pipelines_controller_pipelinerun_total
   - C) http / automatic counters for every namespace
   - D) 9097 / a running-duration histogram

<details>
<summary>Show Answer</summary>

**Answer: B) http-metrics / tekton_pipelines_controller_pipelinerun_total**

Match actual Service labels/ports and Prometheus selectors. The current completion counter carries status only, not a namespace label.

</details>

---

8. What is the default completion behavior for volumeClaimTemplate PVCs with coschedule=workspaces?
   - A) Always immediately deleted
   - B) Retained; the exact true auto-cleanup annotation can opt into completion cleanup
   - C) Existing user-provided PVCs are always deleted too
   - D) PipelineRuns have a default seven-day TTL

<details>
<summary>Show Answer</summary>

**Answer: B) Retained; the exact true auto-cleanup annotation can opt into completion cleanup**

Other coschedule modes and pre-existing PVCs have different lifecycles. Check completion time, retention and log/signature archives before deleting run records.

</details>
