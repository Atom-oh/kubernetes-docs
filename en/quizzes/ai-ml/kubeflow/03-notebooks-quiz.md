# Kubeflow Notebooks Quiz

Baseline: Notebooks 1.11.0 / Community Distribution 26.03.1.

## Multiple Choice Questions

1. What does the Notebook controller reconcile?

   - A) A browser process on the user laptop
   - B) StatefulSet, Service and configured routing resources from a Notebook CR
   - C) An EC2 instance for every user
   - D) Only an HTML dashboard

<details>
<summary>Show Answer</summary>

**Answer: B) StatefulSet, Service and configured routing resources from a Notebook CR**

The StatefulSet controller creates Pods and Kubernetes schedules them. The dashboard is a UI entry point.
</details>

2. What is the precise version baseline here?

   - A) All components are Workspaces GA
   - B) Notebooks v1.11.0; 26.03.1 calls Workspaces beta while its images are v2.0.0-alpha.3
   - C) Notebook and Workspace are identical APIs
   - D) v1 has a confirmed end-of-support date in this chapter

<details>
<summary>Show Answer</summary>

**Answer: B) Notebooks v1.11.0; 26.03.1 calls Workspaces beta while its images are v2.0.0-alpha.3**

Release descriptions and image tags differ. Verify actual API/migration support instead of inferring GA or a v1 retirement date.
</details>

3. Does a Profile automatically isolate every notebook from every other user?

   - A) Yes, including AWS and storage
   - B) No; Profiles can be shared and network, storage, IAM and app authorization remain separate
   - C) Yes, because namespaces block network packets
   - D) Yes, because RBAC cancels all unrelated grants

<details>
<summary>Show Answer</summary>

**Answer: B) No; Profiles can be shared and network, storage, IAM and app authorization remain separate**

The full UI selects a Profile namespace. The Notebook CRD itself does not require a Profile object in every namespace.
</details>

4. What survives replacement of a notebook Pod?

   - A) All process memory
   - B) Every package installed anywhere in the container
   - C) Data on retained persistent volumes; container-layer packages and kernel memory do not
   - D) Every attached EC2 instance

<details>
<summary>Show Answer</summary>

**Answer: C) Data on retained persistent volumes; container-layer packages and kernel memory do not**

Check mount locations, PVC/volume lifecycle and backups. ReadWriteOnce is a single-node access mode, not a single-Pod guarantee.
</details>

5. What are the inspected idle-culling defaults?

   - A) Enabled, with a one-minute idle threshold
   - B) Disabled; idle threshold 1440 minutes, check period 1 minute
   - C) Enabled for every RStudio and shell process
   - D) Disabled only for GPU notebooks

<details>
<summary>Show Answer</summary>

**Answer: B) Disabled; idle threshold 1440 minutes, check period 1 minute**

The culler uses Jupyter kernel activity. Failed/empty API results leave old activity unchanged and can still lead to stopping. Test the actual image and access path.
</details>

6. How does v1.11.0 represent a stopped Notebook?

   - A) spec.replicas: 0
   - B) Presence of kubeflow-resource-stopped; the controller sets StatefulSet replicas to zero
   - C) Annotation value false means running
   - D) Deleting its PVC

<details>
<summary>Show Answer</summary>

**Answer: B) Presence of kubeflow-resource-stopped; the controller sets StatefulSet replicas to zero**

NotebookSpec has no replicas field. Resume by removing the annotation. Even a false string still counts as present.
</details>

7. What does a custom image digest guarantee?

   - A) All users have identical complete runtime environments
   - B) The referenced image content; mounted data and runtime changes can still differ
   - C) Automatic compatibility with all GPU drivers
   - D) That UI image restrictions cannot be bypassed through the API

<details>
<summary>Show Answer</summary>

**Answer: B) The referenced image content; mounted data and runtime changes can still differ**

Use tested server-prefix/port/UID behavior, dependencies and architecture. A mutable tag alone does not pin image bytes.
</details>

## Short Answer Questions

8. Why does stopping an idle GPU notebook not guarantee immediate cost savings?

<details>
<summary>Show Answer</summary>

Pod requests can be released, but other workloads, PDBs, NodePool limits/disruption policies and capacity management affect node termination. EC2 charges can continue while the node remains running.
</details>

9. How do RBAC, Istio authorization and NetworkPolicy differ for notebooks?

<details>
<summary>Show Answer</summary>

RBAC governs Kubernetes API actions. Istio authorization controls requests handled by configured proxies and policies. NetworkPolicy governs allowed Pod network traffic when enforced by the CNI. None alone guarantees storage/IAM/application isolation.
</details>

---

[Return to Learning Materials](../../../ai-ml/kubeflow/03-notebooks.md)
