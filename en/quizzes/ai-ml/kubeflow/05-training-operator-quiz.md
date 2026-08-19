# Kubeflow Trainer and Distributed Training Quiz

This quiz tests your understanding of the legacy Training Operator's framework-specific CRDs, the shift to Kubeflow Trainer v2's unified `TrainJob`/runtime model, and distributed training mechanics on Kubernetes.

## Multiple Choice Questions

1. What was the fundamental architectural approach of the original (v1) Training Operator, consolidated in 2021?
   - A) A single CRD that all frameworks shared, with framework detection at runtime
   - B) A separate CRD (e.g., `PyTorchJob`, `TFJob`, `MPIJob`) per ML framework, each with its own controller implementing that framework's distributed-training semantics
   - C) No CRDs at all — jobs were submitted directly via a `kubectl run` container with training args baked into the image
   - D) A single `TrainingJob` CRD with a `framework` field but one shared controller

<details>
<summary>Show Answer</summary>

**Answer: B) A separate CRD (e.g., `PyTorchJob`, `TFJob`, `MPIJob`) per ML framework, each with its own controller implementing that framework's distributed-training semantics**

**Explanation:**
The v1 Training Operator provided one CRD per framework — `PyTorchJob`, `TFJob`, `MPIJob`, and others — each backed by its own controller that understood that specific framework's distributed-training conventions (e.g., PyTorch's rank/env-var model vs. TensorFlow's `TF_CONFIG`).

</details>

2. What environment variables did the `PyTorchJob` controller inject to let workers form a `torch.distributed` process group?
   - A) `TF_CONFIG` only
   - B) `MASTER_ADDR`, `RANK`, and `WORLD_SIZE`
   - C) `KUBEFLOW_HOST` and `KUBEFLOW_PORT`
   - D) `POD_IP` and `POD_NAMESPACE`

<details>
<summary>Show Answer</summary>

**Answer: B) `MASTER_ADDR`, `RANK`, and `WORLD_SIZE`**

**Explanation:**
The `PyTorchJob` controller injected `MASTER_ADDR`, `RANK`, and `WORLD_SIZE` into each worker Pod so PyTorch's `torch.distributed` machinery could form a process group and coordinate.

</details>

3. What is the central architectural change introduced by Kubeflow Trainer v2 compared to the v1 Training Operator?
   - A) It adds more framework-specific CRDs on top of the existing ones
   - B) It replaces per-framework CRDs with a unified `TrainJob` API plus reusable `TrainingRuntime`/`ClusterTrainingRuntime` templates
   - C) It removes the need for controllers entirely, relying only on admission webhooks
   - D) It merges `TrainJob` and `ClusterTrainingRuntime` back into a single per-framework CRD

<details>
<summary>Show Answer</summary>

**Answer: B) It replaces per-framework CRDs with a unified `TrainJob` API plus reusable `TrainingRuntime`/`ClusterTrainingRuntime` templates**

**Explanation:**
Instead of one CRD and controller per framework, Trainer v2 introduces `TrainJob` (what to run) and `TrainingRuntime`/`ClusterTrainingRuntime` (how to run it — a reusable, framework-specific execution template), decoupling job submission from distributed-launch mechanics.

</details>

4. In the `TrainJob` / `ClusterTrainingRuntime` split, which object is typically owned by a platform team and reused across many individual training runs?
   - A) `TrainJob`
   - B) `ClusterTrainingRuntime`
   - C) Both are always created fresh per run
   - D) Neither — a `PyTorchJob` is created instead

<details>
<summary>Show Answer</summary>

**Answer: B) `ClusterTrainingRuntime`**

**Explanation:**
`ClusterTrainingRuntime` (or the namespace-scoped `TrainingRuntime`) is the reusable template a platform team defines once, covering the container image and distributed launch mechanics. Individual `TrainJob`s reference it by name and supply only the run-specific script, arguments, and worker count.

</details>

5. What two additional training runtimes did Kubeflow Trainer v2.2 add first-class support for?
   - A) TensorFlow and MXNet
   - B) JAX and XGBoost
   - C) Scikit-learn and ONNX
   - D) Spark MLlib and H2O

<details>
<summary>Show Answer</summary>

**Answer: B) JAX and XGBoost**

**Explanation:**
According to Kubeflow Trainer's [release notes](https://github.com/kubeflow/trainer/releases), v2.2 (released around March 2026) added first-class JAX and XGBoost training runtimes alongside existing PyTorch support, along with enhanced observability and Flux Framework integration for HPC-style workloads.

</details>

6. Which statement most accurately describes the current state of the v1-to-Trainer-v2 migration as of the Kubeflow Community Distribution 26.03 release?
   - A) The migration is fully complete; the legacy Training Operator has been removed from all distributions
   - B) The legacy Training Operator (1.9.2) is still bundled alongside Trainer v2 in the 26.03 distribution, and migrating existing jobs to `TrainJob` is an active, ongoing transition for many teams
   - C) Kubeflow Trainer v2 was deprecated in favor of reverting to the v1 CRDs
   - D) `TrainJob` and `PyTorchJob` are simply two names for the identical CRD

<details>
<summary>Show Answer</summary>

**Answer: B) The legacy Training Operator (1.9.2) is still bundled alongside Trainer v2 in the 26.03 distribution, and migrating existing jobs to `TrainJob` is an active, ongoing transition for many teams**

**Explanation:**
The Kubeflow Community Distribution 26.03 still ships the legacy Training Operator 1.9.2 alongside Trainer v2, reflecting that the two coexist and that many teams are still mid-migration rather than having completed a full cutover to `TrainJob`.

</details>

7. Why do distributed training jobs typically require gang scheduling?
   - A) Kubernetes requires all Pods in a namespace to be gang-scheduled by default
   - B) All workers generally need to be scheduled and running together before training can start; partial scheduling wastes GPU capacity and can deadlock
   - C) Gang scheduling is required only for stateless web workloads
   - D) It is a billing requirement imposed by cloud providers

<details>
<summary>Show Answer</summary>

**Answer: B) All workers generally need to be scheduled and running together before training can start; partial scheduling wastes GPU capacity and can deadlock**

**Explanation:**
A distributed training job that gets only some of its required workers scheduled can wait indefinitely for the rest, wasting held GPU capacity and potentially deadlocking. Gang-scheduling primitives group a job's Pods as an all-or-nothing scheduling unit to avoid this.

</details>

## Short Answer Questions

8. What role does a headless Service play in coordinating a multi-worker distributed training job on Kubernetes?

<details>
<summary>Show Answer</summary>

**Answer:** It gives each worker Pod a stable, resolvable DNS name so other workers can discover it, instead of relying on Pod IPs that can change on reschedule.

**Explanation:**
Distributed training workers need to find each other reliably; a headless Service in front of the worker Pods provides stable DNS-based discovery that survives individual Pod rescheduling.

</details>

9. In the Katib cross-reference from this document, what role does a `TrainJob` play within a Katib Trial?

<details>
<summary>Show Answer</summary>

**Answer:** Katib commonly templates a `TrainJob` as the underlying training job for each Trial, injecting that Trial's chosen hyperparameter values as script arguments, and reads back the reported metrics to guide the search.

**Explanation:**
Katib itself doesn't need to know about distributed-launch mechanics — it stamps out a `TrainJob` per Trial against a runtime the platform team already defined, keeping the hyperparameter-search logic decoupled from the training execution mechanics.

</details>

10. Where should you go for the authoritative, field-by-field reference on migrating existing v1 CRD manifests (e.g., `PyTorchJob`) to Kubeflow Trainer v2, rather than relying on this document?

<details>
<summary>Show Answer</summary>

**Answer:** The "Migrating to Kubeflow Trainer v2" guide on kubeflow.org.

**Explanation:**
This document covers the conceptual shift and mechanics at a high level but deliberately does not restate every migration step; the official kubeflow.org migration guide is the authoritative source for the concrete field-by-field mapping.

</details>

---

[Return to Learning Materials](../../../ai-ml/kubeflow/05-training-operator.md)
