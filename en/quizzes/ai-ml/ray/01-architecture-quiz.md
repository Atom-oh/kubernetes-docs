# Ray Architecture Quiz

## Multiple Choice Questions

1. How do you submit a remote function?
   - A) Call f(...) normally
   - B) Use f.remote(...) on the @ray.remote function
   - C) Only call ray.get(f)
   - D) Create a Pod for each call

<details>
<summary>Show Answer</summary>

**Answer: B**

The single-return example yields an ObjectRef; ray.get reads its value.
</details>

2. Are all Ray tasks independent and side-effect-free?
   - A) Yes; Ray never tracks dependencies
   - B) No; account for ObjectRef dependencies, side effects, and retries
   - C) Only actors return ObjectRefs
   - D) Every function executes exactly once

<details>
<summary>Show Answer</summary>

**Answer: B**

A stateless execution unit is not a purity or exactly-once guarantee.
</details>

3. Which actor-state statement is accurate?
   - A) Instance memory persists across calls; failure recovery is separate
   - B) All state is automatically durable
   - C) Actors run only on the head
   - D) Enabling restarts restores previous memory

<details>
<summary>Show Answer</summary>

**Answer: A**

max_restarts reruns the constructor; it does not replace checkpoint recovery.
</details>

4. What zero-copy scope was verified?
   - A) All Python objects and GPU memory
   - B) One physical RAM shared by every node
   - C) Read-only NumPy shared-memory views on the same node
   - D) Zero network-transfer cost in all cases

<details>
<summary>Show Answer</summary>

**Answer: C**

Mutation requires copying. Do not generalize to other objects, GPUs, or cross-node transfers.
</details>

5. What is the GCS name and role?
   - A) Global Control Service; cluster metadata such as actors, nodes, placement groups
   - B) GPU Copy Store for all weights
   - C) Global Control Store; the sole owner of all ObjectRef metadata
   - D) Replacement for the Kubernetes API server

<details>
<summary>Show Answer</summary>

**Answer: A**

Object ownership metadata belongs to the process creating the original ObjectRef, not universally to the GCS.
</details>

6. Can two nodes with one free CPU each execute one two-CPU task?
   - A) Always, because their sum is two
   - B) Ray automatically splits the task in half
   - C) No; the task must fit one feasible node
   - D) CPU requirements never matter if memory is available

<details>
<summary>Show Answer</summary>

**Answer: C**

Cluster-level selection still depends on node-level resource feasibility.
</details>

7. What does num_cpus=1 mean?
   - A) The OS pins all threads to one core
   - B) A logical Ray scheduling/admission requirement, separate from OS limits
   - C) A guaranteed dedicated physical core
   - D) An automatic GPU-memory limit

<details>
<summary>Show Answer</summary>

**Answer: B**

Container limits and library thread settings are separate.
</details>

8. What does KubeRay do?
   - A) Automatically chooses Train, Tune, or Serve for the application
   - B) Reconciles Ray CRs and Pod lifecycles on Kubernetes
   - C) Replaces kube-scheduler
   - D) Creates a new EC2 instance for every Ray task

<details>
<summary>Show Answer</summary>

**Answer: B**

Ray work scheduling, Pod placement, and EC2 provisioning are separate layers.
</details>

## Short Answer Questions

9. Why is an actor appropriate for keeping a model resident across requests?

<details>
<summary>Show Answer</summary>

An explicit remote instance owns the state. Do not rely on incidental task-worker global-cache reuse for correctness. Actor failure still requires checkpoint and recovery design.
</details>

10. Why separate GCS recovery from object and actor application recovery?

<details>
<summary>Show Answer</summary>

Durable cluster metadata, object ownership/lineage/value recovery, and actor checkpoints solve different problems. Redis or alpha RocksDB configuration alone does not restore every value and application state.
</details>

---

[Return to Learning Materials](../../../ai-ml/ray/01-architecture.md)
