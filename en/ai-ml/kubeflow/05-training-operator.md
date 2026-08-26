# Part 5: Kubeflow Trainer and Distributed Training

> **Supported Versions**: Kubeflow Trainer v2.1 (bundled in 26.03) through v2.3, legacy Training Operator 1.9.2 (bundled in Kubeflow Community Distribution 26.03)
> **Last Updated**: August 19, 2026

## Lab Environment Setup

To follow along with the examples in this document, you will need the following tools and environment:

### Required Tools

* kubectl v1.34 or later
* A working Amazon EKS cluster with a GPU-capable node pool (see the [Karpenter](../../autoscaling/02-karpenter.md) and GPU node scheduling material referenced below — this document does not re-derive that setup)
* Kubeflow installed via the Community Distribution, or Kubeflow Trainer installed standalone

## From Framework-Specific Operators to a Unified API

Distributed training on Kubernetes has gone through a real architectural shift inside the Kubeflow project, and this is the most important thing to understand before touching any YAML.

### The original Training Operator (v1)

The Training Operator that Kubeflow consolidated in 2021 took a **framework-specific CRD** approach. Each supported ML framework got its own Custom Resource Definition, each with its own controller implementing that framework's particular distributed-training semantics:

* **`PyTorchJob`** — the controller understood PyTorch's distributed launch conventions, injecting environment variables like `MASTER_ADDR`, `RANK`, and `WORLD_SIZE` into each worker Pod so `torch.distributed` could form a process group.
* **`TFJob`** — the controller instead constructed a `TF_CONFIG` environment variable (a JSON blob describing the cluster's task roles — chief, worker, parameter server) that TensorFlow's distribution strategies expect.
* **`MPIJob`** — the controller handled launching an MPI job across Pods, coordinating an `mpirun`-style launcher against a set of worker Pods.

Beyond these three, the v1 Training Operator also shipped CRDs for a handful of other frameworks. Each CRD encoded a different framework's idea of "how workers find each other and agree on their roles" directly into a separate controller, so adding a new framework meant writing an entirely new controller rather than reusing existing plumbing.

### The shift to Kubeflow Trainer v2

Kubeflow Trainer v2 replaces this with a single, unified API built around two concepts instead of one CRD per framework:

* **`TrainJob`** — describes *what* to run: the training script/entrypoint, arguments, resource counts (e.g., number of workers), and a reference to the runtime that should execute it. This is the object an ML practitioner creates for an individual training run.
* **`TrainingRuntime` / `ClusterTrainingRuntime`** — describes *how* to run it: a reusable, framework-specific execution template covering the container image, the distributed launch mechanics (how workers discover each other, what env vars or launcher process gets used), and default resource shape. A platform team defines a small set of these once — say, a PyTorch DDP runtime, an MPI runtime — and many different `TrainJob`s reference the same runtime across many training runs.

This mirrors a pattern seen elsewhere in Kubernetes: separating a reusable "template" resource from the "instance" that consumes it, similar in spirit to how a `StorageClass` is a reusable template that many `PersistentVolumeClaim`s reference. The practical benefit is that a platform team can own and version the tricky distributed-launch mechanics in one place (the runtime), while ML practitioners submitting jobs only need to supply their script and ask for a runtime by name — they don't need to know or care how rank assignment or address discovery actually happens under the hood.

According to its [release notes](https://github.com/kubeflow/trainer/releases), **Kubeflow Trainer v2.2** (released around March 2026, and the version bundled starting with the Kubeflow Community Distribution's 26.03.1 patch — 26.03 itself ships v2.1.0) builds on this with:

* First-class **JAX** and **XGBoost** training runtimes, alongside the existing PyTorch support — so distributed training for these frameworks now goes through the same `TrainJob`/runtime split rather than a bespoke CRD.
* Enhanced **observability**: training progress and metrics can be propagated from the training script itself up into the `TrainJob`'s status, rather than requiring an operator to go dig through logs or a separate metrics backend to see how a run is progressing.
* **Flux Framework integration**, bringing an HPC-style job launcher into the Trainer ecosystem for MPI-style workloads — useful for tightly-coupled, HPC-flavored distributed jobs that benefit from Flux's scheduling and process-launch model rather than a simpler `mpirun` launch.

### The migration is real but not finished

It's important not to overstate where the ecosystem actually is: the **Kubeflow Community Distribution 26.03** still bundles the **legacy Training Operator 1.9.2** — the v1, framework-specific-CRD operator — as of that release. Kubeflow Trainer v2 and the legacy Training Operator currently coexist in the ecosystem, and migrating a given team's jobs from `PyTorchJob`/`TFJob`/`MPIJob` manifests over to `TrainJob` + a runtime is an **active, ongoing transition** that many teams are only partway through — not a completed cutover you can assume has already happened in a given cluster.

If you're planning an actual migration, don't treat this document as the migration guide — the authoritative, field-by-field reference is **"Migrating to Kubeflow Trainer v2"** on [kubeflow.org](https://www.kubeflow.org/docs/components/trainer/operator-guides/migration/). That guide covers the concrete mapping from each v1 CRD's fields onto a `TrainJob` and a default runtime, which is out of scope to restate exhaustively here.

A separate note for anyone already running Trainer v2: **Trainer v2.3.0** (released August 2026) shipped after v2.2 with breaking changes to the runtime CRDs this document describes — Runtime Finalizers were removed, and CRDs moved into the Helm chart's template directory — and its own [release notes](https://github.com/kubeflow/trainer/releases) call out that clusters on v2.0/v2.1/v2.2 must upgrade to v2.3 before upgrading further. Check that guidance directly before upgrading a cluster already running Trainer v2.

## Conceptual Shape of a TrainJob

At a conceptual level (without inventing exact field names this document hasn't verified), a `TrainJob` for, say, a PyTorch distributed data-parallel (DDP) run splits responsibility roughly like this:

* A **`ClusterTrainingRuntime`**, created once by a platform team, that bundles: the training container image (or a base image expectation), the number of worker replicas as a default, and the distributed launch mechanics for PyTorch DDP (how the workers discover the rendezvous address and agree on rank/world size).
* A **`TrainJob`**, created per training run, that references that `ClusterTrainingRuntime` by name and supplies the run-specific pieces: the actual training script or command to execute, any script arguments (learning rate, dataset path, epochs, etc.), and how many workers this particular run needs.

The `TrainJob` is intentionally the "thin" object — most of the complexity about *how* distributed coordination happens lives in the runtime, not in every individual job manifest. This is what makes runtimes reusable across many training runs, and why a platform team, not each individual data scientist, typically owns and hardens the runtime definitions.

## Distributed Training Mechanics on Kubernetes

Regardless of which framework's runtime is in play, multi-worker distributed training on Kubernetes generally coordinates through the same handful of primitives:

* **A headless Service** in front of the worker Pods, so each worker gets a stable, resolvable DNS name for the others rather than relying on Pod IPs that can change on reschedule.
* **Injected environment variables** (or an equivalent config file/init step) that tell each worker its rank, the total worker count, and the address of whichever worker is acting as the rendezvous/coordinator — this is the mechanism `MASTER_ADDR`/`RANK`/`WORLD_SIZE` served for PyTorch, and what `TF_CONFIG` served for TensorFlow, generalized under the runtime abstraction in Trainer v2.
* **Gang scheduling considerations**: distributed training jobs generally need *all* their workers to be scheduled and running before training can start — a job that gets half its workers scheduled and waits indefinitely for the rest wastes GPU capacity and can deadlock. This is why distributed training controllers commonly rely on (or integrate with) gang-scheduling primitives — grouping a job's Pods so the scheduler treats them as an all-or-nothing unit — rather than the default Kubernetes behavior of scheduling each Pod independently.

On EKS specifically, this interacts directly with however your GPU node pools are provisioned and scaled. A distributed job that needs, say, 8 GPU workers needs 8 GPU-capable nodes (or slots) available at once — not one at a time as they trickle in from an autoscaler. The mechanics of sizing and scaling GPU node pools (Karpenter NodePools, instance type selection, binpacking GPUs) are covered in this site's autoscaling and GPU scheduling material rather than re-derived here. The point to carry into this document is simply that gang-scheduling requirements and GPU node pool elasticity need to be designed together, since a training job that can't get all its workers scheduled at once will stall regardless of how correct its `TrainJob`/runtime configuration is.

![The Kubeflow Trainer Controller watches both the TrainJob and its referenced ClusterTrainingRuntime, creates a JobSet that spawns gang-scheduled worker pods, which discover each other through a headless Service and report progress and metrics back to the controller, which in turn writes that into TrainJob status.](../../.gitbook/assets/en-ai-ml-kubeflow-05-training-operator-0.png)

## Cross-Reference: Katib and TrainJob

Part 4 of this series covers Katib, Kubeflow's hyperparameter-tuning component. Each Katib Trial in an experiment needs an underlying training job to actually run one hyperparameter combination — and in a Trainer v2-based setup, that underlying job is commonly a `TrainJob` templated by Katib once per Trial, with each Trial's chosen hyperparameter values injected as script arguments. The runtime/job split described above applies here too: Katib doesn't need to know anything about distributed launch mechanics — it just stamps out a `TrainJob` per Trial against a runtime the platform team already defined, and reads the reported metrics back to decide where to search next.

## Next Steps

With the shift from framework-specific CRDs to the unified `TrainJob`/runtime model in place, [Part 6: KServe — Model Serving on Kubernetes](./06-kserve.md) covers what happens to a model once training against a `TrainJob` completes: serving it for inference.

[Return to Main Page](./README.md)

## Quiz

To test what you've learned in this chapter, try the [Topic Quiz](../../quizzes/ai-ml/kubeflow/05-training-operator-quiz.md).
